#!/usr/bin/env python3
"""Контракт-тест двух JTBD-скилов (bead rick-ej1).

Красная фаза: файлы SKILL.md ещё не существуют -> exit 1.
Зелёная фаза: оба скила проходят проверки Gate A -> exit 0.

Запуск: python3 .agents/skills/2-jtbd-scenarium-create/tests/test_skill_contract.py
"""

import re
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    "2-jtbd-scenarium-create": {
        "name": "jtbd-scenarium-create",
        "must_contain": [
            "Big JTBD", "Medium JTBD", "Small JTBD",
            "9 част", "N×7", "Фальсификация",
        ],
    },
    "2-jtbd-ticket-and-skill-writer": {
        "name": "jtbd-ticket-and-skill-writer",
        "must_contain": [
            "bd create", "Acceptance Criteria", "Когда {",
            "frontmatter", "Gate A", "Self-falsification gate",
        ],
    },
}

FRONT = re.compile(r"\A---\nname:\s*(?P<name>[a-z0-9-]+)\ndescription:\s*\"(?P<desc>.+?)\"\n---\n", re.S)


def check(skill_dir: str, spec: dict) -> list[str]:
    errors: list[str] = []
    path = SKILLS_ROOT / skill_dir / "SKILL.md"
    if not path.exists():
        return [f"{skill_dir}: SKILL.md не существует"]
    text = path.read_text(encoding="utf-8")

    m = FRONT.match(text)
    if not m:
        return [f"{skill_dir}: frontmatter не парсится (name + description в кавычках)"]
    if m["name"] != spec["name"]:
        errors.append(f"{skill_dir}: name `{m['name']}` != каталог-найм `{spec['name']}`")
    desc = m["desc"]
    if len(desc) > 1024:
        errors.append(f"{skill_dir}: description {len(desc)} > 1024 символов")
    if not desc.startswith("Use when"):
        errors.append(f"{skill_dir}: description не начинается с `Use when` (WHEN, не WHAT)")
    triggers = desc.count("«")
    if triggers < 5:
        errors.append(f"{skill_dir}: триггер-фраз {triggers} < 5")
    if "NOT for" not in desc:
        errors.append(f"{skill_dir}: нет exclusion-блока `NOT for:`")
    for token in spec["must_contain"]:
        if token not in text:
            errors.append(f"{skill_dir}: в теле нет обязательного блока `{token}`")
    if "Hired for JTBD" not in text:
        errors.append(f"{skill_dir}: нет секции `Hired for JTBD`")
    return errors


def main() -> int:
    all_errors: list[str] = []
    for skill_dir, spec in TARGETS.items():
        all_errors.extend(check(skill_dir, spec))
    if all_errors:
        print("FAIL:")
        for e in all_errors:
            print(" -", e)
        return 1
    print("OK: 2 skills pass contract (frontmatter, Use when, триггеры, NOT-for, длина <=1024)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
