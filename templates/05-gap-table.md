# Template: Gap Table (Expectation vs Reality)

> Каноничная таблица для фальсификации гипотезы / проверки доставки. Используется в mandatory delivery section #9 «Hypothesis falsification».

## Минимальные колонки (mandatory)

| # | Expectation | Reality | Δ | Severity | Verdict | Next action | Усилие человека (0-100) |
|---|---|---|---|---|---|---|---|

7 колонок. Меньше — нарушение стандарта (см. RCA 2026-04 «mandatory table columns»).

## Семантика колонок

| Колонка | Что в неё писать |
|---|---|
| `Expectation` | Что должно быть истинно если гипотеза верна. С макросом `E01 — что проверяем` |
| `Reality` | Что фактически наблюдается на диске / в продукте / в данных. Со ссылкой на источник |
| `Δ` | Разница в человекочитаемой форме. Не «несоответствует» — а «ожидали 95%, получили 78%, минус 17 процентных пунктов» |
| `Severity` | `critical` (блокирует доставку) / `high` (нужно исправить до closure) / `medium` (записать в follow-up) / `low` (информационно) |
| `Verdict` | `match` / `partial` / `falsified` |
| `Next action` | Конкретное действие если `partial` или `falsified`. С макросом `G01 — что чинить` |
| `Усилие человека (0-100)` | По шкале из [`02-rca-effort-scale-0-100.md`](02-rca-effort-scale-0-100.md) |

## Минимальный размер

**Минимум 2 содержательные строки.** Декоративная одна строка «всё OK» — не считается. Если действительно 1 проверка — добавь explicit «нет других проверок» с обоснованием.

## Финальный verdict (под таблицей)

После таблицы один из трёх verdict:

```
verdict: confirmed | partially confirmed | falsified
```

- `confirmed` — все строки `match`
- `partially confirmed` — есть `partial` строки, но все `next action`s готовы и плановые
- `falsified` — есть `falsified` строки → доставка заблокирована, идти на re-implementation

При `partially confirmed` или `confirmed` — обязательно применить `2-so-what-outcome-ladder` (см. [`templates/10-so-what-ladder.md`](10-so-what-ladder.md)).

## Worked example

```
| # | Expectation | Reality | Δ | Severity | Verdict | Next action | Усилие человека (0-100) |
|---|---|---|---|---|---|---|---|
| 1 | E01 — README содержит структуру репо | README.md есть, структура есть | — | low | ✅ match | — | 0 |
| 2 | E02 — все 18 скилов скопированы | `ls skills/` = 18 файлов | — | low | ✅ match | — | 0 |
| 3 | E03 — анонимизация прошла без false positives | grep `client-name-leak` → 0 hits | — | medium | ✅ match | — | 0 |
| 4 | E04 — все 10 субагентов скопированы | `ls agents/` = 10 файлов | — | low | ✅ match | — | 0 |
| 5 | E05 — Apache 2.0 license валиден | LICENSE-CODE = official text | — | low | ✅ match | — | 0 |
| 6 | E06 — initial commit запушен в GitHub | `git log` показывает 1 commit, но `git push` ещё не сделан | push pending | high | ⚠️ partial | G01 — запушить до closure | 10 (один git push) |

verdict: partially confirmed
next-action digest: G01 — запушить → 10 единиц усилия владельца (запросить confirmation на push) или 0 (если push авторизован)
```

## Anti-patterns

- ❌ Колонки `Severity` и `Verdict` объединены в одну
- ❌ Отсутствует `Усилие человека (0-100)` — нарушение mandatory format
- ❌ `Δ` = «не совпало» вместо конкретной разницы
- ❌ В `Reality` нет источника (где это видно?)
- ❌ Verdict под таблицей отсутствует или нечёткий («вроде ОК»)

## Связанные

- [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md)
- [`templates/02-rca-effort-scale-0-100.md`](02-rca-effort-scale-0-100.md)
- [`templates/06-owner-effort-digest.md`](06-owner-effort-digest.md)
- AGENTS.md §Mandatory delivery format §9
