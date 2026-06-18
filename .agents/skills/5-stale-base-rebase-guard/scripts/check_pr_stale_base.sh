#!/usr/bin/env bash
# check_pr_stale_base.sh — типовое действие проверки PR на stale-base drift.
#
# Detects when current branch's base (origin/main) moved ahead by ≥N commits
# AFTER worktree/branch was created — diff PR vs origin/main starts to show
# integrated work as "deletions" (false negative in nothing-lost contract).
#
# RCA-source: 2026-05-24 PR #119 — worktree created 5a5c40f97, main moved
# +63 commits, PR diff showed 5 files as "deleted" (pre_push_deletion_guard.py
# + V1.x sections of 3 sibling skills + consolidate_branches.py). Auditor
# subagent flagged 💀 catastrophic verdict before rebase fixed root cause.
#
# Universal: works for any branch + any clean origin, no client/project hardcode.
#
# Usage:
#   bash check_pr_stale_base.sh                    # check, exit 0 if OK, 1 if stale
#   bash check_pr_stale_base.sh --threshold 10     # custom drift threshold (default 5)
#   bash check_pr_stale_base.sh --auto-rebase      # auto rebase if stale (DANGER — use only with clean tree)
#   bash check_pr_stale_base.sh --json             # JSON output for tooling

set -euo pipefail

THRESHOLD=5
AUTO_REBASE=0
JSON_OUT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --auto-rebase) AUTO_REBASE=1; shift ;;
    --json) JSON_OUT=1; shift ;;
    -h|--help) head -25 "$0" | tail -23; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

BRANCH=$(git branch --show-current 2>/dev/null || echo "DETACHED")
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "DETACHED" ]; then
  if [ "$JSON_OUT" = "1" ]; then
    echo '{"branch":"'$BRANCH'","stale":false,"reason":"main/detached — not applicable"}'
  else
    echo "stale-base-check: not applicable (branch=$BRANCH)"
  fi
  exit 0
fi

git fetch origin main --quiet 2>/dev/null || {
  echo "stale-base-check: WARNING — git fetch origin main failed (offline?)" >&2
}

AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)

# Check for files that appear "deleted" in PR diff because main moved ahead
DRIFT_FILES=""
if [ "$BEHIND" -gt 0 ]; then
  DRIFT_FILES=$(git log HEAD..origin/main --name-only --pretty=format: 2>/dev/null \
    | grep -v "^$" | sort -u | head -20 || echo "")
fi
DRIFT_COUNT=$(echo "$DRIFT_FILES" | grep -c "^[^[:space:]]" 2>/dev/null || echo 0)

STALE=0
if [ "$BEHIND" -ge "$THRESHOLD" ]; then
  STALE=1
fi

if [ "$JSON_OUT" = "1" ]; then
  printf '{"branch":"%s","ahead":%s,"behind":%s,"threshold":%s,"stale":%s,"drift_file_count":%s}\n' \
    "$BRANCH" "$AHEAD" "$BEHIND" "$THRESHOLD" "$STALE" "$DRIFT_COUNT"
else
  echo "stale-base-check: branch=$BRANCH ahead=$AHEAD behind=$BEHIND threshold=$THRESHOLD"
  if [ "$STALE" = "1" ]; then
    echo "🚩 STALE BASE detected — origin/main moved $BEHIND commits ahead"
    echo "   ${DRIFT_COUNT} files in mainline drift that may appear as 'deletions' in PR diff:"
    echo "$DRIFT_FILES" | head -10 | sed 's/^/     /'
    if [ "$DRIFT_COUNT" -gt 10 ]; then
      echo "     ... ($((DRIFT_COUNT - 10)) more)"
    fi
    echo ""
    echo "Action: rebase onto origin/main BEFORE next commit/push:"
    echo "   git rebase origin/main"
    echo "   git push --force-with-lease   # after rebase rewrote sha"
    echo ""
    echo "Reference: RCA 2026-05-24 PR #119 stale-base 'deleted' files."
  else
    echo "✅ OK — base is fresh"
  fi
fi

if [ "$STALE" = "1" ] && [ "$AUTO_REBASE" = "1" ]; then
  echo "--auto-rebase: rebasing..."
  git rebase origin/main || {
    echo "❌ rebase failed — resolve conflicts manually" >&2
    exit 2
  }
  echo "✅ rebased; verify with: git diff --name-only --diff-filter=D origin/main..HEAD"
fi

exit $STALE
