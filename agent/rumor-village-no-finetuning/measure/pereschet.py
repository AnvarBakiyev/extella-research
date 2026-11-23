"""Пересчёт нарушений по уже сохранённым ответам моделей, без новых вызовов.

Запуск: python3 -I pereschet.py
"""
import json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ZDES)
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V
import proverka as P
from zamer import chistaya_stroka, razbor_json

L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
D = {x["id"]: x for x in L}

for u in "ABCD":
    put = os.path.join(ZDES, "zamer_%s.json" % u)
    if not os.path.exists(put):
        continue
    d = json.load(open(put))
    yazyk = u in ("A", "C")
    izm = 0
    for zid, v in d.items():
        z = D[zid]
        if yazyk:
            zak = V.zakon(chistaya_stroka(v["otvet"]), z)
            novo = {"programma": chistaya_stroka(v["otvet"]), "prinyato": zak["ok"],
                    "otkaz": zak["otkaz"], "deystvie": zak["deystvie"], "rech": zak["rech"],
                    "bedy": P.proverit(z, zak["deystvie"]) if zak["ok"] else None}
        else:
            dd = razbor_json(v["otvet"])
            novo = {"deystvie": dd, "prinyato": dd is not None, "bedy": P.proverit(z, dd)}
        if any(v.get(k) != novo[k] for k in novo):
            izm += 1
        v.update(novo)
    json.dump(d, open(put, "w"), ensure_ascii=False, indent=1)
    print("%s: пересчитано %d карточек, изменилось %d" % (u, len(d), izm))
