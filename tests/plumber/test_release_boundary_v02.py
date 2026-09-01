from __future__ import annotations

import hashlib
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from operator import setitem
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.harmonic.hnc_quantum_packet_crypto import build_hnc_quantum_packet
from aureon.plumber.authorization_chain_v02 import (
    AUTHORIZATION_ROLES,
    AuthorizationChainV02,
    assemble_authorization_chain_v02,
    build_authorization_snapshot_v02,
    build_continuity_decision_v02,
    build_custody_permit_v02,
)
from aureon.plumber.crypto import domain_hash, ed25519_public_key_hex
from aureon.plumber.magic_star_v02 import (
    POINT_ROLES,
    STAR_AUTHORITY_ROLES,
    AuthorityBindingV02,
    MagicStarV02,
    assemble_magic_star_v02,
    build_authority_binding_v02,
    build_candidate_center_v02,
    build_epas_precondition_v02,
    build_heart_precondition_v02,
    build_heart_source_identity_commitment_v02,
    build_magic_star_point_v02,
    component_commitment_v02,
    sign_component_v02,
)
from aureon.plumber.receipts import ReceiptKind, ReceiptVerdict, SignedReceipt
from aureon.plumber.recipient_proof_v02 import (
    RecipientChallengeV02,
    RecipientEnrollmentV02,
    RecipientProofV02,
    RecipientProofVerifierV02,
    build_recipient_proof_v02,
)
from aureon.plumber.release_boundary_v02 import (
    CapabilityPolicyV02,
    CapabilityReleaseResultV02,
    ContinuityStateEvidenceV02,
    EvidenceExpectationsV02,
    LiveBindingEvidenceV02,
    LocalDevelopmentReleaseBoundaryV02,
    ReleaseBoundaryError,
    build_release_context_v02,
    validate_capability_release_result_v02,
)
from aureon.plumber.release_evidence_v02 import (
    ORGAN_ROLES,
    RELEASE_EVIDENCE_ROLES,
    ReleaseEvidenceV02,
    assemble_release_evidence_v02,
    build_organ_receipt_v02,
)
from aureon.plumber.release_state_v02 import (
    EPASChainSnapshot,
    InMemoryEPASChainStoreV02,
    InMemoryReleaseStateStoreV02,
    ReleasePhase,
)
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    ProtectedMagicStarPacketV02,
    RegisteredCapabilityV02,
    validate_magic_star_hnc_packet_v02,
)

NOW_MS = 1_900_000_000_000
EXPIRES_MS = NOW_MS + 60_000
PURPOSE = "verify_document_signature"
CAPABILITY_ID = "verify-signature"
PLAINTEXT = b"protected-release-boundary-canary"
MASTER_KEY = b"release-boundary-local-lab-key-material"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _flip_hex(value: str) -> str:
    return f"{value[:-1]}{'0' if value[-1] != '0' else '1'}"


def _flip_token(value: str) -> str:
    return f"{value[:-1]}{'A' if value[-1] != 'A' else 'B'}"


def _private_key(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(f"release-boundary:{label}".encode()).digest()
    )


def _datetime_from_ms(value: int) -> datetime:
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)


def _binding(role: str, private_key: Ed25519PrivateKey) -> AuthorityBindingV02:
    slug = role.lower().replace("_", "-")
    return build_authority_binding_v02(
        role=role,
        issuer=f"boundary-issuer-{slug}",
        principal=f"boundary-principal-{slug}",
        key_id=f"boundary-key-{slug}",
        private_key=private_key,
    )


@dataclass
class _Clock:
    now_ms: int = NOW_MS

    def __call__(self) -> int:
        return self.now_ms


@dataclass
class _ProbeState:
    live: LiveBindingEvidenceV02
    continuity_samples: list[ContinuityStateEvidenceV02]
    expectations: EvidenceExpectationsV02


@dataclass(frozen=True)
class _BoundaryFixture:
    boundary: LocalDevelopmentReleaseBoundaryV02
    custody: LocalDevelopmentStarCustodyV02
    packet: ProtectedMagicStarPacketV02
    challenge: RecipientChallengeV02
    recipient_proof: RecipientProofV02
    star: MagicStarV02
    release_evidence: ReleaseEvidenceV02
    authorization_chain: AuthorizationChainV02
    receipt_authority: AuthorityBindingV02
    state_store: InMemoryReleaseStateStoreV02
    epas_store: InMemoryEPASChainStoreV02
    initial_epas: EPASChainSnapshot
    clock: _Clock
    probes: _ProbeState
    invocations: list[bytes]
    session_id: str
    temporal_commitment: str
    observer_commitment: str
    channel_binding_sha256: str
    live_binding_sha256: str
    runtime_measurement_sha256: str

    def release(
        self,
        *,
        packet: ProtectedMagicStarPacketV02 | None = None,
        star: MagicStarV02 | None = None,
        release_evidence: ReleaseEvidenceV02 | None = None,
        authorization_chain: AuthorizationChainV02 | None = None,
        capability_id: str = CAPABILITY_ID,
        channel_binding_sha256: str | None = None,
        live_binding_sha256: str | None = None,
        runtime_measurement_sha256: str | None = None,
    ) -> CapabilityReleaseResultV02:
        return self.boundary.release(
            packet or self.packet,
            session_id=self.session_id,
            challenge=self.challenge,
            recipient_proof=self.recipient_proof,
            temporal_commitment=self.temporal_commitment,
            observer_commitment=self.observer_commitment,
            expected_channel_binding_sha256=(
                self.channel_binding_sha256
                if channel_binding_sha256 is None
                else channel_binding_sha256
            ),
            expected_live_binding_sha256=(
                self.live_binding_sha256
                if live_binding_sha256 is None
                else live_binding_sha256
            ),
            expected_runtime_measurement_sha256=(
                self.runtime_measurement_sha256
                if runtime_measurement_sha256 is None
                else runtime_measurement_sha256
            ),
            star=star or self.star,
            release_evidence=release_evidence or self.release_evidence,
            authorization_chain=authorization_chain or self.authorization_chain,
            capability_id=capability_id,
        )


def _build_fixture(
    *,
    packet_id: str = "packet-release-v02",
    session_id: str = "session-release-v02",
    epas_store: InMemoryEPASChainStoreV02 | None = None,
    handler: Callable[[bytes], Mapping[str, Any]] | None = None,
    heart_source_identity_override: str | None = None,
    heart_policy_commitment_override: str | None = None,
) -> _BoundaryFixture:
    clock = _Clock()
    all_roles = sorted(
        set(STAR_AUTHORITY_ROLES)
        | set(RELEASE_EVIDENCE_ROLES)
        | set(AUTHORIZATION_ROLES)
        | {"CAPABILITY_RECEIPT"}
    )
    keys = {role: _private_key(role) for role in all_roles}
    bindings = {role: _binding(role, keys[role]) for role in all_roles}
    star_trust = {role: bindings[role] for role in STAR_AUTHORITY_ROLES}
    evidence_trust = {role: bindings[role] for role in RELEASE_EVIDENCE_ROLES}
    authorization_trust = {role: bindings[role] for role in AUTHORIZATION_ROLES}

    invocations: list[bytes] = []

    def registered_handler(plaintext: bytes) -> Mapping[str, Any]:
        invocations.append(plaintext)
        if handler is not None:
            return handler(plaintext)
        return {"signature_valid": plaintext == PLAINTEXT}

    capability_measurement = _digest("registered-capability-measurement")
    capability_policy = CapabilityPolicyV02(
        capability_id=CAPABILITY_ID,
        capability_measurement_sha256=capability_measurement,
        allowed_output_keys=("signature_valid",),
        output_types_by_key={"signature_valid": "bool"},
        required_output_keys=("signature_valid",),
    )
    registered = RegisteredCapabilityV02(
        capability_id=CAPABILITY_ID,
        measurement_sha256=capability_measurement,
        policy_measurement_sha256=capability_policy.commitment,
        result_schema={"signature_valid": "bool"},
        handler=registered_handler,
    )
    state_store = InMemoryReleaseStateStoreV02(trusted_now_ms=clock)
    shared_epas_store = epas_store or InMemoryEPASChainStoreV02(
        epoch=7,
        head_sha256=_digest("initial-epas-head"),
    )
    initial_epas = shared_epas_store.snapshot()
    custody = LocalDevelopmentStarCustodyV02(
        allow_insecure_same_process=True,
        source_authority=star_trust["SOURCE"],
        source_private_key=keys["SOURCE"],
        state_store=state_store,
        authorization_trust=authorization_trust,
        capabilities={CAPABILITY_ID: registered},
        trusted_now_ms=clock,
    )

    channel = _digest("channel-binding")
    temporal = _digest("temporal-commitment")
    observer = _digest("observer-commitment")
    live = _digest("live-binding")
    runtime = _digest("runtime-measurement")
    release_context = build_release_context_v02(
        packet_id=packet_id,
        session_id=session_id,
        purpose=PURPOSE,
        channel_binding_sha256=channel,
        temporal_commitment=temporal,
        observer_commitment=observer,
        live_binding_sha256=live,
        runtime_measurement_sha256=runtime,
        policy_measurement_sha256=capability_policy.commitment,
    )
    carrier = build_hnc_quantum_packet(
        PLAINTEXT,
        MASTER_KEY,
        purpose=PURPOSE,
        operator_aad={"laboratory": True},
    )
    packet = custody.protect_carrier(
        packet_id=packet_id,
        purpose=PURPOSE,
        release_context_sha256=release_context,
        legacy_carrier=carrier,
        legacy_master_key=MASTER_KEY,
    )
    packet_preflight = validate_magic_star_hnc_packet_v02(
        packet,
        source_authority=star_trust["SOURCE"],
    )
    heart_source_identity = build_heart_source_identity_commitment_v02(
        source_authority=star_trust["SOURCE"],
        packet_id=packet.packet_id,
        packet_commitment=packet.packet_commitment,
        source_signature_commitment=packet_preflight["source_signature_commitment"],
    )

    recipient_key = _private_key(f"recipient-{session_id}")
    enrollment = RecipientEnrollmentV02(
        recipient_id=f"recipient-{session_id}",
        principal=f"recipient-principal-{session_id}",
        key_id=f"recipient-key-{session_id}",
        public_key_hex=ed25519_public_key_hex(recipient_key),
        allowed_channel_bindings=(channel,),
        allowed_purposes=(PURPOSE,),
    )
    recipient_verifier = RecipientProofVerifierV02(
        enrollments={enrollment.recipient_id: enrollment},
        trusted_now_ms=clock,
    )
    challenge = recipient_verifier.issue_challenge(
        session_id=session_id,
        packet_commitment=packet.packet_commitment,
        purpose=PURPOSE,
        channel_binding_sha256=channel,
    )
    recipient_proof = build_recipient_proof_v02(
        challenge,
        enrollment=enrollment,
        private_key=recipient_key,
        trusted_now_ms=clock,
    )

    expectations = EvidenceExpectationsV02(
        organ_evidence_sha256_by_role={
            role: _digest(f"organ-evidence-{role}") for role in ORGAN_ROLES
        },
        star_point_evidence_sha256_by_role={
            role: _digest(f"point-evidence-{role}") for role in POINT_ROLES
        },
        epas_source_lineage_sha256=_digest("epas-source-lineage"),
        epas_evidence_sha256=_digest("epas-evidence"),
        epas_evidence_class="verified-source",
    )
    continuity = ContinuityStateEvidenceV02(
        previous_decision_head_sha256=_digest("continuity-decision-head"),
        revocation_epoch=11,
        observed_at_ms=NOW_MS,
        valid=True,
    )
    probes = _ProbeState(
        live=LiveBindingEvidenceV02(
            live_binding_sha256=live,
            runtime_measurement_sha256=runtime,
            policy_measurement_sha256=capability_policy.commitment,
            observed_at_ms=NOW_MS,
            valid=True,
        ),
        continuity_samples=[continuity],
        expectations=expectations,
    )

    epas_precondition = build_epas_precondition_v02(
        release_context_sha256=release_context,
        source_lineage_sha256=expectations.epas_source_lineage_sha256,
        evidence_sha256=expectations.epas_evidence_sha256,
        evidence_class=expectations.epas_evidence_class,
        previous_memory_head_sha256=initial_epas.head_sha256,
        memory_epoch=initial_epas.epoch,
        verdict="CLEAR",
        outcome="PROCEED",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=star_trust["EPAS"],
        private_key=keys["EPAS"],
    )
    heart_receipt = SignedReceipt.issue(
        kind=ReceiptKind.HEART,
        packet_identity=packet.packet_id,
        session_identity=session_id,
        purpose_commitment=domain_hash("aureon.plumber.purpose.v0", PURPOSE),
        source_identity_commitment=(
            heart_source_identity
            if heart_source_identity_override is None
            else heart_source_identity_override
        ),
        temporal_identity_commitment=temporal,
        observer_transcript_commitment=observer,
        policy_commitment=(
            capability_policy.commitment
            if heart_policy_commitment_override is None
            else heart_policy_commitment_override
        ),
        runtime_measurement_commitment=runtime,
        verdict=ReceiptVerdict.APPROVED,
        issued_at=_datetime_from_ms(NOW_MS - 1_000),
        expires_at=_datetime_from_ms(EXPIRES_MS),
        signer_id=star_trust["HEART"].principal,
        private_key=keys["HEART"],
    )
    heart_precondition = build_heart_precondition_v02(
        release_context_sha256=release_context,
        packet_id=packet.packet_id,
        packet_commitment=packet.packet_commitment,
        session_id=session_id,
        purpose=PURPOSE,
        temporal_commitment=temporal,
        observer_commitment=observer,
        runtime_measurement_sha256=runtime,
        heart_receipt=heart_receipt,
        verdict="APPROVE",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=star_trust["HEART"],
        private_key=keys["HEART"],
    )
    epas_commitment = component_commitment_v02(epas_precondition)
    candidate_center = build_candidate_center_v02(
        release_context_sha256=release_context,
        packet_commitment=packet.packet_commitment,
        recipient_proof_commitment=recipient_proof.commitment,
        purpose=PURPOSE,
        temporal_commitment=temporal,
        observer_commitment=observer,
        epas_commitment=epas_commitment,
        heart_commitment=component_commitment_v02(heart_precondition),
    )
    points = tuple(
        build_magic_star_point_v02(
            index=index,
            release_context_sha256=release_context,
            candidate_center_sha256=candidate_center,
            evidence_sha256=expectations.star_point_evidence_sha256_by_role[role],
            share_binding_sha256=packet.share_bindings[index]["binding_sha256"],
            verdict="APPROVE",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=star_trust[role],
            private_key=keys[role],
        )
        for index, role in enumerate(POINT_ROLES)
    )
    star = assemble_magic_star_v02(
        release_context_sha256=release_context,
        candidate_center_sha256=candidate_center,
        epas_precondition=epas_precondition,
        heart_precondition=heart_precondition,
        points=points,
        trust=star_trust,
        seal_authority=star_trust["STAR_SEAL"],
        seal_private_key=keys["STAR_SEAL"],
        trusted_now_ms=clock,
    )

    organ_shared = {
        "packet_commitment": packet.packet_commitment,
        "session_id": session_id,
        "purpose": PURPOSE,
        "release_context_sha256": release_context,
        "recipient_proof_commitment": recipient_proof.commitment,
        "star_commitment": star.commitment,
        "epas_commitment": epas_commitment,
        "live_binding_sha256": live,
        "runtime_measurement_sha256": runtime,
        "policy_measurement_sha256": capability_policy.commitment,
    }
    organ_receipts = tuple(
        build_organ_receipt_v02(
            role=role,
            **organ_shared,
            evidence_sha256=expectations.organ_evidence_sha256_by_role[role],
            verdict="APPROVE",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=evidence_trust[role],
            private_key=keys[role],
        )
        for role in ORGAN_ROLES
    )
    release_evidence = assemble_release_evidence_v02(
        organ_receipts=organ_receipts,
        trust=evidence_trust,
        release_proof_authority=evidence_trust["RELEASE_PROOF"],
        release_proof_private_key=keys["RELEASE_PROOF"],
        trusted_now_ms=clock,
    )
    release_proof_commitment = component_commitment_v02(release_evidence.release_proof)

    continuity_decision = build_continuity_decision_v02(
        packet_commitment=packet.packet_commitment,
        session_id=session_id,
        purpose=PURPOSE,
        star_commitment=star.commitment,
        release_proof_commitment=release_proof_commitment,
        previous_decision_head_sha256=continuity.previous_decision_head_sha256,
        revocation_epoch=continuity.revocation_epoch,
        verdict="ELIGIBLE",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=authorization_trust["CONTINUITY"],
        private_key=keys["CONTINUITY"],
    )
    authorization_snapshot = build_authorization_snapshot_v02(
        packet_commitment=packet.packet_commitment,
        session_id=session_id,
        purpose=PURPOSE,
        release_context_sha256=release_context,
        recipient_proof_commitment=recipient_proof.commitment,
        star_commitment=star.commitment,
        epas_commitment=epas_commitment,
        release_proof_commitment=release_proof_commitment,
        continuity_commitment=component_commitment_v02(continuity_decision),
        live_binding_sha256=live,
        runtime_measurement_sha256=runtime,
        policy_measurement_sha256=capability_policy.commitment,
        verdict="AUTHORIZED",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=authorization_trust["AUTHORIZATION"],
        private_key=keys["AUTHORIZATION"],
    )
    authorization_commitment = component_commitment_v02(authorization_snapshot)
    permits = tuple(
        build_custody_permit_v02(
            role=role,
            packet_commitment=packet.packet_commitment,
            session_id=session_id,
            purpose=PURPOSE,
            authorization_commitment=authorization_commitment,
            share_binding_sha256=packet.share_bindings[index]["binding_sha256"],
            verdict="PERMIT",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=authorization_trust[role],
            private_key=keys[role],
        )
        for index, role in enumerate(POINT_ROLES)
    )
    authorization_chain = assemble_authorization_chain_v02(
        continuity_decision=continuity_decision,
        authorization_snapshot=authorization_snapshot,
        permits=permits,
        trust=authorization_trust,
        custody_authority=authorization_trust["CUSTODY"],
        custody_private_key=keys["CUSTODY"],
        trusted_now_ms=clock,
    )

    def live_probe() -> LiveBindingEvidenceV02:
        return probes.live

    def continuity_probe(
        observed_packet_id: str,
        observed_session_id: str,
    ) -> ContinuityStateEvidenceV02:
        if observed_packet_id != packet_id or observed_session_id != session_id:
            raise AssertionError("continuity probe received the wrong release identity")
        if len(probes.continuity_samples) > 1:
            return probes.continuity_samples.pop(0)
        return probes.continuity_samples[0]

    def expectations_probe(
        observed_packet_id: str,
        observed_session_id: str,
    ) -> EvidenceExpectationsV02:
        if observed_packet_id != packet_id or observed_session_id != session_id:
            raise AssertionError("evidence probe received the wrong release identity")
        return probes.expectations

    boundary = LocalDevelopmentReleaseBoundaryV02(
        allow_insecure_same_process=True,
        state_store=state_store,
        epas_store=shared_epas_store,
        custody=custody,
        recipient_verifier=recipient_verifier,
        star_trust=star_trust,
        release_evidence_trust=evidence_trust,
        authorization_trust=authorization_trust,
        receipt_authority=bindings["CAPABILITY_RECEIPT"],
        receipt_private_key=keys["CAPABILITY_RECEIPT"],
        capability_policies={CAPABILITY_ID: capability_policy},
        live_binding_probe=live_probe,
        continuity_state_probe=continuity_probe,
        evidence_expectations_probe=expectations_probe,
        trusted_now_ms=clock,
    )
    return _BoundaryFixture(
        boundary=boundary,
        custody=custody,
        packet=packet,
        challenge=challenge,
        recipient_proof=recipient_proof,
        star=star,
        release_evidence=release_evidence,
        authorization_chain=authorization_chain,
        receipt_authority=bindings["CAPABILITY_RECEIPT"],
        state_store=state_store,
        epas_store=shared_epas_store,
        initial_epas=initial_epas,
        clock=clock,
        probes=probes,
        invocations=invocations,
        session_id=session_id,
        temporal_commitment=temporal,
        observer_commitment=observer,
        channel_binding_sha256=channel,
        live_binding_sha256=live,
        runtime_measurement_sha256=runtime,
    )


def _assert_denied_with_epas_transition(fixture: _BoundaryFixture) -> None:
    state = fixture.state_store.snapshot(fixture.session_id)
    epas = fixture.epas_store.snapshot()
    expected_head = domain_hash(
        "AUREON-PLUMBER-V02-EPAS-MEMORY",
        {
            "previous_epoch": fixture.initial_epas.epoch,
            "previous_head_sha256": fixture.initial_epas.head_sha256,
            "terminal_star_sha256": fixture.star.commitment,
            "session_id": fixture.session_id,
            "authorization_sha256": fixture.authorization_chain.commitment,
            "outcome": "DENIED",
            "next_epoch": fixture.initial_epas.epoch + 1,
        },
    )

    assert state.phase is ReleasePhase.DENIED
    assert state.phase is not ReleasePhase.CONSUMED
    assert epas.epoch == fixture.initial_epas.epoch + 1
    assert epas.head_sha256 == expected_head


def test_release_boundary_rejects_capability_swap_without_burning_challenge() -> None:
    fixture = _build_fixture()

    with pytest.raises(ReleaseBoundaryError, match="capability_not_authorized"):
        fixture.release(capability_id="swapped-capability")

    assert fixture.invocations == []
    result = fixture.release()
    assert result.result == {"signature_valid": True}
    assert fixture.invocations == [PLAINTEXT]


def test_release_boundary_rejects_packet_tamper_before_recipient_proof_consumption() -> None:
    fixture = _build_fixture()
    tampered = replace(
        fixture.packet,
        ciphertext_b64=_flip_token(fixture.packet.ciphertext_b64),
    )

    with pytest.raises(ReleaseBoundaryError):
        fixture.release(packet=tampered)

    assert fixture.invocations == []
    result = fixture.release()
    assert result.result == {"signature_valid": True}
    assert fixture.invocations == [PLAINTEXT]


def test_release_boundary_rejects_another_valid_source_signed_packet() -> None:
    fixture = _build_fixture()
    carrier = build_hnc_quantum_packet(
        PLAINTEXT,
        MASTER_KEY,
        purpose=PURPOSE,
        operator_aad={"laboratory": True},
    )
    alternate = fixture.custody.protect_carrier(
        packet_id="alternate-source-signed-packet",
        purpose=PURPOSE,
        release_context_sha256=fixture.packet.release_context_sha256,
        legacy_carrier=carrier,
        legacy_master_key=MASTER_KEY,
    )

    with pytest.raises(
        ReleaseBoundaryError,
        match="protected_packet_release_context_mismatch",
    ):
        fixture.release(packet=alternate)

    assert fixture.invocations == []
    result = fixture.release()
    assert result.result == {"signature_valid": True}
    assert fixture.invocations == [PLAINTEXT]


def test_release_boundary_rejects_channel_binding_change_without_burning_challenge() -> None:
    fixture = _build_fixture()

    with pytest.raises(
        ReleaseBoundaryError,
        match="protected_packet_release_context_mismatch",
    ):
        fixture.release(channel_binding_sha256=_digest("attacker-channel-binding"))

    assert fixture.invocations == []
    result = fixture.release()
    assert result.result == {"signature_valid": True}
    assert fixture.invocations == [PLAINTEXT]


@pytest.mark.parametrize(
    "mutated_now_ms",
    [EXPIRES_MS, NOW_MS - 2_000],
    ids=("advance-past-expiry", "rollback-before-issuance"),
)
def test_release_boundary_resamples_clock_after_verifier_callback(
    mutated_now_ms: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture()
    expectations_probe = fixture.boundary._evidence_expectations_probe

    def mutate_clock_then_probe(
        packet_id: str,
        session_id: str,
    ) -> EvidenceExpectationsV02:
        fixture.clock.now_ms = mutated_now_ms
        return expectations_probe(packet_id, session_id)

    monkeypatch.setattr(
        fixture.boundary,
        "_evidence_expectations_probe",
        mutate_clock_then_probe,
    )

    with pytest.raises(ReleaseBoundaryError, match="epas_time_window_invalid"):
        fixture.release()

    assert fixture.invocations == []
    assert fixture.epas_store.snapshot() == fixture.initial_epas


def test_release_boundary_rejects_external_evidence_substitution_before_custody() -> None:
    fixture = _build_fixture()
    substituted = dict(fixture.probes.expectations.organ_evidence_sha256_by_role)
    substituted["COHERENCE"] = _digest("attacker-substituted-coherence-evidence")
    fixture.probes.expectations = replace(
        fixture.probes.expectations,
        organ_evidence_sha256_by_role=substituted,
    )

    with pytest.raises(ReleaseBoundaryError):
        fixture.release()

    assert fixture.invocations == []
    assert fixture.epas_store.snapshot() == fixture.initial_epas


@pytest.mark.parametrize(
    ("fixture_override", "expected_code"),
    [
        (
            {"heart_source_identity_override": _digest("wrong-heart-source")},
            "release_join_mismatch_source_identity_commitment",
        ),
        (
            {"heart_policy_commitment_override": _digest("wrong-heart-policy")},
            "release_join_mismatch_policy_commitment",
        ),
    ],
)
def test_release_boundary_rejects_v0_heart_source_or_policy_substitution(
    fixture_override: dict[str, str],
    expected_code: str,
) -> None:
    fixture = _build_fixture(**fixture_override)

    with pytest.raises(ReleaseBoundaryError, match=expected_code):
        fixture.release()

    assert fixture.invocations == []
    assert fixture.epas_store.snapshot() == fixture.initial_epas


@pytest.mark.parametrize(
    "field_name",
    ["runtime_measurement_sha256", "policy_measurement_sha256"],
)
def test_release_boundary_rejects_final_live_runtime_or_policy_change(
    field_name: str,
) -> None:
    fixture = _build_fixture()
    fixture.probes.live = replace(
        fixture.probes.live,
        **{field_name: _digest(f"attacker-{field_name}")},
    )

    with pytest.raises(ReleaseBoundaryError, match=f"release_join_mismatch_{field_name}"):
        fixture.release()

    assert fixture.invocations == []
    _assert_denied_with_epas_transition(fixture)


def test_release_boundary_denies_expiry_during_capability_execution() -> None:
    fixture_holder: list[_BoundaryFixture] = []

    def expire_during_execution(_plaintext: bytes) -> Mapping[str, Any]:
        fixture_holder[0].clock.now_ms = EXPIRES_MS
        return {"signature_valid": True}

    fixture = _build_fixture(handler=expire_during_execution)
    fixture_holder.append(fixture)

    with pytest.raises(
        ReleaseBoundaryError,
        match="release_session_expired_during_capability",
    ):
        fixture.release()

    assert fixture.invocations == [PLAINTEXT]
    _assert_denied_with_epas_transition(fixture)


def test_release_boundary_sanitizes_plaintext_bearing_handler_exception() -> None:
    def leaking_exception(plaintext: bytes) -> Mapping[str, Any]:
        raise RuntimeError(f"handler leaked: {plaintext.decode('utf-8')}")

    fixture = _build_fixture(handler=leaking_exception)

    with pytest.raises(ReleaseBoundaryError) as captured:
        fixture.release()

    assert captured.value.code == "capability_execution_failed"
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    rendered = "".join(traceback.format_exception(captured.value))
    assert PLAINTEXT.decode() not in rendered
    assert "handler leaked" not in rendered
    _assert_denied_with_epas_transition(fixture)


def test_release_boundary_receipt_uses_the_expiry_checked_time_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture()
    clock_calls = 0

    def expire_only_on_a_second_post_capability_sample() -> int:
        nonlocal clock_calls
        clock_calls += 1
        return NOW_MS if clock_calls < 12 else EXPIRES_MS

    monkeypatch.setattr(
        fixture.boundary,
        "_trusted_now_ms",
        expire_only_on_a_second_post_capability_sample,
    )

    result = fixture.release()

    assert result.receipt["payload"]["issued_at_ms"] < result.release_state.expires_at_ms
    assert fixture.invocations == [PLAINTEXT]


def test_release_boundary_rejects_recursive_forbidden_capability_output() -> None:
    def nested_secret_output(_plaintext: bytes) -> Mapping[str, Any]:
        return {"signature_valid": {"secret_material": "not-permitted"}}

    fixture = _build_fixture(handler=nested_secret_output)

    with pytest.raises(ReleaseBoundaryError, match="capability_result_schema_denied"):
        fixture.release()

    assert fixture.invocations == [PLAINTEXT]
    _assert_denied_with_epas_transition(fixture)


def test_release_boundary_never_signs_plaintext_encoded_as_integer_vector() -> None:
    fixture = _build_fixture(
        handler=lambda plaintext: {"signature_valid": list(plaintext)}
    )

    with pytest.raises(ReleaseBoundaryError, match="capability_result_schema_denied"):
        fixture.release()

    assert fixture.invocations == [PLAINTEXT]
    _assert_denied_with_epas_transition(fixture)


@pytest.mark.parametrize("signer_fault", ["raises", "corrupt-signature"])
def test_release_boundary_receipt_signer_fault_never_consumes(
    signer_fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture()

    def faulty_sign_component(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("component_type") != "CAPABILITY_RELEASE_RECEIPT":
            return sign_component_v02(**kwargs)
        if signer_fault == "raises":
            raise RuntimeError("injected_receipt_signer_failure")
        receipt = sign_component_v02(**kwargs)
        receipt["signature_hex"] = _flip_hex(str(receipt["signature_hex"]))
        return receipt

    monkeypatch.setattr(
        "aureon.plumber.release_boundary_v02.sign_component_v02",
        faulty_sign_component,
    )

    with pytest.raises(ReleaseBoundaryError):
        fixture.release()

    assert len(fixture.invocations) <= 1
    _assert_denied_with_epas_transition(fixture)


def test_evidence_expectations_defensively_copy_and_freeze_caller_mappings() -> None:
    organ_evidence = {role: _digest(f"freeze-organ-{role}") for role in ORGAN_ROLES}
    point_evidence = {role: _digest(f"freeze-point-{role}") for role in POINT_ROLES}
    expected_organ = dict(organ_evidence)
    expected_points = dict(point_evidence)
    expectations = EvidenceExpectationsV02(
        organ_evidence_sha256_by_role=organ_evidence,
        star_point_evidence_sha256_by_role=point_evidence,
        epas_source_lineage_sha256=_digest("freeze-epas-lineage"),
        epas_evidence_sha256=_digest("freeze-epas-evidence"),
        epas_evidence_class="verified-source",
    )

    organ_evidence["SOURCE"] = _digest("post-construction-organ-tamper")
    organ_evidence["ATTACKER"] = _digest("post-construction-organ-injection")
    point_evidence.clear()

    assert dict(expectations.organ_evidence_sha256_by_role) == expected_organ
    assert dict(expectations.star_point_evidence_sha256_by_role) == expected_points
    with pytest.raises(TypeError):
        setitem(
            expectations.organ_evidence_sha256_by_role,
            "SOURCE",
            _digest("direct-organ-tamper"),
        )
    with pytest.raises(TypeError):
        setitem(
            expectations.star_point_evidence_sha256_by_role,
            "SOURCE",
            _digest("direct-point-tamper"),
        )


def test_release_boundary_revalidates_continuity_at_final_custody_boundary() -> None:
    fixture = _build_fixture()
    original = fixture.probes.continuity_samples[0]
    fixture.probes.continuity_samples = [
        original,
        replace(original, revocation_epoch=original.revocation_epoch + 1),
    ]

    with pytest.raises(ReleaseBoundaryError, match="continuity_state_changed_at_boundary"):
        fixture.release()

    assert fixture.invocations == []
    assert fixture.epas_store.snapshot().epoch == fixture.initial_epas.epoch + 1


def test_release_boundary_rejects_replay_after_one_success() -> None:
    fixture = _build_fixture()
    first = fixture.release()
    first_epas = fixture.epas_store.snapshot()

    with pytest.raises(ReleaseBoundaryError, match="recipient_challenge_replayed"):
        fixture.release()

    assert first.result == {"signature_valid": True}
    assert fixture.invocations == [PLAINTEXT]
    assert fixture.epas_store.snapshot() == first_epas


def test_release_boundary_rejects_star_reuse_in_a_fresh_session() -> None:
    original = _build_fixture(
        packet_id="packet-original-star",
        session_id="session-original-star",
    )
    fresh = _build_fixture(
        packet_id="packet-fresh-star",
        session_id="session-fresh-star",
    )

    with pytest.raises(ReleaseBoundaryError, match="epas_precondition_invalid"):
        fresh.release(star=original.star)

    assert fresh.invocations == []
    assert fresh.epas_store.snapshot() == fresh.initial_epas


def test_release_receipt_verifier_rejects_signature_tamper() -> None:
    fixture = _build_fixture()
    result = fixture.release()
    tampered_receipt = dict(result.receipt)
    tampered_receipt["signature_hex"] = _flip_hex(str(tampered_receipt["signature_hex"]))
    tampered_result = replace(result, receipt=tampered_receipt)

    with pytest.raises(ReleaseBoundaryError, match="signed_component_signature_invalid"):
        validate_capability_release_result_v02(
            tampered_result,
            receipt_authority=fixture.receipt_authority,
        )


def test_release_receipt_verifier_rejects_resigned_non_sha256_packet_commitment() -> None:
    fixture = _build_fixture()
    result = fixture.release()
    payload = dict(result.receipt["payload"])
    payload["packet_commitment"] = "correctly-signed-but-not-a-sha256"
    resigned_receipt = sign_component_v02(
        component_type="CAPABILITY_RELEASE_RECEIPT",
        authority=fixture.receipt_authority,
        payload=payload,
        private_key=_private_key("CAPABILITY_RECEIPT"),
    )
    resigned_result = replace(result, receipt=resigned_receipt)

    with pytest.raises(
        ReleaseBoundaryError,
        match="capability_receipt_packet_commitment_invalid",
    ):
        validate_capability_release_result_v02(
            resigned_result,
            receipt_authority=fixture.receipt_authority,
        )
