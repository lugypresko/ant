#!/usr/bin/env python3
# Experiment 3b (scripted, $0): blank-environment nest.
# Ants invent arbitrary labeled artifacts with NO SDLC vocabulary; the only
# reward is downstream coding-task outcomes. Latent needs: 6 'sdlc-like',
# 6 'novel'. Scripted version tests reinforcement dynamics (convergence,
# coverage, what selection favors), not semantics.
import json, random, hashlib

NEEDS = ["versioning","verification","gating","reusable_tools","conventions","documentation",
         "pattern_cache","error_atlas","snippet_farm","prompt_scaffolds","example_bank","risk_flags"]
SDLC = set(NEEDS[:6])
ALPHABET = "abcdefgh"
WINDOW, TICKS = 10, 100

def label_needs(label):
    h = hashlib.sha256(label.encode()).digest()
    return {NEEDS[h[0] % len(NEEDS)]: (h[2] % 100) / 100.0 * 0.55}

def rand_label(rng): return "".join(rng.choice(ALPHABET) for _ in range(6))
def mutate(label, rng):
    i = rng.randrange(len(label))
    return label[:i] + rng.choice(ALPHABET) + label[i+1:]

class Task:
    def __init__(self, rng):
        self.w = {}
        for n in rng.sample(NEEDS, rng.choice([3,4])):
            self.w[n] = rng.uniform(0.25, 0.45)

def eval_tasks(artifacts, tasks, rng, base=0.05):
    # pass prob per task from best-artifact coverage of its needs
    passes = 0
    for t in tasks:
        q = base
        for n, w in t.w.items():
            best = max((a["needs"].get(n, 0) for a in artifacts.values()), default=0)
            q += w * best
        if rng.random() < min(q, 0.97): passes += 1
    return passes / len(tasks)

def run_arm(arm, nants, seed):
    rng = random.Random(seed)
    reward_tasks = [Task(rng) for _ in range(10)]
    eval_taskset = [Task(random.Random(seed+777)) for _ in range(20)]
    arts = {}   # label -> {needs, pheromone, born}
    hist, last_score = [], 0.0
    for t in range(TICKS):
        for _ in range(nants):
            if arm == "blank": break
            if arm == "classic":
                pool = [l for l in arts if set(arts[l]["needs"]) & SDLC]
                if not arts or rng.random() < 0.3:
                    # biased: only sdlc-like labels admitted (pre-imposed frame)
                    while True:
                        l = rand_label(rng)
                        if set(label_needs(l)) & SDLC: break
                    arts.setdefault(l, {"needs": label_needs(l), "pher": 0.0, "born": t})
                elif pool:
                    l = rng.choice(pool); nl = mutate(l, rng)
                    if set(label_needs(nl)) & SDLC:
                        arts.setdefault(nl, {"needs": label_needs(nl), "pher": arts[l]["pher"]*0.5, "born": t})
            elif arm in ("emergent", "central"):
                nact = nants if arm == "emergent" else 1
                if _ > 0 and arm == "central": break
                top = sorted(arts, key=lambda l: -arts[l]["pher"])[:5]
                r = rng.random()
                if not arts or r < 0.25:
                    l = rand_label(rng)
                    arts.setdefault(l, {"needs": label_needs(l), "pher": 0.0, "born": t})
                elif r < 0.75 and top:
                    l = rng.choice(top); nl = mutate(l, rng)
                    arts.setdefault(nl, {"needs": label_needs(nl), "pher": arts[l]["pher"]*0.6, "born": t})
                elif top:
                    arts[rng.choice(top)]["pher"] += 0.2  # reinforce
        if t % WINDOW == WINDOW-1 or t == TICKS-1:
            score = eval_tasks(arts, reward_tasks, rng)
            delta = score - last_score
            recent = [l for l, a in arts.items() if a["born"] > t - WINDOW]
            if delta > 0 and recent:
                for l in recent: arts[l]["pher"] += delta / len(recent)
            for a in arts.values(): a["pher"] *= 0.9  # evaporation
            hist.append(round(score, 3)); last_score = score
            if len(arts) > 30:  # pruning: weak artifacts forgotten
                for l in sorted(arts, key=lambda l: arts[l]["pher"])[:len(arts)-30]: del arts[l]
    final = eval_tasks(arts, eval_taskset, rng)
    top10 = sorted(arts, key=lambda l: -arts[l]["pher"])[:10]
    sdlc_share = sum(1 for l in top10 if max(arts[l]["needs"], key=arts[l]["needs"].get) in SDLC) / max(len(top10),1)
    cov = len({n for a in arts.values() for n in a["needs"]})
    t90 = next((i*WINDOW+WINDOW-1 for i, s in enumerate(hist) if s >= 0.9*hist[-1]), None) if hist else None
    return {"final_eval": round(final,3), "hist": hist, "n_artifacts": len(arts),
            "coverage": f"{cov}/12", "top10_sdlc_share": round(sdlc_share,2), "t90": t90}

import statistics as st
def agg(runs):
    fe = [r["final_eval"] for r in runs]
    t9 = [r["t90"] for r in runs if r["t90"] is not None]
    sh = [r["top10_sdlc_share"] for r in runs]
    return {"final_eval_mean": round(st.mean(fe),3), "final_eval_sd": round(st.pstdev(fe),3),
            "t90_mean": round(st.mean(t9),1) if t9 else None,
            "top10_sdlc_share_mean": round(st.mean(sh),2),
            "coverage_mean": round(st.mean(int(r["coverage"].split("/")[0]) for r in runs),1),
            "n_artifacts_mean": round(st.mean(r["n_artifacts"] for r in runs),1),
            "sample_hist": runs[0]["hist"]}
out = {}
for arm in ("emergent", "classic", "central", "blank"):
    out[arm] = agg([run_arm(arm, 30, 100+s) for s in range(8)])
out["scale_emergent"] = {str(n): agg([run_arm("emergent", n, 200+s) for s in range(8)]) for n in (10, 30, 100, 300)}
print(json.dumps(out, indent=1))
json.dump(out, open("run/nest_blank_sim.json", "w"), indent=1)
