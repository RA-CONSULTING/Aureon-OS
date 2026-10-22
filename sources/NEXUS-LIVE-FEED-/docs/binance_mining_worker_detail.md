# Binance Mining Worker Detail Endpoint

The mining worker detail endpoint exposes hourly and daily hashrate statistics for an individual mining worker that belongs to a mining account. Requests must be signed with an HMAC SHA-256 signature generated from the query string using the mining API secret. The `timestamp` value must be the current UNIX time in milliseconds. Optionally, a `recvWindow` (maximum `60000`) may be provided to widen the allowable timestamp drift.

- **HTTP Method:** `GET`
- **Path:** `/sapi/v1/mining/worker/detail`
- **Request Weight:** 5
- **Response Content-Type:** `application/json`

---

## Request Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `algo` | STRING | ✅ | Mining algorithm identifier (for example `sha256`). |
| `userName` | STRING | ✅ | Mining account name that owns the worker. |
| `workerName` | STRING | ✅ | Fully-qualified worker identifier to query. |
| `recvWindow` | LONG |  | Optional timestamp tolerance in milliseconds (≤ 60000). |
| `timestamp` | LONG | ✅ | Millisecond UNIX timestamp when the request is signed. |
| `signature` | STRING | ✅ | HMAC SHA-256 signature of the query string using the mining API secret. |

**Example**

```http
GET /sapi/v1/mining/worker/detail?algo=sha256&userName=test&workerName=bhdc1.16A10404B&timestamp=1587906000000&signature=2f91270cc9b0...
```

---

## Response Schema

```json
{
  "code": 0,
  "msg": "",
  "data": [
    {
      "workerName": "bhdc1.16A10404B",
      "type": "H_hashrate",
      "hashrateDatas": [
        {
          "time": 1587902400000,
          "hashrate": "0",
          "reject": 0
        },
        {
          "time": 1587906000000,
          "hashrate": "0",
          "reject": 0
        }
      ]
    },
    {
      "workerName": "bhdc1.16A10404B",
      "type": "D_hashrate",
      "hashrateDatas": [
        {
          "time": 1587902400000,
          "hashrate": "0",
          "reject": 0
        },
        {
          "time": 1587906000000,
          "hashrate": "0",
          "reject": 0
        }
      ]
    }
  ]
}
```

### Field Notes

- `code`: `0` indicates a successful response. Non-zero values correspond to error conditions described in the Binance mining error catalog.
- `msg`: Optional message accompanying the status code. Empty when the request succeeds.
- `data`: Array containing separate series for hourly (`H_hashrate`) and daily (`D_hashrate`) worker statistics.
  - `workerName`: Repeats the worker identifier echoed from the request.
  - `type`: Indicates the granularity of the hashrate data. Currently observed values are `H_hashrate` (hourly) and `D_hashrate` (daily).
  - `hashrateDatas`: Ordered list of measurements for the specified period.
    - `time`: Millisecond UNIX timestamp identifying the measurement window.
    - `hashrate`: String representation of the computed hashrate. Convert to a numeric type as needed for downstream processing.
    - `reject`: Rejection rate reported for the window. Expressed as a numeric ratio.

---

## Usage Notes

- Only mining accounts that have enabled API access can call this endpoint.
- When polling for near-real-time visibility, respect the weight limit by spacing calls appropriately; the mining API enforces a 5 weight per request.
- Combine the hourly and daily series to monitor short-term fluctuations and longer-term trends in worker performance.
