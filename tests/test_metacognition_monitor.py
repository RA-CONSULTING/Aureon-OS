"""
MetacognitionMonitor — the organism reads its own signals and loops back.

Offline + hermetic: an isolated AUREON_BUS_TRACE_DIR + metacognition lambda path
per test, and a fresh global bus seeded with the self-signals. Proves the
assessment is honest (truth_status, no fabrication) and that reflect() closes the
loop by publishing the ``metacognition_monitor`` sub-field back into the field.
"""

from __future__ import annotations

import json
import time

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.bus_trace import append_trace
from aureon.core.hnc_field import read_subfields
from aureon.core.metacognition_monitor import MetacognitionMonitor
from aureon.observer.real_data_contract import TRUTH_STATUSES


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_METACOG_LAMBDA_PATH", str(tmp_path / "metacog_lambda.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    import aureon.core.aureon_thought_bus as tb

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    return tmp_path


def _hnc_envelope(symbolic_life_score, coherence_gamma, consciousness_psi=None):
    received_at = time.time()
    psi = coherence_gamma if consciousness_psi is None else consciousness_psi
    return {
        "data_status": "live",
        "source": "hnc_live_daemon",
        "source_id": "aureon:hnc:live_daemon",
        "source_timestamp": received_at,
        "received_at": received_at,
        "ts": received_at,
        "receipt_id": "hnc:live_field:test-metacognition",
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": ["test.provider:metacognition"],
        "freshness_status": "fresh",
        "symbolic_life_score": symbolic_life_score,
        "coherence_gamma": coherence_gamma,
        "consciousness_psi": psi,
        "consciousness_level": "AWARE",
        "lambda_t": symbolic_life_score,
        "source_count": 1,
        "operational_eligible": False,
        "provider_eligible": False,
        "action_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "equation_inputs_complete": True,
        "action_gate_passed": False,
        "action_gate_reason": "route_specific_market_link_required",
    }


def _seed_signals():
    b = get_thought_bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload=_hnc_envelope(0.6, 0.9, 0.4)))
    append_trace("auris_cosmic_state", {"cosmic_score": 0.7, "gate_open": True, "_ts": 1.0})
    append_trace("lighthouse_event", {"type": "PHASE_RESET", "severity": 0.2, "_ts": 1.0})
    append_trace("local_action_verdict", {"approved": True, "verdict": "APPROVED"})
    return b


def test_assess_returns_scored_self_state():
    _seed_signals()
    a = MetacognitionMonitor().assess()
    assert a.available is True
    assert a.truth_status in TRUTH_STATUSES
    # the Master-Formula machinery scored the organism's own signals
    assert a.self_coherence is not None
    assert a.psi is not None
    assert a.consciousness_level is not None
    # per-signal provenance, drawn from the contract vocabulary
    for sig in a.signals.values():
        assert sig.get("truth_status") in TRUTH_STATUSES or "blocker" in sig


def test_assess_is_read_only_does_not_publish():
    _seed_signals()
    b = get_thought_bus()
    MetacognitionMonitor().assess()
    assert "metacognition_monitor" not in read_subfields(b)  # assess never publishes


def test_reflect_closes_the_loop():
    b = _seed_signals()
    before = "metacognition_monitor" in read_subfields(b)
    MetacognitionMonitor().reflect()
    after = "metacognition_monitor" in read_subfields(b)
    assert before is False and after is True  # the self-assessment fed back into the field


def test_no_signals_is_no_data_never_fabricated(monkeypatch, tmp_path):
    # Fresh bus with no pulse, empty trace dir, and no field trace → honest no_data.
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "absent.jsonl"))
    from aureon.core import aureon_thought_bus as tb

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    a = MetacognitionMonitor().assess()
    # With nothing flowing the monitor reports no_data — no invented coherence.
    assert a.truth_status == "no_data"
    assert a.available is False or a.self_coherence is None


def test_trace_field_is_classified_as_cached_real(tmp_path):
    (tmp_path / "hnc_trace.jsonl").write_text(
        json.dumps(_hnc_envelope(0.61, 0.59)) + "\n",
        encoding="utf-8",
    )
    a = MetacognitionMonitor().assess()
    assert a.signals["field"]["truth_status"] == "cached_real"


def test_self_term_persists_across_ticks():
    _seed_signals()
    m = MetacognitionMonitor()
    m.reflect()
    # the engine accumulated history (the β·Λ(t−τ) echo store) across the tick
    assert len(m._engine._history) >= 1  # noqa: SLF001 — asserting the self-term store grew
    n0 = len(m._engine._history)  # noqa: SLF001
    m.reflect()
    assert len(m._engine._history) > n0  # noqa: SLF001 — grows each reflect
