#!/bin/sh
cd "$(dirname "$0")"; AG=<agent-id>; MAC=<mac-device-id>
Q=$(python3 -c "import json;print(json.loads(open('../../data/gsm8k_test.jsonl').readline())['question'])")
if false; then echo "HTTP (REST expert/run):"
python3 - "$Q" <<'PY'
import sys; sys.path.insert(0, "..")
import ext
r, dt = ext.run("gsm_solve", {"question": sys.argv[1]}, ext.MAC)
print(r.get("result", r) if isinstance(r, dict) else r, round(dt, 1), "с")
PY
fi
echo "Codex через стандартный MCP Extella (события):"
EXTELLA_API_TOKEN="$(cat ~/.extella/api_token.txt)" codex exec --json --skip-git-repo-check -s read-only -c approval_policy='"never"' -c "mcp_servers.extella.http_headers.X-Agent-Id=\"$AG\"" -c 'mcp_servers.extella.default_tools_approval_mode="approve"' -c 'mcp_servers.extella.tool_timeout_sec=1500' -c 'mcp_servers.extella_primary.url="https://api.extella.ai/mcp/"' -c 'mcp_servers.extella_primary.bearer_token_env_var="EXTELLA_API_TOKEN"' -c 'mcp_servers.extella_primary.env_http_headers={"X-Auth-Token"="EXTELLA_API_TOKEN"}' -c "mcp_servers.extella_primary.http_headers={\"X-Profile-Id\"=\"default\",\"X-Agent-Id\"=\"$AG\"}" -c 'mcp_servers.extella_primary.default_tools_approval_mode="approve"' -c 'mcp_servers.extella_primary.tool_timeout_sec=1500' "Use the run_expert MCP tool to run the expert gsm_solve with params {\"question\": <the question below, exactly>} and targets [\"$MAC\"]. If it returns a task_id, poll check_task until it is done. Do not compute the answer yourself. Reply with only the answer number from the tool result. Question: $Q" < /dev/null > codex_events.jsonl 2>&1
python3 -c "
import json
ev=[json.loads(l) for l in open('codex_events.jsonl') if l.startswith('{')]
items=[e.get('item',{}) for e in ev if e.get('type')=='item.completed']
print('вызовы MCP:', [(i.get('server'), i.get('tool'), i.get('status')) for i in items if i.get('type')=='mcp_tool_call'])
print('ответ:', [i.get('text') for i in items if i.get('type')=='agent_message'][-1:])"
