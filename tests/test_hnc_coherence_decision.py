from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from aureon.core.hnc_field import CanonicalField, build_hnc_live_field_receipt_id
from aureon.governance.cognition_gate import (
    build_hnc_coherence_request,
    evaluate_hnc_coherence,
    validate_hnc_coherence_decision,
)

NOW = 1_800_000_000.0
PROPOSAL = "tool:proposal:" + ("a" * 64)
ACTIVE_V1 = 0.80
LIGHTHOUSE_V1 = 0.945


def _field(*, gamma: float = ACTIVE_V1, age_s: float = 1.0) -> CanonicalField:
    source_timestamp = NOW - age_s
    received_at = source_timestamp + 0.1
    step = 11
    memory_hash = "2" * 64
    memory_receipt_id = f"hnc:lambda_history:{memory_hash}"
    input_receipt_ids = tuple(sorted((
        memory_receipt_id,
        "provider:test:a",
        "provider:test:b",
    )))
    receipt_id = build_hnc_live_field_receipt_id(
        input_receipt_ids=input_receipt_ids,
        source_timestamp=source_timestamp,
        received_at=received_at,
        step=step,
        lambda_t=0.63,
        coherence_gamma=gamma,
        consciousness_psi=0.72,
        symbolic_life_score=0.91,
    )
    return CanonicalField(
        available=True,
        symbolic_life_score=0.91,
        coherence_gamma=gamma,
        consciousness_psi=0.72,
        consciousness_level="aware",
        lambda_t=0.63,
        step=step,
        source="hnc_live_daemon",
        evidence_transport="persisted_trace",
        source_id="aureon:hnc:live_daemon",
        source_timestamp=source_timestamp,
        received_at=received_at,
        receipt_id=receipt_id,
        receipt_type="hnc_live_field",
        provider_receipt_type="hnc_live_field",
        input_receipt_ids=input_receipt_ids,
        memory_receipt_id=memory_receipt_id,
        memory_canonical_hash=memory_hash,
        data_status="live",
        truth_status="real_derived",
        generated_values=False,
        source_count=2.0,
        freshness_status="fresh",
        equation_inputs_complete=True,
        action_gate_reason="route_specific_market_link_required",
    )


def _request(effect: str = "read_only"):
    return build_hnc_coherence_request(
        proposal_digest=PROPOSAL,
        effect=effect,
        operation_id="aureon.test.hnc-decision.v1",
    )


def _assert_numeric_free(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, dict):
        for nested in value.values():
            _assert_numeric_free(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_numeric_free(nested)
        return
    assert not isinstance(value, (int, float)), value


def test_active_hnc_proceeds_for_read_only_but_remains_evidence_only() -> None:
    decision = evaluate_hnc_coherence(
        _request(),
        canonical_field=_field(gamma=ACTIVE_V1),
        now=NOW,
    )

    assert decision["outcome"] == "PROCEED"
    assert decision["policy_version"] == "aureon.hnc_coherence.policy.v1"
    assert decision["threshold"] == ACTIVE_V1
    assert decision["coherence_satisfied"] is True
    assert decision["route_authorization_required"] is True
    assert decision["action_eligible"] is False
    assert decision["economic_eligible"] is False
    assert decision["economic_mutation"] is False
    assert decision["receipt_id"].startswith("hnc:coherence_decision:")
    assert validate_hnc_coherence_decision(
        decision,
        expected_proposal_digest=PROPOSAL,
        now=NOW,
    ) == decision


def test_consequential_effect_uses_lighthouse_threshold_deterministically() -> None:
    held = evaluate_hnc_coherence(
        _request("economic_mutation"),
        canonical_field=_field(gamma=LIGHTHOUSE_V1 - 0.001),
        now=NOW,
    )
    proceeded = evaluate_hnc_coherence(
        _request("economic_mutation"),
        canonical_field=_field(gamma=LIGHTHOUSE_V1),
        now=NOW,
    )

    assert held["outcome"] == "HOLD"
    assert held["flow"] == "OBSERVE"
    assert proceeded["outcome"] == "PROCEED"
    assert proceeded["threshold"] == LIGHTHOUSE_V1
    # HNC decides coherence; it does not counterfeit route authority.
    assert proceeded["route_authorization_required"] is True
    assert proceeded["economic_eligible"] is False


@pytest.mark.parametrize(
    ("effect", "threshold"),
    [
        ("read_only", 0.80),
        ("local_mutation", 0.80),
        ("external_mutation", 0.945),
        ("economic_mutation", 0.945),
        ("privileged", 0.945),
    ],
)
def test_v1_effect_threshold_contract_is_literal(effect: str, threshold: float) -> None:
    decision = evaluate_hnc_coherence(
        _request(effect),
        canonical_field=_field(gamma=threshold),
        now=NOW,
    )

    assert decision["policy_version"] == "aureon.hnc_coherence.policy.v1"
    assert decision["threshold"] == threshold
    assert decision["outcome"] == "PROCEED"
    assert decision["route_authorization_required"] is True
    assert decision["economic_eligible"] is False


@pytest.mark.parametrize(
    "field",
    [
        CanonicalField(),
        _field(age_s=301.0),
        replace(_field(), generated_values=True),
        replace(_field(), input_receipt_ids=()),
    ],
)
def test_missing_stale_or_laundered_field_enters_numeric_free_repair(field) -> None:
    decision = evaluate_hnc_coherence(
        _request(),
        canonical_field=field,
        now=NOW,
    )

    assert decision["outcome"] == "REPAIR"
    assert decision["receipt_id"] is None
    assert decision["coherence_gamma"] is None
    assert decision["repair_safe_only"] is True
    _assert_numeric_free(decision)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("outcome", "HOLD"),
        ("operation_id", "aureon.test.changed.v1"),
        ("coherence_gamma", 0.1),
        ("hnc_field_digest", "0" * 64),
        ("action_eligible", True),
    ],
)
def test_receipt_tampering_is_rejected(field: str, value: Any) -> None:
    decision = evaluate_hnc_coherence(
        _request(),
        canonical_field=_field(),
        now=NOW,
    )
    tampered = {**decision, field: value}

    with pytest.raises(ValueError):
        validate_hnc_coherence_decision(tampered, now=NOW)


def test_receipt_cannot_be_replayed_for_another_proposal() -> None:
    decision = evaluate_hnc_coherence(
        _request(),
        canonical_field=_field(),
        now=NOW,
    )

    with pytest.raises(ValueError, match="proposal_mismatch"):
        validate_hnc_coherence_decision(
            decision,
            expected_proposal_digest="tool:proposal:" + ("b" * 64),
            now=NOW,
        )


def test_receipt_freshness_window_cannot_be_widened_by_caller() -> None:
    decision = evaluate_hnc_coherence(
        _request(),
        canonical_field=_field(),
        now=NOW,
    )

    with pytest.raises(ValueError, match="fresh_hnc_coherence_decision_required"):
        validate_hnc_coherence_decision(
            decision,
            now=NOW + 301.0,
            max_age_s=3600.0,
        )


def test_unknown_effect_aborts_without_fabricating_a_receipt() -> None:
    decision = evaluate_hnc_coherence(
        _request("unknown"),
        canonical_field=_field(),
        now=NOW,
    )

    assert decision["outcome"] == "ABORT"
    assert decision["receipt_id"] is None
    assert decision["reason"] == "known_effect_class_required"
