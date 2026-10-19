"""Re-runs every claim of the CSPL description that can be checked on one device and saves the raw answers.
Order: register the tally handler, run a tally program, run a program the language rejects, replace the program and
run again, restore it, then run experts in Go, Rust and C. Writes runs-<date>.json next to this file.
Usage: python3 verify_all.py --agent <agent id> --device <device id>"""
import argparse, json, os, platform, subprocess, time, urllib.request, urllib.error

API = "https://api.extella.ai/api"; HOME = os.path.expanduser("~/.extella"); HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("--agent", default="agent_extella_default"); ap.add_argument("--device", default=open(os.path.join(HOME, "device.txt")).read().strip())
ap.add_argument("--listener", default="", help="listener version, recorded as given"); a = ap.parse_args()
TOKEN = open(os.path.join(HOME, "api_token.txt")).read().strip()


def call(path, body, timeout=150):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": a.agent, "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e: return {"status": "error", "http": e.code, "body": e.read().decode()[:300]}


def save(name, code, cspl, description):
    return call("/expert/save", {"name": name, "description": description, "code": code, "cspl": cspl, "kwargs": {}, "global": False}).get("status")


LOG = []
def run(step, name):
    t0 = time.time(); out = call("/expert/run", {"name": name, "params": {}, "targets": [a.device]})
    while isinstance(out, dict) and out.get("task_id") and "result" not in out:
        time.sleep(2); chk = call("/tasks/check", {"task_id": out["task_id"]}, timeout=30)
        if str(chk.get("status")) in ("completed", "done", "success", "finished", "error", "failed"): out = chk
    rec = {"step": step, "expert": name, "seconds": round(time.time() - t0, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "result": out.get("result"), "status": out.get("status")}
    LOG.append(rec); print("%-34s %5ss  %s" % (step, rec["seconds"], str(rec["result"])[:150])); return rec


handler = open(os.path.join(HERE, "handler.py"), encoding="utf-8").read()
registrar = ('$extens("include.py")\ninclude("import os", [])\n\ndef register_tally() -> dict:\n    import disnet\n    handler_code = \'\'\'' + handler +
             '\'\'\'\n    d = disnet.Disnet(url="https://disnet.extella.ai")\n'
             '    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "tally", "response_format": None}\n'
             '    d.container(code=handler_code, func_name="tally", container_path="tally", args=None, kwargs=envelope, cspl_type="fython", push=False)\n'
             '    return {"status": "success", "registered": "tally", "bytes": len(handler_code)}\n')
save("register_tally", registrar, "fython", "Registers the handler of the tally language on the device it runs on.")
run("register tally handler", "register_tally")
save("tally_demo", "add 5\nadd 7\nsub 2\n", "tally", "A tally program: add 5, add 7, sub 2.")
run("tally program", "tally_demo")
save("tally_bad", "add 5\nimport os\n", "tally", "Not a tally program.")
run("program the language rejects", "tally_bad")
save("tally_demo", "add 100\nsub 1\n", "tally", "A tally program, replaced: add 100, sub 1.")
run("same name, replaced source", "tally_demo")
save("tally_demo", "add 5\nadd 7\nsub 2\n", "tally", "A tally program: add 5, add 7, sub 2.")
GO = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tsum := 0\n\tfor i := 1; i <= 10; i++ {\n\t\tsum += i\n\t}\n\tfmt.Printf("{\\"language\\":\\"go\\",\\"sum\\":%d}", sum)\n}\n'
RUST = 'fn main() {\n    let v: Vec<u64> = (1..=10).collect();\n    let sum: u64 = v.iter().sum();\n    println!("{{\\"language\\":\\"rust\\",\\"sum\\":{}}}", sum);\n}\n'
C = '#include <stdio.h>\nint main(void) {\n    long sum = 0;\n    for (int i = 1; i <= 10; i++) sum += i;\n    printf("{\\"language\\":\\"c\\",\\"sum\\":%ld}", sum);\n    return 0;\n}\n'
hc = open(os.path.join(HERE, "handler_c.py"), encoding="utf-8").read()
reg_c = ('$extens("include.py")\ninclude("import os", [])\n\ndef register_c() -> dict:\n    import disnet\n    handler_code = \'\'\'' + hc +
         '\'\'\'\n    d = disnet.Disnet(url="https://disnet.extella.ai")\n'
         '    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "c", "response_format": None}\n'
         '    d.container(code=handler_code, func_name="c", container_path="c", args=None, kwargs=envelope, cspl_type="fython", push=False)\n'
         '    return {"status": "success", "registered": "c"}\n')
save("tiny_go_sum", GO, "go", "Go: sum of 1..10, prints JSON."); run("go expert (handler already on device)", "tiny_go_sum")
save("tiny_rust_sum", RUST, "rust", "Rust: sum of 1..10, prints JSON."); run("rust expert (handler already on device)", "tiny_rust_sum")
save("register_c", reg_c, "fython", "Registers a handler for C: compile with the device compiler and run."); run("register c handler", "register_c")
save("tiny_c_sum", C, "c", "C: sum of 1..10, prints JSON."); run("c expert", "tiny_c_sum")
git = subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
out = {"date": time.strftime("%Y-%m-%d"), "machine": platform.platform(), "python": platform.python_version(), "listener": a.listener, "source_commit": git,
       "note": "device host names are kept as returned; agent and device ids are not recorded", "runs": LOG}
p = os.path.join(HERE, "runs-%s.json" % out["date"]); json.dump(out, open(p, "w"), ensure_ascii=False, indent=1); print("saved", p)
