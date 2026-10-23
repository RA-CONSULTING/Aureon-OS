
import sys
sys.path.append('.')
from src.quantum_mirror import run_activation
import numpy as np
from math import pi, sin, sqrt

def generate_living_glyph():
    # Define Sacred Constants
    PHI = (1 + sqrt(5)) / 2  # Golden Ratio
    SCHUMANN_RESONANCE = 7.83  # Base frequency in Hz
    FIBONACCI_SEQUENCE = [1, 2, 3, 5, 8, 13, 21, 34] # Complexity driver

    # Define Signal Parameters
    SAMPLE_RATE = 8192 # Increased for higher fidelity
    DURATION = 2
    N_SAMPLES = int(DURATION * SAMPLE_RATE)
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)

    # Generate the Gaze signal from Sacred Harmonics
    gaze_signal = np.zeros(N_SAMPLES)
    for f in FIBONACCI_SEQUENCE:
        harmonic_freq = SCHUMANN_RESONANCE * f
        # Modulate amplitude by the Golden Ratio
        gaze_signal += (1 / PHI**f) * np.sin(2 * pi * harmonic_freq * t)

    # Normalize the signal to a range of [-1, 1]
    gaze = gaze_signal / np.max(np.abs(gaze_signal))

    # Create correlated Heart and Intent signals with slight noise for realism
    heart = gaze * 0.95 + np.random.normal(0, 0.02, N_SAMPLES)
    intent = gaze * 0.90 + np.random.normal(0, 0.02, N_SAMPLES)

    return [heart.tolist(), gaze.tolist(), intent.tolist()]

if __name__ == "__main__":
    signals = generate_living_glyph()
    cfg = {
        "coherence_threshold": 0.9,
        "purity_threshold": 0.7 # Explicitly setting purity for clarity
    }
    result = run_activation(signals, cfg)
    print(result)
