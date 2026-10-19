# Extella research

Open experiments, measurements and materials about [Extella](https://extella.dev/): the code we ran, the raw answers we got and what they show. Each folder says what was measured, when, on what, and what was not measured.

| Folder | What it holds |
|---|---|
| [`cspl/`](cspl/) | Materials behind the article [CSPL: a program is stored separately from the way it is executed](https://extella.dev/articles/cspl/) ([на русском](https://extella.dev/ru/articles/cspl/)) |

More topics will be added as separate top-level folders.

## How a folder is organised

- One folder per experiment or measurement, with a `README.md`: date, question, setup (models, machines, versions), files, result, limits.
- Raw results stay as they were recorded. If something was fixed and re-run, both runs stay and the README says which one counts.
- Before publishing, local paths become `~` or `<repo>`, and account identifiers (agents, devices, profiles) become placeholders such as `<agent-id>`. Keys and tokens are never in the files: the scripts read them from `~/.extella/` on the machine that runs them.
- To reproduce a run you need Extella installed and signed in; the scripts say what else they need.

## License

Code: MIT. Texts, results and data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [`LICENSE`](LICENSE).

---

## Коротко по-русски

Открытые опыты, замеры и материалы об Extella: код, который мы запускали, сырые ответы и что они показывают. В каждой папке написано, что измеряли, когда, на чём и что не измеряли. Сейчас здесь материалы к статье о CSPL (папка `cspl/`), дальше будут добавляться другие темы отдельными папками. Часть описаний внутри папок на русском: так они были написаны во время опытов.
