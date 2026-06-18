---
name: sync-github-checklist
description: "Use when preparing to sync repository with GitHub. Merges branches and validates Windows-compatible filenames. Based on core-auto.mdc sync-github command. Use when user says \"prepare sync\", \"check filenames\", \"готовлю репо\", \"sync github\"."
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скилл `0-keychain-audit`. Любой вызов external API → сначала `cm.get_credential('<key>')` из `<internal-module>/shared/credentials_manager.py`.

# Sync GitHub Checklist Skill

## Overview

Перед синхронизацией репозитория с GitHub (команда `/sync-github`) нужно выполнить проверки, чтобы у Windows-пользователей клон выгружался без ошибок и статус субмодулей был явно зафиксирован в отчёте.

**Based on:** `.cursor/commands/sync-github.md`, скрипт `<internal-module>/scripts/check_windows_safe_filenames.py`

## When to Use

- Перед выполнением команды `/sync-github`
- Когда задачи ставятся с телефона и background-агенты создали ветки (merge в main)
- Когда готовите репозиторий к выгрузке для команды (в т.ч. проверка имён файлов/папок)
- Когда нужно явно отчитаться по субмодулям после синхронизации
- Когда пользователь говорит `stage all`, `git add -A`, `застейджи всё`, `сделай stage-all`

## Inputs

- **Repo root**: (Optional) Корень репозитория; по умолчанию — текущий workspace.

## Hard gates before publish

- **Workflow SSOT:** перед любым заявлением `sync done` открыть и применить
  [`workflow.yaml`](workflow.yaml). Он содержит машиночитаемые `definition_of_done`,
  `acceptance_criteria`, `cleanup_verification` и `guardian_checks`. Если YAML и текст
  skill расходятся — YAML считается операционным контрактом, а skill надо обновить в
  той же сессии.
- Если root `main` грязный, publish из него запрещён. Сначала перейти в clean branch/worktree и только там собирать publish scope.
- Перед `gh pr create` обязательно выполнить `5-stale-base-rebase-guard`: `bash .agents/skills/5-stale-base-rebase-guard/scripts/check_pr_stale_base.sh`. PR создаётся только после fresh-base verdict и только с явным JTBD title: `gh pr create --head <branch> --base main --title="Когда ..., хотим ..."`. `--fill` не является источником project name.
- Publish запрещён, если branch/worktree не связаны с bead: branch должен быть `pr-rick-<jtbd-slug>-<bead-id>`, а worktree folder должен совпадать с branch.
- Skill canon должен быть целым: `.claude/skills` и `.codex/skills` обязаны быть symlink на `.agents/skills`, иначе команда получает разные skill trees.
- Перед publish и после `pull/merge` использовать единый contract guard:
  - `python3 <internal-module>/scripts/verify_sync_github_contract.py --strict --tracked-only`
  - `python3 <internal-module>/scripts/verify_branch_hygiene.py --strict`
  - `python3 <internal-module>/scripts/verify_workspace_consistency.py --strict` — сверка cross-references между артефактами (субагенты frontmatter ↔ README ↔ Registry, guardian формула версия, симлинки)
  - локально перед publish: `make sync-github-guard`
  - после `git pull --rebase origin main`: `make team-activate` (или auto `post-rewrite` + затем `make team-sync-guard`)
- Для Windows prerequisite обязателен до clone/pull/publish:
  - `git config --global core.longpaths true`
  - короткий workspace root вида `C:\ws\heroes-rickai-workspace`
- Generated client exports не входят в publish scope:
  - `<internal-folder>/clients/all-clients/**/bronze|silver|<layer>/` = local-only derived layers
  - `<internal-folder>/clients/all-clients/<id>/` = bug-generated numeric mirrors, если они context-only и резолвятся в slug
  - human handoff folder = `<internal-folder>/clients/all-clients/{client_alias}/google-drive-exchange/`, тоже local-only и не для GitHub
- Branch/worktree backlog не должен быть скрытым:
  - stale remote integration branches (`ik-codex/*`, `codex/*`, `cursor/*`, `sync/*`) подлежат audit перед publish
  - detached worktrees и merged local branches перечисляются отдельно как cleanup candidates / unsafe tails
  - сам `/sync-github` не должен молча удалять или auto-merge ветки; удаление/merge — только через отдельный cleanup slice или explicit review. **«Explicit review» (RCA 2026-06-03) = агент САМ изучает все PR/ветки/CI, выписывает детали, принимает решение о порядке merge, разруливает конфликты, и показывает owner ГОТОВЫЙ результат на post-hoc review — НЕ откладывает решение порядка / диагностику CI на owner развилкой.** Owner ревьюит результат, а не пред-решает порядок (см. §Autonomy contract для sync → «Решение о порядке merge / диагностике CI = обязанность агента»).
  - GitHub почти всегда показывает больше веток, чем local branch picker, потому что считает remote `origin/*` refs; merge-решения принимаются не по raw count, а по buckets `merged_into_main=true` vs `ahead_of_main>0`
  - `ahead_of_main>0` ветка обязана получить явный verdict `compare/PR candidate` или `оставить вне текущего sync pass`; age/prefix never equals merge approval

## Team language: clone, update, publish

Use one of these verbs explicitly in docs and team rollout:

- `забрать workspace из GitHub` = `git clone ...heroes-rickai-workspace.git`
- `забрать workspace из GitHub` завершается только после `make team-activate`
- для Windows: сначала `git config --global core.longpaths true`, затем clone в короткий root
- `полный синк с main и получение последней версии` = `make team-main-sync`
- `обновить локальную копию` = `make team-main-sync`
- `обновить локальную копию` завершается только после успешного `make team-main-sync`
- `make team-main-sync` обязан подтянуть обязательные MCP, Model Context Protocol submodules через `make team-activate`, а не только сделать `pull`
- `make team-main-sync` обязан ставить Node workspaces через direct `npm install --workspaces` c `NODE_GYP_FORCE_PYTHON` + `npm_config_python` + `PYTHON`, чтобы native npm modules не падали на fresh clone из-за global Python 3.13 / missing `distutils`
- `<internal-module>/n8n-mcp` в этом route не входит в root workspaces и не входит в baseline teammate bootstrap; если конкретной задаче действительно нужен local `n8n-mcp`, это explicit opt-in route `WITH_OPTIONAL_N8N_MCP=1 make workspace-node-install`
- `n8n-mcp` не должен блокировать сам командный route `make team-main-sync`: optional degraded MCP остаётся warning/report surface, а не причиной лишить всю команду latest `main`
- если в fresh clone есть только `.beads/issues.jsonl`, activation contract обязан использовать `bd --no-db` и не считать отсутствие локальной `.beads/*.db` поломкой sync
- `синхронизировать / выгрузить изменения в GitHub` = run `/sync-github` or ask the agent to publish the current branch after checks
- stale remote branches должны классифицироваться до любых merge-решений: `merged_into_main=true` = cleanup/archive candidate, `ahead_of_main>0` = explicit review candidate; агент не должен auto-merge ветки только потому, что они старые
- lifecycle после классификации:
  - cleanup/archive candidate = уже в `main`, можно удалить/архивировать в отдельном branch-cleanup pass;
  - explicit review candidate = не дозаливать автоматически, пока нет compare against `main` и owner review;
  - raw branch count mismatch between GitHub and local UI is evidence of different surfaces, not evidence that every remote branch must be merged
- GitHub branch count и local UI branch count не обязаны совпадать: remote refs могут жить на GitHub без локального checkout branch; canonical verdict даёт `verify_branch_hygiene.py`, а не веточный dropdown
- тяжёлый RickAI pre-push gate считается scope-mismatched, если diff не затрагивает прямой RickAI export/runtime bundle (`tools/`, `workflows/`, `request_contracts.py`, `src/data_export.py`, `src/clickhouse_internal.py`, gate scripts и связанные contract/unit tests). Для infra/docs/sync-contract правок documented bypass допустим только после RCA, Root Cause Analysis — анализ корневых причин.
- если rebased integration branch force-push поднимает heavy gate, а push того же `HEAD` в `main` его уже не поднимает, это branch-range RCA-layer; auxiliary branch publish не должен отменять честный verdict `команда уже может получить latest main`

Human-facing request examples without naming the internal command:

- `Синхронизируй текущую ветку с GitHub и покажи финальный статус.`
- `Подтяни main, проверь Windows-safe filenames и выгрузи изменения обратно в GitHub.`
- `Подготовь publish scope и обнови remote ветку без пропуска changelog и nested repos.`

## Instructions

### 0.0.−1. Two invariants gate — ОБЯЗАТЕЛЬНО рамка любого sync (RCA 2026-05-14 + 2026-05-16)

Любой sync flow выполняется внутри **двух канонических инвариантов AGENTS.md**. Это не шаги — это рамка, активная на каждом шаге ниже.

| Инвариант | Канон | Что значит для sync | Hard trigger |
|---|---|---|---|
| **Always-green main** | AGENTS.md §`Always-green main invariant (RCA 2026-05-14)` | Если в ходе sync обнаружен broken main (ImportError на entrypoint, CI red на нашей ветке, validator упал, orphan commit, stale symlink, missing canonical file, MCP tools не surface) — **STOP sync, fix main в той же сессии, incremental commit починки ДО продолжения sync.** Sync не «обходит» broken main. Переопределяет autonomous/ralph continuation default. | broken main detected during sync |
| **Nothing-lost & team-can-use** | AGENTS.md §`Nothing-lost & team-can-use-everything invariant (RCA 2026-05-16)` | Работа «не потеряна» ТОЛЬКО когда достижима из `origin/main` через `git pull`. Каждый branch/stash/worktree/orphan → (a) in-main / (b) superseded+reason / (c) owner-decision+эскалация (см. §0.0.6 v4). Stash/tag/wip ≠ delivery. | финал sync с unclassified ветками/stash |

**Принцип (universal, не case-detail):** обнаружил проблему в ходе sync (даже смежную) → обязан устранить корневую причину в той же сессии, не «отдельной сессией», не «обошёл». Always-working-prod. Зависимости разруливаются, не срезаются. Это следствие обоих инвариантов и §Same-session ownership contract.

**Hard fail:** sync завершён при broken main без fix → `category: prod-broken-bypassed`. Sync завершён с «ничего не потеряно» при unclassified ветке/stash → `category: nothing-lost-false-claim`.

### 0.0.−1a. Owner-flagged branch = FIRST PRIORITY (RCA 2026-06-02)

**Корневая причина:** owner steering 2026-06-02 — «если я прошу, это первый приоритет… мне нужен outcome/output и чтобы команда воспользовалась (не срезая углы, правильный мердж), а после рефакторинг и системное решение. Ты теряешь моё время». Агент ушёл в системную консолидацию/cleanup ДО того как реально доставил флагнутую владельцем ветку → owner не получил outcome, время потеряно.

**Правило (переопределяет порядок любого sync-flow):** если owner ЯВНО указал на ветку/PR («доведи X», «замержи X», «X не дозалита») — она получает **АБСОЛЮТНЫЙ первый приоритет**:

1. **Outcome-first:** довести именно её до origin/main **правильным мерджем** (реальный контент в main, достижим `git pull`), а НЕ close-as-superseded/archive в обход. Если ветка stale-base → ADDED-only extract + 3-way для MODIFIED, но контент обязан оказаться в main.
2. **Verify outcome:** `git ls-tree -r origin/main | grep <ключевой-файл-ветки>` + сослаться на merge-commit SHA. Заявлять «готово» только с этим доказательством (§State-claim verification).
3. **Только ПОСЛЕ** доставки флагнутой ветки → systemic / refactor / branch-cleanup / consolidation остальных.
4. **Не лить в чужой репо:** работа идёт в проектный репо (`git -C <repo>` / `gh --repo <owner/repo>`), НЕ в репо, к которому случайно привязана сессия. Verify `git remote get-url origin` целевого репо до push.

**Hard fail:** агент начал systemic/cleanup/refactor пока флагнутая owner ветка НЕ в origin/main с verify → `category: owner-priority-inverted`. Флагнутая ветка closed-as-superseded без реального merge её уникального контента → `category: flagged-branch-corner-cut`.

### 0.0.−1b. Disk-space & worktree guard — ОБЯЗАТЕЛЬНО в начале и конце sync (RCA 2026-06-02)

**Корневая причина:** owner 2026-06-02 — «worktree стабильно съедают 40-140ГБ на диске». Каждый `git worktree add` = полный checkout (~40k файлов). 15-25 worktree молча съедают десятки ГБ → `no space left on device` ломает ВСЕ git/tool операции посреди задачи (наблюдалось: 84GB в worktree-чекаутах, диск заполнен).

**Правило:** в начале sync-flow И перед завершением прогнать:

```bash
python3 scripts/worktree_disk_guard.py          # report: count / GB / free
python3 scripts/worktree_disk_guard.py --strict # exit 2 если > порога (count>8, size>40GB, free<20GB)
```

Если over-threshold → **prune disposable checkouts** (zero-loss: ветки на origin + archive-tags, checkout = кэш):

```bash
python3 scripts/worktree_disk_guard.py --prune  # удаляет worktree merged/archived веток
```

**Инвариант worktree-lifecycle:** worktree создаётся под одну JTBD-задачу и **удаляется сразу после merge/archive** ветки (не копится). Финал sync: ≤8 worktree, ≤40GB, ≥20GB free. Branch-cleanup и worktree-cleanup — один pass (удалил origin-ветку → удали и её локальный worktree-checkout).

**Hard fail:** sync завершён с >8 worktree ИЛИ <20GB free без prune-попытки → `category: worktree-disk-sprawl-unresolved`. Создан worktree, merged ветку, но checkout не удалён → растёт sprawl.

### 0.0.−1c. Anti-phantom-deletion + honest verification (RCA 2026-06-02)

**Корневая причина (катастрофа #290):** коммит собран из `--no-checkout` worktree (неполный индекс) → дерево 12 файлов, удалило 41 107 из main; смержен `gh pr merge --admin` (обошёл CI deletion-guard). Два стэка: partial-tree commit + --admin bypass. main обнулён 41119→12. Поймано только после pushback owner — я проверял по ЛОКАЛЬНЫМ refs (которые врут: локальный origin/main = что я напушил, не GitHub-правда).

**Жёсткие правила (не нарушать):**
1. **НИКОГДА не коммить из `--no-checkout`/partial-index worktree.** Перед commit: `git ls-files | wc -l` ≈ полному дереву.
2. **НИКОГДА `gh pr merge --admin` в main** — это обходит deletion/tree CI-гарды (именно так прошёл #290). Обычный merge, уважающий CI.
3. **ПЕРЕД любым merge/push в main:** `python3 scripts/verify_tree_completeness.py <ref>` — блок если дерево <90% main (phantom-deletion класс). Гард сам не дал бы #290.
4. **ПОСЛЕ merge — verify через GitHub API, НЕ локальные refs:** `gh api repos/<o>/<r>/git/trees/main?recursive=true --jq '.tree|length'` + `gh api .../contents/AGENTS.md?ref=main`. Заявлять «готово» ТОЛЬКО с GitHub-API-доказательством. Локальный `git log origin/main` ≠ GitHub-правда.

**Hard fail:** merge в main без `verify_tree_completeness` → `category: phantom-deletion-guard-skipped`. «Готово» заявлено по локальным refs без GitHub-API verify → `category: claim-from-local-not-authoritative`. `--admin` merge в main → `category: ci-guard-bypassed-on-main`.

### 0.0.−1d. Definition of Done — «команда получила полный результат в origin/main» (verify via GitHub API)

Заявлять «готово» ТОЛЬКО когда ВСЕ пункты ✅ **с GitHub-API-доказательством** (не `git log origin/main` — локальный ref показывает то, что ты напушил, не GitHub-правду; RCA #290):

- [ ] нет открытых PR — `gh api repos/<o>/<r>/pulls?state=open --jq length` == 0
- [ ] нет открытых веток на origin кроме main + infra — `git ls-remote --heads origin`
- [ ] изменения достижимы из GitHub main (НЕ только локальные refs) — `gh api repos/<o>/<r>/contents/<key-file>?ref=main`
- [ ] main цел: `gh api .../git/trees/main?recursive=true --jq .truncated` (true → 40k+) И AGENTS.md present И `verify_tree_completeness.py` ok
- [ ] каждая ветка классифицирована (a) in-main / (b) superseded+archive-tag+delete / (c) owner-decision+archive+escalate
- [ ] archive-tags для (b)/(c) на origin — `git ls-remote --tags origin | grep archive/`
- [ ] локальные ветки-призраки выпилены (`git branch -D`), пикер UI = main+active+infra
- [ ] disk: ≤8 worktree, ≥20GB free — `python3 scripts/worktree_disk_guard.py`
- [ ] merge сделан server-side gh (НЕ worktree-per-merge), БЕЗ `--admin` в main
- [ ] нет ЛОКАЛЬНЫХ веток с несмерженным уникальным (НЕ только origin — owner видит локальные в пикере): `git branch` + `git diff --diff-filter=A origin/main..<b>` каждый ADDED-файл в origin/main
- [ ] сессия/working-dir на `main` (НЕ припаркована на stale/consolidate-ветке — RCA #290 был на parked --no-checkout ветке)
- [ ] owner-flagged ветка ПРОПЕРЛИ смержена (контент в origin/main, verify API), НЕ archived-as-superseded; удалена local И origin
- [ ] landing-process локальные ветки (`recover-*`, `*-land`, consolidate-tmp) удалены ПОСЛЕ merge (иначе копятся в пикере = иллюзия «не done»)
- [ ] worktree merged/archived веток выпилены: `python3 scripts/worktree_disk_guard.py --prune`
- [ ] UI branch-picker (owner-view) = ТОЛЬКО main + active-worktree-task + infra

**Hard fail:** «готово» при любом ❌ или без GitHub-API-доказательства → `category: dod-claimed-incomplete`.

### 0.0.−1e. Lean merge path (anti-waste, RCA 2026-06-02 — токены/действия/диск)

Default merge = `gh pr merge <n> --squash --delete-branch` — **server-side: 0 worktree, 0 диска, не гоняет локальные хуки** (именно локальные worktree+хуки были источником waste и катастрофы #290). НЕ создавать worktree/commit-tree на КАЖДЫЙ merge. Worktree — только для РАЗРАБОТКИ одной JTBD-задачи, удаляется после. Stale/conflicting ветки: ОДИН проход — triage → gh-merge mergeable → land unique-union одним commit-tree (с `verify_tree_completeness`) → archive+delete остальные через `gh api -X DELETE`.

**Hard fail:** worktree создан ради merge (а не разработки) → `category: worktree-per-merge-waste`.

### 0.0. Sit-down dirty-tree triage — ОБЯЗАТЕЛЬНО ПЕРЕД любой git op (RCA 2026-05-13)

**Корневая причина:** RCA 2026-05-13 — owner steering «ты не должен блокироваться и недоделывать сам всё». В предыдущей sync-сессии я (a) увидел 821 dirty entries, (b) попытался `git pull --rebase` сразу, (c) нарвался на «cannot rebase with locally recorded submodule modifications», (d) начал ad-hoc reset submodule pointers без сверки со SSOT, (e) выписал owner «Решить судьбу 821 dirty entries… усилие 50» вместо того чтобы **сесть и разобраться сам**. Skill дал §0.1 «классификация при коммите», но **не дал** обязательного pre-flight «сядь и разберись с деревом данных ДО любой git op».

**Правило: ВСЕГДА перед `git pull` / `git rebase` / `git checkout -b` / `git stash` / `git push` / `git add` / `git commit` агент обязан сесть и разобраться с деревом данных.** Это не optional, не «если успею», не «после первой попытки rebase». Это **первая команда** в любом sync-flow.

**Anti-block contract (под полученным go owner на sync):**

- **Запрещено:** возвращать owner «у тебя 800+ dirty entries, классифицируй и реши что коммитить» — это decision-handoff (см. AGENTS.md §Mandatory delivery format §10 ЗАПРЕЩЁННЫЕ next actions).
- **Запрещено:** делать `git add -A` / `git stash` blind без классификации.
- **Запрещено:** делать `git checkout HEAD -- <submodule>` ad-hoc без сверки с YAML SSOT (см. §2.0).
- **Обязательно:** прогнать inventory → classified report → per-layer decision → action.

**Алгоритм 7 шагов:**

0. **Sync state diagnostic — ДО inventory** (RCA 2026-05-13 — agent путал 0/0 vs branch с 26/2 vs main):

   ```bash
   git rev-list --left-right --count HEAD...origin/$(git symbolic-ref --short HEAD)  # vs origin branch
   git rev-list --left-right --count HEAD...origin/main                              # vs origin/main
   ```

   Классификация состояния:

   | HEAD vs origin/branch | HEAD vs origin/main | Состояние | Действие |
   |---|---|---|---|
   | `0 0` | `0 0` | clean | nothing to sync |
   | `0 0` | `N 0` (N>0) | ahead of main, branch in sync | push branch / open PR (если PR нет) |
   | `0 0` | `N M` (M>0) | ahead AND behind main | **rebase on main, then push branch** (текущий сценарий 2026-05-13) |
   | `0 N` (N>0) | — | behind own branch | `git pull --ff-only origin <branch>` — teammate работал параллельно |
   | `N 0` (N>0) | — | ahead own branch | push branch |
   | `N M` (N>0, M>0) | — | diverged own branch | conflict — read teammate intent first, then rebase OR merge |

   Запишите состояние в `.agents/memory/runtime/git-sync-intents.md` row **до** любого write op.

1. **Inventory:** `python3 scripts/git_workspace_inventory.py 2>&1 | tail -60` — config-driven classifier dirty entries по 12 категориям (artefact_bloat / rag_etl_staging / backup_files / submodule_pointers / legitimate_renames / client_data / agent_workspace_evolution / standards_evolution / project_bloat / config_drift / tooling / uncategorized). Output: text summary в stdout + детальный Markdown report в `<internal-folder>/git-workspace-inventory-{date}.md`.

2. **Read report:** открыть `<internal-folder>/git-workspace-inventory-{date}.md` и проверить распределение по категориям. Цель — понять «что это вообще такое» **до** действия.

3. **Per-layer decision** (использовать таблицу §0.1 как reference + AGENTS.md §Same-session ownership):

   | Категория из inventory | Default действие | Когда отклониться |
   |---|---|---|
   | `artefact_bloat` (Playwright/screenshots/temp) | `git rm --cached` + `.gitignore` | если owner явно сохраняет evidence для PR |
   | `rag_etl_staging` (n8n JSON, schema snapshots) | commit как отдельный слой `data: refresh {source}` | если staging > 50MB — LFS |
   | `backup_files` (`*.backup.YYYY*`) | удалить через `rm` | никогда не коммитить |
   | `submodule_pointers` | см. §2.0 per-submodule policy | reset to HEAD для `manual-bump` без go |
   | `legitimate_renames` (mass rename папки) | commit отдельным слоем `chore: rename {old} → {new}` | если ≥100 files — preview через `git status -s \| head -20` ДО stage |
   | `client_data` (`<internal-folder>/clients/...`) | проверить <layer>/<layer>/gold per Standard 4.6 | <layer>/<layer>/gold = local-only, НЕ публиковать |
   | `agent_workspace_evolution` (`.agents/skills/*`, `.agents/agents/*`) | commit как `feat(agents)/feat(skills): ...` | если есть untracked symlinks — fix через `0-align-skill-name-and-trigger-to-jtbd` |
   | `standards_evolution` (`<standard-ref>) | commit как `docs(standards): ...` | если ≥3 файлов — отдельный bead |
   | `project_bloat` (Projects/*, экспорты) | проверить `.gitignore` | новые экспорты обычно НЕ для git |
   | `config_drift` (`.cursor/mcp.json`, `Makefile`) | commit `chore(config): ...` | если absolute paths — fix перед commit |
   | `tooling` (scripts/, .githooks/) | commit `chore(tooling): ...` | preview diff обязателен |
   | `uncategorized` | прочитать руками 3-5 примеров, классифицировать или extend config | если >50 uncategorized — stop и попросить owner expand config |

4. **Sequence layers as commits:** записать план «слой → файлы → commit message» в `.agents/memory/runtime/git-sync-intents.md`. Несколько self-contained коммитов лучше одного monolithic `git add -A`. Каждый слой = один логический change.

5. **Execute layers sequentially:** для каждого слоя — `git add <explicit-paths-only>` (НИКОГДА `-A`/`.`), `git commit -m "<scope>: <intent>"`, проверить `git status --porcelain | wc -l` уменьшается ожидаемым образом. **Не blind add**: всегда explicit paths.

6. **Verify before rebase:** после прохождения всех слоёв `git status --porcelain | wc -l` должен быть **< WARN_THRESHOLD (50)** ИЛИ оставшиеся entries — это явно known-residual (например `*.gitignore`-violating client bronze, которые не должны коммититься). Только после verify → `git pull --rebase` / `git push`.

7. **Post-sync bootstrap verify (RCA 2026-05-13):** после успешного `git pull --rebase` или merge **обязательно** выполнить:

   ```bash
   make team-activate           # подтягивает baseline-mcp submodules (heroes_telegram_mcp, n8n-mcp) per §2.0
   make team-sync-guard         # запускает verify_sync_github_contract.py --strict --tracked-only + verify_branch_hygiene.py
   ```

   Hook `.githooks/post-rewrite` запускает `post_sync_bootstrap_guard.py` автоматом после rebase, но guard НЕ заменяет verify — он только проверяет diff на bootstrap-relevant changes. Полноценная activate-чейн обязательна когда: (a) изменились `pyproject.toml` / `requirements*.txt` / `package*.json` / `.cursor/mcp.json.example` / `Makefile`, (b) bumped baseline-mcp submodule pointer, (c) sync затронул `.agents/skills/` / `.agents/agents/` (canon symlinks).

   **Hard fail:** rebase прошёл, agent сразу пушит без `make team-activate` если diff содержит bootstrap-relevant пути → `category: post-sync-bootstrap-skipped`.

**Override для honest carry-over:** если dirty tree содержит **намеренный** WIP (intentional in-flight cleanup сессия, planned migration sweep, owner explicit «оставь этот хвост»), agent **обязан**:
- export `DIRTY_TREE_ACK="<reason>"` env var
- зафиксировать reason в `.agents/memory/runtime/git-sync-intents.md`
- двигаться дальше с rebase/push под autostash (RCA 2026-05-13 sub-case: «819 entries состоят из 757 D от mass rename `[<client>]` папки + 26 M from in-flight skill edits + 38 ?? from new client projects — owner cleanup сессия параллельная, autostash через rebase preserve»)

**Hard fail (RCA-инцидент в `<internal-folder>/ai.incidents.md`):**

- Agent запустил `git pull` / `git rebase` / `git push` / `git add -A` без предварительного inventory → `category: dirty-tree-triage-skipped`.
- Agent вернул owner «реши что коммитить из 800+ файлов» как Owner effort digest action → `category: decision-handoff-instead-of-triage` (см. AGENTS.md §Mandatory delivery format §10 ЗАПРЕЩЁННЫЕ next actions).
- Agent сделал ad-hoc decision (reset / discard / commit blind) на основе intuition без inventory output → `category: ad-hoc-tree-decision-without-triage`.
- Agent пропустил Step 0 sync state diagnostic, перепутал `0/0 vs origin/branch` с `N M vs origin/main` → `category: sync-state-diagnostic-skipped`.
- Agent пропустил Step 7 post-sync bootstrap, запушил после rebase без `make team-activate` при diff с bootstrap-relevant путями → `category: post-sync-bootstrap-skipped`.

### 0.0.1. Confidence calibration — 2× self-check перед вопросом owner (RCA 2026-05-13)

**Корневая причина:** Owner steering 2026-05-13: «после первого анализа, ты обязан присылать таблицу с планом действий, где мои усилия 0, мои задачи 0, ты сам все понимаешь и задаешь мне вопросы только если уверенность падает ниже 0.9 но после того, как 2 раза сам все изучишь». Раньше agent (я в этой сессии turn 1) сразу выписывал owner action 50-усилий, не пройдя ни одного self-check.

**Контракт перед любым `AskUserQuestion` / «жду go» / «pending owner action» / «Decide between A or B»:**

1. **1-й self-check:** прогнать минимум один из: `Grep` по релевантной teme, `Read` SSOT-файла (`AGENTS.md` секция / skill `.md` / standard `.md` / YAML registry), inventory tool (`scripts/git_workspace_inventory.py`), API call (Rick MCP, gh, git status). Записать findings в reasoning log.
2. **Confidence assessment:** оценить уверенность что у меня достаточно информации сделать самому, шкала 0.0-1.0. Если ≥0.9 → действуй без вопроса. Если <0.9 → шаг 3.
3. **2-й self-check** (обязательный, если 1-й дал <0.9): прогнать **другой** источник — если 1-й был grep по skills, 2-й = read AGENTS.md или Standard; если 1-й был API call, 2-й = read implementation; если 1-й был inventory, 2-й = read recent commits / RCAs. Записать findings.
4. **Final confidence:** если после 2-х self-check confidence ≥0.9 → действуй. Если <0.9 → допустимо `AskUserQuestion` с конкретным вопросом + контекст что я уже проверил.

**Запрещённые формулировки** (нарушают anti-block contract per AGENTS.md §10):

- «Сделать сейчас или потом?» при наличии blanket-go.
- «Decide between A or B» когда SSOT/registry/skill algorithm даёт однозначный ответ.
- «Review my X» / «Verify my Y» — transparency-артефакт не должен быть owner action.
- «Что предпочитаешь?» когда у меня есть 0 self-check — это lazy handoff.

**Допустимые формулировки** (когда confidence <0.9 после 2× проверки):

- «Я проверил X (file:line) и Y (skill §N). Расхождение: SSOT говорит A, RCA говорит B. Какой канон?»
- «Документации нет на C, владельца этого кода не нашёл в git blame последних 6 месяцев. Что должно происходить в этом сценарии?»
- «D — irreversible side-effect (push в external repo / drop production table / отправка клиенту). Подтверди.»

**Hard fail:**

- AskUserQuestion возвращён без логов 2× self-check в reasoning trace → `category: ask-without-self-check`.
- Owner action в Owner effort digest с усилием >0 при confidence ≥0.9 → `category: handoff-with-high-confidence`.
- Сначала action, потом вопрос («сделал X, проверь правильно ли») → `category: ask-after-fact-instead-of-before`.

### 0.0.4. Universal Project-State Router (v3, RCA 2026-05-14)

**Корневая причина (RCA 2026-05-14):** Owner blanket-go «делай сам, не блокируйся, через @auto» сессия — agent (я в Turn 5) застрял на ad-hoc submodule wrestling 7 tool calls подряд, потеряв стратегический фокус. Skill v2 описывал «как делать sync» но **не описывал** *в каком из 11 состояний проекта* мы сейчас и *какой autonomous routing* применить. Каждое состояние требует разной стратегии — без классификатора agent блуждает.

**Правило:** перед выполнением sync-flow агент обязан **классифицировать состояние** через `git rev-list --left-right --count origin/<branch>...HEAD` + `git status --porcelain | wc -l` + `gh pr view <num>` + `gh pr list --base main` и выбрать стратегию из таблицы. Универсально — работает для любого репозитория workspace (этот repo, submodules, client repos, external git hosts).

#### Таблица 11 состояний и стратегий

| State | Условие | Default action | Subagent chain | Risk |
|---|---|---|---|---|
| **A** | clean tree, ahead=0, behind=0 | nothing to do, exit | — | none |
| **B** | clean tree, ahead>0, behind=0 | `git push` (own repo) или PR (external) | git-sync-curator | low |
| **C** | clean tree, ahead=0, behind>0 | `git pull --ff-only` | git-sync-curator | low |
| **D** | clean tree, ahead>0, behind>0 | rebase + push (own) или rebase + PR (external) | git-sync-curator | medium |
| **E** | dirty <50 + any ahead/behind | per-layer incremental commits + state B/C/D | git-sync-curator | low |
| **F** | dirty 50-200 + any | sit-down triage (§0.0) → batched commits per category → state D | git-sync-curator + cleanup-guardian | medium |
| **G** | dirty ≥200 + any | mandatory inventory (`scripts/git_workspace_inventory.py`) + DIRTY_TREE_ACK + per-category cleanup plan | git-sync-curator + cleanup-guardian + manager-lead-orchestrator | high |
| **H** | branch merged via PR, but local ahead | stale branch — rescue local-only via stash → switch to main → fast-forward → delete merged branch | git-sync-curator | medium |
| **I** | submodule divergence (parent gitlink ≠ submodule HEAD) | apply per-submodule policy из `submodules-and-projects-registry.yaml`: own → bump+push, vendor → revert, active-project → consult registry | git-sync-curator + <teammate>-git-sync (если <teammate> submodule) | high |
| **J** | open PR with red CI checks | ralph-loop: fix-push-wait-assess-iterate via `1-ralph-loop-autonomy` outer frame | git-sync-curator + <teammate>-code-review + ralph-loop | high |
| **K** | teammate work in flight (<teammate>/<teammate>/<teammate>/<teammate> на other branches) | preserve через `external-git-hosts.yaml` read-only policy + git-rick-ai-curator inventory | git-rick-ai-curator + gitrick-team-release-tracker | high |

#### Per-state best-practice exit checklist (universal — для любого репо/клиента)

Каждое состояние закрыто ТОЛЬКО когда его exit-checklist пройден. Это «чеклисты по проектам/состояниям» — общий принцип, не case-detail.

| State | Best-practice exit checklist (все ✓ обязательны) |
|---|---|
| **A** clean synced | ✓ `git rev-list --count` 0/0  ✓ submodule drift=0  ✓ branch-dropdown = только main\|active\|infra |
| **B** ahead only | ✓ incremental commits per layer (не один mega-commit)  ✓ own→push / external→PR+gate  ✓ post-push `git rev-parse HEAD == origin` |
| **C** behind only | ✓ `git pull --ff-only` (НЕ merge)  ✓ post-pull `make team-activate` если submodule/dep changed  ✓ broken-main check (always-green gate) |
| **D** diverged | ✓ §0.0.6 preservation ДО rebase  ✓ rebase (own) / PR (external)  ✓ append-only файлы union-merge не потеряны |
| **E/F/G** dirty | ✓ sit-down triage §0.0  ✓ inventory script (G)  ✓ per-category incremental commits  ✓ финал dirty=0 ИЛИ classified |
| **H** stale merged branch | ✓ local-only rescue → stash apply  ✓ switch main → FF  ✓ branch (a)/(b)/(c) → archive-tag → delete  ✓ dropdown clean |
| **I** submodule drift | ✓ registry policy applied  ✓ submodule push-before-bump (own)  ✓ parent pointer == intended  ✓ нет dirty-content-in-submodule |
| **J** red CI PR | ✓ ralph-loop fix-push-wait-assess  ✓ root cause fixed (не workaround)  ✓ CI green ДО merge claim |
| **K** teammate in flight | ✓ teammate scan 24h  ✓ external read-only policy  ✓ ни одна teammate-ветка не удалена/перезаписана |
| **ALL (финальный gate)** | ✓ **always-green:** broken main не найден ИЛИ починен (§0.0.−1)  ✓ **nothing-lost:** каждый branch/stash/worktree → (a)/(b)/(c) записан в Run Evidence  ✓ 0 unclassified в branch-dropdown  ✓ archive-теги для (b)/(c) на origin |

#### Алгоритм определения

```python
# pseudo-code; agent выполняет equivalent bash в одном tool call
# State — это set[str] (union букв), не int. Union через add(), не битовый OR.
ahead, behind = parse(`git rev-list --left-right --count origin/<branch>...HEAD`)
dirty = int(`git status --porcelain | wc -l`)
pr_state = parse_json(`gh pr view {pr_num} --json state,statusCheckRollup`)  # {pr_num} from gh pr list
submodule_drift = int(`git diff --submodule | wc -l`) > 0
teammate_branches = list_active_branches_24h_from_yaml(".agents/config/teammate-emails.yaml")

states: set[str] = set()

# Primary state (dirty × ahead/behind) — единственный из этой группы
if dirty == 0 and ahead == 0 and behind == 0:    states.add("A")
elif dirty == 0 and ahead > 0 and behind == 0:   states.add("B")
elif dirty == 0 and ahead == 0 and behind > 0:   states.add("C")
elif dirty == 0 and ahead > 0 and behind > 0:    states.add("D")
elif 0 < dirty < 50:                              states.add("E")
elif 50 <= dirty < 200:                           states.add("F")
elif dirty >= 200:                                states.add("G")

# Overlay states (могут добавляться сверху primary)
if pr_state and pr_state["state"] == "MERGED" and ahead > 0:           states.add("H")
if submodule_drift:                                                     states.add("I")
if pr_state and any(c["conclusion"] == "FAILURE" for c in pr_state["statusCheckRollup"]):
                                                                         states.add("J")
if teammate_branches:                                                   states.add("K")

# Result example: {"G", "H", "I"} = heavy dirty + PR merged stale + submodule drift
```

State — set, может содержать примеры комбинаций: `{A}`, `{B}`, `{G, H, I}`, `{F, J}`, `{C, K}`. Agent применяет стратегии **последовательно** в порядке приоритета: **K → I → G → H → J → F → D → E → B → C → A** (high-risk first; low-risk last).

Bash equivalent (для inline classification без python):

```bash
AB=$(git rev-list --left-right --count origin/$(git branch --show-current)...HEAD 2>/dev/null || echo "0	0")
AHEAD=$(echo "$AB" | awk '{print $2}'); BEHIND=$(echo "$AB" | awk '{print $1}')
DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
STATES=""
[ "$DIRTY" -eq 0 ] && [ "$AHEAD" -eq 0 ] && [ "$BEHIND" -eq 0 ] && STATES="A"
[ "$DIRTY" -eq 0 ] && [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -eq 0 ] && STATES="B"
[ "$DIRTY" -eq 0 ] && [ "$AHEAD" -eq 0 ] && [ "$BEHIND" -gt 0 ] && STATES="C"
[ "$DIRTY" -eq 0 ] && [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -gt 0 ] && STATES="D"
[ "$DIRTY" -gt 0 ] && [ "$DIRTY" -lt 50 ] && STATES="E"
[ "$DIRTY" -ge 50 ] && [ "$DIRTY" -lt 200 ] && STATES="F"
[ "$DIRTY" -ge 200 ] && STATES="G"
git diff --submodule | grep -q . && STATES="$STATES I"
echo "States: $STATES (ahead=$AHEAD behind=$BEHIND dirty=$DIRTY)"
```

#### Hard fail

- Sync-flow начат без классификации состояния через `git rev-list` + `wc -l` + `gh pr view` → `category: project-state-classification-skipped`.
- Стратегия выбрана из intuition без сверки с таблицей → `category: strategy-without-router-lookup`.
- State G запущен без `scripts/git_workspace_inventory.py` + DIRTY_TREE_ACK env → блок через mechanical hook + RCA.

### 0.0.4a. Verification asymmetry root + branch independence test (RCA 2026-06-04)

**Главный корень (META 5-why — почему агент НЕ нашёл свой косяк и делал лишнюю работу):**

| # | Почему | Ответ |
|---|---|---|
| 1 | Почему делал лишнюю работу (закрыл 3 безопасные ветки, extract уже-в-main, борьба с хуками)? | Действовал на выводе «landmine / откатит» НЕ проверив его авторитетным тестом |
| 2 | Почему действовал без проверки вывода? | Взял ПЕРВУЮ метрику подтверждающую «опасность» (two-dot diff показал «revert») и остановился — anchoring на danger-нарратив |
| 3 | Почему не фальсифицировал свой вывод? | Self-check (§9 Hypothesis falsification) проверяет «закрыл ли запрос» (OUTCOME), НЕ «истинен ли мой промежуточный диагноз» (PREMISE) |
| 4 | Почему не распознал «landmine» как capability-denial класс? | §Capability-denial gate сформулирован узко («API can't / impossible») — его триггер-слова не включают «landmine / откатит / нельзя залить / unsafe merge» |
| 5 | **КОРЕНЬ — verification asymmetry** | **Positive claim («X done/works») гейтится механически (§State-claim gate, Stop-хуки). Negative/danger claim («X опасно/landmine/откатит/нельзя/blocked») — НЕ гейтится.** Хотя действие на ЛОЖНОМ danger-выводе даёт БОЛЬШЕ waste (закрыл безопасное, redundant extract), чем ложный done. Cheapest authoritative falsification test был в 1 команде (`merge-tree`), но я не запускал его ДО действия |

**Универсальное правило (hard, переопределяет «danger = меньше проверки»):** прежде чем агент **действует** на любом выводе формы «опасно / landmine / откатит / нельзя залить / stale-base revert / blocked / can't merge / would break» — он **обязан** запустить **самый дешёвый авторитетный тест, который этот вывод ФАЛЬСИФИЦИРОВАЛ БЫ**, в том же turn. Negative claims проверяются **так же строго**, как positive. Запрещено действовать (закрыть ветку / extract / архивировать / эскалировать «нельзя») на danger-выводе, выведенном из косвенной метрики (ratio / two-dot diff / behind / «выглядит как»).

**Cheapest authoritative falsification tests (negative claim → тест который его опровергает):**

| Danger-вывод | Cheapest falsification | Если тест опроверг — вывод был ЛОЖНЫЙ |
|---|---|---|
| «ветка landmine / откатит интегрированное» | `git merge-tree $(git merge-base origin/main $br) origin/main $br \| grep -c '^<<<<<<<'` | `0` = CLEAN, 0 revert → НЕ landmine |
| «эту работу надо extract (она не в main)» | `git cat-file -e origin/main:<file>` | exists → уже в main, extract = лишняя работа |
| «push нельзя / упадёт» | `git cat-file -s $br:<file>` > 104857600 на ADDED | нет >100MB → push пройдёт |
| «API не умеет / impossible» | §Capability-denial gate ≥3 falsified alternatives | — |
| «нужна новая инфраструктура» | §Wiring-first 4 checks | — |

**Branch independence test (применение правила к sync «куча веток») — 4 проверки ДО вердикта о ветке:**

| # | Проверка | Mechanical команда | Вердикт |
|---|---|---|---|
| 1 | **3-way merge-tree** (НЕ two-dot) | `git merge-tree $(git merge-base origin/main $br) origin/main $br \| grep -c '^<<<<<<<'` | `0` = независима, 0 revert · `>0` = resolve (§V1.0 Class 4-5) |
| 2 | **revert-harness** | `git show $br:<canonical> \| grep <fixed-marker>` | старая версия + merge-tree CLEAN = ветка не трогала файл → 3-way оставит main → revert НЕТ |
| 3 | **already-in-main dedup** | `git cat-file -e origin/main:<ADDED-file>` | exists = НЕ извлекать · not-exists = truly-unique |
| 4 | **>100MB preflight** | `git cat-file -s $br:<f>` > 104857600 | >100MB = bronze, исключить (Standard 4.6) до push |

**Алгоритм sync «куча веток»:** для каждой `ahead>0` → merge-tree (1) → truly-unique ADDED (3, не <layer>/gold, не >100MB (4)) → extract на чистую ветку от origin/main → push → `gh api PUT .../merge`. Уже-в-main НЕ трогать. Закрытие ветки только после check 1+3 (НЕ по ratio/two-dot).

**Hard fail (RCA-инцидент):**
- Действие (close/extract/archive/«нельзя») на danger-выводе БЕЗ cheapest falsification test в том же turn → `category: danger-claim-acted-without-falsification` (verification asymmetry, RCA 2026-06-04).
- Ветка «landmine/откатит/нельзя залить» на основе `ratio`/`two-dot diff` БЕЗ `git merge-tree` → `category: <client>-ratio-not-merge-tree`.
- ADDED extract без `git cat-file -e origin/main:<f>` dedup → `category: already-in-main-re-extracted`.
- Ветка закрыта как «revert risk» когда merge-tree CLEAN → `category: safe-branch-closed-as-landmine` (RCA 2026-06-04, #312/#308/#305 закрыты зря).
- Push без >100MB preflight → GitHub reject → `category: large-file-push-no-preflight`.

**Связь:** §Capability-denial gate (RCA 2026-05-19) — частный случай (claim «impossible»); этот корень шире — ВСЕ danger/blocking-выводы. §State-claim verification gate (RCA 2026-05-25) — там verified positive claims; этот закрывает симметричную дыру negative claims. §V1.0 Anti-pattern «direct merge может revert» = предупреждение, проверяется merge-tree, НЕ ratio.

### 0.0.5. Subagent Chain Pattern (v3, RCA 2026-05-14)

**Корневая причина:** Owner request 2026-05-14: «через субагентов: оркестратор, разработчик, QA». Main agent в substantial sync flow не должен делать всё **inline** — должен делегировать через chain. Chain pattern обеспечивает (a) parallel work where possible, (b) independent verification, (c) recursion control through orchestrator/main-agent continuation.

**Chain template:**

```
Owner trigger ("синкни", "доделай", "sync автономно")
  ↓
main-agent/orchestrator continuation (если триггер matches §Dispatch table)
  ├─ Шаг 6 Ralph loop wave 1
  └─ Шаг 7.X dispatch:
       ↓
[ORCHESTRATOR] manager-lead-orchestrator
  ├─ читает state через §0.0.4 Router
  ├─ строит per-state action plan
  └─ spawns parallel:
       ├─ [DEVELOPER] git-sync-curator (write-enabled: commits, push, rebase, submodule bump)
       └─ [QA-1] code-reviewer (READ-ONLY review of diff)
       └─ [QA-2] inception-reviewer (READ-ONLY gap analysis vs Standard 1.15 job chain)
       ↓
[QA-3] subagent-falsification (cross-check между QA-1 + QA-2 verdicts)
  ↓
[DELIVERY] release-notes-dispatcher (если push в main + Unreleased не пуст)
  ↓
`1-auto-continue-unfinished` Шаг 8 falsification (2-hypothesis-gap-falsification + 2-so-what-outcome-ladder)
```

**Когда применять полный chain:**

- dirty ≥ 50 entries (State F/G)
- ahead ≥ 5 commits (substantial publish scope)
- PR с red CI checks (State J)
- submodule divergence touching active-project submodule (State I)
- teammate work in flight (State K)

**Когда упрощённый chain (только orchestrator + developer, без QA):**

- dirty < 50 (State E)
- ahead < 5 (small publish)

**Когда minimal (developer only):**

- State A/B/C with trivial action (ff-only pull, single push)
- Routine periodic sync ритуал

**Hard fail:**

- Substantial sync (State F/G/I/J/K) выполнен main agent inline без chain → `category: subagent-chain-skipped-substantial-sync`.
- Chain собран но QA-3 cross-check пропущен (только QA-1 OR QA-2, не оба) → `category: qa-cross-check-skipped`.
- Developer (git-sync-curator) спавнен без orchestrator plan-card → `category: developer-without-plan`.

### 0.0.5a. GitHub sync telemetry + no-extra-work eval (RCA 2026-06-07)

**Корневая причина:** правила sync/hook-chain раньше отвечали на вопрос «безопасно ли?», но не отвечали на вопрос owner'а «почему стало быстрее и почему агент больше не делает лишнюю работу». Один green guard или текст в skill — НЕ доказательство. Нужно измерять полный route и фальсифицировать extra work на данных.

**Канонический measured route для полного sync:**

```bash
make team-main-sync-measured
make sync-github-telemetry-summary
make sync-github-telemetry-owner-line
make sync-github-telemetry-eval
```

`make team-main-sync-measured` делает тот же flow, что `make team-main-sync`, но оборачивает фазы в telemetry: `git_fetch`, `checkout_main`, `pull_rebase_main`, `team_activate`, `team_sync_guard` и внутренние guard-фазы. Старый `make team-main-sync` оставлен для совместимости, но в substantial sync-report owner получает данные только из measured route.

**Storage contract:**

- Tracked protocol/code: `.agents/skills/5-sync-github-checklist/scripts/github_sync_telemetry.py`
- Tracked real-route eval budget: `.agents/skills/5-sync-github-checklist/evals/github-sync-budget.json`
- Tracked synthetic no-extra-work eval budget: `.agents/skills/5-sync-github-checklist/evals/github-sync-no-extra-work-budget.json`
- Runtime JSONL, gitignored: `.agents/memory/runtime/5-sync-github-checklist/github-sync-telemetry.jsonl`

Skill владеет протоколом и бюджетом, но mutable timing rows не живут в `.agents/skills/...`, чтобы не создавать постоянный git-churn.

**JSONL schema minimum:**

`session_id`, `run_id`, `bead_id`, `repo_root`, `client_domain|null`, `branch`, `stage`, `phase`, `timestamp`, `duration_ms`, `status`, `command`, `exit_code`, `action_counts`, `state_set`, `qa_code_review`, `qa_design_review`, `qa_ui_review`, `verdict`, `blocked_reason`.

`action_counts` обязателен для falsification, не только для скорости: `commands_count`, `git_commands_count`, `gh_commands_count`, `network_calls_count`, `fetch_count`, `guard_count`, `worktree_created_count`, `rebase_attempt_count`, `merge_attempt_count`, `push_count`, `auto_stop_commit_count`, `extra_actions_count`, `missing_actions_count`.

**No-extra-work proof = данные + eval, не ощущение:**

| Claim | Mechanical evidence |
|---|---|
| «стало быстрее» | `run_total.p50/p95` + phase p50/p95 по `team_sync_guard` / QA stages на ≥10 сопоставимых runs |
| «лишняя работа не делается» | synthetic replay eval по `github-sync-no-extra-work-budget.json`: `extra_actions_count=0`, `missing_actions_count=0`, `worktree_created_count=0` для `already_in_main` / `mergeable_pr` / `dirty_under_50` в одном complete run |
| «QA/design не пропущены» | telemetry rows contain `qa_code_review`, `qa_design_review`, `qa_ui_review` verdicts before final `sync complete` |
| «hook-chain не деградировал» | `gen_hook_jtbd_registry.py --check` PASS + no new uncovered hook beyond baseline |

**Что НЕ считается доказательством:**

- skill text says telemetry exists;
- empty/missing telemetry JSONL;
- incomplete route with only one phase;
- один green `make team-sync-guard`;
- `hook-eval gate OK` при старых baseline-uncovered hooks;
- локальный `git log origin/main` вместо GitHub API truth;
- меньше жалоб owner'а без command trace.

**Evals vs GEPA decision:**

- Evals first: deterministic regressions (`new hook has no eval`, `QA stage missing`, `Stage Compliance Tracker absent`, `sync complete before dirty classification`, `already-in-main re-extracted`, `worktree-per-merge`).
- GEPA only after eval coverage exists and failures are behavioral/prompt-level: agent read the rule but still chose wrong ordering, hid p95, skipped owner-facing progress despite telemetry data.
- No GEPA for missing mechanical checks. Missing detector = implement eval/hook/script first.

**Owner-facing progress line (обязательна перед `sync complete`):**

```text
GitHub sync progress: stage qa_code_design_review PASS · current 18m · p50 11m · p95 42m · blockers 0 · delivered_without_qa 0
```

**Hard fail:**

- Full sync report без telemetry summary/eval verdict → `category: sync-telemetry-proof-missing`.
- `sync complete` без QA/design verdict fields для substantial flow → `category: sync-qa-verdict-telemetry-missing`.
- Already-in-main / mergeable PR сценарий создал worktree или re-extract → `category: no-extra-work-eval-failed`.

### 0.0.6. «Nothing lost» preservation contract (v4, RCA 2026-05-14 + 2026-05-16)

**Канонический источник:** AGENTS.md §`Nothing-lost & team-can-use-everything invariant (RCA 2026-05-16)`. Этот раздел skill — operating procedure того инварианта для sync flow. При расхождении — AGENTS.md канон.

**Корневое определение (v4, RCA 2026-05-16):** работа «не потеряна» ТОЛЬКО когда её уникальный контент **достижим из `origin/main` обычным `git pull`**. Stash / archive-tag / wip-branch / reflog / orphan = recovery ref, **НЕ delivery**. «Сохранил в stash/tag» как доказательство «ничего не потеряно» = **ложь** (RCA 2026-05-16: 30 skill-файлов жили только на stale wip-ветке, недостижимы команде).

**Корневая причина:** Owner steering 2026-05-14: «чтобы ничего не потерялось». Sync операции имеют **6 potential loss vectors** которые без contract систематически срабатывают. Universal — для любого repo / любых клиентов / любых teammates.

#### 5 потерь и mitigation

| Loss vector | Что теряется | Universal mitigation |
|---|---|---|
| **L1 Teammate work in flight** | branches других авторов на other repo/branch которые не merged | Перед `checkout`, `reset`, `rebase`: `git log --all --since=24h --author='<email>'` для каждого teammate из workspace registry + `gh pr list --state open`. Если есть unmerged commits — stop, не destroy |
| **L2 Untracked local-only** | новые файлы (агенты, скиллы, KB drafts) untracked, не в stash, не в commit | Перед любой destructive op (`reset --hard`, `clean -fd`, `checkout` чужой ветки) — `git stash push -u -m "auto-sync-rescue-<date>" -- <selective paths>` для каждого top-level untracked directory |
| **L3 Submodule HEAD ahead of parent gitlink** | работа сделанная внутри submodule, parent ещё не bumped | `git submodule foreach 'git status --short'` ДО любой destructive op. Если submodule dirty — `cd <sub> && git push HEAD` then bump parent. Submodule registry policy из `submodules-and-projects-registry.yaml` |
| **L4 Stash forgotten** | работа в stash после context switch / new session | `git stash list` в начале каждой sync-session. Если N stashes > 5 — обязательная classification + pop/drop per stash. Пометить unresolved stashes в `<internal-folder>/ai.legacy.md` §Stash backlog |
| **L5 Force-push на external** | overwrite work других на external repo (`<internal-host>/*`, `<internal-host>/*`) | `external-git-hosts.yaml` SSOT определяет policy per host. Force-push в external — **hard fail** без `{HOST}_PUSH_APPROVED_BY` env var + explicit owner go. `--force-with-lease` only, never `--force` |
| **L6 Parallel-session untracked work** (NEW, RCA 2026-05-14 incident-cleaned-parallel-cost-allocation) | `git clean -fd <path>` уничтожает untracked work другой Claude/Cursor/IDE сессии — параллельный agent создаёт scaffold через `Write` tool_use, но ещё не сделал `git add`. Высокий риск для `<internal-module>/<new-framework>/`, `.agents/skills/<new-skill>/`, `<internal-folder>/clients/<new-client>/`, build artefacts (`.rick-form-build/`, `<layer>/`, dist/) | **ПЕРЕД `git clean -fd <path>`** обязательная 3-layer проверка: (a) `find <path> -type f -mmin -60` — файлы созданы за последний час и mtime не от моих tool calls → STOP; (b) `ls -lat /tmp/claude-501/-Users-*-heroes-rickai-workspace/ \| head -5` — активные параллельные Claude sessions → STOP; (c) `grep -lE '"file_path".*<path>' ~/.claude/projects/-Users-*-heroes-rickai-workspace/*/subagents/*.jsonl 2>/dev/null \| head -5` — Write tool_use entries в активных subagents → STOP. Если **ЛЮБОЙ** layer positive — `git clean -fd` **запрещён**, использовать `git stash push -u -m "rescue-parallel-<path>" -- <path>` вместо. **Recovery if already cleaned**: scan `~/.claude/projects/<project>/<session>/subagents/*.jsonl` для `Write tool_use entries`, extract `block.input.content`, write back to disk через template script `/tmp/recover_lost.py` (see RCA 2026-05-14 для канона) |

#### Preservation checklist (применять ПЕРЕД любой destructive sync op)

```bash
# 1. Teammate scan (last 24h)
for email in $(cat .agents/config/teammate-emails.yaml); do
  git log --all --since=24h --author="$email" --oneline | head -5
done
# Если N>0 — выписать в reasoning log, ПРОВЕРИТЬ что unmerged commits в их branches не уйдут

# 2. Untracked rescue
git status --porcelain | grep "^??" | awk '{print $2}' | head -50
# Если есть .agents/ / .claude/ / <internal-folder>/ / new files → stash push -u

# 3. Submodule check
git submodule foreach 'git status --short'
git diff --submodule
# Если modified content — commit+push внутри submodule СНАЧАЛА

# 4. Stash inventory
git stash list
# Если N>5 — pause sync, классифицировать каждый, decide pop/drop

# 5. External target check
gh remote get-url origin | grep -qE "(<internal-host>|git\.rick\.ai)" && \
  echo "EXTERNAL HOST — push требует {HOST}_PUSH_APPROVED_BY"
```

#### v4 upgrade — per-branch/stash (a)/(b)/(c) classification (RCA 2026-05-16)

**L7 Stash/branch scope (NEW, RCA 2026-05-16):** bare global `git stash push -u` (без pathspec) захватывает untracked work параллельной сессии workspace-wide (incident S9). В sync **запрещён** bare `-u` — только `git stash push -u -- <selective paths>`. `git stash pop`/`drop` → заменить на `git stash apply` + per-file (a)/(b)/(c) verify.

**Завершающий gate sync — каждый branch / stash / worktree / orphan classified в (a)/(b)/(c):**

| Кат. | Значение | Verify-команда | Закрыть? |
|---|---|---|---|
| **(a) in-main** | контент достижим из `origin/main` | `git cat-file -e origin/main:<path>` / `git merge-base --is-ancestor <sha> origin/main` | ✅ + delete branch |
| **(b) superseded/churn** | дублирует более новую интегрированную версию в main ИЛИ generated churn | archive-tag + 1 строка причины | ✅ + delete branch, reason записан |
| **(c) owner-decision** | уникальная ценная работа НЕ в main | archive-tag + эскалация владельцу с точной командой extract | ⚠️ flag, НЕ закрывать молча |

**Stale-base extraction (RCA 2026-05-16):** ветку N-behind `origin/main` **запрещено** branch-merge'ить (reverts интегрированное — инцидент 246k строк). Только ADDED-only: `git diff --diff-filter=A --name-only origin/main..<stale>` → `git checkout <stale> -- <added files>` на свежей ветке от origin/main. MODIFIED файлы → origin/main это integrated truth, остаются (b)/(c) на archive ref.

**Branch-dropdown hygiene:** в финале sync в IDE branch-dropdown допустимы ТОЛЬКО `main` | активная рабочая ветка | registry-infra (`beads-sync`). Остальное = незакрытый DoD → resolve в (a)+delete / (b)+delete / (c)+эскалация.

#### Hard fail

- Destructive op (`reset --hard`, `clean -fd`, force-push) выполнена без preservation checklist `git stash list` + teammate scan + submodule check → `category: nothing-lost-contract-skipped`.
- Stash list > 5 несколько sessions подряд без classification → `category: stash-backlog-accumulating`.
- Force-push в external repo без env var → blocked by hook + RCA.
- Финал sync с «всё ок / ничего не потеряно» при ≥1 ветке/stash без (a)/(b)/(c) classification → `category: nothing-lost-false-claim` (AGENTS.md §Nothing-lost).
- Branch-dropdown содержит non-(main|active|infra) ветку без эскалации → `category: branch-dropdown-clutter-unresolved`.
- Stale-base ветка branch-merged вместо ADDED-only extract → `category: stale-base-revert`.
- `git stash drop`/`pop` вместо `apply` + per-file (a)/(b)/(c) → `category: nothing-lost-false-claim`.

#### Sanctioned recovery-ref drain (RCA 2026-05-16 inception G2 — закрывает stash/branch accumulation deadlock)

**Проблема (subagent-caught, 2× independent):** `apply` not `pop` + `stash drop/clear` BANNED + `branch -D` gated unless origin-tag → recovery refs **накапливаются монотонно**, L4 hard-fail штрафует >5 stashes, но **легального пути очистки нет** → deadlock. Это НЕ «nothing lost», это «nothing ever cleaned» — новый класс долга.

**Sanctioned drain path (документированный, НЕ аварийный) — выполняется ПОСЛЕ verify:**

| Recovery ref | Условие легального drain | Sanctioned команда |
|---|---|---|
| **stash** | для КАЖДОГО файла в stash: `git cat-file -e HEAD:<path>` PASS И `git diff stash@{N}:<path> HEAD:<path>` пусто (контент = (a) in-HEAD) | `DESTRUCTIVE_GIT_STASH_ACK="drain: stash@{N} all files verified (a) in-HEAD <sha>" git stash drop stash@{N}` |
| **branch (b) superseded** | archive-тег указывающий на tip **подтверждён ON ORIGIN** (`git ls-remote --tags origin \| grep <tag>`) | `git branch -D <b>` — hook v3 сам verify origin-tag, разрешит (zero-loss provable) |
| **branch (a) in-main** | tip ∈ `origin/main` (`git merge-base --is-ancestor <tip> origin/main`) | `git branch -d <b>` (merged — проходит hook без ACK) |
| **branch (c) owner-decision** | НЕ drain. archive-тег push на origin + эскалация владельцу | оставить, flag |

**Правило:** drain — это **завершающий шаг** каждого sync (не накопление до >5). После (a)/(b)/(c) verify + (для (b)) archive-tag-on-origin confirmed → немедленный sanctioned drain. Stash list в конце sync ≤ предыдущего, не растёт. Это снимает L4 `stash-backlog-accumulating` штраф легально.

**Hard fail:** sync завершён с stash list > previous без sanctioned drain attempt → `category: recovery-ref-accumulation-no-drain`.

### 0.0.5a. QA-3 cross-check verdict format (v3, RCA 2026-05-14 inception G3)

**Корневая причина:** Chain §0.0.5 говорит «QA-1 + QA-2 → QA-3 cross-check», но без verdict schema cross-check декоративен. Inception-reviewer G3 (2026-05-14): «без schema PASS/FAIL/CONTRADICTION — placebo gate».

**Контракт QA-3 (subagent-falsification) output:**

| Dimension | QA-1 verdict | QA-2 verdict | Agreement | Escalation |
|---|---|---|---|---|
| Correctness | approve / block / approve-with-followups | ready / needs-revision / blocking | `agree` / `disagree` / `partial-agree` | если `disagree` → owner для tie-break, иначе chain proceeds |
| Architecture | tags | tags | agree/disagree | same |
| Generalization (4×yes) | yes/no per Q1-Q4 | yes/no per Q1-Q4 | agree/disagree | если оба `no` на same Q → block, чинить до commit |
| Hard fails enforceable | mechanical/partial/no | mechanical/partial/no | agree/disagree | если оба `no` → follow-up bead для hook |
| Glue effort owner (Δ vs v2) | numeric | numeric | within ±20% / >20% diff | если >20% → escalate which is correct |

**Agreement rules:**

- `agree` (оба verdicts compatible, конкретные refs match): proceed to commit/push
- `partial-agree` (один блокирует, второй approve-with-followups на ту же тему): proceed, but include followups в commit message
- `disagree` (опposite verdicts на same dimension): mandatory pause, escalate to owner с <client>-side comparison

**Escalation format в чат:**

```
QA-3 cross-check disagreement on <dimension>:
  QA-1 (<subagent>): "<verbatim quote>" — verdict X
  QA-2 (<subagent>): "<verbatim quote>" — verdict Y
  Root: <my analysis why they disagree>
  Recommend: <my choice + 1-line rationale>
  Owner action: confirm or override (1 click)
```

**Hard fail:**

- Chain executed без QA-3 cross-check table → `category: qa-cross-check-skipped`
- Disagree detected но agent proceeded без escalation → `category: disagreement-suppressed`

### 0.0.7. Autonomous continuation integration — sync trigger detection (v3, RCA 2026-05-14)

**Корневая причина:** старый continuation envelope detected only «доделай / continue» triggers. Sync triggers («синкни», «push», «sync», «rebase», «закрой PR») должны routed в **autonomous sync mode** который dispatches `git-sync-curator` + applies §0.0.4 Router + §0.0.5 Chain + §0.0.6 Preservation.

**Dispatch для main-agent autonomous continuation:**

| Trigger phrase | Dispatch | Reason |
|---|---|---|
| «синк / синкни / sync / push в main / закрой PR» | main agent → §0.0.4 Router → §0.0.5 Chain | Sync as autonomous closure |
| «доделай sync / закрой sync session» (есть prior turns) | main agent → §0.0.4 Router + same-session ownership | Continuation |
| «открой PR / push branch / rebase» (одно действие) | main agent → minimal chain (git-sync-curator only) | Atomic action |
| «push в <teammate> / push в <teammate> / external sync» | main agent → <teammate>-git-sync OR git-rick-ai-curator | External host, special policy |

**Hard fail:**

- Sync trigger без orchestrator/continuation routing → main agent делает всё inline → `category: sync-without-autonomous-routing`.
- Autonomous dispatch проигнорировал §0.0.4 Router → запустил Chain без state classification → `category: chain-without-router`.

### 0.0.8. Recovery Playbook — 6 failure modes (v3, RCA 2026-05-14 inception G4)

**Корневая причина:** Sync mid-flight failures (network drop, force-push reject, submodule 403, rebase abort, hook fail, conflict cascade) систематически срабатывают, но v2 описывал только happy path Сценарии A-E. Stage 6 «Recover» job chain была пустая → agent блуждал, terminates с pseudo-completion.

**Universal — для любого repo / branch / submodule. Применять как первый response при error message от git/gh.**

#### F1: Push rejected (non-fast-forward)

```bash
# Symptom: "Updates were rejected because the remote contains work that you do not have locally"
git fetch origin <branch>
git log HEAD..origin/<branch> --oneline | head -5  # what teammate added
# Decision tree:
#   - own repo + we know teammate work — rebase: git rebase origin/<branch>
#   - own repo + we don't know — abort + ask owner
#   - external repo (<internal-host>/<internal-host>) — NEVER force, abort + PR
# Recovery:
git rebase origin/<branch>  # if conflicts → F4
git push --force-with-lease origin <branch>  # NEVER --force
```

#### F2: Force-with-lease rejected (someone else pushed since fetch)

```bash
# Symptom: "stale info" / "remote ref is at <SHA> but expected <SHA>"
# Means: another agent / teammate pushed in between our fetch and our push
# DO NOT retry with --force. STOP.
git fetch origin <branch>
git log <previous-our-HEAD>..origin/<branch> --oneline  # see what they did
# Decide: do they overlap our changes?
#   - no overlap → rebase + retry with --force-with-lease
#   - overlap → manual merge + commit + retry
#   - destructive overlap (force-pushed history) → escalate to owner: F2-escalation
```

#### F3: Rebase mid-flight abort needed

```bash
# Symptom: rebase stuck on conflict cascade, no progress
git rebase --abort  # safe — restores pre-rebase state
git status  # confirm clean
# Decide alternative:
#   - merge instead of rebase: git merge origin/<branch> --no-edit
#   - cherry-pick selective commits: git cherry-pick <sha>
#   - reset and re-do: git reset --hard origin/<branch> + manual replay (last resort)
```

#### F4: Conflict in append-only narrative files (changelog.md / ai.incidents.md / ai.legacy.md)

```bash
# Per AGENTS.md §Append-only narrative files + .gitattributes merge=union
# Should auto-resolve via union driver. If not:
git config merge.union.name "Union merge driver"
git config merge.union.driver "cat %B >> %A && cp %A %X"
bash scripts/setup/git_config_merge_drivers.sh  # reinstall driver
git rebase --continue  # retry
```

#### F5: Submodule push 403 (no write access to upstream)

```bash
# Symptom: git push в submodule даёт 403
# Decision:
gh repo view <submodule-upstream> --json viewerCanAdminister
#   - viewerCanAdminister=true → not 403 issue, retry with correct creds
#   - false + own fork exists → push to fork, NOT upstream
gh repo fork <submodule-upstream> --remote-name fork --clone=false  # idempotent
git -C <submodule-path> push fork HEAD:<branch>
# Then parent: do NOT bump gitlink to local-only SHA, bump to fork SHA
```

#### F6: Network drop / timeout / SSL error

```bash
# Symptom: "Could not resolve host", "SSL_ERROR_SYSCALL", "Operation timed out"
# 3× retry with backoff 5s, 15s, 45s per §3.0.1
for backoff in 5 15 45; do
  sleep $backoff
  git <command> && break
done
# If still fails after 3 retries:
#   - check VPN / proxy state
#   - check gh auth status (token may have expired mid-session)
#   - if owner in geo-restricted location (per RCA 2026-05-13) → fall back to local-only commits, defer push
```

#### F7 (bonus): Pre-push hook mutated worktree post-push

```bash
# Symptom: push succeeded (remote HAS our SHA) but worktree shows new dirty files
# Per §3.1 — NOT a failure, this is expected hook behavior (snapshots / latest-files generation)
# Verify remote:
git ls-remote origin <branch> | awk '{print $1}'  # should match our pre-push HEAD
# If matches → sync IS complete. Treat new dirty files as separate task (next commit decision)
# Do NOT retry push. Do NOT panic.
```

#### F8 (RCA 2026-05-16 inception G3): destructive_op_full_ban.py fail-closed offline

```bash
# Symptom: `git branch -D <b>` BLOCKED by hook with
#   "cannot prove zero-loss — `git fetch origin main` failed (network)"
# Cause: hook v3 is fail-CLOSED — without origin reachability it cannot verify
#   the recovery tag is ON ORIGIN, so it refuses (correct for data safety).
# This is NOT a hook bug — it is the safety contract. The branch is NOT lost
#   (it still exists locally + likely on origin). Sync is NOT hard-stuck:
#
# Legitimate offline finish (ONLY after you manually verified team-recoverability):
#   1. Confirm tip is preserved: `git tag --points-at <branch>` shows an archive/* tag
#      AND you KNOW that tag (or the branch itself) is already on origin from a
#      prior session — OR the branch tip is an ancestor of a previously-fetched origin/main.
#   2. Then: DESTRUCTIVE_GIT_BRANCH_ACK="offline: <branch> tip <sha> preserved by
#      archive/<tag> confirmed on origin <date>, manually verified team-recoverable" \
#      git branch -D <branch>
#   3. If you canNOT manually confirm origin-recoverability → DO NOT delete.
#      Leave the branch (it IS the recovery ref) + note in Run Evidence as
#      (c) owner-decision: "remote cleanup pending network". Zero-loss holds —
#      a stale branch on origin is itself a valid recovery ref.
# Never bypass via git -C / $() / unsetting the hook — that re-opens the
#   incident class this hook closes.
```

#### Recovery decision table

| Error message contains | First action | Section |
|---|---|---|
| "Updates were rejected" / "non-fast-forward" | F1 | rebase + force-with-lease |
| "stale info" / "remote ref expected" | F2 | fetch + analyze + selective replay |
| Rebase conflict on N>3 files | F3 | abort + alternative path |
| Conflict in changelog.md / ai.*.md | F4 | union driver verify |
| "Permission to ... denied" / 403 on submodule | F5 | fork route |
| "Could not resolve host" / SSL / timeout | F6 | 3× backoff retry |
| Push success + worktree dirty after | F7 | verify remote, NOT retry |
| "cannot prove zero-loss" / hook fail-closed offline | F8 | manual verify → documented ACK, OR leave branch as recovery ref (zero-loss holds) |

#### Hard fail

- Sync error encountered, agent не использовал F1-F7 lookup → `category: recovery-playbook-skipped`
- Force-push (`--force` без `--force-with-lease`) использован при F1/F2 → `category: unsafe-force-push`
- Retry without backoff на network error → `category: tight-retry-loop`

### Autonomy contract для sync

Когда owner даёт явную команду «синк в origin/main» / «push всё» / «команда должна получить наработки»:
- Агент выполняет **полный** sync-flow автономно, без промежуточных подтверждений.
- Промежуточные вопросы допустимы **только** при: (a) конфликте merge, который агент сам разрешить не смог после ≥3 falsified подходов (не «есть конфликт → спрошу», а «не разрешается потому что X/Y/Z»), (b) 403 на push в субмодуль, (c) файле >100MB, (d) **destructive op на external/shared resource** (push в чужой репо, force-push main, drop production data).
- Итоговый отчёт выдаётся **после** завершения sync, не между волнами.
- **Запрещено:** спрашивать owner «подтверди G01–G09» или «дай ок по каждому пункту» — owner уже дал команду.

#### Решение о порядке merge / диагностике CI = обязанность агента, не owner (RCA 2026-06-03)

**Trigger phrase (owner direct, 2026-06-03):** «пропиши в скиле, что ты обязан сам изучать все и сам должен принимать решения для синка, изучив, что есть, выписав подробности и разрулив конфликты и ничего не потеряв».

**Главный принцип (hard, переопределяет default «спрошу owner порядок»):** при команде sync агент **обязан сам** довести до решения, не возвращая owner развилку вида «какой порядок merge выбрать (1/2/3)?» / «диагностировать ли CI-red сначала?» / «сразу мержить #N или нет?». Развилка о **порядке/стратегии** sync — это **не** одно из разрешённых исключений (a)–(d) выше; это lazy handoff (нарушает §0.0.1 Confidence calibration). Owner ревьюит **готовый результат** post-hoc, а не пред-решает план.

**4 обязательных self-step ДО любого вопроса owner (всё автономно):**

| # | Шаг | Mechanical действие | Что запрещено вместо этого |
|---|---|---|---|
| **1** | **Изучить ВСЁ** | `gh pr list --json number,title,mergeable,statusCheckRollup` + `git log origin/main..<branch>` + `git diff --name-status origin/main..<branch>` для КАЖДОГО PR/ветки. Если CI red — **прочитать сам failing лог** (`gh run view <id> --log-failed` / `gh pr checks <N>`), не «вижу red, спрошу что делать» | спросить «что внутри PR?» / «диагностировать ли CI?» — это и есть изучение, делается самим |
| **2** | **Выписать подробности** | per-PR таблица в чат: ветка / mergeable / CI verdict (root cause если red) / что внутри / решение `merge now` \| `rebase-then-merge` \| `fix-CI-then-merge` \| `defer + reason` | сводка «5 PR, часть red» без per-PR root cause |
| **3** | **Разрулить конфликты** | CONFLICTING → `git rebase origin/main` в worktree → resolve (union driver для narrative-файлов, ручной для кода) → retry. CI-red общий на всех = broken-main → §Always-green: fix root → re-run. ≥3 falsified подхода ДО любого «не смог» (§Capability-denial gate) | вернуть «есть конфликты, что делать?» без попытки resolve |
| **4** | **Ничего не потерять** | per-branch (a)/(b)/(c) classification (§0.0.6 Nothing-lost contract) ДО любого `branch -d` / закрытия PR. Каждая ветка получает verdict in-main / superseded / owner-decision | закрыть ветку «сохранено на теге» без (a)/(b)/(c) |

После 4 self-step агент **либо** выполняет merge-план автономно и показывает результат, **либо** (если genuine blocker (a)–(d)) присылает ОДИН конкретный вопрос с уже проделанным анализом (формат §0.0.1 «Допустимые формулировки»).

**Hard fail (RCA-инцидент в `<internal-folder>/ai.incidents.md`):**
- Возврат owner развилки о порядке/стратегии merge («какой порядок 1/2/3?» / «диагностировать ли CI сначала?») при наличии команды sync → `category: sync-order-decision-offloaded-to-owner` + переделка (агент проходит 4 self-step и решает сам).
- Заявление «CI red на всех PR» без прочитанного failing-лога хотя бы одного → `category: ci-red-not-self-diagnosed` (нарушение §0.0.1 self-check + §Always-green broken-main detection).
- «Есть конфликт → спрашиваю owner» без ≥3 falsified подходов resolve → `category: conflict-not-self-resolved` (нарушение §Capability-denial gate).

**RCA-источник:** 2026-06-03 — owner дал «синк в origin/main», агент (turn 1) собрал статус 5 PR (#298/#305/#308/#312/#314), увидел red CI на всех + 3 CONFLICTING, и вместо самостоятельной диагностики CI-логов + resolve вернул owner развилку «выбери порядок: (1) чинить CI-root, (2) мержить #314, (3) harness #312». Owner steering: «ты обязан сам изучать все и сам принимать решения». Корень: §721 перечислял 3 исключения но не запрещал явно развилку о порядке; §0.0.1 (2× self-check) не сработал в голове потому что агент ложно прочитал стр. 48 «explicit review» как «спроси owner порядок». Closed via PR (этот) — wiring §721 + §0.0.1 + стр. 48, не новый слой (§Wiring-first gate).

### Critical loop-breakers (ОБЯЗАТЕЛЬНО перед повторной попыткой commit/push)

Если sync уже пытались выполнить и агент повторяет тот же цикл `git add -A -> git commit -> git push`, **сначала исправить blocker state**, а не запускать те же команды ещё раз.

0. **Stage-all intent classification**
   - Если пользователь просит `stage all`, сначала определить режим:
     - `local checkpoint snapshot` — нужно просто зафиксировать текущее локальное состояние в staging; после этого **не** считать staged set publish-ready и **не** переходить автоматически к `commit/push`.
     - `publishable selective commit` — нужно подготовить безопасный payload для GitHub; тогда staging по умолчанию делается **селективно по pathset**, а не `git add -A`, пока scope не очищен.
   - По умолчанию для грязного монорепо с несколькими top-level зонами (`<internal-folder>`, `<internal-folder>`, `<internal-component>`, nested repos) `git add -A` трактуется как **local snapshot**, а не как publish scope.
   - `git add -A` как publish step разрешён только один раз в самом конце, когда changelog обновлён, hook-generated outputs стабилизированы, nested repo refs опубликованы и список публикуемых зон уже понятен.
   - **Запрещено:** после ad-hoc `stage all` считать весь staged set “следующим коммитом по умолчанию”.

1. **Stable blocker detection**
   - Если повторяется тот же blocker (`changelog.md is not staged`, один и тот же `pre-push` gate, те же `403` на nested repo push), не делать ещё один `git add -A` / `git commit` / `git push`, пока не изменён вход в этот шаг.
   - Сначала выписать blocker в чат и зафиксировать RCA через `rca-incidents`.

2. **Commit blocked by changelog**
   - Если commit blocked: `Project files changed but changelog.md is not staged`, правильное действие одно:
     - обновить корневой `changelog.md` в `## [Unreleased]`,
     - `git add changelog.md`,
     - затем один раз повторить `git commit`.
   - **Запрещено:** повторять `git add -A` и тот же `git commit` без новой записи в changelog.

3. **Pre-push hook mutates worktree**
   - Если `git push` или `pre-push` hook создаёт новые snapshots / меняет файлы:
     - остановить повторные push attempts;
     - прочитать hook (`.githooks/pre-push` или repo-local equivalent);
     - понять, что он генерирует и есть ли документированный bypass;
     - зафиксировать hook-generated files отдельным commit **или** использовать документированный bypass только после того, как результат hook уже понятен и не несёт новой кодовой проверки.
   - **Запрещено:** запускать один и тот же `git push` снова и снова, если hook продолжает мутировать дерево.
   - Для текущего root pre-push действует отдельная граница: `SKIP_REAL_MCP_SMOKE=1 git push` допустим только как documented emergency bypass, когда gate уже исследован, scope текущего publish не про RickAI real-data path, а сам blocker зафиксирован через RCA. Это не default happy-path и не замена нормальному smoke.

3.0.1. **Transient network/SSL error on push — retry with backoff (RCA 2026-05-13)**
   - Если `git push` возвращает `SSL_ERROR_SYSCALL` / `Could not resolve host` / `RPC failed; HTTP 5xx` / `unable to access ... : LibreSSL SSL_connect: SSL_ERROR_SYSCALL`:
     - Проверить network reachability: `curl -I https://github.com -o /dev/null -s -w "HTTP %{http_code} time=%{time_total}s\n"` — если ≠200 → escalate как infra issue, не retry.
     - Если network ok → **3 retry с backoff 5s/15s/45s**, не больше. Между retry — НЕ менять команду push, не trigger ad-hoc reset.
     - Если 3-й retry падает с тем же error → escalate с детальной diagnostic (`git --version`, `curl -v https://github.com`, proxy/VPN status). Не выписывать owner «не могу запушить» без diagnostic chain.
   - **Запрещено:** делать `git reset` / `git stash drop` / переустанавливать ветку при transient SSL — состояние локально valid, причина network-side.

3.0.2. **Pre-push hook hangs (lefthook wrapper stdin bug — RCA 2026-05-13)**
   - Симптомы: `git push` запущен, висит без output >2 минут; `ps aux | grep pre-push` показывает процесс с `0:00.0X CPU` и `S+` (idle wait, не active).
   - Diagnostic: `ps -p <pid> -o etime,state,pcpu` — если elapsed >120s и pcpu=0.0 → hook deadlock'нулся.
   - Корневая причина (current workspace): `.githooks/pre-push.backup` содержит `while read -r local_ref local_sha remote_ref remote_sha; do` — ждёт stdin. Lefthook `rickai-gate` command вызывает wrapper через `"$REPO_ROOT/.githooks/pre-push.backup" "{0}" "{1}" || true` БЕЗ stdin redirect → infinite hang.
   - Recovery:
     - `pkill -9 -f "pre-push.backup"` + `pkill -9 -f "lefthook run pre-push"`
     - Если commits уже прошли CI ранее (rebased re-push of tested SHAs) → `SKIP_REAL_MCP_SMOKE=1 git push --force-with-lease origin <branch>` — это **legitimate emergency bypass** документированный в самом хуке (`if [[ "${SKIP_REAL_MCP_SMOKE:-0}" == "1" ]]; then exit 0`).
     - Если commits новые и **затрагивают** `<internal-module>/<internal-component>/(tools|workflows|src/clickhouse_internal|src/data_export|scripts)` (см. `RICKAI_GATE_RELEVANT_REGEX` в hook) → НЕ bypass; вместо этого fix stdin bug в wrapper до push.
   - **Запрещено:** retry `git push` снова без kill висящих pre-push процессов — они продолжат ждать stdin и блокировать lock-файлы.

3.1. **Push already succeeded but worktree became dirty again**
   - Если `git push` завершился успешно и целевой commit уже есть на remote, а после этого дерево снова dirty из-за auto-generated snapshots / latest files / post-push refresh:
     - считать sync **успешно завершённым для опубликованного commit**;
     - отдельно выписать residual dirty tree как **новое локальное состояние после sync**, а не как причину повторять тот же sync cycle;
     - новый `git add/commit/push` запускать только если пользователь явно просит опубликовать и эти новые файлы.
   - Проверка: `git rev-parse HEAD` == `git rev-parse origin/<current_branch>` или целевой SHA найден на remote.
   - **Запрещено:** начинать новый полный sync только потому, что после успешного push появились новые `*_latest` / snapshot-файлы.

4. **Submodule / nested repo pushability**
   - Если nested repo dirty и его commit должен попасть в parent repo:
     - сначала закоммитить внутри nested repo;
     - затем убедиться, что этот SHA опубликован на каком-то remote;
     - только после этого обновлять gitlink в parent repo.
   - Если push в `origin` даёт `403`, нужно:
     - проверить наличие `fork` remote;
     - если его нет и есть `gh`, создать fork;
     - пушить в fork/new branch;
     - если publish невозможен, **не включать этот gitlink в parent commit** и залогировать blocker.

5. **Final stage-all only once**
   - `git add -A` делать после того, как:
     - changelog updated,
     - hook-generated outputs стабилизированы,
     - nested repo commits опубликованы,
     - больше не планируются новые file edits.
   - После этого идёт один финальный `git commit` и один финальный `git push`.
   - Если раньше уже делался `stage all` как local snapshot, перед publish нужно либо:
     - очистить staging (`git reset`) и собрать селективный publish set заново,
     - либо явно проверить, что staged set совпадает с intended release scope.

### 0. Merge веток в main (ПЕРЕД add/commit) — для задач с телефона и background-агентов

**Цель:** Когда пользователь ставит задачи с телефона, Cursor background-агенты и feature-ветки создают коммиты в `cursor/*`, `feature/*`, `fix/*`. При `/sync-github` нужно собрать все эти ветки в `main`, чтобы команда получала единый актуальный main.

**Порядок выполнения (в начале sync, до add/commit):**

1. Если есть незакоммиченные изменения: **СНАЧАЛА** §0.0.6 preservation contract (teammate scan + (a)/(b)/(c) classification). Затем **selective** stash (НЕ bare global `-u` — это incident S9 root cause: захват untracked параллельной сессии workspace-wide): `git stash push -u -m "sync-merge-$(date +%Y%m%d)" -- <selective top-level paths>` для каждого intended directory. Восстановить: `git stash apply` (НЕ `pop` — `apply` сохраняет stash как recovery ref до verify; per §Nothing-lost invariant). Bare `git stash push -u` без pathspec **запрещён** в sync (см. §0.0.6 L2 + AGENTS.md §Nothing-lost & team-can-use-everything invariant).
2. `git fetch --all --prune` — обновить все remote-ветки
3. `git checkout main` (если не на main)
4. `git pull --rebase origin main` (или `git pull origin main`) — подтянуть актуальный main
5. **Для каждой удалённой ветки**, у которой есть коммиты впереди main:
   - Исключить: `main`, `HEAD`, ветки вида `replit-*`, `sync/windows-*` (старые sync-ветки)
   - Включить: `cursor/*` (background-агенты), `feature/*`, `fix/*`
   - Команда: `git merge origin/<branch> --no-edit`
   - **Если конфликт:** `git merge --abort`, залогировать в чат: `⚠️ Merge skipped (conflicts): <branch>`, перейти к следующей ветке
   - **Если успех:** залогировать: `✅ Merged: <branch>`
6. После merge-цикла: при stashed изменениях — `git stash apply` (НЕ `pop` — `apply` сохраняет stash как recovery ref до per-file (a)/(b)/(c) verify; `pop` запрещён §0.0.6 L7 + hard fail `nothing-lost-false-claim`). Drain stash только через sanctioned path (§0.0.6 «Sanctioned recovery-ref drain»). Затем перейти к п.1 (Windows-имена) и далее по чеклисту

### 0.1. Sync-fetch-rebase-push — когда local main разошёлся с origin/main

**Цель:** Привести local main и origin/main к единому состоянию, когда оба имеют коммиты, которых нет у другого (diverged history).

**Когда применять:** `git log --oneline HEAD..origin/main` показывает коммиты И `git log --oneline origin/main..HEAD` тоже показывает коммиты.

**Порядок:**

1. **Stash:** §0.0.6 preservation contract first (teammate scan + (a)/(b)/(c)). Затем **selective** `git stash push -u -m "sync-rebase-$(date +%Y%m%d%H%M)" -- <selective paths>` (НЕ bare global `-u` — incident S9; bare захватывает untracked work параллельной сессии workspace-wide). Bare `-u` без pathspec **запрещён** (AGENTS.md §Nothing-lost invariant + §0.0.6 L2/L6/L7).
2. **Отключить хуки для rebase:** `git -c core.hooksPath=/dev/null pull --rebase origin main`
   - **Почему отключать хуки:** `post-checkout` / `post-rewrite` хуки (например `post_sync_bootstrap_guard.py`) мутируют дерево во время rebase, создавая dirty tree между промежуточными шагами rebase и вызывая `error: Your local changes would be overwritten by merge`
   - Хуки восстанавливаются автоматически при следующем обычном git-действии
3. **Конфликты при rebase:**
   - Если конфликт в append-only файлах (`ai.incidents.md`, `changelog.md`) — сохранить обе стороны, отсортировать по дате
   - `git add <resolved_file> && git -c core.hooksPath=/dev/null rebase --continue`
   - Если конфликт неразрешимый: `git rebase --abort`, перейти к стратегии merge (без rebase)
4. **Push:** `git -c core.hooksPath=/dev/null push origin main`
5. **Stash restore:** `git stash apply` (НЕ `pop` — `apply` сохраняет stash как recovery ref до verify)
   - Если apply конфликтует (файл из rebase уже существует): **запрещено** `git stash drop` «приняв что файлы уже в HEAD» вслепую (это incident-class nothing-lost violation + `git stash drop` BANNED hook'ом `destructive_op_full_ban.py`). Вместо: для КАЖДОГО файла в stash прогнать §Nothing-lost (a)/(b)/(c) — `git cat-file -e HEAD:<path>` И `git diff stash@{0}:<path> HEAD:<path>`; если контент идентичен HEAD → (a) in-HEAD, stash оставить как archive ref (drop только через owner-ACK); если отличается → (c) уникальная работа, extract на ветку. Никогда не drop без per-file (a)/(b)/(c) verify.
6. **Проверка:** `git rev-parse HEAD` == `git rev-parse origin/main`

**Классификация грязного дерева (ПЕРЕД коммитом):**

Прежде чем делать `git add -A`, классифицировать dirty-файлы по источникам:

| Источник | Пример | Действие |
|---|---|---|
| Скрипт массового обновления | `*.context.md` с изменённым timestamp | Коммитить, но зафиксировать в changelog побочный эффект |
| Битые симлинки из sandbox | `→ ../../../openclaw/.agents/skills/*` | Удалить |
| Runtime-артефакты | `.beads/daemon*.log.gz`, `*.bak` | Удалить, добавить в `.gitignore` |
| Backup-директории | `*.backup.2026*` | Удалить |
| Легитимные новые файлы | Новые скиллы, инструменты MCP | Коммитить |
| Embedded repos | `git status` показывает `?? path/to/repo` | Не добавлять через `git add -A`, настроить как субмодуль или `.gitignore` |

**Примечание:** Старые ветки (например `feature/cursor-onboarding` от Oct 2025) могут давать сотни конфликтов из‑за структурных изменений в main. Их merge пропускается; при необходимости — ручной merge или cherry-pick нужных коммитов.

**Post-sync teammate bootstrap (обязательно после pull/merge):**

- После успешного `git pull` / merge у тиммейта автоматически срабатывают `.githooks/post-merge` и `.githooks/post-checkout`.
- После успешного `git pull --rebase` автоматически должен сработать `.githooks/post-rewrite`.
- Hooks запускают `<internal-module>/scripts/post_sync_bootstrap_guard.py`, который:
  - смотрит diff после sync;
  - если изменились `pyproject.toml`, `setup.py`, `requirements*.txt`, `package*.json`, `.cursor/mcp.json.example`, `setup_mcp_config.py`, `Makefile`, заново запускает `team_workspace_activate.py`;
  - отдельно выводит список changed `README` / onboarding paths;
  - проверяет skill canon: `.claude/skills` и `.codex/skills` должны вести в `.agents/skills`;
  - валидирует `.cursor/mcp.json` на absolute local paths;
  - smoke-check'ит локальные MCP серверы из workspace сборки;
  - прогоняет `verify_sync_github_contract.py` как единый repo-level sync guard;
  - при `Dolt` backend сверяет bootstrap peers из `Supabase`, локально прописывает federation peer list и публикует node heartbeat.
- Для ручного прогона тот же контракт доступен как `make team-sync-guard`.

### 1. Проверка имён для Windows

- **Обязательно** запустить скрипт из корня репо: `python3 <internal-module>/scripts/check_windows_safe_filenames.py`
- Скрипт проверяет: пробел/точка в конце имени и **все символы, запрещённые в Windows** (`\ / : * ? " < > |`). Без этой проверки клон на Windows не выгружается (инцидент 13 Feb 2026, ai.incidents.md).
- Для repo/CI contract использовать tracked-only режим с case-collision check:
  - `python3 <internal-module>/scripts/check_windows_safe_filenames.py --tracked-only --check-path-length --check-case-collisions`
- Если скрипт вернул exit 1 (найдены небезопасные имена) — переименовать: `python3 <internal-module>/scripts/check_windows_safe_filenames.py --fix`, затем снова запустить без `--fix` и убедиться в exit 0. Только после этого выполнять `git add`.

### 2.0. Per-submodule classification — что брать при синке (RCA 2026-05-13)

**Корневая причина:** RCA 2026-05-13 — при `git pull --rebase origin main` agent наткнулся на «cannot rebase with locally recorded submodule modifications» и принял ad-hoc решение «reset cybos+lightrag pointers to HEAD, оставить symphony как есть» **без сверки с SSOT**. Owner steering: «явно пропиши в скилле синка, список что submodules нужно брать». До этой правки skill говорил «коммить и пушь каждый dirty submodule», но **не классифицировал** что делать при pointer-divergence ДО rebase / pull. Decision-handoff to ad-hoc reasoning вместо чтения SSOT.

**SSOT:** [`submodules-and-projects-registry.yaml`](submodules-and-projects-registry.yaml) — единственный источник истины. Список ниже — оперативная выжимка для применения **перед** pull / rebase / push. При расхождении со SSOT — обновить ОБА файла в одной сессии (same-session ownership).

**Алгоритм перед любым `git pull --rebase` / `git rebase origin/main` / `make team-main-sync`:**

1. Прочитать `submodules-and-projects-registry.yaml`.
2. `git diff HEAD --submodule=short` — для каждой записи определить: pointer SHA отличается от HEAD? содержит `-dirty`? обе?
3. По таблице ниже выбрать действие. Если действие = «reset pointer to HEAD» — попытаться `git checkout HEAD -- <path>`; если failed `cannot unpack tree object` (старый SHA не выгружен в submodule local clone) — пропустить и использовать `git -c submodule.recurse=false -c diff.ignoreSubmodules=all rebase`.
4. Pointer-bump submodules (`active-project` + `manual-bump`): если SHA отличается, **не reset**, а commit pointer bump на ветку **перед** rebase (если интент известен) или отложить bump в отдельную сессию с явным go owner.
5. Записать решение в `.agents/memory/runtime/git-sync-intents.md` (короткоживущий runtime intent log, см. AGENTS.md §git-sync-intents).

**Per-submodule policy table (11 submodules, выжимка из YAML 2026-05-07):**

| # | Path | Class | Sync policy | При pull/rebase main | При pointer divergence | Push в submodule | Notes |
|---|------|-------|-------------|----------------------|------------------------|------------------|-------|
| 1 | `<internal-module>/heroes_telegram_mcp` — telegram MCP | baseline-mcp | on-pull | взять автоматом через `make team-activate` post-merge hook | commit bump на ветку перед rebase | да, в `idkras/telegram-mcp.git` (own) | Mandatory MCP per AGENTS.md §10-14 |
| 2 | `<internal-module>/n8n-mcp` — n8n MCP | baseline-mcp | on-pull | взять автоматом через post-merge hook | commit bump | да, в `idkras/n8n-mcp.git` (own) | Mandatory MCP. `data/nodes.db` autogen — в submodule .gitignore |
| 3 | `<internal-module>/youtube-transcript-mcp` — YT transcript MCP | baseline-mcp | upstream-track | renovate/cron автоматом PR при upstream HEAD change | commit bump только если upstream-track PR смёржен | нет (no write access в `MalikElate/yt-description-mcp`) | RCA 2026-05-07 archive/local-cf0e7ac. Owner decision pending: request access / fork |
| 4 | `<internal-folder>/HumanCompiler` — internal Heroes tool | active-project | manual-bump | НЕ трогать pointer автоматом | reset pointer to HEAD если SHA отличается без явного go owner | да, в `idkras/HumanCompiler.git` (own) | Standard 7-human-compiler skill |
| 5 | `<internal-folder>/cybos` — VC ops AI assistant | active-project | manual-bump | НЕ трогать pointer | reset pointer to HEAD; divergence 2 ours vs 28 upstream — beads ticket OPEN, отдельная сессия | да, в `idkras/cybos.git` (own fork от Gerstep/cybos) | Standard 5.34. `archive/pre-rebase-2026-05-07` сохраняет local |
| 6 | `<internal-folder>/heroes-<internal-component>` — <teammate> <internal-component> | active-project | on-pull | взять автоматом если post-merge hook (мы pull-only consumer) | bump pointer **только** через skill `5-<teammate>-<internal-component>-sync` (требует <teammate>ова PR review) | в `idkras/heroes-<internal-component>.git` через PR (см. skill 5-<teammate>-<internal-component>-sync) | Owner = <teammate>; active branch `feat/<teammate>-<internal-component>-integration` |
| 7 | `<internal-folder>/laba` — AppCraftHub лендинг platform | active-project | manual-bump | НЕ трогать | reset to HEAD; bump только через `5-gitea-appcraft-sync` skill | external host `<internal-host>/AppCraftHub/laba` — read-only по AGENTS.md §External Git Hosts Policy | Юст owner. Push требует `GITEA_PUSH_APPROVED_BY` env |
| 8 | `<internal-folder>/lightrag-workspace/vendor/LightRAG` — RAG engine | vendor-mirror | upstream-track | renovate/cron автоматом PR | reset to HEAD; bump только через upstream-track PR смёрдженный в `HKUDS/LightRAG` | нет (наших коммитов нет, vendor mirror) | Standard 7-lightrag-knowledge-layer |
| 9 | `self-hosted/openclaw` — Claude deploy infra | sandbox | on-demand | НЕ трогать автоматом | reset to HEAD; bump только при active rebrand WIP | да, в `idkras/openclaw.git` (own) | Standard 5.42. Sync с paperclip |
| 10 | `self-hosted/paperclip` — Claude adapter | sandbox | on-demand | НЕ трогать | reset to HEAD; bump только при active rebrand WIP | да, в `idkras/paperclip.git` (own) | Standard 5.42. Sync с openclaw |
| 11 | `tools/symphony` — auto-coding agent | active-project | manual-bump | НЕ трогать | reset to HEAD; если `git checkout HEAD -- tools/symphony` падает `cannot unpack tree object` (HEAD SHA не в local clone) — fallback `-c submodule.recurse=false -c diff.ignoreSubmodules=all rebase` | да, в `idkras/symphony` (own) | Standard 4.15. archive branch сохраняет local. RCA 2026-05-13: `970cddcee` HEAD pointer не выгружен в local clone — symphony submodule нужен deeper fetch |

**Classification cheat-sheet (когда вообще брать):**

- **`baseline-mcp` (on-pull)** — ВСЕГДА берётся при `make team-main-sync` через `make team-activate`. Локально dirty = commit bump перед rebase.
- **`baseline-mcp` (upstream-track)** — НЕ брать вручную. Ждать renovate/cron PR.
- **`active-project` (on-pull)** — взять автоматом (как baseline-mcp), но только через team-activate hook. Manual bump запрещён.
- **`active-project` (manual-bump)** — НЕ трогать при routine sync. Bump только через soldier skill (`5-<teammate>-<internal-component>-sync`, `5-gitea-appcraft-sync`, или явный go owner для cybos/HumanCompiler/symphony).
- **`vendor-mirror` (upstream-track)** — НЕ трогать. Renovate/cron делает PR.
- **`sandbox` (on-demand)** — НЕ трогать при routine sync. Bump только если owner запросил конкретный slice (active rebrand, infra change).

**Hard fail (RCA-инцидент в `<internal-folder>/ai.incidents.md`):**

- Agent делает `git checkout HEAD -- <submodule_path>` для `manual-bump` submodule без сверки с YAML → `category: submodule-policy-skipped`.
- Agent коммитит pointer bump для `manual-bump` submodule без явного go owner → `category: submodule-manual-bump-without-go`.
- Agent классифицирует submodule (например «не наш», «можно reset», «можно push») на основе **не**-YAML источника (memory, hardcoded list в agent .md, intuition) → `category: submodule-classification-not-from-ssot`.

### 2. Субмодули — ОБЯЗАТЕЛЬНО пушить все изменения (full sync для команды)

**Цель:** Всё, что сделано локально (в т.ч. в субмодулях), должно быть доступно команде на GitHub. Не оставлять тебе проверку «запушил ли я субмодули».

- Выполнить: `git submodule status` (если команда падает из‑за "no submodule mapping" для какого‑то пути — этот путь пропускаем в списке субмодулей; основной репо всё равно синхронизируем).
- **Для каждой строки с `modified content` или `untracked content`:**
  1. Зайти в каталог субмодуля: `cd <path>`
  2. Если это git-репозиторий (`git rev-parse --git-dir` успешен): `git status`, затем `git add -A`, `git commit -m "chore: sync local changes (team sync)"` (или осмысленное сообщение), `git push origin <текущая_ветка>` (ветку взять из `git branch --show-current`). Если push возвращает 403/нет прав — залогировать в чат и перейти к следующему.
  3. Вернуться в корень репо: `cd <корень_workspace>`
- **После пуша всех субмодулей с изменениями:** в корне репо выполнить `git add <путь_субмодуля>` для каждого такого пути (обновит зафиксированный коммит субмодуля в родительском репо), затем включить эти изменения в общий коммит родителя и `git push origin <ветка>`.
- **Итог:** основной репозиторий и все субмодули, в которых были изменения, запушены; тиммейты видят полное состояние без ручной проверки.
- **Important MCP note:** папка `<internal-module>/heroes_telegram_mcp` — canonical Telegram MCP, Model Context Protocol; при наличии изменений обязательно коммит и пуш внутри неё, затем обновление ref в родителе.
- **Если push в upstream дал 403:** не останавливаться на «залогировать и перейти дальше», если parent repo должен ссылаться на этот commit. Сначала проверить `fork`, при необходимости создать fork через `gh repo fork`, затем пушить в fork-ветку (предпочтительно `ik-codex/*`) и только после этого обновлять gitlink в родителе.
- **Если nested repo не опубликован на remote:** gitlink в parent repo не должен указывать на локальный-only commit.
- **WIP-submodule policy:** Если субмодуль содержит WIP-изменения (uncommitted или staged, но не ready для release):
  - Коммитить WIP-состояние внутри субмодуля с сообщением `wip: sync local state (team sync YYYY-MM-DD)`.
  - Пушить в текущую ветку субмодуля.
  - Обновить gitlink в родителе.
  - В changelog/commit message родителя указать: `includes WIP state of <submodule>`.
  - **Не** оставлять dirty submodule как residual — team sync означает «команда видит всё текущее состояние».

### 3. Pre-commit: размер файлов

- Локальный хук `.githooks/pre-commit` и CI `.github/workflows/repo-guard.yml` ограничивают **один файл до 100 MB** (не 500 KB). Файлы >100 MB — в .gitignore или Git LFS.
- **RCA 16 Feb 2026:** лимит 500 KB был слишком жёстким и блокировал обычные ассеты (HTML/JS/CSS в `<internal-folder>/yandex direct goals/assets/`). Поднят до 100 MB.

### 4. Длинные пути (path component >255 bytes) — чтобы тиммейты видели данные в GitHub

**Проблема:** Pre-commit (`.githooks/pre-commit`) блокирует коммит, если **любой компонент пути** (имя папки или файла) длиннее **255 байт** в UTF-8 (лимит Linux/CI; GitHub не сможет выгрузить такой путь).

**Каталоги с длинными именами (известные места):**

| Путь | Описание | Решение для тиммейтов |
|------|----------|------------------------|
| `<internal-folder> flow.rick.ai/docs/` | n8n auto-generated docs: папки вида `[active]_general-..._workflow_Unknown_Narkiskeeper_prod_CAfed34NxoDKwRxu` (полное имя workflow как имя папки) | **Обрезать концовку**, а не заменять на криптичное короткое имя. Оставлять **большую часть названия** читаемой (чтобы человек понял, о чём папка). Удалять только повторяющийся суффикс в конце (например `_workflow_Unknown_Narkiskeeper_prod`), оставлять `workflow_id` для уникальности. Итог: ≤255 байт, но имя читаемое (напр. `[active]_general-..._поле_CAfed34NxoDKwRxu`). |
| `<internal-folder> flow.rick.ai/workflows/{date}/` | Экспорт через `export_all_workflows.py` | Уже безопасно. Ничего менять не нужно. |
| `<internal-folder> knowledge base .../transcripts/gdrive_*/` | Транскрипты: имена файлов с датой, темой | Короткое имя + маппинг в INDEX/README, либо .gitignore. |
| Другие каталоги с <teammate>ицей/эмодзи | При появлении — проверять длину в байтах | **Обрезать концовку**, сохраняя читаемую часть; не заменять на «что непонятно о чём». |

**Обязательные правила при длинном имени (path component >255 байт):**

1. **Не заменять на криптичное короткое имя** (типа `narkis_amocrm_notes_CAfed34NxoDKwRxu`) — по такому имени человек не поймёт, о чём папка.
2. **Обрезать концовку** (или повторяющийся суффикс в конце): оставить **большую часть названия** читаемой, убрать только лишнее до ≤255 байт. Пример: убрать `_workflow_Unknown_Narkiskeeper_prod`, оставить `_CAfed34NxoDKwRxu` для уникальности.
3. **Человекочитаемость:** после переименования по имени папки должно быть понятно, о чём данные (workflow, документ, экспорт).
4. **INDEX** в `docs/INDEX.md`: таблица `| folder_name | full_name | workflow_id |`, обновлять при экспорте.

**Если pre-commit заблокировал коммит из‑за "Path component > 255 bytes":**

- Найти проблемные пути: pre-commit выводит путь и длину компонента.
- **Правильное решение:** переименовать папку/файл **обрезанием концовки** (удалить повторяющийся суффикс в конце), чтобы длина ≤255 байт и **название осталось читаемым**. Не заменять на короткий непонятный тег.
- **Временное:** снять с индекса только эти файлы, закоммитить остальное; потом переименовать по правилу выше и добавить в следующий коммит.

**Проверка перед коммитом:** Pre-commit уже проверяет длину компонентов при коммите. Заранее (по всему дереву) можно запустить: `python3 <internal-module>/scripts/check_windows_safe_filenames.py --check-path-length` — скрипт выведет все пути с компонентом >255 байт и вернёт exit 1 (см. Script Reference ниже).

### 4.9. `{io-checklist}` — канонический макрос Input/Output/Outcome (RCA 2026-05-17)

**Корневая причина:** owner steering 2026-05-17 — «зафиксируй output чеклист в скиле в общем случае через {шаблон-макрос}… потребуем чтобы во всех скилах выводился input/output/outcome чеклист в таком формате». Output-чеклист рендерился как голый `[ ]/[x]` без колонки доказательства → owner не мог проверить «сделано» без ручного раскапывания. Это разрыв процесса (обещанное минус показанное) — закрывается макросом с **обязательной колонкой факта**.

**SSOT макроса:** этот раздел. Любой скил, доставляющий substantial-результат, рендерит блок ниже. Текст макроса **не копируется** в тело других скилов (анти-паттерн <client>-addition, CLAUDE.md §Agent role × invariant matrix) — наследуется через AGENTS.md §Mandatory delivery format §3–5, которые ссылаются сюда.

**Формат рендера (строго; статус-эмодзи + колонка факта обязательны):**

```
## INPUT checklist
| ✓ | Input | Факт (источник: команда / файл / gh-api) |
|---|-------|------------------------------------------|
| ✅ | {что получено на вход} | {реальное значение / путь / sha / row count} |

## OUTPUT checklist (что физически сделано — с фактами)
| ✓ | Output | Факт (authoritative: gh-api / git / file) |
|---|--------|-------------------------------------------|
| ✅ | {артефакт создан} | {sha / PR# MERGED ts / ls -la / test PASS} |
| ❌ | {не сделано} | {почему — конкретно, не «не успел»} |
| ⚠️ | {частично} | {что именно осталось + риск} |

## OUTCOME checklist (закрылся ли JTBD владельца — с фактами)
| ✓ | Outcome | Факт |
|---|---------|------|
| ✅ | {измеримая выгода owner} | {доказательство что JTBD закрыт} |
| ❌ | {outcome не достигнут} | {единственный незакрытый + next action} |
```

**Правила макроса (hard):**

1. **Колонка «Факт» обязательна** в каждой из трёх таблиц. Ячейка факта = команда+вывод / путь+содержимое / `gh-api sha` / `PR# state ts` / `test PASS/FAIL`. Запрещено: «сделано», «готово», «всё зелёное», пустая ячейка, «TODO».
2. **3 статус-эмодзи**: `✅` сделано-и-доказано · `❌` не сделано (+ почему конкретно) · `⚠️` частично (+ что осталось + риск). Запрещено молча опускать `❌`/`⚠️` строки ради красивого вида.
3. **Authoritative-источник для git/PR-фактов** — только `gh-api` (`gh pr view --json`, `gh api .../contents?ref=main`), НЕ локальный `git cat-file origin/main` / `git rev-parse` (stale-ref → false-claim; RCA 2026-05-17, поймано дважды в этой же сессии).
4. **Falsify перед `✅`**: если строка Outcome помечена `✅` — в Hypothesis falsification секции должна быть проверка этого факта (gap table), иначе строка = `⚠️`.

**Anti-example (RCA 2026-05-17):** `- [x] всё смержено` без колонки факта → owner не может ревью, делает steering «пиздеж, фальсифицируй».
**Corrected example:** `| ✅ | 5 PR смержены | #81 MERGED 19:41:16Z, #84 19:46:57Z (gh-api) |` — факт authoritative, проверяемый одним кликом.

### 4.10. Layer 2 mechanical — `head_pin_preflight_gate.py` (RCA 2026-05-10 + 2026-05-17 Why 5)

**Status: BUILT 2026-05-17** (ранее в Standard 0.2 §10 значился «designed not built»).

PreToolUse Bash hook `.claude/hooks/head_pin_preflight_gate.py`, зарегистрирован в `.claude/settings.json` Bash-matcher **перед** `branch_ownership_gate.py` (HEAD проверяется до ownership). Закрывает корневую причину branch-substitution (5-почему Why 5): silent HEAD-switch параллельной сессией (Cowork click / Cursor picker / Codex pack / Symphony) в shared `.git/`.

- **Механизм (zero agent cooperation):** на git-write op (`commit`/`push`/`add`/`merge`/`rebase --continue`/`cherry-pick`) auto-pin `git symbolic-ref --short HEAD` в `.claude/.head_pin_<session>`. Если между двумя write-ops в окне 6h HEAD сменился — **BLOCK exit 2** (skill-правило «abort, не autorecover»).
- **Detached HEAD** (rebase/bisect/temp worktree) — никогда не блокирует (legit state).
- **Override:** sentinel `.claude/.destructive_ack` строка `HEAD_PIN_ACK: <reason ≥10 chars> @ <iso>` fresh ≤10 min (intentional verified switch) → re-pin + PASS.
- **Tests:** 5 functional (auto-pin / same-branch / silent-switch BLOCK=2 / non-trigger / ACK-override) — все PASS 2026-05-17.

Это complement к `branch_ownership_gate.py` (тот ловит чужую *заявленную* ветку; head_pin ловит *silent switch* на ветку без claim, которую ownership пропускает).

### 4.11. EXECUTE gate — классификация ≠ выполнено (RCA 2026-05-17)

**Корневая причина:** owner steering 2026-05-17 «почему Я а не ТЫ нахожу открытые ветки/stash/worktrees?» — agent классифицировал 9 веток + 3 stale `.claude/worktrees/*` в таблицу (a)/(b)/(c), но **физически не выполнил** delete/prune. Правило branch-dropdown-hygiene (§0.0.6) и ALL-gate (§0.0.4) уже требуют «0 unclassified», но agent читал «resolve» как «classify в Run Evidence» и останавливался → owner находил clutter сам. Разрыв «анализ вместо исполнения». Добавлен **обязательный EXECUTE-блок с командами + worktree-prune (его не было в §0.0.6) + механическая end-of-session проверка**.

**EXECUTE — обязательная последовательность (классификация в таблицу = НЕ выполнено):**

```bash
# 1. для КАЖДОЙ (b)/(c) ветки: archive EXACT local tip → push (preserve до delete)
for b in <classified-b-c-branches>; do
  git tag "archive/localtip-$b-$(date +%Y%m%d)" "$(git rev-parse "$b")"
  git push origin "archive/localtip-$b-$(date +%Y%m%d)"   # точечный push тега, НЕ --tags (pre-receive policy)
done
# 2. delete: archive-tag-backed/ancestor → ban-hook carve-out; иначе sentinel
#    .claude/.destructive_ack строка `DESTRUCTIVE_GIT_BRANCH_ACK: <≥10ch reason team-recoverable> @ <iso>`
for b in <safe-branches>; do git branch -D "$b"; done   # НЕ трогать live-parallel/current
# 3. worktree prune (БЫЛО ПРОПУЩЕНО в §0.0.6 — stale .claude/worktrees/* блокируют branch -D)
git worktree list
git worktree prune
for wt in $(git worktree list --porcelain | grep '^worktree ' | awk '{print $2}' | grep '\.claude/worktrees/'); do
  git worktree remove --force "$wt"   # удаление worktree-каталога != потеря (коммиты на origin)
done
# 4. MECHANICAL re-verify (end-of-session gate) — НЕ декоративно
test "$(git for-each-ref refs/heads/ | wc -l | tr -d ' ')" -le 4 \
  && ! git worktree list --porcelain | grep -q '\.claude/worktrees/' \
  && echo "EXECUTE-gate PASS: dropdown == {main|active|infra|live-escalated}, 0 stale worktrees" \
  || echo "EXECUTE-gate FAIL — clutter remains, sync NOT done"
```

**Hard fail (RCA-инцидент):** session завершилась с branch-dropdown > {main|active|infra|live-escalated} ИЛИ ≥1 stale `.claude/worktrees/*` ИЛИ agent выписал классификацию (a)/(b)/(c) в Run Evidence БЕЗ выполнения EXECUTE-блока → `category: classify-without-execute` (owner находит clutter = разрыв «анализ != исполнение»).

**Anti-example (2026-05-17):** agent: «таблица: pr-X (a) in-main, pr-Y (b) archive, 8 stashes (b)» → Run Evidence записан → session end → owner видит 9 веток + 3 worktrees в IDE dropdown, steering «почему Я нахожу а не ТЫ».
**Corrected:** agent: классифицировал → **выполнил** archive-tip+push+`branch -D`+`worktree prune` → re-verify `git for-each-ref | wc -l <= 4` PASS → Run Evidence содержит факт «9->4, 3 worktrees removed» с командой, не только таблицу.

### 5. Output checklist после синхронизации

В отчёт в чате включить:

- [ ] Если sync пошёл по кругу, выполнен loop-breaker: RCA зафиксирован, blocker устранён до повторной попытки
- [ ] Если пользователь просил `stage all`, режим классифицирован: `local snapshot` или `publishable selective commit`
- [ ] При блоке commit по changelog: `changelog.md` обновлён и staged до повторного `git commit`
- [ ] Если `pre-push` mutates worktree: hook inspected, новые артефакты либо committed, либо использован документированный bypass
- [ ] Если push уже успешен, но дерево снова dirty: remote SHA подтверждён, residual dirty tree перечислен отдельно, повторный sync не запускался без нового explicit ask
- [ ] Ветки с `ahead_of_main>0` не были auto-merged по возрасту или префиксу; для них отдельно перечислены review/merge candidates vs cleanup/archive candidates
- [ ] Branch/worktree backlog audit выполнен (`verify_branch_hygiene.py --strict`); stale remote branches, detached worktrees и merged local branches перечислены явно
- [ ] Проверка Windows-имён выполнена (`check_windows_safe_filenames.py` — exit 0; нет символов `\ / : * ? " < > |` и нет пробела/точки в конце имён)
- [ ] **Субмодули: для каждого с `modified content` / `untracked content` выполнен коммит и пуш внутри каталога, затем обновлён ref в родителе и запушен родитель** — всё доступно команде
- [ ] При блоке коммита по размеру: один файл до 100 MB разрешён; больше — .gitignore или LFS
- [ ] При блоке по длине пути (>255 байт компонент): исключённые из коммита каталоги перечислены; решение для тиммейтов: короткие имена + INDEX в docs/ (см. §4)

### 5.2. Post-push release notes delivery (АВТОМАТИЧЕСКИ после успешного push в main)

**Цель:** Сразу после успешного `git push origin main` разослать человекочитаемую выжимку из `changelog.md [Unreleased]` в каналы, настроенные в `.agents/config/release-notes-channels.yaml` (Telegram «в юстировке», позже Slack `#dostavili-to-production`). ≤5 мин от push до release note; 0 кликов owner в мессенджерах.

**Autonomy contract:** если owner уже дал команду «синк в origin/main» / «push всё» — этот шаг выполняется автоматически, без дополнительного подтверждения. Owner получит итоговый отчёт после, не между.

**Когда запускать:**

- Сразу после `git push origin main` с exit code 0 (или push успешен, но worktree снова dirty из-за auto-snapshots — см. §3.1).
- Не запускать если:
  - `changelog.md [Unreleased]` пуст (dispatcher сам вернёт `status=nothing_to_post`);
  - push в не-main ветку (feature/fix/cursor/* — release notes идут только из main);
  - `sync-github` завершился с `status=partial` и main так и не получил commit.

**Как запускать:**

1. Вызвать субагент `release-notes-dispatcher` с промптом:
   ```
   Задача: разослать свежие записи из changelog.md [Unreleased] по
   каналам из SSOT .agents/config/release-notes-channels.yaml.
   Commit SHA: <git rev-parse --short HEAD>
   Autonomy: full — owner дал команду на sync.
   ```
2. Dispatcher читает SSOT YAML, применяет transform (care_team_ru для «в юстировке», dev_digest_ru для Slack), проходит мини-CPR, отправляет через соответствующий MCP.
3. В отчёт sync-flow включается блок «Release notes dispatched» с таблицей `канал / transform / длина / статус`.

**Graceful degradation:**

- Если Telegram MCP недоступен → помечаем `Telegram: skipped (MCP down)`, остальной sync завершается успешно.
- Если Slack MCP не установлен → канал `slack_dostavili_to_production` в SSOT имеет `enabled: false` или dispatcher вернёт `status=not_configured_gracefully`. Это не блокирует push.
- Если мини-CPR нашёл gap в сообщении → dispatcher не отправляет, возвращает draft + gap list. Sync считается успешным (push прошёл), release note остаётся draft для ручного review.

**Hard fail (RCA-заметка в `ai.incidents.md`):**

- Push в main завершён успешно, changelog `[Unreleased]` не пуст, но dispatcher не был вызван → `category: release-notes-dispatch-skipped`.
- Dispatcher вызван, но сообщение отправлено без мини-CPR → `category: cpr-gate-bypassed`.

**Связанные артефакты:**

- SSOT каналов — `.agents/config/release-notes-channels.yaml`
- Субагент — `.agents/agents/release-notes-dispatcher.md`
- Skill — `.agents/skills/0-changelog-release-notes/SKILL.md` §5.1 Channel routing

### 5.1. Post-commit completeness gate (ОБЯЗАТЕЛЬНО)

После каждого `git commit` в sync-flow **обязательно** выполнить:

1. `git status --porcelain` — вывести все оставшиеся dirty файлы.
2. Если вывод не пуст:
   - Классифицировать каждый dirty файл по таблице §0.1 (скрипт, runtime, backup, легитимный, embedded repo, submodule).
   - Для каждого файла: `include в следующий commit` / `exclude с обоснованием` / `add to .gitignore`.
   - Если есть файлы `include` — сделать ещё один `git add` + `git commit` в том же sync pass.
3. Повторять пока `git status --porcelain` не вернёт пустой вывод **или** все residuals имеют явное `exclude` с обоснованием.
4. **Запрещено:** писать `sync complete` / `confirmed` пока gate не пройден.
5. **Запрещено:** писать `sync complete` / `confirmed` без owner-facing telemetry line из §0.0.5a: current duration + p50/p95 + blockers + delivered_without_qa.
6. **Запрещено:** спрашивать owner подтверждение для каждой волны — если owner уже дал команду «синк всё в origin/main», агент выполняет полный sync автономно, показывая итоговый отчёт **после** завершения.

## Script Reference

- **Скрипт проверки имён:** `<internal-module>/scripts/check_windows_safe_filenames.py`
  - Запуск: из корня репо `python3 <internal-module>/scripts/check_windows_safe_filenames.py`
  - Проверяет: trailing space/dot и символы `\ / : * ? " < > |` (запрещённые в Windows)
  - Опция `--fix`: переименовать найденные имена (`:` → `-`, `|` → ` - ` и т.д.); после — снова запустить без `--fix` до exit 0
- **Pre-commit (длина пути):** `.githooks/pre-commit` — проверяет каждый компонент пути на ≤255 байт (UTF-8). При превышении коммит блокируется; см. §4 для решения (короткие имена в docs/ + INDEX).
- **Проверка длинных путей по дереву:** `python3 <internal-module>/scripts/check_windows_safe_filenames.py --check-path-length` — сканирует репо и выводит все пути с компонентом >255 байт; exit 1 при наличии таких путей. Не переименовывает (длинные имена исправляются переэкспортом в короткие + INDEX).
- **Единый contract guard:** `python3 <internal-module>/scripts/verify_sync_github_contract.py --strict --tracked-only` — проверяет skill symlinks, tracked checkout safety, case collisions и при локальном publish может дополнительно требовать clean root main.
- **Branch/worktree hygiene guard:** `python3 <internal-module>/scripts/verify_branch_hygiene.py --strict` — строит audit по local branches, detached worktrees и stale remote integration branches; broken refs/worktrees = error, backlog = warning/report surface.
- **Команда синхронизации:** `.cursor/commands/sync-github.md` (полный протокол `/sync-github`)

## JTBD, Jobs To Be Done — задача, которую решает клиент

**Когда** команда хочет выгрузить репозиторий в GitHub и не сломать клон у Windows-пользователей, **использует** этот чеклист (и при необходимости скрипт проверки имён), **чтобы** перед `git add` устранить небезопасные имена и явно отчитаться по субмодулям.


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/` → duckdb). Узел «свернул не туда»: `scripts/reasoning_log/graph.py --find-divergence`. Ручная markdown-таблица в чат — только если owner явно спросил «почему ты так решил». Полный протокол: `agent-reasoning-log/SKILL.md` (v2, RCA 2026-05-17).


## V1.0 framework — sync branch to main без потерь (RCA 2026-05-23 case study)

ОБЯЗАТЕЛЬНО когда ветка >50 commits ahead AND/OR >20 behind main, PR обозначен CONFLICTING либо требует careful merge без revert интегрированной работы.

### 8 классов проблем в безопасном порядке (operational playbook)

| # | Class | Symptom (что видит owner) | JTBD (когда → хочу → чтобы) | Solution | Verify (authoritative) | Time |
|---|---|---|---|---|---|---|
| 0 | Diagnostics | proactive, нет симптома | факты до плана — план на доказательствах | git rev-list left-right count vs origin/main; gh pr list; status porcelain count | числа фиксируют ahead/behind/dirty | 2 мин |
| 1 | Pre-commit validator FAIL | FAIL E09/E10 в validate_agent_skills | когда validator стопит → хочу root-fix маппинги — чтобы прошёл без bypass | add to AGENT_ROLES; add Credentials line per Std 4.8 §B C13 | validator FAIL count = 0 | 5 мин |
| 2 | Bloat-категория в branch (>100MB regenerable) | inventory script показывает >100MB cluster | когда archive/runtime в branch — хочу untrack без удаления — чтобы main не вырос | gitignore add path; rm cached -r quiet path | ls-tree origin/main path = 0; локально find >0 | 3 мин |
| 3 | Накопленная работа не закоммичена | 100+ dirty entries from many sessions | когда уйма uncommitted — хочу не потерять — команда получает всё | stage-all then unstage DENY-list (sacred/runtime/personal) then commit | catastrophe-guard: staged-as-deleted count = 0 for ADD-only | 5 мин |
| 4 | Branch behind main → PR CONFLICTING | GitHub UI красный «CONFLICTING» | когда N behind — хочу примирить divergence без revert — чтобы PR mergeable | clean worktree off branch tip; merge --no-commit --no-ff origin/main; count conflicts | conflict count <60 fix locally / >=60 escalate GitHub UI | 5-10 мин |
| 5 | Per-file conflict resolution | 1-60 файлов с конфликт-markers | когда overlapping changes — хочу осознанный per-file выбор — чтобы ничего ценного не потерять | per-category: theirs для workspace canonicals (main integrated); ours для client/project work | diff-filter U = 0; merge committed | 10-30 мин |
| 6 | Push merged branch | после resolve | local-only → team-reachable mergeable PR | push origin HEAD branch — НИКОГДА force | gh pr view mergeable = MERGEABLE | 1 мин |
| 7 | Final merge PR → main | PR mergeable | когда PR MERGEABLE — команда получает всё через main | gh pr merge N merge; fallback admin merge для UNSTABLE billing-CI | gh pr view state = MERGED + cat-file sample ✓ | 1 мин |

### Anti-patterns (что НЕ делать — case study RCA 2026-05-19 → 2026-05-23)

| Anti-pattern | Почему failed в этой сессии | Что делать вместо |
|---|---|---|
| worktree add --no-checkout для commit-building | Empty index → commit записывает ТОЛЬКО staged files → merge wipes ВСЁ (PR #108: 27,772 files / 55M line removals) | Full-checkout worktree (~60-90с цена за safety) |
| Elaborate Python orchestration scripts для merge | Auditor: 1 BLOCKING + 10 HIGH bugs; silent failures на subprocess | Direct git commands видимые owner'у |
| Background subagent delegation без verify-after | Notifications не переживают session-resume; «launched» ≠ «done» | Authoritative state check каждый шаг (gh pr view state + cat-file) |
| Claim «всё в origin» когда только в branch | branch в origin ≠ main; team git pull origin main не получает branches | Уточнять team-reachable via main |
| Mass-commit без deletion-sanity | PR #108 catastrophe class | Pre-commit: staged-deleted file count = 0 для ADD-only operations |
| Direct merge branch→main когда branch behind | Может revert интегрированную работу (stale-base) | Merge main INTO branch first; resolve conflicts на branch side; затем ff |
| Force push | Уничтожает чужие commits | force-with-lease ТОЛЬКО на свой ref + ACK; иначе никогда |
| Удаление ветки после merge | Owner: DELETE NOTHING | gh pr close без delete-branch; ветка живёт |

### JTBD mapping (3-level Bruce)

| Уровень | JTBD | Steps closing |
|---|---|---|
| Big | менеджер видит open PR от агентов — хочет team получает всё через git pull origin main — чтобы все пользовались | 0→7 целиком |
| Medium-preserve | сохранить накопленную работу не потеряв sacred — reset не уничтожит | 1, 2, 3 |
| Medium-conflict | PR CONFLICTING — осознанный per-file выбор — main canonical И branch work оба сохранились | 4, 5 |
| Medium-deliver | branch ff-mergeable — довести в main — команда реально получает | 6, 7 |

### Mechanical enforcement

- pre_push_deletion_guard.py (.claude/hooks/, registered via scripts/setup/hooks-registry.json) — abort push если commit removes >=100 files unexpectedly. Override: GIT_PUSH_DELETION_ACK env >=10 chars. Closes #108-класс mechanically.
- auto_commit_on_stop.py (existing) — capture all uncommitted на Stop с DENY-list reset. Safety net для step 3.

### Case study refs

PR #108 (catastrophe rescued via #109 revert) → PR #110 (consolidate) → PR #111 (final merge всех агентов в main, 12,170 net files) → PR #113 (script B1 tempfile fix) → PR #114 (admin bloat cleanup).


## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Heroes/Rick (включая TaskMaster и связанные стандарты Heroes Rickai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.


---

## Skill contract (Standard 4.8 §B)

### Hired for JTBD

Когда нужен полный sync репозитория в origin/main без потерь, ты как owner/teammate хочешь чтобы все ветки/stash/worktree были классифицированы и доведены, чтобы команда git pull получила полную версию.

### Workflow

1. Sit-down dirty-tree triage (§0.0) -> 2. Universal Project-State Router (§0.0.4) -> 3. Nothing-lost (a)/(b)/(c) (§0.0.6) -> 4. io-checklist render (§4.9) -> 5. EXECUTE-gate archive-tip->branch -D->worktree prune->re-verify (§4.11) -> 6. push/PR -> 7. release-notes (§5.2).

### Input checklist

- [ ] git status/porcelain, gh-api PR state, branch+stash+worktree inventory, submodules-registry.yaml

### Output checklist

- [ ] 0 open PR (gh-api), branch-dropdown == main|active|infra, archive-теги на origin для (b)/(c), 0 stale worktrees

### Outcome checklist (owner benefit)

- [ ] owner перестаёт быть QA git-состояния — команда git pull origin main получает полную функциональную версию, ничего уникального не потеряно

### Owner value

owner value: ноль ручного разбора почему куча веток / чей коммит / что потеряно — sync доводится агентом до clean state, не классифицируется в таблицу

### Self-falsification gate

После исполнения скилл обязан прогнать гипотезу «этот скилл закрыл свой JTBD» через [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md): gap table Ожидание | Факт | Δ, verdict confirmed | partial | falsified. При partial/falsified — новая рабочая гипотеза, не закрывать как done.

### Reasoning Log Protocol

Каждое исполнение ведёт reasoning log в чате (решения + evidence + gap + blocking instruction) и строку в `<internal-folder>/ai.incidents.md` §Append-only trace. Hard fail: без reasoning log скилл не исполнен. Канон — `agent-reasoning-log` в AGENTS.md.

### Связанные скилы / Related skills

- [`2-hypothesis-gap-falsification`](../2-hypothesis-gap-falsification/SKILL.md) — self-falsification gate
- [`5-sync-github-checklist`](../5-sync-github-checklist/SKILL.md) — общий sync ритуал + io-checklist макрос §4.9
- `agent-reasoning-log` — обязательный reasoning log протокол (AGENTS.md)
