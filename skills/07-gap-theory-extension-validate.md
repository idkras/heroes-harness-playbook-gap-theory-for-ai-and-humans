---

name: gap-theory-extension-validate
description: "Use when validating the Gap Theory Standard extension \"Agent Dunbar and Capacity of Relaxation\" against the 10 hypotheses. Produces output/outcome checklist and verification result. Use when user asks to \"проверить новый стандарт\", \"валидировать расширение теории гепов\", or \"гипотезы валидации\"."
---

# Gap Theory Extension Validation Skill

## Overview

Validates the **Gap Theory Standard 1.5** extension "Agent Dunbar and Capacity of Relaxation" (2026-02-15) against 10 explicit hypotheses. Each hypothesis has **meaningful output** (what artifact or observation) and **outcome** (what value for the user), not only formal success criteria.

**Standard path:** `[standards .md]/1. process · goalmap · task · incidents · tickets · qa/1.5 gap theory standard 26 august 2025 2325 CET by ilya krasinsky.md`  
**Section to check:** `## 🤖 Расширение: Agent Dunbar и Capacity of Relaxation` and subsection `### Гипотезы валидации расширения`.

## When to Use

- User asks to "проверить новый стандарт", "валидировать расширение теории гепов", "гипотезы валидации расширения".
- After updating the Gap Theory Standard extension: run this skill and output the result to chat.
- When designing or reviewing a Cursor/Codex skill that applies Agent Dunbar or Capacity of Relaxation: ensure the standard passes the hypotheses that matter for that skill.

## Inputs

- **Standard path** (optional): path to the Gap Theory Standard .md file. If omitted, use the path above.
- **Scope** (optional): "all" (default), or list of hypothesis IDs to check (e.g. H1, H3, H8).

## Instructions

1. **Open the standard** at the given path and locate the section "Расширение: Agent Dunbar и Capacity of Relaxation".
2. **Read the subsection "Гипотезы валидации расширения"** if present; otherwise use the table below.
3. **For each hypothesis H1–H10** (or the requested subset):
   - **Output:** What concrete artifact or observation the standard must provide (e.g. "Formula Nmax = T/(r0×G×R) and block «Как увеличить Nmax»").
   - **Outcome:** What value for the user (e.g. "Manager gets Nmax estimate without reading the full standard").
   - **Check:** Does the extension section + dictionary contain the required elements? Set ✅ (verified in text), ⏳ (requires field data or runtime check), or ❌ (missing).
4. **Output to chat** a table with columns: #, Hypothesis, Output, Outcome, Check. Then a short summary: how many ✅/⏳/❌ and what, if anything, is missing or to be done in the field.

## Hypothesis Reference (meaningful output/outcome)

| # | Hypothesis | Output | Outcome |
|---|------------|--------|---------|
| H1 | По расширению можно за ~15 мин оценить Nmax для workflow | Число Nmax + короткий список рекомендаций | Менеджер получает оценку без чтения всего стандарта |
| H2 | Формула применима к реальным логам | Подстановка T, r0, G, R → Nmax | Nmax близок к наблюдаемому порогу деградации |
| H3 | Компактный «без гепов» достаточен для скилла | Ответ агента: Plan, Gap check, Explanation, Verification | Рецензент проверяет 4 блока без знания полного раздела |
| H4 | Компактная «связность» даёт операционные метрики | Ggap, P(понимание) для текста | Можно вычислить и оценить вероятность понимания |
| H5 | Leading indicators пригодны как чеклист для ретро | 6 пунктов (бэклог, уверенность, диффы, уточнения, контекст, фиксы/откаты, переводчики) | Команда ставит галочки еженедельно |
| H6 | Протокол эксперимента однозначно определяет Nmax | Capacity profile после 3–5 дней на 1 агенте и пошагового +1 агента | Зафиксированный Nmax для домена |
| H7 | Рекомендации «как увеличить Nmax» маппятся на практики | ≥2 примера на категорию (r0, G, R, политика ревью) | Действия конкретны и выполнимы |
| H8 | Шаблон промпта порождает выход с profile + рекомендации + план | Три блока: capacity profile, рекомендации, план эксперимента | Агент выдаёт структурированный ответ по вводу workflow |
| H9 | Термины T, r, r0, G, R, Nmax, CR, E2_total, dS/dt согласованы со словарём | Нулевая путаница при кросс-чтении | Словарь и раздел расширения используют одни определения |
| H10 | Расширение не дублирует, а ссылается на полные протоколы | Явные отсылки «выше» к полным версиям | Компактные версии для скиллов, полные — в стандарте |

## Output Format

```
## Gap Theory Extension — Validation Report

[Date]

| # | Hypothesis | Output | Outcome | Check |
|---|------------|--------|---------|-------|
| H1 | ... | ... | ... | ✅/⏳/❌ |
...

Summary: ✅ N passed (in text), ⏳ M require field/runtime, ❌ K missing. [Optional: what to add or measure.]
```

## JTBD, Jobs To Be Done — задача, которую решает клиент

When someone needs to **validate the Gap Theory extension** (Agent Dunbar, Capacity of Relaxation) or **run the 10 hypotheses** against the standard, use this skill so that the result is explicit (output/outcome + check) and can be reproduced or re-run after standard edits.


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
