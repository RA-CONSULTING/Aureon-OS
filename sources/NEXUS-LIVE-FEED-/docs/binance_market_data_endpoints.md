# Binance Market Data REST Endpoints

This reference condenses the Binance REST market data surface that the Nexus trading tooling
interacts with most frequently. Each section summarises request weight, parameters, notable
behaviour, and canonical response envelopes so you can design cache lifetimes, polling cadence,
and fallback flows without leaving the repo. The Spot JSON-RPC gateway mirrors the REST
contracts; example payloads below show both the HTTPS route and the corresponding `method`
name alongside the JSON-RPC wrapper (`id`, `status`, `result`, `rateLimits`).

When continuous updates are required (book deltas, live trades, ticker rolls, etc.) initialise the
local cache with the REST call, then subscribe to the matching WebSocket stream referenced in each
section.

## Unauthenticated Market Data Surface

Binance exposes a dedicated domain—`https://data-api.binance.vision`—that mirrors the production
market data endpoints without requiring an API key. The table below captures the unauthenticated
surface that is guaranteed to work for REST callers when only public market data is required.

| HTTP Method | Endpoint | Description |
|-------------|----------|-------------|
| `GET` | `/api/v3/aggTrades` | Aggregated trades with price/quantity buckets. Supports `fromId`, `startTime`, `endTime`, and `limit`. |
| `GET` | `/api/v3/avgPrice` | 5-minute rolling average price for the symbol provided. |
| `GET` | `/api/v3/depth` | Order book snapshot. Respect the documented request weights per `limit`. |
| `GET` | `/api/v3/exchangeInfo` | Instrument metadata, rate limits, and trading rules. |
| `GET` | `/api/v3/klines` | Candlestick data. Requires `symbol` and `interval`; accepts optional pagination parameters. |
| `GET` | `/api/v3/ping` | Liveness probe that returns `{}` on success. |
| `GET` | `/api/v3/ticker` | Rolling 24hr ticker statistics across symbols. |
| `GET` | `/api/v3/ticker/24hr` | 24-hour ticker statistics per symbol. Accepts `symbol` or `symbols`. |
| `GET` | `/api/v3/ticker/bookTicker` | Best bid/ask for all symbols or a specific symbol. |
| `GET` | `/api/v3/ticker/price` | Latest price for all symbols or a specific symbol. |
| `GET` | `/api/v3/time` | Server time in milliseconds. |
| `GET` | `/api/v3/trades` | Recent trades (up to 1,000). |
| `GET` | `/api/v3/uiKlines` | UI-optimised candlesticks with additional stat fields. |

**Sample REST request**

```bash
curl -sX GET "https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT"
```

For realtime delivery, pair the REST snapshot with the WebSocket market data gateway at
`wss://data-stream.binance.vision:443`. Any public stream documented in the Binance WebSocket
Market Streams guide can be retrieved from this host (e.g., `wss://data-stream.binance.vision:443/ws/btcusdt@kline_1m`).
User Data Streams remain exclusive to the authenticated production domains and cannot be accessed
through the public data mirror.

## Order Book – `GET /api/v3/depth` · `method: "depth"`

- **Weight:** depends on `limit`
  - `1–100` → 5
  - `101–500` → 25
  - `501–1000` → 50
  - `1001–5000` → 250
- **Parameters:**
  - `symbol` (string, required)
  - `limit` (int, optional, default `100`, maximum `5000`)
  - `symbolStatus` (enum, optional: `TRADING`, `HALT`, `BREAK`)
- **Notes:** Snapshot depth is limited; combine with `<symbol>@depth<levels>` or `<symbol>@depth`
  streams to maintain a local order book. Requests above 5000 levels are capped. A symbol/status
  mismatch raises `-1220 SYMBOL_DOES_NOT_MATCH_STATUS`. Bid levels are sorted high→low, ask levels
  low→high.
- **Data source:** Memory
- **RPC request:**

  ```json
  {
    "id": "51e2affb-0aba-4821-ba75-f2625006eb43",
    "method": "depth",
    "params": {
      "symbol": "BNBBTC",
      "limit": 5
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "51e2affb-0aba-4821-ba75-f2625006eb43",
    "status": 200,
    "result": {
      "lastUpdateId": 2731179239,
      "bids": [
        ["0.01379900", "3.43200000"],
        ["0.01379800", "3.24300000"],
        ["0.01379700", "10.45500000"],
        ["0.01379600", "3.82100000"],
        ["0.01379500", "10.26200000"]
      ],
      "asks": [
        ["0.01380000", "5.91700000"],
        ["0.01380100", "6.01400000"],
        ["0.01380200", "0.26800000"],
        ["0.01380300", "0.33800000"],
        ["0.01380400", "0.26800000"]
      ]
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## Mining Algorithm Catalogue – `GET /sapi/v1/mining/pub/algoList` · `method: "mining.algoList"`

- **Weight:** 1
- **Parameters:** none
- **Notes:** Returns the catalog of proof-of-work algorithms that Binance's mining pool supports.
  Each entry includes the public-facing name, the numeric `algoId` used when configuring endpoints
  such as hashpower marketplace orders, an internal `poolIndex`, and the hash rate `unit`. The
  payload is static until Binance lists a new algorithm, making it safe to cache for long periods. No
  API key is required despite the `sapi` prefix.
- **Data source:** Memory
- **RPC request:** Not currently mirrored on the Spot JSON-RPC gateway; call the REST route.
- **Response:**

  ```json
  {
    "code": 0,
    "msg": "",
    "data": [
      {
        "algoName": "sha256",
        "algoId": 1,
        "poolIndex": 0,
        "unit": "h/s"
      }
    ]
  }
  ```

## Recent Trades – `GET /api/v3/trades` · `method: "trades.recent"`

- **Weight:** 25
- **Parameters:**
  - `symbol` (string, required)
  - `limit` (int, optional, default `500`, maximum `1000`)
- **Notes:** Use `<symbol>@trade` to stream fills; REST assists with cache warm-up or recovery.
- **Data source:** Memory
- **RPC request:**

  ```json
  {
    "id": "409a20bd-253d-41db-a6dd-687862a5882f",
    "method": "trades.recent",
    "params": {
      "symbol": "BNBBTC",
      "limit": 1
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "409a20bd-253d-41db-a6dd-687862a5882f",
    "status": 200,
    "result": [
      {
        "id": 194686783,
        "price": "0.01361000",
        "qty": "0.01400000",
        "quoteQty": "0.00019054",
        "time": 1660009530807,
        "isBuyerMaker": true,
        "isBestMatch": true
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## Historical Trades – `GET /api/v3/historicalTrades` · `method: "trades.historical"`

- **Weight:** 25
- **Parameters:**
  - `symbol` (string, required)
  - `fromId` (long, optional) – trade ID to begin at
  - `limit` (int, optional, default `500`, maximum `1000`)
- **Notes:** When `fromId` is omitted the server returns the most recent trades. Use the endpoint to
  backfill deeper history; for live updates rely on the trade WebSocket.
- **Data source:** Database
- **RPC request:**

  ```json
  {
    "id": "cffc9c7d-4efc-4ce0-b587-6b87448f052a",
    "method": "trades.historical",
    "params": {
      "symbol": "BNBBTC",
      "fromId": 0,
      "limit": 1
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "cffc9c7d-4efc-4ce0-b587-6b87448f052a",
    "status": 200,
    "result": [
      {
        "id": 0,
        "price": "0.00005000",
        "qty": "40.00000000",
        "quoteQty": "0.00200000",
        "time": 1500004800376,
        "isBuyerMaker": true,
        "isBestMatch": true
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 10
      }
    ]
  }
  ```

## Aggregate Trades – `GET /api/v3/aggTrades` · `method: "trades.aggregate"`

- **Weight:** 4
- **Parameters:**
  - `symbol` (string, required)
  - `fromId` (long, optional) – aggregate trade ID to begin at (inclusive)
  - `startTime` / `endTime` (long, optional)
  - `limit` (int, optional, default `500`, maximum `1000`)
- **Notes:** When `fromId` is supplied the response includes aggregate IDs ≥ the provided value. You
  cannot combine `fromId` with the time filters. Omitting pagination parameters yields the latest
  aggregate trades. Use `<symbol>@aggTrade` for realtime updates.
- **Data source:** Database
- **RPC request:**

  ```json
  {
    "id": "189da436-d4bd-48ca-9f95-9f613d621717",
    "method": "trades.aggregate",
    "params": {
      "symbol": "BNBBTC",
      "fromId": 50000000,
      "limit": 1
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "189da436-d4bd-48ca-9f95-9f613d621717",
    "status": 200,
    "result": [
      {
        "a": 50000000,
        "p": "0.00274100",
        "q": "57.19000000",
        "f": 59120167,
        "l": 59120170,
        "T": 1565877971222,
        "m": true,
        "M": true
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## Kline Candles – `GET /api/v3/klines` · `method: "klines"`

- **Weight:** 2
- **Parameters:**
  - `symbol` (string, required)
  - `interval` (enum, required) – `1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`,
    `8h`, `12h`, `1d`, `3d`, `1w`, `1M`
  - `startTime` / `endTime` (long, optional)
  - `timeZone` (string, optional, default `0` for UTC)
  - `limit` (int, optional, default `500`, maximum `1000`)
- **Notes:** Without explicit start/end times the most recent candles are returned. `timeZone`
  adjusts bucket alignment but filters remain in UTC. For realtime candles use
  `<symbol>@kline_<interval>`.
- **Data source:** Database
- **RPC request:**

  ```json
  {
    "id": "1dbbeb56-8eea-466a-8f6e-86bdcfa2fc0b",
    "method": "klines",
    "params": {
      "symbol": "BNBBTC",
      "interval": "1h",
      "startTime": 1655969280000,
      "limit": 1
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "1dbbeb56-8eea-466a-8f6e-86bdcfa2fc0b",
    "status": 200,
    "result": [
      [
        1655971200000,
        "0.01086000",
        "0.01086600",
        "0.01083600",
        "0.01083800",
        "2290.53800000",
        1655974799999,
        "24.85074442",
        2283,
        "1171.64000000",
        "12.71225884",
        "0"
      ]
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## UI Kline Candles – `GET /api/v3/uiKlines` · `method: "uiKlines"`

- **Weight:** 2
- **Parameters:** identical to `klines`
- **Notes:** Returns presentation-optimised candlesticks for charting. Start/end filters operate in
  UTC even when a `timeZone` offset is specified.
- **Data source:** Database
- **RPC request:** mirrors `klines`
- **Response:**

  ```json
  {
    "id": "b137468a-fb20-4c06-bd6b-625148eec958",
    "status": 200,
    "result": [
      [
        1655971200000,
        "0.01086000",
        "0.01086600",
        "0.01083600",
        "0.01083800",
        "2290.53800000",
        1655974799999,
        "24.85074442",
        2283,
        "1171.64000000",
        "12.71225884",
        "0"
      ]
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## Current Average Price – `GET /api/v3/avgPrice` · `method: "avgPrice"`

- **Weight:** 2
- **Parameters:**
  - `symbol` (string, required)
- **Notes:** Returns the average price calculated over the last 5 minutes of trades.
- **Data source:** Memory
- **RPC request:**

  ```json
  {
    "id": "ddbfb65f-9ebf-42ec-8240-8f0f91de0867",
    "method": "avgPrice",
    "params": {
      "symbol": "BNBBTC"
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "ddbfb65f-9ebf-42ec-8240-8f0f91de0867",
    "status": 200,
    "result": {
      "mins": 5,
      "price": "9.35751834",
      "closeTime": 1694061154503
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## 24h Ticker Statistics – `GET /api/v3/ticker/24hr` · `method: "ticker.24hr"`

- **Weight:** depends on payload size
  - single `symbol`: 2
  - `symbols` array (1–20): 2, (21–100): 40, (>100): 80
  - omit `symbol`/`symbols` (all symbols): 80
- **Parameters:**
  - `symbol` (string) **or** `symbols` (array of strings)
  - `type` (enum, optional: `FULL`, `MINI`)
  - `symbolStatus` (enum, optional: `TRADING`, `HALT`, `BREAK`)
- **Notes:** `symbol` and `symbols` are mutually exclusive. Status mismatches throw
  `-1220 SYMBOL_DOES_NOT_MATCH_STATUS` for single-symbol requests; non-matching symbols are omitted
  from array responses. Prefer `<symbol>@ticker` / `<symbol>@miniTicker` streams for realtime stats.
- **Data source:** Memory
- **RPC request:**

  ```json
  {
    "id": "93fb61ef-89f8-4d6e-b022-4f035a3fadad",
    "method": "ticker.24hr",
    "params": {
      "symbol": "BNBBTC"
    }
  }
  ```

- **Response (FULL, single symbol):**

  ```json
  {
    "id": "93fb61ef-89f8-4d6e-b022-4f035a3fadad",
    "status": 200,
    "result": {
      "symbol": "BNBBTC",
      "priceChange": "0.00013900",
      "priceChangePercent": "1.020",
      "weightedAvgPrice": "0.01382453",
      "prevClosePrice": "0.01362800",
      "lastPrice": "0.01376700",
      "lastQty": "1.78800000",
      "bidPrice": "0.01376700",
      "bidQty": "4.64600000",
      "askPrice": "0.01376800",
      "askQty": "14.31400000",
      "openPrice": "0.01362800",
      "highPrice": "0.01414900",
      "lowPrice": "0.01346600",
      "volume": "69412.40500000",
      "quoteVolume": "959.59411487",
      "openTime": 1660014164909,
      "closeTime": 1660100564909,
      "firstId": 194696115,
      "lastId": 194968287,
      "count": 272173
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

- **Response (MINI, single symbol):**

  ```json
  {
    "id": "9fa2a91b-3fca-4ed7-a9ad-58e3b67483de",
    "status": 200,
    "result": {
      "symbol": "BNBBTC",
      "openPrice": "0.01362800",
      "highPrice": "0.01414900",
      "lowPrice": "0.01346600",
      "lastPrice": "0.01376700",
      "volume": "69412.40500000",
      "quoteVolume": "959.59411487",
      "openTime": 1660014164909,
      "closeTime": 1660100564909,
      "firstId": 194696115,
      "lastId": 194968287,
      "count": 272173
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

- **Response (array):**

  ```json
  {
    "id": "901be0d9-fd3b-45e4-acd6-10c580d03430",
    "status": 200,
    "result": [
      {
        "symbol": "BNBBTC",
        "priceChange": "0.00016500",
        "priceChangePercent": "1.213",
        "weightedAvgPrice": "0.01382508",
        "prevClosePrice": "0.01360800",
        "lastPrice": "0.01377200",
        "lastQty": "1.01400000",
        "bidPrice": "0.01377100",
        "bidQty": "7.55700000",
        "askPrice": "0.01377200",
        "askQty": "4.37900000",
        "openPrice": "0.01360700",
        "highPrice": "0.01414900",
        "lowPrice": "0.01346600",
        "volume": "69376.27900000",
        "quoteVolume": "959.13277091",
        "openTime": 1660014615517,
        "closeTime": 1660101015517,
        "firstId": 194697254,
        "lastId": 194969483,
        "count": 272230
      },
      {
        "symbol": "BTCUSDT",
        "priceChange": "-938.06000000",
        "priceChangePercent": "-3.938",
        "weightedAvgPrice": "23265.34432003",
        "prevClosePrice": "23819.17000000",
        "lastPrice": "22880.91000000",
        "lastQty": "0.00536000",
        "bidPrice": "22880.40000000",
        "bidQty": "0.00424000",
        "askPrice": "22880.91000000",
        "askQty": "0.04276000",
        "openPrice": "23818.97000000",
        "highPrice": "23933.25000000",
        "lowPrice": "22664.69000000",
        "volume": "153508.37606000",
        "quoteVolume": "3571425225.04441220",
        "openTime": 1660014615977,
        "closeTime": 1660101015977,
        "firstId": 1592019902,
        "lastId": 1597301762,
        "count": 5281861
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

## Trading Day Ticker – `GET /api/v3/ticker/tradingDay` · `method: "ticker.tradingDay"`

- **Weight:** 4 per requested symbol (caps at 200 once `symbols` length > 50)
- **Parameters:**
  - `symbol` (string) **or** `symbols` (array of strings, max 100)
  - `timeZone` (string, optional, default `0` / UTC)
  - `type` (enum, optional: `FULL`, `MINI`)
  - `symbolStatus` (enum, optional)
- **Notes:** `symbol`/`symbols` are mutually exclusive. Status mismatches mirror the 24 h ticker
  behaviour. `timeZone` accepts offsets between `-12:00` and `+14:00`. For rolling-window updates use
  `<symbol>@ticker_<window>` streams.
- **Data source:** Database
- **RPC request:**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "method": "ticker.tradingDay",
    "params": {
      "symbols": ["BNBBTC", "BTCUSDT"],
      "timeZone": "00:00"
    }
  }
  ```

- **Response (FULL, single symbol):**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "status": 200,
    "result": {
      "symbol": "BTCUSDT",
      "priceChange": "-83.13000000",
      "priceChangePercent": "-0.317",
      "weightedAvgPrice": "26234.58803036",
      "openPrice": "26304.80000000",
      "highPrice": "26397.46000000",
      "lowPrice": "26088.34000000",
      "lastPrice": "26221.67000000",
      "volume": "18495.35066000",
      "quoteVolume": "485217905.04210480",
      "openTime": 1695686400000,
      "closeTime": 1695772799999,
      "firstId": 3220151555,
      "lastId": 3220849281,
      "count": 697727
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 4
      }
    ]
  }
  ```

- **Response (FULL, array):**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "status": 200,
    "result": [
      {
        "symbol": "BTCUSDT",
        "priceChange": "-83.13000000",
        "priceChangePercent": "-0.317",
        "weightedAvgPrice": "26234.58803036",
        "openPrice": "26304.80000000",
        "highPrice": "26397.46000000",
        "lowPrice": "26088.34000000",
        "lastPrice": "26221.67000000",
        "volume": "18495.35066000",
        "quoteVolume": "485217905.04210480",
        "openTime": 1695686400000,
        "closeTime": 1695772799999,
        "firstId": 3220151555,
        "lastId": 3220849281,
        "count": 697727
      },
      {
        "symbol": "BNBUSDT",
        "priceChange": "2.60000000",
        "priceChangePercent": "1.238",
        "weightedAvgPrice": "211.92276958",
        "openPrice": "210.00000000",
        "highPrice": "213.70000000",
        "lowPrice": "209.70000000",
        "lastPrice": "212.60000000",
        "volume": "280709.58900000",
        "quoteVolume": "59488753.54750000",
        "openTime": 1695686400000,
        "closeTime": 1695772799999,
        "firstId": 672397461,
        "lastId": 672496158,
        "count": 98698
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 8
      }
    ]
  }
  ```

- **Response (MINI, single symbol):**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "status": 200,
    "result": {
      "symbol": "BTCUSDT",
      "openPrice": "26304.80000000",
      "highPrice": "26397.46000000",
      "lowPrice": "26088.34000000",
      "lastPrice": "26221.67000000",
      "volume": "18495.35066000",
      "quoteVolume": "485217905.04210480",
      "openTime": 1695686400000,
      "closeTime": 1695772799999,
      "firstId": 3220151555,
      "lastId": 3220849281,
      "count": 697727
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 4
      }
    ]
  }
  ```

- **Response (MINI, array):**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "status": 200,
    "result": [
      {
        "symbol": "BTCUSDT",
        "openPrice": "26304.80000000",
        "highPrice": "26397.46000000",
        "lowPrice": "26088.34000000",
        "lastPrice": "26221.67000000",
        "volume": "18495.35066000",
        "quoteVolume": "485217905.04210480",
        "openTime": 1695686400000,
        "closeTime": 1695772799999,
        "firstId": 3220151555,
        "lastId": 3220849281,
        "count": 697727
      },
      {
        "symbol": "BNBUSDT",
        "openPrice": "210.00000000",
        "highPrice": "213.70000000",
        "lowPrice": "209.70000000",
        "lastPrice": "212.60000000",
        "volume": "280709.58900000",
        "quoteVolume": "59488753.54750000",
        "openTime": 1695686400000,
        "closeTime": 1695772799999,
        "firstId": 672397461,
        "lastId": 672496158,
        "count": 98698
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 8
      }
    ]
  }
  ```

## Rolling Window Price Statistics – `GET /api/v3/ticker` · `method: "ticker"`

- **Weight:** depends on symbol count
  - up to 50 symbols → 4 weight each (capped at 200 beyond 50)
  - 51–100 symbols → 200
- **Parameters:**
  - `symbol` (string) **or** `symbols` (array of strings, max 200)
  - `windowSize` (enum, optional, default `1d` – supports `1m`…`59m`, `1h`…`23h`, `1d`…`7d`)
  - `type` (enum, optional: `FULL`, `MINI`)
  - `symbolStatus` (enum, optional)
- **Notes:** Window start always aligns to a minute boundary. The effective window can be up to
  59 999 ms wider than requested because `closeTime` is the request timestamp. For streaming stats
  use `<symbol>@ticker_<window_size>`.
- **Data source:** Database
- **RPC request:**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "method": "ticker",
    "params": {
      "symbols": ["BNBBTC", "BTCUSDT"],
      "windowSize": "7d"
    }
  }
  ```

- **Response (FULL, single symbol):**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "status": 200,
    "result": {
      "symbol": "BNBBTC",
      "priceChange": "0.00061500",
      "priceChangePercent": "4.735",
      "weightedAvgPrice": "0.01368242",
      "openPrice": "0.01298900",
      "highPrice": "0.01418800",
      "lowPrice": "0.01296000",
      "lastPrice": "0.01360400",
      "volume": "587179.23900000",
      "quoteVolume": "8034.03382165",
      "openTime": 1659580020000,
      "closeTime": 1660184865291,
      "firstId": 192977765,
      "lastId": 195365758,
      "count": 2387994
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 4
      }
    ]
  }
  ```

- **Response (MINI, single symbol):**

  ```json
  {
    "id": "bdb7c503-542c-495c-b797-4d2ee2e91173",
    "status": 200,
    "result": {
      "symbol": "BNBBTC",
      "openPrice": "0.01298900",
      "highPrice": "0.01418800",
      "lowPrice": "0.01296000",
      "lastPrice": "0.01360400",
      "volume": "587179.23900000",
      "quoteVolume": "8034.03382165",
      "openTime": 1659580020000,
      "closeTime": 1660184865291,
      "firstId": 192977765,
      "lastId": 195365758,
      "count": 2387994
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 4
      }
    ]
  }
  ```

- **Response (FULL, array):**

  ```json
  {
    "id": "f4b3b507-c8f2-442a-81a6-b2f12daa030f",
    "status": 200,
    "result": [
      {
        "symbol": "BNBBTC",
        "priceChange": "0.00061500",
        "priceChangePercent": "4.735",
        "weightedAvgPrice": "0.01368242",
        "openPrice": "0.01298900",
        "highPrice": "0.01418800",
        "lowPrice": "0.01296000",
        "lastPrice": "0.01360400",
        "volume": "587169.48600000",
        "quoteVolume": "8033.90114517",
        "openTime": 1659580020000,
        "closeTime": 1660184820927,
        "firstId": 192977765,
        "lastId": 195365700,
        "count": 2387936
      },
      {
        "symbol": "BTCUSDT",
        "priceChange": "1182.92000000",
        "priceChangePercent": "5.113",
        "weightedAvgPrice": "23349.27074846",
        "openPrice": "23135.33000000",
        "highPrice": "24491.22000000",
        "lowPrice": "22400.00000000",
        "lastPrice": "24318.25000000",
        "volume": "1039498.10978000",
        "quoteVolume": "24271522807.76838630",
        "openTime": 1659580020000,
        "closeTime": 1660184820927,
        "firstId": 1568787779,
        "lastId": 1604337406,
        "count": 35549628
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 8
      }
    ]
  }
  ```

## Symbol Price Ticker – `GET /api/v3/ticker/price` · `method: "ticker.price"`

- **Weight:**
  - single `symbol`: 2
  - `symbols` array or omit both `symbol`/`symbols`: 4
- **Parameters:**
  - `symbol` (string, optional)
  - `symbols` (array of strings, optional)
  - `symbolStatus` (enum, optional)
- **Notes:** `symbol` and `symbols` cannot be combined. Use `<symbol>@aggTrade` or `<symbol>@trade`
  to stream prices; REST provides last executed price snapshots.
- **Data source:** Memory
- **RPC request:**

  ```json
  {
    "id": "043a7cf2-bde3-4888-9604-c8ac41fcba4d",
    "method": "ticker.price",
    "params": {
      "symbol": "BNBBTC"
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "043a7cf2-bde3-4888-9604-c8ac41fcba4d",
    "status": 200,
    "result": {
      "symbol": "BNBBTC",
      "price": "0.01361900"
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

  ```json
  {
    "id": "e739e673-24c8-4adf-9cfa-b81f30330b09",
    "status": 200,
    "result": [
      { "symbol": "BNBBTC", "price": "0.01363700" },
      { "symbol": "BTCUSDT", "price": "24267.15000000" },
      { "symbol": "BNBBUSD", "price": "331.10000000" }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 4
      }
    ]
  }
  ```

## Order Book Ticker – `GET /api/v3/ticker/bookTicker` · `method: "ticker.book"`

- **Weight:** same as `/api/v3/ticker/price`
- **Parameters:**
  - `symbol` (string, optional)
  - `symbols` (array of strings, optional)
  - `symbolStatus` (enum, optional)
- **Notes:** Streams `<symbol>@bookTicker` yield best bid/ask updates; REST returns the current top of
  book snapshot.
- **Data source:** Memory
- **RPC request:**

  ```json
  {
    "id": "057deb3a-2990-41d1-b58b-98ea0f09e1b4",
    "method": "ticker.book",
    "params": {
      "symbols": ["BNBBTC", "BTCUSDT"]
    }
  }
  ```

- **Response:**

  ```json
  {
    "id": "9d32157c-a556-4d27-9866-66760a174b57",
    "status": 200,
    "result": {
      "symbol": "BNBBTC",
      "bidPrice": "0.01358000",
      "bidQty": "12.53400000",
      "askPrice": "0.01358100",
      "askQty": "17.83700000"
    },
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 2
      }
    ]
  }
  ```

  ```json
  {
    "id": "057deb3a-2990-41d1-b58b-98ea0f09e1b4",
    "status": 200,
    "result": [
      {
        "symbol": "BNBBTC",
        "bidPrice": "0.01358000",
        "bidQty": "12.53400000",
        "askPrice": "0.01358100",
        "askQty": "17.83700000"
      },
      {
        "symbol": "BTCUSDT",
        "bidPrice": "23980.49000000",
        "bidQty": "0.01000000",
        "askPrice": "23981.31000000",
        "askQty": "0.01512000"
      }
    ],
    "rateLimits": [
      {
        "rateLimitType": "REQUEST_WEIGHT",
        "interval": "MINUTE",
        "intervalNum": 1,
        "limit": 6000,
        "count": 4
      }
    ]
  }
  ```

## Mining Coin Catalogue — `GET /sapi/v1/mining/pub/coinList` · `method: "mining.coinList"`

Enumerates every asset supported by Binance Pool along with its algorithm metadata. The endpoint is
a zero-parameter market data call surfaced under the SAPI mining namespace, so it does not require
API key signing and carries a negligible request weight. Use it to populate dropdown selectors for
hashrate monitoring or to validate user input when bootstrapping mining dashboards.

- **Weight:** 1
- **Parameters:** _none_
- **Notes:** Values are returned in ascending `poolIndex` order. The list is versioned centrally by
  Binance; clients should treat `coinId` as an opaque identifier and persist `algoId`/`algoName`
  pairs when they need to filter by hashing algorithm.
- **Data source:** Memory ⇒ Database

| Field | Type | Description |
| --- | --- | --- |
| `coinName` | STRING | Ticker-style symbol for the minable asset (e.g., `BTC`). |
| `coinId` | INTEGER | Stable identifier for the asset within Binance Pool. |
| `poolIndex` | INTEGER | Sort order for display within the Binance Pool UI. |
| `algoId` | INTEGER | Stable identifier for the hashing algorithm. |
| `algoName` | STRING | Human-readable algorithm name (e.g., `sha256`). |

**Sample REST request**

```bash
curl -s "https://api.binance.com/sapi/v1/mining/pub/coinList"
```

**Sample JSON-RPC request**

```json
{
  "id": "8e3d8738-1fb7-4d15-8104-cb0287f9a055",
  "method": "mining.coinList",
  "params": {}
}
```

**Response**

```json
{
  "id": "8e3d8738-1fb7-4d15-8104-cb0287f9a055",
  "status": 200,
  "result": [
    {
      "coinName": "BTC",
      "coinId": 1,
      "poolIndex": 0,
      "algoId": 1,
      "algoName": "sha256"
    },
    {
      "coinName": "BCH",
      "coinId": 2,
      "poolIndex": 1,
      "algoId": 1,
      "algoName": "sha256"
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 1
    }
  ]
}
```
