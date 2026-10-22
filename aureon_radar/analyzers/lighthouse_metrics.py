"""Reusable metrics engine for Lighthouse Protocol analytics."""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy.signal import welch


@dataclass(frozen=True)
class LighthouseBands:
    lighthouse: float
    distortion: float
    gamma: float


class LighthouseMetricsEngine:
    """Headless computation of Lighthouse Protocol spectral metrics."""

    def __init__(
        self,
        restoration_freq: float = 528.0,
        distortion_freq: float = 440.0,
        epsilon: float = 1e-12,
    ) -> None:
        self.restoration_freq = restoration_freq
        self.distortion_freq = distortion_freq
        self.interference_ratio = distortion_freq / restoration_freq if restoration_freq else 0.0
        self.epsilon = epsilon

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_arrays(timestamps: Sequence[float], values: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
        ts = np.asarray(timestamps, dtype=float)
        vals = np.asarray(values, dtype=float)
        if ts.ndim != 1 or vals.ndim != 1:
            raise ValueError("timestamps and values must be 1-D sequences")
        if ts.size != vals.size:
            raise ValueError("timestamps and values must have the same length")
        if ts.size < 8:
            raise ValueError("at least 8 samples required for spectral analysis")
        order = np.argsort(ts)
        ts = ts[order]
        vals = vals[order]
        return ts, vals

    @staticmethod
    def _infer_sampling_rate(timestamps: np.ndarray) -> float:
        diffs = np.diff(timestamps)
        positive = diffs[diffs > 0]
        if positive.size == 0:
            return 1.0
        median_dt = float(np.median(positive))
        return 1.0 / median_dt if median_dt > 0 else 1.0

    @staticmethod
    def _band_power(freqs: np.ndarray, psd: np.ndarray, band: Tuple[float, float]) -> float:
        lo, hi = band
        if lo >= hi:
            return 0.0
        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            return 0.0
        return float(np.trapezoid(psd[mask], freqs[mask]))

    @staticmethod
    def _log_returns(values: np.ndarray) -> np.ndarray:
        shifted = np.roll(values, 1)
        shifted[0] = values[0]
        safe_vals = np.maximum(values, 1e-9)
        safe_shifted = np.maximum(shifted, 1e-9)
        returns = np.log(safe_vals / safe_shifted)
        return returns[1:]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def map_score_to_emotion(self, score: float) -> Tuple[str, str]:
        if score > 0.9:
            return "AWE (Resonant)", "purple"
        if score > 0.7:
            return "LOVE (528Hz)", "blue"
        if score > 0.4:
            return "GRATITUDE", "green"
        if score > 0.2:
            return "FEAR (Dissonant)", "orange"
        return "ANGER (Chaotic)", "red"

    def analyze_series(
        self,
        timestamps: Sequence[float],
        values: Sequence[float],
        sampling_rate: Optional[float] = None,
        detrend: bool = True,
        nperseg: Optional[int] = None,
    ) -> Mapping[str, object]:
        ts, vals = self._ensure_arrays(timestamps, values)
        raw_vals = vals.copy()

        if detrend:
            vals = vals - np.mean(vals)

        fs = sampling_rate if sampling_rate and sampling_rate > 0 else self._infer_sampling_rate(ts)
        nyquist = fs / 2.0
        if nyquist <= 0:
            raise ValueError("sampling rate must be positive")

        segment = nperseg or min(len(vals), 512)
        if segment < 8:
            segment = len(vals)
        freqs, psd = welch(vals, fs=fs, nperseg=segment)

        total_power = max(float(np.trapezoid(psd, freqs)), self.epsilon)
        low_band = (0.0, 0.1 * nyquist)
        distortion_center = min(max(self.interference_ratio * nyquist, 0.0), nyquist)
        distortion_half_width = 0.08 * nyquist
        distortion_band = (
            max(distortion_center - distortion_half_width, 0.0),
            min(distortion_center + distortion_half_width, nyquist),
        )
        gamma_band = (0.6 * nyquist, nyquist)

        lighthouse_power = self._band_power(freqs, psd, low_band)
        distortion_power = self._band_power(freqs, psd, distortion_band)
        gamma_power = self._band_power(freqs, psd, gamma_band)

        coherence_score = lighthouse_power / total_power
        gamma_ratio = gamma_power / total_power
        distortion_index = distortion_power / max(lighthouse_power + distortion_power, self.epsilon)

        returns = self._log_returns(raw_vals)
        maker_bias = float(np.mean(returns >= 0)) if returns.size else 0.5

        emotion, color = self.map_score_to_emotion(coherence_score)

        return {
            "freqs": freqs,
            "psd": psd,
            "sampling_rate": fs,
            "band_powers": LighthouseBands(
                lighthouse=lighthouse_power,
                distortion=distortion_power,
                gamma=gamma_power,
            ),
            "coherence_score": float(coherence_score),
            "gamma_ratio": float(gamma_ratio),
            "distortion_index": float(distortion_index),
            "maker_bias": float(maker_bias),
            "emotion": emotion,
            "emotion_color": color,
        }
