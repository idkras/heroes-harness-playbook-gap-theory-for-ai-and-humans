---
name: 5-land-to-main-mechanical
description: "Use when a feature branch / PR must reach origin/main but a naive merge/rebase thrashes — stale base (many commits behind), shared-state conflicts (counter / issues.jsonl / ai-promts.md), re-exportable data or >100MB files in history, cascading hook blocks, or you catch yourself reaching for --no-verify. Triggers: «довести ветку до origin/main», «branch consolidation», «PR конфликтует / behind», rebase-hell, «ничего не потеряй»."
---

**Mode:** [ACTIVE]

## Hired for (JTBD)
Когда у меня есть ветка с уникальной работой, но довести её до origin/main наивным merge/rebase
невозможно без многочасового боя (stale base, shared-state, 110MB, каскад хуков) — я хочу
**механически извлечь только уникальную работу и приземлить её чисто**, ничего не потеряв, чтобы
команда воспользовалась результатом. RCA 2026-06-02: без этого аффорданса каждый landing = ручная
§Nothing-lost классификация + --no-verify + plumbing-хаки (которые САМИ есть риск потери).

## Owner value
Вал из N открытых PR рассасывается механически, без потери работы и без поломки origin/main.
`--no-verify` и rebase-ад больше не нужны.

## Workflow
1. **Triage (read-only):** `python3 scripts/land_to_main.py <branch> [...]`. Для каждой ветки
   классифицирует ADDED-файлы относительно `merge-base(origin/main, branch)`:
   - `unique` — нет в origin/main → приземлить;
   - `superseded` — идентичны origin/main → закрыть+archive;
   - `data/scratch` — <layer>/<layer>/<layer>/issues.jsonl/counter → исключить (re-exportable);
   - `oversized` — >50MB → исключить (Git LFS / bronze).
2. **Apply:** `... --apply`. Archive-тегает ветку (`archive/land-<branch>`, zero-loss), затем:
   - `SUPERSEDED` → `gh pr close <n>` (контент уже в main);
   - `LANDED` → строит `commit-tree` = `origin/main` + ТОЛЬКО unique-файлы (без stale-base M/D,
     без 110MB-истории, без shared-state), force-push в ветку → `gh pr merge <n> --squash`.
3. **MODIFIED shared files** (например `hooks-registry.json`) triage показывает отдельно — их
   приземляют 3-way merge'ем конкретного файла (union), не overlay'ем.
4. **MODIFIED non-shared files / explicit rescue overlay:** если rebase/cherry-pick блокируется
   локальным submodule/sequencer состоянием, но нужный scope уже классифицирован вручную, использовать
   только `python3 scripts/git_clean_ref_overlay.py --source <ref> --paths-file <allowlist> --expected-count <N>`.
   Запрещено писать ad-hoc shell `commit-tree` loop: zsh `path`/`PATH`, stale-base diff и implicit
   path expansion уже приводили к polluted PR. Скрипт строит `origin/main + explicit allowlist`,
   валидирует фактический diff и падает при любом extra path.

## Input / Output / Outcome
- **Input (checklist):**
  - [ ] список веток/PR на приземление
  - [ ] origin/main fetched (свежая база)
  - [ ] подтверждено, что pre-push oversized-guard читает реальный push-range (PR #284)
- **Output (checklist):**
  - [ ] per-branch вердикт (LANDED / SUPERSEDED / NOBASE)
  - [ ] archive-tag на каждую тронутую ветку
  - [ ] 0 удалений файлов в landed-коммитах (dogfood)
- **Outcome (checklist):**
  - [ ] уникальная работа достижима из origin/main `git pull`
  - [ ] открытых PR не осталось (или каждый имеет вердикт)
  - [ ] ничего не потеряно (archive-tag ИЛИ контент в main)

## Hard fail (запрещено)
- ❌ `git push --no-verify` / `gh pr merge` мусорной ветки с 110MB или stale-base M/D.
- ❌ Наивный `git merge <stale-branch>` в main (откатит N коммитов origin/main).
- ❌ Закрыть ветку без archive-tag, если в ней есть НЕ-superseded уникальный контент.
- ❌ Приземлить overlay'ем ветку, которая МОДИФИЦИРУЕТ shared-файлы (затрёт чужое — нужен 3-way).

## Self-falsification gate
После приземления прогнать `2-hypothesis-gap-falsification`: гипотеза «вся уникальная работа в
origin/main» фальсифицируется проверкой `git diff --diff-filter=A merge-base..origin/<branch>` →
каждый ADDED-файл должен быть ЛИБО в origin/main, ЛИБО в archive-tag. Если файл нигде — потеря, fix.

## Связанные скилы
- `0-main-cleanliness-guard` — чистота origin/main.
- `5-git-parallel-coordination` — координация параллельных сессий/веток.
- `2-rca-incidents` — фиксация инцидентов landing.
- `make worktree` (#282) — парная команда создания JTBD-worktree.

## Канонические источники
| Источник | Путь |
| --- | --- |
| Скрипт | `scripts/land_to_main.py` |
| Explicit rescue overlay | `scripts/git_clean_ref_overlay.py` |
| Pre-push range fix | `scripts/check_no_oversized_files.py` (PR #284) |

## Reasoning Log Protocol
Перед каждым `--apply` записать в reasoning-log: список веток + вердикт triage. После — per-branch
результат + archive-tag SHA. При `ERR-*` — не закрывать PR, эскалировать в `2-rca-incidents`.

## RCA-источник
2026-06-02 branch-consolidation thrash: 19 открытых PR, stale base + shared-state + 110MB +
HEAD-keyed хуки. Этот скил + PR #284 (pre-push range fix) = механическое приземление без боя.
