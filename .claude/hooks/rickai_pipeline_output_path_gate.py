#!/usr/bin/env python3
"""rickai_pipeline_output_path_gate — PreToolUse Bash hook.

RCA 2026-05-28 (<layer>/<layer>/bronze lost to /tmp): a Rick.ai data-pipeline
(`4-rick-graphql-products-gold-extract` and any future skill pipeline under
`.agents/skills/*/scripts/`) was invoked with `--out /tmp/run-xyz`. The OS
garbage-collected /tmp → the canonical project folder lost its parquet →
`test_cross_check_structural.py` skipped silently (no reference parquet) →
tichaya regressiya (silent-fail class, same as RCA 2026-05-14 pipeline outage).

Per §Wiring-first gate (RCA 2026-05-25 v3): this is the ONE new mechanical
hook of a Path-B fix. The other layers WIRE existing infrastructure:
- `_lib.resolve_canonical_project_dir` + `assert_persistable_out_dir` (code guard)
- `0-rick-client-kb-save-gate` skill (40-span SSOT for client-folder writes)
- `run_all_phases.py --bead` default → canonical Standard 4.6 folder

What this hook adds: the CLI layer. The code guard only fires if the pipeline
calls it; a direct `python 4_emit_gold.py --out /tmp` bypasses the code. This
hook inspects the literal Bash command the agent/operator runs and BLOCKS when
a skill-pipeline script persists output under an ephemeral root.

Universal — no client/skill hardcode. Matches ANY python script under
`.agents/skills/*/scripts/*.py` with an `--out`/`--output`/`--out-dir`/`-o`
argument resolving under an ephemeral root.

Skips (legitimate ephemeral use):
- command contains `pytest` (unit tests use tmp_path by design)
- command contains `--allow-ephemeral` (explicit dev/test override)
- env RICKAI_PIPELINE_OUT_ACK set (>=12 chars) — documented exception

Exit codes:
  0 — pass / skip / ACK
  2 — BLOCK (ephemeral persist path detected)
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

ACK_ENV = "RICKAI_PIPELINE_OUT_ACK"
ACK_MIN_CHARS = 12

# A skill-pipeline script: .agents/skills/<name>/scripts/<file>.py
PIPELINE_SCRIPT_RE = re.compile(r"\.agents/skills/[^/\s]+/scripts/[^/\s]+\.py")
# --out / --output / --out-dir / -o  (space- or =-separated)
OUT_ARG_RE = re.compile(r"(?:--out|--output|--out-dir|--output-dir|-o)(?:[=\s]+)(\S+)")

# Raw ephemeral tokens caught without resolving (covers $TMPDIR, mktemp).
RAW_EPHEMERAL_RE = re.compile(
    r"^(/tmp/|/private/tmp/|/var/folders/|/private/var/folders/" r"|\$TMPDIR|\$\{TMPDIR\}|\$\(mktemp)"
)

_EPHEMERAL_ROOTS = tuple(
    {
        str(Path(p).resolve())
        for p in (
            "/tmp",
            "/private/tmp",
            "/var/folders",
            "/private/var/folders",
            tempfile.gettempdir(),
        )
    }
)


def _is_ephemeral(raw_value: str) -> bool:
    v = raw_value.strip().strip("'\"")
    if not v:
        return False
    if RAW_EPHEMERAL_RE.match(v):
        return True
    # Resolve and prefix-check (absolute or relative).
    try:
        resolved = str(Path(v).resolve())
    except (OSError, ValueError, RuntimeError):
        return False
    for root in _EPHEMERAL_ROOTS:
        if resolved == root or resolved.startswith(root + os.sep):
            return True
    return False


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0

    # ACK override
    ack = os.environ.get(ACK_ENV, "")
    if len(ack) >= ACK_MIN_CHARS:
        return 0

    # Skip test runs (tmp_path is the intended unit-test isolation) + explicit override
    if "pytest" in command or "--allow-ephemeral" in command:
        return 0

    # Only inspect commands that invoke a skill-pipeline script.
    if not PIPELINE_SCRIPT_RE.search(command):
        return 0

    # Find any --out value that points at an ephemeral root.
    offending = []
    for m in OUT_ARG_RE.finditer(command):
        val = m.group(1)
        if _is_ephemeral(val):
            offending.append(val.strip("'\""))

    if not offending:
        return 0

    sys.stderr.write(
        "rickai-pipeline-output-path-gate: BLOCK\n"
        "\n"
        "A Rick.ai skill-pipeline is about to persist <layer>/<layer>/gold under\n"
        "an EPHEMERAL root (the OS garbage-collects it → data lost → cross-check\n"
        "test skips silently). RCA 2026-05-28.\n"
        "\n"
        f"  offending --out value(s): {', '.join(offending)}\n"
        "\n"
        "Required: persist into the canonical project folder per Standard 4.6:\n"
        "  <internal-folder>/clients/all-clients/<client>/projects/<bead>/\n"
        "\n"
        "How to fix (pick one):\n"
        "  1. Omit --out and pass --bead — run_all_phases.py resolves the\n"
        "     canonical folder for you:\n"
        "       run_all_phases.py --client <c> --app-id <id> \\\n"
        "         --start <d> --end <d> --bead pr-rick-<slug>\n"
        "  2. Pass --out explicitly to the project folder:\n"
        '       --out "<internal-folder>/clients/all-clients/<client>/projects/<bead>/"\n'
        "\n"
        "Legitimate ephemeral use (dev/test only):\n"
        f'  add --allow-ephemeral  OR  export {ACK_ENV}="reason ... (>= {ACK_MIN_CHARS} chars)"\n'
        "\n"
        "Source: AGENTS.md §Always-green main + skill\n"
        "4-rick-graphql-products-gold-extract + 0-rick-client-kb-save-gate.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover — fail open
        sys.stderr.write(f"rickai-pipeline-output-path-gate: internal error: {exc}\n")
        sys.exit(0)
