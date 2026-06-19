#!/usr/bin/env python3
"""bd_anti_legend — единый детектор bare-«легенда»-кодов в beads (pr-rick-camh).

Owner 2026-06-13: «доработай хуки, чтобы в beads не было С1 H1/H4 — протокол
антилегенда, его нужно встроить в workflow yaml и скрипты создания тикетов».

RCA-источник: закрытый bead pr-rick-271k нёс `(C1+H1+H4+H2)` в title и `C1` /
`(H1/H4)` / `(H2)` / `(M6)` внутри подзадач — это внутренние коды code-reviewer /
гипотез / missing-test, которые ничего не значат для owner без отдельного
словаря-легенды. Анти-легенда (AGENTS.md §Installed skills → Anti-legend) такие
голые коды запрещает: «полные названия критериев в той же строке, что и код; не
выдавать владельцу отдельный мини-словарь».

Это SSOT-детектор. Его импортируют ОБА слоя enforcement, чтобы правило не
дрейфовало (§Wiring-first):
  • `.claude/hooks/bd_anti_legend_gate.py` — PreToolUse Bash gate на `bd create` /
    `bd update` (доезжает до партнёров через harness-manifest.json);
  • `scripts/check_bd_anti_legend.py` — lefthook pre-commit backstop на staged
    `.beads/issues.jsonl` (canonical git-слой).

Детект (precision-first — узкий surface: title + Sub-tasks checklist):

  1. Parenthetical legend cluster — `(C1+H1+H4+H2)`, `(H1/H4)`, `(H2)`, `(M6)`.
     Скобка, внутри которой ТОЛЬКО finding-коды через `+ / ,`, не добавляет
     читаемого смысла → ВСЕГДА нарушение (ищется в title + всём description).
  2. Inline bare finding-code — токен `C1` / `H4` / `M6` (finding-буква
     C,H,G,E,M,D,F латиница + С,К,Г,Е,М,Д,Ф <teammate>ица + 1-2 цифры), который НЕ
     объяснён §0-макросом ` — <название>` / `: <название>` сразу после кода
     (ищется в title + строках Sub-tasks checklist).

НЕ ловится (precision guards):
  • приоритеты P0–P3 (P не в finding-наборе);
  • bead-id `pr-rick-271k` (lowercase-префикс, не uppercase-буква+цифра);
  • `PR #502` (две буквы / нет ведущей одиночной finding-буквы);
  • уже объяснённый код: `C1 — единый classify_check` (§0-макрос after);
  • годы / widget-id / многобуквенные токены (`GA4`, `BU16571`).

Универсально: никаких client/project хардкодов — чистая текстовая логика.
"""

from __future__ import annotations

import re

# Finding-буквы: code-reviewer (C), hypothesis (H), gap (G), expectation (E),
# missing-test (M), design (D), finding (F) + <teammate>ические зеркала.
_FINDING_CHARS = "CHGEMDFСКГЕМДФ"
# Любой буквенно-цифровой символ обоих алфавитов — для word-boundary без \b
# (стандартный \b ненадёжен на <teammate>ице в некоторых сборках).
_WORDCHAR = r"[0-9A-Za-zА-Яа-яЁё]"
_CODE = r"[" + _FINDING_CHARS + r"]\d{1,2}"

# (C1+H1+H4+H2) | (H1/H4) | (H2) | (M6) — скобка только из finding-кодов.
_PAREN_CLUSTER_RE = re.compile(r"\(\s*" + _CODE + r"(?:\s*[+/,]\s*" + _CODE + r")*\s*\)")
# Одиночный код с обеих сторон word-boundary.
_INLINE_RE = re.compile(r"(?<!" + _WORDCHAR + r")(" + _CODE + r")(?!" + _WORDCHAR + r")")
# §0-макрос: код объяснён, если сразу после идёт ` — слово` / `-- слово` / `: слово`.
_EXPLAINED_AFTER_RE = re.compile(r"^[*_\s]{0,3}(?:—|--|:)\s*\S")

# Checklist-строка `- [x] ...` / `- [ ] ...` (любой маркер статуса).
_CHECK_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX~!]\]\s*(.+)$")


def find_violations(text: str) -> list[dict]:
    """Вернуть нарушения в одном куске текста.

    Каждое нарушение: {"kind": "cluster"|"inline", "code": <строка>, "pos": int}.
    Сначала ловятся parenthetical clusters; их содержимое маскируется, чтобы
    внутренние коды не считались ещё раз как inline (нет двойного счёта)."""
    if not text:
        return []
    violations: list[dict] = []
    for m in _PAREN_CLUSTER_RE.finditer(text):
        violations.append({"kind": "cluster", "code": m.group(0), "pos": m.start()})
    masked = _PAREN_CLUSTER_RE.sub(lambda mm: " " * len(mm.group(0)), text)
    for m in _INLINE_RE.finditer(masked):
        tail = masked[m.end() : m.end() + 12]
        if _EXPLAINED_AFTER_RE.match(tail):
            continue  # §0-макрос: код объяснён рядом — допустимо
        violations.append({"kind": "inline", "code": m.group(1), "pos": m.start()})
    return violations


def _checklist_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        m = _CHECK_LINE_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def scan_bead(title: str, description: str) -> list[dict]:
    """Просканировать один bead. Возвращает список нарушений с полем `where`.

    Surface (precision/recall баланс):
      • title — clusters И inline-коды;
      • description — clusters везде (высокая точность), inline — только на
        строках Sub-tasks checklist (ограниченный surface против ложных
        срабатываний в свободной прозе)."""
    title = title or ""
    description = description or ""
    out: list[dict] = []
    for v in find_violations(title):
        out.append({**v, "where": "title"})
    for v in find_violations(description):
        if v["kind"] == "cluster":
            out.append({**v, "where": "description"})
    for line in _checklist_lines(description):
        for v in find_violations(line):
            if v["kind"] == "inline":
                out.append({**v, "where": "subtask", "line": line.strip()[:80]})
    return out


def format_report(bead_id: str, violations: list[dict]) -> str:
    """Человекочитаемый отчёт по нарушениям одного bead (для stderr хука/lefthook)."""
    codes = ", ".join(sorted({v["code"] for v in violations}))
    lines = [f"  {bead_id or '<new>'}: голые коды легенды → {codes}"]
    for v in violations:
        loc = v["where"]
        if v.get("line"):
            loc += f" «{v['line']}»"
        kind_ru = "кластер в скобках" if v["kind"] == "cluster" else "одиночный код"
        lines.append(f"    - {v['code']} ({kind_ru}) в {loc}")
    return "\n".join(lines)


REMEDIATION = (
    "Анти-легенда (AGENTS.md §Anti-legend): внутренние коды ревью/гипотез "
    "(C1/H1/H4/M6/…) не несут смысла для owner без словаря.\n"
    "  Уберите код ИЛИ замените на полное название в той же строке:\n"
    "    плохо:   …не врали друг другу (C1+H1+H4+H2)\n"
    "    хорошо:  …не врали друг другу\n"
    "    плохо:   когда code-reviewer нашёл C1 → output …\n"
    "    хорошо:  когда code-reviewer нашёл расхождение определений «закрыто» → output …\n"
)
