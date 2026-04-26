# 📘 Heroes Crew AI Management Onboarding Standard

<!-- 🔒 PROTECTED SECTION: BEGIN -->
type: standard
standard_id: 7.2
logical_id: standard:heroes_crew_ai_management_onboarding
updated: 17 April 2026, 12:00 CET by AI Assistant (draft for human review)
previous version: N/A
based on: [Task Master Standard](abstract://standard:task_master_standard), [Registry Standard](abstract://standard:registry_standard), [Symphony Linear Beads Orchestration Standard 4.15](abstract://standard:symphony_linear_beads_orchestration), [Speed of Trust Standard 7.1](abstract://standard:speed_of_trust_economics), [Pulse.ai Knowledge Base Standard 2.8](abstract://standard:pulseai_knowledge_base), [Cursor Folder Structure Standard 4.6](abstract://standard:pulseai_cursor_folder_structure), [Hypothesis Gap Falsification Standard](abstract://standard:hypothesis_gap_falsification)
integrated: AGENTS.md (root), .agents/skills/, .agents/agents/, .beads/, [standards .md]/, [pulse.ai]/clients/all-clients/
version: 1.0 (draft)
status: Draft — pending human review by Ilya Krasinsky
tags: standard, onboarding, team-management, ai-agents, beads, subagents, github, knowledge-base, crew-management
<!-- 🔒 PROTECTED SECTION: END -->

---

## 🛡️ Лицензия и условия использования

**Все права защищены.** Документ — интеллектуальная собственность Ильи Красинского. Magic Rick Inc. (Делавэр, США) защищает авторские права согласно законодательству США.

---

## 🎯 Цель документа

Закрыть онбординг-разрыв для новых членов команды Heroes/Pulse.ai (Милена, Крис, Аня и следующие): дать одну точку входа, которая объясняет — **как устроена работа в воркспейсе, где SSOT для каждого слоя, как пользоваться `.beads`-тикетами, скилами, субагентами, GitHub и базой знаний клиентов**, чтобы человек за 1 день дошёл до первого самостоятельного тикета без разрушения соседних потоков.

**Job to be done:** «Когда новый человек присоединяется к команде Heroes/Pulse.ai, он хочет понять контур работы и начать делать тикеты, не сломав соседям git и не перепутав скилы со стандартами, чтобы за первую неделю выйти на стабильный поток задач без постоянного дёрганья Ильи».

---

## 📐 Scope

Применяется к:
- новым членам команды (advising, analytics, dev, design, QA);
- людям, которые работают **через AI-агента** (Cursor, Claude Code, Codex CLI, Cowork);
- ситуациям, когда действующий участник переходит в **новый домен** (например, аналитик начинает работать с клиентом и `.beads`).

Не применяется к:
- клиентским командам (для них — Стандарт 5.22 AppCraft и `4-pulseai-onboarding-orchestrator`);
- разовому консультированию без доступа к репо.

---

## 1. Три слоя работы — карта мира

| Слой | Что это | Где SSOT | Чем НЕ является |
|---|---|---|---|
| **Стандарты** | Каноничные правила «как мы делаем». Версионируются. | `[standards .md]/` | Не процедуры — это правила. Не редактируются на лету. |
| **Скилы** | Исполняемые процедуры агента. Триггер → шаги → артефакт. 129 шт. | `.agents/skills/{N-name}/SKILL.md` | Не правила — это инструкции для агента. Изменяются часто. |
| **Субагенты** | Отдельные процессы со своим контекстом, моделью и tool-set. 18 шт. | `.agents/agents/{name}.md` | Не скилы — это **отдельный agent**, спавнится через `Agent` tool. |
| **База знаний клиента (KB)** | JTBD, виджеты, переписки, сценарии. | `[pulse.ai]/clients/all-clients/{client}/` | Не свалка артефактов — структура по 2.8. |
| **`.beads`** | Project graph: тикеты, статусы, блокеры, зависимости. | `.beads/issues.jsonl` | Не todo-лист — это **граф зависимостей**, не плоский список. |
| **`todo.md`** | Reflection-слой над `.beads` для людей. | корень + `{project}.todo.md` | НЕ source of truth. Если расходится с `.beads` — `.beads` прав. |

**Жёсткое правило:** скилы ссылаются на стандарты, KB ссылается на скилы и стандарты, `.beads` ссылается на всё. Никогда наоборот.

---

## 2. История субагентов (.agents/agents/) — кого когда зовём

Субагент = **отдельный процесс с изолированным контекстом и ограниченным tool-set**. Зовётся через `Agent(subagent_type=...)`. Используется когда:
- нужна **изоляция** (READ-ONLY ревью, adversarial критика);
- нужен **специализированный MCP** (Jira API, Telegram MCP);
- нужно **параллельное исполнение** независимых задач (3-7 ревьюеров одновременно).

### Полный реестр субагентов

| Субагент | Категория | Когда зовём | Tools |
|---|---|---|---|
| **manager-lead-orchestrator** | оркестрация | главный менеджер pipeline 12 стадий; вызывает остальных, не делает сам | Read, Edit, Write, Bash + Agent(всех остальных) |
| **rca-investigator** | расследование | RCA, 5 whys, разбор инцидентов | Read, Grep, Glob (READ-ONLY) |
| **inception-reviewer** | gate | проверка готовности проекта к dev по job chain (Стандарт 1.15); считает glue effort | Read, Grep, Glob (READ-ONLY) |
| **review-gate-checker** | gate | A1/A2/B/C готовность к human review; обновляет `.beads` статус | Read, Grep, Glob, Bash |
| **code-reviewer** | review | общее ревью кода (корректность, безопасность, perf, тесты) | Read, Grep, Glob, Bash (READ-ONLY) |
| **frontend-reviewer** | review | React/TS/CSS глубже, чем code-reviewer | Read, Grep, Glob, Bash |
| **backend-reviewer** | review | Python/Node/SQL/HTTP/SSE, MCP, query plans, retry/timeout | Read, Grep, Glob, Bash |
| **security-reviewer** | review | XSS, CSRF, prompt injection, auth bypass, secrets, supply chain | Read, Grep, Glob, Bash |
| **perf-reviewer** | review | bundle size, FPS, memory leaks, network waterfall | Read, Grep, Glob, Bash |
| **a11y-reviewer** | review | WCAG AA/AAA, keyboard, screen reader, focus trap | Read, Grep, Glob, Bash |
| **design-art-director** | adversarial | stress-test дизайна, ищет failure modes, защитные реакции команды | Read, Grep, Glob (READ-ONLY) |
| **ui-qa-engineer** | QA | JTBD-дерево, угловые случаи, тест-кейсы, визуальная регрессия | Read, Grep, Glob, Bash |
| **cleanup-guardian** | hygiene | сканер 17 категорий долга, debt score, hardcoded paths | Read, Grep, Glob, Bash |
| **data-analyst** | данные | проверка gold mart перед записью в Sheets; выгрузка через pulseai MCP | Read, Grep, Glob, Bash + pulseai MCP |
| **sheets-qa-verifier** | QA | после записи в Google Sheets — checklist по Стандарту 5.30 | Read, Grep, Glob, Bash |
| **cohort-delivery-manager** | оркестрация | цепочка когортного отчёта: data-analyst → writer → sheets-qa-verifier | Read, Edit, Write, Bash + Agent(data-analyst, sheets-qa-verifier) |
| **jira-beads-manager** | sync | управление тикетами beads (RW) + импорт из Jira | Read, Grep, Glob, Bash, Edit, Write |
| **telegram-delivery-sender** | доставка | форматирование + проверка читаемости (CPR) до отправки в Telegram | Telegram MCP + PulseAI MCP |

### Эволюция (история)

1. **2026-Q1** — был один `orchestrator.md`, делал и менеджмент, и исполнение → перегружался контекст, путались стадии. Файл сейчас лежит как `orchestrator.md.deprecated`.
2. **2026-03** — введён канонический pipeline 12 стадий (Стандарт 4.15). Создан `manager-lead-orchestrator` — **только менеджер, не исполнитель**.
3. **2026-04** — добавлены adversarial-роли (`design-art-director`, `inception-reviewer`) после инцидентов, где review squad из одних «согласных» ревьюеров пропускал баги.
4. **2026-04** — `cohort-delivery-manager` и `sheets-qa-verifier` появились после серии инцидентов с записью в Google Sheets без верификации (rows 69-81 vs 56-67, conv rates в неправильных колонках).
5. **2026-04** — `cleanup-guardian` расширен с 12 до 17 категорий после workspace audit (debt=39).

### Правила вызова

- **Никогда** не вызывать субагента «на всякий случай». Каждый вызов = строка в `agent-reasoning-log` (см. одноимённый скилл).
- **Параллельный squad на стадии in_review** (стадия 6 pipeline): минимум 3, оптимум 5-7 субагентов одним сообщением, multiple `Agent` tool calls.
- **Hypothesis falsification:** при 2+ субагентах — обязательный cross-check verdicts (`subagent-falsification` скилл).
- **READ-ONLY субагенты НЕ редактируют файлы.** Если ревьюер просит изменения — это commentary, исполнение делает родительский агент.

---

## 3. Скилы для работы с GitHub

GitHub — это **share state**, ошибка тут стоит дороже всего. Для каждой git-операции есть свой скилл.

### Карта git-скилов

| Скилл | Когда применять | Что делает |
|---|---|---|
| **`5-git-parallel-coordination`** | **ПЕРЕД** `checkout`, `pull`, `merge`, `rebase`, `commit`, `push`, `Stage all` в параллельной работе | Читает `.codex-memory/topics/git-parallel-coordination.md` + `.codex-memory/runtime/git-sync-intents.md`; добавляет intent-row до операции; чистит после sync |
| **`0-main-cleanliness-guard`** | Локальный `main` грязный, diverged, перегружен parked branches/worktrees; перед `Stage all` или publish from main | Создаёт изолированный clean worktree; не даёт запушить мусор в `main` |
| **`5-sync-github-checklist`** | Перед `git push` к GitHub | Проверяет Windows-совместимость имён файлов, мержит ветки по чек-листу |
| **`0-claude-code-mcp-sync`** | Изменилась MCP-конфигурация → нужно синкнуть Claude Code | Автоматическая синхронизация `.cursor/mcp.json` ↔ Claude Code config |
| **`2-release-final-check`** | Перед deployment / релизом | Чек-лист: tech debt, test gaps, missing docs, file organization |
| **`1-close-task-or-project-cleanly`** | Закрытие тикета/проекта | Обновляет `todo.md` статус + добавляет ссылки на artefact'ы (PR url) |

### Правила работы с git (из AGENTS.md)

1. **Один активный child bead = одна активная branch/worktree.**
2. Owner child bead'а владеет только branch-local scope. Интеграция в `main` — у parent epic owner.
3. **Запрещено:** `--no-verify`, `--no-gpg-sign`, force push в `main`, `git reset --hard` без явной просьбы owner.
4. **Перед `git add -A` или `git add .`** — проверь, что не добавляешь `.env`, credentials, large binaries. Лучше явно по именам.
5. **Pre-commit hook упал → `--amend` ЗАПРЕЩЁН.** Создавай новый commit.
6. **Runtime intent после успешного sync:** удалить строку в `.codex-memory/runtime/git-sync-intents.md`. Recurring drift → `[todo · incidents]/ai.legacy.md`. RCA-worthy breakage → `ai.incidents.md`.

### Создание PR через `gh`

```bash
gh pr create --title "короткий title <70 chars" --body "$(cat <<'EOF'
## Summary
- bullet 1
- bullet 2

## Test plan
- [ ] manual test 1

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Никаких bare `PR #123` — всегда полный markdown-link с URL.

### Deploy & PR review contract (обязательная секция в delivery)

В каждом существенном ответе с git-изменением — секция `Deploy & PR review`:
- branch name + pushed/not;
- PR URL или явно «PR не открыт»;
- CI/CD status (проверенный с PR-страницы, **не** угаданный из локальных тестов);
- ready ли для owner review;
- нужно ли обновить Linear / отправить в Slack для Ильи и Жени.

---

## 4. `.beads`-тикеты — как работать

`.beads` — **primary editable layer** для project state. `todo.md` — отражение.

### Базовый workflow

1. **Перед созданием тикета** — обязательный `Quick ticket card` в чате (Стандарт 4.15 §5.3): JTBD, контекст, output checklist, outcome, DoD, тесты, corner cases, blockers, next-action digest. **Без card → создание тикета запрещено.**
2. **Skill `1-change-task-and-project-state-via-beads`** — при любом планировании, создании, триаже, смене статуса.
3. **Skill `1-project-beads-migration-review`** — если открываешь legacy `{project}.todo.md` без соответствующего bead.
4. **Skill `1-beads-id-namespaces`** — для нового ID (`pr-hero-*`, `pr-rick-*`, `pr-adv-*`).
5. **Skill `1-beads-ticket-full-display`** — показать тикет в чат как Quick ticket card (не только header).

### Pipeline 12 стадий (Стандарт 4.15)

```
backlog → next → dod_blocked → in_design → in_progress → in_review
       → rework ↺ in_review (≤2 круга)
       → hypothesis_validation → hypothesis_confirmed/failed
       → owner_received → owner_activated → outcome_realized
```

**Не пропускать `hypothesis_validation`** — измерять на метриках, не «на глаз».

### Label `blocked`

`blocked` — это **label, а не статус**. Может быть на любой стадии. Если блокер фундаментальный (нужно уточнить DoD) → откат в `dod_blocked`. Если ждём external dependency → оставить с label.

### §0 макрос для ID (обязательно везде)

Голые `P0`, `G01`, `pr-rick-1234` без подписи — **запрещены**. Формат: `pr-rick-42 — {title из bead}`. Hard fail при нарушении.

---

## 5. Стандарты — структура и навигация

`[standards .md]/` разделён по доменам:

| Префикс | Домен | Примеры |
|---|---|---|
| `0.` | core | Task Master 0.0, Registry 0.1 |
| `1.` | process · goalmap · task · incidents · tickets · qa | 1.13 widgets, 1.15 job chain |
| `2.` | books · skills, projects · context | 2.7 KB JTBD, 2.8 Pulse.ai KB |
| `3.` | scenarium · jtbd · hipothises · offering · tone | |
| `4.` | dev · design · qa | 4.6 folder structure, 4.10 agentation, 4.13 GSAP, 4.15 beads orchestration |
| `5.` | pulse.ai · integrations · product heroes | 5.19 Sleepwell regions, 5.20 user_id, 5.22 AppCraft, 5.30 cohort, 5.37 raw events |
| `6.` | advising · review · supervising | |
| `7.` | team management · culture | 7.1 trust, **7.2 — этот документ** |
| `9.` | heroes · posts · offers · marketing | |
| `10.` | AI personality | |
| `11.` | contracts | |

**Имя файла = заголовок:** `{N.M} {название} {DD month YYYY HHMM CET} by {автор}.md`. Изменение имени без обновления заголовка внутри — запрещено (валидируется `validate_filename_header_sync`).

Любые изменения стандартов — через скилл `0-standards-create-update-review` с обязательным human review **перед** регистрацией.

---

## 6. Скилы — структура каталога

`.agents/skills/{N-name}/SKILL.md`. Префикс N — приоритет/категория:

- **0-** guard'ы и инфра
- **1-** оркестрация задач, тикеты, проекты
- **2-** RCA, гипотезы, QA, протокол challenge
- **3-** доставка артефактов клиенту
- **4-** Pulse.ai-специфика (виджеты, KJ, KB, snippet)
- **5-** sync, git
- **6-** health, MCP мониторинг
- **7-** большие воркфлоу (когда клиент пишет, оффер, cybos, advising)
- **8-** внешние системы (Telegram, Google Sheets, AmoCRM, n8n)
- **9-** дизайн и UI (Stitch, Figma, GSAP, Excalidraw)

**SSOT — `.agents/skills/`.** `.claude/skills/` и `.codex/skills/` — root-симлинки на ту же папку. Редактируешь только в `.agents/skills/`.

Изменение скилла → обязательно `0-align-skill-name-and-trigger-to-jtbd` (метаданные + контракт + root-симлинки).

---

## 7. База знаний клиента (KB) — каноническая структура

`[pulse.ai]/clients/all-clients/{client-alias}/`:

```
{client-alias}/
├── {client-alias}.rick.context.md       # ОБЯЗАТЕЛЬНО — главный контекст
├── {client-alias}.todo.md               # отражение .beads
├── README.md / RICK_AI_STRUCTURE_GUIDE.md
├── analytics_counters.yaml              # карта счётчиков
├── business_units_settings_*.json       # снапшоты BU
├── {client}_{system}_{counter_id}/      # папка на каждый источник
├── knowledge-base/                      # ★ JTBD-сценарии
│   └── {when-asked-...} or {N.M название}/
├── scenario-folder/exports/             # gold/silver parquet
├── bronze/                              # сырые выгрузки
├── rules-registry/                      # KJ rules, attribution
├── chats/ telegram_exports/             # переписки
├── checklists/ notebooks/ sync/
```

**Эталон:** `fashionhub-ru/`. **Анти-эталон:** `sleepwell-ru/` (много рабочих artefact'ов в корне — технический долг).

Любая новая папка в KB — называется по JTBD-сценарию (`when-asked-...` или `N.M название`), **не** по тикету и **не** по дате (Стандарт 2.7).

---

## 8. Mandatory delivery format (из AGENTS.md)

Каждый существенный ответ агента содержит 11 секций:

1. `Было/Стало`
2. `JTBD-сценарий`
3. `Input checklist`
4. `Output checklist`
5. `Outcome checklist`
6. `Design review`
7. `QA review`
8. `Deploy & PR review`
9. `Hypothesis falsification (delivery self-check)` — gap table `Ожидание | Факт | Δ`, verdict
10. `Owner effort digest` — таблица `next action | усилие человека (0-100) | что агент может сделать сам`
11. `Run Evidence`

**Hard fails:**
- голый ID без подписи (`P0`, `G01`, `pr-rick-42` без ` — {smysl}`);
- отдельная «легенда» вместо самодостаточных заголовков (+100 на переделку);
- `ready for review` без проверки реальной PR/checks страницы;
- DOM-only evidence для UI-claim (нужен screenshot + независимый субагент — RCA 2026-04-16).

---

## 9. Чеклист онбординга (Day 1 → Day 7)

### Day 1 (2-3 часа)
- [ ] Прочитать `AGENTS.md` (root) — это symlink на CLAUDE.md и CODEX.md.
- [ ] Прочитать этот стандарт (7.2) до конца.
- [ ] Прогнать скилл `0-workspace-team-activation` (один проход: dependencies, MCP config, beads import, Dolt federation).
- [ ] Прогнать `0-teammate-mcp-setup` — сгенерировать `mcp.json` + health check.
- [ ] Прогнать `0-keychain-audit` — проверить что нужные ключи в Mac Keychain.
- [ ] Открыть `.beads/issues.jsonl` и `todo.md`, посмотреть текущее состояние.

### Day 2 — практика на чужом тикете
- [ ] Взять один `status:next` bead (низкий приоритет, наблюдательный).
- [ ] Применить `1-beads-ticket-full-display` — увидеть полную ticket card.
- [ ] Пройти по pipeline стадиям, проследить переходы.
- [ ] Прочитать соответствующий standard для этой задачи.

### Day 3 — первый свой тикет
- [ ] Создать `Quick ticket card` в чате по Стандарту 4.15 §5.3.
- [ ] Через `1-change-task-and-project-state-via-beads` создать bead.
- [ ] Если задача клиентская — проверить структуру KB по разделу 7 этого документа.
- [ ] До `git push` — `5-git-parallel-coordination` + `5-sync-github-checklist`.

### Day 4-5 — review-практика
- [ ] Запустить параллельный review squad на свой тикет (3-7 субагентов).
- [ ] Применить `subagent-falsification` для cross-check verdicts.
- [ ] Зафиксировать BLOCKING/CRITICAL до перехода `in_review → hypothesis_validation`.

### Day 6-7 — доставка и outcome
- [ ] Через `3-orchestrator-delivery-bundle` собрать client-facing artefact.
- [ ] Через `3-review-artifact-for-client-readiness` — pre-flight check.
- [ ] Если в чат клиенту — `3-client-chat-delivery` (draft → review → send).
- [ ] Дойти до `outcome_realized` с proof: метрика-до / метрика-после.

---

## 10. Quality gates (что считается «онбординг закрыт»)

Человек считается онбординг-завершённым когда:

1. ✅ Самостоятельно создал и закрыл минимум 3 bead с прохождением всех 12 стадий pipeline.
2. ✅ Хотя бы один из закрытых тикетов прошёл через параллельный review squad из 5+ субагентов.
3. ✅ Хотя бы один client-facing artefact доставлен через `3-client-chat-delivery` без правок Ильи на стадии review.
4. ✅ Не было incident'ов в `ai.incidents.md` за неделю по причине нарушения git protocol или KB structure.
5. ✅ trust_score ≥ 70 (по Стандарту 7.1 Speed of Trust).

---

## 11. Anti-patterns (что точно нельзя)

- ❌ Создавать документ без прогона `0-document-creation-guard`.
- ❌ Редактировать `todo.md` напрямую вместо `.beads`.
- ❌ Запускать субагента «на всякий случай» без записи в `agent-reasoning-log`.
- ❌ Делать `git push` в `main` без `5-git-parallel-coordination` в параллельной работе.
- ❌ Помечать тикет `ready for review` без открытой PR-страницы и проверенных CI checks.
- ❌ Доставлять UI-claim только с DOM-queries без screenshot + независимого субагента.
- ❌ Создавать KB-папку с именем `tikket-1234` или `2026-04-17-export` вместо JTBD-сценария.
- ❌ Использовать англицизмы (`стейкхолдер`, `митинг`, `дедлайн`, `фидбек`) — есть русские эквиваленты.
- ❌ Делать summary-only delivery, когда есть git/RCA/release/incident-факты — нужен detail-first.
- ❌ Класть рабочие artefact'ы в корень клиентской папки (как sleepwell-ru) — должны быть в `knowledge-base/{сценарий}/`.

---

## 12. Recovery — что делать если сломал

| Ситуация | Что делать |
|---|---|
| Пушнул мусор в `main` | `0-main-cleanliness-guard` + RCA в `ai.incidents.md` через `2-rca-incidents` |
| Сломал `.beads` (расхождение с `todo.md`) | `1-project-beads-migration-review` — `.beads` всегда прав |
| Тикет застрял в `dod_blocked` | Вызвать `inception-reviewer` субагента |
| Review squad дал противоречивые verdict'ы | `subagent-falsification` + cross-check |
| Гипотеза не подтвердилась на стадии 8 | Вернуть в `next` с обновлённой гипотезой через `2-hypothesis-eval-loop` |
| MCP не работает | `6-mcp-check-transport-closed` + `6-mcp-logs-read-analyze` |
| Не понимаю что делать дальше | `1-next` — построит критическую цепочку Голдрата (3-5 шагов) |

---

## 13. Связь с другими стандартами

- **4.15 Symphony Linear Beads Orchestration** — каноничные правила pipeline и Quick ticket card.
- **2.8 Pulse.ai Knowledge Base Standard** — структура KB.
- **4.6 Cursor Folder Structure Standard** — структура клиентских папок.
- **7.1 Speed of Trust Economics** — экономика доверия и измерение trust_score.
- **0.0 Task Master** — базовая модель задач.
- **0.1 Registry Standard** — регистрация документов.
- **2.6 Book Conversion** — как извлекать знания.
- **Outcome Zero-Gap JTBD Transfer** — handoff между членами команды.
- **Gap Theory Standard** — поиск разрывов.

---

## 14. Open questions для human review

1. Нужно ли добавлять trust_score в Day 7 quality gate, или это слишком рано для нового человека?
2. Какие именно тикеты считать «низкий приоритет, наблюдательный» для Day 2 — нужен ли реестр стартовых тикетов?
3. Добавлять ли отдельный sub-skill `7-team-onboarding-tracker` для метрик онбординга (cycle time, time-to-first-bead, time-to-outcome)?
4. Кто owner стандарта после регистрации — Илья или role «team lead»?

---

## Status

**Draft v1.0 — pending human review by Ilya Krasinsky.** После approve:
1. Зарегистрировать в Registry (Стандарт 0.1).
2. Добавить в `[standards .md]/7. team management · culture/README.md` если есть.
3. Создать соответствующий скилл-обвязку `0-heroes-crew-onboarding-tracker` (опционально).
4. Сослаться из AGENTS.md в разделе «Mandatory delivery».
