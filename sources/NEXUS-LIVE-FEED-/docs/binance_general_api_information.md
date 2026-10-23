# Binance General API Information

This guide consolidates the operational rules that apply to the Binance Spot production REST API. Use it as a baseline reference for connectivity requirements, request semantics, and the rate limits enforced at the gateway. For Testnet-specific nuances, see the [Binance Spot Testnet General Notes](./binance_general_endpoints.md).

## Base Endpoints
- `https://api.binance.com`
- `https://api1.binance.com`
- `https://api2.binance.com`
- `https://api3.binance.com`
- `https://api4.binance.com`

The alternate hosts (`api1`–`api4`) sometimes provide lower latency but can be less stable than the primary hostname. All endpoints return JSON objects or arrays and serialize results in ascending order (oldest first, newest last).

## Time Semantics
- All timestamps are expressed in **milliseconds** unless otherwise stated.
- You may opt into microsecond timestamps by adding the `X-MBX-TIME-UNIT: MICROSECOND` header (case-insensitive) or by supplying microsecond values in request parameters.
- When `startTime` and/or `endTime` are provided, pagination proceeds chronologically from the starting boundary and respects the configured `limit`.

## HTTP Return Codes
- **4XX** → Client-side or malformed request.
- **403** → Web Application Firewall (WAF) limit violated.
- **409** → `cancelReplace` partially succeeded (for example, cancel failed but replace succeeded).
- **429** → Request or order rate limit breached.
- **418** → IP auto-banned after repeated 429 violations.
- **5XX** → Internal error; treat the execution status as **unknown** and confirm via a follow-up query or stream event.

See [HTTP Return Codes](./http_return_codes.md) for a dedicated quick reference.

## Error Payload
Errors are returned as JSON objects containing a numeric code and descriptive message:

```json
{
  "code": -1121,
  "msg": "Invalid symbol."
}
```

Refer to the [Binance Error Codes](./binance_error_codes.md) catalog for the complete mapping.

## Parameter Handling
- **GET** endpoints expect parameters in the query string.
- **POST**, **PUT**, and **DELETE** endpoints accept parameters either in the query string or request body (`application/x-www-form-urlencoded`). Mixing locations is supported; when duplicates exist the query string wins.
- Parameters may be transmitted in any order.

## Rate Limit Overview
Binance publishes the authoritative rate limit configuration through the `rateLimits` array in `GET /api/v3/exchangeInfo`. Headers also expose real-time usage counters:

- `X-MBX-USED-WEIGHT-(intervalNum)(intervalLetter)` → request weight consumed per IP for the associated limiter.
- `X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)` → orders acknowledged by the account for each order limiter (present on successful order responses).

When a limiter is exceeded the server returns **429**. Clients must back off and honor the `Retry-After` header (present on 429/418 responses). Repeated violations can result in auto-bans with increasing durations (2 minutes up to 3 days). The limits apply on a **per-IP** basis; switching API keys does not reset counters.

For a deeper breakdown, consult the [Binance Rate Limits](./binance_rate_limits.md) and [Binance Spot Unfilled Order Count](./binance_spot_unfilled_order_count.md) guides.

### IP Limits
- Every response includes `X-MBX-USED-WEIGHT-*` headers for each defined limiter.
- Each REST route carries a weight cost; multi-symbol and bulk endpoints have heavier weights.
- A **418** indicates an automated IP ban triggered by continued requests after a 429. Wait for the `Retry-After` duration before reconnecting.

### Order Rate Limits
- Only successful order acknowledgements increment the `X-MBX-ORDER-COUNT-*` headers.
- Exceeding the order quota yields a **429** without `Retry-After`. Monitor `GET /api/v3/rateLimit/order` to observe current consumption.

### WebSocket Limits
- A single connection may send up to **5 incoming messages per second** (counting pings, pongs, and JSON control frames).
- Maximum of **1024 streams** per connection.
- Limit of **300 connection attempts per 5-minute window per IP**.
- Connections exceeding the limits are disconnected; repeated violations may trigger bans.

### `/api/` vs `/sapi/`
- `/api/*` endpoints share a combined **6000 weight/minute** limit per IP. Successful orders also expose the order-count headers described above.
- `/sapi/*` endpoints are annotated as **IP-limited** or **UID-limited**:
  - IP-limited routes → **12,000 weight/minute** per IP with `X-SAPI-USED-IP-WEIGHT-1M` headers.
  - UID-limited routes → **180,000 weight/minute** per account with `X-SAPI-USED-UID-WEIGHT-1M` headers.

## Data Sources
Each endpoint advertises the data source that feeds its response, listed from most to least current:
1. **Matching Engine**
2. **Memory**
3. **Database**

Endpoints can fall back through multiple sources; for example, `Memory ⇒ Database` means the service checks in-memory caches before hitting the database.

## Endpoint Security Types
Endpoints declare their security type, which dictates authentication and signing requirements:

| Security Type | Description |
| ------------- | ----------- |
| `NONE` | Public endpoints; no key required. |
| `USER_STREAM` | Requires a valid API key; no signature. |
| `MARKET_DATA` | Requires a valid API key; no signature. |
| `TRADE` / `MARGIN` / `USER_DATA` | Require both an API key and a signature. |

API keys are supplied via the `X-MBX-APIKEY` header. Keys and secret material are case-sensitive and can be scoped to specific permissions.

## Signed Endpoint Requirements
Signed endpoints (TRADE, USER_DATA, and MARGIN) require two additional parameters:

- `timestamp` → Millisecond timestamp when the request was generated.
- `signature` → HMAC SHA256 or RSA signature of the concatenated query string + body (`totalParams`).
- Optional `recvWindow` (default 5000 ms) defines how long the request remains valid.

A request is processed only when `timestamp < serverTime + 1000` and `serverTime - timestamp <= recvWindow`. Larger windows are allowed up to 60,000 ms, but Binance recommends keeping them at 5,000 ms or lower to account for network jitter.

### HMAC SHA256 Workflow
1. Concatenate parameters into a `key=value` string separated by `&` (query + body in any order).
2. Sign the string using HMAC SHA256 with the API secret as the key.
3. Append the resulting hex digest as the `signature` parameter.

Example:

```bash
echo -n "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559" \
  | openssl dgst -sha256 -hmac "<secretKey>"
# (stdin)= c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71

curl -H "X-MBX-APIKEY: <apiKey>" -X POST \
  'https://api.binance.com/api/v3/order?symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559&signature=c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71'
```

### RSA (PKCS#8) Workflow
1. Concatenate parameters as before.
2. Sign using RSASSA-PKCS1-v1_5 with SHA-256.
3. Base64-encode the signature, then URL-encode it when transmitting via query/body.

```bash
payload='symbol=BTCUSDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=0.2&timestamp=1668481559918&recvWindow=5000'
base64_sig=$(echo -n "$payload" \
  | openssl dgst -sha256 -sign ./test-prv-key.pem \
  | openssl enc -base64 -A)

curl -H "X-MBX-APIKEY: <apiKey>" -X POST \
  "https://api.binance.com/api/v3/order?$payload" \
  --data-urlencode "signature=$base64_sig"
```

A sample Bash helper script illustrating these steps is included below:

```bash
#!/usr/bin/env bash
API_KEY="<apiKey>"
PRIVATE_KEY_PATH="test-prv-key.pem"
API_METHOD="POST"
API_CALL="api/v3/order"
API_PARAMS="symbol=BTCUSDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=0.2"

timestamp=$(date +%s000)
params_with_ts="$API_PARAMS&timestamp=$timestamp"
signature=$(echo -n "$params_with_ts" \
  | openssl dgst -sha256 -sign "$PRIVATE_KEY_PATH" \
  | openssl enc -base64 -A)

curl -H "X-MBX-APIKEY: $API_KEY" -X "$API_METHOD" \
  "https://api.binance.com/$API_CALL?$params_with_ts" \
  --data-urlencode "signature=$signature"
```

Following these patterns ensures that every signed request satisfies Binance's timing and authentication requirements while preserving deterministic ordering of parameters.
