---
name: 4-conversation-action-chain-extract
description: "Use when need to extract verifyable action chain (5-15 turns) от decision-line / aha-moment / pricing pivot / objection-resolution backtrack to find what sales said immediately ДО client insight. Output — table с file:line refs для verification (sed-able). Замыкается на skill `4-call-aha-moment-detector` (находит decision turn) → этот skill backtracks. Универсальный — работает на любом normalized conversation. Триггеры: «извлеки цепочку действий», «backtrack от ключевой реплики», «action chain до инсайта», «5 почему сделка случилась», «verify-able sales chain»."
---

**Credentials:** metadata SSOT — `heroes_harness/credentials_registry.yaml`; runtime API — `heroes_platform.credentials`; workflow — `0-credentials-manager` и metadata-only `0-keychain-audit`.

**Mode:** [PASSIVE]

# Action Chain Extract — backtrack от decision-line к корневому действию sales

## Когда использовать

- После `4-call-aha-moment-detector` нашёл decision turn
- Для построения Monday note секции «Что получилось хорошо»
- Для обучения других sales — показать canonical pattern
- В составе `sales-call-deep-listener` Skill 5

## Когда НЕ использовать

- Single-turn analysis — нет chain
- Conversation < 10 turns — не хватает context
- Anchor turn unclear — сначала запусти `4-call-aha-moment-detector`

## Generalization-first gate (4×yes)

| # | Вопрос | Ответ |
|---|---|---|
| 1 | Универсально для всех клиентов / sales людей? | ✅ — алгоритм работает с unified turn-list |
| 2 | Anchor turn из input? | ✅ — `anchor_turn_index` параметр |
| 3 | Multilingual? | ✅ — оперирует turn-индексами и speaker_role |
| 4 | Новый клиент = новый run, без правки кода? | ✅ |

## Источники канон

- Roman card §поля 7-11 (Ильяховская картина мира)
- AGENTS.md §0 Macro «outcome ДО output»
- Standard 2.5 §JTBD scenarium

## Credentials

Не требует — детерминированный backtracking algorithm.

## Inputs

```yaml
normalized_turns: list[Turn]              # output Skill 1
anchor_turn_index: int                    # decision/aha turn
anchor_type: decision | aha | pricing_pivot | objection_resolution | check_in_response
backtrack_window: int                     # default 15
forward_window: int                       # default 3
include_micro_aha: bool                   # default true
```

## Outputs

```yaml
anchor:
  turn_index: int
  speaker: client
  text: string
  source_line_ref: string                 # "L222"

chain: list[Step]                         # см. главную таблицу ниже

verification:
  sed_command: string                     # «sed -n '199,222p' file.txt»
  total_steps: int
  duration_in_chain_min: float | null
  micro_aha_count: int
  client_initiated_count: int
  decision_velocity: string               # "11 minutes from intro to decision"
```

## Главная таблица — пример Gian decision chain (1-table-default)

Verified output для Gian #01, anchor=L222 (`«Yeah, it's a very cool machine. Perfect. Yeah, I think I decide.»`):

| step | turn_index | speaker_role | speaker_name | text | source_line_ref | action_classification | why_this_action_works |
|---|---:|---|---|---|---|---|---|
| 1 | 199 | sales | Daria | «Here, with us, you're de-pulling at the same time, the whole batch.» | L199 | contrast_statement | Контраст с drum-roaster (Giesen клиента) — клиент видит разницу до того как защищается |
| 2 | 201 | sales | Daria | «...you're not ending up having, like, some beans wasted, some beans being overrasted.» | L201 | proactive_objection_close | Закрывает скрытое возражение «качество» ДО того как клиент его озвучил |
| 3 | 207 | sales | Daria | «So you see what I was explaining, the whole batch is out, because with a drum racer, some parts will still be racing.» | L207 | physical_demo | Visual proof — клиент верит глазам, не словам sales |
| 4 | 208 | client | Gian | «Wow.» | L208 | micro_aha | Клиент сам подтверждает движение к decision — buying signal |
| 5 | 210 | sales | Daria | «It's only… the full batch is out, and we've been racing only for 5 minutes, 17 seconds.» | L210 | factual_anchor | Конкретное число подтверждает claim о speed |
| 6 | 211 | sales | Daria | «And it's beautiful aroma, you know, there is no smoke.» | L211 | sensory_anchor | Активирует sensory imagination — anchor сильнее argumentation |
| 7 | 213 | client | Gian | «Fantastic.» | L213 | micro_aha | Sensory confirmation — клиент почти решил |
| 8 | 216 | sales | Daria | «In about 1 minute 30 seconds, we could start racing the next batch, so you end up having batch after batch non-stop.» | L216 | productivity_claim | Productivity vs Giesen — value frame |
| 9 | 221 | sales | Daria | «So, how did you like, the racing?» | L221 | check_in_question | Заставляет вербализовать positive reaction вслух → коммитится |
| 10 | 222 | client | Gian | «Yeah, it's a very cool machine. Perfect. Yeah, I think I decide.» | L222 | decision | Финальная decision на языке клиента |

**Verification command:** `sed -n '199,222p' "[rick.ai]/clients/all-clients/typhoon-coffee/calls-daria-transcripts/01_Gian.txt"`
**Decision velocity:** 11 минут от intro (turn ~50, ~9:00) до decision (turn 222, 20:02).
**Micro-aha count:** 2 («Wow» L208, «Fantastic» L213).

## Action classification taxonomy (deterministic rules — НЕ LLM)

| Class | Trigger pattern | Why it works |
|---|---|---|
| `contrast_statement` | sales turn содержит «vs», «here vs there», «with us / with them», «при этом» | Клиент видит разницу до защиты |
| `physical_demo` | sales содержит «show / let me» + «you see», «look» | Visual proof |
| `sensory_anchor` | sales содержит «aroma», «smell», «smoke», «taste», «feel» | Activates sensory imagination |
| `check_in_question` | sales заканчивается «?» И содержит «how / what do you think» | Forces verbalization |
| `micro_aha` | client turn ≤3 words И positive interjection (Wow, Fantastic, Cool, Понял, Точно, Ясно) | Buying signal |
| `pricing_reveal` | sales содержит currency mention (через `pricing_decoder` regex) | Price без защиты |
| `reframe` | sales содержит «that's what I was saying about», «as you correctly mentioned», «exactly» | Использует слова клиента как trigger |
| `mirror_words` | sales повторяет ≥3 слов из preceding client turn | «Ты меня слышишь» |
| `reference_drop` | sales упоминает named existing customer | Trust signal на capex |
| `confirmation_request` | sales содержит «can we / shall we / agreed?» | Explicit close |
| `proactive_objection_close` | sales pre-emptively addresses common concern | Закрывает возражение до его озвучивания |
| `factual_anchor` | sales содержит number/measurement | Конкретика > абстракции |
| `productivity_claim` | sales формулирует output/time claim | Value frame |
| `decision` | client turn содержит «decide», «take it», «sign me up» | Финальная decision |

## Algorithm (5 шагов)

1. **Validate input** — `anchor_turn_index` ∈ [0, len-1]; clamp windows к границам
2. **Slice window** — `window = turns[max(0, anchor-back):min(len, anchor+forward+1)]`
3. **Classify each turn** — apply rules таблицы выше per turn (deterministic)
4. **Compute «why this action works»** — template per classification (deterministic)
5. **Build verification artifacts** — `sed_command`, `decision_velocity` из timestamps, aggregate stats

## Definition of Done

- [ ] Output validates через jsonschema
- [ ] `sed_command` runnable
- [ ] Каждый step имеет classification из enum (no «other»)
- [ ] `why_this_action_works` non-empty per step
- [ ] Spot-check на 3 anchor types (decision / pricing_pivot / objection_resolution)

## Common failures

| Failure | Симптом | Fix |
|---|---|---|
| Anchor turn в самом начале | backtrack_window > anchor | clamp + warning |
| All turns classified «other» | rule set не покрывает pattern | extend rule table, не silent skip |
| micro_aha false positive | client сказал «Wow» иронически | classification остаётся, downstream LLM (Layer 2) валидирует |
| timestamps absent (chat/email) | `decision_velocity = null` | OK, async conversations не имеют velocity |

## Связанные артефакты

- Upstream: `4-conversation-normalize` (Skill 1)
- Sibling: `4-call-aha-moment-detector` (находит anchor) ↔ этот skill (backtracks)
- Downstream: `4-conversation-monday-note-render` (Skill 7)
- Pipeline: `4-call-deep-listener-orchestrate` Skill 5
- Python: `heroes_platform/sales_injury/action_chain_extract.py`
- Tests: `tests/sales_injury/test_action_chain_extract.py`

## Authorship

Создан 2026-05-14 в рамках pr-rick-7r1 после owner challenge «дай больше контекста, не одну фразу — цепочку из N действий Дарьи до инсайта». Verifyable через sed-able line refs — anti-hallucination by design.
