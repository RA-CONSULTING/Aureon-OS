"""Purpose-bound sympathetic identity commitment for Plumber v0."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from .crypto import domain_hash
from .schema import DenialCode, SchemaError, require_exact_keys, require_sha256

SYMPATHETIC_IDENTITY_SCHEMA = "aureon.plumber.sympathetic-identity.v0"
_FIELDS = (
    "schema",
    "source_identity_commitment",
    "hardware_identity_commitment",
    "operator_identity_commitment",
    "temporal_identity_commitment",
    "observer_identity_commitment",
    "purpose_commitment",
    "policy_commitment",
    "identity_commitment",
)


@dataclass(frozen=True, slots=True)
class SympatheticIdentityV0:
    schema: str
    source_identity_commitment: str
    hardware_identity_commitment: str
    operator_identity_commitment: str
    temporal_identity_commitment: str
    observer_identity_commitment: str
    purpose_commitment: str
    policy_commitment: str
    identity_commitment: str

    def __post_init__(self) -> None:
        if self.schema != SYMPATHETIC_IDENTITY_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        for field in _FIELDS[1:]:
            require_sha256(getattr(self, field), field=field)
        if domain_hash("aureon.plumber.sympathetic-identity.v0", self.commitment_payload()) != self.identity_commitment:
            raise SchemaError(DenialCode.SYMPATHETIC_IDENTITY_MISMATCH, field="identity_commitment")

    @classmethod
    def build(cls, **commitments: str) -> Self:
        expected = set(_FIELDS) - {"schema", "identity_commitment"}
        parsed = require_exact_keys(commitments, expected, field="sympathetic_identity")
        values = {"schema": SYMPATHETIC_IDENTITY_SCHEMA, **parsed}
        return cls(
            **values,
            identity_commitment=domain_hash("aureon.plumber.sympathetic-identity.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _FIELDS, field="sympathetic_identity"))

    def commitment_payload(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _FIELDS if field != "identity_commitment"}

    def to_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _FIELDS}

    def public_summary(self) -> dict[str, str]:
        return self.to_dict()


def build_sympathetic_identity(**values: Any) -> SympatheticIdentityV0:
    return SympatheticIdentityV0.build(**values)


__all__ = [
    "SYMPATHETIC_IDENTITY_SCHEMA",
    "SympatheticIdentityV0",
    "build_sympathetic_identity",
]
