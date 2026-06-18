#!/usr/bin/env python3
"""userprompt_branch_bead_nudge — Claude Code UserPromptSubmit hook.

Answers owner Q2 (2026-05-28): «если чат уже не создал session start →
own branch + own bd-ticket + {projectname}.todo.md, какой хук и триггер
в след. запрос от меня заставит его уйти в свою ветку?».

THE TRIGGER: this UserPromptSubmit hook fires on the OWNER'S NEXT REQUEST
(every prompt submit). It is the EARLIEST possible trigger — before the
agent reads/writes/thinks. It complements the PreToolUse Write gate
(first_substantial_write_branch_bead_gate.py, PR #172):

  - UserPromptSubmit (THIS hook): proactive nudge at request time —
    injects a context reminder so the agent creates own branch+bead+todo
    as its FIRST action this turn.
  - PreToolUse Write (PR #172): hard BLOCK at write time — if the agent
    ignores the nudge and tries to Write a critical file on shared tree,
    exit 2 blocks it.

Two-layer: nudge → (if ignored) BLOCK. Closes the gap where a research-
only next request (Read/Bash, no Write) never triggers the Write gate,
so the session keeps working on the inherited shared HEAD.

Behavior:
- Fires on every UserPromptSubmit.
- If cwd is a per-session worktree (.claude/worktrees/* OR /tmp/wt-*) →
  silent (already isolated).
- If HEAD == main/master/etc OR claude/wip/tmp/rescue → silent (allowlist).
- If on shared root tree non-main branch without own bd-claim AND no
  per-branch {projectname}.todo.md → emit additionalContext reminder
  (stdout JSON `{"hookSpecificOutput":{"additionalContext":"..."}}`) so
  the agent's FIRST action is branch+bead+todo creation.
- NEVER blocks the prompt (UserPromptSubmit exit 2 would drop the owner's
  message — unacceptable). Always exit 0. Nudge is context-injection only;
  the hard stop is the PreToolUse Write gate.

Universal — no client/project hardcode. Suppress via
SESSION_BRANCH_NUDGE_OFF=1 env (for sessions intentionally on shared tree,
e.g. RCA-only / narrative-only work).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8, cwd=cwd, check=False)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _is_worktree(repo: str) -> bool:
    if ".claude/worktrees/" in repo or "/tmp/wt-" in repo or "/private/tmp/wt-" in repo:
        return True
    gd = _run(["git", "rev-parse", "--git-dir"], cwd=repo)
    cd = _run(["git", "rev-parse", "--git-common-dir"], cwd=repo)
    return bool(gd and cd and gd != cd)


def _session_id(transcript_path: str = "") -> str:
    # RCA 2026-06-02: Cowork doesn't export CLAUDE_SESSION_ID; transcript_path
    # filename (.../<session-id>.jsonl) is the reliable per-session id.
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    if sid:
        return sid[:8]
    if transcript_path:
        name = Path(transcript_path).name.split(".", 1)[0]
        if name and len(name) >= 8:
            return name[:8]
    return ""


def _has_own_claim(branch: str, sid: str, ledger: Path) -> bool:
    if not ledger.exists() or not sid:
        return False
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("branch") == branch and e.get("status") == "active" and (e.get("session_id") or "")[:8] == sid:
                return True
    except OSError:
        pass
    return False


def main() -> int:
    if os.environ.get("SESSION_BRANCH_NUDGE_OFF", "") == "1":
        return 0
    transcript_path = ""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        transcript_path = payload.get("transcript_path", "") or ""
    except json.JSONDecodeError:
        pass

    repo = _run(["git", "rev-parse", "--show-toplevel"]) or os.getcwd()
    if _is_worktree(repo):
        return 0  # already isolated — silent

    branch = _run(["git", "symbolic-ref", "--short", "-q", "HEAD"])
    if not branch:
        return 0
    # RCA 2026-06-02: main/master/production/release NOT skipped — they ARE the
    # shared root tree. Starting on main without own branch+bead is the most
    # common dirty-tree source; the old allowlist made this nudge silent there.
    if branch.startswith(("claude/", "wip/", "tmp/", "rescue/")):
        return 0

    sid = _session_id(transcript_path)
    ledger = Path(repo) / ".agents" / "memory" / "runtime" / "branch-ownership-ledger.jsonl"
    if _has_own_claim(branch, sid, ledger):
        return 0  # already claimed own branch this session

    # Measure how polluted the shared tree currently is (for urgency signal)
    ahead = _run(["git", "rev-list", "--count", "origin/main..HEAD"]) or "?"

    context = (
        f"⚠ SESSION ISOLATION REMINDER (userprompt_branch_bead_nudge, RCA 2026-05-28):\n"
        f"You are on the SHARED ROOT TREE branch `{branch}` "
        f"({ahead} commits ahead of origin/main), NOT a per-session worktree, "
        f"with no own branch-ownership claim.\n\n"
        f"Per AGENTS.md §Branch-and-bead-first-touch invariant — your FIRST "
        f"action this turn (before any substantial Write/Edit) MUST be:\n"
        f'  1. bd create --title="<JTBD: Когда ..., хотим ...>" --type=task\n'
        f"  2. make worktree BEAD=<bead-id>  (derives JTBD-slug name + full checkout)\n"
        f"     cd .claude/worktrees/pr-rick-<slug>-<bead-id> && bd update <bead-id> --claim\n"
        f"  3. {{projectname}}.todo.md via skill 1-critical-chain-status-report (substantial work)\n\n"
        f"If you skip this and try to Write a critical-path file on this shared "
        f"tree, first_substantial_write_branch_bead_gate.py will BLOCK (exit 2). "
        f"Create the branch+bead+todo now to avoid the block and to keep shared "
        f"HEAD clean (auto-stop commits then land on YOUR branch).\n\n"
        f"Exempt this session (RCA-only / narrative-only): file ack\n"
        f"  mkdir -p .claude/.state && echo 'reason: ...' > .claude/.state/branch_bead_gate_ack"
    )

    # UserPromptSubmit additionalContext injection (non-blocking)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover — fail open
        sys.stderr.write(f"userprompt-branch-bead-nudge: internal error: {exc}\n")
        sys.exit(0)
