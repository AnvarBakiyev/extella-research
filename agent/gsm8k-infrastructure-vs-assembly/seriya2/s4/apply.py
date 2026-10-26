"""S4, часть «применена ли операция»: план с одного раза (без обратной связи), три варианта подсказки:
нет подсказки / 2 операции из поиска Python / 2 операции из поиска Extella (сохранённые выдачи retrieval_*.json)."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import ustroystvo33 as C
sys.path.insert(0, os.path.join(HERE, "..")); import steps_handler as H
ops = {o["name"]: o for o in json.load(open(os.path.join(HERE, "ops.json")))}
rows = open(os.path.join(HERE, "..", "..", "data", "gsm8k_test.jsonl")).read().splitlines()
ret = {s: {r["task"]: r["top2"] for r in json.load(open(os.path.join(HERE, f"retrieval_{s}.json")))} for s in ("python", "extella")}
out = []
for task in sorted(ret["python"]):
    d = json.loads(rows[task - 1]); q = d["question"]; et = float(d["answer"].split("####")[-1].strip().replace(",", ""))
    for var in ("none", "python", "extella"):
        hint = "" if var == "none" else "\n\nOperations from the library that may help:\n" + "\n".join(f"# {ops[n]['description']}\n# {ops[n]['snippet']}" for n in ret[var][task])
        t, i, o, _ = C.вызов(q + hint + "\n\n" + C.ЯЗЫК, 1500)
        plan = re.sub(r"^```\w*|```$", "", t.strip(), flags=re.M).strip()
        r = H.run_plan(plan, q, "plan")
        out.append({"task": task, "var": var, "tokens_in": i, "tokens_out": o, "status": r["status"], "answer": r.get("answer"), "correct": r["status"] == "success" and abs(r["answer"] - et) < 1e-6})
        json.dump(out, open(os.path.join(HERE, "apply.json"), "w"), ensure_ascii=False, indent=1)
for var in ("none", "python", "extella"):
    xs = [x for x in out if x["var"] == var]
    print(var, "верных", sum(x["correct"] for x in xs), "из", len(xs), "| принято", sum(x["status"] == "success" for x in xs), "| токенов на задачу", round(sum(x["tokens_in"] + x["tokens_out"] for x in xs) / len(xs)))
