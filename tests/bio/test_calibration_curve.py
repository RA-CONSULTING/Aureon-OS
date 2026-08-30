"""Tests for the per-test null-calibration curve.

Under many synthetic true-null draws, the audit measures how often Test A, Test B, and their
conjunction reject across an α grid, and confirms the detection rule (the conjunction) stays at or
below its nominal size. Synthetic only — no real subject, never a claim about a person.
"""

from __future__ import annotations

import json

from aureon.bio import calibration_curve as cc

TRIALS = 200
NULLS = 100
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def test_null_tones_are_in_band_and_sorted():
    tones = cc._null_tones(0)
    lo, hi = cc.engine.TARGET_BAND_HZ
    assert tones.shape == (cc._NULL_TONE_COUNT,)
    assert all(lo <= t < hi for t in tones)
    assert list(tones) == sorted(tones)


def test_detection_rule_conservative_across_grid():
    report = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    assert report.n_points == len(cc.DEFAULT_ALPHAS)
    assert report.joint_conservative
    assert report.test_A_conservative
    assert report.max_joint_exceedance <= report.tolerance
    for p in report.points:
        # the conjunction rejects only when both do, so its rate can't exceed either test's
        assert p.rate_joint <= p.rate_A + 1e-9
        assert p.rate_joint <= p.rate_B + 1e-9
        assert 0.0 <= p.rate_joint <= 1.0
        assert p.rate_joint <= p.alpha + report.tolerance


def test_compute_is_deterministic():
    r1 = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    r2 = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    assert r1.to_dict() == r2.to_dict()


def test_write_curve_report_writes_md_and_json(tmp_path):
    report = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    out_md = tmp_path / "curve.md"
    out_json = tmp_path / "curve.json"
    rendered = cc.write_curve_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert cc.CALIBRATION_CURVE_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_points + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_points"] == report.n_points
    assert loaded["boundary"] == cc.CALIBRATION_CURVE_BOUNDARY


def test_write_curve_report_is_byte_identical_on_rewrite(tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    cc.write_curve_report(cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0), a_md, a_json)
    cc.write_curve_report(cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0), b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    report = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    d = report.to_dict()
    assert d["boundary"] == cc.CALIBRATION_CURVE_BOUNDARY
    for p in report.points:
        for key, value in p.to_dict().items():
            if isinstance(value, str):
                low = value.lower()
                for w in _FORBIDDEN:
                    assert w not in low, f"point field {key!r} leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(cc)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_curve_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    payload = cc.emit_curve(report, bus=_Bus(), trace=False)
    assert payload["n_points"] == report.n_points
    assert len(published) == 1
    assert published[0].topic == cc.CURVE_RUN_TOPIC
    assert published[0].payload["joint_conservative"] == report.joint_conservative
    assert published[0].payload["boundary"] == cc.CALIBRATION_CURVE_BOUNDARY


def test_emit_curve_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = cc.compute_calibration(trials=TRIALS, nulls=NULLS, seed0=0)
    payload = cc.emit_curve(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["n_points"] == report.n_points
