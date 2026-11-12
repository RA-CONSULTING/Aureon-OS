"""Hand-worked checks for aureon.harmonic.hnc_photon_feedback_loop.

Paper line numbers refer to the plain-text copy of Leckey, "The Harmonic Nexus
Core".  Every expected number below is worked by hand in the comment beside
it; the shape parameters are round test values, not values tuned to the
paper's landmarks.  Claim state HOLD.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pytest

from aureon.harmonic import hnc_photon_feedback_loop as pf

MODULE = Path(pf.__file__)

# Round test values only (none comes from the paper; the paper gives none).
PARAMS = pf.PhotonFeedbackParams(
    fwm_peak_gain=0.2,
    fwm_peak_hz=1.0e14,
    fwm_width_decades=0.5,
    absorption_onset_hz=1.0e15,
    tpa_coefficient=0.01,
    fca_coefficient=0.01,
    loss_saturation=0.02,
    surge_relaxation=1.0,
)


def test_e_ideal_is_h_times_f_line_70():
    # h = 6.62607015e-34 J s (exact SI).  1e12 Hz -> 6.62607015e-22 J,
    # 1e15 Hz -> 6.62607015e-19 J, 1e16 Hz -> 6.62607015e-18 J.
    e = pf.photon_energy_ideal([1e12, 1e15, 1e16])
    assert e == pytest.approx([6.62607015e-22, 6.62607015e-19, 6.62607015e-18], rel=1e-15)


def test_sweep_is_1thz_to_10phz_at_90ghz_lines_67_69():
    # (1e16 - 1e12) / 9e10 = 9.999e15 / 9e10 = 111100 steps -> 111101 points,
    # last point 1e12 + 111100 * 9e10 = 1e16.
    f = pf.frequency_sweep()
    assert f.size == 111101
    assert f[0] == 1e12
    assert f[1] - f[0] == 9e10
    assert f[-1] == pytest.approx(1e16, rel=1e-12)


def test_fwm_gain_peak_and_one_width_lines_118_123():
    # At f = f_g the exponent is 0 -> G = 0.2.
    # At f = f_g * 10**0.5 the log10 offset is one width -> 0.2 * exp(-0.5) = 0.12130613...
    g = pf.fwm_gain([1e14, 1e14 * 10**0.5, 1e14 / 10**0.5], PARAMS)
    assert g[0] == pytest.approx(0.2, rel=1e-15)
    assert g[1] == pytest.approx(0.2 * math.exp(-0.5), rel=1e-12)
    assert g[1] == pytest.approx(0.121306132, rel=1e-8)
    assert g[2] == pytest.approx(g[1], rel=1e-12)


def test_tpa_fca_loss_hand_values_and_saturation_lines_124_133_172_191():
    # x = 1:  raw = 0.01*1 + 0.01*1 = 0.02;  L = 0.02 / (1 + 0.02/0.02) = 0.01
    # x = 2:  raw = 0.02 + 0.04 = 0.06;      L = 0.06 / (1 + 3) = 0.015
    # x -> 0: L -> 0;  x -> large: L -> L_sat = 0.02 and never exceeds it.
    loss = pf.tpa_fca_loss([1e15, 2e15, 1e9, 1e20], PARAMS)
    assert loss[0] == pytest.approx(0.01, rel=1e-12)
    assert loss[1] == pytest.approx(0.015, rel=1e-12)
    assert loss[2] == pytest.approx(1e-8, rel=1e-3)  # raw = 0.01*1e-6 + tiny
    assert loss[3] < 0.02 and loss[3] == pytest.approx(0.02, rel=1e-6)
    f = pf.frequency_sweep(1e12, 1e17, 1e14)
    assert np.all(np.diff(pf.tpa_fca_loss(f, PARAMS)) >= 0)


def test_surge_window_recursion_hand_values_lines_136_150():
    # d_0 = 0.1; C_1 = -1*0.5*0.1 = -0.05 -> d_1 = 0.05; C_2 = -0.075 -> d_2 = 0.025; d_3 = 0.0125.
    d = pf.surge_window_sweep([0.1] * 4, [0.5] * 4, 1.0)
    assert d == pytest.approx([0.1, 0.05, 0.025, 0.0125], rel=1e-12)


def test_surge_window_fixed_point_and_stability_bound():
    # d_{n+1} = (1 - kappa*s) d_n.  kappa*s = 1 -> zero after one step.
    assert pf.surge_window_sweep([0.3] * 3, [1.0] * 3, 1.0) == pytest.approx([0.3, 0.0, 0.0], abs=1e-15)
    # kappa*s = 2 -> factor -1: no convergence (edge of stability).
    assert pf.surge_window_sweep([0.1] * 4, [1.0] * 4, 2.0) == pytest.approx([0.1, -0.1, 0.1, -0.1])
    # kappa = 0 or s = 0 -> no restoring term; open loop passes through.
    assert pf.surge_window_sweep([0.1, -0.2], [0.7, 0.7], 0.0) == pytest.approx([0.1, -0.2])
    assert pf.surge_window_sweep([0.1, -0.2], [0.0, 0.0], 1.0) == pytest.approx([0.1, -0.2])


def test_surge_window_is_path_dependent_lines_98_103():
    # Same final input, different history -> different final output.
    a = pf.surge_window_sweep([0.0, 0.0, 0.1], [0.5, 0.5, 0.5], 1.0)
    b = pf.surge_window_sweep([0.2, 0.2, 0.1], [0.5, 0.5, 0.5], 1.0)
    # a: d=0,0,0.1.  b: d0=0.2, C1=-0.1, d1=0.1, C2=-0.15, d2=-0.05.
    assert a[-1] == pytest.approx(0.1)
    assert b[-1] == pytest.approx(-0.05)


def test_modulated_energy_matches_its_parts_lines_71_74():
    f = np.array([1e15, 2e15])
    out = pf.modulated_energy(f, PARAMS)
    # gain at 1e15 is one decade from 1e14, two widths: 0.2*exp(-2); at 2e15:
    # log10(20)/0.5 widths.  loss 0.01, 0.015 (worked above).  s = 0.5, 0.75.
    g0 = 0.2 * math.exp(-2.0)
    z = math.log10(20.0) / 0.5
    g1 = 0.2 * math.exp(-0.5 * z * z)
    d0 = g0 - 0.01
    d1 = (g1 - 0.015) - 1.0 * 0.5 * d0
    assert out["deviation"] == pytest.approx([d0, d1], rel=1e-12)
    assert out["e_mod_j"] == pytest.approx(out["e_ideal_j"] * (1 + out["deviation"]), rel=1e-15)
    assert out["deviation_pct"] == pytest.approx(100 * out["deviation"], rel=1e-9)


def test_no_restoring_term_reduces_to_gain_minus_loss():
    p = pf.PhotonFeedbackParams(**{**PARAMS.__dict__, "surge_relaxation": 0.0})
    f = pf.frequency_sweep(1e12, 1e16, 1e13)
    out = pf.modulated_energy(f, p)
    assert np.array_equal(out["deviation"], out["gain"] - out["loss"])


def test_full_paper_sweep_is_deterministic():
    f = pf.frequency_sweep()
    a = pf.modulated_energy(f, PARAMS)["deviation_pct"]
    b = pf.modulated_energy(f, PARAMS)["deviation_pct"]
    assert np.array_equal(a, b)
    assert np.all(np.isfinite(a))


def test_profile_landmarks_reads_extremes():
    marks = pf.profile_landmarks([1.0, 2.0, 3.0, 4.0], [5.0, 30.0, -2.0, 0.5])
    assert marks["peak_gain"] == {"frequency_hz": 2.0, "deviation_pct": 30.0}
    assert marks["max_loss"] == {"frequency_hz": 3.0, "deviation_pct": -2.0}
    assert marks["recovery"] == {"frequency_hz": 4.0, "deviation_pct": 0.5}
    assert set(marks) == set(pf.PAPER_REPORTED_LANDMARKS)


def test_paper_landmarks_are_recorded_as_reported():
    # lines 82-83, 88-89, 94-95
    assert pf.PAPER_REPORTED_LANDMARKS["peak_gain"] == {"frequency_hz": 1.45e14, "deviation_pct": 30.0}
    assert pf.PAPER_REPORTED_LANDMARKS["max_loss"] == {"frequency_hz": 9.12e15, "deviation_pct": -1.79}
    assert pf.PAPER_REPORTED_LANDMARKS["recovery"] == {"frequency_hz": 1.0e16, "deviation_pct": 0.0}
    assert pf.CLAIM_STATE == "HOLD"


def test_unspecified_constants_have_no_defaults():
    with pytest.raises(TypeError):
        pf.PhotonFeedbackParams()  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        pf.PhotonFeedbackParams(**{**PARAMS.__dict__, "loss_saturation": 0.0})


def test_module_imports_only_math_and_numpy():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "math", "dataclasses", "typing", "numpy"}
    src = MODULE.read_text(encoding="utf-8")
    assert "np.random" not in src and "import random" not in src
