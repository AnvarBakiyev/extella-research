"""Сводка второго замера. Карточка принята, если принят первый круг, иначе если принят повтор."""
import collections, json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
IMENA = {"A2": "Qwen 3.5 9B, новый запрос", "C2": "DeepSeek-V4-Flash, новый запрос",
         "E": "DeepSeek-V4-Flash, агент с законом в инструкциях"}


def svod(u):
    p1 = os.path.join(ZDES, "zamer3_%s.json" % u)
    if not os.path.exists(p1):
        return None
    d1 = json.load(open(p1))
    p2 = os.path.join(ZDES, "zamer3_%s_povtor.json" % u)
    d2 = json.load(open(p2)) if os.path.exists(p2) else {}
    pervyy = sum(1 for v in d1.values() if v["prinyato"])
    itog = sum(1 for k, v in d1.items()
               if v["prinyato"] or (d2.get(k) or {}).get("prinyato"))
    nar = collections.Counter()
    for isto in (d1, d2):
        for v in isto.values():
            for vid, spisok in (v.get("bedy") or {}).items():
                nar[vid] += len(spisok)
    otkazy = collections.Counter()
    for k, v in d1.items():
        if not v["prinyato"] and not (d2.get(k) or {}).get("prinyato"):
            otkazy[((d2.get(k) or v).get("otkaz") or "").split(":")[0][:55]] += 1
    rech = sum(1 for v in d1.values() if v.get("rech_ot_modeli"))
    tin = [v["tok_in"] for v in d1.values() if v["tok_in"]]
    sek = sum(v["sek"] for v in d1.values()) / max(len(d1), 1)
    return {"n": len(d1), "pervyy": pervyy, "itog": itog, "nar": nar, "otkazy": otkazy,
            "rech": rech, "tok": (sum(tin) // len(tin), max(tin)) if tin else None, "sek": sek}


def main():
    print("| условие | карточек | принято с первого раза | принято после повтора | выдуманных | отклонённых | речь от модели | секунд | токенов |")
    print("|---|---|---|---|---|---|---|---|---|")
    for u in ("A2", "C2", "E"):
        s = svod(u)
        if not s:
            continue
        print("| %s | %d | %d (%.1f %%) | %d (%.1f %%) | %d | %d | %d | %.1f | %s |"
              % (IMENA[u], s["n"], s["pervyy"], 100.0 * s["pervyy"] / s["n"],
                 s["itog"], 100.0 * s["itog"] / s["n"], s["nar"]["vydumannoe"],
                 s["nar"]["otklonennoe"], s["rech"], s["sek"],
                 "%d (макс %d)" % s["tok"] if s["tok"] else "не считались"))
    print()
    for u in ("A2", "C2", "E"):
        s = svod(u)
        if not s or not s["otkazy"]:
            continue
        print("### %s: осталось без хода %d" % (IMENA[u], sum(s["otkazy"].values())))
        for k, n in s["otkazy"].most_common(8):
            print("- %d × %s" % (n, k))
        print()


if __name__ == "__main__":
    main()
