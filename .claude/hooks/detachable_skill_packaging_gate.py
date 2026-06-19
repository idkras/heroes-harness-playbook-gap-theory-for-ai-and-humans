#!/usr/bin/env python3
"""PreToolUse gate: keep skill logic out of top-level scripts/.

Canon: skill 0-detachable-skill-packaging + Standard 4.8 §Detachable skill packaging.

Root problem (RCA: scripts live separately from skills → skills non-detachable):
a teammate/Rick client cannot copy one skill folder and run it, because its
logic + tests sit in top-level scripts/ instead of `.agents/skills/<skill>/scripts/`
+ `tests/`. This gate makes "put it in the skill folder" the default and dropping
a loose script the blocked exception.

Fires ONLY when ALL hold (precise leak surface — never blocks existing infra):
  1. tool_name ∈ Write/Edit/NotebookEdit
  2. file_path is a `.py` under `scripts/` (ANY depth — closes the depth-2 bypass
     `scripts/utils/x.py`, RCA design-review 2026-06-03), EXCEPT:
       - under an infra subdir (setup/git/beads/launchd/system/cursor/github/structure)
  3. NEW loose scripts are blocked unless they look like infra; EXISTING loose
     scripts are classified by skill_packaging_inventory.py and blocked when
     category is skill-owned/orphan/legacy-oneoff
  4. filename does NOT match an infra-verb prefix allowlist (check_/validate_/
     verify_/setup_/install_/sync_/register_/... — workspace plumbing)
  5. basename is NOT already referenced (word-boundary) by Makefile / lefthook.yml
  6. env DETACHABLE_PACKAGING_ACK is not set

Action: exit 2 (BLOCK) with remediation pointing to the owning skill folder.
Override: DETACHABLE_PACKAGING_ACK="<reason ≥12 chars>" (e.g. "infra: foo wired into Makefile").
Fail-open on any parse / IO error (never breaks a session over its own bug).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PROTECTED_TOOLS = {"Write", "Edit", "NotebookEdit"}

# Subdirs under scripts/ that are workspace plumbing (not detachable skill logic).
INFRA_SUBDIRS = {"setup", "git", "beads", "launchd", "system", "cursor", "github", "structure"}

# Infra-verb prefixes → workspace plumbing, legitimately top-level.
# NB: debug_/inspect_/temp_/audit_ are DELIBERATELY excluded (RCA code-review C1):
# the classifier marks those legacy-oneoff, so the gate must NOT silently pass them.
INFRA_PREFIX_RE = re.compile(
    r"^(check_|validate_|verify_|setup_|install_|sync_|post_sync|register_|merge_|"
    r"build_|run_|team_|mcp_|get_|export_beads|enrich_beads|gmail_|telegram_bronze|"
    r"sales_marketing|packaging_process|log_health|auto_format|land_to_main|owner_link|"
    r"branch_lifecycle|git_workspace|cleanup_|rotate_|recover_|heroes_management|bootstrap)",
    re.IGNORECASE,
)
BLOCK_EXISTING_CATEGORIES = {"skill-owned", "orphan", "legacy-oneoff"}


def _project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _rel_parts(file_path: str, project_dir: Path) -> list[str]:
    """Relative path parts WITHOUT resolve() — resolving a symlinked path
    (e.g. <internal-folder>/) could escape project_dir and silently bypass the gate
    (RCA code-review H2). We compare normalized lexical parts so `../scripts/x.py`
    cannot bypass the gate while still avoiding symlink resolution."""
    p = Path(file_path)
    if p.is_absolute():
        try:
            rel = p.relative_to(project_dir)
        except ValueError:
            # absolute path outside project dir → not our scripts/ → empty
            return []
    else:
        rel = p
    normalized: list[str] = []
    for seg in rel.parts:
        if seg in ("", "."):
            continue
        if seg == "..":
            if normalized:
                normalized.pop()
            else:
                normalized.append(seg)
            continue
        normalized.append(seg)
    return normalized


def _referenced_in_infra(basename: str, project_dir: Path) -> bool:
    pat = re.compile(rf"(^|[\s/]){re.escape(basename)}(\s|$|\b)")
    for rel in ("Makefile", "lefthook.yml", "lefthook.yaml"):
        f = project_dir / rel
        if not f.is_file():
            continue
        try:
            if pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                return True
        except OSError:
            continue
    return False


def _existing_script_classification(project_dir: Path, relpath: str) -> tuple[str, str, str] | None:
    """Classify an existing top-level script using the skill-packaging SSOT."""
    inv_dir = project_dir / ".agents" / "skills" / "0-detachable-skill-packaging" / "scripts"
    if not inv_dir.is_dir():
        return None
    sys.path.insert(0, str(inv_dir))
    try:
        import skill_packaging_inventory as spi  # type: ignore

        cfg = spi.Config(repo_root=project_dir, scripts_dir=project_dir / "scripts")
        item = spi.classify_script(
            relpath,
            skill_refs=spi.build_skill_ref_index(cfg),
            infra_refs=spi.build_infra_ref_set(cfg),
            import_counts=spi.build_import_index(cfg),
            infra_subdirs=cfg.infra_subdirs,
        )
        return item.category, item.owning_skill, item.recommended_action
    except Exception:
        return None


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if (payload.get("tool_name") or "") not in PROTECTED_TOOLS:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return 0

    project_dir = _project_dir()
    parts = _rel_parts(file_path, project_dir)

    # condition 2: a .py somewhere under scripts/ (any depth)
    if len(parts) < 2 or parts[0] != "scripts" or not parts[-1].endswith(".py"):
        return 0
    basename = parts[-1]
    subdirs = parts[1:-1]  # path segments between scripts/ and the file

    # 2a: infra subdir → workspace plumbing, allow
    if subdirs and subdirs[0] in INFRA_SUBDIRS:
        return 0

    relpath = "/".join(parts)

    # condition 3a: existing loose scripts must be triaged/migrated before edit
    target = project_dir.joinpath(*parts)
    if target.exists():
        classified = _existing_script_classification(project_dir, relpath)
        if classified:
            category, owning_skill, action = classified
            if category in BLOCK_EXISTING_CATEGORIES:
                ack = os.environ.get("DETACHABLE_PACKAGING_ACK", "").strip()
                msg = (
                    f"detachable-skill-packaging-gate: BLOCK — existing `{relpath}` is `{category}`.\n"
                    f"\n"
                    f"Do not keep editing loose top-level script logic. First triage/migrate it so the\n"
                    f"owning skill stays detachable.\n"
                    f"  category: {category}\n"
                    f"  owning_skill: {owning_skill or '—'}\n"
                    f"  action: {action}\n"
                    f"\n"
                    f"If this is genuinely workspace plumbing, document the wiring and override once:\n"
                    f'  export DETACHABLE_PACKAGING_ACK="infra: {basename} wired into <where>"\n'
                )
                if len(ack) >= 12:
                    print(
                        f"detachable-skill-packaging-gate: OVERRIDE existing loose script via "
                        f"DETACHABLE_PACKAGING_ACK ({ack[:40]})",
                        file=sys.stderr,
                    )
                    return 0
                print(msg, file=sys.stderr)
                return 2
        return 0

    # condition 6: explicit override
    ack = os.environ.get("DETACHABLE_PACKAGING_ACK", "").strip()
    if len(ack) >= 12:
        print(f"detachable-skill-packaging-gate: OVERRIDE via DETACHABLE_PACKAGING_ACK ({ack[:40]})", file=sys.stderr)
        return 0

    # condition 4 + 5: infra allowlist
    if INFRA_PREFIX_RE.match(basename) or _referenced_in_infra(basename, project_dir):
        print(
            f"detachable-skill-packaging-gate: PASS — {basename} looks like workspace plumbing (infra).",
            file=sys.stderr,
        )
        return 0

    # BLOCK
    msg = (
        f"detachable-skill-packaging-gate: BLOCK — новый `{relpath}` (skill-логика в scripts/).\n"
        f"\n"
        f"Логика скила должна жить ВНУТРИ его папки, не в top-level scripts/, чтобы скил был\n"
        f"отчуждаемым (товарищ/клиент копирует ОДНУ папку и запускает без всего repo).\n"
        f"Канон: skill `0-detachable-skill-packaging` + Standard 4.8 §Detachable skill packaging.\n"
        f"\n"
        f"Сделай вместо этого:\n"
        f"  1. Определи owning-скил (или создай новый `.agents/skills/<skill>/`).\n"
        f"  2. Положи код в `.agents/skills/<skill>/scripts/{basename}`\n"
        f"     и тест в `.agents/skills/<skill>/tests/test_*.py` (C15 контракта).\n"
        f"  3. Обнови `skill.yaml` (detachable/deps/entrypoints) и сошлись на скрипт из SKILL.md.\n"
        f"\n"
        f"Если это РЕАЛЬНО workspace-плумбинг (хук/Makefile/bootstrap/CI), а не логика скила —\n"
        f'  export DETACHABLE_PACKAGING_ACK="infra: {basename} wired into <where>"\n'
        f"и повтори Write.\n"
    )
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail-open — never break a session over hook bug
        print(f"detachable-skill-packaging-gate: internal error, failing open ({exc})", file=sys.stderr)
        sys.exit(0)
