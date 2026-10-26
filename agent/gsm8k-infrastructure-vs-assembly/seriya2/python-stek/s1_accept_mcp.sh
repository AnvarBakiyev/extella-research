#!/bin/sh
cd "$(dirname "$0")"; PY="$PWD/.venv/bin/python"
Q=$("$PY" -c "import json;print(json.loads(open('../../data/gsm8k_test.jsonl').readline())['question'])")

echo "Codex через MCP:"; codex exec --skip-git-repo-check -s read-only -c approval_policy='"never"' -c "mcp_servers.gsm.command=\"$PY\"" -c "mcp_servers.gsm.args=[\"$PWD/mcp_server.py\"]" -c 'mcp_servers.gsm.tool_timeout_sec=1200' -c 'mcp_servers.gsm.default_tools_approval_mode="approve"' -c 'mcp_servers.gsm.startup_timeout_sec=60' "Call the solve_gsm tool with exactly this question and reply with only the answer number it returns: $Q" 2>&1 | tail -4
../j.sh python S1 "приёмка MCP-путей: конец"
