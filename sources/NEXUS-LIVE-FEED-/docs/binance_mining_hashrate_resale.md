# Binance Mining Hashrate Resale API

The Binance Mining REST surface exposes user data endpoints for managing
hashrate resale agreements. All routes reside under the `/sapi/v1/mining`
namespace and require a valid API key with Mining permissions plus an HMAC
SHA-256 signature generated from the query string and API secret.

---

## Cancel Hashrate Resale Configuration — `POST /sapi/v1/mining/hash-transfer/config/cancel`

Cancel an existing resale configuration so that the specified mining account
stops transferring hashrate to the configured recipient. The request consumes a
`REQUEST_WEIGHT` of **5** and must include a signed `timestamp`.

- **Security Type:** `USER_DATA`
- **Weight:** 5
- **Response:** Boolean flag (`true` on success)

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `configId` | INTEGER | ✅ | Identifier of the resale configuration returned by the hash transfer detail endpoints. |
| `userName` | STRING | ✅ | Mining account name associated with the configuration. |
| `recvWindow` | LONG |  | Optional request validity window in milliseconds (max `60000`). |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp used for the signature. |

### Example Request

```bash
curl -X POST "https://api.binance.com/sapi/v1/mining/hash-transfer/config/cancel" \
  -H "X-MBX-APIKEY: <api_key>" \
  -d "configId=168" \
  -d "userName=test" \
  -d "timestamp=$(date +%s000)" \
  -d "signature=<computed_signature>"
```

### Example Response

```json
{
  "code": 0,
  "msg": "",
  "data": true
}
```

A response with `data: true` confirms that Binance accepted the cancellation.
If the configuration has already been deactivated or does not belong to the
provided `userName`, Binance returns an error code describing the failure.
