---
name: portable-claude-hooks
description: "Use BEFORE editing .claude/settings.json or .codex/hooks.json hook commands, when adding a new .agents/hooks/* hook, or when a teammate reports Bash/Edit/Write/UserPrompt blocked after git pull / 'hook path not found' on another Mac, Windows, Claude, or Codex. Enforces zero absolute/direct hook paths via the portable launcher + verify_hook_portability.py. Triggers: 'хуки не работают у команды', 'абсолютный путь в settings.json', 'portable hooks', 'add a hook', 'settings.json для всех', 'hook path not found на другой машине'."
paths:
  - .agents/hooks/**
  - .claude/settings.json
  - .codex/hooks.json
---

**Mode:** [PASSIVE]

# Portable hooks (Claude/Codex, cross-platform team)

## Hired for Jobs To Be Done

Когда тиммейт (другой Mac с другим `$HOME`, Windows, Claude Code или Codex) делает `git pull` и открывает сессию → owner получает рабочие governance-хуки **без** ручной правки путей под себя, `sed`-патчей `settings.json`/`hooks.json` или удаления файла; `Bash/Edit/Write/UserPrompt` не блокируются чужим абсолютным путём.

## Overview

`.claude/settings.json` и `.codex/hooks.json` — **git-tracked** и общие для всей команды. Любая хук-команда с абсолютным машинным путём (`/Users/<кто-то>/.../.codex/hooks/X.py`, `C:\Users\...`) или direct `$CLAUDE_PROJECT_DIR/.claude/hooks/X.py` ломает hook layer при пустом env / другом CLI → инструменты или owner prompt блокируются.

Канон: командные строки несут **ноль** абсолютных/direct hook путей. Project root резолвится launcher'ом через `CODEX_PROJECT_DIR` → `CLAUDE_PROJECT_DIR` → script-relative → `PWD`; интерпретатор python резолвится `python3`→`python`→`py`.

SSOT-механизм:
- `.agents/hooks/run` (POSIX sh) + `.agents/hooks/run.cmd` (Windows) — портативный launcher; `.claude/hooks` и `.codex/hooks` только aliases; fail-open но **громкий** (stderr), `PORTABLE_HOOK_FAILMODE=closed` → exit 2.
- `.agents/hooks/verify_hook_portability.py` — scan (`--check`, exit 2) / авто-починка (`--fix`, идемпотентно) / SessionStart (`--warn`, exit 0) / `--quiet`.
- `heroes_platform/tests/test_hook_portability.py` — регрессия (stdlib unittest, без pytest-deps).

## When to Use

- **Перед** Edit/Write в `.claude/settings.json` или `.codex/hooks.json` (особенно блок `hooks`).
- При добавлении нового `.agents/hooks/<name>.py` или `<name>.sh` — его регистрация обязана идти через launcher, не через absolute/direct путь.
- Когда тиммейт сообщает «после git pull всё заблокировано» / «hook path not found» / «работает у тебя, не работает у меня».

## Workflow

1. Найти все затронутые hook command-строки в `.claude/settings.json`, `.codex/hooks.json`, `heroes_harness/scripts/setup/hooks-registry.json` или target mirror output.
2. Переписать direct/absolute вызовы на portable launcher `.agents/hooks/run`.
3. Прогнать `python3 .agents/hooks/verify_hook_portability.py --fix`, затем `--check`.
4. Прогнать регрессию `python3 heroes_platform/tests/test_hook_portability.py`.
5. Если менялся mirror/register/bootstrap слой, прогнать соответствующие tests и `verify_harness_wiring.py --smoke`.
6. Перед delivery проверить хотя бы один distributed target или fixture, где `CODEX_PROJECT_DIR` есть, а `CLAUDE_PROJECT_DIR` пустой.

## Procedure (типовое действие — всё через скрипт, не вручную)

1. **Никогда** не писать в command абсолютный путь. Канонические формы:
   - python-хук: `sh "${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}/.agents/hooks/run" <hook>.py [args]`
   - repo-относительный скрипт (нужен cwd=root): `sh "${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}/.agents/hooks/run" --root <rel/path>.py [args]`
   - shell-хук: `sh "${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}/.agents/hooks/run" --sh <hook>.sh [args]`
   - чистый inline-shell без python: `cd "$CLAUDE_PROJECT_DIR" && <команда>`
2. После любой правки `settings.json` прогнать починку (идемпотентно):
   `python3 .agents/hooks/verify_hook_portability.py --fix`
3. Проверить, что чисто (должно быть exit 0, `PASS`):
   `python3 .agents/hooks/verify_hook_portability.py --check`
4. Прогнать регрессию: `python3 -m unittest heroes_platform.tests.test_hook_portability`
5. Коммитить `settings.json` обычным `git commit` — lefthook `hook-portability` сам заблокирует, если абсолютный путь просочился.

Регрессия ловится тремя слоями: pre-commit (block) → SessionStart (warn после чужого pull) → `make bootstrap` (`--fix` self-heal на свежем clone).

## Self-falsification gate

Проверяемое утверждение: «tracked hook config не ломает Claude/Codex на другой машине».

| Expectation ID | Что должно быть истинно | Где подтверждается | Next action if unmet | усилие человека (0–100) | Actor |
|---|---|---|---|---:|---|
| E01 — нет абсолютных/direct hook путей | `verify_hook_portability.py --check` возвращает `PASS` | stdout + exit 0 | запустить `--fix`, проверить diff, повторить `--check` | 0 | agent |
| E02 — Codex root работает без Claude env | launcher использует `CODEX_PROJECT_DIR` и не требует `.claude/hooks` | `test_codex_env_resolves_root_when_claude_env_unset` | чинить `.agents/hooks/run` / `run.cmd` | 0 | agent |
| E03 — mirror не создаёт dangling commands | partial profile не wires missing hook files | `heroes_harness/scripts/tests/test_register_hooks_partial_profile.py` | чинить `register_hooks.py` file-ref parser | 0 | agent |
| E04 — target harness wired | `verify_harness_wiring.py --repo-root <target> --smoke` даёт `0 GAP` | target verifier output | докопировать manifest deps / aliases / settings | 0 | agent |

Verdict `confirmed` допустим только если E01-E04 подтверждены на текущем diff. Если хотя бы один пункт не проверен, итоговый verdict = `partial`, а delivery обязан назвать непроверенный слой.

## Input / Output / Outcome checklist

### Input checklist
| ✓ | Что на входе | Факт |
|---|---|---|
| ✅ | список изменённых hook configs/scripts | `git diff --name-only` |
| ✅ | canonical launcher | `.agents/hooks/run`, `.agents/hooks/run.cmd` |
| ✅ | verifier | `.agents/hooks/verify_hook_portability.py` |

### Output checklist
| ✓ | Что на выходе | Факт |
|---|---|---|
| ✅ | portable hook commands | `verify_hook_portability.py --check` PASS |
| ✅ | regression tests | `heroes_platform/tests/test_hook_portability.py` PASS |
| ✅ | distributed target sanity | mirror/verifier output with `gaps==0` |

### Outcome checklist
| ✓ | Какая выгода owner | Факт / как проверено |
|---|---|---|
| ✅ | Codex/Claude больше не блокируют prompt/tool из-за чужого path | no direct/absolute hook commands |
| ✅ | новый target получает self-healing hook setup | mirror writes `.codex/hooks.json` + aliases + bootstrap |
| ✅ | будущая регрессия ловится до merge | pre-commit + tests + SessionStart warn |

## Reasoning Log Protocol

В Reasoning Log фиксировать: (1) какие command-строки `settings.json` затронуты; (2) результат `verify_hook_portability.py --check` (exit code + PASS/FAIL + список нарушений дословно); (3) что launcher зарезолвил при smoke (`$CLAUDE_PROJECT_DIR` set vs относительный fallback) + результат unittest. Запрещено писать «хуки портативны» без вывода `--check`.

## Hard fail / Запрещено

- Запрещено коммитить `.claude/settings.json` / `.codex/hooks.json` с абсолютным путём (`/Users/`, `/home/`, `/root/`, `C:\`) или direct hook invocation (`python3 $CLAUDE_PROJECT_DIR/.claude/hooks/X.py`) → portability gate блокирует; обход через `--no-verify` = RCA `category: portable-hooks-bypassed`.
- Запрещено заявлять «работает у всех в команде» без `verify_hook_portability.py --check` exit 0 + unittest PASS в Run Evidence.
- Запрещено «починю в отдельной сессии» — это прямой §Always-green main invariant (committed config ломает прод тиммейтов).

## Owner value

Owner value: тиммейт после `git clone && git pull` получает рабочую governance-обвязку за 0 кликов (раньше — ручной `sed`/удаление `settings.json` ≈ 50+ усилия и потеря всех гейтов). Регрессия невозможна без явного `--no-verify` bypass. Value tracking: count steering «хуки не работают у X» в `ai.incidents.md` → target 0 после внедрения.

## Связанные скилы / Related skills

- `.agents/skills/5-git-parallel-coordination/SKILL.md` — общий git-протокол (worktree, incremental commits).
- `.agents/skills/0-claude-code-mcp-sync/SKILL.md` — синхронизация Claude Code конфигов между средами.
- `.agents/skills/5-sync-github-checklist/SKILL.md` — push/PR ритуал.
- AGENTS.md §Portable hooks invariant (cross-platform team) — нормативный инвариант, этот скил — его процедура.
