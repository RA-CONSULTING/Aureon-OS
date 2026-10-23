# Azyra Warehouse Admin Reality Check

Aureon now treats SFG warehouse correction work as production administration, not as a demo. The Azyra path is:

```text
audit source data -> select eligible candidate -> dedupe completed screen films -> verify live gates -> capture before evidence -> type/update through Azyra -> capture after evidence -> mark closeout -> move to next line
```

Dry-run output is not the finish line. It is a preflight gate. A line is production-ready only when all of the following are true:

- The row is an `ADJUSTMENT_CANDIDATE`, not a source-review or live-movement hold.
- The adjustment uses unit variance only; encoded SKU or tracker suffixes such as `=150`, `=14`, `=40`, or `-150` are measurement sizes, not quantities to type.
- Existing `commit_ok` screen films and closeout records have been checked so Aureon does not double-post a line.
- Azyra is open, logged in, focused, and the keyboard route is proven for the current RemoteApp session.
- `AZYRA_OPERATOR_ALLOW_INPUT=true` is enabled for live typing, and `AZYRA_OPERATOR_ALLOW_SUBMIT=true` is enabled only for an approved submit/post stage.
- Required stage evidence is recorded: before balance, header prerequisites, header focus, line-entry focus, entered-values review, submit approval, and after-balance verification.

Useful Azyra evidence and operator files:

| File | Purpose |
|---|---|
| `outputs/complete_adjustment_execution_pack/complete_adjustment_execution_pack_data.json` | Canonical execution pack of ready adjustment candidates, holds, and live-gate contract. |
| `outputs/aureon_live_learning_pass/live_adjustment_candidate_queue.json` | Current live-learning queue of candidate stock corrections. |
| `outputs/live_azyra_stock_adjustment_demo/latest_live_stock_adjustment_demo_result.json` | Latest gated live-intent result, including blockers when production execution is refused. |
| `state/azyra_operator/films/**/manifest.json` | Screen-film evidence for live typing, review, and commit/OK stages. |
| `state/azyra_operator/live_stock_adjustment_routes/live_stock_adjustment_route_20260604_192637_keyboard_proven.json` | Proof that the RemoteApp keyboard route works for staged keyboard workflows. |

Run the current capability and admin stress checks with:

```powershell
.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_capability_stress_audit
.\.venv\Scripts\python.exe -m pytest tests\test_aureon_capability_stress_audit.py tests\test_admin_capability_matrix.py tests\test_goal_capability_map.py tests\test_office_solo_operator.py tests\test_office_workweek_monitor.py tests\test_office_self_audit.py -q
```

If the latest live-intent result reports blockers such as `input_gate_disabled`, `submit_gate_disabled`, `keyboard_route_not_safe`, or missing stage evidence, Aureon must clear those blockers as work items. It must not pretend that a dry run or blocked preflight changed production stock.
