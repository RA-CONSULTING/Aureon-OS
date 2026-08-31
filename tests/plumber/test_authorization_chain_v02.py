from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.plumber.authorization_chain_v02 import (
    AUTHORIZATION_ROLES,
    AuthorizationChainError,
    AuthorizationChainV02,
    assemble_authorization_chain_v02,
    build_authorization_snapshot_v02,
    build_continuity_decision_v02,
    build_custody_permit_v02,
    validate_authorization_chain_v02,
)
from aureon.plumber.crypto import ed25519_public_key_hex
from aureon.plumber.magic_star_v02 import (
    POINT_ROLES,
    AuthorityBindingV02,
    build_authority_binding_v02,
    component_commitment_v02,
    sign_component_v02,
)

NOW_MS = 1_900_000_000_000
EXPIRES_MS = NOW_MS + 60_000
PURPOSE = "verify_document_signature"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _private_key(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(f"authorization:{label}".encode()).digest()
    )


def _binding(role: str, key: Ed25519PrivateKey) -> AuthorityBindingV02:
    slug = role.lower().replace("_", "-")
    return build_authority_binding_v02(
        role=role,
        issuer=f"authorization-issuer-{slug}",
        principal=f"authorization-principal-{slug}",
        key_id=f"authorization-key-{slug}",
        private_key=key,
    )


@dataclass(frozen=True)
class _AuthorizationFixture:
    chain: AuthorizationChainV02
    continuity: dict[str, object]
    authorization: dict[str, object]
    permits: tuple[dict[str, object], ...]
    trust: dict[str, AuthorityBindingV02]
    keys: dict[str, Ed25519PrivateKey]
    fields: dict[str, str]
    previous_head: str
    revocation_epoch: int


def _build_authorization(
    *,
    previous_head: str | None = None,
    revocation_epoch: int = 11,
) -> _AuthorizationFixture:
    keys = {role: _private_key(role) for role in AUTHORIZATION_ROLES}
    trust = {role: _binding(role, keys[role]) for role in AUTHORIZATION_ROLES}
    fields = {
        "packet_commitment": _digest("protected-packet"),
        "session_id": "session-v02",
        "purpose": PURPOSE,
        "release_context_sha256": _digest("release-context"),
        "recipient_proof_commitment": _digest("recipient-proof"),
        "star_commitment": _digest("star"),
        "release_proof_commitment": _digest("release-proof"),
        "live_binding_sha256": _digest("live-binding"),
        "runtime_measurement_sha256": _digest("runtime"),
        "policy_measurement_sha256": _digest("policy"),
    }
    expected_previous_head = previous_head or _digest("continuity-head")
    continuity = build_continuity_decision_v02(
        packet_commitment=fields["packet_commitment"],
        session_id=fields["session_id"],
        purpose=fields["purpose"],
        star_commitment=fields["star_commitment"],
        release_proof_commitment=fields["release_proof_commitment"],
        previous_decision_head_sha256=expected_previous_head,
        revocation_epoch=revocation_epoch,
        verdict="ELIGIBLE",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=trust["CONTINUITY"],
        private_key=keys["CONTINUITY"],
    )
    authorization = build_authorization_snapshot_v02(
        **fields,
        epas_commitment=_digest("epas"),
        continuity_commitment=component_commitment_v02(continuity),
        verdict="AUTHORIZED",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=trust["AUTHORIZATION"],
        private_key=keys["AUTHORIZATION"],
    )
    authorization_commitment = component_commitment_v02(authorization)
    permits = tuple(
        build_custody_permit_v02(
            role=role,
            packet_commitment=fields["packet_commitment"],
            session_id=fields["session_id"],
            purpose=fields["purpose"],
            authorization_commitment=authorization_commitment,
            share_binding_sha256=_digest(f"share-binding-{role}"),
            verdict="PERMIT",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=trust[role],
            private_key=keys[role],
        )
        for role in POINT_ROLES
    )
    chain = assemble_authorization_chain_v02(
        continuity_decision=continuity,
        authorization_snapshot=authorization,
        permits=permits,
        trust=trust,
        custody_authority=trust["CUSTODY"],
        custody_private_key=keys["CUSTODY"],
        trusted_now_ms=lambda: NOW_MS,
    )
    return _AuthorizationFixture(
        chain=chain,
        continuity=continuity,
        authorization=authorization,
        permits=permits,
        trust=trust,
        keys=keys,
        fields=fields,
        previous_head=expected_previous_head,
        revocation_epoch=revocation_epoch,
    )


def _validate(
    fixture: _AuthorizationFixture,
    chain: AuthorizationChainV02 | None = None,
    *,
    trust: dict[str, AuthorityBindingV02] | None = None,
    now_ms: int = NOW_MS,
) -> dict[str, object]:
    return validate_authorization_chain_v02(
        chain or fixture.chain,
        trust=trust or fixture.trust,
        expected_previous_decision_head_sha256=fixture.previous_head,
        expected_revocation_epoch=fixture.revocation_epoch,
        trusted_now_ms=lambda: now_ms,
    )


def _flip_hex(value: str) -> str:
    return f"{value[:-1]}{'0' if value[-1] != '0' else '1'}"


def test_authorization_chain_happy_path_requires_all_five_permits() -> None:
    fixture = _build_authorization()

    result = _validate(fixture)

    assert result["valid"] is True
    assert result["permit_count"] == 5
    assert result["purpose"] == PURPOSE
    assert result["authorization_chain_commitment"] == fixture.chain.commitment


def test_authorization_public_serialization_contains_no_raw_key_share_or_plaintext() -> None:
    fixture = _build_authorization()
    rendered = json.dumps(fixture.chain.public_dict(), sort_keys=True)

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
    for role in AUTHORIZATION_ROLES:
        assert hashlib.sha256(f"authorization:{role}".encode()).hexdigest() not in rendered


def test_authorization_builder_rejects_wrong_signing_key() -> None:
    fixture = _build_authorization()

    with pytest.raises(AuthorizationChainError, match="component_signer_key_mismatch"):
        build_custody_permit_v02(
            role="SOURCE",
            packet_commitment=fixture.fields["packet_commitment"],
            session_id=fixture.fields["session_id"],
            purpose=fixture.fields["purpose"],
            authorization_commitment=component_commitment_v02(fixture.authorization),
            share_binding_sha256=_digest("wrong-key-share"),
            verdict="PERMIT",
            issued_at_ms=NOW_MS,
            expires_at_ms=EXPIRES_MS,
            authority=fixture.trust["SOURCE"],
            private_key=_private_key("wrong-source"),
        )


@pytest.mark.parametrize("attribute", ["issuer", "principal", "public_key_hex"])
def test_authorization_rejects_wrong_issuer_principal_or_key(attribute: str) -> None:
    fixture = _build_authorization()
    original = fixture.trust["SOURCE"]
    replacement_value = {
        "issuer": "authorization-issuer-untrusted",
        "principal": "authorization-principal-untrusted",
        "public_key_hex": ed25519_public_key_hex(_private_key("untrusted-key")),
    }[attribute]
    bad_trust = {
        **fixture.trust,
        "SOURCE": replace(original, **{attribute: replacement_value}),
    }

    with pytest.raises(AuthorizationChainError, match="signed_component_authority_mismatch"):
        _validate(fixture, trust=bad_trust)


def test_authorization_rejects_duplicate_authority() -> None:
    fixture = _build_authorization()
    bad_trust = {
        **fixture.trust,
        "OBSERVER": replace(
            fixture.trust["OBSERVER"],
            public_key_hex=fixture.trust["SOURCE"].public_key_hex,
        ),
    }

    with pytest.raises(AuthorizationChainError, match="authorization_keys_not_distinct"):
        _validate(fixture, trust=bad_trust)


@pytest.mark.parametrize("missing_role", POINT_ROLES)
def test_authorization_rejects_each_missing_custody_permit(
    missing_role: str,
) -> None:
    fixture = _build_authorization()
    permits = tuple(
        permit
        for role, permit in zip(POINT_ROLES, fixture.permits, strict=True)
        if role != missing_role
    )

    with pytest.raises(AuthorizationChainError, match="all_five_custody_permits_required"):
        assemble_authorization_chain_v02(
            continuity_decision=fixture.continuity,
            authorization_snapshot=fixture.authorization,
            permits=permits,
            trust=fixture.trust,
            custody_authority=fixture.trust["CUSTODY"],
            custody_private_key=fixture.keys["CUSTODY"],
            trusted_now_ms=lambda: NOW_MS,
        )


@pytest.mark.parametrize("permit_count", [3, 4])
def test_authorization_has_no_generic_threshold_acceptance(permit_count: int) -> None:
    fixture = _build_authorization()

    with pytest.raises(AuthorizationChainError, match="all_five_custody_permits_required"):
        assemble_authorization_chain_v02(
            continuity_decision=fixture.continuity,
            authorization_snapshot=fixture.authorization,
            permits=fixture.permits[:permit_count],
            trust=fixture.trust,
            custody_authority=fixture.trust["CUSTODY"],
            custody_private_key=fixture.keys["CUSTODY"],
            trusted_now_ms=lambda: NOW_MS,
        )


def test_authorization_rejects_expired_continuity() -> None:
    fixture = _build_authorization()

    with pytest.raises(AuthorizationChainError, match="continuity_time_window_invalid"):
        _validate(fixture, now_ms=EXPIRES_MS)


def test_authorization_rejects_unsigned_and_resigned_permit_tamper() -> None:
    fixture = _build_authorization()
    permit = dict(fixture.chain.permits[0])
    payload = dict(permit["payload"])
    payload["purpose"] = "tampered-purpose"
    permit["payload"] = payload
    permits = list(fixture.chain.permits)
    permits[0] = permit
    with pytest.raises(AuthorizationChainError, match="signed_component_payload_hash_mismatch"):
        _validate(fixture, replace(fixture.chain, permits=tuple(permits)))

    resigned = sign_component_v02(
        component_type="CUSTODY_PERMIT",
        authority=fixture.trust["SOURCE"],
        payload=payload,
        private_key=fixture.keys["SOURCE"],
    )
    permits[0] = resigned
    with pytest.raises(AuthorizationChainError, match="custody_permit_join_mismatch_purpose"):
        assemble_authorization_chain_v02(
            continuity_decision=fixture.continuity,
            authorization_snapshot=fixture.authorization,
            permits=permits,
            trust=fixture.trust,
            custody_authority=fixture.trust["CUSTODY"],
            custody_private_key=fixture.keys["CUSTODY"],
            trusted_now_ms=lambda: NOW_MS,
        )


def test_authorization_rejects_resigned_snapshot_with_changed_packet_join() -> None:
    fixture = _build_authorization()
    payload = dict(fixture.authorization["payload"])
    payload["packet_commitment"] = _digest("alternate-carrier-packet")
    resigned = sign_component_v02(
        component_type="AUTHORIZATION_SNAPSHOT",
        authority=fixture.trust["AUTHORIZATION"],
        payload=payload,
        private_key=fixture.keys["AUTHORIZATION"],
    )

    with pytest.raises(
        AuthorizationChainError,
        match="authorization_continuity_join_mismatch_packet_commitment",
    ):
        _validate(
            fixture,
            replace(fixture.chain, authorization_snapshot=resigned),
        )


def test_authorization_rejects_custody_seal_tamper() -> None:
    fixture = _build_authorization()
    custody = dict(fixture.chain.custody_authorization)
    custody["signature_hex"] = _flip_hex(custody["signature_hex"])

    with pytest.raises(AuthorizationChainError, match="signed_component_signature_invalid"):
        _validate(fixture, replace(fixture.chain, custody_authorization=custody))


def test_authorization_rejects_stale_continuity_head_or_epoch() -> None:
    stale = _build_authorization()

    with pytest.raises(AuthorizationChainError, match="continuity_head_mismatch"):
        validate_authorization_chain_v02(
            stale.chain,
            trust=stale.trust,
            expected_previous_decision_head_sha256=_digest("current-continuity-head"),
            expected_revocation_epoch=stale.revocation_epoch,
            trusted_now_ms=lambda: NOW_MS,
        )

    with pytest.raises(AuthorizationChainError, match="continuity_revocation_epoch_mismatch"):
        validate_authorization_chain_v02(
            stale.chain,
            trust=stale.trust,
            expected_previous_decision_head_sha256=stale.previous_head,
            expected_revocation_epoch=stale.revocation_epoch + 1,
            trusted_now_ms=lambda: NOW_MS,
        )
