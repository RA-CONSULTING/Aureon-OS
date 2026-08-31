from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aureon.plumber.crypto import generate_ed25519_private_key
from aureon.plumber.immune_gate import GateClass, GateEvidence, GateVerdict, evaluate_immune_gate
from aureon.plumber.quorum import (
    AuthorityPermit,
    AuthorityRole,
    QuorumPolicyV0,
    evaluate_quorum,
)
from aureon.plumber.schema import DenialCode

DIGESTS = tuple(f"{number:064x}" for number in range(1, 30))
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def test_immune_gate_requires_all_six_evidence_classes() -> None:
    evidence = tuple(
        GateEvidence(gate_class=gate_class, receipt_commitment=DIGESTS[index], valid=True)
        for index, gate_class in enumerate(GateClass)
    )
    gate_context = {
        "packet_inspection_commitment": DIGESTS[25],
        "evaluated_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
    }
    approved = evaluate_immune_gate(evidence, **gate_context)
    assert approved.verdict is GateVerdict.APPROVED
    assert not approved.quarantine_required

    missing = evaluate_immune_gate(evidence[:-1], **gate_context)
    assert missing.verdict is GateVerdict.DENIED
    assert missing.quarantine_required
    assert DenialCode.POLICY_RECEIPT_MISSING in missing.denial_codes

    invalid = (*evidence[:-1], GateEvidence(
        gate_class=GateClass.GOVERNANCE,
        receipt_commitment=DIGESTS[5],
        valid=False,
        denial_codes=(str(DenialCode.PURPOSE_MISMATCH),),
    ))
    assert DenialCode.PURPOSE_MISMATCH in evaluate_immune_gate(
        invalid,
        **gate_context,
    ).denial_codes


def _permits(policy: QuorumPolicyV0) -> list[AuthorityPermit]:
    return [
        AuthorityPermit.issue(
            role=role,
            authority_id=f"authority-{role}",
            packet_identity="packet-1",
            session_identity="session-1",
            purpose_commitment=DIGESTS[10],
            policy_commitment=policy.policy_commitment,
            wrapped_share_commitment=DIGESTS[11 + index],
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=5),
            private_key=generate_ed25519_private_key(),
        )
        for index, role in enumerate(policy.required_roles)
    ]


def test_typed_quorum_requires_distinct_authorities_and_roles() -> None:
    policy = QuorumPolicyV0.build()
    permits = _permits(policy)
    result = evaluate_quorum(
        policy,
        tuple(reversed(permits)),
        now=NOW + timedelta(seconds=1),
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=DIGESTS[10],
    )
    assert result.valid
    assert set(result.accepted_roles) == set(policy.required_roles)

    incomplete = evaluate_quorum(
        policy,
        permits[:-1],
        now=NOW + timedelta(seconds=1),
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=DIGESTS[10],
    )
    assert DenialCode.QUORUM_INCOMPLETE in incomplete.denial_codes

    duplicate = AuthorityPermit.issue(
        role=permits[-1].role,
        authority_id=permits[0].authority_id,
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=DIGESTS[10],
        policy_commitment=policy.policy_commitment,
        wrapped_share_commitment=DIGESTS[20],
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        private_key=generate_ed25519_private_key(),
    )
    duplicate_result = evaluate_quorum(
        policy,
        (*permits[:-1], duplicate),
        now=NOW + timedelta(seconds=1),
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=DIGESTS[10],
    )
    assert DenialCode.QUORUM_DUPLICATE_AUTHORITY in duplicate_result.denial_codes
