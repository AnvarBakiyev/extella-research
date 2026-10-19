# Replacing a shared operation on two machines

6 October 2026. One operation (the value of a fund at the second custodian) has three users: two on a laptop, one on a server. It was replaced from Python to Go in two ways: as Extella experts with a Go language handler, and as a plain program. A 30-second call was in flight during the replacement.

What the run recorded: on the platform the replacement was one action (2.4 s) against eight for the plain program; the call in flight finished on the old implementation in both; the replacement also reached the server, which has no Go compiler, so the third user failed there, while the plain program shipped a built binary and kept working; the rollback on the platform worked only because the old text was kept locally, the platform keeps no versions; every platform call took about ten times longer.

- `run16.py`: the script that ran both arms and counted the steps.
- `fund_value_v1.py`, `fund_value_v2.go`: the two implementations of the operation.
- `handler_go.py`: the Go language handler registered on the devices.
- `result_extella.json`, `result_plain.json`: recorded timelines of both arms.
