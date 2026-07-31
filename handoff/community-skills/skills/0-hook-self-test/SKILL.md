---
name: 0-hook-self-test
description: "Use when adding or modifying any .claude/hooks/*.py hook. Enforces eval-first contract per Claude Skills 2.0 — каждый hook обязан иметь fixtures в heroes_harness/scripts/tests/test_hooks_smoke.py покрывающие pass/block/override cases. Триггеры: «добавить hook», «новый hook», «модифицирую hook», «hook не работает», «hook false-positive», «hook overreach», «hook лежит test»."
paths:
  - .claude/hooks/**
---

**Credentials:** см. AGENTS.md §Credentials SSOT и скиллы `0-credentials-manager` + `0-keychain-audit`. Hooks могут вызывать `bd`, `git`, или внешние команды — credentials через `heroes_platform.credentials`.

# Когда добавляю или меняю Claude Code hook, хотим runtime-verified что hook ловит violations и не блокирует legitimate work (0-hook-self-test)

## Hired for JTBD

Когда agent / тиммейт добавляет или меняет hook в `.claude/hooks/*.py`, хочет mechanical guarantee что hook ловит true violations (pass/block cases tested) и не блокирует legitimate work (false-positive cases tested) и respects override env vars — без падения owner в session-time на rephrase 5×. Этот навык нанимается на работу: **каждый hook = unit под test, eval-first**.

## Назначение

Один skill для **дисциплины hook authorship**: перед commit нового или изменённого hook агент обязан добавить ≥4 fixture cases в `heroes_harness/scripts/tests/test_hooks_smoke.py` покрывающие минимум: (a) pass case (legitimate work), (b) block case (true violation), (c) override-ack pass, (d) fail-open malformed payload. Lefthook pre-commit job `hook-smoke-tests` BLOCK commit если test harness fail.

**Принцип Claude Skills 2.0:** evals enforce behavior. Hook без passing fixtures = декларативный, не mechanical.

**Based on:** Claude Skills 2.0 §«evals», AGENTS.md §«Always-green main invariant», RCA 2026-05-24 (ASSISTANT_LOOKBACK overreach — 5 false-positive blocks в одной сессии, root cause = hook без runtime fixtures на autonomous Ralph loop scenario).

## When to Use

- Создаю новый `.claude/hooks/*.py` hook
- Меняю constants / regex / logic existing hook (даже 1 строка)
- Hook false-positive в ходе сессии (≥2 blocks) — добавить regression fixture
- Изменение `.claude/settings.json` matcher pattern для hook

## Workflow

1. **Input checklist:** имя hook, его JTBD (что блокирует / warn-ит), все trigger conditions (matcher + payload patterns), override env var name.
2. **Implement hook** в `.claude/hooks/{name}.py` — stdlib-only Python, fail-open на malformed payload, structured stderr с recovery hint.
3. **Add ≥4 fixture cases** в `heroes_harness/scripts/tests/test_hooks_smoke.py` `TEST_CASES` list:
   - **Pass case** — legitimate work проходит exit 0
   - **Block / Warn case** — true violation exit 2 (block mode) или exit 0 + stderr (warn mode)
   - **Override-ack pass** — env var с ≥12 chars reason → exit 0 + stderr warning
   - **Fail-open malformed payload** — empty dict / missing keys → exit 0 (no crash)
   - **(Optional) Edge cases:** non-matching tool_name skip, allowlist patterns, regex edge
4. **Run** `python3 heroes_harness/scripts/tests/test_hooks_smoke.py --hook {name}` локально — все cases PASS.
5. **Wire** hook в `.claude/settings.json` правильный matcher (`Write|Edit|NotebookEdit` / `Bash` / `mcp__*` / etc.) через `${CLAUDE_PROJECT_DIR}/.venv/bin/python ${CLAUDE_PROJECT_DIR}/.claude/hooks/{name}.py` (portable form per §Portable hooks invariant).
6. **Commit** — lefthook pre-commit job `hook-smoke-tests` автоматически gate'ит.
7. **Output checklist:** hook file + fixtures + settings.json wire-up + lefthook job activated + smoke test green.
8. **Outcome checklist / owner value:** hooks больше не блокируют legitimate autonomous Ralph loop работу false-positive — owner не теряет turn time на rephrase. Это **прямой owner benefit** (мера: hook false-positive count в session goes 0).

## Self-falsification gate

После добавления hook прогнать гипотезу «hook ловит true violations и пропускает legitimate work» через [`2-hypothesis-gap-falsification`](mdc:.agents/skills/2-hypothesis-gap-falsification/SKILL.md):

- **Expectation:** N fixture cases — N/N PASS (зелёные)
- **Reality:** runtime `python3 heroes_harness/scripts/tests/test_hooks_smoke.py --hook {name}` output
- **Gap:** any FAIL → исправить hook ИЛИ fixture (hook ≠ fixture mismatch = real bug somewhere)

## Forbidden

- ❌ Commit hook без fixture в `test_hooks_smoke.py` — `category: hook-without-eval`
- ❌ Bypass lefthook через `--no-verify` для прохождения broken hook tests — `category: hook-bypass-attempt`
- ❌ Hook без override env var (нет escape hatch для emergency / legitimate exception) — `category: hook-no-override`
- ❌ Hook BLOCK mode без 2-week WARN-mode telemetry (no adoption data) — `category: hook-block-without-telemetry`

## Required

- ✅ ≥4 fixture cases (pass / block / override / malformed)
- ✅ Portable form `${CLAUDE_PROJECT_DIR}/...` в settings.json
- ✅ Override env var documented в hook stderr message
- ✅ Phase 1 (WARN) → Phase 2 (BLOCK) для new hooks с adoption risk
- ✅ Cross-link на canonical RCA / Standard в hook docstring

## Hard fail категории

- `hook-without-eval` — commit hook без fixtures
- `hook-bypass-attempt` — `--no-verify` для обхода broken tests
- `hook-no-override` — hard BLOCK без escape hatch
- `hook-block-without-telemetry` — Phase 2 BLOCK без WARN telemetry baseline

## Related

- `2-hypothesis-gap-falsification` — falsification protocol для hook expectation vs reality
- `0-portable-claude-hooks` — `${CLAUDE_PROJECT_DIR}` form для settings.json
- `5-git-parallel-coordination` V1.2 — branch_name_bead_ref_check.py example

## Канонические источники

- `heroes_harness/scripts/tests/test_hooks_smoke.py` — universal test harness (TEST_CASES list)
- `lefthook.yml` pre-commit job `hook-smoke-tests` — mechanical enforcement
- `.claude/hooks/branch_name_bead_ref_check.py` — reference implementation (9 fixture cases)
- Claude Skills 2.0 docs — eval-first contract: <https://docs.claude.com/en/docs/agents-and-tools/skills>

---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`).

## Reasoning Log Protocol

Reasoning Log v2 — авто-захват из транскрипта в граф (`.reasoning-log/spans/` → duckdb). Полный протокол: `agent-reasoning-log/SKILL.md`.

## Связанные скилы

- **agent-reasoning-log** — см. AGENTS.md
- **owner-prompt-capture** — см. AGENTS.md

---

## Авторство

Скил создан в Ralph loop сессии 2026-05-24 (Ilya Krasinsky owner) для закрытия recurring class «hook overreach без runtime test discipline». RCA-источник — bead `pr-rick-4eh` (C1 JTBD validator) + auditor verdict 2026-05-24 → L4.5 hook lookback fix → этот skill systematizes practice.
