"""Machine-validated Magic Star evidence for the Aureon Plumber v0.2 lab path.

Geometry, the Rainbow and EPAS labels are authenticated public context.  They
are never entropy, nonces, shares, liveness evidence or release authority.
Ed25519 signatures from verifier-enrolled, distinct authorities carry the
authority in this module.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.harmonic.rainbow_reference import rainbow_json, verify_rainbow

from .crypto import domain_hash, ed25519_public_key_hex, sha256_hex, sign_ed25519, verify_ed25519
from .receipts import RECEIPT_SCHEMA, ReceiptKind, ReceiptVerdict, SignedReceipt
from .schema import freeze_mapping, parse_timestamp, thaw_json

PROTOCOL_ID = "AUREON_PLUMBER_V0_2_MAGIC_STAR"
PROFILE_ID = "AUREON_PLUMBER_MAGIC_STAR_POLICY_V0_2"
SOURCE_PROFILE_COMMITMENT = "8a263a1af1067fb997eefeeff4c2beec43a8fad83bab9338a1b5a2cc8c0d9935"
COMPONENT_SCHEMA = "aureon.plumber.magic-star.signed-component.v02"
STAR_SCHEMA = "aureon.plumber.magic-star.v02"
COMPONENT_SIGNING_DOMAIN = "MAGIC-STAR-V0.2"

POINTS: tuple[Mapping[str, Any], ...] = (
    MappingProxyType({"index": 0, "lens": "Hexahedron", "element": "Earth", "role": "SOURCE"}),
    MappingProxyType({"index": 1, "lens": "Icosahedron", "element": "Water", "role": "OBSERVER"}),
    MappingProxyType({"index": 2, "lens": "Octahedron", "element": "Air", "role": "CONSCIENCE"}),
    MappingProxyType({"index": 3, "lens": "Dodecahedron", "element": "Ether", "role": "GOVERNANCE"}),
    MappingProxyType({"index": 4, "lens": "Tetrahedron", "element": "Fire", "role": "OPERATOR"}),
)
POINT_ROLES: tuple[str, ...] = tuple(str(point["role"]) for point in POINTS)
PENTAGRAM_ROUTE: tuple[tuple[int, int], ...] = ((0, 2), (2, 4), (4, 1), (1, 3), (3, 0))
RAINBOW_FREQUENCIES: tuple[str, ...] = (
    "7.83",
    "174",
    "285",
    "396",
    "417",
    "528",
    "639",
    "741",
    "852",
    "963",
)
STAR_AUTHORITY_ROLES = (*POINT_ROLES, "EPAS", "HEART", "STAR_SEAL")

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_KEY = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE = re.compile(r"^[0-9a-f]{128}$")


PROFILE_DESCRIPTOR: Mapping[str, Any] = MappingProxyType({
    "protocol_id": PROTOCOL_ID,
    "profile_id": PROFILE_ID,
    "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
    "points": POINTS,
    "pentagram_route": PENTAGRAM_ROUTE,
    "rainbow_frequencies": RAINBOW_FREQUENCIES,
    "heart_frequency": "528",
    "heart_receipt_schema": RECEIPT_SCHEMA,
    "heart_receipt_kind": str(ReceiptKind.HEART),
    "heart_receipt_bridge_required": True,
    "point_verdict_required": "APPROVE",
    "cryptographic_carriers": ("AES-256-GCM", "HKDF-SHA256", "Ed25519", "SHA-256"),
    "public_context_is_not_entropy": True,
    "production_ready": False,
})
IMPLEMENTATION_PROFILE_SHA256 = domain_hash(
    "AUREON-PLUMBER-V02-IMPLEMENTATION-PROFILE", PROFILE_DESCRIPTOR
)
RAINBOW_SOURCE_SHA256 = sha256_hex(rainbow_json())
_MAX_COMPONENT_TTL_MS = 5 * 60 * 1000
_UTC_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_EPAS_FIELDS = {
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "release_context_sha256",
    "source_lineage_sha256",
    "evidence_sha256",
    "evidence_class",
    "previous_memory_head_sha256",
    "memory_epoch",
    "verdict",
    "outcome",
    "issued_at_ms",
    "expires_at_ms",
    "physical_effects_claimed",
}
_HEART_FIELDS = {
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "release_context_sha256",
    "packet_id",
    "packet_commitment",
    "session_id",
    "purpose",
    "source_identity_commitment",
    "temporal_commitment",
    "observer_commitment",
    "policy_commitment",
    "runtime_measurement_sha256",
    "heart_receipt",
    "heart_receipt_commitment",
    "verdict",
    "issued_at_ms",
    "expires_at_ms",
    "heart_frequency",
}
_POINT_FIELDS = {
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "implementation_profile_sha256",
    "index",
    "lens",
    "element",
    "role",
    "release_context_sha256",
    "candidate_center_sha256",
    "evidence_sha256",
    "share_binding_sha256",
    "rainbow_source_sha256",
    "verdict",
    "issued_at_ms",
    "expires_at_ms",
}
_SEAL_FIELDS = {
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "implementation_profile_sha256",
    "release_context_sha256",
    "candidate_center_sha256",
    "epas_commitment",
    "heart_commitment",
    "point_commitments",
    "edges",
    "rainbow_chain",
    "formation_sha256",
    "all_five_required",
    "four_of_five_denied",
    "sealed_at_ms",
}


class MagicStarError(ValueError):
    """A stable fail-closed Magic Star validation error."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _identifier(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise MagicStarError(code)
    return value


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise MagicStarError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MagicStarError(code)
    return value


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _datetime_from_epoch_ms(value: object, *, code: str) -> datetime:
    milliseconds = _uint(value, code=code)
    try:
        return _UTC_EPOCH + timedelta(milliseconds=milliseconds)
    except OverflowError as exc:
        raise MagicStarError(code) from exc


def _timestamp_to_epoch_ms(value: object, *, code: str) -> int:
    try:
        parsed = parse_timestamp(value, field=code)
        elapsed = parsed - _UTC_EPOCH
    except (OverflowError, TypeError, ValueError) as exc:
        raise MagicStarError(code) from exc
    return (
        elapsed.days * 86_400_000
        + elapsed.seconds * 1_000
        + elapsed.microseconds // 1_000
    )


def heart_receipt_commitment_v02(receipt: SignedReceipt) -> str:
    """Commit the complete signed v0 Heart receipt, including its signature."""

    if not isinstance(receipt, SignedReceipt):
        raise MagicStarError("heart_receipt_type_invalid")
    return domain_hash("AUREON-PLUMBER-V02-HEART-RECEIPT", receipt.to_dict())


def build_heart_source_identity_commitment_v02(
    *,
    source_authority: AuthorityBindingV02,
    packet_id: str,
    packet_commitment: str,
    source_signature_commitment: str,
) -> str:
    """Bind the v0 Heart receipt to the exact source-signed v0.2 packet."""

    if not isinstance(source_authority, AuthorityBindingV02) or source_authority.role != "SOURCE":
        raise MagicStarError("heart_source_authority_invalid")
    return domain_hash(
        "AUREON-PLUMBER-V02-HEART-SOURCE-IDENTITY",
        {
            "protocol_id": PROTOCOL_ID,
            "profile_id": PROFILE_ID,
            "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
            "packet_id": _identifier(packet_id, code="packet_id_invalid"),
            "packet_commitment": _sha256(
                packet_commitment, code="packet_commitment_invalid"
            ),
            "source_signature_commitment": _sha256(
                source_signature_commitment,
                code="source_signature_commitment_invalid",
            ),
            "source_authority": source_authority.public_dict(),
        },
    )


def _profile_public() -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "points": [dict(point) for point in POINTS],
        "pentagram_route": [list(edge) for edge in PENTAGRAM_ROUTE],
        "rainbow_frequencies": list(RAINBOW_FREQUENCIES),
        "heart_frequency": "528",
        "heart_receipt_schema": RECEIPT_SCHEMA,
        "heart_receipt_kind": str(ReceiptKind.HEART),
        "heart_receipt_bridge_required": True,
        "point_verdict_required": "APPROVE",
        "cryptographic_carriers": ["AES-256-GCM", "HKDF-SHA256", "Ed25519", "SHA-256"],
        "public_context_is_not_entropy": True,
        "production_ready": False,
    }


def _require_profile_and_shape(payload: Mapping[str, Any], fields: set[str], *, code: str) -> None:
    if set(payload) != fields or any(
        payload.get(key) != value
        for key, value in {
            "protocol_id": PROTOCOL_ID,
            "profile_id": PROFILE_ID,
            "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        }.items()
    ):
        raise MagicStarError(code)


def _validate_window(payload: Mapping[str, Any], *, now: int, prefix: str) -> None:
    issued = _uint(payload.get("issued_at_ms"), code=f"{prefix}_issued_at_invalid")
    expires = _uint(payload.get("expires_at_ms"), code=f"{prefix}_expires_at_invalid")
    if issued > now or expires <= now or expires <= issued or expires - issued > _MAX_COMPONENT_TTL_MS:
        raise MagicStarError(f"{prefix}_time_window_invalid")


@dataclass(frozen=True, slots=True)
class AuthorityBindingV02:
    role: str
    issuer: str
    principal: str
    key_id: str
    public_key_hex: str

    def __post_init__(self) -> None:
        if self.role not in STAR_AUTHORITY_ROLES and self.role not in {
            "COHERENCE",
            "CONTINUITY",
            "AUTHORIZATION",
            "CUSTODY",
            "CAPABILITY_RECEIPT",
            "RELEASE_PROOF",
        }:
            raise MagicStarError("authority_role_invalid")
        _identifier(self.issuer, code="authority_issuer_invalid")
        _identifier(self.principal, code="authority_principal_invalid")
        _identifier(self.key_id, code="authority_key_id_invalid")
        if not isinstance(self.public_key_hex, str) or _PUBLIC_KEY.fullmatch(self.public_key_hex) is None:
            raise MagicStarError("authority_public_key_invalid")

    def public_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "issuer": self.issuer,
            "principal": self.principal,
            "key_id": self.key_id,
            "public_key_hex": self.public_key_hex,
        }


def build_authority_binding_v02(
    *,
    role: str,
    issuer: str,
    principal: str,
    key_id: str,
    private_key: Ed25519PrivateKey,
) -> AuthorityBindingV02:
    return AuthorityBindingV02(
        role=role,
        issuer=issuer,
        principal=principal,
        key_id=key_id,
        public_key_hex=ed25519_public_key_hex(private_key),
    )


def validate_distinct_authorities_v02(
    trust: Mapping[str, AuthorityBindingV02],
    *,
    required_roles: Sequence[str],
) -> None:
    if set(trust) != set(required_roles):
        raise MagicStarError("authority_role_set_incomplete")
    bindings = [trust[role] for role in required_roles]
    for role, binding in zip(required_roles, bindings, strict=True):
        if not isinstance(binding, AuthorityBindingV02) or binding.role != role:
            raise MagicStarError("authority_role_binding_mismatch")
    for attribute, code in (
        ("public_key_hex", "authority_keys_not_distinct"),
        ("key_id", "authority_key_ids_not_distinct"),
        ("principal", "authority_principals_not_distinct"),
        ("issuer", "authority_issuers_not_distinct"),
    ):
        values = [getattr(binding, attribute) for binding in bindings]
        if len(set(values)) != len(values):
            raise MagicStarError(code)


def _component_unsigned(
    *,
    component_type: str,
    authority: AuthorityBindingV02,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    component = _identifier(component_type, code="component_type_invalid")
    body = dict(payload)
    return {
        "schema": COMPONENT_SCHEMA,
        "component_type": component,
        "authority": authority.public_dict(),
        "payload": body,
        "payload_sha256": domain_hash(f"AUREON-PLUMBER-V02-{component}", body),
    }


def sign_component_v02(
    *,
    component_type: str,
    authority: AuthorityBindingV02,
    payload: Mapping[str, Any],
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if ed25519_public_key_hex(private_key) != authority.public_key_hex:
        raise MagicStarError("component_signer_key_mismatch")
    unsigned = _component_unsigned(
        component_type=component_type,
        authority=authority,
        payload=payload,
    )
    return {
        **unsigned,
        "signature_hex": sign_ed25519(
            private_key,
            unsigned,
            domain=f"{COMPONENT_SIGNING_DOMAIN}:{component_type}",
        ),
    }


def component_commitment_v02(component: Mapping[str, Any]) -> str:
    return domain_hash("AUREON-PLUMBER-V02-SIGNED-COMPONENT", dict(component))


def verify_component_v02(
    component: Mapping[str, Any],
    *,
    expected_type: str,
    expected_authority: AuthorityBindingV02,
) -> dict[str, Any]:
    exact_fields = {
        "schema",
        "component_type",
        "authority",
        "payload",
        "payload_sha256",
        "signature_hex",
    }
    if not isinstance(component, Mapping) or set(component) != exact_fields:
        raise MagicStarError("signed_component_shape_invalid")
    if component.get("schema") != COMPONENT_SCHEMA or component.get("component_type") != expected_type:
        raise MagicStarError("signed_component_schema_or_type_mismatch")
    if component.get("authority") != expected_authority.public_dict():
        raise MagicStarError("signed_component_authority_mismatch")
    payload = component.get("payload")
    if not isinstance(payload, Mapping):
        raise MagicStarError("signed_component_payload_invalid")
    unsigned = _component_unsigned(
        component_type=expected_type,
        authority=expected_authority,
        payload=payload,
    )
    if component.get("payload_sha256") != unsigned["payload_sha256"]:
        raise MagicStarError("signed_component_payload_hash_mismatch")
    signature = component.get("signature_hex")
    if not isinstance(signature, str) or _SIGNATURE.fullmatch(signature) is None:
        raise MagicStarError("signed_component_signature_invalid")
    if not verify_ed25519(
        expected_authority.public_key_hex,
        unsigned,
        signature,
        domain=f"{COMPONENT_SIGNING_DOMAIN}:{expected_type}",
    ):
        raise MagicStarError("signed_component_signature_invalid")
    return {key: thaw_json(value) for key, value in payload.items()}


def _validate_heart_receipt_bridge(
    payload: Mapping[str, Any],
    *,
    authority: AuthorityBindingV02,
    trusted_now_ms: int,
) -> SignedReceipt:
    receipt_value = payload.get("heart_receipt")
    if not isinstance(receipt_value, Mapping):
        raise MagicStarError("heart_receipt_schema_invalid")
    try:
        receipt = SignedReceipt.from_dict(receipt_value)
    except (TypeError, ValueError) as exc:
        raise MagicStarError("heart_receipt_schema_invalid") from exc
    if receipt.kind != str(ReceiptKind.HEART):
        raise MagicStarError("heart_receipt_kind_invalid")
    if receipt.verdict != str(ReceiptVerdict.APPROVED):
        raise MagicStarError("heart_receipt_verdict_invalid")
    if (
        receipt.signer_public_key != authority.public_key_hex
        or receipt.signer_id != authority.principal
    ):
        raise MagicStarError("heart_receipt_authority_mismatch")

    packet_id = _identifier(payload.get("packet_id"), code="packet_id_invalid")
    session_id = _identifier(payload.get("session_id"), code="session_id_invalid")
    purpose = _identifier(payload.get("purpose"), code="purpose_invalid")
    source_identity = _sha256(
        payload.get("source_identity_commitment"),
        code="heart_source_identity_commitment_invalid",
    )
    temporal = _sha256(
        payload.get("temporal_commitment"), code="temporal_commitment_invalid"
    )
    observer = _sha256(
        payload.get("observer_commitment"), code="observer_commitment_invalid"
    )
    policy = _sha256(
        payload.get("policy_commitment"), code="heart_policy_commitment_invalid"
    )
    runtime = _sha256(
        payload.get("runtime_measurement_sha256"),
        code="runtime_measurement_invalid",
    )
    expected_receipt_fields = {
        "packet_identity": packet_id,
        "session_identity": session_id,
        "purpose_commitment": domain_hash("aureon.plumber.purpose.v0", purpose),
        "source_identity_commitment": source_identity,
        "temporal_identity_commitment": temporal,
        "observer_transcript_commitment": observer,
        "policy_commitment": policy,
        "runtime_measurement_commitment": runtime,
    }
    if any(
        getattr(receipt, field) != value
        for field, value in expected_receipt_fields.items()
    ):
        raise MagicStarError("heart_receipt_binding_mismatch")
    if payload.get("verdict") != "APPROVE" or payload.get("heart_frequency") != "528":
        raise MagicStarError("heart_precondition_denied")
    if payload.get("heart_receipt_commitment") != heart_receipt_commitment_v02(receipt):
        raise MagicStarError("heart_receipt_commitment_mismatch")

    receipt_issued_ms = _timestamp_to_epoch_ms(
        receipt.issued_at, code="heart_receipt_issued_at_invalid"
    )
    receipt_expires_ms = _timestamp_to_epoch_ms(
        receipt.expires_at, code="heart_receipt_expires_at_invalid"
    )
    if (
        payload.get("issued_at_ms") != receipt_issued_ms
        or payload.get("expires_at_ms") != receipt_expires_ms
    ):
        raise MagicStarError("heart_receipt_time_join_mismatch")
    validation = receipt.validate(
        now=_datetime_from_epoch_ms(
            trusted_now_ms, code="heart_receipt_trusted_time_invalid"
        ),
        expected_packet_identity=packet_id,
        expected_session_identity=session_id,
        expected_purpose_commitment=expected_receipt_fields["purpose_commitment"],
        expected_signer_public_key=authority.public_key_hex,
        require_approved=True,
    )
    if not validation.valid:
        if any(code in {"future_state", "stale_state"} for code in validation.denial_codes):
            raise MagicStarError("heart_receipt_time_window_invalid")
        raise MagicStarError("heart_receipt_validation_failed")
    return receipt


def build_epas_precondition_v02(
    *,
    release_context_sha256: str,
    source_lineage_sha256: str,
    evidence_sha256: str,
    evidence_class: str,
    previous_memory_head_sha256: str,
    memory_epoch: int,
    verdict: str,
    outcome: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if authority.role != "EPAS":
        raise MagicStarError("epas_authority_role_invalid")
    payload: dict[str, Any] = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "release_context_sha256": _sha256(release_context_sha256, code="release_context_invalid"),
        "source_lineage_sha256": _sha256(source_lineage_sha256, code="source_lineage_invalid"),
        "evidence_sha256": _sha256(evidence_sha256, code="epas_evidence_invalid"),
        "evidence_class": _identifier(evidence_class, code="epas_evidence_class_invalid"),
        "previous_memory_head_sha256": _sha256(
            previous_memory_head_sha256, code="epas_memory_head_invalid"
        ),
        "memory_epoch": _uint(memory_epoch, code="epas_memory_epoch_invalid"),
        "verdict": str(verdict),
        "outcome": str(outcome),
        "issued_at_ms": _uint(issued_at_ms, code="epas_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="epas_expires_at_invalid"),
        "physical_effects_claimed": False,
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise MagicStarError("epas_time_window_invalid")
    return sign_component_v02(
        component_type="EPAS_PRECONDITION",
        authority=authority,
        payload=payload,
        private_key=private_key,
    )


def build_heart_precondition_v02(
    *,
    release_context_sha256: str,
    packet_id: str,
    packet_commitment: str,
    session_id: str,
    purpose: str,
    temporal_commitment: str,
    observer_commitment: str,
    runtime_measurement_sha256: str,
    heart_receipt: SignedReceipt,
    verdict: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if authority.role != "HEART":
        raise MagicStarError("heart_authority_role_invalid")
    if not isinstance(heart_receipt, SignedReceipt):
        raise MagicStarError("heart_receipt_type_invalid")
    payload: dict[str, Any] = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "release_context_sha256": _sha256(release_context_sha256, code="release_context_invalid"),
        "packet_id": _identifier(packet_id, code="packet_id_invalid"),
        "packet_commitment": _sha256(packet_commitment, code="packet_commitment_invalid"),
        "session_id": _identifier(session_id, code="session_id_invalid"),
        "purpose": _identifier(purpose, code="purpose_invalid"),
        "source_identity_commitment": heart_receipt.source_identity_commitment,
        "temporal_commitment": _sha256(temporal_commitment, code="temporal_commitment_invalid"),
        "observer_commitment": _sha256(observer_commitment, code="observer_commitment_invalid"),
        "policy_commitment": heart_receipt.policy_commitment,
        "runtime_measurement_sha256": _sha256(
            runtime_measurement_sha256, code="runtime_measurement_invalid"
        ),
        "heart_receipt": heart_receipt.to_dict(),
        "heart_receipt_commitment": heart_receipt_commitment_v02(heart_receipt),
        "verdict": str(verdict),
        "issued_at_ms": _uint(issued_at_ms, code="heart_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="heart_expires_at_invalid"),
        "heart_frequency": "528",
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise MagicStarError("heart_time_window_invalid")
    _require_profile_and_shape(
        payload, _HEART_FIELDS, code="heart_precondition_profile_or_shape_invalid"
    )
    _validate_window(
        payload,
        now=_uint(payload["issued_at_ms"], code="heart_issued_at_invalid"),
        prefix="heart",
    )
    _validate_heart_receipt_bridge(
        payload,
        authority=authority,
        trusted_now_ms=_uint(
            payload["issued_at_ms"], code="heart_issued_at_invalid"
        ),
    )
    return sign_component_v02(
        component_type="HEART_PRECONDITION",
        authority=authority,
        payload=payload,
        private_key=private_key,
    )


def build_candidate_center_v02(
    *,
    release_context_sha256: str,
    packet_commitment: str,
    recipient_proof_commitment: str,
    purpose: str,
    temporal_commitment: str,
    observer_commitment: str,
    epas_commitment: str,
    heart_commitment: str,
) -> str:
    return domain_hash(
        "AUREON-PLUMBER-V02-CANDIDATE-CENTER",
        {
            "protocol_id": PROTOCOL_ID,
            "profile_id": PROFILE_ID,
            "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
            "release_context_sha256": _sha256(
                release_context_sha256, code="release_context_invalid"
            ),
            "packet_commitment": _sha256(packet_commitment, code="packet_commitment_invalid"),
            "recipient_proof_commitment": _sha256(
                recipient_proof_commitment, code="recipient_proof_commitment_invalid"
            ),
            "purpose": _identifier(purpose, code="purpose_invalid"),
            "temporal_commitment": _sha256(
                temporal_commitment, code="temporal_commitment_invalid"
            ),
            "observer_commitment": _sha256(
                observer_commitment, code="observer_commitment_invalid"
            ),
            "epas_commitment": _sha256(epas_commitment, code="epas_commitment_invalid"),
            "heart_commitment": _sha256(heart_commitment, code="heart_commitment_invalid"),
        },
    )


def build_magic_star_point_v02(
    *,
    index: int,
    release_context_sha256: str,
    candidate_center_sha256: str,
    evidence_sha256: str,
    share_binding_sha256: str,
    verdict: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    point_index = _uint(index, code="star_point_index_invalid")
    if point_index >= len(POINTS):
        raise MagicStarError("star_point_index_invalid")
    definition = POINTS[point_index]
    if authority.role != definition["role"]:
        raise MagicStarError("star_point_authority_role_mismatch")
    point_verdict = str(verdict)
    if point_verdict not in {"APPROVE", "VETO"}:
        raise MagicStarError("star_point_verdict_invalid")
    payload: dict[str, Any] = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "implementation_profile_sha256": IMPLEMENTATION_PROFILE_SHA256,
        **definition,
        "release_context_sha256": _sha256(release_context_sha256, code="release_context_invalid"),
        "candidate_center_sha256": _sha256(
            candidate_center_sha256, code="candidate_center_invalid"
        ),
        "evidence_sha256": _sha256(evidence_sha256, code="star_point_evidence_invalid"),
        "share_binding_sha256": _sha256(
            share_binding_sha256, code="star_point_share_binding_invalid"
        ),
        "rainbow_source_sha256": RAINBOW_SOURCE_SHA256,
        "verdict": point_verdict,
        "issued_at_ms": _uint(issued_at_ms, code="star_point_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="star_point_expires_at_invalid"),
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise MagicStarError("star_point_time_window_invalid")
    return sign_component_v02(
        component_type="MAGIC_STAR_POINT",
        authority=authority,
        payload=payload,
        private_key=private_key,
    )


def _rainbow_chain(release_context_sha256: str, candidate_center_sha256: str) -> dict[str, Any]:
    previous = domain_hash(
        "AUREON-PLUMBER-V02-RAINBOW-SEED",
        {
            "release_context_sha256": release_context_sha256,
            "candidate_center_sha256": candidate_center_sha256,
            "rainbow_source_sha256": RAINBOW_SOURCE_SHA256,
        },
    )
    rungs: list[dict[str, Any]] = []
    for index, frequency in enumerate(RAINBOW_FREQUENCIES):
        current = domain_hash(
            "AUREON-PLUMBER-V02-RAINBOW-RUNG",
            {
                "index": index,
                "frequency_hz": frequency,
                "previous_sha256": previous,
                "release_context_sha256": release_context_sha256,
                "candidate_center_sha256": candidate_center_sha256,
            },
        )
        rungs.append(
            {
                "index": index,
                "frequency_hz": frequency,
                "previous_sha256": previous,
                "commitment": current,
            }
        )
        previous = current
    return {"rungs": rungs, "terminal_sha256": previous}


@dataclass(frozen=True, slots=True)
class MagicStarV02:
    schema: str
    profile: Mapping[str, Any]
    epas_precondition: Mapping[str, Any]
    heart_precondition: Mapping[str, Any]
    points: tuple[Mapping[str, Any], ...]
    seal: Mapping[str, Any]

    def __post_init__(self) -> None:
        for field_name in ("profile", "epas_precondition", "heart_precondition", "seal"):
            object.__setattr__(
                self,
                field_name,
                freeze_mapping(getattr(self, field_name), field=field_name),
            )
        object.__setattr__(
            self,
            "points",
            tuple(
                freeze_mapping(point, field=f"points[{index}]")
                for index, point in enumerate(self.points)
            ),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "profile": thaw_json(self.profile),
            "epas_precondition": thaw_json(self.epas_precondition),
            "heart_precondition": thaw_json(self.heart_precondition),
            "points": [thaw_json(point) for point in self.points],
            "seal": thaw_json(self.seal),
        }

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V02-MAGIC-STAR", self.public_dict())


def assemble_magic_star_v02(
    *,
    release_context_sha256: str,
    candidate_center_sha256: str,
    epas_precondition: Mapping[str, Any],
    heart_precondition: Mapping[str, Any],
    points: Sequence[Mapping[str, Any]],
    trust: Mapping[str, AuthorityBindingV02],
    seal_authority: AuthorityBindingV02,
    seal_private_key: Ed25519PrivateKey,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> MagicStarV02:
    validate_distinct_authorities_v02(trust, required_roles=STAR_AUTHORITY_ROLES)
    if trust["STAR_SEAL"] != seal_authority:
        raise MagicStarError("star_seal_authority_mismatch")
    context = _sha256(release_context_sha256, code="release_context_invalid")
    center = _sha256(candidate_center_sha256, code="candidate_center_invalid")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")

    epas_payload = verify_component_v02(
        epas_precondition,
        expected_type="EPAS_PRECONDITION",
        expected_authority=trust["EPAS"],
    )
    heart_payload = verify_component_v02(
        heart_precondition,
        expected_type="HEART_PRECONDITION",
        expected_authority=trust["HEART"],
    )
    _require_profile_and_shape(
        epas_payload, _EPAS_FIELDS, code="epas_precondition_profile_or_shape_invalid"
    )
    _require_profile_and_shape(
        heart_payload, _HEART_FIELDS, code="heart_precondition_profile_or_shape_invalid"
    )
    _validate_window(epas_payload, now=now, prefix="epas")
    _validate_window(heart_payload, now=now, prefix="heart")
    _validate_heart_receipt_bridge(
        heart_payload,
        authority=trust["HEART"],
        trusted_now_ms=now,
    )
    if (
        epas_payload.get("release_context_sha256") != context
        or epas_payload.get("verdict") != "CLEAR"
        or epas_payload.get("outcome") != "PROCEED"
        or epas_payload.get("physical_effects_claimed") is not False
    ):
        raise MagicStarError("epas_precondition_denied")
    if heart_payload.get("release_context_sha256") != context or heart_payload.get("verdict") != "APPROVE":
        raise MagicStarError("heart_precondition_denied")

    if len(points) != len(POINTS):
        raise MagicStarError("all_five_star_points_required")
    point_components: list[dict[str, Any]] = []
    point_payloads: list[dict[str, Any]] = []
    for index, supplied in enumerate(points):
        payload = verify_component_v02(
            supplied,
            expected_type="MAGIC_STAR_POINT",
            expected_authority=trust[POINTS[index]["role"]],
        )
        _require_profile_and_shape(
            payload, _POINT_FIELDS, code="star_point_profile_or_shape_invalid"
        )
        _validate_window(payload, now=now, prefix="star_point")
        if any(payload.get(key) != value for key, value in POINTS[index].items()):
            raise MagicStarError("star_point_definition_mismatch")
        if payload.get("verdict") != "APPROVE":
            raise MagicStarError("star_point_denied")
        if payload.get("release_context_sha256") != context or payload.get(
            "candidate_center_sha256"
        ) != center:
            raise MagicStarError("star_point_context_mismatch")
        point_components.append(dict(supplied))
        point_payloads.append(payload)

    point_commitments = [component_commitment_v02(point) for point in point_components]
    edges = [
        {
            "from": start,
            "to": end,
            "commitment": domain_hash(
                "AUREON-PLUMBER-V02-STAR-EDGE",
                {
                    "from": start,
                    "to": end,
                    "from_point": point_commitments[start],
                    "to_point": point_commitments[end],
                    "candidate_center_sha256": center,
                },
            ),
        }
        for start, end in PENTAGRAM_ROUTE
    ]
    rainbow = _rainbow_chain(context, center)
    formation_sha256 = domain_hash(
        "AUREON-PLUMBER-V02-STAR-FORMATION",
        {
            "point_commitments": point_commitments,
            "edges": edges,
            "rainbow_terminal_sha256": rainbow["terminal_sha256"],
            "epas_commitment": component_commitment_v02(epas_precondition),
            "heart_commitment": component_commitment_v02(heart_precondition),
            "release_context_sha256": context,
            "candidate_center_sha256": center,
        },
    )
    seal_payload = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "implementation_profile_sha256": IMPLEMENTATION_PROFILE_SHA256,
        "release_context_sha256": context,
        "candidate_center_sha256": center,
        "epas_commitment": component_commitment_v02(epas_precondition),
        "heart_commitment": component_commitment_v02(heart_precondition),
        "point_commitments": point_commitments,
        "edges": edges,
        "rainbow_chain": rainbow,
        "formation_sha256": formation_sha256,
        "all_five_required": True,
        "four_of_five_denied": True,
        "sealed_at_ms": now,
    }
    seal = sign_component_v02(
        component_type="MAGIC_STAR_SEAL",
        authority=seal_authority,
        payload=seal_payload,
        private_key=seal_private_key,
    )
    star = MagicStarV02(
        schema=STAR_SCHEMA,
        profile=_profile_public(),
        epas_precondition=dict(epas_precondition),
        heart_precondition=dict(heart_precondition),
        points=tuple(point_components),
        seal=seal,
    )
    validate_magic_star_v02(
        star,
        trust=trust,
        expected_release_context_sha256=context,
        expected_candidate_center_sha256=center,
        trusted_now_ms=trusted_now_ms,
    )
    return star


def validate_magic_star_v02(
    star: MagicStarV02,
    *,
    trust: Mapping[str, AuthorityBindingV02],
    expected_release_context_sha256: str,
    expected_candidate_center_sha256: str,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> dict[str, Any]:
    if not isinstance(star, MagicStarV02) or star.schema != STAR_SCHEMA:
        raise MagicStarError("magic_star_wire_schema_invalid")
    if thaw_json(star.profile) != _profile_public():
        raise MagicStarError("magic_star_profile_mismatch")
    validate_distinct_authorities_v02(trust, required_roles=STAR_AUTHORITY_ROLES)
    context = _sha256(expected_release_context_sha256, code="release_context_invalid")
    center = _sha256(expected_candidate_center_sha256, code="candidate_center_invalid")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")

    epas_payload = verify_component_v02(
        star.epas_precondition,
        expected_type="EPAS_PRECONDITION",
        expected_authority=trust["EPAS"],
    )
    heart_payload = verify_component_v02(
        star.heart_precondition,
        expected_type="HEART_PRECONDITION",
        expected_authority=trust["HEART"],
    )
    _require_profile_and_shape(
        epas_payload, _EPAS_FIELDS, code="epas_precondition_profile_or_shape_invalid"
    )
    _require_profile_and_shape(
        heart_payload, _HEART_FIELDS, code="heart_precondition_profile_or_shape_invalid"
    )
    _validate_window(epas_payload, now=now, prefix="epas")
    _validate_window(heart_payload, now=now, prefix="heart")
    heart_receipt = _validate_heart_receipt_bridge(
        heart_payload,
        authority=trust["HEART"],
        trusted_now_ms=now,
    )
    if (
        epas_payload.get("release_context_sha256") != context
        or epas_payload.get("verdict") != "CLEAR"
        or epas_payload.get("outcome") != "PROCEED"
        or epas_payload.get("physical_effects_claimed") is not False
    ):
        raise MagicStarError("epas_precondition_invalid")
    if (
        heart_payload.get("release_context_sha256") != context
        or heart_payload.get("verdict") != "APPROVE"
    ):
        raise MagicStarError("heart_precondition_invalid")
    if len(star.points) != len(POINTS):
        raise MagicStarError("all_five_star_points_required")
    point_commitments: list[str] = []
    for index, component in enumerate(star.points):
        payload = verify_component_v02(
            component,
            expected_type="MAGIC_STAR_POINT",
            expected_authority=trust[POINTS[index]["role"]],
        )
        _require_profile_and_shape(
            payload, _POINT_FIELDS, code="star_point_profile_or_shape_invalid"
        )
        _validate_window(payload, now=now, prefix="star_point")
        if any(payload.get(key) != value for key, value in POINTS[index].items()):
            raise MagicStarError("star_point_definition_mismatch")
        if payload.get("verdict") != "APPROVE":
            raise MagicStarError("star_point_denied")
        if payload.get("release_context_sha256") != context or payload.get(
            "candidate_center_sha256"
        ) != center:
            raise MagicStarError("star_point_context_mismatch")
        point_commitments.append(component_commitment_v02(component))

    seal_payload = verify_component_v02(
        star.seal,
        expected_type="MAGIC_STAR_SEAL",
        expected_authority=trust["STAR_SEAL"],
    )
    _require_profile_and_shape(
        seal_payload, _SEAL_FIELDS, code="magic_star_seal_profile_or_shape_invalid"
    )
    expected_edges = [
        {
            "from": start,
            "to": end,
            "commitment": domain_hash(
                "AUREON-PLUMBER-V02-STAR-EDGE",
                {
                    "from": start,
                    "to": end,
                    "from_point": point_commitments[start],
                    "to_point": point_commitments[end],
                    "candidate_center_sha256": center,
                },
            ),
        }
        for start, end in PENTAGRAM_ROUTE
    ]
    rainbow = _rainbow_chain(context, center)
    expected_formation = domain_hash(
        "AUREON-PLUMBER-V02-STAR-FORMATION",
        {
            "point_commitments": point_commitments,
            "edges": expected_edges,
            "rainbow_terminal_sha256": rainbow["terminal_sha256"],
            "epas_commitment": component_commitment_v02(star.epas_precondition),
            "heart_commitment": component_commitment_v02(star.heart_precondition),
            "release_context_sha256": context,
            "candidate_center_sha256": center,
        },
    )
    exact = {
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "implementation_profile_sha256": IMPLEMENTATION_PROFILE_SHA256,
        "release_context_sha256": context,
        "candidate_center_sha256": center,
        "epas_commitment": component_commitment_v02(star.epas_precondition),
        "heart_commitment": component_commitment_v02(star.heart_precondition),
        "point_commitments": point_commitments,
        "edges": expected_edges,
        "rainbow_chain": rainbow,
        "formation_sha256": expected_formation,
        "all_five_required": True,
        "four_of_five_denied": True,
    }
    if any(seal_payload.get(key) != value for key, value in exact.items()):
        raise MagicStarError("magic_star_seal_join_mismatch")
    sealed_at = _uint(seal_payload.get("sealed_at_ms"), code="magic_star_seal_time_invalid")
    latest_issued = max(
        _uint(epas_payload["issued_at_ms"], code="epas_issued_at_invalid"),
        _uint(heart_payload["issued_at_ms"], code="heart_issued_at_invalid"),
        *(
            _uint(
                verify_component_v02(
                    component,
                    expected_type="MAGIC_STAR_POINT",
                    expected_authority=trust[POINTS[index]["role"]],
                )["issued_at_ms"],
                code="star_point_issued_at_invalid",
            )
            for index, component in enumerate(star.points)
        ),
    )
    if sealed_at < latest_issued or sealed_at > now:
        raise MagicStarError("magic_star_seal_time_invalid")
    source_rainbow = verify_rainbow()
    if source_rainbow.get("consistent") is not True:
        raise MagicStarError("canonical_rainbow_source_inconsistent")
    return {
        "valid": True,
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "release_context_sha256": context,
        "candidate_center_sha256": center,
        "formation_sha256": expected_formation,
        "star_commitment": star.commitment,
        "heart_receipt_commitment": heart_receipt_commitment_v02(heart_receipt),
        "point_count": len(point_commitments),
        "expires_at_ms": min(
            _uint(epas_payload["expires_at_ms"], code="epas_expires_at_invalid"),
            _uint(heart_payload["expires_at_ms"], code="heart_expires_at_invalid"),
            *(
                _uint(
                    verify_component_v02(
                        component,
                        expected_type="MAGIC_STAR_POINT",
                        expected_authority=trust[POINTS[index]["role"]],
                    )["expires_at_ms"],
                    code="star_point_expires_at_invalid",
                )
                for index, component in enumerate(star.points)
            ),
        ),
        "production_ready": False,
    }


__all__ = [
    "AuthorityBindingV02",
    "IMPLEMENTATION_PROFILE_SHA256",
    "MagicStarError",
    "MagicStarV02",
    "PENTAGRAM_ROUTE",
    "POINTS",
    "POINT_ROLES",
    "PROFILE_DESCRIPTOR",
    "PROFILE_ID",
    "PROTOCOL_ID",
    "RAINBOW_FREQUENCIES",
    "RAINBOW_SOURCE_SHA256",
    "SOURCE_PROFILE_COMMITMENT",
    "STAR_AUTHORITY_ROLES",
    "assemble_magic_star_v02",
    "build_authority_binding_v02",
    "build_candidate_center_v02",
    "build_epas_precondition_v02",
    "build_heart_precondition_v02",
    "build_heart_source_identity_commitment_v02",
    "build_magic_star_point_v02",
    "component_commitment_v02",
    "heart_receipt_commitment_v02",
    "sign_component_v02",
    "validate_distinct_authorities_v02",
    "validate_magic_star_v02",
    "verify_component_v02",
]
