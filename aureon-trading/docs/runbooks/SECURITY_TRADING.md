# Binance Trading Integration Security & Usage

## Key Principles

- NEVER commit real API keys. `.env` is gitignored; use `.env.example` as template.
- Rotate keys immediately if exposed anywhere (chat, issue, log).
- Start on testnet (`BINANCE_USE_TESTNET=true`) and `BINANCE_DRY_RUN=true` until strategy validated.
- Restrict key permissions: SPOT trading only, no withdrawals. Add IP whitelist when stable.
- Log every order attempt with notional, side, timestamp.

## Environment Variables

| Variable | Purpose | Recommended Initial Value |
|----------|---------|---------------------------|
| `BINANCE_API_KEY` | API key | (set after generation) |
| `BINANCE_API_SECRET` | API secret | (set after generation) |
| `BINANCE_USE_TESTNET` | Switch endpoints | `true` |
| `BINANCE_DRY_RUN` | Skip real order placement | `true` |
| `BINANCE_RISK_MAX_ORDER_USDT` | Cap notional per order | `25` |
| `BINANCE_RISK_FRACTION` | Percent of free quote balance to risk | `0.02` |
| `BINANCE_SYMBOL` | Default trading symbol | `BTCUSDT` |

## Workflow

1. Copy `.env.example` -> `.env` and fill keys (keep testnet true).
2. Run `python binance_trade_sample.py` to verify connectivity & sizing.
3. Adjust risk controls until position sizing matches desired exposure.
4. Set `BINANCE_DRY_RUN=false` while still on testnet for end-to-end order path.
5. Flip `BINANCE_USE_TESTNET=false` ONLY after:
   - Strategy logic validated
   - Risk sizing audited
   - Keys restricted & IP whitelisted
6. Monitor `trade_audit.log` (implement extended logging if needed) for anomalies.

## Extending

- Add strategy module placing orders via `BinanceClient.place_market_order` after pre-trade checks.
- Implement cooldown windows & max daily loss limits (e.g., track cumulative PnL and disable after threshold).
- Add signature replay protection by verifying server time drift before placing orders.

## Deposit Addresses

- Retrieval implemented via `BinanceClient.get_deposit_address(coin, network=None)`.
- Not available on testnet; do not disable testnet until trading logic is validated.
- Always verify the returned `address` and `tag/memo` (if present) before transferring funds.
- Script: `python binance_get_address.py BTC` (requires `BINANCE_USE_TESTNET=false`).
- Never paste deposit addresses or keys into public channels; treat them as sensitive.

## Incident Response

- If suspicious activity detected: disable API key, export trade history, rotate secrets, review logs.
- Maintain off-exchange record of executed trades for reconciliation.

## Disclaimer

This code is for educational integration. No guarantee of profit; you accept full responsibility for live trading risk.
