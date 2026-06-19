#!/usr/bin/env python3
r"""Expected output announce check — Claude Code PreToolUse hook.

Closes RCA 2026-04-27 incident-expected-output-3rd-recurrence (3 рецидива за 4 дня:
24 Apr amoCRM 1127 LOC без announce; 26 Apr fragmented chat без announce;
27 Apr scenarium 32 таблиц без announce). Declarative AGENTS.md §Expected output
table gate (RCA 2026-04-24) не enforce'ится без mechanical layer — agent под
нагрузкой пропускает announce-step, owner steering rate растёт.

Behavior (PreToolUse event для Write/Edit):
- Reads stdin JSON payload from Claude Code PreToolUse event.
- Extracts tool_name (Write / Edit / NotebookEdit) + tool_input.file_path.
- If file_path matches protected analysis-artefact paths (regex below):
  - Reads transcript_path JSONL.
  - Parses last 10 assistant text messages.
  - Searches each for regex `^##\s*(Expected output|Ожидаемая структура|Ожидаемый результат|Expected result)`
    (case-insensitive, multiline).
  - If no match → exit 2 + stderr block message back to agent.
- Else (file_path doesn't match) → exit 0 (rule not applicable).

Allowlist: protected paths regex covers analysis artefacts where missing announce
caused recurrences:
  1. <internal-folder>/jtbd-scenarium/**.md
  2. <internal-folder>/rca/**.md
  3. <internal-folder>/ai.incidents.md
  4. **/scenarium/**.md (any client/project scenarium folder)
  5. Any markdown file Edit'ed in <internal-folder>/clients/all-clients/**/projects/**
  6. .agents/agents/*.md (subagent definitions — RCA 2026-05-13 G08 closure)
  7. .agents/skills/*/SKILL.md (skill definitions — RCA 2026-05-13 G08 closure)

Universal client policy: this hook fires for ANY client (Rick.ai, advising clients,
any new client added later), no hardcoded alias. Detection by path pattern, not by
client identity. Same policy applies to agent/skill creation: any new subagent or
skill in any session must announce expected structure (frontmatter shape, sections,
skill chain) before Write/Edit lands.

Exit codes:
  0 = pass (announce found OR rule not applicable)
  2 = block (announce missing on protected path — message to stderr)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Lookback window for assistant messages — counts ALL assistant text messages
# back from current tool call. Each tool_result counts as a message in transcript,
# so multi-tool-call autonomous stages (Ralph loop, @auto) easily span 15-25
# messages between announce and protected Write. 10 was too aggressive (RCA
# 2026-05-24 — 5 false-positive blocks in one autonomous session of C1+C4 skill
# extensions where announce was 12-18 messages back due to bash/read tool calls).
# 30 covers typical autonomous Ralph loop stage without losing protection against
# the recurring class «scenarium without announce» (RCA 2026-04-24/26/27).
ASSISTANT_LOOKBACK = 30

# Regex matching announce header in the agent's own chat message.
# Multiline so `^` matches line start anywhere in the message body.
ANNOUNCE_PATTERN = re.compile(
    r"^\s*##\s*(Expected\s+output|Ожидаемая\s+структура|Ожидаемый\s+результат|Expected\s+result)",
    re.IGNORECASE | re.MULTILINE,
)

# Protected paths — analysis artefacts where missing announce caused 3 recurrences.
# Universal across clients: detection by path pattern, no hardcoded alias.
PROTECTED_PATH_PATTERNS = [
    re.compile(r"\[todo\s*·\s*incidents\]/jtbd-scenarium/.+\.md$"),
    re.compile(r"\[todo\s*·\s*incidents\]/rca/.+\.md$"),
    re.compile(r"\[todo\s*·\s*incidents\]/ai\.incidents\.md$"),
    re.compile(r"/scenarium/.+\.md$"),
    re.compile(r"\[rick\.ai\]/clients/all-clients/[^/]+/projects/.+\.md$"),
    # RCA 2026-05-13 G08 closure: subagent + skill creation must announce too.
    # Universal policy: any new agent/skill in any session needs Expected output
    # block describing frontmatter shape, sections, skill chain — owner can review
    # design BEFORE 100+ LOC of agent/skill markdown lands.
    re.compile(r"\.agents/agents/[^/]+\.md$"),
    re.compile(r"\.agents/skills/[^/]+/SKILL\.md$"),
]

# Tool names that perform writes large enough to require announce.
# NotebookEdit also covers Jupyter cell rewrites (analysis artefacts often live there).
PROTECTED_TOOLS = {"Write", "Edit", "NotebookEdit"}


def path_is_protected(file_path: str) -> bool:
    """Return True if file_path matches any protected analysis-artefact pattern."""
    if not file_path:
        return False
    for pattern in PROTECTED_PATH_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def read_recent_assistant_texts(transcript_path: Path, limit: int = ASSISTANT_LOOKBACK) -> list[str]:
    """Return list of last `limit` assistant text messages from JSONL transcript."""
    texts: list[str] = []
    with transcript_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message") or {}
            content = msg.get("content")
            if isinstance(content, list):
                parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                if parts:
                    texts.append("\n".join(parts))
            elif isinstance(content, str):
                texts.append(content)
    return texts[-limit:]


def announce_present(texts: list[str]) -> bool:
    """Return True if ANY of the last assistant texts contains the announce header."""
    for text in texts:
        if ANNOUNCE_PATTERN.search(text):
            return True
    return False


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"expected-output-announce-check: cannot parse stdin JSON ({exc}); skipping", file=sys.stderr)
        return 0

    tool_name = payload.get("tool_name") or ""
    if tool_name not in PROTECTED_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""

    if not path_is_protected(file_path):
        # Path not protected — rule not applicable, allow Write/Edit through.
        return 0

    transcript = payload.get("transcript_path")
    if not transcript:
        # No transcript context (e.g., dry-run). Fail open with warning, do not block.
        print(
            "expected-output-announce-check: no transcript_path in payload; allowing Write but flagging.",
            file=sys.stderr,
        )
        return 0

    path = Path(transcript)
    if not path.exists():
        print(
            f"expected-output-announce-check: transcript path missing ({transcript}); allowing Write.",
            file=sys.stderr,
        )
        return 0

    texts = read_recent_assistant_texts(path, ASSISTANT_LOOKBACK)
    if announce_present(texts):
        print(
            f"expected-output-announce-check: PASS — announce header found in last {len(texts)} assistant messages.",
            file=sys.stderr,
        )
        return 0

    block_message = (
        f"expected-output-announce-check: BLOCK — Write/Edit на protected analysis path "
        f"({file_path}) без предварительного announce.\n"
        f"\n"
        f"Перед Write/Edit в analysis artefact (jtbd-scenarium / rca / incidents / client projects) "
        f"агент ОБЯЗАН выписать в чат блок начинающийся с заголовка '## Expected output' "
        f"(или 'Ожидаемая структура' / 'Ожидаемый результат') в одном из последних "
        f"{ASSISTANT_LOOKBACK} assistant messages.\n"
        f"\n"
        f"Блок должен описывать структуру предстоящего артефакта:\n"
        f"  - какие колонки таблицы (поля по горизонтали);\n"
        f"  - какие примеры строк (по вертикали);\n"
        f"  - сколько таблиц всего (правило 1-table-default);\n"
        f"  - какие headers и subsections.\n"
        f"\n"
        f"Источник правила: AGENTS.md §Expected output table gate (RCA 2026-04-24 + расширение "
        f"RCA 2026-04-27 mechanical enforcement). 3 рецидива за 4 дня (24/26/27 апреля) "
        f"закрыты этим PreToolUse hook'ом.\n"
        f"\n"
        f"Recovery: напиши '## Expected output' блок в следующем сообщении, затем повтори Write/Edit."
    )
    print(block_message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
