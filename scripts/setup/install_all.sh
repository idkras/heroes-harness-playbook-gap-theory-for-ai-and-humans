#!/usr/bin/env bash
# install_all.sh — idempotent one-shot installer для всего toolchain Heroes Harness.
#
# JTBD: когда участник клонирует харнесс из git, он (или SessionStart-хук за него)
# запускает ОДНУ команду — и весь инструментарий приходит в рабочее состояние:
#   1. python .venv + зависимости из requirements.txt (pytest, PyYAML, networkx)
#   2. beads (bd) — AI-native трекер задач
#   3. Dolt — БД-движок под beads ("DAC DB" на слух = Dolt DB)
#   4. bd init — инициализация .beads/ если её нет
#   5. graphify — опционально (canonical-only, в публичный шаблон не входит)
#
# Идемпотентно: уже установленное пропускается, безопасно гонять повторно.
# macOS (brew) — первичный путь; curl-upstream — fallback для bd на Linux.
#
# Usage:
#   scripts/setup/install_all.sh           # установить недостающее
#   scripts/setup/install_all.sh --check   # только отчёт (exit!=0 если чего-то нет), ничего не ставит
#
# Почему это отдельный скрипт, а не внутри harness_bootstrap.py:
#   bootstrap — stdlib-only Python (обвязка/хуки/checksum). Установка тулчейна —
#   сетевые операции (brew/curl/pip), их место в shell-инсталляторе. bootstrap
#   лишь ВЫЗЫВАЕТ этот скрипт один раз (marker-guarded) на первом SessionStart.

set -uo pipefail

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

ok()   { printf '  ✅ %s\n' "$1"; }
miss() { printf '  ⚠️  %s\n' "$1"; }
act()  { printf '  → %s\n' "$1"; }

MISSING=0

echo "# Heroes Harness — toolchain installer"
echo "root: $ROOT  (mode: $([ "$CHECK" = 1 ] && echo check || echo install))"

# ---------------------------------------------------------------- 1. python venv
if [ -x ".venv/bin/python" ]; then
  ok ".venv present ($(.venv/bin/python --version 2>&1))"
elif [ "$CHECK" = 1 ]; then
  miss ".venv missing"; MISSING=1
else
  act "python3 -m venv .venv"; python3 -m venv .venv || miss "venv create failed"
fi

# ---------------------------------------------------------------- 2. python deps
if [ -x ".venv/bin/python" ] && [ -f requirements.txt ]; then
  DEPS_OK=1
  .venv/bin/python - <<'PY' || DEPS_OK=0
import importlib.util, sys
missing = [m for m in ("pytest", "yaml", "networkx") if importlib.util.find_spec(m) is None]
sys.exit(1 if missing else 0)
PY
  if [ "$DEPS_OK" = 1 ]; then
    ok "python deps satisfied (pytest, PyYAML, networkx)"
  elif [ "$CHECK" = 1 ]; then
    miss "python deps incomplete"; MISSING=1
  else
    act "pip install -r requirements.txt"; .venv/bin/pip install -q --upgrade pip >/dev/null 2>&1
    .venv/bin/pip install -q -r requirements.txt || miss "pip install failed"
  fi
fi

# ---------------------------------------------------------------- 3. beads (bd)
if command -v bd >/dev/null 2>&1; then
  ok "bd present ($(bd version 2>&1 | head -1))"
elif [ "$CHECK" = 1 ]; then
  miss "bd missing"; MISSING=1
elif command -v brew >/dev/null 2>&1; then
  act "brew install beads (fallback: curl upstream)"
  brew install beads >/dev/null 2>&1 \
    || curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash \
    || miss "bd install failed — см. https://github.com/steveyegge/beads"
else
  act "curl upstream install bd"
  curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash \
    || miss "bd install failed — см. https://github.com/steveyegge/beads"
fi

# ---------------------------------------------------------------- 4. Dolt (DAC DB)
if command -v dolt >/dev/null 2>&1; then
  ok "dolt present ($(dolt version 2>&1 | head -1))"
elif [ "$CHECK" = 1 ]; then
  miss "dolt missing (движок beads)"; MISSING=1
elif command -v brew >/dev/null 2>&1; then
  act "brew install dolt"; brew install dolt >/dev/null 2>&1 || miss "dolt install failed"
else
  miss "dolt: установи вручную — https://docs.dolthub.com/introduction/installation"
fi

# ---------------------------------------------------------------- 5. bd init
# beads usable, если резолвит workspace (bd list даёт exit 0) — это покрывает и
# локальный .beads/, и worktree/мульти-репо, где БД резолвится из родителя.
if command -v bd >/dev/null 2>&1; then
  if bd list >/dev/null 2>&1; then
    ok "beads workspace resolved (Dolt DB задач)"
  elif [ "$CHECK" = 1 ]; then
    miss ".beads not initialized"; MISSING=1
  else
    act "bd init"; bd init >/dev/null 2>&1 && ok "bd init done" || miss "bd init failed (запусти 'bd init' вручную)"
  fi
fi

# ---------------------------------------------------------------- 6. graphify (опц.)
if command -v graphify >/dev/null 2>&1; then
  ok "graphify present"
else
  miss "graphify: optional/canonical-only — НЕ входит в публичный шаблон."
  printf '       граф зависимостей доступен через: bd graph (+ networkx в .venv)\n'
fi

echo
if [ "$CHECK" = 1 ] && [ "$MISSING" = 1 ]; then
  printf '🔴 toolchain incomplete — запусти: scripts/setup/install_all.sh\n'
  exit 1
fi
printf '🟢 toolchain ready\n'
