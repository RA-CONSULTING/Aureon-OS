# Spot Unfilled Order Count Rules

Binance enforces a dedicated *unfilled order* limiter alongside the standard request-weight and raw-request quotas. The limiter ensures that accounts cannot flood the order book with orders that never trade while allowing efficient traders to keep placing new orders.

## Discovering the Current Limits

You can inspect the live configuration by querying the exchange metadata endpoints:

- **REST** – `GET /api/v3/exchangeInfo`
- **WebSocket** – `exchangeInfo`
- **FIX** – `LimitQuery<XLQ>`

Within the payload, the `rateLimitType: "ORDERS"` entries specify the active cap. For example:

```json
{
  "rateLimitType": "ORDERS",
  "interval": "SECOND",
  "intervalNum": 10,
  "limit": 100
}
```

The above indicates that, for the given symbol set, at most 100 new orders can remain unfilled during any 10-second window. Additional entries (for example, a `DAY` interval) may apply concurrently.

> **Note**
> Order-placement requests are still subject to the standard request-weight, raw-request, and FIX message limits. A surge of order placement calls can therefore trip either the unfilled order limiter or the general request limiters.

## Counting Rules

- Every successful placement of a new order increases the unfilled order count by one for *every* ORDERS limiter interval currently configured.
- Orders that are partially or fully filled do not count against the cap after their first fill event. The first fill decrements the unfilled count by at least one across all active intervals.
- Cancelling or allowing an order to expire **does not** decrease the count. Only fills do.
- If the count reaches the configured limit, subsequent placement attempts receive HTTP **429 Too Many Requests** with error code **-1015** ("Too many new orders"). The same rejection applies across REST, WebSocket, and FIX APIs.
- The unfilled order count is tracked per (sub)account. All API keys, IPs, and protocols attached to the account share the same quota.

Because the counter is evaluated per interval, the allowance resets when the interval rolls over (for example, every 10 seconds for an interval of `SECOND` × `10`).

## Effect of Fills

The first trade execution on an order determines how much relief you receive:

- **Taker fills** (orders that match immediately) reduce the count by one.
- **Maker fills** (orders that rest on the book) can reduce the count by more than one, especially when they provide significant liquidity or fill large quantities. The exact multiplier is not disclosed, but maker orders that eventually trade tend to free up more quota.

There is a short delay between the fill event and the counter decrement. Exercise caution when operating close to the limit because fills may take a moment to register.

### Taker Example

| Time      | Action                    | Unfilled Count |
|-----------|---------------------------|----------------|
| 00:00:00  | —                         | 0              |
| 00:00:01  | Place LIMIT order A       | 1 *(+1)*       |
| 00:00:02  | Place LIMIT order B       | 2 *(+1)*       |
|           | Order B partially filled  | 1 *(−1)*       |
| 00:00:03  | Place LIMIT order C       | 2 *(+1)*       |
| 00:00:04  | Order B partially filled  | 2              |
| 00:00:04  | Order B fully filled      | 2              |
| 00:00:05  | Place MARKET order D      | 3 *(+1)*       |
|           | Order D fully filled      | 2 *(−1)*       |

### Maker Example

| Time      | Action                    | Unfilled Count |
|-----------|---------------------------|----------------|
| 00:00:00  | —                         | 0              |
| 00:00:01  | Place LIMIT order A       | 1 *(+1)*       |
| 00:00:01  | Place LIMIT order B       | 2 *(+1)*       |
| 00:00:02  | Place LIMIT order C       | 3 *(+1)*       |
| 00:00:02  | Place LIMIT order D       | 4 *(+1)*       |
| 00:00:02  | Place LIMIT order E       | 5 *(+1)*       |
| 00:00:03  | Order A partially filled  | 0 *(−5)*       |
| 00:00:04  | Place LIMIT order F       | 1 *(+1)*       |
| 00:00:04  | Place LIMIT order G       | 2 *(+1)*       |
| 00:00:05  | Order A partially filled  | 2              |
| 00:00:05  | Order A fully filled      | 2              |
| 00:00:05  | Order B partially filled  | 0 *(−5)*       |
| 00:00:06  | Place LIMIT order H       | 1 *(+1)*       |

## Cancelled or Expired Orders

Cancelling an order—or letting a fill-or-kill (FOK) order expire without a trade—does not change the unfilled order count. Only fills reduce the counter.

| Time      | Action                       | Unfilled Count |
|-----------|------------------------------|----------------|
| 00:00:00  | —                            | 0              |
| 00:00:01  | Place LIMIT order A          | 1 *(+1)*       |
| 00:00:02  | Cancel order A               | 1              |
| 00:00:02  | Place LIMIT order B          | 2 *(+1)*       |
| 00:00:03  | Place LIMIT FOK order C      | 3 *(+1)*       |
|           | Order C fully filled         | 2 *(−1)*       |
| 00:00:05  | Place LIMIT order D          | 3 *(+1)*       |
| 00:00:06  | Place LIMIT FOK order E      | 4 *(+1)*       |
|           | Order E expires, no fill     | 4              |
| 00:00:07  | Cancel order D               | 4              |
| 00:00:07  | Place LIMIT order F          | 5 *(+1)*       |

## Interval Boundaries and Time Zones

- Intervals expressed as `DAY` are anchored to UTC.
- Fills reduce the current unfilled order count regardless of the day the order was originally submitted.

Example:

| Time              | Action                 | Unfilled Count |
|-------------------|------------------------|----------------|
| 2024-01-01 09:00   | Place orders 1–5       | 5              |
| 2024-01-02 00:00   | Interval resets        | 0              |
| 2024-01-02 09:00   | Place orders 6–15      | 10             |
| 2024-01-02 12:00   | Orders 1–5 filled      | 5              |
| 2024-01-02 13:00   | Orders 6–10 filled     | 0              |
| 2024-01-02 14:00   | Place orders 16–17     | 2              |
| 2024-01-02 15:00   | Orders 11–15 filled    | 0              |

Once the unfilled order count reaches zero, additional fills do not push it negative. Each new order increments the count again as usual.

## Operational Guidance

1. Track the order-count headers (`X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)`) returned with successful order placements.
2. When error **-1015** or HTTP **429** is encountered, pause new order submissions until the relevant interval elapses.
3. Prefer strategies that lead to quick fills—especially maker fills—to free up quota faster.
4. Remember that bursty placement can also collide with the general request-weight limits, leading to bans if you continue to send traffic after receiving throttling errors.

Staying within these constraints preserves healthy matching engine performance and keeps your trading access uninterrupted.
