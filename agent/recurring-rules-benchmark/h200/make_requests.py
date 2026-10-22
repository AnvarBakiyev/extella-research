#!/usr/bin/env python3
"""Собирает requests.json для bench.py: те же промпты способов A и B на 50 заказах zakaz3 и zakaz12."""
import json, os, sys
ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__)); КОРЕНЬ = os.path.dirname(ЗДЕСЬ)
sys.argv = ["zamer_sposoby.py", "sonnet"]
_g = {"__file__": f"{ЗДЕСЬ}/zamer_sposoby.py"}; exec(open(f"{КОРЕНЬ}/zamer_sposoby.py", encoding="utf-8").read().split("итог = {")[0], _g)
out = []
for имя, т in _g["ЗАДАЧИ"].items():
    for з in т["заказы"]:
        вход = json.dumps(т["вход"](з), ensure_ascii=False)
        out.append({"способ": "A", "задача": имя, "max_out": 600, "промпт": т["правила"] + "\n\nЗаказ:\n" + вход + "\n\nОтветь одним JSON-объектом без пояснений."})
        out.append({"способ": "B", "задача": имя, "max_out": 1500, "промпт": т["правила"] + "\n\nЗаказ:\n" + вход +
                    "\n\nНапиши функцию на Python `def решить(заказ: dict) -> dict`, которая считает результат по этим правилам; она будет вызвана с этим заказом. Только код, без пояснений."})
json.dump(out, open(f"{ЗДЕСЬ}/requests.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "запросов →", f"{ЗДЕСЬ}/requests.json")
