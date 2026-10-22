# Binance Mining Worker List (USER_DATA)

_Last updated: 2025-10-24_

The Mining endpoints expose operational telemetry for every worker attached to a Binance Pool account. `GET /sapi/v1/mining/worker/list` returns the paginated roster of miners, allowing dashboards to review health, performance, and submission activity in near real-time. Because the call discloses account-level data, it resides under the **USER_DATA** security tier and requires a signed request.

---

## Endpoint Summary

- **HTTP Method:** `GET`
- **Path:** `/sapi/v1/mining/worker/list`
- **Weight (IP):** `5`
- **Security:** `USER_DATA` (HMAC SHA-256 signature generated with the mining account's API secret)
- **Response Content-Type:** `application/json`

Include the standard `timestamp` and (optionally) `recvWindow` parameters with every signed call. Signature generation follows the same process as other signed REST endpoints—concatenate the query string, apply HMAC SHA-256 with the API secret, and append the hexadecimal digest as the `signature` parameter.

---

## Request Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `algo` | STRING | ✅ | Hashing algorithm associated with the mining account (e.g., `sha256`). |
| `userName` | STRING | ✅ | Mining account name. This is the identifier returned by `GET /sapi/v1/mining/pub/publicKey`. |
| `pageIndex` | INTEGER |  | 1-based page index. Defaults to `1` when omitted. |
| `sort` | INTEGER |  | Sort direction. `0` = ascending (default), `1` = descending. |
| `sortColumn` | INTEGER |  | Column to sort. `1` = worker name, `2` = real-time hashrate, `3` = 24h average hashrate, `4` = real-time rejection rate, `5` = last share submission time. |
| `workerStatus` | INTEGER |  | Worker status filter. `0` = all (default), `1` = valid, `2` = invalid, `3` = failed. |
| `recvWindow` | LONG |  | Optional timing tolerance in milliseconds (≤ 60000). |
| `timestamp` | LONG | ✅ | Current client timestamp in milliseconds. |
| `signature` | STRING | ✅ | HMAC SHA-256 signature covering all query parameters. |

### Usage Notes

- Binance applies pagination automatically. Each response includes a `pageSize` field representing the number of workers per page. Iterate `pageIndex` to traverse the full roster.
- `sortColumn` and `sort` work together. For example, to display the most recently active miners first, set `sortColumn=5` and `sort=1`.
- `workerStatus=3` returns miners that are **no longer valid** (workers that have stopped submitting shares).

---

## Response Schema

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "workerDatas": [
      {
        "workerId": "1420554439452400131",
        "workerName": "2X73",
        "status": 3,
        "hashRate": 0,
        "dayHashRate": 0,
        "rejectRate": 0,
        "lastShareTime": 1587712919000
      }
    ],
    "totalNum": 0,
    "pageSize": 20
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | INTEGER | Request status code (`0` = success). |
| `msg` | STRING | Diagnostic message (typically empty on success). |
| `data` | OBJECT | Container for the paginated worker dataset. |
| `data.workerDatas` | ARRAY | List of worker records for the requested page. |
| `data.totalNum` | INTEGER | Total number of workers across the account that match the filter criteria. |
| `data.pageSize` | INTEGER | Maximum number of workers returned per page. |

### Worker Record (`workerDatas[]`)

| Field | Type | Description |
|-------|------|-------------|
| `workerId` | STRING | Unique identifier assigned to the miner. |
| `workerName` | STRING | Friendly miner label configured in the mining console. |
| `status` | INTEGER | Worker health status: `1` = valid, `2` = invalid, `3` = no longer valid. |
| `hashRate` | DECIMAL | Real-time hashrate for the most recent measurement window. Units depend on the mining algorithm (e.g., H/s for `sha256`). |
| `dayHashRate` | DECIMAL | Average hashrate over the trailing 24 hours. |
| `rejectRate` | DECIMAL | Real-time rejected share rate. Expressed as a ratio (0–1). |
| `lastShareTime` | LONG | Timestamp (milliseconds) of the most recent share submitted by the worker. |

---

## Example Request

```http
GET /sapi/v1/mining/worker/list?algo=sha256&userName=test&pageIndex=1&timestamp=1587969727000&signature=<signature>
Host: api.binance.com
X-MBX-APIKEY: <apiKey>
```

### Example Response

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "workerDatas": [
      {
        "workerId": "1420554439452400131",
        "workerName": "2X73",
        "status": 3,
        "hashRate": 0,
        "dayHashRate": 0,
        "rejectRate": 0,
        "lastShareTime": 1587712919000
      },
      {
        "workerId": "7893926126382807951",
        "workerName": "AZDC1.1A10101",
        "status": 2,
        "hashRate": 29711247541680,
        "dayHashRate": 12697781298013.66,
        "rejectRate": 0,
        "lastShareTime": 1587969727000
      }
    ],
    "totalNum": 18530,
    "pageSize": 20
  }
}
```

This payload mirrors Binance's live response structure and can be stored as a fixture for integration testing or UI prototyping.

---

## Troubleshooting Tips

- **Empty `workerDatas` array:** Confirm the `algo` and `userName` parameters correspond to an active mining account. Binance returns an empty array when no workers match the filters.
- **Signature errors (`-1022`):** Ensure the query string used for signing matches the transmitted parameters exactly, including the order and URL encoding. Also verify that the client timestamp is within the `recvWindow` tolerance.
- **Stale `lastShareTime`:** Workers with status `3` are considered offline. Investigate hardware or network issues if the timestamp lags behind the expected submission cadence.

