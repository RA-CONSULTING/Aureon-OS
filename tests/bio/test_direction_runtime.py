"""Tests for the runtime direction audit — is the canonical field load-bearing at each real consumer?

Drives all five real adaptive consumers with the canonical HNC field set low then high and asserts each
output changes. Deterministic (two fixed field values); byte-identical artifacts; never a claim about a
person.
"""

from __future__ import annotations

import copy
import json

from aureon.bio import direction_runtime as dr

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")
_NOW = 1_800_000_000.0


def _receipts():
    low_id = "canonical-field-low-24711"
    high_id = "canonical-field-high-24711"
    hnc_id = "hnc-direction-24711"
    common = {
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_cognition": True,
        "eligible_for_publication": True,
        "equation_inputs_complete": True,
        "evaluation_id": "direction-evaluation-24711",
        "consumer_set_id": dr.DIRECTION_RUNTIME_CONSUMER_SET_ID,
        "source_timestamp": _NOW - 2,
        "received_at": _NOW - 1,
    }
    hnc = {
        **common,
        "receipt_id": hnc_id,
        "source_id": "aureon-hnc-field",
        "provider_receipt_type": "HNCDirectionEvaluation",
        "equation_id": "hnc-direction-equation-v1",
        "input_receipt_ids": [low_id, high_id],
        "low_field_receipt_id": low_id,
        "high_field_receipt_id": high_id,
        "low_field_value": "0.05",
        "high_field_value": "0.95",
        "hnc_signal": "0.72",
    }
    auris = {
        **common,
        "receipt_id": "auris-direction-24711",
        "source_id": "aureon-auris-engine",
        "provider_receipt_type": "AurisDirectionEvaluation",
        "equation_id": "auris-direction-equation-v1",
        "input_receipt_ids": [low_id, high_id, hnc_id],
        "hnc_receipt_id": hnc_id,
        "low_field_receipt_id": low_id,
        "high_field_receipt_id": high_id,
        "auris_signal": "0.68",
        "consumer_names": [
            name for name, _module, _note, _runner in dr.consumer_specs()
        ],
    }
    return hnc, auris


def _report():
    hnc, auris = _receipts()
    return dr.compute_direction_runtime(
        evaluators=dr.deterministic_evaluators(),
        hnc_receipt=hnc,
        auris_receipt=auris,
        clock=lambda: _NOW,
    )


# ── the audit ────────────────────────────────────────────────────────────────────────────────────


def test_all_consumers_are_swayed_by_the_field():
    report = _report()
    assert report.n_consumers == len(dr.consumer_specs()) and report.n_consumers >= 5
    assert report.all_sway
    assert report.n_inert == 0
    assert not report.inert_names
    assert report.eligible_for_cognition is True
    assert report.eligible_for_publication is True


def test_each_consumer_output_actually_moves():
    report = _report()
    for r in report.readings:
        assert r["sways"], f"{r['name']} did not move with the field"
        assert r["delta"] > 0.0
        assert r["output_low"] != r["output_high"]


def test_kelly_buffer_widens_as_field_falls():
    # The Kelly reading is r_prime_buffer at low vs high Γ; a lower field must WIDEN the buffer.
    report = _report()
    kelly = next(r for r in report.readings if r["name"] == "kelly_gate")
    assert kelly["output_low"] > kelly["output_high"]  # low coherence → wider safety buffer


def test_conscience_veto_relaxes_as_field_rises():
    report = _report()
    c = next(r for r in report.readings if r["name"] == "queen_conscience")
    assert c["output_low"] < c["output_high"]  # low SLS = VETO(0.0) → higher SLS = CONCERNED(0.5)


def test_compute_is_deterministic():
    assert _report().to_dict() == _report().to_dict()


# ── the report ─────────────────────────────────────────────────────────────────────────────────


def test_write_report_writes_md_and_json(tmp_path):
    report = _report()
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
    report = _report()
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

    report = _report()
    payload = dr.emit_direction_runtime(report, bus=_Bus(), trace=False)
    assert payload["all_sway"] == report.all_sway
    assert len(published) == 1
    assert published[0].topic == dr.DIRECTION_RUNTIME_RUN_TOPIC


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = _report()
    payload = dr.emit_direction_runtime(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["all_sway"] == report.all_sway


def test_invalid_evidence_is_numeric_free_no_data_and_never_publishes(tmp_path):
    published = []
    traced = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = dr.compute_direction_runtime(
        evaluators=dr.deterministic_evaluators(),
        clock=lambda: _NOW,
    )
    payload = report.to_dict()
    assert payload["data_status"] == "no_data"
    assert payload["truth_status"] == "no_data"
    assert payload["eligible_for_cognition"] is False
    assert payload["eligible_for_publication"] is False

    def assert_numeric_free(value):
        if isinstance(value, dict):
            for nested in value.values():
                assert_numeric_free(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                assert_numeric_free(nested)
        else:
            assert not (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

    assert_numeric_free(payload)
    out_md = tmp_path / "withheld.md"
    out_json = tmp_path / "withheld.json"
    assert dr.write_direction_runtime_report(
        report,
        out_md,
        out_json,
    ) is report
    assert not out_md.exists()
    assert not out_json.exists()
    assert dr.emit_direction_runtime(
        report,
        bus=_Bus(),
        trace_writer=lambda *args: traced.append(args),
    ) == payload
    assert published == []
    assert traced == []

    hnc, auris = _receipts()
    broken = copy.deepcopy(auris)
    broken["hnc_receipt_id"] = "unlinked-hnc-receipt-24711"
    unlinked = dr.compute_direction_runtime(
        evaluators=dr.deterministic_evaluators(),
        hnc_receipt=hnc,
        auris_receipt=broken,
        clock=lambda: _NOW,
    )
    assert unlinked.data_status == "no_data"
    assert unlinked.reason == "auris_hnc_receipt_link_mismatch"
    assert_numeric_free(unlinked.to_dict())
