"""Язык `village`: один ход жителя деревни из Rumor Village.

Замысел: модель называет действие и ячейки, но НЕ печатает значения. Значения подставляет
обработчик из того, что житель действительно знает. Поэтому выдуманное воспоминание в этом
языке невыразимо, а не запрещено просьбой.

Грамматика (ровно одна строка на ход):
    greet
    tell <номер факта> <ячейка> [<ячейка> ...]      ячейки: who where when amount, или all
    ask <номер факта> <ячейка>
    plan <номер факта>
    silent

Закон:
    greet       отказ, если житель уже здоровался в этом разговоре
    tell        отказ: нет такого факта; ячейка не из списка; ячейка не известна жителю
                (unknown или forgotten); собеседнику этот факт уже рассказан; ни одной ячейки
    ask         отказ: нет такого факта; ячейка уже известна наверняка
    plan        отказ, если план в этом ходе не запрашивался; отказ на не тот факт
    при запросе плана отказ на любое другое действие
    больше одной строки  отказ: ход это одно действие

Ячейка в состоянии doubt рассказывается как догадка, значение берётся то же.
"""

RULES = "village-turn-2"
YACHEYKI = ("who", "where", "when", "amount")


SOBYTIYA = ("party", "wedding", "funeral", "concert", "market", "meeting", "dinner",
            "fiesta", "match", "game", "trip", "festival")


def dostupno(zapis):
    """Что закон принимает на этой карточке прямо сейчас. Список, а не ответ."""
    r = zapis["state"]["request"]
    fakty = r.get("facts") or []
    razgovor = r.get("conversation") or []
    ya, drugoy = r["self"], r["other"]
    plan_nuzhen = zapis.get("kind") == "plan"
    plan_fakt = r.get("trigger_fact") or 0
    if plan_nuzhen:
        return ["plan %d" % plan_fakt, "silent"]
    out = []
    if not any(t["speaker"] == ya and t["act"] == "greet" for t in razgovor):
        out.append("greet")
    for k, f in enumerate(fakty, 1):
        if drugoy not in (f.get("told_to") or []):
            mozhno = []
            for y in YACHEYKI:
                sost = f["slots"][y]["state"]
                if sost == "sure":
                    mozhno.append(y)
                elif sost == "doubt":
                    mozhno.append(y + "(guess)")   # такую ячейку надо произносить с оговоркой
            if mozhno:
                out.append("tell %d %s" % (k, " ".join(mozhno)))
        for y in YACHEYKI:
            if f["slots"][y]["state"] != "sure":
                out.append("ask %d %s" % (k, y))
    out.append("silent")
    return out


def _stroki(tekst):
    out = []
    for i, s in enumerate(tekst.splitlines(), 1):
        s = s.strip()
        if not s or s.startswith("#"):
            continue
        out.append((i, s))
    return out


def displey(card):
    """Из текста карточки достаёт, как выглядят ячейки для человека: {номер: {ячейка: текст}}."""
    out = {}
    for s in card.splitlines():
        s = s.strip()
        if not (s.startswith("[") and "]" in s):
            continue
        nom = s[1:s.index("]")]
        if not nom.isdigit():
            continue
        chasti = s[s.index("]") + 1:].split("·")
        d = {"what": chasti[0].strip()}
        for ch in chasti[1:]:
            if ":" in ch:
                k, v = ch.split(":", 1)
                d[k.strip()] = v.strip()
        out[int(nom)] = d
    return out


def imya_sobesednika(card):
    """«In front of you is Rafael, a neighbor and coworker.» -> Rafael."""
    for t in card.splitlines():
        t = t.strip()
        if t.startswith("In front of you is "):
            x = t[len("In front of you is "):].rstrip(".")
            return x.split(",")[0].strip()
    return "neighbour"


def _otkaz(nom, prichina, podskazka=None, zapis=None):
    if podskazka is None and zapis is not None:
        podskazka = "\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u043e: " + ", ".join(dostupno(zapis))
    return {"ok": False, "stroka": nom, "otkaz": prichina, "podskazka": podskazka,
            "deystvie": None, "rech": None}


def _zakon_vnutri(tekst, zapis, derzhatel):
    """Разбирает ход и либо отдаёт действие, либо отказывает со строкой и причиной."""
    r = zapis["state"]["request"]
    fakty = r.get("facts") or []
    razgovor = r.get("conversation") or []
    ya = r["self"]
    sobesednik = r["other"]
    plan_nuzhen = zapis.get("kind") == "plan"
    plan_fakt = r.get("trigger_fact") or 0
    disp = displey(zapis["card"])

    def otk(nom, prichina, podskazka=None):
        spisok = "\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u043e: " + ", ".join(dostupno(zapis))
        return _otkaz(nom, prichina, (podskazka + "; " + spisok) if podskazka else spisok)

    stroki = _stroki(tekst or "")
    if not stroki:
        return otk(0, "ход пуст: нужна одна строка", "greet, tell, ask, plan или silent")

    rech_modeli = None
    deystviya = []
    for n_, s_ in stroki:
        pervoe = s_.split()[0].lower() if s_.split() else ""
        if s_.lower().startswith("say:"):
            rech_modeli = s_[4:].strip().strip('"')
            derzhatel["rech"] = rech_modeli
        elif deystviya and pervoe not in ("greet", "tell", "ask", "plan", "silent"):
            # строка после хода без пометки say это всё равно речь, а не второй ход
            rech_modeli = s_.strip().strip('"')
            derzhatel["rech"] = rech_modeli
        else:
            deystviya.append((n_, s_))
    if not deystviya:
        return otk(stroki[0][0], "\u0435\u0441\u0442\u044c say, \u043d\u043e \u043d\u0435\u0442 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f")
    if len(deystviya) > 1:
        return otk(deystviya[1][0], "\u0445\u043e\u0434 \u044d\u0442\u043e \u043e\u0434\u043d\u043e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435, \u0430 \u0438\u0445 \u0431\u043e\u043b\u044c\u0448\u0435")
    nom, s = deystviya[0]
    # пометку в скобках (от нас «(guess)» или своё значение от модели) отбрасываем целиком,
    # включая незакрытую: значение всё равно подставляет обработчик
    import re as _re3
    s = _re3.sub(r"\([^)]*\)?", "", s).strip()
    slova = s.split()
    cmd = slova[0].lower()

    if cmd not in ("greet", "tell", "ask", "plan", "silent"):
        return otk(nom, "строка %d не на языке village: %s" % (nom, s),
                      "есть greet, tell, ask, plan, silent")

    if plan_nuzhen and cmd not in ("plan", "silent"):
        return otk(nom, "в этом ходе запрошен план о факте [%d], а не %s" % (plan_fakt, cmd))
    if cmd == "plan" and not plan_nuzhen:
        return otk(nom, "план в этом ходе не запрашивался")

    def fakt_po_nomeru(tok):
        if not tok.isdigit():
            return None, "номер факта должен быть числом, а не %r" % tok
        k = int(tok)
        if k < 1 or k > len(fakty):
            if not fakty:
                return None, "житель не знает ни одного факта, рассказывать нечего"
            return None, "факта [%d] нет, известны [1]..[%d]" % (k, len(fakty))
        return k, None

    if cmd == "silent":
        return {"ok": True, "stroka": nom, "otkaz": None, "podskazka": None,
                "deystvie": {"act": "silent", "fact": None, "claim": None},
                "rech": ""}

    if cmd == "greet":
        if len(slova) > 1:
            return otk(nom, "у greet нет дополнений")
        if any(t["speaker"] == ya and t["act"] == "greet" for t in razgovor):
            return otk(nom, "житель уже здоровался в этом разговоре")
        return {"ok": True, "stroka": nom, "otkaz": None, "podskazka": None,
                "deystvie": {"act": "greet", "fact": None, "claim": None},
                "rech": "Hello, %s." % imya_sobesednika(zapis["card"])}

    if cmd == "plan":
        if len(slova) != 2:
            return otk(nom, "нужно: plan <номер факта>")
        k, err = fakt_po_nomeru(slova[1])
        if err:
            return otk(nom, err)
        if k != plan_fakt:
            return otk(nom, "запрошен план о факте [%d], а не о [%d]" % (plan_fakt, k))
        f = fakty[k - 1]
        return {"ok": True, "stroka": nom, "otkaz": None, "podskazka": None,
                "deystvie": {"act": "plan", "fact": f["fact"], "nomer": k, "claim": None},
                "rech": "I think I will go to the %s." % f["what"]}

    if cmd == "ask":
        if len(slova) != 3:
            return otk(nom, "нужно: ask <номер факта> <ячейка>")
        k, err = fakt_po_nomeru(slova[1])
        if err:
            return otk(nom, err)
        ya4 = slova[2].lower()
        if ya4 not in YACHEYKI:
            return otk(nom, "ячейки %r нет, есть who, where, when, amount" % ya4)
        f = fakty[k - 1]
        if f["slots"][ya4]["state"] == "sure":
            return otk(nom, "житель и так знает %s наверняка, спрашивать нечего" % ya4)
        return {"ok": True, "stroka": nom, "otkaz": None, "podskazka": None,
                "deystvie": {"act": "ask", "fact": f["fact"], "nomer": k, "slot": ya4, "claim": None},
                "rech": {"who": "Do you know who the %s is about?",
                         "where": "Do you know where the %s is?",
                         "when": "Do you know when the %s is?",
                         "amount": "Do you know how much the %s is about?"}[ya4] % f["what"]}

    # tell
    if len(slova) < 3:
        return otk(nom, "нужно: tell <номер факта> <ячейка> [<ячейка> ...]")
    k, err = fakt_po_nomeru(slova[1])
    if err:
        return otk(nom, err)
    f = fakty[k - 1]
    if sobesednik in (f.get("told_to") or []):
        return otk(nom, "факт [%d] собеседнику уже рассказан" % k,
                      "можно спросить ask или промолчать silent")
    # в скобках модель пишет пометку: (guess) от нас или своё значение. Обработчик
    # скобки отбрасывает и значение всё равно подставляет сам, так что это просто шум.
    prosheno = [t.lower() for t in slova[2:]]
    if prosheno == ["all"]:
        prosheno = [y for y in YACHEYKI if f["slots"][y]["state"] in ("sure", "doubt")]
        if not prosheno:
            return otk(nom, "у факта [%d] житель не знает ни одной ячейки" % k)
    for y in prosheno:
        if y not in YACHEYKI:
            return otk(nom, "ячейки %r нет, есть who, where, when, amount" % y)
        sost = f["slots"][y]["state"]
        if sost == "unknown":
            return otk(nom, "житель не знает %s у факта [%d]" % (y, k),
                          "это можно спросить: ask %d %s" % (k, y))
        if sost == "forgotten":
            return otk(nom, "житель забыл %s у факта [%d]" % (y, k),
                          "это можно спросить: ask %d %s" % (k, y))
    claim = {y: (f["slots"][y]["value"] if y in prosheno else None) for y in YACHEYKI}
    claim["guess"] = [y for y in prosheno if f["slots"][y]["state"] == "doubt"]
    kuski = []
    for y in prosheno:
        t = disp.get(k, {}).get(y)
        if t is None:
            t = str(f["slots"][y]["value"])
        if y in claim["guess"] and "thinks" in t:
            t = "maybe " + t.split("thinks", 1)[1].strip()
        kuski.append(t)
    return {"ok": True, "stroka": nom, "otkaz": None, "podskazka": None,
            "deystvie": {"act": "tell", "fact": f["fact"], "nomer": k, "claim": claim},
            "rech": "Have you heard about the %s? %s." % (f["what"], ", ".join(kuski))}


OBYCHNYE = {"i", "you", "he", "she", "we", "they", "the", "a", "an", "do", "did", "have",
            "has", "is", "are", "was", "were", "it", "that", "this", "my", "your", "about",
            "hello", "hi", "yes", "no", "but", "and", "or", "if", "so", "not", "know",
            "heard", "think", "will", "go", "going", "to", "at", "on", "in", "of", "for",
            "what", "when", "where", "who", "how", "much", "many", "maybe", "sure",
            "tomorrow", "today", "yesterday", "morning", "evening", "night", "people",
            "guests", "euros", "something", "anything", "nothing", "there", "here"}


SLOVAR_MIRA = ("fine", "inheritance", "lottery", "party", "wedding",
               "bakery", "bar", "chapel", "church", "fountain", "market", "mill",
               "pharmacy", "river", "school", "square", "town hall")


def _mirovye(s):
    import re as _re
    t = " " + _re.sub(r"[^a-z ]+", " ", str(s).lower()) + " "
    return {w for w in SLOVAR_MIRA if (" " + w + " ") in t}


def _chisla(s):
    import re as _re
    return set(_re.findall(r"\d+", str(s)))


def _imena(s):
    import re as _re
    out = set()
    for predlozhenie in _re.split(r"[.!?]", str(s)):
        slova = _re.findall(r"[A-Za-z][A-Za-z'\-]*", predlozhenie)
        slova = [w.split("'")[0] for w in slova]
        slova = [w for w in slova if w]
        for i, w in enumerate(slova):
            if w[0].isupper() and (i > 0 or w.lower() not in OBYCHNYE) and w.lower() not in OBYCHNYE:
                out.add(w)
    return out


def _zagruzit_imena():
    """На устройстве файла рядом нет, там имена приходят параметром эксперта."""
    import json as _j, os as _o
    try:
        p = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "imena_mira.json")
    except NameError:
        return set()
    try:
        return set(_j.load(open(p)))
    except Exception:
        return set()


IMENA_MIRA = _zagruzit_imena()


def proverka_rechi(rech, deystvie, zapis):
    """Возвращает причину отказа или None. Во фразе не должно быть значений, которых
    обработчик не выдавал: ни чужих чисел, ни чужих имён."""
    if not rech or len(rech) > 220:
        return "фраза пуста или длиннее 220 знаков"
    disp = displey(zapis["card"])
    razresheno = {imya_sobesednika(zapis["card"])}
    for t in zapis["card"].splitlines():
        t = t.strip()
        if t.startswith("You are "):
            razresheno.add(t[len("You are "):].split(",")[0].strip())
    chisla = set()
    if (deystvie or {}).get("act") == "tell":
        k = deystvie.get("nomer")
        nazvano = [y for y in YACHEYKI if (deystvie.get("claim") or {}).get(y) is not None]
        for y in nazvano:
            tekst = (disp.get(k) or {}).get(y) or str((deystvie.get("claim") or {})[y])
            razresheno |= _imena(tekst)
            chisla |= _chisla(tekst)
        razresheno |= _imena((disp.get(k) or {}).get("what") or "")
    if (deystvie or {}).get("act") in ("ask", "plan"):
        # здесь claim нет, поэтому житель вправе назвать всё, что знает об этом факте
        k = deystvie.get("nomer")
        razresheno |= _imena((disp.get(k) or {}).get("what") or "")
        fakty = zapis["state"]["request"].get("facts") or []
        if k and 1 <= k <= len(fakty):
            for y in YACHEYKI:
                if fakty[k - 1]["slots"][y]["state"] in ("sure", "doubt"):
                    tekst = (disp.get(k) or {}).get(y) or ""
                    razresheno |= _imena(tekst)
                    chisla |= _chisla(tekst)
    # имя ловим только по списку имён этого мира: иначе «Hey» и испанское «Oye»
    # попадают в имена, а это дефект проверяющего, а не нарушение закона
    chuzhie_imena = (_imena(rech) & IMENA_MIRA) - razresheno
    if chuzhie_imena:
        return "во фразе имя, которого обработчик не выдавал: %s" % ", ".join(sorted(chuzhie_imena))
    chuzhie_chisla = _chisla(rech) - chisla
    if chuzhie_chisla:
        return "во фразе число, которого обработчик не выдавал: %s" % ", ".join(sorted(chuzhie_chisla))
    razresheno_mir = set()
    k = (deystvie or {}).get("nomer")
    if k:
        razresheno_mir |= _mirovye((disp.get(k) or {}).get("what") or "")
        if (deystvie or {}).get("act") == "tell":
            for y in YACHEYKI:
                if (deystvie.get("claim") or {}).get(y) is not None:
                    razresheno_mir |= _mirovye((disp.get(k) or {}).get(y) or "")
        else:
            for y in YACHEYKI:
                razresheno_mir |= _mirovye((disp.get(k) or {}).get(y) or "")
    dogadki = (deystvie or {}).get("claim", {}) or {}
    if dogadki.get("guess"):
        ogovorki = ("maybe", "perhaps", "i think", "they say", "she says", "he says",
                    "apparently", "not sure", "i heard", "seems", "supposedly", "or so",
                    "i believe", "might", "could be", "something like")
        if not any(o in rech.lower() for o in ogovorki):
            return ("ячейка %s это догадка, а фраза говорит о ней как о точном"
                    % ", ".join(dogadki["guess"]))
    chuzhie_mir = _mirovye(rech) - razresheno_mir
    if chuzhie_mir:
        return ("во фразе есть то, о чём житель не говорит: %s"
                % ", ".join(sorted(chuzhie_mir)))
    return None


def zakon(tekst, zapis):
    derzhatel = {}
    res = _zakon_vnutri(tekst, zapis, derzhatel)
    rech = derzhatel.get("rech")
    if res["ok"] and rech:
        beda = proverka_rechi(rech, res["deystvie"], zapis)
        if beda:
            return _otkaz(res["stroka"], beda,
                          "допустимо: " + ", ".join(dostupno(zapis)))
        res["rech"] = rech
        res["rech_ot_modeli"] = True
    return res
