"""K4 на Extella: одна команда — на каждом устройстве кандидат steps проверяется на 100 программах по базе устройства
и ставится как k3_steps только при чистой проверке; при отказе на первом устройстве дальше не идём."""
import base64, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "gsm8k-infrastructure-vs-assembly", "seriya2")); import ext
cand = open(sys.argv[1], encoding="utf-8").read(); chk = open(os.path.join(ROOT, "k4", "check.py"), encoding="utf-8").read()
b = lambda s: base64.b64encode(s.encode()).decode()
code = '''def k3_publish_steps(cases: list = None, db: str = "~/kompoziciya/orders.db") -> dict:
    import base64, hashlib, os, sqlite3, types, disnet
    cand = base64.b64decode("%s").decode("utf-8")
    m = types.ModuleType("candidate"); exec(cand, m.__dict__)
    ns = {}; exec(base64.b64decode("%s").decode("utf-8"), ns)
    rows = [dict(zip(("is_wholesale", "is_vip", "qty", "price_cents", "coupon"), r)) for r in sqlite3.connect(os.path.expanduser(db)).execute("SELECT is_wholesale, is_vip, qty, price_cents, coupon FROM orders ORDER BY id")]
    bad = ns["check"](m, cases or [], rows); sha = hashlib.sha256(cand.encode()).hexdigest()[:12]
    if bad: return {"status": "refused", "installed": False, "candidate": sha, "blocked_by": len(bad), "examples": bad[:3]}
    env = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "k3_steps", "response_format": None}
    disnet.Disnet(url="https://disnet.extella.ai").container(code=cand, func_name="steps", container_path="k3_steps", args=None, kwargs=env, cspl_type="fython", push=False)
    return {"status": "success", "installed": True, "candidate": sha, "checked": len(cases or [])}
''' % (b(cand), b(chk))
ext.save("k3_publish_steps", code, "fython", "Series 3 K4: checks a candidate k3_steps handler on saved programs and installs it only if nothing unexpected changes.", {"cases": [], "db": "~/kompoziciya/orders.db"})
cases = json.load(open(os.path.join(ROOT, "k4", "cases.json")))
for name, t in (("mac", ext.MAC), ("server-1", ext.VPS)):
    r, dt = ext.run("k3_publish_steps", {"cases": cases}, t); r = r.get("result", r) if isinstance(r, dict) and "installed" not in r else r
    print(name, round(dt, 1), "с", {k: r.get(k) for k in ("status", "installed", "candidate", "blocked_by", "checked")} if isinstance(r, dict) else str(r)[:200])
    if isinstance(r, dict) and r.get("status") == "refused": sys.exit("отказ на " + name + ": дальше не публикую")
