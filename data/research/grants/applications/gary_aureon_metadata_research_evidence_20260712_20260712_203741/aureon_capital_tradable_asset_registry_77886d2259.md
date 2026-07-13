# Aureon Capital Tradable Asset Registry

Generated: 2026-05-21T14:21:52.432491+00:00
Schema: aureon-capital-tradable-asset-registry-v1

This registry records Capital.com market metadata and the Aureon code route used to buy, sell, or close a CFD. It does not submit orders; live orders still pass through the existing runtime, portfolio, confidence, and exchange gates.

## Summary

- Total Capital markets discovered: 0
- Snapshot enriched this run: 0 / budget 100
- Trade route configured: 0
- Trade ready with sampled cost and margin: 0
- Cost known: 0
- Margin known: 0

## Execution Route

- BUY: `CapitalClient.place_market_order(symbol, "BUY", size)` via `POST /positions`
- SELL: `CapitalClient.place_market_order(symbol, "SELL", size)` via `POST /positions`
- CLOSE: `CapitalClient.close_position(deal_id)` via `DELETE /positions/{dealId}`

## Top Blockers


## Asset Class Counts

