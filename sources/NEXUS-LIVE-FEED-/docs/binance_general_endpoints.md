# Binance REST API General Endpoints

The Binance REST API exposes a handful of ultra-lightweight endpoints that are perfect for quick connectivity or liveness checks.  The table below consolidates the endpoints most commonly used by the Nexus Live Feed ingestion services when verifying network connectivity before any trading logic is triggered.

| HTTP Method | Endpoint | Weight | Description | Notes |
|-------------|----------|--------|-------------|-------|
| `GET` | `/api/v3/ping` | 1 | Confirms that the REST gateway is reachable. | Returns an empty JSON object (`{}`) on success. Useful for health checks and CI smoke tests. |
| `GET` | `/api/v3/time` | 1 | Retrieves the current Binance server time. | Response contains a `serverTime` field with the server's Unix timestamp in milliseconds. Align local timestamps with this value to prevent signature skew. |
| `GET` | `/api/v3/exchangeInfo` | 20 | Provides symbol metadata, trading rules, rate limits, and permission sets. | Accepts optional query parameters: `symbol`, `symbols`, `permissions`, `showPermissionSets`, and `symbolStatus`. Use `permissions` to explicitly request symbols with non-spot capabilities (e.g., `"MARGIN"`, `"LEVERAGED"`). |

## Request Parameter Details

### `/api/v3/exchangeInfo`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | STRING | No | Single symbol identifier (e.g., `BNBBTC`). Cannot be used with `symbols` or `permissions`. |
| `symbols` | ARRAY of STRING | No | URL-encoded array of symbols (e.g., `%5B"BNBBTC","BTCUSDT"%5D`). Cannot be used with `symbol` or `permissions`. |
| `permissions` | ENUM or ARRAY of ENUM | No | One or more permission scopes (e.g., `SPOT`, `["MARGIN","LEVERAGED"]`). Cannot be combined with `symbol` or `symbols`. |
| `showPermissionSets` | BOOLEAN | No | Toggles population of the `permissionSets` field. Defaults to `true`. |
| `symbolStatus` | ENUM | No | Filters symbols by trading status. Valid values: `TRADING`, `HALT`, `BREAK`. Mutually exclusive with `symbol` and `symbols`. |

### Interpretation Tips

* Binance may expose multiple permission sets for a symbol. Each inner array represents an "AND" clause, while the outer array acts as an "OR" clause. For example:
  * `[["SPOT","MARGIN"]]` means the symbol is accessible if the account has either `SPOT` **or** `MARGIN` permission.
  * `[["A"],["B","C"]]` means the account must have `A` **and** (`B` **or** `C`).
* The `quotePrecision` field is slated for removal in future API versions (v4+); rely on `quoteAssetPrecision` instead.
* When Smart Order Routing (SOR) is enabled, the payload may include a `sors` array listing alternate symbols for a given base asset.

## Example Responses

<details>
<summary><code>GET /api/v3/ping</code></summary>

```json
{}
```

</details>

<details>
<summary><code>GET /api/v3/time</code></summary>

```json
{
  "serverTime": 1499827319559
}
```

</details>

<details>
<summary><code>GET /api/v3/exchangeInfo</code> (excerpt)</summary>

```json
{
  "timezone": "UTC",
  "serverTime": 1565246363776,
  "rateLimits": [
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalNum": 1,
      "limit": 1200
    }
  ],
  "symbols": [
    {
      "symbol": "ETHBTC",
      "status": "TRADING",
      "baseAsset": "ETH",
      "baseAssetPrecision": 8,
      "quoteAsset": "BTC",
      "quotePrecision": 8,
      "quoteAssetPrecision": 8,
      "baseCommissionPrecision": 8,
      "quoteCommissionPrecision": 8,
      "orderTypes": [
        "LIMIT",
        "LIMIT_MAKER",
        "MARKET",
        "STOP_LOSS",
        "STOP_LOSS_LIMIT",
        "TAKE_PROFIT",
        "TAKE_PROFIT_LIMIT"
      ],
      "icebergAllowed": true,
      "ocoAllowed": true,
      "otoAllowed": true,
      "quoteOrderQtyMarketAllowed": true,
      "allowTrailingStop": false,
      "cancelReplaceAllowed": false,
      "amendAllowed": false,
      "pegInstructionsAllowed": true,
      "isSpotTradingAllowed": true,
      "isMarginTradingAllowed": true,
      "filters": [],
      "permissions": [],
      "permissionSets": [
        [
          "SPOT",
          "MARGIN"
        ]
      ],
      "defaultSelfTradePreventionMode": "NONE",
      "allowedSelfTradePreventionModes": [
        "NONE"
      ]
    }
  ]
}
```

</details>

These examples mirror the responses returned by the live Binance REST API and can be used for unit test fixtures or quick manual verification.
