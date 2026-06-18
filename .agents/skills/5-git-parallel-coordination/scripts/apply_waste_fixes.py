#!/usr/bin/env python3
"""apply_waste_fixes.py — idempotent landing of WASTE-001..006 fixes.

Typical-action script (owner directive: recurring actions → committed skill
script). Applies 5 edits to a repo root; each edit is grep-guarded so the
script is safe to re-run. Exit 0 = all applied-or-already-present;
exit 1 = an anchor not found (STOP, do not guess).

Usage: python3 apply_waste_fixes.py <repo_root>
"""

from __future__ import annotations

import sys
from pathlib import Path

CLAUSE = """## Parallel-session hazard neutralization — ответственность активного агента (RCA 2026-05-19)

Обнаружение и нейтрализация параллельно-сессионных опасностей (branch-substitution,
shared dirty tree, чужие живые сессии, spawn-pressure хуки) И верификация
делегированной субагентам работы по authoritative git/gh state (НЕ по слову
субагента, НЕ по факту launch — background-результат не переживает
session-resume) — ОБЯЗАННОСТЬ активного агента, НЕ owner-действие. SSOT
принципа — AGENTS.md §Agent role × invariant matrix (R2/R3); здесь role-форма,
текст инвариантов не дублируется (анти-паттерн <client>-addition).

Агент ОБЯЗАН сам, в той же сессии:
1. Детектить живые сессии (ps/PID) ДО любой git-write операции.
2. При чужой живой сессии ИЛИ dirty-tree ≥ BLOCK → дефолт = clone-isolated
   worktree (git worktree add /tmp/... origin/main → edit → push → PR), без
   запроса owner.
3. Нейтрализовать spawn-pressure (HARD-BLOCK хуки → soft-nudge) вместо жалобы
   «воркспейс форсит агентов».
4. Делегировал субагенту → ОБЯЗАН verify-after по authoritative
   `git show origin/main:<path>` / `gh pr view --json state`. «Запустил
   субагента» ≠ «сделано». Атомарный scope делегирования (один субагент =
   одна закрываемая единица), не compound; повтор тихого провала = retry с
   ИЗМЕНЁННЫМ подходом (сделать самому in-session), не тем же способом.
5. Взять ownership консолидации (extract ADDED-only, классиф (a)/(b)/(c), PR)
   — не перекладывать «разрули ветки» на owner. Owner-действие только для
   физически недостижимого агенту (закрыть GUI-окно) → message по
   3-human-help-url-mandatory.

Hard fail: «делегировал и считаю сделанным без authoritative verify» →
RCA category: delegated-not-verified. «параллельные сессии — закрой окна»
как owner-effort >0 без clone-isolated дефолта и без нейтрализации
spawn-pressure → category: parallel-session-hazard-offloaded.

"""

WASTE_BLOCK = """### WASTE-2026-05-19 — session waste audit (6 items, RCA-source git-sync-curator run + parent session)

| ID | What | Where | Severity | Fix | Status |
|---|---|---|---|---|---|
| WASTE-001 | sync-guard --strict fires on path-only/throwaway checkout (~260s/run) | lefthook.yml post-checkout/post-merge | P0-high | predicate `[ "{2}"=0 ] && exit 0` + /tmp skip + LEFTHOOK_SYNC_GUARD_SKIP | LANDED-this-PR |
| WASTE-002 | poll-thrash 15× Read same file + 3 waiter loops | 5-git-parallel-coordination clone-recipe | P1-medium | rule "one bg + single blocking until-loop, never re-Read >2×" | open |
| WASTE-003 | shell fn shadows git/awk/python3 in /tmp non-interactive bash | scripts/setup + 5-git-parallel-coordination | P1-medium | mandate /usr/bin/git in throwaway; clean_git_env.sh | open |
| WASTE-004 | extract files already blob-identical in origin/main (~80-100s + 6 calls) | 5-sync-github-checklist Step 0 | P1-medium | pre-flight `git rev-parse <sha>:<p> == origin/main:<p>` → SKIP | open |
| WASTE-005 | broken HumanCompiler recurses → forced --no-verify (2× session) | git config + submodules-and-projects-registry.yaml | P0-high | submodule.recurse=false | LANDED-this-PR |
| WASTE-006 | delegated-not-verified + Symphony misdiagnosis ~17 turns + dirty-tree transport tax (8th dirty-tree recidive) | parent session / 2-rca-incidents | P0-systemic | verify-after gate (clause this PR) + escalate ai.incidents category symphony-misdiagnosis-turn-waste | open |

"""


def patch_lefthook(root: Path) -> str:
    p = root / "lefthook.yml"
    t = p.read_text(encoding="utf-8")
    if "WASTE-001" in t:
        return "lefthook.yml: already patched (skip)"
    pc_anchor = "      # Falls back to main repo's .venv if temp worktree has none.\n" "      run: |\n"
    pc_inject = pc_anchor + (
        "        # WASTE-001 (RCA 2026-05-19): skip strict sync-guard on\n"
        "        # path-only checkout ({2}==0) and throwaway /tmp worktrees —\n"
        "        # branch-switch bootstrap guard, not file-restore; ~260s/run.\n"
        '        [ "{2}" = "0" ] && exit 0\n'
        '        case "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" in /tmp/*|/private/tmp/*) exit 0;; esac\n'
        '        [ "${LEFTHOOK_SYNC_GUARD_SKIP:-}" = "1" ] && exit 0\n'
    )
    if pc_anchor not in t:
        raise SystemExit("lefthook.yml: post-checkout sync-guard anchor not found")
    t = t.replace(pc_anchor, pc_inject, 1)
    pm_anchor = (
        "    sync-guard:\n" "      run: |\n" '        REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"\n'
    )
    pm_inject = (
        "    sync-guard:\n"
        "      run: |\n"
        "        # WASTE-001 (RCA 2026-05-19): skip strict sync-guard in\n"
        "        # throwaway /tmp worktrees — clone-isolated needs no\n"
        "        # team-bootstrap guard (~60s/merge there).\n"
        '        case "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" in /tmp/*|/private/tmp/*) exit 0;; esac\n'
        '        [ "${LEFTHOOK_SYNC_GUARD_SKIP:-}" = "1" ] && exit 0\n'
        '        REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"\n'
    )
    if pm_anchor not in t:
        raise SystemExit("lefthook.yml: post-merge sync-guard anchor not found")
    t = t.replace(pm_anchor, pm_inject, 1)
    p.write_text(t, encoding="utf-8")
    return "lefthook.yml: WASTE-001 predicate added (post-checkout + post-merge)"


def patch_git_config_script(root: Path) -> str:
    p = root / "scripts/setup/git_config_merge_drivers.sh"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    t = p.read_text(encoding="utf-8")
    if "submodule.recurse" in t:
        return "git_config_merge_drivers.sh: already has submodule.recurse (skip)"
    line = (
        "\n# WASTE-005 (RCA 2026-05-19): broken <internal-folder>/HumanCompiler recurses\n"
        "# into cherry-pick/merge → forced --no-verify twice/session. Pin false.\n"
        "git config --get submodule.recurse 2>/dev/null | grep -qx false "
        "|| git config submodule.recurse false\n"
    )
    p.write_text(t.rstrip() + "\n" + line, encoding="utf-8")
    return "git_config_merge_drivers.sh: submodule.recurse=false guard appended"


def patch_orchestrator_hook(root: Path) -> str:
    """Soften HARD-BLOCK (return 2) → nudge (return 0) IF present.

    Correct semantic: origin/main's version is nudge-only (no `return 2`).
    The aggressive HARD-BLOCK tier is local-unmerged work and is
    intentionally NOT propagated to the canonical tree — its absence is
    the SAFE state, not a failure. So when no `return 2` anchor exists,
    this is a graceful no-op skip, never a hard error.
    """
    p = root / ".claude/hooks/substantial_task_orchestrator_trigger.py"
    t = p.read_text(encoding="utf-8")
    if "WASTE-2026-05-19" in t:
        return "orchestrator hook: already annotated (skip)"
    if "return 2" not in t:
        return (
            "orchestrator hook: origin/main already nudge-only "
            "(no HARD-BLOCK to soften) — SAFE, intentional no-op skip"
        )
    old = "        print(block, file=sys.stderr)\n        return 2\n"
    new = (
        "        print(block, file=sys.stderr)\n"
        "        # WASTE-2026-05-19: HARD-BLOCK softened to strong-nudge —\n"
        "        # forcing subagent spawn under load was itself a\n"
        "        # parallel-agent-proliferation source (owner directive).\n"
        "        # Keep the printed guidance; never block.\n"
        "        return 0\n"
    )
    if old not in t:
        return (
            "orchestrator hook: 'return 2' present but exact anchor "
            "shape differs — skipped, needs manual review (non-fatal)"
        )
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    return "orchestrator hook: HARD-BLOCK → soft-nudge (return 2→0)"


def patch_skill(root: Path) -> str:
    p = root / ".agents/skills/5-git-parallel-coordination/SKILL.md"
    t = p.read_text(encoding="utf-8")
    if "Parallel-session hazard neutralization" in t:
        return "5-git-parallel-coordination/SKILL.md: clause already present (skip)"
    anchor = "## Авторство"
    if anchor not in t:
        raise SystemExit("5-git-parallel-coordination/SKILL.md: '## Авторство' anchor not found")
    p.write_text(t.replace(anchor, CLAUSE + anchor, 1), encoding="utf-8")
    return "5-git-parallel-coordination/SKILL.md: verify-after responsibility clause inserted"


def patch_ai_legacy(root: Path) -> str:
    p = root / "<internal-folder>/ai.legacy.md"
    t = p.read_text(encoding="utf-8")
    if "WASTE-2026-05-19" in t:
        return "ai.legacy.md: WASTE-2026-05-19 already present (skip)"
    if "## Счётчики" in t:
        out = t.replace("## Счётчики", WASTE_BLOCK + "## Счётчики", 1)
    else:
        out = t.rstrip() + "\n\n" + WASTE_BLOCK
    p.write_text(out, encoding="utf-8")
    return "ai.legacy.md: WASTE-2026-05-19 6-row block appended"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply_waste_fixes.py <repo_root>")
        return 1
    root = Path(sys.argv[1])
    if not (root / ".git").exists() and not (root / "lefthook.yml").exists():
        print(f"not a repo root: {root}")
        return 1
    # Resilient: one anchor-miss must NOT abort the other independent
    # patches (WASTE-004-class defect that lost 3 good edits). Apply all,
    # collect failures, exit 1 only if a real failure occurred.
    failures = []
    for fn in (
        patch_lefthook,
        patch_git_config_script,
        patch_orchestrator_hook,
        patch_skill,
        patch_ai_legacy,
    ):
        try:
            print("  ✓ " + fn(root))
        except SystemExit as e:
            print(f"  ✗ {fn.__name__}: {e}")
            failures.append(fn.__name__)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {fn.__name__}: {type(e).__name__}: {e}")
            failures.append(fn.__name__)
    if failures:
        print(f"WASTE-FIXES-PARTIAL — failed: {', '.join(failures)}")
        return 1
    print("WASTE-FIXES-APPLIED-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
