# Skill vs expert: when does a saved program pay for itself?

27 September 2026, one measurement. A small local model (qwen3.5:9b through Ollama, temperature 0) handled the same task two ways: as a **skill** (the rules go to the model on every run) and as an **expert** (the model writes a Python function once; the function then runs with no model call).

| | Skill | Expert |
|---|---|---|
| Tokens to create | – | 403 (one attempt, 17 s) |
| Tokens per run | 328.7 | 0 |
| Correct of 100 | 28 | 100 |
| Break-even | | the second run (403 ÷ 328.7 = 1.23) |

What the numbers do not mean: 28 of 100 is the accuracy of a 9B model on this task, not a property of skills; the skill here is a short one (288 input tokens), the most favourable case for the skill side; one task, one model, one day. The expert was created locally because the platform agent was unavailable that day; the run through Extella on a Mac took 7–9 s per call. Details and caveats: `otchet.md` (report, in Russian), `metodika.md` (method, written before the run).

Files: `zamer.py` (the measurement), `dataset.json` (100 orders with reference answers), `expert_code.py` (the function the model wrote), `results.json` (raw results), `zamer.log`.

The orders are synthetic. After the run the client names in `dataset.json` were replaced with neutral labels (`Клиент 01` … `Клиент 10`) and the currency word in the method was neutralised; nothing else was changed. `results.json` never contained the names.
