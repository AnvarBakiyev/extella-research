"""Собирает эксперты Extella-стороны серии 3: регистратор языков k3_* и построитель базы заказов на устройстве."""
import base64, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "gsm8k-infrastructure-vs-assembly", "seriya2")); import ext
L = lambda f: open(os.path.join(ROOT, "langs", f), encoding="utf-8").read()
CALL = '''
def _run_lang(lang, code, params):
    import os
    from extella_listener.executor import run_container
    wd = next((d for d in (os.getcwd(), os.path.expanduser("~/.extella"), "/opt/extella-listener") if os.path.exists(os.path.join(d, "containers_folder", lang))), os.getcwd())
    return run_container({"cspl": lang, "filtered_source_code": code, "func_name": "program", "args": [], "kwargs": params}, work_dir=wd)
'''
HANDLERS = {
    "k3_readsql": (L("readsql.py"), "readsql"),
    "k3_steps": (L("steps.py"), "steps"),
    "k3_card": (L("card.py"), "card"),
    "k3_rulebook": (L("rulebook.py") + CALL + '''
def rulebook(code="", filtered_source_code="", func_name="", **extra):
    p = dict(extra); p.update(extra.get("kwargs") or {})
    return run(code or filtered_source_code or "", p.get("rows") or [], lambda plan, rows, outs: _run_lang("k3_steps", plan, {"mode": "map", "rows": rows, "outputs": outs}))
''', "rulebook"),
    "k3_chain": (L("chain.py") + CALL + '''
def chain(code="", filtered_source_code="", func_name="", **extra):
    p = dict(extra); p.update(extra.get("kwargs") or {})
    return run(code or filtered_source_code or "", p, _run_lang)
''', "chain"),
}
def register_code(only=None):
    items = {k: v for k, v in HANDLERS.items() if not only or k in only}
    blob = base64.b64encode(repr({k: (base64.b64encode(c.encode()).decode(), f) for k, (c, f) in items.items()}).encode()).decode()
    return '''$extens("include.py")
include("import os", [])

def k3_register_langs() -> dict:
    import base64, hashlib, ast, disnet
    items = ast.literal_eval(base64.b64decode("%s").decode())
    d = disnet.Disnet(url="https://disnet.extella.ai"); out = {}
    for lang, (b64, fn) in items.items():
        code = base64.b64decode(b64).decode("utf-8")
        env = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": lang, "response_format": None}
        d.container(code=code, func_name=fn, container_path=lang, args=None, kwargs=env, cspl_type="fython", push=False)
        out[lang] = hashlib.sha256(code.encode()).hexdigest()[:12]
    return {"status": "success", "registered": out}
''' % blob
DB = L("../data/make_orders.py").split('if __name__')[0]
DB_CODE = DB + '''
def k3_build_db(path: str = "~/kompoziciya/orders.db") -> dict:
    import os, hashlib, sqlite3
    p = os.path.expanduser(path); os.makedirs(os.path.dirname(p), exist_ok=True); build(p)
    rows = sqlite3.connect(p).execute("SELECT * FROM orders ORDER BY id").fetchall()
    return {"status": "success", "path": p, "rows": len(rows), "content_sha": hashlib.sha256(repr(rows).encode()).hexdigest()[:16]}
'''
# эксперт должен начинаться с вызываемой функции (урок серии 2): переставляем
DB_CODE = DB_CODE[DB_CODE.index("def k3_build_db"):] + "\n" + DB_CODE[:DB_CODE.index("def k3_build_db")]
if __name__ == "__main__":
    print(ext.save("k3_register_langs", register_code(), "fython", "Registers the series 3 languages k3_readsql, k3_steps, k3_card, k3_rulebook, k3_chain on this device."))
    print(ext.save("k3_build_db", DB_CODE, "fython", "Builds the deterministic 2000-order SQLite database for series 3 on this device.", {"path": "~/kompoziciya/orders.db"}))
