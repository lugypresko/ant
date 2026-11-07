#!/usr/bin/env python3
"""
Faithful ant colony v4: queen (population factory), heterogeneous response thresholds
(emergent division of labor), three pheromone types (success, alarm, negative),
optional spatial layer (toggle). No model calls. 30 seeds, 3 loads.
"""
import random, statistics, json, math

FAMILIES = ["drop_multiline","drop_nonascii","drop_long","dup_records",
            "ts_shift","bad_encoding","schema_drift","partial_write"]
FAMILY_W = [8,6,5,4,3,2,1,1]
T, SLA, CALL_BUDGET = 200, 8, 1200
BUILD_CALLS, REUSE_CALLS = 8, 1
BREACH_COST, TOOL_VALUE, CALL_COST = 50.0, 120.0, 0.04
# pheromone params
DECAY_S, DECAY_A, DECAY_N = 0.99, 0.95, 0.97
DEP_OK, DEP_FAIL_N, DEP_BREACH_A, DEP_SIGHT_A = 0.2, 0.10, 0.30, 0.15
CAP = 3.0
EPS, WINDOW, LIB_THRESH = 0.10, 5, 1.0
# queen
START_ANTS, FOOD_PER_SUCCESS, SPAWN_COST, MAX_ANTS, DEATH_P = 5, 1, 10, 60, 0.005
# thresholds: lognormal, median ~0.6
TH_MU, TH_SIGMA = -0.5, 0.6
ZONES = 10
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
            inc.append({"id": iid, "fam": fam, "born": t, "deadline": t + SLA,
                        "zone": rng.randrange(ZONES)}); iid += 1
    return inc

def new_ant(rng):
    return {"state": "searching", "carry": None, "ok": False, "zone": 0,
            "theta": rng.lognormvariate(TH_MU, TH_SIGMA), "done": 0}

def run_ants(seed, lam, spatial):
    rng = random.Random(seed + 7777)
    incidents = gen(seed, lam)
    ws, wa, wn = {}, {}, {}
    wz = {}
    ants = [new_ant(rng) for _ in range(START_ANTS)]
    food = 0.0; calls = resolved = reuses = 0
    library = set(); queue = []; pop_track = {}
    for t in range(T):
        for ic in incidents:
            if ic["born"] == t: queue.append(dict(ic))
        queue.sort(key=lambda q: q["deadline"])
        still = []
        for q in queue:
            if t <= q["deadline"]: still.append(q)
            else: wa[q["fam"]] = min(CAP, wa.get(q["fam"], 0.0) + DEP_BREACH_A)  # breach -> alarm
        queue = still
        for a in ants:
            if a["state"] == "returning":
                fam = a["carry"]
                if a["ok"]:
                    ws[fam] = min(CAP, ws.get(fam, 0.0) + DEP_OK); food += FOOD_PER_SUCCESS
                    if ws[fam] >= LIB_THRESH: library.add(fam)
                    wz[a["zone"]] = min(CAP, wz.get(a["zone"], 0.0) + 0.2)
                else:
                    wn[fam] = min(CAP, wn.get(fam, 0.0) + DEP_FAIL_N)
                a["state"] = "searching"; a["carry"] = None; a["ok"] = False
                continue
            # searching
            if spatial:
                visible = [q for q in queue if min(abs(q["zone"]-a["zone"]), ZONES-abs(q["zone"]-a["zone"])) <= 1]
            else:
                visible = queue[:WINDOW]
            # near-deadline sighting deposits alarm (local sensing, free)
            for q in visible:
                if q["deadline"] - t <= 2:
                    wa[q["fam"]] = min(CAP, wa.get(q["fam"], 0.0) + DEP_SIGHT_A)
            if not visible:
                if spatial:
                    left = (a["zone"] - 1) % ZONES; right = (a["zone"] + 1) % ZONES
                    a["zone"] = rng.choices([left, right],
                        weights=[wz.get(left, 0.0) + 0.05, wz.get(right, 0.0) + 0.05])[0]
                continue
            if calls >= CALL_BUDGET: continue
            def score(q):
                f = q["fam"]
                return max(0.05, (1 + ws.get(f,0.0)) * (1 + 2*wa.get(f,0.0)) * (1 - min(0.8, wn.get(f,0.0))))
            if rng.random() < EPS or all(score(v) <= 1.0 for v in visible):
                ic = rng.choice(visible)
            else:
                ic = rng.choices(visible, weights=[score(v) for v in visible])[0]
            if score(ic) <= a["theta"]:
                continue  # stimulus below personal threshold: ant stays put (division of labor)
            queue.remove(ic); calls += 1; a["zone"] = ic["zone"]
            p = min(0.95, max(0.25, 0.25 + 0.5 * ws.get(ic["fam"], 0.0)))
            ok = rng.random() < p
            if ok:
                resolved += 1; a["done"] += 1
                if ic["fam"] in library: reuses += 1
            else:
                ic["deadline"] += 2; queue.append(ic)
            a["state"] = "returning"; a["carry"] = ic["fam"]; a["ok"] = ok
        while food >= SPAWN_COST and len(ants) < MAX_ANTS:
            food -= SPAWN_COST; ants.append(new_ant(rng))
        ants = [a for a in ants if rng.random() >= DEATH_P]
        for d, dec in ((ws,DECAY_S),(wa,DECAY_A),(wn,DECAY_N),(wz,0.98)):
            for f in list(d):
                d[f] *= dec
                if d[f] < 0.02: del d[f]
        if t in (0,50,100,150,199): pop_track[t] = len(ants)
    arrived = len(incidents); breaches = arrived - resolved
    avoided = reuses * (BUILD_CALLS - REUSE_CALLS) * CALL_COST
    done = sorted((a["done"] for a in ants), reverse=True)
    top20 = sum(done[:max(1,len(done)//5)]); tot = sum(done) or 1
    return dict(arrived=arrived, resolved=resolved, breaches=breaches, calls=calls,
                library=len(library), reuses=reuses, pop=pop_track, final_pop=len(ants),
                dol_top20_share=round(top20/tot, 3),
                byproduct_usd=round(len(library)*TOOL_VALUE + avoided, 1))

def run_central_or_4cell(seed, lam, n_agents, shared):
    rng = random.Random(seed + 3333)
    incidents = gen(seed, lam)
    boards = {} if shared else {a: {} for a in range(n_agents)}
    calls = resolved = reuses = 0
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
                calls += BUILD_CALLS
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

def agg(runs, ant=False):
    out = {}
    keys = ["arrived","resolved","breaches","calls","library","reuses","byproduct_usd"]
    if ant: keys += ["final_pop","dol_top20_share"]
    for k in keys:
        vals = [r[k] for r in runs]
        out[k] = {"mean": round(statistics.mean(vals),1), "sd": round(statistics.pstdev(vals),1)}
    if ant:
        out["pop_over_time"] = {str(t): round(statistics.mean([r["pop"][t] for r in runs]),1) for t in (0,50,100,150,199)}
    return out

SEEDS = range(30)
report = {}
for lam in [0.5, 1.5, 3.0]:
    A  = agg([run_ants(s, lam, False) for s in SEEDS], ant=True)
    AS = agg([run_ants(s, lam, True)  for s in SEEDS], ant=True)
    C  = agg([run_central_or_4cell(s, lam, 1, False) for s in SEEDS])
    F  = agg([run_central_or_4cell(s, lam, 4, True)  for s in SEEDS])
    report[str(lam)] = {"ants_full": A, "ants_spatial": AS, "central": C, "cells4": F,
        "sla_ants_vs_central": round((C["breaches"]["mean"]-A["breaches"]["mean"])*BREACH_COST,1),
        "sla_ants_vs_4cell": round((F["breaches"]["mean"]-A["breaches"]["mean"])*BREACH_COST,1),
        "sla_spatial_vs_flat": round((A["breaches"]["mean"]-AS["breaches"]["mean"])*BREACH_COST,1)}
sens = {}
import copy
def run_ants_p(seed, lam, spatial, eps, decs):
    global EPS, DECAY_S
    old_eps, old_decs = EPS, DECAY_S
    globals()['EPS'] = eps; globals()['DECAY_S'] = decs
    r = run_ants(seed, lam, spatial)
    globals()['EPS'] = old_eps; globals()['DECAY_S'] = old_decs
    return r
for decs in (0.95, 0.99):
    for eps in (0.05, 0.10, 0.20):
        rr = agg([run_ants_p(s, 3.0, True, eps, decs) for s in SEEDS], ant=True)
        sens[f"decay_s={decs},eps={eps}"] = {"breaches": rr["breaches"], "library": rr["library"], "final_pop": rr["final_pop"]}
report["sensitivity_spatial_lam3"] = sens
print(json.dumps(report, indent=1))
