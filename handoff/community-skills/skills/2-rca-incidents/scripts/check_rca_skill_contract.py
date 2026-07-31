#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"

REQUIRED_MARKERS = [
    "### 0.1. Existing ticket first (ОБЯЗАТЕЛЬНО)",
    "### 0.2. Rewrite gate for bad existing ticket/card (ОБЯЗАТЕЛЬНО)",
    "1-ticket-review",
    "fenced `md` code block",
    "### 1. Зафиксировать инцидент",
    "### 2. RCA — 5 почему и корневая причина",
    "### 4.1. Post-change loop в `ai.incidents.md` (ОБЯЗАТЕЛЬНО после внесения изменений)",
    "### 7.0. Проверка после redo: сработала гипотеза или нет (ОБЯЗАТЕЛЬНО)",
    "Good-ticket proof:",
    "same-turn redo",
]


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    lines = text.count("\n") + 1
    errors = []
    warnings = []

    for marker in REQUIRED_MARKERS:
        if marker not in text:
            errors.append(f"missing marker: {marker}")

    if not REFERENCES.exists():
        errors.append("references/ directory is missing")

    if lines > 500:
        errors.append(f"SKILL.md is too long: {lines} lines (>500)")
    elif lines > 200:
        warnings.append(f"SKILL.md is above preferred fast-load target: {lines} lines (>200)")

    print("RCA skill contract check")
    print(f"- SKILL lines: {lines}")
    print(f"- references dir: {'present' if REFERENCES.exists() else 'missing'}")

    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("\nPASS: skill contract looks consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
