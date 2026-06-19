#!/usr/bin/env python3
r"""Untracked critical files gate — Claude Code PreToolUse hook (RCA 2026-05-15).

Closes RCA 15 May 2026 «Uncommitted enrichment pipeline code lost on branch switch»
(~1000+ LOC потеряны: amocrm_enrichment_pipeline.py + customer_360_writer.py +
18 contract tests + build_customer_360_cards.py + project-progress-auditor.md +
2 SKILL.md — все на одну branch switch без incremental commits).

Root cause (RCA 2026-05-15):
- AGENTS.md §Incremental commits mandatory декларативный, не mechanical.
- @auto/ralph/orchestrator имеют commit-before-switch правило только judgment-based.
- При 6+ часах Ralph loop без commit → одна `git checkout <other-branch>` уничтожает working tree.

Behavior (PreToolUse event для Bash):
- Reads stdin JSON payload from Claude Code PreToolUse event.
- Extracts tool_name = "Bash" + tool_input.command.
- If command matches risky branch-switching pattern (regex below) — scans repo для:
  (a) untracked .py файлов >100 LOC в critical dirs, mtime старше N минут (default 120 = 2h)
  (b) untracked .md файлов >100 LOC в .agents/skills/ или .agents/agents/, mtime старше N min
- If таких файлов ≥1 — BLOCK (exit 2): message указывает agent на необходимость
  `git add` + `git commit` ДО branch switch.

Critical dirs (universal, не client-specific):
- <internal-module>/**/workflows/
- <internal-module>/**/tests/
- .agents/skills/**/
- .agents/agents/
- <internal-folder>/clients/all-clients/<any>/projects/<any>/

Risky git patterns blocked (branch-switching = working tree replaced):
- `git checkout <branch>` (not `git checkout <file>` — anchored by context)
- `git switch <branch>` and `git switch -c`
- `git rebase` / `git rebase -i`
- `git pull --rebase`
- `git worktree add` (carries dirty state to new worktree)
- `git reset --hard`

Override: `UNTRACKED_CRITICAL_ACK=<reason>` env var (12+ chars with letters + separator).

Universal — no client hardcodes. Works for any workspace using git + matches by
filesystem patterns, not registry. Threshold configurable via env:
- UNTRACKED_CRITICAL_MIN_LOC (default 100)
- UNTRACKED_CRITICAL_MIN_AGE_MIN (default 120 = 2h)

Exit codes:
  0 = pass (no critical untracked files OR rule not applicable OR override acked)
  2 = block (≥1 critical untracked file >threshold age) — message to stderr
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Defaults configurable via env
MIN_LOC = int(os.environ.get("UNTRACKED_CRITICAL_MIN_LOC", "100"))
MIN_AGE_MINUTES = int(os.environ.get("UNTRACKED_CRITICAL_MIN_AGE_MIN", "120"))
OVERRIDE_ENV_VAR = "UNTRACKED_CRITICAL_ACK"

# Risky branch-switching git ops. Same logic as git_dirty_count_gate but targeted
# at the SPECIFIC subset that REPLACES working tree (not just modifies).
RISKY_GIT_PATTERNS = [
    # Branch switch (named branch arg, not file arg)
    re.compile(r"\bgit\s+checkout\s+(?!--|\.|-b\b)[A-Za-z0-9_/-]+"),
    re.compile(r"\bgit\s+switch\s+(?!-c\b)[A-Za-z0-9_/-]+"),
    re.compile(r"\bgit\s+switch\s+-c\b"),
    # Rebase replaces commits/working tree
    re.compile(r"\bgit\s+rebase\b"),
    re.compile(r"\bgit\s+pull\s+(?:[^|;&]*\s+)?--rebase\b"),
    re.compile(r"\bgit\s+pull\s+--rebase\b"),
    # Worktree add carries dirty state
    re.compile(r"\bgit\s+worktree\s+add\b"),
    # Reset --hard destroys uncommitted work
    re.compile(r"\bgit\s+reset\s+--hard\b"),
]

# Filter false-positives — text-emitting commands
TEXT_EMIT_PREFIXES = re.compile(r"^\s*(?:echo\b|printf\b|cat\s+(?:>>?|<<<?|<)|#|//|export\s+[A-Z_]+=)")
QUOTED_SPAN = re.compile(r"""(?:'[^']*'|"[^"]*"|`[^`]*`)""")
HEREDOC_START = re.compile(r"<<-?\s*[\"']?(?P<delim>[A-Za-z_][A-Za-z0-9_]*)[\"']?")

# Critical dir patterns — universal, glob-like
# Matched against repo-relative path of untracked file
CRITICAL_DIR_PATTERNS = [
    # Python workflows + tests (any product under <internal-module>/)
    re.compile(r"^<internal-module>/[^/]+/workflows/.*\.py$"),
    re.compile(r"^<internal-module>/[^/]+/tests/.*\.py$"),
    # Agent/skill files (any depth under .agents/)
    re.compile(r"^\.agents/skills/.+\.md$"),
    re.compile(r"^\.agents/agents/.+\.md$"),
    # Client project artifacts (rick.ai canonical structure)
    re.compile(r"^\[rick\.ai\]/clients/all-clients/[^/]+/projects/[^/]+/.*\.(py|md)$"),
]

# Zero-threshold critical patterns (RCA 2026-06-17 branch-substitution loss).
# Client deliverables under projects/ are git-TRACKED; a parallel session's
# `git checkout`/`reset` to another branch wipes them from the working tree.
# They slipped the LOC+age thresholds above (fresh <100-LOC *.md). A 20-line
# client analysis is as valuable as a 200-LOC script → ANY untracked file here
# blocks a branch-switch regardless of size/age. The gate scans the SHARED
# working tree, so the *switching* session blocks even if another session
# authored the files — closing the cross-session vector.
ZERO_THRESHOLD_PATTERNS = [
    re.compile(r"^\[rick\.ai\]/clients/all-clients/[^/]+/projects/[^/]+/.*\.(py|md|csv|json|yaml)$"),
]

OVERRIDE_VALID = re.compile(r"^(?=.{12,})(?=.*[A-Za-z]{3,}).+[\s\-_:]+.+$")


def is_text_emit(command: str) -> bool:
    return bool(TEXT_EMIT_PREFIXES.match(command))


def has_risky_git_op_outside_quotes(command: str) -> bool:
    """Strip quoted spans and heredoc bodies; check if any RISKY pattern matches."""
    cleaned = command
    heredoc_match = HEREDOC_START.search(cleaned)
    if heredoc_match:
        delim = heredoc_match.group("delim")
        end_pat = re.compile(rf"^\s*{re.escape(delim)}\s*$", re.MULTILINE)
        end_match = end_pat.search(cleaned, heredoc_match.end())
        if end_match:
            cleaned = cleaned[: heredoc_match.start()] + cleaned[end_match.end() :]
        else:
            cleaned = cleaned[: heredoc_match.start()]
    cleaned = QUOTED_SPAN.sub(" ", cleaned)
    return any(pat.search(cleaned) for pat in RISKY_GIT_PATTERNS)


def find_repo_root(start: Path | None = None) -> Path | None:
    cwd = (start or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def list_untracked(repo_root: Path) -> list[str]:
    """Return list of untracked repo-relative paths."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def is_critical(rel_path: str) -> bool:
    return any(pat.match(rel_path) for pat in CRITICAL_DIR_PATTERNS)


def file_meets_thresholds(abs_path: Path, min_loc: int, min_age_min: int) -> bool:
    """Return True if file ≥ min_loc lines AND mtime older than min_age_min."""
    try:
        if not abs_path.is_file():
            return False
        stat = abs_path.stat()
        age_min = (time.time() - stat.st_mtime) / 60.0
        if age_min < min_age_min:
            return False
        # Count lines without loading whole file
        with abs_path.open("rb") as f:
            loc = sum(1 for _ in f)
        return loc >= min_loc
    except Exception:
        return False


def find_critical_untracked(repo_root: Path) -> list[tuple[str, int, float]]:
    """Return list of (rel_path, loc, age_minutes) for critical untracked files
    that meet both thresholds."""
    out: list[tuple[str, int, float]] = []
    for rel in list_untracked(repo_root):
        abs_path = repo_root / rel
        if not abs_path.is_file():
            continue
        zero_threshold = any(p.match(rel) for p in ZERO_THRESHOLD_PATTERNS)
        if not zero_threshold:
            if not is_critical(rel):
                continue
            if not file_meets_thresholds(abs_path, MIN_LOC, MIN_AGE_MINUTES):
                continue
        try:
            stat = abs_path.stat()
            with abs_path.open("rb") as f:
                loc = sum(1 for _ in f)
            age_min = (time.time() - stat.st_mtime) / 60.0
            out.append((rel, loc, age_min))
        except Exception:
            continue
    return out


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_name = payload.get("tool_name", "")
    if tool_name != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip() or is_text_emit(command):
        return 0
    if not has_risky_git_op_outside_quotes(command):
        return 0

    # Check override
    override = os.environ.get(OVERRIDE_ENV_VAR, "").strip()
    if override and OVERRIDE_VALID.match(override):
        print(
            f"[untracked-critical-files-gate] OVERRIDE acked: {override} — bypassing",
            file=sys.stderr,
        )
        return 0

    repo_root = find_repo_root()
    if repo_root is None:
        return 0

    critical = find_critical_untracked(repo_root)
    if not critical:
        return 0

    # BLOCK
    lines = [
        "untracked-critical-files-gate: BLOCK — обнаружены untracked critical .py/.md файлы > {} LOC старше {} мин в critical dirs:".format(
            MIN_LOC, MIN_AGE_MINUTES
        ),
        "",
    ]
    for rel, loc, age_min in sorted(critical, key=lambda x: -x[1]):
        lines.append(f"  · {rel} ({loc} LOC, age {age_min:.0f} min)")
    lines += [
        "",
        "Branch switch / rebase / reset --hard поверх этих файлов = потеря работы (RCA 15 May 2026).",
        "",
        "Recovery: выполни `git add` + `git commit` для перечисленных файлов ДО risky операции,",
        "ИЛИ установи `UNTRACKED_CRITICAL_ACK=<reason>` (12+ chars с letters + separator)",
        "если carry-over намеренный (например stash без сохранения).",
        "",
        "Источник правила: AGENTS.md §Always-green main invariant + §Commit-before-branch-switch invariant.",
        "RCA: <internal-folder>/ai.incidents.md § «15 May 2026 — Uncommitted enrichment pipeline code lost on branch switch».",
    ]
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
