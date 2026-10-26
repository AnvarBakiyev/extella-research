"""Python-сторона серии 3: те же языки как модули, цепочка — вызов функций по имени языка."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "langs"))
import readsql, steps, card, rulebook, chain

def run_lang(lang, code, params):
    if lang == "k3_readsql": return readsql.run_sql(code, params.get("db") or "~/kompoziciya/orders.db")
    if lang == "k3_steps": return steps.steps(code=code, **params)
    if lang == "k3_card": return card.render(code, params.get("rows") or [])
    if lang == "k3_rulebook": return rulebook.run(code, params.get("rows") or [], lambda p, r, o: steps.run_map(p, r, o))
    if lang == "k3_chain": return chain.run(code, params, run_lang)
    return {"status": "refused", "reason": f"unknown language {lang}"}

if __name__ == "__main__":
    print(json.dumps(run_lang(sys.argv[1], open(sys.argv[2]).read(), json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))[:400])
