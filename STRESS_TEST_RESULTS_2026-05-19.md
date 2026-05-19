# Stress Test Results — 2026-05-19

## What was run
1. Attempted to boot the unified trader runtime in this environment for 45 seconds:
   - `env PYTHONPATH=. python3 -m aureon.exchanges.unified_market_trader`
2. Ran the latency extraction stress tool:
   - `python3 scripts/diagnostics/stress_test_intelligence_to_trade_latency.py --tail 10000`

## Measured result (exact for this run)
- **Intelligence → trade execution latency: not measurable** in this run because **no order intents were published and no orders were submitted**.
- The runtime execution snapshots show:
  - `attempted_count = 0`
  - `submitted_count = 0`
  - `trade_path_state = runtime_clearance_hold`
  - blockers: `exchange_mutations_disabled`, `live_trading_not_enabled`, `order_intent_publish_disabled`, `real_orders_disabled`, `real_orders_not_allowed_by_runtime`, `unified_order_executor_disabled`

## Why this is the exact outcome
The stress tool computes timing only when it can match a full lifecycle chain (intent + execution + broker ack). In this run:
- intent snapshots: `0`
- lifecycle events: `1`
- execution snapshots: `21` but all blocked by runtime clearances.

Therefore, **the exact latency from intelligence to trade is currently undefined/blocked in this environment**.

## What to do to get a numeric latency immediately
Run the same script on a runtime where order intents and executor are enabled (paper/sandbox or live with safeguards clear). The output JSON at `state/latency_stress_report.json` will print p50/p95/p99 in milliseconds for:
- intent→execution result,
- intent→order submitted,
- order submitted→broker ack.
