"""Strict, fail-closed schema primitives for Aureon Plumber v0.

The v0 packet is an authenticated metadata envelope.  It deliberately makes
no claim that encrypted material has been released, executed, or accepted by
any production system.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Self, cast

from .crypto import canonical_json_bytes, domain_hash

PLUMBER_MAGIC = "AUREON-HNC-PLUMBER"
PLUMBER_SCHEMA_VERSION = 0
PLUMBER_PACKET_SCHEMA = "aureon.plumber.packet.v0"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ED25519_SIGNATURE_RE = re.compile(r"^[0-9a-f]{128}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_FIXED_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")


class DenialCode(StrEnum):
    """Stable machine-readable failure codes shared by the v0 modules."""

    INVALID_SCHEMA = "invalid_schema"
    UNKNOWN_FIELD = "unknown_field"
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    INVALID_SIGNATURE = "invalid_signature"
    SIGNER_MISMATCH = "signer_mismatch"
    PACKET_IDENTITY_MISMATCH = "packet_identity_mismatch"
    SESSION_IDENTITY_MISMATCH = "session_identity_mismatch"
    PACKET_COMMITMENT_MISMATCH = "packet_commitment_mismatch"
    SOURCE_IDENTITY_MISMATCH = "source_identity_mismatch"
    TEMPORAL_IDENTITY_MISMATCH = "temporal_identity_mismatch"
    OBSERVER_TRANSCRIPT_MISMATCH = "observer_transcript_mismatch"
    TWIN_RUNE_MISMATCH = "twin_rune_mismatch"
    SYMPATHETIC_IDENTITY_MISMATCH = "sympathetic_identity_mismatch"
    POLICY_RECEIPT_MISSING = "policy_receipt_missing"
    POLICY_RECEIPT_INVALID = "policy_receipt_invalid"
    QUORUM_INCOMPLETE = "quorum_incomplete"
    QUORUM_DUPLICATE_AUTHORITY = "quorum_duplicate_authority"
    FRAGMENT_SET_INCOMPLETE = "fragment_set_incomplete"
    FRAGMENT_INVALID = "fragment_invalid"
    FRAGMENT_EXPIRED = "fragment_expired"
    REPLAY_DETECTED = "replay_detected"
    STALE_STATE = "stale_state"
    FUTURE_STATE = "future_state"
    COUNTER_ROLLBACK = "counter_rollback"
    PREVIOUS_STATE_MISMATCH = "previous_state_mismatch"
    PURPOSE_MISMATCH = "purpose_mismatch"
    QUARANTINED = "quarantined"
    INTERNAL_ERROR = "internal_error"


class SchemaError(ValueError):
    """A validation failure that never interpolates rejected values."""

    def __init__(self, code: DenialCode | str, *, field: str | None = None) -> None:
        self.code = str(code)
        self.field = field
        message = self.code if field is None else f"{self.code}:{field}"
        super().__init__(message)


def require_exact_keys(
    value: Mapping[str, Any],
    expected: Iterable[str],
    *,
    field: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    if any(not isinstance(key, str) for key in value):
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    expected_keys = frozenset(expected)
    actual_keys = frozenset(value)
    missing = sorted(expected_keys - actual_keys)
    if missing:
        raise SchemaError(DenialCode.MISSING_FIELD, field=f"{field}.{missing[0]}")
    unknown = sorted(actual_keys - expected_keys)
    if unknown:
        raise SchemaError(DenialCode.UNKNOWN_FIELD, field=f"{field}.{unknown[0]}")
    return dict(value)


def require_mapping(value: Any, *, field: str, nonempty: bool = True) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    result = dict(value)
    if nonempty and not result:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    try:
        canonical_json_bytes(result)
    except ValueError as exc:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field) from exc
    return result


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_json(item) for item in value)
    return value


def freeze_mapping(value: Any, *, field: str, nonempty: bool = True) -> Mapping[str, Any]:
    """Validate and defensively freeze a JSON mapping."""

    return cast(
        Mapping[str, Any],
        _freeze_json(require_mapping(value, field=field, nonempty=nonempty)),
    )


def thaw_json(value: Any) -> Any:
    """Return a recursively mutable, JSON-serializable public copy."""

    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [thaw_json(item) for item in value]
    return value


def require_nonblank(value: Any, *, field: str, max_length: int = 512) -> str:
    if not isinstance(value, str):
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    if not value or value != value.strip() or len(value) > max_length or _CONTROL_RE.search(value):
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return value


def require_sha256(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return value


def require_ed25519_public_key(value: Any, *, field: str) -> str:
    return require_sha256(value, field=field)


def require_ed25519_signature(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _ED25519_SIGNATURE_RE.fullmatch(value) is None:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return value


def require_int(value: Any, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return value


def require_fixed_decimal(value: Any, *, field: str) -> str:
    """Return the v0 canonical number representation.

    Python floats are intentionally rejected.  Integers normalize to decimal
    strings and callers with measured fractional values must supply a fixed
    decimal string without redundant leading or trailing zeroes.
    """

    if type(value) is int:
        value = str(value)
    if not isinstance(value, str):
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    if _FIXED_DECIMAL_RE.fullmatch(value) is None:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return value


def format_timestamp(value: datetime) -> str:
    normalized = require_aware_datetime(value, field="timestamp")
    if normalized.microsecond:
        raise SchemaError(DenialCode.INVALID_VALUE, field="timestamp")
    return normalized.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as exc:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field) from exc
    if parsed.microsecond or format_timestamp(parsed) != value:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return parsed


def require_aware_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    return value.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


_PACKET_FIELDS = (
    "magic",
    "schema",
    "schema_version",
    "packet_identity",
    "source_identity",
    "temporal_identity",
    "requested_purpose",
    "hnc_observer_challenge",
    "canonical_field_receipt",
    "observer_transcript_commitment",
    "twin_rune_seal",
    "sympathetic_identity_commitment",
    "heart_receipt",
    "conscience_receipt",
    "governance_receipt",
    "quorum_policy",
    "encrypted_payload",
    "spore_manifest",
    "packet_commitment",
    "signatures",
)


def _copy_json(value: Mapping[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(canonical_json_bytes(value)))


def _packet_commitment_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: values[key] for key in _PACKET_FIELDS if key not in {"packet_commitment", "signatures"}}


@dataclass(frozen=True, slots=True)
class PlumberPacketV0:
    magic: str
    schema: str
    schema_version: int
    packet_identity: str
    source_identity: Mapping[str, Any]
    temporal_identity: Mapping[str, Any]
    requested_purpose: str
    hnc_observer_challenge: str
    canonical_field_receipt: Mapping[str, Any]
    observer_transcript_commitment: str
    twin_rune_seal: Mapping[str, Any]
    sympathetic_identity_commitment: str
    heart_receipt: Mapping[str, Any]
    conscience_receipt: Mapping[str, Any]
    governance_receipt: Mapping[str, Any]
    quorum_policy: Mapping[str, Any]
    encrypted_payload: Mapping[str, Any]
    spore_manifest: Mapping[str, Any]
    packet_commitment: str
    signatures: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.magic != PLUMBER_MAGIC or self.schema != PLUMBER_PACKET_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="packet")
        if type(self.schema_version) is not int or self.schema_version != PLUMBER_SCHEMA_VERSION:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema_version")
        require_nonblank(self.packet_identity, field="packet_identity")
        require_nonblank(self.requested_purpose, field="requested_purpose", max_length=1024)
        require_sha256(self.hnc_observer_challenge, field="hnc_observer_challenge")
        require_sha256(self.observer_transcript_commitment, field="observer_transcript_commitment")
        require_sha256(self.sympathetic_identity_commitment, field="sympathetic_identity_commitment")
        require_sha256(self.packet_commitment, field="packet_commitment")
        for name in (
            "source_identity",
            "temporal_identity",
            "canonical_field_receipt",
            "twin_rune_seal",
            "heart_receipt",
            "conscience_receipt",
            "governance_receipt",
            "quorum_policy",
            "encrypted_payload",
            "spore_manifest",
        ):
            object.__setattr__(self, name, freeze_mapping(getattr(self, name), field=name))
        if not isinstance(self.signatures, Mapping):
            raise SchemaError(DenialCode.INVALID_TYPE, field="signatures")
        for signer, signature in self.signatures.items():
            require_nonblank(signer, field="signatures.signer")
            require_ed25519_signature(signature, field="signatures.signature")
        object.__setattr__(self, "signatures", freeze_mapping(self.signatures, field="signatures", nonempty=False))
        if self.computed_commitment() != self.packet_commitment:
            raise SchemaError(DenialCode.PACKET_COMMITMENT_MISMATCH, field="packet_commitment")

    @classmethod
    def build(cls, **values: Any) -> Self:
        allowed = set(_PACKET_FIELDS) - {"packet_commitment"}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise SchemaError(DenialCode.UNKNOWN_FIELD, field=f"packet.{unknown[0]}")
        required = allowed - {"magic", "schema", "schema_version", "signatures"}
        missing = sorted(required - set(values))
        if missing:
            raise SchemaError(DenialCode.MISSING_FIELD, field=f"packet.{missing[0]}")
        parsed = {
            "magic": values.get("magic", PLUMBER_MAGIC),
            "schema": values.get("schema", PLUMBER_PACKET_SCHEMA),
            "schema_version": values.get("schema_version", PLUMBER_SCHEMA_VERSION),
            **{key: value for key, value in values.items() if key not in {"magic", "schema", "schema_version"}},
        }
        parsed.setdefault("signatures", {})
        parsed["packet_commitment"] = domain_hash(
            "aureon.plumber.packet.v0",
            _packet_commitment_payload(parsed),
        )
        return cls.from_dict(parsed)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        parsed = require_exact_keys(value, _PACKET_FIELDS, field="packet")
        return cls(**parsed)

    def to_dict(self) -> dict[str, Any]:
        return _copy_json({name: getattr(self, name) for name in _PACKET_FIELDS})

    def computed_commitment(self) -> str:
        return domain_hash("aureon.plumber.packet.v0", _packet_commitment_payload(self.to_dict()))

    def public_summary(self) -> dict[str, Any]:
        """Return commitments and counts only; omit payload, purpose, and signatures."""

        return {
            "magic": self.magic,
            "schema": self.schema,
            "schema_version": self.schema_version,
            "packet_identity": self.packet_identity,
            "purpose_commitment": domain_hash("aureon.plumber.purpose.v0", self.requested_purpose),
            "observer_transcript_commitment": self.observer_transcript_commitment,
            "sympathetic_identity_commitment": self.sympathetic_identity_commitment,
            "packet_commitment": self.packet_commitment,
            "signature_count": len(self.signatures),
            "release_state": "not_released",
        }


__all__ = [
    "DenialCode",
    "PLUMBER_MAGIC",
    "PLUMBER_PACKET_SCHEMA",
    "PLUMBER_SCHEMA_VERSION",
    "PlumberPacketV0",
    "SchemaError",
    "format_timestamp",
    "freeze_mapping",
    "thaw_json",
    "parse_timestamp",
    "require_aware_datetime",
    "require_ed25519_public_key",
    "require_ed25519_signature",
    "require_exact_keys",
    "require_int",
    "require_fixed_decimal",
    "require_mapping",
    "require_nonblank",
    "require_sha256",
    "utc_now",
]
