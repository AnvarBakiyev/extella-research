#!/usr/bin/env python3
"""A custom MCP server for Extella: your own tool list on top of the Extella HTTP API (official Python SDK, FastMCP, stdio).

The standard Extella MCP server gives an agent 44 tools. This one runs on YOUR machine, talks to the same account
through the public HTTP API and gives the agent six tools shaped for one job: write a program, run it on a device,
keep every version, go back to an earlier one.

  save_program   save a program in Extella AND keep the version in a local SQLite file
  run_program    run a saved program on a device chosen by a short name ("server", "laptop"); waits for the answer itself
  get_program    read the current code from Extella, or any earlier version from the local history
  history        versions and recent runs of one program, or the list of programs this server has saved
  diff_versions  what changed between two versions
  rollback       make an earlier version the current one in Extella again

What it adds to the standard server: versions (Extella keeps one copy per name, a save overwrites), rollback, a run log
with seconds, device names instead of ids, one call per run (a deferred task is polled here, not by the agent), a waiting
time you set, and plain Python as a language (the server adds the two-line header that Extella's Python programs start with).
Nothing has to be installed on the Extella side: what this server saves are ordinary experts, still visible to the
standard server and the API.

Honest limits. The history lives in ONE local file (default ~/.extella/custom-mcp/history.db, readable only by you): lose
the file and the history is gone, the programs in Extella stay. It holds only versions saved THROUGH this server or
noticed by it: before a save or a rollback and at a run or a read it compares the copy in Extella with the latest local
version and records a difference as a version "saved outside this server"; a copy saved elsewhere and overwritten
elsewhere before that is not in it. One user, no locking between two copies of this server.
The server has the rights of the token it reads, and six tools do not make them narrower: whatever the agent saves here
can run on your devices with the rights of the Extella listener there, and a Python program run that way can read that
user's files, the token file included. The tools work by name on any program the agent id can reach (read its code, run
it, save over it), not only on programs saved through this server. The token is sent to the address in EXTELLA_API.
The transport is stdio; do not expose it on a network.

Setup: pip install mcp; a token in ~/.extella/api_token.txt; device names in ~/.extella/custom-mcp/devices.json,
for example {"server": "<device id>", "laptop": "<device id>"}. Agent scope: EXTELLA_AGENT_ID (default agent_extella_default).
Other settings: EXTELLA_CUSTOM_MCP_HOME (directory of history.db and devices.json), EXTELLA_TOKEN_FILE (another token
file), EXTELLA_RUN_WAIT (seconds, default 120), EXTELLA_API (another address of the API).
Usage: python3 extella_custom_mcp.py"""
import ast, asyncio, difflib, hashlib, json, os, re, sqlite3, time, urllib.error, urllib.request

from mcp.server.fastmcp import FastMCP

API = os.environ.get("EXTELLA_API") or "https://api.extella.ai/api"
HOME = os.environ.get("EXTELLA_CUSTOM_MCP_HOME") or os.path.expanduser("~/.extella/custom-mcp")
TOKEN_FILE = os.environ.get("EXTELLA_TOKEN_FILE") or os.path.expanduser("~/.extella/api_token.txt")
AGENT = os.environ.get("EXTELLA_AGENT_ID") or "agent_extella_default"
RUN_WAIT = float(os.environ.get("EXTELLA_RUN_WAIT") or 120)
NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
FINISHED = ("completed", "done", "success", "finished", "error", "failed")
FAILED = ("error", "failed")
PYTHON_HEADER = '$extens("include.py")\ninclude("import os", [])\n\n'        # the header Extella's Python programs (language fython) start with
mcp = FastMCP("extella-custom")


def _db():
    os.makedirs(HOME, mode=0o700, exist_ok=True)
    path = os.path.join(HOME, "history.db")
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)                                                # the file holds the full text of every version
    db.execute("CREATE TABLE IF NOT EXISTS versions (name TEXT, version INTEGER, saved_at TEXT, language TEXT, description TEXT,"
               " note TEXT, sha256 TEXT, code TEXT, PRIMARY KEY (name, version))")
    db.execute("CREATE TABLE IF NOT EXISTS runs (name TEXT, version INTEGER, ran_at TEXT, device TEXT, seconds REAL, ok INTEGER)")
    return db


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def _sha(code):
    return hashlib.sha256(code.rstrip("\n").encode()).hexdigest()       # expert/get returns the code without the final newline


def _call(path, body, timeout=60):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={
        "X-Auth-Token": open(TOKEN_FILE).read().strip(), "X-Profile-Id": "default", "X-Agent-Id": AGENT, "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        return {"status": "error", "reason": "HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300])}
    except TimeoutError:                                                 # connected, no answer within the timeout
        return {"status": "error", "reason": "no answer in %d s" % timeout, "unreachable": True, "timed_out": True}
    except Exception as e:                                               # no network, not JSON
        return {"status": "error", "reason": "Extella is not reachable: %s" % e, "unreachable": True}


def _devices():
    try:
        return json.load(open(os.path.join(HOME, "devices.json")))
    except Exception:
        return {}


def _latest(db, name):
    return db.execute("SELECT version, sha256, code, language, description FROM versions WHERE name = ? ORDER BY version DESC LIMIT 1", (name,)).fetchone()


def _record(db, name, code, language, description, note):
    last = _latest(db, name)
    if last and last[1] == _sha(code) and (last[3] or "") == (language or ""):
        return last[0], False
    try:
        db.execute("INSERT INTO versions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (name, (last[0] if last else 0) + 1, _now(), language, description, note, _sha(code), code))
        db.commit()
    except sqlite3.IntegrityError:                                       # a parallel call recorded this version number first
        return _record(db, name, code, language, description, note)
    return (last[0] if last else 0) + 1, True


def _remote(name):
    got = _call("/expert/get", {"name": name})
    code = got.get("expert_code") if isinstance(got, dict) else None
    return (code, got.get("cspl") or "", got.get("expert_description") or "", got) if code else (None, "", "", got)


def _sync(db, name, must=False):
    """Record the copy that is in Extella now if it is not the latest local version (somebody saved it elsewhere).
    With must: raise if the copy could not be read for a reason other than 'there is no such program'."""
    code, language, description, raw = _remote(name)
    if code is None:
        if must and "not found" not in str(raw).lower():
            raise RuntimeError("could not read the current copy from Extella, nothing was changed: " + str(raw)[:200])
        return None
    last = _latest(db, name)
    return _record(db, name, code, language or (last[3] if last else ""), description or (last[4] if last else ""), "saved outside this server")[0]


def _save(db, name, code, language, description, note):
    """Keep what is about to be overwritten, save to Extella, record the new version."""
    try:
        _sync(db, name, must=True)
    except RuntimeError as e:
        return {"status": "error", "error": str(e)}
    saved = _call("/expert/save", {"name": name, "description": description, "code": code, "cspl": language, "kwargs": {}, "global": False})
    if not isinstance(saved, dict) or saved.get("status") != "success":
        return {"status": "error", "error": "Extella did not confirm the save: " + str(saved)[:400]}
    version, new = _record(db, name, code, language, description, note)
    return {"status": "success", "name": name, "version": version, "new_version": new, "language": language}


def _checked(name):
    if not NAME.fullmatch(name or ""):
        raise ValueError("program name must match [a-z][a-z0-9_]{0,63}")


@mcp.tool()
def save_program(name: str, code: str, language: str = "python", description: str = "", note: str = "") -> dict:
    """Save a program in Extella under a name and keep this version in the local history.
    language 'python': plain Python that defines a function with the same name as the program; the function takes the
    program's parameters as keyword arguments and returns a dict. Any other value is the name of a language that has a
    handler on the device where the program will run (for example 'readsql', 'page', 'go'); the code is saved as is.
    note is a one-line reason for this version. Saving the same code in the same language again creates no new version."""
    _checked(name)
    if language in ("python", "fython"):
        language, code = "fython", code if code.lstrip().startswith("$extens(") else PYTHON_HEADER + code
    return _save(_db(), name, code, language, description, note)


@mcp.tool()
async def run_program(name: str, params: dict | None = None, device: str = "") -> dict:
    """Run a saved program by name on a device and return its result. device is a short name such as 'server' or
    'laptop'; an unknown or empty name is refused with the list of known names. The call waits for the answer
    itself; a typical run takes 6-14 seconds."""
    _checked(name)
    devices = _devices()
    if device not in devices:
        return {"status": "error", "error": "no device named %r; known: %s" % (device, ", ".join(sorted(devices)) or "none (fill devices.json)")}
    version = await asyncio.to_thread(lambda: _sync(_db(), name))       # a connection of its own: SQLite objects stay in their thread
    t0 = time.time()
    out = await asyncio.to_thread(_call, "/expert/run", {"name": name, "params": params or {}, "targets": [devices[device]]}, RUN_WAIT)
    task, lost = None, ""
    if isinstance(out, dict) and out.get("task_id") and ("result" not in out or str(out["result"]).startswith("deferred")):
        task = out["task_id"]                                            # a deferred run: poll it here, not in the agent
    while task and time.time() - t0 < RUN_WAIT:
        await asyncio.sleep(2)
        chk = await asyncio.to_thread(_call, "/tasks/check", {"task_id": task}, 30)
        if not isinstance(chk, dict) or chk.get("unreachable"):
            lost = str(chk.get("reason") if isinstance(chk, dict) else chk)[:200]     # the check failed, not the program: keep waiting
        elif str(chk.get("status")) in FINISHED:
            out, task = chk, None
    seconds = round(time.time() - t0, 1)
    no_answer = bool(task) or bool(isinstance(out, dict) and out.get("timed_out"))
    failed_outside = isinstance(out, dict) and str(out.get("status")) in FAILED
    res = out.get("result", out) if isinstance(out, dict) else out
    if isinstance(res, dict) and "result" in res:
        res = res["result"]
    if isinstance(res, str):
        for loader in (json.loads, ast.literal_eval):
            try:
                res = loader(res)
                break
            except Exception:
                pass
    ok = not no_answer and not failed_outside and not (isinstance(res, dict) and res.get("status") in FAILED)
    db = _db()
    db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)", (name, version, _now(), device, seconds, int(ok)))
    db.commit()
    if no_answer:
        return {"status": "error", "error": "no answer in %d s (EXTELLA_RUN_WAIT); the run may still finish on the device" % RUN_WAIT,
                "task_id": task or "", "last_check_error": lost, "seconds": seconds}
    return {"status": "success" if ok else "error", "result": res, "version": version, "device": device, "seconds": seconds}


@mcp.tool()
def get_program(name: str, version: int = 0) -> dict:
    """Return the code of a program. version 0 is the current copy in Extella (if Extella is not reachable, the latest
    local version, marked from_local_history); a positive version is read from the local history."""
    _checked(name)
    db = _db()
    if version:
        row = db.execute("SELECT code, language, saved_at, note FROM versions WHERE name = ? AND version = ?", (name, version)).fetchone()
        return {"status": "success", "name": name, "version": version, "code": row[0], "language": row[1], "saved_at": row[2], "note": row[3]} if row \
            else {"status": "error", "error": "no version %d of %r in the local history" % (version, name)}
    code, language, description, raw = _remote(name)
    if code is not None:
        last = _latest(db, name)
        current = _record(db, name, code, language or (last[3] if last else ""), description or (last[4] if last else ""), "saved outside this server")[0]
        return {"status": "success", "name": name, "version": current, "code": code, "language": language}
    last = _latest(db, name)
    if last and isinstance(raw, dict) and raw.get("unreachable"):
        return {"status": "success", "name": name, "version": last[0], "code": last[2], "language": last[3], "from_local_history": True}
    return {"status": "error", "error": "no program named %r in Extella: %s" % (name, str(raw)[:200])}


@mcp.tool()
def history(name: str = "") -> dict:
    """Versions and the last ten runs of one program. With an empty name: the programs this server has saved."""
    db = _db()
    if not name:
        rows = db.execute("SELECT name, MAX(version), MAX(saved_at) FROM versions GROUP BY name ORDER BY 3 DESC").fetchall()
        return {"status": "success", "programs": [{"name": r[0], "versions": r[1], "last_saved_at": r[2]} for r in rows]}
    _checked(name)
    versions = [{"version": r[0], "saved_at": r[1], "language": r[2], "note": r[3], "sha256": r[4][:12], "lines": r[5].rstrip("\n").count("\n") + 1}
                for r in db.execute("SELECT version, saved_at, language, note, sha256, code FROM versions WHERE name = ? ORDER BY version", (name,))]
    runs = [{"version": r[0], "ran_at": r[1], "device": r[2], "seconds": r[3], "ok": bool(r[4])}
            for r in db.execute("SELECT version, ran_at, device, seconds, ok FROM runs WHERE name = ? ORDER BY rowid DESC LIMIT 10", (name,))]
    return {"status": "success", "name": name, "versions": versions, "last_runs": runs}


@mcp.tool()
def diff_versions(name: str, old: int, new: int) -> dict:
    """Show what changed between two versions of a program (a unified diff of the code)."""
    _checked(name)
    db = _db()
    code = {v: db.execute("SELECT code FROM versions WHERE name = ? AND version = ?", (name, v)).fetchone() for v in (old, new)}
    missing = [v for v in (old, new) if not code[v]]
    if missing:
        return {"status": "error", "error": "no version %s of %r in the local history" % (missing, name)}
    lines = list(difflib.unified_diff(code[old][0].rstrip("\n").splitlines(), code[new][0].rstrip("\n").splitlines(), "v%d" % old, "v%d" % new, lineterm=""))
    return {"status": "success", "name": name, "diff": "\n".join(lines) or "no difference"}


@mcp.tool()
def rollback(name: str, version: int) -> dict:
    """Make an earlier version the current one in Extella again. The history is not rewritten: the restored code
    becomes a new version with a note, and what was current before stays in the history."""
    _checked(name)
    db = _db()
    row = db.execute("SELECT code, language, description FROM versions WHERE name = ? AND version = ?", (name, version)).fetchone()
    if not row:
        return {"status": "error", "error": "no version %d of %r in the local history" % (version, name)}
    out = _save(db, name, row[0], row[1], row[2], "rollback to version %d" % version)
    if out["status"] == "success":
        out["restored_from"] = version
    return out


if __name__ == "__main__":
    mcp.run()
