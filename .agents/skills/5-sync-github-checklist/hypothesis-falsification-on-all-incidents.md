# Hypothesis Falsification — v3 sync architecture vs ALL 14 known sync incidents

**Hypothesis (H):** v3 sync skill (§0.0.0 sit-down triage + §0.0.4 Project-State Router + §0.0.5 Subagent Chain + §0.0.5a QA-3 verdict + §0.0.6 «Nothing Lost» L1-L6 + §0.0.7 @auto integration + §0.0.8 Recovery Playbook F1-F7) **prevents all 14 inventoried sync RCA incidents from `<internal-folder>/ai.incidents.md`** when applied as mandatory pre-flight.

**Falsification method:** для каждого инцидента восстановить sequence событий, проверить какой v3 section (если есть) **остановил бы** этот sequence на каком шаге. Verdict per incident: `confirmed` (v3 blocks at step X) / `partial` (v3 reduces probability but doesn't block) / `falsified` (v3 doesn't address class).

## Master falsification table

| # | Incident | Date | Root cause class | v3 section that blocks | Block step | Verdict | Residual risk |
|---|---|---|---|---|---|---|---|
| I14 | git clean -fd parallel-session <internal-component> | 2026-05-14 | RC-A | §0.0.6 L6 + hook `pre_git_clean_parallel_check.py` | Layer C JSONL grep returns match → exit 2 BLOCK | **confirmed** (mechanical) | `L6_ACK` bypass + heuristic mtime threshold misses fast-write parallel session (rare) |
| I13 | .githooks/* broken shell syntax → checkout fails | 2026-05-10 | RC-E | §0.0.6 L2 untracked scan reveals modified .githooks/*; pre-flight `bash -n .githooks/*` syntax check | Step 2 syntax check fails → STOP before checkout | **partial** | v3 не имеет explicit `bash -n` step yet; relies on agent intuition |
| I12 | Rick.ai Tests misreported sync readiness (stale evidence) | 2026-04-03 | RC-B | §0.0.4 State C/E + post-fetch invalidate stale evidence | State router triggers fresh inventory pre-test | **partial** | scope-specific (Rick.ai Tests CI); v3 generic |
| I11 | Team-main-sync blocked by degraded n8n-mcp | 2026-04-03 | RC-C | §0.0.5 Chain dispatch — degraded MCP = warning, not blocker | Chain selection rules allow degraded sub-status | **confirmed** | requires Makefile-level coordination (separate from skill) |
| I10 | Fresh clone — n8n-mcp inferred from tracked artifacts only | 2026-04-03 | RC-D | §0.0.4 State C post-sync `make team-activate` mandatory | Step 4 post-sync bootstrap | **confirmed** | depends on Makefile contract |
| I9 | n8n native deps через root workspaces несмотря на tracked | 2026-04-03 | RC-D | §0.0.4 State I + submodules-registry.yaml classification | Step 1 inventory checks registry | **confirmed** | new submodule = registry edit; agent must commit registry first |
| I8 | team-main-sync failed clone — node-gyp / Python 3.13 | 2026-04-03 | RC-D | §0.0.4 State C bootstrap env contract | Step 4 post-sync activate | **partial** | env mismatch detected by Makefile, not by skill itself |
| I7 | Parallel Codex agents shared dirty main | 2026-03-09 | RC-A | §0.0.4 State G + §0.0.6 L1 teammate scan; AGENTS.md «worktree per child bead» | L1 teammate scan finds 24h commits → STOP | **confirmed** | requires AGENTS.md «one bead one worktree» discipline |
| I6 | Blind RickAI pre-push gate too heavy для non-RickAI | 2026-03-09 | RC-C | §0.0.5 minimal vs full chain by diff scope; documented `SKIP_REAL_MCP_SMOKE=1` bypass | Chain selection based on State | **confirmed** | requires pre-push hook understanding bypass env |
| I5 | `stage all` treated as publish scope | 2026-03-09 | RC-B | §Critical loop-breakers §0 «Stage-all intent classification» | Step 0 forces classification | **confirmed** | declarative; agent must read SKILL §Critical loop-breakers |
| I4 | n8n-mcp external nested repo без registry | 2026-03-09 | RC-D | §0.0.4 State I + submodules-registry.yaml SSOT | Step 1 inventory enumerates registry | **confirmed** | one-time registry creation completed |
| I3 | Sync goes in circles на changelog gate + mutating pre-push + unpublished nested | 2026-03-08 | RC-B | §Critical loop-breakers §1-§4 + §0.0.8 F4 narrative file union driver + F5 submodule 403 fork route | Loop-breaker §1 detects same blocker repeating → STOP retry | **confirmed** | declarative; needs agent self-discipline |
| I2 | Submodule не запушены — команда не получает | 2026-02-16 | RC-D | §Шаг 4 Submodule discipline (push inside before bump parent) + §0.0.6 L3 | Step 4 sequence push-before-bump | **confirmed** | requires teammates push access to submodule repo |
| I1 | Pre-commit 500KB limit blocked normal assets | 2026-02-16 | RC-E | §3 documented 100MB threshold | Documentation prevents recurrence | **confirmed** | one-time threshold fix; future drift = new RCA |

## Verdict summary

| Verdict | Count | % |
|---|---|---|
| confirmed (v3 blocks) | 11/14 | 78% |
| partial (v3 reduces probability) | 3/14 | 22% |
| falsified (v3 doesn't address) | 0/14 | 0% |

**Hypothesis status:** **confirmed for 11 incidents; partially confirmed for 3 (I13, I12, I8)** — these have residual risk requiring complementary mechanisms (Makefile contract for I12/I8; explicit `bash -n` syntax step for I13).

## Coverage gaps (что v3 пока НЕ закрывает полностью)

| Gap | Source incident | Recommended addition | Priority |
|---|---|---|---|
| G-gap1: Hook syntax validation в pre-flight | I13 | Add `## Step 2.5 hook syntax check` в pre-flight-workflow.md (`bash -n .githooks/*` + `python3 -c "import ast; ast.parse(...)"` for .py hooks) | medium |
| G-gap2: Stale evidence blocks fresh clone (CI-side) | I12 | Coordinate с CI workflow team — not in skill scope alone | low (separate concern) |
| G-gap3: Env mismatch detection (Python 3.x, node-gyp) | I8 | Document `make team-activate` contract — covered separately в Makefile + post_sync_bootstrap_guard.py | low (covered) |
| G-gap4: New incident class L7 «mid-session merge conflict в active subagent worktree» | hypothetical | Watch for occurrence; add to checklist if observed | watch |

## Mechanical enforcement status

| Section | Enforcement | Status |
|---|---|---|
| §0.0 Sit-down triage | declarative | <client>-reading |
| §0.0.4 State Router | declarative | <client>-reading |
| §0.0.5 Subagent Chain | declarative | <client>-reading |
| §0.0.5a QA-3 verdict | declarative | <client>-reading |
| §0.0.6 L1-L5 preservation | declarative | <client>-reading |
| **§0.0.6 L6 parallel-session** | **mechanical** (`.claude/hooks/pre_git_clean_parallel_check.py`) | **landed 2026-05-14** |
| §0.0.7 @auto dispatch | declarative | <client>-reading |
| §0.0.8 Recovery Playbook F1-F7 | declarative | <client>-reading |
| dirty tree ≥ 200 | **mechanical** (`.claude/hooks/git_dirty_count_gate.py`) | landed earlier |

**Conclusion:** только **2 из 9** v3 layers имеют mechanical enforcement; 7 declarative. Это **major gap** — без mechanical PreToolUse hooks для §0.0.4 (State Router check), §0.0.5 (Chain dispatch), §0.0.6 L1-L5 (preservation), §Critical loop-breakers — рецидивы возможны под agent cognitive load.

## Falsification test cases (future)

Для каждого incident — построить test fixture в `tests/sync/test_incident_<id>.py`:
- Setup: воспроизвести state ПЕРЕД incident (dirty tree, branches, submodules)
- Action: запустить command который вызывал incident
- Assert: v3 hook BLOCKs ИЛИ skill reading catches issue ДО action

Это **separate bead** — `pr-sync-v3-falsification-fixtures`.

## How to use this falsification table

ДО каждого sync flow agent читает эту таблицу + `known-incidents-checklist.md`:

1. Identifies какой incident-pattern actually matches current state
2. Checks Verdict — если `confirmed` → следует соответствующему v3 section
3. Если `partial` → escalate risk + applies extra caution
4. Если новый pattern не в таблице → discovery → нужен новый RCA + новый v3 section + new row в этой таблице

**Hard fail:** sync flow выполнен без чтения этой таблицы при `state` совпадающем с любым из I1-I14 → RCA `category: hypothesis-falsification-table-skipped`.
