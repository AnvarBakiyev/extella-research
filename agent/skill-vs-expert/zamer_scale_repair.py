#!/usr/bin/env python3
"""Вторая попытка для провалившихся первых (20.10.2026): что даёт одно исправление.

Берёт из results_scale_<модель>_<N>.json прогоны с ошибками первой попытки и делает ровно один
повторный вызов с сообщением о причине: для zakaz2 — текст отказа обработчика (разбор) или первый
расходящийся заказ; для Python — текст исключения/ошибки компиляции или первый расходящийся заказ.
Пишет results_scale_repair_<модель>_<N>.json.
Запуск: python3 zamer_scale_repair.py <sonnet|haiku|qwen> <12|24|48>
"""
import json, sys, re
_m, _n = sys.argv[1], sys.argv[2]
sys.argv = ["zamer_scale.py", _m, _n, "0"]
exec(open("<this folder>/zamer_scale.py", encoding="utf-8").read().split("if __name__")[0])

def причина(вариант, код):
    if вариант == "zakaz2":
        try: программа = разобрать_программу(код)
        except Exception as e: return f"Обработчик не принял программу: {e}"
        for з, эт in zip(ЗАКАЗЫ, ЭТАЛОНЫ):
            окр = [dict(з)]
            try:
                for имя, дерево in программа: окр[0][имя] = вычислить(дерево, окр)
                r = {k: окр[0].get(k) for k in ПОЛЯ}
                diff = [(k, r.get(k), эт[k]) for k in ПОЛЯ if r.get(k) != эт[k]]
                if diff: return f"Заказ {з['id']}: поле {diff[0][0]} = {diff[0][1]!r}, ожидалось {diff[0][2]!r}"
            except Exception as e: return f"Заказ {з['id']}: ошибка выполнения {e}"
    else:
        пр = {}
        try: exec(код, пр); f = пр["решить"]
        except Exception as e: return f"Код не выполняется: {e!r}"
        for з, эт in zip(ЗАКАЗЫ, ЭТАЛОНЫ):
            try:
                r = f(json.loads(json.dumps(з))); diff = [(k, r.get(k), эт[k]) for k in ПОЛЯ if r.get(k) != эт[k]]
                if diff: return f"Заказ {з['id']}: поле {diff[0][0]} = {diff[0][1]!r}, ожидалось {diff[0][2]!r}"
            except Exception as e: return f"Заказ {з['id']}: исключение {e!r}"
    return "неизвестно"

d = json.load(open(f"{ПАПКА}/results_scale_{МОДЕЛЬ}_{N}.json", encoding="utf-8"))
итог = {"модель": МОДЕЛЬ, "правил": N, "исправления": []}
for p in d["прогоны"]:
    if p["ошибок_из_100"] == 0: continue
    базовый = ПРОМПТ_P if p["вариант"] == "python" else ПРОМПТ_Z
    прич = причина(p["вариант"], p["код"])
    промпт = базовый + "\n\nТвоя предыдущая программа:\n" + p["код"] + "\n\nОна не принята. " + прич + ". Исправь и верни только программу."
    текст, вх, вых, сек = вызов(промпт)
    код = снять_ограду(текст); n = (ошибок_p if p["вариант"] == "python" else ошибок_z)(код)
    итог["исправления"].append({"прогон": p["прогон"], "вариант": p["вариант"], "причина": прич, "ошибок_было": p["ошибок_из_100"],
                                "ошибок_стало": n, "вход": вх, "выход": вых, "сек": round(сек, 1), "код": код})
    print(f"  {МОДЕЛЬ} {N} прогон {p['прогон']} {p['вариант']}: было {p['ошибок_из_100']} → стало {n} ({сек:.0f} c) | {прич[:80]}", flush=True)
    json.dump(итог, open(f"{ПАПКА}/results_scale_repair_{МОДЕЛЬ}_{N}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("== ИТОГ repair", МОДЕЛЬ, N, [(i["вариант"], i["ошибок_было"], i["ошибок_стало"]) for i in итог["исправления"]])
