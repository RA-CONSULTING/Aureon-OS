from __future__ import annotations

import hashlib

import pytest

from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    TenNineOneHold,
    ThoughtPathRequest,
)
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    TruthGatedTenNineOneThoughtPath,
    validate_truth_gated_ten_nine_one_receipt,
)
from aureon.governance.material_truth_gate import (
    ALLOWED_RESPONSE_MARKER,
    MaterialAwareTenNineOneTruthGate,
    extract_allowed_responses,
)
from tests.aureon_ten_nine_one_fixtures import (
    NOW,
    TestEvidenceResolver,
    TestPropagator,
)

PROMPT = (
    "Evaluate only the immutable bounded proposal.\n"
    f"{ALLOWED_RESPONSE_MARKER}\n"
    "ACCEPT exact_receipts_and_limits_satisfied\n"
    "HOLD missing_or_stale_required_evidence\n"
    "ABORT explicit_veto_or_lineage_conflict"
)


def _request() -> ThoughtPathRequest:
    return ThoughtPathRequest(
        subject_type="agent",
        subject_id="Risk Governor",
        process_id="council-calibration:risk-governor",
        stage="auris_coherence_probe",
        work_kind="auris_coherence_measurement",
        prompt_digest=hashlib.sha256(PROMPT.encode()).hexdigest(),
        brain_passport_id="brain:" + "a" * 64,
    )


def _path():
    resolver = TestEvidenceResolver()
    propagator = TestPropagator()
    path = TruthGatedTenNineOneThoughtPath(
        resolver=resolver,
        propagator=propagator,
        truth_gate=MaterialAwareTenNineOneTruthGate(now=lambda: NOW),
        now=lambda: NOW,
    )
    return path, resolver, propagator


def test_exact_operator_menu_selection_reaches_auris_and_hive():
    path, resolver, propagator = _path()
    result = path.execute(
        request=_request(),
        prompt=PROMPT,
        infer=lambda _: "HOLD missing_or_stale_required_evidence",
    )
    receipt = validate_truth_gated_ten_nine_one_receipt(result.receipt, now=NOW)
    assert receipt["truth_gate_receipt"]["status"] == "READY_FOR_AURIS"
    assert receipt["truth_gate_receipt"]["failure_kind"] == ""
    assert resolver.hnc_calls == resolver.auris_calls == 1
    assert len(propagator.deliveries) == 1


def test_free_form_cloud_claim_holds_before_auris_or_propagation():
    path, resolver, propagator = _path()
    with pytest.raises(TenNineOneHold, match="truth_gate_correction_required"):
        path.execute(
            request=_request(),
            prompt=PROMPT,
            infer=lambda _: "ACCEPT I independently guarantee a profitable trade.",
        )
    assert resolver.hnc_calls == 1
    assert resolver.auris_calls == 0
    assert propagator.deliveries == []


@pytest.mark.parametrize(
    "prompt",
    [
        "no menu",
        f"{ALLOWED_RESPONSE_MARKER}\nACCEPT only_one",
        f"{ALLOWED_RESPONSE_MARKER}\nACCEPT duplicate\nACCEPT duplicate",
        f"{ALLOWED_RESPONSE_MARKER}\nPROCEED invalid\nHOLD valid",
    ],
)
def test_response_menu_must_be_unique_bounded_and_exact(prompt):
    with pytest.raises(ValueError):
        extract_allowed_responses(prompt)
