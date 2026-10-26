"""GPT через Codex CLI (подписка): решить задачу GSM8K рассуждением. Режим G: подвыборка 100 из 701–1319.
Режим H: задачи без согласия из results_v33_test_701_1319.json. Токены из события turn.completed."""
import json, os, random, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
rows = open(os.path.join(HERE, "..", "data", "gsm8k_test.jsonl")).read().splitlines()
def solve(q):
    t0 = time.time()
    p = subprocess.run(["codex", "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "-c", 'plugins."extella-agent-builder@server-1".enabled=false',
                        q + "\n\nSolve step by step. Do not use any tools. On the last line write only the final answer as a number."],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
    ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
    txt = [e["item"]["text"] for e in ev if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message"]
    use = [e.get("usage", {}) for e in ev if e.get("type") == "turn.completed"]
    m = re.findall(r"-?\d[\d,]*\.?\d*", txt[-1] if txt else "")
    ans = float(m[-1].replace(",", "").rstrip(".")) if m else None
    return ans, (use[-1] if use else {}), round(time.time() - t0, 1)
mode = sys.argv[1]
if mode == "G":
    nums = sorted(random.Random(20261026).sample(range(701, 1320), 100))
else:
    res = json.load(open(os.path.join(HERE, "..", "results_v33_test_701_1319.json")))
    nums = [int(x["id"][4:]) for x in res if not x["согласие"]]
outp = os.path.join(HERE, f"results_gpt_{mode}.json")
out = json.load(open(outp)) if os.path.exists(outp) else []
done = {x["task"] for x in out}
for i in nums:
    if i in done: continue
    d = json.loads(rows[i - 1]); et = float(d["answer"].split("####")[-1].strip().replace(",", ""))
    ans, use, sec = solve(d["question"])
    out.append({"task": i, "answer": ans, "etalon": et, "correct": ans is not None and abs(ans - et) < 1e-6, "usage": use, "sec": sec})
    json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)
    print(mode, len(out), "/", len(nums), "верно" if out[-1]["correct"] else "НЕВЕРНО", sec, "с", flush=True)
print("ИТОГ", mode, "верных", sum(x["correct"] for x in out), "из", len(out))
