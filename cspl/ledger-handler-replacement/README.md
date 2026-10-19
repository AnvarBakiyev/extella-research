# Ledger: a handler replaced under four saved programs

2 October 2026. A small language `ledger` of two statements. `handler_via_mcp.py` saves two registrars (handler v1 and v2), registers v1 on a laptop, runs four `ledger` programs and one text that is not a ledger program, replaces the handler with v2 and runs the same four programs again without saving them anew, then registers v1 on a Linux server and runs two of the programs there. Every step is a call of the MCP tools `save_expert` and `run_expert`.

- `handler_via_mcp.py`: the script.
- `handler-via-mcp-2026-10-02.json`: the recorded answers. The program texts stayed the same; after the replacement the answers carry the fields the new handler adds.
