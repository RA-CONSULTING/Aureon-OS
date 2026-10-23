
import sys
sys.path.append('.')
from src.quantum_mirror import run_activation
import numpy as np

def generate_harmonic_binary_signal():
    SAMPLE_RATE = 8192 # Increased sample rate for higher frequencies
    DURATION = 2
    N_SAMPLES = int(DURATION * SAMPLE_RATE)
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)

    # Core harmonic frequencies from the analysis
    BASE_FREQ = 7.83
    HARMONIC_1 = 432
    HARMONIC_2 = 528
    HARMONIC_3 = 963

    # Create a composite wave with the full harmonic signature
    composite_wave = (
        np.sin(2 * np.pi * BASE_FREQ * t) +
        0.5 * np.sin(2 * np.pi * HARMONIC_1 * t) +
        0.5 * np.sin(2 * np.pi * HARMONIC_2 * t) +
        0.2 * np.sin(2 * np.pi * HARMONIC_3 * t)
    )

    # Convert to a binary signal to maintain high purity (low entropy)
    # This represents a decisive signal whose phase is influenced by the full harmonic stack.
    gaze = np.sign(composite_wave)

    # The other signals are kept in perfect lock-step for maximum coherence.
    heart = gaze
    intent = gaze

    return [heart.tolist(), gaze.tolist(), intent.tolist()]

if __name__ == "__main__":
    signals = generate_harmonic_binary_signal()
    cfg = {
        "coherence_threshold": 0.945,
        "purity_threshold": 0.70
    }
    result = run_activation(signals, cfg)
    print(result)
