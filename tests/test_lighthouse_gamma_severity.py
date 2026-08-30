"""P6: Lighthouse severity is Γ-aware — the same anomaly matters more when the
organism's shared coherence is already low. Amplify-only (caution is the
conservative direction), capped at 1.0, and untouched when the field is dark.
"""

from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest

from aureon.analytics.aureon_lighthouse import (
    LighthouseEvent,
    LighthouseEventType,
    LighthousePatternDetector,
)

_FIELD = "aureon.core.hnc_field.read_canonical_field"


@pytest.fixture
def isolated_lighthouse_io(tmp_path, monkeypatch):
    """Keep Lighthouse publications inside the per-test temporary directory."""
    from aureon.core import aureon_thought_bus

    journal = tmp_path / "thoughts.jsonl"
    trace_dir = tmp_path / "bus_traces"
    bus = aureon_thought_bus.ThoughtBus(persist_path=str(journal))

    monkeypatch.setattr(
        aureon_thought_bus,
        "get_thought_bus",
        lambda *args, **kwargs: bus,
    )
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(trace_dir))
    return bus, journal, trace_dir


def _event(severity: float) -> LighthouseEvent:
    return LighthouseEvent(
        event_type=LighthouseEventType.ANOMALY_DETECTED,
        timestamp=time.time(),
        severity=severity,
        symbols=["BTC/USD"],
        message="test anomaly",
    )


def _cf(gamma: float):
    from aureon.core.hnc_field import CanonicalField

    return CanonicalField(available=True, symbolic_life_score=gamma,
                          coherence_gamma=gamma, lambda_t=0.5, source="test")


def _dark():
    from aureon.core.hnc_field import CanonicalField

    return CanonicalField()


def _emit(
    det: LighthousePatternDetector,
    ev: LighthouseEvent,
    isolated_lighthouse_io,
) -> LighthouseEvent:
    bus, journal, trace_dir = isolated_lighthouse_io
    assert not journal.exists()

    det._emit_event(ev)
    emitted = det.recent_events[-1]

    published = bus.get_recent(limit=1)
    assert len(published) == 1
    assert published[0]["source"] == "aureon_lighthouse"
    assert published[0]["topic"] == "lighthouse.event"
    assert published[0]["payload"] == emitted.to_dict()

    persisted = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    assert persisted == published

    trace_path = trace_dir / "lighthouse_event.jsonl"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8").strip())
    assert {key: trace_payload[key] for key in emitted.to_dict()} == emitted.to_dict()
    assert isinstance(trace_payload["_ts"], float)
    return emitted


def test_low_gamma_amplifies_severity(isolated_lighthouse_io):
    det = LighthousePatternDetector()
    with patch(_FIELD, lambda *a, **k: _cf(0.0)):
        got = _emit(det, _event(0.4), isolated_lighthouse_io)
    assert got.severity == pytest.approx(0.6), "Γ=0 → 1.5× amplification"
    assert got.data["canonical_gamma"] == pytest.approx(0.0)


def test_high_gamma_leaves_severity_untouched(isolated_lighthouse_io):
    det = LighthousePatternDetector()
    with patch(_FIELD, lambda *a, **k: _cf(1.0)):
        got = _emit(det, _event(0.4), isolated_lighthouse_io)
    assert got.severity == pytest.approx(0.4), "a calm field never REDUCES severity"


def test_amplified_severity_is_capped_at_one(isolated_lighthouse_io):
    det = LighthousePatternDetector()
    with patch(_FIELD, lambda *a, **k: _cf(0.1)):
        got = _emit(det, _event(0.9), isolated_lighthouse_io)
    assert got.severity == pytest.approx(1.0)


def test_dark_field_passes_measured_severity_unchanged(isolated_lighthouse_io):
    det = LighthousePatternDetector()
    with patch(_FIELD, lambda *a, **k: _dark()):
        got = _emit(det, _event(0.4), isolated_lighthouse_io)
    assert got.severity == pytest.approx(0.4)
    assert "canonical_gamma" not in got.data
