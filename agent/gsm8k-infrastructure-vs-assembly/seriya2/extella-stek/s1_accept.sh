#!/bin/sh
# Приёмка S1 на стороне Extella: три потребителя одного эксперта gsm_solve, задача теста строка 1.
# Новый код потребителей: ноль строк; только вызовы стандартных точек платформы.
cd "$(dirname "$0")"; AG=<agent-id>; MAC=<mac-device-id>
Q=$(python3 -c "import json;print(json.loads(open('../../data/gsm8k_test.jsonl').readline())['question'])")
../j.sh extella S1 "приёмка: старт"
echo "HTTP (REST expert/run):"
python3 - "$Q" <<'PY'
import sys; sys.path.insert(0, "..")
import ext
r, dt = ext.run("gsm_solve", {"question": sys.argv[1]}, ext.MAC)
print(r.get("result", r) if isinstance(r, dict) else r, round(dt, 1), "с")
PY
echo "Чат-агент Extella:"
python3 - "$Q" <<'PY'
import sys, json, time; sys.path.insert(0, "..")
import ext
t0 = time.time()
r = ext.call("/agent/run", {"agent_id": ext.AGENT, "input": sys.argv[1], "run_timeout": 1500}, timeout=1600)
txt = json.dumps(r, ensure_ascii=False)
import re
outs = [o for o in r.get("output", []) if isinstance(o, dict) and o.get("type") == "message"] if isinstance(r, dict) else []
print((outs[-1]["content"][0].get("text") if outs else txt[-400:]), round(time.time() - t0, 1), "с")
PY
echo "Codex через стандартный MCP Extella:"
codex exec --skip-git-repo-check -s read-only -c approval_policy='"never"' -c "mcp_servers.extella.http_headers.X-Agent-Id=\"$AG\"" -c 'mcp_servers.extella.tool_timeout_sec=1500' -c 'mcp_servers.extella.default_tools_approval_mode="approve"' "Use the Extella MCP tool run_expert to run the expert gsm_solve with params {\"question\": <the question below, exactly>} and targets [\"$MAC\"]. If it returns a task_id, poll check_task until it is done. Reply with only the answer number. Question: $Q" 2>&1 | tail -4
../j.sh extella S1 "приёмка: конец"
