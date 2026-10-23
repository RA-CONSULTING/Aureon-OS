
import json
import math
import random
import time

# Potential neural states for display in diagnostics
BRAINWAVE_STATES = [
    "Alpha (Calm)",
    "Beta (Focused)",
    "Theta (Dream)",
    "Delta (Restorative)",
    "Gamma (Elevated)",
]

# A list of sample species and their approximate locations
SAMPLE_SPECIES = [
    ("Monarch Butterfly", "Sierra Madre, Mexico"),
    ("Blue Whale", "Pacific Ocean"),
    ("Giant Sequoia", "California, USA"),
    ("Bengal Tiger", "Sundarbans, India"),
    ("Emperor Penguin", "Antarctica"),
    ("Golden Lion Tamarin", "Brazilian Atlantic Forest")
]

def generate_ecg_signal(length=84):
    """Create a synthetic ECG-like waveform with gentle noise."""
    # Build a repeating waveform that loosely resembles a cardiac rhythm
    signal = []
    for index in range(length):
        phase = (index % 40) / 40.0

        # Base heartbeat spike using a sharp exponential rise and decay
        spike = math.exp(-40 * (phase - 0.1) ** 2)

        # Baseline sine oscillation with minor drift
        baseline = 0.12 * math.sin(2 * math.pi * phase * 1.5)

        # Introduce subtle noise so the graph feels alive
        noise = random.uniform(-0.05, 0.05)

        signal.append(baseline + 1.8 * spike + noise)

    return signal


def generate_metrics():
    """Construct a coherent set of biometric readings."""
    heart_rate = random.randint(58, 98)
    temperature = round(random.uniform(36.4, 37.4), 1)

    return {
        "heartRate": heart_rate,
        "oxygenSaturation": random.randint(94, 100),
        "bloodPressure": f"{random.randint(108, 124)}/{random.randint(68, 82)}",
        "respirationRate": random.randint(11, 19),
        "bodyTemperature": temperature,
        "brainwaveState": random.choice(BRAINWAVE_STATES),
        "auricFieldStrength": random.uniform(72, 98),
        "ecg": generate_ecg_signal(),
    }


def generate_bio_resonance_data(include_metrics=False):
    """Generates a sample bio-resonance reading."""
    species, location = random.choice(SAMPLE_SPECIES)

    # Simulate a resonance factor. A value closer to 1.0 is ideal.
    # We will simulate a range of values to represent species in various states of health.
    resonance_factor = random.uniform(0.3, 0.99)

    payload = {
        "species": species,
        "resonanceFactor": resonance_factor,
        "location": location,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if include_metrics:
        payload["metrics"] = generate_metrics()

    return payload

def stream_bio_resonance_data():
    """Yields a continuous stream of bio-resonance data."""
    while True:
        # Generate a list of readings for different species
        entries = []
        count = random.randint(3, 5)

        # Ensure at least one entry carries rich biometric metrics for the UI snapshot
        metrics_index = random.randrange(count)

        for idx in range(count):
            entries.append(generate_bio_resonance_data(include_metrics=idx == metrics_index))

        data = {"bioResonance": entries}
        yield f"data: {json.dumps(data)}\n\n"
        time.sleep(2) # Simulate a 2-second interval between readings

if __name__ == "__main__":
    for data_point in stream_bio_resonance_data():
        print(data_point)
