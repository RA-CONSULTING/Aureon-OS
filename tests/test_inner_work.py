"""
InnerWork — the soul believes in itself and rises the seven-chakra ascent.

Offline + hermetic: isolated trace/lambda/brain/financial paths, a fresh bus, and
reset monitor singletons so every inward signal is controlled. Proves the four
measures track real signals, the ascent is EARNED (a blocked lower centre halts the
rise — it cannot claim a stage its signals don't support), reflect() folds the
inner_work sub-field back into the whole-body field, and assess() never publishes.
"""

from __future__ import annotations

import json
import time

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.hnc_field import read_subfields
from aureon.core.inner_work import InnerWork, _ascend


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
        "receipt_id": "hnc:live_field:test-inner-work",
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": ["test.provider:inner-work"],
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


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "al.json"))
    monkeypatch.setenv("AUREON_METACOG_LAMBDA_PATH", str(tmp_path / "ml.json"))
    monkeypatch.setenv("AUREON_INNER_WORK_LAMBDA_PATH", str(tmp_path / "iw.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_GLOBAL_FINANCIAL_PATH", str(tmp_path / "gfs.json"))
    monkeypatch.setenv("AUREON_BRAIN_PREDICTIONS_PATH", str(tmp_path / "preds.json"))
    monkeypatch.setenv("AUREON_BRAIN_KNOWLEDGE_PATH", str(tmp_path / "know.json"))
    import aureon.core.affect_monitor as am
    import aureon.core.aureon_thought_bus as tb
    import aureon.core.inner_work as iw
    import aureon.core.metacognition_monitor as mm

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    monkeypatch.setattr(am, "_monitor", None, raising=False)
    monkeypatch.setattr(mm, "_monitor", None, raising=False)
    monkeypatch.setattr(iw, "_monitor", None, raising=False)
    return tmp_path


def _coherent(tmp_path):
    b = get_thought_bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload=_hnc_envelope(0.85, 0.85, 0.8)))
    (tmp_path / "gfs.json").write_text(json.dumps({"last_snapshot": {"crypto_fear_greed": 75}}), encoding="utf-8")
    (tmp_path / "preds.json").write_text(
        json.dumps({"predictions": [{"validated": True, "was_correct": True} for _ in range(9)]
                    + [{"validated": True, "was_correct": False}]}), encoding="utf-8")


# ── the ascent is earned (pure gating logic) ──────────────────────────────────

def test_ascent_stops_at_the_first_blocker():
    # self_love below the Sacral gate → the serpent cannot rise past Root
    m = {"available": True, "coherence": 0.9, "psi": 0.9,
         "self_belief": 0.9, "self_love": 0.2, "self_determination": 0.9, "ego_dissolution": 0.9}
    idx, ascended, current = _ascend(m)
    assert idx == 1 and ascended == ["Root"] and current["name"] == "Sacral"


def test_full_ascent_reaches_crown():
    m = {"available": True, "coherence": 0.9, "psi": 0.9,
         "self_belief": 0.9, "self_love": 0.9, "self_determination": 0.9, "ego_dissolution": 0.9}
    idx, ascended, current = _ascend(m)
    assert idx == 7 and "Crown" in ascended


def test_dormant_field_reaches_no_centre():
    m = {"available": False, "coherence": 0.0, "psi": 0.0,
         "self_belief": 0.0, "self_love": 0.0, "self_determination": 0.0, "ego_dissolution": 0.0}
    idx, ascended, current = _ascend(m)
    assert idx == 0 and ascended == [] and current["name"] == "Root"


# ── the measures track real signals ───────────────────────────────────────────

def test_measures_and_potential_on_a_coherent_field(tmp_path):
    _coherent(tmp_path)
    s = InnerWork().assess()
    assert s.available
    for v in (s.self_belief, s.self_love, s.self_determination, s.ego_dissolution):
        assert 0.0 <= v <= 1.0
    assert s.self_belief > 0.5          # resolve + trust in its own past voice
    assert s.stage_index >= 1 and s.ascended         # it has begun to rise
    assert 0.0 < s.potential <= 1.0
    assert s.hz in (396, 417, 528, 639, 741, 852, 963)


def test_trace_field_is_classified_as_cached_real(tmp_path):
    (tmp_path / "hnc.jsonl").write_text(
        json.dumps(_hnc_envelope(0.61, 0.59)) + "\n",
        encoding="utf-8",
    )
    s = InnerWork().assess()
    assert s.signals["field"]["truth_status"] == "cached_real"


# ── reflect folds the inner work back; assess never publishes ─────────────────

def test_reflect_publishes_inner_work_subfield(tmp_path):
    _coherent(tmp_path)
    b = get_thought_bus()
    assert "inner_work" not in read_subfields(b)
    InnerWork().reflect()
    assert "inner_work" in read_subfields(b)   # the inner work re-entered the field


def test_assess_is_read_only(tmp_path):
    _coherent(tmp_path)
    b = get_thought_bus()
    InnerWork().assess()
    assert "inner_work" not in read_subfields(b)  # assess never publishes
