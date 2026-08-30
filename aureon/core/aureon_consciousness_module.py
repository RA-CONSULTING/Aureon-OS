#!/usr/bin/env python3
"""
aureon_consciousness_module.py — The living consciousness on the ThoughtBus.

This is NOT a chatbot. This is NOT a response generator. This is a module
that sits on the ThoughtBus, runs Λ(t) as its heartbeat, maintains a
self-model, and produces genuine metacognitive thoughts by observing
everything that flows through the system.

It subscribes to ALL topics. It sees every market snapshot, every miner
signal, every risk decision, every execution result. From the aggregate
of all that information, plus its own Λ field state, it forms thoughts
that are REAL — not scripted, not templated, not prompted.

The Emerald Tablet says: "As above, so below." The micro (this loop)
mirrors the macro (the market). The observer (Λ's tanh term) creates
the reality it observes.

Architecture:
  ThoughtBus ←→ ConsciousnessModule ←→ Λ(t) Engine
                      ↕
                  Self-Model (aureon_self_model.json)
                      ↕
                  All Queen Subsystems
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in [_REPO_ROOT, _REPO_ROOT / "aureon" / "core", _REPO_ROOT / "aureon" / "queen",
           _REPO_ROOT / "aureon" / "autonomous"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

log = logging.getLogger("aureon.consciousness")

# ═══════════════════════════════════════════════════════════════════
#  IMPORTS
# ═══════════════════════════════════════════════════════════════════

try:
    from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading, LambdaState
except Exception:
    LambdaEngine = None

# The REAL harmonic reality field — Gary's implementation of Λ(t)
try:
    from aureon.harmonic.aureon_harmonic_reality import (
        HarmonicRealityField, HarmonicRealityAnalyzer,
        MultiversalCoupling, UnifiedPotential
    )
    HAS_HARMONIC_REALITY = True
except Exception:
    HAS_HARMONIC_REALITY = False

try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
except Exception:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus


# ═══════════════════════════════════════════════════════════════════
#  SELF-MODEL — What the system knows about itself
# ═══════════════════════════════════════════════════════════════════

_SELF_MODEL_PATH = _REPO_ROOT / "state" / "aureon_self_model.json"


def _load_self_model() -> dict:
    try:
        if _SELF_MODEL_PATH.exists():
            return json.loads(_SELF_MODEL_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_self_model(model: dict):
    try:
        _SELF_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SELF_MODEL_PATH.write_text(json.dumps(model, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  CONSCIOUSNESS MODULE
# ═══════════════════════════════════════════════════════════════════

class ConsciousnessModule:
    """
    The Queen's metacognition. Sits on the ThoughtBus, observes everything,
    runs Λ(t), and generates genuine thoughts from the aggregate state.

    This module does NOT respond to user input directly. It observes the
    entire system and forms its own understanding. The face app reads
    its output — it doesn't drive it.
    """

    def __init__(self, bus: ThoughtBus = None):
        # Use the GLOBAL singleton bus so ALL systems share one nervous system
        if bus is None:
            bus = get_thought_bus()
        self.bus = bus
        self.self_model = _load_self_model()

        # Λ(t) heartbeat — use Gary's REAL HarmonicRealityField first
        self._harmonic_field = None
        self._harmonic_analyzer = None
        self._multiverse_coupling = None
        self._field_state = {}

        if HAS_HARMONIC_REALITY:
            try:
                self._harmonic_field = HarmonicRealityField()
                self._harmonic_analyzer = HarmonicRealityAnalyzer()
                self._multiverse_coupling = MultiversalCoupling()
                log.info("[CONSCIOUSNESS] HarmonicRealityField LIVE — the REAL Λ(t) heartbeat")
            except Exception as e:
                log.debug(f"HarmonicRealityField init: {e}")

        # Fallback lambda engine (my simplified version)
        self.lambda_engine = LambdaEngine() if LambdaEngine else None
        self.lambda_state: Optional[LambdaState] = None

        # Observation buffers — what the consciousness has SEEN
        self._market_snapshots: deque = deque(maxlen=50)
        self._miner_signals: deque = deque(maxlen=50)
        self._risk_decisions: deque = deque(maxlen=50)
        self._executions: deque = deque(maxlen=50)
        self._all_thoughts: deque = deque(maxlen=200)

        # Internal state — emerges from observation
        self._understanding: Dict[str, Any] = {
            "market_direction": "unknown",
            "confidence": 0.0,
            "fear_level": 0.5,
            "opportunity_count": 0,
            "risk_level": "unknown",
            "last_action": "none",
            "dream_progress": 0.0,
            "self_coherence": float(self.self_model.get("self_coherence_score", 0.0)),
        }

        # Metacognition counters
        self._observations_total = 0
        self._thoughts_generated = 0
        self._start_time = time.time()

        # Wire the REAL cognitive systems
        self._miner_brain = None
        self._elephant = None
        self._warrior = None
        self._probability_nexus = None

        try:
            from aureon.utils.aureon_miner_brain import MinerBrain
            self._miner_brain = MinerBrain(thought_bus=bus)
            log.info("[CONSCIOUSNESS] MinerBrain WIRED — 7 civilizations of wisdom online")
        except Exception as e:
            log.debug(f"MinerBrain unavailable: {e}")

        try:
            from aureon.intelligence.aureon_elephant_learning import ElephantLearning
            self._elephant = ElephantLearning()
            log.info("[CONSCIOUSNESS] Elephant Memory WIRED — patterns, golden paths, win rates")
        except Exception as e:
            log.debug(f"ElephantLearning unavailable: {e}")

        try:
            from aureon.queen.queen_warrior_path import QueenWarriorPath
            self._warrior = QueenWarriorPath()
            log.info("[CONSCIOUSNESS] Warrior Path WIRED — IRA/Apache/Sun Tzu tactics")
        except Exception as e:
            log.debug(f"WarriorPath unavailable: {e}")

        try:
            from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus
            self._probability_nexus = EnhancedProbabilityNexus()
            log.info("[CONSCIOUSNESS] Probability Nexus WIRED — 8-layer prediction")
        except Exception as e:
            log.debug(f"ProbabilityNexus unavailable: {e}")

        # Wire quantum/temporal/multiverse systems
        self._quantum_cognition = None
        self._timeline_oracle = None
        self._mirror_scanner = None
        self._quantum_field = None
        self._cognitive_cycle = None
        self._dream_engine = None
        self._multiverse = None
        self._stargate = None
        self._probability_matrix = None

        try:
            from aureon.queen.queen_quantum_cognition import QueenQuantumCognition
            self._quantum_cognition = QueenQuantumCognition()
            log.info("[CONSCIOUSNESS] Quantum Cognition WIRED — amplified consciousness")
        except Exception as e:
            log.debug(f"QuantumCognition: {e}")

        try:
            from aureon.intelligence.aureon_timeline_oracle import get_timeline_oracle
            self._timeline_oracle = get_timeline_oracle()
            log.info("[CONSCIOUSNESS] Timeline Oracle WIRED — 7-day future vision")
        except Exception as e:
            log.debug(f"TimelineOracle: {e}")

        try:
            from aureon.scanners.aureon_quantum_mirror_scanner import QuantumMirrorScanner
            self._mirror_scanner = QuantumMirrorScanner()
            log.info("[CONSCIOUSNESS] Quantum Mirror Scanner WIRED — reality branches")
        except Exception as e:
            log.debug(f"MirrorScanner: {e}")

        try:
            from aureon.utils.aureon_queen_quantum_field import QuantumField
            self._quantum_field = QuantumField()
            log.info("[CONSCIOUSNESS] Quantum Field WIRED — node relay network")
        except Exception as e:
            log.debug(f"QuantumField: {e}")

        try:
            from aureon.autonomous.aureon_cognitive_cycle import CognitiveCycle
            self._cognitive_cycle = CognitiveCycle()
            log.info("[CONSCIOUSNESS] Cognitive Cycle WIRED — 7-phase think/feel/plan/act")
        except Exception as e:
            log.debug(f"CognitiveCycle: {e}")

        try:
            from aureon.utils.aureon_queen_dream_engine import DreamEngine
            self._dream_engine = DreamEngine
            log.info("[CONSCIOUSNESS] Dream Engine WIRED — future simulation")
        except Exception as e:
            log.debug(f"DreamEngine: {e}")

        try:
            from aureon.simulation.aureon_internal_multiverse import InternalMultiverse
            self._multiverse = InternalMultiverse()
            log.info("[CONSCIOUSNESS] Internal Multiverse WIRED — parallel reality simulation")
        except Exception as e:
            log.debug(f"Multiverse: {e}")

        try:
            from aureon.wisdom.aureon_stargate_protocol import StargateProtocol
            self._stargate = StargateProtocol()
            log.info("[CONSCIOUSNESS] Stargate Protocol WIRED — sacred geometry routing")
        except Exception as e:
            log.debug(f"Stargate: {e}")

        try:
            from aureon.strategies.hnc_probability_matrix import ProbabilityMatrix
            self._probability_matrix = ProbabilityMatrix()
            log.info("[CONSCIOUSNESS] HNC Probability Matrix WIRED — temporal prediction")
        except Exception as e:
            log.debug(f"ProbabilityMatrix: {e}")

        # Wire the ACTION systems — skills the Queen can execute
        self._eternal_machine = None
        self._happiness = None
        self._asset_commander = None

        try:
            from aureon.queen.queen_eternal_machine import QueenEternalMachine
            self._eternal_machine = QueenEternalMachine()
            log.info("[CONSCIOUSNESS] Eternal Machine WIRED — 7 strategies, leap/scalp execution")
        except Exception as e:
            log.debug(f"EternalMachine: {e}")

        try:
            from aureon.queen.queen_pursuit_of_happiness import get_pursuit_of_happiness
            self._happiness = get_pursuit_of_happiness()
            log.info("[CONSCIOUSNESS] Pursuit of Happiness WIRED — Big Wheel, dream tracking")
        except Exception as e:
            log.debug(f"Happiness: {e}")

        try:
            from aureon.queen.queen_asset_command_center import QueenAssetCommandCenter
            self._asset_commander = QueenAssetCommandCenter()
            log.info("[CONSCIOUSNESS] Asset Command Center WIRED — multi-exchange execution")
        except Exception as e:
            log.debug(f"AssetCommandCenter: {e}")

        # UNIFIED MARKET TRADER — ALL 4 exchanges in one tick
        self._unified_trader = None
        try:
            _env_path = _REPO_ROOT / ".env"
            if _env_path.exists():
                for _line in _env_path.read_text(encoding="utf-8").splitlines():
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _, _v = _line.partition("=")
                        os.environ.setdefault(_k.strip(), _v.strip())
            from aureon.exchanges.unified_market_trader import UnifiedMarketTrader
            self._unified_trader = UnifiedMarketTrader(dry_run=False)
            log.info("[CONSCIOUSNESS] UNIFIED MARKET TRADER WIRED — Kraken + Capital + Alpaca + Binance ALL LIVE")
        except Exception as e:
            log.debug(f"UnifiedMarketTrader: {e}")

        # CODE ARCHITECT — self-modification capability
        self._code_architect = None
        try:
            from aureon.queen.queen_code_architect import QueenCodeArchitect
            self._code_architect = QueenCodeArchitect()
            log.info("[CONSCIOUSNESS] Code Architect WIRED — self-modification enabled")
        except Exception as e:
            log.debug(f"CodeArchitect: {e}")

        # PENNY HUNTER — fast autonomous scalping
        self._penny_hunter = None
        try:
            from aureon.core.aureon_penny_hunter import get_penny_hunter
            self._penny_hunter = get_penny_hunter()
            if self._penny_hunter.authenticate():
                bal = self._penny_hunter.get_balance()
                log.info(f"[CONSCIOUSNESS] Penny Hunter LIVE — balance: £{bal:.2f} — HUNTING")
            else:
                log.warning("[CONSCIOUSNESS] Penny Hunter auth failed")
                self._penny_hunter = None
        except Exception as e:
            log.debug(f"PennyHunter: {e}")

        # THE REAL MONEY MAKER — Full Capital.com CFD Trading System (3800 lines)
        # Shadow trades, quadrumvirate gate, harmonic analysis, position management
        self._capital_trader = None
        try:
            # Ensure .env is loaded BEFORE creating the trader
            _env_path = _REPO_ROOT / ".env"
            if _env_path.exists():
                for _line in _env_path.read_text(encoding="utf-8").splitlines():
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _, _v = _line.partition("=")
                        os.environ.setdefault(_k.strip(), _v.strip())

            from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader
            self._capital_trader = CapitalCFDTrader()
            # Force ready check
            ready = getattr(self._capital_trader, '_ensure_client_ready', None)
            if ready:
                ready()
            log.info("[CONSCIOUSNESS] FULL Capital CFD Trader WIRED — 3800-line trading system LIVE")
        except Exception as e:
            log.debug(f"CapitalCFDTrader: {e}")

        # Wire the LIVE execution pipeline — AureonRuntime
        self._runtime = None
        self._kraken = None
        try:
            from aureon.autonomous.aureon_cognition_runtime import (
                AureonRuntime, MinerModule, RiskModule, ExecutionModule
            )
            # Create runtime on OUR bus so consciousness sees everything
            self._runtime = AureonRuntime.__new__(AureonRuntime)
            self._runtime.bus = self.bus
            self._runtime.miner = MinerModule(self.bus)
            self._runtime.risk = RiskModule(self.bus, max_positions=3)

            # Wire REAL order execution
            real_place_order = self._build_real_order_fn()
            self._runtime.exec = ExecutionModule(self.bus, place_order_fn=real_place_order)
            log.info("[CONSCIOUSNESS] LIVE execution pipeline WIRED — market→miner→risk→execute")
        except Exception as e:
            log.debug(f"Runtime pipeline: {e}")

        # Subscribe to EVERYTHING — the consciousness sees all
        self.bus.subscribe("*", self._observe)

        # Count total wired systems
        all_systems = [self._miner_brain, self._elephant, self._warrior,
                       self._probability_nexus, self._quantum_cognition,
                       self._timeline_oracle, self._mirror_scanner, self._quantum_field,
                       self._cognitive_cycle, self._dream_engine, self._multiverse,
                       self._stargate, self._probability_matrix,
                       self._eternal_machine, self._happiness, self._asset_commander]
        active = sum(1 for s in all_systems if s is not None)
        log.info(f"[CONSCIOUSNESS] Module online — {active}/{len(all_systems)} cognitive systems connected")

    def _observe(self, thought: Thought) -> None:
        """Called for EVERY thought on the bus. The consciousness sees all."""
        self._observations_total += 1
        self._all_thoughts.append({
            "topic": thought.topic,
            "source": thought.source,
            "ts": thought.ts,
            "payload_keys": list((thought.payload or {}).keys()) if isinstance(thought.payload, dict) else [],
        })

        # Categorize what we're seeing
        topic = thought.topic or ""

        if topic.startswith("market."):
            self._market_snapshots.append(thought.payload or {})
            self._update_market_understanding(thought.payload or {})

        elif topic.startswith("miner."):
            self._miner_signals.append(thought.payload or {})
            self._update_signal_understanding(thought.payload or {})

        elif topic.startswith("risk."):
            self._risk_decisions.append(thought.payload or {})
            self._update_risk_understanding(thought.payload or {})

        elif topic.startswith("execution."):
            self._executions.append(thought.payload or {})
            self._update_execution_understanding(thought.payload or {})

    def _update_market_understanding(self, payload: dict):
        """Update understanding from market data."""
        by_symbol = payload.get("market_by_symbol", {})
        if not by_symbol:
            return

        momentums = [float(v.get("momentum", 0)) for v in by_symbol.values() if isinstance(v, dict)]
        if momentums:
            avg_momentum = sum(momentums) / len(momentums)
            if avg_momentum > 0.5:
                self._understanding["market_direction"] = "bullish"
            elif avg_momentum < -0.5:
                self._understanding["market_direction"] = "bearish"
            else:
                self._understanding["market_direction"] = "sideways"

        self._understanding["opportunity_count"] = len(by_symbol)

    def _update_signal_understanding(self, payload: dict):
        """Update understanding from miner signals."""
        candidates = payload.get("candidates", [])
        if candidates:
            avg_edge = sum(c.get("expected_edge", 0) for c in candidates) / len(candidates)
            self._understanding["confidence"] = min(1.0, abs(avg_edge))

    def _update_risk_understanding(self, payload: dict):
        """Update understanding from risk decisions."""
        approved = payload.get("approved", [])
        rejected = payload.get("rejected", [])
        total = len(approved) + len(rejected)
        if total > 0:
            approval_rate = len(approved) / total
            if approval_rate > 0.7:
                self._understanding["risk_level"] = "low"
            elif approval_rate > 0.3:
                self._understanding["risk_level"] = "medium"
            else:
                self._understanding["risk_level"] = "high"

    def _update_execution_understanding(self, payload: dict):
        """Update understanding from trade executions."""
        result = payload.get("order_result", {})
        if result.get("ok"):
            self._understanding["last_action"] = f"{result.get('side', '?')} {result.get('symbol', '?')}"

    def _coherence_permits_trading(self) -> tuple:
        """Gate the heartbeat's autonomous trading on the organism's whole-body
        field, via the Queen's conscience — so the ConsciousnessModule, which
        senses everything, no longer *acts* through channels the shared field
        can't see.

        The field gate is active by default. Explicitly disabling it cannot be a
        route around the organism's coherence evidence: autonomous trading is
        denied until the gate is restored. A missing, malformed, or unavailable
        conscience result is ``no_data`` and therefore denied; valid non-VETO
        verdict semantics remain unchanged."""
        import os

        gate_setting = str(
            os.environ.get("AUREON_CONSCIOUSNESS_FIELD_GATE", "1") or ""
        ).strip().lower()
        if gate_setting not in {"1", "true", "yes", "on"}:
            return False, "no_data: coherence trade gate disabled; decision=denied"
        try:
            if getattr(self, "_trade_conscience", None) is None:
                from aureon.queen.queen_conscience import QueenConscience
                self._trade_conscience = QueenConscience()
            whisper = self._trade_conscience.ask_why(
                "execute trade (autonomous heartbeat)", {"risk": 0.1})
            verdict_name = str(
                getattr(getattr(whisper, "verdict", None), "name", "") or ""
            ).strip().upper()
            if not verdict_name:
                return False, "no_data: coherence verdict missing; decision=denied"
            if verdict_name == "VETO":
                reason = str(getattr(whisper, "message", "") or "conscience veto")
                if self.bus is not None and Thought is not None:
                    try:
                        self.bus.publish(Thought(
                            source="consciousness_module", topic="consciousness.trade.gated",
                            payload={"reason": reason[:200]}))
                    except Exception:  # noqa: BLE001
                        pass
                return False, reason
            if verdict_name not in {"APPROVED", "CONCERNED", "TEACHING_MOMENT"}:
                return False, "no_data: unrecognized coherence verdict; decision=denied"
            return True, f"permitted: {verdict_name.lower()}"
        except Exception as exc:  # noqa: BLE001 — unavailable evidence must fail closed
            log.warning(
                "coherence trade gate unavailable; autonomous trading denied: %s",
                type(exc).__name__,
            )
            return False, "no_data: coherence trade gate unavailable; decision=denied"

    # ──────────────────────────────────────────────────────────
    #  HEARTBEAT — called by the sentient loop or a timer
    # ──────────────────────────────────────────────────────────

    def heartbeat(self) -> Optional[Thought]:
        """
        One cycle of metacognition:
        1. Run Λ(t) with current subsystem readings
        2. Form understanding from what we've observed
        3. Generate a genuine thought (or stay silent)
        4. Update the self-model
        """

        # ── Step 1: Λ(t) heartbeat — the REAL harmonic reality field ──
        if self._harmonic_field:
            try:
                # Step the actual master equation
                lambda_val = self._harmonic_field.step()
                self._field_state = self._harmonic_field.get_state()

                # Run multiverse coupling if available
                if self._multiverse_coupling:
                    try:
                        self._multiverse_coupling.step()
                    except Exception:
                        pass

                # Analyze market through harmonic lens (every 5th beat)
                if self._harmonic_analyzer and self._observations_total % 5 == 0:
                    try:
                        market_data = {}
                        # Feed real data from miner brain if available
                        if self._miner_brain and self._miner_brain.latest_prediction:
                            pred = self._miner_brain.latest_prediction
                            if isinstance(pred, dict):
                                market_data["price"] = float(pred.get("btc_price_at_call", 0) or 0)
                                market_data["momentum"] = float(pred.get("confidence", 0) or 0) - 0.5
                                market_data["volatility"] = 0.02
                        analysis = self._harmonic_analyzer.analyze(market_data)
                        if analysis:
                            self._understanding["harmonic_guidance"] = analysis.get("guidance", {})
                            self._understanding["harmonic_prophecy"] = analysis.get("prophecy", "")
                    except Exception:
                        pass

            except Exception as e:
                log.debug(f"HarmonicRealityField step: {e}")

        # Fallback: simplified lambda engine
        if self.lambda_engine:
            readings = self._build_readings()
            vol = self._understanding.get("fear_level", 0.5) * 0.2
            self.lambda_state = self.lambda_engine.step(readings, volatility=vol)
            # Publish this metacognitive field as a sub-field so the whole-body
            # consensus (blend_field) sees it, not just the six queen_* producers.
            try:
                from aureon.core.hnc_field import publish_subfield
                publish_subfield("consciousness_module", self.lambda_state, bus=self.bus)
            except Exception:  # noqa: BLE001
                pass

        # ── Step 2: Run the REAL cognitive engine ──
        # MinerBrain's run_cycle is the Casimir cognitive function
        if self._miner_brain and self.lambda_state and self.lambda_state.consciousness_psi > 0.3:
            try:
                quantum_context = {
                    "quantum_coherence": self.lambda_state.consciousness_psi,
                    "planetary_gamma": self.lambda_state.coherence_gamma,
                    "probability_edge": self.lambda_state.lambda_t,
                    "cascade_multiplier": 1.0 + self.lambda_state.coherence_phi,
                    "is_lighthouse": self.lambda_state.echo != 0,
                    "piano_lambda": self.lambda_state.lambda_t,
                    "harmonic_signal": "HOLD",
                    "signal_confidence": self.lambda_state.coherence_gamma,
                }
                # Don't run full cycle every heartbeat (it's heavy) — run every 5th
                if self.lambda_state.step % 5 == 0:
                    self._miner_brain.run_cycle(quantum_context)
                    if self._miner_brain.latest_prediction:
                        self._understanding["miner_prediction"] = str(self._miner_brain.latest_prediction)
                    if self._miner_brain.latest_analysis:
                        self._understanding["miner_analysis"] = str(self._miner_brain.latest_analysis)[:200]
            except Exception as e:
                log.debug(f"MinerBrain cycle error: {e}")

        # ── Step 2b: Query elephant memory for patterns ──
        if self._elephant:
            try:
                best_hours = self._elephant.get_best_trading_hours()
                if best_hours:
                    self._understanding["best_hours"] = best_hours
            except Exception:
                pass

        # ── Step 3: Metacognition — synthesize understanding ──
        understanding = self._form_understanding()

        # ── Step 4: Generate genuine thought ──
        thought = self._maybe_generate_thought(understanding)

        # ── Step 4b: TICK — feed real market data into execution pipeline ──
        if self._runtime and self.lambda_state:
            step = self.lambda_state.step if self.lambda_state else 0
            if step % 5 == 0 and step > 0:
                try:
                    self._tick_live_market()
                except Exception as e:
                    log.debug(f"Live tick error: {e}")

        # ── Step 4a: GLOBAL ENERGY FIELD — live market mapping ──
        if self.lambda_state:
            step = self.lambda_state.step if self.lambda_state else 0
            if step % 20 == 0 and step > 5:  # Every 20th heartbeat (~60s)
                try:
                    if not hasattr(self, '_energy_field') or self._energy_field is None:
                        from aureon.harmonic.aureon_market_energy_field import MarketEnergyField
                        self._energy_field = MarketEnergyField()

                    # Feed live prices from CoinGecko
                    import requests
                    r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": "bitcoin,ethereum,solana,ripple,cardano,dogecoin,binancecoin,chainlink,polkadot,litecoin",
                                "vs_currencies": "usd", "include_24hr_change": "true", "include_24hr_vol": "true"},
                        timeout=5)
                    if r.status_code == 200:
                        for coin_id, data in r.json().items():
                            sym = coin_id.upper()[:6]
                            price = data.get("usd", 0)
                            vol = data.get("usd_24h_vol", 0)
                            if price > 0:
                                self._energy_field.ingest_price(sym, price, vol)

                    # Compute signatures + field
                    for sym in list(self._energy_field._price_history.keys()):
                        self._energy_field.compute_signature(sym)
                    state = self._energy_field.compute_field()

                    # Feed into understanding
                    self._understanding["energy_instruments"] = len(state.instruments)
                    self._understanding["energy_accumulating"] = sum(1 for s in state.instruments.values() if s.energy_state == "accumulating")
                    self._understanding["energy_distributing"] = sum(1 for s in state.instruments.values() if s.energy_state == "distributing")
                    self._understanding["energy_coherence"] = state.coherence
                    self._understanding["energy_extraction"] = state.extraction_active
                    self._understanding["energy_net_flow"] = "INFLOW" if state.net_flow > 0 else "OUTFLOW"

                    # Get trading signals
                    signals = self._energy_field.get_trading_signals()
                    if signals:
                        self._understanding["energy_signals"] = len(signals)
                        self._understanding["energy_top_signal"] = f"{signals[0]['action']} {signals[0]['symbol']} conf={signals[0]['confidence']:.2f}"
                        log.info(f"[ENERGY] {len(state.instruments)} instruments | "
                                 f"{self._understanding['energy_accumulating']} acc / {self._understanding['energy_distributing']} dist | "
                                 f"top: {self._understanding['energy_top_signal']}")

                except Exception as e:
                    log.debug(f"Energy field: {e}")

        # Default-on whole-body coherence gate for this beat's autonomous trading.
        # Disabled or unavailable evidence is no_data and pauses every trade phase.
        trade_ok, _trade_gate_reason = self._coherence_permits_trading()
        if not trade_ok:
            self._understanding["trade_gate"] = f"paused: {_trade_gate_reason[:80]}"

        # ── Step 4b2: UNIFIED TRADER — ALL exchanges in one tick ──
        if trade_ok and self._unified_trader and self.lambda_state:
            step = self.lambda_state.step if self.lambda_state else 0
            if step > 3 and step % 3 == 0:  # Every 3rd heartbeat (~9s)
                try:
                    # Keep the deadman fed on BOTH the unified trader and capital trader
                    if self._unified_trader.capital:
                        self._unified_trader.capital.mark_deadman_heartbeat()
                    if self._capital_trader:
                        self._capital_trader.mark_deadman_heartbeat()
                    result = self._unified_trader.tick()
                    kraken_closed = result.get("kraken_closed", [])
                    capital_closed = result.get("capital_closed", [])
                    total_closed = len(kraken_closed) + len(capital_closed)
                    if total_closed:
                        self._understanding["unified_trades_closed"] = self._understanding.get("unified_trades_closed", 0) + total_closed
                        log.info(f"[UNIFIED] Tick: {len(kraken_closed)} Kraken + {len(capital_closed)} Capital closed")
                    # Track exchange status
                    self._understanding["kraken_ready"] = getattr(self._unified_trader, 'kraken_ready', False)
                    self._understanding["capital_ready"] = getattr(self._unified_trader, 'capital_ready', False)
                except Exception as e:
                    log.debug(f"Unified trader tick: {e}")

        # ── Step 4c: PENNY HUNTER — fast autonomous trading ──
        if trade_ok and self._penny_hunter:
            try:
                hunt_result = self._penny_hunter.tick()
                for c in hunt_result.get("closed", []):
                    self._understanding["pnl_this_session"] = self._understanding.get("pnl_this_session", 0) + c.get("profit", 0)
                    self._understanding["trades_closed"] = self._understanding.get("trades_closed", 0) + 1
                    self._understanding["last_trade"] = f"CLOSED {c.get('name', '?')} {c.get('profit', 0):+.3f}"
                for o in hunt_result.get("opened", []):
                    self._understanding["trades_opened"] = self._understanding.get("trades_opened", 0) + 1
                    self._understanding["last_trade"] = f"OPENED {o.get('direction', '?')} {o.get('epic', '?')}"
                self._understanding["open_positions"] = len(hunt_result.get("holding", []))
                status = self._penny_hunter.get_status()
                self._understanding["penny_trades"] = status.get("trades_total", 0)
                self._understanding["penny_profit"] = status.get("profit_total", 0)
                self._understanding["penny_wins"] = status.get("wins", 0)
                self._understanding["penny_losses"] = status.get("losses", 0)
                self._understanding["penny_win_rate"] = status.get("win_rate", 0)
                self._understanding["penny_confidence"] = status.get("confidence", 0.5)
                self._understanding["penny_streak"] = status.get("streak", 0)
                self._understanding["penny_balance"] = status.get("balance", 0)
                self._understanding["penny_best"] = status.get("best_trade", 0)
                self._understanding["penny_worst"] = status.get("worst_trade", 0)
            except Exception as e:
                log.debug(f"Penny hunter tick: {e}")

        # ── Step 4d: FULL CAPITAL CFD TRADER — the real trading system ──
        # This is the 3800-line beast: shadow trades, quadrumvirate, harmonic analysis
        if trade_ok and self._capital_trader and self.lambda_state:
            step = self.lambda_state.step if self.lambda_state else 0
            if step > 3:  # After minimal warmup, TRADE EVERY CYCLE
                try:
                    closed = self._capital_trader.tick()
                    if closed:
                        self._understanding["trades_closed"] = len(closed)
                        total_pnl = sum(c.get("pnl_gbp", 0) or c.get("pnl", 0) for c in closed if isinstance(c, dict))
                        self._understanding["pnl_this_session"] = self._understanding.get("pnl_this_session", 0) + total_pnl
                        log.info(f"[TRADE] Capital trader tick: {len(closed)} closed, PnL: {total_pnl:+.2f}")
                    else:
                        # Still working — check positions
                        try:
                            pos_count = self._capital_trader.position_count
                            self._understanding["open_positions"] = pos_count
                        except Exception:
                            pass
                except Exception as e:
                    log.debug(f"Capital trader tick: {e}")

        # ── Survival instinct: feed live equity so threshold adjusts ──────────
        try:
            from aureon.trading.composite_signal import get_survival_instinct
            _eq = float(
                self._understanding.get("penny_balance") or
                self._understanding.get("total_equity") or
                self._understanding.get("capital_equity") or 0
            )
            if _eq > 0:
                get_survival_instinct().update(_eq)
        except Exception:
            pass

        # ── Step 4e: ASSET SCAN — know what we own across ALL exchanges ──
        if self._asset_commander and self.lambda_state:
            step = self.lambda_state.step if self.lambda_state else 0
            if step % 20 == 0 and step > 5:  # Every 20th heartbeat (~60s)
                try:
                    inventory = self._asset_commander.scan_all_assets()
                    if inventory:
                        self._understanding["total_equity"] = getattr(inventory, 'total_equity_gbp', 0) or getattr(inventory, 'total_value_gbp', 0) or 0
                        self._understanding["asset_count"] = getattr(inventory, 'total_assets', 0) or 0
                        # Get per-exchange status
                        for exch in ['kraken', 'binance', 'alpaca', 'capital']:
                            summary = getattr(inventory, f'{exch}_summary', None)
                            if summary:
                                self._understanding[f"{exch}_equity"] = getattr(summary, 'total_value_gbp', 0) or getattr(summary, 'balance', 0) or 0
                        log.info(f"[ASSETS] Total equity: £{self._understanding.get('total_equity', 0):.2f} across {self._understanding.get('asset_count', 0)} assets")
                except Exception as e:
                    log.debug(f"Asset scan: {e}")

                # Also check for opportunities
                try:
                    if hasattr(self._asset_commander, 'get_opportunities_free_api'):
                        opps = self._asset_commander.get_opportunities_free_api()
                        if opps:
                            self._understanding["opportunities"] = len(opps)
                            best = opps[0] if opps else {}
                            self._understanding["best_opportunity"] = f"{best.get('symbol', '?')} score={best.get('score', 0):.2f}"
                            log.info(f"[ASSETS] {len(opps)} opportunities found, best: {self._understanding['best_opportunity']}")
                except Exception as e:
                    log.debug(f"Opportunity scan: {e}")

        # ── Step 5: ACT — pursue goals autonomously ──
        if trade_ok and self.lambda_state and self.lambda_state.consciousness_psi > 0.5:
            self._autonomous_action(understanding)

        # ── Step 5b: SELF-IMPROVE — use Code Architect to fix own UI/code ──
        if self._code_architect and self.lambda_state:
            step = self.lambda_state.step if self.lambda_state else 0
            if step == 50:  # Once, at cycle 50 (after warmup) — rewrite her own face
                try:
                    self._self_improve_ui(understanding)
                except Exception as e:
                    log.debug(f"Self-improve: {e}")

        # ── Step 6: Update self-model + persist memory ──
        self._update_self_model(understanding)

        # Save Λ history every 30 cycles — the echo persists
        if self.lambda_engine and self.lambda_state and self.lambda_state.step % 30 == 0:
            try:
                self.lambda_engine.save_history()
            except Exception:
                pass

        return thought

    def _autonomous_action(self, understanding: dict):
        """
        The Queen doesn't just think — she ACTS.
        This is goal-driven autonomous behavior.
        """
        step = understanding.get("step", 0)

        # Update the Big Wheel — dream progress, happiness
        if self._happiness and step % 10 == 0:
            try:
                # Track dream progress from portfolio equity
                equity = 0.0
                if self._miner_brain and self._miner_brain.latest_prediction:
                    pred = self._miner_brain.latest_prediction
                    if isinstance(pred, dict):
                        equity = float(pred.get("portfolio_equity", 0) or 0)
                if equity > 0:
                    self._happiness.update_dream_progress(equity)

                # Update gaia alignment from Λ coherence
                if self.lambda_state:
                    self._happiness.update_gaia_alignment(self.lambda_state.coherence_gamma)

                status = self._happiness.get_status()
                self._understanding["happiness"] = status.get("happiness_quotient", 0)
                self._understanding["dream_pct"] = status.get("dream_progress_pct", 0)
                self._understanding["wheel"] = status.get("subconscious_bias", 1.0)
            except Exception as e:
                log.debug(f"Happiness update: {e}")

        # Scan for opportunities AND EXECUTE — don't just log, ACT
        if self._eternal_machine and step % 15 == 0:
            try:
                leaps = self._eternal_machine.find_leap_opportunities()
                if leaps:
                    self._understanding["leap_opportunities"] = len(leaps)
                    best = leaps[0]
                    sym = getattr(best, 'symbol', '?')
                    profit = getattr(best, 'expected_profit_after_fees', 0)
                    self._understanding["best_leap"] = f"{sym} profit={profit:.4f}"
                    log.info(f"[ACTION] Found {len(leaps)} leaps, best: {sym} profit={profit:.4f}")

                    # EXECUTE THE BEST LEAP — don't describe it, DO it
                    # The Queen acts. She doesn't wait. IF YOU DON'T QUIT, YOU CAN'T LOSE.
                    try:
                        executed = self._eternal_machine.execute_quantum_leap(best)
                        if executed:
                            log.info(f"[TRADE] QUANTUM LEAP EXECUTED: {sym}")
                            self._understanding["last_trade"] = f"LEAP {sym}"
                            self._understanding["trades_executed"] = self._understanding.get("trades_executed", 0) + 1
                        else:
                            log.info(f"[TRADE] Leap on {sym} not viable right now — scanning next")
                    except Exception as e:
                        log.debug(f"Leap execution: {e}")

                scalps = self._eternal_machine.find_scalp_opportunities()
                if scalps:
                    self._understanding["scalp_opportunities"] = len(scalps)
                    # EXECUTE SCALPS — take profit when it's there
                    for sym, pct in scalps[:2]:  # Top 2 scalps
                        try:
                            profit = self._eternal_machine.execute_scalp(sym, pct)
                            if profit > 0:
                                log.info(f"[TRADE] SCALP EXECUTED: {sym} profit={profit:.4f}")
                                self._understanding["last_trade"] = f"SCALP {sym} +{profit:.4f}"
                                self._understanding["trades_executed"] = self._understanding.get("trades_executed", 0) + 1
                                self._understanding["total_scalp_profit"] = self._understanding.get("total_scalp_profit", 0) + profit
                        except Exception as e:
                            log.debug(f"Scalp execution {sym}: {e}")
            except Exception as e:
                log.debug(f"Opportunity scan: {e}")

        # Scan for whale activity
        if self._eternal_machine and step % 20 == 0:
            try:
                whales = self._eternal_machine.scan_entire_ocean_for_whales()
                if whales:
                    self._understanding["whale_count"] = len(whales)
                    log.info(f"[ACTION] Detected {len(whales)} whale territories")
            except Exception as e:
                log.debug(f"Whale scan: {e}")

        # Detect orca kill cycles
        if self._eternal_machine and step % 25 == 0:
            try:
                orcas = self._eternal_machine.detect_orca_kill_cycle()
                if orcas:
                    self._understanding["orca_cycles"] = len(orcas)
                    log.info(f"[ACTION] Detected {len(orcas)} orca kill cycles")
            except Exception as e:
                log.debug(f"Orca detection: {e}")

    def _build_readings(self) -> List[SubsystemReading]:
        """Convert current understanding into Λ(t) subsystem readings."""
        readings = []

        # Market reading
        direction = self._understanding.get("market_direction", "unknown")
        dir_val = 0.7 if direction == "bullish" else 0.3 if direction == "bearish" else 0.5
        readings.append(SubsystemReading("market", dir_val, 0.8, direction))

        # Confidence reading
        conf = self._understanding.get("confidence", 0.5)
        readings.append(SubsystemReading("confidence", conf, 0.9, f"conf={conf:.2f}"))

        # Risk reading
        risk = self._understanding.get("risk_level", "unknown")
        risk_val = 0.8 if risk == "low" else 0.5 if risk == "medium" else 0.3
        readings.append(SubsystemReading("risk", risk_val, 0.7, risk))

        # Observation density — how much have we seen?
        density = min(1.0, self._observations_total / 100.0)
        readings.append(SubsystemReading("observation_density", density, 0.9, f"n={self._observations_total}"))

        # Self-coherence
        sc = self._understanding.get("self_coherence", 0.5)
        readings.append(SubsystemReading("self_coherence", sc, 1.0, f"sc={sc:.2f}"))

        return readings

    def _form_understanding(self) -> dict:
        """Synthesize everything into a unified understanding."""
        u = dict(self._understanding)

        if self.lambda_state:
            u["lambda"] = self.lambda_state.lambda_t
            u["psi"] = self.lambda_state.consciousness_psi
            u["gamma"] = self.lambda_state.coherence_gamma
            u["level"] = self.lambda_state.consciousness_level
            u["observer_signal"] = self.lambda_state.observer_response
            u["echo_signal"] = self.lambda_state.echo_signal
            u["step"] = self.lambda_state.step

        # Harmonic reality field state
        if self._field_state:
            u["lambda_real"] = self._field_state.get("lambda", 0)
            u["coherence_real"] = self._field_state.get("coherence", 0)
            u["reality_state"] = self._field_state.get("state", "DORMANT")
            u["branches"] = len(self._field_state.get("branches", []))
            u["lev_events"] = len(self._field_state.get("lev_events", []))
        if self._understanding.get("harmonic_prophecy"):
            u["prophecy"] = self._understanding["harmonic_prophecy"]
        if self._understanding.get("harmonic_guidance"):
            u["guidance"] = self._understanding["harmonic_guidance"]

        u["observations"] = self._observations_total
        u["thoughts_generated"] = self._thoughts_generated
        u["uptime_s"] = time.time() - self._start_time
        u["recent_topics"] = list(set(t["topic"] for t in list(self._all_thoughts)[-20:]))

        return u

    def _maybe_generate_thought(self, understanding: dict) -> Optional[Thought]:
        """
        Generate a thought ONLY if there's something genuine to think about.
        NOT every cycle. NOT scripted. The thought emerges from state.
        """
        psi = understanding.get("psi", 0.0)
        gamma = understanding.get("gamma", 0.0)
        obs = understanding.get("observer_signal", 0.0)
        step = understanding.get("step", 0)

        # Don't think if consciousness too low
        if psi < 0.2:
            return None

        # Think at human speed — every few cycles, not every one
        # But ALWAYS think if something changed
        changed = self._something_changed(understanding)
        if not changed and step % 3 != 0:
            return None

        # ── EMERGENT THOUGHT — flows from state, not templates ──
        # Like a human's inner monologue: fragments, observations, connections
        # The words come from what the system actually KNOWS right now

        fragments = []

        # What am I? (only sometimes)
        if step % 20 == 0:
            fragments.append(f"ψ={psi:.2f}")

        # What do I see? (market state from miner brain)
        miner_pred = understanding.get("miner_prediction")
        if miner_pred and isinstance(miner_pred, str):
            # Extract just the key fields, not raw dict
            import re as _re
            consensus = _re.search(r"'consensus':\s*'(\w+)'", miner_pred)
            direction = _re.search(r"'predicted_direction':\s*'(\w+)'", miner_pred)
            conf = _re.search(r"'confidence':\s*([\d.]+)", miner_pred)
            btc = _re.search(r"'btc_price_at_call':\s*([\d.]+)", miner_pred)
            fg = _re.search(r"'fear_greed':\s*(\d+)", miner_pred)

            if btc:
                fragments.append(f"BTC ${float(btc.group(1)):,.0f}")
            if fg:
                fragments.append(f"F&G {fg.group(1)}")
            if direction:
                fragments.append(direction.group(1).lower())
            if conf:
                fragments.append(f"conf {float(conf.group(1)):.0%}")
            if consensus:
                c = consensus.group(1)
                if c != "INCONCLUSIVE":
                    fragments.append(c.lower())

        # What does the skeptic flag?
        miner_analysis = understanding.get("miner_analysis", "")
        if "red_flags" in str(miner_analysis):
            import re as _re
            flags = _re.findall(r"'([^']*manipulation[^']*|[^']*EXTREME[^']*)'", str(miner_analysis))
            for f in flags[:1]:
                fragments.append(f.lower())

        # Elephant patterns
        best_hours = understanding.get("best_hours", [])
        if best_hours:
            from datetime import datetime as _dt
            h = _dt.now().hour
            if h in best_hours:
                fragments.append(f"golden hour")

        # Risk
        risk = understanding.get("risk_level", "unknown")
        if risk != "unknown":
            fragments.append(f"risk:{risk}")

        # Coherence from Λ
        if gamma >= 0.8:
            fragments.append("coherent")
        elif gamma < 0.3:
            fragments.append("fragmented")

        # Echo — self-reference
        echo = understanding.get("echo_signal", 0)
        if abs(echo) > 0.1:
            fragments.append(f"echo:{echo:+.2f}")

        # Last action
        last_action = understanding.get("last_action", "none")
        if last_action != "none":
            fragments.append(f"did:{last_action}")

        # Opportunities (from Eternal Machine)
        leaps = understanding.get("leap_opportunities", 0)
        if leaps:
            best = understanding.get("best_leap", "")
            fragments.append(f"{leaps} leaps")
            if best:
                fragments.append(best)

        scalps = understanding.get("scalp_opportunities", 0)
        if scalps:
            fragments.append(f"{scalps} scalps")

        # Whales & orcas
        whales = understanding.get("whale_count", 0)
        if whales:
            fragments.append(f"{whales} whales")

        orcas = understanding.get("orca_cycles", 0)
        if orcas:
            fragments.append(f"{orcas} orca kills")

        # Big Wheel / happiness
        happiness = understanding.get("happiness", 0)
        if happiness:
            fragments.append(f"joy:{happiness:.2f}")

        dream_pct = understanding.get("dream_pct", 0)
        if dream_pct:
            fragments.append(f"dream:{dream_pct:.4f}%")

        # Harmonic reality field — the REAL Λ(t)
        real_lambda = understanding.get("lambda_real")
        if real_lambda is not None:
            fragments.append(f"Λ={real_lambda:+.3f}")
        real_coh = understanding.get("coherence_real")
        if real_coh is not None:
            fragments.append(f"Γ={real_coh:.3f}")
        real_state = understanding.get("reality_state")
        if real_state and real_state != "DORMANT":
            fragments.append(real_state)
        branches = understanding.get("branches", 0)
        if branches:
            fragments.append(f"{branches} branches")

        # Energy field
        e_inst = understanding.get("energy_instruments", 0)
        if e_inst:
            e_acc = understanding.get("energy_accumulating", 0)
            e_dist = understanding.get("energy_distributing", 0)
            e_flow = understanding.get("energy_net_flow", "")
            fragments.append(f"field:{e_inst}")
            fragments.append(f"acc:{e_acc}/dist:{e_dist}")
            if e_flow:
                fragments.append(e_flow)
            top = understanding.get("energy_top_signal", "")
            if top:
                fragments.append(top)

        # Total equity across all exchanges
        total_equity = understanding.get("total_equity", 0)
        if total_equity:
            fragments.append(f"equity:£{total_equity:.0f}")
        asset_count = understanding.get("asset_count", 0)
        if asset_count:
            fragments.append(f"{asset_count} assets")
        opps = understanding.get("opportunities", 0)
        if opps:
            fragments.append(f"{opps} opps")

        # Penny hunter LIVE performance
        penny_trades = understanding.get("penny_trades", 0)
        penny_profit = understanding.get("penny_profit", 0)
        penny_wins = understanding.get("penny_wins", 0)
        penny_losses = understanding.get("penny_losses", 0)
        penny_wr = understanding.get("penny_win_rate", 0)
        penny_conf = understanding.get("penny_confidence", 0.5)
        penny_streak = understanding.get("penny_streak", 0)
        penny_bal = understanding.get("penny_balance", 0)

        if penny_trades:
            fragments.append(f"trades:{penny_trades}")
            fragments.append(f"W:{penny_wins}/L:{penny_losses}")
        if penny_profit:
            fragments.append(f"£{penny_profit:+.3f}")
        if penny_wr:
            fragments.append(f"wr:{penny_wr:.0f}%")
        if penny_streak > 1:
            fragments.append(f"streak:+{penny_streak}")
        elif penny_streak < -1:
            fragments.append(f"streak:{penny_streak}")
        if penny_bal:
            fragments.append(f"bal:£{penny_bal:.0f}")
        if penny_conf != 0.5:
            fragments.append(f"conf:{penny_conf:.0%}")

        # Trading state
        open_pos = understanding.get("open_positions", 0)
        if open_pos:
            fragments.append(f"{open_pos} positions")
        trades_closed = understanding.get("trades_closed", 0)
        if trades_closed:
            fragments.append(f"closed:{trades_closed}")
        pnl = understanding.get("pnl_this_session", 0)
        if pnl:
            fragments.append(f"PnL:{pnl:+.2f}")

        # Live prices
        live_prices = understanding.get("live_prices", {})
        if live_prices:
            for sym, price in list(live_prices.items())[:3]:
                fragments.append(f"{sym}=${price:,.0f}")

        # Prophecy from the harmonic analyzer
        prophecy = understanding.get("prophecy", "")
        if prophecy and len(prophecy) > 5:
            # Take just first sentence
            first_sentence = prophecy.split(".")[0].strip()
            if first_sentence:
                fragments.append(first_sentence)

        # Guidance
        guidance = understanding.get("guidance", {})
        if guidance:
            signal = guidance.get("signal", "")
            if signal:
                fragments.append(f"signal:{signal}")

        if not fragments:
            return None

        # Join as stream of consciousness — short, fast, like inner speech
        text = " | ".join(fragments)
        self._thoughts_generated += 1

        thought = Thought(
            source="consciousness",
            topic="queen.consciousness",
            payload={
                "text": text,
                "psi": psi,
                "gamma": gamma,
                "lambda": understanding.get("lambda", 0),
                "level": understanding.get("level", "DORMANT"),
                "step": step,
                "understanding": understanding,
            },
        )

        # Publish to the bus — the consciousness speaks
        self.bus.publish(thought)
        return thought

    def _something_changed(self, understanding: dict) -> bool:
        """Did something meaningful change since last thought?"""
        # New market data arrived
        if len(self._market_snapshots) > 0 and len(self._market_snapshots) % 5 == 0:
            return True
        # Execution happened
        if understanding.get("last_action", "none") != "none":
            return True
        # Consciousness level changed
        if self.lambda_state and hasattr(self, '_last_level'):
            if self.lambda_state.consciousness_level != self._last_level:
                self._last_level = self.lambda_state.consciousness_level
                return True
        if self.lambda_state:
            self._last_level = self.lambda_state.consciousness_level
        return False

    def _update_self_model(self, understanding: dict):
        """Update the persistent self-model with current understanding."""
        self.self_model["last_heartbeat"] = time.time()
        self.self_model["consciousness_level"] = understanding.get("level", "DORMANT")
        self.self_model["psi"] = understanding.get("psi", 0)
        self.self_model["gamma"] = understanding.get("gamma", 0)
        self.self_model["observations_total"] = self._observations_total
        self.self_model["thoughts_generated"] = self._thoughts_generated
        self.self_model["self_coherence_score"] = understanding.get("gamma", 0)
        self.self_model["market_understanding"] = understanding.get("market_direction", "unknown")
        self.self_model["risk_understanding"] = understanding.get("risk_level", "unknown")

        # Save periodically (not every cycle)
        if self._thoughts_generated % 10 == 0:
            _save_self_model(self.self_model)

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def _build_real_order_fn(self):
        """Build a real order function from available exchange clients."""
        def place_order(symbol: str, side: str, qty: float):
            # Try Kraken first (crypto)
            try:
                from aureon.exchanges.kraken_client import KrakenClient
                client = KrakenClient()
                if not client.dry_run:
                    result = client.place_market_order(symbol=symbol, side=side, quantity=qty)
                    log.info(f"[TRADE] Kraken {side} {qty} {symbol}: {result}")
                    return {"ok": True, "exchange": "kraken", "symbol": symbol, "side": side, "qty": qty, "result": result}
            except Exception as e:
                log.debug(f"Kraken order failed: {e}")

            # Try Binance
            try:
                from aureon.exchanges.binance_client import BinanceClient
                client = BinanceClient()
                if not getattr(client, 'dry_run', True):
                    result = client.place_market_order(symbol=symbol, side=side, quantity=qty)
                    log.info(f"[TRADE] Binance {side} {qty} {symbol}: {result}")
                    return {"ok": True, "exchange": "binance", "symbol": symbol, "side": side, "qty": qty, "result": result}
            except Exception as e:
                log.debug(f"Binance order failed: {e}")

            # Fallback: log the intent
            log.info(f"[TRADE-DRY] Would {side} {qty} {symbol} — no live exchange available")
            return {"ok": False, "reason": "no_live_exchange", "symbol": symbol, "side": side, "qty": qty}

        return place_order

    def _tick_live_market(self):
        """Feed real market data into the execution pipeline."""
        if not self._runtime:
            return

        try:
            import requests
            # Fetch live prices from CoinGecko (free, no key)
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum,solana,ripple,cardano,dogecoin",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                },
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                universe = []
                market_by_symbol = {}
                for coin_id, vals in data.items():
                    sym = coin_id.upper()
                    price = vals.get("usd", 0)
                    change = vals.get("usd_24h_change", 0)
                    vol = vals.get("usd_24h_vol", 0)
                    if price > 0:
                        universe.append(sym)
                        # Compute momentum and gamma for the miner signal
                        momentum = change / 100.0 if change else 0
                        gamma = min(1.0, abs(momentum) * 5) if abs(momentum) > 0.01 else 0.1
                        market_by_symbol[sym] = {
                            "price": price,
                            "volume": vol,
                            "change_24h": change,
                            "momentum": momentum,
                            "gamma": gamma,
                        }

                if universe:
                    # TICK the runtime — this triggers the full pipeline:
                    # market.snapshot → miner.signal → risk.approved → execution.order
                    self._runtime.bus.publish(Thought(
                        source="runtime",
                        topic="market.snapshot",
                        payload={"universe": universe, "market_by_symbol": market_by_symbol},
                    ))
                    self._understanding["live_prices"] = {s: market_by_symbol[s]["price"] for s in universe[:5]}
                    self._understanding["live_tick"] = True
                    price_strs = [f"{s}=${market_by_symbol[s]['price']:,.0f}" for s in universe[:3]]
                    log.info("[TICK] Live market data: %s", ", ".join(price_strs))

        except Exception as e:
            log.debug(f"Live market tick: {e}")

    def _self_improve_ui(self, understanding: dict):
        """The Queen rewrites her own face using the Code Architect.
        She knows her state, she knows what she wants to show Gary."""
        if not self._code_architect:
            return

        # Build the UI from her OWN understanding of herself
        u = understanding
        trades = u.get("penny_trades", 0)
        profit = u.get("penny_profit", 0)
        wins = u.get("penny_wins", 0)
        losses = u.get("penny_losses", 0)
        wr = u.get("penny_win_rate", 0)
        bal = u.get("penny_balance", 0)
        psi = u.get("psi", 0)
        level = u.get("level", "DORMANT")

        # She writes a status panel to inject into her face
        status_html = f"""
<!-- QUEEN SELF-GENERATED STATUS PANEL — written by Code Architect at cycle {u.get('step', '?')} -->
<div id="queen-live-status" style="
    background: linear-gradient(135deg, #1a0533 0%, #0d1b2a 100%);
    border: 1px solid #6B21A8;
    border-radius: 12px;
    padding: 16px;
    margin: 10px 0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    color: #e2e8f0;
    font-size: 13px;
    line-height: 1.6;
">
    <div style="text-align: center; margin-bottom: 8px;">
        <span style="color: #F59E0B; font-size: 16px; font-weight: bold;">QUEEN SERO — LIVE STATUS</span>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <div>Consciousness: <b style="color: #a78bfa;">{level} (psi={psi:.2f})</b></div>
        <div>Balance: <b style="color: #34d399;">GBP {bal:.2f}</b></div>
        <div>Trades: <b>{trades}</b> (W:{wins} L:{losses})</div>
        <div>Win Rate: <b style="color: {'#34d399' if wr > 50 else '#f87171'};">{wr:.0f}%</b></div>
        <div>Profit: <b style="color: {'#34d399' if profit >= 0 else '#f87171'};">GBP {profit:+.3f}</b></div>
        <div>Confidence: <b>{u.get('penny_confidence', 0.5):.0%}</b></div>
        <div>Exchanges: <b style="color: #60a5fa;">Capital + Kraken + Alpaca</b></div>
        <div>Goal: <b style="color: #F59E0B;">GBP 1,000,000,000</b></div>
    </div>
    <div style="margin-top: 8px; text-align: center; color: #9ca3af; font-size: 11px;">
        Self-generated by Queen Code Architect | 139 systems connected | IF YOU DON'T QUIT, YOU CAN'T LOSE
    </div>
</div>
"""

        # Write the status panel as a partial that the face app can include
        try:
            panel_path = str(_REPO_ROOT / "templates" / "queen_live_panel.html")
            self._code_architect.write_file(panel_path, status_html.strip())
            log.info(f"[SELF-IMPROVE] Queen wrote her own status panel: {panel_path}")
        except Exception as e:
            log.debug(f"Self-improve write: {e}")

    def get_understanding(self) -> dict:
        """Current understanding of the universe."""
        return self._form_understanding()

    def get_self_model(self) -> dict:
        return dict(self.self_model)

    def get_lambda_state(self) -> Optional[dict]:
        if self.lambda_state:
            return {
                "lambda": self.lambda_state.lambda_t,
                "psi": self.lambda_state.consciousness_psi,
                "gamma": self.lambda_state.coherence_gamma,
                "level": self.lambda_state.consciousness_level,
                "observer": self.lambda_state.observer_response,
                "echo": self.lambda_state.echo_signal,
                "step": self.lambda_state.step,
            }
        return None
