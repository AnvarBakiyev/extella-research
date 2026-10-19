"""Опыт 21, шаг 2: тот же сценарий, что в опыте 16, на локальном Windmill (открытая редакция, одна машина).
Операция «стоимость фонда у второго кастодиана», три потребителя вызывают её по пути, замена Python -> Go с тем же контрактом,
вызов на 30 секунд в полёте во время замены, откат. Потребители не правятся."""
import json, threading, time, urllib.request, urllib.error
B = "http://127.0.0.1:8300/api"; WS = "op21b"; P = "u/admin/fund_value_b"; WANT = 492127140105.4; rec = {"timeline": []}; T0 = time.time(); TOKEN = None
def http(method, path, body=None, timeout=900):
    req = urllib.request.Request(B + path, data=None if body is None else json.dumps(body).encode(), method=method, headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            t = r.read().decode()
            try: return r.status, json.loads(t)
            except ValueError: return r.status, t
    except urllib.error.HTTPError as ex: return ex.code, ex.read().decode()[:400]
def note(what, **kw): rec["timeline"].append({"at": round(time.time() - T0, 1), "what": what, **kw}); print(round(time.time() - T0, 1), what, json.dumps(kw, ensure_ascii=False)[:260], flush=True)
def judge(out): return {"impl": out.get("impl") if isinstance(out, dict) else None, "correct": isinstance(out, dict) and abs(float(out.get("value_usd", 0)) - WANT) < 0.01, "error": None if isinstance(out, dict) and "impl" in out else str(out)[:200]}
PY = '''import csv, time
def main(fund: str, statement: str, pause: float = 0):
    total = 0.0; rows = 0; num = lambda v: float(v.replace(",", "."))
    with open(statement, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["Portfolio"].strip() == fund: total += num(r["Settled holding"]) * num(r["Market price"]) * num(r["FX to USD"]); rows += 1
    time.sleep(float(pause))
    return {"fund": fund, "value_usd": round(total, 2), "rows": rows, "impl": "python-v1"}
'''
GO = '''package inner

import (
	"bufio"
	"encoding/csv"
	"io"
	"math"
	"os"
	"strconv"
	"strings"
	"time"
)

func num(v string) float64 { f, _ := strconv.ParseFloat(strings.Replace(v, ",", ".", 1), 64); return f }

func main(fund string, statement string, pause float64) (interface{}, error) {
	f, err := os.Open(statement)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	in := bufio.NewReader(f)
	if b, _ := in.Peek(3); len(b) == 3 && b[0] == 0xEF {
		in.Discard(3)
	}
	r := csv.NewReader(in)
	r.Comma = ';'
	head, _ := r.Read()
	ix := map[string]int{}
	for i, h := range head {
		ix[strings.TrimSpace(h)] = i
	}
	total, rows := 0.0, 0
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		if strings.TrimSpace(row[ix["Portfolio"]]) == fund {
			total += num(row[ix["Settled holding"]]) * num(row[ix["Market price"]]) * num(row[ix["FX to USD"]])
			rows++
		}
	}
	time.Sleep(time.Duration(pause * float64(time.Second)))
	return map[string]interface{}{"fund": fund, "value_usd": math.Round(total*100) / 100, "rows": rows, "impl": "go-v2"}, nil
}
'''
SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": ["fund", "statement"], "properties": {"fund": {"type": "string"}, "statement": {"type": "string"}, "pause": {"type": "number", "default": 0}}}
ARGS = {"fund": "FUND045", "statement": "/data/custodian2_statement.csv"}
def run(pause=0):
    t = time.time(); s, r = http("POST", f"/w/{WS}/jobs/run_wait_result/p/{P}", {**ARGS, "pause": pause}); return round(time.time() - t, 2), r if s == 200 else {"http": s, "err": str(r)[:300]}
def deploy(content, lang, parent=None, summary=""):
    body = {"path": P, "summary": summary, "description": "op21", "content": content, "language": lang, "schema": SCHEMA, "is_template": False, "kind": "script"}
    if parent: body["parent_hash"] = parent
    t = time.time(); s, r = http("POST", f"/w/{WS}/scripts/create", body); api = round(time.time() - t, 2)
    h = r if isinstance(r, str) else None
    for _ in range(240):  # развёртывание идёт отдельной задачей (зависимости, сборка); ждём, пока версия станет вызываемой
        s2, d = http("GET", f"/w/{WS}/scripts/deployment_status/h/{h}")
        if isinstance(d, dict) and d.get("lock") is not None or (isinstance(d, dict) and d.get("lock_error_logs")): break
        time.sleep(0.5)
    rec.setdefault("deploys", []).append({"summary": summary, "api_seconds": api, "until_callable_seconds": round(time.time() - t, 2), "status": d if isinstance(d, dict) else str(d)[:200]})
    return round(time.time() - t, 2), s, r
def current_hash():
    s, r = http("GET", f"/w/{WS}/scripts/get/p/{P}"); return r.get("hash") if isinstance(r, dict) else None

s, r = http("POST", "/auth/login", {"email": "admin@windmill.dev", "password": "changeme"}); assert s == 200, (s, r); TOKEN = r if isinstance(r, str) else r.get("token")
s, r = http("GET", "/version"); note("version", version=str(r)[:80])
s, r = http("POST", "/workspaces/create", {"id": WS, "name": WS}); note("workspace", http=s, resp=str(r)[:120])
if True:
    sec, s, r = deploy(PY, "python3", summary="v1 python"); note("prepare: deploy v1 (1 действие)", seconds=sec, http=s, resp=str(r)[:80])
    time.sleep(2)
h1 = current_hash(); note("hash v1", hash=h1)
sec, out = run(); note("первый вызов v1 (холодный)", seconds=sec, **judge(out))
lat = []
for i in range(10): sec, out = run(); lat.append(sec); assert judge(out)["correct"], out
note("10 повторных вызовов v1", seconds_min=min(lat), seconds_max=max(lat), median=sorted(lat)[5])
cons = [dict(zip(("seconds", "out"), run())) for _ in range(3)]; note("три потребителя до замены", results=[{**judge(c["out"]), "s": c["seconds"]} for c in cons])
flight = {}
def inflight(): flight["seconds"], flight["out"] = run(pause=30)
th = threading.Thread(target=inflight); th.start(); time.sleep(6)
sec, s, r = deploy(GO, "go", parent=h1, summary="v2 go"); note("ЗАМЕНА: deploy v2 go (1 действие)", seconds=sec, http=s, resp=str(r)[:120])
h2 = current_hash(); note("hash v2", hash=h2)
sec, out = run(); note("первый вызов после замены (сборка Go)", seconds=sec, **judge(out))
cons = [dict(zip(("seconds", "out"), run())) for _ in range(3)]; note("три потребителя после замены", results=[{**judge(c["out"]), "s": c["seconds"]} for c in cons])
th.join(); note("вызов, шедший во время замены", seconds=flight.get("seconds"), **judge(flight.get("out")))
s, hist = http("GET", f"/w/{WS}/scripts/history/p/{P}"); note("история версий", http=s, count=len(hist) if isinstance(hist, list) else None, sample=json.dumps(hist, ensure_ascii=False)[:200])
t = time.time(); s, old = http("GET", f"/w/{WS}/scripts/get/h/{h1}"); a = 1
sec, s2, r = deploy(old.get("content", ""), old.get("language", "python3"), parent=h2, summary="rollback to v1") if isinstance(old, dict) else (0, s, old); a += 1
note("ОТКАТ: взять прежнюю версию по хешу и развернуть (2 действия через API)", seconds=round(time.time() - t, 2), http=s2, actions=a)
sec, out = run(); note("вызов после отката", seconds=sec, **judge(out))
json.dump(rec, open("result_windmill_2workers.json", "w"), ensure_ascii=False, indent=1)
