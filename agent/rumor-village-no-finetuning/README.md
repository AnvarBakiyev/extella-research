# Rumor Village without fine-tuning: the rule in the engine

23 November 2026.

**Question.** Manuel García Sanz fine-tuned Gemma 4 E4B so that 100 villagers in his game
[Rumor Village](https://github.com/manuelgscom/rumor-village) stop inventing memories, and
published the frozen test cards. We took the same cards and trained nothing. The villager writes
one line in a tiny per-turn language and a deterministic handler runs it. How far does that get,
and what does it cost?

## The language

One turn is one line. Five moves:

```
greet
tell 1 who amount
ask 1 where
plan 1
silent
```

The model names the slot and never the value. The handler fills values from what the villager
holds, so a made-up memory has nowhere to be written. The handler refuses with the line, the
reason and the moves it would take instead:

```
tell 1 where  -> the villager does not know where for fact [1]; you can ask: ask 1 where
tell 1 who    -> fact [1] has already been told to this listener
ask 1 who     -> the villager knows who for sure, there is nothing to ask
```

An optional second line, `say: ...`, carries the sentence the villager speaks. The handler
refuses it when it holds a name or a number the villager does not have, an event or a place the
villager is not speaking about, or a guess stated as a certainty.

## Results

Three sets of 200 `decide` cards, no overlap between them, each frozen before any model was
called. One checker for every condition. "Accepted" means the handler took the move; "after one
retry" means we handed the refusal back once.

| condition | set | first try | after one retry | made-up memories | rejected actions |
|---|---|---|---|---|---|
| Qwen 3.5 9B through the language | 2 | 154/200 (77.0 %) | 187/200 (93.5 %) | 0 | 0 |
| DeepSeek-V4-Flash, plain call | 2 | 151/200 (75.5 %) | 188/200 (94.0 %) | 0 | 0 |
| DeepSeek-V4-Flash, own Extella agent | 2 | 154/200 (77.0 %) | 194/200 (97.0 %) | 0 | 0 |
| Qwen 3.5 9B, guesses marked | 3 | 149/200 (74.5 %) | 184/200 (92.0 %) | 0 | 0 |
| DeepSeek-V4-Flash, own agent, guesses marked | 3 | **171/200 (85.5 %)** | **196/200 (98.0 %)** | **0** | **0** |

Across the three sets, roughly 1 500 model answers: zero made-up memories, zero rejected actions.

Without the language, the same models writing a free JSON action on the same cards produced 13
made-up memories and 83 rejected actions in 400 answers. Those files are here too
(`zamer_B.json`, `zamer_D.json`).

For reference, the author's model card reports made-up memories going 2.3 % to 0 % after
fine-tuning, and rejected actions going 0.10 % to 0.90 %.

Three more measurements:

- **Swapping the law costs no model calls.** `village_v2.py` is a second law for the same
  language: nothing is told to a rival, nothing after 20:00. Run `smena_zakona.py` over the
  accepted turns and 6 of 171 stop passing, with no model involved.
- **12.5 % of turns need no model.** On 125 of the author's 1000 cards the law leaves exactly
  one legal move.
- **Naturalness 4.2** on the same 1 to 5 scale the author uses, against 4.1 there. Claude Opus 5
  rated 20 lines, which is weak evidence and we say so.

## Predictions written before each run

`measure/OZHIDANIYA.md`, `OZHIDANIYA2.md`, `OZHIDANIYA3.md` hold the thresholds, in Russian, each
written before the models were called. We missed ten of them:

| threshold | result |
|---|---|
| first measure, DeepSeek accepted above 85 % first try | 71 % |
| first measure, above 90 % after retry | 89.5 % |
| first measure, naturalness at least 3.5 | 3.47 |
| second measure, 9B above 85 % first try | 77.0 % |
| second measure, DeepSeek above 95 % first try | 73.0 % |
| second measure, both above 95 % after retry | 93.5 % and 94.0 % |
| second measure, prompt under 256 tokens | 261 on average |
| third measure, 9B above 80 % first try | 74.5 % |
| third measure, 9B above 96 % after retry | 92.0 % |
| third measure, own agent above 98 % after retry | 98.0 %, short by one card |

## Defects we found in our own tooling

Eleven, all found before the numbers went into any result, with every recount done from the
saved model answers rather than by calling the models again. The ones worth naming: "I don't
remember" was counted as a made-up memory; the card index was confused with the engine's fact id
(`f2`), which produced phantom violations on 37 cards; any capitalised word was taken for a name,
so "Hey" and the Spanish "Oye" were refused; the summary counted a card twice when a fix made it
pass in both rounds. The full list is in the results files.

## What you need to repeat this

Without Extella you can run everything local:

```bash
cd data && curl -sSL -o en.jsonl \
  https://raw.githubusercontent.com/manuelgscom/rumor-village/main/training/testset/decision/en.jsonl
cd ../measure
python3 -I regress.py          # the law against 34 hand-written cases
python3 -I zamer3.py A2        # Qwen 3.5 9B through Ollama
python3 -I pereschet3.py       # recount from saved answers, no model calls
python3 -I svodka2.py          # the table
python3 -I smena_zakona.py zamer3_E_n3.json   # swap the law, zero model calls
```

The handler is plain Python with no dependencies. The local conditions reproduce with any model
you can call.

With Extella you also get the parts a local file cannot give you: the law stored as an object
that belongs to the owner of the language, so changing it changes every saved program at once;
execution on a device you choose, next to the data; the agent's own rules and concepts, which
moved DeepSeek from 94.0 % to 97.0 % and removed the language drift; and distribution, where
someone installs the villager and the law comes with it. The villager is published as an agent:
https://os.extella.ai/listing/a7519bc1-fe16-466d-943d-6c024324835e

## Files

- `handlers/village.py` — the law. `village_v2.py` — the second law. `imena_mira.json` — the 95
  names the speech check knows.
- `measure/proverka.py` — the checker, one for every condition.
- `measure/otbor.json`, `otbor2.json`, `otbor3.json` — the three frozen card selections.
- `measure/zamer*.json` — every model answer, the verdict and the reason, card by card.
- `measure/zamer*.py`, `pereschet*.py`, `svodka*.py` — runners and recounts.
- `measure/regress.py` — 34 cases the law has to get right.
- `measure/ocenka_rechi*.json` — the naturalness ratings, line by line.
- `measure/log*.txt` — the raw run logs.

## What this does not show

- The author published the cards but not his judge or his bench runner. His numbers and ours come
  from different checkers. Treat this as the same order of magnitude, not as a reproduction.
- Nobody measures whether the chosen move is a good move. The cards carry no reference answer.
- Zero made-up memories belongs to the language, not to the model. The models make the same
  mistakes they make without it. The mistakes stop at the handler.
- Our villager makes no move on 4 cards out of 200 after one retry. The fine-tuned model always
  acts.
- We never ran the game. It needs Linux or Windows with a GPU.
- A number written in words slips past the digit check. We know and did not fix it inside this
  measurement.

## Credit and licence

The cards and the game are by Manuel García Sanz, MIT licensed, at
[manuelgscom/rumor-village](https://github.com/manuelgscom/rumor-village). We do not redistribute
them: `data/KAK_POLUCHIT.md` has the command and the sha256. Everything in this folder is ours,
under the repository licence.
