# Aureon Exchange Data Capability Matrix

- Generated: 2026-05-15T17:35:17.985618+00:00
- Status: exchange_data_capability_matrix_connected_guarded_runtime_stale
- Connected exchanges: 4/4
- Fresh feeds: 4/4
- Decision-fed exchanges: 0/4
- Data-boost eligible exchanges: 2
- Cash/position-active exchanges: 2
- Runtime booting: False
- Trading/data ready: True/True
- Preflight: yellow

| Exchange | Trading modes | Fresh | Decision fed | Safe calls/min | Market data/min | Optimizer | Gaps |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| Binance | crypto_spot, margin_route_planning_if_account_supported | True | False | 240.0 | 196.8 | Use this idle/no-cash venue for wider market discovery, quote probes, and cross-exchange confirmation. | per_exchange_orderbook_depth_not_proven, runtime_stale, runtime_stale_blocks_fresh_live_decision_use |
| Kraken | crypto_spot, crypto_margin | True | False | 30.0 | 8.4 | Reserve private calls for balances, collateral, and execution; keep history sync capped and favor public streams. | cost_and_fee_context_not_confirmed, margin_pair_quotes_not_confirmed, per_exchange_orderbook_depth_not_proven, runtime_stale, runtime_stale_blocks_fresh_live_decision_use |
| Alpaca | stocks, etfs, crypto_spot_if_enabled | True | False | 120.0 | 98.4 | Use this idle/no-cash venue for wider market discovery, quote probes, and cross-exchange confirmation. | authenticated_market_data_entitlement_not_proven, market_hours_state_not_confirmed, news_context_if_available_not_confirmed, portfolio_balance_not_confirmed, runtime_stale |
| Capital.com | cfds, forex, indices, equity_cfds | True | False | 45.0 | 18.9 | Prioritize open-position P/L, confirmations, and a 40-instrument high-volatility watchlist. | capital_market_hours_and_position_close_speed_not_proven, market_hours_state_not_confirmed, runtime_stale, runtime_stale_blocks_fresh_live_decision_use |

This matrix is evidence-only and does not place orders.
