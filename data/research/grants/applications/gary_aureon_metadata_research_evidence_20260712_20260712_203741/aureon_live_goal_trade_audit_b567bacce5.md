# Aureon Live Goal Trade Audit

- Status: `live_goal_trade_audit_blocked_live_gold_data_not_fresh`
- Proof state: `blocked_live_gold_data_not_fresh`
- Live trade produced: `False`
- GOLD order intent ready: `False`
- Fresh data ready: `False`
- Executor ready: `False`

## Data Capture
- Stream cache: `live_data_not_action_fresh` age `45717.022` sec, tickers `3028`
- Capital GOLD: `capital_gold_not_action_fresh` assets `0`

## Intent And Executor
- Intent packet: `gold_order_intent_not_ready` total `1` GOLD `0`
- Executor: `executor_gated` attempted `0` submitted `0`
- Lifecycle stress: `order_lifecycle_stress_certified` cases `12/12` requirements `15/15`
- Capital ecosystem: `capital_ecosystem_intelligence_attention` active watchlist `0/0` shadow hedges `0`
- Capital live dry stress: `live_dry_attention` status `` blockers `1`
- Capital revenue logic: `capital_revenue_logic_attention` net-positive `0` intent-eligible `0` blockers `2`
- Capital live-gate readiness: `capital_revenue_live_gate_attention` ready-now `0` missing gates `0` blockers `0`
- Live signal fabric stress: `live_trade_signal_fabric_stress_attention` chain `real_data_attention` real-only `True` synthetic traces `0` publisher gaps `1658` rate gaps `4609` broker gaps `89` real gaps `4547` top `candidate_ready/unified_market_trader/proof_mode_live_runtime`

## Blockers
- `stream_cache_stale`
- `stale_active_sources:alpaca,binance,capital,kraken`
- `capital_gold_registry_missing`
- `order_intent_packet_stale`
- `no_gold_order_intent_published`
- `exchange_mutations_disabled`
- `live_trading_not_enabled`
- `order_intent_publish_disabled`
- `real_orders_disabled`
- `real_orders_not_allowed_by_runtime`
- `unified_order_executor_disabled`
- `lifecycle_continuity_missing`

## Next Action
Refresh live stream cache and Capital GOLD quote proof before promoting any GOLD order-intent.
