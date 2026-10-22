# Binance WebSocket API Rate Limits

This document summarizes the connection-level and per-request throttling rules for the Binance WebSocket API (WS API v3).

## Connection Limits

- You can establish **up to 300 WebSocket API connections every 5 minutes per IP address**.
- Each connection consumes request weight (see below) and is subject to the same IP-based accounting.

## Rate Limit Model

The API enforces multiple rate limit intervals at the same time. Each request response may include a `rateLimits` array describing the active limits that the request consumed.

| Field | Description |
| --- | --- |
| `rateLimitType` | Either `REQUEST_WEIGHT` or `ORDERS`. |
| `interval` | `SECOND`, `MINUTE`, `HOUR`, or `DAY`. |
| `intervalNum` | Multiplier for the interval (e.g., `1` minute, `10` seconds). |
| `limit` | Maximum number of requests permitted in the interval. |
| `count` | Current usage within the interval. |

Intervals reset on natural boundaries. For example:

- A `1 MINUTE` interval resets at the start of each minute (00:00, 00:01, 00:02, ...).
- A `10 SECOND` interval resets on the tens of seconds (00, 10, 20, ...).
- A `1 DAY` interval resets at **00:00 UTC**.

If you exhaust a shorter interval while the longer interval still has capacity, you must wait for the shorter interval to reset. Exhausting a longer interval requires waiting for that interval even if shorter windows show zero usage.

### Sample Rate Limit Payload

```json
{
  "id": "7069b743-f477-4ae3-81db-db9b8df085d2",
  "status": 200,
  "result": {
    "serverTime": 1656400526260
  },
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 70
    }
  ]
}
```

### Hiding Rate Limit Data

The `rateLimits` field is included by default. To omit it, set `returnRateLimits` to `false`:

- Per request: `{"id":2,"method":"time","params":{"returnRateLimits":false}}`
- Per connection: append `?returnRateLimits=false` to the WebSocket URL (e.g., `wss://ws-api.binance.com:443/ws-api/v3?returnRateLimits=false`).

When disabled globally, include `"returnRateLimits": true` in individual requests where you need the information.

> **Note:** Requests remain throttled even if you suppress rate limit fields.

## Request Weight Limits

- Each WebSocket API connection consumes **2 weight**.
- Weight is tracked by IP address and shared across all connections from that IP.
- Use the `exchangeInfo` request to discover current limits.
- When weight exceeds the allowed threshold, responses return **status 429** with a `retryAfter` timestamp indicating when you may resume requests.
- Persistently exceeding limits or ignoring backoff guidance results in an automatic IP ban (**status 418**). Bans escalate from 2 minutes up to 3 days.

### Sample Responses

Successful response showing current weight usage:

```json
{
  "id": "7069b743-f477-4ae3-81db-db9b8df085d2",
  "status": 200,
  "result": [],
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 70
    }
  ]
}
```

Banned response (status 418) with retry guidance:

```json
{
  "id": "fc93a61a-a192-4cf4-bb2a-a8f0f0c51e06",
  "status": 418,
  "error": {
    "code": -1003,
    "msg": "Way too much request weight used; IP banned until 1659146400000. Please use WebSocket Streams for live updates to avoid bans.",
    "data": {
      "serverTime": 1659142907531,
      "retryAfter": 1659146400000
    }
  },
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 2411
    }
  ]
}
```

## Order Submission Limits

- Successfully placed orders increment the `ORDERS` rate limit type.
- Unfilled order limits are enforced per account and shared across API keys.
- Use `account.rateLimits.orders` to monitor usage.
- Responses that exceed the limit return **status 429** with a `retryAfter` field.

Example response illustrating order usage windows:

```json
{
  "id": "e2a85d9f-07a5-4f94-8d5f-789dc3deb097",
  "status": 200,
  "result": {
    "symbol": "BTCUSDT",
    "orderId": 12510053279,
    "orderListId": -1,
    "clientOrderId": "a097fe6304b20a7e4fc436",
    "transactTime": 1655716096505,
    "price": "0.10000000",
    "origQty": "10.00000000",
    "executedQty": "0.00000000",
    "origQuoteOrderQty": "0.000000",
    "cummulativeQuoteQty": "0.00000000",
    "status": "NEW",
    "timeInForce": "GTC",
    "type": "LIMIT",
    "side": "BUY",
    "workingTime": 1655716096505,
    "selfTradePreventionMode": "NONE"
  },
  "rateLimits": [
    {
      "rateLimitType": "ORDERS",
      "interval": "SECOND",
      "intervalNum": 10,
      "limit": 50,
      "count": 12
    },
    {
      "rateLimitType": "ORDERS",
      "interval": "DAY",
      "intervalNum": 1,
      "limit": 160000,
      "count": 4043
    },
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 6000,
      "count": 321
    }
  ]
}
```

## Handling Limit Violations

- Status **429** (Too Many Requests): wait until `retryAfter` before retrying.
- Status **418** (Banned): cease requests until the ban expires; repeated offenses increase ban duration.
- Always implement exponential backoff and monitor the `rateLimits` data to avoid disruptions.

