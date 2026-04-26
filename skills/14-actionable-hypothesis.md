---

name: actionable-hypothesis
description: "Use when analyzing Pulse.ai widgets, reports, or any analytical data to generate structured hypotheses (0th hypothesis + alternatives) with verdicts (confirmed/rejected/to be tested). Based on SGR JTBD Offer Writer 2.9 and Hypothesis Standard. Use when user says \"сформулируй гипотезу\", \"что значат эти данные\", \"гипотеза по виджету\", \"альтернативные объяснения\", \"generate hypothesis from widget data\"."
---

# 🎯 Actionable Hypothesis Skill

**Skill Type:** Analysis & Reporting
**When to Use:** When analyzing Pulse.ai widgets, reports, or any analytical data to generate hypotheses and alternative explanations
**Based on:** [SGR JTBD Offer Writer Standard](abstract://standard:sgr_jtbd_offer_writer_standard), версия 2.9, [Hypothesis Standard](abstract://standard:hypothesis_standard), [RCA Standard](abstract://standard:root_cause_analysis_standard)

---

## 🎯 Purpose

Generate actionable hypotheses (0th hypothesis and alternatives) from analytical data, following the format from Figma design template.

**JTBD, Jobs To Be Done:** When analyzing Pulse.ai widgets or reports, I want to generate structured hypotheses with verdicts (confirmed/rejected/to be tested) and alternative explanations, so that clients can immediately see conclusions in the header and understand what needs to be verified.

---

## 🧷 PraxisGPT landing review: гипотеза = тизер приёма, не саммари

**Когда:** документ — ревью лендинга по [PraxisGPT Landing Analysis Standard v1.8](mdc:[standards .md]/6. advising · review · supervising/2.0 🤖 PraxisGPT Landing Analysis Standard v1.8.md) (или тот же смысл в заголовках секций).

**Формула:** в **`Гипотеза:`** писать **не narrative-саммари**, а **тизер** — одна строка **активирующего знания**: какой **приём / техника / рычаг** (из decision psychology, копирайтинга, UX) и **узкий тезис** о том, что сделано на странице.

- **Тизер** — короткая метка, по которой читатель **узнаёт ход** и понимает, зачем читать блок доказательств ниже.
- **Саммари** — пересказ выводов своими словами без имени приёма; для гипотезы **запрещён** как основной формат.

**Примеры:**

| Вместо саммари | Тизер (приём + тезис) |
|----------------|------------------------|
| «Лендинг хорошо снимает тревогу» | «Risk reversal: гарантия 30 дней на первом экране закрывает страх «кинут»» |
| «Блок цен понятный» | «Контрастный якорь: отсечка «было/стало» в тарифах» |

**Где в документе:** строка **`Гипотеза:`** в шаблоне ниже; детали и цифры — в `Видим на…` и таблицах.

**Стандарт:** секция «Гипотеза в landing review» в PraxisGPT v1.8 (метаданные / skills).

---

## 📋 Format from Figma Design Template

Based on the Figma design template, the hypothesis format should be:

```
## [Period] · [Verdict: гипотеза подтвердилась/отклонена/требует проверки]

**Гипотеза:** [Teaser: technique/lever + narrow thesis — for landing review see § PraxisGPT landing review above; for widgets/reports: clear testable statement]

**Видим на [data source] за [period]:**
*   [Observation 1: specific data point with numbers]
*   [Observation 2: specific data point with numbers]

**Что видим прежде всего:**
*   [Key insight: what stands out most]

[Data table as proof]
```

**Example from Figma:**
```
## 1..18 дек · гипотеза подтвердилась

**Гипотеза:** есть категории товаров у которых воронка в заказ сложнее из-за специфики товара, поэтому их конверсия будет значительно ниже при высоком интересе среди пользователей.

**Видим на сделках за декабрь:**
*   среди популярных категорий товаров ниже всего конверсия в заказ у Диванов
*   выше всего у Матрасов

**Что видим прежде всего:**
*   больше всего пользователей интересуются — имеют события ecommerce в категориях: Матрасы, Диваны, Кровати, Текстиль и Подушки
```

---

## 🔄 Process

### Step 1: Extract 0th Hypothesis from Data

**Input:**
- Analytical data (widget data, report data, metrics)
- Key findings from analysis
- Patterns observed in data

**Process:**
1. Identify the main pattern or anomaly in the data
2. Formulate 0th hypothesis (primary explanation)
3. Ensure hypothesis is:
   - Specific (with numbers, metrics, examples)
   - Testable (can be verified through data or experiments)
   - Actionable (leads to specific actions if confirmed)

**Output:**
- 0th hypothesis statement
- Data points supporting the hypothesis
- Key observations from data

### Step 2: Generate Alternative Hypotheses

**Process:**
1. Think of alternative explanations for the same pattern
2. For each alternative:
   - Formulate hypothesis statement
   - Identify what data would support it
   - Identify what data would contradict it
   - Determine how to test it

**Output:**
- List of alternative hypotheses (2-3 alternatives)
- Test methods for each alternative
- Data sources needed for verification

### Step 3: Determine Verdict

**Process:**
1. Evaluate 0th hypothesis against data:
   - **Confirmed:** Data strongly supports hypothesis
   - **Rejected:** Data contradicts hypothesis
   - **To be tested:** Need additional data or experiments

2. For each alternative hypothesis:
   - Evaluate support from current data
   - Determine if it needs verification through other reports/widgets

**Output:**
- Verdict for 0th hypothesis (confirmed/rejected/to be tested)
- Status for each alternative hypothesis
- Next steps for verification (if needed)

### Step 4: Format Hypothesis Section

**Format:**
```markdown
## [Period] · [Verdict]

**Гипотеза:** [0th hypothesis statement]

**Видим на [data source] за [period]:**
*   [Observation 1: specific with numbers]
*   [Observation 2: specific with numbers]

**Что видим прежде всего:**
*   [Key insight: what stands out most]

**Альтернативные объяснения (требуют проверки):**
1. [Alternative hypothesis 1]: [what data would support it, which reports/widgets to check]
2. [Alternative hypothesis 2]: [what data would support it, which reports/widgets to check]

[Data table or proof section]
```

---

## ✅ Checklist

**Before finalizing hypothesis section:**

- [ ] If **landing review**: `Гипотеза:` is a **teaser** (named technique + narrow thesis), not a narrative summary (see § PraxisGPT landing review)
- [ ] 0th hypothesis is specific (with numbers, metrics, examples)
- [ ] 0th hypothesis is testable (can be verified)
- [ ] 0th hypothesis is actionable (leads to actions if confirmed)
- [ ] Verdict is clear (confirmed/rejected/to be tested)
- [ ] Observations are specific (with actual data points)
- [ ] Key insight is highlighted ("Что видим прежде всего")
- [ ] Alternative hypotheses are listed (2-3 alternatives)
- [ ] Test methods for alternatives are specified
- [ ] Data sources for verification are identified
- [ ] Format matches Figma template (header with verdict, hypothesis, observations, insight)

---

## 📚 Related Standards

- [SGR JTBD Offer Writer Standard](abstract://standard:sgr_jtbd_offer_writer_standard), версия 2.9 - Quality Analytical Conclusions Checklist
- [Hypothesis Standard](abstract://standard:hypothesis_standard) - Hypothesis structure and testing
- [Root Cause Analysis Standard](abstract://standard:root_cause_analysis_standard) - 5 Whys methodology
- [Factor Analysis Standard](abstract://standard:factor_analysis_standard), версия 4.0 - Factor analysis methodology

---

**Confidence: 90% → 85% — skill created based on Figma template and standards; v1.8.19 adds landing-review teaser formula; requires testing on real reports**


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
