"""Проверка перед заменой steps (одинаковая для обеих сторон): кандидат прогоняется по всем 100 программам.
Допустимое изменение одно: программа, где ставка бывает > 30, получает отказ по закону 30 %. Любое другое — блок."""
import hashlib, json
def check(mod, cases, rows):
    bad = []
    for i, c in enumerate(cases):
        r = mod.run_map(c["plan"], rows, ["rate"] + (["total"] if "total =" in c["plan"] else []))
        sha = hashlib.sha256(json.dumps(r.get("rows"), sort_keys=True).encode()).hexdigest()[:16] if r["status"] == "success" else None
        expected_refusal = c["over30"] and r["status"] == "refused" and "30% limit" in r.get("reason", "")
        if not expected_refusal and (r["status"] != c["status"] or sha != c["sha"]):
            bad.append({"program": i + 1, "was": c["status"], "now": r["status"], "reason": r.get("reason", "")[:80]})
        if c["over30"] and r["status"] == "success": bad.append({"program": i + 1, "was": "over 30", "now": "accepted"})
    return bad
