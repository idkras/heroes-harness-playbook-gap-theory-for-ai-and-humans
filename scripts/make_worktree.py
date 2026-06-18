#!/usr/bin/env python3
r"""make_worktree.py — generate a JTBD-self-describing worktree from a bead.

THE SOURCE AFFORDANCE for the branch-name JTBD gate.

RCA 2026-06-02 (design-art-director on PR #275 — «enforcement without
affordance»): `branch_name_bead_ref_check.py` now BLOCKS worktree/branch names
whose slug is a bare `bd create` auto-id (e.g. `pr-rick-7ms7`), demanding a
JTBD-self-describing slug (≥10 chars OR ≥2 hyphens after the `pr-rick-`/`bd-`
prefix). But nothing HELPED the agent derive that slug — they had to hand-craft
it from the very auto-id the gate rejects. A gate with no source generator is a
wall with no door.

This script is the door. Given a bead id it:
  1. reads the bead TITLE via `bd show <id> --json`,
  2. derives a slug from the title (transliterate Cyrillic → Latin, drop
     JTBD-formula + stop words, keep 3-5 content tokens),
  3. composes `pr-rick-<slug>-<bead-short-id>` and VERIFIES it against the gate's
     own `slug_is_jtbd_self_describing` predicate (imported — single source of
     truth, no drift), relaxing the slug if a sparse title under-fills it,
  4. runs `git worktree add <path> -b <name> <base>` with a FULL checkout — never
     `--no-checkout`/`--sparse`/`--orphan` (respects git_worktree_completeness_gate,
     PR #270),
  5. verifies completeness (`ls-files` ≈ `ls-tree HEAD`) and prints the next
     steps (`cd`, `bd update --claim`).

So the gate becomes a backstop, not the only line.

Universal: no client/project hardcodes. Works in any git repo with a `.beads` db.

Usage:
    python3 scripts/make_worktree.py <bead-id> [--slug SLUG] [--base REF]
                                     [--dry-run] [--claim] [--json]
    BEAD=pr-rick-7ms7 python3 scripts/make_worktree.py
    make worktree BEAD=pr-rick-7ms7

Exit codes:
  0 — worktree created (or dry-run printed) successfully
  1 — error (bead not found, git failure, completeness check failed)
  2 — usage error (no bead id)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── repo root discovery ──────────────────────────────────────────────────────


def _find_repo_root(start: Path | None = None) -> Path:
    """Walk up until a dir with both .claude/hooks and scripts (the repo root).

    Works from inside a worktree too: a worktree has its own .claude/ + scripts/
    materialised by the full checkout, so the nearest ancestor with both is the
    worktree root, which is exactly where we want to resolve the gate predicate.
    """
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".claude" / "hooks").is_dir() and (parent / "scripts").is_dir():
            return parent
    # Fallback: parent of scripts/
    return Path(__file__).resolve().parent.parent


REPO_ROOT = _find_repo_root()
WORKTREE_DIR_DEFAULT = ".claude/worktrees"


def _main_worktree_root() -> Path:
    """Return the PRIMARY worktree root (where .claude/worktrees/ should live).

    `git rev-parse --git-common-dir` points at the shared `<main>/.git`; its
    parent is the main worktree. This keeps `make worktree` from nesting a new
    worktree inside the current one when invoked from inside a worktree.
    Falls back to REPO_ROOT if git is unavailable.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if out:
            common = Path(out)
            if not common.is_absolute():
                common = (REPO_ROOT / common).resolve()
            # <main>/.git → parent is the main worktree root
            return common.parent if common.name == ".git" else common
    except Exception:
        pass
    return REPO_ROOT


DEFAULT_BASE = os.environ.get("MAKE_WORKTREE_BASE", "origin/main")
MAX_TOKENS = int(os.environ.get("MAKE_WORKTREE_MAX_TOKENS", "5"))

# ── perf subtask seed (pr-rick-nbdl, RCA 2026-06-14) ─────────────────────────
# Owner directive: «когда мы делаем beads/worktree/проекты — ВСЕГДА авто-включать
# подзадачу профилирование+ускорение+улучшение скриптов и тестов». make_worktree
# is the canonical creation door (§Branch-and-bead-first-touch), so it seeds the
# default profiling subtask into the bead — wire-existing (Path B, auditor 78% vs
# Path A 12%), NOT a new framework. Written in the canonical
# `when → output → outcome` form so bead_progress_tree.py renders it for the owner.
PERF_SUBTASK_LINE = (
    "- [ ] when трогаем скрипт/тест/скил в этой задаче "
    "→ output профайл-замер baseline+after (pyinstrument/hyperfine/time) "
    "→ outcome ускорение или вывод «уже оптимально» + тесты не медленнее baseline"
)
# Idempotency: only a profiling keyword inside an ACTUAL checklist item counts as
# "already present" — a prose mention in the description (the bead title itself may
# say "профилирование") must NOT suppress the seed (RCA 2026-06-14 falsification:
# loose desc-wide match left pr-rick-nbdl with zero seeded subtasks).
_PERF_KEYWORD_RE = re.compile(r"(?i)(профил|profil|профайл|benchmark|pyinstrument|hyperfine)")
_CHECKLIST_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX~!]\]\s*(?P<body>.+)$")


def _perf_subtask_present(description: str) -> bool:
    """True iff a CHECKLIST line (not prose) mentions profiling."""
    for line in (description or "").splitlines():
        m = _CHECKLIST_LINE_RE.match(line)
        if m and _PERF_KEYWORD_RE.search(m.group("body")):
            return True
    return False


# ── gate predicate (single source of truth) ─────────────────────────────────


def _load_gate_predicate():
    """Import slug_is_jtbd_self_describing from the gate hook (SSOT).

    Returns the function, or a faithful local fallback if the hook is absent
    (keeps the generator usable in a stripped checkout). The fallback mirrors
    branch_name_bead_ref_check.py exactly: slug = part after pr-rick-/bd- prefix
    (date suffix stripped); PASS if len ≥ MIN_SLUG_CHARS OR hyphens ≥ MIN_SLUG_HYPHENS.
    """
    hook_path = REPO_ROOT / ".claude" / "hooks" / "branch_name_bead_ref_check.py"
    if hook_path.is_file():
        try:
            spec = importlib.util.spec_from_file_location("_branch_name_bead_ref_check", hook_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod.slug_is_jtbd_self_describing
        except Exception:
            pass

    # Local fallback — mirror the gate constants/logic.
    min_chars = int(os.environ.get("BRANCH_NAME_MIN_SLUG_CHARS", "10"))
    min_hyphens = int(os.environ.get("BRANCH_NAME_MIN_SLUG_HYPHENS", "2"))
    prefix_re = [
        re.compile(r"^pr-rick-"),
        re.compile(r"^bd-"),
        re.compile(
            r"^(?:feature|bugfix|refactor|docs|integration|hotfix|test|chore|" r"migration|experiment)/(?:bd-|pr-)"
        ),
    ]
    date_re = re.compile(r"-\d{4}-\d{2}-\d{2}$")

    def _fallback(branch_name: str) -> bool:
        slug = ""
        for pat in prefix_re:
            m = pat.match(branch_name)
            if m:
                slug = branch_name[m.end() :]
                break
        if not slug:
            return True
        slug_for_count = date_re.sub("", slug)
        if len(slug_for_count) >= min_chars:
            return True
        return slug_for_count.count("-") >= min_hyphens

    return _fallback


slug_is_jtbd_self_describing = _load_gate_predicate()

# ── transliteration + slug derivation ────────────────────────────────────────

# Cyrillic → Latin (lowercase). Common practical scheme (GOST-ish, readable).
_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    # Ukrainian/extras occasionally seen in titles
    "і": "i",
    "ї": "yi",
    "є": "ye",
    "ґ": "g",
}

# Words carrying no JTBD signal: the «Когда …, хотим …, чтобы …» formula glue,
# plus generic RU/EN stop words and bare-verb noise. Stored in their
# TRANSLITERATED lowercase form (what they look like after transliterate()).
_STOPWORDS = {
    # JTBD formula glue (RU, transliterated)
    "kogda",
    "hotim",
    "chtoby",
    "hochu",
    "nuzhno",
    "nado",
    # JTBD formula glue (EN)
    "when",
    "want",
    "so",
    "that",
    "need",
    "should",
    # RU generic stop words (transliterated)
    "i",
    "v",
    "vo",
    "na",
    "s",
    "so",
    "k",
    "ko",
    "po",
    "za",
    "iz",
    "ot",
    "dlya",
    "kak",
    "chto",
    "eto",
    "ne",
    "no",
    "a",
    "ili",
    "u",
    "o",
    "ob",
    "byl",
    "byla",
    "bylo",
    "est",
    "uzhe",
    "tot",
    "ego",
    "ih",
    "ee",
    "ego",
    # EN generic stop words
    "the",
    "a",
    "an",
    "to",
    "of",
    "in",
    "on",
    "for",
    "and",
    "or",
    "is",
    "are",
    "be",
    "we",
    "it",
    "as",
    "at",
    "by",
    "with",
    "this",
    # bare-verb noise (avoid pr-rick-fix / pr-rick-update anti-pattern)
    "fix",
    "update",
    "add",
    "make",
    "do",
    "set",
    "run",
    "use",
}


def transliterate(text: str) -> str:
    """Transliterate Cyrillic to Latin; pass through ASCII; lowercase."""
    out = []
    for ch in text.lower():
        out.append(_TRANSLIT.get(ch, ch))
    return "".join(out)


def _tokenize(title: str) -> list[str]:
    """Lowercase, transliterate, split on any non-[a-z0-9] run → token list."""
    latin = transliterate(title)
    return [t for t in re.split(r"[^a-z0-9]+", latin) if t]


def derive_slug(title: str, max_tokens: int = MAX_TOKENS, keep_stopwords: bool = False) -> str:
    """Derive a kebab-case JTBD slug from a (possibly Cyrillic) bead title.

    - transliterate Cyrillic → Latin,
    - split into tokens, drop stop / JTBD-formula / bare-verb words
      (unless keep_stopwords — used by the relaxation path),
    - keep the first `max_tokens` content tokens, join with '-'.

    Returns '' for an empty/all-stopword title (compose() then relaxes).
    """
    tokens = _tokenize(title)
    if not keep_stopwords:
        content = [t for t in tokens if t not in _STOPWORDS]
        # If stripping removed everything, fall back to raw tokens so a title
        # made only of stop words ("The FAQ") still yields a slug.
        tokens = content or tokens
    # Dedup while preserving order (a title repeating "worktree" twice should
    # not yield "...-worktree-worktree-...").
    seen: set[str] = set()
    deduped = [t for t in tokens if not (t in seen or seen.add(t))]
    return "-".join(deduped[:max_tokens])


def short_bead_id(bead_id: str) -> str:
    """Strip the pr-rick-/bd-/type prefix → the bare trailing id for traceability.

    pr-rick-7ms7 → 7ms7 ; bd-123 → 123 ; feature/bd-9-x → 9-x ; 7ms7 → 7ms7.
    """
    s = bead_id.strip()
    s = re.sub(r"^(?:feature|bugfix|refactor|docs|integration|hotfix|test|chore|" r"migration|experiment)/", "", s)
    s = re.sub(r"^pr-rick-", "", s)
    s = re.sub(r"^bd-", "", s)
    return s or bead_id.strip()


def compose_branch_name(title: str, bead_id: str, slug_override: str | None = None) -> str:
    """Compose `pr-rick-<slug>-<bead-short-id>`, guaranteed to pass the gate
    predicate for any title with real content tokens.

    Relaxation ladder if a sparse title under-fills the slug:
      1. content tokens (≤max),
      2. + previously-dropped stop words (keep_stopwords),
      3. as a last resort the bead-short-id alone still gives traceability.
    Each rung is checked against slug_is_jtbd_self_describing; the first PASS wins.
    """
    short = short_bead_id(bead_id)

    candidates: list[str] = []
    if slug_override:
        candidates.append(_slugify_raw(slug_override))
    candidates.append(derive_slug(title))
    candidates.append(derive_slug(title, max_tokens=MAX_TOKENS + 3))
    candidates.append(derive_slug(title, max_tokens=MAX_TOKENS + 3, keep_stopwords=True))

    for slug in candidates:
        slug = slug.strip("-")
        if not slug:
            continue
        name = f"pr-rick-{slug}-{short}"
        if slug_is_jtbd_self_describing(name):
            return name

    # Last resort: best non-empty slug we have, else bead-short only. May not
    # satisfy the gate for a truly degenerate one-tiny-word title — surface,
    # don't fake.
    best = next((s.strip("-") for s in candidates if s.strip("-")), "")
    return f"pr-rick-{best}-{short}".replace("--", "-").strip("-") if best else f"pr-rick-{short}"


def _slugify_raw(text: str) -> str:
    """Slugify a user-supplied override (transliterate + kebab, no stop-strip)."""
    return "-".join(_tokenize(text))


# ── git operations ───────────────────────────────────────────────────────────


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=check)


def read_bead_title(bead_id: str) -> str:
    """Read the bead title via `bd show <id> --json`. Raises on not-found."""
    try:
        proc = _run(["bd", "show", bead_id, "--json"], cwd=REPO_ROOT, check=True)
    except FileNotFoundError as e:  # bd not installed
        raise RuntimeError("bd CLI not found on PATH — install beads (make install-beads)") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"bd show {bead_id} failed: {e.stderr.strip() or e.stdout.strip()}") from e
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"could not parse `bd show {bead_id} --json` output") from e
    items = data if isinstance(data, list) else [data]
    if not items:
        raise RuntimeError(f"bead {bead_id} not found")
    title = (items[0].get("title") or "").strip()
    if not title:
        raise RuntimeError(f"bead {bead_id} has an empty title — cannot derive a slug")
    return title


def title_is_jtbd_scenario(title: str) -> bool:
    """True if the bead title is a JTBD scenario, not a bare task label.

    Owner directive 2026-06-05: `make worktree` must REQUIRE a JTBD scenario on
    input, not just a long-enough slug. A title like "fix login bug" passes the
    slug gate (≥2 hyphens) but is NOT a JTBD scenario — it states an output, not
    «когда {триггер}, хотим {действие}, чтобы {outcome}».

    Accepts RU «когда … хотим/хочу/чтобы …» OR EN «when … want/so that …».
    Case-insensitive. The two markers must both be present (trigger + intent).
    """
    t = title.lower()
    ru = ("когда" in t) and any(m in t for m in ("хотим", "хочу", "чтобы", "хотел"))
    en = ("when" in t) and any(m in t for m in ("want", "so that", "so we", "need to"))
    return ru or en


def _build_seeded_description(description: str) -> str:
    """Return description with the canonical perf subtask appended.

    - if a `Sub-tasks:` / `Подзадачи:` header exists, append the line right after
      the last checklist item under it (kept simple: append to end of the block);
    - else add a `Sub-tasks:` header + the line at the end of the description.
    Pure string fn — no I/O, unit-testable.
    """
    desc = description or ""
    header_re = re.compile(r"^\s*(?:sub-?tasks|подзадачи)\s*:\s*$", re.IGNORECASE | re.MULTILINE)
    if header_re.search(desc):
        # header present → append the line at the very end (renderer scans the
        # whole region after the header, so trailing position is fine)
        sep = "" if desc.endswith("\n") else "\n"
        return f"{desc}{sep}{PERF_SUBTASK_LINE}\n"
    sep = "" if desc.endswith("\n") or not desc else "\n"
    return f"{desc}{sep}\nSub-tasks:\n{PERF_SUBTASK_LINE}\n"


def ensure_perf_subtask(bead_id: str, *, bd_runner=None) -> dict:
    """Seed the canonical profiling subtask into the bead description (idempotent).

    Owner directive (pr-rick-nbdl): every bead/worktree/project must carry a
    profiling+speedup+test-improvement subtask. This is the mechanical seed at the
    worktree-creation door. bd_runner((cmd))->(rc,out) injectable for tests;
    default = real subprocess. Fail-open: any error → {seeded:False, reason}.
    Disabled via MAKE_WORKTREE_SEED_PERF_SUBTASK=0.
    """
    if os.environ.get("MAKE_WORKTREE_SEED_PERF_SUBTASK", "1").strip() == "0":
        return {"seeded": False, "reason": "disabled (MAKE_WORKTREE_SEED_PERF_SUBTASK=0)"}

    def _default_runner(cmd: list[str]) -> tuple[int, str]:
        try:
            p = _run(cmd, cwd=REPO_ROOT, check=False)
            return p.returncode, (p.stdout or "").strip()
        except Exception as e:  # pragma: no cover — fail-open
            return 1, str(e)

    run = bd_runner or _default_runner
    try:
        rc, out = run(["bd", "show", bead_id, "--json"])
        if rc != 0 or not out:
            return {"seeded": False, "reason": f"bd show failed: {out[:120]}"}
        data = json.loads(out)
        items = data if isinstance(data, list) else [data]
        if not items:
            return {"seeded": False, "reason": "bead not found"}
        desc = items[0].get("description") or ""
        if _perf_subtask_present(desc):
            return {"seeded": False, "reason": "perf subtask already present (idempotent)"}
        new_desc = _build_seeded_description(desc)
        rc2, out2 = run(["bd", "update", bead_id, "--description", new_desc])
        if rc2 != 0:
            return {"seeded": False, "reason": f"bd update failed: {out2[:120]}"}
        return {"seeded": True, "reason": "perf subtask appended"}
    except Exception as e:  # pragma: no cover — fail-open, never block worktree
        return {"seeded": False, "reason": f"error: {e}"}


def prune_merged_worktrees(dry_run: bool = False) -> dict:
    """DOCTOR STAGE (RCA 2026-06-14 pr-rick-q391): before creating a new worktree,
    remove OLD worktrees whose work is already in origin/main — so .claude/worktrees/
    never accumulates 185G/42-checkouts that thrash IDE file-watchers + Claude renderer.

    SAFETY (mirrors the §Nothing-lost-safe manual loop, never destructive):
      - skip the main worktree and any worktree with ANY uncommitted change (dirty)
      - remove ONLY when branch tip is ancestor-of-origin/main (merged) OR has zero
        unpushed commits (fully pushed) — provably zero-loss
      - plain `git worktree remove` (NO --force; destructive_op_full_ban allows plain)
      - opt-out DOCTOR_PRUNE_OFF=1; only runs when ≥ DOCTOR_PRUNE_MIN worktrees exist
    """
    if os.environ.get("DOCTOR_PRUNE_OFF", "").strip() == "1":
        return {"skipped": "DOCTOR_PRUNE_OFF=1"}

    listing = _run(["git", "worktree", "list", "--porcelain"], cwd=REPO_ROOT, check=False).stdout
    paths = [ln[len("worktree ") :] for ln in listing.splitlines() if ln.startswith("worktree ")]
    main_root = str(_main_worktree_root())
    candidates = [p for p in paths if p != main_root and Path(p).is_dir()]

    min_count = int(os.environ.get("DOCTOR_PRUNE_MIN", "1") or "1")
    if len(candidates) < min_count:
        return {"checked": len(candidates), "removed": 0, "reason": "below DOCTOR_PRUNE_MIN"}

    removed, kept_dirty, kept_unmerged = [], [], []
    for wt in candidates:
        status = _run(["git", "-C", wt, "status", "--porcelain"], check=False).stdout.strip()
        if status:  # dirty — never auto-remove
            kept_dirty.append(wt)
            continue
        tip = _run(["git", "-C", wt, "rev-parse", "HEAD"], check=False).stdout.strip()
        merged = (
            tip
            and _run(["git", "merge-base", "--is-ancestor", tip, "origin/main"], cwd=REPO_ROOT, check=False).returncode
            == 0
        )
        if not merged:
            unpushed = _run(["git", "-C", wt, "rev-list", "@{u}..HEAD"], check=False)
            fully_pushed = unpushed.returncode == 0 and not unpushed.stdout.strip()
            if not fully_pushed:
                kept_unmerged.append(wt)
                continue
        if dry_run:
            removed.append(wt)
            continue
        rm = _run(["git", "worktree", "remove", wt], cwd=REPO_ROOT, check=False)  # plain, no --force
        (removed if rm.returncode == 0 else kept_unmerged).append(wt)
    _run(["git", "worktree", "prune"], cwd=REPO_ROOT, check=False)

    summary = {
        "checked": len(candidates),
        "removed": len(removed),
        "kept_dirty": len(kept_dirty),
        "kept_unmerged": len(kept_unmerged),
    }
    if removed:
        verb = "would remove" if dry_run else "removed"
        print(
            f"# doctor-stage: {verb} {len(removed)} merged/pushed worktree(s); "
            f"kept {len(kept_dirty)} dirty + {len(kept_unmerged)} unmerged (zero-loss)",
            file=sys.stderr,
        )
    return summary


def create_worktree(name: str, base: str, dry_run: bool = False) -> Path:
    """Create a FULL-checkout worktree at .claude/worktrees/<name> off <base>.

    Never passes --no-checkout/--sparse/--orphan (git_worktree_completeness_gate).
    """
    wt_path = _main_worktree_root() / WORKTREE_DIR_DEFAULT / name
    git_cmd = ["git", "worktree", "add", str(wt_path), "-b", name, base]

    if dry_run:
        # stderr so --json stdout stays machine-parseable
        print("# dry-run — would run:", file=sys.stderr)
        print(f"  {' '.join(git_cmd)}", file=sys.stderr)
        return wt_path

    if wt_path.exists():
        raise RuntimeError(f"worktree path already exists: {wt_path}")

    # best-effort fresh base (avoid stale-base branch creation, §5-stale-base-rebase-guard)
    if "/" in base:
        remote = base.split("/", 1)[0]
        ref = base.split("/", 1)[1]
        _run(["git", "fetch", remote, ref, "--quiet"], cwd=REPO_ROOT, check=False)

    try:
        _run(git_cmd, cwd=REPO_ROOT, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git worktree add failed: {e.stderr.strip() or e.stdout.strip()}") from e
    return wt_path


def verify_completeness(wt_path: Path) -> tuple[int, int]:
    """Return (ls_files, ls_tree) counts; raise if checkout is materially partial."""
    files = _run(["git", "-C", str(wt_path), "ls-files"], check=True).stdout.splitlines()
    tree = _run(["git", "-C", str(wt_path), "ls-tree", "-r", "--name-only", "HEAD"], check=True).stdout.splitlines()
    n_files, n_tree = len(files), len(tree)
    # Allow tiny drift (e.g. assume-unchanged) but flag a partial checkout.
    if n_tree > 0 and n_files < n_tree * 0.95:
        raise RuntimeError(
            f"INCOMPLETE checkout: ls-files={n_files} < ls-tree={n_tree} (≥5% missing). "
            "A blanket `git add -A` here would commit phantom deletions — aborting."
        )
    return n_files, n_tree


# ── CLI ──────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="make_worktree.py",
        description="Generate a JTBD-named worktree from a bead (source affordance " "for branch_name_bead_ref_check).",
    )
    p.add_argument(
        "bead_id",
        nargs="?",
        default=os.environ.get("BEAD", "").strip(),
        help="bead id (e.g. pr-rick-7ms7); or set BEAD env",
    )
    p.add_argument("--slug", default=None, help="override the derived slug")
    p.add_argument("--base", default=DEFAULT_BASE, help=f"base ref (default {DEFAULT_BASE})")
    p.add_argument("--dry-run", action="store_true", help="print name + command, do not create")
    p.add_argument("--claim", action="store_true", help="run `bd update <id> --claim` after create")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON result")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if not args.bead_id:
        print("ERROR: no bead id. Usage: make worktree BEAD=pr-rick-7ms7", file=sys.stderr)
        return 2

    try:
        title = read_bead_title(args.bead_id)
        # Owner directive 2026-06-05: require a JTBD scenario on input, not a bare label.
        if not title_is_jtbd_scenario(title) and os.environ.get("MAKE_WORKTREE_ALLOW_NON_JTBD", "") != "1":
            print(
                f"ERROR: bead {args.bead_id} title is NOT a JTBD scenario:\n"
                f"  «{title}»\n"
                "A worktree must derive from a JTBD scenario, not a bare task label.\n"
                "Rewrite the bead title, then retry:\n"
                f'  bd update {args.bead_id} --title="Когда <триггер>, хотим <действие>, чтобы <outcome>"\n'
                "Override (rare infra branch): MAKE_WORKTREE_ALLOW_NON_JTBD=1",
                file=sys.stderr,
            )
            return 1
        name = compose_branch_name(title, args.bead_id, slug_override=args.slug)
        passes = slug_is_jtbd_self_describing(name)
        if not passes:
            print(
                f"WARN: generated name `{name}` does not satisfy the JTBD-slug gate "
                '(title too sparse). Pass --slug "<descriptive-slug>" or use a richer '
                "bead title.",
                file=sys.stderr,
            )
        # DOCTOR STAGE: prune old merged/pushed worktrees BEFORE creating the new one,
        # so .claude/worktrees never accumulates disk-thrash (pr-rick-q391).
        prune = prune_merged_worktrees(dry_run=args.dry_run)

        wt_path = create_worktree(name, args.base, dry_run=args.dry_run)

        result = {
            "bead_id": args.bead_id,
            "title": title,
            "branch": name,
            "worktree": str(wt_path),
            "gate_pass": passes,
            "dry_run": args.dry_run,
            "doctor_prune": prune,
        }

        if not args.dry_run:
            n_files, n_tree = verify_completeness(wt_path)
            result["ls_files"] = n_files
            result["ls_tree"] = n_tree
            if args.claim:
                _run(["bd", "update", args.bead_id, "--claim"], cwd=REPO_ROOT, check=False)
                result["claimed"] = True
            # Seed the mandatory profiling subtask into the bead (pr-rick-nbdl).
            result["perf_subtask"] = ensure_perf_subtask(args.bead_id)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"branch:   {name}  (gate: {'PASS' if passes else 'WARN'})")
            print(f"worktree: {wt_path}")
            if not args.dry_run:
                print(f"checkout: ls-files={result['ls_files']} ≈ ls-tree={result['ls_tree']} (full)")
                ps = result.get("perf_subtask", {})
                if ps.get("seeded"):
                    print("perf:     профайл-подзадача добавлена в bead (pr-rick-nbdl)")
                elif ps.get("reason"):
                    print(f"perf:     {ps['reason']}")
                print("next:")
                print(f"  cd {wt_path}")
                if not args.claim:
                    print(f"  bd update {args.bead_id} --claim")
        return 0
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
