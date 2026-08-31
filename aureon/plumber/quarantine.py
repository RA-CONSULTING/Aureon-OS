"""Metadata-only quarantine records for denied Plumber material."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from .crypto import domain_hash
from .schema import (
    DenialCode,
    SchemaError,
    format_timestamp,
    freeze_mapping,
    parse_timestamp,
    require_exact_keys,
    require_nonblank,
    require_sha256,
)

QUARANTINE_SCHEMA = "aureon.plumber.quarantine-record.v0"
_FIELDS = (
    "schema",
    "quarantine_id",
    "packet_identity",
    "session_identity",
    "packet_commitment",
    "denial_codes",
    "evidence_commitments",
    "quarantined_at",
    "record_commitment",
)


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    schema: str
    quarantine_id: str
    packet_identity: str
    session_identity: str
    packet_commitment: str
    denial_codes: tuple[str, ...]
    evidence_commitments: Mapping[str, str]
    quarantined_at: str
    record_commitment: str

    def __post_init__(self) -> None:
        if self.schema != QUARANTINE_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        for field in ("quarantine_id", "packet_identity", "session_identity"):
            require_nonblank(getattr(self, field), field=field)
        for field in ("packet_commitment", "record_commitment"):
            require_sha256(getattr(self, field), field=field)
        if not self.denial_codes or tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if not isinstance(self.evidence_commitments, Mapping):
            raise SchemaError(DenialCode.INVALID_TYPE, field="evidence_commitments")
        for name, commitment in self.evidence_commitments.items():
            require_nonblank(name, field="evidence_commitments.key")
            require_sha256(commitment, field="evidence_commitments.value")
        object.__setattr__(
            self,
            "evidence_commitments",
            freeze_mapping(self.evidence_commitments, field="evidence_commitments", nonempty=False),
        )
        parse_timestamp(self.quarantined_at, field="quarantined_at")
        if domain_hash("aureon.plumber.quarantine-record.v0", self.commitment_payload()) != self.record_commitment:
            raise SchemaError(DenialCode.INVALID_VALUE, field="record_commitment")

    @classmethod
    def build(
        cls,
        *,
        quarantine_id: str,
        packet_identity: str,
        session_identity: str,
        packet_commitment: str,
        denial_codes: Sequence[DenialCode | str],
        evidence_commitments: Mapping[str, str],
        quarantined_at: datetime,
    ) -> Self:
        normalized_codes = tuple(sorted({str(code) for code in denial_codes}))
        normalized_evidence = dict(evidence_commitments)
        quarantined_at_text = format_timestamp(quarantined_at)
        values = {
            "schema": QUARANTINE_SCHEMA,
            "quarantine_id": quarantine_id,
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "packet_commitment": packet_commitment,
            "denial_codes": normalized_codes,
            "evidence_commitments": normalized_evidence,
            "quarantined_at": quarantined_at_text,
        }
        return cls(
            schema=QUARANTINE_SCHEMA,
            quarantine_id=quarantine_id,
            packet_identity=packet_identity,
            session_identity=session_identity,
            packet_commitment=packet_commitment,
            denial_codes=normalized_codes,
            evidence_commitments=normalized_evidence,
            quarantined_at=quarantined_at_text,
            record_commitment=domain_hash("aureon.plumber.quarantine-record.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        parsed = require_exact_keys(value, _FIELDS, field="quarantine_record")
        if not isinstance(parsed["denial_codes"], list):
            raise SchemaError(DenialCode.INVALID_TYPE, field="denial_codes")
        parsed["denial_codes"] = tuple(parsed["denial_codes"])
        return cls(**parsed)

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "quarantine_id": self.quarantine_id,
            "packet_identity": self.packet_identity,
            "session_identity": self.session_identity,
            "packet_commitment": self.packet_commitment,
            "denial_codes": list(self.denial_codes),
            "evidence_commitments": dict(self.evidence_commitments),
            "quarantined_at": self.quarantined_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "record_commitment": self.record_commitment}

    def public_summary(self) -> dict[str, Any]:
        return self.to_dict()


__all__ = ["QUARANTINE_SCHEMA", "QuarantineRecord"]
