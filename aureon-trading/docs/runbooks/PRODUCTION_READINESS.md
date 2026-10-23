# Production Readiness (Free APIs + WebSockets)

Self-repair and the self-coder do not arm live trading, loosen evidence gates, change position sizing, or write `.env` and credential files. Those attempts are refused before a patch is applied. Self-repair stays disabled unless `AUREON_SELF_REPAIR_ENABLE=1` and `state/self_repair_config.json` contains `{"enabled": true}`. `AUREON_SELF_REPAIR_KILL=1` or a missing config stops it. `AUREON_CODE_AUTO_APPROVE` does not cover protected paths. The fusion note is `PRODUCTION_READINESS.md` at the repository root. Gary-leckey/aureon-trading was diffed against upstream and did not change this rule. See `MERGE_PLAN.md`.



Goal: reduce REST load and scanning latency by using free WebSocket feeds for "heavy lifting" market data, **without changing the trading strategy logic**.

## What Changed
- Added an **optional** WebSocket market-data feeder: `ws_market_data_feeder.py`
- Added an **optional** cache read step at the top of `fetch_prices()` in `micro_profit_labyrinth.py`
  - Default behavior is unchanged unless you set `WS_PRICE_CACHE_PATH`

## Why This Helps
- REST `ticker/24hr` calls are heavy and rate-limit prone at 100% coverage.
- Binance WebSocket `!ticker@arr` is free and provides full-market tickers continuously.
- The trader can now pre-seed `prices` + `ticker_cache` from disk in O(1) time.

## How To Run (Recommended)

### 1) Start the WebSocket feeder

Writes a continuously refreshed cache file:
- output: `ws_cache/ws_prices.json`

Command:
- `nohup python ws_market_data_feeder.py --out ws_cache/ws_prices.json > ws_feeder.log 2>&1 &`

### 2) Start the trader using the cache (optional)

Set these env vars:
- `WS_PRICE_CACHE_PATH=ws_cache/ws_prices.json`
- `WS_PRICE_CACHE_MAX_AGE_S=2.0`

Command:
- `nohup WS_PRICE_CACHE_PATH=ws_cache/ws_prices.json WS_PRICE_CACHE_MAX_AGE_S=2.0 python micro_profit_labyrinth.py --live --yes --multi-exchange > trading_live.log 2>&1 &`

## Notes / Constraints
- This is intentionally additive: if the cache is missing/stale, the system falls back to existing REST fetches.
- Binance is the best "free full-market" WS source; Kraken WS is per-pair subscription (not ideal for full market), so Kraken stays REST by default.

## Tuning
- Increase `WS_PRICE_CACHE_MAX_AGE_S` if disk writes are slower.
- Increase feeder `--write-interval-s` if you want fewer writes.

## Dependencies
- `websockets>=12.0` added to `requirements.txt`.
