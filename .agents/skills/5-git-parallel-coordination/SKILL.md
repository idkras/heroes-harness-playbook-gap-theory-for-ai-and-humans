---
name: git-parallel-coordination
description: "Use when git work can change shared branch/worktree/history or publish commits and parallel agents need one coordination ritual. Based on the workspace git coordination standard and `.beads` protocol. Reads durable git protocol plus the short-lived runtime intent log, links the work to a bead, records current git intent before write-like actions, and performs post-sync cleanup into runtime memory, durable memory, ai.legacy, or ai.incidents. Use when user says \"синкнись\", \"работай с git\", \"не мешайте друг другу в git\", \"prepare push\", or before checkout/pull/merge/rebase/commit/push in parallel work."
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `<internal-module>/shared/credentials_manager.py`.

# Git Parallel Coordination

## Hired for JTBD, Jobs To Be Done — задача, которую решает клиент

Когда параллельный агент собирается менять branch, worktree, history или публиковать commits и не должен помешать соседнему треду, этот skill нанимается на работу `согласовать git-намерение через memory и правильно очистить след после sync`.

## Purpose

Этот skill разводит два слоя:

- durable git protocol в `.codex-memory/topics/git-parallel-coordination.md`
- short-lived runtime intent в `.codex-memory/runtime/git-sync-intents.md`

`.beads` остаётся source of truth для project graph. Runtime git intent нужен только для координации git-writing шагов.

## Use this skill for

- `checkout`, `switch`
- `pull`, `merge`, `rebase`, `cherry-pick`
- `commit`, `push`
- `git add`, `git reset`, `git restore --staged`, UI `Stage all`, GUI commit preparation
- branch sync or branch publication
- destructive cleanup or ref-moving recovery

Only reading commands such as `git status`, `git log`, `git diff`, `git show` do not require an intent row unless they are part of an imminent git-changing flow.

## §Push-first protocol (ОБЯЗАТЕЛЬНО для substantial work, RCA 2026-05-10)

**Корневая причина:** параллельная Cowork session делает периодический `git reset --hard origin/main` (видно в reflog как pattern «commit → reset → commit → reset»). Local main без push в origin = **guaranteed loss** на следующем reset cycle.

**Правило:** для substantial work (P0/epic, >5 файлов, >30 мин):

1. **СНАЧАЛА** `git checkout -b pr-{namespace}-{slug}` + `git push -u origin pr-{namespace}-{slug}` (claim namespace на remote, push empty branch OK)
2. **ПОТОМ** работа: Edit / Write / Bash
3. **После каждого** logical layer (yaml / scripts / skills / docs) → `git add <explicit-paths>` + commit + `git push` immediately
4. **При detect parallel session** (`ps aux | grep -c "git push" > 0`) или recurring `.git/index.lock` → `git worktree add /tmp/recovery-{bead}` + работа оттуда

**Anti-pattern (запрещено):**

- ❌ Делать substantial work на `main` без push → Cowork reset уничтожит
- ❌ Push в конце сессии, не после каждого layer — потеряешь промежуточный прогресс
- ❌ `git add -A` / `git add .` — staging чужой работы (`metrics-methodology-curator.md` от другого agent)

**Retry policy для `.git/index.lock`:** exponential backoff 1-2-4-8-16-30s (max 5 min), потом `lsof .git/index.lock` + `rm` если stale process. Не сдаваться после 1 retry.

**Hard fail:** Cowork reset wiped commits в этой сессии (видно в reflog) — это RCA-incident `category: silent-reset-data-loss`, требует push-first protocol enforcement.

## Workflow

1. Run memory bootstrap or at minimum read:
   - `.codex-memory/MEMORY.md`
   - `.codex-memory/topics/git-parallel-coordination.md`
   - `.codex-memory/runtime/git-sync-intents.md`
2. Resolve the current bead.
3. If overlap is possible, run `sync-thread-with-neighbor-beads`.
4. Before git-changing work, add one latest-first row to `.codex-memory/runtime/git-sync-intents.md` with:
   - timestamp
   - bead
   - branch / target
   - merge owner / handoff target
   - paths / scope
   - git intent
   - status
   - cleanup note
4.4. **Sit-down dirty-tree triage (RCA 2026-05-13 — anti-block contract):** перед любым `git pull` / `git rebase` / `git checkout -b` / `git stash` / `git add` / `git commit` / `git push` агент **обязан** запустить `python3 scripts/git_workspace_inventory.py`, прочитать `<internal-folder>/git-workspace-inventory-{date}.md`, классифицировать dirty entries по 12 категориям и принять per-layer decision. **Запрещено** возвращать owner «реши что коммитить из 800+ файлов» — это decision-handoff. **Запрещено** делать `git add -A` / `git stash` blind или ad-hoc reset без inventory output. Полный 6-шаговый алгоритм + per-category default actions: [`5-sync-github-checklist` §0.0 Sit-down dirty-tree triage](.agents/skills/5-sync-github-checklist/SKILL.md). Hard fails: `dirty-tree-triage-skipped`, `decision-handoff-instead-of-triage`, `ad-hoc-tree-decision-without-triage`.
4.5. **Submodule pre-flight (RCA 2026-05-13):** перед любым `git pull --rebase` / `git rebase` / `make team-main-sync` прочитать [`5-sync-github-checklist` §2.0 Per-submodule classification](.agents/skills/5-sync-github-checklist/SKILL.md) и SSOT [`submodules-and-projects-registry.yaml`](submodules-and-projects-registry.yaml). Для каждого submodule с pointer divergence или `-dirty` suffix применить policy из таблицы (11 submodules). **Hard fail:** ad-hoc reset/bump pointer'а submodule без сверки с YAML → `category: submodule-classification-not-from-ssot`.
5. Execute the git work.
   - In one shared worktree, run **only one git write-like operation at a time**.
   - Do not run `git add` / `git reset` / `git commit` / `git merge` in parallel tabs, parallel tool calls, or simultaneously with GUI staging if they touch the same root repo.
   - If the symptom is `Unable to create '.git/index.lock': File exists`, first treat it as a lock-race check, not immediately as a content blocker.
   - **HEAD-pin guard перед каждым write op (RCA 2026-05-10 — silent HEAD switch by Cowork session click):** перед `git add` / `git commit` / `git push` обязательный preflight `git symbolic-ref HEAD` и сверка с pinned значением branch из intent row (шаг 4). При mismatch — **abort, не autorecover**, alert owner: «HEAD switched from `<expected>` to `<actual>` by another process — не коммичу». Sequential ordering сам по себе **не** защищает от внешних HEAD switches: Cowork session click, Cursor branch picker, Codex morning-action-pack делают `git checkout` в shared `.git/` без уведомления. Single-write-at-a-time предотвращает только `index.lock` race, не silent rebase target switching.
   - **Worktree-first для long-running write tasks:** если работа > 30 мин и шанс что owner откроет соседнюю Cowork session отличный от нуля — **обязательно** работать в выделенном `.claude/worktrees/<slug>/`, не в root worktree. См. AGENTS.md §«Защитный worktree (не просто ветка)».
   - **Rebase с отключёнными хуками:** при `git pull --rebase` использовать `git -c core.hooksPath=/dev/null pull --rebase origin main`. Хук `post_sync_bootstrap_guard.py` мутирует файлы (`core-auto.mdc` и др.) между шагами rebase, вызывая `error: Your local changes would be overwritten by merge`. Push после rebase — тоже через `git -c core.hooksPath=/dev/null push origin main`. Полный протокол: [sync-github-checklist §0.1](.agents/skills/5-sync-github-checklist/SKILL.md).
   - **Broken submodule worktree recovery:** если `git status/rebase/cherry-pick` падает на
     `fatal: not a git repository: .../.git/worktrees/<wt>/modules/<submodule>`, сначала снять
     незавершённый state (`git cherry-pick --quit`, `git rebase --quit`), затем восстановить именно
     submodule-worktree из root checkout: `git -C <root>/<submodule> worktree add --detach <wt>/<submodule> <gitlink-sha>`.
     Не продолжать sequencer, пока submodule gitdir не восстановлен: иначе `--skip/--continue`
     не может reset submodule index и оставляет повторный mid-rebase мусор.
   - **Классификация грязного дерева перед stage-all:** не делать `git add -A` на грязном main без предварительной разбивки dirty-файлов на категории (скрипт-генерированные, битые симлинки, runtime-артефакты, backup-директории, легитимные изменения, embedded repos). Таблица классификации: [sync-github-checklist §0.1](.agents/skills/5-sync-github-checklist/SKILL.md) и [main-cleanliness-guard §2.2](.agents/skills/0-main-cleanliness-guard/SKILL.md).
6. After outcome is known:
   - successful and fully resolved:
     - remove or close the runtime intent row
     - keep only durable lessons in `.codex-memory/`
   - successful but handoff/open risk remains:
     - update the runtime row with the remaining boundary
   - recurring workaround / drift / stale contour:
     - log through `ai-legacy-log`
   - real incident / breakage / RCA-worthy failure:
     - update `<internal-folder>/ai.incidents.md`
7. Update the bead note with what git action was actually performed and what cleanup path was chosen.

## Main integration ownership

- One active child bead should map to one active branch or worktree.
- The agent working in that child bead owns only the branch-local changes for that scope.
- Merge, rebase, or push to `main` belongs to the parent epic owner by default.
- If someone else should do the final integration, create an explicit merge-owner bead and name the handoff target in the runtime intent row before shared-branch work starts.
- Do not let multiple agents independently "finish in main" from sibling beads.

## Worktree teardown — branch merged → prune worktree (V1.4, RCA 2026-05-28)

**Принцип-инвариант:** worktree существует только пока его ветка НЕ в `origin/main`. Как только ветка смержена — worktree это мёртвый след, который (a) засоряет `git worktree list`, (b) держит per-session runtime-untracked файлы (`.reasoning-log/`, `.beads/`, hook `.state`), которые выглядят как «untracked lost work» в каждом worktree. RCA-источник 2026-05-28: 48 worktrees sprawl, 7 gone-dir, 41/42 «untracked» = runtime deny-list noise.

**Teardown DoD (после merge ветки в origin/main):**

1. **Не удаляй вручную ad-hoc.** Канон — `make prune-merged-worktrees` (dry-run) → проверь verdict → `EXECUTE=1 make prune-merged-worktrees`.
2. Prune действует только на **merged-and-clean** (ветка ancestor of `origin/main` + нет real-dirty не-deny-list файлов) и **gone-dir** (`/tmp/*` исчезли). Catastrophe-guard **никогда** не трогает worktree с real untracked/modified кодом или unmerged-веткой (Nothing-lost).
3. Каждый prune-merged-clean worktree сначала получает `archive/<branch>-pruned-<date>` тег (recovery ref), потом `git worktree remove --force` + `git branch -d`.
4. Runtime-noise (`.reasoning-log/`, `.beads/`, hook `.state`) теперь в `.gitignore` — не появляется как untracked. Если worktree показывает untracked файл вне deny-list — это **real work** → закоммить в ветку ДО teardown.

**Mechanical SSOT:** `<internal-module>/scripts/verify_branch_hygiene.py --prune [--execute]` (классификатор + 8 unit-тестов `test_worktree_prune_classifier.py`). cleanup-guardian git-state category флагует sprawl; этот target его закрывает.

## Post-sync disposition

After a successful sync, decide explicitly:

- delete from runtime memory:
  - completed git intent rows with no remaining overlap or handoff risk
- keep in runtime memory:
  - only active git intent rows where a next git step is still pending
- keep in durable memory:
  - proven git protocol, branch/worktree lessons, verified recovery rules
- move to `ai.legacy.md`:
  - recurring git drift, old workaround, stale branch/process contour, repeated footgun
- move to `ai.incidents.md`:
  - broken sync that caused regression, lost work, publish failure, or RCA-worthy incident


## V1.2 — bd merge-slot + branch-name bead-ref + dolt remote migration (RCA 2026-05-24)

### bd merge-slot — native primitive для serialized conflict resolution

**RCA-источник:** auditor verdict 2026-05-24 + 9-statement validation. До V1.2 мы пытались строить serialized conflict resolution через worktree + locks вручную. bd CLI имеет это нативно через `bd merge-slot` — exclusive-access primitive предотвращающий «monkey knife fights» (multiple agents race на conflict resolution → cascading conflicts).

**Дополнение к §«Защитный worktree» (RCA 2026-04-17):**
- **worktree** изолирует **FILE** changes (per-task working tree)
- **bd merge-slot** serializes **MERGE** ops (один agent держит slot на time)

Это **разные слои**. Worktree даёт parallel writes; merge-slot — serialized integration.

**Канонический workflow для 3+ параллельных агентов:**

```bash
# Setup (один раз per rig):
bd merge-slot create                   # ✓ Created merge slot: <prefix>-merge-slot

# Agent A workflow перед merge в integration branch:
bd merge-slot check                    # available?
bd merge-slot acquire                  # держит slot exclusively
# ... выполняет merge / rebase / conflict resolution ...
bd merge-slot release                  # отпускает для следующего

# Agent B параллельно:
bd merge-slot check                    # not available; B попадает в waiters queue (priority-ordered)
# Agent B блокируется до release Agent A
```

**Status / metadata semantics:**
- `status=open`: slot available
- `status=in_progress`: slot held
- `metadata.holder`: текущий agent (для observability)
- `metadata.waiters`: priority-ordered queue

**Hard fail:** Agent делает merge / rebase в integration branch БЕЗ `bd merge-slot acquire` при наличии >1 active parallel agent в репо → `category: parallel-merge-without-slot-acquire`.

### Branch-name JTBD-self-describing convention (RCA 2026-05-24 + RCA 2026-05-26 hardening)

**Принцип-инвариант (universal, не case detail):** branch name **обязан** быть **self-describing JTBD slug** + bead-id reference. Owner steering 2026-05-26: «обрати внимание что worktree названо дурацки как и beads тикеты — они должны отражать JTBD работу, которую мы делаем и outcome от этой работы».

Branch read in `git branch -a` / IDE sidebar / `git worktree list` должен за 5 секунд позволять читателю понять **что эта ветка делает**, не дёргая `bd show <id>`.

**Канонические patterns (наш workspace):**
- ✅ `pr-rick-<jtbd-slug>` — слаг ≥10 chars ИЛИ ≥2 hyphen-separated tokens. Пример: `pr-rick-luis-funnel-mapping-rick-exchange`, `pr-rick-parallel-agents-coord`
- ✅ `pr-rick-<jtbd-slug>-<bead-id>` — slug + traceability. Пример: `pr-rick-luis-funnel-mapping-wwc` (slug + bead id `wwc`)
- ✅ `<type>/bd-<id>-<slug>` где type ∈ {feature, bugfix, refactor, docs, integration, hotfix, test, chore, migration, experiment}
- ✅ `bd-<id>-<slug>` (generic bd с slug)

**Anti-patterns (FLAG, не allowlist):**
- ❌ `pr-rick-wwc` — pure 3-char auto-id from `bd create` без JTBD slug. RCA-источник 2026-05-26.
- ❌ `pr-rick-4eh` — same class (был misleading example в этой skill до RCA 2026-05-26).
- ❌ `pr-rick-x` — single-char, нечитаемо.
- ❌ `pr-rick-task` — generic placeholder без specificity.
- ❌ `pr-rick-fix` / `pr-rick-update` / `pr-rick-test` — verb-only без object.

**Минимум для PASS:** slug часть (после `pr-rick-` или `bd-`) **либо** длина ≥10 chars, **либо** содержит ≥2 hyphen-separated tokens (e.g. `pr-rick-fix-luis-x` = 3 tokens после `pr-rick-` → PASS даже если суммарно <10).

**Allowlist (no flag, special-purpose):** `main`, `master`, `production`, `release`, `claude/*` (Cowork auto-branches — IDE generates names), `wip/*` (intentional WIP scratch), `tmp/*`, `rescue/*` (emergency recovery).

**Mechanical enforcement:** `.claude/hooks/branch_name_bead_ref_check.py` PreToolUse Bash matcher на `git checkout -b` / `git switch -c` / `git worktree add -b` / `git branch <new>`. **Phase 1 (current): WARN-only** для adoption. Hook теперь делает 2 checks:
1. Structural: branch matches bead-ref pattern (existing regex)
2. Semantic (NEW RCA 2026-05-26): slug часть ≥10 chars OR ≥2 hyphens — иначе WARN «pure auto-id без JTBD slug»

Override (legitimate exception): `BRANCH_NAME_BEAD_ACK="<reason ≥12 chars>"` (universal — covers both structural and semantic anti-patterns).

**Canonical creation path — `make worktree BEAD=<id>` (RCA 2026-06-02):** не собирай slug руками — запусти `make worktree BEAD=pr-rick-7ms7`. Это источник-аффорданс к `branch_name_bead_ref_check`: читает bead title (`bd show --json`), derive 3-5 JTBD-токенов (транслит <teammate>ицы, dropped stop/JTBD-formula/bare-verb words), composes `pr-rick-<slug>-<bead-id>`, verifies против gate-предиката (slug ≥10 chars OR ≥2 hyphens), и делает `git worktree add` с ПОЛНЫМ checkout (без `--no-checkout`/`--sparse`, respects `git_worktree_completeness_gate`). Имя ЗАВЕДОМО проходит gate. SSOT: `scripts/make_worktree.py`. Override slug: `SLUG="..."`. Preview: `DRY_RUN=1`. Auto-claim: `CLAIM=1`.

**PR naming continuity (RCA 2026-06-07):** PR — это публикация той же branch в `main`, а не новая сущность с новым названием. Перед `gh pr create`:
1. branch уже должна быть `pr-rick-<jtbd-slug>-<bead-id>`;
2. worktree folder basename должен совпадать с branch;
3. stale-base guard уже пройден;
4. PR создаётся с явным JTBD title: `gh pr create --head <branch> --base main --title="Когда ..., хотим ..."`; `--fill` запрещён как источник PR title, потому что теряет связь с bead title;
5. Mechanical backstops: `.claude/hooks/branch_name_bead_ref_check.py` проверяет branch/worktree форму, `.claude/hooks/pr_bead_jtbd_ref_check.py` проверяет JTBD bead title -> branch/worktree -> PR title continuity. Emergency override only with `BRANCH_NAME_BEAD_ACK` / `JTBD_PROJECT_NAMING_ACK` and a real reason.

**Naming derivation procedure (что делает `make worktree` под капотом / manual fallback):**
1. Read bead title через `bd show <id> --json` (e.g. «Luis funnel mapping: 9-step JTBD → Rick exchange /create payloads + skill + tests for cell-level cross-checks»)
2. Extract 3-5 key tokens reflecting JTBD/outcome: `luis-funnel-mapping-rick-exchange-payloads`
3. Compose: `pr-rick-<slug>` OR `pr-rick-<slug>-<bead-id>` (latter preserves traceability link to bead)
4. Verify: would teammate without bd CLI understand the branch purpose? Yes → ship. No → re-derive.

Example readable layout (`git worktree list` clarity):
```
.../pr-rick-luis-funnel-mapping-rick-exchange-wwc/   ← slug + bead-id
.../pr-rick-typhoon-products-quiz-2026-05-25/         ← slug + date suffix
.../pr-rick-jtbd-self-describing-branch-names/        ← slug only
.../pr-rick-wwc/                                       ← ❌ anti-pattern, flagged
```

### Dolt remote vs embedded — honest challenge (RCA 2026-05-24 owner steering)

Owner challenged 2026-05-24: «почему обоснуй? почему не перейти на dolt? обоснуй и сделай челендж». Честный анализ, не «миграция меня беспокоит».

**Состояние runtime 2026-05-24:** 6 active worktrees в workspace (pr-rick-typhoon-form-mapping, pr-rick-kb-guardian-offer-checklist, pr-rick-portable-hooks, pr-rickai-ui-kit-architecture, beads-sync, pr-rick-parallel-agents-coord). Это **за порогом** который я первоначально ставил для миграции (3+).

**Falsification 3 alternative hypotheses:**

| Hypothesis | Evidence | Verdict |
|---|---|---|
| **H1: embedded + git sync достаточно** | `git log --grep="conflict.*issues.jsonl"` — **0 historical merge conflicts** на JSONL за всю историю workspace. bd `export.auto=true` + `export.interval=60s` throttling работает. Cowork Милена / Codex / Cursor — никто не репортил bd state collision | **confirmed для текущего scale (6 worktrees, асинхронные write ops)** |
| **H2: Dolt remote (DoltHub free tier) сейчас лучше** | DoltHub free tier существует (https://www.dolthub.com — managed Dolt hosting), bd CLI имеет `bd dolt remote add origin <url>` нативно. Setup ~30 мин once. **Но**: vendor lock-in, network call per bd write (~50-200ms latency), team-wide adoption required (Codex morning-pack + Cowork + Cursor должны знать URL) | **partial — works но cost > benefit** при 0 observed conflicts |
| **H3: Self-hosted Dolt server (dolt sql-server в Docker)** | Eliminates vendor lock-in. Cost: maintain Docker image, backup strategy, access management. ~4-8h initial + ongoing ops | **falsified для нашего scale** — ops burden > benefit |

**3 honest decision factors против миграции прямо сейчас:**

1. **Vendor lock-in / network dependency** — DoltHub down → bd write blocked. Сейчас embedded = local SSOT, нет внешней зависимости.
2. **Latency tax** — каждый `bd create` / `update` делает network call к remote. На локальной работе embedded быстрее.
3. **Team-wide adoption coordination** — Codex / Cowork / Cursor + Lisa team должны все pull new bootstrap. Это change-management cost.

**3 honest decision factors ЗА миграцию когда-то:**

1. **Native concurrent writes** — Dolt remote мержит structured data без line-ordering JSONL conflicts. Сейчас pain нулевой, но при росте >10 active agents — становится bottleneck.
2. **Real-time visibility** — `bd ready` shows live shared state без git pull rebase loop.
3. **bd doctor unlocked** — embedded mode НЕ поддерживает `bd doctor` (verified runtime); server mode = full diagnostics.

**Финальный verdict (после falsification):**

- **Сейчас (6 worktrees, 0 observed JSONL conflicts):** оставляем embedded + git sync. Не потому что «миграция беспокоит», а потому что **cost-benefit не оправдывает миграцию пока pain не материализовался**.
- **Trigger миграции (precise):** ИЛИ (a) `git log -p -- .beads/issues.jsonl` показывает реальные line-conflict на same-issue concurrent writes ≥1/неделю; ИЛИ (b) количество active worktrees переваливает за 10; ИЛИ (c) Codex / Cowork требует concurrent write features которые embedded не поддерживает.
- **Pilot setup (concrete, любой time):** `bd dolt remote add origin <doltlab-url>` + `bd dolt push --first-time` + add в `make bootstrap`. **Reversible** — `bd dolt remote remove origin` снимает.

**Recommendation:** ставлю pilot setup в gap-list следующей сессии как **opt-in, не mandatory**. Когда trigger материализуется — миграция занимает <2h, не блокер.

## V1.1 — catastrophe-guard rule + verify-after bidirectional (RCA 2026-05-23)

### Catastrophe-guard rule (universal — ОБЯЗАТЕЛЬНО для ADD-only ops)

Применимо к ЛЮБОЙ операции claiming «nothing-lost» / «ADD-only» / «no revert» (consolidation, extraction, mass-commit, branch-merge):

ПЕРЕД push требуется ВСЕ 3 sanity-check'a:
1. files-removed count: diff --cached --diff-filter=D --name-only count = 0 (или явный intentional ACK)
2. line-deletions total: diff --cached --shortstat deletions < 500 (mass-wipe threshold)
3. changed-files count == staged-files count (touched-the-unexpected catch)

Любой fail → SAFETY-ABORT до push. Override для intentional mass cleanup: GIT_PUSH_DELETION_ACK env с reason >= 10 chars.

Source: RCA 2026-05-19 PR #108 — worktree-add no-checkout произвело empty-index commit → merge wiped 27,772 files / 55M line removals from origin/main. Mechanical enforcement: .claude/hooks/pre_push_deletion_guard.py (registered scripts/setup/hooks-registry.json, активируется make bootstrap).

### Verify-after bidirectional rule (anti false-completeness)

ОБЯЗАТЕЛЬНО для ЛЮБОГО claim о статусе work (как «done», так и «not-started»):

- «Done» claim требует authoritative gh pr view --json state + cat-file -e origin/main:<sample> proof. Никаких «commit pushed → done».
- «Failed/not-started/not-landed» claim ТАКЖЕ требует authoritative state snapshot. Silent fail в background может выглядеть как «не запустилось» но реально in-flight slow.
- «In-flight / launched / spawned» — это L0 action, НЕ L1 checkpoint. Не должно использоваться как claim о delivered state.
- Background subagent notifications не переживают session-resume — после resume обязателен заново authoritative state check.
- Multiple-marker verify: один substring grep может false-negative из-за formatting drift. Verify по >=2 independent markers per claim.

Source: RCA 2026-05-23 — пара эпизодов в одной session: (a) agent declared subagent's H5 patch «did not land» based on wrong-substring grep, actually H5 landed (5 markers in origin/main); (b) auditor declared «no PR in flight» при snapshot до того как параллельный bash завершил PR #115 merge. Обе ошибки — opposite directions того же класса false-completeness pattern.

### Cross-references

- consolidate_branches.py — embeds catastrophe-guard inline (H5/H6/H8 patches landed PR #116; B1 PR #113)
- 5-sync-github-checklist V1.0 framework — 8-step operational playbook applies these rules at each step
- AGENTS.md §Always-green main invariant — overarching invariant which catastrophe-guard mechanically enforces


## Branch closure DoD — file-level ground truth (V1.3, RCA 2026-05-25)

Перед declared `done` / `consolidated` / `closed` для ANY feature/wip branch обязательны 5 mechanical checks. Закрывает 2-й рецидив `nothing-lost-false-claim` (DoD должен быть file-level, не commit-level — большие data/JSON files или новые skill folders могут добавиться в commits без отражения в commit subjects, скрытое от log-based view).

1. **Commit count (proxy view):** `N_commits=$(git log origin/main..<branch> --oneline | wc -l)`
2. **File count (ground truth):** `N_files=$(git diff --name-status origin/main..<branch> | wc -l)` — единица DoD = файл, не commit
3. **Sanity ratio:** если `N_files > N_commits × 10` — STOP, branch содержит большой file diff не отражённый в commit subjects (`proxy-metric anchoring` failure); second-pass обязателен
4. **Per-status classification:**
   - `git diff --name-status origin/main..<branch> | awk '$1=="A"'` — ADDED: для каждого `git cat-file -e origin/main:<path>` (есть в main → (b) superseded, нет → (a)-candidate landed via focused PR)
   - `git diff --name-status origin/main..<branch> | awk '$1=="M"'` — MODIFIED: blob-compare `git rev-parse origin/main:<file>` vs `HEAD:<file>`; main untouched since merge-base → safe extract; иначе (c) owner-decision с конкретной merge command
   - `git diff --name-status origin/main..<branch> | awk '$1=="D"'` — DELETED: verify intentional cleanup в main через `git log origin/main -- <path>`, НЕ accidental revert. При branch-merge эти deletions vanish из main → `category: stale-base-revert`
5. **Run Evidence обязан содержать обе метрики:** `commits_classified: N / files_classified: M / ratio sanity: yes (M < N × 10) или no (second-pass required)`

Mechanical hook `.claude/hooks/branch_closure_diff_check.py` (PreToolUse `Bash` matcher для `gh pr merge` / `git push origin <branch>` / `git branch -d`) BLOCKS если ratio fail без env `BRANCH_CLOSURE_DIFF_ACK=<reason 12+chars>`.

Hard fail: declared done без `git diff --name-status` cross-check в Run Evidence → `category: branch-closure-log-based-not-diff-based`.

**RCA-источник 2026-05-25:** agent declared «branch consolidation complete, trust 88/100» после classification 5 ahead commits, не запустив `git diff --name-status` (показал бы 182 файла = 22 ADDED + 91 DELETED + 69 MODIFIED, 388,969 строк уникальной работы — skill `1-client-workspace-bootstrap` 15 files + Standard 4.6.1 + 4 huge data dumps). Закрыто PR #135 (governance landed) + PR #136 (этот mechanical gate).


## Forbidden

- Do not start git-changing work without a bead.
- Do not run parallel git write operations in the same worktree. Reading commands may run in parallel; write-like commands may not.
- Do not leave stale completed rows in `git-sync-intents.md`.
- Do not store full git history or long postmortems in runtime memory.
- Do not treat runtime git intent as a replacement for `.beads`.


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/` → duckdb). Узел «свернул не туда»: `scripts/reasoning_log/graph.py --find-divergence`. Ручная markdown-таблица в чат — только если owner явно спросил «почему ты так решил». Полный протокол: `agent-reasoning-log/SKILL.md` (v2, RCA 2026-05-17).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Parallel-session hazard neutralization — ответственность активного агента (RCA 2026-05-19)

Обнаружение и нейтрализация параллельно-сессионных опасностей (branch-substitution,
shared dirty tree, чужие живые сессии, spawn-pressure хуки) И верификация делегированной
субагентам работы по authoritative git/gh state (НЕ по слову субагента, НЕ по факту
launch — background-результат не переживает session-resume) — ОБЯЗАННОСТЬ активного
агента, НЕ owner-действие. SSOT принципа — AGENTS.md §Agent role × invariant matrix
(R2/R3); здесь role-форма, текст инвариантов не дублируется.

Агент ОБЯЗАН сам, в той же сессии:
1. Детектить живые сессии (ps/PID) ДО git-write.
2. При чужой живой сессии ИЛИ dirty-tree ≥ BLOCK → дефолт clone-isolated worktree
   (git worktree add /tmp/... origin/main → edit → push → PR), без запроса owner.
3. Нейтрализовать spawn-pressure (HARD-BLOCK → soft-nudge) вместо жалобы.
4. Делегировал субагенту → ОБЯЗАН verify-after: authoritative `git show origin/main:<path>`
   / `gh pr view --json state`. «Запустил субагента» ≠ «сделано». Атомарный scope
   делегирования (один субагент = одна закрываемая единица), не compound.
5. Взять ownership консолидации (extract ADDED-only, классиф (a)/(b)/(c), PR) —
   не перекладывать на owner. Owner-действие только для физически недостижимого
   (закрыть GUI-окно) → message по 3-human-help-url-mandatory.

Hard fail: «делегировал и считаю сделанным без authoritative verify» →
category: delegated-not-verified. «параллельные сессии — закрой окна» как
owner-effort >0 без clone-isolated дефолта → category: parallel-session-hazard-offloaded.


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick (включая TaskMaster и связанные стандарты Heroes Rickai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.


---

## Skill contract (Standard 4.8 §B)

### Hired for JTBD

Когда параллельный агент меняет branch/worktree/history, ты как агент хочешь согласовать git-намерение через memory + HEAD-pin, чтобы не помешать соседнему треду и не подменить ветку.

### Workflow

1. read memory (MEMORY.md + git-parallel topic + git-sync-intents) -> 2. resolve bead -> 3. intent row latest-first -> 4. HEAD-pin preflight перед каждым write op -> 5. one git-write-op at a time -> 6. execute -> 7. post-sync disposition.

### Input checklist

- [ ] git-sync-intents.md, branch-ownership-ledger.jsonl, current bead, git symbolic-ref HEAD

### Output checklist

- [ ] intent row записан до write, HEAD-pin verified, post-sync cleanup выполнен, no parallel git-write collision

### Outcome checklist (owner benefit)

- [ ] параллельные сессии не подменяют ветки и не теряют наработки друг друга — каждый bead = одна ветка/worktree

### Owner value

owner value: нет инцидента коммит лёг не на ту ветку / потеряна работа teammate при rebase — координация механическая, не на доверии

### Self-falsification gate

После исполнения скилл обязан прогнать гипотезу «этот скилл закрыл свой JTBD» через [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md): gap table Ожидание | Факт | Δ, verdict confirmed | partial | falsified. При partial/falsified — новая рабочая гипотеза, не закрывать как done.

### Reasoning Log Protocol

Каждое исполнение ведёт reasoning log в чате (решения + evidence + gap + blocking instruction) и строку в `<internal-folder>/ai.incidents.md` §Append-only trace. Hard fail: без reasoning log скилл не исполнен. Канон — `agent-reasoning-log` в AGENTS.md.

### Связанные скилы / Related skills

- [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md) — self-falsification gate
- [`5-sync-github-checklist`](../5-sync-github-checklist/SKILL.md) — общий sync ритуал + io-checklist макрос §4.9
- `agent-reasoning-log` — обязательный reasoning log протокол (AGENTS.md)
