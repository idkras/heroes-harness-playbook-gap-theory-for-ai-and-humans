# Hook Chat Result: How The Runtime Was Proven

This is the compact handoff note for the previous hooks chat/result that community members asked to see.

## What Was Demonstrated

The hook system is not only prose in `AGENTS.md`. It has three layers:

| Layer | What it does | Example proof |
|---|---|---|
| Configuration | Runtime reads project hook config such as `.codex/hooks.json` or Claude hook settings | hook config is present and points to hook runner scripts |
| Smoke wiring | A harness command checks that a hook is discoverable and can be invoked | `runtime_smoke.py` proves wiring scope |
| Live fire | A trusted fixture project triggers the real runtime event and observes that the hook fired | `codex_live_fire.py` returned `hook_fired=true` for `PreToolUse` and `UserPromptSubmit` |

## Why The First Attempt Was Not Enough

The first Codex hook live-fire check returned `hook_not_observed`. That did not prove hooks were broken. It proved the test harness was too noisy: the temp project was not trusted and user-level config leaked into the run.

The fix was to isolate the test:

1. create an isolated `CODEX_HOME`;
2. use a trusted temporary project;
3. enable `features.hooks=true`;
4. run a live-fire check for the exact event;
5. only claim success when the runtime reports `hook_fired=true`.

## Community Takeaway

When you apply hooks in another repo:

1. Do not trust config presence alone.
2. Run a smoke check to prove wiring.
3. Run a live-fire check to prove the runtime actually emits the event.
4. Treat `hook_not_observed` as a falsification prompt, not as permission to claim success.
5. Record the proof as command + exit code + stdout, not as a summary.

## Source Evidence Summary

From the previous live-fire chat summary:

```text
scripts/hooks/codex_live_fire.py proved hook_fired=true for both PreToolUse and UserPromptSubmit.
scripts/hooks/runtime_smoke.py was treated as wiring proof only.
The stronger claim required live-fire in an isolated CODEX_HOME with a trusted fixture project.
```

## Related Skills In This Handoff

- `skills/0-hook-self-test/`
- `skills/0-hooks-minimum-sufficiency/`
- `skills/0-portable-claude-hooks/`
