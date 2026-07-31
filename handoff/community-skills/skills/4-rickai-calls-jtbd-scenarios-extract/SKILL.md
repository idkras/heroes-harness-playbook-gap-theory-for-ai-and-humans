---
name: 4-rickai-calls-jtbd-scenarios-extract
description: "Use when you need to generate JTBD scenario .md files from Supabase calls parquet — with FULL transcripts, ≥10 hypotheses per scenario, and enriched per-call cards (ALL 31 analysis_fields, empty → ⚠️ нужно перезапустить алгоритм). Triggers: «создай jtbd сценарий по звонкам», «полный лог звонков по сценарию», «гипотезы по calls parquet», «enriched per-call карты», «обнови сценарий с полями из analysis_fields», «10+ гипотез по звонкам клиента», «отправка-счёта-клиенту.md», «досылка-документов.md», «универсальный orchestrator для calls»."
type: orchestrator-skill
version: 2.0
owner: Ilya Krasinsky & Rick.ai team
source: ./scripts/add_call_cards_to_jtbd_scenario.py (canonical enrichment, JTBD-named 2026-05-28); bronze/calls-supabase_calls/calls.parquet (от 4-rickai-calls-supabase-export)
---

**Mode:** [PASSIVE]

**Credentials:** Этот скил читает из локальных parquet-файлов (не обращается к Supabase напрямую). Если parquet нет — сначала `4-rickai-calls-supabase-export` → там Credentials SSOT: `supabase_rick_db_url` из `heroes_platform/credentials`. Скилл `0-keychain-audit` — аудит credentials.

# Calls JTBD сценарии из Supabase — оркестратор

## Назначение (JTBD)

**JTBD:** Когда нужно понять почему клиенты звонят по конкретной теме, я хочу получить .md-файл со ВСЕМИ транскриптами + enriched per-call картами (31 поле) + ≥10 проверяемых гипотез, чтобы РОП увидел паттерны и изменил скрипт продаж.

**«Hired for»:** полный разбор звонков по одному JTBD-сценарию с гипотезами которые охватывают >80% случаев.

**Клиент-универсальность:** все параметры параметризованы через `{client_alias}` — скил работает для luis-ru, avtoall-ru, typhoon-coffee и любого нового клиента без правки кода.

---

## When to Use

- «создай JTBD сценарий по звонкам клиента»
- «полный лог звонков по теме X для клиента Y»
- «обнови сценарий — добавь enriched поля из analysis_fields»
- «мне нужны 10+ гипотез почему клиенты звонят насчёт счёта»
- «досылка документов — все звонки + что они хотели»
- После `4-rickai-calls-supabase-export` когда bronze parquet готов

## When NOT to Use

- Bronze parquet ещё не создан → сначала `4-rickai-calls-supabase-export`
- Нужен только quantity count без транскриптов → прямой pandas groupby
- Нужен cross-scenario анализ (несколько JTBD) → `sales-call-deep-listener` + `sales-aha-aggregator`

---

## Input checklist

| Параметр | Обязательно | Пример | Откуда |
|---|---|---|---|
| `calls.parquet` | Да | `bronze/calls-supabase_calls/calls.parquet` | `4-rickai-calls-supabase-export` |
| `transcripts.parquet` | Нет | `bronze/calls-supabase_transcripts/transcripts.parquet` | тот же |
| `scenario_keywords` | Да | `["счёт", "счета", "invoice"]` | семантика JTBD |
| `scenario_name` | Да | `отправка-счёта-клиенту` | человекочитаемый kebab-case |
| `{client_alias}` | Да | `luis-ru` | Registry (любой клиент) |
| `intake_date_slug` | Да | `2026-05-26-invoice-issues-full-log` | папка intake/ |

---

## Канонические источники

Все скрипты находятся ВНУТРИ папки скилла (`./scripts/`) — скилл самодостаточен.

| Компонент | Путь | Назначение |
|---|---|---|
| Enrichment script | `./scripts/add_call_cards_to_jtbd_scenario.py` | Добавляет карточки анализа звонков в JTBD-сценарий |
| Safe corpus renderer | `./scripts/render_sanitized_call_corpus.py` | Строгий 1:1 corpus: safe Parquet + один Markdown/stub на звонок + reconciliation/privacy QA |
| Tests | `./scripts/test_add_call_cards_to_jtbd_scenario.py` | 47 unit tests (47/47 PASS) |
| Deprecated alias | `./scripts/enrich_scenario_md.py` | Backward-compat → re-exports из add_call_cards_to_jtbd_scenario |
| Bronze calls parquet | `[rick.ai]/clients/all-clients/{client_alias}/bronze/calls-supabase_calls/calls.parquet` | Источник данных |
| Bronze transcripts | `[rick.ai]/clients/all-clients/{client_alias}/bronze/calls-supabase_transcripts/transcripts.parquet` | Полные тексты |
| Export script (prerequisite) | `.agents/skills/4-rickai-calls-supabase-export/scripts/supabase_calls_export.py` | Generates input bronze |

---

## PIPELINE — 10 обязательных стадий оркестратора

> **ВАЖНО:** Оркестратор ОБЯЗАН пройти ВСЕ 10 стадий. Стадии 8–10 (QA + Design Review + Delivery) запускаются ВСЕГДА, без исключений. Hard fail — скипнуть любую стадию после Stage 7.

### Опциональный privacy-safe полный corpus перед scenario-анализом

Когда нужен проверяемый снимок **всех** звонков, а не только одного сценария,
сначала отрендерить локальный bronze в безопасный corpus. Скрипт отвергает
duplicate call IDs, foreign-company rows и orphan joins; сохраняет порядок всех
сегментов; для отсутствующего транскрипта создаёт явный stub. Raw IDs, телефоны,
hashes, audio URLs и operator names в output не переносятся.
`client_phone*`, `company_phone*` и их hashes запрещено использовать как
identity/repeat-customer evidence: direction-dependent стороны могут быть
зеркальными. Единственный grain reconciliation здесь — source call ID,
преобразованный в deterministic safe ref.

```bash
uv run .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/render_sanitized_call_corpus.py \
  --calls /local/bronze/calls.parquet \
  --transcripts /local/bronze/transcripts.parquet \
  --analyses /local/bronze/analyses.parquet \
  --expected-company-id "<company-uuid>" \
  --snapshot-at "YYYY-MM-DDTHH:MM:SSZ" \
  --output-dir /path/to/knowledge-base/call-corpus
```

Acceptance: `qa/reconciliation.json` имеет
`source_calls == source_unique_call_ids == parquet_rows == markdown_files`,
нулевые `missing_refs`, `extra_refs`, `duplicate_refs`,
`foreign_company_rows`; `qa/privacy-scan.json.passed == true`.
Privacy scan покрывает все finalized `.md/.json/.yaml/.yml` и каждую
string-like колонку всех Parquet. Повторный аудит существующего corpus:

```bash
uv run .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/render_sanitized_call_corpus.py \
  --audit-existing-output /path/to/finalized/call-corpus
```

Acceptance повторного аудита:
`qa/privacy-scan.json.adversarial_missed == 0`, inventory содержит все
text/Parquet артефакты, `finding_counts == {}`.

`qa/reconciliation.json.duration_qa` отдельно показывает, сколько numeric
last-segment timestamps превышают source call duration на `>5s` и `>30s`.
Это warning о различии source semantics: QA не удаляет, не обрезает, не
переставляет и не блокирует transcript text.

### Stage 1 — Prerequisites check

```python
import pandas as pd
from pathlib import Path

client_alias = "{client_alias}"
parquet_path = f"[rick.ai]/clients/all-clients/{client_alias}/bronze/calls-supabase_calls/calls.parquet"
df = pd.read_parquet(parquet_path)
print(f"calls: {len(df)} rows, cols: {list(df.columns)}")
# Ожидание: client_phone_hash в cols, analysis_fields непустой у >30% строк
```

Если parquet отсутствует → STOP и запустить `4-rickai-calls-supabase-export`.

### Stage 2 — Filter scenario calls

```python
import pandas as pd, json

flat_path = f"[rick.ai]/clients/all-clients/{client_alias}/bronze/calls-supabase_calls/calls_analysis_flat.parquet"
# Если calls_analysis_flat нет — создать через:
# python3 .agents/skills/4-rickai-calls-supabase-export/scripts/supabase_calls_export.py
#     --client-alias {client_alias} --company-id {uuid} --tables calls --flatten-analysis

df = pd.read_parquet(flat_path)
keywords = {keywords}  # e.g. ["счёт", "счета", "invoice"]

mask = (
    df["af_user_small_jtbd"].str.contains("|".join(keywords), case=False, na=False) |
    df["af_situation"].str.contains("|".join(keywords), case=False, na=False)
)
scenario_df = df[mask].copy()
print(f"Звонков: {len(scenario_df)}, phone_hash: {scenario_df['client_phone_hash'].nunique()}")
```

### Stage 3 — Formulate ≥10 hypotheses (10-type taxonomy)

Минимум 10 гипотез из 10 типов (Тип 1–10, см. ниже). На каждую — доля звонков и фальсификация.

### Stage 4 — Join with transcripts

```python
transcripts = pd.read_parquet(f"[rick.ai]/clients/all-clients/{client_alias}/bronze/calls-supabase_transcripts/transcripts.parquet")
merged = scenario_df.merge(transcripts, left_on="transcript_id", right_on="id", how="left", suffixes=("_call", "_tr"))
```

### Stage 5 — Write .md skeleton (hypotheses + transcript blocks)

Путь: `[rick.ai]/clients/all-clients/{client_alias}/intake/{date-slug}/bronze/полные-транскрипты-по-jtbd/{scenario_name}.md`

### Stage 6 — Inject enriched per-call cards via script

```bash
python3 .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/add_call_cards_to_jtbd_scenario.py \
    --client-alias {client_alias} \
    --scenario-md-path "[rick.ai]/clients/all-clients/{client_alias}/intake/{date-slug}/bronze/полные-транскрипты-по-jtbd/{scenario_name}.md"
# Ожидание: N enriched / 0 not_found
```

Правило: ALL 31 analysis_fields в каждой карте. Пустое/null → `— ⚠️ нужно перезапустить алгоритм`.
**Запрещено** фильтровать поля, даже если они 0% заполнены — owner должен видеть косяки алгоритма.

### Stage 7 — Self-verify

```bash
# Проверить что файл существует и открывается
ls -la "[rick.ai]/clients/all-clients/{client_alias}/intake/{date-slug}/bronze/полные-транскрипты-по-jtbd/{scenario_name}.md"
# Проверить что карты вставлены и поля пустые показаны как ⚠️
grep -c "нужно перезапустить" "{scenario_name}.md"  # > 0 ожидается для 0%-полей
grep -c "enriched-card" "{scenario_name}.md"         # = N звонков
```

### Stage 8 — QA review (ОБЯЗАТЕЛЬНО — запустить subagent)

**Оркестратор ОБЯЗАН spawn `@code-reviewer` и `@backend-reviewer` на скрипты:**

```
Spawn: @code-reviewer
Context: Review .agents/skills/4-rickai-calls-jtbd-scenarios-extract/scripts/add_call_cards_to_jtbd_scenario.py
- Check: all 31 fields present in _ANALYSIS_KEYS and _CARD_SECTIONS (no omissions)
- Check: _MISSING constant used for all empty/null values (no silent filtering)
- Check: idempotency logic (_is_already_enriched scans from call_id_pos to transcript_pos)
- Check: error handling for missing call_id in parquet (graceful warning, not crash)
- Check: backup created before in-place modification
Return: verdict pass/block with specific findings
```

```
Spawn: @ui-qa-engineer (или general-purpose)
Context: Verify enriched .md file quality
- Spot-check 5 random calls: card BEFORE transcript, all sections present
- Verify ⚠️ markers appear for 0%-fill fields (desire, crm_deal_id, transaction_id)
- Verify transcript text intact after card injection
Return: verdict ship-ready/needs-work
```

**Hard fail:** оркестратор завершил Stage 7 и сразу к Delivery без Stage 8 → `category: orchestrator-skipped-qa`.

### Stage 9 — Design review (ОБЯЗАТЕЛЬНО — запустить subagent)

**Оркестратор ОБЯЗАН spawn `@design-art-director`:**

```
Spawn: @design-art-director
Context: Review per-call enrichment card design in 4-rickai-calls-jtbd-scenarios-extract/SKILL.md
Goal: РОП открывает .md и за 30 секунд понимает паттерн по сценарию
Questions:
- Порядок секций в карте оптимален для РОПа? (сначала что важно)
- ⚠️ маркер читаем или создаёт шум?
- 31 поле — перегруз или нужно всё?
- Что должно быть в первых 3 строках каждой карты для maximum signal?
Return: verdict + specific redesign recommendations
```

**Hard fail:** оркестратор завершил Stage 8 без Design Review → `category: orchestrator-skipped-design-review`.

### Stage 10 — Delivery

После approve от Stage 8 QA и Stage 9 Design Review:

1. Ссылка в чате: `[{scenario_name}.md]([rick.ai]/clients/all-clients/{client_alias}/intake/{date-slug}/bronze/полные-транскрипты-по-jtbd/{scenario_name}.md)`
2. Обновить статус в «Действующие сценарии» таблице в этом SKILL.md
3. Коммит: `git add [rick.ai]/... && git commit -m "feat(calls): enriched per-call cards for {scenario_name} ({client_alias})"`

---

## Канонический формат .md-файла

```markdown
# JTBD Сценарий: {Название}

**Scenario ID:** {H_NN} | **Звонков:** {N} | **phone_hash:** {M}
**Источник:** Supabase call_analytics, company_id={uuid} | **Дата:** {YYYY-MM-DD}

---

## §1 Гипотезы (≥10)

| # | Гипотеза | Доля | Сигналы | Фальсификация |
|---|---|---|---|---|
| H01 | ... | ~X% | ... | ... |
... (≥10 строк из 10 типов)

---

## §2 Транскрипты и per-call карты

### Звонки по phone_hash `{hash}` (N={count})

#### Звонок {N}/{total} — `{datetime}` · {operator} · {direction} · {duration}s · call_id `{uuid}`

<!-- enriched-card call_id:{uuid} -->

**Карта звонка (analysis_fields + классификация):**

**Классификация звонка**

| Поле | Значение |
|---|---|
| Корень причины | process_gap |
| Тип разговора | question |
| JTBD L1 | C1.1 |

**ABCDX сегмент**

| Поле | Значение |
|---|---|
| Сегмент ABCD | B |
| Квалификация | — ⚠️ нужно перезапустить алгоритм |
| Цель сегмента | Получить счёт |

**JTBD (оператор)**

| Поле | Значение |
|---|---|
| Big JTBD (пользователь) | Решение вопросов документооборота |
| Medium JTBD (пользователь) | Получение корректного счёта |
| Small JTBD (пользователь) | C1.1 Отправка счёта клиенту |

**JTBD (AI)**

| Поле | Значение |
|---|---|
| Big JTBD (AI) | — ⚠️ нужно перезапустить алгоритм |
| Medium JTBD (AI) | — ⚠️ нужно перезапустить алгоритм |
| Small JTBD (AI) | — ⚠️ нужно перезапустить алгоритм |

**Анализ звонка**

| Поле | Значение |
|---|---|
| Желание (`desire`) | — ⚠️ нужно перезапустить алгоритм |
| Блокер | Нет поля ИГК в форме |
| Триггер | Нужен счёт с ИГК для 275-ФЗ |
| Ситуация | Клиент оформляет заказ по 275-ФЗ |
| Клиент | ООО Ромашка |
| Получит на этом этапе | Счёт после уточнения данных |
| 5 Почему | 1) Нет UI для ИГК → 2) Функция не разработана → ... |
| Триггер+Ситуация | Оформляет заказ, нет ИГК |
| Блокер продажи | — ⚠️ нужно перезапустить алгоритм |

**Паттерны**

| Поле | Значение |
|---|---|
| Стоп-слова | — ⚠️ нужно перезапустить алгоритм |
| Рекомендованные фразы | ... |
| Навыки продаж (Big) | — ⚠️ нужно перезапустить алгоритм |
...

**CRM / Rick Exchange**

| Поле | Значение |
|---|---|
| CRM сделка ID | — ⚠️ нужно перезапустить алгоритм |
| CRM сделка статус | — ⚠️ нужно перезапустить алгоритм |
| Транзакция (Rick Exchange) | — ⚠️ нужно перезапустить алгоритм |
| Контакт (Rick Exchange) | — ⚠️ нужно перезапустить алгоритм |
| Выручка транзакции | — ⚠️ нужно перезапустить алгоритм |
| Товары (JSON) | — ⚠️ нужно перезапустить алгоритм |

<!-- /enriched-card -->

**Транскрипт (дословно, без сокращений):**
```
agent: Луис Плюс, добрый день.
client: Добрый день, мне нужен счёт с ИГК...
```
```

---

## Типология гипотез (Тип 1–10) — минимум по 1 из каждого типа

| Тип | Источник данных | Пример |
|---|---|---|
| 1 — Частотные | `af_user_small_jtbd` value_counts | «клиент не получил счёт на почту» (~35%) |
| 2 — Процессные | `af_stop_words_patterns`, `af_recommended_phrases` | «менеджер не называет срок отправки» |
| 3 — Системные | `af_root_cause_5why` patterns | «1С не отправляет автоматически» |
| 4 — JTBD смещения | `af_when_trigger` + `af_desire` divergence | «звонят по счёту, а хотят статус доставки» |
| 5 — Временные | `call_date` distribution | «80% звонков в конце месяца» |
| 6 — Сегментные | `af_segment_abcd` × topic | «сегмент C чаще звонит повторно» |
| 7 — Блокерные | `af_blocker`, `af_sale_blocker` | «нет ЭДО — клиент не может принять счёт» |
| 8 — Edge-cases | аномальная длительность, null segment | «7 звонков без segment_abcd — новый сегмент?» |
| 9 — Контрфактические | `af_recommended_phrases` | «если менеджер скажет X — клиент не перезвонит» |
| 10 — Метрические пробелы | `desire`, `transaction_id` null rate | «desire пустой у 100% — AI не понял цель; transaction_id 0% — нет связки со сделкой» |

---

## Output checklist

- [ ] `{scenario_name}.md` создан по канонической структуре
- [ ] §1 содержит ≥10 гипотез из ≥8 типов типологии, с долями % и фальсификациями
- [ ] §2 содержит enriched per-call карту для КАЖДОГО звонка (31 поле, пустые → `⚠️`)
- [ ] Полные транскрипты — без сокращений и пропусков
- [ ] Stage 8 QA: `@code-reviewer` + `@ui-qa-engineer` — оба вернули approve
- [ ] Stage 9 Design: `@design-art-director` — вернул verdict
- [ ] Ссылка в чате: `[{имя}.md](relative/path/имя.md)` (кириллица as-is)

---

## Outcome checklist (owner benefit)

- [ ] РОП видит паттерны: топ-3 гипотезы охватывают >60% звонков
- [ ] Каждая гипотеза имеет actionable фальсификацию (что проверить в следующем разборе)
- [ ] Owner видит какие поля надо перезапустить алгоритм (⚠️ маркеры)
- [ ] Owner value: время на анализ 100 звонков сокращается с 4h (ручной просмотр) до <30 мин
- [ ] Готов к использованию в `sales-call-deep-listener` для следующего batch

---

## Hard fail (Запрещено)

- Менее 5 гипотез на сценарий → `category: jtbd-scenario-insufficient-hypotheses`
- Пустое поле per-call карты без явного `— ⚠️ нужно перезапустить алгоритм` → `category: enriched-field-silently-omitted`
- Сокращение транскрипта (ellipsis, «...», «[сокращено]») → `category: transcript-truncated-in-scenario`
- Генерация значений для `analysis_fields` которые отсутствуют в parquet → `category: analysis-fields-fabricated`
- Ссылка в чате через `file:///` или URL-encoding кириллицы → `category: local-file-link-wrong-format` (RCA 2026-05-27)
- Запись в `bronze/` директорию клиента без `0-rick-client-kb-save-gate` → `category: client-kb-save-gate-skipped`
- Скипнуть Stage 8 (QA) → `category: orchestrator-skipped-qa`
- Скипнуть Stage 9 (Design Review) → `category: orchestrator-skipped-design-review`
- Создавать скрипты скилла в `heroes_platform/scripts/` вместо `./scripts/` → `category: skill-not-self-contained` (RCA 2026-05-28)
- Хардкодить `{client_alias}` (`luis-ru`, `avtoall-ru`) в скриптах скилла → `category: generalization-first-violated` (AGENTS.md §Generalization-first gate)

---

## Reasoning Log Protocol

Таблица решений в чат + строка в `ai.incidents.md` §Append-only trace. Канон: `agent-reasoning-log`.
Специфично: при пустом `af_desire` / `af_what_client` — писать `— ⚠️ нужно перезапустить алгоритм` и добавить в Тип 10 гипотезу, не придумывать значение.

---

## Self-falsification gate

После генерации прогнать гипотезу «сценарий содержит все нужные данные» через `2-hypothesis-gap-falsification`:
- Ожидание: ≥10 гипотез → Факт: count(§1 rows) → Δ?
- Ожидание: per-call карта 31 поле для каждого звонка → Факт: grep count "enriched-card" == N звонков → Δ?
- Ожидание: пустые поля как ⚠️ → Факт: grep "нужно перезапустить" > 0 → Δ?
- Ожидание: транскрипты полные → Факт: нет «...» / ellipsis в тексте → Δ?

---

## Действующие сценарии (luis-ru)

| Файл (1 клик) | JTBD | Звонков | phone_hash | Статус |
|---|---|---|---|---|
| [отправка-счёта-клиенту.md]([rick.ai]/clients/all-clients/luis-ru/intake/2026-05-26-invoice-issues-full-log/bronze/полные-транскрипты-по-jtbd/отправка-счёта-клиенту.md) | С1.1 Отправка счёта | 89 | 43 | ⚠️ нет enriched карт (P2) |
| [досылка-недостающих-документов.md]([rick.ai]/clients/all-clients/luis-ru/intake/2026-05-26-invoice-issues-full-log/bronze/полные-транскрипты-по-jtbd/досылка-недостающих-документов.md) | С6.2 Досылка документов | 269 | 36 | ⚠️ нет enriched карт (P2) |
| [проверка-упд-и-счёта-до-отправки.md]([rick.ai]/clients/all-clients/luis-ru/intake/2026-05-26-invoice-issues-full-log/bronze/полные-транскрипты-по-jtbd/проверка-упд-и-счёта-до-отправки.md) | С6.1 Проверка УПД/счёта | 50 | 33 | ⚠️ нет enriched карт (P2) |

---

## Связанные скилы (Related skills)

- [`4-rickai-calls-supabase-export`](.agents/skills/4-rickai-calls-supabase-export/SKILL.md) — prerequisite: bronze parquet
- [`0-rick-client-kb-save-gate`](.agents/skills/0-rick-client-kb-save-gate/SKILL.md) — paths в clients/
- `sales-call-deep-listener` — следующий шаг: глубокий per-call анализ (enriched cards)
- `sales-aha-aggregator` — cross-call агрегация паттернов
- `2-hypothesis-gap-falsification` — self-falsification gate
- `Standard 4.6 v1.1` — folder naming

---

## Авторство

Создан по канону Standard 4.8 §B. v2.0 (2026-05-28): universal {client_alias} param; all 31 fields in per-call card (empty → ⚠️); canonical script in ./scripts/; orchestrator 10-stage pipeline with mandatory Stage 8 QA + Stage 9 Design Review. RCA 2026-05-27: owner «минимум 10+ гипотез; в документах нет полезных полей из supabase analysis_fields».
