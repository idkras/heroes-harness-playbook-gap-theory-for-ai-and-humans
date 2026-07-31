---
name: 4-conversation-normalize
description: "Use when need to normalize conversation transcript from ANY source (Zoom WebVTT / WhatsApp text / Telegram JSON / email mbox / Intercom API / plain chat dump) into universal turn-list schema for downstream call-review skills (jtbd-extract / sales-scorecard / action-chain / roman-card / monday-note-render). Adapter pattern — добавление нового источника = новый parser в этом skill, остальные 7 skills pipeline не меняются. Универсальный для Typhoon Racers (Daria English Zoom) / Avtoall (RU calls + WhatsApp) / любого клиента sales-injury. Триггеры: «нормализуй транскрипт», «привести WhatsApp к unified format», «универсальный адаптер для conversations», «conversation normalize»."
---

**Credentials:** metadata SSOT — `heroes_harness/credentials_registry.yaml`; runtime API — `heroes_platform.credentials`; workflow — `0-credentials-manager` и metadata-only `0-keychain-audit`.

**Mode:** [PASSIVE]

# Conversation Normalize — universal adapter ANY source → unified turn-list

## Когда использовать

- Перед запуском любого call-review skill из pipeline (Skills 2-8 в `4-call-deep-listener-orchestrate`)
- При добавлении нового источника conversations (новый CRM, новый messenger)
- Для batch миграции исторических transcripts в unified format

## Когда НЕ использовать

- Conversation уже в unified format — skip
- Анализ raw воды (sentiment / topic) — нужен отдельный skill, normalize только структурирует turn-list

## Generalization-first gate (4×yes)

| # | Вопрос | Ответ |
|---|---|---|
| 1 | Универсально для всех клиентов / всех источников? | ✅ — adapter pattern, новый источник = новый parser, остальные skills не трогаются |
| 2 | Source identifier из input (`source: zoom \| whatsapp \| telegram \| email \| chat \| call`)? | ✅ — explicit field, no autodetect heuristics |
| 3 | Multilingual (RU + EN + mixed)? | ✅ — language pass-through, normalize не транслирует |
| 4 | Новый источник = новый parser в этом skill, не правка downstream? | ✅ — Skills 2-8 работают с unified turn-list |

## Источники канон

- AGENTS.md §0 Macro «Outcome ДО output»
- Standard 4.6 v1.3 §Universal client check
- Roman card §Speaker Swap Protocol (Skill 2 downstream)

## Credentials

Не требует — pure transformation.

## Inputs

```yaml
source: zoom | whatsapp | telegram | email | chat | call    # explicit, no autodetect
source_format: webvtt | plain_text | markdown | json | mbox  # как parse
raw_text: string                                              # full conversation content
participants_hint:                                            # optional
  - role: sales | client
    name: string
    identifier: string
language_hint: ru | en | mixed | auto                         # default auto
```

## Outputs (unified turn-list — single contract для Skills 2-8)

```yaml
conversation_id: string
source: string
language_detected: ru | en | mixed
total_turns: int
total_duration_min: float | null
participants:
  - role: sales | client
    name: string
    identifier: string
turns:
  - turn_index: int                     # 0-based, monotonic
    speaker_role: sales | client | unknown
    speaker_name: string
    text: string
    timestamp_iso: string | null
    timestamp_offset_sec: float | null
    source_line_ref: string             # "L120" / "msg-id-abc" — для verifyable cite
metadata:
  parser_version: string
  parsed_at: iso
  warnings: list[string]
```

## Adapter table — 5 source-format pairs (1-table-default)

| # | source × source_format | Parser file | Input pattern | Output mapping | Known issues / fallback |
|---|---|---|---|---|---|
| 1 | `zoom × webvtt` | `parsers/zoom_webvtt.py` | `WEBVTT\n\n{n}\n{HH:MM:SS} --> {HH:MM:SS}\n{Speaker}: {text}` | `turn_index = n − 1`, `speaker_name = Speaker`, `timestamp_offset_sec = parse(start_HH:MM:SS)`, `source_line_ref = "L{file_line_of_speaker_tag}"` | Speaker tag missing → `speaker_role = unknown`, warning logged |
| 2 | `whatsapp × plain_text` | `parsers/whatsapp_plain.py` | `[DD.MM.YY, HH:MM:SS] {Name}: {text}` (или `DD/MM/YY HH:MM - {Name}: {text}`) | `turn_index = sequential`, `speaker_name = Name`, `timestamp_iso = parse(date+time)`, `source_line_ref = "msg-{n}"` | Multi-line message → join до next `[DD.MM` marker. Media → text = `[media: {filename}]` |
| 3 | `telegram × json` | `parsers/telegram_json.py` | Telegram export schema `messages[]` array (`from`, `text`, `date`, `id`) | `turn_index = idx in array`, `speaker_name = from`, `timestamp_iso = date`, `source_line_ref = "msg-id-{id}"` | Service messages (`type=service`) → skip + warning. Forwarded → text = `[forwarded from {from}]: {text}` |
| 4 | `email × mbox` | `parsers/email_mbox.py` | Mbox `From {sender} {date}\n{headers}\n\n{body}` | `turn_index = msg index`, `speaker_name = parse(From header)`, `timestamp_iso = Date header`, `source_line_ref = "Message-ID: {id}"` | Quoted reply (`> {text}`) → strip из body, добавить в `metadata.quoted_history`. Multipart → use text/plain |
| 5 | `chat × markdown` | `parsers/markdown_chat.py` | `**{Name}** ({timestamp}): {text}` или `### {Name}\n{text}` | `turn_index = sequential`, `speaker_name = Name`, parsed timestamp если есть | Heading style varies — fall back на bold-name pattern если heading не match |

**Adapter pattern invariant:** добавление 6-го источника (Intercom Live Chat API JSON) = новый файл `parsers/intercom_api.py` + строка в этой таблице. Skills 2-8 downstream не меняются.

## Speaker role disambiguation

Если в input `participants_hint` указан `name + role` — direct mapping (case-insensitive, fuzzy ≤3 edit distance).

Если нет — heuristic:
- Self-introduction («I'm {Name}, {Role} at {Company}» + Company match `client_business_context`) → sales
- Pricing initiator (первый произнёс цифру с currency) → client (это buying-signal, sales обычно name price reactively)
- Question initiator (≥3 questions в первые 10 turns) → sales
- Long answer (longest avg turn length) → client

Если ambiguity > 30% turns → `speaker_role = unknown`, **HARD FAIL** для Skills downstream без `4-conversation-speaker-swap-check` пройденного.

## Algorithm (5 шагов)

1. **Validate input** — `source` ∈ enum, `raw_text` non-empty, length ≤ 1MB
2. **Dispatch to parser** — `parser_fn = REGISTRY[(source, source_format)]; turns_raw = parser_fn(raw_text)`
3. **Speaker disambiguation** — direct map by hint OR apply heuristic table
4. **Language detection** — sample first 500 chars → langdetect → mixed if no single lang >70%
5. **Validate output schema** — jsonschema strict, monotonic turn_index, source_line_ref non-empty per turn

## Definition of Done

- [ ] All 5 source × format pairs имеют parser в `heroes_platform/sales_injury/parsers/`
- [ ] Каждый parser имеет unit tests на 3 fixtures (RU + EN + edge case)
- [ ] Output validates через jsonschema strict
- [ ] Speaker disambiguation accuracy ≥ 70% на test corpus
- [ ] Универсальный — добавление 6-го источника = только новый parser file

## Common failures

| Failure | Симптом | Fix |
|---|---|---|
| WebVTT speaker tag missing | Whisper output без `Speaker:` префикса | Fallback role=unknown + warning, downstream Skill 2 обязателен |
| WhatsApp multi-line с emoji | Emoji ломает regex | Use `re.UNICODE` flag, test на emoji corpus |
| Email quoted history | `> > >` blocks intermixed | Strip pre-parse, restore в metadata |
| Mixed RU/EN в одной фразе | langdetect возвращает RU для «нет, just kidding» | Mixed = ok, downstream обрабатывает |

## Связанные артефакты

- Pipeline: `4-call-deep-listener-orchestrate` Skill 1
- Subagent: `sales-call-deep-listener` (вызывает этот skill первым)
- Python: `heroes_platform/sales_injury/conversation_normalize.py` + `parsers/` directory
- Tests: `tests/sales_injury/test_conversation_normalize.py`
- Standard refs: 5.37 §5.37.5 (Stage 5.0 — pre-classify normalization)

## Authorship

Создан 2026-05-14 в рамках pr-rick-7r1 для закрытия owner challenge: «pipeline должен работать с любым источником — звонки, WhatsApp, email — устойчиво». Universal adapter pattern.
