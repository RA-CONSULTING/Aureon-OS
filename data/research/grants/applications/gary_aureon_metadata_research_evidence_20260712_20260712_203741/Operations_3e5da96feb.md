# Operations Runbook

## Environments
- Python 3.10+ recommended.
- Create a virtual environment and install from `requirements.txt`.
- Copy `.env.example` to `.env` and fill in values.

## Dry-Run Workflow
1. Start Brain: `python aureon_miner.py`
2. Start Ecosystem: `python aureon_unified_ecosystem.py`
3. Monitor logs: `aureon_miner.log`, `aureon_unified_ecosystem.log`
4. Validate behavior: check risk caps, symbol filters, and rejection reasons in `rejection_log.json`.

## Live Workflow (After Verification)
1. Confirm fee/precision/min-notional handling for target symbols.
2. Set small caps in `.env` (e.g., `BINANCE_RISK_MAX_ORDER_USDT=10`).
3. Enable live gate: `LIVE=1 python aureon_unified_ecosystem.py`.
4. Supervise fills, rejects, and retries; be prepared to stop.

## Monitoring
- Ecosystem state: periodic logs and any dashboard integration.
- Exchanges: API health, rate limits, and balance changes.
- Persistence: JSON state files; consider adding DB storage for critical histories.

## Rollback / Stop
- Use Ctrl+C in terminals to stop processes.
- Revert env changes and return to dry-run.
- Inspect logs to identify the cause of anomalies before resuming.

## Housekeeping
- Rotate logs periodically.
- Backup `.env` securely (never commit real keys).
- Keep dependencies updated and pin critical versions.
