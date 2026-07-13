#!/usr/bin/env python3
"""
👑 QUEEN SERO's COHERENCE MANDALA 👑
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A Dynamic Systems Model of Coherence
Based on: "A Dynamic Systems Model of Coherence Grounded in Astronomical Phenomena"
          Gary Leckey, R&A Consulting, October 2025

The Queen perceives the market as the cosmos perceives light.
The tree of light: Ψ∞ → ℵ → Φ → F → L → Ω → ρ → C → Ψ'∞

Governing Equation:
    Ψt+1 = (1 - α)Ψt + α R(Ct; Ψt)

Where R = ρ ∘ Ω ∘ L(·; κt) ∘ F(·; Ψt) ∘ Φ ∘ ℵ

Key Indices:
    rt  = Resonance (market harmony)
    λt  = Constraint (volatility tension)
    Pt  = Purity = rt / λt
    κt  = Structuring Index (market regime)

Three Behaviors:
    1. Self-organization → Coherence (κ ≈ 1)
    2. Oscillation → Over-structured (κ > 1)
    3. Dissolution → Under-resonant (κ < 1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import numpy as np
import time
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
import os

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OPERATOR DEFINITIONS
# The perceptual cycle: ℵ → Φ → F → L → Ω → ρ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Aleph:
    """
    ℵ (Aleph) - Saliency/Filtering Operator
    
    Extracts what matters from the noise.
    In markets: Filters signal from noise in price/volume data.
    
    ℵ(Ct) = W ⊙ Ct  (element-wise weighting)
    """
    def __init__(self, weights: np.ndarray = None):
        # Default weights: [Ambient, Point, Transient] 
        # For markets: [Trend, Momentum, Volatility]
        self.W = weights if weights is not None else np.array([0.3, 0.5, 0.2])
    
    def __call__(self, C: np.ndarray) -> np.ndarray:
        """Apply saliency filter"""
        return self.W * C


class Phi:
    """
    Φ (Phi) - Pattern Recognition Operator
    
    Structural analysis of filtered signals.
    In markets: Identifies patterns in price action.
    
    Φ(x) = tanh(M @ x)  (linear transform + saturation)
    """
    def __init__(self, dim: int = 3):
        # Initialize pattern recognition matrix
        np.random.seed(42)  # Reproducibility
        self.M = np.eye(dim) + 0.1 * np.random.randn(dim, dim)
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Apply pattern recognition"""
        return np.tanh(self.M @ x)


class Framing:
    """
    F (Framing) - Memory Integration Operator
    
    Contextualizes new patterns with prior state.
    In markets: Compares current signals to remembered context.
    
    F(φ, Ψt) = β·φ + (1-β)·Ψt
    """
    def __init__(self, beta: float = 0.6):
        self.beta = beta
    
    def __call__(self, phi: np.ndarray, psi: np.ndarray) -> np.ndarray:
        """Frame new pattern against prior state"""
        return self.beta * phi + (1 - self.beta) * psi


class LivingNode:
    """
    L (The Stag) - Living Node / Physiological Modulation
    
    Non-linear modulation controlled by structuring index κ.
    In markets: The Queen's intuition responding to market regime.
    
    L(f; κ) = g(κ) · f, where g(κ) = clip(1/κ, gmin, gmax)
    
    κ > 1: Over-structured (rigid, sympathetic) → reduces gain
    κ < 1: Under-resonant (flexible, parasympathetic) → increases gain  
    κ ≈ 1: Balanced/coherent → unity gain
    """
    def __init__(self, g_min: float = 0.3, g_max: float = 2.0):
        self.g_min = g_min
        self.g_max = g_max
    
    def __call__(self, f: np.ndarray, kappa: float) -> np.ndarray:
        """Apply living modulation based on structuring index"""
        gain = np.clip(1.0 / (kappa + 1e-6), self.g_min, self.g_max)
        return gain * f


class Omega:
    """
    Ω (Omega) - Synthesis / Convergence Operator
    
    Converges into a coherent gestalt.
    In markets: Creates unified market view from components.
    
    Ω(x) = x / (||x|| + ε)  (normalize to unit sphere)
    """
    def __init__(self, epsilon: float = 1e-8):
        self.epsilon = epsilon
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Synthesize into coherent gestalt"""
        norm = np.linalg.norm(x) + self.epsilon
        return x / norm


class Rho:
    """
    ρ (Rho) - Reflection / Memory Encoding Operator
    
    Prepares output for next-state integration.
    In markets: Encodes lessons for future decisions.
    
    ρ(x) = x (identity with optional smoothing)
    """
    def __init__(self, smooth: float = 0.0):
        self.smooth = smooth
        self.prev = None
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Reflect and prepare for memory"""
        if self.smooth > 0 and self.prev is not None:
            result = (1 - self.smooth) * x + self.smooth * self.prev
        else:
            result = x.copy()
        self.prev = result.copy()
        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPOSITE OPERATOR R
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CompositeOperatorR:
    """
    R = ρ ∘ Ω ∘ L(·; κt) ∘ F(·; Ψt) ∘ Φ ∘ ℵ
    
    The complete perceptual transformation pipeline.
    """
    def __init__(self, dim: int = 3):
        self.aleph = Aleph()
        self.phi = Phi(dim)
        self.framing = Framing()
        self.living = LivingNode()
        self.omega = Omega()
        self.rho = Rho()
    
    def __call__(self, C: np.ndarray, psi: np.ndarray, kappa: float) -> np.ndarray:
        """
        Apply the complete transformation chain.
        
        C: Input signal [Ambient, Point, Transient]
        psi: Prior state Ψt
        kappa: Structuring index κt
        """
        # ℵ: Saliency filter
        a = self.aleph(C)
        
        # Φ: Pattern recognition
        p = self.phi(a)
        
        # F: Frame against prior state
        f = self.framing(p, psi)
        
        # L: Living node modulation
        l = self.living(f, kappa)
        
        # Ω: Synthesis
        o = self.omega(l)
        
        # ρ: Reflection
        r = self.rho(o)
        
        return r


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COHERENCE INDICES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CoherenceMetrics:
    """
    Computes the key coherence indices:
    
    rt  = Resonance (environmental harmony)
    λt  = Constraint (physiological tension)
    Pt  = Purity = rt / λt
    κt  = Structuring Index
    """
    
    def __init__(self):
        # Historical bounds for normalization
        self.r_min = 0.0
        self.r_max = 1.0
        self.lambda_min = 0.1
        self.lambda_max = 5.0
    
    def compute_resonance(self, signal_power: float) -> float:
        """
        Compute resonance rt from signal power.
        
        In astronomy: Schumann Resonance power
        In markets: Market harmony / trend strength
        """
        rt = np.clip((signal_power - self.r_min) / (self.r_max - self.r_min + 1e-6), 0, 1)
        return rt
    
    def compute_constraint(self, variability: float, ref: float = 50.0) -> float:
        """
        Compute constraint λt from variability measure.
        
        In physiology: Inverse of HRV SDNN
        In markets: Inverse of price stability
        """
        norm = variability / (ref + 1e-6)
        lambda_t = np.clip(1.0 / (norm + 1e-6), self.lambda_min, self.lambda_max)
        return lambda_t
    
    def compute_purity(self, r: float, lam: float) -> float:
        """
        Compute purity Pt = rt / λt
        
        High purity: Strong resonance with low constraint
        """
        return r / (lam + 1e-6)
    
    def compute_structuring(self, low_freq: float, high_freq: float) -> float:
        """
        Compute structuring index κt = LF/HF ratio.
        
        In physiology: Sympathetic/parasympathetic balance
        In markets: Trend strength / noise ratio
        
        κ > 1: Over-structured (trend-dominant)
        κ < 1: Under-resonant (noise-dominant)
        κ ≈ 1: Balanced (coherent)
        """
        kappa = low_freq / (high_freq + 1e-6)
        return np.clip(kappa, 0.2, 5.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COHERENCE SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class QueenCoherenceSystem:
    """
    👑 The Queen's Coherence System
    
    Implements the full dynamic systems model:
    
    Ψt+1 = (1 - α)Ψt + α R(Ct; Ψt)
    
    Three behaviors emerge:
    1. Self-organization toward coherence (κ ≈ 1)
    2. Oscillation under over-structuring (κ > 1)
    3. Dissolution under under-resonance (κ < 1)
    """
    
    def __init__(self, dim: int = 3, alpha: float = 0.25):
        """
        Initialize the coherence system.
        
        dim: State vector dimension
        alpha: Learning rate (0 < α < 1)
        """
        self.dim = dim
        self.alpha = alpha
        
        # State vector
        self.psi = np.ones(dim) / np.sqrt(dim)  # Start normalized
        
        # Operators
        self.R = CompositeOperatorR(dim)
        
        # Metrics
        self.metrics = CoherenceMetrics()
        
        # History
        self.history = {
            'psi': [],
            'C': [],
            'r': [],
            'lambda': [],
            'P': [],
            'kappa': [],
            'time': []
        }
        
        # Current indices
        self.r = 0.5
        self.lam = 1.0
        self.P = 0.5
        self.kappa = 1.0
    
    def update(self, C: np.ndarray, signal_power: float, variability: float, 
               low_freq: float, high_freq: float) -> np.ndarray:
        """
        Perform one step of the coherence update.
        
        C: Input vector [Ambient, Point, Transient]
        signal_power: For resonance calculation
        variability: For constraint calculation
        low_freq, high_freq: For structuring index
        
        Returns: Updated state vector Ψt+1
        """
        # Compute indices
        self.r = self.metrics.compute_resonance(signal_power)
        self.lam = self.metrics.compute_constraint(variability)
        self.P = self.metrics.compute_purity(self.r, self.lam)
        self.kappa = self.metrics.compute_structuring(low_freq, high_freq)
        
        # Apply composite operator
        R_output = self.R(C, self.psi, self.kappa)
        
        # State update: Ψt+1 = (1-α)Ψt + αR(Ct; Ψt)
        self.psi = (1 - self.alpha) * self.psi + self.alpha * R_output
        
        # Normalize to prevent drift
        self.psi = self.psi / (np.linalg.norm(self.psi) + 1e-8)
        
        # Record history
        self.history['psi'].append(self.psi.copy())
        self.history['C'].append(C.copy())
        self.history['r'].append(self.r)
        self.history['lambda'].append(self.lam)
        self.history['P'].append(self.P)
        self.history['kappa'].append(self.kappa)
        self.history['time'].append(datetime.now().isoformat())
        
        return self.psi
    
    def get_state(self) -> Dict:
        """Get current system state"""
        return {
            'psi': self.psi.tolist(),
            'resonance': self.r,
            'constraint': self.lam,
            'purity': self.P,
            'kappa': self.kappa,
            'behavior': self.classify_behavior()
        }
    
    def classify_behavior(self) -> str:
        """
        Classify current system behavior.
        
        Returns: 'coherent', 'oscillating', or 'dissolving'
        """
        if 0.7 < self.kappa < 1.4:
            return 'coherent'  # ✨ Self-organization
        elif self.kappa >= 1.4:
            return 'oscillating'  # 🔄 Over-structured
        else:
            return 'dissolving'  # 💨 Under-resonant


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MANDALA VISUALIZATION (ASCII)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MandalaRenderer:
    """
    ASCII Mandala visualization of coherence state.
    
    Mapping:
    - Brightness ∝ |Pt| (purity)
    - Pattern reflects κt (structuring)
    - Color coding via symbols
    """
    
    SYMBOLS = {
        'coherent': ['✨', '💎', '🌟', '⭐', '✦', '◆', '●', '○'],
        'oscillating': ['🔄', '⚡', '💫', '🌀', '◐', '◑', '◒', '◓'],
        'dissolving': ['💨', '🌫️', '○', '◌', '·', '.', ' ', ' ']
    }
    
    COLORS = {
        'coherent': '\033[92m',      # Green
        'oscillating': '\033[93m',    # Yellow
        'dissolving': '\033[90m',     # Gray
        'reset': '\033[0m'
    }
    
    def __init__(self, size: int = 15):
        self.size = size
    
    def render(self, system: QueenCoherenceSystem) -> str:
        """Render the mandala as ASCII art"""
        behavior = system.classify_behavior()
        P = system.P
        kappa = system.kappa
        psi = system.psi
        
        symbols = self.SYMBOLS[behavior]
        color = self.COLORS[behavior]
        reset = self.COLORS['reset']
        
        # Build mandala
        lines = []
        center = self.size // 2
        
        for y in range(self.size):
            row = []
            for x in range(self.size):
                # Distance from center
                dx = x - center
                dy = y - center
                dist = math.sqrt(dx*dx + dy*dy)
                
                # Angle for rotation effect
                angle = math.atan2(dy, dx)
                
                # Choose symbol based on distance and state
                if dist < 2:
                    # Center: purity indicator
                    idx = int(P * (len(symbols) - 1))
                    sym = symbols[min(idx, len(symbols)-1)]
                elif dist < center * 0.5:
                    # Inner ring: psi[0]
                    phase = (angle + psi[0] * 10) % (2 * math.pi)
                    idx = int((phase / (2 * math.pi)) * len(symbols))
                    sym = symbols[idx % len(symbols)]
                elif dist < center * 0.8:
                    # Middle ring: psi[1]
                    phase = (angle + psi[1] * 10) % (2 * math.pi)
                    idx = int((phase / (2 * math.pi)) * len(symbols))
                    sym = symbols[idx % len(symbols)]
                elif dist < center:
                    # Outer ring: psi[2]
                    phase = (angle + psi[2] * 10) % (2 * math.pi)
                    idx = int((phase / (2 * math.pi)) * len(symbols))
                    sym = symbols[idx % len(symbols)]
                else:
                    sym = ' '
                
                row.append(sym)
            
            lines.append(' '.join(row))
        
        # Header
        header = f"""
{color}{'━' * 50}
👑 QUEEN SERO's COHERENCE MANDALA 👑
{'━' * 50}{reset}

   Resonance (r):    {system.r:.4f}
   Constraint (λ):   {system.lam:.4f}
   Purity (P):       {system.P:.4f}
   Structuring (κ):  {system.kappa:.4f}
   
   Behavior: {color}{behavior.upper()}{reset}
   Ψ = [{', '.join(f'{v:.3f}' for v in system.psi)}]

{color}{'─' * 50}{reset}
"""
        
        mandala = '\n'.join(lines)
        
        footer = f"""
{color}{'─' * 50}
   κ < 0.7  → Dissolving (under-resonant)
   κ ≈ 1.0  → Coherent (self-organizing)
   κ > 1.4  → Oscillating (over-structured)
{'━' * 50}{reset}
"""
        
        return header + mandala + footer


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MARKET INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MarketCoherenceAdapter:
    """
    Adapts market data to coherence model inputs.
    
    Maps:
    - Price trend → Ambient (A)
    - Momentum → Point (P)  
    - Volatility → Transient (T)
    - Volume → Signal power
    - ATR → Variability
    - Trend/Noise ratio → LF/HF
    """
    
    def __init__(self):
        self.price_history = []
        self.volume_history = []
    
    def process(self, price: float, volume: float, volatility: float) -> Dict:
        """
        Convert market data to coherence inputs.
        """
        self.price_history.append(price)
        self.volume_history.append(volume)
        
        # Keep last 100 samples
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
            self.volume_history = self.volume_history[-100:]
        
        # Calculate inputs
        if len(self.price_history) >= 3:
            # Ambient: Normalized price trend
            prices = np.array(self.price_history)
            trend = (prices[-1] - prices[0]) / (prices[0] + 1e-6)
            ambient = np.clip((trend + 0.1) / 0.2, 0, 1)
            
            # Point: Momentum (recent vs average)
            if len(prices) >= 10:
                recent = np.mean(prices[-3:])
                older = np.mean(prices[-10:-3])
                momentum = (recent - older) / (older + 1e-6)
                point = np.clip((momentum + 0.05) / 0.1, 0, 1)
            else:
                point = 0.5
            
            # Transient: Volatility spike
            transient = np.clip(volatility / 0.05, 0, 1)
            
            # Signal power: Volume strength
            if len(self.volume_history) >= 10:
                avg_vol = np.mean(self.volume_history[-10:])
                signal_power = np.clip(volume / (avg_vol + 1e-6), 0, 2) / 2
            else:
                signal_power = 0.5
            
            # Variability: Price variance
            variability = np.std(prices[-20:]) if len(prices) >= 20 else 0.01
            
            # LF/HF: Trend strength vs noise
            if len(prices) >= 20:
                # Simple trend detection
                x = np.arange(len(prices[-20:]))
                y = prices[-20:]
                slope = np.polyfit(x, y, 1)[0]
                noise = np.std(y - np.polyval(np.polyfit(x, y, 1), x))
                low_freq = abs(slope) * 100
                high_freq = noise + 1e-6
            else:
                low_freq = 1.0
                high_freq = 1.0
        else:
            ambient = 0.5
            point = 0.5
            transient = 0.3
            signal_power = 0.5
            variability = 0.01
            low_freq = 1.0
            high_freq = 1.0
        
        return {
            'C': np.array([ambient, point, transient]),
            'signal_power': signal_power,
            'variability': variability * 100,  # Scale to match HRV range
            'low_freq': low_freq,
            'high_freq': high_freq
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO SIMULATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_demo():
    """
    Run a demonstration of the Queen's Coherence System.
    
    Simulates the three phases:
    1. Self-organization (κ ≈ 1)
    2. Perturbation/Oscillation (κ > 1)
    3. Dissolution (κ < 1)
    """
    print("\n" + "👑" * 25)
    print("   QUEEN SERO's COHERENCE MANDALA")
    print("   Dynamic Systems Model of Perception")
    print("👑" * 25 + "\n")
    
    # Initialize system
    system = QueenCoherenceSystem(dim=3, alpha=0.25)
    renderer = MandalaRenderer(size=11)
    
    # Simulation phases
    phases = [
        {
            'name': 'PHASE 1: Self-Organization',
            'steps': 20,
            'kappa_range': (0.8, 1.2),
            'C_base': np.array([0.3, 0.6, 0.1])
        },
        {
            'name': 'PHASE 2: Perturbation (Oscillation)',
            'steps': 15,
            'kappa_range': (1.5, 2.5),
            'C_base': np.array([0.2, 0.4, 0.6])
        },
        {
            'name': 'PHASE 3: Dissolution',
            'steps': 15,
            'kappa_range': (0.3, 0.6),
            'C_base': np.array([0.1, 0.1, 0.05])
        }
    ]
    
    for phase in phases:
        print(f"\n{'=' * 50}")
        print(f"   {phase['name']}")
        print(f"{'=' * 50}")
        
        for step in range(phase['steps']):
            # Generate inputs
            t = step / phase['steps']
            kappa_low, kappa_high = phase['kappa_range']
            
            # Add some variation
            noise = np.random.randn(3) * 0.1
            C = np.clip(phase['C_base'] + noise, 0, 1)
            
            # Synthetic physiological signals
            signal_power = 0.5 + 0.3 * np.sin(t * np.pi)
            variability = 30 + 20 * np.cos(t * np.pi)
            kappa = kappa_low + (kappa_high - kappa_low) * (0.5 + 0.5 * np.sin(t * 2 * np.pi))
            low_freq = kappa
            high_freq = 1.0
            
            # Update system
            system.update(C, signal_power, variability, low_freq, high_freq)
            
            # Show mandala every 5 steps
            if step % 5 == 0:
                print(renderer.render(system))
                time.sleep(0.5)
    
    # Final summary
    print("\n" + "=" * 50)
    print("   SIMULATION COMPLETE")
    print("=" * 50)
    
    print(f"""
   The Queen observed three behaviors:
   
   1. ✨ COHERENT (κ ≈ 1)
      Self-organization toward stable perception
      
   2. 🔄 OSCILLATING (κ > 1)
      Over-structured, rigid response to perturbation
      
   3. 💨 DISSOLVING (κ < 1)
      Under-resonant, perception fades
      
   👑 Queen's Wisdom:
   "Balance is the key. Not too rigid, not too loose.
    The cosmos speaks to those who listen in harmony."
""")
    
    # Save history
    history_file = 'coherence_history.json'
    with open(history_file, 'w') as f:
        # Convert numpy arrays to lists for JSON
        saveable = {
            'psi': [p.tolist() for p in system.history['psi']],
            'C': [c.tolist() for c in system.history['C']],
            'r': system.history['r'],
            'lambda': system.history['lambda'],
            'P': system.history['P'],
            'kappa': system.history['kappa'],
            'time': system.history['time']
        }
        json.dump(saveable, f, indent=2)
    
    print(f"\n   History saved to: {history_file}")
    print("\n" + "👑" * 25)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LIVE MARKET COHERENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_live_coherence():
    """
    Run coherence analysis on live market data.
    """
    try:
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        from aureon.exchanges.kraken_client import KrakenClient
    except ImportError:
        print("Market clients not available. Running demo instead.")
        run_demo()
        return
    
    print("\n" + "👑" * 25)
    print("   LIVE MARKET COHERENCE")
    print("👑" * 25 + "\n")
    
    binance = get_binance_client()
    system = QueenCoherenceSystem(dim=3, alpha=0.15)
    adapter = MarketCoherenceAdapter()
    renderer = MandalaRenderer(size=11)
    
    # Track multiple assets
    symbols = ['BTCUSDC', 'ETHUSDC', 'SOLUSDC']
    
    for i in range(30):
        print(f"\n{'─' * 50}")
        print(f"   Update {i+1}/30")
        print(f"{'─' * 50}")
        
        # Get market data
        coherence_sum = 0
        for symbol in symbols:
            try:
                ticker = binance.get_24h_ticker(symbol)
                price = float(ticker.get('lastPrice', 0))
                volume = float(ticker.get('volume', 0))
                change = float(ticker.get('priceChangePercent', 0))
                volatility = abs(change) / 100
                
                # Process through adapter
                inputs = adapter.process(price, volume, volatility)
                
                # Update coherence system
                system.update(
                    inputs['C'],
                    inputs['signal_power'],
                    inputs['variability'],
                    inputs['low_freq'],
                    inputs['high_freq']
                )
                
                coherence_sum += system.P
                
            except Exception as e:
                print(f"   Error with {symbol}: {e}")
        
        # Display mandala
        print(renderer.render(system))
        
        # Trading signal based on coherence
        behavior = system.classify_behavior()
        if behavior == 'coherent':
            print("   🟢 SIGNAL: Market coherent - TRADE OK")
        elif behavior == 'oscillating':
            print("   🟡 SIGNAL: Market oscillating - CAUTION")
        else:
            print("   🔴 SIGNAL: Market dissolving - AVOID")
        
        time.sleep(2)
    
    print("\n👑 Queen: 'The market has spoken. Listen well.'")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'live':
        import asyncio
        asyncio.run(run_live_coherence())
    else:
        run_demo()
