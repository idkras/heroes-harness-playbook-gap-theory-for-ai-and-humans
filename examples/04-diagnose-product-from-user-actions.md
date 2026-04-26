# Example: Диагностика продукта по действиям пользователя

> **Метод:** через event-логи (что пользователь сделал и что НЕ сделал) находим где продукт создаёт glue effort. Diagnose by silence.

## Контекст

**Кто:** designcraft — design platform, B2C+B2B, freemium, 230k активных пользователей.
**Запрос:** «D7 retention новых пользователей упал с 38% до 27% за 4 месяца. Не понимаем где теряем».

**Что у нас есть:**
- Mixpanel events за 90 дней
- Cohort analysis по неделям регистрации
- 12 user-interview транскриптов (по 30 мин каждый)

## Шаг 1. Восстанавливаем JTBD-дерево пользователя

Big JTBD: «Создать визуальный артефакт (presentation / mockup / social post) за 30 минут от идеи до отправки коллеге».

Medium JTBD:
- M1: Найти template / starting point
- M2: Адаптировать template под мою идею (текст, цвета, контент)
- M3: Сохранить и поделиться (link / export)

Small JTBD под M2 (адаптация — самое сложное):
- S2.1: Заменить placeholder text на свой
- S2.2: Поменять цветовую схему
- S2.3: Добавить свой логотип
- S2.4: Изменить layout одного слайда / страницы
- S2.5: Дублировать элемент

## Шаг 2. Воронка действий из событий (по cohort 4 месяца назад)

```
Регистрация               100%
   ↓
Открытие editor           94%   (good: ↓ 6%)
   ↓
Выбор template            81%   (drop 13%)
   ↓
Замена text (S2.1)        67%   (drop 14%)
   ↓
Замена color (S2.2)       38%   (drop 29% ← 🚨)
   ↓
Добавление logo (S2.3)    21%   (drop 17%)
   ↓
Сохранение                32%   (хм, выше чем S2.3 — некоторые сохраняют без logo)
   ↓
Поделиться link           18%   (drop 14%)
   ↓
D7 retention              27%
```

**Pattern:** самые большие drops:
1. **S2.2 «замена цвета» — 29% drop** (самый большой!)
2. S2.3 «добавление logo» — 17%
3. Поделиться link — 14%

## Шаг 3. Что говорят user interviews про S2.2

Цитаты (анонимизированные):

> «Я выбрал темплейт — а цвета все на бренд-мнения других. Я понимаю что надо изменить, но окно с цветами в правой панели не понятно — там палитра, а где целая схема?» (user 4)

> «Изменил один цвет — и всё посыпалось. Текст стал нечитаемым. Откатил — снова всё хорошо. Решил оставить как есть.» (user 7)

> «Я не дизайнер, мне нужен button "make it match my brand" — а тут отдельные цвета, отдельные шрифты. Слишком много. Бросил.» (user 11)

**Pattern:**
- 7 из 12 описывают **knowledge gap**: «не знаю как менять scheme не отдельные цвета»
- 4 из 12 описывают **execution gap**: «начал, но сломал, бросил»
- 6 из 12 описывают **integration gap**: «нет brand-kit интеграции, выбираю цвета руками»

## Шаг 4. Размечаем gaps + glue effort

### S2.2 «замена цвета» — детальный разрыв

| Симптом | Тип gap | Glue effort | Источник |
|---|---|---|---|
| User не понимает что палитра ≠ scheme | Knowledge | 70 (cognitive) | UI-affordance |
| User меняет цвет → сломалась контрастность → бросает | Execution | 80 (mechanical + cognitive recovery) | Нет защиты от bad color choices |
| User хочет вписать свой brand но это руками | Integration | 90 (mechanical, переключение в Figma / brand guidelines) | Нет brand-kit feature |
| User не получает feedback что «изменение прошло хорошо» | Feedback | 30 | Нет confirm UI |

**Total glue effort на S2.2: 270 единиц** на одного пользователя в первом сеансе.

## Шаг 5. Что было 4 месяца назад (cohort comparison)

Сравниваем cohort_n4 (current, retention 27%) vs cohort_old (4 месяца назад, retention 38%):

| Параметр | cohort_n4 | cohort_old | Δ |
|---|---|---|---|
| S2.2 drop | 29% | 21% | +8% |
| Avg time on color step | 4:20 мин | 2:50 мин | +1:30 |
| % «brand-kit upload» action | 0% (не было фичи) | 14% | -14% (фича была убрана!) |

🚨 **Найдено:** 4 месяца назад была фича «brand-kit upload» — её удалили в релизе 2026-04-15 «cleanup». Никто не заметил эффект на retention.

## Шаг 6. Системные исправления

| Gap | Решение | Тип | Усилие |
|---|---|---|---|
| Knowledge: палитра ≠ scheme | Переименовать UI panel «Color palette» → «Color schemes». Добавить first-time tooltip «один клик → меняет всю scheme» | UI copy + tooltip | 1 спринт |
| Execution: сломалась контрастность | Constraint solver: не позволяет выбрать цвет если контраст < 4.5:1 ratio. Auto-suggest альтернативу | Tech | 2 спринта |
| Integration: нет brand-kit | **Восстановить brand-kit upload** + extend на color extraction из URL/image (paste brand image → extract colors) | Feature recovery + extension | 2 спринта |
| Feedback: нет confirm | Animation + toast «Scheme applied to all 12 elements» | UI animation | 0.5 спринт |

**Эффект (моделирование на cohort_old):**
- S2.2 drop: 29% → 22% (если все 4 решения)
- D7 retention: 27% → 35%
- Не вернёт 38%, но ~80% потерянного

## Шаг 7. Что вернули PM

```
D7 retention упал с 38% до 27% не из-за «трафик стал хуже».

Главная причина: за 4 месяца назад убрали фичу «brand-kit upload»
в cleanup-релизе 2026-04-15. Drop S2.2 (замена цвета) вырос с 21% до 29%.

Brand-kit давал 14% пользователей путь обхода knowledge gap (не нужно
понимать палитру vs scheme — просто загрузил brand image).

4 системные меры (восстановить brand-kit + 3 UX fix'а) дадут retention
27% → 35% (~80% возврата потерянного).

Cost: 5.5 спринтов = 1 квартал.
ROI: 8% retention point на 230k активных = ~18k retained users в первом квартале.

Lesson: cleanup-релизы должны проходить retention gate перед merge.
Без бенчмарка cohort comparison фича удалилась — никто не заметил.
```

## Чему это учит

1. **Diagnose by silence в действиях.** Drop в воронке = пользователи, которые «промолчали» — самый честный feedback.
2. **Cohort comparison обязателен** для любой product-метрики. Без сравнения «что было / что есть» нельзя найти причину drift'а.
3. **Cleanup-релизы — частый источник regression.** Не очевидные фичи могут давать 14% обхода knowledge gap.
4. **UI copy + constraint solver > tutorial.** Пользователь не учится — он либо понимает с одного взгляда, либо уходит.

## Как применить

1. Восстанови JTBD-дерево от регистрации до core action
2. Замерь funnel drops по событиям
3. Для каждого drop > 15% — user interview (5-10 человек)
4. Размeти причины по 4 типам gap
5. Сравни current cohort с тем когда метрика была хорошей
6. Найди не «улучшения» а **regressions** в продукте

## Связанные

- [`templates/08-jtbd-scenarium-tree.md`](../templates/08-jtbd-scenarium-tree.md)
- [`standards/01-gap-theory.md`](../standards/01-gap-theory.md)
- [`agents/inception-reviewer.md`](../agents/inception-reviewer.md)
