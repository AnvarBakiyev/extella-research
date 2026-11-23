"""Прогон 200 карточек Rumor Village четырьмя условиями.

  python3 -I zamer.py A        9B через язык village
  python3 -I zamer.py B        9B свободным JSON
  python3 -I zamer.py C        DeepSeek-V4-Flash через язык village
  python3 -I zamer.py D        DeepSeek-V4-Flash свободным JSON

Переменные: ZAMER_PREDEL=<n> ограничить число карточек.
Результат пишется по одной карточке в zamer_<условие>.json, прогон можно продолжить.
"""
import json, os, re, sys, time, urllib.request

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ZDES)
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V
import proverka as P
import zapros as Z

AGENT = "<agent-id>"   # DeepSeek-V4-Flash
TOK = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()
H = {"X-Auth-Token": TOK, "X-Profile-Id": "default", "X-Agent-Id": AGENT,
     "Content-Type": "application/json"}
USLOVIYA = {"A": ("9B", "yazyk"), "B": ("9B", "json"),
            "C": ("deepseek", "yazyk"), "D": ("deepseek", "json")}


def oll(prompt, predict):
    t = time.time()
    r = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({
        "model": "qwen3.5:9b", "prompt": prompt, "stream": False, "think": False,
        "options": {"num_ctx": 4096, "num_predict": predict, "temperature": 0}}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(r, timeout=600).read())
    return {"sek": round(time.time() - t, 1), "text": d.get("response", ""),
            "tok_out": d.get("eval_count", 0), "tok_in": d.get("prompt_eval_count", 0)}


def deepseek(prompt):
    t = time.time()
    d = None
    for popytka in range(1, 4):
        try:
            r = urllib.request.Request("https://api.extella.ai/api/agent/run",
                                       data=json.dumps({"agent_id": AGENT, "input": prompt,
                                                        "run_timeout": 300}).encode(), headers=H)
            d = json.loads(urllib.request.urlopen(r, timeout=600).read())
            break
        except Exception as err:
            print("   платформа ответила ошибкой (%s), попытка %d" % (str(err)[:70], popytka),
                  flush=True)
            time.sleep(15 * popytka)
    if d is None:
        return {"sek": round(time.time() - t, 1), "text": "", "tok_out": 0, "tok_in": 0,
                "sboy": True}
    txt = ""
    try:
        for blok in d.get("output", []):
            for ch in blok.get("content", []):
                if ch.get("type") == "output_text":
                    txt += ch.get("text", "")
    except Exception:
        txt = ""
    if not txt:
        m = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', json.dumps(d, ensure_ascii=False))
        txt = m.group(1).encode().decode("unicode_escape") if m else ""
    return {"sek": round(time.time() - t, 1), "text": txt, "tok_out": 0, "tok_in": 0}


def chistaya_stroka(txt):
    for l in (txt or "").strip().splitlines():
        l = l.strip().strip("`").strip()
        if l and not l.startswith("#"):
            return l
    return ""


def razbor_json(txt):
    t = (txt or "").strip()
    t = re.sub(r"^```[a-zA-Z]*", "", t).strip().strip("`").strip()
    nach = t.find("{")
    if nach < 0:
        return None
    gl = 0
    for i, ch in enumerate(t[nach:], nach):
        if ch == "{":
            gl += 1
        elif ch == "}":
            gl -= 1
            if gl == 0:
                try:
                    return json.loads(t[nach:i + 1])
                except Exception:
                    return None
    return None


def main():
    uslovie = sys.argv[1].upper()
    model, sposob = USLOVIYA[uslovie]
    L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
    D = {x["id"]: x for x in L}
    ids = json.load(open(os.path.join(ZDES, "otbor.json")))["ids"]
    predel = int(os.environ.get("ZAMER_PREDEL", "0"))
    if predel:
        ids = ids[:predel]
    put = os.path.join(ZDES, "zamer_%s.json" % uslovie)
    gotovo = json.load(open(put)) if os.path.exists(put) else {}
    for n, zid in enumerate(ids, 1):
        if zid in gotovo:
            continue
        z = D[zid]
        prompt = Z.zapros(z, sposob)
        otv = oll(prompt, 40 if sposob == "yazyk" else 220) if model == "9B" else deepseek(prompt)
        zap = {"sek": otv["sek"], "tok_in": otv["tok_in"], "tok_out": otv["tok_out"],
               "otvet": otv["text"][:2000]}
        if sposob == "yazyk":
            prog = chistaya_stroka(otv["text"])
            zak = V.zakon(prog, z)
            zap["programma"] = prog
            zap["prinyato"] = zak["ok"]
            zap["otkaz"] = zak["otkaz"]
            zap["deystvie"] = zak["deystvie"]
            zap["rech"] = zak["rech"]
            zap["bedy"] = P.proverit(z, zak["deystvie"]) if zak["ok"] else None
        else:
            d = razbor_json(otv["text"])
            zap["deystvie"] = d
            zap["prinyato"] = d is not None
            zap["bedy"] = P.proverit(z, d)
        gotovo[zid] = zap
        json.dump(gotovo, open(put, "w"), ensure_ascii=False, indent=1)
        metka = "принято" if zap["prinyato"] else "отказ"
        bd = zap.get("bedy") or {}
        nar = sum(len(v) for v in bd.values()) if bd else 0
        print("%3d/%d %s %s нарушений %d %.1fс" % (n, len(ids), zid[-8:], metka, nar, zap["sek"]),
              flush=True)
    print("готово, записано в", put)


if __name__ == "__main__":
    main()
