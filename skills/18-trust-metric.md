---
name: trust-metric
description: "Use when calculating and reporting trust level in AI agent. Tracks steering corrections and incidents. Based on core-auto OUTPUT/OUTCOME protocol. Use when user says \"trust score\", \"calculate trust\", \"report trust\", \"trust metric\"."
---

# Trust Metric — метрика доверия пользователя к агенту

**Skill Type:** Core metric, protocol integration
**When to Use:** Session start, after completing work, after user correction/steering, when documenting incidents; whenever OUTPUT/OUTCOME STATUS is written
**Based on:** [core-auto.mdc](.cursor/rules/core-auto.mdc), [next](.claude/skills/1-next/SKILL.md), RCA, Root Cause Analysis — анализ корневых причин incidents from workspace canon

---

## Purpose

**Trust (доверие)** — метрика того, насколько пользователю приходится направлять (steering) и корректировать агента. Отличается от **Confidence** (уверенность агента в своей работе).

| Метрика | Кто оценивает | Что измеряет |
|---------|---------------|--------------|
| **Confidence** | Агент | Самооценка качества работы агента (код не тестирован, данные не проверены и т.д.) |
| **Trust** | Факты сессии | Сколько steering/направлений от пользователя и инцидентов; доверие пользователя к результату |

---

## Trust Scale (0–100)

**100 единиц** = минимальный steering, нет новых инцидентов, результат доставлен без коррекций.

Каждое событие снижает Trust:

| Событие | Снижение Trust |
|---------|----------------|
| **Steering (направление):** пользователь поправил направление, сказал «не то», «сделай иначе», «уточни» | −5 до −15 (по серьёзности) |
| **Коррекция:** «исправь X», «добавь Y», «убери Z» | −3 до −10 |
| **Инцидент** (зафиксирован в ai.incidents.md per RCA, Root Cause Analysis — анализ корневых причин protocol) | −10 до −25 |
| **Freeze/abort** (пользователь остановил процесс) | −15 до −25 |
| **Много итераций** до результата (5+ значимых правок) | −5 до −15 |
| **Пропуск протокола** (не применил скилл, не сделал real request) | −5 до −15 |

**Trust не может быть < 0.**

---

## Calculation Template

```
📊 TRUST (доверие к результату):

Base: 100
Adjustments:
- Steering/коррекция: [описание] → −[N]
- Инциденты (ai.incidents): [дата, кратко] → −[N]
- Итерации (много правок): [N итераций] → −[N]

Trust: [100 − сумма] = [X] единиц
Интерпретация: [минимальный steering / умеренный steering / требуется постоянное направление]
```

---

## Output Format (MANDATORY in Chat)

**MANDATORY:** При каждом завершении работы или значимом действии агент **явно пишет** Trust в чат:

```
📊 TRUST (доверие к результату): [X] / 100
- Steering в сессии: [число событий]
- Инциденты: [если были]
- [краткая интерпретация]
```

---

## Unified Delivery Format Integration (MANDATORY)

`Trust` не должен идти отдельно от контекста доставки. В финальном ответе вместе с Trust обязательно указывать:

1. **Было/Стало** (что изменилось в задаче).
2. **JTBD-сценарий** (Когда, Роль, Хочет, Закрывает потребность, Делает, Мы хотим).
3. **Input/Output/Outcome checklists** (факт выполнения).
4. **Run Evidence** (какие команды/проверки реально выполнены и с каким результатом).

Минимум для trust-блока:
- `📊 TRUST (доверие к результату): X / 100`
- `Steering events: N`
- `Incidents: N`
- `Run evidence status: PASS/FAIL`

**FORBIDDEN:** выводить Trust без run evidence статуса.

---

## When to Apply

1. **Session start** — если есть контекст прошлой сессии (steering, инциденты), выписать текущий Trust
2. **After completing work** — всегда выписать Trust по итогам сессии
3. **After user correction** — пересчитать Trust с учётом нового steering
4. **After incident** — обновить Trust с учётом инцидента

---

## Integration

- **core-auto.mdc:** Trust добавляется в OUTPUT/OUTCOME STATUS блок; строка в таблице триггеров «After completing work»
- **next:** при вызове skill next — выписать Trust в конце
- **rca-incidents:** после записи инцидента — пересчитать Trust

---

## Related

- [core-auto.mdc](.cursor/rules/core-auto.mdc) — OUTPUT/OUTCOME, Confidence
- [core-check.mdc](.cursor/rules/core-check.mdc) — Confidence Calibration Matrix
- [next](.claude/skills/1-next/SKILL.md) — gap, outcome, HADI
- `rca-incidents` from workspace canon — инциденты
- `champion-playbook-gap-theory-agent` from workspace canon — Effort₁, Effort₂, gap types

---

**Confidence: 85% → 75% — skill создан; требует проверки на практике и уточнения коэффициентов снижения Trust**


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)

При каждом исполнении этого скилла агент ОБЯЗАН:

1. **Вести reasoning log в чате** — таблица решений с evidence, gaps и blocking instructions:

```markdown
### Reasoning Log — [дата UTC]
| # | Decision | Evidence source | Gap found | Blocking instruction | Owner value |
|---|----------|-----------------|-----------|---------------------|-------------|
```

**§0 macro (hard fail):** колонка **Gap found** — не голый `G01`, а **`G01 — краткое имя гепа`**. Любой ID (`P0`, `G01`, `E01`, `pr-rick-*`) без ` — {человекочитаемое имя}` = hard fail. См. `AGENTS.md` секция «Plain language» и `CLAUDE.md` §0.

2. Записать строку в `ai.incidents.md` таблица.

3. При задачах > 3 ходов — сохранить лог в `<internal-folder>/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным.

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
