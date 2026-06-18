---
name: rca-incidents
description: "Use when an RCA incident needs a reviewable first screen, design injection, and same-turn redo. Based on the RCA standard and `ai.incidents.md` protocol. Logs to ai.incidents.md. Use when user says \"do RCA\", \"incident\", \"design-injection\", \"работа по инцидентам\", or says the first delivery or ticket was unreadable, unreviewable, or structurally wrong."
---

# RCA & Incidents Skill

## Назначение

**JTBD, Jobs To Be Done — задача, которую решает клиент:** Когда нужно провести анализ корневых причин, зафиксировать инцидент, найти место для дизайн-инъекции и пройти полный цикл изменений и исправлений — делать это по протоколу «без гепов», с явными input/output чеклистами и с финальной доставкой лучше первой попытки.

**Контекст:** Фидбек пользователя и работа по инциденту (дейли без review-artifact-for-client-readiness) запускаются через этот скилл: одна и та же последовательность шагов для любого инцидента.

---

## When to Use

- «Сделай RCA по этому сбою»
- «Зафиксируй инцидент», «запиши в ai.incidents.md»
- «Найди место для дизайн-инъекции»
- «Работа по инцидентам», «цикл изменений и исправлений»
- После фидбека пользователя о качестве доставки (дейли, отчёт и т.д.) — разобрать как инцидент и довести до «доставлено лучше, чем в первый раз»

---

## Input Checklist (перед началом)

- [ ] Есть описание симптома или фидбек пользователя (что пошло не так, что «не читается», что забыли).
- [ ] Открыт файл инцидентов: `<internal-folder>/ai.incidents.md`.
- [ ] Понятен **канон записи в журнал**: одна секция `## DD MMM YYYY` на календарный день, внутри дня — **одна** markdown-таблица на все строки этого дня (trace и полный RCA — одна ширина колонок); см. Standard 1.1 § «Канон разметки `ai.incidents.md`». При **реструктуризации всего файла** или смене заголовка таблицы — не массово с первого прохода: протокол S0–S7 в `.agents/skills/1-next/SKILL.md` § «Шаг за шагом» + falsification по `.agents/skills/2-hypothesis-gap-falsification/SKILL.md`.
- [ ] Выполнен precedent scan по `ai.incidents.md`: найдены похожие инциденты, прошлые design injections, reusable verdicts или честно написано, что похожих кейсов не найдено.
- [ ] Прочитаны стандарты: [AI Incident Standard 1.1](<standard-ref>), [RCA Standard 1.6](<standard-ref>), при необходимости [Gap Theory 1.5](<standard-ref>).
- [ ] Понятно, какой артефакт/доставка была «первой попыткой» (дейли, отчёт, сообщение в чат и т.д.).
- [ ] Проверено, не работал ли инцидент в multi-agent режиме (2+ агентов в одном workspace / branch / worktree).
- [ ] Проверено, виден ли lifecycle проекта в `todo.md`, `.beads` и обязательном временном `duckdb` слое.
- [ ] Если инцидент связан с live workflow / automation, доказан ли business context target: audience, sender, recipients, storage, JTBD этого flow.

---

## Instructions (протокол без гепов)

### 0. Precedent scan + visible RCA artifact in chat (ОБЯЗАТЕЛЬНО)

- До или вместе с file updates RCA обязан показать в чате reviewable RCA artifact, а не только line refs / summary.
- Минимальный chat artifact:
  - `Текущий тикет` — если уже есть existing bead / ticket / issue, показать именно его целиком в fenced `md` code block.
  - `Similar incidents` — 1-5 похожих записей из `ai.incidents.md` с коротким объяснением, что именно переиспользуем.
  - `Past design injections reused` — какие старые injections подходят к текущему кейсу.
  - `Hypotheses table` — primary + alternatives с verdict.
  - `Primary chain / secondary chain`.
  - `Chosen design injection`.
- Если похожих инцидентов нет, агент обязан написать это явно: `No similar incidents found in ai.incidents.md after scan`.
- Если в этом же ходе менялись файлы, в чат нужно вывести не только paths, но и **exact changed excerpts / change-pack**:
  - `before -> after`
  - или короткие цитаты изменённых строк / блоков
  - или table `request -> change -> rationale -> artifact`
- Запрещено считать RCA reviewable, если в чат ушли только:
  - ссылки на файлы,
  - line refs,
  - summary без hypotheses/precedents,
  - заявление `всё исправлено` без видимого artifact.

### 0.1. Existing ticket first (ОБЯЗАТЕЛЬНО)

- Если incident уже привязан к existing bead / ticket / issue, RCA обязан продолжать **этот же** artifact.
- Synthetic `local-*` ticket или shadow replacement card запрещены.
- В первом большом RCA-ответе блок `Текущий тикет` идёт первым и отвечает на 4 вопроса:
  - какой artifact главный;
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
### 0.2. Rewrite gate for bad existing ticket/card (ОБЯЗАТЕЛЬНО)
- Если owner пишет, что existing ticket / bead `плохой`, `не по стандарту`, `не проходит review`, RCA не имеет права использовать его как будто continuity уже достаточна.
- Обязательный порядок:
  1. назвать existing artifact;
  2. кратко показать standard violations;
  3. same-turn запустить rewrite-route по `ticket_review` и [`ticket-review-update`](.agents/skills/1-ticket-review-update/SKILL.md);
  4. проверить readback из source-of-truth;
  5. только потом снова использовать его как `Текущий тикет`.
- Запрещено:
  - лечить только chat delivery вокруг плохой карточки;
  - выдавать список section labels за proof качества;
  - создавать новый substitute ticket вместо rewrite same ticket.
- Good-ticket proof: в чате показана **переписанная та же карточка целиком** в fenced `md` block, сразу после этого выполнен `ticket-review-update` writeback, а затем показан readback proof из source-of-truth в fenced `text/json` block.

### 1. Зафиксировать инцидент

- Добавить запись в `ai.incidents.md` (в начало файла).
- Формат: дата, краткое описание, симптом, при необходимости гепы (Gap Theory): процессный, JTBD, контекстный.

### 2. RCA — 5 почему и корневая причина

- Провести разбор «5 почему» до корневой причины (не останавливаться на симптоме).
- Записать корневую причину в инцидент (кратко, до ~100 символов).

### 2.1. Альтернативные корневые причины и причинная цепочка (ОБЯЗАТЕЛЬНО)

- Построить минимум 3 альтернативные гипотезы корневой причины (не только primary).
- Для каждой гипотезы выписать:
  - подтверждающие факты,
  - опровергающие факты,
  - оценку вероятности (0.0-1.0),
  - impact (1-5),
  - вердикт (`accepted` / `rejected` / `needs-data`).
- Формат таблицы:

| Гипотеза | Факты "за" | Факты "против" | Вероятность | Impact | Вердикт |
| --- | --- | --- | --- | --- | --- |
| [альтернатива #1] | [...] | [...] | [0.00-1.00] | [1-5] | accepted/rejected/needs-data |

- Построить причинно-следственную цепочку (chain), чтобы не терять промежуточные причины:
  - `Симптом -> Промежуточная причина -> Процессный дефект -> Корневая причина -> Design Injection`.
- Если есть несколько веток, явно выделить primary chain и secondary chain.
- Добавить `broken / not broken` карту по зонам влияния:
  - что сломано точно,
  - что не сломано (чтобы не чинить лишнее),
  - какие зоны требуют дополнительной валидации.
- Эти гипотезы нельзя держать только во внутреннем reasoning или только в `ai.incidents.md`: краткая hypothesis table обязана появиться и в чате.

### 2.1.5.1. Opaque jargon / abbreviations in agent chat (ОБЯЗАТЕЛЬНО, если owner жалуется на «непонятные сокращения» или рост cognitive load)

**Симптом:** В ответе агента появляются аббревиатуры без расшифровки в том же сообщении (пример исторического долга: **OEU** = введено в §7.2 этого скилла как «Owner Effort Units» — для owner это шум).

**Root cause (типовой):** Скилл/стандарт ввёл метку для краткости внутри команды; агент скопировал метку в operator-facing таблицу без колонки «что это значит».

**Где искать источник «говна» (порядок):**

1. **Репо:** `rg` по `.agents/skills/`, `AGENTS.md`, `<standard-ref>).
2. **Трассировки в репо:** `<internal-folder>/ai.incidents.md` → секция **Append-only trace**; при наличии — `<internal-folder>/reasoning-logs/*.md`.
3. **Логи Cursor (размышления / tool / MCP):** macOS — `~/Library/Application Support/Cursor/logs/` (см. [read-verify-logs-output](mdc:.agents/skills/2-read-verify-logs-output/SKILL.md)); искать строки с тем же токеном рядом с решением агента.

**Design injection (обязательная):**

- В **owner-facing** таблицах: **не вводить** новые аббревиатуры; для шкалы усилий использовать колонку **`усилие человека (0–100)`** (или полное предложение в заголовке), а не сокращения вроде исторического OEU.
- Если аббревиатура неизбежна (имена API): одна строка glossary **в той же таблице**.
- Обновить источник в скилле/правиле, откуда агент скопировал жаргон; одна строка в **Сводка по инцидентам** Standard 1.13 при системном паттерне.

### 2.1.5. Similar incidents and previous design injections (ОБЯЗАТЕЛЬНО)

- При каждом RCA сделать поиск по `ai.incidents.md` на:
  - похожий symptom,
  - похожий process failure,
  - похожий delivery failure,
  - похожую design injection.
- В чате и в incident entry выписать:
  - `Similar incidents considered`
  - `Which old injections still apply`
  - `Why old injection was not enough`
  - `What new injection is added now`
- Если старый инцидент уже содержал подходящую injection, а текущий сбой всё равно произошёл, RCA обязан отдельно ответить:
  - почему injection не была enforced,
  - в каком skill/rule/flow enforcement развалился,
  - что именно меняем теперь: canon, router, validator, or delivery contract.

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

### 2.2. Widget Evidence Card для инцидентов <internal-component> (ОБЯЗАТЕЛЬНО при `widget_id`)

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

### 3. Место для дизайн-инъекции

- Указать **конкретную точку** в процессе/скилле/правиле/коде, где нужно изменить поведение (не более ~50 символов в формулировке).
- Примеры: «Этап перед отправкой дейли в чат (скилл registry-daily-digest)», «Правило core-auto: секция TEAM-FACING MESSAGES».

### 4. Дизайн изменения

- Описать конкретные изменения (что добавить/изменить в скилле, правиле, стандарте, скрипте), адресующие корневую причину.
- Зафиксировать в инциденте блок «Дизайн изменения».

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
- **Стандарт 1.13** ([AI Agent Typical Gaps and Prevention](<standard-ref>)) — обновить обязательно:
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
- **REQUIRED:** использовать **Document Addressing Block** из skill [`hypothesis-gap-falsification`](.agents/skills/2-hypothesis-gap-falsification/SKILL.md) для любых «я сейчас вставляю / генерю большой блок в документ».

### 7. Исправить задачу и сделать новую доставку

- **Обязательно:** не заканчивать только «исправлениями в документах». Нужна **новая доставка** того же артефакта (дейли, отчёт, сообщение в чат) — уже с учётом ошибок и косяков первой попытки.
- **Immediate redo contract:** если пользователь попросил `RCA`, `зафиксируй инцидент`, `сделай дизайн-инъекцию`, агент в этом же ходе обязан после внесения design changes **сразу попробовать заново выполнить исходную задачу / повторить прошлую доставку**, а не останавливаться на docs-only pass.
- Если redo в этом же ходе невозможен, агент обязан явно показать:
  - какой exact blocker мешает redo сейчас,
  - почему его нельзя обойти разумным способом,
  - какой exact next action остался.
- Порядок: черновик → review-artifact-for-client-readiness (если применимо) → правки → отправка/публикация.
- Критерий: получатель может прочитать и понять без внутреннего контекста; заголовки выделены (полужирные в чате); «доставлено» vs «написал в чат» разделены, если речь про дейли.
- Если сбой произошёл в `beads-first / project-governance / registry` deliverable, повторная доставка обязана содержать отдельный блок `Graph from .beads` с источником графа (`bd`, `beads.db`, `issues.jsonl`, fallback).
  - Human-facing contract: сначала смысловые ветки, активные блокеры и следующие outputs.
  - Raw bead ids допустимы только как secondary technical refs, а не как первая строка каждого узла.
- В summary явно перечислить `Skills used`, и если был применён этот протокол, писать `rca-incidents` первым.
- Если исходный фидбек был про reviewability (`не вижу`, `не могу сделать review`, `покажи изменения`, `где гипотезы`, `где примеры`), новая доставка обязана содержать:
  - exact changed excerpts,
  - visible hypotheses,
  - similar incidents,
  - reused design injections,
  а не только итоговый список changed files.
- Если этот же фидбек был про плохой ticket/bead, новая доставка обязана в том же ходе содержать full rewritten ticket в fenced `md` block, diff-layer `Source wording vs Agent wording` и `ticket-review-update` readback proof.

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

**RCA-источник 2026-04-16:** агент после фикса UI-инцидента (`<internal-component>` <internal-component> + <internal-component>Section) проверил результат только через `preview_eval` JSON (`duplicates: []`, `funnelBigfinCount: 15`), написал `worked`. Owner открыл глазами — canvas визуально пустой, zoom=3%, загрузка 12 минут. Redo верdict был ложный.

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

### 7.2. Next-Action Digest — что делает человек дальше (ОБЯЗАТЕЛЬНО в финальном чате после RCA с тех- или процесс-фиксом)

**Когда:** финальный ответ пользователю после цикла `rca-incidents`, если остались шаги на стороне owner/оператора или нужно **явно** развести «агент делает сам» vs «только human».

**Где в чате:** сразу после блока `Protocol challenge (кратко)` (или эквивалента), перед `Run Evidence` / итоговым summary.

**Запрещено в заголовках таблиц:** сокращения вроде **OEU** без расшифровки в той же таблице — они повышают cognitive load у owner (исторический источник путаницы: старая редакция этого пункта называла шкалу «Owner Effort Units»).

**Связка с falsification / приоритетами:** если в том же ответе есть ссылки на `P0`, `G01`, `E01`, `pr-rick-*` из цикла [`hypothesis-gap-falsification` §0](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md), **всегда** дублировать подпись **` — {человекочитаемое имя}`** в той же ячейке или фразе. Голый код без подписи = тот же класс ошибки, что нерасшифрованный заголовок.

**Обязательная таблица (ровно 3 колонки, читаемые слова):**

| next action | усилие человека (0–100) | что агент может сделать сам |
| --- | --- | --- |

**Шкала «усилие человека»** — диапазон **0–100**, где **любой клик или действие owner = минимум 50 единиц**:

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

**Связь с KB:** для client-facing шагов «как использовать» допускается ссылка на **Effort** из [Standard 2.8](mdc:<standard-ref>). Колонка «усилие человека» здесь про **оператора репо / workspace**, не про клиента.

**Скиллы-дополнения:** тот же блок обязан присутствовать в финальном delivery-сообщении по [`orchestrator-delivery-bundle`](mdc:.agents/skills/3-orchestrator-delivery-bundle/SKILL.md) (см. `Delivery contract`).

---

## Output Checklist (хорошая работа по инцидентам)

- [ ] Инцидент записан в `ai.incidents.md` с датой и описанием.
- [ ] 5 почему разбор проведён и записан.
- [ ] Корневая причина сформулирована кратко.
- [ ] Построены и оценены альтернативные корневые причины (минимум 3 гипотезы).
- [ ] Зафиксирована причинно-следственная цепочка (`симптом -> ... -> root cause -> design injection`).
- [ ] Составлена карта `broken / not broken` по blast radius.
- [ ] Для инцидентов с `widget_id` добавлена Widget Evidence Card / Trust Pack (`human label`, `widget URL`, `group/folder`, `system_name`, `yaml path`, `app_id`, период, `groups/group_key`, `metric_key -> glossary_name -> ui_label`, 3-10 raw sample rows, при необходимости отдельный derived sample mapping).
- [ ] Для Rick data scenarios (`behavior / ecommerce / geo / demand`) добавлена Rick Taxonomy Card (`anchor widgets`, `behavior widgets`, `grouping catalog`, `event taxonomy`, `metric glossary`, `geo/session taxonomy`, `verification contract`).
- [ ] Указано место для дизайн-инъекции (конкретная точка).
- [ ] Описаны дизайн-изменения и они внесены во все зависимые документы/скиллы/стандарты.
- [ ] После внесения изменений в записи инцидента заполнен post-change loop: `Решение`, `Что изменили`, `Как проверяем гипотезу`, `Когда вернуться к проверке`.
- [ ] **Стандарт 1.13 обновлён:** в таблице «Сводка по инцидентам» есть строка по этому инциденту; при новом типе гэпа — добавлена строка в «Типовые гэпы и проблемы».
- [ ] Статус инцидента обновлён в ai.incidents.md и в таблице 1.13 (In Progress → Hypothesis Testing после внедрения; при успехе — Hypothesis Confirmed после проверки).
- [ ] Выполнена **новая доставка** артефакта (дейли/отчёт/сообщение) — лучше первой попытки (читаемость, оформление, разделение «доставлено»/«написал в чат»).
- [ ] New delivery / redo выполнены **в том же ходе после design injection**, если не было реального blocker.
- [ ] После RCA с остаточными шагами owner в чате есть **Next-Action Digest** (§7.2): таблица `next action | усилие человека (0–100) | что агент может сделать сам` + при необходимости **узкое место** и **сумма подряд** (словами, не аббревиатурами); применены **+50** за шаги «открыть файл/папку в IDE» и не использован **отдельный мини-словарь** вместо самодостаточных заголовков (**провал +100**).
- [ ] После redo явно зафиксировано, сработала гипотеза или нет на текущем кейсе (`worked / partially worked / did not work`), а не только факт повторной доставки.
- [ ] Для runtime-инцидентов (сервис, API, UI, pipeline) redo verdict подтверждён **runtime evidence** (браузер, API-вызов, скриншот, stdout), а не только проверкой файлов (§7.0.1).
- [ ] В чате или в отчёте явно указано: что изменено по фидбеку и что доставлено повторно.
- [ ] При полном цикле по этому skill добавлена **одна строка** в таблицу `Append-only trace` в `<internal-folder>/ai.incidents.md` (дата, `rca-incidents`, сжатый промт owner, целевые paths, 3–7 bullets reasoning); если файл недоступен — строка выведена в чат для ручной вставки.
- [ ] Для changelog / visual / announcement инцидентов повторная доставка содержит `action-ready change contract`, а не только recap.
- [ ] Для beads-first / project-governance инцидентов повторная доставка содержит `Graph from .beads`, а не generic `Goal Map`.
- [ ] Для beads-first / project-governance инцидентов повторная доставка semantic-first: не начинается с raw bead ids, а показывает branch -> blocker -> next output.

---

## Что значит «хорошая работа по инцидентам»

- **RCA:** корневая причина найдена через 5 почему, не «залатаны» только симптомы.
- **Дизайн-инъекция:** точка вмешательства указана точно (процесс/скилл/правило/файл).
- **Цикл изменений:** правки внесены во все зависимые места; протокол «без гепов» соблюдён.
- **Финальный шаг:** задача по инциденту закрыта **новой доставкой** того же артефакта, с учётом ошибок первой попытки (оформление, читаемость, client-perspective), и эта доставка сделана сразу после design injection, если нет реального blocker.

---

## Связанные стандарты и правила

- [AI Incident Standard 1.1](<standard-ref>)
- [Root Cause Analysis Standard 1.6](<standard-ref>)
- [Gap Theory Standard 1.5](<standard-ref>)
- [AI Agent Typical Gaps and Prevention Standard 1.13](<standard-ref>) — типовые гэпы и профилактика
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
  [`hypothesis-gap-falsification`](.agents/skills/2-hypothesis-gap-falsification/SKILL.md).
- Обязательный маршрут: `Проверяемая гипотеза -> Ожидаемое состояние -> Собранные факты -> Gap table -> Gap count -> Falsification verdict -> Новая рабочая гипотеза -> План действий`.
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

5. **Где design injection / Что меняем**
- Отдельно назвать точку инъекции: в каком contract / skill / rule / artifact меняется поведение.
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

**FORBIDDEN:** закрывать RCA без блоков `5 почему` и `Где design injection / Что меняем` в самом ответе пользователю.
**FORBIDDEN:** писать эти блоки summary-фразами без actor/place/stage/cause/mechanism detail.
**FORBIDDEN:** закрывать RCA без блока `Было/Стало` и без `Run Evidence`.
**FORBIDDEN:** писать `repair complete`, если не показан falsification-pass по схеме `ожидание -> реальность -> gap count`.
## Validation helper
- Contract check:
  - `python3 .agents/skills/2-rca-incidents/scripts/check_rca_skill_contract.py`
- Bad-ticket anti-patterns:
  - `.agents/skills/2-rca-incidents/references/bad-ticket-anti-patterns.md`
- Existing-ticket rewrite route:
  - `.agents/skills/1-ticket-review-update/SKILL.md`
- Hypothesis falsification protocol:
  - `.agents/skills/2-hypothesis-gap-falsification/SKILL.md`


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)

При каждом исполнении этого скилла агент ОБЯЗАН:

1. **Вести reasoning log в чате** — таблица решений с evidence, gaps и blocking instructions:

```markdown
### Reasoning Log — [дата UTC]
| # | Decision | Evidence source | Gap found | Blocking instruction | Owner value |
|---|----------|-----------------|-----------|---------------------|-------------|
```

**§0 macro (hard fail):** колонка **Gap found** — не голый `G01`, а **`G01 — краткое имя гепа`**. Любой ID (`P0`, `G01`, `E01`, `pr-rick-*`) без ` — {человекочитаемое имя}` = hard fail. См. `AGENTS.md` секция «Plain language» и `CLAUDE.md` §0.

2. **Записать строку в `ai.incidents.md`** — таблица `## Append-only trace`:

```
| {UTC date} | {skill_name} | {owner prompt ≤240} | {steering: yes/no} | {target artifact} | {reasoning bullets} | {blocking_instruction} |
```

3. **При задачах > 3 ходов** — сохранить лог в `<internal-folder>/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным. См. протокол **agent-reasoning-log** в `AGENTS.md` (список навыков).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
