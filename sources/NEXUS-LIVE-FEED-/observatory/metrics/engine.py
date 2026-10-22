"""Metrics engine implementing Integrity, CCI, Polaris ΔCₜ, Choerance, Ping–Pong, Grav, Unity, Inercha, and Coherence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from observatory.metrics.registry import MetricRun, RegistryClient


@dataclass
class EngineConfig:
    metrics_config: Dict[str, object]
    output_path: Path


class MetricsEngine:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config

    def compute(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Compute all Observatory metrics on the provided feature frame."""

        frame = frame.copy()
        frame["integrity_perturbation"] = self._integrity(frame)
        for column in ("flag_volume_spike", "flag_impact", "flag_rv", "flag_benford"):
            if column not in frame:
                frame[column] = False
        frame["CCI"] = self._cci(frame)
        frame["deltaC_polaris"] = self._polaris(frame)
        frame["choerance_phi"] = self._choerance(frame)
        frame["pingpong_corr"] = self._ping_pong(frame)
        frame["grav_corr"] = self._grav(frame)
        frame["unity_index"] = self._unity(frame)
        frame["inercha_speed"] = self._inercha(frame)
        frame["coherence_score"] = self._coherence(frame)
        return frame

    def _integrity(self, frame: pd.DataFrame) -> pd.Series:
        window = int(self.config.metrics_config["integrity"]["zscore_window"])
        volume_z = (frame["volume"] - frame["volume"].rolling(window).mean()) / frame["volume"].rolling(window).std()
        return volume_z.abs().fillna(0.0)

    def _cci(self, frame: pd.DataFrame) -> pd.Series:
        cfg = self.config.metrics_config["cci"]
        delta_p = frame["close"].pct_change().abs()
        delta_v = frame["volume"].pct_change().abs().fillna(0.0)
        sigma = frame["close"].pct_change().rolling(cfg["sigma_window"]).std().fillna(0.0)
        return (delta_p + cfg["alpha"] * delta_v) / (1 + cfg["beta"] * sigma)

    def _polaris(self, frame: pd.DataFrame) -> pd.Series:
        baseline = pd.Timestamp(self.config.metrics_config["polaris"]["baseline_date"])
        baseline_slice = frame.loc[frame["date"] == baseline, "CCI"]
        baseline_value = baseline_slice.mean() if not baseline_slice.empty else frame["CCI"].iloc[0]
        return frame["CCI"] - baseline_value

    def _choerance(self, frame: pd.DataFrame) -> pd.Series:
        sigma = frame["CCI"].rolling(self.config.metrics_config["choerance"]["sigma_window"]).std().fillna(1.0)
        return np.arctan((frame["CCI"] - frame["CCI"].mean()) / sigma)

    def _ping_pong(self, frame: pd.DataFrame) -> pd.Series:
        window = self.config.metrics_config["ping_pong"]["window_corr"]
        return frame["CCI"].rolling(window).corr(frame.get("schumann_amp", pd.Series(index=frame.index))).fillna(0.0)

    def _grav(self, frame: pd.DataFrame) -> pd.Series:
        window = self.config.metrics_config["grav_reflection"]["window_corr"]
        return frame.get("schumann_amp", pd.Series(index=frame.index)).rolling(window).corr(frame.get("gw_power_index", pd.Series(index=frame.index))).fillna(0.0)

    def _unity(self, frame: pd.DataFrame) -> pd.Series:
        vectors = frame[["integrity_perturbation", "CCI", "choerance_phi", "pingpong_corr", "grav_corr"]].fillna(0.0)
        norms = np.linalg.norm(vectors.values, axis=1, keepdims=True)
        normalized = np.divide(vectors.values, norms, out=np.zeros_like(vectors.values), where=norms != 0)
        cosines = normalized @ normalized.T
        return pd.Series(np.nanmean(cosines, axis=1), index=frame.index)

    def _inercha(self, frame: pd.DataFrame) -> pd.Series:
        diff = frame[["integrity_perturbation", "CCI", "choerance_phi", "pingpong_corr", "grav_corr"]].diff().fillna(0.0)
        return np.linalg.norm(diff.values, axis=1)

    def _coherence(self, frame: pd.DataFrame) -> pd.Series:
        weights = self.config.metrics_config["coherence_index"]["weights"]
        components = {
            key: frame[column].fillna(0.0)
            for key, column in {
                "integrity": "integrity_perturbation",
                "cci": "CCI",
                "polaris": "deltaC_polaris",
                "choerance": "choerance_phi",
                "ping_pong": "pingpong_corr",
                "grav_reflection": "grav_corr",
                "unity": "unity_index",
                "inercha": "inercha_speed",
            }.items()
        }
        score = sum(weights[name] * components[name] for name in weights)
        return (score - score.min()) / (score.max() - score.min() + 1e-9)


def build_daily_metrics() -> None:  # pragma: no cover - orchestrated
    """Entry point for orchestration layers."""

    # In practice the feature frame would come from the cleaned zone.
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "close": np.linspace(100, 105, 5),
            "volume": np.linspace(1_000_000, 1_500_000, 5),
            "schumann_amp": np.linspace(0.1, 0.5, 5),
            "gw_power_index": np.linspace(0.2, 0.6, 5),
        }
    )

    client = RegistryClient(Path("/tmp/observatory_registry.json"))
    metrics_config = client.load_metric_config() or {
        "integrity": {"zscore_window": 5},
        "cci": {"alpha": 1.0, "beta": 1.0, "sigma_window": 5},
        "polaris": {"baseline_date": "2024-01-01"},
        "choerance": {"sigma_window": 5},
        "ping_pong": {"window_corr": 3},
        "grav_reflection": {"window_corr": 3},
        "coherence_index": {
            "weights": {
                "integrity": 0.2,
                "cci": 0.2,
                "polaris": 0.15,
                "choerance": 0.15,
                "ping_pong": 0.1,
                "grav_reflection": 0.1,
                "unity": 0.05,
                "inercha": 0.05,
            }
        },
    }
    engine = MetricsEngine(EngineConfig(metrics_config=metrics_config, output_path=Path("/lake/marts")))
    enriched = engine.compute(frame)
    run = MetricRun.from_frame(enriched)
    client.log_run(run)
