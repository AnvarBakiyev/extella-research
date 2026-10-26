# What do we lose without Extella? GSM8K, the same logic on the platform and on a hand-built stack (25–26 Oct 2026)

The question: keep the same model, the same algorithm, the same functions and the same knowledge, remove Extella. What is lost?

Extella is treated here as infrastructure for storing, composing, executing and distributing programs and knowledge. It is not treated as a language competing with Python: Python is itself one of the languages Extella runs. So the comparison is "the platform" against "the same thing assembled from parts". The parts are FastAPI, the MCP Python SDK, Redis and RQ, an ssh tunnel and scikit-learn.

Model: Qwen3.5 9B in local Ollama, temperature 0. The solver logic is the same on both sides. It runs two independent paths, step-by-step reasoning and a plan, and the plan is computed by an exact executor with checks. When the paths disagree, the executor's feedback goes back to the model and an arbiter decides. GPT was called through the Codex CLI subscription. The protocol, including six dated amendments, was written before the runs: `PROTOKOL-2-chto-teryaem-bez-extella.md`, in Russian.

## Results

**1. Accuracy: nothing is lost and nothing is gained.** The same plans ran on the platform's executor on two machines and in plain Python. All 153 plans out of 153 gave the same outcome, including 43 refusals with the same reason. Platform errors: 0. Running one plan through the platform took a median of 10.8 s on a server and 12.3 s on a laptop.

**2. Two paths and a check let a small model hand off only the doubtful quarter.** 619 GSM8K test problems (701–1319), not opened before the run:

| Variant | Correct of 619 | Large-model calls |
|---|---|---|
| Qwen 9B alone, step-by-step | 581 (93.9%) | 0 |
| 9B with the plan executor, the check and the arbiter | 579 (93.5%) | 0 |
| Hybrid: agreed problems stay with 9B, disagreements go to GPT | 601 (97.1%) | 142 (22.9%) |

The two paths agreed on 477 problems (77.1%), and 465 of those answers were correct (97.5%). On a pre-registered subsample of 100 problems, GPT answering every problem got 96. The hybrid also got 96 with 22 GPT calls. This is a property of the method, not of the platform. The executor alone added no accuracy on GSM8K: the 9B model's errors here are in reading the problem, not in arithmetic.

**3. Operations: where the platform saves work and where it costs.** Both sides were built by the same author, Claude, against acceptance checks written in advance. Lines are counted without blank lines and comments; the solver logic is given and not counted.

| Scenario | Hand-built stack | Extella | Time per action |
|---|---|---|---|
| S1. One solver called from a chat agent, from Codex over MCP and over HTTP | 35 lines, an HTTP service and an MCP server | 4-line wrapper; no new service | solve: 119 s over REST, 197 s through the chat agent |
| S2. A new rule on two machines, checked on 40 saved plans before replacing the old one | 9 lines + 16 shared; a worker on each machine, Redis, a tunnel | 31 lines + 16 shared; nothing to run | 2 s vs 25 s |
| S3. Execution on a machine with no inbound ports | 19 lines; system Redis on a server, an ssh tunnel, a worker | 0 lines; the listener was already installed | 0.21 s vs 7–12 s |
| S4. Find and apply a reusable operation (8 operations, 20 problems) | found 12, solved 12 | found 11, solved 11 | search: 0.002 s vs 2.3 s |
| S5. Three agents share 17 facts; add an 18th | one Redis write, all three see it | one global concept; reading agents ask with `global=true` (visible to the agents of the profile, per the official guide) | |

The broken rule changed 7 of the 40 outcomes. Both sides stopped it on the first machine and installed the correct one on both machines. Each side needed 7 manual fixes. On the Extella side all 7 came from platform rules the documentation does not state, for example that the first function in an expert's code is the one called.

What the scenarios show:

- **The platform saves work** on reaching many consumers and on executing on machines without inbound ports: almost no code and no services to keep running.
- **It costs speed**, 10–100× per call.
- **The hand-built stack is simpler** for a checked handler replacement (S2). Shared knowledge (S5) is equal: one write on both sides.
- **Composition was barely tested here.** It is the subject of a next series.

## What can and cannot be said

- **Can:**
  - "The same logic, unchanged, is available from chat, API and Codex and runs on your machines with no inbound ports open."
  - "On the platform a program runs exactly as it does without it (153 of 153)."
  - "On GSM8K a local 9B model handles three quarters of the problems by itself, and the hybrid matches the large model's accuracy with 4.5× fewer large-model calls."
- **Cannot:**
  - "Extella makes the model more accurate."
  - "Extella is faster."
  - "Extella is simpler in every case."

## Limits

- One author built both sides.
- The scenarios are small: one problem in S1, 40 plans in S2, 20 problems in S4.
- GPT on every problem was run on a subsample of 100, not on all 619.
- Money for GPT calls is not computed, because the calls went through a subscription. The median call used 20k input tokens, mostly the Codex system prompt, and 120 output tokens.
- About 2 in 300 GSM8K reference answers are wrong, so 100% is not reachable.
- Windows was not tested.
- Part 5 of the protocol, switching mechanisms off one at a time, was cancelled before it started. It compared two languages inside the platform and does not answer the question above.

## Files

The layout is the one the runs used, so the scripts' relative paths work as they are.

| Path | What it is |
|---|---|
| `PROTOKOL-2-chto-teryaem-bez-extella.md` | protocol with six dated amendments (Russian) |
| `ustroystvo33.py` | the solver, frozen (SHA-256 starts d137a69a) |
| `results_v33_test_701_1319.json` | part 1: 619 problems |
| `seriya2/OTCHET.md`, `seriya2/OPIS-inzhenernoy-stoimosti.md` | report and engineering-cost inventory (Russian) |
| `seriya2/zhurnal-python-stek.md`, `seriya2/zhurnal-extella-stek.md` | time-stamped work logs of both sides |
| `seriya2/steps_handler.py`, `seriya2/ustroystvo_d.py`, `seriya2/ext.py` | the plan language executor, the solver on Extella, a thin REST client |
| `seriya2/python-stek/`, `seriya2/extella-stek/` | the hand-built stack and the Extella build for scenarios S1–S5 |
| `seriya2/s2/`, `seriya2/s4/`, `seriya2/s4_tasks.txt` | rule-replacement check and reusable-operation data |
| `seriya2/gpt.py`, `seriya2/results_gpt_*.json` | GPT through the Codex CLI: 100 problems and the 142 disagreements |
| `seriya2/results_D_*.json` | the platform runs (part 2) |

To reproduce:

1. Download `test.jsonl` from [openai/grade-school-math](https://github.com/openai/grade-school-math) (MIT) and put it at `data/gsm8k_test.jsonl` in this folder.
2. Install Ollama with `qwen3.5:9b`.
3. Install the Codex CLI for the GPT runs.
4. Install Extella and sign in for the platform runs. Scripts read the token from `~/.extella/`. Agent and device identifiers are placeholders such as `<agent-id>`.

---

**Коротко по-русски.** Та же логика на платформе Extella и на стеке, собранном руками. Точность одинаковая: 153 плана из 153 дали тот же исход. Платформа экономит код и службы при подключении потребителей и при исполнении на машинах без входящих портов, но медленнее на вызов в 10–100 раз. Гибрид «9B решает сама, спорное отдаёт GPT» на 619 нетронутых задачах даёт 97,1 % и вызывает GPT в 22,9 % случаев. На подвыборке из 100 задач у гибрида та же точность, что у GPT на всех задачах. Подробности в `OTCHET.md`.
