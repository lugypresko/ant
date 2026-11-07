#!/usr/bin/env python3
# Experiment 3b (real LLM, Gemini free tier): blank-environment nest.
# Ants invent arbitrary workspace artifacts with NO SDLC vocabulary in prompts.
# Reward = downstream coding-task pass rate only. Arms: emergent, classic SDLC,
# central, blank; scale sweep scripted + LLM spot-checks. Checkpointed, --part.
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nest_llm as B   # reuse llm(), run_downstream, run_code, extract_code, logging
from tasks import TASKS, REWARD_TASKS

TICKS, WINDOW, MAXART = 60, 10, 30
CKPT_DIR = "run"

SYS_EMERGENT = (
 "You are one of a colony of simple agents sharing a workspace. The colony's only goal is to get better "
 "at solving small Python coding tasks. The colony may keep shared artifacts in the workspace: any named "
 "text or code the agents consider useful. There are no required categories and no rules about what to "
 "build. The only feedback the colony ever gets is its recent success rate on coding tasks. "
 "Reply ONLY with a JSON array of actions, one per agent: "
 "[{\"agent\":<id>,\"op\":\"create\"|\"improve\"|\"drop\"|\"none\",\"name\":\"<short artifact name>\","
 "\"content\":\"<artifact text, at least 30 chars when creating or improving>\"}]. No prose.")

def workspace_view(arts, last_score, prev_score, tick):
    lines = [f"Tick {tick}. Recent coding-task success rate: {last_score:.2f}"
             + (f" (previous: {prev_score:.2f}, change {last_score-prev_score:+.2f})" if prev_score is not None else " (first measurement)")]
    if not arts:
        lines.append("Workspace is EMPTY.")
    else:
        lines.append("Workspace artifacts:")
        for name, a in list(arts.items())[:MAXART]:
            lines.append(f"- {name} (reinforcement {a['pher']:.2f}): {a['content'][:120]!r}")
    return "\n".join(lines)

def eval_on(arts, taskset):
    nest = B.Nest()
    for name, a in arts.items():
        nest.art["conventions"].append(f"{name}: {a['content'][:150]}")
    p, fails, _ = B.run_downstream(nest, taskset)
    return p / len(taskset), fails

def blank_context_nest(arts):
    nest = B.Nest()
    for name, a in arts.items():
        nest.art["conventions"].append(f"{name}: {a['content'][:150]}")
    return nest

def scripted_emergent(arts, nagents, rng):
    ops = []
    names = list(arts)
    for i in range(nagents):
        r = rng.random()
        if not arts or r < 0.3:
            ops.append({"agent": i, "op": "create", "name": f"note_{rng.randrange(10**6)}", "content": ""})
        elif r < 0.7 and names:
            ops.append({"agent": i, "op": "improve", "name": rng.choice(names), "content": ""})
        elif names and r < 0.8:
            ops.append({"agent": i, "op": "drop", "name": rng.choice(names), "content": ""})
        else:
            ops.append({"agent": i, "op": "none", "name": "", "content": ""})
    return ops

def apply_actions(arts, actions, generic):
    for a in actions:
        try:
            op, name, content = a.get("op"), str(a.get("name", ""))[:40], str(a.get("content", ""))
        except Exception:
            continue
        if op == "create" and name and (generic or len(content.strip()) >= 30):
            if len(arts) < MAXART or name in arts:
                arts[name] = {"content": content.strip()[:800] or "(placeholder)", "pher": 0.0, "born_tick": -1}
        elif op == "improve" and name in arts and (generic or len(content.strip()) >= 30):
            if content.strip(): arts[name]["content"] = content.strip()[:800]
            arts[name]["pher"] += 0.2
        elif op == "drop" and name in arts:
            del arts[name]

def part_emergent(nagents=30, llm=True, spot=None, seed=7, label="emergent", reward_every=WINDOW):
    ck = os.path.join(CKPT_DIR, f"ckpt_{label}.json")
    rng = random.Random(seed)
    if os.path.exists(ck):
        d = json.load(open(ck)); arts = d["arts"]; start = d["tick"]+1
        hist, fallbacks = d["hist"], d["fallbacks"]; last, prev = d["last"], d["prev"]
    else:
        arts, start, hist, fallbacks, last, prev = {}, 0, [], 0, 0.0, None
    for t in range(start, TICKS):
        use_llm = llm and (spot is None or t in spot)
        actions = None
        if use_llm:
            n_ask = min(nagents, 30)
            prompt = workspace_view(arts, last, prev, t) + f"\nProduce exactly {n_ask} actions, agent ids 0..{n_ask-1}."
            for _ in range(2):
                try:
                    actions = B.parse_json(B.llm(prompt, SYS_EMERGENT, max_tokens=3500)); break
                except Exception:
                    actions = None
            if not isinstance(actions, list): actions = None
        if actions is None:
            actions = scripted_emergent(arts, nagents, rng)
            if use_llm: fallbacks += 1
        apply_actions(arts, actions, generic=not use_llm or actions is None)
        for a in arts.values(): a["born_tick"] = t if a["born_tick"] == -1 else a["born_tick"]
        if t % reward_every == reward_every - 1 or t == TICKS - 1:
            score, _ = eval_on(arts, REWARD_TASKS)
            delta = score - last
            recent = [n for n, a in arts.items() if a["born_tick"] > t - WINDOW]
            if delta > 0 and recent:
                for n in recent: arts[n]["pher"] += delta / len(recent)
            for a in arts.values(): a["pher"] *= 0.9
            hist.append(round(score, 3)); prev, last = last, score
        tmp = ck + ".tmp"
        json.dump({"arts": arts, "tick": t, "hist": hist, "fallbacks": fallbacks,
                   "last": last, "prev": prev}, open(tmp, "w"))
        os.replace(tmp, ck)
        print(label, "tick", t, "arts", len(arts), "hist", hist[-1] if hist else None, flush=True)
    d = json.load(open(ck)); done = d.get("eval_done", {})
    for t in TASKS:
        if t["id"] in done: continue
        nest = blank_context_nest(arts)
        ok = False
        for _ in range(2):
            try:
                code = B.extract_code(B.llm(f"PROJECT WORKSPACE:\n{nest.context()}\n\nTASK: {t['spec']}\nWrite the function `{t['entry']}`.", B.SYS_CODE, max_tokens=1200))
                ok = B.run_code(code, t["tests"], t["entry"]); break
            except Exception: pass
        done[t["id"]] = bool(ok)
        d2 = json.load(open(ck)); d2["eval_done"] = done
        tmp = ck + ".tmp"; json.dump(d2, open(tmp, "w")); os.replace(tmp, ck)
    final = sum(done.values()) / len(TASKS); fails = [k for k, v in done.items() if not v]
    out = {"final_eval": round(final, 3), "fails": fails, "hist": hist, "fallbacks": fallbacks,
           "artifacts": {n: a["content"][:200] for n, a in arts.items()},
           "pher": {n: round(a["pher"], 3) for n, a in arts.items()}}
    json.dump(out, open(os.path.join(CKPT_DIR, f"result_{label}.json"), "w"), indent=1)
    print(label, "FINAL", out["final_eval"], "fallbacks", fallbacks, flush=True)

SDLC_COMPONENTS = ["repo", "tests", "ci_gates", "tool_library", "conventions", "docs"]
SYS_CLASSIFY = ("You classify workspace artifacts. For each artifact name+content, say which of these classic "
 "software-lifecycle functions it serves, if any: versioning, verification/testing, ci_gates, reusable_tools, "
 "conventions/style, documentation. If none fits, answer 'novel: <one or two words naming its function>'. "
 "Reply ONLY with JSON: {\"<artifact name>\": \"<function or novel: ...>\"}.")

def part_classic_central():
    dmg = B.damage_schedule()[:TICKS]
    for arm, n, u in (("classic", 4, 3), ("central", 1, 8)):
        ck = os.path.join(CKPT_DIR, f"ckpt_{arm}.json")
        if os.path.exists(os.path.join(CKPT_DIR, f"result_{arm}.json")):
            continue
        if os.path.exists(ck):
            d = json.load(open(ck))
            nest = B.Nest(); nest.mat = d["mat"]; nest.art = d["art"]; nest.prog = d["prog"]
            start, fb = d["tick"] + 1, d["fallbacks"]
        else:
            nest, start, fb = B.Nest(), 0, 0
        for t in range(start, TICKS):
            nest.damage(dmg[t])
            actions, used_fb = None, False
            for _ in range(2):
                try:
                    actions = B.parse_json(B.llm(B.build_prompt(arm, n, nest.mat, dmg[t], t), B.SYS_BUILD))
                    break
                except Exception:
                    pass
            if not isinstance(actions, list):
                actions, used_fb = B.scripted_actions(nest, n), True
            fb += 1 if used_fb else 0
            for a in actions:
                try:
                    c, w = a["component"], a.get("work", "")
                except Exception:
                    continue
                nest.apply(c, w, u, generic=used_fb)
            tmp = ck + ".tmp"
            json.dump({"mat": nest.mat, "art": nest.art, "prog": nest.prog,
                       "tick": t, "fallbacks": fb}, open(tmp, "w")); os.replace(tmp, ck)
            print(arm, "tick", t, nest.mat, flush=True)
        # final eval (easy 20) checkpointed per task
        d = json.load(open(ck)); done = d.get("eval_done", {})
        for task in TASKS:
            if task["id"] in done: continue
            ok = False
            for _ in range(2):
                try:
                    code = B.extract_code(B.llm(f"PROJECT INFRASTRUCTURE STATE:\n{nest.context()}\n\nTASK: {task['spec']}\nWrite the function `{task['entry']}`.", B.SYS_CODE, max_tokens=1200))
                    ok = B.run_code(code, task["tests"], task["entry"]); break
                except Exception:
                    pass
            done[task["id"]] = bool(ok)
            d2 = json.load(open(ck)); d2["eval_done"] = done
            tmp = ck + ".tmp"; json.dump(d2, open(tmp, "w")); os.replace(tmp, ck)
        out = {"final_eval": round(sum(done.values())/len(TASKS), 3),
               "fails": [k for k, v in done.items() if not v], "nest_score": nest.score(),
               "maturities": nest.mat, "fallbacks": fb}
        json.dump(out, open(os.path.join(CKPT_DIR, f"result_{arm}.json"), "w"), indent=1)
        print(arm, "FINAL", out["final_eval"], flush=True)

def part_blank_scale():
    empty = B.Nest()
    p, fails, _ = B.run_downstream(empty, TASKS)
    json.dump({"final_eval": round(p/len(TASKS), 3), "fails": fails},
              open(os.path.join(CKPT_DIR, "result_blank.json"), "w"), indent=1)
    print("blank FINAL", round(p/len(TASKS),3), flush=True)
    for size in (100, 300):
        rng = random.Random(1000+size)
        spot = set(rng.sample(range(TICKS), 10))
        part_emergent(nagents=size, llm=True, spot=spot, seed=1000+size, label=f"scale{size}", reward_every=20)

def part_classify():
    d = json.load(open(os.path.join(CKPT_DIR, "result_emergent.json")))
    listing = "\n".join(f"- {n}: {c!r}" for n, c in d["artifacts"].items())
    txt = B.llm("Artifacts:\n" + listing, SYS_CLASSIFY, max_tokens=2000)
    mapping = B.parse_json(txt)
    json.dump(mapping, open(os.path.join(CKPT_DIR, "result_classify.json"), "w"), indent=1)
    vals = list(mapping.values())
    novel = [v for v in vals if str(v).startswith("novel")]
    print("classified", len(vals), "novel", len(novel))
    print(json.dumps(mapping, indent=1)[:2000])

if __name__ == "__main__":
    os.makedirs(CKPT_DIR, exist_ok=True)
    part = sys.argv[1] if len(sys.argv) > 1 else "emergent"
    {"emergent": part_emergent, "classic_central": part_classic_central,
     "blank_scale": part_blank_scale, "classify": part_classify}[part]()
