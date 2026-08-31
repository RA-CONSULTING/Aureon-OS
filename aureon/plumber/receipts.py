"""Signed, purpose-bound receipts for the foundational Plumber protocol."""

from __future__ import annotations

from collections.abc import Mapping
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

RECEIPT_SCHEMA = "aureon.plumber.receipt.v0"
_RECEIPT_SIGNATURE_DOMAIN = "aureon.plumber.receipt.signature.v0"


class ReceiptKind(StrEnum):
    FIELD = "field"
    OBSERVER = "observer"
    HEART = "heart"
    CONSCIENCE = "conscience"
    GOVERNANCE = "governance"
    SOURCE = "source"
    OPERATOR = "operator"


class ReceiptVerdict(StrEnum):
    APPROVED = "approved"
    DENIED = "denied"


_RECEIPT_FIELDS = (
    "schema",
    "kind",
    "packet_identity",
    "session_identity",
    "purpose_commitment",
    "source_identity_commitment",
    "temporal_identity_commitment",
    "observer_transcript_commitment",
    "policy_commitment",
    "runtime_measurement_commitment",
    "verdict",
    "issued_at",
    "expires_at",
    "signer_id",
    "signer_public_key",
    "receipt_hash",
    "signature",
)


@dataclass(frozen=True, slots=True)
class ReceiptValidation:
    valid: bool
    denial_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SignedReceipt:
    schema: str
    kind: str
    packet_identity: str
    session_identity: str
    purpose_commitment: str
    source_identity_commitment: str
    temporal_identity_commitment: str
    observer_transcript_commitment: str
    policy_commitment: str
    runtime_measurement_commitment: str
    verdict: str
    issued_at: str
    expires_at: str
    signer_id: str
    signer_public_key: str
    receipt_hash: str
    signature: str

    def __post_init__(self) -> None:
        if self.schema != RECEIPT_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        try:
            ReceiptKind(self.kind)
            ReceiptVerdict(self.verdict)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="receipt_enum") from exc
        for field in ("packet_identity", "session_identity", "signer_id"):
            require_nonblank(getattr(self, field), field=field)
        for field in (
            "purpose_commitment",
            "source_identity_commitment",
            "temporal_identity_commitment",
            "observer_transcript_commitment",
            "policy_commitment",
            "runtime_measurement_commitment",
            "receipt_hash",
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
        kind: ReceiptKind | str,
        packet_identity: str,
        session_identity: str,
        purpose_commitment: str,
        source_identity_commitment: str,
        temporal_identity_commitment: str,
        observer_transcript_commitment: str,
        policy_commitment: str,
        runtime_measurement_commitment: str,
        verdict: ReceiptVerdict | str,
        issued_at: datetime,
        expires_at: datetime,
        signer_id: str,
        private_key: Ed25519PrivateKey | bytes | str,
    ) -> Self:
        key = load_ed25519_private_key(private_key)
        values: dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "kind": str(ReceiptKind(kind)),
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "purpose_commitment": purpose_commitment,
            "source_identity_commitment": source_identity_commitment,
            "temporal_identity_commitment": temporal_identity_commitment,
            "observer_transcript_commitment": observer_transcript_commitment,
            "policy_commitment": policy_commitment,
            "runtime_measurement_commitment": runtime_measurement_commitment,
            "verdict": str(ReceiptVerdict(verdict)),
            "issued_at": format_timestamp(issued_at),
            "expires_at": format_timestamp(expires_at),
            "signer_id": signer_id,
            "signer_public_key": ed25519_public_key_hex(key),
        }
        receipt_hash = domain_hash("aureon.plumber.receipt.v0", values)
        signature = sign_ed25519(key, {"receipt_hash": receipt_hash}, domain=_RECEIPT_SIGNATURE_DOMAIN)
        return cls(**values, receipt_hash=receipt_hash, signature=signature)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _RECEIPT_FIELDS, field="receipt"))

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in _RECEIPT_FIELDS
            if field not in {"receipt_hash", "signature"}
        }

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _RECEIPT_FIELDS}

    def validate(
        self,
        *,
        now: datetime,
        expected_packet_identity: str | None = None,
        expected_session_identity: str | None = None,
        expected_purpose_commitment: str | None = None,
        expected_signer_public_key: str | None = None,
        require_approved: bool = True,
    ) -> ReceiptValidation:
        denials: set[str] = set()
        if domain_hash("aureon.plumber.receipt.v0", self.unsigned_payload()) != self.receipt_hash:
            denials.add(str(DenialCode.INVALID_SIGNATURE))
        if not verify_ed25519(
            self.signer_public_key,
            {"receipt_hash": self.receipt_hash},
            self.signature,
            domain=_RECEIPT_SIGNATURE_DOMAIN,
        ):
            denials.add(str(DenialCode.INVALID_SIGNATURE))
        if expected_packet_identity is not None and self.packet_identity != expected_packet_identity:
            denials.add(str(DenialCode.PACKET_IDENTITY_MISMATCH))
        if expected_session_identity is not None and self.session_identity != expected_session_identity:
            denials.add(str(DenialCode.SESSION_IDENTITY_MISMATCH))
        if expected_purpose_commitment is not None and self.purpose_commitment != expected_purpose_commitment:
            denials.add(str(DenialCode.PURPOSE_MISMATCH))
        if expected_signer_public_key is not None and self.signer_public_key != expected_signer_public_key:
            denials.add(str(DenialCode.SIGNER_MISMATCH))
        current = require_aware_datetime(now, field="now")
        if current < parse_timestamp(self.issued_at, field="issued_at"):
            denials.add(str(DenialCode.FUTURE_STATE))
        if current >= parse_timestamp(self.expires_at, field="expires_at"):
            denials.add(str(DenialCode.STALE_STATE))
        if require_approved and self.verdict != ReceiptVerdict.APPROVED:
            denials.add(str(DenialCode.POLICY_RECEIPT_INVALID))
        return ReceiptValidation(valid=not denials, denial_codes=tuple(sorted(denials)))

    def public_summary(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "kind": self.kind,
            "packet_identity": self.packet_identity,
            "session_identity": self.session_identity,
            "purpose_commitment": self.purpose_commitment,
            "verdict": self.verdict,
            "expires_at": self.expires_at,
            "signer_id": self.signer_id,
            "signer_public_key": self.signer_public_key,
            "receipt_hash": self.receipt_hash,
        }


def sign_receipt(**values: Any) -> SignedReceipt:
    """Compatibility-friendly function form of :meth:`SignedReceipt.issue`."""

    return SignedReceipt.issue(**values)


def validate_receipt(receipt: SignedReceipt, **expectations: Any) -> ReceiptValidation:
    return receipt.validate(**expectations)


__all__ = [
    "RECEIPT_SCHEMA",
    "ReceiptKind",
    "ReceiptValidation",
    "ReceiptVerdict",
    "SignedReceipt",
    "sign_receipt",
    "validate_receipt",
]
