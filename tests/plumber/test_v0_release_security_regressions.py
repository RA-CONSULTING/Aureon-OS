from __future__ import annotations

from datetime import timedelta

from aureon.plumber.enclave import LocalComputationResult
from aureon.plumber.immune_gate import (
    GateClass,
    GateEvidence,
    build_gate_context_commitment,
    evaluate_immune_gate,
)
from aureon.plumber.release_engine import ReleaseCode, ReleaseDisposition
from aureon.plumber.schema import parse_timestamp
from tests.plumber.test_packet_release_engine import (
    DIGESTS,
    MASTER_KEY,
    NOW,
    PURPOSE,
    Fixture,
    _fixture,
)


def _inspect(fixture: Fixture):  # type: ignore[no-untyped-def]
    return fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )


def _processor(_view: memoryview) -> LocalComputationResult:
    return LocalComputationResult(
        outcome_code="synthetic_ok",
        result_commitment=DIGESTS[71],
        evidence_commitments={},
    )


def _execute(fixture: Fixture, inspection, gate, *, now):  # type: ignore[no-untyped-def]
    return fixture.engine.execute(
        inspection,
        gate,
        fixture.hnc_packet,
        master_key=MASTER_KEY,
        expected_purpose=PURPOSE,
        processor_id="security_regression_probe",
        processor=_processor,
        now=now,
    )


def _externally_computed_gate(inspection, *, inspection_commitment: str):  # type: ignore[no-untyped-def]
    context = build_gate_context_commitment(
        packet_identity=inspection.packet_identity,
        session_identity=inspection.session_identity,
        purpose_commitment=inspection.purpose_commitment,
    )
    evidence = tuple(
        GateEvidence(
            gate_class=gate_class,
            receipt_commitment=inspection.gate_evidence_commitments[str(gate_class)],
            valid=True,
            context_commitment=context,
        )
        for gate_class in GateClass
    )
    return evaluate_immune_gate(
        evidence,
        packet_inspection_commitment=inspection_commitment,
        evaluated_at=parse_timestamp(inspection.inspected_at, field="inspected_at"),
        expires_at=parse_timestamp(
            inspection.evidence_expires_at,
            field="evidence_expires_at",
        ),
    )


def test_release_engine_rejects_expired_and_rollback_execution_time() -> None:
    expired_fixture = _fixture()
    expired_inspection = _inspect(expired_fixture)
    expired_gate = expired_fixture.engine.issue_gate(expired_inspection)
    expired, expired_enclave = _execute(
        expired_fixture,
        expired_inspection,
        expired_gate,
        now=NOW + timedelta(days=365),
    )
    assert expired.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.INSPECTION_EVIDENCE_EXPIRED in expired.denial_codes
    assert expired_enclave is None

    rollback_fixture = _fixture()
    rollback_inspection = _inspect(rollback_fixture)
    rollback_gate = rollback_fixture.engine.issue_gate(rollback_inspection)
    rollback, rollback_enclave = _execute(
        rollback_fixture,
        rollback_inspection,
        rollback_gate,
        now=NOW,
    )
    assert rollback.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.INSPECTION_TIME_ROLLBACK in rollback.denial_codes
    assert rollback_enclave is None


def test_release_engine_requires_engine_issued_exact_inspection_gate() -> None:
    fixture = _fixture()
    inspection = _inspect(fixture)
    unissued = _externally_computed_gate(
        inspection,
        inspection_commitment=inspection.inspection_commitment,
    )
    unissued_decision = fixture.engine.evaluate(inspection, unissued)
    assert unissued_decision.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.IMMUNE_GATE_NOT_ISSUED in unissued_decision.denial_codes
    denied, enclave = _execute(
        fixture,
        inspection,
        unissued,
        now=NOW + timedelta(seconds=2),
    )
    assert denied.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.IMMUNE_GATE_NOT_ISSUED in denied.denial_codes
    assert enclave is None

    wrong_binding = _externally_computed_gate(
        inspection,
        inspection_commitment=DIGESTS[75],
    )
    decision = fixture.engine.evaluate(inspection, wrong_binding)
    assert decision.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.IMMUNE_GATE_BINDING_MISMATCH in decision.denial_codes

    issued = fixture.engine.issue_gate(inspection)
    completed, completed_enclave = _execute(
        fixture,
        inspection,
        issued,
        now=NOW + timedelta(seconds=2),
    )
    assert completed.disposition is ReleaseDisposition.COMPLETED_LOCAL
    assert completed_enclave is not None
