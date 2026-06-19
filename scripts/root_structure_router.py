#!/usr/bin/env python3
"""Root structure router — config-driven классификатор top-level записей корня workspace.

SSOT манифест: config/root-structure-manifest.yaml (allowed_dirs/files/dotfiles,
routing[], junk_patterns/junk_dirs, large_data, owner_decision_dirs).

Универсальный (без hardcode клиента/проекта): классификация по pattern-правилам.
Новый клиент/проект попадает под routing-правила без правки кода.

Зависимости: PyYAML + стандартная библиотека (zero сторонних).

CLI:
    python3 scripts/root_structure_router.py --report
    python3 scripts/root_structure_router.py --report --out report.md
    python3 scripts/root_structure_router.py --apply --only route
    python3 scripts/root_structure_router.py --apply --only junk

По умолчанию (без --apply) — только отчёт, ничего не двигает (dry-run).
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML обязателен
    sys.stderr.write("ERROR: PyYAML не установлен. Используй .venv/bin/python " "или pip install pyyaml.\n")
    raise

# ─────────────────────────────────────────────────────────────────────────
# Verdict-константы
# ─────────────────────────────────────────────────────────────────────────
V_ALLOWED = "allowed"
V_ROUTE = "route"
V_JUNK = "junk"
V_LARGE = "large_data_candidate"
V_OWNER = "owner_decision"
V_UNKNOWN = "unknown"
V_ERROR = "error"

VERDICT_ORDER = [V_ALLOWED, V_ROUTE, V_JUNK, V_OWNER, V_LARGE, V_UNKNOWN, V_ERROR]


# ─────────────────────────────────────────────────────────────────────────
# Pure-функции (тестируемые без I/O)
# ─────────────────────────────────────────────────────────────────────────
def load_manifest(path: str | Path) -> dict[str, Any]:
    """Прочитать YAML-манифест в dict. Бросает FileNotFoundError если нет файла.

    M3 — structural validation: hard fail с описательной ошибкой на битом YAML
    (вместо silent miscategorize при, например, routing=None или scalar вместо list).

    F8/L2 — cross-check инвариант: НИ ОДИН routing.target не должен указывать на dir,
    который перечислен в owner_decision_dirs ИЛИ junk_dirs. Иначе route переносит
    запись в папку, помеченную как «не трогать без owner» / «junk» → противоречие.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Манифест {path} не является YAML-mapping (got {type(data)})")

    # --- M3: структурная валидация типов ключевых секций ---
    _list_keys = [
        "allowed_dirs",
        "allowed_files",
        "allowed_dotfiles",
        "allowed_dir_patterns",
        "routing",
        "junk_patterns",
        "junk_dirs",
        "junk_files",
        "owner_decision_dirs",
    ]
    for key in _list_keys:
        if key in data and data[key] is not None and not isinstance(data[key], list):
            raise ValueError(
                f"Манифест {path}: ключ '{key}' обязан быть list, "
                f"получено {type(data[key]).__name__} ({data[key]!r})"
            )

    routing = data.get("routing")
    if routing is not None:
        for i, rule in enumerate(routing):
            if not isinstance(rule, dict):
                raise ValueError(
                    f"Манифест {path}: routing[{i}] обязан быть mapping, " f"получено {type(rule).__name__} ({rule!r})"
                )
            if not rule.get("id"):
                raise ValueError(f"Манифест {path}: routing[{i}] без обязательного поля 'id'")
            if not (rule.get("match") or rule.get("match_any")):
                raise ValueError(f"Манифест {path}: routing rule '{rule.get('id')}' " f"без 'match' и без 'match_any'")
            if "target" not in rule:
                raise ValueError(f"Манифест {path}: routing rule '{rule.get('id')}' без поля 'target'")

    large_data = data.get("large_data")
    if large_data is not None and not isinstance(large_data, dict):
        raise ValueError(f"Манифест {path}: 'large_data' обязан быть mapping, " f"получено {type(large_data).__name__}")

    # --- F8/L2: routing.target ∉ owner_decision_dirs ∪ junk_dirs ---
    owner_dirs = set(_as_list(data.get("owner_decision_dirs")))
    junk_dirs = set(_as_list(data.get("junk_dirs")))
    forbidden_targets = owner_dirs | junk_dirs
    for rule in _as_list(data.get("routing")):
        if not isinstance(rule, dict):
            continue
        target = rule.get("target")
        if not target or target == "NEEDS_OWNER_DECISION":
            continue
        # target обычно вида "exports/" / "docs/" / "<internal-folder>/" — нормализуем имя dir
        target_dir = str(target).rstrip("/").split("/")[0]
        if target_dir in forbidden_targets:
            where = "owner_decision_dirs" if target_dir in owner_dirs else "junk_dirs"
            raise ValueError(
                f"Манифест {path}: routing rule '{rule.get('id')}' target '{target}' "
                f"указывает на dir '{target_dir}', который в {where} — "
                f"запись была бы перенесена в папку, помеченную как «не авто-трогать». "
                f"Вынеси '{target_dir}' в allowed_dirs ИЛИ смени target."
            )

    return data


def _as_list(value: Any) -> list:
    """Нормализовать None/scalar/list в list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _matches_any_glob(name: str, patterns: list[str]) -> bool:
    """True если name матчит хотя бы один glob-паттерн."""
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def _matches_any_dir_pattern(name: str, patterns: list[str]) -> bool:
    """True если name матчит хотя бы один allowed_dir_pattern.

    Спец-обработка bracketed-конвенции: pattern `[*]` означает «имя начинается с `[`»
    (каноническая knowledge/client content-dir). fnmatch трактует `[...]` как
    char-class, поэтому `[*]` обрабатывается явно. Остальные паттерны — обычный fnmatch.
    """
    for pat in patterns:
        if pat == "[*]":
            if name.startswith("["):
                return True
        elif fnmatch.fnmatch(name, pat):
            return True
    return False


def classify_entry(
    name: str,
    is_dir: bool,
    manifest: dict[str, Any],
    is_symlink: bool = False,
) -> dict[str, Any]:
    """Классифицировать одну top-level запись по имени.

    Приоритет (RCA 2026-06-02 reorder):
      allowed_exact → owner_decision → junk → allowed_dir_patterns/symlink
      → routing (first match) → unknown.
    Explicit-решения (owner_decision, junk) бьют broad bracket-pattern и symlink:
    junk/owner symlink или bracketed-dir всё равно флагается корректно.
    Классификация по ИМЕНИ записи (не рекурсивно).

    Returns dict: {entry, is_dir, verdict, target, reason, rule_id}.
    """
    allowed_dirs = set(_as_list(manifest.get("allowed_dirs")))
    allowed_files = set(_as_list(manifest.get("allowed_files")))
    allowed_dotfiles = set(_as_list(manifest.get("allowed_dotfiles")))
    allowed_dir_patterns = _as_list(manifest.get("allowed_dir_patterns"))
    allow_symlinks = bool(manifest.get("allow_symlinks", False))
    owner_dirs = set(_as_list(manifest.get("owner_decision_dirs")))
    junk_dirs = set(_as_list(manifest.get("junk_dirs")))
    junk_files = set(_as_list(manifest.get("junk_files")))
    junk_patterns = _as_list(manifest.get("junk_patterns"))
    routing = _as_list(manifest.get("routing"))

    base = {"entry": name, "is_dir": is_dir, "target": None, "rule_id": None}

    # 1. ALLOWED — точное имя в одном из allowed-наборов
    if is_dir and name in allowed_dirs:
        return {**base, "verdict": V_ALLOWED, "reason": "канонический allowed dir"}
    if not is_dir and name in allowed_files:
        return {**base, "verdict": V_ALLOWED, "reason": "канонический allowed file"}
    if not is_dir and name in allowed_dotfiles:
        return {**base, "verdict": V_ALLOWED, "reason": "канонический allowed dotfile"}

    # 2. OWNER_DECISION — точное имя dir (приоритет над junk/routing/symlink/bracket).
    #    H2: owner_decision_dirs применяется ТОЛЬКО к директориям, не к файлам —
    #    файл с именем совпавшим с owner-dir не должен молча уходить в owner_decision.
    if is_dir and name in owner_dirs:
        return {
            **base,
            "verdict": V_OWNER,
            "target": "NEEDS_OWNER_DECISION",
            "reason": "запись требует решения владельца",
        }

    # 3. JUNK — junk_dirs / junk_files (точное имя) или junk_patterns (glob по имени)
    #    C3/C4: НИ ОДНО junk-правило не применяется к symlink — symlink защищён
    #    (storytelling, .codex-memory~origin_main, skills и т.п. могут случайно
    #    совпасть по имени/glob, но мы их НЕ помечаем junk и НЕ двигаем).
    if not is_symlink and is_dir and name in junk_dirs:
        return {**base, "verdict": V_JUNK, "reason": "junk dir (в trash, не в репо)"}
    # junk_files — только для НЕ-symlink файлов (не задеть реальную dir / symlink)
    if not is_dir and not is_symlink and name in junk_files:
        return {**base, "verdict": V_JUNK, "reason": "junk file (stray, в trash, не в репо)"}
    # junk_patterns (glob) — тоже НЕ применяем к symlink (C3 защита storytelling и пр.)
    if not is_symlink and _matches_any_glob(name, junk_patterns):
        return {**base, "verdict": V_JUNK, "reason": "junk pattern (в trash, не в репо)"}

    # 4a. ALLOWED_DIR_PATTERNS — bracketed `[*]` content-dir by pattern
    #     (после junk/owner_decision, чтобы explicit-решения побеждали broad pattern)
    if is_dir and _matches_any_dir_pattern(name, [str(p) for p in allowed_dir_patterns]):
        return {**base, "verdict": V_ALLOWED, "reason": "канонический bracketed content-dir"}

    # 4b. SYMLINK — намеренный symlink (после junk/owner_decision/bracket)
    if is_symlink and allow_symlinks:
        return {**base, "verdict": V_ALLOWED, "reason": "intentional symlink"}

    # 5. ROUTING — first match wins (поддержка match / match_any + exclude)
    for rule in routing:
        if not isinstance(rule, dict):
            continue
        rule_id = rule.get("id")
        exclude = _as_list(rule.get("exclude"))
        if name in exclude:
            continue
        match_one = rule.get("match")
        match_any = _as_list(rule.get("match_any"))
        hit = False
        if match_one and fnmatch.fnmatch(name, str(match_one)):
            hit = True
        elif match_any and _matches_any_glob(name, [str(m) for m in match_any]):
            hit = True
        if hit:
            return {
                "entry": name,
                "is_dir": is_dir,
                "verdict": V_ROUTE,
                "target": rule.get("target"),
                "reason": rule.get("reason", ""),
                "rule_id": rule_id,
                "git_mv": bool(rule.get("git_mv", False)),
            }

    # 6. UNKNOWN — stray, ни под одно правило
    return {
        **base,
        "verdict": V_UNKNOWN,
        "reason": "stray-запись, не покрыта ни одним правилом манифеста",
    }


# ─────────────────────────────────────────────────────────────────────────
# I/O-функции (сканирование реального дерева)
# ─────────────────────────────────────────────────────────────────────────
def scan_root(root_path: str | Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Перебрать top-level записи корня, классифицировать каждую. .git пропускается.

    Корректно обрабатывает имена с пробелами/<teammate>ицей/скобками/·.
    """
    root = Path(root_path)
    results: list[dict[str, Any]] = []
    with os.scandir(root) as it:
        for entry in it:
            if entry.name == ".git":
                continue
            # H4: per-entry classify в try/except — PermissionError / OSError на
            # одной записи (broken symlink target, perm denied) НЕ должен ронять
            # весь scan; такая запись получает verdict="error", scan продолжается.
            try:
                # symlink check ПЕРЕД is_dir: symlink-на-dir рапортует is_dir=True,
                # поэтому islink проверяется первым и is_dir сбрасывается в False.
                try:
                    is_symlink = entry.is_symlink()
                except OSError:
                    is_symlink = False
                if is_symlink:
                    is_dir = False
                else:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        is_dir = False
                results.append(classify_entry(entry.name, is_dir, manifest, is_symlink=is_symlink))
            except OSError as exc:
                results.append(
                    {
                        "entry": entry.name,
                        "is_dir": False,
                        "verdict": V_ERROR,
                        "target": None,
                        "rule_id": None,
                        "reason": f"scan error: {exc.__class__.__name__}: {exc}",
                    }
                )
    results.sort(
        key=lambda r: (VERDICT_ORDER.index(r["verdict"]) if r["verdict"] in VERDICT_ORDER else 99, r["entry"].lower())
    )
    return results


def _dir_size_mb(path: Path) -> float:
    """Размер папки в MB. Пытается du, fallback на os.walk-сумму."""
    try:
        out = subprocess.run(
            ["du", "-sk", str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if out.returncode == 0:
            kb = int(out.stdout.split()[0])
            return kb / 1024.0
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    # fallback: os.walk сумма (медленнее)
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                total += fp.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total / (1024.0 * 1024.0)


def _glob_with_literal_brackets(root: Path, pattern: str) -> list[Path]:
    """Resolve glob где сегменты со скобками `[...]` трактуются ЛИТЕРАЛЬНО.

    pathlib.glob интерпретирует `<internal-folder>` как char-class и не матчит литеральную
    папку. Здесь walk посегментно: сегмент с `*`/`?` → fnmatch по listdir;
    сегмент без `*`/`?` (даже со скобками) → точное имя.
    """
    segments = [s for s in pattern.split("/") if s]
    frontier: list[Path] = [root]
    for seg in segments:
        nxt: list[Path] = []
        has_wildcard = "*" in seg or "?" in seg
        for cur in frontier:
            if not cur.is_dir():
                continue
            if has_wildcard:
                try:
                    for child in cur.iterdir():
                        if fnmatch.fnmatch(child.name, seg):
                            nxt.append(child)
                except OSError:
                    continue
            else:
                cand = cur / seg
                if cand.exists():
                    nxt.append(cand)
        frontier = nxt
    return frontier


def scan_large_data(root_path: str | Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """По large_data.scan_globs найти папки > threshold_mb → кандидаты на gitignore_in_place.

    F3/F10: стратегия gitignore_in_place — данные ОСТАЮТСЯ на месте, добавляются
    в .gitignore (НЕ перемещаются, НЕ symlink в git). scan репортит кандидата +
    предлагаемую .gitignore-строку (rel_path с trailing slash для папки).

    Returns list dict: {path, rel_path, size_mb, gitignore_line}.
    """
    root = Path(root_path)
    ld = manifest.get("large_data") or {}
    threshold = float(ld.get("threshold_mb", 100))
    globs = _as_list(ld.get("scan_globs"))
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for g in globs:
        for match in _glob_with_literal_brackets(root, str(g)):
            if not match.is_dir() or match.is_symlink():
                continue
            rel = str(match.relative_to(root))
            if rel in seen:
                continue
            seen.add(rel)
            size_mb = _dir_size_mb(match)
            if size_mb >= threshold:
                candidates.append(
                    {
                        "path": str(match),
                        "rel_path": rel,
                        "size_mb": round(size_mb, 1),
                        # gitignore-строка: путь папки относительно корня + trailing slash.
                        # leading slash якорит к корню репо (не матчит вложенные одноимённые).
                        "gitignore_line": f"/{rel}/",
                    }
                )
    candidates.sort(key=lambda c: c["size_mb"], reverse=True)
    return candidates


# ─────────────────────────────────────────────────────────────────────────
# Отчёт
# ─────────────────────────────────────────────────────────────────────────
def render_report(results: list[dict[str, Any]], large: list[dict[str, Any]]) -> str:
    """Markdown-отчёт: таблица по verdict-группам + large_data + счётчики."""
    counts = {v: 0 for v in VERDICT_ORDER}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    lines: list[str] = []
    lines.append("# Root structure report")
    lines.append("")
    lines.append(
        f"Всего top-level записей классифицировано: {len(results)} "
        f"(.git пропущен). Сгенерировано {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
    )
    lines.append("")
    lines.append("## Счётчики по вердиктам")
    lines.append("")
    lines.append("| verdict | count |")
    lines.append("|---|---|")
    for v in VERDICT_ORDER:
        lines.append(f"| {v} | {counts.get(v, 0)} |")
    lines.append(f"| large_data (отдельный скан) | {len(large)} |")
    lines.append("")

    # Одна consolidated таблица на verdict-группу
    for v in VERDICT_ORDER:
        group = [r for r in results if r["verdict"] == v]
        if not group:
            continue
        lines.append(f"## verdict: {v} ({len(group)})")
        lines.append("")
        lines.append("| entry | type | verdict | target | reason |")
        lines.append("|---|---|---|---|---|")
        for r in group:
            etype = "dir" if r.get("is_dir") else "file"
            target = r.get("target") or "—"
            reason = (r.get("reason") or "").replace("|", "\\|")
            entry = r["entry"].replace("|", "\\|")
            lines.append(f"| {entry} | {etype} | {v} | {target} | {reason} |")
        lines.append("")

    # large_data секция (gitignore_in_place — НЕ move, НЕ symlink)
    lines.append("## large_data candidates (> threshold → gitignore_in_place)")
    lines.append("")
    lines.append(
        "Стратегия: данные остаются на месте, добавляются в `.gitignore`, "
        "Syncthing синкает реальный путь. Symlink-in-git ЗАПРЕЩЁН (broken на clone без Syncthing). "
        "Предлагаемые `.gitignore`-строки ниже — owner добавляет их вручную после ревью."
    )
    lines.append("")
    if large:
        lines.append("| rel_path | size_mb | предлагаемая .gitignore строка |")
        lines.append("|---|---|---|")
        for c in large:
            rel = str(c["rel_path"]).replace("|", "\\|")
            gi = str(c["gitignore_line"]).replace("|", "\\|")
            lines.append(f"| {rel} | {c['size_mb']} | `{gi}` |")
    else:
        lines.append("_Нет папок выше threshold (или scan_globs не совпали)._")
    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Apply (moves)
# ─────────────────────────────────────────────────────────────────────────
def _git_tracked(root: Path, rel: str) -> bool:
    """True если файл tracked в git.

    H1: `--` separator перед путём — иначе пути со скобками (`<internal-folder>`) или
    начинающиеся с `-` git трактует как pathspec-magic / опции и даёт ложный ответ.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _resolve_trash_dir(root: Path, ts: str) -> Path:
    """F6: trash-папка кладётся ВНЕ корня workspace, не как новый top-level stray.

    Приоритет: <root>/.cache/root-trash/<ts>/ (если .cache существует ИЛИ gitignored
    по convention — .cache редко трекается) → fallback tempfile.gettempdir().
    `.cache` — стандартный gitignored runtime-кэш; не плодит top-level записи в корне
    (внутри .cache, не на верхнем уровне рядом с allowed_dirs).
    """
    cache_root = root / ".cache" / "root-trash" / ts
    # .cache допустим как контейнер trash — он не top-level stray (вложен в .cache).
    return cache_root


def apply_moves(
    results: list[dict[str, Any]],
    root_path: str | Path,
    dry_run: bool = True,
    git_mv: bool = True,
    only: str | None = None,
) -> list[dict[str, Any]]:
    """Выполнить moves для verdict=route (и junk→trash).

    НИКОГДА не трогает allowed/owner_decision/large_data/unknown/error.
    large_data вообще не двигается (gitignore_in_place — см. scan_large_data).
    dry_run=True (default) только печатает план, ничего не двигает.

    Защита от потери данных (RCA 2026-06-02 code-review):
      B1 — collision: если destination уже существует → action="skip-collision",
           executed=False (НИКОГДА не перезаписываем).
      B2 — git mv: capture returncode; != 0 → action="git-mv-failed", executed=False.
      C1 — cross-fs / любой move в try/except: при ошибке src НЕ трогается,
           action="move-failed", executed=False, в plan записывается error.
      F6 — trash ВНЕ корня (.cache/root-trash/<ts>/), не новый top-level stray.

    Returns list dict: {entry, action, src, dst, executed, [reason|stderr|error]}.
    """
    root = Path(root_path)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    trash_dir = _resolve_trash_dir(root, ts)
    plan: list[dict[str, Any]] = []

    for r in results:
        verdict = r["verdict"]
        # Фильтр --only
        if only == "route" and verdict != V_ROUTE:
            continue
        if only == "junk" and verdict != V_JUNK:
            continue
        if verdict not in (V_ROUTE, V_JUNK):
            continue  # allowed/owner/large/unknown/error — НИКОГДА не двигаем

        entry = r["entry"]
        src = root / entry

        if verdict == V_ROUTE:
            target = r.get("target")
            if not target or target == "NEEDS_OWNER_DECISION":
                plan.append(
                    {
                        "entry": entry,
                        "action": "skip-needs-owner",
                        "src": str(src),
                        "dst": None,
                        "executed": False,
                    }
                )
                continue
            dst_dir = root / target
            dst = dst_dir / entry

            # B1 — collision check ПЕРЕД любым move (route): не перезаписываем.
            if dst.exists() or dst.is_symlink():
                plan.append(
                    {
                        "entry": entry,
                        "action": "skip-collision",
                        "src": str(src),
                        "dst": str(dst),
                        "executed": False,
                        "reason": f"destination уже существует: {dst} — НЕ перезаписываем",
                    }
                )
                continue

            use_git = git_mv and bool(r.get("git_mv")) and _git_tracked(root, entry)
            action = "git-mv" if use_git else "move"
            if not dry_run:
                if use_git:
                    # B2 — capture returncode; != 0 → git-mv-failed, НЕ executed.
                    try:
                        proc = subprocess.run(
                            ["git", "mv", "--", entry, str(Path(target) / entry)],
                            cwd=str(root),
                            capture_output=True,
                            text=True,
                            timeout=60,
                        )
                    except (OSError, subprocess.SubprocessError) as exc:
                        plan.append(
                            {
                                "entry": entry,
                                "action": "git-mv-failed",
                                "src": str(src),
                                "dst": str(dst),
                                "executed": False,
                                "stderr": f"{exc.__class__.__name__}: {exc}",
                            }
                        )
                        continue
                    if proc.returncode != 0:
                        plan.append(
                            {
                                "entry": entry,
                                "action": "git-mv-failed",
                                "src": str(src),
                                "dst": str(dst),
                                "executed": False,
                                "stderr": (proc.stderr or "").strip(),
                            }
                        )
                        continue
                else:
                    # C1 — cross-fs / любой move в try/except: src нетронут при ошибке.
                    try:
                        dst_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), str(dst))
                    except (OSError, shutil.Error) as exc:
                        plan.append(
                            {
                                "entry": entry,
                                "action": "move-failed",
                                "src": str(src),
                                "dst": str(dst),
                                "executed": False,
                                "error": f"{exc.__class__.__name__}: {exc}",
                            }
                        )
                        continue
            plan.append(
                {
                    "entry": entry,
                    "action": action,
                    "src": str(src),
                    "dst": str(dst),
                    "executed": not dry_run,
                }
            )

        elif verdict == V_JUNK:
            # SAFETY (RCA 2026-06-05): НЕ перемещать в trash git-tracked файлы/папки.
            # Манифест может ошибочно классифицировать tracked-контент (output/ 1165
            # файлов) как junk_dir — shutil.move в trash = массовое удаление tracked
            # из дерева. Tracked junk → owner decision (git rm вручную), не авто-trash.
            if _git_tracked(root, entry):
                plan.append(
                    {
                        "entry": entry,
                        "action": "skip-tracked-junk-needs-owner",
                        "src": str(src),
                        "executed": False,
                        "reason": (
                            "junk-классифицированная запись git-tracked — НЕ авто-trash "
                            "(возможна ошибка манифеста / реальный committed-контент); "
                            "owner решает git rm или manifest reclassify"
                        ),
                    }
                )
                continue
            dst = trash_dir / entry
            # B1 — collision check для junk→trash тоже (не перезаписываем в trash).
            if (dst.exists() or dst.is_symlink()) and not dry_run:
                plan.append(
                    {
                        "entry": entry,
                        "action": "skip-collision",
                        "src": str(src),
                        "dst": str(dst),
                        "executed": False,
                        "reason": f"trash destination уже существует: {dst} — НЕ перезаписываем",
                    }
                )
                continue
            if not dry_run:
                # C1 — move в trash в try/except: src нетронут при ошибке.
                try:
                    trash_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                except (OSError, shutil.Error) as exc:
                    plan.append(
                        {
                            "entry": entry,
                            "action": "trash-failed",
                            "src": str(src),
                            "dst": str(dst),
                            "executed": False,
                            "error": f"{exc.__class__.__name__}: {exc}",
                        }
                    )
                    continue
            plan.append(
                {
                    "entry": entry,
                    "action": "trash",
                    "src": str(src),
                    "dst": str(dst),
                    "executed": not dry_run,
                }
            )

    return plan


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────
def _default_manifest_path(root: Path) -> Path:
    return root / "config" / "root-structure-manifest.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Root structure router — классификатор + apply (config-driven).")
    parser.add_argument("--root", default=os.getcwd(), help="корень workspace (default: cwd)")
    parser.add_argument(
        "--manifest", default=None, help="путь к манифесту (default: <root>/config/root-structure-manifest.yaml)"
    )
    parser.add_argument("--report", action="store_true", help="напечатать markdown-отчёт в stdout")
    parser.add_argument("--out", default=None, help="сохранить отчёт в файл")
    parser.add_argument("--apply", action="store_true", help="выполнить moves (иначе dry-run)")
    parser.add_argument("--only", choices=["route", "junk"], default=None, help="ограничить apply одним verdict")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest) if args.manifest else _default_manifest_path(root)
    if not manifest_path.exists():
        sys.stderr.write(f"ERROR: манифест не найден: {manifest_path}\n")
        return 1

    manifest = load_manifest(manifest_path)
    results = scan_root(root, manifest)
    large = scan_large_data(root, manifest)

    report = render_report(results, large)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        sys.stderr.write(f"Отчёт сохранён: {args.out}\n")
    if args.report or not (args.apply or args.out):
        print(report)

    if args.apply:
        plan = apply_moves(results, root, dry_run=False, git_mv=True, only=args.only)
        sys.stderr.write(f"\nApply executed: {len([p for p in plan if p['executed']])} moves\n")
        for p in plan:
            sys.stderr.write(f"  [{p['action']}] {p['entry']} → {p['dst']}\n")
    else:
        # dry-run preview moves
        plan = apply_moves(results, root, dry_run=True, git_mv=True, only=args.only)
        if plan:
            sys.stderr.write(f"\nDry-run move plan ({len(plan)} entries, ничего не двигалось):\n")
            for p in plan:
                sys.stderr.write(f"  [{p['action']}] {p['entry']} → {p['dst']}\n")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
