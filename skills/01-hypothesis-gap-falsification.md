---
name: hypothesis-gap-falsification
description: "Use when a claim, repair, rollout, RCA, ticket, skill, or workflow must be challenged against reality. Based on Gap Theory and expectation-versus-reality falsification. Output MUST include: таблица ожиданий (Expectations) with Next action if unmet + column усилие человека (0–100); таблица гепов (Gap table) with Next action + усилие человека for open/partial; Next-Action Digest after gap table (plain Russian headers, no unexplained abbreviations); every E/G/P/bead id shown as CODE — human-readable title in same cell (§0 macro); verdict; plan linked to digest priorities. Trigger phrases: \"проверь гипотезу\", \"опровергни\", \"ожидание vs реальность\", \"challenge this\", \"show the gap\", \"сколько тут гепов\"."
---

# Hypothesis Gap Falsification Skill

## Назначение

Этот skill нужен, когда уже есть гипотеза или claim вида:

- `мы уже починили`
- `тикет уже хороший`
- `skill уже работает`
- `workflow уже зелёный`
- `этот путь должен сработать`

и надо не защищать claim, а **построить ожидаемое состояние, столкнуть его с реальностью, посчитать гепы и вынести falsification verdict**.

---

## When to Use

- `проверь свою гипотезу`
- `опровергни`
- `challenge this`
- `ожидание vs реальность`
- `show the gap`
- `сколько здесь гепов`
- `покажи разрыв между expected и actual`

---

## Input checklist

- [ ] Понятен конкретный claim или гипотеза, которую нужно проверить.
- [ ] Понятно, в каких слоях claim должен подтверждаться:
  - repo files
  - `.beads` / tracker
  - runtime / logs
  - standards / incidents
  - external system
- [ ] Для claim можно сформулировать 3-7 наблюдаемых ожиданий, а не только абстрактную цель.
- [ ] Есть способ собрать факты из source-of-truth, а не из памяти агента.

---

## Core route

### 0. Макрос «ID + человекочитаемое имя» (ОБЯЗАТЕЛЬНО)

**Проблема:** строки вроде голого `P0`, `G01`, `E03`, `pr-rick-1234` без сказуемого — owner не должен держать в голове внутреннюю нумерацию агента.

**Правило:** в таблицах и в любом повторном упоминании в чате **код и подпись — в одной ячейке или одной фразе**, через **` — `** (пробел, длинное тире, пробел). Подпись = **3–15 слов по-русски** (или короткий title тикета), без нового алфавита.

| Сущность | Обязательный вид в чате / в ячейке | Откуда брать подпись |
| --- | --- | --- |
| **Gap ID** (`G01` …) | `G01 — {что за геп: что не сошлось / что сломано}` | из колонок Expectation / Reality |
| **Expectation ID** (`E01` …) | `E01 — {что именно проверяем одной фразой}` | из «Что должно быть истинно» |
| **Priority** (`P0` …) | `P0 — {суть шага: что делаем дальше}` | из Next action той же строки Digest |
| **Bead / тикет** (`pr-rick-42`, `pr-hero-7`, Linear key) | `pr-rick-42 — {title из .beads / bd show / issues.jsonl}` | readback из SoT; если title не прочитан — явно «прочитать `bd show pr-rick-42`» |
| **Closes gaps** (§7 plan) | не `G01, G02`, а **`G01 — …; G02 — …`** (краткие подписи повторить) | те же подписи, что в Gap table |

**В Reasoning Log** (и в любом аналоге): колонка **Gap found** — не голый `G01`, а **`G01 — краткое имя гепа`**.

**FORBIDDEN:** ячейка или фраза, где виден **только** `P0` / `G01` / `pr-rick-*` **без** ` — {подпись}` (исключение: техническая строка `Technical refs` в конце блока, где перечислены сырые id для копипаста — и то предпочтительно с title).

**Hard fail:** нарушение макроса §0 в любой из таблиц E / Gap / Next-Action Digest / §7 Plan — считать skill-output **неисполненным**.

### 1. Build expected state first

До проверки нужно выписать ожидания в верифицируемом виде.

Формат (обязательные колонки **Next action** и **усилие человека (0–100)** — без них таблица считается неполной; **не** использовать сокращение **OEU** и подобные в заголовках без расшифровки в той же таблице — см. `rca-incidents` §7.2):

| Expectation ID | Что должно быть истинно | Где это должно подтверждаться | **Next action if unmet** (что сделать, если факт не совпал) | **усилие человека (0–100)** (см. шкалу в `rca-incidents` §7.2; любой клик owner = минимум 50) | **Actor** (agent / owner / both) |
| --- | --- | --- | --- | --- | --- |
| E01 — все папки скиллов с префиксом `0-9-` | … | file / bead / log / API / screenshot | конкретный шаг, не «разобраться» | 0 (агент) / 50+ (owner кликает) | … |

Правила:

- Одно ожидание = один наблюдаемый факт.
- Не писать `всё хорошо` или `skill починен`.
- Хорошее ожидание: `в skill есть ровно один section X`, `ticket читается из same bead`, `checker script существует`.
- Колонка **Next action if unmet** заполняется **до** сбора фактов: это заранее заготовленный маршрут при провале E—иначе таблица декоративная.

### 2. Gather actual evidence

Собирать факты только из source-of-truth.

Порядок:

1. repo / file
2. tracker / `.beads`
3. logs / runtime
4. external system

Для каждого ожидания выписать:

- exact command / read action
- exact fact found
- whether evidence is direct or fallback

**Content-depth gate (hard fail):** «exact fact found» обязан содержать **конкретные значения из source-of-truth**: имена сценариев/записей, ID, CSS-значения в hex/rgba, имена тестов, числовые показатели, цитаты из кода. Пересказ («20 design tokens подтверждены», «62 теста прошли», «данные на месте») **без перечисления хотя бы 3–5 конкретных значений** из источника = hard fail. Если source содержит 33 записи — назвать минимум 5 с точными полями; если 62 теста — назвать минимум 5 имён тестов с тем, что именно каждый проверяет.

### 2.6. Copy-ready Review Gate (ОБЯЗАТЕЛЬНО для ticket/review/copy claims)

Если проверяемая гипотеза связана с claim:
- `ticket теперь reviewable`,
- `owner может скопировать в 1 клик`,
- `delivery не summary-only`,

то evidence обязан включать **полный fenced `md` block** целевого артефакта (например полного beads-ticket).  
Скриншот/пересказ/таблица без полного блока считаются недостаточным доказательством.

Правило:
1. Добавить отдельное ожидание в таблицу E: `E0N — есть полный fenced md block`.
2. Проверить фактом в чате/артефакте, что блок полный и единый.
3. При отсутствии блока создать gap: `G0N — нет copy-ready fenced md блока`.

### 2.5. Runtime Verification Gate (ОБЯЗАТЕЛЬНО для гипотез про сервисы, UI, API, pipeline)

**RCA-источник:** инцидент 2026-04-05 — агент собрал инфраструктуру LightRAG (скрипты, .env, health checker), заявил «всё готово», но ни разу не открыл `localhost:9621` и не вызвал API. Формально таблица ожиданий была заполнена, verdict выдан — но ни один fact не получен из runtime. Гипотеза «сервис работает» прошла все формальные шаги без единого обращения к сервису.

**Правило:** если проверяемая гипотеза содержит claim о работающем сервисе, доступном API, заполненном графе, загруженных данных, пройденном pipeline, открывающемся UI или любом **runtime-состоянии** — агент **обязан** выполнить хотя бы одну из следующих проверок **до** заполнения verdict:

| Проверка | Инструмент | Когда применять |
| --- | --- | --- |
| Открыть URL в браузере и прочитать ответ | Chrome MCP (`navigate` + `get_page_text` / `javascript_tool`) | Сервис с HTTP/WebUI |
| Вызвать API endpoint и показать JSON | Chrome MCP (`javascript_tool` с `fetch()`) или `curl` если доступен | REST API / health endpoint |
| Сделать скриншот состояния | Computer-use (`screenshot`) | UI native-приложения |
| Запустить скрипт и показать stdout | Bash tool / Computer-use Terminal | CLI-утилиты, pipeline |
| Перезапустить сервис на изменённых данных и показать diff | Любой из вышеперечисленных | Гипотеза «после fix данные изменились» |

**Hard fail:** verdict `confirmed` или `partially confirmed` для runtime-гипотезы **без** хотя бы одного evidence из runtime (браузер, API-вызов, скриншот, stdout). Evidence из repo/file/bead **недостаточно** для runtime-claim.

**Порядок при недоступности runtime:**

1. Попытаться запустить через доступные инструменты (Chrome MCP, computer-use, bash).
2. Если runtime недоступен (нет ключа, сервис не запущен, sandbox-ограничение) — **явно зафиксировать** в таблице ожиданий: `Reality: runtime недоступен, проверка невозможна`.
3. Verdict для таких строк = `open` или `falsified`, **никогда** не `confirmed`.
4. В Gap table обязательная строка: `G0N — runtime не проверен: {причина}`.

**Перезапуск на изменённых данных (revalidation):**

Если предыдущий агент или предыдущий прогон оставил артефакты (скрипты, конфиги, данные), а текущий прогон изменил эти артефакты — **недостаточно** проверить, что файлы на месте. Обязательно:

1. Перезапустить сервис / pipeline на **новых** данных.
2. Показать, что результат **отличается** от предыдущего прогона (или объяснить почему одинаков).
3. Без перезапуска verdict = `open`, не `confirmed`.

### 2.5.1. Visual Gate (ОБЯЗАТЕЛЬНО для UI/canvas/layout-гипотез)

**RCA-источник:** инцидент 2026-04-16 `<internal-component> <internal-component> + <internal-component>Section` — агент проверил UI только через `preview_eval` (JSON-числа: `duplicates: []`, `funnelBigfinCount: 15`, `persistedClient: '<client>-online'`), написал «confirmed, всё работает, ship-ready». Owner открыл `localhost:3013` глазами — **canvas визуально пустой**, zoom=0.03 (3%), загрузка ~12 минут, empty-widget Designcraft невидим физически. Гипотеза **falsified** по всем визуальным осям. Корневая причина: агент проверял **собственные данные своими же DOM-запросами** → самоподтверждающаяся петля, которая не видит zoom, overlapping, contrast, typography, layout shift.

**Правило:** для UI/UX/canvas/layout-гипотез `preview_eval`-only НЕДОПУСТИМ как evidence. Обязательно:

1. **Screenshot в чат** через `preview_screenshot` / Chrome MCP screenshot / computer-use — как минимум 1 картинка.
2. **Независимый субагент-тестировщик** (`ui-qa-engineer`, `design-art-director`, `code-reviewer` с vision) с явным промптом «посмотри screenshot глазами, опиши что видно, найди что сломано». Родительский агент **не может** быть сам себе QA для visual-гипотез.
3. **Screenshot попадает в prompt субагента** — если субагент не может описать картинку, verdict `confirmed` запрещён.
4. Если subagent возвращает partial/falsified — родительский агент НЕ пишет `confirmed`. Фикс → новый subagent-прогон → новый screenshot.

**Запрещённые паттерны self-review для UI (hard fail):**

- `document.querySelectorAll('[data-node-id]').length === 15` как proof «виджеты на canvas видны»;
- `getComputedStyle(el).opacity === '0.15'` как proof «dimming выглядит красиво»;
- `localStorage.getItem('selectedClient') === 'X'` как proof «persist работает для пользователя»;
- `const zoom = document.querySelector('.space-transform').style.transform` без visual проверки что zoom осмысленный для owner;
- «funnel widget rendered in DOM» без screenshot показывающего его в viewport со зримым контентом.

**Допустимые evidence для UI-claim:**

| Evidence type | Когда достаточно | Когда требуется subagent |
| --- | --- | --- |
| `screenshot + описание что видно + subagent verdict` | всегда OK | — |
| recorded video / gif + subagent analysis | всегда OK | — |
| Chrome MCP `read_page_text` + `screenshot` + subagent | всегда OK | — |
| `preview_eval` JSON only | **никогда** (hard fail для UI) | **всегда обязательно** |
| owner manual confirmation (скриншот от owner) | OK | — (owner = верификатор) |

**В QA review секции явная пометка:** `evidence type: screenshot + subagent / DOM-queries only / both`. Первые два допустимы, третий (DOM-only) = hard fail для UI-гипотезы.

**Hard fail (добавлен к §Hard fail conditions):** UI/canvas/layout-гипотеза с verdict `confirmed`/`partially confirmed` **без** screenshot в evidence И **без** subagent-verdict от независимого тестировщика.

### 2.7. User Simulation Gate (РЕКОМЕНДУЕТСЯ для продуктовых и UX-гипотез)

**Когда применять:** Если проверяемая гипотеза связана с продуктовым изменением, новым workflow, UX-улучшением, onboarding-фичей или agent-поведением — **до** gap table пройти пошаговую симуляцию пользователя.

**Каноническая job chain** из Standard 1.15 (`product-ops/ai-inception-delivery-process-ux-glue-effort-gap-discovery-system.md` §3):
0. Активирующее знание и сопротивление новому
1. Trigger — событие, которое запускает задачу
2. Setup — подготовка к выполнению
3. Execute — выполнение (cycle time)
4. Verify — проверка результата
5. Integrate — встраивание в существующий рабочий процесс
6. Recover — что делать при ошибке

**Формат User Simulation table:**

| Шаг (job chain) | Пользователь хочет | Пользователь ожидает | Факт (по spec/коду/runtime) | Трение | Тип разрыва |
| --- | --- | --- | --- | --- | --- |
| 0. Активирующее знание | {мотивация} | {что думает что будет} | {что реально происходит} | {где буксует} | knowledge / execution / integration |
| 1. Trigger | ... | ... | ... | ... | ... |

**Правила:**
- Каждая строка трения = кандидат в Gap table (шаг 3).
- Если трений 0 — явно написать: `Симуляция пройдена без трений. Confidence: X%`.
- Если spec/код недоступен — колонка «Факт» = `spec не проверен` и severity повышается.
- Не подменять симуляцию пересказом spec. Идти **от контекста пользователя**, не от документации.

### 3. Compute the gap table

Обязательная таблица (для строк с `verdict` = `open` или `partial` колонки **Next action** и **усилие человека (0–100)** обязательны; для `closed` можно `—` в Next action, если дубликат digest):

| Gap ID | Expectation | Reality | Gap type | Severity | Verdict | **Next action** (закрыть gap) | **усилие человека (0–100)** | **Actor** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G01 — битые ссылки в related-skills | … | … | knowledge / execution / feedback / integration | 1-5 | open / closed / partial | конкретный шаг или PR-граница | 0 (агент) / 50+ (owner кликает) | agent / owner / both |

Правила:

- `Gap ID` обязателен и **всегда с подписью** по макросу §0 (`G01 — …`).
- Если ожидание подтвердилось без оговорок, gap не создаётся.
- Если ожидание подтвердилось частично, verdict = `partial`.
- `Gap type` использовать из Gap Theory:
  - knowledge gap
  - execution gap
  - feedback gap
  - integration gap
- **Нельзя** оставлять `Next action` пустым для `open` / `partial`: иначе hard fail (см. ниже).

### 3.1 Next-Action Digest — обязательный блок после Gap table

Сразу после gap table (и до `Gap count`) вывести **одну** агрегирующую таблицу — dedup шагов из колонок Next action:

| Priority (Приоритет) | Next action | усилие человека (0–100) | Что агент может сделать сам | Что только owner |
| --- | --- | --- | --- | --- |
| P0 — починить ссылки в целевом SKILL | … | 0 (агент) / 50+ (owner кликает) | … | … |

- Если открытых/partial gap **нет**: строка **`Нет шагов для человека`** + одна фраза причины (не использовать «N/A» без пояснения).
- Смысл **сумма подряд** и **узкое место** — в `RCA, Root Cause Analysis — анализ корневых причин` incidents §7.2 (`.agents/skills/2-rca-incidents/SKILL.md`); здесь — то же **усилие человека**, не абстрактная «сложность».
- **Главное правило шкалы:** любой клик или действие owner = **минимум 50**. Ноль — только когда агент делает всё сам, owner не участвует. Провал **+100** — если вместо переписывания заголовков добавлен **отдельный мини-словарь/легенда**.

### 4. Count the gaps

После таблицы обязательно посчитать:

- `gaps_total`
- `gaps_open`
- `gaps_partial`
- `gaps_closed`
- `highest_severity`

Итоговый блок:

```text
Gap count
- total: N
- open: N
- partial: N
- closed: N
- highest severity: N/5
```

### 5. Falsification verdict

После gap table вынести только один verdict:

- `hypothesis confirmed`
- `hypothesis partially confirmed`
- `hypothesis falsified`

Правило:

- если есть хотя бы один gap, который ломает core claim, нельзя писать `confirmed`
- если core artifact отсутствует, verdict почти всегда `falsified`

### 5.1 Outcome Ladder Gate (ОБЯЗАТЕЛЬНО после verdict=confirmed или partially confirmed)

**RCA-источник:** инцидент 2026-04-17 — фальсификация прошла по E01-E08 (20/20 агентов с skills, validator 0 errors), verdict=`confirmed`. Но в ответе **потерян JTBD** владельца задачи и **не применены 5 so-what**. Owner в чате: «я уже потерял jtbd и outcome по итоговой задаче и 5 so what, похоже outcome designer не применялся». Корневая причина: `2-hypothesis-gap-falsification` закрывает гипотезу на уровне output (E01-E08 прошли), но не связывает output с бизнес-outcome. Фальсификация без outcome ladder = «мы доказали что technically работает», но не «зачем это было и что клиент/команда получают».

**Правило:** если verdict = `confirmed` или `partially confirmed`, агент **обязан** до закрытия ответа выполнить `2-so-what-outcome-ladder`:

1. **JTBD владельца задачи** — одна фраза «Когда {триггер}, хочу {action}, чтобы {outcome}»
2. **5 so-what (лестница)** — от output → N so-what → real outcome:
   - Output: что физически создано/изменилось (файлы, скрипты, коммиты)
   - 1-4 so-what: каждый уровень «И что с того?» до реального бизнес-outcome
   - 5 so-what: **real outcome** — что клиент/команда получают, какой метрикой измеряется
3. **Пересечение с gap table** — какие гепы блокируют какой уровень outcome

**Hard fail:** verdict=`confirmed` без применения §5.1 = фальсификация считается неисполненной. Agent должен немедленно применить `2-so-what-outcome-ladder` и переписать ответ.

Для verdict=`falsified` §5.1 не требуется — идём сразу в §6 new working hypothesis.

### 6. Generate a new working hypothesis

Если исходная гипотеза не подтверждена, сформулировать новую:

| New hypothesis | Why it explains the observed gaps better | What would falsify it next |
| --- | --- | --- |
| ... | ... | ... |

Новая гипотеза должна:

- объяснять максимум открытых gap'ов
- быть уже, чем исходный claim
- иметь явный следующий falsification test

### 7. Action plan (связан с §3.1)

После новой гипотезы **не дублировать** полностью таблицу из §3.1 — дать короткий нумерованный plan, который **ссылается** на Priority P0..Pn из Next-Action Digest:

| Step | Ref (Priority) | Action | Expected artifact | Closes gaps |
| --- | --- | --- | --- | --- |
| 1 | P0 — починить ссылки в целевом SKILL | … | … | G01 — битые ссылки; G02 — архив в changelog |

План должен быть:

- коротким
- artifact-first
- без fake subtask inflation
- каждый шаг traceable к строке **Next-Action Digest**

---

## Document Addressing Block (ОБЯЗАТЕЛЬНО, если falsification касается правок в файлах или больших вставок)

Перед тем как в чате написать «вставляю раздел», «добавляю §…», «через скрипт из‑за объёма» или любой аналог, показать блок **из четырёх строк**:

1. **Файл (repo path):** абсолютный или от корня репо, например `<internal-folder>/clients/<client>.pro/premiya-<client>-ILYA-review-and-Nadya-memo-2026-04-05.md`
2. **Секция как в файле:** точный заголовок Markdown (`## …` / `### …`), не только «§2.2» — например `### 2.2 Карточки «пруф + цитаты + логика баллов»`
3. **JTBD одной строкой:** зачем owner это читает / что решаем
4. **Пример соседнего артефакта** (если уместно): папка или 1 файл для контекста, например `premiya-<client>-linked-docs/…`

**FORBIDDEN в operator comms:**

- Только `§N.N` без path и без цитаты заголовка H2/H3 (коллизия с нумерацией в других скиллах/стандартах: у `rca-incidents` свой пункт 2.2 — Widget Evidence).
- Фразы «вставляю через скрипт из‑за объёма» **без** Document Addressing Block и без имени инструмента/команды, если скрипт реально используется.

---

## Execution trace + запись в `ai.incidents.md` (ОБЯЗАТЕЛЬНО при выполнении этого skill по запросу owner)

После построения gap table (или в том же ходе до финального ответа):

1. **В чат** — блок `### Execution trace` с датой (UTC или локальная с явной зоной), 3–7 bullets: *что решил → какой файл открыл/команду запустил → какой факт получил → какой gap выявлен*.
2. **В файл** `<internal-folder>/ai.incidents.md` — добавить **одну строку** в таблицу секции `## Append-only trace: skill runs & owner prompts (gap-hunting)`:
   - колонки: дата, `hypothesis-gap-falsification`, сжатый текст запроса owner (≤240 символов), целевой path + H2/H3 если есть, краткий reasoning log (можно через `; `).
3. **Опционально** — если выявлен **системный** долг без отдельного RCA (например «нужна автоматизация каждого промта»), одна строка в `<internal-folder>/ai.legacy.md` по контракту таблицы там; в trace можно сослаться `see ai.legacy`.

Если правка `ai.incidents.md` невозможна (read-only sandbox), явно написать в чат: блок trace всё равно обязателен + строка для ручной вставки owner.

---

## Hard fail conditions

Проверка провалена, если:

1. агент сравнивает ожидание с памятью, а не с фактом;
2. нет gap table;
3. нет gap count;
4. нет falsification verdict;
5. новая гипотеза не выдвинута после провала старой;
6. action plan не связан с конкретными gap IDs **с подписями** (макрос §0: `G01 — …`, `P0 — …`);
7. при запросе на trace/logging от owner нет блока `Execution trace` и нет попытки строки в `ai.incidents.md` (см. выше);
8. нет блока **Next-Action Digest** (§3.1) после gap table, или для любого gap с `open`/`partial` не заполнены **Next action** + **усилие человека (0–100)**;
9. таблица ожиданий (§1) без колонок **Next action if unmet** и **усилие человека (0–100)** (неполный формат);
10. есть **отдельный блок** «мини-словарь / glossary / легенда», чтобы объяснить заголовки E/Gap/Digest вместо переписанных **самодостаточных** заголовков и ячеек (провал anti-legend).
11. нарушен макрос **§0** (голый `P0` / `G01` / `E01` / `pr-rick-*` без ` — {человекочитаемое имя}` в таблицах E / Gap / Digest / §7 Plan или в Reasoning Log **Gap found**).
12. verdict `confirmed` / `partially confirmed` для **runtime-гипотезы** (сервис, API, UI, pipeline, граф данных) **без** хотя бы одного evidence из runtime — browser probe, API call, screenshot, stdout (§2.5 Runtime Verification Gate).
13. предыдущий прогон оставил артефакты, текущий их изменил, но **не перезапустил** сервис/pipeline на новых данных для сравнения (§2.5 revalidation).
14. ячейка «exact fact found» (§2) или «Reality» (§3 Gap table) содержит **только пересказ** («N тестов прошли», «design tokens на месте», «данные корректны») **без конкретных значений** из source-of-truth (имена, ID, hex-цвета, имена тестов, цитаты кода). Минимум 3–5 конкретных значений на ожидание (§2 Content-depth gate).
15. review/copy/ticket claim помечен как `confirmed` или `partially confirmed`, но в evidence отсутствует **полный fenced `md` block** целевого артефакта (§2.6 Copy-ready Review Gate).

---

## Output contract

Финальный ответ по skill обязан содержать в этом порядке:

1. `Проверяемая гипотеза`
2. `Ожидаемое состояние` (**таблица E** с колонками из §1, включая **Next action if unmet** и **усилие человека (0–100)**; **Expectation ID** по макросу §0)
3. `Собранные факты`
4. `Gap table` (с колонками **Next action**, **усилие человека (0–100)**, **Actor** для open/partial)
5. **`Next-Action Digest`** (§3.1) — обязательно; при нуле открытых gap — строка **«Нет шагов для человека»** + причина
6. `Gap count`
7. `Falsification verdict`
8. `Новая рабочая гипотеза`
9. `План действий` (§7, ссылки на Priority из digest)

Если claim связан с ticket / bead / skill / workflow, в `Собранные факты` обязаны быть абсолютные пути, exact ids и exact commands.

Если проверка касается markdown-документов с нумерацией «§», в `Собранные факты` обязательно: **path + H2/H3 заголовок**, а не только «§2.2».

### Как добиться повторяемости в каждом ответе агента (не магия)

Соблюдение этого контракта **обязательно** в workspace по цепочке:

1. **`AGENTS.md`** — пункты 9–10: мини gap-check + **Owner effort digest**; полный формат с таблицей ожиданий + digest — этот skill.
2. **`.cursor/rules/core-auto.mdc`** — таблица Skills: триггер «проверка гипотезы / всё исправлено» → этот skill.
3. Любой агент без доступа к правилам репо **не гарантирован** — источник истины для Cursor-агента: правила + явный запрос owner «по skill hypothesis-gap-falsification».

Итог: **каждый существенный ответ** в этом репо уже требует §9–10 в `AGENTS.md`; **полная** E+Gap+Digest таблица — при триггере skill или явном запросе на falsification.

---

## Стек «substantial delivery» (после `Deploy & PR review`, Ilya-facing)

Когда ответ попадает под обязательный формат доставки в `AGENTS.md` (есть `Design review`, `QA review`, `Deploy & PR review`), **после** блока `Deploy & PR review` и **перед** `Run Evidence` агент добавляет:

### 9. Hypothesis falsification (delivery self-check)

Не дублирует полный цикл п.1–8 сверху, если уже был отдельный falsification-pass по задаче; тогда — **сжатая** версия (строки таблицы — **с подписями**, макрос §0: если вводишь код строки гепа, добавь ` — {имя}`):

| Проверяемая гипотеза (доставка) | Ожидание | Факт | Δ |
| --- | --- | --- | --- |
| одна фраза: «что обещано owner» | конкретно | что в репо/чате видно | 0 или зазор |

- **Verdict:** `confirmed` | `partially confirmed` | `falsified`
- При `falsified` или `partially confirmed`: **новая рабочая гипотеза** (1–2 предложения) + **следующий шаг** (кто: AI vs owner)

### 10. Owner effort digest

Таблица из [`rca-incidents` §7.2](mdc:.agents/skills/2-rca-incidents/SKILL.md):

| next action | усилие человека (0–100) | что агент может сделать сам | что только owner |
| --- | --- | --- | --- |

- При необходимости: **узкое место** и **сумма подряд** (словами, как в `rca-incidents` §7.2).
- Если **нет** остаточных шагов для человека: строка **`Нет шагов для человека`** + причина (например «запрос был только анализ», «всё в merge»).

**Hard fail (substantial delivery):** финальный ответ с `Deploy & PR review`, но без п.9 **или** без п.10 (включая явную строку «нет шагов», если хвоста нет) — считается неполным.

---

## Inline anti-legend (отдельного скилла нет)

**FORBIDDEN:** выносить смысл таблицы в **отдельную легенду или мини-словарь** в конце сообщения, если заголовок колонки или ячейка без легенды нечитаемы.

**REQUIRED:**

- в ячейке с кодом (`К7`, `E01`, …) — **полное имя критерия рядом** в той же ячейке или в **человекочитаемом** заголовке колонки;
- для owner-facing Outcome — короткая таблица **без** нового алфавита (никаких GEU/Δ/осей как обязательного слоя для владельца);
- при claim «таблица читаемая»: проверка = **можно ли убрать приложение/легенду без потери смысла**; если нет — переписать строки, не добавлять словарь.

Связка: [`ticket-review-update` §5](mdc:.agents/skills/1-ticket-review-update/SKILL.md), [`review-artifact-for-client-readiness`](mdc:.agents/skills/3-review-artifact-for-client-readiness/SKILL.md), [`RCA incidents §7.2`](mdc:.agents/skills/2-rca-incidents/SKILL.md).

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

2. Записать строку в `ai.incidents.md` таблица.

3. При задачах > 3 ходов — сохранить лог в `<internal-folder>/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным.

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
