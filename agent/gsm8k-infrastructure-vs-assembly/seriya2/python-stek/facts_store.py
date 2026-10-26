"""Общее хранилище фактов: Redis-хэш gsm:facts (регулярное выражение -> факт) на сервере."""
import json, os, sys
from redis import Redis
URL = os.environ.get("FACTS_REDIS", "redis://127.0.0.1:16379")

def load_facts():
    h = Redis.from_url(URL, decode_responses=True).hgetall("gsm:facts")
    return sorted(h.items())

def seed():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import ustroystvo33 as C
    Redis.from_url(URL).hset("gsm:facts", mapping={r: f for r, _, f in C.КОНЦЕПТЫ})

if __name__ == "__main__":
    if sys.argv[1] == "seed": seed()
    elif sys.argv[1] == "add": Redis.from_url(URL).hset("gsm:facts", sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "agent":
        f = load_facts(); print(sys.argv[2], len(f), any("score" in x for _, x in f))
