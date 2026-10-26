"""K2 на Extella: 20 наборов правил через цепочку readsql -> rulebook на устройстве; затем замена только k3_steps на v2."""
import json, os, sys, base64
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "gsm8k-infrastructure-vs-assembly", "seriya2")); sys.path.insert(0, HERE)
import ext, build
target = {"mac": ext.MAC, "server-1": ext.VPS}[sys.argv[1]]; phase = sys.argv[2]
sets = json.load(open(os.path.join(ROOT, "data", "rulesets.json"))); ref = json.load(open(os.path.join(ROOT, "data", "rulesets_reference.json")))
sel = open(os.path.join(ROOT, "data", "select.readsql")).read()
res = []
for k, s in enumerate(sets, 1):
    name = f"k3_rb_{k:02d}"
    if phase == "v1":
        ext.save(name, json.dumps([{"lang": "k3_readsql", "code": sel}, {"lang": "k3_rulebook", "code": s}]), "k3_chain", "Series 3 K2: discount rules as a rulebook program over the orders.", {"db": "~/kompoziciya/orders.db"})
    r, dt = ext.run(name, {"db": "~/kompoziciya/orders.db"}, target)
    r = r if isinstance(r, dict) and ("rows" in r or "reason" in r) else (r.get("result") if isinstance(r, dict) else r)
    if isinstance(r, dict) and r.get("status") == "success":
        res.append({"set": k, "status": "success", "equal": [x["rate"] for x in r["rows"]] == ref[k - 1], "sec": round(dt, 1)})
    else:
        res.append({"set": k, "status": "refused", "reason": str(r.get("reason") if isinstance(r, dict) else r)[:160], "sec": round(dt, 1)})
json.dump(res, open(os.path.join(ROOT, f"results_k2_extella_{sys.argv[1]}_{phase}.json"), "w"), ensure_ascii=False, indent=1)
print(phase, sys.argv[1], "успешно", sum(x["status"] == "success" for x in res), "| совпало с эталоном", sum(x.get("equal", False) for x in res),
      "| отказов", sum(x["status"] == "refused" for x in res), "| отказов с законом 30 %", sum("30% limit" in x.get("reason", "") for x in res),
      "| медиана, с", sorted(x["sec"] for x in res)[10])
