from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


SCRIPT = Path(__file__).with_name("render_sanitized_call_corpus.py")
SPEC = importlib.util.spec_from_file_location("render_sanitized_call_corpus", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def source_files(tmp_path: Path) -> dict[str, Path]:
    company_id = "11111111-1111-1111-1111-111111111111"
    call_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    call_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    calls = pd.DataFrame(
        [
            {
                "id": call_a,
                "company_id": company_id,
                "date": "2026-07-01T12:00:00Z",
                "duration_sec": 42,
                "direction": "inbound",
                "status": "done",
                "operator_name": "Иван Иванов",
                "client_phone": "+7 999 123-45-67",
                "audio_url": "https://private.example/audio",
            },
            {
                "id": call_b,
                "company_id": company_id,
                "date": "2026-07-02T13:00:00Z",
                "duration_sec": 15,
                "direction": "outbound",
                "status": "error",
                "operator_name": "Иван Иванов",
                "client_phone_hash": "secret-hash",
            },
        ]
    )
    transcripts = pd.DataFrame(
        [
            {
                "call_id": call_a,
                "text": "",
                "segments": json.dumps(
                    [
                        {
                            "speaker": "agent",
                            "start": 0.0,
                            "text": "Иван Иванов: звоните +7 999 123-45-67",
                        },
                        {
                            "speaker": "client",
                            "start": 2.5,
                            "text": "Меня зовут Анна, почта anna@example.com, сайт https://example.com",
                        },
                        {
                            "speaker": "client",
                            "start": 5.0,
                            "text": "Анна, хочу подарок на день рождения",
                        },
                        {
                            "speaker": "agent",
                            "start": 7.0,
                            "text": "Здравствуйте, Мария, расскажу про условия",
                        },
                    ],
                    ensure_ascii=False,
                ),
            }
        ]
    )
    analyses = pd.DataFrame(
        [
            {
                "call_id": call_a,
                "summary": "Анна Петрова спросила про скидку.",
                "result": json.dumps(
                    {
                        "desire": "Получить бонус",
                        "contact_id": "raw-contact-id",
                        "crm_deal_id": "raw-deal-id",
                    },
                    ensure_ascii=False,
                ),
            }
        ]
    )
    paths = {
        "calls": tmp_path / "calls.parquet",
        "transcripts": tmp_path / "transcripts.parquet",
        "analyses": tmp_path / "analyses.parquet",
        "output": tmp_path / "safe",
        "company_id": company_id,
        "call_a": call_a,
        "call_b": call_b,
    }
    calls.to_parquet(paths["calls"], index=False)
    transcripts.to_parquet(paths["transcripts"], index=False)
    analyses.to_parquet(paths["analyses"], index=False)
    return paths


def _render(paths: dict[str, Path]) -> dict:
    return MODULE.render_corpus(
        calls_path=paths["calls"],
        transcripts_path=paths["transcripts"],
        analyses_path=paths["analyses"],
        output_dir=paths["output"],
        expected_company_id=paths["company_id"],
        snapshot_at="2026-07-16T00:00:00Z",
    )


def test_one_to_one_counts_and_missing_transcript_stub(source_files):
    reconciliation = _render(source_files)
    assert reconciliation["source_calls"] == 2
    assert reconciliation["parquet_rows"] == 2
    assert reconciliation["markdown_files"] == 2
    assert reconciliation["missing_transcript_stubs"] == 1
    assert reconciliation["missing_transcript_rows"] == 1
    assert reconciliation["empty_transcript_rows"] == 0
    assert reconciliation["duration_qa"]["numeric_last_timestamp_comparisons"] == 1
    assert reconciliation["duration_qa"]["last_timestamp_over_call_duration_plus_5s"] == 0
    assert reconciliation["duration_qa"]["last_timestamp_over_call_duration_plus_30s"] == 0
    assert reconciliation["counts_match"] is True
    assert "MUST NOT be used to infer a repeat customer" in reconciliation["identity_evidence_warning"]
    parquet = pd.read_parquet(source_files["output"] / "data" / "calls.parquet")
    stub = parquet.loc[parquet["transcript_status"] == "missing_stub"].iloc[0]
    stub_md = (source_files["output"] / stub["markdown_path"]).read_text(encoding="utf-8")
    assert "**Явный stub:**" in stub_md


def test_segment_order_is_preserved(source_files):
    _render(source_files)
    parquet = pd.read_parquet(source_files["output"] / "data" / "calls.parquet")
    available = parquet.loc[parquet["transcript_status"] == "available"].iloc[0]
    segments = json.loads(available["segments_json"])
    assert [segment["ordinal"] for segment in segments] == [1, 2, 3, 4]
    assert [segment["timestamp"] for segment in segments] == ["0.0", "2.5", "5.0", "7.0"]
    assert segments[2]["text"] == "[REDACTED_PERSON], хочу подарок на день рождения"
    assert segments[3]["text"] == "Здравствуйте, [REDACTED_PERSON], расскажу про условия"


def test_safe_refs_are_deterministic_and_do_not_expose_raw_ids(source_files):
    first = MODULE.safe_call_ref(source_files["call_a"], source_files["company_id"])
    second = MODULE.safe_call_ref(source_files["call_a"], source_files["company_id"])
    assert first == second
    assert source_files["call_a"] not in first
    _render(source_files)
    rendered_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_files["output"].rglob("*.md")
    )
    assert source_files["call_a"] not in rendered_text
    assert source_files["company_id"] not in rendered_text


def test_privacy_redaction_and_scan_pass(source_files):
    _render(source_files)
    parquet = pd.read_parquet(source_files["output"] / "data" / "calls.parquet")
    combined = "\n".join(
        parquet["summary"].tolist()
        + parquet["segments_json"].tolist()
        + parquet["analysis_json"].tolist()
    )
    assert "+7 999 123-45-67" not in combined
    assert "anna@example.com" not in combined
    assert "https://example.com" not in combined
    assert "Иван Иванов" not in combined
    assert "Анна Петрова" not in combined
    assert "Анна, хочу" not in combined
    assert "Здравствуйте, Мария" not in combined
    assert MODULE.REDACTED_PHONE in combined
    assert MODULE.REDACTED_EMAIL in combined
    assert MODULE.REDACTED_URL in combined
    assert MODULE.REDACTED_PERSON in combined
    privacy = json.loads(
        (source_files["output"] / "qa" / "privacy-scan.json").read_text(encoding="utf-8")
    )
    assert privacy["passed"] is True
    assert privacy["finding_counts"] == {}
    assert privacy["adversarial_missed"] == 0
    assert privacy["inventory"]["text_files_by_suffix"][".md"] == 2
    assert privacy["inventory"]["text_files_by_suffix"][".json"] == 2
    assert privacy["inventory"]["parquet_files"] == 1
    expected_string_columns = sum(
        pd.api.types.is_object_dtype(parquet[column].dtype)
        or pd.api.types.is_string_dtype(parquet[column].dtype)
        for column in parquet.columns
    )
    assert privacy["inventory"]["parquet_string_columns"] == expected_string_columns
    manifest = json.loads(
        (source_files["output"] / "manifest.json").read_text(encoding="utf-8")
    )
    assert "Do not infer repeat customers" in manifest["data_quality_warnings"][0]
    assert len(manifest["source"]["calls_sha256"]) == 64
    assert len(manifest["source"]["transcripts_sha256"]) == 64
    assert len(manifest["source"]["analyses_sha256"]) == 64
    assert len(manifest["artifacts"]["parquet_sha256"]) == 64


def test_duplicate_call_id_is_rejected(source_files):
    calls = pd.read_parquet(source_files["calls"])
    pd.concat([calls, calls.iloc[[0]]], ignore_index=True).to_parquet(
        source_files["calls"], index=False
    )
    with pytest.raises(MODULE.CorpusValidationError, match="duplicate"):
        _render(source_files)


def test_foreign_company_is_rejected(source_files):
    calls = pd.read_parquet(source_files["calls"])
    calls.loc[1, "company_id"] = "22222222-2222-2222-2222-222222222222"
    calls.to_parquet(source_files["calls"], index=False)
    with pytest.raises(MODULE.CorpusValidationError, match="company scope mismatch"):
        _render(source_files)


def test_forbidden_columns_are_absent(source_files):
    _render(source_files)
    parquet = pd.read_parquet(source_files["output"] / "data" / "calls.parquet")
    assert not MODULE.FORBIDDEN_OUTPUT_COLUMNS.intersection(parquet.columns)
    assert "raw-contact-id" not in "\n".join(parquet["analysis_json"])
    assert "raw-deal-id" not in "\n".join(parquet["analysis_json"])


def test_h02_tags_are_literal_and_not_inferred():
    assert MODULE.literal_h02_tags("Поздравляем с днем рождения") == ["birthday"]
    assert MODULE.literal_h02_tags("Клиент доволен заказом") == []


def test_name_heuristics_do_not_redact_normal_greeting_request():
    assert (
        MODULE.sanitize_text("Здравствуйте, подскажите стоимость")
        == "Здравствуйте, подскажите стоимость"
    )
    assert MODULE.sanitize_text("Скидка на День Рождения") == "Скидка на День Рождения"
    assert MODULE._privacy_findings("2026-05-26 21:21 — 2026-07-11 01:11:59", ()) == []


@pytest.mark.parametrize(
    "source",
    MODULE.ADVERSARIAL_RU_NAME_CASES,
)
def test_generic_ru_name_lexicon_redacts_adversarial_forms(source):
    sanitized = MODULE.sanitize_text(source)
    assert MODULE.REDACTED_PERSON in sanitized
    assert MODULE.RU_FIRST_NAME_RE.search(sanitized) is None
    assert MODULE._privacy_findings(sanitized, ()) == []


def test_generic_ru_name_lexicon_has_30_plus_unambiguous_names():
    assert len(set(MODULE.RU_FIRST_NAMES)) >= 30
    for ambiguous_common_noun in ("Вера", "Надежда", "Любовь", "Лев", "Роман"):
        assert ambiguous_common_noun not in MODULE.RU_FIRST_NAMES


@pytest.mark.parametrize(
    "source",
    (
        "маргарита подтвердила бронь",
        "говорила с жанной",
        "передайте ахмеду условия",
        "договорились с кузнецовым",
        "ответ от сергеевича получен",
    ),
)
def test_morphology_redacts_names_surnames_and_patronymics_outside_fixed_lexicon(source):
    sanitized = MODULE.sanitize_text(source)
    assert MODULE.REDACTED_PERSON in sanitized
    assert MODULE._has_morph_person_token(sanitized) is False


def test_morphology_keeps_low_probability_business_homonyms():
    source = "валидной брони, лид и описание оффера"
    assert MODULE.sanitize_text(source) == source


@pytest.mark.parametrize(
    "source",
    (
        "-маргарита подтвердила",
        "жанна- ответила",
        "-ахмед- уточнил",
        "ответил -сергеевич-",
    ),
)
def test_morphology_strips_ascii_hyphens_at_person_token_boundaries(source):
    sanitized = MODULE.sanitize_text(source)
    assert MODULE.REDACTED_PERSON in sanitized
    assert MODULE._has_morph_person_token(sanitized) is False


def test_audit_existing_output_covers_all_finalized_text_and_parquet_strings(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    for suffix in (".md", ".json", ".yaml", ".yml"):
        (root / f"safe{suffix}").write_text(
            f"safe {MODULE.REDACTED_PERSON}\n",
            encoding="utf-8",
        )
    pd.DataFrame(
        {
            "text_a": ["safe", MODULE.REDACTED_PERSON],
            "text_b": ["safe", "safe"],
            "number": [1, 2],
        }
    ).to_parquet(root / "safe.parquet", index=False)

    report = MODULE.audit_existing_output(root)

    assert report["passed"] is True
    assert report["finding_counts"] == {}
    assert report["adversarial_missed"] == 0
    assert report["inventory"]["text_files"] == 4
    assert report["inventory"]["text_files_by_suffix"] == {
        ".json": 1,
        ".md": 1,
        ".yaml": 1,
        ".yml": 1,
    }
    assert report["inventory"]["parquet_files"] == 1
    assert report["inventory"]["parquet_rows"] == 2
    assert report["inventory"]["parquet_string_columns"] == 2
    assert report["inventory"]["parquet_string_values"] == 4
    assert (root / "qa" / "privacy-scan.json").exists()
    repeated = MODULE.audit_existing_output(root)
    assert repeated["inventory"] == report["inventory"]


def test_audit_existing_output_detects_names_in_each_supported_surface(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    leak = MODULE.ADVERSARIAL_RU_NAME_CASES[0]
    for suffix in (".md", ".json", ".yaml", ".yml"):
        (root / f"leak{suffix}").write_text(leak, encoding="utf-8")
    pd.DataFrame({"string_column": [leak], "number": [1]}).to_parquet(
        root / "leak.parquet",
        index=False,
    )

    report = MODULE.audit_existing_output(root)

    assert report["passed"] is False
    assert report["finding_counts"]["ru_first_name"] == 5
    assert len(report["artifacts_with_findings"]) == 5


def test_curated_docs_use_lexicon_without_generic_title_shape_false_positive(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "analysis.md").write_text(
        "# Risk Assumption Tests\nЭто граница snapshot. Следовательно, вывод ограничен.\n",
        encoding="utf-8",
    )
    report = MODULE.audit_existing_output(root)
    assert report["passed"] is True


def test_audit_existing_output_cli_mode_does_not_require_render_inputs(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "safe.md").write_text("safe", encoding="utf-8")
    assert MODULE.main(["--audit-existing-output", str(root)]) == 0
    report = json.loads((root / "qa" / "privacy-scan.json").read_text(encoding="utf-8"))
    assert report["passed"] is True


def test_duration_qa_reports_but_does_not_trim_or_fail(source_files):
    calls = pd.read_parquet(source_files["calls"])
    calls.loc[0, "duration_sec"] = 1
    calls.to_parquet(source_files["calls"], index=False)
    transcripts = pd.read_parquet(source_files["transcripts"])
    segments = json.loads(transcripts.loc[0, "segments"])
    segments[-1]["start"] = 40.0
    transcripts.loc[0, "segments"] = json.dumps(segments, ensure_ascii=False)
    transcripts.to_parquet(source_files["transcripts"], index=False)

    reconciliation = _render(source_files)

    assert reconciliation["duration_qa"]["last_timestamp_over_call_duration_plus_5s"] == 1
    assert reconciliation["duration_qa"]["last_timestamp_over_call_duration_plus_30s"] == 1
    parquet = pd.read_parquet(source_files["output"] / "data" / "calls.parquet")
    available = parquet.loc[parquet["transcript_status"] == "available"].iloc[0]
    rendered_segments = json.loads(available["segments_json"])
    assert len(rendered_segments) == 4
    assert rendered_segments[-1]["timestamp"] == "40.0"


def test_numeric_timestamp_uses_last_endpoint_from_source_range():
    assert MODULE._numeric_timestamp([12.0, 15.5]) == 15.5
    assert MODULE._numeric_timestamp("[12.0, 15.5]") == 15.5


def test_overwrite_preserves_curated_root_docs_and_audits_them(source_files):
    output = source_files["output"]
    output.mkdir()
    curated = output / "workflow.yaml"
    curated.write_text("client_alias: harizma-club\n", encoding="utf-8")

    MODULE.render_corpus(
        calls_path=source_files["calls"],
        transcripts_path=source_files["transcripts"],
        analyses_path=source_files["analyses"],
        output_dir=output,
        expected_company_id=source_files["company_id"],
        snapshot_at="2026-07-16T00:00:00Z",
        overwrite=True,
    )

    assert curated.read_text(encoding="utf-8") == "client_alias: harizma-club\n"
    privacy = json.loads((output / "qa" / "privacy-scan.json").read_text(encoding="utf-8"))
    assert privacy["inventory"]["text_files_by_suffix"][".yaml"] == 1
