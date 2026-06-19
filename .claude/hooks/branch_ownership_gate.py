#!/usr/bin/env python3
"""PreToolUse Bash hook — Standard 0.2 §2 Pillar A / §10 Layer 1.

Branch-ownership lock: BLOCK `git commit / branch -f / merge / push <branch>`
when an ACTIVE claim on that branch in
`.agents/memory/runtime/branch-ownership-ledger.jsonl` belongs to a DIFFERENT
Claude session. Forces per-session branch ownership → agents stop substituting
branches / working in another agent's branch / mixing results (RCA 2026-05-16:
parallel PR #77/#78/#79 collision; R7 9 diverged skills on a foreign branch).

Resolution model:
- Each git-changing agent appends a CLAIM row (session_id, branch, ...).
- This hook reads the ledger; if the target branch has an `active` claim by
  ANOTHER session whose last_heartbeat is recent (<60 min) → BLOCK.
- If no active claim → PASS (but reminder to claim).
- Own-session claim → PASS.

Session id source: $CLAUDE_SESSION_ID env if present, else first 8 chars of the
newest dir under /tmp/claude-501/-Users-*-heroes-rickai-workspace*/ (best-effort).

Override: sentinel `.claude/.destructive_ack` line
`BRANCH_OWNERSHIP_ACK: <reason ≥10 chars> @ <iso>` (fresh ≤10 min) — for the
case where the other claim is stale/abandoned and you verified it manually.

Exit 0 = pass, exit 2 = BLOCK.
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
LEDGER = WORKSPACE / ".agents" / "memory" / "runtime" / "branch-ownership-ledger.jsonl"
SENTINEL = WORKSPACE / ".claude" / ".destructive_ack"

# git ops that write to a branch
WRITE_OP = re.compile(
    r"\bgit\s+(?:-C\s+\S+\s+|-c\s+\S+\s+)*"
    r"(?:commit\b|push\b|merge\s+(?!--abort)\S|branch\s+-\w*[fDM]|rebase\b|cherry-pick\b)"
)
PUSH_BRANCH = re.compile(r"\bgit\s+push\b[^\n]*?\borigin\b\s+(?:--\S+\s+)*([\w./-]+)")
BRANCH_F = re.compile(r"\bgit\s+branch\s+-\w*f\w*\s+([\w./-]+)")


def _current_session() -> str:
    sid = os.environ.get("CLAUDE_SESSION_ID", "").strip()
    if sid:
        return sid[:8]
    try:
        cands = []
        for p in Path("/tmp/claude-501").glob("-Users-*-heroes-rickai-workspace*"):
            for d in p.iterdir():
                if d.is_dir():
                    cands.append((d.stat().st_mtime, d.name))
        if cands:
            return sorted(cands, reverse=True)[0][1][:8]
    except OSError:
        pass
    return "unknown0"


def _target_branch(cmd: str) -> str:
    m = PUSH_BRANCH.search(cmd)
    if m:
        return m.group(1)
    m = BRANCH_F.search(cmd)
    if m:
        return m.group(1)
    # commit/merge/rebase → current branch
    try:
        import subprocess

        r = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], capture_output=True, text=True, timeout=8)
        return r.stdout.strip()
    except (OSError, Exception):
        return ""


def _active_claims(branch: str) -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    cutoff = time.time() - 3600
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith('{"_schema"'):
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if rec.get("branch") != branch or rec.get("status") != "active":
                continue
            hb = rec.get("last_heartbeat", "")
            try:
                ts = time.mktime(time.strptime(hb.replace("Z", ""), "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, TypeError):
                ts = time.time()  # malformed → treat as fresh (conservative)
            if ts > cutoff:
                out.append(rec)
    except OSError:
        return []
    return out


def _ack_ok() -> bool:
    if len(os.environ.get("BRANCH_OWNERSHIP_ACK", "").strip()) >= 10:
        return True
    try:
        if not SENTINEL.exists() or time.time() - SENTINEL.stat().st_mtime > 600:
            return False
        for ln in SENTINEL.read_text(encoding="utf-8").splitlines():
            if ln.strip().startswith("BRANCH_OWNERSHIP_ACK:"):
                reason = ln.split(":", 1)[1].split("@")[0].strip()
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
    if not cmd.strip() or not WRITE_OP.search(cmd):
        sys.exit(0)
    if "/tmp/" in cmd or ".claude/worktrees/" in cmd:
        sys.exit(0)  # isolated worktree/clone — ownership not shared
    branch = _target_branch(cmd)
    if not branch or branch == "main":
        sys.exit(0)  # main handled by other gates; no branch → skip
    me = _current_session()
    claims = _active_claims(branch)
    foreign = [c for c in claims if (c.get("session_id", "") or "")[:8] != me]
    if not foreign:
        sys.exit(0)  # no foreign active claim → ok (own claim or none)
    if _ack_ok():
        print(f"branch-ownership: ACK accepted — foreign claim on {branch} verified stale", file=sys.stderr)
        sys.exit(0)
    bar = "=" * 72
    print(bar, file=sys.stderr)
    print("BRANCH-OWNERSHIP BLOCK — Standard 0.2 §2 / §10 Layer 1", file=sys.stderr)
    print(f"Branch '{branch}' has an ACTIVE claim by another session:", file=sys.stderr)
    for c in foreign[:3]:
        print(
            f"  session={c.get('session_id','?')[:8]} role={c.get('agent_role','?')} "
            f"intent={c.get('intent','?')[:60]} hb={c.get('last_heartbeat','?')}",
            file=sys.stderr,
        )
    print("RCA 2026-05-16: parallel agents substituting branches → PR collision,", file=sys.stderr)
    print("9 diverged skills on a foreign branch, mixed results.", file=sys.stderr)
    print(bar, file=sys.stderr)
    print("REQUIRED: work in YOUR own branch/worktree, or claim this branch:", file=sys.stderr)
    print("  1. git worktree add .claude/worktrees/<your-bead> -b <your-branch>", file=sys.stderr)
    print("  2. append CLAIM row to .agents/memory/runtime/branch-ownership-ledger.jsonl", file=sys.stderr)
    print("Override (only if foreign claim verified stale/abandoned):", file=sys.stderr)
    print('  echo "BRANCH_OWNERSHIP_ACK: <reason ≥10 chars> @ $(date -u +%FT%TZ)" \\', file=sys.stderr)
    print("    >> .claude/.destructive_ack", file=sys.stderr)
    print(bar, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
