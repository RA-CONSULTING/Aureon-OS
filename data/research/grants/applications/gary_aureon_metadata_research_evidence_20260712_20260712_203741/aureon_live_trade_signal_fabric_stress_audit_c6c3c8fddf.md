# Aureon Live Trade Signal Fabric Stress Audit

- Status: `real_evidence_missing`
- Chain state: `real_data_attention`
- Event count: `5000`
- Traces: active `193` broken `275` complete `0`
- Recovered traces: `21`
- Real-evidence-only mode: `True` synthetic traces `0` events `0`
- Producer gaps: `1004`
- API budget gaps: `232`
- Broker proof gaps: `77`
- Real-evidence gaps: `172`
- Real-evidence top phase/producer/field: `data_ready` / `unified_market_trader` / `proof_mode_live_runtime`
- Capital complete A-to-B traces: `138`
- External live-route leaks: `81`
- ThoughtBus receiving: `True`
- Mycelium receiving: `True`
- Executor gate respected: `True`
- A-to-B speed scope: `current_runtime_session` answer `Signals are visible, but this scope has not reached position_open yet.`
- A-to-open fastest/p50/p95 ms: `None` / `None` / `None`
- A-to-gain fastest/p50/p95 ms: `None` / `None` / `None`

## Top Burn-Down Rows
- `olife-b54ce2361705b0d3df` `external_shadow_only` phase `broker_acknowledged` missing `1` id_gaps `4` rate_gaps `0` broker_gaps `1` real_gaps `0`
- `olife-83478f29b636127126` `external_shadow_only` phase `order_blocked` missing `1` id_gaps `3` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-3ef8f0035c52c674a3` `broken_chain` phase `order_blocked` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-29ea48c715d3e9236f` `broken_chain` phase `executor_accepted` missing `3` id_gaps `1` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-efda46024128abffd2` `broken_chain` phase `intent_published` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-f71fe7a0ddc05266e7` `broken_chain` phase `counter_intel_passed` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-289a214506baefc3f6` `broken_chain` phase `counter_intel_passed` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-f3d70781beeae9a6d8` `broken_chain` phase `counter_intel_passed` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-264e876096e534aa36` `broken_chain` phase `counter_intel_passed` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-257649f30625c0ca4d` `broken_chain` phase `counter_intel_passed` missing `1` id_gaps `0` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-806058b774b3105e1f` `external_shadow_only` phase `order_blocked` missing `1` id_gaps `2` rate_gaps `0` broker_gaps `0` real_gaps `0`
- `olife-0f6f10fb5a73a55ceb` `external_shadow_only` phase `order_blocked` missing `1` id_gaps `3` rate_gaps `0` broker_gaps `0` real_gaps `0`

## Blockers
- `external_live_route_leak`
- `broken_chain`
- `rate_budget_missing`
- `broker_proof_missing`
- `real_evidence_missing`
- `recovered_upstream_context_missing`
