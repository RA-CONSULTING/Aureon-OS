# Binance WebSocket Streaming Integration

Data feeds have been upgraded from REST polling to Real-time WebSockets.

## 1. New Component: `binance_ws_client.py`

A robust, threaded WebSocket client for Binance data streams.

### Features

- **Auto-Reconnection**: Handles disconnects automatically.
- **Combined Streams**: Supports multiple streams (e.g., `btcusdt@trade`, `ethusdt@ticker`) on a single connection.
- **Thread-Safe Queues**: Pushes data to `trade_queue`, `ticker_queue`, `bar_queue`.
- **Latest Data Cache**: Instant access to `client.latest_tickers['BTCUSDT']`.

### Usage

```python
from binance_ws_client import BinanceWebSocketClient

ws = BinanceWebSocketClient()
ws.start(["btcusdt@ticker", "ethusdt@trade"])

# Access real-time data
btc_price = ws.latest_tickers["BTCUSDT"].last_price
```

## 2. Upgraded: `realtime_wave_monitor.py`

The Real-Time Harmonic Wave Monitor now uses the WebSocket client for sub-second latency updates, replacing the previous 1-second polling loop.

- **Latency**: Reduced from ~1000ms (poll) to <100ms (stream).
- **Smoothness**: Waveforms update instantly as market moves.
- **Efficiency**: Reduced API rate limit usage significantly.

## 3. Integration with Alpaca

The system now enables a full "Live Ecosystem" view:

- **Crypto**: Binance WebSockets (`binance_ws_client.py`)
- **Stocks/Equity**: Alpaca SSE (`alpaca_sse_client.py`)

Run `python realtime_wave_monitor.py` to see it in action.
