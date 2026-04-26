# Outcome Zero-Gap JTBD Transfer Standard

<!-- 🔒 PROTECTED SECTION: BEGIN -->
type: standard
standard_id: 1.6
logical_id: standard:outcome_zero_gap_jtbd_transfer
updated: 21 February 2026, CET by AI Assistant
previous version: None (initial version)
based on: [Gap Theory Standard](abstract://standard:gap_theory_standard), [Task Master Standard](abstract://standard:task_master_standard), [Registry Standard](abstract://standard:registry_standard)
integrated: [Pulse.ai MCP Standard](abstract://standard:rick_ai_mcp_standard), [TDD Documentation Standard 4.1](abstract://standard:tdd_documentation_standard)
version: 1.0
status: Draft
tags: standard, outcome, jtbd, gap-theory, handoff, transferability, real-data
<!-- 🔒 PROTECTED SECTION: END -->

---

## Цель

Сделать качество результата измеримым не через "тесты зеленые", а через полезность результата в реальном процессе:

- другой человек может взять результат и использовать `as is`;
- output закрывает input JTBD без зазоров передачи;
- пользовательские усилия на применение результата стремятся к нулю;
- результат меняет поведение процесса;
- мелкие правки стоят почти ноль.

---

## Формализм (ядро)

### 1) Вход и выход задачи

- `JTBD_in = {trigger, actor, desired_job, constraints, expected_outcome, next_handoff_step}`
- `Output_out = {artifact, runbook, real_data_evidence, decision_log, owner_next_step}`

### 2) Output Gap Function

Для каждого требуемого элемента `r_i` из `JTBD_in` задается бинарное покрытие `cov_i in {0,1}` и вес `w_i`.

`Coverage = (SUM(w_i * cov_i)) / (SUM(w_i))`

`functional_gap_score_zero_is_best = 1 - Coverage`

Критерий: `functional_gap_score_zero_is_best = 0`.

### 3) User Effort Function

`user_effort_steps_required_after_automation_zero_is_best = max(0, manual_steps - 1) + manual_decisions + context_switches + reruns_required + config_edits`

Критерий: `user_effort_steps_required_after_automation_zero_is_best = 0` (или максимально близко к нулю).

### 4) Transferability (handoff)

`handoff_readiness_score_one_is_best = (runbook + exact_command + expected_output + failure_rules + artifact_paths + owner_next_step) / 6`

Каждый компонент — 0/1.

Критерий: `handoff_readiness_score_one_is_best = 1`.

### 5) Behavior Change

`behavior_change_ratio_compared_to_manual_process = (manual_steps_before - manual_steps_after) / max(1, manual_steps_before)`

Критерий: `behavior_change_ratio_compared_to_manual_process > 0` и закреплено в процессе/чеклисте.

### 6) Cost of Minor Fixes

`estimated_fix_cost_points_zero_is_best = median(minor_fix_time_minutes)`

Критерий: `estimated_fix_cost_points_zero_is_best <= 10` минут, целевой режим `~0`.

### 7) Dopamine Proxy (операционный, не медицинский)

`delivery_quality_proxy_score_one_is_best = clamp(1 - 0.35*user_effort_normalized - 0.25*failed_run_ratio - 0.20*time_to_first_value_normalized - 0.20*estimated_fix_cost_normalized, 0, 1)`

Где:
- `user_effort_normalized = min(1, user_effort_steps_required_after_automation_zero_is_best/5)`
- `failed_run_ratio = failed_runs / max(1, total_runs)`
- `time_to_first_value_normalized = min(1, time_to_first_value_sec/300)`
- `estimated_fix_cost_normalized = min(1, estimated_fix_cost_points_zero_is_best/10)`

Критерий: `delivery_quality_proxy_score_one_is_best >= 0.8`.

---

## Критерий "Качественный результат"

Результат считается качественным, если одновременно:

1. `functional_gap_score_zero_is_best = 0`
2. `user_effort_steps_required_after_automation_zero_is_best = 0`
3. `handoff_readiness_score_one_is_best = 1`
4. `behavior_change_ratio_compared_to_manual_process > 0`
5. `estimated_fix_cost_points_zero_is_best <= 10` (цель `~0`)
6. `delivery_quality_proxy_score_one_is_best >= 0.8`
7. Для data-проектов: `real_data_export_success_rate_one_is_best = 1.0`

Если хотя бы один пункт не выполнен — фиксируется residual gap и следующий шаг закрытия.

### Дополнительный gate для MCP refactoring

Для задач по рефакторингу MCP quality считается достигнутым только если:

1. Обновлена owner-матрица в registry (`JTBD | tool | outcome | internal? | owner | decision | merge_target`).
2. Для каждой переназначенной/скрытой ручки указан merge target и сохранена совместимость full registry.
3. После изменений подтверждён реальный прогон (`real-data` + post-export gate / equivalent workflow) без регрессии.

---

## Типы проектов из todo.md и методы расчета

### A. Data Export / Diagnostics / Monitoring

Примеры из `todo.md`: #1, #7, #13, #19, #23, #24, #29, #31, #32, #33, #34, #35, #38.

Дополнительно считать:
- `RealDataCompleteness = exported_targets_ok / required_targets`
- `ScenarioCoverage = required_scenario_folders_found / required_scenario_folders`
- `ChecklistCoverage = checked_items / required_checklist_items`

Критерий: все три метрики = 1.

### B. Integration / Deployment / Automation

Примеры: #2, #4, #8, #22, #26, #30.

Дополнительно считать:
- `AutomationRatio = automated_steps / total_steps`
- `RecoveryReadiness = rollback_runbook_present * smoke_after_restart_passed`
- `OperatorIndependence = 1`, если новый оператор проходит runbook без автора.

Критерий: `AutomationRatio >= 0.8`, `RecoveryReadiness = 1`, `OperatorIndependence = 1`.

### C. Standards / Knowledge Transfer / Context

Примеры: #14, #15, #18, #25, #27.

Дополнительно считать:
- `ReconstructionSuccess = independent_replay_success / replay_attempts`
- `AmbiguityCount = unresolved_terms + missing_steps`

Критерий: `ReconstructionSuccess = 1`, `AmbiguityCount = 0`.

### D. Product / UX / Design / Research

Примеры: #5, #10, #11.

Дополнительно считать:
- `InsightToAction = accepted_actions / proposed_actions`
- `TimeToDecision = minutes_from_report_to_next_action`

Критерий: `InsightToAction >= 0.7`, `TimeToDecision` уменьшается vs baseline.

### E. Client Communication / Offers / Content

Примеры: #21, #28.

Дополнительно считать:
- `ReuseRate = reused_fragments / total_fragments`
- `ClarificationRate = followup_questions_needed / deliveries`

Критерий: `ReuseRate >= 0.8`, `ClarificationRate <= 0.2`.

### F. Engineering Quality / Incident-to-Test

Примеры: #12, #36, #37.

Дополнительно считать:
- `IncidentToGuardrail = incidents_converted_to_tests / incidents_total`
- `RegressionEscapeRate = escaped_regressions / releases`

Критерий: `IncidentToGuardrail = 1`, `RegressionEscapeRate -> 0`.

---

## Метод проверки "другой человек использует as is"

Blind Handoff Test:

1. Передать оператору только:
- путь к артефакту;
- 1 команду запуска;
- expected output/fail rules.
2. Оператор не спрашивает автора и не правит код.
3. Если оператор получил ожидаемый outcome с первой попытки:
- `handoff_readiness_score_one_is_best = 1`;
- `user_effort_steps_required_after_automation_zero_is_best = 0`.

---

## Evidence Block (обязательный формат)

```markdown
### Outcome Zero-Gap Evidence
```

```bash
# commands run
...
```

```json
{
  "functional_gap_score_zero_is_best": 0.0,
  "user_effort_steps_required_after_automation_zero_is_best": 0,
  "handoff_readiness_score_one_is_best": 1.0,
  "behavior_change_ratio_compared_to_manual_process": 0.75,
  "estimated_fix_cost_points_zero_is_best": 0,
  "delivery_quality_proxy_score_one_is_best": 0.93,
  "real_data_export_success_rate_one_is_best": 1.0,
  "residual_gaps": []
}
```

```text
artifact: <path>
```

---

## Примечание

Тесты и базовые метрики остаются важными, но в этом стандарте они считаются входом в проверку, а не финальным доказательством улучшения.
