"""Continuity, authorization, five permits and custody join for v0.2."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import domain_hash
from .magic_star_v02 import (
    POINT_ROLES,
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

AUTHORIZATION_CHAIN_SCHEMA = "aureon.plumber.magic-star.authorization-chain.v02"
AUTHORIZATION_ROLES = ("CONTINUITY", "AUTHORIZATION", *POINT_ROLES, "CUSTODY")
_MAX_COMPONENT_TTL_MS = 5 * 60 * 1000
_PROFILE_FIELDS = {
    "protocol_id": PROTOCOL_ID,
    "profile_id": PROFILE_ID,
    "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
}
_CONTINUITY_FIELDS = {
    *_PROFILE_FIELDS,
    "packet_commitment",
    "session_id",
    "purpose",
    "star_commitment",
    "release_proof_commitment",
    "previous_decision_head_sha256",
    "revocation_epoch",
    "verdict",
    "issued_at_ms",
    "expires_at_ms",
}
_AUTHORIZATION_FIELDS = {
    *_PROFILE_FIELDS,
    "packet_commitment",
    "session_id",
    "purpose",
    "release_context_sha256",
    "recipient_proof_commitment",
    "star_commitment",
    "epas_commitment",
    "release_proof_commitment",
    "continuity_commitment",
    "live_binding_sha256",
    "runtime_measurement_sha256",
    "policy_measurement_sha256",
    "verdict",
    "issued_at_ms",
    "expires_at_ms",
}
_PERMIT_FIELDS = {
    *_PROFILE_FIELDS,
    "role",
    "packet_commitment",
    "session_id",
    "purpose",
    "authorization_commitment",
    "share_binding_sha256",
    "verdict",
    "issued_at_ms",
    "expires_at_ms",
}
_CUSTODY_FIELDS = {
    *_PROFILE_FIELDS,
    "packet_commitment",
    "session_id",
    "purpose",
    "star_commitment",
    "release_proof_commitment",
    "authorization_commitment",
    "permit_roles",
    "permit_commitments",
    "share_bindings",
    "all_five_required",
    "authorized_at_ms",
    "expires_at_ms",
}


class AuthorizationChainError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise AuthorizationChainError(code)
    return value


def _identifier(value: object, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or any(not (c.isascii() and (c.isalnum() or c in "._:/-")) for c in value)
    ):
        raise AuthorizationChainError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuthorizationChainError(code)
    return value


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _require_profile_and_shape(payload: Mapping[str, Any], fields: set[str], *, code: str) -> None:
    if set(payload) != fields or any(payload.get(key) != value for key, value in _PROFILE_FIELDS.items()):
        raise AuthorizationChainError(code)


def _validate_window(payload: Mapping[str, Any], *, now: int, prefix: str) -> None:
    issued = _uint(payload.get("issued_at_ms"), code=f"{prefix}_issued_at_invalid")
    expires = _uint(payload.get("expires_at_ms"), code=f"{prefix}_expires_at_invalid")
    if issued > now or expires <= now or expires <= issued or expires - issued > _MAX_COMPONENT_TTL_MS:
        raise AuthorizationChainError(f"{prefix}_time_window_invalid")


def validate_authorization_trust_v02(trust: Mapping[str, AuthorityBindingV02]) -> None:
    if set(trust) != set(AUTHORIZATION_ROLES):
        raise AuthorizationChainError("authorization_authority_set_incomplete")
    bindings = [trust[role] for role in AUTHORIZATION_ROLES]
    for role, binding in zip(AUTHORIZATION_ROLES, bindings, strict=True):
        if not isinstance(binding, AuthorityBindingV02) or binding.role != role:
            raise AuthorizationChainError("authorization_authority_binding_mismatch")
    for attribute, code in (
        ("public_key_hex", "authorization_keys_not_distinct"),
        ("key_id", "authorization_key_ids_not_distinct"),
        ("principal", "authorization_principals_not_distinct"),
        ("issuer", "authorization_issuers_not_distinct"),
    ):
        values = [getattr(binding, attribute) for binding in bindings]
        if len(set(values)) != len(values):
            raise AuthorizationChainError(code)


def build_continuity_decision_v02(
    *,
    packet_commitment: str,
    session_id: str,
    purpose: str,
    star_commitment: str,
    release_proof_commitment: str,
    previous_decision_head_sha256: str,
    revocation_epoch: int,
    verdict: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if authority.role != "CONTINUITY":
        raise AuthorizationChainError("continuity_authority_role_invalid")
    payload: dict[str, Any] = {
        **_PROFILE_FIELDS,
        "packet_commitment": _sha256(packet_commitment, code="packet_commitment_invalid"),
        "session_id": _identifier(session_id, code="session_id_invalid"),
        "purpose": _identifier(purpose, code="purpose_invalid"),
        "star_commitment": _sha256(star_commitment, code="star_commitment_invalid"),
        "release_proof_commitment": _sha256(
            release_proof_commitment, code="release_proof_commitment_invalid"
        ),
        "previous_decision_head_sha256": _sha256(
            previous_decision_head_sha256, code="continuity_head_invalid"
        ),
        "revocation_epoch": _uint(revocation_epoch, code="revocation_epoch_invalid"),
        "verdict": str(verdict),
        "issued_at_ms": _uint(issued_at_ms, code="continuity_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="continuity_expires_at_invalid"),
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise AuthorizationChainError("continuity_time_window_invalid")
    try:
        return sign_component_v02(
            component_type="CONTINUITY_DECISION",
            authority=authority,
            payload=payload,
            private_key=private_key,
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc


def build_authorization_snapshot_v02(
    *,
    packet_commitment: str,
    session_id: str,
    purpose: str,
    release_context_sha256: str,
    recipient_proof_commitment: str,
    star_commitment: str,
    epas_commitment: str,
    release_proof_commitment: str,
    continuity_commitment: str,
    live_binding_sha256: str,
    runtime_measurement_sha256: str,
    policy_measurement_sha256: str,
    verdict: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if authority.role != "AUTHORIZATION":
        raise AuthorizationChainError("authorization_snapshot_authority_role_invalid")
    payload: dict[str, Any] = {
        **_PROFILE_FIELDS,
        "packet_commitment": _sha256(packet_commitment, code="packet_commitment_invalid"),
        "session_id": _identifier(session_id, code="session_id_invalid"),
        "purpose": _identifier(purpose, code="purpose_invalid"),
        "release_context_sha256": _sha256(release_context_sha256, code="release_context_invalid"),
        "recipient_proof_commitment": _sha256(
            recipient_proof_commitment, code="recipient_proof_commitment_invalid"
        ),
        "star_commitment": _sha256(star_commitment, code="star_commitment_invalid"),
        "epas_commitment": _sha256(epas_commitment, code="epas_commitment_invalid"),
        "release_proof_commitment": _sha256(
            release_proof_commitment, code="release_proof_commitment_invalid"
        ),
        "continuity_commitment": _sha256(
            continuity_commitment, code="continuity_commitment_invalid"
        ),
        "live_binding_sha256": _sha256(live_binding_sha256, code="live_binding_invalid"),
        "runtime_measurement_sha256": _sha256(
            runtime_measurement_sha256, code="runtime_measurement_invalid"
        ),
        "policy_measurement_sha256": _sha256(
            policy_measurement_sha256, code="policy_measurement_invalid"
        ),
        "verdict": str(verdict),
        "issued_at_ms": _uint(issued_at_ms, code="authorization_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="authorization_expires_at_invalid"),
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise AuthorizationChainError("authorization_time_window_invalid")
    try:
        return sign_component_v02(
            component_type="AUTHORIZATION_SNAPSHOT",
            authority=authority,
            payload=payload,
            private_key=private_key,
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc


def build_custody_permit_v02(
    *,
    role: str,
    packet_commitment: str,
    session_id: str,
    purpose: str,
    authorization_commitment: str,
    share_binding_sha256: str,
    verdict: str,
    issued_at_ms: int,
    expires_at_ms: int,
    authority: AuthorityBindingV02,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if role not in POINT_ROLES or authority.role != role:
        raise AuthorizationChainError("custody_permit_role_invalid")
    payload: dict[str, Any] = {
        **_PROFILE_FIELDS,
        "role": role,
        "packet_commitment": _sha256(packet_commitment, code="packet_commitment_invalid"),
        "session_id": _identifier(session_id, code="session_id_invalid"),
        "purpose": _identifier(purpose, code="purpose_invalid"),
        "authorization_commitment": _sha256(
            authorization_commitment, code="authorization_commitment_invalid"
        ),
        "share_binding_sha256": _sha256(
            share_binding_sha256, code="share_binding_invalid"
        ),
        "verdict": str(verdict),
        "issued_at_ms": _uint(issued_at_ms, code="custody_permit_issued_at_invalid"),
        "expires_at_ms": _uint(expires_at_ms, code="custody_permit_expires_at_invalid"),
    }
    if payload["expires_at_ms"] <= payload["issued_at_ms"]:
        raise AuthorizationChainError("custody_permit_time_window_invalid")
    try:
        return sign_component_v02(
            component_type="CUSTODY_PERMIT",
            authority=authority,
            payload=payload,
            private_key=private_key,
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc


@dataclass(frozen=True, slots=True)
class AuthorizationChainV02:
    schema: str
    continuity_decision: Mapping[str, Any]
    authorization_snapshot: Mapping[str, Any]
    permits: tuple[Mapping[str, Any], ...]
    custody_authorization: Mapping[str, Any]

    def __post_init__(self) -> None:
        for field_name in (
            "continuity_decision",
            "authorization_snapshot",
            "custody_authorization",
        ):
            object.__setattr__(
                self,
                field_name,
                freeze_mapping(getattr(self, field_name), field=field_name),
            )
        object.__setattr__(
            self,
            "permits",
            tuple(
                freeze_mapping(permit, field=f"permits[{index}]")
                for index, permit in enumerate(self.permits)
            ),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "continuity_decision": thaw_json(self.continuity_decision),
            "authorization_snapshot": thaw_json(self.authorization_snapshot),
            "permits": [thaw_json(permit) for permit in self.permits],
            "custody_authorization": thaw_json(self.custody_authorization),
        }

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V02-AUTHORIZATION-CHAIN", self.public_dict())


def assemble_authorization_chain_v02(
    *,
    continuity_decision: Mapping[str, Any],
    authorization_snapshot: Mapping[str, Any],
    permits: Sequence[Mapping[str, Any]],
    trust: Mapping[str, AuthorityBindingV02],
    custody_authority: AuthorityBindingV02,
    custody_private_key: Ed25519PrivateKey,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> AuthorizationChainV02:
    validate_authorization_trust_v02(trust)
    if trust["CUSTODY"] != custody_authority:
        raise AuthorizationChainError("custody_authority_mismatch")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    try:
        continuity = verify_component_v02(
            continuity_decision,
            expected_type="CONTINUITY_DECISION",
            expected_authority=trust["CONTINUITY"],
        )
        authorization = verify_component_v02(
            authorization_snapshot,
            expected_type="AUTHORIZATION_SNAPSHOT",
            expected_authority=trust["AUTHORIZATION"],
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc
    if continuity.get("verdict") != "ELIGIBLE" or now >= _uint(
        continuity.get("expires_at_ms"), code="continuity_expires_at_invalid"
    ):
        raise AuthorizationChainError("continuity_not_eligible")
    if authorization.get("verdict") != "AUTHORIZED" or now >= _uint(
        authorization.get("expires_at_ms"), code="authorization_expires_at_invalid"
    ):
        raise AuthorizationChainError("authorization_snapshot_denied")
    _require_profile_and_shape(
        continuity, _CONTINUITY_FIELDS, code="continuity_profile_or_shape_invalid"
    )
    _require_profile_and_shape(
        authorization,
        _AUTHORIZATION_FIELDS,
        code="authorization_profile_or_shape_invalid",
    )
    _validate_window(continuity, now=now, prefix="continuity")
    _validate_window(authorization, now=now, prefix="authorization")
    continuity_commitment = component_commitment_v02(continuity_decision)
    if authorization.get("continuity_commitment") != continuity_commitment:
        raise AuthorizationChainError("authorization_continuity_join_mismatch")
    for field in ("packet_commitment", "session_id", "purpose", "star_commitment", "release_proof_commitment"):
        if authorization.get(field) != continuity.get(field):
            raise AuthorizationChainError(f"authorization_continuity_join_mismatch_{field}")
    if len(permits) != len(POINT_ROLES):
        raise AuthorizationChainError("all_five_custody_permits_required")
    authorization_commitment = component_commitment_v02(authorization_snapshot)
    permit_components: list[dict[str, Any]] = []
    permit_payloads: list[dict[str, Any]] = []
    for role, permit in zip(POINT_ROLES, permits, strict=True):
        try:
            payload = verify_component_v02(
                permit,
                expected_type="CUSTODY_PERMIT",
                expected_authority=trust[role],
            )
        except MagicStarError as exc:
            raise AuthorizationChainError(exc.code) from exc
        if payload.get("role") != role:
            raise AuthorizationChainError("custody_permit_order_or_role_mismatch")
        _require_profile_and_shape(
            payload, _PERMIT_FIELDS, code="custody_permit_profile_or_shape_invalid"
        )
        _validate_window(payload, now=now, prefix="custody_permit")
        if payload.get("verdict") != "PERMIT" or now >= _uint(
            payload.get("expires_at_ms"), code="custody_permit_expires_at_invalid"
        ):
            raise AuthorizationChainError("custody_permit_denied")
        if payload.get("authorization_commitment") != authorization_commitment:
            raise AuthorizationChainError("custody_permit_authorization_join_mismatch")
        for field in ("packet_commitment", "session_id", "purpose"):
            if payload.get(field) != authorization.get(field):
                raise AuthorizationChainError(f"custody_permit_join_mismatch_{field}")
        permit_components.append(dict(permit))
        permit_payloads.append(payload)
    custody_payload = {
        **_PROFILE_FIELDS,
        "packet_commitment": authorization["packet_commitment"],
        "session_id": authorization["session_id"],
        "purpose": authorization["purpose"],
        "star_commitment": authorization["star_commitment"],
        "release_proof_commitment": authorization["release_proof_commitment"],
        "authorization_commitment": authorization_commitment,
        "permit_roles": list(POINT_ROLES),
        "permit_commitments": [
            component_commitment_v02(component) for component in permit_components
        ],
        "share_bindings": [payload["share_binding_sha256"] for payload in permit_payloads],
        "all_five_required": True,
        "authorized_at_ms": now,
        "expires_at_ms": min(
            _uint(payload["expires_at_ms"], code="custody_permit_expires_at_invalid")
            for payload in permit_payloads
        ),
    }
    try:
        custody_authorization = sign_component_v02(
            component_type="CUSTODY_AUTHORIZATION",
            authority=custody_authority,
            payload=custody_payload,
            private_key=custody_private_key,
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc
    chain = AuthorizationChainV02(
        schema=AUTHORIZATION_CHAIN_SCHEMA,
        continuity_decision=dict(continuity_decision),
        authorization_snapshot=dict(authorization_snapshot),
        permits=tuple(permit_components),
        custody_authorization=custody_authorization,
    )
    validate_authorization_chain_v02(chain, trust=trust, trusted_now_ms=trusted_now_ms)
    return chain


def validate_authorization_chain_v02(
    chain: AuthorizationChainV02,
    *,
    trust: Mapping[str, AuthorityBindingV02],
    expected_previous_decision_head_sha256: str | None = None,
    expected_revocation_epoch: int | None = None,
    expected_join: Mapping[str, Any] | None = None,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> dict[str, Any]:
    if not isinstance(chain, AuthorizationChainV02) or chain.schema != AUTHORIZATION_CHAIN_SCHEMA:
        raise AuthorizationChainError("authorization_chain_schema_invalid")
    validate_authorization_trust_v02(trust)
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    try:
        continuity = verify_component_v02(
            chain.continuity_decision,
            expected_type="CONTINUITY_DECISION",
            expected_authority=trust["CONTINUITY"],
        )
        authorization = verify_component_v02(
            chain.authorization_snapshot,
            expected_type="AUTHORIZATION_SNAPSHOT",
            expected_authority=trust["AUTHORIZATION"],
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc
    if continuity.get("verdict") != "ELIGIBLE" or authorization.get("verdict") != "AUTHORIZED":
        raise AuthorizationChainError("authorization_chain_not_approved")
    _require_profile_and_shape(
        continuity, _CONTINUITY_FIELDS, code="continuity_profile_or_shape_invalid"
    )
    _require_profile_and_shape(
        authorization,
        _AUTHORIZATION_FIELDS,
        code="authorization_profile_or_shape_invalid",
    )
    _validate_window(continuity, now=now, prefix="continuity")
    _validate_window(authorization, now=now, prefix="authorization")
    if expected_previous_decision_head_sha256 is not None and continuity.get(
        "previous_decision_head_sha256"
    ) != _sha256(
        expected_previous_decision_head_sha256,
        code="continuity_head_invalid",
    ):
        raise AuthorizationChainError("continuity_head_mismatch")
    if expected_revocation_epoch is not None and continuity.get("revocation_epoch") != _uint(
        expected_revocation_epoch, code="revocation_epoch_invalid"
    ):
        raise AuthorizationChainError("continuity_revocation_epoch_mismatch")
    if authorization.get("continuity_commitment") != component_commitment_v02(
        chain.continuity_decision
    ):
        raise AuthorizationChainError("authorization_continuity_join_mismatch")
    for field in ("packet_commitment", "session_id", "purpose", "star_commitment", "release_proof_commitment"):
        if authorization.get(field) != continuity.get(field):
            raise AuthorizationChainError(f"authorization_continuity_join_mismatch_{field}")
    if len(chain.permits) != len(POINT_ROLES):
        raise AuthorizationChainError("all_five_custody_permits_required")
    authorization_commitment = component_commitment_v02(chain.authorization_snapshot)
    permit_commitments: list[str] = []
    share_bindings: list[str] = []
    for role, permit in zip(POINT_ROLES, chain.permits, strict=True):
        try:
            payload = verify_component_v02(
                permit,
                expected_type="CUSTODY_PERMIT",
                expected_authority=trust[role],
            )
        except MagicStarError as exc:
            raise AuthorizationChainError(exc.code) from exc
        if payload.get("role") != role or payload.get("verdict") != "PERMIT":
            raise AuthorizationChainError("custody_permit_order_or_verdict_invalid")
        _require_profile_and_shape(
            payload, _PERMIT_FIELDS, code="custody_permit_profile_or_shape_invalid"
        )
        _validate_window(payload, now=now, prefix="custody_permit")
        if payload.get("authorization_commitment") != authorization_commitment:
            raise AuthorizationChainError("custody_permit_authorization_join_mismatch")
        for field in ("packet_commitment", "session_id", "purpose"):
            if payload.get(field) != authorization.get(field):
                raise AuthorizationChainError(f"custody_permit_join_mismatch_{field}")
        permit_commitments.append(component_commitment_v02(permit))
        share_bindings.append(_sha256(payload.get("share_binding_sha256"), code="share_binding_invalid"))
    try:
        custody = verify_component_v02(
            chain.custody_authorization,
            expected_type="CUSTODY_AUTHORIZATION",
            expected_authority=trust["CUSTODY"],
        )
    except MagicStarError as exc:
        raise AuthorizationChainError(exc.code) from exc
    _require_profile_and_shape(
        custody, _CUSTODY_FIELDS, code="custody_authorization_profile_or_shape_invalid"
    )
    expected = {
        "packet_commitment": authorization["packet_commitment"],
        "session_id": authorization["session_id"],
        "purpose": authorization["purpose"],
        "star_commitment": authorization["star_commitment"],
        "release_proof_commitment": authorization["release_proof_commitment"],
        "authorization_commitment": authorization_commitment,
        "permit_roles": list(POINT_ROLES),
        "permit_commitments": permit_commitments,
        "share_bindings": share_bindings,
        "all_five_required": True,
    }
    if any(custody.get(key) != value for key, value in expected.items()):
        raise AuthorizationChainError("custody_authorization_join_mismatch")
    custody_authorized_at = _uint(
        custody.get("authorized_at_ms"), code="custody_authorization_issued_at_invalid"
    )
    custody_expires = _uint(
        custody.get("expires_at_ms"), code="custody_authorization_expiry_invalid"
    )
    expected_custody_expiry = min(
        _uint(
            verify_component_v02(
                permit,
                expected_type="CUSTODY_PERMIT",
                expected_authority=trust[role],
            ).get("expires_at_ms"),
            code="custody_permit_expires_at_invalid",
        )
        for role, permit in zip(POINT_ROLES, chain.permits, strict=True)
    )
    if custody_authorized_at > now or custody_expires <= now or custody_expires != expected_custody_expiry:
        raise AuthorizationChainError("custody_authorization_time_window_invalid")
    summary = {
        "valid": True,
        **{key: authorization[key] for key in (
            "packet_commitment",
            "session_id",
            "purpose",
            "release_context_sha256",
            "recipient_proof_commitment",
            "star_commitment",
            "epas_commitment",
            "release_proof_commitment",
            "live_binding_sha256",
            "runtime_measurement_sha256",
            "policy_measurement_sha256",
        )},
        "authorization_commitment": authorization_commitment,
        "custody_authorization_commitment": component_commitment_v02(
            chain.custody_authorization
        ),
        "authorization_chain_commitment": chain.commitment,
        "permit_count": len(permit_commitments),
        "share_bindings": share_bindings,
        "expires_at_ms": min(
            _uint(continuity["expires_at_ms"], code="continuity_expires_at_invalid"),
            _uint(
                authorization["expires_at_ms"],
                code="authorization_expires_at_invalid",
            ),
            custody_expires,
        ),
    }
    if expected_join is not None:
        for key, value in expected_join.items():
            if summary.get(key) != value:
                raise AuthorizationChainError(f"authorization_expected_join_mismatch_{key}")
    return summary


__all__ = [
    "AUTHORIZATION_CHAIN_SCHEMA",
    "AUTHORIZATION_ROLES",
    "AuthorizationChainError",
    "AuthorizationChainV02",
    "assemble_authorization_chain_v02",
    "build_authorization_snapshot_v02",
    "build_continuity_decision_v02",
    "build_custody_permit_v02",
    "validate_authorization_chain_v02",
    "validate_authorization_trust_v02",
]
