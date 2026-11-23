"""Смена закона без обращения к модели.

Берём ходы, которые уже приняты первым законом, и исполняем те же самые программы
вторым законом. Модель не вызывается ни разу.
"""
import json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V1
import village_v2 as V2

L = [json.loads(l) for l in open(os.path.join(ZDES, "..", "data", "en.jsonl"))]
D = {x["id"]: x for x in L}

for imya in sys.argv[1:]:
    d = json.load(open(os.path.join(ZDES, imya)))
    vzyato = prinyato1 = prinyato2 = 0
    primery = []
    for zid, v in d.items():
        if not v["prinyato"]:
            continue
        z = D[zid]
        vzyato += 1
        r1 = V1.zakon(v["programma"], z)
        r2 = V2.zakon(v["programma"], z)
        prinyato1 += bool(r1["ok"])
        prinyato2 += bool(r2["ok"])
        if r1["ok"] and not r2["ok"] and len(primery) < 3:
            primery.append((zid, v["programma"].splitlines()[0], r2["otkaz"], r2["podskazka"]))
    print("%s: принятых ходов %d; под первым законом проходит %d, под вторым %d, обращений к модели 0"
          % (imya, vzyato, prinyato1, prinyato2))
    for zid, prog, otkaz, podsk in primery:
        print("   %s  %-22s -> %s | %s" % (zid[-8:], prog, otkaz, podsk))
