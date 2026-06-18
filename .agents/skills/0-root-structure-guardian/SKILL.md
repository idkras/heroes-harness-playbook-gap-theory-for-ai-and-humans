---
name: 0-root-structure-guardian
description: >
  Guardian чистоты КОРНЯ workspace (не путать с 0-project-structure-guardian — тот про
  папку клиента/проекта). Use BEFORE создания нового top-level файла/папки в корне
  workspace, при аудите «что за левые папки в корне», при подготовке sync/merge в main,
  или когда owner говорит «почисти корень», «каких папок не должно быть», «куда это
  перенести», «индексация корня». SSOT — config/root-structure-manifest.yaml (что
  разрешено в top-level + куда роутить stray). Инструмент — scripts/root_structure_router.py
  (классификатор + dry-run report + --apply с collision-защитой). Механический gate —
  .claude/hooks/root_new_entry_gate.py (PreToolUse Write+Bash блок нового stray top-level).
  Универсален: pattern-based, без hardcode клиента; новый клиент/проект под routing-правила
  без правки. Триггеры — «почисти корень», «индексация корня», «что за левые папки»,
  «куда перенести файл», «каких папок не должно быть в корне», «root cleanup»,
  «root structure guardian», «классифицируй top-level».
---

**Mode:** [ACTIVE] — обязательный вызов ПЕРЕД созданием нового top-level entry в корне workspace и при любом аудите/чистке корня.

# Root structure guardian (канон корня workspace + router + hook)

## §0 Зачем (RCA-источник 2026-06-02, owner /goal)

После merge в origin/main owner увидел в корне 167 top-level записей, много «левых»: `docs/` bloat, 13× stray `*.todo.md`, 4 stray `*.py`, output-мусор (`*.png`/`*.log`/`*.xlsx`), 0-byte accidental файлы (`index` 4.9MB / `lead` / `transaction`), дубли (`projects/` vs `<internal-folder>/`, `tools/` vs `tooling/`, `workshops/` vs `[workshops]/`), и 42GB client <layer>/quarantine данных в рабочем дереве.

Корень: **ни `0-project-structure-guardian` (про папку клиента), ни `0-main-cleanliness-guard` (про git-гигиену) не определяли КАНОН корня workspace** — что вообще разрешено в top-level и куда роутить остальное. Owner: «проверь скил guardian и проверь где они должны лежать все и каких папок в корне не должно быть … спроектируй системное решение без легаси, universal для всех клиентов».

## §1 JTBD

**Когда** агент создаёт новый файл/папку в корне ИЛИ owner просит почистить/проиндексировать корень, **хочу** механически свериться с единым манифестом (что разрешено в top-level + куда роутить stray) и классифицировать каждую запись (allowed / route / junk / owner_decision / large_data), **чтобы** корень оставался review-safe, в нём не накапливались «левые» папки/файлы, а крупные client-данные оставались вне git (через .gitignore + Syncthing), а не раздували репозиторий.

Owner benefit: открывает корень в IDE и видит только канонические записи; новый stray не появляется (хук блокирует Write И Bash mkdir/cp/mv); крупные данные не ломают `git push` (GitHub лимит 100MB/файл); один прогон router'а даёт полный индекс + план переноса.

## §2 Trigger (когда обязателен)

- агент собирается `Write` / `mkdir` / `cp` / `mv` / `touch` нового top-level entry в корне workspace;
- owner: «почисти корень», «индексация корня», «что за левые папки», «куда перенести», «каких папок не должно быть»;
- подготовка sync/merge в main (companion к `0-main-cleanliness-guard`);
- периодический аудит (`cleanup-guardian` Category 27 root-manifest-drift).

Не активируется для записи ВНУТРИ уже-канонической папки (`scripts/foo.py`, `<internal-folder>/clients/...`) — это scope `0-rick-client-kb-save-gate` / `0-document-creation-guard`.

## §3 Workflow

### Шаг 1 — Индекс корня (router report, дерево В ТЕЛО сообщения)

```bash
python3 scripts/root_structure_router.py \
  --root "$WORKSPACE_ROOT" \
  --manifest config/root-structure-manifest.yaml \
  --report --out "$WORKSPACE_ROOT/root-index-report.md"
```

Скопируй markdown-отчёт (5 verdict-групп + large_data + счётчики) в **тело** assistant-сообщения (НЕ оставляй в свёрнутом Bash-чипе — Cowork rendering rule, RCA 2026-06-01). `unknown` должно быть 0; если >0 — дотриажить в манифест (добавить allowed/junk/routing-правило), НЕ оставлять unknown.

### Шаг 2 — Классификация (5 verdict)

| verdict | значение | действие |
|---|---|---|
| **allowed** | точное имя в allowed_* ИЛИ bracketed-pattern ИЛИ symlink | оставить |
| **route** | stray, есть target | `--apply --only route` (git mv tracked / mv untracked, **collision-safe**: пропуск если target существует) |
| **junk** | мусор (`*.log`/`*.png`/0-byte stray/`.DS_Store`) | `--apply --only junk` → `<root>/.cache/root-trash/<ts>/` (обратимо, вне корня) |
| **owner_decision** | дубль/легаси/политика (`projects`, `workshops`, legacy bracketed) | НЕ авто; вывести owner с рекомендацией + deadline |
| **large_data** | client <layer>/<layer>/gold > threshold_mb | → .gitignore in-place (Syncthing синкает реальный путь, см. §4) |

### Шаг 3 — Apply (dry-run по умолчанию)

Сначала всегда dry-run (без `--apply`) → показать план. `--apply` выполняет moves: route + junk автономно (reversible — collision-safe git mv / trash вне корня). large_data + owner_decision router НЕ двигает (report-only). Перед первым `--apply` на реальном корне — backup tracked-state через git (ветка/worktree).

### Шаг 4 — Falsify

После apply прогнать `2-hypothesis-gap-falsification`: гипотеза «корень чист», gap table Ожидание|Факт|Δ (re-run report → unknown=0, route=0, junk=0 после переноса), verdict confirmed|partial|falsified.

## §4 Large data — .gitignore in-place + Syncthing (НЕ symlink в git)

Крупные client `<layer>/<layer>/<layer>/_quarantine` (> `large_data.threshold_mb`, на 2026-06-02 ~42GB) НЕ коммитятся в git (GitHub лимит 100MB/файл, раздутие репо). **Стратегия `gitignore_in_place`** (НЕ `move_then_symlink`):

- данные **остаются на своём месте** (`<internal-folder>/clients/.../bronze`);
- путь добавляется в `.gitignore` → не в git;
- **Syncthing синкает реальный путь** между машинами команды (P2P);
- **НЕТ symlink в git.**

**Почему не symlink (design-review F3+F10, CATEGORICAL no-go):** symlink `bronze → ../../syncthing/...` закоммиченный в git ломается при `git clone` на машине без Syncthing (Cursor Cloud / CI / новый teammate) → broken symlink → MCP-читатели bronze (`data_manager.py`, `<internal-component>_server.py`) падают `FileNotFoundError`. Это нарушает §Nothing-lost «команда может воспользоваться всем». `gitignore_in_place` оставляет реальную папку на месте — код её резолвит независимо от Syncthing-статуса; Syncthing лишь реплицирует содержимое.

Router `scan_large_data` репортит кандидатов > threshold + предлагает `.gitignore`-строки (`/<internal-folder>/.../<layer>/`). Apply для large_data = только печать предлагаемых строк, НЕ move.

## §5 Hard fail

- Новый top-level entry создан в корне (Write ИЛИ Bash mkdir/cp/mv/touch) без сверки с манифестом (verdict ≠ allowed) и без routing → `category: root-stray-created-without-guardian`.
- `unknown > 0` оставлено без дотриажа в манифест → `category: root-entry-unclassified`.
- 42GB+ client data закоммичено в git (вместо .gitignore in-place) → `category: large-data-committed-to-git`.
- symlink на gitignored путь закоммичен в git → `category: broken-symlink-in-git` (ломает clone без Syncthing).
- Удаление (не trash) junk без go owner → `category: root-junk-deleted-not-trashed`.

## Input checklist

Формат — AGENTS.md §Макрос {io-checklist}.

| ✓ | Что на входе | Факт |
|---|---|---|
| ✅ | манифест-SSOT существует | `config/root-structure-manifest.yaml` |
| ✅ | router исполним + протестирован | `scripts/root_structure_router.py` + 59 pytest tests |

## Output checklist

| ✓ | Что на выходе | Факт |
|---|---|---|
| ✅ | индекс корня (5 verdict + счётчики) | `root_structure_router.py --report`, unknown=0 |
| ⚠️ | корень очищен (route+junk перенесены) | `--apply` после owner go на destructive часть |

## Outcome checklist (owner benefit)

| ✓ | Какая выгода | Факт / проверка |
|---|---|---|
| ⚠️ | owner видит в корне только канон | re-run report: route=0 junk=0 unknown=0 после apply |
| ✅ | новый stray не появится | хук `root_new_entry_gate.py` блокирует Write+Bash |

## Owner value

owner value: корень workspace review-safe навсегда — один манифест-SSOT + хук-гейт (Write+Bash) предотвращают рецидив «левых папок», крупные данные не раздувают git и не ломают clone.

## Self-falsification gate

После исполнения скилл обязан прогнать гипотезу «корень чист и канон закреплён» через [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md): gap table Ожидание | Факт | Δ, verdict confirmed | partial | falsified. При partial/falsified — новая рабочая гипотеза, не закрывать как done.

## Reasoning Log Protocol

Каждое исполнение ведёт reasoning log (решения + evidence + gap + blocking instruction) и строку в `<internal-folder>/ai.incidents.md` §Append-only trace. Hard fail: без reasoning log скилл не исполнен. Канон — `agent-reasoning-log` в AGENTS.md.

## Связанные скилы / Related skills

- [`0-project-structure-guardian`](../0-project-structure-guardian/SKILL.md) — парный guardian, но про папку клиента/проекта (pre-read), не корень
- [`0-main-cleanliness-guard`](../0-main-cleanliness-guard/SKILL.md) — git-гигиена main (dirty/diverged), companion при sync
- [`0-document-creation-guard`](../0-document-creation-guard/SKILL.md) — §0 Intent Router, куда писать новый документ
- [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md) — self-falsification gate
- `agent-reasoning-log` — обязательный reasoning log протокол (AGENTS.md)

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick. Развивается как часть единой системы навыков `.agents/skills/`.
