# Binance Request Security Overview

>> main

## Security Types and Permissions

| Security Type | Description | Typical Examples |
| --- | --- | --- |
| `NONE` | Public market data. | Exchange info, book depth, price tickers. |
| `TRADE` | Order placement and cancellation. | New order, cancel order, OCO management. |
| `USER_DATA` | Private account information. | Account balances, order status, trade history. |
| `USER_STREAM` | User Data Stream management. | Creating, keeping alive, or closing listen keys. |

API keys are permission scoped. You might keep one key with `TRADE` enabled for order execution and a separate key with only
`USER_DATA` enabled for monitoring. Trading access is disabled by default—enable it manually in the API Management console.
Keys can be created (and safely tested) on the Spot Test Network after logging in with your GitHub account. Rotate credentials
regularly and immediately revoke any key that shows suspicious activity.



Secure methods (anything other than `NONE`, with the exception of listen key management) require:

- `timestamp`: The current Unix timestamp in milliseconds or microseconds.
- `signature`: A cryptographic signature derived from the request payload and your secret key.

You may also include `recvWindow` (milliseconds, up to three decimal places). The default is `5000` and the maximum is `60000`.
`recvWindow` defines how long Binance should consider the request valid, providing protection against network jitter. Keep it as
small as practical (≤ `5000`) to minimize risk from delayed requests.

### Timing Validation

Signed requests are validated twice: once at the API gateway and again before the matching engine processes the order. The
server checks that the timestamp is within one second of its clock and inside the `recvWindow` threshold both times:

```pseudo
serverTime = getCurrentTime()
if (timestamp < (serverTime + 1 second) && (serverTime - timestamp) <= recvWindow) {
  // begin processing request
  serverTime = getCurrentTime()
  if (serverTime - timestamp <= recvWindow) {
    // forward request to Matching Engine
  } else {
    // reject request
  }
  // finish processing request
} else {
  // reject request
}
```



## HMAC (API Secret) Signatures

1. Assemble every request parameter except `signature` into `key=value` pairs joined with `&`. The order does not matter, but a
   consistent sort (alphabetical) simplifies testing.
2. Compute an HMAC-SHA-256 digest of that payload using your secret key.
3. Hex-encode the digest and append it as the `signature` parameter.

**Example request (body):**

```text
symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559
```

**Signature generation:**

```bash
echo -n "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559" \
  | openssl dgst -sha256 -hmac "<HMAC_SECRET_KEY>"
```

**curl command:**

```bash
curl -H "X-MBX-APIKEY: <HMAC_API_KEY>" \
  -X POST 'https://api.binance.com/api/v3/order' \
  -d 'symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559&signature=<HEX_SIGNATURE>'
```

The same payload can be sent as a query string, or split between query string and body. Remember that any parameters included
in the query string must also be part of the payload that is signed—missing an ampersand or parameter will change the digest.
Binance treats signatures case-insensitively, but keep the hex lowercase for consistency.

## RSA Signatures

1. Build the signature payload exactly as with HMAC (sorted `key=value` pairs joined with `&`).
2. Sign the ASCII payload with `RSASSA-PKCS1-v1_5` using SHA-256 and your private key.
3. Base64-encode the signature and URL-encode it when sending via HTTP.

```bash
PAYLOAD='symbol=BTCUSDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=0.2&timestamp=1668481559918&recvWindow=5000'
SIGNATURE=$(echo -n "$PAYLOAD" \
  | openssl dgst -sha256 -sign ./test-prv-key.pem \
  | openssl enc -base64 -A)

curl -H "X-MBX-APIKEY: <RSA_API_KEY>" \
  -X POST "https://api.binance.com/api/v3/order?$PAYLOAD&signature=$(python -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$SIGNATURE")"
```

## Ed25519 Signatures

Ed25519 keys deliver strong security with minimal computational overhead. The payload rules mirror HMAC and RSA: build the
payload string, sign it, base64-encode the signature, then attach it as the `signature` parameter.

```python
#!/usr/bin/env python3
import base64
import time
import requests
from cryptography.hazmat.primitives.serialization import load_pem_private_key

API_KEY = "<ED25519_API_KEY>"
PRIVATE_KEY_PATH = "test-prv-key.pem"

with open(PRIVATE_KEY_PATH, "rb") as handle:
    private_key = load_pem_private_key(data=handle.read(), password=None)

params = {
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "1",
    "price": "0.2",
    "timestamp": int(time.time() * 1000),
}

payload = "&".join(f"{key}={value}" for key, value in params.items())
params["signature"] = base64.b64encode(private_key.sign(payload.encode("ASCII"))).decode("ASCII")

response = requests.post(
    "https://api.binance.com/api/v3/order",
    headers={"X-MBX-APIKEY": API_KEY},
    data=params,
)
print(response.json())
```

Keep private keys encrypted at rest and never share API keys or secrets. If you detect unexpected activity, revoke the
associated keys immediately and contact Binance support.
