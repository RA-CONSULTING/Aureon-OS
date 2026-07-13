# Aureon Exchange Monitoring Checklist

- Generated: 2026-05-15T17:35:01.992024+00:00
- Status: exchange_monitoring_connected_guarded_runtime_stale
- Connected exchanges: 4/4
- Fresh exchange sources: 4/4
- Decision-fed exchanges: 0/4
- Fast-money usable exchanges: 0/4
- Waveform history exchanges: 4/4
- Total tickers monitored: 3026
- Runtime stale: True tick_in_progress_stalled

| Exchange | Connected | Fresh Cache | Tickers | Venues | Decision Fed | Fast Money | Missing |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| Binance | True | True | 2978 | 1 | False | False | per_exchange_orderbook_depth_not_proven, runtime_stale_blocks_fresh_live_decision_use |
| Kraken | True | True | 24 | 2 | False | False | cost_and_fee_context_not_confirmed, margin_pair_quotes_not_confirmed, per_exchange_orderbook_depth_not_proven, runtime_stale_blocks_fresh_live_decision_use |
| Alpaca | True | True | 6 | 1 | False | False | authenticated_market_data_entitlement_not_proven, market_hours_state_not_confirmed, news_context_if_available_not_confirmed, portfolio_balance_not_confirmed |
| Capital.com | True | True | 18 | 1 | False | False | capital_market_hours_and_position_close_speed_not_proven, market_hours_state_not_confirmed, runtime_stale_blocks_fresh_live_decision_use |

This checklist is evidence-only. It does not place orders or bypass live runtime checks.
