---
name: agent-reasoning-log
description: "Универсальный протокол reasoning log + trace-first для ВСЕХ скилов и субагентов. Канон Standard 4.18. Mechanical enforcement через hook trace_required_check.py. Когда owner хочет понять, почему агент принял конкретное решение, какие инструкции в стандартах/скилах помешали или помогли, где расхождение ожидания-реальности и что субагент реально делал — ответ в trace file (primary), а не в summary в чате (secondary)."
---

**Mode:** [PASSIVE]

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `<internal-module>/shared/credentials_manager.py`.

# Agent Reasoning Log + Trace-first — универсальный протокол

## v2 — reasoning GRAPH, авто-захват из транскрипта (RCA 2026-05-17, канон)

**Что изменилось и зачем:** owner — «у нас 100500 reasoning log в duckdb, а не 1 с графом; задача фиксировать дерево мыслей агента, чтобы найти узел, где он свернул не туда; reasoning log нужен у исполнителя И у субагентов-проверяющих; ошибочные ветки помечать как ошибки». Старый протокол требовал, чтобы агент **руками** писал markdown-таблицу reasoning-log в чат и в `ai.incidents.md §Append-only trace`. Это (а) пропускалось под нагрузкой (RCA-доказано — anchoring-инцидент не залогирован ни разу), (б) было плоским списком без рёбер — «дерево мыслей» не существовало, (в) дублировалось boilerplate в 168 скилах.

**Новая модель — три слоя, write-path авто:**

| Слой | Где (path) | Кто пишет | Зачем | Статус |
|---|---|---|---|---|
| **v2 span graph** | `.reasoning-log/spans/{date}/{trace_id}.ndjson` → duckdb `reasoning_spans`+`reasoning_edges` | **Stop hook авто** (`transcript_ingest.py` парсит Claude Code transcript JSONL) | дерево мыслей: `span_id`=uuid, `parent_span_id`/`msg_uuid`=parentUuid → 1 граф/сессия. Субагент-ревьюер = `isSidechain` child span. `graph.py --find-divergence` находит узел «свернул не туда», помечает поддерево `falsified`, шлёт в GEPA | **канон** |
| **v1 flat row** | `.reasoning-log/live/**/*.ndjson` → `reasoning_log` | `append.py` (Stop hook минимальная строка + явный вызов агентом для substantial decision) | `query.py` метрики (steering-rate, top-blockers) | сохранён |
| **markdown trace** | `ai.incidents.md §Append-only trace` | никто новый | historical | **frozen** (read-only с 2026-05-10) |

**Контракт для агента/субагента (v2):**

- **НЕ обязан** руками писать markdown reasoning-log таблицу в чат на каждый скилл — она авто-захватывается из транскрипта Stop-хуком в граф. Boilerplate-блок «## Reasoning Log Protocol» в скилах — **deprecated**, заменяется одной строкой-указателем (sed-cleanup, отдельный коммит).
- **Обязан** писать reasoning-log таблицу в чат **только** когда owner явно спрашивает «почему ты так решил» / «покажи дерево рассуждения» — формат ниже.
- Для **substantial RCA** 16-field «Контекст инцидента» блок в trace file остаётся обязательным (§Auto-inject ниже) — GEPA training data, дополняет авто-граф смысловой разметкой.
- Найти узел-развилку: `python3 scripts/reasoning_log/graph.py --latest --find-divergence` (`--trace <id>` / `--all`). Граф в duckdb: `duckdb .reasoning-log/archive/reasoning.duckdb "SELECT * FROM reasoning_falsified"`.

**Canonical reference:** [`<standard-ref>)
**Mechanical enforcement:** [`.claude/hooks/trace_required_check.py`](../../.claude/hooks/trace_required_check.py) (PostToolUse on Stop event)

## Hired for JTBD

Когда owner хочет понять, почему агент принял конкретное решение, какие инструкции повлияли и где расхождение между ожиданием и реальностью → найти ответ в reasoning log, а не в памяти агента.

## When to use

- При каждом исполнении **любого** скилла (протокол инъецирован в 114 скилов)
- Когда owner спрашивает «почему ты так решил»
- Когда нужно найти инструкцию в стандартах/скилах, которая помешала сделать правильно
- Когда задача длится >3 ходов — лог сохраняется в файл

## Формат reasoning log в чате

```markdown
### Reasoning Log — [дата UTC]
| # | Решение | Источник evidence | Найден геп | Блокирующая инструкция | Ценность для owner |
|---|---------|-------------------|------------|------------------------|-------------------|
| 1 | {что решил агент} | {файл / команда / API} | {G01 — краткое имя гепа или «—»} | {path + секция + цитата ≤80 или «—»} | {что получил owner} |
```

**§0 macro:** колонка «Найден геп» — не голый `G01`, а **`G01 — краткое имя гепа`**. Голый код без подписи = hard fail (см. `AGENTS.md` §0 и `hypothesis-gap-falsification` §0).

## Формат записи в ai.incidents.md

Каждый вызов скилла оставляет строку в `<internal-folder>/ai.incidents.md` → таблица `## Append-only trace`:

```
| {UTC date} | {skill_name} | {owner prompt ≤240} | {steering: yes/no} | {target artifact} | {reasoning bullets} | {blocking_instruction} |
```

## Формат файлового лога (задачи >3 ходов)

Сохранять в `<internal-folder>/reasoning-logs/{date}-{skill}-{short-id}.md`:

```markdown
# Reasoning Log — {skill_name}
**Date:** {UTC}
**Owner prompt:** {≤240 chars}
**Task:** {краткое описание}

## Decisions
| # | Решение | Evidence | Геп | Блокирующая инструкция | Ценность |
|---|---------|----------|-----|------------------------|----------|

## Summary
- Гепов найдено: N
- Блокирующих инструкций: N
- Итог: {что сделано / что осталось}
```

## Метрики (считаем еженедельно)

- `reasoning_log_coverage` = скиллы с протоколом / всего скилов (target: 100%)
- `blocking_instruction_rate` = строки с blocking instruction / всего строк trace (target: снижение)
- `gap_discovery_rate` = строки с найденным гепом / всего строк (information only)

## Subagent pointer protocol (Standard 4.18 §Subagent pointer protocol)

Когда **субагент** (любой `code-reviewer`, `frontend-reviewer`, `backend-reviewer`, `ui-qa-engineer`, `security-reviewer`, `design-art-director`, `perf-reviewer`, `a11y-reviewer`, `rca-investigator`, `data-analyst`, `knowledge-researcher`, `outcome-designer`, etc.) возвращает результат main agent'у:

| Случай | Что возвращать в text response |
|---|---|
| Trace ≥ 500 строк ИЛИ ≥ 5 file changes | **Pointer-only:** строка `Trace: <internal-folder>/reasoning-logs/{date}-{agent}-{id}.md` + 3-line summary + verdict + top-3 findings |
| Trace < 500 строк И < 5 file changes | **Inline + pointer:** полный reasoning log как раздел в response + duplicate в file для history |
| Findings-table-first reviewer (8 review-агентов) | Findings table inline (как сейчас) + **обязательный** trace file pointer строкой в конце response с verdict roll-up |

**Hard fail для субагента:** возврат result без trace file pointer в substantial задаче.

## Self-check pre-answer (1 вопрос, не 7 — RCA 2026-04-26 v3.1)

Перед отправкой ответа в чат, агент **обязан** мысленно задать один вопрос:

> «Есть ли в моём финальном ответе путь к trace file (либо inline reasoning log если задача < 500 строк / < 5 file changes)?»

Если **нет** — переписать финальный ответ, добавив pointer на trace перед отправкой.

Это заменяет 7-вопросный self-check из owner Notion-документа: широкий чеклист → 0% adoption под нагрузкой; одно binary check → реализуемо.

## Auto-inject Контекст инцидента при substantial RCA (RCA 2026-05-02)

При любой substantial задаче (≥30 мин ИЛИ ≥5 file writes ИЛИ subagent invoked ИЛИ Write на protected path) агент **обязан** проверить триггеры RCA и при их наличии авто-инжектить блок «Контекст инцидента (для GEPA training data)» в свой trace file ДО его закрытия.

**Триггеры активации авто-инжекции** (any one):

| # | Триггер | Источник |
|---|---|---|
| 1 | Owner steering keywords: «опять», «снова», «уже X раз», «нихуя», «не работает», «переделай», «не понимаю», «recurrence», «рецидив» | последнее сообщение owner |
| 2 | Subagent verdict = `FAIL` / `needs-rework` / `falsified` | возврат субагента в текущем хождении |
| 3 | Hard fail из любого `.agents/skills/*/SKILL.md` активирован (vocabulary, expected-output, generalization, anti-legend, RU-language, runtime-not-checked) | inline detection |
| 4 | Hook block (`coherent_narrative_check.py`, `expected_output_announce_check.py`, `trace_required_check.py`) → exit 2 | stderr из hook |
| 5 | Owner написал `/rca` или явно «зафиксируй инцидент» | system message |

**Что инжектить (16 полей в 4 группах, шаблон — RCA 2026-05-03 owner T24 расширил с 12 до 16):**

```markdown
## Контекст инцидента (для GEPA training data)

### A. Контекст задачи и истории
- **original_owner_task:** "{первое сообщение owner запускающее ВСЮ задачу ≤500 — НЕ последнее steering!}"
- **task_origin_pointer:** {bead_id} — {bead title} — [bead]({URL}); [project]({path к {project}.todo.md}); [chat]({Telegram URL ИЛИ session ID})
- **reasoning_log_pointer:** <internal-folder>/reasoning-logs/{YYYY-MM-DD}-rca-{slug}.md
- **reasoning_log_excerpts:**
  - "{дословная цитата #1 ≤200 chars из trace file — ключевое decision}"
  - "{дословная цитата #2 ≤200 chars — failed attempt + reason}"
  - "{дословная цитата #3 ≤200 chars — blocking instruction найденная агентом}"

### B. Owner intent и failure
- **owner_prompt_verbatim:** "{последнее сообщение owner перед инцидентом ≤500}"
- **chat_jtbd:** Когда {триггер} → хочет {action} → чтобы {outcome}
- **expected_delivery:** {что owner ждал получить}
- **actual_failure_mode:** "{verbatim что сломалось ≤200}"

### C. GEPA tuning targets
- **target_artifact_for_tuning:** .agents/skills/{X}/SKILL.md (§{section}) ИЛИ .agents/agents/{Y}.md ИЛИ AGENTS.md §{section}
- **steering_verbatim:** "{correction цитата ИЛИ `none`}"
- **scoring_rubric_pass_criteria:**
  - ✓ {критерий 1}
  - ✓ {критерий 2}
  - ✓ {критерий 3}
- **cognitive_load_symptom:** {категория из канона: unreadable / bare-id-no-name / fragmented-tables / summary-only / subagent-output-unreadable / legend-instead-of-headers / forbidden-vocabulary / runtime-not-checked / context-lost / gate-skipped / missing-task-origin}

### D. Triggers и recurrence
- **recurrence_count_14d:** {N через grep -c "category: <cat>" "<internal-folder>/ai.incidents.md"}
- **triggers_that_should_have_fired:** {skill_name + trigger-token list}
- **skills_active_at_failure:** {skill_name list загруженных в context}
- **failed_attempts_summary:** {bullet-list попыток + причина провала каждой}
```

**Anti-summary правило (RCA 2026-05-03 owner T24, заимствовано из owner Notion-документа «trace-first»):**

- Trace file = **primary output**. Chat response = **secondary** (только pointer + 3-line summary + verdict).
- Если 16-field блок попал в чат целиком вместо строки `Trace: <path> + 16-field GEPA context attached` — **violation**: контекст должен жить в trace file, чат — только указатель.
- Mandatory tables в trace file (Standard 4.18 §Format trace file):
  1. **Files inspected** (path / why inspected / confidence)
  2. **Files changed** (path / change / reason / risk / how to verify)
  3. **Decisions** (step / decision / evidence / next step)
  4. **Errors and blockers** (blocker / where / cause / attempted fix / remaining risk)
  5. **Verification steps** (what / how / passed/failed)
- Без этих 5 таблиц trace неполный — `original_owner_task + reasoning_log_excerpts` ссылаются на пустоту.

**Self-check pre-answer (расширен с 1 до 3 вопросов — RCA 2026-05-03):**

Перед отправкой ответа в чат, агент **обязан** мысленно ответить «да» на 3 вопроса:

1. «Есть ли в моём финальном ответе путь к trace file (либо inline reasoning log если задача < 500 строк)?»
2. «Если был активирован RCA-trigger: записан ли 16-field блок в trace file (НЕ в чат)?»
3. «Если 16-field блок записан: содержит ли trace file 5 mandatory tables (Files inspected / Files changed / Decisions / Errors / Verification)?»

Если **любой ответ «нет»** — переписать финальный ответ ИЛИ trace file перед отправкой.

**Куда инжектить:**

1. **Primary:** в trace file `<internal-folder>/reasoning-logs/{date}-{agent-or-skill}-{id}.md` отдельной секцией `## Контекст инцидента (для GEPA training data)` после секции `## Decisions`.
2. **Mirror:** в incident block `<internal-folder>/ai.incidents.md` если RCA скил активирован (`rca-incidents` self-trigger).
3. **NOT в чат:** в финальном chat response достаточно одной строки `Trace: <path> + 12-field GEPA context attached`. Полный 12-field блок не выводить в чат — он в trace file.

**Связь с GEPA loop:** все 12-field блоки автоматически конвертируются в trainset.jsonl через `python3 .agents/skills/2-rca-incidents/scripts/incidents_to_gepa_trainset.py --incidents "<internal-folder>/ai.incidents.md" --since 14d --output trainset.jsonl`.

**Связь с rca-investigator:** субагент `rca-investigator` уже включает блок в `## Формат ответа` (см. `.agents/agents/rca-investigator.md` §Контекст инцидента). Auto-inject здесь нужен для **main agent** + других субагентов (не только rca-investigator) когда триггеры срабатывают вне явного RCA-flow.

**Hard fail (новый, RCA 2026-05-02):**
- Substantial задача с активированным триггером (любой из 1-5) завершилась без `## Контекст инцидента` блока в trace file → block + RCA `category: rca-context-auto-inject-skipped`.
- Trigger #4 (hook exit 2) активирован, но 12-field блок отсутствует → mechanical fail through hook + steering correction owner.

## Hard fail conditions (v2 — пересмотрено RCA 2026-05-17)

**Снято (было ошибочно hard fail):** «нет markdown reasoning-log таблицы в чате» / «не записана строка в ai.incidents.md trace» больше **НЕ** hard fail — reasoning log v2 авто-захватывается из транскрипта Stop-хуком в граф; ручная запись в чат и в frozen markdown-trace не требуется. Это снимает противоречие SKILL.md (mandate) vs MIGRATION.md (frozen, RCA 2026-05-17 G02) и убирает boilerplate из 168 скилов.

**Действующие hard fail (v2):**

1. Substantial RCA-триггер активирован (steering / subagent FAIL / hook exit 2 / hard fail из skill / `/rca`), но 16-field «Контекст инцидента (для GEPA training data)» блок не записан в trace file → RCA `category: rca-context-auto-inject-skipped` + delivery rework
2. Trace file создан, но не упомянут pointer'ом в финальном chat response (substantial задача) → reject, добавить pointer
3. Owner явно спросил «почему ты так решил» / «покажи дерево рассуждения», агент ответил без reasoning-log таблицы И без ссылки на `graph.py --find-divergence`
4. Субагент-ревьюер вернул verdict, но его `isSidechain` споны отсутствуют в графе (owner должен видеть дерево рассуждения проверяющего, не только исполнителя — RCA 2026-05-17 owner: «reasoning log нужен у субагентов-проверяющих»)
5. **(NEW v4.18, сохранено)** Substantial delivery (≥30 мин ИЛИ ≥5 file writes ИЛИ subagent invoked ИЛИ Write на protected path) без trace file в `<internal-folder>/reasoning-logs/{date}-{agent-or-skill}-{id}.md` → mechanical block через `trace_required_check.py` hook + RCA `category: trace-required-skipped`

## Owner value

Каждый reasoning log позволяет owner: (1) находить инструкции которые мешают, (2) видеть цепочку решений агента, (3) отслеживать метрики качества взаимодействия.

## Связанные скилы

- [`owner-prompt-capture`](.agents/skills/owner-prompt-capture/SKILL.md) — автозапись промтов owner
- [`hypothesis-gap-falsification`](.agents/skills/2-hypothesis-gap-falsification/SKILL.md) — фальсификация гипотез
- [`rca-incidents`](.agents/skills/2-rca-incidents/SKILL.md) — анализ корневых причин

## Reasoning Log Protocol (v2 — авто)

Reasoning log v2 ведётся **автоматически**: Stop hook (`reasoning_log_stop.py`) на каждом ходе вызывает `transcript_ingest.py`, который парсит Claude Code transcript JSONL в span-граф (`.reasoning-log/spans/` → duckdb). Агент не пишет markdown-таблицу руками. Boilerplate-блок «## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)» в 168 скилах — deprecated, заменяется одной строкой:

> `Reasoning Log: авто-захват из транскрипта в граф (.reasoning-log/), find-divergence — scripts/reasoning_log/graph.py. См. agent-reasoning-log/SKILL.md.`

Применяется один sed-проход (dry-run → отдельный коммит после verify ядра).


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick (включая TaskMaster и связанные стандарты Heroes Rickai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
