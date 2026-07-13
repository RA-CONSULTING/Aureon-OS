# Open Market Data Matrix

This file tracks the repo's public/open market-data systems, what they cover, and whether they are feeding the current unified live stack.

## Status Keys

- `wired`: actively contributing to selection, monitoring, or live dashboard state
- `partial`: present in runtime or telemetry, but not materially affecting both venue paths yet
- `available`: exists in repo and is usable, but not wired into the current live path

## Current Live Consumers

- `Kraken trader`: `aureon/exchanges/kraken_margin_penny_trader.py`
- `Capital trader`: `aureon/exchanges/capital_cfd_trader.py`
- `Unified runner`: `aureon/exchanges/unified_market_trader.py`
- `Frontend`: `frontend/src/hooks/useTerminalSync.ts`

## Public/Open Feeds Already In The Live Path

| Feed | File | Coverage | Status | Current Consumer |
| --- | --- | --- | --- | --- |
| Binance public websocket/book-ticker/trades | `aureon/exchanges/kraken_margin_penny_trader.py` | crypto live monitoring | wired | Kraken trader active-trade monitor, top-7 watchlist |
| Binance public REST pricing | `aureon/exchanges/kraken_margin_penny_trader.py` | crypto universe pricing | wired | Kraken trader shortlist scan |
| Kraken public market metadata | `aureon/exchanges/kraken_margin_penny_trader.py` | margin-eligible pairs, pair metadata | wired | Kraken trader universe discovery |
| Capital.com market snapshots | `aureon/exchanges/capital_cfd_trader.py` | CFDs, FX, indices, commodities, shares | wired | Capital trader selection and monitoring |
| Live TV station log feed | `aureon/data_feeds/aureon_live_tv_station.py` | public stream-derived market telemetry | wired | Kraken trader score overlay, terminal snapshot, dashboard payload |
| Ocean Wave scanner | `aureon/scanners/aureon_ocean_wave_scanner.py` | bot/whale microstructure from live tape | wired | Kraken trader score overlay, terminal snapshot, dashboard payload |
| Whale orderbook analyzer | `aureon/analytics/aureon_whale_orderbook_analyzer.py` | public orderbook pressure | wired | Kraken trader score overlay, terminal snapshot, dashboard payload |

## Public/Open Feeds Present But Only Partially Used

| Feed | File | Coverage | Status | Current Gap |
| --- | --- | --- | --- | --- |
| Unified local telemetry API | `aureon/exchanges/unified_market_trader.py` | combined Kraken + Capital state | partial | frontend consumes it, but underlying venue market watchers are still asymmetric |
| Local terminal telemetry API | `aureon/exchanges/kraken_margin_penny_trader.py` | Kraken-only local state | partial | superseded by unified runner in end-user mode |
| Capital live candidate snapshots | `aureon/exchanges/capital_cfd_trader.py` | Capital Top 7 selection state | partial | visible in status/dashboard, but not backed by additional public cross-check feeds |

## High-Value Public/Open Feeds Available But Not Wired

| Feed | File | Coverage | Status | Best Use |
| --- | --- | --- | --- | --- |
| Global Wave scanner | `aureon/scanners/aureon_global_wave_scanner.py` | broader cross-market wave states | available | shortlist overlay for Kraken + Capital |
| Live Momentum Hunter | `aureon/scanners/aureon_live_momentum_hunter.py` | fast impulse detection | available | top-7 validation and entry timing |
| Live market feed | `aureon/data_feeds/aureon_live_market_feed.py` | public market stream broker | available | unified watcher service |
| Market Data Hub | `aureon/data_feeds/market_data_hub.py` | feed aggregation/cache | available | centralize open-feed access for both venues |
| Global Financial Feed | `aureon/data_feeds/global_financial_feed.py` | macro/public market context | available | Capital macro overlay, cross-market risk filter |
| CoinGecko price feeder | `aureon/exchanges/coingecko_price_feeder.py` | public crypto fallback pricing | available | Kraken fallback confirmation/cache |
| Coinbase historical feed | `aureon/exchanges/coinbase_historical_feed.py` | public crypto historical candles | available | projection/history enrichment for Kraken |
| Whale integration | `aureon/analytics/aureon_whale_integration.py` | unified whale signal layer | available | combine whale modules into one venue-agnostic overlay |
| Live whale profiler | `aureon/analytics/aureon_live_whale_profiler.py` | public large-flow tracking | available | confirmation overlay and dashboard watcher |

## Current Asymmetry

Kraken currently has the richer public/open feed stack:

- Binance live watchlist
- Live TV overlay
- Ocean Wave overlay
- Whale orderbook overlay

Capital currently relies much more on:

- Capital.com market snapshots
- internal scoring/intelligence layers
- local shadow validation

Capital is missing equivalent extra public/open watcher layers.

## Network And Decision Routing

The repo already contains the internal network layer needed to route these feeds into higher cognition:

| Layer | File | Status | Current Role |
| --- | --- | --- | --- |
| ThoughtBus | `aureon/core/aureon_thought_bus.py` | wired | market snapshots and decision events published by live traders |
| Unified Intelligence Registry | `aureon/intelligence/aureon_unified_intelligence_registry.py` | partial | category and chain snapshots surfaced in trader telemetry |
| Unified Decision Engine | `aureon/intelligence/aureon_unified_decision_engine.py` | partial | best-candidate audit/decision signal sink |
| Cognition Runtime | `aureon/autonomous/aureon_cognition_runtime.py` | partial | recent cognition topics surfaced via ThoughtBus snapshots |

This means the practical route is:

1. open/public market feeds
2. ThoughtBus publication
3. registry / cognition snapshots
4. unified decision engine
5. venue trader execution

## Recommended Wiring Order

1. `aureon/scanners/aureon_global_wave_scanner.py`
   Apply to both Kraken and Capital top-7 candidate scoring.
2. `aureon/scanners/aureon_live_momentum_hunter.py`
   Use as a fast timing layer for both venues.
3. `aureon/data_feeds/market_data_hub.py`
   Centralize open/public feed access and caching for the unified runner.
4. `aureon/data_feeds/global_financial_feed.py`
   Add macro/public context to Capital selection and unified risk view.
5. `aureon/analytics/aureon_whale_integration.py`
   Normalize whale/flow overlays into one shared interface.
6. `aureon/exchanges/coingecko_price_feeder.py`
   Add public fallback crypto pricing for Kraken resilience.
7. `aureon/exchanges/coinbase_historical_feed.py`
   Add richer public historical context for Kraken timeline/projection.

## Immediate Next Tasks

1. Wire Global Wave scanner into Kraken and Capital candidate scoring.
2. Wire Live Momentum Hunter into Kraken and Capital top-7 monitoring.
3. Expose both new overlays in unified terminal and dashboard payloads.
4. Move shared public-feed access behind a single adapter in `market_data_hub.py`.
