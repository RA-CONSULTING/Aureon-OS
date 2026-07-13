# Troubleshooting

## Brain not connected
- Ensure `python aureon_miner.py` is running before the ecosystem.
- Check file bridge/state is updating (e.g., `aureon_kraken_state.json`).

## "Global Harmonic Field not available"
- Verify imports and presence of `global_harmonic_field.py` if referenced.
- Ensure ecosystem is reading the correct state file.

## No trades executing
- Review `rejection_log.json` — fee gate, coherence thresholds, or Ω below required levels.
- Confirm env flags: `BINANCE_DRY_RUN`, `BINANCE_USE_TESTNET`.
- Check symbol precision/min-notional compatibility.

## API errors
- Verify `.env` API keys and regional availability (e.g., Binance UK constraints).
- Watch for rate limiting and apply backoff.

## Encoding or terminal issues
- Use UTF-8; prefer plain logging mode if fancy output fails.

## Win rate below targets
- Keep dry-run; review strategy filters and fee-aware exits.
- Validate that brain signals are reaching the ecosystem.

## Logs and Artifacts
- Ecosystem: `aureon_unified_ecosystem.log`
- Brain: `aureon_miner.log`
- Rejections: `rejection_log.json`
- State: `aureon_kraken_state.json` and any other shared JSON files
