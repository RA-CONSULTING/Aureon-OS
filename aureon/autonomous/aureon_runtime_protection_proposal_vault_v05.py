"""Durable encrypted HOLD vault for runtime-remediation review material.

The runtime intrusion ledger is the sole event owner.  This module materializes
one deterministic proposal and one fixed-template protection-code candidate
from that exact ledger.  Their canonical envelope is stored only as an
authenticated HNC ciphertext plus bounded commitment metadata.  The candidate
is a review-only new-file unified diff: this module has no apply, import,
execution, subprocess, network, release, provider, or economic-action route.

SQLite/WAL is not WORM storage or an external monotonic anchor.  A valid-prefix
rollback, a byte-for-byte clone, and arbitrary code execution in this Python
process remain outside this local HOLD-only proof.
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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from aureon.autonomous.aureon_intrusion_protection_bridge import (
    INTRUSION_PROTECTION_PROPOSAL_SCHEMA,
    AureonIntrusionProtectionWorkProposalV04,
    build_runtime_intrusion_protection_proposal_v04,
)
from aureon.harmonic.hnc_quantum_packet_crypto import (
    HNCPacketError,
    build_hnc_quantum_packet,
    decode_hnc_quantum_packet,
    normalize_hnc_key_material,
    validate_hnc_packet_contract,
)
from aureon.harmonic.hnc_quantum_packet_crypto import (
    canonical_json_bytes as canonical_hnc_json_bytes,
)
from aureon.plumber.audit import assert_public_summary_safe
from aureon.plumber.crypto import canonical_json_bytes, decode_canonical_json, domain_hash
from aureon.plumber.runtime_intrusion_ledger_v04 import (
    RUNTIME_INTRUSION_LEDGER_SCHEMA,
    SQLiteRuntimeIntrusionLedgerV04,
)
from aureon.plumber.schema import SchemaError, freeze_mapping, require_sha256, thaw_json

RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault.v05"
)
RUNTIME_PROTECTION_PROPOSAL_VAULT_ENTRY_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-entry.v05"
)
RUNTIME_PROTECTION_PROPOSAL_VAULT_RECEIPT_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-receipt.v05"
)
RUNTIME_PROTECTION_PROPOSAL_VAULT_VERIFIED_RECEIPT_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-verified-receipt.v05"
)
RUNTIME_PROTECTION_PROPOSAL_REVIEW_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-review.v05"
)
RUNTIME_PROTECTION_PROPOSAL_REVIEW_MATERIAL_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-review-material.v05"
)
RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-code-candidate.v05"
)
RUNTIME_PROTECTION_CODE_CANDIDATE_REVIEW_MATERIAL_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-code-candidate-review-material.v05"
)
RUNTIME_PROTECTION_REVIEW_ENVELOPE_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-review-envelope.v05"
)
RUNTIME_PROTECTION_PROPOSAL_PURPOSE: Final = (
    "aureon.autonomous.runtime-protection-proposal.v05"
)

_ZERO_SHA256: Final = "0" * 64
_ID_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_MAX_PROPOSALS_LIMIT: Final = 64
_MAX_SOURCE_VIOLATION_ENTRIES_FOR_VAULT: Final = 64
_MAX_PACKET_BYTES_LIMIT: Final = 32 * 1024 * 1024
_MIN_PACKET_BYTES: Final = 128 * 1024
_MAX_APPEND_TIMEOUT_MS: Final = 30_000
_NON_TERMINAL_SEAL_ERRORS: Final = frozenset(
    {"runtime_protection_vault_capacity_exhausted"}
)
_KEY_DERIVATION_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-key.v05"
)
_GENESIS_HMAC_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-genesis-hmac.v05"
)
_ENTRY_HMAC_SCHEMA: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-entry-hmac.v05"
)
_ENTRY_COMMITMENT_DOMAIN: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-entry.v05"
)
_CANDIDATE_COMMITMENT_DOMAIN: Final = (
    "aureon.autonomous.runtime-protection-code-candidate.v05"
)
_INSTANCE_DOMAIN: Final = (
    "aureon.autonomous.runtime-protection-proposal-vault-instance.v05"
)
_MAX_CANDIDATE_SOURCE_BYTES: Final = 16 * 1024
_MAX_CANDIDATE_DIFF_BYTES: Final = 32 * 1024
_CANDIDATE_RECIPE_ID: Final = "aureon.runtime-protection.exact-hold-guard.v01"
_CANDIDATE_RECIPE_DOMAIN: Final = "aureon.runtime-protection.recipe.v01"
_CANDIDATE_RECIPE_SPEC: Final = {
    "schema": _CANDIDATE_RECIPE_DOMAIN,
    "recipe_id": _CANDIDATE_RECIPE_ID,
    "source_encoding": "utf-8",
    "line_endings": "LF",
    "target_kind": "new_unregistered_python_review_module",
    "exact_event_and_reason_decision": "HOLD",
    "all_other_input_decision": "OUT_OF_SCOPE",
    "allow_decision_present": False,
    "caller_supplied_prompt_or_source": False,
    "apply_import_execute_or_release_route": False,
}
_CANDIDATE_RECIPE_SHA256: Final = domain_hash(
    _CANDIDATE_RECIPE_DOMAIN,
    _CANDIDATE_RECIPE_SPEC,
)
_EXACT_CANDIDATE_RECIPE_ID: Final = _CANDIDATE_RECIPE_ID
_EXACT_CANDIDATE_RECIPE_SHA256: Final = _CANDIDATE_RECIPE_SHA256

_EXACT_PROPOSAL_BUILDER: Final = build_runtime_intrusion_protection_proposal_v04
_EXACT_PROPOSAL_BUILDER_CODE: Final = _EXACT_PROPOSAL_BUILDER.__code__
_EXACT_SOURCE_PREFLIGHT: Final = SQLiteRuntimeIntrusionLedgerV04.preflight
_EXACT_SOURCE_PREFLIGHT_CODE: Final = _EXACT_SOURCE_PREFLIGHT.__code__
_EXACT_SOURCE_BATCH_PROJECTION: Final = (
    SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projections
)
_EXACT_SOURCE_BATCH_PROJECTION_CODE: Final = (
    _EXACT_SOURCE_BATCH_PROJECTION.__code__
)
_EXACT_SOURCE_LEDGER_METHODS: Final = (
    (
        "preflight",
        SQLiteRuntimeIntrusionLedgerV04.preflight,
        SQLiteRuntimeIntrusionLedgerV04.preflight.__code__,
    ),
    (
        "authenticated_violation_projection",
        SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projection,
        SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projection.__code__,
    ),
    (
        "authenticated_violation_projections",
        _EXACT_SOURCE_BATCH_PROJECTION,
        _EXACT_SOURCE_BATCH_PROJECTION_CODE,
    ),
    (
        "_validated_entries_in_atomic_snapshot",
        SQLiteRuntimeIntrusionLedgerV04._validated_entries_in_atomic_snapshot,
        SQLiteRuntimeIntrusionLedgerV04._validated_entries_in_atomic_snapshot.__code__,
    ),
    (
        "_validate_pragmas",
        SQLiteRuntimeIntrusionLedgerV04._validate_pragmas,
        SQLiteRuntimeIntrusionLedgerV04._validate_pragmas.__code__,
    ),
    (
        "_validate_schema",
        SQLiteRuntimeIntrusionLedgerV04._validate_schema,
        SQLiteRuntimeIntrusionLedgerV04._validate_schema.__code__,
    ),
    (
        "_validated_entries",
        SQLiteRuntimeIntrusionLedgerV04._validated_entries,
        SQLiteRuntimeIntrusionLedgerV04._validated_entries.__code__,
    ),
    (
        "_validate_row",
        SQLiteRuntimeIntrusionLedgerV04._validate_row,
        SQLiteRuntimeIntrusionLedgerV04._validate_row.__code__,
    ),
    (
        "_required_ledger_instance_commitment",
        SQLiteRuntimeIntrusionLedgerV04._required_ledger_instance_commitment,
        SQLiteRuntimeIntrusionLedgerV04._required_ledger_instance_commitment.__code__,
    ),
)
_RECEIPT_FACTORY_TOKEN: Final = object()
_REVIEW_FACTORY_TOKEN: Final = object()

_PROPOSAL_FIELDS: Final = frozenset(
    {
        "schema",
        "proposal_owner",
        "owner_route",
        "proposal_kind",
        "remediation_template_id",
        "intrusion_evidence",
        "canonical_work_ledger_schema",
        "canonical_proposal_forge_schema",
        "canonical_proposal_forge_id",
        "production_release_command_schema",
        "magic_star_schema",
        "disposition",
        "review_required",
        "commitment_only",
        "signature_present",
        "single_owner_route",
        "duplicate_queue_created",
        "proposal_persisted",
        "work_ledger_appended",
        "proposal_forge_invoked",
        "source_request_generated",
        "code_generation_invoked",
        "target_path_present",
        "unified_diff_present",
        "patch_applied",
        "repository_mutation_authorized",
        "release_broker_invoked",
        "magic_star_invoked",
        "external_action_authorized",
        "action_eligible",
        "economic_eligible",
        "production_ready",
        "proposal_id",
        "proposal_commitment",
    }
)
_FALSE_PROPOSAL_FIELDS: Final = frozenset(
    {
        "signature_present",
        "duplicate_queue_created",
        "proposal_persisted",
        "work_ledger_appended",
        "proposal_forge_invoked",
        "source_request_generated",
        "code_generation_invoked",
        "target_path_present",
        "unified_diff_present",
        "patch_applied",
        "repository_mutation_authorized",
        "release_broker_invoked",
        "magic_star_invoked",
        "external_action_authorized",
        "action_eligible",
        "economic_eligible",
        "production_ready",
    }
)

_CANDIDATE_FIELDS: Final = frozenset(
    {
        "schema",
        "candidate_owner",
        "owner_route",
        "candidate_kind",
        "generator_recipe_id",
        "generator_recipe_sha256",
        "target_path",
        "unified_diff",
        "candidate_source_sha256",
        "candidate_source_size_bytes",
        "unified_diff_sha256",
        "unified_diff_size_bytes",
        "source_event_name",
        "source_reason_code",
        "proposal_id",
        "proposal_commitment",
        "disposition",
        "review_required",
        "single_owner_route",
        "deterministic_template_rendered",
        "technical_provenance_recorded",
        "openai_assistance_disclosed",
        "code_generation_invoked",
        "external_model_invoked",
        "self_coder_invoked",
        "proposal_forge_invoked",
        "apply_authorized",
        "import_authorized",
        "execute_authorized",
        "release_authorized",
        "patch_applied",
        "repository_mutation_authorized",
        "external_action_authorized",
        "action_eligible",
        "economic_eligible",
        "semantic_correctness_attested",
        "integration_tested",
        "legal_title_attested",
        "production_ready",
        "candidate_commitment",
    }
)
_FALSE_CANDIDATE_FIELDS: Final = frozenset(
    {
        "external_model_invoked",
        "self_coder_invoked",
        "proposal_forge_invoked",
        "apply_authorized",
        "import_authorized",
        "execute_authorized",
        "release_authorized",
        "patch_applied",
        "repository_mutation_authorized",
        "external_action_authorized",
        "action_eligible",
        "economic_eligible",
        "semantic_correctness_attested",
        "integration_tested",
        "legal_title_attested",
        "production_ready",
    }
)

_METADATA_TABLE_SQL: Final = """
CREATE TABLE runtime_protection_vault_metadata_v05 (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    schema TEXT NOT NULL,
    vault_id TEXT NOT NULL,
    vault_instance_commitment TEXT NOT NULL,
    source_ledger_id TEXT NOT NULL,
    source_ledger_instance_commitment TEXT NOT NULL,
    max_proposals INTEGER NOT NULL,
    max_packet_bytes INTEGER NOT NULL,
    append_timeout_ms INTEGER NOT NULL,
    metadata_commitment TEXT NOT NULL,
    genesis_hmac_sha256 TEXT NOT NULL
) STRICT
""".strip()

_ENTRY_TABLE_SQL: Final = """
CREATE TABLE runtime_protection_vault_entries_v05 (
    sequence INTEGER PRIMARY KEY,
    proposal_id TEXT NOT NULL UNIQUE,
    proposal_commitment TEXT NOT NULL UNIQUE,
    candidate_commitment TEXT NOT NULL,
    source_ledger_sequence INTEGER NOT NULL UNIQUE,
    source_entry_commitment TEXT NOT NULL UNIQUE,
    source_projection_commitment TEXT NOT NULL,
    previous_entry_commitment TEXT NOT NULL,
    previous_entry_hmac_sha256 TEXT NOT NULL,
    proposal_packet_json BLOB NOT NULL,
    proposal_packet_sha256 TEXT NOT NULL,
    proposal_payload_sha256 TEXT NOT NULL,
    proposal_payload_size_bytes INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    terminal_after_append INTEGER NOT NULL CHECK(terminal_after_append IN (0,1)),
    entry_commitment TEXT NOT NULL UNIQUE,
    entry_hmac_sha256 TEXT NOT NULL
) STRICT
""".strip()

_TRIGGER_SQL: Final = {
    "runtime_protection_vault_metadata_v05_no_update": """
CREATE TRIGGER runtime_protection_vault_metadata_v05_no_update
BEFORE UPDATE ON runtime_protection_vault_metadata_v05
BEGIN SELECT RAISE(ABORT, 'runtime_protection_vault_metadata_immutable'); END
""".strip(),
    "runtime_protection_vault_metadata_v05_no_delete": """
CREATE TRIGGER runtime_protection_vault_metadata_v05_no_delete
BEFORE DELETE ON runtime_protection_vault_metadata_v05
BEGIN SELECT RAISE(ABORT, 'runtime_protection_vault_metadata_immutable'); END
""".strip(),
    "runtime_protection_vault_metadata_v05_singleton": """
CREATE TRIGGER runtime_protection_vault_metadata_v05_singleton
BEFORE INSERT ON runtime_protection_vault_metadata_v05
WHEN (SELECT COUNT(*) FROM runtime_protection_vault_metadata_v05) > 0
BEGIN SELECT RAISE(ABORT, 'runtime_protection_vault_metadata_singleton'); END
""".strip(),
    "runtime_protection_vault_entries_v05_no_update": """
CREATE TRIGGER runtime_protection_vault_entries_v05_no_update
BEFORE UPDATE ON runtime_protection_vault_entries_v05
BEGIN SELECT RAISE(ABORT, 'runtime_protection_vault_entries_immutable'); END
""".strip(),
    "runtime_protection_vault_entries_v05_no_delete": """
CREATE TRIGGER runtime_protection_vault_entries_v05_no_delete
BEFORE DELETE ON runtime_protection_vault_entries_v05
BEGIN SELECT RAISE(ABORT, 'runtime_protection_vault_entries_immutable'); END
""".strip(),
    "runtime_protection_vault_entries_v05_chain": """
CREATE TRIGGER runtime_protection_vault_entries_v05_chain
BEFORE INSERT ON runtime_protection_vault_entries_v05
BEGIN
    SELECT CASE
      WHEN NEW.sequence != (SELECT COUNT(*) + 1 FROM runtime_protection_vault_entries_v05)
      THEN RAISE(ABORT, 'runtime_protection_vault_sequence_invalid')
    END;
    SELECT CASE
      WHEN NEW.previous_entry_commitment != COALESCE(
        (SELECT entry_commitment FROM runtime_protection_vault_entries_v05 ORDER BY sequence DESC LIMIT 1),
        '0000000000000000000000000000000000000000000000000000000000000000')
      THEN RAISE(ABORT, 'runtime_protection_vault_previous_commitment_invalid')
    END;
    SELECT CASE
      WHEN NEW.previous_entry_hmac_sha256 != COALESCE(
        (SELECT entry_hmac_sha256 FROM runtime_protection_vault_entries_v05 ORDER BY sequence DESC LIMIT 1),
        '0000000000000000000000000000000000000000000000000000000000000000')
      THEN RAISE(ABORT, 'runtime_protection_vault_previous_hmac_invalid')
    END;
    SELECT CASE
      WHEN EXISTS(SELECT 1 FROM runtime_protection_vault_entries_v05 WHERE terminal_after_append = 1)
      THEN RAISE(ABORT, 'runtime_protection_vault_terminal')
    END;
END
""".strip(),
}

_METADATA_COLUMNS: Final = (
    "singleton",
    "schema",
    "vault_id",
    "vault_instance_commitment",
    "source_ledger_id",
    "source_ledger_instance_commitment",
    "max_proposals",
    "max_packet_bytes",
    "append_timeout_ms",
    "metadata_commitment",
    "genesis_hmac_sha256",
)
_ENTRY_COLUMNS: Final = (
    "sequence",
    "proposal_id",
    "proposal_commitment",
    "candidate_commitment",
    "source_ledger_sequence",
    "source_entry_commitment",
    "source_projection_commitment",
    "previous_entry_commitment",
    "previous_entry_hmac_sha256",
    "proposal_packet_json",
    "proposal_packet_sha256",
    "proposal_payload_sha256",
    "proposal_payload_size_bytes",
    "recorded_at",
    "terminal_after_append",
    "entry_commitment",
    "entry_hmac_sha256",
)
_EXPECTED_SCHEMA_OBJECTS: Final = frozenset(
    {
        ("table", "runtime_protection_vault_metadata_v05", "runtime_protection_vault_metadata_v05"),
        ("table", "runtime_protection_vault_entries_v05", "runtime_protection_vault_entries_v05"),
        *(
            (
                "index",
                f"sqlite_autoindex_runtime_protection_vault_entries_v05_{position}",
                "runtime_protection_vault_entries_v05",
            )
            for position in range(1, 6)
        ),
        *(
            (
                "trigger",
                name,
                (
                    "runtime_protection_vault_metadata_v05"
                    if name.startswith("runtime_protection_vault_metadata")
                    else "runtime_protection_vault_entries_v05"
                ),
            )
            for name in _TRIGGER_SQL
        ),
    }
)


class RuntimeProtectionProposalVaultError(RuntimeError):
    """Stable, non-secret vault failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _validate_source_ledger_code_identity(
    source_ledger: SQLiteRuntimeIntrusionLedgerV04,
) -> None:
    """Reject class replacement, code replacement, and instance shadowing.

    The captured public source methods still dispatch through ``self``.  The
    complete transitive authentication chain therefore has to remain exact;
    pinning only ``preflight`` or ``authenticated_violation_projection`` does
    not authenticate what those methods actually execute.
    """

    if type(source_ledger) is not SQLiteRuntimeIntrusionLedgerV04:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_source_ledger_code_identity_invalid"
        )
    class_namespace = vars(SQLiteRuntimeIntrusionLedgerV04)
    if (
        "__getattribute__" in class_namespace
        or SQLiteRuntimeIntrusionLedgerV04.__getattribute__
        is not object.__getattribute__
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_source_ledger_code_identity_invalid"
        )
    instance_namespace = object.__getattribute__(source_ledger, "__dict__")
    for name, exact_method, exact_code in _EXACT_SOURCE_LEDGER_METHODS:
        if (
            name in instance_namespace
            or class_namespace.get(name) is not exact_method
            or exact_method.__code__ is not exact_code
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_ledger_code_identity_invalid"
            )


_EXACT_SOURCE_IDENTITY_GATE: Final = _validate_source_ledger_code_identity
_EXACT_SOURCE_IDENTITY_GATE_CODE: Final = _EXACT_SOURCE_IDENTITY_GATE.__code__


def _stable_error(
    exc: BaseException,
    *,
    fallback: str,
) -> RuntimeProtectionProposalVaultError:
    if isinstance(exc, RuntimeProtectionProposalVaultError):
        return exc
    return RuntimeProtectionProposalVaultError(fallback)


def _count(value: object, *, code: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise RuntimeProtectionProposalVaultError(code)
    return value


def _identifier(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise RuntimeProtectionProposalVaultError(code)
    return value


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _required_sha256(value: object, *, code: str, field: str) -> str:
    try:
        validated = require_sha256(value, field=field)
    except (SchemaError, TypeError, ValueError) as exc:
        raise RuntimeProtectionProposalVaultError(code) from exc
    return str(validated)


def _hmac_frame(value: object) -> bytes:
    if type(value) is int:
        kind = b"integer"
        encoded = str(value).encode("ascii")
    elif type(value) is str:
        kind = b"text"
        encoded = value.encode("utf-8", errors="strict")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        kind = b"blob"
        encoded = bytes(value)
    else:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_entry_authentication_invalid"
        )
    return (
        len(kind).to_bytes(2, "big")
        + kind
        + len(encoded).to_bytes(8, "big")
        + encoded
    )


def _metadata_payload(
    *,
    vault_id: str,
    vault_instance_commitment: str,
    source_ledger_id: str,
    source_ledger_instance_commitment: str,
    max_proposals: int,
    max_packet_bytes: int,
    append_timeout_ms: int,
) -> dict[str, Any]:
    return {
        "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
        "vault_id": vault_id,
        "vault_instance_commitment": vault_instance_commitment,
        "source_ledger_id": source_ledger_id,
        "source_ledger_instance_commitment": source_ledger_instance_commitment,
        "max_proposals": max_proposals,
        "max_packet_bytes": max_packet_bytes,
        "append_timeout_ms": append_timeout_ms,
    }


def _derive_keys(
    proposal_key: bytearray,
    *,
    metadata: Mapping[str, Any],
) -> tuple[bytearray, bytearray]:
    context = canonical_json_bytes(
        {"schema": _KEY_DERIVATION_SCHEMA, "metadata": dict(metadata)}
    )
    packet_key = bytearray(
        hmac.new(bytes(proposal_key), b"packet\x00" + context, hashlib.sha256).digest()
    )
    auth_key = bytearray(
        hmac.new(bytes(proposal_key), b"chain\x00" + context, hashlib.sha256).digest()
    )
    return packet_key, auth_key


def _genesis_hmac(
    auth_key: bytearray,
    *,
    metadata: Mapping[str, Any],
    metadata_commitment: str,
) -> str:
    message = canonical_json_bytes(
        {
            "schema": _GENESIS_HMAC_SCHEMA,
            "metadata": dict(metadata),
            "metadata_commitment": metadata_commitment,
        }
    )
    return hmac.new(bytes(auth_key), message, hashlib.sha256).hexdigest()


def _entry_hmac(
    auth_key: bytearray,
    *,
    vault_id: str,
    fields: tuple[Any, ...],
) -> str:
    if len(fields) != len(_ENTRY_COLUMNS) - 1:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_entry_authentication_invalid"
        )
    mac = hmac.new(bytes(auth_key), digestmod=hashlib.sha256)
    mac.update(_ENTRY_HMAC_SCHEMA.encode("ascii"))
    mac.update(_hmac_frame(vault_id))
    for position, value in enumerate(fields):
        mac.update(position.to_bytes(2, "big"))
        mac.update(_hmac_frame(value))
    return mac.hexdigest()


def _normalize_sql(value: object) -> str:
    # sqlite_schema preserves the submitted DDL text.  Do not remove interior
    # whitespace or case-fold here: either transformation also changes quoted
    # SQL literals and could make a semantically modified trigger compare equal.
    return str(value or "").replace("\r\n", "\n").strip()


def _decode_hnc_packet_bytes(raw: bytes, *, maximum_bytes: int) -> dict[str, Any]:
    """Decode one exact canonical HNC packet, including its finite floats."""

    if not raw or len(raw) > maximum_bytes:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_packet_invalid"
        )

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_packet_invalid"
                )
            result[key] = item
        return result

    def reject_constant(_value: str) -> Any:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_packet_invalid"
        )

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except RuntimeProtectionProposalVaultError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_packet_invalid"
        ) from exc
    if (
        not isinstance(value, dict)
        or canonical_hnc_json_bytes(value, max_bytes=maximum_bytes) != raw
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_packet_invalid"
        )
    return value


def _proposal_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_proposal_payload_invalid"
        )
    try:
        encoded = canonical_json_bytes(dict(value))
        parsed = decode_canonical_json(
            encoded,
            require_mapping=True,
            max_bytes=4 * 1024 * 1024,
        )
    except BaseException as exc:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_proposal_payload_invalid"
        ) from exc
    if (
        not isinstance(parsed, dict)
        or set(parsed) != _PROPOSAL_FIELDS
        or parsed.get("schema") != INTRUSION_PROTECTION_PROPOSAL_SCHEMA
        or parsed.get("proposal_owner") != "Aureon"
        or parsed.get("proposal_kind") != "security_remediation_review"
        or parsed.get("disposition") != "HOLD"
        or parsed.get("review_required") is not True
        or parsed.get("commitment_only") is not True
        or parsed.get("single_owner_route") is not True
        or any(parsed.get(name) is not False for name in _FALSE_PROPOSAL_FIELDS)
        or not isinstance(parsed.get("intrusion_evidence"), Mapping)
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_proposal_payload_invalid"
        )
    proposal_id = parsed.get("proposal_id")
    proposal_commitment = parsed.get("proposal_commitment")
    if (
        not isinstance(proposal_id, str)
        or not proposal_id.startswith("remediation-")
        or len(proposal_id) != 44
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_proposal_payload_invalid"
        )
    commitment = _required_sha256(
        proposal_commitment,
        code="runtime_protection_vault_proposal_payload_invalid",
        field="proposal_commitment",
    )
    core = {
        key: parsed[key]
        for key in _PROPOSAL_FIELDS
        if key not in {"proposal_id", "proposal_commitment"}
    }
    expected_commitment = domain_hash(
        INTRUSION_PROTECTION_PROPOSAL_SCHEMA,
        core,
    )
    if (
        commitment != expected_commitment
        or proposal_id != f"remediation-{commitment[:32]}"
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_proposal_payload_invalid"
        )
    assert_public_summary_safe(parsed)
    return parsed


def _render_protection_code_candidate(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Render one exact review-only new-file diff without invoking another route."""

    parsed_proposal = _proposal_payload(proposal)
    evidence = parsed_proposal.get("intrusion_evidence")
    if not isinstance(evidence, Mapping):  # pragma: no cover - proposal invariant
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_source_invalid"
        )
    event_name = evidence.get("event_name")
    reason_code = evidence.get("reason_code")
    proposal_id = parsed_proposal.get("proposal_id")
    proposal_commitment = parsed_proposal.get("proposal_commitment")
    if (
        not isinstance(event_name, str)
        or not event_name
        or not isinstance(reason_code, str)
        or not reason_code
        or not isinstance(proposal_id, str)
        or not isinstance(proposal_commitment, str)
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_source_invalid"
        )

    target_path = (
        "aureon/autonomous/generated/"
        f"runtime_protection_review_{proposal_commitment[:32]}.py"
    )
    source_lines = (
        '"""Deterministic runtime-protection review candidate; grants no authority."""',
        "",
        'CANDIDATE_OWNER = "Aureon"',
        f"GENERATOR_RECIPE_ID = {json.dumps(_EXACT_CANDIDATE_RECIPE_ID, ensure_ascii=True)}",
        f"EXPECTED_EVENT_NAME = {json.dumps(event_name, ensure_ascii=True)}",
        f"EXPECTED_REASON_CODE = {json.dumps(reason_code, ensure_ascii=True)}",
        f"SOURCE_PROPOSAL_COMMITMENT = {json.dumps(proposal_commitment, ensure_ascii=True)}",
        "",
        "",
        "def review_runtime_protection_candidate(",
        "    *, event_name: str, reason_code: str",
        ") -> str:",
        "    if (",
        "        type(event_name) is str",
        "        and type(reason_code) is str",
        "        and event_name == EXPECTED_EVENT_NAME",
        "        and reason_code == EXPECTED_REASON_CODE",
        "    ):",
        '        return "HOLD"',
        '    return "OUT_OF_SCOPE"',
    )
    candidate_source = "\n".join(source_lines) + "\n"
    unified_diff_lines = (
        f"diff --git a/{target_path} b/{target_path}",
        "new file mode 100644",
        "--- /dev/null",
        f"+++ b/{target_path}",
        f"@@ -0,0 +1,{len(source_lines)} @@",
        *(f"+{line}" for line in source_lines),
    )
    unified_diff = "\n".join(unified_diff_lines) + "\n"
    candidate_source_bytes = candidate_source.encode("utf-8", errors="strict")
    unified_diff_bytes = unified_diff.encode("utf-8", errors="strict")
    if (
        len(candidate_source_bytes) > _MAX_CANDIDATE_SOURCE_BYTES
        or len(unified_diff_bytes) > _MAX_CANDIDATE_DIFF_BYTES
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_capacity_exceeded"
        )
    core = {
        "schema": RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA,
        "candidate_owner": "Aureon",
        "owner_route": parsed_proposal["owner_route"],
        "candidate_kind": "review_only_new_file_unified_diff",
        "generator_recipe_id": _EXACT_CANDIDATE_RECIPE_ID,
        "generator_recipe_sha256": _EXACT_CANDIDATE_RECIPE_SHA256,
        "target_path": target_path,
        "unified_diff": unified_diff,
        "candidate_source_sha256": _sha256(candidate_source_bytes),
        "candidate_source_size_bytes": len(candidate_source_bytes),
        "unified_diff_sha256": _sha256(unified_diff_bytes),
        "unified_diff_size_bytes": len(unified_diff_bytes),
        "source_event_name": event_name,
        "source_reason_code": reason_code,
        "proposal_id": proposal_id,
        "proposal_commitment": proposal_commitment,
        "disposition": "HOLD",
        "review_required": True,
        "single_owner_route": True,
        "deterministic_template_rendered": True,
        "technical_provenance_recorded": True,
        "openai_assistance_disclosed": True,
        "code_generation_invoked": True,
        "external_model_invoked": False,
        "self_coder_invoked": False,
        "proposal_forge_invoked": False,
        "apply_authorized": False,
        "import_authorized": False,
        "execute_authorized": False,
        "release_authorized": False,
        "patch_applied": False,
        "repository_mutation_authorized": False,
        "external_action_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
        "semantic_correctness_attested": False,
        "integration_tested": False,
        "legal_title_attested": False,
        "production_ready": False,
    }
    return {
        **core,
        "candidate_commitment": domain_hash(_CANDIDATE_COMMITMENT_DOMAIN, core),
    }


_EXACT_CANDIDATE_RENDERER: Final[
    Callable[[Mapping[str, Any]], dict[str, Any]]
] = _render_protection_code_candidate
_EXACT_CANDIDATE_RENDERER_CODE: Final = _EXACT_CANDIDATE_RENDERER.__code__


def _render_exact_protection_code_candidate(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Call only the import-time renderer identity used by this vault contract."""

    if (
        globals().get("_render_protection_code_candidate")
        is not _EXACT_CANDIDATE_RENDERER
        or _EXACT_CANDIDATE_RENDERER.__code__ is not _EXACT_CANDIDATE_RENDERER_CODE
        or globals().get("_CANDIDATE_RECIPE_ID") != _EXACT_CANDIDATE_RECIPE_ID
        or globals().get("_CANDIDATE_RECIPE_SHA256")
        != _EXACT_CANDIDATE_RECIPE_SHA256
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_renderer_identity_invalid"
        )
    renderer: Callable[[Mapping[str, Any]], dict[str, Any]] = (
        _EXACT_CANDIDATE_RENDERER
    )
    return renderer(proposal)


_EXACT_CANDIDATE_RENDERER_GATE: Final[
    Callable[[Mapping[str, Any]], dict[str, Any]]
] = _render_exact_protection_code_candidate
_EXACT_CANDIDATE_RENDERER_GATE_CODE: Final = (
    _EXACT_CANDIDATE_RENDERER_GATE.__code__
)


def _protection_code_candidate(
    value: object,
    *,
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_payload_invalid"
        )
    try:
        encoded = canonical_json_bytes(dict(value))
        parsed = decode_canonical_json(
            encoded,
            require_mapping=True,
            max_bytes=_MAX_CANDIDATE_DIFF_BYTES * 2,
        )
    except BaseException as exc:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_payload_invalid"
        ) from exc
    if (
        not isinstance(parsed, dict)
        or set(parsed) != _CANDIDATE_FIELDS
        or parsed.get("schema") != RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA
        or parsed.get("candidate_owner") != "Aureon"
        or parsed.get("candidate_kind") != "review_only_new_file_unified_diff"
        or parsed.get("generator_recipe_id") != _EXACT_CANDIDATE_RECIPE_ID
        or parsed.get("generator_recipe_sha256")
        != _EXACT_CANDIDATE_RECIPE_SHA256
        or parsed.get("disposition") != "HOLD"
        or parsed.get("review_required") is not True
        or parsed.get("single_owner_route") is not True
        or parsed.get("deterministic_template_rendered") is not True
        or parsed.get("technical_provenance_recorded") is not True
        or parsed.get("openai_assistance_disclosed") is not True
        or parsed.get("code_generation_invoked") is not True
        or any(parsed.get(name) is not False for name in _FALSE_CANDIDATE_FIELDS)
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_payload_invalid"
        )
    for name in (
        "candidate_source_sha256",
        "unified_diff_sha256",
        "generator_recipe_sha256",
        "proposal_commitment",
        "candidate_commitment",
    ):
        _required_sha256(
            parsed.get(name),
            code="runtime_protection_vault_candidate_payload_invalid",
            field=name,
        )
    for name, maximum in (
        ("candidate_source_size_bytes", _MAX_CANDIDATE_SOURCE_BYTES),
        ("unified_diff_size_bytes", _MAX_CANDIDATE_DIFF_BYTES),
    ):
        _count(
            parsed.get(name),
            code="runtime_protection_vault_candidate_payload_invalid",
            minimum=1,
            maximum=maximum,
        )
    if (
        globals().get("_render_exact_protection_code_candidate")
        is not _EXACT_CANDIDATE_RENDERER_GATE
        or _EXACT_CANDIDATE_RENDERER_GATE.__code__
        is not _EXACT_CANDIDATE_RENDERER_GATE_CODE
    ):
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_renderer_identity_invalid"
        )
    expected = _EXACT_CANDIDATE_RENDERER_GATE(proposal)
    if parsed != expected:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_candidate_payload_invalid"
        )
    return parsed


def _review_envelope(
    value: object,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema",
        "proposal",
        "protection_code_candidate",
    }:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_review_envelope_invalid"
        )
    if value.get("schema") != RUNTIME_PROTECTION_REVIEW_ENVELOPE_SCHEMA:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_review_envelope_invalid"
        )
    proposal = _proposal_payload(value.get("proposal"))
    candidate = _protection_code_candidate(
        value.get("protection_code_candidate"),
        proposal=proposal,
    )
    return proposal, candidate


@dataclass(frozen=True, slots=True, init=False)
class ProtectionProposalVaultReceiptV05:
    vault_id: str
    vault_instance_commitment: str
    sequence: int
    proposal_id: str
    proposal_commitment: str
    candidate_commitment: str
    candidate_source_sha256: str
    candidate_unified_diff_sha256: str
    source_ledger_id: str
    source_ledger_instance_commitment: str
    source_ledger_sequence: int
    source_entry_commitment: str
    source_projection_commitment: str
    proposal_packet_sha256: str
    proposal_payload_sha256: str
    recorded_at: str
    entry_commitment: str
    terminal_after_append: bool
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_receipt_factory_required"
        )

    @classmethod
    def _issue(
        cls,
        *,
        factory_token: object | None = None,
        vault_id: str,
        vault_instance_commitment: str,
        sequence: int,
        proposal_id: str,
        proposal_commitment: str,
        candidate_commitment: str,
        candidate_source_sha256: str,
        candidate_unified_diff_sha256: str,
        source_ledger_id: str,
        source_ledger_instance_commitment: str,
        source_ledger_sequence: int,
        source_entry_commitment: str,
        source_projection_commitment: str,
        proposal_packet_sha256: str,
        proposal_payload_sha256: str,
        recorded_at: str,
        entry_commitment: str,
        terminal_after_append: bool,
    ) -> ProtectionProposalVaultReceiptV05:
        if factory_token is not _RECEIPT_FACTORY_TOKEN:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_receipt_origin_invalid"
            )
        instance = object.__new__(cls)
        values = {
            "vault_id": vault_id,
            "vault_instance_commitment": vault_instance_commitment,
            "sequence": sequence,
            "proposal_id": proposal_id,
            "proposal_commitment": proposal_commitment,
            "candidate_commitment": candidate_commitment,
            "candidate_source_sha256": candidate_source_sha256,
            "candidate_unified_diff_sha256": candidate_unified_diff_sha256,
            "source_ledger_id": source_ledger_id,
            "source_ledger_instance_commitment": source_ledger_instance_commitment,
            "source_ledger_sequence": source_ledger_sequence,
            "source_entry_commitment": source_entry_commitment,
            "source_projection_commitment": source_projection_commitment,
            "proposal_packet_sha256": proposal_packet_sha256,
            "proposal_payload_sha256": proposal_payload_sha256,
            "recorded_at": recorded_at,
            "entry_commitment": entry_commitment,
            "terminal_after_append": terminal_after_append,
        }
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        object.__setattr__(instance, "_factory_token", _RECEIPT_FACTORY_TOKEN)
        instance._validate()
        return instance

    def _validate(self) -> None:
        if self._factory_token is not _RECEIPT_FACTORY_TOKEN:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_receipt_origin_invalid"
            )
        _identifier(self.vault_id, code="runtime_protection_vault_receipt_invalid")
        _identifier(
            self.source_ledger_id,
            code="runtime_protection_vault_receipt_invalid",
        )
        _count(
            self.sequence,
            code="runtime_protection_vault_receipt_invalid",
            minimum=1,
            maximum=_MAX_PROPOSALS_LIMIT,
        )
        _count(
            self.source_ledger_sequence,
            code="runtime_protection_vault_receipt_invalid",
            minimum=2,
            maximum=2**63 - 1,
        )
        for name in (
            "vault_instance_commitment",
            "proposal_commitment",
            "candidate_commitment",
            "candidate_source_sha256",
            "candidate_unified_diff_sha256",
            "source_ledger_instance_commitment",
            "source_entry_commitment",
            "source_projection_commitment",
            "proposal_packet_sha256",
            "proposal_payload_sha256",
            "entry_commitment",
        ):
            _required_sha256(
                getattr(self, name),
                code="runtime_protection_vault_receipt_invalid",
                field=name,
            )
        if self.proposal_id != f"remediation-{self.proposal_commitment[:32]}":
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_receipt_invalid"
            )
        try:
            recorded = datetime.fromisoformat(self.recorded_at)
        except (TypeError, ValueError) as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_receipt_invalid"
            ) from exc
        if (
            recorded.tzinfo is None
            or recorded.utcoffset() != UTC.utcoffset(recorded)
            or type(self.terminal_after_append) is not bool
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_receipt_invalid"
            )

    def public_summary(self) -> dict[str, Any]:
        self._validate()
        summary = {
            "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_RECEIPT_SCHEMA,
            "vault_id": self.vault_id,
            "vault_instance_commitment": self.vault_instance_commitment,
            "sequence": self.sequence,
            "proposal_id": self.proposal_id,
            "proposal_commitment": self.proposal_commitment,
            "candidate_commitment": self.candidate_commitment,
            "candidate_source_sha256": self.candidate_source_sha256,
            "candidate_unified_diff_sha256": self.candidate_unified_diff_sha256,
            "source_ledger_id": self.source_ledger_id,
            "source_ledger_instance_commitment": self.source_ledger_instance_commitment,
            "source_ledger_sequence": self.source_ledger_sequence,
            "source_entry_commitment": self.source_entry_commitment,
            "source_projection_commitment": self.source_projection_commitment,
            "proposal_packet_sha256": self.proposal_packet_sha256,
            "proposal_payload_sha256": self.proposal_payload_sha256,
            "recorded_at": self.recorded_at,
            "entry_commitment": self.entry_commitment,
            "terminal_after_append": self.terminal_after_append,
            "disposition": "HOLD",
            "standalone_receipt_authenticated": False,
            "live_vault_verification_required": True,
            "durability_readback": False,
            "keyed_entry_authenticated": False,
            "encrypted_hnc_packet_persisted": False,
            "encrypted_hnc_packet_authenticated": False,
            "encrypted_protection_code_candidate_persisted": False,
            "encrypted_protection_code_candidate_authenticated": False,
            "review_required": True,
            "commitment_only": True,
            "proposal_owner": "Aureon",
            "technical_provenance_recorded": False,
            "legal_title_attested": False,
            "key_provider_restart_continuity_attested": False,
            "independent_key_custody_attested": False,
            "code_generation_invoked": True,
            "external_model_invoked": False,
            "self_coder_invoked": False,
            "proposal_forge_invoked": False,
            "apply_authorized": False,
            "import_authorized": False,
            "execute_authorized": False,
            "release_authorized": False,
            "repository_mutation_authorized": False,
            "generated_code_execution_authorized": False,
            "release_broker_invoked": False,
            "magic_star_invoked": False,
            "external_action_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
            "external_head_anchor_attested": False,
            "production_ready": False,
        }
        assert_public_summary_safe(summary)
        return summary


@dataclass(frozen=True, slots=True, init=False)
class ReviewableProtectionProposalV05:
    vault_id: str
    vault_instance_commitment: str
    vault_sequence: int
    vault_entry_commitment: str
    _proposal: Mapping[str, Any] = field(repr=False)
    candidate_commitment: str
    candidate_source_sha256: str
    candidate_unified_diff_sha256: str
    _protection_code_candidate: Mapping[str, Any] = field(repr=False)
    _factory_token: object = field(repr=False, compare=False)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeProtectionProposalVaultError(
            "runtime_protection_vault_review_factory_required"
        )

    @classmethod
    def _issue(
        cls,
        *,
        factory_token: object | None = None,
        vault_id: str,
        vault_instance_commitment: str,
        vault_sequence: int,
        vault_entry_commitment: str,
        proposal: Mapping[str, Any],
        protection_code_candidate: Mapping[str, Any],
    ) -> ReviewableProtectionProposalV05:
        if factory_token is not _REVIEW_FACTORY_TOKEN:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_review_origin_invalid"
            )
        parsed = _proposal_payload(proposal)
        candidate = _protection_code_candidate(
            protection_code_candidate,
            proposal=parsed,
        )
        instance = object.__new__(cls)
        object.__setattr__(instance, "vault_id", vault_id)
        object.__setattr__(
            instance,
            "vault_instance_commitment",
            vault_instance_commitment,
        )
        object.__setattr__(instance, "vault_sequence", vault_sequence)
        object.__setattr__(
            instance,
            "vault_entry_commitment",
            vault_entry_commitment,
        )
        object.__setattr__(
            instance,
            "_proposal",
            freeze_mapping(parsed, field="reviewable_protection_proposal"),
        )
        object.__setattr__(
            instance,
            "candidate_commitment",
            str(candidate["candidate_commitment"]),
        )
        object.__setattr__(
            instance,
            "candidate_source_sha256",
            str(candidate["candidate_source_sha256"]),
        )
        object.__setattr__(
            instance,
            "candidate_unified_diff_sha256",
            str(candidate["unified_diff_sha256"]),
        )
        object.__setattr__(
            instance,
            "_protection_code_candidate",
            freeze_mapping(candidate, field="reviewable_protection_code_candidate"),
        )
        object.__setattr__(instance, "_factory_token", _REVIEW_FACTORY_TOKEN)
        instance._validate()
        return instance

    def _validate(self) -> None:
        if self._factory_token is not _REVIEW_FACTORY_TOKEN:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_review_origin_invalid"
            )
        _identifier(self.vault_id, code="runtime_protection_vault_review_invalid")
        _required_sha256(
            self.vault_instance_commitment,
            code="runtime_protection_vault_review_invalid",
            field="vault_instance_commitment",
        )
        _count(
            self.vault_sequence,
            code="runtime_protection_vault_review_invalid",
            minimum=1,
            maximum=_MAX_PROPOSALS_LIMIT,
        )
        _required_sha256(
            self.vault_entry_commitment,
            code="runtime_protection_vault_review_invalid",
            field="vault_entry_commitment",
        )
        proposal = _proposal_payload(self._proposal)
        candidate = _protection_code_candidate(
            self._protection_code_candidate,
            proposal=proposal,
        )
        if (
            self.candidate_commitment != candidate["candidate_commitment"]
            or self.candidate_source_sha256 != candidate["candidate_source_sha256"]
            or self.candidate_unified_diff_sha256 != candidate["unified_diff_sha256"]
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_review_candidate_invalid"
            )

    @property
    def proposal_id(self) -> str:
        return str(self._proposal["proposal_id"])

    @property
    def proposal_commitment(self) -> str:
        return str(self._proposal["proposal_commitment"])

    def proposal_summary(self) -> dict[str, Any]:
        """Return proposal material with explicit non-bearer provenance warnings."""

        self._validate()
        result = thaw_json(self._proposal)
        if not isinstance(result, dict):  # pragma: no cover - frozen mapping invariant
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_review_payload_invalid"
            )
        material = {
            "schema": RUNTIME_PROTECTION_PROPOSAL_REVIEW_MATERIAL_SCHEMA,
            "standalone_review_authenticated": False,
            "live_vault_readback_required": True,
            "proposal_commitment": self.proposal_commitment,
            "proposal": result,
        }
        assert_public_summary_safe(material)
        return material

    def protection_code_candidate_for_review(self) -> dict[str, Any]:
        """Return plaintext candidate plus explicit non-bearer provenance warnings."""

        self._validate()
        result = thaw_json(self._protection_code_candidate)
        if not isinstance(result, dict):  # pragma: no cover - frozen mapping invariant
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_review_candidate_invalid"
            )
        material = {
            "schema": RUNTIME_PROTECTION_CODE_CANDIDATE_REVIEW_MATERIAL_SCHEMA,
            "standalone_review_authenticated": False,
            "live_vault_readback_required": True,
            "candidate_commitment": self.candidate_commitment,
            "protection_code_candidate": result,
        }
        assert_public_summary_safe(material)
        return material

    def public_summary(self) -> dict[str, Any]:
        self._validate()
        summary = {
            "schema": RUNTIME_PROTECTION_PROPOSAL_REVIEW_SCHEMA,
            "vault_id": self.vault_id,
            "vault_instance_commitment": self.vault_instance_commitment,
            "vault_sequence": self.vault_sequence,
            "vault_entry_commitment": self.vault_entry_commitment,
            "proposal_id": self.proposal_id,
            "proposal_commitment": self.proposal_commitment,
            "candidate_commitment": self.candidate_commitment,
            "candidate_source_sha256": self.candidate_source_sha256,
            "candidate_unified_diff_sha256": self.candidate_unified_diff_sha256,
            "disposition": "HOLD",
            "review_required": True,
            "commitment_only": False,
            "proposal_commitment_only": True,
            "public_summary_commitment_only": True,
            "standalone_review_authenticated": False,
            "live_vault_readback_required": True,
            "candidate_review_material_available": True,
            "candidate_plaintext_in_public_summary": False,
            "code_generation_invoked": True,
            "external_model_invoked": False,
            "self_coder_invoked": False,
            "proposal_forge_invoked": False,
            "apply_authorized": False,
            "import_authorized": False,
            "execute_authorized": False,
            "release_authorized": False,
            "repository_mutation_authorized": False,
            "generated_code_execution_authorized": False,
            "external_action_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
            "legal_title_attested": False,
            "external_head_anchor_attested": False,
            "production_ready": False,
        }
        assert_public_summary_safe(summary)
        return summary


class SQLiteRuntimeProtectionProposalVaultV05:
    """Strict local encrypted review materialization for one intrusion ledger."""

    production_ready = False

    def __init__(
        self,
        path: Path,
        *,
        vault_id: str,
        source_ledger: SQLiteRuntimeIntrusionLedgerV04,
        proposal_key_provider: Callable[[], bytes | str | None],
        max_proposals: int = 64,
        max_packet_bytes: int = 1024 * 1024,
        append_timeout_ms: int = 1000,
    ) -> None:
        if not isinstance(path, Path) or not path.is_absolute() or str(path) == ":memory:":
            raise RuntimeProtectionProposalVaultError(
                "durable_runtime_protection_vault_sqlite_path_required"
            )
        resolved = path.resolve()
        if not resolved.parent.exists() or not resolved.parent.is_dir():
            raise RuntimeProtectionProposalVaultError(
                "durable_runtime_protection_vault_sqlite_parent_required"
            )
        if type(source_ledger) is not SQLiteRuntimeIntrusionLedgerV04:
            raise RuntimeProtectionProposalVaultError(
                "exact_runtime_intrusion_ledger_required"
            )
        source_path = getattr(source_ledger, "_path", None)
        if isinstance(source_path, Path) and source_path.resolve() == resolved:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_path_collision"
            )
        self._path = resolved
        self._path_existed = resolved.exists()
        self._path_initial_size = resolved.stat().st_size if self._path_existed else 0
        self._vault_id = _identifier(vault_id, code="runtime_protection_vault_id_invalid")
        self._source_ledger = source_ledger
        self._max_proposals = _count(
            max_proposals,
            code="runtime_protection_vault_capacity_invalid",
            minimum=1,
            maximum=_MAX_PROPOSALS_LIMIT,
        )
        self._max_packet_bytes = _count(
            max_packet_bytes,
            code="runtime_protection_vault_packet_bytes_invalid",
            minimum=_MIN_PACKET_BYTES,
            maximum=_MAX_PACKET_BYTES_LIMIT,
        )
        self._append_timeout_ms = _count(
            append_timeout_ms,
            code="runtime_protection_vault_append_timeout_invalid",
            minimum=1,
            maximum=_MAX_APPEND_TIMEOUT_MS,
        )
        source = self._source_identity()
        self._source_ledger_id = source[0]
        self._source_ledger_instance_commitment = source[1]
        self._source_max_violation_entries = source[2]
        self._lock = threading.RLock()
        self._closed = False
        self._terminal_failure_code: str | None = None
        self._vault_instance_commitment: str | None = None
        self._packet_key = bytearray()
        self._auth_key = bytearray()
        proposal_key = self._load_key(proposal_key_provider)
        connection: sqlite3.Connection | None = None
        try:
            connection = self._open_connection()
            self._connection = connection
            self._initialize_and_validate(proposal_key)
        except BaseException as exc:
            if connection is not None:
                connection.close()
            self._wipe_keys()
            self._closed = True
            error = _stable_error(
                exc,
                fallback="runtime_protection_vault_initialization_failed",
            )
            if error is exc:
                raise
            raise error from exc
        finally:
            proposal_key[:] = bytes(len(proposal_key))

    @staticmethod
    def _load_key(
        provider: Callable[[], bytes | str | None],
    ) -> bytearray:
        if not callable(provider):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_key_provider_invalid"
            )
        try:
            supplied = provider()
            if supplied is None:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_key_unavailable"
                )
            return bytearray(normalize_hnc_key_material(supplied))
        except RuntimeProtectionProposalVaultError:
            raise
        except BaseException as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_key_invalid"
            ) from exc

    def _wipe_keys(self) -> None:
        for retained in (self._packet_key, self._auth_key):
            retained[:] = bytes(len(retained))

    def _source_identity(self) -> tuple[str, str, int]:
        if (
            globals().get("_validate_source_ledger_code_identity")
            is not _EXACT_SOURCE_IDENTITY_GATE
            or _EXACT_SOURCE_IDENTITY_GATE.__code__
            is not _EXACT_SOURCE_IDENTITY_GATE_CODE
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_ledger_code_identity_invalid"
            )
        _EXACT_SOURCE_IDENTITY_GATE(self._source_ledger)
        if (
            type(self._source_ledger) is not SQLiteRuntimeIntrusionLedgerV04
            or vars(SQLiteRuntimeIntrusionLedgerV04).get("preflight")
            is not _EXACT_SOURCE_PREFLIGHT
            or _EXACT_SOURCE_PREFLIGHT.__code__ is not _EXACT_SOURCE_PREFLIGHT_CODE
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_ledger_code_identity_invalid"
            )
        try:
            summary = _EXACT_SOURCE_PREFLIGHT(self._source_ledger)
        except BaseException as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_ledger_unavailable"
            ) from exc
        if (
            summary.get("schema") != RUNTIME_INTRUSION_LEDGER_SCHEMA
            or not isinstance(summary.get("ledger_id"), str)
            or summary.get("keyed_genesis_authentication_ready") is not True
            or summary.get("keyed_entry_authentication_ready") is not True
            or summary.get("external_head_anchor_attested") is not False
            or summary.get("production_ready") is not False
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_ledger_identity_invalid"
            )
        instance = _required_sha256(
            summary.get("ledger_instance_commitment"),
            code="runtime_protection_vault_source_ledger_identity_invalid",
            field="source_ledger_instance_commitment",
        )
        source_max = _count(
            summary.get("max_violation_entries"),
            code="runtime_protection_vault_source_capacity_invalid",
            minimum=1,
            maximum=_MAX_SOURCE_VIOLATION_ENTRIES_FOR_VAULT,
        )
        return str(summary["ledger_id"]), instance, source_max

    def _required_instance(self) -> str:
        if self._vault_instance_commitment is None:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_instance_unavailable"
            )
        return self._vault_instance_commitment

    def _validate_pragmas(self, connection: sqlite3.Connection) -> None:
        values = {
            "journal_mode": connection.execute("PRAGMA journal_mode").fetchone(),
            "synchronous": connection.execute("PRAGMA synchronous").fetchone(),
            "foreign_keys": connection.execute("PRAGMA foreign_keys").fetchone(),
            "busy_timeout": connection.execute("PRAGMA busy_timeout").fetchone(),
            "trusted_schema": connection.execute("PRAGMA trusted_schema").fetchone(),
            "query_only": connection.execute("PRAGMA query_only").fetchone(),
            "writable_schema": connection.execute("PRAGMA writable_schema").fetchone(),
            "ignore_check_constraints": connection.execute(
                "PRAGMA ignore_check_constraints"
            ).fetchone(),
        }
        if (
            values["journal_mode"] is None
            or str(values["journal_mode"][0]).casefold() != "wal"
            or values["synchronous"] != (2,)
            or values["foreign_keys"] != (1,)
            or values["busy_timeout"] != (self._append_timeout_ms,)
            or values["trusted_schema"] != (0,)
            or values["query_only"] != (0,)
            or values["writable_schema"] != (0,)
            or values["ignore_check_constraints"] != (0,)
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_durability_pragmas_invalid"
            )

    def _open_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self._path),
            timeout=self._append_timeout_ms / 1000.0,
            isolation_level=None,
            check_same_thread=False,
        )
        try:
            journal = connection.execute("PRAGMA journal_mode=WAL").fetchone()
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={self._append_timeout_ms}")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA writable_schema=OFF")
            connection.execute("PRAGMA ignore_check_constraints=OFF")
            if journal is None or str(journal[0]).casefold() != "wal":
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_durability_pragmas_invalid"
                )
            self._validate_pragmas(connection)
            return connection
        except BaseException:
            connection.close()
            raise

    def _validate_schema(self) -> None:
        connection = self._connection
        quick_check = connection.execute("PRAGMA quick_check(1)").fetchall()
        schema_objects = frozenset(
            (str(row[0]), str(row[1]), str(row[2]))
            for row in connection.execute(
                "SELECT type, name, tbl_name FROM sqlite_schema"
            ).fetchall()
        )
        if quick_check != [("ok",)] or schema_objects != _EXPECTED_SCHEMA_OBJECTS:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_schema_invalid"
            )
        views = connection.execute(
            "SELECT COUNT(*) FROM sqlite_schema WHERE type='view'"
        ).fetchone()
        explicit_indexes = connection.execute(
            "SELECT COUNT(*) FROM sqlite_schema WHERE type='index' AND sql IS NOT NULL"
        ).fetchone()
        metadata_indexes = connection.execute(
            "PRAGMA index_list(runtime_protection_vault_metadata_v05)"
        ).fetchall()
        entry_indexes = connection.execute(
            "PRAGMA index_list(runtime_protection_vault_entries_v05)"
        ).fetchall()
        if (
            views != (0,)
            or explicit_indexes != (0,)
            or metadata_indexes
            or len(entry_indexes) != 5
            or any(
                len(row) < 5
                or row[2] != 1
                or row[3] != "u"
                or row[4] != 0
                for row in entry_indexes
            )
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_schema_invalid"
            )
        table_names = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        if table_names != {
            "runtime_protection_vault_metadata_v05",
            "runtime_protection_vault_entries_v05",
        }:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_schema_invalid"
            )
        metadata_columns = tuple(
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(runtime_protection_vault_metadata_v05)"
            ).fetchall()
        )
        entry_columns = tuple(
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(runtime_protection_vault_entries_v05)"
            ).fetchall()
        )
        if metadata_columns != _METADATA_COLUMNS or entry_columns != _ENTRY_COLUMNS:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_schema_invalid"
            )
        table_sql = {
            str(row[0]): _normalize_sql(row[1])
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_schema WHERE type='table' AND name IN (?,?)",
                (
                    "runtime_protection_vault_metadata_v05",
                    "runtime_protection_vault_entries_v05",
                ),
            ).fetchall()
        }
        if table_sql != {
            "runtime_protection_vault_metadata_v05": _normalize_sql(_METADATA_TABLE_SQL),
            "runtime_protection_vault_entries_v05": _normalize_sql(_ENTRY_TABLE_SQL),
        }:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_schema_invalid"
            )
        triggers = {
            str(row[0]): _normalize_sql(row[1])
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_schema WHERE type='trigger'"
            ).fetchall()
        }
        if triggers != {name: _normalize_sql(sql) for name, sql in _TRIGGER_SQL.items()}:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_schema_invalid"
            )

    def _initialize_and_validate(self, proposal_key: bytearray) -> None:
        connection = self._connection
        try:
            connection.execute("BEGIN IMMEDIATE")
            object_count = connection.execute(
                "SELECT COUNT(*) FROM sqlite_schema "
                "WHERE type IN ('table','index','trigger','view')"
            ).fetchone()
            if object_count == (0,):
                if self._path_existed and self._path_initial_size > 0:
                    raise RuntimeProtectionProposalVaultError(
                        "runtime_protection_vault_schema_invalid"
                    )
                connection.execute(_METADATA_TABLE_SQL)
                connection.execute(_ENTRY_TABLE_SQL)
                for sql in _TRIGGER_SQL.values():
                    connection.execute(sql)
            self._validate_schema()
            row = connection.execute(
                "SELECT singleton, schema, vault_id, vault_instance_commitment, "
                "source_ledger_id, source_ledger_instance_commitment, max_proposals, "
                "max_packet_bytes, append_timeout_ms, metadata_commitment, "
                "genesis_hmac_sha256 FROM runtime_protection_vault_metadata_v05 "
                "WHERE singleton=1"
            ).fetchone()
            if row is None:
                existing_entries = connection.execute(
                    "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
                ).fetchone()
                if existing_entries != (0,):
                    raise RuntimeProtectionProposalVaultError(
                        "runtime_protection_vault_metadata_missing"
                    )
                instance = domain_hash(
                    _INSTANCE_DOMAIN,
                    {"nonce": secrets.token_hex(32)},
                )
            else:
                instance = _required_sha256(
                    row[3],
                    code="runtime_protection_vault_instance_invalid",
                    field="vault_instance_commitment",
                )
            self._vault_instance_commitment = instance
            expected = _metadata_payload(
                vault_id=self._vault_id,
                vault_instance_commitment=instance,
                source_ledger_id=self._source_ledger_id,
                source_ledger_instance_commitment=self._source_ledger_instance_commitment,
                max_proposals=self._max_proposals,
                max_packet_bytes=self._max_packet_bytes,
                append_timeout_ms=self._append_timeout_ms,
            )
            packet_key, auth_key = _derive_keys(proposal_key, metadata=expected)
            self._packet_key = packet_key
            self._auth_key = auth_key
            metadata_commitment = domain_hash(
                RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
                expected,
            )
            genesis = _genesis_hmac(
                self._auth_key,
                metadata=expected,
                metadata_commitment=metadata_commitment,
            )
            expected_row = (
                1,
                RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
                self._vault_id,
                instance,
                self._source_ledger_id,
                self._source_ledger_instance_commitment,
                self._max_proposals,
                self._max_packet_bytes,
                self._append_timeout_ms,
                metadata_commitment,
                genesis,
            )
            if row is None:
                connection.execute(
                    "INSERT INTO runtime_protection_vault_metadata_v05 VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    expected_row,
                )
            elif tuple(row) != expected_row:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_metadata_authentication_invalid"
                )
            self._validated_entries()
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise

    def _validate_metadata_row(self) -> None:
        metadata = _metadata_payload(
            vault_id=self._vault_id,
            vault_instance_commitment=self._required_instance(),
            source_ledger_id=self._source_ledger_id,
            source_ledger_instance_commitment=self._source_ledger_instance_commitment,
            max_proposals=self._max_proposals,
            max_packet_bytes=self._max_packet_bytes,
            append_timeout_ms=self._append_timeout_ms,
        )
        metadata_commitment = domain_hash(
            RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
            metadata,
        )
        expected = (
            1,
            RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
            self._vault_id,
            self._required_instance(),
            self._source_ledger_id,
            self._source_ledger_instance_commitment,
            self._max_proposals,
            self._max_packet_bytes,
            self._append_timeout_ms,
            metadata_commitment,
            _genesis_hmac(
                self._auth_key,
                metadata=metadata,
                metadata_commitment=metadata_commitment,
            ),
        )
        row = self._connection.execute(
            "SELECT singleton, schema, vault_id, vault_instance_commitment, "
            "source_ledger_id, source_ledger_instance_commitment, max_proposals, "
            "max_packet_bytes, append_timeout_ms, metadata_commitment, "
            "genesis_hmac_sha256 FROM runtime_protection_vault_metadata_v05 "
            "WHERE singleton=1"
        ).fetchone()
        if row is None or tuple(row) != expected:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_metadata_authentication_invalid"
            )

    def _expected_aad(
        self,
        *,
        sequence: int,
        proposal_id: str,
        proposal_commitment: str,
        candidate_commitment: str,
        source_ledger_sequence: int,
        source_entry_commitment: str,
        source_projection_commitment: str,
        previous_entry_commitment: str,
        previous_entry_hmac_sha256: str,
        proposal_payload_sha256: str,
        proposal_payload_size_bytes: int,
    ) -> dict[str, Any]:
        return {
            "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_ENTRY_SCHEMA,
            "vault_schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
            "vault_id": self._vault_id,
            "vault_instance_commitment": self._required_instance(),
            "vault_sequence": sequence,
            "previous_entry_commitment": previous_entry_commitment,
            "previous_entry_hmac_sha256": previous_entry_hmac_sha256,
            "source_ledger_schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
            "source_ledger_id": self._source_ledger_id,
            "source_ledger_instance_commitment": self._source_ledger_instance_commitment,
            "source_ledger_sequence": source_ledger_sequence,
            "source_entry_commitment": source_entry_commitment,
            "source_projection_commitment": source_projection_commitment,
            "proposal_schema": INTRUSION_PROTECTION_PROPOSAL_SCHEMA,
            "proposal_id": proposal_id,
            "proposal_commitment": proposal_commitment,
            "review_envelope_schema": RUNTIME_PROTECTION_REVIEW_ENVELOPE_SCHEMA,
            "protection_code_candidate_schema": RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA,
            "candidate_commitment": candidate_commitment,
            "proposal_payload_sha256": proposal_payload_sha256,
            "proposal_payload_size_bytes": proposal_payload_size_bytes,
            "disposition": "HOLD",
            "review_required": True,
            "commitment_only": True,
            "code_generation_invoked": True,
            "external_model_invoked": False,
            "self_coder_invoked": False,
            "proposal_forge_invoked": False,
            "apply_authorized": False,
            "import_authorized": False,
            "execute_authorized": False,
            "release_authorized": False,
            "repository_mutation_authorized": False,
            "generated_code_execution_authorized": False,
            "release_broker_invoked": False,
            "magic_star_invoked": False,
            "external_action_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
            "production_ready": False,
        }

    def _build_row(
        self,
        *,
        sequence: int,
        proposal: AureonIntrusionProtectionWorkProposalV04,
        previous_entry_commitment: str,
        previous_entry_hmac_sha256: str,
        terminal_after_append: bool,
    ) -> tuple[Any, ...]:
        payload = _proposal_payload(proposal.public_summary())
        payload_bytes = canonical_json_bytes(payload)
        if (
            globals().get("_render_exact_protection_code_candidate")
            is not _EXACT_CANDIDATE_RENDERER_GATE
            or _EXACT_CANDIDATE_RENDERER_GATE.__code__
            is not _EXACT_CANDIDATE_RENDERER_GATE_CODE
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_candidate_renderer_identity_invalid"
            )
        candidate = _EXACT_CANDIDATE_RENDERER_GATE(payload)
        candidate_commitment = str(candidate["candidate_commitment"])
        envelope_bytes = canonical_json_bytes(
            {
                "schema": RUNTIME_PROTECTION_REVIEW_ENVELOPE_SCHEMA,
                "proposal": payload,
                "protection_code_candidate": candidate,
            }
        )
        evidence = payload.get("intrusion_evidence")
        if not isinstance(evidence, Mapping):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_proposal_evidence_invalid"
            )
        source_sequence = _count(
            evidence.get("ledger_sequence"),
            code="runtime_protection_vault_proposal_evidence_invalid",
            minimum=2,
            maximum=2**63 - 1,
        )
        source_entry = _required_sha256(
            evidence.get("entry_commitment"),
            code="runtime_protection_vault_proposal_evidence_invalid",
            field="source_entry_commitment",
        )
        projection_commitment = _required_sha256(
            evidence.get("projection_commitment"),
            code="runtime_protection_vault_proposal_evidence_invalid",
            field="source_projection_commitment",
        )
        if (
            evidence.get("ledger_id") != self._source_ledger_id
            or evidence.get("ledger_instance_commitment")
            != self._source_ledger_instance_commitment
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_join_invalid"
            )
        payload_sha = _sha256(payload_bytes)
        aad = self._expected_aad(
            sequence=sequence,
            proposal_id=proposal.proposal_id,
            proposal_commitment=proposal.proposal_commitment,
            candidate_commitment=candidate_commitment,
            source_ledger_sequence=source_sequence,
            source_entry_commitment=source_entry,
            source_projection_commitment=projection_commitment,
            previous_entry_commitment=previous_entry_commitment,
            previous_entry_hmac_sha256=previous_entry_hmac_sha256,
            proposal_payload_sha256=payload_sha,
            proposal_payload_size_bytes=len(payload_bytes),
        )
        try:
            packet = build_hnc_quantum_packet(
                envelope_bytes,
                bytes(self._packet_key),
                purpose=RUNTIME_PROTECTION_PROPOSAL_PURPOSE,
                operator_aad=aad,
                hnc_context={
                    "vault_schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
                    "vault_instance_commitment": self._required_instance(),
                    "source_ledger_instance_commitment": self._source_ledger_instance_commitment,
                },
            )
            packet_bytes = canonical_hnc_json_bytes(
                packet,
                max_bytes=self._max_packet_bytes,
            )
        except BaseException as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_hnc_seal_failed"
            ) from exc
        if len(packet_bytes) > self._max_packet_bytes:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_packet_capacity_exceeded"
            )
        packet_sha = _sha256(packet_bytes)
        recorded_at = datetime.now(UTC).isoformat()
        commitment_payload = {
            "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_ENTRY_SCHEMA,
            "vault_id": self._vault_id,
            "vault_instance_commitment": self._required_instance(),
            "sequence": sequence,
            "proposal_id": proposal.proposal_id,
            "proposal_commitment": proposal.proposal_commitment,
            "candidate_commitment": candidate_commitment,
            "source_ledger_id": self._source_ledger_id,
            "source_ledger_instance_commitment": self._source_ledger_instance_commitment,
            "source_ledger_sequence": source_sequence,
            "source_entry_commitment": source_entry,
            "source_projection_commitment": projection_commitment,
            "previous_entry_commitment": previous_entry_commitment,
            "previous_entry_hmac_sha256": previous_entry_hmac_sha256,
            "proposal_packet_sha256": packet_sha,
            "proposal_payload_sha256": payload_sha,
            "proposal_payload_size_bytes": len(payload_bytes),
            "recorded_at": recorded_at,
            "terminal_after_append": terminal_after_append,
        }
        entry_commitment = domain_hash(
            _ENTRY_COMMITMENT_DOMAIN,
            commitment_payload,
        )
        fields: tuple[Any, ...] = (
            sequence,
            proposal.proposal_id,
            proposal.proposal_commitment,
            candidate_commitment,
            source_sequence,
            source_entry,
            projection_commitment,
            previous_entry_commitment,
            previous_entry_hmac_sha256,
            packet_bytes,
            packet_sha,
            payload_sha,
            len(payload_bytes),
            recorded_at,
            int(terminal_after_append),
            entry_commitment,
        )
        entry_hmac = _entry_hmac(
            self._auth_key,
            vault_id=self._vault_id,
            fields=fields,
        )
        return (*fields, entry_hmac)

    def _proposal_from_source(
        self,
        *,
        sequence: int,
        entry_commitment: str,
    ) -> AureonIntrusionProtectionWorkProposalV04:
        if (
            globals().get("_validate_source_ledger_code_identity")
            is not _EXACT_SOURCE_IDENTITY_GATE
            or _EXACT_SOURCE_IDENTITY_GATE.__code__
            is not _EXACT_SOURCE_IDENTITY_GATE_CODE
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_ledger_code_identity_invalid"
            )
        _EXACT_SOURCE_IDENTITY_GATE(self._source_ledger)
        if (
            _EXACT_PROPOSAL_BUILDER.__code__ is not _EXACT_PROPOSAL_BUILDER_CODE
            or type(self._source_ledger) is not SQLiteRuntimeIntrusionLedgerV04
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_code_identity_invalid"
            )
        try:
            proposal = _EXACT_PROPOSAL_BUILDER(
                ledger=self._source_ledger,
                sequence=sequence,
                entry_commitment=entry_commitment,
            )
        except BaseException as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_authentication_failed"
            ) from exc
        if type(proposal) is not AureonIntrusionProtectionWorkProposalV04:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_proposal_type_invalid"
            )
        return proposal

    def _validate_row(
        self,
        row: tuple[Any, ...],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        if len(row) != len(_ENTRY_COLUMNS):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_entry_shape_invalid"
            )
        values = dict(zip(_ENTRY_COLUMNS, row, strict=True))
        sequence = _count(
            values["sequence"],
            code="runtime_protection_vault_entry_invalid",
            minimum=1,
            maximum=self._max_proposals,
        )
        proposal_id = _identifier(
            values["proposal_id"],
            code="runtime_protection_vault_entry_invalid",
        )
        proposal_commitment = _required_sha256(
            values["proposal_commitment"],
            code="runtime_protection_vault_entry_invalid",
            field="proposal_commitment",
        )
        candidate_commitment = _required_sha256(
            values["candidate_commitment"],
            code="runtime_protection_vault_entry_invalid",
            field="candidate_commitment",
        )
        source_sequence = _count(
            values["source_ledger_sequence"],
            code="runtime_protection_vault_entry_invalid",
            minimum=2,
            maximum=2**63 - 1,
        )
        source_entry = _required_sha256(
            values["source_entry_commitment"],
            code="runtime_protection_vault_entry_invalid",
            field="source_entry_commitment",
        )
        source_projection = _required_sha256(
            values["source_projection_commitment"],
            code="runtime_protection_vault_entry_invalid",
            field="source_projection_commitment",
        )
        previous = _required_sha256(
            values["previous_entry_commitment"],
            code="runtime_protection_vault_entry_invalid",
            field="previous_entry_commitment",
        )
        previous_hmac = _required_sha256(
            values["previous_entry_hmac_sha256"],
            code="runtime_protection_vault_entry_invalid",
            field="previous_entry_hmac_sha256",
        )
        packet_bytes = values["proposal_packet_json"]
        if not isinstance(packet_bytes, bytes) or not 1 <= len(packet_bytes) <= self._max_packet_bytes:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_packet_invalid"
            )
        packet_sha = _required_sha256(
            values["proposal_packet_sha256"],
            code="runtime_protection_vault_packet_invalid",
            field="proposal_packet_sha256",
        )
        payload_sha = _required_sha256(
            values["proposal_payload_sha256"],
            code="runtime_protection_vault_entry_invalid",
            field="proposal_payload_sha256",
        )
        payload_size = _count(
            values["proposal_payload_size_bytes"],
            code="runtime_protection_vault_entry_invalid",
            minimum=1,
            maximum=4 * 1024 * 1024,
        )
        fields = tuple(row[:-1])
        supplied_hmac = _required_sha256(
            row[-1],
            code="runtime_protection_vault_entry_authentication_invalid",
            field="entry_hmac_sha256",
        )
        expected_hmac = _entry_hmac(
            self._auth_key,
            vault_id=self._vault_id,
            fields=fields,
        )
        if not hmac.compare_digest(supplied_hmac, expected_hmac):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_entry_authentication_invalid"
            )
        if _sha256(packet_bytes) != packet_sha:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_packet_invalid"
            )
        packet = _decode_hnc_packet_bytes(
            packet_bytes,
            maximum_bytes=self._max_packet_bytes,
        )
        validation = validate_hnc_packet_contract(packet)
        if validation.get("valid") is not True:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_packet_invalid"
            )
        expected_aad = self._expected_aad(
            sequence=sequence,
            proposal_id=proposal_id,
            proposal_commitment=proposal_commitment,
            candidate_commitment=candidate_commitment,
            source_ledger_sequence=source_sequence,
            source_entry_commitment=source_entry,
            source_projection_commitment=source_projection,
            previous_entry_commitment=previous,
            previous_entry_hmac_sha256=previous_hmac,
            proposal_payload_sha256=payload_sha,
            proposal_payload_size_bytes=payload_size,
        )
        try:
            decoded = decode_hnc_quantum_packet(
                packet,
                bytes(self._packet_key),
                expected_purpose=RUNTIME_PROTECTION_PROPOSAL_PURPOSE,
                expected_operator_aad=expected_aad,
            )
        except HNCPacketError as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_packet_authentication_invalid"
            ) from exc
        try:
            envelope = decode_canonical_json(
                decoded.plaintext,
                require_mapping=True,
                max_bytes=4 * 1024 * 1024,
            )
        except BaseException as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_payload_authentication_invalid"
            ) from exc
        if (
            not isinstance(envelope, dict)
            or canonical_json_bytes(envelope) != decoded.plaintext
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_review_envelope_invalid"
            )
        parsed, candidate = _review_envelope(envelope)
        parsed_payload_bytes = canonical_json_bytes(parsed)
        if (
            len(parsed_payload_bytes) != payload_size
            or _sha256(parsed_payload_bytes) != payload_sha
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_payload_authentication_invalid"
            )
        if candidate["candidate_commitment"] != candidate_commitment:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_candidate_commitment_invalid"
            )
        evidence = parsed.get("intrusion_evidence")
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("ledger_id") != self._source_ledger_id
            or evidence.get("ledger_instance_commitment")
            != self._source_ledger_instance_commitment
            or evidence.get("ledger_sequence") != source_sequence
            or evidence.get("entry_commitment") != source_entry
            or evidence.get("projection_commitment") != source_projection
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_source_join_invalid"
            )
        recorded_at = values["recorded_at"]
        try:
            recorded = datetime.fromisoformat(recorded_at)
        except (TypeError, ValueError) as exc:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_entry_invalid"
            ) from exc
        if recorded.tzinfo is None or recorded.utcoffset() != UTC.utcoffset(recorded):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_entry_invalid"
            )
        terminal_raw = values["terminal_after_append"]
        if terminal_raw not in (0, 1) or type(terminal_raw) is not int:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_entry_invalid"
            )
        commitment_payload = {
            "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_ENTRY_SCHEMA,
            "vault_id": self._vault_id,
            "vault_instance_commitment": self._required_instance(),
            "sequence": sequence,
            "proposal_id": proposal_id,
            "proposal_commitment": proposal_commitment,
            "candidate_commitment": candidate_commitment,
            "source_ledger_id": self._source_ledger_id,
            "source_ledger_instance_commitment": self._source_ledger_instance_commitment,
            "source_ledger_sequence": source_sequence,
            "source_entry_commitment": source_entry,
            "source_projection_commitment": source_projection,
            "previous_entry_commitment": previous,
            "previous_entry_hmac_sha256": previous_hmac,
            "proposal_packet_sha256": packet_sha,
            "proposal_payload_sha256": payload_sha,
            "proposal_payload_size_bytes": payload_size,
            "recorded_at": recorded_at,
            "terminal_after_append": bool(terminal_raw),
        }
        expected_commitment = domain_hash(
            _ENTRY_COMMITMENT_DOMAIN,
            commitment_payload,
        )
        entry_commitment = _required_sha256(
            values["entry_commitment"],
            code="runtime_protection_vault_entry_invalid",
            field="entry_commitment",
        )
        if entry_commitment != expected_commitment:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_entry_commitment_invalid"
            )
        values["terminal_after_append"] = bool(terminal_raw)
        values["candidate_source_sha256"] = candidate["candidate_source_sha256"]
        values["candidate_unified_diff_sha256"] = candidate["unified_diff_sha256"]
        return values, parsed, candidate

    def _validated_entries(
        self,
    ) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
        self._validate_metadata_row()
        census = self._connection.execute(
            "SELECT COUNT(*), COALESCE(MAX(length(proposal_packet_json)),0), "
            "COALESCE(SUM(length(proposal_packet_json)),0), "
            "COALESCE(MAX(length(proposal_id)),0), COALESCE(MAX(length(recorded_at)),0), "
            "COALESCE(SUM(CASE WHEN "
            "typeof(sequence)!='integer' OR typeof(source_ledger_sequence)!='integer' OR "
            "typeof(proposal_packet_json)!='blob' OR "
            "typeof(proposal_payload_size_bytes)!='integer' OR "
            "typeof(terminal_after_append)!='integer' OR "
            "length(proposal_commitment)!=64 OR length(candidate_commitment)!=64 OR "
            "length(source_entry_commitment)!=64 OR "
            "length(source_projection_commitment)!=64 OR "
            "length(previous_entry_commitment)!=64 OR "
            "length(previous_entry_hmac_sha256)!=64 OR "
            "length(proposal_packet_sha256)!=64 OR "
            "length(proposal_payload_sha256)!=64 OR "
            "length(entry_commitment)!=64 OR length(entry_hmac_sha256)!=64 "
            "THEN 1 ELSE 0 END),0) "
            "FROM runtime_protection_vault_entries_v05"
        ).fetchone()
        if (
            census is None
            or len(census) != 6
            or type(census[0]) is not int
            or type(census[1]) is not int
            or type(census[2]) is not int
            or type(census[3]) is not int
            or type(census[4]) is not int
            or type(census[5]) is not int
            or census[0] > self._max_proposals
            or census[1] > self._max_packet_bytes
            or census[2] > self._max_proposals * self._max_packet_bytes
            or census[3] > 128
            or census[4] > 64
            or census[5] != 0
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_bounded_census_invalid"
            )
        entries: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
        previous = _ZERO_SHA256
        previous_hmac = _ZERO_SHA256
        terminal_seen = False
        rows = self._connection.execute(
            "SELECT "
            + ",".join(_ENTRY_COLUMNS)
            + " FROM runtime_protection_vault_entries_v05 ORDER BY sequence"
        )
        for expected_sequence, raw in enumerate(rows, start=1):
            values, payload, candidate = self._validate_row(tuple(raw))
            if (
                values["sequence"] != expected_sequence
                or values["previous_entry_commitment"] != previous
                or values["previous_entry_hmac_sha256"] != previous_hmac
                or terminal_seen
            ):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_chain_invalid"
                )
            terminal_seen = values["terminal_after_append"] is True
            previous = str(values["entry_commitment"])
            previous_hmac = str(values["entry_hmac_sha256"])
            entries.append((values, payload, candidate))
        if entries:
            if (
                globals().get("_validate_source_ledger_code_identity")
                is not _EXACT_SOURCE_IDENTITY_GATE
                or _EXACT_SOURCE_IDENTITY_GATE.__code__
                is not _EXACT_SOURCE_IDENTITY_GATE_CODE
            ):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_source_ledger_code_identity_invalid"
                )
            _EXACT_SOURCE_IDENTITY_GATE(self._source_ledger)
            if (
                vars(SQLiteRuntimeIntrusionLedgerV04).get(
                    "authenticated_violation_projections"
                )
                is not _EXACT_SOURCE_BATCH_PROJECTION
                or _EXACT_SOURCE_BATCH_PROJECTION.__code__
                is not _EXACT_SOURCE_BATCH_PROJECTION_CODE
            ):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_source_ledger_code_identity_invalid"
                )
            selections = tuple(
                (
                    int(values["source_ledger_sequence"]),
                    str(values["source_entry_commitment"]),
                )
                for values, _payload, _candidate in entries
            )
            try:
                projections = _EXACT_SOURCE_BATCH_PROJECTION(
                    self._source_ledger,
                    selections=selections,
                )
            except BaseException as exc:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_source_authentication_failed"
                ) from exc
            if len(projections) != len(entries):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_source_join_invalid"
                )
            for (_values, payload, _candidate), projection in zip(
                entries,
                projections,
                strict=True,
            ):
                evidence = payload.get("intrusion_evidence")
                if not isinstance(evidence, Mapping) or dict(evidence) != projection:
                    raise RuntimeProtectionProposalVaultError(
                        "runtime_protection_vault_source_join_invalid"
                    )
        if bool(entries) and (len(entries) == self._max_proposals) != terminal_seen:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_terminal_state_invalid"
            )
        return entries

    def _receipt(self, entry: Mapping[str, Any]) -> ProtectionProposalVaultReceiptV05:
        return ProtectionProposalVaultReceiptV05._issue(
            factory_token=_RECEIPT_FACTORY_TOKEN,
            vault_id=self._vault_id,
            vault_instance_commitment=self._required_instance(),
            sequence=int(entry["sequence"]),
            proposal_id=str(entry["proposal_id"]),
            proposal_commitment=str(entry["proposal_commitment"]),
            candidate_commitment=str(entry["candidate_commitment"]),
            candidate_source_sha256=str(entry["candidate_source_sha256"]),
            candidate_unified_diff_sha256=str(
                entry["candidate_unified_diff_sha256"]
            ),
            source_ledger_id=self._source_ledger_id,
            source_ledger_instance_commitment=self._source_ledger_instance_commitment,
            source_ledger_sequence=int(entry["source_ledger_sequence"]),
            source_entry_commitment=str(entry["source_entry_commitment"]),
            source_projection_commitment=str(entry["source_projection_commitment"]),
            proposal_packet_sha256=str(entry["proposal_packet_sha256"]),
            proposal_payload_sha256=str(entry["proposal_payload_sha256"]),
            recorded_at=str(entry["recorded_at"]),
            entry_commitment=str(entry["entry_commitment"]),
            terminal_after_append=entry["terminal_after_append"] is True,
        )

    def verify_receipt(
        self,
        receipt: ProtectionProposalVaultReceiptV05,
    ) -> dict[str, Any]:
        """Verify a receipt against the live authenticated vault and source.

        A receipt object is intentionally not a bearer proof.  Only this exact
        read-back can truthfully attest persistence and keyed authentication.
        """

        if type(receipt) is not ProtectionProposalVaultReceiptV05:
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_receipt_type_invalid"
            )
        receipt._validate()
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeProtectionProposalVaultError("runtime_protection_vault_busy")
        try:
            if self._closed:
                raise RuntimeProtectionProposalVaultError("runtime_protection_vault_closed")
            source_id, source_instance, source_max = self._source_identity()
            if (
                source_id != self._source_ledger_id
                or source_instance != self._source_ledger_instance_commitment
                or source_max != self._source_max_violation_entries
            ):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_source_ledger_identity_changed"
                )
            self._validate_pragmas(self._connection)
            self._connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            self._connection.execute("COMMIT")
            matches = [
                values
                for values, _payload, _candidate in entries
                if values["sequence"] == receipt.sequence
                and values["entry_commitment"] == receipt.entry_commitment
                and values["proposal_commitment"] == receipt.proposal_commitment
                and values["candidate_commitment"] == receipt.candidate_commitment
            ]
            if len(matches) != 1 or self._receipt(matches[0]) != receipt:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_receipt_verification_failed"
                )
            summary = {
                **receipt.public_summary(),
                "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_VERIFIED_RECEIPT_SCHEMA,
                "standalone_receipt_authenticated": False,
                "live_vault_verification_required": False,
                "live_vault_verification_performed": True,
                "durability_readback": True,
                "keyed_entry_authenticated": True,
                "encrypted_hnc_packet_persisted": True,
                "encrypted_hnc_packet_authenticated": True,
                "encrypted_protection_code_candidate_persisted": True,
                "encrypted_protection_code_candidate_authenticated": True,
                "technical_provenance_recorded": True,
                "duplicate_vault_absence_attested": False,
                "external_head_anchor_attested": False,
                "production_ready": False,
            }
            assert_public_summary_safe(summary)
            return summary
        except BaseException as exc:
            if self._connection.in_transaction:
                try:
                    self._connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(
                exc,
                fallback="runtime_protection_vault_receipt_verification_failed",
            )
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def preflight(self) -> dict[str, Any]:
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeProtectionProposalVaultError("runtime_protection_vault_busy")
        try:
            if self._closed:
                raise RuntimeProtectionProposalVaultError("runtime_protection_vault_closed")
            source_id, source_instance, source_max = self._source_identity()
            if (
                source_id != self._source_ledger_id
                or source_instance != self._source_ledger_instance_commitment
                or source_max != self._source_max_violation_entries
            ):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_source_ledger_identity_changed"
                )
            self._validate_pragmas(self._connection)
            self._connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            self._connection.execute("COMMIT")
            terminal = self._terminal_failure_code is not None or len(entries) == self._max_proposals
            summary = {
                "schema": RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
                "vault_id": self._vault_id,
                "vault_instance_commitment": self._required_instance(),
                "source_ledger_id": self._source_ledger_id,
                "source_ledger_instance_commitment": self._source_ledger_instance_commitment,
                "source_max_violation_entries": self._source_max_violation_entries,
                "source_capacity_bound_enforced": True,
                "source_authentication_scaling": "O(source_entries+vault_entries)",
                "ready": not terminal,
                "reason_code": self._terminal_failure_code or ("terminal" if terminal else "ready"),
                "entry_count": len(entries),
                "max_proposals": self._max_proposals,
                "remaining_proposal_capacity": max(0, self._max_proposals - len(entries)),
                "head_entry_commitment": (
                    str(entries[-1][0]["entry_commitment"]) if entries else _ZERO_SHA256
                ),
                "preopened_connection": True,
                "append_only_schema": True,
                "durability_readback": True,
                "keyed_genesis_authentication_ready": True,
                "keyed_entry_authentication_ready": True,
                "current_open_key_matches_authenticated_metadata": True,
                "key_provider_restart_continuity_attested": False,
                "independent_key_custody_attested": False,
                "future_restart_decryption_attested": False,
                "encrypted_hnc_packet_persistence_ready": True,
                "encrypted_hnc_packets_persisted": bool(entries),
                "encrypted_hnc_packets_authenticated": bool(entries),
                "encrypted_protection_code_candidate_persistence_ready": True,
                "encrypted_protection_code_candidates_persisted": bool(entries),
                "encrypted_protection_code_candidates_authenticated": bool(entries),
                "proposal_owner": "Aureon",
                "single_owner_route_configured": True,
                "single_owner_route_externally_attested": False,
                "duplicate_queue_created_by_this_operation": False,
                "duplicate_vault_absence_attested": False,
                "raw_intrusion_material_retained": False,
                "raw_source_request_retained": False,
                "raw_unified_diff_persisted_outside_encrypted_vault_packet": False,
                "code_generation_invoked": bool(entries),
                "external_model_invoked": False,
                "self_coder_invoked": False,
                "proposal_forge_invoked": False,
                "apply_authorized": False,
                "import_authorized": False,
                "execute_authorized": False,
                "release_authorized": False,
                "repository_mutation_authorized": False,
                "generated_code_execution_authorized": False,
                "release_broker_invoked": False,
                "magic_star_invoked": False,
                "external_action_authorized": False,
                "action_eligible": False,
                "economic_eligible": False,
                "legal_title_attested": False,
                "external_head_anchor_attested": False,
                "production_ready": False,
            }
            assert_public_summary_safe(summary)
            return summary
        except BaseException as exc:
            if self._connection.in_transaction:
                try:
                    self._connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(exc, fallback="runtime_protection_vault_preflight_failed")
            if (
                self._terminal_failure_code is None
                and error.code not in _NON_TERMINAL_SEAL_ERRORS
            ):
                self._terminal_failure_code = error.code
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def seal_from_intrusion(
        self,
        *,
        source_sequence: int,
        source_entry_commitment: str,
    ) -> ProtectionProposalVaultReceiptV05:
        sequence = _count(
            source_sequence,
            code="runtime_protection_vault_source_sequence_invalid",
            minimum=2,
            maximum=2**63 - 1,
        )
        source_entry = _required_sha256(
            source_entry_commitment,
            code="runtime_protection_vault_source_entry_commitment_invalid",
            field="source_entry_commitment",
        )
        if (
            type(self) is not SQLiteRuntimeProtectionProposalVaultV05
            or "_proposal_from_source" in vars(self)
            or vars(SQLiteRuntimeProtectionProposalVaultV05).get(
                "_proposal_from_source"
            )
            is not _EXACT_VAULT_PROPOSAL_RESOLVER
            or _EXACT_VAULT_PROPOSAL_RESOLVER.__code__
            is not _EXACT_VAULT_PROPOSAL_RESOLVER_CODE
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_proposal_resolver_identity_invalid"
            )
        proposal = _EXACT_VAULT_PROPOSAL_RESOLVER(
            self,
            sequence=sequence,
            entry_commitment=source_entry,
        )
        if (
            globals().get("_render_exact_protection_code_candidate")
            is not _EXACT_CANDIDATE_RENDERER_GATE
            or _EXACT_CANDIDATE_RENDERER_GATE.__code__
            is not _EXACT_CANDIDATE_RENDERER_GATE_CODE
        ):
            raise RuntimeProtectionProposalVaultError(
                "runtime_protection_vault_candidate_renderer_identity_invalid"
            )
        candidate = _EXACT_CANDIDATE_RENDERER_GATE(proposal.public_summary())
        candidate_commitment = str(candidate["candidate_commitment"])
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeProtectionProposalVaultError("runtime_protection_vault_busy")
        try:
            if self._closed:
                raise RuntimeProtectionProposalVaultError("runtime_protection_vault_closed")
            if self._terminal_failure_code is not None:
                raise RuntimeProtectionProposalVaultError(self._terminal_failure_code)
            self._validate_pragmas(self._connection)
            self._connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            matches = [
                item
                for item in entries
                if item[0]["proposal_commitment"] == proposal.proposal_commitment
                or item[0]["source_ledger_sequence"] == sequence
                or item[0]["source_entry_commitment"] == source_entry
            ]
            if matches:
                exact = matches[0][0]
                if (
                    len(matches) != 1
                    or exact["proposal_id"] != proposal.proposal_id
                    or exact["proposal_commitment"] != proposal.proposal_commitment
                    or exact["candidate_commitment"] != candidate_commitment
                    or exact["source_ledger_sequence"] != sequence
                    or exact["source_entry_commitment"] != source_entry
                ):
                    raise RuntimeProtectionProposalVaultError(
                        "runtime_protection_vault_replay_conflict"
                    )
                self._connection.execute("COMMIT")
                return self._receipt(exact)
            if len(entries) >= self._max_proposals:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_capacity_exhausted"
                )
            vault_sequence = len(entries) + 1
            previous = str(entries[-1][0]["entry_commitment"]) if entries else _ZERO_SHA256
            previous_hmac = str(entries[-1][0]["entry_hmac_sha256"]) if entries else _ZERO_SHA256
            row = self._build_row(
                sequence=vault_sequence,
                proposal=proposal,
                previous_entry_commitment=previous,
                previous_entry_hmac_sha256=previous_hmac,
                terminal_after_append=vault_sequence == self._max_proposals,
            )
            self._connection.execute(
                "INSERT INTO runtime_protection_vault_entries_v05 VALUES ("
                + ",".join("?" for _ in _ENTRY_COLUMNS)
                + ")",
                row,
            )
            self._connection.execute("COMMIT")
            self._connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            readback = self._validated_entries()
            self._connection.execute("COMMIT")
            if len(readback) != vault_sequence:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_durability_readback_failed"
                )
            exact = readback[-1][0]
            if (
                exact["proposal_commitment"] != proposal.proposal_commitment
                or exact["candidate_commitment"] != candidate_commitment
                or exact["source_ledger_sequence"] != sequence
                or exact["source_entry_commitment"] != source_entry
            ):
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_durability_readback_failed"
                )
            return self._receipt(exact)
        except BaseException as exc:
            if self._connection.in_transaction:
                try:
                    self._connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(exc, fallback="runtime_protection_vault_seal_failed")
            if (
                self._terminal_failure_code is None
                and error.code not in _NON_TERMINAL_SEAL_ERRORS
            ):
                self._terminal_failure_code = error.code
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def read_for_review(
        self,
        *,
        vault_sequence: int,
        vault_entry_commitment: str,
        proposal_commitment: str,
        candidate_commitment: str,
    ) -> ReviewableProtectionProposalV05:
        sequence = _count(
            vault_sequence,
            code="runtime_protection_vault_review_selector_invalid",
            minimum=1,
            maximum=self._max_proposals,
        )
        entry_commitment = _required_sha256(
            vault_entry_commitment,
            code="runtime_protection_vault_review_selector_invalid",
            field="vault_entry_commitment",
        )
        proposal_hash = _required_sha256(
            proposal_commitment,
            code="runtime_protection_vault_review_selector_invalid",
            field="proposal_commitment",
        )
        candidate_hash = _required_sha256(
            candidate_commitment,
            code="runtime_protection_vault_review_selector_invalid",
            field="candidate_commitment",
        )
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeProtectionProposalVaultError("runtime_protection_vault_busy")
        try:
            if self._closed:
                raise RuntimeProtectionProposalVaultError("runtime_protection_vault_closed")
            if self._terminal_failure_code is not None:
                raise RuntimeProtectionProposalVaultError(self._terminal_failure_code)
            self._validate_pragmas(self._connection)
            self._connection.execute("BEGIN IMMEDIATE")
            self._validate_schema()
            entries = self._validated_entries()
            self._connection.execute("COMMIT")
            selected = [
                item
                for item in entries
                if item[0]["sequence"] == sequence
                and item[0]["entry_commitment"] == entry_commitment
                and item[0]["proposal_commitment"] == proposal_hash
                and item[0]["candidate_commitment"] == candidate_hash
            ]
            if len(selected) != 1:
                raise RuntimeProtectionProposalVaultError(
                    "runtime_protection_vault_review_selector_mismatch"
                )
            values, payload, candidate = selected[0]
            return ReviewableProtectionProposalV05._issue(
                factory_token=_REVIEW_FACTORY_TOKEN,
                vault_id=self._vault_id,
                vault_instance_commitment=self._required_instance(),
                vault_sequence=sequence,
                vault_entry_commitment=str(values["entry_commitment"]),
                proposal=payload,
                protection_code_candidate=candidate,
            )
        except BaseException as exc:
            if self._connection.in_transaction:
                try:
                    self._connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            error = _stable_error(exc, fallback="runtime_protection_vault_review_failed")
            if error is exc:
                raise
            raise error from exc
        finally:
            self._lock.release()

    def close(self) -> None:
        acquired = self._lock.acquire(timeout=self._append_timeout_ms / 1000.0)
        if not acquired:
            raise RuntimeProtectionProposalVaultError("runtime_protection_vault_busy")
        try:
            if not self._closed:
                try:
                    self._connection.close()
                except BaseException as exc:
                    raise RuntimeProtectionProposalVaultError(
                        "runtime_protection_vault_close_failed"
                    ) from exc
                finally:
                    self._wipe_keys()
                    self._closed = True
        finally:
            self._lock.release()

    def __enter__(self) -> SQLiteRuntimeProtectionProposalVaultV05:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()


_EXACT_VAULT_PROPOSAL_RESOLVER: Final = (
    SQLiteRuntimeProtectionProposalVaultV05._proposal_from_source
)
_EXACT_VAULT_PROPOSAL_RESOLVER_CODE: Final = (
    _EXACT_VAULT_PROPOSAL_RESOLVER.__code__
)


__all__ = [
    "RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA",
    "RUNTIME_PROTECTION_CODE_CANDIDATE_REVIEW_MATERIAL_SCHEMA",
    "RUNTIME_PROTECTION_PROPOSAL_PURPOSE",
    "RUNTIME_PROTECTION_PROPOSAL_REVIEW_SCHEMA",
    "RUNTIME_PROTECTION_PROPOSAL_REVIEW_MATERIAL_SCHEMA",
    "RUNTIME_PROTECTION_PROPOSAL_VAULT_ENTRY_SCHEMA",
    "RUNTIME_PROTECTION_PROPOSAL_VAULT_RECEIPT_SCHEMA",
    "RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA",
    "RUNTIME_PROTECTION_PROPOSAL_VAULT_VERIFIED_RECEIPT_SCHEMA",
    "RUNTIME_PROTECTION_REVIEW_ENVELOPE_SCHEMA",
    "ProtectionProposalVaultReceiptV05",
    "ReviewableProtectionProposalV05",
    "RuntimeProtectionProposalVaultError",
    "SQLiteRuntimeProtectionProposalVaultV05",
]
