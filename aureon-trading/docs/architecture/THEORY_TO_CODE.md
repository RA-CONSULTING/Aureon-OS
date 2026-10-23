# Theory to Code: Research → Implementation Map

How Aureon's research concepts become working code.

## Harmonic Nexus Core (HNC)
**Theory:** The master formula Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α tanh(g Λ_Δt(t)) + β Λ(t-τ)
**Implementation:** `aureon/core/aureon_nexus.py` — Central signal processing
**Used by:** All trading strategies, intelligence systems

## Planetary Harmonic Sweep  
**Theory:** FFT spectral analysis aligned with planetary orbital frequencies
**Implementation:** `aureon/harmonic/aureon_planetary_harmonic_sweep.py`
**Used by:** Harmonic fusion → Intelligence → Trading decisions

## Queen Hive Mind
**Theory:** Multi-layer AI decision system with 4th-pass veto authority
**Implementation:** `aureon/queen/` — 53 modules including neural implementation, cognitive narrator
**Used by:** Final trade approval, strategy selection

## Bot Census & Detection
**Theory:** Identifying 23 algorithmic trading patterns from 37 institutional firms
**Implementation:** `aureon/bots_intelligence/` — 21 modules for detection & profiling
**Also:** `aureon/analytics/aureon_historical_bot_census.py`
**Research:** [Bot Intelligence](../research/BOT_INTELLIGENCE.md)

## Ancient Wisdom Integration
**Theory:** 12 civilizations' mathematical patterns applied to market cycles
**Implementation:** `aureon/wisdom/` — 35 modules (Celtic, Ghost Dance, Enigma, QGita)
**Also:** `aureon/decoders/` — 11 modules (Emerald Tablet, Aztec, Egyptian, Ogham)
**Research:** [Ancient Convergence](../research/ANCIENT_CONVERGENCE.md)

## Geopolitical Forensics
**Theory:** Geopolitical events correlate with market movements via harmonic signatures
**Implementation:** `aureon/harmonic/geopolitical_forensics.py`
**Fed by:** `aureon/data_feeds/` news and event streams

## Unified Market Trader
**Theory:** Cross-exchange arbitrage via central beat feed merging
**Implementation:** `aureon/exchanges/unified_market_trader.py` (1,420 lines)
**Coordinates:** Kraken, Capital.com, Alpaca, Binance in one runtime

## Voice Agent System
**Theory:** Natural language voice control for trading operations
**Implementation:** `aureon/autonomous/aureon_unified_voice_agent.py` + 14 supporting modules
**Includes:** Intent cognition, desktop control, elephant memory, code bridges

## Adaptive Profit Gate
**Theory:** Kelly-criterion risk management adapted for harmonic trading
**Implementation:** `aureon/utils/adaptive_prime_profit_gate.py`
**Used by:** All trading modules for position sizing

## Ghost Dance Protocol
**Theory:** Counter-manipulation protocol inspired by indigenous resistance
**Implementation:** `aureon/wisdom/aureon_ghost_dance_protocol.py`
**Used by:** Trading execution layer as a market manipulation shield
**Research:** [Counter-Strategies](../research/COUNTER_STRATEGIES.md)

## See Also
- [Module Reference](../MODULES_AT_A_GLANCE.md) — Full 715-module directory
- [Intelligence Wiring Matrix](INTELLIGENCE_WIRING_MATRIX.md) — What feeds what
- [HNC White Paper](../HNC_UNIFIED_WHITE_PAPER.md) — Mathematical foundations
