# Technical Overview

This repository provides a research and prototyping framework for multi-exchange automated trading. The central engine ("Unified Ecosystem") wires together exchange connectivity, strategy evaluation, risk sizing, and order execution. This document keeps to practical details: what exists, how it runs, and real limits.

## Capabilities
- Connects to supported exchanges to fetch prices, balances, and place/cancel orders (when not in dry-run/testnet).
- Runs strategies/heuristics inside one orchestrator process that schedules scans and sizes positions.
- Supports simulation scripts to test logic without live orders.
- Uses environment variables to enforce dry-run/testnet and risk caps.

## Safety First
- Losses are possible. Dry-run/testnet-first is strongly recommended.
- Respect exchange precision/min-notional/fee rules; size conservatively.
- Start with small caps and supervise runs.

## Quick Start (Dry-Run)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Edit .env values as needed

# Terminal 1: Brain
python aureon_miner.py

# Terminal 2: Ecosystem (dry-run unless you enable live)
python aureon_unified_ecosystem.py
```

To allow live behavior (only after full review and with small sizing):
```bash
LIVE=1 python aureon_unified_ecosystem.py
```

## Configuration (Environment)
Key variables from `.env.example`:
- `BINANCE_API_KEY` / `BINANCE_API_SECRET`: credentials (never commit real keys)
- `BINANCE_USE_TESTNET=true`: use testnet (recommended first)
- `BINANCE_RISK_MAX_ORDER_USDT=25`: per-order risk cap
- `BINANCE_DRY_RUN=true`: simulate orders (no live POST)
- `BINANCE_SYMBOL=BTCUSDT`: default symbol for sample scripts
- `BINANCE_RISK_FRACTION=0.02`: fraction of free quote balance per trade

Other venues and modules may have their own variables; check their client files.

## Architecture (High-Level)
- Orchestrator: `aureon_unified_ecosystem.py`
  - Initializes exchange clients, maintains state cache, evaluates strategies, sizes orders, and executes when permitted.
- Brain: `aureon_miner.py`
  - Produces signals/state that the ecosystem reads.
- Simulation: `aureon_51_sim.py` and related scripts for non-order testing.
- Helpers: `binance_client.py`, `alpaca_client.py`, etc.

## Running Modes
- Simulation: `python aureon_51_sim.py`
- Dry-Run: default unless you set explicit live flags
- Live: gated by env and risk caps; enable only after verification

## Key Files
- Orchestrator: `aureon_unified_ecosystem.py`
- Brain: `aureon_miner.py`
- Simulation: `aureon_51_sim.py`
- Binance helper: `binance_client.py`
- Alpaca helper: `alpaca_client.py`
- Config template: `.env.example`
- Start scripts: `start_full_ecosystem.sh`, `start_full_ecosystem.ps1`

## Limits & Responsibilities
- No guarantees of profit; markets carry risk and friction (fees, slippage, partial fills, outages).
- Respect exchange ToS and regional constraints.
- Supervise runs; keep conservative risk caps.

## Troubleshooting
See `docs/Troubleshooting.md` for common issues.

## Contributing & Security
- See `CONTRIBUTING.md` for PR guidelines.
- See `SECURITY.md` for vulnerability reporting.
