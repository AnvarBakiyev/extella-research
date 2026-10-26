"""card: отчёт карточками. Программа — строки «ключ: значения»:
  title: <заголовок>      group: <поле>      count: <имя>      sum: <поля через пробел>      money: <поля>
Вход (параметр rows) — строки данных. Выход: агрегаты (целые) и HTML, все строки экранированы."""
import html

def parse(src):
    p = {"title": "Report", "group": None, "count": None, "sum": [], "money": []}
    for n, line in enumerate([l for l in src.splitlines() if l.strip() and not l.strip().startswith("#")], 1):
        if ":" not in line: raise ValueError(f"line {n}: expected 'key: value'")
        k, v = [x.strip() for x in line.split(":", 1)]
        if k not in p: raise ValueError(f"line {n}: unknown key '{k}'; allowed: title, group, count, sum, money")
        p[k] = v.split() if k in ("sum", "money") else v
    if not p["group"]: raise ValueError("a card program needs 'group: <field>'")
    return p

def money(c): return f"{int(c) // 100:,}".replace(",", " ") + f".{int(c) % 100:02d}"

def render(src, rows):
    try: p = parse(src)
    except ValueError as e: return {"status": "refused", "reason": str(e)}
    agg = {}
    for i, r in enumerate(rows):
        if p["group"] not in r: return {"status": "refused", "reason": f"row {i + 1} has no field '{p['group']}'"}
        a = agg.setdefault(str(r[p["group"]]), {})
        if p["count"]: a[p["count"]] = a.get(p["count"], 0) + 1
        for f in p["sum"]:
            if f not in r: return {"status": "refused", "reason": f"row {i + 1} has no field '{f}'"}
            a[f] = a.get(f, 0) + int(round(float(r[f])))
    agg = dict(sorted(agg.items()))
    cols = ([p["count"]] if p["count"] else []) + p["sum"]
    cards = "".join(f"<section class='card'><h3>{html.escape(g)}</h3>" + "".join(
        f"<p>{html.escape(c)}: {money(v[c]) if c in p['money'] else v[c]}</p>" for c in cols) + "</section>" for g, v in agg.items())
    return {"status": "success", "aggregates": agg, "html": f"<h2>{html.escape(p['title'])}</h2>{cards}"}

def card(code="", filtered_source_code="", func_name="", **extra):
    p = dict(extra); p.update(extra.get("kwargs") or {})
    return render(code or filtered_source_code or "", p.get("rows") or [])
