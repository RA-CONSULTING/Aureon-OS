# Aureon Navigation Guide

Three guided paths through the system depending on your role.

## Trader Path
Start here if you want to run the trading system.

1. **[Quick Start](QUICK_START.md)** — Get the system running in 10 minutes
2. **[Exchange Setup](#exchange-setup)** — Configure Kraken, Capital.com, Alpaca, Binance
3. **[Live Trading Runbook](LIVE_TRADING_RUNBOOK.md)** — Day-to-day operations
4. **[Dashboard Guide](DASHBOARD_GUIDE.md)** — Monitor your positions live
5. **[Scripts Index](SCRIPTS_INDEX.md)** — Find the right startup script

## Developer Path  
Start here if you want to understand or extend the system.

1. **[Architecture Overview](architecture/SYSTEM_ARCHITECTURE_MAP.md)** — 5-phase startup, subsystem map
2. **[Module Reference](MODULES_AT_A_GLANCE.md)** — All 715 modules across 24 domains
3. **[Intelligence Wiring Matrix](architecture/INTELLIGENCE_WIRING_MATRIX.md)** — What feeds what
4. **[Open Market Data Matrix](architecture/OPEN_MARKET_DATA_MATRIX.md)** — Data topology
5. **[Theory to Code](architecture/THEORY_TO_CODE.md)** — Research concepts → implementations
6. **[Contributing](../CONTRIBUTING.md)** — Code style, testing, PR process

## Researcher Path
Start here if you're interested in the harmonic/mathematical research.

1. **[HNC White Paper](HNC_UNIFIED_WHITE_PAPER.md)** — Harmonic Nexus Core mathematical framework
2. **[Ancient Convergence](research/ANCIENT_CONVERGENCE.md)** — 12 civilizations, 47+ convergence points
3. **[Bot Intelligence](research/BOT_INTELLIGENCE.md)** — 23 algorithms, 37 firms profiled
4. **[Financial Exposure](research/FINANCIAL_EXPOSURE.md)** — Market extraction evidence
5. **[Unified Field](research/UNIFIED_FIELD.md)** — Connecting all the dots
6. **[Counter-Strategies](research/COUNTER_STRATEGIES.md)** — How to fight back

## Key Concepts Quick Reference
| Concept | What It Is | Where to Find It |
|---------|-----------|-----------------|
| HNC | Harmonic Nexus Core — the master trading formula | `aureon/core/aureon_nexus.py` |
| ThoughtBus | Central event bus connecting all systems | `aureon/core/aureon_thought_bus.py` |
| Queen | AI decision authority with 4th-pass veto power | `aureon/queen/` (53 modules) |
| Auris Nodes | 9 specialized prediction nodes + Lighthouse consensus | `aureon/intelligence/` |
| Seer | ML prediction engine | `aureon/intelligence/aureon_seer.py` |
| Harmonic Fusion | Combines planetary + market harmonics | `aureon/harmonic/aureon_harmonic_fusion.py` |
| Orca Kill Chain | Execution sequence for live trades | `aureon/trading/aureon_orca_kill_chain.py` |
| Ghost Dance | Counter-manipulation protocol | `aureon/wisdom/aureon_ghost_dance_protocol.py` |
| Unified Market Trader | Multi-exchange orchestration | `aureon/exchanges/unified_market_trader.py` |
