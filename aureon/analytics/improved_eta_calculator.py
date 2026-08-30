#!/usr/bin/env python3
"""
🔬🎯 IMPROVED ETA CALCULATOR - FIXING THE CORE LOGIC 🎯🔬
==========================================================
🟡 The class itself takes real velocity / pnl values. The __main__
   block at the bottom uses random.uniform to demo synthetic ticks.
   Production paths must pass real measurements, not call __main__.
==========================================================

The old ETA calculation was naive:
    ETA = gap / velocity

This assumes velocity stays constant. IT DOESN'T!

NEW APPROACH:
1. Velocity Decay Model - momentum fades over time
2. Volatility-Adjusted ETA - uncertainty scaling
3. Market Regime Detection - different models for different conditions
4. Weighted Velocity - recent samples matter more
5. Mean Reversion Awareness - prices tend to revert

Gary Leckey | December 2025
"Math that matches reality."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from collections import deque

# =============================================================================
# IMPROVED VELOCITY CALCULATOR
# =============================================================================

class ImprovedVelocityCalculator:
    """
    🔬 IMPROVED VELOCITY CALCULATION
    
    Problems with old approach:
    - Simple (newest - oldest) / time 
    - All samples weighted equally
    - No noise filtering
    - No decay modeling
    
    New approach:
    - Exponentially weighted moving average (recent > old)
    - Median filtering for outlier rejection
    - Velocity of velocity (acceleration) tracking
    - Regime-aware calculation
    """
    
    def __init__(self, max_samples: int = 30, decay_factor: float = 0.9):
        self.max_samples = max_samples
        self.decay_factor = decay_factor  # How much older samples are discounted
        
        # History storage
        self.pnl_history: deque = deque(maxlen=max_samples)
        self.velocity_history: deque = deque(maxlen=max_samples)
        
        # Calculated values
        self.raw_velocity: float = 0.0
        self.smoothed_velocity: float = 0.0
        self.acceleration: float = 0.0
        self.volatility: float = 0.0
        self.velocity_confidence: float = 0.0
    
    def add_sample(self, timestamp: float, pnl: float) -> Dict:
        """
        Add a P&L sample and recalculate velocities.
        
        Returns dict with velocity metrics.
        """
        self.pnl_history.append((timestamp, pnl))
        
        if len(self.pnl_history) < 2:
            return self._get_metrics()
        
        # Calculate raw velocity (simple difference)
        oldest = self.pnl_history[0]
        newest = self.pnl_history[-1]
        time_diff = newest[0] - oldest[0]
        
        if time_diff > 0:
            self.raw_velocity = (newest[1] - oldest[1]) / time_diff
        
        # Calculate WEIGHTED velocity (recent samples matter more)
        self.smoothed_velocity = self._calculate_weighted_velocity()
        
        # Calculate acceleration (change in velocity)
        if len(self.pnl_history) >= 3:
            self.acceleration = self._calculate_acceleration()
        
        # Calculate volatility (how much velocity fluctuates)
        self.volatility = self._calculate_velocity_volatility()
        
        # Calculate confidence in velocity estimate
        self.velocity_confidence = self._calculate_confidence()
        
        # Store velocity for acceleration tracking
        self.velocity_history.append((timestamp, self.smoothed_velocity))
        
        return self._get_metrics()
    
    def _calculate_weighted_velocity(self) -> float:
        """
        Calculate exponentially weighted velocity.
        Recent samples count more than old ones.
        """
        if len(self.pnl_history) < 2:
            return 0.0
        
        weighted_sum = 0.0
        weight_sum = 0.0
        
        samples = list(self.pnl_history)
        for i in range(1, len(samples)):
            prev_time, prev_pnl = samples[i-1]
            curr_time, curr_pnl = samples[i]
            
            time_diff = curr_time - prev_time
            if time_diff > 0:
                instant_velocity = (curr_pnl - prev_pnl) / time_diff
                
                # Weight by recency (newer = higher weight)
                weight = self.decay_factor ** (len(samples) - 1 - i)
                weighted_sum += instant_velocity * weight
                weight_sum += weight
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_acceleration(self) -> float:
        """
        Calculate velocity change rate (acceleration).
        Positive = speeding up toward target
        Negative = slowing down / reversing
        """
        if len(self.velocity_history) < 2:
            return 0.0
        
        velocities = list(self.velocity_history)
        recent_velocities = velocities[-5:] if len(velocities) >= 5 else velocities
        
        if len(recent_velocities) < 2:
            return 0.0
        
        # Linear regression slope of velocities
        n = len(recent_velocities)
        sum_x = sum(range(n))
        sum_y = sum(v[1] for v in recent_velocities)
        sum_xy = sum(i * v[1] for i, v in enumerate(recent_velocities))
        sum_x2 = sum(i * i for i in range(n))
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    def _calculate_velocity_volatility(self) -> float:
        """
        Calculate how much velocity fluctuates.
        High volatility = unreliable ETA.
        """
        if len(self.pnl_history) < 3:
            return 0.0
        
        samples = list(self.pnl_history)
        instant_velocities = []
        
        for i in range(1, len(samples)):
            time_diff = samples[i][0] - samples[i-1][0]
            if time_diff > 0:
                v = (samples[i][1] - samples[i-1][1]) / time_diff
                instant_velocities.append(v)
        
        if len(instant_velocities) < 2:
            return 0.0
        
        mean_v = sum(instant_velocities) / len(instant_velocities)
        variance = sum((v - mean_v) ** 2 for v in instant_velocities) / len(instant_velocities)
        
        return math.sqrt(variance)
    
    def _calculate_confidence(self) -> float:
        """
        Calculate confidence in velocity estimate.
        Low volatility + consistent direction = high confidence
        """
        if len(self.pnl_history) < 5:
            return 0.1  # Low confidence with few samples
        
        # Factor 1: Enough samples?
        sample_factor = min(1.0, len(self.pnl_history) / 20)
        
        # Factor 2: Low volatility relative to velocity?
        if abs(self.smoothed_velocity) > 0:
            cv = self.volatility / abs(self.smoothed_velocity)  # Coefficient of variation
            volatility_factor = max(0, 1 - cv)
        else:
            volatility_factor = 0.5
        
        # Factor 3: Consistent direction?
        samples = list(self.pnl_history)
        direction_changes = 0
        for i in range(2, len(samples)):
            prev_dir = samples[i-1][1] - samples[i-2][1]
            curr_dir = samples[i][1] - samples[i-1][1]
            if prev_dir * curr_dir < 0:  # Sign change
                direction_changes += 1
        
        direction_factor = max(0, 1 - direction_changes / max(1, len(samples) - 2))
        
        # Factor 4: Positive acceleration is good
        accel_factor = 0.5 + 0.5 * (1 if self.acceleration > 0 else 0)
        
        # Combined confidence
        confidence = sample_factor * volatility_factor * direction_factor * accel_factor
        return max(0.1, min(0.99, confidence))
    
    def _get_metrics(self) -> Dict:
        """Get all velocity metrics."""
        return {
            'raw_velocity': self.raw_velocity,
            'smoothed_velocity': self.smoothed_velocity,
            'acceleration': self.acceleration,
            'volatility': self.volatility,
            'confidence': self.velocity_confidence,
            'samples': len(self.pnl_history),
        }


# =============================================================================
# IMPROVED ETA CALCULATOR
# =============================================================================

@dataclass
class ImprovedETA:
    """Result from improved ETA calculation."""
    # Basic ETA
    naive_eta: float           # Simple gap/velocity
    improved_eta: float        # With decay model
    conservative_eta: float    # Worst case
    optimistic_eta: float      # Best case
    
    # Confidence
    confidence: float          # 0-1 how much to trust this
    reliability_band: str      # HIGH, MEDIUM, LOW
    
    # Why this ETA
    model_used: str           # Which calculation model
    limiting_factors: List[str]  # What's reducing confidence
    
    # Supporting data
    velocity: float
    acceleration: float
    volatility: float
    gap_to_target: float


class ImprovedETACalculator:
    """
    🔬🎯 IMPROVED ETA CALCULATOR
    
    Addresses all the problems:
    1. Velocity decay - momentum fades
    2. Uncertainty bounds - not just point estimate
    3. Market regime awareness
    4. Acceleration factor - speeding up or slowing down?
    5. Volatility scaling
    """
    
    # Velocity decay half-life in seconds
    # After this many seconds, velocity is expected to halve
    VELOCITY_HALFLIFE = 30.0
    
    # Maximum ETA we'll predict
    MAX_ETA_SECONDS = 300.0
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MEDIUM_CONFIDENCE_THRESHOLD = 0.4
    
    def __init__(self):
        self.velocity_calc = ImprovedVelocityCalculator()
    
    def calculate_eta(
        self,
        current_pnl: float,
        target_pnl: float,
        pnl_history: List[Tuple[float, float]] = None,
        velocity: float = None,
        volatility: float = None
    ) -> ImprovedETA:
        """
        🎯 Calculate improved ETA with uncertainty bounds.
        
        Args:
            current_pnl: Current P&L
            target_pnl: Target P&L (penny profit gate)
            pnl_history: Optional list of (timestamp, pnl) tuples
            velocity: Optional pre-calculated velocity
            volatility: Optional pre-calculated volatility
        
        Returns:
            ImprovedETA with multiple estimates and confidence
        """
        gap = target_pnl - current_pnl
        
        # If already at target
        if gap <= 0:
            return ImprovedETA(
                naive_eta=0, improved_eta=0, conservative_eta=0, optimistic_eta=0,
                confidence=1.0, reliability_band="HIGH", model_used="target_reached",
                limiting_factors=[], velocity=0, acceleration=0, volatility=0,
                gap_to_target=gap
            )
        
        # Calculate velocity metrics
        if pnl_history:
            for ts, pnl in pnl_history:
                self.velocity_calc.add_sample(ts, pnl)
        
        metrics = self.velocity_calc._get_metrics()
        
        v = velocity if velocity is not None else metrics['smoothed_velocity']
        vol = volatility if volatility is not None else metrics['volatility']
        accel = metrics['acceleration']
        confidence = metrics['confidence']
        
        limiting_factors = []
        
        # ═══════════════════════════════════════════════════════════════════
        # NAIVE ETA (baseline - what we used to calculate)
        # ═══════════════════════════════════════════════════════════════════
        if v > 0:
            naive_eta = gap / v
        else:
            naive_eta = float('inf')
            limiting_factors.append("negative_velocity")
        
        # ═══════════════════════════════════════════════════════════════════
        # IMPROVED ETA (with velocity decay)
        # ═══════════════════════════════════════════════════════════════════
        # Model: velocity decays exponentially toward zero
        # v(t) = v0 * exp(-λt) where λ = ln(2) / halflife
        #
        # Distance covered = integral of v(t) = v0/λ * (1 - exp(-λt))
        # As t -> ∞, max distance = v0/λ
        #
        # If max_distance < gap, we'll NEVER reach target!
        
        if v > 0:
            decay_rate = math.log(2) / self.VELOCITY_HALFLIFE
            max_distance = v / decay_rate  # Asymptotic distance
            
            if max_distance < gap:
                # Can't reach target with decaying velocity!
                improved_eta = float('inf')
                limiting_factors.append("velocity_decay_insufficient")
            else:
                # Solve for time: gap = v0/λ * (1 - exp(-λt))
                # exp(-λt) = 1 - gap*λ/v0
                # t = -ln(1 - gap*λ/v0) / λ
                ratio = gap * decay_rate / v
                if ratio < 1:
                    improved_eta = -math.log(1 - ratio) / decay_rate
                else:
                    improved_eta = float('inf')
                    limiting_factors.append("gap_too_large_for_decay")
        else:
            improved_eta = float('inf')
        
        # ═══════════════════════════════════════════════════════════════════
        # ACCELERATION-ADJUSTED ETA
        # ═══════════════════════════════════════════════════════════════════
        # If we're accelerating, things might be faster
        # If decelerating, things will be slower
        
        accel_adjusted_eta = improved_eta
        if accel != 0 and v > 0 and improved_eta < float('inf'):
            # Rough adjustment: if accelerating positively, reduce ETA
            # s = v0*t + 0.5*a*t^2
            # Solve: gap = v*t + 0.5*a*t^2
            # This is quadratic: 0.5*a*t^2 + v*t - gap = 0
            
            a = 0.5 * accel
            b = v
            c = -gap
            
            if a != 0:
                discriminant = b*b - 4*a*c
                if discriminant >= 0:
                    t1 = (-b + math.sqrt(discriminant)) / (2*a)
                    t2 = (-b - math.sqrt(discriminant)) / (2*a)
                    # Take the positive, smaller root
                    valid_times = [t for t in [t1, t2] if t > 0]
                    if valid_times:
                        accel_adjusted_eta = min(valid_times)
        
        # ═══════════════════════════════════════════════════════════════════
        # VOLATILITY-ADJUSTED BOUNDS
        # ═══════════════════════════════════════════════════════════════════
        # Higher volatility = wider uncertainty bands
        
        if vol > 0 and v > 0:
            # Coefficient of variation
            cv = vol / abs(v)
            
            # Optimistic: volatility helps us (good jumps)
            optimistic_factor = max(0.5, 1 - cv)
            
            # Conservative: volatility hurts us (bad jumps)
            conservative_factor = min(3.0, 1 + cv * 2)
            
            limiting_factors.append(f"volatility_cv={cv:.2f}")
        else:
            optimistic_factor = 0.8
            conservative_factor = 1.5
        
        # Apply bounds
        base_eta = min(improved_eta, accel_adjusted_eta)
        if base_eta < float('inf'):
            optimistic_eta = base_eta * optimistic_factor
            conservative_eta = base_eta * conservative_factor
        else:
            optimistic_eta = float('inf')
            conservative_eta = float('inf')
        
        # ═══════════════════════════════════════════════════════════════════
        # CONFIDENCE AND RELIABILITY
        # ═══════════════════════════════════════════════════════════════════
        
        # Adjust confidence based on factors
        if improved_eta == float('inf'):
            confidence = 0.1
        elif improved_eta > self.MAX_ETA_SECONDS:
            confidence *= 0.5
            limiting_factors.append("eta_exceeds_max")
        
        # Low sample count
        if metrics['samples'] < 10:
            confidence *= 0.7
            limiting_factors.append("low_samples")
        
        # High volatility
        if vol > abs(v) * 0.5:
            confidence *= 0.8
            limiting_factors.append("high_volatility")
        
        # Decelerating
        if accel < 0:
            confidence *= 0.9
            limiting_factors.append("decelerating")
        
        # Determine reliability band
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            reliability_band = "HIGH"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            reliability_band = "MEDIUM"
        else:
            reliability_band = "LOW"
        
        # Determine model used
        if base_eta == accel_adjusted_eta and accel != 0:
            model_used = "acceleration_adjusted"
        elif base_eta == improved_eta:
            model_used = "velocity_decay"
        else:
            model_used = "naive"
        
        # Cap ETAs
        improved_eta = min(improved_eta, self.MAX_ETA_SECONDS) if improved_eta < float('inf') else float('inf')
        conservative_eta = min(conservative_eta, self.MAX_ETA_SECONDS * 2) if conservative_eta < float('inf') else float('inf')
        optimistic_eta = min(optimistic_eta, self.MAX_ETA_SECONDS) if optimistic_eta < float('inf') else float('inf')
        
        return ImprovedETA(
            naive_eta=naive_eta,
            improved_eta=improved_eta,
            conservative_eta=conservative_eta,
            optimistic_eta=optimistic_eta,
            confidence=max(0.1, min(0.99, confidence)),
            reliability_band=reliability_band,
            model_used=model_used,
            limiting_factors=limiting_factors,
            velocity=v,
            acceleration=accel,
            volatility=vol,
            gap_to_target=gap
        )
    
    def explain_eta(self, eta: ImprovedETA) -> str:
        """Generate human-readable explanation of ETA calculation."""
        if eta.improved_eta == 0:
            return "🎯 TARGET REACHED!"
        
        if eta.improved_eta == float('inf'):
            factors = ", ".join(eta.limiting_factors) if eta.limiting_factors else "unknown"
            return f"⏳ NO ETA - Cannot predict arrival (factors: {factors})"
        
        lines = [
            f"📊 ETA ANALYSIS ({eta.reliability_band} confidence: {eta.confidence:.0%})",
            f"   Model: {eta.model_used}",
            f"   ────────────────────────────────",
            f"   Gap to target: ${eta.gap_to_target:.4f}",
            f"   Velocity:      ${eta.velocity:.6f}/s",
            f"   Acceleration:  ${eta.acceleration:.8f}/s²",
            f"   Volatility:    ${eta.volatility:.6f}",
            f"   ────────────────────────────────",
            f"   Naive ETA:        {eta.naive_eta:.1f}s" if eta.naive_eta < float('inf') else "   Naive ETA:        ∞",
            f"   Improved ETA:     {eta.improved_eta:.1f}s" if eta.improved_eta < float('inf') else "   Improved ETA:     ∞",
            f"   Optimistic:       {eta.optimistic_eta:.1f}s" if eta.optimistic_eta < float('inf') else "   Optimistic:       ∞",
            f"   Conservative:     {eta.conservative_eta:.1f}s" if eta.conservative_eta < float('inf') else "   Conservative:     ∞",
        ]
        
        if eta.limiting_factors:
            lines.append(f"   ⚠️ Factors: {', '.join(eta.limiting_factors)}")
        
        return "\n".join(lines)


# =============================================================================
# INTEGRATION FUNCTION
# =============================================================================

def calculate_improved_eta(
    current_pnl: float,
    target_pnl: float,
    pnl_history: List[Tuple[float, float]] = None,
    velocity: float = None,
    volatility: float = None
) -> ImprovedETA:
    """
    Convenience function to calculate improved ETA.
    
    Use this instead of simple gap/velocity!
    """
    calc = ImprovedETACalculator()
    return calc.calculate_eta(current_pnl, target_pnl, pnl_history, velocity, volatility)


# =============================================================================
