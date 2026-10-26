"""S4, часть «найдена ли операция»: попадает ли операция нужного вида в первые 2 по поиску. Обе стороны, одни запросы."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
ops = json.load(open(os.path.join(HERE, "ops.json"))); cat = {o["name"]: o["cat"] for o in ops}
rows = open(os.path.join(HERE, "..", "..", "data", "gsm8k_test.jsonl")).read().splitlines()
tasks = [l.split("\t") for l in open(os.path.join(HERE, "..", "s4_tasks.txt")).read().splitlines() if l and not l.startswith("#")]
side = sys.argv[1]; out = []
if side == "python":
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    vec = TfidfVectorizer(stop_words="english").fit([o["description"] for o in ops])
    D = vec.transform([o["description"] for o in ops])
    def search(q):
        s = cosine_similarity(vec.transform([q]), D)[0]
        return [ops[i]["name"] for i in s.argsort()[::-1][:2]]
else:
    import ext
    def search(q):
        r = ext.call("/expert/search", {"query": q, "limit": 10}).get("experts", [])
        names = [e["name"] for e in r]
        return {"raw_top2": names[:2], "ops_top2": [n for n in names if n in cat][:2]}
for i, want in tasks:
    q = json.loads(rows[int(i) - 1])["question"]; t0 = time.time(); r = search(q); dt = time.time() - t0
    top = r if isinstance(r, list) else r["ops_top2"]
    out.append({"task": int(i), "want": want, "top2": top, "hit": any(cat.get(n) == want for n in top), "sec": round(dt, 3), **({} if isinstance(r, list) else {"raw_top2": r["raw_top2"]})})
json.dump(out, open(os.path.join(HERE, f"retrieval_{side}.json"), "w"), ensure_ascii=False, indent=1)
print(side, "попаданий", sum(o["hit"] for o in out), "из", len(out), "| по видам", {c: f'{sum(o["hit"] for o in out if o["want"]==c)}/{sum(1 for o in out if o["want"]==c)}' for c in ("percent","rate_time","units","each")},
      ("| чужие эксперты в сырых top2: " + str(sum(1 for o in out if any(n not in cat for n in o.get("raw_top2", []))))) if side != "python" else "", "| медиана, с", sorted(o["sec"] for o in out)[10])
