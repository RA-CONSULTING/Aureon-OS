#!/usr/bin/env python3
"""Video signal adapter — the last real :class:`SignalAdapter` for the
human-harmonic proxy.

It turns a video clip into a derived frequency series and hands it to
:func:`aureon.bio.human_harmonic_proxy.score_signal`, so a recording can finally
be scored by the same falsifiable engine — **without** becoming a face, object,
pose, or scene reader. With this adapter the `SignalAdapter` roadmap is complete:
image · audio · video · UPE · sky · market, all on one unchanged backbone.

Content-agnostic by construction
--------------------------------
Each frame is reduced to a **single global mean-luminance scalar**; the signal is
the sequence of those scalars over time. There is **no** face detection, no object
or pose detection, no scene classification, and no per-region/per-frame content
analysis anywhere in this module. One scalar per frame is *structurally* incapable
of physiognomy regardless of what the clip contains — it is only *statistical
structure in a derived signal*, never a claim, reading, health signal, or trait
about a person. The immutable scientific boundary and the consent/provenance gate
of :mod:`aureon.bio.human_harmonic_proxy` still apply, because all scoring flows
through :func:`score_signal` unchanged.

Physics, reused (not invented)
------------------------------
A per-frame luminance series *is* a time-series sampled at the frame rate, so a
windowed real FFT recovers its dominant temporal frequencies (Hz) directly — the
identical operation the audio and UPE adapters perform on a waveform / photon-count
series. :func:`fold_to_band` then octave-folds those into the engine's 1000-2000 Hz
modulation band, the same octave-fold the engine performs for molecular peaks.

Pure numpy + stdlib for the core; ``imageio`` is imported **lazily and only** to
decode a real video file (the synthetic path and the pure proxy core never need
it). No network, no import-time side effects.
"""

from __future__ import annotations

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
    "VideoSignalAdapter",
    "score_video",
    "synthetic_video",
    "main",
]

PHI: float = float(engine.PHI)

# Rec.601 luma coefficients (global per-frame brightness; not a colour/identity read).
_LUMA_RGB: tuple[float, float, float] = (0.299, 0.587, 0.114)


# ---------------------------------------------------------------------------
# per-frame luminance reduction + dominant-frequency picking
# ---------------------------------------------------------------------------


def _frames_to_luma(frames: np.ndarray) -> np.ndarray:
    """Reduce a frame stack to a per-frame **global mean-luminance** series.

    Accepts ``(F, H, W, 3)`` colour, ``(F, H, W)`` grayscale, or ``(F,)`` scalar
    stacks. Each frame collapses to one number — the whole-frame average brightness
    — so the output carries no spatial, regional, or content information at all.
    """
    arr = np.asarray(frames, dtype=float)
    if arr.ndim == 4 and arr.shape[-1] >= 3:
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        luma = _LUMA_RGB[0] * r + _LUMA_RGB[1] * g + _LUMA_RGB[2] * b
        return luma.reshape(luma.shape[0], -1).mean(axis=1)
    if arr.ndim >= 2:
        return arr.reshape(arr.shape[0], -1).mean(axis=1)
    return arr.ravel()


def _dominant_video_hz(
    luma: np.ndarray,
    *,
    frame_rate_hz: float,
    min_prominence: float = 0.05,
    max_peaks: int = 24,
) -> list[float]:
    """Dominant temporal frequencies (Hz) of a per-frame luminance series via a windowed real FFT.

    The series is mean-detrended and Hann-windowed (standard DSP; suppresses spectral
    leakage so closely-spaced tones resolve cleanly and sidelobes do not fabricate
    structure). Power is normalised 0-1; a peak must be a strict local maximum rising
    at least ``min_prominence`` above its neighbours. A clip with no periodic brightness
    change yields no dominant tone — the honest non-structure result.
    """
    x = np.asarray(luma, dtype=float).ravel()
    if x.size < 4 or frame_rate_hz <= 0:
        return []
    x = x - float(np.mean(x))
    xw = x * np.hanning(x.size)
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(frame_rate_hz))
    power = np.abs(np.fft.rfft(xw)) ** 2
    if freqs.size < 3 or float(np.max(power)) <= 0:
        return []
    norm = power / float(np.max(power))
    picks: list[tuple[float, float]] = []
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] >= norm[i + 1] and norm[i] >= min_prominence and freqs[i] > 0:
            picks.append((float(freqs[i]), float(norm[i])))
    picks.sort(key=lambda p: -p[1])  # brightest first
    return sorted(f for f, _ in picks[:max_peaks])


# ---------------------------------------------------------------------------
# loading frames (array / (frames, fps) / video path via lazy imageio)
# ---------------------------------------------------------------------------


def _load_frames(spec: Any, *, frame_rate_hz: float | None) -> tuple[np.ndarray, float]:
    """Load ``spec`` to a ``(frames, frame_rate_hz)`` pair.

    Accepts a numpy frame stack (``frame_rate_hz`` then required), a
    ``(frames, fps)`` tuple, or a path to a video file decoded via a **lazily
    imported** ``imageio`` (fps read from the reader metadata). Deterministic; no
    randomness, no network. Importing this module never requires ``imageio`` — only
    the real-file path does.
    """
    if isinstance(spec, tuple) and len(spec) == 2 and not isinstance(spec[0], (str, Path)):
        frames, fps = spec
        return np.asarray(frames), float(fps)

    if isinstance(spec, (str, Path)):
        try:
            import imageio
        except Exception as exc:  # noqa: BLE001
            raise ImportError(
                "imageio is required to decode video files "
                "(`pip install imageio[ffmpeg]`); the synthetic path and the pure "
                "proxy core do not need it."
            ) from exc
        reader = imageio.get_reader(str(spec))
        try:
            fps = float(reader.get_meta_data().get("fps", frame_rate_hz or 30.0))
        except Exception:  # noqa: BLE001
            fps = float(frame_rate_hz or 30.0)
        frames = np.stack([np.asarray(fr) for fr in reader])
        reader.close()
        return frames, fps

    if isinstance(spec, np.ndarray):
        if frame_rate_hz is None:
            raise ValueError("frame_rate_hz is required when passing a raw frame stack")
        return spec, float(frame_rate_hz)

    raise TypeError(f"unsupported video spec type: {type(spec)!r}")


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------


class VideoSignalAdapter:
    """Extract a derived signal from a clip's per-frame global luminance.

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Consent and provenance are **required arguments** — the adapter never fabricates
    them; the caller must affirmatively grant consent for the clip.
    """

    modality: str = "video"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        frame_rate_hz: float | None = None,
        max_peaks: int = 24,
    ) -> HumanSignal:
        """Return a :class:`HumanSignal` (modality='video') of folded modulation tones."""
        frames, fps = _load_frames(spec, frame_rate_hz=frame_rate_hz)
        luma = _frames_to_luma(frames)
        raw_hz = _dominant_video_hz(luma, frame_rate_hz=fps, max_peaks=max_peaks)
        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        label = f"video:{Path(spec).name}" if isinstance(spec, (str, Path)) else "video:array"
        return HumanSignal(
            label=label,
            frequencies_hz=tones,
            provenance=provenance,
            consent=consent,
            modality=self.modality,
            notes=(
                f"{len(tones)} dominant per-frame-luma mode(s); global per-frame luminance "
                "only (no face/object/pose analysis), not a claim about any person"
            ),
        )


def score_video(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    frame_rate_hz: float | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
    max_peaks: int = 24,
) -> ProxyResult:
    """Extract a clip's per-frame luminance signal and score it through the governed pipeline."""
    signal = VideoSignalAdapter().extract(
        spec, consent=consent, provenance=provenance, frame_rate_hz=frame_rate_hz, max_peaks=max_peaks
    )
    return score_signal(signal, nulls=nulls, seed=seed)


# ---------------------------------------------------------------------------
# synthetic self-test (no real subject)
# ---------------------------------------------------------------------------


def synthetic_video(
    kind: str = "noise",
    *,
    seed: int = 0,
    frame_rate_hz: float = 4000.0,
    n_frames: int = 4000,
    h: int = 4,
    w: int = 4,
) -> tuple[np.ndarray, float]:
    """Return a ``(frames, frame_rate_hz)`` synthetic clip for the self-test (no real subject).

    ``noise`` = seeded random per-frame luminance (must score non-separable — the
    honest absent anchor). ``structured`` = per-frame luminance driven by a sum of
    sine tones at two tight clusters one golden ratio apart, planted **directly
    in-band and sub-Nyquist** (so :func:`fold_to_band` is the identity and does not
    disturb them) + light seeded noise; its dominant tones equal a known clustered +
    PHI-spaced set, so it must score ``structure_present`` — proving the adapter
    detects real structure, not by fiat. Each frame is a flat ``h×w`` grayscale image
    at that luminance, so it is a genuine frame stack. Fully deterministic per seed.
    """
    rng = np.random.default_rng([int(seed), 13])
    t = np.arange(int(n_frames)) / float(frame_rate_hz)
    if kind == "noise":
        luma = rng.standard_normal(t.size)
    elif kind == "structured":
        base = 1100.0
        centers = np.array([base, base * PHI])  # ~1100 and ~1780, both in-band, < Nyquist(2000)
        offsets = np.array([-4.0, 0.0, 4.0])    # within-cluster spread (drives Test A)
        tones = (centers[:, None] + offsets[None, :]).ravel()
        luma = np.zeros_like(t)
        for f in tones:
            luma = luma + np.sin(2.0 * np.pi * float(f) * t)
        luma = luma + 0.02 * rng.standard_normal(t.size)  # light noise, structure dominates
    else:
        raise ValueError(f"unknown synthetic kind {kind!r}")
    # broadcast the per-frame scalar across a flat grayscale h×w frame -> (F, H, W)
    frames = np.repeat(np.repeat(luma[:, None, None], h, axis=1), w, axis=2)
    return frames, float(frame_rate_hz)


def main(argv: list[str] | None = None) -> int:
    """CLI: score a video clip the caller consents to, or run the synthetic self-test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Score a video clip's per-frame-luminance signal (content-agnostic, no face/object analysis)."
    )
    parser.add_argument("video", nargs="?", help="path to a video the caller consents to analyse")
    parser.add_argument("--consent", action="store_true", help="affirm consent to analyse this clip")
    parser.add_argument("--provenance", default="", help="provenance string (required with --consent)")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true", help="run structured⇒present / noise⇒absent demo")
    args = parser.parse_args(argv)

    print("Video signal adapter — per-frame luminance -> dominant frequency -> folded tone (no face analysis)")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")

    if args.self_test:
        prov = "synthetic video self-test (no real subject)"
        noise = score_video(synthetic_video("noise", seed=args.seed), consent=True, provenance=prov,
                            nulls=args.nulls, seed=args.seed)
        structured = score_video(synthetic_video("structured", seed=args.seed), consent=True, provenance=prov,
                                 nulls=args.nulls, seed=args.seed)
        checks = [
            (noise.valid and not noise.structure_present,
             "random-luminance clip  -> structure ABSENT (honest anchor)"),
            (structured.valid and structured.structure_present,
             "structured luma clip   -> structure PRESENT"),
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

    if not args.video:
        parser.error("provide a video path, or use --self-test")
    result = score_video(args.video, consent=bool(args.consent), provenance=args.provenance,
                        nulls=args.nulls, seed=args.seed)
    d = result.to_dict()
    print(f"  video            : {args.video}")
    print(f"  n_tones          : {d['n_tones']}")
    print(f"  valid / blocked  : {d['valid']} / {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  test_A_p/test_B_p: {d['test_A_p']} / {d['test_B_p']}")
    print(f"  reason           : {d['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
