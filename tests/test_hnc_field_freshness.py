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

from aureon.core.hnc_field import build_hnc_live_field_receipt_id

_CANONICAL_CONTROL_FIELDS = (
    "operational_eligible",
    "provider_eligible",
    "action_eligible",
    "actionable",
    "accounting_eligible",
    "learning_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "action_gate_passed",
)


def _canonical_envelope(now=None, **overrides):
    received_at = time.time() if now is None else now
    source_timestamp = received_at - 1.0
    memory_hash = "1" * 64
    memory_receipt_id = f"hnc:lambda_history:{memory_hash}"
    input_receipt_ids = sorted([
        memory_receipt_id,
        "provider:a:1",
        "provider:b:1",
    ])
    envelope = {
        "data_status": "live",
        "source": "hnc_live_daemon",
        "source_id": "aureon:hnc:live_daemon",
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "ts": source_timestamp,
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": input_receipt_ids,
        "memory_receipt_id": memory_receipt_id,
        "memory_canonical_hash": memory_hash,
        "memory_previous_receipt_id": None,
        "freshness_status": "fresh",
        "operational_eligible": False,
        "provider_eligible": False,
        "action_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "equation_inputs_complete": True,
        "action_gate_passed": False,
        "action_gate_reason": "route_specific_market_link_required",
        "symbolic_life_score": 0.9,
        "coherence_gamma": 0.8,
        "consciousness_psi": 0.7,
        "consciousness_level": "CONNECTED",
        "lambda_t": 0.3,
        "step": 7,
        "source_count": 2,
    }
    envelope["receipt_id"] = build_hnc_live_field_receipt_id(
        input_receipt_ids=input_receipt_ids,
        source_timestamp=envelope["source_timestamp"],
        received_at=envelope["received_at"],
        step=envelope["step"],
        lambda_t=envelope["lambda_t"],
        coherence_gamma=envelope["coherence_gamma"],
        consciousness_psi=envelope["consciousness_psi"],
        symbolic_life_score=envelope["symbolic_life_score"],
    )
    envelope.update(overrides)
    if "source_timestamp" in overrides and "ts" not in overrides:
        envelope["ts"] = overrides["source_timestamp"]
    return envelope


def _read_canonical_transport(hf, tmp_path, transport, envelope):
    if transport == "bus":
        from aureon.core.aureon_thought_bus import Thought, ThoughtBus

        bus = ThoughtBus()
        bus.publish(
            Thought(
                source="hnc_live_daemon",
                topic="symbolic.life.pulse",
                payload=dict(envelope),
            )
        )
        return hf.read_canonical_field(bus)
    (tmp_path / "hnc_live_trace.jsonl").write_text(
        json.dumps(envelope) + "\n",
        encoding="utf-8",
    )
    return hf.read_canonical_field()


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
        json.dumps(_canonical_envelope(source_timestamp=time.time() - 99999)) + "\n",
        encoding="utf-8",
    )
    assert hf.read_canonical_field().available is False


@pytest.mark.parametrize("transport", ("bus", "trace"))
def test_complete_canonical_receipt_is_preserved_but_non_actionable(field, transport):
    hf, _bt, tmp = field
    envelope = _canonical_envelope()
    got = _read_canonical_transport(hf, tmp, transport, envelope)
    assert got.available is True
    assert got.symbolic_life_score == pytest.approx(0.9)
    assert got.evidence_transport == {
        "bus": "thought_bus",
        "trace": "persisted_trace",
    }[transport]
    preserved = got.to_dict()
    for name in (
        "source",
        "source_id",
        "source_timestamp",
        "received_at",
        "receipt_id",
        "receipt_type",
        "provider_receipt_type",
        "input_receipt_ids",
        "memory_receipt_id",
        "memory_canonical_hash",
        "memory_previous_receipt_id",
        "step",
        "data_status",
        "truth_status",
        "generated_values",
        "source_count",
        "freshness_status",
        "equation_inputs_complete",
        "action_gate_reason",
    ):
        assert preserved[name] == envelope[name]
    for name in _CANONICAL_CONTROL_FIELDS:
        assert preserved[name] is False


def test_unknown_evidence_transport_is_rejected(field):
    hf, _bt, _tmp = field
    got = hf._canonical_field_from_envelope(
        _canonical_envelope(),
        evidence_transport="unknown",
    )
    assert got.available is False
    assert got.evidence_transport is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("coherence_gamma", 0.99),
        ("step", 8),
        ("memory_canonical_hash", "f" * 64),
        ("receipt_id", "hnc:live_field:" + ("0" * 24)),
    ),
)
def test_live_field_receipt_is_bound_to_exact_content_and_history(
    field,
    field_name,
    value,
):
    hf, _bt, tmp = field
    envelope = _canonical_envelope()
    envelope[field_name] = value

    got = _read_canonical_transport(hf, tmp, "bus", envelope)

    assert got.available is False


@pytest.mark.parametrize("transport", ("bus", "trace"))
def test_stale_live_field_cannot_be_replayed_by_rewriting_timestamps(
    field,
    transport,
):
    hf, _bt, tmp = field
    envelope = _canonical_envelope(now=time.time() - 99_999.0)
    rewritten_at = time.time()
    envelope.update(
        source_timestamp=rewritten_at - 1.0,
        received_at=rewritten_at,
        ts=rewritten_at - 1.0,
    )

    got = _read_canonical_transport(hf, tmp, transport, envelope)

    assert got.available is False


def test_invalid_bus_pulse_falls_back_to_valid_persisted_trace(field):
    from aureon.core.aureon_thought_bus import Thought, ThoughtBus

    hf, _bt, tmp = field
    valid = _canonical_envelope()
    (tmp / "hnc_live_trace.jsonl").write_text(
        json.dumps(valid) + "\n",
        encoding="utf-8",
    )
    invalid = dict(valid)
    invalid["coherence_gamma"] = 0.99
    bus = ThoughtBus()
    bus.publish(Thought(
        source="hnc_live_daemon",
        topic="symbolic.life.pulse",
        payload=invalid,
    ))

    got = hf.read_canonical_field(bus)

    assert got.available is True
    assert got.evidence_transport == "persisted_trace"
    assert got.coherence_gamma == pytest.approx(valid["coherence_gamma"])


def test_untimestamped_canonical_trace_is_unavailable(field):
    hf, _bt, tmp = field
    (tmp / "hnc_live_trace.jsonl").write_text(
        json.dumps(_canonical_envelope(source_timestamp=None, ts=None)) + "\n",
        encoding="utf-8",
    )
    assert hf.read_canonical_field().available is False


@pytest.mark.parametrize("transport", ("bus", "trace"))
@pytest.mark.parametrize(
    ("case", "updates"),
    [
        ("nonfinite_metric", {"symbolic_life_score": float("nan")}),
        ("nonfinite_received_at", {"received_at": float("inf")}),
        ("missing_receipt_id", {"receipt_id": None}),
        (
            "missing_receipt_type",
            {"receipt_type": None, "provider_receipt_type": None},
        ),
        ("missing_inputs", {"input_receipt_ids": []}),
        ("missing_truth", {"truth_status": None}),
        ("incomplete_equation", {"equation_inputs_complete": False}),
        ("no_data", {"data_status": "no_data", "truth_status": "no_data"}),
        ("generated", {"generated_values": True}),
        ("mismatched_receipt_type", {"provider_receipt_type": "other"}),
    ]
    + [
        (f"{name}_true", {name: True})
        for name in _CANONICAL_CONTROL_FIELDS
    ],
)
def test_incomplete_or_eligible_canonical_receipts_fail_closed(
    field,
    transport,
    case,
    updates,
):
    del case
    hf, _bt, tmp = field
    got = _read_canonical_transport(
        hf,
        tmp,
        transport,
        _canonical_envelope(**updates),
    )
    assert got.available is False
    assert got.data_status == "no_data"
    assert got.symbolic_life_score is None


@pytest.mark.parametrize("transport", ("bus", "trace"))
@pytest.mark.parametrize("case", ("stale", "future_source", "future_received", "laundered"))
def test_canonical_receipt_timestamps_fail_closed(field, transport, case):
    hf, _bt, tmp = field
    now = time.time()
    envelope = _canonical_envelope(now=now)
    if case == "stale":
        envelope["source_timestamp"] = now - 99999
        envelope["ts"] = envelope["source_timestamp"]
    elif case == "future_source":
        envelope["source_timestamp"] = now + 10
        envelope["ts"] = envelope["source_timestamp"]
    elif case == "future_received":
        envelope["received_at"] = now + 10
    else:
        envelope["source_timestamp"] = now - 99999
        envelope["ts"] = now
    assert _read_canonical_transport(hf, tmp, transport, envelope).available is False


# ── the window itself ───────────────────────────────────────────────────────────

def test_window_can_be_tightened_but_never_widened(field, monkeypatch):
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "s", "ts": time.time() - 600, "symbolic_life_score": 0.5})
    assert hf.blend_field().available is False          # 10 min old, default window 5 min
    monkeypatch.setenv("AUREON_HNC_FIELD_MAX_AGE_S", "3600")
    assert hf._max_age_s() == 300.0
    assert hf.blend_field().available is False           # environment cannot widen v1
    monkeypatch.setenv("AUREON_HNC_FIELD_MAX_AGE_S", "60")
    assert hf._max_age_s() == 60.0                       # tightening remains supported
    for bad in ("", "nonsense", "-5", "0", "inf", "nan"):
        monkeypatch.setenv("AUREON_HNC_FIELD_MAX_AGE_S", bad)
        assert hf._max_age_s() == 300.0                 # never zero/negative/unparseable


def test_canonical_validation_rejects_nonfinite_clock(field):
    hf, _bt, _tmp = field
    envelope = {
        **_canonical_envelope(),
        "available": True,
        "evidence_transport": "persisted_trace",
    }

    with pytest.raises(ValueError, match="complete_fresh_canonical_hnc_field_required"):
        hf.validate_canonical_field_snapshot(envelope, now=float("nan"))


def test_canonical_window_cannot_be_widened_by_environment(field, monkeypatch):
    hf, _bt, _tmp = field
    checked_at = time.time()
    envelope = {
        **_canonical_envelope(now=checked_at - 301.0),
        "available": True,
        "evidence_transport": "persisted_trace",
    }
    monkeypatch.setenv("AUREON_HNC_FIELD_MAX_AGE_S", "3600")

    with pytest.raises(ValueError, match="complete_fresh_canonical_hnc_field_required"):
        hf.validate_canonical_field_snapshot(envelope, now=checked_at)


def test_a_clock_skewed_future_row_is_tolerated_not_refused(field):
    """A producer whose clock is a little ahead is still live; only absurd future stamps are refused."""
    hf, bt, _ = field
    bt.append_trace("symbolic_subfield",
                    {"source": "skewed", "ts": time.time() + 20, "symbolic_life_score": 0.5})
    assert hf.blend_field().available is True
    bt.append_trace("symbolic_subfield",
                    {"source": "absurd", "ts": time.time() + 999999, "symbolic_life_score": 0.5})
    assert "absurd" not in hf.blend_field().sources
