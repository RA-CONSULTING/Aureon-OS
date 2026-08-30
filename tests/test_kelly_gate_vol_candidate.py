"""Kelly gate third candidate (P4): predicted vol-safety joins the min — tighten-only.

``_resolve_auto_observer_coherence`` reconciles the observer's rock coherence,
the canonical field's Γ, and now the sentinel's vol_safety = 1 − risk via
``min()``. A min over a SUPERSET of candidates can only be ≤ the previous min —
proven here both ways: the sentinel can tighten, and with the sentinel dark the
result is byte-identical to the pre-P4 formula. DRY_RUN stays bit-identical
(None regardless of candidates).
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from aureon.intelligence.volatility_sentinel import (
    VOL_MIN_CONFIDENCE_KELLY,
    FactorReading,
    VolatilityAssessment,
)
from aureon.utils.adaptive_prime_profit_gate import _resolve_auto_observer_coherence

_FIELD = "aureon.core.hnc_field.read_canonical_field"
_OBSERVER = "aureon.observer.get_observer"
_SCALING = "aureon.observer.production_mode.kelly_buffer_scaling_active"
_SEAM = "aureon.intelligence.volatility_sentinel.read_latest_assessment"


def _field(gamma: float):
    from aureon.core.hnc_field import CanonicalField

    return CanonicalField(available=True, symbolic_life_score=gamma,
                          coherence_gamma=gamma, lambda_t=1.0, source="test")


def _assessment(risk: float, confidence: float = 0.55) -> VolatilityAssessment:
    return VolatilityAssessment(
        status="ok", volatility_risk=risk, confidence=confidence,
        factors=(FactorReading("ewma_vol", risk, 0.35, "ok", ""),),
        blockers=(), symbol=None, ts=time.time(),
    )


def _resolve(gamma: float, assessment) -> float | None:
    with patch(_FIELD, lambda *a, **k: _field(gamma)), \
         patch(_OBSERVER, lambda *a, **k: None), \
         patch(_SCALING, lambda *a, **k: True), \
         patch(_SEAM, lambda *a, **k: assessment):
        return _resolve_auto_observer_coherence()


def test_vol_safety_tightens_below_canonical_gamma():
    score = _resolve(gamma=0.90, assessment=_assessment(risk=0.70))
    assert score == pytest.approx(0.30), "vol_safety = 1 − 0.70 must win the min"


def test_superset_min_is_tighten_only():
    """For the same field, adding the sentinel candidate can never RAISE the score."""
    without = _resolve(gamma=0.60, assessment=None)
    with_calm = _resolve(gamma=0.60, assessment=_assessment(risk=0.10))
    with_stress = _resolve(gamma=0.60, assessment=_assessment(risk=0.80))
    assert without == pytest.approx(0.60)
    assert with_calm is not None and with_calm <= without
    assert with_stress is not None and with_stress <= without
    assert with_stress == pytest.approx(0.20)


def test_no_sentinel_is_byte_identical_regression():
    """Sentinel dark (None) → exactly the pre-P4 result: min(observer, canonical Γ)."""
    assert _resolve(gamma=0.42, assessment=None) == pytest.approx(0.42)


def test_thin_confidence_assessment_is_ignored():
    thin = _assessment(risk=0.90, confidence=0.20)
    assert thin.confidence < VOL_MIN_CONFIDENCE_KELLY
    assert _resolve(gamma=0.75, assessment=thin) == pytest.approx(0.75)


def test_no_data_assessment_is_ignored():
    dark = VolatilityAssessment(
        status="no_data", volatility_risk=None, confidence=0.0,
        factors=(), blockers=("ewma_vol: no prices",), symbol=None, ts=time.time(),
    )
    assert _resolve(gamma=0.75, assessment=dark) == pytest.approx(0.75)


def test_dry_run_returns_none_regardless_of_sentinel():
    """Non-LIVE modes keep the pre-observer multiplier — bit-identical sizing."""
    with patch(_FIELD, lambda *a, **k: _field(0.90)), \
         patch(_OBSERVER, lambda *a, **k: None), \
         patch(_SCALING, lambda *a, **k: False), \
         patch(_SEAM, lambda *a, **k: _assessment(risk=0.95)):
        assert _resolve_auto_observer_coherence() is None


def test_audit_carries_sentinel_keys(monkeypatch):
    rows: list = []
    monkeypatch.setattr("aureon.observer.production_mode.audit",
                        lambda event, payload, **kw: rows.append((event, payload)))
    _resolve(gamma=0.90, assessment=_assessment(risk=0.70))
    kelly = [r for r in rows if r[0] == "kelly_buffer_evaluation"]
    assert kelly
    payload = kelly[0][1]
    assert payload["volatility_sentinel_risk"] == pytest.approx(0.70)
    assert payload["volatility_sentinel_safety"] == pytest.approx(0.30)
