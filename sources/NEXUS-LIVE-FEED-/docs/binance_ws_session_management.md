# Binance WebSocket Session Management

This reference outlines how to authenticate and manage a WebSocket connection when
interacting with the Binance-style session layer used by the Nexus tooling. Only
**Ed25519** API keys are accepted by this flow. Each method below includes the
canonical request envelope, response shape, request weight, and parameter
contract.

## Authentication requests

Only Ed25519 keys are supported for this feature. Once a connection is
authenticated you may omit the `apiKey` and `signature` fields from subsequent
signed calls until the session is cleared or replaced. The requests below mirror
the behaviour exposed by the production WebSocket API.

## Request format

All WebSocket requests **must** be sent as JSON text frames. Every frame follows
the same envelope regardless of the method that you invoke.

```json
{
  "id": "e2a85d9f-07a5-4f94-8d5f-789dc3deb097",
  "method": "order.place",
  "params": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "price": "0.1",
    "quantity": "10",
    "timeInForce": "GTC",
    "timestamp": 1655716096498,
    "apiKey": "your_binance_api_key_here",
    "signature": "5942ad337e6779f2f4c62cd1c26dba71c91514400a24990a3e7f5edec9323f90"
  }
}
```

| Field | Type | Mandatory | Description |
| ----- | ---- | --------- | ----------- |
| `id` | string / integer / null | Yes | Correlates responses with the originating request. You may reuse identifiers so long as no two in-flight frames share the same value. |
| `method` | string | Yes | Name of the API operation. Version prefixes such as `"v3/order.place"` are accepted. |
| `params` | object | No | Method parameters. Omit the field when the call does not require inputs. |

The server does not interpret the `id` beyond echoing it in the response. Use any
format that suits your client (UUIDs, incrementing integers, timestamps, etc.).
Order of keys inside `params` is insignificant, but signatures are generated over
the canonical, alphabetically sorted representation as documented in the request
security guide.

## Log in with API key — `session.logon`

Authenticate the current WebSocket connection with an API key signed request.
After a successful login subsequent signed calls may omit the `apiKey` and
`signature` fields; the session stays bound to the authenticated key until it is
replaced or explicitly cleared. You must still provide the `timestamp` parameter
for every SIGNED request even when the session is authenticated.

- **Weight:** 2
- **Data source:** Memory

| Parameter | Type | Mandatory | Description |
|-----------|------|-----------|-------------|
| `apiKey` | string | Yes | Public API key encoded as base64. |
| `signature` | string | Yes | Ed25519 signature of the request payload. |
| `timestamp` | long | Yes | Millisecond timestamp when the signature was produced. |
| `recvWindow` | decimal | No | Optional grace period (≤ `60000`). Supports three decimal places to express microseconds. |

```json
{
  "id": "c174a2b1-3f51-4580-b200-8528bd237cb7",
  "method": "session.logon",
  "params": {
    "apiKey": "your_binance_api_key_here",
    "signature": "1cf54395b336b0a9727ef27d5d98987962bc47aca6e13fe978612d0adee066ed",
    "timestamp": 1649729878532
  }
}
```

```json
{
  "id": "c174a2b1-3f51-4580-b200-8528bd237cb7",
  "status": 200,
  "result": {
    "apiKey": "your_binance_api_key_here",
    "authorizedSince": 1649729878532,
    "connectedSince": 1649729873021,
    "returnRateLimits": false,
    "serverTime": 1649729878630,
    "userDataStream": false // is User Data Stream subscription active?
  }
}
```

## Query session status — `session.status`

Inspect the authorization state associated with the live connection. The `apiKey`
and `authorizedSince` fields return `null` when the socket is unauthenticated.

- **Weight:** 2
- **Data source:** Memory
- **Parameters:** none

```json
{
  "id": "b50c16cd-62c9-4e29-89e4-37f10111f5bf",
  "method": "session.status"
}
```

```json
{
  "id": "b50c16cd-62c9-4e29-89e4-37f10111f5bf",
  "status": 200,
  "result": {
    "apiKey": "your_binance_api_key_here",
    "authorizedSince": 1649729878532,
    "connectedSince": 1649729873021,
    "returnRateLimits": false,
    "serverTime": 1649730611671,
    "userDataStream": true // is User Data Stream subscription active?
  }
}
```

## Log out of the session — `session.logout`

Unbind the previously authenticated API key without closing the socket. Future
requests that need authorization must once again include `apiKey` and `signature`
parameters.

- **Weight:** 2
- **Data source:** Memory
- **Parameters:** none

```json
{
  "id": "c174a2b1-3f51-4580-b200-8528bd237cb7",
  "method": "session.logout"
}
```

```json
{
  "id": "c174a2b1-3f51-4580-b200-8528bd237cb7",
  "status": 200,
  "result": {
    "apiKey": null,
    "authorizedSince": null,
    "connectedSince": 1649729873021,
    "returnRateLimits": false,
    "serverTime": 1649730611671,
    "userDataStream": false // is User Data Stream subscription active?
  }
}
```

Multiple `session.logon` calls on the same connection replace the active API key.
A subsequent `session.logout` only clears the binding; the socket itself remains
open for continued use.

## Session revocation

If the authenticated API key becomes invalid (for example, its IP whitelist no
longer matches, it is deleted, or its permissions change), the next authorized
request fails and the socket automatically revokes the session. The server
returns an HTTP-like 401 status with the following payload:

```json
{
  "id": null,
  "status": 401,
  "error": {
    "code": -2015,
    "msg": "Invalid API-key, IP, or permissions for action."
  }
}
```

Once revoked, you must call `session.logon` again before sending additional
SIGNED requests.

## Authorize ad hoc requests

An authenticated connection can only track one active API key at a time. When a
request explicitly includes `apiKey` and `signature`, those values override the
authenticated key for that single call. This allows you to keep a USER_DATA key
bound to the connection while submitting specific signed requests with a TRADE
key. Each request still needs its own signature regardless of the active
session.
