"""Validation for the Harmonic Nexus metric fusion helpers."""

import math
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harmonic_nexus_metrics import (
    AuraBioWindow,
    HarmonicNexusParameters,
    SchumannWindow,
    aggregate_windows,
    compute_metrics,
    compute_metrics_from_streams,
    radar_plot,
)


def test_aggregate_windows_returns_parameters():
    schumann = [
        SchumannWindow(7.82, [14.3, 20.8, 27.3, 33.8], 0.9),
        SchumannWindow(7.84, [14.2, 20.9, 27.4, 33.7], 1.1),
    ]
    aura = [
        AuraBioWindow(0.48, 0.33, 0.19, 70.0, 6.0, 9.0),
        AuraBioWindow(0.5, 0.32, 0.18, 66.0, 5.8, 8.8),
    ]

    params = aggregate_windows(schumann, aura)
    assert isinstance(params, HarmonicNexusParameters)
    assert 0.0 <= params.source_potential <= 1.0
    assert 0.0 <= params.nexus_coherence <= 1.0
    assert 0.0 <= params.planetary_resonance <= 1.0
    assert 0.0 <= params.observer_entropy <= 1.0
    assert len(params.force_vector) == 4
    assert all(0.0 <= component <= 1.0 for component in params.force_vector)


def test_compute_metrics_from_streams_matches_direct_call(tmp_path):
    schumann = [
        SchumannWindow(7.83, [14.3, 20.8, 27.3, 33.8], 1.0),
        SchumannWindow(7.81, [14.4, 20.7, 27.2, 33.9], 0.85),
        SchumannWindow(7.85, [14.2, 20.9, 27.5, 33.6], 1.05),
    ]
    aura = [
        AuraBioWindow(0.49, 0.31, 0.20, 68.0, 5.9, 9.4),
        AuraBioWindow(0.47, 0.35, 0.18, 72.0, 6.1, 9.2),
        AuraBioWindow(0.5, 0.34, 0.16, 74.0, 6.0, 8.9),
    ]

    via_wrapper = compute_metrics_from_streams(schumann, aura)
    via_params = compute_metrics(aggregate_windows(schumann, aura))

    assert via_wrapper == pytest.approx(via_params)

    # Ensure the plotting helper can render without displaying a GUI.
    output = tmp_path / "nexus.png"
    radar_plot(via_wrapper, show=False, save_path=output)
    assert output.exists()


@pytest.mark.parametrize(
    "field, expected",
    [
        ("Source Potential", (0.0, 1.0)),
        ("Nexus Coherence", (0.0, 1.0)),
        ("Planetary Resonance", (0.0, 1.0)),
        ("Observer Entropy", (0.0, 1.0)),
        ("Unity Metric", (0.0, 4.0)),
    ],
)
def test_metric_ranges(field, expected):
    params = HarmonicNexusParameters(0.6, 0.75, 0.8, (0.7, 0.5, 0.9, 0.6), 0.3)
    metrics = compute_metrics(params)
    low, high = expected
    assert low <= metrics[field] <= high

    if field == "Unity Metric":
        # Unity Metric scales with coherence; confirm behaviour explicitly.
        params_high = HarmonicNexusParameters(0.6, 1.0, 0.8, (1.0, 1.0, 1.0, 1.0), 0.3)
        unity_high = compute_metrics(params_high)[field]
        assert math.isclose(unity_high, 4.0)
