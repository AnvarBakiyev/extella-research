#!/usr/bin/env python3
"""One job, three programs, three languages, the same call for each.

  1. poly_open_orders   language readsql  a query in a read-only query language: the five largest open orders
  2. poly_order_stats   language fython   Python: sum, average, largest customer, a verdict (with --math go: the same in Go)
  3. poly_order_report  language page     a small page language: the numbers laid out as a short HTML report
Each program is a separately saved expert. The script calls them one after another with the same API call
(expert/run with the program's name, parameters and a device) and passes the result of one as parameters of the next.
There is no service around any of them; what executes each one is the handler of its language on the device.

The device must already have the handlers of readsql and page (they are registered on our demo servers) and the
sample database. WHAT THIS SCRIPT WRITES: three experts named poly_* are created or overwritten in the Extella account
of the token in ~/.extella/api_token.txt, in the scope of --agent, and remain there. Result: three-languages-<date>.json
next to this script, without the token and device ids.
Usage: python3 three_languages.py --device <device id> [--math go] [--database <path on the device>] [--agent <agent id>]"""
import argparse, ast, json, os, sys, time, urllib.request, urllib.error

API, HOME, HERE = "https://api.extella.ai/api", os.path.expanduser("~/.extella"), os.path.dirname(os.path.abspath(__file__))
PROGRAMS = {
    "poly_open_orders": ("readsql", "SELECT id, customer, total FROM orders WHERE status = 'open' ORDER BY total DESC LIMIT 5"),
    "poly_order_stats": ("fython", '$extens("include.py")\ninclude("import os", [])\n\ndef poly_order_stats(rows: str = "[]") -> dict:\n'
                                   '    import json\n    data = json.loads(rows)\n    totals = [float(r["total"]) for r in data]\n    total = sum(totals)\n'
                                   '    top = max(data, key=lambda r: float(r["total"])) if data else {"customer": "", "total": 0}\n'
                                   '    verdict = "open orders above 30k: review before shipping" if total > 30000 else "within normal range"\n'
                                   '    return {"status": "success", "language": "python", "count": len(data), "sum": total, "average": (total / len(data)) if data else 0.0,\n'
                                   '            "largest_customer": top["customer"], "largest_total": float(top["total"]), "verdict": verdict}\n'),
    "poly_order_report": ("page", "# Open orders\n\n## The numbers\n!number {{count}} | open orders in the top five\n!number {{sum}} | combined value\n!number {{average}} | average order\n\n"
                                  "## What it means\n- Largest: {{largest_customer}}\n- {{verdict}}\n> Built by three programs: readsql for the data, Python for the math, page for this report\n"),
}
GO_STATS = r'''package main

import (
	"encoding/json"
	"fmt"
)

type Row struct {
	ID       int     `json:"id"`
	Customer string  `json:"customer"`
	Total    float64 `json:"total"`
}

func main() {
	var rows []Row
	json.Unmarshal([]byte(`{{rows}}`), &rows)
	sum, top, topCustomer := 0.0, 0.0, ""
	for _, r := range rows {
		sum += r.Total
		if r.Total > top {
			top, topCustomer = r.Total, r.Customer
		}
	}
	avg := 0.0
	if len(rows) > 0 {
		avg = sum / float64(len(rows))
	}
	verdict := "within normal range"
	if sum > 30000 {
		verdict = "open orders above 30k: review before shipping"
	}
	b, _ := json.Marshal(map[string]any{
		"count": len(rows), "sum": sum, "average": avg,
		"largest_customer": topCustomer, "largest_total": top,
		"verdict": verdict, "language": "go"})
	fmt.Print(string(b))
}
'''
ap = argparse.ArgumentParser(); ap.add_argument("--device", required=True); ap.add_argument("--math", default="python", choices=["python", "go"], help="language of the second program; go needs the Go toolchain on the device"); ap.add_argument("--agent", default="agent_extella_default")
ap.add_argument("--device_label", default="a Linux server with the handlers of readsql and page registered"); ap.add_argument("--out", default="")
ap.add_argument("--database", default="extella-demos/shop.db"); ap.add_argument("--save_to", default="extella-demos/report-three-languages.html")
a = ap.parse_args(); TOKEN = open(os.path.join(HOME, "api_token.txt")).read().strip()


def call(path, body, timeout=150):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": a.agent, "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e: return {"status": "error", "reason": "HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:200])}


def run(name, params):
    t0 = time.time(); out = call("/expert/run", {"name": name, "params": params, "targets": [a.device]})
    while isinstance(out, dict) and out.get("task_id") and "result" not in out:
        time.sleep(2); chk = call("/tasks/check", {"task_id": out["task_id"]}, timeout=30)
        out = chk if str(chk.get("status")) in ("completed", "done", "success", "finished", "error", "failed") else {"task_id": out["task_id"]}
    res = out.get("result", out) if isinstance(out, dict) else out
    if isinstance(res, dict) and "result" in res: res = res["result"]
    if isinstance(res, str):
        for loader in (json.loads, ast.literal_eval):
            try: res = loader(res); break
            except Exception: pass
    return (res if isinstance(res, dict) else {"status": "error", "reason": str(res)[:300]}), round(time.time() - t0, 1)


if a.math == "go": PROGRAMS["poly_order_stats"] = ("go", GO_STATS)
for name, (cspl, code) in PROGRAMS.items():
    r = call("/expert/save", {"name": name, "description": "Three-languages example: " + name, "code": code, "cspl": cspl, "kwargs": {}, "global": False})
    if r.get("status") != "success": sys.exit("could not save %s: %s" % (name, r))
steps = []
orders, s1 = run("poly_open_orders", {"database": a.database})
steps.append({"program": "poly_open_orders", "language": "readsql", "seconds": s1, "answer": {k: orders.get(k) for k in ("status", "count", "language", "reason") if k in orders}})
if not orders.get("rows"): print(json.dumps(steps, indent=1)); sys.exit("step 1 returned no rows: " + str(orders)[:300])
stats, s2 = run("poly_order_stats", {"rows": json.dumps(orders["rows"])})
if a.math == "go":                                                   # a compiled program answers on standard output
    try: stats = dict(json.loads(stats.get("stdout") or "{}"), status=stats.get("status"))
    except ValueError: stats = {"status": "error", "reason": str(stats)[:200]}
steps.append({"program": "poly_order_stats", "language": "Go" if a.math == "go" else "fython (Python)", "seconds": s2, "answer": {k: stats.get(k) for k in ("status", "count", "sum", "average", "largest_customer", "verdict", "reason") if k in stats}})
if stats.get("status") != "success": print(json.dumps(steps, indent=1)); sys.exit("step 2 failed")
report, s3 = run("poly_order_report", {"count": str(stats["count"]), "sum": "{:,.0f}".format(stats["sum"]), "average": "{:,.0f}".format(stats["average"]),
                                       "largest_customer": stats["largest_customer"], "verdict": stats["verdict"], "saveTo": a.save_to})
steps.append({"program": "poly_order_report", "language": "page", "seconds": s3, "answer": {k: report.get(k) for k in ("status", "slides", "bytes", "language", "reason") if k in report}})
expected = sum(float(r["total"]) for r in orders["rows"])
res = {"date": time.strftime("%Y-%m-%d %H:%M"), "device": a.device_label, "call": "POST /api/expert/run {name, params, targets} for every step",
       "steps": steps, "checks": {"step 1 returned rows from the database": bool(orders.get("rows")), "step 2 computed the sum of the rows of step 1": abs(stats.get("sum", -1) - expected) < 0.01,
                                  "step 3 produced the report from the numbers of step 2": report.get("status") == "success"},
       "notes": ["Three separately saved programs in three languages; the result of each was passed as parameters of the next by this script.", "No service was built around any program; the Extella service and the listener on the device are the network layer.",
                 "Every call takes seconds: this suits steps of a job, not calls inside a tight loop.", "One device, one day."]}
text = json.dumps(res, ensure_ascii=False, indent=1).replace(TOKEN, "<removed>").replace(a.device, "<device>")
open(a.out or os.path.join(HERE, "three-languages-%s.json" % time.strftime("%Y-%m-%d")), "w", encoding="utf-8").write(text); print(text)
