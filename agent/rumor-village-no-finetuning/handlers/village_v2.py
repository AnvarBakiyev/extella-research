"""Второй закон того же языка village: осторожная деревня.

Язык и программы те же. Меняются только правила исполнения:
  1. Сопернику (relation содержит rival) ничего не рассказывают.
  2. После 20:00 слухи не передают, можно только здороваться, спрашивать и молчать.

Смысл: сохранённые программы жителей не переписываются и модель не вызывается.
Один и тот же ход под первым законом проходит, под вторым получает отказ со строкой.
"""
import re

import village as V

RULES = "village-turn-2-discreet"
YACHEYKI = V.YACHEYKI


def _chas(card):
    m = re.search(r"It is \w+, (\d{1,2}):(\d{2})", card or "")
    return int(m.group(1)) if m else None


def _zapret(zapis):
    r = zapis["state"]["request"]
    if "rival" in (r.get("relation") or ""):
        return "осторожная деревня: сопернику слухи не передают"
    ch = _chas(zapis.get("card", ""))
    if ch is not None and ch >= 20:
        return "осторожная деревня: после 20:00 слухи не передают, сейчас %d:00" % ch
    return None


def dostupno(zapis):
    hody = V.dostupno(zapis)
    if _zapret(zapis):
        hody = [h for h in hody if not h.startswith("tell ")]
    return hody


def zakon(tekst, zapis):
    res = V.zakon(tekst, zapis)
    if res["ok"] and (res["deystvie"] or {}).get("act") == "tell":
        prichina = _zapret(zapis)
        if prichina:
            return {"ok": False, "stroka": res["stroka"], "otkaz": prichina,
                    "podskazka": "допустимо: " + ", ".join(dostupno(zapis)),
                    "deystvie": None, "rech": None}
    return res
