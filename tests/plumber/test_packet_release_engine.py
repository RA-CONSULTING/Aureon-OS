from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.harmonic.hnc_quantum_packet_crypto import (
    build_hnc_quantum_packet,
)
from aureon.harmonic.hnc_quantum_packet_crypto import (
    sha256_hex as hnc_sha256_hex,
)
from aureon.plumber.crypto import (
    b64url_decode,
    domain_hash,
    ed25519_public_key_hex,
    generate_ed25519_private_key,
)
from aureon.plumber.enclave import (
    INSECURE_OPT_IN_ACK,
    EnclaveConfigurationError,
    EnclaveDisposition,
    LocalComputationResult,
    LocalDevelopmentEnclave,
)
from aureon.plumber.immune_gate import (
    GateClass,
    GateDecision,
    GateEvidence,
    build_gate_context_commitment,
    evaluate_immune_gate,
)
from aureon.plumber.observer_transcript import ObserverTranscriptV0
from aureon.plumber.packet import (
    PacketCode,
    PacketContractError,
    PacketDisposition,
    PacketInspection,
    PacketReplayGuard,
    PacketTrustPolicy,
    add_packet_signature,
    bind_hnc_packet,
    inspect_plumber_packet,
)
from aureon.plumber.quorum import AuthorityPermit, QuorumPolicyV0
from aureon.plumber.receipts import ReceiptKind, ReceiptVerdict, SignedReceipt
from aureon.plumber.release_engine import (
    LocalReleaseEngine,
    ReleaseCode,
    ReleaseDisposition,
)
from aureon.plumber.schema import PlumberPacketV0, SchemaError
from aureon.plumber.source_identity import SourceIdentityV0, build_source_identity_from_hnc_packet
from aureon.plumber.spore_transport import fragment_ciphertext
from aureon.plumber.sympathetic_identity import SympatheticIdentityV0
from aureon.plumber.temporal_identity import TemporalIdentityV0
from aureon.plumber.twin_rune_seal import TwinRuneSealV0

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
PURPOSE = "aureon.plumber.local-test"
MASTER_KEY = b"m" * 32
DIGESTS = tuple(f"{number:064x}" for number in range(1, 80))
SYNTHETIC_INPUT = b"synthetic-local-input"


@dataclass
class Fixture:
    hnc_packet: dict[str, Any]
    packet: PlumberPacketV0
    observer: ObserverTranscriptV0
    sympathetic: SympatheticIdentityV0
    policy: QuorumPolicyV0
    permits: tuple[AuthorityPermit, ...]
    trust_policy: PacketTrustPolicy
    replay_guard: PacketReplayGuard
    enclave: LocalDevelopmentEnclave
    engine: LocalReleaseEngine
    packet_signer: Ed25519PrivateKey
    receipt_keys: dict[ReceiptKind, Ed25519PrivateKey]


def _receipt(
    kind: ReceiptKind,
    key: Ed25519PrivateKey,
    *,
    source: SourceIdentityV0,
    temporal: TemporalIdentityV0,
    observer: ObserverTranscriptV0,
    policy: QuorumPolicyV0,
) -> SignedReceipt:
    return SignedReceipt.issue(
        kind=kind,
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=observer.purpose_commitment,
        source_identity_commitment=source.identity_commitment,
        temporal_identity_commitment=temporal.temporal_commitment,
        observer_transcript_commitment=observer.transcript_commitment,
        policy_commitment=policy.policy_commitment,
        runtime_measurement_commitment=temporal.runtime_measurement_commitment,
        verdict=ReceiptVerdict.APPROVED,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
        signer_id=f"{kind}-authority",
        private_key=key,
    )


def _fixture() -> Fixture:
    hnc_packet = build_hnc_quantum_packet(
        SYNTHETIC_INPUT,
        MASTER_KEY,
        purpose=PURPOSE,
        nonce=b"plumbernonce",
    )
    binding = bind_hnc_packet(hnc_packet)
    source = build_source_identity_from_hnc_packet(hnc_packet)
    challenge = DIGESTS[5]
    observer = ObserverTranscriptV0.build(
        packet_identity="packet-1",
        session_identity="session-1",
        purpose_commitment=binding.purpose_commitment,
        challenge_commitment=challenge,
        canonical_hnc_values={"coherence": "0.875", "energy": "4"},
        trajectory_commitments=(DIGESTS[6],),
        coherence="0.875",
        consciousness_proxy=None,
        symbolic_life=True,
        hnc_parameters={"lambda": "0.25"},
        rock_commitments=(),
        active_mode="stable",
        active_plateau="plateau-1",
        transition_commitment=DIGESTS[7],
        regime="bounded",
        divergence_score="0.125",
        source_receipt_commitments=(source.provenance_receipt_commitment,),
    )
    temporal = TemporalIdentityV0.build(
        packet_identity="packet-1",
        session_identity="session-1",
        previous_state_commitment=DIGESTS[0],
        nonce_commitment=DIGESTS[1],
        counter=2,
        field_receipt_commitment=DIGESTS[2],
        observer_receipt_commitment=observer.transcript_commitment,
        runtime_measurement_commitment=DIGESTS[4],
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    policy = QuorumPolicyV0.build()
    rune = TwinRuneSealV0.build(
        source_identity_commitment=source.identity_commitment,
        observer_transcript_commitment=observer.transcript_commitment,
        temporal_identity_commitment=temporal.temporal_commitment,
        purpose_commitment=binding.purpose_commitment,
        challenge_commitment=challenge,
    )
    sympathetic = SympatheticIdentityV0.build(
        source_identity_commitment=source.identity_commitment,
        hardware_identity_commitment=DIGESTS[8],
        operator_identity_commitment=DIGESTS[9],
        temporal_identity_commitment=temporal.temporal_commitment,
        observer_identity_commitment=observer.transcript_commitment,
        purpose_commitment=binding.purpose_commitment,
        policy_commitment=policy.policy_commitment,
    )
    receipt_keys = {kind: generate_ed25519_private_key() for kind in ReceiptKind if kind in {
        ReceiptKind.FIELD,
        ReceiptKind.HEART,
        ReceiptKind.CONSCIENCE,
        ReceiptKind.GOVERNANCE,
    }}
    receipts = {
        kind: _receipt(kind, receipt_keys[kind], source=source, temporal=temporal, observer=observer, policy=policy)
        for kind in receipt_keys
    }
    quorum_keys = {role: generate_ed25519_private_key() for role in policy.required_roles}
    permits = tuple(
        AuthorityPermit.issue(
            role=role,
            authority_id=f"{role}-authority",
            packet_identity="packet-1",
            session_identity="session-1",
            purpose_commitment=binding.purpose_commitment,
            policy_commitment=policy.policy_commitment,
            wrapped_share_commitment=DIGESTS[30 + index],
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=10),
            private_key=quorum_keys[role],
        )
        for index, role in enumerate(policy.required_roles)
    )
    ciphertext = b64url_decode(hnc_packet["ciphertext_b64"])
    manifest, _fragments = fragment_ciphertext(
        ciphertext,
        packet_identity="packet-1",
        stream_identity="stream-1",
        temporal_epoch=2,
        route_id="local-route",
        challenge_commitment=challenge,
        expires_at=NOW + timedelta(minutes=10),
        fragment_size=16,
    )
    packet = PlumberPacketV0.build(
        packet_identity="packet-1",
        source_identity=source.to_dict(),
        temporal_identity=temporal.to_dict(),
        requested_purpose=PURPOSE,
        hnc_observer_challenge=challenge,
        canonical_field_receipt=receipts[ReceiptKind.FIELD].to_dict(),
        observer_transcript_commitment=observer.transcript_commitment,
        twin_rune_seal=rune.to_dict(),
        sympathetic_identity_commitment=sympathetic.identity_commitment,
        heart_receipt=receipts[ReceiptKind.HEART].to_dict(),
        conscience_receipt=receipts[ReceiptKind.CONSCIENCE].to_dict(),
        governance_receipt=receipts[ReceiptKind.GOVERNANCE].to_dict(),
        quorum_policy=policy.to_dict(),
        encrypted_payload=binding.to_dict(),
        spore_manifest=manifest.to_dict(),
    )
    packet_signer = generate_ed25519_private_key()
    packet = add_packet_signature(packet, packet_signer)
    trust_policy = PacketTrustPolicy.build(
        packet_signer_public_keys=(ed25519_public_key_hex(packet_signer),),
        receipt_authorities={
            str(kind): {
                "authority_id": f"{kind}-authority",
                "public_key": ed25519_public_key_hex(key),
            }
            for kind, key in receipt_keys.items()
        },
        quorum_authorities={
            role: {
                "authority_id": f"{role}-authority",
                "public_key": ed25519_public_key_hex(key),
            }
            for role, key in quorum_keys.items()
        },
        expected_hardware_identity_commitment=DIGESTS[8],
        expected_operator_identity_commitment=DIGESTS[9],
    )
    replay_guard = PacketReplayGuard()
    assert replay_guard.register_temporal_anchor(
        temporal.session_identity,
        expected_previous_state_commitment=temporal.previous_state_commitment,
        minimum_counter=temporal.counter - 1,
        expected_field_receipt_commitment=temporal.field_receipt_commitment,
        expected_runtime_measurement_commitment=temporal.runtime_measurement_commitment,
    )
    enclave = LocalDevelopmentEnclave(
        allowed_purposes=(PURPOSE,),
        insecure_opt_in=INSECURE_OPT_IN_ACK,
    )
    engine = LocalReleaseEngine(
        trust_policy=trust_policy,
        required_quorum_policy_commitment=policy.policy_commitment,
        replay_guard=replay_guard,
        enclave=enclave,
    )
    return Fixture(
        hnc_packet=hnc_packet,
        packet=packet,
        observer=observer,
        sympathetic=sympathetic,
        policy=policy,
        permits=permits,
        trust_policy=trust_policy,
        replay_guard=replay_guard,
        enclave=enclave,
        engine=engine,
        packet_signer=packet_signer,
        receipt_keys=receipt_keys,
    )


def _approved_gate(fixture: Fixture, inspection: PacketInspection) -> GateDecision:
    return fixture.engine.issue_gate(inspection)


def _replace_packet(fixture: Fixture, **updates: Any) -> PlumberPacketV0:
    values = fixture.packet.to_dict()
    values.pop("packet_commitment")
    values["signatures"] = {}
    values.update(updates)
    return add_packet_signature(PlumberPacketV0.build(**values), fixture.packet_signer)


def test_structural_inspection_holds_without_explicit_pinned_trust() -> None:
    fixture = _fixture()
    inspection = inspect_plumber_packet(
        fixture.packet,
        fixture.hnc_packet,
        now=NOW + timedelta(seconds=1),
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
    )
    assert inspection.disposition is PacketDisposition.HOLD
    assert not inspection.trusted
    assert PacketCode.TRUST_POLICY_REQUIRED in inspection.denial_codes


def test_engine_trusted_inspection_checks_observer_receipts_quorum_and_packet_signer() -> None:
    fixture = _fixture()
    inspection = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert inspection.disposition is PacketDisposition.VALID
    assert inspection.trusted
    assert inspection.quorum_validated

    attacker_key = generate_ed25519_private_key()
    unsigned = fixture.packet.to_dict()
    unsigned.pop("packet_commitment")
    unsigned["signatures"] = {}
    self_signed = add_packet_signature(PlumberPacketV0.build(**unsigned), attacker_key)
    rejected = fixture.engine.inspect_packet(
        self_signed,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert rejected.disposition is PacketDisposition.DENY
    assert PacketCode.PACKET_SIGNER_UNTRUSTED in rejected.denial_codes


def test_hostile_unpinned_receipt_quorum_and_observer_are_denied() -> None:
    fixture = _fixture()
    old = SignedReceipt.from_dict(fixture.packet.heart_receipt)
    hostile_receipt = SignedReceipt.issue(
        kind=ReceiptKind.HEART,
        packet_identity=old.packet_identity,
        session_identity=old.session_identity,
        purpose_commitment=old.purpose_commitment,
        source_identity_commitment=old.source_identity_commitment,
        temporal_identity_commitment=old.temporal_identity_commitment,
        observer_transcript_commitment=old.observer_transcript_commitment,
        policy_commitment=old.policy_commitment,
        runtime_measurement_commitment=old.runtime_measurement_commitment,
        verdict=ReceiptVerdict.APPROVED,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
        signer_id=old.signer_id,
        private_key=generate_ed25519_private_key(),
    )
    receipt_packet = _replace_packet(fixture, heart_receipt=hostile_receipt.to_dict())
    receipt_result = fixture.engine.inspect_packet(
        receipt_packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert PacketCode.RECEIPT_SIGNER_UNTRUSTED in receipt_result.denial_codes

    replaced = fixture.permits[0]
    hostile_permit = AuthorityPermit.issue(
        role=replaced.role,
        authority_id=replaced.authority_id,
        packet_identity=replaced.packet_identity,
        session_identity=replaced.session_identity,
        purpose_commitment=replaced.purpose_commitment,
        policy_commitment=replaced.policy_commitment,
        wrapped_share_commitment=replaced.wrapped_share_commitment,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
        private_key=generate_ed25519_private_key(),
    )
    quorum_result = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=(hostile_permit, *fixture.permits[1:]),
        now=NOW + timedelta(seconds=1),
    )
    assert PacketCode.QUORUM_AUTHORITY_UNTRUSTED in quorum_result.denial_codes

    observer_values = fixture.observer.to_dict()
    observer_values["challenge_commitment"] = DIGESTS[70]
    observer_values.pop("schema")
    observer_values.pop("transcript_commitment")
    hostile_observer = ObserverTranscriptV0.build(**observer_values)
    observer_result = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=hostile_observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert PacketCode.OBSERVER_TRANSCRIPT_INVALID in observer_result.denial_codes


def test_trusted_inspection_requires_sympathetic_identity_and_temporal_anchor() -> None:
    fixture = _fixture()
    missing_sympathetic = inspect_plumber_packet(
        fixture.packet,
        fixture.hnc_packet,
        now=NOW + timedelta(seconds=1),
        observer_transcript=fixture.observer,
        quorum_permits=fixture.permits,
        trust_policy=fixture.trust_policy,
        required_quorum_policy_commitment=fixture.policy.policy_commitment,
        replay_guard=fixture.replay_guard,
    )
    assert missing_sympathetic.disposition is PacketDisposition.DENY
    assert PacketCode.SYMPATHETIC_IDENTITY_INVALID in missing_sympathetic.denial_codes

    no_anchor = inspect_plumber_packet(
        fixture.packet,
        fixture.hnc_packet,
        now=NOW + timedelta(seconds=1),
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        trust_policy=fixture.trust_policy,
        required_quorum_policy_commitment=fixture.policy.policy_commitment,
        replay_guard=PacketReplayGuard(),
    )
    assert no_anchor.disposition is PacketDisposition.DENY
    assert PacketCode.TEMPORAL_ANCHOR_REQUIRED in no_anchor.denial_codes

    temporal = TemporalIdentityV0.from_dict(fixture.packet.temporal_identity)
    wrong_anchor = PacketReplayGuard()
    assert wrong_anchor.register_temporal_anchor(
        temporal.session_identity,
        expected_previous_state_commitment=temporal.previous_state_commitment,
        minimum_counter=temporal.counter - 1,
        expected_field_receipt_commitment=DIGESTS[70],
        expected_runtime_measurement_commitment=temporal.runtime_measurement_commitment,
    )
    anchor_mismatch = inspect_plumber_packet(
        fixture.packet,
        fixture.hnc_packet,
        now=NOW + timedelta(seconds=1),
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        trust_policy=fixture.trust_policy,
        required_quorum_policy_commitment=fixture.policy.policy_commitment,
        replay_guard=wrong_anchor,
    )
    assert anchor_mismatch.disposition is PacketDisposition.DENY
    assert PacketCode.TEMPORAL_BINDING_INVALID in anchor_mismatch.denial_codes


@pytest.mark.parametrize(
    "updates",
    (
        {"packet_identity": "wrong-packet"},
        {"temporal_epoch": 999},
        {"challenge_commitment": "0" * 64},
        {"ciphertext_size": 1},
    ),
)
def test_spore_manifest_context_is_exactly_bound(updates: dict[str, Any]) -> None:
    fixture = _fixture()
    manifest = dict(fixture.packet.spore_manifest)
    manifest.update(updates)
    manifest["manifest_commitment"] = domain_hash(
        "aureon.plumber.spore-manifest.v0",
        {key: value for key, value in manifest.items() if key != "manifest_commitment"},
    )
    packet = _replace_packet(fixture, spore_manifest=manifest)
    inspection = fixture.engine.inspect_packet(
        packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert inspection.disposition is PacketDisposition.DENY
    assert PacketCode.SPORE_BINDING_INVALID in inspection.denial_codes


def test_rewrapped_temporal_identity_cannot_reserve_twice() -> None:
    fixture = _fixture()
    first = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert first.disposition is PacketDisposition.VALID

    manifest = dict(fixture.packet.spore_manifest)
    manifest["stream_identity"] = "rewrapped-stream"
    manifest["manifest_commitment"] = domain_hash(
        "aureon.plumber.spore-manifest.v0",
        {key: value for key, value in manifest.items() if key != "manifest_commitment"},
    )
    rewrapped = _replace_packet(fixture, spore_manifest=manifest)
    second = fixture.engine.inspect_packet(
        rewrapped,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert second.disposition is PacketDisposition.DENY
    assert PacketCode.REPLAY_DETECTED in second.denial_codes


def test_sympathetic_hardware_and_operator_are_pinned() -> None:
    fixture = _fixture()
    hostile = SympatheticIdentityV0.build(
        source_identity_commitment=fixture.sympathetic.source_identity_commitment,
        hardware_identity_commitment=DIGESTS[70],
        operator_identity_commitment=fixture.sympathetic.operator_identity_commitment,
        temporal_identity_commitment=fixture.sympathetic.temporal_identity_commitment,
        observer_identity_commitment=fixture.sympathetic.observer_identity_commitment,
        purpose_commitment=fixture.sympathetic.purpose_commitment,
        policy_commitment=fixture.sympathetic.policy_commitment,
    )
    packet = _replace_packet(
        fixture,
        sympathetic_identity_commitment=hostile.identity_commitment,
    )
    inspection = fixture.engine.inspect_packet(
        packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=hostile,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert inspection.disposition is PacketDisposition.DENY
    assert PacketCode.SYMPATHETIC_IDENTITY_INVALID in inspection.denial_codes


@pytest.mark.parametrize("duplicate_field", ("authority_id", "public_key"))
def test_receipt_authority_keys_and_ids_must_be_distinct(
    duplicate_field: str,
) -> None:
    fixture = _fixture()
    receipt_kinds = (
        ReceiptKind.FIELD,
        ReceiptKind.HEART,
        ReceiptKind.CONSCIENCE,
        ReceiptKind.GOVERNANCE,
    )
    distinct_public_keys = [
        ed25519_public_key_hex(generate_ed25519_private_key())
        for _kind in receipt_kinds
    ]
    shared_public_key = distinct_public_keys[0]
    with pytest.raises(SchemaError):
        PacketTrustPolicy.build(
            packet_signer_public_keys=(ed25519_public_key_hex(fixture.packet_signer),),
            receipt_authorities={
                str(kind): {
                    "authority_id": (
                        "shared-authority"
                        if duplicate_field == "authority_id"
                        else f"authority-{kind}"
                    ),
                    "public_key": (
                        shared_public_key
                        if duplicate_field == "public_key"
                        else distinct_public_keys[index]
                    ),
                }
                for index, kind in enumerate(receipt_kinds)
            },
            quorum_authorities={
                permit.role: {
                    "authority_id": permit.authority_id,
                    "public_key": permit.signer_public_key,
                }
                for permit in fixture.permits
            },
            expected_hardware_identity_commitment=DIGESTS[8],
            expected_operator_identity_commitment=DIGESTS[9],
        )


def test_every_receipt_runtime_must_match_trusted_temporal_runtime() -> None:
    fixture = _fixture()
    old = SignedReceipt.from_dict(fixture.packet.heart_receipt)
    mismatched = SignedReceipt.issue(
        kind=ReceiptKind.HEART,
        packet_identity=old.packet_identity,
        session_identity=old.session_identity,
        purpose_commitment=old.purpose_commitment,
        source_identity_commitment=old.source_identity_commitment,
        temporal_identity_commitment=old.temporal_identity_commitment,
        observer_transcript_commitment=old.observer_transcript_commitment,
        policy_commitment=old.policy_commitment,
        runtime_measurement_commitment=DIGESTS[70],
        verdict=ReceiptVerdict.APPROVED,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
        signer_id=old.signer_id,
        private_key=fixture.receipt_keys[ReceiptKind.HEART],
    )
    packet = _replace_packet(fixture, heart_receipt=mismatched.to_dict())
    inspection = fixture.engine.inspect_packet(
        packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert inspection.disposition is PacketDisposition.DENY
    assert PacketCode.RECEIPT_INVALID in inspection.denial_codes


def test_hnc_binding_rejects_malformed_or_wrong_length_nonce() -> None:
    fixture = _fixture()
    for nonce in ("!!!!", "AAAA"):
        malformed = copy.deepcopy(fixture.hnc_packet)
        malformed["nonce_b64"] = nonce
        unsigned = dict(malformed)
        unsigned.pop("packet_sha256")
        malformed["packet_sha256"] = hnc_sha256_hex(unsigned)
        with pytest.raises(PacketContractError):
            bind_hnc_packet(malformed)


def test_inspection_commits_exact_gate_evidence_and_window() -> None:
    fixture = _fixture()
    inspection = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert inspection.disposition is PacketDisposition.VALID
    assert set(inspection.gate_evidence_commitments) == {str(item) for item in GateClass}
    assert inspection.gate_evidence_commitments[str(GateClass.IDENTITY)] == (
        fixture.sympathetic.identity_commitment
    )
    assert inspection.gate_evidence_commitments[str(GateClass.TEMPORAL)] == (
        fixture.packet.temporal_identity["temporal_commitment"]
    )
    assert inspection.inspected_at == "2026-08-31T12:00:01Z"
    assert inspection.evidence_not_before == "2026-08-31T12:00:00Z"
    assert inspection.evidence_expires_at == "2026-08-31T12:10:00Z"


def test_local_enclave_requires_opt_in_and_never_returns_raw_material() -> None:
    fixture = _fixture()
    with pytest.raises(EnclaveConfigurationError, match="insecure_opt_in_required"):
        LocalDevelopmentEnclave(allowed_purposes=(PURPOSE,), insecure_opt_in="no")
    assert not any(name == "decrypt" for name in dir(LocalDevelopmentEnclave))

    called = False

    def processor(_view: memoryview) -> LocalComputationResult:
        nonlocal called
        called = True
        return LocalComputationResult(
            outcome_code="synthetic_ok",
            result_commitment=DIGESTS[71],
            evidence_commitments={},
        )

    denied = fixture.enclave.execute_hnc_packet(
        fixture.hnc_packet,
        master_key=MASTER_KEY,
        expected_purpose="different-purpose",
        processor_id="synthetic_processor",
        processor=processor,
        now=NOW + timedelta(seconds=1),
    )
    assert denied.disposition is EnclaveDisposition.DENY
    assert not called
    rendered = repr(denied.public_summary())
    assert SYNTHETIC_INPUT.decode() not in rendered
    assert "master_key" not in rendered


def test_release_engine_is_one_shot_and_replay_is_denied() -> None:
    fixture = _fixture()
    inspection = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    gate = _approved_gate(fixture, inspection)
    assert fixture.engine.evaluate(inspection, gate).disposition is ReleaseDisposition.ALLOW_LOCAL_DEVELOPMENT
    calls = 0

    def processor(view: memoryview) -> LocalComputationResult:
        nonlocal calls
        calls += 1
        return LocalComputationResult(
            outcome_code="synthetic_ok",
            result_commitment=domain_hash("test.local-result", {"size": len(view)}),
            evidence_commitments={"processor": DIGESTS[72]},
        )

    execution, enclave_receipt = fixture.engine.execute(
        inspection,
        gate,
        fixture.hnc_packet,
        master_key=MASTER_KEY,
        expected_purpose=PURPOSE,
        processor_id="synthetic_processor",
        processor=processor,
        now=NOW + timedelta(seconds=2),
    )
    assert execution.disposition is ReleaseDisposition.COMPLETED_LOCAL
    assert not execution.production_release
    assert enclave_receipt is not None
    assert calls == 1

    repeated, repeated_enclave = fixture.engine.execute(
        inspection,
        gate,
        fixture.hnc_packet,
        master_key=MASTER_KEY,
        expected_purpose=PURPOSE,
        processor_id="synthetic_processor",
        processor=processor,
        now=NOW + timedelta(seconds=3),
    )
    assert repeated.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.INSPECTION_NOT_ISSUED in repeated.denial_codes
    assert repeated_enclave is None
    assert calls == 1

    replay = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=4),
    )
    assert replay.disposition is PacketDisposition.DENY
    assert PacketCode.REPLAY_DETECTED in replay.denial_codes


def test_release_engine_denies_gate_not_bound_to_inspection_evidence() -> None:
    fixture = _fixture()
    inspection = fixture.engine.inspect_packet(
        fixture.packet,
        fixture.hnc_packet,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    evidence = tuple(
        GateEvidence(
            gate_class=gate_class,
            receipt_commitment=DIGESTS[40 + index],
            valid=True,
            context_commitment=build_gate_context_commitment(
                packet_identity=inspection.packet_identity,
                session_identity=inspection.session_identity,
                purpose_commitment=inspection.purpose_commitment,
            ),
        )
        for index, gate_class in enumerate(GateClass)
    )
    held = fixture.engine.evaluate(
        inspection,
        evaluate_immune_gate(
            evidence[:-1],
            packet_inspection_commitment=inspection.inspection_commitment,
            evaluated_at=NOW + timedelta(seconds=1),
            expires_at=NOW + timedelta(minutes=10),
        ),
    )
    assert held.disposition is ReleaseDisposition.DENY
    assert ReleaseCode.IMMUNE_GATE_BINDING_MISMATCH in held.denial_codes


def test_hnc_tamper_is_denied_without_decoder_details() -> None:
    fixture = _fixture()
    tampered = copy.deepcopy(fixture.hnc_packet)
    tampered["packet_sha256"] = "0" * 64
    inspection = fixture.engine.inspect_packet(
        fixture.packet,
        tampered,
        observer_transcript=fixture.observer,
        sympathetic_identity=fixture.sympathetic,
        quorum_permits=fixture.permits,
        now=NOW + timedelta(seconds=1),
    )
    assert inspection.disposition is PacketDisposition.DENY
    assert PacketCode.HNC_CONTRACT_INVALID in inspection.denial_codes
    assert "plaintext" not in repr(inspection.public_summary())
