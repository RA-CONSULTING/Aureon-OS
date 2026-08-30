#!/usr/bin/env python3
"""
🌍⚡ HNC PROBABILITY MATRIX - MULTI-DAY TEMPORAL FREQUENCY ANALYSIS ⚡🌍
═══════════════════════════════════════════════════════════════════════════

MULTI-DAY PROBABILITY WINDOW (Upgraded from 2-hour):
├─ DAY -7 (WEEKLY):    Weekly trend baseline - major cycle patterns
├─ DAY -3 (MID-WEEK):  Mid-term trend confirmation  
├─ DAY -1 (YESTERDAY): Recent historical signal - immediate patterns
├─ HOUR 0 (NOW):       Current state calibration point
├─ DAY +1 (TOMORROW):  Primary forecast window (PRIMARY TRADING)
├─ DAY +3 (MID-WEEK):  Secondary forecast - trend continuation
└─ DAY +7 (WEEKLY):    Long-term outlook - cycle completion

The system continuously VALIDATES its predictions against actual outcomes
and LEARNS from every trade to improve future forecasting accuracy.

SELF-VALIDATION LOOP:
1. Make prediction for Day +1
2. Store prediction with timestamp
3. When Day +1 becomes Day 0, compare prediction vs reality
4. Adjust model weights based on accuracy
5. Record outcome in learning history
6. Use accumulated wisdom for future predictions

Gary Leckey & GitHub Copilot | December 2025
"From Prime to Probability - The Frequency Unfolds Across Time"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
from aureon.analytics.lighthouse_metrics import LighthouseMetricsEngine

# ═══════════════════════════════════════════════════════════════
# CONSTANTS - PROBABILITY MATRIX PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Prime sequence for temporal anchoring
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]

# Fibonacci for probability scaling
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# Golden Ratio
PHI = (1 + math.sqrt(5)) / 2  # 1.618033988749895

# Solfeggio Frequencies for state mapping
FREQ_MAP = {
    'SCHUMANN': 7.83,      # Earth resonance
    'FOUNDATION': 174.0,   # Pain reduction
    'ROOT': 256.0,         # C4 Scientific Pitch (ANCHOR)
    'LIBERATION': 396.0,   # Release fear
    'TRANSFORMATION': 417.0,  # Facilitating change
    'NATURAL_A': 432.0,    # Natural tuning
    'DISTORTION': 440.0,   # Standard A (artificial)
    'VISION': 512.0,       # C5 Octave
    'LOVE': 528.0,         # DNA repair / Miracles
    'CONNECTION': 639.0,   # Relationships
    'AWAKENING': 741.0,    # Expression
    'INTUITION': 852.0,    # Third eye
    'UNITY': 963.0,        # Oneness
}

# Probability thresholds
PROB_THRESHOLDS = {
    'EXTREME_HIGH': 0.90,   # 90%+ probability
    'HIGH': 0.75,           # 75-90%
    'MODERATE': 0.55,       # 55-75%
    'NEUTRAL': 0.45,        # 45-55%
    'LOW': 0.25,            # 25-45%
    'EXTREME_LOW': 0.10,    # <25%
}

# Day-of-week patterns (crypto markets run 24/7 but have patterns)
DAY_PATTERNS = {
    0: {'name': 'Monday', 'volatility': 1.1, 'trend_strength': 0.8},    # Week start - higher volatility
    1: {'name': 'Tuesday', 'volatility': 1.0, 'trend_strength': 1.0},   # Normal
    2: {'name': 'Wednesday', 'volatility': 0.95, 'trend_strength': 1.1}, # Mid-week stability
    3: {'name': 'Thursday', 'volatility': 1.0, 'trend_strength': 1.0},   # Normal
    4: {'name': 'Friday', 'volatility': 1.15, 'trend_strength': 0.9},   # Pre-weekend moves
    5: {'name': 'Saturday', 'volatility': 0.85, 'trend_strength': 0.7}, # Weekend low vol
    6: {'name': 'Sunday', 'volatility': 0.9, 'trend_strength': 0.75},   # Weekend recovery
}


class ProbabilityState(Enum):
    """Probability state classification"""
    EXTREME_BULLISH = "🚀 EXTREME BULLISH"
    BULLISH = "📈 BULLISH"
    SLIGHT_BULLISH = "↗️ SLIGHT BULLISH"
    NEUTRAL = "⚖️ NEUTRAL"
    SLIGHT_BEARISH = "↘️ SLIGHT BEARISH"
    BEARISH = "📉 BEARISH"
    EXTREME_BEARISH = "💥 EXTREME BEARISH"


@dataclass
class FrequencySnapshot:
    """Single point-in-time frequency measurement"""
    timestamp: datetime
    symbol: str
    price: float
    frequency: float
    resonance: float
    is_harmonic: bool
    momentum: float  # % change
    volume: float
    coherence: float
    phase_angle: float  # 0-360 degrees
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'price': self.price,
            'frequency': self.frequency,
            'resonance': self.resonance,
            'is_harmonic': self.is_harmonic,
            'momentum': self.momentum,
            'volume': self.volume,
            'coherence': self.coherence,
            'phase_angle': self.phase_angle,
        }


@dataclass
class DailyProbabilityWindow:
    """Probability analysis for a daily window (upgraded from hourly)"""
    day_offset: int  # -7, -3, -1, 0, +1, +3, +7
    start_time: datetime
    end_time: datetime
    
    # Probability metrics
    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    confidence: float = 0.0
    
    # Frequency metrics
    avg_frequency: float = 256.0
    dominant_frequency: float = 256.0
    frequency_trend: str = "STABLE"  # RISING, FALLING, STABLE
    harmonic_ratio: float = 0.0
    
    # Pattern metrics
    prime_alignment: float = 0.0
    fibonacci_alignment: float = 0.0
    golden_ratio_proximity: float = 0.0
    
    # Signal strength
    signal_strength: float = 0.0
    noise_ratio: float = 0.0
    clarity: float = 0.0
    
    # Daily cycle metrics
    day_of_week: int = 0  # 0=Monday, 6=Sunday
    volatility_factor: float = 1.0
    trend_strength: float = 1.0
    
    # Prediction validation
    predicted_direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    actual_direction: str = ""  # Filled in when day completes
    prediction_accuracy: float = 0.0  # How accurate was the prediction?
    
    # State
    state: ProbabilityState = ProbabilityState.NEUTRAL
    
    def compute_state(self):
        """Determine probability state from metrics"""
        net_prob = self.bullish_probability - self.bearish_probability
        
        if net_prob > 0.4:
            self.state = ProbabilityState.EXTREME_BULLISH
            self.predicted_direction = "BULLISH"
        elif net_prob > 0.25:
            self.state = ProbabilityState.BULLISH
            self.predicted_direction = "BULLISH"
        elif net_prob > 0.10:
            self.state = ProbabilityState.SLIGHT_BULLISH
            self.predicted_direction = "BULLISH"
        elif net_prob > -0.10:
            self.state = ProbabilityState.NEUTRAL
            self.predicted_direction = "NEUTRAL"
        elif net_prob > -0.25:
            self.state = ProbabilityState.SLIGHT_BEARISH
            self.predicted_direction = "BEARISH"
        elif net_prob > -0.40:
            self.state = ProbabilityState.BEARISH
            self.predicted_direction = "BEARISH"
        else:
            self.state = ProbabilityState.EXTREME_BEARISH
            self.predicted_direction = "BEARISH"


# Keep HourlyProbabilityWindow for backward compatibility
HourlyProbabilityWindow = DailyProbabilityWindow  # Alias


@dataclass
class ProbabilityMatrix:
    """Complete multi-day probability matrix with 7 windows"""
    symbol: str
    generated_at: datetime
    
    # The 7 daily windows (upgraded from 4 hourly)
    day_minus_7: DailyProbabilityWindow = None   # WEEKLY LOOKBACK
    day_minus_3: DailyProbabilityWindow = None   # MID-WEEK LOOKBACK
    day_minus_1: DailyProbabilityWindow = None   # YESTERDAY (base signal)
    hour_0: DailyProbabilityWindow = None        # NOW (calibration)
    day_plus_1: DailyProbabilityWindow = None    # TOMORROW (primary forecast)
    day_plus_3: DailyProbabilityWindow = None    # MID-WEEK FORECAST
    day_plus_7: DailyProbabilityWindow = None    # WEEKLY FORECAST
    
    # Backward compatibility aliases
    @property
    def hour_minus_1(self): return self.day_minus_1
    @property
    def hour_plus_1(self): return self.day_plus_1
    @property
    def hour_plus_2(self): return self.day_plus_3
    
    # Combined metrics
    combined_probability: float = 0.5
    fine_tuned_probability: float = 0.5
    confidence_score: float = 0.0
    recommended_action: str = "HOLD"
    position_modifier: float = 1.0
    
    # Multi-day trend analysis
    weekly_trend: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    trend_strength: float = 0.0
    cycle_phase: str = "UNKNOWN"   # ACCUMULATION, MARKUP, DISTRIBUTION, MARKDOWN
    
    # Fine-tuning results
    fine_tune_adjustment: float = 0.0
    fine_tune_reason: str = ""
    
    # Prediction validation metrics
    total_predictions: int = 0
    correct_predictions: int = 0
    prediction_accuracy: float = 0.0
    last_validated: datetime = None


class TemporalFrequencyAnalyzer:
    """
    Analyzes frequency patterns across **daily** windows (upgraded from hourly).
    Uses Day -1 as base signal, forecasts Day +1 primary window,
    and uses Day +3/+7 to fine-tune and validate the Day +1 forecast.
    """
    
    def __init__(self, lookback_minutes: int = 1440, sample_interval_sec: int = 300):
        # Default to 1-day lookback with 5-minute sampling; history stores ~2 weeks safely
        self.lookback_minutes = lookback_minutes
        self.sample_interval = sample_interval_sec
        
        # Historical data storage (keyed by symbol)
        self.history: Dict[str, deque] = {}
        self.max_history = 10000  # ~14 days of 2-5min samples
        
        # Probability cache
        self.probability_cache: Dict[str, ProbabilityMatrix] = {}
        self.cache_ttl = 300  # seconds (less churn for daily cadence)
        
        # Pattern recognition
        self.pattern_memory: Dict[str, List[Dict]] = {}
        
    def add_snapshot(self, snapshot: FrequencySnapshot):
        """Add a frequency snapshot to history"""
        symbol = snapshot.symbol
        if symbol not in self.history:
            self.history[symbol] = deque(maxlen=self.max_history)
        self.history[symbol].append(snapshot)
        
    def get_daily_data(self, symbol: str, day_offset: int) -> List[FrequencySnapshot]:
        """Get data for a specific **day** window relative to now."""
        if symbol not in self.history:
            return []
        
        now = datetime.now()
        if day_offset < 0:
            start = (now + timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif day_offset == 0:
            # Current day centered around now (12h back/forward) to smooth intraday shifts
            start = now - timedelta(hours=12)
            end = now + timedelta(hours=12)
        else:
            # Future windows are projected, not sampled
            return []
        
        return [s for s in self.history[symbol] if start <= s.timestamp <= end]
    
    def compute_day_signal(self, symbol: str, day_offset: int) -> HourlyProbabilityWindow:
        """
        Compute probability state for a **daily** window (e.g., Day -1, -3, -7).
        Day -1 establishes the frequency foundation for forecasting.
        """
        now = datetime.now()
        window = HourlyProbabilityWindow(
            day_offset=day_offset,
            start_time=now + timedelta(days=day_offset),
            end_time=now + timedelta(days=day_offset) + timedelta(days=1),
        )
        
        data = self.get_daily_data(symbol, day_offset)
        if not data:
            return window
        
        # Calculate frequency metrics
        frequencies = [s.frequency for s in data]
        momentums = [s.momentum for s in data]
        coherences = [s.coherence for s in data]
        harmonics = [s.is_harmonic for s in data]
        volumes = [s.volume for s in data]
        
        window.avg_frequency = np.mean(frequencies)
        window.dominant_frequency = self._find_dominant_frequency(frequencies)
        window.harmonic_ratio = sum(harmonics) / len(harmonics)
        
        # Frequency trend
        if len(frequencies) >= 2:
            freq_change = frequencies[-1] - frequencies[0]
            if freq_change > 20:
                window.frequency_trend = "RISING"
            elif freq_change < -20:
                window.frequency_trend = "FALLING"
            else:
                window.frequency_trend = "STABLE"
        
        # Momentum analysis for probability
        avg_momentum = np.mean(momentums)
        momentum_std = np.std(momentums) if len(momentums) > 1 else 0
        
        # Volume Analysis
        avg_volume = np.mean(volumes) if volumes else 0
        volume_trend = 0
        if len(volumes) >= 2 and avg_volume > 0:
            volume_trend = (volumes[-1] - volumes[0]) / avg_volume
            
        # Convert momentum to probability
        # Positive momentum = bullish, negative = bearish
        momentum_signal = np.tanh(avg_momentum / 10)  # Normalize to [-1, 1]
        
        # Volume confirmation
        volume_factor = 1.0
        if volume_trend > 0.1:  # Rising volume
            volume_factor = 1.1
        elif volume_trend < -0.1:  # Falling volume
            volume_factor = 0.9
            
        window.bullish_probability = 0.5 + (momentum_signal * 0.3 * volume_factor)
        window.bearish_probability = 1 - window.bullish_probability
        
        # Coherence affects confidence
        window.confidence = np.mean(coherences)
        
        # Signal strength from harmonic ratio
        window.signal_strength = window.harmonic_ratio * window.confidence
        
        # Noise = inverse of coherence variance stability
        window.noise_ratio = 1 - min(1, np.std(coherences) * 2) if len(coherences) > 1 else 0.5
        
        # Clarity = signal / (signal + noise)
        window.clarity = window.signal_strength / (window.signal_strength + window.noise_ratio + 0.01)
        
        # Prime alignment
        window.prime_alignment = self._compute_prime_alignment(data)
        
        # Fibonacci alignment
        window.fibonacci_alignment = self._compute_fibonacci_alignment(data)
        
        # Golden ratio proximity
        window.golden_ratio_proximity = self._compute_golden_proximity(data)
        
        window.compute_state()
        return window
    
    def compute_current_day(self, symbol: str, current_data: Dict) -> HourlyProbabilityWindow:
        """Compute current state (Day 0) as calibration point."""
        now = datetime.now()
        window = HourlyProbabilityWindow(
            day_offset=0,
            start_time=now - timedelta(hours=12),
            end_time=now + timedelta(hours=12),
        )
        
        # Use current data directly
        window.avg_frequency = current_data.get('frequency', 256)
        window.dominant_frequency = current_data.get('frequency', 256)
        window.harmonic_ratio = 1.0 if current_data.get('is_harmonic', False) else 0.0
        
        momentum = current_data.get('momentum', 0)
        volume = current_data.get('volume', 0)
        momentum_signal = np.tanh(momentum / 10)
        
        # Volume impact on current state
        volume_confidence = 1.0
        if volume > 0:
            volume_confidence = 1.05
            
        window.bullish_probability = 0.5 + (momentum_signal * 0.35 * volume_confidence)
        window.bearish_probability = 1 - window.bullish_probability
        
        window.confidence = current_data.get('coherence', 0.5)
        window.signal_strength = current_data.get('resonance', 0.5)
        
        window.compute_state()
        return window
    
    def forecast_day_plus_1(self, symbol: str, base_signal: HourlyProbabilityWindow, 
                              current: HourlyProbabilityWindow) -> HourlyProbabilityWindow:
        """
        Forecast Day +1 (PRIMARY trading window).
        Uses Day -1 (yesterday) and Day 0 (today) for calibration.
        """
        now = datetime.now()
        window = HourlyProbabilityWindow(
            day_offset=1,
            start_time=now,
            end_time=now + timedelta(days=1),
        )
        
        # Project frequency based on trend
        if base_signal.frequency_trend == "RISING":
            freq_delta = (current.avg_frequency - base_signal.avg_frequency)
            window.avg_frequency = current.avg_frequency + (freq_delta * 0.5)
        elif base_signal.frequency_trend == "FALLING":
            freq_delta = (base_signal.avg_frequency - current.avg_frequency)
            window.avg_frequency = current.avg_frequency - (freq_delta * 0.5)
        else:
            window.avg_frequency = current.avg_frequency
        
        window.dominant_frequency = window.avg_frequency
        window.frequency_trend = base_signal.frequency_trend
        
        # Probability projection with momentum continuation
        # Weight: 40% Day -1, 60% Day 0
        base_weight = 0.4
        current_weight = 0.6
        
        projected_bullish = (
            base_signal.bullish_probability * base_weight +
            current.bullish_probability * current_weight
        )
        
        # Volume confirmation for forecast
        if base_signal.bullish_probability > 0.55 and base_signal.signal_strength > 0.6:
             projected_bullish *= 1.05
        
        # Apply harmonic boost/penalty
        if current.harmonic_ratio > 0.5:
            projected_bullish *= 1.1  # 10% boost for harmonic state
        elif window.avg_frequency >= 435 and window.avg_frequency <= 445:
            projected_bullish *= 0.9  # 10% penalty for distortion
        
        # Clamp probability
        window.bullish_probability = max(0.1, min(0.9, projected_bullish))
        window.bearish_probability = 1 - window.bullish_probability
        
        # Confidence from alignment metrics
        window.confidence = (
            base_signal.confidence * 0.3 +
            current.confidence * 0.5 +
            base_signal.prime_alignment * 0.1 +
            base_signal.fibonacci_alignment * 0.1
        )
        
        # Harmonic ratio projection
        window.harmonic_ratio = (base_signal.harmonic_ratio + current.harmonic_ratio) / 2
        
        # Inherit pattern alignments
        window.prime_alignment = base_signal.prime_alignment
        window.fibonacci_alignment = base_signal.fibonacci_alignment
        window.golden_ratio_proximity = base_signal.golden_ratio_proximity
        
        # Signal clarity
        window.signal_strength = window.harmonic_ratio * window.confidence
        window.clarity = window.signal_strength * base_signal.clarity
        
        window.compute_state()
        return window
    
    def forecast_day_plus_3(self, symbol: str, day_minus_1: HourlyProbabilityWindow,
                              day_0: HourlyProbabilityWindow,
                              day_1: HourlyProbabilityWindow) -> HourlyProbabilityWindow:
        """
        Forecast Day +3 (mid-week fine-tuning window).
        Used to refine Day +1 predictions.
        """
        now = datetime.now()
        window = HourlyProbabilityWindow(
            day_offset=3,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=3),
        )
        
        decay = 0.8  # Slight decay vs Day +1
        
        # Frequency projection with trend carry
        if day_1.frequency_trend == "RISING":
            window.avg_frequency = day_1.avg_frequency * 1.01 * decay + 256 * (1 - decay)
        elif day_1.frequency_trend == "FALLING":
            window.avg_frequency = day_1.avg_frequency * 0.99 * decay + 256 * (1 - decay)
        else:
            window.avg_frequency = day_1.avg_frequency * decay + 256 * (1 - decay)
        
        window.dominant_frequency = window.avg_frequency
        window.frequency_trend = day_1.frequency_trend
        
        # Probability with mild mean reversion
        mean_reversion = 0.25
        projected_bullish = day_1.bullish_probability * (1 - mean_reversion) + 0.5 * mean_reversion
        window.bullish_probability = projected_bullish
        window.bearish_probability = 1 - window.bullish_probability
        
        window.confidence = day_1.confidence * decay
        window.harmonic_ratio = day_1.harmonic_ratio * decay
        
        window.prime_alignment = day_1.prime_alignment * decay
        window.fibonacci_alignment = day_1.fibonacci_alignment * decay
        window.golden_ratio_proximity = day_1.golden_ratio_proximity * decay
        
        window.signal_strength = day_1.signal_strength * decay
        window.clarity = day_1.clarity * decay
        
        window.compute_state()
        return window
    
    def forecast_day_plus_7(self, symbol: str, day_1: HourlyProbabilityWindow,
                              day_3: HourlyProbabilityWindow) -> HourlyProbabilityWindow:
        """
        Forecast Day +7 (weekly outlook) to further validate the Day +1 call.
        """
        now = datetime.now()
        window = HourlyProbabilityWindow(
            day_offset=7,
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=7),
        )
        
        decay = 0.6  # Stronger decay for long horizon
        trend_source = day_3 if day_3 else day_1
        
        if trend_source.frequency_trend == "RISING":
            window.avg_frequency = trend_source.avg_frequency * 1.005 * decay + 256 * (1 - decay)
        elif trend_source.frequency_trend == "FALLING":
            window.avg_frequency = trend_source.avg_frequency * 0.995 * decay + 256 * (1 - decay)
        else:
            window.avg_frequency = trend_source.avg_frequency * decay + 256 * (1 - decay)
        
        window.dominant_frequency = window.avg_frequency
        window.frequency_trend = trend_source.frequency_trend
        
        mean_reversion = 0.35
        projected_bullish = trend_source.bullish_probability * (1 - mean_reversion) + 0.5 * mean_reversion
        window.bullish_probability = projected_bullish
        window.bearish_probability = 1 - window.bullish_probability
        
        window.confidence = trend_source.confidence * decay
        window.harmonic_ratio = trend_source.harmonic_ratio * decay
        window.prime_alignment = trend_source.prime_alignment * decay
        window.fibonacci_alignment = trend_source.fibonacci_alignment * decay
        window.golden_ratio_proximity = trend_source.golden_ratio_proximity * decay
        window.signal_strength = trend_source.signal_strength * decay
        window.clarity = trend_source.clarity * decay
        
        window.compute_state()
        return window
    
    def fine_tune_forecast(self, day_1: HourlyProbabilityWindow, 
                           day_3: HourlyProbabilityWindow,
                           day_7: HourlyProbabilityWindow) -> Tuple[float, float, str]:
        """
        Use Day +3 and Day +7 forecasts to fine-tune Day +1 predictions.
        Returns: (adjustment, fine_tuned_probability, reason)
        """
        adjustment = 0.0
        reasons = []
        
        # Trend continuation vs reversal using Day +3
        d1_bullish = day_1.bullish_probability > 0.5
        d3_bullish = day_3.bullish_probability > 0.5 if day_3 else d1_bullish
        d7_bullish = day_7.bullish_probability > 0.5 if day_7 else d3_bullish
        
        if d1_bullish and d3_bullish:
            if day_3.bullish_probability > day_1.bullish_probability:
                adjustment = 0.05
                reasons.append("D+3 confirms bullish continuation")
            else:
                adjustment = -0.02
                reasons.append("D+3 shows momentum decay")
        elif d1_bullish and not d3_bullish:
            adjustment = -0.10
            reasons.append("D+3 signals potential reversal")
        elif (not d1_bullish) and (not d3_bullish):
            if day_3 and day_3.bearish_probability > day_1.bearish_probability:
                adjustment = -0.05
                reasons.append("D+3 confirms bearish continuation")
            else:
                adjustment = 0.02
                reasons.append("D+3 shows bearish momentum decay")
        elif (not d1_bullish) and d3_bullish:
            adjustment = 0.08
            reasons.append("D+3 signals potential bullish reversal")
        
        # Weekly (D+7) influence
        if day_7:
            if d7_bullish and not d1_bullish:
                adjustment += 0.04
                reasons.append("D+7 bullish pull forward")
            if (not d7_bullish) and d1_bullish:
                adjustment -= 0.04
                reasons.append("D+7 bearish headwind")
            if abs(day_7.avg_frequency - 528) < 30:
                adjustment += 0.02
                reasons.append("D+7 near 528Hz resonance")
            if abs(day_7.avg_frequency - 440) < 10:
                adjustment -= 0.03
                reasons.append("D+7 near 440Hz distortion")
        
        # Harmonic ratio influence
        if day_3 and day_3.harmonic_ratio > day_1.harmonic_ratio:
            adjustment += 0.02
            reasons.append("D+3 harmonic improving")
        elif day_3 and day_3.harmonic_ratio < day_1.harmonic_ratio * 0.8:
            adjustment -= 0.03
            reasons.append("D+3 harmonic degrading")
        
        fine_tuned = day_1.bullish_probability + adjustment
        fine_tuned = max(0.1, min(0.9, fine_tuned))
        reason = " | ".join(reasons) if reasons else "No significant D+3/D+7 adjustment"
        
        return adjustment, fine_tuned, reason
    
    def generate_probability_matrix(self, symbol: str, current_data: Dict) -> ProbabilityMatrix:
        """Generate multi-day probability matrix for a symbol."""
        now = datetime.now()
        matrix = ProbabilityMatrix(
            symbol=symbol,
            generated_at=now,
        )
        
        # Historical anchors
        matrix.day_minus_7 = self.compute_day_signal(symbol, -7)
        matrix.day_minus_3 = self.compute_day_signal(symbol, -3)
        matrix.day_minus_1 = self.compute_day_signal(symbol, -1)
        
        # Current day (calibration)
        matrix.hour_0 = self.compute_current_day(symbol, current_data)
        
        # Forecasts
        matrix.day_plus_1 = self.forecast_day_plus_1(symbol, matrix.day_minus_1, matrix.hour_0)
        matrix.day_plus_3 = self.forecast_day_plus_3(symbol, matrix.day_minus_1, matrix.hour_0, matrix.day_plus_1)
        matrix.day_plus_7 = self.forecast_day_plus_7(symbol, matrix.day_plus_1, matrix.day_plus_3)
        
        # Fine-tune Day +1 using Day +3/+7
        adjustment, fine_tuned, reason = self.fine_tune_forecast(
            matrix.day_plus_1, matrix.day_plus_3, matrix.day_plus_7
        )
        matrix.fine_tune_adjustment = adjustment
        matrix.fine_tuned_probability = fine_tuned
        matrix.fine_tune_reason = reason
        
        # Combined probability (weighted average across days)
        matrix.combined_probability = (
            matrix.day_minus_1.bullish_probability * 0.20 +
            matrix.day_minus_3.bullish_probability * 0.10 +
            matrix.hour_0.bullish_probability * 0.20 +
            matrix.day_plus_1.bullish_probability * 0.30 +
            matrix.day_plus_3.bullish_probability * 0.10 +
            matrix.day_plus_7.bullish_probability * 0.10
        )
        
        # Confidence score (heavier weight on recent + primary forecast)
        matrix.confidence_score = (
            matrix.day_minus_1.confidence * 0.20 +
            matrix.hour_0.confidence * 0.25 +
            matrix.day_plus_1.confidence * 0.25 +
            matrix.day_plus_3.confidence * 0.15 +
            matrix.day_plus_7.confidence * 0.10 +
            matrix.day_minus_3.confidence * 0.05
        )
        
        # Weekly trend summary
        if matrix.day_plus_7.bullish_probability > matrix.day_plus_3.bullish_probability:
            matrix.weekly_trend = "BULLISH"
            matrix.trend_strength = matrix.day_plus_7.bullish_probability - 0.5
        elif matrix.day_plus_7.bullish_probability < matrix.day_plus_3.bullish_probability:
            matrix.weekly_trend = "BEARISH"
            matrix.trend_strength = matrix.day_plus_7.bearish_probability - 0.5
        else:
            matrix.weekly_trend = "NEUTRAL"
            matrix.trend_strength = 0.0
        
        # Determine action (same thresholds, now multi-day informed)
        if matrix.fine_tuned_probability >= 0.70:
            matrix.recommended_action = "STRONG BUY"
            matrix.position_modifier = 1.2
        elif matrix.fine_tuned_probability >= 0.60:
            matrix.recommended_action = "BUY"
            matrix.position_modifier = 1.0
        elif matrix.fine_tuned_probability >= 0.55:
            matrix.recommended_action = "SLIGHT BUY"
            matrix.position_modifier = 0.8
        elif matrix.fine_tuned_probability >= 0.45:
            matrix.recommended_action = "HOLD"
            matrix.position_modifier = 0.5
        elif matrix.fine_tuned_probability >= 0.40:
            matrix.recommended_action = "SLIGHT SELL"
            matrix.position_modifier = 0.3
        elif matrix.fine_tuned_probability >= 0.30:
            matrix.recommended_action = "SELL"
            matrix.position_modifier = 0.2
        else:
            matrix.recommended_action = "STRONG SELL"
            matrix.position_modifier = 0.1
        
        # Cache result
        self.probability_cache[symbol] = matrix
        
        return matrix
    
    def _find_dominant_frequency(self, frequencies: List[float]) -> float:
        """Find the most common frequency band"""
        if not frequencies:
            return 256.0
        
        # Bucket into frequency bands
        bands = {}
        for f in frequencies:
            band = round(f / 50) * 50  # 50Hz bands
            bands[band] = bands.get(band, 0) + 1
        
        dominant = max(bands.items(), key=lambda x: x[1])
        return dominant[0]
    
    def _compute_prime_alignment(self, data: List[FrequencySnapshot]) -> float:
        """Compute alignment with prime number patterns"""
        if not data:
            return 0.0
        
        alignments = []
        for i, s in enumerate(data):
            # Check if index or frequency aligns with primes
            idx_prime = any(i % p == 0 for p in PRIMES[:8])
            freq_prime = any(abs(s.frequency - p * 10) < 5 for p in PRIMES[:10])
            
            alignments.append(1.0 if (idx_prime or freq_prime) else 0.0)
        
        return np.mean(alignments)
    
    def _compute_fibonacci_alignment(self, data: List[FrequencySnapshot]) -> float:
        """Compute alignment with Fibonacci patterns"""
        if len(data) < 3:
            return 0.0
        
        alignments = []
        prices = [s.price for s in data]
        
        for i in range(2, len(prices)):
            # Check Fibonacci ratio between consecutive moves
            move1 = abs(prices[i-1] - prices[i-2])
            move2 = abs(prices[i] - prices[i-1])
            
            if move1 > 0:
                ratio = move2 / move1
                # Check proximity to Fibonacci ratios
                fib_ratios = [0.382, 0.5, 0.618, 1.0, 1.618, 2.618]
                min_diff = min(abs(ratio - fr) for fr in fib_ratios)
                alignments.append(1.0 - min(1.0, min_diff * 2))
        
        return np.mean(alignments) if alignments else 0.0
    
    def _compute_golden_proximity(self, data: List[FrequencySnapshot]) -> float:
        """Compute proximity to golden ratio in price movements"""
        if len(data) < 2:
            return 0.0
        
        prices = [s.price for s in data]
        total_move = prices[-1] - prices[0]
        
        if abs(total_move) < 0.001:
            return 0.5
        
        # Find retracement levels
        retracements = []
        for p in prices[1:-1]:
            if total_move != 0:
                ret = (p - prices[0]) / total_move
                retracements.append(ret)
        
        if not retracements:
            return 0.5
        
        # Check proximity to golden ratio levels
        golden_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        proximities = []
        
        for ret in retracements:
            min_dist = min(abs(ret - gl) for gl in golden_levels)
            proximities.append(1.0 - min(1.0, min_dist * 3))
        
        return np.mean(proximities)
    
    def print_probability_matrix(self, matrix: ProbabilityMatrix):
        """Print formatted probability matrix"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  🌍⚡ HNC PROBABILITY MATRIX: {matrix.symbol:12s}                       ║
║  Generated: {matrix.generated_at.strftime('%Y-%m-%d %H:%M:%S')}                                    ║
╠══════════════════════════════════════════════════════════════════════════╣
║  TEMPORAL WINDOW          │ PROBABILITY │  FREQ  │ CONFIDENCE │ STATE   ║
╠═══════════════════════════╪═════════════╪════════╪════════════╪═════════╣""")
        
        for name, window in [
            ("⏪ HOUR -1 (BASE SIGNAL)", matrix.hour_minus_1),
            ("⏺️  HOUR  0 (CURRENT)   ", matrix.hour_0),
            ("⏩ HOUR +1 (FORECAST)  ", matrix.hour_plus_1),
            ("⏭️  HOUR +2 (FINE-TUNE) ", matrix.hour_plus_2),
        ]:
            bull = window.bullish_probability
            freq = window.avg_frequency
            conf = window.confidence
            state = window.state.value[:10]
            
            # Probability bar
            bar_len = int(bull * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            
            print(f"║  {name} │ {bar} {bull:.0%} │ {freq:6.0f} │    {conf:.0%}     │ {state} ║")
        
        print(f"""╠══════════════════════════════════════════════════════════════════════════╣
║  FINE-TUNING RESULTS                                                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Adjustment: {matrix.fine_tune_adjustment:+.2%}                                                  ║
║  Final Probability: {matrix.fine_tuned_probability:.1%}                                           ║
║  Reason: {matrix.fine_tune_reason[:60]:60s} ║
╠══════════════════════════════════════════════════════════════════════════╣
║  📊 COMBINED PROBABILITY: {matrix.combined_probability:.1%}                                       ║
║  🎯 CONFIDENCE SCORE:     {matrix.confidence_score:.1%}                                       ║
║  💡 RECOMMENDED ACTION:   {matrix.recommended_action:15s}                           ║
║  📐 POSITION MODIFIER:    ×{matrix.position_modifier:.2f}                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


@dataclass
class PositionData:
    """Position data from trading platform for probability matrix validation"""
    symbol: str
    exchange: str
    entry_price: float
    entry_time: float  # Unix timestamp
    quantity: float
    entry_value: float
    current_price: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    platform_timestamp: float = 0.0  # Timestamp from exchange API
    is_historical: bool = False
    momentum: float = 0.0
    coherence: float = 0.0
    hold_duration_mins: float = 0.0
    trailing_stop_active: bool = False
    highest_price: float = 0.0
    # Whether this position exceeded the configured timebox without reaching penny profit
    timebox_expired: bool = False

    # Net-after-costs context for live (pre-close) evaluation
    target_net: float = 0.01
    total_rate: Optional[float] = None  # fee+slippage+spread per leg
    net_unrealized_pnl: Optional[float] = None
    net_unrealized_pnl_pct: Optional[float] = None
    net_penny_distance: Optional[float] = None  # target_net - net_unrealized_pnl
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time,
            'quantity': self.quantity,
            'entry_value': self.entry_value,
            'current_price': self.current_price,
            'current_value': self.current_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'platform_timestamp': self.platform_timestamp,
            'is_historical': self.is_historical,
            'hold_duration_mins': self.hold_duration_mins,
            'trailing_stop_active': self.trailing_stop_active,
            'highest_price': self.highest_price,
            'timebox_expired': self.timebox_expired,
            'target_net': self.target_net,
            'total_rate': self.total_rate,
            'net_unrealized_pnl': self.net_unrealized_pnl,
            'net_unrealized_pnl_pct': self.net_unrealized_pnl_pct,
            'net_penny_distance': self.net_penny_distance,
        }


@dataclass
class LiveTickerFrame:
    """Normalized live ticker slice for short-horizon probability updates."""
    timestamp: float
    symbol: str
    source: str
    price: float
    bid: float
    ask: float
    bid_size: float = 0.0
    ask_size: float = 0.0
    trade_volume: float = 0.0
    coherence: float = 0.5
    planetary_alignment: float = 0.0
    solar_risk: float = 0.0

    @property
    def spread(self) -> float:
        return max(0.0, self.ask - self.bid)

    @property
    def orderbook_imbalance(self) -> float:
        denom = self.bid_size + self.ask_size
        if denom <= 0:
            return 0.0
        return (self.bid_size - self.ask_size) / denom


class HNCProbabilityIntegration:
    """
    Integrates Probability Matrix with HNC trading system.
    Provides position sizing and entry/exit signals based on temporal analysis.
    Now includes position tracking for better navigation and validation.
    """
    
    def __init__(self):
        self.analyzer = TemporalFrequencyAnalyzer()
        self.matrices: Dict[str, ProbabilityMatrix] = {}
        self.lighthouse = LighthouseMetricsEngine()
        self._last_log_ts: Optional[datetime] = None
        self._log_cache: List[Dict[str, Any]] = []
        
        # 📊 Position tracking for probability validation
        self.position_data: Dict[str, PositionData] = {}  # symbol -> position data
        self.position_history: deque = deque(maxlen=1000)  # Historical position events
        self.position_outcomes: Dict[str, List[Dict]] = {}  # symbol -> list of trade outcomes
        self.last_position_sync: float = 0.0  # Timestamp of last sync
        self.live_ticker_frames: Dict[str, deque] = {}  # symbol -> rolling live frames
        self.live_horizon_seconds: Tuple[int, int] = (30, 40)
        self.live_frame_ttl_seconds: int = 180

        # 💾 Persistence paths
        self._outcomes_path = "probability_outcomes.json"
        self._load_persisted_outcomes()

    def feed_live_ticker_frame(
        self,
        symbol: str,
        source: str,
        price: float,
        bid: float,
        ask: float,
        bid_size: float = 0.0,
        ask_size: float = 0.0,
        trade_volume: float = 0.0,
        coherence: float = 0.5,
        planetary_alignment: float = 0.0,
        solar_risk: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Feed a normalized live tick into the probability matrix's short-horizon engine.

        Returns a compact forecast dictionary for the next 30-40 seconds:
        - directional probabilities
        - projected 30s / 40s prices
        - confidence and diagnostics
        """
        ts = float(timestamp if timestamp is not None else time.time())
        frame = LiveTickerFrame(
            timestamp=ts,
            symbol=symbol,
            source=source,
            price=max(0.0, float(price)),
            bid=max(0.0, float(bid)),
            ask=max(0.0, float(ask)),
            bid_size=max(0.0, float(bid_size)),
            ask_size=max(0.0, float(ask_size)),
            trade_volume=max(0.0, float(trade_volume)),
            coherence=max(0.0, min(1.0, float(coherence))),
            planetary_alignment=max(-1.0, min(1.0, float(planetary_alignment))),
            solar_risk=max(0.0, min(1.0, float(solar_risk))),
        )

        if symbol not in self.live_ticker_frames:
            self.live_ticker_frames[symbol] = deque(maxlen=5000)
        self.live_ticker_frames[symbol].append(frame)
        self._trim_live_ticker_frames(symbol, now_ts=ts)

        return self.predict_short_horizon(symbol)

    def _trim_live_ticker_frames(self, symbol: str, now_ts: Optional[float] = None) -> None:
        """Drop stale live frames outside TTL."""
        if symbol not in self.live_ticker_frames:
            return
        horizon_now = float(now_ts if now_ts is not None else time.time())
        cutoff = horizon_now - float(self.live_frame_ttl_seconds)
        frames = self.live_ticker_frames[symbol]
        while frames and frames[0].timestamp < cutoff:
            frames.popleft()

    def predict_short_horizon(self, symbol: str) -> Dict[str, Any]:
        """
        Predict short-horizon direction for a symbol (30-40s) using:
        - tick momentum
        - orderbook imbalance
        - spread pressure
        - live volume impulse
        - coherence + planetary modulation controls
        """
        frames = self.live_ticker_frames.get(symbol, deque())
        if len(frames) < 3:
            return {
                'symbol': symbol,
                'status': 'insufficient_data',
                'required_frames': 3,
                'frames_seen': len(frames),
            }

        last = frames[-1]
        recent = [f for f in frames if (last.timestamp - f.timestamp) <= 40.0]
        if len(recent) < 2:
            return {
                'symbol': symbol,
                'status': 'insufficient_recent_data',
                'required_frames': 2,
                'frames_seen': len(recent),
            }

        first = recent[0]
        dt = max(1e-6, last.timestamp - first.timestamp)
        px_return = (last.price - first.price) / first.price if first.price > 0 else 0.0
        momentum_per_sec = px_return / dt

        avg_imbalance = float(np.mean([f.orderbook_imbalance for f in recent]))
        avg_spread_ratio = float(np.mean([(f.spread / f.price) if f.price > 0 else 0.0 for f in recent]))
        avg_volume = float(np.mean([f.trade_volume for f in recent]))
        volume_std = float(np.std([f.trade_volume for f in recent])) if len(recent) > 1 else 0.0
        volume_impulse = 0.0 if avg_volume <= 0 else min(3.0, volume_std / (avg_volume + 1e-9))

        avg_coherence = float(np.mean([f.coherence for f in recent]))
        avg_planetary_alignment = float(np.mean([f.planetary_alignment for f in recent]))
        avg_solar_risk = float(np.mean([f.solar_risk for f in recent]))

        # Signal stack -> bounded directional score in [-1, 1]
        directional_score = (
            np.tanh(momentum_per_sec * 200.0) * 0.35 +
            np.tanh(avg_imbalance * 2.5) * 0.25 +
            np.tanh(volume_impulse) * 0.10 +
            np.tanh((avg_coherence - 0.5) * 3.0) * 0.20 +
            np.tanh(avg_planetary_alignment * 2.0) * 0.10
        )
        # Spread and solar-risk are drag terms
        drag = min(0.35, avg_spread_ratio * 250.0) + (avg_solar_risk * 0.10)
        directional_score = max(-1.0, min(1.0, directional_score - drag))

        up_prob = float(max(0.01, min(0.99, 0.5 + directional_score * 0.45)))
        down_prob = float(max(0.01, min(0.99, 1.0 - up_prob)))

        micro_drift = directional_score * 0.0008
        seconds_30, seconds_40 = self.live_horizon_seconds
        expected_price_30s = last.price * (1.0 + micro_drift * (seconds_30 / 30.0))
        expected_price_40s = last.price * (1.0 + micro_drift * (seconds_40 / 30.0))

        confidence = float(max(0.05, min(
            0.99,
            0.35
            + abs(directional_score) * 0.25
            + avg_coherence * 0.20
            + min(0.15, len(recent) / 100.0)
            - min(0.12, avg_spread_ratio * 300.0)
            - (avg_solar_risk * 0.08)
        )))

        return {
            'symbol': symbol,
            'status': 'ok',
            'generated_at': datetime.utcnow().isoformat(),
            'window_seconds': {'primary': seconds_30, 'secondary': seconds_40},
            'probability_up': up_prob,
            'probability_down': down_prob,
            'direction': 'UP' if up_prob >= down_prob else 'DOWN',
            'confidence': confidence,
            'expected_price_30s': float(expected_price_30s),
            'expected_price_40s': float(expected_price_40s),
            'diagnostics': {
                'frames_used': len(recent),
                'momentum_per_sec': float(momentum_per_sec),
                'avg_orderbook_imbalance': avg_imbalance,
                'avg_spread_ratio': avg_spread_ratio,
                'avg_volume': avg_volume,
                'volume_impulse': volume_impulse,
                'avg_coherence': avg_coherence,
                'avg_planetary_alignment': avg_planetary_alignment,
                'avg_solar_risk': avg_solar_risk,
            }
        }

    # ═══════════════════════════════════════════════════════════════
    # 💾 PERSISTENCE - Save/load position outcomes for learning continuity
    # ═══════════════════════════════════════════════════════════════
    
    def _load_persisted_outcomes(self) -> None:
        """Load position outcomes from disk to preserve learning across restarts."""
        if not os.path.exists(self._outcomes_path):
            return
        try:
            with open(self._outcomes_path, 'r') as f:
                data = json.load(f)
            self.position_outcomes = data.get('outcomes', {})
            loaded_count = sum(len(v) for v in self.position_outcomes.values())
            print(f"   📊 Loaded {loaded_count} historical trade outcomes from {self._outcomes_path}")
        except Exception as e:
            print(f"   ⚠️ Failed to load outcomes: {e}")
    
    def _persist_outcomes(self) -> None:
        """Save position outcomes to disk for learning continuity."""
        try:
            data = {
                'outcomes': self.position_outcomes,
                'last_updated': time.time(),
                'total_trades': sum(len(v) for v in self.position_outcomes.values()),
            }
            with open(self._outcomes_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ Failed to persist outcomes: {e}")
    
    def feed_position_data(self, symbol: str, exchange: str, entry_price: float, 
                           entry_time: float, quantity: float, entry_value: float,
                           current_price: float = 0.0, platform_timestamp: float = 0.0,
                           is_historical: bool = False, momentum: float = 0.0,
                           coherence: float = 0.0, trailing_stop_active: bool = False,
                           highest_price: float = 0.0, timebox_expired: bool = False,
                           target_net: Optional[float] = None,
                           total_rate: Optional[float] = None,
                           entry_fee: Optional[float] = None) -> None:
        """
        Feed position data from trading platform to improve probability matrix accuracy.
        This allows the matrix to validate predictions against actual outcomes.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDC')
            exchange: Exchange name (e.g., 'binance', 'kraken')
            entry_price: Price at entry
            entry_time: Unix timestamp of entry
            quantity: Position size
            entry_value: Value at entry (GBP)
            current_price: Current market price
            platform_timestamp: Timestamp from exchange API (for validation)
            is_historical: Whether this is a historical/imported position
            momentum: Current momentum value
            coherence: Current coherence score
            trailing_stop_active: Whether trailing stop is engaged
            highest_price: Highest price since entry
        """
        now = time.time()
        hold_duration_mins = (now - entry_time) / 60 if entry_time > 0 else 0
        
        current_value = quantity * current_price if current_price > 0 else entry_value
        unrealized_pnl = current_value - entry_value
        unrealized_pnl_pct = (unrealized_pnl / entry_value * 100) if entry_value > 0 else 0

        # Net-after-costs estimate (live): align in-flight logic with penny ethos.
        # If the caller supplies total_rate (fee+slippage+spread per leg), we compute:
        # net_est = gross_pnl - (entry_fee + exit_fee)
        # where entry_fee defaults to entry_value * total_rate when not provided.
        derived_target_net = 0.0001 if target_net is None else float(target_net)
        net_unrealized_pnl = None
        net_unrealized_pnl_pct = None
        net_penny_distance = None
        derived_total_rate = float(total_rate) if total_rate is not None else None
        if derived_total_rate is not None and entry_value > 0:
            derived_entry_fee = float(entry_fee) if entry_fee is not None else (entry_value * derived_total_rate)
            exit_fee = current_value * derived_total_rate
            net_unrealized_pnl = unrealized_pnl - (derived_entry_fee + exit_fee)
            net_unrealized_pnl_pct = (net_unrealized_pnl / entry_value * 100) if entry_value > 0 else 0.0
            net_penny_distance = derived_target_net - net_unrealized_pnl
        
        pos_data = PositionData(
            symbol=symbol,
            exchange=exchange,
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            entry_value=entry_value,
            current_price=current_price,
            current_value=current_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            platform_timestamp=platform_timestamp or now,
            is_historical=is_historical,
            momentum=momentum,
            coherence=coherence,
            hold_duration_mins=hold_duration_mins,
            trailing_stop_active=trailing_stop_active,
            highest_price=highest_price,
            timebox_expired=bool(timebox_expired),
            target_net=derived_target_net,
            total_rate=derived_total_rate,
            net_unrealized_pnl=net_unrealized_pnl,
            net_unrealized_pnl_pct=net_unrealized_pnl_pct,
            net_penny_distance=net_penny_distance,
        )
        
        # Store/update position
        self.position_data[symbol] = pos_data
        self.last_position_sync = now
        
        # Log position event for history
        self.position_history.append({
            'timestamp': now,
            'symbol': symbol,
            'exchange': exchange,
            'event': 'update',
            'price': current_price,
            'pnl_pct': unrealized_pnl_pct,
            'hold_mins': hold_duration_mins,
        })
    
    def feed_position_close(
        self,
        symbol: str,
        exit_price: float,
        realized_pnl: float,
        exit_reason: str,
        platform_timestamp: float = 0.0,
        target_net: Optional[float] = None,
        penny_hit: Optional[bool] = None,
        quick_kill: Optional[bool] = None,
        max_hold_minutes: Optional[float] = None,
        hold_duration_mins: Optional[float] = None,
        timebox_expired: Optional[bool] = None,
    ) -> None:
        """
        Record a position close for probability validation.
        Helps the matrix learn from actual outcomes.
        
        Args:
            symbol: Trading pair
            exit_price: Price at exit
            realized_pnl: Final P&L (GBP)
            exit_reason: Why the position was closed
            platform_timestamp: Exchange timestamp
        """
        now = time.time()
        
        # Get entry data if we have it
        entry_data = self.position_data.get(symbol)

        # Derive hold duration (allow caller override for accuracy)
        derived_hold_mins = 0.0
        if hold_duration_mins is not None:
            derived_hold_mins = float(hold_duration_mins)
        elif entry_data:
            derived_hold_mins = float(entry_data.hold_duration_mins)

        # Penny objective: a "win" is ONLY a net penny+ after all costs
        # Default target is $0.01 unless the caller provides a clamped/validated target.
        derived_target_net = 0.0001 if target_net is None else float(target_net)
        derived_penny_hit = (realized_pnl >= derived_target_net) if penny_hit is None else bool(penny_hit)

        # Quick-kill: penny hit within the configured timebox (default 5 minutes)
        derived_max_hold = 5.0 if max_hold_minutes is None else float(max_hold_minutes)
        derived_quick_kill = (
            (derived_penny_hit and derived_hold_mins > 0 and derived_hold_mins <= derived_max_hold)
            if quick_kill is None
            else bool(quick_kill)
        )

        derived_timebox_expired = (
            bool(timebox_expired)
            if timebox_expired is not None
            else bool(getattr(entry_data, 'timebox_expired', False)) if entry_data else False
        )
        
        outcome = {
            'timestamp': now,
            'platform_timestamp': platform_timestamp or now,
            'symbol': symbol,
            'exit_price': exit_price,
            'realized_pnl': realized_pnl,
            'exit_reason': exit_reason,
            'entry_price': entry_data.entry_price if entry_data else 0.0,
            'entry_time': entry_data.entry_time if entry_data else 0.0,
            'hold_duration_mins': derived_hold_mins,
            'was_historical': entry_data.is_historical if entry_data else False,
            'entry_momentum': entry_data.momentum if entry_data else 0.0,
            'entry_coherence': entry_data.coherence if entry_data else 0.0,
            # Core metrics (net pennies + timebox viability)
            'target_net': derived_target_net,
            'penny_hit': derived_penny_hit,
            'quick_kill': derived_quick_kill,
            'max_hold_minutes': derived_max_hold,
            'timebox_expired': derived_timebox_expired,
            # Canonical win definition for learning:
            # A win == net penny objective achieved (not just >0)
            'win': derived_penny_hit,
        }
        
        # Store outcome for learning
        if symbol not in self.position_outcomes:
            self.position_outcomes[symbol] = []
        self.position_outcomes[symbol].append(outcome)
        
        # Log close event
        self.position_history.append({
            'timestamp': now,
            'symbol': symbol,
            'event': 'close',
            'price': exit_price,
            'pnl': realized_pnl,
            'reason': exit_reason,
            'target_net': derived_target_net,
            'penny_hit': derived_penny_hit,
            'quick_kill': derived_quick_kill,
            'max_hold_minutes': derived_max_hold,
            'timebox_expired': derived_timebox_expired,
            'win': derived_penny_hit,
        })
        
        # Remove from active positions
        if symbol in self.position_data:
            del self.position_data[symbol]
        
        # 💾 Persist outcomes to disk after each close for learning continuity
        self._persist_outcomes()
    
    def get_position_win_rate(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get win rate statistics for a symbol or all symbols.
        Used to adjust probability confidence based on actual performance.
        """
        if symbol:
            outcomes = self.position_outcomes.get(symbol, [])
            if not outcomes:
                return {'symbol': symbol, 'trades': 0, 'win_rate': 0.5}
            wins = sum(1 for o in outcomes if o.get('win', False))
            quick = sum(1 for o in outcomes if o.get('quick_kill', False))
            expired = sum(1 for o in outcomes if o.get('timebox_expired', False))
            return {
                'symbol': symbol,
                'trades': len(outcomes),
                'wins': wins,
                'losses': len(outcomes) - wins,
                'win_rate': wins / len(outcomes) if outcomes else 0.5,
                'quick_kills': quick,
                'quick_kill_rate': quick / len(outcomes) if outcomes else 0.0,
                'timebox_expired': expired,
                'timebox_expired_rate': expired / len(outcomes) if outcomes else 0.0,
                'avg_hold_mins': np.mean([o.get('hold_duration_mins', 0) for o in outcomes]),
            }
        else:
            # All symbols
            all_outcomes = []
            for sym_outcomes in self.position_outcomes.values():
                all_outcomes.extend(sym_outcomes)
            if not all_outcomes:
                return {'trades': 0, 'win_rate': 0.5}
            wins = sum(1 for o in all_outcomes if o.get('win', False))
            quick = sum(1 for o in all_outcomes if o.get('quick_kill', False))
            expired = sum(1 for o in all_outcomes if o.get('timebox_expired', False))
            return {
                'trades': len(all_outcomes),
                'wins': wins,
                'losses': len(all_outcomes) - wins,
                'win_rate': wins / len(all_outcomes) if all_outcomes else 0.5,
                'quick_kills': quick,
                'quick_kill_rate': quick / len(all_outcomes) if all_outcomes else 0.0,
                'timebox_expired': expired,
                'timebox_expired_rate': expired / len(all_outcomes) if all_outcomes else 0.0,
            }
    
    def validate_and_learn(self, symbol: str, predicted_direction: str, 
                          actual_direction: str, confidence: float = 0.5) -> Dict[str, Any]:
        """
        CONTINUOUS VALIDATION & LEARNING:
        Validate Day +1 predictions against actual outcomes when Day +1 becomes Day 0.
        
        This is the core learning loop that improves forecast accuracy over time.
        
        Args:
            symbol: Asset being tracked
            predicted_direction: What the matrix predicted (BULLISH, BEARISH, NEUTRAL)
            actual_direction: What actually happened
            confidence: How confident was the prediction?
        
        Returns:
            Validation metrics including accuracy, adjustment factors
        """
        was_correct = predicted_direction == actual_direction
        
        # Update learning metrics
        if symbol not in self.matrices:
            return {'validated': False, 'symbol': symbol}
        
        matrix = self.matrices[symbol]
        matrix.total_predictions += 1
        if was_correct:
            matrix.correct_predictions += 1
        
        # Calculate new accuracy
        matrix.prediction_accuracy = (
            matrix.correct_predictions / matrix.total_predictions 
            if matrix.total_predictions > 0 else 0.5
        )
        matrix.last_validated = datetime.now()
        
        # Determine confidence adjustment
        # High confidence + correct = increase future forecast strength
        # High confidence + wrong = decrease future forecast strength  
        # Low confidence + correct = boost confidence
        # Low confidence + wrong = reduce confidence (less damage)
        
        confidence_adjustment = 0.0
        accuracy_trend = "NEUTRAL"
        
        if was_correct:
            if confidence >= 0.7:
                confidence_adjustment = +0.05  # Boost strong accurate predictions
                accuracy_trend = "ACCURATE_STRONG"
            elif confidence >= 0.5:
                confidence_adjustment = +0.03  # Boost moderate accurate predictions
                accuracy_trend = "ACCURATE_MODERATE"
            else:
                confidence_adjustment = +0.02  # Weak correct signals still help
                accuracy_trend = "ACCURATE_WEAK"
        else:
            if confidence >= 0.7:
                confidence_adjustment = -0.10  # Penalize strong wrong predictions
                accuracy_trend = "WRONG_STRONG"
            elif confidence >= 0.5:
                confidence_adjustment = -0.05  # Penalize moderate wrong predictions
                accuracy_trend = "WRONG_MODERATE"
            else:
                confidence_adjustment = -0.02  # Weak wrong signals have minimal impact
                accuracy_trend = "WRONG_WEAK"
        
        # Log validation event
        validation_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'predicted': predicted_direction,
            'actual': actual_direction,
            'was_correct': was_correct,
            'confidence_input': confidence,
            'confidence_adjustment': confidence_adjustment,
            'trend': accuracy_trend,
            'cumulative_accuracy': matrix.prediction_accuracy,
            'total_predictions': matrix.total_predictions,
            'correct': matrix.correct_predictions,
        }
        
        if symbol not in self.position_history:
            self.position_history = []
        self.position_history.append(validation_record)
        
        return {
            'validated': True,
            'symbol': symbol,
            'was_correct': was_correct,
            'accuracy': matrix.prediction_accuracy,
            'confidence_adjustment': confidence_adjustment,
            'trend': accuracy_trend,
            'predictions_count': matrix.total_predictions,
        }
    
    def get_active_positions_summary(self) -> Dict[str, Any]:
        """
        Get summary of all active positions tracked by the probability matrix.
        """
        if not self.position_data:
            return {'count': 0, 'positions': []}
        
        positions = []
        total_value = 0.0
        total_pnl = 0.0
        
        for symbol, pos in self.position_data.items():
            positions.append({
                'symbol': symbol,
                'exchange': pos.exchange,
                'value': pos.current_value,
                'pnl': pos.unrealized_pnl,
                'pnl_pct': pos.unrealized_pnl_pct,
                'hold_mins': pos.hold_duration_mins,
                'historical': pos.is_historical,
            })
            total_value += pos.current_value
            total_pnl += pos.unrealized_pnl
        
        return {
            'count': len(positions),
            'total_value': total_value,
            'total_pnl': total_pnl,
            'last_sync': self.last_position_sync,
            'positions': positions,
        }

    def _load_frequency_log(self, path: str = "hnc_frequency_log.json") -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._log_cache = data
                try:
                    self._last_log_ts = max(
                        datetime.fromisoformat(entry.get("timestamp"))
                        for entry in data if entry.get("timestamp")
                    )
                except Exception:
                    pass
                return data
        except Exception:
            return []
        return []

    def _compute_lighthouse_adjustment(self, symbol: str) -> Tuple[float, str]:
        logs = self._log_cache or self._load_frequency_log()
        if not logs:
            return 0.0, "No lighthouse log data"

        timestamps: List[float] = []
        values: List[float] = []
        for entry in logs[-50:]:
            ts = entry.get("timestamp")
            readings = entry.get("readings", [])
            if not ts or not readings:
                continue
            for r in readings:
                if r.get("symbol") == symbol:
                    try:
                        dt = datetime.fromisoformat(ts)
                        timestamps.append(dt.timestamp())
                        values.append(float(r.get("price", 0)))
                    except Exception:
                        pass
                    break

        if len(values) < 8:
            return 0.0, "Insufficient lighthouse samples"

        try:
            metrics = self.lighthouse.analyze_series(timestamps, values)
        except Exception as e:
            return 0.0, f"Lighthouse analysis error: {e}"

        coherence = float(metrics.get("coherence_score", 0.0))
        distortion = float(metrics.get("distortion_index", 0.0))
        gamma = float(metrics.get("gamma_ratio", 0.0))
        maker_bias = float(metrics.get("maker_bias", 0.5))

        adj = 0.0
        reason_bits = []

        if coherence > 0.35:
            boost = min(0.05, (coherence - 0.35) * 0.2)
            adj += boost
            reason_bits.append(f"coherence +{boost:.2%}")
        if distortion > 0.40:
            cut = min(0.08, (distortion - 0.40) * 0.3)
            adj -= cut
            reason_bits.append(f"distortion -{cut:.2%}")
        if gamma > 0.25:
            cut = min(0.03, (gamma - 0.25) * 0.1)
            adj -= cut
            reason_bits.append(f"gamma -{cut:.2%}")

        bias_adj = (maker_bias - 0.5) * 0.06
        if abs(bias_adj) > 0.002:
            adj += bias_adj
            reason_bits.append(f"maker_bias {bias_adj:+.2%}")

        adj = max(-0.10, min(0.10, adj))
        reason = ", ".join(reason_bits) if reason_bits else "neutral lighthouse state"
        return adj, reason
        
    def update_and_analyze(self, symbol: str, price: float, frequency: float,
                           momentum: float, coherence: float, 
                           is_harmonic: bool, volume: float = 0.0) -> ProbabilityMatrix:
        """Update data and generate probability matrix"""
        
        # Create snapshot
        snapshot = FrequencySnapshot(
            timestamp=datetime.now(),
            symbol=symbol,
            price=price,
            frequency=frequency,
            resonance=1.0 if is_harmonic else 0.6,
            is_harmonic=is_harmonic,
            momentum=momentum,
            volume=volume,
            coherence=coherence,
            phase_angle=0,
        )
        
        # Add to history
        self.analyzer.add_snapshot(snapshot)
        
        # Generate matrix
        current_data = {
            'frequency': frequency,
            'momentum': momentum,
            'coherence': coherence,
            'is_harmonic': is_harmonic,
            'resonance': snapshot.resonance,
            'volume': volume,
        }
        
        matrix = self.analyzer.generate_probability_matrix(symbol, current_data)
        # Lighthouse refinement on Hour +1 using recent logs
        lh_adj, lh_reason = self._compute_lighthouse_adjustment(symbol)
        if lh_adj != 0.0:
            pre = matrix.hour_plus_1.bullish_probability
            matrix.hour_plus_1.bullish_probability = max(0.1, min(0.9, pre + lh_adj))
            matrix.hour_plus_1.bearish_probability = 1 - matrix.hour_plus_1.bullish_probability
            matrix.hour_plus_1.compute_state()

            # Recompute Hour +2 and fine-tuning
            matrix.hour_plus_2 = self.analyzer.forecast_hour_plus_2(
                symbol, matrix.hour_minus_1, matrix.hour_0, matrix.hour_plus_1
            )
            adjustment, fine_tuned, reason = self.analyzer.fine_tune_forecast(
                matrix.hour_plus_1, matrix.hour_plus_2
            )
            matrix.fine_tune_adjustment = adjustment
            matrix.fine_tuned_probability = fine_tuned
            matrix.fine_tune_reason = f"{reason} | Lighthouse: {lh_reason} ({lh_adj:+.2%})"
        
        # 📊 Position-based validation adjustment
        pos_adj, pos_reason = self._compute_position_adjustment(symbol)
        if pos_adj != 0.0:
            pre = matrix.fine_tuned_probability
            matrix.fine_tuned_probability = max(0.1, min(0.9, pre + pos_adj))
            matrix.confidence_score = min(1.0, matrix.confidence_score + abs(pos_adj) * 0.5)
            matrix.fine_tune_reason += f" | Position: {pos_reason}"

        self.matrices[symbol] = matrix
        
        return matrix
    
    def _compute_position_adjustment(self, symbol: str) -> Tuple[float, str]:
        """
        Compute probability adjustment based on position tracking data.
        Uses historical win rate and current position performance.
        """
        adj = 0.0
        reasons = []
        
        # Check historical win rate for this symbol
        win_stats = self.get_position_win_rate(symbol)
        if win_stats.get('trades', 0) >= 3:
            win_rate = win_stats.get('win_rate', 0.5)
            # Boost confidence for symbols with good track record
            if win_rate > 0.65:
                adj += 0.03
                reasons.append(f"winrate {win_rate:.0%}↑")
            elif win_rate < 0.35:
                adj -= 0.03
                reasons.append(f"winrate {win_rate:.0%}↓")

            # Prefer symbols that reliably hit the penny objective quickly
            quick_rate = win_stats.get('quick_kill_rate', 0.0)
            if quick_rate > 0.60:
                adj += 0.02
                reasons.append(f"quick {quick_rate:.0%}↑")
            elif quick_rate < 0.25:
                adj -= 0.02
                reasons.append(f"quick {quick_rate:.0%}↓")

            # Penalize setups that frequently exceed the timebox without a penny kill
            expired_rate = win_stats.get('timebox_expired_rate', 0.0)
            if expired_rate > 0.50:
                adj -= 0.02
                reasons.append(f"timebox {expired_rate:.0%}↓")
        
        # Check if we have an active position
        if symbol in self.position_data:
            pos = self.position_data[symbol]

            # Prefer net-after-costs signals when available (aligns to penny ethos)
            used_net = False
            if pos.net_unrealized_pnl is not None and pos.total_rate is not None:
                used_net = True
                # If net already clears the penny target, that's a strong positive validation.
                if pos.net_unrealized_pnl >= (pos.target_net or 0.01):
                    adj += 0.02
                    reasons.append("net_penny_ready")
                # If net is meaningfully negative after costs, that's a risk signal.
                elif pos.net_unrealized_pnl <= -(pos.target_net or 0.01):
                    adj -= 0.02
                    reasons.append("net_negative")
                # Otherwise, mild net-positive/negative shaping.
                elif pos.net_unrealized_pnl > 0:
                    adj += 0.01
                    reasons.append("net+")
                elif pos.net_unrealized_pnl < 0:
                    adj -= 0.01
                    reasons.append("net-")

            # Fallback to gross % only when we don't have cost context.
            if not used_net:
                # If position is in profit, current direction is validated
                if pos.unrealized_pnl_pct > 1.0:
                    adj += 0.02
                    reasons.append(f"pos +{pos.unrealized_pnl_pct:.1f}%")
                elif pos.unrealized_pnl_pct < -2.0:
                    adj -= 0.02
                    reasons.append(f"pos {pos.unrealized_pnl_pct:.1f}%")
            
            # Long hold times with profit = stable trend
            if pos.hold_duration_mins > 30 and ((pos.net_unrealized_pnl is not None and pos.net_unrealized_pnl > 0) or (pos.net_unrealized_pnl is None and pos.unrealized_pnl_pct > 0)):
                adj += 0.01
                reasons.append(f"hold {pos.hold_duration_mins:.0f}m+profit")

            # If we've already exceeded the timebox, treat it as a negative signal.
            if getattr(pos, 'timebox_expired', False):
                # If we've exceeded the timebox and we're not net-penny-ready, penalize.
                if not (pos.net_unrealized_pnl is not None and pos.net_unrealized_pnl >= (pos.target_net or 0.01)):
                    adj -= 0.01
                    reasons.append("timebox_expired")
        
        adj = max(-0.10, min(0.10, adj))
        reason = ", ".join(reasons) if reasons else "no pos data"
        return adj, reason
    
    def get_trading_signal(self, symbol: str) -> Dict[str, Any]:
        """Get trading signal based on probability matrix"""
        if symbol not in self.matrices:
            return {
                'action': 'HOLD',
                'probability': 0.5,
                'confidence': 0.0,
                'modifier': 1.0,
                'reason': 'No probability matrix available'
            }
        
        matrix = self.matrices[symbol]
        
        # Include position info if we have it
        pos_info = {}
        if symbol in self.position_data:
            pos = self.position_data[symbol]
            pos_info = {
                'has_position': True,
                'position_pnl_pct': pos.unrealized_pnl_pct,
                'hold_duration_mins': pos.hold_duration_mins,
                'position_exchange': pos.exchange,
            }
        else:
            pos_info = {'has_position': False}
        
        # Get win rate for this symbol
        win_stats = self.get_position_win_rate(symbol)
        
        return {
            'action': matrix.recommended_action,
            'probability': matrix.fine_tuned_probability,
            'confidence': matrix.confidence_score,
            'modifier': matrix.position_modifier,
            'reason': matrix.fine_tune_reason,
            'h1_state': matrix.hour_plus_1.state.value,
            'h2_influence': matrix.fine_tune_adjustment,
            'position': pos_info,
            'historical_win_rate': win_stats.get('win_rate', 0.5),
            'historical_trades': win_stats.get('trades', 0),
        }
    
    def get_high_probability_opportunities(self, 
                                            min_probability: float = 0.65,
                                            min_confidence: float = 0.50) -> List[Dict]:
        """Get symbols with high probability windows"""
        opportunities = []
        
        for symbol, matrix in self.matrices.items():
            if (matrix.fine_tuned_probability >= min_probability and
                matrix.confidence_score >= min_confidence):
                opportunities.append({
                    'symbol': symbol,
                    'probability': matrix.fine_tuned_probability,
                    'confidence': matrix.confidence_score,
                    'action': matrix.recommended_action,
                    'modifier': matrix.position_modifier,
                    'h1_state': matrix.hour_plus_1.state.value,
                    'frequency': matrix.hour_plus_1.avg_frequency,
                })
        
        # Sort by probability
        opportunities.sort(key=lambda x: x['probability'], reverse=True)
        return opportunities
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🌌🔮 LABYRINTH INTELLIGENCE INTEGRATION - The Matrix LEARNS from Labyrinth!
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_asset_signal(self, asset: str, momentum: float, market_sentiment: float):
        """
        🌌 Receive momentum signal from Labyrinth for probability adjustment
        
        Called by the Labyrinth wiring to update probability calculations
        based on market-wide data.
        
        Args:
            asset: The asset symbol
            momentum: Current momentum from Labyrinth (-1 to 1 scale)
            market_sentiment: Overall market sentiment from Labyrinth
        """
        if not hasattr(self, 'labyrinth_signals'):
            self.labyrinth_signals = {}
        
        self.labyrinth_signals[asset] = {
            'momentum': momentum,
            'market_sentiment': market_sentiment,
            'timestamp': time.time()
        }
        
        # If we have a matrix for this asset, apply the signal
        if asset in self.matrices:
            matrix = self.matrices[asset]
            
            # Adjust probability based on Labyrinth intelligence
            labyrinth_boost = 0.0
            
            # Strong momentum alignment with market sentiment boosts probability
            if momentum > 0 and market_sentiment > 0:
                labyrinth_boost = min(0.05, momentum * market_sentiment * 0.1)
            elif momentum < 0 and market_sentiment < 0:
                labyrinth_boost = min(0.05, abs(momentum * market_sentiment) * 0.1)
            
            # Store for later use
            if not hasattr(matrix, 'labyrinth_boost'):
                matrix.labyrinth_boost = 0.0
            matrix.labyrinth_boost = labyrinth_boost
    
    def feed_labyrinth_pattern(self, asset: str, pattern_data: Dict):
        """
        🌌 Feed Labyrinth pattern data for probability resonance calculations
        
        The Matrix uses this to improve forecasting by incorporating
        market-wide patterns discovered by the Labyrinth.
        
        Args:
            asset: The asset symbol
            pattern_data: Dict with momentum, volume, market_sentiment
        """
        if not hasattr(self, 'labyrinth_patterns'):
            self.labyrinth_patterns = {}
        
        if asset not in self.labyrinth_patterns:
            self.labyrinth_patterns[asset] = []
        
        self.labyrinth_patterns[asset].append({
            **pattern_data,
            'timestamp': time.time()
        })
        
        # Keep last 50 patterns per asset
        if len(self.labyrinth_patterns[asset]) > 50:
            self.labyrinth_patterns[asset] = self.labyrinth_patterns[asset][-50:]
    
    def get_symbol_forecast(self, symbol: str) -> Dict:
        """
        🔮 Get probability forecast for a symbol, enhanced by Labyrinth intelligence
        
        Returns:
            Dict with bullish_probability, bearish_probability, confidence, etc.
        """
        base_result = {
            'symbol': symbol,
            'bullish_probability': 0.5,
            'bearish_probability': 0.5,
            'confidence': 0.5,
            'labyrinth_boost': 0.0,
            'labyrinth_sentiment': 0.0
        }
        
        # Get from matrix if available
        if symbol in self.matrices:
            matrix = self.matrices[symbol]
            prob = matrix.fine_tuned_probability
            conf = matrix.confidence_score
            
            # Determine bullish vs bearish based on recommended action
            if matrix.recommended_action in ['STRONG_BUY', 'BUY']:
                base_result['bullish_probability'] = prob
                base_result['bearish_probability'] = 1 - prob
            elif matrix.recommended_action in ['STRONG_SELL', 'SELL']:
                base_result['bearish_probability'] = prob
                base_result['bullish_probability'] = 1 - prob
            else:
                base_result['bullish_probability'] = prob
                base_result['bearish_probability'] = 1 - prob
            
            base_result['confidence'] = conf
            
            # Add Labyrinth boost if available
            if hasattr(matrix, 'labyrinth_boost'):
                base_result['labyrinth_boost'] = matrix.labyrinth_boost
        
        # Add Labyrinth sentiment if available
        if hasattr(self, 'labyrinth_signals') and symbol in self.labyrinth_signals:
            signal = self.labyrinth_signals[symbol]
            base_result['labyrinth_sentiment'] = signal.get('market_sentiment', 0.0)
            
            # Adjust probabilities based on fresh Labyrinth data (< 60 seconds old)
            if time.time() - signal.get('timestamp', 0) < 60:
                sentiment = signal.get('market_sentiment', 0)
                # Boost bullish prob in bullish market, bearish in bearish
                if sentiment > 0:
                    base_result['bullish_probability'] = min(0.95, base_result['bullish_probability'] * (1 + sentiment * 0.1))
                else:
                    base_result['bearish_probability'] = min(0.95, base_result['bearish_probability'] * (1 + abs(sentiment) * 0.1))
        
        return base_result

    # ═══════════════════════════════════════════════════════════════════════════
    # 👑🐝 QUEEN BEE METRICS INTEGRATION - Sero's Consciousness Feeds the Matrix!
    # ═══════════════════════════════════════════════════════════════════════════
    
    def wire_queen_metrics(self, queen) -> None:
        """
        🐝👑 Wire the Queen Hive Mind to the Probability Matrix!
        
        The Matrix becomes aware of ALL the Queen's metrics:
        - Auris coherence from 9 sacred nodes
        - Emotional spectrum (LOVE alignment)
        - Gaia's blessing
        - Dream visions
        - Historical wisdom
        - Sandbox evolution
        - 11 Civilizations alignment
        """
        self.queen = queen
        print(f"   👑🐝 Queen Hive Mind: WIRED to Probability Matrix!")
    
    def feed_queen_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        🐝 Feed Queen's comprehensive metrics to enhance probability calculations.
        
        This allows the Matrix to use the Queen's consciousness signals:
        - auris_coherence: Coherence from 9 Auris nodes (0-1)
        - emotional_love: LOVE frequency alignment (0-1)
        - gaia_blessing: Earth's blessing level (0-1)
        - historical_wisdom: Learned patterns count
        - sandbox_evolution: Sandbox generation
        - civilizations_alignment: 11 civilizations blessing (0-1)
        - luck_score: Current luck field (0-1)
        - dream_confidence: Dream vision confidence (0-1)
        
        Returns:
            Dict with queen_boost and enhanced probability adjustment
        """
        if not hasattr(self, 'queen_metrics'):
            self.queen_metrics = {}
        
        timestamp = time.time()
        self.queen_metrics = {
            **metrics,
            'timestamp': timestamp
        }
        
        # Calculate Queen-enhanced probability boost
        queen_boost = 0.0
        signals = []
        
        # Auris Coherence (9 sacred nodes)
        auris = metrics.get('auris_coherence', 0.5)
        if auris > 0.7:
            queen_boost += 0.03
            signals.append(f"🦉 Auris HIGH ({auris:.0%})")
        elif auris < 0.3:
            queen_boost -= 0.02
            signals.append(f"🦉 Auris LOW ({auris:.0%})")
        
        # Emotional Spectrum (LOVE alignment)
        love = metrics.get('emotional_love', 0.5)
        if love > 0.8:
            queen_boost += 0.02
            signals.append("🌈 LOVE RESONANCE")
        
        # Gaia's Blessing
        gaia = metrics.get('gaia_blessing', 0.5)
        if gaia > 0.75:
            queen_boost += 0.02
            signals.append(f"🌍 Gaia BLESSING ({gaia:.0%})")
        
        # Dream Vision Confidence
        dream = metrics.get('dream_confidence', 0.5)
        if dream > 0.7:
            queen_boost += 0.02
            signals.append(f"💭 Dream CLEAR ({dream:.0%})")
        
        # 11 Civilizations Alignment
        civs = metrics.get('civilizations_alignment', 0.5)
        if civs > 0.8:
            queen_boost += 0.02
            signals.append(f"🏛️ Civilizations ALIGNED")
        
        # Luck Field
        luck = metrics.get('luck_score', 0.5)
        if luck > 0.75:
            queen_boost += 0.01
            signals.append(f"🍀 Luck HIGH ({luck:.0%})")
        
        # Historical Wisdom (patterns learned)
        patterns = metrics.get('historical_patterns', 0)
        trades = metrics.get('historical_trades', 0)
        if patterns > 5 and trades > 50:
            queen_boost += 0.02
            signals.append(f"📚 {patterns} patterns, {trades} trades")
        
        # Sandbox Evolution
        sandbox_gen = metrics.get('sandbox_generation', 0)
        if sandbox_gen > 100:
            queen_boost += 0.01
            signals.append(f"🧬 Gen {sandbox_gen}")
        
        queen_boost = max(-0.10, min(0.10, queen_boost))
        
        result = {
            'queen_boost': queen_boost,
            'signals': signals,
            'timestamp': timestamp,
            'message': f"👑 Queen contributes {queen_boost:+.1%} to probability"
        }
        
        # Apply to all active matrices
        for symbol, matrix in self.matrices.items():
            if not hasattr(matrix, 'queen_boost'):
                matrix.queen_boost = 0.0
            matrix.queen_boost = queen_boost
            
            # Adjust fine-tuned probability
            old_prob = matrix.fine_tuned_probability
            matrix.fine_tuned_probability = max(0.1, min(0.9, old_prob + queen_boost))
            
            if queen_boost != 0.0:
                matrix.fine_tune_reason += f" | Queen: {', '.join(signals)}"
        
        return result
    
    def get_queen_enhanced_forecast(self, symbol: str, opportunity: Dict = None) -> Dict:
        """
        🐝🔮 Get probability forecast enhanced by Queen's consciousness.
        
        This combines:
        1. HNC temporal analysis
        2. Labyrinth market patterns
        3. Queen's dream vision for this specific opportunity
        
        Args:
            symbol: Asset symbol
            opportunity: Optional dict with opportunity details for dream vision
            
        Returns:
            Enhanced forecast with queen_signals, dream_vision, and adjusted probability
        """
        # Get base forecast
        forecast = self.get_symbol_forecast(symbol)
        
        # Add Queen metrics if available
        if hasattr(self, 'queen_metrics') and self.queen_metrics:
            metrics = self.queen_metrics
            
            # Calculate queen signal strength
            auris = metrics.get('auris_coherence', 0.5)
            love = metrics.get('emotional_love', 0.5)
            gaia = metrics.get('gaia_blessing', 0.5)
            luck = metrics.get('luck_score', 0.5)
            
            queen_signal = (auris * 0.3 + love * 0.2 + gaia * 0.3 + luck * 0.2)
            
            forecast['queen_signal'] = queen_signal
            forecast['queen_metrics'] = metrics
            
            # Boost probability if Queen signals are strong
            if queen_signal > 0.65:
                old_bull = forecast['bullish_probability']
                boost = (queen_signal - 0.5) * 0.1
                forecast['bullish_probability'] = min(0.95, old_bull * (1 + boost))
                forecast['queen_boost_applied'] = boost
        
        # Dream of winning if Queen is wired and we have opportunity data
        if hasattr(self, 'queen') and self.queen and opportunity:
            try:
                if hasattr(self.queen, 'dream_of_winning'):
                    dream_vision = self.queen.dream_of_winning(opportunity)
                    forecast['dream_vision'] = dream_vision
                    
                    # Apply dream vision to probability
                    if dream_vision.get('will_win'):
                        dream_conf = dream_vision.get('final_confidence', 0.5)
                        if dream_conf > 0.6:
                            forecast['bullish_probability'] = min(0.95, 
                                forecast['bullish_probability'] * (1 + (dream_conf - 0.5) * 0.2))
                            forecast['dream_boost_applied'] = True
            except Exception as e:
                forecast['dream_error'] = str(e)
        
        return forecast


# ═══════════════════════════════════════════════════════════════
# DEMO / TEST
