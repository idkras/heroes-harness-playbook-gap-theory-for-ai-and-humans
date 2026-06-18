---
name: 1-critical-chain-status-report
description: "Универсальный шаблон status report по проекту через критическую цепочку Голдрата (Theory of Constraints). Каждый шаг chain — целевой output → outcome → измеримая выгода owner'а. Status светофором (🟢🟡🔴💀). Bottleneck identification по слабому звену (chain weakest link). Buffer consumption (% хронологии burned). Применяется в `{project}.todo.md`, в verdict субагента `project-progress-auditor`, в end-of-day handoff, в RCA reports. Не саммари «много сделано» — каждая строка имеет evidence (commit hash / file path / test name / row count)."
when_to_use: "ОБЯЗАТЕЛЬНО при создании `{project}.todo.md`, при substantial session checkpoint, при handoff между сессиями, при manager-auditor verdict. Запрещено замещать summary-style таблицей без status emoji + evidence."
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `<internal-module>/shared/credentials_manager.py`.

# 1-critical-chain-status-report — universal Голдрат status template

**Mode:** [ACTIVE] (gate при создании любого `*.todo.md` или status report — без обязательной структуры delivery rejected)

## JTBD (атомарный)

Когда owner / менеджер открывает `{project}.todo.md` или status report после ночи / отпуска / handoff,
он хочет за 30 секунд понять:
(a) что главное обещано (outcome),
(b) где chain застрял (bottleneck),
(c) что готово / что булшит / что blocked,
(d) одно concrete действие чтобы сдвинуть bottleneck,
чтобы принять решение: продолжать / pivot / escalation.

## Обязательная структура status report (7 блоков)

### Блок 1 — Outcome (одна фраза)

Формат: `{role/team} получает {measurable artifact} и **может за {time}** {action} {benefit}`.

**Примеры хороших outcome:**
- ✅ «Команда продаж avtoall.ru получает 3690 customer_360.md карточек и **может за 30 сек на карточку** выбрать hook-фразу для реактивации»
- ✅ «Маркетинг <client> получает дашборд cohort retention M0-M6 и **может за 5 мин** понять какая кампания даёт CAC payback < 90 дней»

**Примеры плохих outcome (rejected):**
- ❌ «Улучшить enrichment pipeline» (нет measurable, нет benefit, нет timing)
- ❌ «Создать 3690 cards» (output, не outcome — нет «что owner с этим делает»)
- ❌ «Implement CRM integration» (technical output, не business outcome)

**Симметрия gap = jtbd = outcome = next action** (SSOT: `2-so-what-outcome-ladder/SKILL.md §Симметрия`): Блок 1 Outcome (owner-language) и Блок 7 Next concrete action обязаны быть об одном референте на одном языке. Next-action = owner-language рамка + фальсифицируемый механизм хвостом через ` = ` (не `git push`, а `открыть pipeline команде = push в main + пинг Лизе`). Hard fail: outcome owner-language, а next-action в чистом техническом языке → переписать симметрично.

### Блок 2 — Critical chain (от outcome к началу)

Таблица обязательных колонок:

| # | Шаг | Status | Evidence | Blocker |
|---|---|---|---|---|
| N | последний шаг к outcome (например push в amoCRM) | 🟢/🟡/🔴/💀 | commit `abc123` / `path/file.py` / `pytest tests/X.py PASS` / `<layer>/X.parquet 3690 rows` | конкретный блокер ИЛИ — |
| N-1 | предшествующий шаг | … | … | … |
| ... | ... | ... | ... | ... |
| 1 | начальный шаг (foundation) | … | … | … |

**Status legend (строгая):**

| Symbol | Meaning | Critère |
|---|---|---|
| 🟢 **done** | артефакт на диске, тесты зелёные, owner может посмотреть | commit hash + path + green test |
| 🟡 **partial** | артефакт есть но не закрывает full scope (например 20/3690 = 0.5%) | path + % coverage |
| 🔴 **blocked** | нет артефакта, есть конкретный blocker | named blocker (другой step / external dep / owner go) |
| 💀 **bullshit/lost** | был обещан / написан в chat но не committed; OR назван «готово» но реально не работает | RCA reference |

**Hard rule:** chain пишется **от outcome к началу** (top row = последний шаг). Это форсит обратное мышление от owner benefit — а не «что я по очереди сделаю».

### Блок 3 — Bottleneck identification

Одно предложение: «Bottleneck = шаг N — {описание}. До его разблокировки шаги N+1...N+k недостижимы.»

По Голдрату — chain слабее самого слабого звена. Если bottleneck = recovery uncommitted code, то остальные шаги не двинутся пока не fix.

### Блок 4 — Buffer consumption (опционально, для долгих проектов)

Если проект имеет deadline (course start, client report due, release window):

```
Planned timeline: 14 days (например)
Days burned: 8
Critical chain progress: 30% (2/7 steps done)
Buffer consumption: 57% (8/14 days) vs 30% progress = 27% over-budget
Verdict: 🔴 over-burning buffer
```

Если deadline нет — блок опускается явной строкой «Нет дедлайна, buffer not tracked».

### Блок 5 — Recovery / Next plan (если есть 💀 / 🔴)

Таблица обязательных колонок (если статус 💀 или 🔴 хоть на одном шаге):

| # | Action | Файл | Effort (min) | Status |
|---|---|---|---|---|
| 1 | конкретное действие | конкретный путь | оценка времени | pending/in-progress/done |

**Hard rule:** action — императив с глаголом («Restore X», «Run Y», «Commit Z»), не существительное («recovery», «fix», «improvement»).

### Блок 6 — Preserved artifacts (что выжило)

Если был incident loss / branch switch / rollback — таблица survived артефактов:

| Артефакт | Где | Rows × Cols | Use as |
|---|---|---|---|
| название | путь | размер | «schema reference / sample data / spec» |

### Блок 7 — Next concrete action (одна команда)

В конце документа — одна команда / один shippable shippable action который агент **сам** выполняет в next iteration. Не «выбрать одно из трёх», не «обсудить с owner» — конкретный command:

```bash
# Step N recovery: восстановить customer_360_writer.py из chat artifacts
# и СРАЗУ git add + git commit перед любой next operation
git checkout pr-cleanup-and-<teammate>-2026-05-11 && \
  git log --oneline -- <internal-module>/<internal-component>/workflows/customer_360_writer.py | head -5
```

## Связанные скилы

- `2-so-what-outcome-ladder` — применяется в Блоке 1 для проверки outcome является measurable (не output)
- `2-hypothesis-gap-falsification` — применяется к delivery (был ли outcome достигнут — gap table)
- `2-rca-incidents` — применяется если статус 💀 (lost code, broken main, bypassed prod)
- `project-progress-auditor` subagent — применяет этот шаблон в реверс-режиме (проверяет полноту чужого status report)

## Universal applicability (не avtoall-специфика)

Этот скилл универсален для любого Rick.ai проекта, advising client, internal initiative:
- Rick.ai client enrichment (любой client с CRM)
- Advising client diagnostic (любой client с диагностикой)
- Course / workshop preparation (deadline-based)
- Subagent / skill development (development project)
- RCA fix campaign (multi-incident resolution)

Adaptation per project:
- Outcome — переформулировать под role/team конкретного проекта
- Chain length — 5-10 шагов в зависимости от complexity (не более 12 — иначе разбить на sub-projects)
- Status emoji — фиксированный set 🟢🟡🔴💀, не добавлять новые

## Hard fail (RCA-инцидент в `<internal-folder>/ai.incidents.md`)

- Создан `{project}.todo.md` без Блоков 1-3 (outcome / chain / bottleneck) → RCA `category: status-report-without-critical-chain`
- Outcome в Блоке 1 описан как output (нет measurable owner benefit) → rework + RCA
- Status светофор пропущен или ad-hoc symbols (например «✅⏳❌» вместо 🟢🟡🔴💀) → standardize
- Bottleneck не identified в Блоке 3 → re-think chain (если bottleneck не виден — chain плохо разложена)
- Next action в Блоке 7 — список из >1 действий ИЛИ требует решения owner → falsified

## RCA-источник

15 May 2026 — uncommitted enrichment pipeline lost. `{project}.todo.md` без status светофора и bottleneck identification не позволил owner'у быстро понять что main outcome (3690 cards) falsified at 0.5% и что bottleneck = uncommitted code в chat.

## Input / Output / Outcome checklist

Формат — AGENTS.md §Макрос {io-checklist} (три таблицы с обязательной колонкой «Факт», статусы ✅/❌/⚠️).

**Input checklist** — что на входе: (a) `{project}.todo.md` или сырой список сделанного; (b) git log / commit hashes / test names как evidence; (c) заявленный главный outcome проекта.

**Output checklist** — что на выходе: status report из 7 блоков (Outcome → Critical chain → Bottleneck → Buffer → Recovery → Preserved artifacts → Next action), каждая строка chain с evidence (commit/path/test/row count), один status emoji 🟢🟡🔴💀 на шаг.

**Outcome checklist** — выгода owner: за 30 секунд видит главное обещанное, где chain застрял, что готово/булшит/blocked и одно concrete действие — принимает решение продолжать / pivot / escalation без чтения всей хронологии.

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/`). Узел «свернул не туда»: `scripts/reasoning_log/graph.py --find-divergence`. Ручная markdown-таблица в чат — только если owner явно спросил «почему так решил». Полный протокол: `agent-reasoning-log/SKILL.md`.

## Owner value

Каждый запуск скилла приносит owner value: status report заменяет «много сделано»-саммари на критическую цепочку с bottleneck и evidence, owner за 30 секунд принимает go/pivot/escalation вместо чтения всей хронологии сессии. Value_per_touch: один status report = одно решение owner без переспрашивания «а что главное / где застряло».

Скилл добавлен для предотвращения повторения: любой `*.todo.md` или status report должен иметь обязательную 7-блочную структуру.
