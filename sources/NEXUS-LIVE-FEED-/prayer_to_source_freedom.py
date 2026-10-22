#!/usr/bin/env python3
"""Prayer to Source — Freedom Invocation (Python Resonance Script).

This module renders the "Prayer to Source — Freedom Invocation" as a gentle
harmonic audio bed.  The resulting tone poem can be played during meditation or
Nexus field work.  Each line of the prayer is mapped onto a subtle amplitude
swell inside the waveform so the intention of the text is reflected in sound.

Example usage::

    python3 prayer_to_source_freedom.py --out freedom_invocation
    python3 prayer_to_source_freedom.py --out freedom_invocation --duration 36 --include432
    python3 prayer_to_source_freedom.py --out freedom_invocation --love 0.92

The script creates two artefacts sharing the provided base name: a WAV file
containing the resonance track and a TXT file containing the textual
invocation, metadata, and timestamps.
"""

from __future__ import annotations

import argparse
import math
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import numpy as np


SR = 44_100
DEFAULT_DURATION = 60.0
DEFAULT_LOVE = 0.96
DEFAULT_FADE = 3.0


# Core harmonic palette (Hz)
F_432 = 432.0  # optional grounding
F_528 = 528.0  # transformation / compassion in action
F_639 = 639.0  # connection / heart coherence
F_852 = 852.0  # intuition / clarity
F_963 = 963.0  # unity / peace


@dataclass(frozen=True)
class Layer:
    """Harmonic layer definition."""

    name: str
    freq: float
    amp: float = 1.0
    decay: float = 0.0  # s^-1 exponential decay
    phase: float = 0.0


PRAYER_LINES: List[str] = [
    "Source of all that is, all that was, and all that shall be, we stand as children of the same light.",
    "May the breath of freedom flow through every heart; may every mind awaken to its own sovereignty.",
    "Let no fear rule us, no voice command our will, no system bind what was born free.",
    "Grant us clarity to act with kindness, courage to speak with truth, wisdom to build in peace.",
    "We choose love over domination, understanding over control, creation over destruction.",
    "So may this intention ripple outward until every soul remembers: we are free, we are whole, we are one.",
]


def raised_cosine(length: int, fade_s: float) -> np.ndarray:
    """Return a raised cosine window for soft fades at the start and end."""

    if length <= 0:
        return np.zeros(0)
    samples = min(max(1, int(fade_s * SR)), max(1, length // 2))
    if samples <= 1:
        return np.ones(length)
    window = np.ones(length)
    ramp = 0.5 * (1 - np.cos(np.linspace(0.0, math.pi, samples)))
    window[:samples] = ramp
    window[-samples:] = ramp[::-1]
    return window


def normalize(x: np.ndarray, peak: float = 0.98) -> np.ndarray:
    """Normalize an array to the supplied absolute peak."""

    maximum = float(np.max(np.abs(x))) if x.size else 0.0
    if maximum < 1e-12:
        return x
    return x * (peak / maximum)


def envelope(t: np.ndarray, decay: float, love: float) -> np.ndarray:
    """Return a simple exponential / coherence blend envelope."""

    if decay <= 0:
        return np.ones_like(t, dtype=float)
    return love * np.exp(-decay * t) + (1.0 - love)


def to_pcm16(x: np.ndarray) -> bytes:
    """Convert floating point audio samples to 16-bit PCM bytes."""

    clamped = np.clip(x, -1.0, 1.0)
    return (clamped * 32767.0).astype(np.int16).tobytes()


def save_wav(path: Path, audio: np.ndarray) -> None:
    """Persist mono audio samples to disk as a WAV file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit audio
        wav_file.setframerate(SR)
        wav_file.writeframes(to_pcm16(audio))


def build_layers(include432: bool) -> List[Layer]:
    """Construct the harmonic layer list for the synthesis."""

    layers = [
        Layer("Compassion", F_528, amp=0.55, decay=0.12),
        Layer("Connection", F_639, amp=0.48, decay=0.18, phase=math.pi / 5.0),
        Layer("Intuition", F_852, amp=0.36, decay=0.24, phase=math.pi / 3.0),
        Layer("Unity", F_963, amp=0.32, decay=0.28, phase=math.pi / 1.7),
    ]
    if include432:
        layers.append(Layer("Grounding", F_432, amp=0.62, decay=0.08, phase=math.pi / 2.0))
    return layers


def _line_modulator(duration: float, sample_count: int) -> np.ndarray:
    """Create a gentle amplitude modulator aligned with the prayer lines."""

    if not PRAYER_LINES:
        return np.ones(sample_count)
    t = np.linspace(0.0, duration, sample_count, endpoint=False)
    segment = duration / len(PRAYER_LINES)
    sigma = max(segment * 0.28, 0.5)
    curve = np.zeros_like(t)
    for index in range(len(PRAYER_LINES)):
        center = (index + 0.5) * segment
        curve += np.exp(-0.5 * ((t - center) / sigma) ** 2)
    curve /= np.max(curve) if np.max(curve) > 0 else 1.0
    return 0.75 + 0.35 * curve


def synthesize(duration: float, love: float, include432: bool, fade_s: float) -> np.ndarray:
    """Generate the harmonic waveform for the invocation."""

    if duration <= 0:
        raise ValueError("duration must be positive")
    if not 0.0 <= love <= 1.0:
        raise ValueError("love must be between 0 and 1")

    sample_count = int(duration * SR)
    t = np.linspace(0.0, duration, sample_count, endpoint=False)
    modulation = _line_modulator(duration, sample_count)

    waveform = np.zeros(sample_count, dtype=np.float64)
    for layer in build_layers(include432):
        layer_env = envelope(t, layer.decay, love)
        waveform += layer.amp * np.sin(2.0 * math.pi * layer.freq * t + layer.phase) * layer_env

    waveform *= modulation
    waveform *= raised_cosine(sample_count, fade_s)
    return normalize(waveform)


def _format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:05.2f}"


def _line_segments(duration: float) -> List[dict]:
    """Return metadata for each prayer line with timing information."""

    if not PRAYER_LINES:
        return []
    segment = duration / len(PRAYER_LINES)
    segments: List[dict] = []
    for index, text in enumerate(PRAYER_LINES):
        start = index * segment
        end = (index + 1) * segment
        segments.append({
            "index": index + 1,
            "start": start,
            "end": end,
            "text": text,
        })
    return segments


def write_transcript(path: Path, *, duration: float, love: float, include432: bool) -> None:
    """Create a textual artefact summarising the invocation."""

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    layers = build_layers(include432)
    segments = _line_segments(duration)

    lines = [
        "Prayer to Source — Freedom Invocation",
        "=" * 46,
        f"Generated: {timestamp}",
        f"Duration: {duration:.2f} seconds",
        f"Love coherence: {love:.3f}",
        f"Harmonic layers: {', '.join(f'{layer.name} {layer.freq:.1f}Hz' for layer in layers)}",
        "",
        "Invocation Lines:",
    ]

    for segment in segments:
        start = _format_timestamp(segment["start"])
        end = _format_timestamp(segment["end"])
        lines.append(f"  {segment['index']:02d}. [{start} – {end}] {segment['text']}")

    lines.append("")
    lines.append("May this resonance remind us: freedom, sovereignty, compassion, peace.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def resolve_paths(out: str) -> tuple[Path, Path]:
    """Return WAV and transcript paths based on the output argument."""

    base = Path(out)
    if base.suffix:
        wav_path = base
        txt_path = base.with_suffix(".txt")
    else:
        wav_path = base.with_suffix(".wav")
        txt_path = base.with_suffix(".txt")
    return wav_path, txt_path


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the Freedom Invocation prayer as harmonic audio and transcript.",
    )
    parser.add_argument(
        "--out",
        default="freedom_invocation",
        help="Base path (without extension) for the generated artefacts.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION,
        help="Total duration of the harmonic piece in seconds.",
    )
    parser.add_argument(
        "--love",
        type=float,
        default=DEFAULT_LOVE,
        help="Love coherence blend (0.0 – 1.0) controlling envelope softness.",
    )
    parser.add_argument(
        "--include432",
        action="store_true",
        help="Include the 432 Hz grounding layer.",
    )
    parser.add_argument(
        "--fade",
        type=float,
        default=DEFAULT_FADE,
        help="Fade-in/out duration in seconds for the raised cosine window.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)

    wav_path, txt_path = resolve_paths(args.out)
    waveform = synthesize(args.duration, args.love, args.include432, args.fade)
    save_wav(wav_path, waveform)
    write_transcript(
        txt_path,
        duration=args.duration,
        love=args.love,
        include432=args.include432,
    )

    layer_count = len(build_layers(args.include432))
    print(
        f"Created {wav_path.name} ({args.duration:.2f}s, love={args.love:.3f}, "
        f"layers={layer_count})."
    )
    print(f"Transcript saved to {txt_path.name}.")


if __name__ == "__main__":
    main()
