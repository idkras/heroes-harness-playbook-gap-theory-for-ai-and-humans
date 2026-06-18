#!/usr/bin/env python3
"""Skill-packaging inventory: classify top-level ``scripts/`` files into a
migration map so skill-owned logic can be moved INTO its owning skill folder
(``.agents/skills/<skill>/scripts/`` + ``tests/``) and the workspace converges
on detachable (self-contained, copy-one-folder) skills.

Canonical source / контракт: skill ``0-detachable-skill-packaging`` SKILL.md +
Standard 4.8 §Detachable skill packaging.

Zero external dependencies (stdlib only) — this tool dogfoods detachability:
copy this one folder into any teammate/client repo and it runs as-is.

Categories
----------
- ``infra``        — workspace plumbing wired into Makefile / lefthook / hooks /
                     settings / known infra subdirs (setup, git, beads, launchd,
                     system, cursor, github). Correctly lives at top-level.
- ``skill-owned``  — logic referenced by a skill SKILL.md or agent .md, OR whose
                     name maps 1:1 to a skill slug. Should move INTO that skill.
- ``shared-lib``   — library imported by ≥2 other scripts (e.g. lib/, <internal-component>/).
- ``legacy-oneoff``— throwaway: temp/, debug_*, inspect_*, deep_inspect_*, or an
                     unreferenced client-specific one-shot writer.
- ``orphan``       — no references and no heuristic owner. Needs human triage.

CLI
---
    python3 skill_packaging_inventory.py [--scripts-dir scripts] \
        [--repo-root .] [--json out.json] [--md report.md] [--quiet]

Exit code 0 always (read-only inventory; never fails a build).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration (universal — no client/project hardcodes; override via CLI/API)
# --------------------------------------------------------------------------- #

DEFAULT_INFRA_SUBDIRS = {
    "setup",
    "git",
    "beads",
    "launchd",
    "system",
    "cursor",
    "github",
    "structure",
}
# Reference roots scanned for "does any skill/agent cite this script".
DEFAULT_SKILL_REF_ROOTS = (".agents/skills", ".agents/agents")
# Reference files that mark a script as infra plumbing.
DEFAULT_INFRA_REF_GLOBS = (
    "Makefile",
    "lefthook.yml",
    "lefthook.yaml",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".pre-commit-config.yaml",
    "pyproject.toml",
)
DEFAULT_INFRA_REF_DIRS = (".claude/hooks", "scripts/setup")
# Name heuristics for legacy one-offs.
LEGACY_NAME_RE = re.compile(r"^(temp_|debug_|deep_inspect_|inspect_|read_|show_|compare_|_)", re.IGNORECASE)
LEGACY_SUBDIRS = {"temp", "__pycache__"}
CODE_SUFFIXES = (".py", ".sh")


@dataclass
class Config:
    repo_root: Path
    scripts_dir: Path
    infra_subdirs: set = field(default_factory=lambda: set(DEFAULT_INFRA_SUBDIRS))
    skill_ref_roots: tuple = DEFAULT_SKILL_REF_ROOTS
    infra_ref_globs: tuple = DEFAULT_INFRA_REF_GLOBS
    infra_ref_dirs: tuple = DEFAULT_INFRA_REF_DIRS


@dataclass
class Classification:
    script_path: str  # relative to repo root
    category: str  # infra | skill-owned | shared-lib | legacy-oneoff | orphan
    owning_skill: str = ""  # skill slug if skill-owned
    referenced_by: str = ""  # short evidence
    recommended_action: str = ""


# --------------------------------------------------------------------------- #
# Reference indexing
# --------------------------------------------------------------------------- #


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return ""


def _skill_reference_files(root: Path) -> list[Path]:
    """Return canonical files that may prove script ownership.

    Reference/backlog docs often list many scripts as audit evidence. Treating
    those generated inventories as ownership evidence poisons the classifier
    (for example, every row in scripts-migration-backlog.md becomes "owned" by
    the backlog itself). Ownership must come from a skill's own contract.
    """
    return sorted(root.glob("*/SKILL.md"))


def _agent_reference_files(root: Path) -> list[Path]:
    """Return canonical agent markdown files, excluding generated references."""
    return sorted(p for p in root.glob("*.md") if p.is_file())


def build_skill_ref_index(cfg: Config) -> dict:
    """Map basename -> list of owning skill/agent identifiers that cite it."""
    index: dict[str, list[str]] = {}
    for root_rel in cfg.skill_ref_roots:
        root = cfg.repo_root / root_rel
        if not root.is_dir():
            continue
        if root_rel.endswith("/skills") or root.name == "skills":
            md_files = _skill_reference_files(root)
        elif root_rel.endswith("/agents") or root.name == "agents":
            md_files = _agent_reference_files(root)
        else:
            md_files = []
        for md in md_files:
            text = _read_text(md)
            if not text:
                continue
            # owner id = skill slug (parent dir of SKILL.md) or agent file stem
            if md.name == "SKILL.md":
                owner = md.parent.name
            else:
                owner = md.stem
            for m in re.finditer(r"([A-Za-z0-9_./-]+\.(?:py|sh))", text):
                base = os.path.basename(m.group(1))
                index.setdefault(base, [])
                if owner not in index[base]:
                    index[base].append(owner)
    return index


def _normalize_script_ref(path: str) -> str:
    """Return normalized repo-relative script path for a textual scripts/... ref."""
    return "/".join(Path(path).parts)


def build_infra_ref_set(cfg: Config) -> set:
    """Set of normalized `scripts/...` paths referenced by infra plumbing."""
    infra: set[str] = set()
    targets: list[Path] = []
    for g in cfg.infra_ref_globs:
        p = cfg.repo_root / g
        if p.is_file():
            targets.append(p)
    for d in cfg.infra_ref_dirs:
        dp = cfg.repo_root / d
        if dp.is_dir():
            targets.extend(t for t in dp.rglob("*") if t.is_file())
    for t in targets:
        text = _read_text(t)
        for m in re.finditer(r"(scripts/[A-Za-z0-9_./-]+\.(?:py|sh))", text):
            infra.add(_normalize_script_ref(m.group(1)))
    return infra


def build_import_index(cfg: Config) -> dict:
    """Map basename(without ext) -> count of OTHER scripts importing it."""
    counts: dict[str, int] = {}
    py_files = list(cfg.scripts_dir.rglob("*.py"))
    stems = {p.stem for p in py_files}
    for p in py_files:
        text = _read_text(p)
        imported = set()
        for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z0-9_.]+)", text, re.MULTILINE):
            head = m.group(1).split(".")[0]
            if head in stems and head != p.stem:
                imported.add(head)
        for stem in imported:
            counts[stem] = counts.get(stem, 0) + 1
    return counts


# --------------------------------------------------------------------------- #
# Classification (pure function — unit tested)
# --------------------------------------------------------------------------- #


def classify_script(
    rel_path: str,
    *,
    skill_refs: dict,
    infra_refs: set,
    import_counts: dict,
    infra_subdirs: set,
) -> Classification:
    """Classify one script path. Pure: all evidence passed in explicitly."""
    parts = Path(rel_path).parts
    base = os.path.basename(rel_path)
    stem = Path(base).stem
    # everything after the leading 'scripts' segment
    sub = parts[1] if len(parts) > 2 and parts[0] == "scripts" else ""

    # 1. infra by subdir
    if sub in infra_subdirs:
        return Classification(
            rel_path,
            "infra",
            referenced_by=f"infra subdir scripts/{sub}/",
            recommended_action="keep at top-level (workspace plumbing)",
        )
    # 2. infra by wiring reference
    if rel_path in infra_refs:
        return Classification(
            rel_path,
            "infra",
            referenced_by="Makefile/lefthook/hooks/settings",
            recommended_action="keep at top-level (wired into build/CI/hooks)",
        )
    # 3. legacy by subdir
    if sub in LEGACY_SUBDIRS:
        return Classification(
            rel_path,
            "legacy-oneoff",
            referenced_by=f"scripts/{sub}/",
            recommended_action="archive / delete (throwaway)",
        )
    # 4. skill-owned by skill/agent reference
    owners = [o for o in skill_refs.get(base, []) if o]  # drop empty owner strings (RCA H3)
    if owners:
        # Prefer a numbered skill slug (e.g. "4-ga4-admin-diagnostic") over an agent
        # name; agents own scripts only as fallback. Guard empty string before o[0].
        skill_owner = next(
            (o for o in owners if o and o[0].isdigit() and "-" in o),
            owners[0],
        )
        return Classification(
            rel_path,
            "skill-owned",
            owning_skill=skill_owner,
            referenced_by=",".join(owners[:3]),
            recommended_action=f"move into .agents/skills/{skill_owner}/scripts/ + tests/",
        )
    # 5. shared-lib by import fan-in
    if import_counts.get(stem, 0) >= 2 or sub == "lib":
        return Classification(
            rel_path,
            "shared-lib",
            referenced_by=f"imported by {import_counts.get(stem, 0)} scripts",
            recommended_action="keep as shared lib OR co-locate with primary consumer skill",
        )
    # 6. legacy by name heuristic
    if LEGACY_NAME_RE.match(base):
        return Classification(
            rel_path,
            "legacy-oneoff",
            referenced_by="name heuristic (temp/debug/inspect)",
            recommended_action="archive / delete (one-off)",
        )
    # 7. orphan
    return Classification(
        rel_path,
        "orphan",
        referenced_by="no references found",
        recommended_action="human triage: owning skill? infra? delete?",
    )


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def inventory(cfg: Config) -> list:
    skill_refs = build_skill_ref_index(cfg)
    infra_refs = build_infra_ref_set(cfg)
    import_counts = build_import_index(cfg)
    results: list[Classification] = []
    seen_dirs: set[str] = set()
    for p in sorted(cfg.scripts_dir.rglob("*")):
        if not p.is_file() or p.suffix not in CODE_SUFFIXES:
            continue
        rel = os.path.relpath(p, cfg.repo_root)
        # collapse __pycache__ noise
        if "__pycache__" in Path(rel).parts:
            continue
        results.append(
            classify_script(
                rel,
                skill_refs=skill_refs,
                infra_refs=infra_refs,
                import_counts=import_counts,
                infra_subdirs=cfg.infra_subdirs,
            )
        )
    return results


def counts_by_category(results: list) -> dict:
    out: dict[str, int] = {}
    for r in results:
        out[r.category] = out.get(r.category, 0) + 1
    return out


def render_markdown(results: list) -> str:
    lines = [
        "# Skill-packaging inventory",
        "",
        "Classification of `scripts/` files for migration into owning skills.",
        "Canon: skill `0-detachable-skill-packaging`.",
        "",
        "| script_path | category | owning_skill | referenced_by | recommended_action |",
        "|---|---|---|---|---|",
    ]
    order = {"skill-owned": 0, "orphan": 1, "shared-lib": 2, "legacy-oneoff": 3, "infra": 4}
    for r in sorted(results, key=lambda x: (order.get(x.category, 9), x.script_path)):
        lines.append(
            f"| `{r.script_path}` | {r.category} | {r.owning_skill or '—'} "
            f"| {r.referenced_by} | {r.recommended_action} |"
        )
    lines += ["", "## Counts per category", ""]
    for cat, n in sorted(counts_by_category(results).items(), key=lambda kv: -kv[1]):
        lines.append(f"- **{cat}**: {n}")
    lines.append(f"- **total**: {len(results)}")
    return "\n".join(lines) + "\n"


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Classify scripts/ into migration map (detachable skills).")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--scripts-dir", default="scripts")
    ap.add_argument("--json", dest="json_out", default="")
    ap.add_argument("--md", dest="md_out", default="")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    scripts_dir = (repo_root / args.scripts_dir).resolve()
    if not scripts_dir.is_dir():
        print(f"scripts dir not found: {scripts_dir}", file=sys.stderr)
        return 0
    cfg = Config(repo_root=repo_root, scripts_dir=scripts_dir)
    results = inventory(cfg)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.md_out:
        Path(args.md_out).write_text(render_markdown(results), encoding="utf-8")
    if not args.quiet:
        cc = counts_by_category(results)
        print("Skill-packaging inventory —", ", ".join(f"{k}:{v}" for k, v in sorted(cc.items())))
        print(f"total: {len(results)}")
        if args.md_out:
            print(f"report: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
