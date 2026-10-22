# Binance Exchange Filters Reference

This reference summarizes the Binance REST API filters that gate whether a new order or API request is considered valid. Each filter enforces a specific trading invariant. Understanding them is essential for automated strategies such as QGITA, where orders must match the exchange's rule-set on the first attempt to avoid latency penalties.

## Symbol Filters

| Filter | What it Guards | Pass Conditions | Sample `/exchangeInfo` Snippet |
|--------|----------------|-----------------|-------------------------------|
| `PRICE_FILTER` | Allowed price range and precision. | `price ≥ minPrice`, `price ≤ maxPrice`, `price % tickSize == 0` for enabled fields. | ```json
{"filterType": "PRICE_FILTER", "minPrice": "0.00000100", "maxPrice": "100000.00000000", "tickSize": "0.00000100"}
``` |
| `PERCENT_PRICE` | Max/min deviation from the weighted average price. | `price ≤ weightedAveragePrice * multiplierUp`, `price ≥ weightedAveragePrice * multiplierDown`. | ```json
{"filterType": "PERCENT_PRICE", "multiplierUp": "1.3000", "multiplierDown": "0.7000", "avgPriceMins": 5}
``` |
| `PERCENT_PRICE_BY_SIDE` | Side-specific deviation from the weighted average price. | Buy: `price ≤ weightedAveragePrice * bidMultiplierUp` and `price ≥ weightedAveragePrice * bidMultiplierDown`. Sell: `price ≤ weightedAveragePrice * askMultiplierUp` and `price ≥ weightedAveragePrice * askMultiplierDown`. | ```json
{"filterType": "PERCENT_PRICE_BY_SIDE", "bidMultiplierUp": "1.2", "bidMultiplierDown": "0.2", "askMultiplierUp": "5", "askMultiplierDown": "0.8", "avgPriceMins": 1}
``` |
| `LOT_SIZE` | Quantity range and step for limit/stop orders. | `quantity ≥ minQty`, `quantity ≤ maxQty`, `quantity % stepSize == 0`. | ```json
{"filterType": "LOT_SIZE", "minQty": "0.00100000", "maxQty": "100000.00000000", "stepSize": "0.00100000"}
``` |
| `MIN_NOTIONAL` | Minimum notional value (price × qty). | `price * quantity ≥ minNotional`. `applyToMarket` controls whether market orders use the average price over `avgPriceMins`. | ```json
{"filterType": "MIN_NOTIONAL", "minNotional": "0.00100000", "applyToMarket": true, "avgPriceMins": 5}
``` |
| `NOTIONAL` | Acceptable notional range. | `price * quantity ≥ minNotional`, `price * quantity ≤ maxNotional`. `applyMinToMarket` and `applyMaxToMarket` toggle enforcement for market orders (using the average price over `avgPriceMins`). | ```json
{"filterType": "NOTIONAL", "minNotional": "10.00000000", "applyMinToMarket": false, "maxNotional": "10000.00000000", "applyMaxToMarket": false, "avgPriceMins": 5}
``` |
| `ICEBERG_PARTS` | Maximum number of visible slices for iceberg orders. | `ceil(quantity / icebergQty) ≤ limit`. | ```json
{"filterType": "ICEBERG_PARTS", "limit": 10}
``` |
| `MARKET_LOT_SIZE` | Quantity range and step for market orders. | `quantity ≥ minQty`, `quantity ≤ maxQty`, `quantity % stepSize == 0`. | ```json
{"filterType": "MARKET_LOT_SIZE", "minQty": "0.00100000", "maxQty": "100000.00000000", "stepSize": "0.00100000"}
``` |
| `MAX_NUM_ORDERS` | Maximum count of open orders on the symbol. | `openOrders ≤ maxNumOrders`. | ```json
{"filterType": "MAX_NUM_ORDERS", "maxNumOrders": 25}
``` |
| `MAX_NUM_ALGO_ORDERS` | Maximum count of open STOP/TAKE_PROFIT style orders on the symbol. | `openAlgoOrders ≤ maxNumAlgoOrders`. | ```json
{"filterType": "MAX_NUM_ALGO_ORDERS", "maxNumAlgoOrders": 5}
``` |
| `MAX_NUM_ICEBERG_ORDERS` | Maximum count of open iceberg orders on the symbol. | `openIcebergOrders ≤ maxNumIcebergOrders`. | ```json
{"filterType": "MAX_NUM_ICEBERG_ORDERS", "maxNumIcebergOrders": 5}
``` |
| `MAX_POSITION` | Cap on the total base-asset position (free + locked + open BUY qty). | `currentPosition + orderQty ≤ maxPosition`. | ```json
{"filterType": "MAX_POSITION", "maxPosition": "10.00000000"}
``` |
| `TRAILING_DELTA` | Bounds for trailing stop offsets. | Buy-side stop types: `minTrailingAboveDelta ≤ trailingDelta ≤ maxTrailingAboveDelta`. Sell-side stop types: `minTrailingBelowDelta ≤ trailingDelta ≤ maxTrailingBelowDelta`. | ```json
{"filterType": "TRAILING_DELTA", "minTrailingAboveDelta": 10, "maxTrailingAboveDelta": 2000, "minTrailingBelowDelta": 10, "maxTrailingBelowDelta": 2000}
``` |
| `MAX_NUM_ORDER_AMENDS` | Maximum amendments allowed per order. | `amendCount ≤ maxNumOrderAmends`. | ```json
{"filterType": "MAX_NUM_ORDER_AMENDS", "maxNumOrderAmends": 10}
``` |
| `MAX_NUM_ORDER_LISTS` | Maximum open OCO/OTOCO lists per symbol. | `openOrderLists ≤ maxNumOrderLists`. | ```json
{"filterType": "MAX_NUM_ORDER_LISTS", "maxNumOrderLists": 20}
``` |

## Exchange Filters

Exchange filters apply across all symbols for the account.

| Filter | What it Guards | Pass Conditions | Sample `/exchangeInfo` Snippet |
|--------|----------------|-----------------|-------------------------------|
| `EXCHANGE_MAX_NUM_ORDERS` | Total open orders across the exchange. | `totalOpenOrders ≤ maxNumOrders`. | ```json
{"filterType": "EXCHANGE_MAX_NUM_ORDERS", "maxNumOrders": 1000}
``` |
| `EXCHANGE_MAX_NUM_ALGO_ORDERS` | Total open STOP/TAKE_PROFIT style orders. | `totalOpenAlgoOrders ≤ maxNumAlgoOrders`. | ```json
{"filterType": "EXCHANGE_MAX_NUM_ALGO_ORDERS", "maxNumAlgoOrders": 200}
``` |
| `EXCHANGE_MAX_NUM_ICEBERG_ORDERS` | Total open iceberg orders. | `totalOpenIcebergOrders ≤ maxNumIcebergOrders`. | ```json
{"filterType": "EXCHANGE_MAX_NUM_ICEBERG_ORDERS", "maxNumIcebergOrders": 10000}
``` |
| `EXCHANGE_MAX_NUM_ORDER_LISTS` | Total open order lists (OCO/OTOCO). | `totalOpenOrderLists ≤ maxNumOrderLists`. | ```json
{"filterType": "EXCHANGE_MAX_NUM_ORDER_LISTS", "maxNumOrderLists": 20}
``` |

## Asset Filters

Asset filters cover constraints tied to a specific asset, regardless of whether it appears as the base or quote asset in a symbol.

| Filter | What it Guards | Pass Conditions | Sample `/myFilters` Snippet |
|--------|----------------|-----------------|----------------------------|
| `MAX_ASSET` | Maximum transactable quantity (base asset) or notional value (quote asset) per order. | Base asset: `orderQty ≤ limit`. Quote asset: `price * orderQty ≤ limit`. | ```json
{"filterType": "MAX_ASSET", "asset": "USDC", "limit": "42.00000000"}
``` |

## Implementation Tips

- Always fetch `GET /api/v3/exchangeInfo` and (if needed) `GET /sapi/v1/capital/config/getall` at startup to cache the relevant filters for each symbol and asset.
- Normalize comparisons by rounding quantities and prices to the precision implied by each filter (e.g., `tickSize`, `stepSize`).
- For strategies that stage market orders from pre-computed limit prices, re-evaluate both the price and notional filters immediately before submission to capture rapid average-price updates.
- When paper trading against Binance data, mirror these filters in the simulator so fills faithfully reflect production rejection paths.

