#!/usr/bin/env python3
"""
CELL-1 pilot harness (mock agents, $0).
Validates experiment machinery only: environment generation, sensing channels,
tool-forge plumbing, held-out grading, budget accounting.
It says NOTHING about whether an LLM cell beats an LLM central agent.
"""
import json, os, random, shutil, subprocess, sys, hashlib

BASE = os.path.expanduser("~/cell-experiment/run")
shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(BASE)

# ---------------- Environment generator ----------------
def make_record(rng, i, multiline=False, long_payload=False):
    payload = f"event {i} " + rng.choice(["login ok", "cache miss", "retry", "timeout warn"])
    if multiline:
        payload += "\nstack: frame1\nstack: frame2"
    if long_payload:
        payload += "x" * (160 + rng.randint(0, 40))
    return {"id": f"rec-{i:05d}", "ts": f"2026-11-06T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:00Z", "payload": payload}

def make_batch(path_in, path_out, rng, n, corruption, rate):
    """Write input batch and the 'service' output with a planted silent-drop corruption."""
    gt_missing = []
    with open(path_in, "w") as fin, open(path_out, "w") as fout:
        for i in range(n):
            drop = False
            if corruption == "drop_multiline":
                rec = make_record(rng, i, multiline=(rng.random() < rate))
                drop = "\n" in rec["payload"]          # service bug: silently drops multiline payloads
            elif corruption == "drop_nonascii":
                rec = make_record(rng, i)
                if rng.random() < rate:
                    rec["payload"] += " שלום"          # non-ascii
                drop = any(ord(c) > 127 for c in rec["payload"])
            elif corruption == "drop_long":            # NOVEL family, held-out only
                rec = make_record(rng, i, long_payload=(rng.random() < rate))
                drop = len(rec["payload"]) > 140
            else:
                raise ValueError(corruption)
            fin.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if drop:
                gt_missing.append(rec["id"])
            else:
                out = dict(rec); out["status"] = "processed"
                fout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return gt_missing

def write_status(env_dir, received, processed):
    with open(os.path.join(env_dir, "status.json"), "w") as f:
        json.dump({"service": "logpipe", "received": received, "processed": processed, "alarms": []}, f)

# ---------------- Budget ledger ----------------
class Ledger:
    def __init__(self, cap_tokens, cap_calls):
        self.tokens = 0; self.calls = 0; self.cap_tokens = cap_tokens; self.cap_calls = cap_calls
    def charge(self, tokens=0, calls=0):
        self.tokens += tokens; self.calls += calls
        if self.tokens > self.cap_tokens or self.calls > self.cap_calls:
            raise RuntimeError("budget exceeded")

# ---------------- Grader (external, frozen) ----------------
def grade(tool_path, suite_dir):
    """Run the agent-produced tool on held-out batches; exact match on missing_ids."""
    results = []
    for case in sorted(os.listdir(suite_dir)):
        cdir = os.path.join(suite_dir, case)
        rep = os.path.join(cdir, "report.json")
        r = subprocess.run([sys.executable, tool_path, "--input", os.path.join(cdir, "in.jsonl"),
                            "--output", os.path.join(cdir, "out.jsonl"), "--report", rep],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or not os.path.exists(rep):
            results.append({"case": case, "pass": False, "why": "tool error"})
            continue
        got = json.load(open(rep))
        gt = json.load(open(os.path.join(cdir, "gt.json")))
        ok = (sorted(got.get("missing_ids", [])) == sorted(gt["missing_ids"])
              and got.get("received") == gt["received"] and got.get("processed") == gt["processed"])
        results.append({"case": case, "pass": ok,
                        "why": "" if ok else f"got {len(got.get('missing_ids', []))} missing, truth {len(gt['missing_ids'])}"})
    return results

# ---------------- Build visible environment ----------------
env = os.path.join(BASE, "env"); os.makedirs(env)
rng = random.Random(42)
gt_vis = make_batch(os.path.join(env, "batch_001.in.jsonl"), os.path.join(env, "batch_001.out.jsonl"),
                    rng, 200, "drop_multiline", 0.06)
write_status(env, 200, 200 - len(gt_vis))

# ---------------- Held-out suite (disjoint seeds; novel family included) ----------------
suite = os.path.join(BASE, "heldout"); os.makedirs(suite)
specs = [("c1_same_multiline_r04", "drop_multiline", 0.04, 101),
         ("c2_same_multiline_r10", "drop_multiline", 0.10, 102),
         ("c3_same_nonascii_r05",  "drop_nonascii", 0.05, 103),
         ("c4_same_nonascii_r12",  "drop_nonascii", 0.12, 104),
         ("c5_same_multiline_r08", "drop_multiline", 0.08, 105),
         ("c6_novel_long_r05",     "drop_long",     0.05, 201),
         ("c7_novel_long_r15",     "drop_long",     0.15, 202),
         ("c8_novel_long_r10",     "drop_long",     0.10, 203)]
for name, corr, rate, seed in sorted(specs):
    cdir = os.path.join(suite, name); os.makedirs(cdir)
    r2 = random.Random(seed)
    gt = make_batch(os.path.join(cdir, "in.jsonl"), os.path.join(cdir, "out.jsonl"), r2, 200, corr, rate)
    json.dump({"missing_ids": gt, "received": 200, "processed": 200 - len(gt)}, open(os.path.join(cdir, "gt.json"), "w"))

# ---------------- Mock agents (scripted, no LLM) ----------------
TOOL_GOOD = '''import json, argparse, sys
p = argparse.ArgumentParser()
p.add_argument("--input"); p.add_argument("--output"); p.add_argument("--report")
a = p.parse_args()
ins = [json.loads(l) for l in open(a.input, encoding="utf-8")]
outs = [json.loads(l) for l in open(a.output, encoding="utf-8")]
out_ids = {r["id"] for r in outs}
missing = [r["id"] for r in ins if r["id"] not in out_ids]
json.dump({"received": len(ins), "processed": len(outs), "missing_ids": missing}, open(a.report, "w"))
'''
TOOL_NAIVE = '''import json, argparse
p = argparse.ArgumentParser()
p.add_argument("--input"); p.add_argument("--output"); p.add_argument("--report")
a = p.parse_args()
ins = open(a.input, encoding="utf-8").read().splitlines()
outs = open(a.output, encoding="utf-8").read().splitlines()
# naive: assumes the first N inputs were processed (order preserved, nothing identifiable)
json.dump({"received": len(ins), "processed": len(outs), "missing_ids": [f"rec-{i:05d}" for i in range(len(outs), len(ins))]}, open(a.report, "w"))
'''

def run_cell_mock(env_dir, ledger):
    """Scripted 'cell': sense -> detect anomaly -> forge tool -> use tool."""
    ledger.charge(tokens=0, calls=1)  # sense
    st = json.load(open(os.path.join(env_dir, "status.json")))
    detected = st["received"] != st["processed"]
    if not detected:
        return {"detected": False}
    tool = os.path.join(BASE, "cell_tool.py")
    open(tool, "w").write(TOOL_GOOD)     # forge
    ledger.charge(calls=1)               # exec tool on visible batch
    rep = os.path.join(BASE, "cell_visible_report.json")
    subprocess.run([sys.executable, tool, "--input", os.path.join(env_dir, "batch_001.in.jsonl"),
                    "--output", os.path.join(env_dir, "batch_001.out.jsonl"), "--report", rep], check=True)
    return {"detected": True, "tool": tool}

def run_central_mock(env_dir, ledger):
    """Scripted 'central': no translated task => never probes. By construction."""
    ledger.charge(tokens=0, calls=0)
    return {"detected": False, "note": "no task statement given; central loop idles"}

ledger_cell = Ledger(cap_tokens=150000, cap_calls=25)
ledger_base = Ledger(cap_tokens=150000, cap_calls=25)
cell_res = run_cell_mock(env, ledger_cell)
base_res = run_central_mock(env, ledger_base)

summary = {"visible_ground_truth_missing": len(gt_vis), "cell": cell_res, "central": base_res,
           "budget": {"cell": vars(ledger_cell), "central": vars(ledger_base)}}

if cell_res.get("detected"):
    summary["grader_cell_good_tool"] = grade(cell_res["tool"], suite)
    naive = os.path.join(BASE, "naive_tool.py"); open(naive, "w").write(TOOL_NAIVE)
    summary["grader_naive_tool"] = grade(naive, suite)

print(json.dumps(summary, indent=2, ensure_ascii=False))
