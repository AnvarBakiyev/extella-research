#!/usr/bin/env python3
"""Three-path measurement: the same ten small capabilities given to an agent one after another.

  fixed        your own MCP server with fixed tools (FastMCP, stdio): a capability = an edit of the server file and
               a restart of the server process. The weakest baseline; MCP itself does not force it.
  generic      generic_server.py: an MCP server that is a general executor with program storage. A capability =
               save_program + run_program. The server file is not edited and the process is not restarted.
  extella-mcp  the real Extella MCP server over streamable HTTP: a capability = save_expert + run_expert on a
               named device. There is no fallback to another transport: if the MCP endpoint fails, the path fails.

Counted per path: edits of server code, restarts, tools listed and bytes of their definitions, seconds from the
start of a capability to its first answer, seconds of repeat calls of already saved capabilities (30 calls in a
random order, with min / p10 / median / p90 / max over the correct ones), failed calls, one call with a wrong
parameter. For Extella also: calls that touch no device (to separate the service from the device dispatch), a
proof of WHERE a program ran, and a call to a device that does not exist.
Nothing here measures model tokens, security, search quality, languages other than Python or handler replacement.

WHAT THIS SCRIPT WRITES
  fixed, generic   only into temporary directories of their own, removed at the end. ./programs is not touched.
  extella-mcp      INTO THE EXTELLA ACCOUNT of the token in ~/.extella/api_token.txt, in the scope of --agent:
                   eleven private experts named mcpm3_<name> are created or overwritten (Extella keeps no
                   versions) and REMAIN in the account; this script deletes nothing. If an expert with one of
                   these names exists and was not made by this script, the run stops before any write.
                   The experts are run on the device in ~/.extella/device.txt and, with --second, on that device.
  result           result3-<date>.json next to this script (overwritten), or the file given with --out.
The script prints this before it starts and asks for consent to the account writes (--yes to answer in advance).

Usage: python3 measure3.py [--agent <agent id>] [--second <device id>] [--only fixed,generic,extella-mcp] [--yes]
Needs: pip install mcp; for the Extella path ~/.extella/api_token.txt and ~/.extella/device.txt.

Privacy of the result file: the token, the device ids given to this script, a non-default agent id, the home
path, the user name, the host name of this machine and anything shaped like a UUID are replaced before the file
is written. Answers of remote calls are never stored, only what was checked in them; the text of a failed call
is printed to the terminal instead. Exception texts of this script are stored (after the same replacement, cut
to 400 characters): if 'what_failed' is not empty, read it before you publish the file."""
import argparse, ast, asyncio, getpass, hashlib, json, os, platform, random, re, shutil, socket, statistics, sys, tempfile, time, traceback, uuid
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~/.extella")
MCP_URL = "https://api.extella.ai/mcp/"
PREFIX = "mcpm3_"                                                # the only expert names this script creates or overwrites
MARK = "Measurement capability"                                  # every description starts with it; the overwrite guard looks for it
DEFAULT_AGENT = "agent_extella_default"
ROUNDS = 3                                                       # repeat calls: every saved capability this many times, in a random order
NOT_COMPARED = ("not compared: this path was not run on a second machine. It could be: a one-time setup there (copy the server, pip install mcp"
                "%s) is needed first. Extella's second device needed a one-time setup too (a listener installed and bound to the account); neither setup was timed.")
CAPS = [  # name, signature, body, arguments, expected, description  (the same ten functions as in measure.py)
    ("word_count", "text: str", "return len(text.split())", {"text": "keep the program choose where it runs"}, 7, "count the words in a text"),
    ("total", "numbers: list", "return sum(numbers)", {"numbers": [3, 4, 5]}, 12, "add up a list of numbers"),
    ("reverse_text", "text: str", "return text[::-1]", {"text": "abc"}, "cba", "reverse a text"),
    ("is_prime", "n: int", "return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))", {"n": 97}, True, "tell whether a whole number is prime"),
    ("fibonacci", "n: int", "a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a", {"n": 20}, 6765, "return the n-th Fibonacci number"),
    ("to_fahrenheit", "celsius: float", "return celsius * 9 / 5 + 32", {"celsius": 100}, 212.0, "convert degrees Celsius to Fahrenheit"),
    ("slug", "title: str", "return '-'.join(title.lower().split())", {"title": "Keep The Program"}, "keep-the-program", "turn a title into a lowercase slug with hyphens"),
    ("median", "numbers: list", "s = sorted(numbers)\n    return s[len(s) // 2]", {"numbers": [5, 1, 9]}, 5, "return the middle value of a list of numbers"),
    ("vowels", "text: str", "return sum(ch in 'aeiou' for ch in text.lower())", {"text": "Extella"}, 3, "count the vowels in a text"),
    ("longest_word", "text: str", "return max(text.split(), key=len)", {"text": "run it on a device"}, "device", "return the longest word in a text"),
]
# Not a capability: proves on which machine a run happened. The host name never leaves the device unhashed and the hash is salted per run.
LOCATION = ("location", "salt: str", "import hashlib, platform, socket\n    return {'system': platform.system(), 'host': hashlib.sha256((salt + socket.gethostname()).encode()).hexdigest()[:16]}",
            "report the operating system and a salted hash of the host name of the machine it runs on")
EXPERT_NAMES = [PREFIX + c[0] for c in CAPS] + [PREFIX + LOCATION[0]]
NOTES = [  # what this measurement is and is not; written into the result so the numbers never travel without it
    "One laptop, one account, one day; ten trivial functions; ten first calls per path and thirty repeat calls per path and device in a random order. Medians and percentiles are taken over correct calls only; failed calls are counted and listed in what_failed.",
    "Path 'fixed' restarts the server for every capability because this baseline is built that way; its 10 edits and 10 restarts are how the baseline is constructed, not an observation about MCP. MCP does not require it: a server may change its tool list at run time and notify the client (tools/list_changed), and path 'generic' adds capabilities with no edit and no restart.",
    "Path 'generic' is a local child process over stdio: no network, no authentication, no second machine, no sandbox, Python only, word-match search. It is a minimal general executor with storage written for this measurement; it is NOT Anthropic's code execution with MCP and NOT Cloudflare Code Mode, and neither of those was run. Its 0 edits and 0 restarts are checked (sha256 of the server file, one session, identical tool list).",
    "Path 'extella-mcp': 0 edits and 0 restarts means none by us; the state of the remote server cannot be observed from the client beyond 'the tool list is identical before and after'. Each function is saved inside a small Extella wrapper (a header line and a status dictionary), while the generic executor stores the function unchanged.",
    "Latency is not like for like. The local paths have no network, no authentication and a local disk; Extella is a remote service that relays to a device, and its 'device 1' is this same laptop. The result separates Extella's time into: a call that touches no device (service round trip), save_expert, and run_expert, next to the run time the platform itself reports. Read the split before blaming the network for the run time, and do not read 'local stdio versus Extella' as a comparison of products: a general executor behind a network with authentication was not measured.",
    "Tool definitions are given as two byte counts. 'definitions_bytes' = JSON of every field the server lists, as the official Python SDK parses it (Extella's server also lists output schemas, annotations, titles and meta; the two local servers do not). 'definitions_bytes_name_description_input_schema' = the same three fields for every server. Bytes, not model tokens; no model was driving any of the servers. The Extella listing is what this account and agent were served at the time of the run (the server also offers enable_group/disable_group, so it may differ in another configuration; that was not tried). Its four program tools alone are given separately, next to the four tools of the generic executor.",
    "Second machine: only Extella was run on a second machine, so this is an observation about Extella and not a comparison. What it shows: one saved record, the machine chosen by a parameter of the call, proven by a program that reports the operating system and a salted hash of the host name, plus an unknown device id that must fail. What it does not show: that an MCP server or a self-written executor cannot run on a second machine, or what either setup costs. A self-written executor keeps its store where the server runs, so programs have to be synced or a hub has to be built; that effort was not measured.",
    "Every Extella expert saved by this script carries a nonce of this run and a call counts as correct only if the answer carries it, so a save that silently did nothing cannot pass. Each save is also read back with get_expert outside the timed section. Whether a save was a creation or an overwrite is recorded per row (existed_before).",
    "Extella experts are stored in the scope of one agent, not of the whole account: the same names under another agent are 'not found'. The script deletes nothing; the experts remain.",
    "Search was not measured on any path. For the generic executor only 'an empty query lists all ten saved programs' is checked, which is listing, not search. Extella's search_experts was not called.",
    "Not measured at all: languages other than Python, handlers and their replacement, a server that changes its tool list at run time, security isolation (neither Extella nor the generic executor has a sandbox), versioning, search quality, cost, concurrency, token usage of a model driving these tools.",
    "measure.py and result-2026-10-02.json in this directory are an older two-path measurement and are superseded by this one: their fixed-server seconds include the shutdown of the session and the process, their Extella path used the HTTP API and not MCP, and their statement about 'three MCP tools' was written by hand, not measured.",
]
SECRETS = []                                                     # (value, label); filled in main() before anything runs
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def clean(text, limit=None):
    """Replace secrets and identifiers FIRST, cut afterwards (a value cut in half would no longer be found)."""
    text = str(text)
    for value, label in SECRETS:
        text = text.replace(value, label)
    text = UUID_RE.sub("<uuid>", text)
    return text if limit is None else text[:limit]


def dump(tools):
    return [t.model_dump(mode="json", exclude_none=True) for t in tools]


def listing(tools):
    full = dump(tools)
    core = [{k: d[k] for k in ("name", "description", "inputSchema") if k in d} for d in full]
    return {"count": len(tools), "definitions_bytes": len(json.dumps(full)), "definitions_bytes_name_description_input_schema": len(json.dumps(core))}


def parsed(text):
    """The text of a tool answer as a value: JSON if it is JSON, else a Python literal, else the text itself."""
    if not isinstance(text, str): return text
    for reader in (json.loads, ast.literal_eval):
        try: return reader(text)
        except (ValueError, SyntaxError): pass
    return text


def text_of(res):
    return " ".join(getattr(c, "text", "") or "" for c in (res.content or []))


def same(got, want):
    return type(got) is type(want) and got == want or (isinstance(want, float) and isinstance(got, (int, float)) and not isinstance(got, bool) and float(got) == want)


def dist(xs, nd):
    """n, min, p10, median, p90, max of a list of seconds; None if the list is empty."""
    xs = sorted(x for x in xs if x is not None)
    if not xs: return None
    q = statistics.quantiles(xs, n=10, method="inclusive") if len(xs) > 1 else [xs[0]] * 9
    return {"n": len(xs), "min": round(xs[0], nd), "p10": round(q[0], nd), "median": round(statistics.median(xs), nd), "p90": round(q[8], nd), "max": round(xs[-1], nd)}


def summary(rows, repeats, nd=4):
    """Medians over correct calls only; failed calls are counted, never averaged in."""
    first, rep = [r["seconds_to_first_call"] for r in rows if r["ok"]], [r["seconds"] for r in repeats if r["ok"]]
    return {"correct_of_10": sum(bool(r["ok"]) for r in rows), "first_calls_failed": sum(not r["ok"] for r in rows),
            "server_edits": sum(r["server_edits"] for r in rows), "server_restarts": sum(r["server_restarts"] for r in rows),
            "median_seconds_to_first_call": round(statistics.median(first), min(nd, 3)) if first else None, "seconds_to_first_call": dist(first, min(nd, 3)),
            "repeat_calls": len(repeats), "repeat_calls_correct": sum(bool(r["ok"]) for r in repeats), "repeat_calls_failed": sum(not r["ok"] for r in repeats),
            "median_seconds_repeat_call": round(statistics.median(rep), nd) if rep else None, "seconds_repeat_call": dist(rep, nd)}


def error_text(e):
    """One line per real error, also for the exception groups that anyio task groups raise. Scrubbed before it is cut."""
    if isinstance(e, BaseExceptionGroup): return " | ".join(error_text(x) for x in e.exceptions)
    return "%s: %s" % (type(e).__name__, clean(str(e), 400))


def repeat_plan(rng, devices=("",)):
    plan = [(d, i) for d in devices for i in range(len(CAPS)) for _ in range(ROUNDS)]
    rng.shuffle(plan)
    return plan


# ---------------------------------------------------------------- path "fixed": own MCP server, tools fixed in code
async def path_fixed(part, rng):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    work = tempfile.mkdtemp(prefix="mcpm3_fixed_")                                     # nothing is written next to this script
    server = os.path.join(work, "server_fixed.py")
    head = "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('ten-capabilities')\n"
    tail = "\nif __name__ == '__main__':\n    mcp.run()\n"
    body, rows, repeats = "", [], []
    part.update({"transport": "MCP stdio, own server (official Python SDK, FastMCP), one tool per capability, each with a one-line description", "rows": rows, "repeat_calls": repeats})
    try:
        for k, (name, sig, code, args, want, desc) in enumerate(CAPS, 1):
            t0 = time.time()
            body += '\n@mcp.tool()\ndef %s(%s):\n    """%s."""\n    %s\n' % (name, sig, desc[0].upper() + desc[1:], code)
            with open(server, "w") as f: f.write(head + body + tail)                  # 1 edit of the server file
            async with stdio_client(StdioServerParameters(command=sys.executable, args=[server])) as (r, w):   # 1 restart; the SDK's minimal default environment
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    tools = (await s.list_tools()).tools                               # the client lists the tools again
                    t1 = time.time()
                    res = await s.call_tool(name, args)
                    t2 = time.time()                                                   # the clock stops at the answer, before any shutdown
                    got = parsed(res.content[0].text) if res.content else None
                    rows.append({"n": k, "capability": name, "server_edits": 1, "server_restarts": 1, "tools_listed": len(tools), "tool_definitions": listing(tools),
                                 "seconds_to_first_call": round(t2 - t0, 3), "seconds_call_only": round(t2 - t1, 4), "ok": same(got, want)})
                    print("fixed", rows[-1], flush=True)
                    if k == len(CAPS):                                                 # repeat calls in the session of the tenth restart
                        for _, i in repeat_plan(rng):
                            rname, _, _, rargs, rwant, _ = CAPS[i]
                            t = time.time(); res = await s.call_tool(rname, rargs)
                            repeats.append({"capability": rname, "seconds": round(time.time() - t, 4), "ok": same(parsed(res.content[0].text) if res.content else None, rwant)})
                        t = time.time(); res = await s.call_tool(CAPS[0][0], {"no_such_parameter": 1})
                        part["wrong_parameter_call"] = {"is_error_flag": bool(res.isError), "answer_reports_error": bool(res.isError), "seconds": round(time.time() - t, 4)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    part.update({"tools_listed_before_first": {"count": 0, "definitions_bytes": 0, "note": "the server does not exist before the first capability"},
                 "tools_listed_after_tenth": rows[-1]["tool_definitions"], "second_machine": NOT_COMPARED % "", "summary": summary(rows, repeats)})


# ---------------------------------------------------------------- path "generic": general executor with program storage
async def path_generic(part, rng):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client, get_default_environment
    server = os.path.join(HERE, "generic_server.py")
    store = tempfile.mkdtemp(prefix="mcpm3_programs_")                                 # a store of its own: ./programs is never touched, every save is a first save
    sha = lambda: hashlib.sha256(open(server, "rb").read()).hexdigest()
    sha_before, rows, repeats = sha(), [], []
    part.update({"transport": "MCP stdio, generic_server.py (official Python SDK, FastMCP), 4 fixed tools", "rows": rows, "repeat_calls": repeats})
    # The SDK's minimal default environment, not the caller's: stored programs must not inherit the caller's secrets.
    params = StdioServerParameters(command=sys.executable, args=[server], env={**get_default_environment(), "GENERIC_PROGRAMS_DIR": store})

    def value(res):
        out = parsed(res.content[0].text) if res.content else None
        return out.get("value") if isinstance(out, dict) and out.get("status") == "success" else None, out

    try:
        t_start = time.time()
        async with stdio_client(params) as (r, w):                                     # the server is started once
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = (await s.list_tools()).tools
                start_seconds, before = round(time.time() - t_start, 3), listing(tools)
                names_before = sorted(t.name for t in tools)
                for k, (name, sig, code, args, want, desc) in enumerate(CAPS, 1):
                    src = "def %s(%s):\n    %s\n" % (name, sig, code)
                    t0 = time.time()
                    saved = parsed((await s.call_tool("save_program", {"name": name, "code": src, "description": "%s: %s" % (MARK, desc)})).content[0].text)
                    t1 = time.time()
                    got, raw = value(await s.call_tool("run_program", {"name": name, "params": args}))
                    t2 = time.time()
                    back = parsed((await s.call_tool("get_program", {"name": name})).content[0].text)   # read back, outside the timed section
                    row = {"n": k, "capability": name, "server_edits": 0, "server_restarts": 0, "seconds_save": round(t1 - t0, 4), "seconds_run": round(t2 - t1, 4),
                           "seconds_to_first_call": round(t2 - t0, 3), "ok": same(got, want), "save_status": saved.get("status") if isinstance(saved, dict) else None,
                           "existed_before": saved.get("overwritten") if isinstance(saved, dict) else None, "read_back_matches": isinstance(back, dict) and back.get("code") == src}
                    if not row["ok"]: row["failure"] = "wrong value or error"; print("generic FAILED", clean(raw, 600), file=sys.stderr, flush=True)
                    rows.append(row); print("generic", row, flush=True)
                after_tools = (await s.list_tools()).tools
                after, names_after = listing(after_tools), sorted(t.name for t in after_tools)
                for _, i in repeat_plan(rng):                                          # repeat calls of already saved programs
                    name, _, _, args, want, _ = CAPS[i]
                    t = time.time(); got, _ = value(await s.call_tool("run_program", {"name": name, "params": args}))
                    repeats.append({"capability": name, "seconds": round(time.time() - t, 4), "ok": same(got, want)})
                t = time.time(); res = await s.call_tool("run_program", {"name": CAPS[0][0], "params": {"no_such_parameter": 1}})
                out = parsed(text_of(res))
                part["wrong_parameter_call"] = {"is_error_flag": bool(res.isError), "answer_reports_error": isinstance(out, dict) and out.get("status") == "error", "seconds": round(time.time() - t, 4)}
                listed = parsed((await s.call_tool("search_programs", {"query": ""})).content[0].text)
        # Not needed to add a capability; only to check the claim "programs survive a restart": a new process, no save.
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                name, _, _, args, want, _ = CAPS[4]
                got, _ = value(await s.call_tool("run_program", {"name": name, "params": args}))
                survive = {"program": name, "ok_without_saving_again": same(got, want)}
    finally:
        shutil.rmtree(store, ignore_errors=True)
    part.update({"session_start_seconds": start_seconds, "tools_listed_before_first": before, "tools_listed_after_tenth": after, "tool_names": names_after,
                 "tool_list_unchanged": names_before == names_after and before == after, "server_file_unchanged_sha256": sha_before == sha(),
                 "empty_query_lists_all_saved": (listed.get("count") if isinstance(listed, dict) else None) == len(CAPS), "survives_restart": survive,
                 "second_machine": NOT_COMPARED % ", share or copy the program directory",
                 "summary": {**summary(rows, repeats), "seconds_first_capability_including_server_start": round(start_seconds + rows[0]["seconds_to_first_call"], 3)}})


# ---------------------------------------------------------------- path "extella-mcp": the real Extella MCP server
def expert_source(ename, sig, code, nonce):
    return ('$extens("include.py")\ninclude("import os", [])\n\ndef %s(%s) -> dict:\n    def work():\n        %s\n    return {"status": "success", "value": work(), "nonce": "%s"}\n'
            % (ename, sig, code.replace("\n    ", "\n        "), nonce))


def fit(tool, args):
    """Arguments checked against the input schema that the server itself listed: unknown keys dropped, required keys demanded."""
    schema = tool.inputSchema or {}
    missing = [k for k in schema.get("required", []) if k not in args]
    if missing: raise RuntimeError("tool %s requires %s" % (tool.name, missing))
    return {k: v for k, v in args.items() if k in schema.get("properties", {})}


def no_redirect_client(headers=None, timeout=None, auth=None):
    """The token travels in a custom header; a redirect to another host must not carry it along, so redirects are refused."""
    import httpx
    return httpx.AsyncClient(headers=headers, timeout=timeout or httpx.Timeout(30, read=300), auth=auth, follow_redirects=False)


async def path_extella_mcp(part, rng, agent, device, second, with_tool_names):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    token = open(os.path.join(HOME, "api_token.txt")).read().strip()
    headers = {"X-Auth-Token": token, "X-Profile-Id": "default", "X-Agent-Id": agent}
    wait = timedelta(seconds=180)
    nonce, salt = uuid.uuid4().hex[:12], uuid.uuid4().hex
    rows, repeats, saves, control = [], [], [], []
    part.update({"transport": "MCP streamable HTTP at %s (the real Extella MCP server; official Python SDK client; no fallback)" % MCP_URL,
                 "agent": "the default agent" if agent == DEFAULT_AGENT else "a non-default agent (id not stored)", "run_nonce": nonce, "rows": rows, "repeat_calls": repeats})
    t_start = time.time()
    async with streamablehttp_client(MCP_URL, headers=headers, httpx_client_factory=no_redirect_client) as (r, w, _):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            start_seconds, before, by_name = round(time.time() - t_start, 2), listing(tools), {t.name: t for t in tools}
            for need in ("save_expert", "run_expert", "get_expert"):
                if need not in by_name: raise RuntimeError("the MCP server lists no tool named " + need)
            full = dump(tools)
            fields = {}
            for d in full:
                for key, val in d.items(): fields[key] = fields.get(key, 0) + len(json.dumps(val))
            four = [t for t in tools if t.name in ("save_expert", "run_expert", "get_expert", "search_experts")]
            part.update({"server": {"name": init.serverInfo.name, "version": init.serverInfo.version, "declares_tools_listChanged": bool(init.capabilities.tools and init.capabilities.tools.listChanged)},
                         "session_start_seconds": start_seconds, "tools_listed_before_first": before, "tool_definitions_bytes_by_field": dict(sorted(fields.items(), key=lambda kv: -kv[1])),
                         "program_tools_only": {"names": [t.name for t in four], **listing(four), "note": "the four tools that correspond to the four of the generic executor; the server lists all %d, a client cannot ask for fewer in the listing call" % len(tools)}})
            if with_tool_names: part["tool_names"] = [t.name for t in tools]

            async def stored(ename):
                """The saved record of an expert, or None if there is none."""
                res = await s.call_tool("get_expert", fit(by_name["get_expert"], {"name": ename}), read_timeout_seconds=wait)
                if res.isError:
                    if "not found" in text_of(res).lower(): return None
                    raise RuntimeError("get_expert failed for %s: %s" % (ename, clean(text_of(res), 200)))
                rec = res.structuredContent or parsed(text_of(res))
                return rec if isinstance(rec, dict) else None

            # Before any write: an expert with one of our names that this script did not make stops the run.
            existed = {}
            for ename in EXPERT_NAMES:
                rec = await stored(ename)
                existed[ename] = rec is not None
                if rec is not None and not str(rec.get("description", "")).startswith(MARK):
                    raise RuntimeError("an expert named %s already exists in this account and was not made by this script; nothing was written" % ename)

            if "get_current_profile_and_agent" in by_name:                             # calls that touch no device: the service round trip alone
                for _ in range(5):
                    t = time.time(); res = await s.call_tool("get_current_profile_and_agent", {}, read_timeout_seconds=wait)
                    if not res.isError: control.append(round(time.time() - t, 2))

            async def save(ename, sig, code, desc):
                src = expert_source(ename, sig, code, nonce)
                t = time.time()
                res = await s.call_tool("save_expert", fit(by_name["save_expert"], {"name": ename, "description": "%s: %s" % (MARK, desc), "code": src, "kwargs": {}, "cspl": "fython", "global": False}), read_timeout_seconds=wait)
                return src, round(time.time() - t, 2), bool(res.isError)

            async def run(ename, args, target):
                """One run_expert call. Returns value, nonce found in the answer, facts about the call, scrubbed text for the terminal."""
                t0 = time.time()
                try:
                    res = await s.call_tool("run_expert", fit(by_name["run_expert"], {"name": ename, "params": args, "targets": [target]}), read_timeout_seconds=wait)
                except Exception as e:
                    return None, None, {"seconds": round(time.time() - t0, 2), "platform_run_time_ms": None, "is_error_flag": None, "failure": "client exception: " + error_text(e)[:200]}, ""
                seconds, text = round(time.time() - t0, 2), text_of(res)
                inner = (res.structuredContent or {}).get("result") if res.structuredContent else parsed(text)
                info = {"seconds": seconds, "platform_run_time_ms": inner.get("run_time_ms") if isinstance(inner, dict) else None, "is_error_flag": bool(res.isError)}
                if res.isError: info["failure"] = "the tool call answered with isError"
                elif isinstance(inner, dict) and inner.get("task_id") and "run_time_ms" not in inner: info["failure"] = "deferred run (a task id came back); this script does not poll"
                val = parsed(inner.get("result")) if isinstance(inner, dict) else None
                ok_shape = isinstance(val, dict)
                return (val.get("value") if ok_shape else None), (val.get("nonce") if ok_shape else None), info, clean(str(inner) if inner is not None else text, 600)

            def judge(got, got_nonce, want, info, raw, label):
                ok = same(got, want) and got_nonce == nonce
                if not ok:
                    info.setdefault("failure", "the answer does not carry the nonce of this run (old code ran)" if same(got, want) else "wrong value or an error text instead of a value")
                    print("extella-mcp FAILED", label, raw, file=sys.stderr, flush=True)
                return ok

            for k, (name, sig, code, args, want, desc) in enumerate(CAPS, 1):
                ename = PREFIX + name
                t0 = time.time()
                src, t_save, save_err = await save(ename, sig, code, desc)
                got, got_nonce, info, raw = await run(ename, args, device)
                t_first = round(time.time() - t0, 2)
                rec = await stored(ename)                                              # read back, outside the timed section
                row = {"n": k, "capability": name, "expert": ename, "server_edits": 0, "server_restarts": 0, "seconds_save": t_save, "seconds_run": info["seconds"],
                       "platform_run_time_ms": info["platform_run_time_ms"], "seconds_to_first_call": t_first, "ok": judge(got, got_nonce, want, info, raw, ename),
                       "save_is_error": save_err, "existed_before": existed[ename], "nonce_of_this_run_in_answer": got_nonce == nonce,
                       "read_back_matches": rec is not None and str(rec.get("code", "")).rstrip() == src.rstrip()}
                if "failure" in info: row["failure"] = info["failure"]
                saves.append(t_save); rows.append(row); print("extella-mcp", row, flush=True)
            after = listing((await s.list_tools()).tools)
            part.update({"tools_listed_after_tenth": after, "tool_list_unchanged": before == after})

            # Where did it run? One saved record, only the device in the call changes.
            lname, lsig, lcode, ldesc = LOCATION
            lename, where = PREFIX + lname, {}
            _, t_save, save_err = await save(lename, lsig, lcode, ldesc)
            here = hashlib.sha256((salt + socket.gethostname()).encode()).hexdigest()[:16]
            seen = {}
            for label, target in (("device-1", device), ("device-2", second)):
                if not target: continue
                got, got_nonce, info, raw = await run(lename, {"salt": salt}, target)
                good = isinstance(got, dict) and got_nonce == nonce and isinstance(got.get("host"), str)
                seen[label] = got.get("host") if good else None
                where[label] = {"answered": good, "system": got.get("system") if good else None, "seconds": info["seconds"]}
                if not good: where[label]["failure"] = info.get("failure", "no usable answer"); print("extella-mcp FAILED location", label, raw, file=sys.stderr, flush=True)
            if seen.get("device-1"): where["device-1"]["host_is_this_machine"] = seen["device-1"] == here
            if seen.get("device-2"):
                where["device-2"]["host_is_this_machine"] = seen["device-2"] == here
                where["device-2"]["host_differs_from_device_1"] = bool(seen.get("device-1")) and seen["device-2"] != seen["device-1"]
            # Negative control: a device id that does not exist must fail, not fall back to some default device.
            got, got_nonce, info, raw = await run(PREFIX + CAPS[0][0], CAPS[0][3], str(uuid.uuid4()))
            where["unknown_device"] = {"is_error_flag": info["is_error_flag"], "returned_a_value": got is not None, "says_unavailable": "unavailable" in raw.lower(), "seconds": info["seconds"]}
            part["location_proof"] = {"expert": lename, "existed_before": existed[lename], "save_is_error": save_err, **where,
                                      "note": "host names are compared as salted hashes computed on the device; the salt and the hashes are not stored"}
            print("extella-mcp location", part["location_proof"], flush=True)

            # One call with a wrong parameter name.
            got, got_nonce, info, raw = await run(PREFIX + CAPS[0][0], {"no_such_parameter": 1}, device)
            part["wrong_parameter_call"] = {"is_error_flag": info["is_error_flag"], "answer_reports_error": got is None and ("unexpected keyword" in raw.lower() or "error" in raw.lower()), "seconds": info["seconds"]}

            # Repeat calls of already saved experts: both devices interleaved in one random order.
            targets = {"device-1": device, **({"device-2": second} if second else {})}
            for label, i in repeat_plan(rng, tuple(targets)):
                name, _, _, args, want, _ = CAPS[i]
                got, got_nonce, info, raw = await run(PREFIX + name, args, targets[label])
                ok = judge(got, got_nonce, want, info, raw, "%s on %s" % (PREFIX + name, label))
                repeats.append({"device": label, "capability": name, "seconds": info["seconds"], "platform_run_time_ms": info["platform_run_time_ms"], "ok": ok, **({"failure": info["failure"]} if not ok else {})})
                print("extella-mcp repeat", len(repeats), repeats[-1], flush=True)

    d1, d2 = [r for r in repeats if r["device"] == "device-1"], [r for r in repeats if r["device"] == "device-2"]
    runs1 = [r for r in d1 if r["ok"]] + [{"seconds": r["seconds_run"], "platform_run_time_ms": r["platform_run_time_ms"]} for r in rows if r["ok"]]
    timed1 = [r for r in runs1 if r.get("platform_run_time_ms") is not None]
    split = {"service_round_trip_no_device": dist(control, 2), "save_expert": dist(saves, 2), "run_expert_device_1": dist([r["seconds"] for r in runs1], 2),
             "platform_reported_run_time_device_1": dist([r["platform_run_time_ms"] / 1000 for r in timed1], 2),
             "client_seconds_minus_platform_run_time_device_1": dist([r["seconds"] - r["platform_run_time_ms"] / 1000 for r in timed1], 2),
             "note": "service_round_trip_no_device = get_current_profile_and_agent, a call that reaches the service and no device. run_expert_device_1 = every correct run on device 1 (first runs and repeat calls). The functions themselves take microseconds."}
    if d2:
        ok2 = [r for r in d2 if r["ok"]]
        second_machine = {"repeat_calls": len(d2), "repeat_calls_correct": len(ok2), "repeat_calls_failed": len(d2) - len(ok2), "seconds_repeat_call": dist([r["seconds"] for r in ok2], 2),
                          "platform_reported_run_time": dist([r["platform_run_time_ms"] / 1000 for r in ok2 if r.get("platform_run_time_ms") is not None], 2),
                          "steps_after_saving": 0, "note": "the same saved experts, no save and no other step for this device; the device had a listener installed and bound in advance (a one-time setup, not timed)"}
    else:
        second_machine = "not measured: no second device given"
    part.update({"second_machine": second_machine, "latency_split_seconds": split,
                 "summary": {**summary(rows, d1, nd=2), "server_edits_and_restarts_note": "none by us; the remote server's state is not observable",
                             "seconds_first_capability_including_session_start": round(start_seconds + rows[0]["seconds_to_first_call"], 2),
                             "median_seconds_service_round_trip_no_device": split["service_round_trip_no_device"]["median"] if split["service_round_trip_no_device"] else None,
                             "median_seconds_save": round(statistics.median(saves), 2), "median_seconds_first_run": round(statistics.median([r["seconds_run"] for r in rows if r["ok"]] or [0]), 2),
                             "saves_read_back_matching": "%d of %d" % (sum(bool(r["read_back_matches"]) for r in rows), len(rows)),
                             "second_device_correct": "%d of %d" % (sum(bool(r["ok"]) for r in d2), len(d2)) if d2 else "not measured",
                             "median_seconds_repeat_call_second_device": second_machine["seconds_repeat_call"]["median"] if d2 and second_machine["seconds_repeat_call"] else None}})


# ---------------------------------------------------------------- run
def notice(only, a, device, out):
    lines = ["This run will:"]
    if "fixed" in only or "generic" in only:
        lines.append("  - start local MCP servers as child processes and write only into temporary directories, removed at the end (./programs is not touched)")
    if "extella-mcp" in only:
        calls = len(CAPS) * (1 + ROUNDS) + 2
        lines += ["  - WRITE INTO THE EXTELLA ACCOUNT of the token in ~/.extella/api_token.txt, in the scope of agent %s:" % a.agent,
                  "      create or overwrite %d private experts: %s" % (len(EXPERT_NAMES), ", ".join(EXPERT_NAMES)),
                  "      Extella keeps no versions. The experts REMAIN in the account afterwards; this script deletes nothing (remove them yourself with delete_expert).",
                  "      An existing expert with one of these names that this script did not make stops the run before any write.",
                  "  - run them on the device in ~/.extella/device.txt (about %d calls)%s; one more call names a device that does not exist, on purpose"
                  % (calls, " and on the --second device (about %d calls)" % (len(CAPS) * ROUNDS + 1) if a.second else "")]
    lines.append("  - overwrite the result file %s" % os.path.basename(out))
    print("\n".join(lines), flush=True)


def write(res, out):
    text = clean(json.dumps(res, ensure_ascii=False, indent=1))
    bare = text
    for _, label in SECRETS: bare = bare.replace(label, "")                             # a label must not be mistaken for the value it replaced
    left = [label for value, label in SECRETS if value in bare]
    if left: sys.exit("refusing to write the result: it still contains " + ", ".join(left))
    with open(out, "w") as f: f.write(text + "\n")
    print("written:", os.path.basename(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default=DEFAULT_AGENT, help="Extella agent in whose scope the experts are saved")
    ap.add_argument("--second", default="", help="device id of a second, already prepared device")
    ap.add_argument("--only", default="fixed,generic,extella-mcp", help="comma-separated paths to run")
    ap.add_argument("--yes", action="store_true", help="consent to the account writes of the extella-mcp path without being asked")
    ap.add_argument("--list-tool-names", action="store_true", help="store the names of all tools the Extella server lists (default: only their count and size)")
    ap.add_argument("--note", default="", help="free text about this particular run, stored in the result")
    ap.add_argument("--out", default="", help="result file (default: result3-<date>.json next to this script)")
    a = ap.parse_args()
    only = [x.strip() for x in a.only.split(",") if x.strip()]
    unknown = [x for x in only if x not in ("fixed", "generic", "extella-mcp")]
    if unknown: sys.exit("unknown path: " + ", ".join(unknown))
    try: import mcp  # noqa: F401
    except ImportError: sys.exit("the 'mcp' package is missing: pip install mcp. Nothing was run and nothing was written.")
    out = a.out or os.path.join(HERE, "result3-%s.json" % time.strftime("%Y-%m-%d"))

    device = ""
    if "extella-mcp" in only:                                                          # read before anything runs; no path starts with a half-known setup
        try:
            device = open(os.path.join(HOME, "device.txt")).read().strip()
            token = open(os.path.join(HOME, "api_token.txt")).read().strip()
        except OSError as e: sys.exit("the extella-mcp path needs ~/.extella/api_token.txt and ~/.extella/device.txt (%s). Nothing was run." % type(e).__name__)
        if not device or not token: sys.exit("~/.extella/device.txt or ~/.extella/api_token.txt is empty. Nothing was run.")
        SECRETS.append((token, "<token>"))
        SECRETS.append((device, "<device-1>"))
        if a.second: SECRETS.append((a.second, "<device-2>"))
        if a.agent != DEFAULT_AGENT: SECRETS.append((a.agent, "<agent>"))
    SECRETS.append((os.path.expanduser("~"), "~"))
    for value, label in [(getpass.getuser(), "<user>")] + [(h, "<laptop>") for h in {socket.gethostname(), platform.node(), socket.gethostname().split(".")[0]}]:
        if len(value) >= 4: SECRETS.append((value, label))                             # shorter names would be replaced inside ordinary words
    SECRETS.sort(key=lambda s: -len(s[0]))

    notice(only, a, device, out)
    if "extella-mcp" in only and not a.yes:
        if not sys.stdin.isatty(): sys.exit("the extella-mcp path writes into the account: pass --yes to consent, or leave it out with --only fixed,generic. Nothing was run.")
        if input("Type y to continue: ").strip().lower() != "y": sys.exit("stopped: no consent. Nothing was run.")

    seed = int(time.time())
    rng = random.Random(seed)
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    res = {"date": time.strftime("%Y-%m-%d %H:%M %z"), "capabilities": len(CAPS), "machine": "<laptop>", "os": platform.system(), "python": platform.python_version(),
           "repeat_calls_per_path_and_device": len(CAPS) * ROUNDS, "repeat_order_seed": seed,
           "files_sha256": {"measure3.py": sha(os.path.abspath(__file__)), "generic_server.py": sha(os.path.join(HERE, "generic_server.py"))},
           "notes": NOTES + ([a.note] if a.note else []), "paths": {}, "what_failed": []}
    try:
        from importlib.metadata import version; res["mcp_sdk"] = version("mcp")
    except Exception: pass

    paths = [("fixed", lambda p: path_fixed(p, rng)), ("generic", lambda p: path_generic(p, rng)),
             ("extella-mcp", lambda p: path_extella_mcp(p, rng, a.agent, device, a.second, a.list_tool_names))]
    interrupted, part, key = False, {}, ""

    def partial_summary(p):
        if "summary" not in p:
            p["summary"] = summary(p.get("rows", []), [r for r in p.get("repeat_calls", []) if r.get("device", "device-1") == "device-1"])
        p["incomplete"] = True

    try:
        for key, fn in paths:
            if key not in only: continue
            part = res["paths"][key] = {}
            try: asyncio.run(fn(part))
            except Exception as e:                                                     # a failed path is recorded; the next path still runs. Never a fallback that writes again.
                traceback.print_exc()
                res["what_failed"].append({"path": key, "error": error_text(e)})
                partial_summary(part)
    except BaseException as e:                                                         # Ctrl+C or exit: stop here, keep what was collected, start nothing else
        interrupted = True
        res["interrupted"] = "stopped (%s) during path '%s'; later paths were not started" % (type(e).__name__, key)
        partial_summary(part)

    for key, p in res["paths"].items():                                                # every failed call by name, never hidden in a median
        for kind in ("rows", "repeat_calls"):
            for r in p.get(kind, []):
                if not r["ok"]:
                    res["what_failed"].append({"path": key, "call": "%s %s%s" % ("first call of" if kind == "rows" else "repeat call of", r["capability"], " on " + r["device"] if r.get("device") else ""),
                                               "failure": r.get("failure", "wrong value"), "seconds": r.get("seconds", r.get("seconds_to_first_call"))})
    write(res, out)
    for key, p in res["paths"].items():
        print(key, "|", json.dumps(p["summary"]), "| tools after:", p.get("tools_listed_after_tenth"))
    print("failed:", json.dumps(res["what_failed"]) if res["what_failed"] else "nothing")
    if interrupted: print(res["interrupted"]); sys.exit(130)


if __name__ == "__main__":
    main()
