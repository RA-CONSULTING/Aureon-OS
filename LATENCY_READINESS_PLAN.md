# Aureon Latency Readiness Plan (Intelligence → Decision → Live Order)

## Objective
Quantify end-to-end latency from market intelligence gathering to exchange order submission/acknowledgement, then set a realistic ETA for production-grade execution hardening.

## Current System Context (from recent commits + README)
- Runtime is a unified production supervisor with live/dry-run gating and exchange-aware rate-limit budgeting.
- Live order mutation is intentionally blocked by safety gates when stale data, open-position constraints, or risk blockers are present.
- Exchange call planning already includes official per-venue limits and cash-aware prioritisation, which is the right control plane for adding precise latency SLOs.

## Latency Surfaces to Measure
1. **Intelligence ingest latency**
   - Tick/quote arrival to availability in runtime state.
2. **Decision latency**
   - Signal availability to order-intent creation/publication.
3. **Execution path latency**
   - Intent publication to exchange API request dispatch.
4. **Exchange round-trip latency**
   - Request dispatch to exchange acknowledgement (accept/reject/fill update).
5. **Portfolio state convergence latency**
   - Exchange acknowledgement to reflected position/order state in `/api/terminal-state`.

## Required Instrumentation
Add monotonic timestamps for each stage with a shared trace id (`decision_trace_id`):
- `t_intel_seen`
- `t_signal_scored`
- `t_intent_published`
- `t_exec_dispatched`
- `t_exchange_ack`
- `t_state_converged`

Write per-trace records to a rolling JSONL audit artifact and expose percentile summaries in the terminal-state payload.

## SLO Targets (Initial)
- p50 intelligence→intent: <= 150 ms
- p95 intelligence→intent: <= 450 ms
- p50 intent→exchange_ack: <= 250 ms
- p95 intent→exchange_ack: <= 900 ms
- p99 end-to-end intelligence→state_converged: <= 2.5 s

Targets should be split per venue (Binance, Kraken, Alpaca, Capital) due to different external API characteristics.

## Rate-Limit Feasibility Checks
Use the existing exchange rate-limit registry to validate:
- sustained calls/sec under normal operation,
- burst behaviour during volatility,
- headroom reserved for risk/position/account sync,
- worst-case backoff/retry impact on p95/p99.

## Test Matrix
1. **Dry-run replay**
   - Historical high-volatility windows with synthetic intent generation.
2. **Paper/live-sandbox where available**
   - Validate external round-trip latency characteristics.
3. **Constrained rate scenario**
   - Force near-limit budgets to verify graceful degradation and prioritisation.
4. **Failure injection**
   - API timeout, partial outage, delayed websocket updates, clock skew.

## ETA to Production-Latency Readiness
Assuming no major architecture rewrite:
- **Phase 1 (2-3 days):** instrumentation + trace artifacts.
- **Phase 2 (2-4 days):** dashboards, percentile reporting, baseline runs.
- **Phase 3 (3-5 days):** optimisation + rate-limit tuning + queue prioritisation.
- **Phase 4 (2-3 days):** soak tests and go/no-go criteria.

**Estimated total:** 9-15 working days.

## Go/No-Go Exit Criteria
- 7 consecutive days with no safety-gate regressions from added instrumentation.
- Venue-specific p95 SLOs met for at least 95% of sampled sessions.
- No increase in rejected orders attributable to pacing/retry logic.
- Clear operator dashboard view of latency percentiles and current blockers.
