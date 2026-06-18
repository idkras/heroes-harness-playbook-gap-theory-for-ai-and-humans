# Pre-flight Workflow — mandatory order before ANY GitHub command

**Companion to `SKILL.md`** — порядок шагов которые agent **обязан** выполнить ПЕРЕД любой git/gh command, и список опасных команд которые применять **запрещено** без дополнительных проверок.

**Created:** 2026-05-14 after RCA 2026-05-14 incident-cleaned-parallel-cost-allocation.

## When this workflow triggers

**ВСЕГДА** перед любым из:

| Trigger command | Risk class |
|---|---|
| `git checkout <branch>` (switching) | medium — может lose untracked work |
| `git checkout -b <new-branch>` | low |
| `git checkout -- <file>` (revert) | medium — destroys local edits |
| `git pull` (any flavor) | medium — может create autostash conflict |
| `git rebase` | high — может re-write history |
| `git merge` | medium — может create merge conflict |
| `git push` (own repo) | low |
| `git push --force` / `--force-with-lease` | high — overwrites remote |
| `git push <external-host>` | **VERY HIGH** — see external-git-hosts.yaml |
| **`git clean -fd`** | **CRITICAL** — destroys untracked, потенциально parallel-session work |
| **`git reset --hard`** | **CRITICAL** — destroys both tracked & untracked changes |
| `git stash` (any variant) | low |
| `git stash pop / drop` | medium — может lose work |
| `git branch -D <name>` | medium — local-only loss |
| `git submodule update` | medium — può conflict with in-progress submodule work |
| `gh pr merge` | low (in own repo) / very high (external) |

## Dangerous commands — DO NOT USE without explicit gate pass

| Command | Why dangerous | Use instead |
|---|---|---|
| `git push --force <branch>` | Overwrites remote without lease check, можно потерять teammate work | `git push --force-with-lease <branch>` (own repo only) |
| `git push --force <main>` | Overwrites main, destroys merged work | **FORBIDDEN** — open PR + merge instead |
| `git push <external-host>` (<internal-host>, <internal-host>) | Bypasses external-git-hosts.yaml policy | Use `<teammate>-git-sync` subagent или explicit `{HOST}_PUSH_APPROVED_BY` env |
| `git clean -fdx` | Removes ignored files too (.venv, node_modules, build artifacts) | Use `git clean -fd` with explicit paths (still subject to L6 check) |
| `git clean -fd <path>` без L6 check | Destroys parallel-session work | Run §L6 3-layer check ПЕРЕД clean (see SKILL.md §0.0.6) |
| `git reset --hard origin/main` без preservation | Destroys all local work including stashes if branch reflog cleared | Run §0.0.6 L1-L6 preservation первым |
| `git checkout --theirs/ours .` bulk | Hides intentional changes from both sides | Manual resolve per file (see Scenario D in SKILL.md) |
| `--no-verify` на commit/push | Bypasses pre-commit/pre-push hooks (security/quality gates) | Document RCA для bypass; use `SKIP_REAL_MCP_SMOKE=1` for scope-mismatched RickAI gate (see AGENTS.md) |
| `git add -A` на dirty main | Mixes unrelated scopes | Selective `git add <explicit-paths>` |
| `git rebase` on shared branch | Re-writes history others have based on | Use rebase only on personal feature branches not yet pulled by others |
| `git submodule update --force` | Loses local submodule work | First `git -C <sub> stash`, then update, then pop |

## Pre-flight workflow (mandatory ORDER)

ALL steps below ДО первой git/gh tool call в sync session:

### Step 0 — Read known-incidents-checklist.md (30 sec)

```bash
cat .agents/skills/5-sync-github-checklist/known-incidents-checklist.md
```

Identify which of 14 incident classes могут произойти в текущем контексте. If NONE applicable — write «known-incidents-check: clear» в reasoning log.

### Step 1 — Project State Classification (§0.0.4)

```bash
AB=$(git rev-list --left-right --count origin/$(git branch --show-current)...HEAD 2>/dev/null || echo "0	0")
AHEAD=$(echo "$AB" | awk '{print $2}')
BEHIND=$(echo "$AB" | awk '{print $1}')
DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
echo "State: ahead=$AHEAD behind=$BEHIND dirty=$DIRTY"
```

Map в state set {A-K} per SKILL.md §0.0.4 table. Write `State: {...}` в reasoning log.

### Step 2 — «Nothing Lost» preservation checklist (§0.0.6, L1-L6)

```bash
# L1: Teammate scan via universal YAML
yq -r '.teammates[] | .alias as $a | .email_patterns[] | "\($a)\t\(.)"' .agents/config/teammate-emails.yaml | \
  while IFS=$'\t' read -r alias pattern; do
    commits=$(git log --all --since="24h" --author="$pattern" --oneline 2>/dev/null | head -3)
    [ -n "$commits" ] && echo "TEAMMATE-ACTIVE: $alias" && echo "$commits"
  done

# L2: Untracked top-level scan
git status --porcelain | grep "^??" | awk '{print $2}' | head -20

# L3: Submodule check
git submodule foreach --quiet 'echo "$name: $(git status --porcelain | wc -l) dirty files"' 2>/dev/null

# L4: Stash inventory
STASH_COUNT=$(git stash list | wc -l | tr -d ' ')
[ "$STASH_COUNT" -gt 5 ] && echo "WARN: stash backlog $STASH_COUNT — classify first"

# L5: External host check
gh remote get-url origin 2>/dev/null | grep -qE "<internal-host>|git\.rick\.ai" && \
  echo "EXTERNAL HOST — push needs {HOST}_PUSH_APPROVED_BY"

# L6: NEW — Parallel Claude session check (RCA 2026-05-14)
# Run only if planning git clean -fd <path> OR reset --hard
PARALLEL=$(ls /tmp/claude-501/-Users-*-heroes-rickai-workspace/ 2>/dev/null | wc -l | tr -d ' ')
[ "$PARALLEL" -gt 1 ] && echo "L6-WARN: $PARALLEL parallel Claude sessions detected"
```

If **ANY layer positive** AND planning destructive op (L_any) → **STOP**, use `git stash push -u` instead.

### Step 3 — Choose strategy from §0.0.4 state table

Apply prioritized strategy: K → I → G → H → J → F → D → E → B → C → A.

### Step 4 — If destructive op needed → require explicit ACK

Set env var `DIRTY_TREE_ACK="<reason + state + L6-verified>"`:

```bash
export DIRTY_TREE_ACK="pr-<name>: state=<state-set> L6-clear=<yes|no+detail>"
```

Without ACK → `git_dirty_count_gate.py` hook blocks при dirty ≥ 200.

### Step 5 — Subagent chain dispatch (§0.0.5)

| State | Chain |
|---|---|
| A, B, C | minimal — `git-sync-curator` only |
| D, E | basic — developer + `code-reviewer` |
| F | medium — developer + `code-reviewer` + `cleanup-guardian` |
| G, I, J, K | full — `manager-lead-orchestrator` → developer → 2×QA → `subagent-falsification` → `release-notes-dispatcher` |
| H | special — state H = stale merged branch, switch to main first |

### Step 6 — Execute via subagent (NOT inline) for substantial flows

Substantial = ahead ≥ 5 commits OR dirty ≥ 50 OR PR with red CI.

### Step 7 — Post-op verification (§5.1 Post-commit completeness)

```bash
git status --porcelain  # must be empty OR explicitly classified residual
git log --oneline -3
gh pr view <num> --json statusCheckRollup  # CI green?
```

### Step 7.5 — Hook-eval coverage gate (RCA 2026-06-06, pr-rick-owan)

Система хуков — часть git-sync контракта. Перед push «хуже не стало» проверяется механически: новый wired-хук без eval-фикстуры и без waiver = регрессия покрытия.

```bash
# Реестр всех хуков + JTBD + eval-покрытие (GENERATED, SSOT — генератор):
python3 .agents/skills/5-sync-github-checklist/gen_hook_jtbd_registry.py --write
#   → hook-jtbd-registry.md (🟢 покрыт eval / 🟡 waiver / 🔴 без eval / ⚪ deprecated)

# Регрессия покрытия (exit 2 если новый 🔴 сверх baseline) — это же висит в lefthook pre-push:
python3 .agents/skills/5-sync-github-checklist/gen_hook_jtbd_registry.py --check
```

Добавил/изменил хук → добавь фикстуру в `scripts/test_hooks_smoke.py` ИЛИ waiver в `EVAL_WAIVERS` (с причиной) → обнови baseline. Канон-чеклист «что должна делать система хуков»: [`hook-jtbd-registry.md`](hook-jtbd-registry.md).

### Step 7.6 — GitHub sync telemetry emit (RCA 2026-06-07)

Для full sync использовать measured route:

```bash
make team-main-sync-measured
make sync-github-telemetry-summary
make sync-github-telemetry-owner-line
make sync-github-telemetry-eval
```

Runtime rows append-only и gitignored: `.agents/memory/runtime/5-sync-github-checklist/github-sync-telemetry.jsonl`. В финальном отчёте обязательна строка p50/p95 + no-extra-work counters; без неё `sync complete` не подтверждён.

### Step 8 — Falsification (§Hypothesis falsification)

Build gap table for sync claim. Verdict `confirmed / partial / falsified`.

### Step 9 — Update incidents checklist if new class found

If sync encountered NEW failure mode not in known-incidents-checklist.md → add row + write RCA в ai.incidents.md.

## Decision tree (visual)

```
Owner: "sync / push / rebase / clean / reset"
  │
  ├── Read known-incidents-checklist.md (30 sec)
  │
  ├── Classify state via §0.0.4 → {A-K} set
  │
  ├── Run §0.0.6 L1-L6 preservation checklist
  │     │
  │     ├── L1-L5 negative + planning destructive? → require DIRTY_TREE_ACK
  │     │
  │     └── L6 positive (parallel session OR recent files OR JSONL Write) → STOP, use git stash, NOT clean
  │
  ├── Substantial (ahead≥5 / dirty≥50 / red CI)?
  │     │
  │     ├── YES → spawn subagent chain (§0.0.5)
  │     │
  │     └── NO  → execute inline via git-sync-curator only
  │
  ├── Execute → post-op verify → falsify → known-incidents-checklist update if new class
  │
  └── DONE
```

## Hard fails (новые RCA classes if violated)

- Sync op executed без чтения known-incidents-checklist.md → `category: known-incidents-checklist-skipped`
- §0.0.6 L6 не выполнен ПЕРЕД `git clean -fd` → `category: l6-parallel-session-check-skipped`
- Dangerous command (table выше) использована без mitigation → `category: dangerous-command-without-mitigation`
- Substantial sync (ahead≥5 / dirty≥50) выполнен inline без chain → `category: substantial-sync-without-chain`
- Sync завершён без falsification gap table → `category: sync-claim-without-falsification`

## Related artefacts

- Skill: [`5-sync-github-checklist/SKILL.md`](SKILL.md) — full reference
- Incidents log: [`<internal-folder>/ai.incidents.md`](../../../[todo%20·%20incidents]/ai.incidents.md)
- Known incidents table: [`known-incidents-checklist.md`](known-incidents-checklist.md)
- Universal SSOT: [`.agents/config/teammate-emails.yaml`](../../config/teammate-emails.yaml)
- Mechanical hooks: [`.claude/hooks/`](../../../.claude/hooks/)
