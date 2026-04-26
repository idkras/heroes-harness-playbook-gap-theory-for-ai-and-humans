# Glossary: Heroes Gap Theory Terms

Каноничные определения терминов используемых в репо. Если в твоей команде термин уже занят другим значением — используй здесь и аннотируй разницу при цитировании.

## Core terms

### Gap

Разрыв между ожиданием (expectation) и реальностью (reality). Симптом: владелец / пользователь / агент думает что «должно быть X», но видит «Y». Главная единица анализа в Gap Theory.

### Gap types (4 типа)

| Тип | Симптом |
|---|---|
| **Knowledge gap** | «Я не знал что так можно» |
| **Execution gap** | «Знаю, но не делаю» |
| **Feedback gap** | «Сделал — не понял что получилось» |
| **Integration gap** | «Каждый шаг ОК, но всё вместе не склеивается» |

### Glue Effort

Усилия (cognitive + mechanical + integration + coordination) которые требуется человеку чтобы **склеить** разрыв. Измеряется по шкале 0-100 (см. [`templates/02-rca-effort-scale-0-100.md`](../templates/02-rca-effort-scale-0-100.md)).

### JTBD (Job to be Done)

Атомарная задача роли формата `Когда X, я хочу Y, чтобы Z`. Hierarchy:
- **Big JTBD** — стратегическая (недели / месяцы)
- **Medium JTBD** — функциональная (дни)
- **Small JTBD** — операционная / интеракция (минуты) = test case

### Output vs Outcome

| Output | Outcome |
|---|---|
| Артефакт / событие наблюдаемое | Real изменение в роли / жизни |
| «Создан README» | «Метод адоптируется внешними командами» |
| Можно показать пальцем | Проверяется через 5 so-what |

### So-what ladder

Метод проверки настоящего outcome — задаём «И что с того?» 5 раз. Если на 5-м уровне — реальное изменение в роли, это outcome. Если — снова артефакт / промежуточный шаг — это псевдо-outcome.

### Critical chain (Голдрат)

Самая длинная последовательность зависимых шагов от старта до outcome. 3-5 шагов оптимум. Параллельные ветки — не в критической цепочке.

## Falsification terms

### Hypothesis card

Структурированная гипотеза с триггером, ролью, изменением, output, outcome, метриками, baseline, threshold, falsification criterion, stopping criteria.

### Falsification

Систематическая попытка опровергнуть собственную гипотезу через сравнение expectation vs reality. Verdict: `confirmed` / `partially confirmed` / `falsified`.

### Gap table

Таблица 7 колонок: `# / Expectation / Reality / Δ / Severity / Verdict / Next action / Усилие человека (0-100)`. Mandatory минимум 2 строки.

### Owner effort digest

Финальная таблица в delivery: что осталось делать владельцу + усилие 0-100 + что агент может сделать сам.

## Process terms

### Quick ticket card

Шапка + JTBD + контекст + output + outcome + DoD + test cases + corner cases + blockers + next-action. Создаётся перед началом любой substantial задачи.

### Expected output table

Контракт «что появится в результате реализации» — колонки = поля, строки = примеры данных. Создаётся **до** implementation.

### 4×yes Generalization Gate

Перед `Write` в код: (1) работает для всех клиентов через config? (2) identity из manifest? (3) data из manifest.dataSource? (4) новый клиент = manifest edit only? Если хоть один = no — redesign.

### Self-falsification

Между implementation и QA gate агент **сам** запускает hypothesis-gap-falsification на свой output. Цель — поймать success theater до QA.

### Mandatory delivery format

12 секций обязательных в substantial response: Было/Стало, JTBD, Input/Output/Outcome checklists, Design review, QA review, Deploy review, Hypothesis falsification, Owner effort digest, Run evidence, Vocabulary check.

## AI agent terms

### Subagent

AI-агент с узкой ролью, ограниченным tool set, своим model. Спавнится через Agent tool из main orchestrator. Read-only по умолчанию для review-ролей.

### Tool authority

Разделение tools агента на `read` / `write` / `forbidden`. Минимально достаточный set.

### Trust score

`1 - (steering_corrections / total_owner_interactions)`. Целевое > 0.9.

### Reasoning log

Запись что повлияло на решение агента: какие стандарты / скилы / instructions помешали или помогли. Используется для post-mortem.

## Methodology references

### Theory of Constraints (Goldratt)

5 focusing steps: Identify / Exploit / Subordinate / Elevate / Repeat. Используется в critical chain design.

### REDUCE framework (Berger)

Reactance / Endowment / Distance / Uncertainty / Corroborating evidence / Education. Из книги *The Catalyst*. Используется в persuasion-belief-change.

### Картина мира + объяснительная модель (Ильяхов)

Картина мира — что человек уже считает истинным. Объяснительная модель — как ты соединяешь новую идею с его картиной мира. Применяется в communication design.

### Speed of Trust (Covey)

Доверие = функция (характер × компетентность). Скорость = функция доверия. Trust tax / trust dividend в коммуникации.

### 5 пороков команды (Lencioni)

Отсутствие доверия → страх конфликта → отсутствие commitment → избегание ответственности → невнимание к результату. Mapped к gap theory.

## Anonymization placeholders (used in this repo)

| Placeholder | Subject area |
|---|---|
| galaxypets | game-marketplace для виртуальных питомцев |
| autovin | B2B-маркетплейс автозапчастей |
| fashionhub | premium fashion ecommerce |
| sleepwell | sleep-tech retail (matrasses, sleep products) |
| designcraft | design platform |
| fitcrew | fitness apps marketplace |
| bigfin | financial broker (retail investments) |
| tempest | B2B equipment supplier |
| pulse.ai | marketing analytics platform |
| praxis platform | AI methodology platform / internal codebase |
| luminary | small/medium business advising context |

## Связанные стандарты

- [`standards/01-gap-theory.md`](../standards/01-gap-theory.md) — каноничный стандарт Gap Theory
- [`standards/03-outcome-zero-gap-jtbd-transfer.md`](../standards/03-outcome-zero-gap-jtbd-transfer.md) — outcome транзит
- [`standards/05-persuasion-belief-change.md`](../standards/05-persuasion-belief-change.md) — REDUCE framework
- [`standards/08-speed-of-trust-economics.md`](../standards/08-speed-of-trust-economics.md) — trust как метрика
