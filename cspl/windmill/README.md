# The same scenario on Windmill CE

7 October 2026. The fund-value scenario of [`../fund-value-swap/`](../fund-value-swap/) run on Windmill CE v1.825.0 in local Docker, bound to 127.0.0.1, with one and with two workers. The credentials in `docker-compose.yml` and `run_wm.py` are the local defaults of that throwaway setup.

- `docker-compose.yml`, `run_wm.py`: setup and script.
- `result_windmill_2workers.json`, `result_windmill_1worker.json`, `result_windmill.json`: recorded timelines.
- `agent_worker_probe.json`: what happened when we tried to start a remote worker without database access in the community edition.

The Windmill run used one machine. A second machine was not measured.
