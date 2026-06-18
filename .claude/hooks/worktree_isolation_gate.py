#!/usr/bin/env python3
"""PreToolUse Bash hook — Pillar A (Standard 0.2 §2): main checkout in workspace
root is READ-ONLY for agents when parallel sessions are active.

Blocks branch-switching / history-rewriting / tree-destroying git ops executed
from the SHARED workspace root while >1 Claude session is active, because that
destroys another agent's uncommitted work (RCA 2026-05-16: `checkout -f main`
killed owner's live-edited ai-promts.md; `git clean -fd` killed <internal-component>).

Allowed in shared root: read-only git + incremental `git add <path> && commit`.
Required instead: work inside `git worktree` / isolated `git clone --local`.

Exit 0 = pass; exit 2 = BLOCK. Override: sentinel `.claude/.destructive_ack`
line `WORKTREE_ISOLATION_ACK: <reason ≥10 chars> @ <iso>` (fresh ≤10 min) OR
env WORKTREE_ISOLATION_ACK (≥10 chars).
"""

import json
import os
import re
import sys
import time
from pathlib import Path

def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    return Path.cwd()


WORKSPACE = _repo_root()
SENTINEL = WORKSPACE / ".claude" / ".destructive_ack"

# git ops that mutate branch/HEAD/tree (unsafe in shared root under parallel work)
RISKY = re.compile(
    r"\bgit\s+(?:-C\s+\S+\s+|--git-dir\S*\s+|-c\s+\S+\s+)*"
    r"(?:checkout\s+(?!-b\b)(?!-{0,2}\s*$)\S|switch\s+(?!-c\b)\S|"
    r"reset\s+--hard|clean\s+-\w*[fdx]|rebase\b|merge\s+(?!--abort)\S|"
    r"branch\s+-\w*D|stash\s+(?:pop|drop|clear|push\s+-\w*u(?!\s+--?\s*\w*\s+--?\s+\S)))"
)
# `git stash push -u` WITHOUT a pathspec (bare global) = the S9 incident
BARE_STASH_U = re.compile(r"\bgit\s+stash\s+push\b[^\n]*\s-\w*u\w*\b(?![^\n]*\s--\s)")
SAFE_READONLY = re.compile(
    r"\bgit\s+(?:status|log|diff|show|cat-file|ls-tree|ls-files|"
    r"rev-parse|rev-list|fetch|branch\s*$|branch\s+-(?:-list|v|a|r)|"
    r"for-each-ref|worktree\s+(?:list|add)|tag\s+(?:-l|--list)|remote|config\s+--get)"
)


def _in_shared_root(cmd: str) -> bool:
    """True if op targets the shared workspace root (not a worktree / /tmp clone)."""
    if "/tmp/" in cmd or ".claude/worktrees/" in cmd or "git clone" in cmd:
        return False
    try:
        # cwd of the Bash tool is the workspace root by default
        cwd = os.getcwd()
    except OSError:
        return True
    return (
        str(WORKSPACE) == cwd
        or cwd.startswith(str(WORKSPACE) + "/")
        and ".claude/worktrees/" not in cwd
        and "/tmp/" not in cwd
        and cwd == str(WORKSPACE)
    )


def _parallel_sessions() -> int:
    """Count active Claude sessions for this workspace (last 10 min)."""
    try:
        slug = "heroes-rickai-workspace"
        cutoff = time.time() - 600
        n = 0
        for parent in Path("/tmp/claude-501").glob(f"-Users-*-{slug}*"):
            for d in parent.iterdir():
                try:
                    if d.is_dir() and d.stat().st_mtime > cutoff:
                        n += 1
                except OSError:
                    continue
        return n
    except OSError:
        return 0


def _ack_ok() -> bool:
    if len(os.environ.get("WORKTREE_ISOLATION_ACK", "").strip()) >= 10:
        return True
    try:
        if not SENTINEL.exists() or time.time() - SENTINEL.stat().st_mtime > 600:
            return False
        for line in SENTINEL.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("WORKTREE_ISOLATION_ACK:"):
                reason = line.split(":", 1)[1].split("@")[0].strip()
                if len(reason) >= 10:
                    return True
    except OSError:
        return False
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    cmd = (payload.get("tool_input", {}) or {}).get("command", "")
    if not cmd.strip():
        sys.exit(0)
    is_risky = bool(RISKY.search(cmd) or BARE_STASH_U.search(cmd))
    if not is_risky:
        sys.exit(0)
    # read-only-only command line → allow
    if SAFE_READONLY.search(cmd) and not (RISKY.search(cmd) or BARE_STASH_U.search(cmd)):
        sys.exit(0)
    if not _in_shared_root(cmd):
        sys.exit(0)  # already isolated (worktree / /tmp clone)
    if _parallel_sessions() <= 1:
        sys.exit(0)  # single session — shared root acceptable
    if _ack_ok():
        print("worktree-isolation: ACK accepted (Standard 0.2 §2 override)", file=sys.stderr)
        sys.exit(0)
    bar = "=" * 72
    print(bar, file=sys.stderr)
    print("WORKTREE-ISOLATION BLOCK — Standard 0.2 §2 Pillar A", file=sys.stderr)
    print("Branch-switch / history-rewrite / tree-destroy git op in SHARED ROOT", file=sys.stderr)
    print(f"while {_parallel_sessions()} parallel Claude sessions active.", file=sys.stderr)
    print("RCA 2026-05-16: this class killed ai-promts.md + <internal-component>.", file=sys.stderr)
    print(bar, file=sys.stderr)
    print("REQUIRED: work in an isolated copy, not the shared root:", file=sys.stderr)
    print("  git worktree add .claude/worktrees/<bead> -b <branch>   # then cd there", file=sys.stderr)
    print("  OR  git clone --local --no-hardlinks . /tmp/<wt>         # PR from there", file=sys.stderr)
    print("Override (only if you verified no parallel uncommitted work):", file=sys.stderr)
    print('  echo "WORKTREE_ISOLATION_ACK: <reason ≥10 chars> @ $(date -u +%FT%TZ)" \\', file=sys.stderr)
    print("    >> .claude/.destructive_ack", file=sys.stderr)
    print(bar, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
