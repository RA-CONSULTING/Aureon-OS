"""Tests for the runtime direction audit — is the canonical field load-bearing at each real consumer?

Drives all five real adaptive consumers with the canonical HNC field set low then high and asserts each
output changes. Deterministic (two fixed field values); byte-identical artifacts; never a claim about a
person.
"""

from __future__ import annotations

import json

from aureon.bio import direction_runtime as dr

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


# ── the audit ────────────────────────────────────────────────────────────────────────────────────


def test_all_consumers_are_swayed_by_the_field():
    report = dr.compute_direction_runtime()
    assert report.n_consumers == len(dr.consumer_specs()) and report.n_consumers >= 5
    assert report.all_sway
    assert report.n_inert == 0
    assert not report.inert_names


def test_each_consumer_output_actually_moves():
    report = dr.compute_direction_runtime()
    for r in report.readings:
        assert r["sways"], f"{r['name']} did not move with the field"
        assert r["delta"] > 0.0
        assert r["output_low"] != r["output_high"]


def test_kelly_buffer_widens_as_field_falls():
    # The Kelly reading is r_prime_buffer at low vs high Γ; a lower field must WIDEN the buffer.
    report = dr.compute_direction_runtime()
    kelly = next(r for r in report.readings if r["name"] == "kelly_gate")
    assert kelly["output_low"] > kelly["output_high"]  # low coherence → wider safety buffer


def test_conscience_veto_relaxes_as_field_rises():
    report = dr.compute_direction_runtime()
    c = next(r for r in report.readings if r["name"] == "queen_conscience")
    assert c["output_low"] < c["output_high"]  # low SLS = VETO(0.0) → higher SLS = CONCERNED(0.5)


def test_compute_is_deterministic():
    assert dr.compute_direction_runtime().to_dict() == dr.compute_direction_runtime().to_dict()


# ── the report ─────────────────────────────────────────────────────────────────────────────────


def test_write_report_writes_md_and_json(tmp_path):
    report = dr.compute_direction_runtime()
    out_md = tmp_path / "dr.md"
    out_json = tmp_path / "dr.json"
    rendered = dr.write_direction_runtime_report(report, out_md, out_json)
    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)
    assert dr.DIRECTION_RUNTIME_BOUNDARY in out_md.read_text(encoding="utf-8")
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["all_sway"] == report.all_sway
    assert loaded["boundary"] == dr.DIRECTION_RUNTIME_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = dr.compute_direction_runtime()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    dr.write_direction_runtime_report(report, a_md, a_json)
    dr.write_direction_runtime_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    low = dr.DIRECTION_RUNTIME_BOUNDARY.lower()
    for w in _FORBIDDEN:
        assert w not in low


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(dr)]
    for banned in ("face", "speaker", "pose", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = dr.compute_direction_runtime()
    payload = dr.emit_direction_runtime(report, bus=_Bus(), trace=False)
    assert payload["all_sway"] == report.all_sway
    assert len(published) == 1
    assert published[0].topic == dr.DIRECTION_RUNTIME_RUN_TOPIC


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = dr.compute_direction_runtime()
    payload = dr.emit_direction_runtime(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["all_sway"] == report.all_sway
