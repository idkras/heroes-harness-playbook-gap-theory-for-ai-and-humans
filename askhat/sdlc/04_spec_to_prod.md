---
title: "Часть 4. Путь от спеки до прода — ядро работы AI Harness"
version: v1
order: 04
type: methodology
date_added: 2026-04-23
status: draft
---

# Часть 4. Путь от спеки до прода — ядро работы AI Harness

> Эта часть отвечает на главный практический вопрос: **как именно работа проходит через harness — от запроса до прода**. Все механизмы методики (autonomy levels, blast radius, decision log, gates, outcomes) сходятся здесь в один pipeline.
>
> Если предыдущие части отвечали «зачем» (Часть 1), «как ощущается» (Часть 2), «из чего состоит» (Часть 3) — эта часть про то, **как это работает**.
>
> Читается за 25 минут.

---

## 1. Большая картина

Pipeline от запроса до прода имеет **четыре стадии**:

```
[Запрос]
    ↓
┌────────────────────────────────────────┐
│ Стадия 1: Spec creation                │
│   Agent-led диалог с PM,               │
│   обогащённый KB и стандартами         │
│   → выходит: спека + декомпозиция      │
└────────────────────────────────────────┘
    ↓ Spec quality gate (auto)
┌────────────────────────────────────────┐
│ Стадия 2: Per-work-unit execution      │
│   Каждая атомарная единица работы      │
│   проходит автономно (по A1-A5)        │
│   в изолированной ветке                │
│   → выходит: код + decisions log       │
└────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────┐
│ Стадия 3: End-gate                     │
│   Автоматические проверки +            │
│   rule-based routing к ревьюерам       │
│   → выходит: verdict (один из 17)      │
└────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────┐
│ Стадия 4: Outcome execution            │
│   Merge / rollback / postpone /        │
│   convert / другое                     │
└────────────────────────────────────────┘
    ↓
[Прод или нет]
```

Через **все четыре стадии** проходят несколько трансверсальных механизмов:
- **Branch isolation** — работа в изолированной ветке от начала до end-gate
- **KB context** — агент имеет доступ к организационному знанию
- **Decision Log** — каждое значимое решение фиксируется
- **Spec как живой артефакт** — спека обновляется по ходу

Разворачиваю каждую стадию.

---

## 2. Стадия 1 — Spec creation

### Принципы стадии

Спека рождается **в диалоге PM ↔ агент**, где **агент активно ведёт**. Не «PM пишет, AI исполняет». Агент использует KB, стандарты, прошлые паттерны, чтобы помочь PM не накосячить.

У агента есть знания, которых у PM нет в голове. Он применяет их **проактивно**, до того как PM скажет глупость.

### Что происходит шаг за шагом

**0. Intent.** PM формулирует запрос — «хочу feature X».

**1. Агент обогащает контекст до диалога.**
- Ищет в KB похожие прошлые спеки
- Подтягивает применимые стандарты (design system, security, copy guidelines, compliance)
- Идентифицирует вероятные task types
- Готовит skeleton спеки на их базе
- Помечает known constraints (rate limits, expiry defaults)

**2. Диалог с направленными вопросами.**
Агент не «расскажи мне всё», а: «Похоже на invite-flow паттерн X. Применяем тот же email-шаблон? Default expiry 14 дней — норм? Permission flow через workspace-member-permission.v2 — да?» Каждый вопрос закрывает gap в skeleton.

**3. Агент применяет defaults, флагует assumptions.**
Где у KB есть хороший default — агент применяет автоматически, но **явно записывает в Decision Log** как ASSUMPTION для будущего ревью.

**4. Агент проактивно поднимает риски.**
«Затронут permissions — нужен security review на end-gate». «Spam-protection rules были ужесточены после инцидента 2024 — учти». «Может ударить по email-провайдеру — проверь квоты». Эти вещи **PM может не знать** — агент знает.

**5. Декомпозиция в work units во время speccing.**
Спека рождается **уже структурированной**. Не «потом разберём» — сразу видно: какие work units, какие зависимости, какой autonomy level у каждого, какой blast radius.

### Spec quality gate (start-gate)

Прежде чем перейти к коду — **автоматическая проверка спеки**. Layered подход:

**Слой 1 — Hard gate (блокирует).** Структурные/детерминистические rules:
- Все required template fields заполнены
- ≥ 1 user story с ≥ 1 AC
- Декомпозиция в work units сделана (хотя бы preliminary)
- Нет orphan referenced patterns

**Слой 2 — Soft warnings (флагует, не блокирует).** Rule-based:
- «Email feature → должна быть упомянута spam protection»
- «AC не в Given-When-Then формате»
- «Performance budget не указан, но required по KB для type X»

**Слой 3 — LLM-as-judge advisory (асинхронный совет).** Семантический ревью:
- Edge cases которые KB знает
- Ambiguity в формулировке
- Intent vs spec alignment

PM может игнорировать Слои 2 и 3 (с записью в Decision Log как ack'ed-but-not-addressed). Слой 1 блокирует.

### Что выходит со Стадии 1

- **Спека** с user stories, AC, decomposition, dependencies
- **Decision Log** с assumptions из дефолтов и явных PM-решений
- **Список predicted gates** — что потребуется на end-gate
- **Estimated routing** — кто будет ревьюить (по rule-based маршрутизации)

Спека **знает свои собственные риски и точки контроля**.

---

## 3. Стадия 2 — Per-work-unit execution

### Принципы стадии

Каждая атомарная единица работы проходит **самостоятельно** по своему autonomy level. Они **могут идти параллельно** там, где зависимости позволяют. Все работают **в изолированной ветке** — branch isolation.

### Atomic work unit

Что такое work unit:
- Атомарное действие AI: правка файла, добавление модуля, изменение схемы
- Имеет **измеримые свойства**: какие файлы трогает, какой контракт затрагивает, сколько строк, blast radius
- Имеет **приписанный type** (из task-type matrix организации)
- Имеет **default autonomy** (из type, может быть переопределена per-instance)
- Имеет **dependencies** на другие work units (из спеки)

### Autonomy levels — что происходит на каждом

**A1 — Suggest only.** AI предлагает, человек делает. AI участвует как умный консультант. Применяется когда: AI capability gap (FX hot path), critical correctness (auth migration), или low KB maturity для этого type.

**A2 — Propose with approval.** AI готовит PR, человек одобряет каждый шаг или весь PR. Самый частый mode для нерутинных задач.

**A3 — Execute with review.** AI выполняет блок работы, человек проверяет результат. Подходит для типовых задач с устоявшимися паттернами в KB.

**A4 — Autonomous with end-review.** AI делает от начала до конца, человек проверяет только финал. Применяется к задачам с высокой reversibility и низким blast radius.

**A5 — Fully autonomous + auto-deploy.** AI делает и деплоит, человек подключается только при алерте. Применяется к минимально критичным задачам с мгновенной обратимостью (например, через remote config).

### Что определяет autonomy для конкретного work unit

Несколько факторов в порядке влияния:

1. **Default autonomy из task type** — стартовая точка
2. **Blast radius work unit'а** — большой → autonomy ниже
3. **Reversibility** — обратимо легко → autonomy выше; необратимо → ниже
4. **KB maturity для этого type** — больше накопленных паттернов → autonomy выше со временем
5. **AI capability в этом sub-domain** — где AI слабый, autonomy ограничивается даже при низком риске
6. **Recent incident history** — после инцидента соответствующий type откатывается на уровень ниже

### Decision points и assumptions

Во время выполнения work unit AI встречает **decision points** — где есть выбор. По нашей договорённости:

- AI делает **default-предположение** (по KB pattern или sensible default)
- **ЯВНО логирует в Decision Log** как ASSUMPTION
- Продолжает работу

PM по ходу может посмотреть и скорректировать. Если ничего не сказал — работа идёт с принятыми defaults.

Это и есть «PM ок-окает» в нашей предыдущей дискуссии. Branch isolation делает это безопасным — даже если PM невнимательно ок-окнул что-то критическое, end-gate поймает.

### Branch isolation как защитный механизм

Вся работа Стадии 2 происходит **в ветке**. Прод не страдает от любых ошибок здесь. Это значит:

- PM может делать ошибки без катастрофы
- AI может делать ошибки без катастрофы
- Defaults могут быть неправильными — поправят на end-gate

Без branch isolation весь Pattern C (PM-driven flow) невозможен.

### Что выходит со Стадии 2

- **Реализованные work units** в ветке
- **Обновлённая спека** (если по ходу что-то уточнилось)
- **Полный Decision Log** с assumptions и явными решениями
- **Tests** (где соответствует task type)
- **Готовность к end-gate**

---

## 4. Стадия 3 — End-gate

### Принципы стадии

End-gate — **точка контроля методики**. Сюда сходятся все work units. Здесь решается, идёт ли в прод.

End-gate состоит из двух слоёв:
- **Автоматические проверки** (deterministic, быстрые)
- **Human review** (с rule-based routing к компетентному ревьюеру)

### Автоматические проверки

В зависимости от того что было затронуто:
- Tests passed
- Linters / type checks
- Security scan
- Compliance scan (PCI, GDPR rules)
- Performance regression test
- Visual regression test (для UI)
- Dependency / license check
- Audit log integrity
- Spec ↔ code consistency

Не все запускаются всегда. Ranlas-based: «затронут код X → запускается проверка Y». Конкретные правила — content of harness, organizable per organization.

### Rule-based routing к человеческому ревьюеру

Это **единственное место**, где специалист подключается принудительно (см. предыдущее решение про Pattern C). Routing rules — это правила, которые говорят:

- Затронут payment-related код → routes к compliance reviewer
- Затронут auth/security → routes к security reviewer
- Затронут matching engine → routes к senior trading dev
- Затронут схема БД → routes к DBA / senior backend
- Тронуты UI компоненты outside design system → routes к design lead

Routing — **автоматический по rules**. PM не выбирает «к кому отправить». Harness сам определяет.

### Что reviewer делает

Reviewer видит:
- Спеку (с assumptions logged)
- Реализацию
- Diff
- Все автоматические проверки и их verdicts
- Decision Log с явными points для review

Reviewer выбирает **outcome** (см. Стадию 4 — 17 категорий).

### Что выходит со Стадии 3

- **Verdict per work unit** (или per всей работы)
- **Один из 17 outcomes** для каждого work unit
- **Возможно: feedback для автора**

---

## 5. Стадия 4 — Outcome execution

### 17 финальных outcomes

Distribution возможных исходов:

**A — Успешный merge**:
1. Auto-merge silent
2. Auto-merge with notification
3. Approved merge
4. Approved with conditions (follow-up tasks)
5. Conditional merge с feature flag (за флагом, неактивно)
6. Phased / staged rollout (5% → 25% → 100%)
7. A/B-test merge (как ветка эксперимента)

**B — Не дошло до merge, но ценность есть**:
8. Converted to spec/doc (research, не код)
9. Postponed (подождём)
10. Split into sub-units (декомпозиция глубже)

**C — Не дошло, ограниченная ценность**:
11. Returned for rework
12. Routed to specialist (другой человек берёт)
13. Escalated (стратегическое решение выше)
14. Discarded

**D — После merge что-то пошло не так**:
15. Auto-rolled back (мониторинг увидел)
16. Manual rollback (incident)
17. Hotfix-amended (допатчили на лету)

### Какие outcomes доминируют на каком autonomy level

| Autonomy | Доминирующие | Редкие, но возможные |
|---|---|---|
| **A5** | 1, 2 (auto) | 15 (auto-rollback) |
| **A4** | 2, 3, 14 | 11, 16 |
| **A3** | 3, 4, 11 | 12, 13 |
| **A2** | 3, 11, 12 | 8, 9, 14 |
| **A1** | 3, 11, 8 | 12, 13 |

**Наблюдения**:
- На high autonomy (A4-A5) контроль через **monitoring + rollback**, не через ревью
- На A3 баланс **approve/return** — оптимальная зона для PM-driven flow
- На low autonomy (A2-A1) растёт доля **convert to spec / postpone / delegate** — потому что низкая автономия часто значит «работа была преждевременной»

### Special outcomes требующие внимания

**Conditional merge с feature flag (#5)** — мощный механизм для high-autonomy + high-blast-radius комбинаций. Код в main, но не активен. Активация — отдельный act с дополнительной проверкой. Это даёт «safety валентность» к высокой autonomy.

**Convert to spec (#8)** — недооценённый. Работа, не доехавшая до merge, может иметь ценность как investigation. Спека сохраняется в архиве. **Не считается провалом**.

**Routed to specialist (#12)** — НЕ принудительный handoff из методики. Это «end-gate определил что нужен специалист Y» по правилам. Author не теряет authorship — ревью у компетентного человека.

---

## 6. Трансверсальные механизмы

Несколько штук работают **через все 4 стадии**, не привязаны к одной.

### Branch isolation

Вся PM-driven работа происходит в изолированной ветке от Стадии 1 (создание спеки) до Стадии 4 (outcome execution). Это:
- Защищает прод от любых ошибок в процессе
- Позволяет PM свободно итерировать
- Делает все «wasted work» сценарии **безопасными** — максимум потеряно время + токены, прод не страдает

Без branch isolation весь Pattern C невозможен.

### KB context (Knowledge Base)

Агент на каждой стадии имеет доступ к KB. KB предоставляет:
- Прошлые паттерны (для re-use в новых спеках)
- Стандарты (design system, security, conventions)
- Decision Log past tasks (как раньше решали похожее)
- Task-type matrix (defaults и rules)
- Routing rules (кто что ревьюит)

KB **наполняется маховиком** — каждая завершённая работа добавляет в KB. Чем больше задач прошло — тем умнее агент в следующих.

### Decision Log

Запись каждого значимого решения с reasoning. Создаётся на Стадии 1 (assumptions из defaults), пополняется на Стадии 2 (decisions при выполнении), используется на Стадии 3 (reviewer видит assumptions для проверки), архивируется на Стадии 4 (становится материалом для KB).

Особо ценно в Decision Log: **«почему отклонили предложение AI»**. Это — обучающая память.

### Spec как живой артефакт

Спека не «один раз написана и заморожена». Она:
- Создаётся в Стадии 1
- Может уточняться в Стадии 2 (если работа выявила нюансы)
- Используется reviewer'ом на Стадии 3 для проверки
- Сохраняется как final artifact на Стадии 4 (или обновляется при rollback / amendment)

При **convert-to-spec outcome** (#8) спека — единственный остающийся артефакт работы.

---

## 7. Что определяет всё на каждой стадии

Сводная картина — какие факторы влияют на каждом этапе:

### На Стадии 1 (spec creation)
- **KB maturity** — насколько обогащённый skeleton агент может предложить
- **Quality of intent от PM** — насколько чётко PM может сформулировать запрос
- **Domain complexity** — сколько decisions агент применяет default'ом

### На Стадии 2 (execution)
- **Default autonomy от task type**
- **Blast radius work unit'а**
- **Reversibility**
- **AI capability в sub-domain**

### На Стадии 3 (end-gate)
- **Routing rules** — кто что ревьюит
- **Available reviewers** — могут быть в очереди
- **Verdict автоматических проверок** — могут блокировать ещё до human review
- **Risk profile** — high blast → строже review

### На Стадии 4 (outcome execution)
- **Reviewer's verdict**
- **Risk profile** — может диктовать conditional merge или phased rollout вместо straight merge
- **Time pressure** — incident hotfix vs обычная работа

---

## 8. Эволюция autonomy через flywheel

В Стадии 2 default autonomy для task type **меняется со временем**:

**В начале применения методики** для новой команды:
- Все task types на A1-A2
- KB пустой или минимальный
- Каждый work unit активно ревьюится

**Через 3-6 месяцев**:
- Накопились паттерны в KB для типовых работ
- Часть task types можно повышать на A3
- Меньше нужно ревью на типовых

**Через год+**:
- Зрелый KB, много накопленных паттернов
- Часть типовых задач на A4-A5
- Ревью только на нестандартных и критичных

Этот переход — **product flywheel**. Не arbitrary, а на основе **success rate / incident rate per task type**. Если type X consistently не вызывает инцидентов — promote autonomy. Если incident — demote.

Это операционализация маховика из Части 2.

---

## 9. Практический пример end-to-end

Применяем pipeline к запросу из Части 2:

> **PM**: «Хочу добавить приглашение коллег по email».

### Стадия 1 (spec creation)

- Агент находит в KB: 3 invite-flow паттерна, стандартный email template, permission framework workspace-member-permission.v2, spam-protection rules
- Готовит skeleton: invite-flow type, email integration sub-type
- Диалог: «применяем стандартный email и permissions? Default expiry 14 дней? Spam-protection как обычно (50/день, 5/час)?»
- PM подтверждает defaults, добавляет: «expiry 14 дней, не 7»
- Декомпозиция в 6 work units: API endpoint, email integration, UI form, permission change, spam protection, E2E tests
- Spec quality gate: пройден (Layer 1 ✓, Layer 2 ✓, Layer 3 не выявил critical issues)
- Spec ready, передаётся в код

### Стадия 2 (execution)

В branch:
- WU1 (API) — A2, AI пишет, PM смотрит ходом
- WU2 (email) — A2, использует стандартный template
- WU3 (UI) — A2, использует стандартные компоненты
- WU4 (permission) — A1, AI готовит план, PM ack'ает по руководству KB
- WU5 (spam) — A1, AI применяет KB-стандарт, PM accepts
- WU6 (E2E tests) — A2, генерируется по AC

Decision Log: assumptions documented, явные PM-решения documented.

### Стадия 3 (end-gate)

Автоматические проверки:
- Tests pass ✓
- Security scan ✓
- Visual regression на UI ✓
- API contract test ✓

Routing:
- Permission change → routes к security reviewer
- Spam protection → automated check + notification к platform team
- Остальное — без специальных reviewer'ов

Security reviewer смотрит permission change, одобряет. Все verdicts: **Approved merge** (#3).

### Стадия 4 (outcome execution)

Merge в main. Деплой через стандартный pipeline.

KB пополняется:
- Новый use case в библиотеке invite-flows
- Decision: «expiry 14 дней — продуктовая норма для workspace member invites»

**Total time**: ~2 часа (как описывалось в Часть 2 для маховика).

---

## 10. Что эта часть НЕ описывает

Для понимания границ:

- **Adoption playbook** — как вводить методику в команде. Это будущая Часть 5.
- **Кто и как поддерживает harness** — будущая Часть 6.
- **Как методика эволюционирует** — будущая Часть 7.
- **Конкретные шаблоны спек, KB-структура, routing rules format** — это content of harness, не methodology. Заполняется per organization.

---

## 11. Связь с принятыми принципами

Этот pipeline операционализирует и согласуется со всеми meta-принципами:

- **Outcomes not processes** (A23) — pipeline регулирует что должно быть на выходе каждой стадии, не как стадия выполняется
- **Structure not content** (A29) — schema work unit, schema спеки, schema routing — methodology defines, organization fills
- **Optimize for bottleneck** (A27) — спека (короче кода) как точка контроля; auto checks где возможно; human только где нужно
- **Dynamic not static** (A21) — autonomy эволюционирует через flywheel
- **Education as part of methodology** (A38) — диалог агента с PM в Стадии 1 включает образовательный layer (объясняет почему именно так)
- **Spec compactness** (A44) — спека ~10× короче кода → ревью спеки масштабируется
- **Spec-first killer reason** (A43) — здесь видно: high autonomy возможна только потому, что спека ревьюема
- **Codification = THE work** (A46) — KB накопление в Стадии 4 = это и есть «codification»

---

## 12. Главный месседж этой части

> **Путь от спеки до прода — это последовательность четырёх стадий с branch isolation как защитным механизмом, KB как контекстным enrichment, и Decision Log как памятью.**

Каждая стадия имеет:
- Чёткий вход (что приходит)
- Чёткий выход (что должно быть)
- Возможные outcomes (что может произойти)

Все факторы (autonomy, blast radius, AI capability, KB maturity, reviewer availability) **играют роль в pipeline**, но сходятся в простую структуру.

**TTM-эффект** методики возникает потому что:
1. Стадия 1 быстрая (агент ведёт PM, не PM ведёт спеку с нуля)
2. Стадия 2 параллельна (work units идут параллельно где зависимости позволяют)
3. Стадия 3 концентрированная (reviewer работает только когда нужно)
4. Стадия 4 предсказуемая (outcome — один из 17, не surprise)

Без этого pipeline AI-разработка либо хаотична (вайб-кодинг), либо забюрокраченa (всё через сеньора). Pipeline — это **третий путь**, который TTM-friendly при сохранении контроля.

---

## 13. Что в следующих частях

- **Часть 5** — Adoption: как внедрить методику с нуля в организации, первые 30/60/90 дней
- **Часть 6** — Кто и как поддерживает harness в живом состоянии
- **Часть 7** — Эволюция методики со временем, governance меняющегося content (KB, routing rules, task types)
