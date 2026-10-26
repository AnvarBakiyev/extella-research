"""Проверка перед заменой исполнителя (одинаковая для обеих сторон).
cases: [{plan, problem, status, answer}] — исход текущей версии. Новая версия не должна менять статус
и не должна сдвигать ответ на 0,005 и больше (правило «до центов» сдвигает меньше)."""
import importlib.util, json, sys

def check(module, cases):
    bad = []
    for i, c in enumerate(cases):
        r = module.run_plan(c["plan"], c["problem"], "plan")
        if r["status"] != c["status"] or (r["status"] == "success" and abs(r["answer"] - c["answer"]) >= 0.005):
            bad.append({"case": i, "was": [c["status"], c.get("answer")], "now": [r["status"], r.get("answer")]})
    return bad

if __name__ == "__main__":
    s = importlib.util.spec_from_file_location("candidate", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    bad = check(m, json.load(open(sys.argv[2])))
    print(json.dumps({"ok": not bad, "changed": len(bad), "examples": bad[:3]}))
    sys.exit(1 if bad else 0)
