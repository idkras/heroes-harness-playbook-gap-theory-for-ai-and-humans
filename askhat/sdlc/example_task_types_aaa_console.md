---
title: "Пример: Task Types для AAA-игры на консоли"
version: v1
type: example
date_added: 2026-04-23
status: draft
---

# Пример — как могут выглядеть Task Types для AAA-игры на консоли

> Пятый пример. Принципиально другой класс разработки: AAA-игра для консолей (PlayStation, Xbox, Switch), 100-500 человек команда, 3-7 лет цикл, миллионы строк кода + сотни тысяч ассетов.
>
> Цель — показать, как меняются типы, когда **код и ассеты — параллельные пайплайны**, **frame budget — жёсткое ограничение**, и **cert от платформодержателя — release-blocker**.
>
> Читается за 20 минут.

---

## 1. Контекст продукта

Возьмём типичную AAA-игру в разработке — single-player action/adventure или action-RPG, цикл разработки 4-5 лет, релиз планируется на PS5, Xbox Series X/S, PC.

**Технологический контекст**:
- **Engine**: Unreal Engine 5 (или собственный движок, что характерно для AAA)
- **Stack**: C++ для движка и геймплея, скриптовый язык для геймдизайнерского контента (Blueprint в UE, либо Lua, либо собственный)
- **Графика**: DirectX 12, Vulkan, console-specific APIs (GNM на PS, D3D на Xbox)
- **Asset pipeline**: Maya/3ds Max/Blender → exporters → engine, Substance для текстур, Houdini для VFX/FX, ZBrush для моделей
- **Audio**: Wwise или FMOD, custom DSP
- **Версионирование**: Perforce (большие бинарные файлы плохо живут в Git)
- **Build times**: incremental — минуты, full rebuild — несколько часов
- **Multi-platform**: PS5, Xbox, PC — каждая со своими нюансами; иногда добавляются Switch, мобилки

**Главные отличия от других доменов**:
- **Frame budget**: 16.67ms (60fps) или 33.33ms (30fps) на кадр. Каждая фича обязана уложиться или быть выключена на низких пресетах.
- **Memory budget**: жёсткие лимиты на консолях. Ты не можешь «купить больше RAM» — у пользователя 16GB на PS5, точка.
- **Asset pipeline параллелен code pipeline**. Художники, дизайнеры, аниматоры производят контент одновременно с программистами. Их «commits» — это .fbx, .uasset, .png, .wav.
- **Cert от платформодержателя**. Sony (TRC), Microsoft (TCR), Nintendo (Lotcheck) — у каждого набор требований, без прохождения которых игра не выйдет на их платформе. Это release-blocker.
- **Multi-discipline на задачу**. Один gameplay feature почти всегда требует programmer + designer + animator + artist + audio + QA.
- **Tools — half the work**. Большая часть инженерной работы — это **инструменты для контент-команды**, а не сам runtime игры.
- **Очень long cycles**. Релиз — раз в 3-5 лет, не каждую неделю. Это меняет всё.

---

## 2. Что меняется в классификации задач для AAA gamedev

Те же три цели классификации, но с особенностями:

- **Autonomy** — варьирует сильно по типам. Tools — высокая. Гэплей с frame budget impact — низкая. Engine core — самая низкая.
- **Gates специфические**: frame budget regression, memory budget regression, asset budget, cert pre-check, crash rate, multi-platform parity check.
- **Context — multi-disciplinary**. KB должен включать code conventions + asset standards + design pillars + audio guidelines + animation principles. Это разные миры знаний.

И важное: **AI capability в game-разработке** — переменная и разная по дисциплинам:
- **Game code** (C++ gameplay, engine) — AI неплохо для high-level кода, плохо для performance-critical
- **Tooling и pipeline scripts** — AI хорош (Python/C# скрипты, обычная разработка)
- **Asset generation** — отдельный мир, где quality bar AAA таков, что AI image generation, AI animation и т.д. часто **не достигают** AAA quality. Хотя для prototyping и concept work — отлично.

---

## 3. Схема Task Type — та же

```yaml
task_type:
  name
  detection: { triggers, file_signals }
  blast_radius: { players_affected, reversibility, cross_discipline }
  default_autonomy
  required_context
  required_gates
  typical_decomposition
```

Доменно-специфичные поля: `frame_budget_impact`, `memory_budget_impact`, `asset_size_impact`, `cert_relevance`.

---

## 4. Каталог Task Types для AAA-игры

12 типов, представительных для console AAA.

### Type 1. Gameplay feature / new game system

**Что**: новая игровая механика или система. Например, новая система крафта, new traversal mechanic (climbing, swimming), new combat ability.

**Триггеры**: «новая способность игрока», «новая механика», «новый игровой режим».

**Файлы**: gameplay code (C++ или Blueprint), data tables, animations references, audio references.

**Blast radius**: large players (все играющие столкнутся), reversibility — depends on how integrated with progression.

**Default autonomy**: **A2** (programmer review + designer review).

**Required context**: design pillars, related systems, animation system docs, audio integration patterns, save system constraints.

**Required gates**:
- Frame budget impact measured (есть ли регресс)
- Memory budget impact
- Save game compatibility (новая фича не ломает старые сейвы)
- Multi-platform parity (работает одинаково на PS, Xbox, PC)
- QA test pass

**Typical decomposition**: gameplay code + design data + animation integration + audio + UI/HUD + tutorial + balance pass + multiple iterations.

---

### Type 2. Engine code change

**Что**: изменения в движке — rendering pipeline, physics, navigation, animation system, GPU code.

**Default autonomy**: **A1** (engine — святая святых, особенно если custom engine).

**Required context**: engine architecture docs, performance baselines, platform-specific quirks.

**Required gates**:
- **Frame budget regression test** на репрезентативных уровнях
- **Memory regression**
- **GPU performance** на каждой платформе
- **Determinism** (если затрагивает физику или гэплей-критичные системы)
- Cross-platform smoke

**Особенность**: engine changes часто затрагивают всех. Один баг в render pipeline = вся игра выглядит сломанной.

---

### Type 3. Asset integration

**Что**: интеграция нового ассета (3D модель, текстура, анимация, аудио, VFX) в игру.

**Default autonomy**: **A2-A3** (если соблюдены стандарты — почти автоматически).

**Required gates**:
- Asset budget compliance (полигоны, текстуры, animation memory)
- LOD генерация работает
- Платформенная оптимизация (compressed textures для каждой платформы)
- Validation в pipeline (нет broken references, materials корректны)

**Особенность**: это **не код**, это **контент**. Но через pipeline становится частью игры.  AI здесь — **минимальная роль** (валидация, скрипты импорта).

---

### Type 4. Performance / frame budget optimization

**Что**: оптимизация чего-то конкретного — render shader, animation update, AI pathfinding, физика.

**Default autonomy**: **A1-A2** (зависит от глубины).

**Required gates**:
- **Frame profiling до и после** на каждой платформе
- p99 frame time не вырос
- Test на минимальной целевой конфигурации (low-end console mode)
- Determinism preserved (если оптимизация затрагивает gameplay)

**Особенность**: оптимизация в console gamedev — постоянная работа. **Frame budget — не roadmap concern, а ежедневный**.

---

### Type 5. Memory optimization

**Что**: уменьшение memory footprint — компрессия ассетов, streaming improvements, leak fixes.

**Default autonomy**: **A1-A2**.

**Required gates**:
- Memory peak до и после
- На целевой консоли (limited RAM)
- No regressions в качестве (компрессия не убила текстуры)

**Особенность**: на консолях memory — fixed. Превысил — игра не запускается. Обычно отдельный класс работ перед каждым cert submission.

---

### Type 6. Platform-specific work

**Что**: что-то специфичное для одной платформы — PS5 DualSense feedback, Xbox Quick Resume, Switch portable mode optimizations.

**Default autonomy**: **A2** (но требует доступа к платформе).

**Required gates**:
- Соответствует platform guidelines (TRC/TCR)
- Не ломает другие платформы (graceful degradation)
- Тестируется на dev kit конкретной платформы

**Особенность**: **dev kit'ы** — отдельный hardware и software, на котором всё разрабатывается. Под NDA.

---

### Type 7. Tools / pipeline development

**Что**: внутренние инструменты для контент-команды. Editor extensions, asset import wizards, profilers, batch processors.

**Default autonomy**: **A3** (это не runtime — нет frame budget; ниже стек последствий ошибки).

**Required gates**:
- Tools тесты (unit + integration)
- Documentation для контент-команды
- Не сломали существующий контент при изменении пайплайна

**Особенность**: tools development — **самая большая часть** программистской работы в AAA. И **самая высокая autonomy** для AI, потому что это «обычная» разработка.

---

### Type 8. AI / NPC behavior

**Что**: behaviour trees, decision logic, animation state machines для NPC.

**Default autonomy**: **A2** (designer + programmer collab).

**Required gates**:
- Predictable behavior (NPC ведёт себя как ожидается)
- Performance: AI update в frame budget
- Не ломает balance / прохождение

**Особенность**: traditional «game AI» (поведения NPC) ≠ ML AI. Это decision trees, FSM, utility AI. Современные AI-агенты (LLM) пока **минимально** применимы для этого — потому что нужна детерминистичность и performance.

---

### Type 9. Online / multiplayer feature

**Что**: matchmaking, peer connection, lobby system, leaderboards, синхронизация состояния, anti-cheat.

**Default autonomy**: **A1** (security-critical часть, network-critical).

**Required gates**:
- Latency tests (синхронизация на типичных пингах)
- Edge cases: disconnect, reconnect, host migration
- Security audit (cheat protection)
- Cross-platform play (если поддерживается)
- Backend infrastructure ready

**Особенность**: для AAA games online компонент часто отдельная система, отдельная команда, отдельный backend.

---

### Type 10. Localization integration

**Что**: интеграция текстов на N языках, шрифты, layout adaptation, audio dub.

**Default autonomy**: **A3** для ввода текстов в существующую систему; **A1** для новых видов локализуемого контента.

**Required gates**:
- Все строки локализованы (no hardcoded strings)
- UI не ломается на длинных переводах (немецкий, финский)
- Шрифты поддерживают все символы (CJK, Cyrillic, Arabic)
- Voice-over recordings и lipsync для cinematics

**Особенность**: localization — отдельный pipeline с translators, voice actors. Game code просто потребляет результат.

---

### Type 11. Cert / compliance (TRC/TCR/Lotcheck)

**Что**: соответствие требованиям платформодержателя. Sony TRC, Microsoft TCR, Nintendo Lotcheck — стандартные требования для shipping.

**Default autonomy**: **A1** (cert failure блокирует release).

**Required gates**:
- Внутренний pre-cert test (по чеклисту платформы)
- Все required messages корректны (suspend/resume, controller disconnection, parental controls)
- Platform-specific требования (PS Trophy support, Xbox Achievements, Switch sleep mode)
- Crash-free на baseline test scenarios

**Особенность**: **внешний gate** — сама cert проводится платформодержателем. Если не прошёл — переделка + re-submission, можно потерять weeks.

---

### Type 12. Bug fix

**Что**: фикс бага. Категории: gameplay, crash, visual, audio, performance.

**Default autonomy**: **A2** для большинства; **A1** для crash-bugs или cert-blocking.

**Required gates**:
- Воспроизводится → исправлено → не воспроизводится
- Regression test добавлен в QA suite
- Cross-platform проверка (баг на одной платформе может не быть на другой)

**Особенность**: ближе к release crunch — рост темпа фиксов, риск регрессий, специальные процессы (only fixes, no new features).

---

## 5. Worked example — добавить нового playable character

Реалистичный запрос:

> «Добавим нового playable character как DLC. Уникальная боевая механика — управление временем (slow motion, rewind). Полная анимация, voice acting, балансировка. Релиз через 6 месяцев».

Это **большой проект**, типично 4-6 месяцев работы. Декомпозиция:

| # | Work unit | Type | Зависимости | Default autonomy |
|---|---|---|---|---|
| 1 | Game design doc для механики (rewind/slow-mo) | (design) | — | manual |
| 2 | Прототип механики управления временем | Type 1 (gameplay feature) | depends on #1 | A2 |
| 3 | Engine support для time manipulation (replay buffer) | Type 2 (engine) | depends on #2 | A1 |
| 4 | Performance: frame budget для time manipulation | Type 4 (perf) | depends on #3 | A1 |
| 5 | Memory: replay buffer на консоли | Type 5 (memory) | depends on #3 | A1-A2 |
| 6 | Character model (3D mesh, rig) | Type 3 (asset) | — (parallel) | A2 |
| 7 | Character animations (walk/run/combat/special) | Type 3 (asset) | depends on #6 | A2 |
| 8 | Voice acting recording + integration | Type 3 (asset) + Type 10 (localization) | depends on #1 | manual + A3 |
| 9 | Combat abilities — implementations | Type 1 (gameplay) | depends on #2, #6, #7 | A2 |
| 10 | AI/NPC reactions to time manipulation | Type 8 (NPC AI) | depends on #2 | A2 |
| 11 | Visual effects для абилок (particles, post-process) | Type 3 (asset) + engine VFX system | depends on #2 | A2 |
| 12 | Audio: SFX для time manipulation | Type 3 (asset) | depends on #2 | A2 |
| 13 | UI/HUD для нового character (resource bars, abilities) | Type 1 + UI | depends on #9 | A2 |
| 14 | Save / progression integration | Type 1 (gameplay) | depends on #9, #13 | A2 |
| 15 | Tutorial / onboarding для new character | Type 1 (gameplay) | depends on #13 | A2 |
| 16 | Balance pass (10+ iterations) | Type 1 (gameplay) | depends on #9 | A1 |
| 17 | Localization: voice + UI текст для всех языков | Type 10 (localization) | depends on #8, #13 | A3 |
| 18 | Multi-platform тестирование на всех консолях | Type 6 (platform) | depends on все code | A2 |
| 19 | DLC packaging для каждой платформы | (build) | depends on #1-#18 | A2 |
| 20 | Cert submission для каждой платформы | Type 11 (cert) | depends on #19 | manual |
| 21 | Day-1 patch (если cert найдёт issues) | Type 12 (bug fix) | depends on #20 | A1 |

Видно сразу:
- **Многодисциплинарная работа**: programmer + animator + 3D artist + VFX artist + audio designer + voice actor + designer + localization + QA
- **Параллельность**: ассеты (#6, #7) могут делаться параллельно с программистской работой (#3, #4, #5)
- **Iteration-heavy** на балансе (#16) — десятки прохождений, у дизайнеров неделями
- **Cert (#20) — внешний gate**, не зависит только от нас
- **Большая часть на A1-A2** — консолидированная, но не stripped
- **Manual работы** — game design doc, voice recording, cert submission

Это работа на **6+ месяцев** сводной команды из 15-30 человек.

---

## 6. Что становится видно

**(1) Asset pipeline параллелен code pipeline.** В webmobile/payment/FX/1С контент — не fundamentally separate concept. Здесь — **отдельный мир**, отдельные tools, отдельные роли.

**(2) Multi-discipline на единицу работы.** Один new character = programmer + 3-5 artists + designer + audio + QA + production. Methodology должна это recognize в decomposition.

**(3) Frame budget как hard gate.** Похоже на FX trading latency, но математика иная: 60fps игра имеет 16.67ms на кадр **на всё** — рендер, физика, gameplay, AI. Каждое изменение должно умещаться.

**(4) Cert как external gate.** Single methodology element, который не контролируется командой. Приходит снаружи, может откатить release. В webmobile/payment/FX/1С такого нет.

**(5) Tools как ~50% программистской работы.** Это **single highest autonomy area** в gamedev — здесь AI помогает больше всего.

**(6) AI-аssistant для AAA assets — слабая.** Хотя AI image generation, AI music и т.п. уже неплохие, AAA-quality bar таков, что они в основном для prototyping, не final. Code AI для C++ engine кода — middling. Tools AI — хорош.

**(7) Long cycles меняют всё.** Когда релиз через 4 года, frequent micro-iterations меньше актуальны. Вместо этого — long planning, milestones, vertical slices, alphas, betas. Methodology должна работать в этих cycles, не только в weekly.

---

## 7. Что не fits классификацию

**Кейс 1: «Vertical slice»** — построение полностью playable куска игры (один уровень, представляющий весь игровой опыт) для milestone review. Cross-cutting через **все типы**. Это не задача, это **проектная веха**.

**Кейс 2: «Crunch перед alpha/beta/gold»** — режим повышенной интенсивности перед milestone. Ускоренные циклы, упрощённые processes, специальные правила. Этический и health concern, но реалистичная часть AAA.

**Кейс 3: «Live service patch»** — для AAA games с live service элементом (regular content updates). Ближе к webmobile cycle, чем к main game development cycle.

**Кейс 4: «Day-1 fix после cert reject»** — особый случай Type 12, с очень коротким deadline, специальным processes.

---

## 8. Что отличается от четырёх предыдущих примеров

Расширенная сравнительная таблица:

| | Webmobile | Payment | FX Trading | 1С | AAA gamedev |
|---|---|---|---|---|---|
| Главный stake | UX | Money | Latency, money | Учётная корректность | Player experience, **performance**, **cert pass** |
| Доминирующий A-уровень | A2-A3 | A1-A2 | A1 | A1-A2 | **Varies сильно** (A1 в hot path, A3 в tools) |
| AI capability | High | Medium | Low | Low | **Mixed** (high в tools, low в engine) |
| Cycle time | Часы-дни | Дни-недели | Недели-месяцы | Дни-месяцы | **Месяцы-годы** |
| Контент vs код | Код | Код | Код | Метаданные | **Параллельные пайплайны** code + assets |
| Compliance | Опционально | First-class | First-class + quants | First-class + методология | **Cert** (внешний release-blocker) |
| Tools work | Есть | Минимум | Минимум | Платформенный (Конфигуратор) | **~50% программистской работы** |
| Multi-discipline | 2-3 ролей | 2-3 ролей | 3-4 ролей | 2-3 ролей | **5-10 ролей** на единицу работы |
| Performance ограничение | Best-effort | SLA | Microseconds | Reasonable | **16.67/33.33 ms frame** budget |
| Memory ограничение | Practically none | Practically none | Practically none | Сервер-side | **Fixed** на консоли |
| External gates | None | Few | Regulatory | 1С certification | **Cert** (Sony/MS/Nintendo) |
| Reproducibility | Не concept | Желательно | Обязательно | Желательно | Желательно (для replay) |

**Главное наблюдение**: AAA gamedev — **самый «многоосный»** домен из пяти. Здесь сложно зафиксировать «дефолтный A-уровень» — он сильно зависит от sub-domain (engine vs tools vs content vs gameplay).

Из 12 webmobile типов — **2-3 узнаваемы** (bug fix, performance optimization, cosmetic). Из payment — **минимум**. Из FX — **частично performance**. Из 1С — **минимум** (хотя workflow с asset pipeline отдалённо похож на metadata-driven).

Каталоги по-прежнему **минимально пересекаются**.

---

## 9. Что это значит для методики

**(1) Multi-discipline как first-class.** В дополнение к compliance officer / quant / методолог из других доменов, AAA gamedev добавляет: artist, animator, audio designer, level designer, VFX artist. Methodology должна явно recognize, что **task involves multiple disciplines**, и gates у каждой свои.

**(2) Asset pipeline — отдельная архитектура.** Где-то в org layer должно быть место для **asset standards, asset budgets, asset pipeline rules**. Это не код, не текст в обычном смысле, но это **тот же класс артефактов** (правила, паттерны, стандарты).

**(3) Tools layer — отдельный класс работы.** Где autonomy выше всего, AI помогает больше всего. Methodology может ясно отделять «runtime work» от «tools work» как разные mental models.

**(4) External release gates** — methodology должна явно поддерживать «gate, контролируемый извне» (cert, regulatory deadline, vendor approval). В предыдущих доменах — частично. Здесь — first-class.

**(5) Long cycles + milestones** vs **continuous flow**. Методика должна работать в обоих режимах. AAA — milestone-driven (alpha/beta/RC/gold). Webmobile — continuous deploy. Это разные ритмы.

**(6) AI capability — sub-domain dependent**, не product-dependent. В одной AAA-игре tools и runtime имеют разный AI fit. Methodology должна это понимать на уровне task type, не product level.

---

## 10. Открытые вопросы (специфичные для AAA gamedev)

**1. Asset pipeline в KB.** Как описывать в KB asset standards и budgets? Это требует other tooling, не только Markdown.

**2. Cross-discipline collaboration.** Как methodology поддерживает работу programmer + artist + designer на одной задаче? Кто owner gate?

**3. Long-cycle planning.** Methodology работает в milestone-driven контексте? Или это «out of scope» (другая methodology поверх)?

**4. Live service vs main development.** Игры с live service запускают обе модели одновременно. Methodology поддерживает обе?

---

## 11. Главный месседж после пяти примеров

Через **пять разных доменов** концепция Task Type подтвердилась как **схема, а не каталог**:

- Webmobile SaaS: feature-driven, UX-приоритет
- Payment Gateway: money correctness, compliance
- FX Trading core: microsecond latency, determinism
- 1С Development: метаданные, vendor cycle, regulatory
- AAA Console gamedev: multi-discipline, asset pipeline, cert gates

**Каталоги задач между доменами почти не пересекаются**. Из 60 типов в 5 доменах общих — единицы. Domain content вырастает из домен-специфичных constraint'ов.

**Schema того, КАК описывается тип** — единая. Поля одни и те же. Это даёт переносимость методики между доменами без переписывания.

**Methodology — это не «общий каталог практик»**. Это **общая схема + способ её наполнять под домен**. Пять примеров демонстрируют это нормально и без насилия над реальностью.

Это и есть подтверждение нашего A57: **task types — domain content, not methodology content**.

---

## 12. Что ценного добавил пятый пример

Каждый пример обогатил методологию:
- **Webmobile**: базовый каталог
- **Payment**: idempotency, reconciliation, audit-trail
- **FX**: latency-as-feature, determinism, backtesting, **AI capability gap**
- **1С**: метаданные первичны, vendor cycle, **role beyond dev team**
- **AAA gamedev**: parallel content+code pipelines, multi-discipline, **external release gates** (cert), **tools-as-half-of-work**, long-cycle planning

Эти insights не описаны в одном из пяти отдельно — они **накапливаются**. Methodology учится на разнообразии доменов.
