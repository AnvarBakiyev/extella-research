"""readsql: только SELECT/WITH по базе SQLite, открытой на чтение. Параметр db — путь к базе на устройстве."""
import os, re, sqlite3

def run_sql(sql, db):
    s = sql.strip().rstrip(";")
    if not re.match(r"(?is)^\s*(select|with)\b", s) or ";" in s:
        return {"status": "refused", "reason": "only one SELECT or WITH statement is allowed"}
    if not os.path.exists(os.path.expanduser(db)):
        return {"status": "refused", "reason": f"database not found on this device: {db}"}
    con = sqlite3.connect("file:" + os.path.expanduser(db) + "?mode=ro", uri=True); con.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in con.execute(s)]
    except sqlite3.Error as e:
        return {"status": "refused", "reason": f"query failed: {e}"}
    return {"status": "success", "rows": rows}

def readsql(code="", filtered_source_code="", func_name="", **extra):
    p = dict(extra); p.update(extra.get("kwargs") or {})
    return run_sql(code or filtered_source_code or "", str(p.get("db") or "~/kompoziciya/orders.db"))
