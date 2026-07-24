"""Tests for the detection-power / sensitivity sweep.

The audit runs the engine's own Test A + Test B on the canonical structured signal as it is
progressively degraded by jitter, and reports the detection power at each level: high on the
clean signal, collapsing toward the false-positive floor as structure dissolves. Synthetic
only — no real subject, never a claim about a person.
"""

from __future__ import annotations

import json

import numpy as np

from aureon.bio import power_analysis as pa

TRIALS = 60
NULLS = 100
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


# ---------------------------------------------------------------------------
# signal + detection primitives
# ---------------------------------------------------------------------------


def test_structured_tones_clean_is_canonical_six():
    tones = pa._structured_tones(0.0, seed=0)
    assert tones.shape == (6,)
    assert np.all(np.diff(tones) >= 0)  # sorted
    # clean structure is detected
    assert pa._structure_present(tones, nulls=300, seed=0) is True


def test_heavy_jitter_usually_not_detected():
    # a single heavily-jittered draw should (almost always) not be separable
    tones = pa._structured_tones(120.0, seed=3)
    assert pa._structure_present(tones, nulls=300, seed=3) is False


# ---------------------------------------------------------------------------
# the power sweep
# ---------------------------------------------------------------------------


def test_detection_power_curve_high_then_collapses():
    report = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    assert report.n_levels == len(pa.DEFAULT_JITTER_HZ)
    # clean signal is reliably detected
    assert report.clean_power >= 0.8
    # power collapses as the signal dissolves into noise
    assert report.degraded_power <= 0.3
    assert report.degraded_power < report.clean_power
    # monotonically non-increasing (small tolerance for sampling noise)
    powers = [lv.power for lv in report.levels]
    for a, b in zip(powers, powers[1:], strict=False):
        assert b <= a + 0.15, f"power rose too much: {powers}"


def test_detection_power_is_deterministic():
    r1 = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    r2 = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# durable evidence artifact, byte-identical on re-run
# ---------------------------------------------------------------------------


def test_write_power_report_writes_md_and_json(tmp_path):
    report = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    out_md = tmp_path / "power.md"
    out_json = tmp_path / "power.json"
    rendered = pa.write_power_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert pa.POWER_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_levels + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_levels"] == report.n_levels
    assert loaded["boundary"] == pa.POWER_BOUNDARY


def test_write_power_report_is_byte_identical_on_rewrite(tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    pa.write_power_report(pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0), a_md, a_json)
    pa.write_power_report(pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0), b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


# ---------------------------------------------------------------------------
# boundary + governance surface
# ---------------------------------------------------------------------------


def test_boundary_present_and_no_subject_claims():
    report = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    d = report.to_dict()
    assert d["boundary"] == pa.POWER_BOUNDARY
    for lv in report.levels:
        for key, value in lv.to_dict().items():
            if isinstance(value, str):
                low = value.lower()
                for w in _FORBIDDEN:
                    assert w not in low, f"level field {key!r} leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(pa)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


# ---------------------------------------------------------------------------
# cognition emission
# ---------------------------------------------------------------------------


def test_emit_power_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    payload = pa.emit_power(report, bus=_Bus(), trace=False)
    assert payload["n_levels"] == report.n_levels
    assert len(published) == 1
    t = published[0]
    assert t.topic == pa.POWER_RUN_TOPIC
    assert t.payload["clean_power"] == report.clean_power
    assert t.payload["boundary"] == pa.POWER_BOUNDARY


def test_emit_power_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = pa.detection_power(trials=TRIALS, nulls=NULLS, seed0=0)
    payload = pa.emit_power(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["n_levels"] == report.n_levels
