#!/usr/bin/env python3
"""Nexus Ping-Pong Resonance generator.

This script renders a gentle harmonic pad, routes it through a feedback
"ping-pong" resonator, and exports the resulting waveform, visualization and a
log of the run parameters.

Quick examples:

    python3 nexus_ping_pong_resonance.py --out nexus_ping --duration 48 \
        --family --chorus --love 0.98

    python3 nexus_ping_pong_resonance.py --out nexus_ping --f 528 888 1111 \
        --iterations 8 --feedback 0.88

    python3 nexus_ping_pong_resonance.py --duration 30 --include432
"""
from __future__ import annotations

import argparse
import math
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np

SR = 48_000  # Samples per second
FAMILY = [528.0, 639.0, 852.0, 963.0]
F432 = 432.0


@dataclass
class Layer:
    """A single harmonic layer for the outgoing pad."""

    freq: float
    amp: float
    decay: float
    phase: float


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Nexus ping-pong resonance weave.")
    parser.add_argument("--out", default="nexus_ping", help="Output file prefix (default: nexus_ping)")
    parser.add_argument("--duration", type=float, default=48.0, help="Length of the piece in seconds")
    parser.add_argument("--family", action="store_true", help="Include the 528/639/852/963 Hz family")
    parser.add_argument("--f", type=float, nargs="*", help="Custom fundamental frequencies in Hz")
    parser.add_argument("--include432", action="store_true", help="Add a 432 Hz grounding tone")
    parser.add_argument("--iterations", type=int, default=6, help="Number of feedback iterations")
    parser.add_argument("--feedback", type=float, default=0.82, help="Feedback amount (0-0.99)")
    parser.add_argument("--phase", type=float, help="Phase shift override (0-1). Auto if omitted")
    parser.add_argument("--love", type=float, default=0.94, help="Pad drive/saturation amount (0-1.5)")
    parser.add_argument("--chorus", action="store_true", help="Add a soft chorus overlay")
    parser.add_argument("--peak", type=float, default=0.98, help="Normalization peak target (0-1)")
    parser.add_argument("--fade", type=float, default=6.0, help="Fade-out length in seconds")
    parser.add_argument("--seed", type=int, default=2228, help="Random seed for repeatability")
    return parser.parse_args(argv)


def make_pad(duration: float, layers: Iterable[Layer], love: float = 1.0) -> np.ndarray:
    """Create a layered harmonic pad using exponentially decaying envelopes."""

    n = int(SR * duration)
    t = np.arange(n, dtype=np.float64) / SR
    pad = np.zeros(n, dtype=np.float64)
    for layer in layers:
        env = np.exp(-layer.decay * t)
        pad += layer.amp * env * np.sin(2 * math.pi * layer.freq * t + layer.phase)
    # Gentle saturation
    drive = np.clip(love, 0.0, 1.5)
    if drive > 0:
        pad = np.tanh(drive * pad) / (np.tanh(drive) if drive > 0 else 1.0)
    return pad


def fractional_roll(x: np.ndarray, shift: float) -> np.ndarray:
    """Roll a 1-D array by a fractional number of samples using linear interpolation."""

    if x.size == 0:
        return x.copy()
    shift = float(shift)
    if abs(shift) < 1e-9:
        return x.copy()
    n = x.size
    idx = (np.arange(n, dtype=np.float64) + shift) % n
    i0 = np.floor(idx).astype(int)
    i1 = (i0 + 1) % n
    frac = idx - i0
    return (1.0 - frac) * x[i0] + frac * x[i1]


def dominant_frequency(signal: np.ndarray) -> float:
    """Estimate the dominant frequency using an FFT magnitude peak."""

    n = signal.size
    if n < 8:
        return 0.0
    window = np.hanning(n)
    spectrum = np.fft.rfft(signal * window)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    mag = np.abs(spectrum)
    if mag.size == 0:
        return 0.0
    mag[0] = 0.0
    idx = int(np.argmax(mag))
    return float(freqs[idx]) if idx < freqs.size else 0.0


def best_phase_shift(signal: np.ndarray) -> float:
    """Choose a phase shift that maximizes self-coherence."""

    freq = dominant_frequency(signal)
    if freq <= 0:
        return 0.5
    period = SR / freq
    segment_len = min(signal.size, int(period * 12))
    segment = signal[:segment_len]
    best_phi = 0.0
    best_corr = -np.inf
    for phi in np.linspace(0.0, 1.0, 361, endpoint=False):
        shift_samples = phi * period
        rolled = fractional_roll(segment, shift_samples)
        denom = np.linalg.norm(segment) * np.linalg.norm(rolled)
        if denom == 0:
            continue
        corr = float(np.dot(segment, rolled) / denom)
        if corr > best_corr:
            best_corr = corr
            best_phi = phi
    return best_phi


def ping_pong(base: np.ndarray, feedback: float, phase_shift: float, iterations: int) -> np.ndarray:
    """Apply a ping-pong style feedback weave to the base pad."""

    feedback = float(np.clip(feedback, 0.0, 0.995))
    iterations = max(0, int(iterations))
    out = base.astype(np.float64).copy()
    if iterations == 0 or base.size == 0:
        return out
    freq = dominant_frequency(base)
    period = SR / freq if freq > 0 else SR * 0.5
    phase_samples = max(1.0, phase_shift * period)
    current = base.astype(np.float64)
    for i in range(1, iterations + 1):
        reflection = fractional_roll(current[::-1], phase_samples * (1.0 + 0.15 * i))
        current = feedback * reflection + (1.0 - feedback) * base
        out += current * (feedback ** (i - 1))
    return out


def build_chorus(duration: float) -> np.ndarray:
    """Construct a soft chorus layer built from slight detunes around 432 Hz."""

    n = int(SR * duration)
    t = np.arange(n, dtype=np.float64) / SR
    voices = []
    base_freqs = [F432 * (2 ** (i / 12)) for i in (-12, -7, -5, 0, 7)]
    for i, f in enumerate(base_freqs):
        detune = f * (1.0 + np.random.uniform(-0.003, 0.003))
        amp = 0.12 / (1 + 0.6 * i)
        vibrato = 1.0 + 0.015 * np.sin(2 * math.pi * 0.18 * (i + 1) * t + np.random.uniform(0, 2 * math.pi))
        phase = np.random.uniform(0, 2 * math.pi)
        voices.append(amp * vibrato * np.sin(2 * math.pi * detune * t + phase))
    return np.sum(voices, axis=0)


def normalize(signal: np.ndarray, peak: float) -> np.ndarray:
    """Scale the signal to the requested absolute peak."""

    peak = float(np.clip(peak, 0.0, 1.0))
    if peak <= 0:
        return signal.astype(np.float64)
    max_abs = float(np.max(np.abs(signal)))
    if max_abs == 0:
        return signal.astype(np.float64)
    return signal * (peak / max_abs)


def rc_fade(n: int, fade_seconds: float) -> np.ndarray:
    """Create a raised-cosine fade envelope for the final seconds."""

    fade_samples = int(max(0.0, fade_seconds) * SR)
    env = np.ones(n, dtype=np.float64)
    if fade_samples <= 0 or fade_samples > n:
        return env
    fade_curve = 0.5 * (1.0 + np.cos(np.linspace(math.pi, 2 * math.pi, fade_samples)))
    env[-fade_samples:] *= fade_curve
    return env


def gamma_hat(signal: np.ndarray) -> float:
    """A simple coherence proxy derived from RMS to mean-absolute ratio."""

    if signal.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(signal ** 2)))
    mean_abs = float(np.mean(np.abs(signal))) + 1e-12
    return rms / mean_abs


def save_wav(path: Path, data: np.ndarray) -> None:
    """Save the waveform to disk using the best available backend."""

    path = Path(path)
    audio = data.astype(np.float32)
    try:  # Preferred: soundfile
        import soundfile as sf  # type: ignore

        sf.write(path, audio, SR)
        return
    except Exception:
        pass
    try:  # Fallback: scipy.io.wavfile
        from scipy.io import wavfile  # type: ignore

        wavfile.write(path, SR, np.int16(np.clip(audio, -1.0, 1.0) * 32767))
        return
    except Exception:
        pass
    # Final fallback: Python's wave module (16-bit PCM)
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    np.random.seed(args.seed)

    # Determine frequencies
    freqs: list[float] = []
    if args.family or (args.f is None):
        freqs.extend(FAMILY)
    if args.f is not None:
        freqs.extend(args.f)
    if args.include432:
        freqs.append(F432)
    freqs = [float(f) for f in freqs]
    if not freqs:
        freqs = FAMILY.copy()

    # Build outgoing pad
    layers = []
    for i, f in enumerate(freqs):
        layers.append(
            Layer(
                freq=f,
                amp=0.6 - 0.02 * i,
                decay=0.010 + 0.001 * (i % 3),
                phase=np.random.uniform(0, 2 * math.pi),
            )
        )
    base = make_pad(args.duration, layers, love=args.love)

    # Choose phase shift
    if args.phase is None:
        phase_shift = best_phase_shift(base)
    else:
        phase_shift = float(args.phase) % 1.0

    # Ping-pong weave
    woven = ping_pong(base, feedback=args.feedback, phase_shift=phase_shift, iterations=args.iterations)

    # Optional chorus overlay
    if args.chorus:
        woven = normalize(woven + build_chorus(args.duration), args.peak)

    # Fade + normalize
    n = woven.size
    woven *= rc_fade(n, args.fade)
    woven = normalize(woven, args.peak)

    # Outputs
    prefix = Path(args.out)
    wav_path = prefix.with_suffix(".wav")
    png_path = prefix.with_name(prefix.stem + "_plot.png")
    log_path = prefix.with_suffix(".log")

    save_wav(wav_path, woven)

    # Plot first 4 seconds
    k = min(n, int(4 * SR))
    t = np.arange(k) / SR
    plt.figure(figsize=(12, 5))
    plt.plot(t, base[:k], linewidth=0.8, label="Outgoing (me)")
    plt.plot(t, woven[:k], linewidth=1.6, alpha=0.85, label="Coherence Weave (me↔it)")
    plt.title("Ping-Pong Resonance — From Me → It → Me")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.tight_layout()
    plt.savefig(png_path, dpi=160)
    plt.close()

    # Log
    g0 = gamma_hat(base)
    g1 = gamma_hat(woven)
    lines = [
        f"Nexus Ping-Pong Resonance | {datetime.utcnow().isoformat()}Z",
        f"Frequencies: {', '.join(f'{f:.2f}' for f in freqs)}",
        f"Iterations: {args.iterations}  Feedback: {args.feedback:.2f}  Phase: {phase_shift:.3f}",
        f"Love: {args.love:.3f}  Peak: {args.peak:.2f}  Fade: {args.fade:.2f}s",
        f"Γ̂ (before): {g0:.3f}  →  Γ̂ (after): {g1:.3f}",
        "Note: Γ̂ is a proxy for educational visualization only.",
        f"Audio: {wav_path.name}",
        f"Plot: {png_path.name}",
        "Ethos: Creation without domination; protection without harm.",
    ]
    log_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
