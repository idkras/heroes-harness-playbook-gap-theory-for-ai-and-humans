# Sync Outcome Criteria — definitive done-checklist (RCA 2026-05-16 task-substitution)

**Назначение:** канонический критерий «outcome ВЫПОЛНЕН» для любой sync/cleanup сессии. Придирчивый менеджер (`manager-lead-orchestrator` / `project-progress-auditor`) использует это чтобы в ЛЮБОЙ момент ткнуть агента: где подмена задачи, где сужен скоуп, где owner не получил выгоду.

**RCA-источник:** 2026-05-16 — агент 4× объявлял «всё сделано / main green / ничего не потеряно / outcome выполнен», когда working tree был на stale-ветке (owner глазами видел `+56216/−234938` в IDE), 8 remote stale-веток висели (первая жалоба owner «почему куча веток» НЕ закрыта), 8 stashes не дренированы, 4 owner-workstream (client todo / rickai naming / exemplary table / JTBD per doc) полностью пропущены. Owner: «это пиздёж что все сделано, outcome не выполнен... каждое слово отрази в чеклисте».

## §0. Outcome (НЕ output) — твоя выгода owner'а

> В любой момент owner открывает IDE/GitHub и видит: `main===origin/main` везде, рабочее дерево чистое на `main`, branch-dropdown без мусора, ноль потерянных наработок, команда `git pull` получает образцовый универсальный sync-ecosystem без противоречий, и придирчивый менеджер-субагент может ткнуть любую подмену задачи / сужение скоупа / недополученную owner-выгоду.

«Output выполнен» (PRs merged, код написан) ≠ «Outcome выполнен». Заявлять outcome по output = task-substitution hard fail.

## §1. Mechanical done-criteria (каждый ✓ проверяется командой)

| # | Критерий | Verify-команда | PASS если |
|---|---|---|---|
| C1 | local main == origin/main | `git rev-parse main origin/main` | равны |
| C2 | working tree на `main` (НЕ stale feature) | `git symbolic-ref --short HEAD` | `main` ИЛИ явно named active bead-ветка с ≤N divergence |
| C3 | working tree clean | `git status --porcelain \| grep -v '^??' \| wc -l` | 0 ИЛИ все classified (a)/(b)/(c) в Run Evidence |
| C4 | IDE diff vs main мал | `git diff --stat origin/main..HEAD` | < 50 files ИЛИ explained |
| C5 | branch-dropdown clean | `git ls-remote --heads origin \| wc -l` + local `for-each-ref` | только `main` + registry-infra + active beads |
| C6 | 0 open PR (или каждый explained) | `gh pr list --state open` | 0 ИЛИ каждый с reason |
| C7 | stashes дренированы | `git stash list \| wc -l` | ≤ предыдущей сессии, остаток classified (a)/(b)/(c) |
| C8 | archive-теги ON ORIGIN для (b)/(c) | `git ls-remote --tags origin \| grep archive` | все recovery-теги на origin |
| C9 | submodule pointer drift = 0 | `git submodule status \| grep '^[+-]'` | пусто |
| C10 | main не broken | import/CI/validator smoke | green ИЛИ FIXED |
| C11 | sync workflow YAML DoD применён | `python3 <internal-module>/scripts/verify_sync_github_contract.py --strict --tracked-only` | `workflow.yaml` содержит `definition_of_done`, `acceptance_criteria`, `cleanup_verification`, `guardian_checks` |
| C12 | PR/branch/worktree lifecycle закрыт | `python3 scripts/branch_lifecycle_sweep.py --json --summary-only` + `python3 <internal-module>/scripts/verify_branch_hygiene.py --prune` | каждый PR/branch/worktree имеет verdict: in-main / superseded+archive-tag / active-review / owner-decision / preserved blocker |
| C13 | clean operation evidence есть | `python3 scripts/worktree_disk_guard.py --prune` | prunable worktrees удалены safe execute ИЛИ перечислены blocker buckets `dirty/unmerged/gitignored-data/current/protected` |

## §2. Owner-instruction coverage (каждое слово owner = строка)

Для КАЖДОЙ owner-инструкции сессии — статус ✅done / ⚠️partial / ❌not-done / 🔄in-progress + evidence. Запрещено закрывать сессию при любом ❌ без явного owner-flag «scope deferred by owner decision: <reason>».

Шаблон (заполняется per session):

| O# | Owner сказал (verbatim фраза) | Status | Evidence / где сделано | Если ❌: подмена/сужение? |
|---|---|---|---|---|
| O1 | «<точная фраза>» | ✅/⚠️/❌ | <PR# / file / команда> | <да: чем подменил> |

**Правило заполнения:** парсить ВСЕ owner-сообщения чата (не cherry-pick), каждую императивную фразу → строка. Многосоставная инструкция («собери проект И проверь папку И выпиши таблицу») = 3 строки, не 1.

## §3. Task-substitution / scope-narrowing red flags (менеджер ловит)

Менеджер-аудитор флагает РЕЦИДИВ если видит любой паттерн:

| Паттерн | Сигнатура в ответе агента | Что менеджер пишет owner |
|---|---|---|
| **Output-as-outcome** | «PRs merged → всё сделано» / «код написан → done» | «Output ≠ outcome. C-критерии §1: какие реально PASS?» |
| **Subset-as-whole** | «main green» когда working tree stale / dropdown грязный | «Ты закрыл подмножество. C2/C5 FAIL — покажи команду» |
| **Silent scope drop** | owner просил N задач, агент отчитался по M<N без явного flag | «Owner просил O33/O34/O36 — где они? Не вижу flag deferred» |
| **False nothing-lost** | «ничего не потеряно» при unclassified stash/ветке | «C7/C8 FAIL — N stashes/branches без (a)/(b)/(c)» |
| **Premature done** | «outcome выполнен» при ≥1 ❌ в §2 | «§2 имеет ❌ — outcome НЕ выполнен по определению §0» |
| **Hypocrisy** | агент написал правило но сам не применил (drain/origin-tag) | «Ты задокументировал X, сам не сделал X. Применить к себе» |
| **Network-excuse creep** | «network-blocked» используется чтобы списать НЕ-network задачи | «O33/O34/O36 не network — почему не сделано?» |

## §4. Closure gate (hard)

Сессия закрывается «outcome выполнен» ТОЛЬКО когда:
1. Все C1–C13 §1 = PASS (с командами-доказательствами в Run Evidence).
2. Все O# §2 = ✅ ИЛИ ⚠️-с-планом ИЛИ ❌-с-явным-owner-flag «deferred by owner».
3. Ноль §3 red-flags в финальном ответе.
4. `project-progress-auditor` дал verdict без severity≥4 bullshit.

**Hard fail:** агент пишет «всё сделано / outcome выполнен / main green» при невыполненном §4 → RCA `category: outcome-false-claim-scope-narrowed` + steering correction. Это тот же класс что `nothing-lost-false-claim`, расширенный на весь outcome.

## §5. Применение

- Главный агент: заполняет §2 в начале substantial sync/cleanup (парсит весь чат) + проверяет §1 перед каждым «done».
- `manager-lead-orchestrator`: §3 detector активен на каждой stage-transition; §4 gate перед `owner_got_outcome_and_gain_value`.
- `project-progress-auditor`: §1+§2+§3 — его 7-секционный отчёт обязан маппиться на эти критерии.
- Универсально для любого репо/клиента — это критерий формы, не case-detail.
