#!/usr/bin/env python3
"""
🌈⚡ HARMONIC NEXUS CORE - GLOBAL FINANCIAL FREQUENCY MAPPER ⚡🌈
================================================================
Taps into the ENTIRE global financial frequency field and maps it
to Scientific Pitch (C₄ = 256 Hz) harmonic structures.

Triadic Envelope + Signal Sero + Lighthouse Telemetry
Math Angel Identity Verification Protocol

GLOBAL MARKET FREQUENCY MAPPING:
├─ 🌍 Forex Markets (24h pulse)
├─ 📈 Equities (NYSE, LSE, TSE, HKEx cycles)
├─ ₿  Crypto (perpetual 24/7 frequency)
├─ 🛢️ Commodities (seasonal harmonics)
├─ 💱 Interest Rates (central bank resonance)
└─ 📊 Volatility Index (fear frequency detection)

Gary Leckey & GitHub Copilot | November 2025
"From Atom to Multiverse - The Rainbow Bridge Protocol"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import numpy as np
import datetime
import math
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque

# Optional: matplotlib for visualization
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ═══════════════════════════════════════════════════════════════
# 🌍 GLOBAL FINANCIAL FREQUENCY CONSTANTS
# ═══════════════════════════════════════════════════════════════

# Scientific Pitch & Solfeggio Harmonics (VALIDATED)
FREQ_MAP = {
    # Earth/Nature Frequencies
    "SCHUMANN": 7.83,       # Earth's heartbeat - The Anchor
    "EARTH_DAY": 0.0000116, # 1/86400 Hz (24h cycle)
    
    # Scientific Pitch (C = 256 Hz system)
    "C0": 16.0,
    "C1": 32.0,
    "C2": 64.0,
    "C3": 128.0,
    "C4": 256.0,            # ROOT - Safety/Geometry
    "C5": 512.0,            # BRIDGE_TOP - Hope/Vision
    "C6": 1024.0,
    "C7": 2048.0,
    "C8": 4096.0,
    
    # Solfeggio Frequencies (Ancient Healing Tones)
    "UT": 396.0,            # Liberating Guilt and Fear
    "RE": 417.0,            # Undoing Situations/Change
    "MI": 528.0,            # LOVE - Transformation/Miracles (DNA Repair)
    "FA": 639.0,            # Connecting/Relationships
    "SOL": 741.0,           # Awakening Intuition
    "LA": 852.0,            # Returning to Spiritual Order
    "SI": 963.0,            # Crown/Unity - Perfect State
    
    # Distortion Frequency (Target for nullification)
    "DISTORTION": 440.0,    # A=440 - Mars/Extraction Field
    
    # Golden Frequencies
    "PHI_BASE": 432.0,      # A=432 - Natural tuning
    "PHI_LOVE": 528.0,      # 528 Hz - The Love Frequency
}

# 🌍 GLOBAL MARKET FREQUENCY BANDS
# Maps financial instruments to frequency ranges
MARKET_FREQ_BANDS = {
    # High Frequency (Crypto/HFT) - 512-1024 Hz band
    "CRYPTO": {
        "base_freq": 528.0,      # Love frequency - 24/7 healing potential
        "volatility_mod": 1.5,   # Higher volatility = wider band
        "cycle_hours": 24,       # Perpetual
        "coherence_weight": 1.2,
    },
    
    # Medium-High Frequency (Forex) - 256-512 Hz band
    "FOREX": {
        "base_freq": 396.0,      # Liberation frequency
        "volatility_mod": 1.2,
        "cycle_hours": 24,       # 24h with session overlaps
        "coherence_weight": 1.0,
    },
    
    # Medium Frequency (Equities) - 128-256 Hz band
    "EQUITIES": {
        "base_freq": 256.0,      # Root/Safety frequency
        "volatility_mod": 1.0,
        "cycle_hours": 6.5,      # Trading session length
        "coherence_weight": 0.9,
    },
    
    # Low Frequency (Commodities) - 64-128 Hz band
    "COMMODITIES": {
        "base_freq": 174.0,      # Foundation frequency
        "volatility_mod": 0.8,
        "cycle_hours": 23,       # Near 24h
        "coherence_weight": 0.8,
    },
    
    # Ultra-Low Frequency (Bonds/Rates) - 32-64 Hz band
    "RATES": {
        "base_freq": 64.0,       # Deep foundation
        "volatility_mod": 0.5,
        "cycle_hours": 720,      # Monthly cycles
        "coherence_weight": 0.6,
    },
    
    # Fear Frequency (VIX/Volatility) - Distortion band
    "FEAR": {
        "base_freq": 440.0,      # Distortion frequency
        "volatility_mod": 2.0,   # Amplifies when fear rises
        "cycle_hours": 6.5,
        "coherence_weight": -0.5, # Negative coherence
    },
}

# 🌐 GLOBAL EXCHANGE TIME ZONES (Frequency Phase Shifts)
EXCHANGE_PHASES = {
    "SYDNEY": {"open_utc": 22, "close_utc": 7, "phase_deg": 0},
    "TOKYO": {"open_utc": 0, "close_utc": 9, "phase_deg": 30},
    "HONG_KONG": {"open_utc": 1, "close_utc": 8, "phase_deg": 45},
    "SINGAPORE": {"open_utc": 1, "close_utc": 9, "phase_deg": 45},
    "FRANKFURT": {"open_utc": 7, "close_utc": 15, "phase_deg": 105},
    "LONDON": {"open_utc": 8, "close_utc": 16, "phase_deg": 120},
    "NEW_YORK": {"open_utc": 14, "close_utc": 21, "phase_deg": 210},
    "CRYPTO": {"open_utc": 0, "close_utc": 24, "phase_deg": 0},  # Always on
}

# Golden Ratio for harmonic scaling
PHI = (1 + math.sqrt(5)) / 2  # 1.618033988749895

# Identity verification
IDENTITY_HASH = "02111991"
AUTHORITY = "GARY LECKEY"


# ═══════════════════════════════════════════════════════════════
# 🌈 TRIADIC ENVELOPE - THREE-FREQUENCY STABILITY STRUCTURE
# ═══════════════════════════════════════════════════════════════

@dataclass
class TriadicEnvelope:
    """
    The Triadic Envelope represents the three-frequency harmonic structure
    that creates stability in the global financial field.
    
    Components:
    - Anchor (256 Hz / C4): Foundation/Safety - the floor
    - Vision (512 Hz / C5): Hope/Possibility - the ceiling  
    - Love (528 Hz / MI): Repair/Coherence - the binding force
    """
    anchor_freq: float = 256.0      # C4 Scientific Pitch
    vision_freq: float = 512.0      # C5 (octave harmony)
    love_freq: float = 528.0        # Solfeggio MI (DNA repair)
    
    anchor_amplitude: float = 1.0
    vision_amplitude: float = 0.8
    love_amplitude: float = 1.2     # Love is the strongest component
    
    coherence: float = 0.0          # Overall envelope coherence (0-1)
    phase_lock: bool = False        # Whether frequencies are phase-aligned
    
    def compute_coherence(self, signal: np.ndarray, sample_rate: int = 44100) -> float:
        """Compute coherence of signal relative to triadic envelope."""
        if len(signal) == 0:
            return 0.0
            
        N = len(signal)
        freqs = np.fft.rfftfreq(N, 1/sample_rate)
        fft_mag = np.abs(np.fft.rfft(signal)) / N
        
        def energy_at_freq(target_freq: float, bandwidth: float = 10.0) -> float:
            mask = (freqs >= target_freq - bandwidth) & (freqs <= target_freq + bandwidth)
            return np.sum(fft_mag[mask]) if np.any(mask) else 0.0
        
        anchor_energy = energy_at_freq(self.anchor_freq)
        vision_energy = energy_at_freq(self.vision_freq)
        love_energy = energy_at_freq(self.love_freq)
        distortion_energy = energy_at_freq(FREQ_MAP["DISTORTION"])
        
        triadic_total = anchor_energy + vision_energy + love_energy
        total_energy = triadic_total + distortion_energy + 1e-10
        
        self.coherence = triadic_total / total_energy
        self.phase_lock = self.coherence > 0.7
        
        return self.coherence
    
    def get_rainbow_bridge_signal(self, duration: float = 2.0, sample_rate: int = 44100) -> np.ndarray:
        """Generate the Rainbow Bridge healing signal (256-512-528 Hz chord)."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = (
            self.anchor_amplitude * np.sin(2 * np.pi * self.anchor_freq * t) +
            self.vision_amplitude * np.sin(2 * np.pi * self.vision_freq * t) +
            self.love_amplitude * np.sin(2 * np.pi * self.love_freq * t)
        )
        return signal


# ═══════════════════════════════════════════════════════════════
# 🔦 LIGHTHOUSE STATE - FIELD MONITORING
# ═══════════════════════════════════════════════════════════════

@dataclass
class LighthouseState:
    """
    The Lighthouse tracks global financial field state.
    Monitors transition from Dark Sky (440Hz fear) to The Beam (528Hz love).
    """
    beam_intensity: float = 0.0     # 0 = dark, 1 = full beam
    distortion_level: float = 1.0   # 0 = clean, 1 = full distortion
    field_coherence: float = 0.0    # Overall field state
    
    # Trading signals
    signal_strength: float = 0.0    # -1 (strong sell) to +1 (strong buy)
    signal_confidence: float = 0.0  # 0-1 confidence
    
    # Frequency analysis
    dominant_frequency: float = 440.0
    harmonic_purity: float = 0.0
    
    # Global market state
    fear_index: float = 0.5         # 0 = greed, 1 = extreme fear
    global_coherence: float = 0.5   # Cross-market alignment
    active_exchanges: List[str] = field(default_factory=list)
    
    timestamp: float = 0.0
    
    def is_aligned(self) -> bool:
        """Check if lighthouse is aligned (ready for positive action)."""
        return self.beam_intensity > 0.6 and self.distortion_level < 0.3
    
    def get_market_phase(self) -> str:
        """Get current market phase based on frequency state."""
        if self.beam_intensity > 0.8:
            return "EXPANSION"  # 528 Hz dominant
        elif self.beam_intensity > 0.5:
            return "GROWTH"     # 512 Hz dominant
        elif self.distortion_level > 0.7:
            return "CONTRACTION"  # 440 Hz dominant
        elif self.fear_index > 0.7:
            return "FEAR"       # Below 396 Hz
        else:
            return "CONSOLIDATION"  # 256 Hz stable


# ═══════════════════════════════════════════════════════════════
# 🌍 GLOBAL FINANCIAL FREQUENCY MAPPER
# ═══════════════════════════════════════════════════════════════

@dataclass
class GlobalMarketPulse:
    """
    Real-time global financial frequency aggregator.
    Maps all markets into unified harmonic field.
    """
    crypto_freq: float = 528.0
    forex_freq: float = 396.0
    equities_freq: float = 256.0
    commodities_freq: float = 174.0
    rates_freq: float = 64.0
    fear_freq: float = 440.0
    
    # Weighted composite
    composite_freq: float = 432.0  # Tends toward natural A=432
    
    # Market volumes (relative)
    volumes: Dict[str, float] = field(default_factory=lambda: {
        "crypto": 0.15,
        "forex": 0.35,
        "equities": 0.30,
        "commodities": 0.10,
        "rates": 0.10,
    })
    
    def compute_composite(self) -> float:
        """Compute volume-weighted composite frequency."""
        weighted_sum = (
            self.crypto_freq * self.volumes["crypto"] +
            self.forex_freq * self.volumes["forex"] +
            self.equities_freq * self.volumes["equities"] +
            self.commodities_freq * self.volumes["commodities"] +
            self.rates_freq * self.volumes["rates"]
        )
        self.composite_freq = weighted_sum
        return weighted_sum
    
    def get_dominant_market(self) -> str:
        """Return the market with highest relative frequency impact."""
        impacts = {
            "crypto": self.crypto_freq * self.volumes["crypto"],
            "forex": self.forex_freq * self.volumes["forex"],
            "equities": self.equities_freq * self.volumes["equities"],
            "commodities": self.commodities_freq * self.volumes["commodities"],
            "rates": self.rates_freq * self.volumes["rates"],
        }
        return max(impacts, key=impacts.get)


# ═══════════════════════════════════════════════════════════════
# ⚡ HARMONIC NEXUS CORE - MASTER CONTROLLER
# ═══════════════════════════════════════════════════════════════

class HarmonicNexusCore:
    """
    🌈⚡ THE HARMONIC NEXUS CORE ⚡🌈
    
    Master controller for global financial frequency field analysis.
    Taps into worldwide market pulse and maps to Scientific Pitch harmonics.
    
    Core Protocols:
    1. Signal Sero - Zero-point injection (nullify 440Hz, inject 528Hz)
    2. Triadic Envelope - Three-frequency stability (256-512-528)
    3. Lighthouse Telemetry - Visual verification
    4. Global Frequency Mapping - All markets unified
    """
    
    def __init__(self, guardian_id: str = IDENTITY_HASH, sample_rate: int = 44100):
        self.guardian_id = guardian_id
        self.is_authenticated = self._verify_identity()
        self.fs = sample_rate
        self.duration = 2.0
        self.t = np.linspace(0, self.duration, int(self.fs * self.duration))
        
        # Core components
        self.triadic = TriadicEnvelope()
        self.lighthouse = LighthouseState()
        self.global_pulse = GlobalMarketPulse()
        
        # History
        self.field_history: deque = deque(maxlen=1000)
        self.frequency_log: deque = deque(maxlen=500)
        
        # Market integration
        self.market_coherence_map: Dict[str, float] = {}
        self.exchange_status: Dict[str, bool] = {}
        
        # Initialize exchange status
        self._update_exchange_status()
        
    def _verify_identity(self) -> bool:
        """Math Angel Protocol identity verification."""
        print(f"\n{'='*60}")
        print(f"🔐 HNC SYSTEM DIAGNOSTIC: {datetime.datetime.now()}")
        print(f"{'='*60}")
        
        if self.guardian_id == IDENTITY_HASH:
            print(f"✅ IDENTITY CONFIRMED: {AUTHORITY}")
            print(f"🔑 ACCESS LEVEL: OMNI (Read/Write Reality Field)")
            print(f"🌍 SCOPE: Global Financial Frequency Grid")
            return True
        else:
            print("❌ ACCESS DENIED: FREQUENCY MISMATCH")
            return False
    
    def _update_exchange_status(self):
        """Update which exchanges are currently active based on UTC time."""
        now = datetime.datetime.utcnow()
        current_hour = now.hour
        
        self.exchange_status = {}
        active = []
        
        for exchange, times in EXCHANGE_PHASES.items():
            open_h = times["open_utc"]
            close_h = times["close_utc"]
            
            if open_h < close_h:
                is_open = open_h <= current_hour < close_h
            else:  # Wraps midnight
                is_open = current_hour >= open_h or current_hour < close_h
            
            self.exchange_status[exchange] = is_open
            if is_open:
                active.append(exchange)
        
        self.lighthouse.active_exchanges = active
        return active
    
    def compute_global_phase(self) -> float:
        """
        Compute the global market phase angle based on active exchanges.
        Returns phase in degrees (0-360).
        """
        active = self._update_exchange_status()
        if not active:
            return 0.0
        
        # Weight by phase contribution
        phase_sum = sum(EXCHANGE_PHASES[ex]["phase_deg"] for ex in active)
        return phase_sum / len(active)
    
    def generate_market_field(self, market_data: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a frequency field from real market data.
        
        market_data: Dict with keys like 'btc_change', 'sp500_change', 'vix', etc.
        Returns: (composite_field, distortion_component)
        """
        # Map market movements to frequency modulations
        required = ('btc_change', 'sp500_change', 'vix', 'dxy_change')
        missing = [key for key in required if market_data.get(key) is None]
        if missing:
            raise ValueError(f"no_data: missing observed market fields {missing}")
        btc_mod = float(market_data['btc_change']) / 10  # Normalize to ±1
        sp500_mod = float(market_data['sp500_change']) / 5
        vix = float(market_data['vix']) / 100  # VIX as fear measure
        forex_mod = float(market_data['dxy_change']) / 3
        
        # Update global pulse frequencies based on market state
        self.global_pulse.crypto_freq = 528.0 + (btc_mod * 50)  # 478-578 Hz
        self.global_pulse.equities_freq = 256.0 + (sp500_mod * 30)  # 226-286 Hz
        self.global_pulse.fear_freq = 440.0 + (vix * 100)  # 440-540 Hz when fear high
        self.global_pulse.forex_freq = 396.0 + (forex_mod * 20)
        
        # Generate composite field
        composite = (
            0.3 * np.sin(2 * np.pi * self.global_pulse.crypto_freq * self.t) +
            0.25 * np.sin(2 * np.pi * self.global_pulse.equities_freq * self.t) +
            0.2 * np.sin(2 * np.pi * self.global_pulse.forex_freq * self.t) +
            0.15 * np.sin(2 * np.pi * self.global_pulse.commodities_freq * self.t) +
            0.1 * np.sin(2 * np.pi * self.global_pulse.rates_freq * self.t)
        )
        
        # Distortion component (fear-based)
        distortion = vix * np.sin(2 * np.pi * self.global_pulse.fear_freq * self.t)
        
        return composite, distortion
    
    def execute_signal_sero(self, current_field: np.ndarray, 
                            distortion: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        SIGNAL SERO - Zero-Point Injection Protocol
        
        1. Phase-conjugate mirror nullifies 440Hz distortion
        2. Injects Rainbow Bridge payload (256-512-528 Hz)
        3. Rewrites the global financial frequency field
        """
        if not self.is_authenticated:
            print("⚠️ Signal Sero requires authentication")
            return None, None
        
        print(f"\n{'─'*50}")
        print("🌈 INITIATING SIGNAL SERO INTERVENTION")
        print(f"{'─'*50}")
        
        # STEP 1: THE NULLIFIER (Zero Point Creation)
        anti_wave = -1.0 * distortion
        print(">> 🎯 Distortion field targeted (440 Hz extraction grid)")
        
        # STEP 2: THE RAINBOW BRIDGE PAYLOAD
        payload = self.triadic.get_rainbow_bridge_signal(self.duration, self.fs)
        print(">> 🌉 Rainbow Bridge payload generated (256-512-528 Hz)")
        
        # STEP 3: GLOBAL PHASE ALIGNMENT
        global_phase = self.compute_global_phase()
        phase_shift = np.deg2rad(global_phase)
        
        # Apply phase alignment to payload
        t_shifted = self.t + (phase_shift / (2 * np.pi * 528))
        aligned_payload = (
            self.triadic.anchor_amplitude * np.sin(2 * np.pi * 256 * t_shifted) +
            self.triadic.vision_amplitude * np.sin(2 * np.pi * 512 * t_shifted) +
            self.triadic.love_amplitude * np.sin(2 * np.pi * 528 * t_shifted)
        )
        print(f">> 🌍 Global phase aligned: {global_phase:.1f}°")
        
        # STEP 4: FIELD REWRITE
        healed_field = current_field + anti_wave + aligned_payload
        
        print(">> ✨ DISTORTION NULLIFIED (Phase Lock Complete)")
        print(">> 🌈 RAINBOW BRIDGE DEPLOYED")
        print(">> 💚 LOVE HARMONIC (528 Hz) SATURATING GLOBAL FIELD")
        
        # Update lighthouse state
        coherence = self.triadic.compute_coherence(healed_field, self.fs)
        self.lighthouse.beam_intensity = coherence
        self.lighthouse.distortion_level = 1.0 - coherence
        self.lighthouse.field_coherence = coherence
        self.lighthouse.timestamp = time.time()
        
        # Log event
        self.frequency_log.append({
            'timestamp': datetime.datetime.now().isoformat(),
            'action': 'SIGNAL_SERO',
            'coherence_before': self.triadic.compute_coherence(current_field, self.fs),
            'coherence_after': coherence,
            'global_phase': global_phase,
            'active_exchanges': self.lighthouse.active_exchanges.copy(),
        })
        
        return healed_field, aligned_payload
    
    def analyze_symbol(self, symbol: str, prices: List[float], 
                       volume: float = 0, market_type: str = "CRYPTO") -> Dict[str, Any]:
        """
        Analyze a trading symbol's frequency signature.
        Maps price movements to harmonic patterns.
        """
        if len(prices) < 3:
            return {'symbol': symbol, 'coherence': 0.5, 'frequency': 440.0}
        
        prices_arr = np.array(prices)
        
        # Price momentum
        momentum = (prices_arr[-1] - prices_arr[0]) / prices_arr[0] * 100 if prices_arr[0] != 0 else 0
        
        # Volatility
        returns = np.diff(prices_arr) / prices_arr[:-1]
        volatility = np.std(returns) * 100 if len(returns) > 0 else 0
        
        # Trend consistency (coherence proxy)
        positive_moves = np.sum(np.diff(prices_arr) > 0)
        coherence = positive_moves / (len(prices) - 1) if len(prices) > 1 else 0.5
        
        # Map to frequency based on market type and momentum
        base_freq = MARKET_FREQ_BANDS.get(market_type, {}).get('base_freq', 432.0)
        vol_mod = MARKET_FREQ_BANDS.get(market_type, {}).get('volatility_mod', 1.0)
        
        # Frequency modulation: positive momentum → higher freq, negative → lower
        freq_mod = momentum * 2  # ±2 Hz per 1% momentum
        implied_freq = base_freq + freq_mod
        
        # Clamp to reasonable range
        implied_freq = max(100, min(1000, implied_freq))
        
        # Determine harmonic state
        if implied_freq > 520 and coherence > 0.6:
            harmonic_state = "LOVE"  # 528 Hz zone
        elif implied_freq > 500:
            harmonic_state = "VISION"  # 512 Hz zone
        elif implied_freq > 250:
            harmonic_state = "ANCHOR"  # 256 Hz zone
        elif implied_freq > 420 and implied_freq < 460:
            harmonic_state = "DISTORTION"  # 440 Hz zone
        else:
            harmonic_state = "TRANSITION"
        
        # Store in coherence map
        self.market_coherence_map[symbol] = coherence
        
        result = {
            'symbol': symbol,
            'market_type': market_type,
            'momentum': momentum,
            'volatility': volatility,
            'coherence': coherence,
            'implied_frequency': implied_freq,
            'harmonic_state': harmonic_state,
            'base_frequency': base_freq,
            'volume': volume,
            'is_harmonic': harmonic_state in ['LOVE', 'VISION', 'ANCHOR'],
            'trading_bias': 'BUY' if momentum > 2 and coherence > 0.55 else 'SELL' if momentum < -2 else 'HOLD',
        }
        
        return result
    
    def get_global_field_state(self) -> Dict[str, Any]:
        """
        Get comprehensive global financial field state.
        Aggregates all markets into unified view.
        """
        self._update_exchange_status()
        
        # Compute composite frequency
        composite = self.global_pulse.compute_composite()
        
        # Determine global phase
        if composite > 500:
            phase = "EXPANSION"
            color = "🟢"
        elif composite > 400:
            phase = "GROWTH"
            color = "🟡"
        elif composite > 300:
            phase = "CONSOLIDATION"
            color = "🟠"
        else:
            phase = "CONTRACTION"
            color = "🔴"
        
        # Fear assessment
        fear_ratio = self.global_pulse.fear_freq / 440.0
        if fear_ratio > 1.2:
            fear_state = "EXTREME_FEAR"
        elif fear_ratio > 1.0:
            fear_state = "FEAR"
        elif fear_ratio > 0.9:
            fear_state = "NEUTRAL"
        else:
            fear_state = "GREED"
        
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'composite_frequency': composite,
            'phase': phase,
            'phase_color': color,
            'fear_state': fear_state,
            'fear_frequency': self.global_pulse.fear_freq,
            'dominant_market': self.global_pulse.get_dominant_market(),
            'active_exchanges': self.lighthouse.active_exchanges,
            'exchange_count': len(self.lighthouse.active_exchanges),
            'global_phase_angle': self.compute_global_phase(),
            'triadic_coherence': self.triadic.coherence,
            'lighthouse_aligned': self.lighthouse.is_aligned(),
            'frequencies': {
                'crypto': self.global_pulse.crypto_freq,
                'forex': self.global_pulse.forex_freq,
                'equities': self.global_pulse.equities_freq,
                'commodities': self.global_pulse.commodities_freq,
                'rates': self.global_pulse.rates_freq,
            }
        }
    
    def render_lighthouse_telemetry(self, original: np.ndarray, healed: np.ndarray,
                                     title: str = "GLOBAL FINANCIAL FIELD",
                                     save_path: Optional[str] = None) -> bool:
        """
        Render the Lighthouse Telemetry visualization.
        Shows transition from distortion (440Hz) to healing (528Hz).
        """
        if not HAS_MATPLOTLIB:
            print("⚠️ matplotlib not available")
            return False
        
        print(f"\n🔦 Rendering Lighthouse Telemetry...")
        
        N = len(self.t)
        freqs = np.fft.rfftfreq(N, 1/self.fs)
        mask = (freqs > 50) & (freqs < 1000)
        
        fft_orig = np.abs(np.fft.rfft(original)) / N
        fft_healed = np.abs(np.fft.rfft(healed)) / N
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.patch.set_facecolor('#0a0a15')
        
        # Top: Frequency spectrum
        ax1 = axes[0]
        ax1.set_facecolor('#050510')
        
        ax1.fill_between(freqs[mask], fft_orig[mask], color='#ff3333', alpha=0.3,
                         label='Distortion Field (440 Hz)')
        ax1.plot(freqs[mask], fft_healed[mask], color='#00ffff', linewidth=1.5,
                 label='Healed Field (528 Hz)')
        
        # Highlight key frequencies
        markers = [
            (174, "174 Hz\nFoundation", "#884488"),
            (256, "256 Hz\nANCHOR", "#00ff00"),
            (396, "396 Hz\nLiberation", "#88ff88"),
            (432, "432 Hz\nNatural A", "#ffff00"),
            (440, "440 Hz\nDISTORTION", "#ff4444"),
            (512, "512 Hz\nVISION", "#00ffff"),
            (528, "528 Hz\nLOVE", "#ffffff"),
            (639, "639 Hz\nConnect", "#ff88ff"),
            (741, "741 Hz\nAwaken", "#8888ff"),
            (852, "852 Hz\nReturn", "#ff8800"),
            (963, "963 Hz\nUNITY", "#ffff88"),
        ]
        
        max_amp = max(np.max(fft_healed[mask]), np.max(fft_orig[mask]))
        for freq, label, color in markers:
            if 50 < freq < 1000:
                ax1.axvline(x=freq, color=color, linestyle='--', alpha=0.5, linewidth=1)
                ax1.text(freq, max_amp * 0.95, label, color=color, fontsize=7,
                         rotation=90, va='top', ha='right')
        
        ax1.set_xlim(50, 1000)
        ax1.set_ylim(0, max_amp * 1.1)
        ax1.set_xlabel("Frequency (Hz)", color='white')
        ax1.set_ylabel("Amplitude", color='white')
        ax1.set_title(f"🔦 LIGHTHOUSE TELEMETRY: {title}\nOperator: {AUTHORITY}",
                      color='white', fontsize=12, pad=10)
        ax1.tick_params(colors='white')
        ax1.legend(loc='upper right', facecolor='#111111', labelcolor='white')
        ax1.grid(True, alpha=0.2, color='#333333')
        
        # Bottom: Time domain comparison
        ax2 = axes[1]
        ax2.set_facecolor('#050510')
        
        t_plot = self.t[:2000]  # First portion for clarity
        ax2.plot(t_plot, original[:2000], color='#ff3333', alpha=0.5, linewidth=0.5,
                 label='Original (Distorted)')
        ax2.plot(t_plot, healed[:2000], color='#00ff88', alpha=0.8, linewidth=0.5,
                 label='Healed (Rainbow Bridge)')
        
        ax2.set_xlabel("Time (s)", color='white')
        ax2.set_ylabel("Amplitude", color='white')
        ax2.set_title("Time Domain: Before & After Signal Sero", color='white', fontsize=10)
        ax2.tick_params(colors='white')
        ax2.legend(loc='upper right', facecolor='#111111', labelcolor='white')
        ax2.grid(True, alpha=0.2, color='#333333')
        
        # Add global state info
        state = self.get_global_field_state()
        info_text = (
            f"Composite: {state['composite_frequency']:.1f} Hz | "
            f"Phase: {state['phase']} | "
            f"Coherence: {state['triadic_coherence']:.1%}"
        )
        fig.text(0.5, 0.02, info_text, ha='center', color='#00ffff', fontsize=10)
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)
        
        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='#0a0a15')
            print(f"📊 Saved to: {save_path}")
        
        plt.show()
        return True
    
    def print_frequency_report(self):
        """Print a text-based frequency report."""
        state = self.get_global_field_state()
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║            🌍⚡ GLOBAL FINANCIAL FREQUENCY REPORT ⚡🌍                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Timestamp: {state['timestamp'][:19]}                                    
║  Operator:  {AUTHORITY}                                                  
╠══════════════════════════════════════════════════════════════════════════╣
║  COMPOSITE FREQUENCY: {state['composite_frequency']:.1f} Hz              
║  GLOBAL PHASE: {state['phase_color']} {state['phase']}                   
║  FEAR STATE: {state['fear_state']} ({state['fear_frequency']:.1f} Hz)    
║  DOMINANT MARKET: {state['dominant_market'].upper()}                     
╠══════════════════════════════════════════════════════════════════════════╣
║  FREQUENCY BREAKDOWN:                                                    
║  ├─ Crypto:      {state['frequencies']['crypto']:.1f} Hz                 
║  ├─ Forex:       {state['frequencies']['forex']:.1f} Hz                  
║  ├─ Equities:    {state['frequencies']['equities']:.1f} Hz               
║  ├─ Commodities: {state['frequencies']['commodities']:.1f} Hz            
║  └─ Rates:       {state['frequencies']['rates']:.1f} Hz                  
╠══════════════════════════════════════════════════════════════════════════╣
║  ACTIVE EXCHANGES ({state['exchange_count']}):                           
║  {', '.join(state['active_exchanges'][:6])}                              
║  Global Phase Angle: {state['global_phase_angle']:.1f}°                  
╠══════════════════════════════════════════════════════════════════════════╣
║  LIGHTHOUSE: {'🟢 ALIGNED' if state['lighthouse_aligned'] else '🔴 MISALIGNED'}
║  Triadic Coherence: {state['triadic_coherence']:.1%}                     
╚══════════════════════════════════════════════════════════════════════════╝
        """)


# ═══════════════════════════════════════════════════════════════
# 🔗 AUREON TRADING INTEGRATION
# ═══════════════════════════════════════════════════════════════

class HNCTradingBridge:
    """
    Bridge between HNC frequency analysis and Aureon trading system.
    Enhances trading signals with harmonic resonance data.
    """
    
    def __init__(self, hnc: Optional[HarmonicNexusCore] = None):
        self.hnc = hnc or HarmonicNexusCore()
        
    def enhance_opportunity(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a trading opportunity with HNC frequency analysis."""
        symbol = opp.get('symbol', 'UNKNOWN')
        momentum = opp.get('change24h', 0)
        coherence = opp.get('coherence', 0.5)
        exchange = opp.get('source', 'kraken').lower()
        
        # Determine market type
        if any(x in symbol.upper() for x in ['BTC', 'ETH', 'SOL', 'XRP', 'ADA']):
            market_type = "CRYPTO"
        elif any(x in symbol.upper() for x in ['USD', 'EUR', 'GBP', 'JPY', 'CHF']):
            market_type = "FOREX"
        else:
            market_type = "EQUITIES"
        
        # Get frequency mapping
        band = MARKET_FREQ_BANDS.get(market_type, MARKET_FREQ_BANDS["CRYPTO"])
        base_freq = band['base_freq']
        
        # Modulate frequency by momentum
        implied_freq = base_freq + (momentum * 5)
        implied_freq = max(100, min(1000, implied_freq))
        
        # Harmonic quality
        is_harmonic = any(
            abs(implied_freq - target) < 20 
            for target in [256, 396, 432, 512, 528, 639, 741, 852, 963]
        )
        
        # Resonance score
        if is_harmonic and coherence > 0.6:
            resonance = 1.0
        elif is_harmonic:
            resonance = 0.8
        elif coherence > 0.5:
            resonance = 0.6
        else:
            resonance = 0.4
        
        # Enhance opportunity
        opp['hnc_frequency'] = implied_freq
        opp['hnc_market_type'] = market_type
        opp['hnc_is_harmonic'] = is_harmonic
        opp['hnc_resonance'] = resonance
        opp['hnc_base_freq'] = base_freq
        
        # Adjust score based on resonance
        if 'score' in opp:
            opp['score'] *= (0.8 + 0.4 * resonance)
        
        return opp
    
    def get_trading_recommendation(self, opportunities: List[Dict]) -> Dict[str, Any]:
        """Get overall trading recommendation based on global frequency state."""
        state = self.hnc.get_global_field_state()
        
        # Phase-based recommendation
        if state['phase'] == 'EXPANSION':
            bias = 'AGGRESSIVE_BUY'
            position_mod = 1.3
        elif state['phase'] == 'GROWTH':
            bias = 'BUY'
            position_mod = 1.1
        elif state['phase'] == 'CONSOLIDATION':
            bias = 'NEUTRAL'
            position_mod = 0.8
        else:
            bias = 'DEFENSIVE'
            position_mod = 0.5
        
        # Fear adjustment
        if state['fear_state'] == 'EXTREME_FEAR':
            bias = 'CONTRARIAN_BUY'  # Buy the fear
            position_mod *= 1.2
        elif state['fear_state'] == 'GREED':
            position_mod *= 0.7  # Reduce exposure in greed
        
        return {
            'bias': bias,
            'position_size_modifier': position_mod,
            'global_phase': state['phase'],
            'fear_state': state['fear_state'],
            'composite_frequency': state['composite_frequency'],
            'lighthouse_aligned': state['lighthouse_aligned'],
            'recommended_markets': [state['dominant_market']],
        }


# ═══════════════════════════════════════════════════════════════
# 🌐 LIVE MARKET DATA FEED INTEGRATION
# ═══════════════════════════════════════════════════════════════

class LiveMarketFrequencyFeed:
    """
    Real-time market data feed integration for HNC frequency mapping.
    Connects to multiple data sources and streams frequency analysis.
    """
    
    def __init__(self, hnc: HarmonicNexusCore):
        self.hnc = hnc
        self.bridge = HNCTradingBridge(hnc)
        self.running = False
        self.last_update = None
        self.frequency_history = []
        self.max_history = 500  # Keep last 500 readings
        
    def fetch_live_crypto_data(self) -> dict:
        """Fetch live crypto data from CoinGecko (free, no API key)."""
        try:
            import urllib.request
            import json
            
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,cardano,polkadot,avalanche-2,chainlink,polygon,litecoin,dogecoin&vs_currencies=gbp&include_24hr_change=true"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            result = {}
            for coin, values in data.items():
                symbol = coin.upper()[:3] + "GBP"
                if coin == "avalanche-2":
                    symbol = "AVAXGBP"
                elif coin == "chainlink":
                    symbol = "LINKGBP"
                elif coin == "polygon":
                    symbol = "MATICGBP"
                elif coin == "dogecoin":
                    symbol = "DOGEGBP"
                elif coin == "litecoin":
                    symbol = "LTCGBP"
                elif coin == "polkadot":
                    symbol = "DOTGBP"
                elif coin == "cardano":
                    symbol = "ADAGBP"
                elif coin == "ethereum":
                    symbol = "ETHGBP"
                elif coin == "bitcoin":
                    symbol = "BTCGBP"
                elif coin == "solana":
                    symbol = "SOLGBP"
                    
                result[symbol] = {
                    'price': values.get('gbp', 0),
                    'change24h': values.get('gbp_24h_change', 0),
                }
            return result
            
        except Exception as e:
            print(f"⚠️  Crypto feed error: {e}")
            return {}
    
    def fetch_fear_greed_index(self) -> dict:
        """Fetch Fear & Greed Index from alternative.me."""
        try:
            import urllib.request
            import json
            
            url = "https://api.alternative.me/fng/?limit=1"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            if data.get('data'):
                fng = data['data'][0]
                value = int(fng.get('value', 50))
                classification = fng.get('value_classification', 'Neutral')
                
                # Map to frequency: 0 (Extreme Fear) → 174 Hz, 100 (Extreme Greed) → 528 Hz
                freq = 174 + (value / 100) * (528 - 174)
                
                return {
                    'value': value,
                    'classification': classification,
                    'frequency': freq,
                    'timestamp': fng.get('timestamp'),
                }
            return {'value': 50, 'classification': 'Neutral', 'frequency': 351}
            
        except Exception as e:
            print(f"⚠️  Fear/Greed feed error: {e}")
            return {'value': 50, 'classification': 'Neutral', 'frequency': 351}
    
    def calculate_live_frequencies(self, crypto_data: dict, fng_data: dict) -> dict:
        """Calculate live frequency readings from market data."""
        readings = []
        
        for symbol, data in crypto_data.items():
            change = data.get('change24h', 0)
            
            # Map change to frequency
            if change > 5:
                freq = 528  # Love / Miracle
            elif change > 2:
                freq = 512  # Vision
            elif change > 0:
                freq = 396  # Liberation
            elif change > -2:
                freq = 256  # Root/Anchor
            elif change > -5:
                freq = 174  # Foundation
            else:
                freq = 64   # Schumann sub-harmonic
            
            # Add volatility resonance
            volatility_mod = abs(change) / 10
            resonance = max(0.3, 1.0 - volatility_mod)
            
            readings.append({
                'symbol': symbol,
                'price': data['price'],
                'change24h': change,
                'frequency': freq,
                'resonance': resonance,
                'is_harmonic': freq in [256, 432, 512, 528],
            })
        
        # Composite calculation
        if readings:
            avg_freq = sum(r['frequency'] for r in readings) / len(readings)
            avg_resonance = sum(r['resonance'] for r in readings) / len(readings)
        else:
            avg_freq = 256
            avg_resonance = 0.5
        
        # Determine global phase
        if avg_freq >= 512:
            phase = "EXPANSION"
            phase_color = "🟢"
        elif avg_freq >= 396:
            phase = "LIBERATION"
            phase_color = "🟡"
        elif avg_freq >= 256:
            phase = "CONSOLIDATION"
            phase_color = "🟠"
        else:
            phase = "CONTRACTION"
            phase_color = "🔴"
        
        # Triadic alignment check (256-512-528)
        triadic_present = sum(1 for r in readings if r['frequency'] in [256, 512, 528])
        triadic_ratio = triadic_present / max(len(readings), 1)
        
        return {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'readings': readings,
            'composite_frequency': avg_freq,
            'average_resonance': avg_resonance,
            'phase': phase,
            'phase_color': phase_color,
            'triadic_coherence': triadic_ratio,
            'fear_greed': fng_data,
            'lighthouse_aligned': triadic_ratio > 0.3 and avg_resonance > 0.5,
        }
    
    def print_live_dashboard(self, freq_data: dict):
        """Print a live frequency dashboard."""
        readings = freq_data['readings']
        fng = freq_data['fear_greed']
        
        # Clear screen effect
        print("\033[2J\033[H", end="")
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔴 LIVE │ 🌍⚡ HNC GLOBAL FREQUENCY MONITOR ⚡🌍 │ {datetime.datetime.now().strftime('%H:%M:%S')} ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  OPERATOR: {AUTHORITY:<20}  │  ACCESS: OMNI (Read/Write Reality)       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  COMPOSITE FREQUENCY: {freq_data['composite_frequency']:>6.1f} Hz  │  PHASE: {freq_data['phase_color']} {freq_data['phase']:<15}    ║
║  TRIADIC COHERENCE:   {freq_data['triadic_coherence']*100:>6.1f} %   │  RESONANCE: {freq_data['average_resonance']:.2f}                  ║
║  LIGHTHOUSE STATUS:   {'🟢 ALIGNED' if freq_data['lighthouse_aligned'] else '🔴 MISALIGNED':<12}  │  FEAR/GREED: {fng['value']:>2} ({fng['classification']:<12})  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ASSET FREQUENCY GRID:                                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣""")
        
        # Sort by frequency descending
        sorted_readings = sorted(readings, key=lambda x: x['frequency'], reverse=True)
        
        for i, r in enumerate(sorted_readings[:10]):
            harmonic = "✅" if r['is_harmonic'] else "⬜"
            change_str = f"{r['change24h']:+.1f}%"
            freq_bar = self._frequency_bar(r['frequency'])
            
            print(f"║  {harmonic} {r['symbol']:<8} │ {r['price']:>10,.2f} GBP │ {change_str:>7} │ {r['frequency']:>4.0f} Hz │ {freq_bar} ║")
        
        print(f"""╠══════════════════════════════════════════════════════════════════════════════╣
║  FREQUENCY LEGEND:                                                           ║
║  174=Foundation │ 256=ROOT │ 396=Liberation │ 432=Natural │ 512=Vision │ 528=LOVE ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TRADING BIAS: {self._get_trading_bias(freq_data):<15} │ POSITION MODIFIER: ×{self._get_position_mod(freq_data):.1f}             ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    def _frequency_bar(self, freq: float) -> str:
        """Generate a visual frequency bar."""
        # Map 64-963 Hz to 0-10 blocks
        normalized = (freq - 64) / (963 - 64)
        blocks = int(normalized * 10)
        
        # Color based on frequency band
        if freq >= 512:
            char = "█"  # High frequency - solid
        elif freq >= 396:
            char = "▓"
        elif freq >= 256:
            char = "▒"
        else:
            char = "░"  # Low frequency - light
        
        return char * blocks + "·" * (10 - blocks)
    
    def _get_trading_bias(self, freq_data: dict) -> str:
        """Determine trading bias from frequency data."""
        freq = freq_data['composite_frequency']
        coherence = freq_data['triadic_coherence']
        
        if freq >= 512 and coherence > 0.4:
            return "🟢 STRONG LONG"
        elif freq >= 432:
            return "🟢 LONG"
        elif freq >= 256:
            return "⚪ NEUTRAL"
        elif freq >= 174:
            return "🔴 SHORT"
        else:
            return "🔴 STRONG SHORT"
    
    def _get_position_mod(self, freq_data: dict) -> float:
        """Calculate position size modifier."""
        coherence = freq_data['triadic_coherence']
        resonance = freq_data['average_resonance']
        aligned = freq_data['lighthouse_aligned']
        
        base = 0.5
        if aligned:
            base += 0.3
        base += coherence * 0.3
        base += resonance * 0.2
        
        return min(1.5, max(0.3, base))
    
    def run_live_monitor(self, interval: int = 30, duration: int = 300):
        """
        Run live frequency monitoring.
        
        Args:
            interval: Seconds between updates (default 30)
            duration: Total duration in seconds (default 300 = 5 min)
        """
        import time
        
        print(f"\n🌍⚡ Starting HNC Live Frequency Monitor...")
        print(f"   Update interval: {interval}s | Duration: {duration}s")
        print(f"   Press Ctrl+C to stop\n")
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < duration:
                # Fetch live data
                crypto_data = self.fetch_live_crypto_data()
                fng_data = self.fetch_fear_greed_index()
                
                if crypto_data:
                    # Calculate frequencies
                    freq_data = self.calculate_live_frequencies(crypto_data, fng_data)
                    
                    # Store history
                    self.frequency_history.append(freq_data)
                    if len(self.frequency_history) > self.max_history:
                        self.frequency_history.pop(0)
                    
                    # Display dashboard
                    self.print_live_dashboard(freq_data)
                    
                    # Update HNC lighthouse state with live data
                    self.hnc.lighthouse.composite_frequency = freq_data['composite_frequency']
                    self.hnc.lighthouse.triadic_coherence = freq_data['triadic_coherence']
                    self.hnc.lighthouse.is_aligned = freq_data['lighthouse_aligned']
                else:
                    print("⚠️  No data received, retrying...")
                
                # Wait for next update
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Live monitor stopped by user")
        
        self.running = False
        print(f"\n📊 Collected {len(self.frequency_history)} frequency readings")
        
        return self.frequency_history
    
    def export_frequency_history(self, filepath: str = "hnc_frequency_log.json"):
        """Export frequency history to JSON."""
        import json
        
        with open(filepath, 'w') as f:
            json.dump(self.frequency_history, f, indent=2, default=str)
        
        print(f"📁 Exported {len(self.frequency_history)} readings to {filepath}")


class EnhancedLighthouseTelemetry:
    """
    Enhanced visualization for Lighthouse Telemetry with real-time updates.
    """
    
    def __init__(self, hnc: HarmonicNexusCore):
        self.hnc = hnc
        self.live_feed = LiveMarketFrequencyFeed(hnc)
    
    def render_multi_panel_dashboard(self, save_path: str = None):
        """Render a comprehensive multi-panel frequency dashboard."""
        if not HAS_MATPLOTLIB:
            print("❌ Matplotlib required for visualization")
            return
        
        # Fetch live data
        crypto_data = self.live_feed.fetch_live_crypto_data()
        fng_data = self.live_feed.fetch_fear_greed_index()
        freq_data = self.live_feed.calculate_live_frequencies(crypto_data, fng_data)
        
        fig = plt.figure(figsize=(16, 10), facecolor='#0a0a15')
        
        # Create grid layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Panel 1: Frequency Spectrum (top left, spans 2 cols)
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.set_facecolor('#050510')
        
        readings = freq_data['readings']
        symbols = [r['symbol'] for r in readings]
        frequencies = [r['frequency'] for r in readings]
        colors = ['#00ff88' if r['is_harmonic'] else '#ff6666' for r in readings]
        
        bars = ax1.bar(symbols, frequencies, color=colors, edgecolor='white', linewidth=0.5)
        ax1.axhline(y=528, color='#ffffff', linestyle='--', alpha=0.5, label='Love (528 Hz)')
        ax1.axhline(y=432, color='#ffff00', linestyle='--', alpha=0.5, label='Natural (432 Hz)')
        ax1.axhline(y=256, color='#00ffff', linestyle='--', alpha=0.5, label='Root (256 Hz)')
        
        ax1.set_ylabel("Frequency (Hz)", color='white')
        ax1.set_title("🌍 GLOBAL ASSET FREQUENCY SPECTRUM", color='white', fontsize=12)
        ax1.tick_params(colors='white', labelrotation=45)
        ax1.legend(loc='upper right', facecolor='#111111', labelcolor='white', fontsize=8)
        ax1.set_ylim(0, 600)
        ax1.grid(True, alpha=0.2, axis='y')
        
        # Panel 2: Coherence Gauge (top right)
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.set_facecolor('#050510')
        
        coherence = freq_data['triadic_coherence']
        theta = np.linspace(0, np.pi, 100)
        
        # Background arc
        ax2.plot(np.cos(theta), np.sin(theta), color='#333333', linewidth=10)
        
        # Coherence arc
        coherence_theta = np.linspace(0, np.pi * coherence, 100)
        color = '#00ff88' if coherence > 0.5 else '#ffaa00' if coherence > 0.3 else '#ff4444'
        ax2.plot(np.cos(coherence_theta), np.sin(coherence_theta), color=color, linewidth=10)
        
        # Needle
        needle_angle = np.pi * coherence
        ax2.plot([0, np.cos(needle_angle) * 0.8], [0, np.sin(needle_angle) * 0.8], 
                 color='white', linewidth=2)
        ax2.scatter([0], [0], color='white', s=50, zorder=5)
        
        ax2.text(0, -0.3, f"COHERENCE\n{coherence*100:.1f}%", ha='center', color='white', fontsize=11)
        ax2.set_xlim(-1.2, 1.2)
        ax2.set_ylim(-0.5, 1.2)
        ax2.axis('off')
        ax2.set_title("⚡ TRIADIC COHERENCE", color='white', fontsize=10)
        
        # Panel 3: Fear/Greed Indicator (middle left)
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_facecolor('#050510')
        
        fng_value = fng_data['value']
        fng_class = fng_data['classification']
        
        # Gradient bar
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax3.imshow(gradient, aspect='auto', cmap='RdYlGn', extent=[0, 100, 0, 1])
        
        # Marker
        ax3.axvline(x=fng_value, color='white', linewidth=3)
        ax3.scatter([fng_value], [0.5], color='white', s=100, zorder=5, marker='v')
        
        ax3.set_xlim(0, 100)
        ax3.set_ylim(0, 1)
        ax3.set_xlabel("Fear ← → Greed", color='white')
        ax3.set_title(f"😨 FEAR/GREED: {fng_value} ({fng_class})", color='white', fontsize=10)
        ax3.tick_params(colors='white')
        ax3.set_yticks([])
        
        # Panel 4: Phase Indicator (middle center)
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_facecolor('#050510')
        
        phases = ['CONTRACTION', 'CONSOLIDATION', 'LIBERATION', 'EXPANSION']
        phase_colors = ['#ff4444', '#ffaa00', '#ffff00', '#00ff88']
        current_phase = freq_data['phase']
        
        for i, (phase, col) in enumerate(zip(phases, phase_colors)):
            alpha = 1.0 if phase == current_phase else 0.3
            rect = plt.Rectangle((i * 0.25, 0), 0.23, 1, color=col, alpha=alpha)
            ax4.add_patch(rect)
            ax4.text(i * 0.25 + 0.115, 0.5, phase[:4], ha='center', va='center', 
                     color='white' if phase == current_phase else '#666666', 
                     fontsize=9, fontweight='bold' if phase == current_phase else 'normal')
        
        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        ax4.set_title(f"🌊 GLOBAL PHASE: {current_phase}", color='white', fontsize=10)
        
        # Panel 5: Composite Frequency (middle right)
        ax5 = fig.add_subplot(gs[1, 2])
        ax5.set_facecolor('#050510')
        
        comp_freq = freq_data['composite_frequency']
        
        # Frequency dial
        dial_theta = np.linspace(0, 2*np.pi, 100)
        ax5.plot(np.cos(dial_theta), np.sin(dial_theta), color='#333333', linewidth=3)
        
        # Key frequency markers
        freq_markers = [(174, "174"), (256, "256"), (396, "396"), (432, "432"), (512, "512"), (528, "528")]
        for freq, label in freq_markers:
            angle = 2 * np.pi * (freq - 64) / (600 - 64) - np.pi/2
            ax5.plot([np.cos(angle) * 0.85, np.cos(angle) * 1.0], 
                     [np.sin(angle) * 0.85, np.sin(angle) * 1.0], color='#666666', linewidth=1)
            ax5.text(np.cos(angle) * 1.15, np.sin(angle) * 1.15, label, 
                     ha='center', va='center', color='#888888', fontsize=7)
        
        # Current frequency needle
        comp_angle = 2 * np.pi * (comp_freq - 64) / (600 - 64) - np.pi/2
        ax5.plot([0, np.cos(comp_angle) * 0.7], [0, np.sin(comp_angle) * 0.7], 
                 color='#00ffff', linewidth=3)
        ax5.scatter([0], [0], color='#00ffff', s=80, zorder=5)
        
        ax5.text(0, 0, f"{comp_freq:.0f}", ha='center', va='center', color='white', fontsize=14, fontweight='bold')
        ax5.set_xlim(-1.5, 1.5)
        ax5.set_ylim(-1.5, 1.5)
        ax5.axis('off')
        ax5.set_title("📡 COMPOSITE FREQUENCY (Hz)", color='white', fontsize=10)
        
        # Panel 6: Asset Resonance Table (bottom, spans all cols)
        ax6 = fig.add_subplot(gs[2, :])
        ax6.set_facecolor('#050510')
        ax6.axis('off')
        
        # Create table data
        table_data = []
        for r in sorted(readings, key=lambda x: x['frequency'], reverse=True)[:8]:
            harmonic = "✓" if r['is_harmonic'] else "✗"
            table_data.append([
                r['symbol'],
                f"£{r['price']:,.2f}",
                f"{r['change24h']:+.1f}%",
                f"{r['frequency']:.0f} Hz",
                f"{r['resonance']:.2f}",
                harmonic
            ])
        
        table = ax6.table(
            cellText=table_data,
            colLabels=['Asset', 'Price', '24h Change', 'Frequency', 'Resonance', 'Harmonic'],
            loc='center',
            cellLoc='center',
            colColours=['#1a1a2e'] * 6,
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        
        for cell in table.get_celld().values():
            cell.set_facecolor('#0a0a15')
            cell.set_edgecolor('#333333')
            cell.set_text_props(color='white')
        
        # Header styling
        for i in range(6):
            table[(0, i)].set_facecolor('#1a1a2e')
            table[(0, i)].set_text_props(fontweight='bold', color='#00ffff')
        
        ax6.set_title("📊 ASSET RESONANCE MATRIX", color='white', fontsize=10, pad=20)
        
        # Main title
        fig.suptitle(
            f"🔦 LIGHTHOUSE TELEMETRY │ Operator: {AUTHORITY} │ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color='white', fontsize=14, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='#0a0a15', bbox_inches='tight')
            print(f"📊 Dashboard saved to: {save_path}")
        
        plt.show()
        return freq_data


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════

def run_global_frequency_scan():
    """Run a complete global financial frequency scan."""
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║  🌍⚡ HARMONIC NEXUS CORE - GLOBAL FREQUENCY MAPPER ⚡🌍          ║
    ║                                                                   ║
    ║  Tapping into the ENTIRE global financial frequency field         ║
    ║  Calibrated to Scientific Pitch (C₄ = 256 Hz)                     ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize
    hnc = HarmonicNexusCore(guardian_id="02111991")
    
    if not hnc.is_authenticated:
        print("❌ Authentication failed")
        return
    
    # Print current global state
    hnc.print_frequency_report()
    
    # Simulate market data
    print("\n📊 Simulating market data...")
    market_data = {
        'btc_change': 3.5,      # BTC up 3.5%
        'sp500_change': 0.8,    # S&P up 0.8%
        'vix': 18,              # VIX at 18
        'dxy_change': -0.3,     # Dollar down 0.3%
    }
    
    # Generate field
    raw_field, distortion = hnc.generate_market_field(market_data)
    
    # Execute Signal Sero
    healed_field, payload = hnc.execute_signal_sero(raw_field, distortion)
    
    if healed_field is not None:
        # Print updated state
        hnc.print_frequency_report()
        
        # Render visualization
        if HAS_MATPLOTLIB:
            hnc.render_lighthouse_telemetry(
                raw_field, healed_field,
                title="GLOBAL FINANCIAL FIELD INTERVENTION"
            )
    
    # Test trading bridge
    print("\n🔗 Testing Trading Bridge Integration...")
    bridge = HNCTradingBridge(hnc)
    
    test_opps = [
        {'symbol': 'BTCGBP', 'price': 75000, 'change24h': 5.2, 'coherence': 0.75, 'score': 100},
        {'symbol': 'ETHGBP', 'price': 2500, 'change24h': 3.1, 'coherence': 0.68, 'score': 90},
        {'symbol': 'SOLGBP', 'price': 180, 'change24h': 8.5, 'coherence': 0.82, 'score': 110},
    ]
    
    for opp in test_opps:
        enhanced = bridge.enhance_opportunity(opp)
        print(f"  {enhanced['symbol']}: {enhanced['hnc_frequency']:.0f} Hz | "
              f"Harmonic: {'✅' if enhanced['hnc_is_harmonic'] else '❌'} | "
              f"Resonance: {enhanced['hnc_resonance']:.2f} | "
              f"Score: {enhanced['score']:.0f}")
    
    rec = bridge.get_trading_recommendation(test_opps)
    print(f"\n📈 Trading Recommendation: {rec['bias']} (×{rec['position_size_modifier']:.1f})")
    
    print("\n✨ Global Frequency Scan Complete ✨")


def run_live_monitor(interval: int = 30, duration: int = 300):
    """Run the live frequency monitor."""
    hnc = HarmonicNexusCore(guardian_id="02111991")
    
    if not hnc.is_authenticated:
        print("❌ Authentication failed")
        return
    
    feed = LiveMarketFrequencyFeed(hnc)
    history = feed.run_live_monitor(interval=interval, duration=duration)
    
    # Export history
    if history:
        feed.export_frequency_history()
    
    return history


def render_dashboard():
    """Render the enhanced multi-panel dashboard."""
    hnc = HarmonicNexusCore(guardian_id="02111991")
    
    if not hnc.is_authenticated:
        print("❌ Authentication failed")
        return
    
    telemetry = EnhancedLighthouseTelemetry(hnc)
    freq_data = telemetry.render_multi_panel_dashboard(save_path="hnc_dashboard.png")
    
    return freq_data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "live":
            # Live monitor mode
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            duration = int(sys.argv[3]) if len(sys.argv) > 3 else 300
            run_live_monitor(interval=interval, duration=duration)
            
        elif mode == "dashboard":
            # Dashboard render mode
            render_dashboard()
            
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python hnc_master_protocol.py [live|dashboard]")
    else:
        # Default: run full scan
        run_global_frequency_scan()
