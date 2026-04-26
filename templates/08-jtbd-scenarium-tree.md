# Template: JTBD Scenarium Tree (Big / Medium / Small)

> Иерархическое дерево JTBD, используемое для проектирования продукта, фич, диагностики и тестирования. Большой JTBD ломается на средние, средние — на маленькие. Маленькие — это уже test cases.

## Принцип

| Уровень | Что описывает | Размер | Примеры |
|---|---|---|---|
| **Big JTBD** | Стратегическая задача роли (на горизонте недель/месяцев) | 1-3 на роль | «Найти команду для запуска нового продукта» |
| **Medium JTBD** | Функциональная задача внутри Big (на горизонте дней) | 5-15 на Big | «Просмотреть 30 кандидатов на Linkedin за неделю» |
| **Small JTBD** | Операционная задача / интеракция (на горизонте минут) | 5-15 на Medium | «Открыть профиль кандидата → понять подходит ли за 30 секунд» |

**Small JTBD = test case** — это атомарная операция, которую можно проверить.

## Шаблон

### Корень: роль

```
Role: <название роли + контекст>
Example: «Founder тех-стартапа на стадии Series A, ищущий VP Engineering»
```

### Big JTBD (1-3 на роль)

```
Big-1: <стратегическая задача>
  └─ Когда: <триггер>
  └─ Хочу: <что делать>
  └─ Чтобы: <real outcome>
  └─ Размер: недели / месяцы
```

### Medium JTBD (5-15 на Big)

```
Big-1
├─ Medium-1.1: <функциональная задача>
│     └─ Когда: <триггер>
│     └─ Хочу: <что делать>
│     └─ Чтобы: <middle outcome>
│     └─ Размер: дни
├─ Medium-1.2: ...
└─ Medium-1.3: ...
```

### Small JTBD (5-15 на Medium = test cases)

```
Big-1
├─ Medium-1.1
│     ├─ Small-1.1.1: <операционная задача>
│     │     └─ Когда: <триггер>
│     │     └─ Хочу: <конкретное действие>
│     │     └─ Чтобы: <immediate outcome>
│     │     └─ Test: <как проверить что работает>
│     │     └─ Corner cases: <что может пойти не так>
│     ├─ Small-1.1.2: ...
│     └─ Small-1.1.3: ...
└─ Medium-1.2: ...
```

## Worked example: founder ищет VP Engineering

```
Role: Founder, B2B SaaS, Series A, ищет VP Engineering на 12-15 человек

Big-1: Найти и нанять VP Engineering
├─ Когда: команда выросла до 8 инженеров, нужен management layer
├─ Хочу: закрыть позицию за 8 недель
└─ Чтобы: разгрузить себя от code review и 1:1 с инженерами

  ├─ Medium-1.1: Сформировать pipeline кандидатов на 30 человек за 2 недели
  │     ├─ Когда: подписан job description
  │     ├─ Хочу: иметь воронку 30 candidates → 10 phone screens → 5 onsite
  │     └─ Чтобы: конкуренция в воронке давала качественный signal
  │
  │     ├─ Small-1.1.1: Выгрузить из Linkedin 100 потенциальных кандидатов
  │     │     ├─ Test: список из 100 имён + URL профилей в spreadsheet
  │     │     └─ Corner: Linkedin лимитирует поиск > 1000 в день
  │     │
  │     ├─ Small-1.1.2: Написать первое сообщение каждому из 100
  │     │     ├─ Test: 100 отправленных, < 5% марки spam
  │     │     └─ Corner: тон message — холодный или с tepid intro?
  │     │
  │     └─ Small-1.1.3: Получить 30 ответов «да, готов поговорить»
  │           ├─ Test: response rate ≥ 30%
  │           └─ Corner: что если response rate 10% — переписать message
  │
  ├─ Medium-1.2: Провести 10 phone screens за 1 неделю
  │     └─ ...
  │
  └─ Medium-1.3: Сделать предложение и подписать contract
        └─ ...
```

## Применение к продукту / UI

Каждый Small JTBD = test case для UI:

```
Small-1.1.1 (выгрузить кандидатов из Linkedin):
  Test cases:
  - Поиск по location + role title возвращает > 100 результатов
  - Экспорт в CSV содержит url, name, current_company
  - При лимите Linkedin (> 1000 поисков) — graceful error
  - Можно сохранить поиск и вернуться завтра
```

## Применение к диагностике человека / команды

Чтобы найти **где человек/команда теряют время** — построй JTBD-дерево их роли и пройди каждое Small. Где Small существует, но не выполняется → execution gap. Где Small выполняется через 5 переключений контекста → integration gap.

См. worked example: [`examples/02-diagnose-company-from-team-chat.md`](../examples/02-diagnose-company-from-team-chat.md).

## Anti-patterns

- ❌ Big JTBD = «улучшить продукт» — это не JTBD, это стремление
- ❌ Medium и Small смешаны: одни — на минуты, другие — на дни
- ❌ Small без test case — это не Small, это Medium с амбициями
- ❌ Дерево без corner cases — продукт сломается в проде

## Связанные

- [`agents/ui-qa-engineer.md`](../agents/ui-qa-engineer.md) — JTBD-дерево как основа QA
- [`templates/07-quick-ticket-card.md`](07-quick-ticket-card.md)
- [`standards/01-gap-theory.md`](../standards/01-gap-theory.md)
