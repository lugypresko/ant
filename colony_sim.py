#!/usr/bin/env python3
"""
CodeNest colony simulation v2 (scripted, $0, no model calls).
Colony (4 cells, shared stigmergy board) vs central agent (1, private memory), equal budget.
Load sweep: mean arrival rate lam in {0.5, 1.5, 3.0} incidents/tick, Poisson.
Business value = SLA breaches avoided + reusable tool library + avoided compute.
Honest scope: mechanics under chosen rules only. Says NOTHING about LLM behavior.
"""
import random, statistics, json, math

FAMILIES = ["drop_multiline","drop_nonascii","drop_long","dup_records",
            "ts_shift","bad_encoding","schema_drift","partial_write"]
FAMILY_W = [8,6,5,4,3,2,1,1]
T = 200
SLA = 8
BUILD_CALLS = 8
REUSE_CALLS = 1
CALL_BUDGET = 1200
EVAP = 0.995
STRENGTHEN = 0.15
S_MAX = 0.98
BREACH_COST = 50.0
TOOL_VALUE = 120.0
CALL_COST = 0.04

def poisson(rng, lam):
    L = math.exp(-lam); k = 0; p = 1.0
    while True:
        p *= rng.random()
        if p <= L: return k
        k += 1

def run_arm(seed, n_agents, shared, lam):
    rng = random.Random(seed)
    incidents = []
    iid = 0
    for t in range(T):
        for _ in range(poisson(rng, lam)):
            fam = rng.choices(FAMILIES, weights=FAMILY_W)[0]
            incidents.append({"id": iid, "fam": fam, "born": t, "deadline": t + SLA})
            iid += 1
    boards = {} if shared else {a: {} for a in range(n_agents)}
    calls = resolved = reuses = builds = failed_reuse = 0
    queue = []
    for t in range(T):
        for ic in incidents:
            if ic["born"] == t:
                queue.append(dict(ic))
        queue.sort(key=lambda q: q["deadline"])
        for a in range(n_agents):
            if not queue or calls >= CALL_BUDGET:
                break
            ic = queue.pop(0)
            board = boards if shared else boards[a]
            s = board.get(ic["fam"], 0.0)
            if s > 0:
                calls += REUSE_CALLS
                if rng.random() < s:
                    resolved += 1; reuses += 1
                    board[ic["fam"]] = min(S_MAX, s + STRENGTHEN)
                else:
                    failed_reuse += 1
                    ic["deadline"] += 2
                    queue.append(ic)
            else:
                if calls + BUILD_CALLS > CALL_BUDGET:
                    queue.append(ic); continue
                calls += BUILD_CALLS; builds += 1
                board[ic["fam"]] = 1.0
                resolved += 1
        if shared:
            for f in list(boards):
                boards[f] *= EVAP
                if boards[f] < 0.05: del boards[f]
        queue = [q for q in queue if t <= q["deadline"]]
    arrived = len(incidents)
    breaches = arrived - resolved
    lib = len(boards) if shared else len(set().union(*[set(b) for b in boards.values()]))
    avoided = reuses * (BUILD_CALLS - REUSE_CALLS) * CALL_COST
    byproduct = lib * TOOL_VALUE + avoided
    return dict(arrived=arrived, resolved=resolved, breaches=breaches, calls=calls,
                builds=builds, reuses=reuses, failed_reuse=failed_reuse, library=lib,
                byproduct_usd=round(byproduct,1),
                cost_per_resolved=round(calls*CALL_COST/max(resolved,1),3))

SEEDS = range(30)
report = {}
for lam in [0.5, 1.5, 3.0]:
    col = [run_arm(s, 4, True, lam) for s in SEEDS]
    cen = [run_arm(s, 1, False, lam) for s in SEEDS]
    def agg(runs):
        out = {}
        for k in ["arrived","resolved","breaches","calls","builds","reuses","library","byproduct_usd","cost_per_resolved"]:
            vals = [r[k] for r in runs]
            out[k] = {"mean": round(statistics.mean(vals),1), "sd": round(statistics.pstdev(vals),1)}
        return out
    A, B = agg(col), agg(cen)
    report[str(lam)] = {"colony": A, "central": B,
        "sla_value_usd": round((B["breaches"]["mean"] - A["breaches"]["mean"]) * BREACH_COST, 1)}
print(json.dumps(report, indent=1))
