#!/usr/bin/env python3
"""
incidents_to_gepa_trainset.py — конвертирует блоки «Контекст инцидента (для GEPA training data)»
из [todo · incidents]/ai.incidents.md в trainset.jsonl для 2-gepa-prompt-loop.

Каждый инцидент с этим блоком становится одной строкой trainset.jsonl формата:

    {
      "input": "<owner_prompt_verbatim>",
      "additional_context": {
        "chat_jtbd": "...",
        "skills_active": [...],
        "triggers_missed": [...],
        "recurrence_14d": N,
        "cognitive_load_symptom": "..."
      },
      "answer": "<expected_delivery>",
      "feedback": "<actual_failure_mode> + <steering_verbatim>",
      "rubric": [<scoring_rubric_pass_criteria>],
      "target_component": "<target_artifact_for_tuning>",
      "_meta": {
        "incident_date": "YYYY-MM-DD",
        "incident_header": "...",
        "source_offset_line": N
      }
    }

Usage:
    python3 .agents/skills/2-rca-incidents/scripts/incidents_to_gepa_trainset.py \\
      --incidents "[todo · incidents]/ai.incidents.md" \\
      --since 14d \\
      --target-artifact ".agents/skills/X/SKILL.md" \\
      --output "[projects]/gepa-runs/<tag>/trainset.jsonl"

    --since accepts: 14d, 7d, 30d, all (default: all)
    --target-artifact (optional): фильтр — оставить только incident'ы где target_artifact_for_tuning == указанный
    --min-rubric-criteria (default 3): отбросить incident'ы с rubric <N критериев

Exit codes:
    0 — success (>=1 case extracted)
    1 — no incidents matched filter
    2 — parse errors (incident with malformed «Контекст инцидента» block)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

CONTEXT_BLOCK_HEADER = "## Контекст инцидента (для GEPA training data)"
INCIDENT_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b.*$|^##\s+(\d+)\s+(\w+)\s+(\d{4})\s*[—-]?\s*(.*)$")
DATE_LINE_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b\s*[—-]?\s*(.*)$")
# Matches both markdown forms:
#   - **field_name:** value
#   - **field_name**: value
FIELD_RE = re.compile(r"^\s*[-*]\s+\*\*([a-z_][a-z0-9_]*)(?::\*\*|\*\*:)\s*(.*)$", re.IGNORECASE)
RUBRIC_ITEM_RE = re.compile(r"^\s*[-*]\s+(?:✓|✔|\[x\]|\[X\])\s+(.+)$")


@dataclass
class IncidentContext:
    """Распарсенный блок «Контекст инцидента (для GEPA training data)» — 16 полей в 4 группах.

    Расширено с 12 до 16 полей в RCA 2026-05-03 (owner T24): добавлены `original_owner_task`,
    `task_origin_pointer`, `reasoning_log_excerpts`, `failed_attempts_summary`. Поле `trace_pointer`
    переименовано в `reasoning_log_pointer` для согласованности; парсер принимает оба имени для
    backward compat.
    """

    incident_header: str = ""
    incident_date: str = ""
    source_line: int = 0

    # A. Контекст задачи и истории
    original_owner_task: str = ""
    task_origin_pointer: str = ""
    reasoning_log_pointer: str = ""  # alias: trace_pointer
    reasoning_log_excerpts: list[str] = field(default_factory=list)

    # B. Owner intent и failure
    owner_prompt_verbatim: str = ""
    chat_jtbd: str = ""
    expected_delivery: str = ""
    actual_failure_mode: str = ""

    # C. GEPA tuning targets
    target_artifact_for_tuning: str = ""
    steering_verbatim: str = ""
    scoring_rubric_pass_criteria: list[str] = field(default_factory=list)
    cognitive_load_symptom: str = ""

    # D. Triggers и recurrence
    recurrence_count_14d: int = 0
    triggers_that_should_have_fired: list[str] = field(default_factory=list)
    skills_active_at_failure: list[str] = field(default_factory=list)
    failed_attempts_summary: str = ""

    parse_errors: list[str] = field(default_factory=list)

    # 6 required string fields + 1 list (reasoning_log_excerpts ≥3 below)
    REQUIRED_STRING_FIELDS = (
        "original_owner_task",
        "task_origin_pointer",
        "reasoning_log_pointer",
        "owner_prompt_verbatim",
        "chat_jtbd",
        "expected_delivery",
        "actual_failure_mode",
        "target_artifact_for_tuning",
    )

    def is_valid(self, min_rubric: int = 3, min_excerpts: int = 3) -> bool:
        for f in self.REQUIRED_STRING_FIELDS:
            v = getattr(self, f)
            if not v or v.strip() in ("", "TODO", "—", "-", "?"):
                self.parse_errors.append(f"empty required field: {f}")
                return False
        if len(self.scoring_rubric_pass_criteria) < min_rubric:
            self.parse_errors.append(
                f"rubric has {len(self.scoring_rubric_pass_criteria)} criteria, need >= {min_rubric}"
            )
            return False
        if len(self.reasoning_log_excerpts) < min_excerpts:
            self.parse_errors.append(
                f"reasoning_log_excerpts has {len(self.reasoning_log_excerpts)} quotes, "
                f"need >= {min_excerpts} (RCA 2026-05-03 owner T24: «не вижу цитаты из reasoning log»)"
            )
            return False
        if self.target_artifact_for_tuning.strip().lower() in ("unknown", "n/a", "none"):
            self.parse_errors.append("target_artifact_for_tuning is unknown — GEPA cannot tune")
            return False
        if self.original_owner_task.strip() == self.owner_prompt_verbatim.strip():
            self.parse_errors.append(
                "original_owner_task == owner_prompt_verbatim (same text) — these MUST be different "
                "(original = root task from start of chat / bead, prompt = last steering before incident)"
            )
            return False
        # task_origin_pointer must contain at least bead OR project marker
        top = self.task_origin_pointer.lower()
        if not any(marker in top for marker in ("bead", "pr-", ".todo.md", "project", "[bead]", "[project]")):
            self.parse_errors.append(
                "task_origin_pointer missing bead ID or project todo path "
                "(format: '{bead_id} — {title} — [bead](URL); [project](path); [chat](URL)')"
            )
            return False
        return True

    def to_gepa_case(self) -> dict:
        feedback_parts = [self.actual_failure_mode]
        if self.steering_verbatim and self.steering_verbatim.lower() not in ("none", "—", "-"):
            feedback_parts.append(f"OWNER STEERING: {self.steering_verbatim}")
        if self.failed_attempts_summary:
            feedback_parts.append(f"FAILED ATTEMPTS: {self.failed_attempts_summary}")
        return {
            "input": self.owner_prompt_verbatim,
            "additional_context": {
                "original_task": self.original_owner_task,
                "task_origin": self.task_origin_pointer,
                "reasoning_excerpts": list(self.reasoning_log_excerpts),
                "chat_jtbd": self.chat_jtbd,
                "skills_active": self.skills_active_at_failure,
                "triggers_missed": self.triggers_that_should_have_fired,
                "recurrence_14d": self.recurrence_count_14d,
                "cognitive_load_symptom": self.cognitive_load_symptom,
                "failed_attempts": self.failed_attempts_summary,
            },
            "answer": self.expected_delivery,
            "feedback": " | ".join(p for p in feedback_parts if p),
            "rubric": list(self.scoring_rubric_pass_criteria),
            "target_component": self.target_artifact_for_tuning,
            "_meta": {
                "incident_date": self.incident_date,
                "incident_header": self.incident_header,
                "source_line": self.source_line,
                "reasoning_log_pointer": self.reasoning_log_pointer,
            },
        }


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
        return v[1:-1]
    if v.startswith("«") and v.endswith("»") and len(v) >= 2:
        return v[1:-1]
    return v


def _parse_int_recurrence(value: str) -> int:
    m = re.match(r"^\s*(\d+)", value)
    return int(m.group(1)) if m else 0


def _parse_list_field(value: str) -> list[str]:
    """Поле может быть inline списком через запятую или указанием на multi-line."""
    v = value.strip()
    if not v or v in ("—", "-", "none"):
        return []
    parts = [p.strip() for p in re.split(r"[,;]", v) if p.strip()]
    return parts


def parse_incidents_file(path: Path) -> Iterator[IncidentContext]:
    """Итерирует по incident'ам с блоком «Контекст инцидента (для GEPA training data)»."""
    if not path.exists():
        raise FileNotFoundError(f"incidents file not found: {path}")
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    current_incident_header: str = ""
    current_incident_date: str = ""

    i = 0
    while i < len(lines):
        line = lines[i]
        # Track current incident header (## YYYY-MM-DD ... or ## D Mon YYYY ...)
        if line.startswith("## ") and CONTEXT_BLOCK_HEADER not in line:
            m = DATE_LINE_RE.match(line)
            if m:
                current_incident_date = m.group(1)
                current_incident_header = line[3:].strip()
            else:
                # Try free-form header — keep last seen if no date
                free = line[3:].strip()
                if free and not free.startswith("Контекст"):
                    current_incident_header = free
        # Detect context block
        if line.strip() == CONTEXT_BLOCK_HEADER:
            ctx = IncidentContext(
                incident_header=current_incident_header,
                incident_date=current_incident_date,
                source_line=i + 1,
            )
            j = i + 1
            in_rubric = False
            in_excerpts = False
            while j < len(lines):
                inner = lines[j]
                # End of block: next ## header or end (### subheaders are part of block)
                if inner.startswith("## ") and not inner.startswith("### "):
                    break
                if inner.startswith("# "):
                    break
                fm = FIELD_RE.match(inner)
                if fm:
                    in_rubric = False
                    in_excerpts = False
                    field_name = fm.group(1).strip().lower()
                    field_value = fm.group(2).strip()
                    # A. Контекст задачи и истории
                    if field_name == "original_owner_task":
                        ctx.original_owner_task = _strip_quotes(field_value)
                    elif field_name == "task_origin_pointer":
                        ctx.task_origin_pointer = field_value
                    elif field_name in ("reasoning_log_pointer", "trace_pointer"):
                        # accept both names (backward compat with v1 of skill, RCA 2026-05-02)
                        ctx.reasoning_log_pointer = field_value
                    elif field_name == "reasoning_log_excerpts":
                        in_excerpts = True
                    # B. Owner intent и failure
                    elif field_name == "owner_prompt_verbatim":
                        ctx.owner_prompt_verbatim = _strip_quotes(field_value)
                    elif field_name == "chat_jtbd":
                        ctx.chat_jtbd = field_value
                    elif field_name == "expected_delivery":
                        ctx.expected_delivery = field_value
                    elif field_name == "actual_failure_mode":
                        ctx.actual_failure_mode = _strip_quotes(field_value)
                    # C. GEPA tuning targets
                    elif field_name == "target_artifact_for_tuning":
                        ctx.target_artifact_for_tuning = field_value
                    elif field_name == "steering_verbatim":
                        ctx.steering_verbatim = _strip_quotes(field_value)
                    elif field_name == "scoring_rubric_pass_criteria":
                        in_rubric = True
                    elif field_name == "cognitive_load_symptom":
                        ctx.cognitive_load_symptom = field_value
                    # D. Triggers и recurrence
                    elif field_name == "recurrence_count_14d":
                        ctx.recurrence_count_14d = _parse_int_recurrence(field_value)
                    elif field_name == "triggers_that_should_have_fired":
                        ctx.triggers_that_should_have_fired = _parse_list_field(field_value)
                    elif field_name == "skills_active_at_failure":
                        ctx.skills_active_at_failure = _parse_list_field(field_value)
                    elif field_name == "failed_attempts_summary":
                        ctx.failed_attempts_summary = field_value
                elif in_rubric:
                    rm = RUBRIC_ITEM_RE.match(inner)
                    if rm:
                        ctx.scoring_rubric_pass_criteria.append(rm.group(1).strip())
                elif in_excerpts:
                    # Bullet item with quoted excerpt: `  - "quote ≤200 chars"`
                    em = re.match(r"^\s*[-*]\s+(.+)$", inner)
                    if em:
                        excerpt = _strip_quotes(em.group(1).strip())
                        if excerpt:
                            ctx.reasoning_log_excerpts.append(excerpt)
                j += 1
            yield ctx
            i = j
            continue
        i += 1


def filter_by_since(incidents: list[IncidentContext], since: str) -> list[IncidentContext]:
    if since == "all":
        return incidents
    m = re.match(r"^(\d+)d$", since)
    if not m:
        raise ValueError(f"invalid --since value: {since} (expected: 7d / 14d / 30d / all)")
    days = int(m.group(1))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for inc in incidents:
        if not inc.incident_date:
            continue
        try:
            d = datetime.strptime(inc.incident_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if d >= cutoff:
            out.append(inc)
    return out


def filter_by_target(incidents: list[IncidentContext], target: str | None) -> list[IncidentContext]:
    if not target:
        return incidents
    return [inc for inc in incidents if target in inc.target_artifact_for_tuning]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert ai.incidents.md context blocks → GEPA trainset.jsonl",
    )
    parser.add_argument("--incidents", required=True, help="path to ai.incidents.md")
    parser.add_argument("--output", required=True, help="output trainset.jsonl path")
    parser.add_argument("--since", default="all", help="14d / 7d / 30d / all (default: all)")
    parser.add_argument("--target-artifact", default=None, help="filter by target_artifact_for_tuning substring")
    parser.add_argument("--min-rubric-criteria", type=int, default=3, help="min rubric items (default 3)")
    parser.add_argument("--strict", action="store_true", help="exit code 2 on parse errors")
    args = parser.parse_args()

    incidents_path = Path(args.incidents)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_incidents = list(parse_incidents_file(incidents_path))
    if not all_incidents:
        print(f"warning: no «{CONTEXT_BLOCK_HEADER}» blocks found in {incidents_path}", file=sys.stderr)
        return 1

    filtered = filter_by_since(all_incidents, args.since)
    filtered = filter_by_target(filtered, args.target_artifact)

    valid_cases = []
    invalid_cases = []
    for inc in filtered:
        if inc.is_valid(min_rubric=args.min_rubric_criteria):
            valid_cases.append(inc)
        else:
            invalid_cases.append(inc)

    if not valid_cases:
        print(
            f"warning: 0 valid cases after filter (since={args.since}, target={args.target_artifact}, "
            f"total_with_block={len(all_incidents)}, after_since_target={len(filtered)}, "
            f"invalid={len(invalid_cases)})",
            file=sys.stderr,
        )
        if invalid_cases:
            print("\nSkipped (invalid):", file=sys.stderr)
            for inc in invalid_cases:
                print(
                    f"  - {inc.incident_date or '?'} {inc.incident_header[:60]} "
                    f"(line {inc.source_line}): {'; '.join(inc.parse_errors)}",
                    file=sys.stderr,
                )
        return 1

    with out_path.open("w", encoding="utf-8") as fh:
        for inc in valid_cases:
            fh.write(json.dumps(inc.to_gepa_case(), ensure_ascii=False) + "\n")

    print(
        f"OK: {len(valid_cases)} cases → {out_path} "
        f"(filtered from {len(all_incidents)} total context blocks, "
        f"{len(invalid_cases)} skipped as invalid)"
    )
    if invalid_cases:
        print("\nSkipped (invalid):", file=sys.stderr)
        for inc in invalid_cases:
            print(
                f"  - {inc.incident_date or '?'} {inc.incident_header[:60]} "
                f"(line {inc.source_line}): {'; '.join(inc.parse_errors)}",
                file=sys.stderr,
            )
        if args.strict:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
