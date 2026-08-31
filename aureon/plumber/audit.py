"""In-memory, metadata-only audit records for the Plumber protocol."""

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
    require_mapping,
    require_nonblank,
    require_sha256,
)

_FORBIDDEN_PUBLIC_KEYS = {
    "plaintext",
    "decrypted_payload",
    "private_key",
    "root_key",
    "session_key",
    "raw_share",
    "secret_value",
}


def assert_public_summary_safe(value: Mapping[str, Any]) -> None:
    """Reject common secret-bearing fields before a summary crosses a boundary."""

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if not isinstance(key, str) or key.casefold() in _FORBIDDEN_PUBLIC_KEYS:
                    raise SchemaError(DenialCode.INVALID_SCHEMA, field="public_summary")
                walk(nested)
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for nested in item:
                walk(nested)

    walk(value)


_AUDIT_FIELDS = (
    "event_type",
    "trace_id",
    "packet_identity",
    "session_identity",
    "outcome",
    "denial_codes",
    "evidence_commitments",
    "recorded_at",
    "event_commitment",
)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str
    trace_id: str
    packet_identity: str
    session_identity: str
    outcome: str
    denial_codes: tuple[str, ...]
    evidence_commitments: Mapping[str, str]
    recorded_at: str
    event_commitment: str

    def __post_init__(self) -> None:
        for field in ("event_type", "trace_id", "packet_identity", "session_identity", "outcome"):
            require_nonblank(getattr(self, field), field=field)
        parse_timestamp(self.recorded_at, field="recorded_at")
        require_sha256(self.event_commitment, field="event_commitment")
        if not isinstance(self.denial_codes, tuple) or any(
            not isinstance(code, str) or not code for code in self.denial_codes
        ):
            raise SchemaError(DenialCode.INVALID_TYPE, field="denial_codes")
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        evidence = require_mapping(self.evidence_commitments, field="evidence_commitments", nonempty=False)
        for key, commitment in evidence.items():
            require_nonblank(key, field="evidence_commitments.key")
            require_sha256(commitment, field="evidence_commitments.value")
        object.__setattr__(
            self,
            "evidence_commitments",
            freeze_mapping(evidence, field="evidence_commitments", nonempty=False),
        )
        if domain_hash("aureon.plumber.audit.v0", self.commitment_payload()) != self.event_commitment:
            raise SchemaError(DenialCode.INVALID_VALUE, field="event_commitment")

    @classmethod
    def build(
        cls,
        *,
        event_type: str,
        trace_id: str,
        packet_identity: str,
        session_identity: str,
        outcome: str,
        denial_codes: Sequence[DenialCode | str] = (),
        evidence_commitments: Mapping[str, str] | None = None,
        recorded_at: datetime,
    ) -> Self:
        normalized_codes = tuple(sorted({str(code) for code in denial_codes}))
        normalized_evidence = dict(evidence_commitments or {})
        recorded_at_text = format_timestamp(recorded_at)
        values = {
            "event_type": event_type,
            "trace_id": trace_id,
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "outcome": outcome,
            "denial_codes": normalized_codes,
            "evidence_commitments": normalized_evidence,
            "recorded_at": recorded_at_text,
        }
        return cls(
            event_type=event_type,
            trace_id=trace_id,
            packet_identity=packet_identity,
            session_identity=session_identity,
            outcome=outcome,
            denial_codes=normalized_codes,
            evidence_commitments=normalized_evidence,
            recorded_at=recorded_at_text,
            event_commitment=domain_hash("aureon.plumber.audit.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        parsed = require_exact_keys(value, _AUDIT_FIELDS, field="audit_event")
        if not isinstance(parsed["denial_codes"], list):
            raise SchemaError(DenialCode.INVALID_TYPE, field="denial_codes")
        parsed["denial_codes"] = tuple(parsed["denial_codes"])
        return cls(**parsed)

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "trace_id": self.trace_id,
            "packet_identity": self.packet_identity,
            "session_identity": self.session_identity,
            "outcome": self.outcome,
            "denial_codes": list(self.denial_codes),
            "evidence_commitments": dict(self.evidence_commitments),
            "recorded_at": self.recorded_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "event_commitment": self.event_commitment}

    def public_summary(self) -> dict[str, Any]:
        summary = self.to_dict()
        assert_public_summary_safe(summary)
        return summary


__all__ = ["AuditEvent", "assert_public_summary_safe"]
