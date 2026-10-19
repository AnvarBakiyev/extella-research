"""The smallest complete CSPL example: declare a language (tally), register its handler on a device, save a program
in it as an expert, run the expert on the device. Uses the token and device id that an installed Extella writes to
~/.extella/. Usage: python3 run_tiny.py [--agent <agent id>] [--device <device id>]"""
import argparse, json, os, time, urllib.request, urllib.error

API = "https://api.extella.ai/api"
HOME = os.path.expanduser("~/.extella")
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("--agent", default="agent_extella_default")
ap.add_argument("--device", default=open(os.path.join(HOME, "device.txt")).read().strip() if os.path.exists(os.path.join(HOME, "device.txt")) else "")
a = ap.parse_args(); TOKEN = open(os.path.join(HOME, "api_token.txt")).read().strip()


def call(path, body, timeout=150):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": a.agent, "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e: return {"status": "error", "http": e.code, "body": e.read().decode()[:300]}


def run(name, params=None):
    t0 = time.time(); out = call("/expert/run", {"name": name, "params": params or {}, "targets": [a.device]})
    while isinstance(out, dict) and out.get("task_id") and "result" not in out:      # long calls come back deferred
        time.sleep(2); out = call("/tasks/check", {"task_id": out["task_id"]}, timeout=30)
        if str(out.get("status")) not in ("completed", "done", "success", "finished", "error", "failed"): out = {"task_id": out.get("task_id") or ""}
    return out, round(time.time() - t0, 1)


handler = open(os.path.join(HERE, "handler.py"), encoding="utf-8").read()
assert chr(92) not in handler and "'" * 3 not in handler            # the handler text is embedded in a string literal
# 1. the registrar: an ordinary expert in the built-in language fython that registers the handler for "tally" on the device it runs on
registrar = ('$extens("include.py")\ninclude("import os", [])\n\ndef register_tally() -> dict:\n    import disnet\n    handler_code = \'\'\'' + handler +
             '\'\'\'\n    d = disnet.Disnet(url="https://disnet.extella.ai")\n'
             '    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "tally", "response_format": None}\n'
             '    d.container(code=handler_code, func_name="tally", container_path="tally", args=None, kwargs=envelope, cspl_type="fython", push=False)\n'
             '    return {"status": "success", "registered": "tally", "bytes": len(handler_code)}\n')
print("save registrar :", call("/expert/save", {"name": "register_tally", "description": "Registers the handler of the tally language on the device it runs on.", "code": registrar, "cspl": "fython", "kwargs": {}, "global": False}).get("status"))
out, s = run("register_tally"); print("register on device (%ss):" % s, str(out.get("result"))[:120])
# 2. a program in the new language, saved as an expert
print("save program   :", call("/expert/save", {"name": "tally_demo", "description": "A tally program: add 5, add 7, sub 2.", "code": "add 5\nadd 7\nsub 2\n", "cspl": "tally", "kwargs": {}, "global": False}).get("status"))
out, s = run("tally_demo"); print("run on device (%ss):" % s, str(out.get("result"))[:200])
# 3. a program the language cannot express is rejected by the handler
print("save bad       :", call("/expert/save", {"name": "tally_bad", "description": "Not a tally program.", "code": "add 5\nimport os\n", "cspl": "tally", "kwargs": {}, "global": False}).get("status"))
out, s = run("tally_bad"); print("run bad (%ss):" % s, str(out.get("result"))[:200])
