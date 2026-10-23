# Binance Mining Hashrate Resale Request — `POST /sapi/v1/mining/hash-transfer/config`

Submit a resale configuration that transfers a portion of a mining account's hashrate to another Binance Pool account. The resale starts and ends at the millisecond timestamps you provide, and the transfer only becomes effective once Binance validates that the source account holds at least the requested hash power.

- **Request Weight:** 5
- **Security:** Signed (HMAC SHA-256 of the query string using the mining account's API secret)

## Request Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `userName` | STRING | ✅ | Source mining account initiating the resale. |
| `algo` | STRING | ✅ | Mining algorithm of the hashrate being transferred (e.g., `sha256`). |
| `endDate` | LONG | ✅ | Millisecond timestamp when the resale stops. Must be greater than `startDate`. |
| `startDate` | LONG | ✅ | Millisecond timestamp when the resale begins. |
| `toPoolUser` | STRING | ✅ | Destination Binance Pool mining account receiving the hash power. |
| `hashRate` | LONG | ✅ | Hashrate to transfer in h/s. Minimums: BTC ≥ 500,000,000,000; ETH ≥ 500,000. |
| `recvWindow` | LONG |  | Optional override for the request validity window (max 60,000 ms). |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp of the request. Used for replay protection. |

> ℹ️ Include the `signature` parameter in the query string; although not listed in the upstream schema, every Mining Signed endpoint requires it. The signature is calculated from all query parameters including `timestamp` and `recvWindow`.

## Example Request

```http
POST /sapi/v1/mining/hash-transfer/config?userName=test&algo=sha256&startDate=1607659086000&endDate=1617659086000&toPoolUser=S19pro&hashRate=100000000&timestamp=1617659086123&signature=<calculated_signature>
```

## Example Response

```json
{
  "code": 0,
  "msg": "",
  "data": 171
}
```

`data` returns the target mining account ID once Binance accepts the resale configuration. A non-zero `code` indicates that the request failed; consult `binance_error_codes.md` for diagnostic guidance.
