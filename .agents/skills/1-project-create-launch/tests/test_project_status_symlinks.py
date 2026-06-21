"""Tests for project_status_symlinks.py — the projects/ Kanban symlink mover.

Run: python3 -m pytest .agents/skills/1-project-create-launch/tests/ -q
Stdlib + pytest only; no .beads db needed (offline .project-status path is exercised).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "pss", SKILL / "scripts" / "project_status_symlinks.py"
)
pss = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pss)

CFG = pss.load_lanes()
FOLDER = {lane["id"]: lane["folder"] for lane in CFG["lanes"]}  # lane id -> numbered folder name


def lane_path(repo, lane_id, name=""):
    p = repo / "projects" / FOLDER[lane_id]
    return p / name if name else p


# ── lane resolution from bead state (pure, the SSOT logic) ───────────────────
@pytest.mark.parametrize(
    "status,labels,expected",
    [
        ("open", set(), "backlog"),
        ("open", {"dod_blocked"}, "dod-n-blocked"),     # dod_blocked label → the gate
        ("open", {"next"}, "backlog"),
        ("in_progress", set(), "in-progress"),
        ("in_progress", {"in_review"}, "in-progress"),
        ("in_progress", {"delivering"}, "to-delivery"),
        ("in_progress", {"owner_received"}, "to-delivery"),
        ("in_progress", {"outcome_realized"}, "verify-and-done"),
        ("blocked", set(), "dod-n-blocked"),            # status override → DoD/blocked gate
        ("blocked", {"in_review"}, "dod-n-blocked"),    # status override beats progress label
        ("closed", set(), "verify-and-done"),           # status override
        ("closed", {"in_progress"}, "verify-and-done"), # status override beats label
        ("weird-status", set(), "backlog"),             # default
        # label_overrides: a blocked/dod_blocked label pulls to the gate regardless of progress
        ("in_progress", {"blocked"}, "dod-n-blocked"),
        ("in_progress", {"owner_received", "blocked"}, "dod-n-blocked"),
        ("in_progress", {"dod_blocked"}, "dod-n-blocked"),
        # Std-4.15 `status:` prefixed labels normalize to bare names
        ("in_progress", {"status:owner_received"}, "to-delivery"),
        ("in_progress", {"status:outcome_realized"}, "verify-and-done"),
        # finer 4.15 stage names used as a status string resolve too
        ("in_review", set(), "in-progress"),
        ("owner_received", set(), "to-delivery"),
        ("outcome_realized", set(), "verify-and-done"),
    ],
)
def test_resolve_lane_from_bead(status, labels, expected):
    assert pss.resolve_lane_from_bead(status, labels, CFG) == expected


@pytest.mark.parametrize(
    "status,labels,mappable",
    [
        ("", set(), True),                  # brand-new
        ("open", set(), True),
        ("in_progress", {"delivering"}, True),
        ("blocked", set(), True),
        ("in_progress", {"blocked"}, True),  # via label_override
        ("frobnicate", set(), False),        # unknown → not mappable (doctor will flag)
        ("frobnicate", {"mystery"}, False),
    ],
)
def test_status_is_mappable(status, labels, mappable):
    assert pss.status_is_mappable(status, labels, CFG) is mappable


def test_lanes_json_is_lifecycle_ordered():
    ids = [lane["id"] for lane in CFG["lanes"]]
    assert ids == ["backlog", "dod-n-blocked", "in-progress", "to-delivery", "verify-and-done"]


def test_lane_folders_are_numbered():
    folders = [lane["folder"] for lane in CFG["lanes"]]
    assert folders == ["1. backlog", "2. dod-n-blocked", "3. in-progress", "4. to-delivery", "5. verify-and-done"]


def test_init_creates_numbered_scaffold(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".git").mkdir()
    assert pss.cmd_init(_ns(), CFG, tmp_path) == 0
    assert (tmp_path / "projects" / "all-projects").is_dir()
    for lane in CFG["lanes"]:
        assert (tmp_path / "projects" / lane["folder"]).is_dir()
    # idempotent
    assert pss.cmd_init(_ns(), CFG, tmp_path) == 0


# ── filesystem mechanics in a temp repo ──────────────────────────────────────
@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".git").mkdir()
    pdir = tmp_path / CFG["projects_root"]
    (pdir / CFG["master_dir"]).mkdir(parents=True)
    for lane in CFG["lanes"]:
        (pdir / lane["folder"]).mkdir(parents=True)
    return tmp_path


def _ns(**kw):
    import argparse
    return argparse.Namespace(**kw)


def test_new_creates_folder_todo_and_single_symlink(repo):
    rc = pss.cmd_new(_ns(name="pr-rick-demo-aaa1", bead="pr-rick-aaa1", jtbd="Когда X, хотим Y", lane=None), CFG, repo)
    assert rc == 0
    proj = repo / "projects" / "all-projects" / "pr-rick-demo-aaa1"
    assert proj.is_dir()
    assert (proj / "pr-rick-demo-aaa1.todo.md").exists()
    assert json.loads((proj / ".project-meta.json").read_text())["bead_id"] == "pr-rick-aaa1"
    # default lane = backlog (1. backlog), exactly one symlink, relative target
    link = lane_path(repo, "backlog", "pr-rick-demo-aaa1")
    assert link.is_symlink()
    assert str(link.readlink()) == "../all-projects/pr-rick-demo-aaa1"
    assert link.resolve() == proj.resolve()


def test_move_is_idempotent_single_lane(repo):
    pss.cmd_new(_ns(name="p1", bead="", jtbd="", lane=None), CFG, repo)
    pss.cmd_move(_ns(name="p1", lane="in-progress"), CFG, repo)
    pss.cmd_move(_ns(name="p1", lane="in-progress"), CFG, repo)  # twice = still one
    mounts = [
        lane["id"] for lane in CFG["lanes"]
        if (repo / "projects" / lane["folder"] / "p1").is_symlink()
    ]
    assert mounts == ["in-progress"]


def test_move_then_to_delivery_then_done(repo):
    pss.cmd_new(_ns(name="p2", bead="", jtbd="", lane=None), CFG, repo)
    for lane in ("in-progress", "to-delivery", "verify-and-done"):
        pss.cmd_move(_ns(name="p2", lane=lane), CFG, repo)
        present = [
            l["id"] for l in CFG["lanes"]
            if (repo / "projects" / l["folder"] / "p2").is_symlink()
        ]
        assert present == [lane]


def test_sync_uses_status_file_when_no_bead(repo):
    pss.cmd_new(_ns(name="p3", bead="", jtbd="", lane=None), CFG, repo)
    # simulate offline lane change by writing the marker directly, then sync
    (repo / "projects" / "all-projects" / "p3" / ".project-status").write_text("to-delivery\n")
    pss.cmd_sync(_ns(name="p3"), CFG, repo)
    assert lane_path(repo, "to-delivery", "p3").is_symlink()
    assert not lane_path(repo, "backlog", "p3").is_symlink()


def test_board_groups_by_lane(repo):
    pss.cmd_new(_ns(name="a", bead="", jtbd="", lane="backlog"), CFG, repo)
    pss.cmd_new(_ns(name="b", bead="", jtbd="", lane="in-progress"), CFG, repo)
    board = pss._collect_board(CFG, repo)
    assert board["backlog"] == ["a"]
    assert board["in-progress"] == ["b"]


def test_doctor_clean_then_detects_orphan_and_multilane(repo):
    pss.cmd_new(_ns(name="ok", bead="", jtbd="", lane="in-progress"), CFG, repo)
    assert pss.cmd_doctor(_ns(json=True), CFG, repo) == 0

    # orphan: symlink with no backing project
    (lane_path(repo, "to-delivery", "ghost")).symlink_to("../all-projects/ghost")
    # multi-lane: add a second symlink for the real project
    (lane_path(repo, "to-delivery", "ok")).symlink_to("../all-projects/ok")
    assert pss.cmd_doctor(_ns(json=False), CFG, repo) == 3


def test_new_rejects_duplicate(repo):
    pss.cmd_new(_ns(name="dup", bead="", jtbd="", lane=None), CFG, repo)
    assert pss.cmd_new(_ns(name="dup", bead="", jtbd="", lane=None), CFG, repo) == 1


def test_new_rejects_unknown_lane(repo):
    assert pss.cmd_new(_ns(name="x", bead="", jtbd="", lane="nope"), CFG, repo) == 2


# ── hardening fixes from review ───────────────────────────────────────────────
def test_clear_links_removes_stray_file_shadow(repo):
    """A regular-file shadow in a lane (e.g. zip-flattened symlink) must not block a move."""
    pss.cmd_new(_ns(name="p", bead="", jtbd="", lane=None), CFG, repo)
    # plant a stray *file* (not symlink) named like the project in another lane
    lane_path(repo, "in-progress", "p").write_text("../all-projects/p\n")
    pss.cmd_move(_ns(name="p", lane="to-delivery"), CFG, repo)  # would FileExistsError on the dead branch
    present = [l["id"] for l in CFG["lanes"] if (repo / "projects" / l["folder"] / "p").is_symlink()]
    assert present == ["to-delivery"]
    assert not lane_path(repo, "in-progress", "p").exists()  # stray cleared


def test_clear_links_refuses_real_directory_in_lane(repo):
    pss.cmd_new(_ns(name="p", bead="", jtbd="", lane=None), CFG, repo)
    lane_path(repo, "in-progress", "p").mkdir()  # someone's real data, not a symlink
    with pytest.raises(pss.ProjectError):
        pss.cmd_move(_ns(name="p", lane="to-delivery"), CFG, repo)
    # and via main() it becomes a clean exit-1, not a traceback
    assert pss.main(["move", "p", "to-delivery"]) == 1


def test_main_turns_project_error_into_exit_1(repo, monkeypatch):
    monkeypatch.chdir(repo)
    assert pss.main(["move", "../escape", "in-progress"]) == 1   # invalid name
    assert pss.main(["sync", "no-such-project"]) == 1


@pytest.mark.parametrize("bad", ["../escape", "a/b", ".", "..", ""])
def test_name_validation_rejects_traversal(bad):
    with pytest.raises(pss.ProjectError):
        pss.validate_name(bad)


def test_doctor_detects_wrong_target(repo):
    pss.cmd_new(_ns(name="ok", bead="", jtbd="", lane="in-progress"), CFG, repo)
    link = lane_path(repo, "in-progress", "ok")
    link.unlink()
    link.symlink_to("../all-projects/SOMETHING-ELSE")  # exists check passes only if target exists; wrong path regardless
    rc = pss.cmd_doctor(_ns(json=True), CFG, repo)
    assert rc == 3  # wrong-target flagged


def test_doctor_detects_drift(repo):
    pss.cmd_new(_ns(name="d", bead="", jtbd="", lane="in-progress"), CFG, repo)
    # change the offline marker WITHOUT re-syncing → mounted (in-progress) != derived (to-delivery)
    (repo / "projects" / "all-projects" / "d" / ".project-status").write_text("to-delivery\n")
    assert pss.cmd_doctor(_ns(json=False), CFG, repo) == 3


def test_link_then_sync_uses_bead(repo, monkeypatch):
    pss.cmd_new(_ns(name="m", bead="", jtbd="", lane=None), CFG, repo)
    assert pss.cmd_link(_ns(name="m", bead="pr-rick-zzz9"), CFG, repo) == 0
    import json as _json
    meta = _json.loads((repo / "projects" / "all-projects" / "m" / ".project-meta.json").read_text())
    assert meta["bead_id"] == "pr-rick-zzz9"
    # with bead unreachable (no db) sync falls back to .project-status (still backlog)
    monkeypatch.setattr(pss, "bead_state", lambda bid, root: None)
    assert pss.cmd_sync(_ns(name="m"), CFG, repo) == 0


def test_resolve_lane_prefers_bead_over_status_file(repo, monkeypatch):
    pss.cmd_new(_ns(name="b", bead="pr-rick-aaa", jtbd="", lane="backlog"), CFG, repo)
    monkeypatch.setattr(pss, "bead_state", lambda bid, root: ("in_progress", {"owner_received"}))
    assert pss.resolve_lane("b", CFG, repo) == "to-delivery"  # bead wins over backlog marker
