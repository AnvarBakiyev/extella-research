# CSPL: an independent experiment series run with Codex (OpenAI), 18–21 October 2026

Fourteen reports and a product-oriented conclusion from a series of experiments on CSPL in Extella, planned and run by Codex on Anvar Bakiyev's machines (a Mac and a Linux host) between 18 and 21 October 2026. The reports are in Russian. They are published here as written, with only paths, timezone and account identifiers replaced; `EVIDENCE.json` keeps the SHA-256 of each original.

## What the series found, in the authors' own words

The main report (`reports/cspl-comprehensive-20261020__REPORT.txt`) states the result plainly: CSPL does store a program together with the name of its handler and runs it through the standard Extella interface; through this mechanism short domain programs, nested calls, dependency graphs, handler versions and compilation to C with native execution all worked. But in an honest comparison, Python with the same ready library, registry, algorithm, cache and validation got the same capabilities; **no unique quantitative advantage of the CSPL mechanism itself was found**. Its confirmed property is the built-in platform convention "source + handler".

Other verified points worth reading:

- One saved Expert holding five programs in four languages (a custom FLOW language, SQL, JavaScript, Python); mutual Python↔JavaScript recursion to 8 levels; one child replaced from JavaScript to Python without touching the parents (`cspl-polyglot-nesting-20261021`).
- A chain JSON → handler → C → machine code, executed on ARM64 Mach-O and x86-64 ELF; 104 calls matched an independent Decimal reference.
- Token numbers: with the same library, a JSON policy cost 5.8 % fewer tokens than Python in one creation series and more in others; the authors say the sign changes by task and no universal saving follows. A 6/6 vs 4/6 result on Haiku came from answer formatting (code fences, prose before the call), not from business logic.
- Boundaries of the current platform interface found along the way: on the external call path `0`, `false`, `""`, `null`, `[]` and `{}` are lost as parameters; saving strips trailing whitespace bytes; `isError=false` can accompany a failed execution.

## How to read `CONCLUSION.txt`

`reports/cspl-conclusion-20261021__CONCLUSION.txt` is a product-facing synthesis of the same material. Its eleven "confirmed" properties are properties of the handlers and libraries written for the experiments; the main report says so, the conclusion only in its introduction. Read the conclusion together with the main report, and take the application examples from it, not the word "confirmed".

## Relation to our own measurements

This series was run independently of the measurements in `../` and `../../agent/skill-vs-expert/`. Its main finding agrees with ours: on a strong model the mechanism gives no accuracy or token advantage by itself; what it gives is a stored, replaceable, uniformly callable program object, and, with a small task language, a boundary and checks before execution.

Files: `reports/` (15 text files, Russian), `EVIDENCE.json`. The full working folders (scripts, raw responses, hashes, review runs; about 120 MB) are kept privately and can be shared on request.
