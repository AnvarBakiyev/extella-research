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

## 20 October 2026: the same measurement on Claude Sonnet 5.5 and Opus 5.5, plus a task language

Same 100 orders, same rules, same reference. The models were called through an Extella agent with no tools and a four-line system prompt; token counts are Anthropic's `usage` numbers (each call carries the ~300-token system prompt, which the Qwen run did not have).

| | Qwen3.5 9B (27 Sep) | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| Skill: correct of 100 | 28 | 100 | 100 |
| Skill: tokens per run | 329 | 1061 | 1063 |
| Python expert: tokens to create | 403 | 1123 | 1161 |
| Task-language expert (`zakaz`): tokens to create | – | 1393 | 1393 |
| Break-even | the second run | the second run | the second run |

The third variant asks the model to write the program in a small task language, `zakaz`, whose grammar (642 characters) is given in the prompt; a human-written 95-line handler runs it. Both models wrote the same three-line program on the first attempt, 0 errors. The program is shorter (3 lines against 20–25, output 81 tokens against 207–245), but the grammar in the prompt costs more than the short program saves, so creation is more expensive than Python on this three-rule task. What the task language does give here is a boundary: a `zakaz` program cannot touch files, the network or arbitrary code, because the language has none of that.

On a strong model the accuracy argument for saved programs disappears (100 of 100 either way); the token argument stays and does not depend on the model: one write costs about one run, after that the saving equals the number of runs. Qwen and Claude token counts are not directly comparable (different tokenizers, the system prompt); break-even is the comparable number. Report: `otchet-claude.md` (in Russian). Files: `zamer_claude.py`, `zamer_lang.py`, `results_claude_{sonnet,opus}.json`, `results_lang_{sonnet,opus}.json`, `expert_code_claude_{sonnet,opus}.py`, logs.

### Longer rules: 6 and 12 rules (same day)

`zamer_long.py`: the same order task with 6 or 12 rules (discount by client category, routing, shortage, delivery, controlled goods, priority, total, prepayment), a human-written reference, 100 generated orders. The task language `zakaz2` adds lists, `in`, `count`, `max`, `any`, `round`; its handler is 130 lines. Tokens to create (input + output), lines, errors on the first attempt:

| Model, rules | Python | `zakaz2` | Difference |
|---|---|---|---|
| Sonnet, 6 | 1820, 21 lines, 0 | 2369, 7 lines, 0 | +549 |
| Sonnet, 12 | 2737, 49 lines, 0 | 3141, 13 lines, 0 | +404 |
| Opus, 6 | 2145, 29 lines, 0 | 2372, 7 lines, 0 | +227 |
| Opus, 12 | 3045, 52 lines, 0 | 3137, 13 lines, 0 | +92 |

The grammar (~700 input tokens) pays back slowly: Python output grows about three times faster than task-language output, so the gap closes with more rules (break-even extrapolated at 15–25 rules; not measured). The program is 3.5–4× shorter at the same 0 errors. First-attempt accuracy does not diverge up to 12 rules on these models. Report: `otchet-long.md` (in Russian); raw: `results_long_{sonnet,opus}_{6,12}.json`, logs.

### Accuracy: checkability of corrupted programs, and first-attempt correctness as rules grow (same day)

**A. Corrupted programs** (`zamer_mutacii.py`). Every single-point corruption of the correct 12-rule programs (delete a line, flip a comparison, change a constant, swap a string, swap an identifier) and who catches it first:

| Program | Corrupted versions | Caught before running | Caught by the 100-order test | Silent |
|---|---|---|---|---|
| `zakaz2`, Sonnet (13 lines) | 96 | 58 (60 %) | 38 | 0 |
| Python, Sonnet (49 lines) | 186 | 70 (38 %) | 113 | 3 |
| `zakaz2`, Opus (13 lines) | 97 | 59 (61 %) | 38 | 0 |
| Python, Opus (52 lines) | 218 | 92 (42 %) | 121 | 5 |

"Before running" is the handler's static check for `zakaz2` (parse, all fields set, names defined, field types, closed value sets declared by a human) and compile + pyflakes for Python; Python has no type or closed-set check. Flipped comparisons and changed constants are caught only by the test in both languages. Silent Python versions are dead defensive code.

**B. First-attempt correctness as rules grow** (`zamer_scale.py`, generated rules with an automatic reference, 3 runs per cell, errors of 100):

| Model | Rules | Python | `zakaz2` |
|---|---|---|---|
| Sonnet 5.5 | 12 / 24 / 48 | all 0 | all 0 |
| Haiku 5.5 | 12 / 24 / 48 | all 0 | all 0 except one run at 24: a line of prose before the program, refused at parse |
| Qwen3.5 9B | 12 | 0, 0, 100 | 0, 0, 100 |
| Qwen3.5 9B | 24 | 52, 0, 24 | 100, 100, 100 |
| Qwen3.5 9B | 48 | 0, 100, 100 | 100, 100, 100 |

On strong models there is no difference up to 48 rules. On the 9B model the task language lowers the share of accepted first attempts (0 of 6 at 24–48 rules against 3 of 6 for Python), but every task-language failure is a refusal before running with an exact reason, while two Python failures ran and returned wrong answers on 52 and 24 of 100 orders. One repair attempt with the reason (`zamer_scale_repair.py`): Haiku 1 of 1, Qwen Python 2 of 5, Qwen `zakaz2` 1 of 7; the grammar in the prompt carried no example program, which is a limitation of this setup. Tokens to create stay lower for Python up to 48 rules on these one-line rules. Report: `otchet-tochnost.md` (in Russian).
