# AGENTS.md — Project meta-rules for AI agents working with this repo

This file is the **AI-agnostic protocol** for any AI agent (Claude, GPT, Gemini, custom) operating on this repository.

For the orchestration playbook (12 stages, QA gate, design gate), see [`playbook/03-orchestrator-with-qa-design-gate.md`](playbook/03-orchestrator-with-qa-design-gate.md).

---

## Mandatory delivery format

Every substantial response must include:

1. Было / Стало (Was / Became)
2. JTBD scenario
3. Input checklist
4. Output checklist
5. Outcome checklist
6. Design review
7. QA review
8. Deploy & PR review
9. **Hypothesis falsification** — gap table `Expectation | Reality | Δ | Verdict`
10. **Owner effort digest** — next-action with 0-100 effort scale; any single click by owner = minimum 50
11. Run Evidence
12. Canonical Vocabulary Check (PASS / FAIL)

See [`templates/06-owner-effort-digest.md`](templates/06-owner-effort-digest.md) for owner effort scale.

---

## Generalization-first gate

Before writing any code or component, agent MUST get 4×yes:

1. Works for all clients from manifest without code change?
2. Client identity from manifest, not from props/state literals?
3. Data paths resolve from manifest.dataSource, not string literals?
4. New client = manifest edit only, no new components?

If any answer is "no" — redesign before implementation.

See [`playbook/03-orchestrator-with-qa-design-gate.md`](playbook/03-orchestrator-with-qa-design-gate.md) §3.

---

## Self-falsification mandatory

After substantial delivery, agent runs [`skills/01-hypothesis-gap-falsification.md`](skills/01-hypothesis-gap-falsification.md) on own work:

1. Hypothesis in one sentence
2. Expectations table (5+ rows)
3. Reality check (read files, run tests)
4. Gap table with verdict
5. If `falsified` or `partially confirmed` — go back to implementation, don't deliver

---

## Mandatory subagent gates

Orchestrator MUST run before delivery:

- `ui-qa-engineer` (if UI involved) + `code-reviewer` (always) — **parallel**
- `design-art-director` — adversarial stress-test
- `rca-investigator` — if any gap found

See `agents/` folder for canonical definitions.

---

## Anonymization policy

This repo uses anonymized client names (<client>, <client>, <client>, <client>, designcraft, fitcrew, bigfin, tempest, <internal-component>, praxis platform). When contributing examples:

- Use anonymized similar-domain names (don't expose real client identities)
- Preserve subject area (auto B2B, fashion ecom, mattress retail, etc.) so readers can map to their context
- Real numbers can be modified to anonymized but proportional values

---

## Language

Russian primary for human-facing delivery. English for: API names, code identifiers, vendor UI labels, technical proper names (JTBD, RCA, SSOT, MCP).

---

## Anti-patterns

- Don't add backward-compat shims for code you control
- Don't write multi-paragraph comments — code should be self-explanatory through naming
- Don't create new docs unless asked
- Don't deliver with `if (alias === "X")` branches — use manifest
- Don't skip QA / design / falsification stages

---

## When in doubt

Read the relevant standard from `standards/`. If still unclear, open Issue or Discussion before changing canon.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
