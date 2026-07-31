"""
Unit tests for add_call_cards_to_jtbd_scenario.py

JTBD: «когда аналитик запускает скрипт → карточки звонков инжектируются в сценарий
правильно → чтобы сценарий стал самодостаточным источником анализа».

Run:
    python3 -m pytest .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/test_add_call_cards_to_jtbd_scenario.py -v
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

# Add skill scripts dir to path
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from add_call_cards_to_jtbd_scenario import (  # type: ignore[import]
    _ANALYSIS_KEYS,
    _CARD_SECTIONS,
    _FIELD_LABELS,
    _MISSING,
    _build_card,
    _is_already_enriched,
    _md_cell_safe,
    _safe_val,
    enrich_scenario_md,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

CALL_ID_1 = "019d4792-d46a-700e-8023-9907b3702bc0"
CALL_ID_2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _make_parquet_with_calls(tmp_path: Path, rows: list[dict]) -> Path:
    """Create a minimal calls.parquet for tests."""
    import pandas as pd

    df = pd.DataFrame(rows)
    p = tmp_path / "calls.parquet"
    df.to_parquet(p, index=False, engine="pyarrow")
    return p


def _make_scenario_md(tmp_path: Path, content: str, name: str = "scenario.md") -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ── Module-level fixtures shared by TestEnrichScenarioMd + TestForceReinjection ──
# H1 fix (code-reviewer 2026-05-28): previously _SAMPLE_MD and _make_parquet were class-level
# private attributes in TestEnrichScenarioMd. TestForceReinjection then used cross-class
# references (TestEnrichScenarioMd._SAMPLE_MD, TestEnrichScenarioMd._make_parquet(TestEnrichScenarioMd(), ...))
# which are fragile and break silently on class refactoring.
# Fix: extract to module-level so both classes reference the same canonical source.

_FIXTURE_SAMPLE_MD = textwrap.dedent(f"""\
    # JTBD Сценарий: Тест

    ## §1 Гипотезы

    | # | Гипотеза |
    |---|---|
    | H01 | Тест |

    ## §2 Транскрипты

    ### Звонки по phone_hash `abc123` (N=1)

    #### Звонок 1/1 — `2026-03-04 08:04:18` · Иванова · inbound · 59s · call_id `{CALL_ID_1}`

    **Транскрипт (дословно, без сокращений):**
    ```
    agent: Здравствуйте.
    client: Здравствуйте, счёт нужен.
    ```
""")


def _make_fixture_parquet(tmp_path: Path) -> Path:
    """Create the standard single-call parquet used by most scenario enrichment tests."""
    return _make_parquet_with_calls(
        tmp_path,
        [
            {
                "id": CALL_ID_1,
                "root_cause_category": "process_gap",
                "conversation_type": "question",
                "jtbd_l1": "C1.1",
                "analysis_fields": json.dumps(
                    {
                        "blocker": "Нет ИГК в форме",
                        "situation": "Оформляет заказ по ФЗ",
                        "what_client": "ООО Ромашка",
                        "root_cause_5why": "1) Нет UI → ...",
                        "user_small_jtbd": "C1.1 Отправка счёта",
                        "segment_abcd": "B",
                    }
                ),
            }
        ],
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestSafeVal:
    def test_none_returns_missing(self):
        assert _safe_val(None) == _MISSING

    def test_empty_string_returns_missing(self):
        assert _safe_val("") == _MISSING

    def test_none_string_returns_missing(self):
        assert _safe_val("None") == _MISSING

    def test_normal_value_returned_as_is(self):
        assert _safe_val("Блокер ИГК") == "Блокер ИГК"

    def test_numeric_value(self):
        assert _safe_val(49800.0) == "49800.0"

    def test_null_string_returns_missing(self):
        assert _safe_val("null") == _MISSING


class TestAnalysisKeys:
    def test_all_31_keys_present(self):
        # == 31, not >= 31 (M6 fix — QA 2026-05-28: lock the count, don't silently accept drift)
        assert len(_ANALYSIS_KEYS) == 31

    def test_no_duplicates(self):
        assert len(_ANALYSIS_KEYS) == len(set(_ANALYSIS_KEYS))

    def test_rick_exchange_keys_present(self):
        for k in ("transaction_id", "contact_id", "transaction_revenue", "items_json"):
            assert k in _ANALYSIS_KEYS

    def test_core_enrichment_keys_present(self):
        for k in ("desire", "blocker", "situation", "what_client", "root_cause_5why"):
            assert k in _ANALYSIS_KEYS


class TestCardSections:
    def test_all_31_keys_covered_in_sections(self):
        """Every key in _ANALYSIS_KEYS must appear in exactly one section."""
        covered = set()
        for _, fields in _CARD_SECTIONS:
            covered.update(fields)
        for key in _ANALYSIS_KEYS:
            assert key in covered, f"Key '{key}' missing from _CARD_SECTIONS"

    def test_no_section_key_duplicates(self):
        all_keys = []
        for _, fields in _CARD_SECTIONS:
            all_keys.extend(fields)
        assert len(all_keys) == len(set(all_keys))


class TestBuildCard:
    def test_card_contains_call_id(self, tmp_path):
        import pandas as pd

        rows = [
            {
                "id": CALL_ID_1,
                "root_cause_category": "process_gap",
                "conversation_type": "question",
                "jtbd_l1": "C1.1",
                "analysis_fields": json.dumps(
                    {
                        "blocker": "Нет ИГК",
                        "situation": "Оформляет счёт",
                        "what_client": "ООО Ромашка",
                        "root_cause_5why": "1) Нет ИГК → ...",
                        "user_small_jtbd": "C1.1 Отправка счёта",
                        "segment_abcd": "B",
                    }
                ),
            }
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)

        assert found is True
        assert CALL_ID_1 in card
        assert "<!-- enriched-card" in card
        assert "<!-- /enriched-card -->" in card

    def test_empty_fields_show_missing_marker(self, tmp_path):
        """All zero-fill fields (desire, crm_deal_id) must show _MISSING, not silence.
        CRM/Exchange fields show _MISSING_NULL ("нет в CRM") not the ⚠️ retry marker.
        """
        import pandas as pd

        rows = [
            {
                "id": CALL_ID_1,
                "root_cause_category": "process_gap",
                "analysis_fields": json.dumps(
                    {
                        # desire intentionally absent → must be ⚠️
                        "blocker": "Нет кнопки",
                        "situation": "Клиент звонит",
                    }
                ),
            }
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)

        assert found is True
        # Empty analysis fields must appear as _MISSING (⚠️ retry)
        assert _MISSING in card, "Empty fields must show ⚠️ нужно перезапустить алгоритм"
        # Verify specific empty fields are represented
        assert "Желание (`desire`)" in card
        assert "CRM сделка ID" in card
        # Design fix 5: label renamed from "Rick Exchange" to "CRM/Exchange"
        assert "Транзакция (CRM/Exchange)" in card
        assert "Транзакция (Rick Exchange)" not in card
        # Design fix 3: CRM fields show _MISSING_NULL ("нет в CRM") not the ⚠️ retry marker
        from add_call_cards_to_jtbd_scenario import _MISSING_NULL

        assert _MISSING_NULL in card

    def test_crm_fields_with_direct_parquet_column_pd_na_show_missing_null(self, tmp_path):
        """MED finding (code-reviewer 2026-05-28): CRM fields that arrive as DIRECT
        parquet columns (not only via analysis_fields JSONB) with pd.NA values must
        show _MISSING_NULL ('нет в CRM'), NOT _MISSING ('⚠️ нужно перезапустить алгоритм').

        Root: get_val() falls through direct-column path (sv == _MISSING → no return)
        → reaches JSONB path → af.get(key) = None → _MISSING → key in _DATA_FIELDS
        → _MISSING_NULL. Verified by _build_card live test 2026-05-28.
        """
        import pandas as pd
        from add_call_cards_to_jtbd_scenario import _DATA_FIELDS, _MISSING_NULL

        rows = [
            {
                "id": CALL_ID_1,
                "crm_deal_id": pd.NA,  # direct column, pd.NA
                "crm_deal_status": pd.NA,  # direct column, pd.NA
                "transaction_id": pd.NA,  # direct column, pd.NA
                "contact_id": pd.NA,  # direct column, pd.NA
                "transaction_revenue": pd.NA,  # direct column, pd.NA
                "analysis_fields": "{}",  # empty JSONB — no af fallback values
            }
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)

        assert found is True
        # All CRM/Exchange fields must show "нет в CRM", not ⚠️ retry
        assert _MISSING_NULL in card, "CRM fields with direct pd.NA must show 'нет в CRM', not ⚠️ retry marker"
        # Verify each CRM field label is present
        for label in ("CRM сделка ID", "CRM сделка статус", "Транзакция (CRM/Exchange)", "Контакт (CRM/Exchange)"):
            assert label in card, f"Expected label '{label}' in card"
            # Find the line for this label and confirm it shows _MISSING_NULL
            for line in card.split("\n"):
                if label in line:
                    assert _MISSING_NULL in line, f"Label '{label}' line should show 'нет в CRM', got: {line}"
                    break

    def test_nonexistent_call_id_shows_warning(self, tmp_path):
        import pandas as pd

        rows = [{"id": CALL_ID_1, "analysis_fields": None}]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_2, df)  # CALL_ID_2 not in parquet

        assert found is False
        assert "не найден в parquet" in card

    def test_null_analysis_fields_shows_missing_for_all(self, tmp_path):
        """If analysis_fields is null, every analysis field must be ⚠️."""
        import pandas as pd

        rows = [{"id": CALL_ID_1, "root_cause_category": "process_gap", "analysis_fields": None}]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)

        assert found is True
        # blocker, desire, etc. must all be missing
        assert _MISSING in card

    def test_all_section_headers_present(self, tmp_path):
        import pandas as pd

        rows = [{"id": CALL_ID_1, "analysis_fields": json.dumps({"blocker": "test"})}]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)

        assert found is True
        for section_name, _ in _CARD_SECTIONS:
            assert section_name in card, f"Section '{section_name}' missing from card"


class TestIsAlreadyEnriched:
    def test_detects_existing_marker(self):
        lines = [
            "#### Звонок 1/5\n",  # call_id_pos = 0
            f"<!-- enriched-card call_id:{CALL_ID_1} -->\n",  # index 1
            "| Поле | Значение |\n",
            "<!-- /enriched-card -->\n",
            "\n",  # transcript_idx = 5
        ]
        assert _is_already_enriched(lines, call_id_pos=0, transcript_idx=5, call_id=CALL_ID_1) is True

    def test_misses_different_call_id(self):
        lines = [
            "#### Звонок 1/5\n",
            f"<!-- enriched-card call_id:{CALL_ID_2} -->\n",
            "| Поле | Значение |\n",
        ]
        assert _is_already_enriched(lines, call_id_pos=0, transcript_idx=3, call_id=CALL_ID_1) is False

    def test_empty_lines_not_enriched(self):
        lines = ["#### Звонок 1/5\n", "\n"]
        assert _is_already_enriched(lines, call_id_pos=0, transcript_idx=2, call_id=CALL_ID_1) is False

    def test_marker_outside_scan_range_not_detected(self):
        """Marker from a PREVIOUS call must not affect current call detection."""
        lines = [
            f"<!-- enriched-card call_id:{CALL_ID_1} -->\n",  # index 0 — old call
            "<!-- /enriched-card -->\n",
            "#### Звонок 2/5\n",  # call_id_pos = 2 for new call
            "sometext\n",
        ]
        # CALL_ID_1 marker is at index 0, outside scan range [2, 4)
        assert _is_already_enriched(lines, call_id_pos=2, transcript_idx=4, call_id=CALL_ID_1) is False


class TestEnrichScenarioMd:
    """Tests for the full add_call_cards_to_jtbd_scenario() pipeline.

    Uses module-level _FIXTURE_SAMPLE_MD and _make_fixture_parquet
    (H1 fix — code-reviewer 2026-05-28: removed class-level private attrs to prevent
    fragile cross-class references in TestForceReinjection).
    """

    def test_enriches_one_call(self, tmp_path):
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)

        result = enrich_scenario_md(md, parquet, dry_run=False)

        assert result["enriched"] == 1
        assert result["already_done"] == 0
        assert result["not_found"] == 0

        enriched_text = md.read_text(encoding="utf-8")
        assert f"<!-- enriched-card call_id:{CALL_ID_1} -->" in enriched_text
        assert "<!-- /enriched-card -->" in enriched_text
        # Card must be BEFORE the transcript
        card_pos = enriched_text.find(f"<!-- enriched-card call_id:{CALL_ID_1} -->")
        transcript_pos = enriched_text.find("**Транскрипт (дословно, без сокращений):**")
        assert card_pos < transcript_pos, "Card must be inserted BEFORE transcript line"

    def test_backup_created(self, tmp_path):
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)

        enrich_scenario_md(md, parquet, dry_run=False)

        backup = md.with_suffix(".md.bak")
        assert backup.exists(), "Backup .md.bak must be created"
        assert backup.read_text(encoding="utf-8") == _FIXTURE_SAMPLE_MD

    def test_idempotent_second_run(self, tmp_path):
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)

        # First run
        r1 = enrich_scenario_md(md, parquet, dry_run=False)
        assert r1["enriched"] == 1

        # Second run — must detect already done
        r2 = enrich_scenario_md(md, parquet, dry_run=False)
        assert r2["already_done"] == 1
        assert r2["enriched"] == 0

    def test_dry_run_does_not_modify_file(self, tmp_path):
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)
        original = md.read_text(encoding="utf-8")

        result = enrich_scenario_md(md, parquet, dry_run=True)

        assert md.read_text(encoding="utf-8") == original
        assert result["enriched"] == 1  # would have enriched

    def test_missing_field_shows_warning_not_omitted(self, tmp_path):
        """Fields 0%-populated (desire, crm_deal_id) must show ⚠️ NOT be absent."""
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)  # no 'desire' field in analysis_fields

        enrich_scenario_md(md, parquet, dry_run=False)

        enriched = md.read_text(encoding="utf-8")
        assert _MISSING in enriched, "Empty field must show ⚠️ in enriched card"
        # Verify 'Желание' row is present (not filtered out)
        assert "Желание (`desire`)" in enriched

    def test_all_31_analysis_fields_appear_in_card(self, tmp_path):
        """All 31 analysis_fields must appear as row labels in the enriched card."""
        from add_call_cards_to_jtbd_scenario import _FIELD_LABELS  # type: ignore[import]

        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)

        enrich_scenario_md(md, parquet, dry_run=False)
        enriched = md.read_text(encoding="utf-8")

        for key in _ANALYSIS_KEYS:
            label = _FIELD_LABELS.get(key, key)
            assert label in enriched, f"Field '{key}' (label='{label}') missing from enriched card"

    def test_call_not_in_parquet_shows_warning(self, tmp_path):
        md_content = textwrap.dedent(f"""\
            # Test
            #### Звонок 1/1 — call_id `{CALL_ID_2}`
            **Транскрипт (дословно, без сокращений):**
            ```
            agent: Привет.
            ```
        """)
        md = _make_scenario_md(tmp_path, md_content)
        # Parquet with CALL_ID_1, not CALL_ID_2
        parquet = _make_parquet_with_calls(tmp_path, [{"id": CALL_ID_1, "analysis_fields": None}])

        result = enrich_scenario_md(md, parquet, dry_run=False)
        assert result["not_found"] == 1

        enriched = md.read_text(encoding="utf-8")
        assert "не найден в parquet" in enriched

    def test_transcript_order_preserved(self, tmp_path):
        """Transcript text must remain in the file, after the card."""
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)

        enrich_scenario_md(md, parquet, dry_run=False)
        enriched = md.read_text(encoding="utf-8")

        # Original transcript still present
        assert "agent: Здравствуйте." in enriched
        assert "client: Здравствуйте, счёт нужен." in enriched


class TestMdCellSafe:
    """C4 fix (QA 2026-05-28): pipe and newline in values must be escaped."""

    def test_pipe_escaped(self):
        assert _md_cell_safe("foo | bar") == "foo \\| bar"

    def test_newline_replaced_with_space(self):
        assert _md_cell_safe("foo\nbar") == "foo bar"

    def test_cr_replaced(self):
        assert _md_cell_safe("foo\r\nbar") == "foo  bar"

    def test_no_change_for_plain_value(self):
        assert _md_cell_safe("Нет ИГК в форме") == "Нет ИГК в форме"

    def test_missing_marker_passthrough(self):
        """_MISSING string must pass through unchanged (no pipes or newlines in it)."""
        assert _md_cell_safe(_MISSING) == _MISSING


class TestBuildCardReturnType:
    """H2 fix (QA 2026-05-28): _build_card returns (str, bool), not str."""

    def test_found_returns_true(self, tmp_path):
        import pandas as pd

        rows = [{"id": CALL_ID_1, "analysis_fields": '{"blocker": "Нет ИГК"}'}]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)
        assert found is True
        assert isinstance(card, str)

    def test_not_found_returns_false(self, tmp_path):
        import pandas as pd

        rows = [{"id": CALL_ID_1, "analysis_fields": None}]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_2, df)  # CALL_ID_2 not in parquet
        assert found is False
        assert "не найден в parquet" in card


class TestDuplicateIdsInParquet:
    """H1 fix (QA 2026-05-28): duplicate IDs from incremental ETL must not crash."""

    def test_duplicate_id_deduped(self, tmp_path):
        import pandas as pd

        rows = [
            {"id": CALL_ID_1, "analysis_fields": '{"blocker": "first"}'},
            {"id": CALL_ID_1, "analysis_fields": '{"blocker": "second (last)"}'},
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = _load_calls_df_for_test(parquet)
        # After dedup, only one row remains
        assert CALL_ID_1 in df.index
        assert df.index.duplicated().sum() == 0

    def test_duplicate_id_enrichment_does_not_crash(self, tmp_path):
        """add_call_cards_to_jtbd_scenario must succeed even if parquet has duplicate IDs."""
        import textwrap

        md_content = textwrap.dedent(f"""\
            # Test
            #### Звонок 1/1 — call_id `{CALL_ID_1}`
            **Транскрипт (дословно, без сокращений):**
            ```
            agent: Привет.
            ```
        """)
        md = _make_scenario_md(tmp_path, md_content)
        rows = [
            {"id": CALL_ID_1, "analysis_fields": '{"blocker": "first"}'},
            {"id": CALL_ID_1, "analysis_fields": '{"blocker": "second"}'},
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        result = enrich_scenario_md(md, parquet, dry_run=False)
        # No crash, one call enriched
        assert result["enriched"] == 1
        assert result["not_found"] == 0


class TestPipeInCellValues:
    """C4 fix (QA 2026-05-28): table cells with | or newlines must be escaped."""

    def test_pipe_in_blocker_escaped_in_output(self, tmp_path):
        import pandas as pd

        rows = [
            {
                "id": CALL_ID_1,
                "analysis_fields": json.dumps(
                    {
                        "blocker": "цена | наличие | срок",
                        "situation": "normal text",
                    }
                ),
            }
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)
        assert found is True
        # The pipe in blocker must be escaped — raw | would break markdown table
        assert "цена \\| наличие \\| срок" in card
        # The label row must be valid markdown (not have unescaped | inside cell value)
        # Check that each data row has exactly 2 | separators (3 pipes per row: |col1|col2|)
        # Use exact label with pipe boundary to distinguish "| Блокер |" from "| Блокер продажи |"
        data_rows = [line for line in card.splitlines() if "| Блокер |" in line]
        assert len(data_rows) == 1, f"Expected exactly 1 'Блокер' row, got: {data_rows}"
        # Row is: | Блокер | цена \| наличие \| срок |
        # 3 structural pipes + 2 literal | chars inside \| sequences = 5 total
        # (backslash-escape keeps the | char present in the string; markdown renderer treats \| as non-separator)
        assert data_rows[0].count("|") == 5

    def test_newline_in_value_replaced(self, tmp_path):
        import pandas as pd

        rows = [
            {
                "id": CALL_ID_1,
                "analysis_fields": json.dumps(
                    {
                        "blocker": "первая строка\nвторая строка",
                    }
                ),
            }
        ]
        parquet = _make_parquet_with_calls(tmp_path, rows)
        df = pd.read_parquet(parquet).set_index("id")
        card, found = _build_card(CALL_ID_1, df)
        assert found is True
        # Newline must be replaced with space
        assert "первая строка\nвторая строка" not in card
        assert "первая строка вторая строка" in card


class TestForceReinjection:
    """--force flag must replace existing cards, not duplicate them.

    Uses module-level _FIXTURE_SAMPLE_MD and _make_fixture_parquet
    (H1 fix — code-reviewer 2026-05-28: removed fragile cross-class private references).
    """

    def test_force_replaces_not_duplicates(self, tmp_path):
        md = _make_scenario_md(tmp_path, _FIXTURE_SAMPLE_MD)
        parquet = _make_fixture_parquet(tmp_path)

        # First run
        r1 = enrich_scenario_md(md, parquet, dry_run=False)
        assert r1["enriched"] == 1

        # Force second run
        r2 = enrich_scenario_md(md, parquet, dry_run=False, force=True)
        assert r2["enriched"] == 1
        assert r2["already_done"] == 0

        enriched = md.read_text(encoding="utf-8")
        # Must have exactly ONE card marker for this call_id
        assert enriched.count(f"<!-- enriched-card call_id:{CALL_ID_1} -->") == 1


class TestFieldLabelsCompleteness:
    """M1 fix (QA 2026-05-28): every key in _CARD_SECTIONS must have a label in _FIELD_LABELS."""

    def test_all_card_section_keys_have_labels(self):
        all_section_keys = [k for _, fields in _CARD_SECTIONS for k in fields]
        for key in all_section_keys:
            assert key in _FIELD_LABELS, (
                f"Key '{key}' in _CARD_SECTIONS has no entry in _FIELD_LABELS — " "add a human-readable Russian label."
            )


# ── Import helper for duplicate ID test ──────────────────────────────────────


def _load_calls_df_for_test(parquet_path: Path):
    """Import the real _load_calls_df for use in tests."""
    from add_call_cards_to_jtbd_scenario import _load_calls_df  # type: ignore[import]

    return _load_calls_df(parquet_path)


class TestRender5Why:
    """G01 fix (LOW 2026-05-28): _render_5why extracted to avoid duplicate re.sub."""

    def test_renders_arrow_before_numbered_step_dot(self):
        from add_call_cards_to_jtbd_scenario import _render_5why  # type: ignore[import]

        val = "причина → 1. нет связи → 2. нет базы"
        result = _render_5why(val)
        assert "<br>1." in result
        assert "<br>2." in result
        assert "→" not in result

    def test_renders_arrow_before_numbered_step_paren(self):
        from add_call_cards_to_jtbd_scenario import _render_5why  # type: ignore[import]

        val = "корень → 1) шаг один → 2) шаг два"
        result = _render_5why(val)
        assert "<br>1)" in result
        assert "<br>2)" in result

    def test_no_change_when_no_arrows(self):
        from add_call_cards_to_jtbd_scenario import _render_5why  # type: ignore[import]

        val = "просто текст без стрелок"
        assert _render_5why(val) == val

    def test_empty_string(self):
        from add_call_cards_to_jtbd_scenario import _render_5why  # type: ignore[import]

        assert _render_5why("") == ""
