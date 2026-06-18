#!/usr/bin/env python3
"""harness_template_checksum.py — контроль ЦЕЛОСТНОСТИ и ПОЛНОТЫ harness-сборки.

Зачем: после зеркала (mirror) надо гарантировать, что в target-репо приехала ПОЛНАЯ
и НЕИСКАЖЁННАЯ обвязка — и что ни один файл harness не «выпал из-под контроля»
(RCA <client> 2026-06-16: часть обвязки была вне зеркала и замёрзла на марте).

Манифест self-describing: хранит СПИСОК КОРНЕЙ (roots) + sha256 каждого файла под ними.
  generate → обходит roots, пишет .harness-checksums.json.
  verify   → заново обходит ТЕ ЖЕ roots и сравнивает с манифестом:
     • missing      — файл есть в манифесте, нет на диске           → FAIL
     • changed      — sha256 не совпал                              → FAIL
     • uncontrolled — файл под root есть на диске, но НЕ в манифесте → FAIL (полнота!)
  exit 0 только когда всё совпало. --strict делает то же (для CI единообразия).

Это и есть «build guarantee»: сборка считается воспроизведённой ТОЛЬКО при verify==0.
Stdlib-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = ".harness-checksums.json"

# Корни harness-footprint в target/template-репо (bounded — НЕ весь canonical).
DEFAULT_ROOTS = [
    ".claude/hooks",
    ".claude/settings.json",
    ".agents/skills",
    ".agents/agents",
    "harness-workflow.yaml",
    "scripts/harness_bootstrap.py",
    "scripts/harness_template_checksum.py",
]

EXCLUDE_PARTS = {"__pycache__", ".pytest_cache", "node_modules", ".git", ".beads"}
EXCLUDE_SUFFIX = {".pyc", ".parquet", ".csv", ".xlsx"}
EXCLUDE_NAMES = {".DS_Store"}


def _included(p: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in p.parts):
        return False
    if p.name in EXCLUDE_NAMES or p.suffix in EXCLUDE_SUFFIX:
        return False
    return True


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(root_repo: Path, roots: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    for r in roots:
        base = root_repo / r
        if base.is_file():
            if _included(base):
                files[r] = _sha256(base)
        elif base.is_dir():
            for f in sorted(base.rglob("*")):
                if f.is_file() and not f.is_symlink() and _included(f):
                    files[str(f.relative_to(root_repo))] = _sha256(f)
    return files


def generate(root_repo: Path, roots: list[str]) -> int:
    files = walk(root_repo, roots)
    manifest = {
        "schema": 1,
        "generated_for": root_repo.name,
        "roots": roots,
        "n_files": len(files),
        "files": files,
    }
    out = root_repo / MANIFEST
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"generate: {len(files)} файлов под {len(roots)} корнями → {MANIFEST}")
    return 0


def verify(root_repo: Path) -> int:
    mpath = root_repo / MANIFEST
    if not mpath.exists():
        print(f"verify: {MANIFEST} отсутствует — сборка НЕ зафиксирована (запусти --generate)")
        return 2
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    roots = manifest.get("roots", DEFAULT_ROOTS)
    expected: dict[str, str] = manifest.get("files", {})
    current = walk(root_repo, roots)

    missing = sorted(set(expected) - set(current))
    uncontrolled = sorted(set(current) - set(expected))
    changed = sorted(f for f in (set(expected) & set(current)) if expected[f] != current[f])

    ok = not (missing or uncontrolled or changed)
    print(f"verify: roots={len(roots)} expected={len(expected)} current={len(current)}")
    for label, items in (("MISSING", missing), ("UNCONTROLLED", uncontrolled), ("CHANGED", changed)):
        for f in items[:50]:
            print(f"  {label:<12} {f}")
        if len(items) > 50:
            print(f"  {label:<12} … +{len(items) - 50} ещё")
    if ok:
        print(f"verify: OK — {len(current)} файлов harness под контролем, целостность подтверждена")
        return 0
    print(f"verify: FAIL — missing={len(missing)} uncontrolled={len(uncontrolled)} changed={len(changed)}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generate", action="store_true", help="пересоздать манифест контрольных сумм")
    ap.add_argument("--verify", action="store_true", help="сверить рабочее дерево с манифестом")
    ap.add_argument("--strict", action="store_true", help="(совместимость; verify и так возвращает !=0 при провале)")
    ap.add_argument("--root", help="repo root (default: cwd-up)")
    ap.add_argument("--roots", nargs="*", help="переопределить список корней при --generate")
    args = ap.parse_args()

    if args.root:
        root_repo = Path(args.root).resolve()
    else:
        root_repo = Path.cwd()
        for _ in range(8):
            if (root_repo / ".agents").exists() or (root_repo / ".claude").exists():
                break
            if root_repo.parent == root_repo:
                break
            root_repo = root_repo.parent

    if args.generate:
        return generate(root_repo, args.roots or DEFAULT_ROOTS)
    if args.verify:
        return verify(root_repo)
    ap.error("нужен --generate или --verify")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
