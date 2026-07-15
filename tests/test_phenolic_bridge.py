"""Tests for the phenolic-fingerprint → cognition bridge."""

from __future__ import annotations

from pathlib import Path

import pytest

from aureon.cognition import phenolic_bridge as bridge
from aureon.core.aureon_thought_bus import ThoughtBus

_ANALYSIS = {
    "valid": True,
    "alpha": 0.05,
    "source_path": "x.csv",
    "formats": ["native"],
    "controls": {"positive": {"passed": True}, "negative": {"passed": True}},
    "compounds": {
        "caffeic acid": {"test_A_p": 0.003, "test_B_p": 0.7, "separable": False,
                          "n_peaks": 59, "sources": ["doi:cga"]},
        "luteolin": {"test_A_p": 0.005, "test_B_p": 0.6, "separable": True,
                     "n_peaks": 21, "sources": ["doi:lut", "COMPUTED GFN2-xTB (theoretical, non-experimental)"]},
        "apigenin": {"test_A_p": 0.8, "test_B_p": 0.9, "separable": False,
                     "n_peaks": 5, "sources": ["doi:api"]},
    },
}


def test_summarize_patterns():
    s = bridge.summarize_patterns(_ANALYSIS)
    assert s["valid"] is True
    assert s["controls_pass"] is True
    assert s["n_compounds"] == 3
    assert s["separable"] == ["luteolin"]
    assert s["separable_fraction"] == pytest.approx(1 / 3)
    assert s["clustering_significant"] == ["caffeic acid", "luteolin"]
    assert s["provenance_counts"] == {"experimental": 2, "mixed": 1}
    assert "separable" in s["headline"]


def test_emit_publishes_topics_and_payloads(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    captured = []
    bus.subscribe("phenolic.*", lambda t: captured.append(t))

    summary = bridge.emit_to_cognition(_ANALYSIS, bus=bus)

    topics = [t.topic for t in captured]
    assert topics.count(bridge.RUN_TOPIC) == 1
    assert topics.count(bridge.COMPOUND_TOPIC) == 3
    # all share one trace_id
    assert len({t.trace_id for t in captured}) == 1
    # compound payloads carry the engine scores + provenance
    comp = next(t for t in captured if t.topic == bridge.COMPOUND_TOPIC
                and t.payload["compound"] == "luteolin")
    assert comp.payload["separable"] is True
    assert comp.payload["provenance"] == "mixed"
    assert "test_A_p" in comp.payload and "sources" in comp.payload
    assert summary["separable"] == ["luteolin"]


def test_emit_writes_bus_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    from aureon.core.bus_trace import read_trace_latest

    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    bridge.emit_to_cognition(_ANALYSIS, bus=bus)
    tr = read_trace_latest(bridge.TRACE_NAME)
    assert tr is not None
    assert tr["n_compounds"] == 3
    assert tr["n_separable"] == 1
    assert tr["controls_pass"] is True


def test_emit_tolerates_throwing_bus(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))

    class _BadBus:
        def publish(self, *a, **k):
            raise RuntimeError("bus down")

    # must not raise; still returns a summary
    summary = bridge.emit_to_cognition(_ANALYSIS, bus=_BadBus())
    assert summary["n_compounds"] == 3
