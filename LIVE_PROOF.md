# Aureon Trading System — designed path (go-live HOLD; no verified live track record)

> **What the trading path is designed to do. There is no verified live track record. Go-live is terminal HOLD. Exchange keys in `.env` do not boot a supported live session. The orange release-boundary badge stays HOLD.**

> **The run boundary is [`RUNNING.md`](RUNNING.md). There is no approved production start.**
>
> ℹ️ Some `4_output/...json` paths below refer to runtime-generated state files. These are produced when the system runs — you won't find them at those paths until you've executed the relevant module. The JSON paths in this doc reflect logical organization, not necessarily on-disk location of pre-existing files. To find runtime artifacts on your install, search by filename:
> ```bash
> find . -name "<filename>.json" -not -path "./.venv/*" -not -path "./node_modules/*"
> ```

---

## Status

Earlier drafts of this note quoted backtest and paper-trading totals as if they were a verified record. They were not. Those P&L amounts, win rates, and trade counts are not repeated here. Live performance is not yet measured. There is no verified live track record. Go-live stays HOLD. Exchange keys in `.env` are not a start.

---

## What the four stages are designed to do

| Stage | What the code is designed to do | Measured result |
|-------|----------------------------------|-----------------|
| **Stage 1: Backtesting** | Replay historical candles through HNC signals and write a results file | none yet |
| **Stage 2: Paper trading** | Simulate fills against market data and store a trade record with HNC fields | none yet |
| **Stage 3: Live trading** | Designed to place orders on a connected exchange. This checkout does not clear that. Go-live stays HOLD. | none yet |
| **Stage 4: Verification** | Compare a predicted time-to-target with the fill that actually happened | none yet |

---

## Stage 1: Backtesting — historical replay

The spot replay is `aureon/analytics/aureon_historical_backtest.py`. The margin replay is `aureon/analytics/super_intelligence_backtest.py`.

They are designed to write:

- `4_output/performance_metrics/backtest_spot_results.json`
- `4_output/performance_metrics/backtest_margin_results.json`

The spot path is designed for long-only pairs. The margin path is designed to record long margin, short sales, leverage, and rollover fees. A results file from either path is not treated here as a verified performance record.

What this stage is designed to record:

- whether a coherence threshold produced an entry
- whether a harmonic-frequency reading lined up with the bar
- drawdown, fees, and direction, as fields on the replay

Running the replay does not, by itself, establish that the strategy made money.

---

## Stage 2: Paper trading — real-time simulation

Designed output: `4_output/trade_outputs/paper_trade_history.json`

A paper record is designed to hold:

- symbol, entry price, exit price, pnl, and pnl percent
- `hnc_analysis`: frequency, coherence, score, action, probability
- `execution`: exchange, entry time, exit time, hold time, reason

Coherence is scored on a 0–1 scale. The productive band named on this path is 0.35–0.945. That is a design bound on the signal, not a measured win rate.

What this stage is designed to do:

- run against market data without sending an order
- attach an HNC reading to each simulated fill
- keep a losing fill inside the risk limits the run was given

Measured session P&L and win rate are not yet measured. There is no verified live track record.

---

## Stage 3: Live trading — exchange book

Designed state file: `4_output/portfolio_management/portfolio_truth.json`

The live book is designed to list positions per exchange. Kraken and Binance are the adapters this path names. Each position is designed to carry units, cost, value, and a P&L field. No account snapshot is quoted here.

What the book design names. None of this is a cleared production path:

1. **Multi-exchange coordination**
   - Position tracking across Kraken and Binance at the same time
   - A place to record a hedge across venues
   - A place to record an arbitrage candidate

2. **Real-time updates**
   - Balance monitoring, as a designed field
   - Position P&L tracking
   - Entry price versus current price

3. **Risk management**
   - Stop-loss exit
   - Position size from account equity
   - Cross-exchange margin tracking

There is no verified live track record. Go-live stays HOLD. Exchange keys in `.env` do not boot a supported live session. This note does not arm one.

---

## Stage 4: Verification — timing against the fill

Designed history: `4_output/trade_outputs/eta_verification_history.json`

ETA prediction is the attempt to name, in seconds, when a trade will reach its target. A verification record is designed to hold:

- signal metrics: confidence, momentum score, cascade level, coherence zone
- the predicted ETA and the target
- the actual ETA, the actual fill time, and the final pnl
- a time error and a verdict

The verifier is also designed to store a velocity correction and an ETA bias so a later run can adjust. Measured hit rate and timing error are not yet measured. A record of this shape is not a verified track record.

---

## Trade validation

Module: `aureon/portfolio/trade_profit_validator.py`

The validator is designed to check three stretches of a fill.

Entry:

- price recorded
- timestamp lined up with the exchange
- signal strength present
- frequency reading present

Hold:

- position tracked while it is open
- risk limits enforced
- volatility noted
- slippage looked at

Exit:

- exit price against the prediction
- time to target
- P&L reconciliation
- commission and fees deducted

Passing those checks is a property of one recorded fill. It is not a win rate.

---

## Risk controls the code is designed to apply

Spot and margin replays are designed to record max drawdown.

- Spot: a stop when the coherence threshold breaks
- Margin: position size from coherence, plus a hedge on leveraged pairs

Paper mode is designed to record win size, loss size, a profit factor, losing streaks, and recovery time. Those are field names. No measured risk statistic is quoted here. That measurement is not yet measured.

---

## Pipeline from signal to execution

```
1. HARMONIC ANALYSIS
   ├─ Market frequency scanning (1_substrate/frequencies/)
   ├─ φ² Coherence Bridge detection
   ├─ Sacred frequency alignment (528 Hz, 432 Hz, etc.)
   └─ Output: Entry signal strength

2. HNC EVALUATION
   ├─ Apply LTDE equation: Ψ(t) = Σₖ aₖ·Λₖ(t-τₖ)·e^(iθₖ)
   ├─ Calculate Γ coherence (0-1 scale)
   ├─ Measure probability confidence
   └─ Output: BUY/SELL action

3. RISK ASSESSMENT
   ├─ Portfolio coherence check
   ├─ Leverage limits verification
   ├─ Volatility adjustment
   └─ Output: Position size calculation

4. EXECUTION
   ├─ Place limit order at harmonic price
   ├─ Monitor coherence during hold
   ├─ Auto-exit on coherence break or time limit
   └─ Output: Trade record with HNC metrics

5. VALIDATION
   ├─ PnL reconciliation
   ├─ Timing accuracy audit
   ├─ Signal quality verification
   └─ Output: Trade audit record
```

The backtest is designed so a later measured run can be split by regime (trend, range, reversal, high volatility) and by direction (long or short). No regime table is quoted. That split is not yet measured.

No win rate, drawdown, or P&L comparison with any other framework is claimed. A comparison waits on a measured, reproducible Aureon run.

---

## Module paths (not an approved start)

These are the module paths the stages name. They are not an approved run, they do not clear HOLD, and they do not turn an old note into a verified record. Treat any JSON a later run might write as unmeasured until that run is reproduced and the raw output is kept.

### Backtesting

```bash
# Spot trading backtest
python3 aureon/analytics/aureon_historical_backtest.py

# Margin trading backtest
python3 aureon/analytics/super_intelligence_backtest.py

# View results
cat 4_output/performance_metrics/backtest_spot_results.json
cat 4_output/performance_metrics/backtest_margin_results.json
```

### Paper trading

```bash
# Historical ignition path. Not an approved start.
python scripts/aureon_ignition.py

# Portfolio tracker module. Not a live session.
python3 aureon/portfolio/live_portfolio_growth_tracker.py

# View trade history
cat 4_output/trade_outputs/paper_trade_history.json
```

### Book paths (not a start)

```bash
# Portfolio-state module. Not a start, and not a live book.
python3 scripts/diagnostics/check_portfolio.py

# View recent trades
python3 scripts/diagnostics/check_recent_trades.py

# View detailed accounting
python3 aureon/bots/king_accounting.py
```

### Trade checks

```bash
# Trade-check module. Not a validation of the release.
python3 aureon/portfolio/trade_profit_validator.py

# View audit trail
cat 4_output/performance_metrics/trade_history_audit.json

# ETA history file the design names. Not a verified prediction.
cat 4_output/trade_outputs/eta_verification_history.json
```

---

## Data files

| File | What it is designed to hold |
|------|-----------------------------|
| `4_output/trade_outputs/paper_trade_history.json` | Paper fills and their HNC fields |
| `4_output/performance_metrics/backtest_spot_results.json` | Spot replay |
| `4_output/performance_metrics/backtest_margin_results.json` | Margin replay |
| `4_output/portfolio_management/portfolio_truth.json` | Positions on connected exchanges |
| `4_output/trade_outputs/eta_verification_history.json` | Predicted time versus the fill |
| `4_output/performance_metrics/trade_history_audit.json` | Validator output |

Performance figures from these files are not quoted. There is no verified live track record.

---

## Takeaway

The design names a historical replay, a paper simulation, position fields, and a timing check against a fill. Go-live stays HOLD. Exchange keys in `.env` do not boot a supported live session. The orange release-boundary badge stays HOLD.

Measured P&L, win rate, and trade counts are not yet measured. There is no verified live track record.

What the design uses, in place of a plain moving-average stack:

- HNC (Harmonic Nexus Core), including the φ² Coherence Bridge and the frequencies the signal path already names (528 Hz among them)
- an ETA: a predicted time to a target
- bot-pattern tracking (Domain III)
- the same harmonic frame the rest of the organism uses

---

**Last Updated:** 2026-11-05
**Repository:** gary-leckey/aureon-trading
**Architect:** Gary LeCkey
**Model:** PEFCφS (Position of Echo-Feedback Cognitive φ-Substrate)
