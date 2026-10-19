#!/usr/bin/env python3
# Operation "fund value at the second custodian": sum of quantity x price x FX over the rows of one fund.
# Contract: arguments fund, statement, pause (seconds of extra work); answer JSON {fund, value_usd, rows, impl}.
import csv, json, sys, time
def fund_value(fund, statement, pause=0):
    total = 0.0; rows = 0; num = lambda v: float(v.replace(",", "."))
    with open(statement, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["Portfolio"].strip() == fund: total += num(r["Settled holding"]) * num(r["Market price"]) * num(r["FX to USD"]); rows += 1
    time.sleep(float(pause))
    return {"fund": fund, "value_usd": round(total, 2), "rows": rows, "impl": "python-v1"}
if __name__ == "__main__": print(json.dumps(fund_value(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 0)))
