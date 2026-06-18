# Example: Диагностика sales-команды по транскриптам звонков

> **Метод:** через транскрипты 50-100 звонков команды продаж за месяц находим где sales теряет deals в склейке между этапами воронки. Diagnose **what they say** + **what they don't say** + **what they say but don't follow through**.

## Контекст

**Кто:** <client> — sleep-tech retail, B2C, средний чек $500.
**Команда продаж:** 8 sellers, head of sales, head of customer success.
**Запрос:** «Конверсия от первого звонка к покупке упала с 18% до 11% за 3 месяца. Почему?»

**Что у нас есть:**
- 87 транскриптов звонков за 30 дней (через JustCall + Whisper)
- CRM-export deals (статусы, переходы, сроки)
- Скрипт продаж (внутренний документ)

## Шаг 1. Outcome-mapping звонков

Каждый звонок имеет один из исходов:

| Исход | Кол-во | % |
|---|---|---|
| Покупка сразу | 4 | 5% |
| Получили email на follow-up | 31 | 36% |
| «Я подумаю» | 28 | 32% |
| Отказ с возражением | 18 | 21% |
| No answer / disconnect | 6 | 7% |

**Pattern:** 32% «я подумаю» — это большой gap между «звонок прошёл» и «решение принято». Эту группу разбираем глубже.

## Шаг 2. Размечаем 4 типа gap в звонках

### Knowledge gap у клиента (он не знает что ему предлагают)

Симптомы в транскриптах:
- «Я не понял что именно даёт ваш продукт» (12 звонков из 28)
- «А чем это отличается от X?» (без ответа от seller — 9 раз)
- Seller перечисляет фичи без связи с ситуацией клиента (44 раза в 87 звонках)

**Глубже:** 7 из 8 sellers не делают «mirror back» — не повторяют ситуацию клиента **его словами** перед предложением. Клиент не чувствует что услышан → не доверяет.

### Execution gap у клиента (знает, но не покупает сейчас)

Симптомы:
- «Поговорю с супругой / партнёром» (14 звонков) — но в 11 из них seller НЕ предложил конкретное время follow-up
- «Сейчас не время / нет бюджета» (8 звонков) — в 5 seller НЕ предложил installment plan, хотя он есть в скрипте

**Глубже:** seller'ы не следуют по воронке после возражений. Скрипт есть, но в моменте — bypass.

### Feedback gap у sellers (после звонка нет цикла)

CRM-данные показывают:
- 56% звонков не имеют CRM-записи в течение 24 часов
- 78% «follow-up email» отправок без content templating (каждый seller пишет с нуля)
- 0% автоматического измерения «через сколько дней клиент возвращается»

**Глубже:** sellers не получают feedback что их «я подумаю» означает 31% от звонков → не корректируют стиль.

### Integration gap (между sales и операциями)

- 12 deals «сорвались» потому что customer success не подключился к onboarding в течение 48 часов после покупки (refund rate 14% против 6% когда подключение в 24ч)
- 5 deals «потеряны» потому что покупатель не знал что доставка занимает 14 дней — это всплыло после оплаты, refund

## Шаг 3. Glue effort на каждый «я подумаю» deal

Из 28 «я подумаю» — за месяц 6 вернулись и купили (21%), 22 не вернулись.

Реконструкция усилия SELLER на возвращение:

| Действие | Cognitive | Mechanical | Integration | Coordination | Total |
|---|---|---|---|---|---|
| Найти CRM-запись звонка через 5 дней | 30 | 30 | 0 | 0 | **60** |
| Вспомнить что обсуждали (без транскрипта) | 50 | 0 | 0 | 0 | **50** |
| Написать персонализированный email | 50 | 30 | 0 | 0 | **80** |
| Дозвониться (часто mailbox) | 20 | 50 | 0 | 0 | **70** |
| Если не отвечает — повторный цикл | 30 | 70 | 30 | 0 | **130** |

**Total per deal: 390 единиц на возвращение «я подумаю» клиента.**
**Conversion: 21%.** Реальный effort на конвертированный deal = ~1850 единиц.

## Шаг 4. Сравнение топ-2 sellers vs bottom-2

|  | Top-2 sellers | Bottom-2 sellers |
|---|---|---|
| Conversion | 24% | 7% |
| Avg call length | 18 мин | 9 мин |
| Mirror-back per call | 4× | 0.5× |
| Specific follow-up time agreed | 80% | 25% |
| CRM filled within 24h | 95% | 30% |
| Used installment offer | 60% | 5% |

**Conclusion:** разница между top и bottom — НЕ в харизме / навыках. В **mechanics**: mirror-back, specific time, CRM-discipline.

## Шаг 5. Системные решения (вместо «больше тренинг»)

| Gap | Точечный фикс (плохо) | Системное решение (хорошо) | Кто |
|---|---|---|---|
| Mirror-back отсутствует | «Тренировка по mirror-back» | AI-coach каждые 3 звонка пишет seller'у: «в 4 из 5 звонков mirror-back был < 10 секунд — попробуй так:» с цитатой | AI-bot + head of sales |
| Specific follow-up time не назначается | «Напоминать sellers» | Скрипт CRM: чекбокс «follow-up time agreed: yes/no, when?» — обязателен для closure call | RevOps |
| Installment plan не предлагается | «Тренировка по plan'ам» | Реал-тайм AI suggestion: при возражении «нет бюджета» — POPUP «предложи installment X» | AI + CRM |
| CRM не заполнен в 24ч | «Дисциплина» | Чёткий incentive — bonus только если CRM-discipline > 90%; иначе bonus -20% | head of sales |
| Customer success не подключается в 24ч после покупки | «Лучше координировать» | Auto-handoff: deal close → trigger в #cs-onboarding с deadline 24h, escalation на head of CS если просрочено | CS lead |
| Доставка 14 дней — surprise | «Sellers, говорите про доставку» | Mandatory скрипт: «доставка 14 дней — это вписывается в твои планы?» в чек-листе перед closing | Skript update |

**Эффект:** через 60 дней conversion 11% → 16% (по моделированию на исторических данных).

## Шаг 6. Что вернули head of sales

```
Конверсия упала с 18% до 11% не из-за «команда хуже работает»,
а потому что 6 механик отсутствуют системно:

1. Mirror-back в звонках (нет AI-coach feedback)
2. Specific follow-up time (нет CRM enforcement)
3. Installment plan на возражения (нет real-time prompt)
4. CRM в 24ч (нет привязки к bonus)
5. CS handoff в 24ч (нет auto-trigger)
6. Доставка surprise (нет mandatory chek в скрипте)

Top-2 sellers делают эти 6 механик «по себе».
Bottom-2 — никогда. Тренинг не помогает потому что
проблема не в навыке, а в системе которая делает забыть невозможным.

ROI: -7% conversion → +5% за 60 дней = +$X / месяц на тех же сделках.
Cost: 1 RevOps sprint + 1 AI-bot setup.
```

## Чему это учит

1. **Sales conversion редко падает из-за навыков.** Чаще — из-за пропавших микро-механик в воронке (mirror-back / specific time / mandatory checks).
2. **Top performers vs bottom performers** — лучший benchmark. Mechanics, not personality.
3. **AI-coach в реальном времени** > тренинг по выходным. Контекст важен.
4. **Diagnose what they DON'T say** в звонках — это часто красноречивее чем то что говорят.

## Как применить

1. Транскрибируй 50-100 звонков (Whisper / любой ASR)
2. Размeти outcome каждого звонка
3. Группируй «я подумаю» отдельно — 30%+ = signal на gap
4. Сравни top-2 vs bottom-2 sellers по 5-10 механикам
5. Найди 5 системных решений (CRM enforcement, AI-coach, скрипт, auto-handoff)
6. Не «больше тренинг» — а механика которая делает forget невозможным

## Связанные

- [`agents/process-correspondence-investigator.md`](../agents/process-correspondence-investigator.md)
- [`standards/05-persuasion-belief-change.md`](../standards/05-persuasion-belief-change.md)
- [`standards/07-abcdx-segmentation.md`](../standards/07-abcdx-segmentation.md)
