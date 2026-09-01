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
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, Protocol, TypeAlias

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
    StarCustodyError,
    validate_magic_star_inner_carrier_capacity_v02,
)

OS_PROTECTION_SCHEMA: Final = "aureon.plumber.os-protection.v0"
OS_INGRESS_AAD_SCHEMA: Final = "aureon.plumber.os-ingress-aad.v0"
OS_QUARANTINE_EVIDENCE_SCHEMA: Final = "aureon.plumber.os-quarantine-evidence.v0"
OS_QUARANTINE_EVIDENCE_PURPOSE: Final = "aureon.plumber.os.quarantine-evidence.v0"
OS_KEY_PREFLIGHT_SCHEMA: Final = "aureon.plumber.os-key-preflight.v0"
OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA: Final = (
    "aureon.plumber.os-durable-quarantine-evidence.v04"
)
OS_RUNTIME_GUARD_LIFECYCLE_SCHEMA: Final = (
    "aureon.plumber.os-runtime-guard-lifecycle.v04"
)
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


class QuarantineEvidenceSink(Protocol):
    """Pre-opened durable sink used without returning sealed HNC packets."""

    def preflight(self) -> Mapping[str, Any]: ...

    def append_violation(
        self,
        *,
        intrusion_id: str,
        runtime_metadata: Mapping[str, Any],
        quarantine_summary: Mapping[str, Any],
        hnc_packet: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def seal_for_runtime_guard(self, owner_token: str) -> Mapping[str, Any]: ...

    def validate_runtime_guard_seal(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> Mapping[str, Any]: ...

    def runtime_guard_lifecycle_lease(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> AbstractContextManager[Mapping[str, Any]]: ...


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
        quarantine_evidence_sink: QuarantineEvidenceSink | None = None,
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
        if quarantine_evidence_sink is not None and (
            not callable(getattr(quarantine_evidence_sink, "preflight", None))
            or not callable(
                getattr(quarantine_evidence_sink, "append_violation", None)
            )
            or not callable(
                getattr(quarantine_evidence_sink, "seal_for_runtime_guard", None)
            )
            or not callable(
                getattr(
                    quarantine_evidence_sink,
                    "validate_runtime_guard_seal",
                    None,
                )
            )
            or not callable(
                getattr(
                    quarantine_evidence_sink,
                    "runtime_guard_lifecycle_lease",
                    None,
                )
            )
        ):
            raise OSProtectionError("quarantine_evidence_sink_invalid")
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
        self._quarantine_evidence_sink = quarantine_evidence_sink
        self._durable_evidence_terminal = False
        self._durable_evidence_failure_code: str | None = None
        self._durable_evidence_count = 0
        self._durable_evidence_head_commitment = "0" * 64
        self._durable_evidence_ledger_id: str | None = None
        self._durable_evidence_ledger_instance_commitment: str | None = None
        self._durable_evidence_entry_count: int | None = None
        self._durable_evidence_violation_count: int | None = None
        self._durable_evidence_last_receipt_sequence: int | None = None
        self._durable_evidence_packets_persisted = False
        # Serializes one complete boundary operation with runtime-guard
        # evidence lifecycle transitions.  The state lock below remains the
        # short critical-section lock for counters and opaque records; this
        # lifecycle lock may intentionally span validator/custody calls so a
        # terminal transition is linearly ordered before or after the whole
        # operation, never through its middle.
        self._runtime_guard_lifecycle_lock = threading.RLock()
        self._runtime_guard_sealed = False
        self._runtime_guard_owner_token: str | None = None
        self._runtime_guard_owner_token_sha256: str | None = None
        self._runtime_guard_sink_generation: int | None = None
        self._runtime_guard_lifecycle_generation = 0
        self._seen_replay_tokens: set[str] = set()
        self._records: dict[str, _AdmissionRecord] = {}
        self._active_ingress_bytes = 0
        self._consumed_handle_commitments: set[str] = set()
        self._quarantine_packets: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _mark_durable_evidence_terminal_locked(self, code: str) -> None:
        """Make one sticky terminal transition while ``self._lock`` is held."""

        selected = _bounded_text(
            code,
            field_name="durable_quarantine_failure_code",
            maximum_bytes=128,
        )
        if not self._durable_evidence_terminal:
            self._runtime_guard_lifecycle_generation += 1
            self._durable_evidence_terminal = True
            self._durable_evidence_failure_code = selected
        elif self._durable_evidence_failure_code is None:  # pragma: no cover
            self._durable_evidence_failure_code = selected

    def _lifecycle_operation_generation(self) -> int:
        """Snapshot one non-terminal generation for later atomic commit."""

        with self._runtime_guard_lifecycle_lock:
            self._require_durable_evidence_ready()
            with self._lock:
                if self._durable_evidence_terminal:
                    raise OSProtectionError("durable_quarantine_evidence_terminal")
                return self._runtime_guard_lifecycle_generation

    def _require_lifecycle_generation_locked(self, generation: int) -> None:
        """Reject in-flight work invalidated by a completed transition."""

        if (
            self._durable_evidence_terminal
            or generation != self._runtime_guard_lifecycle_generation
        ):
            raise OSProtectionError("durable_quarantine_evidence_terminal")

    @contextmanager
    def _lifecycle_commit_lease(self, generation: int) -> Iterator[None]:
        """Linearize one admission/custody return against durable lifecycle."""

        with self._runtime_guard_lifecycle_lock:
            with self._lock:
                self._require_lifecycle_generation_locked(generation)
                sink = self._quarantine_evidence_sink
                sealed = self._runtime_guard_sealed
                owner_token = self._runtime_guard_owner_token
                sink_generation = self._runtime_guard_sink_generation
            if not sealed or sink is None:
                self._require_durable_evidence_ready()
                with self._lock:
                    self._require_lifecycle_generation_locked(generation)
                yield
                with self._lock:
                    self._require_lifecycle_generation_locked(generation)
                return
            lease = getattr(sink, "runtime_guard_lifecycle_lease", None)
            if (
                not callable(lease)
                or owner_token is None
                or sink_generation is None
            ):
                with self._lock:
                    self._mark_durable_evidence_terminal_locked(
                        "runtime_guard_sink_lease_unsupported"
                    )
                raise OSProtectionError("runtime_guard_sink_lease_unsupported")
            body_failed = False
            try:
                with lease(owner_token, sink_generation) as raw:
                    state = self._validated_runtime_guard_sink_seal(
                        raw,
                        owner_token_sha256=sha256_hex(
                            owner_token.encode("utf-8", errors="strict")
                        ),
                        expected_generation=sink_generation,
                    )
                    with self._lock:
                        self._join_durable_sink_state(
                            {
                                "ledger_id": state["ledger_id"],
                                "ledger_instance_commitment": state[
                                    "ledger_instance_commitment"
                                ],
                                "entry_count": state["entry_count"],
                                "violation_count": state["violation_count"],
                                "persisted": state["violation_count"] > 0,
                            }
                        )
                        self._require_lifecycle_generation_locked(generation)
                    try:
                        yield
                    except BaseException:
                        body_failed = True
                        raise
                    with self._lock:
                        self._require_lifecycle_generation_locked(generation)
            except BaseException as exc:
                if body_failed:
                    raise
                with self._lock:
                    failure_code = (
                        exc.code
                        if isinstance(exc, OSProtectionError)
                        else "runtime_guard_sink_lease_failed"
                    )
                    self._mark_durable_evidence_terminal_locked(
                        failure_code
                    )
                if isinstance(exc, OSProtectionError):
                    raise
                raise OSProtectionError("runtime_guard_sink_lease_failed") from exc

    def durable_quarantine_evidence_preflight(self) -> dict[str, Any]:
        """Validate the pre-opened sink without exposing packet or key material."""

        with self._runtime_guard_lifecycle_lock, self._lock:
            sink = self._quarantine_evidence_sink
            if sink is None:
                result = {
                    "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
                    "configured": False,
                    "ready": False,
                    "reason_code": "durable_quarantine_evidence_not_configured",
                    "remaining_violation_capacity": 0,
                    "encrypted_hnc_packets_persisted": False,
                    "external_head_anchor_attested": False,
                    "magic_star_durable_custody_attested": False,
                    "production_ready": False,
                }
                assert_public_summary_safe(result)
                return result
            if self._durable_evidence_terminal:
                result = {
                    "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
                    "configured": True,
                    "ready": False,
                    "reason_code": self._durable_evidence_failure_code
                    or "durable_quarantine_evidence_terminal",
                    "remaining_violation_capacity": 0,
                    "encrypted_hnc_packets_persisted": (
                        self._durable_evidence_packets_persisted
                    ),
                    "external_head_anchor_attested": False,
                    "magic_star_durable_custody_attested": False,
                    "production_ready": False,
                }
                assert_public_summary_safe(result)
                return result
            try:
                state = self._validated_durable_sink_state(sink.preflight())
                self._join_durable_sink_state(state)
                result = {
                    "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
                    "configured": True,
                    "ready": state["ready"],
                    "reason_code": state["reason_code"],
                    "remaining_violation_capacity": state["remaining"],
                    "encrypted_hnc_packets_persisted": state["persisted"],
                    "external_head_anchor_attested": state[
                        "external_head_anchor_attested"
                    ],
                    "magic_star_durable_custody_attested": state[
                        "magic_star_durable_custody_attested"
                    ],
                    "production_ready": False,
                }
                assert_public_summary_safe(result)
                if state["ready"] is not True:
                    raise OSProtectionError("durable_quarantine_evidence_not_ready")
                return result
            except BaseException as exc:
                failure_code = (
                    exc.code
                    if isinstance(exc, OSProtectionError)
                    else "durable_quarantine_evidence_preflight_failed"
                )
                self._mark_durable_evidence_terminal_locked(failure_code)
                raise OSProtectionError(
                    "durable_quarantine_evidence_preflight_failed"
                ) from exc

    def _validated_durable_sink_state(
        self,
        raw: Mapping[str, Any] | object,
    ) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise OSProtectionError("durable_quarantine_evidence_preflight_invalid")
        ready = raw.get("ready")
        remaining = raw.get("remaining_violation_capacity")
        entry_count = raw.get("entry_count")
        violation_count = raw.get("violation_count")
        ledger_id = raw.get("ledger_id")
        try:
            ledger_instance_commitment = require_sha256(
                raw.get("ledger_instance_commitment"),
                field="durable_ledger_instance_commitment",
            )
        except (TypeError, ValueError) as exc:
            raise OSProtectionError(
                "durable_quarantine_evidence_preflight_invalid"
            ) from exc
        persisted = raw.get("encrypted_hnc_packets_persisted")
        if (
            type(ready) is not bool
            or type(remaining) is not int
            or remaining < 0
            or type(entry_count) is not int
            or entry_count < 1
            or type(violation_count) is not int
            or violation_count < 0
            or violation_count > entry_count
            or not isinstance(ledger_id, str)
            or not ledger_id
            or type(persisted) is not bool
        ):
            raise OSProtectionError("durable_quarantine_evidence_preflight_invalid")
        reason_code = _bounded_text(
            raw.get("reason_code"),
            field_name="durable_quarantine_reason_code",
            maximum_bytes=128,
        )
        actual_persistence = persisted and violation_count > 0
        return {
            "ledger_id": ledger_id,
            "ledger_instance_commitment": ledger_instance_commitment,
            "ready": ready,
            "reason_code": reason_code,
            "remaining": remaining,
            "entry_count": entry_count,
            "violation_count": violation_count,
            "persisted": actual_persistence,
            "external_head_anchor_attested": (
                raw.get("external_head_anchor_attested") is True
            ),
            "magic_star_durable_custody_attested": (
                raw.get("magic_star_durable_custody_attested") is True
            ),
        }

    def _join_durable_sink_state(self, state: Mapping[str, Any]) -> None:
        ledger_id = str(state["ledger_id"])
        ledger_instance_commitment = str(state["ledger_instance_commitment"])
        entry_count = int(state["entry_count"])
        violation_count = int(state["violation_count"])
        if self._durable_evidence_ledger_id is None:
            self._durable_evidence_ledger_id = ledger_id
            self._durable_evidence_ledger_instance_commitment = (
                ledger_instance_commitment
            )
            self._durable_evidence_entry_count = entry_count
            self._durable_evidence_violation_count = violation_count
        elif (
            ledger_id != self._durable_evidence_ledger_id
            or ledger_instance_commitment
            != self._durable_evidence_ledger_instance_commitment
            or entry_count != self._durable_evidence_entry_count
            or violation_count != self._durable_evidence_violation_count
        ):
            raise OSProtectionError("durable_quarantine_evidence_state_join_invalid")
        if self._durable_evidence_packets_persisted and state["persisted"] is not True:
            raise OSProtectionError("durable_quarantine_evidence_persistence_regressed")
        self._durable_evidence_packets_persisted = (
            self._durable_evidence_packets_persisted or state["persisted"] is True
        )

    def _require_durable_evidence_ready(self) -> None:
        with self._lock:
            configured = self._quarantine_evidence_sink is not None
        if not configured:
            return
        preflight = self.durable_quarantine_evidence_preflight()
        if preflight.get("ready") is not True:
            raise OSProtectionError("durable_quarantine_evidence_terminal")

    def _validated_runtime_guard_sink_seal(
        self,
        raw: Mapping[str, Any] | object,
        *,
        owner_token_sha256: str,
        expected_generation: int | None,
    ) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise OSProtectionError("runtime_guard_sink_seal_invalid")
        generation = raw.get("lifecycle_generation")
        if (
            raw.get("sealed") is not True
            or raw.get("owner_token_sha256") != owner_token_sha256
            or type(generation) is not int
            or generation < 1
            or (
                expected_generation is not None
                and generation != expected_generation
            )
            or raw.get("close_rejected_while_sealed") is not True
            or raw.get("ready") is not True
            or raw.get("production_ready") is not False
        ):
            raise OSProtectionError("runtime_guard_sink_seal_invalid")
        ledger_id = _bounded_text(
            raw.get("ledger_id"),
            field_name="runtime_guard_sink_ledger_id",
            maximum_bytes=128,
        )
        try:
            ledger_instance_commitment = require_sha256(
                raw.get("ledger_instance_commitment"),
                field="runtime_guard_sink_ledger_instance_commitment",
            )
        except (TypeError, ValueError) as exc:
            raise OSProtectionError("runtime_guard_sink_seal_invalid") from exc
        entry_count = raw.get("entry_count")
        violation_count = raw.get("violation_count")
        remaining = raw.get("remaining_violation_capacity")
        if (
            type(entry_count) is not int
            or entry_count < 1
            or type(violation_count) is not int
            or violation_count < 0
            or violation_count > entry_count
            or type(remaining) is not int
            or remaining < 0
        ):
            raise OSProtectionError("runtime_guard_sink_seal_invalid")
        return {
            "ledger_id": ledger_id,
            "ledger_instance_commitment": ledger_instance_commitment,
            "generation": generation,
            "entry_count": entry_count,
            "violation_count": violation_count,
            "remaining": remaining,
        }

    def seal_for_runtime_guard(self, owner_token: str) -> dict[str, Any]:
        """Irreversibly pin the configured durable sink before hook install."""

        token = _bounded_text(
            owner_token,
            field_name="runtime_guard_owner_token",
            maximum_bytes=128,
        )
        owner_sha256 = sha256_hex(token.encode("utf-8", errors="strict"))
        with self._runtime_guard_lifecycle_lock:
            with self._lock:
                if self._durable_evidence_terminal:
                    raise OSProtectionError("durable_quarantine_evidence_terminal")
                if self._runtime_guard_sealed:
                    if not secrets.compare_digest(
                        owner_sha256,
                        self._runtime_guard_owner_token_sha256 or "",
                    ):
                        raise OSProtectionError("runtime_guard_owner_mismatch")
                    return self.validate_runtime_guard_seal(
                        token,
                        self._runtime_guard_lifecycle_generation,
                    )
                sink = self._quarantine_evidence_sink
            sink_generation: int
            ledger_id: str | None = None
            try:
                if sink is None:
                    sink_generation = 1
                else:
                    seal = getattr(sink, "seal_for_runtime_guard", None)
                    if not callable(seal):
                        raise OSProtectionError(
                            "runtime_guard_sink_seal_unsupported"
                        )
                    state = self._validated_runtime_guard_sink_seal(
                        seal(token),
                        owner_token_sha256=owner_sha256,
                        expected_generation=None,
                    )
                    sink_generation = int(state["generation"])
                    ledger_id = str(state["ledger_id"])
                    with self._lock:
                        self._join_durable_sink_state(
                            {
                                "ledger_id": ledger_id,
                                "ledger_instance_commitment": state[
                                    "ledger_instance_commitment"
                                ],
                                "entry_count": state["entry_count"],
                                "violation_count": state["violation_count"],
                                "persisted": state["violation_count"] > 0,
                            }
                        )
            except BaseException as exc:
                with self._lock:
                    failure_code = (
                        exc.code
                        if isinstance(exc, OSProtectionError)
                        else "runtime_guard_sink_seal_failed"
                    )
                    self._mark_durable_evidence_terminal_locked(failure_code)
                raise OSProtectionError("runtime_guard_sink_seal_failed") from exc
            with self._lock:
                self._runtime_guard_sealed = True
                self._runtime_guard_owner_token = token
                self._runtime_guard_owner_token_sha256 = owner_sha256
                self._runtime_guard_sink_generation = sink_generation
                self._runtime_guard_lifecycle_generation += 1
                result = {
                    "schema": OS_RUNTIME_GUARD_LIFECYCLE_SCHEMA,
                    "boundary_id": self._boundary_id,
                    "sealed": True,
                    "owner_token_sha256": owner_sha256,
                    "lifecycle_generation": (
                        self._runtime_guard_lifecycle_generation
                    ),
                    "sink_lifecycle_generation": sink_generation,
                    "durable_sink_configured": sink is not None,
                    "durable_ledger_id": ledger_id,
                    "close_rejected_while_sealed": sink is not None,
                    "terminal": False,
                    "production_ready": False,
                }
            assert_public_summary_safe(result)
            return result

    def validate_runtime_guard_seal(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> dict[str, Any]:
        """Revalidate the exact irreversible sink pin under the lifecycle lock."""

        token = _bounded_text(
            owner_token,
            field_name="runtime_guard_owner_token",
            maximum_bytes=128,
        )
        owner_sha256 = sha256_hex(token.encode("utf-8", errors="strict"))
        if type(lifecycle_generation) is not int or lifecycle_generation < 1:
            raise OSProtectionError("runtime_guard_lifecycle_generation_invalid")
        with self._runtime_guard_lifecycle_lock:
            with self._lock:
                if (
                    not self._runtime_guard_sealed
                    or not secrets.compare_digest(
                        owner_sha256,
                        self._runtime_guard_owner_token_sha256 or "",
                    )
                    or lifecycle_generation
                    != self._runtime_guard_lifecycle_generation
                    or self._durable_evidence_terminal
                ):
                    raise OSProtectionError("runtime_guard_lifecycle_invalid")
                sink = self._quarantine_evidence_sink
                sink_generation = self._runtime_guard_sink_generation
            try:
                if sink is not None:
                    validate = getattr(
                        sink,
                        "validate_runtime_guard_seal",
                        None,
                    )
                    if not callable(validate) or sink_generation is None:
                        raise OSProtectionError(
                            "runtime_guard_sink_seal_unsupported"
                        )
                    state = self._validated_runtime_guard_sink_seal(
                        validate(token, sink_generation),
                        owner_token_sha256=owner_sha256,
                        expected_generation=sink_generation,
                    )
                    with self._lock:
                        self._join_durable_sink_state(
                            {
                                "ledger_id": state["ledger_id"],
                                "ledger_instance_commitment": state[
                                    "ledger_instance_commitment"
                                ],
                                "entry_count": state["entry_count"],
                                "violation_count": state["violation_count"],
                                "persisted": state["violation_count"] > 0,
                            }
                        )
                result = {
                    "schema": OS_RUNTIME_GUARD_LIFECYCLE_SCHEMA,
                    "boundary_id": self._boundary_id,
                    "sealed": True,
                    "owner_token_sha256": owner_sha256,
                    "lifecycle_generation": lifecycle_generation,
                    "sink_lifecycle_generation": sink_generation,
                    "durable_sink_configured": sink is not None,
                    "close_rejected_while_sealed": sink is not None,
                    "terminal": False,
                    "production_ready": False,
                }
                assert_public_summary_safe(result)
                return result
            except BaseException as exc:
                with self._lock:
                    failure_code = (
                        exc.code
                        if isinstance(exc, OSProtectionError)
                        else "runtime_guard_sink_seal_validation_failed"
                    )
                    self._mark_durable_evidence_terminal_locked(failure_code)
                raise OSProtectionError(
                    "runtime_guard_sink_seal_validation_failed"
                ) from exc

    @contextmanager
    def runtime_guard_lifecycle_lease(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> Iterator[dict[str, Any]]:
        """Hold one non-mutating lifecycle decision stable; never append inside."""

        with self._runtime_guard_lifecycle_lock:
            before = self.validate_runtime_guard_seal(
                owner_token,
                lifecycle_generation,
            )
            with self._lock:
                sink = self._quarantine_evidence_sink
                sink_generation = self._runtime_guard_sink_generation
            if sink is None:
                yield before
                self.validate_runtime_guard_seal(
                    owner_token,
                    lifecycle_generation,
                )
                return
            lease = getattr(sink, "runtime_guard_lifecycle_lease", None)
            if not callable(lease) or sink_generation is None:
                with self._lock:
                    self._mark_durable_evidence_terminal_locked(
                        "runtime_guard_sink_lease_unsupported"
                    )
                raise OSProtectionError("runtime_guard_sink_lease_unsupported")
            body_failed = False
            try:
                with lease(owner_token, sink_generation) as raw:
                    self._validated_runtime_guard_sink_seal(
                        raw,
                        owner_token_sha256=sha256_hex(
                            owner_token.encode("utf-8", errors="strict")
                        ),
                        expected_generation=sink_generation,
                    )
                    try:
                        yield before
                    except BaseException:
                        body_failed = True
                        raise
                    # The sink context performs its own post-body validation
                    # inside the still-open SQLite transaction.  Re-entering
                    # its public validate method here would attempt a nested
                    # BEGIN IMMEDIATE on the same pre-opened connection.
                    with self._lock:
                        if (
                            not self._runtime_guard_sealed
                            or lifecycle_generation
                            != self._runtime_guard_lifecycle_generation
                            or self._durable_evidence_terminal
                        ):
                            raise OSProtectionError(
                                "runtime_guard_lifecycle_invalid"
                            )
            except BaseException as exc:
                if body_failed or isinstance(
                    exc,
                    (GeneratorExit, KeyboardInterrupt, SystemExit),
                ):
                    raise
                # Sink/validation exceptions make the boundary terminal before
                # propagating.  Body exceptions above retain their own stable
                # type and code.
                with self._lock:
                    failure_code = (
                        exc.code
                        if isinstance(exc, OSProtectionError)
                        else "runtime_guard_sink_lease_failed"
                    )
                    self._mark_durable_evidence_terminal_locked(
                        failure_code
                    )
                if isinstance(exc, OSProtectionError):
                    raise
                raise OSProtectionError("runtime_guard_sink_lease_failed") from exc

    def _persist_quarantine_evidence(
        self,
        *,
        outcome: QuarantinedHNC,
        evidence_packet: Mapping[str, Any],
    ) -> None:
        binding = outcome.hnc_evidence_binding
        if binding is None:
            raise OSProtectionError("durable_quarantine_hnc_evidence_required")
        metadata = {
            "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
            "intrusion_id": outcome.admission_id,
            "content_sha256": outcome.content_sha256,
            "source_id_sha256": sha256_hex(outcome.source_id.encode("utf-8")),
            "ingress_kind_sha256": sha256_hex(outcome.ingress_kind.encode("utf-8")),
            "denial_code_count": len(outcome.denial_codes),
            "raw_arguments_retained": False,
            "plaintext_retained": False,
            "action_eligible": False,
            "economic_eligible": False,
            "production_ready": False,
        }
        try:
            with self._lock:
                sink = self._quarantine_evidence_sink
                if sink is None:
                    return
                if self._durable_evidence_terminal:
                    raise OSProtectionError("durable_quarantine_evidence_terminal")
                before = self._validated_durable_sink_state(sink.preflight())
                self._join_durable_sink_state(before)
                if before["ready"] is not True:
                    raise OSProtectionError("durable_quarantine_evidence_not_ready")
                expected_sequence = int(before["entry_count"]) + 1
                expected_violation_count = int(before["violation_count"]) + 1
                receipt = sink.append_violation(
                    intrusion_id=outcome.admission_id,
                    runtime_metadata=metadata,
                    quarantine_summary=outcome.public_summary(),
                    hnc_packet=evidence_packet,
                )
                if not isinstance(receipt, Mapping):
                    raise OSProtectionError(
                        "durable_quarantine_evidence_readback_invalid"
                    )
                sequence = receipt.get("sequence")
                terminal_after_append = receipt.get("terminal_after_append")
                previous_entry_commitment = require_sha256(
                    receipt.get("previous_entry_commitment"),
                    field="durable_quarantine_previous_entry_commitment",
                )
                entry_commitment = require_sha256(
                    receipt.get("entry_commitment"),
                    field="durable_quarantine_entry_commitment",
                )
                if (
                    type(sequence) is not int
                    or sequence != expected_sequence
                    or type(terminal_after_append) is not bool
                    or receipt.get("ledger_id") != before["ledger_id"]
                    or receipt.get("ledger_instance_commitment")
                    != before["ledger_instance_commitment"]
                    or receipt.get("intrusion_id") != outcome.admission_id
                    or receipt.get("quarantine_commitment")
                    != outcome.quarantine_commitment
                    or receipt.get("quarantine_record_commitment")
                    != outcome.quarantine_record.record_commitment
                    or receipt.get("hnc_packet_commitment")
                    != binding.hnc_packet_commitment
                    or receipt.get("hnc_binding_commitment")
                    != binding.binding_commitment
                    or receipt.get("durability_readback") is not True
                    or receipt.get("encrypted_hnc_packet_persisted") is not True
                    or (
                        self._durable_evidence_last_receipt_sequence is not None
                        and (
                            sequence
                            != self._durable_evidence_last_receipt_sequence + 1
                            or previous_entry_commitment
                            != self._durable_evidence_head_commitment
                        )
                    )
                ):
                    raise OSProtectionError(
                        "durable_quarantine_evidence_readback_invalid"
                    )
                after = self._validated_durable_sink_state(sink.preflight())
                expected_entry_count = expected_sequence + int(terminal_after_append)
                if (
                    after["ledger_id"] != before["ledger_id"]
                    or after["ledger_instance_commitment"]
                    != before["ledger_instance_commitment"]
                    or after["entry_count"] != expected_entry_count
                    or after["violation_count"] != expected_violation_count
                    or after["remaining"] != max(0, int(before["remaining"]) - 1)
                    or after["persisted"] is not True
                    or (terminal_after_append and after["ready"] is not False)
                    or (not terminal_after_append and after["ready"] is not True)
                ):
                    raise OSProtectionError(
                        "durable_quarantine_evidence_post_append_join_invalid"
                    )
                self._durable_evidence_entry_count = expected_entry_count
                self._durable_evidence_violation_count = expected_violation_count
                self._durable_evidence_packets_persisted = True
                self._durable_evidence_count += 1
                self._durable_evidence_head_commitment = entry_commitment
                self._durable_evidence_last_receipt_sequence = sequence
                if terminal_after_append:
                    self._mark_durable_evidence_terminal_locked(
                        "runtime_intrusion_ledger_capacity_exhausted"
                    )
        except BaseException as exc:
            with self._lock:
                failure_code = (
                    exc.code
                    if isinstance(exc, OSProtectionError)
                    else "durable_quarantine_evidence_append_failed"
                )
                self._mark_durable_evidence_terminal_locked(failure_code)
            raise OSProtectionError("durable_quarantine_evidence_append_failed") from exc

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

    def key_preflight(self) -> dict[str, Any]:
        """Verify key availability without returning key material or granting admission.

        This preflight is intentionally metadata-only.  Callers that will process
        sensitive plaintext use it to fail before model inference; admission still
        performs its own independent key validation to avoid treating this receipt
        as an authorization token.
        """

        material, error = self._key_material()
        ready = material is not None and error is None
        if material is not None:
            # Best-effort destruction of the temporary normalized copy.  The key
            # provider and Python runtime may retain other copies, so no stronger
            # memory-erasure claim is made.
            scratch = bytearray(material)
            for index in range(len(scratch)):
                scratch[index] = 0
            del scratch
            del material
        return {
            "schema": OS_KEY_PREFLIGHT_SCHEMA,
            "boundary_id": self._boundary_id,
            "ready": ready,
            "reason_code": "ready" if ready else str(error or "master_key_unavailable"),
            "key_material_returned": False,
            "admission_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
            "local_development_only": True,
            "production_ready": False,
        }

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
        """Admit only if its starting lifecycle generation remains current."""

        lifecycle_generation = self._lifecycle_operation_generation()
        return self._admit_external_under_lifecycle(
            raw,
            source_id=source_id,
            ingress_kind=ingress_kind,
            purpose=purpose,
            operator_aad=operator_aad,
            content_validator=content_validator,
            lifecycle_generation=lifecycle_generation,
        )

    def _admit_external_under_lifecycle(
        self,
        raw: bytes | bytearray | memoryview,
        *,
        source_id: str,
        ingress_kind: str,
        purpose: str,
        operator_aad: Mapping[str, Any] | None = None,
        content_validator: ContentValidator | None = None,
        lifecycle_generation: int,
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
        with self._lock:
            ledger_instance_commitment = (
                self._durable_evidence_ledger_instance_commitment
            )
            durable_sink_configured = self._quarantine_evidence_sink is not None
        if durable_sink_configured and ledger_instance_commitment is None:
            raise OSProtectionError(
                "durable_quarantine_ledger_instance_unavailable"
            )
        if ledger_instance_commitment is not None:
            ingress_aad["ledger_instance_commitment"] = ledger_instance_commitment
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
                validate_magic_star_inner_carrier_capacity_v02(
                    packet_id=admission_id,
                    purpose=bounded_purpose,
                    legacy_carrier=packet,
                    legacy_master_key=key_material,
                )
            except StarCustodyError as exc:
                denial_codes.add(
                    "magic_star_inner_capacity_exceeded"
                    if exc.code == "inner_carrier_too_large"
                    else "magic_star_inner_preflight_failed"
                )
            except BaseException:
                denial_codes.add("hnc_packet_seal_failed")
            else:
                handle = OpaqueHNCHandle.issue(
                    boundary_id=self._boundary_id,
                    handle_id=admission_id,
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
                outcome = AdmittedHNC(
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
                # This is the admission linearization point.  A terminal or
                # seal transition completed while the caller validator/crypto
                # work was in flight invalidates the result before custody is
                # stored or an opaque handle can escape.
                stored_record: _AdmissionRecord | None = None
                try:
                    with self._lifecycle_commit_lease(
                        lifecycle_generation
                    ), self._lock:
                        capacity_available = (
                            len(self._records) < self._max_active_handles
                            and self._active_ingress_bytes + content_size
                            <= self._max_active_ingress_bytes
                        )
                        if capacity_available:
                            stored_record = _AdmissionRecord(
                                packet=dict(packet),
                                master_key=bytearray(key_material),
                                purpose=bounded_purpose,
                                handle_commitment=handle.handle_commitment,
                                content_size_bytes=content_size,
                            )
                            self._records[admission_id] = stored_record
                            self._active_ingress_bytes += content_size
                        else:
                            denial_codes.add(
                                "active_admission_capacity_exhausted"
                            )
                except BaseException:
                    if stored_record is not None:
                        with self._lock:
                            if self._records.get(admission_id) is stored_record:
                                self._records.pop(admission_id, None)
                                self._active_ingress_bytes = max(
                                    0,
                                    self._active_ingress_bytes - content_size,
                                )
                        stored_record.master_key[:] = bytes(
                            len(stored_record.master_key)
                        )
                    raise
                if capacity_available:
                    return outcome
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
        evidence_packet: dict[str, Any] | None = None
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
                        evidence_packet = None
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
        outcome = QuarantinedHNC(
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
        if evidence_packet is not None:
            self._persist_quarantine_evidence(
                outcome=outcome,
                evidence_packet=evidence_packet,
            )
        return outcome

    def protect_for_magic_star(
        self,
        handle: OpaqueHNCHandle,
        *,
        custody: LocalDevelopmentStarCustodyV02,
        release_context_sha256: str,
    ) -> ProtectedMagicStarPacketV02:
        """Reject custody results invalidated by a terminal transition."""

        lifecycle_generation = self._lifecycle_operation_generation()
        return self._protect_for_magic_star_under_lifecycle(
            handle,
            custody=custody,
            release_context_sha256=release_context_sha256,
            lifecycle_generation=lifecycle_generation,
        )

    def _protect_for_magic_star_under_lifecycle(
        self,
        handle: OpaqueHNCHandle,
        *,
        custody: LocalDevelopmentStarCustodyV02,
        release_context_sha256: str,
        lifecycle_generation: int,
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
        with self._lifecycle_commit_lease(lifecycle_generation):
            pass
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
        """Linearly order destruction of a held admission with lifecycle state."""

        with self._runtime_guard_lifecycle_lock:
            return self._discard_admitted_under_lifecycle(
                handle,
                reason_code=reason_code,
            )

    def _discard_admitted_under_lifecycle(
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
        with self._runtime_guard_lifecycle_lock, self._lock:
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
                "durable_quarantine_evidence_configured": (
                    self._quarantine_evidence_sink is not None
                ),
                "durable_quarantine_evidence_count": self._durable_evidence_count,
                "durable_quarantine_evidence_head_commitment": (
                    self._durable_evidence_head_commitment
                ),
                "durable_quarantine_evidence_last_receipt_sequence": (
                    self._durable_evidence_last_receipt_sequence
                ),
                "durable_quarantine_evidence_ledger_entry_count": (
                    self._durable_evidence_entry_count
                ),
                "durable_quarantine_evidence_ledger_violation_count": (
                    self._durable_evidence_violation_count
                ),
                "durable_quarantine_evidence_packets_persisted": (
                    self._durable_evidence_packets_persisted
                ),
                "durable_quarantine_evidence_terminal": (
                    self._durable_evidence_terminal
                ),
                "durable_quarantine_evidence_failure_code": (
                    self._durable_evidence_failure_code
                ),
                "runtime_guard_lifecycle_sealed": self._runtime_guard_sealed,
                "runtime_guard_lifecycle_generation": (
                    self._runtime_guard_lifecycle_generation
                ),
                "runtime_guard_sink_generation": (
                    self._runtime_guard_sink_generation
                ),
                "external_head_anchor_attested": False,
                "magic_star_durable_custody_attested": False,
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
    "OS_KEY_PREFLIGHT_SCHEMA",
    "OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA",
    "OS_PROTECTION_SCHEMA",
    "OS_QUARANTINE_EVIDENCE_PURPOSE",
    "OS_QUARANTINE_EVIDENCE_SCHEMA",
    "OS_RUNTIME_GUARD_LIFECYCLE_SCHEMA",
    "AdmissionOutcome",
    "AdmittedHNC",
    "ContentValidator",
    "IngressDisposition",
    "LocalOSProtectionBoundary",
    "MasterKeyProvider",
    "OSProtectionError",
    "OpaqueHNCHandle",
    "QuarantinedHNC",
    "QuarantineEvidenceSink",
]
