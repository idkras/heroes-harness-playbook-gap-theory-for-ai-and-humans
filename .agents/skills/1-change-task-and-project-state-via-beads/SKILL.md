---
name: change-task-and-project-state-via-beads
description: "Use when planning work, creating or updating tasks/projects, triaging backlog, changing status/blockers/priority, or synchronizing todo.md / project todo files. Based on the .beads operating standard. Use when user says \"обнови beads\", \"измени статус задачи\", \"создай задачу\", or \"синхронизируй todo\"."
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `<internal-module>/shared/credentials_manager.py`.

# Когда нужно менять состояние задач и проектов, хотим сначала обновить `.beads`, а потом отражения (`change-task-and-project-state-via-beads`)

## Hired for JTBD — задача, которую решает клиент

Когда нужно создать, обновить, закрыть или переприоритизировать задачу/проект и не потерять главный источник истины (Single Source of Truth - SSOT), этот навык нанимается на работу `сначала изменить состояние в .beads, потом отразить его в todo.md и других слоях, понятных людям`.

## Purpose

This workspace is transitioning to a `beads-first` operating model:

- `.beads` = primary editable task graph
- `todo.md` and project `*.todo.md` = reflection / registry / communication layer
- `duckdb` = legacy or import-only mirror when still present

Agents must not treat `todo.md` as the primary (Single Source of Truth) place where operational state is edited.

## See also

- **1-beads-ticket-full-display** (`.agents/skills/1-beads-ticket-full-display/SKILL.md`) — показать тикет из `bd show` / Dolt **человекочитаемо**; `.beads/issues.jsonl` допустим только как fallback/export surface. Формат: таблица полей верхнего уровня, распакованный `description` обычным Markdown (не только JSON), итоговая output-таблица (Effort использования output = Standard 2.8, 0–5) и next-action digest с **усилием человека (0–100, клик = 50+)** по шкале A `2-rca-incidents §7.2`; сырой JSON опционально.

## When to use

- Creating a new task or project
- Updating status, blockers, priority, assignee, parent-child links, comments
- Backlog triage or release planning
- Reflecting work into root `todo.md`, project `*.todo.md`, or tickets registries
- Auditing whether a project is already migrated to `.beads`

## Step 0: Pin verify + CHEATSHEET sync (ОБЯЗАТЕЛЬНО, RCA 2026-05-10)

Перед первым `bd create/update/list` в сессии:

```bash
bd version | grep -q "1.0.4" || { echo "❌ DRIFT"; bash scripts/setup/install_beads.sh; }
bd config get export.auto | grep -q "true"
bd config get export.git-add | grep -q "true"
bd config get export.path | grep -q "issues.jsonl"
```

**Actual flags + commands** — в [`.beads/CHEATSHEET.md`](../../../.beads/CHEATSHEET.md). При DRIFT — `bd <cmd> --help` + update cheatsheet ПЕРЕД работой.

**RCA-источник:** 2026-05-10 — использовал `--depends-on` (не существует), 8 child beads потеряны silently. Cheatsheet = mechanical anti-drift gate.

## Core rule

For any operational change:

1. Update `.beads` first
2. Export/sync if needed
3. Reflect the new state into `todo.md`, project `*.todo.md`, or other registry files

If the agent entered an existing `{project}.todo.md` and no matching bead exists yet:

1. stop treating the markdown file as the operational source
2. create or plan the migration in `.beads`
3. review progress, blockers, dependencies and goal map in `.beads`
4. only then continue execution and refresh reflections

If a workflow still has a `duckdb` layer:

- read from it only when importing legacy data
- do not use it as the editable source of truth

## Editable vs reflective layers

### Editable

- `bd` CLI backed by embedded Dolt (`bd show`, `bd list`, `bd ready`, `bd update`, `bd close`)
- `.beads/beads.db` / embedded Dolt storage
- `.beads/issues.jsonl` only as mandatory git-export visibility layer and fallback, not live canonical state
- `bd` operations (`create`, `update`, `close`, `dep add`, `rename`, `comment`, `sync`)

### Reflective

- root [`todo.md`](todo.md)
- project `*.todo.md`
- [`<internal-folder>/tickets.todo.md`]([todo%20%C2%B7%20incidents]/tickets.todo.md)
- generated registry/digest/status markdown files

### Import-only / legacy

- `duckdb` snapshots
- older roadmap exports
- external trackers during transition (`Jira`, later `Linear`) unless explicitly declared primary for a given sync

## Required workflow

### 1. Read current state from `.beads`

- Use `bd show`, `bd list`, `bd ready`, or direct Dolt/DB queries first. Use `.beads/issues.jsonl` only as fallback/export read surface.
- If `todo.md` and `.beads` disagree, treat `.beads` as canonical and repair reflection.

### 2. Make operational change in `.beads`

- Create/update/close the bead
- Перед началом git/project работы явно claim задачу: `bd update <bead-id> --status in_progress --claim`. Это делает owner/assignee видимыми до branch/worktree/PR операций и связывает текущий checkout с живым обязательством.
- Update blockers and dependencies in `.beads`, not in prose only
- If the work is not just technically complete but already handed off to the requester, use the canonical acceptance marker (Definition of Done - DOD):
  - status remains `closed`
  - add label `owner-got-output`
  - add metadata `{"owner_got_output": true, "owner_got_output_at": "YYYY-MM-DD"}`
  - append a short note/comment naming which output the owner already received
- Use namespace IDs:
  - `pr-hero-*`
  - `pr-rick-*`
  - `pr-adv-*`
- **Waste tagging contract (added 7 May 2026, Standard 1.5 §11):** at `bd close`, add a `waste:*` label если в работе была хотя бы одна Lean потеря. Допустимые значения (single primary, до 2 secondary):
  - `waste:overproduction` — делали раньше / больше чем нужно under triggering job
  - `waste:motion` — лишние клики / переключения внутри Execute
  - `waste:transportation` — ручной перенос состояния между системами
  - `waste:inventory` — WIP-aged, накопленные epics / drafts
  - `waste:overprocess` — больше шагов чем нужно для outcome
  - `waste:waiting` — заблокированы ротацией ключа / approval / external fields
  - `waste:defect` — RCA-driven, redo, утерянное состояние
  Без waste-label при close агрегатная аналитика `bd list --label waste:waiting --closed-since 30d` невозможна. Single-primary правило: один primary, до двух secondary. Если кажется что подходят 5+ — это сигнал что классификация поверхностна.

### 3. Reflect into human-facing files

- Update the relevant `todo.md` or generated reflection script
- Recompute registry lead time if the root registry changed
- Keep reflection concise; avoid duplicating operational logic manually if it can be generated

### 4. State migration status explicitly

For any project / workstream, explicitly state which mode it is in:

- `beads-primary`
- `legacy-importing`
- `mixed / not yet migrated`

If it is still mixed, list the exact remaining gap.

### 5. Delivery contract for beads-first work

For any project / release / dependency-heavy final answer that relies on `.beads`:

- include a separate block named `Graph from bd/Dolt`
- source the graph from `bd show` / `bd list` / direct Dolt query first; use `.beads/issues.jsonl` only when `bd` is unavailable or as a committed export surface
- make the graph **semantic-first for humans**:
  - lead with branch / blocker / next output wording that a teammate can act on;
  - if using Mermaid, node labels must start with a short JTBD in the form `Когда ..., хотим ...`, then `output`, and only then show the bead id as a secondary ref;
  - **макрос id + title:** в любой таблице / списке для людей каждая строка с `pr-*` — **`pr-rick-N — {title}`** (см. [`hypothesis-gap-falsification` §0](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md));
- answer `что уже сделано`, `что проверено`, `какой blocker сейчас активен`, `какой next output нужен`;
- outcome в human-facing beads delivery формулировать как `что теперь изменилось для команды / пользователя`, а не как `какой internal status достигнут`;
- запрещено называть outcome системным состоянием (`accepted`, `uploaded`, `closed`, `synced`) без описания пользы/изменения процесса.
  - bead ids are allowed only as secondary technical refs in parentheses or in a short `Technical refs` line
- show statuses, parent-child or dependency edges, and remaining blockers
- mark which nodes are already verified / tested
- if `.beads` is unavailable or out of sync, say that explicitly and name the fallback source (`beads.db`, `issues.jsonl`, or reflection file)
- before any operational change in `.beads`, the agent must first show the quick reusable ticket card in chat
- if the card is missing, bead-create / bead-update is premature and must not proceed
- for any new bead/task, the human-facing node description must follow the canonical ticket contract:
  - `Название` in the form `Когда ..., хотим ...` (JTBD title formula — полная процедура и 10 примеров в §JTBD title formula ниже)
  - `Ситуация-триггер и проблема`
  - `JTBD-сценарий`
  - `1-й релиз и DOD, Definition of Done — определение готовности`
  - `Тест-кейсы`
  - `Ручные тесты`
  - `Corner cases`
  - `Recover / rollback`
  - `Blockers & Gaps`
  - `Sub-tasks` (**обязана включать профайл-подзадачу** — RCA 2026-06-14 pr-rick-nbdl, см. §Обязательная подзадача профилирования ниже; `make worktree` seed'ит её автоматически)
  - `Reasoning-log analysis` — **ОБЯЗАТЕЛЬНО в каждом bead** (RCA 2026-06-13, owner ask: «чтобы анализ reasoning log'a всегда был во всех beads, loop улучшения скилов/агентов через skillops»). См. §Reasoning-log analysis section ниже.
  - `Итоговый результат`
  - `Пример output / shape of final artifact`
- do not invent a separate pseudo-schema for beads that conflicts with ticket standard
- for data/sheet/report beads, the card is incomplete unless it shows:
  - `artifact_type`
  - `one_row_equals`
  - `target_document_name`
  - `target_document_link`
  - `target_read_url`
  - `target_worksheet_name`
  - `required_shared_to`
  - `read_access_verification`
  - `output_schema_table`
  - `sample_rows_table`
  - `field_source_map_table`
- for data/sheet/report beads, the output section must be **table-first**:
  - one markdown table with the exact output columns in final display order;
  - one markdown table with 1-2 real sample rows when current data already exists;
  - one markdown table for source/proof mapping;
- if the agent proposes a better ticket/output format, the same turn must include an immediate rewritten example, not only recommendations.

## Обязательная подзадача профилирования (RCA 2026-06-14, pr-rick-nbdl)

**Owner directive:** «когда мы делаем beads тикеты, worktree и проекты — всегда включать подзадачу профилирование, ускорение и улучшение скриптов в скилах и везде, в том числе тестов, чтобы перф-долг не копился».

**Правило:** каждый bead, который трогает скрипт / скил / тест / pipeline, **обязан** нести профайл-подзадачу в каноническом виде `when → output → outcome` (та же форма, что §Owner-visible bead progress tree). `make worktree BEAD=<id>` **seed'ит её автоматически** в `Sub-tasks:` (см. `scripts/make_worktree.py` `ensure_perf_subtask`, идемпотентно — повторно не дублирует). При ручном `bd create` без worktree — добавить руками.

**Канонический вид подзадачи (копировать в `Sub-tasks:`):**

```
- [ ] when трогаем скрипт/тест/скил в этой задаче → output профайл-замер baseline+after (pyinstrument/hyperfine/time) → outcome ускорение или вывод «уже оптимально» + тесты не медленнее baseline
```

**Что профилировать (checklist «что измерять», не дробить на отдельный skill):**

| # | Слой | Чем мерять | Что искать |
|---|---|---|---|
| 1 | wall-clock per stage (I/O-bound) | `time.monotonic()` обёртка / `hyperfine` для CLI | стадия, доминирующая по времени (обычно сеть/диск, не CPU) |
| 2 | CPU hot-path (compute-bound) | `pyinstrument` (sampling) / `py-spy` (на живой процесс) | функция с наибольшим self-time |
| 3 | память | `tracemalloc` / `scalene` | рост на больших входах, утечки в цикле |
| 4 | регрессия тестов | прогон до/после + сравнение wall-clock | тесты не стали медленнее baseline после правки |
| 5 | I/O-bound → НЕ cProfile | wall-clock, а не CPU-профайл | cProfile вводит в заблуждение на сетевых пайплайнах |

**Цель замера = решение, не число:** результат подзадачи — либо измеримое ускорение (target ≥X% vs baseline, X фиксируется в bead), либо честный вывод «уже оптимально» с baseline в bead notes. Пустой ✅ без замера = брак.

**Когда подзадача неприменима (skip без RCA):** bead чисто-документационный (правка narrative/changelog/incident), не трогает исполняемый код/тест/pipeline. Тогда `make worktree` всё равно seed'ит строку, но агент помечает её `- [x]` с пометкой «N/A — нет исполняемого кода» — это легитимно, не обход.

**Связь:** §Owner-visible bead progress tree (форма when→output→outcome), §Wiring-first (seed в существующем `make_worktree`, не новый фреймворк), `2-skillopt-training-loop` (улучшение самого скила через замер).

## JTBD title formula — читаемость #1 для команды (RCA 2026-05-24)

**Why это #1 приоритет:** owner steering 2026-05-24 — «читаемость bd ready для тебя и команды #1 приоритетно, огромная польза → сейчас это основная причина ошибок». Bead title — то что видит сканирующий `bd ready --json` за 5 секунд без открытия body. Если title технический («Fix auth», «Update tests») — невозможно понять кто что делает, нет ли коллизий, можно ли передать задачу. Параллельная работа N агентов **ломается на этом слое первым**.

**Formula (обязательная для всех новых beads):**

```
Когда <триггер / ситуация>, хотим <actor> <make progress / avoid failure>
```

Английский эквивалент (для bead title в системах с английским locale): `When <trigger>, help <actor> <progress>`.

**Mechanical validation** на `bd create` / `bd update --title` — `scripts/check_bd_title_shape.py` через lefthook `pre-commit` job `bd-title-shape` (glob `.beads/issues.jsonl`). Title без `Когда ..., хотим ...` или `When ..., help ...` → BLOCK commit с подсказкой переименовать. Override: env `BD_TITLE_SHAPE_ACK="<reason ≥12 chars>"` для legacy migration / short-technical-title-with-JTBD-body case.

**Допустимые исключения** (short technical title с JTBD subtitle в body):
- title `Add webhook retry persistence (pr-rick-NN)` allowed ТОЛЬКО если body первая строка = JTBD: `Когда payment webhook delivery fails, хотим preserve event и дать operator safe recovery path`.
- title ≤80 chars предпочтительно (но не hard limit — большинство IDE/CLI truncate at 80+).

### Хорошие примеры (10) — domains нашего workspace

| Когда (триггер) | Хотим (actor → progress) |
|---|---|
| команда сканирует `bd ready --json` | агент понять задачу одной фразой без открытия body |
| параллельный агент пишет в main без бида | hook остановить write до явного go или claim |
| agent закрывает сессию | команда увидеть актуальный bead state через `bd dolt pull` |
| тиммейт читает 1046-строчный AGENTS.md | navigate к invariant за 2 минуты через WORKSPACE_MAP |
| Cowork-сессия Милены ловит абсолютные пути в settings.json | разблокировать Write через portable hooks invariant |
| Rick.ai client запрашивает widget conversion check | агент собрать JTBD scenarium → KB template → beads ticket |
| <teammate> PR review запрос на новый node type | <teammate>-code-review проверить generalization-first 4×yes |
| advising client прислал XLSX через Telegram | Лиза intake → bead → draft → CPR → send |
| MCP server возвращает 401 на rick.ai API | проверить 5 слоёв Recovery Gate до перекладывания на хозяина |
| dirty-tree накопился до ≥200 entries | git_dirty_count_gate заблокировать risky op до cleanup |

### Плохие примеры (10) — что hook BLOCK

| Плохой title | Почему плохой |
|---|---|
| `Fix auth` | техническое действие без actor + trigger + progress |
| `Update tests` | output-only, не outcome; кто страдает без этого? |
| `Refactor dashboard` | scope без JTBD сценария |
| `Add hook` | какой hook кому какую боль закрывает? |
| `Change schema` | какой actor получит progress от смены? |
| `Improve onboarding` | vague «improve» вместо measurable progress |
| `Cleanup code` | output-only, no outcome |
| `Implement API` | какой actor получит чего через API? |
| `Update docs` | какие docs, какому actor, какой progress? |
| `Fix bug` | какой trigger, кто страдает, что станет лучше? |

### Hard fail категория

Agent создал bead с title не matching formula AND не дал inline JTBD в body → `category: vague-bead-title-bypass`. Override env `BD_TITLE_SHAPE_ACK` использован больше 3× за неделю одним agent → recurring pattern, требует RCA не workaround.

## Team starter ritual

When a teammate just opened the repo and wants to understand "what to do next", the default ritual is:

1. `bd ready`
2. `bd list --status open`
3. `bd show <epic-or-task-id>`
4. `bd graph <epic-or-task-id> --compact`
5. only after that decide whether to create/update/close anything

Use this wording in human-facing docs and rollout messages:

- `show me what is ready now`
- `show the project graph and blockers`
- `create the project in .beads first, then reflect it into todo files`
- `plan from the final outcome backward`
- `build a visual explanation of the roadmap and dependencies`

Prompt examples without naming internal skill names:

- `Покажи, что реально ready в этом проекте и какая задача сейчас блокирует остальных.`
- `Разложи проект от конечного результата назад и оформи это как граф задач с зависимостями.`
- `Создай новый проект в .beads, а потом отрази его в todo и README только там, где это нужно.`
- `Сделай визуализацию roadmap и dependency graph по этому workstream.`

## Forbidden

- Do not change task status only in `todo.md`
- Do not keep blockers only in markdown text if they should exist as dependencies
- Do not edit both `duckdb` and `.beads` as parallel operational trackers
- Do not present `todo.md` as source of truth after `.beads` exists for that workflow
- Do not output a generic `Goal Map` for a beads-first task without explicitly showing the `.beads` graph source
- Do not lead a human-facing project answer with raw bead ids like `pr-1.1`, `pr-1.2` when a semantic blocker/output name can be used

## Required output language

When relevant, state explicitly:

- `.beads` is the primary editable layer`
- `todo.md` is a reflection layer`
- `duckdb` is import-only / legacy`
- `Graph from .beads` is the canonical project graph for the final answer`

For human-facing answers in this workspace:

- пиши по-русски по умолчанию
- если английский термин действительно нужен, сразу переводи его при первом упоминании
- предпочитай русские формулировки, когда есть ясный эквивалент:
  - `outcome` -> `изменение / результат для команды или пользователя`
  - `output` -> `артефакт`
  - `handoff` -> `передача`
  - `delivery` -> `доставка`
  - `proof` -> `доказательство`
- не смешивай русский и английский в одном предложении без необходимости

## Related

- [`project-create-launch`](.agents/skills/1-project-create-launch/SKILL.md)
- [`project-todo-registry-check`](.agents/skills/1-project-todo-registry-check/SKILL.md)
- [`close-task-or-project-cleanly`](.agents/skills/1-close-task-or-project-cleanly/SKILL.md)
- [`beads-id-namespaces`](.agents/skills/1-beads-id-namespaces/SKILL.md)

## Workflow

1. **Input checklist:** триггер на смену состояния (новая задача, blocker, completion, hand-off, peer запрос).
2. Прочитать `.beads` SSOT через `bd ready --json` / `bd show <id>`.
3. Применить JTBD title formula (§выше) — title в виде `Когда ..., хотим ...`.
4. `bd create` / `bd update` / `bd close` через CLI.
5. Reflect в `todo.md` ТОЛЬКО ПОСЛЕ `.beads` update.
6. **Output checklist:** обновлённый bead visible via `bd show` + `.beads/issues.jsonl` export refreshed for git visibility + согласованный `todo.md` + JTBD title прошёл validator.
7. **Outcome checklist / owner value:** команда видит читаемый `bd ready` за 5 секунд без открытия body — основная причина ошибок параллельных агентов закрыта.

## Self-falsification gate

После применения скила прогнать гипотезу «состояние задач честно отражено» через [`2-hypothesis-gap-falsification`](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md):

- **Expectation:** `bd ready` показывает все open beads на которые я работал в сессии, с JTBD title.
- **Reality:** что показывает `bd ready --json` после моих изменений.
- **Gap:** title без formula? statuses не sync? blockers не отмечены?

---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning-log analysis section (ОБЯЗАТЕЛЬНО в каждом bead) — loop улучшения скилов/агентов

**RCA 2026-06-13 (owner ask):** «чтобы анализ reasoning log'a всегда был во всех beads, чтобы был loop и процесс улучшения скилов и агентов (можно использовать skillops)». Источник — supervisor-прогон kant.ru (`pr-rick-0o4t`), где 2 broken-main (мёртвый drift-guard + silent-drop секции при consolidation) прошли мимо CI и review. Если бы каждый bead нёс reasoning-log анализ — этот класс ловился бы в цикле, а не случайно.

**Контракт секции `## Reasoning-log analysis` (5 обязательных полей):**

```markdown
## Reasoning-log analysis
- **find-divergence:** <вывод `scripts/reasoning_log/graph.py --latest --find-divergence`: N nodes/edges, M divergences>
- **honest-scope check:** <если divergence=0 — НЕ значит «всё ок». Silent over-claim / silent-drop НЕ ловятся (нет steering-узла). Ручная локализация: сверка артефакта с источником (probe JSON / API / SSOT)>
- **класс сбоя (если найден):** <over-claim / wrong-source / fabricated-value / merge-consolidation-silent-drop / detector-blind-spot / — нет>
- **routing (куда чинить):** <СКРИПТ / скил-текст / skillops — по таблице 0-skill-script-failure-diagnose-via-reasoning-log §2>
- **loop-action:** <что подаётся в self-improvement: regression-тест / новый класс в registry / 2-skillopt-training-loop rollout / — не требуется>
```

**Когда secция пустая/N-A:** даже для тривиального bead поле обязано присутствовать со значением `find-divergence: не запускался (тривиальный bead)` + `класс сбоя: —` + `loop-action: не требуется`. Пустую секцию опускать **запрещено** — это petля обратной связи, а не декорация.

**Loop через skillops (Path B wiring, не новый фреймворк):**

| Шаг loop | Скрипт/скил (существует) | Что делает |
|---|---|---|
| 1. Локализовать | `scripts/reasoning_log/graph.py --find-divergence` + `--to-duckdb` | networkx граф по OTel-спанам + materialize |
| 2. Классифицировать + routing | `0-skill-script-failure-diagnose-via-reasoning-log` §2 | тип сбоя → fixer (СКРИПТ/скил/skillops) |
| 3. Починить корень + regression | СКРИПТ patch + тест | не текст скила, если сбой в коде |
| 4. Закрепить в self-improvement | `2-skillopt-training-loop` (rollout→reflect→update) + `0-skills-self-improvement` | новый класс в registry / тюнинг скила по validation score |

**Honest scope (не overclaim):** find-divergence ловит ТОЛЬКО steering-corrected эпизоды (owner поправил → есть узел расхождения). Silent over-claim и silent-drop (consolidation выронила wiring) детектор НЕ видит — секция обязана это признавать в поле `honest-scope check`, иначе `divergence: 0` читается как ложное «чисто».

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/` → duckdb). Узел «свернул не туда»: `scripts/reasoning_log/graph.py --find-divergence`. Ручная markdown-таблица в чат — только если owner явно спросил «почему ты так решил». Полный протокол: `agent-reasoning-log/SKILL.md` (v2, RCA 2026-05-17).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick (включая TaskMaster и связанные стандарты Heroes Rickai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
