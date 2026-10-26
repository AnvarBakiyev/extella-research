"""K4: 100 составных программ (20 правил rulebook, переведённых в план, и 80 вариантов плана расчёта).
Для каждой — исход текущей версии steps на 2000 заказах (статус и хэш выходов) и флаг «где-то ставка > 30»."""
import hashlib, json, os, random, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "langs"))
import rulebook, steps
rows = [dict(zip(("is_wholesale", "is_vip", "qty", "price_cents", "coupon"), r)) for r in sqlite3.connect(os.path.join(ROOT, "data", "orders.db")).execute("SELECT is_wholesale, is_vip, qty, price_cents, coupon FROM orders ORDER BY id")]
progs = [rulebook.translate(s) for s in json.load(open(os.path.join(ROOT, "data", "rulesets.json")))]
rnd = random.Random(20261029)
for k in range(80):
    progs.append(f"""gross = qty * price_cents
base = {rnd.randint(5, 20)} if is_wholesale * qty >= {rnd.randint(10, 40)} else 0
vipd = {rnd.randint(3, 15)} if is_vip > 0 else 0
rate = max(base, vipd) + {rnd.randint(0, 15)} * coupon
discount = round(gross * rate / 100)
net = gross - discount
tax = round(net * {rnd.choice([0, 5, 12, 20])} / 100)
total = net + tax""")
def outcome(mod, plan):
    r = mod.run_map(plan, rows, ["rate"] + (["total"] if "total =" in plan else []))
    return {"status": r["status"], "sha": hashlib.sha256(json.dumps(r.get("rows"), sort_keys=True).encode()).hexdigest()[:16] if r["status"] == "success" else None, "reason": r.get("reason", "")[:80]}
cases = []
for p in progs:
    o = outcome(steps, p); rates = [x["rate"] for x in steps.run_map(p, rows, ["rate"])["rows"]]
    cases.append({"plan": p, **o, "over30": max(rates) > 30})
json.dump(cases, open(os.path.join(ROOT, "k4", "cases.json"), "w"), indent=1)
print("программ", len(cases), "| успешных", sum(c["status"] == "success" for c in cases), "| со ставкой > 30:", sum(c["over30"] for c in cases))
