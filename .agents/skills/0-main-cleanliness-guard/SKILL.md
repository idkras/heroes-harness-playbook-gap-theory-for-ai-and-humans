---
name: main-cleanliness-guard
description: "Use when local main is dirty, diverged, overloaded with parked branches/worktrees, or when someone wants to run Stage all / publish from main. Based on the workspace git hygiene standard. Creates an isolated cleanup slice, classifies dirty layers, removes only safe local git tails, and protects review-safe handoff. Use when user says \"почисти dirty main\", \"не делай stage all\", or \"prepare clean sync from main\"."
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `<internal-module>/shared/credentials_manager.py`.

# Main Cleanliness Guard

## Hired for Jobs To Be Done

Когда `main` превращается в integration dump и следующий оператор хочет `stage all`, `sync`, `push`, или просто понять, что можно безопасно убрать, этот skill нанимается на работу `удержать main review-safe и не смешать живой slice с историческим хвостом`.

## Use this skill for

- `main...origin/main` is ahead/behind at the same time
- root workspace has a huge unstaged diff
- Codex UI shows `Diff too large to display` or `Stage all` is tempting on dirty `main`
- many local branches are already merged but still hanging around
- many detached worktrees survive after old threads
- user asks `держи main чистым`, `почисти ветки`, `why is main dirty`, `prepare clean sync`

## Do not use this skill for

- ordinary feature work that already lives in its own clean branch/worktree
- a single-file change that does not touch repo-level git hygiene

## Core rule

`main` is not the place to accumulate unrelated work or to press `Stage all` once the workspace is already mixed.

Этот skill — обязательный companion к `/sync-github`, если root `main` грязный или отстаёт/опережает `origin/main`.

If `main` is dirty or diverged:

1. do not stage from root `main`
2. do not publish from root `main`
3. create a cleanup slice from `origin/main` in a dedicated branch/worktree
4. classify the dirt before deleting anything

## Required workflow

### 1. Open the right operational layer first

- Show the quick reusable ticket card in chat.
- Resolve an existing bead or create a cleanup child bead.
- Read:
  - `.codex-memory/MEMORY.md`
  - `.codex-memory/topics/git-parallel-coordination.md`
  - `.codex-memory/runtime/git-sync-intents.md`
- Add a runtime intent row before the first git-changing step.

### 2. Measure the state of `main`

Collect and report at minimum:

- `git status --short --branch`
- `git rev-list --left-right --count origin/main...main`
- `git branch -vv`
- `git worktree list`
- `git stash list`
- `python3 <internal-module>/scripts/verify_branch_hygiene.py --strict`

If `main` is both dirty and diverged, say explicitly:

- `Stage all on root main is forbidden`
- `review-safe handoff is absent`

### 2.1. Если main diverged от origin/main — сначала rebase

Когда `git rev-list --left-right --count origin/main...main` показывает коммиты с обеих сторон:

1. **Stash:** `git stash push -u -m "cleanup-rebase-$(date +%Y%m%d%H%M)"`
2. **Rebase с отключёнными хуками:** `git -c core.hooksPath=/dev/null pull --rebase origin main`
   - **Обязательно отключать хуки:** `post_sync_bootstrap_guard.py` (через `post-checkout`/`post-rewrite`) мутирует `core-auto.mdc` и другие файлы *во время* rebase, ломая промежуточные шаги (`error: Your local changes would be overwritten by merge`)
3. **Конфликты в append-only файлах** (`ai.incidents.md`, `changelog.md`): сохранить обе стороны, отсортировать по дате
4. **Push:** `git -c core.hooksPath=/dev/null push origin main`
5. **Stash pop:** `git stash pop`; если stash pop конфликтует с файлами из rebase — `git stash drop`
6. **Проверка:** `git rev-parse HEAD` == `git rev-parse origin/main`

Полный протокол — [sync-github-checklist §0.1](.agents/skills/5-sync-github-checklist/SKILL.md).

### 2.2. Классификация грязного дерева (ПЕРЕД любым stage/cleanup)

Прежде чем удалять или стейджить, разложить dirty-файлы по источникам:

| Источник | Пример | Действие |
|---|---|---|
| Скрипт массового обновления | `*.context.md` с изменённым timestamp | Коммитить, зафиксировать побочный эффект в changelog |
| Битые симлинки из sandbox | `→ ../../../openclaw/.agents/skills/*` | Удалить (`find .agents/skills -type l ! -exec test -e {} \; -delete`) |
| Runtime-артефакты | `.beads/daemon*.log.gz`, `*.bak`, `*.log.gz` | Удалить, добавить в `.gitignore` |
| Backup-директории | `*.backup.2026*` | Удалить (если закоммичены — удалить из tracked tree тоже) |
| Легитимные новые файлы | Новые скиллы, MCP-инструменты | Коммитить |
| Embedded repos без `.gitmodules` | `git status` показывает `?? path/to/repo` | Не добавлять через `git add -A`; оформить как субмодуль или `.gitignore` |
| Субмодули с modified content | `m <internal-module>/n8n-mcp` | Штатное; коммитить внутри → пушить → обновить gitlink |

### 3. Create an isolated cleanup slice

Use a fresh worktree from `origin/main`, for example:

```bash
git worktree add -b ik-codex/<bead>-main-cleanup /path/to/clean-worktree origin/main
```

All cleanup commands must run from that isolated slice, not from the dirty root `main`.

### 4. Classify dirty layers before cleanup

Split the mess into explicit buckets:

- branch/history tails
- detached worktrees
- tracked code/docs/standards edits
- tracked client exports and local mirrors
- generated outputs
- dirty submodules
- stash tails

Отдельно для Rick.ai client data:

- `bronze|silver|gold` = local/generated layers, не publish payload
- `google-drive-exchange/` = local-only handoff staging, не source-of-truth
- numeric folders `<internal-folder>/clients/all-clients/<id>/` = подозрительные bug mirrors, если там только autogenerated context

Do not call everything just `workspace noise`.

### 5. Safe deletion order

Delete in this order only:

1. local branches already merged into `origin/main` and not occupied by a worktree
2. detached worktrees whose HEAD is already reachable from `origin/main` and whose tracked state is clean
3. detached worktrees with only trivial untracked outputs, but only after naming those files explicitly

### 6. Unsafe tails that require explicit review

Do not auto-delete:

- branches merged only into local dirty `main`
- worktrees whose HEAD is not reachable from `origin/main`
- worktrees with tracked dirty state
- dirty submodule worktrees
- branches with active PRs unless their lifecycle is explicitly complete

These must be reported as `unsafe / needs review`, not silently removed.

### 7. Stage-all policy

If the root `main` still contains mixed unrelated changes:

- do not run `git add -A`
- do not ask the user to review the whole diff
- do not claim the staging problem is solved just because the cleanup branch is clean

Instead say:

- the cleanup branch is clean
- the root `main` still remains a dirty evidence layer
- `Stage all` on root `main` is still not the correct action

### 8. Handoff contract

At the end, report:

- which local branches were deleted
- which worktrees were removed
- which worktrees remain and why
- which branches remain and why
- which stale remote integration branches still remain and why they were not cleaned in this pass
- whether [`5-sync-github-checklist/workflow.yaml`](../5-sync-github-checklist/workflow.yaml)
  `definition_of_done` and `cleanup_verification` are PASS or still blocked
- clean evidence: `worktree_disk_guard.py --prune` summary with `total_worktrees`,
  `prune_merged_clean`, `skip_dirty`, `skip_unmerged`, `skip_gitignored_data`, and free GB
- whether runtime git intent should stay open or be downgraded to a remaining-risk note

If the same pattern repeats, log it to `ai.legacy.md`.
If cleanup reveals a false previous claim or broken publish path, log it to `ai.incidents.md`.

## Minimum output in chat

- `Safe to delete now`
- `Deleted now`
- `Still unsafe`
- `Why Stage all is still wrong or now safe`
- `Next review-safe step`

## Transparency mode for review

If the user asks `что это за папки`, `покажи что внутри`, `дай скриншоты`, or says the cleanup is not transparent enough:

1. name every created folder with its absolute path
2. say whether the folder was created in the current pass, existed before, or is an archive container
3. map each worktree folder to:
   - branch name
   - HEAD commit
   - creation timestamp if available
4. show the top-level entity inventory for each folder, not just a prose summary
5. generate review artifacts the user can inspect by eye:
   - a text listing saved to disk
   - a rendered screenshot or image of that listing when practical
6. distinguish clearly between:
   - git worktrees
   - archive folders
   - ordinary repo folders
7. if a new skill or mirror folder was added, show the exact files created inside it

Do not answer with summary-only prose when the user explicitly asks for folder/entity review.

## Forbidden

- Do not run cleanup directly from dirty root `main`.
- Do not delete local-only merged branches as if they were already published.
- Do not remove detached worktrees without checking both ancestry and dirtiness.
- Do not collapse submodule dirt into generic root dirt.
- Do not say `main is clean` while root `main` still carries mixed unrelated changes.

## Related

- `git-parallel-coordination`
- `rca-incidents`
- `change-task-and-project-state-via-beads`
- `task-completion-persistence`


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/` → duckdb). Узел «свернул не туда»: `scripts/reasoning_log/graph.py --find-divergence`. Ручная markdown-таблица в чат — только если owner явно спросил «почему ты так решил». Полный протокол: `agent-reasoning-log/SKILL.md` (v2, RCA 2026-05-17).

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick (включая TaskMaster и связанные стандарты Heroes Rickai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.


---

## Skill contract (Standard 4.8 §B)

### Hired for JTBD

Когда локальный main грязный/diverged/перегружен parked-ветками, ты как owner хочешь безопасный cleanup slice, чтобы не сделать destructive stage-all и не потерять чужую работу.

### Workflow

1. detect dirty/diverged/overloaded -> 2. classify dirty layers -> 3. isolate cleanup slice -> 4. remove only safe local git tails -> 5. protect review-safe handoff.

### Input checklist

- [ ] git status, git stash list, git worktree list, dirty-entry classification table

### Output checklist

- [ ] main clean ИЛИ classified, 0 unsafe destructive op, review-safe handoff state

### Outcome checklist (owner benefit)

- [ ] owner может делать sync/publish из чистого main без потери параллельной работы и без stage all catastrophe

### Owner value

owner value: ноль потерянной работы команды при чистке main — только safe local tails removed

### Self-falsification gate

После исполнения скилл обязан прогнать гипотезу «этот скилл закрыл свой JTBD» через [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md): gap table Ожидание | Факт | Δ, verdict confirmed | partial | falsified. При partial/falsified — новая рабочая гипотеза, не закрывать как done.

### Reasoning Log Protocol

Каждое исполнение ведёт reasoning log в чате (решения + evidence + gap + blocking instruction) и строку в `<internal-folder>/ai.incidents.md` §Append-only trace. Hard fail: без reasoning log скилл не исполнен. Канон — `agent-reasoning-log` в AGENTS.md.

### Связанные скилы / Related skills

- [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md) — self-falsification gate
- [`5-sync-github-checklist`](../5-sync-github-checklist/SKILL.md) — общий sync ритуал + io-checklist макрос §4.9
- `agent-reasoning-log` — обязательный reasoning log протокол (AGENTS.md)
