# Binance Mining Extra Bonus List — `GET /sapi/v1/mining/payment/other`

This signed endpoint returns supplemental mining payouts that do not appear in
the standard daily income log. Nexus uses it to reconcile Smart Pool earnings,
rebates, and other credits that accrue outside of the primary settlement path.
Each row in the response represents a discrete credit applied to the mining
account.

- **Endpoint:** `GET /sapi/v1/mining/payment/other`
- **Security Type:** `USER_DATA` (HMAC SHA-256 signature required)
- **Request Weight:** `5`
- **Data Source:** Database

---

## Request Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `algo` | STRING | ✅ | Mining algorithm identifier (e.g., `sha256`, `ethash`). Must match the algorithm configured for the mining account. |
| `userName` | STRING | ✅ | Mining account login name. Case-sensitive. |
| `coin` | STRING |  | Limits results to a single coin ticker (e.g., `BTC`). When omitted, all coins under the algorithm are returned. |
| `startDate` | LONG |  | Inclusive start timestamp (milliseconds since epoch). Leave empty to scan the entire history. |
| `endDate` | LONG |  | Inclusive end timestamp (milliseconds since epoch). Leave empty to scan the entire history. |
| `pageIndex` | INTEGER |  | Results page to fetch. Defaults to `1`. |
| `pageSize` | INTEGER |  | Number of rows per page. Minimum `10`, maximum `200`. Default is `20`. |
| `recvWindow` | LONG |  | Optional timestamp skew allowance in milliseconds (≤ `60000`). |
| `timestamp` | LONG | ✅ | Current millisecond timestamp. Must be signed together with the query string. |

**Signature Notes**

Include all query parameters except `signature` in the signing payload, using the
standard Binance concatenation (`key=value` pairs joined with `&`). Use the
mining API key that is provisioned for the target account.

---

## Response Structure

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "otherProfits": [
      {
        "time": 1607443200000,
        "coinName": "BTC",
        "type": 4,
        "profitAmount": 0.0011859,
        "status": 2
      }
    ],
    "totalNum": 3,
    "pageSize": 20
  }
}
```

### Top-Level Fields

| Field | Type | Description |
| --- | --- | --- |
| `code` | INT | `0` when the request succeeds. Non-zero values indicate an error. |
| `msg` | STRING | Error details when `code ≠ 0`; empty when successful. |
| `data` | OBJECT | Container for the paginated result set. |

### `data` Object

| Field | Type | Description |
| --- | --- | --- |
| `otherProfits` | ARRAY of OBJECT | Individual payout records for the requested time span. |
| `totalNum` | INT | Total number of matching records across all pages. |
| `pageSize` | INT | Page size echoed from the request (defaults to `20`). |

### `otherProfits[]` Payload

| Field | Type | Description |
| --- | --- | --- |
| `time` | LONG | Settlement timestamp (milliseconds since epoch). Corresponds to the mining date. |
| `coinName` | STRING | Asset credited to the mining account. |
| `type` | INT | Bonus category code. See table below. |
| `profitAmount` | DECIMAL | Amount of the bonus credited in `coinName` units. |
| `status` | INT | Payout status. See table below. |

#### Bonus Type Codes

| Code | Description |
| --- | --- |
| `1` | Merged Mining |
| `2` | Activity Bonus |
| `3` | Rebate |
| `4` | Smart Pool |
| `6` | Income Transfer |
| `7` | Pool Savings |

#### Status Codes

| Code | Description |
| --- | --- |
| `0` | Unpaid — credit scheduled but not yet distributed. |
| `1` | Paying — payout is in progress. |
| `2` | Paid — credit has been fully applied. |

---

## Usage Tips

- Binance orders records by `time` descending. Use `pageIndex` to paginate
  through older payouts when reconciling long histories.
- When `startDate`/`endDate` are omitted, Binance returns the most recent page of
  bonuses first.
- Apply the same `recvWindow` used for other mining endpoints to keep signature
  validation consistent across requests.
- Combine this dataset with `/sapi/v1/mining/payment/list` to produce a full
  ledger of daily income plus supplemental credits.

