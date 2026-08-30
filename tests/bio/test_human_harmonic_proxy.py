"""Tests for the human-harmonic proxy (derived-signal phenolic scoring).

The Operator hard-boundary layer runs for real in every test; only the Queen
conscience is stubbed (via an autouse APPROVED stub) so the suite stays fast and
quiet. The real conscience path is exercised end-to-end by the module's CLI
self-test (``python -m aureon.bio.human_harmonic_proxy``).
"""

from __future__ import annotations

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.core.aureon_thought_bus import ThoughtBus

# nulls kept modest for speed; the planted structured signal saturates the
# clustering/phi statistics, so its p-value is ~1/(nulls+1) << ALPHA.
NULLS = 300

# words that would signal a claim *about a person* — none may appear outside the
# fixed scientific-boundary disclaimer.
_FORBIDDEN_CLAIM_WORDS = (
    "diagnos", "disease", "healthy", "illness", "personality", "trait",
    "chakra", "psychic", "cure", "heal", "efficacy",
)


class _StubConscience:
    def __init__(self, verdict_name: str) -> None:
        self._verdict = verdict_name

    def ask_why(self, action, context=None):
        return SimpleNamespace(
            verdict=SimpleNamespace(name=self._verdict), message="", why_it_matters=""
        )


@pytest.fixture(autouse=True)
def _approved_conscience(monkeypatch):
    """Default: a fast, quiet APPROVED conscience so the veto layer never blocks."""
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# fold_to_band
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        (1500.0, 1500.0),   # already in-band -> identity
        (750.0, 1500.0),    # one octave up
        (375.0, 1500.0),    # two octaves up
        (3000.0, 1500.0),   # one octave down
        (1000.0, 1000.0),   # low bound is in-band
        (2000.0, 1000.0),   # high bound folds down
    ],
)
def test_fold_to_band_values(raw, expected):
    assert proxy.fold_to_band(raw) == pytest.approx(expected)


def test_fold_to_band_in_band_range_and_idempotent():
    low, high = proxy.TARGET_BAND_HZ
    for raw in (0.03, 7.5, 60.0, 440.0, 1234.0, 9600.0, 1_000_000.0):
        folded = proxy.fold_to_band(raw)
        assert folded is not None
        assert low <= folded < high
        assert proxy.fold_to_band(folded) == pytest.approx(folded)  # idempotent in-band


@pytest.mark.parametrize("bad", [0.0, -1.0, -1234.0, float("inf"), float("nan")])
def test_fold_to_band_rejects_invalid(bad):
    assert proxy.fold_to_band(bad) is None


# ---------------------------------------------------------------------------
# scoring: structured present, noise absent
# ---------------------------------------------------------------------------


def test_structured_signal_structure_present():
    result = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    assert result.valid is True
    assert result.blocked is False
    assert result.structure_present is True
    assert result.test_A_p < proxy.engine.ALPHA
    assert result.test_B_p < proxy.engine.ALPHA
    assert result.n_tones == 6


def test_noise_signal_structure_absent():
    result = proxy.run_synthetic("noise", seed=0, nulls=NULLS)
    assert result.valid is True
    assert result.blocked is False
    assert result.structure_present is False


def test_score_signal_is_deterministic():
    # the core scorer must be reproducible given a fixed seed — every lane relies on it
    r1 = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    r2 = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    assert (r1.test_A_p, r1.test_B_p, r1.n_tones) == (r2.test_A_p, r2.test_B_p, r2.n_tones)


# ---------------------------------------------------------------------------
# consent / provenance gate
# ---------------------------------------------------------------------------


def test_unconsented_run_is_blocked_and_scores_nothing():
    signal = replace(
        proxy.SyntheticSignalAdapter().extract(mode="structured", seed=0), consent=False
    )
    result = proxy.score_signal(signal, nulls=NULLS, seed=0)
    assert result.blocked is True
    assert result.valid is False
    d = result.to_dict()
    assert d["structure_present"] is False
    assert d["test_A_p"] is None and d["test_B_p"] is None
    assert "consent" in (result.reason or "")


def test_missing_provenance_is_blocked():
    signal = replace(
        proxy.SyntheticSignalAdapter().extract(mode="structured", seed=0), provenance="  "
    )
    result = proxy.score_signal(signal, nulls=NULLS, seed=0)
    assert result.blocked is True and result.valid is False


# ---------------------------------------------------------------------------
# scientific boundary + no claims about a person
# ---------------------------------------------------------------------------


def test_boundary_present_and_no_person_claims():
    result = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    d = result.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    # every string field OTHER than the disclaimer must be free of claim words
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for word in _FORBIDDEN_CLAIM_WORDS:
            assert word not in low, f"field {key!r} leaked claim word {word!r}: {value!r}"


# ---------------------------------------------------------------------------
# operator authority boundary
# ---------------------------------------------------------------------------


def test_conscience_veto_blocks_and_suppresses(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("VETO"))
    result = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    assert result.blocked is True
    d = result.to_dict()
    assert d["structure_present"] is False  # positive finding suppressed
    assert "veto" in (result.reason or "").lower()


def test_unreachable_conscience_fails_safe(monkeypatch):
    def _boom():
        raise RuntimeError("conscience down")

    monkeypatch.setattr(proxy, "_get_conscience", _boom)
    result = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    assert result.blocked is True
    assert "fail-safe" in (result.reason or "")
    assert result.to_dict()["structure_present"] is False


# ---------------------------------------------------------------------------
# cognition emission
# ---------------------------------------------------------------------------


def test_emit_publishes_run_topic_and_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    from aureon.core.bus_trace import read_trace_latest

    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    captured = []
    bus.subscribe("bio.*", lambda t: captured.append(t))

    result = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    payload = proxy.emit_proxy_result(result, bus=bus)

    topics = [t.topic for t in captured]
    assert topics.count(proxy.RUN_TOPIC) == 1
    run_thought = next(t for t in captured if t.topic == proxy.RUN_TOPIC)
    assert run_thought.payload["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    assert run_thought.payload["structure_present"] is True
    assert payload["boundary"] == proxy.SCIENTIFIC_BOUNDARY

    tr = read_trace_latest(proxy.TRACE_NAME)
    assert tr is not None
    assert tr["structure_present"] is True
    assert tr["blocked"] is False
    assert tr["boundary"] == proxy.SCIENTIFIC_BOUNDARY


def test_emit_blocked_result_publishes_no_positive_finding(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("VETO"))
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    captured = []
    bus.subscribe("bio.*", lambda t: captured.append(t))

    result = proxy.run_synthetic("structured", seed=0, nulls=NULLS)
    proxy.emit_proxy_result(result, bus=bus)

    run_thought = next(t for t in captured if t.topic == proxy.RUN_TOPIC)
    assert run_thought.payload["blocked"] is True
    assert run_thought.payload["structure_present"] is False


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, *a, **k):
            raise RuntimeError("bus down")

    result = proxy.run_synthetic("noise", seed=0, nulls=NULLS)
    payload = proxy.emit_proxy_result(result, bus=_BadBus(), trace=False)  # must not raise
    assert payload["valid"] is True
    assert payload["boundary"] == proxy.SCIENTIFIC_BOUNDARY
