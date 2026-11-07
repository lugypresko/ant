#!/usr/bin/env python3
"""Summarize Experiment 5 process traces (standard library only)."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def trace_paths(inputs):
    paths = []
    for item in inputs:
        p = Path(item)
        paths.extend(sorted(p.rglob("*.jsonl")) if p.is_dir() else [p])
    return [p for p in paths if p.is_file()]


def read_runs(paths):
    runs = defaultdict(list)
    for path in paths:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not event.get("run_id") or not event.get("event_type"):
                raise ValueError(f"{path}:{line_no}: missing run_id or event_type")
            event["_source_order"] = len(runs[event["run_id"]])
            event["_trace_file"] = str(path)
            runs[event["run_id"]].append(event)
    return runs


def analyze_run(events):
    events.sort(key=lambda e: (e.get("tick", 0), e.get("_source_order", 0)))
    first = events[0]
    counts = Counter(e.get("event_type", "unknown") for e in events)
    actors = defaultdict(Counter)
    actor_artifacts = defaultdict(Counter)
    artifact_writes = []
    task_actors = defaultdict(list)
    sequence = []
    test_runs = 0
    test_statuses = []
    first_test_index = first_test_artifact_index = first_prod_index = None
    calls_before_first_test = 0
    duration_before_first_test = 0
    failure_pending = edit_after_failure = False
    failure_edit_retest_cycles = 0
    path_writes = Counter()
    pool_updates = direct_messages = 0
    tokens_in = tokens_out = worker_calls = 0
    duration_ms = 0

    for i, event in enumerate(events):
        et = event.get("event_type")
        actor = str(event.get("actor_id", "unknown"))
        task = event.get("task_id")
        if task and et in {"decision", "worker_call", "artifact_write"}:
            owners = task_actors[str(task)]
            if not owners or owners[-1] != actor:
                owners.append(actor)
        if et == "worker_call":
            worker_calls += 1
            tokens_in += int(event.get("tokens_in") or 0)
            tokens_out += int(event.get("tokens_out") or 0)
            duration_ms += int(event.get("duration_ms") or 0)
        elif et == "test_run":
            test_runs += 1
            if first_test_index is None:
                first_test_index = i
                calls_before_first_test = worker_calls
                duration_before_first_test = duration_ms
        elif et == "artifact_write":
            path = event.get("artifact_path")
            kind = event.get("artifact_kind") or "unknown"
            artifact_writes.append({"actor": actor, "path": path, "kind": kind, "tick": event.get("tick")})
            actors[actor]["artifact_write"] += 1
            actor_artifacts[actor][kind] += 1
            if path:
                path_writes[str(path)] += 1
            if kind == "test" and first_test_artifact_index is None:
                first_test_artifact_index = i
            if kind == "production" and first_prod_index is None:
                first_prod_index = i
            if failure_pending:
                edit_after_failure = True
                failure_pending = False
            sequence.append(f"write:{kind}")
        elif et == "test_result":
            status = event.get("test_status")
            test_statuses.append(status)
            if status == "fail":
                failure_pending = True
                edit_after_failure = False
            elif status == "pass" and edit_after_failure:
                failure_edit_retest_cycles += 1
                edit_after_failure = False
            sequence.append(f"test:{status or 'unknown'}")
        elif et == "decision":
            actors[actor]["decision"] += 1
            sequence.append("decision:" + str(event.get("selected_action") or "unspecified"))
        elif et == "pool_update":
            pool_updates += 1
            sequence.append("pool_update")
        elif et in {"direct_message", "message"}:
            direct_messages += 1
            sequence.append("message")
        elif et == "test_run":
            sequence.append("test_run")
        else:
            sequence.append(et or "unknown")

    roles = {}
    for actor, kinds in actor_artifacts.items():
        total = sum(kinds.values())
        dominant, count = kinds.most_common(1)[0]
        roles[actor] = {
            "signal": dominant + "_leaning" if total and count / total >= 0.6 else "mixed",
            "artifact_counts": dict(kinds),
        }
    compact_sequence = []
    for item in sequence:
        if not compact_sequence or compact_sequence[-1] != item:
            compact_sequence.append(item)

    return {
        "run_id": first.get("run_id"),
        "arm": first.get("arm"),
        "seed": first.get("seed"),
        "events": len(events),
        "event_counts": dict(counts),
        "worker_calls": worker_calls,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "duration_ms": duration_ms,
        "test_runs": test_runs,
        "test_statuses": test_statuses,
        "calls_before_first_test": calls_before_first_test if first_test_index is not None else None,
        "duration_ms_before_first_test": duration_before_first_test if first_test_index is not None else None,
        "test_artifact_before_production": (
            first_test_artifact_index < first_prod_index
            if first_test_artifact_index is not None and first_prod_index is not None else None
        ),
        "failure_edit_retest_cycles": failure_edit_retest_cycles,
        "artifact_rewrites": sum(max(0, n - 1) for n in path_writes.values()),
        "task_actor_sequences": dict(task_actors),
        "actors_per_task": {task: len(set(owners)) for task, owners in task_actors.items()},
        "artifact_writes": artifact_writes,
        "role_signals_heuristic": roles,
        "pool_updates": pool_updates,
        "direct_messages": direct_messages,
        "work_sequence": compact_sequence,
    }


def aggregate(rows):
    by_arm = defaultdict(list)
    for row in rows:
        by_arm[row.get("arm") or "unknown"].append(row)
    summary = {}
    for arm, group in by_arm.items():
        first_test = [r["test_artifact_before_production"] for r in group
                      if r["test_artifact_before_production"] is not None]
        summary[arm] = {
            "runs": len(group),
            "mean_worker_calls": round(sum(r["worker_calls"] for r in group) / len(group), 2),
            "mean_test_runs": round(sum(r["test_runs"] for r in group) / len(group), 2),
            "test_artifact_first_rate": round(sum(first_test) / len(first_test), 3) if first_test else None,
            "mean_failure_edit_retest_cycles": round(
                sum(r["failure_edit_retest_cycles"] for r in group) / len(group), 2
            ),
            "mean_artifact_rewrites": round(sum(r["artifact_rewrites"] for r in group) / len(group), 2),
            "mean_pool_updates": round(sum(r["pool_updates"] for r in group) / len(group), 2),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="trace JSONL files or directories")
    parser.add_argument("--out", default="run5/process_metrics.json")
    args = parser.parse_args()
    inputs = args.inputs or ["run5/traces"]
    runs = read_runs(trace_paths(inputs))
    rows = [analyze_run(events) for events in runs.values()]
    output = {"runs": rows, "by_arm": aggregate(rows)}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = out.with_suffix(".csv")
    columns = ["run_id", "arm", "seed", "worker_calls", "tokens_in", "tokens_out",
               "duration_ms", "test_runs", "calls_before_first_test",
               "test_artifact_before_production", "failure_edit_retest_cycles",
               "artifact_rewrites", "pool_updates", "direct_messages"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in columns} for row in rows)
    print(f"Analyzed {len(rows)} run(s); wrote {out} and {csv_path}")


if __name__ == "__main__":
    main()
