"""K1, вторая часть: Qwen 9B по описанию языка card пишет программу; программа исполняется обработчиком card на обеих сторонах."""
import json, os, re, sys, urllib.request
sys.path.insert(0, "langs"); sys.path.insert(0, "../gsm8k-infrastructure-vs-assembly/seriya2"); import card, readsql, ext
SPEC = card.__doc__
REQS = ["Report orders by customer_type: number of orders, sum of gross and total, money format for gross and total. Title: By customer type",
        "Report by region with the count of orders called n and the sum of discount in money format. Title: Discounts",
        "Group by coupon; show orders count and sum of tax; tax is money. Title: Coupons",
        "One card per region with total in money format and no count. Title: Totals",
        "By is_vip: count of orders, sums of gross, discount, tax, total, all money. Title: VIP split"]
def model(p):
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({"model": "qwen3.5:9b", "prompt": p, "stream": False, "think": False, "options": {"temperature": 0}}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))["response"]
rows = readsql.run_sql(open("data/select.readsql").read().replace("SELECT ", "SELECT customer_type, ", 1), "data/orders.db")["rows"]
calc = __import__("steps").run_map(open("data/calc.steps").read(), rows, ["gross", "discount", "tax", "total"])["rows"]
data = [dict(a, **b) for a, b in zip(rows, calc)]
out = []
for q in REQS:
    prog = re.sub(r"^```\w*|```$", "", model("Language card:\n" + SPEC + "\nAvailable fields: region, customer_type, is_wholesale, is_vip, qty, price_cents, coupon, gross, discount, tax, total.\nWrite a card program for this request. Output only the program.\nRequest: " + q).strip(), flags=re.M).strip()
    py = card.render(prog, data)
    ext.save("k3_k1_probe", prog, "k3_card", "Series 3 K1: card program written by Qwen 9B.", {})
    r, dt = ext.run("k3_k1_probe", {"rows": data}, ext.MAC); r = r if isinstance(r, dict) and ("aggregates" in r or "reason" in r) else r.get("result", r)
    same = isinstance(r, dict) and r.get("status") == py["status"] and r.get("aggregates") == py.get("aggregates")
    out.append({"request": q, "program": prog, "python": py["status"], "extella": r.get("status") if isinstance(r, dict) else str(r)[:80], "same": same, "reason": py.get("reason", ""), "extella_sec": round(dt, 1)})
    print(out[-1]["python"], out[-1]["extella"], "одинаково:", same, "|", out[-1]["reason"][:80])
json.dump(out, open("results_k1_model.json", "w"), ensure_ascii=False, indent=1)
