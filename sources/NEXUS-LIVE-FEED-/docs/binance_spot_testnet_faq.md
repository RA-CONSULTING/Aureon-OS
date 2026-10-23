# Binance Spot Testnet FAQ

This FAQ compiles the key behaviors, endpoint mappings, authentication flows, and operational guardrails for the Binance Spot Test Network.

## Getting Started

1. **Generate an API key** – Sign in to the Spot Test Network portal and create a key pair.
2. **Target the testnet endpoints** – Replace the production REST and WebSocket URLs with the testnet hosts listed below.

### REST API Hosts

| Production Endpoint | Spot Test Network Endpoint |
|---------------------|-----------------------------|
| `https://api.binance.com/api` | `https://testnet.binance.vision/api` |
| `https://api-gcp.binance.com/api` | `https://testnet.binance.vision/api` |
| `https://api1.binance.com/api` | `https://api1.testnet.binance.vision/api` |
| `https://api2.binance.com/api` | `https://api2.testnet.binance.vision/api` |
| `https://api3.binance.com/api` | `https://api3.testnet.binance.vision/api` |
| `https://api4.binance.com/api` | `https://api4.testnet.binance.vision/api` |

### WebSocket API v3

| Production Endpoint | Spot Test Network Endpoint |
|---------------------|-----------------------------|
| `wss://ws-api.binance.com/ws-api/v3` | `wss://ws-api.testnet.binance.vision/ws-api/v3` |
| `wss://ws-api.binance.com:9443/ws-api/v3` | `wss://ws-api.testnet.binance.vision:9443/ws-api/v3` |

### Market Streams

| Production Endpoint | Spot Test Network Endpoint |
|---------------------|-----------------------------|
| `wss://stream.binance.com/ws` | `wss://stream.testnet.binance.vision/stream` |
| `wss://stream.binance.com:9443/ws` | `wss://stream.testnet.binance.vision:9443/stream` |
| `wss://stream.binance.com/stream` | `wss://stream.testnet.binance.vision/stream` |
| `wss://stream.binance.com:9443/stream` | `wss://stream.testnet.binance.vision:9443/stream` |

### SBE Streams

| Production Endpoint | Spot Test Network Endpoint |
|---------------------|-----------------------------|
| `wss://stream-sbe.binance.com/ws` | `wss://stream-sbe.testnet.binance.vision/ws` |
| `wss://stream-sbe.binance.com:9443/ws` | `wss://stream-sbe.testnet.binance.vision:9443/ws` |
| `wss://stream-sbe.binance.com/stream` | `wss://stream-sbe.testnet.binance.vision/stream` |
| `wss://stream-sbe.binance.com:9443/stream` | `wss://stream-sbe.testnet.binance.vision:9443/stream` |

### FIX Sessions

| Production Endpoint | Spot Test Network Endpoint |
|---------------------|-----------------------------|
| `tcp+tls://fix-oe.binance.com:9000` | `tcp+tls://fix-oe.testnet.binance.vision:9000` |
| `tcp+tls://fix-dc.binance.com:9000` | `tcp+tls://fix-dc.testnet.binance.vision:9000` |
| `tcp+tls://fix-md.binance.com:9000` | `tcp+tls://fix-md.testnet.binance.vision:9000` |

## Available Interfaces

Only the `/api` namespace is exposed on the Spot Test Network. `/sapi` routes are unavailable. Supported features include:

- Market Data Endpoints (REST)
- Market Data Requests (WebSocket API)
- WebSocket market streams
- Trading Endpoints (REST)
- Account Endpoints (REST)
- Trading Requests (WebSocket API)
- Account Requests (WebSocket API)
- User Data Streams

## Funding Behavior

- Accounts receive a simulated asset balance at registration.
- Balances are **virtual** and cannot be deposited to or withdrawn from production.

## Platform Resets

- The Spot Test Network resets roughly **once per month**.
- Resets wipe all active, pending, and historical orders.
- After each reset, accounts are replenished with the default test balances.
- Since August 2020, API keys persist through resets.

## Reference Data

- Rate limits, exchange filters, and symbol filters largely mirror production behavior.
- Fetch current metadata as needed, for example:
  
  ```bash
  curl "https://testnet.binance.vision/api/v3/exchangeInfo"
  ```

## Kline Endpoints

- `klines` and `uiKlines` return identical data on the Spot Test Network.

## RSA API Keys

RSA keys (2048–4096 bits) are accepted. Use the PKCS#1 v1.5 signature scheme.

### Generate Keys

```bash
openssl genrsa -out test-prv-key.pem 2048
openssl rsa -in test-prv-key.pem -pubout -outform PEM -out test-pub-key.pem
```

Register the public key with Binance and retain the API key returned during registration for the `X-MBX-APIKEY` header.

### Example Request Flow (Bash)

```bash
#!/usr/bin/env bash
API_KEY="put your own API Key here"
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
    "https://testnet.binance.vision/$API_CALL?$api_params_with_timestamp" \
    --data-urlencode "signature=$signature"
```

## Ed25519 API Keys

Ed25519 keys provide shorter, faster signatures with security comparable to 3072-bit RSA keys.

### Generate Keys

```bash
openssl genpkey -algorithm ed25519 -out test-prv-key.pem
openssl pkey -pubout -in test-prv-key.pem -out test-pub-key.pem
```

Register the public key and capture the issued API key for the `X-MBX-APIKEY` header.

### Example Request Flow (Python)

```python
#!/usr/bin/env python3
import base64
import requests
import time
from cryptography.hazmat.primitives.serialization import load_pem_private_key

API_KEY = "put your own API Key here"
PRIVATE_KEY_PATH = "test-prv-key.pem"

with open(PRIVATE_KEY_PATH, "rb") as f:
    private_key = load_pem_private_key(data=f.read(), password=None)

params = {
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "1.0000000",
    "price": "0.20",
}

params["timestamp"] = int(time.time() * 1000)
payload = "&".join([f"{param}={value}" for param, value in params.items()])
signature = base64.b64encode(private_key.sign(payload.encode("ASCII")))
params["signature"] = signature

headers = {"X-MBX-APIKEY": API_KEY}
response = requests.post(
    "https://testnet.binance.vision/api/v3/order",
    headers=headers,
    data=params,
)
print(response.json())
```

## RSA vs. Ed25519 Signature Sizes

| API Key Type | Signature Size | Approximate Signing Time |
|--------------|----------------|--------------------------|
| HMAC-SHA-256 | 64 bytes | 0.00 ms |
| Ed25519 | 88 bytes | 0.03 ms |
| RSA (2048-bit) | 344 bytes | 0.55 ms |
| RSA (4096-bit) | 684 bytes | 3.42 ms |

## Connectivity Summary

- **WebSocket API v3**: `wss://ws-api.testnet.binance.vision/ws-api/v3` (port 9443 variant also available).
- **WebSocket Market Streams**: `wss://stream.testnet.binance.vision/stream` (port 9443 variant also available).
- **WebSocket SBE Streams**: `wss://stream-sbe.testnet.binance.vision/ws` and `/stream` (port 9443 variants available).
- **FIX Sessions**: `tcp+tls://fix-oe.testnet.binance.vision:9000`, `tcp+tls://fix-dc.testnet.binance.vision:9000`, `tcp+tls://fix-md.testnet.binance.vision:9000`.

These endpoints mirror the production layout, enabling developers to test REST, WebSocket, and FIX integrations without risking live capital.
