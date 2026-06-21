# projects/ — symlink Kanban for project management

This folder is the team's **project board, as a filesystem**. Every project lives
once under `all-projects/` and is *mounted* by a single relative symlink into one
of five **numbered** lane folders, derived from its bead (the "Bits Ticket"). Open
this folder and you see the board in lifecycle order.

```
projects/
├── all-projects/         # SSOT — every project folder physically lives here, once
├── 1. backlog/           # raw, not yet specced (new project lands here)
├── 2. dod-n-blocked/     # DoD gate: specced before launch · blocked tickets park here
├── 3. in-progress/       # design · build · review
├── 4. to-delivery/       # handed off, awaiting owner activation
└── 5. verify-and-done/   # outcome verified, bead closed
```

> **Install:** create the scaffold once with
> `python3 .agents/skills/1-project-create-launch/scripts/project_status_symlinks.py init`.
> The lane folders are numbered so the explorer sorts them in lifecycle order; the CLI
> uses the short id (`backlog`, `dod-n-blocked`, …), not the number.

## Work runs through Beads → worktree → Graphify

Tasks live **in Beads (Dolt DB), not in files** — the project folder is the
human-readable entry; `bd` is the source of truth. Every project is driven through
the orchestrator (skill 19), not a markdown TODO:

```bash
bd create --title="Когда <ситуация>, хотим <результат>" --type=task   # 1. task in beads
python3 scripts/make_worktree.py <bead-id> --claim                     # 2. isolated worktree
python3 scripts/graphify.py --doctor                                   # 3. dependency graph
bd close <bead-id>                                                     # 4. on completion
```

| Tool | Role |
|---|---|
| **Beads** (`bd`) | source of truth for tasks/projects (Dolt-backed) |
| **Dolt** | DB engine + sync (`refs/dolt/data`) — **local-only, `bd init` per install** |
| **Graphify** | task+process dependency graph → `graphify-out/graph.json` |

## How the lane is decided

- A **project** is one-to-one with a **bead** (Bits Ticket, titled as a JTBD
  `Когда ..., хотим ..., чтобы ...`) and with a **worktree/branch**. The project
  folder name == branch == worktree basename, e.g. `pr-rick-<slug>-<bead-id>`.
- Each project folder physically lives in `all-projects/<name>/`. Its **status** is
  a single relative symlink `<lane>/<name> -> ../all-projects/<name>` — never a
  second physical copy.
- The lane is **derived** from the bead's status + labels via
  [`lanes.json`](../.agents/skills/1-project-create-launch/lanes.json). With no
  `.beads` db, an offline `.project-status` marker in the project folder drives it.

| Lane (folder) | id | Project stages | Bead status / labels |
|---|---|---|---|
| `1. backlog` | `backlog` | intake · pre-DoD | `open` (backlog/next) |
| `2. dod-n-blocked` | `dod-n-blocked` | DoD gate · blocked | label `dod_blocked` · `blocked` |
| `3. in-progress` | `in-progress` | in-dev · review | `in_progress` |
| `4. to-delivery` | `to-delivery` | delivery | label `delivering`/`owner_received` |
| `5. verify-and-done` | `verify-and-done` | outcome-verified · closed | `closed` · `outcome_realized` |

## Driving it

The mechanics + lifecycle live in the skill
[`.agents/skills/1-project-create-launch/`](../.agents/skills/1-project-create-launch/SKILL.md)
(`SKILL.md`, `workflow.yaml`, `lanes.json`, `scripts/project_status_symlinks.py`).
Full harness workflow — [`harness-workflow.yaml`](../harness-workflow.yaml).

```bash
PSS=".agents/skills/1-project-create-launch/scripts/project_status_symlinks.py"
python3 $PSS init                                     # create scaffold (once, at install)
python3 $PSS new pr-rick-<slug>-<id> --bead pr-rick-<id> --jtbd "Когда ..., хотим ..."
python3 $PSS move pr-rick-<slug>-<id> in-progress     # explicit lane (by id)
python3 $PSS sync pr-rick-<slug>-<id>                 # derive lane from bead
python3 $PSS board                                    # print the board
python3 $PSS doctor                                   # orphan / broken / wrong-target / drift / multi-lane
```

> Lane folders hold **only symlinks**. Never put a project's files directly in a
> lane — they belong in `all-projects/`. `doctor` flags any violation.

## Notes

- **Lanes are numbered (`1.`–`5.`)** so a file explorer sorts them in lifecycle order
  instead of alphabetically. The CLI takes the short id, never the number.
- **Portability.** Git stores the lane entries as real symlinks (mode `120000`).
  On Windows without symlink support, or after a GitHub "Download ZIP", they
  flatten into plaintext files — `doctor` reports them as `non-symlink entry`, and
  **`sync-all` rebuilds every lane symlink** from `all-projects/` in one command.
- **One writer.** `.beads` (the bead) is the source of truth for status; the symlink
  is a reflection. A manual `move` that contradicts a reachable bead is **warned
  about and reverted on the next `sync`** — update the bead, not just the folder.
