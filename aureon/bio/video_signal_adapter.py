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
decode a real video file. Controlled generated clips live exclusively in the test
package. No network, no import-time side effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio.derived_nulls import derived_null_generator
from aureon.bio.human_harmonic_proxy import (
    SCIENTIFIC_BOUNDARY,
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)

__all__ = [
    "VideoControlEnvelope",
    "VideoHumanSignal",
    "VideoSignalAdapter",
    "control_video",
    "score_video",
    "synthetic_video",
    "main",
]

PHI: float = float(engine.PHI)
_CONTROL_PREFIX = "bio.control.video."


@dataclass(frozen=True, slots=True)
class VideoControlEnvelope:
    """Immutable generated-video control with explicit non-operational provenance."""

    frame_bytes: bytes
    shape: tuple[int, ...]
    frame_rate_hz: float
    provenance: str
    data_origin: str = "derived_statistical_control"
    truth_status: str = "statistical_control"
    generated_values: bool = True
    control_only: bool = True
    live_data: bool = False
    provider_observation: bool = False
    operational_eligible: bool = False
    action_eligible: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    provider_eligible: bool = False

    def as_frames(self) -> np.ndarray:
        frames = np.frombuffer(self.frame_bytes, dtype="<f8").reshape(self.shape)
        if frames.flags.writeable:
            raise ValueError("video control storage must remain read-only")
        return frames


@dataclass(frozen=True)
class VideoHumanSignal(HumanSignal):
    """HumanSignal carrying the immutable video-control classification."""

    data_origin: str = "derived_signal_analysis"
    truth_status: str = "derived_analysis"
    generated_values: bool = False
    live_data: bool | None = None
    provider_observation: bool = False
    operational_eligible: bool = False
    action_eligible: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    provider_eligible: bool = False


def _finite_positive(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be finite and positive")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be finite and positive") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{label} must be finite and positive")
    return number


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if number <= 0 or number != value:
        raise ValueError(f"{label} must be a positive integer")
    return number


def _freeze_control(
    frames: Any,
    *,
    frame_rate_hz: Any,
    provenance: str,
) -> VideoControlEnvelope:
    if not provenance.startswith(_CONTROL_PREFIX):
        raise ValueError("video control provenance must use bio.control.video")
    array = np.asarray(frames, dtype="<f8")
    if array.ndim < 1 or array.shape[0] < 4 or not np.all(np.isfinite(array)):
        raise ValueError("video control frames must be complete finite values")
    contiguous = np.ascontiguousarray(array, dtype="<f8")
    return VideoControlEnvelope(
        frame_bytes=contiguous.tobytes(order="C"),
        shape=tuple(int(value) for value in contiguous.shape),
        frame_rate_hz=_finite_positive(frame_rate_hz, "frame_rate_hz"),
        provenance=provenance,
    )


def _validate_control(value: VideoControlEnvelope) -> None:
    false_fields = (
        value.live_data,
        value.provider_observation,
        value.operational_eligible,
        value.action_eligible,
        value.actionable,
        value.accounting_eligible,
        value.learning_eligible,
        value.provider_eligible,
    )
    if (
        not value.provenance.startswith(_CONTROL_PREFIX)
        or value.data_origin != "derived_statistical_control"
        or value.truth_status != "statistical_control"
        or value.generated_values is not True
        or value.control_only is not True
        or any(field is not False for field in false_fields)
    ):
        raise ValueError("invalid or relabelled video control envelope")
    _finite_positive(value.frame_rate_hz, "frame_rate_hz")
    frames = value.as_frames()
    if frames.ndim < 1 or frames.shape[0] < 4 or not np.all(np.isfinite(frames)):
        raise ValueError("invalid video control frames")

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
    def require_frame_rate(value: Any) -> float:
        try:
            fps = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("no_data: a finite positive provider frame rate is required") from exc
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError("no_data: a finite positive provider frame rate is required")
        return fps

    if isinstance(spec, VideoControlEnvelope):
        _validate_control(spec)
        fps = require_frame_rate(spec.frame_rate_hz)
        if frame_rate_hz is not None and require_frame_rate(frame_rate_hz) != fps:
            raise ValueError("frame_rate_hz cannot relabel a frozen video control")
        return spec.as_frames(), fps

    if isinstance(spec, tuple) and len(spec) == 2 and not isinstance(spec[0], (str, Path)):
        frames, fps = spec
        return np.asarray(frames), require_frame_rate(fps)

    if isinstance(spec, (str, Path)):
        try:
            import imageio
        except Exception as exc:  # noqa: BLE001
            raise ImportError(
                "imageio is required to decode video files "
                "(`pip install imageio[ffmpeg]`); the pure proxy core does not need it."
            ) from exc
        reader = imageio.get_reader(str(spec))
        try:
            metadata = reader.get_meta_data()
            metadata_fps = metadata.get("fps") if isinstance(metadata, dict) else None
            fps = require_frame_rate(metadata_fps if metadata_fps is not None else frame_rate_hz)
            frames = np.stack([np.asarray(fr) for fr in reader])
        finally:
            reader.close()
        return frames, fps

    if isinstance(spec, np.ndarray):
        if frame_rate_hz is None:
            raise ValueError("frame_rate_hz is required when passing a raw frame stack")
        return spec, require_frame_rate(frame_rate_hz)

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
    ) -> VideoHumanSignal:
        """Return a :class:`HumanSignal` (modality='video') of folded modulation tones."""
        frames, fps = _load_frames(spec, frame_rate_hz=frame_rate_hz)
        control: VideoControlEnvelope | None
        if isinstance(spec, VideoControlEnvelope):
            control = spec
        elif isinstance(spec, (str, Path)):
            control = None
        else:
            control = _freeze_control(
                frames,
                frame_rate_hz=fps,
                provenance=f"{_CONTROL_PREFIX}unverified_input",
            )
            frames = control.as_frames()
        luma = _frames_to_luma(frames)
        raw_hz = _dominant_video_hz(luma, frame_rate_hz=fps, max_peaks=max_peaks)
        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        label = f"video:{Path(spec).name}" if isinstance(spec, (str, Path)) else "video:control"
        declared = bool(str(provenance).strip())
        return VideoHumanSignal(
            label=label,
            frequencies_hz=tones,
            provenance=control.provenance if control is not None else provenance,
            consent=consent is True and declared,
            modality=self.modality,
            notes=(
                f"{len(tones)} dominant per-frame-luma mode(s); global per-frame luminance "
                "only (no face/object/pose analysis), not a claim about any person"
            ),
            control_only=control is not None,
            data_origin=(
                control.data_origin if control is not None else "derived_signal_analysis"
            ),
            truth_status=(
                control.truth_status if control is not None else "derived_analysis"
            ),
            generated_values=(
                control.generated_values if control is not None else False
            ),
            live_data=control.live_data if control is not None else None,
            provider_observation=False,
            operational_eligible=False,
            action_eligible=False,
            actionable=False,
            accounting_eligible=False,
            learning_eligible=False,
            provider_eligible=False,
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


def control_video(
    kind: str = "noise",
    *,
    seed: int = 0,
    frame_rate_hz: float = 4000.0,
    n_frames: int = 4000,
    h: int = 4,
    w: int = 4,
) -> VideoControlEnvelope:
    """Build a frozen video statistical control under canonical provenance."""
    if isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    try:
        seed_value = int(seed)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("seed must be an integer") from exc
    if seed_value != seed:
        raise ValueError("seed must be an integer")
    fps = _finite_positive(frame_rate_hz, "frame_rate_hz")
    frame_count = _positive_int(n_frames, "n_frames")
    height = _positive_int(h, "h")
    width = _positive_int(w, "w")
    rng = derived_null_generator(seed_value, 13)
    t = np.arange(frame_count, dtype=float) / fps
    if kind == "noise":
        luma = rng.standard_normal(t.size)
    elif kind == "structured":
        base = 1100.0
        centers = np.array([base, base * PHI])
        offsets = np.array([-4.0, 0.0, 4.0])
        tones = (centers[:, None] + offsets[None, :]).ravel()
        if float(np.max(tones)) >= fps / 2.0:
            raise ValueError("frame_rate_hz must preserve the structured control below Nyquist")
        luma = np.zeros_like(t)
        for frequency in tones:
            luma = luma + np.sin(2.0 * np.pi * float(frequency) * t)
        luma = luma + 0.02 * rng.standard_normal(t.size)
    else:
        raise ValueError(f"unknown video control kind {kind!r}")
    frames = np.repeat(
        np.repeat(luma[:, None, None], height, axis=1),
        width,
        axis=2,
    )
    return _freeze_control(
        frames,
        frame_rate_hz=fps,
        provenance=f"{_CONTROL_PREFIX}{kind}",
    )


def synthetic_video(
    kind: str = "noise",
    *,
    seed: int = 0,
    frame_rate_hz: float = 4000.0,
    n_frames: int = 4000,
    h: int = 4,
    w: int = 4,
) -> VideoControlEnvelope:
    return control_video(
        kind=kind,
        seed=seed,
        frame_rate_hz=frame_rate_hz,
        n_frames=n_frames,
        h=h,
        w=w,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: score a real video clip the caller has consent to analyse."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Score a video clip's per-frame-luminance signal (content-agnostic, no face/object analysis)."
    )
    parser.add_argument("video", help="path to a video the caller consents to analyse")
    parser.add_argument("--consent", action="store_true", help="affirm consent to analyse this clip")
    parser.add_argument("--provenance", default="", help="provenance string (required with --consent)")
    parser.add_argument(
        "--frame-rate-hz",
        type=float,
        default=None,
        help="observed frame rate, required only when the file has no frame-rate metadata",
    )
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print("Video signal adapter — per-frame luminance -> dominant frequency -> folded tone (no face analysis)")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")

    result = score_video(args.video, consent=bool(args.consent), provenance=args.provenance,
                        frame_rate_hz=args.frame_rate_hz, nulls=args.nulls, seed=args.seed)
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
