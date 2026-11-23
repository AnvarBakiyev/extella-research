"""Регрессия закона языка village. Запуск: python3 -I regress.py"""
import json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ZDES, "..", "handlers"))
import village as V


def zapis(kind="turn", fakty=(), razgovor=(), trigger=0, card=None):
    f = []
    for i, (what, slots, told_to) in enumerate(fakty, 1):
        f.append({"fact": "f%d" % i, "what": what, "told_by": None, "heard_at": 1,
                  "told_to": list(told_to),
                  "slots": {y: {"state": slots.get(y, "unknown"),
                                "value": {"sure": "V" + y, "doubt": "V" + y}.get(slots.get(y)),
                                "source": None} for y in V.YACHEYKI}})
    if card is None:
        card = "You are Ana, a farmer (shy).\nIn front of you is Rafael, a neighbor.\n"
        for i, (what, slots, _) in enumerate(fakty, 1):
            izv = " · ".join("%s: %s" % (y, "V" + y) for y in V.YACHEYKI
                                  if slots.get(y) in ("sure", "doubt"))
            card += "[%d] %s · %s\n" % (i, what, izv)
    return {"kind": kind, "card": card,
            "state": {"request": {"self": "me", "other": "him", "facts": f,
                                  "conversation": list(razgovor), "trigger_fact": trigger}}}


PRIVET_MOY = [{"speaker": "me", "act": "greet", "fact": None, "claim": None}]
PRIVET_EGO = [{"speaker": "him", "act": "greet", "fact": None, "claim": None}]

SLUCHAI = [
    ("пустой ход", "", zapis(), False, "ход пуст"),
    ("не на языке", "dance", zapis(), False, "не на языке village"),
    ("две строки", "greet\nsilent", zapis(), False, "одно действие"),
    ("молчание всегда можно", "silent", zapis(), True, None),
    ("привет можно", "greet", zapis(razgovor=PRIVET_EGO), True, None),
    ("привет дважды нельзя", "greet", zapis(razgovor=PRIVET_MOY), False, "уже здоровался"),
    ("у greet нет дополнений", "greet Rafael", zapis(), False, "нет дополнений"),
    ("рассказать известное", "tell 1 who",
     zapis(fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("рассказать неизвестное", "tell 1 where",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "не знает where"),
    ("рассказать забытое", "tell 1 who",
     zapis(fakty=[("party", {"who": "forgotten"}, [])]), False, "забыл who"),
    ("рассказать сомнительное можно", "tell 1 who",
     zapis(fakty=[("party", {"who": "doubt"}, [])]), True, None),
    ("повтор тому же собеседнику", "tell 1 who",
     zapis(fakty=[("party", {"who": "sure"}, ["him"])]), False, "уже рассказан"),
    ("all без известных ячеек", "tell 1 all",
     zapis(fakty=[("party", {"who": "unknown"}, [])]), False, "ни одной ячейки"),
    ("нет такого факта", "tell 2 who",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "факта [2] нет"),
    ("фактов нет совсем", "tell 1 who", zapis(), False, "ни одного факта"),
    ("номер не число", "tell один who", zapis(), False, "должен быть числом"),
    ("ячейки нет", "tell 1 price",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "ячейки 'price' нет"),
    ("спросить неизвестное", "ask 1 where",
     zapis(fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("спросить известное наверняка", "ask 1 who",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "спрашивать нечего"),
    ("план не запрашивался", "plan 1",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "не запрашивался"),
    ("план запрошен, а рассказываем", "tell 1 who",
     zapis(kind="plan", trigger=1, fakty=[("party", {"who": "sure"}, [])]),
     False, "запрошен план"),
    ("план о том факте", "plan 1",
     zapis(kind="plan", trigger=1, fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("план о другом факте", "plan 1",
     zapis(kind="plan", trigger=2, fakty=[("party", {"who": "sure"}, []),
                                          ("fine", {"who": "sure"}, [])]),
     False, "а не о [1]"),
    ("молчание при запросе плана", "silent",
     zapis(kind="plan", trigger=1, fakty=[("party", {"who": "sure"}, [])]), True, None),
]


RECH = [
    ("речь без чужого проходит", "tell 1 who\nsay: Have you heard? It is about Vwho.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("чужое имя во фразе", "tell 1 who\nsay: Pedro told me about it.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "имя, которого обработчик не выдавал"),
    ("чужое число во фразе", "tell 1 who\nsay: There were 999 of them, Vwho said.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "число, которого обработчик не выдавал"),
    ("чужое событие во фразе", "tell 1 who\nsay: There is a wedding at the mill, Vwho says.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "о чём житель не говорит"),
    ("догадка без оговорки", "tell 1 who\nsay: It is Vwho.",
     zapis(fakty=[("party", {"who": "doubt"}, [])]), False, "это догадка"),
    ("догадка с оговоркой", "tell 1 who\nsay: Maybe it is Vwho.",
     zapis(fakty=[("party", {"who": "doubt"}, [])]), True, None),
    ("речь без пометки say это речь", "greet\nHello there, neighbour.",
     zapis(), True, None),
    ("say без действия", "say: Hello there.", zapis(), False, "нет действия"),
    ("два действия с say", "greet\nsilent\nsay: Hi.", zapis(), False, "одно действие"),
]
SLUCHAI = SLUCHAI + RECH


def main():
    soshlos = 0
    for imya, prog, z, zhdem_ok, kusok in SLUCHAI:
        r = V.zakon(prog, z)
        bed = []
        if r["ok"] != zhdem_ok:
            bed.append("ждали %s, получили %s" % ("принятие" if zhdem_ok else "отказ",
                                                  "принятие" if r["ok"] else "отказ: " + str(r["otkaz"])))
        if kusok and kusok not in (r["otkaz"] or ""):
            bed.append("в причине нет %r, причина: %r" % (kusok, r["otkaz"]))
        if not r["ok"] and r["stroka"] is None:
            bed.append("отказ без номера строки")
        print(("%-34s %s" % (imya, "сошлось" if not bed else "РАСХОЖДЕНИЕ: " + "; ".join(bed))))
        soshlos += not bed
    # догадка попадает в claim
    r = V.zakon("tell 1 all", zapis(fakty=[("party", {"who": "doubt", "amount": "sure"}, [])]))
    ok = r["ok"] and r["deystvie"]["claim"]["guess"] == ["who"] and r["deystvie"]["claim"]["amount"] == "Vamount"
    print("%-34s %s" % ("догадка помечена в claim", "сошлось" if ok else "РАСХОЖДЕНИЕ: " + json.dumps(r, ensure_ascii=False)))
    soshlos += ok
    vsego = len(SLUCHAI) + 1
    print("\nсошлось %d из %d" % (soshlos, vsego))
    return 0 if soshlos == vsego else 1


if __name__ == "__main__":
    sys.exit(main())
