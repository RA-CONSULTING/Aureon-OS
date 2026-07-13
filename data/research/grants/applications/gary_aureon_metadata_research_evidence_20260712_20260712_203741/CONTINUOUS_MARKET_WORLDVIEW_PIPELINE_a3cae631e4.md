# Continuous Market Worldview Pipeline

This blueprint turns the requested "always-on, multi-feed, coherence + geopolitics" vision into a buildable system using the repo's current architecture.

## 1) Reality Constraints (Design Guardrails)

- **Zero latency is not physically possible** across internet venues; target low, measured latency with deterministic failover.
- **No key leakage**: all API keys stay in env/config vaults and never pass through logs, telemetry payloads, or front-end JSON.
- **One canonical event clock**: all events are normalized to UTC with source timestamp + ingest timestamp.
- **Execution separation**: prediction/monitoring streams are isolated from order-routing channels.

## 2) Unified Streaming Topology

```text
Kraken WS/REST   Alpaca WS/REST   Binance WS   Macro/News/Geo Feeds
      \             |              /             /
       \            |             /             /
        -> Ingest adapters -> Normalizer -> Event Bus -> Feature Graph
                                                |             |
                                                |             -> Forecast + anomaly engines
                                                v
                                       Policy/Risk Gate
                                                |
                                                v
                                         Execution adapters
```

### Core stages

1. **Ingest adapters**
   - Per source connector with independent retry logic and heartbeat checks.
2. **Normalizer**
   - Canonical schema for ticks, order book deltas, trades, macro events, and geopolitical events.
3. **Event bus**
   - Single publish/subscribe backbone for all real-time consumers.
4. **Feature graph**
   - Time-zone aware, market-session aware feature windows for micro and macro coherence.
5. **Forecast + anomaly engines**
   - Detect order-book stress, cross-venue dislocations, and event coherence shifts.
6. **Policy/risk gate**
   - Hard limits, kill switches, spread sanity checks, and stale-data checks.

## 3) Canonical Event Schema (Minimum)

Every message should carry:

- `event_id`
- `source` (kraken/alpaca/binance/macro/news)
- `asset_class` (crypto/equity/fx/commodity/index)
- `symbol`
- `event_type` (trade/book_delta/book_snapshot/macro/geopolitical)
- `event_ts_source_utc`
- `event_ts_ingest_utc`
- `latency_ms_source_to_ingest`
- `payload` (source-specific body)
- `confidence`
- `quality_flags` (stale, partial_book, missing_seq, etc.)

## 4) Latency & Integrity Controls

- **Per-source latency SLOs** (p50/p95/p99).
- **Sequence validation** for order books (gap detection + snapshot resync).
- **Clock drift monitor** between host and exchange timestamps.
- **Stale-data quarantine** when heartbeat misses exceed threshold.
- **Deterministic backpressure**: drop low-priority analytics first, never risk gates.

## 5) Coherence Engine (Requested "flavor of coherence")

Compute coherence as a multi-axis score:

- Cross-venue price alignment (Kraken vs Binance vs Alpaca-proxy instruments)
- Volume regime shifts by session/time zone
- Order-book imbalance persistence
- Spread/impact stress
- Macro + geopolitical event proximity (before/after windows)

Output:

- `coherence_score` (0-100)
- `regime` (calm / transitional / stress / dislocation)
- `explanations` (top factors)

## 6) Geopolitical + Macro Trigger Layer

Add a dedicated event channel for:

- Scheduled macro releases (rates, CPI, payrolls)
- Headline/event stream classification
- Currency/commodity sensitivity mapping

Behavior:

- Correlate event onset to volatility bursts and order-book deformation.
- Mark uncertain triggers explicitly (`unknown_trigger=true`) while still capturing market response signatures.
- Keep causality as probabilistic, not absolute.

## 7) "Doctor / Queen / Seer" Mapping Into Concrete Modules

Interpretation for implementation:

- **Doctor** => health/validation subsystem
  - feed health checks, schema validation, model drift checks
- **Queen system** => orchestration and policy layer
  - strategy routing, risk gating, session governance
- **Seer system** => predictive modeling layer
  - short-horizon directional + volatility inference

Each module should publish health + confidence to the same event bus.

## 8) Validation Matrix (Logic Test Plan)

Run automated tests in three blocks:

1. **Feed correctness**
   - sequence continuity, reconnect recovery, timestamp sanity
2. **Model correctness**
   - no-leak backtests, walk-forward validation, calibration error
3. **Execution safety**
   - latency spike simulation, spread blowout simulation, stale-data simulation

Required outputs:

- pass/fail by scenario
- max drawdown under stress simulation
- false-positive/false-negative event trigger rates

## 9) Initial Build Order (Practical)

1. Build canonical schema + normalizer.
2. Wire Kraken + Alpaca + Binance connectors with heartbeats.
3. Add latency dashboard and stale-data gate.
4. Add order-book + volume coherence features.
5. Add macro/geopolitical event channel and correlation tagging.
6. Add regime classifier and risk policy binding.
7. Roll out paper-trade first, then phased live rollout.

## 10) What Success Looks Like

- Continuous stream uptime > 99% over 7 days.
- Measured, bounded ingest latency with automatic degradation behavior.
- Regime/coherence states visible in dashboard and logs.
- Predictive module improves decision quality without violating risk constraints.
- All high-impact actions traceable to event + feature + policy evidence.
