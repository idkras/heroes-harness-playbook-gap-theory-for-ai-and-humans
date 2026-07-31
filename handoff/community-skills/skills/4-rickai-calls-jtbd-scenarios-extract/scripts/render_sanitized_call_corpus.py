#!/usr/bin/env python3
# /// script
# dependencies = [
#   "pandas>=2.0",
#   "pyarrow>=15.0",
#   "pymorphy3>=2.0,<3",
# ]
# ///
"""Render a privacy-safe, one-call-per-row/Markdown corpus from Supabase parquet.

The source parquet files remain local bronze data. This renderer creates a
shareable corpus without raw call/company/contact identifiers, phone hashes,
audio URLs, operator names, or unredacted obvious PII.

Outputs below ``--output-dir``:

* ``data/calls.parquet`` — one sanitized row per source call;
* ``calls/YYYY/MM/<date>__call-<safe_ref>.md`` — one full transcript or stub;
* ``manifest.json`` — deterministic artifact index;
* ``qa/reconciliation.json`` — 1:1 source/output count proof;
* ``qa/privacy-scan.json`` — post-render privacy scan.

The renderer does not infer customer intent. H-02 tags are literal keyword
matches only and are explicitly labelled as such.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import pymorphy3

REDACTION_VERSION = "call-corpus-redaction-v1"
REDACTED_EMAIL = "[REDACTED_EMAIL]"
REDACTED_PHONE = "[REDACTED_PHONE]"
REDACTED_URL = "[REDACTED_URL]"
REDACTED_PERSON = "[REDACTED_PERSON]"
REDACTED_ID = "[REDACTED_ID]"

FORBIDDEN_OUTPUT_COLUMNS = frozenset(
    {
        "id",
        "call_id",
        "company_id",
        "source_id",
        "external_id",
        "audio_url",
        "operator_id",
        "operator_name",
        "client_phone",
        "company_phone",
        "client_phone_hash",
        "client_phone_hash_6",
        "client_phone_hash_9",
        "client_phone_masked",
        "company_phone_masked",
        "rick_contact_id",
        "rick_user_id",
        "rick_rid",
        "counter_client_id",
        "contact_id",
        "transaction_id",
        "crm_deal_id",
    }
)

SAFE_ANALYSIS_FIELDS = (
    "segment_abcd",
    "qualification",
    "segment_goal",
    "desire",
    "blocker",
    "when_trigger",
    "situation",
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
)

H02_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "birthday": ("день рождения", "днём рождения", "днем рождения", "именин"),
    "loyalty": ("лояльност", "постоянн", "повторн", "верну", "снова"),
    "discount": ("скидк", "промокод", "бонус", "подар"),
    "consent": ("соглас", "рассыл", "отпис", "не звон", "не пиш"),
    "channel": ("whatsapp", "ватсап", "telegram", "телеграм", "смс", "sms"),
}

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
UUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)
# Ten digits is the shortest supported phone signal. A seven-digit pattern
# false-positives on segment timestamps, order numbers, and decimal values.
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]*){10,15}(?!\w)")
ISO_DATETIME_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?\b"
)
NAME_CUE_RE = re.compile(
    r"(?iu)\b(?:меня\s+зовут|мо[её]\s+имя|это|я\s*[-—])\s+"
    r"([А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+){0,2})"
)
PERSON_PAIR_RE = re.compile(
    r"(?u)\b([А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}"
    r"|[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b"
)
SAFE_TITLE_PAIR_RE = re.compile(
    r"(?iu)\b(?:день\s+рождения|добрый\s+(?:день|вечер)|новый\s+год|"
    r"friends\s+hall|френдс\s+холл|харизма\s+клуб)\b"
)
DIRECT_ADDRESS_RE = re.compile(
    r"(?u)(?:(?<=^)|(?<=[.!?]\s))"
    r"(?!(?i:здравствуйте|добрый|привет)\b)"
    r"([А-ЯЁ][а-яё]{2,}|[A-Z][a-z]{2,})(?=\s*[,!])"
)
GREETING_NAME_RE = re.compile(
    r"(?u)\b((?i:здравствуйте|добрый\s+(?:день|вечер)|привет)"
    r"(?i:\s+ещ[её]\s+раз)?\s*[,!]?\s+)"
    r"([А-ЯЁA-Z][а-яёa-z]{2,})(?=\b)"
)

# Deliberately excludes first names that are common Russian nouns (for example,
# words meaning faith, hope, love, lion, or novel) to keep false positives
# bounded. The list is still broad enough for a generic 30+ name safety net.
RU_FIRST_NAMES = (
    "Александр",
    "Алексей",
    "Андрей",
    "Антон",
    "Артем",
    "Артём",
    "Борис",
    "Вадим",
    "Валерий",
    "Виктор",
    "Владимир",
    "Владислав",
    "Георгий",
    "Денис",
    "Дмитрий",
    "Евгений",
    "Иван",
    "Игорь",
    "Илья",
    "Кирилл",
    "Константин",
    "Максим",
    "Михаил",
    "Николай",
    "Олег",
    "Павел",
    "Сергей",
    "Станислав",
    "Тимур",
    "Юрий",
    "Ярослав",
    "Анна",
    "Анастасия",
    "Алина",
    "Алёна",
    "Валентина",
    "Виктория",
    "Дарья",
    "Екатерина",
    "Елена",
    "Ирина",
    "Ксения",
    "Марина",
    "Мария",
    "Наталья",
    "Олеся",
    "Ольга",
    "Полина",
    "Светлана",
    "Татьяна",
    "Юлия",
)

RU_NAME_IRREGULAR_FORMS: Mapping[str, tuple[str, ...]] = {
    "Илья": ("Ильи", "Илье", "Илью", "Ильёй", "Ильею"),
    "Павел": ("Павла", "Павлу", "Павлом", "Павле"),
    "Дарья": ("Дарьи", "Дарье", "Дарью", "Дарьей", "Дарьею"),
}

ADVERSARIAL_RU_NAME_CASES = (
    "Сергей уточнил детали.",  # single capitalized name at sentence start
    "Передайте Сергею детали.",  # dative after a verb
    "говорила с сергеем вчера.",  # lowercase instrumental
    "анна петрова подтвердила.",  # lowercase first name + surname
    "Олеся.",
    "Олеся меня зовут.",
    "Ну, Олеся, уточните.",
    "Да, Олеся, добрый день.",
    "с вами, Олесей, прощаюсь.",
)

AUDITED_TEXT_SUFFIXES = frozenset({".md", ".json", ".yaml", ".yml"})
GENERATED_ROOT_ENTRIES = frozenset({"calls", "data", "manifest.json", "qa"})


def _ru_name_surfaces(name: str) -> set[str]:
    forms = {name, *RU_NAME_IRREGULAR_FORMS.get(name, ())}
    if name in RU_NAME_IRREGULAR_FORMS:
        return forms
    if name.endswith("ия"):
        stem = name[:-2]
        forms.update((stem + "ии", stem + "ию", stem + "ией", stem + "иею"))
    elif name.endswith("а"):
        stem = name[:-1]
        genitive = stem + ("и" if stem[-1:].lower() in {"г", "к", "х"} else "ы")
        forms.update((genitive, stem + "е", stem + "у", stem + "ой", stem + "ою"))
    elif name.endswith("я"):
        stem = name[:-1]
        forms.update((stem + "и", stem + "е", stem + "ю", stem + "ей", stem + "ею"))
    elif name.endswith("ий"):
        stem = name[:-2]
        forms.update((stem + "ия", stem + "ию", stem + "ием", stem + "ии"))
    elif name.endswith("ей"):
        stem = name[:-2]
        forms.update((stem + "ея", stem + "ею", stem + "еем", stem + "ее"))
    elif name.endswith("й"):
        stem = name[:-1]
        forms.update((stem + "я", stem + "ю", stem + "ем", stem + "е"))
    elif name.endswith("ь"):
        stem = name[:-1]
        forms.update((stem + "я", stem + "ю", stem + "ем", stem + "е"))
    else:
        forms.update((name + "а", name + "у", name + "ом", name + "е"))
    return forms


RU_FIRST_NAME_SURFACES = frozenset(
    surface
    for first_name in RU_FIRST_NAMES
    for surface in _ru_name_surfaces(first_name)
)
_RU_NAME_ALTERNATIVES = "|".join(
    sorted((re.escape(value) for value in RU_FIRST_NAME_SURFACES), key=len, reverse=True)
)
RU_FIRST_NAME_RE = re.compile(
    rf"(?iu)(?<![а-яёa-z])(?:{_RU_NAME_ALTERNATIVES})(?![а-яёa-z])"
)
RU_WORD_RE = re.compile(r"(?iu)(?<![а-яё])[а-яё][а-яё-]{1,}(?![а-яё])")
_MORPH = pymorphy3.MorphAnalyzer()
_PERSON_GRAMMEMES = frozenset({"Name", "Surn", "Patr"})
# OpenCorpora contains low-probability homonyms such as "бронь" -> the name
# "Броня" and "лид" -> "Лида". Requiring a majority-probability parse keeps
# those business words while still catching common names, surnames and
# patronymics, including lowercase ASR output.
_MIN_PERSON_PARSE_SCORE = 0.5


class CorpusValidationError(ValueError):
    """Raised when source data cannot prove a safe 1:1 corpus."""


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
        if isinstance(missing, bool):
            return missing
    except (TypeError, ValueError):
        pass
    return False


def _parse_jsonish(value: Any, *, expected: type) -> Any:
    if _is_missing(value):
        return expected()
    if isinstance(value, expected):
        return value
    if hasattr(value, "tolist"):
        value = value.tolist()
        if isinstance(value, expected):
            return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return expected()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return expected()
        return parsed if isinstance(parsed, expected) else expected()
    return expected()


def safe_call_ref(call_id: Any, company_id: Any) -> str:
    """Return a deterministic, non-reversible reference without exposing IDs."""
    material = f"{REDACTION_VERSION}\0{company_id}\0{call_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:20]


def _known_person_patterns(values: Iterable[Any]) -> tuple[re.Pattern[str], ...]:
    escaped_values: set[str] = set()
    for value in values:
        if _is_missing(value):
            continue
        text = str(value).strip()
        if len(text) < 2:
            continue
        escaped_values.add(re.escape(text))
    if not escaped_values:
        return ()
    # One alternation is materially faster than applying thousands of repeated
    # operator-name regexes to every transcript segment.
    alternatives = "|".join(sorted(escaped_values, key=len, reverse=True))
    return (re.compile(rf"(?iu)(?<!\w)(?:{alternatives})(?!\w)"),)


def _redact_person_pairs_preserving_safe_titles(text: str) -> str:
    protected_pairs: dict[str, str] = {}

    def protect_pair(match: re.Match[str]) -> str:
        token = f"[[SAFE_TITLE_PAIR_{len(protected_pairs)}]]"
        protected_pairs[token] = match.group(0)
        return token

    result = SAFE_TITLE_PAIR_RE.sub(protect_pair, text)
    previous = None
    while previous != result:
        previous = result
        result = PERSON_PAIR_RE.sub(REDACTED_PERSON, result)
    for token, original in protected_pairs.items():
        result = result.replace(token, original)
    return result


@lru_cache(maxsize=100_000)
def _is_morph_person_token(token: str) -> bool:
    # ASR frequently glues a pause marker to a word as an ASCII hyphen
    # ("-имя" / "имя-"). Keep meaningful internal hyphens, but never send
    # punctuation at token boundaries to the morphological analyzer.
    normalized = token.strip("-").lower()
    if not normalized:
        return False
    return any(
        _PERSON_GRAMMEMES.intersection(parse.tag.grammemes)
        and parse.score >= _MIN_PERSON_PARSE_SCORE
        for parse in _MORPH.parse(normalized)
    )


def _redact_morph_person_tokens(text: str) -> str:
    return RU_WORD_RE.sub(
        lambda match: REDACTED_PERSON
        if _is_morph_person_token(match.group(0))
        else match.group(0),
        text,
    )


def _has_morph_person_token(text: str) -> bool:
    return any(_is_morph_person_token(match.group(0)) for match in RU_WORD_RE.finditer(text))


def sanitize_text(text: Any, known_people: Sequence[re.Pattern[str]] = ()) -> str:
    """Redact obvious PII while retaining transcript wording and order."""
    if _is_missing(text):
        return ""
    result = str(text)
    result = EMAIL_RE.sub(REDACTED_EMAIL, result)
    result = URL_RE.sub(REDACTED_URL, result)
    result = UUID_RE.sub(REDACTED_ID, result)
    result = PHONE_RE.sub(REDACTED_PHONE, result)
    for pattern in known_people:
        result = pattern.sub(REDACTED_PERSON, result)
    result = _redact_morph_person_tokens(result)
    result = RU_FIRST_NAME_RE.sub(REDACTED_PERSON, result)
    result = NAME_CUE_RE.sub(lambda match: match.group(0).replace(match.group(1), REDACTED_PERSON), result)
    result = _redact_person_pairs_preserving_safe_titles(result)
    result = GREETING_NAME_RE.sub(lambda match: match.group(1) + REDACTED_PERSON, result)
    result = DIRECT_ADDRESS_RE.sub(REDACTED_PERSON, result)
    result = _redact_person_pairs_preserving_safe_titles(result)
    return result


def _sanitize_value(value: Any, known_people: Sequence[re.Pattern[str]]) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_value(item, known_people)
            for key, item in value.items()
            if str(key) not in FORBIDDEN_OUTPUT_COLUMNS
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item, known_people) for item in value]
    if isinstance(value, str):
        return sanitize_text(value, known_people)
    if isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(value, known_people)


def _validate_unique(df: pd.DataFrame, column: str, label: str) -> None:
    if column not in df.columns:
        raise CorpusValidationError(f"{label}: required column {column!r} is missing")
    duplicate_count = int(df[column].duplicated().sum())
    if duplicate_count:
        raise CorpusValidationError(f"{label}: {duplicate_count} duplicate {column} values")


def validate_sources(
    calls: pd.DataFrame,
    transcripts: pd.DataFrame,
    analyses: pd.DataFrame,
    expected_company_id: str,
) -> None:
    """Reject ambiguous grain, foreign-company rows, and orphan joins."""
    _validate_unique(calls, "id", "calls")
    _validate_unique(transcripts, "call_id", "transcripts")
    _validate_unique(analyses, "call_id", "analyses")
    if "company_id" not in calls.columns:
        raise CorpusValidationError("calls: required column 'company_id' is missing")
    company_values = {str(value) for value in calls["company_id"].dropna().unique()}
    if company_values != {str(expected_company_id)}:
        raise CorpusValidationError(
            f"calls: company scope mismatch; expected one company, observed {len(company_values)}"
        )
    call_ids = set(calls["id"].astype(str))
    for label, frame in (("transcripts", transcripts), ("analyses", analyses)):
        orphan_ids = set(frame["call_id"].astype(str)) - call_ids
        if orphan_ids:
            raise CorpusValidationError(f"{label}: {len(orphan_ids)} call_id values are outside calls")


def _speaker_role(raw_speaker: Any) -> str:
    if _is_missing(raw_speaker):
        return "participant"
    value = str(raw_speaker).strip().lower()
    if value in {"agent", "operator", "manager", "менеджер", "оператор", "0"}:
        return "agent"
    if value in {"client", "customer", "caller", "клиент", "1"}:
        return "client"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:6]
    return f"participant_{digest}"


def _segment_timestamp(segment: Mapping[str, Any]) -> str | None:
    for key in ("start", "start_time", "timestamp", "time", "offset"):
        value = segment.get(key)
        if not _is_missing(value):
            return str(value)
    return None


def _numeric_timestamp(value: Any) -> float | None:
    if _is_missing(value):
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        for candidate in reversed(value):
            parsed = _numeric_timestamp(candidate)
            if parsed is not None:
                return parsed
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                return _numeric_timestamp(json.loads(stripped))
            except json.JSONDecodeError:
                return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_segments(
    raw_segments: Any,
    fallback_text: Any,
    known_people: Sequence[re.Pattern[str]],
) -> list[dict[str, Any]]:
    """Keep source segment order and sanitize every text payload."""
    segments = _parse_jsonish(raw_segments, expected=list)
    normalized: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(segments, start=1):
        if isinstance(raw, Mapping):
            text = raw.get("text", raw.get("content", raw.get("utterance", "")))
            speaker = raw.get("speaker", raw.get("role", raw.get("speaker_id")))
            timestamp = _segment_timestamp(raw)
        else:
            text = raw
            speaker = None
            timestamp = None
        cleaned = sanitize_text(text, known_people).strip()
        if not cleaned:
            continue
        item: dict[str, Any] = {
            "ordinal": ordinal,
            "speaker_role": _speaker_role(speaker),
            "text": cleaned,
        }
        if timestamp is not None:
            item["timestamp"] = timestamp
        normalized.append(item)
    if normalized:
        return normalized
    fallback = sanitize_text(fallback_text, known_people).strip()
    if fallback:
        return [{"ordinal": 1, "speaker_role": "participant", "text": fallback}]
    return []


def _analysis_payload(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {}
    result = _parse_jsonish(row.get("result"), expected=dict)
    analysis_fields = _parse_jsonish(row.get("analysis_fields"), expected=dict)
    payload: dict[str, Any] = {}
    for field in SAFE_ANALYSIS_FIELDS:
        value = result.get(field, analysis_fields.get(field))
        if not _is_missing(value) and str(value).strip():
            payload[field] = value
    return payload


def literal_h02_tags(*texts: str) -> list[str]:
    """Return literal keyword-family matches; this is not an intent classifier."""
    haystack = "\n".join(texts).lower()
    return [
        tag
        for tag, needles in H02_KEYWORDS.items()
        if any(needle in haystack for needle in needles)
    ]


def _iso_date(value: Any) -> tuple[str, str, str]:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return "unknown", "unknown", "unknown-date"
    return parsed.strftime("%Y"), parsed.strftime("%m"), parsed.strftime("%Y-%m-%d")


def _safe_scalar(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _render_markdown(record: Mapping[str, Any]) -> str:
    lines = [
        f"# Звонок {record['call_ref']}",
        "",
        f"- Дата: {record['call_date'] or 'не указана'}",
        f"- Длительность, сек.: {record['duration_sec'] if record['duration_sec'] is not None else 'не указана'}",
        f"- Направление: {record['direction'] or 'не указано'}",
        f"- Статус обработки: {record['processing_status'] or 'не указан'}",
        f"- Статус транскрипта: {record['transcript_status']}",
        f"- Статус анализа: {record['analysis_status']}",
        f"- H-02 literal tags: {', '.join(record['h02_literal_tags']) or 'нет'}",
        "",
        "> H-02 tags означают только буквальное совпадение словарных маркеров, не доказательство намерения.",
        "",
        "## Краткое описание из источника",
        "",
        record["summary"] or "Нет исходного summary; факты не достраивались.",
        "",
        "## Транскрипт",
        "",
    ]
    segments = record["segments"]
    if not segments:
        lines.extend(
            [
                "**Явный stub:** транскрипт отсутствует в source snapshot.",
                "",
            ]
        )
    else:
        for segment in segments:
            prefix = f"[{segment['timestamp']}] " if segment.get("timestamp") else ""
            lines.append(
                f"{segment['ordinal']}. {prefix}**{segment['speaker_role']}:** {segment['text']}"
            )
        lines.append("")
    lines.extend(
        [
            "## Безопасные поля анализа",
            "",
            "```json",
            json.dumps(record["analysis"], ensure_ascii=False, indent=2, default=_json_default),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _privacy_findings(
    text: str,
    known_people: Sequence[re.Pattern[str]],
    *,
    include_shape_heuristics: bool = True,
) -> list[str]:
    scan_text = text
    for marker in (
        REDACTED_EMAIL,
        REDACTED_PHONE,
        REDACTED_URL,
        REDACTED_PERSON,
        REDACTED_ID,
    ):
        # Keep a non-letter separator so removing the marker cannot join two
        # surrounding fragments into a new synthetic PII match.
        scan_text = scan_text.replace(marker, "◼")
    scan_text = SAFE_TITLE_PAIR_RE.sub("◼", scan_text)
    scan_text = ISO_DATETIME_RE.sub("◼", scan_text)
    findings: list[str] = []
    patterns = [
        ("email", EMAIL_RE),
        ("url", URL_RE),
        ("uuid", UUID_RE),
        ("phone", PHONE_RE),
        ("ru_first_name", RU_FIRST_NAME_RE),
    ]
    if include_shape_heuristics:
        patterns.extend(
            [
                ("name_cue", NAME_CUE_RE),
                ("person_pair", PERSON_PAIR_RE),
                ("greeting_name", GREETING_NAME_RE),
                ("direct_address", DIRECT_ADDRESS_RE),
            ]
        )
    for label, pattern in patterns:
        if pattern.search(scan_text):
            findings.append(label)
    if _has_morph_person_token(scan_text):
        findings.append("ru_morph_person")
    if any(pattern.search(scan_text) for pattern in known_people):
        findings.append("known_person")
    return findings


def _adversarial_missed_count() -> int:
    missed = 0
    for case in ADVERSARIAL_RU_NAME_CASES:
        sanitized = sanitize_text(case)
        if REDACTED_PERSON not in sanitized or RU_FIRST_NAME_RE.search(sanitized):
            missed += 1
    return missed


def audit_existing_output(
    root: Path,
    known_people: Sequence[re.Pattern[str]] = (),
) -> dict[str, Any]:
    """Audit finalized text files and every Parquet string-like column.

    The report itself is excluded to keep repeated audits idempotent.
    """
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"audit root does not exist: {root}")
    report_path = root / "qa" / "privacy-scan.json"
    findings_by_artifact: list[dict[str, Any]] = []
    finding_counts: dict[str, int] = {}
    inventory = {
        "text_files": 0,
        "text_files_by_suffix": {suffix: 0 for suffix in sorted(AUDITED_TEXT_SUFFIXES)},
        "parquet_files": 0,
        "parquet_rows": 0,
        "parquet_string_columns": 0,
        "parquet_string_values": 0,
    }

    def record(relative: str, location: str, findings: Sequence[str]) -> None:
        unique_findings = sorted(set(findings))
        if not unique_findings:
            return
        findings_by_artifact.append(
            {"path": relative, "location": location, "finding_types": unique_findings}
        )
        for finding in unique_findings:
            finding_counts[finding] = finding_counts.get(finding, 0) + 1

    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        if path.resolve() == report_path.resolve():
            continue
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        if suffix in AUDITED_TEXT_SUFFIXES:
            inventory["text_files"] += 1
            inventory["text_files_by_suffix"][suffix] += 1
            use_shape_heuristics = relative.startswith("calls/")
            record(
                relative,
                "whole_file",
                _privacy_findings(
                    path.read_text(encoding="utf-8"),
                    known_people,
                    include_shape_heuristics=use_shape_heuristics,
                ),
            )
            continue
        if suffix != ".parquet":
            continue
        inventory["parquet_files"] += 1
        frame = pd.read_parquet(path)
        inventory["parquet_rows"] += len(frame)
        for column in frame.columns:
            series = frame[column]
            if not (
                pd.api.types.is_object_dtype(series.dtype)
                or pd.api.types.is_string_dtype(series.dtype)
            ):
                continue
            inventory["parquet_string_columns"] += 1
            for row_number, value in enumerate(series):
                if _is_missing(value):
                    continue
                inventory["parquet_string_values"] += 1
                record(
                    relative,
                    f"column={column};row={row_number}",
                    _privacy_findings(str(value), known_people),
                )

    adversarial_missed = _adversarial_missed_count()
    report = {
        "redaction_version": REDACTION_VERSION,
        "audit_root": ".",
        "inventory": inventory,
        "finding_counts": finding_counts,
        "artifacts_with_findings": findings_by_artifact,
        "adversarial_cases": len(ADVERSARIAL_RU_NAME_CASES),
        "adversarial_missed": adversarial_missed,
        "passed": not finding_counts and adversarial_missed == 0,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def render_corpus(
    *,
    calls_path: Path,
    transcripts_path: Path,
    analyses_path: Path,
    output_dir: Path,
    expected_company_id: str,
    snapshot_at: str,
    extra_people: Sequence[str] = (),
    overwrite: bool = False,
) -> dict[str, Any]:
    calls = pd.read_parquet(calls_path)
    transcripts = pd.read_parquet(transcripts_path)
    analyses = pd.read_parquet(analyses_path)
    validate_sources(calls, transcripts, analyses, expected_company_id)

    known_people_values = list(extra_people)
    if "operator_name" in calls.columns:
        known_people_values.extend(calls["operator_name"].dropna().astype(str).tolist())
    known_people = _known_person_patterns(known_people_values)

    transcript_by_call = {
        str(row["call_id"]): row for row in transcripts.to_dict(orient="records")
    }
    analysis_by_call = {
        str(row["call_id"]): row for row in analyses.to_dict(orient="records")
    }

    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() and not overwrite:
        raise FileExistsError(f"output exists: {output_dir}; pass --overwrite to replace it")

    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.", dir=output_dir.parent) as temp_name:
        temp_root = Path(temp_name)
        data_dir = temp_root / "data"
        calls_dir = temp_root / "calls"
        qa_dir = temp_root / "qa"
        data_dir.mkdir()
        calls_dir.mkdir()
        qa_dir.mkdir()

        safe_rows: list[dict[str, Any]] = []
        manifest_calls: list[dict[str, Any]] = []
        md_count = 0
        stub_count = 0
        missing_transcript_row_count = 0
        empty_transcript_row_count = 0
        duration_comparison_count = 0
        duration_over_5s_count = 0
        duration_over_30s_count = 0

        for call in calls.to_dict(orient="records"):
            raw_call_id = str(call["id"])
            ref = safe_call_ref(raw_call_id, call["company_id"])
            transcript = transcript_by_call.get(raw_call_id)
            missing_transcript_row_count += int(transcript is None)
            analysis_row = analysis_by_call.get(raw_call_id)
            segments = normalize_segments(
                transcript.get("segments") if transcript else None,
                transcript.get("text") if transcript else None,
                known_people,
            )
            if segments:
                last_timestamp = _numeric_timestamp(segments[-1].get("timestamp"))
                try:
                    call_duration = float(call.get("duration_sec"))
                except (TypeError, ValueError):
                    call_duration = None
                if last_timestamp is not None and call_duration is not None:
                    duration_comparison_count += 1
                    duration_delta = last_timestamp - call_duration
                    duration_over_5s_count += int(duration_delta > 5)
                    duration_over_30s_count += int(duration_delta > 30)
            raw_analysis = _analysis_payload(analysis_row)
            safe_analysis = _sanitize_value(raw_analysis, known_people)
            summary_source = ""
            if analysis_row:
                summary_source = analysis_row.get("summary") or ""
            if not summary_source:
                summary_source = call.get("summary") or ""
            summary = sanitize_text(summary_source, known_people).strip()
            joined_segment_text = "\n".join(segment["text"] for segment in segments)
            tags = literal_h02_tags(summary, joined_segment_text, json.dumps(safe_analysis, ensure_ascii=False))
            year, month, day = _iso_date(call.get("date"))
            relative_md = Path("calls") / year / month / f"{day}__call-{ref}.md"
            transcript_status = "available" if segments else "missing_stub"
            empty_transcript_row_count += int(transcript is not None and not segments)
            analysis_status = "available" if safe_analysis or summary else "missing"
            record = {
                "call_ref": ref,
                "call_date": _safe_scalar(call.get("date")),
                "duration_sec": _safe_scalar(call.get("duration_sec")),
                "direction": sanitize_text(call.get("direction"), known_people),
                "processing_status": sanitize_text(call.get("status"), known_people),
                "transcript_status": transcript_status,
                "analysis_status": analysis_status,
                "summary": summary,
                "segments": segments,
                "analysis": safe_analysis,
                "h02_literal_tags": tags,
            }
            markdown = _render_markdown(record)
            md_path = temp_root / relative_md
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(markdown, encoding="utf-8")
            md_sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

            safe_rows.append(
                {
                    "call_ref": ref,
                    "call_date": record["call_date"],
                    "duration_sec": record["duration_sec"],
                    "direction": record["direction"],
                    "processing_status": record["processing_status"],
                    "transcript_status": transcript_status,
                    "analysis_status": analysis_status,
                    "summary": summary,
                    "segments_json": json.dumps(segments, ensure_ascii=False, default=_json_default),
                    "analysis_json": json.dumps(safe_analysis, ensure_ascii=False, default=_json_default),
                    "h02_literal_tags_json": json.dumps(tags, ensure_ascii=False),
                    "markdown_path": relative_md.as_posix(),
                    "markdown_sha256": md_sha,
                }
            )
            manifest_calls.append(
                {
                    "call_ref": ref,
                    "markdown_path": relative_md.as_posix(),
                    "markdown_sha256": md_sha,
                    "transcript_status": transcript_status,
                }
            )
            md_count += 1
            stub_count += int(not segments)

        safe_df = pd.DataFrame(safe_rows)
        forbidden_present = sorted(FORBIDDEN_OUTPUT_COLUMNS.intersection(safe_df.columns))
        if forbidden_present:
            raise CorpusValidationError(f"forbidden output columns: {forbidden_present}")
        if safe_df["call_ref"].duplicated().any():
            raise CorpusValidationError("safe call_ref collision detected")
        parquet_path = data_dir / "calls.parquet"
        safe_df.to_parquet(parquet_path, index=False)

        parquet_count = len(pd.read_parquet(parquet_path))
        source_refs = set(safe_df["call_ref"])
        manifest_refs = {item["call_ref"] for item in manifest_calls}
        missing_refs = sorted(source_refs - manifest_refs)
        extra_refs = sorted(manifest_refs - source_refs)
        duplicate_refs = len(manifest_calls) - len(manifest_refs)
        reconciliation = {
            "snapshot_at": snapshot_at,
            "source_calls": int(len(calls)),
            "source_unique_call_ids": int(calls["id"].nunique()),
            "source_transcripts": int(len(transcripts)),
            "source_analyses": int(len(analyses)),
            "parquet_rows": int(parquet_count),
            "markdown_files": int(md_count),
            "missing_transcript_stubs": int(stub_count),
            "missing_transcript_rows": int(missing_transcript_row_count),
            "empty_transcript_rows": int(empty_transcript_row_count),
            "duration_qa": {
                "numeric_last_timestamp_comparisons": int(duration_comparison_count),
                "last_timestamp_over_call_duration_plus_5s": int(duration_over_5s_count),
                "last_timestamp_over_call_duration_plus_30s": int(duration_over_30s_count),
                "warning": (
                    "Source call duration and transcript timestamp semantics may differ. "
                    "Rows are reported only; transcript text is not failed, trimmed, reordered, "
                    "or otherwise changed by this QA."
                ),
            },
            "missing_refs": missing_refs,
            "extra_refs": extra_refs,
            "duplicate_refs": int(duplicate_refs),
            "foreign_company_rows": 0,
            "identity_evidence_warning": (
                "client_phone*, company_phone*, hashes, and mirrored side fields are excluded "
                "and MUST NOT be used to infer a repeat customer; call id grain is the only "
                "reconciliation identity in this corpus"
            ),
            "counts_match": bool(
                len(calls) == calls["id"].nunique() == parquet_count == md_count
                and not missing_refs
                and not extra_refs
                and duplicate_refs == 0
            ),
        }
        if not reconciliation["counts_match"]:
            raise CorpusValidationError(f"reconciliation failed: {reconciliation}")

        manifest = {
            "schema_version": 1,
            "redaction_version": REDACTION_VERSION,
            "snapshot_at": snapshot_at,
            "source": {
                "calls_filename": calls_path.name,
                "calls_sha256": _sha256_file(calls_path),
                "transcripts_filename": transcripts_path.name,
                "transcripts_sha256": _sha256_file(transcripts_path),
                "analyses_filename": analyses_path.name,
                "analyses_sha256": _sha256_file(analyses_path),
                "date_min": _json_default(pd.to_datetime(calls["date"], errors="coerce").min()),
                "date_max": _json_default(pd.to_datetime(calls["date"], errors="coerce").max()),
            },
            "data_quality_warnings": [
                (
                    "Do not infer repeat customers from client_phone*, company_phone*, or phone "
                    "hashes. Direction-dependent mirrored side fields are not a stable person "
                    "identity; those fields are excluded from this corpus."
                )
            ],
            "counts": {
                "calls": len(calls),
                "parquet_rows": parquet_count,
                "markdown_files": md_count,
                "missing_transcript_stubs": stub_count,
                "missing_transcript_rows": missing_transcript_row_count,
                "empty_transcript_rows": empty_transcript_row_count,
            },
            "artifacts": {
                "parquet": "data/calls.parquet",
                "parquet_sha256": _sha256_file(parquet_path),
                "reconciliation": "qa/reconciliation.json",
                "privacy_scan": "qa/privacy-scan.json",
            },
            "calls": manifest_calls,
        }
        (temp_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        (qa_dir / "reconciliation.json").write_text(
            json.dumps(reconciliation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if output_dir.exists():
            for existing in output_dir.iterdir():
                if existing.name in GENERATED_ROOT_ENTRIES:
                    continue
                destination = temp_root / existing.name
                if existing.is_dir():
                    shutil.copytree(existing, destination)
                else:
                    shutil.copy2(existing, destination)
        privacy = audit_existing_output(temp_root, known_people)
        if not privacy["passed"]:
            counts = privacy["finding_counts"]
            raise CorpusValidationError(
                "privacy scan failed: "
                + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
                + f"; adversarial_missed={privacy['adversarial_missed']}"
            )

        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.move(str(temp_root), str(output_dir))

    return reconciliation


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", type=Path, help="calls.parquet")
    parser.add_argument("--transcripts", type=Path, help="transcripts.parquet")
    parser.add_argument("--analyses", type=Path, help="analyses.parquet")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--expected-company-id")
    parser.add_argument(
        "--audit-existing-output",
        type=Path,
        help="Audit an already finalized corpus and rewrite qa/privacy-scan.json",
    )
    parser.add_argument(
        "--snapshot-at",
        default=datetime.now(timezone.utc).isoformat(),
        help="Source snapshot timestamp stored in provenance",
    )
    parser.add_argument(
        "--redact-person",
        action="append",
        default=[],
        help="Additional exact person name to redact; repeatable",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.audit_existing_output:
        known_people = _known_person_patterns(args.redact_person)
        result = audit_existing_output(args.audit_existing_output, known_people)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 2
    missing = [
        option
        for option, value in (
            ("--calls", args.calls),
            ("--transcripts", args.transcripts),
            ("--analyses", args.analyses),
            ("--output-dir", args.output_dir),
            ("--expected-company-id", args.expected_company_id),
        )
        if value is None
    ]
    if missing:
        parser.error("render mode requires: " + ", ".join(missing))
    result = render_corpus(
        calls_path=args.calls,
        transcripts_path=args.transcripts,
        analyses_path=args.analyses,
        output_dir=args.output_dir,
        expected_company_id=args.expected_company_id,
        snapshot_at=args.snapshot_at,
        extra_people=args.redact_person,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
