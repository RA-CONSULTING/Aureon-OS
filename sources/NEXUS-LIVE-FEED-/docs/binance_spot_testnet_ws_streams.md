# Binance Spot Testnet WebSocket Streams

_Last updated: 2025-04-01_

This reference summarizes the JSON WebSocket market data streams that are available on the Binance Spot Testnet. Use it alongside the REST endpoint guides and the WebSocket API v3 documentation when building or troubleshooting the Nexus ingestion services.

## Base Endpoints
- Primary: `wss://stream.testnet.binance.vision/ws`
- Combined stream wrapper: `wss://stream.testnet.binance.vision/stream`
- Market-data-only alias: `wss://data-stream.binance.vision`

Append the raw stream name to `/ws/` (for a single stream) or pass a slash-delimited list of names to `/stream?streams=` to receive combined payloads. All stream identifiers are **lowercase**.

### Time Units
All timestamps default to **milliseconds**. Add `timeUnit=MICROSECOND` (case-insensitive) to opt into microsecond precision for combined streams, e.g. `/stream?streams=btcusdt@trade&timeUnit=MICROSECOND`.

## Connection Lifecycle
- Sessions are valid for **24 hours**. Expect a forced disconnect at the limit and proactively reconnect if necessary.
- The server sends a **ping** every 20 seconds. Reply with a **pong** that echoes the payload within 60 seconds to keep the connection alive. Unsolicited pong frames are allowed but do not reset the timer.
- Each connection can monitor up to **1,024 streams** and must respect a limit of **5 inbound messages per second** (pings, pongs, and JSON control frames count). Exceeding the quota disconnects the session and repeated violations may result in an IP ban.
- A single IP may attempt up to **300 connections** every 5 minutes.

## Live Subscription Control
Send JSON control frames to subscribe or unsubscribe while the socket is open. Supported `method` values include `SUBSCRIBE`, `UNSUBSCRIBE`, `LIST_SUBSCRIPTIONS`, `SET_PROPERTY`, and `GET_PROPERTY`.

```jsonc
{ "method": "SUBSCRIBE", "params": ["btcusdt@aggTrade", "btcusdt@depth"], "id": 1 }
```

`id` may be a 64-bit signed integer, an alphanumeric string (≤ 36 chars), or `null`. Successful non-query commands return `{ "result": null, "id": <matching id> }`.

Use `SET_PROPERTY` to toggle combined payloads on or off and `GET_PROPERTY` to retrieve the active value. Invalid requests return error objects with a `code`/`msg` pair; refer to the Binance documentation for the full list.

## Stream Catalogue
Each payload below mirrors the Spot Testnet schema. Event timestamps (`E`, `T`, etc.) are in milliseconds unless microseconds are requested.

### Aggregate Trades — `<symbol>@aggTrade`
Aggregated trade executions for a single taker order. Delivered in real time with the following fields:

```jsonc
{
  "e": "aggTrade",        // Event type
  "E": 1672515782136,     // Event time
  "s": "BNBBTC",          // Symbol
  "a": 12345,              // Aggregate trade ID
  "p": "0.001",           // Price
  "q": "100",             // Quantity
  "f": 100,                // First trade ID
  "l": 105,                // Last trade ID
  "T": 1672515782136,     // Trade time
  "m": true,               // Is the buyer the market maker?
  "M": true                // Ignore
}
```

### Trades — `<symbol>@trade`
Raw trade events emitted in real time. Each payload includes the unique buyer and seller IDs.

```jsonc
{
  "e": "trade",
  "E": 1672515782136,
  "s": "BNBBTC",
  "t": 12345,             // Trade ID
  "p": "0.001",           // Price
  "q": "100",             // Quantity
  "T": 1672515782136,     // Trade time
  "m": true,               // Is the buyer the market maker?
  "M": true
}
```

### Klines / Candlesticks — `<symbol>@kline_<interval>`
Pushes updates for the in-progress candlestick. Supported intervals: `1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`.

- Update cadence: 1000 ms for the `1s` interval, 2000 ms for all others.
- Include `@+08:00` (e.g. `<symbol>@kline_1m@+08:00`) to align open/close times to **UTC+8**.

### Individual Symbol Mini Ticker — `<symbol>@miniTicker`
Rolling 24-hour statistics for a single symbol, refreshed every second.

### All Market Mini Tickers — `!miniTicker@arr`
Array of mini ticker entries for all symbols that changed during the last update interval.

### Individual Symbol Ticker — `<symbol>@ticker`
Full 24-hour ticker statistics for a symbol. Updates every second with open, high, low, close, bid/ask, volume, and trade counts.

### All Market Tickers — `!ticker@arr`
Array of ticker payloads for every symbol that changed in the last second.

### Rolling Window Statistics — `<symbol>@ticker_<window>`
Ticker statistics computed over rolling windows (`1h`, `4h`, `1d`). There are also all-market variants: `!ticker_<window>@arr`.

### Book Ticker — `<symbol>@bookTicker`
Real-time best bid and ask price/quantity updates for the specified symbol.

### Average Price — `<symbol>@avgPrice`
Rolling average price for a symbol over a fixed interval (e.g. `5m`). Updated every 1000 ms.

### Partial Book Depth — `<symbol>@depth<levels>`
Top `5`, `10`, or `20` bids and asks. Default refresh is 1000 ms; append `@100ms` for faster updates.

### Diff. Depth — `<symbol>@depth`
Incremental order book updates for maintaining a local book. Supports optional `@100ms` cadence. Apply events sequentially and follow Binance's recommended snapshot+diff reconciliation procedure.

## Managing a Local Order Book
1. Connect to `wss://stream.testnet.binance.vision/ws/<symbol>@depth` and buffer incoming events. Record the first event's `U`.
2. Fetch a REST depth snapshot from `https://testnet.binance.vision/api/v3/depth?symbol=<SYMBOL>&limit=5000`.
3. If `lastUpdateId` from the snapshot is **less than** the buffered event's `U`, repeat step 2 until it is ≥ `U`.
4. Drop any buffered events with `u ≤ lastUpdateId`. The first remaining event must overlap the snapshot range.
5. Initialize the local book with the snapshot and set the update ID to `lastUpdateId`.
6. Apply each buffered and subsequent diff event:
   - Ignore if `u` is less than the local book's update ID.
   - If `U` is greater than the local book's update ID, discard the book and restart from step 1.
   - For each bid/ask entry: insert or update the price level; remove entries whose quantity becomes zero.
   - Update the local book's ID to the event's `u`.

> **Note:** REST snapshots cap each side to 5,000 price levels. Levels outside the snapshot remain unknown until Binance publishes an update for them.

## Error Handling
Example error payloads include:
- `{"code": 0, "msg": "Unknown property", "id": <id>}` — Invalid property name in `SET_PROPERTY`/`GET_PROPERTY`.
- `{"code": 1, "msg": "Invalid value type: expected Boolean"}` — Non-boolean property value.
- `{"code": 2, "msg": "Invalid request: ..."}` — Malformed request (unknown method, invalid ID type, missing fields, etc.).
- `{"code": 3, "msg": "Invalid JSON: expected value at line <line> column <column>"}` — JSON syntax error.

Keep client-originated JSON minimal to stay within the 5 messages/second allowance.

## Related References
- [Binance WebSocket API Rate Limits](./binance_ws_api_rate_limits.md)
- [Binance WebSocket Session Management](./binance_ws_session_management.md)
- [Binance General API Information](./binance_general_api_information.md)
