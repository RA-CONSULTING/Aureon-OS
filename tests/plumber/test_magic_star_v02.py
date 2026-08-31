from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.plumber.crypto import domain_hash, ed25519_public_key_hex
from aureon.plumber.magic_star_v02 import (
    POINTS,
    STAR_AUTHORITY_ROLES,
    AuthorityBindingV02,
    MagicStarError,
    MagicStarV02,
    assemble_magic_star_v02,
    build_authority_binding_v02,
    build_candidate_center_v02,
    build_epas_precondition_v02,
    build_heart_precondition_v02,
    build_magic_star_point_v02,
    component_commitment_v02,
    heart_receipt_commitment_v02,
    sign_component_v02,
    validate_magic_star_v02,
)
from aureon.plumber.receipts import ReceiptKind, ReceiptVerdict, SignedReceipt
from aureon.plumber.recipient_proof_v02 import (
    RecipientEnrollmentV02,
    RecipientProofError,
    RecipientProofVerifierV02,
    build_recipient_challenge_v02,
    build_recipient_proof_v02,
    verify_recipient_proof_v02,
)
from aureon.plumber.schema import thaw_json

NOW_MS = 1_900_000_000_000
EXPIRES_MS = NOW_MS + 60_000
PURPOSE = "verify_document_signature"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _private_key(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(f"private:{label}".encode()).digest()
    )


def _datetime_from_ms(value: int) -> datetime:
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)


def _binding(role: str, key: Ed25519PrivateKey) -> AuthorityBindingV02:
    slug = role.lower().replace("_", "-")
    return build_authority_binding_v02(
        role=role,
        issuer=f"issuer-{slug}",
        principal=f"principal-{slug}",
        key_id=f"key-{slug}",
        private_key=key,
    )


@dataclass(frozen=True)
class _StarFixture:
    star: MagicStarV02
    trust: dict[str, AuthorityBindingV02]
    keys: dict[str, Ed25519PrivateKey]
    context: str
    center: str
    packet_id: str
    packet_commitment: str
    heart_receipt: SignedReceipt
    temporal_commitment: str
    observer_commitment: str
    runtime_measurement_sha256: str
    source_identity_commitment: str
    policy_commitment: str


def _build_star() -> _StarFixture:
    keys = {role: _private_key(role) for role in STAR_AUTHORITY_ROLES}
    trust = {role: _binding(role, keys[role]) for role in STAR_AUTHORITY_ROLES}
    context = _digest("release-context")
    packet_id = "packet-v02"
    packet = _digest("packet")
    recipient = _digest("recipient-proof")
    temporal = _digest("temporal")
    observer = _digest("observer")
    runtime = _digest("runtime")
    source_identity = _digest("heart-source-identity")
    policy = _digest("heart-policy")
    epas = build_epas_precondition_v02(
        release_context_sha256=context,
        source_lineage_sha256=_digest("source-lineage"),
        evidence_sha256=_digest("epas-evidence"),
        evidence_class="verified-source",
        previous_memory_head_sha256=_digest("previous-memory"),
        memory_epoch=7,
        verdict="CLEAR",
        outcome="PROCEED",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=trust["EPAS"],
        private_key=keys["EPAS"],
    )
    heart_receipt = SignedReceipt.issue(
        kind=ReceiptKind.HEART,
        packet_identity=packet_id,
        session_identity="session-v02",
        purpose_commitment=domain_hash("aureon.plumber.purpose.v0", PURPOSE),
        source_identity_commitment=source_identity,
        temporal_identity_commitment=temporal,
        observer_transcript_commitment=observer,
        policy_commitment=policy,
        runtime_measurement_commitment=runtime,
        verdict=ReceiptVerdict.APPROVED,
        issued_at=_datetime_from_ms(NOW_MS - 1_000),
        expires_at=_datetime_from_ms(EXPIRES_MS),
        signer_id=trust["HEART"].principal,
        private_key=keys["HEART"],
    )
    heart = build_heart_precondition_v02(
        release_context_sha256=context,
        packet_id=packet_id,
        packet_commitment=packet,
        session_id="session-v02",
        purpose=PURPOSE,
        temporal_commitment=temporal,
        observer_commitment=observer,
        runtime_measurement_sha256=runtime,
        heart_receipt=heart_receipt,
        verdict="APPROVE",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=trust["HEART"],
        private_key=keys["HEART"],
    )
    center = build_candidate_center_v02(
        release_context_sha256=context,
        packet_commitment=packet,
        recipient_proof_commitment=recipient,
        purpose=PURPOSE,
        temporal_commitment=temporal,
        observer_commitment=observer,
        epas_commitment=component_commitment_v02(epas),
        heart_commitment=component_commitment_v02(heart),
    )
    points = [
        build_magic_star_point_v02(
            index=index,
            release_context_sha256=context,
            candidate_center_sha256=center,
            evidence_sha256=_digest(f"point-evidence-{index}"),
            share_binding_sha256=_digest(f"share-binding-{index}"),
            verdict="APPROVE",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=trust[definition["role"]],
            private_key=keys[definition["role"]],
        )
        for index, definition in enumerate(POINTS)
    ]
    star = assemble_magic_star_v02(
        release_context_sha256=context,
        candidate_center_sha256=center,
        epas_precondition=epas,
        heart_precondition=heart,
        points=points,
        trust=trust,
        seal_authority=trust["STAR_SEAL"],
        seal_private_key=keys["STAR_SEAL"],
        trusted_now_ms=lambda: NOW_MS,
    )
    return _StarFixture(
        star=star,
        trust=trust,
        keys=keys,
        context=context,
        center=center,
        packet_id=packet_id,
        packet_commitment=packet,
        heart_receipt=heart_receipt,
        temporal_commitment=temporal,
        observer_commitment=observer,
        runtime_measurement_sha256=runtime,
        source_identity_commitment=source_identity,
        policy_commitment=policy,
    )


def _validate(fixture: _StarFixture, star: MagicStarV02 | None = None) -> dict[str, object]:
    return validate_magic_star_v02(
        star or fixture.star,
        trust=fixture.trust,
        expected_release_context_sha256=fixture.context,
        expected_candidate_center_sha256=fixture.center,
        trusted_now_ms=lambda: NOW_MS,
    )


def _issue_receipt(
    fixture: _StarFixture,
    *,
    kind: ReceiptKind = ReceiptKind.HEART,
    packet_identity: str | None = None,
    session_identity: str = "session-v02",
    purpose_commitment: str | None = None,
    source_identity_commitment: str | None = None,
    temporal_identity_commitment: str | None = None,
    observer_transcript_commitment: str | None = None,
    policy_commitment: str | None = None,
    runtime_measurement_commitment: str | None = None,
    issued_at_ms: int = NOW_MS - 1_000,
    expires_at_ms: int = EXPIRES_MS,
    signer_id: str | None = None,
    private_key: Ed25519PrivateKey | None = None,
) -> SignedReceipt:
    return SignedReceipt.issue(
        kind=kind,
        packet_identity=packet_identity or fixture.packet_id,
        session_identity=session_identity,
        purpose_commitment=purpose_commitment
        or domain_hash("aureon.plumber.purpose.v0", PURPOSE),
        source_identity_commitment=source_identity_commitment
        or fixture.source_identity_commitment,
        temporal_identity_commitment=temporal_identity_commitment
        or fixture.temporal_commitment,
        observer_transcript_commitment=observer_transcript_commitment
        or fixture.observer_commitment,
        policy_commitment=policy_commitment or fixture.policy_commitment,
        runtime_measurement_commitment=runtime_measurement_commitment
        or fixture.runtime_measurement_sha256,
        verdict=ReceiptVerdict.APPROVED,
        issued_at=_datetime_from_ms(issued_at_ms),
        expires_at=_datetime_from_ms(expires_at_ms),
        signer_id=signer_id or fixture.trust["HEART"].principal,
        private_key=private_key or fixture.keys["HEART"],
    )


def _build_heart_bridge(
    fixture: _StarFixture,
    receipt: SignedReceipt,
    *,
    issued_at_ms: int = NOW_MS - 1_000,
    expires_at_ms: int = EXPIRES_MS,
) -> dict[str, object]:
    return build_heart_precondition_v02(
        release_context_sha256=fixture.context,
        packet_id=fixture.packet_id,
        packet_commitment=fixture.packet_commitment,
        session_id="session-v02",
        purpose=PURPOSE,
        temporal_commitment=fixture.temporal_commitment,
        observer_commitment=fixture.observer_commitment,
        runtime_measurement_sha256=fixture.runtime_measurement_sha256,
        heart_receipt=receipt,
        verdict="APPROVE",
        issued_at_ms=issued_at_ms,
        expires_at_ms=expires_at_ms,
        authority=fixture.trust["HEART"],
        private_key=fixture.keys["HEART"],
    )


def _flip_hex(value: str) -> str:
    return f"{value[:-1]}{'0' if value[-1] != '0' else '1'}"


def test_magic_star_happy_path_is_five_point_and_lab_only() -> None:
    fixture = _build_star()

    result = _validate(fixture)

    assert result["valid"] is True
    assert result["point_count"] == 5
    assert result["production_ready"] is False
    assert result["star_commitment"] == fixture.star.commitment
    assert result["heart_receipt_commitment"] == heart_receipt_commitment_v02(
        fixture.heart_receipt
    )


def test_magic_star_rejects_tampered_embedded_v0_heart_receipt() -> None:
    fixture = _build_star()
    heart_payload = thaw_json(fixture.star.heart_precondition["payload"])
    receipt_value = dict(heart_payload["heart_receipt"])
    receipt_value["signature"] = _flip_hex(receipt_value["signature"])
    tampered_receipt = SignedReceipt.from_dict(receipt_value)
    heart_payload["heart_receipt"] = tampered_receipt.to_dict()
    heart_payload["heart_receipt_commitment"] = heart_receipt_commitment_v02(
        tampered_receipt
    )
    resigned = sign_component_v02(
        component_type="HEART_PRECONDITION",
        authority=fixture.trust["HEART"],
        payload=heart_payload,
        private_key=fixture.keys["HEART"],
    )

    with pytest.raises(MagicStarError, match="heart_receipt_validation_failed"):
        _validate(fixture, replace(fixture.star, heart_precondition=resigned))


def test_heart_bridge_rejects_wrong_v0_receipt_kind() -> None:
    fixture = _build_star()
    receipt = _issue_receipt(fixture, kind=ReceiptKind.CONSCIENCE)

    with pytest.raises(MagicStarError, match="heart_receipt_kind_invalid"):
        _build_heart_bridge(fixture, receipt)


@pytest.mark.parametrize("wrong_identity", ["key", "principal"])
def test_heart_bridge_rejects_wrong_receipt_signer_or_principal(
    wrong_identity: str,
) -> None:
    fixture = _build_star()
    receipt = _issue_receipt(
        fixture,
        private_key=(
            _private_key("alternate-heart-receipt")
            if wrong_identity == "key"
            else fixture.keys["HEART"]
        ),
        signer_id=(
            "alternate-heart-principal"
            if wrong_identity == "principal"
            else fixture.trust["HEART"].principal
        ),
    )

    with pytest.raises(MagicStarError, match="heart_receipt_authority_mismatch"):
        _build_heart_bridge(fixture, receipt)


@pytest.mark.parametrize(
    ("receipt_field", "wrong_value"),
    [
        ("packet_identity", "different-packet"),
        ("session_identity", "different-session"),
        ("purpose_commitment", _digest("different-purpose")),
        ("temporal_identity_commitment", _digest("different-temporal")),
        ("observer_transcript_commitment", _digest("different-observer")),
        ("runtime_measurement_commitment", _digest("different-runtime")),
    ],
)
def test_heart_bridge_rejects_receipt_binding_mismatch(
    receipt_field: str,
    wrong_value: str,
) -> None:
    fixture = _build_star()
    receipt = _issue_receipt(fixture, **{receipt_field: wrong_value})

    with pytest.raises(MagicStarError, match="heart_receipt_binding_mismatch"):
        _build_heart_bridge(fixture, receipt)


@pytest.mark.parametrize(
    ("issued_at_ms", "expires_at_ms"),
    [
        (NOW_MS, EXPIRES_MS),
        (NOW_MS - 1_000, EXPIRES_MS - 1_000),
    ],
)
def test_heart_bridge_rejects_inner_outer_time_mismatch(
    issued_at_ms: int,
    expires_at_ms: int,
) -> None:
    fixture = _build_star()

    with pytest.raises(MagicStarError, match="heart_receipt_time_join_mismatch"):
        _build_heart_bridge(
            fixture,
            fixture.heart_receipt,
            issued_at_ms=issued_at_ms,
            expires_at_ms=expires_at_ms,
        )


def test_magic_star_public_serialization_contains_no_private_material_or_plaintext() -> None:
    fixture = _build_star()
    public = fixture.star.public_dict()
    rendered = json.dumps(public, sort_keys=True)

    assert public["profile"]["production_ready"] is False
    assert "protected-plaintext-canary" not in rendered
    for forbidden_key in (
        "private_key",
        "private_key_hex",
        "root_key",
        "session_key",
        "share_bytes",
        "share_hex",
        "plaintext",
    ):
        assert f'"{forbidden_key}"' not in rendered
    for role in STAR_AUTHORITY_ROLES:
        assert hashlib.sha256(f"private:{role}".encode()).hexdigest() not in rendered


@pytest.mark.parametrize("attribute", ["issuer", "principal", "public_key_hex"])
def test_magic_star_rejects_wrong_authority_identity(attribute: str) -> None:
    fixture = _build_star()
    original = fixture.trust["SOURCE"]
    replacement_value = {
        "issuer": "issuer-untrusted-source",
        "principal": "principal-untrusted-source",
        "public_key_hex": ed25519_public_key_hex(_private_key("wrong-source-key")),
    }[attribute]
    bad_trust = {
        **fixture.trust,
        "SOURCE": replace(original, **{attribute: replacement_value}),
    }

    with pytest.raises(MagicStarError, match="signed_component_authority_mismatch"):
        validate_magic_star_v02(
            fixture.star,
            trust=bad_trust,
            expected_release_context_sha256=fixture.context,
            expected_candidate_center_sha256=fixture.center,
            trusted_now_ms=lambda: NOW_MS,
        )


def test_magic_star_rejects_duplicate_authority_key() -> None:
    fixture = _build_star()
    bad_trust = {
        **fixture.trust,
        "OBSERVER": replace(
            fixture.trust["OBSERVER"],
            public_key_hex=fixture.trust["SOURCE"].public_key_hex,
        ),
    }

    with pytest.raises(MagicStarError, match="authority_keys_not_distinct"):
        validate_magic_star_v02(
            fixture.star,
            trust=bad_trust,
            expected_release_context_sha256=fixture.context,
            expected_candidate_center_sha256=fixture.center,
            trusted_now_ms=lambda: NOW_MS,
        )


def test_magic_star_component_builder_rejects_wrong_private_key() -> None:
    fixture = _build_star()

    with pytest.raises(MagicStarError, match="component_signer_key_mismatch"):
        build_magic_star_point_v02(
            index=0,
            release_context_sha256=fixture.context,
            candidate_center_sha256=fixture.center,
            evidence_sha256=_digest("wrong-key-evidence"),
            share_binding_sha256=_digest("wrong-key-share"),
            verdict="APPROVE",
            issued_at_ms=NOW_MS,
            expires_at_ms=EXPIRES_MS,
            authority=fixture.trust["SOURCE"],
            private_key=_private_key("not-source"),
        )


def test_magic_star_rejects_expired_preconditions() -> None:
    fixture = _build_star()

    with pytest.raises(MagicStarError, match="epas_time_window_invalid"):
        validate_magic_star_v02(
            fixture.star,
            trust=fixture.trust,
            expected_release_context_sha256=fixture.context,
            expected_candidate_center_sha256=fixture.center,
            trusted_now_ms=lambda: EXPIRES_MS,
        )


def test_magic_star_rejects_resigned_point_definition_tamper() -> None:
    fixture = _build_star()
    component = fixture.star.points[0]
    payload = dict(component["payload"])
    payload["lens"] = "TamperedLens"
    tampered_point = sign_component_v02(
        component_type="MAGIC_STAR_POINT",
        authority=fixture.trust["SOURCE"],
        payload=payload,
        private_key=fixture.keys["SOURCE"],
    )
    points = list(fixture.star.points)
    points[0] = tampered_point

    with pytest.raises(MagicStarError, match="star_point_definition_mismatch"):
        _validate(fixture, replace(fixture.star, points=tuple(points)))


def test_magic_star_assembler_rejects_signed_point_veto() -> None:
    fixture = _build_star()
    payload = thaw_json(fixture.star.points[0]["payload"])
    payload["verdict"] = "VETO"
    vetoed_point = sign_component_v02(
        component_type="MAGIC_STAR_POINT",
        authority=fixture.trust["SOURCE"],
        payload=payload,
        private_key=fixture.keys["SOURCE"],
    )
    points = list(fixture.star.points)
    points[0] = vetoed_point

    with pytest.raises(MagicStarError, match="star_point_denied"):
        assemble_magic_star_v02(
            release_context_sha256=fixture.context,
            candidate_center_sha256=fixture.center,
            epas_precondition=fixture.star.epas_precondition,
            heart_precondition=fixture.star.heart_precondition,
            points=points,
            trust=fixture.trust,
            seal_authority=fixture.trust["STAR_SEAL"],
            seal_private_key=fixture.keys["STAR_SEAL"],
            trusted_now_ms=lambda: NOW_MS,
        )


@pytest.mark.parametrize("target", ["route", "rainbow"])
def test_magic_star_rejects_resigned_route_or_rainbow_tamper(target: str) -> None:
    fixture = _build_star()
    payload = thaw_json(fixture.star.seal["payload"])
    if target == "route":
        payload["edges"][0]["to"] = 3
    else:
        payload["rainbow_chain"]["rungs"][0]["frequency_hz"] = "999"
    seal = sign_component_v02(
        component_type="MAGIC_STAR_SEAL",
        authority=fixture.trust["STAR_SEAL"],
        payload=payload,
        private_key=fixture.keys["STAR_SEAL"],
    )

    with pytest.raises(MagicStarError, match="magic_star_seal_join_mismatch"):
        _validate(fixture, replace(fixture.star, seal=seal))


def test_magic_star_rejects_seal_signature_tamper() -> None:
    fixture = _build_star()
    seal = dict(fixture.star.seal)
    seal["signature_hex"] = _flip_hex(seal["signature_hex"])

    with pytest.raises(MagicStarError, match="signed_component_signature_invalid"):
        _validate(fixture, replace(fixture.star, seal=seal))


def _recipient_enrollment(
    private_key: Ed25519PrivateKey,
    *,
    principal: str = "recipient-principal",
) -> RecipientEnrollmentV02:
    return RecipientEnrollmentV02(
        recipient_id="recipient-v02",
        principal=principal,
        key_id="recipient-key-v02",
        public_key_hex=ed25519_public_key_hex(private_key),
        allowed_channel_bindings=(_digest("channel-binding"),),
        allowed_purposes=(PURPOSE,),
    )


def test_recipient_challenge_rejects_wrong_key_and_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "aureon.plumber.recipient_proof_v02.secrets.token_bytes",
        lambda size: bytes([size]) * size,
    )
    recipient_key = _private_key("recipient")
    enrollment = _recipient_enrollment(recipient_key)
    challenge = build_recipient_challenge_v02(
        session_id="session-v02",
        packet_commitment=_digest("packet"),
        purpose=PURPOSE,
        channel_binding_sha256=_digest("channel-binding"),
        trusted_now_ms=lambda: NOW_MS,
    )

    with pytest.raises(RecipientProofError, match="recipient_private_key_not_enrolled"):
        build_recipient_proof_v02(
            challenge,
            enrollment=enrollment,
            private_key=_private_key("wrong-recipient"),
            trusted_now_ms=lambda: NOW_MS + 1,
        )

    proof = build_recipient_proof_v02(
        challenge,
        enrollment=enrollment,
        private_key=recipient_key,
        trusted_now_ms=lambda: NOW_MS + 1,
    )
    with pytest.raises(RecipientProofError, match="recipient_enrollment_mismatch"):
        verify_recipient_proof_v02(
            proof,
            challenge,
            enrollment=_recipient_enrollment(recipient_key, principal="wrong-principal"),
            expected_packet_commitment=_digest("packet"),
            expected_purpose=PURPOSE,
            expected_channel_binding_sha256=_digest("channel-binding"),
            trusted_now_ms=lambda: NOW_MS + 2,
        )


def test_recipient_challenge_is_one_use_and_rejects_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "aureon.plumber.recipient_proof_v02.secrets.token_bytes",
        lambda size: bytes([size]) * size,
    )
    recipient_key = _private_key("recipient")
    enrollment = _recipient_enrollment(recipient_key)
    clock = [NOW_MS]
    verifier = RecipientProofVerifierV02(
        enrollments={enrollment.recipient_id: enrollment},
        trusted_now_ms=lambda: clock[0],
    )
    challenge = verifier.issue_challenge(
        session_id="session-v02",
        packet_commitment=_digest("packet"),
        purpose=PURPOSE,
        channel_binding_sha256=_digest("channel-binding"),
    )
    clock[0] = NOW_MS + 1
    proof = build_recipient_proof_v02(
        challenge,
        enrollment=enrollment,
        private_key=recipient_key,
        trusted_now_ms=lambda: clock[0],
    )
    first = verifier.verify_and_consume(
        proof,
        challenge,
        expected_packet_commitment=_digest("packet"),
        expected_purpose=PURPOSE,
        expected_channel_binding_sha256=_digest("channel-binding"),
    )
    assert first["valid"] is True

    with pytest.raises(RecipientProofError, match="recipient_challenge_replayed"):
        verifier.verify_and_consume(
            proof,
            challenge,
            expected_packet_commitment=_digest("packet"),
            expected_purpose=PURPOSE,
            expected_channel_binding_sha256=_digest("channel-binding"),
        )
