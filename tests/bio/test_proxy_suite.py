"""Tests for the signal-adapter conformance suite (capstone roll-up).

The suite runs each self-testable adapter's synthetic structured + null self-test through
the one unchanged ``score_signal`` and reports whether each conforms. Synthetic only — no
real subject, no cross-modal inference, and never a claim about a person.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import proxy_suite as suite

NULLS = 300
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")
_EXPECTED_MODALITIES = {"synthetic", "audio", "video", "upe"}


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# the roll-up: every adapter conforms
# ---------------------------------------------------------------------------


def test_run_suite_all_adapters_conform():
    report = suite.run_suite(nulls=NULLS, seed=0)
    assert report.n_adapters == 4
    assert report.n_conforming == report.n_adapters
    assert {r.modality for r in report.readings} == _EXPECTED_MODALITIES
    for r in report.readings:
        assert r.present_valid and r.present_structure, f"{r.adapter} structured not present"
        assert r.absent_valid and not r.absent_structure, f"{r.adapter} null not absent"
        assert r.conforms


def test_run_suite_is_deterministic():
    r1 = suite.run_suite(nulls=200, seed=0)
    r2 = suite.run_suite(nulls=200, seed=0)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# durable evidence artifact (markdown + JSON), byte-identical on re-run
# ---------------------------------------------------------------------------


def test_write_suite_report_writes_md_and_json(tmp_path):
    report = suite.run_suite(nulls=120, seed=0)
    out_md = tmp_path / "suite.md"
    out_json = tmp_path / "suite.json"
    rendered = suite.write_suite_report(report, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert suite.SUITE_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == report.n_adapters + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["n_adapters"] == report.n_adapters
    assert loaded["boundary"] == suite.SUITE_BOUNDARY


def test_write_suite_report_is_byte_identical_on_rewrite(tmp_path):
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    suite.write_suite_report(suite.run_suite(nulls=120, seed=0), a_md, a_json)
    suite.write_suite_report(suite.run_suite(nulls=120, seed=0), b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


# ---------------------------------------------------------------------------
# boundary + governance surface
# ---------------------------------------------------------------------------


def test_boundary_present_and_no_subject_claims():
    report = suite.run_suite(nulls=120, seed=0)
    d = report.to_dict()
    assert d["boundary"] == suite.SUITE_BOUNDARY
    # no forbidden claim words leak into any non-boundary string field
    for r in report.readings:
        for key, value in r.to_dict().items():
            if not isinstance(value, str):
                continue
            low = value.lower()
            for w in _FORBIDDEN:
                assert w not in low, f"{r.adapter} field {key!r} leaked {w!r}: {value!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(suite)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


# ---------------------------------------------------------------------------
# cognition emission
# ---------------------------------------------------------------------------


def test_emit_suite_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = suite.run_suite(nulls=120, seed=0)
    payload = suite.emit_suite(report, bus=_Bus(), trace=False)
    assert payload["n_adapters"] == report.n_adapters
    assert len(published) == 1
    t = published[0]
    assert t.topic == suite.SUITE_RUN_TOPIC
    assert t.payload["n_conforming"] == report.n_conforming
    assert t.payload["boundary"] == suite.SUITE_BOUNDARY


def test_emit_suite_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = suite.run_suite(nulls=120, seed=0)
    # must not raise
    payload = suite.emit_suite(report, bus=_BadBus(), trace=False)
    assert payload["n_adapters"] == report.n_adapters
