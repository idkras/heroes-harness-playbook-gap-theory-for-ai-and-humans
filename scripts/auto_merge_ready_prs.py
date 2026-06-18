#!/usr/bin/env python3
"""auto_merge_ready_prs.py — universal idempotent sweep that lands ready PRs.

WHY (RCA 2026-06-07, pr-rick-gbpg — 12th recurrence of
`design-injection-without-mechanical-hook`):
10 Codex chats in one day made 4768 shell calls but 8/10 ended on a feature
branch WITHOUT merge → 67 branches ahead of origin/main. Root cause: the
`.claude/hooks/` mechanical enforcement base is wired ONLY to the Claude Code
event schema; the Codex CLI runtime reads CODEX.md→AGENTS.md as a declarative
prompt with no blocking hooks. §Deploy & PR review contract (2026-06-05) was
declarative-only.

CI is ASYNC (85–133 s; `mergeable: UNKNOWN` at push time), so a synchronous
pre-push auto-merge is impossible. The systemic answer is an IDEMPOTENT SWEEP
triggered at natural points by which time CI has completed:
  * GitHub Action `land-ready.yml` schedule  — PRIMARY cross-runtime backstop
    (cannot be `--no-verify`-bypassed; server-side; visible audit in Actions)
  * lefthook pre-push (background)            — opportunistic fast-path
  * Claude SessionStart (background)          — sweeps prior-session leftovers
  * `make land-ready`                         — manual / local cron

SECURITY (Stage-6 security-reviewer S1/S3, 2026-06-07): the repo is GitHub Free
private → branch protection is UNAVAILABLE, so author scoping is the ONLY real
gate. Therefore by default the sweep merges ONLY PRs authored by the resolved
current `gh` login (or the explicit `--author` / AUTO_MERGE_AUTHOR_ALLOWLIST
allowlist) AND only same-repo branches (fork PRs rejected). `--any-author` is an
explicit, <client>-default escape hatch. This kills the "attacker opens pr-evil →
auto-merged → RCE" vector and the "teammate's draft merged on my sweep" surprise.

WARNING (Stage-6 security S2): the author allowlist subsumes a required-review
gate ONLY while the allowlist is a SINGLE trusted owner. If you ever add a
teammate to AUTO_MERGE_AUTHOR_ALLOWLIST, author trust is NOT transitive — you
MUST then also require an approved review (mergeStateStatus already reflects
required reviews when branch protection is enabled; on GitHub Free private it is
not, so multi-author auto-merge there is unsafe without a paid plan).

A PR is "ready" (and merged) only if ALL hold:
  * baseRefName == main (configurable)
  * not draft
  * title has no hold-marker (WIP / DRAFT / DO NOT MERGE / hold / [skip merge]
    / 🚧 / черновик / не мёржить / на доработку)
  * headRefName matches an agent-branch pattern (default pr-* / claude/* / ik-codex/*)
  * head repo == base repo (NOT a fork)
  * author ∈ allowlist (default: resolved current gh login)
  * mergeable == MERGEABLE   (not CONFLICTING, not UNKNOWN)
  * mergeStateStatus == CLEAN (UNSTABLE = a check failed/pending → skip)

This naturally honours the §Deploy & PR review exceptions: CONFLICTING is
skipped, CI-red/pending (UNSTABLE) is skipped, >100 MB never reaches push.
NEVER uses `gh pr merge --admin` (bypasses CI/tree guards — catastrophe #290).

Dry-run by default. Hooks/Action pass --execute explicitly. Fail-open (exit 0)
for hook use unless --strict. Universal: zero client/repo hardcodes.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

DEFAULT_PATTERNS = ["pr-*", "claude/*", "ik-codex/*"]
# Word-like markers get individual \b boundaries (so "drafting" is NOT a hit);
# bracket / emoji / RU markers self-delimit and must NOT carry a leading \b
# (a non-word char like "[" has no word boundary at string start).
HOLD_MARKERS = re.compile(
    r"(\bWIP\b|\bDRAFT\b|\bDO[\s_-]?NOT[\s_-]?MERGE\b|\bHOLD\b"
    r"|\[skip[\s_-]?merge\]|🚧"
    r"|черновик|не[\s_-]+мёржить|не[\s_-]+мержить|на[\s_-]+доработку)",
    re.IGNORECASE,
)
READY_MERGE_STATE = "CLEAN"
READY_MERGEABLE = "MERGEABLE"
DEFAULT_MAX = 10
# isCrossRepository = fork indicator, needed for fork rejection (S3).
PR_FIELDS = "number,headRefName,baseRefName,isDraft,title," "mergeable,mergeStateStatus,author,isCrossRepository"
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a command, return (rc, stdout, stderr). Never raises on non-zero."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(cmd[:3])}"
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}"


def _sanitize(text: str) -> str:
    """Strip control chars / ANSI from untrusted PR strings before logging (S5)."""
    return _CONTROL_CHARS.sub("", str(text))[:200]


def gh_available() -> bool:
    rc, _, _ = _run(["gh", "auth", "status"], timeout=15)
    return rc == 0


def current_gh_login() -> str:
    rc, out, _ = _run(["gh", "api", "user", "--jq", ".login"], timeout=15)
    return out if rc == 0 else ""


def current_branch() -> str:
    rc, out, _ = _run(["git", "symbolic-ref", "--short", "HEAD"], timeout=10)
    return out if rc == 0 else ""


def list_open_prs() -> tuple[list[dict], str | None]:
    """Return (prs, error). error is non-None when the gh call failed (S/L1)."""
    rc, out, err = _run(
        ["gh", "pr", "list", "--state", "open", "--limit", "100", "--json", PR_FIELDS],
        timeout=45,
    )
    if rc != 0:
        return [], f"gh pr list failed (rc={rc}): {_sanitize(err)[:120]}"
    if not out:
        return [], None
    try:
        return json.loads(out), None
    except json.JSONDecodeError as e:
        return [], f"gh pr list JSON parse error: {e}"


def _matches_pattern(branch: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(branch, pat) for pat in patterns)


def _login_of(node: dict | None) -> str:
    return (node or {}).get("login", "") if isinstance(node, dict) else ""


def classify(
    pr: dict,
    *,
    base: str,
    patterns: list[str],
    authors: list[str] | None,
) -> tuple[bool, str]:
    """Return (is_ready, reason). reason explains a skip or confirms ready.

    `authors` None  → any author allowed (explicit --any-author escape hatch).
    `authors` list  → PR author login must be in the list (default safety gate).
    """
    head = pr.get("headRefName", "")
    if pr.get("baseRefName") != base:
        return False, f"base={pr.get('baseRefName')}≠{base}"
    if pr.get("isDraft"):
        return False, "draft"
    title = pr.get("title", "")
    if HOLD_MARKERS.search(title):
        return False, "hold-marker in title"
    if not _matches_pattern(head, patterns):
        return False, f"head '{_sanitize(head)}' not an agent-branch pattern"
    # Fork rejection (S3): never auto-merge a cross-repository (fork) PR.
    if pr.get("isCrossRepository"):
        return False, "fork PR (isCrossRepository)"
    # Author allowlist (S1): only merge trusted-author PRs by default.
    if authors is not None:
        login = _login_of(pr.get("author"))
        if login not in authors:
            return False, f"author {login or '?'} not in allowlist"
    mergeable = pr.get("mergeable")
    if mergeable != READY_MERGEABLE:
        return False, f"mergeable={mergeable}"
    state = pr.get("mergeStateStatus")
    if state != READY_MERGE_STATE:
        # UNSTABLE = a required check failed or is pending → not ready yet.
        return False, f"mergeStateStatus={state}"
    return True, "ready (mergeable+CLEAN)"


def merge_pr(number: int) -> tuple[bool, str]:
    rc, out, err = _run(
        ["gh", "pr", "merge", str(number), "--squash", "--delete-branch"],
        timeout=90,
    )
    if rc == 0:
        return True, out or "merged"
    return False, _sanitize(err or out or f"rc={rc}")


def _resolve_authors(arg_authors: list[str] | None, any_author: bool) -> list[str] | None:
    """Decide the author allowlist. Returns None only for explicit --any-author."""
    if any_author:
        return None
    if arg_authors:
        return arg_authors
    env = os.environ.get("AUTO_MERGE_AUTHOR_ALLOWLIST", "").strip()
    if env:
        return [a.strip() for a in env.split(",") if a.strip()]
    login = current_gh_login()
    return [login] if login else []  # empty list → merges nothing (safe default)


def sweep(
    *,
    scope: str,
    execute: bool,
    base: str,
    patterns: list[str],
    authors: list[str] | None,
    max_merges: int,
) -> dict:
    result: dict = {
        "scope": scope,
        "execute": execute,
        "authors": authors,
        "merged": [],
        "skipped": [],
        "errors": [],
        "ready_dry_run": [],
    }
    if not gh_available():
        result["errors"].append("gh not available / not authenticated")
        return result
    if authors is not None and not authors:
        result["errors"].append(
            "no author allowlist resolved (gh login empty) — refusing to merge; "
            "set AUTO_MERGE_AUTHOR_ALLOWLIST or pass --author / --any-author"
        )
        return result

    prs, list_err = list_open_prs()
    if list_err:
        result["errors"].append(list_err)
    if scope == "current":
        br = current_branch()
        prs = [p for p in prs if p.get("headRefName") == br]
        result["current_branch"] = br

    merged_count = 0
    for pr in prs:
        num = pr.get("number")
        head = _sanitize(pr.get("headRefName", ""))
        ready, reason = classify(pr, base=base, patterns=patterns, authors=authors)
        if not ready:
            result["skipped"].append({"pr": num, "head": head, "why": reason})
            continue
        if not execute:
            result["ready_dry_run"].append({"pr": num, "head": head})
            continue
        if merged_count >= max_merges:
            result["skipped"].append({"pr": num, "head": head, "why": f"max={max_merges} reached"})
            continue
        ok, msg = merge_pr(num)
        if ok:
            result["merged"].append({"pr": num, "head": head})
            merged_count += 1
        else:
            result["errors"].append({"pr": num, "head": head, "why": msg})
    return result


def format_human(result: dict) -> str:
    lines = []
    mode = "EXECUTE" if result["execute"] else "DRY-RUN"
    auth = result.get("authors")
    auth_s = "any-author" if auth is None else ("allowlist=" + ",".join(auth))
    lines.append(f"[auto-merge-ready-prs] scope={result['scope']} mode={mode} {auth_s}")
    if result.get("current_branch") is not None:
        lines.append(f"  current branch: {result['current_branch'] or '(none)'}")
    for m in result["merged"]:
        lines.append(f"  ✅ merged #{m['pr']} {m['head']}")
    for r in result.get("ready_dry_run", []):
        lines.append(f"  ▶ ready (dry-run, not merged) #{r['pr']} {r['head']}")
    for s in result["skipped"]:
        lines.append(f"  – skip #{s['pr']} {s['head']}: {s['why']}")
    for e in result["errors"]:
        if isinstance(e, dict):
            lines.append(f"  ✗ error #{e['pr']} {e['head']}: {e['why']}")
        else:
            lines.append(f"  ✗ {e}")
    if not (result["merged"] or result.get("ready_dry_run") or result["skipped"]):
        lines.append("  (no open PRs in scope)")
    if result["merged"]:
        lines.append("  ℹ opt-out next time: add 'HOLD'/'черновик' to PR title " "OR export AUTO_MERGE_SWEEP_SKIP=1")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--scope",
        choices=["current", "all-own"],
        default="current",
        help="current = this branch's PR only; all-own = all agent-pattern PRs",
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="actually merge (default: dry-run)",
    )
    ap.add_argument("--base", default="main", help="required base branch")
    ap.add_argument(
        "--pattern",
        action="append",
        default=None,
        help="agent-branch glob (repeatable, REPLACES defaults). " "Default: pr-* claude/* ik-codex/*",
    )
    ap.add_argument(
        "--author",
        action="append",
        default=None,
        help="gh login allowed to auto-merge (repeatable). "
        "Default: resolved current gh login OR AUTO_MERGE_AUTHOR_ALLOWLIST",
    )
    ap.add_argument(
        "--any-author",
        action="store_true",
        help="DANGER: merge PRs from any author (off by default; S1 escape hatch)",
    )
    ap.add_argument("--max", type=int, default=DEFAULT_MAX, help="max merges/run")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on any error (default fail-open exit 0 for hooks)",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    patterns = args.pattern if args.pattern else list(DEFAULT_PATTERNS)
    authors = _resolve_authors(args.author, args.any_author)
    result = sweep(
        scope=args.scope,
        execute=args.execute,
        base=args.base,
        patterns=patterns,
        authors=authors,
        max_merges=args.max,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human(result))

    if args.strict and result["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
