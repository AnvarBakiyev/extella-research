#!/bin/sh
# Приёмка S1 на Python-стороне: три потребителя, задача теста строка 1
cd "$(dirname "$0")"; PY="$PWD/.venv/bin/python"; PORT=18765
Q=$("$PY" -c "import json;print(json.loads(open('../../data/gsm8k_test.jsonl').readline())['question'])")
../j.sh python S1 "приёмка: старт"
"$PY" -m uvicorn api:app --port $PORT --log-level warning & UV=$!; sleep 3
echo "HTTP:"; curl -s -X POST localhost:$PORT/solve -H 'Content-Type: application/json' -d "$("$PY" -c "import json,sys;print(json.dumps({'question':sys.argv[1]}))" "$Q")"; echo
kill $UV
echo "MCP-клиент:"; "$PY" mcp_client_check.py "$Q"
echo "Codex через MCP:"; codex exec --skip-git-repo-check -s read-only -c approval_policy='"never"' -c "mcp_servers.gsm.command=\"$PY\"" -c "mcp_servers.gsm.args=[\"$PWD/mcp_server.py\"]" -c 'mcp_servers.gsm.tool_timeout_sec=1200' -c 'mcp_servers.gsm.startup_timeout_sec=60' "Call the solve_gsm tool with exactly this question and reply with only the answer number it returns: $Q" 2>&1 | tail -4
../j.sh python S1 "приёмка: конец"
