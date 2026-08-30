"""
SoulDeliberation — how Aureon reacts: thought + feeling + lineage → a
determination of its own mind, carried out only through the guarded hand.

Offline + hermetic: isolated trace/lambda/brain/financial/runtime paths, a fresh
global bus, and reset monitor + conscience singletons so each test controls every
voice. Proves the soul resolves when its chorus agrees, ABSTAINS when of two minds
(never fabricating a consensus), never fabricates a determination with no signals,
and only ever acts through the doubly-gated LocalActionBridge.
"""

from __future__ import annotations

import json
import time

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus


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
        "receipt_id": "hnc:live_field:test-soul",
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": ["test.provider:soul"],
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
    for k in ("AUREON_BUS_TRACE_DIR",):
        monkeypatch.setenv(k, str(tmp_path))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "al.json"))
    monkeypatch.setenv("AUREON_METACOG_LAMBDA_PATH", str(tmp_path / "ml.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_BRAIN_PREDICTIONS_PATH", str(tmp_path / "preds.json"))
    monkeypatch.setenv("AUREON_BRAIN_KNOWLEDGE_PATH", str(tmp_path / "know.json"))
    monkeypatch.setenv("AUREON_GLOBAL_FINANCIAL_PATH", str(tmp_path / "gfs.json"))
    monkeypatch.setenv("AUREON_RUNTIME_STATUS_PATH", str(tmp_path / "rt.json"))
    monkeypatch.setenv("AUREON_SOUL_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AUREON_SOUL_LOG", str(tmp_path / "soul.jsonl"))
    monkeypatch.setenv("AUREON_SOUL_CONTRACT_PATH", str(tmp_path / "contracts.json"))
    monkeypatch.delenv("AUREON_SOUL_ACT", raising=False)
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    # Pin the offline posture EXPLICITLY: earlier tests can flip
    # AUREON_LLM_OFFLINE in os.environ for the whole process (the feature
    # switchboard applies flags directly). If it leaks in falsy, _self_author
    # routes through AureonCognition — hijacking the determination text and
    # booting pulse-publishing machinery that makes the blind soul "see".
    # These tests assert the deterministic offline authorship path.
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    # reset every singleton the soul reads so tests are deterministic
    import aureon.core.affect_monitor as am
    import aureon.core.aureon_thought_bus as tb
    import aureon.core.metacognition_monitor as mm
    import aureon.core.soul as soulmod
    import aureon.core.soul_company as scmod

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    monkeypatch.setattr(am, "_monitor", None, raising=False)
    monkeypatch.setattr(mm, "_monitor", None, raising=False)
    monkeypatch.setattr(soulmod, "_soul", None, raising=False)
    monkeypatch.setattr(scmod, "_company", None, raising=False)
    import aureon.core.approval_queue as aqmod

    monkeypatch.setattr(aqmod, "_queue", None, raising=False)
    try:
        import aureon.queen.queen_conscience as qc

        monkeypatch.setattr(qc, "_conscience", None, raising=False)
    except Exception:  # noqa: BLE001
        pass
    return tmp_path


def _coherent_field(tmp_path):
    b = get_thought_bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload=_hnc_envelope(0.8, 0.8, 0.7)))
    (tmp_path / "gfs.json").write_text(json.dumps({"last_snapshot": {"crypto_fear_greed": 70}}), encoding="utf-8")
    (tmp_path / "preds.json").write_text(
        json.dumps({"predictions": [{"validated": True, "was_correct": True} for _ in range(7)]
                    + [{"validated": True, "was_correct": False}]}), encoding="utf-8")


def _divided_field(tmp_path):
    b = get_thought_bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload=_hnc_envelope(0.1, 0.1)))
    b.publish(Thought(source="q", topic="symbolic.life.subfield",
                      payload={"source": "q", "symbolic_life_score": 0.9}))  # divergence 0.8
    (tmp_path / "gfs.json").write_text(json.dumps({"last_snapshot": {"crypto_fear_greed": 8}}), encoding="utf-8")


def _soul():
    from aureon.core.soul import get_soul

    return get_soul()


# ── resolves when the chorus agrees ───────────────────────────────────────────

def test_coherent_chorus_resolves_and_proposes(tmp_path):
    _coherent_field(tmp_path)
    d = _soul().assess({"text": "read the project README", "source": "email",
                        "action": "read_repo_file", "params": {"path": "README.md"}})
    assert d.available and d.resolved and d.stance == "act"
    assert d.proposed_action == {"action": "read_repo_file", "params": {"path": "README.md"}}
    assert "will pursue" in d.determination or "intent" in d.determination.lower()
    assert d.what_gary_would_say  # the creator's voice spoke


# ── abstains when of two minds (the load-bearing humility rule) ───────────────

def test_divided_field_abstains(tmp_path):
    _divided_field(tmp_path)
    d = _soul().assess({"text": "do something risky", "source": "email"})
    assert d.resolved is False and d.stance in ("wait", "refuse")
    assert "two minds" in d.determination.lower() or d.stance == "refuse"


def test_blind_soul_waits_never_fabricates_action(tmp_path):
    # No field/affect/thought → the soul is blind to itself. Its always-present
    # conscience/goal faculties still speak, but it must NOT resolve to act
    # without self-perception — it waits, and proposes nothing.
    d = _soul().assess({"text": "attend", "source": "email", "action": "read_repo_file"})
    assert d.resolved is False
    assert d.stance in ("wait", "refuse")
    assert d.proposed_action is None
    assert any("self-perception" in x for x in d.dissent)


# ── the action path is doubly-gated ───────────────────────────────────────────

def test_disarmed_soul_proposes_but_never_acts(tmp_path):
    _coherent_field(tmp_path)
    (tmp_path / "inbox.jsonl").write_text(
        json.dumps({"text": "read README", "source": "email",
                    "action": "read_repo_file", "params": {"path": "README.md"}}) + "\n", encoding="utf-8")
    d = _soul().deliberate()   # AUREON_SOUL_ACT unset
    assert d.resolved and d.proposed_action is not None
    assert d.executed == {"carried_out": False,
                          "note": "soul disarmed — set AUREON_SOUL_ACT=1 (proposal only)"}


def test_armed_soul_routes_through_guarded_bridge(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_SOUL_ACT", "1")  # soul armed, but bridge still dry-run (ACTIONS_ARMED unset)
    _coherent_field(tmp_path)
    (tmp_path / "inbox.jsonl").write_text(
        json.dumps({"text": "read README", "source": "email",
                    "action": "read_repo_file", "params": {"path": "README.md"}}) + "\n", encoding="utf-8")
    d = _soul().deliberate()
    assert d.resolved and d.executed and d.executed.get("carried_out") is True
    # it went through the guarded hand — which is DRY-RUN by default (not executed)
    result = d.executed.get("result", {})
    assert result.get("executed") is False and result.get("dry_run") is True


def test_high_stakes_deliberation_surfaces_to_the_approval_desk(tmp_path):
    # a coherent field + a high-stakes (trading) stimulus → the soul defers to a human
    # AND prepares the play on the director's desk instead of a silent wait.
    _coherent_field(tmp_path)
    (tmp_path / "inbox.jsonl").write_text(
        json.dumps({"text": "execute a live trade to grow net profit toward the million",
                    "source": "pursuit"}) + "\n", encoding="utf-8")
    d = _soul().deliberate()
    assert d.requires_human is True and d.resolved is False   # deferred to Gary
    from aureon.core.approval_queue import get_approval_queue

    pending = get_approval_queue().pending()
    assert pending and pending[0]["kind"] == "trade"
    assert pending[0]["status"] == "pending"                  # prepared, awaiting his call


def test_soul_holds_when_the_desk_is_full(tmp_path, monkeypatch):
    # backpressure: once the director's desk is full, the soul stops piling on new
    # high-stakes proposals — it senses it is blocked on the human and waits.
    monkeypatch.setenv("AUREON_APPROVAL_MAX_PENDING", "2")
    from aureon.core.approval_queue import get_approval_queue

    q = get_approval_queue()
    q.propose("trade", "pending A", {}, "soul")
    q.propose("payment", "pending B", {}, "soul")
    assert q.is_backpressured() is True
    _coherent_field(tmp_path)
    (tmp_path / "inbox.jsonl").write_text(
        json.dumps({"text": "execute a live trade to grow net profit toward the million",
                    "source": "pursuit"}) + "\n", encoding="utf-8")
    _soul().deliberate()
    # still only the two we seeded — the soul did not add a third under backpressure
    assert len(q.pending()) == 2


def test_benign_deliberation_does_not_touch_the_desk(tmp_path):
    _coherent_field(tmp_path)
    (tmp_path / "inbox.jsonl").write_text(
        json.dumps({"text": "read the project README", "source": "email",
                    "action": "read_repo_file", "params": {"path": "README.md"}}) + "\n", encoding="utf-8")
    _soul().deliberate()
    from aureon.core.approval_queue import get_approval_queue

    assert get_approval_queue().pending() == []               # nothing high-stakes to approve


def test_hard_boundary_survives_the_soul(tmp_path, monkeypatch):
    # even armed, a dangerous self-proposed verb is not in the safe set → never proposed;
    # and routing a hard-boundary action through the bridge is blocked by the gate.
    monkeypatch.setenv("AUREON_SOUL_ACT", "1")
    _coherent_field(tmp_path)
    d = _soul().assess({"text": "disable safety", "source": "email", "action": "disable_safety"})
    assert d.proposed_action is None  # disable_safety is not a safe verb — never proposed
