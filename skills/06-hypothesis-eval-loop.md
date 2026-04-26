---
name: hypothesis-eval-loop
description: "Use when a change to the system (skill, protocol, AGENTS.md rule, MCP config, automation) needs before/after proof that it actually reduced gaps, effort, or incidents and increased operator value. Trigger phrases: 'докажи что стало лучше', 'before/after', 'проверь на реальной задаче', 'прогони eval', 'измерь эффект изменения', 'regression check', 'A/B на скиллах', 'стало ли лучше'. Output MUST include: таблица гипотез (hypothesis, metric, baseline, target, falsification criterion), Baseline snapshot, Treatment snapshot, Delta table, Verdict (confirmed / partially / falsified), and Learning record. §0 macro applies: every ID must include human-readable name via ` — `."
---

# Hypothesis Eval Loop

## Hired for JTBD — задача, которую решает этот скилл

Когда инженер или менеджер вносит изменение (новый скилл, новое правило, новую конфигурацию), нужна замкнутая цепочка доказательства, что это изменение реально улучшило систему — а не просто выглядит зелёным на глаз. Скилл нанимается для количественной проверки гипотезы before/after на реальных задачах.

**Назначение:** замкнутый цикл доказательства, что изменение в системе реально улучшило метрики — а не просто «выглядит зелёным».

**Отличие от `2-hypothesis-gap-falsification`:** тот скилл проверяет *один claim* (ожидание → реальность → геп). Этот скилл проверяет *эффект изменения* на реальной задаче/инциденте, измеряя before/after количественно.

## §0 — Macro ID + подпись (наследуется из AGENTS.md)

Голые `H01`, `M01`, `B01` без подписи — **hard fail**. Формат: `H01 — {гипотеза кратко}`, `M01 — functional_gap_score`, `B01 — baseline snapshot id`.

## §1 — Intake: выбор задачи или инцидента

Источники для eval:

| Источник | Где взять | Когда использовать |
| --- | --- | --- |
| Реальный инцидент | `ai.incidents.md` | Изменение чинит известный инцидент |
| Реальная задача из .beads | `bd list` / `bd show {id}` | Изменение улучшает workflow |
| User scenario (ручной) | Оператор описывает сценарий | Новый скилл или правило |
| Tier-A eval pack | `.agents/skills/0-align-skill-name-and-trigger-to-jtbd/references/tier-a-eval-packs.md` | Регрессия существующего скилла |

**Обязательно:** задача должна быть *реальной* — не выдуманной, не упрощённой. Если из `ai.incidents.md`, цитировать `incident_id — {title}`.

## §2 — Таблица гипотез: формулировка гипотезы

Перед любым измерением — таблица гипотез:

| H-ID | Гипотеза (что утверждаем) | Метрика | Baseline (ожидание) | Target | Критерий фальсификации |
| --- | --- | --- | --- | --- | --- |
| `H01 — {кратко}` | После изменения X, метрика Y улучшится | `M01 — {metric_name}` | измерим | ≤ / ≥ / = target | Если metric ∉ [target_range] → falsified |

**Допустимые метрики:**

| M-ID | Метрика | Источник | Ideal |
| --- | --- | --- | --- |
| `M01 — functional_gap_score` | `evaluate_outcome_zero_gap.py` → `functional_gap_score_zero_is_best` | praxis_platform/pulseai_mcp/scripts/ | 0 |
| `M02 — user_effort_steps` | `evaluate_outcome_zero_gap.py` → `user_effort_steps_required_after_automation_zero_is_best` | praxis_platform/pulseai_mcp/scripts/ | 0 |
| `M03 — handoff_readiness` | `evaluate_outcome_zero_gap.py` → `handoff_readiness_score_one_is_best` | praxis_platform/pulseai_mcp/scripts/ | 1 |
| `M04 — gaps_found_count` | `2-hypothesis-gap-falsification` → gap table row count (severity ≥ 3) | Manual count | 0 |
| `M05 — incidents_regression` | Новые записи в `ai.incidents.md` после изменения | grep count | 0 |
| `M06 — eval_pass_rate` | skill-creator `grading.json` → pass count / total | skill-creator agents/grader | 1.0 |
| `M07 — delivery_quality` | `evaluate_outcome_zero_gap.py` → `delivery_quality_proxy_score_one_is_best` | praxis_platform/pulseai_mcp/scripts/ | 1 |
| `M08 — operator_effort_0_5` | `усилие человека (0–100)` из таблицы ожиданий (среднее) | 2-hypothesis-gap-falsification | 0 |
| `M09 — custom` | Любая кастомная метрика, описанная в таблице гипотез | Описать source | Описать target |

## §3 — Baseline measurement

**Прогоняем задачу БЕЗ изменения.**

1. Зафиксировать git state: `git rev-parse HEAD` → `B01 — baseline commit {short_sha}`
2. Прогнать задачу/инцидент через текущую систему
3. Собрать метрики из таблицы гипотез
4. Сохранить snapshot:

```
Baseline snapshot B01 — {описание}
  commit: {sha}
  task/incident: {id — title}
  metrics:
    M01 — functional_gap_score: {value}
    M02 — user_effort_steps: {value}
    ...
  evidence: {ссылки на логи, screenshots, stdout}
  timestamp: {ISO 8601}
```

**Hard fail:** baseline без evidence (логи, stdout, скриншоты). Голое число без пруфа = не считается.

## §4 — Apply change

1. Внести изменение (новый скилл, правка AGENTS.md, правка .mdc, etc.)
2. Зафиксировать: `git diff --stat` → что именно изменилось
3. Записать: `T01 — treatment commit {short_sha}`

## §5 — Treatment measurement

**Прогоняем ТУ ЖЕ задачу/инцидент на изменённой системе.**

1. Та же задача, тот же input, те же метрики
2. Собрать snapshot (формат как в §3, но с prefix `T01`)
3. Если задача требует runtime — обязателен runtime evidence (§2.5 из `2-hypothesis-gap-falsification`)

## §6 — Delta analysis

| H-ID | Метрика | Baseline | Treatment | Delta | Verdict |
| --- | --- | --- | --- | --- | --- |
| `H01 — {кратко}` | `M01 — {name}` | {baseline_value} | {treatment_value} | {delta} | confirmed / partially / falsified |

**Правила verdict:**

| Условие | Verdict |
| --- | --- |
| Все метрики в таблице гипотез достигли target | **confirmed** |
| ≥50% метрик достигли target, остальные улучшились но не достигли | **partially confirmed** |
| Хотя бы одна метрика ухудшилась | **falsified** |
| Метрики не изменились (delta ≈ 0) | **falsified** (изменение не имеет эффекта) |

## §7 — Learning record

Независимо от verdict, записать:

### Если confirmed:
- Merge change (или рекомендовать merge)
- Записать в `.auto-memory/` feedback: `Rule: {что подтвердилось}; Evidence: {delta table}; Scope: repo-canon`
- Обновить Tier-A eval pack если изменение затрагивает скилл

### Если falsified:
- Revert change (или рекомендовать revert)
- Записать в `ai.incidents.md` WHY: `incident: hypothesis {H01} falsified; root cause: {почему не сработало}`
- Предложить альтернативную гипотезу

### Если partially confirmed:
- Записать что сработало, что нет
- Вернуться к §4 с уточнённым изменением (iterate)
- Max 3 итерации, потом — escalate к оператору

## §8 — Integration with existing skills

| Этап | Какой skill вызывать | Зачем |
| --- | --- | --- |
| §1 Intake | `2-rca-incidents` | Если source = инцидент, взять hypothesis table оттуда |
| §2 Таблица гипотез | `2-hypothesis-gap-falsification` | Формат таблицы ожиданий и таблицы гепов |
| §3/§5 Measurement | `evaluate_outcome_zero_gap.py` | Количественные метрики |
| §3/§5 Measurement | `skill-creator` grader agent | Если eval = trigger/quality скилла |
| §5 Runtime | `2-hypothesis-gap-falsification` §2.5 | Runtime evidence gate |
| §6 Delta | `2-gap-theory-extension-validate` | Если нужна gap theory classification |
| §7 Learning | `2-rca-incidents` | Если falsified → записать инцидент |
| §7 Learning | `1-task-completion-persistence` | Зафиксировать результат в .beads |

## §9 — A/B comparison mode (skill vs skill)

Для сравнения двух версий скилла:

1. **Skill A** = текущая версия (baseline)
2. **Skill B** = новая версия (treatment)
3. Прогнать одни и те же eval cases из `evals.json` (skill-creator формат)
4. Для каждого case: собрать grading (pass/fail per expectation)
5. Aggregate: `benchmark.json` формат из skill-creator

```
A/B Summary:
  Skill A pass rate: {x}%
  Skill B pass rate: {y}%
  Delta: {y-x}%
  Flaky evals (high variance): {list}
  Non-discriminating evals (both pass): {list}
  Verdict: B is better / A is better / no significant difference
```

## §10 — Continuous regression check

Когда использовать: после merge любого изменения в AGENTS.md, core-auto.mdc, или tier-2+ скилл.

1. Взять Tier-A eval pack для затронутых скиллов
2. Прогнать 3 positive + 2 negative промпта
3. Если хоть один positive не trigger или negative trigger → regression detected
4. Записать в `ai.incidents.md`

## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)

При каждом исполнении этого скилла агент ОБЯЗАН вести reasoning log в чате с таблицей решений. §0 macro: все ID с подписью. Hard fail без reasoning log.

## Owner value

Каждое исполнение скилла приносит owner value: доказательство, что изменение систему реально улучшило (а не просто выглядит зелёным), предотвращение регрессии в production, quantified feedback для следующей итерации. Value_per_touch: one eval = one decision backed by data = уверенность при merge или revert.

## Связанные скилы

- `2-hypothesis-gap-falsification` — формат таблицы ожиданий и таблицы гепов
- `2-rca-incidents` — источник реальных инцидентов для eval
- `2-gap-theory-extension-validate` — gap theory classification для delta analysis
- `1-task-completion-persistence` — фиксация результатов в .beads
- `skill-creator` — grading agent для skill quality eval

## Appendix: шаблон полного отчёта

```markdown
# Hypothesis Eval Loop Report

## Intake
- Source: {incident / task / scenario}
- ID: {id — title}
- Change under test: {что именно меняем}

## Таблица гипотез
| H-ID | Гипотеза | Метрика | Baseline target | Treatment target | Falsification |
| --- | --- | --- | --- | --- | --- |

## Baseline (B01)
- Commit: {sha}
- Metrics: ...
- Evidence: ...

## Treatment (T01)
- Commit: {sha}
- Change: {git diff --stat}
- Metrics: ...
- Evidence: ...

## Delta
| H-ID | Metric | Baseline | Treatment | Delta | Verdict |
| --- | --- | --- | --- | --- | --- |

## Learning
- Verdict: confirmed / partially / falsified
- Action: merge / revert / iterate
- Memory: {что записать}
- Next: {следующий шаг}
```


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
