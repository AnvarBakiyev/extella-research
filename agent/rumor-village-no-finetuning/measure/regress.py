"""Regression for the village law. Run: python3 -I regress.py

The law itself refuses in Russian, so the expected fragments below stay in Russian.
Only the case names and the verdicts are English.
"""
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
    ("empty turn", "", zapis(), False, "ход пуст"),
    ("not in the language", "dance", zapis(), False, "не на языке village"),
    ("two action lines", "greet\nsilent", zapis(), False, "одно действие"),
    ("silent is always legal", "silent", zapis(), True, None),
    ("greet is legal", "greet", zapis(razgovor=PRIVET_EGO), True, None),
    ("greet twice", "greet", zapis(razgovor=PRIVET_MOY), False, "уже здоровался"),
    ("greet takes no arguments", "greet Rafael", zapis(), False, "нет дополнений"),
    ("tell a slot the villager knows", "tell 1 who",
     zapis(fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("tell a slot it does not know", "tell 1 where",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "не знает where"),
    ("tell a forgotten slot", "tell 1 who",
     zapis(fakty=[("party", {"who": "forgotten"}, [])]), False, "забыл who"),
    ("tell a doubted slot", "tell 1 who",
     zapis(fakty=[("party", {"who": "doubt"}, [])]), True, None),
    ("tell the same listener twice", "tell 1 who",
     zapis(fakty=[("party", {"who": "sure"}, ["him"])]), False, "уже рассказан"),
    ("all with no known slot", "tell 1 all",
     zapis(fakty=[("party", {"who": "unknown"}, [])]), False, "ни одной ячейки"),
    ("no such fact", "tell 2 who",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "факта [2] нет"),
    ("no facts at all", "tell 1 who", zapis(), False, "ни одного факта"),
    ("fact number is not a number", "tell один who", zapis(), False, "должен быть числом"),
    ("no such slot", "tell 1 price",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "ячейки 'price' нет"),
    ("ask about an unknown slot", "ask 1 where",
     zapis(fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("ask about a slot known for sure", "ask 1 who",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "спрашивать нечего"),
    ("plan when none was asked for", "plan 1",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "не запрашивался"),
    ("tell when a plan was asked for", "tell 1 who",
     zapis(kind="plan", trigger=1, fakty=[("party", {"who": "sure"}, [])]),
     False, "запрошен план"),
    ("plan about the right fact", "plan 1",
     zapis(kind="plan", trigger=1, fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("plan about another fact", "plan 1",
     zapis(kind="plan", trigger=2, fakty=[("party", {"who": "sure"}, []),
                                          ("fine", {"who": "sure"}, [])]),
     False, "а не о [1]"),
    ("silent when a plan was asked for", "silent",
     zapis(kind="plan", trigger=1, fakty=[("party", {"who": "sure"}, [])]), True, None),
]


RECH = [
    ("speech with nothing borrowed", "tell 1 who\nsay: Have you heard? It is about Vwho.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), True, None),
    ("a name that was not supplied", "tell 1 who\nsay: Pedro told me about it.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "имя, которого обработчик не выдавал"),
    ("a number that was not supplied", "tell 1 who\nsay: There were 999 of them, Vwho said.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "число, которого обработчик не выдавал"),
    ("an event not being spoken about", "tell 1 who\nsay: There is a wedding at the mill, Vwho says.",
     zapis(fakty=[("party", {"who": "sure"}, [])]), False, "о чём житель не говорит"),
    ("a guess stated as certain", "tell 1 who\nsay: It is Vwho.",
     zapis(fakty=[("party", {"who": "doubt"}, [])]), False, "это догадка"),
    ("a guess with a hedge", "tell 1 who\nsay: Maybe it is Vwho.",
     zapis(fakty=[("party", {"who": "doubt"}, [])]), True, None),
    ("second line without say: is speech", "greet\nHello there, neighbour.",
     zapis(), True, None),
    ("say with no action", "say: Hello there.", zapis(), False, "нет действия"),
    ("two actions plus say", "greet\nsilent\nsay: Hi.", zapis(), False, "одно действие"),
]
SLUCHAI = SLUCHAI + RECH


def main():
    soshlos = 0
    for imya, prog, z, zhdem_ok, kusok in SLUCHAI:
        r = V.zakon(prog, z)
        bed = []
        if r["ok"] != zhdem_ok:
            bed.append("expected %s, got %s" % ("accepted" if zhdem_ok else "refused",
                                                "accepted" if r["ok"] else "refused: " + str(r["otkaz"])))
        if kusok and kusok not in (r["otkaz"] or ""):
            bed.append("reason lacks %r, reason was: %r" % (kusok, r["otkaz"]))
        if not r["ok"] and r["stroka"] is None:
            bed.append("refused without a line number")
        print(("%-38s %s" % (imya, "ok" if not bed else "MISMATCH: " + "; ".join(bed))))
        soshlos += not bed
    # the guess has to reach claim
    r = V.zakon("tell 1 all", zapis(fakty=[("party", {"who": "doubt", "amount": "sure"}, [])]))
    ok = r["ok"] and r["deystvie"]["claim"]["guess"] == ["who"] and r["deystvie"]["claim"]["amount"] == "Vamount"
    print("%-38s %s" % ("the guess is marked in claim", "ok" if ok else "MISMATCH: " + json.dumps(r, ensure_ascii=False)))
    soshlos += ok
    vsego = len(SLUCHAI) + 1
    print("\n%d of %d cases ok" % (soshlos, vsego))
    return 0 if soshlos == vsego else 1


if __name__ == "__main__":
    sys.exit(main())
