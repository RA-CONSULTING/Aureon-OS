# Binance Rate Limits

This document summarizes how Binance applies rate limiting to REST API usage and order placement. It consolidates the key concepts exposed by the `/api/v3/exchangeInfo` endpoint and the accompanying response headers.

## General Information

- **Interval Encoding** – Binance uses the `intervalNum` and `interval` fields to describe how often a limiter resets. Response headers shorten the `interval` to a single letter:
  - `SECOND` → `S`
  - `MINUTE` → `M`
  - `HOUR` → `H`
  - `DAY` → `D`
- **Interval Calculation** – Combine `intervalNum` with the `interval` letter to interpret the window. For example, `intervalNum: 5` with `interval: MINUTE` (header: `5M`) means "every 5 minutes."
- **Rate Limit Types** – The `/api/v3/exchangeInfo` payload exposes the exchange-level `rateLimits` array. It reports the active limiters for:
  - `RAW_REQUESTS`
  - `REQUEST_WEIGHT`
  - `ORDERS`

A truncated example response is shown below:

```json
{
  "symbol": "BTCUSDT",
  "rateLimits": [
    {
      "rateLimitType": "ORDERS",
      "interval": "SECOND",
      "intervalNum": 10,
      "limit": 50
    },
    {
      "rateLimitType": "ORDERS",
      "interval": "DAY",
      "intervalNum": 1,
      "limit": 160000
    },
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000
    }
  ]
}
```

Requests that exceed any of the active limiters receive an HTTP **429** response.

## IP-Level Limits

Binance tracks request usage per IP address. Every REST response includes headers that surface the current usage per limiter:

- `X-MBX-USED-WEIGHT-(intervalNum)(intervalLetter)` – Current weight consumed for the given window across all request limiters.
- Each endpoint has an associated *request weight*. More complex endpoints (for example, batch requests or queries over multiple symbols) consume higher weight values per call.
- When a **429** is returned, clients must back off. Repeated violations without honoring the cooldown trigger an automated IP ban (**418** status). Ban durations scale from 2 minutes up to 3 days.
- Both **429** and **418** responses include a `Retry-After` header indicating how long to wait before resuming activity (for 418, until the ban expires).
- Because limits are enforced per IP, changing API keys does not reset the counters.

## Unfilled Order Count Limits

Order placement is throttled separately from request weight:

- Successful order responses include `X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)` headers that report how many orders were acknowledged within the interval.
- Rejected or otherwise unsuccessful orders are not guaranteed to contain the order-count headers.
- If the unfilled order quota is exceeded, the server returns **429** without a `Retry-After` header. Monitor the limit by polling `GET /api/v3/rateLimit/order`.
- Accounts whose orders consistently fill via trades can continue submitting new orders because the unfilled order count resets as fills occur. Refer to the dedicated [Spot Unfilled Order Count rules](./binance_spot_unfilled_order_count.md) for full details on how fills, cancellations, and interval resets are applied.

## Backoff Guidance

To avoid bans:

1. Track the `X-MBX-USED-WEIGHT-*` headers and pause when approaching the configured ceilings.
2. When a **429** is encountered, immediately stop issuing additional requests until the `Retry-After` interval elapses.
3. If a **418** ban occurs, wait for the `Retry-After` duration before reconnecting. Subsequent bans grow longer, so repeated violations should be avoided.

Understanding and respecting these limits ensures reliable connectivity and prevents trading interruptions on the Binance REST API.
