# Community Skill Handoff

This folder contains the extra working skills requested for the Gap Theory community handoff.

## What Was Requested

| Request | Where it lives | What to check |
|---|---|---|
| RCA skills | `skills/2-rca-incidents/` | `SKILL.md`, `references/`, `scripts/` are present |
| Hook chat result / how hooks work | `docs/hooks-chat-result.md` plus `skills/0-hook-self-test/`, `skills/0-hooks-minimum-sufficiency/`, `skills/0-portable-claude-hooks/` | Read the chat result and run `python3 verify_handoff.py` |
| Visual document skill | `skills/visual-explainer/` | `commands/`, `references/`, `templates/`, `scripts/share.sh` are present |
| Scenarios from обращения / conversations | `skills/4-conversation-normalize/`, `skills/4-conversation-action-chain-extract/`, `skills/2-jtbd-scenarium-create/`, `skills/4-rickai-calls-jtbd-scenarios-extract/` | lightweight text flow and heavier call-corpus flow are both present |

## How To Use

1. Pick the skill folder that matches the job.
2. Read its `SKILL.md` fully.
3. If it references local `scripts/`, `tests/`, `commands/`, `templates/`, or `references/`, use the copy inside this folder.
4. Run `python3 verify_handoff.py` before sharing the bundle.

## Verification

```bash
cd handoff/community-skills
python3 verify_handoff.py
python3 -m pip install -r requirements.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/2-jtbd-scenarium-create/tests \
  skills/4-rickai-calls-jtbd-scenarios-extract/scripts/test_*.py
```

Expected:

```text
COMMUNITY_SKILL_HANDOFF_VERIFY_PASS
```

## License Notes

This repository is distributed under the licenses declared at the repository root. Keep upstream skill metadata and notices visible when redistributing or adapting imported skills.
