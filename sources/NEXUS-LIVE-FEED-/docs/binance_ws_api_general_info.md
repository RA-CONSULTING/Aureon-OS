# Binance Testnet WebSocket API v3 — General Information

The Binance Spot Testnet WebSocket API v3 is reachable at:

- Primary endpoint: `wss://ws-api.testnet.binance.vision/ws-api/v3`
- Alternate port (if port 443 is blocked): `wss://ws-api.testnet.binance.vision:9443/ws-api/v3`

Connections are valid for a maximum of **24 hours**. The server disconnects sessions that
exceed this lifetime.

## Authentication

The WebSocket API supports **HMAC**, **RSA**, and **Ed25519** keys. Refer to the API Key
type documentation for the capabilities and restrictions of each key class.

## Request / Response Semantics

- Responses default to **JSON** payloads. Opt into SBE by including `responseType=SBE`
or the corresponding parameter described in the SBE FAQ.
- Data is returned in **chronological order** unless explicitly stated otherwise.
- `startTime` / `endTime` parameters control pagination:
  - With neither parameter: returns the most recent items up to `limit`.
  - With only `startTime`: returns the oldest items from `startTime` up to `limit`.
  - With only `endTime`: returns the most recent items up to `endTime` and `limit`.
  - With both: behaves like `startTime` pagination but will not exceed `endTime`.
- Timestamp parameters accept **milliseconds** or **microseconds**. Add
  `timeUnit=MICROSECOND` (or `timeUnit=microsecond`) to opt into microsecond
  serialization in responses.
- All field names and values are **case-sensitive** unless otherwise documented.

## Connection Management

- The server sends a **ping frame every 20 seconds**. Reply with a pong containing the
  same payload as soon as possible.
- Failure to return a pong within **60 seconds** results in a disconnect.
- Unsolicited pong frames are allowed but do **not** reset the timeout window.
  Binance recommends leaving their payloads empty.
- The server enforces a **10-second processing timeout**. If the matching engine takes
  longer, the API returns error `-1007 (TIMEOUT)` with the message:
  `"Timeout waiting for response from backend server. Send status unknown; execution status unknown."`
  The request may still succeed; confirm via the User Data Stream or a follow-up status
  query.

## Session Lifetime and Disconnect Handling

- Expect connections to terminate at the **24-hour mark**. Reconnect proactively if the
  session must remain open longer.
- If a response does not arrive and no user data event confirms the outcome, perform an
  explicit **status query** to reconcile state.

## Additional References

- [API Key Types](https://binance-docs.github.io/apidocs/spot/en/#api-key-types)
- [SBE FAQ](https://binance-docs.github.io/apidocs/spot/en/#simple-binary-encoding-sbe)
- [SPOT Glossary](https://binance-docs.github.io/apidocs/spot/en/#public-rest-api-glossary)
