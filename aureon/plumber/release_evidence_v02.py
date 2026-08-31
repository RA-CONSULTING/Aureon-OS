"""Seven-organ post-Star evidence and release proof for Plumber v0.2."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .magic_star_v02 import (
    PROFILE_ID,
    PROTOCOL_ID,
    SOURCE_PROFILE_COMMITMENT,
    AuthorityBindingV02,
    MagicStarError,
    component_commitment_v02,
    sign_component_v02,
    verify_component_v02,
)
from .schema import freeze_mapping, thaw_json

RELEASE_EVIDENCE_SCHEMA = "aureon.plumber.magic-star.release-evidence.v02"
ORGAN_ROLES = (
    "SOURCE",
    "OBSERVER",
    "HEART",
    "COHERENCE",
    "CONSCIENCE",
    "GOVERNANCE",
    "OPERATOR",
)
RELEASE_EVIDENCE_ROLES = (*ORGAN_ROLES, "RELEASE_PROOF")
_MAX_COMPONENT_TTL_MS = 5 * 60 * 1000
_ORGAN_PAYLOAD_FIELDS = {
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "role",
    "packet_commitment",
    "session_id",
    "purpose",
    "release_context_sha256",
    "recipient_proof_commitment",
    "star_commitment",
    "epas_commitment",
    "live_binding_sha256",
    "runtime_measurement_sha256",
    "policy_measurement_sha256",
    "evidence_sha256",
    "verdict",
    "issued_at_ms",
    "expires_at_ms",
}
_RELEASE_PROOF_PAYLOAD_FIELDS = {
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "packet_commitment",
    "session_id",
    "purpose",
    "release_context_sha256",
    "recipient_proof_commitment",
    "star_commitment",
    "epas_commitment",
    "live_binding_sha256",
    "runtime_measurement_sha256",
    "policy_measurement_sha256",
    "organ_roles",
    "organ_commitments",
    "all_seven_required",
    "proof_issued_at_ms",
    "proof_expires_at_ms",
}


class ReleaseEvidenceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ReleaseEvidenceError(code)
    return value


def _identifier(value: object, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or any(not (c.isascii() and (c.isalnum() or c in "._:/-")) for c in value)
    ):
        raise ReleaseEvidenceError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReleaseEvidenceError(code)
    return value


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _validate_component_window(payload: Mapping[str, Any], *, now: int) -> None:
    issued = _uint(payload.get("issued_at_ms"), code="organ_issued_at_invalid")
    expires = _uint(payload.get("expires_at_ms"), code="organ_expires_at_invalid")
    if issued > now or expires <= now or expires <= issued or expires - issued > _MAX_COMPONENT_TTL_MS:
        raise ReleaseEvidenceError("organ_time_window_invalid")


def validate_release_evidence_trust_v02(
    trust: Mapping[str, AuthorityBindingV02],
) -> None:
    if set(trust) != set(RELEASE_EVIDENCE_ROLES):
        raise ReleaseEvidenceError("release_evidence_authority_set_incomplete")
    bindings = [trust[role] for role in RELEASE_EVIDENCE_ROLES]
    for role, binding in zip(RELEASE_EVIDENCE_ROLES, bindings, strict=True):
        if not isinstance(binding, AuthorityBindingV02) or binding.role != role:
            raise ReleaseEvidenceError("release_evidence_authority_binding_mismatch")
    for attribute, code in (
        ("public_key_hex", "release_evidence_keys_not_distinct"),
        ("key_id", "release_evidence_key_ids_not_distinct"),
        ("principal", "release_evidence_principals_not_distinct"),
        ("issuer", "release_evidence_issuers_not_distinct"),
    ):
        values = [getattr(binding, attribute) for binding in bindings]
        if len(set(values)) != len(values):
            raise ReleaseEvidenceError(code)


def build_organ_receipt_v02(
    *,
    role: str,
    packet_commitment: str,
    session_id: str,
    purpose: str,
    release_context_sha256: str,
    recipient_proof_commitment: str,
    star_commitment: str,
    epas_commitment: str,
    live_binding_sha256: str,
    runtime_measurement_sha256: str,
    policy_measurement_sha256: str,
    evidence_sha256: str,
    verdict: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if role not in ORGAN_ROLES or authority.role != role:
        raise ReleaseEvidenceError("organ_role_invalid")
    payload: dict[str, Any] = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "role": role,
        "packet_commitment": _sha256(packet_commitment, code="packet_commitment_invalid"),
        "session_id": _identifier(session_id, code="session_id_invalid"),
        "purpose": _identifier(purpose, code="purpose_invalid"),
        "release_context_sha256": _sha256(release_context_sha256, code="release_context_invalid"),
        "recipient_proof_commitment": _sha256(
            recipient_proof_commitment, code="recipient_proof_commitment_invalid"
        ),
        "star_commitment": _sha256(star_commitment, code="star_commitment_invalid"),
        "epas_commitment": _sha256(epas_commitment, code="epas_commitment_invalid"),
        "live_binding_sha256": _sha256(live_binding_sha256, code="live_binding_invalid"),
        "runtime_measurement_sha256": _sha256(
            runtime_measurement_sha256, code="runtime_measurement_invalid"
        ),
        "policy_measurement_sha256": _sha256(
            policy_measurement_sha256, code="policy_measurement_invalid"
        ),
        "evidence_sha256": _sha256(evidence_sha256, code="organ_evidence_invalid"),
        "verdict": str(verdict),
        "issued_at_ms": _uint(issued_at_ms, code="organ_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="organ_expires_at_invalid"),
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise ReleaseEvidenceError("organ_time_window_invalid")
    try:
        return sign_component_v02(
            component_type="POST_STAR_ORGAN_RECEIPT",
            authority=authority,
            payload=payload,
            private_key=private_key,
        )
    except MagicStarError as exc:
        raise ReleaseEvidenceError(exc.code) from exc


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceV02:
    schema: str
    organ_receipts: tuple[Mapping[str, Any], ...]
    release_proof: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "organ_receipts",
            tuple(
                freeze_mapping(receipt, field=f"organ_receipts[{index}]")
                for index, receipt in enumerate(self.organ_receipts)
            ),
        )
        object.__setattr__(
            self,
            "release_proof",
            freeze_mapping(self.release_proof, field="release_proof"),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "organ_receipts": [thaw_json(receipt) for receipt in self.organ_receipts],
            "release_proof": thaw_json(self.release_proof),
        }

    @property
    def commitment(self) -> str:
        from .crypto import domain_hash

        return domain_hash("AUREON-PLUMBER-V02-RELEASE-EVIDENCE", self.public_dict())


def assemble_release_evidence_v02(
    *,
    organ_receipts: Sequence[Mapping[str, Any]],
    trust: Mapping[str, AuthorityBindingV02],
    release_proof_authority: AuthorityBindingV02,
    release_proof_private_key: Ed25519PrivateKey,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> ReleaseEvidenceV02:
    validate_release_evidence_trust_v02(trust)
    if trust["RELEASE_PROOF"] != release_proof_authority:
        raise ReleaseEvidenceError("release_proof_authority_mismatch")
    if len(organ_receipts) != len(ORGAN_ROLES):
        raise ReleaseEvidenceError("all_seven_organ_receipts_required")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    payloads: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    for role, receipt in zip(ORGAN_ROLES, organ_receipts, strict=True):
        try:
            payload = verify_component_v02(
                receipt,
                expected_type="POST_STAR_ORGAN_RECEIPT",
                expected_authority=trust[role],
            )
        except MagicStarError as exc:
            raise ReleaseEvidenceError(exc.code) from exc
        if payload.get("role") != role:
            raise ReleaseEvidenceError("organ_receipt_order_or_role_mismatch")
        if set(payload) != _ORGAN_PAYLOAD_FIELDS or any(
            payload.get(key) != value
            for key, value in {
                "protocol_id": PROTOCOL_ID,
                "profile_id": PROFILE_ID,
                "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
            }.items()
        ):
            raise ReleaseEvidenceError("organ_receipt_profile_or_shape_invalid")
        if payload.get("verdict") != "APPROVE":
            raise ReleaseEvidenceError("organ_receipt_denied")
        _validate_component_window(payload, now=now)
        payloads.append(payload)
        components.append(dict(receipt))
    join_fields = (
        "packet_commitment",
        "session_id",
        "purpose",
        "release_context_sha256",
        "recipient_proof_commitment",
        "star_commitment",
        "epas_commitment",
        "live_binding_sha256",
        "runtime_measurement_sha256",
        "policy_measurement_sha256",
    )
    for field in join_fields:
        if len({payload[field] for payload in payloads}) != 1:
            raise ReleaseEvidenceError(f"organ_join_mismatch_{field}")
    proof_payload = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        **{field: payloads[0][field] for field in join_fields},
        "organ_roles": list(ORGAN_ROLES),
        "organ_commitments": [component_commitment_v02(component) for component in components],
        "all_seven_required": True,
        "proof_issued_at_ms": now,
        "proof_expires_at_ms": min(
            _uint(payload["expires_at_ms"], code="organ_expires_at_invalid") for payload in payloads
        ),
    }
    try:
        release_proof = sign_component_v02(
            component_type="RELEASE_PROOF",
            authority=release_proof_authority,
            payload=proof_payload,
            private_key=release_proof_private_key,
        )
    except MagicStarError as exc:
        raise ReleaseEvidenceError(exc.code) from exc
    evidence = ReleaseEvidenceV02(
        schema=RELEASE_EVIDENCE_SCHEMA,
        organ_receipts=tuple(components),
        release_proof=release_proof,
    )
    validate_release_evidence_v02(evidence, trust=trust, trusted_now_ms=trusted_now_ms)
    return evidence


def validate_release_evidence_v02(
    evidence: ReleaseEvidenceV02,
    *,
    trust: Mapping[str, AuthorityBindingV02],
    expected_evidence_sha256_by_role: Mapping[str, str] | None = None,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> dict[str, Any]:
    if not isinstance(evidence, ReleaseEvidenceV02) or evidence.schema != RELEASE_EVIDENCE_SCHEMA:
        raise ReleaseEvidenceError("release_evidence_schema_invalid")
    validate_release_evidence_trust_v02(trust)
    if len(evidence.organ_receipts) != len(ORGAN_ROLES):
        raise ReleaseEvidenceError("all_seven_organ_receipts_required")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    payloads: list[dict[str, Any]] = []
    commitments: list[str] = []
    for role, receipt in zip(ORGAN_ROLES, evidence.organ_receipts, strict=True):
        try:
            payload = verify_component_v02(
                receipt,
                expected_type="POST_STAR_ORGAN_RECEIPT",
                expected_authority=trust[role],
            )
        except MagicStarError as exc:
            raise ReleaseEvidenceError(exc.code) from exc
        if payload.get("role") != role:
            raise ReleaseEvidenceError("organ_receipt_order_or_role_mismatch")
        if set(payload) != _ORGAN_PAYLOAD_FIELDS or any(
            payload.get(key) != value
            for key, value in {
                "protocol_id": PROTOCOL_ID,
                "profile_id": PROFILE_ID,
                "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
            }.items()
        ):
            raise ReleaseEvidenceError("organ_receipt_profile_or_shape_invalid")
        if payload.get("verdict") != "APPROVE":
            raise ReleaseEvidenceError("organ_receipt_denied")
        _validate_component_window(payload, now=now)
        if expected_evidence_sha256_by_role is not None:
            if set(expected_evidence_sha256_by_role) != set(ORGAN_ROLES):
                raise ReleaseEvidenceError("expected_organ_evidence_set_invalid")
            expected_evidence = _sha256(
                expected_evidence_sha256_by_role[role],
                code="expected_organ_evidence_invalid",
            )
            if payload.get("evidence_sha256") != expected_evidence:
                raise ReleaseEvidenceError("organ_evidence_substitution_detected")
        payloads.append(payload)
        commitments.append(component_commitment_v02(receipt))
    try:
        proof = verify_component_v02(
            evidence.release_proof,
            expected_type="RELEASE_PROOF",
            expected_authority=trust["RELEASE_PROOF"],
        )
    except MagicStarError as exc:
        raise ReleaseEvidenceError(exc.code) from exc
    if set(proof) != _RELEASE_PROOF_PAYLOAD_FIELDS or any(
        proof.get(key) != value
        for key, value in {
            "protocol_id": PROTOCOL_ID,
            "profile_id": PROFILE_ID,
            "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        }.items()
    ):
        raise ReleaseEvidenceError("release_proof_profile_or_shape_invalid")
    join_fields = (
        "packet_commitment",
        "session_id",
        "purpose",
        "release_context_sha256",
        "recipient_proof_commitment",
        "star_commitment",
        "epas_commitment",
        "live_binding_sha256",
        "runtime_measurement_sha256",
        "policy_measurement_sha256",
    )
    for field in join_fields:
        expected = payloads[0].get(field)
        if any(payload.get(field) != expected for payload in payloads) or proof.get(field) != expected:
            raise ReleaseEvidenceError(f"release_proof_join_mismatch_{field}")
    if (
        proof.get("organ_roles") != list(ORGAN_ROLES)
        or proof.get("organ_commitments") != commitments
        or proof.get("all_seven_required") is not True
    ):
        raise ReleaseEvidenceError("release_proof_organ_join_mismatch")
    proof_issued = _uint(proof.get("proof_issued_at_ms"), code="release_proof_issued_at_invalid")
    proof_expires = _uint(proof.get("proof_expires_at_ms"), code="release_proof_expiry_invalid")
    expected_expiry = min(
        _uint(payload["expires_at_ms"], code="organ_expires_at_invalid")
        for payload in payloads
    )
    if proof_issued > now or proof_expires <= now or proof_expires != expected_expiry:
        raise ReleaseEvidenceError("release_proof_expired")
    return {
        "valid": True,
        **{field: proof[field] for field in join_fields},
        "release_proof_commitment": component_commitment_v02(evidence.release_proof),
        "release_evidence_commitment": evidence.commitment,
        "organ_count": len(ORGAN_ROLES),
        "expires_at_ms": proof_expires,
    }


__all__ = [
    "ORGAN_ROLES",
    "RELEASE_EVIDENCE_ROLES",
    "RELEASE_EVIDENCE_SCHEMA",
    "ReleaseEvidenceError",
    "ReleaseEvidenceV02",
    "assemble_release_evidence_v02",
    "build_organ_receipt_v02",
    "validate_release_evidence_trust_v02",
    "validate_release_evidence_v02",
]
