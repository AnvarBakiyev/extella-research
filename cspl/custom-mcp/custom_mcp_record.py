#!/usr/bin/env python3
"""Records one session with the custom MCP server (extella_custom_mcp.py) against a real Extella account.

An MCP client (official Python SDK, stdio) starts the server and does what an agent would do: lists the tools, saves a
program in plain Python, runs it on a server, saves a changed version, compares the two, rolls back, runs the restored
version on a second machine chosen by name, notices a save made outside the server, and, with the API address pointed
at a closed local port, reads the code from the local history and is refused a save.
For comparison it also lists the tools of the standard Extella MCP server in the same minute and measures both lists
the same way.

WHAT THIS SCRIPT WRITES: one private expert named cmcp_price_with_tax is created or overwritten in the Extella account
of the token in ~/.extella/api_token.txt, in the scope of --agent, and remains there; the last step leaves a
placeholder in it, so that the next recording starts from the same state. The history file of this session
is created in a temporary directory and removed at the end. Result: custom-mcp-<date>.json next to this script, without
the token and the device ids.
Usage: python3 record.py --server <device id> --laptop <device id> [--agent <agent id>]"""
import argparse, asyncio, json, os, shutil, sys, tempfile, time, urllib.request
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment
from mcp.client.streamable_http import streamablehttp_client

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "cmcp_price_with_tax"
CODE = ('def cmcp_price_with_tax(price: float = 0.0) -> dict:\n    import platform\n'
        '    return {"status": "success", "total": round(float(price) * %s, 2), "rate": "%s", "os": platform.system()}\n')
V1, V2 = CODE % ("1.10", "10%"), CODE % ("1.12", "12%")                    # plain Python: the server adds the header Extella needs
HEADER = '$extens("include.py")\ninclude("import os", [])\n\n'
PARKED = HEADER + 'def cmcp_price_with_tax(price: float = 0.0) -> dict:\n    return {"status": "success", "note": "placeholder left by the recording script"}\n'
ap = argparse.ArgumentParser(); ap.add_argument("--server", required=True); ap.add_argument("--laptop", required=True); ap.add_argument("--agent", default="agent_extella_default")
a = ap.parse_args()
TOKEN = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()


def listing(tools):
    full = [t.model_dump(mode="json", exclude_none=True) for t in tools]
    core = [{k: d[k] for k in ("name", "description", "inputSchema") if k in d} for d in full]
    return {"count": len(tools), "definitions_bytes": len(json.dumps(full)), "definitions_bytes_name_description_input_schema": len(json.dumps(core)),
            "names": [t.name for t in tools]}


def value(res):
    try: return json.loads(res.content[0].text)
    except ValueError: raise RuntimeError("the tool answered with text, not JSON: " + res.content[0].text[:400])


async def standard():
    headers = {"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": a.agent}
    async with streamablehttp_client("https://api.extella.ai/mcp/", headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            out = listing((await s.list_tools()).tools); out.pop("names")
            return out


async def session(home, steps, env_extra=None):
    env = dict(get_default_environment(), EXTELLA_CUSTOM_MCP_HOME=home, EXTELLA_AGENT_ID=a.agent, **(env_extra or {}))
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[os.path.join(HERE, "extella_custom_mcp.py")], env=env)) as (r, w):
        async with ClientSession(r, w, read_timeout_seconds=timedelta(seconds=180)) as s:
            await s.initialize()
            return await steps(s)


async def main_steps(s):
    log, checks = [], {}

    async def tool(tool_name, **args):
        t0 = time.time(); out = value(await s.call_tool(tool_name, args))
        log.append({"tool": tool_name, "arguments": {k: (v if k != "code" else "<%d lines>" % (v.count(chr(10)))) for k, v in args.items()}, "seconds": round(time.time() - t0, 1),
                    "answer": {k: v for k, v in out.items() if k not in ("code",)}})
        return out

    tools = listing((await s.list_tools()).tools)
    one = await tool("save_program", name=NAME, code=V1, language="python", description="Price with tax (custom MCP record)", note="rate 10%")
    first = one["version"]
    checks["the first save makes a new version and keeps the copy it replaced"] = one["new_version"] is True and first == 2
    r1 = await tool("run_program", name=NAME, params={"price": 100}, device="server")
    checks["the saved program answers 110.0 on the server"] = r1.get("result", {}).get("total") == 110.0 and r1["result"].get("os") == "Linux"
    two = await tool("save_program", name=NAME, code=V2, language="python", description="Price with tax (custom MCP record)", note="rate 12%")
    r2 = await tool("run_program", name=NAME, params={"price": 100}, device="server")
    checks["the changed version answers 112.0 on the server"] = r2.get("result", {}).get("total") == 112.0 and two["version"] == first + 1
    same = await tool("save_program", name=NAME, code=V2, language="python", description="Price with tax (custom MCP record)", note="the same code again")
    checks["saving the same code makes no new version"] = same["new_version"] is False and same["version"] == two["version"]
    d = await tool("diff_versions", name=NAME, old=first, new=two["version"])
    checks["the diff shows the changed line"] = "-" in d["diff"] and "1.10" in d["diff"] and "1.12" in d["diff"]
    back = await tool("rollback", name=NAME, version=first)
    r3 = await tool("run_program", name=NAME, params={"price": 100}, device="laptop")
    checks["after the rollback the laptop answers 110.0"] = r3.get("result", {}).get("total") == 110.0 and r3["result"].get("os") == "Darwin" and back["version"] == two["version"] + 1
    # a save made outside this server (plain API, as the standard server or another tool would do)
    req = urllib.request.Request("https://api.extella.ai/api/expert/save", data=json.dumps({"name": NAME, "description": "Price with tax (custom MCP record)",
          "code": HEADER + CODE % ("1.20", "20%"), "cspl": "fython", "kwargs": {}, "global": False}).encode(),
          headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": a.agent, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()
    log.append({"outside_this_server": "the program was overwritten through the plain HTTP API (rate 20%)"})
    r4 = await tool("run_program", name=NAME, params={"price": 100}, device="server")
    h = await tool("history", name=NAME)
    notes = [v["note"] for v in h["versions"]]
    checks["a save made elsewhere is noticed and kept as a version"] = r4.get("result", {}).get("total") == 120.0 and notes[-1] == "saved outside this server" and r4["version"] == back["version"] + 1
    bad = await tool("run_program", name=NAME, params={"price": 100}, device="printer")
    checks["an unknown device name is refused with the list of known names"] = bad["status"] == "error" and "laptop" in bad["error"] and "server" in bad["error"]
    checks["the history has every version and the runs"] = [v["version"] for v in h["versions"]] == list(range(1, r4["version"] + 1)) and notes[0] == "saved outside this server" \
        and notes[1] == "rate 10%" and len(h["last_runs"]) == 4
    final = await tool("rollback", name=NAME, version=first)
    return tools, log, checks, first, final["version"]


async def offline_steps(s):
    out = value(await s.call_tool("get_program", {"name": NAME}))
    refused = value(await s.call_tool("save_program", {"name": NAME, "code": V2}))
    return (out.get("from_local_history") is True and "1.10" in out.get("code", ""),
            refused.get("status") == "error" and "nothing was changed" in refused.get("error", ""))


def park():
    req = urllib.request.Request("https://api.extella.ai/api/expert/save", data=json.dumps({"name": NAME, "description": "Price with tax (custom MCP record)",
          "code": PARKED, "cspl": "fython", "kwargs": {}, "global": False}).encode(),
          headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": a.agent, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read()).get("status") == "success"


async def main():
    home = tempfile.mkdtemp(prefix="cmcp-")
    try:
        json.dump({"server": a.server, "laptop": a.laptop}, open(os.path.join(home, "devices.json"), "w"))
        t0 = time.time()
        std = await standard()
        tools, log, checks, first, last = await session(home, main_steps)
        closed = {"EXTELLA_API": "http://127.0.0.1:9"}                    # a closed local port: for the server Extella is unreachable
        checks["with the API unreachable the code is read from the local history"], checks["with the API unreachable a save is refused, nothing is changed"] = await session(home, offline_steps, closed)
        checks["the placeholder is put back for the next recording"] = park()
        result = {"recorded": time.strftime("%Y-%m-%d"), "what": "one session of an MCP client with extella_custom_mcp.py against a real Extella account, two devices",
                  "devices": {"server": "a Linux server", "laptop": "a MacBook"}, "agent": "the default agent" if a.agent == "agent_extella_default" else "a demo agent (id not stored)",
                  "tools": {"custom_server": tools, "standard_extella_server_same_minute": std,
                            "how_measured": "JSON of the tool list as the official Python SDK parses it; the second number counts only name, description and input schema"},
                  "program": NAME, "versions_in_this_session": "%d to %d" % (first, last), "checks": checks, "all_checks_passed": all(checks.values()),
                  "steps": log, "seconds_total": round(time.time() - t0, 1),
                  "before_the_session": "the account held a placeholder under this name, left by the script itself; the first save keeps it as version 1 and makes version 2",
                  "not_shown": "polling of a deferred run (every run here answered in the same call); failures of the API in the middle of a job are covered by test_offline.py with a stub",
                  "not_measured": "model tokens, the work of a real agent (the client here is a script), two users at once, loss of the history file"}
        text = json.dumps(result, ensure_ascii=False, indent=1)
        for secret in (TOKEN, a.server, a.laptop, a.agent if a.agent != "agent_extella_default" else "\0"):
            text = text.replace(secret, "<removed>")
        out = os.path.join(HERE, "custom-mcp-%s.json" % result["recorded"])
        open(out, "w").write(text + "\n")
        print(json.dumps({"tools": {k: {x: y for x, y in v.items() if x != "names"} if isinstance(v, dict) else v for k, v in result["tools"].items()}, "checks": checks, "seconds_total": result["seconds_total"]}, ensure_ascii=False, indent=1))
        print("written:", out)
    finally:
        shutil.rmtree(home, ignore_errors=True)

asyncio.run(main())
