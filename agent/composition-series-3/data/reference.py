"""Эталон отчёта, посчитанный напрямую, без языков и обработчиков.
Правила: оптовый заказ от 20 штук — скидка 10 %; VIP — 5 %; берётся большая; купон добавляет 3 %.
Округление до цента половиной вверх; налог 12 % на сумму после скидки."""
import json, math, sqlite3, sys
def half_up(x): return math.floor(x + 0.5)
def report(path):
    out = {}
    for region, wh, vip, qty, price, coupon in sqlite3.connect(path).execute("SELECT region, is_wholesale, is_vip, qty, price_cents, coupon FROM orders"):
        gross = qty * price
        rate = max(10 if (wh and qty >= 20) else 0, 5 if vip else 0) + (3 if coupon else 0)
        discount = half_up(gross * rate / 100); net = gross - discount; tax = half_up(net * 12 / 100)
        r = out.setdefault(region, {"orders": 0, "gross": 0, "discount": 0, "tax": 0, "total": 0})
        r["orders"] += 1; r["gross"] += gross; r["discount"] += discount; r["tax"] += tax; r["total"] += net + tax
    return dict(sorted(out.items()))
if __name__ == "__main__":
    print(json.dumps(report(sys.argv[1] if len(sys.argv) > 1 else "orders.db"), indent=1))
