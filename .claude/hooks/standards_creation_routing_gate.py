#!/usr/bin/env python3
r"""Standards-creation routing gate — Claude Code PreToolUse hook.

Closes RCA 2026-05-17 incident "Standard создан как doc в external docs/ минуя
0-standards-create-update-review" — 9-й рецидив системного класса
"declarative [ACTIVE] skill-gate без mechanical PreToolUse hook → агент под
нагрузкой пропускает". Прецеденты того же класса закрывались хуками
git_dirty_count_gate.py / expected_output_announce_check.py /
untracked_critical_files_gate.py. Standards-creation был слепым пятном:
из 21 хука НИ ОДИН не детектил "Write target = *standard*.md".

Behavior (PreToolUse event для Write/Edit/NotebookEdit):
- Reads stdin JSON payload from Claude Code PreToolUse event.
- Extracts tool_name + tool_input.file_path + content/new_string.
- Detects "standard-creation intent":
    (a) filename basename matches  (?i).*standard.*\.md$
        (минус safe-list: ai.incidents.md / ai.legacy.md / changelog.md /
         AGENTS.md / CLAUDE.md / CODEX.md / *_spec.md / сами guard-скиллы)
    (b) ИЛИ content имеет frontmatter `type: standard` / `standard_id:` /
        top-heading `^#\s+.*\bStandard\b`.
- Если intent НЕ обнаружен → exit 0 (rule not applicable).
- Если intent обнаружен → PASS только если ОДНО из:
    * в последних N assistant messages (text ИЛИ Skill tool_use) есть
      признак вызова `0-standards-create-update-review` /
      `0-document-creation-guard`;
    * env STANDARDS_GATE_ACK задан (≥12 значимых символов reason);
    * target — сам infrastructure-файл правила (skill/hook/standard о правиле).
  Иначе → exit 2 + stderr routing message.

Side effect (best-effort, never blocks): при срабатывании пишет строку в
reasoning log через scripts/reasoning_log/append.py — закрывает второй геп
того же инцидента (substantial standard-decision не попадал в reasoning log).
Failure любого best-effort шага → stderr only, основной verdict не меняется.

Universal client policy: срабатывание по контенту/имени файла, НЕ по client
identity. Работает для любого нового клиента/проекта/submodule без правки кода.

Exit codes:
  0 = pass (no standard-intent OR skill-ack present OR override OR infra file)
  2 = block (standard-intent без skill-ack — routing message to stderr)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ASSISTANT_LOOKBACK = 12
MIN_ACK_LEN = 12

# Standard-intent by filename: basename contains "standard" + markdown-ish ext.
# MINOR FN fix (code-review 2026-05-17): was .md-only — a standard saved as
# .markdown/.mdx/.txt escaped entirely. Broadened.
FILENAME_STANDARD = re.compile(r"(?i).*standard.*\.(md|markdown|mdx|txt)$")

# Standard-intent by content. Frontmatter signals are strong (Task Master
# template always carries them). MINOR FP fix (code-review 2026-05-17): the
# bare `^#\s+.*\bStandard\b` heading blocked legit non-standard docs like
# "# Coding Standard Notes". Tightened to the canonical numbered-standard
# heading shape ("# 5.46 ... Standard ...") so prose headings don't trip it;
# the loose case is covered by the filename signal anyway.
CONTENT_STANDARD_PATTERNS = [
    re.compile(r"^\s*type:\s*standard\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*standard_id:\s*[0-9]", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*logical_id:\s*standard:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#\s+\d+\.\d+[\s.].*\bStandard\b", re.MULTILINE),
]

# Filenames that legitimately contain "standard" but are NOT new governance
# standards (narrative / governance / infra / engineering spec convention).
SAFE_BASENAMES = {
    "ai.incidents.md",
    "ai.legacy.md",
    "changelog.md",
    "agents.md",
    "claude.md",
    "codex.md",
    "readme.md",
}

# Infrastructure files that DEFINE the rule itself — editing them must not be
# gated by the rule (chicken-and-egg). Substring match on normalized path.
RULE_INFRA_SUBSTRINGS = [
    ".agents/skills/0-standards-create-update-review/",
    ".agents/skills/0-document-creation-guard/",
    ".claude/hooks/standards_creation_routing_gate.py",
    "/standards .md]/0. core standards/0.1 registry standard",
    "/standards .md]/0. core standards/0.0 task master",
]

# Evidence that the standards/doc-guard skill was actually engaged this stage.
SKILL_ACK_TOKENS = [
    "0-standards-create-update-review",
    "0-document-creation-guard",
    "standards-create-update-review",
    "document-creation-guard",
]

PROTECTED_TOOLS = {"Write", "Edit", "NotebookEdit", "Bash"}

# Bash patterns that effectively write to disk (RCA 2026-05-25 hook-bypass closure):
# subagent bypassed gate by using `python -c 'Path(...).write_text(...)'` against a
# standard file. Closes the 10-th recidivism of declarative-without-mechanical-hook
# class (this hook itself was the 9th fix). Universal — works for any file path.
BASH_WRITE_PATTERN = re.compile(r"""(?ix)                              # case-insensitive, verbose
    (?:                                    # one of these write operations:
        >\s*['\"]?                         #   shell redirect:  >  or  >>
        |                                  #
        tee\s+(?:-a\s+)?                   #   tee / tee -a
        |                                  #
        \.\s*write_(?:text|bytes)\s*\(     #   Python Path(...).write_text/bytes(
        |                                  #
        open\s*\([^)]+,\s*['\"]\s*[aw]     #   Python open(..., 'w' / 'a')
        |                                  #
        cp\s+                              #   cp source dest  (if dest matches)
        |                                  #
        mv\s+                              #   mv source dest
    )
    """)

# Detect file paths in Bash commands matching *standard*.md pattern
BASH_STANDARD_PATH_PATTERN = re.compile(r"(?i)([^\s'\"]*standard[^\s'\"]*\.(?:md|markdown|mdx|txt))")


def normalize(p: str) -> str:
    return (p or "").replace("\\", "/").lower()


def basename(p: str) -> str:
    return normalize(p).rsplit("/", 1)[-1]


def is_safe_or_infra(file_path: str) -> bool:
    bn = basename(file_path)
    if bn in SAFE_BASENAMES:
        return True
    # Engineering-spec naming convention (AppCraft data/docs/*_spec.md) — the
    # honest disposition for non-governance engineering docs; not gated.
    if bn.endswith("_spec.md"):
        return True
    norm = normalize(file_path)
    for sub in RULE_INFRA_SUBSTRINGS:
        if sub in norm:
            return True
    return False


def content_of(tool_input: dict) -> str:
    for key in ("content", "new_string", "new_str", "newText"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def has_standard_intent(file_path: str, content: str) -> tuple[bool, str]:
    bn = basename(file_path)
    if FILENAME_STANDARD.match(bn):
        return True, f"filename '{bn}' matches *standard*.md"
    for pat in CONTENT_STANDARD_PATTERNS:
        if pat.search(content or ""):
            return True, f"content matches standard marker /{pat.pattern[:40]}/"
    return False, ""


def read_recent_tool_uses(transcript_path: Path, limit: int) -> list[dict]:
    """Return last `limit` assistant *tool_use* blocks (name + input only).

    MAJOR fail-open fix (code-review 2026-05-17): the previous implementation
    flattened BOTH text and tool_use into one string list and `skill_ack_present`
    did a naive substring scan. That meant merely *mentioning* the skill name in
    prose — or a *negated* mention ("I should NOT call 0-document-creation-guard")
    — passed the gate. The hook's own block message + any review discussing it by
    name trivially bypassed it. Ack is now ONLY a genuine Skill/Task/Agent
    tool_use that names the standards / doc-guard skill — text is ignored
    entirely, so negation/discussion can no longer fail the gate open.
    """
    tool_uses: list[dict] = []
    try:
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
                if not isinstance(content, list):
                    continue
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        tool_uses.append(
                            {
                                "name": str(c.get("name", "")),
                                "input": c.get("input", {}) if isinstance(c.get("input"), dict) else {},
                            }
                        )
    except OSError:
        return []
    return tool_uses[-(limit * 6) :]


def skill_ack_present(tool_uses: list[dict]) -> bool:
    """True iff a genuine Skill/Task/Agent tool_use invoked the standards skill.

    Strict by design — matches AGENTS.md §Skill invocation contract `[ACTIVE]`
    semantics (an [ACTIVE] skill MUST be invoked via the Skill tool, not merely
    described). Free-text mentions never count → no fail-open via prose/negation.
    """
    for tu in tool_uses:
        name = tu["name"]
        inp = tu["input"]
        if name == "Skill":
            skill = str(inp.get("skill", "")).lower()
            if any(tok in skill for tok in SKILL_ACK_TOKENS):
                return True
        elif name in ("Task", "Agent"):
            # A delegated subagent explicitly told to run the standards skill.
            blob = json.dumps(inp, ensure_ascii=False).lower()
            if any(tok in blob for tok in SKILL_ACK_TOKENS):
                return True
    return False


def env_ack() -> str | None:
    val = (os.environ.get("STANDARDS_GATE_ACK") or "").strip()
    if len(val) >= MIN_ACK_LEN:
        return val
    return None


def best_effort_reasoning_log(file_path: str, reason: str, blocked: bool) -> None:
    """Append a reasoning-log row so the standard-decision is captured.

    Closes the second gap of RCA 2026-05-17 (substantial standard-decision was
    never logged because in-turn append.py is declarative). Never blocks.
    """
    try:
        repo = Path(__file__).resolve().parents[2]
        append = repo / "scripts" / "reasoning_log" / "append.py"
        if not append.exists():
            return
        subprocess.run(
            [
                sys.executable,
                str(append),
                "--skill",
                "standards_creation_routing_gate",
                "--stage",
                "design",
                "--decision",
                ("BLOCK standard-creation без skill-ack" if blocked else "PASS standard-intent (skill-ack present)"),
                "--evidence",
                f"{file_path} :: {reason}",
                "--gap",
                ("G — standard создаётся минуя 0-standards-create-update-review" if blocked else "—"),
                "--blocking",
                ("AGENTS.md §Skill invocation contract + RCA 2026-05-17" if blocked else "—"),
                "--outcome",
                ("blocked" if blocked else "in-progress"),
                "--quiet",
            ],
            timeout=5,
            capture_output=True,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, must never raise
        print(f"standards-gate: reasoning-log append skipped ({exc})", file=sys.stderr)


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"standards-gate: cannot parse stdin JSON ({exc}); skipping", file=sys.stderr)
        return 0

    tool_name = payload.get("tool_name") or ""
    if tool_name not in PROTECTED_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    content = content_of(tool_input)

    # RCA 2026-05-25 hook-bypass closure: Bash commands writing to *standard*.md
    # paths (e.g. `python -c 'Path("...standard.md").write_text(...)'`) previously
    # escaped the gate because PROTECTED_TOOLS was Write/Edit/NotebookEdit only.
    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        if not command:
            return 0
        if not BASH_WRITE_PATTERN.search(command):
            return 0  # not a write operation
        path_match = BASH_STANDARD_PATH_PATTERN.search(command)
        if not path_match:
            return 0  # doesn't touch a *standard*.md path
        # Inflate file_path so downstream logic (safe-list, intent) applies
        file_path = path_match.group(1)
        # No content available for Bash — rely on filename-based intent
        if is_safe_or_infra(file_path):
            return 0
        intent, reason = has_standard_intent(file_path, "")
        if not intent:
            return 0
        # Bash bypass intent confirmed — fall through to skill-ack check
        # (with explicit reason tag so reasoning log captures it)
        reason = f"BASH-WRITE bypass attempt: {reason}"
    else:
        if is_safe_or_infra(file_path):
            return 0

        intent, reason = has_standard_intent(file_path, content)
        if not intent:
            return 0

    # Strong-signal escalation: external submodule docs/ + "standard" in name =
    # exactly the RCA 2026-05-17 shape. Logged with higher visibility.
    norm = normalize(file_path)
    external_docs = any(s in norm for s in ("rick-appcarft/", "<internal-folder>/", "/data/docs/"))

    ack = env_ack()
    if ack:
        print(
            f"standards-gate: PASS — STANDARDS_GATE_ACK override ('{ack[:60]}'). " f"Intent: {reason}.",
            file=sys.stderr,
        )
        best_effort_reasoning_log(file_path, f"{reason} | override={ack[:40]}", blocked=False)
        return 0

    transcript = payload.get("transcript_path")
    if transcript and Path(transcript).exists():
        tool_uses = read_recent_tool_uses(Path(transcript), ASSISTANT_LOOKBACK)
        if skill_ack_present(tool_uses):
            print(
                f"standards-gate: PASS — genuine Skill/Task tool_use for "
                f"0-standards-create-update-review / 0-document-creation-guard "
                f"found in recent tool calls. Intent: {reason}.",
                file=sys.stderr,
            )
            best_effort_reasoning_log(file_path, f"{reason} | skill-ack", blocked=False)
            return 0

    best_effort_reasoning_log(file_path, reason, blocked=True)
    block_message = (
        f"standards-creation-routing-gate: BLOCK — Write/Edit выглядит как "
        f"создание/правка СТАНДАРТА без прохождения governance-скилла.\n"
        f"\n"
        f"Target: {file_path}\n"
        f"Intent: {reason}\n"
        + (
            f"⚠️  STRONG SIGNAL — external submodule docs/ (это форма RCA 2026-05-17:\n"
            f"   standard создан как doc в data/docs/ минуя процесс).\n"
            if external_docs
            else ""
        )
        + f"\n"
        f"Стандарт нельзя создавать как обычный документ. Обязательно пройти "
        f"`0-standards-create-update-review` (Skill tool):\n"
        f"  1. Duplicate-check + ID Allocator (rg standard_id среди Active)\n"
        f"  2. document-creation-guard §0 Intent Router (кому документ / по какой задаче)\n"
        f"  3. Task Master шаблон (frontmatter type:standard, лицензия, JTBD, 5W+H)\n"
        f"  4. Атомарная регистрация в Registry 0.1\n"
        f"  5. Save-then-show non-blocking review в защитной ветке pr-*\n"
        f"\n"
        f"Если это НЕ governance-стандарт, а engineering spec — переименуй в "
        f"`*_spec.md` (конвенция AppCraft data/docs/woocommerce_smokeway_spec.md) "
        f"— тогда gate не сработает.\n"
        f"\n"
        f"Источник: AGENTS.md §Skill invocation contract + RCA 2026-05-17 "
        f"(9-й рецидив declarative-without-mechanical-hook).\n"
        f"\n"
        f"Recovery:\n"
        f"  A. Вызови Skill `0-standards-create-update-review`, затем повтори Write; ИЛИ\n"
        f"  B. Переименуй в `*_spec.md` если это engineering doc, не governance standard; ИЛИ\n"
        f'  C. export STANDARDS_GATE_ACK="<причина ≥12 симв. почему gate неприменим>" '
        f"и повтори (явный осознанный override)."
    )
    print(block_message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
