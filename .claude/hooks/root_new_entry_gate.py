#!/usr/bin/env python3
"""PreToolUse hook — BLOCK создания нового stray top-level entry в корне workspace.

Закрывает design-review F1+F7 для root-structure-guardian: декларативный манифест
(config/root-structure-manifest.yaml) + post-hoc router (scripts/root_structure_router.py)
не мешают агенту СОЗДАТЬ новый мусорный top-level файл/папку. Этот hook — mechanical
PreToolUse gate, который ловит и Write, и Bash (mkdir/cp/mv/touch/redirect) — иначе Bash
обходит Write-only проверку (F7).

Контракт Claude Code PreToolUse hook:
    stdin  = JSON {tool_name, tool_input, ...}
    exit 0 = pass (Write/Bash продолжается)
    exit 2 = BLOCK (stderr доносится агенту)
Регистрируется в .claude/settings.json matcher "Write|Edit|NotebookEdit|MultiEdit|Bash".

Принципы (universal, config-driven — без hardcode клиента/проекта):
  - Срабатывает ТОЛЬКО для прямых top-level child НАСТОЯЩЕГО корня workspace
    (не worktree-корня; см. _resolve_workspace_root). Вложенные пути (scripts/x.py,
    <internal-folder>/...) — не наше дело, exit 0.
  - Классификация имени через scripts/root_structure_router.classify_entry. verdict
    != "allowed" → BLOCK.
  - FAIL-OPEN на любой ошибке (нет манифеста / import fail / parse error / странный
    stdin) → exit 0 + stderr warn. Hook НЕ должен ломать workflow агента.
  - Override: env ROOT_STRUCTURE_NEW_ENTRY_ACK (≥12 chars) → exit 0 + note.
  - Консервативный Bash-парсинг: при неуверенности НЕ блокировать (минимум false-positive).

Override:
    ROOT_STRUCTURE_NEW_ENTRY_ACK="<reason ≥12 chars>"  # legitimate exception
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HOOK_NAME = "root_new_entry_gate"
ACK_ENV = "ROOT_STRUCTURE_NEW_ENTRY_ACK"
MANIFEST_REL = ("config", "root-structure-manifest.yaml")
ROUTER_REL = ("scripts", "root_structure_router.py")

# Пути, которые НЕ являются top-level корня workspace (даже если выглядят коротко).
# Абсолютные пути вне workspace, временные каталоги — пропускаем.
_SKIP_ABS_PREFIXES = ("/tmp", "/var", "/private/var", "/private/tmp")


def _warn(msg: str) -> None:
    sys.stderr.write(f"[{HOOK_NAME}] {msg}\n")


def _pass() -> None:
    raise SystemExit(0)


def _block(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    raise SystemExit(2)


# ─────────────────────────────────────────────────────────────────────────
# Workspace-root resolution (НАСТОЯЩИЙ корень, не worktree)
# ─────────────────────────────────────────────────────────────────────────
def _resolve_workspace_root() -> Path | None:
    """Найти НАСТОЯЩИЙ корень workspace (не worktree-корень).

    Приоритет:
      1. env CLAUDE_PROJECT_DIR — если содержит и манифест, и router.
      2. parent(git-common-dir) — в worktree git-common-dir = <real-root>/.git,
         поэтому его parent = real workspace root (а git-toplevel = worktree-корень).
      3. git rev-parse --show-toplevel.
    Для каждого кандидата возвращаем ПЕРВЫЙ, под которым реально лежат и манифест,
    и router. Если ни один не подходит — None (fail-open caller'ом).
    """
    candidates: list[Path] = []

    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if common.returncode == 0:
            common_dir = Path(common.stdout.strip())
            if not common_dir.is_absolute():
                # относительный путь (".git") → резолвим от cwd
                common_dir = (Path.cwd() / common_dir).resolve()
            # parent от .../<root>/.git == <root>
            candidates.append(common_dir.parent)
    except (OSError, subprocess.SubprocessError):
        pass

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if top.returncode == 0:
            candidates.append(Path(top.stdout.strip()))
    except (OSError, subprocess.SubprocessError):
        pass

    # Выбираем первого кандидата, под которым есть и манифест, и router.
    for cand in candidates:
        try:
            cand_r = cand.resolve()
        except OSError:
            continue
        if cand_r.joinpath(*MANIFEST_REL).exists() and cand_r.joinpath(*ROUTER_REL).exists():
            return cand_r

    # fallback: первый существующий кандидат (даже без манифеста — caller fail-open'нет)
    for cand in candidates:
        try:
            if cand.exists():
                return cand.resolve()
        except OSError:
            continue
    return None


def _load_router(root: Path):
    """Импортировать root_structure_router из <root>/scripts/ через importlib.

    Возвращает (module, manifest_dict) либо (None, None) при любой ошибке.
    """
    router_path = root.joinpath(*ROUTER_REL)
    manifest_path = root.joinpath(*MANIFEST_REL)
    if not router_path.exists() or not manifest_path.exists():
        return None, None

    scripts_dir = str(router_path.parent)
    added = False
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
        added = True
    try:
        import importlib

        if "root_structure_router" in sys.modules:
            rsr = importlib.reload(sys.modules["root_structure_router"])
        else:
            rsr = importlib.import_module("root_structure_router")
        manifest = rsr.load_manifest(manifest_path)
        return rsr, manifest
    except Exception as exc:  # noqa: BLE001 — fail-open на любой import/parse error
        _warn(f"router import/manifest load failed ({exc.__class__.__name__}: {exc}) — fail-open")
        return None, None
    finally:
        if added:
            try:
                sys.path.remove(scripts_dir)
            except ValueError:
                pass


# ─────────────────────────────────────────────────────────────────────────
# Классификация одной целевой записи
# ─────────────────────────────────────────────────────────────────────────
def _classify_target(rsr, manifest: dict, root: Path, target: Path, force_is_dir: bool | None = None) -> dict | None:
    """Если target — НОВЫЙ прямой top-level child корня → вернуть classify_entry verdict.

    Возвращает None когда:
      - target НЕ прямой child корня (вложен глубже / вне корня),
      - target уже существует (не новая запись).
    force_is_dir: для Bash mkdir мы знаем что это dir даже если ещё не создан.
    """
    try:
        target_r = target.resolve() if target.is_absolute() else (root / target).resolve()
    except OSError:
        return None

    # Прямой top-level child корня? (parent == root)
    if target_r.parent != root:
        return None

    name = target_r.name
    if not name or name == ".git":
        return None

    # Уже существует → не новая запись (Write в существующий файл — не наше дело)
    if target_r.exists() or target_r.is_symlink():
        return None

    if force_is_dir is not None:
        is_dir = force_is_dir
    else:
        # Write file_path без extension мог бы быть dir, но Write всегда создаёт файл.
        is_dir = False

    try:
        return rsr.classify_entry(name, is_dir, manifest, is_symlink=False)
    except Exception as exc:  # noqa: BLE001 — fail-open
        _warn(f"classify_entry failed for {name!r} ({exc.__class__.__name__}: {exc}) — fail-open")
        return None


def _format_block_message(verdict: dict) -> str:
    name = verdict.get("entry", "?")
    v = verdict.get("verdict", "?")
    target = verdict.get("target")
    reason = verdict.get("reason", "")
    lines = [
        f"[{HOOK_NAME}] BLOCKED — попытка создать новую top-level запись «{name}» в корне workspace.",
        f"  verdict: {v}" + (f"  reason: {reason}" if reason else ""),
    ]
    if target and target != "NEEDS_OWNER_DECISION":
        lines.append(f"  router предлагает положить это в: {target}")
    elif target == "NEEDS_OWNER_DECISION":
        lines.append("  router: это owner_decision — нужно решение владельца, не авто-создание в корне.")
    lines.append("")
    lines.append("Корень workspace — SSOT canon (config/root-structure-manifest.yaml). Новый stray")
    lines.append("top-level entry запрещён. Варианты:")
    lines.append(
        f"  1. Положи файл/папку в правильное место"
        + (f" ({target})" if target and target != "NEEDS_OWNER_DECISION" else " (см. router --report).")
    )
    lines.append("  2. Если это легитимная новая canon-запись корня — добавь её имя в")
    lines.append("     config/root-structure-manifest.yaml (allowed_dirs/allowed_files/allowed_dotfiles).")
    lines.append(f'  3. Намеренное исключение — env {ACK_ENV}="<причина ≥12 символов>".')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Bash command parsing — извлечь top-level create-цели
# ─────────────────────────────────────────────────────────────────────────
def _strip_heredocs(command: str) -> str:
    """Вырезать тела heredoc (`<<EOF ... EOF`, `<<'EOF'`, `<<-EOF`) из команды.

    RCA 2026-06-12 (pr-rick-pq2b): хук получает СЫРУЮ bash-команду, включая тело
    heredoc (например `cat > f <<'EOF' ... EOF`). Содержимое heredoc — это ДАННЫЕ
    (текст файла / commit message), НЕ shell-токены. Парсить его как shell —
    источник false-positive: строка `[name](<abs>) so` отдавала `)` в redirect-regex
    → BLOCK на несуществующей top-level записи «)». Снимаем тело heredoc до парсинга;
    сам редирект `> f` остаётся в первой строке и проверяется нормально.

    Known gap (code-review PR#473 F1.a): `bash <<EOF\nmkdir stray\nEOF` — тело
    heredoc, поданное в `bash`/`sh`, РЕАЛЬНО исполняется, но мы его срезаем →
    stray-create внутри executable-heredoc проскочит gate. Приемлемо: agent-flows
    почти не используют `bash <<EOF` для create-ops; при необходимости —
    ROOT_STRUCTURE_NEW_ENTRY_ACK не нужен (gate просто не сработает). Trade-off
    выбран в пользу нуля false-positive на data-heredocs (частый случай).
    """
    lines = command.split("\n")
    out: list[str] = []
    i = 0
    # heredoc-интродьюсер: <<word | <<'word' | <<"word" | <<-word (optional - strips tabs)
    intro_re = re.compile(r"<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = intro_re.search(line)
        if m:
            delim = m.group(2)
            # пропускаем все строки до строки-ограничителя (delim, опц. с ведущими табами)
            i += 1
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            # строку-ограничитель НЕ добавляем в out (это маркер, не команда)
        i += 1
    return "\n".join(out)


def _split_subcommands(command: str) -> list[str]:
    """Грубо разбить shell-команду на под-команды по ; && || | & newline.

    Консервативно: для оценки top-level creates достаточно посегментного разбора.
    Тела heredoc вырезаются заранее (_strip_heredocs) — это данные, не shell.
    """
    parts = re.split(r"(?:&&|\|\||[;\n|&])", _strip_heredocs(command))
    return [p.strip() for p in parts if p.strip()]


def _safe_tokens(segment: str) -> list[str] | None:
    """shlex.split с fallback на None при unbalanced quotes (консервативно — skip)."""
    try:
        return shlex.split(segment)
    except ValueError:
        return None


def _is_topish(path_str: str) -> bool:
    """Похоже ли что path_str — кандидат на top-level child (а не вложенный/абсолютный вне).

    Консервативно: пропускаем (return False) пути, в которых есть '/' (вложенные),
    абсолютные пути под /tmp /var и т.п., '-'-options, '~', glob-метасимволы.
    """
    if not path_str or path_str.startswith("-"):
        return False
    if path_str.startswith("~"):
        return False
    if any(ch in path_str for ch in ("*", "?", "[", "]")) and not path_str.startswith("["):
        # glob (но bracketed [name] — легитимная top-level конвенция, не glob)
        return False
    # Абсолютный путь под temp/var → не наш корень
    for pref in _SKIP_ABS_PREFIXES:
        if path_str.startswith(pref):
            return False
    # Вложенный путь (содержит '/') и НЕ оканчивается на '/' как top-level dir с trailing slash
    stripped = path_str.rstrip("/")
    if "/" in stripped:
        # абсолютный путь обрабатываем отдельно в caller (резолвим через root);
        # относительный с '/' = вложенный → не top-level child
        if not path_str.startswith("/"):
            return False
    return True


def _extract_bash_targets(command: str) -> list[tuple[str, bool | None]]:
    """Вернуть список (path_str, force_is_dir) кандидатов top-level create из Bash-команды.

    Покрывает: mkdir [-p] <name...>, touch <name...>, cp ... <dst>, mv ... <dst>,
    `> name` / `>> name` redirect.
    force_is_dir: True для mkdir, False для touch/redirect/cp-file/mv-file (точно не знаем
    для cp/mv → None, classify по имени; mkdir → True).
    Консервативно: при сомнении НЕ добавляем (fail-open caller).
    """
    targets: list[tuple[str, bool | None]] = []
    for seg in _split_subcommands(command):
        # redirect: что-то > name  /  >> name.
        # Исключаем из захвата () {} — иначе `<abs>) so` отдаёт `)` как имя
        # (RCA 2026-06-12 pr-rick-pq2b). Редирект-цель = путь, скобок там не бывает.
        for m in re.finditer(r"(?<![0-9])>>?\s*([^\s;|&<>(){}]+)", seg):
            cand = m.group(1).strip().strip('"').strip("'")
            if _is_topish(cand):
                targets.append((cand, False))

        tokens = _safe_tokens(seg)
        if not tokens:
            continue
        cmd0 = tokens[0]

        if cmd0 == "mkdir":
            for tok in tokens[1:]:
                if tok.startswith("-"):
                    continue
                if _is_topish(tok):
                    targets.append((tok, True))
        elif cmd0 == "touch":
            for tok in tokens[1:]:
                if tok.startswith("-"):
                    continue
                if _is_topish(tok):
                    targets.append((tok, False))
        elif cmd0 in ("cp", "mv"):
            # destination = последний non-option аргумент
            args = [t for t in tokens[1:] if not t.startswith("-")]
            if len(args) >= 2:
                dst = args[-1]
                if _is_topish(dst):
                    # dst может быть file или dir — точно не знаем → None (classify по имени)
                    targets.append((dst, None))
    return targets


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────
def main() -> None:
    # 1. Read stdin JSON — fail-open на битом stdin
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as exc:  # noqa: BLE001
        _warn(f"bad stdin JSON ({exc.__class__.__name__}) — fail-open")
        _pass()

    if not isinstance(payload, dict):
        _warn("stdin not a JSON object — fail-open")
        _pass()

    # 2. Override ack
    ack = (os.environ.get(ACK_ENV) or "").strip()
    if len(ack) >= 12:
        _warn(f"override via {ACK_ENV} (reason: {ack[:60]}) — pass")
        _pass()

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        _pass()

    # 3. Resolve real workspace root + router
    root = _resolve_workspace_root()
    if root is None:
        _warn("cannot resolve workspace root — fail-open")
        _pass()

    rsr, manifest = _load_router(root)
    if rsr is None or manifest is None:
        # уже warned внутри _load_router
        _pass()

    # 4a. Write-family: tool_input.file_path
    if tool_name in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        fp = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not fp:
            _pass()
        verdict = _classify_target(rsr, manifest, root, Path(str(fp)))
        if verdict is not None and verdict.get("verdict") != rsr.V_ALLOWED:
            _block(_format_block_message(verdict))
        _pass()

    # 4b. Bash: parse command for top-level create ops
    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        if not isinstance(command, str) or not command.strip():
            _pass()
        for cand_str, force_dir in _extract_bash_targets(command):
            verdict = _classify_target(rsr, manifest, root, Path(cand_str), force_is_dir=force_dir)
            if verdict is not None and verdict.get("verdict") != rsr.V_ALLOWED:
                _block(_format_block_message(verdict))
        _pass()

    # Любой другой tool — не наше дело
    _pass()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — финальный fail-open guard
        sys.stderr.write(f"[{HOOK_NAME}] unexpected error ({exc.__class__.__name__}: {exc}) — fail-open\n")
        raise SystemExit(0)
