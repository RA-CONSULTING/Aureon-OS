#!/usr/bin/env python3
"""Audio signal adapter — the next *real* :class:`SignalAdapter` for the
human-harmonic proxy.

It turns an audio clip into a derived frequency series and hands it to
:func:`aureon.bio.human_harmonic_proxy.score_signal`, so a recording can finally
be scored by the same falsifiable engine — **without** becoming a voice, speaker,
or emotion reader.

Content-agnostic by construction
--------------------------------
The signal is derived from the clip's **global spectral statistics only**: the
dominant temporal frequencies across the whole waveform. There is **no** speech
recognition, no speaker identification, no per-word/per-segment analysis, and no
emotion/voice-trait inference anywhere in this module. That makes it
*structurally* incapable of physiognomy-of-voice regardless of what the clip
contains. A dominant frequency is not identity, and the output is only
*statistical structure in a derived signal* — never a claim, reading, health
signal, or trait about a person. The immutable scientific boundary and the
consent/provenance gate of :mod:`aureon.bio.human_harmonic_proxy` still apply,
because all scoring flows through :func:`score_signal` unchanged.

Physics, reused (not invented)
------------------------------
An audio waveform *is* a time-series of amplitude samples, so a real FFT yields
its dominant temporal frequencies (Hz) directly — the identical operation the UPE
adapter performs on a photon-count series. The proxy's :func:`fold_to_band` then
octave-folds those raw audio frequencies into the engine's 1000-2000 Hz
modulation band, the same octave-fold the engine performs for molecular peaks.

Pure numpy + stdlib (WAV via the stdlib :mod:`wave` module). No new dependency,
no network, no import-time side effects.
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import (
    SCIENTIFIC_BOUNDARY,
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)

__all__ = [
    "AudioSignalAdapter",
    "score_audio",
    "synthetic_audio",
    "main",
]

PHI: float = float(engine.PHI)


# ---------------------------------------------------------------------------
# dominant-frequency picking (audio waveform -> Hz; peaks are FFT local maxima)
# ---------------------------------------------------------------------------


def _dominant_audio_hz(
    samples: np.ndarray,
    *,
    sample_rate_hz: float,
    min_prominence: float = 0.05,
    max_peaks: int = 24,
) -> list[float]:
    """Dominant temporal frequencies (Hz) of a waveform via a windowed real FFT.

    The waveform is mean-detrended and Hann-windowed (standard DSP; suppresses
    spectral leakage so closely-spaced tones resolve cleanly and sidelobes do not
    fabricate structure). Power is normalised 0-1; a peak must be a strict local
    maximum rising at least ``min_prominence`` above its neighbours. A flat /
    broadband spectrum yields no dominant tone — the honest non-structure result,
    never a fabricated one.
    """
    x = np.asarray(samples, dtype=float).ravel()
    if x.size < 4 or sample_rate_hz <= 0:
        return []
    x = x - float(np.mean(x))
    xw = x * np.hanning(x.size)
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate_hz))
    power = np.abs(np.fft.rfft(xw)) ** 2
    if freqs.size < 3 or float(np.max(power)) <= 0:
        return []
    norm = power / float(np.max(power))
    picks: list[tuple[float, float]] = []
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] >= norm[i + 1] and norm[i] >= min_prominence and freqs[i] > 0:
            picks.append((float(freqs[i]), float(norm[i])))
    picks.sort(key=lambda p: -p[1])  # loudest first
    return sorted(f for f, _ in picks[:max_peaks])


# ---------------------------------------------------------------------------
# loading a waveform (array / (samples, rate) / WAV path)
# ---------------------------------------------------------------------------


def _load_waveform(spec: Any, *, sample_rate_hz: float | None) -> tuple[np.ndarray, float]:
    """Load ``spec`` to a (mono float array, sample_rate_hz) pair.

    Accepts a mono ``np.ndarray`` (``sample_rate_hz`` then required), a
    ``(samples, rate)`` tuple, or a path to a PCM WAV file read via the stdlib
    :mod:`wave` module. Multi-channel input is averaged to mono (a global
    statistic, not a per-channel/per-source separation). Deterministic; no
    randomness, no network.
    """
    if isinstance(spec, tuple) and len(spec) == 2 and not isinstance(spec[0], (str, Path)):
        samples, rate = spec
        return _to_mono(np.asarray(samples, dtype=float)), float(rate)

    if isinstance(spec, (str, Path)):
        with wave.open(str(spec), "rb") as wav:
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            rate = float(wav.getframerate())
            raw = wav.readframes(wav.getnframes())
        dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(sampwidth)
        if dtype is None:  # pragma: no cover - guarded by callers
            raise ValueError(f"unsupported WAV sample width: {sampwidth} bytes")
        data = np.frombuffer(raw, dtype=dtype).astype(np.float64)
        if n_channels > 1:
            data = data.reshape(-1, n_channels)
        return _to_mono(data), rate

    if isinstance(spec, np.ndarray):
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required when passing a raw waveform array")
        return _to_mono(spec.astype(np.float64)), float(sample_rate_hz)

    raise TypeError(f"unsupported audio spec type: {type(spec)!r}")


def _to_mono(data: np.ndarray) -> np.ndarray:
    """Average a (samples,) or (samples, channels) array down to a mono series."""
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 2:
        arr = arr.mean(axis=1)
    return arr.ravel()


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------


class AudioSignalAdapter:
    """Extract a derived signal from an audio clip's global spectral statistics.

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Consent and provenance are **required arguments** — the adapter never
    fabricates them; the caller must affirmatively grant consent for the clip.
    """

    modality: str = "audio"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        sample_rate_hz: float | None = None,
        max_peaks: int = 24,
    ) -> HumanSignal:
        """Return a :class:`HumanSignal` (modality='audio') of folded modulation tones."""
        samples, rate = _load_waveform(spec, sample_rate_hz=sample_rate_hz)
        raw_hz = _dominant_audio_hz(samples, sample_rate_hz=rate, max_peaks=max_peaks)
        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        label = f"audio:{Path(spec).name}" if isinstance(spec, (str, Path)) else "audio:array"
        return HumanSignal(
            label=label,
            frequencies_hz=tones,
            provenance=provenance,
            consent=consent,
            modality=self.modality,
            notes=(
                f"{len(tones)} dominant spectral mode(s); global clip statistics only "
                "(no speech/speaker/emotion analysis), not a claim about any person"
            ),
        )


def score_audio(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    sample_rate_hz: float | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
    max_peaks: int = 24,
) -> ProxyResult:
    """Extract an audio clip's spectral signal and score it through the governed pipeline."""
    signal = AudioSignalAdapter().extract(
        spec, consent=consent, provenance=provenance, sample_rate_hz=sample_rate_hz, max_peaks=max_peaks
    )
    return score_signal(signal, nulls=nulls, seed=seed)


# ---------------------------------------------------------------------------
# synthetic self-test (no real subject)
# ---------------------------------------------------------------------------


def synthetic_audio(
    kind: str = "noise",
    *,
    seed: int = 0,
    sample_rate_hz: float = 8000.0,
    n: int = 8000,
) -> tuple[np.ndarray, float]:
    """Return an ``(waveform, sample_rate_hz)`` synthetic clip for the self-test (no real subject).

    ``noise`` = seeded broadband noise (must score non-separable — the honest
    absent anchor). ``structured`` = a sum of sine tones at two tight clusters one
    golden ratio apart, both inside the modulation band, plus light seeded noise;
    its *folded* dominant tones equal a known clustered + PHI-spaced set, so it
    must score ``structure_present`` — proving the adapter detects real structure,
    not by fiat. Fully deterministic for a given seed.
    """
    rng = np.random.default_rng([int(seed), 11])
    t = np.arange(int(n)) / float(sample_rate_hz)
    if kind == "noise":
        return rng.standard_normal(t.size), float(sample_rate_hz)
    if kind == "structured":
        base = 1100.0
        centers = np.array([base, base * PHI])  # ~1100 and ~1780, both in-band
        offsets = np.array([-4.0, 0.0, 4.0])    # within-cluster spread (drives Test A)
        tones = (centers[:, None] + offsets[None, :]).ravel()
        waveform = np.zeros_like(t)
        for f in tones:
            waveform = waveform + np.sin(2.0 * np.pi * float(f) * t)
        waveform = waveform + 0.02 * rng.standard_normal(t.size)  # light noise, structure dominates
        return waveform, float(sample_rate_hz)
    raise ValueError(f"unknown synthetic kind {kind!r}")


def main(argv: list[str] | None = None) -> int:
    """CLI: score an audio clip the caller consents to, or run the synthetic self-test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Score an audio clip's spectral-derived signal (content-agnostic, no voice/speaker analysis)."
    )
    parser.add_argument("audio", nargs="?", help="path to a PCM WAV the caller consents to analyse")
    parser.add_argument("--consent", action="store_true", help="affirm consent to analyse this clip")
    parser.add_argument("--provenance", default="", help="provenance string (required with --consent)")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true", help="run structured⇒present / noise⇒absent demo")
    args = parser.parse_args(argv)

    print("Audio signal adapter — waveform -> dominant frequency -> folded tone (no voice analysis)")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")

    if args.self_test:
        prov = "synthetic audio self-test (no real subject)"
        noise = score_audio(synthetic_audio("noise", seed=args.seed), consent=True, provenance=prov,
                            nulls=args.nulls, seed=args.seed)
        structured = score_audio(synthetic_audio("structured", seed=args.seed), consent=True, provenance=prov,
                                 nulls=args.nulls, seed=args.seed)
        checks = [
            (noise.valid and not noise.structure_present,
             "broadband noise clip  -> structure ABSENT (honest anchor)"),
            (structured.valid and structured.structure_present,
             "structured tone clip  -> structure PRESENT"),
            (structured.boundary == SCIENTIFIC_BOUNDARY,
             "scientific boundary present"),
        ]
        ok = True
        for passed, label in checks:
            ok = ok and passed
            print(f"  {'✅' if passed else '❌'} {label}")
        print(f"  noise:      A_p={noise.test_A_p} B_p={noise.test_B_p} n_tones={noise.n_tones}")
        print(f"  structured: A_p={structured.test_A_p} B_p={structured.test_B_p} n_tones={structured.n_tones}")
        return 0 if ok else 1

    if not args.audio:
        parser.error("provide a WAV path, or use --self-test")
    result = score_audio(args.audio, consent=bool(args.consent), provenance=args.provenance,
                         nulls=args.nulls, seed=args.seed)
    d = result.to_dict()
    print(f"  audio            : {args.audio}")
    print(f"  n_tones          : {d['n_tones']}")
    print(f"  valid / blocked  : {d['valid']} / {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  test_A_p/test_B_p: {d['test_A_p']} / {d['test_B_p']}")
    print(f"  reason           : {d['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
