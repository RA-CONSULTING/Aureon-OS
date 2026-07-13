# Aureon Global Financial Coverage Map

- Generated: 2026-05-22T07:23:27.962011+00:00
- Status: global_financial_map_ready_with_gaps
- Usable domains: 3/6
- Fresh domains: 5/6
- Source coverage: 90.0%
- Usable sources: 9/10 configured/reachable
- Accounted sources: 100.0%
- Live tickers: 3034
- Active live sources: 4
- Fresh exchanges: 4
- Decision-fed exchanges: 1
- History rows: 222639
- History DB bytes: 162885632

| Domain | Fresh | Usable | Live Count | History Count | Missing | Next Action |
| --- | --- | --- | ---: | ---: | --- | --- |
| crypto_live_market | True | True | 3034 | 211772 |  | Keep Binance streaming; activate Kraken live cache, spot/margin fee context, and order-book probes. |
| equity_and_etf_live_market | True | False | 6 | 0 |  | Use Alpaca snapshots/stream entitlements to add fresh equity and ETF ticks. |
| cfd_fx_indices_equities | True | True | 26 | 10634 |  | Add Capital market snapshot refresh and fast profitable-position close telemetry. |
| historical_waveform_memory | True | True | 3034 | 211772 |  | Keep live cache writing bars into global history so models build from 1h through 1y. |
| macro_events_context | False | False | 0 | 0 | fresh_economic_calendar | Refresh owned/licensed macro calendar and event feeds for context-aware trade selection. |
| sentiment_onchain_forecast_context | True | False | 98 | 130 |  | Feed sentiment, on-chain, and forecast claims into the decision memory with timestamps. |

## Source Registry

| Source | Category | Credentials | Usable | Rows | Governor | Reason |
| --- | --- | --- | --- | ---: | --- | --- |
| binance_live | live_exchange | configured | True | 2978 | maintain |  |
| kraken_live | live_exchange | configured | True | 24 | maintain |  |
| alpaca_live | live_exchange | configured | True | 6 | maintain |  |
| capital_live | live_exchange | configured | True | 26 | maintain |  |
| yfinance_history | history | not_required | False | 0 | provider_unavailable | provider_returned_no_usable_rows |
| coinapi_history | history | configured | False | 0 | run_refresh | no_usable_rows_or_fresh_cache |
| coinbase_history | history | not_required | True | 52500 | maintain |  |
| coingecko_snapshot | context | not_required | True | 28 | maintain |  |
| fred_macro | macro | missing | False | 0 | credential_required | required_credentials_missing |
| fmp_calendar | events | missing | False | 0 | credential_required | required_credentials_missing |
| world_news | sentiment | missing | False | 0 | credential_required | required_credentials_missing |
| glassnode_onchain | onchain | missing | False | 0 | credential_required | required_credentials_missing |
| macro_snapshot | context | not_required | True | 44 | maintain |  |
| account_trades | account_memory | configured | True | 10634 | maintain |  |
| queen_knowledge | internal | not_required | True | 15401 | maintain |  |

This is an evidence map only. It does not execute trades or bypass live safety checks.
