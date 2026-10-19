#!/usr/bin/env python3
"""Opyt 16: life cycle of replacing one operation used by several consumers.
One operation (fund value at the second custodian), three consumers (two on the laptop, one on the server), replacement of the
implementation Python -> Go with the same contract, a call that is in flight during the replacement, then a rollback.
Arm "extella": the operation is a saved expert. Arm "plain": the operation is a local program called as a subprocess.
Consumers are never edited. Usage: run16.py extella|plain"""
import base64, json, os, shlex, subprocess, sys, threading, time, urllib.request, urllib.error
from pathlib import Path
H = Path(__file__).resolve().parent; arm = sys.argv[1]; rec = {"arm": arm, "timeline": []}; T0 = time.time()
ENV = dict(l.split("=", 1) for l in Path("<repo>/.env").read_text().splitlines() if "=" in l and not l.lstrip().startswith("#"))
clean = lambda v: v.strip().strip("\"'"); SSH = shlex.split(clean(ENV["RECON_SSH"]))
LAPTOP_CSV = "<repo>/data/generated/custodian2_statement.csv"; SERVER_CSV = "/srv/recon-data/custodian2_statement.csv"; WANT = 492127140105.4
def note(what, **kw): rec["timeline"].append({"at": round(time.time() - T0, 1), "what": what, **kw}); print(round(time.time() - T0, 1), what, json.dumps(kw, ensure_ascii=False)[:230], flush=True)
def judge(out): return {"impl": out.get("impl") if isinstance(out, dict) else None, "correct": isinstance(out, dict) and abs(float(out.get("value_usd", 0)) - WANT) < 0.01, "error": None if isinstance(out, dict) and "impl" in out else str(out)[:160]}

if arm == "extella":
    TOKEN = Path(os.path.expanduser(clean(ENV["RECON_TOKEN_FILE"]))).read_text().strip(); AG = "<agent-id>"; DEV = {"laptop": clean(ENV["RECON_DEVICE_A"]), "server": clean(ENV["RECON_DEVICE_B"])}
    def call(path, body):
        req = urllib.request.Request("https://api.extella.ai/api" + path, data=json.dumps(body).encode(), headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": AG, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r: return json.load(r)
        except urllib.error.HTTPError as ex: return {"status": "error", "message": "HTTP %s %s" % (ex.code, ex.read().decode()[:150])}
    def unwrap(x):
        for _ in range(8):
            if isinstance(x, str):
                try: x = json.loads(x); continue
                except ValueError: return x
            if isinstance(x, dict) and "result" in x and "impl" not in x: x = x["result"]; continue
            return x
        return x
    def run(name, device, params=None):
        x = call("/expert/run", {"name": name, "params": params or {}, "targets": [DEV[device]]})
        while isinstance(x, dict) and x.get("task_id") and x.get("status") not in ("completed", "error", "failed"): time.sleep(2); x = call("/tasks/check", {"task_id": x["task_id"]})
        return unwrap(x)
    def save(name, code, lang):
        r = call("/expert/save", {"name": name, "description": "opyt16: " + name, "code": code, "cspl": lang, "kwargs": {}, "global": False}); assert r.get("status") == "success", r
    body = (H / "fund_value_v1.py").read_text().split("def fund_value(fund, statement, pause=0):", 1)[1].split("if __name__", 1)[0]
    V1 = '$extens("include.py")\ninclude("import os", [])\ndef opyt16_fund_value(fund, statement, pause=0):\n    import csv, json, time\n' + body.rstrip().replace("    return {", "    return json.dumps({").rstrip() + ")\n"
    V2 = (H / "fund_value_v2.go").read_text()
    def op(device, pause=0): return run("opyt16_fund_value", device, {"fund": "FUND045", "statement": LAPTOP_CSV if device == "laptop" else SERVER_CSV, "pause": pause})
    def prepare():
        b64 = base64.b64encode((H / "handler_go.py").read_text().encode()).decode()
        handler = 'def opyt16go(code="", filtered_source_code="", func_name="", **extra):\n    import base64,json\n    ns={}\n    exec(base64.b64decode("' + b64 + '").decode(),ns)\n    return json.dumps(ns["execute"](code or filtered_source_code,extra.get("kwargs") or extra))\n'
        registrar = '$extens("include.py")\ninclude("import os", [])\ndef opyt16_register_go():\n    import disnet,json\n    handler_code = ' + repr(handler) + '\n    d=disnet.Disnet(url="https://disnet.extella.ai")\n    d.container(code=handler_code,func_name="opyt16go",container_path="opyt16go",args=None,kwargs={"filtered_source_code":"","func_name":"","args":None,"kwargs":None,"cspl":"opyt16go","response_format":None},cspl_type="fython",push=False)\n    return json.dumps({"status":"success","registered":"opyt16go"})\n'
        save("opyt16_register_go", registrar, "fython"); a = run("opyt16_register_go", "laptop"); b = run("opyt16_register_go", "server"); save("opyt16_fund_value", V1, "fython"); return 5, str(a)[:60] + " / " + str(b)[:60]
    def swap(): save("opyt16_fund_value", V2, "opyt16go"); return 1
    def rollback(): save("opyt16_fund_value", V1, "fython"); return 1
else:
    P = H / "plain"; (P / "ops").mkdir(parents=True, exist_ok=True); OP = P / "ops" / "fund_value"; REMOTE = "/srv/recon-data/opyt16/ops"
    def ssh(cmd, **kw): return subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=300, **kw)
    def op(device, pause=0):
        if device == "laptop": r = subprocess.run([str(OP), "FUND045", LAPTOP_CSV, str(pause)], capture_output=True, text=True)
        else: r = ssh(f"{REMOTE}/fund_value FUND045 {SERVER_CSV} {pause}")
        try: return json.loads(r.stdout)
        except Exception: return (r.stderr or r.stdout).strip()[-200:] or "no output"
    def put(local, n=0):
        tmp = OP.with_suffix(".new"); tmp.write_bytes(Path(local[0]).read_bytes()); tmp.chmod(0o755); os.replace(tmp, OP)                       # atomic on the laptop
        subprocess.run(["scp", "-q"] + SSH[1:-1] + [local[1], SSH[-1] + ":" + REMOTE + "/fund_value.new"], check=True); ssh(f"chmod 755 {REMOTE}/fund_value.new && mv {REMOTE}/fund_value.new {REMOTE}/fund_value")
        return 4
    def prepare():
        ssh(f"sudo mkdir -p {REMOTE} && sudo chown -R ubuntu {REMOTE}/.."); n = put((H / "fund_value_v1.py", H / "fund_value_v1.py")); return n + 1, "python script with a shebang placed on both machines"
    def swap():
        n = 0
        for goos, arch, out in (("darwin", "arm64", "v2-darwin"), ("linux", "amd64", "v2-linux")):
            subprocess.run(["/opt/homebrew/bin/go", "build", "-o", str(P / out), str(H / "fund_value_v2.go")], check=True, env={**os.environ, "GOOS": goos, "GOARCH": arch, "CGO_ENABLED": "0"}); n += 1
        (P / "fund_value.prev").write_bytes(OP.read_bytes()); ssh(f"cp {REMOTE}/fund_value {REMOTE}/fund_value.prev"); n += 2
        return n + put((P / "v2-darwin", P / "v2-linux"))
    def rollback():
        tmp = OP.with_suffix(".new"); tmp.write_bytes((P / "fund_value.prev").read_bytes()); tmp.chmod(0o755); os.replace(tmp, OP); ssh(f"cp {REMOTE}/fund_value.prev {REMOTE}/fund_value.new && mv {REMOTE}/fund_value.new {REMOTE}/fund_value"); return 2

CONSUMERS = [("report", "laptop"), ("dashboard", "laptop"), ("night_job", "server")]
def everyone(label):
    out = {}
    for name, device in CONSUMERS:
        t = time.time(); out[name] = {**judge(op(device)), "seconds": round(time.time() - t, 1)}
    note(label, **out); return out
t = time.time(); n, info = prepare(); rec["prepare"] = {"actions": n, "seconds": round(time.time() - t, 1), "info": info}; note("prepared", **rec["prepare"])
rec["before"] = everyone("all consumers, first implementation")
box = {}; th = threading.Thread(target=lambda: box.update(out=op("laptop", 30))); t_long = time.time(); th.start(); time.sleep(12)
t = time.time(); n = swap(); rec["swap"] = {"actions": n, "seconds": round(time.time() - t, 1)}; note("implementation replaced while a 30-second call is running", **rec["swap"])
quick = judge(op("laptop")); note("a new call made right after the replacement", **quick); rec["new_call_right_after_swap"] = quick
th.join(); rec["in_flight"] = {**judge(box["out"]), "seconds": round(time.time() - t_long, 1)}; note("the call that was in flight finished", **rec["in_flight"])
rec["after_swap"] = everyone("all consumers, after the replacement")
t = time.time(); n = rollback(); rec["rollback"] = {"actions": n, "seconds": round(time.time() - t, 1)}; note("rolled back to the first implementation", **rec["rollback"])
rec["after_rollback"] = everyone("all consumers, after the rollback")
(H / ("result_%s.json" % arm)).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
