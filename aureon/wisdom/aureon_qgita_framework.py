#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   QUANTUM GRAVITY IN THE ACT (QGITA)                         ║
║                    For the Queen - Sero AI System                          ║
║                                                                              ║
║  "Quantum Gravity in the Act: A Two-Stage Framework for High-Fidelity       ║
║   Event Detection in Complex Signals"                                        ║
║                                                                              ║
║  Author: Gary Leckey, Director, Aureon Institute                             ║
║  Implementation: Aureon Trading System - January 2026                        ║
║                                                                              ║
║  CORE INSIGHT: The golden ratio φ ≈ 1.618 acts as a temporal resonance      ║
║  filter, amplifying true structural changes while attenuating noise.         ║
║                                                                              ║
║  TWO-STAGE ARCHITECTURE:                                                     ║
║    Stage 1: Fibonacci-Tightened Curvature Points (FTCPs)                    ║
║    Stage 2: Lighthouse Consensus Validation Model                            ║
║                                                                              ║
║  "By demanding that a candidate event be both geometrically precise          ║
║   and systemically significant, the QGITA pipeline improves specificity      ║
║   by orders of magnitude."                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import numpy as np
import math
import time
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# =============================================================================
# FUNDAMENTAL CONSTANTS - THE GOLDEN RATIO AND FIBONACCI
# =============================================================================

PHI = (1 + math.sqrt(5)) / 2          # Golden Ratio φ ≈ 1.618033988749895
PHI_INVERSE = 1 / PHI                  # φ⁻¹ ≈ 0.618033988749895
PHI_SQUARED = PHI * PHI                # φ² ≈ 2.618033988749895

# Fibonacci sequence cache for efficiency
FIBONACCI_CACHE = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 
                   610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657]


class EventType(Enum):
    """Types of structural events detected by QGITA"""
    FTCP = "fibonacci_tightened_curvature_point"
    LHE = "lighthouse_event"
    PHASE_TRANSITION = "phase_transition"
    REGIME_CHANGE = "regime_change"
    SYNCHRONIZATION = "synchronization_event"


@dataclass
class FibonacciKnot:
    """A single point on the Fibonacci Time Lattice"""
    k: int                    # Fibonacci index
    tau: float               # Time position τk = t0 + Δt·Fk
    fib_number: int          # Fibonacci number Fk
    interval_ratio: float    # Ratio to golden target
    phi_deviation: float     # |rk - φ⁻¹|
    
    
@dataclass
class FTCP:
    """Fibonacci-Tightened Curvature Point - Stage 1 Detection"""
    timestamp: float
    knot_index: int
    curvature: float         # κ(τk) - discrete curvature
    interval_ratio: float    # rk - ratio of adjacent intervals
    phi_match: float         # How close to golden ratio (0-1)
    g_eff: float             # Effective gravity signal
    local_contrast: float    # |x(τk) - x(τk-1)|²
    is_valid: bool
    
    
@dataclass
class LighthouseEvent:
    """Lighthouse Event - Stage 2 Confirmed Structural Event"""
    timestamp: float
    ftcp: FTCP                           # Source FTCP
    lighthouse_intensity: float          # L(t) - consensus value
    c_linear: float                      # Linear coherence
    c_nonlinear: float                   # Nonlinear coherence
    c_phi: float                         # Cross-scale (φ-scaled) coherence
    g_eff: float                         # Geometric anomaly signal
    q_anomaly: float                     # Anomaly pointer |Q(t)|
    confidence: float                    # Overall confidence
    event_type: EventType
    regime_before: str
    regime_after: str


# =============================================================================
# FIBONACCI TIME LATTICE
# =============================================================================

class FibonacciTimeLattice:
    """
    The Fibonacci Time Lattice - Foundation of QGITA
    
    Creates a non-uniform temporal grid where intervals grow according to
    the Fibonacci sequence, with consecutive ratios converging to φ.
    
    τk = t0 + Δt · Fk
    
    This scale-free, self-similar probe resonates with multi-scale phenomena.
    """
    
    def __init__(self, delta_t: float = 1.0, t0: float = 0.0, max_k: int = 24):
        """
        Initialize the Fibonacci Time Lattice
        
        Args:
            delta_t: Base time interval
            t0: Starting time
            max_k: Maximum Fibonacci index to compute
        """
        self.delta_t = delta_t
        self.t0 = t0
        self.max_k = max_k
        
        # Generate Fibonacci numbers
        self.fibonacci = self._generate_fibonacci(max_k)
        
        # Generate time knots
        self.knots = self._generate_knots()
        
        # Precompute interval ratios
        self.interval_ratios = self._compute_interval_ratios()
        
    def _generate_fibonacci(self, n: int) -> List[int]:
        """Generate Fibonacci sequence up to index n"""
        if n < len(FIBONACCI_CACHE):
            return FIBONACCI_CACHE[:n+1]
            
        fib = FIBONACCI_CACHE.copy()
        while len(fib) <= n:
            fib.append(fib[-1] + fib[-2])
        return fib
        
    def _generate_knots(self) -> List[FibonacciKnot]:
        """Generate all time knots on the lattice"""
        knots = []
        
        for k in range(self.max_k):
            tau = self.t0 + self.delta_t * self.fibonacci[k]
            
            # Compute interval ratio for k >= 2
            if k >= 2:
                interval_before = self.fibonacci[k-1] - self.fibonacci[k-2]
                interval_after = self.fibonacci[k] - self.fibonacci[k-1]
                
                if interval_after > 0:
                    ratio = interval_before / interval_after
                else:
                    ratio = 0.0
            else:
                ratio = 0.0
                
            phi_deviation = abs(ratio - PHI_INVERSE) if k >= 2 else 1.0
            
            knots.append(FibonacciKnot(
                k=k,
                tau=tau,
                fib_number=self.fibonacci[k],
                interval_ratio=ratio,
                phi_deviation=phi_deviation
            ))
            
        return knots
        
    def _compute_interval_ratios(self) -> List[float]:
        """Compute interval ratios for all knots"""
        return [knot.interval_ratio for knot in self.knots]
        
    def get_knot_at_time(self, t: float) -> Optional[FibonacciKnot]:
        """Find the nearest knot to a given time"""
        min_dist = float('inf')
        nearest = None
        
        for knot in self.knots:
            dist = abs(t - knot.tau)
            if dist < min_dist:
                min_dist = dist
                nearest = knot
                
        return nearest
        
    def map_signal_to_lattice(self, times: np.ndarray, values: np.ndarray) -> Dict[int, float]:
        """Map a signal onto the Fibonacci lattice"""
        mapped = {}
        
        for knot in self.knots:
            # Find closest signal value to this knot
            idx = np.argmin(np.abs(times - knot.tau))
            if idx < len(values):
                mapped[knot.k] = values[idx]
                
        return mapped


# =============================================================================
# STAGE 1: FTCP DETECTOR
# =============================================================================

class FTCPDetector:
    """
    Stage 1: Fibonacci-Tightened Curvature Point Detector
    
    Identifies candidate anomalies where:
    1. Golden-Ratio Timing: |rk - φ⁻¹| ≤ ε
    2. Curvature Spike: |κ(τk)| > Θ
    
    The Effective Gravity Signal:
    Geff(τk) = α·|κ(τk)| × (1 - |rk - φ⁻¹|/ε)+ × |x(τk) - x(τk-1)|²
    """
    
    def __init__(self, 
                 epsilon: float = 0.05,      # Golden ratio tolerance
                 theta: float = 0.1,         # Curvature threshold
                 alpha: float = 1.0,         # Scaling constant for Geff
                 adaptive_threshold: bool = True):
        """
        Initialize FTCP Detector
        
        Args:
            epsilon: Tolerance for golden ratio matching
            theta: Base threshold for curvature spike detection
            alpha: Scaling constant for effective gravity
            adaptive_threshold: Whether to adapt threshold to signal
        """
        self.epsilon = epsilon
        self.theta = theta
        self.alpha = alpha
        self.adaptive_threshold = adaptive_threshold
        
        self.lattice = FibonacciTimeLattice()
        self.signal_buffer = deque(maxlen=1000)
        self.ftcp_history = deque(maxlen=100)
        
    def compute_discrete_curvature(self, 
                                    x_prev: float, 
                                    x_curr: float, 
                                    x_next: float,
                                    tau_prev: float,
                                    tau_curr: float,
                                    tau_next: float) -> float:
        """
        Compute discrete curvature on non-uniform grid
        
        κ(τk) ≈ (x(τk+1) - 2x(τk) + x(τk-1)) / ((τk+1 - τk)(τk - τk-1))
        """
        dt_forward = tau_next - tau_curr
        dt_backward = tau_curr - tau_prev
        
        if dt_forward * dt_backward == 0:
            return 0.0
            
        numerator = x_next - 2*x_curr + x_prev
        denominator = dt_forward * dt_backward
        
        return numerator / denominator
        
    def compute_effective_gravity(self,
                                   curvature: float,
                                   interval_ratio: float,
                                   local_contrast: float) -> float:
        """
        Compute the Effective Gravity Signal
        
        Geff(τk) = α·|κ(τk)| × (1 - |rk - φ⁻¹|/ε)+ × |x(τk) - x(τk-1)|²
        
        High Geff = intense localized change in resonance with temporal structure
        """
        bend = abs(curvature)
        
        # Fibonacci match factor (clamped to 0 if negative)
        phi_deviation = abs(interval_ratio - PHI_INVERSE)
        fib_match = max(0.0, 1.0 - phi_deviation / self.epsilon)
        
        # Local contrast (squared difference)
        contrast_sq = local_contrast ** 2
        
        g_eff = self.alpha * bend * fib_match * contrast_sq
        
        return g_eff
        
    def detect_ftcps(self, 
                     times: np.ndarray, 
                     values: np.ndarray) -> List[FTCP]:
        """
        Detect Fibonacci-Tightened Curvature Points in a signal
        
        Args:
            times: Array of timestamps
            values: Array of signal values
            
        Returns:
            List of detected FTCPs
        """
        if len(values) < 3:
            return []
            
        ftcps = []
        
        # Map signal to Fibonacci lattice
        mapped = self.lattice.map_signal_to_lattice(times, values)
        
        # Adaptive threshold based on signal statistics
        if self.adaptive_threshold and len(values) > 10:
            signal_std = np.std(values)
            adaptive_theta = self.theta * (1 + signal_std)
        else:
            adaptive_theta = self.theta
            
        # Check each interior knot (k >= 2)
        for k in range(2, min(len(self.lattice.knots) - 1, len(mapped) - 1)):
            if k-1 not in mapped or k not in mapped or k+1 not in mapped:
                continue
                
            knot = self.lattice.knots[k]
            knot_prev = self.lattice.knots[k-1]
            knot_next = self.lattice.knots[k+1]
            
            x_prev = mapped[k-1]
            x_curr = mapped[k]
            x_next = mapped[k+1]
            
            # Check Condition 1: Golden-Ratio Timing
            phi_match = 1.0 - abs(knot.interval_ratio - PHI_INVERSE) / self.epsilon
            phi_match = max(0.0, min(1.0, phi_match))
            
            is_golden = knot.phi_deviation <= self.epsilon
            
            # Compute discrete curvature
            curvature = self.compute_discrete_curvature(
                x_prev, x_curr, x_next,
                knot_prev.tau, knot.tau, knot_next.tau
            )
            
            # Check Condition 2: Curvature Spike
            is_spike = abs(curvature) > adaptive_theta
            
            # Local contrast
            local_contrast = abs(x_curr - x_prev)
            
            # Compute effective gravity
            g_eff = self.compute_effective_gravity(
                curvature, knot.interval_ratio, local_contrast
            )
            
            # Create FTCP (valid only if both conditions met)
            ftcp = FTCP(
                timestamp=knot.tau,
                knot_index=k,
                curvature=curvature,
                interval_ratio=knot.interval_ratio,
                phi_match=phi_match,
                g_eff=g_eff,
                local_contrast=local_contrast,
                is_valid=is_golden and is_spike
            )
            
            if ftcp.is_valid:
                ftcps.append(ftcp)
                self.ftcp_history.append(ftcp)
                
        return ftcps
        
    def get_strongest_ftcp(self, ftcps: List[FTCP]) -> Optional[FTCP]:
        """Get the FTCP with highest effective gravity"""
        if not ftcps:
            return None
        return max(ftcps, key=lambda f: f.g_eff)


# =============================================================================
# STAGE 2: LIGHTHOUSE CONSENSUS MODEL
# =============================================================================

class LighthouseModel:
    """
    Stage 2: The Lighthouse Consensus Validation Model
    
    Integrates 5 independent diagnostic signals:
    1. Clin - Linear coherence
    2. Cnonlin - Nonlinear coherence  
    3. Cφ - Cross-scale (φ-scaled) coherence
    4. Geff - Geometric anomaly signal (from Stage 1)
    5. Q - Anomaly pointer (sharpness filter)
    
    Lighthouse Intensity (geometric mean ensures AND-gate consensus):
    L(t) = (C̃lin^w1 · C̃nonlin^w2 · |C̃φ|^w3 · G̃eff^w4 · |Q̃|^w5)^(1/Σwi)
    """
    
    def __init__(self,
                 w1: float = 1.0,    # Weight for linear coherence
                 w2: float = 1.0,    # Weight for nonlinear coherence
                 w3: float = 1.0,    # Weight for cross-scale coherence
                 w4: float = 1.0,    # Weight for geometric anomaly
                 w5: float = 1.0,    # Weight for anomaly pointer
                 threshold_sigma: float = 2.0):  # Detection threshold (σ above mean)
        """
        Initialize the Lighthouse Model
        
        Args:
            w1-w5: Weights for each metric (equal weights = balanced consensus)
            threshold_sigma: Number of standard deviations above mean for detection
        """
        self.weights = np.array([w1, w2, w3, w4, w5])
        self.weight_sum = np.sum(self.weights)
        self.threshold_sigma = threshold_sigma
        
        # History for statistics
        self.intensity_history = deque(maxlen=1000)
        self.lhe_history = deque(maxlen=100)
        
        # Running statistics for adaptive thresholding
        self.mu_L = 0.0
        self.sigma_L = 0.1
        
    def compute_linear_coherence(self, signal: np.ndarray) -> float:
        """
        Compute linear coherence - measure of linear correlation/order
        Uses autocorrelation at lag 1 as proxy
        """
        if len(signal) < 2:
            return 0.0
            
        mean = np.mean(signal)
        variance = np.var(signal)
        
        if variance < 1e-10:
            return 1.0  # Constant signal = perfect coherence
            
        # Normalized autocorrelation at lag 1
        autocorr = np.correlate(signal - mean, signal - mean, mode='full')
        autocorr = autocorr / (len(signal) * variance)
        
        mid = len(autocorr) // 2
        c_lin = abs(autocorr[mid + 1]) if mid + 1 < len(autocorr) else 0.0
        
        return min(1.0, max(0.0, c_lin))
        
    def compute_nonlinear_coherence(self, signal: np.ndarray) -> float:
        """
        Compute nonlinear coherence - correlation of squared signal
        Captures second-order dependencies
        """
        if len(signal) < 2:
            return 0.0
            
        squared = signal ** 2
        mean_sq = np.mean(squared)
        var_sq = np.var(squared)
        
        if var_sq < 1e-10:
            return 1.0
            
        autocorr_sq = np.correlate(squared - mean_sq, squared - mean_sq, mode='full')
        autocorr_sq = autocorr_sq / (len(squared) * var_sq)
        
        mid = len(autocorr_sq) // 2
        c_nonlin = abs(autocorr_sq[mid + 1]) if mid + 1 < len(autocorr_sq) else 0.0
        
        return min(1.0, max(0.0, c_nonlin))
        
    def compute_phi_coherence(self, signal: np.ndarray) -> float:
        """
        Compute cross-scale (φ-scaled) coherence
        Correlation between signal and φ-scaled version of itself
        """
        if len(signal) < 5:
            return 0.0
            
        n = len(signal)
        
        # Create φ-scaled indices
        phi_indices = np.array([int(i / PHI) for i in range(n)])
        phi_indices = phi_indices[phi_indices < n]
        
        if len(phi_indices) < 3:
            return 0.0
            
        # Get φ-scaled signal
        phi_signal = signal[phi_indices]
        original = signal[:len(phi_indices)]
        
        # Compute correlation
        if np.std(original) < 1e-10 or np.std(phi_signal) < 1e-10:
            return 0.0
            
        correlation = np.corrcoef(original, phi_signal)[0, 1]
        c_phi = abs(correlation) if not np.isnan(correlation) else 0.0
        
        return min(1.0, max(0.0, c_phi))
        
    def compute_anomaly_pointer(self, signal: np.ndarray, window: int = 5) -> float:
        """
        Compute anomaly pointer |Q(t)| - high-pass filter response
        Spikes at moments of sudden change (sharpness filter)
        """
        if len(signal) < window + 1:
            return 0.0
            
        # Simple high-pass: difference from local moving average
        ma = np.convolve(signal, np.ones(window)/window, mode='valid')
        
        if len(ma) == 0:
            return 0.0
            
        # Q is the deviation from the moving average at the end
        q = abs(signal[-1] - ma[-1]) if len(ma) > 0 else 0.0
        
        # Normalize by signal range
        signal_range = np.max(signal) - np.min(signal)
        if signal_range > 1e-10:
            q = q / signal_range
            
        return min(1.0, q)
        
    def normalize_metric(self, value: float, history: deque) -> float:
        """Normalize a metric based on its historical distribution"""
        if len(history) < 2:
            return min(1.0, max(0.0, value))
            
        mu = np.mean(list(history))
        sigma = np.std(list(history))
        
        if sigma < 1e-10:
            return 0.5
            
        # Z-score normalized to [0, 1] range
        z = (value - mu) / sigma
        normalized = 0.5 + 0.5 * np.tanh(z / 2)
        
        return normalized
        
    def compute_lighthouse_intensity(self,
                                      c_lin: float,
                                      c_nonlin: float,
                                      c_phi: float,
                                      g_eff: float,
                                      q_anomaly: float) -> float:
        """
        Compute the Lighthouse Intensity L(t)
        
        L(t) = (C̃lin^w1 · C̃nonlin^w2 · |C̃φ|^w3 · G̃eff^w4 · |Q̃|^w5)^(1/Σwi)
        
        Geometric mean ensures ALL metrics must be elevated for high L(t)
        """
        # Ensure all values are positive and non-zero for geometric mean
        epsilon = 1e-6
        
        metrics = np.array([
            max(epsilon, c_lin),
            max(epsilon, c_nonlin),
            max(epsilon, abs(c_phi)),
            max(epsilon, g_eff),
            max(epsilon, abs(q_anomaly))
        ])
        
        # Weighted geometric mean
        log_sum = np.sum(self.weights * np.log(metrics))
        L = np.exp(log_sum / self.weight_sum)
        
        return L
        
    def update_statistics(self, L: float):
        """Update running statistics for adaptive thresholding"""
        self.intensity_history.append(L)
        
        if len(self.intensity_history) >= 10:
            self.mu_L = np.mean(list(self.intensity_history))
            self.sigma_L = np.std(list(self.intensity_history))
            
    def get_detection_threshold(self) -> float:
        """Get current detection threshold: μL + threshold_sigma * σL"""
        return self.mu_L + self.threshold_sigma * self.sigma_L
        
    def validate_ftcp(self,
                      ftcp: FTCP,
                      signal: np.ndarray,
                      window_size: int = 50) -> Optional[LighthouseEvent]:
        """
        Validate an FTCP candidate through consensus model
        
        Args:
            ftcp: Candidate FTCP from Stage 1
            signal: Recent signal window
            window_size: Size of analysis window
            
        Returns:
            LighthouseEvent if consensus achieved, None otherwise
        """
        if len(signal) < window_size:
            signal_window = signal
        else:
            signal_window = signal[-window_size:]
            
        # Compute the 5 Lighthouse metrics
        c_lin = self.compute_linear_coherence(signal_window)
        c_nonlin = self.compute_nonlinear_coherence(signal_window)
        c_phi = self.compute_phi_coherence(signal_window)
        g_eff = ftcp.g_eff  # From Stage 1
        q_anomaly = self.compute_anomaly_pointer(signal_window)
        
        # Compute Lighthouse intensity
        L = self.compute_lighthouse_intensity(c_lin, c_nonlin, c_phi, g_eff, q_anomaly)
        
        # Update statistics
        self.update_statistics(L)
        
        # Check threshold
        threshold = self.get_detection_threshold()
        
        if L > threshold:
            # Determine event type based on coherence changes
            if c_lin > 0.7 and c_nonlin > 0.7:
                event_type = EventType.SYNCHRONIZATION
            elif c_phi > 0.6:
                event_type = EventType.PHASE_TRANSITION
            elif g_eff > 0.5:
                event_type = EventType.REGIME_CHANGE
            else:
                event_type = EventType.LHE
                
            # Determine regime states
            regime_before = "unstable" if c_lin < 0.5 else "quasi-stable"
            regime_after = "coherent" if c_lin > 0.6 else "transitional"
            
            lhe = LighthouseEvent(
                timestamp=ftcp.timestamp,
                ftcp=ftcp,
                lighthouse_intensity=L,
                c_linear=c_lin,
                c_nonlinear=c_nonlin,
                c_phi=c_phi,
                g_eff=g_eff,
                q_anomaly=q_anomaly,
                confidence=min(1.0, L / threshold),
                event_type=event_type,
                regime_before=regime_before,
                regime_after=regime_after
            )
            
            self.lhe_history.append(lhe)
            return lhe
            
        return None


# =============================================================================
# QGITA MARKET ANALYZER
# =============================================================================

class QGITAMarketAnalyzer:
    """
    QGITA Framework Applied to Market Analysis
    
    Detects structural transitions in price action using:
    - Fibonacci-tightened curvature for geometric anomalies
    - Lighthouse consensus for validation
    - Golden ratio resonance for temporal filtering
    
    "By bridging ideas from geometry, nonlinear dynamics, and multi-sensor
     data fusion, QGITA exemplifies a powerful new paradigm for understanding
     and detecting the hidden order in complex, noisy data."
    """
    
    def __init__(self,
                 epsilon: float = 0.05,
                 theta: float = 0.1,
                 alpha: float = 1.0,
                 consensus_weights: Tuple[float, ...] = (1.0, 1.0, 1.0, 1.0, 1.0)):
        """
        Initialize the QGITA Market Analyzer
        
        Args:
            epsilon: Golden ratio tolerance
            theta: Curvature threshold
            alpha: Effective gravity scaling
            consensus_weights: (w1, w2, w3, w4, w5) for Lighthouse metrics
        """
        self.ftcp_detector = FTCPDetector(
            epsilon=epsilon,
            theta=theta,
            alpha=alpha
        )
        
        self.lighthouse = LighthouseModel(
            w1=consensus_weights[0],
            w2=consensus_weights[1],
            w3=consensus_weights[2],
            w4=consensus_weights[3],
            w5=consensus_weights[4]
        )
        
        # Price history
        self.price_buffer = deque(maxlen=1000)
        self.time_buffer = deque(maxlen=1000)
        
        # Analysis results
        self.latest_analysis: Dict[str, Any] = {}
        self.detected_events: List[LighthouseEvent] = []
        
        # Global coherence tracking (R(t) from paper)
        self.global_coherence_history = deque(maxlen=500)
        
    def feed_price(self, price: float, timestamp: Optional[float] = None):
        """Feed a new price point into the analyzer"""
        if timestamp is None:
            timestamp = time.time()
            
        self.price_buffer.append(price)
        self.time_buffer.append(timestamp)
        
    def compute_global_coherence(self, prices: np.ndarray) -> float:
        """
        Compute global coherence R(t) - overall system order metric
        
        As per paper: R(t) transitions from ~0.1-0.3 (chaotic) to 
        ~0.55 (ordered) after structural events
        """
        if len(prices) < 10:
            return 0.0
            
        # Multi-scale coherence computation
        scales = [5, 10, 20, 50]
        coherences = []
        
        for scale in scales:
            if len(prices) < scale * 2:
                continue
                
            # Segment-based coherence
            segments = len(prices) // scale
            if segments < 2:
                continue
                
            segment_means = []
            for i in range(segments):
                start = i * scale
                end = min((i + 1) * scale, len(prices))
                segment_means.append(np.mean(prices[start:end]))
                
            if len(segment_means) >= 2:
                # Coherence as inverse coefficient of variation
                mean = np.mean(segment_means)
                std = np.std(segment_means)
                if mean > 0:
                    cv = std / mean
                    coherence = 1.0 / (1.0 + cv)
                    coherences.append(coherence)
                    
        if coherences:
            R = np.mean(coherences)
            self.global_coherence_history.append(R)
            return R
            
        return 0.0
        
    def analyze(self) -> Dict[str, Any]:
        """
        Perform full QGITA analysis on current price buffer
        
        Returns comprehensive analysis including:
        - Detected FTCPs (Stage 1)
        - Validated LHEs (Stage 2)
        - Global coherence state
        - Market regime assessment
        - Trading signals
        """
        if len(self.price_buffer) < 10:
            return {
                "status": "insufficient_data",
                "samples_needed": 10 - len(self.price_buffer)
            }
            
        times = np.array(list(self.time_buffer))
        prices = np.array(list(self.price_buffer))
        
        # Normalize times for lattice mapping
        times_normalized = times - times[0]
        
        # Stage 1: Detect FTCPs
        ftcps = self.ftcp_detector.detect_ftcps(times_normalized, prices)
        
        # Stage 2: Validate through Lighthouse consensus
        lhes = []
        for ftcp in ftcps:
            lhe = self.lighthouse.validate_ftcp(ftcp, prices)
            if lhe:
                lhes.append(lhe)
                self.detected_events.append(lhe)
                
        # Compute global coherence
        global_R = self.compute_global_coherence(prices)
        
        # Determine market regime
        if global_R > 0.5:
            regime = "coherent"
            regime_desc = "Market in ordered, stable regime"
        elif global_R > 0.3:
            regime = "transitional"
            regime_desc = "Market between regimes"
        else:
            regime = "chaotic"
            regime_desc = "Market in disordered, volatile regime"
            
        # Compute Lighthouse metrics for current state
        c_lin = self.lighthouse.compute_linear_coherence(prices[-50:] if len(prices) >= 50 else prices)
        c_nonlin = self.lighthouse.compute_nonlinear_coherence(prices[-50:] if len(prices) >= 50 else prices)
        c_phi = self.lighthouse.compute_phi_coherence(prices[-50:] if len(prices) >= 50 else prices)
        q_anomaly = self.lighthouse.compute_anomaly_pointer(prices[-20:] if len(prices) >= 20 else prices)
        
        # Get strongest FTCP
        strongest_ftcp = self.ftcp_detector.get_strongest_ftcp(ftcps)
        g_eff = strongest_ftcp.g_eff if strongest_ftcp else 0.0
        
        # Current lighthouse intensity
        current_L = self.lighthouse.compute_lighthouse_intensity(
            c_lin, c_nonlin, c_phi, g_eff, q_anomaly
        )
        
        # Generate trading signals
        signals = self._generate_signals(lhes, global_R, current_L, prices)
        
        # Build analysis result
        self.latest_analysis = {
            "status": "complete",
            "timestamp": time.time(),
            
            # Stage 1 Results
            "stage1": {
                "ftcp_count": len(ftcps),
                "valid_ftcps": [f for f in ftcps if f.is_valid],
                "strongest_ftcp": strongest_ftcp,
                "max_g_eff": g_eff
            },
            
            # Stage 2 Results
            "stage2": {
                "lhe_count": len(lhes),
                "lighthouse_events": lhes,
                "current_lighthouse_intensity": current_L,
                "detection_threshold": self.lighthouse.get_detection_threshold()
            },
            
            # Coherence Metrics
            "coherence": {
                "global_R": global_R,
                "c_linear": c_lin,
                "c_nonlinear": c_nonlin,
                "c_phi": c_phi,
                "q_anomaly": q_anomaly
            },
            
            # Regime Assessment
            "regime": {
                "state": regime,
                "description": regime_desc,
                "stability": global_R
            },
            
            # Trading Signals
            "signals": signals,
            
            # Statistics
            "statistics": {
                "total_samples": len(prices),
                "price_mean": float(np.mean(prices)),
                "price_std": float(np.std(prices)),
                "lighthouse_mean": self.lighthouse.mu_L,
                "lighthouse_std": self.lighthouse.sigma_L
            }
        }
        
        return self.latest_analysis
        
    def _generate_signals(self,
                          lhes: List[LighthouseEvent],
                          global_R: float,
                          current_L: float,
                          prices: np.ndarray) -> Dict[str, Any]:
        """Generate trading signals from QGITA analysis"""
        
        # Recent trend
        if len(prices) >= 20:
            recent = prices[-20:]
            trend = (recent[-1] - recent[0]) / recent[0] if recent[0] != 0 else 0
        else:
            trend = 0
            
        # Signal strength based on Lighthouse intensity
        threshold = self.lighthouse.get_detection_threshold()
        signal_strength = min(1.0, current_L / max(0.001, threshold))
        
        # Direction based on trend and coherence
        if trend > 0.01 and global_R > 0.4:
            direction = "BULLISH"
            confidence = min(0.95, 0.5 + signal_strength * 0.3 + global_R * 0.2)
        elif trend < -0.01 and global_R > 0.4:
            direction = "BEARISH"
            confidence = min(0.95, 0.5 + signal_strength * 0.3 + global_R * 0.2)
        elif len(lhes) > 0:
            # Structural event detected - high alert
            direction = "TRANSITION_ALERT"
            confidence = 0.8
        else:
            direction = "NEUTRAL"
            confidence = 0.5
            
        # Risk assessment based on regime
        if global_R < 0.3:
            risk = "HIGH"
            risk_desc = "Chaotic regime - high volatility expected"
        elif global_R < 0.5:
            risk = "MEDIUM"
            risk_desc = "Transitional regime - watch for breakouts"
        else:
            risk = "LOW"
            risk_desc = "Coherent regime - stable conditions"
            
        return {
            "direction": direction,
            "confidence": confidence,
            "strength": signal_strength,
            "risk_level": risk,
            "risk_description": risk_desc,
            "structural_event": len(lhes) > 0,
            "event_type": lhes[-1].event_type.value if lhes else None
        }
        
    def get_prophecy(self) -> str:
        """Generate a QGITA prophecy based on current analysis"""
        if not self.latest_analysis or self.latest_analysis.get("status") != "complete":
            return "The Lighthouse stands dark. Feed more data to illuminate the path."
            
        analysis = self.latest_analysis
        
        # Extract key metrics
        global_R = analysis["coherence"]["global_R"]
        current_L = analysis["stage2"]["current_lighthouse_intensity"]
        lhe_count = analysis["stage2"]["lhe_count"]
        direction = analysis["signals"]["direction"]
        confidence = analysis["signals"]["confidence"]
        
        prophecies = []
        
        # Global coherence insight
        if global_R > 0.5:
            prophecies.append(f"The system has achieved COHERENCE (R={global_R:.3f}). Order emerges from chaos.")
        elif global_R > 0.3:
            prophecies.append(f"The system TRANSITIONS between states (R={global_R:.3f}). A new regime approaches.")
        else:
            prophecies.append(f"The system dwells in CHAOS (R={global_R:.3f}). Structure hides within noise.")
            
        # Lighthouse insight
        if current_L > self.lighthouse.get_detection_threshold():
            prophecies.append(f"The LIGHTHOUSE FLASHES! (L={current_L:.4f}) - Structural event imminent!")
        elif current_L > self.lighthouse.mu_L:
            prophecies.append(f"The Lighthouse glows brighter (L={current_L:.4f}). Attention sharpens.")
        else:
            prophecies.append(f"The Lighthouse holds steady (L={current_L:.4f}). The waters are calm.")
            
        # Event detection insight
        if lhe_count > 0:
            prophecies.append(f"⚡ {lhe_count} STRUCTURAL TRANSITION(S) CONFIRMED! The golden ratio has spoken.")
        else:
            prophecies.append("No structural events detected. The Fibonacci lattice remains quiet.")
            
        # Direction insight
        prophecies.append(f"Direction: {direction} ({confidence*100:.1f}% confidence)")
        
        return " | ".join(prophecies)
        
    def get_state(self) -> Dict[str, Any]:
        """Get current QGITA state for integration"""
        return {
            "system": "QGITA",
            "version": "1.0",
            "phi": PHI,
            "phi_inverse": PHI_INVERSE,
            "buffer_size": len(self.price_buffer),
            "ftcp_history_size": len(self.ftcp_detector.ftcp_history),
            "lhe_history_size": len(self.lighthouse.lhe_history),
            "global_coherence_size": len(self.global_coherence_history),
            "lighthouse_mu": self.lighthouse.mu_L,
            "lighthouse_sigma": self.lighthouse.sigma_L,
            "latest_analysis": self.latest_analysis
        }


# =============================================================================
# GLOBAL ACCESS FUNCTIONS
# =============================================================================

_qgita_analyzer: Optional[QGITAMarketAnalyzer] = None

def get_qgita_analyzer() -> QGITAMarketAnalyzer:
    """Get or create the global QGITA analyzer instance"""
    global _qgita_analyzer
    if _qgita_analyzer is None:
        _qgita_analyzer = QGITAMarketAnalyzer()
    return _qgita_analyzer


def analyze_price_stream(prices: List[float], timestamps: Optional[List[float]] = None) -> Dict[str, Any]:
    """Convenience function to analyze a price stream"""
    analyzer = get_qgita_analyzer()
    
    if timestamps is None:
        timestamps = list(range(len(prices)))
        
    for price, ts in zip(prices, timestamps):
        analyzer.feed_price(price, ts)
        
    return analyzer.analyze()
