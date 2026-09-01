"""Fail-closed v0.3 contract for an out-of-process Magic Star broker.

This module defines and verifies the metadata crossing a production release
boundary.  It deliberately contains no decryptor, capability callback, network
client, HSM key, or provider mutation.  A production composition must implement
the canonical-wire protocols below and use four pinned, distinct review,
dispatch, executor, and receipt authorities.

``SQLiteTerminalLedgerV03`` is a durable reference implementation for local
integration and crash tests.  It is not an independently administered
production ledger, but it does prove the required one-use/idempotency semantics
across process restarts.  An expired, uncertain claim is never made retryable
or falsely terminal: it remains unresolved until independently reconciled with
authentic executor/provider evidence.
"""

from __future__ import annotations

import re
import secrets
import sqlite3
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Protocol, TypeAlias, cast, runtime_checkable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .audit import assert_public_summary_safe
from .crypto import (
    canonical_json_bytes,
    decode_canonical_json,
    domain_hash,
    sign_ed25519,
    verify_ed25519,
)

COMMAND_SCHEMA: Final = "aureon.plumber.production-release-command.v03"
DISPATCH_SCHEMA: Final = "aureon.plumber.production-dispatch-claim.v03"
REVIEW_SCHEMA: Final = "aureon.plumber.production-review-authorization.v03"
EXECUTOR_EVIDENCE_SCHEMA: Final = "aureon.plumber.production-executor-evidence.v03"
RELEASE_RECEIPT_SCHEMA: Final = "aureon.plumber.production-release-receipt.v03"
DENIED_RECEIPT_SCHEMA: Final = "aureon.plumber.production-denied-receipt.v03"
LEDGER_SCHEMA: Final = "aureon.plumber.production-terminal-ledger.v03"

REVIEW_SIGNATURE_DOMAIN: Final = "AUREON-PLUMBER-V03-REVIEW-AUTHORIZATION"
DISPATCH_SIGNATURE_DOMAIN: Final = "AUREON-PLUMBER-V03-DISPATCH-CLAIM"
EXECUTOR_SIGNATURE_DOMAIN: Final = "AUREON-PLUMBER-V03-EXECUTOR-EVIDENCE"
RECEIPT_SIGNATURE_DOMAIN: Final = "AUREON-PLUMBER-V03-TERMINAL-RECEIPT"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE = re.compile(r"^[0-9a-f]{128}$")
_MAX_COMMAND_LIFETIME_MS = 15 * 60 * 1000
_MAX_CLOCK_SKEW_MS = 5_000
_MAX_WIRE_BYTES = 64 * 1024
_MAX_SAFE_INTEGER = (1 << 53) - 1
_ZERO_SHA256 = "0" * 64


class ProductionReleaseBrokerError(ValueError):
    """Stable, non-secret contract or durable-state failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _identifier(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ProductionReleaseBrokerError(code)
    return value


def _opaque_id(value: object, *, code: str) -> str:
    """Require a fixed-width opaque identifier, never caller-chosen plaintext."""

    return _sha256(value, code=code)


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ProductionReleaseBrokerError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > _MAX_SAFE_INTEGER
    ):
        raise ProductionReleaseBrokerError(code)
    return value


def _signature(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SIGNATURE.fullmatch(value) is None:
        raise ProductionReleaseBrokerError(code)
    return value


def _exact_mapping(value: object, keys: set[str], *, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ProductionReleaseBrokerError(code)
    return dict(value)


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _decode_wire_mapping(data: bytes | str, *, code: str) -> dict[str, Any]:
    try:
        decoded = decode_canonical_json(
            data,
            require_mapping=True,
            max_bytes=_MAX_WIRE_BYTES,
        )
    except BaseException:
        raise ProductionReleaseBrokerError(code) from None
    if not isinstance(decoded, dict):  # pragma: no cover - require_mapping
        raise ProductionReleaseBrokerError(code)
    return decoded


def _decode_stored_receipt(value: object) -> dict[str, Any]:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, bytearray | memoryview):
        raw = bytes(value)
    else:
        raise ProductionReleaseBrokerError("stored_receipt_invalid")
    return _decode_wire_mapping(raw, code="stored_receipt_invalid")


@dataclass(frozen=True, slots=True)
class AuthorityBindingV03:
    """One pinned public authority identity; never private key custody."""

    role: str
    authority_id: str
    key_id: str
    public_key_hex: str

    def __post_init__(self) -> None:
        _identifier(self.role, code="authority_role_invalid")
        _identifier(self.authority_id, code="authority_id_invalid")
        _identifier(self.key_id, code="authority_key_id_invalid")
        if (
            not isinstance(self.public_key_hex, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.public_key_hex) is None
        ):
            raise ProductionReleaseBrokerError("authority_public_key_invalid")

    def public_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "authority_id": self.authority_id,
            "key_id": self.key_id,
            "public_key_hex": self.public_key_hex,
        }


def _require_distinct_authorities(
    review: AuthorityBindingV03,
    dispatch: AuthorityBindingV03,
    executor: AuthorityBindingV03,
    receipt: AuthorityBindingV03,
) -> None:
    expected = (
        (review, "REVIEW"),
        (dispatch, "DISPATCH"),
        (executor, "EXECUTOR"),
        (receipt, "RECEIPT"),
    )
    if any(binding.role != role for binding, role in expected):
        raise ProductionReleaseBrokerError("authority_role_binding_invalid")
    bindings = (review, dispatch, executor, receipt)
    for field, code in (
        ("authority_id", "authority_ids_not_distinct"),
        ("key_id", "authority_key_ids_not_distinct"),
        ("public_key_hex", "authority_public_keys_not_distinct"),
    ):
        values = {getattr(binding, field) for binding in bindings}
        if len(values) != 4:
            raise ProductionReleaseBrokerError(code)


@dataclass(frozen=True, slots=True)
class ReleaseCommandV03:
    command_id: str
    packet_commitment: str
    admission_commitment: str
    effect_id: str
    capability_id: str
    capability_measurement_sha256: str
    runtime_measurement_sha256: str
    authorization_context_sha256: str
    request_nonce: str
    issued_at_ms: int
    expires_at_ms: int
    schema: str = COMMAND_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != COMMAND_SCHEMA:
            raise ProductionReleaseBrokerError("release_command_schema_invalid")
        for value, code in (
            (self.command_id, "command_id_invalid"),
            (self.effect_id, "effect_id_invalid"),
            (self.capability_id, "capability_id_invalid"),
            (self.request_nonce, "request_nonce_invalid"),
        ):
            _opaque_id(value, code=code)
        for value, code in (
            (self.packet_commitment, "packet_commitment_invalid"),
            (self.admission_commitment, "admission_commitment_invalid"),
            (self.capability_measurement_sha256, "capability_measurement_invalid"),
            (self.runtime_measurement_sha256, "runtime_measurement_invalid"),
            (self.authorization_context_sha256, "authorization_context_invalid"),
        ):
            _sha256(value, code=code)
        issued = _uint(self.issued_at_ms, code="command_issued_at_invalid")
        expires = _uint(self.expires_at_ms, code="command_expires_at_invalid")
        if expires <= issued or expires - issued > _MAX_COMMAND_LIFETIME_MS:
            raise ProductionReleaseBrokerError("command_lifetime_invalid")

    def public_dict(self) -> dict[str, Any]:
        result = {
            "schema": self.schema,
            "command_id": self.command_id,
            "packet_commitment": self.packet_commitment,
            "admission_commitment": self.admission_commitment,
            "effect_id": self.effect_id,
            "capability_id": self.capability_id,
            "capability_measurement_sha256": self.capability_measurement_sha256,
            "runtime_measurement_sha256": self.runtime_measurement_sha256,
            "authorization_context_sha256": self.authorization_context_sha256,
            "request_nonce": self.request_nonce,
            "issued_at_ms": self.issued_at_ms,
            "expires_at_ms": self.expires_at_ms,
            "production_ready": False,
        }
        assert_public_summary_safe(result)
        return result

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V03-RELEASE-COMMAND", self.public_dict())

    def wire_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.public_dict().items()
            if key != "production_ready"
        }

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> ReleaseCommandV03:
        payload = _exact_mapping(
            value,
            {
                "schema", "command_id", "packet_commitment", "admission_commitment",
                "effect_id", "capability_id", "capability_measurement_sha256",
                "runtime_measurement_sha256", "authorization_context_sha256",
                "request_nonce", "issued_at_ms", "expires_at_ms",
            },
            code="release_command_shape_invalid",
        )
        try:
            return cls(**payload)
        except TypeError as exc:
            raise ProductionReleaseBrokerError("release_command_shape_invalid") from exc


@dataclass(frozen=True, slots=True)
class ReviewAuthorizationV03:
    review_id: str
    command_commitment: str
    decision: str
    issued_at_ms: int
    expires_at_ms: int
    authority_id: str
    key_id: str
    signature_hex: str
    schema: str = REVIEW_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != REVIEW_SCHEMA or self.decision != "ALLOW":
            raise ProductionReleaseBrokerError("review_authorization_invalid")
        _opaque_id(self.review_id, code="review_id_invalid")
        _sha256(self.command_commitment, code="review_command_commitment_invalid")
        _identifier(self.authority_id, code="review_authority_id_invalid")
        _identifier(self.key_id, code="review_key_id_invalid")
        _signature(self.signature_hex, code="review_signature_invalid")
        issued = _uint(self.issued_at_ms, code="review_issued_at_invalid")
        expires = _uint(self.expires_at_ms, code="review_expires_at_invalid")
        if expires <= issued or expires - issued > _MAX_COMMAND_LIFETIME_MS:
            raise ProductionReleaseBrokerError("review_lifetime_invalid")

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "review_id": self.review_id,
            "command_commitment": self.command_commitment,
            "decision": self.decision,
            "issued_at_ms": self.issued_at_ms,
            "expires_at_ms": self.expires_at_ms,
            "authority_id": self.authority_id,
            "key_id": self.key_id,
        }

    def wire_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature_hex": self.signature_hex}

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V03-REVIEW", self.wire_dict())


@dataclass(frozen=True, slots=True)
class DispatchClaimV03:
    """Durable, unpredictable claim that the executor must sign back."""

    command_commitment: str
    review_commitment: str
    effect_id: str
    request_nonce: str
    dispatch_nonce: str
    claimed_at_ms: int
    claim_expires_at_ms: int
    authority_id: str
    key_id: str
    signature_hex: str
    schema: str = DISPATCH_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != DISPATCH_SCHEMA:
            raise ProductionReleaseBrokerError("dispatch_claim_schema_invalid")
        for value, code in (
            (self.command_commitment, "dispatch_command_commitment_invalid"),
            (self.review_commitment, "dispatch_review_commitment_invalid"),
            (self.effect_id, "dispatch_effect_id_invalid"),
            (self.request_nonce, "dispatch_request_nonce_invalid"),
            (self.dispatch_nonce, "dispatch_nonce_invalid"),
        ):
            _sha256(value, code=code)
        claimed = _uint(self.claimed_at_ms, code="dispatch_claimed_at_invalid")
        expires = _uint(self.claim_expires_at_ms, code="dispatch_expires_at_invalid")
        if expires <= claimed or expires - claimed > _MAX_COMMAND_LIFETIME_MS:
            raise ProductionReleaseBrokerError("dispatch_lifetime_invalid")
        _identifier(self.authority_id, code="dispatch_authority_id_invalid")
        _identifier(self.key_id, code="dispatch_key_id_invalid")
        _signature(self.signature_hex, code="dispatch_signature_invalid")

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "command_commitment": self.command_commitment,
            "review_commitment": self.review_commitment,
            "effect_id": self.effect_id,
            "request_nonce": self.request_nonce,
            "dispatch_nonce": self.dispatch_nonce,
            "claimed_at_ms": self.claimed_at_ms,
            "claim_expires_at_ms": self.claim_expires_at_ms,
            "authority_id": self.authority_id,
            "key_id": self.key_id,
        }

    def wire_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature_hex": self.signature_hex}

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V03-DISPATCH-CLAIM", self.wire_dict())

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> DispatchClaimV03:
        payload = _exact_mapping(
            value,
            {
                "schema", "command_commitment", "review_commitment", "effect_id",
                "request_nonce", "dispatch_nonce", "claimed_at_ms",
                "claim_expires_at_ms", "authority_id", "key_id", "signature_hex",
            },
            code="dispatch_claim_shape_invalid",
        )
        try:
            return cls(**payload)
        except TypeError as exc:
            raise ProductionReleaseBrokerError("dispatch_claim_shape_invalid") from exc


class ExecutorOutcome(StrEnum):
    CONSUMED = "CONSUMED"
    DENIED = "DENIED"


@dataclass(frozen=True, slots=True)
class ExecutorTerminalEvidenceV03:
    evidence_id: str
    command_commitment: str
    review_commitment: str
    dispatch_commitment: str
    effect_id: str
    capability_id: str
    runtime_measurement_sha256: str
    request_nonce: str
    outcome: ExecutorOutcome
    result_sha256: str
    provider_readback_sha256: str
    reason_code: str
    terminal_at_ms: int
    authority_id: str
    key_id: str
    signature_hex: str
    schema: str = EXECUTOR_EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EXECUTOR_EVIDENCE_SCHEMA:
            raise ProductionReleaseBrokerError("executor_evidence_schema_invalid")
        if not isinstance(self.outcome, ExecutorOutcome):
            raise ProductionReleaseBrokerError("executor_outcome_invalid")
        for value, code in (
            (self.evidence_id, "executor_evidence_id_invalid"),
            (self.effect_id, "executor_effect_id_invalid"),
            (self.capability_id, "executor_capability_id_invalid"),
            (self.request_nonce, "executor_request_nonce_invalid"),
        ):
            _opaque_id(value, code=code)
        for value, code in (
            (self.reason_code, "executor_reason_code_invalid"),
            (self.authority_id, "executor_authority_id_invalid"),
            (self.key_id, "executor_key_id_invalid"),
        ):
            _identifier(value, code=code)
        for value, code in (
            (self.command_commitment, "executor_command_commitment_invalid"),
            (self.review_commitment, "executor_review_commitment_invalid"),
            (self.dispatch_commitment, "executor_dispatch_commitment_invalid"),
            (self.runtime_measurement_sha256, "executor_runtime_measurement_invalid"),
            (self.result_sha256, "executor_result_sha256_invalid"),
            (self.provider_readback_sha256, "executor_readback_sha256_invalid"),
        ):
            _sha256(value, code=code)
        _uint(self.terminal_at_ms, code="executor_terminal_at_invalid")
        _signature(self.signature_hex, code="executor_signature_invalid")
        if self.outcome is ExecutorOutcome.CONSUMED and (
            self.result_sha256 == _ZERO_SHA256
            or self.provider_readback_sha256 == _ZERO_SHA256
            or self.reason_code != "effect_consumed_with_provider_readback"
        ):
            raise ProductionReleaseBrokerError("consumed_executor_evidence_invalid")
        if self.outcome is ExecutorOutcome.DENIED and (
            self.result_sha256 != _ZERO_SHA256
            or self.provider_readback_sha256 == _ZERO_SHA256
            or self.reason_code != "effect_denied_with_provider_readback"
        ):
            raise ProductionReleaseBrokerError("denied_executor_evidence_invalid")

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "evidence_id": self.evidence_id,
            "command_commitment": self.command_commitment,
            "review_commitment": self.review_commitment,
            "dispatch_commitment": self.dispatch_commitment,
            "effect_id": self.effect_id,
            "capability_id": self.capability_id,
            "runtime_measurement_sha256": self.runtime_measurement_sha256,
            "request_nonce": self.request_nonce,
            "outcome": self.outcome.value,
            "result_sha256": self.result_sha256,
            "provider_readback_sha256": self.provider_readback_sha256,
            "reason_code": self.reason_code,
            "terminal_at_ms": self.terminal_at_ms,
            "authority_id": self.authority_id,
            "key_id": self.key_id,
        }

    def wire_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature_hex": self.signature_hex}

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V03-EXECUTOR-EVIDENCE", self.wire_dict())


class ReceiptDisposition(StrEnum):
    RELEASED = "RELEASED"
    DENIED = "DENIED"


@dataclass(frozen=True, slots=True)
class _TerminalReceiptV03:
    receipt_id: str
    command_commitment: str
    review_commitment: str
    executor_evidence_commitment: str
    effect_id: str
    request_nonce: str
    disposition: ReceiptDisposition
    reason_code: str
    terminal_at_ms: int
    authority_id: str
    key_id: str
    signature_hex: str
    effect_retry_authorized: bool = False
    production_ready: bool = False

    def _validate(self, *, expected_schema: str) -> None:
        if getattr(self, "schema", None) != expected_schema:
            raise ProductionReleaseBrokerError("terminal_receipt_schema_invalid")
        for value, code in (
            (self.receipt_id, "terminal_receipt_id_invalid"),
            (self.effect_id, "terminal_effect_id_invalid"),
            (self.request_nonce, "terminal_request_nonce_invalid"),
        ):
            _opaque_id(value, code=code)
        for value, code in (
            (self.reason_code, "terminal_reason_code_invalid"),
            (self.authority_id, "terminal_authority_id_invalid"),
            (self.key_id, "terminal_key_id_invalid"),
        ):
            _identifier(value, code=code)
        for value, code in (
            (self.command_commitment, "terminal_command_commitment_invalid"),
            (self.review_commitment, "terminal_review_commitment_invalid"),
            (self.executor_evidence_commitment, "terminal_executor_evidence_invalid"),
        ):
            _sha256(value, code=code)
        _uint(self.terminal_at_ms, code="terminal_at_invalid")
        _signature(self.signature_hex, code="terminal_signature_invalid")
        if self.effect_retry_authorized is not False or self.production_ready is not False:
            raise ProductionReleaseBrokerError("terminal_scope_invalid")

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,  # type: ignore[attr-defined]
            "receipt_id": self.receipt_id,
            "command_commitment": self.command_commitment,
            "review_commitment": self.review_commitment,
            "executor_evidence_commitment": self.executor_evidence_commitment,
            "effect_id": self.effect_id,
            "request_nonce": self.request_nonce,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "terminal_at_ms": self.terminal_at_ms,
            "authority_id": self.authority_id,
            "key_id": self.key_id,
            "effect_retry_authorized": self.effect_retry_authorized,
            "production_ready": self.production_ready,
        }

    def wire_dict(self) -> dict[str, Any]:
        result = {**self.unsigned_dict(), "signature_hex": self.signature_hex}
        assert_public_summary_safe(result)
        return result

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V03-TERMINAL-RECEIPT", self.wire_dict())


@dataclass(frozen=True, slots=True)
class ReleaseReceiptV03(_TerminalReceiptV03):
    schema: str = RELEASE_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        self._validate(expected_schema=RELEASE_RECEIPT_SCHEMA)
        if (
            self.disposition is not ReceiptDisposition.RELEASED
            or self.reason_code != "effect_consumed_with_provider_readback"
            or self.executor_evidence_commitment == _ZERO_SHA256
        ):
            raise ProductionReleaseBrokerError("release_receipt_invalid")


@dataclass(frozen=True, slots=True)
class DeniedReceiptV03(_TerminalReceiptV03):
    schema: str = DENIED_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        self._validate(expected_schema=DENIED_RECEIPT_SCHEMA)
        if self.disposition is not ReceiptDisposition.DENIED:
            raise ProductionReleaseBrokerError("denied_receipt_invalid")
        if (
            self.reason_code != "effect_denied_with_provider_readback"
            or self.executor_evidence_commitment == _ZERO_SHA256
        ):
            raise ProductionReleaseBrokerError("denied_receipt_invalid")


TerminalReceiptV03: TypeAlias = ReleaseReceiptV03 | DeniedReceiptV03


def decode_release_command_v03(data: bytes | str) -> ReleaseCommandV03:
    """Decode one bounded canonical command with an exact key set."""

    return ReleaseCommandV03.from_wire(
        _decode_wire_mapping(data, code="release_command_wire_invalid")
    )


def decode_dispatch_claim_v03(data: bytes | str) -> DispatchClaimV03:
    """Decode one bounded canonical durable dispatch claim."""

    return DispatchClaimV03.from_wire(
        _decode_wire_mapping(data, code="dispatch_claim_wire_invalid")
    )


def decode_review_authorization_v03(data: bytes | str) -> ReviewAuthorizationV03:
    payload = _exact_mapping(
        _decode_wire_mapping(data, code="review_authorization_wire_invalid"),
        {
            "schema", "review_id", "command_commitment", "decision",
            "issued_at_ms", "expires_at_ms", "authority_id", "key_id",
            "signature_hex",
        },
        code="review_authorization_shape_invalid",
    )
    try:
        return ReviewAuthorizationV03(**payload)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ProductionReleaseBrokerError):
            raise
        raise ProductionReleaseBrokerError("review_authorization_shape_invalid") from exc


def decode_executor_evidence_v03(data: bytes | str) -> ExecutorTerminalEvidenceV03:
    payload = _exact_mapping(
        _decode_wire_mapping(data, code="executor_evidence_wire_invalid"),
        {
            "schema", "evidence_id", "command_commitment", "review_commitment",
            "dispatch_commitment", "effect_id",
            "capability_id", "runtime_measurement_sha256", "request_nonce",
            "outcome", "result_sha256", "provider_readback_sha256",
            "reason_code", "terminal_at_ms", "authority_id", "key_id",
            "signature_hex",
        },
        code="executor_evidence_shape_invalid",
    )
    try:
        payload["outcome"] = ExecutorOutcome(payload["outcome"])
        return ExecutorTerminalEvidenceV03(**payload)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ProductionReleaseBrokerError):
            raise
        raise ProductionReleaseBrokerError("executor_evidence_shape_invalid") from exc


def decode_terminal_receipt_v03(data: bytes | str) -> TerminalReceiptV03:
    payload = _exact_mapping(
        _decode_wire_mapping(data, code="terminal_receipt_wire_invalid"),
        {
            "schema", "receipt_id", "command_commitment", "review_commitment",
            "executor_evidence_commitment", "effect_id", "request_nonce",
            "disposition", "reason_code", "terminal_at_ms", "authority_id",
            "key_id", "effect_retry_authorized", "production_ready",
            "signature_hex",
        },
        code="terminal_receipt_shape_invalid",
    )
    try:
        payload["disposition"] = ReceiptDisposition(payload["disposition"])
        schema = payload.get("schema")
        if schema == RELEASE_RECEIPT_SCHEMA:
            return ReleaseReceiptV03(**payload)
        if schema == DENIED_RECEIPT_SCHEMA:
            return DeniedReceiptV03(**payload)
        raise ProductionReleaseBrokerError("terminal_receipt_schema_invalid")
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ProductionReleaseBrokerError):
            raise
        raise ProductionReleaseBrokerError("terminal_receipt_shape_invalid") from exc


@runtime_checkable
class DispatchClaimSignerV03(Protocol):
    """Canonical-wire adapter for an independently held dispatch key."""

    signer_id: str
    key_id: str

    def sign_dispatch(
        self,
        unsigned_dispatch_wire: bytes,
        *,
        deadline_at_ms: int,
    ) -> bytes: ...


@runtime_checkable
class OutOfProcessReleaseExecutorV03(Protocol):
    """Canonical-wire adapter for a separately isolated executor service.

    A Python protocol cannot itself prove process or administrative isolation;
    the checked-in broker therefore remains non-production until its concrete
    transport and remote service are independently attested.
    """

    executor_id: str

    def execute(
        self,
        command_wire: bytes,
        review_wire: bytes,
        dispatch_wire: bytes,
    ) -> bytes: ...


@runtime_checkable
class TerminalReceiptSignerV03(Protocol):
    """Canonical-wire adapter for an independent remote receipt authority.

    Production implementations must durably deduplicate by the executor
    evidence commitment and return that same signed receipt through readback.
    """

    signer_id: str

    def sign_terminal(
        self,
        command_wire: bytes,
        review_wire: bytes,
        evidence_wire: bytes,
        *,
        idempotency_key: str,
    ) -> bytes: ...

    def read_terminal(self, *, idempotency_key: str) -> bytes | None: ...


def terminal_receipt_id_v03(executor_evidence_commitment: str) -> str:
    """Derive the sole permitted receipt identity for terminal evidence."""

    _sha256(
        executor_evidence_commitment,
        code="terminal_executor_evidence_invalid",
    )
    return domain_hash(
        "AUREON-PLUMBER-V03-TERMINAL-RECEIPT-ID",
        {"executor_evidence_commitment": executor_evidence_commitment},
    )


class ProductionReleaseVerifierV03:
    """Verify exact joins and four independent pinned signatures."""

    production_ready = False

    def __init__(
        self,
        *,
        review_authority: AuthorityBindingV03,
        dispatch_authority: AuthorityBindingV03,
        executor_authority: AuthorityBindingV03,
        receipt_authority: AuthorityBindingV03,
        trusted_now_ms: Callable[[], int] = _system_now_ms,
        max_clock_skew_ms: int = _MAX_CLOCK_SKEW_MS,
    ) -> None:
        _require_distinct_authorities(
            review_authority,
            dispatch_authority,
            executor_authority,
            receipt_authority,
        )
        if not callable(trusted_now_ms):
            raise ProductionReleaseBrokerError("trusted_clock_invalid")
        skew = _uint(max_clock_skew_ms, code="clock_skew_policy_invalid")
        if skew > 60_000:
            raise ProductionReleaseBrokerError("clock_skew_policy_invalid")
        self._review = review_authority
        self._dispatch = dispatch_authority
        self._executor = executor_authority
        self._receipt = receipt_authority
        self._trusted_now_ms = trusted_now_ms
        self._max_clock_skew_ms = skew

    @property
    def authority_ids(self) -> dict[str, str]:
        """Return only pinned public identities for composition checks."""

        return {
            "review": self._review.authority_id,
            "dispatch": self._dispatch.authority_id,
            "executor": self._executor.authority_id,
            "receipt": self._receipt.authority_id,
        }

    def _now(self) -> int:
        return _uint(self._trusted_now_ms(), code="trusted_time_invalid")

    def verify_review(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        require_current: bool = True,
    ) -> None:
        now = self._now()
        if (
            type(command) is not ReleaseCommandV03
            or type(review) is not ReviewAuthorizationV03
            or review.command_commitment != command.commitment
            or review.authority_id != self._review.authority_id
            or review.key_id != self._review.key_id
            or review.expires_at_ms > command.expires_at_ms
            or review.issued_at_ms < command.issued_at_ms - self._max_clock_skew_ms
            or (
                require_current
                and (
                    now < review.issued_at_ms - self._max_clock_skew_ms
                    or now >= review.expires_at_ms
                    or now >= command.expires_at_ms
                )
            )
        ):
            raise ProductionReleaseBrokerError("review_authorization_join_or_time_invalid")
        if not verify_ed25519(
            self._review.public_key_hex,
            review.unsigned_dict(),
            review.signature_hex,
            domain=REVIEW_SIGNATURE_DOMAIN,
        ):
            raise ProductionReleaseBrokerError("review_signature_invalid")

    def verify_dispatch(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        dispatch: DispatchClaimV03,
        *,
        require_current: bool = False,
    ) -> None:
        """Authenticate the ledger-issued dispatch and its exact joins."""

        self.verify_review(command, review, require_current=require_current)
        now = self._now()
        if (
            type(dispatch) is not DispatchClaimV03
            or dispatch.command_commitment != command.commitment
            or dispatch.review_commitment != review.commitment
            or dispatch.effect_id != command.effect_id
            or dispatch.request_nonce != command.request_nonce
            or dispatch.claimed_at_ms < review.issued_at_ms
            or dispatch.claimed_at_ms > now + self._max_clock_skew_ms
            or dispatch.claim_expires_at_ms > command.expires_at_ms
            or dispatch.claim_expires_at_ms > review.expires_at_ms
            or dispatch.authority_id != self._dispatch.authority_id
            or dispatch.key_id != self._dispatch.key_id
            or (
                require_current
                and (
                    now < dispatch.claimed_at_ms - self._max_clock_skew_ms
                    or now >= dispatch.claim_expires_at_ms
                )
            )
        ):
            raise ProductionReleaseBrokerError("dispatch_claim_join_or_time_invalid")
        if not verify_ed25519(
            self._dispatch.public_key_hex,
            dispatch.unsigned_dict(),
            dispatch.signature_hex,
            domain=DISPATCH_SIGNATURE_DOMAIN,
        ):
            raise ProductionReleaseBrokerError("dispatch_signature_invalid")

    def verify_executor_evidence(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        dispatch: DispatchClaimV03,
        evidence: ExecutorTerminalEvidenceV03,
    ) -> None:
        self.verify_dispatch(command, review, dispatch)
        now = self._now()
        if (
            type(evidence) is not ExecutorTerminalEvidenceV03
            or evidence.command_commitment != command.commitment
            or evidence.review_commitment != review.commitment
            or evidence.dispatch_commitment != dispatch.commitment
            or evidence.effect_id != command.effect_id
            or evidence.capability_id != command.capability_id
            or evidence.runtime_measurement_sha256 != command.runtime_measurement_sha256
            or evidence.request_nonce != command.request_nonce
            or evidence.authority_id != self._executor.authority_id
            or evidence.key_id != self._executor.key_id
            or evidence.terminal_at_ms < dispatch.claimed_at_ms
            or evidence.terminal_at_ms >= dispatch.claim_expires_at_ms
            or evidence.terminal_at_ms >= review.expires_at_ms
            or evidence.terminal_at_ms >= command.expires_at_ms
            or evidence.terminal_at_ms > now + self._max_clock_skew_ms
        ):
            raise ProductionReleaseBrokerError("executor_evidence_join_or_time_invalid")
        if not verify_ed25519(
            self._executor.public_key_hex,
            evidence.unsigned_dict(),
            evidence.signature_hex,
            domain=EXECUTOR_SIGNATURE_DOMAIN,
        ):
            raise ProductionReleaseBrokerError("executor_signature_invalid")

    def verify_dispatch_current(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        dispatch: DispatchClaimV03,
    ) -> None:
        """Require an exact durable dispatch lease immediately before transport."""

        self.verify_dispatch(command, review, dispatch, require_current=True)

    def verify_terminal(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        dispatch: DispatchClaimV03,
        receipt: TerminalReceiptV03,
        evidence: ExecutorTerminalEvidenceV03,
    ) -> None:
        self.verify_terminal_receipt_signature(command, review, receipt)
        if type(evidence) is not ExecutorTerminalEvidenceV03:
            raise ProductionReleaseBrokerError("terminal_executor_evidence_required")
        self.verify_executor_evidence(command, review, dispatch, evidence)
        if receipt.executor_evidence_commitment != evidence.commitment:
            raise ProductionReleaseBrokerError("terminal_executor_evidence_join_invalid")
        if (
            receipt.terminal_at_ms < evidence.terminal_at_ms
            or receipt.terminal_at_ms
            > command.expires_at_ms + self._max_clock_skew_ms
        ):
            raise ProductionReleaseBrokerError("terminal_receipt_time_join_invalid")
        if (
            receipt.receipt_id != terminal_receipt_id_v03(evidence.commitment)
            or receipt.reason_code != evidence.reason_code
            or receipt.terminal_at_ms != evidence.terminal_at_ms
        ):
            raise ProductionReleaseBrokerError("terminal_receipt_canonical_join_invalid")
        if (receipt.disposition is ReceiptDisposition.RELEASED) != (
            evidence.outcome is ExecutorOutcome.CONSUMED
        ):
            raise ProductionReleaseBrokerError("terminal_outcome_join_invalid")

    def verify_terminal_receipt_signature(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        receipt: TerminalReceiptV03,
    ) -> None:
        """Authenticate durable replay without re-executing an effect."""

        # Terminal evidence is a durable historical fact.  The review must
        # have been valid inside the command window, while an authentic
        # executor-backed terminal chain remains verifiable after that window.
        self.verify_review(command, review, require_current=False)
        now = self._now()
        if type(receipt) not in {ReleaseReceiptV03, DeniedReceiptV03}:
            raise ProductionReleaseBrokerError("terminal_receipt_type_invalid")
        if (
            receipt.command_commitment != command.commitment
            or receipt.review_commitment != review.commitment
            or receipt.effect_id != command.effect_id
            or receipt.request_nonce != command.request_nonce
            or receipt.authority_id != self._receipt.authority_id
            or receipt.key_id != self._receipt.key_id
            or receipt.terminal_at_ms < review.issued_at_ms
            or receipt.terminal_at_ms > now + self._max_clock_skew_ms
        ):
            raise ProductionReleaseBrokerError("terminal_receipt_join_invalid")
        if not verify_ed25519(
            self._receipt.public_key_hex,
            receipt.unsigned_dict(),
            receipt.signature_hex,
            domain=RECEIPT_SIGNATURE_DOMAIN,
        ):
            raise ProductionReleaseBrokerError("terminal_signature_invalid")


def sign_review_authorization_v03(
    private_key: Ed25519PrivateKey,
    **values: Any,
) -> ReviewAuthorizationV03:
    """Test/integration builder; production review keys remain remote."""

    unsigned = dict(values)
    unsigned.setdefault("schema", REVIEW_SCHEMA)
    signature = sign_ed25519(private_key, unsigned, domain=REVIEW_SIGNATURE_DOMAIN)
    return ReviewAuthorizationV03(**unsigned, signature_hex=signature)


def sign_dispatch_claim_v03(
    private_key: Ed25519PrivateKey,
    **values: Any,
) -> DispatchClaimV03:
    """Test/integration builder; production dispatch keys remain remote."""

    unsigned = dict(values)
    unsigned.setdefault("schema", DISPATCH_SCHEMA)
    signature = sign_ed25519(private_key, unsigned, domain=DISPATCH_SIGNATURE_DOMAIN)
    return DispatchClaimV03(**unsigned, signature_hex=signature)


def sign_executor_evidence_v03(
    private_key: Ed25519PrivateKey,
    **values: Any,
) -> ExecutorTerminalEvidenceV03:
    """Test/integration builder; production executor keys remain remote."""

    unsigned = dict(values)
    unsigned.setdefault("schema", EXECUTOR_EVIDENCE_SCHEMA)
    outcome = unsigned.get("outcome")
    if isinstance(outcome, str):
        unsigned["outcome"] = ExecutorOutcome(outcome)
    signable = {
        **unsigned,
        "outcome": (
            unsigned["outcome"].value
            if isinstance(unsigned.get("outcome"), ExecutorOutcome)
            else unsigned.get("outcome")
        ),
    }
    signature = sign_ed25519(private_key, signable, domain=EXECUTOR_SIGNATURE_DOMAIN)
    return ExecutorTerminalEvidenceV03(**unsigned, signature_hex=signature)


def sign_terminal_receipt_v03(
    private_key: Ed25519PrivateKey,
    *,
    denied: bool,
    **values: Any,
) -> TerminalReceiptV03:
    """Test/integration builder; production receipt keys remain remote."""

    unsigned = dict(values)
    unsigned.setdefault("schema", DENIED_RECEIPT_SCHEMA if denied else RELEASE_RECEIPT_SCHEMA)
    unsigned.setdefault("effect_retry_authorized", False)
    unsigned.setdefault("production_ready", False)
    disposition = unsigned.get("disposition")
    if isinstance(disposition, str):
        unsigned["disposition"] = ReceiptDisposition(disposition)
    signable = {
        **unsigned,
        "disposition": (
            unsigned["disposition"].value
            if isinstance(unsigned.get("disposition"), ReceiptDisposition)
            else unsigned.get("disposition")
        ),
    }
    signature = sign_ed25519(private_key, signable, domain=RECEIPT_SIGNATURE_DOMAIN)
    cls = DeniedReceiptV03 if denied else ReleaseReceiptV03
    return cls(**unsigned, signature_hex=signature)


class LedgerClaimDisposition(StrEnum):
    CLAIMED = "CLAIMED"
    IN_FLIGHT = "IN_FLIGHT"
    STALE_UNCERTAIN = "STALE_UNCERTAIN"
    EVIDENCE_READY = "EVIDENCE_READY"
    TERMINAL_REPLAY = "TERMINAL_REPLAY"


@dataclass(frozen=True, slots=True)
class LedgerClaimV03:
    disposition: LedgerClaimDisposition
    command_commitment: str
    effect_id: str
    request_nonce: str
    dispatch: Mapping[str, Any]
    receipt: Mapping[str, Any] | None = None
    executor_evidence: Mapping[str, Any] | None = None

    def public_dict(self) -> dict[str, Any]:
        result = {
            "schema": LEDGER_SCHEMA,
            "disposition": self.disposition.value,
            "command_commitment": self.command_commitment,
            "effect_id": self.effect_id,
            "request_nonce": self.request_nonce,
            "dispatch": dict(self.dispatch),
            "receipt": None if self.receipt is None else dict(self.receipt),
            "executor_evidence": (
                None if self.executor_evidence is None else dict(self.executor_evidence)
            ),
            "effect_retry_authorized": False,
            "production_ready": False,
        }
        assert_public_summary_safe(result)
        return result


@runtime_checkable
class DurableTerminalLedgerV03(Protocol):
    """Durable ledger boundary supported by the non-production coordinator."""

    production_ready: bool

    def inspect(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> LedgerClaimV03 | None: ...

    def claim(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        verifier: ProductionReleaseVerifierV03,
        claim_timeout_ms: int = 60_000,
    ) -> LedgerClaimV03: ...

    def record_terminal(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        receipt: TerminalReceiptV03,
        evidence: ExecutorTerminalEvidenceV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> dict[str, Any]: ...

    def record_executor_evidence(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        evidence: ExecutorTerminalEvidenceV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> dict[str, Any]: ...


_LEDGER_TABLE_SQL: Final = """
CREATE TABLE release_terminal_v03 (
    command_commitment TEXT PRIMARY KEY,
    effect_id TEXT NOT NULL,
    request_nonce TEXT NOT NULL,
    dispatch_nonce TEXT NOT NULL,
    command_json BLOB NOT NULL,
    review_json BLOB NOT NULL,
    dispatch_unsigned_json BLOB NOT NULL,
    dispatch_json BLOB,
    state TEXT NOT NULL CHECK(state IN ('PENDING_DISPATCH','CLAIMED','EVIDENCED','TERMINAL')),
    claimed_at_ms INTEGER NOT NULL,
    claim_expires_at_ms INTEGER NOT NULL,
    receipt_json BLOB,
    receipt_commitment TEXT,
    executor_evidence_json BLOB,
    executor_evidence_commitment TEXT
) STRICT
""".strip()
_LEDGER_EFFECT_INDEX_SQL: Final = (
    "CREATE UNIQUE INDEX release_terminal_v03_effect_id_uq "
    "ON release_terminal_v03(effect_id)"
)
_LEDGER_NONCE_INDEX_SQL: Final = (
    "CREATE UNIQUE INDEX release_terminal_v03_request_nonce_uq "
    "ON release_terminal_v03(request_nonce)"
)
_LEDGER_DISPATCH_INDEX_SQL: Final = (
    "CREATE UNIQUE INDEX release_terminal_v03_dispatch_nonce_uq "
    "ON release_terminal_v03(dispatch_nonce)"
)


def _normalized_sql(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip()).casefold()


class SQLiteTerminalLedgerV03:
    """Durable local reference ledger with atomic one-use effect claims."""

    production_ready = False

    def __init__(
        self,
        path: Path,
        *,
        dispatch_signer: DispatchClaimSignerV03,
        trusted_now_ms: Callable[[], int] = _system_now_ms,
    ) -> None:
        if not isinstance(path, Path) or not path.is_absolute() or str(path) == ":memory:":
            raise ProductionReleaseBrokerError("durable_sqlite_path_required")
        resolved = path.resolve()
        if not resolved.parent.exists() or not resolved.parent.is_dir():
            raise ProductionReleaseBrokerError("durable_sqlite_parent_required")
        if not callable(trusted_now_ms):
            raise ProductionReleaseBrokerError("trusted_clock_invalid")
        if not isinstance(dispatch_signer, DispatchClaimSignerV03):
            raise ProductionReleaseBrokerError("dispatch_claim_signer_required")
        _identifier(dispatch_signer.signer_id, code="dispatch_signer_id_invalid")
        _identifier(dispatch_signer.key_id, code="dispatch_signer_key_id_invalid")
        self._path = resolved
        self._trusted_now_ms = trusted_now_ms
        self._dispatch_signer = dispatch_signer
        self._initialize()

    def _connect(self, *, validate_schema: bool = True) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._path), timeout=30.0, isolation_level=None)
        try:
            journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            synchronous = connection.execute("PRAGMA synchronous").fetchone()
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()
            if (
                journal_mode is None
                or str(journal_mode[0]).casefold() != "wal"
                or synchronous != (2,)
                or foreign_keys != (1,)
                or busy_timeout != (30_000,)
            ):
                raise ProductionReleaseBrokerError("terminal_ledger_durability_pragmas_invalid")
            if validate_schema:
                self._validate_schema(connection)
            return connection
        except BaseException:
            connection.close()
            raise

    def _initialize(self) -> None:
        connection = self._connect(validate_schema=False)
        try:
            connection.execute(_LEDGER_TABLE_SQL.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1))
            table_row = connection.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='release_terminal_v03'"
            ).fetchone()
            if (
                table_row is None
                or _normalized_sql(table_row[0]) != _normalized_sql(_LEDGER_TABLE_SQL)
            ):
                raise ProductionReleaseBrokerError("terminal_ledger_schema_invalid")
            connection.execute(
                _LEDGER_EFFECT_INDEX_SQL.replace(
                    "CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", 1
                )
            )
            connection.execute(
                _LEDGER_NONCE_INDEX_SQL.replace(
                    "CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", 1
                )
            )
            connection.execute(
                _LEDGER_DISPATCH_INDEX_SQL.replace(
                    "CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", 1
                )
            )
            self._validate_schema(connection)
        finally:
            connection.close()

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        table_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='release_terminal_v03'"
        ).fetchone()
        expected_indexes = {
            "release_terminal_v03_effect_id_uq": _normalized_sql(_LEDGER_EFFECT_INDEX_SQL),
            "release_terminal_v03_request_nonce_uq": _normalized_sql(_LEDGER_NONCE_INDEX_SQL),
            "release_terminal_v03_dispatch_nonce_uq": _normalized_sql(
                _LEDGER_DISPATCH_INDEX_SQL
            ),
        }
        actual_indexes = {
            str(name): _normalized_sql(sql)
            for name, sql in connection.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='index' AND tbl_name='release_terminal_v03' AND sql IS NOT NULL"
            ).fetchall()
        }
        triggers = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='trigger' AND tbl_name='release_terminal_v03'"
        ).fetchall()
        quick_check = connection.execute("PRAGMA quick_check").fetchone()
        if (
            table_row is None
            or _normalized_sql(table_row[0]) != _normalized_sql(_LEDGER_TABLE_SQL)
            or actual_indexes != expected_indexes
            or triggers
            or quick_check != ("ok",)
        ):
            raise ProductionReleaseBrokerError("terminal_ledger_schema_invalid")

    def _now(self) -> int:
        return _uint(self._trusted_now_ms(), code="trusted_time_invalid")

    @staticmethod
    def _command_bytes(command: ReleaseCommandV03) -> bytes:
        if type(command) is not ReleaseCommandV03:
            raise ProductionReleaseBrokerError("release_command_type_invalid")
        return canonical_json_bytes(command.wire_dict())

    @staticmethod
    def _review_bytes(review: ReviewAuthorizationV03) -> bytes:
        if type(review) is not ReviewAuthorizationV03:
            raise ProductionReleaseBrokerError("review_authorization_type_invalid")
        return canonical_json_bytes(review.wire_dict())

    @staticmethod
    def _stored_mapping(value: object, *, code: str) -> dict[str, Any]:
        return _decode_wire_mapping(
            SQLiteTerminalLedgerV03._blob_bytes(value, code=code),
            code=code,
        )

    @staticmethod
    def _blob_bytes(value: object, *, code: str) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray | memoryview):
            return bytes(value)
        raise ProductionReleaseBrokerError(code)

    @classmethod
    def _unsigned_dispatch_from_blob(cls, value: object) -> dict[str, Any]:
        payload = _exact_mapping(
            _decode_wire_mapping(
                cls._blob_bytes(value, code="stored_unsigned_dispatch_invalid"),
                code="stored_unsigned_dispatch_invalid",
            ),
            {
                "schema", "command_commitment", "review_commitment", "effect_id",
                "request_nonce", "dispatch_nonce", "claimed_at_ms",
                "claim_expires_at_ms", "authority_id", "key_id",
            },
            code="stored_unsigned_dispatch_invalid",
        )
        return payload

    def _claim_from_row(
        self,
        row: tuple[Any, ...],
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        verifier: ProductionReleaseVerifierV03,
        now: int,
    ) -> LedgerClaimV03:
        (
            effect_id,
            nonce,
            stored_dispatch_nonce,
            stored_command,
            stored_review,
            state,
            stored_claimed_at,
            stored_expiry,
            dispatch_json,
            receipt_json,
            evidence_json,
            stored_receipt_commitment,
            stored_evidence_commitment,
            unsigned_dispatch_json,
        ) = row
        if (
            effect_id != command.effect_id
            or nonce != command.request_nonce
            or self._blob_bytes(stored_command, code="stored_command_invalid")
            != self._command_bytes(command)
            or self._blob_bytes(stored_review, code="stored_review_invalid")
            != self._review_bytes(review)
        ):
            raise ProductionReleaseBrokerError("stored_command_or_review_join_mismatch")
        dispatch = decode_dispatch_claim_v03(
            self._blob_bytes(dispatch_json, code="stored_dispatch_invalid")
        )
        if (
            dispatch.command_commitment != command.commitment
            or dispatch.review_commitment != review.commitment
            or dispatch.effect_id != command.effect_id
            or dispatch.request_nonce != command.request_nonce
            or stored_dispatch_nonce != dispatch.dispatch_nonce
            or _uint(stored_claimed_at, code="stored_claimed_at_invalid")
            != dispatch.claimed_at_ms
            or _uint(stored_expiry, code="stored_claim_expiry_invalid")
            != dispatch.claim_expires_at_ms
        ):
            raise ProductionReleaseBrokerError("stored_dispatch_join_mismatch")
        verifier.verify_dispatch(command, review, dispatch)
        if self._unsigned_dispatch_from_blob(unsigned_dispatch_json) != dispatch.unsigned_dict():
            raise ProductionReleaseBrokerError("stored_unsigned_dispatch_join_invalid")
        receipt_mapping: Mapping[str, Any] | None = None
        evidence_mapping: Mapping[str, Any] | None = None
        if state == "TERMINAL":
            receipt_mapping = self._stored_mapping(
                receipt_json, code="stored_receipt_invalid"
            )
            evidence_mapping = self._stored_mapping(
                evidence_json, code="stored_executor_evidence_invalid"
            )
            receipt = decode_terminal_receipt_v03(
                canonical_json_bytes(receipt_mapping)
            )
            evidence = decode_executor_evidence_v03(
                canonical_json_bytes(evidence_mapping)
            )
            if (
                stored_receipt_commitment != receipt.commitment
                or stored_evidence_commitment != evidence.commitment
            ):
                raise ProductionReleaseBrokerError("stored_terminal_commitment_mismatch")
            verifier.verify_terminal(command, review, dispatch, receipt, evidence)
            disposition = LedgerClaimDisposition.TERMINAL_REPLAY
        elif state == "EVIDENCED":
            if receipt_json is not None:
                raise ProductionReleaseBrokerError("stored_evidenced_state_invalid")
            evidence_mapping = self._stored_mapping(
                evidence_json, code="stored_executor_evidence_invalid"
            )
            evidence = decode_executor_evidence_v03(
                canonical_json_bytes(evidence_mapping)
            )
            if (
                stored_receipt_commitment is not None
                or stored_evidence_commitment != evidence.commitment
            ):
                raise ProductionReleaseBrokerError("stored_evidence_commitment_mismatch")
            verifier.verify_executor_evidence(command, review, dispatch, evidence)
            disposition = LedgerClaimDisposition.EVIDENCE_READY
        elif state == "CLAIMED" and now >= dispatch.claim_expires_at_ms:
            if (
                receipt_json is not None
                or evidence_json is not None
                or stored_receipt_commitment is not None
                or stored_evidence_commitment is not None
            ):
                raise ProductionReleaseBrokerError("stored_claimed_state_invalid")
            disposition = LedgerClaimDisposition.STALE_UNCERTAIN
        elif state == "CLAIMED":
            if (
                receipt_json is not None
                or evidence_json is not None
                or stored_receipt_commitment is not None
                or stored_evidence_commitment is not None
            ):
                raise ProductionReleaseBrokerError("stored_claimed_state_invalid")
            disposition = LedgerClaimDisposition.IN_FLIGHT
        else:
            raise ProductionReleaseBrokerError("stored_claim_state_invalid")
        return LedgerClaimV03(
            disposition=disposition,
            command_commitment=command.commitment,
            effect_id=command.effect_id,
            request_nonce=command.request_nonce,
            dispatch=dispatch.wire_dict(),
            receipt=receipt_mapping,
            executor_evidence=evidence_mapping,
        )

    def inspect(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> LedgerClaimV03 | None:
        """Return only schema-checked and signature-authenticated state."""

        if type(verifier) is not ProductionReleaseVerifierV03:
            raise ProductionReleaseBrokerError("production_release_verifier_required")
        verifier.verify_review(command, review, require_current=False)
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT effect_id, request_nonce, dispatch_nonce, command_json, "
                "review_json, state, claimed_at_ms, claim_expires_at_ms, "
                "dispatch_json, receipt_json, executor_evidence_json, "
                "receipt_commitment, executor_evidence_commitment, "
                "dispatch_unsigned_json "
                "FROM release_terminal_v03 WHERE command_commitment = ?",
                (command.commitment,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        if row[5] == "PENDING_DISPATCH":
            if any(value is not None for value in row[8:13]):
                raise ProductionReleaseBrokerError("stored_pending_dispatch_state_invalid")
            return None
        return self._claim_from_row(
            row, command, review, verifier=verifier, now=self._now()
        )

    def claim(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        verifier: ProductionReleaseVerifierV03,
        claim_timeout_ms: int = 60_000,
    ) -> LedgerClaimV03:
        if type(verifier) is not ProductionReleaseVerifierV03:
            raise ProductionReleaseBrokerError("production_release_verifier_required")
        timeout = _uint(claim_timeout_ms, code="claim_timeout_invalid")
        if timeout == 0 or timeout > _MAX_COMMAND_LIFETIME_MS:
            raise ProductionReleaseBrokerError("claim_timeout_invalid")
        encoded_command = self._command_bytes(command)
        encoded_review = self._review_bytes(review)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            row = connection.execute(
                "SELECT effect_id, request_nonce, dispatch_nonce, command_json, "
                "review_json, state, claimed_at_ms, claim_expires_at_ms, "
                "dispatch_json, receipt_json, executor_evidence_json, "
                "receipt_commitment, executor_evidence_commitment, "
                "dispatch_unsigned_json "
                "FROM release_terminal_v03 WHERE command_commitment = ?",
                (command.commitment,),
            ).fetchone()
            if row is None:
                # Both clocks and the signed review are rechecked only after
                # the write lock is held, closing the lock-wait expiry race.
                verifier.verify_review(command, review)
                now = self._now()
                if (
                    now < max(command.issued_at_ms, review.issued_at_ms) - _MAX_CLOCK_SKEW_MS
                    or now >= command.expires_at_ms
                    or now >= review.expires_at_ms
                ):
                    raise ProductionReleaseBrokerError("command_or_review_not_current")
                claim_expiry = min(
                    command.expires_at_ms,
                    review.expires_at_ms,
                    now + timeout,
                )
                unsigned_dispatch = {
                    "schema": DISPATCH_SCHEMA,
                    "command_commitment": command.commitment,
                    "review_commitment": review.commitment,
                    "effect_id": command.effect_id,
                    "request_nonce": command.request_nonce,
                    "dispatch_nonce": secrets.token_hex(32),
                    "claimed_at_ms": now,
                    "claim_expires_at_ms": claim_expiry,
                    "authority_id": self._dispatch_signer.signer_id,
                    "key_id": self._dispatch_signer.key_id,
                }
                encoded_unsigned_dispatch = canonical_json_bytes(unsigned_dispatch)
                try:
                    connection.execute(
                        "INSERT INTO release_terminal_v03 ("
                        "command_commitment,effect_id,request_nonce,dispatch_nonce,"
                        "command_json,review_json,dispatch_unsigned_json,dispatch_json,"
                        "state,claimed_at_ms,"
                        "claim_expires_at_ms,receipt_json,receipt_commitment,"
                        "executor_evidence_json,executor_evidence_commitment"
                        ") VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'PENDING_DISPATCH', "
                        "?, ?, NULL, NULL, NULL, NULL)",
                        (
                            command.commitment,
                            command.effect_id,
                            command.request_nonce,
                            unsigned_dispatch["dispatch_nonce"],
                            encoded_command,
                            encoded_review,
                            encoded_unsigned_dispatch,
                            now,
                            claim_expiry,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ProductionReleaseBrokerError(
                        "effect_nonce_or_dispatch_reused"
                    ) from exc
                connection.execute("COMMIT")
            elif row[5] == "PENDING_DISPATCH":
                if (
                    row[0] != command.effect_id
                    or row[1] != command.request_nonce
                    or self._blob_bytes(row[3], code="stored_command_invalid")
                    != encoded_command
                    or self._blob_bytes(row[4], code="stored_review_invalid")
                    != encoded_review
                    or any(value is not None for value in row[8:13])
                ):
                    raise ProductionReleaseBrokerError("stored_pending_dispatch_state_invalid")
                verifier.verify_review(command, review)
                now = self._now()
                unsigned_dispatch = self._unsigned_dispatch_from_blob(row[13])
                if (
                    row[2] != unsigned_dispatch["dispatch_nonce"]
                    or _uint(row[6], code="stored_claimed_at_invalid")
                    != unsigned_dispatch["claimed_at_ms"]
                    or _uint(row[7], code="stored_claim_expiry_invalid")
                    != unsigned_dispatch["claim_expires_at_ms"]
                    or unsigned_dispatch["command_commitment"] != command.commitment
                    or unsigned_dispatch["review_commitment"] != review.commitment
                    or unsigned_dispatch["effect_id"] != command.effect_id
                    or unsigned_dispatch["request_nonce"] != command.request_nonce
                ):
                    raise ProductionReleaseBrokerError("stored_unsigned_dispatch_join_invalid")
                if now >= unsigned_dispatch["claim_expires_at_ms"]:
                    # A PENDING reservation has never produced a signed dispatch,
                    # so executor transport was impossible. Renew it atomically
                    # with a new nonce. A late signer response for the old bytes is
                    # fenced by the exact dispatch_unsigned_json comparison used
                    # during finalization.
                    claim_expiry = min(
                        command.expires_at_ms,
                        review.expires_at_ms,
                        now + timeout,
                    )
                    unsigned_dispatch = {
                        "schema": DISPATCH_SCHEMA,
                        "command_commitment": command.commitment,
                        "review_commitment": review.commitment,
                        "effect_id": command.effect_id,
                        "request_nonce": command.request_nonce,
                        "dispatch_nonce": secrets.token_hex(32),
                        "claimed_at_ms": now,
                        "claim_expires_at_ms": claim_expiry,
                        "authority_id": self._dispatch_signer.signer_id,
                        "key_id": self._dispatch_signer.key_id,
                    }
                    encoded_unsigned_dispatch = canonical_json_bytes(unsigned_dispatch)
                    updated = connection.execute(
                        "UPDATE release_terminal_v03 SET dispatch_nonce=?, "
                        "dispatch_unsigned_json=?, claimed_at_ms=?, claim_expires_at_ms=? "
                        "WHERE command_commitment=? AND state='PENDING_DISPATCH' "
                        "AND dispatch_unsigned_json=?",
                        (
                            unsigned_dispatch["dispatch_nonce"],
                            encoded_unsigned_dispatch,
                            now,
                            claim_expiry,
                            command.commitment,
                            self._blob_bytes(
                                row[13], code="stored_unsigned_dispatch_invalid"
                            ),
                        ),
                    )
                    if updated.rowcount != 1:
                        raise ProductionReleaseBrokerError(
                            "pending_dispatch_renewal_race"
                        )
                else:
                    encoded_unsigned_dispatch = canonical_json_bytes(unsigned_dispatch)
                connection.execute("COMMIT")
            else:
                verifier.verify_review(command, review, require_current=False)
                claim = self._claim_from_row(
                    row, command, review, verifier=verifier, now=now
                )
                connection.execute("COMMIT")
                return claim
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

        # The potentially remote signer is called only after the SQLite write
        # transaction is closed.  The PENDING_DISPATCH reservation is durable
        # and retryable without ever authorizing executor dispatch.
        try:
            signed_dispatch_wire = self._dispatch_signer.sign_dispatch(
                encoded_unsigned_dispatch,
                deadline_at_ms=_uint(
                    unsigned_dispatch["claim_expires_at_ms"],
                    code="dispatch_signer_deadline_invalid",
                ),
            )
            if type(signed_dispatch_wire) is not bytes:
                raise ProductionReleaseBrokerError("dispatch_signer_wire_type_invalid")
            dispatch = decode_dispatch_claim_v03(signed_dispatch_wire)
        except BaseException:
            raise ProductionReleaseBrokerError(
                "dispatch_signer_unavailable_claim_reserved"
            ) from None
        if dispatch.unsigned_dict() != unsigned_dispatch:
            raise ProductionReleaseBrokerError("dispatch_signer_join_invalid")
        verifier.verify_dispatch_current(command, review, dispatch)
        encoded_dispatch = canonical_json_bytes(dispatch.wire_dict())

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state, dispatch_unsigned_json, dispatch_json FROM "
                "release_terminal_v03 WHERE command_commitment=?",
                (command.commitment,),
            ).fetchone()
            if row is None or self._blob_bytes(
                row[1], code="stored_unsigned_dispatch_invalid"
            ) != encoded_unsigned_dispatch:
                raise ProductionReleaseBrokerError("dispatch_reservation_missing")
            if row[0] == "PENDING_DISPATCH":
                updated = connection.execute(
                    "UPDATE release_terminal_v03 SET state='CLAIMED', dispatch_json=? "
                    "WHERE command_commitment=? AND state='PENDING_DISPATCH'",
                    (encoded_dispatch, command.commitment),
                )
                if updated.rowcount != 1:
                    raise ProductionReleaseBrokerError("dispatch_finalize_race")
                connection.execute("COMMIT")
                return LedgerClaimV03(
                    disposition=LedgerClaimDisposition.CLAIMED,
                    command_commitment=command.commitment,
                    effect_id=command.effect_id,
                    request_nonce=command.request_nonce,
                    dispatch=dispatch.wire_dict(),
                )
            if self._blob_bytes(
                row[2], code="stored_dispatch_invalid"
            ) != encoded_dispatch:
                raise ProductionReleaseBrokerError("dispatch_finalize_conflict")
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        existing = self.inspect(command, review, verifier=verifier)
        if existing is None:
            raise ProductionReleaseBrokerError("dispatch_finalize_state_invalid")
        return existing

    def record_executor_evidence(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        evidence: ExecutorTerminalEvidenceV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> dict[str, Any]:
        """Persist authentic executor evidence before any receipt-signing call."""

        if type(verifier) is not ProductionReleaseVerifierV03:
            raise ProductionReleaseBrokerError("production_release_verifier_required")
        if type(evidence) is not ExecutorTerminalEvidenceV03:
            raise ProductionReleaseBrokerError("exact_executor_evidence_required")
        evidence_bytes = canonical_json_bytes(evidence.wire_dict())
        command_bytes = self._command_bytes(command)
        review_bytes = self._review_bytes(review)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT command_json, review_json, dispatch_json, state, "
                "executor_evidence_json, executor_evidence_commitment "
                "FROM release_terminal_v03 WHERE command_commitment = ?",
                (command.commitment,),
            ).fetchone()
            if (
                row is None
                or self._blob_bytes(row[0], code="stored_command_invalid")
                != command_bytes
                or self._blob_bytes(row[1], code="stored_review_invalid")
                != review_bytes
            ):
                raise ProductionReleaseBrokerError("release_claim_required")
            dispatch = decode_dispatch_claim_v03(
                self._blob_bytes(row[2], code="stored_dispatch_invalid")
            )
            verifier.verify_executor_evidence(command, review, dispatch, evidence)
            if row[3] in {"EVIDENCED", "TERMINAL"}:
                if (
                    self._blob_bytes(
                        row[4], code="stored_executor_evidence_invalid"
                    )
                    != evidence_bytes
                    or row[5] != evidence.commitment
                ):
                    raise ProductionReleaseBrokerError("executor_evidence_conflict")
                connection.execute("COMMIT")
                return evidence.wire_dict()
            if row[3] != "CLAIMED":
                raise ProductionReleaseBrokerError("release_claim_state_invalid")
            updated = connection.execute(
                "UPDATE release_terminal_v03 SET state='EVIDENCED', "
                "executor_evidence_json=?, executor_evidence_commitment=? "
                "WHERE command_commitment=? AND state='CLAIMED'",
                (evidence_bytes, evidence.commitment, command.commitment),
            )
            if updated.rowcount != 1:
                raise ProductionReleaseBrokerError("executor_evidence_record_race")
            connection.execute("COMMIT")
            return evidence.wire_dict()
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def record_terminal(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        receipt: TerminalReceiptV03,
        evidence: ExecutorTerminalEvidenceV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> dict[str, Any]:
        if type(verifier) is not ProductionReleaseVerifierV03:
            raise ProductionReleaseBrokerError("production_release_verifier_required")
        if (
            type(receipt) not in {ReleaseReceiptV03, DeniedReceiptV03}
            or type(evidence) is not ExecutorTerminalEvidenceV03
        ):
            raise ProductionReleaseBrokerError("exact_terminal_chain_required")
        receipt_bytes = canonical_json_bytes(receipt.wire_dict())
        evidence_bytes = canonical_json_bytes(evidence.wire_dict())
        command_bytes = self._command_bytes(command)
        review_bytes = self._review_bytes(review)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT command_json, review_json, dispatch_json, state, receipt_json, "
                "receipt_commitment, executor_evidence_json, executor_evidence_commitment "
                "FROM release_terminal_v03 WHERE command_commitment = ?",
                (command.commitment,),
            ).fetchone()
            if (
                row is None
                or self._blob_bytes(row[0], code="stored_command_invalid")
                != command_bytes
                or self._blob_bytes(row[1], code="stored_review_invalid")
                != review_bytes
            ):
                raise ProductionReleaseBrokerError("release_claim_required")
            dispatch = decode_dispatch_claim_v03(
                self._blob_bytes(row[2], code="stored_dispatch_invalid")
            )
            verifier.verify_terminal(command, review, dispatch, receipt, evidence)
            if row[3] == "TERMINAL":
                if (
                    self._blob_bytes(row[4], code="stored_receipt_invalid")
                    != receipt_bytes
                    or row[5] != receipt.commitment
                    or self._blob_bytes(
                        row[6], code="stored_executor_evidence_invalid"
                    )
                    != evidence_bytes
                    or row[7] != evidence.commitment
                ):
                    raise ProductionReleaseBrokerError("terminal_receipt_conflict")
                connection.execute("COMMIT")
                return receipt.wire_dict()
            if (
                row[3] != "EVIDENCED"
                or self._blob_bytes(
                    row[6], code="stored_executor_evidence_invalid"
                )
                != evidence_bytes
                or row[7] != evidence.commitment
            ):
                raise ProductionReleaseBrokerError("recorded_executor_evidence_required")
            updated = connection.execute(
                "UPDATE release_terminal_v03 SET state='TERMINAL', receipt_json=?, "
                "receipt_commitment=? "
                "WHERE command_commitment=? AND state='EVIDENCED'",
                (
                    receipt_bytes,
                    receipt.commitment,
                    command.commitment,
                ),
            )
            if updated.rowcount != 1:
                raise ProductionReleaseBrokerError("terminal_receipt_record_race")
            connection.execute("COMMIT")
            return receipt.wire_dict()
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def read_terminal(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
        *,
        verifier: ProductionReleaseVerifierV03,
    ) -> dict[str, Any] | None:
        claim = self.inspect(command, review, verifier=verifier)
        if claim is None or claim.disposition is not LedgerClaimDisposition.TERMINAL_REPLAY:
            return None
        if claim.receipt is None or claim.executor_evidence is None:
            raise ProductionReleaseBrokerError("stored_terminal_chain_invalid")
        decoded = dict(claim.receipt)
        assert_public_summary_safe(decoded)
        return decoded


class ProductionReleaseBrokerV03:
    """Reference coordinator for signed out-of-process execution.

    The coordinator exchanges only bounded canonical metadata bytes with its
    executor and receipt-signer adapters.  A real deployment must prove those
    adapters are remote and independently administered; this Python contract
    cannot establish that property by structural typing alone.
    The checked-in coordinator and SQLite ledger therefore remain explicitly
    non-production until that live composition is attested.
    """

    production_ready = False

    def __init__(
        self,
        *,
        verifier: ProductionReleaseVerifierV03,
        ledger: DurableTerminalLedgerV03,
        executor: OutOfProcessReleaseExecutorV03,
        receipt_signer: TerminalReceiptSignerV03,
        claim_timeout_ms: int = 60_000,
    ) -> None:
        if type(verifier) is not ProductionReleaseVerifierV03:
            raise ProductionReleaseBrokerError("production_release_verifier_required")
        if not isinstance(ledger, DurableTerminalLedgerV03):
            raise ProductionReleaseBrokerError("durable_terminal_ledger_required")
        if not isinstance(executor, OutOfProcessReleaseExecutorV03):
            raise ProductionReleaseBrokerError("out_of_process_executor_required")
        if not isinstance(receipt_signer, TerminalReceiptSignerV03):
            raise ProductionReleaseBrokerError("terminal_receipt_signer_required")
        identities = verifier.authority_ids
        if (
            executor.executor_id != identities["executor"]
            or receipt_signer.signer_id != identities["receipt"]
            or cast(object, executor) is cast(object, receipt_signer)
        ):
            raise ProductionReleaseBrokerError("broker_adapter_authority_join_invalid")
        timeout = _uint(claim_timeout_ms, code="claim_timeout_invalid")
        if timeout == 0 or timeout > _MAX_COMMAND_LIFETIME_MS:
            raise ProductionReleaseBrokerError("claim_timeout_invalid")
        self._verifier = verifier
        self._ledger = ledger
        self._executor = executor
        self._receipt_signer = receipt_signer
        self._claim_timeout_ms = timeout

    def execute_release(
        self,
        command: ReleaseCommandV03,
        review: ReviewAuthorizationV03,
    ) -> dict[str, Any]:
        """Execute or recover exactly one metadata-bound effect claim."""

        if type(command) is not ReleaseCommandV03 or type(review) is not ReviewAuthorizationV03:
            raise ProductionReleaseBrokerError("exact_release_command_and_review_required")
        existing = self._ledger.inspect(
            command,
            review,
            verifier=self._verifier,
        )
        if existing is None:
            # Authorization is validated before the first durable claim so an
            # unauthenticated caller cannot burn an effect id or nonce.
            self._verifier.verify_review(command, review)
            claim = self._ledger.claim(
                command,
                review,
                verifier=self._verifier,
                claim_timeout_ms=self._claim_timeout_ms,
            )
        else:
            claim = existing
        if type(claim) is not LedgerClaimV03:
            raise ProductionReleaseBrokerError("exact_ledger_claim_required")
        if claim.disposition is LedgerClaimDisposition.TERMINAL_REPLAY:
            if claim.receipt is None or claim.executor_evidence is None:
                raise ProductionReleaseBrokerError("stored_terminal_chain_invalid")
            result = dict(claim.receipt)
            receipt = decode_terminal_receipt_v03(canonical_json_bytes(result))
            evidence = decode_executor_evidence_v03(
                canonical_json_bytes(claim.executor_evidence)
            )
            dispatch = DispatchClaimV03.from_wire(claim.dispatch)
            self._verifier.verify_terminal(
                command, review, dispatch, receipt, evidence
            )
            assert_public_summary_safe(result)
            return result
        if claim.disposition is LedgerClaimDisposition.IN_FLIGHT:
            raise ProductionReleaseBrokerError("release_claim_in_flight")
        if claim.disposition is LedgerClaimDisposition.STALE_UNCERTAIN:
            self._verifier.verify_review(command, review, require_current=False)
            # An expired lease is not proof that the remote effect failed.  It
            # remains durably unresolved and can never authorize a retry or a
            # fabricated terminal denial.
            raise ProductionReleaseBrokerError(
                "release_claim_stale_uncertain_reconciliation_required"
            )

        dispatch = DispatchClaimV03.from_wire(claim.dispatch)
        command_wire = canonical_json_bytes(command.wire_dict())
        review_wire = canonical_json_bytes(review.wire_dict())
        if claim.disposition is LedgerClaimDisposition.EVIDENCE_READY:
            if claim.executor_evidence is None:
                raise ProductionReleaseBrokerError("stored_executor_evidence_invalid")
            evidence = decode_executor_evidence_v03(
                canonical_json_bytes(claim.executor_evidence)
            )
            self._verifier.verify_executor_evidence(
                command, review, dispatch, evidence
            )
        elif claim.disposition is LedgerClaimDisposition.CLAIMED:
            # Recheck authorization immediately before crossing the transport.
            self._verifier.verify_dispatch_current(command, review, dispatch)
            dispatch_wire = canonical_json_bytes(dispatch.wire_dict())
            try:
                evidence_wire = self._executor.execute(
                    command_wire,
                    review_wire,
                    dispatch_wire,
                )
                if type(evidence_wire) is not bytes:
                    raise ProductionReleaseBrokerError("executor_wire_type_invalid")
                evidence = decode_executor_evidence_v03(evidence_wire)
            except BaseException:
                # The durable CLAIMED row is intentionally retained.  Retrying an
                # effect after an uncertain remote failure is forbidden.
                raise ProductionReleaseBrokerError(
                    "executor_unavailable_or_uncertain_claim_retained"
                ) from None
            self._verifier.verify_executor_evidence(
                command, review, dispatch, evidence
            )
            self._ledger.record_executor_evidence(
                command,
                review,
                evidence,
                verifier=self._verifier,
            )
        else:
            raise ProductionReleaseBrokerError("release_claim_state_invalid")
        signed_receipt_wire: bytes | None = None
        try:
            candidate = self._receipt_signer.sign_terminal(
                command_wire,
                review_wire,
                canonical_json_bytes(evidence.wire_dict()),
                idempotency_key=evidence.commitment,
            )
            if type(candidate) is not bytes:
                raise ProductionReleaseBrokerError("terminal_receipt_wire_type_invalid")
            signed_receipt_wire = candidate
        except BaseException:
            # The signing service may have committed before its response was
            # lost. The mandatory idempotent readback below is authoritative.
            signed_receipt_wire = None
        try:
            receipt_wire = self._receipt_signer.read_terminal(
                idempotency_key=evidence.commitment
            )
            if type(receipt_wire) is not bytes:
                raise ProductionReleaseBrokerError("terminal_receipt_readback_missing")
            if signed_receipt_wire is not None and signed_receipt_wire != receipt_wire:
                raise ProductionReleaseBrokerError("terminal_receipt_readback_mismatch")
            receipt = decode_terminal_receipt_v03(receipt_wire)
        except BaseException:
            raise ProductionReleaseBrokerError(
                "terminal_signer_unavailable_evidence_retained"
            ) from None
        if type(receipt) not in {ReleaseReceiptV03, DeniedReceiptV03}:
            raise ProductionReleaseBrokerError("terminal_receipt_type_invalid")
        self._verifier.verify_terminal(
            command, review, dispatch, receipt, evidence
        )
        return self._ledger.record_terminal(
            command,
            review,
            receipt,
            evidence,
            verifier=self._verifier,
        )


__all__ = [
    "COMMAND_SCHEMA",
    "DENIED_RECEIPT_SCHEMA",
    "DISPATCH_SCHEMA",
    "EXECUTOR_EVIDENCE_SCHEMA",
    "LEDGER_SCHEMA",
    "RELEASE_RECEIPT_SCHEMA",
    "REVIEW_SCHEMA",
    "AuthorityBindingV03",
    "DeniedReceiptV03",
    "DispatchClaimV03",
    "DispatchClaimSignerV03",
    "DurableTerminalLedgerV03",
    "ExecutorOutcome",
    "ExecutorTerminalEvidenceV03",
    "LedgerClaimDisposition",
    "LedgerClaimV03",
    "OutOfProcessReleaseExecutorV03",
    "ProductionReleaseBrokerError",
    "ProductionReleaseBrokerV03",
    "ProductionReleaseVerifierV03",
    "ReceiptDisposition",
    "ReleaseCommandV03",
    "ReleaseReceiptV03",
    "ReviewAuthorizationV03",
    "SQLiteTerminalLedgerV03",
    "TerminalReceiptSignerV03",
    "TerminalReceiptV03",
    "decode_executor_evidence_v03",
    "decode_dispatch_claim_v03",
    "decode_release_command_v03",
    "decode_review_authorization_v03",
    "decode_terminal_receipt_v03",
    "sign_executor_evidence_v03",
    "sign_dispatch_claim_v03",
    "sign_review_authorization_v03",
    "sign_terminal_receipt_v03",
    "terminal_receipt_id_v03",
]
