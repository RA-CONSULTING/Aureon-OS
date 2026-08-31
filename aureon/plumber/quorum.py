"""Typed-authority quorum permits for Aureon Plumber v0.

Permits carry only wrapped-share commitments.  This module never accepts or
returns a raw key share and does not reconstruct a session key.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import (
    domain_hash,
    ed25519_public_key_hex,
    load_ed25519_private_key,
    sign_ed25519,
    verify_ed25519,
)
from .schema import (
    DenialCode,
    SchemaError,
    format_timestamp,
    parse_timestamp,
    require_aware_datetime,
    require_ed25519_public_key,
    require_ed25519_signature,
    require_exact_keys,
    require_nonblank,
    require_sha256,
)

QUORUM_POLICY_SCHEMA = "aureon.plumber.quorum-policy.v0"
AUTHORITY_PERMIT_SCHEMA = "aureon.plumber.authority-permit.v0"
_SIGNATURE_DOMAIN = "aureon.plumber.authority-permit.signature.v0"


class AuthorityRole(StrEnum):
    SOURCE = "source"
    OBSERVER = "observer"
    CONSCIENCE = "conscience"
    GOVERNANCE = "governance"
    OPERATOR = "operator"


_POLICY_FIELDS = ("schema", "required_roles", "operator_required", "policy_commitment")


@dataclass(frozen=True, slots=True)
class QuorumPolicyV0:
    schema: str
    required_roles: tuple[str, ...]
    operator_required: bool
    policy_commitment: str

    def __post_init__(self) -> None:
        if self.schema != QUORUM_POLICY_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        if type(self.operator_required) is not bool:
            raise SchemaError(DenialCode.INVALID_TYPE, field="operator_required")
        if not isinstance(self.required_roles, tuple) or not self.required_roles:
            raise SchemaError(DenialCode.INVALID_TYPE, field="required_roles")
        try:
            parsed = tuple(str(AuthorityRole(role)) for role in self.required_roles)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="required_roles") from exc
        if tuple(sorted(set(parsed))) != parsed:
            raise SchemaError(DenialCode.INVALID_VALUE, field="required_roles")
        if self.operator_required != (str(AuthorityRole.OPERATOR) in parsed):
            raise SchemaError(DenialCode.INVALID_VALUE, field="operator_required")
        require_sha256(self.policy_commitment, field="policy_commitment")
        if domain_hash("aureon.plumber.quorum-policy.v0", self.commitment_payload()) != self.policy_commitment:
            raise SchemaError(DenialCode.INVALID_VALUE, field="policy_commitment")

    @classmethod
    def build(
        cls,
        *,
        required_roles: Sequence[AuthorityRole | str] = (
            AuthorityRole.SOURCE,
            AuthorityRole.OBSERVER,
            AuthorityRole.CONSCIENCE,
            AuthorityRole.GOVERNANCE,
        ),
        operator_required: bool = False,
    ) -> Self:
        roles = {str(AuthorityRole(role)) for role in required_roles}
        if operator_required:
            roles.add(str(AuthorityRole.OPERATOR))
        else:
            roles.discard(str(AuthorityRole.OPERATOR))
        required_roles_value = tuple(sorted(roles))
        values = {
            "schema": QUORUM_POLICY_SCHEMA,
            "required_roles": required_roles_value,
            "operator_required": operator_required,
        }
        return cls(
            schema=QUORUM_POLICY_SCHEMA,
            required_roles=required_roles_value,
            operator_required=operator_required,
            policy_commitment=domain_hash("aureon.plumber.quorum-policy.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        parsed = require_exact_keys(value, _POLICY_FIELDS, field="quorum_policy")
        if not isinstance(parsed["required_roles"], list):
            raise SchemaError(DenialCode.INVALID_TYPE, field="required_roles")
        parsed["required_roles"] = tuple(parsed["required_roles"])
        return cls(**parsed)

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "required_roles": list(self.required_roles),
            "operator_required": self.operator_required,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "policy_commitment": self.policy_commitment}


_PERMIT_FIELDS = (
    "schema",
    "role",
    "authority_id",
    "packet_identity",
    "session_identity",
    "purpose_commitment",
    "policy_commitment",
    "wrapped_share_commitment",
    "issued_at",
    "expires_at",
    "signer_public_key",
    "permit_hash",
    "signature",
)


@dataclass(frozen=True, slots=True)
class AuthorityPermit:
    schema: str
    role: str
    authority_id: str
    packet_identity: str
    session_identity: str
    purpose_commitment: str
    policy_commitment: str
    wrapped_share_commitment: str
    issued_at: str
    expires_at: str
    signer_public_key: str
    permit_hash: str
    signature: str

    def __post_init__(self) -> None:
        if self.schema != AUTHORITY_PERMIT_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        try:
            AuthorityRole(self.role)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="role") from exc
        for field in ("authority_id", "packet_identity", "session_identity"):
            require_nonblank(getattr(self, field), field=field)
        for field in (
            "purpose_commitment",
            "policy_commitment",
            "wrapped_share_commitment",
            "permit_hash",
        ):
            require_sha256(getattr(self, field), field=field)
        require_ed25519_public_key(self.signer_public_key, field="signer_public_key")
        require_ed25519_signature(self.signature, field="signature")
        issued = parse_timestamp(self.issued_at, field="issued_at")
        expires = parse_timestamp(self.expires_at, field="expires_at")
        if expires <= issued:
            raise SchemaError(DenialCode.INVALID_VALUE, field="expires_at")

    @classmethod
    def issue(
        cls,
        *,
        role: AuthorityRole | str,
        authority_id: str,
        packet_identity: str,
        session_identity: str,
        purpose_commitment: str,
        policy_commitment: str,
        wrapped_share_commitment: str,
        issued_at: datetime,
        expires_at: datetime,
        private_key: Ed25519PrivateKey | bytes | str,
    ) -> Self:
        key = load_ed25519_private_key(private_key)
        values = {
            "schema": AUTHORITY_PERMIT_SCHEMA,
            "role": str(AuthorityRole(role)),
            "authority_id": authority_id,
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "purpose_commitment": purpose_commitment,
            "policy_commitment": policy_commitment,
            "wrapped_share_commitment": wrapped_share_commitment,
            "issued_at": format_timestamp(issued_at),
            "expires_at": format_timestamp(expires_at),
            "signer_public_key": ed25519_public_key_hex(key),
        }
        permit_hash = domain_hash("aureon.plumber.authority-permit.v0", values)
        signature = sign_ed25519(key, {"permit_hash": permit_hash}, domain=_SIGNATURE_DOMAIN)
        return cls(**values, permit_hash=permit_hash, signature=signature)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _PERMIT_FIELDS, field="authority_permit"))

    def unsigned_payload(self) -> dict[str, str]:
        return {
            field: getattr(self, field)
            for field in _PERMIT_FIELDS
            if field not in {"permit_hash", "signature"}
        }

    def to_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _PERMIT_FIELDS}

    def signature_valid(self) -> bool:
        return (
            domain_hash("aureon.plumber.authority-permit.v0", self.unsigned_payload()) == self.permit_hash
            and verify_ed25519(
                self.signer_public_key,
                {"permit_hash": self.permit_hash},
                self.signature,
                domain=_SIGNATURE_DOMAIN,
            )
        )

    def public_summary(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _PERMIT_FIELDS if field != "signature"}


@dataclass(frozen=True, slots=True)
class QuorumValidation:
    valid: bool
    denial_codes: tuple[str, ...]
    accepted_roles: tuple[str, ...]
    permit_set_commitment: str


def evaluate_quorum(
    policy: QuorumPolicyV0,
    permits: Sequence[AuthorityPermit],
    *,
    now: datetime,
    packet_identity: str,
    session_identity: str,
    purpose_commitment: str,
) -> QuorumValidation:
    if not isinstance(policy, QuorumPolicyV0):
        raise SchemaError(DenialCode.INVALID_TYPE, field="policy")
    if isinstance(permits, (str, bytes, bytearray)) or not isinstance(permits, Sequence):
        raise SchemaError(DenialCode.INVALID_TYPE, field="permits")
    denials: set[str] = set()
    by_role: dict[str, AuthorityPermit] = {}
    authority_ids: set[str] = set()
    public_keys: set[str] = set()
    current = require_aware_datetime(now, field="now")
    for permit in permits:
        if not isinstance(permit, AuthorityPermit):
            raise SchemaError(DenialCode.INVALID_TYPE, field="permits")
        if permit.role in by_role or permit.authority_id in authority_ids or permit.signer_public_key in public_keys:
            denials.add(str(DenialCode.QUORUM_DUPLICATE_AUTHORITY))
        by_role.setdefault(permit.role, permit)
        authority_ids.add(permit.authority_id)
        public_keys.add(permit.signer_public_key)
        if permit.role not in policy.required_roles:
            denials.add(str(DenialCode.POLICY_RECEIPT_INVALID))
        if not permit.signature_valid():
            denials.add(str(DenialCode.INVALID_SIGNATURE))
        if permit.packet_identity != packet_identity or permit.session_identity != session_identity:
            if permit.packet_identity != packet_identity:
                denials.add(str(DenialCode.PACKET_IDENTITY_MISMATCH))
            if permit.session_identity != session_identity:
                denials.add(str(DenialCode.SESSION_IDENTITY_MISMATCH))
        if permit.purpose_commitment != purpose_commitment:
            denials.add(str(DenialCode.PURPOSE_MISMATCH))
        if permit.policy_commitment != policy.policy_commitment:
            denials.add(str(DenialCode.POLICY_RECEIPT_INVALID))
        if current < parse_timestamp(permit.issued_at, field="issued_at"):
            denials.add(str(DenialCode.FUTURE_STATE))
        if current >= parse_timestamp(permit.expires_at, field="expires_at"):
            denials.add(str(DenialCode.STALE_STATE))
    if set(policy.required_roles) - set(by_role):
        denials.add(str(DenialCode.QUORUM_INCOMPLETE))
    summaries = [by_role[role].public_summary() for role in sorted(by_role)]
    return QuorumValidation(
        valid=not denials,
        denial_codes=tuple(sorted(denials)),
        accepted_roles=tuple(sorted(set(by_role) & set(policy.required_roles))),
        permit_set_commitment=domain_hash("aureon.plumber.permit-set.v0", summaries),
    )


__all__ = [
    "AUTHORITY_PERMIT_SCHEMA",
    "QUORUM_POLICY_SCHEMA",
    "AuthorityPermit",
    "AuthorityRole",
    "QuorumPolicyV0",
    "QuorumValidation",
    "evaluate_quorum",
]
