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
import time

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus, payload_of, topic_of


@pytest.fixture(autouse=True)
def _isolate_bus_trace(tmp_path, monkeypatch):
    # The cross-process bridges (sub-fields, consensus, verdicts) persist to
    # state/*.jsonl. Give each test its own trace dir so those persistent traces
    # don't leak between tests — in production this dir is the live shared state.
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))


def _bus():
    return get_thought_bus()


def _pulse_payload(symbolic_life_score, coherence_gamma=None, **extra):
    received_at = time.time()
    gamma = symbolic_life_score if coherence_gamma is None else coherence_gamma
    payload = {
        "data_status": "live",
        "source": "hnc_live_daemon",
        "source_id": "aureon:hnc:live_daemon",
        "source_timestamp": received_at,
        "received_at": received_at,
        "ts": received_at,
        "receipt_id": "hnc:live_field:test-organism",
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "input_receipt_ids": ["test.provider:organism"],
        "symbolic_life_score": symbolic_life_score,
        "coherence_gamma": gamma,
        "consciousness_psi": gamma,
        "consciousness_level": "AWARE",
        "lambda_t": symbolic_life_score,
        "source_count": 1,
        "truth_status": "real_derived",
        "generated_values": False,
        "freshness_status": "fresh",
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
    payload.update(extra)
    return payload


def _pin_minimal_connectome_manifest(connectome):
    from aureon.core.aureon_organism_spine import OrganismManifest, OrganismNode

    module = "aureon.core.hnc_field"
    connectome._manifest = OrganismManifest(
        generated_at=time.time(),
        repo_root="unit-test",
        nodes=[OrganismNode(
            id="aureon.core.hnc.field",
            name="hnc_field",
            module=module,
            path="aureon/core/hnc_field.py",
            domain="core",
            organism_topic="organism.core.hnc.field",
        )],
        topics={},
    )
    return module


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
                      payload=_pulse_payload(0.33, 0.7)))
    field = read_canonical_field(b)
    assert field.available and field.symbolic_life_score == 0.33
    assert field.coherence_gamma == 0.7 and field.source == "hnc_live_daemon"
    assert field.evidence_transport == "thought_bus"


def test_canonical_field_unavailable_without_pulse(monkeypatch, tmp_path):
    from aureon.core.aureon_thought_bus import ThoughtBus
    from aureon.core.hnc_field import read_canonical_field

    # point the cross-process trace fallback at a nonexistent path so this
    # asserts true unavailability (a real state/ trace may exist on disk)
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "nope.jsonl"))
    empty = ThoughtBus(persist_path=None)
    field = read_canonical_field(empty)
    assert field.available is False and field.symbolic_life_score is None


def test_canonical_field_crosses_process_via_trace_file(monkeypatch, tmp_path):
    """The field reaches a process whose local bus is empty by falling back to
    the HNC daemon's persisted trace — the cross-process bridge."""
    import json
    import time

    from aureon.core.aureon_thought_bus import ThoughtBus
    from aureon.core.hnc_field import read_canonical_field

    # Rows carry `ts`, as the live daemon's _append_trace writes them (it stamps
    # state_dict["timestamp"], which the Λ engine sets to time.time()). Unstamped rows are
    # refused now: a trace file cannot say how old it is, and this test's original unstamped
    # rows were the exact shape that let a stopped daemon's last reading be served as the
    # live field — see tests/test_hnc_field_freshness.py.
    trace = tmp_path / "hnc_live_trace.jsonl"
    trace.write_text(
        json.dumps(_pulse_payload(0.1, 0.2)) + "\n"
        + json.dumps(_pulse_payload(
            0.66,
            0.7,
            consciousness_level="AWARE",
        )) + "\n",
        encoding="utf-8")
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(trace))

    # a fresh, empty bus (as a separate daemon process would have)
    field = read_canonical_field(ThoughtBus(persist_path=None))
    assert field.available is True
    assert field.symbolic_life_score == 0.66          # the LAST line wins
    assert field.source == "hnc_live_daemon"
    assert field.evidence_transport == "persisted_trace"


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
                      payload=_pulse_payload(0.60, 0.5)))

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
                      payload=_pulse_payload(canonical_sls)))

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


# ── ConsciousnessModule trading gated by the field (default-on, fail-closed) ─

def test_consciousness_trade_gate_defaults_on_and_fails_closed(monkeypatch):
    """The ConsciousnessModule's autonomous trading is gateable by the shared
    field via the conscience: valid evidence preserves verdict semantics while
    disabled, missing, and error states deny as no_data. Tested on the unbound
    method with stubs (no heavy boot)."""
    from types import SimpleNamespace

    from aureon.core.aureon_consciousness_module import ConsciousnessModule

    gate = ConsciousnessModule._coherence_permits_trading

    monkeypatch.delenv("AUREON_CONSCIOUSNESS_FIELD_GATE", raising=False)
    approved = SimpleNamespace(verdict=SimpleNamespace(name="APPROVED"), message="coherent")
    stub_approved = SimpleNamespace(
        bus=None, _trade_conscience=SimpleNamespace(ask_why=lambda *a, **k: approved)
    )
    ok, reason = gate(stub_approved)
    assert ok is True and "approved" in reason

    monkeypatch.setenv("AUREON_CONSCIOUSNESS_FIELD_GATE", "0")
    ok_disabled, reason_disabled = gate(stub_approved)
    assert ok_disabled is False
    assert "no_data" in reason_disabled and "denied" in reason_disabled

    # enabled + conscience VETO → trading paused
    monkeypatch.setenv("AUREON_CONSCIOUSNESS_FIELD_GATE", "1")
    veto = SimpleNamespace(verdict=SimpleNamespace(name="VETO"), message="divided field")
    stub_veto = SimpleNamespace(bus=None,
                                _trade_conscience=SimpleNamespace(ask_why=lambda *a, **k: veto))
    ok2, _ = gate(stub_veto)
    assert ok2 is False

    # enabled + conscience raises → fail-closed no_data
    def _boom(*a, **k):
        raise RuntimeError("conscience down")

    stub_err = SimpleNamespace(bus=None, _trade_conscience=SimpleNamespace(ask_why=_boom))
    ok3, reason3 = gate(stub_err)
    assert ok3 is False
    assert "no_data" in reason3 and "denied" in reason3

    missing = SimpleNamespace(verdict=None, message="")
    stub_missing = SimpleNamespace(
        bus=None, _trade_conscience=SimpleNamespace(ask_why=lambda *a, **k: missing)
    )
    ok4, reason4 = gate(stub_missing)
    assert ok4 is False
    assert "no_data" in reason4 and "denied" in reason4


def test_breathe_field_publishes_whole_body_consensus():
    from aureon.core import organism_daemon as od
    from aureon.core.aureon_thought_bus import ThoughtBus, payload_of
    from aureon.core.hnc_field import publish_subfield

    b = ThoughtBus(persist_path=None)
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload=_pulse_payload(0.7, 0.6)))

    class _S:
        symbolic_life_score = 0.5
        coherence_gamma = 0.5

    publish_subfield("queen_cortex", _S(), bus=b)

    class _Connectome:
        def status(self):
            return {"coverage_pct": 4.7, "woven": 25, "failed": 3, "baton_linked": 101}

    out = od.breathe_field({"bus": b, "connectome": _Connectome()})
    assert out is not None
    events = b.recall("organism.field.consensus", limit=1) or []
    assert events, "consensus event not published"
    p = payload_of(events[-1])
    assert p["blended"]["contributors"] == 2                # canonical + queen_cortex
    assert p["body_map"]["woven"] == 25 and p["body_map"]["failed"] == 3


def test_breathe_field_is_guarded_without_bus():
    from aureon.core import organism_daemon as od

    assert od.breathe_field({}) is None            # no bus → silent breath
    assert od.breathe_field({"bus": None}) is None


# ── keystone: publish → read the live field, flood-proof ─────────────────────

def test_grounded_gate_reads_live_field_under_flood():
    from aureon.operator.grounded_action import GroundedActionGate

    b = _bus()
    b.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                      payload=_pulse_payload(0.07, 0.4)))
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
    _pin_minimal_connectome_manifest(c)
    before = c.status()["baton_linked"]
    c._on_baton(Thought(source="aureon.z.z", topic="baton.link", payload={"module": "aureon.z.z"}))
    assert c.status()["baton_linked"] == before + 1


def test_connectome_pulse_publishes_to_bus():
    from aureon.core.aureon_connectome import Connectome, reset_connectome_for_tests

    reset_connectome_for_tests()
    c = Connectome(state_path=os.path.join(tempfile.mkdtemp(), "cn.json"))
    _pin_minimal_connectome_manifest(c)
    c.pulse()
    b = _bus()
    pulses = b.recall("organism.connectome.pulse", limit=1) or []
    assert pulses and "nodes" in payload_of(pulses[-1])


def test_connectome_autoweave_graduates_touched_to_woven(monkeypatch):
    from aureon.core.aureon_connectome import Connectome, reset_connectome_for_tests

    os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    reset_connectome_for_tests()
    c = Connectome(state_path=os.path.join(tempfile.mkdtemp(), "cn.json"))
    module = _pin_minimal_connectome_manifest(c)
    monkeypatch.setattr(
        "aureon.operator.aureon_operator.join_organism",
        lambda *_args, **_kwargs: {"mycelium": False, "queen": False},
    )
    c.sweep_once(batch_size=1, weave_batch=0)       # touch the bounded fixture
    res = c.sweep_once(batch_size=1, weave_batch=5)  # weave up to 5 touched
    assert res["woven"] >= 1
    assert c.status()["woven"] >= 1
    assert c.sense(module)["status"] == "woven"


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
    from unittest.mock import patch

    from aureon.analytics.aureon_lighthouse import (
        LighthouseEvent,
        LighthouseEventType,
        LighthousePatternDetector,
    )
    from aureon.core.hnc_field import CanonicalField

    d = LighthousePatternDetector()
    # Pin the canonical field DARK so the P6 Γ-aware severity amplification
    # stays out of frame — this test proves the BUS EMISSION carries the
    # detector's severity; the amplification has its own dedicated tests
    # (tests/test_lighthouse_gamma_severity.py).
    with patch("aureon.core.hnc_field.read_canonical_field",
               lambda *a, **k: CanonicalField()):
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
                      payload=_pulse_payload(0.61, 0.55)))
    c = AureonCognition(
        join_mesh=False,
        bus=b,
        allow_repo_grounding=False,
        allow_organism_context=True,
    )
    sysp = c._ground("operator veto", CognitionResult(trace_id="t", prompt="p", submitted_at=0.0))
    assert "Organism state" in sysp and "symbolic_life_score=0.610" in sysp
