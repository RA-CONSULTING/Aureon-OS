"""Unit tests for the control/null calibration validator."""

from __future__ import annotations

from pathlib import Path

import pytest

import calibration
import phenolic_fingerprint as pf

_CSV = (
    "molecule,peak_value,unit,rel_intensity,source\n"
    + "".join(
        f"m1,{v},cm^-1,m,doi:x\n" for v in (1603, 1632, 1160, 1444, 1517, 1606, 1682, 1300)
    )
    + "".join(f"m2,{v},cm^-1,m,doi:y\n" for v in (1624, 1607, 1594, 1582, 1567, 1660))
)


def _write(tmp_path: Path) -> Path:
    p = tmp_path / "cal.csv"
    p.write_text(_CSV, encoding="utf-8")
    return p


def test_calibrate_returns_report_and_preserves_alpha(tmp_path):
    alpha_before = pf.ALPHA
    report = calibration.calibrate([_write(tmp_path)], nulls=40, seed=0, fpr_trials=20)
    assert report.alpha == pf.ALPHA == alpha_before  # thresholds untouched
    assert 0.0 <= report.empirical_fpr_separable <= 1.0
    assert report.n_compounds == 2
    assert report.controls_valid is True


def test_calibrate_deterministic(tmp_path):
    p = _write(tmp_path)
    r1 = calibration.calibrate([p], nulls=40, seed=0, fpr_trials=20)
    r2 = calibration.calibrate([p], nulls=40, seed=0, fpr_trials=20)
    assert r1.to_dict() == r2.to_dict()


def test_calibrate_requires_testable_compound(tmp_path):
    p = tmp_path / "single.csv"
    p.write_text("molecule,peak_value,unit,rel_intensity,source\nlonely,1600,cm^-1,m,doi:z\n",
                 encoding="utf-8")
    with pytest.raises(ValueError):
        calibration.calibrate([p], nulls=20, seed=0, fpr_trials=5)
