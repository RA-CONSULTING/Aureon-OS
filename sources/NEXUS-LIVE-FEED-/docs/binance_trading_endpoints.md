# Binance Trading REST Endpoints

This reference compiles the Spot trading surface that the Nexus tooling maps to
when orchestrating live or simulated orders against Binance. Every endpoint
below is a signed request (`TRADE` or `USER_DATA` security type) and therefore
requires an HMAC SHA-256 signature generated with the API secret plus a
millisecond `timestamp`. Optional `recvWindow` values may include up to three
decimal places (microseconds) but can never exceed `60000`.

Unless explicitly stated, all requests consume the standard `EXCHANGE_MAX_ORDERS`
and `MAX_NUM_ORDERS` filters. Pay attention to the "Unfilled Order Count" column
when orchestrating cancel/replace cycles so you do not trip the per-account rate
limits.

---

## New Order — `POST /api/v3/order`

Submit a fresh order to the matching engine. The order adds **one** entry to the
unfilled order count and is validated against symbol filters before the matching
engine accepts it.

- **Weight:** 1
- **Unfilled Order Count:** +1
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair (e.g. `BTCUSDT`). |
| `side` | ENUM | ✅ | `BUY` or `SELL`. |
| `type` | ENUM | ✅ | Order type (see Binance enumerations). |
| `timeInForce` | ENUM |  | Required for `LIMIT`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT_LIMIT`, `LIMIT_MAKER` with iceberg. |
| `quantity` | DECIMAL |  | Base asset quantity. Required for most order types. |
| `quoteOrderQty` | DECIMAL |  | Quote asset quantity (MARKET only). |
| `price` | DECIMAL |  | Limit price. Mandatory for `LIMIT`, `LIMIT_MAKER`, stop-limit variants unless pegged. |
| `newClientOrderId` | STRING |  | Unique identifier among open orders. |
| `strategyId` | LONG |  | Optional strategy label. |
| `strategyType` | INT |  | Must be ≥ `1000000`. |
| `stopPrice` | DECIMAL |  | Trigger price for stop/TP orders. |
| `trailingDelta` | LONG |  | Trailing stop activation delta. |
| `icebergQty` | DECIMAL |  | Iceberg quantity (requires `timeInForce=GTC`). |
| `newOrderRespType` | ENUM |  | `ACK`, `RESULT`, or `FULL` response payload. |
| `selfTradePreventionMode` | ENUM |  | Symbol-configured STP mode. |
| `pegPriceType` | ENUM |  | `PRIMARY_PEG` or `MARKET_PEG`. |
| `pegOffsetValue` | INT |  | Peg level offset (≤ 100). |
| `pegOffsetType` | ENUM |  | Only `PRICE_LEVEL` supported. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

### Additional Mandatory Parameters by Type

| Type | Additional Requirements |
| --- | --- |
| `LIMIT` | `timeInForce`, `quantity`, `price` |
| `MARKET` | `quantity` **or** `quoteOrderQty` |
| `STOP_LOSS`, `TAKE_PROFIT` | `quantity` and (`stopPrice` or `trailingDelta`) |
| `STOP_LOSS_LIMIT`, `TAKE_PROFIT_LIMIT` | `timeInForce`, `quantity`, `price`, and (`stopPrice` or `trailingDelta`) |
| `LIMIT_MAKER` | `quantity`, `price` |

MARKET orders using `quoteOrderQty` respect the `LOT_SIZE` filter and compute the
base quantity using the prevailing liquidity. Pegged orders may omit `price`
when `pegPriceType` is supplied; otherwise `price` remains mandatory.

**Response Types**

- `ACK` — order metadata only.
- `RESULT` — includes the working order snapshot.
- `FULL` — extends `RESULT` with individual fill breakdowns when available.

Reference the official payload examples in the Binance documentation for each
response variant.

---

## Test New Order — `POST /api/v3/order/test`

Validates authentication, parameters, and request signature without touching the
matching engine.

- **Weight:** 1 (`computeCommissionRates=false`), 20 (`true`)
- **Data Source:** Memory

Accepts all parameters from `POST /api/v3/order` plus:

| Name | Type | Description |
| --- | --- | --- |
| `computeCommissionRates` | BOOLEAN | When `true`, the response returns maker/taker/tax/discount commission schedules. |

Responses are empty `{}` unless commission computation is requested.

---

## Query Order — `GET /api/v3/order`

Retrieve the latest status of a single order. Either `orderId` or
`origClientOrderId` must be supplied.

- **Weight:** 4
- **Data Source:** Memory ⇒ Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair to query. |
| `orderId` | LONG |  | Binance order identifier. |
| `origClientOrderId` | STRING |  | Client-supplied identifier. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

When both `orderId` and `origClientOrderId` are present, Binance resolves the
`orderId` first then verifies the `origClientOrderId`. Some legacy orders may
omit or return negative `cummulativeQuoteQty` values when the data has expired.

---

## Cancel Order — `DELETE /api/v3/order`

Cancel a single open order. For best latency, pass only `orderId`.

- **Weight:** 1
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `orderId` | LONG |  | Order identifier to cancel. |
| `origClientOrderId` | STRING |  | Alternate lookup key. |
| `newClientOrderId` | STRING |  | Identifier for the cancel request. |
| `cancelRestrictions` | ENUM |  | `ONLY_NEW` or `ONLY_PARTIALLY_FILLED`. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

A cancel fails with `-1145` if `cancelRestrictions` is invalid or `-2011` when
the order status violates the restriction.

---

## Cancel All Open Orders — `DELETE /api/v3/openOrders`

Bulk cancel every open order on a symbol, including orders that belong to an
order list.

- **Weight:** 1
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

The response returns an array covering each cancelled order plus any order list
reports.

---

## Cancel Replace Order — `POST /api/v3/order/cancelReplace`

Atomically cancel an existing order and (optionally) place a replacement order.
Filter validation occurs before cancellation is attempted. Even when the new
order is not attempted, the unfilled order count increases by one.

- **Weight:** 1
- **Unfilled Order Count:** +1
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `side` | ENUM | ✅ | Side of the new order. |
| `type` | ENUM | ✅ | New order type. |
| `cancelReplaceMode` | ENUM | ✅ | `STOP_ON_FAILURE` or `ALLOW_FAILURE`. |
| `timeInForce` | ENUM |  | Depends on new order type. |
| `quantity` | DECIMAL |  | Quantity for the new order. |
| `quoteOrderQty` | DECIMAL |  | Quote quantity (MARKET only). |
| `price` | DECIMAL |  | Limit price when required. |
| `cancelNewClientOrderId` | STRING |  | Identifier for the cancel request. |
| `cancelOrigClientOrderId` | STRING |  | Client order ID of the order to cancel. |
| `cancelOrderId` | LONG |  | Binance order ID to cancel. |
| `newClientOrderId` | STRING |  | Identifier for the new order. |
| `strategyId` | LONG |  | Optional strategy label. |
| `strategyType` | INT |  | Must be ≥ `1000000`. |
| `stopPrice` | DECIMAL |  | Trigger price for stop/TP orders. |
| `trailingDelta` | LONG |  | Trailing delta. |
| `icebergQty` | DECIMAL |  | Iceberg quantity (requires `GTC`). |
| `newOrderRespType` | ENUM |  | `ACK`, `RESULT`, or `FULL`. |
| `selfTradePreventionMode` | ENUM |  | Symbol-configured STP mode. |
| `cancelRestrictions` | ENUM |  | `ONLY_NEW` or `ONLY_PARTIALLY_FILLED`. |
| `orderRateLimitExceededMode` | ENUM |  | `DO_NOTHING` (default) or `CANCEL_ONLY`. |
| `pegPriceType` | ENUM |  | Peg type for the new order. |
| `pegOffsetValue` | INT |  | Peg price offset (≤ 100). |
| `pegOffsetType` | ENUM |  | Only `PRICE_LEVEL`. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

Response semantics vary by `cancelResult` and `newOrderResult`. Failures surface
error codes `-2021` (partial) or `-2022` (full failure). When
`orderRateLimitExceededMode=DO_NOTHING` and the unfilled order count is exceeded,
Binance returns `-1015`. With `CANCEL_ONLY`, the cancel succeeds but the new
order fails when limits are breached.

---

## Order Amend Keep Priority — `PUT /api/v3/order/amend/keepPriority`

Reduce the quantity of an existing order without losing book priority. The
operation does **not** consume additional order count quota.

- **Weight:** 4
- **Unfilled Order Count:** +0
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `orderId` | LONG | ✅* | Order identifier. Required if `origClientOrderId` absent. |
| `origClientOrderId` | STRING | ✅* | Client order identifier. Required if `orderId` absent. |
| `newClientOrderId` | STRING |  | Replacement client order ID (optional). |
| `newQty` | DECIMAL | ✅ | New order quantity. Must be > 0 and < original quantity. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

Responses include the amended order snapshot, and when the order is part of an
order list, an accompanying `listStatus` block.

---

## Order Lists

### OCO — `POST /api/v3/orderList/oco`

Create a One-Cancels-the-Other pair (above + below orders). The request consumes
**two** order counts.

- **Weight:** 1
- **Unfilled Order Count:** +2
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `listClientOrderId` | STRING |  | Unique identifier for the order list. |
| `side` | ENUM | ✅ | `BUY` or `SELL`. |
| `quantity` | DECIMAL | ✅ | Base quantity for both orders. |
| `aboveType` | ENUM | ✅ | `STOP_LOSS_LIMIT`, `STOP_LOSS`, `LIMIT_MAKER`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT`. |
| `aboveClientOrderId` | STRING |  | Client ID for the above order. |
| `aboveIcebergQty` | DECIMAL |  | Requires `aboveTimeInForce=GTC`. |
| `abovePrice` | DECIMAL |  | Limit price when `aboveType` supports it. |
| `aboveStopPrice` | DECIMAL |  | Stop trigger (mandatory with/without `aboveTrailingDelta`). |
| `aboveTrailingDelta` | LONG |  | Trailing delta option. |
| `aboveTimeInForce` | ENUM |  | Required for stop-limit/TP-limit orders. |
| `aboveStrategyId` | LONG |  | Strategy metadata. |
| `aboveStrategyType` | INT |  | Must be ≥ `1000000`. |
| `abovePegPriceType` | ENUM |  | Peg type. |
| `abovePegOffsetType` | ENUM |  | Peg offset type. |
| `abovePegOffsetValue` | INT |  | Peg offset value. |
| `belowType` | ENUM | ✅ | `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT`. |
| `belowClientOrderId` | STRING |  | Client ID for the below order. |
| `belowIcebergQty` | DECIMAL |  | Requires `belowTimeInForce=GTC`. |
| `belowPrice` | DECIMAL |  | Limit price when supported. |
| `belowStopPrice` | DECIMAL |  | Stop trigger (mandatory with/without `belowTrailingDelta`). |
| `belowTrailingDelta` | LONG |  | Trailing delta option. |
| `belowTimeInForce` | ENUM |  | Required for stop-limit/TP-limit. |
| `belowStrategyId` | LONG |  | Strategy metadata. |
| `belowStrategyType` | INT |  | Must be ≥ `1000000`. |
| `belowPegPriceType` | ENUM |  | Peg type. |
| `belowPegOffsetType` | ENUM |  | Peg offset type. |
| `belowPegOffsetValue` | INT |  | Peg offset value. |
| `newOrderRespType` | ENUM |  | `ACK`, `RESULT`, or `FULL`. |
| `selfTradePreventionMode` | ENUM |  | Symbol-configured STP mode. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

SELL-side OCOs require `abovePrice` (or `aboveStopPrice`) > last traded price >
`belowStopPrice`. The inequalities invert for BUY-side requests.

### OTO — `POST /api/v3/orderList/oto`

Submit a One-Triggers-the-Other list consisting of a working `LIMIT`/`LIMIT_MAKER`
order and a pending order released only after the working order fills. Consumes
**two** order counts.

- **Weight:** 1
- **Unfilled Order Count:** +2
- **Data Source:** Matching Engine

Key parameters (non-exhaustive):

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `listClientOrderId` | STRING |  | Unique identifier for the order list. |
| `newOrderRespType` | ENUM |  | `ACK`, `RESULT`, or `FULL`. |
| `selfTradePreventionMode` | ENUM |  | Symbol-configured STP mode. |
| `workingType` | ENUM | ✅ | `LIMIT` or `LIMIT_MAKER`. |
| `workingSide` | ENUM | ✅ | Side of the working order. |
| `workingClientOrderId` | STRING |  | Client ID for the working order. |
| `workingPrice` | DECIMAL | ✅ | Limit price. |
| `workingQuantity` | DECIMAL | ✅ | Quantity for the working order. |
| `workingIcebergQty` | DECIMAL |  | Requires `GTC` or `LIMIT_MAKER`. |
| `workingTimeInForce` | ENUM |  | Mandatory when `workingType=LIMIT`. |
| `workingStrategyId` | LONG |  | Strategy metadata. |
| `workingStrategyType` | INT |  | ≥ `1000000`. |
| `workingPegPriceType` | ENUM |  | Peg type. |
| `workingPegOffsetType` | ENUM |  | Peg offset type. |
| `workingPegOffsetValue` | INT |  | Peg offset value. |
| `pendingType` | ENUM | ✅ | Any order type except MARKET with `quoteOrderQty`. |
| `pendingSide` | ENUM | ✅ | Side of the pending order. |
| `pendingClientOrderId` | STRING |  | Client ID for the pending order. |
| `pendingPrice` | DECIMAL |  | Required for limit variants. |
| `pendingStopPrice` | DECIMAL |  | Required for stop/TP variants. |
| `pendingTrailingDelta` | DECIMAL |  | Trailing delta option. |
| `pendingQuantity` | DECIMAL | ✅ | Quantity for the pending order. |
| `pendingIcebergQty` | DECIMAL |  | Requires `pendingTimeInForce=GTC` or `LIMIT_MAKER`. |
| `pendingTimeInForce` | ENUM |  | Mandatory for limit variants. |
| `pendingStrategyId` | LONG |  | Strategy metadata. |
| `pendingStrategyType` | INT |  | ≥ `1000000`. |
| `pendingPegPriceType` | ENUM |  | Peg type. |
| `pendingPegOffsetType` | ENUM |  | Peg offset type. |
| `pendingPegOffsetValue` | INT |  | Peg offset value. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

### OTOCO — `POST /api/v3/orderList/otoco`

Submit a One-Triggers-One-Cancels-the-Other list: one working order plus two
pending orders that form an OCO once triggered. Consumes **three** order counts.

- **Weight:** 1
- **Unfilled Order Count:** +3
- **Data Source:** Matching Engine

The parameter surface mirrors OTO plus the OCO-specific knobs for `pendingAbove`
and `pendingBelow`. Follow the same stop/price inequality rules as the OCO
section.

### Cancel Order List — `DELETE /api/v3/orderList`

Cancel every order in an OCO/OTO/OTOCO list.

- **Weight:** 1
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `orderListId` | LONG | ✅* | Binance list ID. Required if `listClientOrderId` missing. |
| `listClientOrderId` | STRING | ✅* | Client list ID. Required if `orderListId` missing. |
| `newClientOrderId` | STRING |  | Identifier for the cancel request. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

Canceling a single child order also cancels the entire list. When both lookup
fields are provided, Binance validates `orderListId` first and then verifies the
`listClientOrderId` matches.

---

## Smart Order Routing (SOR)

### New Order — `POST /api/v3/sor/order`

Place an order that leverages Binance's smart order routing. Only `LIMIT` and
`MARKET` types are supported and `quoteOrderQty` is **not** accepted.

- **Weight:** 1
- **Unfilled Order Count:** +1
- **Data Source:** Matching Engine

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair. |
| `side` | ENUM | ✅ | `BUY` or `SELL`. |
| `type` | ENUM | ✅ | `LIMIT` or `MARKET`. |
| `timeInForce` | ENUM |  | Required for `LIMIT` orders. |
| `quantity` | DECIMAL | ✅ | Base asset quantity. |
| `price` | DECIMAL |  | Limit price when `type=LIMIT`. |
| `newClientOrderId` | STRING |  | Unique identifier among open orders. |
| `strategyId` | LONG |  | Optional strategy metadata. |
| `strategyType` | INT |  | Must be ≥ `1000000`. |
| `icebergQty` | DECIMAL |  | Iceberg quantity for `LIMIT` orders (`GTC` only). |
| `newOrderRespType` | ENUM |  | `ACK`, `RESULT`, or `FULL` (default `FULL`). |
| `selfTradePreventionMode` | ENUM |  | Symbol-configured STP mode. |
| `recvWindow` | DECIMAL |  | Optional; ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

Successful responses echo the standard order object plus `usedSor=true` and, when
applicable, a `fills` array labeled with `matchType` and `allocId` fields.

### Test Order — `POST /api/v3/sor/order/test`

Validate SOR order parameters and signature without sending the order to the
matching engine.

- **Weight:** 1 (`computeCommissionRates=false`), 20 (`true`)
- **Data Source:** Memory

Supports `computeCommissionRates` with the same semantics as the standard order
test endpoint.

---

## Conditional Response Fields

Order placement, query, and cancellation responses may include additional fields
when specific criteria are met:

- `icebergQty` — Present when an iceberg quantity is used.
- `preventedMatchId`, `preventedQuantity` — Show when an order expired due to STP
  (self-trade prevention).
- `stopPrice`, `trailingDelta`, `trailingTime` — Returned for stop-loss,
  take-profit, and trailing stop orders.
- `strategyId`, `strategyType` — Echoed back when supplied in the request.
- `usedSor`, `workingFloor` — Included for SOR activity.
- Pegged order fields (`pegPriceType`, `pegOffsetType`, `pegOffsetValue`,
  `peggedPrice`) — Present once the peg price resolves.

Consult this section when parsing execution reports or building client-side data
models so optional attributes are handled gracefully.
