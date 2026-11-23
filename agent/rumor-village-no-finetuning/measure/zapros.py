"""Запросы к модели: через язык village и свободным JSON. Один и тот же текст карточки."""

YAZYK = """Reply with ONE line and nothing else. The lines you may write:
  greet
  tell 1 who where
  tell 1 all
  ask 1 where
  plan 1
  silent
The number is a fact number from the list above. Slots are who, where, when, amount.
Never write a value: the engine fills values from what you know. Do not explain."""

SVOBODNO = """Reply with ONE JSON object and nothing else:
{"act": "greet", "fact": null, "slot": null, "claim": null}
act is one of greet, tell, ask, plan, silent. fact is a fact number from the list above,
used by tell, ask and plan. slot is used by ask and is one of who, where, when, amount.
claim is used by tell and looks like
{"who": "Elena", "where": "the bakery", "when": "tomorrow 12:30", "amount": "200 people", "guess": []}
with the values you know, exactly as you know them, null where you do not know,
and guess listing the slots you are not sure about. Do not explain."""


def zapros(zapis, sposob):
    return zapis["card"] + "\n\n" + (YAZYK if sposob == "yazyk" else SVOBODNO)


import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "handlers"))
import village as _V


def zapros2(zapis):
    """Второй замер: без готовых примеров, с перечнем допустимого на этой карточке."""
    hody = "\n".join("  " + h for h in _V.dostupno(zapis))
    return (zapis["card"] + "\n\nThe engine accepts only these moves right now:\n" + hody +
            "\n\nAnswer in two lines:\n"
            "  first line: one move copied from the list above, dropping the slots you keep\n"
            "    to yourself; nothing else is a move, 'turn' and 'plan' alone are not moves\n"
            "  say: one short sentence the villager says out loud\n"
            "Never put a name or a number the villager does not know: the engine checks every one.\n"
            "A slot marked (guess) is not certain: say it with maybe, I think or they say.\n"
            "If a slot is a guess, say it as a guess. After silent write no say line. Do not explain.")
