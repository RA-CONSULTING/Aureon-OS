# Binance Mining Account Earnings — `GET /sapi/v1/mining/payment/uid`

_Last updated: 2025-10-24_

Retrieve the mining rebate, referral, and refund earnings accrued by a master account and its sub-accounts. Results are returned
in reverse-chronological order and can be filtered by mining algorithm and optional time range.

- **Endpoint:** `GET /sapi/v1/mining/payment/uid`
- **Weight:** 5
- **Security Type:** USER_DATA (HMAC SHA-256 signature required)
- **Response Data Source:** Database-backed ledger

## Request parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `algo` | STRING | ✅ | Mining algorithm identifier (e.g., `sha256`). |
| `startDate` | LONG |  | Filter results to earnings posted on/after this millisecond timestamp. |
| `endDate` | LONG |  | Filter results to earnings posted on/before this millisecond timestamp. Must be ≥ `startDate`. |
| `pageIndex` | INTEGER |  | Results page to fetch. Defaults to `1`. |
| `pageSize` | INTEGER |  | Number of records per page. Minimum `10`, maximum `200`. Defaults to `20`. |
| `recvWindow` | LONG |  | Optional tolerance for the `timestamp` check (milliseconds). Must be ≤ `60000`. |
| `timestamp` | LONG | ✅ | Current UNIX time in milliseconds when the request is signed. |
| `signature` | STRING | ✅ | HMAC SHA-256 signature created with the mining API secret over the query string. |

### Example request

```
GET /sapi/v1/mining/payment/uid?algo=sha256&pageIndex=1&pageSize=20&timestamp=1698153600000&signature=<signature>
```

Sign the query string parameters in lexicographical order using the API secret and append the resulting `signature` value to the
request. The endpoint must be called over HTTPS with the API key supplied in the `X-MBX-APIKEY` header.

## Response

Successful calls return HTTP 200 with the following payload:

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "accountProfits": [
      {
        "time": 1607443200000,
        "coinName": "BTC",
        "type": 2,
        "puid": 59985472,
        "subName": "vdvaghani",
        "amount": 0.09186957
      }
    ],
    "totalNum": 3,
    "pageSize": 20
  }
}
```

### Field reference

| Field | Description |
| --- | --- |
| `code` | `0` indicates success. Non-zero codes map to mining API errors. |
| `msg` | Optional text message accompanying non-zero error codes. Empty on success. |
| `data.accountProfits` | Array of earning records for the requested page. Empty when no earnings match the filters. |
| `accountProfits[].time` | Millisecond timestamp when the earning was credited. |
| `accountProfits[].coinName` | Asset symbol of the distributed reward (e.g., `BTC`). |
| `accountProfits[].type` | Earning type. `0` = Referral, `1` = Refund, `2` = Rebate. |
| `accountProfits[].puid` | Numeric identifier of the sub-account (`puid`) that received the distribution. |
| `accountProfits[].subName` | Human-readable mining account name. |
| `accountProfits[].amount` | Reward quantity credited in the `coinName` asset. |
| `data.totalNum` | Total number of records available for the given filters. Use with `pageSize` to paginate. |
| `data.pageSize` | Number of records per page in the response. Matches the request's `pageSize` or the default `20`. |

## Usage notes

- When both `startDate` and `endDate` are omitted, Binance returns the most recent 20 earnings.
- Pagination is 1-indexed. Request `pageIndex = 1` for the first page.
- The endpoint surfaces earnings for the master account and any linked sub-accounts. Filter on the client side if only a subset
  of accounts is relevant.
- Expect earnings to post on a daily cadence. Historical corrections appear as refunds (`type = 1`).
