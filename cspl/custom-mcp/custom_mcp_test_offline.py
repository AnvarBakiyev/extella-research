#!/usr/bin/env python3
"""Offline checks of extella_custom_mcp.py: the Extella API is replaced by a stub, nothing leaves this machine.
Covers what the recorded session cannot show safely: failures of the API in the middle of a job.
Usage: python3 test_offline.py"""
import asyncio, json, os, sys, tempfile

home = tempfile.mkdtemp(prefix="cmcp-test-")
os.environ.update(EXTELLA_CUSTOM_MCP_HOME=home, EXTELLA_RUN_WAIT="7", EXTELLA_TOKEN_FILE=os.devnull)
json.dump({"server": "device-1"}, open(os.path.join(home, "devices.json"), "w"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extella_custom_mcp as m

store, plan = {}, {}                                                     # name -> (code, cspl); path -> list of forced answers


def stub(path, body, timeout=60):
    if plan.get(path):
        return plan[path].pop(0)
    if path == "/expert/get":
        if body["name"] not in store:
            return {"status": "error", "reason": 'HTTP 500: {"status":"error","message":"Expert not found"}'}
        code, cspl = store[body["name"]]
        return {"status": "success", "expert_code": code.rstrip("\n"), "cspl": cspl, "expert_description": ""}
    if path == "/expert/save":
        store[body["name"]] = (body["code"], body["cspl"]); return {"status": "success"}
    if path == "/expert/run":
        return {"status": "success", "result": "{'status': 'success', 'value': 1}"}
    raise AssertionError(path)


m._call = stub
run = lambda **k: asyncio.run(m.run_program(**k))
checks = {}

a = m.save_program("q", "SELECT 1", "fython"); b = m.save_program("q", "SELECT 1", "readsql"); m.save_program("q", "SELECT 2", "readsql"); m.rollback("q", b["version"])
checks["the same code in another language is a new version, and a rollback restores that language"] = (a["version"], b["version"], b["new_version"], store["q"]) == (1, 2, True, ("SELECT 1", "readsql"))

store["w"] = ("outside copy", "fython"); plan["/expert/get"] = [{"status": "error", "reason": "HTTP 502: bad gateway"}]
r = m.save_program("w", "def w():\n    return {}\n")
checks["a save is refused when the current copy cannot be read"] = r["status"] == "error" and "nothing was changed" in r["error"] and store["w"][0] == "outside copy"
r = m.save_program("w", "def w():\n    return {}\n"); h = m.history("w")["versions"]
checks["the copy a save replaces is kept first"] = r["status"] == "success" and [v["note"] for v in h] == ["saved outside this server", ""] and store["w"][0].startswith("$extens(")

plan["/expert/save"] = [{"status": "queued"}]
checks["a save Extella did not confirm is not recorded as a version"] = m.save_program("w", "def w():\n    return {'v': 2}\n")["status"] == "error" and len(m.history("w")["versions"]) == 2

plan["/expert/run"] = [{"task_id": "t1"}]; plan["/tasks/check"] = [{"status": "error", "reason": "Extella is not reachable: x", "unreachable": True}, {"status": "completed", "result": "{'status': 'success', 'value': 2}"}]
r = run(name="w", device="server")
checks["a failed check of a deferred run is not taken for a failed run"] = r["status"] == "success" and r["result"]["value"] == 2

plan["/expert/run"] = [{"task_id": "t2"}]; plan["/tasks/check"] = [{"status": "error", "result": "Traceback: boom"}]
r = run(name="w", device="server")
checks["a run that finished with an error and a text is an error"] = r["status"] == "error" and "boom" in str(r["result"])

plan["/expert/run"] = [{"task_id": "t3", "result": "deferred, check later"}]; plan["/tasks/check"] = [{"status": "running"}] * 9
r = run(name="w", device="server")
checks["a run with no answer in time says so and gives the task id"] = r["status"] == "error" and "no answer" in r["error"] and r["task_id"] == "t3"

plan["/expert/run"] = [{"status": "error", "reason": "no answer in 7 s", "unreachable": True, "timed_out": True}]
checks["a held connection is reported as no answer, not as unreachable"] = "no answer" in run(name="w", device="server")["error"]
checks["an empty device name is refused"] = run(name="w")["status"] == "error"
checks["the run log marks failed runs"] = [x["ok"] for x in m.history("w")["last_runs"]] == [False, False, False, True]

print(json.dumps(checks, indent=1)); sys.exit(0 if all(checks.values()) else 1)
