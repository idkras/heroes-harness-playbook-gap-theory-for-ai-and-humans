# Playbook: AI-Management Galaxypets-Style

> Практики управления AI-агентами как членами команды, применённые при advising Galaxypets-management и других команд. Анонимизированный case study + переносимые правила.

## Контекст применения

**Команда:** Galaxypets-management — холдинг управляющий несколькими game-продуктами в pets-marketplace. ~80 человек, из которых 12 связаны с product / engineering / data, 8 — operations / finance, остальные — content / community / sales.

**Запрос owner'а холдинга:** «Хочу чтобы каждый менеджер в команде работал в паре с AI-агентом — но не как chatbot, а как junior consultant который помнит контекст, делает проверяемые гипотезы, и не создаёт мне новых проблем».

**Что было до:** ChatGPT использовали в одиночку, 80% запросов были «помоги написать сообщение клиенту», 20% — «найди инсайт в данных». Но никто не верил выводам — каждый раз приходилось перепроверять.

**Что стало после 6 месяцев:** AI-агенты участвуют в 4 из 12 операционных процессов как полноправные роли (с tool access, ограниченным scope, обязательной фальсификацией).

---

## Принцип №1: AI-агент = роль с обязательствами и ограничениями

Не «инструмент» а **роль** в команде. У роли есть:

| Атрибут | Описание |
|---|---|
| **Имя** | Конкретное (например, «Лиза — team care coordinator») |
| **JTBD** | Атомарный, измеримый, документированный |
| **Tool access** | Ограниченный список MCP / API / системы |
| **Authority limits** | Что может делать без подтверждения, что — только с подтверждением |
| **Reporting cadence** | Как часто и кому докладывает |
| **Falsification обязательна** | Все выводы → gap table → verdict до доставки |
| **Recovery procedure** | Что делать если что-то пошло не так |

См. [`standards/09-praxis-crew-ai-management-onboarding.md`](../standards/09-praxis-crew-ai-management-onboarding.md).

### Пример: 4 AI-роли в Galaxypets

| Имя | JTBD | Authority |
|---|---|---|
| **Лиза** (team-care coordinator) | Принимает файлы от клиентов в Telegram → фиксирует в bead → готовит draft response | Может писать draft, **не может** отправить без owner go |
| **Роман** (sales call analyzer) | Анализирует записи звонков команды продаж → выдаёт per-call cards в Google Sheet | Может писать в Sheet, **не может** менять CRM |
| **Анна** (data analyst) | По запросу собирает виджет данных из Pulse.ai → готовит analysis | Может читать данные, **не может** менять конфигурацию |
| **Олег** (orchestrator) | Принимает задачу → разбивает на стадии → спавнит других агентов → проверяет QA + design gates | Может спавнить любого из выше, обязан запустить QA + design |

Каждый имеет свой `.md` файл-описание с обязательствами и tool list. См. `agents/` папку этого репо.

---

## Принцип №2: Tool authority ≠ generic agent

Распространённая ошибка: дать ChatGPT/Claude доступ ко **всему** через MCP. В Galaxypets провалилось 2 раза:

1. AI-агент с full Slack access начал писать в публичные каналы вместо DM
2. AI-агент с full Linear access закрывал тикеты как `done` без верификации

**Правило:** каждый агент имеет **минимально достаточный** tool list:

```yaml
# .agents/agents/lisa-team-care.md
---
name: Лиза (team care coordinator)
tools:
  read:
    - telegram-mcp.search_messages   # читать сообщения
    - telegram-mcp.get_chat          # метаданные чата
    - google-drive-mcp.search        # искать файлы клиентов
  write:
    - bash (Write, Edit)             # писать в локальный bead
  forbidden:
    - telegram-mcp.send_message      # ← НЕ может отправить без owner
    - linear.update_issue            # ← НЕ может менять Linear
authority:
  - Создавать draft response
  - Создавать bead-тикет
  - НЕ отправлять сообщение
  - НЕ менять статус Linear-тикета
recovery:
  - Если tool fails → log + ping owner
  - Если access denied → попытка через credentials_manager
---
```

Разделение на `read` / `write` / `forbidden` — обязательное.

---

## Принцип №3: Hypothesis falsification как обязательный gate

Каждый substantial output AI-агента проходит через [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md):

1. Гипотеза одной фразой
2. Expectations table
3. Reality check (читает файлы / запускает тесты / смотрит данные)
4. Gap table с verdict
5. Если ≠ `confirmed` → re-implementation, не доставка

**Эффект в Galaxypets:**
- До: 28% выводов AI-агента надо было перепроверять руками (RCA-инцидентов в месяц = 11)
- После 3 месяцев применения: 4% перепроверки (RCA = 2 в месяц)

Это **самая большая отдача** из всех практик — и самая дешёвая в реализации.

См. `playbook/03-orchestrator-with-qa-design-gate.md` — оркестратор обеспечивает что falsification запускается всегда.

---

## Принцип №4: Subagents через Agent tool, не через recursion

Многие команды пытаются «сделать одного супер-агента который умеет всё». Это не работает:
- Контекст переполняется быстро
- Один tool-set = compromise (для всех задач — никакая хорошо)
- Reasoning ухудшается с длиной context

**Galaxypets pattern:** main agent (orchestrator) спавнит **subagents** через Agent tool с:
- Узкой role
- Ограниченным tool set
- Своим model (Opus для complex reasoning, Haiku для bulk operations)
- READ-ONLY mode по умолчанию (все ревьюеры — read-only)

Пример flow для «отчёт по неделе для клиента»:

```
User: «подготовь отчёт по неделе для клиента X»
  ↓
Orchestrator (Opus)
  ↓ spawn parallel
  ├─ data-analyst (Sonnet) — собирает widget data
  ├─ correspondence-investigator (Opus) — извлекает темы из чата
  └─ rca-investigator (Opus) — если нашли incidents за неделю
  ↓ collect results
  ↓ spawn QA
  ├─ ui-qa-engineer (Sonnet) — проверяет визуально
  └─ code-reviewer (Sonnet) — проверяет логику
  ↓ collect QA verdict
  ↓ spawn design
  └─ design-art-director (Opus) — adversarial review
  ↓ final delivery
User получает report + 12 mandatory секций
```

Time to delivery: 8-12 минут вместо «1 агент думает 30 минут».

---

## Принцип №5: Beads / Linear как SSOT, не chat

Раньше вся работа AI-агентов жила в чате (Slack threads, Telegram messages). Это ломалось:
- Невозможно поднять контекст через 2 недели
- Сообщения переезжают в архив, ссылки ломаются
- Несколько разных задач смешиваются в одном thread

**Galaxypets pattern:**

| Layer | Что хранит | Editable by |
|---|---|---|
| `.beads/issues.jsonl` (или Linear) | Канонический state of all work | AI + humans |
| Chat (Telegram / Slack) | Reactive communication, не SSOT | humans |
| Daily digest / morning pack | Reflection of beads, не source | AI generates |
| Project folder | Artifacts (md, parquet, screenshots) | AI + humans |

Все AI-агенты пишут в **beads** как primary, в chat — как notification copy.

См. [`skills/16-task-completion-persistence.md`](../skills/16-task-completion-persistence.md).

---

## Принцип №6: Memory с предсказуемой структурой

ChatGPT memory / Claude memory часто становится свалкой. В Galaxypets применяем **typed memory** с 4 типами:

| Type | Когда писать | Что писать |
|---|---|---|
| `user` | Узнал что-то про owner | Роль, предпочтения, экспертиза |
| `feedback` | Owner поправил / одобрил подход | Правило с **Why:** и **How to apply:** |
| `project` | Узнал про текущую задачу / клиента | Дедлайны, кто-что-делает |
| `reference` | Узнал где искать инфу | URL, instrument, channel |

См. AGENTS.md `# auto memory` секцию (в этом репо `AGENTS.md` тоже есть аналог).

**Эффект:** через 3 месяца использования agent отвечает на «как мы делаем X в этом контексте?» правильно в 92% случаев (без typed memory было 41%).

---

## Принцип №7: Trust-metric как command level KPI

В Galaxypets каждый месяц считается **trust score** AI-агента:

```
trust_score = 1 - (steering_corrections / total_owner_interactions)
```

| Балл | Что значит |
|---|---|
| > 0.9 | Высокое доверие — agent делает работу правильно с первого раза в 90%+ случаев |
| 0.7-0.9 | Среднее — нужны точечные tuning-правки в скилах |
| < 0.7 | Низкое — agent либо в неправильной роли, либо стандарты дрейфуют |

**Steering corrections** = моменты когда owner написал «нет, не так» или «делай по-другому» или «эту секцию я не просил».

См. [`skills/18-trust-metric.md`](../skills/18-trust-metric.md).

---

## Принцип №8: «No new documents» policy

Из всех практик AI-агенты больше всего ошибаются в **создании новых файлов вместо правки существующих**. Документ-bloat — главный враг.

**Galaxypets policy:**
- Перед `Write` агент проверяет «существует ли уже такой документ?»
- Создание нового `.md` требует обоснования в 3 предложениях
- В клиентских папках жёсткий artifact-budget (max N файлов на bead)

См. [`skills/17-document-creation-guard.md`](../skills/17-document-creation-guard.md).

---

## Принцип №9: Mandatory delivery format

Каждое substantial AI-доставка (≥ 5 минут работы или ≥ 3 file writes) проходит через 12 mandatory sections (см. AGENTS.md):

1. Было / Стало
2. JTBD
3. Input checklist
4. Output checklist
5. Outcome checklist
6. Design review
7. QA review
8. Deploy & PR review
9. Hypothesis falsification + gap table
10. Owner effort digest
11. Run Evidence
12. Canonical Vocabulary Check

Эта структура **в команде стала стандартом** — owner ожидает её и в человеческих доставках тоже.

---

## Антипаттерны (что в Galaxypets не сработало)

| Anti-pattern | Почему провалилось | Что заменили |
|---|---|---|
| «Дать AI полный access ко всему через MCP» | AI отправлял что не должен | Tool authority с `read` / `write` / `forbidden` |
| «Один super-agent делает всё» | Контекст переполняется, reasoning хуже | Subagents с узкими ролями |
| «AI учит сам что нужно — read team docs» | Команда не пишет docs, agent ищет противоречия | Standards как SSOT, периодический skill-cleanup |
| «AI пусть думает дольше, лучше будет» | Длительность ≠ качество, чаще наоборот | Time-box reasoning + falsification gate |
| «Memory как chat-history dump» | Свалка, нерелевантное берётся | Typed memory с 4 категориями |
| «AI может закрывать тикеты сам» | Закрывались без верификации | Authority limits: AI создаёт draft, owner closes |

---

## Метрики команды (после 6 месяцев)

| Метрика | До AI-management | После 6 мес |
|---|---|---|
| Time от запроса owner до response | 2-4 часа | 8-15 минут |
| Trust score across 4 agents | 0.41 | 0.87 |
| Manual steering corrections / неделя | 47 | 9 |
| RCA-инцидентов с AI / месяц | 11 | 2 |
| Time spent в operationsза неделю owner-side | ~25h | ~9h |

Освободившееся время: ~16 часов / неделя × 6 месяцев = ~400 часов = $40-100k стоимости advising-уровня времени, в зависимости от расценок.

---

## Как стартовать у себя

Минимальная конфигурация (1-2 недели):

1. **Выбрать 1 ритуал** для AI-делегирования (например, weekly digest)
2. **Создать AI-роль** для этого ритуала (имя + JTBD + tool list)
3. **Запустить через Claude Code или эквивалент** с проектным `AGENTS.md`
4. **Применить hypothesis-falsification** к каждому output
5. **Замерить steering rate** через 4 недели
6. **Если > 30% steering** — пересмотреть JTBD / tools / standards
7. **Если < 10% steering** — добавить второй ритуал

Через 8 недель должно быть 2-3 продуктивных AI-роли. Через 6 месяцев — 4-6.

См. [`standards/04-ai-management-workflow.md`](../standards/04-ai-management-workflow.md) для полной методологии.

---

## Связанные

- [`standards/04-ai-management-workflow.md`](../standards/04-ai-management-workflow.md) — каноничный стандарт
- [`standards/09-praxis-crew-ai-management-onboarding.md`](../standards/09-praxis-crew-ai-management-onboarding.md) — onboarding new AI-роли в команду
- [`playbook/03-orchestrator-with-qa-design-gate.md`](03-orchestrator-with-qa-design-gate.md) — оркестратор с QA gate
- [`agents/manager-lead-orchestrator.md`](../agents/manager-lead-orchestrator.md)
