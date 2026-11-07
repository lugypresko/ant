#!/usr/bin/env python3
"""
Faithful ant colony v3: queen = population factory (no coordination, no task assignment).
Start 5 ants. Each successful resolution brings 1 food. Food bank >= 10 -> queen spawns
1 ant (costs 10 food), cap 60. Each ant dies each tick with prob 0.005 (fixed rate).
Reports population over time per load. 30 seeds, 3 loads, vs central and 4-cell arms.
"""
import random, statistics, json, math

FAMILIES = ["drop_multiline","drop_nonascii","drop_long","dup_records",
            "ts_shift","bad_encoding","schema_drift","partial_write"]
FAMILY_W = [8,6,5,4,3,2,1,1]
T, SLA, CALL_BUDGET = 200, 8, 1200
BUILD_CALLS, REUSE_CALLS = 8, 1
BREACH_COST, TOOL_VALUE, CALL_COST = 50.0, 120.0, 0.04
EVAP_A, DEPOSIT_OK, DEPOSIT_FAIL = 0.99, 0.2, 0.03
EPS, WINDOW, LIB_THRESH = 0.10, 5, 1.0
START_ANTS, FOOD_PER_SUCCESS, SPAWN_COST, MAX_ANTS, DEATH_P = 5, 1, 10, 60, 0.005
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

def run_ants_queen(seed, lam):
    rng = random.Random(seed + 7777)
    incidents = gen(seed, lam)
    w = {}
    ants = [{"state": "searching", "carry": None, "ok": False} for _ in range(START_ANTS)]
    food = 0.0
    calls = resolved = reuses = 0
    library = set(); queue = []
    pop_track = {}
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
                if a.get("ok"): food += FOOD_PER_SUCCESS
                a["state"] = "searching"; a["carry"] = None; a["ok"] = False
            elif a["state"] == "searching" and queue and calls < CALL_BUDGET:
                visible = queue[:WINDOW]
                if rng.random() < eps_or(EPS) or all(w.get(v["fam"],0.0)==0 for v in visible):
                    ic = rng.choice(visible)
                else:
                    weights = [w.get(v["fam"], 0.0) + 0.05 for v in visible]
                    ic = rng.choices(visible, weights=weights)[0]
                queue.remove(ic)
                calls += 1
                p = min(0.95, max(0.25, 0.25 + 0.5 * w.get(ic["fam"], 0.0)))
                ok = rng.random() < p
                if ok:
                    resolved += 1
                    if ic["fam"] in library: reuses += 1
                else:
                    ic["deadline"] += 2; queue.append(ic)
                a["state"] = "returning"; a["carry"] = ic["fam"]; a["ok"] = ok
        # queen: population factory driven by food only
        while food >= SPAWN_COST and len(ants) < MAX_ANTS:
            food -= SPAWN_COST
            ants.append({"state": "searching", "carry": None, "ok": False})
        # fixed death rate
        ants = [a for a in ants if rng.random() >= DEATH_P]
        for f in list(w):
            w[f] *= EVAP_A
            if w[f] < 0.02: del w[f]
        if t in (0, 50, 100, 150, 199):
            pop_track[t] = len(ants)
    arrived = len(incidents); breaches = arrived - resolved
    avoided = reuses * (BUILD_CALLS - REUSE_CALLS) * CALL_COST
    return dict(arrived=arrived, resolved=resolved, breaches=breaches, calls=calls,
                library=len(library), reuses=reuses, pop=pop_track,
                final_pop=len(ants),
                byproduct_usd=round(len(library)*TOOL_VALUE + avoided, 1))

def eps_or(e): return e

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
                    board[ic["fam"]] = min(S_MAX4, s + STRENGTHEN4); library.add(ic["fam"])
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
                library=len(library), reuses=reuses,
                byproduct_usd=round(len(library)*TOOL_VALUE + avoided, 1))

def agg(runs, with_pop=False):
    out = {}
    for k in ["arrived","resolved","breaches","calls","library","reuses","byproduct_usd"]:
        vals = [r[k] for r in runs]
        out[k] = {"mean": round(statistics.mean(vals),1), "sd": round(statistics.pstdev(vals),1)}
    if with_pop:
        out["pop_over_time"] = {str(t): round(statistics.mean([r["pop"][t] for r in runs]),1) for t in (0,50,100,150,199)}
        vals=[r["final_pop"] for r in runs]
        out["final_pop"]={"mean": round(statistics.mean(vals),1), "sd": round(statistics.pstdev(vals),1)}
    return out

SEEDS = range(30)
report = {}
for lam in [0.5, 1.5, 3.0]:
    A = agg([run_ants_queen(s, lam) for s in SEEDS], with_pop=True)
    C = agg([run_central_or_4cell(s, lam, 1, False) for s in SEEDS])
    F = agg([run_central_or_4cell(s, lam, 4, True) for s in SEEDS])
    report[str(lam)] = {"ants_queen": A, "central": C, "cells4": F,
        "sla_value_ants_vs_central": round((C["breaches"]["mean"] - A["breaches"]["mean"]) * BREACH_COST, 1),
        "sla_value_ants_vs_4cell": round((F["breaches"]["mean"] - A["breaches"]["mean"]) * BREACH_COST, 1)}
print(json.dumps(report, indent=1))
