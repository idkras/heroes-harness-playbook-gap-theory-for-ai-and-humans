"""Tests for verify_harness_wiring.py — the harness self-verifier.

Run: python3 -m pytest .agents/skills/0-governance-harness-portability/tests/ -q
Stdlib + pytest only (detachable: true).
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import verify_harness_wiring as v  # noqa: E402

# --- matcher_covers (registration matching core) ---


@pytest.mark.parametrize(
    "matcher,tool,expected",
    [
        ("Write|Edit|NotebookEdit", "Write", True),
        ("Write|Edit|NotebookEdit", "Bash", False),
        ("Bash", "Bash", True),
        ("", "Write", True),  # empty matcher = catch-all (UserPromptSubmit style)
        ("*", "Bash", True),
        ("Write|Edit", "*", True),  # requirement is catch-all
        ("Write | Edit ", "Edit", True),  # tolerant of spaces
    ],
)
def test_matcher_covers(matcher, tool, expected):
    assert v.matcher_covers(matcher, tool) is expected


# --- registration detection ---


def _settings(*triples):
    """Build a settings dict from (event, matcher, command) triples."""
    hooks: dict = {}
    for event, matcher, cmd in triples:
        hooks.setdefault(event, []).append({"matcher": matcher, "hooks": [{"type": "command", "command": cmd}]})
    return {"hooks": hooks}


def test_registered_satisfied():
    regs = v.collect_registrations(
        _settings(
            ("PreToolUse", "Write|Edit|NotebookEdit", "python3 .claude/hooks/docs_client_doc_gate.py"),
        )
    )
    ok, _ = v.hook_register_satisfied(regs, "docs_client_doc_gate.py", "PreToolUse", ["Write", "Edit"])
    assert ok is True


def test_registered_missing_is_gap():
    regs = v.collect_registrations(
        _settings(
            ("PreToolUse", "Bash", "python3 .claude/hooks/other.py"),
        )
    )
    ok, detail = v.hook_register_satisfied(regs, "docs_client_doc_gate.py", "PreToolUse", ["Write"])
    assert ok is False
    assert "not registered" in detail


def test_registered_substring_collision_is_gap():
    # RCA code-review M1: 'gate.py' must NOT be considered registered just because
    # 'branch_gate.py' (a suffix-superset) is in settings.json.
    regs = v.collect_registrations(
        _settings(
            ("PreToolUse", "Bash", "python3 .claude/hooks/branch_gate.py"),
        )
    )
    ok, detail = v.hook_register_satisfied(regs, "gate.py", "PreToolUse", ["Bash"])
    assert ok is False
    assert "not registered" in detail
    # and the real one IS detected
    ok2, _ = v.hook_register_satisfied(regs, "branch_gate.py", "PreToolUse", ["Bash"])
    assert ok2 is True


def test_registered_wrong_matcher_is_gap():
    # present under PreToolUse but only Bash matcher; requirement needs Write -> gap
    regs = v.collect_registrations(
        _settings(
            ("PreToolUse", "Bash", "python3 .claude/hooks/root_new_entry_gate.py"),
        )
    )
    ok, detail = v.hook_register_satisfied(regs, "root_new_entry_gate.py", "PreToolUse", ["Write"])
    assert ok is False
    assert "no matcher covers" in detail


# --- end-to-end verify() against a synthetic repo ---


def _write(p: Path, text: str = "x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _mini_manifest(tmp: Path, hook_registered: bool, dep_present: bool):
    _write(tmp / ".claude/hooks/gate.py", "import sys; sys.exit(0)")
    if dep_present:
        _write(tmp / "scripts/dep.py")
    # knowledge skill ok
    _write(tmp / ".agents/skills/k-skill/SKILL.md")
    # code skill missing tests -> should GAP on S2-tests
    _write(tmp / ".agents/skills/c-skill/skill.yaml", "detachable: true")
    _write(tmp / ".agents/skills/c-skill/scripts/x.py")
    _write(tmp / "scripts/aff.py")
    manifest = {
        "schema_version": 1,
        "name": "t",
        "standard": "0.3",
        "paths": {
            "hooks_dir": ".claude/hooks",
            "skills_dir": ".agents/skills",
            "settings": ".claude/settings.json",
            "settings_local": ".claude/settings.local.json",
        },
        "hooks": [
            {
                "file": "gate.py",
                "pillar": "A",
                "register": [{"event": "PreToolUse", "tools": ["Write"]}],
                "depends_on": ["scripts/dep.py"],
            }
        ],
        "skills": [
            {"name": "k-skill", "pillar": "A", "kind": "knowledge"},
            {"name": "c-skill", "pillar": "C", "kind": "code"},
        ],
        "scripts": [{"file": "scripts/aff.py", "role": "affordance"}],
    }
    mpath = tmp / "harness-manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    settings = (
        _settings(("PreToolUse", "Write|Edit", "python3 .claude/hooks/gate.py"))
        if hook_registered
        else _settings(("PreToolUse", "Bash", "python3 .claude/hooks/other.py"))
    )
    (tmp / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return mpath


def test_verify_all_green(tmp_path):
    mpath = _mini_manifest(tmp_path, hook_registered=True, dep_present=True)
    findings = v.verify(tmp_path, mpath, tmp_path / ".claude/settings.json", smoke=False)
    statuses = {(f.component, f.check): f.status for f in findings}
    assert statuses[("hook:gate.py", "H1-exists")] == v.PASS
    assert statuses[("hook:gate.py", "H2-registered[PreToolUse:Write]")] == v.PASS
    assert statuses[("hook:gate.py", "H3-dep")] == v.PASS
    # code skill missing tests/ is a real GAP the verifier must catch
    assert statuses[("skill:c-skill", "S2-tests")] == v.GAP


def test_verify_catches_dormant_hook(tmp_path):
    mpath = _mini_manifest(tmp_path, hook_registered=False, dep_present=True)
    findings = v.verify(tmp_path, mpath, tmp_path / ".claude/settings.json", smoke=False)
    g = [f for f in findings if f.component == "hook:gate.py" and f.check.startswith("H2")]
    assert g and g[0].status == v.GAP  # dormant hook detected


def test_verify_catches_missing_dep(tmp_path):
    mpath = _mini_manifest(tmp_path, hook_registered=True, dep_present=False)
    findings = v.verify(tmp_path, mpath, tmp_path / ".claude/settings.json", smoke=False)
    dep = [f for f in findings if f.check == "H3-dep"]
    assert dep and dep[0].status == v.GAP  # missing dep -> silent no-op risk caught


def test_main_exit_code_on_gap(tmp_path, capsys):
    mpath = _mini_manifest(tmp_path, hook_registered=False, dep_present=True)
    rc = v.main(
        ["--repo-root", str(tmp_path), "--manifest", str(mpath), "--settings", str(tmp_path / ".claude/settings.json")]
    )
    assert rc == 1  # gaps -> non-zero for CI gating
    out = capsys.readouterr().out
    assert "GAP" in out
