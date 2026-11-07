#!/usr/bin/env python3
"""
Faithful ant-model colony simulation (scripted, $0, no model calls).
30 two-state agents (searching/returning), purely local sensing, pheromone-weighted
stochastic choice + epsilon exploration, no personal memory, no roles, no coordinator.
Shared field: family -> weight; constant evaporation, reinforcement on successful returns.
Compared to single central agent and 4-cell shared-board design at 3 loads, 30 seeds.
"""
import random, statistics, json, math

FAMILIES = ["drop_multiline","drop_nonascii","drop_long","dup_records",
            "ts_shift","bad_encoding","schema_drift","partial_write"]
FAMILY_W = [8,6,5,4,3,2,1,1]
T, SLA, CALL_BUDGET = 200, 8, 1200
BUILD_CALLS, REUSE_CALLS = 8, 1
BREACH_COST, TOOL_VALUE, CALL_COST = 50.0, 120.0, 0.04
# ant params (frozen pre-run)
N_ANTS, EVAP_A = 30, 0.99
DEPOSIT_OK, DEPOSIT_FAIL = 0.2, 0.03
EPS, WINDOW, LIB_THRESH = 0.10, 5, 1.0
# 4-cell params (as in v2)
EVAP4, STRENGTHEN4, S_MAX4 = 0.995, 0.15, 0.98

def poisson(rng, lam):
    L = math.exp(-lam); k = 0; p = 1.0
    while True:
        p *= rng.random()
        if p <= L: return k
        k += 1

def gen(seed, lam):
    rng = random.Random(seed); inc = []; iid = 0
    for t in range(T):
        for _ in range(poisson(rng, lam)):
            fam = rng.choices(FAMILIES, weights=FAMILY_W)[0]
            inc.append({"id": iid, "fam": fam, "born": t, "deadline": t + SLA}); iid += 1
    return inc

def run_ants(seed, lam, eps=EPS, evap=EVAP_A):
    rng = random.Random(seed + 7777)  # arm-specific stream, same incidents via gen()
    incidents = gen(seed, lam)
    w = {}                       # pheromone field: fam -> weight
    ants = [{"state": "searching", "carry": None} for _ in range(N_ANTS)]
    calls = resolved = reuses = 0
    library = set()
    resolved_first50 = resolved_last50 = 0
    queue = []
    for t in range(T):
        for ic in incidents:
            if ic["born"] == t: queue.append(dict(ic))
        queue.sort(key=lambda q: q["deadline"])
        queue = [q for q in queue if t <= q["deadline"]]
        for a in ants:
            if a["state"] == "returning":
                fam = a["carry"]
                w[fam] = w.get(fam, 0.0) + (DEPOSIT_OK if a.get("ok") else DEPOSIT_FAIL)
                if w[fam] >= LIB_THRESH: library.add(fam)
                a["state"] = "searching"; a["carry"] = None; a["ok"] = False
            elif a["state"] == "searching" and queue and calls < CALL_BUDGET:
                visible = queue[:WINDOW]
                if rng.random() < eps or all(w.get(v["fam"], 0.0) == 0 for v in visible):
                    ic = rng.choice(visible)          # exploration / cold start
                else:
                    weights = [w.get(v["fam"], 0.0) + 0.05 for v in visible]
                    ic = rng.choices(visible, weights=weights)[0]
                queue.remove(ic)
                calls += 1
                p = min(0.95, max(0.25, 0.25 + 0.5 * w.get(ic["fam"], 0.0)))
                ok = rng.random() < p
                if ok:
                    resolved += 1
                    if ic["born"] < 50: resolved_first50 += 1
                    if ic["born"] >= 150: resolved_last50 += 1
                    if ic["fam"] in library: reuses += 1
                else:
                    ic["deadline"] += 2; queue.append(ic)
                a["state"] = "returning"; a["carry"] = ic["fam"]; a["ok"] = ok
        for f in list(w):
            w[f] *= evap
            if w[f] < 0.02: del w[f]
    arrived = len(incidents); breaches = arrived - resolved
    avoided = reuses * (BUILD_CALLS - REUSE_CALLS) * CALL_COST
    return dict(arrived=arrived, resolved=resolved, breaches=breaches, calls=calls,
                library=len(library), reuses=reuses,
                first50=resolved_first50, last50=resolved_last50,
                byproduct_usd=round(len(library)*TOOL_VALUE + avoided, 1))

def run_central_or_4cell(seed, lam, n_agents, shared):
    rng = random.Random(seed + 3333)
    incidents = gen(seed, lam)
    boards = {} if shared else {a: {} for a in range(n_agents)}
    calls = resolved = reuses = builds = 0
    library = set(); queue = []
    for t in range(T):
        for ic in incidents:
            if ic["born"] == t: queue.append(dict(ic))
        queue.sort(key=lambda q: q["deadline"])
        for a in range(n_agents):
            if not queue or calls >= CALL_BUDGET: break
            ic = queue.pop(0)
            board = boards if shared else boards[a]
            s = board.get(ic["fam"], 0.0)
            if s > 0:
                calls += REUSE_CALLS
                if rng.random() < s:
                    resolved += 1; reuses += 1
                    board[ic["fam"]] = min(S_MAX4, s + STRENGTHEN4)
                    library.add(ic["fam"])
                else:
                    ic["deadline"] += 2; queue.append(ic)
            else:
                if calls + BUILD_CALLS > CALL_BUDGET: queue.append(ic); continue
                calls += BUILD_CALLS; builds += 1
                board[ic["fam"]] = 1.0; library.add(ic["fam"]); resolved += 1
        if shared:
            for f in list(boards):
                boards[f] *= EVAP4
                if boards[f] < 0.05: del boards[f]
        queue = [q for q in queue if t <= q["deadline"]]
    arrived = len(incidents); breaches = arrived - resolved
    avoided = reuses * (BUILD_CALLS - REUSE_CALLS) * CALL_COST
    return dict(arrived=arrived, resolved=resolved, breaches=breaches, calls=calls,
                library=len(library), reuses=reuses, first50=0, last50=0,
                byproduct_usd=round(len(library)*TOOL_VALUE + avoided, 1))

def agg(runs):
    out = {}
    for k in ["arrived","resolved","breaches","calls","library","reuses","byproduct_usd","first50","last50"]:
        vals = [r[k] for r in runs]
        out[k] = {"mean": round(statistics.mean(vals),1), "sd": round(statistics.pstdev(vals),1)}
    return out

SEEDS = range(30)
report = {}
for lam in [0.5, 1.5, 3.0]:
    A = agg([run_ants(s, lam) for s in SEEDS])
    C = agg([run_central_or_4cell(s, lam, 1, False) for s in SEEDS])
    F = agg([run_central_or_4cell(s, lam, 4, True) for s in SEEDS])
    report[str(lam)] = {"ants30": A, "central": C, "cells4": F,
        "sla_value_ants_vs_central": round((C["breaches"]["mean"] - A["breaches"]["mean"]) * BREACH_COST, 1),
        "sla_value_ants_vs_4cell": round((F["breaches"]["mean"] - A["breaches"]["mean"]) * BREACH_COST, 1)}
# sensitivity at high load
sens = {}
for evap in [0.95, 0.99]:
    for eps in [0.05, 0.10, 0.20]:
        r = agg([run_ants(s, 3.0, eps=eps, evap=evap) for s in SEEDS])
        sens[f"evap={evap},eps={eps}"] = {"breaches": r["breaches"], "resolved": r["resolved"], "library": r["library"]}
report["sensitivity_lam3"] = sens
print(json.dumps(report, indent=1))
