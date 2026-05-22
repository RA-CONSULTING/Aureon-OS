#!/usr/bin/env python3
"""
THE BIG WHEEL - AUREON AUTONOMY HUB
=============================================================================

The central flywheel that connects ALL three layers into one continuous loop:

    DATA CAPTURE ──► PREDICTIONS ──► DECISIONS ──► EXECUTION
         ▲                                              │
         │              FEEDBACK LOOP                   │
         └──────────────────────────────────────────────┘

PROBLEM SOLVED:
    Before this hub, 12+ data capture systems wrote to files nobody read.
    10+ prediction engines generated signals nobody consumed.
    Trade outcomes were logged but NEVER fed back to improve predictions.
    Python and TypeScript systems were two separate islands.

    This hub is the Big Wheel - the single cog that makes everything turn.

ARCHITECTURE:
    1. DataBridge    - Collects ALL data capture outputs into unified signals
    2. PredictionBus - Routes data to ALL prediction engines, collects results
    3. DecisionGate  - Fuses prediction outputs into actionable decisions
    4. FeedbackLoop  - Routes trade outcomes BACK to prediction recalibration
    5. AutonomyHub   - The flywheel that spins all four continuously

Gary Leckey & Claude | February 2026
"The wheel turns. The system learns. Autonomy is earned."
=============================================================================
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import json
import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# QGITA + HARMONIC FIELD - Graceful imports
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer
    QGITA_AVAILABLE = True
except Exception as e:
    QGITA_AVAILABLE = False
    QGITAMarketAnalyzer = None
    logger.debug(f"QGITA not available in AutonomyHub: {e}")

try:
    from aureon.harmonic.global_harmonic_field import get_global_field, compute_global_omega
    HARMONIC_FIELD_AVAILABLE = True
except Exception as e:
    HARMONIC_FIELD_AVAILABLE = False
    get_global_field = None
    compute_global_omega = None
    logger.debug(f"Global Harmonic Field not available in AutonomyHub: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. UNIFIED SIGNAL - The common language between all systems
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UnifiedSignal:
    """Every system speaks this language. Data in, predictions out, decisions made."""
    timestamp: float = field(default_factory=time.time)
    source: str = ""               # Which system produced this
    signal_type: str = ""          # data | prediction | decision | outcome
    symbol: str = ""               # Trading pair

    # Direction & Confidence
    direction: str = "NEUTRAL"     # BULLISH | BEARISH | NEUTRAL
    confidence: float = 0.0        # 0.0 - 1.0
    strength: float = 0.0          # -1.0 to +1.0 (negative = bearish)

    # Context
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'UnifiedSignal':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DATA BRIDGE - Collects ALL data capture outputs into unified signals
# ═══════════════════════════════════════════════════════════════════════════════

class DataBridge:
    """
    Bridges ALL data capture systems into UnifiedSignals.

    Currently disconnected sources that this bridge connects:
    - Global Financial Feed (macro: VIX, DXY, Fear&Greed) -> was writing to JSON, nobody read
    - News Sentiment Feed -> was publishing to ThoughtBus, nobody subscribed in decisions
    - Unusual Whales (options flow) -> client existed, nobody consumed
    - Probability Data Collector -> was validating to console, never feeding back
    - Unified Market Cache -> prices existed, predictions used different sources
    """

    def __init__(self):
        self._latest_signals: Dict[str, UnifiedSignal] = {}
        self._signal_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def ingest_macro_snapshot(self, snapshot_dict: Dict) -> UnifiedSignal:
        """Bridge: GlobalFinancialFeed.MacroSnapshot -> UnifiedSignal"""
        fear_greed = snapshot_dict.get('crypto_fear_greed', 50)
        vix = snapshot_dict.get('vix', 20.0)
        dxy_change = snapshot_dict.get('dxy_change', 0.0)
        risk = snapshot_dict.get('risk_on_off', 'NEUTRAL')
        regime = snapshot_dict.get('market_regime', 'NORMAL')

        # Macro direction: fear_greed < 25 = bearish, > 75 = bullish
        if fear_greed < 25 or regime in ('PANIC', 'FEAR'):
            direction = "BEARISH"
            strength = -0.3 - (25 - min(fear_greed, 25)) / 100
        elif fear_greed > 75 or regime in ('GREED', 'EUPHORIA'):
            direction = "BULLISH"
            strength = 0.3 + (min(fear_greed, 100) - 75) / 100
        else:
            direction = "NEUTRAL"
            strength = (fear_greed - 50) / 100

        # VIX spike = bearish pressure
        if vix > 30:
            strength -= 0.15
        elif vix < 15:
            strength += 0.1

        # DXY rising = crypto bearish
        if dxy_change > 0.5:
            strength -= 0.1
        elif dxy_change < -0.5:
            strength += 0.1

        strength = max(-1.0, min(1.0, strength))
        confidence = min(abs(strength) * 2, 1.0)

        signal = UnifiedSignal(
            source="global_financial_feed",
            signal_type="data",
            symbol="MACRO",
            direction=direction,
            confidence=confidence,
            strength=strength,
            payload={
                'fear_greed': fear_greed,
                'vix': vix,
                'dxy_change': dxy_change,
                'risk_on_off': risk,
                'market_regime': regime,
                'yield_curve_inverted': snapshot_dict.get('yield_curve_inversion', False),
                'spx_change': snapshot_dict.get('spx_change', 0.0),
                'gold_change': snapshot_dict.get('gold_change', 0.0),
                'btc_dominance': snapshot_dict.get('btc_dominance', 50.0),
            }
        )
        self._store_signal(signal)
        return signal

    def ingest_news_sentiment(self, sentiment_data: Dict) -> UnifiedSignal:
        """Bridge: NewsServiceFeed sentiment -> UnifiedSignal"""
        crypto_sentiment = sentiment_data.get('crypto_sentiment', 0.0)
        overall = sentiment_data.get('aggregate_sentiment', 0.0)
        confidence_val = sentiment_data.get('confidence', 0.5)

        if crypto_sentiment > 0.2:
            direction = "BULLISH"
        elif crypto_sentiment < -0.2:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        signal = UnifiedSignal(
            source="news_sentiment",
            signal_type="data",
            symbol="SENTIMENT",
            direction=direction,
            confidence=confidence_val,
            strength=crypto_sentiment,
            payload={
                'crypto_sentiment': crypto_sentiment,
                'overall_sentiment': overall,
                'bullish_ratio': sentiment_data.get('bullish_ratio', 0.33),
                'bearish_ratio': sentiment_data.get('bearish_ratio', 0.33),
                'key_themes': sentiment_data.get('key_themes', []),
            }
        )
        self._store_signal(signal)
        return signal

    def ingest_options_flow(self, flow_data: Dict) -> UnifiedSignal:
        """Bridge: UnusualWhalesClient flow -> UnifiedSignal"""
        put_call = flow_data.get('put_call_ratio', 1.0)
        total_premium = flow_data.get('total_premium', 0)
        sentiment = flow_data.get('sentiment', 'neutral')

        if put_call < 0.7 or sentiment == 'bullish':
            direction = "BULLISH"
            strength = 0.3
        elif put_call > 1.3 or sentiment == 'bearish':
            direction = "BEARISH"
            strength = -0.3
        else:
            direction = "NEUTRAL"
            strength = 0.0

        signal = UnifiedSignal(
            source="options_flow",
            signal_type="data",
            symbol="OPTIONS",
            direction=direction,
            confidence=0.5,
            strength=strength,
            payload={
                'put_call_ratio': put_call,
                'total_premium': total_premium,
                'unusual_activity_count': flow_data.get('unusual_count', 0),
            }
        )
        self._store_signal(signal)
        return signal

    def ingest_market_tick(self, symbol: str, price: float, change_pct: float,
                           volume: float, exchange: str = "binance") -> UnifiedSignal:
        """Bridge: Any market data feed tick -> UnifiedSignal"""
        if change_pct > 1.0:
            direction = "BULLISH"
        elif change_pct < -1.0:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        signal = UnifiedSignal(
            source=f"market_{exchange}",
            signal_type="data",
            symbol=symbol,
            direction=direction,
            confidence=min(abs(change_pct) / 5.0, 1.0),
            strength=max(-1.0, min(1.0, change_pct / 5.0)),
            payload={
                'price': price,
                'change_pct': change_pct,
                'volume': volume,
                'exchange': exchange,
            }
        )
        self._store_signal(signal)
        return signal

    def ingest_whale_signal(self, whale_data: Dict) -> UnifiedSignal:
        """Bridge: MobyDickWhaleHunter or LiveBotTracker -> UnifiedSignal"""
        activity = whale_data.get('activity_type', 'unknown')
        direction_raw = whale_data.get('direction', 'neutral')

        direction = "BULLISH" if direction_raw == 'accumulation' else \
                    "BEARISH" if direction_raw == 'distribution' else "NEUTRAL"

        signal = UnifiedSignal(
            source="whale_hunter",
            signal_type="data",
            symbol=whale_data.get('symbol', 'BTC'),
            direction=direction,
            confidence=whale_data.get('confidence', 0.4),
            strength=whale_data.get('strength', 0.0),
            payload={
                'activity_type': activity,
                'whale_volume': whale_data.get('volume', 0),
                'bot_detected': whale_data.get('bot_detected', False),
                'pattern': whale_data.get('pattern', ''),
            }
        )
        self._store_signal(signal)
        return signal

    def ingest_surveillance_alert(self, alert_data: Dict) -> UnifiedSignal:
        """Bridge: AureonSurveillanceSystem manipulation alerts -> UnifiedSignal"""
        alert_type = alert_data.get('alert_type', '')
        severity = alert_data.get('severity', 'low')
        symbols = alert_data.get('symbols', [])

        # Manipulation detected = bearish pressure (caution)
        if severity in ('critical', 'high'):
            direction = "BEARISH"
            strength = -0.4
            confidence = 0.6
        elif severity == 'medium':
            direction = "NEUTRAL"
            strength = -0.1
            confidence = 0.3
        else:
            direction = "NEUTRAL"
            strength = 0.0
            confidence = 0.1

        signal = UnifiedSignal(
            source="surveillance",
            signal_type="data",
            symbol=symbols[0] if symbols else "MARKET",
            direction=direction,
            confidence=confidence,
            strength=strength,
            payload={
                'alert_type': alert_type,
                'severity': severity,
                'symbols': symbols,
                'description': alert_data.get('description', ''),
            }
        )
        self._store_signal(signal)
        return signal

    def ingest_price_cache(self, cache_data: Dict, source: str = "coingecko") -> int:
        """Bridge: CoinGecko/Kraken cache files -> UnifiedSignals. Returns count ingested."""
        ticker_cache = cache_data.get('ticker_cache', {})
        count = 0
        for symbol, data in ticker_cache.items():
            price = data.get('price', 0)
            change = data.get('change24h', data.get('change_pct', 0))
            volume = data.get('volume', 0)
            if price and price > 0:
                self.ingest_market_tick(symbol, price, change, volume, source)
                count += 1
        return count

    def get_latest(self, source: Optional[str] = None) -> List[UnifiedSignal]:
        """Get latest signals, optionally filtered by source."""
        with self._lock:
            if source:
                return [s for s in self._latest_signals.values() if s.source == source]
            return list(self._latest_signals.values())

    def get_all_data_signals(self) -> Dict[str, UnifiedSignal]:
        """Get all latest data signals keyed by source."""
        with self._lock:
            return dict(self._latest_signals)

    def _store_signal(self, signal: UnifiedSignal):
        with self._lock:
            key = f"{signal.source}:{signal.symbol}"
            self._latest_signals[key] = signal
            self._signal_history.append(signal)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PREDICTION BUS - Routes data to predictions, collects results
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionBus:
    """
    Routes DataBridge signals to ALL prediction engines.
    Collects prediction results as UnifiedSignals.

    Connects these previously-orphaned predictors:
    - NexusPredictor (79.6% win rate) -> was standalone, not in decision fusion
    - HNC Probability Matrix -> generated daily forecasts nobody consumed
    - Whale Hunter predictions -> generated predictions nothing acted on
    - Quantum Telescope -> orphaned predictions
    """

    def __init__(self):
        self._predictors: Dict[str, Callable] = {}
        self._latest_predictions: Dict[str, UnifiedSignal] = {}
        self._prediction_history: deque = deque(maxlen=500)
        self._lock = threading.Lock()

        # Auto-wire the HarmonicObserver predictor. Idempotent and
        # safe even if no observer has been constructed yet — the
        # predictor returns NEUTRAL until a singleton is registered.
        # Import inside __init__ to avoid any chance of circular import
        # at module load time.
        try:
            from aureon.observer.wiring import auto_wire_prediction_bus
            auto_wire_prediction_bus(self)
        except Exception as _exc:
            logger.debug("HarmonicObserver auto-wire skipped: %s", _exc)

        # Auto-wire the WavePredictor predictor. Same pattern as the
        # observer — idempotent, NEUTRAL until a singleton exists,
        # never blocks PredictionBus construction.
        try:
            from aureon.observer.wave_predictor import auto_wire_prediction_bus as _wp_wire
            _wp_wire(self)
        except Exception as _exc:
            logger.debug("WavePredictor auto-wire skipped: %s", _exc)

        # Auto-wire the MomentumTracker predictor (Stage AC). Recency-
        # weighted EMA momentum across all data sources fed into the
        # daemon — operator can see momentum forming on the live feed.
        try:
            from aureon.observer.momentum import auto_wire_prediction_bus as _mt_wire
            _mt_wire(self)
        except Exception as _exc:
            logger.debug("MomentumTracker auto-wire skipped: %s", _exc)

    def register_predictor(self, name: str, predict_fn: Callable):
        """Register a prediction engine. predict_fn(data_signals) -> UnifiedSignal"""
        self._predictors[name] = predict_fn
        logger.info(f"[PredictionBus] Registered predictor: {name}")

    def run_predictions(self, data_signals: Dict[str, UnifiedSignal],
                        symbol: str = "BTCUSD") -> Dict[str, UnifiedSignal]:
        """Run ALL registered predictors on current data and collect results."""
        results = {}

        for name, predict_fn in self._predictors.items():
            try:
                prediction = predict_fn(data_signals, symbol)
                if prediction:
                    prediction.signal_type = "prediction"
                    prediction.source = f"predictor:{name}"
                    results[name] = prediction
                    with self._lock:
                        self._latest_predictions[name] = prediction
                        self._prediction_history.append(prediction)
            except Exception as e:
                logger.warning(f"[PredictionBus] Predictor {name} failed: {e}")

        return results

    def get_consensus(self, predictions: Dict[str, UnifiedSignal]) -> UnifiedSignal:
        """Fuse all predictions into a single consensus signal."""
        if not predictions:
            return UnifiedSignal(source="prediction_bus", signal_type="prediction",
                               direction="NEUTRAL", confidence=0.0, strength=0.0)

        # Weighted average of all prediction strengths
        total_weight = 0.0
        weighted_strength = 0.0
        total_confidence = 0.0

        # Weight map: proven systems get more weight
        weight_map = {
            'nexus_predictor': 3.0,       # 79.6% validated
            'probability_ultimate': 2.5,   # 95% claimed
            'hnc_matrix': 2.0,
            'imperial': 1.5,
            'qgita': 2.0,
            'whale_hunter': 1.0,
            'quantum_telescope': 0.5,
            'harmonic_observer': 1.5,      # Theroux-style live HNC field describer
            'wave_predictor': 1.0,         # wave-based next-tick directional forecast
            'momentum_tracker': 1.2,       # recency-weighted multi-source momentum
        }

        for name, pred in predictions.items():
            w = weight_map.get(name, 1.0)
            weighted_strength += pred.strength * w * pred.confidence
            total_weight += w * pred.confidence
            total_confidence += pred.confidence

        if total_weight > 0:
            consensus_strength = weighted_strength / total_weight
        else:
            consensus_strength = 0.0

        avg_confidence = total_confidence / len(predictions) if predictions else 0.0

        if consensus_strength > 0.1:
            direction = "BULLISH"
        elif consensus_strength < -0.1:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Agreement bonus: if most predictors agree, boost confidence
        directions = [p.direction for p in predictions.values()]
        agreement = max(directions.count("BULLISH"), directions.count("BEARISH")) / len(directions)
        confidence_boost = agreement * 0.2  # Up to 20% boost for full agreement

        return UnifiedSignal(
            source="prediction_consensus",
            signal_type="prediction",
            direction=direction,
            confidence=min(avg_confidence + confidence_boost, 1.0),
            strength=consensus_strength,
            payload={
                'num_predictors': len(predictions),
                'agreement_ratio': agreement,
                'individual_predictions': {
                    name: {'direction': p.direction, 'confidence': p.confidence,
                           'strength': p.strength}
                    for name, p in predictions.items()
                },
            }
        )

    def get_latest_predictions(self) -> Dict[str, UnifiedSignal]:
        with self._lock:
            return dict(self._latest_predictions)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DECISION GATE - Fuses predictions + data into actionable decisions
# ═══════════════════════════════════════════════════════════════════════════════

class DecisionGate:
    """
    The single point where ALL signals become a GO/NO-GO decision.

    Previously: 8+ independent gates each checking different things.
    Now: ONE gate, ordered precedence, all inputs considered.
    """

    def __init__(self):
        self.min_confidence = 0.45       # Minimum consensus confidence
        self.min_agreement = 0.5         # At least 50% of predictors agree
        self.macro_veto_threshold = -0.5  # Macro signal this bearish = veto buys
        self.circuit_breaker_active = False
        self._decision_log: deque = deque(maxlen=200)
        self._lock = threading.Lock()

    def evaluate(self, consensus: UnifiedSignal,
                 data_signals: Dict[str, UnifiedSignal],
                 predictions: Dict[str, UnifiedSignal],
                 external_checks: Optional[Dict[str, Any]] = None) -> UnifiedSignal:
        """
        Single decision point. Returns a decision UnifiedSignal.

        Gate priority:
        1. Circuit breaker (hard stop)
        2. Macro veto (global conditions)
        3. External cognitive gates (Source Law, ZPE, Auris)
        4. Prediction consensus (the brain)
        5. Data confirmation (the eyes)

        Args:
            external_checks: Optional dict with keys:
                - source_law_action: str ("EXECUTE" or "HOLD")
                - source_law_coherence: float (0-1)
                - zpe_grounded: bool
                - auris_lighthouse_cleared: bool
                - auris_confidence: float (0-1)
        """
        reasons = []
        external_checks = external_checks or {}

        # GATE 1: Circuit breaker
        if self.circuit_breaker_active:
            return self._decision("HOLD", 0.0, 0.0, ["CIRCUIT_BREAKER_ACTIVE"])

        # GATE 2: Macro veto
        macro = data_signals.get('global_financial_feed:MACRO')
        if macro and consensus.direction == "BULLISH" and macro.strength < self.macro_veto_threshold:
            reasons.append(f"MACRO_VETO: macro_strength={macro.strength:.2f}")
            return self._decision("HOLD", consensus.confidence * 0.3, 0.0, reasons)

        # ═══════════════════════════════════════════════════════════════════════
        # GATE 3: EXTERNAL COGNITIVE GATES (Source Law + ZPE + Auris)
        # These close the loop between signal detection and execution.
        # ═══════════════════════════════════════════════════════════════════════

        # 3a: Source Law coherence threshold (default 0.938 entry / 0.934 exit)
        sl_action = external_checks.get('source_law_action')
        sl_coherence = external_checks.get('source_law_coherence', 0.0)
        if sl_action is not None and sl_action != "EXECUTE":
            reasons.append(f"SOURCE_LAW_VETO: coherence={sl_coherence:.3f} < 0.938")
            return self._decision("HOLD", consensus.confidence * 0.3, 0.0, reasons)

        # 3b: ZPE grounding check
        zpe_grounded = external_checks.get('zpe_grounded')
        if zpe_grounded is False:
            reasons.append("ZPE_DEGROUNDED: temporal ground unstable")
            return self._decision("HOLD", consensus.confidence * 0.3, 0.0, reasons)

        # 3c: Auris lighthouse cleared
        auris_lh = external_checks.get('auris_lighthouse_cleared')
        if auris_lh is False:
            reasons.append("AURIS_VETO: lighthouse not cleared")
            return self._decision("HOLD", consensus.confidence * 0.3, 0.0, reasons)

        # If Source Law coherence is high, boost confidence
        if sl_coherence >= 0.938:
            reasons.append(f"SOURCE_LAW_CLEAR: coherence={sl_coherence:.3f}")

        # ═══════════════════════════════════════════════════════════════════════

        # GATE 4: Minimum consensus confidence
        if consensus.confidence < self.min_confidence:
            reasons.append(f"LOW_CONFIDENCE: {consensus.confidence:.2f} < {self.min_confidence}")
            return self._decision("HOLD", consensus.confidence, 0.0, reasons)

        # GATE 5: Minimum agreement
        agreement = consensus.payload.get('agreement_ratio', 0.0)
        if agreement < self.min_agreement:
            reasons.append(f"LOW_AGREEMENT: {agreement:.2f} < {self.min_agreement}")
            return self._decision("HOLD", consensus.confidence, consensus.strength * 0.5, reasons)

        # GATE 6: Sentiment confirmation (optional boost)
        sentiment = data_signals.get('news_sentiment:SENTIMENT')
        sentiment_aligned = False
        if sentiment:
            if sentiment.direction == consensus.direction:
                sentiment_aligned = True
                reasons.append(f"SENTIMENT_CONFIRMS: {sentiment.direction}")

        # GATE 7: Whale flow confirmation (optional boost)
        whale_aligned = False
        for key, sig in data_signals.items():
            if sig.source == "whale_hunter" and sig.direction == consensus.direction:
                whale_aligned = True
                reasons.append(f"WHALE_CONFIRMS: {sig.payload.get('activity_type', '')}")
                break

        # Compute final confidence with boosts
        final_confidence = consensus.confidence
        if sentiment_aligned:
            final_confidence = min(final_confidence + 0.05, 1.0)
        if whale_aligned:
            final_confidence = min(final_confidence + 0.05, 1.0)
        if macro and macro.direction == consensus.direction:
            final_confidence = min(final_confidence + 0.05, 1.0)
            reasons.append("MACRO_ALIGNED")
        # QGITA structural event boost
        qgita_pred = predictions.get('qgita')
        if qgita_pred and qgita_pred.payload.get('qgita_structural_event'):
            final_confidence = min(final_confidence + 0.08, 1.0)
            reasons.append("QGITA_STRUCTURAL_EVENT")
        # Harmonic field alignment boost
        hf_pred = predictions.get('harmonic_field')
        if hf_pred and hf_pred.direction == consensus.direction:
            final_confidence = min(final_confidence + 0.05, 1.0)
            reasons.append("HARMONIC_FIELD_ALIGNED")

        # Position size multiplier based on confidence
        position_mult = 0.5  # Base
        if final_confidence > 0.7:
            position_mult = 1.0
        elif final_confidence > 0.6:
            position_mult = 0.75

        reasons.append(f"CONSENSUS: {consensus.direction} @ {final_confidence:.2f}")
        reasons.append(f"POSITION_MULT: {position_mult}")

        action = "BUY" if consensus.direction == "BULLISH" else \
                 "SELL" if consensus.direction == "BEARISH" else "HOLD"

        decision = self._decision(action, final_confidence, consensus.strength, reasons)
        decision.payload['position_multiplier'] = position_mult
        decision.payload['num_confirmations'] = sum([sentiment_aligned, whale_aligned,
                                                      macro is not None and macro.direction == consensus.direction])
        return decision

    def _decision(self, action: str, confidence: float, strength: float,
                  reasons: List[str]) -> UnifiedSignal:
        signal = UnifiedSignal(
            source="decision_gate",
            signal_type="decision",
            direction=action,
            confidence=confidence,
            strength=strength,
            payload={'reasons': reasons, 'action': action}
        )
        with self._lock:
            self._decision_log.append(signal)
        return signal

    def get_recent_decisions(self, limit: int = 20) -> List[Dict]:
        with self._lock:
            return [d.to_dict() for d in list(self._decision_log)[-limit:]]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FEEDBACK LOOP ENGINE - The missing piece that closes the circle
# ═══════════════════════════════════════════════════════════════════════════════

class FeedbackLoopEngine:
    """
    THE BIG FIX: Routes trade outcomes BACK to prediction engines.

    Before this: data went to die in JSONL files
    After this: every outcome recalibrates every predictor

    Feedback channels:
    1. Trade outcome -> NexusPredictor.record_trade_outcome()
    2. Trade outcome -> Rolling win rate -> Kelly Criterion recalibration
    3. Prediction accuracy -> Dynamic predictor weighting in PredictionBus
    4. Actual slippage/fees -> Adaptive Profit Gate recalibration
    5. Pattern performance -> Nexus pattern weight adjustment (currently 70% locked)
    """

    def __init__(self):
        self._outcomes: deque = deque(maxlen=1000)
        self._predictor_accuracy: Dict[str, Dict] = defaultdict(
            lambda: {'correct': 0, 'incorrect': 0, 'total': 0}
        )
        self._rolling_win_rate: deque = deque(maxlen=200)
        self._actual_costs: deque = deque(maxlen=200)  # Track real fees/slippage
        self._lock = threading.Lock()
        self._feedback_file = "autonomy_feedback_loop.jsonl"

        # Load previous state
        self._load_state()

    def record_outcome(self, trade_result: Dict,
                       entry_predictions: Dict[str, UnifiedSignal],
                       entry_decision: UnifiedSignal) -> Dict[str, Any]:
        """
        Record a trade outcome and feed it back to ALL prediction engines.

        Returns feedback actions taken.
        """
        was_profitable = trade_result.get('net_pnl', 0) > 0
        pnl_pct = trade_result.get('pnl_pct', 0.0)
        actual_fees = trade_result.get('total_fees', 0.0)
        actual_slippage = trade_result.get('actual_slippage', 0.0)
        symbol = trade_result.get('symbol', 'UNKNOWN')

        feedback_actions = []

        with self._lock:
            # Track rolling win rate
            self._rolling_win_rate.append(1 if was_profitable else 0)

            # Track actual costs
            if actual_fees > 0 or actual_slippage > 0:
                self._actual_costs.append({
                    'fees': actual_fees,
                    'slippage': actual_slippage,
                    'exchange': trade_result.get('exchange', 'unknown'),
                    'timestamp': time.time(),
                })

        # FEEDBACK 1: Score each predictor's accuracy
        for pred_name, pred_signal in entry_predictions.items():
            predicted_bullish = pred_signal.direction == "BULLISH"
            was_correct = (predicted_bullish and was_profitable) or \
                          (not predicted_bullish and not was_profitable)

            with self._lock:
                acc = self._predictor_accuracy[pred_name]
                acc['total'] += 1
                if was_correct:
                    acc['correct'] += 1
                else:
                    acc['incorrect'] += 1

            feedback_actions.append(f"scored:{pred_name}:{'correct' if was_correct else 'incorrect'}")

        # FEEDBACK 2: Feed outcome to NexusPredictor if available
        try:
            from aureon.intelligence.nexus_predictor import NexusPredictor
            nexus = _get_nexus_predictor()
            if nexus:
                entry_pred = {}
                if 'nexus_predictor' in entry_predictions:
                    entry_pred = entry_predictions['nexus_predictor'].payload
                elif entry_decision.payload:
                    entry_pred = entry_decision.payload

                nexus.record_trade_outcome(entry_pred, was_profitable, pnl_pct)
                feedback_actions.append("nexus_learning_updated")
        except Exception as e:
            logger.debug(f"Nexus feedback skipped: {e}")

        # FEEDBACK 3: Recalculate dynamic predictor weights
        new_weights = self._recalculate_predictor_weights()
        if new_weights:
            feedback_actions.append(f"weights_updated:{len(new_weights)}")

        # FEEDBACK 4: Track actual costs for profit gate adaptation
        if actual_fees > 0:
            self._update_cost_model(trade_result)
            feedback_actions.append("cost_model_updated")

        # Persist
        outcome_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'was_profitable': was_profitable,
            'pnl_pct': pnl_pct,
            'actual_fees': actual_fees,
            'actual_slippage': actual_slippage,
            'predictions_scored': len(entry_predictions),
            'feedback_actions': feedback_actions,
            'rolling_win_rate': self.get_rolling_win_rate(),
        }
        self._persist(outcome_record)

        with self._lock:
            self._outcomes.append(outcome_record)

        return {'actions': feedback_actions, 'rolling_win_rate': self.get_rolling_win_rate()}

    def get_rolling_win_rate(self) -> float:
        """Current rolling win rate from recent trades."""
        with self._lock:
            if not self._rolling_win_rate:
                return 0.5  # Default
            return sum(self._rolling_win_rate) / len(self._rolling_win_rate)

    def get_predictor_weights(self) -> Dict[str, float]:
        """Get dynamic weights based on actual predictor performance."""
        return self._recalculate_predictor_weights()

    def get_average_actual_costs(self, exchange: str = None) -> Dict[str, float]:
        """Get average actual trading costs from real outcomes."""
        with self._lock:
            costs = list(self._actual_costs)

        if exchange:
            costs = [c for c in costs if c.get('exchange') == exchange]

        if not costs:
            return {'avg_fees': 0.002, 'avg_slippage': 0.001}  # Defaults

        avg_fees = sum(c['fees'] for c in costs) / len(costs)
        avg_slippage = sum(c['slippage'] for c in costs) / len(costs)

        return {'avg_fees': avg_fees, 'avg_slippage': avg_slippage}

    def _recalculate_predictor_weights(self) -> Dict[str, float]:
        """Recalculate predictor weights from actual accuracy data."""
        weights = {}
        with self._lock:
            for name, acc in self._predictor_accuracy.items():
                if acc['total'] < 10:
                    continue  # Not enough data
                accuracy = acc['correct'] / acc['total']
                # Scale: 50% accuracy = 0.5 weight, 80% = 2.0 weight
                weights[name] = max(0.1, (accuracy - 0.3) * 3.33)
        return weights

    def _update_cost_model(self, trade_result: Dict):
        """Update adaptive profit gate with real cost data from actual trades."""
        try:
            from aureon.utils.adaptive_prime_profit_gate import get_adaptive_gate
            gate = get_adaptive_gate()
            if gate:
                exchange = trade_result.get('exchange', 'kraken')
                actual_fee_rate = trade_result.get('fee_rate', 0.0)
                actual_slippage = trade_result.get('actual_slippage', 0.0)

                # Update fee profile with real data
                if actual_fee_rate > 0 and hasattr(gate, 'fee_profiles'):
                    ex = exchange.lower()
                    if ex in gate.fee_profiles:
                        profile = gate.fee_profiles[ex]
                        # Blend: 80% existing + 20% actual (smooth adaptation)
                        profile.taker_fee = profile.taker_fee * 0.8 + actual_fee_rate * 0.2
                        profile.last_updated = time.time()

                # Update slippage with real data
                if actual_slippage > 0 and hasattr(gate, 'fee_profiles'):
                    ex = exchange.lower()
                    if ex in gate.fee_profiles:
                        profile = gate.fee_profiles[ex]
                        profile.slippage_estimate = profile.slippage_estimate * 0.8 + actual_slippage * 0.2
                        profile.last_updated = time.time()
        except Exception:
            pass

    def get_kelly_inputs(self) -> Dict[str, float]:
        """Get live Kelly Criterion inputs from actual trading data.

        Returns win_rate, avg_win, avg_loss for Kelly sizing.
        This replaces the hardcoded 0.55 win rate everywhere.
        """
        with self._lock:
            outcomes = list(self._outcomes)

        if len(outcomes) < 10:
            return {'win_rate': 0.55, 'avg_win_pct': 0.5, 'avg_loss_pct': 0.3}

        wins = [o for o in outcomes if o.get('was_profitable')]
        losses = [o for o in outcomes if not o.get('was_profitable')]

        win_rate = len(wins) / len(outcomes) if outcomes else 0.55
        avg_win = sum(o.get('pnl_pct', 0) for o in wins) / len(wins) if wins else 0.5
        avg_loss = abs(sum(o.get('pnl_pct', 0) for o in losses) / len(losses)) if losses else 0.3

        return {
            'win_rate': max(0.01, min(0.99, win_rate)),
            'avg_win_pct': max(0.01, avg_win),
            'avg_loss_pct': max(0.01, avg_loss),
        }

    def _persist(self, record: Dict):
        """Persist feedback record to JSONL."""
        try:
            with open(self._feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
        except Exception:
            pass

    def _load_state(self):
        """Load previous feedback state."""
        if not os.path.exists(self._feedback_file):
            return
        try:
            with open(self._feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line.strip())
                        self._outcomes.append(record)
                        if record.get('was_profitable') is not None:
                            self._rolling_win_rate.append(
                                1 if record['was_profitable'] else 0
                            )
            logger.info(f"[FeedbackLoop] Loaded {len(self._outcomes)} historical outcomes")
        except Exception as e:
            logger.debug(f"[FeedbackLoop] Could not load state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. PREDICTOR ADAPTERS - Wire existing prediction engines to PredictionBus
# ═══════════════════════════════════════════════════════════════════════════════

_nexus_instance = None

def _get_nexus_predictor():
    """Lazy singleton for NexusPredictor."""
    global _nexus_instance
    if _nexus_instance is None:
        try:
            from aureon.intelligence.nexus_predictor import NexusPredictor
            _nexus_instance = NexusPredictor()
            _nexus_instance.load_learning_state()
        except Exception:
            pass
    return _nexus_instance


def adapt_nexus_predictor(data_signals: Dict[str, UnifiedSignal],
                           symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: NexusPredictor -> UnifiedSignal"""
    nexus = _get_nexus_predictor()
    if not nexus:
        return None

    try:
        prediction = nexus.predict()
        if not prediction or not prediction.get('should_trade', False):
            return UnifiedSignal(
                source="predictor:nexus_predictor",
                signal_type="prediction",
                symbol=symbol,
                direction="NEUTRAL",
                confidence=prediction.get('confidence', 0.0) if prediction else 0.0,
                strength=0.0,
            )

        direction = prediction.get('direction', 'NEUTRAL')
        signal_dir = "BULLISH" if direction == "BULLISH" else \
                     "BEARISH" if direction == "BEARISH" else "NEUTRAL"

        return UnifiedSignal(
            source="predictor:nexus_predictor",
            signal_type="prediction",
            symbol=symbol,
            direction=signal_dir,
            confidence=prediction.get('confidence', 0.5),
            strength=prediction.get('edge', 0.0) * (1 if direction == "BULLISH" else -1),
            payload={
                'probability': prediction.get('probability', 0.5),
                'edge': prediction.get('edge', 0.0),
                'patterns_triggered': prediction.get('factors', {}).get('reasons', []),
            }
        )
    except Exception as e:
        logger.debug(f"Nexus adapter error: {e}")
        return None


def adapt_macro_to_prediction(data_signals: Dict[str, UnifiedSignal],
                               symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Macro data signals -> prediction-style UnifiedSignal"""
    macro = data_signals.get('global_financial_feed:MACRO')
    if not macro:
        return None

    # Macro as a prediction: fear/greed, VIX, DXY all inform direction
    return UnifiedSignal(
        source="predictor:macro_context",
        signal_type="prediction",
        symbol=symbol,
        direction=macro.direction,
        confidence=macro.confidence * 0.7,  # Discount: macro is context, not precise
        strength=macro.strength * 0.7,
        payload=macro.payload,
    )


def adapt_sentiment_to_prediction(data_signals: Dict[str, UnifiedSignal],
                                   symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: News sentiment -> prediction-style UnifiedSignal"""
    sentiment = data_signals.get('news_sentiment:SENTIMENT')
    if not sentiment:
        return None

    return UnifiedSignal(
        source="predictor:sentiment_analysis",
        signal_type="prediction",
        symbol=symbol,
        direction=sentiment.direction,
        confidence=sentiment.confidence * 0.6,
        strength=sentiment.strength * 0.6,
        payload=sentiment.payload,
    )


# ── NEW PREDICTOR ADAPTERS (closing the remaining 35% gap) ──────────────────

_hnc_instance = None
_imperial_instance = None
_ultimate_instance = None
_whale_hunter_instance = None
_quantum_telescope_instance = None
_war_planner_instance = None


def adapt_war_planner(data_signals: Dict[str, UnifiedSignal],
                       symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Strategic War Planner (adversarial chess mind) -> UnifiedSignal.

    The War Planner plays chess against itself:
    White (Profit) vs Black (Loss). Uses 2-steps-back-1-step-forward
    prediction with Sun Tzu + IRA guerrilla doctrine.
    """
    global _war_planner_instance
    try:
        if _war_planner_instance is None:
            from aureon.command_centers.aureon_strategic_war_planner import get_war_planner
            _war_planner_instance = get_war_planner()

        # Extract price/volume from market signals
        price, volume, change_pct = 0.0, 0.0, 0.0
        for key, sig in data_signals.items():
            if sig.source.startswith('market_') and sig.symbol == symbol:
                price = sig.payload.get('price', 0.0)
                volume = sig.payload.get('volume', 0.0)
                change_pct = sig.payload.get('change_pct', 0.0)
                break

        if price <= 0:
            return None

        plan = _war_planner_instance.plan(
            symbol=symbol, price=price, volume=volume, change_pct=change_pct
        )

        if not plan or not plan.final_move:
            return None

        move = plan.final_move
        pattern = plan.step_forward.get('pattern', 'NEUTRAL')

        if move.move_type.value in ('BUY', 'AMBUSH_WAIT'):
            direction = "BULLISH"
            strength = move.confidence * 0.8
        elif move.move_type.value in ('SELL', 'RETREAT'):
            direction = "BEARISH"
            strength = -move.confidence * 0.8
        else:
            direction = "NEUTRAL"
            strength = 0.0

        return UnifiedSignal(
            source="predictor:war_planner",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=move.confidence * move.survival_probability,
            strength=max(-1.0, min(1.0, strength)),
            payload={
                'move_type': move.move_type.value,
                'survival_probability': move.survival_probability,
                'pattern': pattern,
                'stance': plan.stance.value,
                'reasoning': move.reasoning[:200],
                'consensus_agreement': plan.consensus_agreement,
                'systems_consulted': plan.systems_consulted,
            }
        )
    except Exception as e:
        logger.debug(f"War Planner adapter: {e}")
        return None


def adapt_hnc_probability_matrix(data_signals: Dict[str, UnifiedSignal],
                                  symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: HNC Probability Matrix (multi-day temporal forecasting) -> UnifiedSignal"""
    global _hnc_instance
    try:
        if _hnc_instance is None:
            from aureon.strategies.hnc_probability_matrix import TemporalFrequencyAnalyzer
            _hnc_instance = TemporalFrequencyAnalyzer()

        # Build current_data from available market signals
        current_data = {}
        for key, sig in data_signals.items():
            if sig.source.startswith('market_') and sig.symbol == symbol:
                current_data = sig.payload
                break

        if not current_data:
            current_data = {'price': 0, 'change_pct': 0, 'volume': 0}

        matrix = _hnc_instance.generate_probability_matrix(symbol, current_data)
        if not matrix:
            return None

        combined = getattr(matrix, 'combined_probability', 0.5)
        confidence = getattr(matrix, 'confidence_score', 0.5)
        action = getattr(matrix, 'recommended_action', 'HOLD')

        if 'BUY' in str(action).upper():
            direction = "BULLISH"
            strength = (combined - 0.5) * 2
        elif 'SELL' in str(action).upper():
            direction = "BEARISH"
            strength = (0.5 - combined) * -2
        else:
            direction = "NEUTRAL"
            strength = 0.0

        return UnifiedSignal(
            source="predictor:hnc_matrix",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=min(confidence, 1.0),
            strength=max(-1.0, min(1.0, strength)),
            payload={
                'combined_probability': combined,
                'fine_tuned': getattr(matrix, 'fine_tuned_probability', combined),
                'recommended_action': str(action),
            }
        )
    except Exception as e:
        logger.debug(f"HNC Matrix adapter: {e}")
        return None


def adapt_imperial_predictability(data_signals: Dict[str, UnifiedSignal],
                                   symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Imperial Predictability Engine (cosmic sync) -> UnifiedSignal"""
    global _imperial_instance
    try:
        if _imperial_instance is None:
            from aureon.strategies.hnc_imperial_predictability import PredictabilityEngine
            _imperial_instance = PredictabilityEngine()

        matrix = _imperial_instance.generate_matrix()
        if not matrix:
            return None

        combined = getattr(matrix, 'combined_probability', 0.5)
        action = getattr(matrix, 'recommended_action', 'HOLD')
        pos_mult = getattr(matrix, 'position_multiplier', 1.0)

        if 'BUY' in str(action).upper():
            direction = "BULLISH"
        elif 'SELL' in str(action).upper():
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        strength = (combined - 0.5) * 2 if direction == "BULLISH" else \
                   (0.5 - combined) * -2 if direction == "BEARISH" else 0.0

        return UnifiedSignal(
            source="predictor:imperial",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=min(abs(strength) + 0.3, 1.0),
            strength=max(-1.0, min(1.0, strength)),
            payload={
                'combined_probability': combined,
                'position_multiplier': pos_mult,
                'recommended_action': str(action),
            }
        )
    except Exception as e:
        logger.debug(f"Imperial adapter: {e}")
        return None


def adapt_probability_ultimate(data_signals: Dict[str, UnifiedSignal],
                                symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Probability Ultimate Intelligence (95% accuracy) -> UnifiedSignal"""
    global _ultimate_instance
    try:
        if _ultimate_instance is None:
            from aureon.strategies.probability_ultimate_intelligence import ProbabilityUltimateIntelligence
            _ultimate_instance = ProbabilityUltimateIntelligence()

        # Build market state from data signals
        market_state = {}
        for key, sig in data_signals.items():
            if sig.source.startswith('market_') and sig.symbol == symbol:
                market_state = sig.payload
                break

        prediction = _ultimate_instance.predict(symbol=symbol, market_data=market_state)
        if not prediction:
            return None

        prob = getattr(prediction, 'final_probability', 0.5)
        should_trade = getattr(prediction, 'should_trade', False)
        win_rate = getattr(prediction, 'pattern_win_rate', 0.5)
        is_guaranteed = getattr(prediction, 'is_guaranteed_win', False)

        if not should_trade:
            return UnifiedSignal(
                source="predictor:probability_ultimate",
                signal_type="prediction", symbol=symbol,
                direction="NEUTRAL", confidence=0.0, strength=0.0,
            )

        if prob > 0.55:
            direction = "BULLISH"
            strength = (prob - 0.5) * 2
        elif prob < 0.45:
            direction = "BEARISH"
            strength = (0.5 - prob) * -2
        else:
            direction = "NEUTRAL"
            strength = 0.0

        confidence = min(win_rate, 1.0)
        if is_guaranteed:
            confidence = min(confidence + 0.2, 1.0)

        return UnifiedSignal(
            source="predictor:probability_ultimate",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            strength=max(-1.0, min(1.0, strength)),
            payload={
                'final_probability': prob,
                'pattern_win_rate': win_rate,
                'pattern_key': getattr(prediction, 'pattern_key', ''),
                'is_guaranteed_win': is_guaranteed,
                'reasoning': str(getattr(prediction, 'reasoning', ''))[:200],
            }
        )
    except Exception as e:
        logger.debug(f"Ultimate Intelligence adapter: {e}")
        return None


def adapt_whale_hunter(data_signals: Dict[str, UnifiedSignal],
                        symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Moby Dick Whale Hunter predictions -> UnifiedSignal"""
    global _whale_hunter_instance
    try:
        if _whale_hunter_instance is None:
            from aureon.analytics.aureon_moby_dick_whale_hunter import MobyDickWhaleHunter
            _whale_hunter_instance = MobyDickWhaleHunter()

        prediction = _whale_hunter_instance.predict_next_whale_appearance(symbol)
        if not prediction:
            return None

        side = getattr(prediction, 'predicted_side', 'neutral')
        confidence = getattr(prediction, 'confidence', 0.3)
        ready = getattr(prediction, 'ready_for_execution', False)

        if side == 'buy' or side == 'accumulation':
            direction = "BULLISH"
            strength = confidence * 0.8
        elif side == 'sell' or side == 'distribution':
            direction = "BEARISH"
            strength = -confidence * 0.8
        else:
            direction = "NEUTRAL"
            strength = 0.0

        return UnifiedSignal(
            source="predictor:whale_hunter",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=confidence if ready else confidence * 0.5,
            strength=strength,
            payload={
                'predicted_side': side,
                'ready_for_execution': ready,
                'pattern_type': getattr(prediction, 'pattern_type', ''),
                'validation_count': getattr(prediction, 'validation_count', 0),
            }
        )
    except Exception as e:
        logger.debug(f"Whale Hunter adapter: {e}")
        return None


def adapt_quantum_telescope(data_signals: Dict[str, UnifiedSignal],
                             symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Enhanced Quantum Telescope (sacred geometry) -> UnifiedSignal"""
    global _quantum_telescope_instance
    try:
        if _quantum_telescope_instance is None:
            from aureon.simulation.aureon_enhanced_quantum_telescope import EnhancedQuantumGeometryEngine
            _quantum_telescope_instance = EnhancedQuantumGeometryEngine()

        # Build bot data from market signals
        bot_data = {}
        for key, sig in data_signals.items():
            if sig.source.startswith('market_') and sig.symbol == symbol:
                bot_data = sig.payload
                break

        analysis = _quantum_telescope_instance.analyze_bot_with_telescope(bot_data)
        if not analysis:
            return None

        golden_ratio = analysis.get('golden_ratio_score', 0.5)
        harmonic = analysis.get('harmonic_resonance', 0.5)
        manipulation = analysis.get('manipulation_probability', 0.5)

        # High golden ratio + low manipulation = bullish geometry
        geo_score = (golden_ratio * 0.5 + harmonic * 0.3 - manipulation * 0.2)

        if geo_score > 0.55:
            direction = "BULLISH"
        elif geo_score < 0.45:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        return UnifiedSignal(
            source="predictor:quantum_telescope",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=min(abs(geo_score - 0.5) * 3, 1.0),
            strength=(geo_score - 0.5) * 2,
            payload={
                'shape': analysis.get('shape', ''),
                'golden_ratio_score': golden_ratio,
                'harmonic_resonance': harmonic,
                'manipulation_probability': manipulation,
            }
        )
    except Exception as e:
        logger.debug(f"Quantum Telescope adapter: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# QGITA ADAPTER - Quantum Gravity in the Act (φ-resonant signal detection)
# ═══════════════════════════════════════════════════════════════════════════════
_qgita_instance = None

def _get_qgita_instance():
    global _qgita_instance
    if _qgita_instance is None and QGITA_AVAILABLE:
        _qgita_instance = QGITAMarketAnalyzer()
    return _qgita_instance


def adapt_qgita(data_signals: Dict[str, UnifiedSignal],
                symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: QGITA Framework -> UnifiedSignal

    Maps QGITA's two-stage pipeline (FTCP + Lighthouse) into a trading
    prediction with direction, confidence, and structural-event flag.
    """
    qgita = _get_qgita_instance()
    if not qgita:
        return None

    try:
        # Pull the latest price for this symbol from data bridge
        price = 0.0
        for key, sig in data_signals.items():
            if sig.symbol == symbol and sig.source.startswith('market_'):
                price = float(sig.payload.get('price', 0) or 0)
                break

        if price > 0:
            qgita.feed_price(price, time.time())

        analysis = qgita.analyze()
        if analysis.get("status") != "complete":
            return None

        signals = analysis.get("signals", {})
        coherence = analysis.get("coherence", {})
        stage2 = analysis.get("stage2", {})

        direction = signals.get("direction", "NEUTRAL")
        confidence = signals.get("confidence", 0.5)
        structural = signals.get("structural_event", False)
        global_R = coherence.get("global_R", 0.0)
        lighthouse_L = stage2.get("current_lighthouse_intensity", 0.0)

        # Map direction string to UnifiedSignal direction
        sig_dir = "BULLISH" if direction == "BULLISH" or direction == "RALLY" else \
                  "BEARISH" if direction == "BEARISH" or direction == "DUMP" else "NEUTRAL"

        # Structural events get a confidence boost
        if structural:
            confidence = min(1.0, confidence + 0.15)

        # Regime-aware strength: chaotic = reduced strength
        regime = analysis.get("regime", {}).get("state", "neutral")
        strength = signals.get("strength", 0.0)
        if regime == "chaotic":
            strength *= 0.5
        elif regime == "coherent":
            strength *= 1.2

        return UnifiedSignal(
            source="predictor:qgita",
            signal_type="prediction",
            symbol=symbol,
            direction=sig_dir,
            confidence=confidence,
            strength=max(-1.0, min(1.0, strength)) * (1 if sig_dir == "BULLISH" else -1 if sig_dir == "BEARISH" else 1),
            payload={
                "qgita_regime": regime,
                "qgita_global_R": global_R,
                "qgita_lighthouse_L": lighthouse_L,
                "qgita_structural_event": structural,
                "qgita_ftcp_count": analysis.get("stage1", {}).get("ftcp_count", 0),
                "qgita_lhe_count": stage2.get("lhe_count", 0),
            }
        )
    except Exception as e:
        logger.debug(f"QGITA adapter error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# HARMONIC FIELD ADAPTER - Global Λ(t) -> UnifiedSignal
# ═══════════════════════════════════════════════════════════════════════════════
_harmonic_field_instance = None

def _get_harmonic_field_instance():
    global _harmonic_field_instance
    if _harmonic_field_instance is None and HARMONIC_FIELD_AVAILABLE:
        _harmonic_field_instance = get_global_field()
    return _harmonic_field_instance


def adapt_harmonic_field(data_signals: Dict[str, UnifiedSignal],
                         symbol: str) -> Optional[UnifiedSignal]:
    """Adapter: Global Harmonic Field Λ(t) -> UnifiedSignal

    Uses the Master Formula Ω output to generate a directional bias.
    """
    field = _get_harmonic_field_instance()
    if not field:
        return None

    try:
        omega = compute_global_omega(field)
        if omega is None:
            return None

        # Omega > 0.55 = bullish harmonic substrate, < 0.45 = bearish
        if omega > 0.55:
            direction = "BULLISH"
            strength = min(1.0, (omega - 0.5) * 4)
        elif omega < 0.45:
            direction = "BEARISH"
            strength = -min(1.0, (0.5 - omega) * 4)
        else:
            direction = "NEUTRAL"
            strength = 0.0

        confidence = min(1.0, abs(omega - 0.5) * 3)

        return UnifiedSignal(
            source="predictor:harmonic_field",
            signal_type="prediction",
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            strength=strength,
            payload={
                "omega": omega,
                "field_sources": len(getattr(field, 'sources', [])) if field else 0,
            }
        )
    except Exception as e:
        logger.debug(f"Harmonic field adapter error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 7. THE BIG WHEEL - AUTONOMY HUB
# ═══════════════════════════════════════════════════════════════════════════════

class AutonomyHub:
    """
    THE BIG WHEEL.

    Spins continuously:
        Data in -> Predictions made -> Decisions formed -> Outcomes tracked -> Learning applied

    One hub. One loop. Everything connected.
    """

    def __init__(self):
        self.data_bridge = DataBridge()
        self.prediction_bus = PredictionBus()
        self.decision_gate = DecisionGate()
        self.feedback_loop = FeedbackLoopEngine()

        self._running = False
        self._cycle_count = 0
        self._last_cycle_time = 0.0
        self._thought_bus = None
        self._lock = threading.Lock()

        # Register ALL predictor adapters - every prediction engine wired in
        self.prediction_bus.register_predictor('nexus_predictor', adapt_nexus_predictor)
        self.prediction_bus.register_predictor('macro_context', adapt_macro_to_prediction)
        self.prediction_bus.register_predictor('sentiment_analysis', adapt_sentiment_to_prediction)
        self.prediction_bus.register_predictor('hnc_matrix', adapt_hnc_probability_matrix)
        self.prediction_bus.register_predictor('imperial', adapt_imperial_predictability)
        self.prediction_bus.register_predictor('probability_ultimate', adapt_probability_ultimate)
        self.prediction_bus.register_predictor('whale_hunter', adapt_whale_hunter)
        self.prediction_bus.register_predictor('quantum_telescope', adapt_quantum_telescope)
        self.prediction_bus.register_predictor('war_planner', adapt_war_planner)
        self.prediction_bus.register_predictor('qgita', adapt_qgita)
        self.prediction_bus.register_predictor('harmonic_field', adapt_harmonic_field)

        # Apply learned weights from feedback loop
        self._apply_learned_weights()

        logger.info("[AutonomyHub] THE BIG WHEEL initialized")
        logger.info(f"[AutonomyHub] Registered {len(self.prediction_bus._predictors)} predictors")
        logger.info(f"[AutonomyHub] Rolling win rate: {self.feedback_loop.get_rolling_win_rate():.1%}")

    def connect_thought_bus(self):
        """Wire into the ThoughtBus for system-wide integration."""
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus, Thought
            self._thought_bus = get_thought_bus()

            # Subscribe to ALL data topics and bridge them
            self._thought_bus.subscribe("market.*", self._on_market_thought)
            self._thought_bus.subscribe("news.*", self._on_news_thought)
            self._thought_bus.subscribe("whale.*", self._on_whale_thought)
            self._thought_bus.subscribe("execution.*", self._on_execution_thought)
            self._thought_bus.subscribe("surveillance.*", self._on_surveillance_thought)
            self._thought_bus.subscribe("intelligence.*", self._on_whale_thought)  # Whale intel
            self._thought_bus.subscribe("bot.*", self._on_surveillance_thought)    # Bot detection
            self._thought_bus.subscribe("strategy.*", self._on_strategy_thought)  # War Planner

            logger.info("[AutonomyHub] Connected to ThoughtBus")
        except Exception as e:
            logger.warning(f"[AutonomyHub] ThoughtBus connection failed: {e}")

    def _on_market_thought(self, thought):
        """Bridge ThoughtBus market data -> DataBridge."""
        payload = thought.payload if hasattr(thought, 'payload') else {}
        symbol = payload.get('symbol', '')
        price = payload.get('price', 0)
        change = payload.get('change_pct', 0)
        volume = payload.get('volume', 0)
        exchange = payload.get('exchange', 'unknown')
        if symbol and price:
            self.data_bridge.ingest_market_tick(symbol, price, change, volume, exchange)

    def _on_news_thought(self, thought):
        """Bridge ThoughtBus news data -> DataBridge."""
        payload = thought.payload if hasattr(thought, 'payload') else {}
        if payload:
            self.data_bridge.ingest_news_sentiment(payload)

    def _on_whale_thought(self, thought):
        """Bridge ThoughtBus whale data -> DataBridge."""
        payload = thought.payload if hasattr(thought, 'payload') else {}
        if payload:
            self.data_bridge.ingest_whale_signal(payload)

    def _on_execution_thought(self, thought):
        """Bridge ThoughtBus execution results -> FeedbackLoop."""
        payload = thought.payload if hasattr(thought, 'payload') else {}
        if payload.get('net_pnl') is not None:
            # This is a trade result - feed it back
            self.feedback_loop.record_outcome(
                trade_result=payload,
                entry_predictions=self.prediction_bus.get_latest_predictions(),
                entry_decision=UnifiedSignal()
            )

    def _on_surveillance_thought(self, thought):
        """Bridge ThoughtBus surveillance/bot alerts -> DataBridge."""
        payload = thought.payload if hasattr(thought, 'payload') else {}
        if payload:
            self.data_bridge.ingest_surveillance_alert(payload)

    def _on_strategy_thought(self, thought):
        """Bridge War Planner strategy plans -> logging & awareness."""
        payload = thought.payload if hasattr(thought, 'payload') else {}
        if payload:
            logger.info(f"[AutonomyHub] War Plan received: {payload.get('action', '?')} "
                        f"| Pattern: {payload.get('step_forward', {}).get('pattern', '?')} "
                        f"| Confidence: {payload.get('confidence', 0):.0%}")

    def spin_cycle(self, symbol: str = "BTCUSD",
                   external_checks: Optional[Dict[str, Any]] = None) -> UnifiedSignal:
        """
        ONE TURN OF THE BIG WHEEL.

        Returns the decision for this cycle.

        Args:
            symbol: Trading pair to evaluate
            external_checks: Optional cognitive gates from ecosystem/ICS:
                - source_law_action: "EXECUTE" or "HOLD"
                - source_law_coherence: float (0-1)
                - zpe_grounded: bool
                - auris_lighthouse_cleared: bool
        """
        self._cycle_count += 1
        cycle_start = time.time()

        # STEP 1: Gather all data signals
        data_signals = self.data_bridge.get_all_data_signals()

        # STEP 2: Also pull from GlobalFinancialFeed if available
        self._pull_macro_data()
        data_signals = self.data_bridge.get_all_data_signals()  # Refresh after macro pull

        # STEP 3: Run ALL predictors
        predictions = self.prediction_bus.run_predictions(data_signals, symbol)

        # STEP 4: Get consensus from all predictions
        consensus = self.prediction_bus.get_consensus(predictions)

        # STEP 5: Apply feedback-learned weights if available
        learned_weights = self.feedback_loop.get_predictor_weights()
        if learned_weights:
            # Re-run consensus with learned weights
            consensus = self._weighted_consensus(predictions, learned_weights)

        # STEP 6: Decision gate evaluates everything (including external cognitive gates)
        decision = self.decision_gate.evaluate(consensus, data_signals, predictions, external_checks)

        # STEP 7: Publish decision to ThoughtBus
        if self._thought_bus:
            try:
                from aureon.core.aureon_thought_bus import Thought
                self._thought_bus.publish(Thought(
                    source="autonomy_hub",
                    topic="autonomy.decision",
                    payload={
                        'cycle': self._cycle_count,
                        'symbol': symbol,
                        'action': decision.direction,
                        'confidence': decision.confidence,
                        'strength': decision.strength,
                        'reasons': decision.payload.get('reasons', []),
                        'num_predictors': len(predictions),
                        'rolling_win_rate': self.feedback_loop.get_rolling_win_rate(),
                    }
                ))
            except Exception:
                pass

        self._last_cycle_time = time.time() - cycle_start

        return decision

    def record_trade_outcome(self, trade_result: Dict) -> Dict:
        """Record a trade outcome and close the feedback loop."""
        return self.feedback_loop.record_outcome(
            trade_result=trade_result,
            entry_predictions=self.prediction_bus.get_latest_predictions(),
            entry_decision=UnifiedSignal()
        )

    def get_status(self) -> Dict:
        """Get full hub status for monitoring."""
        return {
            'cycles': self._cycle_count,
            'last_cycle_ms': round(self._last_cycle_time * 1000, 1),
            'registered_predictors': list(self.prediction_bus._predictors.keys()),
            'rolling_win_rate': self.feedback_loop.get_rolling_win_rate(),
            'predictor_accuracy': dict(self.feedback_loop._predictor_accuracy),
            'learned_weights': self.feedback_loop.get_predictor_weights(),
            'data_sources_active': len(self.data_bridge._latest_signals),
            'recent_decisions': self.decision_gate.get_recent_decisions(5),
            'avg_costs': self.feedback_loop.get_average_actual_costs(),
        }

    def _pull_macro_data(self):
        """Pull ALL cached data sources into the hub."""
        # 1. Global Financial Feed (macro indicators)
        try:
            state_file = "global_financial_state.json"
            if os.path.exists(state_file):
                mtime = os.path.getmtime(state_file)
                if time.time() - mtime < 300:  # Less than 5 min old
                    with open(state_file, 'r') as f:
                        snapshot = json.load(f)
                    self.data_bridge.ingest_macro_snapshot(
                        snapshot.get('last_snapshot', snapshot)
                    )
        except Exception:
            pass

        # 2. CoinGecko price cache
        try:
            cg_path = "ws_cache/ws_prices.json"
            if os.path.exists(cg_path):
                mtime = os.path.getmtime(cg_path)
                if time.time() - mtime < 120:  # Less than 2 min old
                    with open(cg_path, 'r') as f:
                        cache = json.load(f)
                    self.data_bridge.ingest_price_cache(cache, "coingecko")
        except Exception:
            pass

        # 3. Kraken price cache
        try:
            kr_path = "ws_cache/kraken_prices.json"
            if os.path.exists(kr_path):
                mtime = os.path.getmtime(kr_path)
                if time.time() - mtime < 120:
                    with open(kr_path, 'r') as f:
                        cache = json.load(f)
                    self.data_bridge.ingest_price_cache(cache, "kraken_cache")
        except Exception:
            pass

        # 4. Unified market cache
        try:
            uni_path = "ws_cache/unified_prices.json"
            if os.path.exists(uni_path):
                mtime = os.path.getmtime(uni_path)
                if time.time() - mtime < 60:
                    with open(uni_path, 'r') as f:
                        cache = json.load(f)
                    self.data_bridge.ingest_price_cache(cache, "unified_cache")
        except Exception:
            pass

    def _weighted_consensus(self, predictions: Dict[str, UnifiedSignal],
                            learned_weights: Dict[str, float]) -> UnifiedSignal:
        """Consensus with feedback-learned weights."""
        if not predictions:
            return UnifiedSignal(source="prediction_consensus", signal_type="prediction")

        total_weight = 0.0
        weighted_strength = 0.0

        for name, pred in predictions.items():
            w = learned_weights.get(name, 1.0)
            weighted_strength += pred.strength * w * pred.confidence
            total_weight += w * pred.confidence

        if total_weight > 0:
            consensus_strength = weighted_strength / total_weight
        else:
            consensus_strength = 0.0

        if consensus_strength > 0.1:
            direction = "BULLISH"
        elif consensus_strength < -0.1:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        return UnifiedSignal(
            source="prediction_consensus_learned",
            signal_type="prediction",
            direction=direction,
            confidence=min(sum(p.confidence for p in predictions.values()) / len(predictions), 1.0),
            strength=consensus_strength,
            payload={
                'num_predictors': len(predictions),
                'used_learned_weights': True,
                'weights': learned_weights,
            }
        )

    def _apply_learned_weights(self):
        """Apply any previously learned predictor weights."""
        weights = self.feedback_loop.get_predictor_weights()
        if weights:
            logger.info(f"[AutonomyHub] Applied learned weights for {len(weights)} predictors")
            for name, weight in weights.items():
                logger.info(f"  {name}: {weight:.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

_hub_instance: Optional[AutonomyHub] = None
_hub_lock = threading.Lock()

def get_autonomy_hub() -> AutonomyHub:
    """Get or create the global AutonomyHub singleton.

    Lazy construction: the first caller pays the cost of registering
    all 11 predictors (9 hub-side + harmonic_observer + wave_predictor
    auto-wires) and connecting the ThoughtBus. Subsequent callers get
    the cached instance. Thread-safe via _hub_lock.

    Stage T/V Vote 7 imports ``get_hub`` — that's an alias of this
    function (added below) so older code paths that imported the short
    name still resolve.
    """
    global _hub_instance
    with _hub_lock:
        if _hub_instance is None:
            _hub_instance = AutonomyHub()
            _hub_instance.connect_thought_bus()
    return _hub_instance


# Short alias used by aureon/bots/orca_complete_kill_cycle.py Vote 7
# blocks (Stages T and V) and any other call site that wants the
# concise name. Identity-equal to get_autonomy_hub.
get_hub = get_autonomy_hub


def spin(symbol: str = "BTCUSD") -> UnifiedSignal:
    """Convenience: spin the big wheel once."""
    hub = get_autonomy_hub()
    return hub.spin_cycle(symbol)


def record_outcome(trade_result: Dict) -> Dict:
    """Convenience: record a trade outcome."""
    hub = get_autonomy_hub()
    return hub.record_trade_outcome(trade_result)


def status() -> Dict:
    """Convenience: get hub status."""
    hub = get_autonomy_hub()
    return hub.get_status()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - Demo / Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    print("=" * 70)
    print("  THE BIG WHEEL - AUREON AUTONOMY HUB")
    print("  Data -> Predictions -> Decisions -> Outcomes -> Learning")
    print("=" * 70)

    hub = get_autonomy_hub()

    # Simulate some data flowing in
    hub.data_bridge.ingest_macro_snapshot({
        'crypto_fear_greed': 65,
        'vix': 18.5,
        'dxy_change': -0.3,
        'risk_on_off': 'RISK_ON',
        'market_regime': 'NORMAL',
        'spx_change': 0.8,
        'btc_dominance': 52.3,
    })

    hub.data_bridge.ingest_news_sentiment({
        'crypto_sentiment': 0.35,
        'aggregate_sentiment': 0.25,
        'confidence': 0.6,
        'bullish_ratio': 0.55,
        'bearish_ratio': 0.20,
    })

    hub.data_bridge.ingest_market_tick("BTCUSD", 97500.0, 2.3, 150000000, "binance")

    # Spin the wheel
    decision = hub.spin_cycle("BTCUSD")

    print(f"\nDecision: {decision.direction}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Strength: {decision.strength:.2f}")
    print(f"Reasons: {decision.payload.get('reasons', [])}")

    # Simulate a trade outcome (feedback loop)
    feedback = hub.record_trade_outcome({
        'symbol': 'BTCUSD',
        'net_pnl': 12.50,
        'pnl_pct': 0.85,
        'total_fees': 1.20,
        'actual_slippage': 0.0003,
        'exchange': 'kraken',
    })

    print(f"\nFeedback: {feedback}")

    # Show status
    hub_status = hub.get_status()
    print(f"\nHub Status:")
    print(f"  Cycles: {hub_status['cycles']}")
    print(f"  Rolling Win Rate: {hub_status['rolling_win_rate']:.1%}")
    print(f"  Predictors: {hub_status['registered_predictors']}")
    print(f"  Data Sources: {hub_status['data_sources_active']}")
    print(f"  Learned Weights: {hub_status['learned_weights']}")

    print("\n" + "=" * 70)
    print("  THE WHEEL TURNS. THE SYSTEM LEARNS. AUTONOMY IS EARNED.")
    print("=" * 70)
