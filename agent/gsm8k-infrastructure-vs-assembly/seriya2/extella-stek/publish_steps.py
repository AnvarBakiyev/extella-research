"""publish_steps.py <кандидат steps_handler.py>: одна команда — на Mac и на VPS кандидат проверяется на 40 планах
и регистрируется как язык steps только при чистой проверке (иначе остаётся прежняя версия)."""
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ext
HERE = os.path.dirname(os.path.abspath(__file__))
cand = open(sys.argv[1], encoding="utf-8").read()
check = open(os.path.join(HERE, "..", "s2", "check_release.py"), encoding="utf-8").read().split('if __name__')[0]
code = '''$extens("include.py")
include("import os", [])

def gsm_publish_steps(cases: list = None) -> dict:
    import base64, hashlib, types, disnet
    cand = base64.b64decode("%s").decode("utf-8")
    m = types.ModuleType("candidate"); exec(cand, m.__dict__)
    ns = {}; exec(base64.b64decode("%s").decode("utf-8"), ns)
    bad = ns["check"](m, cases or [])
    sha = hashlib.sha256(cand.encode()).hexdigest()[:12]
    if bad:
        return {"status": "refused", "installed": False, "candidate": sha, "changed": len(bad), "examples": bad[:3]}
    d = disnet.Disnet(url="https://disnet.extella.ai")
    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "steps", "response_format": None}
    d.container(code=cand, func_name="steps", container_path="steps", args=None, kwargs=envelope, cspl_type="fython", push=False)
    return {"status": "success", "installed": True, "candidate": sha, "checked": len(cases or [])}
''' % (base64.b64encode(cand.encode()).decode(), base64.b64encode(check.encode()).decode())
ext.save("gsm_publish_steps", code, "fython", "Checks a candidate steps handler against saved plans and registers it on this device only if no outcome changes.", {"cases": []})
cases = json.load(open(os.path.join(HERE, "..", "s2", "cases.json")))
for name, t in (("mac", ext.MAC), ("second", "<server-2-device-id>")):
    r, dt = ext.run("gsm_publish_steps", {"cases": cases}, t)
    r = r.get("result", r) if isinstance(r, dict) else r
    print(name, round(dt, 1), "с", r if not isinstance(r, dict) else {k: r.get(k) for k in ("status", "installed", "candidate", "changed", "checked")})
    if isinstance(r, dict) and r.get("status") == "refused": sys.exit("отказ на " + name + ": дальше не публикую")
