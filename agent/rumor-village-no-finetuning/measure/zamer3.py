"""Второй замер: новый запрос, новые 200 карточек.

  python3 -I zamer3.py A2 | C2        первый круг
  python3 -I zamer3.py A2 povtor      круг с возвратом причины отказа
"""
import json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ZDES)
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V
import proverka as P
import zapros as Z
from zamer import oll, deepseek

MODEL = {"A2": "9B", "C2": "deepseek"}


HODY = ("greet", "tell", "ask", "plan", "silent")


def chistyy(txt):
    """Ход ищем по ключевому слову, а не по номеру строки: модель может рассуждать вслух."""
    stroki = [l.strip().strip("`").strip() for l in (txt or "").strip().splitlines()]
    stroki = [l for l in stroki if l and not l.startswith("#")]
    nachalo = None
    for i, l in enumerate(stroki):
        if l.split() and l.split()[0].lower() in HODY:
            nachalo = i
    if nachalo is None:
        return "\n".join(stroki[:2])
    out = [stroki[nachalo]]
    if nachalo + 1 < len(stroki):
        out.append(stroki[nachalo + 1])
    return "\n".join(out)


def zvat(u, prompt):
    return oll(prompt, 90) if MODEL[u] == "9B" else deepseek(prompt)


def main():
    u = sys.argv[1]
    povtor = len(sys.argv) > 2 and sys.argv[2] == "povtor"
    L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
    D = {x["id"]: x for x in L}
    ids = json.load(open(os.path.join(ZDES, os.environ.get("ZAMER_NABOR", "otbor2.json"))))["ids"]
    predel = int(os.environ.get("ZAMER_PREDEL", "0"))
    if predel:
        ids = ids[:predel]
    put = os.path.join(ZDES, "zamer3_%s%s%s.json" % (u, os.environ.get("ZAMER_METKA", ""), "_povtor" if povtor else ""))
    gotovo = json.load(open(put)) if os.path.exists(put) else {}
    if povtor:
        pervyy = json.load(open(os.path.join(ZDES, "zamer3_%s%s.json" % (u, os.environ.get("ZAMER_METKA", "")))))
        ids = [k for k, v in pervyy.items() if not v["prinyato"]]
    for n, zid in enumerate(ids, 1):
        if zid in gotovo:
            continue
        z = D[zid]
        prompt = Z.zapros2(z)
        if povtor:
            v = pervyy[zid]
            prompt += ("\n\nYou wrote:\n" + (v["programma"] or "(nothing)") +
                       "\nThe engine refused it: " + str(v["otkaz"]) +
                       ("\n" + v["podskazka"] if v.get("podskazka") else "") +
                       "\nWrite a move the engine accepts.")
        otv = zvat(u, prompt)
        prog = chistyy(otv["text"])
        zak = V.zakon(prog, z)
        gotovo[zid] = {"sek": otv["sek"], "tok_in": otv["tok_in"], "tok_out": otv["tok_out"],
                       "otvet": otv["text"][:2000], "programma": prog,
                       "prinyato": zak["ok"], "otkaz": zak["otkaz"],
                       "podskazka": zak.get("podskazka"), "deystvie": zak["deystvie"],
                       "rech": zak["rech"], "rech_ot_modeli": zak.get("rech_ot_modeli", False),
                       "bedy": P.proverit(z, zak["deystvie"]) if zak["ok"] else None}
        print("%3d/%d %s %s %.1fс" % (n, len(ids), zid[-8:],
                                      "принято" if zak["ok"] else "отказ: " + str(zak["otkaz"])[:55],
                                      otv["sek"]), flush=True)
        json.dump(gotovo, open(put, "w"), ensure_ascii=False, indent=1)
    print("готово")


if __name__ == "__main__":
    main()
