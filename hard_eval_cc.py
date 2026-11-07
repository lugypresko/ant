import sys, os, json
import nest_llm as B
from tasks_hard import HARD_TASKS
arm = sys.argv[1]
d = json.load(open(f"run/ckpt_{arm}.json"))
nest = B.Nest(); nest.art = {k: [x for x in v] for k, v in d["art"].items()}; nest.mat = d["mat"]
ck = f"run/ckpt_hard_{arm}.json"
done = json.load(open(ck)) if os.path.exists(ck) else {}
for t in HARD_TASKS:
    if t["id"] in done: continue
    ok = False
    for _ in range(2):
        try:
            code = B.extract_code(B.llm(f"PROJECT INFRASTRUCTURE STATE:\n{nest.context()}\n\nTASK: {t['spec']}\nWrite the function or class `{t['entry']}`.", B.SYS_CODE, max_tokens=1500))
            ok = B.run_code(code, t["tests"], t["entry"]); break
        except Exception: pass
    done[t["id"]] = bool(ok)
    tmp = ck + ".tmp"; json.dump(done, open(tmp, "w")); os.replace(tmp, ck)
print(arm, "hard:", len(done), "pass:", sum(done.values()))
if len(done) == len(HARD_TASKS):
    json.dump({"pass": sum(done.values()), "total": 10, "fails": [k for k, v in done.items() if not v]},
              open(f"run/result_hard_{arm}.json", "w"))
