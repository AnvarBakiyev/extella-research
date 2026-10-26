"""K2 на Python: 20 наборов правил через цепочку readsql -> rulebook; языки берутся из установленной папки ~/kompoziciya/py/langs."""
import importlib, json, os, sys, time
LANGS = os.path.expanduser("~/kompoziciya/py/langs"); sys.path.insert(0, LANGS)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import readsql, steps, rulebook, chain
def run_lang(lang, code, params):
    if lang == "k3_readsql": return readsql.run_sql(code, params.get("db"))
    if lang == "k3_rulebook": return rulebook.run(code, params.get("rows") or [], lambda p, r, o: steps.run_map(p, r, o))
    return {"status": "refused", "reason": "unknown language " + lang}
sets = json.load(open(os.path.join(ROOT, "data", "rulesets.json"))); ref = json.load(open(os.path.join(ROOT, "data", "rulesets_reference.json")))
sel = open(os.path.join(ROOT, "data", "select.readsql")).read(); res = []
for k, s in enumerate(sets, 1):
    t0 = time.time(); r = chain.run(json.dumps([{"lang": "k3_readsql", "code": sel}, {"lang": "k3_rulebook", "code": s}]), {"db": "~/kompoziciya/orders.db"}, run_lang)
    res.append({"set": k, "status": r["status"], "equal": r["status"] == "success" and [x["rate"] for x in r["rows"]] == ref[k - 1], "reason": r.get("reason", ""), "sec": round(time.time() - t0, 3)})
print(sys.argv[1], "успешно", sum(x["status"] == "success" for x in res), "| совпало", sum(x["equal"] for x in res), "| отказов с законом 30 %", sum("30% limit" in x["reason"] for x in res), "| медиана, с", sorted(x["sec"] for x in res)[10])
