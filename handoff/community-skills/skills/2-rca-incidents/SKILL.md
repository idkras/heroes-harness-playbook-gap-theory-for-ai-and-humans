---
name: rca-incidents
description: "Используй, когда нужен понятный разбор инцидента: что случилось, почему, что меняем и как проверяем, что исправление реально сработало. Основано на RCA-стандарте и протоколе `ai.incidents.md`."
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скиллы `0-credentials-manager` + `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `heroes_platform/credentials`.

# RCA & Incidents Skill

## Назначение

**JTBD, Jobs To Be Done — задача, которую решает клиент:** Когда нужно провести анализ корневых причин, зафиксировать инцидент, найти место для дизайн-инъекции и пройти полный цикл изменений и исправлений — делать это по протоколу «без гепов», с явными input/output чеклистами и с финальной доставкой лучше первой попытки.

**Контекст:** Фидбек пользователя и работа по инциденту (дейли без review-artifact-for-client-readiness) запускаются через этот скилл: одна и та же последовательность шагов для любого инцидента.

## Обязательное правило языка для менеджера

Когда итоговый разбор читают менеджер, владелец проекта или любой человек без технического бэкграунда, использовать только понятные русские названия.

Писать так:

| Не писать в ответе пользователю | Писать так |
| --- | --- |
| `precedent scan` | `поиск похожих случаев` |
| `design injection` | `что именно меняем в процессе` |
| `blast radius` | `границы проблемы` |
| `artifact` | `материал`, `результат`, `сообщение`, `документ` — по смыслу |
| `claim` | `проверяемое утверждение` |
| `runtime evidence` | `проверка в живой работе` |
| `hard fail` | `проверка провалена` |
| `primary chain / secondary chain` | `основная цепочка причин / дополнительная цепочка причин` |
| `accepted / rejected / needs-data` | `подтверждается / отвергнута / не хватает данных` |
| `Next-Action Digest` | `что делать дальше` |

Если технический термин неизбежен, сначала написать смысл по-русски, потом точное имя в скобках один раз.

**Симметрия gap = jtbd = outcome = next action** (SSOT: `2-so-what-outcome-ladder/SKILL.md §Симметрия`): поле «next-best-action» в RCA обязано быть в owner-language с фальсифицируемым хвостом — не `commit fix`, а `избежать переделки X = добавить grep-проверку в orchestrator (1 строка)`. Hard fail: next-best-action в чистом техническом языке без owner-рамки → переписать симметрично outcome.

---

## When to Use

- «Сделай RCA по этому сбою»
- «Зафиксируй инцидент», «запиши в ai.incidents.md»
- «Найди место для дизайн-инъекции»
- «Работа по инцидентам», «цикл изменений и исправлений»
- После фидбека пользователя о качестве доставки (дейли, отчёт и т.д.) — разобрать как инцидент и довести до «доставлено лучше, чем в первый раз»

## Self-Trigger Contract (ОБЯЗАТЕЛЬНО, RCA 2026-04-25, recurrence-aware)

**Корневая причина:** скилл `2-rca-incidents` срабатывал только на явный owner-промпт «сделай RCA». Когда агент сам пропускал gate (vocabulary, generalization-first, expected output table) и owner ловил это в delivery, RCA не запускался автоматически — приходилось owner-у явно говорить «зафиксируй RCA». Это **5-й рецидив** vocabulary gate skip 2026-04-25.

**Правило (self-trigger):** агент **обязан** активировать `2-rca-incidents` скилл БЕЗ явного owner-промпта в следующих случаях:

| # | Триггер | Counter source (где живёт состояние) |
|---|---|---|
| 1 | Owner написал «опять», «снова», «уже X раз», «5-й раз», «recurrence», «3-й рецидив» | stateless (sufficient в текущем сообщении) |
| 2 | Agent сам обнаружил что нарушил hard rule из AGENTS.md / skill / standard (vocabulary gate, generalization-first, expected output table, RU-language, anti-legend) | stateless |
| 3 | Owner steering correction содержит «не делай X» / «почему ты опять делаешь X» | stateless |
| 4 | Subagent verdict = FAIL и есть ≥2 предыдущих RCA-trace с тем же `category` за последние 14 дней | **state источник:** grep по `[todo · incidents]/ai.incidents.md` `## Append-only trace` за последние 14 дней по полю category. Не sticky counter в memory, а audit log read. |
| 5 | Owner сказал «прочитай весь чат и найди свои ошибки» | stateless |
| 6 | Hard fail из любого `.agents/skills/*/SKILL.md` (HARD FAIL labels) активирован В ПЕРВЫЙ РАЗ в этом инциденте (idempotency-guard, RCA 2026-04-26 code-reviewer C2: иначе self-loop) | **state источник:** grep по `[todo · incidents]/ai.incidents.md` за текущую UTC-дату по `incident_id` или симптому. Если для текущего инцидента уже есть RCA-trace с этой категорией → skip. |

**Idempotency guard (RCA 2026-04-26 code-reviewer C2):**
- Один инцидент = один RCA-trace в `ai.incidents.md` за UTC-дату.
- Триггер #6 не запускает новый RCA если для текущего incident_id (или ≥2 совпадений симптом-токенов) уже есть запись с `## YYYY-MM-DD ## incident-{id}`. Иначе hard fail self-trigger создал бы рекурсию (skill сам содержит hard fail про rca-self-trigger-skipped).
- Если симптом тот же, но повторился — это рецидив (триггер #1 «X раз»), не новый инцидент. Pre-check grep на recurrence до создания нового entry.

**Что обязан сделать агент** при self-trigger:

1. Открыть `[todo · incidents]/ai.incidents.md` и проверить precedent (grep по симптому за последние 14 дней).
2. **Idempotency check:** есть ли уже RCA-trace для текущего инцидента? Да → skip. Нет → continue.
3. Записать строку в `## Append-only trace` таблицу с полями: дата UTC, skill_name, owner prompt, steering: yes/no, target artifact, reasoning bullets, blocking_instruction.
4. Для рецидива ≥3 (по grep counter триггера #4) — провести **полный RCA** по протоколу §0–§7 (5 whys, primary/secondary chain, hypotheses, design injection).
5. Применить **design injection** (не addition, а структурный фикс) к скиллу/стандарту/AGENTS.md, который пропустил рецидив.
6. В chat artifact — Reasoning Log с decision/evidence/gap found/blocking_instruction/owner value.

**Hard fail self-trigger (с idempotency-aware semantics):**
- Owner написал «опять», агент не активировал скилл, idempotency check не прошёл → RCA в `ai.incidents.md` `category: rca-self-trigger-skipped`
- Subagent FAIL и grep по trace за 14 дней показал ≥2 предыдущих RCA того же category, RCA не запущен → RCA + steering correction owner
- Hard fail из other skill активирован В ПЕРВЫЙ РАЗ для текущего инцидента, RCA не записан → RCA + design injection. **Повторный** hard fail того же RCA (рекурсия) → НЕ создаёт новый RCA, только инкрементит counter в существующем trace.

---

## Input Checklist (перед началом)

- [ ] Есть описание симптома или фидбек пользователя (что пошло не так, что «не читается», что забыли).
- [ ] Открыт файл инцидентов: `[todo · incidents]/ai.incidents.md`.
- [ ] Понятен **канон записи в журнал**: одна секция `## DD MMM YYYY` на календарный день, внутри дня — **одна** markdown-таблица на все строки этого дня (trace и полный RCA — одна ширина колонок); см. Standard 1.1 § «Канон разметки `ai.incidents.md`». При **реструктуризации всего файла** или смене заголовка таблицы — не массово с первого прохода: протокол S0–S7 в `.agents/skills/1-next/SKILL.md` § «Шаг за шагом» + falsification по `.agents/skills/2-hypothesis-gap-falsification/SKILL.md`.
- [ ] Выполнен поиск похожих случаев по `ai.incidents.md`: найдены похожие инциденты, прошлые решения, которые уже предлагались, и повторно используемые выводы; либо честно написано, что похожих случаев не найдено.
- [ ] Прочитаны стандарты: [AI Incident Standard 1.1]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.1 ai incident standard 14 may 2025 0505 cet by ai assistant.md), [RCA Standard 1.6]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.6 root cause analysis 14 may 2025 0700 cet by ai assistant.md), при необходимости [Gap Theory 1.5]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.5 gap theory standard 26 august 2025 2325 CET by ilya krasinsky.md).
- [ ] Понятно, какой артефакт/доставка была «первой попыткой» (дейли, отчёт, сообщение в чат и т.д.).
- [ ] Проверено, не работал ли инцидент в multi-agent режиме (2+ агентов в одном workspace / branch / worktree).
- [ ] Проверено, виден ли lifecycle проекта в `todo.md`, `.beads` и обязательном временном `duckdb` слое.
- [ ] Если инцидент связан с live workflow / automation, доказан ли business context target: audience, sender, recipients, storage, JTBD этого flow.

---

## Instructions (протокол без гепов)

### 0. Поиск похожих случаев + видимый разбор в чате (ОБЯЗАТЕЛЬНО)

- До или вместе с обновлением файлов RCA обязан показать в чате читаемый разбор, а не только ссылки на строки или краткое резюме.
- Минимальный материал в чате:
  - `Текущий тикет` — если уже есть existing bead / ticket / issue, показать именно его целиком в fenced `md` code block.
  - `Похожие случаи` — 1-5 похожих записей из `ai.incidents.md` с коротким объяснением, что именно переиспользуем.
  - `Какие старые решения переиспользуем` — что из прошлых исправлений подходит к текущему случаю.
  - `Таблица гипотез` — основное объяснение и альтернативы с выводом по каждой.
  - `Основная и дополнительная цепочка причин`.
  - `Что именно меняем`.
- Если похожих инцидентов нет, агент обязан написать это явно: `Похожих инцидентов в ai.incidents.md не найдено`.
- Если в этом же ходе менялись файлы, в чат нужно вывести не только paths, но и **exact changed excerpts / change-pack**:
  - `before -> after`
  - или короткие цитаты изменённых строк / блоков
  - или таблицу `запрос -> изменение -> почему это сделали -> где это видно`
- Запрещено считать RCA пригодным для проверки, если в чат ушли только:
  - ссылки на файлы,
  - line refs,
  - резюме без гипотез и похожих случаев,
  - заявление `всё исправлено` без видимого материала.

### 0.1. Existing ticket first (ОБЯЗАТЕЛЬНО)

- Если incident уже привязан к existing bead / ticket / issue, RCA обязан продолжать **этот же** материал, а не создавать параллельный.
- Synthetic `local-*` ticket или shadow replacement card запрещены.
- В первом большом RCA-ответе блок `Текущий тикет` идёт первым и отвечает на 4 вопроса:
  - какой материал главный;
  - что в нём сейчас сломано;
  - что считаем критерием готовности;
  - что делаем сейчас.

```text
Текущий тикет
id: ...
название: ...
статус: ...
ситуация-проблема: ...
критерий готовности: ...
что делаем сейчас: ...
```
### 0.2. Переписать плохой текущий тикет или карточку (ОБЯЗАТЕЛЬНО)
- Если owner пишет, что existing ticket / bead `плохой`, `не по стандарту`, `не проходит review`, RCA не имеет права использовать его как будто continuity уже достаточна.
- Обязательный порядок:
  1. назвать текущий материал;
  2. кратко показать standard violations;
  3. same-turn запустить rewrite-route по [`1-ticket-review`](../1-ticket-review/SKILL.md);
  4. проверить readback из source-of-truth;
  5. только потом снова использовать его как `Текущий тикет`.
- Запрещено:
  - лечить только chat delivery вокруг плохой карточки;
  - выдавать список section labels за proof качества;
  - создавать новый substitute ticket вместо rewrite same ticket.
- Хорошее доказательство качества тикета: в чате показана **переписанная та же карточка целиком** в fenced `md` block, сразу после этого выполнен `1-ticket-review`, а затем показано подтверждение чтением из источника истины в fenced `text/json` block.

### 0.3. Контекст инцидента — 12 полей для GEPA training data (ОБЯЗАТЕЛЬНО, RCA 2026-05-02)

**Зачем:** запись инцидента становится одной trainset case для `2-gepa-prompt-loop`. Reflection LLM использует `owner_prompt_verbatim + actual_failure_mode + steering_verbatim + scoring_rubric` для генерации улучшенного промта target артефакта. Без этих полей RCA технически closed, но GEPA не может тюнить промт — генерируется «общая» mutation вместо адресной.

**RCA-источник 2026-05-02:** инциденты `incident-code-reviewer-output-unreadable-for-owner` (T22) показали что без сохранённого `owner_prompt_verbatim` + `chat_jtbd` контекст теряется через 1-2 ходов; через неделю невозможно восстановить «почему именно это сломалось» и какой промт подкручивать.

**16 обязательных полей** в 4 группах (A контекст задачи / B owner intent / C GEPA targets / D triggers) — записываются в `ai.incidents.md` в инцидент-блок ПЕРЕД 5 whys. Расширено с 12 до 16 (RCA 2026-05-03 owner T24): добавлены `original_owner_task` (первое сообщение owner запускающее задачу, не последнее steering), `task_origin_pointer` (bead + project todo + chat origin), `reasoning_log_excerpts` (3-5 прямых цитат из trace file), `failed_attempts_summary` (что агент попробовал и почему не сработало).

### A. Контекст задачи и истории — 4 поля

| # | Поле | Что писать | Источник |
|---|---|---|---|
| 1 | `original_owner_task` | **первое** сообщение owner запускающее ВСЮ задачу ≤500 символов (не последнее steering!) | backscroll начала чата · `{project}.todo.md` · bead `Description` |
| 2 | `task_origin_pointer` | bead + project todo + chat origin через §0 macro трёхзвенно | `{bead_id} — {title} — [bead]({url}); [project]({path}); [chat]({URL/ID})` |
| 3 | `reasoning_log_pointer` | `[todo · incidents]/reasoning-logs/{YYYY-MM-DD}-rca-{slug}.md` | создать ДО RCA write (Standard 4.18) |
| 4 | `reasoning_log_excerpts` | **3-5 прямых цитат ≤200 chars каждая** из trace file: ключевые decisions / failed attempts / blocking instructions | копировать дословно (не парафраз) |

### B. Owner intent и failure — 4 поля

| # | Поле | Что писать | Источник |
|---|---|---|---|
| 5 | `owner_prompt_verbatim` | дословная цитата **последнего** запроса owner ≤500 символов | последнее сообщение owner перед инцидентом |
| 6 | `chat_jtbd` | JTBD owner восстановленный из последних 5-30 сообщений: «когда → хочет → чтобы» | переписка |
| 7 | `expected_delivery` | что owner ждал получить (формат, поля, структура) — НЕ что агент думал | парафраз последнего «должно быть так» |
| 8 | `actual_failure_mode` | verbatim что сломалось в первой попытке ≤200 символов | observable artifact |

### C. GEPA tuning targets — 4 поля

| # | Поле | Что писать | Источник |
|---|---|---|---|
| 9 | `target_artifact_for_tuning` | путь: `.agents/skills/X/SKILL.md` (§section) ИЛИ `.agents/agents/Y.md` ИЛИ `AGENTS.md §section` | какой prompt тюним через GEPA |
| 10 | `steering_verbatim` | дословная correction («нихуя», «опять», «переделай») ИЛИ `none` | finally правки owner |
| 11 | `scoring_rubric_pass_criteria` | 3-7 binary критериев `✓/✗` для пометки future delivery как PASS | rubric для GEPA evaluator |
| 12 | `cognitive_load_symptom` | категория из канона: `unreadable` / `bare-id-no-name` / `fragmented-tables` / `summary-only` / `subagent-output-unreadable` / `legend-instead-of-headers` / `forbidden-vocabulary` / `runtime-not-checked` / `context-lost` / `gate-skipped` / `missing-task-origin` | Pareto dimension |

### D. Triggers и recurrence — 4 поля

| # | Поле | Что писать | Источник |
|---|---|---|---|
| 13 | `recurrence_count_14d` | N-й раз за 14 дней по `grep -c "category: <cat>" "[todo · incidents]/ai.incidents.md"` | команда обязательна |
| 14 | `triggers_that_should_have_fired` | skill activation triggers / hook patterns / regex которые пропустил агент | grep по `description:` skills |
| 15 | `skills_active_at_failure` | скилы загруженные в context при промахе | `system-reminder` listing |
| 16 | `failed_attempts_summary` | что попробовал и почему не сработало — критично для GEPA reflection_lm | trace file `Decisions` + `Errors` tables |

**Запись в `ai.incidents.md` (формат блока — 16 полей в 4 группах):**

```md
## Контекст инцидента (для GEPA training data)

### A. Контекст задачи и истории
- **original_owner_task:** "{первое сообщение owner запускающее задачу ≤500}"
- **task_origin_pointer:** {bead_id} — {bead title} — [bead]({URL}); [project]({path к {project}.todo.md}); [chat]({Telegram URL ИЛИ session ID})
- **reasoning_log_pointer:** [todo · incidents]/reasoning-logs/{YYYY-MM-DD}-rca-{slug}.md
- **reasoning_log_excerpts:**
  - "{дословная цитата #1 ≤200 chars из trace file — ключевое decision}"
  - "{дословная цитата #2 ≤200 chars — failed attempt + reason}"
  - "{дословная цитата #3 ≤200 chars — blocking instruction найденная агентом}"

### B. Owner intent и failure
- **owner_prompt_verbatim:** "{последнее сообщение owner ≤500}"
- **chat_jtbd:** Когда {триггер} → хочет {action} → чтобы {outcome}
- **expected_delivery:** {что owner ждал получить}
- **actual_failure_mode:** "{verbatim ≤200}"

### C. GEPA tuning targets
- **target_artifact_for_tuning:** .agents/skills/{X}/SKILL.md (§{section})
- **steering_verbatim:** "{correction цитата ИЛИ `none`}"
- **scoring_rubric_pass_criteria:**
  - ✓ {критерий 1}
  - ✓ {критерий 2}
  - ✓ {критерий 3}
- **cognitive_load_symptom:** {категория}

### D. Triggers и recurrence
- **recurrence_count_14d:** {N} (cmd: grep -c ...)
- **triggers_that_should_have_fired:** {skill_name + trigger-token}
- **skills_active_at_failure:** {список skill_name}
- **failed_attempts_summary:** {bullet-list попыток + причина провала}
```

**Hard fail (8 условий):**
1. Запись инцидента без блока с **16 полями** в 4 группах = incident not closed, RCA reject.
2. `original_owner_task` = `owner_prompt_verbatim` (один и тот же текст) = hard fail. Это **разные** поля: первый = корень задачи (start of chat / bead description), второй = последний промпт перед инцидентом.
3. `task_origin_pointer` без bead ID или без path к `{project}.todo.md` = hard fail (теряется ANCHOR — невозможно через неделю понять «в какой задаче случилось»).
4. `reasoning_log_excerpts` пустой ИЛИ <3 цитат ИЛИ парафраз вместо дословных цитат из trace file = hard fail (без citations reflection_lm не видит реальный decision chain).
5. `owner_prompt_verbatim` подменён парафразом / summary = hard fail.
6. `target_artifact_for_tuning` = `unknown` без объяснения = hard fail.
7. `reasoning_log_pointer` указывает на несуществующий file = hard fail (нарушает Standard 4.18 §Subagent pointer protocol).
8. `scoring_rubric_pass_criteria` < 3 критериев = hard fail (rubric не дискриминирует).

**Anti-summary правило (RCA 2026-05-03 owner T24):** trace file = primary output. Chat response = secondary (только pointer + 3-line summary + verdict). Если в чат уходит 16-field блок целиком вместо строки `Trace: <path> + 16-field GEPA context attached` — это **violation**: контекст должен жить в trace file, чат — только указатель.

**Связь с GEPA loop:** этот блок 1:1 конвертируется в одну строку `trainset.jsonl` для [`2-gepa-prompt-loop`](mdc:.agents/skills/2-gepa-prompt-loop/SKILL.md):

```json
{
  "input": "<owner_prompt_verbatim>",
  "additional_context": {
    "chat_jtbd": "...",
    "skills_active": [...],
    "triggers_missed": [...],
    "recurrence_14d": N
  },
  "answer": "<expected_delivery>",
  "feedback": "<actual_failure_mode> + <steering_verbatim>",
  "rubric": [<scoring_rubric_pass_criteria>],
  "target_component": "<target_artifact_for_tuning>"
}
```

**Команда для batch-конверсии всех инцидентов с этим блоком в trainset:**

```bash
python3 .agents/skills/2-rca-incidents/scripts/incidents_to_gepa_trainset.py \
  --incidents "[todo · incidents]/ai.incidents.md" \
  --since 14d \
  --target-artifact ".agents/skills/X/SKILL.md" \
  --output "[projects]/gepa-runs/<tag>/trainset.jsonl"
```

(скрипт создаётся отдельным тикетом — без него owner может конвертировать блоки вручную)

### 1. Зафиксировать инцидент

- Добавить запись в `ai.incidents.md` (в начало файла).

#### 1.0. Git-class routing (ОБЯЗАТЕЛЬНО, RCA 2026-06-04)

Если инцидент **git-класса** (грязное дерево, stash, branch-substitution, merge/rebase конфликт, worktree drift, orphan commit, lost work, CI на ветке, submodule pointer, gitignored-tracked) — запись по **двойному контракту**: (1) полный разбор → `git.incidents.md`; (2) индекс-строка back-link в `ai.incidents.md`; (3) `make incidents-parquet` rebuild. Анализ рецидивов — скил `2-incident-duckdb-analysis`. **Hard fail:** git-инцидент только в `ai.incidents.md` полным разбором (не в `git.incidents.md`) ИЛИ parquet не пересобран → `category: git-incident-routing-skipped`.
- Формат: дата, краткое описание, симптом, **блок «Контекст инцидента (12 полей)» из §0.3**, при необходимости гепы (Gap Theory): процессный, JTBD, контекстный.

### 2. RCA — 5 почему и корневая причина

- Провести разбор «5 почему» до корневой причины (не останавливаться на симптоме).
- Записать корневую причину в инцидент (кратко, до ~100 символов).

### 2.1. Альтернативные корневые причины и причинная цепочка (ОБЯЗАТЕЛЬНО)

- Построить минимум 3 альтернативных объяснения корневой причины (не только основное).
- Для каждой гипотезы выписать:
  - подтверждающие факты,
  - опровергающие факты,
  - оценку вероятности (0.0-1.0),
  - impact (1-5),
  - вывод (`подтверждается` / `отвергнута` / `не хватает данных`).
- Формат таблицы:

| Объяснение | Факты "за" | Факты "против" | Вероятность | Влияние | Вывод |
| --- | --- | --- | --- | --- | --- |
| [вариант #1] | [...] | [...] | [0.00-1.00] | [1-5] | подтверждается / отвергнута / не хватает данных |

- Построить причинно-следственную цепочку, чтобы не терять промежуточные причины:
  - `Симптом -> Промежуточная причина -> Сбой в процессе -> Корневая причина -> Что меняем`.
- Если есть несколько веток, явно выделить основную и дополнительную цепочку причин.
- Добавить карту по зонам влияния:
  - что сломано точно,
  - что не сломано (чтобы не чинить лишнее),
  - какие зоны требуют дополнительной валидации.
- Эти гипотезы нельзя держать только во внутреннем reasoning или только в `ai.incidents.md`: краткая hypothesis table обязана появиться и в чате.

### 2.1.5.1. Opaque jargon / abbreviations in agent chat (ОБЯЗАТЕЛЬНО, если owner жалуется на «непонятные сокращения» или рост cognitive load)

**Симптом:** В ответе агента появляются аббревиатуры без расшифровки в том же сообщении (пример исторического долга: **OEU** = введено в §7.2 этого скилла как «Owner Effort Units» — для owner это шум).

**Root cause (типовой):** Скилл/стандарт ввёл метку для краткости внутри команды; агент скопировал метку в operator-facing таблицу без колонки «что это значит».

**Где искать источник «говна» (порядок):**

1. **Репо:** `rg` по `.agents/skills/`, `AGENTS.md`, `[standards .md]/`, `[todo · incidents]/` на токен аббревиатуры; зафиксировать **первый файл-ввод** (canonical source).
2. **Трассировки в репо:** `[todo · incidents]/ai.incidents.md` → секция **Append-only trace**; при наличии — `[todo · incidents]/reasoning-logs/*.md`.
3. **Логи Cursor (размышления / tool / MCP):** macOS — `~/Library/Application Support/Cursor/logs/` (см. [read-verify-logs-output](mdc:.agents/skills/2-read-verify-logs-output/SKILL.md)); искать строки с тем же токеном рядом с решением агента.

**Design injection (обязательная):**

- В **owner-facing** таблицах: **не вводить** новые аббревиатуры; для шкалы усилий использовать колонку **`усилие человека (0–100)`** (или полное предложение в заголовке), а не сокращения вроде исторического OEU.
- Если аббревиатура неизбежна (имена API): одна строка glossary **в той же таблице**.
- Обновить источник в скилле/правиле, откуда агент скопировал жаргон; одна строка в **Сводка по инцидентам** Standard 1.13 при системном паттерне.

### 2.1.5. Похожие случаи и прошлые решения (ОБЯЗАТЕЛЬНО)

- При каждом RCA сделать поиск по `ai.incidents.md` на:
  - похожий symptom,
  - похожий process failure,
  - похожий delivery failure,
  - похожее изменение в процессе или правиле.
- В чате и в incident entry выписать:
  - `Какие похожие случаи посмотрели`
  - `Какие старые решения подходят и сейчас`
  - `Почему старого решения оказалось недостаточно`
  - `Какое новое изменение добавляем сейчас`
- Если старый инцидент уже содержал подходящую injection, а текущий сбой всё равно произошёл, RCA обязан отдельно ответить:
  - почему это изменение не было реально внедрено,
  - в каком skill/rule/flow enforcement развалился,
  - что именно меняем теперь: правило, маршрут, проверку или формат доставки.

### 2.1.4. Poor subtask decomposition / critical-chain incident (ОБЯЗАТЕЛЬНО при фидбеке на плохие подзадачи)

- Если пользователь говорит, что подзадачи выделены плохо, их слишком много, они не образуют критическую цепочку или в них потерян `Outcome -> Output -> Blockers`, RCA обязан отдельно выписать:
  - какой skill был использован как primary planner;
  - какой skill должен был быть primary (`next` по умолчанию для critical chain и from-the-end planning);
  - где произошла подмена: `inventory of tasks` вместо `constraint-driven chain`;
  - какой первый measurable/usable outcome должен был быть anchor point.
- После этого RCA обязан собрать **сокращённую critical chain**:
  - `Outcome`
  - `Output`
  - `Current blocker / constraint`
  - `ST001`
  - `ST002`
  - `ST003` only if required to reach first usable outcome
- Если после сокращения остаётся 4+ равновесных подзадачи, incident считать не закрытым: root cause ещё не найдена.

### 2.1.1. Multi-agent isolation check (ОБЯЗАТЕЛЬНО при параллельной работе)

- Если пользователь запускал 2+ агентов одновременно, RCA обязан отдельно проверить:
  - работали ли агенты в одном `main` worktree;
  - были ли отдельные branch/worktree на каждую задачу;
  - смешался ли `stage all` / commit / release scope между задачами;
  - мешал ли shared worktree вернуться к исходной задаче.
- Если ответ хотя бы на один из пунктов выше `да`, в RCA и design changes нужно добавить isolation contract:
  - `one agent -> one branch/worktree`
  - `main` only for selective merge/release
  - старый shared dirty worktree не использовать как release candidate

### 2.1.2. Project visibility contract (ОБЯЗАТЕЛЬНО для больших инициатив)

- Если инцидент связан с тем, что пользователь не видит проект как целый lifecycle, RCA обязан отдельно проверить:
  - есть ли отдельный `{projectname}.todo.md`;
  - зарегистрирован ли проект в root `todo.md`;
  - есть ли bead/issue в `.beads`;
  - есть ли временный `duckdb` mirror для проектных фаз, если migration to beads is not complete.
- Если хотя бы одного слоя нет, design changes обязаны указать:
  - где создать/обновить `todo.md`;
  - как зарегистрировать проект в `.beads`;
  - где лежит canonical `duckdb` mirror и какие таблицы в нём обязательны (`project_status`, `phase_status` или эквивалент).
- Если проектная фаза или blocker изменились, RCA обязан обновить все три слоя синхронно:
  - project/root `todo.md`;
  - `.beads` issue/project;
  - временный `duckdb` mirror.

### 2.1.3. Live workflow business-context audit (ОБЯЗАТЕЛЬНО перед production edit)

- Перед любым `PUT` / deploy в live `n8n` workflow RCA и execution pass обязаны доказать:
  - `workflow_id` и `UI title`;
  - кто реальный получатель (`client`, `student`, `internal team`, `care`, `onboarding`);
  - кто sender (`Lisa`, bot, manager, moderation path);
  - какие storage артефакты и таблицы он пишет;
  - почему этот flow относится именно к текущему JTBD-проекту.
- Если хотя бы один из пунктов выше не доказан, live edit запрещён; статус проекта должен вернуться в `discovery / target confirmation`, а не в `partial live`.

### 2.2. Widget Evidence Card для инцидентов Rick.ai (ОБЯЗАТЕЛЬНО при `widget_id`)

- Если симптом/разбор содержит `widget_id`, в RCA и в повторной доставке добавить **Widget Evidence Card**:
  - `company_alias`, `app_id`, `widget_id`
  - `widget title / human label` (если API `name` пустой, собрать рабочее название из `group_name + widget role`)
  - `widget type`
  - `widget url` (deep link через `generate_widget_url`, а не вручную)
  - `system_name`
  - `group / folder`: `group_name`, `group_id`
  - `scenario-folder yaml path` или явно `yaml export not available`
  - период (`start_date`, `end_date`)
  - `groups/group_key` (точный список)
  - `metrics catalog`: `metric_key -> glossary_name -> ui_label` (не только `custom_metrics_v2.*`)
  - 3-10 **raw widget sample rows** с реальными значениями
  - если в ответе фигурирует итоговый CSV / report / upload artifact, отдельно дать `Derived Artifact Sample` и mapping `raw widget field -> derived field`
- Запрещено закрывать RCA по виджету, если в тексте есть только номер виджета без карточки.
- Запрещено выдавать sample rows из итогового artifact как будто это raw rows самого widget.

### 2.3. Rick Taxonomy Card для data-сценариев (ОБЯЗАТЕЛЬНО при `behavior / ecommerce / geo / demand`)

- Если симптом/разбор связан не с одним isolated widget, а со сценарием:
  - `behavior history`
  - `ecommerce events`
  - `city / region`
  - `session / traffic / landing`
  - `demand / search / product discovery`
  в RCA и в повторной доставке добавить **Rick Taxonomy Card**.
- Минимальный состав:
  - `anchor widgets`
  - `behavior widgets`
  - `grouping catalog`
  - `event taxonomy`
  - `metric glossary`
  - `geo/session taxonomy`
  - `verification contract`
- Запрещено закрывать RCA фразой «нашли нужный widget», если не показано, как этот widget встроен в полный taxonomy contract сценария.

### 3. Где именно менять процесс

- Указать **конкретную точку** в процессе/скилле/правиле/коде, где нужно изменить поведение (не более ~50 символов в формулировке).
- Примеры: «Этап перед отправкой дейли в чат (скилл registry-daily-digest)», «Правило core-auto: секция TEAM-FACING MESSAGES».

### 4. Что именно меняем

- Описать конкретные изменения: что добавить или изменить в скилле, правиле, стандарте, скрипте, чтобы убрать корневую причину.
- Зафиксировать в инциденте блок `Что именно меняем`.

### 4.1. Post-change loop в `ai.incidents.md` (ОБЯЗАТЕЛЬНО после внесения изменений)

- Сразу после фактических правок обновить **эту же запись инцидента** в `ai.incidents.md`, а не оставлять только RCA и design injection.
- В записи инцидента обязаны появиться отдельные блоки:
  - `Решение` — какой operational/design choice принят.
  - `Что изменили` — какие skill/rule/standard/code paths реально изменены.
  - `Как проверяем гипотезу` — какой наблюдаемый сигнал должен измениться, где он проверяется, что считаем `confirmed` и что считаем `failed`.
  - `Когда вернуться к проверке` — дата, следующий trigger/event или условие повторной проверки.
- Минимальный шаблон для записи:

```md
**Решение:**
- [...]

**Что изменили:**
- [path / skill / rule] — [delta]

**Как проверяем гипотезу:**
- signal: [...]
- where to check: [...]
- success criteria: [...]
- failure signal: [...]

**Когда вернуться к проверке:**
- [date / next recurring task / next live delivery / next similar request]
```

- Если изменения внесены, но блок `Как проверяем гипотезу` не заполнен, статус `Hypothesis Testing` ставить запрещено.
- Если нет явного `Когда вернуться к проверке`, инцидент считается плохо замкнутым: к нему трудно вернуться и проверить, сработала гипотеза или нет.
- После same-turn redo в эту же запись инцидента нужно дописать явный verdict проверки: `сработало / не сработало / сработало частично`.

### 5. Обновить стандарт 1.13 и список инцидентов

- **ai.incidents.md** — источник истины для полного текста инцидента (уже добавлена запись на шаге 1).
- После design changes именно `ai.incidents.md` должен содержать не только RCA, но и post-change verification loop: `Решение -> Что изменили -> Как проверяем гипотезу -> Когда вернуться к проверке`.
- **Стандарт 1.13** ([AI Agent Typical Gaps and Prevention]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.13 ai agent typical gaps and prevention standard 13 feb 2026 cet by ai assistant.md)) — обновить обязательно:
  - В таблицу **«Сводка по инцидентам»** добавить или обновить строку: дата, симптом (коротко), корневая причина (коротко), дизайн-инъекция, статус.
  - Если инцидент выявил новый тип гэпа (нет в таблице «Типовые гэпы и проблемы») — добавить строку в эту таблицу: категория, типовой гэп, ожидаемое поведение, где зафиксировано (ai.incidents + дата).
- Без обновления 1.13 работа по инциденту не считается завершённой.

### 6. Цикл изменений и исправлений

- Внести изменения во все зависимые документы (скиллы, правила, стандарты, KB).
- Обновить версии/changelog где применимо.
- Проверить: нет ли гепов между ожидаемым и фактическим поведением (Gap Theory).

### 6.1. Operator comms: запрет §-заглушек и коллизия нумерации (ОБЯЗАТЕЛЬНО при RCA про reviewability / markdown-доставку)

- **FORBIDDEN:** сообщения в чат вида «Вставляю §2.2 через скрипт из‑за объёма» **без**:
  - repo path целевого файла;
  - точного заголовка секции как в файле (`##` / `###`);
  - одной строки JTBD (зачем owner это смотрит);
  - при использовании скрипта — имени команды/скрипта и зачем он (не «из-за объёма» как единственное объяснение).
- **Почему:** символ **§ и номер секции** легко **конфликтуют** с нумерацией в этом же skill (например, здесь **§2.2** в другом контексте = Widget Evidence Card для `widget_id`) и с другими стандартами; без path owner не может сопоставить комм с артефактом.
- **REQUIRED:** использовать **Document Addressing Block** из skill [`hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md) для любых «я сейчас вставляю / генерю большой блок в документ».

### 7. Исправить задачу и сделать новую доставку

- **Обязательно:** не заканчивать только «исправлениями в документах». Нужна **новая доставка** того же артефакта (дейли, отчёт, сообщение в чат) — уже с учётом ошибок и косяков первой попытки.
- **Immediate redo contract:** если пользователь попросил `RCA`, `зафиксируй инцидент`, `сделай дизайн-инъекцию`, агент в этом же ходе обязан после внесения design changes **сразу попробовать заново выполнить исходную задачу / повторить прошлую доставку**, а не останавливаться на docs-only pass.
- Если redo в этом же ходе невозможен, агент обязан явно показать:
  - какой exact blocker мешает redo сейчас,
  - почему его нельзя обойти разумным способом,
  - какой exact next action остался.
- Порядок: черновик → review-artifact-for-client-readiness (если применимо) → правки → отправка/публикация.
- Критерий: получатель может прочитать и понять без внутреннего контекста; заголовки выделены (полужирные в чате); «доставлено» vs «написал в чат» разделены, если речь про дейли.
- Если сбой произошёл в `beads-first / project-governance / registry` deliverable, повторная доставка обязана содержать отдельный блок `Graph from bd/Dolt` с источником графа (`bd --readonly list/show --json` или server-backed Dolt). Root `issues.jsonl` и `.beads/issues.jsonl` не являются fallback и должны отсутствовать; `.beads/issues.jsonl` дополнительно опасен тем, что может запустить stale auto-import до загрузки config.
  - Human-facing contract: сначала смысловые ветки, активные блокеры и следующие outputs.
  - Raw bead ids допустимы только как secondary technical refs, а не как первая строка каждого узла.
- В summary явно перечислить `Skills used`, и если был применён этот протокол, писать `rca-incidents` первым.
- Если исходный фидбек был про reviewability (`не вижу`, `не могу сделать review`, `покажи изменения`, `где гипотезы`, `где примеры`), новая доставка обязана содержать:
  - exact changed excerpts,
  - visible hypotheses,
  - similar incidents,
  - reused design injections,
  а не только итоговый список changed files.
- Если этот же фидбек был про плохой ticket/bead, новая доставка обязана в том же ходе содержать full rewritten ticket в fenced `md` block, diff-layer `Source wording vs Agent wording` и `1-ticket-review` readback proof.

### 7.0. Проверка после redo: сработала гипотеза или нет (ОБЯЗАТЕЛЬНО)

- После **same-turn redo** агент обязан не только повторить задачу, но и явно проверить, устранила ли design injection исходный симптом на этом же кейсе.
- В финальном pass обязателен короткий verdict:
  - `Redo result: worked`
  - `Redo result: partially worked`
  - `Redo result: did not work`
- Для verdict нужно показать:
  - какой исходный симптом проверяли,
  - чем именно его перепроверили после redo,
  - какой observable result получили,
  - считается ли гипотеза подтверждённой на этом кейсе.
- Если redo выполнен, но symptom всё ещё воспроизводится или outcome всё ещё не достигнут:
  - запрещено закрывать цикл на `Hypothesis Testing` как будто всё в порядке;
  - нужно явно написать `hypothesis did not hold on redo`;
  - продолжить цикл: новый gap -> уточнение root cause/design change -> ещё один redo или явный blocker.
- Если symptom снят на текущем кейсе, но нужен отложенный follow-up на следующем живом запросе/итерации, писать оба слоя:
  - `Redo result on this case: worked`
  - `Follow-up status: still monitoring`
- Минимальный блок для `ai.incidents.md` после redo:

```md
**Результат проверки после redo:**
- initial symptom checked: [...]
- redo check: [...]
- observed result: [...]
- verdict: worked / partially worked / did not work
- next move: confirm / keep monitoring / reopen RCA
```

### 7.0.1. Runtime Verification Gate при redo (ОБЯЗАТЕЛЬНО для сервисов, API, UI, pipeline)

**RCA-источник:** инцидент 2026-04-05 — агент собрал инфраструктуру LightRAG (скрипты, .env, health checker), заявил «всё готово» через redo, но ни разу не открыл `localhost:9621` и не вызвал API. Файлы на месте, verdict `worked` — а сервис не запущен.

**Правило:** если исходный симптом инцидента связан с **runtime-состоянием** (сервис не работает, API не отвечает, pipeline не прошёл, UI не открывается, граф данных пуст), то redo verdict **обязан** включать хотя бы одно runtime-доказательство:

| Доказательство | Инструмент | Когда |
| --- | --- | --- |
| Открыть URL и показать ответ | Chrome MCP (`navigate` + `get_page_text`) | HTTP/WebUI сервис |
| Вызвать API endpoint, показать JSON | Chrome MCP (`javascript_tool` с `fetch()`) или `curl` | REST API / health |
| Скриншот состояния | Computer-use (`screenshot`) | Native UI |
| Запустить скрипт, показать stdout | Bash / Computer-use Terminal | CLI / pipeline |

**Hard fail:** verdict `worked` или `partially worked` для runtime-инцидента **без** хотя бы одного evidence из runtime (браузер, API-вызов, скриншот, stdout). File-only evidence **недостаточно**.

**При недоступности runtime:** явно зафиксировать `runtime недоступен: {причина}`, verdict = `did not work` или `partially worked` с блокером, **никогда** не `worked`.

**Связь:** этот пункт — enforcement зеркало `§2.5 Runtime Verification Gate` из [`hypothesis-gap-falsification`](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md). Различие: §2.5 — про falsification verdict, §7.0.1 — про redo verdict в RCA-цикле.

### 7.0.2. Visual Gate для UI/canvas redo (ОБЯЗАТЕЛЬНО)

**RCA-источник 2026-04-16:** агент после фикса UI-инцидента (`space-ui` ClientFilterDropdown + UniversalFunnelSection) проверил результат только через `preview_eval` JSON (`duplicates: []`, `funnelBcsCount: 15`), написал `worked`. Owner открыл глазами — canvas визуально пустой, zoom=3%, загрузка 12 минут. Redo верdict был ложный.

Для UI / canvas / layout инцидентов **`preview_eval`-only запрещён** как единственный evidence redo-цикла (hard fail). Обязательно:

1. **Screenshot в чат** — хотя бы 1 картинка после fix.
2. **Независимый субагент-тестировщик** (`ui-qa-engineer`, `code-reviewer` с vision, `design-art-director`) получает screenshot + промпт «посмотри глазами, опиши что видно, найди что сломано». Родительский RCA-агент не может быть сам себе QA для visual redo.
3. Subagent возвращает verdict; если partial/falsified — redo цикл повторяется.
4. **В отчёте RCA явно**: `evidence type: screenshot+subagent / DOM-queries / both`.

**Hard fail (добавлен):** UI/canvas/layout redo-verdict `worked` без screenshot и без subagent-verdict.

Каноны: AGENTS.md §QA Visual Gate, hypothesis-gap-falsification §2.5.1 Visual Gate, ui-qa-engineer SKILL.

### 7.1. Коммуникационные и visual deliverables: action-ready redo (ОБЯЗАТЕЛЬНО)

Если инцидент связан с:
- changelog,
- release notes,
- visual explanation,
- team/client announcement,
- rollout message,

то повторная доставка обязана быть не просто «более аккуратной», а **action-ready**.

Минимальный состав повторной доставки:
- `Было`
- `Стало`
- `Кто меняет поведение`
- `Что делать сейчас`
- `Что перестаём делать`
- `Proof`
- `Boundary`

Если пользователь попросил **inline Mermaid в чате**, а не browser HTML page:
- нельзя повторно отдавать один плотный Mermaid-граф, который требует zoom controls;
- redo обязан идти как `split-view`: `overview Mermaid` + `critical chain Mermaid` + краткая dependency table;
- каждый Mermaid должен держать одну мысль и не превышать читаемый размер chat-контейнера;
- если для чтения всё ещё нужен zoom, redo считается незавершённым.

Если после RCA visual page или сообщение всё ещё отвечает только на вопрос `что произошло`, а не `что менять`, redo считается незавершённым.

### 7.2. Что человеку делать дальше (ОБЯЗАТЕЛЬНО в финальном чате после RCA с тех- или процесс-фиксом)

**Когда:** финальный ответ пользователю после цикла `rca-incidents`, если остались шаги на стороне owner/оператора или нужно **явно** развести «агент делает сам» vs «только human».

**Где в чате:** сразу после блока `Protocol challenge (кратко)` (или эквивалента), перед `Run Evidence` / итоговым summary.

**Запрещено в заголовках таблиц:** сокращения вроде **OEU** без расшифровки в той же таблице — они повышают cognitive load у owner (исторический источник путаницы: старая редакция этого пункта называла шкалу «Owner Effort Units»).

**Связка с falsification / приоритетами:** если в том же ответе есть ссылки на `P0`, `G01`, `E01`, `pr-rick-*` из цикла [`hypothesis-gap-falsification` §0](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md), **всегда** дублировать подпись **` — {человекочитаемое имя}`** в той же ячейке или фразе. Голый код без подписи = тот же класс ошибки, что нерасшифрованный заголовок.

**Обязательная таблица — канон Owner effort digest (ровно 5 колонок, читаемые слова). Это единый SSOT формата для всех скилов: остальные скилы/агенты ссылаются сюда, не переопределяют состав колонок.**

| Priority (что за шаг) | next action | усилие человека (0–100, клик = 50+) | что агент может сделать сам | waste type |
| --- | --- | --- | --- | --- |

- **Priority (что за шаг)** — по макросу §0 «ID + имя»: `P0 — {суть шага}`, не голый `P0`. Если приоритет не задан — короткое имя шага.
- **усилие человека (0–100, клик = 50+)** — шкала A ниже. **Не путать** со шкалой B «остаточный glue (0–100)» из [`2-so-what-outcome-ladder`](mdc:.agents/skills/2-so-what-outcome-ladder/SKILL.md) (та измеряет glue на *использование* output, не клики owner на next action).

**Колонка `waste type`** (RCA-инъекция 7 May 2026, источник: Standard 1.5 §11 «7 видов потерь Lean»): какая из 7 потерь Lean доминирует в этой строке. Допустимые значения (single primary): `overproduction`, `motion`, `transportation`, `inventory`, `over-processing`, `waiting`, `defect`, `—` (если потерь нет — действие чисто-полезное). Это поле включает агрегатную аналитику по 30-дневному окну: `bd list --label waste:waiting --closed-since 30d` показывает доминирующий класс. Если один и тот же `waste type` встречается ≥ 2 раз за 30 дней — это сигнал на systemic design injection, а не point-fix.

**Шкала A «усилие человека» (клик = 50+)** — диапазон **0–100**, где **любой клик или действие owner = минимум 50 единиц**. Это шкала про оператора репо на `next action`; её нельзя смешивать со шкалой B «остаточный glue» (4 измерения × 0–3 из `2-so-what-outcome-ladder`, про усилие на *использование* output). Низкие значения 5/10/15 в этой колонке **запрещены** для строк, где owner кликает/решает — это рецидив (см. RCA 2026-05-28 ниже), ловится Stop-hook `owner_effort_scale_check.py`.

| усилие (0–100) | Класс шага | Примеры |
| --- | --- | --- |
| 0 | Агент делает всё сам, owner не нужен | правка репо, pytest, commit, grep, обновление скилла — owner не кликает |
| 50 | Один клик / одно действие owner | открыть ссылку, нажать approve, скопировать и вставить одну команду, открыть файл в IDE |
| 60 | Несколько кликов в одном контексте | Cursor Settings, merge conflict, починить сломанный env |
| 70 | Браузерная сессия под аккаунтом owner | логин Yandex/Google в нужном профиле, 2FA, UI-форма |
| 80 | Серия действий в разных системах | починить env + запустить + проверить в браузере |
| 90 | Координация с людьми | approve от другого человека, созвон, передача секрета |
| 100 | Полная ручная переработка | owner переделывает с нуля то, что агент не смог |

**Главное правило: любой клик owner = минимум 50.** Если `next action` требует хотя бы одного действия человека (открыть файл, нажать кнопку, скопировать команду, переключить контекст) — значение не может быть ниже 50. Ноль — только когда owner вообще ничего не делает.

**Формулы (в чате — словами, не аббревиатурами):**

- **Сумма подряд** = сложить «усилие человека» по строкам, если шаги выполняются последовательно.
- **Узкое место** = максимум «усилие человека» по строкам (самый тяжёлый шаг для человека).
- При 3+ строках указать **оба** числа, если это влияет на приоритет.

**Провал anti-legend — отдельный мини-словарь или легенда к заголовкам:** если агент добавляет **отдельный блок** «мини-словарь / glossary / расшифровка кодов», потому что **заголовки таблиц или колонок непонятны без приложения**, это **провал**: нужно **переписать заголовки и ячейки** так, чтобы смысл был **в той же строке** (полные названия критериев рядом с кодами в ячейке, не вынесенные в легенду). В digest усилий для следующего хода учитывай **+100** на переделку; первичная доставка с такой легендой вместо правки текста — **недопустимый компромисс**.

**Колонка «что агент может сделать сам»:** для каждой строки — `yes` / `partial` / `no` + одна короткая причина (credentials, только browser human, и т.д.).

**Если нечего поручать человеку:** одна строка **`Нет шагов для человека`** + причина (например «запрос был только анализ», «всё в merge»).

**Связь с KB:** для client-facing шагов «как использовать» допускается ссылка на **Effort** из [Standard 2.8](mdc:[standards .md]/5. rick.ai standards/2.8 rick.ai knowledge base standard 10 january 2026 0005 cet by ai assistant.md). Колонка «усилие человека» здесь про **оператора репо / workspace**, не про клиента.

**Скиллы-дополнения:** тот же блок обязан присутствовать в финальном delivery-сообщении по [`orchestrator-delivery-bundle`](mdc:.agents/skills/3-orchestrator-delivery-bundle/SKILL.md) (см. `Delivery contract`).

---

## Output Checklist (хорошая работа по инцидентам)

- [ ] Инцидент записан в `ai.incidents.md` с датой и описанием.
- [ ] **Блок «Контекст инцидента (для GEPA training data)» с 12 полями записан** (§0.3): owner_prompt_verbatim, chat_jtbd, trace_pointer, target_artifact_for_tuning, expected_delivery, actual_failure_mode, steering_verbatim, recurrence_count_14d, cognitive_load_symptom, scoring_rubric_pass_criteria (≥3), triggers_that_should_have_fired, skills_active_at_failure.
- [ ] **Trace file создан** в `[todo · incidents]/reasoning-logs/{date}-rca-{slug}.md` и `trace_pointer` в инциденте указывает на него (Standard 4.18).
- [ ] **target_artifact_for_tuning** указан конкретным path (не `unknown`); если несколько — основной первым, остальные перечислены.
- [ ] 5 почему разбор проведён и записан.
- [ ] Корневая причина сформулирована кратко.
- [ ] Построены и оценены альтернативные корневые причины (минимум 3 гипотезы).
- [ ] Зафиксирована причинно-следственная цепочка (`симптом -> ... -> корневая причина -> что меняем`).
- [ ] Составлена карта границ проблемы: что точно сломано, что точно не сломано, что ещё нужно проверить.
- [ ] Для инцидентов с `widget_id` добавлена Widget Evidence Card / Trust Pack (`human label`, `widget URL`, `group/folder`, `system_name`, `yaml path`, `app_id`, период, `groups/group_key`, `metric_key -> glossary_name -> ui_label`, 3-10 raw sample rows, при необходимости отдельный derived sample mapping).
- [ ] Для Rick data scenarios (`behavior / ecommerce / geo / demand`) добавлена Rick Taxonomy Card (`anchor widgets`, `behavior widgets`, `grouping catalog`, `event taxonomy`, `metric glossary`, `geo/session taxonomy`, `verification contract`).
- [ ] Указано место, где именно меняем процесс или правило (конкретная точка).
- [ ] Описано, что именно меняем, и правки внесены во все зависимые документы/скиллы/стандарты.
- [ ] После внесения изменений в записи инцидента заполнен post-change loop: `Решение`, `Что изменили`, `Как проверяем гипотезу`, `Когда вернуться к проверке`.
- [ ] **Стандарт 1.13 обновлён:** в таблице «Сводка по инцидентам» есть строка по этому инциденту; при новом типе гэпа — добавлена строка в «Типовые гэпы и проблемы».
- [ ] Статус инцидента обновлён в ai.incidents.md и в таблице 1.13 (In Progress → Hypothesis Testing после внедрения; при успехе — Hypothesis Confirmed после проверки).
- [ ] Выполнена **новая доставка** артефакта (дейли/отчёт/сообщение) — лучше первой попытки (читаемость, оформление, разделение «доставлено»/«написал в чат»).
- [ ] Новая попытка доставки выполнена **в том же ходе после изменения процесса**, если не было реального блокера.
- [ ] После RCA с остаточными шагами owner в чате есть блок **«Что человеку делать дальше»** (§7.2): таблица 5-кол. superset `Priority (что за шаг) | next action | усилие человека (0–100, клик = 50+) | что агент может сделать сам | waste type` + при необходимости **узкое место** и **сумма подряд** (словами, не аббревиатурами); применены **+50** за шаги «открыть файл/папку в IDE» и не использован **отдельный мини-словарь** вместо самодостаточных заголовков (**провал +100**). Значение < 50 в строке-клике = hard fail.
- [ ] После redo явно зафиксировано, сработала гипотеза или нет на текущем кейсе (`worked / partially worked / did not work`), а не только факт повторной доставки.
- [ ] Для runtime-инцидентов (сервис, API, UI, pipeline) redo verdict подтверждён **runtime evidence** (браузер, API-вызов, скриншот, stdout), а не только проверкой файлов (§7.0.1).
- [ ] В чате или в отчёте явно указано: что изменено по фидбеку и что доставлено повторно.
- [ ] При полном цикле по этому skill добавлена **одна строка** в таблицу `Append-only trace` в `[todo · incidents]/ai.incidents.md` (дата, `rca-incidents`, сжатый промт owner, целевые paths, 3–7 bullets reasoning); если файл недоступен — строка выведена в чат для ручной вставки.
- [ ] Для changelog / visual / announcement инцидентов повторная доставка содержит `action-ready change contract`, а не только recap.
- [ ] Для beads-first / project-governance инцидентов повторная доставка содержит `Graph from .beads`, а не generic `Goal Map`.
- [ ] Для beads-first / project-governance инцидентов повторная доставка semantic-first: не начинается с raw bead ids, а показывает branch -> blocker -> next output.

---

## Что значит «хорошая работа по инцидентам»

- **RCA:** корневая причина найдена через 5 почему, не «залатаны» только симптомы.
- **Что именно меняем:** точка вмешательства указана точно (процесс/скилл/правило/файл).
- **Цикл изменений:** правки внесены во все зависимые места; протокол «без гепов» соблюдён.
- **Финальный шаг:** задача по инциденту закрыта **новой доставкой** того же материала, с учётом ошибок первой попытки (оформление, читаемость, взгляд получателя), и эта доставка сделана сразу после изменения процесса, если нет реального блокера.

---

## Связанные стандарты и правила

- [AI Incident Standard 1.1]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.1 ai incident standard 14 may 2025 0505 cet by ai assistant.md)
- [Root Cause Analysis Standard 1.6]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.6 root cause analysis 14 may 2025 0700 cet by ai assistant.md)
- [Gap Theory Standard 1.5]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.5 gap theory standard 26 august 2025 2325 CET by ilya krasinsky.md)
- [AI Agent Typical Gaps and Prevention Standard 1.13]([standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.13 ai agent typical gaps and prevention standard 13 feb 2026 cet by ai assistant.md) — типовые гэпы и профилактика
- core-auto.mdc — TEAM-FACING MESSAGES, определения «доставили» / «написал в чат»
- [registry-daily-digest](mdc:.agents/skills/3-registry-daily-digest/SKILL.md) — шаг 4 (review перед отправкой), оформление дейли
- [review-artifact-for-client-readiness](mdc:.agents/skills/3-review-artifact-for-client-readiness/SKILL.md) — ревью текста с точки зрения получателя

---

## Output

1. Обновлённый `ai.incidents.md` с полной записью инцидента и статусом.
2. Изменения в зависимых документах (скиллы, правила, стандарты, KB).
3. Новая доставка артефакта (дейли/сообщение/отчёт) в чат или адресату — лучше первой попытки.
4. Краткое резюме в чат: что зафиксировано, где дизайн-инъекция, что изменено, куда доставлено повторно.

## Claim falsification before `repair complete` (MANDATORY)

- Если RCA утверждает, что `repair уже сделан`, `тикет уже хороший`, `skill уже работает`, `workflow уже зелёный`, нужно прогнать отдельный falsification-pass по skill
  [`hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md).
- Обязательный маршрут: `Проверяемая гипотеза -> Ожидаемое состояние -> Собранные факты -> Таблица разрывов -> Количество разрывов -> Вывод проверки гипотезы -> Новая рабочая гипотеза -> План действий`.
- Если остаётся хотя бы один core gap, писать `repair complete` запрещено.
- Если оказалось, что continuity, bead, script или support artifact были выдуманы, RCA обязан:
  - назвать старый claim ложным;
  - честно materialize отсутствующий слой;
  - повторить falsification-pass на новом состоянии.
- Минимальный acceptable proof в чате:
  - одна таблица `Expectation -> Reality -> Gap type -> Severity -> Verdict`;
  - один блок `Gap count`;
  - один явный verdict `confirmed / partially confirmed / falsified`.

## Unified Delivery Format (MANDATORY)

Финальная доставка по инциденту должна включать:

1. **Было/Стало**
- Было: симптом и провал первой доставки.
- Стало: конкретные изменения и итог повторной доставки.

2. **JTBD-сценарий**
- Когда, Роль, Хочет, Закрывает потребность, Делает, Мы хотим.

3. **Input / Output / Outcome Checklists**
- С фактическим прогоном (`[x]/[ ]`) на текущем инциденте.

4. **5 почему**
- Все 5 шагов обязаны быть видимы прямо в ответе пользователю.
- Нельзя заменять этот блок одной строкой `root cause` или ссылкой на `ai.incidents.md`.
- Каждый шаг писать как самодостаточную фразу с конкретикой по 5W+H: какой пользователь/агент или слой ошибся, что именно произошло, где именно это проявилось, на каком этапе это сорвало workflow, почему это было проблемой и как это подтверждено текущим кейсом.

5. **Где именно меняем процесс / Что меняем**
- Отдельно назвать точку изменения: в каком правиле, скилле, договорённости или материале меняется поведение.
- Отдельно назвать design changes: что именно переписано или добавлено.
- Для каждой точки инъекции явно указывать: какой слой меняем, какой exact section/file, какой симптом она закрывает в текущем кейсе, и каким механизмом изменение предотвратит повтор.

6. **Run Evidence**
- Какие команды/действия выполнены (обновления ai.incidents, 1.13, повторная доставка).
- PASS/FAIL проверки.
- Пути к изменённым артефактам.
- Каждая строка evidence должна отвечать на 5W+H без абстракций: какой command/tool, над каким файлом или surface, в какой момент, зачем запускался и какой observable result получен.

7. **Review Checkpoint**
- Если симптом был в том, что агент убежал в edits без понятного confirm-step, то same-turn redo обязан начинаться с короткого блока:
  - что делаю,
  - какой exact source использую,
  - зачем он нужен,
  - что из него пойдёт в output.

**FORBIDDEN:** закрывать RCA без блоков `5 почему` и `Где именно меняем процесс / Что меняем` в самом ответе пользователю.
**FORBIDDEN:** писать эти блоки summary-фразами без actor/place/stage/cause/mechanism detail.
**FORBIDDEN:** закрывать RCA без блока `Было/Стало` и без `Run Evidence`.
**FORBIDDEN:** писать `repair complete`, если не показан falsification-pass по схеме `ожидание -> реальность -> gap count`.
## Validation helper
- Contract check:
  - `python3 .agents/skills/2-rca-incidents/scripts/check_rca_skill_contract.py`
- Bad-ticket anti-patterns:
  - `.agents/skills/2-rca-incidents/references/bad-ticket-anti-patterns.md`
- Existing-ticket rewrite route:
  - `.agents/skills/1-ticket-review/SKILL.md`
- Hypothesis falsification protocol:
  - `.agents/skills/2-hypothesis-gap-falsification/SKILL.md`


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/` → duckdb). Узел «свернул не туда»: `heroes_harness/scripts/reasoning_log/graph.py --find-divergence`. Ручная markdown-таблица в чат — только если owner явно спросил «почему ты так решил». Полный протокол: `agent-reasoning-log/SKILL.md` (v2, RCA 2026-05-17).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick (включая TaskMaster и связанные стандарты Heroes Rickai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
