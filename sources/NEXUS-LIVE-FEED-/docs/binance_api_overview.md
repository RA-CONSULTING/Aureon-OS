# Binance REST API Overview

## Base Endpoints
- `https://api.binance.com`
- `https://api1.binance.com`
- `https://api2.binance.com`
- `https://api3.binance.com`
- `https://api4.binance.com`

> The alternate `api1`-`api4` domains can offer better performance but are typically less stable.

## Response Format
- Responses are JSON objects or arrays.
- Results are sorted in ascending order (oldest first).
- All timestamps are expressed in **milliseconds**.

## HTTP Status Codes
- **4XX**: Client errors (malformed requests).
- **403**: Web Application Firewall (WAF) limit violated.
- **409**: `cancelReplace` partially succeeded.
- **418**: IP auto-ban after repeated rate-limit violations.
- **429**: Request or order rate limit reached.
- **5XX**: Internal server errors (execution status is unknown).

## Error Payload Structure
```json
{
  "code": -1121,
  "msg": "Invalid symbol."
}
```
Refer to the official *Error Codes* documentation for the complete list of codes and messages.

## Parameter Handling
- GET parameters must be sent as a query string.
- POST/PUT/DELETE parameters can be in the query string or request body (`application/x-www-form-urlencoded`).
- Parameters can be mixed between query and body; the query string takes precedence when duplicated.
- Parameter order does not matter.

## Rate Limits
Binance enforces several limit types (RAW_REQUESTS, REQUEST_WEIGHT, ORDERS). You can retrieve limit definitions via `GET /api/v3/exchangeInfo` in the `rateLimits` array.

### General
- Response headers include `X-MBX-USED-WEIGHT-(intervalNum)(intervalLetter)` showing request usage for the IP.
- Exceeding a limit returns HTTP **429**. Clients should back off immediately to avoid bans.
- Repeat violations trigger automatic IP bans (HTTP **418**). `Retry-After` headers indicate backoff durations.

### IP Limits
- Each endpoint has a weight indicating its cost toward rate limits.
- Weight usage headers are returned per request.

### Order Limits
- Successful order responses include `X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)` headers.
- Violations return HTTP **429** without `Retry-After`. Check `GET /api/v3/rateLimit/order` for reactivation timing.
- Order counts are per account; rejected orders may not include headers.

### WebSocket Limits
- Maximum **5 incoming messages/second** per connection (PING, PONG, or JSON control messages).
- Connections exceeding the limit are disconnected; repeated offenses risk bans.
- Each connection supports up to **1024 streams**.
- Up to **300 connection attempts** per 5-minute window per IP.

### /api/ and /sapi/ Limits
- `/api/*` endpoints: 6000 weight/minute per IP, with headers `X-MBX-USED-WEIGHT-(intervalNum)(intervalLetter)`.
- `/sapi/*` endpoints distinguish IP vs. UID (account) limits, with headers `X-SAPI-USED-IP-WEIGHT-1M` or `X-SAPI-USED-UID-WEIGHT-1M`.
- `/sapi/*` endpoints with IP limits allow 12000 weight/minute; UID-limited endpoints allow 180000 weight/minute.

## Data Sources
Endpoints may draw from:
1. Matching Engine (most current)
2. Memory
3. Database (potential delays)

If a value is missing from a primary source, the next source is queried.

## Security Types
- **NONE**: No authentication required.
- **USER_STREAM** / **MARKET_DATA**: API key required.
- **TRADE**, **MARGIN**, **USER_DATA**: API key and signature required.

API keys are case sensitive and scoped to permissions configured in your Binance account.

## Signed Endpoints
Signed endpoints (TRADE/MARGIN/USER_DATA) require:
- `timestamp` (milliseconds when the request was created).
- Optional `recvWindow` (default 5000 ms, max 60000).
- `signature` generated with HMAC SHA256 (for secret keys) or RSA (PKCS#8) depending on your API key type.

### Timing Validation Logic
```
if (timestamp < serverTime + 1000 && (serverTime - timestamp) <= recvWindow) {
  // request accepted
} else {
  // request rejected
}
```

### HMAC SHA256 Signing Example (POST /api/v3/order)
Parameters:
```
symbol=LTCBTC
side=BUY
type=LIMIT
timeInForce=GTC
quantity=1
price=0.1
recvWindow=5000
timestamp=1499827319559
```

Signature command:
```bash
echo -n "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559" \
  | openssl dgst -sha256 -hmac "<secretKey>"
```

#### Example Requests
- **All parameters in body:**
  ```bash
  curl -H "X-MBX-APIKEY: <apiKey>" -X POST 'https://api.binance.com/api/v3/order' \
    -d 'symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559&signature=<signature>'
  ```
- **All parameters in query:**
  ```bash
  curl -H "X-MBX-APIKEY: <apiKey>" -X POST 'https://api.binance.com/api/v3/order?symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559&signature=<signature>'
  ```
- **Mixed query/body:**
  ```bash
  curl -H "X-MBX-APIKEY: <apiKey>" -X POST 'https://api.binance.com/api/v3/order?symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC' \
    -d 'quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559&signature=<signature>'
  ```

> Note: When mixing query and body parameters, ensure the concatenated string used for signing matches the exact parameter order and separators.

### RSA Signing Example (POST /api/v3/order)
Parameters:
```
symbol=BTCUSDT
side=SELL
type=LIMIT
timeInForce=GTC
quantity=1
price=0.2
recvWindow=5000
timestamp=1668481559918
```

Steps:
1. Concatenate parameters with `&` separators.
2. Sign using RSASSA-PKCS1-v1_5 with SHA-256.
   ```bash
   echo -n 'symbol=BTCUSDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=0.2&timestamp=1668481559918&recvWindow=5000' \
     | openssl dgst -sha256 -sign ./test-prv-key.pem
   ```
3. Base64 encode the result, then URL-encode if necessary.
4. Send the signed request:
   ```bash
   curl -H "X-MBX-APIKEY: <apiKey>" -X POST 'https://api.binance.com/api/v3/order?symbol=BTCUSDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=0.2&timestamp=1668481559918&recvWindow=5000' \
     --data-urlencode "signature=<urlEncodedSignature>"
   ```

### Sample Bash Script (RSA Signing)
```bash
#!/usr/bin/env bash
API_KEY="<apiKey>"
PRIVATE_KEY_PATH="test-prv-key.pem"
API_METHOD="POST"
API_CALL="api/v3/order"
API_PARAMS="symbol=BTCUSDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=0.2"

timestamp=$(date +%s000)
api_params_with_timestamp="$API_PARAMS&timestamp=$timestamp"
signature=$(echo -n "$api_params_with_timestamp" \
  | openssl dgst -sha256 -sign "$PRIVATE_KEY_PATH" \
  | openssl enc -base64 -A)

curl -H "X-MBX-APIKEY: $API_KEY" -X "$API_METHOD" \
  "https://api.binance.com/$API_CALL?$api_params_with_timestamp" \
  --data-urlencode "signature=$signature"
```

## Best Practices
- Prefer WebSockets for streaming data to reduce REST request weight.
- Always honor `Retry-After` headers and back off after 429/418 responses.
- Keep `recvWindow` small (≤ 5000 ms) to minimize timing issues.
- Ensure system clocks are synchronized to avoid timestamp validation failures.

