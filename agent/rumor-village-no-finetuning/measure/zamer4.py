"""Условие E: тот же DeepSeek-V4-Flash, но закон языка передан как инструкции агента.

Настройка самого агента не меняется: instructions передаются на один запуск.
  python3 -I zamer4.py            первый круг
  python3 -I zamer4.py povtor     круг с возвратом причины отказа
"""
import json, os, re, sys, time, urllib.request

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ZDES); sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V, proverka as P
from zamer3 import chistyy

AGENT = "<agent-id>"   # village_hod_v1: закон в инструкциях, правила и концепты свои
TOK = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()
H = {"X-Auth-Token": TOK, "X-Profile-Id": "default", "X-Agent-Id": AGENT,
     "Content-Type": "application/json"}
INSTR = open(os.path.join(ZDES, "instrukciya_E.txt")).read()


def zvat(vhod):
    t = time.time()
    d = None
    for popytka in range(1, 4):
        try:
            r = urllib.request.Request("https://api.extella.ai/api/agent/run",
                                       data=json.dumps({"agent_id": AGENT, "input": vhod,
                                                        "run_timeout": 300}).encode(), headers=H)
            d = json.loads(urllib.request.urlopen(r, timeout=600).read())
            break
        except Exception as err:
            print("   ошибка платформы (%s), попытка %d" % (str(err)[:60], popytka), flush=True)
            time.sleep(15 * popytka)
    if d is None:
        return {"sek": round(time.time() - t, 1), "text": ""}
    txt = "".join(c.get("text", "") for b in d.get("output", [])
                  for c in b.get("content", []) if c.get("type") == "output_text")
    return {"sek": round(time.time() - t, 1), "text": txt}


def main():
    povtor = len(sys.argv) > 1 and sys.argv[1] == "povtor"
    L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
    D = {x["id"]: x for x in L}
    ids = json.load(open(os.path.join(ZDES, os.environ.get("ZAMER_NABOR", "otbor2.json"))))["ids"]
    predel = int(os.environ.get("ZAMER_PREDEL", "0"))
    if predel:
        ids = ids[:predel]
    put = os.path.join(ZDES, "zamer3_E%s%s.json" % (os.environ.get("ZAMER_METKA", ""), "_povtor" if povtor else ""))
    gotovo = json.load(open(put)) if os.path.exists(put) else {}
    if povtor:
        pervyy = json.load(open(os.path.join(ZDES, "zamer3_E%s.json" % os.environ.get("ZAMER_METKA", ""))))
        ids = [k for k, v in pervyy.items() if not v["prinyato"]]
    for n, zid in enumerate(ids, 1):
        if zid in gotovo:
            continue
        z = D[zid]
        vhod = (z["card"] + "\n\nThe engine accepts only these moves right now:\n" +
                "\n".join("  " + h for h in V.dostupno(z)))
        if povtor:
            v = pervyy[zid]
            vhod += ("\n\nYou wrote:\n" + (v["programma"] or "(nothing)") +
                     "\nThe engine refused it: " + str(v["otkaz"]) +
                     ("\n" + v["podskazka"] if v.get("podskazka") else "") +
                     "\nWrite a move the engine accepts.")
        otv = zvat(vhod)
        prog = chistyy(otv["text"])
        zak = V.zakon(prog, z)
        gotovo[zid] = {"sek": otv["sek"], "tok_in": 0, "tok_out": 0, "otvet": otv["text"][:2000],
                       "programma": prog, "prinyato": zak["ok"], "otkaz": zak["otkaz"],
                       "podskazka": zak.get("podskazka"), "deystvie": zak["deystvie"],
                       "rech": zak["rech"], "rech_ot_modeli": zak.get("rech_ot_modeli", False),
                       "bedy": P.proverit(z, zak["deystvie"]) if zak["ok"] else None}
        json.dump(gotovo, open(put, "w"), ensure_ascii=False, indent=1)
        print("%3d/%d %s %s %.1fс" % (n, len(ids), zid[-8:],
                                      "принято" if zak["ok"] else "отказ: " + str(zak["otkaz"])[:50],
                                      otv["sek"]), flush=True)
    print("готово")


if __name__ == "__main__":
    main()
