---
name: 19-orchestrator-pipeline
description: >
  Universal orchestrator pipeline — the single source of truth for how a manager-lead
  agent drives ANY task (code, document, program, data, client artifact) through all
  12 stages from intake to verified outcome. Client-agnostic: works for every client
  via config/manifest, never via `if client == "X"` branches. Makes QA review + design
  review + self-falsification MANDATORY gates that ALWAYS run before delivery — not
  "when there is time". Use whenever you act as orchestrator / manager-lead, or before
  any substantial delivery (≥5 file writes, ≥10 min work, any commit to main, any
  client-facing artifact). Pairs with agents/manager-lead-orchestrator.md (the role)
  and playbook/03-orchestrator-with-qa-design-gate.md (the worked example).
---

# Skill 19 — Universal Orchestrator Pipeline

> **This skill is the SSOT for the orchestrator's stages.** The agent file
> (`agents/manager-lead-orchestrator.md`) describes *who* the orchestrator is; this
> skill describes *the stages it must pass through, in order, every time*. If the two
> ever disagree, **this skill wins** for stage definitions.

## Core law

> **The orchestrator does not do the work. It drives the work through stages and
> spawns specialists.** It never skips a gate to save time. QA, Design, and
> Self-falsification (stages 7–9) are **not optional** — skipping any is an incident.

Five universal design principles (apply to every client, every artifact):

1. **Universal, not client-specific.** Every solution works for all clients through
   `config` / `manifest`, never through `if (client === "X")` branches or
   `ClientNameThing.tsx` files. Enforced by the **Generalization Gate** (stage 5).
2. **Falsification is mandatory.** After building, the orchestrator falsifies its own
   "I fixed everything" hypothesis via `skills/01-hypothesis-gap-falsification.md`
   (stage 7) **before** QA ever sees it. Catches success-theater early.
3. **QA + Design review every time.** Stages 8 and 9 are gates before delivery — run
   the reviewer subagents in **parallel** (one message, multiple Agent calls), always.
4. **Stages are enumerated and announced.** The orchestrator states "I am at stage X
   of 12" and may not jump ahead. No silent skipping.
5. **No legacy.** No backward-compat shims, feature flags, or `_v2` appendices bolted
   on the side. If something old blocks the root cause — redesign it at the root.

---

## The 12 stages (mandatory, in order)

| # | Stage | What happens | Driven by | Output / gate artifact |
|---|---|---|---|---|
| 1 | **Intake** | Capture what the owner wants + what they already tried | Orchestrator | One-line JTBD + quick ticket card |
| 2 | **Outcome design** | 5×so-what ladder to the *real* owner outcome + critical chain | `outcome-designer` | Outcome card |
| 3 | **Hypothesis design** | Falsifiable hypothesis + alternative + falsification criterion + baseline/threshold | `hypothesis-designer` | Hypothesis card |
| 4 | **Expected-output table** | Contract: what will exist when done (columns=fields, rows=example data) | Orchestrator | Markdown table *before* build |
| 5 | **Generalization Gate (4×yes)** | Solution works for all clients via config, not branches | Orchestrator + `code-reviewer` | 4×yes, or redesign |
| 6 | **Implementation** | Build code/doc/artifact in incremental slices | Developer (agent or human) | Files + tests |
| 7 | **Self-falsification** ⚠ | Orchestrator falsifies its own work (`skills/01`) | Orchestrator | Gap table + verdict |
| 8 | **QA review** ⚠ (gate) | `ui-qa-engineer` + `code-reviewer` independently, in parallel | 2+ subagents | QA verdict + issues |
| 9 | **Design review** ⚠ (gate) | `design-art-director` adversarial stress-test | `design-art-director` | Design verdict + risks |
| 10 | **RCA-injection** (if gap) | If 7–9 found a gap → root-cause-first, fix the standard/skill/agent, not the symptom | `rca-investigator` | RCA card (0–100 scale) |
| 11 | **Delivery** | Final answer with the 12 mandatory sections | Orchestrator | Structured delivery |
| 12 | **Outcome verify** | After N days: did the stage-2 outcome materialize? | Orchestrator + metrics | Confirmation or new bead |

**Hard fail:** skipping stage **5, 7, 8, 9, or 12** is an RCA incident. Stages 7–9 are
the quality core and are never optional, regardless of task size.

---

## Stage transition checklist (a gate, not an auto-step)

Before moving `current → next`, all checks must pass, and the result is recorded in the
reasoning log (`skills/10-agent-reasoning-log.md`) as one line with the minimum schema
`stage | decision | evidence | gap-found | next-action`. An empty or missing log line =
`stage-gate-skipped`. If any check fails, the task stays.

**Every** transition below is gated by its checklist — not just 5/7/8/9/12. Skipping the
checklist for *any* transition (including 2, 3, 4, 6, 10, 11) is `stage-gate-skipped`.

| Transition | Must be true |
|---|---|
| 1→2 | JTBD captured in one human sentence |
| 2→3 | Outcome card exists; critical chain drawn |
| 3→4 | Hypothesis is falsifiable (has baseline + threshold + falsification criterion) |
| 4→5 | Expected-output table written *before* any code/doc write |
| 5→6 | 4×yes Generalization Gate passed (see below) |
| 6→7 | Build complete; local tests green (or "why not" stated) |
| 7→8 | Self-falsification verdict = `confirmed` (else back to 6) |
| 8→9 | No `critical`/`blocking` QA issue open (else back to 6 or 10) |
| 9→10/11 | Design verdict = `approved` (else back to 6 or 10) |
| 10→11 | Root cause fixed at standard/skill/agent level, logged in incidents |
| 11→12 | Delivery has all 12 sections |
| 12→done | Outcome materialized, or new bead created with next hypothesis |

---

## Stage 5 — Generalization Gate (4×yes)

Before any `Write` to code/doc/template, get 4 `yes`:

1. Works for **all clients** from manifest without editing the component — only via `config.json` / `manifest.dataSource`?
2. Client identity comes from `manifest`/`config`, not props/state/literals?
3. Data paths resolve from `manifest.dataSource`, not string literals?
4. A **new client** is added by editing only `manifest.json` + dropping data files — no new `.tsx`, no registry edits?

Any `no` → redesign before building. (RCA source: 2026-04-17 — agent built
`BigfinFunnelSection.tsx` + `if (alias === 'bigfin')`; owner: "we build universal code
for all clients, right?". Correct pattern: one `<FunnelSection manifest={...} />`.)

For **non-code artifacts** (a skill, a standard, an educational program, a template),
the same gate reads: *does this work for any client/cohort by swapping inputs, or did I
bake one client's specifics into the structure?*

---

## Stage 7 — Self-falsification (BEFORE QA)

Run `skills/01-hypothesis-gap-falsification.md` on your own work:

1. Hypothesis in one line: "I closed the owner's job via X."
2. Expectations table — ≥5 things that must be true.
3. Reality check — what is *actually* on disk / in the product / in the data (read it, don't assume).
4. Gap table: `Expectation | Reality | Δ | Severity | Next action | Human effort (0–100)`.
5. Verdict: `confirmed | partially confirmed | falsified`.

If verdict ≠ `confirmed` → do **not** deliver; return to stage 6. Purpose: catch
success-theater before QA or the owner does.

> ⚠ **Self-falsification is structurally weak — it is a conflict of interest.** The same
> agent that built the work is biased toward writing `confirmed`. Stage 7 is therefore
> only the *cheap first pass*. It does **not** replace independent falsification: the
> stage-8 reviewers run **independently** of the builder, and at least one of them MUST
> apply `skills/11-subagent-falsification.md` (an independent agent that actively tries to
> *refute* the work, defaulting to "falsified" when uncertain). Treating stage 7 as the
> only falsification = theatre. (Design-review finding F8, 2026-06.)

---

## Stages 8–9 — QA + Design gates (ALWAYS, in parallel)

After build, the orchestrator **always** runs, in **one message with multiple Agent calls**:

### Mandatory minimum (every task — all three)

| Subagent | Always? | Checks |
|---|---|---|
| `code-reviewer` | yes (even for docs) | correctness, security baseline, architecture, maintainability, tests |
| `ui-qa-engineer` | yes | JTBD tree (big/medium/small), corner cases (5W+H × role × state), ≥10 test cases, coverage gaps; for UI: screenshot evidence (DOM-only = hard fail) |
| `design-art-director` | yes (UI/UX/docs/operator-flow) | adversarial stress-test: hidden complexity, trust erosion, false confidence, integration gaps, team defensive reactions |

### Conditional extras (add by task type)

| Task type | Add |
|---|---|
| Readiness-to-build / job-chain | `inception-reviewer` |
| Incident fix / regression / root-cause gap found by ≥2 reviewers | `rca-investigator` (also acts as a stage-8 reviewer here, not only stage-10 driver) |
| Independent falsification of the build (mandatory ≥1 reviewer) | `rca-investigator` or any reviewer applying `skills/11-subagent-falsification.md` |
| Client-facing document (named recipient) | `client-persona-reviewer` (**mandatory, blocking**) |
| Process reconstruction from chat/calls | `process-correspondence-investigator` |

> **Extended deployment roster (optional, NOT in this repo's core):** some deployments
> add specialist reviewers — `frontend-reviewer`, `backend-reviewer`, `security-reviewer`,
> `perf-reviewer`, `a11y-reviewer`, `review-gate-checker`, `cleanup-guardian`,
> `data-analyst`. If they are not defined in your `agents/` folder, fold their concerns
> into `code-reviewer` + `design-art-director`. **Never reference an agent that does not
> exist** — that is a broken-reference legacy smell.

### Verdict format (every reviewer returns)

```
verdict: pass | needs-work | blocking
issues:
  - severity: critical | high | medium | low
    description: ...
    location: file:line  (or section)
    fix-direction: ...
```

Any `critical` / `blocking` → do not deliver; return to stage 6 (re-build) or 10 (RCA).
If 2+ reviewers find the same issue → raise its severity one step.

### Re-review loop (after fixing blocking issues)

After a hot-fix that closes blocking findings, run a **mini-squad of only the reviewers
who raised them** ("does commit/edit X close findings A,B,C? closed/partial/regression")
before any stage transition. Skipping re-review after a hot-fix is an incident.

---

## Stage 11 — Delivery (12 mandatory sections)

1. Was / Became
2. JTBD scenario
3. Input checklist
4. Output checklist
5. Outcome checklist
6. Design review (verdict + risks)
7. QA review (verdict + pass/fail)
8. Deploy & PR review (or "n/a — no code")
9. Hypothesis falsification (gap table + verdict)
10. Owner effort digest (next actions, 0–100 scale)
11. Run evidence (commits/files/links)
12. Canonical vocabulary check (PASS/FAIL)

---

## Enforcement loop (the orchestrator runs this for every substantial delivery)

```
1. Stages 1–4: intake → outcome-designer → hypothesis-designer → expected-output table
2. Stage 5: 4×yes Generalization Gate (else redesign)
3. Stage 6: delegate Implementation to developer (don't build it yourself)
4. Stage 7: self-falsify (skills/01) — verdict must be `confirmed`
5. Stage 8+9: emit task-cards, then Agent(code-reviewer, ui-qa-engineer, design-art-director, ...) IN PARALLEL
6. Merge reports: severity × source × location × status; any 2 agreeing → +1 severity
7. Fix every blocking/critical in the same session → stage 10 RCA if root-cause gap
8. Mini-squad re-review of only the finders → must say `closed`
9. Stage 11: deliver with 12 sections
10. Stage 12: schedule outcome verify
```

**"Substantial delivery" — THE single definition (do not restate a different number
elsewhere):** ≥5 file writes OR ≥10 min work OR any edit to `src/` / `standards/` /
`skills/` / `agents/` / client data OR any commit to main OR any client-facing artifact.
Trivial (one typo fix in a single file, reading files, simple Q&A, git status/log/diff)
does not require the full squad. **There is no self-exemption for editing the
orchestrator's own skill/agent files** — changing the pipeline is itself substantial and
must pass stages 7–9. (Code-review finding: two conflicting thresholds + a self-exemption
loophole, 2026-06.)

## Enforcement reality (honest limitation)

The hard-fail catalog is an **honor system**: an orchestrator under time pressure can
*claim* it ran the gate, or run a "fake parallel" (one Agent call, mocked result). The
catalog deters but does not detect. Two real defenses, in order of strength:

1. **External hook (recommended where supported):** a Stop / PostToolUse hook that counts
   `Write`/`Edit` calls in a turn and refuses completion unless ≥3 reviewer `Agent` calls
   were emitted in one message since the last delivery. This is deployment-specific
   (e.g. `settings.json` hooks) and moves enforcement out of the model's own judgment.
2. **Reasoning-log audit:** a periodic independent pass over the reasoning log checks that
   each substantial delivery has the stage-7/8/9 lines with real reviewer agent-ids.

Without one of these, "always run QA + design" is a discipline, not a guarantee — state
this honestly to the owner rather than implying mechanical certainty. (Design finding F7.)

## Hard-fail catalog (each = an incident in your incidents log)

| Category | Trigger |
|---|---|
| `stage-gate-skipped` | moved ANY stage (1→2 … 12→done) without logging the checklist line |
| `outcome-design-skipped` | built without stage 2 (outcome-designer) |
| `hypothesis-design-skipped` | built without stage 3 falsifiable hypothesis (baseline+threshold) |
| `expected-output-skipped` | wrote code/doc without the stage-4 contract table |
| `generalization-gate-skipped` | wrote client-specific code/structure without 4×yes |
| `self-falsification-skipped` | delivered without stage 7 |
| `independent-falsification-skipped` | stage 8 ran without ≥1 reviewer applying skills/11 |
| `qa-gate-skipped` | delivered without stage 8 (code-reviewer + ui-qa-engineer) |
| `design-gate-skipped` | delivered without stage 9 (design-art-director) |
| `squad-not-parallel` | reviewers run sequentially instead of one parallel message |
| `blocking-not-closed` | blocking/critical left open before a transition |
| `hot-fix-no-reverify` | hot-fix without mini-squad re-review |
| `delivery-format-incomplete` | stage-11 delivery missing any of the 12 sections |
| `broken-agent-reference` | referenced an agent that does not exist in `agents/` |
| `outcome-verify-skipped` | closed without stage 12 |

## Related

- `agents/manager-lead-orchestrator.md` — the orchestrator role
- `playbook/03-orchestrator-with-qa-design-gate.md` — worked example
- `skills/01-hypothesis-gap-falsification.md` — stage 7 (mandatory)
- `skills/03-so-what-outcome-ladder.md` — stage 2
- `skills/09-critical-chain-design.md` — stage 2 critical chain
- `skills/11-subagent-falsification.md` — independent falsification in stages 8–9
- `skills/16-task-completion-persistence.md` — don't stop at partial
- `templates/04-expected-output-table.md` — stage 4
- `templates/06-owner-effort-digest.md` — stage 11 section 10
