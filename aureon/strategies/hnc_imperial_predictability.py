#!/usr/bin/env python3
"""
🌌⚡ HNC IMPERIAL PREDICTABILITY ENGINE ⚡🌌
═══════════════════════════════════════════════════════════════

COSMIC SYNCHRONIZATION + TEMPORAL FORECASTING + TRADING INTEGRATION

Integrates the Imperial Master Protocol's cosmic equations with the
Aureon trading ecosystem for enhanced predictability and position sizing.

CORE EQUATIONS:
├─ Imperial Yield: E = (J³ × C² × R × T²) / D × 10³³
├─ Cosmic Torque: Planetary alignments + Lunar phases + Schumann
├─ Temporal Windows: 2-hour probability + 8-day cosmic calendar
├─ Financial Momentum: PHI-scaled market predictions
└─ Distortion Nullification: 440Hz → 528Hz transformation

COMPONENTS:
1. CosmicStateEngine - Real-time cosmic parameter computation
2. ImperialYieldCalculator - Financial momentum from cosmic state
3. PredictabilityMatrix - Multi-timeframe probability forecasts
4. TradingIntegration - Position sizing and opportunity enhancement

Gary Leckey & GitHub Copilot | December 2025
"From Atom to Multiverse - The Imperial Protocol Unfolds"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import math
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

# Golden Ratio & Core Constants
PHI = (1 + np.sqrt(5)) / 2  # 1.618033988749895
CRITICAL_MASS = 1.0e33

# ═══════════════════════════════════════════════════════════════
# 🌍 COSMIC RESONANCE CONSTANTS
# ═══════════════════════════════════════════════════════════════

# Scientific Pitch & Solfeggio Frequencies
FREQUENCIES = {
    'SCHUMANN': 7.83,       # Earth's heartbeat
    'FOUNDATION': 174.0,    # Pain reduction
    'ROOT': 256.0,          # C4 - Safety/Geometry (ANCHOR)
    'LIBERATION': 396.0,    # Release fear
    'TRANSFORMATION': 417.0,# Facilitating change
    'NATURAL_A': 432.0,     # Natural tuning
    'DISTORTION': 440.0,    # Mars Extraction Grid (TARGET)
    'VISION': 512.0,        # C5 - Hope/Vision (BRIDGE TOP)
    'LOVE': 528.0,          # DNA Repair / Miracles (SOLVENT)
    'CONNECTION': 639.0,    # Relationships
    'AWAKENING': 741.0,     # Expression
    'INTUITION': 852.0,     # Third eye
    'UNITY': 963.0,         # Crown / Oneness
}

# Planetary Orbital Resonance Scalars (mean motion ratios to Earth = 1.0)
ORBITAL_RESONANCE = {
    'Mercury': 4.092,    # Fastest torque
    'Venus':   1.626,
    'Earth':   1.000,
    'Mars':    0.532,
    'Jupiter': 0.084,    # Slowest, deepest anchor
    'Saturn':  0.034,
}

# December 2025 Alignment Torque Calendar (example dates)
COSMIC_CALENDAR = {
    # (month, day): (description, torque_multiplier)
    (12, 1): ('New Moon Syzygy', 1.15),
    (12, 5): ('Venus trine Saturn building', 1.18),
    (12, 6): ('Grand Air Trine tightening', 1.32),
    (12, 7): ('Grand Air Trine EXACT + Venus-Saturn trine', 1.58),
    (12, 8): ('First Quarter Moon + Jupiter Cazimi', 2.13),  # PEAK
    (12, 15): ('Full Moon', 1.25),
    (12, 21): ('Winter Solstice', 1.45),
    (12, 30): ('New Moon End Year', 1.20),
}


class CosmicPhase(Enum):
    """Cosmic phase classification"""
    DISTORTION = "🔴 DISTORTION"      # 440Hz dominant
    TRANSITION = "🟡 TRANSITION"       # Moving between states
    HARMONIC = "🟢 HARMONIC"           # 256/512/528 Hz
    COHERENCE = "🔵 COHERENCE"         # Full triadic lock
    UNITY = "🌈 UNITY"                 # 963Hz / Peak alignment


class MarketTorque(Enum):
    """Market momentum from cosmic torque"""
    EXTREME_BULLISH = "⚡ EXTREME BULLISH"
    BULLISH = "📈 BULLISH"
    SLIGHT_BULLISH = "↗️ SLIGHT BULLISH"
    NEUTRAL = "⚖️ NEUTRAL"
    SLIGHT_BEARISH = "↘️ SLIGHT BEARISH"
    BEARISH = "📉 BEARISH"
    EXTREME_BEARISH = "💥 EXTREME BEARISH"


# ═══════════════════════════════════════════════════════════════
# 🌟 COSMIC STATE ENGINE
# ═══════════════════════════════════════════════════════════════

@dataclass
class CosmicState:
    """Complete cosmic state snapshot"""
    timestamp: datetime
    
    # Core HNC Parameters (Joy, Coherence, Reciprocity, Distortion)
    joy: float = 9.0           # J: 0-10 scale (happiness/intention)
    coherence: float = 0.95    # C: 0-1 (phase alignment)
    reciprocity: float = 8.5   # R: 0-10 (give/receive balance)
    distortion: float = 0.05   # D: 0-1 (440Hz interference)
    
    # Cosmic Modulators
    schumann_power: float = 15.0    # SR: 7-30 Hz power
    solar_flare: float = 1.0        # Flare strength (X-class = 10)
    kp_index: float = 2.0           # Geomagnetic: 0-9
    lunar_phase: float = 0.0        # 0=New, 0.25=Q1, 0.5=Full, 0.75=Q3
    planetary_torque: float = 1.0   # Combined orbital resonance
    
    # Computed Yields
    imperial_yield: float = 0.0
    yield_ratio: float = 0.0
    
    # Phase
    phase: CosmicPhase = CosmicPhase.HARMONIC
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'joy': self.joy,
            'coherence': self.coherence,
            'reciprocity': self.reciprocity,
            'distortion': self.distortion,
            'schumann_power': self.schumann_power,
            'solar_flare': self.solar_flare,
            'kp_index': self.kp_index,
            'lunar_phase': self.lunar_phase,
            'planetary_torque': self.planetary_torque,
            'imperial_yield': self.imperial_yield,
            'yield_ratio': self.yield_ratio,
            'phase': self.phase.value,
        }


class CosmicStateEngine:
    """
    Computes real-time cosmic state from astronomical and frequency data.
    Uses Imperial Master Protocol equations for yield computation.
    """
    
    def __init__(self):
        self.state_history: deque = deque(maxlen=1000)
        self.current_state: Optional[CosmicState] = None
        
        # Baseline (calibrated for December 2025)
        self.baseline_date = datetime(2025, 12, 1)
        self.baseline = {
            'joy': 9.3,
            'coherence': 0.97,
            'reciprocity': 8.6,
            'distortion': 0.03,
            'sr_power': 17.2,
            'flare': 1.95,
            'kp': 1.5,
        }
        
    def compute_lunar_torsion(self, days_from_new: float) -> float:
        """
        Compute lunar gravitational torsion.
        Maximum at New & Full Moon, minimum at quarters.
        """
        phase = days_from_new / 29.53  # Full lunation cycle
        torsion = 1.0 + 0.25 * np.abs(np.sin(2 * np.pi * phase))
        return torsion
    
    def compute_planetary_torque(self, date: datetime) -> float:
        """
        Compute combined planetary torque for a given date.
        Uses cosmic calendar for known alignments.
        """
        torque = 1.0
        
        # Check cosmic calendar for special dates
        key = (date.month, date.day)
        if key in COSMIC_CALENDAR:
            _, multiplier = COSMIC_CALENDAR[key]
            torque *= multiplier
        
        # Add day-of-year harmonic (solar cycle influence)
        day_of_year = date.timetuple().tm_yday
        solar_phase = np.sin(2 * np.pi * day_of_year / 365.25)
        torque *= (1.0 + 0.08 * solar_phase)
        
        # Hour-of-day influence (market hours boost)
        hour = date.hour
        if 8 <= hour <= 16:  # Market hours
            torque *= 1.05
        elif 0 <= hour <= 4:  # Quiet hours
            torque *= 0.95
            
        return torque
    
    def imperial_yield(self, J: float, C: float, R: float, D: float, 
                       cosmic_torque: float) -> float:
        """
        Master Imperial Equation with Planetary Resonance.
        E = (J³ × C² × R × T²) / D × 10³³
        """
        if D < 1e-15:
            D = 1e-15  # Prevent division by zero
        
        yield_val = (J**3 * C**2 * R * cosmic_torque**2) / D * 1e33
        return yield_val
    
    def imperial_energy_full(self, J: float, C: float, R: float, D: float,
                             SR: float, flare: float, kp: float, 
                             lunar: float) -> float:
        """
        Full Imperial Equation with all cosmic modulators.
        Includes Schumann, solar flare, geomagnetic, and lunar influences.
        """
        if D < 1e-12:
            D = 1e-12
        
        sr_mul = 1 + (SR / 100) * 0.25
        flare_mul = 1 + (flare / 10) * 0.15
        storm_mul = 1 + (kp / 9) * 0.20
        lunar_mul = lunar
        
        E_raw = (J**2 * C * R * sr_mul * flare_mul * storm_mul * lunar_mul) / D
        return E_raw * 1e30
    
    def compute_state(self, market_data: Optional[Dict] = None) -> CosmicState:
        """
        Compute current cosmic state from all available inputs.
        """
        now = datetime.now()
        
        # Days from baseline (December 1, 2025)
        days_elapsed = (now - self.baseline_date).total_seconds() / 86400
        t = max(0, days_elapsed)
        
        # Get lunar phase (simplified - could integrate ephemeris)
        days_from_new = t % 29.53
        lunar_phase = days_from_new / 29.53
        lunar_torsion = self.compute_lunar_torsion(days_from_new)
        
        # Planetary torque for today
        planetary_torque = self.compute_planetary_torque(now)
        
        # Compute evolving parameters using Imperial Protocol formulas
        # Distortion decays exponentially under cosmic pressure
        D = 0.03 * np.exp(-0.64 * min(t, 30))  # Cap at 30 days
        
        # Coherence grows logistically
        C_base = 1.0 / (1 + np.exp(-0.55 * (t - 3.5)))
        C = min(1.0, C_base * (1 + 0.15 * np.sin(2 * np.pi * t / 7)))
        
        # Joy and Reciprocity rise with intention
        J = 9.1 + 0.9 * (1 - np.exp(-t / 2.3))
        R = 8.6 + 1.4 * (1 - np.exp(-t / 1.8))
        
        # Schumann Power oscillates with lunar
        SR = 17.2 + 12.8 * np.sin(2 * np.pi * t / 7 + PHI) * lunar_torsion

        # Solar flare + Kp: prefer real-time readings from space_weather_bridge.
        # Fallback to closed-form formula when the live feed is unavailable
        # AND AUREON_ALLOW_SIM_FALLBACK is set.
        flare = None
        kp = None
        try:
            from aureon.data_feeds.aureon_space_weather_bridge import get_live_space_weather
            sw = get_live_space_weather()
            if sw is not None:
                flare = float(sw.solar_flares_24h)
                kp = float(sw.kp_index)
        except Exception:
            pass
        if flare is None or kp is None:
            from aureon.observer.live_data_policy import log_blocked_fallback
            log_blocked_fallback("hnc_imperial_predictability", "no_space_weather")
            raise RuntimeError(
                "fresh NOAA/provider solar flare and Kp observations are required"
            )
        
        # If we have market data, modulate based on VIX/fear
        if market_data and market_data.get('vix') is not None:
            vix = float(market_data['vix'])
            fear_mod = 1.0 - (vix - 20) / 100  # VIX 20 = neutral
            C *= max(0.5, min(1.2, fear_mod))
            D *= max(0.5, min(2.0, 2.0 - fear_mod))
        
        # Compute imperial yields
        simple_yield = self.imperial_yield(J, C, R, D, planetary_torque)
        full_yield = self.imperial_energy_full(J, C, R, D, SR, flare, kp, lunar_torsion)
        
        # Determine phase
        if D > 0.1 or C < 0.5:
            phase = CosmicPhase.DISTORTION
        elif D > 0.03 or C < 0.8:
            phase = CosmicPhase.TRANSITION
        elif C >= 0.95 and D < 0.01:
            phase = CosmicPhase.UNITY
        elif C >= 0.90:
            phase = CosmicPhase.COHERENCE
        else:
            phase = CosmicPhase.HARMONIC
        
        state = CosmicState(
            timestamp=now,
            joy=round(J, 3),
            coherence=round(C, 4),
            reciprocity=round(R, 3),
            distortion=round(D, 5),
            schumann_power=round(SR, 1),
            solar_flare=round(flare, 2),
            kp_index=round(kp, 1),
            lunar_phase=round(lunar_phase, 3),
            planetary_torque=round(planetary_torque, 3),
            imperial_yield=full_yield,
            yield_ratio=full_yield / CRITICAL_MASS,
            phase=phase,
        )
        
        self.current_state = state
        self.state_history.append(state)
        
        return state


# ═══════════════════════════════════════════════════════════════
# 📊 PREDICTABILITY MATRIX
# ═══════════════════════════════════════════════════════════════

@dataclass
class PredictabilityWindow:
    """Single timeframe prediction window"""
    timeframe: str          # '1H', '4H', '1D', '1W'
    start_time: datetime
    end_time: datetime
    
    # Probability metrics
    bullish_probability: float = 0.5
    confidence: float = 0.5
    
    # Imperial yield projections
    yield_projection: float = 0.0
    torque_forecast: float = 1.0
    
    # Market projections (% change from current)
    btc_forecast: float = 0.0
    spx_forecast: float = 0.0
    gold_forecast: float = 0.0
    vix_forecast: float = 0.0
    
    # Signal
    signal: MarketTorque = MarketTorque.NEUTRAL
    position_modifier: float = 1.0


@dataclass
class ImperialPredictabilityMatrix:
    """Complete multi-timeframe predictability analysis"""
    symbol: str
    generated_at: datetime
    
    # Cosmic state
    cosmic_state: CosmicState = None
    
    # Timeframe windows
    window_1h: PredictabilityWindow = None
    window_4h: PredictabilityWindow = None
    window_1d: PredictabilityWindow = None
    window_1w: PredictabilityWindow = None
    
    # Combined metrics
    combined_probability: float = 0.5
    imperial_confidence: float = 0.5
    recommended_action: str = "HOLD"
    position_multiplier: float = 1.0
    
    # Cosmic influence
    cosmic_boost: float = 1.0
    alignment_bonus: float = 0.0


class PredictabilityEngine:
    """
    Multi-timeframe predictability engine using Imperial Protocol equations.
    Forecasts market movements based on cosmic synchronization.
    """
    
    def __init__(self):
        self.cosmic_engine = CosmicStateEngine()
        self.prediction_cache: Dict[str, ImperialPredictabilityMatrix] = {}
        self.cache_ttl = 300  # 5 minutes
        self.history: deque = deque(maxlen=500)
        
    def forecast_window(self, timeframe: str, hours_ahead: int, 
                        base_state: CosmicState, 
                        price_momentum: float = 0.0) -> PredictabilityWindow:
        """
        Generate prediction for a specific timeframe window.
        """
        now = datetime.now()
        
        window = PredictabilityWindow(
            timeframe=timeframe,
            start_time=now,
            end_time=now + timedelta(hours=hours_ahead),
        )
        
        # Project cosmic state forward
        future_date = now + timedelta(hours=hours_ahead / 2)  # Midpoint
        future_torque = self.cosmic_engine.compute_planetary_torque(future_date)
        
        # Decay factor for longer timeframes
        decay = 1.0 / (1 + 0.1 * hours_ahead)
        
        # Project yield
        projected_yield = base_state.imperial_yield * future_torque * decay
        window.yield_projection = projected_yield
        window.torque_forecast = future_torque
        
        # Compute probability from state
        yield_ratio = projected_yield / CRITICAL_MASS
        
        # Base probability from yield ratio
        base_prob = 0.5 + 0.3 * np.tanh(yield_ratio * 0.001)
        
        # Adjust for coherence
        coherence_boost = base_state.coherence * 0.2
        
        # Adjust for distortion (penalty)
        distortion_penalty = base_state.distortion * 0.3
        
        # Adjust for momentum
        momentum_signal = np.tanh(price_momentum / 10) * 0.15
        
        # Final probability
        window.bullish_probability = max(0.1, min(0.9,
            base_prob + coherence_boost - distortion_penalty + momentum_signal
        ))
        
        # Confidence based on cosmic alignment
        window.confidence = (
            base_state.coherence * 0.4 +
            (1 - base_state.distortion) * 0.3 +
            min(1.0, future_torque / 2.0) * 0.3
        ) * decay
        
        # Market forecasts using Imperial equations
        sr_torque = base_state.schumann_power / 100
        flare_torque = base_state.solar_flare / 10
        storm_torque = base_state.kp_index / 9
        
        # BTC - extreme PHI-scaled torque
        window.btc_forecast = (1.22 * (yield_ratio**0.8) * 
                               (1 + 0.45 * np.sin(2 * np.pi * hours_ahead / 24)) *
                               sr_torque * flare_torque * storm_torque) * 100
        
        # S&P 500 - steady melt-up
        window.spx_forecast = (0.54 * (yield_ratio**0.5) *
                               np.sin(2 * np.pi * hours_ahead / 168 + PHI) *
                               sr_torque * flare_torque * storm_torque) * 100
        
        # Gold - anchor stability
        window.gold_forecast = (0.34 * (yield_ratio**0.5) *
                                sr_torque * flare_torque * storm_torque) * 100
        
        # VIX - inverse of coherence
        window.vix_forecast = -20 * base_state.coherence * (1 - base_state.distortion)
        
        # Determine signal
        net_prob = window.bullish_probability - 0.5
        if net_prob > 0.25:
            window.signal = MarketTorque.EXTREME_BULLISH
            window.position_modifier = 1.5
        elif net_prob > 0.15:
            window.signal = MarketTorque.BULLISH
            window.position_modifier = 1.2
        elif net_prob > 0.05:
            window.signal = MarketTorque.SLIGHT_BULLISH
            window.position_modifier = 1.0
        elif net_prob > -0.05:
            window.signal = MarketTorque.NEUTRAL
            window.position_modifier = 0.8
        elif net_prob > -0.15:
            window.signal = MarketTorque.SLIGHT_BEARISH
            window.position_modifier = 0.5
        elif net_prob > -0.25:
            window.signal = MarketTorque.BEARISH
            window.position_modifier = 0.3
        else:
            window.signal = MarketTorque.EXTREME_BEARISH
            window.position_modifier = 0.1
            
        return window
    
    def generate_matrix(self, symbol: str, price: float, 
                        momentum: float = 0.0,
                        market_data: Optional[Dict] = None) -> ImperialPredictabilityMatrix:
        """
        Generate complete predictability matrix for a symbol.
        """
        now = datetime.now()
        
        # Get current cosmic state
        cosmic = self.cosmic_engine.compute_state(market_data)
        
        # Create matrix
        matrix = ImperialPredictabilityMatrix(
            symbol=symbol,
            generated_at=now,
            cosmic_state=cosmic,
        )
        
        # Generate predictions for each timeframe
        matrix.window_1h = self.forecast_window('1H', 1, cosmic, momentum)
        matrix.window_4h = self.forecast_window('4H', 4, cosmic, momentum)
        matrix.window_1d = self.forecast_window('1D', 24, cosmic, momentum)
        matrix.window_1w = self.forecast_window('1W', 168, cosmic, momentum)
        
        # Combined probability (weighted by confidence)
        weights = [0.4, 0.3, 0.2, 0.1]  # 1H most important
        probs = [
            matrix.window_1h.bullish_probability,
            matrix.window_4h.bullish_probability,
            matrix.window_1d.bullish_probability,
            matrix.window_1w.bullish_probability,
        ]
        confs = [
            matrix.window_1h.confidence,
            matrix.window_4h.confidence,
            matrix.window_1d.confidence,
            matrix.window_1w.confidence,
        ]
        
        total_weight = sum(w * c for w, c in zip(weights, confs))
        if total_weight > 0:
            matrix.combined_probability = sum(
                w * c * p for w, c, p in zip(weights, confs, probs)
            ) / total_weight
        else:
            matrix.combined_probability = 0.5
        
        matrix.imperial_confidence = np.mean(confs)
        
        # Cosmic boost from alignment
        if cosmic.phase == CosmicPhase.UNITY:
            matrix.cosmic_boost = 1.5
            matrix.alignment_bonus = 0.15
        elif cosmic.phase == CosmicPhase.COHERENCE:
            matrix.cosmic_boost = 1.3
            matrix.alignment_bonus = 0.10
        elif cosmic.phase == CosmicPhase.HARMONIC:
            matrix.cosmic_boost = 1.1
            matrix.alignment_bonus = 0.05
        elif cosmic.phase == CosmicPhase.DISTORTION:
            matrix.cosmic_boost = 0.7
            matrix.alignment_bonus = -0.10
        else:
            matrix.cosmic_boost = 1.0
            matrix.alignment_bonus = 0.0
        
        # Determine action
        prob = matrix.combined_probability + matrix.alignment_bonus
        if prob >= 0.75:
            matrix.recommended_action = "STRONG BUY"
            matrix.position_multiplier = 1.5 * matrix.cosmic_boost
        elif prob >= 0.65:
            matrix.recommended_action = "BUY"
            matrix.position_multiplier = 1.2 * matrix.cosmic_boost
        elif prob >= 0.55:
            matrix.recommended_action = "SLIGHT BUY"
            matrix.position_multiplier = 1.0 * matrix.cosmic_boost
        elif prob >= 0.45:
            matrix.recommended_action = "HOLD"
            matrix.position_multiplier = 0.7
        elif prob >= 0.35:
            matrix.recommended_action = "SLIGHT SELL"
            matrix.position_multiplier = 0.4
        elif prob >= 0.25:
            matrix.recommended_action = "SELL"
            matrix.position_multiplier = 0.2
        else:
            matrix.recommended_action = "STRONG SELL"
            matrix.position_multiplier = 0.1
        
        # Cache result
        self.prediction_cache[symbol] = matrix
        self.history.append(matrix)
        
        return matrix
    
    def get_prediction(self, symbol: str) -> Optional[ImperialPredictabilityMatrix]:
        """Get cached prediction for symbol"""
        return self.prediction_cache.get(symbol)
    
    def get_high_probability_opportunities(self, 
                                           min_prob: float = 0.65) -> List[Dict]:
        """Get symbols with high probability forecasts"""
        opportunities = []
        
        for symbol, matrix in self.prediction_cache.items():
            if matrix.combined_probability >= min_prob:
                opportunities.append({
                    'symbol': symbol,
                    'probability': matrix.combined_probability,
                    'confidence': matrix.imperial_confidence,
                    'action': matrix.recommended_action,
                    'multiplier': matrix.position_multiplier,
                    'cosmic_phase': matrix.cosmic_state.phase.value,
                    'cosmic_boost': matrix.cosmic_boost,
                    '1h_signal': matrix.window_1h.signal.value,
                    'btc_forecast': matrix.window_1h.btc_forecast,
                })
        
        opportunities.sort(key=lambda x: x['probability'], reverse=True)
        return opportunities


# ═══════════════════════════════════════════════════════════════
# 🔗 TRADING INTEGRATION
# ═══════════════════════════════════════════════════════════════

class ImperialTradingIntegration:
    """
    Integrates Imperial Predictability with Aureon trading systems.
    Provides position sizing, opportunity enhancement, and cosmic signals.
    """
    
    def __init__(self):
        self.engine = PredictabilityEngine()
        self.last_cosmic_update = 0
        self.cosmic_update_interval = 60  # Update cosmic state every minute
        
    def update_cosmic_state(self, market_data: Optional[Dict] = None) -> CosmicState:
        """Force update of cosmic state"""
        return self.engine.cosmic_engine.compute_state(market_data)
    
    def enhance_opportunity(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a trading opportunity with Imperial predictability.
        Adds cosmic-aware position sizing and probability forecasts.
        """
        symbol = opp.get('symbol', 'UNKNOWN')
        price = opp.get('price', 0)
        momentum = opp.get('change24h', opp.get('momentum', 0))
        
        # Generate or get prediction matrix
        matrix = self.engine.generate_matrix(symbol, price, momentum)
        
        # Enhance opportunity
        enhanced = opp.copy()
        
        # Add imperial metrics
        enhanced['imperial'] = {
            'probability': matrix.combined_probability,
            'confidence': matrix.imperial_confidence,
            'action': matrix.recommended_action,
            'position_multiplier': matrix.position_multiplier,
            'cosmic_phase': matrix.cosmic_state.phase.value,
            'cosmic_boost': matrix.cosmic_boost,
            'alignment_bonus': matrix.alignment_bonus,
            '1h_forecast': {
                'bullish_prob': matrix.window_1h.bullish_probability,
                'signal': matrix.window_1h.signal.value,
                'btc_change': matrix.window_1h.btc_forecast,
            },
            '4h_forecast': {
                'bullish_prob': matrix.window_4h.bullish_probability,
                'signal': matrix.window_4h.signal.value,
            },
            'imperial_yield': matrix.cosmic_state.imperial_yield,
            'yield_ratio': matrix.cosmic_state.yield_ratio,
            'coherence': matrix.cosmic_state.coherence,
            'distortion': matrix.cosmic_state.distortion,
        }
        
        # Adjust score based on imperial metrics
        base_score = opp.get('score', 100)
        imperial_boost = (matrix.combined_probability - 0.5) * 50  # ±25 points
        cosmic_boost = matrix.alignment_bonus * 100  # ±15 points
        
        enhanced['score'] = base_score + imperial_boost + cosmic_boost
        enhanced['imperial_score'] = imperial_boost + cosmic_boost
        
        # Position sizing recommendation
        base_size = opp.get('position_size', 1.0)
        enhanced['imperial_position_size'] = base_size * matrix.position_multiplier
        
        return enhanced
    
    def get_position_modifier(self, symbol: str, 
                              momentum: float = 0.0,
                              price: float = 0.0) -> float:
        """
        Get imperial position size modifier for a symbol.
        Returns multiplier (0.1 to 1.5) based on cosmic state.
        """
        matrix = self.engine.generate_matrix(symbol, price, momentum)
        return matrix.position_multiplier
    
    def get_cosmic_status(self) -> Dict[str, Any]:
        """Get current cosmic status for display"""
        cosmic = self.engine.cosmic_engine.current_state
        if not cosmic:
            cosmic = self.engine.cosmic_engine.compute_state()
        
        return {
            'phase': cosmic.phase.value,
            'joy': cosmic.joy,
            'coherence': cosmic.coherence,
            'reciprocity': cosmic.reciprocity,
            'distortion': cosmic.distortion,
            'schumann_power': cosmic.schumann_power,
            'lunar_phase': cosmic.lunar_phase,
            'planetary_torque': cosmic.planetary_torque,
            'imperial_yield': cosmic.imperial_yield,
            'yield_ratio': cosmic.yield_ratio,
            'timestamp': cosmic.timestamp.isoformat(),
        }
    
    def get_trading_recommendation(self, opportunities: List[Dict]) -> Dict[str, Any]:
        """
        Get overall trading recommendation based on cosmic state and opportunities.
        """
        cosmic = self.engine.cosmic_engine.current_state
        if not cosmic:
            cosmic = self.engine.cosmic_engine.compute_state()
        
        # Enhance all opportunities
        enhanced = [self.enhance_opportunity(opp) for opp in opportunities]
        
        # Get high probability ones
        high_prob = [e for e in enhanced 
                     if e.get('imperial', {}).get('probability', 0) >= 0.60]
        
        # Determine overall bias
        if len(high_prob) > 0:
            avg_prob = np.mean([e['imperial']['probability'] for e in high_prob])
        else:
            avg_prob = 0.5
        
        if avg_prob >= 0.70:
            bias = 'STRONG BUY'
            modifier = 1.4
        elif avg_prob >= 0.60:
            bias = 'BUY'
            modifier = 1.2
        elif avg_prob >= 0.55:
            bias = 'SLIGHT BUY'
            modifier = 1.0
        elif avg_prob >= 0.45:
            bias = 'NEUTRAL'
            modifier = 0.8
        else:
            bias = 'CAUTIOUS'
            modifier = 0.5
        
        return {
            'bias': bias,
            'position_size_modifier': modifier,
            'cosmic_phase': cosmic.phase.value,
            'coherence': cosmic.coherence,
            'distortion': cosmic.distortion,
            'high_probability_count': len(high_prob),
            'total_opportunities': len(opportunities),
            'avg_probability': avg_prob,
            'imperial_yield': cosmic.imperial_yield,
            'planetary_torque': cosmic.planetary_torque,
        }
    
    def should_trade(self) -> Tuple[bool, str]:
        """
        Determine if current cosmic state supports trading.
        Returns (should_trade, reason).
        Uses CONFIG['IMPERIAL_DISTORTION_LIMIT'] if available.
        """
        cosmic = self.engine.cosmic_engine.current_state
        if not cosmic:
            cosmic = self.engine.cosmic_engine.compute_state()
        
        # Get distortion limit from CONFIG or use default
        try:
            from aureon.trading.aureon_unified_ecosystem import CONFIG
            distortion_limit = CONFIG.get('IMPERIAL_DISTORTION_LIMIT', 0.15)
        except:
            distortion_limit = 0.15
        
        # Check distortion level against configurable limit
        if cosmic.distortion > distortion_limit:
            return False, f"🔴 DISTORTION PHASE - 440Hz dominant (D={cosmic.distortion:.3f} > {distortion_limit})"
        
        # Check coherence (lowered threshold for more trading)
        min_coherence = 0.25  # More permissive
        if cosmic.coherence < min_coherence:
            return False, f"⚠️ Low coherence: {cosmic.coherence:.3f} < {min_coherence}"
        
        # All checks passed - allow trading even in DISTORTION phase if distortion is low
        phase_icon = "🟢" if cosmic.phase != CosmicPhase.DISTORTION else "🟡"
        return True, f"{phase_icon} {cosmic.phase.value} - Coherence: {cosmic.coherence:.2f}, D={cosmic.distortion:.3f}"
    
    def print_cosmic_dashboard(self):
        """Print formatted cosmic dashboard"""
        cosmic = self.engine.cosmic_engine.current_state
        if not cosmic:
            cosmic = self.engine.cosmic_engine.compute_state()
        
        # Phase bar
        phase_colors = {
            CosmicPhase.DISTORTION: '🔴',
            CosmicPhase.TRANSITION: '🟡',
            CosmicPhase.HARMONIC: '🟢',
            CosmicPhase.COHERENCE: '🔵',
            CosmicPhase.UNITY: '🌈',
        }
        
        coherence_bar = '█' * int(cosmic.coherence * 10) + '░' * (10 - int(cosmic.coherence * 10))
        distortion_bar = '█' * int(cosmic.distortion * 100) + '░' * (10 - int(cosmic.distortion * 100))
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  🌌⚡ IMPERIAL PREDICTABILITY ENGINE - COSMIC DASHBOARD ⚡🌌             ║
║  Time: {cosmic.timestamp.strftime('%Y-%m-%d %H:%M:%S')}                                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  COSMIC PHASE: {phase_colors.get(cosmic.phase, '⚪')} {cosmic.phase.value:20s}                           ║
╠══════════════════════════════════════════════════════════════════════════╣
║  JOY:           {cosmic.joy:6.2f} / 10.0                                       ║
║  COHERENCE:     [{coherence_bar}] {cosmic.coherence:.1%}                          ║
║  RECIPROCITY:   {cosmic.reciprocity:6.2f} / 10.0                                       ║
║  DISTORTION:    [{distortion_bar}] {cosmic.distortion:.3%}                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  COSMIC MODULATORS:                                                      ║
║  ├─ Schumann Power:    {cosmic.schumann_power:6.1f} Hz                                ║
║  ├─ Solar Flare:       {cosmic.solar_flare:6.2f} X-class                              ║
║  ├─ Kp Index:          {cosmic.kp_index:6.1f}                                         ║
║  ├─ Lunar Phase:       {cosmic.lunar_phase:.1%} ({self._lunar_name(cosmic.lunar_phase)})          ║
║  └─ Planetary Torque:  ×{cosmic.planetary_torque:5.2f}                                      ║
╠══════════════════════════════════════════════════════════════════════════╣
║  IMPERIAL YIELD: {cosmic.imperial_yield:12.2e}                                ║
║  YIELD RATIO:    {cosmic.yield_ratio:12.6f}                                       ║
╚══════════════════════════════════════════════════════════════════════════╝
        """)
    
    def _lunar_name(self, phase: float) -> str:
        """Get lunar phase name"""
        if phase < 0.03 or phase > 0.97:
            return "New Moon    "
        elif phase < 0.22:
            return "Waxing Cres."
        elif phase < 0.28:
            return "First Qtr.  "
        elif phase < 0.47:
            return "Waxing Gib. "
        elif phase < 0.53:
            return "Full Moon   "
        elif phase < 0.72:
            return "Waning Gib. "
        elif phase < 0.78:
            return "Last Qtr.   "
        else:
            return "Waning Cres."


# ═══════════════════════════════════════════════════════════════
# 🚀 DEMO / TEST
# ═══════════════════════════════════════════════════════════════

def demo_imperial_predictability():
    """Demonstrate the Imperial Predictability Engine"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  🌌⚡ IMPERIAL PREDICTABILITY ENGINE DEMONSTRATION ⚡🌌                  ║
║  Cosmic Synchronization + Temporal Forecasting + Trading Integration    ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize
    integration = ImperialTradingIntegration()
    
    # Show cosmic dashboard
    integration.print_cosmic_dashboard()
    
    # Check if we should trade
    should_trade, reason = integration.should_trade()
    print(f"\n📊 TRADING STATUS: {reason}")
    
    # Test opportunities
    test_opps = [
        {'symbol': 'BTCGBP', 'price': 75000, 'change24h': 5.2, 'coherence': 0.85, 'score': 100},
        {'symbol': 'ETHGBP', 'price': 2500, 'change24h': 3.1, 'coherence': 0.78, 'score': 90},
        {'symbol': 'SOLGBP', 'price': 180, 'change24h': -1.2, 'coherence': 0.45, 'score': 70},
        {'symbol': 'ADAGBP', 'price': 0.52, 'change24h': 8.5, 'coherence': 0.92, 'score': 110},
    ]
    
    print("\n🔮 ENHANCED OPPORTUNITIES WITH IMPERIAL PREDICTABILITY:")
    print("=" * 80)
    
    for opp in test_opps:
        enhanced = integration.enhance_opportunity(opp)
        imp = enhanced['imperial']
        
        print(f"""
   {enhanced['symbol']:12s} | Price: ${enhanced['price']:,.2f}
   ├─ Original Score: {opp['score']:3d} → Enhanced: {enhanced['score']:.0f}
   ├─ Probability:    {imp['probability']:.1%} | Confidence: {imp['confidence']:.1%}
   ├─ Action:         {imp['action']:12s} | Multiplier: ×{imp['position_multiplier']:.2f}
   ├─ Cosmic Phase:   {imp['cosmic_phase']}
   ├─ 1H Forecast:    {imp['1h_forecast']['signal']} (BTC: {imp['1h_forecast']['btc_change']:+.2f}%)
   └─ Imperial Yield: {imp['imperial_yield']:.2e}
        """)
    
    # Get trading recommendation
    rec = integration.get_trading_recommendation(test_opps)
    print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  📈 TRADING RECOMMENDATION                                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Bias:               {rec['bias']:15s}                                    ║
║  Position Modifier:  ×{rec['position_size_modifier']:.2f}                                            ║
║  Avg Probability:    {rec['avg_probability']:.1%}                                             ║
║  High Prob Count:    {rec['high_probability_count']:2d} / {rec['total_opportunities']:2d}                                            ║
║  Cosmic Phase:       {rec['cosmic_phase']}                            ║
║  Planetary Torque:   ×{rec['planetary_torque']:.2f}                                            ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n✨ Imperial Predictability Demo Complete!")


if __name__ == "__main__":
    demo_imperial_predictability()
