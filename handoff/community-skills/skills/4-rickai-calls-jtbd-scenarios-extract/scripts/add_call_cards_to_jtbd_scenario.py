#!/usr/bin/env python3
"""
add_call_cards_to_jtbd_scenario.py — добавляет карточки анализа звонков в JTBD-сценарий.

JTBD владельца: «когда я открываю JTBD-сценарий по клиенту → хочу видеть карточку
с полным анализом для каждого звонка прямо в тексте → чтобы не переключаться между
документами и сразу видеть гипотезы, блокеры и 5 почему».

OUTPUT (что получите): каждый звонок в .md обогащается карточкой из 31 поля анализа
ПЕРЕД блоком «**Транскрипт**». Пустые поля видны явно (⚠️), данные из CRM тоже.

OUTCOME (какая выгода): аналитик видит полный контекст звонка без переключения
между parquet и markdown — скорость разбора сценария ×3, ошибки пропуска данных → 0.

CANONICAL LOCATION: .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/

Reads:
  - bronze/calls-supabase_calls/calls.parquet (or --calls-parquet-path)
  - scenario .md file (--scenario-md-path)

For each call found in the .md (by call_id UUID), injects an enrichment card
with ALL 31 analysis_fields (from _ANALYSIS_KEYS) BEFORE the «**Транскрипт**» line.

Empty / null / "None" values → "— ⚠️ нужно перезапустить алгоритм"
(owner must see data quality issues, NOT filtered away — RCA 2026-05-28)

Idempotent: cards already injected (<!-- enriched-card -->) are skipped.

Note on default parquet path: the default parquet path uses _WORKSPACE_ROOT which is
computed as 5 parents from __file__. When running from a git worktree (.claude/worktrees/),
the computed root is the worktree root, not the main workspace. In that case, pass
--calls-parquet-path explicitly.

Usage:
    python3 .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/add_call_cards_to_jtbd_scenario.py \\
        --client-alias luis-ru \\
        --scenario-md-path "[rick.ai]/clients/all-clients/luis-ru/intake/..." \\
        [--calls-parquet-path /path/to/calls.parquet]  # optional, defaults to canonical

Output:
    Modifies .md in-place (backup at .md.bak created first).
    Reports: N enriched / M already done / K not found in parquet.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────
# Script at .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/
# 5 parents: scripts/ → skill/ → skills/ → .agents/ → workspace_root
# NOTE: from a git worktree (.claude/worktrees/<branch>/), this resolves to the
# worktree root, not the main workspace. Pass --calls-parquet-path explicitly in that case.
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# ── Analysis keys — ALL 31 fields (mirror of _ANALYSIS_KEYS in supabase_calls_export) ──
_ANALYSIS_KEYS = (
    "crm_deal_id",
    "crm_deal_status",
    "segment_abcd",
    "qualification",
    "segment_goal",
    "desire",
    "blocker",
    "when_trigger",
    "situation",
    "what_client",
    "get_on_this_stage",
    "root_cause_5why",
    "user_big_jtbd",
    "user_medium_jtbd",
    "user_small_jtbd",
    "ai_user_big_jtbd",
    "ai_user_medium_jtbd",
    "ai_user_small_jtbd",
    "sale_blocker",
    "when_trigger_situation",
    "stop_words_patterns",
    "recommended_phrases",
    "sales_skills_big_jtbd",
    "sales_skills_medium_jtbd",
    "sales_skills_small_jtbd",
    "ai_sales_skills_big_jtbd",
    "ai_sales_skills_medium_jtbd",
    "transaction_id",
    "contact_id",
    "transaction_revenue",
    "items_json",
)

# ── Human-readable labels ─────────────────────────────────────────────────────
_FIELD_LABELS: dict[str, str] = {
    # Core call table fields (not in analysis_fields JSONB)
    "root_cause_category": "Корень причины",
    "conversation_type": "Тип разговора",
    "jtbd_l1": "JTBD L1",
    # ABCDX
    "segment_abcd": "Сегмент ABCD",
    "qualification": "Квалификация",
    "segment_goal": "Цель сегмента",
    # JTBD hierarchy
    "user_big_jtbd": "Big JTBD (пользователь)",
    "user_medium_jtbd": "Medium JTBD (пользователь)",
    "user_small_jtbd": "Small JTBD (пользователь)",
    "ai_user_big_jtbd": "Big JTBD (AI)",
    "ai_user_medium_jtbd": "Medium JTBD (AI)",
    "ai_user_small_jtbd": "Small JTBD (AI)",
    # Enrichment
    "desire": "Желание (`desire`)",
    "blocker": "Блокер",
    "when_trigger": "Триггер",
    "situation": "Ситуация",
    "what_client": "Клиент",
    "get_on_this_stage": "Получит на этом этапе",
    "root_cause_5why": "5 Почему",
    "when_trigger_situation": "Триггер+Ситуация",
    "sale_blocker": "Блокер продажи",
    # Patterns
    "stop_words_patterns": "Стоп-слова",
    "recommended_phrases": "Рекомендованные фразы",
    "sales_skills_big_jtbd": "Навыки продаж (Big)",
    "sales_skills_medium_jtbd": "Навыки продаж (Medium)",
    "sales_skills_small_jtbd": "Навыки продаж (Small)",
    "ai_sales_skills_big_jtbd": "AI навыки продаж (Big)",
    "ai_sales_skills_medium_jtbd": "AI навыки продаж (Medium)",
    # CRM
    "crm_deal_id": "CRM сделка ID",
    "crm_deal_status": "CRM сделка статус",
    # CRM / Exchange v2
    "transaction_id": "Транзакция (CRM/Exchange)",
    "contact_id": "Контакт (CRM/Exchange)",
    "transaction_revenue": "Выручка транзакции",
    "items_json": "Товары (JSON)",
}

# ── Card sections (ordered groups for readability) ─────────────────────────────
_CARD_SECTIONS: list[tuple[str, list[str]]] = [
    # Section name, list of field keys
    ("Классификация звонка", ["root_cause_category", "conversation_type", "jtbd_l1"]),
    ("ABCDX сегмент", ["segment_abcd", "qualification", "segment_goal"]),
    ("JTBD (оператор)", ["user_big_jtbd", "user_medium_jtbd", "user_small_jtbd"]),
    ("JTBD (AI)", ["ai_user_big_jtbd", "ai_user_medium_jtbd", "ai_user_small_jtbd"]),
    (
        "Анализ звонка",
        [
            "desire",
            "blocker",
            "when_trigger",
            "situation",
            "what_client",
            "get_on_this_stage",
            "root_cause_5why",
            "when_trigger_situation",
            "sale_blocker",
        ],
    ),
    (
        "Паттерны",
        [
            "stop_words_patterns",
            "recommended_phrases",
            "sales_skills_big_jtbd",
            "sales_skills_medium_jtbd",
            "sales_skills_small_jtbd",
            "ai_sales_skills_big_jtbd",
            "ai_sales_skills_medium_jtbd",
        ],
    ),
    (
        "CRM / Exchange",
        [
            "crm_deal_id",
            "crm_deal_status",
            "transaction_id",
            "contact_id",
            "transaction_revenue",
            "items_json",
        ],
    ),
]

# ── Markers ───────────────────────────────────────────────────────────────────
_ENRICH_OPEN = "<!-- enriched-card"
_ENRICH_CLOSE = "<!-- /enriched-card -->"
_TRANSCRIPT_MARKERS = (
    "**Транскрипт (дословно, без сокращений):**",
    "**Транскрипт:**",
)
_CALL_ID_PATTERN = re.compile(r"call_id\s+`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`")
_MISSING = "— ⚠️ нужно перезапустить алгоритм"
# Null-value for optional CRM/Exchange fields: absence = not yet in CRM (not a retry signal)
# "нет в CRM" is unambiguous for non-technical readers vs plain "—" (Design fix RCA 2026-05-28)
_MISSING_NULL = "нет в CRM"
# Fields where null = «not yet in CRM» (not a retry-algorithm signal)
_DATA_FIELDS: frozenset[str] = frozenset(
    {
        "crm_deal_id",
        "crm_deal_status",
        "transaction_id",
        "contact_id",
        "transaction_revenue",
        "items_json",
    }
)
# Magic string used in not-found warning card (kept as constant to avoid fragile substring matching)
_NOT_FOUND_MARKER = "не найден в parquet"


def _get_workspace_root() -> Path:
    return _WORKSPACE_ROOT


def _load_calls_df(parquet_path: Path) -> Any:
    """Load calls parquet; index by call id for O(1) lookup.

    Handles duplicate IDs (incremental ETL re-exports) by keeping last row.
    """
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pandas not installed. Run: pip install pandas pyarrow")
    df = pd.read_parquet(parquet_path)
    # Guard against duplicate IDs from incremental ETL (H1 fix — QA 2026-05-28)
    n_dups = df.duplicated(subset=["id"]).sum()
    if n_dups > 0:
        print(
            f"WARNING: {n_dups} duplicate call IDs found in parquet — keeping last. "
            "This may indicate incremental export overlap.",
            file=sys.stderr,
        )
        df = df.drop_duplicates(subset=["id"], keep="last")
    return df.set_index("id")


def _safe_val(v: Any) -> str:
    """Return human-readable value or _MISSING placeholder."""
    try:
        import pandas as pd

        if pd.isna(v):  # handles np.nan, pd.NA, pd.NaT (M3 fix — QA 2026-05-28)
            return _MISSING
    except (TypeError, ImportError):
        pass
    if v is None:
        return _MISSING
    s = str(v).strip()
    if s in ("", "None", "null", "nan", "NaN"):
        return _MISSING
    return s


def _md_cell_safe(v: str) -> str:
    """Escape value for safe insertion into markdown table cell.

    Replaces | → \\| and newlines → space so table structure is not broken.
    (C4 fix — QA 2026-05-28: values from analysis_fields may contain pipe chars)
    """
    return v.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _render_5why(val: str) -> str:
    """Render numbered Why steps with line breaks for readability (Design fix 4).

    Converts ' → 1.' / ' → 2)' patterns to '<br>1.' for markdown display.
    Extracted from get_val() to avoid duplicate re.sub calls (G01 — LOW 2026-05-28).
    """
    return re.sub(r"\s*→\s*(?=\d+[).])", "<br>", val)


def _build_card(call_id: str, df_indexed: Any) -> tuple[str, bool]:
    """
    Build enriched per-call markdown card for one call_id.

    Returns:
        (card_text: str, found: bool)
        found=True when call_id exists in parquet and card has real data.
        found=False when call_id is not in parquet (warning card rendered).

    Uses _MISSING for any empty/null field so owner sees data quality gaps.
    (H2 fix — QA 2026-05-28: return bool instead of substring-match on card text)
    """
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pandas not installed")

    lines: list[str] = []
    lines.append(f"{_ENRICH_OPEN} call_id:{call_id} -->")
    lines.append("")
    lines.append("**Карта звонка (analysis_fields + классификация):**")
    lines.append("")

    # Get row from parquet (may not exist)
    if call_id not in df_indexed.index:
        lines.append(f"⚠️ `call_id` `{call_id}` {_NOT_FOUND_MARKER} — проверь выгрузку bronze.")
        lines.append("")
        lines.append(_ENRICH_CLOSE)
        lines.append("")
        return "\n".join(lines) + "\n", False

    row = df_indexed.loc[call_id]

    # Guard: if duplicate IDs slipped through (shouldn't after drop_duplicates),
    # take first row to avoid DataFrame-vs-Series confusion (C3 fix — QA 2026-05-28)
    # NOTE: must use isinstance(row, pd.DataFrame), NOT hasattr(row, "iloc") —
    # pd.Series also has .iloc, so hasattr would always be True.
    if isinstance(row, pd.DataFrame):
        print(
            f"WARNING: call_id {call_id} matched multiple rows after dedup — taking first.",
            file=sys.stderr,
        )
        row = row.iloc[0]

    # Parse analysis_fields JSONB (stored as text in parquet)
    af: dict[str, Any] = {}
    try:
        raw_af = row["analysis_fields"]
    except (KeyError, TypeError):
        raw_af = None

    if raw_af is not None:
        try:
            import pandas as pd

            is_missing = pd.isna(raw_af)
        except (TypeError, ImportError):
            is_missing = False
        if not is_missing and str(raw_af).strip() not in ("", "None", "nan"):
            try:
                af = json.loads(raw_af)
            except (json.JSONDecodeError, TypeError) as exc:
                # Log warning but continue — all fields will show _MISSING
                # (C9 fix — QA 2026-05-28: don't silently swallow JSON errors)
                preview = str(raw_af)[:200]
                print(
                    f"WARNING: call_id {call_id} — failed to parse analysis_fields JSON: {exc}. "
                    f"Raw value (first 200 chars): {preview}",
                    file=sys.stderr,
                )
                af = {}

    # Helper to get value — first from direct parquet column, then from af
    def get_val(key: str) -> str:
        # Direct parquet column (root_cause_category, conversation_type, jtbd_l1, etc.)
        try:
            direct = row[key]
            sv = _safe_val(direct)
            if sv != _MISSING:
                val = _md_cell_safe(sv)
                if key == "root_cause_5why":
                    val = _render_5why(val)
                return val
        except (KeyError, TypeError):
            pass
        # From analysis_fields JSONB
        af_val = af.get(key)
        sv = _safe_val(af_val)
        # CRM/Exchange fields: absence = null ("—"), not a retry signal (Design fix 3)
        if sv == _MISSING and key in _DATA_FIELDS:
            return _MISSING_NULL
        val = _md_cell_safe(sv)
        if key == "root_cause_5why" and sv != _MISSING:
            val = _render_5why(val)
        return val

    # Summary header: quick one-line digest before full sections (Design fix 2)
    _summary_parts = []
    for _hkey, _hlabel in (
        ("root_cause_category", "категория"),
        ("segment_abcd", "сегмент"),
        ("user_small_jtbd", "small JTBD"),
        ("crm_deal_status", "CRM статус"),
    ):
        _hval = get_val(_hkey)
        if _hval and _hval not in (_MISSING, _MISSING_NULL):
            _summary_parts.append(f"{_hlabel} `{_hval}`")
    if _summary_parts:
        lines.append("> " + " · ".join(_summary_parts))
        lines.append("")

    # Render sections
    for section_name, fields in _CARD_SECTIONS:
        lines.append(f"**{section_name}**")
        lines.append("")
        lines.append("| Поле | Значение |")
        lines.append("|---|---|")
        for key in fields:
            label = _FIELD_LABELS.get(key, key)
            val = get_val(key)
            lines.append(f"| {label} | {val} |")
        lines.append("")

    lines.append(_ENRICH_CLOSE)
    lines.append("")
    return "\n".join(lines) + "\n", True


def _is_already_enriched(lines: list[str], call_id_pos: int, transcript_idx: int, call_id: str) -> bool:
    """Check if the enrichment card for call_id exists between call_id_pos and transcript_idx."""
    # Scan lines from where call_id was found to current position.
    # This avoids fixed-window problems when the card spans many lines.
    marker = f"call_id:{call_id}"
    for j in range(call_id_pos, transcript_idx):
        if _ENRICH_OPEN in lines[j] and marker in lines[j]:
            return True
    return False


def enrich_scenario_md(
    scenario_md_path: Path,
    calls_parquet_path: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """
    Inject enrichment cards into scenario .md file.

    Returns dict: {enriched: int, already_done: int, not_found: int, total: int}
    """
    content = scenario_md_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    df_indexed = _load_calls_df(calls_parquet_path)

    stats = {"enriched": 0, "already_done": 0, "not_found": 0, "total": 0}

    result_lines: list[str] = []
    current_call_id: str | None = None
    current_call_id_pos: int = -1  # position in result_lines where call_id was detected

    i = 0
    in_force_skip = False  # True when inside an existing card block being stripped (force=True)

    while i < len(lines):
        line = lines[i]

        # When force=True, strip existing enriched-card blocks so re-injection doesn't duplicate.
        # Skip all lines from <!-- enriched-card ... --> through <!-- /enriched-card --> (inclusive).
        if force:
            if not in_force_skip and _ENRICH_OPEN in line:
                in_force_skip = True
                i += 1
                continue
            if in_force_skip:
                if _ENRICH_CLOSE in line:
                    in_force_skip = False
                i += 1
                continue

        # Detect call_id on any line
        m = _CALL_ID_PATTERN.search(line)
        if m:
            current_call_id = m.group(1)
            current_call_id_pos = len(result_lines)  # record position BEFORE appending
            stats["total"] += 1

        # Detect transcript marker
        is_transcript = any(marker in line for marker in _TRANSCRIPT_MARKERS)

        if is_transcript and current_call_id:
            call_id = current_call_id
            call_id_pos = current_call_id_pos
            current_call_id = None  # reset — consumed
            current_call_id_pos = -1

            if not force and _is_already_enriched(result_lines, call_id_pos, len(result_lines), call_id):
                stats["already_done"] += 1
                result_lines.append(line)
                i += 1
                continue

            # Build and inject card (H2 fix: bool return, not substring match)
            card, found = _build_card(call_id, df_indexed)
            if found:
                stats["enriched"] += 1
            else:
                stats["not_found"] += 1

            result_lines.append(card)
            result_lines.append(line)
            i += 1
            continue

        result_lines.append(line)
        i += 1

    new_content = "".join(result_lines)

    if not dry_run:
        # Write backup — rotate existing .md.bak to timestamped name (MED fix 2 — QA 2026-05-28)
        backup_path = scenario_md_path.with_suffix(".md.bak")
        if backup_path.exists():
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            rotated_path = scenario_md_path.with_name(scenario_md_path.stem + f".bak.{ts}")
            backup_path.rename(rotated_path)
        with open(backup_path, "w", encoding="utf-8") as _bak_f:
            _bak_f.write(content)
            _bak_f.flush()
            os.fsync(_bak_f.fileno())
        # Atomic write: write to temp then os.replace; cleanup orphan on error (MED fix 1 — QA 2026-05-28)
        parent = scenario_md_path.parent
        _tmp_file: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=parent, suffix=".md.tmp", delete=False
            ) as tmp:
                _tmp_file = Path(tmp.name)
                tmp.write(new_content)
            os.replace(_tmp_file, scenario_md_path)
            _tmp_file = None  # success — consumed by os.replace
        except Exception:
            if _tmp_file is not None and _tmp_file.exists():
                try:
                    _tmp_file.unlink()
                except OSError:
                    pass
            raise
        print(f"Written: {scenario_md_path}")
        print(f"Backup:  {backup_path}")
    else:
        print("[dry-run] Would write enriched content")

    stats["success"] = True
    return stats


def _default_calls_parquet(client_alias: str) -> Path:
    ws = _get_workspace_root()
    return (
        ws
        / "[rick.ai]"
        / "clients"
        / "all-clients"
        / client_alias
        / "bronze"
        / "calls-supabase_calls"
        / "calls.parquet"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Inject enriched per-call cards into JTBD scenario .md files")
    p.add_argument("--client-alias", required=True, help="e.g. luis-ru, avtoall-ru")
    p.add_argument("--scenario-md-path", required=True, help="Path to scenario .md file")
    p.add_argument(
        "--calls-parquet-path",
        default=None,
        help=(
            "Override bronze calls.parquet path (default: canonical path by client_alias). "
            "REQUIRED when running from a git worktree (.claude/worktrees/)."
        ),
    )
    p.add_argument("--dry-run", action="store_true", help="Print stats, do not modify file")
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-inject cards even if already enriched (replaces existing cards)",
    )
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    md_path = Path(args.scenario_md_path)
    if not md_path.exists():
        print(f"ERROR: scenario md not found: {md_path}", file=sys.stderr)
        return 1

    if args.calls_parquet_path:
        parquet_path = Path(args.calls_parquet_path)
    else:
        parquet_path = _default_calls_parquet(args.client_alias)

    if not parquet_path.exists():
        print(f"ERROR: calls.parquet not found: {parquet_path}", file=sys.stderr)
        print(
            "If running from a git worktree, pass --calls-parquet-path explicitly.",
            file=sys.stderr,
        )
        print("Otherwise run 4-rickai-calls-supabase-export first.", file=sys.stderr)
        return 1

    result = enrich_scenario_md(
        scenario_md_path=md_path,
        calls_parquet_path=parquet_path,
        dry_run=args.dry_run,
        force=args.force,
    )

    print("\n=== Enrichment summary ===")
    print(f"  Total calls in .md: {result['total']}")
    print(f"  Enriched (new):     {result['enriched']}")
    print(f"  Already done:       {result['already_done']}")
    print(f"  Not found in parquet: {result['not_found']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
