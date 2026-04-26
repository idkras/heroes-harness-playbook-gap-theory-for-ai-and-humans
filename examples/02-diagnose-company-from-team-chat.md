# Example: Диагностика компании по командному чату

> **Метод:** через 30-дневную выгрузку командного Slack/Telegram находим где компания теряет время **между** ролями (в склейках), а не **внутри** ролей.

## Контекст

**Кто:** Autovin — B2B-маркетплейс автозапчастей, 47 человек, GMV $4.5M/мес.
**Запрос:** CEO заметил что инженерные релизы стали выходить медленнее. «От тикета до прода теперь 3 недели вместо 5 дней годом ранее».

**Что у нас есть:**
- Slack-выгрузка: каналы #engineering, #product, #releases, #incidents за 30 дней
- Linear-export тикетов за тот же период
- Git-история (коммиты + PR метаданные)

## Шаг 1. Mapping ролей и интеракций

| Роль | Кол-во в команде | Главные каналы коммуникации |
|---|---|---|
| Product Manager | 4 | #product, 1:1 с inженерами |
| Tech Lead | 3 | #engineering, code review |
| Backend Dev | 8 | #engineering, PRs |
| Frontend Dev | 6 | #engineering, PRs |
| QA | 3 | #releases, #incidents |
| DevOps | 2 | #releases, #incidents |
| Designer | 2 | #product, Figma |

## Шаг 2. Реконструкция типичного релиз-flow

Из переписки восстанавливаем как путь тикета:

```
PM пишет тикет (Linear)
   ↓ ~2 дня — wait
Tech Lead приоритизирует
   ↓ ~3 дня — wait
Backend dev берёт в работу
   ↓ ~5 дней — implementation
Backend dev открывает PR
   ↓ ~2 дня — wait на code review
Tech Lead делает review
   ↓ ~1 день — back-and-forth
PR merged
   ↓ ~1 день — frontend integration
Frontend dev добавляет UI
   ↓ ~2 дня — wait на QA
QA тестирует
   ↓ ~1 день — bugs found, back to dev
Бэк-форс back-and-forth между dev и QA
   ↓ ~3 дня — back-and-forth
Релиз готов к деплою
   ↓ ~1 день — wait DevOps window
Релиз деплоится
```

**Total: 21 день. Pure work time: ~6 дней. Wait time: ~15 дней.**

## Шаг 3. Размечаем gaps между ролями

| Переход | Что происходит | Тип gap | Симптом в чате |
|---|---|---|---|
| PM → Tech Lead | 2 дня wait | **Integration** | PM пишет в #product, Tech Lead не подписан, видит через день |
| Tech Lead → Backend dev | 3 дня wait | **Execution** | TL приоритизирует на standup в среду, dev берёт в работу в понедельник (никто не дёргает) |
| Backend dev → Tech Lead (code review) | 2 дня wait | **Feedback** | Reviewer не уведомлён в Slack, узнаёт случайно |
| Frontend dev → QA | 2 дня wait | **Integration** | QA получает trigger через emails, не Slack, проверяет почту 1×/день |
| QA → Backend dev | 3 дня back-and-forth | **Knowledge** | QA не знает acceptance criteria, ищет → backend пишет → QA снова не уверен |

**Wait time распределение:**
- Integration gaps: 4 дня (PM→TL и Frontend→QA)
- Execution gap: 3 дня (TL→backend dev)
- Feedback gap: 2 дня (PR review)
- Knowledge gap: 3 дня (QA back-and-forth)

**Pure work distribution:**
- Backend implementation: 5 дней
- Frontend integration: 1 день

**Conclusion:** проблема НЕ в скорости разработчиков. Проблема в **15 днях wait** между ролями.

## Шаг 4. Glue effort по ролям

| Роль | Глюинговое усилие в неделю на 1 тикет | Главный gap |
|---|---|---|
| PM | 50 (writing + chasing) | Integration (никто не reads его product channel) |
| Tech Lead | 80 (review delays + standup catch-up) | Feedback (нет уведомлений на PR) |
| Backend dev | 30 (acceptance ambiguity) | Knowledge (acceptance criteria неполные) |
| Frontend dev | 60 (trigger ambiguity) | Integration (когда подключаться?) |
| QA | 90 (back-and-forth) | Knowledge + Integration |
| DevOps | 40 (release window scheduling) | Integration (release window не в календаре) |

**Total team glue effort per ticket: 350 единиц.** На 4 ticket'a в неделю = 1400 единиц. Это эквивалент 1 FTE целиком на склейку.

## Шаг 5. Системные решения (root cause first, не workarounds)

| Gap | Workaround (плохо) | Системное решение (хорошо) | Эффект |
|---|---|---|---|
| PM→TL (2 дня) | «PM, пиши Tech Lead в личку» | Auto-bot: новый тикет → ping Tech Lead в #engineering сразу | -2 дня, -50 effort |
| TL→Backend (3 дня) | Daily standup standup | Tickets с label `prio:next` → bot уведомляет dev назначенного на rotation | -2 дня, -80 effort |
| PR review (2 дня) | «Делайте review быстрее» | GitHub action: PR open > 4h → ping reviewer в Slack | -1 день, -40 effort |
| Frontend→QA (2 дня) | «QA, проверяйте email чаще» | Slack-integration: PR merged → автоматически создаётся QA-тикет с trigger в #releases | -2 дня, -60 effort |
| QA back-and-forth (3 дня) | «Лучше пишите acceptance criteria» | Linear template enforcement: тикет нельзя закрыть без секции `Acceptance criteria` со ссылкой на test cases | -2 дня, -90 effort |

**Эффект от 5 системных решений:**
- Wait time: 15 → 6 дней
- Total per ticket: 21 → 12 дней (40% быстрее)
- Glue effort: 350 → 90 единиц
- Не нужны новые инженеры — нужны новые **связки** между ролями

## Шаг 6. Что вернули CEO

```
Релизы замедлились НЕ потому что инженеры стали хуже работать.
Замедлились потому что глюинговое усилие между ролями выросло
с одного потеряного дня в год назад до 15 дней сейчас.

Размер компании вырос (12 → 47), а связки остались "общалово в #channel".

5 системных мер дадут 21 → 12 дней (40% быстрее) без найма:
1. Auto-bot: PM-ticket → Tech Lead ping
2. Linear label `prio:next` → dev rotation ping
3. GitHub action: PR open > 4h → reviewer Slack ping
4. PR merged → автоматический QA-тикет
5. Acceptance criteria field обязателен в Linear

Total cost: 1 неделя dev work + 0.5 неделя процесс-договорённостей.
ROI: ~1 FTE годом эквивалент в первый месяц.
```

## Чему это учит

1. **Замедление не = некомпетентность.** Замедление чаще = накопление integration gaps по мере роста команды.
2. **Glue effort растёт квадратично от размера команды,** если связки остаются ad-hoc.
3. **Diagnose by wait time, not work time** — где люди ждут друг друга, там и gap.
4. **Bot / automation редко решает knowledge gap, но почти всегда решает integration gap.** Knowledge gap нужен document / template / rubric.

## Как применить

1. Выгрузи Slack или эквивалент за 30 дней
2. Реконструируй типичный flow задачи
3. Замерь wait time между ролями
4. Размети wait time по 4 типам gap
5. Реши каждый gap системно (bot / template / rubric / ritual), не «лучше работайте»

## Связанные

- [`examples/01-diagnose-founder-from-correspondence.md`](01-diagnose-founder-from-correspondence.md) — диагностика индивидуальных причин
- [`agents/process-correspondence-investigator.md`](../agents/process-correspondence-investigator.md)
- [`standards/04-ai-management-workflow.md`](../standards/04-ai-management-workflow.md)
- [`templates/08-jtbd-scenarium-tree.md`](../templates/08-jtbd-scenarium-tree.md)
