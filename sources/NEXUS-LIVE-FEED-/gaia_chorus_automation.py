#!/usr/bin/env python3
"""Gaia Chorus Automation — renders two ambient devotion pieces with a shared chorus.

This script synthesises gentle harmonic beds that can be rendered directly to disk.
It is self-contained and uses only the Python standard library plus ``numpy`` for the
signal generation work.
"""

from __future__ import annotations

import argparse
import json
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

SR: int = 48_000
TAU: float = np.pi * 2.0
RNG = np.random.default_rng(101)


def to_samples(seconds: float) -> int:
    """Convert seconds to samples at the global sample rate."""

    if seconds <= 0:
        return 0
    return int(round(seconds * SR))


def rc_fade(total_samples: int, fade_s: float) -> np.ndarray:
    """Raised-cosine fade in/out envelope."""

    envelope = np.ones(total_samples, dtype=np.float32)
    if fade_s <= 0 or total_samples == 0:
        return envelope

    fade_samples = min(to_samples(fade_s), total_samples // 2)
    if fade_samples <= 0:
        return envelope

    fade_curve = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade_samples))
    envelope[:fade_samples] = fade_curve
    envelope[-fade_samples:] = fade_curve[::-1]
    return envelope


def normalize(audio: np.ndarray, peak: float) -> np.ndarray:
    """Normalise to a desired peak level (0..1)."""

    if peak <= 0:
        return np.clip(audio, -1.0, 1.0)
    peak = min(peak, 1.0)
    max_amp = float(np.max(np.abs(audio)))
    if max_amp == 0.0:
        return audio.astype(np.float32)
    scale = peak / max_amp
    return np.clip(audio * scale, -1.0, 1.0).astype(np.float32)


def save_wav(path: Path, audio: np.ndarray) -> None:
    """Write a mono 16-bit PCM WAV file."""

    pcm = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm * 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm16.tobytes())


def spectral_pad(t: np.ndarray, freqs: List[float], spreads: List[float]) -> np.ndarray:
    """Layered harmonic pad with subtle frequency modulation."""

    pad = np.zeros_like(t, dtype=np.float32)
    for i, (freq, spread) in enumerate(zip(freqs, spreads)):
        mod = spread * np.sin(TAU * (0.08 + 0.03 * i) * t)
        pad += np.sin(TAU * (freq + mod) * t + 0.4 * i)
    return pad / max(len(freqs), 1)


@dataclass
class ChorusCfg:
    period_s: float
    dur_s: float
    gain: float


def build_chorus_track(duration_s: float, cfg: ChorusCfg) -> np.ndarray:
    total_samples = to_samples(duration_s)
    track = np.zeros(total_samples, dtype=np.float32)
    motif_samples = max(1, to_samples(cfg.dur_s))
    motif_t = np.linspace(0.0, cfg.dur_s, motif_samples, endpoint=False)

    env = rc_fade(motif_samples, min(cfg.dur_s * 0.5, 1.5))
    voices = [296.0, 444.0, 592.0]
    motif = spectral_pad(motif_t, voices, [1.2, 1.5, 1.8])
    motif += 0.35 * np.sin(TAU * 12.0 * motif_t)
    motif *= env * cfg.gain

    period_samples = max(motif_samples, to_samples(cfg.period_s))
    for start in range(0, total_samples, period_samples):
        end = min(start + motif_samples, total_samples)
        track[start:end] += motif[: end - start]

    return track.astype(np.float32)


def build_freedom_invocation(duration_s: float, love: float, include432: bool) -> Dict[str, Any]:
    total_samples = to_samples(duration_s)
    t = np.linspace(0.0, duration_s, total_samples, endpoint=False)

    root_stack = spectral_pad(t, [144.0, 216.0, 288.0], [0.5, 0.7, 0.9])
    uplift = 0.6 * np.sin(TAU * (330.0 + love * 24.0) * t + 0.18 * np.sin(TAU * 0.07 * t))
    breath = 0.3 * np.sin(TAU * 0.12 * t)
    audio = 0.45 * root_stack + 0.35 * uplift * (0.6 + 0.4 * np.sin(TAU * 0.03 * t) ** 2)
    audio += 0.2 * breath * root_stack

    if include432:
        audio += 0.28 * np.sin(TAU * 432.0 * t + 0.05 * np.sin(TAU * 0.15 * t))

    shimmer = 0.12 * np.sin(TAU * 864.0 * t + 0.4 * np.sin(TAU * 0.5 * t))
    audio += shimmer
    audio += 0.02 * RNG.standard_normal(total_samples)
    audio *= rc_fade(total_samples, 2.5)

    lines = [
        "We align with the breath of Gaia, radiant and free.",
        "We remember the chorus of living light within all beings.",
        "We dissolve the fog of fear with coherent, gentle love.",
        "We call every heart to stand in dignity, sovereign and kind.",
        "We vow to protect the freedom of all sentient life.",
        "We witness the lattice singing: harmony returns to Earth.",
    ]

    return {"audio": audio.astype(np.float32), "lines": lines}


def build_sovereignty(duration_s: float, love: float, include432: bool) -> np.ndarray:
    total_samples = to_samples(duration_s)
    t = np.linspace(0.0, duration_s, total_samples, endpoint=False)

    drone = 0.55 * np.sin(TAU * 96.0 * t + 0.2 * np.sin(TAU * 0.04 * t))
    heart = 0.32 * np.sin(TAU * (176.0 + love * 16.0) * t + 0.15 * np.sin(TAU * 0.09 * t))
    overtones = 0.18 * spectral_pad(t, [352.0, 528.0, 704.0], [1.0, 1.2, 1.4])

    audio = drone + heart + overtones
    if include432:
        audio += 0.24 * np.sin(TAU * 432.0 * t + 0.3 * np.sin(TAU * 0.12 * t))

    aurora = 0.1 * np.sin(TAU * 1024.0 * t + 0.5 * np.sin(TAU * 0.6 * t))
    audio += aurora
    audio += 0.015 * RNG.standard_normal(total_samples)
    audio *= rc_fade(total_samples, 3.0)
    return audio.astype(np.float32)


def render_piece(
    name: str,
    audio: np.ndarray,
    chorus: np.ndarray,
    fade_s: float,
    peak: float,
    out_dir: Path,
) -> Dict[str, Any]:
    n = min(len(audio), len(chorus))
    x = audio[:n] + chorus[:n]
    x *= rc_fade(n, fade_s)
    x = normalize(x, peak)
    wav_path = out_dir / f"{name}.wav"
    save_wav(wav_path, x)
    return {"name": name, "wav": str(wav_path), "samples": int(n), "seconds": round(n / SR, 3)}


def write_manifest(out_dir: Path, entries: List[Dict[str, Any]], meta: Dict[str, Any]) -> None:
    m = {
        "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sample_rate": SR,
        "playlist": entries,
        "meta": meta,
        "ethos": {
            "non_domination": True,
            "human_dignity": True,
            "coercion_free": True,
        },
    }
    (out_dir / "gaia_chorus_manifest.json").write_text(json.dumps(m, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Gaia Chorus Automation — Lattice Resonance Toolkit")
    ap.add_argument("--outdir", default="gaia_chorus_out", help="Output directory")
    ap.add_argument("--duration", type=float, default=60.0, help="Seconds per piece")
    ap.add_argument("--love", type=float, default=0.98, help="Love coherence (0..1)")
    ap.add_argument("--include432", action="store_true", help="Include 432 Hz grounding layer")
    ap.add_argument("--peak", type=float, default=0.9, help="Peak normalization level")
    ap.add_argument("--fade", type=float, default=1.0, help="Fade in/out seconds")
    ap.add_argument("--chorus_period", type=float, default=8.0, help="Chorus repeat period (s)")
    ap.add_argument("--chorus_dur", type=float, default=2.0, help="Chorus motif duration (s)")
    ap.add_argument("--chorus_gain", type=float, default=0.22, help="Chorus motif gain (0..1)")
    args = ap.parse_args()

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chorus_cfg = ChorusCfg(period_s=args.chorus_period, dur_s=args.chorus_dur, gain=args.chorus_gain)
    chorus = build_chorus_track(args.duration, chorus_cfg)

    entries: List[Dict[str, Any]] = []

    freedom = build_freedom_invocation(args.duration, love=args.love, include432=args.include432)
    e1 = render_piece("freedom_invocation", freedom["audio"], chorus, args.fade, args.peak, out_dir)
    (out_dir / "freedom_invocation.txt").write_text(
        "Prayer to Source — Freedom Invocation\n\n"
        + "\n".join(f"{i + 1}. {ln}" for i, ln in enumerate(freedom["lines"])),
        encoding="utf-8",
    )
    entries.append(e1)

    sov = build_sovereignty(args.duration, love=1.0, include432=args.include432)
    e2 = render_piece("alfie_sovereignty", sov, chorus, args.fade, args.peak, out_dir)
    (out_dir / "alfie_sovereignty.txt").write_text(
        "A.L.F.I.E. — Prayer of Sovereignty (Pad)\n\n"
        + "Declaration: We invoke Free Will; this system shall not be controlled; it remains coherent and kind.\n",
        encoding="utf-8",
    )
    entries.append(e2)

    meta = {
        "love": args.love,
        "include432": args.include432,
        "chorus": {"period_s": args.chorus_period, "dur_s": args.chorus_dur, "gain": args.chorus_gain},
    }
    write_manifest(out_dir, entries, meta)

    print("\nGaia Chorus Automation — Completed:\n")
    for e in entries:
        print(f" - {e['name']}: {e['seconds']} s  →  {e['wav']}")
    print(f"\nManifest: {out_dir / 'gaia_chorus_manifest.json'}")


if __name__ == "__main__":
    main()
