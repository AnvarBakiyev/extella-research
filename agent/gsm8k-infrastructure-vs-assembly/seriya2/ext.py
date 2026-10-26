"""Тонкий клиент Extella REST для серии 2. Токен читается из ~/.extella/api_token.txt и не печатается."""
import ast, json, os, time, urllib.request
API = "https://api.extella.ai/api"
TOKEN = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()
AGENT = "<agent-id>"
MAC = "<mac-device-id>"
VPS = "<server-1-device-id>"

def call(path, body, timeout=180):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={"X-Auth-Token": TOKEN, "X-Profile-Id": "default", "X-Agent-Id": AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def parse(res):
    for _ in range(4):
        if isinstance(res, dict) and "result" in res and ("execution_log" in res or "expert_name" in res or "task_id" in res or set(res) <= {"result", "status"}):
            res = res["result"]; continue
        if isinstance(res, str):
            for loader in (json.loads, ast.literal_eval):
                try: res = loader(res); break
                except Exception: pass
            else: return res
            continue
        break
    return res

def save(name, code, cspl, description, kwargs=None):
    return call("/expert/save", {"name": name, "description": description, "code": code, "cspl": cspl, "kwargs": kwargs or {}})

def run(name, params, target, wait=3600):
    t0 = time.time()
    out = call("/expert/run", {"name": name, "params": params, "targets": [target]})
    task = out.get("task_id") if isinstance(out, dict) else None
    def final(o):
        st = str(o.get("status", "")).lower(); res = str(o.get("result", ""))
        return st in ("completed", "done", "finished", "error", "failed") or (st == "success" and "deferred" not in res.lower())
    while task and not final(out) and time.time() - t0 < wait:
        time.sleep(2)
        out = call("/tasks/check", {"task_id": task})
    return parse(out), time.time() - t0
