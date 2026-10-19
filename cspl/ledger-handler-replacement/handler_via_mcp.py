#!/usr/bin/env python3
"""A language of your own, registered, used and replaced through the Extella MCP server only.

What it does, every step being a call of an MCP tool (save_expert or run_expert) of https://api.extella.ai/mcp/ :
  1. saves two registrar programs: each registers a handler (v1 or v2) for a small language "ledger" on the device it runs on
  2. runs registrar v1 on device 1: the device now understands "ledger"
  3. saves four programs in "ledger" and one text that is not a ledger program, runs all five on device 1
  4. runs registrar v2 on device 1 and runs the same four programs again WITHOUT saving them again
  5. with --second: runs registrar v1 on device 2 and runs two of the programs there, while device 1 keeps v2
The language: a program is lines "add N" or "sub N". Handler v1 returns the total; handler v2 also returns the number
of entries and the largest entry. Both check the whole program first and reject anything that is not a ledger statement.

WHAT THIS SCRIPT WRITES: into the Extella account of the token in ~/.extella/api_token.txt, in the scope of --agent, seven
experts named mcph_* are created or overwritten and remain there; on each device a handler file for the language "ledger"
is written by the listener. Nothing is deleted. The handlers run with the rights of the user that runs Extella; there is
no sandbox. Result: handler-via-mcp-<date>.json next to this script (no token, no device ids, no host names).
Usage: python3 handler_via_mcp.py [--agent <agent id>] [--second <device id>] [--yes]      needs: pip install mcp"""
import argparse, ast, asyncio, json, os, sys, time

HOME = os.path.expanduser("~/.extella")
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = ('    lines = [line.split() for line in (code or filtered_source_code or "").splitlines() if line.split()]\n'
         '    for n, parts in enumerate(lines, 1):\n'
         '        if len(parts) != 2 or parts[0] not in ("add", "sub") or not parts[1].isdigit():\n'
         '            return {"status": "rejected", "reason": "statement %d is not a ledger statement: %s" % (n, " ".join(parts)[:40])}\n'
         '    total = 0\n'
         '    for op, number in lines:\n'
         '        total += int(number) if op == "add" else -int(number)\n')
HANDLER = {1: 'def ledger(code = "", filtered_source_code = "", func_name = "", **extra):\n    import platform\n' + CHECK +
              '    return {"status": "success", "language": "ledger", "handler": 1, "expert": func_name, "total": total, "os": platform.system()}\n',
           2: 'def ledger(code = "", filtered_source_code = "", func_name = "", **extra):\n    import platform\n' + CHECK +
              '    largest = max([int(number) for op, number in lines] or [0])\n'
              '    return {"status": "success", "language": "ledger", "handler": 2, "expert": func_name, "total": total, "entries": len(lines), "largest": largest, "os": platform.system()}\n'}
PROGRAMS = {"mcph_ledger_a": ("add 5\nadd 7\nsub 2", 10), "mcph_ledger_b": ("add 100\nsub 1", 99), "mcph_ledger_c": ("add 40\nadd 2", 42), "mcph_ledger_d": ("sub 3\nadd 30\nsub 7\nadd 1", 21)}
BAD = ("mcph_ledger_e", "add 5\nimport os")


def registrar(version):
    name = "mcph_register_ledger_v%d" % version
    text = HANDLER[version]
    assert chr(92) not in text and "'" * 3 not in text                 # the handler text is embedded in a string literal
    return name, ('$extens("include.py")\ninclude("import os", [])\n\ndef %s() -> dict:\n    import disnet\n    handler_code = \'\'\'%s\'\'\'\n'
                  '    d = disnet.Disnet(url="https://disnet.extella.ai")\n'
                  '    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "ledger", "response_format": None}\n'
                  '    d.container(code=handler_code, func_name="ledger", container_path="ledger", args=None, kwargs=envelope, cspl_type="fython", push=False)\n'
                  '    return {"status": "success", "registered": "ledger", "handler": %d, "bytes": len(handler_code)}\n') % (name, text, version)


def parsed(res):
    text = res.content[0].text if res.content else ""
    try: out = json.loads(text)
    except ValueError: return {"status": "error", "reason": text[:200]}
    r = out.get("result", out)
    if isinstance(r, dict) and "result" in r: r = r["result"]
    if isinstance(r, str):
        for loader in (json.loads, ast.literal_eval):
            try: return loader(r)
            except Exception: pass
    return r if isinstance(r, dict) else {"status": "error", "reason": str(r)[:200]}


async def main(a, token, device):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    log = []
    headers = {"X-Auth-Token": token, "X-Profile-Id": "default", "X-Agent-Id": a.agent}
    async with streamablehttp_client("https://api.extella.ai/mcp/", headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            async def save(name, code, cspl, desc):
                t0 = time.time(); await s.call_tool("save_expert", {"name": name, "description": desc, "code": code, "cspl": cspl, "kwargs": {}})
                log.append({"tool": "save_expert", "name": name, "cspl": cspl, "seconds": round(time.time() - t0, 1)})
            async def run(name, dev, label):
                t0 = time.time(); out = parsed(await s.call_tool("run_expert", {"name": name, "params": {}, "targets": [dev]}))
                row = {"tool": "run_expert", "name": name, "device": label, "seconds": round(time.time() - t0, 1), "answer": {k: out.get(k) for k in ("status", "registered", "handler", "total", "entries", "largest", "os", "reason") if k in out}}
                log.append(row); print(row); return out
            for v in (1, 2):
                name, code = registrar(v); await save(name, code, "fython", "Registers handler v%d of the small language ledger on the device it runs on." % v)
            await run("mcph_register_ledger_v1", device, "device 1")
            for name, (code, _) in PROGRAMS.items(): await save(name, code, "ledger", "A program in the language ledger.")
            await save(BAD[0], BAD[1], "ledger", "Not a ledger program: the second line is not a statement of the language.")
            v1 = {name: await run(name, device, "device 1") for name in PROGRAMS}
            bad = await run(BAD[0], device, "device 1")
            await run("mcph_register_ledger_v2", device, "device 1")
            v2 = {name: await run(name, device, "device 1") for name in PROGRAMS}                     # the programs are NOT saved again
            second = {}
            if a.second:
                await run("mcph_register_ledger_v1", a.second, "device 2")
                for name in ("mcph_ledger_a", "mcph_ledger_d"): second[name] = await run(name, a.second, "device 2")
    checks = {"four programs ran under handler 1 with the expected totals": all(v1[n].get("handler") == 1 and v1[n].get("total") == PROGRAMS[n][1] for n in PROGRAMS),
              "a text that is not a ledger program was rejected by the handler": bad.get("status") == "rejected",
              "after replacing the handler the same four programs, not saved again, ran under handler 2 with the same totals and the new fields": all(v2[n].get("handler") == 2 and v2[n].get("total") == PROGRAMS[n][1] and "entries" in v2[n] for n in PROGRAMS)}
    if a.second: checks["device 2 ran the same programs under handler 1 while device 1 held handler 2"] = all(second[n].get("handler") == 1 and second[n].get("total") == PROGRAMS[n][1] for n in second) and second["mcph_ledger_a"].get("os") != v2["mcph_ledger_a"].get("os")
    return {"date": time.strftime("%Y-%m-%d %H:%M"), "transport": "MCP streamable HTTP, tools save_expert and run_expert only", "language": "ledger", "calls": log, "checks": checks,
            "notes": ["Every step was a call of an MCP tool; no HTTP API call and no shell access to the devices was used.", "One laptop and one Linux server; one day; a toy language of two statements.",
                      "A script made the calls. The same sequence was also done by a model through the same MCP tools in a working session on the same day; that session's transcript is not published.",
                      "No sandbox: the handler is a Python function that runs with the rights of the user that runs Extella on the device."]}


ap = argparse.ArgumentParser(); ap.add_argument("--agent", default="agent_extella_default"); ap.add_argument("--second", default=""); ap.add_argument("--yes", action="store_true")
a = ap.parse_args()
try: token = open(os.path.join(HOME, "api_token.txt")).read().strip(); device = open(os.path.join(HOME, "device.txt")).read().strip()
except OSError as e: sys.exit("needs ~/.extella/api_token.txt and ~/.extella/device.txt (%s). Nothing was run." % e)
print(__doc__.split("WHAT THIS SCRIPT WRITES:")[1].split("Usage:")[0].strip())
if not a.yes:
    try: ok = input("Proceed? [y/N] ").strip().lower() in ("y", "yes")
    except EOFError: ok = False
    if not ok: sys.exit("nothing was written")
res = asyncio.run(main(a, token, device))
out = os.path.join(HERE, "handler-via-mcp-%s.json" % time.strftime("%Y-%m-%d"))
text = json.dumps(res, ensure_ascii=False, indent=1)
for secret in (token, device, a.second):
    if secret: text = text.replace(secret, "<removed>")
open(out, "w", encoding="utf-8").write(text)
print(json.dumps(res["checks"], indent=1)); print("saved", out)
