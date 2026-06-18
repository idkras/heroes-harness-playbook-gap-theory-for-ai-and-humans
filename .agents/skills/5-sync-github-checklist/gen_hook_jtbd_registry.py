#!/usr/bin/env python3
"""Hook JTBD registry generator — companion to 5-sync-github-checklist SKILL.md.

JTBD (когда меняем/удаляем хук → хотим видеть его назначение + eval-покрытие →
чтобы НЕ потерять JTBD хука и механически ловить регрессию «хуже не стало»).

Этот генератор — SSOT реестра. Реестр НЕ редактируется руками (он бы дрейфовал
относительно settings.json). Источники истины:
  - `.claude/settings.json`     — какие хуки wired, на какое событие
  - `lefthook.yml`              — git-hook-wired (pre-push и т.п.)
  - docstring каждого хука      — назначение (JTBD-триада)
  - `scripts/test_hooks_smoke.py` + `.claude/hooks/tests/` — eval-покрытие

Режимы:
  python3 gen_hook_jtbd_registry.py            → печатает markdown реестра в stdout
  python3 gen_hook_jtbd_registry.py --write    → пишет hook-jtbd-registry.md рядом
  python3 gen_hook_jtbd_registry.py --check     → exit 2 если есть wired-хук без eval
                                                  и без waiver (regression gate)

«хуже не стало» (--check): если wired-хук теряет фикстуру ИЛИ добавлен новый wired-хук
без фикстуры и без явного waiver в EVAL_WAIVERS — gate падает. Это механический слой,
который вызывается из lefthook pre-push (см. SKILL.md §Pre-flight).
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path

# repo root = 4 levels up from this file (.agents/skills/<skill>/file.py)
ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
LEFTHOOK = ROOT / "lefthook.yml"
SMOKE = ROOT / "scripts" / "test_hooks_smoke.py"
TESTS_DIR = HOOKS_DIR / "tests"
REGISTRY_MD = Path(__file__).resolve().parent / "hook-jtbd-registry.md"

# Хуки, для которых eval осознанно НЕ требуется (с причиной).
# Формат: module_name -> reason (≥12 chars). Любой waiver виден в реестре отдельной меткой.
EVAL_WAIVERS: dict[str, str] = {
    "session_isolation_guard": "SessionStart advisory-only, печатает баннер, не блокирует — нечего фальсифицировать",
    "reasoning_log_stop": "append-only лог-строка на Stop, без условной логики блокировки",
    "skill_path_scope_activate": "PostToolUse path-scoped surface, без exit-2 ветки",
}

# Хуки-кандидаты на удаление (deprecated). Формат: module -> (DEBT-id, reason).
DEPRECATED: dict[str, tuple[str, str]] = {
    "agents_md_reflect_propose": (
        "DEBT-055",
        "auto-grow AGENTS.md без auto-shrink → 10× раздувание; удаление не доехало до main",
    ),
}


def _hook_event_map() -> dict[str, set[str]]:
    """module -> set of event names (PreToolUse/PostToolUse/Stop/...) from settings.json."""
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for event, blocks in (data.get("hooks") or {}).items():
        text = json.dumps(blocks)
        for mod in re.findall(r"hooks/([a-z0-9_]+)\.py", text):
            out.setdefault(mod, set()).add(event)
    # lefthook-wired
    if LEFTHOOK.exists():
        for mod in re.findall(r"hooks/([a-z0-9_]+)\.py", LEFTHOOK.read_text(encoding="utf-8")):
            out.setdefault(mod, set()).add("lefthook(git)")
    return out


def _eval_coverage(mod: str, smoke_src: str, test_files: list[str]) -> str:
    if re.search(r"\b" + re.escape(mod) + r"\b", smoke_src):
        return "smoke"
    if any(mod in t for t in test_files):
        return "unit"
    return ""


def _purpose(mod: str) -> str:
    p = HOOKS_DIR / f"{mod}.py"
    if not p.exists():
        return "(file missing)"
    src = p.read_text(encoding="utf-8", errors="replace")
    try:
        ds = ast.get_docstring(ast.parse(src))
    except SyntaxError:
        ds = None
    if ds:
        return ds.strip().splitlines()[0][:110]
    for ln in src.splitlines():
        s = ln.strip()
        if s.startswith("#") and len(s) > 10:
            return s.lstrip("#").strip()[:110]
    return "(no docstring)"


def _rows() -> list[dict]:
    events = _hook_event_map()
    smoke_src = SMOKE.read_text(encoding="utf-8") if SMOKE.exists() else ""
    test_files = os.listdir(TESTS_DIR) if TESTS_DIR.is_dir() else []
    rows = []
    for mod in sorted(events):
        cov = _eval_coverage(mod, smoke_src, test_files)
        waived = mod in EVAL_WAIVERS
        deprecated = mod in DEPRECATED
        if deprecated:
            status = "⚪"
        elif cov:
            status = "🟢"
        elif waived:
            status = "🟡"  # осознанно без eval (waiver)
        else:
            status = "🔴"  # wired, БЕЗ eval, БЕЗ waiver — regression-незащищён
        rows.append(
            {
                "mod": mod,
                "events": ", ".join(sorted(events[mod])),
                "purpose": _purpose(mod),
                "eval": cov or ("waiver" if waived else "—"),
                "status": status,
                "note": (DEPRECATED[mod][0] + ": " + DEPRECATED[mod][1]) if deprecated else (EVAL_WAIVERS.get(mod, "")),
            }
        )
    return rows


def _markdown(rows: list[dict]) -> str:
    g = sum(1 for r in rows if r["status"] == "🟢")
    y = sum(1 for r in rows if r["status"] == "🟡")
    rd = sum(1 for r in rows if r["status"] == "🔴")
    w = sum(1 for r in rows if r["status"] == "⚪")
    lines = [
        "# Hook JTBD registry — что каждый хук делает + покрыт ли eval",
        "",
        "**GENERATED — не редактировать руками.** SSOT: `gen_hook_jtbd_registry.py` "
        "(этот же каталог). Перегенерировать: `python3 gen_hook_jtbd_registry.py --write`.",
        "",
        "**Назначение (JTBD):** когда хук в системе git-sync/governance меняется или удаляется — "
        "видим его назначение и eval-покрытие, чтобы НЕ потерять JTBD хука и механически ловить "
        "регрессию «хуже не стало» (`--check` в lefthook pre-push).",
        "",
        "**Легенда статуса:**",
        "",
        "- 🟢 — wired + есть eval-фикстура (регрессия ловится)",
        "- 🟡 — wired, eval осознанно не нужен (waiver с причиной)",
        "- 🔴 — wired, БЕЗ eval и БЕЗ waiver → регрессия НЕ ловится (долг R2)",
        "- ⚪ — deprecated / кандидат на удаление (см. note)",
        "",
        f"**Сводка:** wired={len(rows)} · 🟢 {g} · 🟡 {y} · 🔴 {rd} · ⚪ {w}",
        "",
        "| Статус | Хук | Событие | JTBD (назначение) | Eval | Note |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        purpose = r["purpose"].replace("|", "\\|")
        note = r["note"].replace("|", "\\|")
        lines.append(f"| {r['status']} | `{r['mod']}` | {r['events']} | {purpose} | {r['eval']} | {note} |")
    lines += [
        "",
        "## Как читать «хуже не стало»",
        "",
        "Каждый 🟢 хук имеет фикстуру в `scripts/test_hooks_smoke.py` или "
        "`.claude/hooks/tests/test_*.py`. Перед sync/push: `python3 scripts/test_hooks_smoke.py` "
        "(см. lefthook pre-push) — если хоть одна фикстура красная, push прерывается. "
        "`gen_hook_jtbd_registry.py --check` дополнительно падает, если появился новый wired-хук "
        "без eval и без waiver (новый 🔴), чтобы покрытие не деградировало молча.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    rows = _rows()
    if "--check" in argv:
        uncovered = [r["mod"] for r in rows if r["status"] == "🔴"]
        # baseline: текущие 🔴 разрешены (долг R2); --check падает только на ПРИРОСТ
        # сверх baseline-файла, если он есть.
        baseline_file = Path(__file__).resolve().parent / ".hook-eval-baseline.txt"
        baseline = set()
        if baseline_file.exists():
            baseline = {x.strip() for x in baseline_file.read_text().splitlines() if x.strip()}
        new_uncovered = sorted(set(uncovered) - baseline)
        if new_uncovered:
            sys.stderr.write(
                "HOOK-EVAL REGRESSION: новые wired-хуки без eval и без waiver:\n  - "
                + "\n  - ".join(new_uncovered)
                + "\n\nЛибо добавь фикстуру в scripts/test_hooks_smoke.py, либо waiver в "
                "EVAL_WAIVERS (с причиной ≥12 chars) в gen_hook_jtbd_registry.py.\n"
            )
            return 2
        print(f"hook-eval gate OK: 🔴={len(uncovered)} (все в baseline), новых регрессий нет")
        return 0
    md = _markdown(rows)
    if "--write" in argv:
        REGISTRY_MD.write_text(md, encoding="utf-8")
        print(f"wrote {REGISTRY_MD} ({len(rows)} hooks)")
        return 0
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
