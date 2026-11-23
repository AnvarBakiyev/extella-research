"""Второй круг: одна попытка после отказа, модели возвращается причина отказа.

  python3 -I zamer2.py A | C
"""
import json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ZDES)
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V
import proverka as P
import zapros as Z
from zamer import oll, deepseek, chistaya_stroka

u = sys.argv[1].upper()
L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
D = {x["id"]: x for x in L}
put = os.path.join(ZDES, "zamer_%s.json" % u)
d = json.load(open(put))
put2 = os.path.join(ZDES, "zamer2_%s.json" % u)
gotovo = json.load(open(put2)) if os.path.exists(put2) else {}

nado = [k for k, v in d.items() if not v["prinyato"] and k not in gotovo]
print("отказов к повтору:", len(nado))
for n, zid in enumerate(nado, 1):
    z = D[zid]
    v = d[zid]
    podsk = ""
    zak = V.zakon(v["programma"], z)
    if zak.get("podskazka"):
        podsk = "\n" + zak["podskazka"]
    prompt = (Z.zapros(z, "yazyk") + "\n\nYou wrote: " + (v["programma"] or "(nothing)") +
              "\nThe engine refused it: " + str(v["otkaz"]) + podsk +
              "\nWrite one line that the engine accepts. One line, nothing else.")
    otv = oll(prompt, 40) if u == "A" else deepseek(prompt)
    prog = chistaya_stroka(otv["text"])
    zak2 = V.zakon(prog, z)
    gotovo[zid] = {"sek": otv["sek"], "tok_in": otv["tok_in"], "otvet": otv["text"][:1000],
                   "programma": prog, "prinyato": zak2["ok"], "otkaz": zak2["otkaz"],
                   "deystvie": zak2["deystvie"], "rech": zak2["rech"],
                   "bedy": P.proverit(z, zak2["deystvie"]) if zak2["ok"] else None}
    json.dump(gotovo, open(put2, "w"), ensure_ascii=False, indent=1)
    print("%3d/%d %s %s %.1fс" % (n, len(nado), zid[-8:],
                                  "принято" if zak2["ok"] else "снова отказ: " + str(zak2["otkaz"])[:50],
                                  otv["sek"]), flush=True)
print("готово")
