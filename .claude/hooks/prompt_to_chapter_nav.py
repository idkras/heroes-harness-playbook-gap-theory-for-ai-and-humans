#!/usr/bin/env python3
r"""prompt_to_chapter_nav.py — UserPromptSubmit hook.

Owner ask 2026-06-21: «каждое моё сообщение-промт и steering должны попадать в
навигацию по чату по умолчанию».

HONEST LIMITATION (verified против Claude Code hooks reference): a UserPromptSubmit
hook CANNOT create a navigation chapter itself. The chat table-of-contents is
populated by the `mcp__ccd_session__mark_chapter` MCP tool, which only the MODEL can
call. A hook can only inject context the model then acts on. So this hook does the
one thing it can: on every substantive prompt it injects a directive telling the
agent to call mark_chapter with a short title derived from the message — making each
user prompt / steering reliably show up in chat navigation.

It is therefore semi-deterministic (depends on the model obeying the injected
directive), not a hard guarantee. Paired with an AGENTS.md rule it is the closest
reliable mechanism available today.

Contract (Claude Code UserPromptSubmit hook):
    stdin  = JSON {prompt, session_id, ...}
    stdout = JSON {hookSpecificOutput: {hookEventName, additionalContext}}
    exit 0 = pass (prompt proceeds; additionalContext is injected for the model)

Skips trivial prompts (one short ack / a slash-command only) so navigation isn't
spammed. Fail-open on any error (never blocks the user's turn).
"""

from __future__ import annotations

import json
import re
import sys

# Trivial prompts that should NOT create a nav chapter (acks, pure slash-commands).
_TRIVIAL = re.compile(
    r"^\s*(ok(ay)?|ок(ей)?|да|нет|yes|no|ага|угу|thx|спасибо|готово|done|/\S+|\+\d+)\s*$",
    re.IGNORECASE,
)
_MAX_TITLE_WORDS = 8
_MAX_TITLE_CHARS = 48


def derive_title(prompt: str) -> str:
    """A short noun-phrase title from the user's message — first meaningful line."""
    # First non-empty line, stripped of markdown/quote noise.
    line = ""
    for raw in prompt.splitlines():
        s = raw.strip().lstrip("#>*-•").strip()
        if s:
            line = s
            break
    line = re.sub(r"\s+", " ", line)
    words = line.split(" ")
    title = " ".join(words[:_MAX_TITLE_WORDS])
    if len(title) > _MAX_TITLE_CHARS:
        title = title[:_MAX_TITLE_CHARS].rstrip() + "…"
    return title or "Steering"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    prompt = (payload.get("prompt") or "").strip()
    if not prompt or _TRIVIAL.match(prompt):
        return 0

    title = derive_title(prompt)
    directive = (
        "📍 Chat navigation (UserPromptSubmit auto-nav): near the START of this turn, "
        "before substantive tool use, call mcp__ccd_session__mark_chapter to register "
        f"this user message in the chat table-of-contents. Suggested title: \"{title}\" "
        "(refine to a short noun phrase if it better captures the ask; set a one-line "
        "summary). Mark exactly once per user message. Skip only if this turn is a pure "
        "ack with no new task. This keeps every prompt/steering navigable by default."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": directive,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # pragma: no cover — never block the user's turn
        sys.exit(0)
