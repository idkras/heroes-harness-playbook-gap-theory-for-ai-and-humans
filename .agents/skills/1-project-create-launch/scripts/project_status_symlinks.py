#!/usr/bin/env python3
r"""project_status_symlinks.py — the mechanical mover for the projects/ Kanban.

THE SOURCE OF TRUTH for *where a project is mounted*. Every project folder
physically lives once under `projects/all-projects/<name>/`. Its *status* is
expressed as a single relative symlink in exactly one of the four lane folders:

    projects/
    ├── all-projects/          # SSOT — every project folder lives here, once
    │   └── <name>/            #   <name> == bead-id-bearing branch/worktree basename
    ├── 1. backlog/            # lane id: backlog         (raw, not yet specced)
    ├── 2. dod-n-blocked/      # lane id: dod-n-blocked   (DoD gate / blocked)
    ├── 3. in-progress/        # lane id: in-progress     (design / build / review)
    ├── 4. to-delivery/        # lane id: to-delivery     (handed off, awaiting activation)
    └── 5. verify-and-done/    # lane id: verify-and-done (outcome verified, closed)
    # Folders are numbered for explorer sort order; the CLI uses the short id.

A project is one-to-one with a bead ("Bits Ticket", titled as a JTBD) and with a
worktree/branch. The lane is *derived* from the bead's status+labels (when a
`.beads` db is reachable via `bd`), or from a `.project-status` marker file in the
project folder (the offline fallback so this works in a repo without beads init).

The lane mapping is NOT hardcoded here — it is read from `../lanes.json` (the
declarative SSOT). Add a lane = edit lanes.json; this script derives from it.

Universal: no client/project hardcode. Stdlib only.

Usage:
    project_status_symlinks.py new <name> [--bead ID] [--jtbd TEXT] [--lane LANE]
    project_status_symlinks.py move <name> <lane>
    project_status_symlinks.py sync <name>
    project_status_symlinks.py sync-all
    project_status_symlinks.py board [--json]
    project_status_symlinks.py doctor [--json]

    # lane ids: backlog | dod-n-blocked | in-progress | to-delivery | verify-and-done
    # <name> is the project folder basename (== branch/worktree basename, e.g.
    #        pr-rick-projects-symlink-kanban-7ms7)

Exit codes:
  0 — ok (board/doctor clean, op succeeded)
  1 — operation error (unknown project/lane, broken state)
  2 — usage error
  3 — doctor found inconsistencies (orphan symlink / missing mount / multi-lane)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LANES_JSON = SKILL_DIR / "lanes.json"
STATUS_FILE = ".project-status"   # offline lane marker inside a project folder
META_FILE = ".project-meta.json"  # {name, bead_id, jtbd}


class ProjectError(Exception):
    """A user-facing operation error — printed and turned into exit code 1 by main()."""


def validate_name(name: str) -> str:
    """A project name must be a single safe path segment (no traversal / separators)."""
    if not name or name in (".", "..") or name != Path(name).name:
        raise ProjectError(
            f"invalid project name {name!r}: must be one path segment, no '/' or '..'"
        )
    return name


# ── config ───────────────────────────────────────────────────────────────────
def load_lanes(path: Path = LANES_JSON) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["_lane_ids"] = [lane["id"] for lane in cfg["lanes"]]
    cfg["_folder_by_id"] = {lane["id"]: lane["folder"] for lane in cfg["lanes"]}
    return cfg


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up to the repo root (the nearest ancestor holding .git).

    Override with PROJECTS_REPO_ROOT / CLAUDE_PROJECT_DIR. If the override is set
    but missing, warn and fall through (don't silently scaffold into the wrong tree).
    """
    raw = os.environ.get("PROJECTS_REPO_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR")
    if raw and Path(raw).exists():
        return Path(raw).resolve()
    if raw:
        print(f"warning: repo-root override {raw!r} does not exist — ignoring", file=sys.stderr)
    cur = (start or Path.cwd()).resolve()
    for cand in (cur, *cur.parents):
        if (cand / ".git").exists():
            return cand
    return cur


def projects_dir(cfg: dict, repo_root: Path) -> Path:
    return repo_root / cfg.get("projects_root", "projects")


def master_dir(cfg: dict, repo_root: Path) -> Path:
    return projects_dir(cfg, repo_root) / cfg.get("master_dir", "all-projects")


# ── bead state ───────────────────────────────────────────────────────────────
def _bd_available() -> bool:
    try:
        subprocess.run(["bd", "version"], capture_output=True, timeout=8, check=False)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def bead_state(bead_id: str, repo_root: Path) -> tuple[str, set[str]] | None:
    """Return (status, labels) from `bd show <id> --json`, or None if unavailable."""
    if not bead_id or not _bd_available():
        return None
    try:
        r = subprocess.run(
            ["bd", "show", bead_id, "--json"],
            capture_output=True, text=True, timeout=10, cwd=str(repo_root), check=False,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        data = json.loads(r.stdout)
        if isinstance(data, list):
            data = data[0] if data else {}
        status = str(data.get("status") or "").strip()
        labels = data.get("labels") or data.get("tags") or []
        if isinstance(labels, str):
            labels = [labels]
        return status, {str(x).strip() for x in labels}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, IndexError):
        return None


def resolve_lane_from_bead(status: str, labels: set[str], cfg: dict) -> str:
    """Map a bead status+labels to a lane id using lanes.json (no hardcoded branches).

    Rule: status_overrides win first (blocked->backlog, closed->done); otherwise the
    *furthest-right* lane (latest in lifecycle order) whose bead_status or bead_labels
    matches takes the project — a label like `delivering` bumps an in_progress bead to
    to-delivery; `outcome_realized` bumps it to verify-and-done.
    """
    overrides = cfg.get("status_overrides", {})
    if status in overrides:
        return overrides[status]
    # Normalize Std-4.15 `status:in_review` style labels to bare `in_review` so both spellings match.
    norm = set(labels)
    for lab in labels:
        if lab.startswith("status:"):
            norm.add(lab[len("status:"):])
    # A blocked / dod_blocked label pulls a project back to backlog regardless of any progress label.
    for lab, lane_id in cfg.get("label_overrides", {}).items():
        if lab in norm:
            return lane_id
    best_idx: int | None = None
    for idx, lane in enumerate(cfg["lanes"]):
        if status and status in lane.get("bead_status", []):
            best_idx = idx
        if norm & set(lane.get("bead_labels", [])):
            best_idx = idx
    if best_idx is None:
        return cfg.get("default_lane", cfg["_lane_ids"][0])
    return cfg["lanes"][best_idx]["id"]


def status_is_mappable(status: str, labels: set[str], cfg: dict) -> bool:
    """True if the bead state matches an override / any lane status / any lane label.

    A non-empty status that matches nothing falls to default_lane — doctor flags that
    as 'unmapped' so a silent wrong-lane never reads as a confident placement.
    """
    if not status and not labels:
        return True  # brand-new project, legitimately default
    if status in cfg.get("status_overrides", {}):
        return True
    norm = set(labels)
    for lab in labels:
        if lab.startswith("status:"):
            norm.add(lab[len("status:"):])
    if set(cfg.get("label_overrides", {})) & norm:
        return True
    for lane in cfg["lanes"]:
        if status and status in lane.get("bead_status", []):
            return True
        if norm & set(lane.get("bead_labels", [])):
            return True
    return False


# ── project meta / status ────────────────────────────────────────────────────
def read_meta(proj: Path) -> dict:
    f = proj / META_FILE
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def read_status_file(proj: Path) -> str | None:
    f = proj / STATUS_FILE
    if f.exists():
        val = f.read_text(encoding="utf-8").strip()
        return val or None
    return None


def resolve_lane(name: str, cfg: dict, repo_root: Path) -> str:
    """Resolve a project's lane: bead state (if reachable) > .project-status > default."""
    proj = master_dir(cfg, repo_root) / name
    meta = read_meta(proj)
    bead_id = meta.get("bead_id", "")
    bs = bead_state(bead_id, repo_root)
    if bs is not None:
        return resolve_lane_from_bead(bs[0], bs[1], cfg)
    marker = read_status_file(proj)
    if marker in cfg["_lane_ids"]:
        return marker
    return cfg.get("default_lane", cfg["_lane_ids"][0])


# ── symlink mechanics ────────────────────────────────────────────────────────
def lane_link(cfg: dict, repo_root: Path, lane_id: str, name: str) -> Path:
    return projects_dir(cfg, repo_root) / cfg["_folder_by_id"][lane_id] / name


def clear_links(cfg: dict, repo_root: Path, name: str) -> None:
    """Remove the project's lane entry from every lane folder (idempotent).

    A lane holds only symlinks. A symlink (live or broken) is removed; a stray
    *file* shadow (e.g. a zip-flattened symlink) is also removed so it can't occupy
    the slot; a real *directory* in a lane is someone's data — refuse, don't delete.
    """
    for lane_id in cfg["_lane_ids"]:
        link = lane_link(cfg, repo_root, lane_id, name)
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.is_dir():
            raise ProjectError(
                f"lane {cfg['_folder_by_id'][lane_id]}/ contains a real directory "
                f"'{name}', not a symlink — move its contents into all-projects/ first"
            )


def place_link(cfg: dict, repo_root: Path, lane_id: str, name: str) -> Path:
    """Create the single relative symlink lane/<name> -> ../all-projects/<name>."""
    clear_links(cfg, repo_root, name)
    link = lane_link(cfg, repo_root, lane_id, name)
    link.parent.mkdir(parents=True, exist_ok=True)
    rel_target = Path("..") / cfg.get("master_dir", "all-projects") / name
    link.symlink_to(rel_target)
    return link


# ── commands ─────────────────────────────────────────────────────────────────
def cmd_init(args, cfg: dict, repo_root: Path) -> int:
    """Create the projects/ scaffold: all-projects/ + the numbered lane folders.

    This is the install-time step the harness SSOT requires — the board structure
    must exist before any project is created. Idempotent.
    """
    pd = projects_dir(cfg, repo_root)
    md = master_dir(cfg, repo_root)
    md.mkdir(parents=True, exist_ok=True)
    (md / ".gitkeep").touch()
    created = []
    for lane in cfg["lanes"]:
        folder = pd / lane["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").touch()
        created.append(lane["folder"])
    print(f"projects/ scaffold ready under {pd.relative_to(repo_root)}/")
    print(f"  master:  {cfg.get('master_dir')}/")
    for i, name in enumerate(created, 1):
        print(f"  lane {i}: {name}/")
    return 0


def cmd_new(args, cfg: dict, repo_root: Path) -> int:
    name = validate_name(args.name)
    lane = args.lane or cfg.get("default_lane")
    if lane not in cfg["_lane_ids"]:
        print(f"error: unknown lane {lane!r}; one of {cfg['_lane_ids']}", file=sys.stderr)
        return 2
    proj = master_dir(cfg, repo_root) / name
    if proj.exists():
        print(f"error: project already exists: {proj}", file=sys.stderr)
        return 1
    proj.mkdir(parents=True)
    meta = {"name": name, "bead_id": args.bead or "", "jtbd": args.jtbd or ""}
    (proj / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (proj / STATUS_FILE).write_text(lane + "\n", encoding="utf-8")
    todo = proj / f"{name}.todo.md"
    todo.write_text(_seed_todo(name, args.jtbd or "", args.bead or ""), encoding="utf-8")
    place_link(cfg, repo_root, lane, name)
    print(f"created project {name!r} in lane {lane!r}")
    print(f"  folder: {proj.relative_to(repo_root)}")
    print(f"  todo:   {todo.relative_to(repo_root)}")
    print(f"  mount:  {lane_link(cfg, repo_root, lane, name).relative_to(repo_root)} -> ../all-projects/{name}")
    return 0


def cmd_move(args, cfg: dict, repo_root: Path) -> int:
    name, lane = validate_name(args.name), args.lane
    if lane not in cfg["_lane_ids"]:
        print(f"error: unknown lane {lane!r}; one of {cfg['_lane_ids']}", file=sys.stderr)
        return 2
    proj = master_dir(cfg, repo_root) / name
    if not proj.is_dir():
        print(f"error: no such project: {proj}", file=sys.stderr)
        return 1
    (proj / STATUS_FILE).write_text(lane + "\n", encoding="utf-8")
    meta = read_meta(proj)
    bead_id = meta.get("bead_id", "")
    bs = bead_state(bead_id, repo_root) if bead_id else None
    if bs is not None:
        derived = resolve_lane_from_bead(bs[0], bs[1], cfg)
        if derived != lane:
            print(f"WARNING: bead {bead_id} derives lane {derived!r}, not {lane!r}. "
                  f"`sync`/`sync-all` will REVERT this manual move — update the bead "
                  f"(`bd update {bead_id} ...`) to make {lane!r} stick.", file=sys.stderr)
    place_link(cfg, repo_root, lane, name)
    print(f"moved {name!r} -> {lane!r}")
    return 0


def cmd_sync(args, cfg: dict, repo_root: Path) -> int:
    name = validate_name(args.name)
    proj = master_dir(cfg, repo_root) / name
    if not proj.is_dir():
        print(f"error: no such project: {proj}", file=sys.stderr)
        return 1
    lane = resolve_lane(name, cfg, repo_root)
    place_link(cfg, repo_root, lane, name)
    print(f"synced {name!r} -> {lane!r}")
    return 0


def cmd_link(args, cfg: dict, repo_root: Path) -> int:
    """Attach a bead id to an existing project (the migration path when .beads arrives)."""
    name = validate_name(args.name)
    proj = master_dir(cfg, repo_root) / name
    if not proj.is_dir():
        print(f"error: no such project: {proj}", file=sys.stderr)
        return 1
    meta = read_meta(proj)
    meta["name"] = name
    meta["bead_id"] = args.bead
    (proj / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"linked {name!r} -> bead {args.bead!r}; run `sync {name}` to derive lane from the bead")
    return 0


def cmd_sync_all(args, cfg: dict, repo_root: Path) -> int:
    md = master_dir(cfg, repo_root)
    if not md.is_dir():
        print(f"error: master dir missing: {md}", file=sys.stderr)
        return 1
    n = 0
    for proj in sorted(md.iterdir()):
        if not proj.is_dir() or proj.name.startswith("."):
            continue
        lane = resolve_lane(proj.name, cfg, repo_root)
        place_link(cfg, repo_root, lane, proj.name)
        print(f"  {proj.name} -> {lane}")
        n += 1
    print(f"synced {n} project(s)")
    return 0


def _collect_board(cfg: dict, repo_root: Path) -> dict[str, list[str]]:
    board = {lane_id: [] for lane_id in cfg["_lane_ids"]}
    md = master_dir(cfg, repo_root)
    if md.is_dir():
        for proj in sorted(md.iterdir()):
            if not proj.is_dir() or proj.name.startswith("."):
                continue
            board[resolve_lane(proj.name, cfg, repo_root)].append(proj.name)
    return board


def cmd_board(args, cfg: dict, repo_root: Path) -> int:
    board = _collect_board(cfg, repo_root)
    if args.json:
        print(json.dumps(board, ensure_ascii=False, indent=2))
        return 0
    for lane in cfg["lanes"]:
        items = board[lane["id"]]
        print(f"\n## {lane['folder']}  — {lane['title']}  ({len(items)})")
        for it in items:
            print(f"  • {it}")
        if not items:
            print("  (empty)")
    print()
    return 0


def cmd_doctor(args, cfg: dict, repo_root: Path) -> int:
    """Find inconsistencies: orphan symlinks, unmounted projects, multi-lane mounts."""
    issues: list[str] = []
    md = master_dir(cfg, repo_root)
    pd = projects_dir(cfg, repo_root)
    names = {p.name for p in md.iterdir() if p.is_dir() and not p.name.startswith(".")} if md.is_dir() else set()

    master_name = cfg.get("master_dir", "all-projects")
    mounts: dict[str, list[str]] = {}
    for lane_id in cfg["_lane_ids"]:
        folder = pd / cfg["_folder_by_id"][lane_id]
        if not folder.is_dir():
            continue
        for link in folder.iterdir():
            if link.name.startswith("."):
                continue
            if not link.is_symlink():
                issues.append(f"non-symlink entry in lane {lane_id}: {link.name}")
                continue
            mounts.setdefault(link.name, []).append(lane_id)
            # target must be exactly ../<master>/<name> — guards invariant_relative_target
            want = f"../{master_name}/{link.name}"
            if os.readlink(link) != want:
                issues.append(f"wrong-target symlink: {lane_id}/{link.name} -> {os.readlink(link)} (want {want})")
            if link.name not in names:
                issues.append(f"orphan symlink: {lane_id}/{link.name} -> (no project in all-projects)")
            elif not link.resolve().exists():
                issues.append(f"broken symlink: {lane_id}/{link.name}")

    for name in sorted(names):
        lanes_for = mounts.get(name, [])
        if not lanes_for:
            issues.append(f"unmounted project (no lane symlink): {name}")
        elif len(lanes_for) > 1:
            issues.append(f"multi-lane project (must be exactly one): {name} in {lanes_for}")
        else:
            # drift: the lane it's mounted in must equal the lane its bead/.project-status derives
            derived = resolve_lane(name, cfg, repo_root)
            if derived != lanes_for[0]:
                issues.append(f"drift: {name} mounted in {lanes_for[0]} but derives {derived} — run `sync {name}`")
            # unmapped: a bead status/labels that match nothing reads as a confident backlog, but isn't
            meta = read_meta(md / name)
            bs = bead_state(meta.get("bead_id", ""), repo_root) if meta.get("bead_id") else None
            if bs is not None and not status_is_mappable(bs[0], bs[1], cfg):
                issues.append(f"unmapped bead state: {name} status={bs[0]!r} labels={sorted(bs[1])} → defaulted to {derived}")

    if args.json:
        print(json.dumps({"issues": issues, "projects": sorted(names)}, ensure_ascii=False, indent=2))
    else:
        if not issues:
            print(f"doctor: OK — {len(names)} project(s), each mounted in exactly one lane")
        else:
            print(f"doctor: {len(issues)} issue(s)")
            for i in issues:
                print(f"  ✗ {i}")
    return 3 if issues else 0


def _seed_todo(name: str, jtbd: str, bead_id: str) -> str:
    return f"""# {name} — TODO

## OUTPUT / OUTCOME STATUS
- 📦 OUTPUT: <what artifact this project produces>
- ✅ OUTCOME: <what changes for the owner/team/user>
- 🚫 BLOCKERS: <named blockers, or none>
- 📋 NEXT STEPS: <next action>

## Ticket (one-to-one with the bead)
- JTBD title: {jtbd or "Когда ..., хотим ..., чтобы ..."}
- Bead (Bits Ticket): {bead_id or "<pr-rick-...> — create via `bd create`"}
- Branch / worktree: {name}

## 🚀 Critical chain (outcome -> first output, 3–5 links)
1. ...

## Last Updated
<date>
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="projects/ Kanban symlink mover")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the projects/ scaffold (all-projects + numbered lane folders)")

    sp = sub.add_parser("new", help="scaffold a new project in all-projects + mount in a lane")
    sp.add_argument("name")
    sp.add_argument("--bead", default="", help="bead id (Bits Ticket), e.g. pr-rick-7ms7")
    sp.add_argument("--jtbd", default="", help="JTBD title: 'Когда ..., хотим ..., чтобы ...'")
    sp.add_argument("--lane", default=None, help="initial lane id (default: backlog)")

    sp = sub.add_parser("move", help="set a project's lane explicitly (writes .project-status)")
    sp.add_argument("name")
    sp.add_argument("lane")

    sp = sub.add_parser("sync", help="re-derive a project's lane from its bead/.project-status")
    sp.add_argument("name")

    sp = sub.add_parser("link", help="attach a bead id to an existing project (migration when .beads arrives)")
    sp.add_argument("name")
    sp.add_argument("--bead", required=True, help="bead id (Bits Ticket)")

    sub.add_parser("sync-all", help="reconcile every project's lane symlink")

    sp = sub.add_parser("board", help="print the Kanban board")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("doctor", help="check for orphan/broken/wrong-target/drift/unmapped/multi-lane")
    sp.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_lanes()
    repo_root = find_repo_root()
    dispatch = {
        "init": cmd_init, "new": cmd_new, "move": cmd_move, "sync": cmd_sync, "link": cmd_link,
        "sync-all": cmd_sync_all, "board": cmd_board, "doctor": cmd_doctor,
    }
    try:
        return dispatch[args.cmd](args, cfg, repo_root)
    except ProjectError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
