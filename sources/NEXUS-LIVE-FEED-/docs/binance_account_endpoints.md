# Binance Account Signed Endpoints (JSON-RPC Envelope)

This reference catalogs the JSON-RPC style account endpoints that the trading tooling in this repository calls. Every request must include a millisecond `timestamp` and a HMAC SHA-256 `signature` generated with the account's API secret. Optional `recvWindow` parameters accept up to three decimal places (microseconds) and cannot exceed `60000`.

Unless otherwise specified, responses originate from an in-memory cache backed by the database. The Binance API continues to enforce the standard request weight limits described below.

---


## Account Status — `GET /api/v3/account` / `method: "account.status"`

Query high-level account information, including commission settings, flags indicating whether trading/withdrawals/deposits are enabled, and the current asset balances. When `omitZeroBalances` is set to `true`, only assets with a non-zero `free` or `locked` value are returned.

- **Weight:** 20
- **Data Source:** Memory ⇒ Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `apiKey` | STRING | ✅ | API key issued by Binance |
| `omitZeroBalances` | BOOLEAN |  | Exclude assets with zero balances (default `false`) |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000. Supports up to 3 decimal places. |
| `signature` | STRING | ✅ | HMAC SHA-256 signature using the API secret |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "605a6d20-6588-4cb9-afa0-b0ab087507ba",
  "method": "account.status",
  "params": {
    "apiKey": "your_binance_api_key_here",
    "signature": "83303b4a136ac1371795f465808367242685a9e3a42b22edb4d977d0696eb45c",
    "timestamp": 1660801839480
  }
}
```

**Example Response**

```json
{
  "id": "605a6d20-6588-4cb9-afa0-b0ab087507ba",
  "status": 200,
  "result": {
    "makerCommission": 15,
    "takerCommission": 15,
    "buyerCommission": 0,
    "sellerCommission": 0,
    "canTrade": true,
    "canWithdraw": true,
    "canDeposit": true,
    "commissionRates": {
      "maker": "0.00150000",
      "taker": "0.00150000",
      "buyer": "0.00000000",
      "seller": "0.00000000"
    },
    "brokered": false,
    "requireSelfTradePrevention": false,
    "preventSor": false,
    "updateTime": 1660801833000,
    "accountType": "SPOT",
    "balances": [
      {
        "asset": "BNB",
        "free": "0.00000000",
        "locked": "0.00000000"
      },
      {
        "asset": "BTC",
        "free": "1.3447112",
        "locked": "0.08600000"
      },
      {
        "asset": "USDT",
        "free": "1021.21000000",
        "locked": "0.00000000"
      }
    ],
    "permissions": [
      "SPOT"
    ],
    "uid": 354937868
  },
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Order Status — `GET /api/v3/order` / `method: "order.status"`

Check the execution status of an individual order. If both `orderId` and `origClientOrderId` are supplied, Binance first looks up the `orderId` and verifies that the `origClientOrderId` matches that record. Some historical orders may omit `cummulativeQuoteQty` (or return it as a negative value) when the data is unavailable.

- **Weight:** 4  
- **Data Source:** Memory ⇒ Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair (e.g., `BTCUSDT`) |
| `orderId` | LONG | ✅* | Search by Binance order ID |
| `origClientOrderId` | STRING |  | Client-assigned identifier. Used if `orderId` not found. |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "aa62318a-5a97-4f3b-bdc7-640bbe33b291",
  "method": "order.status",
  "params": {
    "symbol": "BTCUSDT",
    "orderId": 12569099453,
    "apiKey": "your_binance_api_key_here",
    "signature": "2c3aab5a078ee4ea465ecd95523b77289f61476c2f238ec10c55ea6cb11a6f35",
    "timestamp": 1660801720951
  }
}
```

**Example Response**

```json
{
  "id": "aa62318a-5a97-4f3b-bdc7-640bbe33b291",
  "status": 200,
  "result": {
    "symbol": "BTCUSDT",
    "orderId": 12569099453,
    "orderListId": -1,
    "clientOrderId": "4d96324ff9d44481926157",
    "price": "23416.10000000",
    "origQty": "0.00847000",
    "executedQty": "0.00847000",
    "cummulativeQuoteQty": "198.33521500",
    "status": "FILLED",
    "timeInForce": "GTC",
    "type": "LIMIT",
    "side": "SELL",
    "stopPrice": "0.00000000",
    "trailingDelta": 10,
    "trailingTime": -1,
    "icebergQty": "0.00000000",
    "time": 1660801715639,
    "updateTime": 1660801717945,
    "isWorking": true,
    "workingTime": 1660801715639,
    "origQuoteOrderQty": "0.00000000",
    "strategyId": 37463720,
    "strategyType": 1000000,
    "selfTradePreventionMode": "NONE",
    "preventedMatchId": 0,
    "preventedQuantity": "1.200000"
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

---

## Open Orders — `GET /api/v3/openOrders` / `method: "openOrders.status"`

Fetch the execution status of all open orders. Passing a `symbol` restricts the results to that market; omitting it returns every open order at a cost of 80 weight units.

- **Weight:** 6 with `symbol`; 80 without `symbol`  
- **Data Source:** Memory ⇒ Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING |  | Trading pair. When omitted, all symbols are returned. |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "55f07876-4f6f-4c47-87dc-43e5fff3f2e7",
  "method": "openOrders.status",
  "params": {
    "symbol": "BTCUSDT",
    "apiKey": "your_binance_api_key_here",
    "signature": "d632b3fdb8a81dd44f82c7c901833309dd714fe508772a89b0a35b0ee0c48b89",
    "timestamp": 1660813156812
  }
}
```

**Example Response**

```json
{
  "id": "55f07876-4f6f-4c47-87dc-43e5fff3f2e7",
  "status": 200,
  "result": [
    {
      "symbol": "BTCUSDT",
      "orderId": 12569099453,
      "orderListId": -1,
      "clientOrderId": "4d96324ff9d44481926157",
      "price": "23416.10000000",
      "origQty": "0.00847000",
      "executedQty": "0.00720000",
      "origQuoteOrderQty": "0.000000",
      "cummulativeQuoteQty": "172.43931000",
      "status": "PARTIALLY_FILLED",
      "timeInForce": "GTC",
      "type": "LIMIT",
      "side": "SELL",
      "stopPrice": "0.00000000",
      "icebergQty": "0.00000000",
      "time": 1660801715639,
      "updateTime": 1660801717945,
      "isWorking": true,
      "workingTime": 1660801715639,
      "origQuoteOrderQty": "0.00000000",
      "selfTradePreventionMode": "NONE"
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 6
    }
  ]
}
```

---

## Order History — `GET /api/v3/allOrders` / `method: "allOrders"`

Return active, canceled, and filled orders for a symbol over a limited time range (≤ 24 hours) or starting from a specific `orderId`. When `startTime`/`endTime` are supplied, `orderId` is ignored.

- **Weight:** 20  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `orderId` | LONG |  | Fetch orders with ID ≥ `orderId` |
| `startTime` | LONG |  | Millisecond UNIX timestamp |
| `endTime` | LONG |  | Millisecond UNIX timestamp |
| `limit` | INT |  | Defaults to 500; max 1000 |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "734235c2-13d2-4574-be68-723e818c08f3",
  "method": "allOrders",
  "params": {
    "symbol": "BTCUSDT",
    "startTime": 1660780800000,
    "endTime": 1660867200000,
    "limit": 5,
    "apiKey": "your_binance_api_key_here",
    "signature": "f50a972ba7fad92842187643f6b930802d4e20bce1ba1e788e856e811577bd42",
    "timestamp": 1661955123341
  }
}
```

**Example Response**

```json
{
  "id": "734235c2-13d2-4574-be68-723e818c08f3",
  "status": 200,
  "result": [
    {
      "symbol": "BTCUSDT",
      "orderId": 12569099453,
      "orderListId": -1,
      "clientOrderId": "4d96324ff9d44481926157",
      "price": "23416.10000000",
      "origQty": "0.00847000",
      "executedQty": "0.00847000",
      "cummulativeQuoteQty": "198.33521500",
      "status": "FILLED",
      "timeInForce": "GTC",
      "type": "LIMIT",
      "side": "SELL",
      "stopPrice": "0.00000000",
      "icebergQty": "0.00000000",
      "time": 1660801715639,
      "updateTime": 1660801717945,
      "isWorking": true,
      "workingTime": 1660801715639,
      "origQuoteOrderQty": "0.00000000",
      "selfTradePreventionMode": "NONE",
      "preventedMatchId": 0,
      "preventedQuantity": "1.200000"
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Order List Status — `GET /api/v3/orderList` / `method: "orderList.status"`

Retrieve the execution state of an OCO order list by `orderListId` or `origClientOrderId`. When both are provided, Binance uses `origClientOrderId` and ignores `orderListId`.

- **Weight:** 4  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `origClientOrderId` | STRING | ✅* | Query by OCO `listClientOrderId` |
| `orderListId` | INT | ✅* | Binance OCO list identifier |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "b53fd5ff-82c7-4a04-bd64-5f9dc42c2100",
  "method": "orderList.status",
  "params": {
    "origClientOrderId": "08985fedd9ea2cf6b28996",
    "apiKey": "your_binance_api_key_here",
    "signature": "d12f4e8892d46c0ddfbd43d556ff6d818581b3be22a02810c2c20cb719aed6a4",
    "timestamp": 1660801713965
  }
}
```

**Example Response**

```json
{
  "id": "b53fd5ff-82c7-4a04-bd64-5f9dc42c2100",
  "status": 200,
  "result": {
    "orderListId": 1274512,
    "contingencyType": "OCO",
    "listStatusType": "EXEC_STARTED",
    "listOrderStatus": "EXECUTING",
    "listClientOrderId": "08985fedd9ea2cf6b28996",
    "transactionTime": 1660801713793,
    "symbol": "BTCUSDT",
    "orders": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12569138901,
        "clientOrderId": "BqtFCj5odMoWtSqGk2X9tU"
      },
      {
        "symbol": "BTCUSDT",
        "orderId": 12569138902,
        "clientOrderId": "jLnZpj5enfMXTuhKB1d0us"
      }
    ]
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

---

## Open Order Lists — `GET /api/v3/openOrderList` / `method: "openOrderLists.status"`

Return the currently executing OCO order lists for the account.

- **Weight:** 6  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "3a4437e2-41a3-4c19-897c-9cadc5dce8b6",
  "method": "openOrderLists.status",
  "params": {
    "apiKey": "your_binance_api_key_here",
    "signature": "1bea8b157dd78c3da30359bddcd999e4049749fe50b828e620e12f64e8b433c9",
    "timestamp": 1660801713831
  }
}
```

**Example Response**

```json
{
  "id": "3a4437e2-41a3-4c19-897c-9cadc5dce8b6",
  "status": 200,
  "result": [
    {
      "orderListId": 0,
      "contingencyType": "OCO",
      "listStatusType": "EXEC_STARTED",
      "listOrderStatus": "EXECUTING",
      "listClientOrderId": "08985fedd9ea2cf6b28996",
      "transactionTime": 1660801713793,
      "symbol": "BTCUSDT",
      "orders": [
        {
          "symbol": "BTCUSDT",
          "orderId": 4,
          "clientOrderId": "CUhLgTXnX5n2c0gWiLpV4d"
        },
        {
          "symbol": "BTCUSDT",
          "orderId": 5,
          "clientOrderId": "1ZqG7bBuYwaF4SU8CwnwHm"
        }
      ]
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 6
    }
  ]
}
```

---

## Order List History — `GET /api/v3/allOrderList` / `method: "allOrderLists"`

List historical OCO order lists. Time windows must not exceed 24 hours. If `startTime`/`endTime` are supplied, `fromId` is ignored.

- **Weight:** 20  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `fromId` | INT |  | Return order lists with ID ≥ `fromId` |
| `startTime` | LONG |  | Millisecond UNIX timestamp |
| `endTime` | LONG |  | Millisecond UNIX timestamp |
| `limit` | INT |  | Defaults to 500; max 1000 |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "8617b7b3-1b3d-4dec-94cd-eefd929b8ceb",
  "method": "allOrderLists",
  "params": {
    "startTime": 1660780800000,
    "endTime": 1660867200000,
    "limit": 5,
    "apiKey": "your_binance_api_key_here",
    "signature": "c8e1484db4a4a02d0e84dfa627eb9b8298f07ebf12fcc4eaf86e4a565b2712c2",
    "timestamp": 1661955123341
  }
}
```

**Example Response**

```json
{
  "id": "8617b7b3-1b3d-4dec-94cd-eefd929b8ceb",
  "status": 200,
  "result": [
    {
      "orderListId": 1274512,
      "contingencyType": "OCO",
      "listStatusType": "EXEC_STARTED",
      "listOrderStatus": "EXECUTING",
      "listClientOrderId": "08985fedd9ea2cf6b28996",
      "transactionTime": 1660801713793,
      "symbol": "BTCUSDT",
      "orders": [
        {
          "symbol": "BTCUSDT",
          "orderId": 12569138901,
          "clientOrderId": "BqtFCj5odMoWtSqGk2X9tU"
        },
        {
          "symbol": "BTCUSDT",
          "orderId": 12569138902,
          "clientOrderId": "jLnZpj5enfMXTuhKB1d0us"
        }
      ]
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Trade History — `GET /api/v3/myTrades` / `method: "myTrades"`

Retrieve fills for a symbol. Provide `orderId` to reduce the weight from 20 to 5. Supported combinations include `symbol + orderId`, `symbol + startTime + endTime`, and `symbol + fromId`.

- **Weight:** 20 without `orderId`; 5 with `orderId`  
- **Data Source:** Memory ⇒ Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `orderId` | LONG |  | Filter trades related to the specified order |
| `startTime` | LONG |  | Millisecond UNIX timestamp |
| `endTime` | LONG |  | Millisecond UNIX timestamp |
| `fromId` | INT |  | Return trades with ID ≥ `fromId` (cannot be combined with time filters) |
| `limit` | INT |  | Defaults to 500; max 1000 |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "f4ce6a53-a29d-4f70-823b-4ab59391d6e8",
  "method": "myTrades",
  "params": {
    "symbol": "BTCUSDT",
    "startTime": 1660780800000,
    "endTime": 1660867200000,
    "apiKey": "your_binance_api_key_here",
    "signature": "c5a5ffb79fd4f2e10a92f895d488943a57954edf5933bde3338dfb6ea6d6eefc",
    "timestamp": 1661955125250
  }
}
```

**Example Response**

```json
{
  "id": "f4ce6a53-a29d-4f70-823b-4ab59391d6e8",
  "status": 200,
  "result": [
    {
      "symbol": "BTCUSDT",
      "id": 1650422481,
      "orderId": 12569099453,
      "orderListId": -1,
      "price": "23416.10000000",
      "qty": "0.00635000",
      "quoteQty": "148.69223500",
      "commission": "0.00000000",
      "commissionAsset": "BNB",
      "time": 1660801715793,
      "isBuyer": false,
      "isMaker": true,
      "isBestMatch": true
    },
    {
      "symbol": "BTCUSDT",
      "id": 1650422482,
      "orderId": 12569099453,
      "orderListId": -1,
      "price": "23416.50000000",
      "qty": "0.00212000",
      "quoteQty": "49.64298000",
      "commission": "0.00000000",
      "commissionAsset": "BNB",
      "time": 1660801715793,
      "isBuyer": false,
      "isMaker": true,
      "isBestMatch": true
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Unfilled Order Count — `GET /api/v3/rateLimit/order` / `method: "account.rateLimits.orders"`

Return the current unfilled order usage for each throttle window. Helpful for proactive rate limiting within automation.

- **Weight:** 40  
- **Data Source:** Memory

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "d3783d8d-f8d1-4d2c-b8a0-b7596af5a664",
  "method": "account.rateLimits.orders",
  "params": {
    "apiKey": "your_binance_api_key_here",
    "signature": "76289424d6e288f4dc47d167ac824e859dabf78736f4348abbbac848d719eb94",
    "timestamp": 1660801839500
  }
}
```

**Example Response**

```json
{
  "id": "d3783d8d-f8d1-4d2c-b8a0-b7596af5a664",
  "status": 200,
  "result": [
    {
      "rateLimitType": "ORDERS",
      "interval": "SECOND",
      "intervalNum": 10,
      "limit": 50,
      "count": 0
    },
    {
      "rateLimitType": "ORDERS",
      "interval": "DAY",
      "intervalNum": 1,
      "limit": 160000,
      "count": 0
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 40
    }
  ]
}
```

---

## Prevented Matches — `GET /api/v3/myPreventedMatches` / `method: "myPreventedMatches"`

Show orders that expired due to self-trade prevention (STP). Supported lookup combinations include `symbol + preventedMatchId`, `symbol + orderId`, and `symbol + orderId + fromPreventedMatchId (+ limit)`.

- **Weight:** 2 when the `symbol` is invalid or when querying by `preventedMatchId`; 20 when querying by `orderId`
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `preventedMatchId` | LONG |  | Filter by prevented match ID |
| `orderId` | LONG |  | Filter prevented matches for an order |
| `fromPreventedMatchId` | LONG |  | Pagination cursor |
| `limit` | INT |  | Defaults to 500; max 1000 |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "g4ce6a53-a39d-4f71-823b-4ab5r391d6y8",
  "method": "myPreventedMatches",
  "params": {
    "symbol": "BTCUSDT",
    "orderId": 35,
    "apiKey": "your_binance_api_key_here",
    "signature": "c5a5ffb79fd4f2e10a92f895d488943a57954edf5933bde3338dfb6ea6d6eefc",
    "timestamp": 1673923281052
  }
}
```

**Example Response**

```json
{
  "id": "g4ce6a53-a39d-4f71-823b-4ab5r391d6y8",
  "status": 200,
  "result": [
    {
      "symbol": "BTCUSDT",
      "preventedMatchId": 1,
      "takerOrderId": 5,
      "makerSymbol": "BTCUSDT",
      "makerOrderId": 3,
      "tradeGroupId": 1,
      "selfTradePreventionMode": "EXPIRE_MAKER",
      "price": "1.100000",
      "makerPreventedQuantity": "1.300000",
      "transactTime": 1669101687094
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Allocations — `GET /api/v3/myAllocations` / `method: "myAllocations"`

Retrieve allocations generated by Smart Order Routing (SOR). Results can be filtered by `orderId`, `fromAllocationId`, or time range (≤ 24 hours).

- **Weight:** 20  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `startTime` | LONG |  | Millisecond UNIX timestamp |
| `endTime` | LONG |  | Millisecond UNIX timestamp |
| `fromAllocationId` | INT |  | Pagination cursor |
| `limit` | INT |  | Defaults to 500; max 1000 |
| `orderId` | LONG |  | Filter allocations for an order |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG |  | Millisecond UNIX timestamp (optional but recommended) |

**Example Request**

```json
{
  "id": "g4ce6a53-a39d-4f71-823b-4ab5r391d6y8",
  "method": "myAllocations",
  "params": {
    "symbol": "BTCUSDT",
    "orderId": 500,
    "apiKey": "your_binance_api_key_here",
    "signature": "c5a5ffb79fd4f2e10a92f895d488943a57954edf5933bde3338dfb6ea6d6eefc",
    "timestamp": 1673923281052
  }
}
```

**Example Response**

```json
{
  "id": "g4ce6a53-a39d-4f71-823b-4ab5r391d6y8",
  "status": 200,
  "result": [
    {
      "symbol": "BTCUSDT",
      "allocationId": 0,
      "allocationType": "SOR",
      "orderId": 500,
      "orderListId": -1,
      "price": "1.00000000",
      "qty": "0.10000000",
      "quoteQty": "0.10000000",
      "commission": "0.00000000",
      "commissionAsset": "BTC",
      "time": 1687319487614,
      "isBuyer": false,
      "isMaker": false,
      "isAllocator": false
    }
  ],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Commission Rates — `GET /api/v3/account/commission` / `method: "account.commission"`

Return the current commission configuration for a symbol, including standard, special, and tax rates as well as the BNB discount settings.

- **Weight:** 20  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "d3df8a61-98ea-4fe0-8f4e-0fcea5d418b0",
  "method": "account.commission",
  "params": {
    "symbol": "BTCUSDT",
    "apiKey": "your_binance_api_key_here",
    "signature": "c5a5ffb79fd4f2e10a92f895d488943a57954edf5933bde3338dfb6ea6d6eefc",
    "timestamp": 1673923281052
  }
}
```

**Example Response**

```json
{
  "id": "d3df8a61-98ea-4fe0-8f4e-0fcea5d418b0",
  "status": 200,
  "result": {
    "symbol": "BTCUSDT",
    "standardCommission": {
      "maker": "0.00000010",
      "taker": "0.00000020",
      "buyer": "0.00000030",
      "seller": "0.00000040"
    },
    "specialCommission": {
      "maker": "0.01000000",
      "taker": "0.02000000",
      "buyer": "0.03000000",
      "seller": "0.04000000"
    },
    "taxCommission": {
      "maker": "0.00000112",
      "taker": "0.00000114",
      "buyer": "0.00000118",
      "seller": "0.00000116"
    },
    "discount": {
      "enabledForAccount": true,
      "enabledForSymbol": true,
      "discountAsset": "BNB",
      "discount": "0.75000000"
    }
  },
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 20
    }
  ]
}
```

---

## Order Amendments — `GET /api/v3/order/amendments` / `method: "order.amendments"`

List amendments performed on a single order. Use `fromExecutionId` to paginate older amendments.

- **Weight:** 4  
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `orderId` | LONG | ✅ | Binance order ID |
| `fromExecutionId` | LONG |  | Return amendments with execution ID ≥ value |
| `limit` | INT |  | Defaults to 500; max 1000 |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "6f5ebe91-01d9-43ac-be99-57cf062e0e30",
  "method": "order.amendments",
  "params": {
    "orderId": "23",
    "recvWindow": 5000,
    "symbol": "BTCUSDT",
    "timestamp": 1741925524887,
    "apiKey": "your_binance_api_key_here",
    "signature": "0eed2e9d95b6868ea5ec21da0d14538192ef344c30ecf9fe83d58631699334dc"
  }
}
```

**Example Response**

```json
{
  "id": "6f5ebe91-01d9-43ac-be99-57cf062e0e30",
  "status": 200,
  "result": [
    {
      "symbol": "BTCUSDT",
      "orderId": 23,
      "executionId": 60,
      "origClientOrderId": "my_pending_order",
      "newClientOrderId": "xbxXh5SSwaHS7oUEOCI88B",
      "origQty": "7.00000000",
      "newQty": "5.00000000",
      "time": 1741924229819
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

---

## Relevant Filters — `GET /api/v3/myFilters` / `method: "myFilters"`

Return the exchange, symbol, and asset-level filters applied to the account. This endpoint is the only way to surface `MAX_ASSET` filter assignments.

- **Weight:** 40  
- **Data Source:** Memory

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `symbol` | STRING | ✅ | Trading pair |
| `apiKey` | STRING | ✅ | API key |
| `recvWindow` | DECIMAL |  | Must be ≤ 60000 |
| `signature` | STRING | ✅ | HMAC SHA-256 signature |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp |

**Example Request**

```json
{
  "id": "74R4febb-d142-46a2-977d-90533eb4d97g",
  "method": "myFilters",
  "params": {
    "recvWindow": 5000,
    "symbol": "BTCUSDT",
    "timestamp": 1758008841149,
    "apiKey": "your_binance_api_key_here",
    "signature": "7edc54dd0493dd5bc47adbab9b17bfc9b378d55c20511ae5a168456d3d37aa3a"
  }
}
```

**Example Response**

```json
{
  "id": "1758009606869",
  "status": 200,
  "result": {
    "exchangeFilters": [
      {
        "filterType": "EXCHANGE_MAX_NUM_ORDERS",
        "maxNumOrders": 1000
      }
    ],
    "symbolFilters": [
      {
        "filterType": "MAX_NUM_ORDER_LISTS",
        "maxNumOrderLists": 20
      }
    ],
    "assetFilters": [
      {
        "filterType": "MAX_ASSET",
        "asset": "JPY",
        "limit": "1000000.00000000"
      }
    ]
  }
}
```

---

## Mining Account Hashrate Statistics — `GET /sapi/v1/mining/statistics/user/list` / `method: "mining.statistics.user.list"`

Query hourly and daily hashrate metrics for a specific mining account. Results are grouped by
`type`, with `H_hashrate` buckets representing hourly aggregates and `D_hashrate` representing
daily aggregates. Each bucket includes the `time` (millisecond epoch), reported `hashrate`, and
`reject` rate. Because this is a mining User Data endpoint the request must be signed and include
the `X-MBX-APIKEY` header.

- **Weight:** 5
- **Data Source:** Upstream Mining Service

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `apiKey` | STRING | ✅ | API key issued by Binance. Sent via `X-MBX-APIKEY` header. |
| `algo` | STRING | ✅ | Hashing algorithm (e.g., `sha256`, `ethash`). |
| `userName` | STRING | ✅ | Mining account name. |
| `recvWindow` | LONG |  | Optional window in milliseconds (≤ 60000). |
| `signature` | STRING | ✅ | HMAC SHA-256 signature using the API secret. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp. |

**Example REST request**

```bash
curl -H "X-MBX-APIKEY: <api-key>" \
  "https://api.binance.com/sapi/v1/mining/statistics/user/list?algo=sha256&userName=test&timestamp=1587909600000&signature=<sig>"
```

**Example JSON-RPC request**

```json
{
  "id": "4b3ae1f7-470d-4460-b573-a37bd5641c77",
  "method": "mining.statistics.user.list",
  "params": {
    "apiKey": "your_binance_api_key_here",
    "algo": "sha256",
    "userName": "test",
    "timestamp": 1587909600000,
    "signature": "1e72058b58d4f4a9d44ca9f2f8823e0d3d17a585d8cc7f3b6a3d6045559a1d15"
  }
}
```

**Example Response**

```json
{
  "id": "4b3ae1f7-470d-4460-b573-a37bd5641c77",
  "status": 200,
  "result": {
    "code": 0,
    "msg": "",
    "data": [
      {
        "type": "H_hashrate",
        "userName": "test",
        "list": [
          {
            "time": 1585267200000,
            "hashrate": "0.00000000",
            "reject": "0.00000000"
          },
          {
            "time": 1585353600000,
            "hashrate": "0.00000000",
            "reject": "0.00000000"
          }
        ]
      },
      {
        "type": "D_hashrate",
        "userName": "test",
        "list": [
          {
            "time": 1587906000000,
            "hashrate": "0.00000000",
            "reject": "0.00000000"
          },
          {
            "time": 1587909600000,
            "hashrate": "0.00000000",
            "reject": "0.00000000"
          }
        ]
      }
    ]
  },
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 1200,
      "count": 5
    }
  ]
}
```
