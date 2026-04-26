# Template: Expected Output Table (контракт ДО implementation)

> Перед любой реализацией (код / отчёт / снапшот / миграция / экспорт) команда обязана показать таблицу того что появится в результате. Без неё — implementation заблокирован.
>
> **RCA-источник:** многократные инциденты «агент написал 1000+ строк кода до того как показал владельцу expected rows».

## Правило ориентации (строгое)

- **Поля / параметры / группировки → колонки**
- **Примеры данных → строки**

**Запрещено** делать строками `field / type / example / required` — это schema, не output. Schema описывается отдельно и НЕ заменяет expected rows.

## Шаблон

### Output type (что это будет)

```
☐ Code (signatures of new functions/classes)
☐ Snapshot / JSON (flat view of records)
☐ Report / sheet (rows of metrics by cohort)
☐ Migration (table changes)
☐ API response (JSON keys и values примеры)
☐ Document / artifact (sections + key claims)
```

### Expected rows (минимум 3 примера, лучше 5-10)

#### Example 1: код-сигнатуры новых методов

| # | method | signature | returns | raises |
|---|---|---|---|---|
| 1 | `calculate_glue_effort` | `(team_size: int, integration_points: int) -> int` | `0-100 score` | `ValueError if team_size < 1` |
| 2 | `classify_gap` | `(symptom: str) -> Literal["knowledge","execution","feedback","integration"]` | gap type | `ValueError if symptom empty` |
| 3 | `falsify_hypothesis` | `(h: HypothesisCard, evidence: list[Evidence]) -> Verdict` | verdict object | — |

#### Example 2: report rows

| # | cohort | leads | first_orders | cr1 | gross_profit | conversion_step |
|---|---|---|---|---|---|---|
| 1 | 2026-04-week-1 | 1240 | 96 | 7.7% | 12480 | search → browse |
| 2 | 2026-04-week-2 | 1180 | 89 | 7.5% | 11250 | search → browse |
| 3 | 2026-04-week-3 | 1320 | 112 | 8.5% | 14080 | search → browse |

#### Example 3: API response

| # | request | status | response.data.id | response.data.gap_type | response.data.effort_score |
|---|---|---|---|---|---|
| 1 | POST /diagnose с симптомом «не знаю как настроить» | 200 | "g-001" | "knowledge" | 30 |
| 2 | POST /diagnose с симптомом «знаю, но не делаю» | 200 | "g-002" | "execution" | 50 |
| 3 | POST /diagnose без симптома | 422 | null | null | null |

### Δ-таблица после реализации (post-implementation gap check)

После того как реализация готова, заполняется зеркальная таблица:

| # | Колонка | Ожидание (из expected output) | Факт (из реальной выгрузки) | Verdict |
|---|---|---|---|---|
| 1 | `cr1` для week-1 | 7.7% | 7.7% | ✅ match |
| 2 | `gross_profit` для week-2 | 11250 | 10980 | ⚠️ partial — расхождение -2.4% |
| 3 | `conversion_step` для week-3 | "search → browse" | null | ❌ falsified — поле не заполнилось |

**Hard fail:** если в Δ-таблице есть `falsified` строки — implementation возвращается на доработку, не доставляется.

## Anti-patterns

- ❌ Schema-style таблица с колонками `field / type / example / required` (это schema, не output)
- ❌ Примеры заполнены `TODO` / `пример` / пусто
- ❌ Только одна строка примеров — нужно минимум 3 для разнообразия
- ❌ После реализации не сделана Δ-таблица

## Связанные

- AGENTS.md §Mandatory delivery format
- [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md)
- [`templates/05-gap-table.md`](05-gap-table.md)
