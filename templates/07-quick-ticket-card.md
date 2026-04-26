# Template: Quick Ticket Card

> Однострочная шапка + ВСЕ секции тикета. Используется на стадии 1 (Intake) оркестратора и ДО любой substantial работы. Без неё — bead/Linear/Jira/беклог-карточка не создаётся.

## Шаблон

```yaml
---
id: <namespace>-<slug>      # pr-rick-mcp-events-api-refactor
title: <одна фраза>
type: feature | bugfix | refactor | research | doc | spike
priority: P0 | P1 | P2 | P3
owner: <name>
created: YYYY-MM-DD
status: backlog | in_progress | in_review | done
---
```

### JTBD (атомарный)

```
Когда я <ситуация / триггер>,
я хочу <что хочу делать / получить>,
чтобы <что для меня станет возможным / изменится>.
```

Размер: 2-3 строки. Если нужно больше — JTBD не атомарный, расщепи.

### Контекст

| Что | Описание |
|---|---|
| Что уже пробовал | ... |
| Что не сработало | ... |
| Какие альтернативы рассмотрены | ... |
| Что мне известно НЕ из этого тикета | ... |
| Связанные тикеты / стандарты / скилы | ... |

### Output checklist (что появится наблюдаемо)

```
☐ <output 1: файл / документ / артефакт>
☐ <output 2>
☐ <output 3>
```

### Outcome (через 5 so-what)

```
Output → so what?
       → so what?
       → so what?
       → so what?
       → real outcome для роли
```

### Definition of Done

```
☐ Все output появились
☐ QA gate прошёл (subagent-call успешен)
☐ Design review прошёл
☐ Self-falsification verdict = confirmed (или partial с понятным next action)
☐ Outcome verify запланирован на дату ...
```

### Test cases (manual)

| # | Action | Expected | Pass / Fail |
|---|---|---|---|
| 1 | ... | ... | ... |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |

Минимум 5-10 строк для substantial задачи.

### Corner cases (5W+H × роль)

```
- Что если пользователь без аккаунта? ...
- Что если данные пустые? ...
- Что если задача дублирует существующее? ...
- Что если изменение откатить через 1 час? ...
- Что если 100 пользователей делают это одновременно? ...
- Кто получает уведомление если что-то пошло не так? ...
```

### Blockers / dependencies

```
- Blocked by: <ticket / person / stage>
- Depends on: <prerequisite>
- Blocks: <downstream tickets>
```

### Next-action digest

```
Следующий шаг: <одна фраза>
Кто: <name>
Когда: <дата или event>
Усилие человека (0-100): <балл>
```

## Hard rules

1. **Card создаётся ДО bead-тикета и ДО первого `Write`/`Edit`** в файлы.
2. **Все секции заполнены**, не только header. Card без JTBD = invalid.
3. **Owner делает review card** перед началом implementation.
4. **При rewrite старого тикета** — card создаётся заново, не правится поверх (старая card остаётся в комментарии).

## Связанные

- [`skills/15-next-outcome-output-mapping.md`](../skills/15-next-outcome-output-mapping.md)
- [`templates/08-jtbd-scenarium-tree.md`](08-jtbd-scenarium-tree.md)
- [`templates/10-so-what-ladder.md`](10-so-what-ladder.md)
