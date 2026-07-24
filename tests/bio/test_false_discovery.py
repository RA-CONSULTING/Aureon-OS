"""Tests for the false-discovery-rate (Benjamini–Hochberg) audit.

Across many synthetic families mixing true-null and true-signal lanes, the audit measures the
false-discovery rate and power of three decision rules (uncorrected / Bonferroni / BH) and confirms
that Benjamini–Hochberg controls the FDR at the nominal level while rejecting a superset of what
Bonferroni rejects (so it recovers more true detections). Synthetic only — no real subject, never a
claim about a person.
"""

from __future__ import annotations

import json

import numpy as np

from aureon.bio import false_discovery as fd

TRIALS = 12
NULLS = 300
M_NULL = 5
M_SIGNAL = 5
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def _report():
    return fd.compute_false_discovery(
        trials=TRIALS, nulls=NULLS, m_null=M_NULL, m_signal=M_SIGNAL, seed0=0
    )


def test_bh_reject_matches_hand_computed():
    q = 0.05
    # m=5, thresholds (i/5)*q = [0.01, 0.02, 0.03, 0.04, 0.05]; largest passing rank is 0.012 → cutoff.
    mask = fd._bh_reject(np.array([0.001, 0.008, 0.012, 0.20, 0.60]), q)
    assert list(mask) == [True, True, True, False, False]
    # order-independence: a lane below the step-up cutoff is rejected wherever it sits.
    mask2 = fd._bh_reject(np.array([0.04, 0.001]), q)  # m=2, thr=[0.025, 0.05]; cutoff 0.04
    assert list(mask2) == [True, True]
    # nothing passes → reject none.
    mask3 = fd._bh_reject(np.array([0.5, 0.6]), q)
    assert not mask3.any()
    # empty input is safe.
    assert fd._bh_reject(np.array([]), q).shape == (0,)


def test_bh_controls_fdr_and_dominates_bonferroni():
    report = _report()
    assert report.n_methods == 3
    assert report.bh_controls_fdr
    assert report.bh_dominates_bonferroni
    by_name = {m.name: m for m in report.methods}
    bh, bonf, unc = by_name["benjamini_hochberg"], by_name["bonferroni"], by_name["uncorrected"]
    assert bh.fdr <= report.q + report.tolerance
    # BH ⊇ Bonferroni ⇒ at least as many rejections and at least as much power.
    assert bh.power >= bonf.power - 1e-9
    assert bh.mean_rejections >= bonf.mean_rejections - 1e-9
    # uncorrected is the most lenient rule ⇒ at least as much power as BH.
    assert unc.power >= bh.power - 1e-9
    for m in report.methods:
        assert 0.0 <= m.fdr <= 1.0
        assert 0.0 <= m.power <= 1.0
        assert m.mean_rejections >= 0.0


def test_compute_is_deterministic():
    r1 = _report()
    r2 = _report()
    assert r1.to_dict() == r2.to_dict()


def test_write_report_writes_md_and_json(tmp_path):
    report = _report()
    out_md = tmp_path / "fdr.md"
    out_json = tmp_path / "fdr.json"
    rendered = fd.write_false_discovery_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert fd.FALSE_DISCOVERY_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_methods + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_methods"] == report.n_methods
    assert loaded["boundary"] == fd.FALSE_DISCOVERY_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = _report()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    fd.write_false_discovery_report(report, a_md, a_json)
    fd.write_false_discovery_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    report = _report()
    d = report.to_dict()
    assert d["boundary"] == fd.FALSE_DISCOVERY_BOUNDARY
    for m in report.methods:
        for key, value in m.to_dict().items():
            if isinstance(value, str):
                low = value.lower()
                for w in _FORBIDDEN:
                    assert w not in low, f"method field {key!r} leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(fd)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = _report()
    payload = fd.emit_false_discovery(report, bus=_Bus(), trace=False)
    assert payload["n_methods"] == report.n_methods
    assert len(published) == 1
    assert published[0].topic == fd.FDR_RUN_TOPIC
    assert published[0].payload["bh_controls_fdr"] == report.bh_controls_fdr
    assert published[0].payload["boundary"] == fd.FALSE_DISCOVERY_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = _report()
    payload = fd.emit_false_discovery(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["n_methods"] == report.n_methods
