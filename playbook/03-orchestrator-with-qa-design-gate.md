# Orchestrator With Mandatory QA + Design Gate

> Универсальный playbook оркестратора многошаговых задач — для команд и AI-агентов. Делает обязательным **прогон через QA-агентов и дизайнеров** на ревью результата ДО доставки владельцу.
>
> **Source RCA:** инцидент 2026-04-16 «UI-claim без screenshot», 2026-04-17 «client-specific код вместо универсального», 2026-04-23 «orchestrator пропустил QA-стадию».
>
> **Применимо к:** любой команде где задача проходит несколько ролей (planner → developer → reviewer → delivery).

---

## §0. Принципы проектирования

1. **Универсальность кода** — реализация работает для всех клиентов через manifest/config, а не через `if (client == "X")` ветки. Перед любым `Write`-действием в код проходит **4×yes Generalization Gate** (см. §3).
2. **Falsification обязательна** — после доставки запускается фальсификация собственной гипотезы «я всё исправил» через [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md).
3. **QA + design review каждый раз** — не «когда есть время», а как gate перед `delivery → owner`.
4. **Stages enumerated** — оркестратор обязан явно проговорить «я сейчас на стадии X из 12», не имеет права срезать стадии.
5. **Без legacy** — не делаем backward-compat shims, feature flags, _vars-аппендиксов. Если что-то старое мешает — переделываем под root cause, не пристраиваем сбоку.

---

## §1. 12 стадий оркестрации (mandatory enumeration)

Каждая задача проходит ВСЕ 12 стадий. Орестратор отмечает текущую и не имеет права перепрыгивать вперёд.

| # | Стадия | Что делается | Кем | Output |
|---|---|---|---|---|
| 1 | **Intake** | Принимаем запрос, фиксируем что владелец хочет, что уже пробовал | Orchestrator | Одна фраза JTBD + Quick ticket card |
| 2 | **Outcome design** | Применяем `5 so-what`-ladder до настоящего outcome владельца | `outcome-designer` | Outcome card с критической цепочкой |
| 3 | **Hypothesis design** | Формулируем 0-ю гипотезу + альтернативу + критерий фальсификации | `hypothesis-designer` | Hypothesis card |
| 4 | **Expected output table** | Контракт «что появится в результате» — колонки = поля, строки = примеры данных | Orchestrator | Markdown table до implementation |
| 5 | **4×yes Generalization Gate** | Решение работает для всех клиентов через config, не через if-ветки | Orchestrator + `code-reviewer` | yes/yes/yes/yes или redesign |
| 6 | **Implementation** | Пишем код / документ / артефакт. Incremental commits каждый слой | Developer | Файлы + тесты |
| 7 | **Self-falsification** | Запускаем `01-hypothesis-gap-falsification` на свою же работу | Orchestrator | Gap table с verdict |
| 8 | **QA review** (mandatory gate) | `ui-qa-engineer` + `code-reviewer` независимо смотрят на результат | 2+ субагента параллельно | QA verdict + список багов |
| 9 | **Design review** (mandatory gate) | `design-art-director` adversarial stress-test: что может сломаться | `design-art-director` | Design verdict + риски |
| 10 | **RCA-injection если найден gap** | Если QA/Design нашли проблему — root-cause-first, не workaround | `rca-investigator` | RCA card с +50/+100 шкалой |
| 11 | **Delivery** | Финальный ответ владельцу с 12 mandatory секциями (Было/Стало, JTBD, Hypothesis falsification и т.д.) | Orchestrator | Markdown с полной структурой |
| 12 | **Outcome verify** | Через N дней проверяем — outcome из стадии 2 материализовался? | Orchestrator + метрики | Подтверждение или новый bead |

**Hard fail:** если оркестратор перепрыгнул стадию 5, 7, 8, 9, или 12 — это RCA-инцидент. Стадии 7-9 НЕ опциональны.

---

## §2. Контракт между ролями

```
                  ┌──────────────────────────────────────────────┐
                  │          ORCHESTRATOR (manager-lead)          │
                  │  — управляет 12 стадиями, не делает работу    │
                  │  — спавнит субагентов, собирает их verdict-ы  │
                  └────────┬───────────────────────────┬─────────┘
                           │                           │
              ┌────────────▼──────┐         ┌──────────▼─────────┐
              │  hypothesis-      │         │  outcome-designer  │
              │  designer         │         │  (5 so-what)       │
              │  (фальс. форма)   │         └────────────────────┘
              └────────┬──────────┘
                       │
              ┌────────▼─────────────────────────────────────────┐
              │              DEVELOPER (any role)                │
              │  — пишет код / документ / артефакт               │
              │  — incremental commits                           │
              │  — НЕ начинает без Expected output table         │
              └────────────────────────┬─────────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
       ┌────────▼─────────┐                       ┌───────────▼────────┐
       │  ui-qa-engineer  │                       │  code-reviewer     │
       │  (визуальный QA  │                       │  (логика, корнеры) │
       │  + screenshot)   │                       │                    │
       └────────┬─────────┘                       └───────────┬────────┘
                │                                             │
                └─────────────────┬───────────────────────────┘
                                  │
                       ┌──────────▼────────────┐
                       │  design-art-director  │
                       │  (adversarial stress) │
                       └──────────┬────────────┘
                                  │
                       ┌──────────▼────────────┐
                       │   rca-investigator    │
                       │  (если есть gap)      │
                       └──────────┬────────────┘
                                  │
                                  ▼
                              DELIVERY
```

---

## §3. 4×yes Generalization Gate (стадия 5)

Перед любым `Write` в код / документ / шаблон оркестратор обязан получить 4 ответа `yes`:

| # | Вопрос | Что значит «no» |
|---|---|---|
| 1 | Решение работает для всех клиентов из manifest без правки кода компонента, только через `config.json` / `manifest.dataSource`? | hardcoded `if alias == "<client>"` или клиент-специфичный файл |
| 2 | Client identity приходит из `manifest` / `config`, а не из props/state/литералов? | `props.clientName === "<client>"` |
| 3 | Пути к данным разрешаются из `manifest.dataSource`, а не из строковых литералов? | `fetch("/data/<client>/funnel.json")` без manifest |
| 4 | Новый клиент добавляется правкой ТОЛЬКО `manifest.json` + кладкой data-файлов, без новых `.tsx` / без правки registry? | нужно создать `<client>FunnelSection.tsx` и зарегистрировать |

Если хоть один = no — **redesign до implementation**. Не писать `Write` пока не получено `yes/yes/yes/yes`.

**RCA-источник:** инцидент 2026-04-17 — агент создал `BigfinFunnelSection.tsx` + `bigfin-funnel-*` hardcoded keys + `if (alias === 'bigfin')` ветку. Owner: «мы делаем универсальный код для всех клиентов, верно?». Правильный паттерн — все клиенты через один `<FunnelSection manifest={...} />`.

---

## §4. QA review gate (стадия 8) — обязательный

После implementation оркестратор **ВСЕГДА** запускает минимум **2 субагента параллельно**:

### 4.1 `ui-qa-engineer` (если есть UI)

Проверяет:
- Дерево JTBD (big / medium / small) для затронутой страницы / экрана
- Угловые случаи (5W+H × роль × устройство × состояние данных)
- Манульные тест-кейсы (минимум 10 строк `# / Action / Expected / Pass-Fail`)
- Visual regression (screenshot baseline + diff)
- `evidence type: screenshot + subagent` обязательно для UI-claim — **DOM-queries only = hard fail**

### 4.2 `code-reviewer` (всегда, даже для документов)

Проверяет:
- Корректность логики
- Безопасность (XSS / SQL injection / secret leakage / path traversal)
- Performance (re-renders, query plans, bundle size)
- Maintainability (читабельность, naming, абстракции)
- Тесты есть и адекватные — не моки на критичных контрактах

### 4.3 Параллельный запуск

Оба субагента стартуют **одновременно** (один Agent tool call с двумя tool uses). Оркестратор НЕ имеет права запустить только одного.

### 4.4 Verdict format

Каждый субагент возвращает:

```
verdict: pass | needs-work | blocking
issues:
  - severity: critical | high | medium | low
    description: ...
    file: path:line
    fix-direction: ...
```

Если хоть один issue с `severity: critical` или `verdict: blocking` — оркестратор НЕ доставляет владельцу, а возвращает на стадию 6 (re-implementation) или 10 (RCA).

---

## §5. Design review gate (стадия 9) — обязательный

После QA gate (даже если QA прошёл) оркестратор запускает `design-art-director`:

### 5.1 Что делает design-art-director

**Adversarial stress-test** — ищет failure modes:

- Скрытая сложность (что не видно с первого взгляда?)
- Снижение доверия (где владелец/пользователь усомнится?)
- Ложная уверенность (где результат выглядит правильно, но на грани?)
- Integration gaps (где склейка с соседними системами шатается?)
- Защитные реакции команды (что команда отвергнет?)

### 5.2 Output

```
design verdict: approved | concerns | block
concerns:
  - what: ...
    why-it-matters: ...
    failure-mode: ...
    mitigation: ...
```

`block` или `concerns` с failure mode «critical» — возврат на стадию 6 или 10.

---

## §6. Self-falsification (стадия 7) — между implementation и QA

Между implementation и QA gate оркестратор обязан **сам** сделать фальсификацию через [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md):

1. Сформулировать гипотезу одной фразой: «я закрыл задачу владельца через X»
2. Expectations table — что должно быть истинно (минимум 5 строк)
3. Reality check — что фактически на диске / в продукте / в данных
4. Gap table: `Ожидание | Факт | Δ | Severity | Next action | Усилие человека (0-100)`
5. Verdict: `confirmed | partially confirmed | falsified`

Если verdict ≠ `confirmed` — оркестратор НЕ доставляет, а идёт обратно на стадию 6.

**Цель self-falsification:** ловить «success theater» (агент рапортует success, а на самом деле что-то пропустил) ДО того как это увидит QA-агент или владелец.

---

## §7. RCA-injection (стадия 10)

Если на стадиях 7-9 найден gap, оркестратор НЕ просто чинит симптом — спавнит `rca-investigator`:

1. **5 whys** до root cause
2. Применяет шкалу 0-100 (см. [`templates/02-rca-effort-scale-0-100.md`](../templates/02-rca-effort-scale-0-100.md))
3. Делает design-injection в:
   - стандарт (если был пробел в каноне)
   - скилл (если был пробел в protocol)
   - агента (если был пробел в роли)
   - mandatory delivery format (если был пробел в проверке)
4. Логирует в `incidents.md` с: `Что произошло | Root cause | Design injection | Где зафиксировано`

**Workaround параллельно с root-cause** допустим только если время критично — но root-cause-fix приоритетнее.

---

## §8. Delivery format (стадия 11)

Финальный ответ владельцу всегда содержит **12 секций**:

1. Было / Стало (Was / Became)
2. JTBD-сценарий
3. Input checklist
4. Output checklist
5. Outcome checklist
6. Design review (verdict + risks)
7. QA review (verdict + что прошло, что нет)
8. Deploy & PR review
9. Hypothesis falsification (gap table + verdict)
10. Owner effort digest (next-action table со шкалой 0-100)
11. Run Evidence (что выполнено, ссылки на коммиты/файлы)
12. Canonical Vocabulary Check (PASS / FAIL с указанием нарушений)

См. [`templates/06-owner-effort-digest.md`](../templates/06-owner-effort-digest.md) и [`AGENTS.md`](../AGENTS.md).

---

## §9. Outcome verify (стадия 12)

Через N дней (от 1 до 30 в зависимости от природы изменения) оркестратор обязан **вернуться** и проверить:

- Outcome из стадии 2 материализовался в метриках?
- Команда / владелец продолжают использовать новое решение?
- Появились ли новые гепы из-за этого изменения?

Если outcome не материализовался — **новый bead** с гипотезой почему и план следующей итерации. Это закрывает petlю: output → outcome.

---

## §10. Anti-patterns — что оркестратор НЕ делает

| Anti-pattern | Почему плохо | Что делать вместо |
|---|---|---|
| «Запускаю QA только если есть время» | QA становится случайным, gaps накапливаются | QA — это gate, не опция |
| «Сам сделаю всю работу» | Оркестратор НЕ developer — он спавнит роли | Делегировать через subagent calls |
| «Если subagent сказал OK — значит OK» | Trust but verify — agent intent ≠ actual outcome | Reading actual files / artifacts |
| «Этот клиент особенный» | Создаёт hardcoded ветки, ломает универсальность | 4×yes Generalization Gate |
| «Falsification это для критичных задач» | Любой output может содержать success theater | Self-falsification — обязательна для всех substantial deliveries |
| «Сделаем рефактор позже» | «Позже» не наступает | Root cause fix immediately, не workaround |
| «Доставлю draft, владелец доделает» | Стандарт качества «handoff-ready», не draft | Стадия 12 outcome verify требует завершённости |

---

## §11. Метрика качества оркестратора

| Метрика | Формула | Целевое значение |
|---|---|---|
| Stages skipped rate | `skipped_stages / total_deliveries` | 0% (любой пропуск = RCA) |
| Self-falsification gap rate | `falsified_post_self_check / falsified_post_QA` | > 80% (агент сам ловит большинство, не QA) |
| QA pass rate first attempt | `qa_pass / total_qa_runs` | 60-80% (если 100% — QA слишком мягкий, если <40% — стадия 6 хромает) |
| Owner effort per delivery | среднее «усилие человека (0-100)» из effort digest | < 30 (большинство задач — без вмешательства владельца) |
| Outcome verify success | `outcomes_materialized / outcomes_planned` | > 70% |

---

## §12. Как это применять самому

1. **Скопируй этот playbook** в свою команду
2. **Назначь оркестратора** — человека или AI-агента (см. [`agents/manager-lead-orchestrator.md`](../agents/manager-lead-orchestrator.md))
3. **Настрой роли** — кто `developer`, кто `qa`, кто `design-reviewer`, кто `rca-investigator`. Один человек может играть несколько ролей, но не все одновременно для одной задачи (нужна independence для QA/design)
4. **Запиши 12 стадий** в свой ритуал (Notion / Linear / `.beads`)
5. **Mandatory: stages 5, 7, 8, 9, 12 не пропускать**
6. **Метрики из §11** ведутся командой, обсуждаются на ретро

---

## Связанные файлы

- [`agents/manager-lead-orchestrator.md`](../agents/manager-lead-orchestrator.md) — каноничное описание оркестратора как субагента
- [`agents/ui-qa-engineer.md`](../agents/ui-qa-engineer.md) — QA gate субагент
- [`agents/code-reviewer.md`](../agents/code-reviewer.md) — code review gate
- [`agents/design-art-director.md`](../agents/design-art-director.md) — design adversarial review
- [`agents/rca-investigator.md`](../agents/rca-investigator.md) — RCA после найденных gaps
- [`skills/01-hypothesis-gap-falsification.md`](../skills/01-hypothesis-gap-falsification.md) — обязательный self-falsification
- [`templates/04-expected-output-table.md`](../templates/04-expected-output-table.md) — контракт перед implementation
- [`templates/06-owner-effort-digest.md`](../templates/06-owner-effort-digest.md) — финальный effort digest
- [`standards/04-ai-management-workflow.md`](../standards/04-ai-management-workflow.md) — каноничный AI management workflow стандарт
