# Aureon Quantum Trading System — Technical Specification

This document describes the production-grade architecture of the Aureon Quantum Trading System (AQTS), covering core services, configuration surfaces, automation workflows, and operational guardrails. It is designed to be the single source of truth for building, testing, and deploying AQTS in live or paper-trading environments.

---

## 1. System Overview

AQTS is organised into six cooperative layers that map directly to the source code:

| Layer | Purpose | Key Modules |
| --- | --- | --- |
| Multi-Source Data Ingestion | Aggregates market, order book, on-chain, sentiment, and macro signals. | [`core/dataIngestion.ts`](../core/dataIngestion.ts) |
| QGITA Detection Engine | Generates Lighthouse Events via Fibonacci time lattices and coherence metrics. | [`core/qgitaEngine.ts`](../core/qgitaEngine.ts) |
| AI Decision Fusion | Blends ensemble ML outputs with QGITA signals and crowd sentiment. | [`core/decisionFusion.ts`](../core/decisionFusion.ts) |
| Risk Management Core | Applies Kelly sizing, circuit breakers, hold windows, and liquidation logic. | [`core/riskManagement.ts`](../core/riskManagement.ts) |
| Execution Engine | Performs smart routing, latency modelling, and partial fills. | [`core/executionEngine.ts`](../core/executionEngine.ts) |
| Performance & Analytics | Tracks realised/unrealised P&L, Sharpe, drawdown, and Aureon telemetry. | [`core/performanceTracker.ts`](../core/performanceTracker.ts), UI components

The [`core/aqtsOrchestrator.ts`](../core/aqtsOrchestrator.ts) module wires these layers together and exposes a single `next()` loop that advances the entire system by one timestep.

---

## 2. Configuration Model

Centralised configuration lives in [`core/config.ts`](../core/config.ts). It unifies every subsystem via the `AQTSConfig` interface and provides a `mergeConfig` helper so overrides can be layered onto the shipped `defaultAQTSConfig`.

Key config blocks:

- **`ingestion`** — exchange roster, base price, and latency budgets.
- **`qgita`** — Fibonacci lattice depths, history retention, confidence gates.
- **`decision`** — buy/sell thresholds plus weighting between ensemble, sentiment, and QGITA inputs.
- **`risk`** — initial equity, Kelly multiplier, per-trade risk caps, leverage ceiling, hold windows, and drawdown circuit breaker.
- **`execution`** — slippage guardrails, latency ranges, and partial fill modelling.
- **`analytics`** — sliding window sizes for dashboards.

A ready-to-use configuration template is shipped at [`config/config.example.json`](../config/config.example.json). Copy this file, inject exchange API credentials (outside of version control), and adjust limits before live deployment.

---

## 3. Runtime Services

### 3.1 AQTS Orchestrator

The orchestrator accepts optional `DeepPartial<AQTSConfig>` overrides, constructs all layer instances, and exposes:

- `next()` — advances the simulation or live session by a single tick and returns raw data, Lighthouse events, decision output, any executed order, and performance snapshots.
- `getPortfolioState()` — returns current equity, max drawdown, and open positions (complete with stop-loss, take-profit, and hold window metadata).
- `reset()` — rebuilds the entire pipeline with fresh state and optional new overrides.

### 3.2 Risk Life-Cycle

Risk management now tracks realised equity, closes positions automatically when stop-loss/take-profit/hold conditions trigger, and enforces a hard circuit breaker via forced liquidation. This ensures P&L accounting remains consistent for downstream analytics and backtests.

### 3.3 Execution Semantics

Smart routing selects the optimal exchange venue and applies configurable slippage bounds, latency jitter, and partial fill probability, enabling more realistic execution metrics for monitoring and post-trade analysis.

---

## 4. Automation & Backtesting Toolkit

Two TypeScript scripts provide out-of-the-box automation:

| Command | Purpose | Notes |
| --- | --- | --- |
| `npm run simulate` | Streams a step-by-step session using `config/config.example.json` (or a custom file via `AQTS_CONFIG`). | Emits per-tick price, action, and signal diagnostics to the console. |
| `npm run backtest` | Runs multi-iteration backtests with aggregated win-rate, Sharpe, confidence, and drawdown stats. | Accepts overrides via environment variables: `AQTS_STEPS`, `AQTS_ITERATIONS`. |

Both scripts rely on [`scripts/simulate.ts`](../scripts/simulate.ts) and [`scripts/backtest.ts`](../scripts/backtest.ts) which read JSON overrides, merge them with `defaultAQTSConfig`, and then drive the `AQTSOrchestrator` / `runBacktest` APIs.

> **Note:** The scripts expect a TypeScript runtime such as [`tsx`](https://github.com/esbuild-kit/tsx). Install dependencies with `npm install` prior to execution (`npm install` may require proxy configuration in restricted environments).

---

## 5. Deployment Guidance

1. **Environment Preparation**
   - Provision a Node 20+ runtime (for CLI + orchestration) and a static hosting target for the Vite/React dashboard.
   - Inject exchange and messaging credentials via environment variables (never commit secrets).

2. **Build Targets**
   - `npm run build` bundles the analytics dashboard for static hosting.
   - Use `npm run simulate` or `npm run backtest` inside a supervisor (e.g., PM2, systemd) for headless orchestration.

3. **Process Model**
   - Front-end (Vite preview or bundled build) consumes the simulated WebSocket feed from [`websocketService.ts`](../websocketService.ts).
   - Back-end automation can run independently to produce orders, alerts, and reports.

4. **Scaling Considerations**
   - Use `AQTS_CONFIG` to point to environment-specific JSON definitions (paper/live).
   - Tune `risk.circuitBreaker` and `execution.maxSlippageBps` per exchange liquidity profile.

---

## 6. Monitoring & Maintenance

- **Real-Time Dashboards** — UI components (e.g., `LiveAnalysisStream`, `MonitoringPanel`, `PerformanceTracker`) consume orchestrator output for live visualisation.
- **Alerting** — Extend the alert service hooks in `MonitoringPanel` to push Telegram/Email/SMS notifications when Lighthouse confidence exceeds thresholds or when drawdown breaches warning levels.
- **Logs & Audits** — CLI scripts print granular per-step diagnostics; pipe to log aggregation (CloudWatch, ELK) for retention.
- **Housekeeping** — Rotate API keys regularly, enforce least privilege, and update dependency locks monthly to track upstream fixes.

---

## 7. Next Steps

- Integrate live exchange connectors to replace simulated fills while keeping the orchestration and risk interfaces unchanged.
- Attach machine-learning model backends to the `DecisionFusionLayer` to replace the current synthetic signals.
- Extend `runBacktest` with scenario seeds (bull/bear/sideways) to stress-test risk parameters before live trading.

