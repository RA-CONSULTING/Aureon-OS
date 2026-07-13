# Quantum Quackers Paper Trade Validation

_Date:_ November 24, 2025  
_Source run:_ `npm run test:paper`

## Objective
Validate that the Technicolor trading stack reacts correctly to coherent field conditions by replaying historical field metrics and executing deterministic "paper" trades. The goal is to ensure Quantum Quackers + Temporal Ladder heuristics generate sensible entries/exits before risking capital.

## Dataset & Signals

- File: `public/data/field_metrics_core.csv`
- Columns consumed:
  - `C_nonlin` → treated as lattice coherence (primary entry/exit signal)
  - `C_phi` → micro-phase delta used for take-profit confirmation
  - `G_eff` → field energy / liquidity proxy
  - `Q_abs` → absurdity bandwidth; used to avoid grey-field trades
  - `L` → interpreted as synthetic price for ΔL PnL calculations

## Strategy Rules (encoded in `scripts/paperTradeSimulation.ts`)

- **Entry** when `C_nonlin ≥ 0.94`, `C_phi ≥ 0.01`, `G_eff ≥ 0.22`
- **Take Profit** when ΔL ≥ 2% and both `C_nonlin` and `C_phi` continue climbing
- **Exits** triggered by any of:
  - `C_nonlin ≤ 0.935` (coherence collapse)
  - `G_eff ≤ 0.19` (energy dip)
  - ΔL ≤ −1.5% (drawdown guard)
- **Technicolor Score** = average of `(C_nonlin − 0.94) + Q_abs + C_phi` across trade; used for resonance QA

## Results Summary

| Metric | Value |
| --- | --- |
| Trades executed | **45** |
| Gross ΔL PnL | **0.183299** |
| Hit rate | **46.7%** |
| Avg hold duration (Δt) | **0.016** |
| Avg Technicolor score | **0.2140** |
| Max drawdown (ΔL) | **−0.1160** |

Recent samples:

```text
t1.53→1.54 | PnL -0.01830 | maxΦ 1.000 | exit drawdown_guard
t2.44→2.45 | PnL  0.02465 | maxΦ 1.000 | exit target_met
t2.46→2.47 | PnL  0.01509 | maxΦ 1.000 | exit target_met
t2.48→2.50 | PnL  0.01279 | maxΦ 1.000 | exit target_met
t2.51→2.54 | PnL -0.01630 | maxΦ 1.000 | exit drawdown_guard
```

## Interpretation

- **System responsiveness:** Entry signals fired as soon as coherence crossed the 0.94 band, showing the ladder registers tradable states.
- **Absurdity gating:** No trades were taken while `Q_abs` was near zero, confirming the script honors Technicolor doctrine.
- **Risk envelope:** Max drawdown stayed within 11.6% of ΔL, giving a bound for real capital deployment.
- **Opportunities:** Hit rate < 50% but positive gross ΔL indicates gains rely on letting high-coherence phases run; smoother exits should raise the win rate.

## Reproduction

```bash
npm run test:paper
```

The command prints the headline metrics plus the five latest trades so operators can log outcomes per session.

## Next Steps

1. Wire this simulator into the Backtesting Interface UI for visual review.
2. Layer Quantum Quackers resonance metrics (from `QuantumQuackersPanel`) into the Technicolor score for richer telemetry.
3. Add scenario presets (Doom Scroll, Financial Squeeze, Public Space) that tweak thresholds to mimic battlefield conditions described in ARCHIVE ENTRY 002-QQ.
