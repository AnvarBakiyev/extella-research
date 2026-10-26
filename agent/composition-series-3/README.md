# Composition: what is lost without Extella when a program is assembled from parts (26 Oct 2026)

Series 3 after [`../gsm8k-infrastructure-vs-assembly/`](../gsm8k-infrastructure-vs-assembly/). Extella is treated as infrastructure for storing, composing, executing and distributing programs. This series tests composition:

- add a language;
- build a language on top of another;
- chain programs in three languages;
- replace a part used by 100 programs;
- run the same composite program on three machines.

Both sides use the same language code (`langs/`). Only the way parts are connected, replaced and delivered differs. The protocol, with two dated amendments, was written before the runs: `PROTOKOL.md`, in Russian.

The task is an orders report. 2000 synthetic orders (seed 20261027) go through a chain of three languages:

1. `readsql`: SELECT only, the database is opened read-only;
2. `steps`: the plan executor from series 2, with a per-row mode;
3. `card`: HTML report cards.

A fourth language, `rulebook`, holds discount rules as a table. Its handler turns the table into a `steps` plan and hands it to the `steps` handler. The reference report is computed directly, without any of the languages.

## Results

| Scenario | Extella | Assembled in Python | Prediction | Outcome |
|---|---|---|---|---|
| K1. New language `card` | one registrar call per device, 7–11 s; 0 logins to the machine | a module, one line of dispatch, a file copy to each machine | Extella cheaper | partly: fewer actions on machines, same code |
| K1. The model (Qwen 9B, local) writes `card` programs | run 1: 0 of 5 pass; run 2, with an example in the description: 5 of 5 pass (4 of 5 do what was asked) | same programs, same outcome | — | equal |
| K2. `rulebook` on top of `steps` | 20 of 20 match the reference; after replacing only `steps` with v2 (a 30% rate limit): 13 match, 7 refused by the new law, `rulebook` untouched; 8 lines of glue through an undocumented internal call | same 20, 13 and 7; 1 line, a plain import | Extella cheaper if the path is official | refuted for the path we used (internal `run_container`): Python is simpler; documented paths were not tried |
| K3. Chain of three languages | matches the reference, 8.7–11.3 s; a broken link is reported with its number and language | matches, 0.18 s; same error | equal code, Python faster | confirmed |
| K4. Replace `steps` under 100 composite programs, checked first | broken version stopped on the first machine (39 unacceptable changes); correct one installed on 2 machines with one command, 76 s; 24 lines | same 39; one command, 72 s; 10 lines | Extella cheaper | refuted: one command on both sides, actions do not grow with the number of programs; less code in Python |
| K5. Same program on three machines | matches on all three, 8–10 s; a new machine needs 2 platform calls and no login | matches on two, 0.2–1.2 s; a new machine needs ~7 ssh actions; the third machine has no shell access, so the stack cannot be installed there | Extella cheaper | confirmed |

## What it shows

- **Composition works on the pla- **We composed through an internal path and did not try the documented ones.** In this series a handler called another handler through the listener's internal `run_container` function. A review after the series (`DIAGNOSTIKA-kompozicii.md`, Russian) found documented paths: an orchestrator expert (`cspl=nohup`) calling other experts over REST with the account key read from the KV store, pipelines in the API, and the SDK's public `Disnet.run`. Whether they are easier than plain Python was not measured.rough the platform, because it does not receive an account key.
- **The platform's advantage is delivery and execution on machines.** A new machine is prepared with two platform calls. A machine with no shell access is reached through its listener.
- **On the path we used, the platform is not cheaper in code.** It is 10–50× slower per run.

Findings along the way:

- The series-2 `steps` executor crashes on `max()` with one argument instead of refusing.
- A language description without an example made the model write every program on one line.
- The `card` handler's error message for that case is misleading.

## Limits

- One author built both sides.
- One synthetic task.
- Python ran on two machines, not three.
- Windows was not tested.
- Account and device identifiers, the server address and local paths are placeholders.
- `ext.py` comes from the series-2 folder next to this one.
- The SQLite database is not included: `data/make_orders.py` rebuilds it, and its content hash is in the journals.

## Files

| Path | What it is |
|---|---|
| `PROTOKOL.md`, `OTCHET.md` | protocol and report (Russian) |
| `DIAGNOSTIKA-kompozicii.md` | after the series: which composition mechanisms Extella documents and which we used (Russian) |
| `zhurnal-*.md` | time-stamped work logs of both sides |
| `langs/` | shared language code, `steps` v2 and a broken v2 |
| `data/` | order generator, references, programs, 20 rule sets |
| `extella-side/`, `python-side/` | the two builds |
| `k4/` | 100 programs and the shared pre-replacement check |
| `k1_model*.py`, `results_*.json` | model-written programs and raw results |

---

**Коротко по-русски.** Композиция на Extella работает и даёт тот же результат, что тот же код без платформы. Но в серии мы собирали её через внутренний вызов слушателя, а документированные пути не проверили: оркестратор nohup с ключом из KV, пайплайны и Disnet.run. По коду она не дешевле, а на вызов медленнее. Выигрыш платформы в доставке: новую машину готовят двумя вызовами, без входа на неё, а машину без shell-доступа платформа достаёт через слушателя.
