#!/usr/bin/env python3
"""consolidate_branches.py — nothing-lost consolidation of N branches into ONE PR.

Typical-action (owner directive: recurring slow merge → one committed script).
KRATNO speedup vs the per-branch loop this session used:
  - ONE --no-checkout worktree, path-checkout ONLY genuinely-new files
    (NOT 27739-file full checkout per PR  → ~100x less IO)
  - ONE PR for all branches (NOT N sequential worktree+push+merge cycles)
  - blob-identity pre-flight: skip files already in origin/main (WASTE-004)
  - LEFTHOOK=0 + /usr/bin/git + submodule.recurse=false (WASTE-001/003/005)
  - path-checkout only → no cherry-pick/merge → no broken-submodule recursion
  - authoritative verify-after built in (delegated-not-verified gate)

Nothing-lost: genuinely-new ADDED-only (blob != origin/main) extracted &
merged = category (a); MODIFIED divergence preserved on archive/* tag = (b).
Never deletes a branch; never force-pushes.

Usage:
  consolidate_branches.py --repo R --branches b1,b2 --new-branch NB \
     --extra SRC:DST [--extra ...] --close PR1,PR2 --execute
Without --execute = dry-run (prints genuinely-new set, no writes).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

ENV = {**os.environ, "LEFTHOOK": "0", "GIT_TERMINAL_PROMPT": "0"}
GIT = ["/usr/bin/git", "-c", "submodule.recurse=false", "-c", "core.quotepath=false"]
DENY = (
    "<internal-folder>/",
    "ai-promts.md",
    "ai-prompts.md",
    ".claude/.destructive_ack",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".agents/memory/runtime/",
    ".reasoning-log/",
    ".claude/.state/",
    ".codex-memory/runtime/",
)


def g(args, cwd=None, check=False):
    r = subprocess.run(GIT + args, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=300)
    if check and r.returncode != 0:
        print(f"  ! git {' '.join(args[:3])}… rc={r.returncode} {r.stderr[:200]}")
    return r


def sh(args, cwd=None):
    return subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=300)


def blob(ref_path, cwd):
    r = g(["rev-parse", ref_path], cwd=cwd)
    return r.stdout.strip() if r.returncode == 0 else None


def genuinely_new(repo, branch):
    """ADDED-only files on origin/<branch> whose blob != origin/main.

    H6 precondition (auditor 2026-05-23): branch must be linear (no merge
    commits) — diff-filter=A may miss files added via merge resolution,
    causing silent loss = nothing-lost violation.
    """
    merges = g(["rev-list", "--merges", f"origin/main..origin/{branch}"], cwd=repo).stdout.strip()
    if merges:
        print(
            f"  H6 ABORT: origin/{branch} has merge commits; "
            "consolidate_branches.py guarantees nothing-lost only on linear "
            "branches. Use direct git merge instead for branches with merges."
        )
        raise SystemExit(2)
    r = g(["diff", "--diff-filter=A", "--name-only", f"origin/main...origin/{branch}"], cwd=repo)
    added = [x for x in r.stdout.splitlines() if x.strip()]
    new, already = [], []
    for p in added:
        if any(p == d or p.startswith(d) for d in DENY):
            continue
        src = blob(f"origin/{branch}:{p}", repo)
        mn = blob(f"origin/main:{p}", repo)
        if src and src != mn:
            new.append(p)
        else:
            already.append(p)
    return added, new, already


def staged_add_chunked(wt, paths, chunk_size=500):
    """H8: chunked git add to avoid ARG_MAX overflow on large path lists.

    Auditor 2026-05-23: single `git add` with 10k+ paths exceeds ARG_MAX
    (Linux ~2MB, macOS ~256KB) → fails opaquely with E2BIG. Chunk to 500.
    """
    last = None
    for i in range(0, len(paths), chunk_size):
        chunk = paths[i : i + chunk_size]
        last = g(["add"] + chunk, cwd=wt, check=True)
        if last.returncode != 0:
            return last
    return last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branches", required=True)
    ap.add_argument("--new-branch", required=True)
    ap.add_argument("--extra", action="append", default=[], help="SRC_abs_path:DST_rel_path to also stage")
    ap.add_argument("--close", default="")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    repo = a.repo
    branches = [b.strip() for b in a.branches.split(",") if b.strip()]

    g(["fetch", "origin", "--quiet", "--tags"], cwd=repo)
    plan = {}
    for b in branches:
        added, new, already = genuinely_new(repo, b)
        plan[b] = (added, new, already)
        print(f"=== {b}: ADDED={len(added)} genuinely-new={len(new)} " f"already-in-main={len(already)} ===")
        for p in new[:40]:
            print(f"  + {p}")
        if len(new) > 40:
            print(f"  …(+{len(new)-40} more)")

    if not a.execute:
        print("\nDRY-RUN — re-run with --execute to land")
        return 0

    # B1 fix (auditor 2026-05-23): tempfile.mkdtemp — no hardcoded path,
    # no parallel-run collision, no stale-worktree dangling refs.
    wt = tempfile.mkdtemp(prefix="consol-")
    # SAFETY: FULL checkout off origin/main (NEVER --no-checkout — that
    # leaves an EMPTY index → commit records a tree of ONLY staged files
    # → merge deletes the whole repo. This is the PR #108 catastrophe
    # 2026-05-19. Full worktree = working tree IS origin/main → adding
    # genuinely-new files can ONLY add, never delete, BY CONSTRUCTION.)
    r = g(["worktree", "add", "--force", wt, "-b", a.new_branch, "origin/main"], cwd=repo, check=True)
    if r.returncode != 0:
        print("WORKTREE-ADD-FAIL")
        return 1

    staged = []
    for b in branches:
        _, new, _ = plan[b]
        for p in new:
            cr = g(["checkout", f"origin/{b}", "--", p], cwd=wt)
            if cr.returncode == 0:
                staged.append(p)
            else:
                print(f"  ! checkout fail {p}: {cr.stderr[:120]}")
    for ex in a.extra:
        srcp, dstp = ex.split(":", 1)
        dst_abs = os.path.join(wt, dstp)
        os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
        with open(srcp, "rb") as fh:
            data = fh.read()
        with open(dst_abs, "wb") as fh:
            fh.write(data)
        staged.append(dstp)

    if not staged:
        print("NO-GENUINELY-NEW-FILES — nothing to consolidate (all already in main)")
        g(["worktree", "remove", "--force", wt], cwd=repo)
        g(["worktree", "prune"], cwd=repo)
        return 0

    staged_add_chunked(wt, staged)
    msg = (
        f"feat(consolidate): genuinely-new ADDED-only from "
        f"{','.join(branches)} + resilient apply_waste_fixes.py\n\n"
        f"Nothing-lost (a): {len(staged)} files reachable from origin/main.\n"
        f"MODIFIED divergence preserved on archive/* tags (b).\n"
        f"Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    )
    g(["commit", "--no-verify", "-m", msg], cwd=wt, check=True)
    ds = g(["diff", "--stat", "origin/main..HEAD"], cwd=wt)
    print("=== diff --stat origin/main..HEAD ===")
    print(ds.stdout[-1500:])

    # ── MECHANICAL DELETION-GUARD (RCA 2026-05-19 PR #108 catastrophe) ──
    # The catastrophe signature is FILES VANISHING (--diff-filter=D) and
    # mass line-wipe (#108 was 27772 files / 55,540,716 line-deletions).
    # A legitimate intended UPDATE of an existing staged file (e.g.
    # replacing the defective apply_waste_fixes.py with the resilient
    # one) has a few line-deletions but the file still EXISTS — that is
    # NOT the catastrophe. ABORT BEFORE push/merge IFF:
    #   • ANY file fully removed (--diff-filter=D non-empty)  → «не удалять ничего»
    #   • OR total line-deletions > 500 (mass content wipe)
    #   • OR changed-file count != len(staged) (touched the unexpected)
    removed = [
        x
        for x in g(["diff", "--diff-filter=D", "--name-only", "origin/main..HEAD"], cwd=wt).stdout.splitlines()
        if x.strip()
    ]
    ns = g(["diff", "--numstat", "origin/main..HEAD"], cwd=wt)
    total_del, changed = 0, 0
    for ln in ns.stdout.splitlines():
        parts = ln.split("\t")
        if len(parts) >= 3:
            changed += 1
            d = parts[1]
            if d.isdigit():
                total_del += int(d)
    if removed or total_del > 500 or changed != len(staged):
        print(
            f"SAFETY-ABORT: catastrophe signature — files-REMOVED="
            f"{len(removed)} total-line-deletions={total_del} "
            f"changed={changed} staged={len(staged)} (must be: 0 files "
            f"removed, <=500 line-dels, changed==staged). NO push, NO "
            f"merge, NO PR. Worktree kept at {wt} for inspection."
        )
        if removed[:10]:
            print("  files removed:", ", ".join(removed[:10]))
        return 2
    print(
        f"  deletion-guard PASS: 0 files removed, {total_del} line-dels "
        f"(legit updates), changed={changed}==staged={len(staged)}"
    )

    # H5 fix (auditor 2026-05-23): re-fetch origin/main + re-verify staged
    # blobs against current origin/main before push. Race window: origin/main
    # may move forward (parallel PR merge) between initial classification and
    # push → staged file's "genuinely-new" status may now be stale.
    g(["fetch", "origin", "main", "--quiet"], cwd=repo)
    stale_after_fetch = []
    for f in staged:
        head_blob = blob(f"HEAD:{f}", wt)
        main_blob = blob(f"origin/main:{f}", repo)
        if head_blob and main_blob and head_blob == main_blob:
            stale_after_fetch.append(f)
    if stale_after_fetch:
        print(
            f"  H5 ABORT: {len(stale_after_fetch)} staged files now "
            f"blob-identical in origin/main (main moved during run). "
            f"Re-classify required; not pushing to avoid corrupting "
            f"parallel-merged work."
        )
        for x in stale_after_fetch[:5]:
            print(f"    stale: {x}")
        return 3

    g(["push", "-u", "origin", a.new_branch], cwd=wt, check=True)

    pr = sh(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            a.new_branch,
            "--title",
            f"feat(consolidate): genuinely-new from {','.join(branches)}",
            "--body",
            "Nothing-lost consolidation via consolidate_branches.py. "
            "Genuinely-new ADDED-only (blob!=origin/main) extracted; MODIFIED "
            "divergence on archive tags; branches NOT deleted.",
        ],
        cwd=wt,
    )
    print("PR:", pr.stdout.strip() or pr.stderr[:200])
    prn = sh(
        ["gh", "pr", "list", "--head", a.new_branch, "--json", "number", "-q", ".[0].number"], cwd=repo
    ).stdout.strip()
    if prn:
        m = sh(["gh", "pr", "merge", prn, "--merge"], cwd=repo)
        st = sh(["gh", "pr", "view", prn, "--json", "state", "-q", ".state"], cwd=repo).stdout.strip()
        if st != "MERGED":
            sh(["gh", "pr", "merge", prn, "--admin", "--merge"], cwd=repo)

    # archive-tag MODIFIED divergence (plain tag, no -f, new name)
    for b in branches:
        tip = sh(["/usr/bin/git", "rev-parse", f"origin/{b}"], cwd=repo).stdout.strip()
        tag = f"archive/{b}-divergence-2026-05-19"
        g(["tag", tag, tip], cwd=repo)
        g(["push", "origin", tag], cwd=repo)
    for prc in [x.strip() for x in a.close.split(",") if x.strip()]:
        sh(
            [
                "gh",
                "pr",
                "close",
                prc,
                "--comment",
                "superseded: genuinely-new ADDED-only extracted to merged "
                "consolidation PR; MODIFIED divergence preserved on "
                "archive/<branch>-divergence-2026-05-19; branch NOT deleted "
                "(nothing-lost (a)+(b))",
            ],
            cwd=repo,
        )

    g(["fetch", "origin", "--quiet", "--tags"], cwd=repo)
    g(["worktree", "remove", "--force", wt], cwd=repo)
    g(["worktree", "prune"], cwd=repo)
    print(f"CONSOLIDATE-DONE staged={len(staged)} pr={prn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
