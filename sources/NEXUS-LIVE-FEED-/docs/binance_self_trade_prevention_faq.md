# Self Trade Prevention (STP) FAQ

> **Disclaimer**
>
> The commissions and prices used here are fictional and do not imply anything about the actual setup on the live exchange.

## What is Self Trade Prevention?

Self Trade Prevention (STP) stops a user's orders—or orders submitted by accounts that share the same `tradeGroupId`—from matching with each other.

## What defines a self-trade?

A self-trade can be triggered in either of the following situations:

- The order would trade against another order from the same account.
- The order would trade against an order from an account that shares the same `tradeGroupId`.

## What happens when STP is triggered?

Five modes determine how the exchange handles a potential self-trade. The mode on the _taker_ order always controls the outcome once the trade is evaluated.

- **`NONE`** – The order bypasses STP entirely; accounts and trade group IDs are ignored and the orders match normally.
- **`EXPIRE_TAKER`** – The taker order's remaining quantity expires immediately, preventing the trade.
- **`EXPIRE_MAKER`** – The maker order's remaining quantity expires immediately, preventing the trade.
- **`EXPIRE_BOTH`** – Both maker and taker orders have their remaining quantities expired immediately.
- **`DECREMENT`** – The prevented quantity is added to both orders. The smaller order expires (or both if their remaining quantities are equal).

Because the taker order's mode governs the action, an order that sits on the book with a specific mode will have that mode ignored once another taker attempts to trade against it.

## What is a Trade Group ID?

Accounts that share a `tradeGroupId` are treated as a single trade group for STP purposes. A user can check an account's `tradeGroupId` via:

- `GET /api/v3/account` (REST API)
- `account.status` (WebSocket API)

The `tradeGroupId` also appears in responses from `GET /api/v3/preventedMatches` and the WebSocket stream `myPreventedMatches`. A value of `-1` indicates that the account is not in a trade group, so STP will only compare orders from the same account.

## What is a prevented match?

A prevented match records any potential self-trade that STP blocked. Prevented quantities on the affected orders increase, and one or both orders may expire. This is _not_ a trade—the orders never execute—but it documents what would have matched.

Retrieve prevented matches with:

- `GET /api/v3/preventedMatches` (REST API)
- `myPreventedMatches` (WebSocket API)

**Sample response**

```json
[
  {
    "symbol": "BTCDUSDT",
    "preventedMatchId": 8,
    "takerOrderId": 12,
    "makerOrderId": 10,
    "tradeGroupId": 1,
    "selfTradePreventionMode": "EXPIRE_BOTH",
    "price": "50.00000000",
    "takerPreventedQuantity": "1.00000000",
    "makerPreventedQuantity": "10.00000000",
    "transactTime": 1663190634060
  }
]
```

## What is prevented quantity?

Prevented quantity tracks how much of an order was expired because of STP events. For `EXPIRE_TAKER`, `EXPIRE_MAKER`, and `EXPIRE_BOTH`, the entire remaining quantity of the affected order is removed. Execution reports for orders involved in STP may contain the following fields:

```json
{
  "A": "3.000000", // Prevented Quantity (cumulative)
  "B": "3.000000"  // Last Prevented Quantity (per event)
}
```

- Field `B` appears when `executionType` is `TRADE_PREVENTION` and reports the quantity removed by that specific STP event.
- Field `A` is the cumulative prevented quantity over the order's lifetime. For `EXPIRE_*` modes it will equal `B`.

REST API responses for orders that expired because of STP include a `preventedQuantity` field with the same cumulative value.

While an order remains open, the following relationship holds:

```
original order quantity - executed quantity - prevented quantity = quantity available for further execution
```

When the available quantity reaches zero, the order leaves the book and transitions to `EXPIRED_IN_MATCH`, `FILLED`, or `EXPIRED`.

## How do I know which symbol uses STP?

Each symbol specifies its default STP mode and allowed modes:

- `defaultSelfTradePreventionMode` – Applied when an order omits the `selfTradePreventionMode` field.
- `allowedSelfTradePreventionModes` – Enumerates the valid STP modes for that symbol.

Example configuration:

```json
{
  "defaultSelfTradePreventionMode": "NONE",
  "allowedSelfTradePreventionModes": [
    "NONE",
    "EXPIRE_TAKER",
    "EXPIRE_BOTH"
  ]
}
```

If an order omits `selfTradePreventionMode`, the symbol defaults to `NONE`. Supplying any of the allowed modes explicitly is accepted. Attempting to use an unsupported mode—for example, sending `EXPIRE_MAKER` in the configuration above—returns error `-1013` with the message `"This symbol does not allow the specified self-trade prevention mode."`

## How do I know if an order expired due to STP?

Orders that expire because of STP report the status `EXPIRED_IN_MATCH`.

## Scenario walkthroughs

All examples below assume the orders come from the same account unless noted otherwise.

### Scenario A — No STP (mode `NONE`)

- **Maker**: `BUY`, `LIMIT`, quantity `1`, price `1`, `selfTradePreventionMode=NONE`
- **Taker**: `SELL`, `LIMIT`, quantity `1`, price `1`, `selfTradePreventionMode=NONE`

Result: No STP triggers and the orders match. Both orders end with status `FILLED`.

### Scenario B — Taker uses `EXPIRE_MAKER`

- **Maker 1**: `BUY`, `LIMIT`, quantity `1.2`, price `1.2`, mode `NONE`
- **Maker 2**: `BUY`, `LIMIT`, quantity `1.3`, price `1.1`, mode `NONE`
- **Maker 3**: `BUY`, `LIMIT`, quantity `8.1`, price `1`, mode `NONE`
- **Taker**: `SELL`, `LIMIT`, quantity `3`, price `1`, mode `EXPIRE_MAKER`

Result: The three maker orders each expire with status `EXPIRED_IN_MATCH`, recording their prevented quantities. The taker order remains on the book with status `NEW`, including a list of prevented matches.

### Scenario C — Taker uses `EXPIRE_TAKER`

- **Maker 1**: `BUY`, `LIMIT`, quantity `1.2`, price `1.2`, mode `NONE`
- **Maker 2**: `BUY`, `LIMIT`, quantity `1.3`, price `1.1`, mode `NONE`
- **Maker 3**: `BUY`, `LIMIT`, quantity `8.1`, price `1`, mode `NONE`
- **Taker**: `SELL`, `LIMIT`, quantity `3`, price `1`, mode `EXPIRE_TAKER`

Result: The taker order expires (`EXPIRED_IN_MATCH`) with its full quantity prevented. The maker orders remain untouched on the book.

### Scenario D — Taker uses `EXPIRE_BOTH`

- **Maker**: `BUY`, `LIMIT`, quantity `1`, price `1`, mode `NONE`
- **Taker**: `SELL`, `LIMIT`, quantity `3`, price `1`, mode `EXPIRE_BOTH`

Result: Both orders expire with status `EXPIRED_IN_MATCH`, each recording their prevented quantities under the same `preventedMatchId`.

### Scenario E — Maker mode ignored; taker uses `EXPIRE_TAKER`

- **Maker**: `BUY`, `LIMIT`, quantity `1`, price `1`, mode `EXPIRE_MAKER`
- **Taker**: `SELL`, `LIMIT`, quantity `1`, price `1`, mode `EXPIRE_TAKER`

Result: The taker order's mode controls the outcome, so it expires with status `EXPIRED_IN_MATCH`. The maker order stays on the book.

### Scenario F — Market taker uses `EXPIRE_MAKER`

- **Maker**: `BUY`, `LIMIT`, quantity `1`, price `1`, mode `NONE`
- **Taker**: `SELL`, `MARKET`, quantity `1`, mode `EXPIRE_MAKER`

Result: The maker order expires due to STP. The taker market order also expires with status `EXPIRED` because no other liquidity was available after preventing the self-trade.

### Scenario G — Taker uses `DECREMENT`

- **Maker**: `BUY`, `LIMIT`, quantity `6`, price `2`, mode `NONE`
- **Taker**: `SELL`, `LIMIT`, quantity `2`, price `2`, mode `DECREMENT`

Result: Both orders have their prevented quantities increased by `2`. The taker order expires (`EXPIRED_IN_MATCH`) because its entire quantity was prevented, while the maker order remains with reduced available quantity.

