#!/usr/bin/env python3
"""Бенчмарк повторяющихся правил: способы A (навык), B (код на лету), C (сохранённая программа).
Протокол: PROTOKOL.md. Запуск: python3 zamer_sposoby.py sonnet   (агент zamer-claude на нужной модели)
Пишет results_<модель>.json и печатает сводку.
"""
import json, re, time, urllib.request, sys, os, traceback

МЕТКА = sys.argv[1] if len(sys.argv) > 1 else "sonnet"
ЛОКАЛЬНО = МЕТКА == "qwen9b"
CODEX = МЕТКА == "gpt"
ИСТОЧНИК = "sonnet" if (ЛОКАЛЬНО or CODEX) else МЕТКА  # программы для способа C берём из прогонов Sonnet
АГЕНТ = "<agent id>"
ТОКЕН = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()
ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
ЗАМЕР = os.path.join(os.path.dirname(ЗДЕСЬ), "zamer-navyki-vs-eksperty")
N = 50

# ---- задача zakaz3 ----
ЗАКАЗЫ3 = json.load(open(f"{ЗАМЕР}/dataset.json", encoding="utf-8"))[:N]
ПРАВИЛА3 = """Ты — модуль согласования заказов. На вход приходит заказ в JSON: id, клиент, позиции; у каждой позиции: товар, кол, цена, остаток.
Правила:
1. Сумма заказа = сумма по всем позициям (кол × цена).
2. Если сумма больше 200000 — маршрут "ждать_менеджера", иначе "резерв".
3. Позиция в дефиците, если кол больше остатка. Перечисли товары таких позиций в порядке следования.
Результат — объект {"сумма": <целое число>, "маршрут": "<ждать_менеджера|резерв>", "дефицит": [<товары>]}"""
ПОЛЯ3 = ["сумма", "маршрут", "дефицит"]
def эталон3(з): return з["эталон"]
def вход3(з): return {k: v for k, v in з.items() if k != "эталон"}
ПРОГРАММА3 = json.load(open(f"{ЗАМЕР}/results_claude_{ИСТОЧНИК}.json", encoding="utf-8"))["эксперт"]["попытки"][-1]["код"]
ТОКЕНЫ_СОЗДАНИЯ3 = json.load(open(f"{ЗАМЕР}/results_claude_{ИСТОЧНИК}.json", encoding="utf-8"))["эксперт"]["токены_создания"]

# ---- задача zakaz12 (из zamer_long.py) ----
sys.argv = ["zamer_long.py", "x", "12"]
_g = {}; exec(open(f"{ЗАМЕР}/zamer_long.py", encoding="utf-8").read().split('if МЕТКА == "selfcheck"')[0], _g)
ЗАКАЗЫ12 = _g["ЗАКАЗЫ"][:N]; ПРАВИЛА12 = _g["ШАПКА"]; ПОЛЯ12 = _g["ПОЛЯ"]; ЭТАЛОН12 = _g["ЭТАЛОН"]; совпало12 = _g["совпало"]
ПРОГРАММА12 = json.load(open(f"{ЗАМЕР}/results_long_{ИСТОЧНИК}_12.json", encoding="utf-8"))["python"]["попытки"][-1]["код"]
ТОКЕНЫ_СОЗДАНИЯ12 = json.load(open(f"{ЗАМЕР}/results_long_{ИСТОЧНИК}_12.json", encoding="utf-8"))["python"]["токены_создания"]

def совпало3(ответ, эт):
    try:
        return (int(ответ.get("сумма")) == эт["сумма"] and ответ.get("маршрут") == эт["маршрут"] and list(ответ.get("дефицит", [])) == эт["дефицит"])
    except Exception:
        return False

ЗАДАЧИ = {
    "zakaz3": dict(заказы=ЗАКАЗЫ3, правила=ПРАВИЛА3, вход=вход3, эталон=эталон3, совпало=совпало3, программа=ПРОГРАММА3, создание=ТОКЕНЫ_СОЗДАНИЯ3),
    "zakaz12": dict(заказы=ЗАКАЗЫ12, правила=ПРАВИЛА12, вход=lambda з: з, эталон=ЭТАЛОН12, совпало=совпало12, программа=ПРОГРАММА12, создание=ТОКЕНЫ_СОЗДАНИЯ12),
}

def вызов_qwen(промпт, max_out=1500):
    t0 = time.time()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({"model": "qwen3.5:9b", "prompt": промпт, "stream": False,
        "think": False, "options": {"temperature": 0, "num_predict": max_out, "num_ctx": 8192}}).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    return r.get("response", ""), r.get("prompt_eval_count", 0), r.get("eval_count", 0), time.time() - t0

import subprocess, tempfile
_CODEX_DIR = tempfile.mkdtemp(prefix="codex-bench-")
subprocess.run(["git", "init", "-q"], cwd=_CODEX_DIR)
def вызов_codex(промпт, max_out=1500):
    """GPT через подписку ChatGPT: codex exec --json. Вход включает системный промпт Codex (~20 тыс. токенов,
    большей частью из кеша), поэтому входные токены с другими способами не сравниваются; выход и верность сравнимы."""
    t0 = time.time()
    r = subprocess.run(["codex", "exec", "--json", "--skip-git-repo-check", "-m", "gpt-6-astra", "-s", "read-only",
                        "-c", 'model_reasoning_effort="low"', промпт], cwd=_CODEX_DIR, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    текст = ""; u = {}
    for line in r.stdout.splitlines():
        try: e = json.loads(line)
        except Exception: continue
        if e.get("type") == "item.completed" and e.get("item", {}).get("type") == "agent_message": текст = e["item"].get("text", "")
        if e.get("type") == "turn.completed": u = e.get("usage", {})
    return текст, u.get("input_tokens", 0), u.get("output_tokens", 0) + u.get("reasoning_output_tokens", 0), time.time() - t0

def вызов(промпт, max_out=1500):
    if ЛОКАЛЬНО: return вызов_qwen(промпт, max_out)
    if CODEX: return вызов_codex(промпт, max_out)
    t0 = time.time()
    тело = {"agent_id": АГЕНТ, "input": промпт, "max_output_tokens": max_out, "store": False, "run_timeout": 180}
    req = urllib.request.Request("https://api.extella.ai/api/agent/run", data=json.dumps(тело).encode(),
        headers={"Content-Type": "application/json", "X-Auth-Token": ТОКЕН, "X-Profile-Id": "default", "X-Agent-Id": АГЕНТ})
    for попытка in range(6):
        try: r = json.load(urllib.request.urlopen(req, timeout=240)); break
        except urllib.error.HTTPError as e:
            if e.code != 429 or попытка == 5: raise
            пауза = int(e.headers.get("Retry-After") or 0) or 15 * (попытка + 1); print(f"  (429, жду {пауза} с)", flush=True); time.sleep(пауза)
    time.sleep(1.5)
    текст = "".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
    u = r.get("usage") or {}
    return текст, u.get("input_tokens", 0), u.get("output_tokens", 0), time.time() - t0

def разобрать_json(т):
    m = re.search(r"\{.*\}", т, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

def снять_ограду(т):
    m = re.search(r"```(?:\w+)?\s*(.*?)```", т, re.S); return (m.group(1) if m else т).strip()

def исполнить(код, заказ):
    пр = {}; exec(код, пр); return пр["решить"](json.loads(json.dumps(заказ)))

итог = {"модель": МЕТКА, "n": N, "задачи": {}}
for имя, т in ЗАДАЧИ.items():
    print(f"== {имя}", flush=True)
    рез = {"A_навык": [], "B_на_лету": [], "C_программа": {"токены_создания": т["создание"], "прогоны": []}}
    # C: 50 исполнений без модели
    for з in т["заказы"]:
        t0 = time.time()
        try: ок = т["совпало"](исполнить(т["программа"], т["вход"](з)), т["эталон"](з))
        except Exception: ок = False
        рез["C_программа"]["прогоны"].append({"id": з["id"], "верно": ок, "сек": round(time.time() - t0, 4)})
    print(f"  C: верных {sum(p['верно'] for p in рез['C_программа']['прогоны'])}/{N}", flush=True)
    # A: навык
    for i, з in enumerate(т["заказы"], 1):
        текст, вх, вых, сек = вызов(т["правила"] + "\n\nЗаказ:\n" + json.dumps(т["вход"](з), ensure_ascii=False) + "\n\nОтветь одним JSON-объектом без пояснений.", 600)
        ответ = разобрать_json(текст); ок = т["совпало"](ответ, т["эталон"](з)) if ответ else False
        рез["A_навык"].append({"id": з["id"], "вход": вх, "выход": вых, "сек": round(сек, 1), "верно": ок})
        if i % 10 == 0: print(f"  A {i}/{N}: верных {sum(p['верно'] for p in рез['A_навык'])}", flush=True)
    # B: код на лету
    for i, з in enumerate(т["заказы"], 1):
        текст, вх, вых, сек = вызов(т["правила"] + "\n\nЗаказ:\n" + json.dumps(т["вход"](з), ensure_ascii=False) +
            "\n\nНапиши функцию на Python `def решить(заказ: dict) -> dict`, которая считает результат по этим правилам; она будет вызвана с этим заказом. Только код, без пояснений.", 1500)
        код = снять_ограду(текст); t1 = time.time()
        try: ок = т["совпало"](исполнить(код, т["вход"](з)), т["эталон"](з)); ошибка = None
        except Exception as e: ок = False; ошибка = repr(e)[:120]
        рез["B_на_лету"].append({"id": з["id"], "вход": вх, "выход": вых, "сек": round(сек + time.time() - t1, 1), "верно": ок, "ошибка": ошибка})
        if i % 10 == 0: print(f"  B {i}/{N}: верных {sum(p['верно'] for p in рез['B_на_лету'])}", flush=True)
    итог["задачи"][имя] = рез
    json.dump(итог, open(f"{ЗДЕСЬ}/results_sposoby_{МЕТКА}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\n== СВОДКА (на прогон, среднее)")
for имя, рез in итог["задачи"].items():
    for спос in ("A_навык", "B_на_лету"):
        p = рез[спос]; n = len(p)
        print(f"{имя} {спос}: вход {sum(x['вход'] for x in p)/n:.0f}, выход {sum(x['выход'] for x in p)/n:.0f}, сек {sum(x['сек'] for x in p)/n:.1f}, верных {sum(x['верно'] for x in p)}/{n}")
    c = рез["C_программа"]
    print(f"{имя} C_программа: создание {c['токены_создания']} токенов один раз, исполнение {sum(x['сек'] for x in c['прогоны'])/N*1000:.2f} мс/прогон, верных {sum(x['верно'] for x in c['прогоны'])}/{N}")
