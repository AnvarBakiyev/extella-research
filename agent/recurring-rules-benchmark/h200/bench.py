#!/usr/bin/env python3
"""Пропускная способность vLLM на H200 на запросах бенчмарка (способы A и B, задачи zakaz3 и zakaz12).
Запуск на поде рядом с vLLM:  python3 bench.py http://localhost:8000 <модель> requests.json
requests.json готовится на Mac скриптом make_requests.py (те же промпты, что в zamer_sposoby.py).
Пишет results_h200.json: по каждой точке (способ, задача, параллелизм) токены вход/выход, токены/с, p50/p95.
"""
import json, sys, time, threading, urllib.request, statistics

БАЗА, МОДЕЛЬ, ФАЙЛ = sys.argv[1], sys.argv[2], sys.argv[3]
ЗАПРОСЫ = json.load(open(ФАЙЛ, encoding="utf-8"))   # [{"способ","задача","промпт","max_out"}]
ПАРАЛЛЕЛИЗМ = [1, 8, 32, 64]

def один(промпт, max_out):
    тело = {"model": МОДЕЛЬ, "messages": [{"role": "user", "content": промпт}], "max_tokens": max_out, "temperature": 0}
    req = urllib.request.Request(f"{БАЗА}/v1/chat/completions", data=json.dumps(тело).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time(); r = json.load(urllib.request.urlopen(req, timeout=600)); dt = time.time() - t0
    u = r.get("usage", {}); return u.get("prompt_tokens", 0), u.get("completion_tokens", 0), dt

итог = []
группы = {}
for з in ЗАПРОСЫ: группы.setdefault((з["способ"], з["задача"]), []).append(з)
for (способ, задача), список in группы.items():
    for p in ПАРАЛЛЕЛИЗМ:
        вх = []; вых = []; задержки = []; lock = threading.Lock()
        очередь = list(список)
        def worker():
            while True:
                with lock:
                    if not очередь: return
                    з = очередь.pop()
                a, b, dt = один(з["промпт"], з["max_out"])
                with lock: вх.append(a); вых.append(b); задержки.append(dt)
        t0 = time.time()
        потоки = [threading.Thread(target=worker) for _ in range(p)]
        for t in потоки: t.start()
        for t in потоки: t.join()
        стена = time.time() - t0
        row = {"способ": способ, "задача": задача, "параллелизм": p, "запросов": len(список), "стена_с": round(стена, 2),
               "вход_всего": sum(вх), "выход_всего": sum(вых), "вход_ток_с": round(sum(вх) / стена, 1), "выход_ток_с": round(sum(вых) / стена, 1),
               "p50_с": round(statistics.median(задержки), 2), "p95_с": round(sorted(задержки)[int(len(задержки) * 0.95) - 1], 2),
               "gpu_сек_на_прогон": round(стена / len(список), 3)}
        итог.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
        json.dump({"модель": МОДЕЛЬ, "точки": итог}, open("results_h200.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
