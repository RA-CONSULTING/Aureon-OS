# Aureon Kraken Tradable Asset Registry

Generated: 2026-05-15T14:52:23.492505+00:00
Schema: aureon-kraken-tradable-asset-registry-v1

This registry records Kraken spot and margin pair metadata, minimum order/cost evidence, maker/taker fee tiers, leverage availability, and the Aureon code route used to buy, sell, protect, or reduce-only close crypto trades. It does not submit orders; live orders still pass through runtime gates.

## Summary

- Total Kraken pairs discovered: 1540
- Ticker enriched this run: 50 / budget 50
- Spot trade ready: 50
- Margin-capable pairs: 265
- Margin trade ready: 10
- Cost known: 1540
- Fee tier known: 1540
- Audit status: passed (14/14)

## Execution Route

- SPOT BUY: `KrakenClient.place_market_order(symbol, "buy", quantity=base_qty)` via `POST /0/private/AddOrder`
- SPOT SELL: `KrakenClient.place_market_order(symbol, "sell", quantity=base_qty)` via `POST /0/private/AddOrder`
- LIMIT/POST-ONLY: `KrakenClient.place_limit_order(symbol, side, quantity, price, post_only=True)`
- TAKE PROFIT: `KrakenClient.place_take_profit_order(symbol, close_side, quantity, take_profit_price)`
- MARGIN: `KrakenClient.place_margin_order(symbol, side, quantity, leverage, take_profit=target, stop_loss=stop)`
- REDUCE-ONLY CLOSE: `KrakenClient.close_margin_position(symbol, close_side, volume)`

## Official Basis

- Kraken AssetPairs supplies tradable pairs, precision, order minimums, and leverage evidence.
- Kraken AddOrder is the REST order route for spot, margin, limit, stop, and take-profit orders.
- Kraken trading fees depend on pair, 30-day volume, and maker/taker execution.
- Margin trades add opening and rollover fees in addition to normal trade fees.

## Audit Checks

- PASS schema_version: aureon-kraken-tradable-asset-registry-v1
- PASS official_basis_present: 4 official/source URLs
- PASS asset_pairs_present: 1540 pairs
- PASS ticker_budget_declared: budget=50
- PASS spot_route_declared: spot buy/sell routes
- PASS take_profit_route_declared: take-profit route
- PASS margin_route_declared: margin long/short/close routes
- PASS asset_route_fields_present: sampled first 50 assets
- PASS fee_evidence_present: 1540 pairs with fees
- PASS cost_evidence_present: 1540 pairs with cost minimums
- PASS margin_evidence_present: 265 margin-capable pairs
- PASS survival_policy_present: pending-order survival policy
- PASS submission_default_guarded: pending submission off unless explicitly enabled
- PASS secret_key_scan: no credential-like keys emitted

## Top Blockers

- ticker_not_sampled_budget: 1490

## Asset Class Counts

- crypto_cross_pair: 61
- crypto_fiat_or_stable_pair: 1473
- crypto_spot_pair: 6
