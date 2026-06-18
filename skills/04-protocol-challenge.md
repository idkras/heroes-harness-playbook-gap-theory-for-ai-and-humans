---

name: protocol-challenge
description: "Use when a task is complete and you need a deliberate falsification pass against the deliverable. Tests counter-evidence, weak assumptions, and hidden gaps. Based on protocol challenge methodology. Use when user says \"protocol challenge\", \"протокол челендж\", \"critical review\", \"validate\"."
---

# Protocol Challenge Skill


## Hired for JTBD

Когда агенту нужно выполнить задачу, связанную с этим скилом → owner получает результат с reasoning log, evidence-based решениями и привязкой к value.



## Overview

The **Protocol Challenge** is a mandatory self-check: deliberately try to **falsify** your conclusions and hypotheses, list what you did **not** consider, and state what would be unclear to a manager, developer, or team. It reduces overconfidence and surfaces gaps before delivery.

**Based on:** `.cursor/rules/protocol.mdc` (Протокол "Challenge"), `.cursor/rules/core-check.mdc` (Section 4. CHALLENGE PROTOCOL).

## When to Use

- **After completing a task** — before marking it done or reporting "ready".
- When the user asks: "протокол челендж", "protocol challenge", "критический анализ", "проверь по протоколу челендж", "фальсифицируй вывод".
- Before finalizing reports, analyses, or code delivery: run the challenge and document the result.

## Inputs

- **Deliverable**: What was produced (artifact, conclusion, code, document).
- **Claim**: What you claim (e.g. "Keychain keys are in order", "Both Dadata keys work").

## Instructions

### Step 1: Read what resulted

- Open and read the actual output (files, logs, script output).
- Do not rely on memory; verify content and behavior.

### Step 2: What I did not consider

- List **concrete** gaps: missing edge cases, assumptions not checked, data not verified, dependencies not updated, docs not updated.
- Be specific (e.g. "Did not check that dadata_secret_key is used by any code path", "Did not run Dadata API with the new secret").

### Step 3: What needs to be added

- What should be added so the deliverable is complete or maintainable?
- Tests, docs, error handling, logging, alignment with standards.

### Step 4: What will be unclear

- **To manager:** What decision or context is missing?
- **To developer:** What is ambiguous or undocumented?
- **To team:** What could cause misuse or rework?

### Step 5: Falsification attempt

- **Original conclusion:** State your conclusion clearly.
- **Counter-evidence:** What facts or tests could contradict it?
- **Alternative explanation:** Another plausible interpretation.
- **Revised conclusion:** Conclusion after challenge (e.g. "Still holds but only if X; need to verify Y").

### Step 6: Confidence after challenge

- Use the template: `Initial: [X]% → After Challenge: [Y]% — [reason].`
- Typical adjustment: if no real data tested or no cross-check → reduce confidence.

## Макрос «ID + человекочитаемое имя» (ОБЯЗАТЕЛЬНО)

См. канон: [`hypothesis-gap-falsification` §0](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md). В этом skill: в **Reasoning Log** и в блоке **FALSIFICATION ATTEMPT** не использовать голые `G01` / `P0` / `pr-rick-*` — только **`CODE — краткая подпись`**.

## Output Format

Write to chat in this structure:

```
🔍 CHALLENGE PROTOCOL:

📋 WHAT I DID NOT CONSIDER:
- [Item 1]
- [Item 2]

❓ WHAT NEEDS TO BE ADDED:
- [Item 1]
- [Item 2]

⚠️ WHAT WILL BE UNCLEAR:
- To manager: [point]
- To developer: [point]
- To team: [point]

🔄 FALSIFICATION ATTEMPT:
- Original conclusion: [statement]
- Counter-evidence: [evidence]
- Alternative explanation: [hypothesis]
- Revised conclusion: [statement]

📊 CONFIDENCE AFTER CHALLENGE:
Initial: [X]% → After Challenge: [Y]% — [reason]
```

## References

- `.cursor/rules/protocol.mdc` — Протокол "Challenge" (цель, варианты применения, результаты).
- `.cursor/rules/core-check.mdc` — Section 4. CHALLENGE PROTOCOL (steps, template).


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

2. **Записать строку в `ai.incidents.md`** — таблица `## Append-only trace`:

```
| {UTC date} | {skill_name} | {owner prompt ≤240} | {steering: yes/no} | {target artifact} | {reasoning bullets} | {blocking_instruction} |
```

3. **При задачах > 3 ходов** — сохранить лог в `<internal-folder>/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным. См. протокол **agent-reasoning-log** в `AGENTS.md` (список навыков).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
