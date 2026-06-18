#!/usr/bin/env python3
"""first_substantial_write_branch_bead_gate — PreToolUse Write|Edit hook.

RCA 2026-05-28 (10th recurrence of design-injection-without-mechanical-hook
class, owner direct steering: «опять грязное дерево, найди чаты все кто
не работает в своих ветках, почему они создают ветки и тикеты в beads
после ревью моего или откладывают это решение, а не сразу как только чат
начался»).

This hook closes the gap left by 8 existing branch/git hooks: ALL of them
fire on git ops (`commit`, `push`, `checkout -b`, `merge`), NONE fire on
the first substantial Write/Edit when an agent inherits HEAD from a prior
session without creating own branch + bd-ticket.

Per §Wiring-first gate (RCA 2026-05-25 v3): wires existing infrastructure
- `.agents/memory/runtime/branch-ownership-ledger.jsonl` (SSOT for
  branch_ownership_gate.py)
- bd/Dolt live state via `bd list --json` (with `.beads/issues.jsonl` export fallback)
- session_isolation_guard.py SessionStart warning (advisory)

What this hook adds: FIRST substantial Write/Edit/MultiEdit trigger ←
which existing hooks miss.

Conditions for WARN (all must hold):
1. tool_input.file_path is on critical path (not narrative)
2. CWD is the SHARED root tree (not .claude/worktrees/*, not /tmp/wt-*)
3. Current HEAD branch is NOT main/master/production/release
4. No own active claim for $CLAUDE_SESSION_ID in branch-ownership-ledger
5. No bd-ticket in-progress assigned @me whose slug matches HEAD branch

Phase 2 (RCA 2026-05-28 escalation): BLOCK (exit 2). Owner steering repeated
4+ sessions «почему новая сессия сразу не создаёт ветку + bead + todo» →
Phase 1 WARN was ignorable → escalated to BLOCK. Staged-rollback to WARN via
`BRANCH_BEAD_GATE_PHASE1_WARN=1` env. Also surfaces {projectname}.todo.md gap.

Universal — no client/project hardcode. Override:
`OWN_BRANCH_BEAD_ACK=<reason ≥12 chars>` env.

Exit codes:
  0 — pass / WARN-only / ACK present
  2 — Phase 2 BLOCK (future, currently unused)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ACK_ENV = "OWN_BRANCH_BEAD_ACK"
ACK_MIN_CHARS = 12
# File-based ACK sentinel — Cowork-compatible override.
# RCA 2026-06-02: env ACK (OWN_BRANCH_BEAD_ACK) does NOT reach this PreToolUse
# hook in Cowork — the hook runs in Claude Code's own process env, not as a
# child of the Bash/Write command, so an inline `OWN_BRANCH_BEAD_ACK=...`
# prefix never propagates. This file sentinel is the working escape hatch.
FILE_ACK_REL = ".claude/.state/branch_bead_gate_ack"
FILE_ACK_MAX_AGE_MIN = 360  # 6h validity window

# Narrative paths — agents legitimately write here without branch/bead
NARRATIVE_PATTERNS = [
    r"\[todo\s+·?\s+incidents\]/ai\.(incidents|legacy|todo)\.md$",
    r"changelog\.md$",
    r"\.reasoning-log/",
    r"\.agents/memory/runtime/",
    r"\.claude/\.state/",
    r"^/tmp/",
    r"/tmp/[^/]+\.(md|txt|json|log)$",
    # CHANGELOG fragments + RCA fragments
    r"changes\.d/",
    r"incidents\.d/",
    r"legacy\.d/",
]
NARRATIVE_RE = re.compile("|".join(NARRATIVE_PATTERNS), re.IGNORECASE)

# Critical-path heuristics — substantial work usually touches these
CRITICAL_PATH_PATTERNS = [
    r"^<internal-module>/",
    r"^\.agents/skills/[^/]+/(SKILL\.md|scripts/|references/|templates/|tests/)",
    r"^\.agents/agents/[^/]+\.md$",
    r"^\.claude/hooks/[^/]+\.py$",
    r"^\[standards\s+\.md\]/",
    r"^\[rick\.ai\]/clients/all-clients/[^/]+/projects/",
    r"^scripts/",
    r"^tests/",
    r"^Makefile$",
    r"^AGENTS\.md$",
]
CRITICAL_RE = re.compile("|".join(CRITICAL_PATH_PATTERNS))


def _run(cmd: list[str], cwd: str | None = None) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8, cwd=cwd, check=False)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _run_rc(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8, cwd=cwd, check=False)
        return r.returncode, (r.stdout or "").strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        return 1, str(e)


def _is_narrative(file_path: str) -> bool:
    return bool(NARRATIVE_RE.search(file_path))


def _is_critical(file_path: str) -> bool:
    # Normalize: strip absolute path prefix to make patterns match
    rel = file_path
    repo_root_match = re.search(r"heroes-rickai-workspace/(.*)$", file_path)
    if repo_root_match:
        rel = repo_root_match.group(1)
    return bool(CRITICAL_RE.search(rel))


def _is_in_own_worktree(cwd: str) -> bool:
    """Detect if CWD is in a session-isolated worktree."""
    if ".claude/worktrees/" in cwd:
        return True
    if "/tmp/wt-" in cwd or cwd.startswith("/tmp/wt-"):
        return True
    if "/private/tmp/wt-" in cwd:
        return True
    # Compare git-dir vs git-common-dir — if different, this is a worktree
    git_dir = _run(["git", "rev-parse", "--git-dir"], cwd=cwd)
    common_dir = _run(["git", "rev-parse", "--git-common-dir"], cwd=cwd)
    if git_dir and common_dir and git_dir != common_dir:
        return True
    return False


def _has_file_ack(repo_root: str) -> bool:
    """File-based override — the Cowork-compatible escape hatch.

    Env ACK can't reach this hook (RCA 2026-06-02). Presence of
    .claude/.state/branch_bead_gate_ack with mtime within FILE_ACK_MAX_AGE_MIN
    = ack. Create via:
      mkdir -p .claude/.state
      echo "reason: <why> <bd-id>" > .claude/.state/branch_bead_gate_ack
    """
    if os.environ.get("BRANCH_BEAD_GATE_IGNORE_FILE_ACK") == "1":
        return False
    ack = Path(repo_root) / FILE_ACK_REL
    if not ack.exists():
        return False
    try:
        age_min = (time.time() - ack.stat().st_mtime) / 60.0
        if age_min >= FILE_ACK_MAX_AGE_MIN:
            return False
        # Content validation (design-review P0, RCA 2026-06-02): require a real
        # reason ≥12 chars with a letter run + separator — same shape as other
        # gate ACKs. An empty / garbage file does NOT disable the invariant.
        reason = ack.read_text(encoding="utf-8", errors="replace")[:4096].strip()
        return bool(re.match(r"^(?=.{12,})(?=.*[A-Za-z]{3,}).+[\s\-_:]+.+$", reason))
    except OSError:
        return False


def _get_session_id(transcript_path: str = "") -> str:
    """Best-effort current Claude session id.

    Priority: CLAUDE_SESSION_ID env → transcript_path filename → /tmp glob.
    RCA 2026-06-02: Cowork does NOT export CLAUDE_SESSION_ID, but DOES pass
    transcript_path in the hook payload (e.g. .../<session-id>.jsonl) — that
    is a reliable per-session id, unlike the fragile newest-mtime /tmp glob
    which can resolve a DIFFERENT parallel session.
    """
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    if sid:
        return sid[:8]
    # transcript_path: .../<session-id>.jsonl — reliable when env is absent.
    # Split on FIRST dot (not Path.stem) so multi-dot names (<id>.2026.jsonl)
    # still yield the full id (code-review M1, RCA 2026-06-02).
    if transcript_path:
        name = Path(transcript_path).name.split(".", 1)[0]
        if name and len(name) >= 8:
            return name[:8]
    # Fallback: newest dir under /tmp/claude-501/-Users-*-heroes-rickai-workspace*/
    try:
        candidates = list(Path("/tmp/claude-501").glob("-Users-*-heroes-rickai-workspace*"))
        if not candidates:
            return ""
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        subdirs = sorted(
            newest.iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for d in subdirs:
            if d.is_dir() and len(d.name) >= 8:
                return d.name[:8]
    except OSError:
        pass
    return ""


def _branch_has_own_claim(branch: str, session_id: str, ledger: Path) -> bool:
    """Read branch-ownership-ledger.jsonl, check own active claim."""
    if not ledger.exists() or not session_id:
        return False
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("branch") != branch:
                continue
            if entry.get("status") != "active":
                continue
            entry_sid = (entry.get("session_id") or "")[:8]
            if entry_sid == session_id:
                return True
    except OSError:
        pass
    return False


def _parse_json_array(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def _load_active_beads(repo_root: str, beads_file: Path) -> list[dict]:
    """Read active bead state through bd/Dolt first, JSONL export as fallback.

    bd 1.0.4 treats Dolt as the canonical datastore. This workspace still keeps
    `.beads/issues.jsonl` as a required git-export visibility surface, but hooks
    must not depend on it as the live source when `bd list --json` works.
    """
    merged: dict[str, dict] = {}
    saw_success = False
    for status in ("open", "in_progress", "blocked"):
        rc, out = _run_rc(["bd", "list", "--status", status, "--limit", "0", "--json"], cwd=repo_root)
        if rc != 0:
            continue
        saw_success = True
        for bead in _parse_json_array(out):
            bid = bead.get("id")
            if bid:
                merged[str(bid)] = bead
    if saw_success:
        return list(merged.values())
    if not beads_file.exists():
        return []
    out: list[dict] = []
    try:
        for line in beads_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
    except OSError:
        pass
    return out


def _has_active_bd_ticket_for_branch(branch: str, repo_root: str, beads_file: Path) -> bool:
    """Check active bd/Dolt state for a ticket matching branch slug.

    Branch convention: pr-rick-<slug>[-<date>] OR pr-rick-<slug>.
    Match: bd-ticket id appears as substring of branch OR title token matches.
    """
    # Extract bead-id from branch (e.g. pr-rick-wwc → wwc, pr-rick-jtbd-... → jtbd-...)
    m = re.match(r"^pr-rick-([a-z0-9][a-z0-9-]+)$", branch)
    if not m:
        return False
    branch_slug = m.group(1).split("-")[0]
    for entry in _load_active_beads(repo_root, beads_file):
        bid = entry.get("id", "")
        status = entry.get("status", "")
        # Match: bd-id is contained in branch name OR bd-id ends with our slug
        if status in ("open", "in_progress", "blocked") and (
            bid.endswith(f"-{branch_slug}") or f"-{branch_slug}-" in bid or branch.endswith(bid) or bid in branch
        ):
            return True
    return False


def _find_projectname_todo(repo_root: str, branch: str) -> str:
    """Best-effort check whether a {projectname}.todo.md exists for branch slug.

    Returns human-readable hint string for the remediation message.
    Per skill 1-critical-chain-status-report — substantial work MUST have a
    {project}.todo.md with Goldratt chain + outcome + bottleneck.
    """
    m = re.match(r"^pr-rick-([a-z0-9][a-z0-9-]+?)(?:-\d{4}-\d{2}-\d{2})?$", branch)
    slug = m.group(1) if m else branch
    # RCA 2026-06-02: a recursive `**` glob over this workspace (huge <internal-folder>
    # client data, node_modules, .git) takes >10s and times out the hook on
    # the BLOCK path. Search only SHALLOW canonical todo locations — repo root
    # and one level under client projects — never a full-tree walk.
    try:
        root = Path(repo_root)
        search_globs = [
            f"{slug}.todo.md",
            f"*{slug}*.todo.md",
            f"<internal-folder>/clients/all-clients/*/projects/*/{slug}.todo.md",
            f"<internal-folder>/clients/all-clients/*/projects/*/*{slug}*.todo.md",
        ]
        for pat in search_globs:
            hits = list(root.glob(pat))[:3]
            if hits:
                return f"found ({hits[0].relative_to(root)})"
    except (OSError, ValueError):
        pass
    return "none — create per 1-critical-chain-status-report"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    # ACK override (env — works only if Claude Code was launched with it set;
    # does NOT propagate from an inline Bash/Write prefix in Cowork. The
    # working escape hatch is the file sentinel checked below — RCA 2026-06-02)
    ack = os.environ.get(ACK_ENV, "")
    if len(ack) >= ACK_MIN_CHARS:
        return 0

    transcript_path = payload.get("transcript_path", "") or ""
    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return 0

    # Skip narrative paths
    if _is_narrative(file_path):
        return 0

    # Skip non-critical paths (avoid noise on misc files)
    if not _is_critical(file_path):
        return 0

    # Get repo state
    cwd = os.getcwd()
    repo_root = _run(["git", "rev-parse", "--show-toplevel"]) or cwd
    branch = _run(["git", "symbolic-ref", "--short", "-q", "HEAD"])

    if not branch:
        return 0  # detached HEAD — N/A (bisect / rebase / etc.)

    # NOTE (RCA 2026-06-02): main/master/production/release are NOT skipped.
    # They ARE the shared root tree this invariant protects. The old
    # `if branch in ("main",...): return 0` silently allowlisted exactly the
    # most common dirty-tree source — a session starting on main and doing
    # critical work without own branch+bead. Verified empirically: gate
    # exit 0 on main, so beads/worktree were never forced. Now main proceeds
    # to the worktree/claim/bd-ticket checks below; the legitimate escape is
    # creating a worktree (detected) or own claim — not "being on main".
    #
    # Still skip Cowork auto-branches + scratch (genuinely transient).
    if branch.startswith(("claude/", "wip/", "tmp/", "rescue/")):
        return 0

    # Skip if in own session-isolated worktree (the intended escape path)
    if _is_in_own_worktree(repo_root):
        return 0

    # File-based ACK escape (Cowork-compatible — env ACK can't reach this hook)
    if _has_file_ack(repo_root):
        return 0

    # Check branch ownership claim (session id from transcript_path — reliable
    # in Cowork where CLAUDE_SESSION_ID is unset, RCA 2026-06-02)
    session_id = _get_session_id(transcript_path)
    ledger = Path(repo_root) / ".agents" / "memory" / "runtime" / "branch-ownership-ledger.jsonl"
    if _branch_has_own_claim(branch, session_id, ledger):
        return 0

    # Check bd-ticket match
    beads_file = Path(repo_root) / ".beads" / "issues.jsonl"
    if _has_active_bd_ticket_for_branch(branch, repo_root, beads_file):
        return 0

    # ALL conditions met. Phase 2 (RCA 2026-05-28 escalation): BLOCK.
    # Owner steering repeated 4+ sessions «почему новая сессия сразу не
    # создаёт ветку + bead + todo» → WARN-only был ignorable → escalated
    # to BLOCK. Dirty-tree root cause: inherited-HEAD work + auto_commit_
    # on_stop wip-pollution compound. BLOCK forces own branch BEFORE first
    # substantial Write so auto-stop commits land on own branch, not shared
    # HEAD.
    #
    # Phase 1 WARN remains available via PHASE1_WARN_ONLY env for staged
    # rollout / debugging.
    phase1 = os.environ.get("BRANCH_BEAD_GATE_PHASE1_WARN", "") == "1"
    verb = "WARN (Phase 1 — non-blocking)" if phase1 else "BLOCK (Phase 2)"
    todo_hint = _find_projectname_todo(repo_root, branch)

    sys.stderr.write(
        f"first-substantial-write-branch-bead-gate: {verb}\n"
        f"\n"
        f"You are about to {tool_name} a critical-path file ON THE SHARED ROOT TREE:\n"
        f"  {file_path}\n"
        f"\n"
        f"Current state (no own branch claim, no matched bd-ticket, no {{projectname}}.todo.md):\n"
        f"  HEAD branch:  {branch}  (inherited or shared with other sessions)\n"
        f"  Repo root:    {repo_root}\n"
        f"  Session id:   {session_id or '(unknown — fallback)'}\n"
        f"  Ledger claim: none for this session on this branch\n"
        f"  bd-ticket:    no in-progress ticket matches branch slug\n"
        f"  {{projectname}}.todo.md: {todo_hint}\n"
        f"\n"
        f"WHY THIS BLOCKS (RCA 2026-05-28 dirty-tree root cause):\n"
        f"  Working here → auto_commit_on_stop.py commits your wip to THIS\n"
        f"  shared HEAD on every Stop → next session inherits it → +167k\n"
        f"  «грязное дерево» compounds. Own branch first = wip lands on YOUR\n"
        f"  branch, shared HEAD stays clean.\n"
        f"\n"
        f"Required FIRST action (bead-first, AGENTS.md §Branch-and-bead-first-touch):\n"
        f"  1. bd-ticket (JTBD one-liner = source of branch slug):\n"
        f'     bd create --title="<JTBD: Когда ..., хотим ...>" --type=task\n'
        f"  2. Canonical worktree (make worktree derives JTBD-slug name + full checkout):\n"
        f"     make worktree BEAD=<bead-id>\n"
        f"     cd .claude/worktrees/pr-rick-<slug>-<bead-id> && bd update <bead-id> --claim\n"
        f"     (fallback if bd unavailable: git worktree add .claude/worktrees/pr-rick-<jtbd-slug> -b pr-rick-<jtbd-slug>)\n"
        f"  3. {{projectname}}.todo.md (skill 1-critical-chain-status-report — Goldratt chain + outcome)\n"
        f"\n"
        f"Override / escape hatches:\n"
        f"  • File ACK (Cowork-compatible — USE THIS, env does not reach this hook):\n"
        f"      mkdir -p .claude/.state && echo 'reason: <why> <bd-id>' > {FILE_ACK_REL}\n"
        f"      (valid {FILE_ACK_MAX_AGE_MIN} min; delete after the legitimate hotfix)\n"
        f"  • Env ACK (only if Claude Code was LAUNCHED with it — inline prefix won't work):\n"
        f'      {ACK_ENV}="reason: ... <bd-id>" (≥{ACK_MIN_CHARS} chars)\n'
        f"  • Staged rollout to WARN: BRANCH_BEAD_GATE_PHASE1_WARN=1\n"
        f"\n"
        f"Source: RCA 2026-05-28 (10th recurrence) + RCA 2026-06-02 (main allowlist\n"
        f"bug — gate slept on the most common shared-tree state; env ACK unreachable).\n"
    )
    return 0 if phase1 else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover — fail open
        sys.stderr.write(f"first-substantial-write-branch-bead-gate: internal error: {exc}\n")
        sys.exit(0)
