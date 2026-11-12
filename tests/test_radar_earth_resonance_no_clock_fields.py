"""The aureon_radar copies of the earth resonance engine must not report
wall-clock sin/cos as live field coherence, phase lock or stability either.
Each copy is loaded by file path; mode powers are passed in, so no network."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ["aureon_radar/harmonic/earth_resonance_engine.py",
          "aureon_radar/planetary/earth_resonance_engine.py"]
MODES = dict(mode1_power=0.8, mode2_power=0.6, mode3_power=0.5)


def _load(rel):
    name = "_radar_ere_" + rel.split("/")[1]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("rel", COPIES)
def test_no_clock_values_without_dev_switch(monkeypatch, rel):
    mod = _load(rel)
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    for now in (1_786_400_000.0, 1_786_400_777.0):
        monkeypatch.setattr(mod.time, "time", lambda now=now: now)
        eng = mod.EarthResonanceEngine()
        s = eng.update_schumann_state(**MODES)
        assert (s.field_coherence, s.phase_lock, s.resonance_stability) == (0.0, 0.0, 0.0)
        assert eng._schumann_state_initialized is False
        assert eng.get_trading_gate_status()[0] is False


@pytest.mark.parametrize("rel", COPIES)
def test_dev_switch_values_never_open_gate(monkeypatch, rel):
    mod = _load(rel)
    monkeypatch.setattr(mod.time, "time", lambda: 1_786_400_000.0)
    monkeypatch.setenv("AUREON_ALLOW_SIM_FALLBACK", "1")
    eng = mod.EarthResonanceEngine()
    eng.update_schumann_state(**MODES)
    assert eng._schumann_state_initialized is False
    assert eng.get_trading_gate_status()[0] is False
