---
name: 1-project-create-launch
description: "Use when creating a new project or moving a project through its lifecycle: create the bead (Bits Ticket = JTBD), the worktree, the project folder in projects/all-projects/, and mount it as a symlink in the right numbered Kanban lane (1. backlog → 2. dod-n-blocked → 3. in-progress → 4. to-delivery → 5. verify-and-done). Drives scripts/project_status_symlinks.py. Use when user says \"создай проект\", \"запусти проект\", \"new project\", \"project launch\", \"передвинь проект\", \"move project to delivery\", \"покажи доску проектов\"."
type: process
version: 1.0
related_skills:
  - 1-change-task-and-project-state-via-beads
  - 1-critical-chain-status-report
  - critical-chain-design
  - 2-hypothesis-gap-falsification
  - 2-so-what-outcome-ladder
  - 5-sync-github-checklist
---

# 1-project-create-launch — создание проекта и его движение по канбану симлинков

**Mode:** [ACTIVE] — обязательный вызов Skill ПЕРЕД `bd create --type epic`, фразой «создай проект / запусти проект», или при смене статуса проекта (перемещение между lane-папками).

## Owner value

Новая работа сразу получает: понятное JTBD-имя, durable bead («Bits Ticket»), isolated worktree, self-describing branch, и физическую папку в `projects/all-projects/`, которая **автоматически монтируется симлинком в ровно одну lane-папку** по статусу bead. Owner и следующий агент видят канбан-доску, просто открыв `projects/`, без расшифровки opaque id.

## Картина целиком (folder layout)

```
projects/
├── all-projects/                       # SSOT — каждый проект живёт здесь ОДИН раз
│   └── <jtbd-slug>-<bead-id>/          #   имя == branch == worktree basename
│       ├── <jtbd-slug>-<bead-id>.todo.md
│       ├── .project-meta.json          #   {name, bead_id, jtbd}
│       └── .project-status             #   offline lane-маркер (fallback без .beads)
├── 1. backlog/          <name> ─┐
├── 2. dod-n-blocked/    <name> ─┤
├── 3. in-progress/      <name> ─┤  симлинки → ../all-projects/<name>
├── 4. to-delivery/      <name> ─┤  (ровно один симлинк на проект)
└── 5. verify-and-done/  <name> ─┘
```

Папки **нумерованы** (`N. name`) — explorer сортирует их в порядке жизненного цикла; CLI принимает короткий id (`backlog`, `dod-n-blocked`, …), не номер. Scaffold создаётся командой `init` (см. §Создание).

**Инвариант:** проект физически живёт только в `all-projects/`; lane-папки содержат **только относительные симлинки** `<lane>/<name> -> ../all-projects/<name>`. Каждый проект смонтирован в **ровно одну** lane.

## Именная цепочка (project ↔ bead ↔ worktree — один-к-одному)

| Звено | Форма |
|---|---|
| JTBD title (источник имени) | `Когда ..., хотим ..., чтобы ...` |
| bead (Bits Ticket) | `pr-rick-<id>` — durable обязательство, primary tracker (`.beads`) |
| branch | `pr-rick-<jtbd-slug>-<bead-id>` |
| worktree | basename == branch (`.claude/worktrees/pr-rick-<jtbd-slug>-<bead-id>`) |
| project folder | `projects/all-projects/<jtbd-slug>-<bead-id>/` (== branch basename) |
| PR title | тот же JTBD язык |

Один разрыв в цепочке (opaque slug, папка без bead, bead без worktree) **блокирует** claim «launch завершён» — см. §Self-falsification.

## Четыре lane и жизненный цикл (полный список стадий)

Полный жизненный цикл и SSOT перехода между симлинками — в [`workflow.yaml`](./workflow.yaml). Машинный SSOT маппинга bead→lane — в [`lanes.json`](./lanes.json). Коротко:

| Lane (папка) | id | Стадии (P1–P7 + B) | bead-статус/лейблы | Канон 4.15 |
|---|---|---|---|---|
| `1. backlog` | `backlog` | P1 intake · P2 pre-DoD | `open` (backlog/next) | backlog · next |
| `2. dod-n-blocked` | `dod-n-blocked` | P2 DoD-gate · B blocked | label `dod_blocked` · `blocked` (override) | dod_blocked |
| `3. in-progress` | `in-progress` | P3 in-dev · P4 review | `in_progress` (in_design/in_review/rework) | in_design…rework |
| `4. to-delivery` | `to-delivery` | P5 delivery | label delivering/owner_received | hypothesis…owner_received |
| `5. verify-and-done` | `verify-and-done` | P6 outcome-verified · P7 closed | `closed` (override) · outcome_realized | owner_activated · outcome_realized |

`2. dod-n-blocked` = «DoD-gate / заблокированный бэклог»: здесь тикет **детализируется в bead** (DoD, output, outcome, спека, требования) ДО запуска в работу, и сюда же паркуется blocked-тикет. Точка bd-стандарта `dod_blocked` — тикет не берётся в work, пока DoD/output/outcome не уточнены. `1. backlog` = сырой список идей (status `open`), куда приземляется новый проект.

## Step 0 — Trigger detection (ОБЯЗАТЕЛЬНО ПЕРЕД `bd create`)

Триггеры: «создай проект» / «запусти проект» / «new project» / `bd create --type epic` / «передвинь проект в …».

Действие при активации (порядок нельзя нарушать):
1. Прочитать §Картина целиком + §Именная цепочка.
2. **First-touch триада в первые 5 tool calls:** bead с JTBD title → worktree → работать только внутри worktree.
3. Выполнить §Создание (ниже) по шагам.
4. **Step 0.5 verify:** убедиться что `projects/all-projects/<name>/<name>.todo.md` физически создан (`ls`/`Read`). Если нет — hard fail + RCA.

## Создание проекта (the create flow)

```bash
# 0. (один раз при установке) создать scaffold projects/ — 5 нумерованных lane
python3 .agents/skills/1-project-create-launch/scripts/project_status_symlinks.py init

# 1. bead-тикет (Bits Ticket) — JTBD title = источник slug
bd create --title="Когда <триггер>, хотим <actor> <progress>, чтобы <outcome>" --type=task
#    → выдаёт bead-id, например pr-rick-7ms7

# 2. canonical worktree (derives JTBD-slug branch + full checkout + claim)
python3 scripts/make_worktree.py pr-rick-7ms7 --claim
#    → ветка/worktree pr-rick-<slug>-7ms7

# 3. физическая папка проекта + симлинк в стартовой lane (1. backlog)
python3 .agents/skills/1-project-create-launch/scripts/project_status_symlinks.py \
    new pr-rick-<slug>-7ms7 --bead pr-rick-7ms7 --jtbd "Когда ..., хотим ..., чтобы ..."
#    → projects/all-projects/pr-rick-<slug>-7ms7/  + симлинк в "projects/1. backlog/"

# 4. отразить в реестре (bead-first, потом reflection): строка в корневом todo.md
```

**Без `.beads`** (default в чистом template, где `bd init` ещё не сделан): шаги 1–2
пропускаются — это **полноценный поддерживаемый путь, не «второй сорт»**. `new` создаёт
папку + `.project-status=backlog` + симлинк; lane ведётся через `move`/`.project-status`.
Когда команда сделает `bd init` и заведёт bead, привяжи его и переключись на bead-driven:

```bash
PSS=".agents/skills/1-project-create-launch/scripts/project_status_symlinks.py"
python3 $PSS link pr-rick-<slug>-7ms7 --bead pr-rick-7ms7   # записывает bead_id в .project-meta.json
python3 $PSS sync pr-rick-<slug>-7ms7                       # дальше lane выводится из bead
```

До `bd create` показать в чат **canonical ticket card** (Название `Когда…хотим…`, Ситуация-триггер, JTBD-сценарий, DoD, Тест-кейсы, Corner cases, Recover/rollback, Blockers, Sub-tasks, Reasoning-log analysis, Итоговый результат) — контракт из `1-change-task-and-project-state-via-beads`.

## Движение по канбану (move / sync)

```bash
PSS=".agents/skills/1-project-create-launch/scripts/project_status_symlinks.py"

# Явный перевод (пишет .project-status + переустанавливает симлинк):
python3 $PSS move pr-rick-<slug>-7ms7 in-progress

# Авто-вывод lane из bead-статуса (после `bd update`), затем переустановка симлинка:
bd update pr-rick-7ms7 --status in_progress --claim
python3 $PSS sync pr-rick-<slug>-7ms7

# Привязать bead к существующему проекту (миграция, когда появился .beads):
python3 $PSS link pr-rick-<slug>-7ms7 --bead pr-rick-7ms7

# Реконсиляция всех проектов разом + доска + диагностика:
python3 $PSS sync-all
python3 $PSS board
python3 $PSS doctor        # orphan / broken / wrong-target / drift / unmapped / multi-lane → exit 3
```

`doctor` ловит и **drift** (симлинк в одной lane, а bead/`.project-status` выводит другую — «доска врёт»; чинится `sync`), и **wrong-target** (симлинк не на `../all-projects/<name>`), и **unmapped** (bead-статус, который не матчит ни одну lane → молчаливый backlog). Чистый `doctor` = доска говорит правду.

`sync` выводит lane так: bead (если `.beads` доступен) → status+labels по `lanes.json` → lane; иначе `.project-status`; иначе default `backlog`. `move` — ручной override, пишет `.project-status` (и подсказывает синхронизировать bead).

## Закрытие (P6 → P7)

Закрытие — зеркало создания, через `1-close-task-or-project-cleanly`: `bd close` + label `owner-got-output` ПЕРЕД reflection → `sync` (override `closed` → `verify-and-done`) → registry/todo обновлён → nothing-lost (reachable из origin/main) → worktree pruned.

## Forbidden

- ❌ Создавать проект без `{name}.todo.md` в `all-projects/`.
- ❌ Класть проект физически в lane-папку (lane = только симлинки).
- ❌ Монтировать проект в две lane сразу (move/sync гарантируют ровно одну).
- ❌ Менять статус только перемещением симлинка вручную, не обновив bead — `.beads` остаётся primary, симлинк — reflection.
- ❌ Opaque branch slug / папка без bead — разрыв именной цепочки.

## Required

- ✅ Сначала bead (`.beads`), затем worktree, затем папка+симлинк, затем reflection в todo.
- ✅ `new`/`move`/`sync` — только через `project_status_symlinks.py` (один источник механики симлинков).
- ✅ После операции — `doctor` чистый (ровно одна lane на проект, нет orphan).

## Output checklist

- [ ] `projects/all-projects/<name>/<name>.todo.md` создан (OUTPUT/OUTCOME, критическая цепочка).
- [ ] `.project-meta.json` содержит `bead_id` (один-к-одному с Bits Ticket).
- [ ] Проект смонтирован симлинком в ровно одну lane (`doctor` == OK).
- [ ] Строка в корневом `todo.md`-реестре (bead-first → reflection).
- [ ] В чат: что создано/передвинуто, путь, текущая lane.

## Self-falsification gate

После launch/перехода прогнать через `2-hypothesis-gap-falsification`: ожидание = bead title `Когда…хотим…`; branch = `pr-rick-<slug>-<bead-id>`; project folder basename == branch; симлинк в ровно одной lane соответствует bead-статусу. Любой разрыв → follow-up bead, claim «launch завершён» блокируется.

## Related

- [`workflow.yaml`](./workflow.yaml) — SSOT жизненного цикла + переходов между симлинками.
- [`lanes.json`](./lanes.json) — машинный SSOT маппинга bead-статус → lane.
- [`scripts/project_status_symlinks.py`](./scripts/project_status_symlinks.py) — механический мувер.
- `1-change-task-and-project-state-via-beads` — beads-first смена состояния (зеркало по действию).
- `1-critical-chain-status-report` — `{name}.todo.md` skeleton (Голдрат-цепочка).
- `1-close-task-or-project-cleanly` — закрытие (P6→P7).

## Input / Output / Outcome checklist

**Input:** запрос owner (создать/передвинуть проект) + тип (client-driven / workspace-level / cross-client) + JTBD-формулировка.
**Output:** `projects/all-projects/<name>/` с `{name}.todo.md` + `.project-meta.json` (bead_id) + симлинк в ровно одной lane; строка в корневом реестре.
**Outcome (owner benefit):** owner и следующий агент видят канбан-доску открыв `projects/`; статус проекта = его lane, выводится из bead автоматически; ничего не теряется, нет opaque id.

## Reasoning Log Protocol

При создании/перемещении проекта агент фиксирует в чат: выбранную lane + почему (bead-статус или `.project-status`), и какие пункты Output checklist N/A. Reasoning Log v2 — авто-захват из транскрипта; ручная markdown-таблица в чат только если owner явно спросил «почему ты так решил».

## Связанные скилы

- `1-change-task-and-project-state-via-beads` — beads-first смена состояния (primary tracker, симлинк = reflection).
- `1-critical-chain-status-report` — `{name}.todo.md` skeleton (Голдрат-цепочка от outcome к первому output).
- `1-close-task-or-project-cleanly` — закрытие проекта (P6→P7), зеркало create.
- `2-hypothesis-gap-falsification` — self-falsification gate именной цепочки.
- `2-so-what-outcome-ladder` — P6 outcome-verified (outcome ≠ output).

## Язык результата

Русский по умолчанию. Английский только для имён API/методов/идентификаторов кода/vendor UI labels. Устоявшиеся сокращения (JTBD, DoD, RCA, SSOT, MCP) допустимы.
