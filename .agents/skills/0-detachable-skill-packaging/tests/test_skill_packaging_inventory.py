#!/usr/bin/env python3
"""Tests for skill_packaging_inventory — bundled with the script (detachable).

Run: python3 -m pytest .agents/skills/0-detachable-skill-packaging/tests/ -q
Zero external deps beyond pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

# allow `import skill_packaging_inventory` when run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import skill_packaging_inventory as spi  # noqa: E402


def _classify(rel, **kw):
    base = dict(skill_refs={}, infra_refs=set(), import_counts={}, infra_subdirs=set(spi.DEFAULT_INFRA_SUBDIRS))
    base.update(kw)
    return spi.classify_script(rel, **base)


# --- category rules ------------------------------------------------------- #


def test_infra_by_subdir():
    c = _classify("scripts/setup/install_beads.sh")
    assert c.category == "infra"
    assert "setup" in c.referenced_by


def test_infra_by_wiring_reference():
    c = _classify("scripts/post_sync_bootstrap_guard.py", infra_refs={"scripts/post_sync_bootstrap_guard.py"})
    assert c.category == "infra"
    assert "keep at top-level" in c.recommended_action


def test_skill_owned_by_reference_points_to_owning_skill():
    c = _classify(
        "scripts/gap_effort_calculator.py",
        skill_refs={"gap_effort_calculator.py": ["2-so-what-outcome-ladder", "outcome-designer"]},
    )
    assert c.category == "skill-owned"
    assert c.owning_skill == "2-so-what-outcome-ladder"
    assert "move into" in c.recommended_action


def test_reference_backlog_does_not_become_owning_skill(tmp_path):
    root = tmp_path
    (root / "scripts").mkdir()
    (root / "scripts" / "loose_export.py").write_text("print(1)", encoding="utf-8")

    skill = root / ".agents" / "skills" / "0-detachable-skill-packaging"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Packaging\n", encoding="utf-8")
    (skill / "references" / "scripts-migration-backlog.md").write_text(
        "| script_path |\n|---|\n| `scripts/loose_export.py` |\n",
        encoding="utf-8",
    )

    cfg = spi.Config(repo_root=root, scripts_dir=root / "scripts")
    refs = spi.build_skill_ref_index(cfg)
    assert "loose_export.py" not in refs


def test_skill_owned_prefers_numbered_skill_slug_over_agent():
    # agent listed first, numbered skill slug must still win
    c = _classify(
        "scripts/ga4_setup_diagnostic.py",
        skill_refs={"ga4_setup_diagnostic.py": ["some-agent", "4-ga4-admin-diagnostic"]},
    )
    assert c.owning_skill == "4-ga4-admin-diagnostic"


def test_shared_lib_by_import_fanin():
    c = _classify("scripts/leverage_calc.py", import_counts={"leverage_calc": 3})
    assert c.category == "shared-lib"


def test_shared_lib_by_lib_subdir():
    c = _classify("scripts/lib/leverage_calc.py")
    assert c.category == "shared-lib"


def test_legacy_by_name_heuristic():
    for name in ("temp_explorer.py", "debug_workflow.py", "inspect_bronze.py"):
        c = _classify(f"scripts/{name}")
        assert c.category == "legacy-oneoff", name


def test_legacy_by_temp_subdir():
    c = _classify("scripts/temp/temp_screenshot.py")
    assert c.category == "legacy-oneoff"


def test_orphan_when_nothing_matches():
    c = _classify("scripts/mystery_writer.py")
    assert c.category == "orphan"
    assert "human triage" in c.recommended_action


def test_infra_reference_beats_skill_reference():
    # a script wired into Makefile AND cited by a skill stays infra (build safety)
    c = _classify(
        "scripts/branch_lifecycle_sweep.py",
        infra_refs={"scripts/branch_lifecycle_sweep.py"},
        skill_refs={"branch_lifecycle_sweep.py": ["5-git-parallel-coordination"]},
    )
    assert c.category == "infra"


def test_infra_reference_is_path_specific_not_basename_collision():
    c = _classify(
        "scripts/reasoning_log/query.py",
        infra_refs={"scripts/incidents/query.py"},
        skill_refs={"query.py": ["agent-reasoning-log"]},
    )
    assert c.category == "skill-owned"
    assert c.owning_skill == "agent-reasoning-log"


# --- aggregation ---------------------------------------------------------- #


def test_counts_by_category():
    results = [
        spi.Classification("a", "skill-owned"),
        spi.Classification("b", "skill-owned"),
        spi.Classification("c", "infra"),
    ]
    cc = spi.counts_by_category(results)
    assert cc == {"skill-owned": 2, "infra": 1}


def test_render_markdown_has_table_and_counts():
    results = [
        spi.Classification(
            "scripts/x.py", "skill-owned", owning_skill="2-foo", referenced_by="2-foo", recommended_action="move"
        )
    ]
    md = spi.render_markdown(results)
    assert "| script_path | category |" in md
    assert "scripts/x.py" in md
    assert "## Counts per category" in md
    assert "total**: 1" in md


# --- end-to-end on a synthetic tree -------------------------------------- #


def test_inventory_end_to_end(tmp_path):
    root = tmp_path
    (root / "scripts").mkdir()
    (root / "scripts" / "setup").mkdir()
    (root / "scripts" / "setup" / "boot.sh").write_text("echo hi", encoding="utf-8")
    (root / "scripts" / "debug_thing.py").write_text("print(1)", encoding="utf-8")
    (root / "scripts" / "mything.py").write_text("print(1)", encoding="utf-8")
    # a skill that cites mything.py
    skdir = root / ".agents" / "skills" / "4-my-skill"
    skdir.mkdir(parents=True)
    (skdir / "SKILL.md").write_text("uses `scripts/mything.py`", encoding="utf-8")

    cfg = spi.Config(repo_root=root, scripts_dir=root / "scripts")
    results = spi.inventory(cfg)
    by_path = {r.script_path: r for r in results}
    # normalize path separators
    paths = {Path(p).name: r for p, r in by_path.items()}
    assert paths["boot.sh"].category == "infra"
    assert paths["debug_thing.py"].category == "legacy-oneoff"
    assert paths["mything.py"].category == "skill-owned"
    assert paths["mything.py"].owning_skill == "4-my-skill"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
