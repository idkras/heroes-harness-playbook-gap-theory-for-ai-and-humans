---
title: "Пример: Task Types для типовой мобильной игры на Unity"
version: v1
type: example
date_added: 2026-04-23
status: draft
---

# Пример — как могут выглядеть Task Types для мобильной F2P игры на Unity

> Шестой пример. Намеренный контраст с AAA Console: **та же индустрия (gamedev)**, но **совершенно другая модель** — мобильная free-to-play игра на Unity, маленькая команда, быстрые циклы, **live ops dominant после релиза**.
>
> Цель — показать, что даже внутри одной индустрии каталоги задач могут принципиально отличаться, если меняется бизнес-модель.
>
> Читается за 20 минут.

---

## 1. Контекст продукта

Возьмём типовую **free-to-play (F2P) мобильную игру на Unity** — например, casual puzzle, hyper-casual или mid-core RPG. После софт-лонча активная live ops модель.

**Технологический контекст**:
- **Engine**: Unity (LTS), C# scripting
- **Команда**: 8-25 человек — программисты + game designer + 2-3 артиста + 1 producer + live ops manager
- **Платформы**: iOS (App Store) + Android (Google Play)
- **Backend**: лёгкий — Firebase / PlayFab / Unity Game Services / собственный микросервис на Node/Go
- **Аналитика**: Unity Analytics + GameAnalytics + AppsFlyer + custom events
- **Monetization**: ads (Unity Ads / IronSource / AppLovin) + IAP + сезонные battle pass + gacha (для жанров)
- **Live ops**: ежедневные / еженедельные события, сезоны, A/B-тесты, remote config
- **Ритм релизов**: hotfix — дни, fearure update — 2-4 недели, major content drop — месяц-два
- **Цикл**: первый soft launch через 6-12 месяцев, затем **бесконечная live ops**

**Главные отличия от AAA Console**:
- **Цикл бесконечный**, не 4-7 лет → потом релиз. После soft launch — постоянная live ops.
- **Маленькая команда**, многие роли совмещены или outsourced.
- **Monetization — first-class concern** на каждой задаче. Многие задачи буквально про монетизацию.
- **Multi-device fragmentation**: тысячи моделей Android устройств, разные iPhone-поколения. Тестирование на представительной выборке.
- **A/B testing — стандартная практика**, почти на каждой важной фиче.
- **Store submission** — relativeно lighter чем cert на консоли, но всё равно release-blocker.
- **Player retention метрики** — Day-1, Day-7, Day-30 retention, ARPDAU, conversion to payer — это **продуктовые метрики**, по которым принимаются решения.
- **Ads SDK integration** — отдельный класс работы, постоянно меняющиеся SDK.

---

## 2. Что меняется в классификации задач для mobile F2P

Те же три цели (autonomy, gates, context), но особенности:

- **Autonomy выше, чем в AAA Console.** Маленькая команда, быстрые циклы, более agile-like поток. Много A2-A3.
- **Gates другого характера**: ad SDK compliance, store guidelines, A/B test rigor, retention impact, monetization metrics, multi-device performance.
- **Context — heavy на live ops паттерны**: economy balance, retention loops, monetization funnels, store metadata, ad placement best practices.

И ключевое: **monetization** живёт буквально в каждом типе задачи. Новый game mode → как монетизируется? UI change → не сломали ли мы IAP-конверсию? Performance optimization → не убили ли мы ad revenue из-за ad-blocker'ов? Это сквозной concern.

---

## 3. Схема Task Type — та же

```yaml
task_type:
  name
  detection: { triggers, file_signals }
  blast_radius: { players_affected, reversibility, cross_team }
  default_autonomy
  required_context
  required_gates
  typical_decomposition
```

Доменно-специфичные поля: `monetization_impact`, `retention_impact`, `ab_test_required`.

---

## 4. Каталог Task Types для типовой mobile F2P игры

12 типов, отражающих типичную работу команды на Unity F2P.

### Type 1. Gameplay feature / new mechanic

**Что**: новая игровая механика или режим. Например, новый puzzle-type, новый combat mode, новый mini-game.

**Default autonomy**: **A2** (programmer + designer review).

**Required context**: design pillars, player progression docs, balance constants, related systems.

**Required gates**:
- Frame rate на target devices (low-end Android included)
- Не сломали retention (если фича сильно меняет core loop — A/B test обязателен)
- Tutorial / onboarding adapted
- Localization keys заведены

**Typical decomposition**: prototype → playtest → balance pass → integration → tutorial → A/B rollout.

---

### Type 2. UI / UX change

**Что**: изменения в UI — новый экран, изменение существующего флоу, кастомизация анимаций интерфейса.

**Default autonomy**: **A2-A3** (cosmetic — A3, structural flow change — A2).

**Required gates**:
- Multi-resolution test (от 4:3 iPad до 21:9 Android phones)
- Localized text не ломает layout
- Accessibility (touch target sizes)
- Performance (UI updates в frame budget)

**Особенность**: **UI важнейший touchpoint для monetization**. Каждый UI change по факту может повлиять на конверсии. Если фича близка к store / IAP — A/B test обязателен.

---

### Type 3. Asset integration

**Что**: новые ассеты — текстуры, 3D модели, sprites, аудио, анимации.

**Default autonomy**: **A2-A3** (если стандарты соблюдены).

**Required gates**:
- Размер билда (mobile games — sensitive к download size)
- Память (загруженные ассеты влезают на low-end)
- Atlasing / compression корректные
- Lazy loading работает

**Особенность**: **mobile size budget** жёстче чем desktop. Каждый MB в билде — потенциальная потеря установок. App Store / Google Play штрафуют за большой размер (требуют Wi-Fi для загрузки).

---

### Type 4. Performance optimization

**Что**: оптимизация для **low-end devices** — старые Android, бюджетные смартфоны. Frame rate, battery drain, thermal throttling.

**Default autonomy**: **A2** (но требует профилирования на конкретных устройствах).

**Required gates**:
- Profile на reference low-end devices
- Battery drain test (не должен расти)
- Thermal test (не throttle до критики после 15 минут)
- Memory peak в лимитах

**Особенность**: low-end Android — реальная аудитория в emerging markets. Оптимизация под них = retention в этих регионах.

---

### Type 5. Monetization change

**Что**: изменения в IAP, ads placement, pricing, гача-вероятностях, battle pass.

**Триггеры**: «изменить цену…», «добавить IAP package», «новый ad placement», «новая drop rate».

**Default autonomy**: **A1-A2** (всегда product / monetization team review).

**Required gates**:
- A/B test обязателен для значимых изменений
- Compliance с store guidelines (Apple / Google strict про IAP)
- Compliance с regional regulations (gacha law в Japan, China, Korea, etc.)
- Финансовый impact projected (estimated ARPDAU change)
- Реверсируемость через remote config (мгновенный rollback если плохо)

**Особенность**: **самый sensitive класс задач**. Ошибка → revenue drop сразу видим. Поэтому много gates, строго A/B testing.

---

### Type 6. Live ops event / season

**Что**: ограниченное по времени contentное событие. Halloween event, Christmas, summer season, special collaboration.

**Default autonomy**: **A2** (по знакомому шаблону).

**Required gates**:
- Time-zone correctness (event запускается одновременно во всём мире или по local time?)
- Server config готов
- Все ассеты доставлены через CDN до старта
- Push notification scheduled
- Rollback план при проблемах

**Особенность**: live ops events — **повторяющийся шаблон**. Команды делают много похожих, KB должен иметь template event flow.

---

### Type 7. A/B test setup

**Что**: настройка A/B теста — на новой фичи, изменении цен, на UI варианте.

**Default autonomy**: **A2** (но требует data analyst review на metrics).

**Required gates**:
- Statistical power рассчитан (sample size adequate)
- Метрики decision-criteria определены **до запуска**
- Контрольная группа есть
- No interaction with other simultaneous tests
- Длительность теста определена

**Особенность**: **A/B testing — самостоятельная дисциплина**. Без правильной statistics результаты ничего не значат. Часто требует data analyst или специалиста по экспериментам.

---

### Type 8. Backend / remote config change

**Что**: изменения через remote config — экономика, цены, drop rates, feature flags. **Без выкатки клиента**.

**Триггеры**: «изменить цены», «увеличить drop rate», «выключить фичу X для отдельного сегмента».

**Default autonomy**: **A2-A3** для config changes (не code).

**Required gates**:
- Validation на staging (config корректен)
- Phased rollout (5% → 25% → 100%)
- Monitoring: ключевые метрики не упали
- Rollback plan (предыдущий config сохранён)

**Особенность**: **самая частая задача** в активной live ops фазе. Каждый день — какие-то tweaks. AI здесь хорош (changes небольшие, низкий риск, обратимо мгновенно).

---

### Type 9. Analytics / event tracking

**Что**: добавление нового события трекинга, изменение существующего, dashboard updates.

**Default autonomy**: **A2** (но качество событий важно).

**Required gates**:
- Event schema документирован
- Не дубль с существующим событием
- PII не утекает в analytics (privacy compliance)
- Dashboard обновлён
- QA сходство теста и продакшна (события приходят корректно)

**Особенность**: **garbage in — garbage out**. Плохие события в analytics → плохие решения. Требует строгости в naming, schema, validation.

---

### Type 10. Store compliance / submission

**Что**: подготовка к store submission — App Store / Google Play. Metadata, screenshots, описания, privacy labels, ad-related disclosures.

**Default autonomy**: **A2** для metadata, **A1** для compliance issues.

**Required gates**:
- App Store Review Guidelines compliance
- Google Play Policy compliance
- Privacy labels корректны (Apple Privacy Nutrition Label)
- IDFA / GAID handling корректен (consent UI)
- Ad SDK disclosures корректны

**Особенность**: **store reject** = задержка на дни-недели. Особенно критично для time-sensitive contents (event launch).

---

### Type 11. Bug fix

**Что**: фикс бага — gameplay, crash, monetization blocker, store reject issue.

**Default autonomy**: **A2** для обычных, **A1** для critical / monetization-blocking.

**Required gates**:
- Воспроизводится → исправлено → не воспроизводится
- Regression test
- Crash-free rate metric improvement (измеряется в production via Crashlytics)

**Особенность**: **mobile game crashes** — измеряемые в percent (Crashlytics, Firebase). 99%+ crash-free rate — нормальный target. Каждое decimal point — много пользователей.

---

### Type 12. Ad SDK integration / update

**Что**: интеграция нового ad network'а, обновление существующего SDK, изменение ad placement strategy.

**Default autonomy**: **A2** (но требует тестирования на реальных рекламах).

**Required gates**:
- SDK не увеличивает crash rate
- Ad performance metrics (eCPM, fill rate) reasonable
- User experience не страдает (ads не блокируют critical paths)
- Mediation работает корректно (waterfalls и bidding)

**Особенность**: ad SDKs **ужасно качества** часто. Падают, тянут память, конфликтуют между собой. **Много времени уходит** на их укрощение.

---

## 5. Worked example — запуск сезонного Battle Pass

Реалистичная задача:

> «Запускаем Summer Season — battle pass на 6 недель. Премиум tier $9.99, 50 уровней наград. Эксклюзивные cosmetics, новый game mode "Beach Tournament", лидерборд с топ-100 наград. Запуск 1 июня».

Для типовой mobile F2P это **2-3 месяца работы** небольшой команды:

| # | Work unit | Type | Зависимости | Default autonomy |
|---|---|---|---|---|
| 1 | Game design: структура battle pass (50 tiers, награды) | (design) | — | manual |
| 2 | Backend: модель battle pass progress | Type 8 (backend) | depends on #1 | A2 |
| 3 | UI: экран battle pass + анимации | Type 2 (UI) | depends on #2 | A2 |
| 4 | IAP: purchase flow battle pass premium | Type 5 (monetization) | depends on #2 | A1 |
| 5 | Cosmetic assets: 50 уникальных награды | Type 3 (assets) | — (parallel, art team) | A2 |
| 6 | New game mode "Beach Tournament" implementation | Type 1 (gameplay) | depends on game core | A2 |
| 7 | Leaderboard backend + UI | Type 8 (backend) + Type 2 (UI) | depends on #6 | A2 |
| 8 | Onboarding tutorial для battle pass (для новых) | Type 2 (UI) + Type 1 | depends on #3 | A2 |
| 9 | Push notification system: prompts на ключевых tier | Type 8 (backend, push infra) | depends on #2 | A2 |
| 10 | Localization: 12 языков для UI и описаний | Type 2 + Type 10 | depends on #3, #6, #7 | A3 |
| 11 | Analytics events: tier reached, IAP, mode plays | Type 9 (analytics) | depends on #2, #6 | A2 |
| 12 | A/B test: вариант с 30 vs 50 tiers (для будущих сезонов) | Type 7 (A/B test) | depends on #2 | A2 |
| 13 | Remote config: server-side контроль времени запуска | Type 8 (config) | depends on #2 | A2 |
| 14 | Performance: новые ассеты не убивают low-end | Type 4 (perf) | depends on #5 | A2 |
| 15 | Store metadata update (новые скриншоты, видео) | Type 10 (store) | depends on #3, #6 | manual |
| 16 | Submit билд в App Store + Google Play (за 2 недели до launch) | Type 10 (store) | depends on #1-#15 | manual |
| 17 | Pre-launch QA pass на reference devices | (QA) | depends on #16 | manual |
| 18 | Monitor launch day: dashboards, alerts | (live ops) | depends on launch | manual |
| 19 | Day-1 hotfix readiness | Type 11 (bug fix) on standby | — | A1 |

Видно сразу:
- **Параллельность** ассетов (#5) и кода (#1-#14)
- **External dependencies** на art team (#5)
- **Store submission timing** (#16) — критическая контрольная точка, **за 2 недели** до launch
- **A/B test** идёт параллельно (#12) для калибровки следующих сезонов
- **Monetization (#4) на A1** — нельзя ошибиться
- **Большая часть на A2** — типичный live ops темп
- **Manual работы** — game design, store metadata, QA, monitoring

Это **2-3 месяца** для маленькой команды.

---

## 6. Что становится видно

**(1) Live ops цикл — основной режим работы.** В отличие от AAA Console (где основное — pre-release development), в мобильной F2P **80% жизни продукта** — это live ops. Каталог типов это отражает: backend config, A/B test, live ops event, monetization change.

**(2) Monetization — сквозной concern.** Каждый тип в каталоге так или иначе пересекается с monetization. UI change → не сломал IAP. Gameplay feature → как монетизируется. Asset → не вырос ли download size (и не упали ли установки).

**(3) A/B testing — first-class.** В AAA Console A/B testing редкий. Здесь — стандартная практика. Methodology должна это recognize.

**(4) Remote config заменяет деплой.** Многие изменения **не требуют сборки**. Поменять цены, drop rates, feature flags — через config. Это **уникальное** свойство mobile F2P (и live service games). AI здесь — высокая autonomy, обратимо моментально.

**(5) Store gates — другого характера, чем cert.** Apple / Google review строгие, но не такие тяжёлые как platform cert. Зато **более частые** (каждый билд).

**(6) Multi-device — другая фрагментация.** В AAA Console ~3 платформы. На mobile — тысячи Android устройств + 10+ iPhone-моделей. Тестирование на представительной выборке — обязательно.

**(7) Команда меньше, темп быстрее.** 8-25 человек vs 100-500 в AAA. 2-3 недели цикл vs годы. Это **другой ритм работы**, methodology должна работать в обоих.

---

## 7. Что отличается от AAA Console (внутридоменные различия)

Сравнение mobile F2P vs AAA Console — **внутри индустрии gamedev**:

| | AAA Console | Mobile F2P |
|---|---|---|
| Команда | 100-500 человек | 8-25 человек |
| Цикл до релиза | 3-7 лет | 6-12 месяцев |
| Живёт после релиза | DLC изредка | **Постоянная live ops** |
| Тип монетизации | Premium (purchase) | F2P (IAP + ads) |
| Ad SDKs | Обычно отсутствуют | First-class класс работы |
| A/B testing | Изредка | Постоянно |
| Remote config | Минимум | Доминирующий способ изменений |
| Cert | Тяжёлая (TRC/TCR/Lotcheck) | Легче (App Store / Google Play) |
| Frame budget | 16.67 / 33.33 ms на консоли | Variable, зависит от device tier |
| Memory budget | Fixed на консоли | Variable, нужно target low-end |
| Asset quality | Cinematic AAA | Mobile-acceptable |
| Tools work | ~50% | ~20-30% |
| Multi-discipline на задачу | 5-10 ролей | 2-4 ролей |

**Ключевой вывод**: **gamedev — не один домен**. Mobile F2P и AAA Console принадлежат одной индустрии, но **task types сильно различаются**. Из 12 AAA Console типов в mobile F2P переходят **частично 4-5** (gameplay feature, performance, asset, bug fix, localization). Остальные специфичны для одной модели или другой.

---

## 8. Что отличается от всех предыдущих (5 примеров)

Расширенная таблица по 6 доменам:

| | Webmobile | Payment | FX | 1С | AAA Console | Mobile F2P |
|---|---|---|---|---|---|---|
| Доминирующий A | A2-A3 | A1-A2 | A1 | A1-A2 | Mixed | **A2-A3** |
| Цикл changes | Часы-дни | Дни-недели | Недели-месяцы | Дни-месяцы | Месяцы-годы | **Дни-недели** |
| Live ops | Continuous deploy | Continuous | N/A (instances) | Periodic | DLC + service | **Dominant** |
| A/B testing | Иногда | Минимум | Не применимо | Минимум | Редко | **First-class** |
| Remote config | Иногда | Иногда | Минимум | N/A | Редко | **Dominant способ изменений** |
| Monetization concern | Опционально | Core | Не applicable directly | Не applicable | Pre-release фокус | **Первоклассный сквозной** |
| Cert / store | None | Light | Regulatory | Light | Heavy | **Medium** |
| Player metrics | UX metrics | Transaction success | Trade execution | N/A | Reviews / Sales | **Retention, ARPDAU, IAP conversion** |
| Memory profile | Server-side | Server-side | Hardware-fixed | Server-side | Console-fixed | **Multi-device variable** |

**Главное наблюдение через 6 примеров**: каждый раз каталог меняется радикально. Mobile F2P оказался **наиболее похож на webmobile SaaS**, чем на AAA Console — потому что обе модели continuous-deploy + retention-driven.

То есть **бизнес-модель (subscription / F2P / premium / regulatory) определяет каталог сильнее, чем технологический стек**.

---

## 9. Что это значит для методики

**(1) Внутри одной индустрии каталоги отличаются.** AAA Console и Mobile F2P — gamedev оба, но business model разводит их task types. Methodology не должна предлагать «gamedev catalog» как один.

**(2) Live ops — отдельный класс типов.** Появляется в mobile F2P, в webmobile partly, в payment partly (если live tweaking есть). Methodology может dедликat «live ops zones», где правила другие.

**(3) Monetization concern — сквозной**, как compliance в payment / FX. Methodology не должна делать его «отдельным типом», но требовать что **каждый тип в monetization-heavy product** имеет monetization gate.

**(4) A/B testing — отдельная дисциплина**. Methodology должна давать affordance для A/B test workflow: setup, statistics, decision criteria, rollout.

**(5) Remote config — путь к высокой автономии без риска.** В mobile F2P остановка через config — обратима мгновенно. Этот **самый высокий уровень автономии** возможен **благодаря** instant rollback. Methodology может это recognize: «обратимые изменения → высокая autonomy».

**(6) Business model > tech stack.** Pаботают похожие подходы для webmobile SaaS и mobile F2P (continuous, retention-driven), несмотря на разный stack. И разные подходы для AAA Console и Mobile F2P, несмотря на одну индустрию. **Это диктует фрейм классификации**.

---

## 10. Главный месседж после 6 примеров

Через шесть **сильно разных** примеров (web, payment, FX, 1С, AAA, mobile F2P):

1. **Schema task type — universal.** Поля одни и те же.
2. **Каталоги — radically domain-specific.** Из 72 типов в 6 доменах общих — единицы.
3. **Business model влияет сильнее tech stack.** Mobile F2P ближе к webmobile, чем к AAA Console.
4. **Specific concerns доминируют классификацию**: latency (FX), compliance (payment), métadata (1С), cert (AAA), monetization (mobile F2P), UX (webmobile).
5. **Default autonomy — domain trait, не organization trait.** Domains с reversible changes → высокая autonomy. Domains с irreversible или regulated → низкая.

Это окончательное подтверждение — методика **не предписывает каталог**, она даёт **схему наполнения каталога** под конкретный domain × business model × org capability.
