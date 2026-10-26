"""20 наборов правил rulebook (seed 20261028) и прямой вычислитель ставок для эталона, без перевода в steps."""
import json, random, sys
FIELDS = [("is_wholesale", None), ("is_vip", None), ("coupon", None), ("qty", (">=", 10, 40)), ("price_cents", (">", 5000, 40000))]
def make():
    rnd = random.Random(20261028); sets = []
    for k in range(20):
        lines = []
        for kind, n in (("rate", rnd.randint(1, 3)), ("extra", rnd.randint(0, 2))):
            for _ in range(n):
                conds = []
                for f, op in rnd.sample(FIELDS, rnd.randint(1, 2)):
                    conds.append(f if op is None else f"{f} {op[0]} {rnd.randint(op[1], op[2])}")
                lines.append(f"{kind} when {' and '.join(conds)}: {rnd.randint(1, 20)}")
        lines.insert(rnd.randint(0, len(lines)), "take: " + rnd.choice(["max", "sum"]))
        sets.append("\n".join(lines))
    return sets
def direct(src, row):
    rates, extras, take = [], [], "max"
    for l in src.splitlines():
        if l.startswith("take:"): take = l.split(":")[1].strip(); continue
        kind, rest = l.split(" when ", 1); conds, val = rest.rsplit(":", 1); ok = True
        for c in conds.split(" and "):
            p = c.split()
            if len(p) == 1: ok &= row[p[0]] > 0
            else: ok &= (row[p[0]] >= float(p[2])) if p[1] == ">=" else (row[p[0]] > float(p[2]))
        (rates if kind == "rate" else extras).append(float(val) if ok else 0.0)
    base = (max(rates) if take == "max" else sum(rates)) if rates else 0.0
    return base + sum(extras)
if __name__ == "__main__":
    json.dump(make(), open(sys.argv[1] if len(sys.argv) > 1 else "rulesets.json", "w"), indent=1)
