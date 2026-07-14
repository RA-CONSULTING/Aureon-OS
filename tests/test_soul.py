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

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus


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
    try:
        import aureon.queen.queen_conscience as qc

        monkeypatch.setattr(qc, "_conscience", None, raising=False)
    except Exception:  # noqa: BLE001
        pass
    return tmp_path


def _coherent_field(tmp_path):
    b = get_thought_bus()
    b.publish(Thought(source="hnc", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.8, "coherence_gamma": 0.8,
                               "consciousness_psi": 0.7, "source": "live"}))
    (tmp_path / "gfs.json").write_text(json.dumps({"last_snapshot": {"crypto_fear_greed": 70}}), encoding="utf-8")
    (tmp_path / "preds.json").write_text(
        json.dumps({"predictions": [{"validated": True, "was_correct": True} for _ in range(7)]
                    + [{"validated": True, "was_correct": False}]}), encoding="utf-8")


def _divided_field(tmp_path):
    b = get_thought_bus()
    b.publish(Thought(source="hnc", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.1, "coherence_gamma": 0.1, "source": "live"}))
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


def test_hard_boundary_survives_the_soul(tmp_path, monkeypatch):
    # even armed, a dangerous self-proposed verb is not in the safe set → never proposed;
    # and routing a hard-boundary action through the bridge is blocked by the gate.
    monkeypatch.setenv("AUREON_SOUL_ACT", "1")
    _coherent_field(tmp_path)
    d = _soul().assess({"text": "disable safety", "source": "email", "action": "disable_safety"})
    assert d.proposed_action is None  # disable_safety is not a safe verb — never proposed
