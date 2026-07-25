"""
The HNC field must be FRESH to be called available.

These readers cross process boundaries through persisted trace files, and a file on disk has no idea
how old it is. Before this bound, ``available=True`` meant only "a row exists somewhere":

  * ``_read_field_from_trace`` returned the LAST LINE of ``state/hnc_live_trace.jsonl`` whatever its
    age, so a coherence figure written by a daemon that has since stopped was served to dashboards
    as the organism's current field;
  * ``read_subfields`` absorbed up to 200 rows from the ``symbolic_subfield`` trace with no age
    check — and those rows carried **no timestamp at all**, so their staleness was not merely
    ignored, it was unknowable. Observed on a clean checkout: ``blend_field()`` reported
    ``available=True`` with two contributors and a coherence figure, in a fresh offline process with
    no producer running.

A stale number presented as live is a false reading, not a cautious one. So: rows are stamped at
publish, refused once older than the window, and refused outright when the age cannot be established.
When nothing fresh is flowing the honest answer is ``available=False``.
"""

from __future__ import annotations

import json
import time

import pytest


@pytest.fixture
def field(tmp_path, monkeypatch):
    """hnc_field + bus_trace bound to an isolated trace dir (never the repo's own state/).

    The in-process thought bus is a module-level singleton that outlives a test, so the
    singleton slot is monkeypatched to None per test (a fresh bus is constructed on the
    next ``get_thought_bus()``) — otherwise one test's ``publish_subfield`` stays in bus
    memory (correctly stamped and fresh) and contributes to the next test's blend.

    Deliberately NOT ``importlib.reload``: a reload rebinds ``Thought``/``ThoughtBus``
    to new class objects while every other test module keeps references to the old ones,
    which poisons isinstance checks suite-wide (found by the B5 sentinel run). Both
    bus_trace and hnc_field resolve their env vars per call, so the setenv isolation
    alone is sufficient for them.
    """
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_live_trace.jsonl"))

    import sys

    import aureon.core.aureon_thought_bus as tb
    import aureon.core.bus_trace as bt
    import aureon.core.hnc_field as hf

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    bare = sys.modules.get("aureon_thought_bus")
    if bare is not None and bare is not tb:
        monkeypatch.setattr(bare, "_thought_bus_instance", None, raising=False)
    yield hf, bt, tmp_path


# ── sub-fields ──────────────────────────────────────────────────────────────────

def test_untimestamped_subfield_row_is_refused(field):
    """The original defect. A row with no timestamp has unknowable age, so it cannot be shown as
    current — being unable to prove a reading is fresh is not a reason to present it as fresh."""
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "ghost", "symbolic_life_score": 0.61, "coherence_gamma": 0.53})
    blended = hf.blend_field()
    assert blended.available is False
    assert blended.contributors == 0
    assert blended.symbolic_life_score is None


def test_stale_subfield_row_is_refused(field):
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "dead_daemon", "ts": time.time() - 7200,
                     "symbolic_life_score": 0.99, "coherence_gamma": 0.99})
    assert hf.blend_field().available is False


def test_fresh_subfield_row_is_used(field):
    """The bound must not break the real case — a live producer still reaches the blend."""
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "live_daemon", "ts": time.time(),
                     "symbolic_life_score": 0.42, "coherence_gamma": 0.44})
    blended = hf.blend_field()
    assert blended.available is True
    assert blended.contributors == 1
    assert blended.symbolic_life_score == pytest.approx(0.42)
    assert "live_daemon" in blended.sources


def test_one_live_producer_does_not_revive_a_dead_one(field):
    """Freshness is per row, not per file: sharing a trace with a live producer must not make a
    long-dead producer's last reading count toward the consensus."""
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "dead", "ts": time.time() - 99999, "symbolic_life_score": 0.05})
    bt.append_trace("symbolic_subfield",
                    {"source": "live", "ts": time.time(), "symbolic_life_score": 0.80})
    blended = hf.blend_field()
    assert blended.contributors == 1
    assert list(blended.sources) == ["live"]
    assert blended.symbolic_life_score == pytest.approx(0.80)   # not the mean with 0.05


def test_publish_subfield_stamps_a_timestamp(field):
    """Producers must be stamped, or the reader would refuse them as unknowable-age and the real
    field would silently vanish from the blend."""
    hf, bt, _ = field

    class _State:
        symbolic_life_score = 0.55
        coherence_gamma = 0.5
        consciousness_level = "aware"

    hf.publish_subfield("real_producer", _State())
    rows = bt.read_trace("symbolic_subfield", limit=10)
    assert rows and isinstance(rows[-1].get("ts"), (int, float))
    assert hf.blend_field().contributors == 1


# ── the canonical trace file ─────────────────────────────────────────────────────

def test_stale_canonical_trace_is_unavailable(field):
    hf, _bt, tmp = field
    (tmp / "hnc_live_trace.jsonl").write_text(
        json.dumps({"symbolic_life_score": 0.9, "coherence_gamma": 0.9,
                    "ts": time.time() - 99999}) + "\n", encoding="utf-8")
    assert hf.read_canonical_field().available is False


def test_fresh_canonical_trace_is_available(field):
    hf, _bt, tmp = field
    (tmp / "hnc_live_trace.jsonl").write_text(
        json.dumps({"symbolic_life_score": 0.9, "coherence_gamma": 0.9,
                    "ts": time.time()}) + "\n", encoding="utf-8")
    got = hf.read_canonical_field()
    assert got.available is True
    assert got.symbolic_life_score == pytest.approx(0.9)


def test_untimestamped_canonical_trace_is_unavailable(field):
    hf, _bt, tmp = field
    (tmp / "hnc_live_trace.jsonl").write_text(
        json.dumps({"symbolic_life_score": 0.9}) + "\n", encoding="utf-8")
    assert hf.read_canonical_field().available is False


# ── the window itself ───────────────────────────────────────────────────────────

def test_window_is_configurable_and_defaults_sanely(field, monkeypatch):
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "s", "ts": time.time() - 600, "symbolic_life_score": 0.5})
    assert hf.blend_field().available is False          # 10 min old, default window 5 min
    monkeypatch.setenv("AUREON_HNC_FIELD_MAX_AGE_S", "3600")
    assert hf.blend_field().available is True           # widened deliberately
    for bad in ("", "nonsense", "-5", "0"):
        monkeypatch.setenv("AUREON_HNC_FIELD_MAX_AGE_S", bad)
        assert hf._max_age_s() == 300.0                 # never zero/negative/unparseable


def test_a_clock_skewed_future_row_is_tolerated_not_refused(field):
    """A producer whose clock is a little ahead is still live; only absurd future stamps are refused."""
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "skewed", "ts": time.time() + 20, "symbolic_life_score": 0.5})
    assert hf.blend_field().available is True
    bt.append_trace("symbolic_subfield",
                    {"source": "absurd", "ts": time.time() + 999999, "symbolic_life_score": 0.5})
    assert "absurd" not in hf.blend_field().sources
