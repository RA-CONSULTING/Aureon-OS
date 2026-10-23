"""P3 direction proof: predicted volatility can lower the canonical field (b46).

The sentinel enters Λ(t) as SAFETY = 1 − risk. Γ = 1 − |σ/μ| over reading
VALUES, so a low-safety reading among otherwise-agreeing sources strictly
lowers Γ. reconcile_gamma returns the caller's figure and does not impose
that lower gamma as an order floor.
This file proves each link with the REAL engine and the REAL field reader:

  1. LambdaEngine.step — Γ strictly lower with the low-SAFETY reading present;
  2. the mapper — no_data → None, never a neutral placeholder (Γ ignores
     confidence, so a substituted 0.5 would move the canonical field);
  3. end-to-end — a canonical trace row does not replace the local figure
     at reconcile_gamma.
"""

from __future__ import annotations

import json
import time

import pytest

from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
from aureon.core.hnc_live_daemon import _map_volatility_sentinel
from aureon.intelligence.volatility_sentinel import (
    FactorReading,
    VolatilityAssessment,
)

# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Isolate every persistence seam a test here can touch: the engine's
    lambda_history.json, the bus trace dir, the daemon trace path, and the
    process-global thought-bus singleton (same pattern as
    tests/test_hnc_field_freshness.py — no importlib.reload)."""
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_live_trace.jsonl"))

    import sys

    import aureon.core.aureon_thought_bus as tb

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    bare = sys.modules.get("aureon_thought_bus")
    if bare is not None and bare is not tb:
        monkeypatch.setattr(bare, "_thought_bus_instance", None, raising=False)
    return tmp_path


def _engine(tmp_path) -> LambdaEngine:
    eng = LambdaEngine()
    # Never write the repo's state/lambda_history.json from a test.
    eng._state_path = tmp_path / "lambda_history.json"
    return eng


def _readings(*values: float) -> list[SubsystemReading]:
    return [
        SubsystemReading(name=f"src_{i}", value=v, confidence=0.9, state="test")
        for i, v in enumerate(values)
    ]


# ── 1. engine direction ─────────────────────────────────────────────────────


def test_low_safety_reading_strictly_lowers_gamma(isolated):
    base = (0.85, 0.90, 0.88, 0.87)

    eng_hi = _engine(isolated)
    gamma_hi = eng_hi.step(_readings(*base)).coherence_gamma

    eng_lo = _engine(isolated)
    low_safety = SubsystemReading(
        name="volatility_sentinel", value=0.10, confidence=0.9,
        state="risk=0.90;factors=ewma_vol,phase_transition",
    )
    gamma_lo = eng_lo.step(_readings(*base) + [low_safety]).coherence_gamma

    assert gamma_lo < gamma_hi, (
        "a predicted-volatility (low SAFETY) reading must strictly lower Γ"
    )


def test_high_safety_reading_does_not_collapse_gamma(isolated):
    """Sanity bound: an AGREEING safety reading (calm prediction) leaves Γ high —
    the tightening comes from disagreement with a stressed sentinel, not from
    the source's mere presence."""
    base = (0.85, 0.90, 0.88, 0.87)
    eng = _engine(isolated)
    calm = SubsystemReading(
        name="volatility_sentinel", value=0.88, confidence=0.9, state="risk=0.12")
    gamma = eng.step(_readings(*base) + [calm]).coherence_gamma
    assert gamma > 0.9


# ── 2. mapper honesty ───────────────────────────────────────────────────────


def test_map_no_data_is_none_never_a_placeholder():
    a = VolatilityAssessment(
        status="no_data", volatility_risk=None, confidence=0.0,
        factors=(), blockers=("ewma_vol: no prices",), symbol=None, ts=time.time(),
    )
    assert _map_volatility_sentinel(a) is None
    assert _map_volatility_sentinel(None) is None


def test_map_ok_assessment_is_safety_inverted():
    a = VolatilityAssessment(
        status="ok", volatility_risk=0.75, confidence=0.55,
        factors=(FactorReading("ewma_vol", 0.75, 0.35, "ok", "ratio=2.4"),),
        blockers=(), symbol=None, ts=time.time(),
    )
    r = _map_volatility_sentinel(a)
    assert r is not None
    assert r.name == "volatility_sentinel"
    assert r.value == pytest.approx(0.25)   # SAFETY = 1 − risk
    assert r.confidence == pytest.approx(0.55)
    assert "risk=0.75" in r.state and "ewma_vol" in r.state


# ── 3. end-to-end: tightened Γ reaches the gate seam ────────────────────────


def test_reconcile_gamma_keeps_the_local_figure(isolated):
    """A canonical gamma does not replace the local figure, lower or higher."""
    from aureon.core.hnc_field import reconcile_gamma

    trace = isolated / "hnc_live_trace.jsonl"
    observed_at = time.time()
    from tests.hnc_live_envelope import live_field_envelope

    row = live_field_envelope(
        0.71,
        0.42,  # the tightened field
        0.66,
        provider_receipt="provider:volatility:1",
        source_timestamp=observed_at - 1.0,
        received_at=observed_at,
        ts=observed_at - 1.0,
        consciousness_level="CONNECTED",
        lambda_t=0.66,
    )
    trace.write_text(json.dumps(row) + "\n", encoding="utf-8")

    assert reconcile_gamma(0.93) == pytest.approx(0.93)
    assert reconcile_gamma(0.30) == pytest.approx(0.30)


def test_reconcile_gamma_passes_through_when_field_dark(isolated):
    """No trace, no pulse → the local figure passes unchanged (offline-safe,
    nothing substituted)."""
    from aureon.core.hnc_field import reconcile_gamma

    assert reconcile_gamma(0.77) == pytest.approx(0.77)
