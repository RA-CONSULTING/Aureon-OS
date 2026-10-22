
import sys
sys.path.append('.')
from src.quantum_mirror import run_activation
import numpy as np

def generate_pure_signal():
    # The system requires a HIGHLY pure (low entropy) signal.
    # This means the signal's values should be concentrated in a narrow range.
    # We create a signal that is mostly constant (0.5) with a tiny, coherent sine wave.
    # This provides the variance needed for coherence while keeping entropy extremely low.

    # Define Signal Parameters
    SAMPLE_RATE = 4096
    DURATION = 2
    N_SAMPLES = int(DURATION * SAMPLE_RATE)
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)

    # Create a low-amplitude sine wave
    subtle_wave = 0.01 * np.sin(2 * np.pi * 7.83 * t)

    # Create a base "gaze" signal that is mostly constant
    gaze = 0.5 + subtle_wave

    # Create highly correlated Heart and Intent signals
    heart = gaze + np.random.normal(0, 0.001, N_SAMPLES)
    intent = gaze + np.random.normal(0, 0.001, N_SAMPLES)

    return [heart.tolist(), gaze.tolist(), intent.tolist()]

if __name__ == "__main__":
    signals = generate_pure_signal()
    # The validation threshold in quantum_mirror.py is 0.945 for coherence
    # and 0.70 for purity.
    cfg = {
        "coherence_threshold": 0.945,
        "purity_threshold": 0.70
    }
    result = run_activation(signals, cfg)
    print(result)
