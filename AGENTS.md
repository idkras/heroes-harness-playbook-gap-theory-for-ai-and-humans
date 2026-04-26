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

This repo uses anonymized client names (galaxypets, autovin, fashionhub, sleepwell, designcraft, fitcrew, bigfin, tempest, pulse.ai, praxis platform). When contributing examples:

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
