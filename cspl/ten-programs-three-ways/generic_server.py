#!/usr/bin/env python3
"""A general executor with program storage, as an MCP server (official Python SDK, FastMCP, stdio).

Four fixed tools: save_program, run_program, get_program, search_programs. A program is Python source that defines
a function with the SAME NAME as the program. It is stored as a file in ./programs next to this server (another
directory: GENERIC_PROGRAMS_DIR) and survives restarts. Adding a program never changes the tool list and needs
neither an edit nor a restart of this server.

Honest limits. NO SANDBOX: run_program executes the stored code in a separate Python process with a timeout, but
with the full rights of the OS user who started the server (files, network, everything). The separate process
protects the server from a crash or a hang of the program; it does not protect the machine from the program.
Stored programs also see every environment variable of this server process (start it with a minimal environment).
The transport is stdio only. Do NOT start this server with a network transport: it would hand arbitrary code
execution on this machine to whoever can reach the port.
No versioning (a save overwrites), no access control, one machine (programs run where this server runs; a second
machine needs its own copy of the server and a shared or copied program directory), one language (Python).
search_programs is a plain word match on name and description, not a semantic search.
Usage: python3 generic_server.py        needs: pip install mcp"""
import asyncio, json, os, re, subprocess, sys, time

from mcp.server.fastmcp import FastMCP

STORE = os.environ.get("GENERIC_PROGRAMS_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "programs")
NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
mcp = FastMCP("generic-executor")

# Runs inside the child process: load the stored file, call the function named like the program, print the answer.
RUNNER = """
import json, sys
job = json.load(sys.stdin)
answer, sys.stdout = sys.stdout, sys.stderr          # whatever the program prints goes to stderr, the answer to stdout
scope = {"__name__": "program"}
exec(compile(open(job["path"], encoding="utf-8").read(), job["path"], "exec"), scope)
answer.write(json.dumps({"value": scope[job["name"]](**job["params"])}))
"""


def _paths(name: str):
    if not NAME.fullmatch(name or ""):
        raise ValueError("program name must match [a-z][a-z0-9_]{0,63}")
    return os.path.join(STORE, name + ".py"), os.path.join(STORE, name + ".json")


@mcp.tool()
def save_program(name: str, code: str, description: str) -> dict:
    """Save a Python program under a name. The code must define a function with the same name as the program;
    its keyword parameters are the program's parameters and its return value must be JSON-serializable.
    Saving an existing name overwrites it (no versions). The code is only syntax-checked here, not run.
    NO SANDBOX: once run, the saved code has the rights of the user who started this server."""
    src, meta = _paths(name)
    try:
        compile(code, name + ".py", "exec")
    except SyntaxError as e:
        return {"status": "error", "error": "syntax error: %s (line %s)" % (e.msg, e.lineno)}
    os.makedirs(STORE, exist_ok=True)
    existed = os.path.exists(src)
    with open(src, "w", encoding="utf-8") as f:
        f.write(code)
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({"name": name, "description": description, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S %z")}, f, ensure_ascii=False)
    return {"status": "success", "name": name, "overwritten": existed}


@mcp.tool()
async def run_program(name: str, params: dict | None = None, timeout_seconds: float = 30) -> dict:
    """Run a saved program by name with the given parameters (passed as keyword arguments) and return its result.
    NO SANDBOX: the program runs in a separate process with the rights of the user who started this server."""
    src, _ = _paths(name)
    if not os.path.exists(src):
        return {"status": "error", "error": "no program named %r; use search_programs" % name}
    job = json.dumps({"path": src, "name": name, "params": params or {}})
    t0 = time.time()
    try:
        done = await asyncio.to_thread(subprocess.run, [sys.executable, "-c", RUNNER], input=job, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout after %s s" % timeout_seconds}
    seconds = round(time.time() - t0, 3)
    if done.returncode != 0:
        return {"status": "error", "error": done.stderr[-2000:], "seconds": seconds}
    return {"status": "success", "value": json.loads(done.stdout)["value"], "seconds": seconds}


@mcp.tool()
def get_program(name: str) -> dict:
    """Return the stored code and description of a program."""
    src, meta = _paths(name)
    if not os.path.exists(src):
        return {"status": "error", "error": "no program named %r" % name}
    info = json.load(open(meta, encoding="utf-8")) if os.path.exists(meta) else {"name": name, "description": ""}
    return {"status": "success", **info, "code": open(src, encoding="utf-8").read()}


@mcp.tool()
def search_programs(query: str = "", limit: int = 20) -> dict:
    """Find saved programs whose name or description contains every word of the query (empty query: list all)."""
    words, found = query.lower().split(), []
    for fname in sorted(os.listdir(STORE)) if os.path.isdir(STORE) else []:
        if not fname.endswith(".json"):
            continue
        info = json.load(open(os.path.join(STORE, fname), encoding="utf-8"))
        text = (info.get("name", "") + " " + info.get("description", "")).lower()
        if all(w in text for w in words):
            found.append({"name": info.get("name"), "description": info.get("description")})
    return {"status": "success", "count": len(found), "programs": found[:limit]}


if __name__ == "__main__":
    mcp.run()
