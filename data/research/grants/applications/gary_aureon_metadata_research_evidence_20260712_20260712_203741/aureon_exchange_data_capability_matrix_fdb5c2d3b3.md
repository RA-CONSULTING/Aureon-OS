# Aureon Exchange Data Capability Matrix

- Generated: 2026-05-22T07:23:21.204485+00:00
- Status: exchange_data_capability_matrix_connected_guarded_runtime_not_ready
- Connected exchanges: 3/4
- Fresh feeds: 4/4
- Decision-fed exchanges: 1/4
- Data-boost eligible exchanges: 4
- Cash/position-active exchanges: 0
- Runtime booting: True
- Trading/data ready: True/True
- Preflight: red

| Exchange | Trading modes | Fresh | Decision fed | Safe calls/min | Market data/min | Optimizer | Gaps |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| Binance | crypto_spot, margin_route_planning_if_account_supported | True | False | 240.0 | 196.8 | Use this idle/no-cash venue for wider market discovery, quote probes, and cross-exchange confirmation. | no_exchange_action_plan_venue, per_exchange_orderbook_depth_not_proven, runtime_booting, runtime_stale |
| Kraken | crypto_spot, crypto_margin | True | False | 60.0 | 42.0 | Configure and validate this exchange client before assigning scan or execution budget. | cost_and_fee_context_not_confirmed, exchange_client_not_ready_or_credentials_missing, margin_pair_quotes_not_confirmed, no_exchange_action_plan_venue, per_exchange_orderbook_depth_not_proven |
| Alpaca | stocks, etfs, crypto_spot_if_enabled | True | False | 120.0 | 98.4 | Use this idle/no-cash venue for wider market discovery, quote probes, and cross-exchange confirmation. | authenticated_market_data_entitlement_not_proven, market_hours_state_not_confirmed, news_context_if_available_not_confirmed, no_exchange_action_plan_venue, portfolio_balance_not_confirmed |
| Capital.com | cfds, forex, indices, equity_cfds | True | True | 45.0 | 33.75 | Use this idle/no-cash venue for wider market discovery, quote probes, and cross-exchange confirmation. | capital_market_hours_and_position_close_speed_not_proven, market_hours_state_not_confirmed, open_position_context_not_confirmed, portfolio_balance_not_confirmed, profit_loss_context_not_confirmed |

This matrix is evidence-only and does not place orders.
