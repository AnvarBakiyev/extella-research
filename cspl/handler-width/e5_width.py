"""Opyt 22, width: one handler, 40 saved programs. Change of the rule in one place; a broken handler version and its reach;
a guard (a handler for the handler) that runs every saved program against a candidate before registering it. No model calls.
Writes e5_result.json."""
import json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import save_expert, run_expert, register, api, MAC, unwrap

LANG = "report22"
BODY = '''    lines = [l.strip() for l in (code or filtered_source_code or "").splitlines() if l.strip()]
    title, rows = "", []
    for n, line in enumerate(lines, 1):
        if line.startswith("title "): title = line[6:]
        elif line.startswith("row "):
            p = line.split()
            if len(p) != 3: return {"status": "rejected", "errors": ["line %d: row needs a label and an amount" % n]}
            rows.append((p[1], AMOUNT(p[2])))
        else: return {"status": "rejected", "errors": ["line %d is not a report22 statement" % n]}
    total = round(sum(a for _, a in rows), 2)
'''
V1 = ('def report22(code = "", filtered_source_code = "", func_name = "", **extra):\n    AMOUNT = float\n' + BODY +
      '    return {"status": "success", "version": 1, "title": title, "rows": len(rows), "total": total}\n')
V2 = ('def report22(code = "", filtered_source_code = "", func_name = "", **extra):\n    AMOUNT = float\n' + BODY +
      '    labels = [l for l, _ in rows]\n'
      '    if len(set(labels)) != len(labels): return {"status": "rejected", "errors": ["a label repeats"]}\n'
      '    formatted = "{:,.2f}".format(total).replace(",", " ") + " KZT"\n'
      '    return {"status": "success", "version": 2, "title": title, "rows": len(rows), "total": total, "formatted": formatted}\n')
V3 = V2.replace("AMOUNT = float", "AMOUNT = lambda s: float(int(float(s)))").replace('"version": 2', '"version": 3')   # silent bug: drops decimals

GUARD = '''$extens("include.py")
include("import os", [])

def opyt22_guard(candidate: str = "", programs: str = "") -> dict:
    import json, disnet
    ns = {}
    try:
        exec(candidate, ns)
        fn = ns["report22"]
    except Exception as e:
        return {"status": "rejected", "reason": "candidate does not load: %s" % e}
    failures = []
    for name, text, total in json.loads(programs):
        try:
            r = fn(code=text, filtered_source_code=text, func_name=name)
            if r.get("status") != "success" or abs(r.get("total", 0) - total) > 0.005:
                failures.append([name, r.get("status"), r.get("total"), total])
        except Exception as e:
            failures.append([name, "crash", str(e)[:80], total])
    if failures:
        return {"status": "rejected", "checked": len(json.loads(programs)), "failures": len(failures), "first": failures[:3]}
    d = disnet.Disnet(url="https://disnet.extella.ai")
    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "report22", "response_format": None}
    d.container(code=candidate, func_name="report22", container_path="report22", args=None, kwargs=envelope, cspl_type="fython", push=False)
    return {"status": "registered", "checked": len(json.loads(programs))}
'''

def programs():
    rnd = random.Random(22); out = []
    for i in range(40):
        rows = []
        for j in range(rnd.randint(2, 6)):
            amt = round(rnd.uniform(-500, 5000), rnd.choice([0, 2]))
            rows.append(("item%d" % j, amt))
        text = "title Report %02d\n" % i + "\n".join("row %s %s" % (l, a) for l, a in rows)
        out.append(("opyt22_rep%02d" % i, text, round(sum(a for _, a in rows), 2)))
    return out

def run_all(progs):
    t = time.time()
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda p: run_expert(p[0])[0], progs))
    right = sum(1 for (n, _, tot), r in zip(progs, res) if isinstance(r, dict) and r.get("status") == "success" and abs(r.get("total", 0) - tot) <= 0.005)
    versions = sorted(set(str(r.get("version")) for r in res if isinstance(r, dict)))
    silent = sum(1 for (n, _, tot), r in zip(progs, res) if isinstance(r, dict) and r.get("status") == "success" and abs(r.get("total", 0) - tot) > 0.005)
    return {"right": right, "of": len(progs), "silently_wrong": silent, "versions": versions, "seconds": round(time.time() - t, 1),
            "formatted_example": next((r.get("formatted") for r in res if isinstance(r, dict) and r.get("formatted")), None)}

def guard(candidate, progs):
    t = time.time()
    r, _ = run_expert("opyt22_guard", {"candidate": candidate, "programs": json.dumps(progs)})
    return {"result": r, "seconds": round(time.time() - t, 1)}

if __name__ == "__main__":
    P = programs(); out = {"programs": len(P), "steps": []}
    def step(what, **kw): out["steps"].append({"what": what, **kw}); print(what, kw, flush=True)
    step("register v1", **register(LANG, V1))
    t = time.time()
    with ThreadPoolExecutor(6) as ex: saves = list(ex.map(lambda p: save_expert(p[0], p[1], LANG).get("status"), P))
    step("save 40 programs", ok=saves.count("success"), seconds=round(time.time() - t, 1))
    step("run all on v1", **run_all(P))
    step("register v2 (one action)", **register(LANG, V2))
    step("run all on v2, programs not re-saved", **run_all(P))
    step("save guard", status=save_expert("opyt22_guard", GUARD, "fython").get("status"))
    step("guard on broken v3", **guard(V3, P))
    step("run all after guard refused v3", **run_all(P))
    step("register broken v3 without guard", **register(LANG, V3))
    step("run all on broken v3", **run_all(P))
    step("guard on v2 (restore through guard)", **guard(V2, P))
    step("run all after restore", **run_all(P))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "e5_result.json"), "w"), indent=1, ensure_ascii=False)
