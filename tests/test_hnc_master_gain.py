import math
import subprocess
import sys

import numpy as np
import pytest

from aureon.harmonic import hnc_master_gain as mg
from aureon.harmonic import hnc_photon_feedback_loop as pfl


def test_claim_state_is_hold():
    assert mg.CLAIM_STATE == "HOLD"
    assert mg.gain_at_frequency(1.45e14).claim_state == "HOLD"


def test_landmarks_come_from_the_photon_module_not_new_numbers():
    lms = mg.landmark_gains()
    assert list(lms) == ["peak_gain", "max_loss", "recovery"]
    for key, v in lms.items():
        src = pfl.PAPER_REPORTED_LANDMARKS[key]
        assert v["frequency_hz"] == src["frequency_hz"]
        assert v["deviation_pct"] == src["deviation_pct"]
    assert lms["peak_gain"]["lines"] == "82-83"
    assert lms["max_loss"]["lines"] == "89"
    assert lms["recovery"]["lines"] == "94-95"


def test_landmark_gains_and_range():
    lms = mg.landmark_gains()
    assert lms["peak_gain"]["g"] == pytest.approx(1.30)
    assert lms["max_loss"]["g"] == pytest.approx(0.9821)
    assert lms["recovery"]["g"] == pytest.approx(1.0)
    assert mg.gain_range() == (pytest.approx(0.9821), pytest.approx(1.30))


def test_g_is_not_a_constant_and_is_not_the_papers_1_5():
    gs = {mg.gain_at_frequency(f).g for f in (1.45e14, 1e15, 9.12e15, 1e16)}
    assert len(gs) > 1
    assert all(g != 1.5 for g in gs)


def test_exact_at_landmarks_with_paper_source():
    r = mg.gain_at_frequency(9.12e15)
    assert r.g == pytest.approx(0.9821) and r.phase == "loss"
    assert r.source == "paper landmark, line 89"
    assert mg.gain_at_frequency(1.45e14).phase == "gain"
    assert mg.gain_at_frequency(1e16).phase == "recovery"


def test_between_landmarks_is_labelled_interpolation_and_bounded():
    for f in np.logspace(math.log10(1.45e14), math.log10(1e16), 25)[1:-1]:
        r = mg.gain_at_frequency(float(f))
        if r.source.startswith("paper landmark"):
            continue
        assert r.source == mg.INTERPOLATION_SOURCE
        lo, hi = mg.gain_range()
        assert lo - 1e-12 <= r.g <= hi + 1e-12
    # log-midpoint between gain and loss landmarks is the mean of their g
    mid = 10 ** ((math.log10(1.45e14) + math.log10(9.12e15)) / 2)
    assert mg.gain_at_frequency(mid).g == pytest.approx((1.30 + 0.9821) / 2)


@pytest.mark.parametrize("f", [1e14, 1.0e12, 1.01e16, 0.0, -1.0, float("nan"), float("inf")])
def test_refuses_outside_span_or_bad_input(f):
    with pytest.raises(ValueError):
        mg.gain_at_frequency(f)


def test_gain_from_deviation_pct():
    assert mg.gain_from_deviation_pct(30.0) == pytest.approx(1.3)
    arr = mg.gain_from_deviation_pct([0.0, -1.79, 30.0])
    assert np.allclose(arr, [1.0, 0.9821, 1.3])
    for bad in (-100.0, -150.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            mg.gain_from_deviation_pct(bad)


def test_import_has_no_side_effects_and_no_randomness():
    code = (
        "import sys, random; s = random.getstate();"
        "import aureon.harmonic.hnc_master_gain as m;"
        "assert random.getstate() == s;"
        "assert 'requests' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
    with open(mg.__file__, encoding="utf-8") as fh:
        src = fh.read().lower()
    assert "import random" not in src and "np.random" not in src
