# Market fingerprint — scanning a market-derived series through the engine

*Same song, different singer: the same phenolic engine — φ logic unchanged —
pointed at market dynamics, the repository's headline claim.*

## What it is

`aureon/bio/market_signal_adapter.py` scans a market-derived series through the
**identical** pre-registered engine every other adapter uses: Test A (coherence
clustering) + Test B (golden-interval / φ alignment) + the positive/negative
controls, scored via `score_signal` (controls → tests → separability at `ALPHA`).
Nothing about the engine is modified. The adapter only feeds it a market series and
reports what the test returns.

Inputs (`aureon/bio/market_signal_adapter.py`):
- **prices** — a price series (folded via standard log-returns),
- **returns** — a returns/change series already computed,
- **timeseries** — any scalar market series (e.g. momentum), used as-is.

The dominant cycles are extracted with the same FFT seam the UPE adapter uses
(`_dominant_timeseries_hz`) and octave-fold into the modulation band.

## The boundary (load-bearing)

This is the honest test of the HNC market thread. The scan looks for **statistical
structure in a derived series** and reports exactly what the engine returns. It is
**not a trading signal, a forecast, or financial advice, and it makes no profit or
efficacy claim** (`MARKET_BOUNDARY`). The engine's shared `SCIENTIFIC_BOUNDARY` rides
on every result; a blocked (unconsented) run can never publish a positive finding.

## Real local data (`aureon/bio/market_reference.py`)

- `data/probability_predictions.jsonl` — per-symbol `price_at_prediction` series
  (hundreds of points for the liquid symbols, e.g. APEUSDT ~823, BTCUSDT ~151).
- `data/queen_trades.jsonl` — a short dry-run `entry_price` log.

## Controls

Every governed scan runs the engine's control arms. Two market reference series
exercise them directly:
- `efficient_market_returns` — i.i.d. returns, the efficient-market null
  (**negative-control reference**: a memoryless walk must not over-fire).
- `structured_returns` — planted clustered + φ-spaced cycles (**positive-control
  demonstration**: real coherence is detected).

## Scan results (whatever the test returns)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Scan | tones | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| APEUSDT (823 real points) | 24 | 0.698 | 0.821 | False |
| BTCUSDT (151 real points) | 13 | 0.635 | 0.106 | False |

Controls: the efficient-market null stays quiet (A_p ≈ 0.22); the planted positive is
detected (A_p = B_p ≈ 0.003). The scan is deterministic.

## Run it

```bash
# control self-test (efficient-market null + planted structure)
python -m aureon.bio.market_signal_adapter --self-test

# list available symbols in the local prediction log
python -m aureon.bio.market_signal_adapter --list

# scan a real symbol's price series through the engine
python -m aureon.bio.market_signal_adapter --symbol APEUSDT
```

Benchmarked as Tier-A invariant **b13 "Market derived-signal"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 13/13). The benchmark reads the
committed local logs offline, so CI never depends on the network.
