# Stage 8 exchanges read surface

Decision: **HOLD**. Live orders: **refused**. Read-gated: yes.
Go-live is not clear. This page does not publish a Space.

Pin: `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. Pin moved: no. Badge: unchanged.
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
