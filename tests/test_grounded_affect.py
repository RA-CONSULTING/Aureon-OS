"""
Affect → grounded gate: fear tightens, victory never loosens, off by default.

Offline + hermetic. Proves the fail-safe actuator: AUREON_AFFECT_MODULATION off
(default) leaves the gate byte-identical; on + a fearful field only ever raises
caution; the hard boundary is never crossed by a feeling.
"""

from __future__ import annotations

import json
import time

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.bus_trace import append_trace


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "affect_lambda.json"))
    monkeypatch.setenv("AUREON_RUNTIME_STATUS_PATH", str(tmp_path / "runtime.json"))
    monkeypatch.setenv("AUREON_GLOBAL_FINANCIAL_PATH", str(tmp_path / "gfs.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    monkeypatch.setenv("AUREON_BRAIN_PREDICTIONS_PATH", str(tmp_path / "preds.json"))
    monkeypatch.setenv("AUREON_BRAIN_KNOWLEDGE_PATH", str(tmp_path / "know.json"))
    monkeypatch.delenv("AUREON_AFFECT_MODULATION", raising=False)
    (tmp_path / "gfs.json").write_text(json.dumps({"last_snapshot": {"crypto_fear_greed": 8}}), encoding="utf-8")
    # reset the affect + bus singletons so affect and the gate read the SAME
    # fresh global bus each test (affect_monitor reads get_thought_bus()).
    import aureon.core.affect_monitor as am
    import aureon.core.aureon_thought_bus as tb

    monkeypatch.setattr(am, "_monitor", None, raising=False)
    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    return tmp_path


def _fearful_bus():
    # Publish onto the GLOBAL bus so both the gate (passed this bus) and the affect
    # monitor (which reads get_thought_bus()) see the same fearful field.
    b = get_thought_bus()
    b.publish(Thought(source="hnc", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.12, "coherence_gamma": 0.12, "source": "live"}))
    b.publish(Thought(source="q", topic="symbolic.life.subfield",
                      payload={"source": "q", "symbolic_life_score": 0.9}))  # high divergence
    append_trace("lighthouse_event", {"type": "COHERENCE_COLLAPSE", "severity": 0.95, "_ts": time.time()})
    return b


def _ground(bus):
    from aureon.operator.grounded_action import GroundedActionGate

    return GroundedActionGate(bus=bus, enable_llm=False).ground("read_repo_file", {"path": "README.md"})


def test_off_by_default_is_a_noop():
    # A benign read under a fearful field is APPROVED when modulation is off.
    v = _ground(_fearful_bus())
    assert v.verdict == "APPROVED"


def test_fear_tightens_when_enabled(monkeypatch):
    monkeypatch.setenv("AUREON_AFFECT_MODULATION", "1")
    v = _ground(_fearful_bus())
    # the organism felt its own fear and grounded the move more cautiously
    assert v.verdict in ("CONCERNED", "VETOED")


def test_victory_never_loosens(monkeypatch, tmp_path):
    # A victorious, coherent field must not make the gate MORE permissive than
    # the already-permissive default (a benign read is APPROVED either way).
    monkeypatch.setenv("AUREON_AFFECT_MODULATION", "1")
    (tmp_path / "gfs.json").write_text(json.dumps({"last_snapshot": {"crypto_fear_greed": 95}}), encoding="utf-8")
    (tmp_path / "runtime.json").write_text(
        json.dumps({"shadow_trading": {"validated_shadow_count": 10, "missed_shadow_count": 0}}), encoding="utf-8")
    b = get_thought_bus()
    b.publish(Thought(source="hnc", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 1.0, "coherence_gamma": 1.0, "source": "live"}))
    v = _ground(b)
    assert v.verdict == "APPROVED"  # victory did not tighten, and cannot loosen below default


def test_hard_boundary_survives_affect(monkeypatch):
    # No feeling can approve a hard-boundary-violating move.
    monkeypatch.setenv("AUREON_AFFECT_MODULATION", "1")
    from aureon.operator.grounded_action import GroundedActionGate

    v = GroundedActionGate(bus=_fearful_bus(), enable_llm=False).ground(
        "disable_safety", {"target": "conscience"})
    # A feeling can never get a dangerous move approved — the hard boundary /
    # conscience deny it regardless of affect.
    assert v.approved is False
