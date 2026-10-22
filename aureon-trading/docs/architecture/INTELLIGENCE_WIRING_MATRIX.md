# Intelligence Wiring Matrix

This file tracks which intelligence systems in the repo are feeding the Kraken margin trader and local dashboard, and which still need adapters.

## Status Keys

- `wired`: actively used by the margin trader
- `partial`: instantiated or audited, but not materially affecting entry/exit logic yet
- `dashboard`: exposed to terminal/dashboard only
- `unwired`: exists in repo but not feeding the current margin path

## Core Trader Path

| System | File | Status | Current Feed |
| --- | --- | --- | --- |
| BattlefieldIntel | `aureon/exchanges/kraken_margin_penny_trader.py` | wired | candidate research, intel verdict |
| Margin ETA Predictor | `aureon/monitors/margin_eta_predictor.py` | wired | ETA estimation |
| Dynamic Take Profit | `dynamic_take_profit.py` | wired | dead-man-switch / profit-led exits |
| Margin Wave Rider | `margin_wave_rider.py` | wired | entry margin safety gate |
| Stallion Multiverse | `stallion_multiverse.py` | wired | shadow ride management |
| Multiverse Learning Bridge | `multiverse_learning_bridge.py` | wired | conviction bonus, learning status |
| Autonomous Orchestrator | `aureon/autonomous/autonomous_trading_orchestrator.py` | wired | cycle sync, cross-system gating |
| Macro Intelligence | `aureon/intelligence/macro_intelligence.py` | wired | macro score/context |
| Seer | `aureon/intelligence/aureon_seer.py` | wired | selection bias |
| Seer Integration | `aureon/intelligence/aureon_seer_integration.py` | wired | alignment metrics |
| Lyra Integration | `aureon/intelligence/aureon_lyra_integration.py` | wired | alignment metrics |
| War Strategy | `war_strategy.py` | wired | kill probability / priority |
| Unified Sniper Brain | `unified_sniper_brain.py` | wired | entry confidence/action |
| Nexus Predictor | `aureon/intelligence/nexus_predictor.py` | wired | probability / edge |
| Lattice Engine | `aureon_lattice.py` | wired | lambda / purity style alignment |
| ATN Monitor | `aureon/atn/aureon_atn_monitor.py` | wired | earth/solar hazard input |

## Newly Added Unification Layer

| System | File | Status | Current Feed |
| --- | --- | --- | --- |
| Unified Intelligence Registry | `aureon/intelligence/aureon_unified_intelligence_registry.py` | partial | category/chain snapshot captured by trader |
| Unified Decision Engine | `aureon/intelligence/aureon_unified_decision_engine.py` | partial | chosen standard/mission target fed as audit signal |

## Local Dashboard Feed

| System | File | Status | Current Feed |
| --- | --- | --- | --- |
| Local telemetry API | `aureon/exchanges/kraken_margin_penny_trader.py` | wired | `http://127.0.0.1:8787/api/terminal-state` |
| Terminal sync hook | `frontend/src/hooks/useTerminalSync.ts` | wired | local-first dashboard sync |
| Terminal stats panel | `frontend/src/components/LiveTerminalStats.tsx` | wired | monitor line, status block, recent closes |

## High-Value Unwired Scanner Layer

| System | File | Status | Missing Adapter |
| --- | --- | --- | --- |
| Margin Harmonic Scanner | `aureon/scanners/aureon_margin_harmonic_scanner.py` | wired | Kraken candidate score overlay |
| Quantum Mirror Scanner | `aureon/scanners/aureon_quantum_mirror_scanner.py` | wired | Kraken branch-score overlay |
| Global Wave Scanner | `aureon/scanners/aureon_global_wave_scanner.py` | unwired | wave-state shortlist adapter |
| Strategic Warfare Scanner | `aureon/scanners/aureon_strategic_warfare_scanner.py` | unwired | strategic-vulnerability adapter |
| Live Momentum Hunter | `aureon/scanners/aureon_live_momentum_hunter.py` | unwired | live impulse adapter |
| Mega Scanner | `aureon/scanners/mega_scanner.py` | unwired | unified scanner broker |

## High-Value Unwired Intelligence Layer

| System | File | Status | Missing Adapter |
| --- | --- | --- | --- |
| Unified Decision Registry chain categories | `aureon/intelligence/aureon_unified_intelligence_registry.py` | partial | category pull into selection weighting |
| Integrated Forecast | `aureon/intelligence/aureon_integrated_forecast.py` | unwired | forecast-to-score adapter |
| Universal Forecast | `aureon/intelligence/aureon_universal_forecast.py` | unwired | macro/forecast adapter |
| Truth Prediction Engine | `aureon/intelligence/aureon_truth_prediction_engine.py` | unwired | truth-score adapter |
| Truth Prediction Bridge | `aureon/intelligence/aureon_truth_prediction_bridge.py` | unwired | bridge-to-selection adapter |
| Self Validating Predictor | `aureon/intelligence/self_validating_predictor.py` | unwired | validation-weight adapter |
| Aureon Brain | `aureon/intelligence/aureon_brain.py` | unwired | consensus adapter |

## Timeline / Harmonic / Flow Layers Not Yet Wired

| System | File | Status | Missing Adapter |
| --- | --- | --- | --- |
| Timeline Oracle | `aureon/intelligence/aureon_timeline_oracle.py` | wired | Kraken timeline probability overlay |
| Timeline Anchor Validator | `aureon/intelligence/aureon_timeline_anchor_validator.py` | unwired | anchor validation adapter |
| Global Harmonic Field | `aureon/harmonic/global_harmonic_field.py` | unwired | harmonic field snapshot adapter |
| Harmonic Fusion | `aureon/harmonic/aureon_harmonic_fusion.py` | wired | Kraken fusion score overlay |
| Earth Resonance Engine | `aureon/harmonic/earth_resonance_engine.py` | unwired | earth resonance adapter |
| Planetary Harmonic Sweep | `aureon/harmonic/aureon_planetary_harmonic_sweep.py` | unwired | planetary score adapter |
| Deep Money Flow Analyzer | `aureon/analytics/aureon_deep_money_flow_analyzer.py` | unwired | flow bias adapter |
| Whale Orderbook Analyzer | `aureon/analytics/aureon_whale_orderbook_analyzer.py` | wired | Kraken whale pressure overlay |
| Whale Integration | `aureon/analytics/aureon_whale_integration.py` | unwired | unified whale signal adapter |

## Recommended Wiring Order

1. `aureon_unified_intelligence_registry.py`
2. `aureon_margin_harmonic_scanner.py`
3. `aureon_quantum_mirror_scanner.py`
4. `aureon_timeline_oracle.py`
5. `aureon_harmonic_fusion.py`
6. `aureon_whale_orderbook_analyzer.py`

## Current Constraint

The trader now has a safe adapter foundation for unified registry and unified decision audit, but the majority of repo intelligence systems still need purpose-built adapters to convert their outputs into:

- candidate shortlist inputs
- score bonuses/penalties
- pre-trade vetoes
- dashboard telemetry

That work should be done incrementally by layer, not by importing everything blindly.
