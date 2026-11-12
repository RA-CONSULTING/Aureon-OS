"""Earth resonance field values must never come from the wall clock in live posture.

Before this fix ``update_schumann_state`` set field_coherence, phase_lock and
resonance_stability from sin/cos of time.time() on every call, even when the
mode powers were real, then marked the engine initialised, so the trading gate
could treat clock values as a real reading. Now they come only from a fresh
accepted Schumann receipt, or report no data and keep the gate closed.
No network: mode powers are passed in explicitly.
"""
from __future__ import annotations

import aureon.harmonic.earth_resonance_engine as ere
from aureon.harmonic.earth_resonance_engine import (
    EARTH_GATE_RECEIPT_MAX_AGE_SECONDS,
    EarthResonanceEngine,
)

MODES = dict(mode1_power=0.8, mode2_power=0.6, mode3_power=0.5)


def _engine(monkeypatch, now):
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    monkeypatch.setattr(ere.time, "time", lambda: now)
    return EarthResonanceEngine()


def test_no_receipt_reports_no_data_and_gate_stays_closed(monkeypatch):
    values = []
    for now in (1_786_400_000.0, 1_786_400_777.0, 1_786_403_333.0):
        eng = _engine(monkeypatch, now)
        state = eng.update_schumann_state(**MODES)
        values.append((state.field_coherence, state.phase_lock, state.resonance_stability))
        ok, reason = eng.get_trading_gate_status()
        assert ok is False and "no_live_schumann_data" in reason
    assert values == [(0.0, 0.0, 0.0)] * 3  # same at every clock time: nothing clock-derived


def test_fresh_receipt_values_are_used(monkeypatch):
    now = 1_786_400_000.0
    eng = _engine(monkeypatch, now)
    eng._receipt_field_values = {"coherence": 0.9, "stability": 0.8, "source_timestamp": now - 10}
    state = eng.update_schumann_state(**MODES, market_volatility=0.0)
    assert (state.field_coherence, state.phase_lock, state.resonance_stability) == (0.9, 0.8, 0.8)
    assert eng._schumann_state_initialized is True


def test_stale_receipt_is_not_used(monkeypatch):
    now = 1_786_400_000.0
    eng = _engine(monkeypatch, now)
    eng._receipt_field_values = {
        "coherence": 0.9,
        "stability": 0.8,
        "source_timestamp": now - EARTH_GATE_RECEIPT_MAX_AGE_SECONDS - 1,
    }
    state = eng.update_schumann_state(**MODES)
    assert state.field_coherence == 0.0 and state.phase_lock == 0.0
    assert eng._schumann_state_initialized is False


def test_dev_sim_values_never_open_the_gate(monkeypatch):
    eng = _engine(monkeypatch, 1_786_400_000.0)
    monkeypatch.setenv("AUREON_ALLOW_SIM_FALLBACK", "1")
    state = eng.update_schumann_state(**MODES)
    assert state.field_coherence > 0.0  # dev-only clock values exist...
    assert eng._schumann_state_initialized is False  # ...but never open the gate
    ok, reason = eng.get_trading_gate_status()
    assert ok is False and "no_live_schumann_data" in reason
