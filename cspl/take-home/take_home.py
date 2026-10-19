#!/usr/bin/env python3
"""Run an expert from extella.dev (robot route or site block) on YOUR device.

    python3 take_home.py https://extella.dev/api/robot/export/skill_route_nearest

What it does, in the open:
  1. downloads the bundle: the language handler + the expert (both are JSON)
  2. saves both into your Extella account (your token, your agent, nothing leaves your machine except these two saves)
  3. runs the language handler once on your device, so the device understands route
  4. runs the expert on your device and prints where it ran and what it delivered

Needs: Extella installed and signed in (it writes ~/.extella/api_token.txt and ~/.extella/device.txt).
Options: --token, --device, --agent override the files. --level picks the map (level1 or seed<N>). Python 3.8+, standard library only.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

API = "https://api.extella.ai/api"
HOME = os.path.join(os.path.expanduser("~"), ".extella")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def call(path, body, token, agent, timeout=120):
    req = urllib.request.Request(API + path, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"X-Auth-Token": token, "X-Profile-Id": "default", "X-Agent-Id": agent,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def unwrap(out):
    import ast
    res = out.get("result", out) if isinstance(out, dict) else out
    if isinstance(res, dict) and "result" in res:
        res = res["result"]
    if isinstance(res, str):
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(res)
            except Exception:
                pass
    return res


def run(name, params, token, agent, device):
    t0 = time.time()
    out = call("/expert/run", {"name": name, "params": params, "targets": [device]}, token, agent, timeout=150)
    task = out.get("task_id") if isinstance(out, dict) else None
    while task:
        time.sleep(2)
        chk = call("/tasks/check", {"task_id": task}, token, agent, timeout=30)
        if str(chk.get("status")) in ("completed", "done", "success", "finished", "error", "failed"):
            out = chk
            break
    res = unwrap(out)
    if not isinstance(res, dict):
        res = {"status": "error", "reason": str(res)[:300]}
    res["_seconds"] = round(time.time() - t0, 1)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="bundle URL from the page, or a local .json file")
    ap.add_argument("--token", default=read(os.path.join(HOME, "api_token.txt")))
    ap.add_argument("--device", default=read(os.path.join(HOME, "device.txt")))
    ap.add_argument("--agent", default="")
    ap.add_argument("--level", default="seed7", help="route: level1 or seed<N>; blocks: render")
    a = ap.parse_args()

    if not a.token:
        sys.exit("No Extella token. Install Extella and sign in (it writes ~/.extella/api_token.txt), or pass --token.")
    if not a.device:
        sys.exit("No device id. Start Extella on this machine once (it writes ~/.extella/device.txt), or pass --device.")

    print("1/4  bundle ...", end=" ", flush=True)
    if a.bundle.startswith("http"):
        with urllib.request.urlopen(a.bundle, timeout=60) as r:
            bundle = json.loads(r.read().decode("utf-8"))
    else:
        bundle = json.load(open(a.bundle, encoding="utf-8"))
    experts = bundle.get("experts") or []
    if bundle.get("format") != "extella-expert-bundle/1" or len(experts) != 2:
        sys.exit("This is not an expert bundle from the robot page.")
    handler, expert = experts
    print("ok:", handler["name"], "(language handler) +", expert["name"], "(" + expert["cspl"] + " program)")

    agent = a.agent
    if not agent:
        try:
            agents = call("/agent/list", {}, a.token, "agent_extella_default", timeout=30).get("agents") or []
        except urllib.error.HTTPError as e:
            sys.exit("Token not accepted by the platform (HTTP %d). Check ~/.extella/api_token.txt or pass --token." % e.code)
        ids = [x.get("id") for x in agents]
        agent = "agent_extella_default" if "agent_extella_default" in ids else (ids[0] if ids else "")
        if not agent:
            sys.exit("Your account has no agent yet. Create one in Extella, then rerun.")

    print("2/4  saving both experts into your account (agent %s) ..." % agent, end=" ", flush=True)
    for e in experts:
        out = call("/expert/save", {"name": e["name"], "description": e.get("description", "")[:300], "code": e["code"],
                                    "cspl": e["cspl"], "kwargs": e.get("kwargs") or {}, "global": False}, a.token, agent, timeout=60)
        if out.get("status") != "success":
            sys.exit("save failed for %s: %s" % (e["name"], json.dumps(out)[:200]))
    print("ok")

    print("3/4  teaching your device the %s language ..." % expert["cspl"], end=" ", flush=True)
    reg = run(handler["name"], {}, a.token, agent, a.device)
    if reg.get("status") != "success":
        sys.exit("handler did not register: %s" % json.dumps(reg, ensure_ascii=False)[:300])
    print("ok in %ss, folder %s" % (reg["_seconds"], reg.get("folder", "?")))

    print("4/4  running %s on your device, level %s ..." % (expert["name"], a.level), end=" ", flush=True)
    ep = run(expert["name"], {"level": a.level, "mode": "run"}, a.token, agent, a.device)
    if ep.get("status") != "success":
        sys.exit("run failed: %s" % json.dumps(ep, ensure_ascii=False)[:300])
    print("ok in %ss" % ep["_seconds"])
    print()
    print("ran on        %s  (%s)" % (ep.get("host"), ep.get("os")))
    print("language      %s, handler v%s, sha %s" % (ep.get("language"), ep.get("handler_version"), str(ep.get("handler_sha", ""))[:16]))
    if ep.get("order") is not None:                      # a route expert: three deliveries
        print("rule          %s" % ep.get("rule_text"))
        print("level         %s · start %s · houses %s" % (ep.get("level", {}).get("id"), ep.get("level", {}).get("start"), ep.get("level", {}).get("houses")))
        print("order         %s   moves %s   delivered %s/3" % (" -> ".join(ep.get("order", [])), ep.get("moves"), ep.get("delivered")))
        for d in ep.get("decisions", []):
            print("  at %-7s -> %s: %s" % (d["at"], d["house"], d["why"]))
    if ep.get("html") is not None:                       # a block expert: a rendered fragment
        print("block type    %s · handler %s · law %s" % (ep.get("block_type"), ep.get("handler_name"), ep.get("law")))
        if ep.get("text"):
            print("text output:")
            print(ep["text"])
        else:
            print("html          %d bytes: %s" % (len(ep["html"]), ep["html"][:160].replace(chr(10), " ")))
    print("model calls   %s" % ep.get("model_calls", 0))
    print()
    print("Both experts now live in your account. Change the rules of %s in Extella and run it again: no model, no server of ours." % expert["name"])


if __name__ == "__main__":
    main()
