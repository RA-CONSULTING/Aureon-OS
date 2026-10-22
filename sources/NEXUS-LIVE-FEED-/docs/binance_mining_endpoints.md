# Binance Mining Account Endpoints

The secure mining endpoints live under the `/sapi/v1/mining` namespace and all
require `USER_DATA` credentials. Signed requests must include a millisecond
`timestamp`, optionally a `recvWindow` (≤ `60000`), and an HMAC SHA-256
`signature` generated with the API secret.

Unless noted otherwise, mining earnings data is sourced from Binance's database
layer, which adds modest latency compared to cache-backed account queries.

---

## Earnings List — `GET /sapi/v1/mining/payment/list`

Retrieve historical earnings credited to a mining account. Rows include the
daily hashrate snapshot, the profit credited for that day, and optional
hashrate or revenue transfers. When `startDate`/`endDate` are omitted, Binance
returns the full history for the specified account.

- **Weight:** 5
- **Security Type:** `USER_DATA`
- **Data Source:** Database

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `algo` | STRING | ✅ | Mining algorithm (e.g., `sha256`). |
| `userName` | STRING | ✅ | Mining account identifier. |
| `coin` | STRING |  | Filter by settlement coin. |
| `startDate` | LONG |  | Millisecond timestamp filter (inclusive). |
| `endDate` | LONG |  | Millisecond timestamp filter (inclusive). |
| `pageIndex` | INTEGER |  | Page number (≥ 1). Defaults to 1. |
| `pageSize` | INTEGER |  | Results per page (10–200). |
| `recvWindow` | LONG |  | Optional; must be ≤ `60000`. |
| `timestamp` | LONG | ✅ | Current Unix time in milliseconds. |

### Example Request

```http
GET /sapi/v1/mining/payment/list?algo=sha256&userName=test&timestamp=1700000000000&signature=<sig>
```

### Example Response

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "accountProfits": [
      {
        "time": 1586188800000,
        "type": 31,
        "hashTransfer": null,
        "transferAmount": null,
        "dayHashRate": 129129903378244,
        "profitAmount": 8.6083060304,
        "coinName": "BTC",
        "status": 2
      },
      {
        "time": 1607529600000,
        "coinName": "BTC",
        "type": 0,
        "dayHashRate": 9942053925926,
        "profitAmount": 0.85426469,
        "hashTransfer": 200000000000,
        "transferAmount": 0.02180958,
        "status": 2
      },
      {
        "time": 1607443200000,
        "coinName": "BTC",
        "type": 31,
        "dayHashRate": 200000000000,
        "profitAmount": 0.02905916,
        "hashTransfer": null,
        "transferAmount": null,
        "status": 2
      }
    ],
    "totalNum": 3,
    "pageSize": 20
  }
}
```

**Field Notes**

- `type` enumerations:
  - `0` — Mining Wallet
  - `5` — Mining Address
  - `7` — Pool Savings
  - `8` — Transferred
  - `31` — Income Transfer
  - `32` — Hashrate Resale (Mining Wallet)
  - `33` — Hashrate Resale (Pool Savings)
- `status` codes: `0` (Unpaid), `1` (Paying), `2` (Paid).
- `hashTransfer` and `transferAmount` are populated when the earnings were
  redirected to another account or balance type.
