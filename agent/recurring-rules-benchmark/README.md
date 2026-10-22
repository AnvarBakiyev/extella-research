# Recurring-rules benchmark: prompt per run, code on the fly, or a saved program (22 Oct 2026)

Two order-approval tasks (3 rules and 12 rules), 50 orders each with a reference answer, four ways to do the job:

- **A. Prompt per run** (a "skill"): rules and the order go to the model every time.
- **B. Code on the fly**: the model writes a function for this order, it runs locally, the code is thrown away (how Code Mode / MCP code execution work without saving).
- **C. Saved program**: one model call to write the function, checked against the reference, then runs with no model.
- **D. Local 9B writes the program**: as C, but the author is Qwen3.5 9B on a laptop (Ollama).

Correct of 50, tokens per run (input / output):

| Task | Method | Qwen3.5 9B, local | GPT via Codex subscription | Claude Sonnet 5.5 (20 Oct) |
|---|---|---|---|---|
| 3 rules | A prompt per run | **14/50**, 287 / 39 | 50/50, – / 34 | 50/50, 998 / 54 |
| 3 rules | B code on the fly | 50/50, 316 / 155 | 50/50, – / 111 | not measured |
| 3 rules | C saved program | 50/50, 0 tokens, 0.1 ms | 50/50 | 50/50, written once for 1123 |
| 3 rules | D 9B writes it | 1 attempt, 396 tokens, 18 s → 50/50 | | |
| 12 rules | A prompt per run | **4/50**, 794 / 176 | 50/50, – / 169 | not measured |
| 12 rules | B code on the fly | 50/50, 823 / 768 | 49/50, – / 595 | not measured |
| 12 rules | C saved program | 50/50, 0 tokens, 4 ms | 50/50 | 50/50, written once for 2737 |
| 12 rules | D 9B writes it | 1 attempt, 1513 tokens, 40 s → 50/50 | | |

GPT input tokens are omitted: Codex adds its own ~20k-token system prompt to every call. Sonnet cells come from the 20 Oct measurement in `../skill-vs-expert/`; no new paid calls were made.

What it shows: a 9B model answers the rules badly (14/50, 4/50) but writes correct code for the same rules (50/50), so on a laptop the model should write the program once, not answer each time. Code on the fly costs 3–4× the output of a prompt per run and adds no accuracy on a strong model; a saved program costs about one run to write and nothing after. Money at Anthropic list prices and an order-of-magnitude H200 estimate from a published third-party throughput figure are in `OTCHET.md` (Russian), with their limits. Protocol written before the runs: `PROTOKOL.md`.
