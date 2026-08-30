#!/usr/bin/env python3
"""
🌊🎶 AUREON HARMONIC NEXUS CORE (HNC) - SURGE DETECTOR 🎶🌊
═══════════════════════════════════════════════════════════════════════════════
"The universe is a symphony of vibrating strings." - String Theory

This module implements the Harmonic Nexus Core theory to identify "Surge Windows"
for optimal trading. HNC theory posits that markets, like all systems, exhibit
resonant frequencies. When these frequencies align, they create constructive
interference, leading to high-energy "surge events" of increased volatility and
predictable movement.

HNC THEORY PRINCIPLES:
  1.  **Universal Harmonics**: The market is influenced by a set of universal,
      sacred frequencies (Schumann, Solfeggio, etc.).
  2.  **Harmonic Stacking**: These base frequencies and their harmonics (based on
      the Golden Ratio φ and Prime Numbers) stack up.
  3.  **Constructive Interference**: When enough harmonics align, they create a
      "Resonance Cascade" - a surge in market energy.
  4.  **Surge Windows**: These cascades are predictable, temporary windows of
      high opportunity. We trade the surge, not the noise.

This system listens for the market's symphony and tells us when the crescendo
is about to hit.

Gary Leckey | January 2026 | "Listen to the market's song."
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import io
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import deque

# ═══════════════════════════════════════════════════════════════════════════════
# 👑💰 QUEEN'S SACRED 1.88% LAW - SURGE = PROFIT! 💰👑
# ═══════════════════════════════════════════════════════════════════════════════
#
#   THE QUEEN COMMANDS: MIN_COP = 1.0188 (1.88% MINIMUM REALIZED PROFIT)
#   Only trade surges that can achieve 1.88%!
#
# ═══════════════════════════════════════════════════════════════════════════════

QUEEN_MIN_COP = 1.0188               # 👑 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88          # 👑 The sacred number as percentage
QUEEN_SURGE_MIN_STRENGTH = 0.60      # 👑 Minimum surge strength for profit potential

# ═══════════════════════════════════════════════════════════════════════════════
# 🎶 HNC SACRED CONSTANTS & FREQUENCIES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Harmonic:
    name: str
    frequency_hz: float
    influence: float  # How much this harmonic contributes to the resonance score
    category: str

# --- Foundational Universal Frequencies ---
SACRED_HARMONICS = [
    # Earth's "heartbeat" - the fundamental market rhythm
    Harmonic("Schumann Resonance", 7.83, 1.0, "Geophysical"),
    
    # 👑 Queen's Profit Frequency - THE SACRED 1.88!
    Harmonic("Queen's Profit", 188.0, 1.0, "Sacred"),  # NEW!
    
    # Solfeggio Frequencies - ancient tones of creation and transformation
    Harmonic("UT - Liberating Guilt", 396.0, 0.5, "Solfeggio"),
    Harmonic("RE - Facilitating Change", 417.0, 0.5, "Solfeggio"),
    Harmonic("MI - Transformation & Miracles", 528.0, 0.8, "Solfeggio"), # The "love" frequency
    Harmonic("FA - Connecting Relationships", 639.0, 0.6, "Solfeggio"),
    Harmonic("SOL - Awakening Intuition", 741.0, 0.7, "Solfeggio"),
    Harmonic("LA - Returning to Spirit", 852.0, 0.6, "Solfeggio"),

    # Planetary Harmonics
    Harmonic("Sun", 126.22, 0.4, "Planetary"),
    Harmonic("Moon", 210.42, 0.3, "Planetary"),
    Harmonic("Earth Day", 194.18, 0.4, "Planetary"),
]

# --- Harmonic Modulators ---
PHI = (1 + math.sqrt(5)) / 2  # 1.618... Golden Ratio, for harmonic progression
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19] # For creating complex overtones

# ═══════════════════════════════════════════════════════════════════════════════
# 🌊 HNC DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedFrequency:
    """A frequency component detected in the market data stream."""
    frequency_hz: float
    amplitude: float # Normalized amplitude (0-1)
    phase: float

@dataclass
class ResonanceEvent:
    """When a detected frequency aligns with a sacred harmonic."""
    detected_freq: DetectedFrequency
    sacred_harmonic: Harmonic
    harmonic_multiple: float # e.g., 1.0 for fundamental, 2.0 for octave
    proximity: float # How close the match is (1.0 = perfect)
    resonance_score: float = 0.0

    def __post_init__(self):
        # Score is based on harmonic's influence, match proximity, and amplitude
        self.resonance_score = (
            self.sacred_harmonic.influence *
            self.proximity *
            self.detected_freq.amplitude
        )

@dataclass
class SurgeWindow:
    """A predicted window of high market energy and opportunity."""
    symbol: str
    start_time: float
    end_time: float
    peak_time: float
    intensity: float # Overall resonance score (0-1)
    primary_harmonic: str # The dominant sacred harmonic in the surge
    contributing_events: List[ResonanceEvent] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def is_active(self) -> bool:
        now = time.time()
        return self.start_time <= now < self.end_time

# ═══════════════════════════════════════════════════════════════════════════════
# 🔬 HNC SURGE DETECTOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class HncSurgeDetector:
    """
    Listens to the market's song to predict high-energy surge windows.
    """
    def __init__(self, sample_rate: int = 100, analysis_window_size: int = 1024):
        self.sample_rate = sample_rate  # Hz (e.g., 100 samples per second)
        self.analysis_window_size = analysis_window_size # Number of samples for FFT
        
        # Data buffers for analysis
        self.price_history: Dict[str, deque] = {}
        
        # Configuration
        self.resonance_threshold = 1.5 # Minimum cumulative score to trigger a surge
        self.frequency_tolerance = 0.02 # 2% tolerance for matching harmonics
        
        print("🌊🎶 HNC Surge Detector Initialized 🎶🌊")
        print(f"   Resonance Threshold: {self.resonance_threshold}")
        print(f"   Analysis Window: {self.analysis_window_size / self.sample_rate:.2f}s")

    def _get_or_create_buffer(self, symbol: str) -> deque:
        """Get or create a data buffer for a given symbol."""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.analysis_window_size)
        return self.price_history[symbol]

    def add_price_tick(self, symbol: str, price: float):
        """Add a new price tick to the analysis buffer."""
        buffer = self._get_or_create_buffer(symbol)
        buffer.append(price)

    def _perform_fft_analysis(self, data: np.ndarray) -> List[DetectedFrequency]:
        """
        Perform Fast Fourier Transform to find dominant frequencies in the data.
        """
        if len(data) < self.analysis_window_size:
            return []

        # Apply a window function to reduce spectral leakage
        window = np.hanning(len(data))
        data = data * window

        # Perform FFT
        fft_result = np.fft.rfft(data)
        fft_freq = np.fft.rfftfreq(len(data), d=1./self.sample_rate)
        
        amplitudes = np.abs(fft_result)
        phases = np.angle(fft_result)

        # Normalize amplitudes
        if np.max(amplitudes) > 0:
            normalized_amplitudes = amplitudes / np.max(amplitudes)
        else:
            normalized_amplitudes = amplitudes

        detected_frequencies = []
        for i in range(len(fft_freq)):
            # Ignore DC component and very low amplitudes
            if fft_freq[i] > 0.1 and normalized_amplitudes[i] > 0.1:
                detected_frequencies.append(
                    DetectedFrequency(
                        frequency_hz=fft_freq[i],
                        amplitude=normalized_amplitudes[i],
                        phase=phases[i]
                    )
                )
        
        # Sort by amplitude to focus on dominant frequencies
        detected_frequencies.sort(key=lambda d: d.amplitude, reverse=True)
        return detected_frequencies

    def _find_resonance_events(self, detected_frequencies: List[DetectedFrequency]) -> List[ResonanceEvent]:
        """
        Compare detected frequencies against the sacred harmonics library.
        """
        events = []
        if not detected_frequencies:
            return events

        for det_freq in detected_frequencies[:20]: # Check top 20 dominant frequencies
            for sac_harm in SACRED_HARMONICS:
                # Check for matches with the base harmonic and its overtones
                # Overtones are created using Golden Ratio and Prime multipliers
                modulators = [1.0] + [PHI**i for i in range(1, 4)] + PRIMES
                
                for mod in modulators:
                    target_freq = sac_harm.frequency_hz * mod
                    
                    # Check if the detected frequency is close to the target
                    if abs(det_freq.frequency_hz - target_freq) / target_freq < self.frequency_tolerance:
                        proximity = 1.0 - (abs(det_freq.frequency_hz - target_freq) / (target_freq * self.frequency_tolerance))
                        
                        event = ResonanceEvent(
                            detected_freq=det_freq,
                            sacred_harmonic=sac_harm,
                            harmonic_multiple=mod,
                            proximity=proximity
                        )
                        events.append(event)
                        # Stop checking modulators for this detected frequency if a match is found
                        break 
        
        events.sort(key=lambda e: e.resonance_score, reverse=True)
        return events

    def detect_surge(self, symbol: str) -> Optional[SurgeWindow]:
        """
        Analyze the current market data for a symbol and detect if a surge is forming.
        """
        buffer = self._get_or_create_buffer(symbol)
        if len(buffer) < self.analysis_window_size:
            # Not enough data to perform analysis
            return None

        price_data = np.array(list(buffer))
        
        # 1. Find dominant frequencies in the price data
        detected_frequencies = self._perform_fft_analysis(price_data)
        
        # 2. Find resonance with sacred harmonics
        resonance_events = self._find_resonance_events(detected_frequencies)
        
        if not resonance_events:
            return None
            
        # 3. Calculate total resonance score
        total_resonance = sum(event.resonance_score for event in resonance_events)

        # 4. Check if a surge is triggered
        if total_resonance >= self.resonance_threshold:
            # A SURGE IS DETECTED! Now, define the window.
            
            # Find the dominant harmonic in the surge
            primary_event = resonance_events[0]
            
            # Estimate surge duration based on the primary harmonic's frequency
            # Lower frequencies = longer surges
            base_duration = (1 / primary_event.sacred_harmonic.frequency_hz) * PHI * 5
            surge_duration = max(5.0, min(base_duration, 300.0)) # Clamp between 5s and 5min
            
            now = time.time()
            start_time = now
            peak_time = now + (surge_duration / 2)
            end_time = now + surge_duration
            
            surge_window = SurgeWindow(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                peak_time=peak_time,
                intensity=min(1.0, total_resonance / (self.resonance_threshold * 2)), # Normalize
                primary_harmonic=primary_event.sacred_harmonic.name,
                contributing_events=resonance_events
            )
            return surge_window
            
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# 🎮 DEMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def run_hnc_demo():
    """Demonstrate the HNC Surge Detector in action.

    🟡 DEMO ONLY — uses np.random.randn for the base price walk and
    injects a synthetic harmonic blend. Do not call from production
    decision paths. Production uses HncSurgeDetector.add_price_tick()
    with real exchange ticks.
    """

    raise RuntimeError(
        "Generated HNC input has been retired. Feed provider-observed ticks "
        "to HncSurgeDetector.add_price_tick() with source provenance."
    )

    print("\n" + "="*80)
    print("🌊🎶 HNC SURGE DETECTOR - SYNTHETIC DEMO (DEV ONLY) 🎶🌊")
    print("="*80 + "\n")
    
    detector = HncSurgeDetector(sample_rate=100, analysis_window_size=1024)
    symbol = "BTC/USD"
    
    print(f"Simulating market data for {symbol}...")
    print("Listening for a Resonance Cascade...\n")
    
    # Simulate price data with embedded harmonics
    duration_seconds = 20
    sample_rate = detector.sample_rate
    num_samples = duration_seconds * sample_rate
    
    time_vector = np.linspace(0, duration_seconds, num_samples)
    
    # Base price movement (random walk)
    base_price = np.full(num_samples, np.nan)
    
    # --- Inject a Resonance Cascade halfway through ---
    surge_start_time = 10 # seconds
    surge_duration = 5 # seconds
    
    # Create a blend of sacred harmonics for the surge
    surge_signal = (
        # Schumann Resonance (fundamental)
        0.8 * np.sin(2 * np.pi * 7.83 * time_vector) +
        # 528 Hz (Love Frequency) - strong component
        1.0 * np.sin(2 * np.pi * 528 * time_vector) +
        # 528 * PHI (Golden Ratio overtone)
        0.5 * np.sin(2 * np.pi * 528 * PHI * time_vector) +
        # 396 Hz (Solfeggio)
        0.4 * np.sin(2 * np.pi * 396 * time_vector)
    )
    
    # Create a smooth window for the surge event
    surge_window_mask = np.zeros(num_samples)
    start_index = int(surge_start_time * sample_rate)
    end_index = int((surge_start_time + surge_duration) * sample_rate)
    surge_window_mask[start_index:end_index] = np.hanning(end_index - start_index)
    
    # Add the surge to the base price
    final_price_series = base_price + surge_signal * surge_window_mask * 15.0 # Amplify surge effect
    
    # --- Run the simulation tick by tick ---
    for i in range(num_samples):
        current_time_sec = i / sample_rate
        price = final_price_series[i]
        
        detector.add_price_tick(symbol, price)
        
        # Run detection every ~1/4 second
        if i % (sample_rate // 4) == 0:
            surge = detector.detect_surge(symbol)
            
            if surge:
                print(f"[{current_time_sec:5.2f}s] 🌊🌊🌊 SURGE DETECTED! 🌊🌊🌊")
                print(f"    Symbol:           {surge.symbol}")
                print(f"    Intensity:        {'█' * int(surge.intensity * 20)} ({surge.intensity:.2f})")
                print(f"    Duration:         {surge.duration_seconds:.2f} seconds")
                print(f"    Primary Harmonic: {surge.primary_harmonic} ({surge.contributing_events[0].sacred_harmonic.frequency_hz:.2f} Hz)")
                print(f"    Dominant Freq:    {surge.contributing_events[0].detected_freq.frequency_hz:.2f} Hz")
                
                print("\n    Contributing Resonances:")
                for event in surge.contributing_events[:3]:
                    print(f"      - {event.sacred_harmonic.name:<20s} ({event.sacred_harmonic.frequency_hz:.2f} Hz * {event.harmonic_multiple:.2f}) | Score: {event.resonance_score:.2f}")
                
                print("\n" + "-"*80)
                # In a real system, we would now alert the trading engine
                # For the demo, we'll just wait for the surge to pass
                time.sleep(surge.duration_seconds)
                print(f"[{current_time_sec + surge.duration_seconds:5.2f}s]  शांत The surge window has passed. Returning to normal scan.")
                print("-"*80 + "\n")
                # Clear buffer to avoid re-detecting the same surge
                detector.price_history[symbol].clear()

            else:
                # print(f"[{current_time_sec:5.2f}s] ...scanning... no surge detected.")
                sys.stdout.write(f"\r[{current_time_sec:5.2f}s] ...scanning... no surge detected. Resonance: {sum(e.resonance_score for e in detector._find_resonance_events(detector._perform_fft_analysis(np.array(list(detector.price_history[symbol]))))):.2f}      ")
                sys.stdout.flush()

        time.sleep(0.001) # Simulate real-time data feed

    print("\n\nDemo complete.")


if __name__ == "__main__":
    run_hnc_demo()
