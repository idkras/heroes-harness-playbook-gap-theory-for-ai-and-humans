#!/usr/bin/env python3
"""pr_bead_jtbd_ref_check — project-name continuity guard.

Mechanical contract for new project/chat work:
  JTBD title in bead -> derived project slug -> branch -> worktree -> PR title.

This is stronger than "branch contains a bead ref". The name must carry the
same project meaning, not just an opaque id. Override:
`JTBD_PROJECT_NAMING_ACK=<reason >=12 chars>`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ACK_ENV = "JTBD_PROJECT_NAMING_ACK"
ACK_MIN_CHARS = 12
ACK_VALID = re.compile(r"^(?=.{12,})(?=.*[A-Za-z]{3,}).+[\s\-_:]+.+$")
JTBD_WHEN_RE = re.compile(r"\b(когда|when)\b", re.IGNORECASE)
JTBD_WANT_RE = re.compile(r"\b(хотим|хочу|нужно|надо|want|need)\b", re.IGNORECASE)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".claude" / "hooks").is_dir() and (parent / "scripts").is_dir():
            return parent
    return here.parents[2]


ROOT = _repo_root()


def _load_module(rel: str, name: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


BRANCH_GATE = _load_module(".claude/hooks/branch_name_bead_ref_check.py", "_branch_name_bead_ref_check")
MAKE_WORKTREE = _load_module("scripts/make_worktree.py", "_make_worktree")


def _run(args: list[str], cwd: str | None = None) -> str:
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=8, check=False)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _segments(command: str) -> list[list[str]]:
    out: list[list[str]] = []
    for seg in re.split(r"&&|\|\||[;|\n]", command):
        seg = seg.strip()
        if not seg:
            continue
        try:
            out.append(shlex.split(seg, comments=False, posix=True))
        except ValueError:
            out.append(seg.split())
    return out


def _flag_value(tokens: list[str], *names: str) -> str:
    for i, tok in enumerate(tokens):
        for name in names:
            if tok == name and i + 1 < len(tokens):
                return tokens[i + 1]
            if tok.startswith(f"{name}="):
                return tok.split("=", 1)[1]
    return ""


def _current_branch(cwd: str | None = None) -> str:
    if os.environ.get("PR_BEAD_TEST_CURRENT_BRANCH"):
        return os.environ["PR_BEAD_TEST_CURRENT_BRANCH"]
    return _run(["git", "symbolic-ref", "--short", "-q", "HEAD"], cwd=cwd)


def _normalize_head(raw: str) -> str:
    return raw.rsplit(":", 1)[-1].strip() if ":" in raw else raw.strip()


def _title_looks_jtbd(title: str) -> bool:
    return bool(JTBD_WHEN_RE.search(title) and JTBD_WANT_RE.search(title))


def _slug_tokens(slug: str) -> list[str]:
    return [t for t in slug.split("-") if t and not re.fullmatch(r"[a-z0-9]{3,5}", t)]


def _title_slug(title: str) -> str:
    slug = MAKE_WORKTREE.derive_slug(title)
    if not BRANCH_GATE.slug_is_jtbd_self_describing(f"pr-rick-{slug}"):
        slug = MAKE_WORKTREE.derive_slug(title, keep_stopwords=True)
    return slug


def _short_id(bead_id: str) -> str:
    return MAKE_WORKTREE.short_bead_id(bead_id)


def _beads_file() -> Path:
    test_path = os.environ.get("JTBD_PROJECT_NAMING_TEST_BEADS")
    return Path(test_path) if test_path else ROOT / ".beads" / "issues.jsonl"


def _load_beads() -> list[dict]:
    path = _beads_file()
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _resolve_bead(branch: str) -> dict | None:
    beads = _load_beads()
    for bead in beads:
        bid = str(bead.get("id") or "")
        if not bid:
            continue
        sid = _short_id(bid)
        if branch == bid or bid in branch or (sid and branch.endswith(f"-{sid}")):
            return bead
    return None


def _project_slug_from_branch(branch: str, bead_id: str = "") -> str:
    slug = branch
    if slug.startswith("pr-rick-"):
        slug = slug[len("pr-rick-") :]
    if bead_id:
        sid = _short_id(bead_id)
        if sid and slug.endswith(f"-{sid}"):
            slug = slug[: -(len(sid) + 1)]
    return slug.strip("-")


def _slug_reflects_title(project_slug: str, title: str) -> bool:
    expected = _title_slug(title)
    if not project_slug or not expected:
        return False
    if project_slug == expected or project_slug.startswith(expected) or expected.startswith(project_slug):
        return True
    expected_tokens = _slug_tokens(expected)
    project_tokens = set(_slug_tokens(project_slug))
    needed = min(2, len(expected_tokens))
    return needed > 0 and sum(1 for t in expected_tokens if t in project_tokens) >= needed


def _title_reflects_project(title: str, project_slug: str) -> bool:
    if not _title_looks_jtbd(title):
        return False
    return _slug_reflects_title(project_slug, title)


def _worktree_add_path(tokens: list[str]) -> str:
    try:
        idx = tokens.index("add") + 1
    except ValueError:
        return ""
    skip_next = False
    for tok in tokens[idx:]:
        if skip_next:
            skip_next = False
            continue
        if tok in {"-b", "-B"}:
            skip_next = True
            continue
        if tok.startswith("-"):
            continue
        return tok
    return ""


def _new_branch(tokens: list[str]) -> tuple[str, str]:
    # Returns (branch, worktree_path). path is non-empty only for worktree add.
    if not tokens or "git" not in tokens:
        return "", ""
    if "worktree" in tokens and "add" in tokens:
        branch = _flag_value(tokens, "-b", "-B")
        return branch, _worktree_add_path(tokens)
    if "checkout" in tokens:
        return _flag_value(tokens, "-b", "-B"), ""
    if "switch" in tokens:
        return _flag_value(tokens, "-c", "-C", "--create"), ""
    return "", ""


def _is_bd_create(tokens: list[str]) -> bool:
    return len(tokens) >= 2 and tokens[0] == "bd" and tokens[1] == "create"


def _is_gh_pr_create(tokens: list[str]) -> bool:
    return len(tokens) >= 3 and tokens[0] == "gh" and tokens[1] == "pr" and tokens[2] == "create"


def _block(command: str, reason: str, canonical: str) -> int:
    sys.stderr.write(
        "\n[jtbd-project-naming] BLOCK — project name must stay continuous: "
        "JTBD bead title -> branch/worktree -> PR.\n\n"
        f"  command: {command[:240]}{'...' if len(command) > 240 else ''}\n"
        f"  reason: {reason}\n\n"
        f"Canonical:\n{canonical}\n\n"
        f"Override (legacy/manual exception, real reason >= {ACK_MIN_CHARS} chars):\n"
        f'  {ACK_ENV}="reason: ..." <command>\n'
    )
    return 2


def _check_bd_create(tokens: list[str], command: str) -> int:
    title = _flag_value(tokens, "--title", "-t")
    if not title:
        return _block(
            command,
            "bd create must include --title on JTBD language",
            '  bd create --title="Когда ..., хотим ..., чтобы ..." --type=task',
        )
    if not _title_looks_jtbd(title):
        return _block(
            command,
            f"bead title is not JTBD-shaped: `{title}`",
            '  bd create --title="Когда ..., хотим ..., чтобы ..." --type=task',
        )
    return 0


def _check_branch(branch: str, path: str, command: str, *, strict: bool = False) -> int:
    branch = _normalize_head(branch)
    if not branch:
        return (
            _block(command, "PR/worktree branch is missing", "  make worktree BEAD=<bead-id> CLAIM=1") if strict else 0
        )
    if BRANCH_GATE.looks_exempt(branch):
        return 0
    if not BRANCH_GATE.has_bead_ref(branch) or not BRANCH_GATE.slug_is_jtbd_self_describing(branch):
        if strict:
            return _block(command, f"branch `{branch}` is not a JTBD/bead branch", "  pr-rick-<jtbd-slug>-<bead-id>")
        return 0  # branch_name_bead_ref_check blocks branch creation; avoid duplicate verdicts.
    bead = _resolve_bead(branch)
    if not bead:
        return _block(
            command,
            f"branch `{branch}` has no matching bead id in .beads/issues.jsonl",
            "  make worktree BEAD=<bead-id> CLAIM=1",
        )
    title = str(bead.get("title") or "")
    if not _title_looks_jtbd(title):
        return _block(
            command,
            f"matching bead `{bead.get('id')}` title is not JTBD-shaped: `{title}`",
            '  bd update <bead-id> --title="Когда ..., хотим ..., чтобы ..."',
        )
    project_slug = _project_slug_from_branch(branch, str(bead.get("id") or ""))
    if not _slug_reflects_title(project_slug, title):
        expected = _title_slug(title)
        return _block(
            command,
            f"branch project slug `{project_slug}` does not reflect bead title slug `{expected}`",
            "  make worktree BEAD=<bead-id> CLAIM=1  # derives pr-rick-<jtbd-slug>-<bead-id>",
        )
    if path:
        basename = Path(path).name
        if basename != branch:
            return _block(
                command,
                f"worktree folder `{basename}` must equal branch `{branch}`",
                "  git worktree add .claude/worktrees/<branch> -b <branch> origin/main",
            )
    return 0


def _check_pr(tokens: list[str], command: str, cwd: str) -> int:
    head = _normalize_head(_flag_value(tokens, "--head", "-H") or _current_branch(cwd))
    rc = _check_branch(head, "", command, strict=True)
    if rc:
        return rc
    bead = _resolve_bead(head)
    if not bead:
        return 0
    project_slug = _project_slug_from_branch(head, str(bead.get("id") or ""))
    title = _flag_value(tokens, "--title", "-t")
    if not title or "--fill" in tokens or "--fill-first" in tokens or "--fill-verbose" in tokens:
        return _block(
            command,
            "PR must pass an explicit JTBD --title, not rely on --fill/editor defaults",
            '  gh pr create --head <branch> --base main --title="Когда ..., хотим ..., чтобы ..."',
        )
    if not _title_reflects_project(title, project_slug):
        return _block(
            command,
            f"PR title does not use JTBD language or does not reflect project slug `{project_slug}`",
            '  gh pr create --title="Когда ..., хотим ..., чтобы ..." ...',
        )
    return 0


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if (payload.get("tool_name") or payload.get("toolName")) != "Bash":
        return 0
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    command = str(tool_input.get("command") or "")
    if not command:
        return 0
    ack = os.environ.get(ACK_ENV, "").strip()
    if ack and ACK_VALID.match(ack):
        sys.stderr.write(f"jtbd-project-naming: ACK present ({ACK_ENV}), proceeding.\n")
        return 0
    cwd = tool_input.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or str(ROOT)
    for tokens in _segments(command):
        if _is_bd_create(tokens):
            rc = _check_bd_create(tokens, command)
        elif _is_gh_pr_create(tokens):
            rc = _check_pr(tokens, command, cwd)
        else:
            branch, path = _new_branch(tokens)
            rc = _check_branch(branch, path, command) if branch else 0
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        sys.stderr.write(f"jtbd-project-naming: internal error: {exc}\n")
        sys.exit(0)
