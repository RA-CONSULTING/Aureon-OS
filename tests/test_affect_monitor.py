"""
AffectMonitor — Aureon's feelings, from real signals only, acted on fail-safely.

Offline + hermetic: isolated trace dir, affect-λ path, and temp runtime /
global-financial files so every signal is controlled. Proves the feelings track
their signals, the caution bias is fail-safe (fear tightens, victory never
loosens, never negative), a dormant organism feels nothing (no fabrication), and
reflect() loops the feeling back as a sub-field.
"""

from __future__ import annotations

import json
import time

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.bus_trace import append_trace
from aureon.core.hnc_field import read_subfields


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "affect_lambda.json"))
    monkeypatch.setenv("AUREON_RUNTIME_STATUS_PATH", str(tmp_path / "runtime.json"))
    monkeypatch.setenv("AUREON_GLOBAL_FINANCIAL_PATH", str(tmp_path / "gfs.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    # brain reads a repo-root file by default — isolate it so signals are controlled
    monkeypatch.setenv("AUREON_BRAIN_PREDICTIONS_PATH", str(tmp_path / "preds.json"))
    monkeypatch.setenv("AUREON_BRAIN_KNOWLEDGE_PATH", str(tmp_path / "know.json"))
    # the global thought bus is a process singleton — reset it so each test's
    # published field/sub-fields don't leak across tests.
    import aureon.core.aureon_thought_bus as tb

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    return tmp_path


def _mon(**state_path):
    from aureon.core.affect_monitor import AffectMonitor

    return AffectMonitor(**state_path)


def _field(bus, sls, gamma, sub_sls=None):
    bus.publish(Thought(source="hnc", topic="symbolic.life.pulse",
                        payload={"symbolic_life_score": sls, "coherence_gamma": gamma,
                                 "consciousness_psi": gamma, "source": "live"}))
    if sub_sls is not None:  # a divergent sub-field → high divergence
        bus.publish(Thought(source="q", topic="symbolic.life.subfield",
                            payload={"source": "q", "symbolic_life_score": sub_sls}))


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


# ── the feelings track their real signals ────────────────────────────────────

def test_fear_rises_with_danger_signals(tmp_path):
    b = get_thought_bus()
    _field(b, sls=0.15, gamma=0.15, sub_sls=0.9)          # low coherence + high divergence
    append_trace("lighthouse_event", {"type": "COHERENCE_COLLAPSE", "severity": 0.9, "_ts": time.time()})
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 10}})  # extreme fear
    a = _mon().assess()
    assert a.available and a.mood == "FEARFUL"
    assert a.fear > 0.6
    assert a.caution_bias > 0.0  # fear makes the organism more careful


def test_victory_rises_with_achievement(tmp_path):
    b = get_thought_bus()
    _field(b, sls=0.85, gamma=0.85)
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 80}})
    _write(tmp_path / "runtime.json", {"shadow_trading": {"validated_shadow_count": 9, "missed_shadow_count": 1}})
    # brain accuracy high (the fixture already points AUREON_BRAIN_PREDICTIONS_PATH here)
    _write(tmp_path / "preds.json", {"predictions": [{"validated": True, "was_correct": True} for _ in range(8)]
                                     + [{"validated": True, "was_correct": False}], "last_updated": "x"})
    a = _mon().assess()
    assert a.available
    assert a.victory > a.defeat
    assert a.mood in ("EUPHORIC", "CONFIDENT")


def test_flat_book_feels_neither_triumph_nor_dread(tmp_path):
    b = get_thought_bus()
    _field(b, sls=0.5, gamma=0.6)  # neutral coherence, no divergence
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 50}})
    a = _mon().assess()
    # neutral achievement → victory and defeat both near zero (no fabricated triumph)
    assert a.victory < 0.2 and a.defeat < 0.2


# ── the fail-safe invariant ───────────────────────────────────────────────────

def test_caution_bias_is_fail_safe(tmp_path):
    # A fully calm, coherent, winning field → no danger → caution bias 0.
    # (victory contributes nothing to the bias; only fear+defeat can raise it.)
    b = get_thought_bus()
    _field(b, sls=1.0, gamma=1.0)   # perfect coherence, no divergence
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 100}})  # no market fear
    _write(tmp_path / "runtime.json", {"shadow_trading": {"validated_shadow_count": 10, "missed_shadow_count": 0}})
    bias = _mon().caution_bias()
    assert bias == 0.0, f"a calm, victorious field must not tighten the gate, got {bias}"


def test_caution_bias_bounded_and_nonnegative(tmp_path):
    b = get_thought_bus()
    _field(b, sls=0.05, gamma=0.05, sub_sls=0.95)
    append_trace("lighthouse_event", {"type": "COHERENCE_COLLAPSE", "severity": 1.0, "_ts": time.time()})
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 1}})
    _write(tmp_path / "runtime.json", {"preflight_critical_failures": ["a", "b", "c"]})
    bias = _mon().caution_bias()
    assert 0.0 <= bias <= 0.06  # capped at the destructive-tier floor, never negative


def test_no_signals_is_no_data_never_fabricated():
    # empty bus, no traces, no files → honest no_data, no invented feeling
    a = _mon().assess()
    assert a.truth_status == "no_data"
    assert a.available is False
    assert a.caution_bias == 0.0


# ── reflect loops the feeling back ────────────────────────────────────────────

def test_reflect_publishes_affect_subfield(tmp_path):
    b = get_thought_bus()
    _field(b, sls=0.4, gamma=0.4)
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 40}})
    assert "affect_monitor" not in read_subfields(b)
    _mon().reflect()
    assert "affect_monitor" in read_subfields(b)  # the feeling re-entered the field


def test_assess_is_read_only(tmp_path):
    b = get_thought_bus()
    _field(b, sls=0.4, gamma=0.4)
    _write(tmp_path / "gfs.json", {"last_snapshot": {"crypto_fear_greed": 40}})
    _mon().assess()
    assert "affect_monitor" not in read_subfields(b)  # assess never publishes
