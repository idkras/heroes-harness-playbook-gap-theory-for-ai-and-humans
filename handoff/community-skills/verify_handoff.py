#!/usr/bin/env python3
"""Verify the Gap Theory community skill handoff."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

REQUIRED_PATHS = [
    "README.md",
    "manifest.json",
    "requirements.txt",
    "docs/hooks-chat-result.md",
    "skills/2-rca-incidents/SKILL.md",
    "skills/2-rca-incidents/scripts/check_rca_skill_contract.py",
    "skills/2-rca-incidents/scripts/incidents_to_gepa_trainset.py",
    "skills/2-rca-incidents/references/bad-ticket-anti-patterns.md",
    "skills/0-hook-self-test/SKILL.md",
    "skills/0-hooks-minimum-sufficiency/SKILL.md",
    "skills/0-portable-claude-hooks/SKILL.md",
    "skills/visual-explainer/SKILL.md",
    "skills/visual-explainer/commands/generate-web-diagram.md",
    "skills/visual-explainer/commands/generate-slides.md",
    "skills/visual-explainer/references/css-patterns.md",
    "skills/visual-explainer/references/libraries.md",
    "skills/visual-explainer/templates/architecture.html",
    "skills/visual-explainer/templates/mermaid-flowchart.html",
    "skills/visual-explainer/scripts/share.sh",
    "skills/4-conversation-normalize/SKILL.md",
    "skills/4-conversation-action-chain-extract/SKILL.md",
    "skills/2-jtbd-scenarium-create/SKILL.md",
    "skills/2-jtbd-scenarium-create/tests/test_skill_contract.py",
    "skills/4-rickai-calls-jtbd-scenarios-extract/SKILL.md",
    "skills/4-rickai-calls-jtbd-scenarios-extract/scripts/add_call_cards_to_jtbd_scenario.py",
    "skills/4-rickai-calls-jtbd-scenarios-extract/scripts/enrich_scenario_md.py",
    "skills/4-rickai-calls-jtbd-scenarios-extract/scripts/render_sanitized_call_corpus.py",
]


def main() -> int:
    errors: list[str] = []

    manifest_path = ROOT / "manifest.json"
    if manifest_path.exists():
        try:
            json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"manifest.json invalid: {exc}")

    requirements_path = ROOT / "requirements.txt"
    if requirements_path.exists():
        requirements = requirements_path.read_text(encoding="utf-8")
        for package in ("pandas", "pyarrow", "pymorphy3", "pytest"):
            if package not in requirements:
                errors.append(f"requirements.txt missing: {package}")

    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"missing: {rel}")

    noisy = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.name in {".DS_Store"} or "__pycache__" in path.parts or path.suffix == ".pyc"
    ]
    if noisy:
        errors.append("noise files present: " + ", ".join(noisy[:20]))

    if errors:
        print("COMMUNITY_SKILL_HANDOFF_VERIFY_FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"COMMUNITY_SKILL_HANDOFF_VERIFY_PASS required_paths={len(REQUIRED_PATHS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
