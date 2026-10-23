"""Trading detection interfaces that wrap the QGITA pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence

import numpy as np

from qgita_pipeline import (
    compute_lighthouse_metrics,
    detect_ftcps,
    detect_lhes,
    segma_cluster,
)


@dataclass(frozen=True)
class LighthouseEvent:
    """Represents a Lighthouse consensus flash detected by QGITA."""

    time: float
    intensity: float
    curvature: float
    ratio: float
    g_eff: float


class QGITADetector:
    """High level interface over the QGITA anomaly detection pipeline.

    The original :mod:`qgita_pipeline` module exposes a collection of functions that
    work on numpy arrays.  The trading bot consumes a more structured summary, so we
    wrap the pipeline inside this class to provide a deterministic, testable API.
    """

    def __init__(
        self,
        base_dt: float = 1.0,
        fib_tolerance: float = 0.04,
        curvature_threshold: float = 10.0,
        segma_radius: float = 0.5,
        lighthouse_sigma: float = 2.0,
        link_window: float = 0.2,
        metric_weights: Sequence[float] | None = None,
    ) -> None:
        self.base_dt = base_dt
        self.fib_tolerance = fib_tolerance
        self.curvature_threshold = curvature_threshold
        self.segma_radius = segma_radius
        self.lighthouse_sigma = lighthouse_sigma
        self.link_window = link_window
        self.metric_weights = np.array(metric_weights) if metric_weights is not None else None

    def _prepare_signal(self, signal: Iterable[Iterable[float]]) -> np.ndarray:
        array = np.asarray(signal, dtype=float)
        if array.ndim == 1:
            array = array[np.newaxis, :]
        if array.ndim != 2:
            raise ValueError("Signal must be 1D or 2D array-like")
        return array

    def detect(
        self,
        times: Sequence[float],
        signal: Iterable[Iterable[float]],
    ) -> Dict[str, object]:
        """Run the full detection pipeline.

        Parameters
        ----------
        times:
            Sequence of timestamps aligned with the signal samples.
        signal:
            Either a single price/feature stream or a set of stacked channels.

        Returns
        -------
        Dict[str, object]
            A dictionary containing the FTCP candidates, lighthouse metric series and
            a list of :class:`LighthouseEvent` instances.
        """

        times_arr = np.asarray(times, dtype=float)
        if times_arr.ndim != 1:
            raise ValueError("`times` must be a one-dimensional sequence")
        signal_arr = self._prepare_signal(signal)
        if signal_arr.shape[1] != times_arr.size:
            raise ValueError("Signal length and time vector must match")

        energy_envelope = np.sqrt(np.mean(signal_arr**2, axis=0))
        ftcps = detect_ftcps(
            times_arr,
            energy_envelope,
            base_dt=self.base_dt,
            tolerance=self.fib_tolerance,
            threshold=self.curvature_threshold,
        )
        segma_candidates = segma_cluster(ftcps, eps_seconds=self.segma_radius)
        weights = self.metric_weights if self.metric_weights is not None else np.ones(5)
        metrics = compute_lighthouse_metrics(times_arr, signal_arr, segma_candidates, metric_weights=weights)
        lhes, threshold = detect_lhes(
            metrics["L"],
            times_arr,
            segma_candidates,
            k_sigma=self.lighthouse_sigma,
            window=self.link_window,
        )

        events = [
            LighthouseEvent(
                time=float(lhe["t"]),
                intensity=float(lhe["L"]),
                curvature=float(lhe["linked_ftcp"]["kappa"]),
                ratio=float(lhe["linked_ftcp"]["r"]),
                g_eff=float(lhe["linked_ftcp"]["G"]),
            )
            for lhe in lhes
        ]

        return {
            "times": times_arr,
            "metrics": metrics,
            "ftcps": segma_candidates,
            "threshold": float(threshold),
            "events": events,
        }


__all__ = ["QGITADetector", "LighthouseEvent"]
