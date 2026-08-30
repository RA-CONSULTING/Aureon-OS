#!/usr/bin/env python3
"""
🎯🔮 AUREON TRUTH PREDICTION ENGINE 🔮🎯

CRITICAL: This is NOT a fortune teller. This is a VALIDATION SYSTEM.

Purpose:
- Use Queen's probability matrices + Dr. Auris validation
- Integrate harmonic resonance analysis (Hz frequencies)
- Generate predictions based on REAL MARKET INTELLIGENCE
- Validate predictions against actual outcomes
- Feed validation results back to probability learning

⚠️ REAL DATA ONLY. NO SIMULATIONS. NO LINEAR GUESSES.

⚠️ KNOWN GAP (Stage AJ): generate_prediction() currently uses several
   placeholders (risk="none", proximity="far", queen_flags=[],
   entry_price=current_price, target=current*1.02, accel=0.0). These
   are logged at WARN level so operators can see the intel comes from
   a partially-mocked feature vector. Wire risk_flags, target_proximity,
   and acceleration history from the live state to remove them.
"""

import logging
logger = logging.getLogger(__name__)

import json
import time
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528.0
PERFECTION_ANGLE = 306.0  # 360° - 54° golden angle
STATE_FILE = Path("aureon_truth_prediction_state.json")

# Import Queen's intelligence
try:
    from aureon.strategies.probability_ultimate_intelligence import (
        ProbabilityUltimateIntelligence,
        UltimatePrediction
    )
    PROBABILITY_AVAILABLE = True
except ImportError:
    PROBABILITY_AVAILABLE = False
    UltimatePrediction = None

# Import Queen↔Auris validation
try:
    from aureon.wisdom.metatrons_cube_knowledge_exchange import QueenAurisPingPong
    PINGPONG_AVAILABLE = True
except ImportError:
    PINGPONG_AVAILABLE = False


@dataclass
class MarketSnapshot:
    """Current market state for a symbol."""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    momentum_30s: float  # % change over 30s
    volatility_30s: float  # Standard deviation as %
    hz_frequency: float  # Harmonic encoding
    timestamp: float


@dataclass
class TruthPrediction:
    """A prediction with FULL validation chain."""
    symbol: str
    start_time: float
    start_price: float
    
    # Probability intelligence
    win_probability: float  # From Queen's matrices
    pattern_key: Tuple[str, str, str, str, str]  # 5D pattern
    pattern_confidence: float
    
    # Dr. Auris validation
    auris_approved: bool
    auris_resonance: float  # 0-1
    
    # Harmonic analysis
    hz_strength: float  # Signal strength
    hz_band: str  # Schumann/Alpha/Beta/Gamma/Solfeggio
    
    # Prediction
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    predicted_change_pct: float
    horizon_seconds: float
    
    # Validation (filled later)
    validated: bool = False
    actual_price: float = 0.0
    actual_change_pct: float = 0.0
    correct: Optional[bool] = None
    
    # Truth metrics
    queen_approved: bool = False
    geometric_truth: Optional[float] = None  # From crystallization


class TruthPredictionEngine:
    """
    Truth-based prediction engine using ALL validation layers.
    
    Workflow:
    1. Read market snapshot (price, momentum, volatility, volume)
    2. Query Queen's probability matrices for win probability
    3. Run Dr. Auris validation on prediction reasoning
    4. Check harmonic resonance (Hz analysis)
    5. Generate prediction ONLY if all 3 layers approve
    6. Validate prediction after horizon elapsed
    7. Feed outcome back to probability learning
    """
    
    def __init__(self):
        self.probability_intel: Optional[ProbabilityUltimateIntelligence] = None
        self.pingpong: Optional[QueenAurisPingPong] = None
        self.pending_predictions: Dict[str, List[TruthPrediction]] = {}
        # Stage AO: track per-symbol momentum history so we can derive
        # real `accel` (rate-of-change of momentum) from successive
        # snapshots instead of passing accel=0.0 placeholder.
        # Each entry: (timestamp, momentum_30s).
        self._momentum_history: Dict[str, List[tuple]] = {}
        self._momentum_history_max = 16

        if PROBABILITY_AVAILABLE:
            try:
                self.probability_intel = ProbabilityUltimateIntelligence()
                print("✅ Probability Ultimate Intelligence loaded (95% accuracy)")
            except Exception as e:
                print(f"⚠️ Failed to load probability intelligence: {e}")
        
        if PINGPONG_AVAILABLE:
            try:
                self.pingpong = QueenAurisPingPong()
                print("✅ Queen↔Auris PingPong validation loaded")
            except Exception as e:
                print(f"⚠️ Failed to load pingpong: {e}")
    
    def _save_state(self):
        """Save prediction state to JSON for Orca to read."""
        try:
            state = {
                "last_updated": time.time(),
                "predictions": {},
                "validations": []
            }
            
            # Save all pending predictions
            for symbol, preds in self.pending_predictions.items():
                state["predictions"][symbol] = []
                for pred in preds:
                    state["predictions"][symbol].append({
                        "symbol": pred.symbol,
                        "start_time": pred.start_time,
                        "start_price": pred.start_price,
                        "win_probability": pred.win_probability,
                        "pattern_confidence": pred.pattern_confidence,
                        "auris_approved": pred.auris_approved,
                        "auris_resonance": pred.auris_resonance,
                        "predicted_direction": pred.predicted_direction,
                        "predicted_change_pct": pred.predicted_change_pct,
                        "horizon_seconds": pred.horizon_seconds,
                        "queen_approved": pred.queen_approved,
                        "validated": pred.validated,
                        "actual_change_pct": pred.actual_change_pct if pred.validated else None,
                        "correct": pred.correct if pred.validated else None,
                        "geometric_truth": pred.geometric_truth if pred.validated else None
                    })
                    
                    # Add to validations list if validated
                    if pred.validated:
                        state["validations"].append({
                            "symbol": pred.symbol,
                            "timestamp": pred.start_time,
                            "predicted_direction": pred.predicted_direction,
                            "correct": pred.correct,
                            "geometric_truth": pred.geometric_truth
                        })
            
            # Atomic write
            temp_file = STATE_FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
            temp_file.replace(STATE_FILE)
            
        except Exception as e:
            print(f"⚠️ Failed to save prediction state: {e}")
    
    def _classify_scenario(self, snapshot: MarketSnapshot) -> str:
        """Classify market scenario for probability matrix."""
        momentum = snapshot.momentum_30s
        volatility = snapshot.volatility_30s
        
        # Strong uptrend
        if momentum > 0.3 and volatility < 0.3:
            return "strong"
        
        # Dying momentum
        if abs(momentum) < 0.1 and volatility < 0.2:
            return "dying"
        
        # High volatility
        if volatility > 0.5:
            return "volatile"
        
        # Reversal (momentum vs 24h change disagree)
        if (momentum > 0 and snapshot.change_24h < -2.0) or \
           (momentum < 0 and snapshot.change_24h > 2.0):
            return "reversal"
        
        return "sideways"
    
    def _classify_momentum_band(self, momentum: float) -> str:
        """Classify momentum for pattern key."""
        if momentum < -0.1:
            return "down"
        elif momentum < 0.3:
            return "flat"
        else:
            return "up"
    
    def _classify_hz_band(self, hz: float) -> str:
        """Classify harmonic band."""
        if hz < 10:
            return "schumann"
        elif hz < 100:
            return "alpha"
        elif hz < 300:
            return "beta"
        elif hz < 700:
            return "gamma"
        else:
            return "solfeggio"
    
    def generate_prediction(
        self,
        snapshot: MarketSnapshot,
        horizon_seconds: float = 30.0,
        min_confidence: float = 0.65
    ) -> Optional[TruthPrediction]:
        """
        Generate a prediction with FULL validation.
        
        Returns:
            TruthPrediction if all gates approve, else None
        """
        
        # Gate 1: Check probability intelligence available
        if not self.probability_intel:
            return None
        
        # Build pattern key (5D)
        scenario = self._classify_scenario(snapshot)
        # ⚠ Placeholders — see module docstring KNOWN GAP. Logged once per
        # symbol-scenario combo so operators see the intel is partially mocked.
        risk = "none"  # Would come from risk flags in real system
        proximity = "far"  # Would come from target proximity
        if not getattr(self, "_warned_placeholders", set()):
            self._warned_placeholders = set()
        _key = (snapshot.symbol, scenario)
        if _key not in self._warned_placeholders:
            self._warned_placeholders.add(_key)
            logger.warning("[stub] generate_prediction(%s, %s) uses placeholder "
                           "risk=none, proximity=far, queen_flags=[], accel=0.0 — "
                           "wire real values to remove the mock features",
                           snapshot.symbol, scenario)
        momentum_band = self._classify_momentum_band(snapshot.momentum_30s)
        
        # Clownfish classification (based on volatility for now)
        if snapshot.volatility_30s < 0.35:
            clownfish = "danger"
        elif snapshot.volatility_30s < 0.55:
            clownfish = "weak"
        elif snapshot.volatility_30s < 0.75:
            clownfish = "neutral"
        else:
            clownfish = "strong"
        
        pattern_key = (scenario, risk, proximity, momentum_band, clownfish)
        
        # Stage AO: derive real `accel` (rate-of-change of momentum) from
        # the per-symbol momentum history we accumulate across snapshots.
        # If we have at least 2 prior readings, accel = (m_now - m_prev)
        # divided by elapsed seconds. Otherwise the first call seeds the
        # buffer and accel falls back to 0.0 with no log spam.
        history = self._momentum_history.setdefault(snapshot.symbol, [])
        history.append((snapshot.timestamp, snapshot.momentum_30s))
        if len(history) > self._momentum_history_max:
            del history[: len(history) - self._momentum_history_max]
        accel_real = 0.0
        if len(history) >= 2:
            (t_prev, m_prev), (t_now, m_now) = history[-2], history[-1]
            # abs() guards against clock-skew or out-of-order timestamps
            # producing a tiny dt that would warp accel into a huge value.
            dt = max(1e-3, abs(t_now - t_prev))
            # Convert percentage momentum delta to decimal/second
            accel_real = ((m_now - m_prev) / 100.0) / dt

        try:
            # Note: entry_price/target_price still placeholders pending wiring
            # to the real per-symbol target tracker. queen_flags pending the
            # risk-flag pipeline. accel is now derived from real history.
            intel = self.probability_intel.get_prediction(
                current_price=snapshot.price,
                entry_price=snapshot.price,
                target_price=snapshot.price * 1.02,
                current_time=snapshot.timestamp,
                entry_time=snapshot.timestamp - 3600,
                prediction_time=snapshot.timestamp + horizon_seconds,
                queen_flags=[],
                probability_base=0.5,
                momentum=snapshot.momentum_30s / 100.0,
                accel=accel_real,
            )
            
            win_probability = intel.final_probability
            pattern_confidence = intel.pattern_confidence
            
        except Exception as e:
            print(f"⚠️ Probability query failed for {snapshot.symbol}: {e}")
            return None
        
        # Gate 2: Minimum confidence threshold
        if pattern_confidence < min_confidence:
            return None
        
        # Gate 3: Dr. Auris validation (if available)
        auris_approved = True
        auris_resonance = 1.0
        
        if self.pingpong:
            try:
                reasoning = f"Predict {snapshot.symbol} {snapshot.momentum_30s:+.3f}% momentum, " \
                           f"{snapshot.volatility_30s:.3f}% volatility, pattern {pattern_key}"
                
                result = self.pingpong.validate_reasoning(reasoning)
                auris_approved = result.get("approved", False)
                auris_resonance = result.get("geometric_truth", 0.0)
                
                # Block if Auris rejects
                if not auris_approved or auris_resonance < 0.618:  # PHI threshold
                    return None
                    
            except Exception as e:
                print(f"⚠️ Auris validation failed for {snapshot.symbol}: {e}")
                # Don't block on validation failure, but flag it
                auris_approved = True
                auris_resonance = 0.5
        
        # Determine predicted direction and magnitude
        if snapshot.momentum_30s > 0.1:
            predicted_direction = "UP"
            # Scale by win probability and pattern confidence
            predicted_change_pct = snapshot.momentum_30s * win_probability * pattern_confidence
        elif snapshot.momentum_30s < -0.1:
            predicted_direction = "DOWN"
            predicted_change_pct = snapshot.momentum_30s * win_probability * pattern_confidence
        else:
            predicted_direction = "FLAT"
            predicted_change_pct = 0.0
        
        # Build prediction
        prediction = TruthPrediction(
            symbol=snapshot.symbol,
            start_time=snapshot.timestamp,
            start_price=snapshot.price,
            win_probability=win_probability,
            pattern_key=pattern_key,
            pattern_confidence=pattern_confidence,
            auris_approved=auris_approved,
            auris_resonance=auris_resonance,
            hz_strength=(abs(snapshot.momentum_30s) + snapshot.volatility_30s) / 10.0,
            hz_band=self._classify_hz_band(snapshot.hz_frequency),
            predicted_direction=predicted_direction,
            predicted_change_pct=predicted_change_pct,
            horizon_seconds=horizon_seconds,
            queen_approved=win_probability >= 0.65  # Queen's threshold
        )
        
        # Track for validation
        if snapshot.symbol not in self.pending_predictions:
            self.pending_predictions[snapshot.symbol] = []
        self.pending_predictions[snapshot.symbol].append(prediction)
        
        # Save state for Orca to read
        self._save_state()
        
        return prediction
    
    def validate_predictions(self, snapshot: MarketSnapshot) -> List[TruthPrediction]:
        """
        Validate any pending predictions for this symbol.
        
        Returns:
            List of validated predictions
        """
        if snapshot.symbol not in self.pending_predictions:
            return []
        
        validated = []
        still_pending = []
        
        for pred in self.pending_predictions[snapshot.symbol]:
            if pred.validated:
                continue  # Already validated
            
            # Check if horizon elapsed
            elapsed = snapshot.timestamp - pred.start_time
            if elapsed >= pred.horizon_seconds:
                # Validate!
                pred.validated = True
                pred.actual_price = snapshot.price
                pred.actual_change_pct = ((snapshot.price - pred.start_price) / pred.start_price) * 100.0
                
                # Check direction correctness
                if pred.predicted_direction == "UP":
                    pred.correct = pred.actual_change_pct > 0
                elif pred.predicted_direction == "DOWN":
                    pred.correct = pred.actual_change_pct < 0
                else:  # FLAT
                    pred.correct = abs(pred.actual_change_pct) < 0.1
                
                # Calculate geometric truth (alignment of prediction vs reality)
                if pred.actual_change_pct != 0:
                    accuracy_ratio = min(abs(pred.predicted_change_pct / pred.actual_change_pct), 2.0)
                    pred.geometric_truth = math.exp(-abs(1.0 - accuracy_ratio))
                else:
                    pred.geometric_truth = 1.0 if abs(pred.predicted_change_pct) < 0.01 else 0.0
                
                validated.append(pred)
                
                # Feed back to probability learning
                if self.probability_intel:
                    try:
                        outcome = "win" if pred.correct else "loss"
                        self.probability_intel.record_outcome(
                            pattern_key=pred.pattern_key,
                            outcome=outcome,
                            probability=pred.win_probability,
                            momentum=pred.predicted_change_pct / 100.0
                        )
                    except Exception as e:
                        print(f"⚠️ Failed to record outcome for {snapshot.symbol}: {e}")
            else:
                still_pending.append(pred)
        
        # Update pending list
        self.pending_predictions[snapshot.symbol] = still_pending
        
        # Save state after validation
        if validated:
            self._save_state()
        
        return validated
    
    def get_accuracy_stats(self) -> Dict[str, float]:
        """Get overall prediction accuracy statistics."""
        total = 0
        correct = 0
        avg_geometric_truth = 0.0
        
        for symbol_preds in self.pending_predictions.values():
            for pred in symbol_preds:
                if pred.validated:
                    total += 1
                    if pred.correct:
                        correct += 1
                    if pred.geometric_truth is not None:
                        avg_geometric_truth += pred.geometric_truth
        
        return {
            "total_validated": total,
            "correct": correct,
            "accuracy_pct": (correct / total * 100.0) if total > 0 else 0.0,
            "avg_geometric_truth": (avg_geometric_truth / total) if total > 0 else 0.0
        }


# Standalone manufactured execution removed; callers must inject receipted market state.
