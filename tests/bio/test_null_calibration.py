"""Tests for the null-calibration / false-positive-rate audit.

The audit runs the engine's own Test A + Test B on each adapter's synthetic *null* signal
many times and asserts the empirical false-``structure_present`` rate stays within the
pre-registered bound (≤ ALPHA) while the structured anchor still fires. Synthetic only — no
real subject, no cross-modal inference, never a claim about a person.
"""

from __future__ import annotations

import json

import numpy as np

from aureon.bio import null_calibration as nc

TRIALS = 50
NULLS = 100
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")
_EXPECTED_MODALITIES = {"synthetic", "audio", "video", "upe"}


# ---------------------------------------------------------------------------
# the detection rule directly
# ---------------------------------------------------------------------------


def test_structure_present_true_on_structured_tones():
    # two tight clusters one golden ratio apart, in-band (the engine's own positive shape)
    base = 1100.0
    phi = float(nc.engine.PHI)
    tones = np.array([base - 4, base, base + 4, base * phi - 4, base * phi, base * phi + 4])
    assert nc._structure_present(tones, nulls=300, seed=0) is True


def test_structure_present_false_on_spread_tones():
    # evenly spaced, no clustering (<25 Hz) and no φ ratios -> absent
    tones = np.array([1000.0, 1150.0, 1300.0, 1450.0, 1600.0, 1750.0])
    assert nc._structure_present(tones, nulls=300, seed=0) is False


def test_structure_present_needs_two_tones():
    assert nc._structure_present(np.array([1500.0]), nulls=300, seed=0) is False


# ---------------------------------------------------------------------------
# the family-wide audit
# ---------------------------------------------------------------------------


def test_calibrate_nulls_all_adapters_conform():
    report = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    assert report.n_adapters == 4
    assert report.n_conforming == report.n_adapters
    assert {r.modality for r in report.readings} == _EXPECTED_MODALITIES
    for r in report.readings:
        assert r.structured_fires, f"{r.adapter} structured anchor did not fire"
        assert r.fpr <= nc.ALPHA, f"{r.adapter} FPR {r.fpr} exceeds ALPHA {nc.ALPHA}"
        assert r.false_positives <= r.trials
        assert r.conforms


def test_calibrate_nulls_is_deterministic():
    r1 = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    r2 = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# durable evidence artifact, byte-identical on re-run
# ---------------------------------------------------------------------------


def test_write_calibration_report_writes_md_and_json(tmp_path):
    report = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    out_md = tmp_path / "cal.md"
    out_json = tmp_path / "cal.json"
    rendered = nc.write_calibration_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert nc.CALIBRATION_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_adapters + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_adapters"] == report.n_adapters
    assert loaded["boundary"] == nc.CALIBRATION_BOUNDARY


def test_write_calibration_report_is_byte_identical_on_rewrite(tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    nc.write_calibration_report(nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0), a_md, a_json)
    nc.write_calibration_report(nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0), b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


# ---------------------------------------------------------------------------
# boundary + governance surface
# ---------------------------------------------------------------------------


def test_boundary_present_and_no_subject_claims():
    report = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    d = report.to_dict()
    assert d["boundary"] == nc.CALIBRATION_BOUNDARY
    for r in report.readings:
        for key, value in r.to_dict().items():
            if not isinstance(value, str):
                continue
            low = value.lower()
            for w in _FORBIDDEN:
                assert w not in low, f"{r.adapter} field {key!r} leaked {w!r}: {value!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(nc)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


# ---------------------------------------------------------------------------
# cognition emission
# ---------------------------------------------------------------------------


def test_emit_calibration_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    payload = nc.emit_calibration(report, bus=_Bus(), trace=False)
    assert payload["n_adapters"] == report.n_adapters
    assert len(published) == 1
    t = published[0]
    assert t.topic == nc.CAL_RUN_TOPIC
    assert t.payload["n_conforming"] == report.n_conforming
    assert t.payload["boundary"] == nc.CALIBRATION_BOUNDARY


def test_emit_calibration_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = nc.calibrate_nulls(trials=TRIALS, nulls=NULLS, seed0=0)
    payload = nc.emit_calibration(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["n_adapters"] == report.n_adapters
