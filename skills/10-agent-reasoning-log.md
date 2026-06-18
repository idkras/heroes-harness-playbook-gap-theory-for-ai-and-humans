---
name: agent-reasoning-log
description: "Универсальный протокол reasoning log для ВСЕХ скилов. Когда owner хочет понять, почему агент принял конкретное решение, какие инструкции в стандартах/скилах помешали или помогли, и где расхождение ожидания-реальности — этот протокол обязывает вести таблицу решений с evidence и blocking instructions."
---

# Agent Reasoning Log — универсальный протокол для всех скилов

## Hired for JTBD

Когда owner хочет понять, почему агент принял конкретное решение, какие инструкции повлияли и где расхождение между ожиданием и реальностью → найти ответ в reasoning log, а не в памяти агента.

## When to use

- При каждом исполнении **любого** скилла (протокол инъецирован в 114 скилов)
- Когда owner спрашивает «почему ты так решил»
- Когда нужно найти инструкцию в стандартах/скилах, которая помешала сделать правильно
- Когда задача длится >3 ходов — лог сохраняется в файл

## Формат reasoning log в чате

```markdown
### Reasoning Log — [дата UTC]
| # | Решение | Источник evidence | Найден геп | Блокирующая инструкция | Ценность для owner |
|---|---------|-------------------|------------|------------------------|-------------------|
| 1 | {что решил агент} | {файл / команда / API} | {G01 — краткое имя гепа или «—»} | {path + секция + цитата ≤80 или «—»} | {что получил owner} |
```

**§0 macro:** колонка «Найден геп» — не голый `G01`, а **`G01 — краткое имя гепа`**. Голый код без подписи = hard fail (см. `AGENTS.md` §0 и `hypothesis-gap-falsification` §0).

## Формат записи в ai.incidents.md

Каждый вызов скилла оставляет строку в `<internal-folder>/ai.incidents.md` → таблица `## Append-only trace`:

```
| {UTC date} | {skill_name} | {owner prompt ≤240} | {steering: yes/no} | {target artifact} | {reasoning bullets} | {blocking_instruction} |
```

## Формат файлового лога (задачи >3 ходов)

Сохранять в `<internal-folder>/reasoning-logs/{date}-{skill}-{short-id}.md`:

```markdown
# Reasoning Log — {skill_name}
**Date:** {UTC}
**Owner prompt:** {≤240 chars}
**Task:** {краткое описание}

## Decisions
| # | Решение | Evidence | Геп | Блокирующая инструкция | Ценность |
|---|---------|----------|-----|------------------------|----------|

## Summary
- Гепов найдено: N
- Блокирующих инструкций: N
- Итог: {что сделано / что осталось}
```

## Метрики (считаем еженедельно)

- `reasoning_log_coverage` = скиллы с протоколом / всего скилов (target: 100%)
- `blocking_instruction_rate` = строки с blocking instruction / всего строк trace (target: снижение)
- `gap_discovery_rate` = строки с найденным гепом / всего строк (information only)

## Hard fail conditions

Скилл считается неисполненным, если:

1. Нет reasoning log в чате (ни таблица, ни bullets)
2. Нет evidence source (откуда факт — файл, команда, API)
3. Нет колонки blocking instruction (даже если «—»)
4. Нет колонки owner value (даже если «информация»)
5. Не записана строка в ai.incidents.md trace

## Owner value

Каждый reasoning log позволяет owner: (1) находить инструкции которые мешают, (2) видеть цепочку решений агента, (3) отслеживать метрики качества взаимодействия.

## Связанные скилы

- [`owner-prompt-capture`](.agents/skills/owner-prompt-capture/SKILL.md) — автозапись промтов owner
- [`hypothesis-gap-falsification`](.agents/skills/2-hypothesis-gap-falsification/SKILL.md) — фальсификация гипотез
- [`rca-incidents`](.agents/skills/2-rca-incidents/SKILL.md) — анализ корневых причин

## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)

Этот скилл сам является протоколом reasoning log. При каждом его применении агент ведёт reasoning log по формату, описанному выше в разделах «Формат reasoning log в чате» и «Формат записи в ai.incidents.md».

Hard fail: скилл считается неисполненным, если reasoning log отсутствует.


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
