# Aureon Exchange Monitoring Checklist

- Generated: 2026-05-22T07:23:19.643386+00:00
- Status: exchange_monitoring_ready
- Connected exchanges: 3/4
- Fresh exchange sources: 4/4
- Decision-fed exchanges: 1/4
- Fast-money usable exchanges: 1/4
- Waveform history exchanges: 4/4
- Total tickers monitored: 3034
- Runtime stale: False 

| Exchange | Connected | Fresh Cache | Tickers | Venues | Decision Fed | Fast Money | Missing |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| Binance | True | True | 2978 | 0 | False | False | no_exchange_action_plan_venue, per_exchange_orderbook_depth_not_proven |
| Kraken | False | True | 24 | 0 | False | False | cost_and_fee_context_not_confirmed, exchange_client_not_ready_or_credentials_missing, margin_pair_quotes_not_confirmed, no_exchange_action_plan_venue |
| Alpaca | True | True | 6 | 0 | False | False | authenticated_market_data_entitlement_not_proven, market_hours_state_not_confirmed, news_context_if_available_not_confirmed, no_exchange_action_plan_venue |
| Capital.com | True | True | 26 | 1 | True | True | capital_market_hours_and_position_close_speed_not_proven, market_hours_state_not_confirmed, open_position_context_not_confirmed, portfolio_balance_not_confirmed |

This checklist is evidence-only. It does not place orders or bypass live runtime checks.
