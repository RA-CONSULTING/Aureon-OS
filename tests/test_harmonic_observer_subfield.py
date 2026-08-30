"""P3: the harmonic observer's local field joins the whole-body consensus.

The observer computes a real local field (rock-stability coherence over the
Λ(t) trace) yet was pinned in the logic-train audit as a producer nobody
could see. ``publish_field()`` closes that: the field appears as the
``harmonic_observer`` sub-field in ``read_subfields``/``blend_field`` — and
publishes NOTHING before data (an unmeasured field is not reported).

The final test proves the Pattern-G bookkeeping: with the wire in place the
KNOWN_UNWIRED pin is deleted and ``compute_logic_train`` still passes — the
module is wired as a producer, not a new unexpected gap.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Same isolation pattern as tests/test_hnc_field_freshness.py: trace dirs
    to tmp, thought-bus singleton reset (no importlib.reload)."""
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


def _observer():
    from aureon.observer.harmonic_observer import HarmonicObserver

    return HarmonicObserver(publish_to_bus=False)


def _state(lambda_t: float = 0.71, gamma: float = 0.83) -> SimpleNamespace:
    return SimpleNamespace(
        lambda_t=lambda_t,
        timestamp=time.time(),
        consciousness_psi=0.44,
        consciousness_level="RECURSIVE",
        coherence_gamma=gamma,
    )


# ── publishes nothing before data ───────────────────────────────────────────


def test_no_subfield_before_any_data(isolated):
    from aureon.core.hnc_field import read_subfields

    obs = _observer()
    obs.publish_field()
    assert "harmonic_observer" not in read_subfields(), (
        "an unmeasured field must not be reported"
    )


# ── the wire: sub-field visible to the whole body ───────────────────────────


def test_subfield_appears_after_ingest(isolated):
    from aureon.core.hnc_field import read_subfields

    obs = _observer()
    obs.ingest_state(_state(gamma=0.83))
    obs.publish_field()

    subs = read_subfields()
    assert "harmonic_observer" in subs
    sub = subs["harmonic_observer"]
    assert sub.get("coherence_gamma") == pytest.approx(0.83)
    assert sub.get("symbolic_life_score") is not None, (
        "the coherence score is the observer's own measured field value"
    )


def test_subfield_joins_blend_contributors(isolated):
    from aureon.core.hnc_field import blend_field

    obs = _observer()
    obs.ingest_state(_state())
    obs.publish_field()

    blended = blend_field()
    assert blended.available is True
    assert "harmonic_observer" in blended.sources


def test_publish_is_throttled(isolated):
    """A second publish inside the 30 s window is a no-op — the daemon calls
    this every 5 s compute step and must not flood the bus/trace."""
    from aureon.core.bus_trace import read_trace

    obs = _observer()
    obs.ingest_state(_state())
    obs.publish_field()
    obs.ingest_state(_state(lambda_t=0.72))
    obs.publish_field()

    rows = [r for r in (read_trace("symbolic_subfield") or [])
            if r.get("source") == "harmonic_observer"]
    assert len(rows) == 1


# ── Pattern-G: the pin is gone and the audit still passes ───────────────────


def test_logic_train_audit_passes_with_harmonic_observer_wired():
    from aureon.cognition.logic_train_audit import KNOWN_UNWIRED, compute_logic_train

    assert "aureon/observer/harmonic_observer.py" not in KNOWN_UNWIRED, (
        "the pin must be deleted in the same change that lands the wire"
    )
    report = compute_logic_train()
    assert "aureon/observer/harmonic_observer.py" not in report.unwired
    assert report.unexpected_unwired == []
    assert report.retired_gaps == []

    site = next(s for s in report.sites
                if s["module"] == "aureon/observer/harmonic_observer.py")
    assert site["wired"] is True
    assert site["role"] == "producer"
