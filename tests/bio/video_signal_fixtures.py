"""Controlled generated frame stacks for video-adapter tests only."""

from __future__ import annotations

import numpy as np

from aureon.bio.derived_nulls import derived_null_generator
import phenolic_fingerprint as engine


def video_fixture(
    kind: str = "noise",
    *,
    seed: int = 0,
    frame_rate_hz: float = 4000.0,
    n_frames: int = 4000,
    height: int = 4,
    width: int = 4,
) -> tuple[np.ndarray, float]:
    """Return deterministic generated frames used only as a scientific control."""
    rng = derived_null_generator(int(seed), 13)
    t = np.arange(int(n_frames)) / float(frame_rate_hz)
    if kind == "noise":
        luma = rng.standard_normal(t.size)
    elif kind == "structured":
        base = 1100.0
        centers = np.array([base, base * float(engine.PHI)])
        offsets = np.array([-4.0, 0.0, 4.0])
        tones = (centers[:, None] + offsets[None, :]).ravel()
        luma = np.zeros_like(t)
        for frequency in tones:
            luma = luma + np.sin(2.0 * np.pi * float(frequency) * t)
        luma = luma + 0.02 * rng.standard_normal(t.size)
    else:
        raise ValueError(f"unknown fixture kind {kind!r}")
    frames = np.repeat(
        np.repeat(luma[:, None, None], height, axis=1),
        width,
        axis=2,
    )
    return frames, float(frame_rate_hz)
