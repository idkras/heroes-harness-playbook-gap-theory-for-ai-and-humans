---
title: "Пример: Task Types для интеграционного продукта (payment gateway)"
version: v1
type: example
date_added: 2026-04-23
status: draft
---

# Пример — как могут выглядеть Task Types для платёжного шлюза

> Это второй пример (первый — для классического enterprise web+mobile SaaS, см. отдельный файл). Показывает, как **тот же концепт** — Task Type — приземляется в **другую предметную область**, и почему конкретный каталог типов в результате выходит совсем другим.
>
> Цель — увидеть domain-specificity на практике. Что переносится между доменами, что нет.
>
> Читается за 20 минут.

---

## 1. Контекст продукта

Возьмём типичный **payment gateway** — продукт, который интегрирует множество платёжных провайдеров (Stripe, PayPal, Klarna, Adyen, локальные методы) и предоставляет мерчантам единое API для приёма платежей.

**Технологический контекст**:
- **Backend-heavy**: основное — серверная часть, обработка транзакций, очереди, webhook-handlers
- **Минимальный UI**: только внутренние admin-панели, дашборды, иногда checkout-виджеты
- **Async processing**: транзакции, реконсилиация, отчёты — всё через очереди
- **Высокие SLA**: downtime = потерянные деньги
- **Compliance**: PCI-DSS, PSD2, AML, KYC, региональные требования
- **Reconciliation**: каждая транзакция должна сматчиться между нашей системой и провайдером

**Главное отличие от типового SaaS**: в коде ходят **деньги**. Бажный код — это не «пользователю неудобно», это **финансовые потери**, регуляторные санкции, audit-failures.

---

## 2. Что меняется в классификации задач для этого домена

Те же три цели классификации (автономия, проверки, контекст) — но **разный калибр последствий**:

- **Автономия**: дефолт по всем типам **ниже**, чем в SaaS. AI почти нигде не работает на A4-A5. Money-related → A1-A2 максимум.
- **Проверки**: гораздо больше типов проверок: PCI compliance, idempotency, reconciliation, audit trail, regulatory, load testing. Это не roadmap-фича, а обязательная инфраструктура.
- **Контекст**: KB наполнен compliance-документами, regulatory-маппингами, провайдер-specific quirks. Это специальное знание, которое нужно AI давать explicitly.

И ещё одно структурное отличие: **внешние зависимости** — провайдеры, регуляторы, банки-партнёры. Они меняются по своему графику, и продукт реагирует. Так что появляются типы задач «они изменились — нам надо мигрировать», которых в обычном SaaS не бывает.

---

## 3. Схема Task Type — та же, что в webmobile-примере

Перепиcывать нет смысла — **схема одна и та же**:

```yaml
task_type:
  name: "<краткое имя>"
  detection: { triggers, file_signals }
  blast_radius: { users_affected, reversibility, cross_team }
  default_autonomy: <A1 | A2 | A3 | A4 | A5>
  required_context: [<patterns / standards>]
  required_gates: [<обязательные проверки>]
  typical_decomposition: [<подзадачи>]
```

Это и есть подтверждение методического принципа: **схема универсальна, наполнение domain-specific**.

---

## 4. Каталог Task Types для платёжного шлюза

12 типов, покрывающих основное пространство работы.

### Type 1. New payment provider integration

**Что**: добавление нового провайдера целиком (например, начали интегрировать Adyen с нуля).

**Триггеры**: «интегрировать <provider>», «добавить поддержку <provider>».

**Файлы**: новый модуль провайдера, маппинг внутренних объектов, webhook handlers, reconciliation logic, secrets, sandbox config.

**Blast radius**: small users изначально (новый, никто не использует), но **потенциал large** при включении в продакшн.

**Default autonomy**: **A1** (новые провайдеры всегда под senior + compliance review).

**Required context**: integration patterns library, security baseline, PCI scope, internal таксономия методов оплаты.

**Required gates**: 
- Sandbox certification (от провайдера) 
- PCI scope review
- Reconciliation работает на тестовых данных
- Idempotency tests
- Load tests
- Security audit

**Typical decomposition**: 
- Сам клиент к API провайдера
- Маппинг объектов
- Webhook handlers
- Reconciliation
- Refund handling
- Admin UI для конфигурации
- Documentation

Это **многонедельная задача**, всегда декомпозируется в 10+ work units.

---

### Type 2. Provider API update

**Что**: провайдер изменил своё API — нам нужно адаптироваться (deprecation, breaking change, new fields).

**Триггеры**: deprecation notice от провайдера, sandbox несовместим с продом, breaking change announcement.

**Файлы**: модуль провайдера, версионирование, миграция, тесты.

**Blast radius**: large (все мерчанты, использующие провайдера), reversibility — hard (нельзя «откатить» изменение в API провайдера).

**Default autonomy**: **A1** (риск регресса слишком высок).

**Required context**: changelog провайдера, текущая интеграция, история integration patterns, regression test history.

**Required gates**: 
- Sandbox tests на новой версии
- Reconciliation regression tests
- Phased rollout (флаг на provider per merchant)
- Backward compat для in-flight транзакций
- Audit trail of migration

**Особенность**: **временные ограничения извне** — провайдер может дать дедлайн «после X числа старая API не работает». Это создаёт давление на качество.

---

### Type 3. New payment method (within existing provider)

**Что**: у уже интегрированного провайдера добавляется новый метод (например, Apple Pay через Stripe — сам Stripe уже интегрирован).

**Default autonomy**: **A2** (PR + review, но не такая тяжёлая работа как новый провайдер).

**Required context**: provider's docs, internal таксономия методов.

**Required gates**: end-to-end в sandbox, конфликт с существующими методами проверен.

**Typical decomposition**: маппинг → admin config → checkout integration → reconciliation → docs.

---

### Type 4. New currency support

**Что**: добавление поддержки новой валюты.

**Default autonomy**: **A2**.

**Required gates**: rounding rules tests (минорные единицы, дробные части), forex rate handling, валидация по ISO 4217, regulatory check (некоторые валюты ограничены).

**Особенность**: кажется простой задачей, но содержит много edge cases (currencies без minor units, currencies с тремя decimals, restricted currencies).

---

### Type 5. Webhook handler change

**Что**: добавление или модификация обработчика входящих событий от провайдера. Например, поддержать новый тип события или поправить existing.

**Default autonomy**: **A2**.

**Required context**: idempotency patterns, retry/replay logic, audit trail conventions.

**Required gates**: 
- **Idempotency tests** — обязательно (одно и то же событие не должно обрабатываться дважды)
- Replay tests (как обработка ведёт себя при дублирующем events)
- Out-of-order tests
- Failure recovery tests

**Особенность**: webhook'и — главная точка hidden bugs. Идемпотентность — критический пункт.

---

### Type 6. Reconciliation logic change

**Что**: изменение в логике сверки транзакций между нашей системой и провайдером.

**Default autonomy**: **A1** (затрагивает money flow correctness).

**Required gates**:
- Регрессия на исторических данных (последние N месяцев) — **обязательно**
- Diff с предыдущей версией: должны совпадать на 99.9%+
- Performance test (reconciliation крутится в production scale)

**Особенность**: ошибки здесь не приводят к immediate visible problems, но проявляются в **финансовом несоответствии** в отчётах. Это самый «тихий» класс багов.

---

### Type 7. Fraud rule update

**Что**: добавление, удаление, корректировка правила в anti-fraud системе.

**Default autonomy**: **A2** (но требует review fraud team).

**Required gates**: 
- Симуляция на исторических транзакциях (false positive rate, false negative rate)
- A/B тест если возможно
- Rollback plan

**Особенность**: tradeoff между **пропуском мошенничества** (financial loss) и **блокировкой добросовестных пользователей** (lost revenue). Метрика — оба показателя.

---

### Type 8. Compliance / regulatory update

**Что**: реакция на изменение в законе, регуляции, стандарте. Например, новая версия PSD2, новые требования AML, обновление 3DS.

**Триггеры**: regulatory notice, audit finding, deadline от регулятора.

**Default autonomy**: **A1** (юрист или compliance officer ставит подпись).

**Required gates**:
- Legal review — обязательный
- Compliance officer approval
- Audit trail of why changes (regulatory citation)
- Phased rollout if scope-significant

**Особенность**: **дедлайны жёсткие** (часто внешние, юридические). Работа с compliance officer — first-class participant.

---

### Type 9. Refund / chargeback flow

**Что**: изменения в том, как обрабатываются возвраты или chargeback'и.

**Default autonomy**: **A1-A2** (затрагивает money flow и иногда регуляторные требования).

**Required gates**:
- Ledger consistency tests
- Edge case tests (partial refund, refund after chargeback, etc.)
- Provider-specific quirks documented
- Tax handling correctness

**Особенность**: **tax**, **bookkeeping**, **provider-specific behaviors** — три источника сложности. Каждый refund flow обычно сложнее, чем кажется.

---

### Type 10. Tokenization / PCI scope change

**Что**: изменения, затрагивающие обработку карточных данных. Любое касание PCI scope.

**Default autonomy**: **A1** (PCI-trained dev обязательно).

**Required gates**:
- PCI scope assessment
- Security audit
- Penetration test if scope-significant
- QSA review (если applicable)

**Особенность**: **самый жёсткий тип** в плане gates. Ошибка → потеря PCI compliance → потенциальное прекращение обработки карт. Цена ошибки — катастрофическая.

---

### Type 11. Performance / reliability optimization

**Что**: throughput, latency, reliability improvements. Кеширование, индексы, бекплейн оптимизации, retry logic.

**Default autonomy**: **A2**.

**Required gates**:
- Load test на production-like scale
- p99 latency budget сохранён
- Memory profile checked
- Circuit breaker / backpressure correct

**Особенность**: финансовые транзакции имеют жёсткие SLA — user-facing латентность напрямую влияет на conversion. Performance — не optimization, это product feature.

---

### Type 12. Reporting / internal analytics

**Что**: внутренние отчёты, dashboards, BI-выгрузки. Не money-touching.

**Default autonomy**: **A3** (read-only пути, низкий риск).

**Required gates**: data accuracy tests против golden datasets, performance на больших объёмах.

**Особенность**: **единственный тип**, где autonomy относительно высокая. Потому что это **read-only** относительно money flow — меньше cost при ошибке.

---

## 5. Worked example — интеграция Klarna

Реалистичный запрос:

> «Давайте добавим Klarna. Хотим BNPL (buy-now-pay-later) и обычные платежи. Должно работать в EU и в US».

Сразу видно — это **не одна задача**. Декомпозируется примерно так:

| # | Work unit | Type | Зависимости | Default autonomy |
|---|---|---|---|---|
| 1 | Базовая интеграция Klarna API | Type 1 (new provider) | — | A1 |
| 2 | Маппинг Klarna's payment methods на нашу таксономию | Type 3 sub | depends on #1 | A2 |
| 3 | Поддержка SEK, NOK, DKK | Type 4 (currency) | depends on #1 | A2 |
| 4 | Webhook handlers для Klarna events | Type 5 | depends on #1 | A2 |
| 5 | Reconciliation для Klarna транзакций | Type 6 | depends on #1, #4 | A1 |
| 6 | BNPL-specific fraud rules (другой риск-профиль) | Type 7 | depends on #1, #2 | A2 |
| 7 | PSD2 SCA для EU транзакций | Type 8 (compliance) | depends on #1 | A1 |
| 8 | US-specific compliance (отличается от EU) | Type 8 (compliance) | depends on #1 | A1 |
| 9 | Refund flow Klarna | Type 9 | depends on #1, #5 | A1 |
| 10 | Tokenization для Klarna (если затрагивает PCI scope) | Type 10 | depends on #1 | A1 |
| 11 | Admin UI: настройки Klarna для merchant | Type 13 (UI) | depends on #1 | A2 |
| 12 | Reporting: новые отчёты с Klarna transactions | Type 12 | depends on #1, #5 | A3 |
| 13 | Idempotency tests для Klarna webhooks | (часть #4 + #5) | — | A2 |
| 14 | Load test и failover для Klarna | Type 11 | depends on большинство | A2 |
| 15 | Internal docs + KB updates | (cross-cutting) | — | A2 |

Видно сразу:
- **Один внешний запрос = почти все 12 типов задействованы**.
- Зависимости от #1 — он каскадирует на всё остальное.
- **9 из 15 work units на A1** (низкая автономия) — это норма для платёжного шлюза.
- **Compliance — два разных work unit** (EU и US), потому что регуляторика разная.
- Это работа на **квартал** для команды, а не на спринт.

---

## 6. Что становится видно

**(1) Default autonomy в этом домене систематически ниже.** В webmobile примере было много A2-A3, тут — много A1. Это не «команда не доверяет AI», это **природа cost ошибки** в этом домене.

**(2) Compliance — first-class concern.** В webmobile примере compliance проявлялся изредка. Здесь — почти в каждом work unit. PSD2, PCI, AML, region-specific — это **обязательная нагрузка**.

**(3) Idempotency как cross-cutting.** Невидимая в webmobile, но критическая здесь. Webhook handler без idempotency — почти гарантия dup-charges. Поэтому в нашем каталоге это явная gate в Type 5.

**(4) Reconciliation — отдельный тип, не часть testing.** В webmobile это было бы сабтаска внутри backend. Здесь — отдельный тип, потому что **reconciliation — самостоятельный сервис**, со своей логикой и своими ошибками.

**(5) Внешние дедлайны** (regulatory deadline, provider deprecation) — фактор, которого почти нет в webmobile. Создаёт давление, требует special handling.

**(6) Money-touching vs read-only** — главный водораздел autonomy. Read-only (reporting) можно дать AI-агенту с лёгкой автономией. Money-touching — никогда.

---

## 7. Что не fits классификацию

Те же edge cases, что в webmobile, плюс свои:

**Кейс 1: «Подготовиться к Black Friday»** — это performance + reliability + monitoring + capacity planning + incident readiness. Несколько типов в одной операции.

**Кейс 2: «Добавить новую регуляторную требованию для одной страны»** — это compliance + reporting + tokenization + admin UI. Тоже несколько типов.

**Кейс 3: «Pivot — теперь работаем не только B2C, но и B2B»** — это **архитектурное изменение**, которое не описывается через task type вообще. Это уровень спеки, которую методика помогает декомпозировать, но сама работа — гора отдельных types.

**Кейс 4: Reactive incident** — провайдер положил их API, у нас падают платежи. Это **emergency response**, который выходит из обычного workflow (как Type 12 hotfix в webmobile, но более частая ситуация).

---

## 8. Что отличается от webmobile-примера

Ключевые сравнения:

| | Webmobile SaaS | Payment Gateway |
|---|---|---|
| Главный stake | UX, продуктовая ценность | Money correctness, compliance |
| Default autonomy distribution | Много A2-A3 | Много A1, единичные A3 |
| Cosmetic / UI changes | Большая часть работ | Незначительная (только admin UI) |
| Compliance | Изредка (security, GDPR) | First-class в каждом типе |
| External dependencies | Несколько integration | **Большинство работ** про внешние интеграции |
| Idempotency | Опционально | Critical |
| Reconciliation | Не concept | Самостоятельная категория работ |
| Reversibility | Обычно easy | Часто hard (deniedможно потерять деньги) |
| Time pressure | Внутренний (релизы) | Внешний (regulatory, provider deadlines) |
| Mobile specifics | Большой Type | Минимальный (только консьюмер-чекаут) |
| Refactoring | Регулярно | Редко (риск разрушения работающего money flow) |
| Cost ошибки | UX или revenue | Регуляторика, потерянные деньги, потеря лицензии |

**Главный вывод**: каталог типов в этих двух доменах **пересекается слабо**. Из 12 webmobile типов в payment gateway переносятся условно ~3 (UI cosmetic admin, performance, отчасти bug fix). Остальные — **доменно-специфичны**.

---

## 9. Что это значит для методики

**(1) Универсальные task types не работают.** Если методика предлагает «вот общий каталог типов» — он либо webmobile-bias, либо payment-bias, либо такой generic что бесполезен. **Каждая организация наполняет свой каталог**.

**(2) Схема Task Type — переносится.** То, *как описывается* тип (поля, blast radius, autonomy, gates) — одинаково для обоих доменов. Это и есть structure-vs-content из принципов методики.

**(3) Уровни autonomy дефолтно разные между доменами.** Methodology может дать **рекомендации** «по дефолту начинайте с A2 для большинства задач, A1 для money-touching», но **финальные значения — domain-call**.

**(4) Gates сильно differ.** Каждая отрасль имеет свои обязательные проверки. Webmobile нужна visual regression. Payment нужна reconciliation. Это **часть domain knowledge**, не методики.

**(5) Декомпозиция глубже в payment domain.** Один внешний запрос = десятки work units. AI-агент должен это уметь, в KB должны быть **patterns of decomposition** для типичных payment-related scope'ов (новый provider, новая регуляторика, etc.).

---

## 10. Открытые вопросы (специфичные для этого домена)

- **Как методика взаимодействует с regulatory release cadence?** Compliance updates часто идут с жёстким дедлайном. Methodology должна разрешать «accelerated path» с дополнительными gates, не replace их.

- **Cross-team в payments — это отдельная ось**. Платёжный шлюз почти всегда взаимодействует со многими внешними сторонами (провайдеры, банки, регуляторы). Это нужно отдельной категории, не просто «cross-team change».

- **Money-touching как central axis** — может стоит явно ввести как поле task type («money-touching: yes/no»), потому что это меняет всё.

- **Audit trail by default** — каждое изменение, не только money-touching, должно логироваться для аудита. Это скорее всеобщее свойство, чем тип.

---

## 11. Главный месседж этих двух примеров

Те же два месседжа, но в новой формулировке после второго примера:

**Methodology — это schema. Application of methodology — это content.**

Webmobile и payment gateway применяют **одну и ту же methodology**. Они получают **разные task type catalogs**, разные default autonomy, разные gates, разные KB content. Но **схема как описывается каталог** — одна.

Это нормально и правильно. Универсалистский каталог не работает. Schema работает.
