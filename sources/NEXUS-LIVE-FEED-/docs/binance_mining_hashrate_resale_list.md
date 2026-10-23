# Binance Mining — Hashrate Resale List

Track resale contracts that transfer hashrate from one mining sub-account to
another. The endpoint is part of the Signed Mining API surface, so the request
must include a valid signature, millisecond `timestamp`, and (optionally)
`recvWindow`.

- **Endpoint:** `GET /sapi/v1/mining/hash-transfer/config/details/list`
- **Security Type:** `USER_DATA` (HMAC SHA-256 signature)
- **Weight (per IP):** 5
- **Response Source:** Binance Mining backend

## Request Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `pageIndex` | INTEGER |  | Page index, starting at `1`. Empty defaults to the first page. |
| `pageSize` | INTEGER |  | Page size, minimum `10`, maximum `200`. |
| `recvWindow` | LONG |  | Optional; must be ≤ `60000`. |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp used for the signature. |

### Pagination Notes

- Binance returns `pageSize` echoing the effective page limit in the response
  body.
- When `pageIndex` is omitted the first page is returned automatically.

## Response

```
{
  "code": 0,
  "msg": "",
  "data": {
    "configDetails": [
      {
        "configId": 168,
        "poolUsername": "123",
        "toPoolUsername": "user1",
        "algoName": "Ethash",
        "hashRate": 5000000,
        "startDay": 20201210,
        "endDay": 20210405,
        "status": 1
      },
      {
        "configId": 166,
        "poolUsername": "pop",
        "toPoolUsername": "111111",
        "algoName": "Ethash",
        "hashRate": 3320000,
        "startDay": 20201226,
        "endDay": 20201227,
        "status": 0
      }
    ],
    "totalNum": 21,
    "pageSize": 200
  }
}
```

### Field Reference

| Field | Description |
| --- | --- |
| `configDetails` | Array of resale contract entries returned for the requested page. |
| `configId` | Unique mining transfer configuration identifier. |
| `poolUsername` | Source mining sub-account that is transferring hashrate out. |
| `toPoolUsername` | Destination sub-account receiving the hashrate. |
| `algoName` | Mining algorithm associated with the transferred hashrate. |
| `hashRate` | Total quantity of hashrate being transferred. |
| `startDay` | Contract start date in `yyyyMMdd` format. |
| `endDay` | Contract end date in `yyyyMMdd` format. |
| `status` | Contract status: `0` Processing, `1` Cancelled, `2` Terminated. |
| `totalNum` | Total number of resale contracts that match the query. |
| `pageSize` | Page size echoed back by Binance for the current response. |

The `status` value reflects the lifecycle of each resale contract. Contracts in
"Processing" state (`0`) are still active, while `1` and `2` signal that the
transfer has been halted before or at completion.
