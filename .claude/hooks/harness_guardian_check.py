#!/usr/bin/env python3
"""harness_guardian_check — cycle-end Stop hook: verify the harness did not break.

Path B (project-progress-auditor verdict 78% vs 12% for a new triple): this hook does
NOT reimplement a harness verifier — it ORCHESTRATES existing wire-targets and surfaces
one 4-row verdict at Stop. The verifier itself (`verify_harness_wiring.py`) already exists
in skill `0-governance-harness-portability` but was dormant (1 span / 60 days) — not invoked
in the work cycle. This hook closes that gap.

Four rows (each a thin call to an existing tool, never a new judge):
  wiring      verify_harness_wiring.py --json → gaps==0   (skill 0-governance-harness-portability)
  graph       graphify-out/graph.json exists + fresh       (make graphify-doctor mtime proxy)
  branch/bead substantial work on own branch+bead, not shared main (fix part-2 read-only gap)
  tools       decision-log (.reasoning-log) / graphify / networkx exercised this session (WARN-only)

Honest scope: presence-check (verifiers ran + gaps==0), NOT proof of depth. Deeper review =
@project-progress-auditor in runtime. tools row is WARN-only (auditor flagged calibration risk
as the bottleneck — false-positive shelf-ware). Default mode = Phase 1 WARN (advisory print,
exit 0); promotion to BLOCK after baseline via HARNESS_GUARDIAN_BLOCK=1.

Contract: reads Claude Code Stop hook JSON from stdin. NEVER hard-breaks the session on its own
error (fail-open, exit 0). Override: HARNESS_GUARDIAN_ACK="<reason >=12 chars>".
Staged rollback: HARNESS_GUARDIAN_PHASE1_WARN=1 (force WARN even if BLOCK enabled).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        if out:
            return Path(out).resolve()
    except Exception:
        pass
    return Path(__file__).resolve().parents[2]


def _run(cmd: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def _row_wiring(root: Path) -> tuple[str, str]:
    """gaps==0 via existing verify_harness_wiring.py --json (skill 0-governance-harness-portability)."""
    verifier = root / ".agents/skills/0-governance-harness-portability/scripts/verify_harness_wiring.py"
    if not verifier.exists():
        return "⚠️", "verify_harness_wiring.py не найден (skill 0-governance-harness-portability)"
    rc, out = _run([sys.executable, str(verifier), "--json", "--repo-root", str(root)], root, timeout=40)
    gaps = None
    try:
        data = json.loads(out)
        gaps = data.get("gaps") if isinstance(data, dict) else None
        if gaps is None and isinstance(data, dict):
            gaps = len([r for r in data.get("results", []) if r.get("status") in ("FAIL", "❌")])
    except Exception:
        gaps = None
    # detect-of-detector (code-review M1 + AGENTS.md green-health-false-positive):
    # gaps==0 → ✅; gaps>0 → ❌; gaps is None → schema drift / parse fail = ⚠️ INCONCLUSIVE,
    # NEVER a silent ✅ (that is exactly the false-positive class guardian exists to catch).
    if rc == 0 and gaps == 0:
        return "✅", "gaps==0 (verify_harness_wiring --json)"
    if gaps and gaps > 0:
        return "❌", f"wiring gaps={gaps} (verify_harness_wiring --json)"
    return "⚠️", f"INCONCLUSIVE: gaps не распознан (rc={rc}, manifest schema drift?)"


def _row_graph(root: Path) -> tuple[str, str]:
    """graphify graph.json freshness (mtime). Honest scope: freshness only — queryability
    НЕ проверяется здесь (design-review: mtime-as-✅ = green-health-false-positive). Полная
    проверка queryable = `make graphify-doctor` (агент запускает в ASSEMBLE step 2)."""
    gj = root / "graphify-out" / "graph.json"
    if not gj.exists():
        return "⚠️", "graphify-out/graph.json отсутствует (make graphify-build)"
    try:
        age_h = (time.time() - gj.stat().st_mtime) / 3600.0
    except Exception:
        return "⚠️", "graph.json есть, mtime недоступен"
    if age_h < 168:
        return "✅", f"freshness ok: mtime {age_h:.0f}h (queryability не проверена — make graphify-doctor)"
    return "⚠️", f"stale {age_h:.0f}h (make graphify-update)"


def _in_worktree(root: Path) -> bool:
    """Canonical worktree detect (code-review M2): git-dir != git-common-dir → linked worktree.
    Reuses the same signal as first_substantial_write_branch_bead_gate.py (no path-substring guess)."""
    rc1, gd = _run(["git", "rev-parse", "--git-dir"], root, timeout=5)
    rc2, gcd = _run(["git", "rev-parse", "--git-common-dir"], root, timeout=5)
    if rc1 == 0 and rc2 == 0 and gd.strip() and gcd.strip():
        return gd.strip() != gcd.strip()
    # fallback to path heuristic only if git-dir probe failed
    return ".claude/worktrees/" in str(root) or "/tmp/wt-" in str(root)


def _row_branch_bead(root: Path) -> tuple[str, str]:
    """Fix part-2 gap: substantial cycle on shared main without branch+bead → WARN."""
    rc, head = _run(["git", "symbolic-ref", "--short", "HEAD"], root, timeout=5)
    branch = head.strip() if rc == 0 else "?"
    shared = {"main", "master", "production", "release"}
    in_wt = _in_worktree(root)
    if branch in shared and not in_wt:
        return "⚠️", f"работа на shared {branch} без own worktree (см. branch-bead-first-touch)"
    return "✅", f"ветка {branch}" + (" (worktree)" if in_wt else "")


def _row_tools(root: Path) -> tuple[str, str]:
    """WARN-only: were decision-log / graphify / networkx exercised? (auditor: calibration bottleneck)."""
    spans_dir = root / ".reasoning-log" / "spans"
    span_count = 0
    if spans_dir.is_dir():
        try:
            cutoff = time.time() - 24 * 3600
            for p in spans_dir.rglob("*"):
                if p.is_file() and p.stat().st_mtime > cutoff:
                    span_count += 1
        except Exception:
            pass
    graph_fresh = (root / "graphify-out" / "graph.json").exists()
    parts = []
    parts.append(f"decision-log spans(24h)={span_count}")
    parts.append("graphify=есть" if graph_fresh else "graphify=нет")
    # tools row never blocks — informational only
    status = "✅" if (span_count > 0 or graph_fresh) else "⚠️"
    return status, " · ".join(parts)


def main() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0  # fail-open
    # recursion guard (Claude Code re-fires Stop with stop_hook_active=True)
    if hook_input.get("stop_hook_active"):
        return 0

    ack = os.environ.get("HARNESS_GUARDIAN_ACK", "").strip()
    if len(ack) >= 12:
        return 0  # owner ack — skip silently

    root = _repo_root()
    rows = [
        ("wiring", *_row_wiring(root)),
        ("graph", *_row_graph(root)),
        ("branch/bead", *_row_branch_bead(root)),
        ("tools", *_row_tools(root)),
    ]
    # anti-alarm-fatigue (design-review): all-green → one line; any ⚠️/❌ → full table.
    all_green = all(r[1] == "✅" for r in rows)
    if all_green:
        verdict = "🛡️ harness ok (wiring✅ graph✅ branch/bead✅ tools✅)"
    else:
        lines = ["🛡️ harness-guardian · cycle-end"]
        for name, status, detail in rows:
            lines.append(f"  {name:<11} {status} {detail}")
        verdict = "\n".join(lines)

    # BLOCK candidate = wiring ❌ only (graph/branch-bead/tools are advisory).
    wiring_failed = rows[0][1] == "❌"
    block_enabled = os.environ.get("HARNESS_GUARDIAN_BLOCK") == "1"
    phase1_warn = os.environ.get("HARNESS_GUARDIAN_PHASE1_WARN") == "1"

    sys.stderr.write(verdict + "\n")
    if wiring_failed and block_enabled and not phase1_warn:
        sys.stderr.write(
            "\nharness-guardian BLOCK: wiring gaps>0 — harness рассинхронизирован.\n"
            "Fix: python3 .agents/skills/0-governance-harness-portability/scripts/verify_harness_wiring.py\n"
            'Override: HARNESS_GUARDIAN_ACK="<reason >=12 chars>"\n'
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
