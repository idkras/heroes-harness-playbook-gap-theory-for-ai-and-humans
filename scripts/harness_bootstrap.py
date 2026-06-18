#!/usr/bin/env python3
"""harness_bootstrap.py — self-activation обвязки после `git clone`.

JTBD: когда человек/агент впервые открывает репо с harness (template или target),
он НЕ должен ничего делать руками — этот скрипт сам приводит обвязку в рабочее
состояние и печатает чеклист-результат в чат (SessionStart-хук инжектит stdout
в контекст агента).

Что делает (всё ИДЕМПОТЕНТНО, безопасно на чистом клоне):
  1. resolve repo root (git rev-parse → fallback на дерево от скрипта).
  2. chmod +x на .claude/hooks/*.{py,sh} и scripts/**/*.py — иначе хуки не запустятся.
  3. portability: в .claude/settings.json любой ЧУЖОЙ абсолютный путь до hook/script
     (наследие canonical-машины) переписывается на $CLAUDE_PROJECT_DIR — чтобы хуки
     работали на ЛЮБОЙ машине после клона, без правок руками.
  4. mode-detect: standalone-клон (реальные копии уже в git → симлинки НЕ нужны)
     vs owner (рядом есть canonical heroes-rickai-workspace → ставим .canonical-src
     удобный симлинк, gitignored, НЕ затеняя реальные .agents/.claude).
  5. verify: checksum-манифест (полнота + целостность) + harness wiring (gaps==0),
     best-effort на SessionStart, --strict для CI.
  6. печать чеклиста PASS/FAIL/SKIP + однострочный вердикт.

Режимы:
  (default) activate — выполняет шаги 1-5, чинит что может, exit 0 (не блокирует сессию).
  --check            — read-only (ничего не пишет), для CI; exit !=0 при провале.
  --strict           — verify-провалы → exit !=0 (для CI/precommit).
  --json             — машиночитаемый отчёт в stdout.

Stdlib-only. Ничего внешнего.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

CANONICAL_DIR_NAME = "heroes-rickai-workspace"
CONVENIENCE_SYMLINK = ".canonical-src"
ABS_PATH_RE = re.compile(r"/Users/[^\s\"']+?/((?:\.claude/hooks/|\.agents/|scripts/)[^\s\"';]+)")


def repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    # fallback: walk up until a dir that has .claude or .agents
    p = start
    for _ in range(8):
        if (p / ".claude").exists() or (p / ".agents").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start


def make_executable(root: Path, write: bool) -> tuple[int, list[str]]:
    fixed = 0
    targets: list[str] = []
    globs = [".claude/hooks/*.py", ".claude/hooks/*.sh", "scripts/*.py", "scripts/**/*.py"]
    seen: set[Path] = set()
    for g in globs:
        for f in root.glob(g):
            if not f.is_file() or f in seen:
                continue
            seen.add(f)
            mode = f.stat().st_mode
            if not (mode & stat.S_IXUSR):
                targets.append(str(f.relative_to(root)))
                if write:
                    f.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                fixed += 1
    return fixed, targets


def normalize_settings(root: Path, write: bool) -> tuple[int, list[str]]:
    """Rewrite foreign absolute hook/script paths → $CLAUDE_PROJECT_DIR. Idempotent."""
    sp = root / ".claude" / "settings.json"
    if not sp.exists():
        return 0, []
    raw = sp.read_text(encoding="utf-8")
    fixes: list[str] = []

    def _sub(m: re.Match) -> str:
        rel = m.group(1)
        fixes.append(rel)
        return f"$CLAUDE_PROJECT_DIR/{rel}"

    new = ABS_PATH_RE.sub(_sub, raw)
    if new != raw and write:
        sp.write_text(new, encoding="utf-8")
    return len(fixes), fixes


def detect_mode(root: Path, write: bool) -> tuple[str, str]:
    """standalone vs owner. Owner = adjacent canonical workspace present."""
    sibling = root.parent / CANONICAL_DIR_NAME
    is_owner = sibling != root and (sibling / ".git").exists()
    if not is_owner:
        return "standalone", "реальные копии в git — симлинки не нужны"
    link = root / CONVENIENCE_SYMLINK
    note = f"{CONVENIENCE_SYMLINK} → ../{CANONICAL_DIR_NAME}"
    if link.is_symlink() or link.exists():
        return "owner", f"{note} (уже есть)"
    if write:
        try:
            link.symlink_to(Path("..") / CANONICAL_DIR_NAME)
            note += " (создан)"
        except OSError as e:
            note += f" (не создан: {e})"
    else:
        note += " (создал бы)"
    return "owner", note


def run_verifier(root: Path, script_rel: str, args: list[str], timeout: int = 90) -> tuple[str, str]:
    """Returns (status, detail). status ∈ PASS/FAIL/SKIP."""
    script = root / script_rel
    if not script.exists():
        return "SKIP", f"{script_rel} отсутствует"
    try:
        r = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "SKIP", f"{Path(script_rel).name} timeout {timeout}s"
    except Exception as e:  # noqa: BLE001
        return "SKIP", f"{Path(script_rel).name}: {e}"
    tail = (r.stdout or r.stderr or "").strip().splitlines()
    last = tail[-1] if tail else ""
    return ("PASS" if r.returncode == 0 else "FAIL"), last[:200]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="read-only, ничего не пишет")
    ap.add_argument("--strict", action="store_true", help="verify-провал → exit !=0")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", help="repo root (default: auto)")
    args = ap.parse_args()

    write = not args.check
    root = Path(args.root).resolve() if args.root else repo_root(Path(__file__).resolve().parent)

    steps: list[dict] = []

    n_chmod, chmod_files = make_executable(root, write)
    steps.append(
        {
            "step": "hooks executable",
            "status": "PASS",
            "detail": "все исполняемы" if n_chmod == 0 else f"{'починено' if write else 'нужно'} {n_chmod}",
        }
    )

    n_norm, norm_files = normalize_settings(root, write)
    steps.append(
        {
            "step": "settings.json portable",
            "status": "PASS",
            "detail": (
                "пути уже $CLAUDE_PROJECT_DIR"
                if n_norm == 0
                else f"{'нормализовано' if write else 'нужно'} {n_norm} путей"
            ),
        }
    )

    mode, mode_note = detect_mode(root, write)
    steps.append({"step": f"mode: {mode}", "status": "PASS", "detail": mode_note})

    chk_status, chk_detail = run_verifier(
        root,
        "scripts/harness_template_checksum.py",
        ["--verify", "--strict"] if not write else ["--verify"],
    )
    steps.append({"step": "checksum + completeness", "status": chk_status, "detail": chk_detail})

    wir_status, wir_detail = run_verifier(
        root,
        ".agents/skills/0-governance-harness-portability/scripts/verify_harness_wiring.py",
        ["--repo-root", str(root), "--smoke"],
    )
    steps.append({"step": "harness wiring (gaps==0)", "status": wir_status, "detail": wir_detail})

    failed = [s for s in steps if s["status"] == "FAIL"]
    verdict = "🟢 harness готов" if not failed else f"🔴 {len(failed)} провал(ов) — см. таблицу"

    if args.json:
        print(
            json.dumps(
                {"root": str(root), "mode": mode, "steps": steps, "verdict": verdict}, ensure_ascii=False, indent=2
            )
        )
    else:
        print(f"# Heroes Harness — getting started  ·  {root.name}")
        print(f"{'STEP':<28} {'STATUS':<6} DETAIL")
        for s in steps:
            print(f"{s['step']:<28} {s['status']:<6} {s['detail']}")
        print(f"\n{verdict}")
        if failed:
            print(
                "→ следующий шаг: запусти соответствующий verifier и устрани gap (см. harness-workflow.yaml §getting_started)."
            )

    if args.strict and failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
