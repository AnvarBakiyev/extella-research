#!/usr/bin/env python3
"""Верность первой попытки как функция числа правил (20.10.2026).

Правила порождаются генератором из восьми заготовок с seed, чтобы получать 12, 24, 48 правил
с эталоном автоматически. Эталон — программа на zakaz2, порождённая тем же генератором и
исполненная обработчиком из zamer_long.py; модельные программы (Python и zakaz2) сравниваются
с ней на 100 заказах. Считается только первая попытка: ошибок из 100, токены, время.

Запуск: python3 zamer_scale.py <sonnet|haiku|qwen> <12|24|48> <число прогонов>
  sonnet/haiku — через агента zamer-claude (модель у агента переключается заранее);
  qwen — qwen3.5:9b через Ollama на этой машине, temperature 0.7, без размышлений.
"""
import json, re, time, urllib.request, sys, os, random

_arg = sys.argv[1:]
МОДЕЛЬ = _arg[0] if _arg else "sonnet"
N = int(_arg[1]) if len(_arg) > 1 else 12
ПРОГОНОВ = int(_arg[2]) if len(_arg) > 2 else 3
ПАПКА = "<this folder>"
АГЕНТ = "<agent id>"

sys.argv = ["zamer_long.py", "x", "12"]
_src = open(f"{ПАПКА}/zamer_long.py", encoding="utf-8").read().split('if МЕТКА == "selfcheck"')[0]
exec(_src, globals())   # ГРАММАТИКА, лексемы/Разбор/вычислить/разобрать_программу, ЗАКАЗЫ (seed 20261020)

# ---------- Генератор правил ----------
def породить(n, seed=20261020):
    """Возвращает (текст правил, программа-эталон на zakaz2, список полей, типы полей)."""
    rnd = random.Random(seed * 1000 + n)
    правила, программа, поля, типы = [], [], [], {}
    числа = [];  булевы = []; строки_поля = []
    def добавить(имя, t, текст, строка):
        правила.append(f"{len(правила)+1}. {текст}"); программа.append(f"{имя} = {строка}"); поля.append(имя); типы[имя] = t
        (числа if t == "num" else булевы if t == "bool" else строки_поля if t == "str" else []).append(имя)
    добавить("сумма", "num", 'Сумма заказа ("сумма") = сумма по всем позициям (кол × цена).', "sum(позиции, кол * цена)")
    k = 1
    while len(правила) < n:
        шаблон = rnd.choice("BCDEFGH")
        k += 1
        if шаблон == "B":
            c = rnd.randint(1, 30) * 10000; имя = f"порог_{k}"
            добавить(имя, "bool", f'"{имя}" — истина, если сумма больше {c}, иначе ложь.', f"сумма > {c}")
        elif шаблон == "C":
            a, b, c = rnd.choice([0.1, 0.15, 0.2]), rnd.choice([0.05, 0.08]), rnd.choice([0, 0.02]); имя = f"ставка_{k}"
            добавить(имя, "num", f'"{имя}" по категории клиента: "vip" — {a}, "постоянный" — {b}, "новый" — {c}.',
                     f'if клиент == "vip" then {a} else if клиент == "постоянный" then {b} else {c}')
        elif шаблон == "D":
            d = rnd.randint(0, 5); имя = f"число_{k}"
            добавить(имя, "num", f'"{имя}" — число позиций, у которых кол больше, чем остаток + {d}.', f"count(select(позиции, кол > остаток + {d}, товар))")
        elif шаблон == "E":
            if not числа: continue
            a = rnd.choice(числа); c = rnd.randint(1, 9) * 100; имя = f"значение_{k}"
            добавить(имя, "num", f'"{имя}" = {a} + {c}, затем умножить на число позиций заказа.', f"({a} + {c}) * count(позиции)")
        elif шаблон == "F":
            крупные = [x for x in числа if not x.startswith("ставка") and not x.startswith("число")]
            if not крупные: continue
            a = rnd.choice(крупные); c = rnd.randint(1, 50) * 1000; имя = f"метка_{k}"; s1, s2 = f"выше_{k}", f"ниже_{k}"
            добавить(имя, "str", f'"{имя}": "{s1}", если {a} больше {c}, иначе "{s2}".', f'if {a} > {c} then "{s1}" else "{s2}"')
        elif шаблон == "G":
            t1, t2 = rnd.sample(range(1, 21), 2); имя = f"флаг_{k}"
            добавить(имя, "bool", f'"{имя}" — истина, если в заказе есть товар "Товар-{t1}" или "Товар-{t2}".', f'any(позиции, товар in ["Товар-{t1}", "Товар-{t2}"])')
        elif шаблон == "H":
            if len(булевы) < 2: continue
            a, b = rnd.sample(булевы, 2); имя = f"оба_{k}"
            добавить(имя, "bool", f'"{имя}" — истина, если {a} и {b} истинны одновременно.', f"{a} and {b}")
    return "\n".join(правила), "\n".join(программа), поля, типы

ТЕКСТ, ЭТАЛОН_ПРОГРАММА, ПОЛЯ, ТИПЫ = породить(N)
ЭТАЛОН_РАЗОБРАН = разобрать_программу(ЭТАЛОН_ПРОГРАММА)
def эталон(з):
    окр = [dict(з)]
    for имя, дерево in ЭТАЛОН_РАЗОБРАН: окр[0][имя] = вычислить(дерево, окр)
    return {k: окр[0][k] for k in ПОЛЯ}
ЭТАЛОНЫ = [эталон(з) for з in ЗАКАЗЫ]

ШАПКА = ('Ты — модуль согласования заказов. На вход приходит заказ в JSON: id, клиент (строка: "новый", "постоянный" или "vip"), '
         'доставка (строка: "самовывоз" или "курьер"), позиции; у каждой позиции: товар, кол, цена, остаток.\nПравила:\n' + ТЕКСТ +
         '\nРезультат — объект с полями: ' + ", ".join(ПОЛЯ) + '.')

def совпало(ответ, эт):
    if not isinstance(ответ, dict): return False
    try:
        for k in ПОЛЯ:
            a, b = ответ.get(k), эт[k]
            if isinstance(b, bool):
                if bool(a) is not b: return False
            elif isinstance(b, (int, float)):
                if abs(float(a) - float(b)) > 1e-9: return False
            elif a != b: return False
        return True
    except Exception:
        return False

def ошибок_z(код):
    try: программа = разобрать_программу(код)
    except Exception: return 100
    n = 0
    for з, эт in zip(ЗАКАЗЫ, ЭТАЛОНЫ):
        try:
            окр = [dict(з)]
            for имя, дерево in программа: окр[0][имя] = вычислить(дерево, окр)
            if not совпало({k: окр[0].get(k) for k in ПОЛЯ}, эт): n += 1
        except Exception: n += 1
    return n

def ошибок_p(код):
    пр = {}
    try: exec(код, пр); f = пр["решить"]
    except Exception: return 100
    n = 0
    for з, эт in zip(ЗАКАЗЫ, ЭТАЛОНЫ):
        try:
            if not совпало(f(json.loads(json.dumps(з))), эт): n += 1
        except Exception: n += 1
    return n

# ---------- Вызовы моделей ----------
ТОКЕН = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()
def вызов_агента(промпт, max_out=4000):
    t0 = time.time()
    тело = {"agent_id": АГЕНТ, "input": промпт, "max_output_tokens": max_out, "store": False, "run_timeout": 300}
    req = urllib.request.Request("https://api.extella.ai/api/agent/run", data=json.dumps(тело).encode(),
        headers={"Content-Type": "application/json", "X-Auth-Token": ТОКЕН, "X-Profile-Id": "default", "X-Agent-Id": АГЕНТ})
    for попытка in range(6):
        try: r = json.load(urllib.request.urlopen(req, timeout=330)); break
        except urllib.error.HTTPError as e:
            if e.code != 429 or попытка == 5: raise
            пауза = int(e.headers.get("Retry-After") or 0) or 15 * (попытка + 1); print(f"  (429, жду {пауза} с)", flush=True); time.sleep(пауза)
    time.sleep(1.5)
    текст = "".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
    u = r.get("usage") or {}
    return текст, u.get("input_tokens", 0), u.get("output_tokens", 0), time.time() - t0

def вызов_qwen(промпт, max_out=4000):
    t0 = time.time()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({"model": "qwen3.5:9b", "prompt": промпт, "stream": False,
        "think": False, "options": {"temperature": 0.7, "num_predict": max_out, "num_ctx": 8192}}).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    return r.get("response", ""), r.get("prompt_eval_count", 0), r.get("eval_count", 0), time.time() - t0

вызов = вызов_qwen if МОДЕЛЬ == "qwen" else вызов_агента

def снять_ограду(т):
    m = re.search(r"```(?:\w+)?\s*(.*?)```", т, re.S); return (m.group(1) if m else т).strip()

ПРОМПТ_P = ШАПКА + "\n\nНапиши функцию на Python с сигнатурой `def решить(заказ: dict) -> dict`, реализующую эти правила и возвращающую объект результата. Только код, без пояснений, без примеров."
ПРОМПТ_Z = ШАПКА + "\n\n" + ГРАММАТИКА + "\n\nНапиши программу на языке zakaz2, реализующую эти правила: по строке на каждое поле результата. Только программу, без пояснений и без markdown."

if __name__ == "__main__":
    assert ошибок_z(ЭТАЛОН_ПРОГРАММА) == 0
    итог = {"модель": МОДЕЛЬ, "правил": N, "знаков_правил": len(ТЕКСТ), "прогоны": []}
    for i in range(1, ПРОГОНОВ + 1):
        for вариант, промпт, проверка in (("python", ПРОМПТ_P, ошибок_p), ("zakaz2", ПРОМПТ_Z, ошибок_z)):
            текст, вх, вых, сек = вызов(промпт)
            код = снять_ограду(текст); n = проверка(код)
            итог["прогоны"].append({"прогон": i, "вариант": вариант, "вход": вх, "выход": вых, "сек": round(сек, 1), "ошибок_из_100": n,
                                   "строк": len([с for с in код.splitlines() if с.strip()]), "код": код})
            print(f"  {МОДЕЛЬ} {N} правил, прогон {i}, {вариант}: вход {вх}, выход {вых}, {сек:.0f} c, ошибок {n}/100", flush=True)
            json.dump(итог, open(f"{ПАПКА}/results_scale_{МОДЕЛЬ}_{N}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("== ИТОГ", МОДЕЛЬ, N, {v: [p["ошибок_из_100"] for p in итог["прогоны"] if p["вариант"] == v] for v in ("python", "zakaz2")})
