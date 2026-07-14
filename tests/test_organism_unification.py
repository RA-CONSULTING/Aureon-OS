"""
Aureon — organism unification (Phase 19).

The connective substrate existed but was silently dead at both ends. These tests
pin the revived edges so they can't rot again: the live HNC field is published and
read (flood-proof), the connectome telemetry is honest, mesh broadcasts are
delivered, Lighthouse reaches the bus, cognition senses the field, and the
connectome weaves the body. Offline; no network, no OS deps.
"""

from __future__ import annotations

import os
import tempfile

from aureon.core.aureon_thought_bus import Thought, get_thought_bus, payload_of, topic_of


def _bus():
    return get_thought_bus()


# ── shape-agnostic accessors ─────────────────────────────────────────────────

def test_topic_and_payload_accessors_handle_both_shapes():
    b = _bus()
    b.publish(Thought(source="x", topic="unit.test.shape", payload={"k": 1}))
    obj = b._memory[-1]                       # a Thought object (subscribe shape)
    dct = b.get_recent(1)[0]                  # a to_json dict (get_recent shape)
    assert topic_of(obj) == "unit.test.shape" and topic_of(dct) == "unit.test.shape"
    assert payload_of(obj)["k"] == 1 and payload_of(dct)["k"] == 1


# ── the canonical field accessor (single source of truth) ───────────────────

def test_canonical_field_reads_the_shared_pulse():
    from aureon.core.hnc_field import read_canonical_field

    b = _bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.33, "coherence_gamma": 0.7,
                               "source": "unit"}))
    field = read_canonical_field(b)
    assert field.available and field.symbolic_life_score == 0.33
    assert field.coherence_gamma == 0.7 and field.source == "unit"


def test_canonical_field_unavailable_without_pulse():
    from aureon.core.aureon_thought_bus import ThoughtBus
    from aureon.core.hnc_field import read_canonical_field

    empty = ThoughtBus(persist_path=None)
    field = read_canonical_field(empty)
    assert field.available is False and field.symbolic_life_score is None


def test_subfields_publish_and_read_by_source():
    from aureon.core.hnc_field import publish_subfield, read_subfields

    b = _bus()

    class _S:
        symbolic_life_score = 0.44
        coherence_gamma = 0.6
        consciousness_level = "AWARE"

    publish_subfield("queen_cortex", _S(), bus=b)
    publish_subfield("queen_source_law", _S(), bus=b)
    subs = read_subfields(b)
    assert "queen_cortex" in subs and "queen_source_law" in subs
    assert subs["queen_cortex"]["symbolic_life_score"] == 0.44


def test_blended_field_is_consensus_with_divergence():
    from aureon.core.aureon_thought_bus import ThoughtBus
    from aureon.core.hnc_field import blend_field, publish_subfield

    b = ThoughtBus(persist_path=None)   # isolated bus for a clean consensus
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.60, "coherence_gamma": 0.5}))

    class _A:
        symbolic_life_score = 0.40
        coherence_gamma = 0.5

    publish_subfield("queen_cortex", _A(), bus=b)
    blended = blend_field(b)
    assert blended.available and blended.contributors == 2
    assert abs(blended.symbolic_life_score - 0.50) < 1e-9   # mean of 0.60, 0.40
    assert abs(blended.divergence - 0.20) < 1e-9            # spread
    assert "canonical" in blended.sources and "queen_cortex" in blended.sources


def _divided_bus(canonical_sls: float, sub_sls: float):
    """An isolated bus with a canonical field + one disagreeing sub-field."""
    from aureon.core.aureon_thought_bus import ThoughtBus
    from aureon.core.hnc_field import publish_subfield

    b = ThoughtBus(persist_path=None)
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": canonical_sls}))

    class _Sub:
        symbolic_life_score = sub_sls
        coherence_gamma = 0.5

    publish_subfield("queen_cortex", _Sub(), bus=b)
    return b


def test_divergence_cautions_a_risky_move_when_sls_healthy():
    from aureon.operator.grounded_action import GroundedActionGate

    # canonical 0.9, sub 0.4 → divergence 0.5 (>0.35); mean SLS 0.65 (healthy island)
    b = _divided_bus(0.9, 0.4)
    v = GroundedActionGate(bus=b, enable_llm=False).ground("delete_file", {"path": "x"})
    assert v.verdict == "CONCERNED" and v.approved is True
    assert v.field_divergence is not None and v.field_divergence >= 0.35


def test_divergence_vetoes_when_also_off_the_island():
    from aureon.operator.grounded_action import GroundedActionGate

    # canonical 0.5, sub 0.05 → divergence 0.45; but conscience reads the LOW
    # sub via _current_sls? gate passes mean-agnostic sls; force drift via context.
    b = _divided_bus(0.5, 0.05)
    v = GroundedActionGate(bus=b, enable_llm=False).ground(
        "delete_file", {"path": "x"}, {"symbolic_life_score": 0.3})  # off-island SLS
    assert v.verdict == "VETOED" and v.approved is False


def test_low_divergence_leaves_a_healthy_move_approved():
    from aureon.operator.grounded_action import GroundedActionGate

    # canonical 0.8, sub 0.75 → divergence 0.05 (<0.35); healthy → approve
    b = _divided_bus(0.8, 0.75)
    v = GroundedActionGate(bus=b, enable_llm=False).ground("delete_file", {"path": "x"})
    assert v.verdict == "APPROVED" and v.approved is True


def test_divided_field_gates_a_trade_via_the_fallback(monkeypatch):
    """A trade decision passes no field_divergence, yet the live whole-body
    consensus still gates it — the field now reaches every conscience caller
    (trades, goals, skills), not just the local-action gate. Hermetic: the live
    field is injected via a patched blend_field, not the shared bus."""
    from aureon.core.hnc_field import BlendedField
    from aureon.queen.queen_conscience import ConscienceVerdict, QueenConscience

    monkeypatch.setattr(
        "aureon.core.hnc_field.blend_field",
        lambda bus=None: BlendedField(
            available=True, symbolic_life_score=0.60, coherence_gamma=0.5,
            contributors=2, divergence=0.60, sources=("canonical", "queen_cortex")),
    )
    c = QueenConscience()
    # trade context carries NO field_divergence — the fallback must supply it,
    # and SLS 0.30 is off the island → VETO.
    whisper = c.ask_why("Execute trade buy BTC", {"symbolic_life_score": 0.30, "risk": 0.1})
    assert whisper.verdict == ConscienceVerdict.VETO


# ── keystone: publish → read the live field, flood-proof ─────────────────────

def test_grounded_gate_reads_live_field_under_flood():
    from aureon.operator.grounded_action import GroundedActionGate

    b = _bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.07, "coherence_gamma": 0.4}))
    # bury the pulse under a baton flood — recall() must still find it by topic
    for i in range(300):
        b.publish(Thought(source=f"m{i}", topic="baton.link", payload={"module": f"m{i}"}))
    gate = GroundedActionGate(bus=b, enable_llm=False)
    v = gate.ground("delete_file", {"path": "x"})   # low SLS + risky → veto
    assert v.symbolic_life_score == 0.07
    assert v.verdict == "VETOED"


# ── connectome telemetry is honest ───────────────────────────────────────────

def test_connectome_baton_ear_reads_payload():
    from aureon.core.aureon_connectome import Connectome, reset_connectome_for_tests

    reset_connectome_for_tests()
    c = Connectome(state_path=os.path.join(tempfile.mkdtemp(), "cn.json"))
    before = c.status()["baton_linked"]
    c._on_baton(Thought(source="aureon.z.z", topic="baton.link", payload={"module": "aureon.z.z"}))
    assert c.status()["baton_linked"] == before + 1


def test_connectome_pulse_publishes_to_bus():
    from aureon.core.aureon_connectome import Connectome, reset_connectome_for_tests

    reset_connectome_for_tests()
    c = Connectome(state_path=os.path.join(tempfile.mkdtemp(), "cn.json"))
    c.pulse()
    b = _bus()
    pulses = b.recall("organism.connectome.pulse", limit=1) or []
    assert pulses and "nodes" in payload_of(pulses[-1])


def test_connectome_autoweave_graduates_touched_to_woven():
    from aureon.core.aureon_connectome import Connectome, reset_connectome_for_tests

    os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    reset_connectome_for_tests()
    c = Connectome(state_path=os.path.join(tempfile.mkdtemp(), "cn.json"))
    c.sweep_once(batch_size=20, weave_batch=0)      # touch a batch
    res = c.sweep_once(batch_size=1, weave_batch=5)  # weave up to 5 touched
    assert res["woven"] >= 1
    assert c.status()["woven"] >= 1


# ── mesh delivery actually reaches subsystems ────────────────────────────────

def test_broadcast_to_mesh_reaches_receive_mycelium_message():
    from aureon.core.aureon_mycelium import get_mycelium
    from aureon.operator.aureon_operator import broadcast_to_mesh

    seen = {}

    class _Rcv:
        def receive_mycelium_message(self, mt, pl):
            seen["hit"] = (mt, pl)

    get_mycelium().connect_subsystem("unify_test_rcv", _Rcv())
    broadcast_to_mesh("unify.mesh.test", {"v": 7})
    assert seen.get("hit") == ("unify.mesh.test", {"v": 7})


# ── lighthouse reaches the bus ───────────────────────────────────────────────

def test_lighthouse_emits_to_bus():
    from aureon.analytics.aureon_lighthouse import (
        LighthouseEvent,
        LighthouseEventType,
        LighthousePatternDetector,
    )

    d = LighthousePatternDetector()
    d._emit_event(LighthouseEvent(
        event_type=LighthouseEventType.COHERENCE_COLLAPSE, timestamp=0.0,
        severity=0.9, symbols=["BTC"], message="unit collapse"))
    got = _bus().recall("lighthouse.event", limit=1) or []
    assert got and payload_of(got[-1]).get("severity") == 0.9


# ── cognition senses the field ───────────────────────────────────────────────

def test_cognition_folds_field_into_ground_prompt():
    from aureon.operator.cognition import AureonCognition, CognitionResult

    b = _bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload={"symbolic_life_score": 0.61, "coherence_gamma": 0.55}))
    c = AureonCognition(join_mesh=False)
    sysp = c._ground("operator veto", CognitionResult(trace_id="t", prompt="p", submitted_at=0.0))
    assert "Organism state" in sysp and "symbolic_life_score=0.610" in sysp
