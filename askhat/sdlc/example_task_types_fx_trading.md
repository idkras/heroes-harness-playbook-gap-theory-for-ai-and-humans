---
title: "Пример: Task Types для FX trading platform core"
version: v1
type: example
date_added: 2026-04-23
status: draft
---

# Пример — как могут выглядеть Task Types для ядра FX trading платформы

> Третий пример (после webmobile SaaS и payment gateway). Та же концепция Task Type — приземлена в **третью предметную область**: ядро трейдинговой платформы FX, где real-time вычисления, microsecond-latency и детерминизм являются фундаментальными требованиями.
>
> Цель — показать, как меняется каталог типов когда **latency сама становится feature**, и как **детерминизм** диктует особый подход к разработке.
>
> Читается за 20 минут.

---

## 1. Контекст продукта

Возьмём типичное **ядро FX trading платформы** — backend, который принимает котировки от провайдеров ликвидности, поддерживает order book, исполняет сделки, управляет risk-лимитами и позициями в real-time.

**Технологический контекст**:
- **Stack**: C++ или Rust для критичных путей; Java/Kotlin для менее критичных. Python почти не используется в hot path.
- **Сетевой transport**: бинарные протоколы (FIX, ITCH, кастомные), часто UDP/multicast для market data, TCP для orders
- **Co-location**: серверы в дата-центрах рядом с биржами/банками — physical latency имеет значение
- **Persistence**: всё через event log (event sourcing), для возможности replay
- **Тестирование**: backtesting на исторических данных — first-class capability
- **Regulatory**: MiFID II, Dodd-Frank, региональные требования, transaction reporting
- **SLA**: измеряется в **микросекундах**, не миллисекундах

**Главные отличия от других доменов**:
- **Latency — это feature**, не просто performance optimization. Каждая дополнительная микросекунда — потерянный спред, потерянная сделка, потерянный клиент.
- **Детерминизм** — вход → выход всегда одинаковый. Тот же ордер в тот же state book → тот же результат. Без этого нельзя ни replay, ни регресс-тестировать.
- **Аудит-каждое-действие** — каждый order, modification, fill, reject — в event log с timestamp с микросекундной точностью.
- **Backtesting** — ни одна fundamental изменение не идёт в прод без прогона на исторических данных.
- **Reproducibility** — должна быть возможность воспроизвести сценарий из прода byte-for-byte.

---

## 2. Что меняется в классификации задач для этого домена

Те же три цели классификации (autonomy, gates, context), но по сравнению с payment gateway:

- **Autonomy ещё ниже.** В payment gateway много A1, единичные A3. Здесь — **почти всё A1**, A2 — исключение для совсем некритичных вещей.
- **Gates другого характера.** В payment gateway — reconciliation, idempotency, PCI. Здесь — **latency budget**, **determinism check**, **backtest regression**, **replay correctness**, **risk consistency**.
- **Context — heavy на математику и микроструктуру рынка.** Pricing models, risk models, market microstructure rules — это **специальная область знания**, которая должна быть в KB.

И ещё одно отличие: **AI-ассистент в этом домене работает совсем иначе**. Современные AI пишут код, который функционально корректен, но **может быть катастрофически медленным**. Аллокация памяти в hot path, неоптимальные структуры данных, false sharing — AI этого не понимает без явного контекста. Поэтому **autonomy здесь ограничивается ещё и AI capability**, не только risk profile.

---

## 3. Схема Task Type — та же

Опять — схема не меняется:

```yaml
task_type:
  name
  detection: { triggers, file_signals }
  blast_radius: { users_affected, reversibility, cross_team }
  default_autonomy
  required_context
  required_gates
  typical_decomposition
```

Доменно-специфичные поля (например, `latency_budget_impact`) могут добавляться в каждой организации. Это уже **расширение схемы под домен**, но базовая структура — та же.

---

## 4. Каталог Task Types для FX trading core

12 типов, наиболее представительных для core-команды.

### Type 1. Matching engine change

**Что**: изменение в логике сопоставления ордеров. Изменение приоритетов (price/time, pro-rata), обработка self-trade, partial fills, кросс-логика.

**Триггеры**: «изменить priority для…», «новые правила matching для…», «hard fix in matching».

**Файлы**: ядро matching engine — обычно несколько ключевых файлов в hot path.

**Blast radius**: maximum (затрагивает всех клиентов и все котировки). Reversibility — нужен replay тестов на staging, прежде чем что-то откатывать.

**Default autonomy**: **A1** (это **святая святых** платформы — изменения только под senior + extensive testing).

**Required gates**:
- **Backtest на 6+ месяцах исторических данных** — обязательно
- **Determinism test** — тот же input → тот же output
- **Latency budget** не превышен (микросекундный budget на матчинг)
- **Replay test** против золотого набора сценариев
- Audit log of changes

---

### Type 2. Pricing engine change

**Что**: изменение в логике формирования котировок — спреды, агрегация ликвидности, smart order routing decisions.

**Default autonomy**: **A1** (та же категория критичности, что matching engine).

**Required context**: pricing model documentation, market microstructure rules, regulatory pricing requirements.

**Required gates**: 
- Backtest обязателен
- **P&L impact analysis** — как изменение влияет на исторический P&L
- Latency budget
- Risk team review

---

### Type 3. New currency pair / instrument

**Что**: добавление нового инструмента — например, нового FX pair (USD/CHF), индекса, экзотики.

**Default autonomy**: **A2** (рутина с хорошо известным шаблоном; но новый instrument всегда несёт risk-implications).

**Required gates**:
- Корректность tick size / lot size
- Reference data корректна (settlement, holiday calendar)
- Risk parameters настроены
- Liquidity provider mapping
- Smoke test против provider

**Typical decomposition**: reference data → matching engine config → pricing config → risk parameters → order routing → reporting.

---

### Type 4. New order type

**Что**: добавление нового типа ордера — например, peg orders, hidden orders, iceberg, TWAP.

**Default autonomy**: **A1** (новый тип ордера может выявить взаимодействия с существующими — risky).

**Required gates**:
- Comprehensive scenario test (взаимодействие со всеми существующими типами)
- Backtest с историческими сценариями
- Documentation для clients (FIX spec)
- Compliance check (некоторые типы ордеров регулируются)

---

### Type 5. Risk model update

**Что**: изменение модели риска — VaR, stress test parameters, exposure calculations.

**Default autonomy**: **A1** (риск-модели — territory of risk team + quants).

**Required gates**:
- Model validation team approval (отдельная функция)
- Backtest на историческом sample (predictive accuracy)
- Stress scenario tests
- Regulatory model approval (если требуется)
- Phased rollout с monitoring

**Особенность**: **отдельный сложный процесс «model validation»** — это часто отдельная команда внутри организации. Methodology должна это recognize.

---

### Type 6. Risk limit / circuit breaker

**Что**: изменения в risk-limit'ах — позиционные лимиты, drawdown breakers, концентрация риска.

**Default autonomy**: **A1** (и обязательно с risk officer).

**Required gates**: 
- Backtest на исторических кризисных периодах (2008, 2015 SNB, 2020 COVID, 2024-2025 events)
- Шаблонные сценарии-extreme
- Documentation для compliance

---

### Type 7. Performance / latency optimization

**Что**: уменьшение latency — устранение аллокаций в hot path, cache-friendliness, lock-free структуры, NUMA-awareness, kernel bypass.

**Default autonomy**: **A1-A2** (зависит от глубины изменений; **никогда A3+** в hot path).

**Required gates**:
- **Microbenchmarks** — обязательно, измерены p50/p99/p99.9
- **Production replay** на представительной выборке
- **Determinism** не сломан
- **Memory profile** — нет регрессий
- **Performance regression suite** в CI

**Особенность**: latency — **measured outcome**, не subjective. Если изменение ухудшило p99 на 5 микросекунд — это блокер.

---

### Type 8. Market data feed integration

**Что**: интеграция нового feed'а от провайдера ликвидности или биржи. Парсинг бинарного протокола, нормализация, sequence number handling.

**Default autonomy**: **A2**.

**Required gates**:
- Conformance test с provider'ом
- Sequence gap handling
- Snapshot + delta correctness
- Out-of-order handling
- Replay test с историческим feed sample

**Особенность**: каждый feed имеет свои quirks (sequence numbers, snapshots, recovery sessions) — KB должен документировать особенности.

---

### Type 9. FIX / protocol gateway change

**Что**: изменения в FIX-gateway или другой protocol layer — добавление полей, поддержка нового FIX-tag, мapping changes.

**Default autonomy**: **A2** (но требует careful testing — clients могут полагаться на текущее поведение).

**Required gates**:
- FIX conformance tests
- Backwards compatibility тест с существующими клиентами
- Roundtrip test: order → fill → cancel
- Audit log integrity

---

### Type 10. Compliance / regulatory update

**Что**: реакция на изменения в регуляторике — MiFID II reporting, RTS 22 enrichment, EMIR, Reg NMS, post-trade transparency.

**Default autonomy**: **A1** (всегда compliance officer + audit).

**Required gates**:
- Compliance officer review
- Audit trail end-to-end
- Reporting completeness check (все required поля заполнены)
- Hard deadline tracking (regulatory дедлайны не двигаются)

**Особенность**: пересекается с Type 5 (risk model), Type 6 (limits) и Type 9 (FIX) — часто требует изменений в нескольких местах.

---

### Type 11. Backtesting / replay infrastructure

**Что**: изменения в самой backtesting-системе — добавление новых типов тестов, оптимизация replay скорости, новые datasets.

**Default autonomy**: **A2** (это инструмент, не money-touching).

**Required gates**:
- Self-consistency: backtest of backtest (мета-проверка)
- Performance: full historical replay укладывается в SLA
- Determinism: тот же replay → те же результаты

**Особенность**: **единственный тип, где AI имеет относительную свободу**, потому что это инфраструктура для тестов, не money-touching путь.

---

### Type 12. Position keeping / settlement

**Что**: логика учёта позиций, settlement, end-of-day процедуры, корпоративные действия (для applicable instruments).

**Default autonomy**: **A1**.

**Required gates**:
- Reconciliation с provider'ами и custodians
- End-of-day correctness vs prior day baseline
- Audit completeness
- Tax/regulatory reporting consistency

---

## 5. Worked example — внедрение нового risk model

Реалистичная задача:

> «Risk team разработала новую модель stress testing для FX exposure (с учётом расширенного scope сценариев — включая пандемии и flash crash'и). Нужно внедрить в core. Срок — следующий quarter, дальше регуляторный дедлайн».

Декомпозиция:

| # | Work unit | Type | Зависимости | Default autonomy |
|---|---|---|---|---|
| 1 | Реализация новой stress test математики | Type 5 (risk model) | — | A1 |
| 2 | Backtest на исторических данных | Type 11 (backtesting infra) | depends on #1 | A2 |
| 3 | Optimization для real-time исполнения (latency budget) | Type 7 (latency) | depends on #1 | A1 |
| 4 | Интеграция в risk limit checks | Type 6 (risk limit) | depends on #1, #3 | A1 |
| 5 | Reporting изменений: новые поля для regulatory | Type 10 (compliance) | depends on #1, #4 | A1 |
| 6 | Conformance с MiFID II RTS 22 | Type 10 (compliance) | depends on #5 | A1 |
| 7 | FIX gateway: новый field в reject reason | Type 9 (FIX) | depends on #4 | A2 |
| 8 | Phased rollout: по одному asset class | (deployment process) | depends on #1-#7 | manual |
| 9 | Production monitoring: новые dashboards | (infrastructure) | depends on #4 | A2 |
| 10 | Documentation для compliance audit | (cross-cutting) | depends on #1-#7 | A2 |
| 11 | Stress scenarios: добавить в KB | Type 5 sub | depends on #1 | A2 |
| 12 | Quants peer review | (review process) | depends on #1, #2 | manual |

Видно сразу:
- **8 из 12 work units на A1** — критичность дефолтно высока
- Зависимости каскадируют от #1 (модель) — это центральный work unit
- **Компонент peer review (#12)** — это **отдельная активность**, не часть кода. Quants ставят подпись.
- **#8 phased rollout** — это **процедурный** unit, без code. Но он критически важен и должен быть явно в плане.
- **Жёсткий внешний дедлайн** (regulatory) задаёт темп.

Этот work — **полный квартал** для core team. Не неделя, не спринт.

---

## 6. Что становится видно

**(1) Default autonomy катастрофически низкая.** Из 12 типов — 9 на A1, 2 на A2, 1 на A3 (только backtesting infra). Это **физика домена**, не «команда не доверяет AI».

**(2) Backtesting — обязательный gate почти везде.** Без него нельзя оценить regression. В webmobile и payment gateway этого не было. Здесь — обязательная инфраструктура.

**(3) Latency как explicit gate.** В payment gateway latency проверяется, но это не отдельная категория. Здесь — каждое изменение проходит latency budget.

**(4) Determinism — first-class concern.** Любое изменение проверяется, что не сломан детерминизм. Без этого нельзя replay.

**(5) Peer review математики — отдельная роль.** В webmobile и payment gateway не было «model validation team». Здесь — есть. Это специальная компетенция.

**(6) AI-ассистент здесь работает иначе.** Из-за нативного hot-path-кодирования AI часто **физически не способен** написать код, который пройдёт latency budget. Поэтому AI используется в основном для:
- Backtesting infrastructure (Type 11)
- Reference data, configuration
- Documentation
- Test scenarios
- Tooling around core (admin, monitoring)

В **самом hot path** AI редко пишет финальный код — обычно генерирует прототип, человек переписывает с учётом latency.

---

## 7. Что не fits классификацию (специфичные для домена кейсы)

**Кейс 1: «Optimize end-to-end latency»** — это не один тип, а cross-cutting активность через все hot path компоненты. Включает Type 1, 2, 7, 8, 9. Это **тематическая инициатива**, не one task.

**Кейс 2: «Прохождение audit от регулятора»** — это серия compliance, document review, sometimes code changes. Это сезонная активность, не задача в обычном смысле.

**Кейс 3: «New venue / counterparty integration»** — близко к Type 8 (market data feed), но с правовым/контрактным слоем (легальные обязательства, операционная готовность). Не чисто техническая задача.

**Кейс 4: Production incident** — например, mismatched fill между нашими данными и provider'ом. Тут нужно: триаж → recovery → reconciliation → root cause → fix → backtest. Это **incident workflow**, отдельный от обычного.

---

## 8. Что отличается от двух предыдущих примеров

Сравнительная таблица, расширяющая webmobile vs payment vs FX trading:

| | Webmobile | Payment Gateway | FX Trading Core |
|---|---|---|---|
| Главный stake | UX, продуктовая ценность | Money correctness, compliance | Microsecond latency, determinism, money correctness |
| Доминирующий A-уровень | A2-A3 | A1-A2 | A1 (почти всё) |
| Stack profile | Modern web/mobile | Backend SaaS | Native (C++/Rust), low-level |
| Latency как concern | Best-effort | SLA milliseconds | **Microsecond budget**, gate per change |
| Determinism | Weak | Important | **Critical**, gate per change |
| AI capability в core | Высокая | Средняя | **Низкая** (AI не понимает hot path) |
| Backtesting | Не concept | Замкнутый сервис | **First-class infrastructure**, обязательная gate |
| Audit trail | Базовый (git, logs) | Расширенный (financial) | **Микросекундная точность**, регуляторное требование |
| Compliance | Изредка | First-class | First-class + квантовые модели |
| Внешние интеграции | Несколько | Большинство работ | Конкретные провайдеры, бинарные протоколы |
| Quant / model team | Нет | Иногда | **Обязательно** — отдельная роль с собственной gate |
| Reproducibility / replay | Не concept | Желательно | **Обязательно** для регуляторов |
| Время цикла фичи | Дни | Недели | Месяцы (с backtest и rollout) |
| Cost ошибки | UX, revenue | Деньги, compliance | Огромные деньги (микросекунды стоят миллионы), регуляторика |

**Главное наблюдение**: каталоги почти **не пересекаются** между тремя доменами. Из 12 webmobile типов в FX trading переходит **0**. Из 12 payment gateway типов в FX trading условно переходят **3** (provider integration похож на venue integration; performance optimization есть везде; compliance везде).

То есть **разные домены — реально разные миры**. Унификация через generic catalog — fundamentally невозможна.

---

## 9. Что это окончательно подтверждает для методики

**(1) Schema universal, content domain-specific** — это ещё раз подтверждено третьим примером. Schema Task Type вообще не меняется. Каталог наполнения — драматически разный.

**(2) Default autonomy distribution domain-zависит**, не organization-зависит. FX trading — везде A1. Webmobile — везде A2. Это **природа домена**.

**(3) Backtest / replay — отдельный класс gates**, который актуален только для определённых доменов (FX trading, ML systems, simulation-driven). Methodology должна давать **affordance** для этого класса, но не делать обязательным.

**(4) AI capability сама становится фактором** определения autonomy. Где AI справляется хуже (hot-path C++) — autonomy ниже **независимо от** теоретического risk profile.

**(5) Compliance, audit, regulatory — у каждого домена свой характер.** В methodology можно говорить «обязательны соответствующие gates», но конкретный characher gate'ов — domain-specific.

**(6) Размер команды и структура ролей зависят от домена.** Webmobile может работать tiny team. FX trading требует quant + risk + compliance + core dev — отдельные роли. Methodology не предписывает структуру team — она обеспечивает что **нужные роли подключены при правильных gates**.

---

## 10. Открытые вопросы (специфичные для FX trading)

**1. AI-ассистент в hot path** — методика как-то рассматривает что AI здесь физически имеет lower applicability? Может быть нужен явный концепт «AI-restricted zones»?

**2. Replay infrastructure as foundational** — это часть org layer или это нечто более фундаментальное? В webmobile replay не нужен, в FX — критичен.

**3. Quant / model validation роль** — methodology признаёт её как отдельную, или это «один из видов senior review»?

**4. Microsecond budget** — это measurable concrete gate, который можно автоматизировать. Methodology может предусмотреть schema для таких budget-gates?

---

## 11. Главный месседж после трёх примеров

Если webmobile и payment gateway показали, что **schemas universal, content domain-specific** — то FX trading усиливает это до **«контентов нет почти ничего общего»**.

Methodology, которая претендует на **общий каталог task types для всех** — будет либо webmobile-biased (и не работает в FX), либо настолько generic, что бесполезна.

Правильная methodology:
- Даёт **schema** task type
- Даёт **схему процесса** заполнения каталога под домен
- Даёт **примеры из разных доменов** для калибровки
- **Не претендует** на готовый каталог, который применим везде

Это и есть наш A57: **task types — domain content, не methodology content**. Три примера — три радикально разных каталога. Методика общая. Это работает.
