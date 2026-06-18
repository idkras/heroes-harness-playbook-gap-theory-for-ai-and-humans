# Known Sync Incidents Checklist — what v3 must prevent

**Companion to `SKILL.md`** — exhaustive inventory всех sync/git RCA incidents в `<internal-folder>/ai.incidents.md` с mapping на v3 sections.

**Purpose:** ДО каждого sync flow agent читает эту таблицу, identifies which incident classes могут произойти в текущей situation, и применяет соответствующий v3 section. Если incident class **не покрыт** v3 — обязательно добавить новый section в SKILL.md и записать новый RCA.

**Updated:** 2026-05-14 (14 incidents inventoried, 1 new from this session).

## Incidents table (sorted by date desc)

| # | Date | Incident headline | RCA link | Root cause class | How v3 prevents (section) | Status |
|---|---|---|---|---|---|---|
| **I14** | 2026-05-14 | Agent `git clean -fd` уничтожил untracked work параллельной Claude session (<internal-component> + bronze + rick-form-build) | [ai.incidents:4](../../../[todo%20·%20incidents]/ai.incidents.md#L4) | destructive-op-without-parallel-session-check | **§0.0.6 L6** «Parallel-session untracked work» — 3-layer pre-clean check (mtime <60min + /tmp claude-sessions + JSONL Write grep). Mechanical hook `pre_git_clean_parallel_check.py` enforces. | **RESOLVED-PARTIAL** (declarative); pending mechanical hook landed (this session) |
| I13 | 2026-05-10 | `.githooks/*` broken shell syntax → каждый `git checkout` валил error | [ai.incidents:5471](../../../[todo%20·%20incidents]/ai.incidents.md#L5471) | hook-shell-syntax-without-pre-merge-validation | **§0.0.6 L4** stash inventory shows hook files; pre-flight workflow runs `bash -n .githooks/*` syntax check | resolved (separate fix) |
| I12 | 2026-04-03 | `Rick.ai Tests` misreported sync readiness because legacy filesystem debt remained | [ai.incidents:4993](../../../[todo%20·%20incidents]/ai.incidents.md#L4993) | stale-evidence-blocks-fresh-clone | **§0.0.4 State C/E** — fresh fetch + inventory cleans before test gate | resolved |
| I11 | 2026-04-03 | Team-main-sync blocked by degraded `n8n-mcp` smoke | [ai.incidents:4965](../../../[todo%20·%20incidents]/ai.incidents.md#L4965) | optional-mcp-treated-as-blocking | **§0.0.5 Chain dispatch** allows degraded MCP as warning, not blocker | resolved (separate Makefile fix) |
| I10 | 2026-04-03 | Fresh clone failed full sync because `n8n-mcp` runtime inferred from tracked artifacts | [ai.incidents:4931](../../../[todo%20·%20incidents]/ai.incidents.md#L4931) | bootstrap-after-clone-skipped | **§0.0.4 State C** post-sync `make team-activate` mandatory | resolved |
| I9 | 2026-04-03 | `n8n` native dependency через root workspaces несмотря на tracked artifacts | [ai.incidents:4903](../../../[todo%20·%20incidents]/ai.incidents.md#L4903) | submodule-build-not-classified | **§0.0.4 State I** + `submodules-and-projects-registry.yaml` classification | resolved (separate Makefile fix) |
| I8 | 2026-04-03 | `team-main-sync` failed on fresh clone — `node-gyp` global Python 3.13 без distutils | [ai.incidents:4820](../../../[todo%20·%20incidents]/ai.incidents.md#L4820) | clone-bootstrap-env-mismatch | **§0.0.4 State C** post-sync Makefile env contract | resolved (separate Makefile fix) |
| I7 | 2026-03-09 | Parallel Codex agents shared one dirty main worktree → mixed scopes | [ai.incidents:2471](../../../[todo%20·%20incidents]/ai.incidents.md#L2471) | parallel-agents-on-dirty-main | **§0.0.4 State G/K** mandatory inventory + teammate scan; **§Worktree per child bead** AGENTS.md rule | resolved (separate) + reinforced by v3 |
| I6 | 2026-03-09 | Blind RickAI pre-push gate too heavy для non-RickAI pushes | [ai.incidents:2666](../../../[todo%20·%20incidents]/ai.incidents.md#L2666) | <client>-diff | **§0.0.5 Chain — minimal vs full** based on diff scope; documented `SKIP_REAL_MCP_SMOKE=1` bypass criteria | resolved |
| I5 | 2026-03-09 | `stage all` treated as publish scope instead of local snapshot | [ai.incidents:2860](../../../[todo%20·%20incidents]/ai.incidents.md#L2860) | stage-all-intent-classification-missing | **§0.0.4 State E/F** classification + `0. Stage-all intent classification` в `Critical loop-breakers` | resolved |
| I4 | 2026-03-09 | `n8n-mcp` external nested repo без root-managed mapping | [ai.incidents:2840](../../../[todo%20·%20incidents]/ai.incidents.md#L2840) | external-nested-repo-not-in-registry | **§0.0.4 State I** + `submodules-and-projects-registry.yaml` SSOT | resolved |
| I3 | 2026-03-08 | Sync goes in circles on `changelog` gate + mutating pre-push + unpublished nested commits | [ai.incidents:3067](../../../[todo%20·%20incidents]/ai.incidents.md#L3067) | retry-without-blocker-fix | **§Critical loop-breakers** §0-§5 in SKILL.md + **§0.0.8 F4** narrative file conflict via union driver + **§0.0.8 F5** submodule 403 fork route | resolved |
| I2 | 2026-02-16 | Submodule не запушены — команда не получает актуальные версии | [ai.incidents:3950](../../../[todo%20·%20incidents]/ai.incidents.md#L3950) | submodule-bump-without-internal-push | **§Шаг 4 Submodule discipline** + **§0.0.6 L3** submodule HEAD ahead | resolved |
| I1 | 2026-02-16 | Pre-commit 500KB limit blocked normal assets | [ai.incidents:4003](../../../[todo%20·%20incidents]/ai.incidents.md#L4003) | hook-threshold-too-strict | **§3 Pre-commit size 100MB** documented threshold | resolved (separate hook fix) |

## Cross-cut root cause classes (5)

Все 14 incidents группируются по 5 root cause классам — это **architectural failure modes** sync flow:

| RC class | Frequency | Examples | v3 prevention layer |
|---|---|---|---|
| **RC-A Destructive op без preservation** | I14 (2026-05-14), I7 (2026-03-09) | `git clean -fd` без parallel-session check; `stage all` on dirty main with teammate work | §0.0.6 L1-L6 «Nothing Lost» + mechanical hooks |
| **RC-B Retry без blocker fix** | I3 (2026-03-08), I12 (2026-04-03) | Цикл `git add -A → commit → push` без устранения blocker; stale evidence blocks fresh clone | §Critical loop-breakers §0-§5 + §0.0.8 Recovery F1-F7 |
| **RC-C Universal gate не scoped по diff** | I6 (2026-03-09), I11 (2026-04-03) | RickAI pre-push gate heavy для non-RickAI commits; n8n-mcp degraded blocks all | §0.0.5 Chain — minimal/basic/full chain selection based on State + bypass criteria |
| **RC-D Submodule/external repo не в registry** | I4 (2026-03-09), I9-I10 (2026-04-03) | n8n-mcp как external untracked; build artifacts через global env | §0.0.4 State I + `submodules-and-projects-registry.yaml` + `external-git-hosts.yaml` SSOT |
| **RC-E Hook syntax / threshold drift** | I1 (2026-02-16), I13 (2026-05-10) | Pre-commit 500KB; broken `.githooks/*` shell syntax | §3 documented thresholds + pre-flight `bash -n` syntax check workflow step |

## v3 coverage matrix

| v3 section | Incidents prevented | Status |
|---|---|---|
| §0.0 Sit-down dirty-tree triage | I3, I5, I7 | landed (RCA 2026-05-13) |
| §0.0.1 Confidence calibration | I3 (retry loop) | landed |
| §0.0.4 Project-State Router | I7, I12, I10, I9 | landed (this session) |
| §0.0.5 Subagent Chain | I6, I11 | landed (this session) |
| §0.0.5a QA-3 verdict format | (preventive — no incident yet, but addresses claim-without-verification class) | landed (this session) |
| §0.0.6 «Nothing Lost» L1-L6 | I14, I7, I2, all RC-A | landed (this session; L6 added after self-falsification) |
| §0.0.7 @auto sync trigger dispatch | (preventive routing) | landed (this session) |
| §0.0.8 Recovery Playbook F1-F7 | I3, I8, F5-submodule-403 | landed (this session) |
| §2.0 Per-submodule classification | I4, I9, I10 | landed (RCA 2026-05-13) |
| §3.0.1 SSL retry policy | (transient network class) | landed (RCA 2026-05-13) |
| §3.0.2 Pre-push hook hangs | I13 | landed (RCA 2026-05-13) |

**Gap:** §0.0.6 L6 enforcement is currently **declarative only**. Mechanical hook `pre_git_clean_parallel_check.py` in this session closes it.

## How to use this checklist

**ДО каждого sync flow** (любое из: `git checkout`, `git pull`, `git rebase`, `git push`, `git clean`, `git reset`, `git stash`, `git merge`):

1. Read this table top-to-bottom (~30 seconds)
2. For each incident row, ask: «Может ли эта ситуация повториться в моём контексте сейчас?»
3. If yes — open соответствующий v3 section in SKILL.md и применить guard
4. If incident class NOT в table — STOP, добавить new row + новый section в SKILL.md + новый RCA в ai.incidents.md (это означает discovery нового loss vector)

**Hard fail:** sync op executed without reading этой таблицы → RCA `category: known-incidents-checklist-skipped`.

## Updates protocol

Когда новый sync RCA добавляется в `ai.incidents.md`:

1. Добавить row в эту таблицу (newest first)
2. Identify root cause class (RC-A/B/C/D/E или новый)
3. Map на v3 section (или создать новый)
4. Update Cross-cut root cause classes table если frequency changed
5. Update v3 coverage matrix
