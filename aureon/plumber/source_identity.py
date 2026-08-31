"""Commitment-only source identity for Aureon Plumber v0."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from .crypto import domain_hash
from .schema import (
    DenialCode,
    SchemaError,
    require_exact_keys,
    require_nonblank,
    require_sha256,
)

SOURCE_IDENTITY_SCHEMA = "aureon.plumber.source-identity.v0"
_FIELDS = (
    "schema",
    "source_type",
    "source_locator_commitment",
    "source_content_commitment",
    "provenance_receipt_commitment",
    "identity_commitment",
)


@dataclass(frozen=True, slots=True)
class SourceIdentityV0:
    schema: str
    source_type: str
    source_locator_commitment: str
    source_content_commitment: str
    provenance_receipt_commitment: str
    identity_commitment: str

    def __post_init__(self) -> None:
        if self.schema != SOURCE_IDENTITY_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        require_nonblank(self.source_type, field="source_type")
        for field in (
            "source_locator_commitment",
            "source_content_commitment",
            "provenance_receipt_commitment",
            "identity_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        if domain_hash("aureon.plumber.source-identity.v0", self.commitment_payload()) != self.identity_commitment:
            raise SchemaError(DenialCode.SOURCE_IDENTITY_MISMATCH, field="identity_commitment")

    @classmethod
    def build(
        cls,
        *,
        source_type: str,
        source_locator_commitment: str,
        source_content_commitment: str,
        provenance_receipt_commitment: str,
    ) -> Self:
        values = {
            "schema": SOURCE_IDENTITY_SCHEMA,
            "source_type": source_type,
            "source_locator_commitment": source_locator_commitment,
            "source_content_commitment": source_content_commitment,
            "provenance_receipt_commitment": provenance_receipt_commitment,
        }
        return cls(
            **values,
            identity_commitment=domain_hash("aureon.plumber.source-identity.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _FIELDS, field="source_identity"))

    def commitment_payload(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _FIELDS if field != "identity_commitment"}

    def to_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _FIELDS}

    def public_summary(self) -> dict[str, str]:
        return self.to_dict()


def build_source_identity(**values: Any) -> SourceIdentityV0:
    return SourceIdentityV0.build(**values)


def build_source_identity_from_hnc_packet(packet: Mapping[str, Any]) -> SourceIdentityV0:
    """Bind an existing, valid HNC quantum packet without decoding it.

    The established HNC validator remains authoritative for its packet
    contract. Plumber consumes only its validated packet and alignment hashes;
    ciphertext, nonce, purpose, and plaintext never enter the public identity.
    """

    if not isinstance(packet, Mapping):
        raise SchemaError(DenialCode.INVALID_TYPE, field="hnc_packet")
    from aureon.harmonic.hnc_quantum_packet_crypto import validate_hnc_packet_contract

    validation = validate_hnc_packet_contract(packet)
    if not validation.get("valid"):
        raise SchemaError(DenialCode.SOURCE_IDENTITY_MISMATCH, field="hnc_packet")
    packet_commitment = require_sha256(
        validation.get("packet_sha256"),
        field="hnc_packet.packet_sha256",
    )
    alignment_commitment = require_sha256(
        validation.get("hnc_alignment_sha256"),
        field="hnc_packet.hnc_alignment_sha256",
    )
    locator_commitment = domain_hash(
        "aureon.plumber.hnc-source-locator.v0",
        {
            "magic": packet.get("magic"),
            "schema_version": packet.get("schema_version"),
        },
    )
    return SourceIdentityV0.build(
        source_type="hnc-quantum-packet-v1",
        source_locator_commitment=locator_commitment,
        source_content_commitment=packet_commitment,
        provenance_receipt_commitment=alignment_commitment,
    )


def verify_source_identity(value: SourceIdentityV0 | Mapping[str, Any]) -> bool:
    try:
        identity = value if isinstance(value, SourceIdentityV0) else SourceIdentityV0.from_dict(value)
        return domain_hash("aureon.plumber.source-identity.v0", identity.commitment_payload()) == identity.identity_commitment
    except (SchemaError, TypeError, ValueError):
        return False


__all__ = [
    "SOURCE_IDENTITY_SCHEMA",
    "SourceIdentityV0",
    "build_source_identity",
    "build_source_identity_from_hnc_packet",
    "verify_source_identity",
]
