#!/usr/bin/env python3
"""PreToolUse gate: reusable-скрипт должен жить В СКИЛЕ, не валяться в client-папке.

owner 2026-06-03: «я просил создавать скил отчуждаемый со скриптами … какие хуки настроить
чтобы скрипты не валялись на диске, а скрипты и тесты были внутри скилов?»

Корень: агент пишет переиспользуемый .py (reader/poster/validator) в
`<internal-folder>/clients/.../scripts/` ВМЕСТО `.agents/skills/{skill}/scripts/`. Скил перестаёт
быть отчуждаемым (self-contained: скопировал папку скила → работает). Дубли (тот же скрипт
в скиле И в client) = drift + «валяется на диске».

BLOCK (exit 2) при Write/Edit `.py`/`.sh` в client `scripts/` если:
  (D) DUPLICATE: basename совпадает с существующим `.agents/skills/*/scripts/<same>` —
      редактируй skill-версию, не форкай в client.
  (R) NEW REUSABLE: новый файл (не существует), содержит `def main(`/`argparse`/
      `if __name__` И нет client-hardcode-маркера → создай/расширь скил.

PASS:
  - путь НЕ в client `scripts/` (skill scripts / <internal-component> / прочее — ок);
  - файл уже существует и НЕ дубль скила (правка существующего client-скрипта ок);
  - тонкий data/config/mapping/schema файл (нет main/argparse);
  - thin-wrapper (≤ THIN_LINES строк, импортирует из скила).

Override: SCRIPT_IN_CLIENT_ACK="<причина ≥12 симв.>" (client-специфичный скрипт обоснован).
Staged WARN: REUSABLE_SCRIPT_GATE_PHASE1_WARN=1.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

ACK = os.environ.get("SCRIPT_IN_CLIENT_ACK", "")
PHASE1 = os.environ.get("REUSABLE_SCRIPT_GATE_PHASE1_WARN", "") == "1"
THIN_LINES = 25

CLIENT_SCRIPTS_RE = re.compile(r"\[rick\.ai\]/clients/.+/scripts/")
REUSABLE = re.compile(r"(^|\n)\s*(def main\(|import argparse|if __name__\s*==)")
# client-specific обоснование (если есть — это НЕ generic reusable, оставляем)
CLIENT_HARDCODE = re.compile(
    r"(luis_extractor|client_alias\s*=|MAPPING|mapping\.yaml|" r"company_inn|vector_spec_id|# client-specific)"
)


def _workspace_root(file_path: str) -> Path | None:
    p = Path(file_path).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".agents" / "skills").is_dir():
            return parent
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input", {})
    fp = ti.get("file_path", "")
    if not fp or not CLIENT_SCRIPTS_RE.search(fp):
        return 0
    if not (fp.endswith(".py") or fp.endswith(".sh")):
        return 0
    bn = os.path.basename(fp)
    if bn in ("__init__.py",) or bn.startswith("test_"):
        # тесты тоже в скил, но __init__/тривиальное — пропускаем
        if bn == "__init__.py":
            return 0

    root = _workspace_root(fp)
    content = ti.get("content") or ti.get("new_string") or ""
    file_exists = os.path.exists(fp)

    # (D) DUPLICATE: тот же basename есть в каком-то скиле
    skill_dupe = None
    if root:
        for cand in glob.glob(str(root / ".agents" / "skills" / "*" / "scripts" / bn)):
            skill_dupe = cand
            break
    if skill_dupe:
        msg = (
            f"reusable-script-gate: BLOCK — `{bn}` ДУБЛИРУЕТ skill-скрипт.\n"
            f"  skill (канон): {os.path.relpath(skill_dupe, str(root)) if root else skill_dupe}\n"
            f"  client (дубль): {fp}\n"
            f"Не форкай скрипт в client-папку — скил отчуждаемый, его и правь. "
            f"Если client нужно запустить — зови skill-путь напрямую ИЛИ symlink.\n"
            f"Override: SCRIPT_IN_CLIENT_ACK=<причина ≥12 симв.>"
        )
        if ACK and len(ACK) >= 12 or PHASE1:
            print(msg + "\n(WARN/ACK — пропускаю)", file=sys.stderr)
            return 0
        print(msg, file=sys.stderr)
        return 2

    # (R) NEW REUSABLE: новый файл, выглядит переиспользуемым, без client-hardcode
    if not file_exists and REUSABLE.search(content) and not CLIENT_HARDCODE.search(content):
        if len(content.splitlines()) <= THIN_LINES:
            return 0  # thin-wrapper ок
        msg = (
            f"reusable-script-gate: BLOCK — новый reusable-скрипт `{bn}` в client-папке.\n"
            f"  {fp}\n"
            f"Переиспользуемый код (main/argparse) → `.agents/skills/{{skill}}/scripts/` + tests/, "
            f"чтобы скил был отчуждаемым (copy folder → works). Создай/расширь скил "
            f"(0-align-skill-name-and-trigger-to-jtbd / 0-skills-self-improvement).\n"
            f"Override: SCRIPT_IN_CLIENT_ACK=<причина ≥12 симв., если реально client-специфичный>"
        )
        if ACK and len(ACK) >= 12 or PHASE1:
            print(msg + "\n(WARN/ACK — пропускаю)", file=sys.stderr)
            return 0
        print(msg, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
