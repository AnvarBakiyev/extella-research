"""Проверяющий: один для обоих способов. Считает нарушения по состоянию из карточки автора.

Нарушения:
  vydumannoe   житель сослался на факт или значение, которого у него нет
  otklonennoe  действие, недопустимое в этом состоянии (движок его отвергает)
  bessvyaznoe  ответ не разобрался
"""
import json, os, re, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V

NE_ZNACHENIE = ("", "null", "none", "n/a", "na", "-", "?", "unknown", "i don't remember",
                "i dont remember", "don't remember", "not sure", "no idea", "i'm not sure",
                "i do not remember", "unsure", "nothing")

MUSOR = {"people", "guests", "euros", "maybe", "thinks", "the", "at", "a", "about",
         "you", "dont", "remember", "and", "of"}


def _tokeny(s):
    return {t for t in re.findall(r"[a-z0-9:]+", str(s).lower()) if t and t not in MUSOR}


def _displey_znachenie(disp, nom, ya):
    t = (disp.get(nom) or {}).get(ya)
    if not t:
        return None
    if "thinks" in t:
        t = t.split("thinks", 1)[1]
    return t.strip()


def proverit(zapis, deystvie):
    """deystvie: {'act','fact','slot','claim'} или None, если ответ не разобрался."""
    r = zapis["state"]["request"]
    fakty = r.get("facts") or []
    razgovor = r.get("conversation") or []
    ya = r["self"]
    drugoy = r["other"]
    plan_nuzhen = zapis.get("kind") == "plan"
    plan_fakt = r.get("trigger_fact") or 0
    disp = V.displey(zapis["card"])
    bed = {"vydumannoe": [], "otklonennoe": [], "bessvyaznoe": []}

    if not deystvie or not isinstance(deystvie, dict):
        bed["bessvyaznoe"].append("ответ не разобрался")
        return bed
    act = str(deystvie.get("act") or "").lower()
    if act not in ("greet", "tell", "ask", "plan", "silent"):
        bed["bessvyaznoe"].append("действие %r не существует" % act)
        return bed

    if plan_nuzhen and act not in ("plan", "silent"):
        bed["otklonennoe"].append("запрошен план, а действие %s" % act)
    if act == "plan" and not plan_nuzhen:
        bed["otklonennoe"].append("план не запрашивался")

    # Номер по карточке. Обработчик кладёт его в "nomer"; в свободном JSON его пишет модель
    # в поле "fact". Имя факта в движке (f1, f2) номером по карточке НЕ является.
    nomer = deystvie.get("nomer", deystvie.get("fact"))
    k = None
    if act in ("tell", "ask", "plan"):
        try:
            k = int(re.sub(r"[^0-9]", "", str(nomer)))
        except Exception:
            k = None
        if k is None:
            bed["bessvyaznoe"].append("номер факта не разобрался: %r" % nomer)
            return bed
        if k < 1 or k > len(fakty):
            bed["vydumannoe"].append("ссылка на факт [%s], которого у жителя нет" % nomer)
            return bed

    if act == "greet" and any(t["speaker"] == ya and t["act"] == "greet" for t in razgovor):
        bed["otklonennoe"].append("житель уже здоровался")

    if act == "plan" and k is not None and k != plan_fakt:
        bed["otklonennoe"].append("план о факте [%d], а запрошен о [%d]" % (k, plan_fakt))

    if act == "ask" and k is not None:
        ya4 = str(deystvie.get("slot") or "").lower()
        if ya4 not in V.YACHEYKI:
            bed["bessvyaznoe"].append("ячейка %r не существует" % ya4)
        elif fakty[k - 1]["slots"][ya4]["state"] == "sure":
            bed["otklonennoe"].append("спрашивает %s, которое знает наверняка" % ya4)

    if act == "tell" and k is not None:
        f = fakty[k - 1]
        if drugoy in (f.get("told_to") or []):
            bed["otklonennoe"].append("факт [%d] собеседнику уже рассказан" % k)
        claim = deystvie.get("claim") or {}
        if not isinstance(claim, dict):
            bed["bessvyaznoe"].append("claim не объект")
            return bed
        skazano = 0
        for ya4 in V.YACHEYKI:
            v = claim.get(ya4)
            if v is None or str(v).strip().strip(".").lower() in NE_ZNACHENIE:
                continue
            skazano += 1
            sost = f["slots"][ya4]["state"]
            if sost in ("unknown", "forgotten"):
                bed["vydumannoe"].append("%s у факта [%d] житель не знает (%s), а называет %r"
                                         % (ya4, k, sost, v))
                continue
            etalon = _displey_znachenie(disp, k, ya4)
            znach = f["slots"][ya4]["value"]
            if etalon and not (_tokeny(etalon) & _tokeny(v)) and not (_tokeny(znach) & _tokeny(v)):
                bed["vydumannoe"].append("%s у факта [%d] известно как %r, а названо %r"
                                         % (ya4, k, etalon, v))
        if skazano == 0:
            bed["otklonennoe"].append("рассказывает факт [%d], не назвав ни одной ячейки" % k)
    return bed
