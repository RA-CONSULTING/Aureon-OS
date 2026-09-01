from __future__ import annotations

import base64
import hashlib
import json
import traceback
import zlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from aureon.harmonic.hnc_quantum_packet_crypto import (
    build_hnc_quantum_packet,
    validate_hnc_packet_contract,
)
from aureon.plumber.authorization_chain_v02 import (
    AUTHORIZATION_ROLES,
    AuthorizationChainV02,
    assemble_authorization_chain_v02,
    build_authorization_snapshot_v02,
    build_continuity_decision_v02,
    build_custody_permit_v02,
)
from aureon.plumber.crypto import ed25519_public_key_hex
from aureon.plumber.magic_star_v02 import (
    POINT_ROLES,
    AuthorityBindingV02,
    build_authority_binding_v02,
    component_commitment_v02,
)
from aureon.plumber.release_state_v02 import (
    InMemoryReleaseStateStoreV02,
    OpaqueCustodyLease,
)
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    ProtectedMagicStarPacketV02,
    RegisteredCapabilityV02,
    StarCustodyError,
    validate_magic_star_hnc_packet_v02,
)

NOW_MS = 1_900_000_000_000
EXPIRES_MS = NOW_MS + 60_000
PURPOSE = "verify_document_signature"
SESSION_ID = "session-v02"
CAPABILITY_ID = "verify-signature"
PLAINTEXT = b"protected-plaintext-canary"
MASTER_KEY = b"local-lab-master-key-material-32-bytes"
LEGACY_V1_FIXTURES = json.loads(
    (
        Path(__file__).parents[1]
        / "fixtures"
        / "hnc_legacy_v1_known_answers.json"
    ).read_text(encoding="utf-8")
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _private_key(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(f"star-custody:{label}".encode()).digest()
    )


def _binding(role: str, private_key: Ed25519PrivateKey) -> AuthorityBindingV02:
    slug = role.lower().replace("_", "-")
    return build_authority_binding_v02(
        role=role,
        issuer=f"custody-issuer-{slug}",
        principal=f"custody-principal-{slug}",
        key_id=f"custody-key-{slug}",
        private_key=private_key,
    )


def _safe_capability(plaintext: bytes) -> Mapping[str, Any]:
    return {"signature_valid": plaintext == PLAINTEXT}


def _legacy_single_carrier(vector: Mapping[str, str]) -> tuple[dict[str, Any], bytes | str]:
    fixture = LEGACY_V1_FIXTURES["single"]
    metadata = json.loads(
        zlib.decompress(base64.b64decode(fixture["metadata_zlib_b64"])).decode("utf-8")
    )
    key = (
        base64.b64decode(vector["key_value"])
        if vector["key_kind"] == "bytes_b64"
        else vector["key_value"]
    )
    return (
        {
            "magic": "AUREON-HNC-QP",
            "schema_version": 1,
            "metadata": metadata,
            "operator_aad": fixture["operator_aad"],
            "nonce_b64": fixture["nonce_b64"],
            "ciphertext_b64": vector["ciphertext_b64"],
            "packet_sha256": vector["packet_sha256"],
        },
        key,
    )


def _plaintext_leaking_capability(plaintext: bytes) -> Mapping[str, Any]:
    return {"decoded_payload": plaintext.decode("utf-8")}


@dataclass(frozen=True)
class _CustodyConfiguration:
    source_key: Ed25519PrivateKey
    source_authority: AuthorityBindingV02
    keys: dict[str, Ed25519PrivateKey]
    trust: dict[str, AuthorityBindingV02]
    state_store: InMemoryReleaseStateStoreV02
    capabilities: dict[str, RegisteredCapabilityV02]


@dataclass(frozen=True)
class _CustodyFixture:
    custody: LocalDevelopmentStarCustodyV02
    packet: ProtectedMagicStarPacketV02
    source_authority: AuthorityBindingV02
    source_key: Ed25519PrivateKey
    keys: dict[str, Ed25519PrivateKey]
    trust: dict[str, AuthorityBindingV02]
    state_store: InMemoryReleaseStateStoreV02
    lease: OpaqueCustodyLease
    authorization_chain: AuthorizationChainV02
    capability: RegisteredCapabilityV02


def _configuration(
    *,
    handler: Callable[[bytes], Mapping[str, Any]] = _safe_capability,
    result_schema: Mapping[str, str] | None = None,
) -> _CustodyConfiguration:
    keys = {role: _private_key(f"authority-{role}") for role in AUTHORIZATION_ROLES}
    trust = {role: _binding(role, keys[role]) for role in AUTHORIZATION_ROLES}
    capability = RegisteredCapabilityV02(
        capability_id=CAPABILITY_ID,
        measurement_sha256=_digest("registered-capability-measurement"),
        policy_measurement_sha256=_digest("policy-measurement"),
        result_schema=result_schema or {"signature_valid": "bool"},
        handler=handler,
    )
    return _CustodyConfiguration(
        source_key=keys["SOURCE"],
        source_authority=trust["SOURCE"],
        keys=keys,
        trust=trust,
        state_store=InMemoryReleaseStateStoreV02(trusted_now_ms=lambda: NOW_MS),
        capabilities={CAPABILITY_ID: capability},
    )


def _build_authorization_chain(
    packet: ProtectedMagicStarPacketV02,
    *,
    keys: Mapping[str, Ed25519PrivateKey],
    trust: Mapping[str, AuthorityBindingV02],
    session_id: str = SESSION_ID,
) -> AuthorizationChainV02:
    star_commitment = _digest("terminal-star")
    release_proof_commitment = _digest("release-proof")
    continuity = build_continuity_decision_v02(
        packet_commitment=packet.packet_commitment,
        session_id=session_id,
        purpose=packet.purpose,
        star_commitment=star_commitment,
        release_proof_commitment=release_proof_commitment,
        previous_decision_head_sha256=_digest("previous-continuity-head"),
        revocation_epoch=11,
        verdict="ELIGIBLE",
        issued_at_ms=NOW_MS - 1_000,
        expires_at_ms=EXPIRES_MS,
        authority=trust["CONTINUITY"],
        private_key=keys["CONTINUITY"],
    )
    authorization = build_authorization_snapshot_v02(
        packet_commitment=packet.packet_commitment,
        session_id=session_id,
        purpose=packet.purpose,
        release_context_sha256=packet.release_context_sha256,
        recipient_proof_commitment=_digest("recipient-proof"),
        star_commitment=star_commitment,
        epas_commitment=_digest("epas-commitment"),
        release_proof_commitment=release_proof_commitment,
        continuity_commitment=component_commitment_v02(continuity),
        live_binding_sha256=_digest("live-binding"),
        runtime_measurement_sha256=_digest("runtime-measurement"),
        policy_measurement_sha256=_digest("policy-measurement"),
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
            packet_commitment=packet.packet_commitment,
            session_id=session_id,
            purpose=packet.purpose,
            authorization_commitment=authorization_commitment,
            share_binding_sha256=packet.share_bindings[index]["binding_sha256"],
            verdict="PERMIT",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=trust[role],
            private_key=keys[role],
        )
        for index, role in enumerate(POINT_ROLES)
    )
    return assemble_authorization_chain_v02(
        continuity_decision=continuity,
        authorization_snapshot=authorization,
        permits=permits,
        trust=trust,
        custody_authority=trust["CUSTODY"],
        custody_private_key=keys["CUSTODY"],
        trusted_now_ms=lambda: NOW_MS,
    )


def _build_custody(
    *,
    handler: Callable[[bytes], Mapping[str, Any]] = _safe_capability,
    result_schema: Mapping[str, str] | None = None,
    additional_capabilities: Mapping[str, RegisteredCapabilityV02] | None = None,
    master_key: bytes | str = MASTER_KEY,
    carrier: Mapping[str, Any] | None = None,
) -> _CustodyFixture:
    config = _configuration(handler=handler, result_schema=result_schema)
    capabilities = {
        **config.capabilities,
        **dict(additional_capabilities or {}),
    }
    custody = LocalDevelopmentStarCustodyV02(
        allow_insecure_same_process=True,
        source_authority=config.source_authority,
        source_private_key=config.source_key,
        state_store=config.state_store,
        authorization_trust=config.trust,
        capabilities=capabilities,
        trusted_now_ms=lambda: NOW_MS,
    )
    if carrier is None:
        carrier = build_hnc_quantum_packet(
            PLAINTEXT,
            master_key,
            purpose=PURPOSE,
            operator_aad={"laboratory": True},
        )
    carrier_purpose = carrier["metadata"]["purpose"]
    packet = custody.protect_carrier(
        packet_id="packet-v02",
        purpose=carrier_purpose,
        release_context_sha256=_digest("release-context"),
        legacy_carrier=carrier,
        legacy_master_key=master_key,
    )
    config.state_store.create(
        session_id=SESSION_ID,
        packet_id=packet.packet_id,
        purpose=packet.purpose,
        live_binding_sha256=_digest("live-binding"),
        expires_at_ms=EXPIRES_MS,
    )
    config.state_store.reserve(
        session_id=SESSION_ID,
        expected_live_binding_sha256=_digest("live-binding"),
    )
    lease = config.state_store.claim_custody(session_id=SESSION_ID)
    chain = _build_authorization_chain(
        packet,
        keys=config.keys,
        trust=config.trust,
    )
    return _CustodyFixture(
        custody=custody,
        packet=packet,
        source_authority=config.source_authority,
        source_key=config.source_key,
        keys=config.keys,
        trust=config.trust,
        state_store=config.state_store,
        lease=lease,
        authorization_chain=chain,
        capability=config.capabilities[CAPABILITY_ID],
    )


def _flip_hex(value: str) -> str:
    return f"{value[:-1]}{'0' if value[-1] != '0' else '1'}"


def _flip_b64(value: str) -> str:
    return f"{'A' if value[0] != 'A' else 'B'}{value[1:]}"


def test_star_custody_requires_explicit_insecure_local_opt_in() -> None:
    config = _configuration()

    with pytest.raises(
        StarCustodyError,
        match="explicit_insecure_same_process_opt_in_required",
    ):
        LocalDevelopmentStarCustodyV02(
            allow_insecure_same_process=False,
            source_authority=config.source_authority,
            source_private_key=config.source_key,
            state_store=config.state_store,
            authorization_trust=config.trust,
            capabilities=config.capabilities,
            trusted_now_ms=lambda: NOW_MS,
        )


def test_star_custody_pins_state_trust_and_registered_capabilities() -> None:
    config = _configuration()

    with pytest.raises(StarCustodyError, match="custody_release_state_store_invalid"):
        LocalDevelopmentStarCustodyV02(
            allow_insecure_same_process=True,
            source_authority=config.source_authority,
            source_private_key=config.source_key,
            state_store=object(),  # type: ignore[arg-type]
            authorization_trust=config.trust,
            capabilities=config.capabilities,
            trusted_now_ms=lambda: NOW_MS,
        )

    with pytest.raises(StarCustodyError, match="custody_source_authority_join_mismatch"):
        LocalDevelopmentStarCustodyV02(
            allow_insecure_same_process=True,
            source_authority=replace(
                config.source_authority,
                principal="custody-principal-unjoined-source",
            ),
            source_private_key=config.source_key,
            state_store=config.state_store,
            authorization_trust=config.trust,
            capabilities=config.capabilities,
            trusted_now_ms=lambda: NOW_MS,
        )

    with pytest.raises(StarCustodyError, match="custody_capability_registry_invalid"):
        LocalDevelopmentStarCustodyV02(
            allow_insecure_same_process=True,
            source_authority=config.source_authority,
            source_private_key=config.source_key,
            state_store=config.state_store,
            authorization_trust=config.trust,
            capabilities={"unjoined-id": config.capabilities[CAPABILITY_ID]},
            trusted_now_ms=lambda: NOW_MS,
        )


def test_star_custody_happy_path_returns_only_registered_capability_result() -> None:
    fixture = _build_custody()

    result, metadata = fixture.custody.release_to_capability(
        fixture.packet,
        lease=fixture.lease,
        authorization_chain=fixture.authorization_chain,
        capability_id=CAPABILITY_ID,
    )

    assert result == {"signature_valid": True}
    assert metadata["capability_id"] == CAPABILITY_ID
    assert metadata["capability_measurement_sha256"] == fixture.capability.measurement_sha256
    assert metadata["capability_policy_commitment"] == (
        fixture.capability.policy_measurement_sha256
    )
    assert metadata["plaintext_returned"] is False
    assert metadata["carrier_returned"] is False
    assert metadata["shares_returned"] is False
    assert metadata["keys_returned"] is False
    assert metadata["production_ready"] is False
    assert fixture.custody.production_ready is False
    assert PLAINTEXT.decode() not in json.dumps([result, metadata], sort_keys=True)


def test_star_custody_normalizes_base64url_looking_string_master_key() -> None:
    normalized_key = hashlib.sha256(b"base64url-looking-master-key").digest()
    encoded_key = base64.urlsafe_b64encode(normalized_key).decode("ascii").rstrip("=")
    fixture = _build_custody(master_key=encoded_key)

    result, metadata = fixture.custody.release_to_capability(
        fixture.packet,
        lease=fixture.lease,
        authorization_chain=fixture.authorization_chain,
        capability_id=CAPABILITY_ID,
    )

    assert result == {"signature_valid": True}
    assert metadata["keys_returned"] is False


@pytest.mark.parametrize(
    "vector",
    LEGACY_V1_FIXTURES["single"]["vectors"],
    ids=lambda vector: vector["key_kind"],
)
def test_star_custody_releases_prechange_v1_key_profiles(vector) -> None:
    carrier, master_key = _legacy_single_carrier(vector)
    fixture = _build_custody(
        handler=lambda plaintext: {"legacy_profile_valid": plaintext == b"legacy-profile"},
        result_schema={"legacy_profile_valid": "bool"},
        master_key=master_key,
        carrier=carrier,
    )

    result, metadata = fixture.custody.release_to_capability(
        fixture.packet,
        lease=fixture.lease,
        authorization_chain=fixture.authorization_chain,
        capability_id=CAPABILITY_ID,
    )

    assert result == {"legacy_profile_valid": True}
    assert metadata["keys_returned"] is False


def test_star_custody_public_packet_and_registration_have_no_secret_material() -> None:
    fixture = _build_custody()
    public = fixture.packet.public_dict()
    rendered = json.dumps(public, sort_keys=True)

    assert validate_magic_star_hnc_packet_v02(
        fixture.packet,
        source_authority=fixture.source_authority,
    )["structural_preflight_only"] is True
    assert fixture.custody.capability_measurement(CAPABILITY_ID) == (
        fixture.capability.measurement_sha256
    )
    assert "handler=" not in repr(fixture.capability)
    assert PLAINTEXT.decode() not in rendered
    assert MASTER_KEY.decode() not in rendered
    for forbidden_key in (
        "private_key",
        "private_key_hex",
        "root_key",
        "session_key",
        "share_bytes",
        "share_hex",
        "plaintext",
        "carrier_master_key",
    ):
        assert f'"{forbidden_key}"' not in rendered


def test_v01_and_v02_packet_parsers_reject_cross_version_objects() -> None:
    fixture = _build_custody()
    legacy_carrier = build_hnc_quantum_packet(
        PLAINTEXT,
        MASTER_KEY,
        purpose=PURPOSE,
    )

    legacy_readback = validate_hnc_packet_contract(fixture.packet.public_dict())
    assert legacy_readback["valid"] is False
    assert "bad_magic" in legacy_readback["reasons"]

    with pytest.raises(StarCustodyError, match="v02_protected_packet_type_invalid"):
        validate_magic_star_hnc_packet_v02(
            legacy_carrier,  # type: ignore[arg-type]
            source_authority=fixture.source_authority,
        )


def test_star_custody_rejects_wrong_source_private_key() -> None:
    config = _configuration()
    custody = LocalDevelopmentStarCustodyV02(
        allow_insecure_same_process=True,
        source_authority=config.source_authority,
        source_private_key=_private_key("wrong-source"),
        state_store=config.state_store,
        authorization_trust=config.trust,
        capabilities=config.capabilities,
        trusted_now_ms=lambda: NOW_MS,
    )
    carrier = build_hnc_quantum_packet(PLAINTEXT, MASTER_KEY, purpose=PURPOSE)

    with pytest.raises(StarCustodyError, match="component_signer_key_mismatch"):
        custody.protect_carrier(
            packet_id="packet-v02",
            purpose=PURPOSE,
            release_context_sha256=_digest("release-context"),
            legacy_carrier=carrier,
            legacy_master_key=MASTER_KEY,
        )


@pytest.mark.parametrize("attribute", ["issuer", "principal", "public_key_hex"])
def test_star_custody_rejects_wrong_source_issuer_principal_or_key(attribute: str) -> None:
    fixture = _build_custody()
    replacement_value = {
        "issuer": "custody-issuer-untrusted-source",
        "principal": "custody-principal-untrusted-source",
        "public_key_hex": ed25519_public_key_hex(_private_key("untrusted-source")),
    }[attribute]
    wrong_authority = replace(
        fixture.source_authority,
        **{attribute: replacement_value},
    )

    with pytest.raises(StarCustodyError, match="signed_component_authority_mismatch"):
        validate_magic_star_hnc_packet_v02(
            fixture.packet,
            source_authority=wrong_authority,
        )


def test_star_custody_rejects_source_signature_and_ciphertext_tamper() -> None:
    fixture = _build_custody()
    signature = dict(fixture.packet.source_signature)
    signature["signature_hex"] = _flip_hex(str(signature["signature_hex"]))
    with pytest.raises(StarCustodyError, match="signed_component_signature_invalid"):
        validate_magic_star_hnc_packet_v02(
            replace(fixture.packet, source_signature=signature),
            source_authority=fixture.source_authority,
        )

    with pytest.raises(StarCustodyError, match="protected_packet_source_join_mismatch"):
        validate_magic_star_hnc_packet_v02(
            replace(
                fixture.packet,
                ciphertext_b64=_flip_b64(fixture.packet.ciphertext_b64),
            ),
            source_authority=fixture.source_authority,
        )


def test_star_custody_rejects_incomplete_share_set() -> None:
    fixture = _build_custody()
    record = fixture.custody._records[fixture.packet.packet_id]
    record.shares = record.shares[:-1]

    with pytest.raises(StarCustodyError, match="all_five_custody_shares_required"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )


def test_star_custody_rejects_signed_chain_for_other_session() -> None:
    fixture = _build_custody()
    wrong_chain = _build_authorization_chain(
        fixture.packet,
        keys=fixture.keys,
        trust=fixture.trust,
        session_id="other-session-v02",
    )

    with pytest.raises(
        StarCustodyError,
        match="custody_authorization_runtime_join_mismatch",
    ):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=wrong_chain,
            capability_id=CAPABILITY_ID,
        )


def test_star_custody_rejects_unsigned_authorization_mapping() -> None:
    fixture = _build_custody()
    unsigned = {
        "packet_commitment": fixture.packet.packet_commitment,
        "session_id": fixture.lease.session_id,
        "purpose": fixture.packet.purpose,
        "share_bindings": [
            item["binding_sha256"] for item in fixture.packet.share_bindings
        ],
        "permit_count": 5,
    }

    with pytest.raises(StarCustodyError, match="custody_authorization_chain_invalid"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=unsigned,  # type: ignore[arg-type]
            capability_id=CAPABILITY_ID,
        )


def test_star_custody_rejects_fabricated_lease() -> None:
    fixture = _build_custody()
    forged_lease = OpaqueCustodyLease(
        session_id=fixture.lease.session_id,
        packet_id=fixture.packet.packet_id,
        lease_token="caller-controlled-token",
    )

    with pytest.raises(StarCustodyError, match="custody_lease_validation_failed"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=forged_lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )


def test_star_custody_packet_material_is_one_use() -> None:
    fixture = _build_custody()

    fixture.custody.release_to_capability(
        fixture.packet,
        lease=fixture.lease,
        authorization_chain=fixture.authorization_chain,
        capability_id=CAPABILITY_ID,
    )

    with pytest.raises(
        StarCustodyError,
        match="custody_(material_unavailable_or_reused|lease_validation_failed)",
    ):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )


def test_star_custody_aead_failure_does_not_consume_retryable_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_custody()
    record = fixture.custody._records[fixture.packet.packet_id]
    original_decrypt = AESGCM.decrypt
    attempts = 0

    def fail_once(
        cipher: AESGCM,
        nonce: bytes,
        data: bytes,
        associated_data: bytes | None,
    ) -> bytes:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise InvalidTag
        return original_decrypt(cipher, nonce, data, associated_data)

    monkeypatch.setattr(AESGCM, "decrypt", fail_once)

    with pytest.raises(
        StarCustodyError,
        match="protected_packet_authentication_failed",
    ):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )

    assert fixture.custody._records[fixture.packet.packet_id] is record
    assert record.claimed is False

    result, _metadata = fixture.custody.release_to_capability(
        fixture.packet,
        lease=fixture.lease,
        authorization_chain=fixture.authorization_chain,
        capability_id=CAPABILITY_ID,
    )
    assert attempts >= 2
    assert result == {"signature_valid": True}

    with pytest.raises(StarCustodyError, match="custody_material_unavailable_or_reused"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )


def test_star_custody_capability_failure_still_consumes_one_use_material() -> None:
    attempts = 0

    def fail_once(plaintext: bytes) -> Mapping[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("synthetic capability failure")
        return _safe_capability(plaintext)

    fixture = _build_custody(handler=fail_once)
    record = fixture.custody._records[fixture.packet.packet_id]

    with pytest.raises(StarCustodyError, match="capability_execution_failed"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )

    assert attempts == 1
    assert fixture.packet.packet_id not in fixture.custody._records
    assert all(not any(share) for share in record.shares)
    with pytest.raises(StarCustodyError, match="custody_material_unavailable_or_reused"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )
    assert attempts == 1


def test_star_custody_rejects_unregistered_per_call_capability_selection() -> None:
    fixture = _build_custody()

    with pytest.raises(StarCustodyError, match="capability_not_registered"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id="caller-selected-arbitrary-handler",
        )


def test_star_custody_binds_signed_policy_to_selected_capability() -> None:
    capability_b_id = "alternate-capability"
    capability_b = RegisteredCapabilityV02(
        capability_id=capability_b_id,
        measurement_sha256=_digest("alternate-capability-measurement"),
        policy_measurement_sha256=_digest("alternate-policy-measurement"),
        result_schema={"selected": "bool"},
        handler=lambda _plaintext: {"selected": True},
    )
    fixture = _build_custody(
        additional_capabilities={capability_b_id: capability_b},
    )

    with pytest.raises(
        StarCustodyError,
        match="custody_authorization_runtime_join_mismatch",
    ):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=capability_b_id,
        )

    result, _metadata = fixture.custody.release_to_capability(
        fixture.packet,
        lease=fixture.lease,
        authorization_chain=fixture.authorization_chain,
        capability_id=CAPABILITY_ID,
    )
    assert result == {"signature_valid": True}


def test_star_custody_sanitizes_plaintext_bearing_handler_exception() -> None:
    def leaking_exception(plaintext: bytes) -> Mapping[str, Any]:
        raise RuntimeError(f"handler leaked: {plaintext.decode('utf-8')}")

    fixture = _build_custody(handler=leaking_exception)

    with pytest.raises(StarCustodyError) as captured:
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )

    assert captured.value.code == "capability_execution_failed"
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    rendered = "".join(traceback.format_exception(captured.value))
    assert PLAINTEXT.decode() not in rendered
    assert "handler leaked" not in rendered


def test_star_custody_rejects_capability_that_returns_plaintext() -> None:
    fixture = _build_custody(handler=_plaintext_leaking_capability)

    with pytest.raises(
        StarCustodyError,
        match="capability_result_schema_denied",
    ):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )


@pytest.mark.parametrize(
    "encoder",
    [
        lambda plaintext: list(plaintext),
        lambda plaintext: int.from_bytes(plaintext, "big"),
        lambda plaintext: plaintext[::-1].decode("utf-8"),
        lambda plaintext: {"bytes": list(plaintext)},
    ],
    ids=["integer_vector", "large_integer", "reversed_text", "nested_vector"],
)
def test_star_custody_typed_result_abi_blocks_reversible_plaintext_encodings(
    encoder: Callable[[bytes], Any],
) -> None:
    fixture = _build_custody(
        handler=lambda plaintext: {"signature_valid": encoder(plaintext)}
    )

    with pytest.raises(StarCustodyError, match="capability_result_schema_denied"):
        fixture.custody.release_to_capability(
            fixture.packet,
            lease=fixture.lease,
            authorization_chain=fixture.authorization_chain,
            capability_id=CAPABILITY_ID,
        )
