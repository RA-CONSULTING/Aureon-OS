"""Local-development whole-OS admission and Magic Star hand-off boundary.

This module is an architectural choke point for *untrusted ingress*.  It does
not claim that locally wrapping bytes establishes remote truth, and it is not a
production sandbox, HSM, durable replay ledger, or malware detector.

Every call to :meth:`LocalOSProtectionBoundary.admit_external` that reaches the
bounded-content contract returns exactly one of two typed outcomes:

* :class:`AdmittedHNC` -- the bytes were sealed into a validated HNC packet and
  retained only behind an opaque, one-use handle; or
* :class:`QuarantinedHNC` -- no application payload was retained.  When a valid
  key is available, a separate HNC packet contains commitment-only quarantine
  metadata.  A missing/invalid key still yields a fail-closed metadata record.

The only supported carrier hand-off consumes the opaque handle and calls the
existing local-development Magic Star custody adapter.  No public API returns
the HNC carrier, its key, or the original bytes.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, TypeAlias

from aureon.harmonic.hnc_quantum_packet_crypto import (
    build_hnc_quantum_packet,
    normalize_hnc_key_material,
    validate_hnc_packet_contract,
)

from .audit import assert_public_summary_safe
from .crypto import canonical_json_bytes, decode_canonical_json, domain_hash, sha256_hex
from .packet import HNCPayloadBindingV0, bind_hnc_packet
from .quarantine import QuarantineRecord
from .schema import (
    SchemaError,
    format_timestamp,
    parse_timestamp,
    require_aware_datetime,
    require_nonblank,
    require_sha256,
)
from .star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    ProtectedMagicStarPacketV02,
)

OS_PROTECTION_SCHEMA: Final = "aureon.plumber.os-protection.v0"
OS_INGRESS_AAD_SCHEMA: Final = "aureon.plumber.os-ingress-aad.v0"
OS_QUARANTINE_EVIDENCE_SCHEMA: Final = "aureon.plumber.os-quarantine-evidence.v0"
OS_QUARANTINE_EVIDENCE_PURPOSE: Final = "aureon.plumber.os.quarantine-evidence.v0"
DEFAULT_MAX_INGRESS_BYTES: Final = 16 * 1024 * 1024
MAX_OPERATOR_AAD_BYTES: Final = 64 * 1024
_MAX_BOUNDARY_ID_BYTES: Final = 128
_MAX_SOURCE_ID_BYTES: Final = 512
_MAX_INGRESS_KIND_BYTES: Final = 128
_MAX_PURPOSE_BYTES: Final = 1024
_MAX_OPERATOR_AAD_DEPTH: Final = 16
_MAX_OPERATOR_AAD_NODES: Final = 4096
_MAX_ACTIVE_HANDLES_LIMIT: Final = 4096
_MAX_ACTIVE_INGRESS_BYTES_LIMIT: Final = 256 * 1024 * 1024
_MAX_REPLAY_TOKENS_LIMIT: Final = 1_000_000
_MAX_QUARANTINE_EVIDENCE_LIMIT: Final = 65_536

MasterKeyProvider: TypeAlias = Callable[[], bytes | str | None]
ContentValidator: TypeAlias = Callable[[memoryview], bool]


class OSProtectionError(ValueError):
    """Stable, non-secret local protection boundary error."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


class IngressDisposition(StrEnum):
    ADMITTED_HNC = "ADMITTED_HNC"
    QUARANTINED_HNC = "QUARANTINED_HNC"


def _system_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _bounded_text(value: object, *, field_name: str, maximum_bytes: int) -> str:
    try:
        text = require_nonblank(value, field=field_name, max_length=maximum_bytes)
        encoded = text.encode("utf-8", errors="strict")
    except (SchemaError, UnicodeEncodeError) as exc:
        raise OSProtectionError(f"{field_name}_invalid") from exc
    if len(encoded) > maximum_bytes or "\x00" in text:
        raise OSProtectionError(f"{field_name}_invalid")
    return text


def _purpose_commitment(purpose: str) -> str:
    return domain_hash("aureon.plumber.purpose.v0", purpose)


def _handle_commitment(*, boundary_id: str, handle_id: str, token: str) -> str:
    return domain_hash(
        "aureon.plumber.os-protection-handle.v0",
        {"boundary_id": boundary_id, "handle_id": handle_id, "token": token},
    )


def _snapshot_operator_aad(
    value: Any,
    *,
    depth: int = 0,
    remaining_nodes: list[int] | None = None,
) -> Any:
    """Copy JSON-like AAD under explicit depth, node, and string budgets."""

    budget = remaining_nodes if remaining_nodes is not None else [_MAX_OPERATOR_AAD_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > _MAX_OPERATOR_AAD_DEPTH:
        raise OSProtectionError("operator_aad_invalid")
    if value is None or type(value) in {bool, int}:
        return value
    if isinstance(value, str):
        if len(value.encode("utf-8", errors="strict")) > MAX_OPERATOR_AAD_BYTES:
            raise OSProtectionError("operator_aad_invalid")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or key in result:
                raise OSProtectionError("operator_aad_invalid")
            if len(key.encode("utf-8", errors="strict")) > MAX_OPERATOR_AAD_BYTES:
                raise OSProtectionError("operator_aad_invalid")
            result[key] = _snapshot_operator_aad(
                item,
                depth=depth + 1,
                remaining_nodes=budget,
            )
        return result
    if isinstance(value, Sequence) and not isinstance(
        value,
        (bytes, bytearray, memoryview, str),
    ):
        return [
            _snapshot_operator_aad(
                item,
                depth=depth + 1,
                remaining_nodes=budget,
            )
            for item in value
        ]
    raise OSProtectionError("operator_aad_invalid")


@dataclass(frozen=True, slots=True)
class OpaqueHNCHandle:
    """Unforgeable, one-use reference to an HNC carrier held by the boundary."""

    boundary_id: str
    handle_id: str
    token: str = field(repr=False)
    handle_commitment: str

    def __post_init__(self) -> None:
        _bounded_text(
            self.boundary_id,
            field_name="boundary_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        _bounded_text(
            self.handle_id,
            field_name="handle_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        if not isinstance(self.token, str) or not self.token:
            raise OSProtectionError("opaque_handle_token_invalid")
        require_sha256(self.handle_commitment, field="handle_commitment")
        if self.handle_commitment != _handle_commitment(
            boundary_id=self.boundary_id,
            handle_id=self.handle_id,
            token=self.token,
        ):
            raise OSProtectionError("opaque_handle_commitment_invalid")

    @classmethod
    def issue(cls, *, boundary_id: str, handle_id: str) -> OpaqueHNCHandle:
        token = secrets.token_urlsafe(32)
        return cls(
            boundary_id=boundary_id,
            handle_id=handle_id,
            token=token,
            handle_commitment=_handle_commitment(
                boundary_id=boundary_id,
                handle_id=handle_id,
                token=token,
            ),
        )

    def public_summary(self) -> dict[str, str]:
        return {
            "boundary_id": self.boundary_id,
            "handle_id": self.handle_id,
            "handle_commitment": self.handle_commitment,
        }


def _common_public_values(
    *,
    disposition: IngressDisposition,
    boundary_id: str,
    admission_id: str,
    source_id: str,
    ingress_kind: str,
    content_sha256: str,
    content_size_bytes: int,
    purpose_commitment: str,
    operator_aad_sha256: str,
    replay_token: str,
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "schema": OS_PROTECTION_SCHEMA,
        "disposition": str(disposition),
        "boundary_id": boundary_id,
        "admission_id": admission_id,
        "source_id": source_id,
        "ingress_kind": ingress_kind,
        "content_sha256": content_sha256,
        "content_size_bytes": content_size_bytes,
        "purpose_commitment": purpose_commitment,
        "operator_aad_sha256": operator_aad_sha256,
        "replay_token": replay_token,
        "recorded_at": recorded_at,
        "local_development_only": True,
        "production_ready": False,
    }


@dataclass(frozen=True, slots=True)
class AdmittedHNC:
    """Validated HNC admission.  It intentionally contains no carrier bytes."""

    boundary_id: str
    admission_id: str
    source_id: str
    ingress_kind: str
    content_sha256: str
    content_size_bytes: int
    purpose_commitment: str
    operator_aad_sha256: str
    replay_token: str
    recorded_at: str
    handle: OpaqueHNCHandle
    hnc_payload_binding: HNCPayloadBindingV0
    admission_commitment: str
    disposition: IngressDisposition = IngressDisposition.ADMITTED_HNC
    local_development_only: bool = True
    production_ready: bool = False

    def __post_init__(self) -> None:
        if self.disposition is not IngressDisposition.ADMITTED_HNC:
            raise OSProtectionError("admitted_disposition_invalid")
        if self.local_development_only is not True or self.production_ready is not False:
            raise OSProtectionError("admitted_scope_invalid")
        if self.handle.boundary_id != self.boundary_id or self.handle.handle_id != self.admission_id:
            raise OSProtectionError("admitted_handle_join_mismatch")
        if not isinstance(self.hnc_payload_binding, HNCPayloadBindingV0):
            raise OSProtectionError("hnc_payload_binding_invalid")
        _bounded_text(
            self.boundary_id,
            field_name="boundary_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        _bounded_text(
            self.admission_id,
            field_name="admission_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        _bounded_text(
            self.source_id,
            field_name="source_id",
            maximum_bytes=_MAX_SOURCE_ID_BYTES,
        )
        _bounded_text(
            self.ingress_kind,
            field_name="ingress_kind",
            maximum_bytes=_MAX_INGRESS_KIND_BYTES,
        )
        parse_timestamp(self.recorded_at, field="recorded_at")
        for value in (
            self.content_sha256,
            self.purpose_commitment,
            self.operator_aad_sha256,
            self.replay_token,
            self.admission_commitment,
        ):
            require_sha256(value, field="admitted_commitment")
        if self.content_size_bytes < 0:
            raise OSProtectionError("content_size_invalid")
        if self.hnc_payload_binding.purpose_commitment != self.purpose_commitment:
            raise OSProtectionError("admitted_hnc_purpose_join_mismatch")
        expected = domain_hash(
            "aureon.plumber.os-admission.v0",
            self._commitment_payload(),
        )
        if expected != self.admission_commitment:
            raise OSProtectionError("admission_commitment_invalid")

    def _commitment_payload(self) -> dict[str, Any]:
        return {
            **_common_public_values(
                disposition=self.disposition,
                boundary_id=self.boundary_id,
                admission_id=self.admission_id,
                source_id=self.source_id,
                ingress_kind=self.ingress_kind,
                content_sha256=self.content_sha256,
                content_size_bytes=self.content_size_bytes,
                purpose_commitment=self.purpose_commitment,
                operator_aad_sha256=self.operator_aad_sha256,
                replay_token=self.replay_token,
                recorded_at=self.recorded_at,
            ),
            "handle": self.handle.public_summary(),
            "hnc_payload_binding": self.hnc_payload_binding.public_summary(),
        }

    def public_summary(self) -> dict[str, Any]:
        summary = {
            **self._commitment_payload(),
            "admission_commitment": self.admission_commitment,
        }
        assert_public_summary_safe(summary)
        return summary


@dataclass(frozen=True, slots=True)
class QuarantinedHNC:
    """Commitment-only denial; the application payload is never retained."""

    boundary_id: str
    admission_id: str
    source_id: str
    ingress_kind: str
    content_sha256: str
    content_size_bytes: int
    purpose_commitment: str
    operator_aad_sha256: str
    replay_token: str
    recorded_at: str
    denial_codes: tuple[str, ...]
    quarantine_record: QuarantineRecord
    hnc_evidence_binding: HNCPayloadBindingV0 | None
    quarantine_commitment: str
    disposition: IngressDisposition = IngressDisposition.QUARANTINED_HNC
    local_development_only: bool = True
    production_ready: bool = False

    def __post_init__(self) -> None:
        if self.disposition is not IngressDisposition.QUARANTINED_HNC:
            raise OSProtectionError("quarantine_disposition_invalid")
        if self.local_development_only is not True or self.production_ready is not False:
            raise OSProtectionError("quarantine_scope_invalid")
        if not self.denial_codes or tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise OSProtectionError("quarantine_denial_codes_invalid")
        if not isinstance(self.quarantine_record, QuarantineRecord):
            raise OSProtectionError("quarantine_record_invalid")
        if self.hnc_evidence_binding is not None and not isinstance(
            self.hnc_evidence_binding,
            HNCPayloadBindingV0,
        ):
            raise OSProtectionError("quarantine_hnc_binding_invalid")
        _bounded_text(
            self.boundary_id,
            field_name="boundary_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        _bounded_text(
            self.admission_id,
            field_name="admission_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        _bounded_text(
            self.source_id,
            field_name="source_id",
            maximum_bytes=_MAX_SOURCE_ID_BYTES,
        )
        _bounded_text(
            self.ingress_kind,
            field_name="ingress_kind",
            maximum_bytes=_MAX_INGRESS_KIND_BYTES,
        )
        parse_timestamp(self.recorded_at, field="recorded_at")
        for value in (
            self.content_sha256,
            self.purpose_commitment,
            self.operator_aad_sha256,
            self.replay_token,
            self.quarantine_commitment,
        ):
            require_sha256(value, field="quarantine_commitment")
        if self.content_size_bytes < 0:
            raise OSProtectionError("content_size_invalid")
        record = self.quarantine_record
        if (
            record.quarantine_id != self.admission_id
            or record.packet_identity != self.admission_id
            or record.session_identity != self.boundary_id
            or record.packet_commitment != self.content_sha256
            or record.denial_codes != self.denial_codes
            or record.quarantined_at != self.recorded_at
            or record.evidence_commitments.get("operator_aad_sha256")
            != self.operator_aad_sha256
            or record.evidence_commitments.get("purpose_commitment")
            != self.purpose_commitment
            or record.evidence_commitments.get("replay_token") != self.replay_token
        ):
            raise OSProtectionError("quarantine_record_join_mismatch")
        if self.hnc_evidence_binding is not None and (
            record.evidence_commitments.get("hnc_quarantine_packet_commitment")
            != self.hnc_evidence_binding.hnc_packet_commitment
            or record.evidence_commitments.get("hnc_quarantine_binding_commitment")
            != self.hnc_evidence_binding.binding_commitment
            or self.hnc_evidence_binding.purpose_commitment
            != _purpose_commitment(OS_QUARANTINE_EVIDENCE_PURPOSE)
        ):
            raise OSProtectionError("quarantine_hnc_join_mismatch")
        expected = domain_hash(
            "aureon.plumber.os-quarantine.v0",
            self._commitment_payload(),
        )
        if expected != self.quarantine_commitment:
            raise OSProtectionError("quarantine_commitment_invalid")

    def _commitment_payload(self) -> dict[str, Any]:
        return {
            **_common_public_values(
                disposition=self.disposition,
                boundary_id=self.boundary_id,
                admission_id=self.admission_id,
                source_id=self.source_id,
                ingress_kind=self.ingress_kind,
                content_sha256=self.content_sha256,
                content_size_bytes=self.content_size_bytes,
                purpose_commitment=self.purpose_commitment,
                operator_aad_sha256=self.operator_aad_sha256,
                replay_token=self.replay_token,
                recorded_at=self.recorded_at,
            ),
            "denial_codes": list(self.denial_codes),
            "quarantine_record": self.quarantine_record.public_summary(),
            "hnc_evidence_binding": (
                None
                if self.hnc_evidence_binding is None
                else self.hnc_evidence_binding.public_summary()
            ),
            "raw_material_retained": False,
        }

    def public_summary(self) -> dict[str, Any]:
        summary = {
            **self._commitment_payload(),
            "quarantine_commitment": self.quarantine_commitment,
        }
        assert_public_summary_safe(summary)
        return summary


AdmissionOutcome: TypeAlias = AdmittedHNC | QuarantinedHNC


@dataclass(slots=True)
class _AdmissionRecord:
    packet: dict[str, Any]
    master_key: bytearray
    purpose: str
    handle_commitment: str
    content_size_bytes: int


class LocalOSProtectionBoundary:
    """Atomic in-memory ingress boundary for local development only."""

    production_ready = False

    def __init__(
        self,
        *,
        boundary_id: str,
        master_key_provider: MasterKeyProvider,
        max_ingress_bytes: int = DEFAULT_MAX_INGRESS_BYTES,
        max_active_handles: int = 64,
        max_active_ingress_bytes: int = 64 * 1024 * 1024,
        max_replay_tokens: int = 8192,
        max_quarantine_evidence: int = 2048,
        trusted_now: Callable[[], datetime] = _system_now,
    ) -> None:
        self._boundary_id = _bounded_text(
            boundary_id,
            field_name="boundary_id",
            maximum_bytes=_MAX_BOUNDARY_ID_BYTES,
        )
        if not callable(master_key_provider):
            raise OSProtectionError("master_key_provider_invalid")
        if not callable(trusted_now):
            raise OSProtectionError("trusted_time_provider_invalid")
        if (
            type(max_ingress_bytes) is not int
            or max_ingress_bytes < 1
            or max_ingress_bytes > DEFAULT_MAX_INGRESS_BYTES
        ):
            raise OSProtectionError("max_ingress_bytes_invalid")
        if (
            type(max_active_handles) is not int
            or max_active_handles < 1
            or max_active_handles > _MAX_ACTIVE_HANDLES_LIMIT
        ):
            raise OSProtectionError("max_active_handles_invalid")
        if (
            type(max_active_ingress_bytes) is not int
            or max_active_ingress_bytes < 1
            or max_active_ingress_bytes > _MAX_ACTIVE_INGRESS_BYTES_LIMIT
        ):
            raise OSProtectionError("max_active_ingress_bytes_invalid")
        if (
            type(max_replay_tokens) is not int
            or max_replay_tokens < 1
            or max_replay_tokens > _MAX_REPLAY_TOKENS_LIMIT
        ):
            raise OSProtectionError("max_replay_tokens_invalid")
        if (
            type(max_quarantine_evidence) is not int
            or max_quarantine_evidence < 1
            or max_quarantine_evidence > _MAX_QUARANTINE_EVIDENCE_LIMIT
        ):
            raise OSProtectionError("max_quarantine_evidence_invalid")
        self._master_key_provider = master_key_provider
        self._max_ingress_bytes = max_ingress_bytes
        self._max_active_handles = max_active_handles
        self._max_active_ingress_bytes = max_active_ingress_bytes
        self._max_replay_tokens = max_replay_tokens
        self._max_quarantine_evidence = max_quarantine_evidence
        self._trusted_now = trusted_now
        self._seen_replay_tokens: set[str] = set()
        self._records: dict[str, _AdmissionRecord] = {}
        self._active_ingress_bytes = 0
        self._consumed_handle_commitments: set[str] = set()
        self._quarantine_packets: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _recorded_at(self) -> tuple[datetime, str | None]:
        try:
            current = require_aware_datetime(self._trusted_now(), field="trusted_now")
            if current.microsecond:
                return current.replace(microsecond=0), "trusted_time_precision_invalid"
            return current, None
        except BaseException:
            # Evidence still needs a bounded timestamp when the trusted clock is
            # unavailable.  This fallback never authorizes admission.
            return _system_now(), "trusted_time_unavailable"

    def _key_material(self) -> tuple[bytes | None, str | None]:
        try:
            supplied = self._master_key_provider()
            if supplied is None:
                return None, "master_key_unavailable"
            return normalize_hnc_key_material(supplied), None
        except BaseException:
            return None, "master_key_invalid"

    def admit_external(
        self,
        raw: bytes | bytearray | memoryview,
        *,
        source_id: str,
        ingress_kind: str,
        purpose: str,
        operator_aad: Mapping[str, Any] | None = None,
        content_validator: ContentValidator | None = None,
    ) -> AdmissionOutcome:
        """Seal one bounded ingress or produce commitment-only quarantine.

        The optional validator is a pure schema/content predicate.  It receives
        a read-only view and cannot authorize effects.  False, an exception, or
        a non-boolean result quarantines the material without exposing details.
        """

        source = _bounded_text(
            source_id,
            field_name="source_id",
            maximum_bytes=_MAX_SOURCE_ID_BYTES,
        )
        kind = _bounded_text(
            ingress_kind,
            field_name="ingress_kind",
            maximum_bytes=_MAX_INGRESS_KIND_BYTES,
        )
        bounded_purpose = _bounded_text(
            purpose,
            field_name="purpose",
            maximum_bytes=_MAX_PURPOSE_BYTES,
        )
        if operator_aad is not None and not isinstance(operator_aad, Mapping):
            raise OSProtectionError("operator_aad_invalid")
        if content_validator is not None and not callable(content_validator):
            raise OSProtectionError("content_validator_invalid")

        denial_codes: set[str] = set()
        try:
            caller_aad_snapshot = _snapshot_operator_aad(dict(operator_aad or {}))
            caller_aad_bytes = canonical_json_bytes(caller_aad_snapshot)
            if len(caller_aad_bytes) > MAX_OPERATOR_AAD_BYTES:
                raise OSProtectionError("operator_aad_invalid")
            decoded_caller_aad = decode_canonical_json(
                caller_aad_bytes,
                require_mapping=True,
                max_bytes=MAX_OPERATOR_AAD_BYTES,
            )
            if not isinstance(decoded_caller_aad, dict):  # pragma: no cover
                raise OSProtectionError("operator_aad_invalid")
            caller_aad = decoded_caller_aad
        except BaseException:
            caller_aad = {}
            denial_codes.add("operator_aad_invalid")

        payload: bytes | None = None
        try:
            view = memoryview(raw)
            content_size = view.nbytes
            if content_size <= self._max_ingress_bytes:
                # Snapshot once so a caller-owned bytearray cannot change
                # between commitment, validation, and encryption.
                payload = view.tobytes()
                content_sha256 = hashlib.sha256(payload).hexdigest()
            else:
                # Do not make a second, potentially huge copy merely to deny
                # an already oversized ingress.
                content_sha256 = hashlib.sha256(view).hexdigest()
        except BaseException:
            view = memoryview(b"")
            content_size = 0
            content_sha256 = domain_hash(
                "aureon.plumber.invalid-ingress-type.v0",
                {"type": type(raw).__name__},
            )
            denial_codes.add("ingress_bytes_invalid")

        if content_size == 0:
            denial_codes.add("ingress_empty")
        if content_size > self._max_ingress_bytes:
            denial_codes.add("ingress_too_large")

        purpose_hash = _purpose_commitment(bounded_purpose)
        ingress_aad: dict[str, Any] = {
            "schema": OS_INGRESS_AAD_SCHEMA,
            "boundary_id": self._boundary_id,
            "source_id": source,
            "ingress_kind": kind,
            "content_sha256": content_sha256,
            "content_size_bytes": content_size,
            "purpose": bounded_purpose,
            "purpose_commitment": purpose_hash,
            "caller_aad": caller_aad,
            "source_truth_established_by_local_wrapping": False,
        }
        try:
            operator_aad_sha256 = sha256_hex(canonical_json_bytes(ingress_aad))
        except BaseException:
            operator_aad_sha256 = domain_hash(
                "aureon.plumber.invalid-os-ingress-aad.v0",
                {
                    "boundary_id": self._boundary_id,
                    "source_id": source,
                    "ingress_kind": kind,
                    "content_sha256": content_sha256,
                    "content_size_bytes": content_size,
                    "purpose_commitment": purpose_hash,
                },
            )
            denial_codes.add("operator_aad_invalid")
        replay_token = domain_hash(
            "aureon.plumber.os-ingress-replay.v0",
            {
                "boundary_id": self._boundary_id,
                "source_id": source,
                "ingress_kind": kind,
                "content_sha256": content_sha256,
                "content_size_bytes": content_size,
                "purpose_commitment": purpose_hash,
                "operator_aad_sha256": operator_aad_sha256,
            },
        )
        admission_id = f"os-ingress-{secrets.token_hex(16)}"
        recorded_at, time_error = self._recorded_at()
        if time_error is not None:
            denial_codes.add(time_error)

        with self._lock:
            if replay_token in self._seen_replay_tokens:
                denial_codes.add("ingress_replay_detected")
            elif len(self._seen_replay_tokens) >= self._max_replay_tokens:
                denial_codes.add("replay_ledger_capacity_exhausted")
            else:
                self._seen_replay_tokens.add(replay_token)

        if not denial_codes and content_validator is not None:
            try:
                if payload is None:  # pragma: no cover - guarded by denial codes
                    raise OSProtectionError("ingress_payload_snapshot_missing")
                valid = content_validator(memoryview(payload).toreadonly())
            except BaseException:
                valid = False
            if valid is not True:
                denial_codes.add("ingress_content_invalid")

        key_material, key_error = self._key_material()
        if key_error is not None:
            denial_codes.add(key_error)

        if not denial_codes and key_material is not None:
            try:
                if payload is None:  # pragma: no cover - guarded by denial codes
                    raise OSProtectionError("ingress_payload_snapshot_missing")
                packet = build_hnc_quantum_packet(
                    payload,
                    key_material,
                    purpose=bounded_purpose,
                    operator_aad=ingress_aad,
                    hnc_context={
                        "os_protection_schema": OS_PROTECTION_SCHEMA,
                        "admission_id": admission_id,
                        "source_truth_established_by_local_wrapping": False,
                    },
                )
                validation = validate_hnc_packet_contract(packet)
                if validation.get("valid") is not True:
                    raise OSProtectionError("hnc_packet_contract_invalid")
                if packet.get("operator_aad") != ingress_aad:
                    raise OSProtectionError("hnc_operator_aad_join_mismatch")
                binding = bind_hnc_packet(packet)
            except BaseException:
                denial_codes.add("hnc_packet_seal_failed")
            else:
                handle = OpaqueHNCHandle.issue(
                    boundary_id=self._boundary_id,
                    handle_id=admission_id,
                )
                with self._lock:
                    capacity_available = (
                        len(self._records) < self._max_active_handles
                        and self._active_ingress_bytes + content_size
                        <= self._max_active_ingress_bytes
                    )
                    if capacity_available:
                        self._records[admission_id] = _AdmissionRecord(
                            packet=dict(packet),
                            master_key=bytearray(key_material),
                            purpose=bounded_purpose,
                            handle_commitment=handle.handle_commitment,
                            content_size_bytes=content_size,
                        )
                        self._active_ingress_bytes += content_size
                    else:
                        denial_codes.add("active_admission_capacity_exhausted")
                if not capacity_available:
                    return self._quarantine(
                        admission_id=admission_id,
                        source_id=source,
                        ingress_kind=kind,
                        content_sha256=content_sha256,
                        content_size_bytes=content_size,
                        purpose_commitment=purpose_hash,
                        operator_aad_sha256=operator_aad_sha256,
                        replay_token=replay_token,
                        ingress_aad=ingress_aad,
                        denial_codes=denial_codes,
                        recorded_at=recorded_at,
                        key_material=key_material,
                    )
                recorded_at_text = format_timestamp(recorded_at)
                values = _common_public_values(
                    disposition=IngressDisposition.ADMITTED_HNC,
                    boundary_id=self._boundary_id,
                    admission_id=admission_id,
                    source_id=source,
                    ingress_kind=kind,
                    content_sha256=content_sha256,
                    content_size_bytes=content_size,
                    purpose_commitment=purpose_hash,
                    operator_aad_sha256=operator_aad_sha256,
                    replay_token=replay_token,
                    recorded_at=recorded_at_text,
                )
                values.update(
                    {
                        "handle": handle.public_summary(),
                        "hnc_payload_binding": binding.public_summary(),
                    }
                )
                return AdmittedHNC(
                    boundary_id=self._boundary_id,
                    admission_id=admission_id,
                    source_id=source,
                    ingress_kind=kind,
                    content_sha256=content_sha256,
                    content_size_bytes=content_size,
                    purpose_commitment=purpose_hash,
                    operator_aad_sha256=operator_aad_sha256,
                    replay_token=replay_token,
                    recorded_at=recorded_at_text,
                    handle=handle,
                    hnc_payload_binding=binding,
                    admission_commitment=domain_hash(
                        "aureon.plumber.os-admission.v0",
                        values,
                    ),
                )

        return self._quarantine(
            admission_id=admission_id,
            source_id=source,
            ingress_kind=kind,
            content_sha256=content_sha256,
            content_size_bytes=content_size,
            purpose_commitment=purpose_hash,
            operator_aad_sha256=operator_aad_sha256,
            replay_token=replay_token,
            ingress_aad=ingress_aad,
            denial_codes=denial_codes,
            recorded_at=recorded_at,
            key_material=key_material,
        )

    def _quarantine(
        self,
        *,
        admission_id: str,
        source_id: str,
        ingress_kind: str,
        content_sha256: str,
        content_size_bytes: int,
        purpose_commitment: str,
        operator_aad_sha256: str,
        replay_token: str,
        ingress_aad: Mapping[str, Any],
        denial_codes: set[str],
        recorded_at: datetime,
        key_material: bytes | None,
    ) -> QuarantinedHNC:
        codes = set(denial_codes or {"ingress_denied"})
        evidence_binding: HNCPayloadBindingV0 | None = None
        if key_material is not None:
            evidence_payload = {
                "schema": OS_QUARANTINE_EVIDENCE_SCHEMA,
                "admission_id": admission_id,
                "boundary_id": self._boundary_id,
                "source_id": source_id,
                "ingress_kind": ingress_kind,
                "content_sha256": content_sha256,
                "content_size_bytes": content_size_bytes,
                "purpose_commitment": purpose_commitment,
                "operator_aad_sha256": operator_aad_sha256,
                "replay_token": replay_token,
                "denial_codes": sorted(codes),
                "raw_material_retained": False,
                "source_truth_established_by_local_wrapping": False,
            }
            quarantine_aad = {
                **dict(ingress_aad),
                "quarantine": True,
                "quarantine_evidence_schema": OS_QUARANTINE_EVIDENCE_SCHEMA,
                "denial_codes": sorted(codes),
            }
            with self._lock:
                if len(self._quarantine_packets) >= self._max_quarantine_evidence:
                    codes.add("quarantine_evidence_capacity_exhausted")
                else:
                    try:
                        evidence_packet = build_hnc_quantum_packet(
                            canonical_json_bytes(evidence_payload),
                            key_material,
                            purpose=OS_QUARANTINE_EVIDENCE_PURPOSE,
                            operator_aad=quarantine_aad,
                            hnc_context={
                                "original_purpose_commitment": purpose_commitment,
                                "metadata_only_quarantine": True,
                            },
                        )
                        validation = validate_hnc_packet_contract(evidence_packet)
                        if validation.get("valid") is not True:
                            raise OSProtectionError("quarantine_hnc_contract_invalid")
                        evidence_binding = bind_hnc_packet(evidence_packet)
                    except BaseException:
                        codes.add("quarantine_hnc_evidence_unavailable")
                        evidence_binding = None
                    else:
                        self._quarantine_packets[admission_id] = dict(evidence_packet)

        normalized_codes = tuple(sorted(codes))
        evidence_commitments = {
            "operator_aad_sha256": operator_aad_sha256,
            "purpose_commitment": purpose_commitment,
            "replay_token": replay_token,
        }
        if evidence_binding is not None:
            evidence_commitments.update(
                {
                    "hnc_quarantine_packet_commitment": evidence_binding.hnc_packet_commitment,
                    "hnc_quarantine_binding_commitment": evidence_binding.binding_commitment,
                }
            )
        record = QuarantineRecord.build(
            quarantine_id=admission_id,
            packet_identity=admission_id,
            session_identity=self._boundary_id,
            packet_commitment=content_sha256,
            denial_codes=normalized_codes,
            evidence_commitments=evidence_commitments,
            quarantined_at=recorded_at,
        )
        recorded_at_text = format_timestamp(recorded_at)
        values = {
            **_common_public_values(
                disposition=IngressDisposition.QUARANTINED_HNC,
                boundary_id=self._boundary_id,
                admission_id=admission_id,
                source_id=source_id,
                ingress_kind=ingress_kind,
                content_sha256=content_sha256,
                content_size_bytes=content_size_bytes,
                purpose_commitment=purpose_commitment,
                operator_aad_sha256=operator_aad_sha256,
                replay_token=replay_token,
                recorded_at=recorded_at_text,
            ),
            "denial_codes": list(normalized_codes),
            "quarantine_record": record.public_summary(),
            "hnc_evidence_binding": (
                None if evidence_binding is None else evidence_binding.public_summary()
            ),
            "raw_material_retained": False,
        }
        return QuarantinedHNC(
            boundary_id=self._boundary_id,
            admission_id=admission_id,
            source_id=source_id,
            ingress_kind=ingress_kind,
            content_sha256=content_sha256,
            content_size_bytes=content_size_bytes,
            purpose_commitment=purpose_commitment,
            operator_aad_sha256=operator_aad_sha256,
            replay_token=replay_token,
            recorded_at=recorded_at_text,
            denial_codes=normalized_codes,
            quarantine_record=record,
            hnc_evidence_binding=evidence_binding,
            quarantine_commitment=domain_hash(
                "aureon.plumber.os-quarantine.v0",
                values,
            ),
        )

    def protect_for_magic_star(
        self,
        handle: OpaqueHNCHandle,
        *,
        custody: LocalDevelopmentStarCustodyV02,
        release_context_sha256: str,
    ) -> ProtectedMagicStarPacketV02:
        """Consume one opaque admission and hand its carrier directly to custody."""

        if not isinstance(custody, LocalDevelopmentStarCustodyV02):
            raise OSProtectionError("local_magic_star_custody_required")
        require_sha256(release_context_sha256, field="release_context_sha256")
        record = self._consume_admitted_record(handle)
        key = bytes(record.master_key)
        try:
            protected = custody.protect_carrier(
                packet_id=handle.handle_id,
                purpose=record.purpose,
                release_context_sha256=release_context_sha256,
                legacy_carrier=record.packet,
                legacy_master_key=key,
            )
        except BaseException:
            raise OSProtectionError("magic_star_protection_failed") from None
        finally:
            record.master_key[:] = bytes(len(record.master_key))
        if not isinstance(protected, ProtectedMagicStarPacketV02):
            raise OSProtectionError("magic_star_protected_packet_invalid")
        return protected

    def _consume_admitted_record(self, handle: OpaqueHNCHandle) -> _AdmissionRecord:
        """Atomically burn one valid handle before any caller-controlled work."""

        if not isinstance(handle, OpaqueHNCHandle):
            raise OSProtectionError("opaque_hnc_handle_required")
        if handle.boundary_id != self._boundary_id:
            raise OSProtectionError("opaque_hnc_handle_boundary_mismatch")
        with self._lock:
            record = self._records.get(handle.handle_id)
            if (
                record is None
                or record.handle_commitment != handle.handle_commitment
                or handle.handle_commitment in self._consumed_handle_commitments
                or not secrets.compare_digest(
                    handle.handle_commitment,
                    _handle_commitment(
                        boundary_id=handle.boundary_id,
                        handle_id=handle.handle_id,
                        token=handle.token,
                    ),
                )
            ):
                raise OSProtectionError("opaque_hnc_handle_unavailable_or_replayed")
            # Burn before the downstream call.  Any failure is fail-closed and
            # cannot expose a retry path for the same admitted carrier.
            self._records.pop(handle.handle_id, None)
            self._active_ingress_bytes = max(
                0,
                self._active_ingress_bytes - record.content_size_bytes,
            )
            self._consumed_handle_commitments.add(handle.handle_commitment)
        return record

    def discard_admitted(
        self,
        handle: OpaqueHNCHandle,
        *,
        reason_code: str,
    ) -> dict[str, Any]:
        """Burn a held admission without decoding or handing off its carrier."""

        reason = _bounded_text(
            reason_code,
            field_name="discard_reason_code",
            maximum_bytes=128,
        )
        record = self._consume_admitted_record(handle)
        try:
            summary = {
                "schema": OS_PROTECTION_SCHEMA,
                "disposition": "DISCARDED_HNC",
                "boundary_id": self._boundary_id,
                "admission_id": handle.handle_id,
                "handle_commitment": handle.handle_commitment,
                "reason_code": reason,
                "carrier_released": False,
                "plaintext_decoded": False,
                "local_development_only": True,
                "production_ready": False,
            }
            assert_public_summary_safe(summary)
            return summary
        finally:
            record.master_key[:] = bytes(len(record.master_key))

    def public_summary(self) -> dict[str, Any]:
        with self._lock:
            summary = {
                "schema": OS_PROTECTION_SCHEMA,
                "boundary_id": self._boundary_id,
                "scope": "in_memory_local_development_only",
                "max_ingress_bytes": self._max_ingress_bytes,
                "max_active_handles": self._max_active_handles,
                "max_active_ingress_bytes": self._max_active_ingress_bytes,
                "max_replay_tokens": self._max_replay_tokens,
                "max_quarantine_evidence": self._max_quarantine_evidence,
                "seen_replay_count": len(self._seen_replay_tokens),
                "active_opaque_handle_count": len(self._records),
                "active_ingress_bytes": self._active_ingress_bytes,
                "consumed_opaque_handle_count": len(self._consumed_handle_commitments),
                "quarantine_evidence_count": len(self._quarantine_packets),
                "raw_material_returned": False,
                "persistent": False,
                "local_development_only": True,
                "production_ready": False,
            }
        assert_public_summary_safe(summary)
        return summary


__all__ = [
    "DEFAULT_MAX_INGRESS_BYTES",
    "MAX_OPERATOR_AAD_BYTES",
    "OS_INGRESS_AAD_SCHEMA",
    "OS_PROTECTION_SCHEMA",
    "OS_QUARANTINE_EVIDENCE_PURPOSE",
    "OS_QUARANTINE_EVIDENCE_SCHEMA",
    "AdmissionOutcome",
    "AdmittedHNC",
    "ContentValidator",
    "IngressDisposition",
    "LocalOSProtectionBoundary",
    "MasterKeyProvider",
    "OSProtectionError",
    "OpaqueHNCHandle",
    "QuarantinedHNC",
]
