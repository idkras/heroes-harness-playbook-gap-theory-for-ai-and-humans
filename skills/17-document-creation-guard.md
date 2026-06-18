---

name: document-creation-guard
description: "Use when you are about to create a new document file and must verify whether creation fits the NO NEW DOCUMENTS protocol. Checks file type, purpose, and allowed exceptions. Based on core-auto.mdc. Use when user says \"create document\", \"новый .md файл\", \"write documentation\", \"документ для проекта\"."
---

# Document Creation Guard Skill

## Overview
This skill prevents creation of unnecessary documents by enforcing the "NO NEW DOCUMENTS PROTOCOL" from `core-auto.mdc`. It checks if a document should be created or if content should be written to chat and added to `{projectname}.todo.md` instead.

## Inputs
- **File Path**: The intended path for the document (e.g., `docs/FIGMA_TOKEN_SETUP.md`)
- **File Type**: The type of document (.md, .txt, etc.)
- **Purpose**: What is the document for? (setup, instructions, report, analysis, etc.)
- **Project Name**: (Optional) The project name to find `{projectname}.todo.md`

## Instructions

1. **Check File Type**:
   - If file is code (.py, .ts, .js, .sql, .sh, .bat) → ✅ ALLOWED
   - If file is config (.json, .yaml, .toml, .env, .ini) → ✅ ALLOWED
   - If file is test (test_*.py, *.test.ts, *.spec.js) → ✅ ALLOWED
   - If file is migration (sql_migrations/*.sql, alembic/versions/*.py) → ✅ ALLOWED
   - If user explicitly requested document creation → ✅ ALLOWED (quote request)
   - If updating existing document → ✅ ALLOWED
   - Otherwise → Check prohibited patterns

1.5. **Check Client Folder Path** (RCA 2026-04-17 — <internal-component> folder enforcement):

   **Триггер:** путь содержит `[<internal-component>]/clients/all-clients/{alias}/` или `<internal-folder>/heroes-<internal-component>/<internal-component>-<internal-component>/public/data/clients/{alias}/`.

   Читай canonical tree из **Standard 4.6 v1.1** (`<standard-ref>) и проверь target path:

   **Canonical slots в `[<internal-component>]/clients/all-clients/{alias}/`:**
   - `{alias}.rick.context.md` (ровно один — canonical context)
   - `{alias}.todo.md` (project todo по Standard 0.1)
   - `business_units_settings_latest.json` + опционально `business_units_settings_{timestamp}.json` в `sync/`, НЕ в корне
   - `knowledge-base/{task_id}-{requester}-{type}-{topic}/` — KB файлы по JTBD
   - `projects/{bead_id}-{jtbd_short}/` — артефакты проектов
   - `{app_name}_{app_id}/<layer>/` и `/<layer>/` и `/<layer>/` — data layers
   - `scenario-folder/` — legacy scenario cache (ingest-only)
   - `sync/` — legacy export mirror (не писать напрямую)

   **PROHIBITED патерны в client root (depth=1):**
   - ❌ `{domain}.context.md` (без `.rick` префикса) — ДУБЛЬ canonical, **always reject**
   - ❌ `*_user_stories_*.md`, `*_analysis_*.md`, `*_review_*.md` в корне — должны идти в `knowledge-base/{task_id}-...` или `projects/`
   - ❌ `clickhouse/`, `analysis/`, `research/`, `data/` новые top-level folders (не из canonical template)
   - ❌ Timestamped копии `business_units_settings_YYYYMMDD_HHMMSS.json` в корне — только `_latest.json` в корне, остальные в `sync/`

   **Для `<internal-folder>/.../public/data/clients/{alias}/`:**
   - ✅ ALLOWED: `funnel.json`, `funnel.v5.json`, `events_flat.parquet`, `funnel_stage_mapping.json`, `index.json` (manifest)
   - ❌ PROHIBITED: дубли bronze данных (например `event_params_keys.json` если уже есть в `[<internal-component>]/.../<layer>/`) — лучше symlink/ref
   - ❌ PROHIBITED: client-specific schemas (`funnel.graphql.v5.json` если другие клиенты используют `funnel.v5.json`) — унифицируй имя

   **Response format при нарушении:**
   ```
   🚨 CLIENT FOLDER PATH VIOLATION (Standard 4.6 v1.1)
   Target: [path]
   Canonical slot: [path per Standard 4.6]
   Fix:
     1. Move to canonical slot: [move command]
     2. Or use Standard 4.6 slot: [alternative]
   Reject Write until fixed.
   ```

   **§1.5.1 Context filename rule (RCA 2026-04-17 — duplicate .context.md):**
   - Canonical: `{alias}.rick.context.md` (из Standard 2.3 строка 41 **после унификации P1.1**)
   - PROHIBITED: `{domain}.context.md` без `.rick` (6 known rogues на 17 Apr 2026: designcraft, <client>, evaai, <client>, elyts, greatrvtrip)
   - Если target path = `*.context.md` без `.rick` — reject, предложи правильное имя

2. **Check Prohibited Patterns**:
   - Pattern: `*{SETUP,INSTRUCTIONS,GUIDE,REPORT,ANALYSIS,SUMMARY,DIAGNOSIS,TROUBLESHOOTING,DEBUG,RECOMMENDATIONS,SUGGESTIONS,RESEARCH,FINDINGS,EVALUATION,REVIEW}*.md` → ❌ PROHIBITED
   - Pattern: `*-{analysis,report,summary,diagnosis,gap-analysis}.md` → ❌ PROHIBITED
   - Any .md in project root (except existing ones) → ❌ PROHIBITED
   - Any document that could be written in chat or added to `{projectname}.todo.md` → ❌ PROHIBITED

3. **Find Project TODO**:
   - Search for `{projectname}.todo.md` in parent directories
   - If found, suggest adding content there instead
   - If not found, suggest writing in chat

4. **Generate Response**:
   - If PROHIBITED: Write to chat: "🔍 PRE-CREATION CHECK: Planning to create [filename]"
   - State file type and purpose
   - Write: "❌ PROHIBITED: This document type is not allowed"
   - Write alternative: "✅ ALTERNATIVE: Will write in chat and add to {projectname}.todo.md → '## {Section}' section"
   - Suggest specific section name based on purpose (Setup, Analysis, Troubleshooting, etc.)
   - DO NOT create the file

5. **If ALLOWED**:
   - Write to chat: "✅ ALLOWED: Creating [filename] (reason: [exception type])"
   - Proceed with creation

6. **JTBD, Jobs To Be Done Scenario Naming (<internal-component> KB / client folders)** — при создании документов в:
   - `[<internal-component>] knowledge base offers-jtbd-scenario-checklists/` или подпапках
   - `[<internal-component>]/clients/all-clients/{client}/` или подпапках
   - **ЗАПРЕЩЕНО:** `README.md` в папке сценария
   - **ОБЯЗАТЕЛЬНО:** имя файла = имя папки сценария (например: `when asked of ecommerce product category funnel conversion.md`)
   - См. [<internal-component> Knowledge Base Standard 2.8](<standard-ref>), [<internal-component> Jobs To Be Done Scenarium 2.4](<standard-ref>)

## Output Format

```
🔍 PRE-CREATION CHECK: Planning to create [filename]

File Type: [.md/.txt/etc]
Purpose: [setup/instructions/report/analysis/etc]

❌ PROHIBITED: This document type violates NO NEW DOCUMENTS PROTOCOL

✅ ALTERNATIVE:
- Write brief summary in chat
- Add full content to: [path to {projectname}.todo.md]
- Section: "## [Section Name]"

Suggested section names:
- Setup → "## Setup"
- Instructions → "## Setup Instructions" or "## Troubleshooting"
- Report/Analysis → "## Analysis" or "## Test Results {release N}"
- Troubleshooting → "## Troubleshooting"
- Recommendations → "## Recommendations" or "## Next Steps"
```

## Examples

**Example 1: Setup Guide**
```
Input: File Path: "docs/FIGMA_TOKEN_SETUP.md", Purpose: "setup instructions"
Output:
🔍 PRE-CREATION CHECK: Planning to create docs/FIGMA_TOKEN_SETUP.md
❌ PROHIBITED: Pattern matches *SETUP*.md
✅ ALTERNATIVE: Write in chat, add to rick-crm-conversations-calls-to-jtbd-dynamic-offers.todo.md → "## Setup" section
```

**Example 2: Analysis Document**
```
Input: File Path: "RCA_ANALYSIS.md", Purpose: "root cause analysis"
Output:
🔍 PRE-CREATION CHECK: Planning to create RCA_ANALYSIS.md
❌ PROHIBITED: Pattern matches *ANALYSIS*.md
✅ ALTERNATIVE: Write in chat, add to {projectname}.todo.md → "## Analysis" section
```

**Example 3: Allowed Code File**
```
Input: File Path: "scripts/setup_figma.py", Purpose: "setup script"
Output:
✅ ALLOWED: Creating scripts/setup_figma.py (reason: code file)
```

## Related Rules
- `.cursor/rules/core-auto.mdc` - NO NEW DOCUMENTS PROTOCOL
- `.cursor/rules/no-new-documents-strict.mdc` - Strict enforcement rule


---

## Язык результата

Весь человекочитаемый результат — на русском. Английский допустим только для точных имён API, методов, идентификаторов кода и меток вендорских интерфейсов. Англицизмы запрещены — использовать русские эквиваленты (см. `AGENTS.md § Workspace memory and git coordination`). Устоявшиеся сокращения (JTBD, DOD, RCA, SSOT, MCP) допустимы с расшифровкой при первом упоминании.

## Reasoning Log Protocol (ОБЯЗАТЕЛЬНО)

При каждом исполнении этого скилла агент ОБЯЗАН:

1. **Вести reasoning log в чате** — таблица решений с evidence, gaps и blocking instructions:

```markdown
### Reasoning Log — [дата UTC]
| # | Decision | Evidence source | Gap found | Blocking instruction | Owner value |
|---|----------|-----------------|-----------|---------------------|-------------|
```

**§0 macro (hard fail):** колонка **Gap found** — не голый `G01`, а **`G01 — краткое имя гепа`**. Любой ID (`P0`, `G01`, `E01`, `pr-rick-*`) без ` — {человекочитаемое имя}` = hard fail. См. `AGENTS.md` секция «Plain language» и `CLAUDE.md` §0.

2. Записать строку в `ai.incidents.md` таблица.

3. При задачах > 3 ходов — сохранить лог в `<internal-folder>/reasoning-logs/`.

Hard fail: без reasoning log скилл считается неисполненным.

## Связанные скилы

- **agent-reasoning-log** — см. `AGENTS.md` (список навыков) — обязательный протокол reasoning log
- **owner-prompt-capture** — см. `AGENTS.md` (список навыков) — автозапись промтов owner


---

## Авторство

Скил создан Ильёй Красинским на основе стандартов Praxis (включая TaskMaster и связанные стандарты Praxisai Workspace). Развивается и поддерживается как часть единой системы навыков `.agents/skills/`.
