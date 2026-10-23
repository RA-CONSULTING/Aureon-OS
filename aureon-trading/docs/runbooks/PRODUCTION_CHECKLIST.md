# Production Safety Checklist (Live Trading)

Use this checklist before enabling live orders. It is not exhaustive; adapt to your environment and regulatory obligations.

## Pre-Run
- Environment
  - `.env` present with correct keys and `BINANCE_USE_TESTNET`/`BINANCE_DRY_RUN` explicitly set.
  - `BINANCE_RISK_MAX_ORDER_USDT` (or equivalent) set to a small value for initial runs.
  - Logs directory writable and monitored.
- Symbols
  - Limit to a small, liquid symbol set (e.g., `BTCUSDT`, `ETHUSDT`).
  - Verify exchange filters: min notional, tick size, step size.
- Funds
  - Confirm balances and quote asset availability via the client or exchange UI.

## Dry-Run / Testnet Validation
- Run `python check_live_environment.py` and resolve warnings.
- Start the runner in dry-run/testnet; verify order intents, sizes, and error handling.
- Confirm position/account state snapshots update as expected.

## Enable Live (Gradually)
- Set `BINANCE_DRY_RUN=false` and (where applicable) `LIVE=1` only after full review.
- Keep `BINANCE_RISK_MAX_ORDER_USDT` small for the first sessions.
- Monitor logs for rejects, precision errors, and partial fills.

## Monitoring & Recovery
- Ensure you can terminate the process cleanly and reconcile open positions.
- Periodically refresh balances and positions from the exchange to prevent state drift.
- Keep a log of orders and fills from the exchange UI for cross-checking.

## Post-Run
- Reconcile realized P&L against exchange reports.
- Review error rates and implement backoff/retry improvements where needed.
- Adjust risk caps conservatively; do not scale sizing until stability is proven.

## Disclaimer
This checklist does not eliminate risk. Markets are volatile, APIs fail, and losses can occur. Use at your own risk and follow all applicable laws and exchange Terms of Service.
