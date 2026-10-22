#!/usr/bin/env python3
"""Способ D: локальная модель Qwen3.5 9B (Ollama на Mac) пишет программу для zakaz3 и zakaz12,
до 3 попыток с сообщением об ошибке, затем 50 исполнений без модели. Протокол: PROTOKOL.md.
Запуск: python3 zamer_lokalno.py  → results_qwen9b.json
"""
import json, re, time, urllib.request, sys, os
ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["zamer_sposoby.py", "sonnet"]
_g = {"__file__": f"{ЗДЕСЬ}/zamer_sposoby.py"}; exec(open(f"{ЗДЕСЬ}/zamer_sposoby.py", encoding="utf-8").read().split("итог = {")[0], _g)
ЗАДАЧИ, снять_ограду, исполнить, N = _g["ЗАДАЧИ"], _g["снять_ограду"], _g["исполнить"], _g["N"]

def вызов_qwen(промпт, max_out=2500):
    t0 = time.time()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({"model": "qwen3.5:9b", "prompt": промпт, "stream": False,
        "think": False, "options": {"temperature": 0, "num_predict": max_out, "num_ctx": 8192}}).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    return r.get("response", ""), r.get("prompt_eval_count", 0), r.get("eval_count", 0), time.time() - t0

def ошибок(код, т):
    n = 0; первая = None
    for з in т["заказы"]:
        try:
            r = исполнить(код, т["вход"](з))
            if not т["совпало"](r, т["эталон"](з)): n += 1; первая = первая or (з["id"], r, т["эталон"](з))
        except Exception as e:
            n += 1; первая = первая or (з["id"], f"исключение: {e!r}"[:200], т["эталон"](з))
    return n, первая

итог = {"модель": "qwen3.5:9b, Ollama, Mac", "n": N, "задачи": {}}
for имя, т in ЗАДАЧИ.items():
    print(f"== {имя}", flush=True)
    промпт = т["правила"] + "\n\nНапиши функцию на Python с сигнатурой `def решить(заказ: dict) -> dict`, реализующую эти правила и возвращающую объект результата. Только код, без пояснений, без примеров."
    попытки = []; готово = None
    for i in range(1, 4):
        текст, вх, вых, сек = вызов_qwen(промпт); код = снять_ограду(текст)
        n, первая = ошибок(код, т)
        попытки.append({"попытка": i, "вход": вх, "выход": вых, "сек": round(сек, 1), "ошибок_из_50": n, "код": код})
        print(f"  попытка {i}: вход {вх}, выход {вых}, {сек:.0f} c, ошибок {n}/{N}", flush=True)
        if n == 0: готово = код; break
        промпт = (т["правила"] + "\n\nТвой предыдущий код:\n```python\n" + код + "\n```\nОн даёт неверный результат. "
                  f"Пример: заказ {первая[0]} → твой ответ {первая[1]}, ожидалось {первая[2]}. Исправь и верни только код функции `решить`.")
    прогоны = []
    if готово:
        for з in т["заказы"]:
            t0 = time.time(); ок = т["совпало"](исполнить(готово, т["вход"](з)), т["эталон"](з)); прогоны.append({"id": з["id"], "верно": ок, "сек": round(time.time() - t0, 4)})
    итог["задачи"][имя] = {"попытки": попытки, "прошла_эталон": готово is not None, "токены_создания": sum(p["вход"] + p["выход"] for p in попытки),
                           "сек_создания": round(sum(p["сек"] for p in попытки), 1), "прогоны": прогоны}
    json.dump(итог, open(f"{ЗДЕСЬ}/results_qwen9b.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("== ИТОГ", {k: (v["прошла_эталон"], len(v["попытки"]), v["токены_создания"], v["сек_создания"]) for k, v in итог["задачи"].items()})
