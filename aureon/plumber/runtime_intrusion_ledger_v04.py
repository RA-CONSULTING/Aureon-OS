"""Pre-opened, append-only SQLite ledger for encrypted HNC intrusion evidence.

The connection is constructed and fully validated before a runtime audit guard
is installed, then retained for the lifetime of the recorder.  Appends use the
same connection, a bounded Python lock, ``BEGIN IMMEDIATE``, SQLite ``FULL``
synchronous durability, exact post-commit read-back, and an INSERT-only hash
chain.  The ledger never stores raw audit arguments or plaintext application
content; it stores the already encrypted HNC quarantine packet plus bounded
commitment metadata.

This remains a local reference, not WORM storage or an external trust anchor.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Iterator, cast

from aureon.harmonic.hnc_quantum_packet_crypto import (
    HNCPacketError,
    decode_hnc_quantum_packet,
    normalize_hnc_key_material,
)
from aureon.harmonic.hnc_quantum_packet_crypto import (
    canonical_json_bytes as canonical_hnc_json_bytes,
)

from .audit import assert_public_summary_safe
from .crypto import canonical_json_bytes, decode_canonical_json, domain_hash
from .os_protection import (
    OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
    OS_INGRESS_AAD_SCHEMA,
    OS_PROTECTION_SCHEMA,
    OS_QUARANTINE_EVIDENCE_PURPOSE,
    OS_QUARANTINE_EVIDENCE_SCHEMA,
    IngressDisposition,
    QuarantinedHNC,
)
from .packet import HNCPayloadBindingV0, bind_hnc_packet
from .quarantine import QuarantineRecord
from .schema import format_timestamp, parse_timestamp, require_sha256

RUNTIME_INTRUSION_LEDGER_SCHEMA: Final = "aureon.plumber.runtime-intrusion-ledger.v04"
RUNTIME_INTRUSION_ENTRY_SCHEMA: Final = "aureon.plumber.runtime-intrusion-entry.v04"
RUNTIME_INTRUSION_AUTHENTICATED_PROJECTION_SCHEMA: Final = (
    "aureon.plumber.runtime-intrusion-authenticated-projection.v04"
)
_ZERO_SHA256: Final = "0" * 64
_LEDGER_ID_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_MAX_VIOLATION_ENTRIES: Final = 65_536
_MAX_AUTHENTICATED_PROJECTION_BATCH: Final = 64
_MAX_ENTRY_BYTES: Final = 32 * 1024 * 1024
_MAX_APPEND_TIMEOUT_MS: Final = 30_000
_LEDGER_AUTH_KEY_SCHEMA: Final = "aureon.plumber.runtime-intrusion-ledger-auth-key.v04"
_LEDGER_INSTANCE_COMMITMENT_SCHEMA: Final = (
    "aureon.plumber.runtime-intrusion-ledger-instance.v04"
)
_LEDGER_GENESIS_HMAC_SCHEMA: Final = (
    "aureon.plumber.runtime-intrusion-ledger-genesis-hmac.v04"
)
_LEDGER_ENTRY_HMAC_SCHEMA: Final = "aureon.plumber.runtime-intrusion-entry-hmac.v04"
_RUNTIME_SOURCE_ID: Final = "aureon:runtime-guard-v04"
_RUNTIME_INTRUSION_PURPOSE: Final = (
    "aureon.plumber.runtime-intrusion-quarantine.v04"
)
_RUNTIME_PREFLIGHT_INGRESS_KIND: Final = "runtime-guard-preflight"
_RUNTIME_VIOLATION_INGRESS_KIND: Final = "runtime-effect-violation"
_RUNTIME_GUARD_PREFLIGHT_SCHEMA: Final = "aureon.plumber.runtime-guard-preflight.v04"
_RUNTIME_INTRUSION_SCHEMA: Final = "aureon.plumber.runtime-intrusion.v04"
_MAX_RUNTIME_RECORDER_SEQUENCE: Final = 4096
_RUNTIME_VIOLATION_REASON_CODE: Final = (
    "runtime_effect_not_magic_star_released"
)
_RUNTIME_AUDIT_EVENT_RE: Final = re.compile(
    r"^[A-Za-z0-9_][A-Za-z0-9._:/-]{0,127}$"
)
_RUNTIME_REASON_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

_QUARANTINE_EVIDENCE_KEYS: Final = frozenset(
    {
        "schema",
        "admission_id",
        "boundary_id",
        "source_id",
        "ingress_kind",
        "content_sha256",
        "content_size_bytes",
        "purpose_commitment",
        "operator_aad_sha256",
        "replay_token",
        "denial_codes",
        "raw_material_retained",
        "source_truth_established_by_local_wrapping",
    }
)

_QUARANTINE_AAD_KEYS: Final = frozenset(
    {
        "schema",
        "ledger_instance_commitment",
        "boundary_id",
        "source_id",
        "ingress_kind",
        "content_sha256",
        "content_size_bytes",
        "purpose",
        "purpose_commitment",
        "caller_aad",
        "source_truth_established_by_local_wrapping",
        "quarantine",
        "quarantine_evidence_schema",
        "denial_codes",
    }
)

_INGRESS_AAD_KEYS: Final = _QUARANTINE_AAD_KEYS - {
    "quarantine",
    "quarantine_evidence_schema",
    "denial_codes",
}

_QUARANTINE_SUMMARY_KEYS: Final = frozenset(
    {
        "schema",
        "disposition",
        "boundary_id",
        "admission_id",
        "source_id",
        "ingress_kind",
        "content_sha256",
        "content_size_bytes",
        "purpose_commitment",
        "operator_aad_sha256",
        "replay_token",
        "recorded_at",
        "local_development_only",
        "production_ready",
        "denial_codes",
        "quarantine_record",
        "hnc_evidence_binding",
        "raw_material_retained",
        "quarantine_commitment",
    }
)

_OS_RUNTIME_METADATA_KEYS: Final = frozenset(
    {
        "schema",
        "intrusion_id",
        "content_sha256",
        "source_id_sha256",
        "ingress_kind_sha256",
        "denial_code_count",
        "raw_arguments_retained",
        "plaintext_retained",
        "action_eligible",
        "economic_eligible",
        "production_ready",
    }
)

class RuntimeIntrusionLedgerError(RuntimeError):
    """Stable, non-secret durable intrusion-ledger failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


_METADATA_TABLE_SQL: Final = """
CREATE TABLE runtime_intrusion_metadata_v04 (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    schema TEXT NOT NULL,
    ledger_id TEXT NOT NULL,
    ledger_instance_commitment TEXT NOT NULL,
    max_violation_entries INTEGER NOT NULL,
    max_entry_bytes INTEGER NOT NULL,
    append_timeout_ms INTEGER NOT NULL,
    metadata_commitment TEXT NOT NULL,
    genesis_hmac_sha256 TEXT NOT NULL
) STRICT
""".strip()

_ENTRY_TABLE_SQL: Final = """
CREATE TABLE runtime_intrusion_entries_v04 (
    sequence INTEGER PRIMARY KEY,
    entry_kind TEXT NOT NULL CHECK(entry_kind IN ('PREFLIGHT','VIOLATION','TERMINAL')),
    intrusion_id TEXT NOT NULL UNIQUE,
    previous_entry_commitment TEXT NOT NULL,
    previous_entry_hmac_sha256 TEXT NOT NULL,
    runtime_metadata_json BLOB NOT NULL,
    runtime_metadata_sha256 TEXT NOT NULL,
    quarantine_summary_json BLOB NOT NULL,
    quarantine_commitment TEXT NOT NULL,
    quarantine_record_commitment TEXT NOT NULL,
    hnc_packet_json BLOB NOT NULL,
    hnc_packet_sha256 TEXT NOT NULL,
    hnc_packet_commitment TEXT NOT NULL,
    hnc_binding_commitment TEXT NOT NULL,
    terminal_after_append INTEGER NOT NULL CHECK(terminal_after_append IN (0,1)),
    recorded_at TEXT NOT NULL,
    entry_commitment TEXT NOT NULL UNIQUE,
    entry_hmac_sha256 TEXT NOT NULL
) STRICT
""".strip()

_ENTRY_COMMITMENT_INDEX_SQL: Final = (
    "CREATE UNIQUE INDEX runtime_intrusion_entries_v04_commitment_uq "
    "ON runtime_intrusion_entries_v04(entry_commitment)"
)

_NO_UPDATE_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_entries_v04_no_update
BEFORE UPDATE ON runtime_intrusion_entries_v04
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
END
""".strip()

_NO_DELETE_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_entries_v04_no_delete
BEFORE DELETE ON runtime_intrusion_entries_v04
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
END
""".strip()

_CONTIGUOUS_SEQUENCE_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_entries_v04_contiguous_sequence
BEFORE INSERT ON runtime_intrusion_entries_v04
WHEN NEW.sequence != COALESCE((SELECT MAX(sequence) + 1 FROM runtime_intrusion_entries_v04), 1)
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_sequence_gap');
END
""".strip()

_PREVIOUS_COMMITMENT_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_entries_v04_previous_commitment
BEFORE INSERT ON runtime_intrusion_entries_v04
WHEN NEW.previous_entry_commitment != COALESCE(
    (SELECT entry_commitment FROM runtime_intrusion_entries_v04 ORDER BY sequence DESC LIMIT 1),
    '0000000000000000000000000000000000000000000000000000000000000000'
)
OR NEW.previous_entry_hmac_sha256 != COALESCE(
    (SELECT entry_hmac_sha256 FROM runtime_intrusion_entries_v04 ORDER BY sequence DESC LIMIT 1),
    (SELECT genesis_hmac_sha256 FROM runtime_intrusion_metadata_v04 WHERE singleton = 1)
)
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_chain_mismatch');
END
""".strip()

_NO_INSERT_AFTER_TERMINAL_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_entries_v04_no_insert_after_terminal
BEFORE INSERT ON runtime_intrusion_entries_v04
WHEN EXISTS(SELECT 1 FROM runtime_intrusion_entries_v04 WHERE terminal_after_append = 1)
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_ledger_terminal');
END
""".strip()

_METADATA_NO_UPDATE_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_metadata_v04_no_update
BEFORE UPDATE ON runtime_intrusion_metadata_v04
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_metadata_immutable');
END
""".strip()

_METADATA_NO_DELETE_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_metadata_v04_no_delete
BEFORE DELETE ON runtime_intrusion_metadata_v04
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_metadata_immutable');
END
""".strip()

_METADATA_SINGLE_INSERT_TRIGGER_SQL: Final = """
CREATE TRIGGER runtime_intrusion_metadata_v04_single_insert
BEFORE INSERT ON runtime_intrusion_metadata_v04
WHEN EXISTS(SELECT 1 FROM runtime_intrusion_metadata_v04)
BEGIN
    SELECT RAISE(ABORT, 'runtime_intrusion_metadata_immutable');
END
""".strip()

_TRIGGER_SQL: Final = {
    "runtime_intrusion_entries_v04_no_update": _NO_UPDATE_TRIGGER_SQL,
    "runtime_intrusion_entries_v04_no_delete": _NO_DELETE_TRIGGER_SQL,
    "runtime_intrusion_entries_v04_contiguous_sequence": _CONTIGUOUS_SEQUENCE_TRIGGER_SQL,
    "runtime_intrusion_entries_v04_previous_commitment": _PREVIOUS_COMMITMENT_TRIGGER_SQL,
    "runtime_intrusion_entries_v04_no_insert_after_terminal": _NO_INSERT_AFTER_TERMINAL_TRIGGER_SQL,
    "runtime_intrusion_metadata_v04_no_update": _METADATA_NO_UPDATE_TRIGGER_SQL,
    "runtime_intrusion_metadata_v04_no_delete": _METADATA_NO_DELETE_TRIGGER_SQL,
    "runtime_intrusion_metadata_v04_single_insert": _METADATA_SINGLE_INSERT_TRIGGER_SQL,
}

_ROW_COLUMNS: Final = (
    "sequence, entry_kind, intrusion_id, previous_entry_commitment, "
    "previous_entry_hmac_sha256, runtime_metadata_json, runtime_metadata_sha256, "
    "quarantine_summary_json, "
    "quarantine_commitment, quarantine_record_commitment, hnc_packet_json, "
    "hnc_packet_sha256, hnc_packet_commitment, hnc_binding_commitment, "
    "terminal_after_append, recorded_at, entry_commitment, entry_hmac_sha256"
)

_EXPECTED_INTERNAL_SCHEMA_OBJECTS: Final = {
    (
        "index",
        "sqlite_autoindex_runtime_intrusion_entries_v04_1",
        "runtime_intrusion_entries_v04",
        None,
    ),
    (
        "index",
        "sqlite_autoindex_runtime_intrusion_entries_v04_2",
        "runtime_intrusion_entries_v04",
        None,
    ),
}


def _normalized_sql(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _identifier(value: object, code: str) -> str:
    if type(value) is not str or _LEDGER_ID_RE.fullmatch(value) is None:
        raise RuntimeIntrusionLedgerError(code)
    return value


def _count(value: object, *, code: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise RuntimeIntrusionLedgerError(code)
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _blob(value: object, *, code: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    raise RuntimeIntrusionLedgerError(code)


def _mapping_bytes(value: Mapping[str, Any], *, code: str) -> bytes:
    if not isinstance(value, Mapping):
        raise RuntimeIntrusionLedgerError(code)
    try:
        return cast(bytes, canonical_json_bytes(value))
    except (TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc


def _decode_mapping(value: object, *, code: str) -> dict[str, Any]:
    raw = _blob(value, code=code)
    try:
        decoded = decode_canonical_json(raw, max_bytes=_MAX_ENTRY_BYTES)
    except (TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc
    if not isinstance(decoded, dict):
        raise RuntimeIntrusionLedgerError(code)
    if canonical_json_bytes(decoded) != raw:
        raise RuntimeIntrusionLedgerError(code)
    return decoded


def _hnc_mapping_bytes(value: Mapping[str, Any], *, code: str) -> bytes:
    if not isinstance(value, Mapping):
        raise RuntimeIntrusionLedgerError(code)
    try:
        return cast(
            bytes,
            canonical_hnc_json_bytes(value, max_bytes=_MAX_ENTRY_BYTES),
        )
    except (HNCPacketError, TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc


def _decode_hnc_mapping(value: object, *, code: str) -> dict[str, Any]:
    raw = _blob(value, code=code)

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        decoded: dict[str, Any] = {}
        for key, item in pairs:
            if key in decoded:
                raise RuntimeIntrusionLedgerError(code)
            decoded[key] = item
        return decoded

    def reject_constant(_value: str) -> Any:
        raise RuntimeIntrusionLedgerError(code)

    try:
        decoded = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except RuntimeIntrusionLedgerError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc
    if not isinstance(decoded, dict):
        raise RuntimeIntrusionLedgerError(code)
    try:
        canonical = canonical_hnc_json_bytes(decoded, max_bytes=_MAX_ENTRY_BYTES)
    except (HNCPacketError, TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc
    if canonical != raw:
        raise RuntimeIntrusionLedgerError(code)
    return decoded


def _require_sha256(value: object, *, code: str, field: str) -> str:
    try:
        return cast(str, require_sha256(value, field=field))
    except (TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc


def _assert_safe_mapping(value: Mapping[str, Any], *, code: str) -> None:
    try:
        assert_public_summary_safe(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc


def _stable_error(exc: BaseException, *, fallback: str) -> RuntimeIntrusionLedgerError:
    if isinstance(exc, RuntimeIntrusionLedgerError):
        return exc
    return RuntimeIntrusionLedgerError(fallback)


def _authenticated_projection_from_entry(
    entry: Mapping[str, Any] | None,
    *,
    selected_sequence: int,
    selected_commitment: str,
    ledger_id: str,
    ledger_instance_commitment: str,
) -> dict[str, Any]:
    """Project one already authenticated ledger row without rescanning SQLite."""

    if entry is None or entry.get("entry_commitment") != selected_commitment:
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_projection_entry_join_invalid"
        )
    violation = entry.get("authenticated_runtime_violation")
    if (
        entry.get("entry_kind") != "VIOLATION"
        or not isinstance(violation, Mapping)
        or set(violation)
        != {"event_name", "resource_commitment", "reason_code"}
    ):
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_projection_runtime_violation_required"
        )

    # The row validator authenticated these values from the encrypted HNC
    # packet's caller AAD.  Recheck the exact public route at projection time.
    from .runtime_guard_v04 import _SUPPORTED_RULE_EVENTS

    event_name = violation.get("event_name")
    reason_code = violation.get("reason_code")
    resource_commitment = violation.get("resource_commitment")
    if (
        type(event_name) is not str
        or event_name not in _SUPPORTED_RULE_EVENTS
        or type(reason_code) is not str
        or reason_code != _RUNTIME_VIOLATION_REASON_CODE
        or type(resource_commitment) is not str
        or _require_sha256(
            resource_commitment,
            code="runtime_intrusion_projection_route_invalid",
            field="resource_commitment",
        )
        != resource_commitment
    ):
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_projection_route_invalid"
        )
    runtime_metadata = entry.get("runtime_metadata")
    if not isinstance(runtime_metadata, Mapping):  # pragma: no cover - validated above
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_projection_metadata_invalid"
        )
    content_sha256 = _require_sha256(
        runtime_metadata.get("content_sha256"),
        code="runtime_intrusion_projection_metadata_invalid",
        field="content_sha256",
    )
    intrusion_id = str(entry["intrusion_id"])
    core = {
        "schema": RUNTIME_INTRUSION_AUTHENTICATED_PROJECTION_SCHEMA,
        "ledger_schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
        "ledger_id": ledger_id,
        "ledger_instance_commitment": ledger_instance_commitment,
        "ledger_sequence": selected_sequence,
        "ledger_authenticated_prefix_entry_count": selected_sequence,
        "ledger_authenticated_prefix_head_commitment": selected_commitment,
        "entry_commitment": selected_commitment,
        "previous_entry_commitment": entry["previous_entry_commitment"],
        "runtime_metadata_sha256": entry["runtime_metadata_sha256"],
        "runtime_content_sha256": content_sha256,
        "hnc_packet_commitment": entry["hnc_packet_commitment"],
        "hnc_binding_commitment": entry["hnc_binding_commitment"],
        "quarantine_commitment": entry["quarantine_commitment"],
        "quarantine_record_commitment": entry[
            "quarantine_record_commitment"
        ],
        "intrusion_id_commitment": domain_hash(
            "aureon.plumber.runtime-intrusion-id-projection.v04",
            {
                "ledger_id": ledger_id,
                "ledger_instance_commitment": ledger_instance_commitment,
                "intrusion_id": intrusion_id,
            },
        ),
        "event_name": event_name,
        "reason_code": reason_code,
        "keyed_chain_authenticated": True,
        "hnc_packet_authenticated": True,
        "exact_runtime_route_authenticated": True,
        "raw_intrusion_id_returned": False,
        "raw_resource_commitment_returned": False,
        "authentication_tag_returned": False,
        "raw_arguments_retained": False,
        "external_head_anchor_attested": False,
        "magic_star_durable_custody_attested": False,
        "production_ready": False,
    }
    result = {
        **core,
        "projection_commitment": domain_hash(
            "aureon.plumber.runtime-intrusion-authenticated-projection.v04",
            core,
        ),
    }
    assert_public_summary_safe(result)
    return result


_EXACT_AUTHENTICATED_PROJECTION_GATE: Final = (
    _authenticated_projection_from_entry
)
_EXACT_AUTHENTICATED_PROJECTION_GATE_CODE: Final = (
    _EXACT_AUTHENTICATED_PROJECTION_GATE.__code__
)


def _metadata_payload(
    *,
    ledger_id: str,
    ledger_instance_commitment: str,
    max_violation_entries: int,
    max_entry_bytes: int,
    append_timeout_ms: int,
) -> dict[str, Any]:
    return {
        "schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
        "ledger_id": ledger_id,
        "ledger_instance_commitment": ledger_instance_commitment,
        "max_violation_entries": max_violation_entries,
        "max_entry_bytes": max_entry_bytes,
        "append_timeout_ms": append_timeout_ms,
    }


def _entry_commitment(payload: Mapping[str, Any]) -> str:
    return cast(
        str,
        domain_hash("aureon.plumber.runtime-intrusion-entry.v04", payload),
    )


def _derive_ledger_auth_key(
    quarantine_hnc_key: bytearray,
    *,
    ledger_id: str,
    ledger_instance_commitment: str,
) -> bytearray:
    context = canonical_json_bytes(
        {
            "schema": _LEDGER_AUTH_KEY_SCHEMA,
            "ledger_id": ledger_id,
            "ledger_instance_commitment": ledger_instance_commitment,
        }
    )
    return bytearray(
        hmac.new(bytes(quarantine_hnc_key), context, hashlib.sha256).digest()
    )


def _genesis_hmac(
    ledger_auth_key: bytearray,
    *,
    metadata: Mapping[str, Any],
    metadata_commitment: str,
) -> str:
    message = canonical_json_bytes(
        {
            "schema": _LEDGER_GENESIS_HMAC_SCHEMA,
            "metadata": dict(metadata),
            "metadata_commitment": metadata_commitment,
        }
    )
    return hmac.new(bytes(ledger_auth_key), message, hashlib.sha256).hexdigest()


def _hmac_frame(value: object) -> bytes:
    if type(value) is int:
        kind = b"integer"
        encoded = str(value).encode("ascii")
    elif type(value) is str:
        kind = b"text"
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_entry_authentication_invalid"
            ) from exc
    elif isinstance(value, (bytes, bytearray, memoryview)):
        kind = b"blob"
        encoded = bytes(value)
    else:
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_entry_authentication_invalid"
        )
    return (
        len(kind).to_bytes(2, "big")
        + kind
        + len(encoded).to_bytes(8, "big")
        + encoded
    )


def _entry_hmac(
    ledger_auth_key: bytearray,
    *,
    ledger_id: str,
    authenticated_fields: tuple[Any, ...],
) -> str:
    if len(authenticated_fields) != 17:
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_entry_authentication_invalid"
        )
    mac = hmac.new(bytes(ledger_auth_key), digestmod=hashlib.sha256)
    mac.update(_LEDGER_ENTRY_HMAC_SCHEMA.encode("ascii"))
    mac.update(_hmac_frame(ledger_id))
    for position, value in enumerate(authenticated_fields):
        mac.update(position.to_bytes(2, "big"))
        mac.update(_hmac_frame(value))
    return mac.hexdigest()


def _validated_quarantined_hnc(
    summary: Mapping[str, Any],
    *,
    intrusion_id: str,
    packet_binding: HNCPayloadBindingV0,
    code: str,
) -> QuarantinedHNC:
    """Reconstruct the complete committed OS-boundary quarantine outcome."""

    if set(summary) != _QUARANTINE_SUMMARY_KEYS:
        raise RuntimeIntrusionLedgerError(code)
    denial_codes = summary.get("denial_codes")
    record_raw = summary.get("quarantine_record")
    binding_raw = summary.get("hnc_evidence_binding")
    if (
        not isinstance(denial_codes, list)
        or not isinstance(record_raw, Mapping)
        or not isinstance(binding_raw, Mapping)
        or summary.get("schema") != OS_PROTECTION_SCHEMA
        or summary.get("disposition") != str(IngressDisposition.QUARANTINED_HNC)
        or summary.get("local_development_only") is not True
        or summary.get("production_ready") is not False
        or summary.get("raw_material_retained") is not False
    ):
        raise RuntimeIntrusionLedgerError(code)
    try:
        record = QuarantineRecord.from_dict(record_raw)
        stored_binding = HNCPayloadBindingV0.from_dict(binding_raw)
        outcome = QuarantinedHNC(
            boundary_id=cast(str, summary.get("boundary_id")),
            admission_id=cast(str, summary.get("admission_id")),
            source_id=cast(str, summary.get("source_id")),
            ingress_kind=cast(str, summary.get("ingress_kind")),
            content_sha256=cast(str, summary.get("content_sha256")),
            content_size_bytes=cast(int, summary.get("content_size_bytes")),
            purpose_commitment=cast(str, summary.get("purpose_commitment")),
            operator_aad_sha256=cast(str, summary.get("operator_aad_sha256")),
            replay_token=cast(str, summary.get("replay_token")),
            recorded_at=cast(str, summary.get("recorded_at")),
            denial_codes=tuple(denial_codes),
            quarantine_record=record,
            hnc_evidence_binding=stored_binding,
            quarantine_commitment=cast(str, summary.get("quarantine_commitment")),
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc
    if (
        outcome.admission_id != intrusion_id
        or stored_binding != packet_binding
        or outcome.public_summary() != dict(summary)
        or record.evidence_commitments.get("hnc_quarantine_packet_commitment")
        != packet_binding.hnc_packet_commitment
        or record.evidence_commitments.get("hnc_quarantine_binding_commitment")
        != packet_binding.binding_commitment
    ):
        raise RuntimeIntrusionLedgerError(code)
    return outcome


def _expected_quarantine_operator_aad(
    packet: Mapping[str, Any],
    *,
    outcome: QuarantinedHNC,
    ledger_instance_commitment: str,
    code: str,
) -> dict[str, Any]:
    raw_aad = packet.get("operator_aad")
    if not isinstance(raw_aad, Mapping):
        raise RuntimeIntrusionLedgerError(code)
    aad = _decode_mapping(
        _mapping_bytes(raw_aad, code=code),
        code=code,
    )
    denial_codes = aad.get("denial_codes")
    caller_aad = aad.get("caller_aad")
    purpose = aad.get("purpose")
    if (
        set(aad) != _QUARANTINE_AAD_KEYS
        or not isinstance(denial_codes, list)
        or not isinstance(caller_aad, dict)
        or type(purpose) is not str
        or not purpose
        or aad.get("schema") != OS_INGRESS_AAD_SCHEMA
        or aad.get("ledger_instance_commitment")
        != ledger_instance_commitment
        or outcome.source_id != _RUNTIME_SOURCE_ID
        or outcome.ingress_kind
        not in {_RUNTIME_PREFLIGHT_INGRESS_KIND, _RUNTIME_VIOLATION_INGRESS_KIND}
        or purpose != _RUNTIME_INTRUSION_PURPOSE
        or aad.get("boundary_id") != outcome.boundary_id
        or aad.get("source_id") != outcome.source_id
        or aad.get("ingress_kind") != outcome.ingress_kind
        or aad.get("content_sha256") != outcome.content_sha256
        or type(aad.get("content_size_bytes")) is not int
        or aad.get("content_size_bytes") != outcome.content_size_bytes
        or aad.get("purpose_commitment") != outcome.purpose_commitment
        or domain_hash("aureon.plumber.purpose.v0", purpose) != outcome.purpose_commitment
        or aad.get("source_truth_established_by_local_wrapping") is not False
        or aad.get("quarantine") is not True
        or aad.get("quarantine_evidence_schema") != OS_QUARANTINE_EVIDENCE_SCHEMA
        or denial_codes != list(outcome.denial_codes)
    ):
        raise RuntimeIntrusionLedgerError(code)
    ingress_aad = {key: aad[key] for key in _INGRESS_AAD_KEYS}
    if _sha256_bytes(canonical_json_bytes(ingress_aad)) != outcome.operator_aad_sha256:
        raise RuntimeIntrusionLedgerError(code)
    if outcome.ingress_kind == _RUNTIME_PREFLIGHT_INGRESS_KIND:
        expected_probe = canonical_json_bytes(
            {
                "schema": _RUNTIME_GUARD_PREFLIGHT_SCHEMA,
                "probe": "commitment-only-hnc-quarantine",
                "production_ready": False,
            }
        )
        if (
            caller_aad != {"preflight": True}
            or outcome.content_sha256 != _sha256_bytes(expected_probe)
            or outcome.content_size_bytes != len(expected_probe)
        ):
            raise RuntimeIntrusionLedgerError(code)
    else:
        # Imported lazily to avoid a module import cycle while still pinning the
        # only dynamic plaintext AAD field to the guard's exact supported census.
        from .runtime_guard_v04 import _SUPPORTED_RULE_EVENTS

        event_name = caller_aad.get("event_name")
        resource_commitment = caller_aad.get("resource_commitment")
        reason_code = caller_aad.get("reason_code")
        if (
            set(caller_aad)
            != {"event_name", "resource_commitment", "reason_code"}
            or type(event_name) is not str
            or _RUNTIME_AUDIT_EVENT_RE.fullmatch(event_name) is None
            or event_name not in _SUPPORTED_RULE_EVENTS
            or type(reason_code) is not str
            or _RUNTIME_REASON_RE.fullmatch(reason_code) is None
            or reason_code != _RUNTIME_VIOLATION_REASON_CODE
        ):
            raise RuntimeIntrusionLedgerError(code)
        _require_sha256(
            resource_commitment,
            code=code,
            field="runtime_resource_commitment",
        )
        exact_content_joined = False
        for recorder_sequence in range(1, _MAX_RUNTIME_RECORDER_SEQUENCE + 1):
            expected_content = canonical_json_bytes(
                {
                    "schema": _RUNTIME_INTRUSION_SCHEMA,
                    "sequence": recorder_sequence,
                    "event_name": event_name,
                    "resource_commitment": resource_commitment,
                    "reason_code": reason_code,
                    "raw_arguments_retained": False,
                    "audit_event_origin_attested": False,
                    "effect_attempt_attested": False,
                    "resource_commitment_confidentiality_attested": False,
                    "resource_commitments_keyed": False,
                    "action_eligible": False,
                    "economic_eligible": False,
                    "production_ready": False,
                }
            )
            if (
                len(expected_content) == outcome.content_size_bytes
                and hmac.compare_digest(
                    _sha256_bytes(expected_content),
                    outcome.content_sha256,
                )
            ):
                exact_content_joined = True
                break
        if not exact_content_joined:
            raise RuntimeIntrusionLedgerError(code)
    return aad


def _authenticate_quarantine_packet(
    packet: Mapping[str, Any],
    *,
    outcome: QuarantinedHNC,
    quarantine_hnc_key: bytearray,
    ledger_instance_commitment: str,
    code: str,
) -> dict[str, Any]:
    """Authenticate and join the commitment-only encrypted evidence payload."""

    expected_aad = _expected_quarantine_operator_aad(
        packet,
        outcome=outcome,
        ledger_instance_commitment=ledger_instance_commitment,
        code=code,
    )
    try:
        decoded = decode_hnc_quantum_packet(
            packet,
            bytes(quarantine_hnc_key),
            expected_purpose=OS_QUARANTINE_EVIDENCE_PURPOSE,
            expected_operator_aad=expected_aad,
        )
        evidence = _decode_mapping(decoded.plaintext, code=code)
    except (HNCPacketError, TypeError, ValueError) as exc:
        raise RuntimeIntrusionLedgerError(code) from exc
    expected_evidence = {
        "schema": OS_QUARANTINE_EVIDENCE_SCHEMA,
        "admission_id": outcome.admission_id,
        "boundary_id": outcome.boundary_id,
        "source_id": outcome.source_id,
        "ingress_kind": outcome.ingress_kind,
        "content_sha256": outcome.content_sha256,
        "content_size_bytes": outcome.content_size_bytes,
        "purpose_commitment": outcome.purpose_commitment,
        "operator_aad_sha256": outcome.operator_aad_sha256,
        "replay_token": outcome.replay_token,
        "denial_codes": list(outcome.denial_codes),
        "raw_material_retained": False,
        "source_truth_established_by_local_wrapping": False,
    }
    if set(evidence) != _QUARANTINE_EVIDENCE_KEYS or evidence != expected_evidence:
        raise RuntimeIntrusionLedgerError(code)
    return expected_aad


def _validate_violation_runtime_metadata(
    metadata: Mapping[str, Any],
    *,
    outcome: QuarantinedHNC,
) -> None:
    """Accept only the OS boundary's exact commitment-only runtime contract."""

    false_fields = (
        "raw_arguments_retained",
        "plaintext_retained",
        "action_eligible",
        "economic_eligible",
        "production_ready",
    )
    if (
        metadata.get("schema") != OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA
        or set(metadata) != _OS_RUNTIME_METADATA_KEYS
    ):
        raise RuntimeIntrusionLedgerError("runtime_intrusion_metadata_contract_invalid")
    try:
        source_id_sha256 = _sha256_bytes(
            outcome.source_id.encode("utf-8", errors="strict")
        )
        ingress_kind_sha256 = _sha256_bytes(
            outcome.ingress_kind.encode("utf-8", errors="strict")
        )
    except UnicodeEncodeError as exc:  # pragma: no cover - outcome validates UTF-8
        raise RuntimeIntrusionLedgerError(
            "runtime_intrusion_metadata_join_invalid"
        ) from exc
    if (
        metadata.get("intrusion_id") != outcome.admission_id
        or metadata.get("content_sha256") != outcome.content_sha256
        or metadata.get("source_id_sha256") != source_id_sha256
        or metadata.get("ingress_kind_sha256") != ingress_kind_sha256
        or type(metadata.get("denial_code_count")) is not int
        or metadata.get("denial_code_count") != len(outcome.denial_codes)
        or any(metadata.get(field) is not False for field in false_fields)
    ):
        raise RuntimeIntrusionLedgerError("runtime_intrusion_metadata_join_invalid")


class SQLiteRuntimeIntrusionLedgerV04:
    """Strict, pre-opened local SQLite sink for encrypted HNC packets."""

    production_ready = False

    def __init__(
        self,
        path: Path,
        *,
        ledger_id: str,
        quarantine_hnc_key_provider: Callable[[], bytes | str | None],
        max_violation_entries: int = 1024,
        max_entry_bytes: int = 4 * 1024 * 1024,
        append_timeout_ms: int = 1000,
    ) -> None:
        if not isinstance(path, Path) or not path.is_absolute() or str(path) == ":memory:":
            raise RuntimeIntrusionLedgerError("durable_intrusion_sqlite_path_required")
        resolved = path.resolve()
        if not resolved.parent.exists() or not resolved.parent.is_dir():
            raise RuntimeIntrusionLedgerError("durable_intrusion_sqlite_parent_required")
        self._ledger_id = _identifier(ledger_id, "runtime_intrusion_ledger_id_invalid")
        self._max_violation_entries = _count(
            max_violation_entries,
            code="runtime_intrusion_capacity_invalid",
            minimum=1,
            maximum=_MAX_VIOLATION_ENTRIES,
        )
        self._max_entry_bytes = _count(
            max_entry_bytes,
            code="runtime_intrusion_entry_bytes_invalid",
            minimum=1024,
            maximum=_MAX_ENTRY_BYTES,
        )
        self._append_timeout_ms = _count(
            append_timeout_ms,
            code="runtime_intrusion_append_timeout_invalid",
            minimum=1,
            maximum=_MAX_APPEND_TIMEOUT_MS,
        )
        self._path = resolved
        self._path_existed = resolved.exists()
        self._path_initial_size = resolved.stat().st_size if self._path_existed else 0
        self._lock = threading.RLock()
        self._terminal_failure_code: str | None = None
        self._closed = False
        self._runtime_guard_owner_token_sha256: str | None = None
        self._lifecycle_generation = 0
        self._ledger_instance_commitment: str | None = None
        self._quarantine_hnc_key = self._load_quarantine_hnc_key(quarantine_hnc_key_provider)
        self._ledger_auth_key = bytearray()
        connection: sqlite3.Connection | None = None
        try:
            connection = self._open_connection()
            self._connection = connection
            self._initialize_and_validate()
        except BaseException as exc:
            if connection is not None:
                connection.close()
            self._wipe_retained_keys()
            self._closed = True
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_ledger_initialization_failed",
            )
            if error is exc:
                raise
            raise error from exc

    @staticmethod
    def _load_quarantine_hnc_key(
        provider: Callable[[], bytes | str | None],
    ) -> bytearray:
        if not callable(provider):
            raise RuntimeIntrusionLedgerError("runtime_intrusion_quarantine_hnc_key_provider_invalid")
        try:
            supplied = provider()
            if supplied is None:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_quarantine_hnc_key_unavailable")
            return bytearray(normalize_hnc_key_material(supplied))
        except RuntimeIntrusionLedgerError:
            raise
        except BaseException as exc:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_quarantine_hnc_key_invalid") from exc

    def _wipe_retained_keys(self) -> None:
        for retained in (self._quarantine_hnc_key, self._ledger_auth_key):
            for index in range(len(retained)):
                retained[index] = 0

    def _validate_pragmas(self, connection: sqlite3.Connection) -> None:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()
        synchronous = connection.execute("PRAGMA synchronous").fetchone()
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()
        trusted_schema = connection.execute("PRAGMA trusted_schema").fetchone()
        query_only = connection.execute("PRAGMA query_only").fetchone()
        locking_mode = connection.execute("PRAGMA locking_mode").fetchone()
        writable_schema = connection.execute("PRAGMA writable_schema").fetchone()
        ignore_check_constraints = connection.execute(
            "PRAGMA ignore_check_constraints"
        ).fetchone()
        if (
            journal_mode is None
            or str(journal_mode[0]).casefold() != "wal"
            or synchronous != (2,)
            or foreign_keys != (1,)
            or busy_timeout != (self._append_timeout_ms,)
            or trusted_schema != (0,)
            or query_only != (0,)
            or locking_mode is None
            or str(locking_mode[0]).casefold() != "normal"
            or writable_schema != (0,)
            or ignore_check_constraints != (0,)
        ):
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_durability_pragmas_invalid"
            )

    def _open_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self._path),
            timeout=self._append_timeout_ms / 1000.0,
            isolation_level=None,
            check_same_thread=False,
        )
        try:
            journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={self._append_timeout_ms}")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA writable_schema=OFF")
            connection.execute("PRAGMA ignore_check_constraints=OFF")
            if journal_mode is None or str(journal_mode[0]).casefold() != "wal":
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_durability_pragmas_invalid")
            self._validate_pragmas(connection)
            return connection
        except BaseException as exc:
            connection.close()
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_ledger_open_failed",
            )
            if error is exc:
                raise
            raise error from exc

    def _initialize_and_validate(self) -> None:
        connection = self._connection
        try:
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            existing_objects = connection.execute(
                "SELECT COUNT(*) FROM sqlite_schema "
                "WHERE type IN ('table','index','trigger','view')"
            ).fetchone()
            if existing_objects == (0,):
                if self._path_existed and self._path_initial_size > 0:
                    raise RuntimeIntrusionLedgerError(
                        "runtime_intrusion_ledger_schema_invalid"
                    )
                connection.execute(_METADATA_TABLE_SQL)
                connection.execute(_ENTRY_TABLE_SQL)
                connection.execute(_ENTRY_COMMITMENT_INDEX_SQL)
                for sql in _TRIGGER_SQL.values():
                    connection.execute(sql)
            self._validate_schema()
            row = connection.execute(
                "SELECT schema, ledger_id, ledger_instance_commitment, "
                "max_violation_entries, max_entry_bytes, append_timeout_ms, "
                "metadata_commitment, genesis_hmac_sha256 "
                "FROM runtime_intrusion_metadata_v04 WHERE singleton = 1"
            ).fetchone()
            if row is None:
                entry_count = connection.execute(
                    "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
                ).fetchone()
                if entry_count != (0,):
                    raise RuntimeIntrusionLedgerError(
                        "runtime_intrusion_ledger_metadata_missing"
                    )
                ledger_instance_commitment = domain_hash(
                    _LEDGER_INSTANCE_COMMITMENT_SCHEMA,
                    {"nonce": secrets.token_hex(32)},
                )
            else:
                ledger_instance_commitment = _require_sha256(
                    row[2],
                    code="runtime_intrusion_ledger_instance_invalid",
                    field="ledger_instance_commitment",
                )
            self._ledger_instance_commitment = ledger_instance_commitment
            self._ledger_auth_key = _derive_ledger_auth_key(
                self._quarantine_hnc_key,
                ledger_id=self._ledger_id,
                ledger_instance_commitment=ledger_instance_commitment,
            )
            expected = _metadata_payload(
                ledger_id=self._ledger_id,
                ledger_instance_commitment=ledger_instance_commitment,
                max_violation_entries=self._max_violation_entries,
                max_entry_bytes=self._max_entry_bytes,
                append_timeout_ms=self._append_timeout_ms,
            )
            expected_commitment = domain_hash(
                "aureon.plumber.runtime-intrusion-ledger.v04",
                expected,
            )
            expected_genesis_hmac = _genesis_hmac(
                self._ledger_auth_key,
                metadata=expected,
                metadata_commitment=expected_commitment,
            )
            self._genesis_hmac_sha256 = expected_genesis_hmac
            if row is None:
                connection.execute(
                    "INSERT INTO runtime_intrusion_metadata_v04 "
                    "(singleton, schema, ledger_id, ledger_instance_commitment, "
                    "max_violation_entries, max_entry_bytes, append_timeout_ms, "
                    "metadata_commitment, genesis_hmac_sha256) "
                    "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        RUNTIME_INTRUSION_LEDGER_SCHEMA,
                        self._ledger_id,
                        ledger_instance_commitment,
                        self._max_violation_entries,
                        self._max_entry_bytes,
                        self._append_timeout_ms,
                        expected_commitment,
                        expected_genesis_hmac,
                    ),
                )
            else:
                if row[:7] != (
                    RUNTIME_INTRUSION_LEDGER_SCHEMA,
                    self._ledger_id,
                    ledger_instance_commitment,
                    self._max_violation_entries,
                    self._max_entry_bytes,
                    self._append_timeout_ms,
                    expected_commitment,
                ):
                    raise RuntimeIntrusionLedgerError(
                        "runtime_intrusion_ledger_metadata_mismatch"
                    )
                stored_genesis_hmac = _require_sha256(
                    row[7],
                    code="runtime_intrusion_ledger_authentication_invalid",
                    field="genesis_hmac_sha256",
                )
                if not hmac.compare_digest(
                    stored_genesis_hmac,
                    expected_genesis_hmac,
                ):
                    raise RuntimeIntrusionLedgerError(
                        "runtime_intrusion_ledger_authentication_invalid"
                    )
            entries = self._validated_entries()
            if not entries:
                metadata = {
                    "schema": RUNTIME_INTRUSION_ENTRY_SCHEMA,
                    "probe": "preopened-durable-hnc-ledger",
                    "ledger_id": self._ledger_id,
                    "raw_material_retained": False,
                    "production_ready": False,
                }
                self._insert_rows_in_current_transaction(
                    [
                        self._build_row(
                            sequence=1,
                            entry_kind="PREFLIGHT",
                            intrusion_id=f"preflight:{self._ledger_id}",
                            previous_entry_commitment=_ZERO_SHA256,
                            previous_entry_hmac_sha256=expected_genesis_hmac,
                            runtime_metadata=metadata,
                            quarantine_summary=None,
                            hnc_packet=None,
                            terminal_after_append=False,
                        )
                    ]
                )
                entries = self._validated_entries()
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
        entries = self._validated_entries_in_atomic_snapshot()
        if entries[-1]["terminal_after_append"] is True:
            terminal_reason = entries[-1]["runtime_metadata"].get("reason_code")
            self._terminal_failure_code = (
                terminal_reason
                if isinstance(terminal_reason, str) and terminal_reason
                else "runtime_intrusion_ledger_terminal"
            )

    def _validate_schema(self) -> None:
        connection = self._connection
        self._validate_pragmas(connection)
        observed = {
            (
                str(object_type),
                str(name),
                str(table_name),
                None if sql is None else _normalized_sql(sql),
            )
            for object_type, name, table_name, sql in connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema "
                "WHERE type IN ('table','index','trigger','view')"
            ).fetchall()
        }
        expected = {
            (
                "table",
                "runtime_intrusion_metadata_v04",
                "runtime_intrusion_metadata_v04",
                _normalized_sql(_METADATA_TABLE_SQL),
            ),
            (
                "table",
                "runtime_intrusion_entries_v04",
                "runtime_intrusion_entries_v04",
                _normalized_sql(_ENTRY_TABLE_SQL),
            ),
            (
                "index",
                "runtime_intrusion_entries_v04_commitment_uq",
                "runtime_intrusion_entries_v04",
                _normalized_sql(_ENTRY_COMMITMENT_INDEX_SQL),
            ),
            *{
                ("trigger", name, name.rsplit("_", 2)[0], _normalized_sql(sql))
                for name, sql in _TRIGGER_SQL.items()
            },
            *_EXPECTED_INTERNAL_SCHEMA_OBJECTS,
        }
        # Trigger table names cannot be inferred safely from their identifiers.
        expected = {
            (
                object_type,
                name,
                (
                    "runtime_intrusion_metadata_v04"
                    if object_type == "trigger" and "metadata" in name
                    else (
                        "runtime_intrusion_entries_v04"
                        if object_type == "trigger"
                        else table_name
                    )
                ),
                sql,
            )
            for object_type, name, table_name, sql in expected
        }
        quick_check = connection.execute("PRAGMA quick_check").fetchone()
        if observed != expected or quick_check != ("ok",):
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_schema_invalid")

    def _now(self) -> str:
        return cast(
            str,
            format_timestamp(datetime.now(UTC).replace(microsecond=0)),
        )

    def _required_ledger_instance_commitment(self) -> str:
        commitment = self._ledger_instance_commitment
        if commitment is None:  # pragma: no cover - constructor is fail closed
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_instance_unavailable"
            )
        return commitment

    def _build_row(
        self,
        *,
        sequence: int,
        entry_kind: str,
        intrusion_id: str,
        previous_entry_commitment: str,
        previous_entry_hmac_sha256: str,
        runtime_metadata: Mapping[str, Any],
        quarantine_summary: Mapping[str, Any] | None,
        hnc_packet: Mapping[str, Any] | None,
        terminal_after_append: bool,
    ) -> tuple[Any, ...]:
        intrusion = _identifier(intrusion_id, "runtime_intrusion_id_invalid")
        previous = _require_sha256(
            previous_entry_commitment,
            code="runtime_intrusion_previous_commitment_invalid",
            field="previous_entry_commitment",
        )
        previous_hmac = _require_sha256(
            previous_entry_hmac_sha256,
            code="runtime_intrusion_previous_hmac_invalid",
            field="previous_entry_hmac_sha256",
        )
        metadata_bytes = _mapping_bytes(
            runtime_metadata,
            code="runtime_intrusion_metadata_invalid",
        )
        metadata = _decode_mapping(
            metadata_bytes,
            code="runtime_intrusion_metadata_invalid",
        )
        _assert_safe_mapping(
            metadata,
            code="runtime_intrusion_metadata_not_public_safe",
        )
        metadata_sha256 = _sha256_bytes(metadata_bytes)
        quarantine_bytes = b""
        quarantine_commitment = _ZERO_SHA256
        quarantine_record_commitment = _ZERO_SHA256
        packet_bytes = b""
        packet_sha256 = _ZERO_SHA256
        packet_commitment = _ZERO_SHA256
        binding_commitment = _ZERO_SHA256
        if entry_kind == "VIOLATION":
            if not isinstance(quarantine_summary, Mapping) or not isinstance(hnc_packet, Mapping):
                raise RuntimeIntrusionLedgerError("complete_runtime_intrusion_hnc_evidence_required")
            quarantine_bytes = _mapping_bytes(
                quarantine_summary,
                code="runtime_intrusion_quarantine_summary_invalid",
            )
            quarantine = _decode_mapping(
                quarantine_bytes,
                code="runtime_intrusion_quarantine_summary_invalid",
            )
            try:
                packet_binding = bind_hnc_packet(hnc_packet)
            except (TypeError, ValueError) as exc:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_hnc_evidence_invalid") from exc
            outcome = _validated_quarantined_hnc(
                quarantine,
                intrusion_id=intrusion,
                packet_binding=packet_binding,
                code="runtime_intrusion_hnc_evidence_invalid",
            )
            _authenticate_quarantine_packet(
                hnc_packet,
                outcome=outcome,
                quarantine_hnc_key=self._quarantine_hnc_key,
                ledger_instance_commitment=(
                    self._required_ledger_instance_commitment()
                ),
                code="runtime_intrusion_hnc_authentication_invalid",
            )
            _validate_violation_runtime_metadata(metadata, outcome=outcome)
            quarantine_commitment = outcome.quarantine_commitment
            quarantine_record_commitment = outcome.quarantine_record.record_commitment
            packet_bytes = _hnc_mapping_bytes(
                hnc_packet,
                code="runtime_intrusion_hnc_packet_invalid",
            )
            packet_sha256 = _sha256_bytes(packet_bytes)
            packet_commitment = packet_binding.hnc_packet_commitment
            binding_commitment = packet_binding.binding_commitment
        elif entry_kind not in {"PREFLIGHT", "TERMINAL"}:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_entry_kind_invalid")
        total_bytes = len(metadata_bytes) + len(quarantine_bytes) + len(packet_bytes)
        if total_bytes > self._max_entry_bytes:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_entry_capacity_exceeded")
        recorded_at = self._now()
        causal = {
            "schema": RUNTIME_INTRUSION_ENTRY_SCHEMA,
            "ledger_id": self._ledger_id,
            "ledger_instance_commitment": (
                self._required_ledger_instance_commitment()
            ),
            "sequence": sequence,
            "entry_kind": entry_kind,
            "intrusion_id": intrusion,
            "previous_entry_commitment": previous,
            "runtime_metadata_sha256": metadata_sha256,
            "quarantine_commitment": quarantine_commitment,
            "quarantine_record_commitment": quarantine_record_commitment,
            "hnc_packet_sha256": packet_sha256,
            "hnc_packet_commitment": packet_commitment,
            "hnc_binding_commitment": binding_commitment,
            "terminal_after_append": terminal_after_append,
            "recorded_at": recorded_at,
        }
        commitment = _entry_commitment(causal)
        authenticated_fields = (
            sequence,
            entry_kind,
            intrusion,
            previous,
            previous_hmac,
            metadata_bytes,
            metadata_sha256,
            quarantine_bytes,
            quarantine_commitment,
            quarantine_record_commitment,
            packet_bytes,
            packet_sha256,
            packet_commitment,
            binding_commitment,
            int(terminal_after_append),
            recorded_at,
            commitment,
        )
        return (
            *authenticated_fields,
            _entry_hmac(
                self._ledger_auth_key,
                ledger_id=self._ledger_id,
                authenticated_fields=authenticated_fields,
            ),
        )

    def _insert_rows(self, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        connection = self._connection
        try:
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            self._insert_rows_in_current_transaction(rows)
            connection.execute("COMMIT")
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        return self._readback_rows_in_atomic_snapshot(rows)

    def _insert_rows_in_current_transaction(
        self,
        rows: list[tuple[Any, ...]],
    ) -> None:
        if not self._connection.in_transaction:
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_transaction_required"
            )
        for row in rows:
            self._connection.execute(
                f"INSERT INTO runtime_intrusion_entries_v04 ({_ROW_COLUMNS}) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )

    def _readback_rows_in_atomic_snapshot(
        self,
        rows: list[tuple[Any, ...]],
    ) -> list[dict[str, Any]]:
        connection = self._connection
        # The insert commit and this read-back snapshot are intentionally two
        # transactions.  BEGIN IMMEDIATE prevents DDL from interleaving across
        # the multi-query schema validation and exact inserted-row read-back.
        try:
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            validated: list[dict[str, Any]] = []
            for row in rows:
                stored = connection.execute(
                    f"SELECT {_ROW_COLUMNS} FROM runtime_intrusion_entries_v04 WHERE sequence = ?",
                    (row[0],),
                ).fetchone()
                expected = self._validate_row(row)
                if stored is None:
                    raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_readback_failed")
                actual = self._validate_row(stored)
                if actual != expected:
                    raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_readback_failed")
                validated.append(actual)
            connection.execute("COMMIT")
            return validated
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise

    def _validate_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        if len(row) != 18:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_row_invalid")
        entry_hmac_sha256 = _require_sha256(
            row[17],
            code="runtime_intrusion_entry_authentication_invalid",
            field="entry_hmac_sha256",
        )
        expected_entry_hmac = _entry_hmac(
            self._ledger_auth_key,
            ledger_id=self._ledger_id,
            authenticated_fields=tuple(row[:17]),
        )
        if not hmac.compare_digest(entry_hmac_sha256, expected_entry_hmac):
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_entry_authentication_invalid"
            )
        sequence = _count(
            row[0],
            code="runtime_intrusion_sequence_invalid",
            minimum=1,
            maximum=_MAX_VIOLATION_ENTRIES + 2,
        )
        entry_kind = str(row[1])
        intrusion_id = _identifier(row[2], "runtime_intrusion_id_invalid")
        previous = _require_sha256(
            row[3],
            code="runtime_intrusion_previous_commitment_invalid",
            field="previous_entry_commitment",
        )
        previous_hmac = _require_sha256(
            row[4],
            code="runtime_intrusion_previous_hmac_invalid",
            field="previous_entry_hmac_sha256",
        )
        metadata_bytes = _blob(row[5], code="runtime_intrusion_metadata_invalid")
        metadata = _decode_mapping(row[5], code="runtime_intrusion_metadata_invalid")
        _assert_safe_mapping(
            metadata,
            code="runtime_intrusion_metadata_not_public_safe",
        )
        metadata_sha256 = _require_sha256(
            row[6],
            code="runtime_intrusion_metadata_hash_invalid",
            field="runtime_metadata_sha256",
        )
        if _sha256_bytes(metadata_bytes) != metadata_sha256:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_metadata_hash_mismatch")
        quarantine_bytes = _blob(row[7], code="runtime_intrusion_quarantine_summary_invalid")
        quarantine_commitment = _require_sha256(
            row[8],
            code="runtime_intrusion_quarantine_commitment_invalid",
            field="quarantine_commitment",
        )
        record_commitment = _require_sha256(
            row[9],
            code="runtime_intrusion_quarantine_record_commitment_invalid",
            field="quarantine_record_commitment",
        )
        packet_bytes = _blob(row[10], code="runtime_intrusion_hnc_packet_invalid")
        packet_sha256 = _require_sha256(
            row[11],
            code="runtime_intrusion_hnc_packet_hash_invalid",
            field="hnc_packet_sha256",
        )
        packet_commitment = _require_sha256(
            row[12],
            code="runtime_intrusion_hnc_packet_commitment_invalid",
            field="hnc_packet_commitment",
        )
        binding_commitment = _require_sha256(
            row[13],
            code="runtime_intrusion_hnc_binding_commitment_invalid",
            field="hnc_binding_commitment",
        )
        if _sha256_bytes(packet_bytes) != packet_sha256 and entry_kind == "VIOLATION":
            raise RuntimeIntrusionLedgerError("runtime_intrusion_hnc_packet_hash_mismatch")
        terminal = row[14] == 1
        if row[14] not in (0, 1):
            raise RuntimeIntrusionLedgerError("runtime_intrusion_terminal_flag_invalid")
        recorded_at = str(row[15])
        try:
            parse_timestamp(recorded_at, field="recorded_at")
        except (TypeError, ValueError) as exc:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_recorded_at_invalid") from exc
        entry_commitment = _require_sha256(
            row[16],
            code="runtime_intrusion_entry_commitment_invalid",
            field="entry_commitment",
        )
        authenticated_runtime_violation: dict[str, str] | None = None
        if entry_kind == "VIOLATION":
            quarantine = _decode_mapping(
                quarantine_bytes,
                code="runtime_intrusion_quarantine_summary_invalid",
            )
            packet = _decode_hnc_mapping(
                packet_bytes,
                code="runtime_intrusion_hnc_packet_invalid",
            )
            try:
                packet_binding = bind_hnc_packet(packet)
            except (TypeError, ValueError) as exc:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_stored_hnc_evidence_invalid") from exc
            outcome = _validated_quarantined_hnc(
                quarantine,
                intrusion_id=intrusion_id,
                packet_binding=packet_binding,
                code="runtime_intrusion_stored_hnc_evidence_invalid",
            )
            authenticated_aad = _authenticate_quarantine_packet(
                packet,
                outcome=outcome,
                quarantine_hnc_key=self._quarantine_hnc_key,
                ledger_instance_commitment=(
                    self._required_ledger_instance_commitment()
                ),
                code="runtime_intrusion_stored_hnc_authentication_invalid",
            )
            if outcome.ingress_kind == _RUNTIME_VIOLATION_INGRESS_KIND:
                caller_aad = authenticated_aad.get("caller_aad")
                if not isinstance(caller_aad, Mapping):  # pragma: no cover - authenticated above
                    raise RuntimeIntrusionLedgerError(
                        "runtime_intrusion_stored_hnc_authentication_invalid"
                    )
                authenticated_runtime_violation = {
                    "event_name": str(caller_aad["event_name"]),
                    "resource_commitment": str(caller_aad["resource_commitment"]),
                    "reason_code": str(caller_aad["reason_code"]),
                }
            _validate_violation_runtime_metadata(metadata, outcome=outcome)
            if (
                outcome.quarantine_commitment != quarantine_commitment
                or outcome.quarantine_record.record_commitment != record_commitment
                or packet_binding.hnc_packet_commitment != packet_commitment
                or packet_binding.binding_commitment != binding_commitment
            ):
                raise RuntimeIntrusionLedgerError("runtime_intrusion_stored_hnc_evidence_join_invalid")
        elif (
            entry_kind not in {"PREFLIGHT", "TERMINAL"}
            or quarantine_bytes
            or packet_bytes
            or any(
                value != _ZERO_SHA256
                for value in (
                    quarantine_commitment,
                    record_commitment,
                    packet_sha256,
                    packet_commitment,
                    binding_commitment,
                )
            )
        ):
            raise RuntimeIntrusionLedgerError("runtime_intrusion_nonviolation_row_invalid")
        causal = {
            "schema": RUNTIME_INTRUSION_ENTRY_SCHEMA,
            "ledger_id": self._ledger_id,
            "ledger_instance_commitment": (
                self._required_ledger_instance_commitment()
            ),
            "sequence": sequence,
            "entry_kind": entry_kind,
            "intrusion_id": intrusion_id,
            "previous_entry_commitment": previous,
            "runtime_metadata_sha256": metadata_sha256,
            "quarantine_commitment": quarantine_commitment,
            "quarantine_record_commitment": record_commitment,
            "hnc_packet_sha256": packet_sha256,
            "hnc_packet_commitment": packet_commitment,
            "hnc_binding_commitment": binding_commitment,
            "terminal_after_append": terminal,
            "recorded_at": recorded_at,
        }
        if _entry_commitment(causal) != entry_commitment:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_entry_commitment_mismatch")
        return {
            **causal,
            "previous_entry_hmac_sha256": previous_hmac,
            "entry_commitment": entry_commitment,
            "entry_hmac_sha256": entry_hmac_sha256,
            "runtime_metadata": metadata,
            # Private authenticated projection material.  It is derived only
            # from the exact AEAD-authenticated runtime-guard caller AAD and is
            # never persisted as a second plaintext ledger field.
            "authenticated_runtime_violation": authenticated_runtime_violation,
        }

    def _validated_entries(self) -> list[dict[str, Any]]:
        census = self._connection.execute(
            "SELECT COUNT(*), COALESCE(MAX("
            "length(runtime_metadata_json) + length(quarantine_summary_json) + "
            "length(hnc_packet_json)), 0) "
            "FROM runtime_intrusion_entries_v04"
        ).fetchone()
        if (
            census is None
            or len(census) != 2
            or type(census[0]) is not int
            or type(census[1]) is not int
            or census[0] < 0
            or census[0] > self._max_violation_entries + 2
        ):
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_capacity_invalid"
            )
        if census[1] < 0 or census[1] > self._max_entry_bytes:
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_entry_capacity_exceeded"
            )
        rows = self._connection.execute(
            f"SELECT {_ROW_COLUMNS} FROM runtime_intrusion_entries_v04 ORDER BY sequence"
        )
        entries: list[dict[str, Any]] = []
        previous = _ZERO_SHA256
        previous_hmac = self._genesis_hmac_sha256
        terminal_seen = False
        violation_count = 0
        for expected_sequence, row in enumerate(rows, start=1):
            entry = self._validate_row(row)
            if (
                entry["sequence"] != expected_sequence
                or entry["previous_entry_commitment"] != previous
                or entry["previous_entry_hmac_sha256"] != previous_hmac
                or terminal_seen
            ):
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_chain_invalid")
            if expected_sequence == 1 and entry["entry_kind"] != "PREFLIGHT":
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_preflight_missing")
            if expected_sequence > 1 and entry["entry_kind"] == "PREFLIGHT":
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_preflight_repeated")
            if entry["entry_kind"] == "TERMINAL":
                if entry["terminal_after_append"] is not True:
                    raise RuntimeIntrusionLedgerError("runtime_intrusion_terminal_marker_invalid")
            elif entry["terminal_after_append"] is not False:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_terminal_marker_invalid")
            if entry["entry_kind"] == "VIOLATION":
                violation_count += 1
            terminal_seen = entry["terminal_after_append"] is True
            previous = str(entry["entry_commitment"])
            previous_hmac = str(entry["entry_hmac_sha256"])
            entries.append(entry)
        if len(entries) != census[0]:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_chain_invalid")
        if violation_count > self._max_violation_entries:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_capacity_invalid")
        capacity_exhausted = violation_count == self._max_violation_entries
        terminal_present = bool(entries) and entries[-1]["entry_kind"] == "TERMINAL"
        if capacity_exhausted != terminal_present:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_terminal_state_invalid")
        return entries

    def _validated_entries_in_atomic_snapshot(self) -> list[dict[str, Any]]:
        connection = self._connection
        try:
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            connection.execute("COMMIT")
            return entries
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise

    def preflight(self) -> dict[str, Any]:
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            self._terminal_failure_code = "runtime_intrusion_ledger_busy"
            raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            entries = self._validated_entries_in_atomic_snapshot()
            violations = sum(entry["entry_kind"] == "VIOLATION" for entry in entries)
            terminal = self._terminal_failure_code is not None or (
                bool(entries) and entries[-1]["terminal_after_append"] is True
            )
            result = {
                "schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
                "ledger_id": self._ledger_id,
                "ledger_instance_commitment": (
                    self._required_ledger_instance_commitment()
                ),
                "ready": not terminal,
                "reason_code": self._terminal_failure_code or ("terminal" if terminal else "ready"),
                "entry_count": len(entries),
                "violation_count": violations,
                "max_violation_entries": self._max_violation_entries,
                "remaining_violation_capacity": max(0, self._max_violation_entries - violations),
                "preopened_connection": True,
                "append_only_schema": True,
                "durability_readback": True,
                "keyed_genesis_authentication_ready": True,
                "keyed_entry_authentication_ready": True,
                "keyed_entries_authenticated": bool(entries),
                "quarantine_hnc_authentication_ready": True,
                "encrypted_hnc_packet_persistence_ready": True,
                "encrypted_hnc_packets_persisted": violations > 0,
                "encrypted_hnc_packets_authenticated": violations > 0,
                "raw_arguments_retained": False,
                "external_head_anchor_attested": False,
                "magic_star_durable_custody_attested": False,
                "production_ready": False,
            }
            assert_public_summary_safe(result)
            return result
        except BaseException as exc:
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_ledger_preflight_failed",
            )
            if self._terminal_failure_code is None:
                self._terminal_failure_code = error.code
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def authenticated_violation_projection(
        self,
        *,
        sequence: int,
        entry_commitment: str,
    ) -> dict[str, Any]:
        """Return one commitment-only, fully authenticated runtime violation.

        The projection is selected by both sequence and entry commitment while
        the ledger lock and ``BEGIN IMMEDIATE`` snapshot are held.  Before any
        event or reason leaves the ledger, the complete schema, keyed chain,
        quarantine joins, encrypted HNC packet, AEAD tag, and exact
        runtime-guard caller AAD are revalidated.  Intrusion IDs, resource
        commitments, authentication tags, and raw arguments never leave this
        boundary.
        """

        selected_sequence = _count(
            sequence,
            code="runtime_intrusion_projection_sequence_invalid",
            minimum=2,
            maximum=self._max_violation_entries + 2,
        )
        selected_commitment = _require_sha256(
            entry_commitment,
            code="runtime_intrusion_projection_entry_commitment_invalid",
            field="entry_commitment",
        )
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            self._terminal_failure_code = "runtime_intrusion_ledger_busy"
            raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
        connection = self._connection
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            entry = next(
                (
                    candidate
                    for candidate in entries
                    if candidate["sequence"] == selected_sequence
                ),
                None,
            )
            if (
                globals().get("_authenticated_projection_from_entry")
                is not _EXACT_AUTHENTICATED_PROJECTION_GATE
                or _EXACT_AUTHENTICATED_PROJECTION_GATE.__code__
                is not _EXACT_AUTHENTICATED_PROJECTION_GATE_CODE
            ):
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_projection_code_identity_invalid"
                )
            result = _EXACT_AUTHENTICATED_PROJECTION_GATE(
                entry,
                selected_sequence=selected_sequence,
                selected_commitment=selected_commitment,
                ledger_id=self._ledger_id,
                ledger_instance_commitment=(
                    self._required_ledger_instance_commitment()
                ),
            )
            connection.execute("COMMIT")
            return cast(dict[str, Any], result)
        except BaseException as exc:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_projection_failed",
            )
            if (
                self._terminal_failure_code is None
                and error.code
                not in {
                    "runtime_intrusion_projection_entry_join_invalid",
                    "runtime_intrusion_projection_runtime_violation_required",
                }
            ):
                self._terminal_failure_code = error.code
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def authenticated_violation_projections(
        self,
        *,
        selections: tuple[tuple[int, str], ...],
    ) -> tuple[dict[str, Any], ...]:
        """Authenticate a bounded set of violations in one ledger snapshot.

        This is the batch form used by the encrypted proposal vault.  The
        complete keyed chain and every encrypted HNC row are validated once;
        selected commitment-only projections are then derived from that same
        atomic snapshot in caller order.
        """

        if (
            type(selections) is not tuple
            or not 1 <= len(selections) <= _MAX_AUTHENTICATED_PROJECTION_BATCH
        ):
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_projection_batch_invalid"
            )
        validated_selections: list[tuple[int, str]] = []
        seen_sequences: set[int] = set()
        seen_commitments: set[str] = set()
        for raw in selections:
            if type(raw) is not tuple or len(raw) != 2:
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_projection_batch_invalid"
                )
            selected_sequence = _count(
                raw[0],
                code="runtime_intrusion_projection_batch_invalid",
                minimum=2,
                maximum=self._max_violation_entries + 2,
            )
            selected_commitment = _require_sha256(
                raw[1],
                code="runtime_intrusion_projection_batch_invalid",
                field="entry_commitment",
            )
            if (
                selected_sequence in seen_sequences
                or selected_commitment in seen_commitments
            ):
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_projection_batch_invalid"
                )
            seen_sequences.add(selected_sequence)
            seen_commitments.add(selected_commitment)
            validated_selections.append(
                (selected_sequence, selected_commitment)
            )

        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            self._terminal_failure_code = "runtime_intrusion_ledger_busy"
            raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
        connection = self._connection
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            entries_by_sequence = {
                int(entry["sequence"]): entry for entry in entries
            }
            ledger_instance_commitment = (
                self._required_ledger_instance_commitment()
            )
            if (
                globals().get("_authenticated_projection_from_entry")
                is not _EXACT_AUTHENTICATED_PROJECTION_GATE
                or _EXACT_AUTHENTICATED_PROJECTION_GATE.__code__
                is not _EXACT_AUTHENTICATED_PROJECTION_GATE_CODE
            ):
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_projection_code_identity_invalid"
                )
            result = tuple(
                _EXACT_AUTHENTICATED_PROJECTION_GATE(
                    entries_by_sequence.get(selected_sequence),
                    selected_sequence=selected_sequence,
                    selected_commitment=selected_commitment,
                    ledger_id=self._ledger_id,
                    ledger_instance_commitment=ledger_instance_commitment,
                )
                for selected_sequence, selected_commitment in validated_selections
            )
            connection.execute("COMMIT")
            return result
        except BaseException as exc:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_projection_batch_failed",
            )
            if (
                self._terminal_failure_code is None
                and error.code
                not in {
                    "runtime_intrusion_projection_entry_join_invalid",
                    "runtime_intrusion_projection_runtime_violation_required",
                    "runtime_intrusion_projection_batch_invalid",
                }
            ):
                self._terminal_failure_code = error.code
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    @staticmethod
    def _owner_token_sha256(owner_token: str) -> str:
        if type(owner_token) is not str or not owner_token:
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_owner_token_invalid"
            )
        try:
            encoded = owner_token.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_owner_token_invalid"
            ) from exc
        if len(encoded) > 4096:
            raise RuntimeIntrusionLedgerError(
                "runtime_intrusion_ledger_owner_token_invalid"
            )
        return _sha256_bytes(encoded)

    def _runtime_guard_snapshot(
        self,
        *,
        entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        violations = sum(entry["entry_kind"] == "VIOLATION" for entry in entries)
        terminal = self._terminal_failure_code is not None or (
            bool(entries) and entries[-1]["terminal_after_append"] is True
        )
        return {
            "schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
            "ledger_id": self._ledger_id,
            "ledger_instance_commitment": (
                self._required_ledger_instance_commitment()
            ),
            "sealed": self._runtime_guard_owner_token_sha256 is not None,
            "owner_token_sha256": self._runtime_guard_owner_token_sha256
            or _ZERO_SHA256,
            "lifecycle_generation": self._lifecycle_generation,
            "close_rejected_while_sealed": True,
            "ready": not terminal,
            "reason_code": self._terminal_failure_code
            or ("terminal" if terminal else "ready"),
            "entry_count": len(entries),
            "violation_count": violations,
            "remaining_violation_capacity": max(
                0,
                self._max_violation_entries - violations,
            ),
            "production_ready": False,
        }

    def seal_for_runtime_guard(self, owner_token: str) -> dict[str, Any]:
        owner_token_sha256 = self._owner_token_sha256(owner_token)
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_busy")
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            if self._terminal_failure_code is not None:
                raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
            entries = self._validated_entries_in_atomic_snapshot()
            if self._runtime_guard_owner_token_sha256 is None:
                self._runtime_guard_owner_token_sha256 = owner_token_sha256
                self._lifecycle_generation += 1
            elif not hmac.compare_digest(
                self._runtime_guard_owner_token_sha256,
                owner_token_sha256,
            ):
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_ledger_already_sealed"
                )
            result = self._runtime_guard_snapshot(entries=entries)
            if result["ready"] is not True:
                raise RuntimeIntrusionLedgerError(str(result["reason_code"]))
            assert_public_summary_safe(result)
            return result
        except BaseException as exc:
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_ledger_seal_failed",
            )
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def validate_runtime_guard_seal(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> dict[str, Any]:
        owner_token_sha256 = self._owner_token_sha256(owner_token)
        generation = _count(
            lifecycle_generation,
            code="runtime_intrusion_ledger_lifecycle_generation_invalid",
            minimum=1,
            maximum=(1 << 53) - 1,
        )
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_busy")
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            if (
                self._runtime_guard_owner_token_sha256 is None
                or not hmac.compare_digest(
                    self._runtime_guard_owner_token_sha256,
                    owner_token_sha256,
                )
                or generation != self._lifecycle_generation
            ):
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_ledger_seal_invalid"
                )
            entries = self._validated_entries_in_atomic_snapshot()
            result = self._runtime_guard_snapshot(entries=entries)
            if result["ready"] is not True:
                raise RuntimeIntrusionLedgerError(str(result["reason_code"]))
            assert_public_summary_safe(result)
            return result
        except BaseException as exc:
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_ledger_seal_validation_failed",
            )
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    @contextmanager
    def runtime_guard_lifecycle_lease(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> Iterator[dict[str, Any]]:
        """Hold one decision-only SQLite write snapshot for the full context.

        The body must not append through this same connection.  Recorder appends
        occur outside lifecycle-decision leases and receive their own atomic
        transaction.
        """

        owner_token_sha256 = self._owner_token_sha256(owner_token)
        generation = _count(
            lifecycle_generation,
            code="runtime_intrusion_ledger_lifecycle_generation_invalid",
            minimum=1,
            maximum=(1 << 53) - 1,
        )
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_busy")
        connection = self._connection
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            if (
                self._runtime_guard_owner_token_sha256 is None
                or not hmac.compare_digest(
                    self._runtime_guard_owner_token_sha256,
                    owner_token_sha256,
                )
                or generation != self._lifecycle_generation
            ):
                raise RuntimeIntrusionLedgerError(
                    "runtime_intrusion_ledger_seal_invalid"
                )
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            before = self._runtime_guard_snapshot(
                entries=self._validated_entries()
            )
            if before["ready"] is not True:
                raise RuntimeIntrusionLedgerError(str(before["reason_code"]))
            yield before
            self._validate_schema()
            after = self._runtime_guard_snapshot(
                entries=self._validated_entries()
            )
            if after["ready"] is not True:
                raise RuntimeIntrusionLedgerError(str(after["reason_code"]))
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
        finally:
            self._lock.release()

    def append_violation(
        self,
        *,
        intrusion_id: str,
        runtime_metadata: Mapping[str, Any],
        quarantine_summary: Mapping[str, Any],
        hnc_packet: Mapping[str, Any],
    ) -> dict[str, Any]:
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            self._terminal_failure_code = "runtime_intrusion_ledger_busy"
            raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
        connection = self._connection
        try:
            if self._closed:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_closed")
            if self._terminal_failure_code is not None:
                raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
            self._validate_pragmas(connection)
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            violations = sum(entry["entry_kind"] == "VIOLATION" for entry in entries)
            if entries[-1]["terminal_after_append"] is True:
                self._terminal_failure_code = "runtime_intrusion_ledger_terminal"
                raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
            if violations >= self._max_violation_entries:
                self._terminal_failure_code = "runtime_intrusion_ledger_capacity_exhausted"
                raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
            sequence = len(entries) + 1
            previous = str(entries[-1]["entry_commitment"])
            previous_hmac = str(entries[-1]["entry_hmac_sha256"])
            violation_row = self._build_row(
                sequence=sequence,
                entry_kind="VIOLATION",
                intrusion_id=intrusion_id,
                previous_entry_commitment=previous,
                previous_entry_hmac_sha256=previous_hmac,
                runtime_metadata=runtime_metadata,
                quarantine_summary=quarantine_summary,
                hnc_packet=hnc_packet,
                terminal_after_append=False,
            )
            rows = [violation_row]
            final_capacity_entry = violations + 1 == self._max_violation_entries
            if final_capacity_entry:
                terminal_metadata = {
                    "schema": RUNTIME_INTRUSION_ENTRY_SCHEMA,
                    "reason_code": "runtime_intrusion_ledger_capacity_exhausted",
                    "last_intrusion_id_commitment": _sha256_bytes(intrusion_id.encode("utf-8")),
                    "raw_material_retained": False,
                    "production_ready": False,
                }
                rows.append(
                    self._build_row(
                        sequence=sequence + 1,
                        entry_kind="TERMINAL",
                        intrusion_id=f"terminal:{_sha256_bytes(intrusion_id.encode('utf-8'))}",
                        previous_entry_commitment=str(violation_row[16]),
                        previous_entry_hmac_sha256=str(violation_row[17]),
                        runtime_metadata=terminal_metadata,
                        quarantine_summary=None,
                        hnc_packet=None,
                        terminal_after_append=True,
                    )
                )
            self._insert_rows_in_current_transaction(rows)
            connection.execute("COMMIT")
            readback = self._readback_rows_in_atomic_snapshot(rows)
            if not readback or readback[0]["sequence"] != sequence:
                raise RuntimeIntrusionLedgerError("runtime_intrusion_ledger_readback_failed")
            entry = readback[0]
            if final_capacity_entry:
                self._terminal_failure_code = "runtime_intrusion_ledger_capacity_exhausted"
            receipt = {
                "schema": RUNTIME_INTRUSION_ENTRY_SCHEMA,
                "ledger_id": self._ledger_id,
                "ledger_instance_commitment": (
                    self._required_ledger_instance_commitment()
                ),
                "sequence": entry["sequence"],
                "intrusion_id": entry["intrusion_id"],
                "entry_commitment": entry["entry_commitment"],
                "previous_entry_commitment": entry["previous_entry_commitment"],
                "hnc_packet_commitment": entry["hnc_packet_commitment"],
                "hnc_binding_commitment": entry["hnc_binding_commitment"],
                "quarantine_commitment": entry["quarantine_commitment"],
                "quarantine_record_commitment": entry["quarantine_record_commitment"],
                "terminal_after_append": final_capacity_entry,
                "durability_readback": True,
                "keyed_entry_authenticated": True,
                "encrypted_hnc_packet_persisted": True,
                "hnc_packet_authenticated": True,
                "raw_arguments_retained": False,
                "external_head_anchor_attested": False,
                "magic_star_durable_custody_attested": False,
                "production_ready": False,
            }
            assert_public_summary_safe(receipt)
            return receipt
        except BaseException as exc:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(
                exc,
                fallback="runtime_intrusion_ledger_append_failed",
            )
            if self._terminal_failure_code is None:
                self._terminal_failure_code = error.code
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def public_summary(self) -> dict[str, Any]:
        try:
            return self.preflight()
        except BaseException:
            result = {
                "schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
                "ledger_id": self._ledger_id,
                "ledger_instance_commitment": (
                    self._required_ledger_instance_commitment()
                ),
                "ready": False,
                "reason_code": self._terminal_failure_code or "runtime_intrusion_ledger_unavailable",
                "preopened_connection": not self._closed,
                "raw_arguments_retained": False,
                "external_head_anchor_attested": False,
                "magic_star_durable_custody_attested": False,
                "production_ready": False,
            }
            assert_public_summary_safe(result)
            return result

    def close(self) -> None:
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            self._terminal_failure_code = "runtime_intrusion_ledger_busy"
            raise RuntimeIntrusionLedgerError(self._terminal_failure_code)
        try:
            if not self._closed:
                if self._runtime_guard_owner_token_sha256 is not None:
                    raise RuntimeIntrusionLedgerError(
                        "runtime_intrusion_ledger_runtime_guard_sealed"
                    )
                try:
                    self._connection.close()
                except BaseException as exc:
                    self._terminal_failure_code = "runtime_intrusion_ledger_close_failed"
                    raise RuntimeIntrusionLedgerError(self._terminal_failure_code) from exc
                finally:
                    self._wipe_retained_keys()
                    self._closed = True
        finally:
            self._lock.release()


__all__ = [
    "RUNTIME_INTRUSION_AUTHENTICATED_PROJECTION_SCHEMA",
    "RUNTIME_INTRUSION_ENTRY_SCHEMA",
    "RUNTIME_INTRUSION_LEDGER_SCHEMA",
    "RuntimeIntrusionLedgerError",
    "SQLiteRuntimeIntrusionLedgerV04",
]
