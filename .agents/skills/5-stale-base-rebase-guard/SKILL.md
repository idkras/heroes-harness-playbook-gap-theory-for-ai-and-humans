---
name: 5-stale-base-rebase-guard
description: "Use BEFORE открытия PR ИЛИ при подозрении что worktree/branch создан давно (>2-3 часа long-running). Detects когда origin/main ушёл вперёд после создания твоей branch и diff PR начинает показывать integrated mainline work как 'deletions' (классический stale-base false-negative класс §Nothing-lost invariant). Запускает scripts/check_pr_stale_base.sh — детектит drift ≥N коммитов behind + список файлов которые попадут в 'deletions' diff. Поддерживает --auto-rebase для тривиальных случаев. Универсальный — без client/project hardcode. Триггеры: «прогон stale-base check», «сделай PR — проверь base», «PR diff показывает deletions», «нужен ли rebase», «origin/main behind check», «long-running worktree refresh»."
mode: ACTIVE
requires:
  - 5-git-parallel-coordination
on_demand:
  - 0-main-cleanliness-guard
  - 5-sync-github-checklist
---

# 5-stale-base-rebase-guard — типовое действие проверки stale base перед PR

**Версия:** 1.0
**Создан:** 24 мая 2026
**Mode:** [ACTIVE] — обязательный вызов перед `gh pr create` или перед `git push` на новой ветке, если worktree существует >2-3 часа.
**RCA-источник:** 2026-05-24 PR #119 — worktree создан от `origin/main 5a5c40f97`, main за это время ушёл +63 коммитов вперёд через 8 merges (PR #114-120). Diff PR vs `origin/main` показал 5 файлов как «deleted»: `pre_push_deletion_guard.py` + V1.x секции 3 sibling skills + `consolidate_branches.py`. Manager-аудитор субагент флагнул 💀 catastrophic verdict до того как rebase раскрыл root cause (stale base, не реальная регрессия).

## JTBD

**Когда** агент работает в worktree/branch созданном давно (>2-3 часа), и собирается открыть PR / push к удалённому remote — **owner хочет**, чтобы агент **сначала** проверил drift между HEAD и `origin/main`, потому что иначе PR diff может показать integrated mainline work (от других teammate) как «deletions» — это вызывает false 💀 verdict от auditor'ов и заставляет owner делать lengthy investigation вместо тривиального `git rebase origin/main`.

## Триггеры активации (ОБЯЗАТЕЛЬНО)

1. Перед `gh pr create` на любой ветке (universal — любой PR).
2. Перед `git push -u origin <branch>` если worktree создан >2 часа назад.
3. Когда auditor / cleanup-guardian / любой review-субагент возвращает verdict «удалено N файлов» / «scope drift» / «потеря работы» — ПЕРВЫЙ шаг: проверить не stale-base ли это.
4. При длительной (>3h) session работы в одном worktree без `git fetch origin main` — periodic refetch. **MECHANICAL ENFORCEMENT v1.1 (RCA 2026-05-26):** триггер теперь fires автоматически через PreToolUse hook `.claude/hooks/work_time_state_drift_guard.py` (`Write|Edit|NotebookEdit|Bash` matcher). Hook проверяет (a) behind origin/main > 100 commits = BLOCK / >30 = WARN; (b) FETCH_HEAD age > 24h = BLOCK / >3h = WARN; (c) MERGE_HEAD age > 60 min = BLOCK на non-resolve ops. Skip-list для merge resolve ops (`git merge --abort/--continue`, `git status/diff/add/commit`). Override: `WORKTIME_STATE_DRIFT_ACK=<reason 12+chars>` env. Этот trigger больше не judgment-based — wired в state-driven mechanical layer per AGENTS.md §Work-time state drift gate.
5. Ручной запрос: «прогон stale-base check», «нужен ли rebase», «PR diff показывает deletions».

## Каноническая база

| Документ | Что покрывает |
|---|---|
| AGENTS.md §Nothing-lost invariant | DoD для «не потерять чужую работу» |
| AGENTS.md §Always-green main invariant | принцип «всегда работающий прод» |
| `5-git-parallel-coordination/SKILL.md` | general git workflow для parallel work |
| `0-main-cleanliness-guard/SKILL.md` | hygiene perspectives |
| `5-sync-github-checklist/SKILL.md` | sync ритуал |
| `scripts/check_pr_stale_base.sh` | универсальный скрипт детекции (без hardcode) |

## Workflow

### Шаг 1 — Запустить проверку

```bash
bash .agents/skills/5-stale-base-rebase-guard/scripts/check_pr_stale_base.sh
```

Output:
- `branch=<X> ahead=<N> behind=<M> threshold=5` — текущие counts
- `✅ OK — base is fresh` если behind < threshold
- `🚩 STALE BASE detected — origin/main moved <M> commits ahead` если behind ≥ threshold + список drift files

Exit code: `0` = OK, `1` = stale (для CI/skript integration).

### Шаг 2 — Решить что делать

| Situation | Decision |
|---|---|
| `✅ OK` (behind < 5) | Continue — open PR / push спокойно |
| `🚩 STALE` + tree clean | `git rebase origin/main` + `git push --force-with-lease` |
| `🚩 STALE` + tree dirty | (a) `git stash push -u -m wip` (b) rebase (c) `git stash pop` |
| `🚩 STALE` + uncommitted critical .py/.md | сначала commit того что не потерять, потом rebase |
| Rebase conflict | resolve manually, `git add`, `git rebase --continue` |

### Шаг 3 — Verify after rebase

```bash
# Re-check после rebase
bash .agents/skills/5-stale-base-rebase-guard/scripts/check_pr_stale_base.sh
# Должен показать ahead=N behind=0
# Verify drift files restored:
git diff --name-only --diff-filter=D origin/main..HEAD | head -10
# Should be empty — если есть файлы, это реальные deletions (intentional)
```

### Шаг 4 — Не auto-rebase под --auto-rebase без owner go

`--auto-rebase` флаг **запрещён** для PR'ов которые уже опубликованы и review (force-push меняет SHA → нарушает reviewer context). Использовать только для local-only веток до первого `git push`.

## Hard fail

- Открыл PR без prior stale-base check → если manager-аудитор флагнет 💀 → RCA `category: stale-base-pr-without-check`.
- Закоммитил «нет чужой работы потеряно» в PR description когда behind ≥ 5 без проверки → RCA `category: nothing-lost-false-claim` (повтор RCA 2026-05-16).
- Auto-rebase на published PR без owner go → RCA `category: published-pr-force-push-without-go`.

## Input / Output / Outcome checklist

**Input:** активная git branch + доступ к `origin/main` (fetch не offline).
**Output:** verdict OK/STALE + counts ahead/behind + список drift files (если STALE) + recommended action.
**Outcome (owner value):** auditor не флагает 💀 catastrophic verdict из-за stale-base false-positive; owner не тратит время на investigation того что fixable одним `git rebase`; chain «open PR → real review» не загрязнён mainline drift noise; **ценность для owner**: -30-60 мин per false-positive auditor verdict + restored trust в auditor feedback.

## Self-falsification gate

После выдачи verdict скилл прогоняет гипотезу через `2-hypothesis-gap-falsification` §2.5 — find counter-example: «behind=0 но drift files существуют» (возможно branch ahead of main on different basis) или «behind=N но drift files all my own» (false-positive — это не чужая работа). Если counter-example ≥2 раз за 14 дней — re-calibration threshold ИЛИ дополнительный context-check к script.

## Связанные скилы

- `5-git-parallel-coordination` — родительский general git workflow
- `5-sync-github-checklist` — push/PR ритуал
- `0-main-cleanliness-guard` — main hygiene
- AGENTS.md §Nothing-lost invariant — DoD контракт «не потерять чужую работу»

---

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф. Ручная markdown-таблица в чат — только если owner явно спросил «почему ты так решил». Полный протокол: `agent-reasoning-log/SKILL.md`.

---

## Авторство

Скил создан Ильёй Красинским 2026-05-24 на основе RCA «stale base detected as deletions» (PR #119). Поддерживается как часть `.agents/skills/` универсальной системы навыков.
