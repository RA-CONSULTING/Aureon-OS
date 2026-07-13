# Aureon Unified Ecosystem — Technical Overview

This document describes the practical architecture of the unified trading engine and related components in this repository. It is intentionally concise and factual.

## Objectives
- Centralize exchange connectivity, strategy evaluation, risk sizing, and order execution into one orchestrator.
- Support dry-run/testnet gating with hard risk caps.
- Allow simulation and debugging without live orders.

## High-Level Flow
1. Data Ingestion
   - Pull tickers, 24h stats, and balances from supported exchanges via REST/WebSocket through a unified client.
   - Cache latest prices per symbol; enforce thread-safe updates.
2. Opportunity Evaluation
   - Run strategy modules/heuristics to score symbols and produce candidate actions (buy/sell/hold), including confidence and sizing hints when available.
   - Optional subsystems (predictors, lattice, etc.) degrade gracefully if absent.
3. Risk and Sizing
   - Apply environment-configured caps (e.g., max per-order notional), min notional checks, and precision rules per exchange.
   - Kelly-like or fixed-fraction risk models may be used where coded; defaults should be conservative.
4. Order Placement (or Dry-Run)
   - If in dry-run/testnet, record intent and simulate fills with reasonable assumptions.
   - If live, submit orders via the exchange client, handle rejects/partial fills, and backoff/retry as needed.
5. State & P&L Tracking
   - Track positions, cost basis, and equity snapshots; refresh periodically from exchange to avoid drift.

## Core Modules
- Orchestrator: `aureon_unified_ecosystem.py`
  - Initializes the multi-exchange client and orchestrates the end-to-end loop.
  - Maintains price caches, symbol metadata, and ecosystem-wide state.
  - Applies strategy outputs, risk sizing, and issues orders (or simulates in dry-run).
- Exchange Layer:
  - `unified_exchange_client.py` / `MultiExchangeClient`: common surface for balances, tickers, and orders.
  - Helpers: [binance_client.py](../binance_client.py), [alpaca_client.py](../alpaca_client.py), others.
- Runners:
  - Live: [run_live_trading.py](../run_live_trading.py)
  - Debug: [run_ecosystem_debug.py](../run_ecosystem_debug.py)
  - Simulation: [aureon_51_sim.py](../aureon_51_sim.py)

## Configuration & Safety
- Environment file: [.env.example](../.env.example)
  - `BINANCE_USE_TESTNET=true` to target testnet where supported.
  - `BINANCE_DRY_RUN=true` to disable live order placement.
  - `BINANCE_RISK_MAX_ORDER_USDT=25` to cap individual order size.
- Precision/Filters
  - Respect exchange rules: min notional, step sizes, tick sizes per symbol.
- Logging & Monitoring
  - Prefer structured logs for orders, positions, and errors; supervise runs.

## Extending Strategies
- Keep strategy logic pure where possible: accept current market state, return ranked signals.
- Include fields like `symbol`, `side`, `confidence`, and optional `target_notional`.
- The orchestrator is responsible for final sizing and execution based on env caps and exchange rules.

## Known Limitations (Realistic)
- API rate limits and outages occur; retries and backoff are necessary but not perfect.
- Slippage and partial fills are part of live trading; simulation is an approximation.
- Backtests/simulations can overstate results if fees, latency, and liquidity aren’t modeled conservatively.

## Disclaimer
This repository is for research and development. It is not financial advice. No guarantees of profits or loss prevention are made. Use at your own risk and comply with all applicable laws and exchange Terms of Service.
