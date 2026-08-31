"""Replay-resistant temporal identity for Aureon Plumber v0."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from .crypto import domain_hash
from .schema import (
    DenialCode,
    SchemaError,
    format_timestamp,
    parse_timestamp,
    require_aware_datetime,
    require_exact_keys,
    require_int,
    require_nonblank,
    require_sha256,
)

TEMPORAL_IDENTITY_SCHEMA = "aureon.plumber.temporal-identity.v0"
_FIELDS = (
    "schema",
    "packet_identity",
    "session_identity",
    "previous_state_commitment",
    "nonce_commitment",
    "counter",
    "field_receipt_commitment",
    "observer_receipt_commitment",
    "runtime_measurement_commitment",
    "issued_at",
    "expires_at",
    "temporal_commitment",
)


@dataclass(frozen=True, slots=True)
class TemporalValidation:
    valid: bool
    denial_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TemporalIdentityV0:
    schema: str
    packet_identity: str
    session_identity: str
    previous_state_commitment: str
    nonce_commitment: str
    counter: int
    field_receipt_commitment: str
    observer_receipt_commitment: str
    runtime_measurement_commitment: str
    issued_at: str
    expires_at: str
    temporal_commitment: str

    def __post_init__(self) -> None:
        if self.schema != TEMPORAL_IDENTITY_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        require_nonblank(self.packet_identity, field="packet_identity")
        require_nonblank(self.session_identity, field="session_identity")
        require_int(self.counter, field="counter", minimum=1)
        for field in (
            "previous_state_commitment",
            "nonce_commitment",
            "field_receipt_commitment",
            "observer_receipt_commitment",
            "runtime_measurement_commitment",
            "temporal_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        issued = parse_timestamp(self.issued_at, field="issued_at")
        expires = parse_timestamp(self.expires_at, field="expires_at")
        if expires <= issued:
            raise SchemaError(DenialCode.INVALID_VALUE, field="expires_at")
        if domain_hash("aureon.plumber.temporal-identity.v0", self.commitment_payload()) != self.temporal_commitment:
            raise SchemaError(DenialCode.TEMPORAL_IDENTITY_MISMATCH, field="temporal_commitment")

    @classmethod
    def build(
        cls,
        *,
        packet_identity: str,
        session_identity: str,
        previous_state_commitment: str,
        nonce_commitment: str,
        counter: int,
        field_receipt_commitment: str,
        observer_receipt_commitment: str,
        runtime_measurement_commitment: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> Self:
        issued_at_text = format_timestamp(issued_at)
        expires_at_text = format_timestamp(expires_at)
        values = {
            "schema": TEMPORAL_IDENTITY_SCHEMA,
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "previous_state_commitment": previous_state_commitment,
            "nonce_commitment": nonce_commitment,
            "counter": counter,
            "field_receipt_commitment": field_receipt_commitment,
            "observer_receipt_commitment": observer_receipt_commitment,
            "runtime_measurement_commitment": runtime_measurement_commitment,
            "issued_at": issued_at_text,
            "expires_at": expires_at_text,
        }
        return cls(
            schema=TEMPORAL_IDENTITY_SCHEMA,
            packet_identity=packet_identity,
            session_identity=session_identity,
            previous_state_commitment=previous_state_commitment,
            nonce_commitment=nonce_commitment,
            counter=counter,
            field_receipt_commitment=field_receipt_commitment,
            observer_receipt_commitment=observer_receipt_commitment,
            runtime_measurement_commitment=runtime_measurement_commitment,
            issued_at=issued_at_text,
            expires_at=expires_at_text,
            temporal_commitment=domain_hash("aureon.plumber.temporal-identity.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _FIELDS, field="temporal_identity"))

    def commitment_payload(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _FIELDS if field != "temporal_commitment"}

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _FIELDS}

    def validate(
        self,
        *,
        now: datetime,
        expected_previous_state_commitment: str,
        minimum_counter: int,
        seen_temporal_commitments: Collection[str] = (),
        seen_nonce_commitments: Collection[str] = (),
    ) -> TemporalValidation:
        if isinstance(seen_temporal_commitments, (str, bytes)) or not isinstance(
            seen_temporal_commitments,
            Collection,
        ):
            raise SchemaError(DenialCode.INVALID_TYPE, field="seen_temporal_commitments")
        if isinstance(seen_nonce_commitments, (str, bytes)) or not isinstance(
            seen_nonce_commitments,
            Collection,
        ):
            raise SchemaError(DenialCode.INVALID_TYPE, field="seen_nonce_commitments")
        denials: set[str] = set()
        current = require_aware_datetime(now, field="now")
        if current < parse_timestamp(self.issued_at, field="issued_at"):
            denials.add(str(DenialCode.FUTURE_STATE))
        if current >= parse_timestamp(self.expires_at, field="expires_at"):
            denials.add(str(DenialCode.STALE_STATE))
        if self.previous_state_commitment != expected_previous_state_commitment:
            denials.add(str(DenialCode.PREVIOUS_STATE_MISMATCH))
        if self.counter <= minimum_counter:
            denials.add(str(DenialCode.COUNTER_ROLLBACK))
        if self.temporal_commitment in seen_temporal_commitments or self.nonce_commitment in seen_nonce_commitments:
            denials.add(str(DenialCode.REPLAY_DETECTED))
        return TemporalValidation(valid=not denials, denial_codes=tuple(sorted(denials)))

    def public_summary(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "packet_identity": self.packet_identity,
            "session_identity": self.session_identity,
            "counter": self.counter,
            "previous_state_commitment": self.previous_state_commitment,
            "nonce_commitment": self.nonce_commitment,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "temporal_commitment": self.temporal_commitment,
        }


def build_temporal_identity(**values: Any) -> TemporalIdentityV0:
    return TemporalIdentityV0.build(**values)


def validate_temporal_identity(identity: TemporalIdentityV0, **expectations: Any) -> TemporalValidation:
    return identity.validate(**expectations)


__all__ = [
    "TEMPORAL_IDENTITY_SCHEMA",
    "TemporalIdentityV0",
    "TemporalValidation",
    "build_temporal_identity",
    "validate_temporal_identity",
]
