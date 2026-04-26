# Example: Диагностика себя по логу собственной недели

> **Метод:** ты ведёшь log своей недели (то что делал + откладывал + сопротивлялся) → размечаешь по 4 типам gap → видишь паттерн «где сам себе мешаешь».
>
> Применимо к любой роли: founder, IC, manager, advisor, researcher.

## Контекст

**Кто:** Илья — advisor / consultant (вы), 4-5 advising проектов параллельно, 1 продукт собственный.
**Запрос (внутренний):** «Чувствую что неделя получилась хаотичной. Хочу понять где я сам теряю время».

**Что у меня есть:**
- Daily log за 7 дней (что сделал, что отложил, что чувствовал — 3 строки в день, 5 минут)
- Календарь (встречи, focus blocks)
- TODO-список (что было в начале недели, что осталось)

## Шаг 1. Восстановление atomic JTBD недели

В понедельник я записал что хочу сделать:

| # | JTBD | Roles |
|---|---|---|
| 1 | Доделать v0.1 публичного gap theory репо | author |
| 2 | Провести 4 advising-сессии с клиентами | advisor |
| 3 | Написать диагностику для galaxypets management | consultant |
| 4 | Переписать CITATION.cff и LICENSE для другого репо | author |
| 5 | Подготовить материалы к workshop в субботу | educator |
| 6 | Прочитать 2 главы новой книги по change management | learner |
| 7 | Сделать 3 family activities | parent / partner |

## Шаг 2. Что фактически произошло (Friday end-of-week review)

| # | JTBD | Сделано? | Реальное состояние |
|---|---|---|---|
| 1 | gap theory репо | 70% | README + LICENSE + 3 standards. Skills + agents + templates + examples — пропущены |
| 2 | 4 advising-сессии | 100% | Все прошли |
| 3 | galaxypets диагностика | 30% | Прочитал материалы, начал draft, остановился на «нужно ещё data» |
| 4 | CITATION.cff другой репо | 0% | Не открывал |
| 5 | Workshop materials | 50% | Slide deck готов, упражнения нет |
| 6 | 2 главы книги | 80% | Прочитал, но не записал takeaways |
| 7 | Family activities | 100% | Все 3 прошли |

**Completed: 3/7. Partial: 3/7. Missed: 1/7.**

## Шаг 3. Размечаем по 4 типам gap

| JTBD | Что НЕ доделано | Тип gap |
|---|---|---|
| 1. gap theory репо | Skills + agents + templates + examples | Execution (знаю как делать, не дошли руки) |
| 3. galaxypets диагностика | «нужно ещё data» — но это excuse, реально я застрял в формулировке | Knowledge (не уверен какой формат diagnostic дать) |
| 4. CITATION.cff | Не открывал | Execution (микро-задача забыта) |
| 5. Workshop упражнения | Не сделал | Knowledge (не уверен какой формат упражнений сработает) |
| 6. Takeaways из книги | Не записал | Feedback (нет ритуала «note after reading») |

**Pattern:**
- 2 Execution gaps (репо + CITATION) — откладываемые маленькие шаги
- 2 Knowledge gaps (galaxypets + workshop) — застревание из-за неуверенности в формате
- 1 Feedback gap (book takeaways) — нет ритуала закрытия

## Шаг 4. Анализ времени по логу

Где время уходило (анализ календаря + log):

| Активность | Время | Тип |
|---|---|---|
| Advising-сессии | 8h | планируемое |
| Подготовка к сессиям | 6h | планируемое |
| Telegram / Slack reactive | 9h | reactive |
| «Подумать о galaxypets» (без действия) | 4h | застревание |
| «Прочитать что-то про workshop format» (research mode) | 3h | прокрастинация в research mode |
| Family time | 6h | планируемое |
| Sleep + meals | 56h | базовое |
| Активный writing на gap theory репо | 5h | планируемое (хотел 15h) |
| Читать книгу | 3h | планируемое |
| Workshop slide deck | 2h | планируемое |

**Surfaces:**
- 9h reactive Telegram = я сам в нём, не другие меня дёргают
- 4h «подумать про galaxypets» — это knowledge gap (застрял в формате) маскируется под «think harder»
- 3h «research workshop format» — то же самое
- На gap theory репо хотел 15h, потратил 5h. Дельта 10h ушла в reactive + research mode

## Шаг 5. Что меня тормозит системно

| Pattern | Тип gap | Glue effort моя | Системное решение |
|---|---|---|---|
| Reactive Telegram 9h/нед — вытесняет writing | Execution (нет block'а) | 9h × 50 = 450 | Daily 4-hour focus block без Telegram до 13:00, notifications off |
| Knowledge gap maskируется под «думать» / «research» | Knowledge | 7h × 70 = 490 | Когда «не знаю формат» — даю себе 30 минут на research, потом start writing draft. Если draft = плохой = ОК, redo lab |
| Feedback gap по чтению книг | Feedback | 0 (no time spent) | После каждой главы — 5 строк takeaway в свой book log. 2 минуты после главы |
| Маленькие задачи (CITATION.cff) забываются | Execution | 100 (потом всплывает + чувство что «забыл») | inbox-zero ритуал: вечером пятницы все < 30 мин задачи закрыть |
| Не сделанные shrинки (упражнения для workshop) | Knowledge gap → execution gap | 200 (в субботу будет переработка) | Когда workshop через 7 дней — обязательно «черновой draft упражнений» в первой трети недели |

**Total моего glue effort: ~1240 единиц / неделя.** Реально полезного работа: 30-40 часов из 7×24=168.

## Шаг 6. Карточка для себя на следующую неделю

```
5 системных мер:

1. 4-hour focus block 9-13 без Telegram. Уведомления OFF.
2. Knowledge gap правило: 30 минут research → потом draft даже плохой.
   «Подумать ещё» = NO, draft + iterate.
3. Reading ritual: после главы — 5 строк takeaway в book log. 2 мин.
4. Friday inbox-zero: 1 час, все < 30 мин задачи закрыть.
5. Long task rule: если задача > 5 часов work и deadline > 7 дней —
   обязательно «черновой output» в первой трети периода.

Ожидаемый эффект:
- gap theory репо доделан (15h есть)
- galaxypets диагностика — Knowledge gap проходится draft'ом, не «думаньем»
- workshop упражнения — black draft в среду, finalize в субботу
- book takeaways — есть, появляются автоматически
- CITATION.cff — закрывается в Friday inbox-zero

Risk: focus block без Telegram → клиент пишет, я не отвечаю.
Mitigation: emergency phone open для критичного,
другие — могут подождать 4 часа.
```

## Чему это учит (meta)

1. **Knowledge gap у умного человека маскируется под «думать ещё».** Это не think — это freeze. 30 мин research → draft.
2. **Reactive чаты — самый дорогой gap для individual contributor.** Я сам в чате, никто не виноват.
3. **«Большую» задачу не доделываешь не потому что она большая.** Не доделываешь потому что в среду не сделал draft, а в пятницу уже поздно.
4. **Меньшие задачи (CITATION.cff) теряются в фоновом шуме.** Inbox-zero ритуал — единственная защита.
5. **Self-diagnosis — это не «строгость к себе».** Это нахождение **системных** ловушек. Без системы воля не помогает.

## Как применить

1. Веди daily log 5 минут вечером: что сделал / отложил / чувствовал
2. В пятницу review:
   - Что было запланировано в понедельник
   - Что фактически сделал
   - Размeti gaps по 4 типам
   - Найди 5 системных мер на следующую неделю
3. Через 4 недели пересмотри — какие меры прижились, какие нет

## Связанные

- [`examples/01-diagnose-founder-from-correspondence.md`](01-diagnose-founder-from-correspondence.md)
- [`templates/02-rca-effort-scale-0-100.md`](../templates/02-rca-effort-scale-0-100.md)
- [`standards/01-gap-theory.md`](../standards/01-gap-theory.md)
