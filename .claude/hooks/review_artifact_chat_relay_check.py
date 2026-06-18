#!/usr/bin/env python3
r"""review_artifact_chat_relay_check — Claude Code Stop hook (RCA 2026-06-17).

Owner steering: «я не вижу в чате ничего на ревью» — the agent prepared review
deliverables (READY_*.md fixes, DIAGNOSTIC/verdict reports) and surfaced only
their FILE PATHS, not their CONTENT. The owner cannot review a path; the review
content must reach the chat in the same turn (parallel to §Orchestrator subagent
tracker relay + §Review-subagent relay extension — those cover SUBAGENT verdicts;
this covers PREPARED ARTIFACT files the agent itself wrote).

Detection is on the FINAL assistant message text (reliable regardless of how the
file was written — Write/Edit tool OR an external python/bash script the tool_use
view can't see): if the final message REFERENCES a review artifact by filename
(READY_*.md / *diagnostic*.md / *verdict*.md / *review*.md) but contains NO
surfaced content (no ``` code-fence AND no markdown table), the review content
was not relayed.

Exit codes:
  0 — N/A (no review-artifact reference / not substantial / content present /
      ACK / stop_hook_active) OR PHASE1_WARN staged-rollback
  2 — BLOCK: review artifact referenced by path but its content not surfaced

Override: REVIEW_ARTIFACT_RELAY_ACK="<reason >=12 chars>" (artifact referenced
but legitimately not for owner review — e.g. internal log pointer).
Staged rollback to WARN: REVIEW_ARTIFACT_RELAY_PHASE1_WARN=1
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ACK_ENV = "REVIEW_ARTIFACT_RELAY_ACK"
ACK_MIN_CHARS = 12
PHASE1_WARN_ENV = "REVIEW_ARTIFACT_RELAY_PHASE1_WARN"
MIN_SUBSTANTIAL_WORDS = 200
_LOOKBACK = 6

# Review-artifact filename references in the final message.
REVIEW_REF_RE = re.compile(
    r"\b(?:READY_[A-Za-z0-9_\-]+\.md"
    r"|[A-Za-z0-9_\-]*diagnostic[A-Za-z0-9_\-]*\.md"
    r"|[A-Za-z0-9_\-]*verdict[A-Za-z0-9_\-]*\.md"
    r"|[A-Za-z0-9_\-]*review[A-Za-z0-9_\-]*\.md)\b",
    re.IGNORECASE,
)
# Content surfaced = a fenced code block OR a markdown table row.
CODE_FENCE_RE = re.compile(r"```")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)


def _read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _iter_assistant(transcript_path: str):
    if not transcript_path:
        return
    p = Path(transcript_path)
    try:
        if not p.exists():
            return
        lines = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    except OSError:
        return
    seen = 0
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message") or entry
        role = entry.get("role") or (msg.get("role") if isinstance(msg, dict) else None) or entry.get("type")
        if role != "assistant":
            continue
        seen += 1
        content = msg.get("content") if isinstance(msg, dict) else None
        text_parts = []
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    text_parts.append(c.get("text", ""))
        elif isinstance(content, str):
            text_parts.append(content)
        yield "\n".join(text_parts)
        if seen >= _LOOKBACK:
            break


def _last_assistant_text(transcript_path: str) -> str:
    for text in _iter_assistant(transcript_path):
        if text.strip():
            return text
    return ""


def _is_substantial(text: str) -> bool:
    if not text:
        return False
    if CODE_FENCE_RE.search(text) or TABLE_ROW_RE.search(text):
        return True
    return len(text.split()) >= MIN_SUBSTANTIAL_WORDS


def _content_surfaced(text: str) -> bool:
    """Heuristic: review content is present if the message has a fenced code block
    OR at least one markdown table row (review artifacts are tables/code/diffs)."""
    return bool(CODE_FENCE_RE.search(text) or TABLE_ROW_RE.search(text))


def main() -> int:
    payload = _read_payload()
    if payload.get("stop_hook_active"):
        return 0  # avoid infinite Stop loop (Claude Code contract)

    ack = os.environ.get(ACK_ENV, "")
    if len(ack.strip()) >= ACK_MIN_CHARS:
        return 0

    transcript_path = payload.get("transcript_path", "")
    last_msg = _last_assistant_text(transcript_path)
    if not _is_substantial(last_msg):
        return 0

    refs = REVIEW_REF_RE.findall(last_msg)
    if not refs:
        return 0  # N/A — no review-artifact reference this turn

    if _content_surfaced(last_msg):
        return 0  # PASS — owner sees content (table/code-fence present)

    warn_only = os.environ.get(PHASE1_WARN_ENV) == "1"
    sample = sorted(set(m.lower() for m in refs))[:3]
    msg = (
        "\n[review-artifact-relay] REVIEW-КОНТЕНТ НЕ ПОКАЗАН ВЛАДЕЛЬЦУ (RCA 2026-06-17)\n"
        "  Финальный ответ ссылается на review-артефакт(ы) путём: " + ", ".join(sample) + "\n"
        "  — но НЕ содержит самого контента (нет ``` code-fence и нет markdown-таблицы).\n\n"
        "  Владелец не может ревьюить путь к файлу. Per AGENTS.md (relay contract):\n"
        "  вставь в ответ САМ контент артефакта — diff/таблицу/before-after — а не только ссылку.\n"
        "  Override (артефакт упомянут, но НЕ для owner-ревью — напр. внутренний лог):\n"
        f'    export {ACK_ENV}="<причина >={ACK_MIN_CHARS} симв>"\n'
    )
    if warn_only:
        sys.stderr.write(msg + "\n  [PHASE1_WARN] не блокирую (staged rollback).\n")
        return 0
    sys.stderr.write(msg)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open — a hook bug must never brick a turn
