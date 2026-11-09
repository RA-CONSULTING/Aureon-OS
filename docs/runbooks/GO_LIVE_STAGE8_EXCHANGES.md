# Stage 8 exchanges read surface

Decision: **HOLD**. Live orders: **refused**. Read-gated: yes.
Go-live is not clear. This page does not publish a Space.

Pin: `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. Pin moved: no. Badge: unchanged.
This receipt was measured before the squash/rebase at `55ab3579e4a1e59b442e46800c5486a270fc5b0c`. That commit is not an ancestor of main. The same work is carried on main by `30d8101b486f6f48b9219a337e2b77808e5038e1` (#263). This page does not remeasure the sweep.
Rows: 647. Called: 0. Reachable: 0.
Imports performed: 0. Key leak: false.
Sockets: 0. Processes: 0. Writes: 0.
Entries sha256: `e24be5f6199f39a6ecee510827b5fc155685b37c45ef474b773d44b773b19226`.

`OPEN_PLAN_THROUGH` is 2. `ENABLED_THROUGH` is 6. Plan stages 3 and 4 stay closed.
The protocol session and the call sweep were not repeated.

Reproduce:

```bash
env PYTHONPATH=mcp python3 scripts/validation/go_live_stage8_exchanges.py --check
```
