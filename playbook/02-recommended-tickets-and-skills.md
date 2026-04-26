# Playbook: Recommended Tickets & Skills To Take Into Work

> Если ты прочитал этот репо и думаешь «с чего начать применение Gap Theory у себя» — это карта рекомендуемых первых тикетов, упорядоченная по effort × impact.

## Quadrant: с чего начать

```
                IMPACT
                 ↑ high
                 |
   Quick wins    | Strategic moves
   ─────────────────────────
   T1, T2, T3   | T7, T8, T9
                 |
   ─────────────────────────  → EFFORT
   Low effort   | High effort
                 |
   T4, T5, T6   | T10, T11
   ─────────────────────────
                 |
                 ↓ low
```

## Quick wins (low effort, high impact) — start here

### T1: Self-diagnostic week log (1-2 дня effort)

**JTBD:** найти где ты сам себе мешаешь, без external advisor.
**Method:** [`examples/05-diagnose-self-from-own-week-log.md`](../examples/05-diagnose-self-from-own-week-log.md).
**Output:** карточка «5 системных мер на следующую неделю».
**Outcome:** -10-30% glue effort на следующей неделе.
**Skills used:** `01-hypothesis-gap-falsification`, `02-rca-incidents`, `03-so-what-outcome-ladder`.

### T2: Mandatory delivery format в своих ответах (1 неделя)

**JTBD:** перестать терять качество в коммуникации с командой / клиентами.
**Method:** взять 12 mandatory sections из AGENTS.md, применять в каждой substantial доставке.
**Output:** все substantial messages в команде имеют структуру.
**Outcome:** -50% «а где результат?», -30% follow-up уточнений.
**Skills used:** `04-protocol-challenge`, `15-next-outcome-output-mapping`.

### T3: Hypothesis card перед action (1 спринт)

**JTBD:** перестать запускать эксперименты без falsification criterion.
**Method:** [`templates/03-hypothesis-card.md`](../templates/03-hypothesis-card.md) — заполнять перед каждым «давайте попробуем X».
**Output:** все эксперименты имеют baseline + threshold + critical chain.
**Outcome:** 60% эксперимент закрывается verdict'ом за 30 дней (вместо «забыли»).
**Skills used:** `14-actionable-hypothesis`, `01-hypothesis-gap-falsification`.

## Low effort но средний impact — после quick wins

### T4: Owner effort digest в каждом отчёте (1 час setup)

**JTBD:** прозрачность для владельца «что осталось ему сделать».
**Method:** [`templates/06-owner-effort-digest.md`](../templates/06-owner-effort-digest.md).
**Output:** все team-reports имеют explicit «next-action + усилие 0-100».
**Outcome:** -40% «я не знаю что делать дальше».

### T5: Quick ticket card для всех substantial задач (2-3 дня для команды)

**JTBD:** перестать терять контекст между ticket creation и start of work.
**Method:** [`templates/07-quick-ticket-card.md`](../templates/07-quick-ticket-card.md) — обязательно перед beads/Linear ticket.
**Output:** все тикеты имеют JTBD + outcome + DoD + corner cases.
**Outcome:** -30% rework, -50% «а что именно надо было сделать?».

### T6: Glossary в команде (1 день)

**JTBD:** перестать ссориться о словах когда суть одна.
**Method:** создать `docs/glossary.md` с каноничными определениями (gap, glue effort, outcome, output, JTBD, etc.). Все team-reports проверяются на соответствие.
**Output:** общий язык в команде.
**Outcome:** -25% времени в обсуждениях на «давайте уточним что мы имеем в виду».

## Strategic moves (high effort + high impact)

### T7: Orchestrator с mandatory QA + design gate (4-6 недель)

**JTBD:** systematically catch quality problems до доставки клиенту/в прод.
**Method:** [`playbook/03-orchestrator-with-qa-design-gate.md`](03-orchestrator-with-qa-design-gate.md). Реализуй 12 стадий + 4×yes generalization gate.
**Output:** оркестратор как роль (человек или AI) запущен в команде.
**Outcome:** -70% production incidents через 3 месяца.
**Skills used:** all 18 skills + 10 agents.

### T8: AI-management роли в команде (3-6 месяцев)

**JTBD:** делегировать routinely-tasks AI-агентам как junior consultants.
**Method:** [`playbook/01-ai-management-galaxypets-style.md`](01-ai-management-galaxypets-style.md). Старт с 1 роли (digest / coordinator), расширение до 4-6 ролей.
**Output:** AI-роли с JTBD + tool list + falsification + reporting cadence.
**Outcome:** ~16 часов / неделя освобождённого времени owner.

### T9: Champion playbook for change management (внутри команды)

**JTBD:** распространить новый метод (например, gap theory сама) в команде без сопротивления.
**Method:** [`standards/06-champion-playbook-change-virus.md`](../standards/06-champion-playbook-change-virus.md), [`skills/13-champion-playbook-gap-theory.md`](../skills/13-champion-playbook-gap-theory.md).
**Output:** 2-3 internal champions + structured rollout.
**Outcome:** team-wide adoption за 8-12 недель вместо «никто не использует».

## High effort, медленный impact (но необходим если масштабируешь)

### T10: Standards repo для команды

**JTBD:** иметь SSOT для всех команд / агентов / процессов.
**Method:** скопировать структуру из этого репо (`standards/` + `skills/` + `agents/`), адаптировать под свою команду.
**Output:** internal standards repo с registry.
**Outcome:** новые члены команды onboard за 1 неделю вместо 4.

### T11: Trust metric tracking

**JTBD:** measure доверия владельца к agent / подчинённому.
**Method:** [`skills/18-trust-metric.md`](../skills/18-trust-metric.md). Steering rate / rework rate / approval rate.
**Output:** dashboard «trust per agent / per teammate».
**Outcome:** 1:1 разговоры основаны на данных, не subjective sense.

---

## Skills priority order для команды (если ты только начинаешь)

1. **`01-hypothesis-gap-falsification`** — фундамент всего
2. **`02-rca-incidents-with-effort-scale`** — для пост-инцидент учения
3. **`03-so-what-outcome-ladder`** — для отсечения псевдо-outcomes
4. **`08-root-cause-first`** — для отказа от workarounds
5. **`14-actionable-hypothesis`** — для exploration / experiments
6. **`15-next-outcome-output-mapping`** — для weekly planning
7. **`04-protocol-challenge`** — для post-delivery verification
8. **`09-critical-chain-design`** — для проектов > 4 недели
9. **`10-agent-reasoning-log`** — для понимания почему agent сделал X
10. **`16-task-completion-persistence`** — для не-отступления от quality

Skills 11-18 — для зрелых команд использующих AI-management или для специфических кейсов (champion playbook, persuasion).

## Tickets чек-листa

```
☐ T1: Self-diagnostic week log
☐ T2: Mandatory delivery format в своих ответах
☐ T3: Hypothesis card перед action
☐ T4: Owner effort digest
☐ T5: Quick ticket card
☐ T6: Glossary
☐ T7: Orchestrator с QA + design gate (advanced)
☐ T8: AI-management роли (advanced)
☐ T9: Champion playbook (для распространения)
☐ T10: Internal standards repo
☐ T11: Trust metric tracking
```

Если делаешь все 11 — это уже зрелая Gap-Theory команда. Большинство команд останавливается на T1-T6 и получает 80% эффекта.

## Связанные

- [`README.md`](../README.md)
- [`playbook/01-ai-management-galaxypets-style.md`](01-ai-management-galaxypets-style.md)
- [`playbook/03-orchestrator-with-qa-design-gate.md`](03-orchestrator-with-qa-design-gate.md)
