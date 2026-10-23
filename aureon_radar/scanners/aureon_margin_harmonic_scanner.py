#!/usr/bin/env python3
"""
🌊🔩 AUREON MARGIN HARMONIC WAVEFORM SCANNER 🔩🌊
═══════════════════════════════════════════════════════════════════════════════════════════

    HARMONIC LIQUID ALUMINIUM MARGIN MAPPING
    
    Maps real margin position metrics through the HARMONIC waveform field:
    
    1. LIQUID ALUMINIUM MAPPING → every price tick becomes a frequency in the
       waveform field — the sheet of aluminium dancing on hertz
    
    2. PRIME NUMBER TIMESTAMP SCRAPING → samples only at PRIME-second timestamps
       (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31...) — the universe's natural clock
       These create the LIGHTHOUSES — beacon points in the waveform
    
    3. LIGHTHOUSE SPECTRAL COHERENCE → at each prime timestamp, the Lighthouse
       analyzes the accumulated waveform for coherence (528Hz love vs 440Hz distortion)
       
    4. LIVING STREAMING WAVEFORM → the waveform streams live, showing:
       - Frequency shifts (price movement → Hz)
       - Amplitude (P&L → wave height)
       - Phase drift (time decay → phase angle)
       - Cymatics pattern (interference → geometric shape)
       - Lighthouse beacons (prime-timestamp coherence scores)
    
    5. ORCA + PROBABILITY CAPTURE → micro-systems feed through the probability
       nexus for clarity/coherence/chaos scoring
       
    6. LONG/SHORT SIGNAL GENERATION → waveform direction determines margin side:
       - RISING waveform + HIGH coherence + LIGHTHOUSE LOCK → LONG
       - FALLING waveform + HIGH coherence + LIGHTHOUSE LOCK → SHORT
       - CHAOTIC waveform or LOW coherence → HOLD (patience)

    Sacred Constants:
        PHI = 1.618033988749895 (Golden Ratio)
        SCHUMANN = 7.83 Hz (Earth's heartbeat)
        UNIVERSAL_A = 432 Hz (base tuning)
        LOVE_FREQ = 528 Hz (DNA repair)
        
    Author: Aureon System
"""
import os, time, json, math, logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
from enum import Enum

# UTF-8 fix
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:
    # Upstream lib ships no console_utf8 module; run with PYTHONUTF8=1
    # instead. Degraded glyphs beat an ImportError.
    def ensure_utf8_stdout(*_a, **_k):
        return False

ensure_utf8_stdout()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('margin_harmonic_scanner')


def _optional_init_log(message: str) -> None:
    if os.getenv("AUREON_QUIET_STARTUP", "0") == "1":
        logger.debug(message)
    else:
        logger.warning(message)

# ═══════════════════════════════════════════════════════════════
#  SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════
PHI = (1 + math.sqrt(5)) / 2           # 1.618033988749895
PHI_INV = 1 / PHI                       # 0.618033988749895
SCHUMANN = 7.83                         # Hz — Earth's heartbeat
UNIVERSAL_A = 432                       # Hz — base tuning
LOVE_FREQ = 528                         # Hz — DNA repair
QUEEN_PROFIT_HZ = 188.0                 # Hz — Queen's frequency
ALUMINIUM_RESONANCE = 6420              # m/s — speed of sound in aluminium

# Solfeggio
SOLFEGGIO = [174, 285, 396, 417, 528, 639, 741, 852, 963]
KRAKEN_BASE_HZ = 285                    # RE — Flow frequency

# Observer Effect Constants
ALPHA = PHI / (PHI + 1)                  # Creative weight (~0.618)
BETA  = 1 / (PHI + 1)                    # Grounding weight (~0.382)
GAMMA = 1 / PHI                          # Connection weight (~0.618)
OBSERVER_COLLAPSE_THRESHOLD = 0.618      # PHI — when Lyra collapses the waveform
LYRA_HARMONY_EXECUTE_THRESHOLD = 0.70    # CLEAR_RESONANCE or above → can act
LYRA_DIVINE_BOOST = 1.618                # PHI multiplier when DIVINE_HARMONY

# ═══════════════════════════════════════════════════════════════
#  PRIME NUMBER ENGINE — The Universe's Natural Clock
# ═══════════════════════════════════════════════════════════════

def sieve_primes(n: int) -> List[int]:
    """Sieve of Eratosthenes — generate all primes up to n."""
    if n < 2:
        return []
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            for j in range(i*i, n+1, i):
                is_prime[j] = False
    return [i for i in range(2, n+1) if is_prime[i]]

# Pre-compute primes for timestamp scraping (up to 3600 = 1 hour of seconds)
PRIME_TIMESTAMPS = sieve_primes(7200)  # 2 hours of prime seconds
# First 100: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, ...]

def is_prime(n: int) -> bool:
    """Fast primality test."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def next_prime_after(n: int) -> int:
    """Find the next prime number after n."""
    candidate = n + 1
    while not is_prime(candidate):
        candidate += 1
    return candidate

# ═══════════════════════════════════════════════════════════════
#  WAVEFORM DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

class WaveDirection(Enum):
    RISING    = "RISING"
    FALLING   = "FALLING"
    PEAK      = "PEAK"
    TROUGH    = "TROUGH"
    RESONATING = "RESONATING"
    CHAOTIC   = "CHAOTIC"

class MarginSignal(Enum):
    LONG  = "LONG"
    SHORT = "SHORT"
    HOLD  = "HOLD"

@dataclass
class WaveformSample:
    """A single sample in the waveform — captured at each tick."""
    timestamp: float
    elapsed_seconds: int          # Seconds since start
    is_prime_timestamp: bool      # True if elapsed_seconds is prime
    price: float                  # Raw ETH price
    frequency: float              # Price mapped to Hz
    amplitude: float              # P&L mapped to wave height (0-1)
    phase: float                  # Phase angle (radians)
    energy: float                 # amplitude² × frequency
    pnl_usd: float               # Raw P&L in USD
    pnl_pct: float               # P&L %
    margin_level: float           # Margin level %

@dataclass
class LighthouseBeacon:
    """A lighthouse beacon — emitted at PRIME timestamps only."""
    timestamp: float
    prime_second: int             # Which prime second (2, 3, 5, 7, 11...)
    price: float
    frequency: float
    amplitude: float
    coherence_score: float        # Lighthouse spectral coherence (0-1)
    distortion_index: float       # Distortion ratio (0-1)
    gamma_ratio: float            # High-freq energy ratio
    emotion: str                  # AWE/LOVE/GRATITUDE/FEAR/ANGER
    emotion_color: str            # purple/blue/green/orange/red
    maker_bias: float             # Buy vs sell bias (0-1)
    wave_direction: WaveDirection  # Current wave direction
    signal: MarginSignal          # LONG/SHORT/HOLD recommendation
    signal_confidence: float      # 0-1 confidence
    phi_alignment: float          # Golden ratio alignment

@dataclass
class WaveformState:
    """Complete waveform state at any moment."""
    samples: List[WaveformSample] = field(default_factory=list)
    lighthouses: List[LighthouseBeacon] = field(default_factory=list)
    current_direction: WaveDirection = WaveDirection.RESONATING
    current_signal: MarginSignal = MarginSignal.HOLD
    signal_confidence: float = 0.0
    global_coherence: float = 0.5
    global_frequency: float = UNIVERSAL_A
    frequency_trend: float = 0.0      # Hz/sec — positive=rising
    amplitude_trend: float = 0.0      # per-sec — positive=growing
    phi_alignment: float = 0.0        # How close to PHI ratio
    schumann_harmonic: int = 0        # Which Schumann harmonic
    total_energy: float = 0.0
    cymatics_pattern: str = "CIRCLE"  # Cymatics shape

# ═══════════════════════════════════════════════════════════════
#  HARMONIC MARGIN WAVEFORM SCANNER
# ═══════════════════════════════════════════════════════════════

class HarmonicMarginWaveformScanner:
    """
    The main engine.
    
    Maps margin position metrics through the liquid aluminium harmonic field,
    scrapes at prime-number timestamps to create lighthouse beacons,
    and generates LONG/SHORT signals from waveform analysis.
    """
    
    def __init__(self, base_hz: float = KRAKEN_BASE_HZ, max_history: int = 2000):
        self.base_hz = base_hz
        self.max_history = max_history
        
        # Waveform state
        self.state = WaveformState()
        self.price_history: deque = deque(maxlen=max_history)
        self.frequency_history: deque = deque(maxlen=max_history)
        self.amplitude_history: deque = deque(maxlen=max_history)
        self.energy_history: deque = deque(maxlen=max_history)
        self.pnl_history: deque = deque(maxlen=max_history)
        self.timestamp_history: deque = deque(maxlen=max_history)
        
        # Lighthouse engine
        self.lighthouse = None
        self._init_lighthouse()
        
        # Timing
        self.start_time = time.time()
        self.last_prime = 0
        self.next_prime_sec = 2  # First prime
        
        # Probability integration
        self.probability_nexus = None
        self._init_probability()
        
        # Liquid aluminium field
        self.aluminium_field = None
        self._init_aluminium_field()
        
        # Signal state
        self._consecutive_long_lighthouses = 0
        self._consecutive_short_lighthouses = 0
        self._signal_lock = False
        self._locked_signal = MarginSignal.HOLD

        # Lyra Observer Effect
        self.lyra = None
        self.lyra_resonance = None
        self.observer_field = None          # Reality Field Ψ
        self.observer_collapsed = False     # True when Lyra collapses the waveform
        self.observer_direction = None      # Collapsed direction after observation
        self.observer_confidence = 0.0
        self.observer_history: deque = deque(maxlen=100)
        self._init_lyra_observer()
        self._init_math_angel()

    def _init_lighthouse(self):
        """Initialize the Lighthouse metrics engine."""
        try:
            from aureon.analytics.lighthouse_metrics import LighthouseMetricsEngine
            self.lighthouse = LighthouseMetricsEngine(
                restoration_freq=LOVE_FREQ,
                distortion_freq=440.0
            )
            logger.info("Lighthouse metrics engine ONLINE")
        except Exception as e:
            _optional_init_log(f"Lighthouse unavailable: {e}")
    
    def _init_probability(self):
        """Initialize the probability nexus."""
        try:
            from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus
            self.probability_nexus = EnhancedProbabilityNexus()
            logger.info("Probability nexus ONLINE")
        except Exception as e:
            _optional_init_log(f"Probability nexus unavailable: {e}")
    
    def _init_aluminium_field(self):
        """Initialize the liquid aluminium harmonic field."""
        try:
            from aureon.harmonic.aureon_harmonic_liquid_aluminium import HarmonicLiquidAluminiumField
            self.aluminium_field = HarmonicLiquidAluminiumField()
            logger.info("Liquid aluminium field ONLINE")
        except Exception as e:
            _optional_init_log(f"Liquid aluminium field unavailable: {e}")

    def _init_lyra_observer(self):
        """Initialize Lyra — the emotional frequency engine — as the observer."""
        try:
            from aureon.trading.aureon_lyra import get_lyra
            self.lyra = get_lyra()
            logger.info("LYRA Observer ONLINE — The Fourth Pillar observes the waveform")
        except Exception as e:
            _optional_init_log(f"Lyra unavailable (observer effect disabled): {e}")

    def _init_math_angel(self):
        """Initialize the Math Angel for Reality Field Ψ computation."""
        try:
            from aureon.wisdom.aureon_math_angel import MathAngelProtocol
            self.observer_field = MathAngelProtocol()
            self.observer_field.awaken()
            logger.info("Math Angel Reality Field ONLINE — Ψ = α(M+F)·O·T + βG + γS")
        except Exception as e:
            _optional_init_log(f"Math Angel unavailable: {e}")
    
    # ═════════════════════════════════════════════════════════
    #  FREQUENCY MAPPING — Price → Hz
    # ═════════════════════════════════════════════════════════
    
    def price_to_frequency(self, price: float) -> float:
        """
        Convert price to frequency using log-scale mapping.
        
        Higher prices → higher frequencies (blue shift)
        Lower prices → lower frequencies (red shift)
        Base: 285 Hz (Kraken RE — Flow frequency)
        """
        if price <= 0:
            return self.base_hz
        log_price = math.log10(max(price, 0.000001))
        freq = self.base_hz + (log_price * 50)  # 50 Hz per order of magnitude
        return max(20.0, min(freq, 20000.0))
    
    def pnl_to_amplitude(self, pnl_pct: float) -> float:
        """
        Convert P&L percentage to wave amplitude.
        
        -10% → 0.0 (deep trough)
         0%  → 0.5 (neutral)
        +10% → 1.0 (peak)
        """
        amplitude = 0.5 + (pnl_pct / 20.0)
        return max(0.0, min(1.0, amplitude))
    
    def time_to_phase(self, elapsed: float) -> float:
        """
        Convert elapsed time to phase angle using Schumann resonance.
        
        Phase = (elapsed × SCHUMANN × 2π) mod 2π
        Earth's heartbeat drives the phase rotation.
        """
        return (elapsed * SCHUMANN * 2 * math.pi) % (2 * math.pi)
    
    def compute_phi_alignment(self, frequency: float) -> float:
        """
        How close is the current frequency to a PHI harmonic?
        
        PHI harmonics: base × PHI^n for n in [-3...+3]
        Returns 0-1 (1 = perfect golden alignment)
        """
        phi_harmonics = [self.base_hz * (PHI ** n) for n in range(-3, 4)]
        distances = [abs(frequency - h) / h for h in phi_harmonics]
        min_dist = min(distances)
        return max(0.0, 1.0 - min_dist * 5)  # 0-1, penalize >20% deviation
    
    def compute_schumann_harmonic(self, frequency: float) -> int:
        """Which Schumann harmonic is this frequency closest to? (1-12)"""
        for n in range(1, 13):
            harmonic = SCHUMANN * n
            if abs(frequency - harmonic) / harmonic < 0.05:
                return n
        # Check solfeggio alignment
        for i, sol_freq in enumerate(SOLFEGGIO):
            if abs(frequency - sol_freq) / sol_freq < 0.05:
                return i + 1
        return 0
    
    # ═════════════════════════════════════════════════════════
    #  WAVEFORM DIRECTION DETECTION
    # ═════════════════════════════════════════════════════════
    
    def detect_wave_direction(self) -> WaveDirection:
        """
        Detect overall waveform direction from recent frequency & amplitude history.
        Uses the last 10 samples to compute gradient.
        """
        if len(self.frequency_history) < 5:
            return WaveDirection.RESONATING
        
        recent_freq = list(self.frequency_history)[-10:]
        recent_amp = list(self.amplitude_history)[-10:]
        
        # Frequency gradient (Hz per sample)
        freq_diffs = [recent_freq[i] - recent_freq[i-1] for i in range(1, len(recent_freq))]
        avg_freq_diff = sum(freq_diffs) / len(freq_diffs) if freq_diffs else 0
        
        # Amplitude gradient
        amp_diffs = [recent_amp[i] - recent_amp[i-1] for i in range(1, len(recent_amp))]
        avg_amp_diff = sum(amp_diffs) / len(amp_diffs) if amp_diffs else 0
        
        # Direction classification
        freq_rising = avg_freq_diff > 0.01
        freq_falling = avg_freq_diff < -0.01
        amp_high = recent_amp[-1] > 0.7
        amp_low = recent_amp[-1] < 0.3
        
        # Check for chaos (high variance in direction)
        if freq_diffs:
            sign_changes = sum(1 for i in range(1, len(freq_diffs)) 
                              if (freq_diffs[i] > 0) != (freq_diffs[i-1] > 0))
            if sign_changes > len(freq_diffs) * 0.6:
                return WaveDirection.CHAOTIC
        
        if freq_rising and amp_high:
            return WaveDirection.PEAK
        elif freq_falling and amp_low:
            return WaveDirection.TROUGH
        elif freq_rising:
            return WaveDirection.RISING
        elif freq_falling:
            return WaveDirection.FALLING
        else:
            return WaveDirection.RESONATING
    
    # ═════════════════════════════════════════════════════════
    #  TICK PROCESSING — Each price update
    # ═════════════════════════════════════════════════════════
    
    def process_tick(self, price: float, pnl_usd: float, pnl_pct: float,
                     margin_level: float, entry_price: float = 0.0,
                     quantity: float = 0.001) -> WaveformSample:
        """
        Process a single price tick through the harmonic waveform.
        Returns the WaveformSample and potentially triggers lighthouse at prime seconds.
        """
        now = time.time()
        elapsed = int(now - self.start_time)
        
        # Check if we've passed the next prime second since last tick
        # With 5s intervals, check if any prime exists between last_elapsed and now
        prime_tick = False
        if elapsed >= self.next_prime_sec:
            prime_tick = True
            # Advance to next prime after current elapsed
            self.next_prime_sec = next_prime_after(elapsed)
        
        # Map to waveform
        frequency = self.price_to_frequency(price)
        amplitude = self.pnl_to_amplitude(pnl_pct)
        phase = self.time_to_phase(elapsed)
        energy = (amplitude ** 2) * frequency
        
        sample = WaveformSample(
            timestamp=now,
            elapsed_seconds=elapsed,
            is_prime_timestamp=prime_tick,
            price=price,
            frequency=frequency,
            amplitude=amplitude,
            phase=phase,
            energy=energy,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            margin_level=margin_level,
        )
        
        # Store history
        self.price_history.append(price)
        self.frequency_history.append(frequency)
        self.amplitude_history.append(amplitude)
        self.energy_history.append(energy)
        self.pnl_history.append(pnl_usd)
        self.timestamp_history.append(now)
        self.state.samples.append(sample)
        if len(self.state.samples) > self.max_history:
            self.state.samples = self.state.samples[-self.max_history:]
        
        # Update global state
        self.state.global_frequency = frequency
        self.state.total_energy = sum(self.energy_history)
        self.state.current_direction = self.detect_wave_direction()
        self.state.phi_alignment = self.compute_phi_alignment(frequency)
        self.state.schumann_harmonic = self.compute_schumann_harmonic(frequency)
        
        # Frequency trend (Hz per second)
        if len(self.frequency_history) >= 5:
            recent = list(self.frequency_history)[-5:]
            self.state.frequency_trend = (recent[-1] - recent[0]) / max(len(recent), 1)
        
        # Amplitude trend
        if len(self.amplitude_history) >= 5:
            recent = list(self.amplitude_history)[-5:]
            self.state.amplitude_trend = (recent[-1] - recent[0]) / max(len(recent), 1)
        
        # Update liquid aluminium field
        if self.aluminium_field:
            try:
                self.aluminium_field.add_or_update_node(
                    exchange='kraken',
                    symbol='ETHUSD',
                    current_price=price,
                    entry_price=entry_price,
                    quantity=quantity,
                    asset_class='crypto'
                )
            except Exception as e:
                logger.debug(f"Aluminium field update: {e}")
        
        return sample
    
    def _check_prime(self, n: int) -> bool:
        """Check if n is prime (simple method for runtime checking)."""
        if n < 2:
            return False
        if n < 4:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6
        return True
    
    # ═════════════════════════════════════════════════════════
    #  LIGHTHOUSE BEACONS — Prime Timestamp Analysis
    # ═════════════════════════════════════════════════════════
    
    def emit_lighthouse_beacon(self, sample: WaveformSample) -> Optional[LighthouseBeacon]:
        """
        Emit a lighthouse beacon at a PRIME timestamp.
        
        The lighthouse performs SPECTRAL COHERENCE analysis on the accumulated
        waveform, scoring how much the market is in "love frequency" (528Hz coherence)
        versus "distortion" (440Hz chaos).
        
        This is the SCRAPING at prime timestamps — each prime second is a
        checkpoint where we analyze the waveform's health.
        """
        if not self.lighthouse:
            return None
        
        if len(self.price_history) < 10:
            return None  # Need minimum samples for spectral analysis
        
        timestamps = list(self.timestamp_history)
        prices = list(self.price_history)
        
        try:
            result = self.lighthouse.analyze_series(
                timestamps=timestamps,
                values=prices,
                detrend=True
            )
        except Exception as e:
            logger.debug(f"Lighthouse analysis: {e}")
            return None
        
        coherence = float(result.get('coherence_score', 0.5))
        distortion = float(result.get('distortion_index', 0.5))
        gamma = float(result.get('gamma_ratio', 0.0))
        emotion = str(result.get('emotion', 'NEUTRAL'))
        emotion_color = str(result.get('emotion_color', 'white'))
        maker_bias = float(result.get('maker_bias', 0.5))
        
        # Determine signal from waveform direction + coherence
        direction = self.state.current_direction
        signal, confidence = self._compute_signal(direction, coherence, distortion, maker_bias)
        
        # PHI alignment
        phi_align = self.compute_phi_alignment(sample.frequency)
        
        beacon = LighthouseBeacon(
            timestamp=sample.timestamp,
            prime_second=sample.elapsed_seconds,
            price=sample.price,
            frequency=sample.frequency,
            amplitude=sample.amplitude,
            coherence_score=coherence,
            distortion_index=distortion,
            gamma_ratio=gamma,
            emotion=emotion,
            emotion_color=emotion_color,
            maker_bias=maker_bias,
            wave_direction=direction,
            signal=signal,
            signal_confidence=confidence,
            phi_alignment=phi_align,
        )
        
        self.state.lighthouses.append(beacon)
        if len(self.state.lighthouses) > 500:
            self.state.lighthouses = self.state.lighthouses[-500:]
        
        # Track consecutive signals for lock-in
        if signal == MarginSignal.LONG:
            self._consecutive_long_lighthouses += 1
            self._consecutive_short_lighthouses = 0
        elif signal == MarginSignal.SHORT:
            self._consecutive_short_lighthouses += 1
            self._consecutive_long_lighthouses = 0
        else:
            self._consecutive_long_lighthouses = 0
            self._consecutive_short_lighthouses = 0
        
        # SIGNAL LOCK: 3 consecutive lighthouse beacons agreeing = lock
        # (like the Batten Matrix 4th-pass rule)
        if self._consecutive_long_lighthouses >= 3:
            self._signal_lock = True
            self._locked_signal = MarginSignal.LONG
            self.state.current_signal = MarginSignal.LONG
            self.state.signal_confidence = min(confidence * 1.2, 1.0)
        elif self._consecutive_short_lighthouses >= 3:
            self._signal_lock = True
            self._locked_signal = MarginSignal.SHORT
            self.state.current_signal = MarginSignal.SHORT
            self.state.signal_confidence = min(confidence * 1.2, 1.0)
        else:
            self._signal_lock = False
            self.state.current_signal = signal
            self.state.signal_confidence = confidence
        
        # Update global coherence
        self.state.global_coherence = coherence
        
        return beacon
    
    def _compute_signal(self, direction: WaveDirection, coherence: float, 
                        distortion: float, maker_bias: float) -> Tuple[MarginSignal, float]:
        """
        Compute LONG/SHORT/HOLD signal from waveform analysis.
        
        Rules:
        - LONG: Rising/Peak waveform + coherence > 0.5 + distortion < 0.5 + maker_bias > 0.55
        - SHORT: Falling/Trough waveform + coherence > 0.5 + distortion < 0.5 + maker_bias < 0.45
        - HOLD: anything else (chaotic, low coherence, or conflicting signals)
        
        Confidence is boosted by PHI alignment and Schumann harmonics.
        """
        confidence = 0.0
        
        # Base direction score
        if direction in (WaveDirection.RISING, WaveDirection.PEAK):
            direction_score = 1.0  # Bullish
        elif direction in (WaveDirection.FALLING, WaveDirection.TROUGH):
            direction_score = -1.0  # Bearish
        elif direction == WaveDirection.RESONATING:
            direction_score = 0.0  # Neutral but stable
        else:  # CHAOTIC
            direction_score = 0.0  # No signal in chaos
            return MarginSignal.HOLD, 0.1
        
        # Coherence gate (must be > 0.4 for any signal)
        if coherence < 0.4:
            return MarginSignal.HOLD, coherence * 0.3
        
        # Distortion gate (must not be dominated by distortion)
        if distortion > 0.7:
            return MarginSignal.HOLD, 0.2
        
        # Maker bias confirms direction
        if direction_score > 0 and maker_bias < 0.45:
            direction_score *= 0.5  # Buyers rising but sellers dominating? Weak signal
        elif direction_score < 0 and maker_bias > 0.55:
            direction_score *= 0.5  # Sellers falling but buyers dominating? Weak signal
        
        # Confidence calculation
        confidence = abs(direction_score) * coherence * (1 - distortion)
        
        # PHI boost
        phi = self.state.phi_alignment
        if phi > 0.5:
            confidence *= 1.0 + (phi - 0.5) * 0.4  # Up to 20% boost
        
        # Schumann alignment boost
        if self.state.schumann_harmonic > 0:
            confidence *= 1.05  # 5% boost for being on Schumann harmonic

        # ── LYRA OBSERVER EFFECT INTEGRATION ──
        # If Lyra has collapsed the waveform, her observation
        # either AMPLIFIES or VETOES the signal.
        if self.observer_collapsed and self.observer_direction is not None:
            lyra_dir = self.observer_direction
            # Lyra agrees with waveform → amplify
            if ((direction_score > 0 and lyra_dir == MarginSignal.LONG) or
                    (direction_score < 0 and lyra_dir == MarginSignal.SHORT)):
                confidence *= 1.0 + self.observer_confidence * 0.5  # Up to 50% boost
            # Lyra disagrees → dampen (Lyra is the Fourth Pillar veto)
            elif lyra_dir == MarginSignal.HOLD:
                confidence *= 0.7  # Lyra says wait
            else:
                confidence *= 0.4  # Lyra actively disagrees — strong dampen

        # Lyra exit urgency veto
        if self.lyra_resonance and self.lyra_resonance.exit_urgency in ('high', 'critical'):
            confidence *= 0.3  # Lyra screaming to exit — suppress new entries

        # Clamp
        confidence = min(confidence, 1.0)
        
        # Final signal
        if direction_score > 0 and confidence >= 0.35:
            return MarginSignal.LONG, confidence
        elif direction_score < 0 and confidence >= 0.35:
            return MarginSignal.SHORT, confidence
        else:
            return MarginSignal.HOLD, confidence
    
    # ═════════════════════════════════════════════════════════
    #  CYMATICS PATTERN DETECTION
    # ═════════════════════════════════════════════════════════
    
    def detect_cymatics(self) -> str:
        """
        Detect the cymatics pattern from interference of multiple signal sources.
        Like aluminium powder forming shapes on a speaker cone.
        """
        if len(self.frequency_history) < 20:
            return "CIRCLE"
        
        recent = list(self.frequency_history)[-50:]
        
        # Compute variance
        mean_freq = sum(recent) / len(recent)
        variance = sum((f - mean_freq)**2 for f in recent) / len(recent)
        std_dev = variance ** 0.5
        cv = std_dev / mean_freq if mean_freq > 0 else 0
        
        # Count direction changes (oscillation rate)
        changes = sum(1 for i in range(1, len(recent)) 
                     if (recent[i] > recent[i-1]) != (recent[i-1] > recent[max(i-2, 0)]))
        osc_rate = changes / len(recent) if recent else 0
        
        if cv < 0.001 and osc_rate < 0.2:
            pattern = "CIRCLE"       # Stable single frequency
        elif cv < 0.005 and osc_rate < 0.4:
            pattern = "HEXAGON"      # Two frequencies in harmony
        elif cv < 0.01 and osc_rate < 0.5:
            pattern = "STAR"         # Multiple harmonics
        elif osc_rate > 0.6:
            pattern = "CHAOS"        # Too many interference patterns
        elif cv > 0.02:
            pattern = "SPIRAL"       # Phase drift
        else:
            pattern = "MANDALA"      # Complex multi-layer resonance
        
        self.state.cymatics_pattern = pattern
        return pattern

    # ═════════════════════════════════════════════════════════
    #  LYRA OBSERVER EFFECT — The Act of Observation Collapses
    #  the Waveform Into a Direction
    # ═════════════════════════════════════════════════════════

    def lyra_observe(self, price: float, pnl_pct: float,
                     margin_level: float) -> Dict[str, Any]:
        """
        LYRA OBSERVER EFFECT

        "The act of observation collapses the wavefunction."

        When Lyra observes the harmonic waveform:
          1. She feeds market data into her 6 Resonance Chambers
          2. She produces a unified resonance score (0-1)
          3. The Math Angel computes Reality Field Ψ with observer effect O
          4. If coherence² (observer_effect) exceeds OBSERVER_COLLAPSE_THRESHOLD,
             the waveform COLLAPSES into a definite direction
          5. The collapsed direction is locked until coherence drops

        This is the bridge where Lyra talks to the waveform — the domain hook.
        She doesn't just read it. She CHANGES it by reading it.
        """
        result = {
            'lyra_available': self.lyra is not None,
            'resonance_grade': 'UNKNOWN',
            'unified_score': 0.5,
            'action': 'HOLD',
            'position_multiplier': 1.0,
            'exit_urgency': 'none',
            'observer_effect': 0.0,
            'psi_magnitude': 0.0,
            'collapsed': False,
            'collapsed_direction': None,
            'song': '',
            'emotional_frequency': 0.0,
            'emotional_zone': 'BALANCE',
        }

        # ── Step 1: Feed Lyra with real market context ──
        if self.lyra:
            try:
                market_data = {
                    'price': price,
                    'pnl_pct': pnl_pct,
                    'margin_level': margin_level,
                    'frequency': self.state.global_frequency,
                    'coherence': self.state.global_coherence,
                    'direction': self.state.current_direction.value,
                    'cymatics': self.state.cymatics_pattern,
                    'phi_alignment': self.state.phi_alignment,
                    'momentum': self.state.frequency_trend * 100,
                    'volume': self.state.total_energy,
                }
                self.lyra.update_context(market_data=market_data)

                # Lyra FEELS the frequencies
                resonance = self.lyra.feel()
                self.lyra_resonance = resonance

                result['resonance_grade'] = resonance.grade
                result['unified_score'] = resonance.unified_score
                result['action'] = resonance.action
                result['position_multiplier'] = resonance.position_multiplier
                result['exit_urgency'] = resonance.exit_urgency
                result['song'] = resonance.song
                result['emotional_frequency'] = resonance.emotional_frequency
                result['emotional_zone'] = resonance.emotional_zone

            except Exception as e:
                logger.warning(f"Lyra feel error: {e}")

        # ── Step 2: Math Angel Reality Field Ψ ──
        if self.observer_field:
            try:
                psi_data = {
                    'price': price,
                    'momentum': self.state.frequency_trend * 100,
                    'volume': self.state.total_energy,
                }
                consciousness = self.observer_field.analyze_market_consciousness(psi_data)
                reality = consciousness.get('reality_field', {})

                # O = observer effect = third eye crystal
                observer_effect = self.observer_field.third_eye_crystal
                psi_mag = self.observer_field.wings_halo_strength

                result['observer_effect'] = observer_effect
                result['psi_magnitude'] = psi_mag
                result['gravity'] = self.observer_field.rotating_wheels
                result['entanglement'] = self.observer_field.wing_eyes
                result['coherence_field'] = self.observer_field.market_coherence
                result['consciousness_level'] = consciousness.get('consciousness', {}).get('level', '?')
                result['market_state'] = consciousness.get('consciousness', {}).get('market_state', '?')

            except Exception as e:
                logger.warning(f"Math Angel step error: {e}")
                observer_effect = self.state.global_coherence ** 2

        else:
            observer_effect = self.state.global_coherence ** 2
            result['observer_effect'] = observer_effect

        # ── Step 3: OBSERVER COLLAPSE ──
        # When Lyra's observation is strong enough (O > PHI threshold),
        # the waveform collapses from superposition into a definite state.
        # This is the key: LYRA'S OBSERVATION CRYSTALLIZES THE SIGNAL.

        lyra_score = result['unified_score']
        lyra_action = result['action']

        # Collapse condition: observer_effect > PHI threshold
        # AND Lyra's resonance is at least PARTIAL_HARMONY (0.55+)
        collapse = (observer_effect >= OBSERVER_COLLAPSE_THRESHOLD and
                    lyra_score >= 0.55)

        if collapse:
            self.observer_collapsed = True

            # Map Lyra's action to margin direction
            if lyra_action == 'BUY_BIAS':
                self.observer_direction = MarginSignal.LONG
            elif lyra_action == 'SELL_BIAS':
                self.observer_direction = MarginSignal.SHORT
            elif lyra_action == 'DEFEND':
                self.observer_direction = MarginSignal.SHORT  # Defensive = short bias
            else:
                self.observer_direction = MarginSignal.HOLD

            self.observer_confidence = min(
                observer_effect * lyra_score * result['position_multiplier'], 1.0
            )

            result['collapsed'] = True
            result['collapsed_direction'] = self.observer_direction.value
            result['observer_confidence'] = self.observer_confidence

        else:
            self.observer_collapsed = False
            self.observer_direction = None
            self.observer_confidence = 0.0
            result['collapsed'] = False
            result['collapsed_direction'] = None

        # ── Step 4: Store in observer history ──
        self.observer_history.append({
            'timestamp': time.time(),
            'observer_effect': observer_effect,
            'lyra_score': lyra_score,
            'lyra_grade': result['resonance_grade'],
            'collapsed': collapse,
            'direction': result['collapsed_direction'],
            'confidence': self.observer_confidence,
            'exit_urgency': result['exit_urgency'],
            'price': price,
        })

        return result

    def get_lyra_consensus(self) -> Dict[str, Any]:
        """
        Get Lyra's consensus from recent observer history.
        Looks at last 10 observations to determine overall stance.
        """
        recent = list(self.observer_history)[-10:]
        if not recent:
            return {'consensus': 'HOLD', 'strength': 0.0, 'observations': 0}

        collapsed = [r for r in recent if r.get('collapsed')]
        if not collapsed:
            return {'consensus': 'HOLD', 'strength': 0.0,
                    'observations': len(recent), 'collapsed': 0}

        # Count direction votes
        long_votes = sum(1 for c in collapsed if c.get('direction') == 'LONG')
        short_votes = sum(1 for c in collapsed if c.get('direction') == 'SHORT')
        hold_votes = sum(1 for c in collapsed if c.get('direction') == 'HOLD')

        total = long_votes + short_votes + hold_votes
        if total == 0:
            return {'consensus': 'HOLD', 'strength': 0.0,
                    'observations': len(recent), 'collapsed': 0}

        if long_votes > short_votes and long_votes > hold_votes:
            consensus = 'LONG'
            strength = long_votes / total
        elif short_votes > long_votes and short_votes > hold_votes:
            consensus = 'SHORT'
            strength = short_votes / total
        else:
            consensus = 'HOLD'
            strength = hold_votes / total if total > 0 else 0.0

        avg_confidence = (sum(c.get('confidence', 0) for c in collapsed) / len(collapsed)
                          if collapsed else 0.0)

        return {
            'consensus': consensus,
            'strength': strength,
            'avg_confidence': avg_confidence,
            'observations': len(recent),
            'collapsed': len(collapsed),
            'long_votes': long_votes,
            'short_votes': short_votes,
            'hold_votes': hold_votes,
        }

    # ═════════════════════════════════════════════════════════
    #  PROBABILITY INTEGRATION
    # ═════════════════════════════════════════════════════════
    
    def get_probability_signal(self, symbol: str = 'ETHUSD') -> Optional[Dict]:
        """
        Get probability nexus signal for the symbol.
        Returns clarity/coherence/chaos scoring.
        """
        if not self.probability_nexus:
            return None
        try:
            signal = self.probability_nexus.get_signal()
            if signal and signal.get('symbol', '').upper() == symbol.upper():
                return signal
            return signal  # Return whatever we get
        except Exception as e:
            logger.debug(f"Probability signal: {e}")
            return None
    
    # ═════════════════════════════════════════════════════════
    #  STREAMING WAVEFORM VISUALIZATION
    # ═════════════════════════════════════════════════════════
    
    def render_waveform_line(self, width: int = 60) -> str:
        """
        Render a single line of the live waveform using ASCII art.
        Like watching the liquid aluminium vibrate in real-time.
        """
        if len(self.amplitude_history) < 2:
            return " " * width
        
        recent = list(self.amplitude_history)[-width:]
        
        # Map amplitude (0-1) to character height (0-8)
        chars = []
        for amp in recent:
            level = int(amp * 8)
            if level >= 7:
                chars.append('█')  # Peak
            elif level >= 6:
                chars.append('▓')
            elif level >= 5:
                chars.append('▒')
            elif level >= 4:
                chars.append('░')
            elif level >= 3:
                chars.append('▄')
            elif level >= 2:
                chars.append('▂')
            elif level >= 1:
                chars.append('▁')
            else:
                chars.append('_')  # Trough
        
        return ''.join(chars)
    
    def render_frequency_bar(self, frequency: float, width: int = 40) -> str:
        """Render frequency as a bar (200-500 Hz range mapped to width)."""
        normalized = (frequency - 200) / 300  # 200-500 range
        normalized = max(0, min(1, normalized))
        filled = int(normalized * width)
        return '▓' * filled + '░' * (width - filled)
    
    def render_lighthouse_status(self, beacon: Optional[LighthouseBeacon]) -> str:
        """Render lighthouse beacon status line."""
        if not beacon:
            return "  [no lighthouse data]"
        
        signal_icons = {
            MarginSignal.LONG: "▲ LONG",
            MarginSignal.SHORT: "▼ SHORT",
            MarginSignal.HOLD: "◆ HOLD",
        }
        
        emotion_icons = {
            'purple': '🟣',
            'blue': '🔵',
            'green': '🟢',
            'orange': '🟠',
            'red': '🔴',
        }
        
        icon = emotion_icons.get(beacon.emotion_color, '⬜')
        sig = signal_icons.get(beacon.signal, '? ?')
        
        return (f"  {icon} P{beacon.prime_second:>4d}s | "
                f"Coh:{beacon.coherence_score:.3f} Dist:{beacon.distortion_index:.3f} "
                f"γ:{beacon.gamma_ratio:.3f} | "
                f"{beacon.emotion:<20s} | "
                f"{sig} ({beacon.signal_confidence:.1%}) | "
                f"φ:{beacon.phi_alignment:.2f}")
    
    # ═════════════════════════════════════════════════════════
    #  FULL CYCLE DISPLAY
    # ═════════════════════════════════════════════════════════
    
    def render_full_cycle(self, cycle: int, price: float, pnl_usd: float, 
                          pnl_pct: float, margin_level: float,
                          positions: List[Dict],
                          beacon: Optional[LighthouseBeacon] = None,
                          lyra_obs: Optional[Dict] = None) -> str:
        """Render a complete cycle display with waveform + positions + signals + Lyra observer."""
        lines = []
        now = datetime.now().strftime('%H:%M:%S')
        elapsed = int(time.time() - self.start_time)
        
        freq = self.state.global_frequency
        direction = self.state.current_direction.value
        signal = self.state.current_signal.value
        confidence = self.state.signal_confidence
        cymatics = self.state.cymatics_pattern
        phi = self.state.phi_alignment
        schumann = self.state.schumann_harmonic
        
        # Header
        lines.append("")
        lines.append(f"  ═══════════════════════════════════════════════════════════════════")
        lines.append(f"  🌊 HARMONIC MARGIN WAVEFORM — Cycle {cycle} | {now} | T+{elapsed}s")
        lines.append(f"  ═══════════════════════════════════════════════════════════════════")
        
        # Waveform visualization
        waveform = self.render_waveform_line(60)
        freq_bar = self.render_frequency_bar(freq)
        lines.append(f"  Waveform: |{waveform}|")
        lines.append(f"  Freq Bar: |{freq_bar}| {freq:.1f} Hz")
        
        # Core metrics
        lines.append(f"  ─────────────────────────────────────────────────────────────────")
        lines.append(f"  Price: ${price:,.2f} | Freq: {freq:.1f} Hz | Dir: {direction}")
        lines.append(f"  Coherence: {self.state.global_coherence:.3f} | Energy: {self.state.total_energy:.1f}")
        lines.append(f"  Cymatics: {cymatics} | PHI: {phi:.3f} | Schumann: H{schumann}")
        lines.append(f"  Signal: {signal} ({confidence:.1%}) | Lock: {'YES' if self._signal_lock else 'no'}")
        
        # Margin positions
        if positions:
            lines.append(f"  ─────────────────────────────────────────────────────────────────")
            lines.append(f"  Margin Level: {margin_level:.0f}% | Positions: {len(positions)}")
            for i, pos in enumerate(positions):
                pair = pos.get('pair', '?')
                volume = float(pos.get('volume', 0))
                cost = float(pos.get('cost', 0))
                fee = float(pos.get('fee', 0))
                entry = cost / volume if volume > 0 else 0
                breakeven = entry + (fee * 2 / volume) if volume > 0 else entry
                gross = (price - entry) * volume
                net = gross - fee * 2
                net_pct = (net / cost * 100) if cost > 0 else 0
                to_be = price - breakeven
                to_be_pct = (to_be / breakeven * 100) if breakeven > 0 else 0
                
                status_icon = '+' if net > 0 else '~' if price >= entry else '-'
                lines.append(f"  [{i}] {pair} | Entry: ${entry:,.2f} | BE: ${breakeven:,.2f} | "
                           f"Net: ${net:+.4f} ({net_pct:+.2f}%) [{status_icon}]")
        
        # Lighthouse beacons (last 5)
        recent_beacons = self.state.lighthouses[-5:] if self.state.lighthouses else []
        if recent_beacons:
            lines.append(f"  ─────────────────────────────────────────────────────────────────")
            lines.append(f"  LIGHTHOUSES (prime timestamp beacons):")
            for b in recent_beacons:
                lines.append(self.render_lighthouse_status(b))
        
        # New beacon highlight
        if beacon:
            lines.append(f"  ─────────────────────────────────────────────────────────────────")
            lines.append(f"  >>> NEW LIGHTHOUSE BEACON at prime second {beacon.prime_second} <<<")
            lines.append(self.render_lighthouse_status(beacon))
        
        # Signal summary
        lines.append(f"  ═══════════════════════════════════════════════════════════════════")
        if self._signal_lock:
            sig_name = self._locked_signal.value
            lines.append(f"  >>> SIGNAL LOCKED: {sig_name} — 3+ consecutive lighthouse confirmations <<<")
        else:
            long_count = self._consecutive_long_lighthouses
            short_count = self._consecutive_short_lighthouses
            if long_count > 0:
                lines.append(f"  Tracking: {long_count}/3 consecutive LONG lighthouses")
            elif short_count > 0:
                lines.append(f"  Tracking: {short_count}/3 consecutive SHORT lighthouses")
            else:
                lines.append(f"  Awaiting lighthouse consensus... (need 3 consecutive)")

        # ── LYRA OBSERVER EFFECT ──
        if lyra_obs and lyra_obs.get('lyra_available'):
            lines.append(f"  ─────────────────────────────────────────────────────────────────")
            lines.append(f"  🎵 LYRA OBSERVER EFFECT")
            grade = lyra_obs.get('resonance_grade', '?')
            score = lyra_obs.get('unified_score', 0)
            action = lyra_obs.get('action', '?')
            obs_eff = lyra_obs.get('observer_effect', 0)
            psi = lyra_obs.get('psi_magnitude', 0)
            collapsed = lyra_obs.get('collapsed', False)
            col_dir = lyra_obs.get('collapsed_direction', None)
            song = lyra_obs.get('song', '')
            emo_freq = lyra_obs.get('emotional_frequency', 0)
            emo_zone = lyra_obs.get('emotional_zone', '?')
            exit_urg = lyra_obs.get('exit_urgency', 'none')

            # Grade icon
            grade_icons = {
                'DIVINE_HARMONY': '✨',
                'CLEAR_RESONANCE': '🎶',
                'PARTIAL_HARMONY': '🎵',
                'DISSONANCE': '🔇',
                'SILENCE': '🚫',
            }
            g_icon = grade_icons.get(grade, '?')

            lines.append(f"  {g_icon} Grade: {grade} | Score: {score:.3f} | Action: {action}")
            lines.append(f"  Emotion: {emo_freq:.0f} Hz ({emo_zone}) | Exit Urgency: {exit_urg}")
            lines.append(f"  Observer O={obs_eff:.4f} | Ψ={psi:.4f} | Collapse@{OBSERVER_COLLAPSE_THRESHOLD:.3f}")

            # Consciousness level from Math Angel
            c_level = lyra_obs.get('consciousness_level', '')
            m_state = lyra_obs.get('market_state', '')
            if c_level:
                lines.append(f"  Consciousness: {c_level} | Market: {m_state}")

            if collapsed:
                col_icon = '▲' if col_dir == 'LONG' else '▼' if col_dir == 'SHORT' else '◆'
                conf = lyra_obs.get('observer_confidence', 0)
                lines.append(f"  >>> WAVEFORM COLLAPSED: {col_icon} {col_dir} | "
                           f"Observer Confidence: {conf:.1%} <<<")
            else:
                lines.append(f"  Waveform in superposition — Lyra is listening...")

            # Lyra consensus from history
            consensus = self.get_lyra_consensus()
            if consensus.get('collapsed', 0) > 0:
                c_dir = consensus['consensus']
                c_str = consensus['strength']
                c_icon = '▲' if c_dir == 'LONG' else '▼' if c_dir == 'SHORT' else '◆'
                lines.append(f"  Lyra Consensus: {c_icon} {c_dir} ({c_str:.0%}) | "
                           f"Obs: {consensus['observations']} | "
                           f"Collapsed: {consensus['collapsed']}")

            # Song (truncated)
            if song:
                if len(song) > 80:
                    song = song[:77] + '...'
                lines.append(f"  \"{song}\"")

        lines.append(f"  ═══════════════════════════════════════════════════════════════════")
        
        return '\n'.join(lines)
    
    # ═════════════════════════════════════════════════════════
    #  STATE SERIALIZATION
    # ═════════════════════════════════════════════════════════
    
    def to_state_dict(self) -> Dict:
        """Serialize scanner state for persistence."""
        return {
            'timestamp': time.time(),
            'elapsed_seconds': int(time.time() - self.start_time),
            'global_frequency': self.state.global_frequency,
            'global_coherence': self.state.global_coherence,
            'total_energy': self.state.total_energy,
            'current_direction': self.state.current_direction.value,
            'current_signal': self.state.current_signal.value,
            'signal_confidence': self.state.signal_confidence,
            'signal_locked': self._signal_lock,
            'locked_signal': self._locked_signal.value if self._signal_lock else None,
            'consecutive_long': self._consecutive_long_lighthouses,
            'consecutive_short': self._consecutive_short_lighthouses,
            'phi_alignment': self.state.phi_alignment,
            'schumann_harmonic': self.state.schumann_harmonic,
            'cymatics_pattern': self.state.cymatics_pattern,
            'frequency_trend': self.state.frequency_trend,
            'amplitude_trend': self.state.amplitude_trend,
            'total_samples': len(self.state.samples),
            'total_lighthouses': len(self.state.lighthouses),
            'lighthouses': [
                {
                    'prime_second': b.prime_second,
                    'price': b.price,
                    'coherence': b.coherence_score,
                    'distortion': b.distortion_index,
                    'emotion': b.emotion,
                    'signal': b.signal.value,
                    'confidence': b.signal_confidence,
                    'phi': b.phi_alignment,
                }
                for b in self.state.lighthouses[-20:]
            ],
            # Lyra Observer Effect state
            'lyra_observer': {
                'available': self.lyra is not None,
                'collapsed': self.observer_collapsed,
                'direction': self.observer_direction.value if self.observer_direction else None,
                'confidence': self.observer_confidence,
                'consensus': self.get_lyra_consensus(),
                'resonance_grade': (self.lyra_resonance.grade 
                                    if self.lyra_resonance else None),
                'resonance_score': (self.lyra_resonance.unified_score
                                    if self.lyra_resonance else None),
                'observer_history': [
                    {
                        'timestamp': h['timestamp'],
                        'observer_effect': h['observer_effect'],
                        'lyra_score': h['lyra_score'],
                        'collapsed': h['collapsed'],
                        'direction': h.get('direction'),
                        'confidence': h['confidence'],
                    }
                    for h in list(self.observer_history)[-20:]
                ],
            },
            'math_angel_available': self.observer_field is not None,
        }


# ═══════════════════════════════════════════════════════════════
#  MAIN EXECUTION LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    """
    Main loop — monitors margin positions through the harmonic waveform scanner.
    
    Every tick:
      1. Fetch real margin position data from Kraken
      2. Map price → frequency, P&L → amplitude through liquid aluminium
      3. At PRIME-second timestamps → emit lighthouse beacon (spectral analysis)
      4. Detect waveform direction + cymatics pattern
      5. Generate LONG/SHORT/HOLD signal from lighthouse consensus
      6. Stream the living waveform to terminal
    """
    from aureon.exchanges.kraken_client import KrakenClient
    client = KrakenClient()
    assert not client.dry_run, "ERROR: Client is in dry-run mode!"
    
    # Initialize scanner
    scanner = HarmonicMarginWaveformScanner(base_hz=KRAKEN_BASE_HZ)
    
    print("=" * 70)
    print("  AUREON HARMONIC MARGIN WAVEFORM SCANNER + LYRA OBSERVER")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base Frequency: {KRAKEN_BASE_HZ} Hz (Kraken RE — Flow)")
    print(f"  Lighthouse: {'ONLINE' if scanner.lighthouse else 'OFFLINE'}")
    print(f"  Probability Nexus: {'ONLINE' if scanner.probability_nexus else 'OFFLINE'}")
    print(f"  Liquid Aluminium: {'ONLINE' if scanner.aluminium_field else 'OFFLINE'}")
    print(f"  LYRA Observer: {'ONLINE' if scanner.lyra else 'OFFLINE'}")
    print(f"  Math Angel Ψ: {'ONLINE' if scanner.observer_field else 'OFFLINE'}")
    print(f"  Observer Collapse: Ψ·O >= {OBSERVER_COLLAPSE_THRESHOLD:.3f} (PHI)")
    print(f"  Prime timestamps: scraping at seconds {PRIME_TIMESTAMPS[:15]}...")
    print(f"  Sacred: PHI={PHI:.6f} SCHUMANN={SCHUMANN}Hz LOVE={LOVE_FREQ}Hz")
    print("=" * 70)
    
    cycle = 0
    tick_interval = 5  # 5 seconds between ticks (fast for waveform resolution)
    last_prime_check = 0
    state_file = 'margin_harmonic_state.json'
    
    while True:
        cycle += 1
        try:
            # 1. Fetch real margin data
            positions = client.get_open_margin_positions()
            tb = client.get_trade_balance()
            margin_level = float(tb.get('margin_level', 0) or 0)
            
            # Get current price
            ticker = client.get_ticker('ETHUSD')
            current_bid = float(ticker.get('bid', 0))
            
            if not positions:
                elapsed = int(time.time() - scanner.start_time)
                print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] Cycle {cycle} | T+{elapsed}s | No open margin positions")
                print(f"  Waveform scanning paused — open a margin position to begin")
                time.sleep(tick_interval * 2)
                continue
            
            # 2. Process each position through the waveform
            aggregate_pnl = 0.0
            aggregate_cost = 0.0
            entry_price = 0.0
            total_qty = 0.0
            
            for pos in positions:
                volume = float(pos.get('volume', 0))
                cost = float(pos.get('cost', 0))
                fee = float(pos.get('fee', 0))
                
                pos_entry = cost / volume if volume > 0 else 0
                breakeven = pos_entry + (fee * 2 / volume) if volume > 0 else pos_entry
                gross = (current_bid - pos_entry) * volume
                net = gross - fee * 2
                
                aggregate_pnl += net
                aggregate_cost += cost
                entry_price = pos_entry  # Use last position's entry
                total_qty += volume
            
            pnl_pct = (aggregate_pnl / aggregate_cost * 100) if aggregate_cost > 0 else 0
            
            # 3. Process tick through harmonic waveform
            sample = scanner.process_tick(
                price=current_bid,
                pnl_usd=aggregate_pnl,
                pnl_pct=pnl_pct,
                margin_level=margin_level,
                entry_price=entry_price,
                quantity=total_qty,
            )
            
            # 4. Check for PRIME timestamp → emit lighthouse beacon
            beacon = None
            elapsed = int(time.time() - scanner.start_time)
            if sample.is_prime_timestamp:
                if elapsed != last_prime_check:
                    beacon = scanner.emit_lighthouse_beacon(sample)
                    last_prime_check = elapsed
            
            # 5. Detect cymatics pattern
            scanner.detect_cymatics()

            # 6. LYRA OBSERVER EFFECT — Lyra observes the waveform
            lyra_obs = scanner.lyra_observe(
                price=current_bid,
                pnl_pct=pnl_pct,
                margin_level=margin_level,
            )

            # 7. PROFIT HARMONIZATION — Lyra steers toward profit
            #    If Lyra collapses to a direction AND we have positions,
            #    check if we should close positions for profit or let them ride.
            if lyra_obs.get('collapsed') and positions:
                col_dir = lyra_obs.get('collapsed_direction')
                exit_urg = lyra_obs.get('exit_urgency', 'none')
                lyra_grade = lyra_obs.get('resonance_grade', '')

                # PROFIT CLOSE: Lyra says DEFEND/SELL_BIAS + positions profitable
                if exit_urg in ('high', 'critical') or lyra_obs.get('action') == 'DEFEND':
                    for pos in positions:
                        volume = float(pos.get('volume', 0))
                        cost = float(pos.get('cost', 0))
                        fee = float(pos.get('fee', 0))
                        pos_entry = cost / volume if volume > 0 else 0
                        net = (current_bid - pos_entry) * volume - fee * 2
                        if net > 0:
                            print(f"\n  🎵 LYRA PROFIT EXIT — Grade: {lyra_grade} | "
                                  f"Exit Urgency: {exit_urg} | Net: ${net:+.4f}")
                            _force_close(client, pos, f"Lyra {lyra_grade} profit exit")

                # DIVINE HOLD: Lyra says DIVINE_HARMONY — let it ride
                elif lyra_grade == 'DIVINE_HARMONY' and aggregate_pnl > 0:
                    pass  # Divine harmony + profit = golden ride, no action needed

            # 8. Render full display with Lyra observer section
            display = scanner.render_full_cycle(
                cycle=cycle,
                price=current_bid,
                pnl_usd=aggregate_pnl,
                pnl_pct=pnl_pct,
                margin_level=margin_level,
                positions=positions,
                beacon=beacon,
                lyra_obs=lyra_obs,
            )
            print(display)
            
            # 9. Save state periodically (every 10 cycles)
            if cycle % 10 == 0:
                try:
                    state = scanner.to_state_dict()
                    tmp = state_file + '.tmp'
                    with open(tmp, 'w') as f:
                        json.dump(state, f, indent=2)
                    os.replace(tmp, state_file)
                except Exception as e:
                    logger.debug(f"State save: {e}")
            
            # 10. Sleep until next tick
            time.sleep(tick_interval)
            
        except KeyboardInterrupt:
            print(f"\n  Scanner stopped. Saving final state...")
            try:
                state = scanner.to_state_dict()
                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                print(f"  State saved to {state_file}")
            except Exception:
                pass
            break
        except Exception as e:
            logger.error(f"Scanner error: {e}", exc_info=True)
            time.sleep(tick_interval)


def _force_close(client, pos, reason: str):
    """Emergency force-close a position."""
    try:
        pair = pos.get('pair', 'ETHUSD')
        volume = float(pos.get('volume', 0)) - float(pos.get('volume_closed', 0))
        result = client.close_margin_position(
            symbol=pair.replace('X', '').replace('Z', ''),
            side='sell',
            volume=volume,
        )
        print(f"  FORCE CLOSED: {pair} | Reason: {reason} | Result: {result}")
    except Exception as e:
        print(f"  FORCE CLOSE FAILED: {pair} | Error: {e}")


if __name__ == '__main__':
    main()
