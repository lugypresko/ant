#!/usr/bin/env python3
# Experiment 4: pure-code ants (state machine, pheromone field with evaporation,
# response thresholds, queen = spawn-rate factory, type-locality) routing
# one-call LLM workers. No LLM inside ant decisions.
# Family A: hard coding tasks. Family B: requirement decomposition.
# Arms: colony, central, pool (fixed 4 generic), cells (4 fixed specialists),
# blueprint (deterministic skeleton). Equal call budget per arm.
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nest_llm as B
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tasks_hard import HARD_TASKS
from ground_truth import REQUIREMENTS, score_decomposition
from ground_truth_hard import HARD_REQUIREMENTS, score_hard

EVAP = 0.9
MAXRETRY = 3
TYPES = {  # task id -> type tag for specialization
 "h01":"parse","h07":"parse","h06":"parse","h09":"algo","h03":"algo","h08":"algo",
 "h05":"algo","h04":"parse","h02":"struct","h10":"struct"}

CF_KEY = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CF_ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CF_MODEL = "@cf/meta/llama-3.1-8b-instruct-awq"
def cf_call(prompt, max_tokens=1500):
    import urllib.request
    key, acct = CF_KEY, CF_ACCOUNT
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{CF_MODEL}"
    body = {"messages": [{"role": "system", "content": B.SYS_CODE}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    r = json.load(urllib.request.urlopen(req, timeout=90))
    B.STATE["calls_today"] += 1
    B.LOG.write(json.dumps({"ts": time.time(), "ok": True, "provider": "cloudflare"}) + "\n"); B.LOG.flush()
    time.sleep(1.0)
    return r["result"]["response"]
USE_CF = bool(CF_KEY and CF_ACCOUNT)
_call_counter = [0]
def worker_call(prompt, max_tokens=1500):
    _call_counter[0] += 1
    if USE_CF and _call_counter[0] % 2 == 0:
        try:
            return cf_call(prompt, max_tokens)
        except Exception:
            pass  # fall back to Gemini
    return B.llm(prompt, B.SYS_CODE, max_tokens=max_tokens)

def attempt_task(task, context=""):
    prompt = (context + "\n\n" if context else "") + f"TASK: {task['spec']}\nWrite the function or class `{task['entry']}`."
    code = B.extract_code(worker_call(prompt))
    return B.run_code(code, task["tests"], task["entry"])

class Worker:
    def __init__(self, wid):
        self.id = wid; self.pref = {}; self.solved = 0; self.calls = 0
    def threshold(self, ttype):
        return 1.0 - 0.3 * min(self.pref.get(ttype, 0.0), 2.0)  # specialists take matching tasks more readily

def run_coding_arm(arm, tasks, seed, budget):
    rng = random.Random(seed)
    calls = solved = 0
    results = {}
    queue = list(tasks)
    attempts = {t["id"]: 0 for t in tasks}
    if arm == "colony":
        workers = [Worker(0)]
        spawn_hist = [(0, 1)]
        backlog_ph = 0.0
        t = 0
        while queue and calls < budget:
            t += 1
            backlog_ph = backlog_ph * EVAP + len(queue) * 0.5
            # queen: spawn-rate factory
            if backlog_ph > 3.0 and len(workers) < 12:
                workers.append(Worker(len(workers))); spawn_hist.append((t, len(workers)))
            idle = [w for w in workers if w.solved == 0 and len(workers) > 1 and backlog_ph < 1.0]
            for w in idle: workers.remove(w)
            for w in list(workers):
                if not queue or calls >= budget: break
                # response threshold with locality: prefer matching type
                cands = sorted(queue, key=lambda x: w.threshold(TYPES.get(x["id"], "algo")) - rng.random()*0.4)
                task = cands[0]
                if w.threshold(TYPES.get(task["id"], "algo")) > 1.3 and len(queue) > 1 and rng.random() < 0.5:
                    continue  # worker idles if nothing matches its threshold
                queue.remove(task)
                calls += 1; w.calls += 1; attempts[task["id"]] += 1
                ok = attempt_task(task)
                if ok:
                    solved += 1; results[task["id"]] = True; w.solved += 1
                    tt = TYPES.get(task["id"], "algo"); w.pref[tt] = w.pref.get(tt, 0) + 1
                else:
                    if attempts[task["id"]] < MAXRETRY: queue.append(task)
                    else: results[task["id"]] = False
        return {"solved": solved, "calls": calls, "results": results,
                "workers_final": len(workers), "spawn_hist": spawn_hist,
                "calls_per_solved": round(calls / max(solved, 1), 2)}
    # non-adaptive arms
    if arm == "central": nwork, special = 1, False
    elif arm == "pool": nwork, special = 4, False
    elif arm == "cells": nwork, special = 4, True
    elif arm == "blueprint": nwork, special = 1, False
    workers = [Worker(i) for i in range(nwork)]
    for task in queue:
        while attempts[task["id"]] < MAXRETRY and calls < budget and task["id"] not in results:
            if special:
                tt = TYPES.get(task["id"], "algo")
                w = workers[hash(tt) % 4]
            else:
                w = workers[attempts[task["id"]] % nwork]
            calls += 1; w.calls += 1; attempts[task["id"]] += 1
            if arm == "blueprint":
                # deterministic skeleton: implement, then one guided fix if needed
                ok = attempt_task(task)
                if not ok and attempts[task["id"]] < MAXRETRY and calls < budget:
                    calls += 1; attempts[task["id"]] += 1
                    fix_prompt = f"TASK: {task['spec']}\nPrevious attempt failed its tests. Write a corrected `{task['entry']}`."
                    ok = B.run_code(B.extract_code(worker_call(fix_prompt)), task["tests"], task["entry"])
            else:
                ok = attempt_task(task)
            if ok:
                solved += 1; results[task["id"]] = True; w.solved += 1
            elif attempts[task["id"]] >= MAXRETRY:
                results[task["id"]] = False
    return {"solved": solved, "calls": calls, "results": results,
            "calls_per_solved": round(calls / max(solved, 1), 2)}

# ---------- Family B: requirement decomposition ----------
SYS_DECOMP = ("You break one requirement or sub-requirement into 2 to 4 smaller concrete parts. "
 "Reply ONLY with a JSON array of short strings, each a self-contained part. No prose.")
CELL_ROLES = (
    "Focus on data, persistence, and state transitions.",
    "Focus on APIs, user workflows, and integrations.",
    "Focus on validation, permissions, and failure handling.",
    "Focus on operations, observability, and recovery.",
)
LEAF_MAX_WORDS = 12

def is_leaf(text):
    return len(text.split()) <= LEAF_MAX_WORDS

def decompose_call(chunk, role=None):
    prompt = f"Break into smaller parts: {chunk}"
    if role:
        prompt += f"\nPerspective: {role}"
    try:
        txt = B.llm(prompt, SYS_DECOMP, max_tokens=600)
    except Exception as e:
        if isinstance(e, B.DailyCapReached):
            raise
        raise RuntimeError("api_error") from e
    try:
        parts = B.parse_json(txt)
    except Exception as e:
        raise ValueError("malformed_json") from e
    if isinstance(parts, list) and parts and all(isinstance(p, str) for p in parts):
        return parts[:4]
    raise TypeError("invalid_structure")

def _record_decomp_failure(failures, exc):
    kind = str(exc) if str(exc) in {"api_error", "malformed_json", "invalid_structure"} else "other_error"
    failures[kind] = failures.get(kind, 0) + 1

def _decomp_score(req, alltext):
    generated = " ".join(alltext)
    return score_decomposition(req, generated) if isinstance(req.get("leaves"), dict) else score_hard(req, generated)

def run_decomp_arm(arm, req, seed, budget=13):
    rng = random.Random(seed)
    calls = 0
    failures = {}
    requests_before = B.STATE["calls_today"]
    tree = {}
    queue = [(req["req"], 0)]
    alltext = [req["req"]]
    if arm == "blueprint":
        # fixed skeleton: requirement -> chunks, then each chunk -> leaves; no adaptivity
        if calls < budget:
            try:
                chunks = decompose_call(req["req"]); calls += 1
            except B.DailyCapReached:
                raise
            except Exception as e:
                calls += 1; _record_decomp_failure(failures, e)
                return {"coverage": 0.0, "passed": False, "calls": calls,
                        "api_requests": B.STATE["calls_today"] - requests_before,
                        "nodes": len(alltext), "failures": failures}
            tree[req["req"]] = chunks; alltext += chunks
            for c in chunks[:3]:
                if calls >= budget: break
                try:
                    subs = decompose_call(c); calls += 1
                    tree[c] = subs; alltext += subs
                except B.DailyCapReached:
                    raise
                except Exception as e:
                    calls += 1; _record_decomp_failure(failures, e)
        cov = _decomp_score(req, alltext)
        return {"coverage": round(cov, 3), "passed": cov >= 1.0, "calls": calls,
                "api_requests": B.STATE["calls_today"] - requests_before,
                "nodes": len(alltext), "failures": failures}
    workers = 1 if arm == "central" else (4 if arm in ("pool", "cells") else None)
    if arm == "colony":
        nwork = 1; spawn_events = []
        ph = {}   # chunk -> unresolved pheromone
        t = 0
        while queue and calls < budget:
            t += 1
            backlog = len(queue)
            if backlog >= 3 and nwork < 6:
                nwork += 1; spawn_events.append((t, nwork))
            if backlog == 0 and nwork > 1: nwork -= 1
            for _ in range(nwork):
                if not queue or calls >= budget: break
                # threshold: take highest-pheromone chunk; fresh chunks get base 1.0
                queue.sort(key=lambda cd: -ph.get(cd[0], 1.0))
                chunk, depth = queue.pop(0)
                try:
                    parts = decompose_call(chunk); calls += 1
                except B.DailyCapReached:
                    raise
                except Exception as e:
                    calls += 1; ph[chunk] = ph.get(chunk, 1.0) + 1.0
                    _record_decomp_failure(failures, e)
                    queue.append((chunk, depth)); continue
                tree[chunk] = parts; alltext += parts
                for p in parts:
                    # depth 0 and 1 always expand; deeper only if still abstract (long)
                    if depth < 2 or not is_leaf(p):
                        queue.append((p, depth + 1)); ph[p] = ph.get(p, 1.0) * EVAP + 0.5
        cov = _decomp_score(req, alltext)
        return {"coverage": round(cov, 3), "passed": cov >= 1.0, "calls": calls,
                "api_requests": B.STATE["calls_today"] - requests_before,
                "nodes": len(alltext), "failures": failures,
                "workers_final": nwork, "spawn_events": spawn_events}
    # central / pool / cells: round-robin decomposers, BFS
    wi = 0
    while queue and calls < budget:
        chunk, depth = queue.pop(0)
        try:
            role = CELL_ROLES[wi % len(CELL_ROLES)] if arm == "cells" else None
            parts = decompose_call(chunk, role=role); calls += 1
        except B.DailyCapReached:
            raise
        except Exception as e:
            calls += 1
            _record_decomp_failure(failures, e)
            if calls < budget: queue.append((chunk, depth))
            continue
        tree[chunk] = parts; alltext += parts
        for p in parts:
            if depth < 2 or not is_leaf(p): queue.append((p, depth + 1))
        wi = (wi + 1) % workers
    cov = _decomp_score(req, alltext)
    return {"coverage": round(cov, 3), "passed": cov >= 1.0, "calls": calls,
            "api_requests": B.STATE["calls_today"] - requests_before,
            "nodes": len(alltext), "failures": failures}

def summarize_decomp_results(done):
    summary = {}
    for arm in ("colony", "central", "pool", "cells", "blueprint"):
        rows = [v for k, v in done.items() if k.startswith(arm + ":")]
        failure_types = {}
        for row in rows:
            for kind, count in row.get("failures", {}).items():
                failure_types[kind] = failure_types.get(kind, 0) + count
            if not row.get("passed"):
                failure_types["coverage_incomplete"] = failure_types.get("coverage_incomplete", 0) + 1
        summary[arm] = {
            "runs_measured": len(rows),
            "strict_passes_measured": sum(bool(r.get("passed")) for r in rows),
            "strict_pass_rate_measured": round(sum(bool(r.get("passed")) for r in rows) / len(rows), 3) if rows else None,
            "mean_leaf_coverage_measured": round(sum(r.get("coverage", 0) for r in rows) / len(rows), 3) if rows else None,
            "api_requests_measured": sum(r.get("api_requests", 0) for r in rows),
            "mean_api_requests_per_requirement_measured": round(sum(r.get("api_requests", 0) for r in rows) / len(rows), 2) if rows else None,
            "worker_invocations_measured": sum(r.get("calls", 0) for r in rows),
            "failure_types_measured": failure_types,
        }
    return summary

def main():
    part = sys.argv[1]
    ckfile = f"run4/ckpt_{part}.json"
    os.makedirs("run4", exist_ok=True)
    state = json.load(open(ckfile)) if os.path.exists(ckfile) else {"done": {}}
    def save():
        tmp = ckfile + ".tmp"; json.dump(state, open(tmp, "w")); os.replace(tmp, ckfile)
    if part == "coding":
        # 5 arms x 5 seeds x 10 tasks, budget 25 calls per run
        for arm in ("colony", "central", "pool", "cells", "blueprint"):
            for seed in range(5):
                key = f"{arm}:{seed}"
                if key in state["done"]: continue
                state["done"][key] = run_coding_arm(arm, HARD_TASKS, 100 + seed, 25)
                save(); print(key, state["done"][key]["solved"], state["done"][key]["calls"], flush=True)
        json.dump(state["done"], open("run4/results_coding.json", "w"), indent=1)
    elif part == "decomp":
        reqs = REQUIREMENTS + HARD_REQUIREMENTS
        for arm in ("colony", "central", "pool", "cells", "blueprint"):
            for seed in range(2):
                for req in reqs:
                    key = f"{arm}:{seed}:{req['id']}"
                    if key in state["done"]: continue
                    try:
                        result = run_decomp_arm(arm, req, 200 + seed)
                    except B.DailyCapReached:
                        save()
                        print("Daily free-tier request cap reached; resume this command after the quota reset.", flush=True)
                        json.dump(state["done"], open("run4/results_decomp.json", "w"), indent=1)
                        json.dump(summarize_decomp_results(state["done"]), open("run4/summary_decomp.json", "w"), indent=1)
                        return
                    state["done"][key] = result
                    save(); print(key, state["done"][key], flush=True)
        json.dump(state["done"], open("run4/results_decomp.json", "w"), indent=1)
        json.dump(summarize_decomp_results(state["done"]), open("run4/summary_decomp.json", "w"), indent=1)

if __name__ == "__main__":
    main()
