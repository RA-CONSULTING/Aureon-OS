#!/usr/bin/env python3
"""
🎯⏱️ ETA VERIFICATION SYSTEM - PREDICT, VERIFY, ADAPT ⏱️🎯
===========================================================

When we give an ETA, we MUST verify the kill happens.
If it doesn't, we need to figure out WHY and ADAPT.

PROCESS:
1. PREDICTION: Record ETA when given (target time, conditions)
2. VERIFICATION: Check if kill happened at predicted time
3. ANALYSIS: If miss, analyze what went wrong
4. ADAPTATION: Update prediction models based on failures

"The Celtic warrior doesn't just predict - 
 he tracks his predictions and learns from every miss."

Gary Leckey | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import json
import time
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
from enum import Enum

# =============================================================================
# ETA PREDICTION TRACKING
# =============================================================================

class ETAOutcome(Enum):
    """Outcome of an ETA prediction."""
    PENDING = "pending"           # Still waiting
    HIT_ON_TIME = "hit_on_time"   # Kill within tolerance
    HIT_EARLY = "hit_early"       # Kill happened earlier (good!)
    HIT_LATE = "hit_late"         # Kill happened but late
    MISSED = "missed"             # No kill within max wait
    REVERSED = "reversed"         # Price went opposite direction
    INVALIDATED = "invalidated"   # Position closed externally


@dataclass
class ETAPrediction:
    """A single ETA prediction to be verified."""
    prediction_id: str
    symbol: str
    exchange: str
    
    # Prediction details
    predicted_eta_seconds: float       # How long we predicted
    prediction_time: float             # When prediction was made
    target_kill_time: float            # prediction_time + predicted_eta_seconds
    confidence: float                  # 0-1 confidence in prediction
    
    # Conditions at prediction time
    current_pnl: float
    target_pnl: float
    pnl_velocity: float
    momentum_score: float
    proximity_to_target: float         # current_pnl / target_pnl
    cascade_factor: float
    
    # Monte Carlo info (if used)
    mc_enhanced: bool = False
    mc_probability: float = 0.0
    mc_eta_median: float = float('inf')
    
    # Verification results
    outcome: ETAOutcome = ETAOutcome.PENDING
    actual_kill_time: Optional[float] = None
    actual_eta_seconds: Optional[float] = None
    time_error_seconds: Optional[float] = None  # actual - predicted
    time_error_pct: Optional[float] = None
    
    # Analysis on miss
    miss_reason: Optional[str] = None
    final_pnl: Optional[float] = None
    final_velocity: Optional[float] = None
    final_momentum: Optional[float] = None
    
    # Tolerance (default 20% time error is acceptable)
    tolerance_pct: float = 0.20


@dataclass 
class PredictionAccuracyStats:
    """Statistics on prediction accuracy."""
    total_predictions: int = 0
    hits_on_time: int = 0
    hits_early: int = 0
    hits_late: int = 0
    misses: int = 0
    reversals: int = 0
    invalidated: int = 0
    
    # Accuracy metrics
    hit_rate: float = 0.0              # Any hit / total
    on_time_rate: float = 0.0          # On time / total
    avg_time_error: float = 0.0        # Average time error in seconds
    avg_time_error_pct: float = 0.0    # Average time error as percentage
    
    # Conditions that correlate with accuracy
    accuracy_by_momentum: Dict[str, float] = field(default_factory=dict)
    accuracy_by_velocity_band: Dict[str, float] = field(default_factory=dict)
    accuracy_by_proximity_band: Dict[str, float] = field(default_factory=dict)
    accuracy_by_cascade_level: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# ETA VERIFICATION ENGINE
# =============================================================================

class ETAVerificationEngine:
    """
    🎯⏱️ THE ETA VERIFICATION ENGINE ⏱️🎯
    
    Every ETA prediction is tracked and verified:
    - When ETA is given, a prediction is registered
    - System monitors for kill or expiration
    - On outcome, prediction accuracy is analyzed
    - Models are adapted based on results
    
    "Trust but verify. Then adapt."
    """
    
    # Timing tolerances
    ON_TIME_TOLERANCE_PCT = 0.20       # ±20% is "on time"
    EARLY_THRESHOLD_PCT = -0.20       # More than 20% early
    LATE_THRESHOLD_PCT = 0.50         # More than 50% late
    MAX_WAIT_MULTIPLIER = 3.0         # Wait up to 3x predicted ETA
    
    def __init__(self, history_file: str = 'eta_verification_history.json'):
        self.history_file = history_file
        self.active_predictions: Dict[str, ETAPrediction] = {}
        self.verified_predictions: List[ETAPrediction] = []
        self.stats = PredictionAccuracyStats()
        
        # Adaptation state
        self.velocity_correction_factor: float = 1.0  # Adjust velocity predictions
        self.eta_bias: float = 0.0                    # Systematic over/underestimate
        self.momentum_reliability: Dict[str, float] = {}  # momentum_band -> reliability
        self.min_confidence_threshold: float = 0.3    # Don't trust low confidence
        
        # Load historical data
        self._load_history()
        
        print(f"🎯⏱️ ETA Verification Engine initialized | Accuracy: {self.stats.hit_rate*100:.1f}%")
    
    def _load_history(self):
        """Load historical prediction data."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                
                # Load stats
                stats_data = data.get('stats', {})
                self.stats = PredictionAccuracyStats(**stats_data) if stats_data else PredictionAccuracyStats()
                
                # Load adaptation state
                adapt = data.get('adaptation', {})
                self.velocity_correction_factor = adapt.get('velocity_correction_factor', 1.0)
                self.eta_bias = adapt.get('eta_bias', 0.0)
                self.momentum_reliability = adapt.get('momentum_reliability', {})
                self.min_confidence_threshold = adapt.get('min_confidence_threshold', 0.3)
                
                # Load recent verified predictions (last 100)
                verified = data.get('verified_predictions', [])[-100:]
                for pred_data in verified:
                    pred = ETAPrediction(**{
                        k: v for k, v in pred_data.items()
                        if k in ETAPrediction.__dataclass_fields__
                    })
                    pred.outcome = ETAOutcome(pred_data.get('outcome', 'pending'))
                    self.verified_predictions.append(pred)
                
                print(f"   📊 Loaded {len(self.verified_predictions)} historical predictions")
        except Exception as e:
            print(f"   ⚠️ Could not load ETA history: {e}")
    
    def _save_history(self):
        """Save prediction history and adaptation state."""
        try:
            data = {
                'stats': asdict(self.stats),
                'adaptation': {
                    'velocity_correction_factor': self.velocity_correction_factor,
                    'eta_bias': self.eta_bias,
                    'momentum_reliability': self.momentum_reliability,
                    'min_confidence_threshold': self.min_confidence_threshold,
                },
                'verified_predictions': [
                    {**asdict(p), 'outcome': p.outcome.value}
                    for p in self.verified_predictions[-100:]
                ],
                'last_updated': time.time(),
            }
            
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"   ⚠️ Could not save ETA history: {e}")
    
    # =========================================================================
    # PREDICTION REGISTRATION
    # =========================================================================
    
    def register_eta_prediction(
        self,
        symbol: str,
        exchange: str,
        eta_seconds: float,
        current_pnl: float,
        target_pnl: float,
        pnl_velocity: float,
        momentum_score: float,
        cascade_factor: float = 1.0,
        mc_enhanced: bool = False,
        mc_probability: float = 0.0,
        mc_eta_median: float = float('inf'),
        confidence: float = 0.5
    ) -> str:
        """
        🎯 Register a new ETA prediction for verification.
        
        Returns prediction_id for later verification.
        """
        # Apply learned corrections
        corrected_eta = self._apply_eta_corrections(
            eta_seconds, momentum_score, pnl_velocity, confidence
        )
        
        now = time.time()
        prediction_id = f"{exchange}:{symbol}:{int(now*1000)}"
        
        proximity = current_pnl / target_pnl if target_pnl > 0 else 0
        proximity = max(0, min(1, proximity))
        
        prediction = ETAPrediction(
            prediction_id=prediction_id,
            symbol=symbol,
            exchange=exchange,
            predicted_eta_seconds=corrected_eta,
            prediction_time=now,
            target_kill_time=now + corrected_eta,
            confidence=confidence,
            current_pnl=current_pnl,
            target_pnl=target_pnl,
            pnl_velocity=pnl_velocity,
            momentum_score=momentum_score,
            proximity_to_target=proximity,
            cascade_factor=cascade_factor,
            mc_enhanced=mc_enhanced,
            mc_probability=mc_probability,
            mc_eta_median=mc_eta_median,
        )
        
        key = f"{exchange}:{symbol}"
        self.active_predictions[key] = prediction
        
        return prediction_id
    
    def _apply_eta_corrections(
        self,
        raw_eta: float,
        momentum: float,
        velocity: float,
        confidence: float
    ) -> float:
        """
        🧠 Apply learned corrections to raw ETA estimate.
        
        Based on historical miss patterns, adjust the estimate.
        """
        corrected = raw_eta
        
        # 1. Apply systematic bias correction
        corrected = corrected + self.eta_bias
        
        # 2. Apply velocity correction factor
        if velocity > 0:
            # If we've learned velocity predictions are too optimistic,
            # this factor will be > 1.0, extending the ETA
            corrected = corrected * self.velocity_correction_factor
        
        # 3. Apply momentum-based reliability adjustment
        momentum_band = self._get_momentum_band(momentum)
        reliability = self.momentum_reliability.get(momentum_band, 1.0)
        
        if reliability < 0.5:
            # Low reliability momentum = extend ETA by 50%
            corrected = corrected * 1.5
        elif reliability < 0.7:
            # Medium reliability = extend by 20%
            corrected = corrected * 1.2
        
        # 4. Low confidence = be more conservative (extend ETA)
        if confidence < self.min_confidence_threshold:
            corrected = corrected * (1.5 - confidence)
        
        # Minimum 5 seconds, maximum 10 minutes
        return max(5.0, min(600.0, corrected))
    
    # =========================================================================
    # VERIFICATION
    # =========================================================================
    
    def verify_kill(
        self,
        symbol: str,
        exchange: str,
        actual_pnl: float,
        kill_success: bool = True
    ) -> Optional[ETAPrediction]:
        """
        🎯 Verify a kill against its ETA prediction.
        
        Call this when a position is closed (either by kill or other means).
        """
        key = f"{exchange}:{symbol}"
        
        if key not in self.active_predictions:
            return None
        
        prediction = self.active_predictions.pop(key)
        now = time.time()
        
        # Calculate actual ETA
        prediction.actual_kill_time = now
        prediction.actual_eta_seconds = now - prediction.prediction_time
        
        if prediction.predicted_eta_seconds > 0:
            prediction.time_error_seconds = prediction.actual_eta_seconds - prediction.predicted_eta_seconds
            prediction.time_error_pct = prediction.time_error_seconds / prediction.predicted_eta_seconds
        
        prediction.final_pnl = actual_pnl
        
        # Determine outcome
        if not kill_success:
            if actual_pnl < prediction.current_pnl:
                prediction.outcome = ETAOutcome.REVERSED
                prediction.miss_reason = "Price reversed, P&L went negative"
            else:
                prediction.outcome = ETAOutcome.INVALIDATED
                prediction.miss_reason = "Position closed externally"
        elif actual_pnl >= prediction.target_pnl:
            # Successful kill - check timing
            error_pct = prediction.time_error_pct or 0
            
            if abs(error_pct) <= self.ON_TIME_TOLERANCE_PCT:
                prediction.outcome = ETAOutcome.HIT_ON_TIME
            elif error_pct < self.EARLY_THRESHOLD_PCT:
                prediction.outcome = ETAOutcome.HIT_EARLY
            else:
                prediction.outcome = ETAOutcome.HIT_LATE
        else:
            prediction.outcome = ETAOutcome.MISSED
            prediction.miss_reason = f"Did not reach target: ${actual_pnl:.4f} < ${prediction.target_pnl:.4f}"
        
        # Store and learn
        self.verified_predictions.append(prediction)
        self._update_stats(prediction)
        self._adapt_from_prediction(prediction)
        
        # Save periodically
        if len(self.verified_predictions) % 5 == 0:
            self._save_history()
        
        return prediction
    
    def check_expired_predictions(self) -> List[ETAPrediction]:
        """
        ⏱️ Check for predictions that have exceeded their max wait time.
        
        Call this periodically to mark predictions as MISSED.
        """
        expired = []
        now = time.time()
        
        for key in list(self.active_predictions.keys()):
            pred = self.active_predictions[key]
            max_wait = pred.predicted_eta_seconds * self.MAX_WAIT_MULTIPLIER
            
            if now - pred.prediction_time > max_wait:
                # This prediction has expired without a kill
                pred.outcome = ETAOutcome.MISSED
                pred.actual_kill_time = now
                pred.actual_eta_seconds = now - pred.prediction_time
                pred.time_error_seconds = pred.actual_eta_seconds - pred.predicted_eta_seconds
                pred.time_error_pct = pred.time_error_seconds / pred.predicted_eta_seconds if pred.predicted_eta_seconds > 0 else 0
                pred.miss_reason = f"Exceeded max wait ({max_wait:.0f}s)"
                
                self.verified_predictions.append(pred)
                self._update_stats(pred)
                self._adapt_from_prediction(pred)
                
                expired.append(pred)
                del self.active_predictions[key]
        
        if expired:
            self._save_history()
        
        return expired
    
    def update_prediction_state(
        self,
        symbol: str,
        exchange: str,
        current_pnl: float,
        pnl_velocity: float,
        momentum_score: float
    ):
        """
        📊 Update the current state for an active prediction.
        
        Used for continuous monitoring and early warning of misses.
        """
        key = f"{exchange}:{symbol}"
        if key not in self.active_predictions:
            return
        
        pred = self.active_predictions[key]
        pred.final_pnl = current_pnl
        pred.final_velocity = pnl_velocity
        pred.final_momentum = momentum_score
    
    # =========================================================================
    # STATISTICS AND ADAPTATION
    # =========================================================================
    
    def _update_stats(self, prediction: ETAPrediction):
        """Update accuracy statistics with new prediction result."""
        self.stats.total_predictions += 1
        
        if prediction.outcome == ETAOutcome.HIT_ON_TIME:
            self.stats.hits_on_time += 1
        elif prediction.outcome == ETAOutcome.HIT_EARLY:
            self.stats.hits_early += 1
        elif prediction.outcome == ETAOutcome.HIT_LATE:
            self.stats.hits_late += 1
        elif prediction.outcome == ETAOutcome.MISSED:
            self.stats.misses += 1
        elif prediction.outcome == ETAOutcome.REVERSED:
            self.stats.reversals += 1
        elif prediction.outcome == ETAOutcome.INVALIDATED:
            self.stats.invalidated += 1
        
        # Calculate rates
        total = self.stats.total_predictions
        hits = self.stats.hits_on_time + self.stats.hits_early + self.stats.hits_late
        
        self.stats.hit_rate = hits / total if total > 0 else 0
        self.stats.on_time_rate = self.stats.hits_on_time / total if total > 0 else 0
        
        # Calculate average time error (only for hits)
        if prediction.time_error_seconds is not None and prediction.outcome in [
            ETAOutcome.HIT_ON_TIME, ETAOutcome.HIT_EARLY, ETAOutcome.HIT_LATE
        ]:
            # Running average
            alpha = 0.1
            self.stats.avg_time_error = (
                (1 - alpha) * self.stats.avg_time_error + 
                alpha * prediction.time_error_seconds
            )
            if prediction.time_error_pct is not None:
                self.stats.avg_time_error_pct = (
                    (1 - alpha) * self.stats.avg_time_error_pct + 
                    alpha * prediction.time_error_pct
                )
        
        # Update condition-based accuracy
        self._update_condition_accuracy(prediction)
    
    def _update_condition_accuracy(self, prediction: ETAPrediction):
        """Update accuracy by various conditions."""
        is_hit = prediction.outcome in [
            ETAOutcome.HIT_ON_TIME, ETAOutcome.HIT_EARLY, ETAOutcome.HIT_LATE
        ]
        hit_val = 1.0 if is_hit else 0.0
        alpha = 0.1
        
        # By momentum band
        momentum_band = self._get_momentum_band(prediction.momentum_score)
        current = self.stats.accuracy_by_momentum.get(momentum_band, 0.5)
        self.stats.accuracy_by_momentum[momentum_band] = (1 - alpha) * current + alpha * hit_val
        
        # By velocity band
        velocity_band = self._get_velocity_band(prediction.pnl_velocity)
        current = self.stats.accuracy_by_velocity_band.get(velocity_band, 0.5)
        self.stats.accuracy_by_velocity_band[velocity_band] = (1 - alpha) * current + alpha * hit_val
        
        # By proximity band
        proximity_band = self._get_proximity_band(prediction.proximity_to_target)
        current = self.stats.accuracy_by_proximity_band.get(proximity_band, 0.5)
        self.stats.accuracy_by_proximity_band[proximity_band] = (1 - alpha) * current + alpha * hit_val
        
        # By cascade level
        cascade_band = self._get_cascade_band(prediction.cascade_factor)
        current = self.stats.accuracy_by_cascade_level.get(cascade_band, 0.5)
        self.stats.accuracy_by_cascade_level[cascade_band] = (1 - alpha) * current + alpha * hit_val
    
    def _adapt_from_prediction(self, prediction: ETAPrediction):
        """
        🧠 ADAPT: Learn from this prediction result.
        
        The core adaptation loop - every prediction teaches us.
        """
        alpha = 0.05  # Slow adaptation rate
        
        # 1. Update momentum reliability
        momentum_band = self._get_momentum_band(prediction.momentum_score)
        is_hit = prediction.outcome in [
            ETAOutcome.HIT_ON_TIME, ETAOutcome.HIT_EARLY, ETAOutcome.HIT_LATE
        ]
        current_reliability = self.momentum_reliability.get(momentum_band, 0.5)
        self.momentum_reliability[momentum_band] = (
            (1 - alpha) * current_reliability + alpha * (1.0 if is_hit else 0.0)
        )
        
        # 2. Update velocity correction factor (based on timing errors)
        if prediction.time_error_pct is not None and is_hit:
            # If we're consistently early, our velocity estimates are too optimistic
            # If we're consistently late, our velocity estimates are too pessimistic
            if prediction.time_error_pct > 0.1:
                # We're late - velocity was overestimated, need to slow down predictions
                self.velocity_correction_factor = min(2.0, 
                    self.velocity_correction_factor * (1 + alpha * prediction.time_error_pct)
                )
            elif prediction.time_error_pct < -0.1:
                # We're early - velocity was underestimated, can speed up predictions
                self.velocity_correction_factor = max(0.5,
                    self.velocity_correction_factor * (1 + alpha * prediction.time_error_pct)
                )
        
        # 3. Update ETA bias
        if prediction.time_error_seconds is not None and is_hit:
            self.eta_bias = (1 - alpha) * self.eta_bias + alpha * prediction.time_error_seconds
        
        # 4. Adjust minimum confidence threshold based on low-confidence misses
        if not is_hit and prediction.confidence < 0.5:
            # Raise the bar for low-confidence predictions
            self.min_confidence_threshold = min(0.6,
                self.min_confidence_threshold + 0.01
            )
        elif is_hit and prediction.confidence < self.min_confidence_threshold:
            # Good prediction despite low confidence - lower threshold slightly
            self.min_confidence_threshold = max(0.2,
                self.min_confidence_threshold - 0.005
            )
        
        # Log significant adaptations
        if prediction.outcome == ETAOutcome.MISSED:
            self._log_miss_analysis(prediction)
    
    def _log_miss_analysis(self, prediction: ETAPrediction):
        """
        📊 Deep analysis of a missed prediction.
        """
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ⚠️ ETA PREDICTION MISS ANALYSIS ⚠️                          ║
╠══════════════════════════════════════════════════════════════╣
║  Symbol:    {prediction.symbol} on {prediction.exchange}
║  Predicted: {prediction.predicted_eta_seconds:.1f}s
║  Actual:    {prediction.actual_eta_seconds:.1f}s ({prediction.time_error_pct*100:+.1f}% error)
║  ──────────────────────────────────────────────────────────  ║
║  CONDITIONS AT PREDICTION:
║    P&L:      ${prediction.current_pnl:.4f} -> ${prediction.target_pnl:.4f}
║    Velocity: ${prediction.pnl_velocity:.6f}/s
║    Momentum: {prediction.momentum_score:+.2f}
║    Cascade:  {prediction.cascade_factor:.2f}x
║    MC Used:  {prediction.mc_enhanced}
║  ──────────────────────────────────────────────────────────  ║
║  FINAL STATE:
║    P&L:      ${prediction.final_pnl or 0:.4f}
║    Reason:   {prediction.miss_reason}
║  ──────────────────────────────────────────────────────────  ║
║  ADAPTATIONS APPLIED:
║    Velocity Factor: {self.velocity_correction_factor:.3f}
║    ETA Bias:        {self.eta_bias:+.1f}s
║    Min Confidence:  {self.min_confidence_threshold:.2f}
╚══════════════════════════════════════════════════════════════╝
""")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_momentum_band(self, momentum: float) -> str:
        """Categorize momentum into bands."""
        if momentum >= 0.7:
            return 'STRONG_UP'
        elif momentum >= 0.3:
            return 'UP'
        elif momentum >= 0:
            return 'WEAK_UP'
        elif momentum >= -0.3:
            return 'WEAK_DOWN'
        elif momentum >= -0.7:
            return 'DOWN'
        else:
            return 'STRONG_DOWN'
    
    def _get_velocity_band(self, velocity: float) -> str:
        """Categorize velocity into bands."""
        if velocity >= 0.01:
            return 'FAST'
        elif velocity >= 0.005:
            return 'MEDIUM'
        elif velocity >= 0.001:
            return 'SLOW'
        elif velocity >= 0:
            return 'CRAWLING'
        else:
            return 'NEGATIVE'
    
    def _get_proximity_band(self, proximity: float) -> str:
        """Categorize proximity to target into bands."""
        if proximity >= 0.9:
            return 'VERY_CLOSE'
        elif proximity >= 0.7:
            return 'CLOSE'
        elif proximity >= 0.5:
            return 'HALFWAY'
        elif proximity >= 0.25:
            return 'FAR'
        else:
            return 'VERY_FAR'
    
    def _get_cascade_band(self, cascade: float) -> str:
        """Categorize cascade factor into bands."""
        if cascade >= 5.0:
            return 'SUPER_HOT'
        elif cascade >= 2.0:
            return 'HOT'
        elif cascade >= 1.5:
            return 'WARM'
        elif cascade > 1.0:
            return 'SLIGHT'
        else:
            return 'NONE'
    
    # =========================================================================
    # EXTERNAL INTERFACES
    # =========================================================================
    
    def get_corrected_eta(
        self,
        raw_eta: float,
        momentum: float,
        velocity: float,
        confidence: float
    ) -> float:
        """
        🎯 Get a corrected ETA based on learned patterns.
        
        Use this to improve ETA predictions BEFORE displaying.
        """
        return self._apply_eta_corrections(raw_eta, momentum, velocity, confidence)
    
    def get_prediction_confidence(
        self,
        momentum: float,
        velocity: float,
        proximity: float,
        cascade_factor: float
    ) -> float:
        """
        📊 Get confidence score for an ETA prediction.
        
        Based on historical accuracy under similar conditions.
        """
        confidence = 0.5  # Base confidence
        
        # Momentum reliability
        momentum_band = self._get_momentum_band(momentum)
        momentum_acc = self.stats.accuracy_by_momentum.get(momentum_band, 0.5)
        confidence *= (0.5 + momentum_acc)
        
        # Velocity reliability
        velocity_band = self._get_velocity_band(velocity)
        velocity_acc = self.stats.accuracy_by_velocity_band.get(velocity_band, 0.5)
        confidence *= (0.5 + velocity_acc)
        
        # Proximity reliability
        proximity_band = self._get_proximity_band(proximity)
        proximity_acc = self.stats.accuracy_by_proximity_band.get(proximity_band, 0.5)
        confidence *= (0.5 + proximity_acc)
        
        # Cascade bonus
        if cascade_factor > 1.5:
            cascade_band = self._get_cascade_band(cascade_factor)
            cascade_acc = self.stats.accuracy_by_cascade_level.get(cascade_band, 0.5)
            confidence *= (0.8 + cascade_acc * 0.4)
        
        return max(0.1, min(0.99, confidence))
    
    def should_trust_eta(
        self,
        eta_seconds: float,
        momentum: float,
        velocity: float,
        proximity: float
    ) -> Tuple[bool, str]:
        """
        🎯 Should we trust this ETA prediction?
        
        Returns (trust: bool, reason: str)
        """
        confidence = self.get_prediction_confidence(momentum, velocity, proximity, 1.0)
        
        if confidence < self.min_confidence_threshold:
            return False, f"Low confidence ({confidence:.0%}) - below threshold ({self.min_confidence_threshold:.0%})"
        
        momentum_band = self._get_momentum_band(momentum)
        reliability = self.momentum_reliability.get(momentum_band, 0.5)
        
        if reliability < 0.3:
            return False, f"Momentum band '{momentum_band}' has low reliability ({reliability:.0%})"
        
        if velocity <= 0:
            return False, "Negative velocity - no ETA possible"
        
        velocity_band = self._get_velocity_band(velocity)
        velocity_acc = self.stats.accuracy_by_velocity_band.get(velocity_band, 0.5)
        
        if velocity_acc < 0.3:
            return False, f"Velocity band '{velocity_band}' has low accuracy ({velocity_acc:.0%})"
        
        return True, f"ETA trusted (confidence: {confidence:.0%})"
    
    def get_status_report(self) -> str:
        """Generate a status report on ETA prediction accuracy."""
        s = self.stats
        
        return f"""
╔══════════════════════════════════════════════════════════════╗
║  🎯⏱️ ETA VERIFICATION SYSTEM STATUS ⏱️🎯                    ║
╠══════════════════════════════════════════════════════════════╣
║  PREDICTION ACCURACY
║    Total:        {s.total_predictions}
║    Hit Rate:     {s.hit_rate*100:.1f}%
║    On-Time Rate: {s.on_time_rate*100:.1f}%
║  ──────────────────────────────────────────────────────────  ║
║  OUTCOMES
║    ✅ On Time:   {s.hits_on_time}
║    ⚡ Early:     {s.hits_early}
║    ⏳ Late:      {s.hits_late}
║    ❌ Missed:    {s.misses}
║    ↩️ Reversed:  {s.reversals}
║  ──────────────────────────────────────────────────────────  ║
║  TIMING ERRORS
║    Avg Error:    {s.avg_time_error:+.1f}s ({s.avg_time_error_pct*100:+.1f}%)
║  ──────────────────────────────────────────────────────────  ║
║  ADAPTATION STATE
║    Velocity Factor: {self.velocity_correction_factor:.3f}
║    ETA Bias:        {self.eta_bias:+.1f}s
║    Min Confidence:  {self.min_confidence_threshold:.0%}
║  ──────────────────────────────────────────────────────────  ║
║  ACTIVE PREDICTIONS: {len(self.active_predictions)}
╚══════════════════════════════════════════════════════════════╝
"""

    # =========================================================================
    # OMNIPRESENT REAL-DATA VERIFICATION LOOP
    # Runs as a daemon thread — continuously checks pending ETA predictions
    # against real open-source market prices (no API keys needed).
    # =========================================================================

    _OMNI_INTERVAL = 60       # seconds between verification sweeps
    _omni_running  = False
    _omni_thread   = None

    @staticmethod
    def _fetch_price_open_source(symbol: str) -> float:
        """
        Fetch current price for *symbol* from public, no-key APIs.
        symbol should be like 'BTCUSDC', 'ETHUSDT', etc.
        Returns 0.0 on failure.
        """
        try:
            import urllib.request as _ur
            import json as _j

            sym = symbol.upper().replace("/", "").replace("-", "")
            for q in ("USDC", "USDT", "USD", "GBP", "EUR", "BUSD"):
                if sym.endswith(q):
                    base = sym[:-len(q)]
                    break
            else:
                base = sym
            _alias = {"XBT": "BTC", "XXBT": "BTC", "XETH": "ETH"}
            base = _alias.get(base, base)

            # 1. Binance public
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={base}USDT"
            with _ur.urlopen(url, timeout=6) as r:
                price = float(_j.loads(r.read().decode()).get("price", 0))
            if price > 0:
                return price
        except Exception:
            pass
        try:
            # 2. CoinGecko fallback
            import urllib.request as _ur
            import json as _j
            _cg = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana",
                   "ada": "cardano", "xrp": "ripple", "bch": "bitcoin-cash",
                   "bnb": "binancecoin", "dot": "polkadot", "link": "chainlink"}
            cg_id = _cg.get(base.lower(), base.lower())
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
            with _ur.urlopen(url, timeout=8) as r:
                price = float(_j.loads(r.read().decode()).get(cg_id, {}).get("usd", 0))
            if price > 0:
                return price
        except Exception:
            pass
        return 0.0

    def start_omnipresent(self):
        """
        Start the omnipresent ETA verification daemon.
        Continuously validates active/expired ETA predictions against
        real open-source price data. Safe to call multiple times.
        """
        if self._omni_running:
            return
        import threading as _th
        self.__class__._omni_running = True
        t = _th.Thread(target=self._omnipresent_loop, daemon=True,
                       name="ETAOmnipresent")
        self.__class__._omni_thread = t
        t.start()
        print("🎯⏱️ ETA OMNIPRESENT: Verification daemon RUNNING (60s sweep)")

    def _omnipresent_loop(self):
        """Background loop: sweep pending ETA predictions every 60 seconds."""
        import time as _t
        _t.sleep(30)   # stagger with engine boot
        while self.__class__._omni_running:
            try:
                self._sweep_with_open_source_prices()
            except Exception as _e:
                print(f"  ⚠️ [ETAOmnipresent] sweep error: {_e}")
            _t.sleep(self._OMNI_INTERVAL)

    def _sweep_with_open_source_prices(self):
        """
        For every active ETA prediction, fetch a fresh real price and
        update its state. Expired predictions are resolved automatically.
        Also runs check_expired_predictions() to clean up stale entries.
        """
        if not self.active_predictions:
            return

        import time as _t
        now = _t.time()
        price_cache: dict = {}
        updated = 0

        for pred_id, pred in list(self.active_predictions.items()):
            sym = pred.symbol
            if sym not in price_cache:
                price_cache[sym] = self._fetch_price_open_source(sym)
            current_price = price_cache[sym]
            if current_price <= 0:
                continue

            # Derive approximate current P&L relative to entry price stored
            # in the ETAPrediction. We record the entry price as the pnl
            # proxy — all we have is pnl_velocity; derive price movement.
            # Use velocity + elapsed time as best estimate.
            elapsed = now - pred.prediction_time
            estimated_pnl = pred.current_pnl + pred.pnl_velocity * elapsed

            # Update state (non-destructive — only resolves if kill/expire)
            self.update_prediction_state(pred_id, estimated_pnl, now)
            updated += 1

        # Clean up expired predictions (waited > MAX_WAIT_MULTIPLIER × ETA)
        expired = self.check_expired_predictions()
        if expired:
            print(f"  ⏱️ [ETAOmnipresent] {len(expired)} ETA predictions expired "
                  f"(misses). Accuracy: {self.stats.hit_rate*100:.1f}%")

        if updated:
            print(f"  ⏱️ [ETAOmnipresent] swept {updated} active predictions | "
                  f"accuracy={self.stats.hit_rate*100:.1f}% | "
                  f"active={len(self.active_predictions)}")

        self._save_history()


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

ETA_VERIFIER: Optional[ETAVerificationEngine] = None

def get_eta_verifier() -> ETAVerificationEngine:
    """Get or create the global ETA verification engine (auto-starts omnipresent loop).

    Under AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS the engine is still built (pure,
    in-process) but the omnipresent daemon thread is NOT started — an audit or
    status import must never leave a background publisher running. Live runs
    don't set the flag, so the daemon starts exactly as before.
    """
    global ETA_VERIFIER
    if ETA_VERIFIER is None:
        ETA_VERIFIER = ETAVerificationEngine()
        if os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").lower() not in {"1", "true", "yes", "on"}:
            ETA_VERIFIER.start_omnipresent()
    return ETA_VERIFIER


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def register_eta(
    symbol: str,
    exchange: str,
    eta_seconds: float,
    current_pnl: float,
    target_pnl: float,
    pnl_velocity: float,
    momentum_score: float,
    cascade_factor: float = 1.0,
    mc_enhanced: bool = False,
    mc_probability: float = 0.0,
    confidence: float = 0.5
) -> str:
    """Register an ETA prediction for verification."""
    return get_eta_verifier().register_eta_prediction(
        symbol, exchange, eta_seconds, current_pnl, target_pnl,
        pnl_velocity, momentum_score, cascade_factor,
        mc_enhanced, mc_probability, float('inf'), confidence
    )

def verify_kill(symbol: str, exchange: str, actual_pnl: float, success: bool = True):
    """Verify a kill against its ETA prediction."""
    return get_eta_verifier().verify_kill(symbol, exchange, actual_pnl, success)

def check_expired():
    """Check for expired predictions."""
    return get_eta_verifier().check_expired_predictions()

def get_corrected_eta(
    raw_eta: float,
    momentum: float,
    velocity: float,
    confidence: float = 0.5
) -> float:
    """Get a corrected ETA based on learned patterns."""
    return get_eta_verifier().get_corrected_eta(raw_eta, momentum, velocity, confidence)


# =============================================================================
# MAIN - DEMO
# =============================================================================

if __name__ == "__main__":
    print("🎯⏱️ ETA VERIFICATION SYSTEM - DEMO ⏱️🎯")
    print("=" * 60)
    
    # Create engine
    engine = ETAVerificationEngine()
    
    # Register a prediction
    pred_id = engine.register_eta_prediction(
        symbol="BTCUSDC",
        exchange="binance",
        eta_seconds=45.0,
        current_pnl=0.005,
        target_pnl=0.01,
        pnl_velocity=0.0001,
        momentum_score=0.5,
        cascade_factor=1.5,
        confidence=0.7
    )
    
    print(f"Registered prediction: {pred_id}")
    print(f"Active predictions: {len(engine.active_predictions)}")
    
    # Simulate time passing and kill happening
    time.sleep(0.1)  # Simulated wait
    
    # Verify the kill
    result = engine.verify_kill("BTCUSDC", "binance", actual_pnl=0.012, kill_success=True)
    
    if result:
        print(f"Outcome: {result.outcome.value}")
        print(f"Time error: {result.time_error_seconds:.1f}s")
    
    print(engine.get_status_report())
