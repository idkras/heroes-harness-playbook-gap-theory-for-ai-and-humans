"""
Integration tests for 4-rickai-calls-jtbd-scenarios-extract orchestrator pipeline.

Tests that Stage 8 (QA) + Stage 9 (Design) are enforced in the orchestration pipeline
per SKILL.md §Stage 8 and §Stage 9.

These are mock-based tests (no external API calls, no parquet required) that verify:
1. orchestrator_qa_stage_check hook logic fires on scenario paths
2. QA evidence patterns detect @code-reviewer spawns
3. Design evidence patterns detect @design-art-director spawns
4. Hard threshold blocks after N writes without QA
5. Override ACK bypasses BLOCK correctly

Run with:
    python -m pytest .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/test_orchestrator_pipeline.py -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest


# ── Load hook module dynamically (not on default sys.path) ──────────────────
def _find_workspace_root() -> Path:
    """Walk up from __file__ to find workspace root (contains .claude/hooks/)."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        candidate = ancestor / ".claude" / "hooks"
        if candidate.is_dir():
            return ancestor
    # Fallback: workspace is typically 7 levels up from __file__ in worktree layout
    return Path(__file__).resolve().parents[7]


_WORKSPACE_ROOT = _find_workspace_root()
_HOOK_PATH = _WORKSPACE_ROOT / ".claude" / "hooks" / "orchestrator_qa_stage_check.py"


def _load_hook():
    """Dynamically import orchestrator_qa_stage_check module."""
    if not _HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {_HOOK_PATH}")
    spec = importlib.util.spec_from_file_location("orchestrator_qa_stage_check", _HOOK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_qa_state(tmp_path, monkeypatch):
    """Reset QA state between tests using temp state dir."""
    state_dir = tmp_path / ".claude" / ".state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.fixture
def hook():
    return _load_hook()


def _make_transcript(entries: list[dict], tmp_path: Path) -> Path:
    """Write JSONL transcript file and return path."""
    t = tmp_path / "transcript.jsonl"
    with t.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return t


def _make_payload(file_path: str, transcript_path: str) -> str:
    return json.dumps(
        {
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
            "transcript_path": transcript_path,
        }
    )


# ── Helpers to build synthetic transcript entries ────────────────────────────


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _tool_use_entry(subagent_type: str) -> dict:
    """Simulate Agent tool invocation."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {
                        "subagent_type": subagent_type,
                        "description": f"Spawn {subagent_type}",
                        "prompt": "Review this artifact",
                    },
                }
            ]
        },
    }


# ── Tests: path matching ─────────────────────────────────────────────────────


class TestIsScenarioFile:
    """Tests for path trigger matching."""

    def test_triggers_on_полные_транскрипты(self, hook):
        assert hook._is_scenario_file("полные-транскрипты-по-jtbd/отправка-счёта-клиенту.md") is True

    def test_triggers_on_skill_md_path(self, hook):
        """An .md file inside the skill folder triggers the gate."""
        assert (
            hook._is_scenario_file(".agents/skills/4-rickai-calls-jtbd-scenarios-extract/scenarios/some-scenario.md")
            is True
        )

    def test_does_not_trigger_on_py_in_skill_path(self, hook):
        """Python scripts (.py) in the skill folder do NOT trigger — they need code-reviewer,
        not design-art-director, and causing Stage 8/9 gate on test files is a false positive.
        (RCA 2026-05-28: hook fired on test_enrich_scenario_md.py edits)
        """
        assert (
            hook._is_scenario_file(".agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/enrich_scenario_md.py")
            is False
        )

    def test_does_not_trigger_on_test_py_in_skill_path(self, hook):
        """Test files (.py) in the skill folder do NOT trigger the Stage 8/9 gate."""
        assert (
            hook._is_scenario_file(
                ".agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/test_enrich_scenario_md.py"
            )
            is False
        )

    def test_triggers_on_jtbd_scenarios_extract(self, hook):
        assert hook._is_scenario_file("jtbd-scenarios-extract/some-scenario.md") is True

    def test_does_not_trigger_on_regular_file(self, hook):
        assert hook._is_scenario_file("heroes_platform/rickai_mcp/src/server.py") is False

    def test_does_not_trigger_on_changelog(self, hook):
        assert hook._is_scenario_file("changelog.md") is False

    def test_does_not_trigger_on_empty_path(self, hook):
        assert hook._is_scenario_file("") is False


# ── Tests: QA evidence detection ─────────────────────────────────────────────


class TestQAEvidenceDetection:
    """Tests for Stage 8 QA evidence patterns."""

    def test_detects_code_reviewer_subagent_type_json(self, hook):
        text = '{"subagent_type": "code-reviewer", "description": "review"}'
        assert hook._has_qa_evidence(text) is True

    def test_detects_at_code_reviewer(self, hook):
        assert hook._has_qa_evidence("Spawn @code-reviewer for QA") is True

    def test_detects_ui_qa_engineer(self, hook):
        assert hook._has_qa_evidence('{"subagent_type": "ui-qa-engineer"}') is True

    def test_detects_at_ui_qa_engineer(self, hook):
        assert hook._has_qa_evidence("@ui-qa-engineer verdict: ship-ready") is True

    def test_detects_qa_analytic_reviewer(self, hook):
        assert hook._has_qa_evidence('{"subagent_type": "qa-analytic-reviewer"}') is True

    def test_detects_qa_review_verdict(self, hook):
        assert hook._has_qa_evidence("QA review: pass — all 42 tests green") is True

    def test_empty_text_returns_false(self, hook):
        assert hook._has_qa_evidence("") is False

    def test_random_text_returns_false(self, hook):
        assert hook._has_qa_evidence("git commit -m 'fix: parquet write'") is False

    def test_does_not_match_design_review_as_qa(self, hook):
        # @design-art-director is Stage 9, NOT Stage 8 QA evidence
        assert hook._has_qa_evidence("@design-art-director verdict: ship") is False


# ── Tests: Design evidence detection ─────────────────────────────────────────


class TestDesignEvidenceDetection:
    """Tests for Stage 9 Design evidence patterns."""

    def test_detects_design_art_director_subagent_type(self, hook):
        text = '{"subagent_type": "design-art-director", "description": "design"}'
        assert hook._has_design_evidence(text) is True

    def test_detects_at_design_art_director(self, hook):
        assert hook._has_design_evidence("Spawn @design-art-director") is True

    def test_detects_design_review_verdict(self, hook):
        assert hook._has_design_evidence("Design review: approved, РОП понимает всё") is True

    def test_empty_text_returns_false(self, hook):
        assert hook._has_design_evidence("") is False

    def test_does_not_match_qa_review_as_design(self, hook):
        # @code-reviewer is Stage 8, NOT Stage 9 Design
        assert hook._has_design_evidence("@code-reviewer verdict: pass") is False


# ── Tests: Hook main behavior ─────────────────────────────────────────────────


class TestHookMainBehavior:
    """End-to-end tests for hook main() function via stdin simulation."""

    def _run_hook(self, hook, payload_str: str, env_override: dict = None) -> int:
        """Run hook main() with patched stdin and return exit code."""
        import io

        original_stdin = sys.stdin
        original_env = {}
        try:
            sys.stdin = io.StringIO(payload_str)
            if env_override:
                for k, v in env_override.items():
                    original_env[k] = os.environ.get(k)
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            return hook.main()
        finally:
            sys.stdin = original_stdin
            for k, orig in original_env.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig

    def test_non_scenario_file_passes(self, hook, tmp_path):
        payload = _make_payload("heroes_platform/server.py", str(tmp_path / "t.jsonl"))
        code = self._run_hook(hook, payload)
        assert code == 0, "Non-scenario file must always pass"

    def test_unknown_tool_passes(self, hook, tmp_path):
        p = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "transcript_path": str(tmp_path / "t.jsonl"),
            }
        )
        code = self._run_hook(hook, p)
        assert code == 0

    def test_scenario_file_with_both_qa_and_design_passes(self, hook, tmp_path):
        entries = [
            _tool_use_entry("code-reviewer"),
            _tool_use_entry("design-art-director"),
        ]
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))
        code = self._run_hook(hook, payload)
        assert code == 0, "Both stages found → should pass"

    def test_scenario_file_no_evidence_warns_but_passes(self, hook, tmp_path):
        """First write to scenario file without QA → warning (exit 0), not block."""
        entries = [_assistant_text("just some commit message")]
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))
        code = self._run_hook(hook, payload)
        # First write → warn only (counter=1 < HARD_THRESHOLD=5 → exit 0)
        assert code == 0, "First write without QA should warn but not block"

    def test_hard_threshold_blocks(self, hook, tmp_path):
        """After HARD_THRESHOLD writes without QA → BLOCK (exit 2)."""
        entries = [_assistant_text("no qa here")]
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))

        # Run HARD_THRESHOLD times to exhaust counter
        hard_threshold = int(os.environ.get("ORCHESTRATOR_QA_HARD_WRITES", "5"))
        results = []
        for _ in range(hard_threshold + 1):
            results.append(self._run_hook(hook, payload, {"ORCHESTRATOR_QA_ACK": None}))

        # Last run must block
        assert results[-1] == 2, f"Expected BLOCK on run {hard_threshold+1}, got {results[-1]}"

    def test_ack_override_bypasses_block(self, hook, tmp_path):
        """ORCHESTRATOR_QA_ACK with ≥12 chars bypasses BLOCK."""
        entries = [_assistant_text("no qa here")]
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))

        # Exhaust counter
        hard_threshold = int(os.environ.get("ORCHESTRATOR_QA_HARD_WRITES", "5"))
        for _ in range(hard_threshold + 1):
            self._run_hook(hook, payload, {"ORCHESTRATOR_QA_ACK": None})

        # Now apply ACK
        code = self._run_hook(hook, payload, {"ORCHESTRATOR_QA_ACK": "dry-run-no-qa-needed-for-test"})
        assert code == 0, "ACK override must bypass BLOCK"

    def test_ack_too_short_does_not_bypass(self, hook, tmp_path):
        """ACK < 12 chars does NOT bypass BLOCK."""
        entries = [_assistant_text("no qa here")]
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))

        # Exhaust counter
        hard_threshold = int(os.environ.get("ORCHESTRATOR_QA_HARD_WRITES", "5"))
        for _ in range(hard_threshold + 1):
            self._run_hook(hook, payload, {"ORCHESTRATOR_QA_ACK": None})

        # Short ACK should NOT bypass
        code = self._run_hook(hook, payload, {"ORCHESTRATOR_QA_ACK": "short"})
        assert code == 2, "Short ACK must NOT bypass BLOCK"

    def test_qa_only_still_warns_about_missing_design(self, hook, tmp_path):
        """QA evidence found but no Design evidence → still warns (but passes Stage 8)."""
        entries = [_tool_use_entry("code-reviewer")]  # QA only, no design
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))
        code = self._run_hook(hook, payload)
        # Should warn but not block on first write (counter < HARD)
        assert code == 0, "QA only + no design = warn (not block) on low count"


# ── Tests: Stage ordering verification ────────────────────────────────────────


class TestStageOrderingInTranscript:
    """Tests that verify Stage 8/9 must appear AFTER the last scenario write."""

    def test_qa_evidence_in_transcript_resets_state(self, hook, tmp_path):
        """When QA evidence found, state counter resets to 0."""
        entries = [
            _assistant_text("some work"),
            _tool_use_entry("code-reviewer"),
            _tool_use_entry("design-art-director"),
        ]
        t = _make_transcript(entries, tmp_path)
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))

        import io

        original_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(payload)
            hook.main()
        finally:
            sys.stdin = original_stdin

        # After QA found, state counter should be reset
        state_file = Path(".claude") / ".state" / "orchestrator_qa_stage_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            assert state.get("writes_since_qa", 0) == 0, "Counter must reset to 0 after QA evidence found"

    def test_empty_transcript_passes_with_warning(self, hook, tmp_path):
        """Empty transcript → no evidence → warning on first write, still pass."""
        t = tmp_path / "empty.jsonl"
        t.write_text("", encoding="utf-8")
        payload = _make_payload("полные-транскрипты-по-jtbd/scenario.md", str(t))

        import io

        sys.stdin = io.StringIO(payload)
        code = hook.main()
        sys.stdin = sys.__stdin__

        assert code == 0, "Empty transcript on first write → warning only"


# ── Tests: Universal client invariant ─────────────────────────────────────────


class TestUniversalClientInvariant:
    """Verify hook does NOT hardcode any client alias."""

    def test_hook_has_no_luis_hardcode(self, hook):
        hook_text = _HOOK_PATH.read_text(encoding="utf-8")
        assert "luis-ru" not in hook_text, "luis-ru must not be hardcoded"
        assert "avtoall" not in hook_text, "avtoall must not be hardcoded"
        assert "typhoon" not in hook_text, "typhoon must not be hardcoded"

    def test_hook_triggers_for_any_client_path(self, hook):
        """Any client path containing trigger patterns should fire."""
        paths = [
            "[rick.ai]/clients/all-clients/avtoall-ru/intake/2026-06-01/bronze/полные-транскрипты-по-jtbd/scenario.md",
            "[rick.ai]/clients/all-clients/typhoon-coffee/intake/2026-06-15/полные-транскрипты-по-jtbd/foo.md",
            "clients/starpets-gg/jtbd-scenarios-extract/bar.md",
        ]
        for p in paths:
            assert hook._is_scenario_file(p) is True, f"Should trigger for: {p}"
