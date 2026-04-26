# Template: Hypothesis Card (Falsifiable Form)

> Каноничная форма гипотезы по [Hypothesis Standard 2.2 v3.0](../standards/01-gap-theory.md). Любая гипотеза в команде должна заполнять ВСЕ поля до первого действия. «Сырые» гипотезы (без baseline / threshold / falsification criterion) не запускаются.

## Шаблон

```yaml
---
id: H-XXX
title: <одна фраза одним предложением>
author: <имя или @handle>
date: YYYY-MM-DD
status: draft | active | confirmed | falsified | abandoned
---
```

### 1. Триггер (когда применять)
```
Условие, при котором эта гипотеза релевантна:
> [например: «когда retention новых пользователей за 7 дней упал ниже 40%»]
```

### 2. Роль (для кого)
```
Кто получит outcome от подтверждения гипотезы:
> [PM / sales lead / customer / founder]
```

### 3. Изменение (что делаем)
```
Конкретное действие/изменение в системе/процессе/коммуникации:
> [например: «добавляем onboarding-вопрос на 3 шаге»]
```

### 4. Output (что появится наблюдаемо)
```
Артефакт / событие, которое можно показать пальцем:
> [например: «новый шаг в воронке onboarding с conversion данными»]
```

### 5. Outcome (что изменится в реальности)
```
Реальное последствие для роли (через 5 so-what):
> output → so what? → so what? → ... → real outcome для роли
```

### 6. Качественные метрики
| # | Метрика | Как измеряем | Источник данных |
|---|---|---|---|
| 1 | Самоощущение PM «вижу что работает» | вопрос на ретро | заметка ретро |
| 2 | Команда продолжает использовать | observation после 14 дней | наблюдение |

### 7. Количественные метрики
| # | Метрика | Baseline (текущее значение) | Threshold (минимум для подтверждения) | Источник |
|---|---|---|---|---|
| 1 | retention day 7 | 38% | ≥ 45% | analytics |
| 2 | onboarding completion | 62% | ≥ 70% | events |

### 8. Critical chain
```
Что должно случиться по порядку чтобы гипотеза подтвердилась:
1. Изменение деплоится в прод
2. Минимум 200 новых пользователей увидят его за 14 дней
3. Метрика № 1 поднимется выше threshold
4. Команда увидит изменение в weekly review
5. Решение принимается: continue / iterate / abandon
```

### 9. Falsification criterion
```
Что должно произойти чтобы гипотеза считалась провалившейся:
> [например: «после 21 дня и 500+ пользователей retention day 7 ≤ 40%
> ИЛИ команда перестала использовать onboarding-step»]
```

### 10. Stopping criteria
```
Когда останавливаем эксперимент даже если результаты неоднозначные:
- При negative side-effect: ... [список]
- При тривиальной стоимости отката: ... [условия]
- При окне времени: > 30 дней без сигнала
```

### 11. Cognitive bias checks
| Bias | Как проверить | Verdict |
|---|---|---|
| Confirmation bias | Я ищу только данные подтверждающие гипотезу? | ... |
| Anchoring | Я анкорю на baseline и не вижу что метрика shifted? | ... |
| Survivorship bias | Я смотрю на survivors, но не на churned cohort? | ... |
| Sunk cost | Я продолжаю потому что уже вложился? | ... |

### 12. RAT (Riskiest Assumption Test)
```
Самое рискованное предположение в гипотезе (если оно неверно — вся гипотеза рушится):
> [например: «новые пользователи в принципе видят шаг 3, не уходят раньше»]

Что делать ДО основного эксперимента чтобы проверить RAT:
> [небольшой A/B на видимости шага 3 за 2 дня]
```

## Worked example

См. [`worked-examples/01-hypothesis-gap-falsification-marketing-funnel.md`](../worked-examples/01-hypothesis-gap-falsification-marketing-funnel.md).

## Связанные

- [`skills/14-actionable-hypothesis.md`](../skills/14-actionable-hypothesis.md)
- [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md)
- [`agents/hypothesis-designer.md`](../agents/hypothesis-designer.md)
