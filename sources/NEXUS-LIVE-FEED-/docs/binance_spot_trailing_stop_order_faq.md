# Spot Trailing Stop Order FAQ

## What is a trailing stop order?
A trailing stop is a contingent order whose trigger price moves dynamically with market price changes. On the Spot API, the required change to trigger the order is expressed in `trailingDelta` and measured in basis points (BIPS). Trailing stop orders allow unlimited movement in a favorable direction but restrict unfavorable movement: the order fires once price reverses by the configured delta from the tracked extreme.

- **Buy orders:** Lower prices are beneficial. Unlimited price decreases are tracked, and the order triggers after the market rises by the specified delta from the lowest price observed since submission.
- **Sell orders:** Higher prices are beneficial. Unlimited price increases are tracked, and the order triggers after the market falls by the specified delta from the highest price observed since submission.

## What are BIPS?
Basis points (BIPS) measure percentage change. A single BIP equals 0.01% (a multiplier of 0.0001). Common conversions are:

| BIPS | Percentage | Multiplier |
| ---: | :--- | ---: |
| 1 | 0.01% | 0.0001 |
| 10 | 0.1% | 0.001 |
| 100 | 1% | 0.01 |
| 1000 | 10% | 0.1 |

For example, a `STOP_LOSS` sell order with `trailingDelta = 100` triggers after the highest price falls by 1% (100 BIPS).

## What order types can use trailing stops?
Trailing stops are available on contingent order types: `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, and `TAKE_PROFIT_LIMIT`. One-cancels-the-other (OCO) orders also support trailing stops on the contingent leg; when the trailing condition triggers, the limit leg is canceled.

## How do I place a trailing stop order?
Submit the same parameters as the corresponding contingent order and include an additional `trailingDelta` value that satisfies the symbol's `TRAILING_DELTA` filter. The `stopPrice` parameter becomes optional:

- If `stopPrice` is supplied, price tracking begins only after the market trades at or through that value.
- If `stopPrice` is omitted, tracking begins immediately on the next trade.

## What price movements trigger a trailing stop order?

| Trailing order type | Side | Stop price condition | Market price movement required |
| --- | --- | --- | --- |
| `TAKE_PROFIT` | SELL | Market price ≥ `stopPrice` | Decrease from tracked maximum |
| `TAKE_PROFIT_LIMIT` | SELL | Market price ≥ `stopPrice` | Decrease from tracked maximum |
| `STOP_LOSS` | SELL | Market price ≤ `stopPrice` | Decrease from tracked maximum |
| `STOP_LOSS_LIMIT` | SELL | Market price ≤ `stopPrice` | Decrease from tracked maximum |
| `STOP_LOSS` | BUY | Market price ≥ `stopPrice` | Increase from tracked minimum |
| `STOP_LOSS_LIMIT` | BUY | Market price ≥ `stopPrice` | Increase from tracked minimum |
| `TAKE_PROFIT` | BUY | Market price ≤ `stopPrice` | Increase from tracked minimum |
| `TAKE_PROFIT_LIMIT` | BUY | Market price ≤ `stopPrice` | Increase from tracked minimum |

## How do I satisfy the `TRAILING_DELTA` filter?

- For `STOP_LOSS BUY`, `STOP_LOSS_LIMIT BUY`, `TAKE_PROFIT SELL`, and `TAKE_PROFIT_LIMIT SELL` orders, ensure `minTrailingAboveDelta ≤ trailingDelta ≤ maxTrailingAboveDelta`.
- For `STOP_LOSS SELL`, `STOP_LOSS_LIMIT SELL`, `TAKE_PROFIT BUY`, and `TAKE_PROFIT_LIMIT BUY` orders, ensure `minTrailingBelowDelta ≤ trailingDelta ≤ maxTrailingBelowDelta`.

## Trailing stop scenarios
### Scenario A — Trailing Stop Loss Limit Buy
1. At 12:01:00 the market trades at 40,000. A `STOP_LOSS_LIMIT` buy order is submitted with `stopPrice = 44,000`, `trailingDelta = 500` (5%), and `price = 45,000`.
2. Prices fall to 37,000 before the stop is touched. Because tracking has not yet begun, these moves are ignored.
3. At 12:02:00 trades reach the stop price (44,000), beginning tracking. The initial low is 44,000; the trigger price is 44,000 × 1.05 = 46,200.
4. Prices rise to 46,000 and then fall to 42,000, updating the tracked low.
5. When prices rebound to 44,100 (42,000 × 1.05), the order triggers and works at its 45,000 limit.

### Scenario B — Trailing Stop Loss Limit Sell
1. At 12:01:00 the market trades at 40,000. A `STOP_LOSS_LIMIT` sell order is submitted with `stopPrice = 39,000`, `trailingDelta = 1000` (10%), and `price = 38,000`.
2. After rising to 41,500, the market drops to the stop price, beginning tracking with a high of 39,000.
3. The tracked high increases to 41,000. When price falls to 36,900 (41,000 × 0.90), the order triggers and works at 38,000.

### Scenario C — Trailing Take Profit Limit Buy
1. At 12:01:00 the market trades at 40,000. A `TAKE_PROFIT_LIMIT` buy order is submitted with `stopPrice = 38,000`, `trailingDelta = 850` (8.5%), and `price = 38,500`.
2. Once the stop price trades, tracking begins with a low of 38,000, later updated to 37,000.
3. When the market rallies to 40,145 (37,000 × 1.085), the order triggers and works at 38,500.

### Scenario D — Trailing Take Profit Limit Sell
1. At 12:01:00 the market trades at 40,000. A `TAKE_PROFIT_LIMIT` sell order is submitted with `stopPrice = 42,000`, `trailingDelta = 750` (7.5%), and `price = 41,000`.
2. Tracking begins at 42,000 and is later updated to a high of 46,500.
3. When price declines to 43,012.5 (46,500 × 0.925), the order triggers and works at 41,000.

### Scenario E — Trailing Stop Order Without a Stop Price
1. At 12:01:00 the market trades at 40,000. A `STOP_LOSS_LIMIT` sell order is submitted without a `stopPrice`, `trailingDelta = 700` (7%), and `price = 39,000`. Tracking begins immediately.
2. The tracked high updates to 45,500. When the market falls to 42,315 (45,500 × 0.93), the order triggers and works at 39,000.

## Trailing stop order examples
Assume the last price is 40,000.

### STOP_LOSS_LIMIT buy with 5% trailing stop
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=BUY&type=STOP_LOSS_LIMIT&timeInForce=GTC&quantity=0.01&price=42000&trailingDelta=500&timestamp=<timestamp>&signature=<signature>
```

With an explicit stop price of 43,000:
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=BUY&type=STOP_LOSS_LIMIT&timeInForce=GTC&quantity=0.01&price=42000&stopPrice=43000&trailingDelta=500&timestamp=<timestamp>&signature=<signature>
```

### STOP_LOSS_LIMIT sell with 2.5% trailing stop
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=SELL&type=STOP_LOSS_LIMIT&timeInForce=GTC&quantity=0.01&price=37500&trailingDelta=250&timestamp=<timestamp>&signature=<signature>
```

With an explicit stop price of 39,000:
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=SELL&type=STOP_LOSS_LIMIT&timeInForce=GTC&quantity=0.01&price=37500&stopPrice=39000&trailingDelta=250&timestamp=<timestamp>&signature=<signature>
```

### TAKE_PROFIT_LIMIT buy with 5% trailing stop
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=BUY&type=TAKE_PROFIT_LIMIT&timeInForce=GTC&quantity=0.01&price=38000&trailingDelta=500&timestamp=<timestamp>&signature=<signature>
```

With an explicit stop price of 36,000:
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=BUY&type=TAKE_PROFIT_LIMIT&timeInForce=GTC&quantity=0.01&price=38000&stopPrice=36000&trailingDelta=500&timestamp=<timestamp>&signature=<signature>
```

### TAKE_PROFIT_LIMIT sell with 1.75% trailing stop
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=SELL&type=TAKE_PROFIT_LIMIT&timeInForce=GTC&quantity=0.01&price=41500&trailingDelta=175&timestamp=<timestamp>&signature=<signature>
```

With an explicit stop price of 42,500:
```http
POST https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=SELL&type=TAKE_PROFIT_LIMIT&timeInForce=GTC&quantity=0.01&price=41500&stopPrice=42500&trailingDelta=175&timestamp=<timestamp>&signature=<signature>
```
