"""chain: цепочка программ на разных языках. Программа — JSON-список звеньев {"lang", "code", "params"}.
Строки данных идут от звена к звену: ответ с полем rows заменяет или дополняет строки (merge по позиции).
Ошибка звена возвращается с его номером и языком. Способ вызвать язык задаёт сторона (call)."""
import json

def run(src, params, call):
    try: links = json.loads(src)
    except ValueError as e: return {"status": "refused", "reason": f"chain program is not JSON: {e}"}
    rows = params.get("rows"); last = None
    for i, l in enumerate(links, 1):
        p = dict(l.get("params") or {}); p.setdefault("db", params.get("db"))
        if rows is not None: p["rows"] = rows
        r = call(l["lang"], l["code"], p)
        if not isinstance(r, dict) or r.get("status") != "success":
            return {"status": "refused", "reason": f"link {i} ({l['lang']}): " + str((r or {}).get("reason") if isinstance(r, dict) else r)[:300]}
        if "rows" in r:
            rows = r["rows"] if rows is None or l.get("merge") is not True else [dict(a, **b) for a, b in zip(rows, r["rows"])]
        last = r
    return last
