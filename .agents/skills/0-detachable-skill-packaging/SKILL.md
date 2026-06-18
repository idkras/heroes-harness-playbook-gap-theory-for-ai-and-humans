---
name: 0-detachable-skill-packaging
description: "Use BEFORE creating a new script+test pair OR a new skill that wraps code, AND when auditing where top-level scripts/ files should be migrated. Enforces the detachable-skill contract: skill logic (scripts/ + tests/) lives INSIDE its skill folder, not in top-level scripts/, so a teammate or Rick client can copy ONE folder and run it without the whole repo. Triggers: «положи скрипт в скил», «отчуждаемый скил», «detachable skill», «куда положить этот скрипт», «скрипты живут отдельно от скилов», «передать скил другой команде/клиенту», «migrate scripts into skills», «classify scripts», «skill packaging audit»."
---

**Mode:** [ACTIVE] — Skill tool invocation обязателен ПЕРЕД (a) созданием нового пары `scripts/x.py` + `test_x.py`, (b) созданием/изменением скила который оборачивает код, (c) решением «куда положить этот скрипт». Mechanical gate `.claude/hooks/detachable_skill_packaging_gate.py` block'ит новый loose top-level `scripts/*.py` и edits existing top-level scripts, которые classifier видит как `skill-owned` / `orphan` / `legacy-oneoff` (infra остаётся разрешённой).

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit` (этот скил сам внешних API не вызывает; строка обязательна для скилов-наследников, оборачивающих API).

# Detachable skill packaging — отчуждаемый скил = код + тесты + процедура в одной папке

## Hired for JTBD

**Когда** я (или товарищ по команде / клиент Рика) хочу взять одну наработанную лучшую практику и применить её в другом проекте/репозитории — **хочу** скопировать ОДНУ папку скила и запустить её код и тесты без всего монорепозитория — **чтобы** обмениваться практиками между командами и клиентами без передачи 50 ГБ workspace и без «а ещё нужен скрипт из `scripts/`, и тест из `scripts/tests/`, и хелпер из `lib/`».

**Корневой разрыв (gap), который закрывает скил:** скрипт и его тест создаются в top-level `scripts/` ОТДЕЛЬНО от `SKILL.md`, который их описывает. Скил перестаёт быть самодостаточным → его нельзя отдать наружу → петля обмена лучшими практиками рвётся. Это integration gap (Standard 1.15): знание (`SKILL.md`) и исполнение (`scripts/`+`tests/`) лежат в разных местах, человек должен их склеить вручную.

## Owner value

**Ценность для owner (value per touch):** каждый раз когда логика скила бандлится в его папку вместо top-level `scripts/`, workspace приближается к состоянию «N отчуждаемых скилов = N передаваемых практик». Метрика — доля скилов с `detachable: true` манифестом и долей top-level `scripts/*.py` со `skill-owned` классификацией, мигрированных в свои скилы (трекается `skill_packaging_inventory.py`).

## Что такое «отчуждаемый скил» (канонический контракт)

**Этот скил НЕ декларирует новый принцип — он операционализирует уже существующий** `Detached-skill invariant` (RCA 2026-05-17, owner steering), задекларированный в [`0-skills-self-improvement` §Detached-skill invariant](.agents/skills/0-skills-self-improvement/SKILL.md). Там — declarative принцип + nightly audit (E08) + creation-gate (`skill_creation_review_gate.py`). Здесь — **механический слой**, которого там не было: контракт C15 (`scripts/` ⇒ `tests/`), активный pre-write gate против top-level утечки, `skill.yaml` манифест с уровнями отчуждаемости, классификатор миграции. Граница: тот скил — passive nightly **audit** качества; этот — active **contract + tooling** упаковки. `credentials_manager` как единственная разрешённая shared-зависимость — наследуется из того инварианта дословно (не противоречим ему).

`skill.yaml` поле **`detachable`** — ТРИ честных уровня, не bool (RCA design-review 2026-06-03: `detachable: true` как наклейка давал false confidence для скилов с API/credentials):

| Уровень | Что значит | Кто скопирует и запустит |
|---|---|---|
| `true` | zero workspace-coupling **КРОМЕ** `credentials_manager` (разрешённый единственный SSOT, доступен в team `.venv` через `pip install -e .` — см. §Detached-skill invariant): ноль прочих `<internal-component>.*`, ноль `import <internal-component>`, ноль чтений `<internal-folder>/`, ноль hardcoded `/Users/`, ноль `requires_skills` | копируешь папку + team `.venv` → `pytest` зелёный |
| `partial` | работает в любом репо, НО требует объявленных зависимостей: `requires_skills` (напр. `0-keychain-audit`) + `requires_credentials` (key NAMES) + `deps.external` (pip) | копируешь папку + ставишь deps + кладёшь ключи по списку → работает |
| `false` | жёстко связан с workspace (`import <internal-component>` ИЛИ `<internal-component>.*` кроме credentials_manager, relative read из соседних папок) — НЕ отчуждаем, кандидат на рефактор | работает только здесь |

**Запрещён overclaim:** `detachable: true` при наличии ЛЮБОГО сигнала coupling (D4) — `category: detachable-overclaim`. Честный уровень для API-скила = `partial` с заполненными `requires_*`.

Условия по уровням:

| # | Условие | Как проверить | Уровень |
|---|---|---|---|
| D1 | Вся логика скила в `<skill>/scripts/`, не в top-level `scripts/` | `ls <skill>/scripts/` | все |
| D2 | Каждому `scripts/*.py` (с логикой) — `tests/test_*.py` в папке скила | C15 в `validate_skill_contract.py` | все |
| D3 | `skill.yaml` объявляет `detachable`/`runtime`/`deps`/`entrypoints`/`tests` (+ `requires_skills`/`requires_credentials` для `partial`) | парсится `skill_packaging_inventory.py` | все |
| D4 | `detachable: true` ⇒ ноль coupling-сигналов: `import <internal-component>`, `<internal-component>.*` (**кроме** `credentials_manager` — разрешён), чтение `<internal-folder>`/`<internal-folder>`, hardcoded `/Users/` | `grep -rE "import <internal-component>\|<internal-component>(?!\.shared\.credentials_manager)\|\<internal-folder>\|/Users/" <skill>/scripts/` пусто | `true` |
| D5 | `SKILL.md` цитирует свои `scripts/` в backticks (Std 4.8 §B C14) | C14 | все |
| D6 | Транзитивные skill-зависимости объявлены в `requires_skills` (один скил редко самодостаточен) | сверить с тем, что вызывает SKILL.md | `partial` |

**Эталон `true` (gold standard):** `4-website-autodetect` — `SKILL.md` + `scripts/` + `tests/` + `pyproject.toml` + `Makefile` + `README.md` + `ci/`; stdlib + один pip (`aiohttp`). Скопировал → `pip install -e .` → работает. Честный пример `partial`: любой `4-amocrm-*` скил — `requires_skills: [0-keychain-audit]` + `requires_credentials: [amocrm_*]`.

## Каноническая структура папки

```
.agents/skills/<skill>/
  SKILL.md          # frontmatter + Mode + JTBD + Workflow + Hard fail + References
                    #   + Reasoning Log Protocol + Self-falsification + io-checklists (Std 4.8 §B)
  skill.yaml        # манифест отчуждаемости (schema_version, detachable, runtime, deps, entrypoints, tests)
  scripts/          # ВСЯ логика скила (CLI + библиотечные модули) — НЕ top-level scripts/
    __init__.py
    <tool>.py
  tests/            # test_*.py РЯДОМ с кодом (bundle) — не в top-level scripts/tests/
    test_<tool>.py
  fixtures/         # опц. тестовые данные
  README.md         # опц. для copy-paste командой/клиентом (как запустить вне repo)
```

## Когда скрипт НЕ идёт в скил (legitimate top-level `scripts/`)

Не вся логика — скил. Остаются в top-level `scripts/` (это плумбинг, не отчуждаемая практика):

- **infra**: вшито в `Makefile` / `lefthook.yml` / `.claude/hooks/*` / `.claude/settings.json` / `scripts/setup/` (например `validate_skill_contract.py`, `branch_lifecycle_sweep.py`, `check_*`, `owner_link.py`, `post_sync_bootstrap_guard.py`).
- **setup / bootstrap**: `scripts/setup/`, `scripts/git/`, `scripts/beads/`, `scripts/launchd/`, `scripts/system/`.
- **legacy-oneoff**: `scripts/temp/`, `debug_*`, `inspect_*` — кандидаты на удаление, не на миграцию.

Классификатор `skill_packaging_inventory.py` различает эти категории автоматически.

## Workflow (процедура)

**Маршрут A — создаёшь новый скрипт+тест (самый частый):**
1. Спроси: это логика конкретного скила или workspace-плумбинг?
   - плумбинг (хук/Makefile/bootstrap) → top-level `scripts/` ок, стоп.
   - логика скила → найди/создай owning-скил, шаг 2.
2. Положи скрипт в `.agents/skills/<skill>/scripts/`, тест — в `.agents/skills/<skill>/tests/test_*.py`. Никогда не в top-level `scripts/`.
3. Создай/обнови `skill.yaml` (D3). Если есть `import <internal-component>` → `detachable: false` + перечисли в `deps.workspace`.
4. Сослись на скрипт из `SKILL.md` (C14) и дай CLI-инвокацию полным путём `.agents/skills/<skill>/scripts/<tool>.py`.
5. Прогони `python3 -m pytest .agents/skills/<skill>/tests/ -q`.

**Маршрут B — аудит/миграция существующего top-level `scripts/`:**
1. `python3 .agents/skills/0-detachable-skill-packaging/scripts/skill_packaging_inventory.py --repo-root . --md report.md` → миграционная карта.
2. Для каждого `skill-owned` ряда: `git mv scripts/<x>.py .agents/skills/<owning>/scripts/<x>.py` (сохраняет историю).
3. Напиши `tests/test_<x>.py` если его не было (D2).
4. Обнови ВСЕ ссылки на старый путь (same-session ownership): `grep -rn "scripts/<x>.py" .agents/ Makefile docs/` → правка.
5. `skill.yaml` (D3) + прогон тестов + Δ-таблица (Ожидание vs Факт).

**Маршрут C — добавляешь хук-gate против рецидива:** `.claude/hooks/detachable_skill_packaging_gate.py` ловит новые top-level `scripts/*.py` со skill-логикой и edits уже существующих top-level scripts, если `skill_packaging_inventory.py` классифицирует их как `skill-owned` / `orphan` / `legacy-oneoff`. Если нужно расширить allowlist — правь его `INFRA_*` константы или wiring evidence, не хардкодь клиента.

## Hard fail (RCA-инцидент)

- Создан `scripts/<x>.py` со skill-логикой (не плумбинг) на top-level вместо `<skill>/scripts/` без `DETACHABLE_PACKAGING_ACK` → `category: skill-logic-in-top-level-scripts` + миграция в owning-скил.
- Existing top-level `scripts/<x>.py` классифицирован как `skill-owned` / `orphan` / `legacy-oneoff`, но агент продолжил его редактировать вместо triage/migration без `DETACHABLE_PACKAGING_ACK` → `category: loose-script-edited-without-packaging-triage`.
- `scripts/` dir в скиле есть, а `tests/` нет (D2 нарушен) → `category: skill-scripts-without-bundled-tests` (mechanical block: `validate_skill_contract.py` C15).
- Скил заявлен `detachable: true` в `skill.yaml`, но имеет `import <internal-component>` (D4 нарушен) → `category: detachable-claim-with-workspace-deps`.
- Миграция выполнена, но старые ссылки на `scripts/<x>.py` не обновлены (broken refs) → `category: migration-left-stale-refs` (нарушает §Same-session ownership contract).

## Self-falsification gate

После запуска применить `2-hypothesis-gap-falsification` к финалу: гипотеза «скил отчуждаем — товарищ скопирует папку и запустит». Фальсифицировать через gap table (Ожидание | Факт | Δ):
1. `ls <skill>/` показывает `SKILL.md` + `scripts/` + `tests/` + `skill.yaml`? (D1, D3)
2. `python3 -m pytest <skill>/tests/ -q` зелёный из чистого checkout? (D2)
3. `grep -rE "import <internal-component>|from scripts" <skill>/scripts/` пусто при `detachable: true`? (D4)
Verdict `confirmed` только когда все 3 строки `match`.

## Input / Output / Outcome

Формат — AGENTS.md §Макрос {io-checklist}.

### Input checklist
| ✓ | Что на входе | Факт |
|---|---|---|
| ✅ | скрипт/тест или top-level `scripts/` для аудита | путь к файлу / `scripts/` |
| ✅ | owning-скил определён (или плумбинг-вердикт) | slug скила или «infra» |

### Output checklist
| ✓ | Что на выходе | Факт |
|---|---|---|
| ✅ | логика в `<skill>/scripts/` + тест в `<skill>/tests/` | пути + `pytest -q` PASS |
| ✅ | `skill.yaml` манифест | путь к `skill.yaml` |
| ✅ | все ссылки на старый путь обновлены | `grep` пусто на stale |

### Outcome checklist
| ✓ | Какая выгода владельца | Факт / как проверено |
|---|---|---|
| ✅ | скил отчуждаем — папка копируется и работает без repo | self-falsification 3/3 match |

## Reasoning Log Protocol

Лог: какие скрипты классифицированы (skill-owned/infra/legacy/orphan), куда мигрированы, какие ссылки обновлены, результат `pytest`. Каждый Gap из self-falsification — строкой `G01 — {что не сошлось}`.

## Канонические источники (Canonical sources)

- Классификатор: `.agents/skills/0-detachable-skill-packaging/scripts/skill_packaging_inventory.py` (+ `tests/test_skill_packaging_inventory.py`).
- Контракт-валидатор C15: `scripts/validate_skill_contract.py`.
- Mechanical gate: `.claude/hooks/detachable_skill_packaging_gate.py`.
- Эталон отчуждаемого скила: `.agents/skills/4-website-autodetect/`.
- Standard 4.8 §Detachable skill packaging.

## Связанные скилы (Related skills)

- `0-align-skill-name-and-trigger-to-jtbd` — frontmatter/JTBD/симлинки.
- `0-skills-self-improvement` — ночной аудит качества скилов.
- `2-<client>-standard` — TDD для bundled тестов.
- `0-legacy-cleanup-trigger` — миграция legacy-oneoff scripts.
