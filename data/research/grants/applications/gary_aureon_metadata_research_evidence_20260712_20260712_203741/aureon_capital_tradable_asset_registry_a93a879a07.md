# Aureon Capital Tradable Asset Registry

Generated: 2026-05-15T17:33:01.491478+00:00
Schema: aureon-capital-tradable-asset-registry-v1

This registry records Capital.com market metadata and the Aureon code route used to buy, sell, or close a CFD. It does not submit orders; live orders still pass through the existing runtime, portfolio, confidence, and exchange gates.

## Summary

- Total Capital markets discovered: 6835
- Snapshot enriched this run: 250 / budget 250
- Trade route configured: 6553
- Trade ready with sampled cost and margin: 242
- Cost known: 250
- Margin known: 250

## Execution Route

- BUY: `CapitalClient.place_market_order(symbol, "BUY", size)` via `POST /positions`
- SELL: `CapitalClient.place_market_order(symbol, "SELL", size)` via `POST /positions`
- CLOSE: `CapitalClient.close_position(deal_id)` via `DELETE /positions/{dealId}`

## Top Blockers

- snapshot_not_sampled_budget: 6585
- minimum_deal_size_unknown: 6585
- price_unknown: 6585
- margin_factor_unknown: 6585
- market_status_closed: 2617
- capital_client_crypto_guard_blocks_direct_order: 282

## Asset Class Counts

- commodity_cfd: 66
- forex: 1
- index_cfd: 99
- stock_cfd: 5973
- unknown: 696
