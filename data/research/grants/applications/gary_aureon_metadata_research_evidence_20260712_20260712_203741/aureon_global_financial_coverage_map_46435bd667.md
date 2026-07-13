# Aureon Global Financial Coverage Map

- Generated: 2026-05-15T17:36:16.000470+00:00
- Status: global_financial_map_complete_for_configured_registry
- Usable domains: 1/6
- Fresh domains: 4/6
- Source coverage: 100.0%
- Usable sources: 10/10 configured/reachable
- Accounted sources: 100.0%
- Live tickers: 3026
- Active live sources: 4
- Fresh exchanges: 4
- Decision-fed exchanges: 0
- History rows: 1419689
- History DB bytes: 1111433216

| Domain | Fresh | Usable | Live Count | History Count | Missing | Next Action |
| --- | --- | --- | ---: | ---: | --- | --- |
| crypto_live_market | False | False | 3026 | 1415626 |  | Keep Binance streaming; activate Kraken live cache, spot/margin fee context, and order-book probes. |
| equity_and_etf_live_market | True | False | 6 | 0 |  | Use Alpaca snapshots/stream entitlements to add fresh equity and ETF ticks. |
| cfd_fx_indices_equities | True | False | 18 | 3291 |  | Add Capital market snapshot refresh and fast profitable-position close telemetry. |
| historical_waveform_memory | True | True | 3026 | 1415626 |  | Keep live cache writing bars into global history so models build from 1h through 1y. |
| macro_events_context | False | False | 0 | 0 | fresh_economic_calendar | Refresh owned/licensed macro calendar and event feeds for context-aware trade selection. |
| sentiment_onchain_forecast_context | True | False | 637 | 669 |  | Feed sentiment, on-chain, and forecast claims into the decision memory with timestamps. |

## Source Registry

| Source | Category | Credentials | Usable | Rows | Governor | Reason |
| --- | --- | --- | --- | ---: | --- | --- |
| binance_live | live_exchange | configured | True | 2978 | mapped_runtime_stale_decision_hold |  |
| kraken_live | live_exchange | configured | True | 24 | mapped_runtime_stale_decision_hold |  |
| alpaca_live | live_exchange | configured | True | 6 | mapped_runtime_stale_decision_hold |  |
| capital_live | live_exchange | configured | True | 18 | mapped_runtime_stale_decision_hold |  |
| yfinance_history | history | not_required | False | 0 | provider_unavailable | provider_returned_no_usable_rows |
| coinapi_history | history | configured | True | 1178036 | maintain |  |
| coinbase_history | history | not_required | True | 52542 | maintain |  |
| coingecko_snapshot | context | not_required | True | 182 | maintain |  |
| fred_macro | macro | missing | False | 0 | credential_required | required_credentials_missing |
| fmp_calendar | events | missing | False | 0 | credential_required | required_credentials_missing |
| world_news | sentiment | missing | False | 0 | credential_required | required_credentials_missing |
| glassnode_onchain | onchain | missing | False | 0 | credential_required | required_credentials_missing |
| macro_snapshot | context | not_required | True | 286 | maintain |  |
| account_trades | account_memory | configured | True | 3291 | maintain |  |
| queen_knowledge | internal | not_required | True | 63823 | maintain |  |

This is an evidence map only. It does not execute trades or bypass live safety checks.
