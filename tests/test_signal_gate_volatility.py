"""SignalGate volatility veto (P4): predicted volatility blocks entries — honestly.

The 4th SignalGate check reads the sentinel's latest assessment through the real
cross-process seam. It blocks only on a fresh, well-covered, high-risk
assessment AND only when the veto is armed (LIVE); everywhere else it audits
``would_have_blocked``. Missing / thin / low-risk assessments are honest
passthroughs — never a substituted risk.
"""

from __future__ import annotations

import time

import pytest

from aureon.core.aureon_operational_core import SignalGate
from aureon.intelligence.volatility_sentinel import (
    VOL_MIN_CONFIDENCE_GATE,
    VOL_RISK_BLOCK,
    FactorReading,
    VolatilityAssessment,
)

_SEAM = "aureon.intelligence.volatility_sentinel.read_latest_assessment"
_VETO = "aureon.observer.production_mode.volatility_veto_active"
_AUDIT = "aureon.observer.production_mode.audit"


def _assessment(risk: float, confidence: float = 0.6) -> VolatilityAssessment:
    return VolatilityAssessment(
        status="ok", volatility_risk=risk, confidence=confidence,
        factors=(FactorReading("ewma_vol", risk, 0.35, "ok", "ratio=3.1"),
                 FactorReading("phase_transition", risk, 0.25, "ok", "p=0.9")),
        blockers=(), symbol=None, ts=time.time(),
    )


@pytest.fixture()
def audits(monkeypatch):
    rows: list = []
    monkeypatch.setattr(_AUDIT, lambda event, payload, **kw: rows.append((event, payload, kw)))
    return rows


def test_high_risk_blocks_when_armed(monkeypatch, audits):
    monkeypatch.setattr(_SEAM, lambda *a, **k: _assessment(0.92))
    monkeypatch.setattr(_VETO, lambda: True)
    allowed, reason = SignalGate().check_entry_allowed("BTC/USD", 100.0)
    assert allowed is False
    assert "VOLATILITY_PREDICTED" in reason
    assert "ewma_vol" in reason and "phase_transition" in reason, (
        "the veto must name its contributing factors"
    )
    rows = [a for a in audits if a[0] == "signal_gate_volatility_check"]
    assert rows and rows[0][2]["actually_blocked"] is True


def test_high_risk_audits_but_allows_when_not_armed(monkeypatch, audits):
    monkeypatch.setattr(_SEAM, lambda *a, **k: _assessment(0.92))
    monkeypatch.setattr(_VETO, lambda: False)
    allowed, reason = SignalGate().check_entry_allowed("BTC/USD", 100.0)
    assert allowed is True and reason == "CLEAR"
    rows = [a for a in audits if a[0] == "signal_gate_volatility_check"]
    assert rows, "an unarmed veto must still leave a would_have_blocked audit row"
    assert rows[0][2]["would_have_blocked"] is True
    assert rows[0][2]["actually_blocked"] is False


def test_low_risk_passes_without_audit(monkeypatch, audits):
    monkeypatch.setattr(_SEAM, lambda *a, **k: _assessment(0.30))
    monkeypatch.setattr(_VETO, lambda: True)
    allowed, _ = SignalGate().check_entry_allowed("BTC/USD", 100.0)
    assert allowed is True
    assert not [a for a in audits if a[0] == "signal_gate_volatility_check"]


def test_no_assessment_is_honest_passthrough(monkeypatch, audits):
    monkeypatch.setattr(_SEAM, lambda *a, **k: None)  # missing or stale → seam says None
    monkeypatch.setattr(_VETO, lambda: True)
    allowed, _ = SignalGate().check_entry_allowed("BTC/USD", 100.0)
    assert allowed is True
    assert not [a for a in audits if a[0] == "signal_gate_volatility_check"]


def test_thin_coverage_cannot_veto(monkeypatch, audits):
    """A single-factor assessment below the gate's coverage bar must not block
    an order, no matter how loud that one factor is."""
    thin = VolatilityAssessment(
        status="ok", volatility_risk=0.95, confidence=0.35,  # < VOL_MIN_CONFIDENCE_GATE
        factors=(FactorReading("ewma_vol", 0.95, 0.35, "ok", ""),),
        blockers=(), symbol=None, ts=time.time(),
    )
    assert thin.confidence < VOL_MIN_CONFIDENCE_GATE
    monkeypatch.setattr(_SEAM, lambda *a, **k: thin)
    monkeypatch.setattr(_VETO, lambda: True)
    allowed, _ = SignalGate().check_entry_allowed("BTC/USD", 100.0)
    assert allowed is True


def test_threshold_boundary_blocks_at_exactly_vol_risk_block(monkeypatch, audits):
    monkeypatch.setattr(_SEAM, lambda *a, **k: _assessment(VOL_RISK_BLOCK))
    monkeypatch.setattr(_VETO, lambda: True)
    allowed, _ = SignalGate().check_entry_allowed("BTC/USD", 100.0)
    assert allowed is False


def test_veto_arming_follows_production_mode(monkeypatch):
    """volatility_veto_active is the production_mode wheel: True only in LIVE."""
    from aureon.observer import production_mode as pm

    monkeypatch.setattr(pm, "is_live", lambda: True)
    assert pm.volatility_veto_active() is True
    monkeypatch.setattr(pm, "is_live", lambda: False)
    assert pm.volatility_veto_active() is False
