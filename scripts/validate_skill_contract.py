#!/usr/bin/env python3
"""
Validate skill contract compliance across all SKILL.md files.
Checks: frontmatter, name, description, reasoning log, JTBD, hard fail,
owner value, input/output/outcome contract, self-falsification gate.

Standard 4.8 §B Contract requires every Tier-A skill body to contain:
JTBD ("Hired for"), explicit input + output + outcome checklists, and a
Self-falsification gate that runs `2-hypothesis-gap-falsification` on the
hypothesis "this skill did its job well" after execution. C10/C11 are
soft (WARN) by default and hard under --strict — same progressive-rollout
design as C06/C08, so adding them does not turn main red on legacy skills.

Usage:
    python3 scripts/validate_skill_contract.py [--strict] [--fix] [--json]
"""

from __future__ import annotations  # Python 3.9 compat for `Path | None` PEP 604 syntax

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / ".agents" / "skills"

CHECKS = {
    "C01_frontmatter": "Has YAML frontmatter (--- block)",
    "C02_name": "Has name field in frontmatter",
    "C03_description": "Has description field in frontmatter",
    "C04_reasoning_log": "Has Reasoning Log Protocol section",
    "C05_references": "Has related skills references",
    "C06_jtbd": "Has Hired for JTBD / JTBD section",
    "C07_hard_fail": "Has Hard fail / Запрещено / Forbidden conditions",
    "C08_owner_value": "Has Owner value or value tracking mention",
    "C09_no_empty": "SKILL.md is not empty / stub (<100 chars)",
    "C10_io_contract": "Has explicit input + output + outcome checklists (Std 4.8 §B)",
    "C11_self_falsification": "Has Self-falsification gate running 2-hypothesis-gap-falsification",
    "C12_workflow": "Has explicit ## Workflow / ## Pipeline / Воркфлоу section (Std 4.8 §B)",
    "C13_credentials_ref": "If skill calls external API → references credentials_manager / Credentials SSOT (conditional)",
    "C14_source_refs": "If skill wraps code (scripts/ dir) → cites canonical source files / Канонические источники (conditional)",
    "C15_description_quality": "description is WHEN-triggers (JTBD), not a WHAT-summary (Std 4.8 / 0-skills-self-improvement)",
}

# C15 description-quality heuristic. A good skill `description` says WHEN to fire
# (Jobs-To-Be-Done triggers — «use when …» / «когда …») so the model can route to
# it. A WHAT-summary («Ensures the tree is clean») describes the skill instead of
# its trigger and routes poorly. Heuristic: flag descriptions that START with a
# WHAT-verb AND contain NO WHEN/trigger token. Tuned against the live corpus to a
# <2% false-positive rate (1/345 at landing) — see scripts/tests. WARN-level only
# (heuristic, false-positives possible); override SKILL_DESC_QUALITY_ACK.
_C15_WHEN_TOKENS = re.compile(
    r"\b(use\s+when|use\s+before|use\s+for|use\s+to|when\s|before\s|after\s|whenever|"
    r"trigger|триггер|когда|перед\s|используй)\b",
    re.I,
)
_C15_WHAT_START = re.compile(
    r"^\s*(ensures|guides|manages|provides|handles|orchestrates|validates|generates|"
    r"creates|runs|merges|checks|audits|evaluates|wraps|builds|computes|describes|"
    r"summari[sz]es|суммирует|описывает|обеспечивает|управляет|предоставляет|"
    r"генерирует|создаёт|создает|проверяет|анализирует|выполняет)\b",
    re.I,
)


def _extract_description(content: str) -> str:
    """Extract the full `description:` value, including YAML block scalars
    (`description: |` / `>` with indented continuation lines). 20 of 345 skills
    use block scalars; a same-line-only regex would miss them entirely."""
    m = re.match(r"---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return ""
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        mm = re.match(r"^description:\s*(.*)$", line)
        if not mm:
            continue
        val = mm.group(1).strip()
        if val in ("|", ">", "|-", ">-", "|+", ">+", ""):
            buf = []
            for cont in lines[i + 1 :]:
                if cont.strip() == "":
                    buf.append("")
                    continue
                if re.match(r"^\s", cont):  # indented → part of block scalar
                    buf.append(cont.strip())
                else:
                    break  # dedented → next frontmatter key
            return " ".join(x for x in buf if x).strip().strip("\"'")
        return val.strip("\"'")
    return ""


# External-API signal words: if a skill body mentions any of these, it almost
# certainly needs a credential and must reference the SSOT (C13). Pure-reasoning
# skills (no external call) are exempt — we do NOT validate scenarios that
# cannot happen (AGENTS.md anti-over-validation).
_EXTERNAL_API_SIGNALS = (
    "rick.ai/",
    "analyticsadmin",
    "googleapis",
    "supabase",
    "amocrm",
    "bitrix24",
    "telegram",
    "google_sheets",
    "google-sheets",
    "google_drive",
    "bigquery",
    "session_cookie",
    "api_key",
    "access_token",
    "oauth",
    "stripe",
    "n8n",
    "flow.rick.ai",
    "x-auth-token",
    "rick_session",
    "curl ",
    "requests.",
    "aiohttp",
)


def validate_skill(skill_path: Path) -> dict:
    content = skill_path.read_text(encoding="utf-8")
    results = {}

    # C01: frontmatter
    results["C01_frontmatter"] = content.startswith("---") and content.count("---") >= 2

    # C02: name in frontmatter
    fm_match = re.match(r"---\s*\n(.*?)\n---", content, re.DOTALL)
    fm = fm_match.group(1) if fm_match else ""
    results["C02_name"] = "name:" in fm

    # C03: description
    results["C03_description"] = "description:" in fm

    # C04: reasoning log
    results["C04_reasoning_log"] = "Reasoning Log Protocol" in content

    # C05: related skills references
    results["C05_references"] = "Связанные скилы" in content or "Related skills" in content

    # C06: JTBD
    results["C06_jtbd"] = "JTBD" in content or "Hired for" in content

    # C07: hard fail
    results["C07_hard_fail"] = any(k in content for k in ["Hard fail", "Запрещено", "Forbidden"])

    # C08: owner value
    cl = content.lower()
    results["C08_owner_value"] = any(
        k in cl for k in ["owner value", "owner_value", "ценность для owner", "value_per_touch"]
    )

    # C09: not empty
    results["C09_no_empty"] = len(content.strip()) >= 100

    # C10: explicit input + output + outcome contract.
    # Accept section headers OR mandatory-delivery-style checklist labels in
    # RU/EN. All three concepts must be present for the check to pass.
    has_input = bool(
        re.search(r"^#+.*\b(input|вход|обязательн\w*\s+(данны|вход))", content, re.I | re.M)
        or re.search(r"input\s*checklist|входн\w*\s+чеклист", content, re.I)
    )
    has_output = bool(
        re.search(r"^#+.*\b(output|выход|результат)\b", content, re.I | re.M)
        or re.search(r"output\s*checklist|выходн\w*\s+чеклист|expected\s+output", content, re.I)
    )
    has_outcome = bool(
        re.search(r"^#+.*\b(outcome|исход|выгод|owner\s+benefit)", content, re.I | re.M)
        or re.search(r"outcome\s*checklist|outcome\s+ladder|so[\s-]?what", content, re.I)
    )
    results["C10_io_contract"] = has_input and has_output and has_outcome

    # C11: self-falsification gate — skill must, after execution, falsify the
    # hypothesis "this skill did its job well" via 2-hypothesis-gap-falsification.
    results["C11_self_falsification"] = bool(
        "2-hypothesis-gap-falsification" in content
        or re.search(
            r"^#+.*(self[\s-]?falsif|self[\s-]?check\s+gate|фальсифи\w*\s+гипотез\w*\s+скил)",
            content,
            re.I | re.M,
        )
    )

    # C12: explicit Workflow / Pipeline section (the "how", Std 4.8 §B body).
    results["C12_workflow"] = bool(
        re.search(r"^#+\s*.*\b(workflow|pipeline|воркфлоу|процедура|steps?|шаги|этапы)\b", content, re.I | re.M)
    )

    # C13: credentials reference — CONDITIONAL. Only required if the skill body
    # signals an external API call. Pure-reasoning skills are exempt.
    needs_creds = any(sig in cl for sig in _EXTERNAL_API_SIGNALS)
    has_creds_ref = (
        "credentials_manager" in cl
        or "credentials ssot" in cl
        or "0-keychain-audit" in content
        or "credential SSOT" in content
    )
    results["C13_credentials_ref"] = (not needs_creds) or has_creds_ref

    # C14: canonical source refs — CONDITIONAL. Only required if the skill ships
    # a scripts/ dir (wraps code) — then it must cite what code/sources it wraps.
    has_scripts = (skill_path.parent / "scripts").is_dir()
    has_source_refs = bool(
        "Канонические источники" in content
        or "Canonical sources" in content
        or re.search(r"`[^`]+\.(py|ts|tsx|sql|js)`|\]\([^)]+\.(py|ts|tsx|sql|js)", content)
    )
    results["C14_source_refs"] = (not has_scripts) or has_source_refs

    # C15: description quality — WHEN-triggers, not WHAT-summary. WARN-level
    # (heuristic). Pass if: no description (other checks own that), OR not a
    # WHAT-start, OR contains a WHEN/trigger token. Override via env so a
    # legitimately WHAT-leaning description can opt out without code change.
    if os.environ.get("SKILL_DESC_QUALITY_ACK"):
        results["C15_description_quality"] = True
    else:
        desc = _extract_description(content)
        if not desc:
            results["C15_description_quality"] = True
        else:
            starts_what = bool(_C15_WHAT_START.match(desc))
            has_when = bool(_C15_WHEN_TOKENS.search(desc))
            results["C15_description_quality"] = (not starts_what) or has_when

    return results


def _changed_skill_files() -> list[Path]:
    """Skill dirs changed vs origin/main (or staged) — the progressive gate
    scope: legacy 192 stay tracked (full-repo run = soft), but any NEW or
    TOUCHED skill must be fully canon (changed-only run = hard, blocking)."""
    import subprocess

    refs = ["origin/main...HEAD", "--cached", "HEAD"]
    paths: set[Path] = set()
    for ref in refs:
        try:
            args = ["git", "diff", "--name-only"] + (ref.split() if " " in ref else [ref])
            out = subprocess.run(args, capture_output=True, text=True, timeout=20)
            for line in out.stdout.splitlines():
                md = _skill_md_for(line)
                if md is not None:
                    paths.add(md)
        except Exception:
            continue
    return sorted(paths)


def _skill_md_for(path_str: str) -> Path | None:
    """Map ANY changed file inside .agents/skills/<skill>/ (SKILL.md OR
    scripts/ OR tests/ OR references/ OR assets/) to that skill's SKILL.md.

    RCA 2026-05-18 (G2): the gate previously only triggered on SKILL.md, so
    editing a skill's scripts/*.py heavily while leaving a non-canon SKILL.md
    untouched BYPASSED the canon check entirely. "touch = canon" must mean
    touching ANY file in the skill dir → its SKILL.md is re-validated.
    """
    norm = path_str
    while norm.startswith("./"):
        norm = norm[2:]
    idx = norm.find(".agents/skills/")
    if idx == -1:
        return None
    norm = norm[idx:]
    parts = norm.split("/")
    if len(parts) < 3:  # .agents/skills/<skill>/...
        return None
    skill_md = SKILLS_DIR / parts[2] / "SKILL.md"
    return skill_md if skill_md.exists() else None


def main():
    strict = "--strict" in sys.argv
    as_json = "--json" in sys.argv
    changed_only = "--changed-only" in sys.argv
    all_results = []
    summary = {"total": 0, "passed": 0, "failed": 0, "warnings": 0}

    if changed_only:
        # Explicit paths after the flag, else auto-detect changed skills.
        idx = sys.argv.index("--changed-only")
        explicit = []
        for a in sys.argv[idx + 1 :]:
            if a.startswith("-"):
                continue
            md = _skill_md_for(a) or (Path(a) if a.endswith("SKILL.md") and Path(a).exists() else None)
            if md is not None:
                explicit.append(md)
        explicit = sorted(set(explicit))
        targets = explicit or _changed_skill_files()
        if not targets:
            print("skill-contract changed-only: no changed SKILL.md — pass")
            return 0
        skill_files = targets
        strict = True  # new/touched skills must be FULLY canon — blocking
    else:
        skill_files = [sd / "SKILL.md" for sd in sorted(SKILLS_DIR.iterdir()) if (sd / "SKILL.md").exists()]

    for sm in skill_files:
        sd = sm.parent
        if sd.name == "_TEMPLATE":
            continue  # the canonical reference template, not a runnable skill
        summary["total"] += 1
        checks = validate_skill(sm)
        fails = [k for k, v in checks.items() if not v]

        # C06/C08/C10/C11/C12/C13/C14 soft in full-repo (progressive rollout:
        # 192 legacy tracked, not main-red); ALL hard in --changed-only/--strict
        # so every NEW or TOUCHED skill ships fully canon ("touch = canon").
        SOFT = (
            "C06_jtbd",
            "C08_owner_value",
            "C10_io_contract",
            "C11_self_falsification",
            "C12_workflow",
            "C13_credentials_ref",
            "C14_source_refs",
        )
        # C15 is a heuristic (false-positives possible) → ALWAYS WARN, never a
        # hard block even under --strict / --changed-only. Override:
        # SKILL_DESC_QUALITY_ACK. This keeps the WHEN-not-WHAT rule mechanical
        # (surfaced on every touched skill) without blocking commits on a guess.
        ALWAYS_SOFT = ("C15_description_quality",)
        hard_fails = [f for f in fails if f not in SOFT and f not in ALWAYS_SOFT]
        soft_fails = [f for f in fails if f in SOFT or f in ALWAYS_SOFT]

        # Under --strict/--changed-only, SOFT checks become hard — but
        # ALWAYS_SOFT (C15 heuristic) stays WARN even then.
        strict_blocking_soft = [f for f in soft_fails if f not in ALWAYS_SOFT]

        status = "PASS"
        if hard_fails or (strict and strict_blocking_soft):
            status = "FAIL"
            summary["failed"] += 1
        elif soft_fails:
            status = "WARN"
            summary["warnings"] += 1
        else:
            summary["passed"] += 1

        all_results.append(
            {
                "skill": sd.name,
                "status": status,
                "checks": checks,
                "fails": fails,
            }
        )

    if as_json:
        print(json.dumps({"summary": summary, "results": all_results}, indent=2, ensure_ascii=False))
        return 1 if (changed_only and summary["failed"]) else 0

    print(f"Skill Contract Validation — {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M UTC')}")
    print(f"{'=' * 65}")
    print(
        f"Total: {summary['total']} | Passed: {summary['passed']} | "
        f"Warnings: {summary['warnings']} | Failed: {summary['failed']}"
    )
    print(f"Mode: {'STRICT' if strict else 'NORMAL'}")
    print(f"{'=' * 65}")

    for r in all_results:
        if r["status"] != "PASS":
            print(f"  [{r['status']}] {r['skill']}: {', '.join(r['fails'])}")

    # Save report only for full-repo runs (changed-only must not clobber the
    # repo-wide tracking snapshot with a 1-skill subset).
    if not changed_only:
        rp = Path(__file__).parent / "skill_contract_report.json"
        with open(rp, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "results": all_results}, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {rp}")

    if changed_only and summary["failed"]:
        print(
            f"\n❌ skill-contract BLOCK: {summary['failed']} new/touched skill(s) non-canon.\n"
            f"   Required (Std 4.8 §B): frontmatter+name+description, Reasoning Log Protocol,\n"
            f"   Связанные скилы, JTBD, Hard fail, Input+Output+Outcome checklists, ## Workflow,\n"
            f"   Self-falsification gate (2-hypothesis-gap-falsification); + credentials_manager\n"
            f"   ref if external API; + canonical source file refs if scripts/ dir.\n"
            f"   See: <standard-ref>"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
