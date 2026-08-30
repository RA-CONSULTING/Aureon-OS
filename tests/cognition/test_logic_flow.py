"""Tests for the logic-flow tracer — one HNC signal crossing the bus into a decision.

On an isolated in-memory bus, a single canonical ``symbolic.life.pulse`` is read through the real
``read_canonical_field`` layer and carried into a downstream decision on ONE trace_id. Deterministic
(fixed seed pulse); byte-identical artifacts; never a claim about a person.
"""

from __future__ import annotations

import json

from aureon.cognition import logic_flow as lf

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def _report():
    return lf.compute_logic_flow(seed_score=0.639, trace_id="test0")


# ── the flow ──────────────────────────────────────────────────────────────────────────────────────


def test_flow_is_intact_end_to_end():
    r = _report()
    assert r.pulse_published
    assert r.field_read and r.field_score == 0.639
    assert r.decision_carries_field
    assert r.trace_id_propagated and r.single_trace_id
    assert r.flow_intact


def test_topic_sequence_is_pulse_then_decision():
    r = _report()
    assert r.topic_sequence[:2] == [lf.PULSE_TOPIC, lf.DECISION_TOPIC]


def test_one_unbroken_trace_id():
    r = _report()
    assert r.trace_id == "test0"
    assert r.single_trace_id


def test_compute_is_deterministic():
    assert _report().to_dict() == _report().to_dict()


# ── the report ─────────────────────────────────────────────────────────────────────────────────


def test_write_report_writes_md_and_json(tmp_path):
    report = _report()
    out_md = tmp_path / "flow.md"
    out_json = tmp_path / "flow.json"
    rendered = lf.write_logic_flow_report(report, out_md, out_json)
    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)
    md = out_md.read_text(encoding="utf-8")
    assert lf.LOGIC_FLOW_BOUNDARY in md
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["flow_intact"] == report.flow_intact
    assert loaded["boundary"] == lf.LOGIC_FLOW_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = _report()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    lf.write_logic_flow_report(report, a_md, a_json)
    lf.write_logic_flow_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    low = lf.LOGIC_FLOW_BOUNDARY.lower()
    for w in _FORBIDDEN:
        assert w not in low


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(lf)]
    for banned in ("face", "speaker", "pose", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = _report()
    payload = lf.emit_logic_flow(report, bus=_Bus(), trace=False)
    assert payload["flow_intact"] == report.flow_intact
    assert len(published) == 1
    assert published[0].topic == lf.LOGIC_FLOW_RUN_TOPIC
    assert published[0].payload["boundary"] == lf.LOGIC_FLOW_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = _report()
    payload = lf.emit_logic_flow(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["flow_intact"] == report.flow_intact
