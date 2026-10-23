# Binance Autonomous Trading Setup

This guide explains how to prepare Binance credentials, verify connectivity,
and run the QGITA autonomous trading bot that ships with this repository.



## 1. Create a Restricted API Key

Create an API key inside your Binance account and apply the following
permissions:

| Permission                        | Status | Notes |
|----------------------------------|:------:|-------|
| Enable Reading                   | ✅     | Required for balances and ticker data. |
| Enable Spot & Margin Trading     | ✅     | Required for order placement. |
| Enable Withdrawals               | ❌     | Leave disabled for security. |
| Enable IP Access Restrictions    | ✅     | Add the public IP address of the host that will run the bot. |
| Enable Universal Transfer        | Optional | Only needed if you plan to move funds between accounts programmatically. |

> **Security tip:** Rotate the key regularly and store the secret securely.

## 2. Verify the Key Permissions

Use the helper snippet below to confirm that the key can access the signed
account endpoint. Replace the placeholders with your credentials:

```python
import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

API_KEY = "your_api_key"
API_SECRET = "your_secret"
BASE_URL = "https://api.binance.com"


def _sign(params: dict) -> str:
    query = urlencode(params)
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()


def get_account_info() -> dict:
    params = {"timestamp": int(time.time() * 1000)}
    params["signature"] = _sign(params)
    headers = {"X-MBX-APIKEY": API_KEY}
    response = requests.get(f"{BASE_URL}/api/v3/account", params=params, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    account = get_account_info()
    print("Account Type:", account.get("accountType"))
    print("Can Trade:", account.get("canTrade"))
    balances = [
        (balance["asset"], balance["free"])
        for balance in account.get("balances", [])
        if float(balance.get("free", 0)) > 0
    ]
    print("Balances:", balances)
```

If the call succeeds, the credentials are ready for live trading. Any HTTP
error indicates that the key lacks permission or the IP restrictions do not
match.

### Quick Connectivity Checks

Before signing requests, it is helpful to verify that the Binance REST gateway
is reachable and to inspect the server time. The endpoints below do not require
authentication and are weighted lightly, so they are safe to call whenever you
need to confirm connectivity.

| Method | Endpoint | Weight | Purpose |
|--------|----------|--------|---------|
| `GET` | `/api/v3/ping` | 1 | Confirms that the REST API is reachable. Returns an empty JSON object `{}`. |
| `GET` | `/api/v3/time` | 1 | Returns the current `serverTime` in milliseconds. Useful when synchronizing timestamps for signed requests. |
| `GET` | `/api/v3/exchangeInfo` | 20 | Provides symbol metadata, trading rules, rate limits, and permission sets. Accepts optional query parameters such as `symbol`, `symbols`, `permissions`, `showPermissionSets`, and `symbolStatus`. |

Example responses:

```jsonc
{}
```

```jsonc
{
  "serverTime": 1499827319559
}
```

```jsonc
{
  "timezone": "UTC",
  "serverTime": 1565246363776,
  "symbols": [
    {
      "symbol": "ETHBTC",
      "status": "TRADING",
      "baseAsset": "ETH",
      "quoteAsset": "BTC",
      "orderTypes": ["LIMIT", "MARKET", "STOP_LOSS", "TAKE_PROFIT"],
      "permissions": [],
      "permissionSets": [["SPOT", "MARGIN"]]
    }
  ]
}
```

## 3. Configure Environment Variables

The trading bot reads its configuration from environment variables, which makes
it easy to keep secrets out of source control. The most important variables are
listed below:

| Variable | Description | Default |
|----------|-------------|---------|
| `BINANCE_API_KEY` | Public API key. | Empty (required for live trading). |
| `BINANCE_API_SECRET` | API secret used for signatures. | Empty (required for live trading). |
| `QGITA_SYMBOL` | Trading pair. | `BTCUSDT` |
| `QGITA_POSITION_SIZE` | Notional position size in USDT. | `100` |
| `QGITA_MAX_POSITION_SIZE` | Maximum total exposure in USDT. | `500` |
| `QGITA_STOP_LOSS` | Stop loss percentage. | `2` |
| `QGITA_TAKE_PROFIT` | Take profit percentage. | `4` |
| `QGITA_PAPER_TRADING` | Enable paper trading (`true`/`false`). | `true` |
| `QGITA_SYMBOL_STATUS` | Optional trading phase guard that maps to Binance's new `symbolStatus` parameter (e.g. `TRADING`). | `TRADING` |

Additional variables exist for tuning the QGITA detector (window size,
curvature threshold, lighthouse consensus threshold, etc.). See the module
docstring in `scripts/binance_trading_bot.py` for the full list.

## 4. Run the Bot

Install the runtime dependencies:

```bash
pip install numpy requests websocket-client
```

Then launch the bot. It defaults to paper trading, so it can be run safely
without real funds:

```bash
python scripts/binance_trading_bot.py --symbol BTCUSDT
```

To fetch a single price update (without opening a WebSocket connection) use:

```bash
python scripts/binance_trading_bot.py --once
```

After verifying the behaviour, enable live trading explicitly. **This will
place real orders.**

```bash
python scripts/binance_trading_bot.py --live --symbol BTCUSDT
```

Use `--account-info` to print the account balances and confirm trading access:

```bash
python scripts/binance_trading_bot.py --live --account-info
```

## 5. Understand Exchange Filters

Binance enforces price, quantity, notional, and order-count filters across
symbols, the entire exchange, and specific assets. Consult the
[Binance Exchange Filters Reference](./binance_exchange_filters.md) for a
complete breakdown before promoting QGITA to production so every submission
conforms to those limits on the first attempt.

## 6. Risk Controls

The implementation enforces several safeguards:

- Daily loss cap (`QGITA_MAX_DAILY_LOSS`) stops trading after sustained losses.
- Daily trade limit (`QGITA_MAX_TRADES`) prevents runaway loops.
- Maximum exposure (`QGITA_MAX_POSITION_SIZE`) ensures each position stays
  within a predefined USDT budget.
- Stop-loss and take-profit levels are calculated immediately when a position
  opens and are monitored on every price update.

These values should be tuned for your account size and risk tolerance before
live deployment.

