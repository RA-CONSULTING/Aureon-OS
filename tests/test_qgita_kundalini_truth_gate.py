from __future__ import annotations

import copy

import pytest

from aureon.governance.qgita_kundalini_truth_gate import (
    CLAIM_SOURCE_PREFIX,
    DIAGNOSTIC_PREFIX,
    DIAGNOSTIC_SCHEMA,
    DIAGNOSTIC_SOURCE_PREFIX,
    GROUNDING_PREFIX,
    GROUNDING_SCHEMA,
    TruthGateRequest,
    evaluate_truth_gate,
    validate_diagnostic_bundle,
    validate_grounding_bundle,
    validate_truth_gate_result,
)
from aureon.governance.qgita_kundalini_truth_gate import _sha256 as sha256

NOW = 1_800_000_000.0
P = "1" * 64
A = "2" * 64
H = "hnc:live_field:" + "3" * 24
E1 = "evidence:grounding:" + "4" * 24
E2 = "evidence:grounding:" + "5" * 24
CS = CLAIM_SOURCE_PREFIX + "7" * 64
DS = DIAGNOSTIC_SOURCE_PREFIX + "8" * 64
FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "action_gate_passed": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "eligible_for_action": False,
    "eligible_for_accounting": False,
    "eligible_for_learning": False,
    "economic_mutation": False,
}


def _seal(prefix, causal):
    return {**causal, "receipt_id": prefix + sha256(causal)}


def _finding(kind="SUPPORTED", claim="6" * 64, links=None):
    if links is None:
        links = [] if kind == "MISSING_GROUNDING" else [E1]
    return {"claim_id": claim, "failure_kind": kind, "evidence_receipt_ids": links}


def _ground(request, findings=None):
    causal = {
        "schema_version": GROUNDING_SCHEMA,
        "resolver_id": "grounder:trusted",
        "source_claim_set_receipt_id": CS,
        "prompt_digest": request.prompt_digest,
        "answer_digest": request.answer_digest,
        "hnc_receipt_id": request.hnc_receipt_id,
        "source_timestamp": NOW - 2,
        "received_at": NOW - 1,
        "truth_status": "real_observed",
        "generated_values": False,
        "evidence_receipt_ids": [E1, E2],
        "claim_findings": findings or [_finding()],
        **FALSE_FLAGS,
    }
    return _seal(GROUNDING_PREFIX, causal)


def _diagnostic(request, ground):
    causal = {
        "schema_version": DIAGNOSTIC_SCHEMA,
        "resolver_id": "diagnostic:trusted",
        "source_diagnostic_signal_receipt_id": DS,
        "grounding_receipt_id": ground["receipt_id"],
        "prompt_digest": request.prompt_digest,
        "answer_digest": request.answer_digest,
        "hnc_receipt_id": request.hnc_receipt_id,
        "source_timestamp": NOW - 2,
        "received_at": NOW - 1,
        "truth_status": "real_derived",
        "generated_values": False,
        "evidence_receipt_ids": [E1, E2],
        "qgita_diagnostics": {"structural_event": "none", "residual": 0.1},
        "math_angle_diagnostics": {"phase_state": "aligned", "spread": 0.2},
        **FALSE_FLAGS,
    }
    return _seal(DIAGNOSTIC_PREFIX, causal)


class Grounder:
    resolver_id = "grounder:trusted"

    def __init__(self, findings=None, mutate=None):
        self.findings = findings
        self.mutate = mutate
        self.calls = 0

    def resolve_grounding(self, request):
        self.calls += 1
        result = _ground(request, self.findings)
        if self.mutate:
            self.mutate(result)
        return result


class Diagnostic:
    resolver_id = "diagnostic:trusted"

    def __init__(self, mutate=None):
        self.mutate = mutate
        self.calls = 0

    def resolve_diagnostics(self, request, grounding):
        self.calls += 1
        result = _diagnostic(request, grounding)
        if self.mutate:
            self.mutate(result)
        return result


def _evaluate(request, grounder=None, diagnostic=None):
    grounder = grounder or Grounder()
    diagnostic = diagnostic or Diagnostic()
    result = evaluate_truth_gate(
        request,
        grounding_resolver=grounder,
        diagnostic_resolver=diagnostic,
        allowed_grounding_resolver_ids=frozenset({"grounder:trusted"}),
        allowed_diagnostic_resolver_ids=frozenset({"diagnostic:trusted"}),
        now=NOW,
        max_age_s=30,
    )
    return result, grounder, diagnostic


def test_request_is_strict_and_rejects_bool_attempt():
    with pytest.raises(ValueError):
        TruthGateRequest(P, A, H, True)
    with pytest.raises(ValueError):
        TruthGateRequest("A" * 64, A, H, 0)
    assert TruthGateRequest(P, A, H, 2).correction_attempt == 2


def test_supported_claims_are_ready_for_auris_not_accept():
    result, grounder, diagnostic = _evaluate(TruthGateRequest(P, A, H, 0))
    assert result["status"] == "READY_FOR_AURIS"
    assert "ACCEPT" not in result.values()
    assert result["kundalini_stage"] == "Crown"
    assert grounder.calls == diagnostic.calls == 1
    validate_truth_gate_result(result)


@pytest.mark.parametrize(
    ("kind", "stage"),
    [
        ("MISSING_GROUNDING", "Root"),
        ("STALE_OR_LINEAGE", "Sacral"),
        ("UNSUPPORTED", "Solar Plexus"),
        ("CONTRADICTED", "Heart"),
        ("SEMANTIC_MISMATCH", "Throat"),
        ("CROSS_CLAIM_CONFLICT", "Third Eye"),
    ],
)
def test_each_failure_maps_to_the_ordered_kundalini_stage(kind, stage):
    result, _, _ = _evaluate(
        TruthGateRequest(P, A, H, 0),
        Grounder([_finding(kind)]),
    )
    assert result["status"] == "CORRECTION_REQUIRED"
    assert result["kundalini_stage"] == stage
    assert result["correction_directive"]["next_attempt"] == 1


def test_first_blocker_is_independent_of_claim_order():
    findings = [
        _finding("CONTRADICTED", "7" * 64, [E2]),
        _finding("MISSING_GROUNDING", "8" * 64, []),
        _finding("UNSUPPORTED", "9" * 64, [E1]),
    ]
    result, _, _ = _evaluate(TruthGateRequest(P, A, H, 1), Grounder(findings))
    assert result["kundalini_stage"] == "Root"
    assert result["correction_directive"]["next_attempt"] == 2


def test_third_attempt_holds_without_diagnostic_numbers():
    result, _, _ = _evaluate(
        TruthGateRequest(P, A, H, 2),
        Grounder([_finding("UNSUPPORTED")]),
    )
    assert result["status"] == "HOLD"
    assert result["diagnostic_receipt_id"] == ""
    assert result["correction_directive"] == {}
    assert all(value is False for key, value in result.items() if key in FALSE_FLAGS)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.__setitem__("receipt_id", GROUNDING_PREFIX + "0" * 64),
        lambda b: b.__setitem__("received_at", NOW - 999),
        lambda b: b.__setitem__("generated_values", True),
        lambda b: b.__setitem__("actionable", True),
        lambda b: b.__setitem__("prompt_digest", "0" * 64),
    ],
)
def test_bad_grounding_holds_and_skips_diagnostics(mutate):
    result, grounder, diagnostic = _evaluate(
        TruthGateRequest(P, A, H, 0),
        Grounder(mutate=mutate),
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "trusted_evidence_required"
    assert grounder.calls == 1
    assert diagnostic.calls == 0


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.__setitem__("receipt_id", DIAGNOSTIC_PREFIX + "0" * 64),
        lambda b: b.__setitem__("truth_status", "generated"),
        lambda b: b["qgita_diagnostics"].__setitem__("confidence", True),
        lambda b: b.__setitem__("grounding_receipt_id", GROUNDING_PREFIX + "0" * 64),
    ],
)
def test_bad_diagnostics_hold_after_exactly_one_call(mutate):
    result, grounder, diagnostic = _evaluate(
        TruthGateRequest(P, A, H, 0),
        diagnostic=Diagnostic(mutate=mutate),
    )
    assert result["status"] == "HOLD"
    assert grounder.calls == diagnostic.calls == 1


def test_diagnostic_scores_cannot_override_unsupported_grounding():
    diagnostic = Diagnostic(
        mutate=lambda b: b["qgita_diagnostics"].update(
            {"coherence": 1.0, "lighthouse": 1.0}
        )
    )
    # Reseal so the high scores form a valid diagnostic receipt.
    original = diagnostic.resolve_diagnostics

    def resolve_and_reseal(request, grounding):
        result = original(request, grounding)
        causal = {key: value for key, value in result.items() if key != "receipt_id"}
        result["receipt_id"] = DIAGNOSTIC_PREFIX + sha256(causal)
        return result

    diagnostic.resolve_diagnostics = resolve_and_reseal
    result, _, _ = _evaluate(
        TruthGateRequest(P, A, H, 0),
        Grounder([_finding("UNSUPPORTED")]),
        diagnostic,
    )
    assert result["status"] == "CORRECTION_REQUIRED"


def test_validators_reject_unknown_fields_and_signed_nonfinite_values():
    request = TruthGateRequest(P, A, H, 0)
    ground = _ground(request)
    ground["unknown"] = "x"
    with pytest.raises(ValueError):
        validate_grounding_bundle(ground, request, now=NOW, max_age_s=30)
    valid_ground = _ground(request)
    diagnostic = _diagnostic(request, valid_ground)
    diagnostic["math_angle_diagnostics"]["spread"] = float("nan")
    with pytest.raises(ValueError):
        validate_diagnostic_bundle(
            diagnostic,
            request,
            valid_ground,
            now=NOW,
            max_age_s=30,
        )


def test_validators_reject_resealed_wrong_upstream_receipt_kinds():
    request = TruthGateRequest(P, A, H, 0)
    ground = _ground(request)
    ground["source_claim_set_receipt_id"] = "other:claim:" + "a" * 64
    ground["receipt_id"] = GROUNDING_PREFIX + sha256(
        {key: value for key, value in ground.items() if key != "receipt_id"}
    )
    with pytest.raises(ValueError, match="canonical_source_claim_set_receipt_id_required"):
        validate_grounding_bundle(ground, request, now=NOW, max_age_s=30)

    valid_ground = _ground(request)
    diagnostic = _diagnostic(request, valid_ground)
    diagnostic["source_diagnostic_signal_receipt_id"] = "other:signal:" + "b" * 64
    diagnostic["receipt_id"] = DIAGNOSTIC_PREFIX + sha256(
        {key: value for key, value in diagnostic.items() if key != "receipt_id"}
    )
    with pytest.raises(
        ValueError,
        match="canonical_source_diagnostic_signal_receipt_id_required",
    ):
        validate_diagnostic_bundle(
            diagnostic,
            request,
            valid_ground,
            now=NOW,
            max_age_s=30,
        )


def test_freshness_accepts_exact_positive_boundary_and_rejects_zero_window():
    request = TruthGateRequest(P, A, H, 0)
    ground = _ground(request)
    ground["source_timestamp"] = NOW - 30
    causal = {key: value for key, value in ground.items() if key != "receipt_id"}
    ground["receipt_id"] = GROUNDING_PREFIX + sha256(causal)
    validate_grounding_bundle(ground, request, now=NOW, max_age_s=30)
    with pytest.raises(ValueError):
        validate_grounding_bundle(ground, request, now=NOW, max_age_s=0)


def test_same_or_unallowlisted_authority_holds_without_calls():
    class Both(Grounder, Diagnostic):
        resolver_id = "same"

    same = Both()
    request = TruthGateRequest(P, A, H, 0)
    result = evaluate_truth_gate(
        request,
        grounding_resolver=same,
        diagnostic_resolver=same,
        allowed_grounding_resolver_ids=frozenset({"same"}),
        allowed_diagnostic_resolver_ids=frozenset({"same"}),
        now=NOW,
        max_age_s=30,
    )
    assert result["status"] == "HOLD"
    assert same.calls == 0


def test_separate_objects_of_the_same_type_can_have_distinct_authority():
    class FlexibleAuthority:
        def __init__(self, resolver_id):
            self.resolver_id = resolver_id
            self.calls = 0

        def resolve_grounding(self, request):
            self.calls += 1
            return _ground(request)

        def resolve_diagnostics(self, request, grounding):
            self.calls += 1
            return _diagnostic(request, grounding)

    request = TruthGateRequest(P, A, H, 0)
    first = FlexibleAuthority("grounder:trusted")
    second = FlexibleAuthority("diagnostic:trusted")
    result = evaluate_truth_gate(
        request,
        grounding_resolver=first,
        diagnostic_resolver=second,
        allowed_grounding_resolver_ids=frozenset({"grounder:trusted"}),
        allowed_diagnostic_resolver_ids=frozenset({"diagnostic:trusted"}),
        now=NOW,
        max_age_s=30,
    )
    assert result["status"] == "READY_FOR_AURIS"
    assert first.calls == second.calls == 1


def test_evaluation_is_deterministic_and_has_no_mutating_output_aliases():
    request = TruthGateRequest(P, A, H, 0)
    first, _, _ = _evaluate(request)
    second, _, _ = _evaluate(request)
    assert first == second
    changed = copy.deepcopy(first)
    changed["status"] = "ACCEPT"
    with pytest.raises(ValueError):
        validate_truth_gate_result(changed)


def test_hash_valid_ready_result_cannot_hide_a_correction_directive():
    result, _, _ = _evaluate(TruthGateRequest(P, A, H, 0))
    result["correction_directive"] = {
        "failure_kind": "UNSUPPORTED",
        "evidence_receipt_ids": [E1],
        "next_attempt": 1,
    }
    causal = {key: value for key, value in result.items() if key != "receipt_id"}
    result["receipt_id"] = "truth-gate:qgita-kundalini:" + sha256(causal)
    with pytest.raises(ValueError):
        validate_truth_gate_result(result)


def test_hash_valid_correction_requires_matching_kundalini_stage():
    result, _, _ = _evaluate(
        TruthGateRequest(P, A, H, 0),
        Grounder([_finding("CONTRADICTED", links=[E2])]),
    )
    result["kundalini_stage"] = "Root"
    causal = {key: value for key, value in result.items() if key != "receipt_id"}
    result["receipt_id"] = "truth-gate:qgita-kundalini:" + sha256(causal)
    with pytest.raises(ValueError):
        validate_truth_gate_result(result)


def test_only_the_invalid_request_hold_may_have_blank_lineage():
    invalid = evaluate_truth_gate(
        object(),
        grounding_resolver=Grounder(),
        diagnostic_resolver=Diagnostic(),
        allowed_grounding_resolver_ids=frozenset({"grounder:trusted"}),
        allowed_diagnostic_resolver_ids=frozenset({"diagnostic:trusted"}),
        now=NOW,
        max_age_s=30,
    )
    validate_truth_gate_result(invalid)
    forged = copy.deepcopy(invalid)
    forged["reason"] = "trusted_evidence_required"
    causal = {key: value for key, value in forged.items() if key != "receipt_id"}
    forged["receipt_id"] = "truth-gate:qgita-kundalini:" + sha256(causal)
    with pytest.raises(ValueError):
        validate_truth_gate_result(forged)


def test_hash_valid_hold_cannot_use_falsy_numeric_diagnostic_id():
    result, _, _ = _evaluate(
        TruthGateRequest(P, A, H, 2),
        Grounder([_finding("UNSUPPORTED")]),
    )
    result["diagnostic_receipt_id"] = 0
    causal = {key: value for key, value in result.items() if key != "receipt_id"}
    result["receipt_id"] = "truth-gate:qgita-kundalini:" + sha256(causal)
    with pytest.raises(ValueError):
        validate_truth_gate_result(result)
