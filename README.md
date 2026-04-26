# Heroes Gap Theory for AI and Humans

> Методология диагностики разрывов (gaps) между ожиданием и реальностью — для команд, AI-агентов, продуктов, людей и компаний.

**Автор:** Илья Красинский (Ilya Krasinsky)
**Версия:** v0.1.0 (initial public release, 26 апреля 2026)
**Статус:** active — расширяется новыми формулами и методами
**Языки:** русский (основной) + English (через перевод)

---

## TL;DR — что внутри

Это публичный экспорт каноничной части **Gap Theory** — методологии, которую я применял с 2024-2026 года в advising-проектах с командами marketing analytics platforms (galaxypets, autovin, fashionhub, sleepwell, designcraft, fitcrew, bigfin), а также в собственной команде Praxis/Pulse.ai.

Репозиторий даёт **9 стандартов**, **18 скилов**, **10 субагентов**, **5 примеров диагностики** и **playbook AI-management** — всё, чтобы внешняя команда или AI-агент могли:

1. **Найти разрыв** между ожиданием и реальностью в любой системе (человек, команда, продукт, процесс)
2. **Классифицировать разрыв** по 4 типам: knowledge / execution / feedback / integration
3. **Измерить glue effort** — сколько усилий нужно человеку, чтобы склеить разрыв (шкала 0-100)
4. **Сформулировать гипотезу** в фальсифицируемой форме с baseline + threshold + critical chain
5. **Фальсифицировать** свои выводы через expectation-vs-reality таблицу
6. **Применить REDUCE framework** для преодоления сопротивления при изменениях

---

## Кому это нужно

| Роль | JTBD | Что брать первым |
|---|---|---|
| **Founder / CEO** | Диагностировать команду и процессы по переписке/действиям | `examples/01-diagnose-founder-from-correspondence.md`, `playbook/01-ai-management-galaxypets-style.md` |
| **Product Manager** | Найти где продукт теряет пользователей и как это починить системно | `standards/01-gap-theory.md`, `examples/04-diagnose-product-from-user-actions.md` |
| **Sales lead / РОП** | Разобрать звонки команды по картам разрыва, поставить выводы | `examples/03-diagnose-sales-team-from-calls.md`, `agents/process-correspondence-investigator.md` |
| **AI engineer / agent builder** | Сделать чтобы агент сам фальсифицировал свои гипотезы и не врал | `skills/01-hypothesis-gap-falsification.md`, `agents/hypothesis-designer.md`, `playbook/03-orchestrator-with-qa-gate.md` |
| **Advising consultant** | Помогать клиенту найти где он сам себе мешает | `standards/05-persuasion-belief-change.md`, `standards/06-champion-playbook-change-virus.md` |
| **Researcher / academic** | Применить Gap Theory к когнитивным процессам и change management | `standards/01-gap-theory.md`, `CITATION.cff` |

---

## Структура репозитория

```
.
├── README.md                          ← вы здесь
├── LICENSE                            ← summary, ссылается на две лицензии
├── LICENSE-CODE                       ← Apache 2.0 для кода (агенты, скрипты)
├── LICENSE-DOCS                       ← CC BY 4.0 для текстов (стандарты, examples)
├── CITATION.cff                       ← академическая атрибуция
├── CONTRIBUTING.md                    ← как контрибьютить
├── CHANGELOG.md                       ← история версий
├── AGENTS.md                          ← мета-правила для AI-агентов
│
├── standards/                         ← 9 каноничных стандартов
│   ├── 01-gap-theory.md
│   ├── 02-typical-gaps-prevention.md
│   ├── 03-outcome-zero-gap-jtbd-transfer.md
│   ├── 04-ai-management-workflow.md
│   ├── 05-persuasion-belief-change.md
│   ├── 06-champion-playbook-change-virus.md
│   ├── 07-abcdx-segmentation.md
│   ├── 08-speed-of-trust-economics.md
│   └── 09-praxis-crew-ai-management-onboarding.md
│
├── skills/                            ← 18 рабочих скилов
│   ├── 01-hypothesis-gap-falsification.md   (КЛЮЧЕВОЙ — фальсификация гипотез)
│   ├── 02-rca-incidents-with-effort-scale.md
│   ├── 03-so-what-outcome-ladder.md
│   ├── 04-protocol-challenge.md
│   ├── 05-systematic-thorough-enumeration.md
│   ├── 06-hypothesis-eval-loop.md
│   ├── 07-gap-theory-extension-validate.md
│   ├── 08-root-cause-first.md
│   ├── 09-critical-chain-design.md
│   ├── 10-agent-reasoning-log.md
│   ├── 11-subagent-falsification.md
│   ├── 12-persuasion-belief-change.md
│   ├── 13-champion-playbook-gap-theory.md
│   ├── 14-actionable-hypothesis.md
│   ├── 15-next-outcome-output-mapping.md
│   ├── 16-task-completion-persistence.md
│   ├── 17-document-creation-guard.md
│   └── 18-trust-metric.md
│
├── agents/                            ← 10 субагентов (Claude/AI-agnostic)
│   ├── hypothesis-designer.md
│   ├── rca-investigator.md
│   ├── outcome-designer.md
│   ├── design-art-director.md
│   ├── inception-reviewer.md
│   ├── process-correspondence-investigator.md
│   ├── client-persona-reviewer.md
│   ├── ui-qa-engineer.md
│   ├── code-reviewer.md
│   └── manager-lead-orchestrator.md  ← с обязательным QA + design gate
│
├── templates/                         ← 10 готовых шаблонов
│   ├── 01-five-whys-plus-h.md
│   ├── 02-rca-effort-scale-0-100.md
│   ├── 03-hypothesis-card.md
│   ├── 04-expected-output-table.md
│   ├── 05-gap-table.md
│   ├── 06-owner-effort-digest.md
│   ├── 07-quick-ticket-card.md
│   ├── 08-jtbd-scenarium-tree.md
│   ├── 09-critical-chain-card.md
│   └── 10-so-what-ladder.md
│
├── examples/                          ← 5 worked examples диагностики
│   ├── 01-diagnose-founder-from-correspondence.md
│   ├── 02-diagnose-company-from-team-chat.md
│   ├── 03-diagnose-sales-team-from-calls.md
│   ├── 04-diagnose-product-from-user-actions.md
│   └── 05-diagnose-self-from-own-week-log.md
│
├── worked-examples/                   ← по одному пример на скилл
│   └── (16 файлов, по одному на скилл)
│
├── playbook/                          ← практические сборки
│   ├── 01-ai-management-galaxypets-style.md
│   ├── 02-recommended-tickets-and-skills.md
│   └── 03-orchestrator-with-qa-design-gate.md
│
└── docs/
    └── glossary.md                    ← термины
```

---

## Ключевая идея Gap Theory

### 4 типа разрывов

| Тип | Симптом | Что значит | Где искать |
|---|---|---|---|
| **Knowledge gap** | «Я не знал что так можно» | Человек/команда не знает что вообще существует решение или как его применить | Onboarding, документация, обучение |
| **Execution gap** | «Знаю, но не делаю» | Намерение есть, но не доходит до действия | Процессы, привычки, ритуалы |
| **Feedback gap** | «Сделал — не понял что получилось» | Действие совершено, но обратная связь отсутствует или искажена | Метрики, дашборды, ритуалы ретро |
| **Integration gap** | «Каждый шаг ОК, но всё вместе не склеивается» | Шаги и инструменты работают, но между ними нужна склейка человеком | API, ручные импорты, копипаст |

### 4 измерения Glue Effort (усилия на склейку)

1. **Cognitive** — сколько надо подумать чтобы понять что делать
2. **Mechanical** — сколько кликов, форм, копипастов
3. **Integration** — сколько систем переключить
4. **Coordination** — сколько людей надо синхронизировать

### Шкала измерения усилий 0-100 (см. `templates/02-rca-effort-scale-0-100.md`)

- **0** = агент/процесс делает сам, у владельца нет шагов
- **10** = одно подтверждение
- **30** = 2-3 клика
- **50** = **любой клик владельца** (один порог)
- **70** = ручное расследование
- **100** = переделка с нуля
- **+100** = провал доверия (надо восстанавливать отношения)

---

## Лицензирование

Двойная лицензия:

- **Код** (агенты, скрипты, шаблоны как структура) — [Apache License 2.0](LICENSE-CODE). Можно использовать коммерчески, модифицировать, распространять. Сохраняй копирайт-нотис и явно отмечай свои изменения.
- **Текст** (стандарты, examples, playbook, README) — [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-DOCS). Можно использовать коммерчески, модифицировать, распространять — **с обязательной атрибуцией**: «Based on Heroes Gap Theory by Ilya Krasinsky, https://github.com/idkras/heroes-gap-theory-for-ai-and-humans».

**Авторские права:** © 2024-2026 Ilya Krasinsky. Все права сохраняются у автора. Лицензии дают вам права на использование при условии атрибуции.

Если ты делаешь коммерческий продукт/курс/консалтинг на базе Gap Theory — формальных требований согласовывать со мной нет, но я буду рад услышать как ты применяешь метод: idkras@gmail.com.

---

## Цитирование

Если ссылаешься в публикации, презентации, курсе — используй [`CITATION.cff`](CITATION.cff) или такой формат:

> Krasinsky, I. (2026). *Heroes Gap Theory for AI and Humans: A methodology for diagnosing gaps between expectation and reality in teams, products, and AI agents.* GitHub. https://github.com/idkras/heroes-gap-theory-for-ai-and-humans

---

## Контрибьютинг

См. [`CONTRIBUTING.md`](CONTRIBUTING.md). Кратко:

1. Issues — для обсуждения новых разрывов, методов, формул
2. PRs — для исправлений / расширений / переводов / новых worked-examples
3. Discussions — для применения теории к новым доменам

Особенно нужны:
- Worked examples из других индустрий (не ecommerce / analytics)
- Перевод на английский
- Применение к когнитивно-поведенческим контекстам (психология, образование)
- Формулы измерения glue effort в не-маркетинговых системах

---

## Roadmap

Версии будут добавлять (приоритет — обратная связь сообщества):

- **v0.2** — формулы измерения glue effort + калькулятор для команды
- **v0.3** — Gap Theory extension «Agent Dunbar and Capacity of Relaxation» (как масштабируется команда AI-агентов под одним человеком)
- **v0.4** — Gap Theory для образовательных программ (курсы, тренинги)
- **v0.5** — interactive web-interface для self-diagnosis
- **v1.0** — каноничная книжка с worked examples из 10 индустрий

---

## Связанные работы и источники

Эта методология опирается на:

- **Theory of Constraints** (Eliyahu Goldratt) — критическая цепочка
- **Jobs to be Done** (Clayton Christensen) — через атомарные JTBD
- **Картина мира + Объяснительная модель** (Максим Ильяхов) — для коммуникации изменений
- **REDUCE framework** (Jonah Berger, *The Catalyst*) — для преодоления сопротивления
- **Speed of Trust** (Stephen M.R. Covey) — экономика доверия
- **5 пороков команды** (Patrick Lencioni)

И на 10+ лет практического применения в продуктовых, аналитических и sales командах.

---

## Контакт

- Email: idkras@gmail.com
- GitHub: [idkras](https://github.com/idkras)
- Telegram (для команды): по запросу через email

Если делаешь что-то крутое на базе теории — пиши, добавлю в каталог использований.
