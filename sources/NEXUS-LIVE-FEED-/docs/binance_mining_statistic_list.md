# Binance Mining Statistic List (USER_DATA)

_Endpoint group: Mining_

The **Statistic List** endpoint returns current and historical performance metrics for a specific mining account. Values are
aggregated per algorithm and include short-term hashrate, 24-hour hashrate, share quality counts, and estimated profitability
for BTC, BSV, and BCH payouts.

- **HTTP method:** `GET`
- **Path:** `/sapi/v1/mining/statistics/user/status`
- **Request weight:** `5`
- **Security type:** `USER_DATA` (signed request)

## Request parameters

| Name        | Type   | Required | Description |
|-------------|--------|----------|-------------|
| `algo`      | String | Yes      | Mining algorithm identifier, such as `sha256`. |
| `userName`  | String | Yes      | Mining account name to query. |
| `recvWindow` | Long   | No       | Optional timestamp window (in milliseconds) to guard against clock drift. |
| `timestamp` | Long   | Yes      | Current timestamp in milliseconds. Used when signing the request. |

> The request must be signed with the API secret key. Include the API key in the `X-MBX-APIKEY` header.

## Response payload

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "fifteenMinHashRate": "457835490067496409.00000000",
    "dayHashRate": "214289268068874127.65000000",
    "validNum": 0,
    "invalidNum": 17562,
    "profitToday": {
      "BTC": "0.00314332",
      "BSV": "56.17055953",
      "BCH": "106.61586001"
    },
    "profitYesterday": {
      "BTC": "0.00314332",
      "BSV": "56.17055953",
      "BCH": "106.61586001"
    },
    "userName": "test",
    "unit": "h/s",
    "algo": "sha256"
  }
}
```

### Top-level fields

| Field | Description |
|-------|-------------|
| `code` | Error code. `0` indicates success. |
| `msg` | Error message string. Empty on success. |
| `data` | Object containing the mining statistics payload. |

### `data` object

| Field | Type | Description |
|-------|------|-------------|
| `fifteenMinHashRate` | String | Average hashrate over the trailing 15 minutes for the specified algorithm. |
| `dayHashRate` | String | Average hashrate over the previous 24 hours. |
| `validNum` | Integer | Count of valid shares submitted during the aggregation period. |
| `invalidNum` | Integer | Count of invalid shares submitted. |
| `profitToday` | Object | Estimated payouts for the current day. Keys map to payout asset symbols (`BTC`, `BSV`, `BCH`). |
| `profitYesterday` | Object | Realized payouts from the previous day. Keys mirror `profitToday`. |
| `userName` | String | Mining account that generated the statistics. |
| `unit` | String | Hashrate unit (e.g., `h/s`). |
| `algo` | String | Mining algorithm identifier provided in the request. |

Both `profitToday` and `profitYesterday` return string-encoded decimal values. Convert them to numeric types as needed when
performing calculations. Hashrate values are returned as strings to preserve precision.
