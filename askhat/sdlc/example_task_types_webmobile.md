---
title: "Пример: Task Types для enterprise web+mobile+backend SaaS"
version: v1
type: example
date_added: 2026-04-23
status: draft
---

# Пример — как могут выглядеть Task Types для классического enterprise приложения

> Это **пример**, не часть методики. Концептуальная проработка: что бы имело смысл специфицировать как «тип задачи» для типичного enterprise SaaS с web + mobile + backend.
>
> Цель — увидеть, как методический концепт «Task Type» приземляется в реальный продуктовый контекст. Что классифицируется чётко, что fuzzy, где границы.
>
> Читается за 20 минут.

---

## 1. Контекст приложения

Возьмём типичный B2B SaaS-продукт — для управления проектами в небольших командах. Похоже на Asana / Monday / ClickUp в упрощённой форме.

**Стек**:
- **Web**: React + TypeScript + Tailwind, монорепо
- **Mobile**: React Native (iOS + Android)
- **Backend**: Node.js + PostgreSQL + Redis, REST API
- **Интеграции**: Slack, Google Calendar, Stripe (биллинг), email-провайдер
- **Инфраструктура**: облако, CI/CD, observability

**Команды**: несколько, у каждой свой кусок продукта (workspace, projects, billing, integrations и т.д.).

---

## 2. Что нам нужно от классификации задач

Прежде чем определять «Task Types», полезно понять, **зачем** мы вообще классифицируем. Чем точнее ответ — тем меньше искушение классифицировать ради классификации.

Классификация нужна для трёх практических вещей:

**(1) Уровень автономии AI** — сколько свободы дать AI на этом виде работы. Менять цвет кнопки → AI может сам. Менять схему БД → нет, человек проверяет.

**(2) Какие проверки запускать** — для security-чувствительных задач включить дополнительные сканы; для cosmetic UI — только snapshot tests. Не делать всё для всего.

**(3) Какой контекст подтянуть** — для backend-изменения нужны API contracts; для UI — design system; для mobile — native-specific правила. Подтягивать релевантное, не всё.

Если классификация не помогает в этих трёх — она бесполезна. Это критерий «надо ли вообще выделять этот тип».

---

## 3. Схема: что описывает Task Type

Каждый «Task Type» — это запись с конкретными полями. Схема:

```yaml
task_type:
  name: "<краткое имя>"
  
  detection:
    # как AI понимает что задача относится к этому типу
    triggers: [<ключевые слова, паттерны>]
    file_signals: [<какие файлы обычно меняются>]
  
  blast_radius:
    users_affected: <small | medium | large>
    reversibility: <trivial | needs_release | hard | impossible>
    cross_team: <yes | no>
  
  default_autonomy: <A1 | A2 | A3 | A4 | A5>
  
  required_context:
    # что AI должен прочитать из KB перед работой
    - <ссылки на patterns / standards>
  
  required_gates:
    # что обязательно проверяется на выходе
    - <автоматические проверки>
    - <требования к human approval>
  
  typical_decomposition:
    # из чего обычно состоит работа этого типа
    - <конкретные подзадачи>
```

Это **схема**, не контент. Конкретные значения каждого поля заполняются под организацию.

---

## 4. Каталог Task Types для нашего приложения

Двенадцать типов, которые покрывают большинство ежедневной работы. Не претендую на полноту — это рабочая выборка.

### Type 1. UI cosmetic change

**Что**: визуальные правки без изменения поведения. Цвет, отступ, иконка, копирайт, anti-aliasing, размер шрифта.

**Триггеры**: «поменять стиль», «исправить отступ», «опечатка в тексте», «изменить цвет», «выровнять».

**Файлы**: `*.css`, `*.tsx` (только разметка/стили), copy-файлы, design-tokens.

**Blast radius**: small users (только видящие), trivial reversible.

**Default autonomy**: **A3** (PR + automatic checks → автомерж с уведомлением).

**Required context**: design tokens, copy guidelines.

**Required gates**: visual regression tests на затронутых компонентах, automated linting.

**Decomposition**: обычно 1 change.

---

### Type 2. UI feature (new screen / component)

**Что**: новый экран, модальное окно, новый компонент в существующих экранах.

**Триггеры**: «добавить страницу», «новая форма», «модал для…», «новый компонент».

**Файлы**: новые `*.tsx`, добавления в роутинг, возможно небольшие изменения backend (если нужен API).

**Blast radius**: medium users, easy reversible (rollback feature flag).

**Default autonomy**: **A2** (PR + human review).

**Required context**: design system, component library, routing patterns, accessibility rules.

**Required gates**: snapshot tests, accessibility tests, manual review on UX.

**Decomposition**: 
- Новый компонент / экран
- Подключение к роутингу
- Возможно: новый API endpoint (другой тип)
- Возможно: mobile-эквивалент (отдельная задача)

---

### Type 3. UX flow change

**Что**: изменение существующего флоу. Например: «при создании проекта сначала спрашиваем шаблон, потом название» (раньше наоборот).

**Триггеры**: «изменить флоу», «переделать как пользователь делает X», «изменить порядок шагов».

**Файлы**: state management, routing, multiple components.

**Blast radius**: large users (все, кто проходит флоу), needs release to reverse.

**Default autonomy**: **A2** (явно review продактом).

**Required context**: текущий флоу как documented, аналитика по конверсии (если есть), accessibility.

**Required gates**: end-to-end tests, аналитический smoke tests, A/B if applicable.

**Decomposition**: обычно несколько changes — изменения в нескольких компонентах + state + routes + tests.

---

### Type 4. API endpoint (new)

**Что**: новый REST endpoint в backend.

**Триггеры**: «новый эндпоинт для…», «нужно отдавать с сервера…», «добавить API для…».

**Файлы**: контроллер, сервис, schema validation, OpenAPI spec, тесты.

**Blast radius**: small (никто пока не использует), trivial reversible.

**Default autonomy**: **A2** (но если только AI добавляет endpoint и сразу его потребляет — близко к A3).

**Required context**: API conventions, error handling patterns, auth/authorization patterns, response format.

**Required gates**: contract tests, OpenAPI valid, security scan (auth check), performance budget.

**Decomposition**:
- Сам endpoint + handler
- Schema validation
- OpenAPI doc update
- Tests

---

### Type 5. API behavior change (existing endpoint)

**Что**: изменение того, как существующий endpoint работает. Поменять формат ответа, добавить поле, изменить логику.

**Триггеры**: «изменить ответ API», «добавить поле в response», «поменять валидацию».

**Файлы**: тот же endpoint файл, OpenAPI, миграция consumer'ов.

**Blast radius**: **большой** — все consumer'ы (web + mobile + integrations).

**Reversibility**: hard (нужна координация со всеми consumers).

**Default autonomy**: **A1 → A2** (зависит от breaking или не breaking).

**Required gates**: contract tests, breaking change detection, **уведомления всем consumers**, версионирование (если breaking).

**Decomposition**:
- Изменение endpoint
- Обновление OpenAPI
- Backwards compat handling
- Координация с consumers (зависимая работа в их зонах)

**Особенность**: это пример где **зависимости между changes критичны** — нельзя просто менять endpoint, не убедившись что consumers готовы.

---

### Type 6. Database schema migration (additive)

**Что**: добавление новой таблицы / нового поля. Без удаления существующего.

**Триггеры**: «добавить колонку», «новая таблица», «индекс на…».

**Файлы**: migration script, ORM models, индексы.

**Blast radius**: medium (вся БД), but reversible (можно дропнуть колонку).

**Default autonomy**: **A2** (review DBA или senior).

**Required gates**: migration dry-run, performance impact на больших таблицах, backup verification.

**Decomposition**:
- Migration script
- Model update
- Возможно: индекс
- Тесты на запросы

---

### Type 7. Database schema migration (destructive)

**Что**: удаление колонки/таблицы, переименование, сложная трансформация данных, миграция типа.

**Триггеры**: «удалить колонку», «переименовать поле», «изменить тип данных», «миграция данных».

**Blast radius**: large (вся БД), hard reversible (если данные потеряны — только из бэкапа).

**Default autonomy**: **A1** (только подсказывает, человек делает руками или после очень внимательного ревью).

**Required gates**: dry-run на staging, бэкап, план отката, человек ставит подпись, **обязательная phased rollout** (deprecate → migrate → remove).

**Decomposition**: сложная — phased migration, обычно несколько релизов.

---

### Type 8. Authentication / permission change

**Что**: изменение правил аутентификации, авторизации, ролей, permissions.

**Триггеры**: «изменить права», «добавить роль», «ограничить доступ», «новый permission».

**Файлы**: middleware, role definitions, RBAC config, tests.

**Blast radius**: large (security-critical), hard reversible (если ошиблись — могут получить доступ кто не должен).

**Default autonomy**: **A1** (human approval обязателен).

**Required gates**: security review (человек), специальные security tests, audit log запись.

**Decomposition**: middleware + role definition + tests + миграция существующих пользователей (если меняется default).

---

### Type 9. Third-party integration

**Что**: интеграция с новым внешним сервисом (Slack, Stripe, и т.п.) или существенное изменение существующей.

**Триггеры**: «интегрировать со…», «подключить…», «синхронизация с…».

**Файлы**: integration module, webhook handlers, секреты, env configs.

**Blast radius**: medium-large (зависит от того, насколько критично), reversibility варьирует.

**Default autonomy**: **A2** (review + manual testing с реальным внешним сервисом).

**Required gates**: integration tests против sandbox, secret management compliance, error handling and retry logic, rate limit handling.

**Decomposition**: сам клиент + конфиг + secrets + handlers + тесты + документация.

---

### Type 10. Mobile-only feature (push notifications, native API)

**Что**: что-то специфичное для iOS/Android — push, native APIs, deep linking, app store metadata.

**Триггеры**: «push-уведомление», «native API», «deep link», «App Store».

**Файлы**: native modules, mobile-specific config, push templates.

**Blast radius**: medium (только mobile users), reversibility варьирует.

**Default autonomy**: **A2** (mobile dev review).

**Required gates**: тесты на симуляторах, store guidelines compliance, certificate management.

**Decomposition**: native side + JS/TS bridge + config + tests + store metadata.

---

### Type 11. Bug fix (logic)

**Что**: фикс функционального бага. Не cosmetic.

**Триггеры**: «не работает», «баг в…», «должно быть X, но Y».

**Файлы**: зависит от бага.

**Blast radius**: зависит от того, где баг — но обычно small-medium.

**Default autonomy**: **A2** (PR + review + добавление regression test).

**Required gates**: **обязательный regression test** для этого бага (без него merge запрещён).

**Decomposition**: voссоздание (test, который красный) → fix → test зеленеет.

---

### Type 12. Critical incident hotfix

**Что**: срочный фикс прод-инцидента. Что-то лежит, теряются деньги, страдают пользователи.

**Триггеры**: алерт в системе, явная пометка PM «срочно».

**Default autonomy**: **A1 / специальный fast-track** — особый процесс, не обычный PR.

**Required gates**: post-fix audit (можно после деплоя, но обязательно), incident retrospective (триггер обновления rules в KB).

**Decomposition**: fix + smoke verify + retrospective.

**Особенность**: **исключение из общего workflow** — методика разрешает обходить обычные gates под ответственность on-call дежурного, с обязательным аудитом после.

---

## 5. Worked example — спека через декомпозицию

Возьмём реалистичный запрос продакта:

> «Давайте сделаем так, чтобы при добавлении задачи в проект можно было сразу прикрепить файл. И уведомление об этом должно приходить в Slack, если у workspace настроена интеграция. И на мобильнике это тоже должно работать».

Это **большой запрос**. Декомпозируется так:

| # | Work unit | Type | Зависимости | Default autonomy |
|---|---|---|---|---|
| 1 | Хранилище файлов: новая таблица `attachments` | Schema migration (additive) | — | A2 |
| 2 | API endpoint `POST /tasks/:id/attachments` | API endpoint (new) | depends on #1 | A2 |
| 3 | API endpoint `GET /tasks/:id/attachments` | API endpoint (new) | depends on #1 | A2 |
| 4 | UI компонент `AttachmentUploader` (web) | UI feature | depends on #2, #3 | A2 |
| 5 | Интеграция в существующий Task-form (web) | UX flow change | depends on #4 | A2 |
| 6 | Mobile: компонент аналог AttachmentUploader (RN) | Mobile-only feature + UI feature | depends on #2, #3 | A2 |
| 7 | Mobile: интеграция в task-form | UX flow change | depends on #6 | A2 |
| 8 | Slack notification: новый event "task_attachment_added" | Third-party integration (config) | depends on #2 | A2 |
| 9 | Permissions: только members workspace могут добавлять файлы | Auth/permission change | depends on #1 | A1 |
| 10 | E2E тесты на полный флоу | (testing) | depends on #4-#8 | A2 |

Уже понятно несколько вещей:
- **Сначала идёт #1 (миграция БД)** — без неё ничего не делается.
- **#2-#3 могут параллельно**.
- **#4-#5 (web) и #6-#7 (mobile) могут параллельно** — но обе ветки зависят от backend.
- **#9 (permissions)** — критичная зависимость, нужно решить **до** того как откроем эндпоинты, иначе security gap.
- **#10 в конце** — только когда всё доехало.

Но даже в этом простом плане видно: **это не один тип задачи**, это **набор разных типов с зависимостями**. И PM, говоря «приложите файл к задаче» — даже не подозревает что внутри 10 разных work units.

---

## 6. Что становится видно

Из этого упражнения несколько наблюдений:

**Чёткая классификация работает для атомарных work units**, не для крупных запросов. Запрос продакта — это несколько task types вместе. Декомпозиция даёт атомарность.

**Type 5 (API behavior change)** — самый болезненный, потому что зависит от внешних consumers. Здесь больше всего падает координационных проблем.

**Mobile** — обычно дублирует web по логике, но требует отдельных work units. Часто можно делать параллельно (если backend готов), но иногда нужно последовательно (если меняется UX flow).

**Permissions (Type 8)** — особенно опасна как «забытая зависимость». Можно сделать API без permissions, забыть, и в проде получить data leak. Поэтому для security-related work units важно обеспечивать что они в плане **есть и сделаны до** соответствующих API.

**Critical hotfix (Type 12)** — единственный тип, который явно **обходит** обычные gates. Это honest исключение, которое методика признаёт.

**Schema destructive (Type 7)** — единственный тип где autonomy реально низкая (A1) и phased rollout обязателен. Большинство остальных — A2/A3.

---

## 7. Где классификация ломается

Не каждая задача fits one type. Бывают edge cases:

**Случай 1: «Переделать флоу регистрации»** — это UX flow change + UI feature + API behavior change + auth change. Четыре типа в одной работе.

**Случай 2: «Добавить рекламу новой фичи в onboarding»** — это часто copy + UI cosmetic + analytics setup + feature flag. Может казаться что просто copy, но если требует трекинга и эксперимента — расширяется.

**Случай 3: «Подготовиться к чёрной пятнице»** — это performance optimization + capacity planning + monitoring setup + incident response readiness. Несколько типов и сильная межкомандная зависимость.

**Случай 4: «Эксперимент с новым алгоритмом сортировки»** — это новый код + A/B framework + analytics + feature flag. Этот может вообще не относиться ни к одному типу — это «эксперимент» как отдельная категория.

**Вывод**: нужен либо **тип «multi-type / cross-cutting»** для крупных работ (которые не декомпозируются в один проход), либо просто mechanism для работы с многотипными задачами через **последовательную декомпозицию** (PM + AI вместе разбирают).

---

## 8. Что это значит для методики

После прохождения этого упражнения концепция «Task Type Library» уточняется:

1. **Каталог типов имеет смысл составлять для атомарных work units**, не для пользовательских запросов.

2. **Декомпозиция — самостоятельный навык**. AI помогает, но в крупных запросах нужен PM/architect для проверки что декомпозиция полная и правильно зависимостями связана.

3. **Зависимости между work units — first-class артефакт**. Без них план не план. Современные инструменты (Claude Code, Cursor) умеют это в рамках одной сессии, но между сессиями это нужно фиксировать в репо.

4. **Каталог из 10-15 типов покрывает большинство** ежедневной работы для типичного enterprise приложения. Не нужно 50.

5. **Критерий полезности типа** — помогает ли он решить три задачи (автономия, проверки, контекст). Если тип одинаково обращается со всеми тремя как другой тип — их нужно объединить.

6. **Methodology специфицирует схему типа**, не сам каталог. Каталог наполняется в конкретной организации под её стек и продукт.

---

## 9. Что в нашей методике остаётся открытым

Этот пример обнажил несколько вопросов, на которые методика пока не отвечает:

- **Как кодифицируется зависимость между work units**? Список с indent? Граф? У нас нет ещё формата.

- **Что делать с «multi-type / cross-cutting» работами**? Особый тип? Pattern? Просто декомпозиция глубже?

- **Как обрабатывается incident hotfix как исключение**? Сейчас это просто «Type 12», но фактически это другой workflow (быстрее, скип некоторых gates, обязательный пост-аудит).

- **Эксперименты / A/B тесты** — отдельный класс работ или подтип?

Эти вопросы — кандидаты для следующей итерации.
