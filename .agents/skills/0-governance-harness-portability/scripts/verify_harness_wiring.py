#!/usr/bin/env python3
r"""verify_harness_wiring.py — self-verifier of the governance harness copy-kit (Standard 0.3).

WHY (RCA 2026-06-07): the copy-kit (§5 of Standard 0.3) was a HAND-MAINTAINED list of
hooks/skills. Falsification found 3 hooks documented as "live mechanical enforcement"
that were NOT registered in settings.json (docs_client_doc_gate, pr_bead_jtbd_ref_check,
root_new_entry_gate) → Pillar B/A silently non-enforcing; and 4 "detachable" skills with
no skill.yaml. A hand-maintained table cannot detect its own drift. This verifier makes
the bundle SELF-VERIFYING: a client copies the harness, runs this, and gets PASS or the
exact gaps — no drift, no trust.

WHAT it checks against harness-manifest.json (the SSOT):
  H1 hook file exists under hooks_dir
  H2 each hook's `register` target is satisfied in settings.json
     (a block under that event whose matcher covers the tool contains the hook command)
  H3 each hook `depends_on` path exists (fail-open hooks silently no-op if a dep is missing)
  H4 (optional --smoke) hook is fail-open: garbage stdin -> exit 0
  S1 each manifest skill dir exists
  S2 code-skill -> requires skill.yaml + scripts/ + tests/
  S3 knowledge-skill -> requires SKILL.md; if skill.yaml present, detachable must be true|partial
  P1 each affordance/config script path exists

Universal: no client/project hardcode; everything is manifest-driven and path-relative to
--repo-root. Stdlib only (json/argparse/pathlib/subprocess/re) -> detachable: true.

Exit codes:
  0 — all PASS (no GAP findings)
  1 — >=1 GAP finding
  2 — usage/IO error (manifest or settings unreadable)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PASS, GAP, WARN = "PASS", "GAP", "WARN"


class Finding:
    __slots__ = ("component", "check", "status", "detail")

    def __init__(self, component: str, check: str, status: str, detail: str):
        self.component = component
        self.check = check
        self.status = status
        self.detail = detail

    def as_dict(self) -> dict:
        return {"component": self.component, "check": self.check, "status": self.status, "detail": self.detail}


def _strip_jsonc(text: str) -> str:
    """settings.json is strict JSON, but tolerate // and /* */ if a teammate added them."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|\s)//[^\n]*", r"\1", text)
    return text


def load_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_strip_jsonc(raw))


def matcher_covers(matcher: str, tool: str) -> bool:
    """A settings matcher covers a tool if tool is one of its |-alternatives, or it is a
    catch-all ('' / '*'), or the requirement itself is catch-all ('*')."""
    if tool == "*":
        return True
    m = (matcher or "").strip()
    if m in ("", "*"):
        return True
    return tool in [p.strip() for p in m.split("|")]


def collect_registrations(settings: dict) -> list[tuple[str, str, str]]:
    """Return [(event, matcher, command), ...] across all hook blocks of a settings dict."""
    out: list[tuple[str, str, str]] = []
    for event, blocks in (settings.get("hooks") or {}).items():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            matcher = block.get("matcher", "")
            for h in block.get("hooks", []) or []:
                cmd = h.get("command", "")
                out.append((event, matcher, cmd))
    return out


def hook_register_satisfied(regs, hook_file: str, event: str, tools: list[str]) -> tuple[bool, str]:
    """True if some registration block under `event` references hook_file and its matcher
    covers ALL required tools (tools is the AND-set for one register target)."""
    # Anchor on basename with a boundary so 'gate.py' does NOT match 'branch_gate.py'
    # (RCA: code-review M1 — bare `name in cmd` substring gave false-positive registration).
    name_re = re.compile(rf"(?:^|[/\s'\"]){re.escape(hook_file)}(?:$|[\s'\"])")
    candidates = [(ev, mt) for (ev, mt, cmd) in regs if ev == event and name_re.search(cmd)]
    if not candidates:
        return False, f"not registered under {event}"
    for tool in tools:
        if not any(matcher_covers(mt, tool) for (_ev, mt) in candidates):
            seen = ", ".join(sorted({mt or "<empty>" for _e, mt in candidates}))
            return False, f"registered under {event} but no matcher covers tool '{tool}' (matchers: {seen})"
    return True, f"{event}:{'|'.join(tools)}"


def smoke_fail_open(hook_path: Path) -> tuple[bool, str]:
    try:
        p = subprocess.run(
            [sys.executable, str(hook_path)],
            input="not-json-garbage",
            text=True,
            capture_output=True,
            timeout=30,
        )
        return (p.returncode == 0, f"exit={p.returncode}")
    except Exception as e:  # noqa: BLE001 — verifier must never crash on a hook
        return False, f"error: {e}"


def verify(repo_root: Path, manifest_path: Path, settings_path: Path, smoke: bool) -> list[Finding]:
    findings: list[Finding] = []
    manifest = load_json(manifest_path)
    paths = manifest.get("paths", {})
    hooks_dir = repo_root / paths.get("hooks_dir", ".claude/hooks")
    skills_dir = repo_root / paths.get("skills_dir", ".agents/skills")

    settings = load_json(settings_path) if settings_path.exists() else {}
    regs = collect_registrations(settings)
    # merge settings.local.json if present (teammate-local registrations are valid too)
    local_path = repo_root / paths.get("settings_local", ".claude/settings.local.json")
    if local_path.exists():
        try:
            regs += collect_registrations(load_json(local_path))
        except Exception as e:  # noqa: BLE001
            print(f"WARN: {local_path} unparseable, skipping local registrations ({e})", file=sys.stderr)

    # --- Hooks ---
    for hk in manifest.get("hooks", []):
        f = hk["file"]
        comp = f"hook:{f}"
        hook_path = hooks_dir / f
        if not hook_path.exists():
            findings.append(Finding(comp, "H1-exists", GAP, f"missing file {hook_path}"))
            continue
        findings.append(Finding(comp, "H1-exists", PASS, "file present"))
        # H2 registration (each register target is an AND-set of tools; all targets must pass)
        for target in hk.get("register", []):
            ev = target["event"]
            # Stop / SessionStart / SessionEnd / UserPromptSubmit have no per-tool matcher —
            # `tools` is optional; empty list = "registered under event" is sufficient.
            tools = target.get("tools", [])
            ok, detail = hook_register_satisfied(regs, f, ev, tools)
            findings.append(Finding(comp, f"H2-registered[{ev}:{'|'.join(tools)}]", PASS if ok else GAP, detail))
        # H3 deps exist
        for dep in hk.get("depends_on", []):
            dep_path = repo_root / dep
            findings.append(
                Finding(
                    comp,
                    "H3-dep",
                    PASS if dep_path.exists() else GAP,
                    f"{'present' if dep_path.exists() else 'MISSING'}: {dep}",
                )
            )
        # H4 fail-open smoke
        if smoke:
            ok, detail = smoke_fail_open(hook_path)
            findings.append(Finding(comp, "H4-fail-open", PASS if ok else WARN, detail))

    # --- Skills ---
    for sk in manifest.get("skills", []):
        name = sk["name"]
        kind = sk.get("kind", "knowledge")
        comp = f"skill:{name}"
        sdir = skills_dir / name
        if not sdir.is_dir():
            findings.append(Finding(comp, "S1-exists", GAP, f"missing dir {sdir}"))
            continue
        findings.append(Finding(comp, "S1-exists", PASS, f"kind={kind}"))
        yaml_path = sdir / "skill.yaml"
        if kind == "code":
            findings.append(
                Finding(
                    comp,
                    "S2-skill.yaml",
                    PASS if yaml_path.exists() else GAP,
                    "present" if yaml_path.exists() else "code-skill MUST have skill.yaml",
                )
            )
            findings.append(
                Finding(
                    comp,
                    "S2-scripts",
                    PASS if (sdir / "scripts").is_dir() else GAP,
                    "present" if (sdir / "scripts").is_dir() else "code-skill MUST have scripts/",
                )
            )
            findings.append(
                Finding(
                    comp,
                    "S2-tests",
                    PASS if (sdir / "tests").is_dir() else GAP,
                    "present" if (sdir / "tests").is_dir() else "code-skill MUST have tests/",
                )
            )
        else:  # knowledge
            has_md = (sdir / "SKILL.md").exists()
            findings.append(
                Finding(
                    comp,
                    "S3-SKILL.md",
                    PASS if has_md else GAP,
                    "present" if has_md else "knowledge-skill MUST have SKILL.md",
                )
            )
            if yaml_path.exists():
                txt = yaml_path.read_text(encoding="utf-8")
                m = re.search(r"^\s*detachable:\s*(\w+)", txt, re.M)
                lvl = m.group(1) if m else "?"
                ok = lvl in ("true", "partial")
                findings.append(Finding(comp, "S3-detachable", PASS if ok else WARN, f"detachable: {lvl}"))

    # --- Scripts / config ---
    for sc in manifest.get("scripts", []):
        f = sc["file"]
        p = repo_root / f
        findings.append(
            Finding(
                f"script:{f}", "P1-exists", PASS if p.exists() else GAP, "present" if p.exists() else f"MISSING {f}"
            )
        )

    return findings


def render_markdown(findings: list[Finding]) -> str:
    n_gap = sum(1 for x in findings if x.status == GAP)
    n_warn = sum(1 for x in findings if x.status == WARN)
    n_pass = sum(1 for x in findings if x.status == PASS)
    icon = {PASS: "✅", GAP: "🔴", WARN: "⚠️"}
    lines = [
        f"# Harness wiring verification — {n_pass} PASS / {n_warn} WARN / {n_gap} GAP",
        "",
        "> Scope: this verifies **wiring** (hook files present + registered on the right matcher + "
        "deps present + skills declared). PASS means a hook is _reachable_, NOT that it _blocks_ a "
        "violation at runtime. Runtime effectiveness = each hook's own bundled tests + the live "
        "`PreToolUse` block you observe in a real session.",
        "",
        "| Status | Component | Check | Detail |",
        "|---|---|---|---|",
    ]
    # gaps and warns first (most actionable)
    order = {GAP: 0, WARN: 1, PASS: 2}
    for x in sorted(findings, key=lambda f: (order[f.status], f.component, f.check)):
        lines.append(f"| {icon[x.status]} {x.status} | `{x.component}` | {x.check} | {x.detail} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve()
    default_manifest = here.parent.parent / "harness-manifest.json"
    ap = argparse.ArgumentParser(description="Verify the governance harness is fully wired (Standard 0.3).")
    ap.add_argument("--repo-root", default=".", help="repo root to verify (default: cwd)")
    ap.add_argument("--manifest", default=str(default_manifest), help="path to harness-manifest.json")
    ap.add_argument(
        "--settings", default=None, help="path to .claude/settings.json (default: <repo-root>/.claude/settings.json)"
    )
    ap.add_argument("--smoke", action="store_true", help="also run fail-open smoke per hook (slower)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    settings_path = Path(args.settings).resolve() if args.settings else repo_root / ".claude" / "settings.json"

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    try:
        findings = verify(repo_root, manifest_path, settings_path, smoke=args.smoke)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: verification failed: {e}", file=sys.stderr)
        return 2

    if args.json:
        n_gap = sum(1 for x in findings if x.status == GAP)
        print(json.dumps({"gaps": n_gap, "findings": [x.as_dict() for x in findings]}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(findings))

    return 1 if any(x.status == GAP for x in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
