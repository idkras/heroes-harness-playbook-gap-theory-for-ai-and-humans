#!/usr/bin/env python3
"""Record and evaluate GitHub sync hook-chain telemetry."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_METRICS_PATH = ".agents/memory/runtime/5-sync-github-checklist/github-sync-telemetry.jsonl"
VALID_STATUSES = {"ok", "fail", "skip"}
ACTION_COUNTERS = {
    "commands_count",
    "git_commands_count",
    "gh_commands_count",
    "network_calls_count",
    "fetch_count",
    "guard_count",
    "worktree_created_count",
    "rebase_attempt_count",
    "merge_attempt_count",
    "push_count",
    "auto_stop_commit_count",
    "files_touched_count",
    "commits_created_count",
    "extra_actions_count",
    "missing_actions_count",
}


def repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd().resolve()
    return Path(result.stdout.strip()).resolve()


def current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def current_session_id() -> str:
    return (
        os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("SESSION_ID")
        or "unknown"
    )


def current_bead_id(branch: str) -> str | None:
    explicit = os.environ.get("BEAD_ID") or os.environ.get("BD_ID")
    if explicit:
        return explicit
    parts = branch.rsplit("-", 1)
    if len(parts) == 2 and parts[0].startswith("pr-") and parts[1]:
        namespace = parts[0].split("-", 2)[:2]
        if len(namespace) == 2:
            return f"{namespace[0]}-{namespace[1]}-{parts[1]}"
    return None


def resolve_metrics_path(raw_path: str | None) -> Path:
    path = Path(raw_path or DEFAULT_METRICS_PATH)
    if path.is_absolute():
        return path
    return repo_root() / path


def iso_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def append_record(
    metrics_path: Path,
    phase: str,
    duration_ms: int,
    status: str,
    command: list[str] | None = None,
    exit_code: int | None = None,
    extra: Any | None = None,
) -> dict[str, Any]:
    branch = current_branch()
    record: dict[str, Any] = {
        "timestamp": iso_timestamp(),
        "session_id": current_session_id(),
        "run_id": os.environ.get("SYNC_GITHUB_RUN_ID") or current_session_id(),
        "bead_id": current_bead_id(branch),
        "client_domain": os.environ.get("CLIENT_DOMAIN"),
        "repo_root": str(repo_root()),
        "branch": branch,
        "stage": phase,
        "phase": phase,
        "duration_ms": duration_ms,
        "status": status,
    }
    if command is not None:
        record["command"] = command
    if exit_code is not None:
        record["exit_code"] = exit_code
    inferred = infer_action_counts(command or [])
    extra_payload = extra if isinstance(extra, dict) else {}
    action_counts = merge_action_counts(inferred, extra_payload)
    record["action_counts"] = action_counts
    record["state_set"] = extra_payload.get("state_set")
    record["aggregate_phase"] = bool(extra_payload.get("aggregate_phase", False))
    record["qa_code_review"] = extra_payload.get("qa_code_review")
    record["qa_design_review"] = extra_payload.get("qa_design_review")
    record["qa_ui_review"] = extra_payload.get("qa_ui_review")
    record["qa_inception_review"] = extra_payload.get("qa_inception_review")
    record["qa_rca_review"] = extra_payload.get("qa_rca_review")
    record["qa_perf_review"] = extra_payload.get("qa_perf_review")
    record["verdict"] = extra_payload.get("verdict", status)
    record["blocked_reason"] = extra_payload.get("blocked_reason")
    if extra is not None:
        record["extra"] = extra

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record


def parse_extra_json(raw: str | None) -> Any | None:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid --extra-json: {exc}") from exc


def infer_action_counts(command: list[str]) -> dict[str, int]:
    counts = {counter: 0 for counter in ACTION_COUNTERS}
    if not command:
        return counts

    counts["commands_count"] = 1
    joined = " ".join(command)
    lower = joined.lower()
    first = Path(command[0]).name.lower()
    is_git = first == "git" or " git " in f" {lower} "
    is_gh = first == "gh" or " gh " in f" {lower} "

    if is_git:
        counts["git_commands_count"] = 1
    if is_gh:
        counts["gh_commands_count"] = 1

    if "git fetch" in lower or "git pull" in lower or "git push" in lower or "gh api" in lower or "gh pr" in lower:
        counts["network_calls_count"] = 1
    if "git fetch" in lower:
        counts["fetch_count"] = 1
    if "verify_" in lower or "team-sync-guard" in lower or "gen_hook_jtbd_registry.py --check" in lower:
        counts["guard_count"] = 1
    if "git worktree add" in lower or "make worktree" in lower:
        counts["worktree_created_count"] = 1
    if "git rebase" in lower or "pull --rebase" in lower:
        counts["rebase_attempt_count"] = 1
    if "git merge" in lower or "gh pr merge" in lower:
        counts["merge_attempt_count"] = 1
    if "git push" in lower:
        counts["push_count"] = 1
    if "auto_commit_on_stop.py" in lower:
        counts["auto_stop_commit_count"] = 1
    return counts


def merge_action_counts(inferred: dict[str, int], extra_payload: dict[str, Any]) -> dict[str, int]:
    counts = dict(inferred)
    extra_counts = extra_payload.get("action_counts")
    if isinstance(extra_counts, dict):
        for key, value in extra_counts.items():
            if key in ACTION_COUNTERS and isinstance(value, int) and value >= 0:
                counts[key] = counts.get(key, 0) + value

    actual_actions = extra_payload.get("actual_actions")
    if isinstance(actual_actions, list):
        counts["commands_count"] = max(counts["commands_count"], len(actual_actions))

    extra_actions = extra_payload.get("extra_actions")
    if isinstance(extra_actions, list):
        counts["extra_actions_count"] += len(extra_actions)

    missing_actions = extra_payload.get("missing_actions")
    if isinstance(missing_actions, list):
        counts["missing_actions_count"] += len(missing_actions)

    return counts


def iter_records(metrics_path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    warning_count = 0
    if not metrics_path.exists():
        return records, warning_count

    with metrics_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                warning_count += 1
                continue
            if not isinstance(parsed, dict):
                warning_count += 1
                continue
            records.append(parsed)
    return records, warning_count


def percentile(values: list[int], percent: int) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    index = max(0, math.ceil((percent / 100) * len(sorted_values)) - 1)
    return sorted_values[index]


def stats_for(records: list[dict[str, Any]]) -> dict[str, int]:
    durations = [
        int(record["duration_ms"])
        for record in records
        if isinstance(record.get("duration_ms"), int) and record.get("duration_ms") >= 0
    ]
    stats = {
        "count": len(records),
        "p50": percentile(durations, 50),
        "p95": percentile(durations, 95),
        "max": max(durations) if durations else 0,
        "fail_count": sum(1 for record in records if record.get("status") == "fail"),
    }
    for counter in sorted(ACTION_COUNTERS):
        stats[counter] = sum_action_counter(records, counter)
    return stats


def sum_action_counter(records: list[dict[str, Any]], counter: str) -> int:
    total = 0
    for record in records:
        action_counts = record.get("action_counts")
        if not isinstance(action_counts, dict):
            continue
        value = action_counts.get(counter)
        if isinstance(value, int) and value >= 0:
            total += value
    return total


def build_summary(metrics_path: Path, limit: int | None = None) -> dict[str, Any]:
    records, warning_count = iter_records(metrics_path)
    if limit is not None:
        records = records[-limit:]

    phases: dict[str, list[dict[str, Any]]] = {}
    runs: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        phase = record.get("phase")
        if not isinstance(phase, str):
            warning_count += 1
            continue
        phases.setdefault(phase, []).append(record)
        run_id = record.get("run_id")
        if isinstance(run_id, str) and run_id:
            runs.setdefault(run_id, []).append(record)

    return {
        "metrics_path": str(metrics_path),
        "warning_count": warning_count,
        "latest_phase": records[-1].get("phase") if records else None,
        "latest_status": records[-1].get("status") if records else None,
        "phases": {phase: stats_for(phase_records) for phase, phase_records in sorted(phases.items())},
        "runs": {run_id: stats_for(run_records) for run_id, run_records in sorted(runs.items())},
        "run_total": stats_for_run_totals(runs),
        "total": stats_for(records),
    }


def stats_for_run_totals(runs: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    run_records: list[dict[str, Any]] = []
    for run_id, records in runs.items():
        run_record: dict[str, Any] = {
            "run_id": run_id,
            "duration_ms": sum(
                int(record["duration_ms"])
                for record in records
                if isinstance(record.get("duration_ms"), int)
                and record.get("duration_ms") >= 0
                and not record.get("aggregate_phase")
            ),
            "status": "fail" if any(record.get("status") == "fail" for record in records) else "ok",
            "action_counts": {},
        }
        action_counts: dict[str, int] = {}
        for counter in ACTION_COUNTERS:
            action_counts[counter] = sum_action_counter(records, counter)
        run_record["action_counts"] = action_counts
        run_records.append(run_record)
    return stats_for(run_records)


def print_summary_text(summary: dict[str, Any]) -> None:
    if summary["warning_count"]:
        print(f"warnings: ignored {summary['warning_count']} invalid JSONL rows", file=sys.stderr)

    print("phase count p50 p95 max fail_count commands git gh network extra missing worktrees")
    for phase, stats in summary["phases"].items():
        print(
            f"{phase} {stats['count']} {stats['p50']} {stats['p95']} "
            f"{stats['max']} {stats['fail_count']} {stats['commands_count']} "
            f"{stats['git_commands_count']} {stats['gh_commands_count']} "
            f"{stats['network_calls_count']} {stats['extra_actions_count']} "
            f"{stats['missing_actions_count']} {stats['worktree_created_count']}"
        )
    total = summary["total"]
    print(
        f"total {total['count']} {total['p50']} {total['p95']} "
        f"{total['max']} {total['fail_count']} {total['commands_count']} "
        f"{total['git_commands_count']} {total['gh_commands_count']} "
        f"{total['network_calls_count']} {total['extra_actions_count']} "
        f"{total['missing_actions_count']} {total['worktree_created_count']}"
    )
    run_total = summary.get("run_total", stats_for([]))
    print(
        f"run_total {run_total['count']} {run_total['p50']} {run_total['p95']} "
        f"{run_total['max']} {run_total['fail_count']} {run_total['commands_count']} "
        f"{run_total['git_commands_count']} {run_total['gh_commands_count']} "
        f"{run_total['network_calls_count']} {run_total['extra_actions_count']} "
        f"{run_total['missing_actions_count']} {run_total['worktree_created_count']}"
    )


def format_ms(duration_ms: int) -> str:
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    seconds = round(duration_ms / 1000)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remainder = seconds % 60
    if remainder:
        return f"{minutes}m{remainder}s"
    return f"{minutes}m"


def print_owner_line(summary: dict[str, Any]) -> None:
    run_total = summary.get("run_total", stats_for([]))
    total = summary["total"]
    stage = summary.get("latest_phase") or "none"
    latest_status = summary.get("latest_status")
    verdict = "NO_DATA"
    if isinstance(latest_status, str):
        verdict = "PASS" if latest_status == "ok" else latest_status.upper()
    blockers = total["fail_count"]
    delivered_without_qa = 0
    print(
        "GitHub sync progress: "
        f"stage {stage} {verdict} · "
        f"current {format_ms(run_total['max'])} · "
        f"p50 {format_ms(run_total['p50'])} · "
        f"p95 {format_ms(run_total['p95'])} · "
        f"blockers {blockers} · "
        f"delivered_without_qa {delivered_without_qa}"
    )


def budget_sections(budget: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    phases = budget.get("phases", budget.get("phase", {}))
    total = budget.get("total", {})
    return (
        phases if isinstance(phases, dict) else {},
        total if isinstance(total, dict) else {},
    )


def evaluate_budget(summary: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    phase_budgets, total_budget = budget_sections(budget)
    failures: list[dict[str, Any]] = []
    total_stats = summary["total"]

    min_records = budget.get("min_records", total_budget.get("min_records"))
    if isinstance(min_records, int) and total_stats["count"] < min_records:
        failures.append(
            {
                "scope": "total",
                "metric": "count",
                "actual": total_stats["count"],
                "budget": min_records,
            }
        )

    required_phases = budget.get("required_phases", total_budget.get("required_phases", []))
    if isinstance(required_phases, list):
        for phase in required_phases:
            if not isinstance(phase, str):
                continue
            actual_count = summary["phases"].get(phase, stats_for([]))["count"]
            if actual_count < 1:
                failures.append(
                    {
                        "scope": "phase",
                        "phase": phase,
                        "metric": "required_phase",
                        "actual": actual_count,
                        "budget": 1,
                    }
                )
        if budget.get("require_complete_run") is True:
            complete_run_count = count_complete_runs(summary, required_phases)
            if complete_run_count < 1:
                failures.append(
                    {
                        "scope": "run",
                        "metric": "complete_required_phase_set",
                        "actual": complete_run_count,
                        "budget": 1,
                    }
                )

    for phase, phase_budget in sorted(phase_budgets.items()):
        if not isinstance(phase_budget, dict):
            continue
        stats = summary["phases"].get(phase, stats_for([]))
        phase_min_records = phase_budget.get("min_records")
        if isinstance(phase_min_records, int) and stats["count"] < phase_min_records:
            failures.append(
                {
                    "scope": "phase",
                    "phase": phase,
                    "metric": "count",
                    "actual": stats["count"],
                    "budget": phase_min_records,
                }
            )

        max_p95_ms = phase_budget.get("max_p95_ms")
        if isinstance(max_p95_ms, (int, float)) and stats["p95"] > max_p95_ms:
            failures.append(
                {
                    "scope": "phase",
                    "phase": phase,
                    "metric": "p95",
                    "actual": stats["p95"],
                    "budget": max_p95_ms,
                }
            )

        max_fail_rate = phase_budget.get("max_fail_rate")
        if isinstance(max_fail_rate, (int, float)):
            fail_rate = stats["fail_count"] / stats["count"] if stats["count"] else 0
            if fail_rate > max_fail_rate:
                failures.append(
                    {
                        "scope": "phase",
                        "phase": phase,
                        "metric": "fail_rate",
                        "actual": fail_rate,
                        "budget": max_fail_rate,
                    }
                )
        failures.extend(evaluate_counter_budget("phase", phase, stats, phase_budget))

    total_max_p95_ms = total_budget.get("max_p95_ms")
    run_total_budget = budget.get("run_total", {})
    if not isinstance(run_total_budget, dict):
        run_total_budget = {}
    run_total_stats = summary.get("run_total", stats_for([]))

    run_total_min_records = run_total_budget.get("min_records")
    if isinstance(run_total_min_records, int) and run_total_stats["count"] < run_total_min_records:
        failures.append(
            {
                "scope": "run_total",
                "metric": "count",
                "actual": run_total_stats["count"],
                "budget": run_total_min_records,
            }
        )

    run_total_max_p95_ms = run_total_budget.get("max_p95_ms")
    if isinstance(run_total_max_p95_ms, (int, float)) and run_total_stats["p95"] > run_total_max_p95_ms:
        failures.append(
            {
                "scope": "run_total",
                "metric": "p95",
                "actual": run_total_stats["p95"],
                "budget": run_total_max_p95_ms,
            }
        )
    if isinstance(total_max_p95_ms, (int, float)) and total_stats["p95"] > total_max_p95_ms:
        failures.append(
            {
                "scope": "total",
                "metric": "p95",
                "actual": total_stats["p95"],
                "budget": total_max_p95_ms,
            }
        )
    max_fail_rate = total_budget.get("max_fail_rate")
    if isinstance(max_fail_rate, (int, float)):
        fail_rate = total_stats["fail_count"] / total_stats["count"] if total_stats["count"] else 0
        if fail_rate > max_fail_rate:
            failures.append(
                {
                    "scope": "total",
                    "metric": "fail_rate",
                    "actual": fail_rate,
                    "budget": max_fail_rate,
                }
            )
    failures.extend(evaluate_counter_budget("total", None, total_stats, total_budget))
    failures.extend(evaluate_counter_budget("run_total", None, run_total_stats, run_total_budget))

    return {
        "pass": not failures,
        "failures": failures,
        "summary": summary,
    }


def count_complete_runs(summary: dict[str, Any], required_phases: list[Any]) -> int:
    required = {phase for phase in required_phases if isinstance(phase, str)}
    if not required:
        return 0
    count = 0
    for run_id in summary.get("runs", {}):
        phases = {record.get("phase") for record in iter_records_for_run(summary["metrics_path"], run_id)}
        if required.issubset(phases):
            count += 1
    return count


def iter_records_for_run(metrics_path: str, run_id: str) -> list[dict[str, Any]]:
    records, _warning_count = iter_records(Path(metrics_path))
    return [record for record in records if record.get("run_id") == run_id]


def evaluate_counter_budget(
    scope: str,
    phase: str | None,
    stats: dict[str, int],
    budget: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    max_counters = budget.get("max_counters")
    if not isinstance(max_counters, dict):
        return failures
    for counter, max_value in sorted(max_counters.items()):
        if counter not in ACTION_COUNTERS or not isinstance(max_value, (int, float)):
            continue
        actual = stats.get(counter, 0)
        if actual > max_value:
            failure: dict[str, Any] = {
                "scope": scope,
                "metric": counter,
                "actual": actual,
                "budget": max_value,
            }
            if phase is not None:
                failure["phase"] = phase
            failures.append(failure)
    return failures


def cmd_record(args: argparse.Namespace) -> int:
    append_record(
        resolve_metrics_path(args.metrics),
        args.phase,
        args.duration_ms,
        args.status,
        command=args.command,
        extra=parse_extra_json(args.extra_json),
    )
    return 0


def cmd_wrap(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("wrap requires COMMAND", file=sys.stderr)
        return 2

    started = time.monotonic()
    try:
        completed = subprocess.run(command)
        exit_code = completed.returncode
    except OSError as exc:
        print(f"failed to run command: {exc}", file=sys.stderr)
        exit_code = 127
    duration_ms = int(round((time.monotonic() - started) * 1000))
    append_record(
        resolve_metrics_path(args.metrics),
        args.phase,
        duration_ms,
        "ok" if exit_code == 0 else "fail",
        command=command,
        exit_code=exit_code,
        extra=parse_extra_json(args.extra_json),
    )
    return exit_code


def cmd_summary(args: argparse.Namespace) -> int:
    summary = build_summary(resolve_metrics_path(args.metrics), args.limit)
    if summary["warning_count"]:
        print(f"warnings: ignored {summary['warning_count']} invalid JSONL rows", file=sys.stderr)
    if args.owner_line:
        print_owner_line(summary)
    elif args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print_summary_text(summary)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    metrics_path = resolve_metrics_path(args.metrics)
    summary = build_summary(metrics_path)
    if summary["warning_count"]:
        print(f"warnings: ignored {summary['warning_count']} invalid JSONL rows", file=sys.stderr)
    with Path(args.budget_json).open("r", encoding="utf-8") as handle:
        budget = json.load(handle)
    result = evaluate_budget(summary, budget)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("PASS" if result["pass"] else "FAIL")
        for failure in result["failures"]:
            print(json.dumps(failure, sort_keys=True))
    return 0 if result["pass"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--metrics", default=DEFAULT_METRICS_PATH)
    record.add_argument("--phase", required=True)
    record.add_argument("--duration-ms", required=True, type=int)
    record.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    record.add_argument("--command", nargs=argparse.REMAINDER)
    record.add_argument("--extra-json")
    record.set_defaults(func=cmd_record)

    wrap = subparsers.add_parser("wrap")
    wrap.add_argument("--metrics", default=DEFAULT_METRICS_PATH)
    wrap.add_argument("--phase", required=True)
    wrap.add_argument("--extra-json")
    wrap.add_argument("command", nargs=argparse.REMAINDER)
    wrap.set_defaults(func=cmd_wrap)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--metrics", default=DEFAULT_METRICS_PATH)
    summary.add_argument("--json", action="store_true")
    summary.add_argument("--owner-line", action="store_true")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=cmd_summary)

    evaluate = subparsers.add_parser("eval")
    evaluate.add_argument("--metrics", default=DEFAULT_METRICS_PATH)
    evaluate.add_argument("--budget-json", required=True)
    evaluate.add_argument("--json", action="store_true")
    evaluate.set_defaults(func=cmd_eval)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "duration_ms") and args.duration_ms < 0:
        parser.error("--duration-ms must be >= 0")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
