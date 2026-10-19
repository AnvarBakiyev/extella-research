# CSPL: materials behind the article

The article: [extella.dev/cspl/](https://extella.dev/cspl/) (English), [extella.dev/cspl/ru/](https://extella.dev/cspl/ru/) (на русском).
Every folder holds the script that was run and the answers it recorded. One run on our own machines each, not a benchmark series.

## По строкам таблицы статьи / By the rows of the article's table

| Строка / Row | Папка / Folder | Главные файлы / Main files |
|---|---|---|
| Ledger: четыре короткие программы / Ledger: four short programs | [`ledger-handler-replacement/`](ledger-handler-replacement/) | `handler_via_mcp.py`, `handler-via-mcp-2026-10-02.json` |
| Десять программ через платформу и простой MCP-сервер / Ten programs through the platform and a plain MCP server | [`ten-programs-three-ways/`](ten-programs-three-ways/) | `measure3.py`, `generic_server.py`, `measure3-result-2026-10-02.json` |
| Изменение оформления одного отчёта / Restyling one report | [`report-restyle/`](report-restyle/) | `journal-ru.md` |
| Обновление 40 отчётов / Updating 40 reports | [`handler-width/`](handler-width/) | `e5_width.py`, `e5_run.log`, `e5_result.json`, `ITOG.md` |
| Расчёт фонда на ноутбуке и сервере / Fund value on a laptop and a server | [`fund-value-swap/`](fund-value-swap/), сравнение / comparison: [`windmill/`](windmill/) | `run16.py`, `result_extella.json`, `result_plain.json`; `run_wm.py`, `result_windmill_*.json` |
| Сайт из блоков / A site made of blocks | открытый пример / live example: [extella.dev/blocks/](https://extella.dev/blocks/), устройство / how it works: [extella.dev/blocks/server/](https://extella.dev/blocks/server/) | — |
| Расписания и маленькая модель / Shift schedules and a small model | [`handler-width/`](handler-width/) | `e3_shifts.py`, `e3v2_result_*.json`, `e3_v2*.log`, `ITOG.md` (раздел «Поправка 15.10») |

## Other materials of the article

| Folder | Section of the article |
|---|---|
| [`tally-example/`](tally-example/) | 4. Declaring a language: the `tally` handler, the script that registers and runs it, and the raw answers of 1 and 16 October 2026 |
| [`three-languages-chain/`](three-languages-chain/) | 5. A chain of three experts in three languages |
| [`custom-mcp/`](custom-mcp/) | A custom MCP server on top of the Extella API: 6 tools against 44 |
