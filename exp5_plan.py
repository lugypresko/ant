#!/usr/bin/env python3
"""Prepare the Experiment 5 run matrix without contacting an LLM provider."""

import argparse
import json
from pathlib import Path

ARMS = ("single", "central_sdlc", "colony", "central_free", "cells")
PILOT_ARMS = ("single", "central_sdlc", "colony")
REQUIREMENT_ID = "invoice-intake-v1"


def build_plan(repetitions: int, arms: tuple[str, ...]) -> dict:
    if repetitions < 1:
        raise ValueError("repetitions must be >= 1")
    unknown = set(arms) - set(ARMS)
    if unknown:
        raise ValueError(f"unknown arm(s): {', '.join(sorted(unknown))}")
    if len(set(arms)) != len(arms):
        raise ValueError("arms must be unique")

    runs = []
    for block in range(1, repetitions + 1):
        for arm in arms:
            runs.append({
                "run_id": f"exp5-{REQUIREMENT_ID}-b{block:02d}-{arm}",
                "requirement_id": REQUIREMENT_ID,
                "arm": arm,
                "seed": block,
                "block": block,
                "status": "planned",
            })
    return {
        "experiment": "exp5",
        "mode": "plan_only",
        "requirement_id": REQUIREMENT_ID,
        "repetitions_per_arm": repetitions,
        "arms": list(arms),
        "planned_runs": len(runs),
        "api_calls": 0,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pilot", action="store_true", help="prepare 3 blocks (default)")
    group.add_argument("--main", action="store_true", help="prepare 30 blocks across all arms")
    parser.add_argument("--repetitions", type=int, help="override block count")
    parser.add_argument("--arms", nargs="+", choices=ARMS,
                        help="override default pilot/main arms")
    parser.add_argument("--out", default="run5/planned_runs.json")
    args = parser.parse_args()

    repetitions = args.repetitions if args.repetitions is not None else (30 if args.main else 3)
    arms = tuple(args.arms) if args.arms else (ARMS if args.main else PILOT_ARMS)
    plan = build_plan(repetitions, arms)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Experiment 5 plan prepared: {plan['planned_runs']} slots, 0 API calls")
    print(f"Arms: {', '.join(plan['arms'])}; repetitions per arm: {repetitions}")
    print(f"Manifest: {out}")


if __name__ == "__main__":
    main()
