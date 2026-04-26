---

name: persuasion-belief-change
description: "Use when facing resistance from teams/clients/stakeholders or designing persuasion strategy. Identifies barriers via REDUCE framework (Reactance, Endowment, Distance, Uncertainty, Corroborating Evidence), chooses approach (listening > arguing, deep canvassing, trials/pilots), avoids pushing tactics, integrates with Standard 8.0 (protective reactions) and 8.1 (organizational change). Trigger phrases: \"сопротивление команды\", \"how to change mind\", \"работа с возражениями\", \"убеди stakeholder\"."
---

# Persuasion and Belief Change Skill

**Skill Type:** Advising · Change · Resistance  
**When to Use:** When facing resistance from teams, clients, or stakeholders; when designing persuasion strategies; when applying 8.0 protective reactions or 8.1 organizational change  
**Based on:** [Standard 8.2 Persuasion and Belief Change]([standards .md]/6. advising · review · supervising/8.2 persuasion and belief change standard 20 feb 2026 cet by ai assistant.md)

---

## 🎯 Purpose

Apply science-backed principles from McRaney (2022) and Berger (2020) to:
1. **Understand** why facts and arguments often fail to change minds
2. **Reduce barriers** using REDUCE framework instead of pushing harder
3. **Listen more than argue** — create conditions for self-persuasion
4. **Integrate** with 8.0 (protective reactions) and 8.1 (organizational change)

---

## 📋 Core Principles (Quick Reference)

| Source | Principle |
|--------|-----------|
| **McRaney** | "You cannot talk someone into changing their mind, but you can listen them into it." |
| **McRaney** | All persuasion is self-persuasion |
| **Berger** | Don't push harder — remove barriers (catalyst analogy) |
| **Berger** | Reactance: when we push, they push back |
| **Product Heroes** | Resistance is the first step to acceptance |

---

## 🔄 REDUCE Framework Checklist

Before attempting to persuade, run through REDUCE barriers:

| Barrier | Question to Ask | Action |
|---------|-----------------|--------|
| **R — Reactance** | Am I threatening their autonomy? | Offer choices; let them persuade themselves; avoid dictating |
| **E — Endowment** | Have I shown cost of inaction? | Surface costs of status quo; frame new option as regaining a loss |
| **D — Distance** | Am I asking for too big a step? | Request smaller first step; find unsticking point |
| **U — Uncertainty** | Can they try before committing? | Offer trial, pilot, freemium, reduced upfront cost |
| **C — Corroborating Evidence** | Is one source enough? | Provide multiple reinforcing sources; concentrate in time |

---

## 📋 Deep Canvassing / Street Epistemology Checklist

When having a difficult conversation about beliefs:

- [ ] Am I asking questions instead of asserting?
- [ ] Am I curious about how they arrived at their belief?
- [ ] Am I sharing my own story (vulnerability) without pushing facts?
- [ ] Am I avoiding evaluative language?
- [ ] Am I asking: "What would change your mind?", "How confident are you (1-10)?"

---

## 🔗 Integration with Project Standards

| Task/Standard | How 8.2 Applies |
|---------------|-----------------|
| **8.0 Sales Marketing Product CJM** | Protective reactions (менеджмент, разработка, маркетинг) → use REDUCE to reduce Reactance, Endowment, Distance; avoid NLP/manipulation language (8.0 § Избегание формулировок) |
| **8.1 Organizational Change** | Ladder of changes, allies, viral k>1 → each step reduces barriers; pilots reduce Uncertainty |
| **8.0 Gradual transition** | "Change for 1-2 people first" → reduces Distance, Reactance |
| **Champion Playbook 9.0** | Socratic questions; change virus; Glue Effort; resistance as first step |
| **JTBD Scenarium** | Defensive reactions → map to REDUCE; use natural language per 8.0 |

---

## 📌 Workflow: When Facing Resistance

1. **Identify barrier(s):** R / E / D / U / C or combination
2. **Choose approach:** REDUCE technique, deep canvassing, street epistemology
3. **Avoid:** Pushing (Reactance); "рефрейминг", "техники влияния" (8.0 forbidden terms)
4. **Do:** Listen more than speak; offer trial/pilot; show cost of inaction
5. **Verify:** Check 8.2 output checklist before delivery

---

## Output

- Barrier identification (R/E/D/U/C)
- Chosen approach with rationale
- Checklist completion (REDUCE, deep canvassing)
- Integration note (8.0, 8.1, Champion Playbook if applicable)


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

3. **При задачах > 3 ходов** — сохранить лог в `[todo · incidents]/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным. См. протокол **agent-reasoning-log** в `AGENTS.md` (список навыков).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
