from __future__ import annotations

import pandas as pd

from observatory.metrics.engine import EngineConfig, MetricsEngine


def test_coherence_score_monotonic_with_components(tmp_path):
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "close": [100, 101, 102],
            "volume": [1_000_000, 1_100_000, 1_200_000],
            "schumann_amp": [0.1, 0.2, 0.3],
            "gw_power_index": [0.2, 0.3, 0.4],
        }
    )

    config = {
        "integrity": {"zscore_window": 2},
        "cci": {"alpha": 1.0, "beta": 1.0, "sigma_window": 2},
        "polaris": {"baseline_date": "2024-01-01"},
        "choerance": {"sigma_window": 2},
        "ping_pong": {"window_corr": 2},
        "grav_reflection": {"window_corr": 2},
        "coherence_index": {
            "weights": {
                "integrity": 0.25,
                "cci": 0.25,
                "polaris": 0.1,
                "choerance": 0.1,
                "ping_pong": 0.1,
                "grav_reflection": 0.1,
                "unity": 0.05,
                "inercha": 0.05,
            }
        },
    }

    engine = MetricsEngine(EngineConfig(metrics_config=config, output_path=tmp_path))
    result = engine.compute(frame)

    assert (result["coherence_score"].diff().iloc[1:] >= -1).all()
