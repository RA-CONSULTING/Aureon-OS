# Smart Order Routing (SOR) FAQ

> **Disclaimer:** The symbols and prices in these examples are fictional. Commissions are excluded for brevity.

Smart Order Routing (SOR) attempts to fill your order across multiple spot books
that share the same base asset and interchangeable quote assets (for example,
stablecoins pegged 1:1 to the same fiat currency). Even though the liquidity may
come from alternate books, the quote asset you receive always matches the
symbol you submitted.

When SOR is engaged, Binance scans the eligible books defined in the SOR
configuration, ranks the best available prices, and consumes liquidity until
your order is filled or the route is exhausted. If the combined liquidity cannot
satisfy the order:

- `MARKET` and `LIMIT IOC` orders immediately expire the unfilled remainder.
- `LIMIT GTC` orders post any remainder on the original symbol's book.

Successful fills include the usual order execution report plus
`"usedSor": true` and `"workingFloor": "SOR"`.

---

## How does SOR compare with standard orders?

Without SOR, a `LIMIT BUY` on `BTCUSDT` only interacts with the `BTCUSDT` book.
The same order placed with SOR can also consume liquidity from `BTCUSDC`,
`BTCUSDP`, or any other interchangeable quote assets listed in the SOR
configuration. Because SOR targets the best overall prices, it can reduce fill
costs or deliver deeper liquidity.

### Example 1 — Price improvement for partial size

SOR configuration: `BTCUSDT`, `BTCUSDC`, `BTCUSDP`

| Book | Quantity | Price | Side |
| --- | ---: | ---: | --- |
| BTCUSDT | 3 | 30,800 | ASK |
| BTCUSDT | 3 | 30,500 | ASK |
| BTCUSDC | 1 | 30,000 | ASK |
| BTCUSDC | 1 | 28,000 | ASK |
| BTCUSDP | 1 | 35,000 | ASK |
| BTCUSDP | 1 | 29,000 | ASK |

- **Standard order:** A `LIMIT GTC BUY` for 0.5 BTC at 31,000 on `BTCUSDT` fills
  against the `BTCUSDT` ask at 30,500. Fill cost: 0.5 × 30,500 = **15,250 USDT**.
- **SOR order:** The same order placed with `/api/v3/sor/order` captures the best
  ask across all eligible books (the `BTCUSDC` level at 28,000). Fill cost:
  0.5 × 28,000 = **14,000 USDT** (still settled in USDT).

### Example 2 — Aggregating liquidity across books

Using the same configuration and depth:

- **Standard order:** Buying 5 BTC at 31,000 on `BTCUSDT` consumes the two
  visible `BTCUSDT` levels for a total cost of 153,100 USDT.
- **SOR order:** The routed order sweeps the cheaper quotes first:
  1 BTC @ 28,000 (`BTCUSDC`), 1 BTC @ 29,000 (`BTCUSDP`), 1 BTC @ 30,000
  (`BTCUSDC`), and the remaining 2 BTC @ 30,500 (`BTCUSDT`). Total cost:
  **148,000 USDT**.

### Example 3 — Partial fill on a market buy

A `MARKET BUY` for 11 BTC finds only 10 BTC of total liquidity across all SOR
books. Once the aggregated depth is exhausted, the remaining 1 BTC expires. The
order status is `EXPIRED`, with `executedQty = 10` and `cummulativeQuoteQty`
reflecting the routed fills.

### Example 4 — Liquidity sourcing for sells

SOR is symmetric for sell orders. With a configuration of `BTCUSDT`, `BTCUSDC`,
and `BTCUSDP`, a `LIMIT GTC SELL` for 10 BTC at 29,000 would only sell 5 BTC on
the `BTCUSDT` book. The SOR version sells all 10 BTC by matching 5 BTC @ 35,000
and 5 BTC @ 30,000 on the `BTCUSDC` book, receiving **325,000 USDT** in total.

---

## How do I discover SOR-enabled symbols?

Query exchange information and inspect the optional `sors` array:

```http
GET /api/v3/exchangeInfo
```

```json
{
  "sors": [
    {
      "baseAsset": "BTC",
      "symbols": ["BTCUSDT", "BTCUSDC", "BTCUSDP"]
    }
  ]
}
```

If the array is omitted, SOR is currently unavailable.

---

## How do I place SOR orders?

- **REST:** `POST /api/v3/sor/order`
- **WebSocket:** `sor.order.place`

Orders accept the same parameters as standard `LIMIT` or `MARKET` orders, except
`quoteOrderQty` is not supported. `LIMIT` orders must include `timeInForce`.

Use `POST /api/v3/sor/order/test` (REST) to validate the payload without
matching against the book. WebSocket support mirrors the standard order
placement flow.

---

## What does the `workingFloor` field indicate?

Execution reports include a `workingFloor` string describing where the last
order activity occurred:

- `"SOR"` — The order interacted with alternate books through smart routing.
- `"EXCHANGE"` — The order executed or rested on the book it was submitted to.

The `usedSor` flag complements this field and is set to `true` whenever the
smart router participates in the lifecycle of the order.

---

## How are fills represented?

When SOR taps into other books, your order receives **allocations** rather than
standard trades. Allocation entries inside the `fills` array show
`"matchType": "ONE_PARTY_TRADE_REPORT"`, a negative `tradeId`, and a zero-based
`allocId`. Standard trades continue to appear with non-negative `tradeId`
values.

You can retrieve allocation history via `GET /api/v3/myAllocations` (REST) or
`myAllocations` (WebSocket). Standard trade history continues to use
`GET /api/v3/myTrades` / `myTrades`.

Example allocation entry:

```json
{
  "symbol": "BTCUSDT",
  "allocationId": 0,
  "allocationType": "SOR",
  "orderId": 2,
  "orderListId": -1,
  "price": "30000.00000000",
  "qty": "5.00000000",
  "quoteQty": "150000.00000000",
  "commission": "0.00000000",
  "commissionAsset": "BTC",
  "time": 1688379272280,
  "isBuyer": true,
  "isMaker": false,
  "isAllocator": false
}
```

---

## How do I identify past SOR orders?

Use the standard order query endpoints (`GET /api/v3/order`, `GET /api/v3/openOrders`,
`GET /api/v3/allOrders`, or their WebSocket equivalents). Orders routed through
SOR include two additional fields:

- `usedSor` — Boolean flag indicating smart-routing involvement.
- `workingFloor` — `SOR` or `EXCHANGE`, pointing to the venue of the last update.

---

## Key takeaways

- SOR can deliver better prices and deeper fills by aggregating interchangeable
  quote books.
- Unfilled remainders on `LIMIT GTC` orders rest on the original book; other
  order types expire immediately when liquidity runs out.
- Allocations document routed fills and are queryable alongside traditional
  trades.
