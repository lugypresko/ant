#!/usr/bin/env python3
# Experiment 3 (real LLM): nest-building colony on Gemini free tier.
# Arms: ants30, 4cell, central. 100 build ticks (1 batched call/tick), then
# 20 downstream coding tasks evaluated by running generated code vs unit tests.
# Scale arm: sizes 10/30/100/300, scripted decisions + LLM spot-checks.
import json, os, random, re, subprocess, sys, tempfile, time, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

KEY = os.environ.get("GEMINI_API_KEY", "")
if not KEY:
    raise SystemExit("Set GEMINI_API_KEY in the environment before running.")
MODEL = os.environ.get("MODEL", "gemini-3.5-flash-lite")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
COMPONENTS = ["repo", "tests", "ci_gates", "tool_library", "conventions", "docs"]
MAXMAT, TICKS = 3, 100
DAILY_CAP = 490
os.makedirs("run", exist_ok=True)
LOG = open("run/llm_log.jsonl", "a")
STATE = {"calls_today": 0}
DAILY_USAGE_FILE = "run/gemini_daily_usage.json"

class DailyCapReached(RuntimeError):
    pass

def reserve_daily_request():
    # Gemini's daily quotas reset on Pacific time. Persist reservations so a
    # restarted process cannot accidentally spend a second daily allowance.
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    try:
        with open(DAILY_USAGE_FILE) as f:
            usage = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        usage = {"date": today, "requests_reserved": 0}
    if usage.get("date") != today:
        usage = {"date": today, "requests_reserved": 0}
    if usage.get("requests_reserved", 0) >= DAILY_CAP:
        raise DailyCapReached("daily cap guard hit")
    usage["requests_reserved"] = usage.get("requests_reserved", 0) + 1
    tmp = DAILY_USAGE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(usage, f)
    os.replace(tmp, DAILY_USAGE_FILE)

def llm(prompt, sysmsg, max_tokens=4000):
    if STATE["calls_today"] >= DAILY_CAP:
        raise DailyCapReached("daily cap guard hit")
    body = {"systemInstruction": {"parts": [{"text": sysmsg}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_tokens}}
    for attempt in range(4):
        reserve_daily_request()
        STATE["calls_today"] += 1
        t0 = time.time()
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
            r = json.load(urllib.request.urlopen(req, timeout=90))
            um = r.get("usageMetadata", {})
            txt = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
            LOG.write(json.dumps({"ts": time.time(), "ok": True, "lat": round(time.time()-t0,2),
                "ptok": um.get("promptTokenCount"), "ctok": um.get("candidatesTokenCount")})+"\n"); LOG.flush()
            time.sleep(4.2)  # 15 RPM
            return txt
        except urllib.error.HTTPError as e:
            LOG.write(json.dumps({"ts": time.time(), "ok": False, "http": e.code})+"\n"); LOG.flush()
            if e.code in (429, 500, 503):
                time.sleep(min(60, 8*(attempt+1))); continue
            raise
        except Exception as e:
            LOG.write(json.dumps({"ts": time.time(), "ok": False, "err": str(e)[:120]})+"\n"); LOG.flush()
            time.sleep(8*(attempt+1))
    raise RuntimeError("llm failed after retries")

def parse_json(txt):
    m = re.search(r"\[.*\]|\{.*\}", txt, re.S)
    if not m: raise ValueError("no json")
    return json.loads(m.group(0))

class Nest:
    def __init__(self):
        self.mat = {c: 0 for c in COMPONENTS}
        self.art = {c: [] for c in COMPONENTS}
        self.prog = {c: 0 for c in COMPONENTS}
    def cost(self, c): return (self.mat[c]+1)*3
    def apply(self, c, work_text, units, generic=False):
        if c not in COMPONENTS or self.mat[c] >= MAXMAT: return False
        if not generic and len((work_text or "").strip()) < 30: return False
        self.prog[c] += units
        if not generic and work_text:
            self.art[c].append(work_text.strip()[:160])
            self.art[c] = self.art[c][-10:]
        while self.mat[c] < MAXMAT and self.prog[c] >= self.cost(c):
            self.prog[c] -= self.cost(c); self.mat[c] += 1
        return True
    def damage(self, events):
        for c in events:
            if self.mat[c] > 0: self.mat[c] -= 1
    def context(self):
        out = []
        for c in COMPONENTS:
            art = " | ".join(self.art[c])[:600] or "nothing built yet"
            out.append(f"{c}: maturity {self.mat[c]}/3. Built artifacts: {art}")
        return "\n".join(out)
    def score(self): return sum(self.mat.values())

def damage_schedule(seed=42):
    rng = random.Random(seed)
    return [[c for c in COMPONENTS if rng.random() < 0.05] for _ in range(TICKS)]

SYS_BUILD = ("You manage work on a software project 'nest' with 6 components: repo, tests, ci_gates, "
    "tool_library, conventions, docs. Each has maturity 0-3. Every tick some components lose 1 maturity (bit-rot). "
    "Reply ONLY with a JSON array of actions: [{\"agent\":<id>,\"component\":<one of the 6>,\"work\":\"<concrete artifact text, at least 30 chars, e.g. a real config snippet, test, convention rule or doc line>\"}]. "
    "Prioritize repairing damaged components, then raising the lowest maturity. No prose, JSON only.")

def build_prompt(arm, nagents, mat, damaged, tick):
    return (f"Tick {tick}. Maturities: {json.dumps(mat)}. Damaged this tick: {damaged or 'none'}. "
            f"Produce exactly {nagents} actions, one per agent id 0..{nagents-1} ({arm} arm).")

def scripted_actions(nest, nagents):
    order = sorted(COMPONENTS, key=lambda c: nest.mat[c])
    return [{"agent": i, "component": order[i % len(order)], "work": ""} for i in range(nagents)]

def run_build(arm, nagents, units_per, dmg, llm_ticks=None, sample=30):
    nest, fallbacks, calls = Nest(), 0, 0
    for t in range(TICKS):
        nest.damage(dmg[t])
        use_llm = llm_ticks is None or t in llm_ticks
        actions, used_fallback = None, False
        if use_llm:
            n_ask = min(nagents, sample)
            for _ in range(2):
                try:
                    actions = parse_json(llm(build_prompt(arm, n_ask, nest.mat, dmg[t], t), SYS_BUILD))
                    calls += 1; break
                except Exception:
                    calls += 1
            if not isinstance(actions, list): actions, used_fallback = None, True
        if actions is None:
            actions = scripted_actions(nest, nagents); used_fallback = use_llm
        fallbacks += 1 if (used_fallback and use_llm) else 0
        seen = {}
        for a in actions:
            try: c, w = a["component"], a.get("work", "")
            except Exception: continue
            generic = (actions is not None and not use_llm) or used_fallback
            seen[c] = seen.get(c, 0) + 1
        # scripted full-count when LLM sampled only `sample` agents
        if use_llm and nagents > sample and not used_fallback:
            extra = scripted_actions(nest, nagents - sample)
            for a in extra:
                nest.apply(a["component"], "", units_per, generic=True)
        for a in actions:
            try: c, w = a["component"], a.get("work", "")
            except Exception: continue
            generic = (not use_llm) or used_fallback
            nest.apply(c, w, units_per, generic=generic)
    return nest, fallbacks, calls

SYS_CODE = ("You are completing a coding task inside a project whose infrastructure was built by a team of agents. "
    "Use the project context (conventions, tools, tests) where helpful. Reply with ONLY the Python code, no explanation, no markdown fences.")

def run_code(code, tests, entry):
    prog = code + "\n\n" + tests + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(prog); path = f.name
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False
    finally:
        os.unlink(path)

def extract_code(txt):
    m = re.search(r"```(?:python)?\s*(.*?)```", txt, re.S)
    return (m.group(1) if m else txt).strip()

def run_downstream(nest, tasks):
    from tasks import TASKS
    passed, calls, fails = 0, 0, []
    for t in (tasks or TASKS):
        prompt = f"PROJECT INFRASTRUCTURE STATE:\n{nest.context()}\n\nTASK: {t['spec']}\nWrite the function `{t['entry']}`."
        ok = False
        for _ in range(2):
            try:
                code = extract_code(llm(prompt, SYS_CODE, max_tokens=1200)); calls += 1
                ok = run_code(code, t["tests"], t["entry"]); break
            except Exception:
                calls += 1
        passed += 1 if ok else 0
        if not ok: fails.append(t["id"])
    return passed, fails, calls

def main():
    from tasks import TASKS
    dmg = damage_schedule()
    results, total_calls = {}, 0
    arms = [("ants30", 30, 1), ("4cell", 4, 3), ("central", 1, 8)]
    for arm, n, u in arms:
        nest, fb, c1 = run_build(arm, n, u, dmg)
        p, fails, c2 = run_downstream(nest, TASKS)
        results[arm] = {"nest_score": nest.score(), "maturities": nest.mat, "fallbacks": fb,
                        "downstream_pass": p, "downstream_fails": fails, "calls": c1+c2}
        total_calls += c1+c2
        print(arm, results[arm], flush=True)
    # scale arm: scripted decisions, LLM spot-check on 10 ticks (sample of 30 agents)
    scale = {}
    for size in (10, 30, 100, 300):
        rng = random.Random(1000+size)
        spot = set(rng.sample(range(TICKS), 10))
        nest, fb, c1 = run_build(f"scale{size}", size, 1, dmg, llm_ticks=spot, sample=min(size,30))
        p, fails, c2 = run_downstream(nest, TASKS)
        scale[size] = {"nest_score": nest.score(), "maturities": nest.mat,
                       "downstream_pass": p, "downstream_fails": fails, "calls": c1+c2}
        total_calls += c1+c2
        print("scale", size, scale[size], flush=True)
    # token-based cost equivalent at paid prices (USD per MTok in/out)
    ptok = ctok = 0
    for line in open("run/llm_log.jsonl"):
        d = json.loads(line)
        if d.get("ok"): ptok += d.get("ptok") or 0; ctok += d.get("ctok") or 0
    prices = {"haiku4.5": (0.10, 0.50), "gpt5.1": (1.25, 10.0), "sonnet4.5": (2.0, 10.0)}
    cost = {k: round(ptok/1e6*v[0] + ctok/1e6*v[1], 4) for k, v in prices.items()}
    out = {"results": results, "scale": scale, "total_calls": total_calls,
           "tokens": {"prompt": ptok, "completion": ctok}, "cost_equiv_usd": cost}
    json.dump(out, open("run/nest_llm_results.json", "w"), indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    os.makedirs("run", exist_ok=True)
    main()
