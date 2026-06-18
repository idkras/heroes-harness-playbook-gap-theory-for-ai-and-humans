#!/usr/bin/env python3
"""
branch_name_bead_ref_check.py — PreToolUse Bash hook: проверка что новые ветки
содержат bead-id в name (per 9-statement validation 2026-05-24, statement #3).

Когда agent / тиммейт создаёт новую ветку без bead-id reference ИЛИ без
JTBD-self-describing slug в имени — hook BLOCK (Phase 2, RCA 2026-06-02).
Закрывает recurring class «branch/worktree без bead reference / без JTBD»
= невозможно сопоставить ветку с задачей (`pr-rick-c0vm` / `pr-rick-wwc`).

Канонические patterns (наш workspace):
  - pr-rick-<id> (например pr-rick-4eh, pr-rick-parallel-agents-coord)
  - bd-<id> или bd-<digits> (generic bd)
  - feature/bd-<id>-<slug>
  - bugfix/bd-<id>-<slug>
  - refactor/bd-<id>-<slug>
  - docs/bd-<id>-<slug>
  - integration/bd-<id>-<slug>
  - hotfix/bd-<id>-<slug>

Phase 2 (current, RCA 2026-06-02): BLOCK (exit 2). WARN-only (Phase 1) was
ignored because relying on the agent to read stderr and self-correct does not
work — `pr-rick-c0vm` recurred. Now mechanical.

Override: env BRANCH_NAME_BEAD_ACK="<reason ≥12 chars>" для legacy migration,
hotfix, experimental scratch branches.

Matcher patterns triggering:
  git checkout -b <new-branch>
  git switch -c <new-branch>
  git worktree add <path> -b <new-branch>

Exit codes:
  0 — pass (branch name matches convention OR rule N/A OR ACK override)
  2 — BLOCK (no bead-ref OR non-JTBD slug, no ACK) — active since 2026-06-02
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

# JTBD/bead reference patterns in branch names
BEAD_REF_PATTERNS = [
    re.compile(r"\bpr-rick-[a-z0-9]+\b"),  # pr-rick-4eh
    re.compile(r"\bbd-[a-z0-9]+\b"),  # bd-123, bd-abc
    re.compile(r"\b(?:feature|bugfix|refactor|docs|integration|hotfix|test|chore|migration|experiment)/bd-[a-z0-9]+\b"),
    re.compile(
        r"\b(?:feature|bugfix|refactor|docs|integration|hotfix|test|chore|migration|experiment)/pr-[a-z0-9-]+\b"
    ),
]

# RCA 2026-06-02 Stage-6 code-review: regex-over-raw-string parsing leaked the
# incident name through quoting (`-b 'pr-rick-c0vm'`), `-C`/`--create`, and
# `-t -b`, AND hard-blocked legit bare `git branch --contains`/backups. Replaced
# with shlex tokenisation scoped to INTENTIONAL feature-branch/worktree creation
# only (checkout -b/-B, switch -c/-C/--create, worktree add -b/-B). Bare
# `git branch <name>` is intentionally NOT covered — too ambiguous (read/list/
# backup/reset share the verb), high false-positive as a BLOCK.
_CREATE_FLAGS = {
    "checkout": {"-b", "-B"},
    "switch": {"-c", "-C", "--create"},
    "worktree": {"-b", "-B"},  # only when 'add' subcommand present
}

# A branch is exempt if its first path/hyphen segment is automation/scratch/
# protected (never bead-bound). RCA 2026-06-02 Stage-6: too-narrow allowlist
# false-blocked bisect/backup/revert/hotfix/dependabot. Segment match handles
# both slash (`backup/x`) and hyphen (`backup-x`) forms.
ALLOWLIST_SEGMENTS = {
    "main",
    "master",
    "production",
    "release",
    "develop",
    "claude",
    "wip",
    "tmp",
    "temp",
    "rescue",
    "scratch",
    "experiment",
    "backup",
    "bisect",
    "revert",
    "hotfix",
    "dependabot",
    "renovate",
}


def looks_exempt(branch_name: str) -> bool:
    """Return True if branch's first segment is in the allowlist."""
    if not branch_name:
        return True
    first = re.split(r"[/-]", branch_name, maxsplit=1)[0].lower()
    return first in ALLOWLIST_SEGMENTS


def has_bead_ref(branch_name: str) -> bool:
    """Return True if branch name contains a recognized bead reference pattern."""
    for pat in BEAD_REF_PATTERNS:
        if pat.search(branch_name):
            return True
    return False


# RCA 2026-05-26: semantic check beyond structural pattern. Branch name like
# `pr-rick-wwc` passes BEAD_REF_PATTERNS (matches `pr-rick-[a-z0-9]+`) but
# violates JTBD-self-describing principle because slug `wwc` is just a
# 3-char auto-id from `bd create`, conveys zero JTBD meaning. Owner steering
# 2026-05-26: «обрати внимание что worktree названо дурацки — должно
# отражать JTBD работу».
#
# Threshold: slug part (after `pr-rick-` or `bd-` prefix) must satisfy either
#   (a) length >= MIN_SLUG_CHARS (default 10), OR
#   (b) >= MIN_SLUG_HYPHENS (default 2) hyphens (e.g. `fix-luis-payload`)
# Date-suffix tokens (e.g. `-2026-05-26`) count as hyphens but NOT toward
# meaningful tokens — see _strip_date_suffix() heuristic.

MIN_SLUG_CHARS = int(os.environ.get("BRANCH_NAME_MIN_SLUG_CHARS", "10"))
MIN_SLUG_HYPHENS = int(os.environ.get("BRANCH_NAME_MIN_SLUG_HYPHENS", "2"))

# Slug-prefix patterns to strip when extracting "the meaningful part"
SLUG_PREFIX_PATTERNS = [
    re.compile(r"^pr-rick-"),
    re.compile(r"^bd-"),
    re.compile(r"^(?:feature|bugfix|refactor|docs|integration|hotfix|test|chore|" r"migration|experiment)/(?:bd-|pr-)"),
]

# Date suffix (YYYY-MM-DD) — strip before counting meaningful hyphens
DATE_SUFFIX_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def _extract_slug(branch_name: str) -> str:
    """Extract slug part (after pr-rick-/bd- prefix). Empty if no prefix match."""
    for pat in SLUG_PREFIX_PATTERNS:
        m = pat.match(branch_name)
        if m:
            return branch_name[m.end() :]
    return ""


def slug_is_jtbd_self_describing(branch_name: str) -> bool:
    """Return True if slug satisfies JTBD-self-describing threshold.

    RCA 2026-05-26: `pr-rick-wwc` slug=`wwc` len=3 hyphens=0 → False.
    `pr-rick-luis-funnel-mapping` slug=`luis-funnel-mapping` len=19 → True.
    `pr-rick-fix-luis-x` slug=`fix-luis-x` hyphens=2 → True (passes by hyphens).
    `pr-rick-events-canonical-ivan-spec-2026-05-26` slug after date strip =
    `events-canonical-ivan-spec` hyphens=3 → True.
    """
    slug = _extract_slug(branch_name)
    if not slug:
        # No prefix matched — irrelevant to this check (caller already
        # handled structural pattern via has_bead_ref). Treat as N/A → True.
        return True
    # Strip date suffix to avoid double-counting `-2026-05-26` as meaningful tokens
    slug_for_count = DATE_SUFFIX_RE.sub("", slug)
    if len(slug_for_count) >= MIN_SLUG_CHARS:
        return True
    n_hyphens = slug_for_count.count("-")
    return n_hyphens >= MIN_SLUG_HYPHENS


def _segment_branch_name(tokens: list[str]) -> str | None:
    """Given shlex tokens of ONE command segment, return the NEW branch name
    being created (checkout -b/-B, switch -c/-C/--create, worktree add -b/-B),
    or None. Flags may appear in any order; quotes are already resolved by shlex.
    A subcommand without its create-flag (e.g. `git checkout main`,
    `git worktree add <path> <existing-branch>`) returns None — not creation."""
    if not tokens or "git" not in tokens:
        return None
    sub = next((t for t in tokens if t in ("checkout", "switch", "worktree")), None)
    if sub is None:
        return None
    if sub == "worktree" and "add" not in tokens:
        return None
    flags = _CREATE_FLAGS[sub]
    for i, t in enumerate(tokens):
        if t in flags and i + 1 < len(tokens):
            cand = tokens[i + 1]
            if cand and not cand.startswith("-"):
                return cand
    return None


def extract_new_branch_names(command: str) -> list[str]:
    """Parse Bash command (incl. compound `a && b`) → new-branch names created."""
    names: list[str] = []
    for seg in re.split(r"&&|\|\||[;|&\n]", command):
        seg = seg.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg, comments=False, posix=True)
        except ValueError:
            tokens = seg.split()
        name = _segment_branch_name(tokens)
        if name:
            names.append(name)
    return names


# RCA 2026-06-01 (merged from #258) — `bd create` bead-id == jtbd slug invariant.
# Kept WARN-only (advisory) — distinct from the branch-name BLOCK.
BD_CREATE_RE = re.compile(r"\bbd\s+create\b")
BD_CREATE_ID_RE = re.compile(r"--id[=\s]+['\"]?([\w./-]+)")


def _bd_create_warn(command: str) -> str | None:
    """Return a WARN string if `bd create` mints a non-jtbd id; else None."""
    if not BD_CREATE_RE.search(command):
        return None
    m = BD_CREATE_ID_RE.search(command)
    if not m:
        return (
            "bd-create-id: WARN — `bd create` без `--id` минтит opaque auto-id "
            "(mtf7 / wwc / 4eh) → bead-id ≠ jtbd slug ≠ branch ≠ folder.\n"
            'Canonical: bd create --id=pr-rick-<jtbd-slug> --title="..." --type=task\n'
            "(slug ≥10 chars OR ≥2 hyphens). Override: BRANCH_NAME_BEAD_ACK (≥12 chars)."
        )
    bead_id = m.group(1)
    if has_bead_ref(bead_id) and not slug_is_jtbd_self_describing(bead_id):
        return (
            f"bd-create-id: WARN — `bd create --id={bead_id}` slug не JTBD-self-describing "
            "(<10 chars И <2 hyphens). bead-id == branch == folder == jtbd slug.\n"
            "Override: BRANCH_NAME_BEAD_ACK (≥12 chars)."
        )
    return None


def main() -> int:
    # Read PreToolUse JSON payload from stdin
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # fail-open on malformed payload

    tool_name = payload.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    tool_input = payload.get("tool_input", {})
    command = str(tool_input.get("command", ""))
    if not command:
        return 0

    ack = os.environ.get("BRANCH_NAME_BEAD_ACK", "").strip()
    # bd-create bead-id==jtbd advisory (WARN-only, merged from #258).
    bd_warn = _bd_create_warn(command)
    if bd_warn and not (ack and len(ack) >= 12):
        print(bd_warn, file=sys.stderr)

    # Quick reject: if no branch-creation subcommand present, skip work
    if not any(k in command for k in ("checkout", "switch", "worktree")):
        return 0

    new_branches = extract_new_branch_names(command)
    if not new_branches:
        return 0

    # Filter out exempt names; split flagged into 2 classes
    flagged_structural: list[str] = []  # No bead-id ref at all
    flagged_short_slug: list[str] = []  # Has ref but slug fails JTBD-self-describing check
    for name in new_branches:
        if looks_exempt(name):
            continue
        if not has_bead_ref(name):
            flagged_structural.append(name)
            continue
        # Structural pass — check semantic (RCA 2026-05-26)
        if not slug_is_jtbd_self_describing(name):
            flagged_short_slug.append(name)

    flagged = flagged_structural + flagged_short_slug
    if not flagged:
        return 0

    # Override check
    ack = os.environ.get("BRANCH_NAME_BEAD_ACK", "").strip()
    if ack and len(ack) >= 12:
        print(
            f"branch-name-bead-ref: PASS (override BRANCH_NAME_BEAD_ACK active: {ack[:40]}...)\n"
            f"  flagged branches: {', '.join(flagged)}",
            file=sys.stderr,
        )
        return 0

    # Phase 2: BLOCK (exit 2). RCA 2026-06-02: `pr-rick-c0vm` recurrence —
    # the agent created a worktree named after the bead auto-id `c0vm` (not a
    # JTBD slug) and got NO feedback because this hook was (a) WARN-only and
    # (b) fully dormant (absent from registry events AND live settings.json).
    # Owner: «bead = worktree = jtbd, ты опять совершил ошибку». WARN-only
    # relied on the agent reading stderr and self-correcting — it did not.
    # Escalated to BLOCK with the same ACK override.
    structural_str = ", ".join(flagged_structural) if flagged_structural else "—"
    short_slug_str = ", ".join(flagged_short_slug) if flagged_short_slug else "—"
    print(
        "branch-name-bead-ref: BLOCK (Phase 2) — branch/worktree name(s) violate convention:\n"
        f"  no bead-ref (structural):    {structural_str}\n"
        f"  short slug (semantic, JTBD): {short_slug_str}\n"
        "\n"
        "Required convention (AGENTS.md §«Default protocol», RCA 2026-05-24 + RCA 2026-05-26):\n"
        "  ✅ pr-rick-<jtbd-slug>          slug ≥10 chars OR ≥2 hyphens\n"
        "                                  e.g. pr-rick-luis-funnel-mapping-rick-exchange\n"
        "  ✅ pr-rick-<jtbd-slug>-<bead-id> slug + traceability\n"
        "                                  e.g. pr-rick-luis-funnel-mapping-wwc\n"
        "  ✅ feature/bd-<id>-<slug>        (e.g. feature/bd-123-auth-empty-state)\n"
        "  ✅ bugfix/bd-<id>-<slug>\n"
        "  ✅ refactor/bd-<id>-<slug>\n"
        "  ✅ docs/bd-<id>-<slug>\n"
        "\n"
        "Allowlist (no flag): main, master, production, release, claude/*, wip/*, tmp/*, rescue/*.\n"
        "\n"
        "Anti-patterns (RCA 2026-05-26): pr-rick-wwc / pr-rick-4eh / pr-rick-task — pure auto-id\n"
        "от `bd create` без JTBD slug. Owner steering 2026-05-26: «обрати внимание что worktree\n"
        "названо дурацки — должно отражать JTBD работу и outcome».\n"
        "\n"
        "Naming derivation: read bead title через `bd show <id>` → extract 3-5 JTBD tokens →\n"
        "compose `pr-rick-<slug>-<bead-id>` (slug + traceability). Verify: teammate без bd CLI\n"
        "должен понять что branch делает за 5 секунд.\n"
        "\n"
        "Why this matters: branch без bead-id ИЛИ без JTBD slug невозможно сопоставить с задачей\n"
        "при `bd ready`/`git branch`, ломает coordination 3+ параллельных агентов. JTBD title\n"
        "formula `Когда ..., хотим ...` в title + JTBD slug в branch name = 5-секундное\n"
        "понимание задачи (owner steering 2026-05-24 + 2026-05-26: «читаемость #1»).\n"
        "\n"
        "Fix: rename the worktree/branch/bead to a JTBD slug, e.g.\n"
        "  git branch -m pr-rick-c0vm pr-rick-<jtbd-slug>-c0vm   # keep bead-id as suffix\n"
        "  git worktree move <old> .claude/worktrees/pr-rick-<jtbd-slug>-c0vm\n"
        "\n"
        'Override (use sparingly): export BRANCH_NAME_BEAD_ACK="<reason ≥12 chars>"\n'
        "  examples: «hotfix-emergency-revert-no-bead-needed», «scratch-experimental-spike».",
        file=sys.stderr,
    )
    return 2  # Phase 2: BLOCK (RCA 2026-06-02 pr-rick-c0vm recurrence)


if __name__ == "__main__":
    sys.exit(main())
