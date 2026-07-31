---
name: 0-hooks-minimum-sufficiency
description: Аудит и проектирование Claude Code hooks. JTBD-сценариум кластеров (A–N), протокол минимальной достаточности, принцип дублирования для надёжности, чеклист аудита 10 пунктов.
mode: PASSIVE
tags: [hooks, audit, minimum-sufficiency, jtbd-scenarium]
skills:
  on_demand: [0-keychain-audit, 2-rca-incidents, 2-hypothesis-gap-falsification]
---

**Credentials:** metadata SSOT — `heroes_harness/credentials_registry.yaml`; runtime API — `heroes_platform.credentials`; workflow — `0-credentials-manager` и metadata-only `0-keychain-audit`.

**Mode:** [PASSIVE] — принципы применяются инлайн при проектировании, чтении и рефакторинге provider-neutral `.agents/hooks/`; `.claude/settings.json` и `.codex/hooks.json` — runtime-проекции, не источники hook-логики.

## §0 Текущий production-контракт

- **Composition SSOT:** `heroes_harness/heroes_harness_workflow_ssot.yaml#hooks`.
- **Wiring registry:** `heroes_harness/scripts/setup/hooks-registry.json`; он хранит semantic policy registrations, а `register_hooks.py` создаёт provider-specific delivery.
- **Runtime sources:** только `.agents/hooks/*.py`; `.claude/hooks` и `.codex/hooks` являются aliases/projections, provider-prefixed source copies запрещены.
- **Минимум не равен числу:** нет цели `≤10`. Минимально достаточен любой набор, где каждый active policy владеет отдельным failure class или документированным reliability layer. Exact duplicate command под тем же event+matcher остаётся багом.
- **Lifecycle scenarium:** SessionStart → UserPromptSubmit → PreToolUse → PostToolUse → Stop/release описан в master SSOT через `lifecycle_contracts`; каждый active row обязан разрешаться в When / want / so-that / effect / fail policy / scoped ACK / test.
- **Provider capabilities:** Claude и Codex получают один semantic registry, но не одинаковый JSON. Codex не получает unsupported `SessionEnd`, Claude glob-matchers переводятся в Codex regex, operator label задаётся поддерживаемым `statusMessage`.
- **Operator text:** decision → violated invariant → measured evidence → one safe next action → scoped ACK. Dates/RCA/incident/PR history остаётся без сокращения в hash-checked `Provenance and incident evidence`, а не в primary runtime output.
- **Mechanical gates:**
  - `python3 heroes_harness/scripts/hooks/normalize_hook_contract_headers.py`
  - `python3 heroes_harness/scripts/hooks/validate_hook_operator_messages.py`
  - `python3 heroes_harness/scripts/harness/reconcile_hook_sources.py`
  - `python3 heroes_harness/scripts/tests/test_hooks_smoke.py`

---

## §1 Принцип минимальной достаточности (Minimum Sufficiency)

Перед созданием любого нового хука агент обязан пройти 4 условия. Если хотя бы одно не выполнено — создание блокируется.

| # | Условие | Как проверить |
|---|---|---|
| **MS-1** | Рецидив задокументирован: ≥2 инцидента в `ai.incidents.md` одного класса, declarative-правил которых недостаточно | `grep "category: <class>" [todo · incidents]/ai.incidents.md \| wc -l` → ≥2 |
| **MS-2** | Нет существующего wire-target: ни один зарегистрированный хук не покрывает этот класс отказа | `grep -l "<keyword>" .claude/hooks/*.py` + проверить в `settings.json` |
| **MS-3** | Механический эффект: хук вернёт `sys.exit(2)` (BLOCK) или `sys.exit(0)` с WARN в stderr — не просто печать/логирование | код хука в теле `main()` |
| **MS-4** | Test + escape contract соответствует роли: BLOCK gate имеет scoped `<NAME>_ACK="<reason ≥12 chars>"` и pass/block/override fixtures; WARN/observer/action доказывает fail-open и idempotence, но не обязан иметь фиктивный ACK | source under `.agents/hooks/` + focused cases in `heroes_harness/scripts/tests/test_hooks_smoke.py` or a named colocated test |

**Hard fail**: хук создан без прохождения MS-1..MS-4 → `category: hook-created-without-minimum-sufficiency-gate` в `ai.incidents.md`.

---

## §2 Принцип дублирования для надёжности (Duplication-for-Reliability)

**Антипаттерн** (выявлен до аудита 2026-06-07): один и тот же `.py`-файл зарегистрирован дважды в `settings.json` под одним event-matcher'ом. Это НЕ надёжность — это двойной вызов и двойное stderr.

**Настоящая надёжность** строится на 4 механиках — без дублирования одного файла:

| Механика | Описание | Пример |
|---|---|---|
| **R-1** | Два разных event-matcher'а для одного файла с разным риском | `source_read_before_4xx_diagnosis.py` зарегистрирован и в Write-, и в Bash-PreToolUse |
| **R-2** | Слоистые пороги (WARN at N1, BLOCK at N2) | `git_dirty_count_gate.py`: WARN=50, BLOCK=200 |
| **R-3** | Fail-open дизайн: `try/except Exception → sys.exit(0)` в Stop-хуках | `auto_commit_on_stop.py` не может заблокировать stop-event |
| **R-4** | Override ACK env (≥12 chars) как единственный escape-hatch | `DIRTY_TREE_ACK`, `OWN_BRANCH_BEAD_ACK`, etc. |

**Правило**: если в `settings.json` два объекта с одинаковым `"command"` под одним matcher — это баг, не надёжность. Удалить дубль.

---

## §3 Когда orphan-хук допустим (без регистрации в settings.json)

Файл в `.claude/hooks/` без записи в `settings.json` = orphan. Допустимо в 3 случаях:

1. **Utility helper**: файл содержит общие функции, импортируемые другими хуками (не точка входа)
2. **On-demand script**: явно помечен в шапке `# ON-DEMAND: вызывается только из Makefile/скрипта`, не из settings
3. **WIP / disabled**: помечен `# DISABLED: причина + bd-id` — временно выключен до исправления

Во всех остальных случаях orphan = долг. Добавить в Guardian improvement plan как DEBT с вердиктом: wire/delete/document.

---

## §4 Исполняемый JTBD-каталог lifecycle policies

Полная таблица активных policy не копируется в skill: её SSOT —
`heroes_harness/heroes_harness_workflow_ssot.yaml` → `hooks`. В ней обязаны
быть три поверхности:

1. `wired` — provider-neutral portable source hooks;
2. `canonical_active_nonportable` — canonical-only source hooks;
3. `runtime_adapters` — активные inline/domain adapters, которым не нужен
   искусственный wrapper в `.agents/hooks/`.

Каждая строка нанимается по одному lifecycle job и содержит:

- `event` + `matcher` — когда policy получает управление;
- `jtbd` — точный failure class в форме «когда / хочу / чтобы» через `contract`;
- `effect` — наблюдаемый механический результат;
- `policy_role` — ровно одна роль: gate, warn, observer, action или check;
- `layering_rationale` — почему этот reliability layer не поглощается другим;
- `policy_fail_ack_contracts` — точное per-policy failure behavior и реальный scoped ACK/opt-out, включая явное `none`, когда bypass нет;
- `test` — falsifying command;
- `runtime_capability` и `universal` — проекция Claude/Codex и public scope.

Source hook дополнительно получает сгенерированный header. Полный прежний
module docstring, включая даты, RCA, ссылки, цитаты, bead/PR ids и исторические
пути, сохраняется без сокращения под `Provenance and incident evidence` и
защищён SHA-256. Runtime adapter хранит provenance прямо в SSOT row или в
указанном `source`.

Проверка каталога:

```bash
python3 heroes_harness/scripts/hooks/normalize_hook_contract_headers.py
python3 heroes_harness/scripts/harness/reconcile_hook_sources.py --json
python3 heroes_harness/scripts/hooks/validate_hook_operator_messages.py
```

`normalize_hook_contract_headers.py` обязан доказать одновременно:

- каждый active registry handler разрешается в semantic policy;
- каждая semantic policy реально wired;
- нет placeholder JTBD и duplicate-only rationale;
- source header совпадает с SSOT и provenance hash;
- inline shell/domain adapters используют явный `policy` key, а не эвристику
  разбора команды.
- high-overlap Stop/delivery cohort имеет полную nearest-neighbor matrix,
  сравнивающую trigger, inspected evidence, decision, remediation и paired
  distinguishing fixture; generic lifecycle prose не является overlap proof.

## §5 Решения по историческим candidate hooks

Число hook’ов не является acceptance criterion. Candidate остаётся, переносится
или удаляется только по behavioural overlap test.

| Policy | Решение | Уникальная работа / граница |
|---|---|---|
| `userprompt_branch_bead_nudge` | keep as layered observer | Prompt-time lineage/isolation visibility покрывает research-only turns; `first_substantial_write_branch_bead_gate` единолично владеет write enforcement. |
| `skill_creation_review_gate` | keep canonical gate | Проверяет полноту skill contract/review; standards routing проверяет место и workflow документа, а не skill acceptance. |
| `reusable_script_belongs_in_skill_gate` | keep canonical gate | Владеет reusable-code placement; не подменяется standards/skill review. |
| `project_structure_guardian_check` | keep canonical check pending measured matcher change | Проверяет drift структуры; matcher можно сузить только после false-positive/latency evidence, а не по ощущению. |
| `graphql_operation_schema_match` | keep canonical gate until CI parity | Перенос в CI разрешён лишь после доказательства одинакового scope, timing, evidence и remediation до записи. |
| `oneof_input_variant_exhaustion` | keep canonical gate until CI parity | Та же migration gate: сначала behavioural parity, затем снятие runtime wiring. |
| `agents_md_reflect_propose` | keep public observer | Предлагает governance reflection; worker остаётся helper, а не второй event policy. |
| `inventory_response_format_check` | keep canonical gate | Владеет owner-visible completeness для exhaustive inventory. |
| `credential_key_alias_search` | keep canonical gate | Владеет alias-resolution failure class, отличный от secret-value detection. |
| `substantial_task_orchestrator_trigger` | keep canonical gate | Владеет отсутствием outcome/audit ролей после порога; threshold меняется только по false-positive fixtures. |

Новый candidate не получает verdict из названия или incident chronology. Нужны
две пары positive/negative fixtures и сравнение `(trigger, current evidence,
decision, remediation)`. Совпали все четыре — merge/retire. Не совпал хотя бы
один — документировать отдельный layer.

## §6 Operator message и naming contract

Runtime message строится в порядке:

```text
<DECISION> <exact_policy_id>: <current condition>.
Invariant: <system rule>.
Evidence: <current mechanically observed fact>.
Next: <one safe action>.
ACK: <scoped override or none>.
```

Правила:

- `ALLOW` обычно silent; Codex `statusMessage` — короткий present-tense label;
- primary output не содержит chronology, RCA diary, obsolete paths или
  необъяснённые bead/PR ids;
- provenance не удаляется: runtime может сослаться на неё, но не пересказывает;
- `*_gate` блокирует, `*_warn` советует, `*_observer` записывает/показывает,
  `*_action` выполняет обратимый effect, `*_check` чисто проверяет state;
- semantic `policy_id` — единственное runtime-имя. Исторические source filenames —
  compatibility keys, а не role labels; их rename допустим только через
  отдельно протестированную registry/import/profile/recipient alias migration;
- Claude и Codex — проекции одного `hooks-registry.json`; provider-specific
  source names запрещены;
- статический Codex UI может показывать `Hook N`: schema не поддерживает
  `name/displayName`; контролируемая поверхность — runtime `statusMessage`.

## §7 Production gate по JTBD-сценарию

| Gate | Фальсифицирующий вопрос | Обязательное доказательство |
|---|---|---|
| Intake | continuation создаёт новый lineage или скрывает старый? | prompt positive/negative fixtures |
| Bootstrap | startup mutates/blocks без declared contract? | adapter policy + skip/ACK test |
| Pre-action | unsafe side effect проходит или safe action false-blocked? | paired gate fixtures |
| Post-action | следующий шаг читает stale/unverified result? | result/evidence fixture |
| Delivery | final claim скрывает ticket, файлы, screenshots или payload? | owner-visible transcript fixtures |
| Provider parity | Claude/Codex исполняют разные semantics? | registry projection + reconcile |
| Distribution | public target получает dangling/private hook? | profile checksum/drift + partial install smoke |
| Live runtime | wiring green, но hook не fires? | isolated Codex live-fire, не только config smoke |

Минимальный release gate:

```bash
python3 heroes_harness/scripts/hooks/normalize_hook_contract_headers.py
python3 heroes_harness/scripts/hooks/validate_hook_operator_messages.py
python3 heroes_harness/scripts/harness/reconcile_hook_sources.py --json
python3 heroes_harness/scripts/setup/register_hooks.py --runtime both --dry-run
python3 heroes_harness/scripts/tests/test_hooks_smoke.py --json
```

Green требует `runtime_not_policy=0`, `policy_not_runtime=0`, exact lifecycle
duplicates `=0`, message chronology `=0`, полный smoke и отдельное live-fire /
distribution proof. Сам факт «тесты зелёные» без этих слоёв — false green.

## §8 Протокол агента при работе с hooks

1. **Перед созданием нового хука**: пройти §1 MS-1..MS-4. Не создавать без ≥2 инцидентов.
2. **Аудит всех источников**: запустить `reconcile_hook_sources.py`; raw command-count vs file-count не является orphan proof, потому что один policy может иметь несколько event layers, а helper — ноль registrations.
3. **Дублирование**: одна `"command"` под одним matcher = баг. Удалить дубль немедленно.
4. **Hardcoded/direct path**: заменить `/Users/.../hooks/X.py` и direct `$CLAUDE_PROJECT_DIR/.claude/hooks/X.py` на launcher `sh "${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}/.agents/hooks/run" X.py`.
5. **Missing python3**: добавить префикс — иначе хук не запустится на PATH без python3.
6. **Orphan-файл**: присвоить §3-статус в master SSOT/registry classification; отдельный legacy ledger не становится вторым composition SSOT.
7. **Рефакторинг хука**: обновить smoke fixtures в `heroes_harness/scripts/tests/test_hooks_smoke.py` в той же сессии.
8. **Перед Stop**: убедиться что `auto_commit_on_stop.py` DENY_PREFIXES актуальны.

---

## Workflow

1. Сформулировать failure-class: какой повторяющийся инцидент hook должен предотвращать.
2. Проверить §1 MS-1..MS-4 и существующие wire-targets в `.claude/hooks/`, `.claude/settings.json`, `lefthook.yml`.
3. Отнести hook к одному кластеру §4 и явно выбрать действие: keep, merge, move-to-CI, disable, delete.
4. Для любого code-change обновить smoke fixtures в `heroes_harness/scripts/tests/test_hooks_smoke.py` и запустить targeted hook smoke.
5. Для любого settings-change запустить portability check из `portable-claude-hooks`.
6. Перед delivery сфальсифицировать гипотезу "hook стал надёжнее": найти false-positive, false-negative и portability regression через `2-hypothesis-gap-falsification`.

## Input Checklist

- [ ] Список hook-файлов или конкретный hook path.
- [ ] Событие Claude Code/Codex, где hook должен срабатывать: `PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `SessionEnd`.
- [ ] Минимум два RCA/incident evidence для нового BLOCK-hook или причина, почему изменение только рефакторит existing hook.
- [ ] Текущая регистрация в `.claude/settings.json` и наличие smoke coverage.

## Output Checklist

- [ ] Вердикт по каждому затронутому hook: keep, merge, move-to-CI, disable, delete.
- [ ] Обновлённая регистрация без дублирующих command под одним matcher.
- [ ] Обновлённые smoke fixtures для block/pass/override/fail-open путей.
- [ ] Portability result: нет absolute `/Users/...` hook paths в team-shared settings.

## Outcome Checklist

- [ ] Hook снижает конкретный повторяющийся риск, а не просто добавляет шум.
- [ ] Legitimate owner/agent workflow не блокируется без ACK escape hatch.
- [ ] Main остаётся зелёным: contract validation, hook smoke и portability checks проходят.
- [ ] Owner value: команда получает меньше false-positive блокировок и меньше ручного восстановления после hook-regression.

## Reasoning Log Protocol

Фиксировать: failure-class, выбранный кластер §4, какие existing hooks проверены на overlap, почему действие минимально достаточное, какие smoke cases запускались, и результат self-falsification через `2-hypothesis-gap-falsification`.

## Связанные скилы / Related skills

- `portable-claude-hooks` — портативная регистрация hook commands без machine-local paths.
- `0-hook-self-test` — smoke discipline для hook behavior.
- `0-hooks-minimum-sufficiency` — этот audit protocol как SSOT для hook-кластеров.
- `2-hypothesis-gap-falsification` — обязательная self-falsification перед delivery.

## Owner Value

Owner value: hook-система перестаёт расти хаотично, новые BLOCK-и появляются только под доказанный рецидив, а существующие hook-и становятся проверяемыми, переносимыми и менее шумными для команды.
