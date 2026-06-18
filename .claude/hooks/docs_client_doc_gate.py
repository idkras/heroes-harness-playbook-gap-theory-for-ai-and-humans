#!/usr/bin/env python3
r"""docs/ client-doc routing gate — Claude Code PreToolUse hook.

Closes the `docs/` blind spot identified by owner 2026-05-19 ("ссылку что ты
даёшь docs/<client>-... не должна тут лежать, настрой хук когда записываешь в
/docs чтобы запускался скилл, прочитай стандарт, в docs больше ничего не было").

Same systemic class as standards_creation_routing_gate.py / expected_output_
announce_check.py: a declarative [ACTIVE] skill-gate (`0-document-creation-guard`
§0 Intent Router, RCA 2026-05-08 `docs/zoho-...-<client>-ac.md`) had NO
mechanical PreToolUse backstop → агент под нагрузкой пишет client/teammate doc
в repo-root `docs/` минуя Intent Router. `standards_creation_routing_gate.py`
ловит только *standard*-intent; generic client/project docs в `docs/` остаются
слепым пятном.

Canon (CLAUDE.md §Document Creation Guard §0 Intent Router + Standard 4.6
`<standard-ref>):
repo-root `docs/` РАЗРЕШЁН только для whole-team governance/onboarding из
whitelist. Любой client/teammate/project документ обязан лежать в
`<internal-folder>/clients/all-clients/{client-domain}/projects/{bead}/`.

Behavior (PreToolUse Write/Edit/NotebookEdit):
  - parse stdin JSON → tool_name + tool_input.file_path + content
  - resolve target; applies ONLY if target real-path is inside repo-root
    `docs/` (NOT `<internal-folder>/.../docs/`, NOT submodule `*/data/docs/`, NOT
    `.agents/.../docs`, NOT `<standard-ref>) — universal, no client hardcode
  - PASS if basename ∈ WHITELIST and file is directly in `docs/` root
    (architecture-decisions.md / cursor-onboarding.md /
     cursor-adoption-explanation.md / README.md — recurring governance edits)
  - PASS if env DOCS_GATE_ACK set (≥12 chars reason — rare legit governance add)
  - PASS if a genuine Skill tool_use of `0-document-creation-guard` is present
    in recent assistant tool calls (Intent Router was actually run)
  - else BLOCK (exit 2) with routing message: read Standard 4.6 + run
    `0-document-creation-guard` §0 Intent Router + route to client folder

Side effect (best-effort, never blocks): append a reasoning-log row.

Exit codes:
  0 = pass (not docs/ target | whitelist root file | env-ack | skill-ack)
  2 = block (non-whitelist write into repo-root docs/ without Intent Router)
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

PROTECTED_TOOLS = {"Write", "Edit", "NotebookEdit"}

# Canonical whitelist — CLAUDE.md §Document Creation Guard §0 Intent Router
# (whole-team governance/onboarding only, repo-root docs/ directly).
WHITELIST_BASENAMES = {
    "architecture-decisions.md",
    "cursor-onboarding.md",
    "cursor-adoption-explanation.md",
    "readme.md",
}

# Evidence that the doc-guard Intent Router was actually engaged this stage.
SKILL_ACK_TOKENS = [
    "0-document-creation-guard",
    "document-creation-guard",
]

# Infra files that DEFINE the rule — editing them must not be gated (chicken
# and egg). Substring match on normalized path.
RULE_INFRA_SUBSTRINGS = [
    ".agents/skills/0-document-creation-guard/",
    ".claude/hooks/docs_client_doc_gate.py",
]


def normalize(p: str) -> str:
    return (p or "").replace("\\", "/")


def basename(p: str) -> str:
    return normalize(p).rsplit("/", 1)[-1].lower()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def real(p: str) -> str:
    try:
        return os.path.realpath(p)
    except OSError:
        return os.path.abspath(p)


def is_repo_root_docs(file_path: str) -> bool:
    """True iff target resolves inside `<repo>/docs/` (NOT client/.../docs/,
    NOT submodule data/docs/, NOT <internal-folder>, NOT .agents)."""
    if not file_path:
        return False
    repo = repo_root()
    docs_root = real(str(repo / "docs"))
    # Resolve target: absolute as-is, else relative to repo root.
    raw = file_path
    if not os.path.isabs(raw):
        raw = str(repo / raw)
    tgt = real(raw)
    # Must be inside repo-root docs/ exactly (prefix match on dir boundary).
    return tgt == docs_root or tgt.startswith(docs_root + os.sep)


def is_whitelisted_root_file(file_path: str) -> bool:
    """True iff file is DIRECTLY in repo-root docs/ AND basename whitelisted."""
    repo = repo_root()
    docs_root = real(str(repo / "docs"))
    raw = file_path if os.path.isabs(file_path) else str(repo / file_path)
    tgt = real(raw)
    parent = os.path.dirname(tgt)
    if parent != docs_root:
        return False  # in a subdir of docs/ → not whitelisted
    return basename(file_path) in WHITELIST_BASENAMES


def is_rule_infra(file_path: str) -> bool:
    norm = normalize(file_path).lower()
    return any(sub in norm for sub in RULE_INFRA_SUBSTRINGS)


def content_of(tool_input: dict) -> str:
    for key in ("content", "new_string", "new_str", "newText"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def detect_client_intent(file_path: str, content: str) -> str:
    """Best-effort hint of WHY this is misrouted (for the block message)."""
    bn = basename(file_path)
    # Filename carries a client-domain-ish slug (kebab + .md, not whitelist).
    if re.match(r"^[a-z0-9]+(?:-[a-z0-9]+){1,}\.md$", bn):
        return f"filename '{bn}' looks like a client/project slug, not governance"
    blob = (content or "")[:4000].lower()
    for marker in (
        "client",
        "клиент",
        "клиента",
        "diagnostic",
        "диагностик",
        "checklist клиент",
        "для виталия",
        "для анны",
        "handoff",
        "<internal-folder>/clients",
        "company alias",
        "client_alias",
    ):
        if marker in blob:
            return f"content mentions '{marker}' — looks client/teammate-facing"
    return "non-whitelist file in repo-root docs/ (governance whitelist only)"


def read_recent_tool_uses(transcript_path: Path, limit: int) -> list[dict]:
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
    """True iff a genuine Skill/Task/Agent tool_use ran 0-document-creation-guard.

    Strict — matches AGENTS.md §Skill invocation contract [ACTIVE]. Free-text
    mentions never count (no fail-open via prose/negation/this hook's message).
    """
    for tu in tool_uses:
        name = tu["name"]
        inp = tu["input"]
        if name == "Skill":
            skill = str(inp.get("skill", "")).lower()
            if any(tok in skill for tok in SKILL_ACK_TOKENS):
                return True
        elif name in ("Task", "Agent"):
            blob = json.dumps(inp, ensure_ascii=False).lower()
            if any(tok in blob for tok in SKILL_ACK_TOKENS):
                return True
    return False


def env_ack() -> str | None:
    val = (os.environ.get("DOCS_GATE_ACK") or "").strip()
    if len(val) >= MIN_ACK_LEN:
        return val
    return None


def best_effort_reasoning_log(file_path: str, reason: str, blocked: bool) -> None:
    try:
        repo = repo_root()
        append = repo / "scripts" / "reasoning_log" / "append.py"
        if not append.exists():
            return
        subprocess.run(
            [
                sys.executable,
                str(append),
                "--skill",
                "docs_client_doc_gate",
                "--stage",
                "design",
                "--decision",
                (
                    "BLOCK docs/ write — non-whitelist, Intent Router skipped"
                    if blocked
                    else "PASS docs/ write (whitelist/ack)"
                ),
                "--evidence",
                f"{file_path} :: {reason}",
                "--gap",
                (
                    "G — client/teammate doc routed to repo-root docs/ minus "
                    "0-document-creation-guard §0 Intent Router"
                    if blocked
                    else "—"
                ),
                "--blocking",
                (
                    "CLAUDE.md §Document Creation Guard + Standard 4.6 + " "RCA 2026-05-08/2026-05-19"
                    if blocked
                    else "—"
                ),
                "--outcome",
                ("blocked" if blocked else "in-progress"),
                "--quiet",
            ],
            timeout=5,
            capture_output=True,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, must never raise
        print(f"docs-gate: reasoning-log append skipped ({exc})", file=sys.stderr)


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"docs-gate: cannot parse stdin JSON ({exc}); skipping", file=sys.stderr)
        return 0

    tool_name = payload.get("tool_name") or ""
    if tool_name not in PROTECTED_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return 0

    # Applies ONLY to repo-root docs/ (universal, no client hardcode).
    if not is_repo_root_docs(file_path):
        return 0
    if is_rule_infra(file_path):
        return 0
    # Recurring governance edits (ADR log, onboarding) — always free.
    if is_whitelisted_root_file(file_path):
        return 0

    content = content_of(tool_input)
    reason = detect_client_intent(file_path, content)

    ack = env_ack()
    if ack:
        print(
            f"docs-gate: PASS — DOCS_GATE_ACK override ('{ack[:60]}'). " f"Target: {file_path}. {reason}.",
            file=sys.stderr,
        )
        best_effort_reasoning_log(file_path, f"{reason} | override={ack[:40]}", blocked=False)
        return 0

    transcript = payload.get("transcript_path")
    if transcript and Path(transcript).exists():
        tool_uses = read_recent_tool_uses(Path(transcript), ASSISTANT_LOOKBACK)
        if skill_ack_present(tool_uses):
            print(
                "docs-gate: PASS — genuine Skill/Task tool_use for "
                "0-document-creation-guard found in recent tool calls. "
                f"Target: {file_path}.",
                file=sys.stderr,
            )
            best_effort_reasoning_log(file_path, f"{reason} | skill-ack", blocked=False)
            return 0

    best_effort_reasoning_log(file_path, reason, blocked=True)
    rel = file_path
    repo = str(repo_root())
    if rel.startswith(repo):
        rel = rel[len(repo) :].lstrip("/")
    block_message = (
        "docs-client-doc-gate: BLOCK — запись в repo-root `docs/` минуя "
        "Intent Router.\n"
        "\n"
        f"Target: {rel}\n"
        f"Signal: {reason}\n"
        "\n"
        "Канон (CLAUDE.md §Document Creation Guard §0 Intent Router + "
        "Standard 4.6 `<standard-ref>"
        "folder structure standard ...`):\n"
        "repo-root `docs/` РАЗРЕШЁН ТОЛЬКО для whole-team governance/onboarding "
        "из whitelist:\n"
        "  • docs/architecture-decisions.md\n"
        "  • docs/cursor-onboarding.md\n"
        "  • docs/cursor-adoption-explanation.md\n"
        "  • docs/README.md\n"
        "\n"
        "Любой client / teammate / project / отчёт / диагностика / чеклист "
        "документ обязан лежать в:\n"
        "  <internal-folder>/clients/all-clients/{client-domain}/projects/{bead}/...\n"
        "(если задача клиентская) или projects/{project}/ (если "
        "общеплатформенная).\n"
        "\n"
        "Что сделать:\n"
        "  1. Прочитать Standard 4.6 (rickai cursor folder structure) +\n"
        "     запустить Skill `0-document-creation-guard` (§0 Intent Router):\n"
        "     ответить — Кому документ? / По какой задаче-клиенту? / "
        "whole-team?\n"
        "  2. Если client/teammate intent → resolve client-domain + bead, "
        "Write\n"
        "     в <internal-folder>/clients/all-clients/{client-domain}/projects/{bead}/\n"
        "  3. Нет bead → создать через "
        "`1-change-task-and-project-state-via-beads` ДО Write\n"
        "\n"
        "Override (редкая легитимная governance-добавка в whitelist):\n"
        '  export DOCS_GATE_ACK="<причина ≥12 симв. почему whole-team '
        'governance>"\n'
        "\n"
        "RCA-источник: 2026-05-08 (docs/zoho-...-<client>-ac.md) + "
        "2026-05-19 owner steering."
    )
    print(block_message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — never hard-crash the tool call
        print(f"docs-gate: unexpected error, failing open ({exc})", file=sys.stderr)
        sys.exit(0)
