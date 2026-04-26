# 📘 AI Management Workflow Standard

<!-- 🔒 PROTECTED SECTION: BEGIN -->
type: standard
standard_id: 1.16
logical_id: standard:ai_management_workflow
updated: 16 March 2026, 09:10 CET by Codex Agent by Ilya Krasinsky
previous version: 1.0, 10 March 2026, 19:55 CET by Codex Agent by Ilya Krasinsky
based on: [Registry Standard](abstract://standard:registry_standard), [AI Inception-Delivery Process UX Glue Effort Gap Discovery System Standard](product-ops/ai-inception-delivery-process-ux-glue-effort-gap-discovery-system.md), [Outcome Zero-Gap JTBD Transfer Standard](abstract://standard:outcome_zero_gap_transfer), [Task Lead Time · CFD Metrics Standard](abstract://standard:task_leadtime_cfd_metrics), [Changelog Standard](abstract://standard:changelog_standard), [release notes standard](abstract://standard:release_notes_standard), [HelpDesk Integration Standard](abstract://standard:helpdesk_integration_standard)
integrated: client workspaces like `galaxypets-management`, `rfl.pro`, shared `heroes-pulseai-workspace`
version: 1.1
status: Active
tags: standard, ai-management, workflow, client-workspace, portfolio, beads, jira, linear, telegram, release-management
<!-- 🔒 PROTECTED SECTION: END -->

---

## 🛡️ Лицензия и условия использования

**Все права защищены.** Данный документ является интеллектуальной собственностью Ильи Красинского и не может быть скопирован, использован или адаптирован в любых целях без предварительного письменного согласия автора. Авторские права защищены законодательством США.

**Magic Rick Inc.**, зарегистрированная в штате Делавэр (США), действует от имени автора в целях защиты его интеллектуальной собственности и будет преследовать любые нарушения в соответствии с законодательством США.

---

## 🎯 Цель документа

Зафиксировать единый порядок внедрения `AI management` в клиентские и внутренние workspace-репозитории. Стандарт отвечает на вопрос не “как настроить одну папку”, а “как перевести компанию на operating model, где discovery, portfolio, execution, ticket bridge, release activation и durable knowledge работают как одна система”.

Этот стандарт нужен для rollout в клиентах вроде `rfl.pro`, но не ограничен одним клиентом. Его задача — дать один воспроизводимый workflow, который можно запускать в разных repo, не копируя каждый раз новую process-версию из `galaxypets`.

## 📋 JTBD-сценарии

| Когда | Роль | Хочет | Чтобы | Мы делаем |
|---|---|---|---|---|
| Когда новый клиентский repo уже существует, но в нём хаос из чатов, todo-файлов и ad-hoc notes | Founder / PM / delivery lead | Быстро понять, что надо поднять, чтобы команда перешла на AI-management | Не изобретать процесс заново и не пропустить критические контуры | Запускаем phased rollout: bootstrap -> diagnostic -> registry -> beads -> external bridge -> release activation |
| Когда команда уже умеет делать discovery, но execution разваливается между Jira, Telegram, changelog и ручными заметками | Product / marketing / ops lead | Свести слои в одну operating system | Инициатива не терялась между идеей, delivery и коммуникацией изменений | Разделяем `Docs`, `Projects`, `.beads` и external trackers по ролям и вводим ticket bridge |
| Когда новый AI-инструмент или workflow релизится внутрь команды | Management / enablement lead | Не ограничиться announcement-message | Изменение реально дошло до первого полезного использования и повторного применения | Используем activation loop: changelog -> note -> first-use route -> follow-up proof |

## 1. Базовая модель слоёв

### 1.1 Shared-first principle

Канонические стандарты и shared tooling должны жить в одном месте, обычно в `heroes-pulseai-workspace`.

Клиентский repo не должен копировать весь process layer целиком.
Он должен:

1. подключить shared standards и tooling;
2. завести локальные packet-ы и durable knowledge;
3. вести локальный execution graph;
4. строить client-specific bridge во внешние системы.

### 1.2 Source-of-truth split

| Layer | Canonical role |
|---|---|
| `Docs/` | discovery, knowledge, ADR, policies, diagnostic evidence |
| `Projects/todo.md` | portfolio registry и stage view |
| `Projects/<ProjectName>/` | initiative packet, output/outcome contract, next-best-action |
| `.beads/` | atomic execution, blockers, dependencies, handoff state |
| `Jira / Linear / Telegram / HelpDesk / CRM` | external delivery, client communication, support, record of interaction |

### 1.3 Non-negotiable rule

External tracker never replaces the local operating graph.

`Jira`, `Linear`, support tickets and chat threads are important, but они не должны становиться единственным местом, где живут next-best-action, blockers и process truth для команды.

## 2. Обязательные артефакты для каждого client workspace

Минимальный рабочий комплект:

1. shared links или equivalent setup для standards / tools / environment;
2. `Docs/` с onboarding и ADR;
3. `Projects/todo.md` как portfolio registry;
4. хотя бы один реальный `Projects/<ProjectName>/` packet;
5. `.beads` как primary execution graph;
6. root `changelog.md`;
7. user-facing или team-facing release notes routine;
8. ticket bridge policy: `packet <-> beads <-> external tracker`;
9. weekly review ritual с verdict;
10. owner / DRI map по функциям.

Если любого из этих пунктов нет, AI-management внедрён частично, а не полностью.

## 3. Фазы внедрения

### Phase 0. Bootstrap

Цель: repo открывается, shared tooling доступен, команда не стартует с пустого места.

Минимум:

- shared standards доступны;
- MCP/tooling path понятен;
- локальный `.beads` создан;
- onboarding doc существует.

Выход:

- repo можно открыть и начать ориентироваться;
- но это ещё не operating system.

### Phase 1. Diagnostic and gap audit

Цель: понять, что реально есть, а что только кажется существующим.

Проверяем:

1. рабочий ли `.beads`;
2. есть ли project packets;
3. есть ли registry row;
4. какие external systems уже участвуют;
5. какие owner/DRI отсутствуют;
6. где broken links, stale repos, missing access;
7. есть ли split-brain между legacy todo и новым operating model.

Обязательный output:

- gap-audit или spec с pass/fail по слоям;
- список critical / high / medium gaps;
- первый adoption packet.

### Phase 2. Portfolio registry

Цель: сделать видимым весь портфель инициатив.

Минимум:

1. `Projects/todo.md` содержит все активные initiatives/projects;
2. у каждой активной инициативы есть stage;
3. у каждой активной инициативы есть owner;
4. outcome и next step заполнены;
5. orphan project folders не допускаются.

Для маркетингового контура дополнительно:

- stage model;
- weekly verdict;
- CFD / lead time review.

### Phase 3. Project packet discipline

Цель: ни одна инициатива не идёт в delivery без packet.

Каждый packet обязан содержать:

1. `Название` в формате `Когда ..., хотим ...`;
2. `Ситуация-триггер и проблема`;
3. `JTBD-сценарий`;
4. `1-й релиз и DOD`;
5. `Тест-кейсы`;
6. `Ручные тесты`;
7. `Corner cases`;
8. `Recover / rollback`;
9. `Blockers & Gaps`;
10. `Sub-tasks`;
11. `Итоговый результат`;
12. `Пример output / shape of final artifact`;
13. `links to external trackers if they exist`.

Если packet не содержит `Blockers & Gaps` или `Sub-tasks` для multi-step work, он считается неполным.
Если packet для data/report/sheet delivery не содержит `Пример output / shape of final artifact`, `target_document_name`, `target_document_link`, `target_read_url`, `target_worksheet_name`, `required_shared_to` и `read_access_verification`, он считается неполным.
`Пример output` для data/report/sheet delivery обязан быть table-first: `output_schema_table`, `sample_rows_table`, `field_source_map_table`.
Если агент предлагает улучшение формата output/ticket, он должен в том же ходе показать concrete rewritten example.

Для Codex / AI-агентов `Quick reusable ticket card` обязателен в чате до packet / beads execution.

Канонический шаблон брать из [4.15 symphony linear beads orchestration standard §5.3 Quick reusable card]([standards%20.md]/4.%20dev%20%C2%B7%20design%20%C2%B7%20qa/4.15%20symphony%20linear%20beads%20orchestration%20standard%2014%20march%202026%20cet%20by%20ilya%20krasinsky.md#L387).

Если card не был показан в чате до operational execution, packet discipline считается нарушенным.

### Phase 4. Beads-primary execution

Цель: перевести execution на atomic graph.

Правила:

1. `.beads` ведёт blockers, dependencies и ready queue.
2. Project packet не дублирует весь graph, а отражает только смысл, фазу и preserved context.
3. Beads issues создаются только после readiness packet.
4. После sync нужен verify-step.

### Phase 5. External bridge layer

Цель: связать локальный operating graph с внешними delivery/communication системами.

Обязательные bridge types:

1. `packet <-> Jira/Linear ticket`
2. `packet <-> Telegram/chat thread`
3. `packet <-> HelpDesk/support ticket`
4. `packet <-> changelog/release note`

Минимальное правило bridge:

У каждой active execution initiative должна быть трасса от гипотезы или packet к delivery ticket и обратно.

Без этого команда не сможет объяснить:

1. зачем тикет существует;
2. к какому outcome он относится;
3. где искать клиентский/операционный контекст.

Минимальный packet-to-tracker mapping:

| Packet field | Beads / local graph | Linear / external tracker |
|---|---|---|
| Название | parent/root bead title | concise human-visible title |
| Ситуация-триггер и проблема | description / root notes | short problem frame |
| JTBD-сценарий | root bead context | optional short summary |
| DOD / tests / corner / recover | execution contract | acceptance gate / review signal |
| Blockers & Gaps | blockers / notes / deps | what is still blocked or unproven |
| Sub-tasks | child beads | optional only as high-level next actions |
| Итоговый результат | output/outcome contract | expected delivered artifact |
| Пример output / shape of final artifact | exact final surface | document name + read link + worksheet/tab + required recipients + read verification + columns + sample rows + source map |

### Phase 6. Functional operating loops

#### Marketing

Минимум:

1. initiative registry;
2. owner;
3. DRI;
4. RAT;
5. weekly verdict;
6. CFD/stage review.

#### Sales / support

Минимум:

1. chat/helpdesk intake;
2. ticket bridge;
3. KB or context source;
4. escalation rule;
5. closing note / outcome note.

#### Product / delivery

Минимум:

1. packet before dev;
2. beads blockers;
3. external ticket for execution;
4. verification artifact;
5. release note or change note.

### Phase 7. Release activation loop

Новый процесс, инструмент или capability не считается внедрённым просто потому, что его сделали.

Обязательный activation loop:

1. `changelog.md` — что изменилось;
2. release note — для какой аудитории и зачем;
3. activation note — какой first-use route доступен сегодня;
4. follow-up proof — пример повторного использования;
5. review — произошло ли реальное принятие.

Это прямое продолжение `1.15`: activation относится к стадиям `-1 / 0 / Verify / Integrate`.

### Phase 8. Weekly management cadence

Минимум один weekly ritual должен собирать:

1. portfolio view;
2. blockers;
3. stage movement;
4. bottleneck;
5. verdict `go / iterate / stop`;
6. next action owner;
7. data gaps.

Без weekly cadence AI-management превращается в архив документов без управляемого движения.

## 4. Обязательные правила качества

1. Любой missing source фиксируется как `data gap`.
2. Ни одна инициатива не входит в execution без owner и DRI.
3. Ни одна execution initiative не живёт без external ticket bridge.
4. Ни один material release не проходит без changelog entry.
5. Ни одна team activation не считается завершённой без first useful artifact.
6. Legacy todo layers либо архивируются, либо явно маркируются как non-canonical.

## 5. Что переносим из GalaxyPets как process pattern

Из `galaxypets-management` в клиентские repo переносится не контент, а operating discipline:

1. unified portfolio registry;
2. owner / DRI / RAT / weekly verdict;
3. CFD and lead-time lens;
4. beads-primary execution;
5. release management;
6. activation after change, not just change itself.

## 6. Anti-patterns

Плохие внедрения выглядят так:

1. “Подняли `.beads`, значит AI-management готов”.
2. “Все задачи живут в Jira, локальный packet не нужен”.
3. “Написали стандарт, но не назначили owner”.
4. “Сделали релиз, но не было activation note и reuse proof”.
5. “В repo есть десятки project folders, но registry не знает о них”.
6. “Есть changelog, но он не связан с tickets и инициативами”.

## 7. Exit criteria for a client workspace

Клиентский repo можно считать переведённым на AI-management, когда:

1. bootstrap завершён;
2. diagnostics пройдены;
3. есть active portfolio registry;
4. есть реальные packets;
5. `.beads` используется как daily execution layer;
6. есть ticket bridge;
7. есть weekly verdict cadence;
8. есть changelog/release activation loop;
9. хотя бы одна инициатива прошла полный цикл от packet до release and feedback.

## 8. Связанные стандарты

- `1.15 AI Inception-Delivery Process UX Glue Effort Gap Discovery System Standard`
- `0.1 Registry Standard`
- `1.6 Outcome Zero-Gap JTBD Transfer Standard`
- `1.9 Task Lead Time · CFD Metrics Standard`
- `Changelog Standard`
- `release notes standard`
- `HelpDesk Integration Standard`
