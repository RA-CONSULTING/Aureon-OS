from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.plumber.crypto import ed25519_public_key_hex
from aureon.plumber.magic_star_v02 import (
    AuthorityBindingV02,
    build_authority_binding_v02,
    sign_component_v02,
)
from aureon.plumber.release_evidence_v02 import (
    ORGAN_ROLES,
    RELEASE_EVIDENCE_ROLES,
    ReleaseEvidenceError,
    ReleaseEvidenceV02,
    assemble_release_evidence_v02,
    build_organ_receipt_v02,
    validate_release_evidence_v02,
)

NOW_MS = 1_900_000_000_000
EXPIRES_MS = NOW_MS + 60_000
PURPOSE = "verify_document_signature"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _private_key(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(f"release-evidence:{label}".encode()).digest()
    )


def _binding(role: str, key: Ed25519PrivateKey) -> AuthorityBindingV02:
    slug = role.lower().replace("_", "-")
    return build_authority_binding_v02(
        role=role,
        issuer=f"release-issuer-{slug}",
        principal=f"release-principal-{slug}",
        key_id=f"release-key-{slug}",
        private_key=key,
    )


@dataclass(frozen=True)
class _EvidenceFixture:
    evidence: ReleaseEvidenceV02
    receipts: tuple[dict[str, object], ...]
    trust: dict[str, AuthorityBindingV02]
    keys: dict[str, Ed25519PrivateKey]
    fields: dict[str, str]
    evidence_hashes: dict[str, str]


def _build_evidence() -> _EvidenceFixture:
    keys = {role: _private_key(role) for role in RELEASE_EVIDENCE_ROLES}
    trust = {role: _binding(role, keys[role]) for role in RELEASE_EVIDENCE_ROLES}
    fields = {
        "packet_commitment": _digest("packet"),
        "session_id": "session-v02",
        "purpose": PURPOSE,
        "release_context_sha256": _digest("release-context"),
        "recipient_proof_commitment": _digest("recipient-proof"),
        "star_commitment": _digest("star"),
        "epas_commitment": _digest("epas"),
        "live_binding_sha256": _digest("live-binding"),
        "runtime_measurement_sha256": _digest("runtime"),
        "policy_measurement_sha256": _digest("policy"),
    }
    evidence_hashes = {role: _digest(f"organ-evidence-{role}") for role in ORGAN_ROLES}
    receipts = tuple(
        build_organ_receipt_v02(
            role=role,
            **fields,
            evidence_sha256=evidence_hashes[role],
            verdict="APPROVE",
            issued_at_ms=NOW_MS - 1_000,
            expires_at_ms=EXPIRES_MS,
            authority=trust[role],
            private_key=keys[role],
        )
        for role in ORGAN_ROLES
    )
    evidence = assemble_release_evidence_v02(
        organ_receipts=receipts,
        trust=trust,
        release_proof_authority=trust["RELEASE_PROOF"],
        release_proof_private_key=keys["RELEASE_PROOF"],
        trusted_now_ms=lambda: NOW_MS,
    )
    return _EvidenceFixture(
        evidence=evidence,
        receipts=receipts,
        trust=trust,
        keys=keys,
        fields=fields,
        evidence_hashes=evidence_hashes,
    )


def _validate(
    fixture: _EvidenceFixture,
    evidence: ReleaseEvidenceV02 | None = None,
    *,
    trust: dict[str, AuthorityBindingV02] | None = None,
    now_ms: int = NOW_MS,
) -> dict[str, object]:
    return validate_release_evidence_v02(
        evidence or fixture.evidence,
        trust=trust or fixture.trust,
        expected_evidence_sha256_by_role=fixture.evidence_hashes,
        trusted_now_ms=lambda: now_ms,
    )


def _flip_hex(value: str) -> str:
    return f"{value[:-1]}{'0' if value[-1] != '0' else '1'}"


def test_release_evidence_happy_path_joins_all_seven_organs() -> None:
    fixture = _build_evidence()

    result = _validate(fixture)

    assert result["valid"] is True
    assert result["organ_count"] == 7
    assert result["purpose"] == PURPOSE
    assert result["release_evidence_commitment"] == fixture.evidence.commitment


def test_release_evidence_public_serialization_has_no_private_key_share_or_plaintext() -> None:
    fixture = _build_evidence()
    rendered = json.dumps(fixture.evidence.public_dict(), sort_keys=True)

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
    for role in RELEASE_EVIDENCE_ROLES:
        seed = hashlib.sha256(f"release-evidence:{role}".encode()).hexdigest()
        assert seed not in rendered


def test_release_evidence_builder_rejects_wrong_signing_key() -> None:
    fixture = _build_evidence()

    with pytest.raises(ReleaseEvidenceError, match="component_signer_key_mismatch"):
        build_organ_receipt_v02(
            role="SOURCE",
            **fixture.fields,
            evidence_sha256=_digest("wrong-key"),
            verdict="APPROVE",
            issued_at_ms=NOW_MS,
            expires_at_ms=EXPIRES_MS,
            authority=fixture.trust["SOURCE"],
            private_key=_private_key("wrong-source"),
        )


@pytest.mark.parametrize("attribute", ["issuer", "principal", "public_key_hex"])
def test_release_evidence_rejects_wrong_issuer_principal_or_key(attribute: str) -> None:
    fixture = _build_evidence()
    original = fixture.trust["SOURCE"]
    replacement_value = {
        "issuer": "release-issuer-untrusted",
        "principal": "release-principal-untrusted",
        "public_key_hex": ed25519_public_key_hex(_private_key("untrusted-key")),
    }[attribute]
    bad_trust = {
        **fixture.trust,
        "SOURCE": replace(original, **{attribute: replacement_value}),
    }

    with pytest.raises(ReleaseEvidenceError, match="signed_component_authority_mismatch"):
        _validate(fixture, trust=bad_trust)


def test_release_evidence_rejects_duplicate_authority_key() -> None:
    fixture = _build_evidence()
    bad_trust = {
        **fixture.trust,
        "OBSERVER": replace(
            fixture.trust["OBSERVER"],
            public_key_hex=fixture.trust["SOURCE"].public_key_hex,
        ),
    }

    with pytest.raises(ReleaseEvidenceError, match="release_evidence_keys_not_distinct"):
        _validate(fixture, trust=bad_trust)


def test_release_evidence_rejects_missing_or_substituted_external_evidence_hash() -> None:
    fixture = _build_evidence()

    with pytest.raises(ReleaseEvidenceError, match="expected_organ_evidence_set_invalid"):
        validate_release_evidence_v02(
            fixture.evidence,
            trust=fixture.trust,
            expected_evidence_sha256_by_role={
                role: fixture.evidence_hashes[role] for role in ORGAN_ROLES[:-1]
            },
            trusted_now_ms=lambda: NOW_MS,
        )

    substituted = {**fixture.evidence_hashes, "SOURCE": _digest("substituted-source-evidence")}
    with pytest.raises(ReleaseEvidenceError, match="organ_evidence_substitution_detected"):
        validate_release_evidence_v02(
            fixture.evidence,
            trust=fixture.trust,
            expected_evidence_sha256_by_role=substituted,
            trusted_now_ms=lambda: NOW_MS,
        )


@pytest.mark.parametrize("missing_role", ORGAN_ROLES)
def test_release_evidence_rejects_each_missing_organ_receipt(
    missing_role: str,
) -> None:
    fixture = _build_evidence()
    receipts = tuple(
        receipt
        for role, receipt in zip(ORGAN_ROLES, fixture.receipts, strict=True)
        if role != missing_role
    )

    with pytest.raises(ReleaseEvidenceError, match="all_seven_organ_receipts_required"):
        assemble_release_evidence_v02(
            organ_receipts=receipts,
            trust=fixture.trust,
            release_proof_authority=fixture.trust["RELEASE_PROOF"],
            release_proof_private_key=fixture.keys["RELEASE_PROOF"],
            trusted_now_ms=lambda: NOW_MS,
        )


def test_release_evidence_rejects_reordered_organ_receipts() -> None:
    fixture = _build_evidence()
    reordered = list(fixture.receipts)
    reordered[0], reordered[1] = reordered[1], reordered[0]

    with pytest.raises(ReleaseEvidenceError, match="signed_component_authority_mismatch"):
        assemble_release_evidence_v02(
            organ_receipts=reordered,
            trust=fixture.trust,
            release_proof_authority=fixture.trust["RELEASE_PROOF"],
            release_proof_private_key=fixture.keys["RELEASE_PROOF"],
            trusted_now_ms=lambda: NOW_MS,
        )


def test_release_evidence_rejects_expired_organ_receipt() -> None:
    fixture = _build_evidence()

    with pytest.raises(ReleaseEvidenceError, match="organ_time_window_invalid"):
        _validate(fixture, now_ms=EXPIRES_MS)


def test_release_evidence_rejects_unsigned_receipt_tamper() -> None:
    fixture = _build_evidence()
    receipt = dict(fixture.evidence.organ_receipts[0])
    payload = dict(receipt["payload"])
    payload["purpose"] = "tampered-purpose"
    receipt["payload"] = payload
    receipts = list(fixture.evidence.organ_receipts)
    receipts[0] = receipt
    tampered = replace(fixture.evidence, organ_receipts=tuple(receipts))

    with pytest.raises(ReleaseEvidenceError, match="signed_component_payload_hash_mismatch"):
        _validate(fixture, tampered)


@pytest.mark.parametrize(
    ("field_name", "substituted_value"),
    [
        ("purpose", "different-purpose"),
        ("star_commitment", _digest("substituted-star")),
    ],
)
def test_release_evidence_rejects_resigned_organ_join_mismatch(
    field_name: str,
    substituted_value: str,
) -> None:
    fixture = _build_evidence()
    receipt = fixture.receipts[0]
    payload = dict(receipt["payload"])
    payload[field_name] = substituted_value
    resigned = sign_component_v02(
        component_type="POST_STAR_ORGAN_RECEIPT",
        authority=fixture.trust["SOURCE"],
        payload=payload,
        private_key=fixture.keys["SOURCE"],
    )
    receipts = list(fixture.receipts)
    receipts[0] = resigned

    with pytest.raises(ReleaseEvidenceError, match=f"organ_join_mismatch_{field_name}"):
        assemble_release_evidence_v02(
            organ_receipts=receipts,
            trust=fixture.trust,
            release_proof_authority=fixture.trust["RELEASE_PROOF"],
            release_proof_private_key=fixture.keys["RELEASE_PROOF"],
            trusted_now_ms=lambda: NOW_MS,
        )


def test_release_evidence_rejects_resigned_organ_with_removed_star_join() -> None:
    fixture = _build_evidence()
    payload = dict(fixture.receipts[0]["payload"])
    payload.pop("star_commitment")
    resigned = sign_component_v02(
        component_type="POST_STAR_ORGAN_RECEIPT",
        authority=fixture.trust["SOURCE"],
        payload=payload,
        private_key=fixture.keys["SOURCE"],
    )
    receipts = list(fixture.receipts)
    receipts[0] = resigned

    with pytest.raises(ReleaseEvidenceError, match="organ_receipt_profile_or_shape_invalid"):
        assemble_release_evidence_v02(
            organ_receipts=receipts,
            trust=fixture.trust,
            release_proof_authority=fixture.trust["RELEASE_PROOF"],
            release_proof_private_key=fixture.keys["RELEASE_PROOF"],
            trusted_now_ms=lambda: NOW_MS,
        )


def test_release_evidence_rejects_tampered_or_resigned_false_release_proof() -> None:
    fixture = _build_evidence()
    unsigned_tamper = dict(fixture.evidence.release_proof)
    unsigned_tamper["signature_hex"] = _flip_hex(unsigned_tamper["signature_hex"])
    with pytest.raises(ReleaseEvidenceError, match="signed_component_signature_invalid"):
        _validate(fixture, replace(fixture.evidence, release_proof=unsigned_tamper))

    payload = dict(fixture.evidence.release_proof["payload"])
    commitments = list(payload["organ_commitments"])
    commitments[0] = _digest("forged-organ")
    payload["organ_commitments"] = commitments
    resigned = sign_component_v02(
        component_type="RELEASE_PROOF",
        authority=fixture.trust["RELEASE_PROOF"],
        payload=payload,
        private_key=fixture.keys["RELEASE_PROOF"],
    )
    with pytest.raises(ReleaseEvidenceError, match="release_proof_organ_join_mismatch"):
        _validate(fixture, replace(fixture.evidence, release_proof=resigned))
