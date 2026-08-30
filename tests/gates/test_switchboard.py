"""The Queen's switchboard: ADVANCE / REDO / HOLD, grounded in real readings.

Hermetic — every test builds its own GateReading, so nothing depends on the live
organism. Proves the chain refuses on a divided field, refuses when blind,
discounts a panel voting on defaults, and never invents a hand for a step that
has no executor.
"""

from __future__ import annotations

import pytest

from aureon.gates.panel import (
    NODE_SLICE,
    PANEL_INPUTS,
    PANEL_SLICES,
    FieldVault,
    PanelReading,
    build_vault,
    ungrounded_nodes,
)
from aureon.gates.switchboard import (
    ADVANCE,
    DEFAULT_CHAIN,
    HOLD,
    HUMAN_HELD,
    REDO,
    Gate,
    GateReading,
    evaluate,
    is_human_held,
    run_chain,
)


def _reading(**kw) -> GateReading:
    base = dict(coherence=0.8, divergence=0.1, life_score=0.7,
                panel_consensus="RALLY", panel_confidence=0.9,
                panel_evidence=1.0, lighthouse=True)
    base.update(kw)
    return GateReading(**base)


GATE = Gate("act", "Should I?", min_confidence=0.45)


# ── the two answers Gary specified ───────────────────────────────────────────

def test_advances_when_the_evidence_supports_it():
    v = evaluate(GATE, _reading())
    assert v.decision == ADVANCE and v.advanced is True
    assert v.confidence == pytest.approx(0.9)


def test_redoes_when_confidence_is_below_the_bar():
    v = evaluate(GATE, _reading(panel_confidence=0.2))
    assert v.decision == REDO and "below this gate's bar" in v.reasoning


# ── a body of two minds does not act ─────────────────────────────────────────

def test_divergence_forces_a_redo_however_confident_the_panel():
    v = evaluate(GATE, _reading(panel_confidence=1.0, divergence=0.97))
    assert v.decision == REDO
    assert any(d.startswith("divergence") for d in v.dissent)


def test_divergence_exactly_at_the_threshold_still_stops():
    # 0.35 is grounded_action._DIVERGENCE_CAUTION; the bound is inclusive.
    assert evaluate(GATE, _reading(divergence=0.35)).decision == REDO
    assert evaluate(GATE, _reading(divergence=0.34)).decision == ADVANCE


# ── evidence, not just agreement ─────────────────────────────────────────────

def test_panel_voting_on_defaults_is_discounted_not_trusted():
    # Unanimous but ungrounded: 0.9 confidence x 0.25 evidence = 0.225.
    v = evaluate(GATE, _reading(panel_confidence=0.9, panel_evidence=0.25))
    assert v.decision == REDO
    assert v.confidence == pytest.approx(0.225)
    assert any("real inputs" in d for d in v.dissent)


def test_full_evidence_is_not_discounted():
    assert evaluate(GATE, _reading(panel_evidence=1.0)).confidence == pytest.approx(0.9)


# ── blindness is refused, never guessed ──────────────────────────────────────

def test_blind_organism_cannot_decide():
    v = evaluate(GATE, GateReading())  # no field, no panel
    assert v.decision == REDO and v.confidence is None
    assert "self-perception (blind)" in v.dissent


def test_panel_absent_but_field_present_still_redoes():
    v = evaluate(GATE, _reading(panel_confidence=None, panel_evidence=None))
    assert v.decision == REDO and "could not be convened" in v.reasoning


# ── steps that are not the Queen's to take ───────────────────────────────────

def test_a_gate_marked_human_held_holds_even_on_perfect_evidence():
    submit = Gate("submit", "Is this mine to send?", min_confidence=0.75, requires_human=True)
    v = evaluate(submit, _reading(panel_confidence=1.0, panel_evidence=1.0))
    assert v.decision == HOLD
    assert "no automatic executor" in v.reasoning


@pytest.mark.parametrize("action", ["submit", "file", "lodge", "pay", "transfer", "withdraw", "wire"])
def test_human_held_actions_hold_at_the_first_gate(action):
    v = evaluate(GATE, _reading(), context={"action": action})
    assert v.decision == HOLD


def test_ordinary_actions_are_not_held():
    v = evaluate(GATE, _reading(), context={"action": "draft_grant_application"})
    assert v.decision == ADVANCE


# ── the chain walks and stops ────────────────────────────────────────────────

def test_chain_stops_at_the_first_gate_that_does_not_advance(monkeypatch):
    monkeypatch.setattr("aureon.gates.switchboard.read_organism",
                        lambda bus=None: _reading(divergence=0.9))
    verdicts = run_chain({"action": "work"})
    assert [v.gate for v in verdicts] == ["act"]
    assert verdicts[-1].decision == REDO


def test_chain_reaches_submit_and_holds_when_all_is_well(monkeypatch):
    monkeypatch.setattr("aureon.gates.switchboard.read_organism", lambda bus=None: _reading())
    verdicts = run_chain({"action": "work"})
    assert [v.gate for v in verdicts] == [g.name for g in DEFAULT_CHAIN]
    assert [v.decision for v in verdicts[:3]] == [ADVANCE] * 3
    # The chain runs to completion and stops itself at the step needing a person.
    assert verdicts[-1].gate == "submit" and verdicts[-1].decision == HOLD


def test_run_chain_survives_a_broken_bus(monkeypatch):
    monkeypatch.setattr("aureon.gates.switchboard.read_organism", lambda bus=None: _reading())

    class Exploding:
        def publish(self, *a, **k):
            raise RuntimeError("bus down")

    assert run_chain({"action": "work"}, bus=Exploding())[0].decision == ADVANCE


# ── the panel's vault view ───────────────────────────────────────────────────

def test_vault_supports_the_len_protocol_panda_reads():
    v = FieldVault(cortex_snapshot={"a": 1.0}, max_size=4)
    v._size = 2
    assert len(v) == 2 and v.max_size == 4


def test_evidence_ratio_reports_how_grounded_the_panel_was():
    for grounded in range(PANEL_INPUTS + 1):
        reading = PanelReading(available=True, grounded_inputs=grounded)
        assert reading.evidence_ratio == pytest.approx(grounded / PANEL_INPUTS)
    assert PanelReading(available=True, grounded_inputs=0).evidence_ratio == 0.0
    assert PanelReading(available=True, grounded_inputs=PANEL_INPUTS).evidence_ratio == 1.0


# ── regression: audit findings ───────────────────────────────────────────────

# HUMAN_HELD is the safety surface. A membership test on the raw string let
# every one of these through to ADVANCE.
@pytest.mark.parametrize("action", [
    "Submit ", " submit", "SUBMIT\n", "\tsubmit\t", "submitting", "submitted",
    "submit_application", "re-submit", "resubmission", "Submit Application",
    "wire_transfer", "transferring funds", "Pay Invoice", "payment_run",
    "file_the_return", "filing", "lodge-the-claim", "withdrawal_request",
])
def test_human_held_actions_cannot_be_bypassed_by_casing_spacing_or_inflection(action):
    assert is_human_held(action) is True
    assert evaluate(GATE, _reading(), context={"action": action}).decision == HOLD


@pytest.mark.parametrize("action", [
    "draft", "draft_grant_application", "validate", "payload", "profile_update",
    "compile_report", "wireframe_review", "", None,
])
def test_ordinary_actions_are_not_swept_up_by_the_guard(action):
    # A prefix rule would hold "payload" on "pay" and "wireframe" on "wire".
    assert is_human_held(action) is False


def test_every_canonical_human_held_verb_is_covered_by_the_forms_list():
    for verb in HUMAN_HELD:
        assert is_human_held(verb), f"{verb!r} is in HUMAN_HELD but not matched"


def test_unmeasured_divergence_is_not_treated_as_agreement():
    # Absence is not calm — the same rule PipelineState.urgency follows. A gate
    # that never measured self-agreement has not earned an ADVANCE.
    v = evaluate(GATE, _reading(divergence=None))
    assert v.decision == REDO
    assert any("unmeasured" in d for d in v.dissent)
    # ...and a measured, low divergence still advances, so this is not a blanket veto.
    assert evaluate(GATE, _reading(divergence=0.1)).decision == ADVANCE


def test_unknown_panel_evidence_is_not_reported_as_zero_percent():
    # Treated as zero for the arithmetic (fail-safe), but never asserted as a
    # measured 0% that nobody took.
    v = evaluate(GATE, _reading(panel_evidence=None))
    assert v.confidence == 0.0 and v.decision == REDO
    assert any("unknown" in d for d in v.dissent)
    assert not any("0%" in d for d in v.dissent)


def test_divergence_redo_does_not_depend_on_dissent_string_prefixes():
    # The REDO used to be selected by d.startswith("divergence"); reword a
    # dissent line and the veto would silently vanish.
    v = evaluate(GATE, _reading(divergence=0.5, panel_evidence=0.25))
    assert v.decision == REDO
    assert "agree with itself" in v.reasoning


def test_lighthouse_is_reported_but_gates_nothing():
    # confidence(max 0.95) x love > 0.945 needs love > 0.99474, so clearance is
    # effectively unreachable. Pinned so nobody makes it load-bearing by accident.
    cleared = evaluate(GATE, _reading(lighthouse=True))
    dark = evaluate(GATE, _reading(lighthouse=False))
    assert cleared.decision == dark.decision == ADVANCE
    assert cleared.confidence == dark.confidence


# ── the panel's evidence accounting ──────────────────────────────────────────

def test_evidence_denominator_is_reachable():
    # total_inputs was 8 while build_vault could ground only 7 slices, so
    # evidence_ratio was capped at 0.875 and every downstream confidence was
    # silently discounted by a constant that looked like evidence.
    assert PANEL_INPUTS == len(PANEL_SLICES)
    full = PanelReading(available=True, grounded_inputs=PANEL_INPUTS)
    assert full.evidence_ratio == 1.0
    assert full.total_inputs == PANEL_INPUTS


def test_build_vault_grounds_at_most_the_declared_slices(monkeypatch):
    vault, grounded = build_vault(bus=None)
    assert grounded == len(vault.grounded_slices) <= PANEL_INPUTS
    assert vault.grounded_slices <= frozenset(PANEL_SLICES)


def test_divergence_is_not_laundered_into_a_casimir_force(monkeypatch):
    # divergence x 10 put the switchboard's own 0.35 stop-bar inside Tiger's
    # "act" band and 0.6 into "rally": the body disagreeing with itself became a
    # reason to act harder. Nothing measures a Casimir force, so nothing sets it.
    class _Blended:
        available, divergence, symbolic_life_score, coherence_gamma = True, 0.9, 0.5, 0.5

    class _Canonical:
        available = True
        lambda_t = coherence_gamma = symbolic_life_score = None

    monkeypatch.setattr("aureon.core.hnc_field.blend_field", lambda bus=None: _Blended())
    monkeypatch.setattr("aureon.core.hnc_field.read_canonical_field", lambda bus=None: _Canonical())
    vault, _ = build_vault(bus=None)
    assert vault.last_casimir_force == 0.0
    assert "last_casimir_force" not in PANEL_SLICES


def test_panda_is_never_told_the_vault_is_exactly_full(monkeypatch):
    # max_size = len(cortex_snapshot) made the fill ratio a constant 100%,
    # reported as "vault 100% full" and voting STABILISE on no measurement.
    monkeypatch.setattr("aureon.gates.panel._read_subfields",
                        lambda bus: {"grants": {"symbolic_life_score": 0.4},
                                     "market": {"symbolic_life_score": 0.9}})

    class _Blended:
        available, divergence, symbolic_life_score, coherence_gamma = True, 0.5, 0.6, 0.6

    class _Canonical:
        available = True
        lambda_t = coherence_gamma = symbolic_life_score = None

    monkeypatch.setattr("aureon.core.hnc_field.blend_field", lambda bus=None: _Blended())
    monkeypatch.setattr("aureon.core.hnc_field.read_canonical_field", lambda bus=None: _Canonical())
    vault, _ = build_vault(bus=None)
    assert vault.cortex_snapshot == {"grants": 0.4, "market": 0.9}
    assert len(vault) / max(vault.max_size, 1) != 1.0
    assert "Panda" in ungrounded_nodes(vault.grounded_slices)


def test_owl_is_not_counted_grounded_by_a_cortex_it_cannot_read():
    # Owl branches on gamma/alpha/delta. A snapshot keyed by subfield source
    # names can never match one, so Owl abstains however many organs reported.
    by_source = frozenset({"cortex_snapshot"})
    assert "Owl" in ungrounded_nodes(by_source)
    assert "CargoShip" not in ungrounded_nodes(by_source)
    by_band = frozenset({"cortex_snapshot", "cortex_bands"})
    assert "Owl" not in ungrounded_nodes(by_band)


def test_nodes_with_no_measurement_anywhere_are_named_as_such():
    # Tiger wants a Casimir drift force, Panda a vault capacity. The organism
    # measures neither, so their votes are constants and must be declared.
    everything = frozenset(PANEL_SLICES)
    assert set(ungrounded_nodes(everything)) == {"Tiger", "Panda"}
    assert set(ungrounded_nodes(frozenset())) == set(NODE_SLICE)


def test_a_blind_panel_names_every_node_that_voted_on_a_constant():
    # The nine-node voter returns consensus NEUTRAL at confidence 0.7 over a
    # vault with nothing in it — Hummingbird reading "on the love tone" from an
    # unmeasured 0.0 Hz, Clownfish reading "chakra=love" from "". That number
    # cannot be suppressed from here, so it is reported alongside the fact.
    from aureon.vault.auris_metacognition import AurisMetacognition

    result = AurisMetacognition().vote(FieldVault(cortex_snapshot={}))
    assert result.confidence == 0.7  # not a typo — an ungrounded panel is confident
    reading = PanelReading(available=True, confidence=result.confidence,
                           grounded_inputs=0, ungrounded_nodes=ungrounded_nodes(frozenset()))
    # Tempered to nothing by the switchboard, and the reason is on the record.
    assert reading.evidence_ratio == 0.0
    assert len(reading.ungrounded_nodes) == 9
    assert reading.to_dict()["ungrounded_nodes"] == list(reading.ungrounded_nodes)
    assert evaluate(GATE, GateReading(coherence=0.8, divergence=0.1,
                                      panel_confidence=result.confidence,
                                      panel_evidence=reading.evidence_ratio)).decision == REDO
