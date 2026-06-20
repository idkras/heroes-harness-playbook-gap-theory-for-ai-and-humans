# projects/ — реестр проектов харнесса

Здесь живут проекты, которые ведутся в этом харнессе. **Вся работа запускается через
связку Beads → worktree → Graphify** — не через markdown-TODO.

## Модель: один проект

```
projects/
  <project-slug>/
    README.md        # JTBD проекта, владелец, ссылки
    <project>.todo.md  # критическая цепочка (скил 1-critical-chain-status-report)
```

Задачи проекта живут **не в файлах, а в Beads** (Dolt DB). Папка проекта — только
человекочитаемый вход; источник истины по задачам — `bd`.

## Как запустить работу по проекту (каждый раз)

```bash
# 1. задача в beads (источник истины)
bd create --title="JTBD: Когда <ситуация>, хотим <результат>" --type=task
#    эпик проекта:  bd create --title="..." --type=epic
#    связи:         bd dep add <child> <parent>

# 2. изолированный worktree+ветка под задачу
python3 scripts/make_worktree.py <bead-id> --claim

# 3. граф зависимостей (Graphify) — пересобрать после изменений задач
python3 scripts/graphify.py            # → graphify-out/graph.json
python3 scripts/graphify.py --doctor    # проверить queryability
bd graph --all                          # быстрый просмотр в терминале

# 4. по завершении
bd close <bead-id>
```

## Связка инструментов (что подключено)

| Инструмент | Роль | Команда проверки |
|---|---|---|
| **Beads** (`bd`) | источник истины по задачам/проектам | `bd list` |
| **Dolt** | БД-движок под beads + sync (`refs/dolt/data`) | `bd dolt push` |
| **Graphify** (`scripts/graphify.py`) | граф зависимостей задач+процесса → `graphify-out/graph.json` | `python3 scripts/graphify.py --doctor` |

Полный воркфлоу — [`harness-workflow.yaml`](../harness-workflow.yaml),
онбординг — [`docs/GETTING_STARTED.md`](../docs/GETTING_STARTED.md).

## Реестр проектов

| Проект (slug) | JTBD | Beads-эпик | Статус |
|---|---|---|---|
| _пример_ | _Когда …, хотим …_ | `bd create --type=epic` | — |

> Добавляя проект: создай `projects/<slug>/`, заведи эпик в beads и впиши строку сюда.
