#!/usr/bin/env python3
"""
Nest-building simulation (scripted, $0, no model calls).
Ants build the nest = factory for code production: 6 components
(repo, tests, ci_gates, tool_library, conventions, docs), maturity 0..3, with bit-rot defects.
After 200 build ticks, a fixed batch of 100 simulated coding tasks runs through the factory:
pass rate, integration time, defect escape. Arms: faithful ants (spatial), ants flat,
4-cell engineered, central. Same budget. 30 seeds.
"""
import random, statistics, json, math

COMPS = ["repo","tests","ci_gates","tool_library","conventions","docs"]
ZONE_OF = {c: i for i, c in enumerate(COMPS)}   # components live in zones 0..5 of 10
ZONES = 10
MAXM = 3
T, CALL_BUDGET = 200, 1200
BITROT_P = 0.01
# ant params
DECAY_S, DECAY_A, DECAY_N, DECAY_Z = 0.99, 0.95, 0.97, 0.98
DEP_OK, DEP_FAIL_N, DEP_SIGHT_A, DEP_BREAK_A = 0.2, 0.10, 0.15, 0.30
CAP = 3.0; EPS = 0.10; LIB_THRESH = 1.0
START_ANTS, FOOD_PER_SUCCESS, SPAWN_COST, MAX_ANTS, DEATH_P = 5, 1, 10, 60, 0.005
TH_MU, TH_SIGMA = -0.5, 0.6
# engineered arms
EVAP4, STRENGTHEN4, S_MAX4 = 0.995, 0.15, 0.98
BUILD_CALLS, REUSE_CALLS = 8, 1
# eval + pricing (assumptions)
EVAL_TASKS = 100
PASS_BASE = 0.35
DEFECT_RATE = 0.15
VALUE_PASS, COST_ESCAPE, COST_TIME, CALL_COST = 100.0, 150.0, 5.0, 0.04

def gen_eval(seed):
    rng = random.Random(seed + 999)
    tasks = []
    for i in range(EVAL_TASKS):
        k = rng.randint(2, 4)
        reqs = {c: rng.randint(1, 3) for c in rng.sample(COMPS, k)}
        tasks.append(reqs)
    return tasks

def evaluate(seed, maturity, defects, calls_used):
    tasks = gen_eval(seed)
    passed = escaped = 0; total_time = 0
    rng = random.Random(seed + 555)
    for reqs in tasks:
        p = PASS_BASE
        broken = False
        extra = 0
        for c, rq in reqs.items():
            m = maturity.get(c, 0)
            p += 0.10 * min(m, rq) / rq
            if m < rq: extra += (rq - m)
            if c in defects: broken = True
        if broken: p *= 0.5
        p = min(0.97, p)
        total_time += 1 + extra
        if rng.random() < p:
            passed += 1
            if rng.random() < DEFECT_RATE:
                detect = 0.3 + 0.11 * maturity.get("tests", 0) + 0.11 * maturity.get("ci_gates", 0)
                if rng.random() >= min(0.96, detect): escaped += 1
    value = passed * VALUE_PASS - escaped * COST_ESCAPE - (total_time - EVAL_TASKS) * COST_TIME - calls_used * CALL_COST
    return dict(passed=passed, pass_rate=round(passed / EVAL_TASKS, 3),
                escaped=escaped, avg_time=round(total_time / EVAL_TASKS, 2),
                value_usd=round(value, 1))

def new_ant(rng):
    return {"state": "searching", "carry": None, "ok": False, "zone": 0,
            "theta": rng.lognormvariate(TH_MU, TH_SIGMA), "done": 0}

def run_ants(seed, spatial, bitrot=BITROT_P):
    rng = random.Random(seed + 7777)
    maturity = {c: 0 for c in COMPS}; defects = set()
    ws, wa, wn, wz = {}, {}, {}, {}
    ants = [new_ant(rng) for _ in range(START_ANTS)]
    food = 0.0; calls = 0
    library = set(); pop_track = {}
    for t in range(T):
        for c in COMPS:  # bit rot
            if maturity[c] > 0 and c not in defects and rng.random() < bitrot:
                defects.add(c); wa[c] = min(CAP, wa.get(c, 0.0) + DEP_BREAK_A)
        for a in ants:
            if a["state"] == "returning":
                c = a["carry"]
                if a["ok"]:
                    ws[c] = min(CAP, ws.get(c, 0.0) + DEP_OK); food += FOOD_PER_SUCCESS
                    if ws[c] >= LIB_THRESH: library.add(c)
                    wz[a["zone"]] = min(CAP, wz.get(a["zone"], 0.0) + 0.2)
                else:
                    wn[c] = min(CAP, wn.get(c, 0.0) + DEP_FAIL_N)
                a["state"] = "searching"; a["carry"] = None; a["ok"] = False
                continue
            if spatial:
                visible = [c for c in COMPS if min(abs(ZONE_OF[c]-a["zone"]), ZONES-abs(ZONE_OF[c]-a["zone"])) <= 1]
            else:
                visible = list(COMPS)
            for c in visible:  # local sensing of broken gates
                if c in defects:
                    wa[c] = min(CAP, wa.get(c, 0.0) + DEP_SIGHT_A)
            if not visible:
                if spatial:
                    l, r = (a["zone"]-1) % ZONES, (a["zone"]+1) % ZONES
                    a["zone"] = rng.choices([l, r], weights=[wz.get(l,0.0)+0.05, wz.get(r,0.0)+0.05])[0]
                continue
            if calls >= CALL_BUDGET: continue
            def score(c):
                need = (MAXM - maturity[c]) / MAXM + (1.0 if c in defects else 0.0)
                return max(0.02, need) * (1 + ws.get(c,0.0)) * (1 + 2*wa.get(c,0.0)) * (1 - min(0.8, wn.get(c,0.0)))
            if rng.random() < EPS:
                c = rng.choice(visible)
            else:
                c = rng.choices(visible, weights=[score(x) for x in visible])[0]
            if score(c) <= a["theta"]:
                continue
            calls += 1; a["zone"] = ZONE_OF[c]
            p = min(0.9, max(0.3, 0.3 + 0.4 * ws.get(c, 0.0)))
            ok = rng.random() < p
            if ok:
                a["done"] += 1
                if c in defects: defects.discard(c)
                elif maturity[c] < MAXM: maturity[c] += 1
            a["state"] = "returning"; a["carry"] = c; a["ok"] = ok
        while food >= SPAWN_COST and len(ants) < MAX_ANTS:
            food -= SPAWN_COST; ants.append(new_ant(rng))
        ants = [a for a in ants if rng.random() >= DEATH_P]
        for d, dec in ((ws,DECAY_S),(wa,DECAY_A),(wn,DECAY_N),(wz,DECAY_Z)):
            for f in list(d):
                d[f] *= dec
                if d[f] < 0.02: del d[f]
        if t in (0,50,100,150,199): pop_track[t] = len(ants)
    ev = evaluate(seed, maturity, defects, calls)
    done = sorted((a["done"] for a in ants), reverse=True)
    top20 = sum(done[:max(1,len(done)//5)]); tot = sum(done) or 1
    return dict(maturity=dict(maturity), defects_left=len(defects), calls=calls,
                library=len(library), final_pop=len(ants), pop=pop_track,
                dol_top20=round(top20/tot,3), **ev)

def run_engineered(seed, n_agents, shared, bitrot=BITROT_P):
    rng = random.Random(seed + 3333)
    maturity = {c: 0 for c in COMPS}; defects = set()
    boards = {} if shared else {a: {} for a in range(n_agents)}
    calls = 0; library = set()
    for t in range(T):
        for c in COMPS:
            if maturity[c] > 0 and c not in defects and rng.random() < bitrot:
                defects.add(c)
        for a in range(n_agents):
            if calls >= CALL_BUDGET: break
            # greedy: repair defects first, then least mature
            targets = sorted(defects, key=lambda c: -1) if defects else None
            if defects:
                c = sorted(defects)[0]
            else:
                c = min(COMPS, key=lambda x: maturity[x])
                if maturity[c] >= MAXM: continue
            board = boards if shared else boards[a]
            s = board.get(c, 0.0)
            if s > 0:
                calls += REUSE_CALLS
                if rng.random() < s:
                    board[c] = min(S_MAX4, s + STRENGTHEN4); library.add(c)
                    if c in defects: defects.discard(c)
                    elif maturity[c] < MAXM: maturity[c] += 1
            else:
                if calls + BUILD_CALLS > CALL_BUDGET: continue
                calls += BUILD_CALLS; board[c] = 1.0; library.add(c)
                if c in defects: defects.discard(c)
                elif maturity[c] < MAXM: maturity[c] += 1
        if shared:
            for f in list(boards):
                boards[f] *= EVAP4
                if boards[f] < 0.05: del boards[f]
    ev = evaluate(seed, maturity, defects, calls)
    return dict(maturity=dict(maturity), defects_left=len(defects), calls=calls,
                library=len(library), final_pop=n_agents, pop={}, dol_top20=0.0, **ev)

def agg(runs, ant=False):
    out = {}
    for k in ["calls","library","defects_left","passed","escaped","avg_time","pass_rate","value_usd"]:
        vals = [r[k] for r in runs]
        out[k] = {"mean": round(statistics.mean(vals),2), "sd": round(statistics.pstdev(vals),2)}
    if ant:
        for k in ["final_pop","dol_top20"]:
            vals=[r[k] for r in runs]
            out[k]={"mean": round(statistics.mean(vals),2), "sd": round(statistics.pstdev(vals),2)}
        out["pop_over_time"] = {str(t): round(statistics.mean([r["pop"][t] for r in runs]),1) for t in (0,50,100,150,199)}
        out["maturity"] = {c: round(statistics.mean([r["maturity"][c] for r in runs]),2) for c in COMPS}
    else:
        out["maturity"] = {c: round(statistics.mean([r["maturity"][c] for r in runs]),2) for c in COMPS}
    return out

SEEDS = range(30)
report = {}
for br in (0.01, 0.03, 0.08):
    report[str(br)] = {
     "ants_spatial": agg([run_ants(s, True, br)  for s in SEEDS], ant=True),
     "ants_flat":    agg([run_ants(s, False, br) for s in SEEDS], ant=True),
     "cells4":       agg([run_engineered(s, 4, True, br)  for s in SEEDS]),
     "central":      agg([run_engineered(s, 1, False, br) for s in SEEDS]),
    }
print(json.dumps(report, indent=1))
