#!/usr/bin/env python3
"""graphify.py — публичный построитель графа зависимостей харнесса (networkx).

JTBD: «Graphify» в canonical-харнессе строил graphify-out/graph.json и был
canonical-only. Этот публичный эквивалент строит ТОТ ЖЕ артефакт из двух
объявленных источников (см. config/root-structure-manifest.yaml: harness-workflow.yaml
= "graphify dep-graph source"):

  1. beads — живой граф задач: узлы из `bd list --json`, рёбра-зависимости из
     `bd graph --all --dot`. Это «каждая работа через beads».
  2. harness-workflow.yaml — стадии процесса (change_lifecycle, session_start_chain)
     как узлы + последовательные рёбра.

Результат — graphify-out/graph.json в формате networkx node-link (queryable).
guardian-проверка `graph` (harness_guardian_check.py) зеленеет при свежем файле.

Режимы:
  (default) build  — собрать граф, записать graphify-out/graph.json
  --doctor         — перезагрузить граф и проверить queryability (узлы/рёбра/DAG)
  --check          — read-only: есть ли свежий graph.json (exit!=0 если нет/устарел)

Деградация: нет bd → строим только из workflow yaml; нет PyYAML → только из beads.
Нужен networkx (в requirements.txt). Без него — понятная ошибка с подсказкой.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

OUT_REL = "graphify-out/graph.json"
FRESH_H = 168  # 7 дней — тот же порог, что у harness_guardian_check._row_graph


def _repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    p = start
    for _ in range(8):
        if (p / ".claude").exists() or (p / "config").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start


def _run(cmd: list[str], cwd: Path, timeout: int = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "")
    except (subprocess.TimeoutExpired, OSError):
        return 1, ""


# ── source 1: beads ───────────────────────────────────────────────────────────
def add_beads(G, root: Path) -> dict:
    stats = {"bd": False, "issues": 0, "dep_edges": 0}
    rc, out = _run(["bd", "list", "--all", "--json"], root)
    if rc != 0 or not out.strip():
        rc, out = _run(["bd", "list", "--json"], root)
    if rc == 0 and out.strip():
        try:
            data = json.loads(out)
            issues = data if isinstance(data, list) else data.get("issues", data.get("data", []))
            for it in issues:
                iid = it.get("id")
                if not iid:
                    continue
                G.add_node(iid, kind="task", layer="beads",
                           title=(it.get("title") or "")[:120],
                           status=it.get("status"), priority=it.get("priority"),
                           issue_type=it.get("issue_type"))
                stats["issues"] += 1
            stats["bd"] = True
        except json.JSONDecodeError:
            pass
    # рёбра-зависимости из DOT (несколько digraph-блоков — парсим все)
    rc, dot = _run(["bd", "graph", "--all", "--dot"], root)
    if rc == 0 and dot:
        for a, b in re.findall(r'"([^"]+)"\s*->\s*"([^"]+)"', dot):
            G.add_node(a, kind="task", layer="beads")
            G.add_node(b, kind="task", layer="beads")
            G.add_edge(a, b, kind="depends_on")
            stats["dep_edges"] += 1
    return stats


# ── source 2: harness-workflow.yaml ────────────────────────────────────────────
def add_workflow(G, root: Path) -> dict:
    stats = {"yaml": False, "stages": 0}
    wf = root / "harness-workflow.yaml"
    if not wf.exists():
        return stats
    try:
        import yaml  # optional
    except ImportError:
        return stats
    try:
        doc = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
    except Exception:
        return stats
    stats["yaml"] = True
    # change_lifecycle: упорядоченная цепочка стадий
    prev = None
    for i, stage in enumerate(doc.get("change_lifecycle", []) or []):
        nid = f"lifecycle:{i}"
        label = stage if isinstance(stage, str) else str(stage)
        G.add_node(nid, kind="workflow_stage", layer="lifecycle", title=label[:120], order=i)
        if prev is not None:
            G.add_edge(prev, nid, kind="then")
        prev = nid
        stats["stages"] += 1
    # session_start_chain
    prev = None
    for i, st in enumerate((doc.get("getting_started", {}) or {}).get("session_start_chain", []) or []):
        nid = f"session_start:{i}"
        label = st.get("step", f"step{i}") if isinstance(st, dict) else str(st)
        G.add_node(nid, kind="session_start", layer="bootstrap", title=str(label)[:120], order=i)
        if prev is not None:
            G.add_edge(prev, nid, kind="then")
        prev = nid
    return stats


def build(root: Path) -> tuple[Path, dict]:
    try:
        import networkx as nx
    except ImportError:
        print("graphify: нужен networkx — `bash scripts/setup/install_all.sh` "
              "(или .venv/bin/pip install networkx)", file=sys.stderr)
        raise SystemExit(3)
    G = nx.DiGraph()
    s_bd = add_beads(G, root)
    s_wf = add_workflow(G, root)
    out = root / OUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = nx.node_link_data(G)
    payload["_meta"] = {
        "generator": "scripts/graphify.py",
        "sources": {"beads": s_bd, "workflow_yaml": s_wf},
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(G),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, payload["_meta"]


def doctor(root: Path) -> int:
    """queryability: перезагрузить и убедиться что граф читается и осмыслен."""
    try:
        import networkx as nx
    except ImportError:
        print("graphify-doctor: networkx отсутствует", file=sys.stderr)
        return 3
    out = root / OUT_REL
    if not out.exists():
        print(f"graphify-doctor: {OUT_REL} отсутствует — запусти `python3 scripts/graphify.py`", file=sys.stderr)
        return 1
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        G = nx.node_link_graph(data)
    except Exception as e:  # noqa: BLE001
        print(f"graphify-doctor: graph.json не queryable: {e}", file=sys.stderr)
        return 1
    m = data.get("_meta", {})
    print(f"graphify-doctor: OK — nodes={G.number_of_nodes()} edges={G.number_of_edges()} "
          f"is_dag={m.get('is_dag')} sources={m.get('sources')}")
    return 0


def check(root: Path) -> int:
    out = root / OUT_REL
    if not out.exists():
        print(f"graphify --check: {OUT_REL} отсутствует", file=sys.stderr)
        return 1
    age_h = (time.time() - out.stat().st_mtime) / 3600.0
    if age_h >= FRESH_H:
        print(f"graphify --check: stale {age_h:.0f}h (>{FRESH_H}h) — пересобери", file=sys.stderr)
        return 1
    print(f"graphify --check: fresh ({age_h:.0f}h)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--doctor", action="store_true", help="проверить queryability графа")
    ap.add_argument("--check", action="store_true", help="read-only: свежесть graph.json")
    ap.add_argument("--root", help="repo root (default: auto)")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else _repo_root(Path(__file__).resolve().parent)
    if args.doctor:
        return doctor(root)
    if args.check:
        return check(root)
    out, meta = build(root)
    print(f"graphify: {out.relative_to(root)} — nodes={meta['nodes']} edges={meta['edges']} "
          f"is_dag={meta['is_dag']} (beads={meta['sources']['beads']['issues']} issues, "
          f"workflow_stages={meta['sources']['workflow_yaml'].get('stages', 0)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
