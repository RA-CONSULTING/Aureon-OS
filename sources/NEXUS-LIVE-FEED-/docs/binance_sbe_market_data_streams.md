# Binance SBE Market Data Streams

This document summarizes the publicly available Binance SBE market data WebSocket streams and their operational requirements.

## Base Endpoint
- **Production:** `stream-sbe.binance.com` or `stream-sbe.binance.com:9443`
- **Spot Testnet:** `stream-sbe.testnet.binance.vision` or `stream-sbe.testnet.binance.vision:9443`

You can subscribe to one stream via `/ws/<streamName>` or to multiple streams via `/stream?streams=<streamName1>/<streamName2>/<streamName3>`.

## General Usage
- Streams deliver market data in SBE (Simple Binary Encoding) format. Use the [official schema](https://github.com/binance/binance-futures-connector-python/blob/master/binance/websockets/sbe_schema) to decode payloads.
- For JSON payloads, fall back to the [Binance WebSocket market data documentation](https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams).
- All stream names use lowercase symbols.
- Connections are valid for up to 24 hours; expect a disconnect at that point.
- All time and timestamp fields are reported in microseconds.
- An API key is required. Only Ed25519 keys are supported.
- Include the API key in the `X-MBX-APIKEY` header when opening the WebSocket. No timestamp or signature is required for public data.
- API key symbol whitelists do not affect access, but IP whitelists still apply if configured.

## Connection Keepalive
- The server sends a WebSocket ping frame every 20 seconds.
- Reply with a pong frame, echoing the ping payload, within 60 seconds to avoid disconnection.
- You may send unsolicited pong frames (recommended with an empty payload), but they do not count toward the keepalive requirement.

## Live Subscription Management
- You can subscribe and unsubscribe while the connection is open.
- Control messages must be sent as JSON text frames. Responses are also JSON.
- Distinguish subscription responses (text frames) from market data events (binary SBE frames).

## Limits
- Maximum 5 client-originated WebSocket messages per second (including ping, pong, and JSON control frames). Exceeding this closes the connection; repeat violations may result in an IP ban.
- Each connection can monitor up to 1,024 streams.
- Maximum 300 connection attempts per IP address every 5 minutes.

## Available Streams
### Trades Stream
- **SBE Message:** `TradesStreamEvent`
- **Stream name:** `<symbol>@trade`
- **Update cadence:** Real-time raw trade events.

### Best Bid/Ask Stream
- **SBE Message:** `BestBidAskStreamEvent`
- **Stream name:** `<symbol>@bestBidAsk`
- **Update cadence:** Real-time updates when best bid or ask changes.
- **Notes:** Supports auto-culling (dropping older queued events per symbol when under load). Includes `eventTime`.

### Diff. Depth Stream
- **SBE Message:** `DepthDiffStreamEvent`
- **Stream name:** `<symbol>@depth`
- **Update cadence:** Incremental order book updates every 100 ms. Use with a local order book procedure.

### Partial Book Depth Stream
- **SBE Message:** `DepthSnapshotStreamEvent`
- **Stream name:** `<symbol>@depth20`
- **Update cadence:** Order book top-20 snapshot every 100 ms.

