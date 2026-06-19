# Getting Started — Heroes Harness (для Миши и новых участников)

> Прочитай это один раз после `git clone`. Цель: за 5 минут понять, **что это за
> харнесс, как он сам ставится, какие скилы/агенты есть и как вести задачи**.

---

## 0. TL;DR — что произойдёт после клона

1. Ты клонируешь репо и открываешь его в Claude Code / Codex.
2. **SessionStart-хук сам себя активирует** (`scripts/harness_bootstrap.py`):
   chmod хуков → портабилизация путей → **установка toolchain** → checksum → wiring.
3. В чат печатается чеклист `# Heroes Harness — getting started` с таблицей
   PASS/WARN/FAIL. `🟢 harness готов` = всё на месте.
4. Если toolchain неполон — один раз автоматически запускается
   `scripts/setup/install_all.sh` (ставит `bd`, Dolt, python-deps).
   Доустановить вручную в любой момент: `bash scripts/setup/install_all.sh`.

Ничего руками настраивать **не нужно**. Если хук показал `WARN`/`FAIL` — в колонке
DETAIL написана точная команда.

---

## 1. Что это за харнесс

Два слоя в одном репо:

- **Контентный слой (Gap Theory)** — методология диагностики разрывов (gaps) между
  ожиданием и реальностью. Это `standards/`, `skills/`, `agents/`, `examples/`,
  `playbook/`. Это то, ради чего репо существует.
- **Governance-слой (обвязка)** — `.claude/hooks/`, `.agents/skills/`, `scripts/`,
  `config/`. Это «иммунная система» репо: гейты, которые **принуждают** держать
  чистоту (ветка+задача перед правкой, структура папок, целостность файлов).

«DAC DB» (на слух) = **Dolt DB** — БД-движок под задачником `beads`. «Graphify» —
опциональный canonical-only инструмент графа зависимостей (в шаблон не входит;
граф задач доступен через `bd graph` + `networkx`).

---

## 2. Структура папок — куда смотреть

| Папка / файл | Что это | Когда нужно |
|---|---|---|
| `README.md` | TL;DR методологии, таблица «кому что брать» | первым делом |
| `AGENTS.md` | правила для AI-агентов (инварианты ветка+задача) | до первой правки |
| `docs/GETTING_STARTED.md` | **этот файл** | онбординг |
| `docs/glossary.md` | термины Gap Theory | по ходу |
| `standards/` (9) | каноничные стандарты методологии | методология |
| `skills/` (19) | методологические скилы — запускаются как `/имя` | применение |
| `agents/` (10) | субагенты (инвеститор, ревьюеры, дизайнеры) | делегирование |
| `examples/`, `worked-examples/` | разобранные кейсы диагностики | как делать |
| `playbook/` | AI-management плейбук | управление |
| `.agents/skills/` (13) | **governance-скилы** обвязки (beads, worktree, land) | механика |
| `.claude/hooks/` (19) | gate-хуки (блокируют грязные действия) | авто |
| `scripts/` | bootstrap, установщик, worktree, checksum, валидаторы | обслуживание |
| `scripts/setup/install_all.sh` | **установщик всего toolchain** | после клона |
| `config/root-structure-manifest.yaml` | SSOT: что куда класть в репо | при создании файлов |
| `.beads/` | **Dolt DB задач** (gitignored локально) | ведение задач |

---

## 3. Скилы — что можно запускать

**Методологические (`skills/`, вызов `/имя` или по описанию):**

| Скил | JTBD |
|---|---|
| `01-hypothesis-gap-falsification` | фальсифицировать свою гипотезу до того как поверил |
| `02-rca-incidents-with-effort-scale` | RCA инцидента + оценка glue effort (0-100) |
| `08-root-cause-first` | не чинить симптом без корневой причины |
| `09-critical-chain-design` | спроектировать критическую цепочку задач |
| `19-orchestrator-pipeline` | 12-стадийный пайплайн с QA/design/фальсификация-гейтами |
| …ещё 14 | enumeration, outcome-ladder, persuasion, trust-metric и др. |

**Governance (`.agents/skills/`) — обвязка задач и git:**

| Скил | Для чего |
|---|---|
| `1-change-task-and-project-state-via-beads` | как вести задачи через `bd` |
| `1-critical-chain-status-report` | `{project}.todo.md` — статус критической цепочки |
| `5-git-parallel-coordination` | параллельная работа в worktree без конфликтов |
| `5-land-to-main-mechanical` | механический мёрдж ветки в `main` |
| `0-root-structure-guardian` | куда класть новый файл (по манифесту) |

---

## 4. Агенты (`agents/`) — кого звать

| Агент | Роль |
|---|---|
| `rca-investigator` | копает корневую причину бага/инцидента |
| `process-correspondence-investigator` | диагностика команды по переписке/звонкам |
| `hypothesis-designer` | формулирует фальсифицируемые гипотезы |
| `code-reviewer` / `ui-qa-engineer` | ревью кода / QA интерфейса |
| `manager-lead-orchestrator` | дирижирует многошаговой работой |
| `outcome-designer` / `design-art-director` / `client-persona-reviewer` / `inception-reviewer` | продукт/дизайн/персоны |

---

## 5. Как вести задачи (главный воркфлоу)

Задачи живут в **beads** (`bd`) — БД в репо (Dolt), не в markdown-TODO.

```bash
bd ready                  # что готово в работу (без блокеров)
bd create --title="JTBD: Когда <ситуация>, хотим <результат>" --type=task
bd update <id> --claim    # взять в работу
bd show <id>              # детали + зависимости
bd graph                  # граф зависимостей задач
bd close <id>             # завершить
bd dep add <A> <B>        # A зависит от B
```

**Инвариант репо (это принуждается хуками!):** перед любой существенной правкой —

```bash
bd create --title="JTBD: ..." --type=task          # 1. завести задачу
python3 scripts/make_worktree.py <bead-id> --claim  # 2. свой worktree+ветка
# 3. {project}.todo.md — критическая цепочка (скил 1-critical-chain-status-report)
```

Если попробуешь писать критический файл прямо на `main` без ветки+задачи —
`first_substantial_write_branch_bead_gate.py` **заблокирует** (exit 2). Это by design:
чистый `main`, каждая задача изолирована в своём дереве.

---

## 6. Бизнес-процесс / жизненный цикл изменения

```
идея/баг
  → bd create (JTBD-задача)
  → make_worktree (ветка+изолированный checkout)
  → {project}.todo.md (критическая цепочка)
  → правки в worktree (хуки-гейты следят за чистотой и структурой)
  → quality gates (pytest, валидаторы скилов, checksum)
  → land-to-main-mechanical (мёрдж в main)
  → bd close + (по профилю) git push / bd dolt push
```

**Профили прав (из CLAUDE.md):**
- **Conservative (по умолчанию):** агент НЕ коммитит/пушит сам — отчитывается и ждёт.
- **Team-maintainer (opt-in):** можно закрывать beads, гонять гейты, коммитить, пушить.

---

## 7. Установка и проверка вручную

```bash
bash scripts/setup/install_all.sh           # поставить недостающее (idempotent)
bash scripts/setup/install_all.sh --check    # только отчёт, ничего не ставит
python3 scripts/harness_bootstrap.py         # пере-активировать обвязку + getting-started
python3 scripts/harness_bootstrap.py --check  # read-only самодиагностика
python3 .claude/hooks/harness_guardian_check.py  # живой статус harness (wiring/graph/tools)
```

Что ставит установщик: `.venv` + `requirements.txt` (pytest, PyYAML, networkx),
`bd` (beads), `dolt`, `bd init`. `graphify` — помечается optional (нет публичного
источника). Подробности почему так — `docs/why-harness-not-installed-5-whys.md`.
