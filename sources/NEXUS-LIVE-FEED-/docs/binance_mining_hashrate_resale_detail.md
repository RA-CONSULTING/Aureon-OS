# Binance Mining Hashrate Resale Detail (USER_DATA)

_Last updated: 2025-10-24_

Retrieve the detailed profit history for a specific Hashrate Resale configuration. This endpoint enumerates daily payouts that were transferred between mining sub-accounts for a given `configId` and mining username.

- **Endpoint:** `GET /sapi/v1/mining/hash-transfer/profit/details`
- **Weight:** 5
- **Security:** Requires an API Key header and an HMAC SHA256 signature (USER_DATA).

## Request Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `configId` | Integer | Yes | Identifier of the Hashrate Resale configuration returned by the `hash-transfer/config/details` endpoints. |
| `userName` | String | Yes | Mining account (pool username) that owns the resale configuration. |
| `pageIndex` | Integer | No | Results page index, starting from `1`. Defaults to the first page when omitted. |
| `pageSize` | Integer | No | Number of rows per page. Minimum `10`, maximum `200`. |
| `recvWindow` | Long | No | Timestamp window in milliseconds for request validity. |
| `timestamp` | Long | Yes | Current epoch time in milliseconds used in the signature. |

### Notes

- Use the same casing for `userName` that appears in the mining account dashboard.
- Omit `pageIndex` and `pageSize` to use Binance defaults (`pageIndex = 1`, `pageSize = 200`).
- Standard USER_DATA signature rules apply (`signature=HMAC_SHA256(apiSecret, queryString)`).

## Response

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "profitTransferDetails": [
      {
        "poolUsername": "test4001",
        "toPoolUsername": "pop",
        "algoName": "sha256",
        "hashRate": 200000000000,
        "day": 20201213,
        "amount": 0.2256872,
        "coinName": "BTC"
      }
    ],
    "totalNum": 8,
    "pageSize": 200
  }
}
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | Integer | Status code (`0` indicates success). |
| `msg` | String | Error description or an empty string on success. |
| `data` | Object | Result payload containing the detail list and pagination metadata. |

### `data` Object

| Field | Type | Description |
|-------|------|-------------|
| `profitTransferDetails` | `Array<Object>` | Collection of transfer records matching the query. |
| `totalNum` | Integer | Total number of records available for the configuration. |
| `pageSize` | Integer | Page size applied to the response. |

### `profitTransferDetails[]`

| Field | Type | Description |
|-------|------|-------------|
| `poolUsername` | String | Sub-account that transferred the hashrate out. |
| `toPoolUsername` | String | Sub-account that received the transferred hashrate. |
| `algoName` | String | Mining algorithm (e.g., `sha256`). |
| `hashRate` | Long | Amount of hashrate transferred, in H/s. |
| `day` | Integer | Settlement day in `yyyyMMdd` format. |
| `amount` | Decimal | Daily income amount transferred to the receiving sub-account. |
| `coinName` | String | Asset symbol of the payout (e.g., `BTC`). |

## Usage Tips

- The endpoint returns payouts that have already been settled. Expect a one-day delay between the hashrate transfer and the appearance of the profit record.
- Combine this endpoint with `GET /sapi/v1/mining/hash-transfer/config/details` to display end-to-end resale configuration details and their realized income.
- For long histories, iterate over the pages until the total number of collected records matches `totalNum`.
