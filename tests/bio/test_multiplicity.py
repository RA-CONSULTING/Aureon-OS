"""Tests for the multiplicity / family-wise error-rate (FWER) audit.

Across many synthetic simultaneous true-null lanes, the audit measures the probability that at least
one lane falsely fires (the FWER) as a function of the number of lanes ``k``, and confirms a
Bonferroni ``α/k`` threshold keeps that FWER at or below the nominal level at every ``k``. Synthetic
only — no real subject, never a claim about a person.
"""

from __future__ import annotations

import json

from aureon.bio import multiplicity as mp

TRIALS = 60
NULLS = 60
KS = (1, 4, 16)
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def test_null_lane_pvals_in_unit_interval():
    p_a, p_b = mp._null_lane_pvals(0, nulls=NULLS)
    assert 0.0 <= p_a <= 1.0
    assert 0.0 <= p_b <= 1.0


def test_bonferroni_controls_across_grid():
    report = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    assert report.n_points == len(KS)
    assert report.bonferroni_controls_all
    for p in report.points:
        assert p.fwer_bonferroni <= report.alpha + report.tolerance
        # any-of-k fires at least as often as the mean per-lane rate
        assert p.fwer_uncorrected >= p.per_lane_rate - 1e-9
        assert 0.0 <= p.per_lane_rate <= 1.0
        assert 0.0 <= p.fwer_uncorrected <= 1.0
        assert 0.0 <= p.fwer_bonferroni <= 1.0


def test_uncorrected_fwer_non_decreasing_in_k():
    report = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    fwers = [p.fwer_uncorrected for p in report.points]
    for lo, hi in zip(fwers, fwers[1:], strict=False):
        assert hi >= lo - 0.02  # soft: more lanes never meaningfully lowers the family rate


def test_compute_is_deterministic():
    r1 = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    r2 = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    assert r1.to_dict() == r2.to_dict()


def test_write_report_writes_md_and_json(tmp_path):
    report = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    out_md = tmp_path / "mult.md"
    out_json = tmp_path / "mult.json"
    rendered = mp.write_multiplicity_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert mp.MULTIPLICITY_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_points + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_points"] == report.n_points
    assert loaded["boundary"] == mp.MULTIPLICITY_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    mp.write_multiplicity_report(mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0), a_md, a_json)
    mp.write_multiplicity_report(mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0), b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    report = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    d = report.to_dict()
    assert d["boundary"] == mp.MULTIPLICITY_BOUNDARY
    for p in report.points:
        for key, value in p.to_dict().items():
            if isinstance(value, str):
                low = value.lower()
                for w in _FORBIDDEN:
                    assert w not in low, f"point field {key!r} leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(mp)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    payload = mp.emit_multiplicity(report, bus=_Bus(), trace=False)
    assert payload["n_points"] == report.n_points
    assert len(published) == 1
    assert published[0].topic == mp.MULT_RUN_TOPIC
    assert published[0].payload["bonferroni_controls_all"] == report.bonferroni_controls_all
    assert published[0].payload["boundary"] == mp.MULTIPLICITY_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = mp.compute_multiplicity(trials=TRIALS, nulls=NULLS, ks=KS, seed0=0)
    payload = mp.emit_multiplicity(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["n_points"] == report.n_points
