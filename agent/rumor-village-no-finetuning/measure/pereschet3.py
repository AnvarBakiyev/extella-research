"""Пересчёт второго замера по сохранённым ответам, без новых вызовов моделей."""
import json, os, sys
ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ZDES); sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V, proverka as P
from zamer3 import chistyy

L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
D = {x["id"]: x for x in L}
for imya in sorted(os.listdir(ZDES)):
    if not (imya.startswith("zamer3_") and imya.endswith(".json")):
        continue
    put = os.path.join(ZDES, imya)
    d = json.load(open(put))
    izm = 0
    for zid, v in d.items():
        zak = V.zakon(chistyy(v["otvet"]), D[zid])
        novo = {"programma": chistyy(v["otvet"]), "prinyato": zak["ok"], "otkaz": zak["otkaz"],
                "podskazka": zak.get("podskazka"), "deystvie": zak["deystvie"],
                "rech": zak["rech"], "rech_ot_modeli": zak.get("rech_ot_modeli", False),
                "bedy": P.proverit(D[zid], zak["deystvie"]) if zak["ok"] else None}
        if any(v.get(k) != novo[k] for k in novo):
            izm += 1
        v.update(novo)
    json.dump(d, open(put, "w"), ensure_ascii=False, indent=1)
    print("%s: %d карточек, изменилось %d" % (imya, len(d), izm))
