#!/usr/bin/env python3
r"""harness_doctor.py — reads harness-workflow.yaml (the SSOT) and verifies that
every element it declares actually came up. ONE command answers "did the harness
install without errors?".

This is the falsifiable proof a fresh clone is healthy: it does not trust that
SessionStart ran — it CHECKS, by the SSOT, section by section, and prints a verdict
table with an exit code.

Criteria (each → PASS / WARN / FAIL), derived from harness-workflow.yaml sections:

  [toolchain]   toolchain.required + getting_started
    venv+deps   PyYAML/pytest/networkx importable (the install_all.sh deps)
    bd          `bd` on PATH (beads task tracker)
    bd-usable   `bd list` resolves a workspace (dolt embedded + bd init done)
  [hooks]       getting_started.session_start_chain + harness-manifest.json
    bootstrap   SessionStart bootstrap registered in .claude/settings.json
    wiring      verify_harness_wiring.py → gaps == 0
  [integrity]
    checksum    harness_template_checksum.py --verify → OK
  [project_management]   project_management.*
    scaffold    projects/all-projects + every declared numbered lane folder exists
    lanes-sync  lanes.json ids == harness-workflow.yaml project_management.lanes (no drift)
    pm-doctor   project_status_symlinks.py doctor → exit 0
  [local_only]  local_only.beads_dolt
    ignored     each declared local-only path is gitignored
    untracked   .beads is NOT tracked in git (partners never inherit it)
  [skills]      skills_index
    present     every skill path in skills_index exists on disk

WARN (not FAIL): toolchain not yet installed pre-`install_all.sh` — the harness is
designed to work degraded, so a missing tool is WARN with the exact fix command.
FAIL: a declared element is broken/inconsistent (drift, wiring gap, tracked .beads).

Exit codes: 0 = no FAIL (PASS or WARN only); 1 = at least one FAIL; 2 = SSOT unreadable.

Usage:
    python3 .agents/skills/0-governance-harness-portability/scripts/harness_doctor.py
    python3 .../harness_doctor.py --json
    python3 .../harness_doctor.py --strict   # WARN also fails (CI gate)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and (Path(env) / "harness-workflow.yaml").exists():
        return Path(env).resolve()
    cur = (start or Path(__file__)).resolve()
    for cand in (cur, *cur.parents):
        if (cand / "harness-workflow.yaml").exists() and (cand / ".git").exists():
            return cand
    # fall back to git toplevel
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=8)
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return cur.parents[3] if len(cur.parents) > 3 else cur


def run(cmd: list[str], root: Path, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(root), check=False)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def load_ssot(root: Path):
    """Read harness-workflow.yaml. Needs PyYAML — which is itself part of the toolchain.

    Returns (data, None) or (None, reason). If PyYAML is missing the harness is by
    definition not installed yet — the caller turns that into a WARN, not a crash.
    """
    f = root / "harness-workflow.yaml"
    if not f.exists():
        return None, "harness-workflow.yaml missing"
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return None, "PyYAML not installed (run scripts/setup/install_all.sh)"
    try:
        return yaml.safe_load(f.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"harness-workflow.yaml unparseable: {e.__class__.__name__}"


class Doctor:
    def __init__(self, root: Path):
        self.root = root
        self.results: list[dict] = []

    def add(self, section: str, check: str, status: str, detail: str) -> None:
        self.results.append({"section": section, "check": check, "status": status, "detail": detail})

    # ── toolchain ──────────────────────────────────────────────────────────
    def check_toolchain(self, ssot: dict | None) -> None:
        missing = [m for m in ("yaml", "pytest", "networkx") if not _importable(m)]
        if not missing:
            self.add("toolchain", "venv+deps", PASS, "PyYAML/pytest/networkx importable")
        else:
            self.add("toolchain", "venv+deps", WARN, f"missing {missing} → bash scripts/setup/install_all.sh")
        if shutil.which("bd"):
            self.add("toolchain", "bd", PASS, "bd on PATH")
            rc, _ = run(["bd", "list"], self.root, timeout=20)
            self.add("toolchain", "bd-usable", PASS if rc == 0 else WARN,
                     "`bd list` resolves workspace" if rc == 0 else "`bd list` fails → run `bd init`")
        else:
            self.add("toolchain", "bd", WARN, "bd not on PATH → bash scripts/setup/install_all.sh")
            self.add("toolchain", "bd-usable", WARN, "n/a (bd absent) — harness fails-open without bd")

    # ── hooks ──────────────────────────────────────────────────────────────
    def check_hooks(self) -> None:
        settings = self.root / ".claude" / "settings.json"
        bootstrap_wired = False
        if settings.exists():
            try:
                d = json.loads(settings.read_text(encoding="utf-8"))
                blob = json.dumps(d.get("hooks", {}))
                bootstrap_wired = "harness_bootstrap" in blob
            except json.JSONDecodeError:
                pass
        self.add("hooks", "bootstrap", PASS if bootstrap_wired else FAIL,
                 "SessionStart harness_bootstrap registered" if bootstrap_wired
                 else "harness_bootstrap NOT in settings.json SessionStart")
        verifier = self.root / ".agents/skills/0-governance-harness-portability/scripts/verify_harness_wiring.py"
        if verifier.exists():
            rc, out = run(["python3", str(verifier), "--repo-root", str(self.root), "--json"], self.root)
            gaps = _extract_gaps(out)
            if gaps == 0:
                self.add("hooks", "wiring", PASS, "verify_harness_wiring gaps==0")
            elif gaps is None:
                self.add("hooks", "wiring", WARN, "wiring verdict inconclusive")
            else:
                self.add("hooks", "wiring", FAIL, f"wiring gaps={gaps}")
        else:
            self.add("hooks", "wiring", WARN, "verify_harness_wiring.py missing")

    # ── integrity ──────────────────────────────────────────────────────────
    def check_integrity(self) -> None:
        cs = self.root / "scripts" / "harness_template_checksum.py"
        if not cs.exists():
            self.add("integrity", "checksum", WARN, "harness_template_checksum.py missing")
            return
        rc, out = run(["python3", str(cs), "--verify"], self.root)
        self.add("integrity", "checksum", PASS if rc == 0 else FAIL,
                 "checksum verify OK" if rc == 0 else "checksum verify FAILED (missing/changed/uncontrolled)")

    # ── project management ───────────────────────────────────────────────────
    def check_project_management(self, ssot: dict | None) -> None:
        pm = (ssot or {}).get("project_management") if ssot else None
        if not pm:
            self.add("project_management", "section", WARN, "no project_management in SSOT (or SSOT unread)")
            return
        master = self.root / pm.get("master_dir", "projects/all-projects")
        lanes = pm.get("lanes", [])
        missing = [l["folder"] for l in lanes if not (self.root / l["folder"]).is_dir()]
        if master.is_dir() and not missing:
            self.add("project_management", "scaffold", PASS,
                     f"all-projects + {len(lanes)} lanes present")
        else:
            why = ([] if master.is_dir() else ["all-projects"]) + missing
            self.add("project_management", "scaffold", FAIL,
                     f"missing {why} → project_status_symlinks.py init")
        # lanes.json must agree with the SSOT (no drift)
        lanes_json = self.root / ".agents/skills/1-project-create-launch/lanes.json"
        if lanes_json.exists():
            try:
                lj = json.loads(lanes_json.read_text(encoding="utf-8"))
                lj_ids = [x["id"] for x in lj.get("lanes", [])]
                ssot_ids = [l["id"] for l in lanes]
                self.add("project_management", "lanes-sync", PASS if lj_ids == ssot_ids else FAIL,
                         "lanes.json == SSOT lanes" if lj_ids == ssot_ids
                         else f"DRIFT: lanes.json {lj_ids} != SSOT {ssot_ids}")
            except (json.JSONDecodeError, KeyError):
                self.add("project_management", "lanes-sync", WARN, "lanes.json unreadable")
        else:
            self.add("project_management", "lanes-sync", WARN, "lanes.json missing")
        # the projects mover's own doctor
        mover = self.root / pm.get("mover", ".agents/skills/1-project-create-launch/scripts/project_status_symlinks.py")
        if mover.exists() and master.is_dir():
            rc, _ = run(["python3", str(mover), "doctor"], self.root)
            self.add("project_management", "pm-doctor", PASS if rc == 0 else FAIL,
                     "projects doctor clean" if rc == 0 else "projects doctor found issues (rc!=0)")
        else:
            self.add("project_management", "pm-doctor", WARN, "mover or scaffold absent")

    # ── local only (beads/dolt) ───────────────────────────────────────────────
    def check_local_only(self, ssot: dict | None) -> None:
        lo = (ssot or {}).get("local_only", {}).get("beads_dolt") if ssot else None
        paths = (lo or {}).get("paths", [".beads/", ".dolt/"])
        not_ignored = []
        for p in paths:
            # Probe a path INSIDE the dir so a dir-only pattern (`.dolt/`) matches even
            # when the dir does not exist yet (git can't infer dir-ness from a bare name).
            probe = p.rstrip("/") + "/.probe"
            rc, _ = run(["git", "check-ignore", probe], self.root)
            if rc != 0:
                not_ignored.append(p)
        self.add("local_only", "ignored", PASS if not not_ignored else FAIL,
                 "all local-only paths gitignored" if not not_ignored else f"NOT gitignored: {not_ignored}")
        rc, out = run(["git", "ls-files", ".beads"], self.root)
        tracked = bool(out.strip())
        self.add("local_only", "untracked", PASS if not tracked else FAIL,
                 ".beads not tracked (partners never inherit it)" if not tracked
                 else ".beads IS tracked in git → git rm -r --cached .beads")

    # ── skills index ─────────────────────────────────────────────────────────
    def check_skills(self, ssot: dict | None) -> None:
        idx = (ssot or {}).get("skills_index") if ssot else None
        if not idx:
            self.add("skills", "present", WARN, "no skills_index in SSOT (or SSOT unread)")
            return
        paths: list[str] = []
        for v in idx.values():
            paths.extend(v if isinstance(v, list) else [v])
        missing = [p for p in paths if not (self.root / p).exists()]
        self.add("skills", "present", PASS if not missing else FAIL,
                 f"all {len(paths)} skills_index paths exist" if not missing else f"missing: {missing}")

    def run_all(self) -> None:
        ssot, reason = load_ssot(self.root)
        if ssot is None:
            self.add("ssot", "read", WARN, reason or "SSOT unreadable")
        self.check_toolchain(ssot)
        self.check_hooks()
        self.check_integrity()
        self.check_project_management(ssot)
        self.check_local_only(ssot)
        self.check_skills(ssot)


def _importable(mod: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(mod) is not None


def _extract_gaps(out: str):
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line).get("gaps")
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(out).get("gaps")
    except json.JSONDecodeError:
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify the harness came up, by harness-workflow.yaml")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN also fails (CI gate)")
    args = ap.parse_args(argv)

    root = find_root()
    doc = Doctor(root)
    doc.run_all()

    n_pass = sum(1 for r in doc.results if r["status"] == PASS)
    n_warn = sum(1 for r in doc.results if r["status"] == WARN)
    n_fail = sum(1 for r in doc.results if r["status"] == FAIL)

    if args.json:
        print(json.dumps({"root": str(root), "pass": n_pass, "warn": n_warn, "fail": n_fail,
                          "results": doc.results}, ensure_ascii=False, indent=2))
    else:
        icon = {PASS: "✅", WARN: "⚠️ ", FAIL: "❌"}
        print(f"\nharness doctor — {root.name}  (reads harness-workflow.yaml)")
        print("─" * 64)
        cur = None
        for r in doc.results:
            if r["section"] != cur:
                cur = r["section"]
                print(f"[{cur}]")
            print(f"  {icon[r['status']]} {r['check']:13} {r['detail']}")
        print("─" * 64)
        verdict = "HEALTHY" if n_fail == 0 and n_warn == 0 else ("DEGRADED (toolchain pending)" if n_fail == 0 else "BROKEN")
        print(f"{n_pass} PASS · {n_warn} WARN · {n_fail} FAIL → {verdict}\n")

    if n_fail:
        return 1
    if args.strict and n_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
