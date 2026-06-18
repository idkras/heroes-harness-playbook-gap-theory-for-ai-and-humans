---
name: subagent-falsification
description: "Протокол фальсификации гипотез для субагентов. Родительский агент формулирует гипотезу ДО запуска субагента. Субагент обязан вернуть структурированный verdict (confirmed/partial/falsified). При 2+ субагентах — cross-check table с обнаружением противоречий. Trigger: запуск субагента, «проверь через субагента», «делегируй и проверь»."
---

# Subagent Falsification — протокол фальсификации для субагентов

## Hired for JTBD

Когда родительский агент делегирует задачу субагенту → убедиться, что субагент получает явную гипотезу, возвращает структурированный verdict и противоречия между субагентами обнаруживаются автоматически.

## When to use

- Запуск любого субагента (Agent tool) для проверки гипотезы
- Делегирование задачи с ожидаемым результатом
- Параллельный запуск 2+ субагентов на одну тему
- «Проверь через субагента», «делегируй проверку»

## Core route

### 1. Родитель формулирует гипотезу ДО запуска субагента

**FORBIDDEN:** запускать субагента без явной гипотезы в prompt.

```markdown
## Hypothesis for subagent
- Claim: {что мы считаем истинным}
- Expected evidence: {что субагент должен найти / проверить}
- Falsification signal: {что опровергнет claim}
```

### 2. Субагент получает гипотезу в prompt

Prompt субагенту обязан содержать:
- Гипотезу в явном виде
- Что проверять (файлы / API / runtime)
- Формат возврата (verdict + evidence)

### 3. Субагент возвращает structured verdict

```markdown
## Subagent Verdict
- Hypothesis: {повтор гипотезы}
- Evidence found: {конкретные факты из source-of-truth}
- Evidence missing: {что не удалось проверить}
- Verdict: confirmed | partially confirmed | falsified
- Reason: {почему этот verdict}
```

### 4. Cross-check table (при 2+ субагентах — ОБЯЗАТЕЛЬНО для openClaw + paperclip)

Когда задача запускается параллельно в двух sandbox (openClaw и paperclip), оркестратор (Claude Code) **обязан** сравнить результаты независимо:

| Критерий проверки | openClaw результат | paperclip результат | Совпадение | Противоречие (если есть) |
|---|---|---|---|---|
| {конкретный наблюдаемый факт} | {ответ + evidence} | {ответ + evidence} | yes / no | {описание расхождения} |

**При обнаружении противоречия:**
1. Не выбирать «кто прав» без evidence
2. Запустить третий проверочный прогон на конкретном факте
3. Или эскалировать owner с обоими ответами

### 4.1 Expectations table для субагентов

Перед запуском субагентов оркестратор выписывает ожидания в формате шкалы **0–100** (любой клик owner = минимум 50):

| Expectation ID | Что должно быть истинно | Где подтверждаться | Next action if unmet | усилие человека (0–100) | Actor |
|---|---|---|---|---:|---|
| E01 — {описание} | … | file / log / API / screenshot | конкретный шаг | 0 (агент) / 50+ (owner кликает) | agent / owner |

## Anti-patterns

| Anti-pattern | Почему плохо | Что делать |
|---|---|---|
| Субагент без гипотезы | Нет критерия оценки результата | Формулировать hypothesis перед запуском |
| «Сделай и скажи что получилось» | Нет falsification signal | Добавить expected evidence и falsification signal |
| Принять verdict субагента без evidence | Доверие без проверки | Потребовать конкретные факты в verdict |
| Игнорировать противоречия | Скрытый геп | Cross-check table обязательна |

## Hard fail conditions

1. Субагент запущен без явной гипотезы в prompt
2. Субагент не вернул structured verdict
3. При 2+ субагентах нет cross-check table
4. Противоречие обнаружено, но не разрешено и не эскалировано

## Owner value

Owner видит: какая гипотеза проверялась → какой evidence найден → verdict → при противоречиях — явная таблица, а не скрытый конфликт.

## Связанные скилы

- [`agent-reasoning-log`](.agents/skills/agent-reasoning-log/SKILL.md) — обязательный протокол reasoning log
- [`owner-prompt-capture`](.agents/skills/owner-prompt-capture/SKILL.md) — автозапись промтов owner
- [`hypothesis-gap-falsification`](.agents/skills/2-hypothesis-gap-falsification/SKILL.md) — фальсификация гипотез (основной скилл)

## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)

При каждом исполнении этого скилла агент ОБЯЗАН:

1. **Вести reasoning log в чате** — таблица решений с evidence, gaps и blocking instructions.
2. **Записать строку в `ai.incidents.md`** — таблица `## Append-only trace`.
3. **При задачах > 3 ходов** — сохранить лог в `<internal-folder>/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным.


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
