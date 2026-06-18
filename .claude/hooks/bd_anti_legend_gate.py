#!/usr/bin/env python3
"""bd_anti_legend_gate — PreToolUse Bash hook (pr-rick-camh).

Owner 2026-06-13: «доработай хуки, чтобы в beads не было С1 H1/H4 — протокол
антилегенда». Перехватывает `bd create` / `bd update` / `bd q` ДО исполнения,
парсит title + description из команды, прогоняет через единый SSOT-детектор
`scripts/bd_anti_legend.py` и БЛОКИРУЕТ (exit 2), если в title/подзадачах есть
голые «легенда»-коды (`(C1+H1+H4+H2)`, `C1`, `(H1/H4)`, `(H2)`, `(M6)`).

Это слой, который ДОЕЗЖАЕТ ДО ПАРТНЁРОВ: hook зарегистрирован в
harness-manifest.json hooks[] с depends_on scripts/bd_anti_legend.py →
mirror_harness_to_target.py копирует и хук, и детектор в <client> /
partner-advisers-* (lefthook.yml партнёрам НЕ зеркалится, поэтому git-backstop
`check_bd_anti_legend.py` — только canonical).

§Wiring-first: новый фреймворк НЕ создаётся — детектор общий с lefthook-слоем,
парсинг команды по образцу существующего bd_create_dup_check.py.

Override: BD_ANTI_LEGEND_ACK="<reason ≥12 chars>" — для редкого легитимного
случая (код в pasted-команде, не в beads-контенте).
Staged-rollback: BD_ANTI_LEGEND_PHASE1_WARN=1 — WARN вместо BLOCK.

Exit codes:
  0 — N/A (не bd create/update, нет title/desc) | PASS | ACK | WARN | любая
      внутренняя ошибка (fail-open — хук не должен ломать turn)
  2 — BLOCK: ≥1 голый код легенды в title/подзадачах.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

ACK_ENV = "BD_ANTI_LEGEND_ACK"
ACK_MIN_CHARS = 12
PHASE1_WARN_ENV = "BD_ANTI_LEGEND_PHASE1_WARN"

_BD_VERB_RE = re.compile(r"\bbd\s+(?:create|update|q)\b")
_VERBS = ("create", "update", "q")


def _repo_root() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if env_root and Path(env_root).is_dir():
        return Path(env_root)
    return Path(__file__).resolve().parents[2]


def _read_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def extract_title_desc(command: str) -> tuple[str | None, str | None]:
    """Достать title + description из `bd create/update/q` команды.

    Поддерживает `--title=X`, `--title X`, `--description=X`, `-d X`,
    позиционный title для `bd create "title"` / `bd q "title"`."""
    if not command or not _BD_VERB_RE.search(command):
        return None, None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None, None
    title: str | None = None
    desc: str | None = None
    positional: str | None = None
    verb: str | None = None
    seen_verb = False
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t == "bd" and i + 1 < n and tokens[i + 1] in _VERBS:
            verb = tokens[i + 1]
            seen_verb = True
            i += 2
            continue
        if t.startswith("--title="):
            title = t[len("--title=") :]
        elif t == "--title" and i + 1 < n:
            title = tokens[i + 1]
            i += 1
        elif t.startswith("--description="):
            desc = t[len("--description=") :]
        elif t in ("--description", "-d") and i + 1 < n:
            desc = tokens[i + 1]
            i += 1
        elif (
            seen_verb
            and verb in ("create", "q")
            and not t.startswith("-")
            and positional is None
            and t not in _VERBS
        ):
            positional = t
        i += 1
    if title is None and positional and verb in ("create", "q"):
        title = positional
    return title, desc


def main() -> int:
    ack = os.environ.get(ACK_ENV, "")
    if len(ack.strip()) >= ACK_MIN_CHARS:
        return 0

    payload = _read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command:
        return 0

    title, desc = extract_title_desc(command)
    if not title and not desc:
        return 0

    scripts_dir = _repo_root() / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        import bd_anti_legend  # type: ignore
    except Exception:
        return 0  # детектор недоступен → fail-open

    violations = bd_anti_legend.scan_bead(title or "", desc or "")
    if not violations:
        return 0

    report = bd_anti_legend.format_report("", violations)
    warn_only = os.environ.get(PHASE1_WARN_ENV) == "1"
    header = "WARN: bare legend codes in bead" if warn_only else "BARE LEGEND CODES IN BEAD"
    msg = (
        f"\n[bd-anti-legend] {header} (§Anti-legend, pr-rick-camh)\n"
        f"{report}\n\n"
        f"{bd_anti_legend.REMEDIATION}\n"
        f'  Override (код в команде, не в beads): {ACK_ENV}="<reason ≥{ACK_MIN_CHARS} chars>"\n'
        f"  Staged rollback to WARN: {PHASE1_WARN_ENV}=1\n"
    )
    sys.stderr.write(msg)
    return 0 if warn_only else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover — никогда не ломаем turn
        sys.stderr.write(f"bd_anti_legend_gate: internal error: {exc}\n")
        sys.exit(0)
