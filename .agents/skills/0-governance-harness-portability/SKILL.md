---
name: 0-governance-harness-portability
description: "Use AFTER copying the Standard 0.3 governance harness into any client/partner repo, OR when auditing whether the harness is fully wired here, OR when adding/removing a hook or skill from the bundle. Runs the manifest-driven verifier: every documented hook is actually registered in settings.json on the right matcher, every hook's script-deps exist (fail-open hooks silently no-op if a dep is missing), every code-skill has skill.yaml+scripts+tests, every knowledge-skill has SKILL.md+skill.yaml. Universal — manifest-driven, no client hardcode. Triggers: «проверь обвязку», «harness wiring», «все ли хуки подключены», «verify governance harness», «скопировал обвязку клиенту», «почему хук не срабатывает», «governance copy-kit verify»."
---

**Mode:** [ACTIVE] — обязательный вызов (a) после копирования harness в новый репозиторий, (b) при добавлении/удалении хука или скила из бандла, (c) при подозрении «хук документирован, но не срабатывает». Это self-verifier комплекта Standard 0.3.

**Prod-safety & autonomy:** при обнаружении broken main / dormant-хука / drift — действуй по своему role-классу (R1 FLAG / R2 FIX / R3 ROUTE / R4 BLOCK) и принимай решения сам. SSOT — AGENTS.md §Agent role × invariant matrix + `0-agent-prod-safety-autonomy-contract`.

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit` (этот скил внешних API не вызывает — stdlib only).

# Governance harness portability — self-verifying копи-кит обвязки (Standard 0.3)

## Hired for JTBD

**Когда** я (или клиент/партнёр Рика) скопировал governance-обвязку Standard 0.3 в свой репозиторий — **хочу** одной командой получить доказательство, что **каждый** документированный хук реально зарегистрирован в `settings.json` на правильном matcher, **каждая** зависимость хука на месте, **каждый** скил отчуждаем по своему `kind` — **чтобы** обвязка реально *подключена*, а не *тихо не-подключена* (dormant-хук = governance-дыра, которую глазами не видно).

**Корневой разрыв (gap), который закрывает скил (RCA 2026-06-07):** копи-кит §5 Standard 0.3 был **рукомейнтейненным списком**. Фальсификация нашла **3 хука**, документированных как «живой mechanical-слой», но **не зарегистрированных** в `settings.json` (`docs_client_doc_gate`, `pr_bead_jtbd_ref_check`, `root_new_entry_gate`) → Pillar A/B молча не-подключены; + 4 «detachable» скила без `skill.yaml`. Рукомейнтейненная таблица **не может обнаружить собственный drift**. Этот скил делает бандл **self-verifying** — manifest SSOT + verifier, а не доверие к тексту.

## Owner value

Каждый прогон verifier'а на новом репозитории клиента/партнёра превращает «надеюсь, обвязка подключена» в «доказано: N PASS / 0 GAP ИЛИ вот точные дыры». Метрика — `gaps == 0` в CI клиента после adopt. Один источник истины (`harness-manifest.json`) → нет дрейфа между документом и реальностью.

## ⚠️ Что verifier ПРОВЕРЯЕТ и что НЕ проверяет (честный scope, RCA design-review 2026-06-07)

Verifier проверяет **wiring (подключение)**, НЕ **runtime-эффективность**:

| Проверяет (wiring) | НЕ проверяет (effectiveness) |
|---|---|
| файл хука на месте (H1) | реально ли хук БЛОКИРУЕТ нарушение на adversarial input |
| хук зарегистрирован в settings.json на нужном matcher (H2) | вызывается ли скил агентом под нагрузкой |
| зависимости хука на месте (H3) | работает ли override-env как задумано |
| хук fail-open на мусорный stdin (H4, `--smoke`) | покрывает ли matcher РЕАЛЬНОЕ имя tool в сессии |
| скил отчуждаем по kind (S2/S3) | честность `detachable: true` (grep-proxy, не AST) |

**`PASS` = хук reachable, НЕ хук effective.** Effectiveness проверяется (a) bundled-тестами каждого хука, (b) живым `PreToolUse` BLOCK, который ты наблюдаешь в реальной сессии. Не читай «N PASS» как «governance работает» — читай как «governance подключён». Roadmap: `--functional-smoke` mode с adversarial fixture per hook (named follow-up, Standard 0.3 §5.8).

## Что проверяет verifier (против `harness-manifest.json`)

| Check | Что | Какой gap ловит |
|---|---|---|
| H1 | файл хука существует | пропал файл при копировании |
| H2 | каждый `register`-target хука удовлетворён в `settings.json` (блок под event'ом с matcher, покрывающим tool, содержит команду хука; анкер по basename — без substring false-positive) | **dormant-хук** (документирован, но не wired) |
| H3 | каждый `depends_on` хука на месте | fail-open хук тихо no-op при пропавшей зависимости |
| H4 | `--smoke`: хук fail-open (мусорный stdin → exit 0) | хук падает вместо fail-open |
| S1/S2 | code-скил: `skill.yaml` + `scripts/` + `tests/` | неотчуждаемый «detachable» скил |
| S3 | knowledge-скил: `SKILL.md` (+ `skill.yaml` с `detachable: true\|partial`) | knowledge-скил без манифеста |
| P1 | affordance/config-скрипты на месте (`make_worktree.py`, `root_structure_router.py`, …) | пропавший генератор-аффорданс |

## Workflow

1. **Прогнать verifier** на текущем репо:
   ```bash
   python3 .agents/skills/0-governance-harness-portability/scripts/verify_harness_wiring.py --repo-root . --smoke
   ```
   Скопировать markdown-отчёт **в тело** assistant-сообщения (не в свёрнутом Bash-чипе). `gaps == 0` → обвязка wired. exit 1 → есть дыры.
2. **Для каждого GAP** — закрыть по типу:
   - `H2 dormant` → добавить хук в `.claude/settings.json` под нужный event/matcher (см. колонку `register` в manifest).
   - `H3 dep missing` → скопировать недостающий скрипт/конфиг (граф зависимостей в `harness-manifest.json`).
   - `S2/S3` → добавить `skill.yaml`/`scripts`/`tests` по `kind`.
   - `P1` → скопировать affordance-скрипт.
3. **Re-run** до `0 GAP`.
4. **Добавляешь хук/скил в бандл** → сначала строка в `harness-manifest.json`, потом re-run (manifest = SSOT, не код verifier'а).
5. **Falsify** через `2-hypothesis-gap-falsification`: гипотеза «обвязка полностью wired» → gap table → verdict.

## Cycle-end GUARD — verifier вызывается в цикле, не только вручную (pr-rick-a9on)

**Проблема:** этот verifier `[ACTIVE]`, но был **dormant** (1 span / 60 days) — никто не запускал его в конце цикла
работы. Закрыто Stop-хуком `.claude/hooks/harness_guardian_check.py` (Path B — wire existing, auditor verdict 78%
vs 12% за новый дублирующий skill). Hook **оркеструет этот verifier** (`verify_harness_wiring.py --json` → gaps==0)
+ `make graphify-doctor` + branch/bead discipline + decision-log/graphify exercised, печатает 4-row вердикт на Stop.

- **Канон guardian-скила = этот skill** (`0-governance-harness-portability`); hook — тонкий cycle-end вызов, НЕ новый
  verifier. Триггер сборки/использования harness-компонента — skill `0-heroes-harness-mirror-guardian §GUARD`.
- **Phase 1 WARN** по умолчанию (advisory print, exit 0); промоушн к BLOCK (`HARNESS_GUARDIAN_BLOCK=1`) после baseline.
- Override: `HARNESS_GUARDIAN_ACK="<reason ≥12 chars>"`. Eval-фикстуры: `scripts/test_hooks_smoke.py::test_harness_guardian_check`.

## Адаптация под не-Heroes стек (честная отчуждаемость)

Текущая adoption-поверхность бандла предполагает: `bd`/beads (Pillar A), Claude Code `.claude/settings.json` PreToolUse (механический слой), `credentials_manager` (для API-скилов). Для клиента на другом стеке:

- **Без `bd`:** `make worktree BEAD=<external-ticket-id> SLUG="..."` — BEAD может быть Jira/Linear id; slug задаётся явно.
- **Cursor/Codex (не Claude Code):** PreToolUse-хуки Claude Code-specific; декларативный слой (AGENTS.md инварианты) переносится, механический backstop требует адаптера под `.cursor/rules/` (named roadmap, Standard 0.3 §5.8).
- **Уровни adoption** (L1 декларативно → L4 full kit) — Standard 0.3 §5.0 roadmap.

Не заявляй «обвязка universal для любого стека» без этой адаптации — overclaim (см. честный scope выше).

## Hard fail (RCA-инцидент)

- Хук документирован в Standard 0.3 / copy-kit, но verifier показывает `H2 GAP` (dormant) и не закрыт → `category: harness-hook-documented-but-dormant`.
- Скил заявлен detachable в бандле, но verifier показывает `S2 GAP` → `category: harness-skill-not-detachable`.
- Новый хук добавлен в `settings.json`, но не в `harness-manifest.json` (manifest drift) → `category: harness-manifest-drift`.
- `verify_harness_wiring.py` показал GAP, agent заявил «обвязка готова» без re-run до `0 GAP` → `category: harness-verify-skipped`.
- Заявление «N PASS = governance работает» (registration прочитан как enforcement) → `category: wiring-pass-read-as-enforcement`.

## Self-falsification gate

После прогона применить `2-hypothesis-gap-falsification`: гипотеза «harness полностью wired, копия клиента подключится». Gap table (Ожидание | Факт | Δ):
1. `verify_harness_wiring.py --smoke` → `gaps == 0`? (H1-H4, S1-S3, P1)
2. `pytest tests/ -q` зелёный? (verifier сам протестирован)
3. `harness-manifest.json` покрывает все хуки из Standard 0.3 §5.1? (нет manifest drift)

Verdict `confirmed` только когда все 3 строки `match`. Помни: verdict про **wiring**, не про runtime-enforcement.

## Input / Output / Outcome

Формат — AGENTS.md §Макрос {io-checklist}.

### Input checklist
| ✓ | Что на входе | Факт |
|---|---|---|
| ✅ | `harness-manifest.json` (SSOT бандла) | путь к manifest |
| ✅ | целевой репо с `.claude/settings.json` | `--repo-root` |

### Output checklist
| ✓ | Что на выходе | Факт |
|---|---|---|
| ✅ | отчёт verifier (PASS/WARN/GAP + disclaimer) | markdown в чат + exit code |
| ✅ | все GAP закрыты | re-run → `0 GAP` |

### Outcome checklist
| ✓ | Какая выгода владельца | Факт / как проверено |
|---|---|---|
| ✅ | копия обвязки у клиента реально подключена | `gaps == 0` в его CI после adopt |
| ✅ | нет drift между документом и реальностью | manifest SSOT + verifier в CI |

## Reasoning Log Protocol

Лог: какие GAP найдены (по типу H1-H4/S/P), как закрыты, результат re-run, `pytest`. Каждый GAP — строкой `G01 — {что не сошлось}`.

## Канонические источники

- SSOT бандла: `.agents/skills/0-governance-harness-portability/harness-manifest.json`
- Verifier: `scripts/verify_harness_wiring.py` (+ `tests/`)
- Standard 0.3 Project Governance Harness §5 Copy kit
- `0-detachable-skill-packaging` — контракт отчуждаемости (этот скил его dogfood'ит)

## Связанные скилы

- `0-detachable-skill-packaging` — уровни отчуждаемости + классификатор
- `0-document-creation-guard`, `0-root-structure-guardian` — Pillar B хосты
- `2-hypothesis-gap-falsification` — self-falsification gate
- `5-land-to-main-mechanical` — довести обвязку до origin/main

## Авторство

Скил создан Ильёй Красинским как часть governance-обвязки Standard 0.3. Развивается синхронно с `harness-manifest.json` и AGENTS.md.
