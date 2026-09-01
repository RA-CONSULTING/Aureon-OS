"""Commitment-only bridge from authenticated runtime HNC evidence to review work.

This module creates no queue, patch, source request, subprocess, or external
action.  It asks the existing durable runtime-intrusion ledger to revalidate one
exact encrypted HNC violation and emits a deterministic Aureon-owned HOLD
proposal for the canonical internal self-coder review route.  The proposal is
not a ``LocalProposalForge`` input: that forge accepts unified diffs, so calling
it here would turn untrusted intrusion material into a code-generation route.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, cast

from aureon.autonomous.aureon_internal_self_coder import SELF_CODER_FORGE_ID
from aureon.autonomous.aureon_internal_work_ledger import STATE_SCHEMA
from aureon.plumber.audit import assert_public_summary_safe
from aureon.plumber.crypto import domain_hash
from aureon.plumber.magic_star_v02 import STAR_SCHEMA
from aureon.plumber.production_release_broker_v03 import COMMAND_SCHEMA
from aureon.plumber.proposal_forge import PROPOSAL_FORGE_SCHEMA
from aureon.plumber.runtime_guard_v04 import _SUPPORTED_RULE_EVENTS
from aureon.plumber.runtime_intrusion_ledger_v04 import (
    RUNTIME_INTRUSION_AUTHENTICATED_PROJECTION_SCHEMA,
    RUNTIME_INTRUSION_LEDGER_SCHEMA,
    SQLiteRuntimeIntrusionLedgerV04,
)
from aureon.plumber.schema import (
    SchemaError,
    freeze_mapping,
    require_exact_keys,
    require_int,
    require_sha256,
    thaw_json,
)

INTRUSION_PROTECTION_PROPOSAL_SCHEMA: Final = "aureon.autonomous.intrusion-protection-work-proposal.v04"
INTRUSION_PROTECTION_PROPOSAL_OWNER: Final = "Aureon"
INTRUSION_PROTECTION_OWNER_ROUTE: Final = "aureon.autonomous.aureon_internal_self_coder"
INTRUSION_PROTECTION_REMEDIATION_TEMPLATE: Final = "review_exact_runtime_effect_guard_policy"
_EXPECTED_REASON_CODE: Final = "runtime_effect_not_magic_star_released"
_PROJECTION_DOMAIN: Final = "aureon.plumber.runtime-intrusion-authenticated-projection.v04"
_PROPOSAL_DOMAIN: Final = "aureon.autonomous.intrusion-protection-work-proposal.v04"
_EXACT_AUTHENTICATED_PROJECTION_METHOD: Final = (
    SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projection
)
_EXACT_AUTHENTICATED_PROJECTION_CODE: Final = (
    _EXACT_AUTHENTICATED_PROJECTION_METHOD.__code__
)
_EXACT_SOURCE_LEDGER_METHODS: Final = (
    (
        "preflight",
        SQLiteRuntimeIntrusionLedgerV04.preflight,
        SQLiteRuntimeIntrusionLedgerV04.preflight.__code__,
    ),
    (
        "authenticated_violation_projection",
        _EXACT_AUTHENTICATED_PROJECTION_METHOD,
        _EXACT_AUTHENTICATED_PROJECTION_CODE,
    ),
    (
        "authenticated_violation_projections",
        SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projections,
        SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projections.__code__,
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
_PROJECTION_FIELDS: Final = frozenset(
    {
        "schema",
        "ledger_schema",
        "ledger_id",
        "ledger_instance_commitment",
        "ledger_sequence",
        "ledger_authenticated_prefix_entry_count",
        "ledger_authenticated_prefix_head_commitment",
        "entry_commitment",
        "previous_entry_commitment",
        "runtime_metadata_sha256",
        "runtime_content_sha256",
        "hnc_packet_commitment",
        "hnc_binding_commitment",
        "quarantine_commitment",
        "quarantine_record_commitment",
        "intrusion_id_commitment",
        "event_name",
        "reason_code",
        "keyed_chain_authenticated",
        "hnc_packet_authenticated",
        "exact_runtime_route_authenticated",
        "raw_intrusion_id_returned",
        "raw_resource_commitment_returned",
        "authentication_tag_returned",
        "raw_arguments_retained",
        "external_head_anchor_attested",
        "magic_star_durable_custody_attested",
        "production_ready",
        "projection_commitment",
    }
)


class IntrusionProtectionBridgeError(ValueError):
    """Stable failure without rejected intrusion material in the message."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _validate_source_ledger_code_identity(
    ledger: SQLiteRuntimeIntrusionLedgerV04,
) -> None:
    if type(ledger) is not SQLiteRuntimeIntrusionLedgerV04:
        raise IntrusionProtectionBridgeError(
            "runtime_intrusion_ledger_code_identity_invalid"
        )
    class_namespace = vars(SQLiteRuntimeIntrusionLedgerV04)
    if (
        "__getattribute__" in class_namespace
        or SQLiteRuntimeIntrusionLedgerV04.__getattribute__
        is not object.__getattribute__
    ):
        raise IntrusionProtectionBridgeError(
            "runtime_intrusion_ledger_code_identity_invalid"
        )
    instance_namespace = object.__getattribute__(ledger, "__dict__")
    for name, exact_method, exact_code in _EXACT_SOURCE_LEDGER_METHODS:
        if (
            name in instance_namespace
            or class_namespace.get(name) is not exact_method
            or exact_method.__code__ is not exact_code
        ):
            raise IntrusionProtectionBridgeError(
                "runtime_intrusion_ledger_code_identity_invalid"
            )


_EXACT_SOURCE_IDENTITY_GATE: Final = _validate_source_ledger_code_identity
_EXACT_SOURCE_IDENTITY_GATE_CODE: Final = _EXACT_SOURCE_IDENTITY_GATE.__code__


def _validated_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        parsed = require_exact_keys(
            value,
            _PROJECTION_FIELDS,
            field="authenticated_runtime_intrusion_projection",
        )
        if (
            parsed["schema"] != RUNTIME_INTRUSION_AUTHENTICATED_PROJECTION_SCHEMA
            or parsed["ledger_schema"] != RUNTIME_INTRUSION_LEDGER_SCHEMA
        ):
            raise IntrusionProtectionBridgeError("runtime_intrusion_projection_schema_invalid")
        require_int(parsed["ledger_sequence"], field="ledger_sequence", minimum=2)
        require_int(
            parsed["ledger_authenticated_prefix_entry_count"],
            field="ledger_authenticated_prefix_entry_count",
            minimum=2,
        )
        if (
            parsed["ledger_authenticated_prefix_entry_count"] != parsed["ledger_sequence"]
            or parsed["ledger_authenticated_prefix_head_commitment"] != parsed["entry_commitment"]
        ):
            raise IntrusionProtectionBridgeError("runtime_intrusion_projection_prefix_invalid")
        for name in (
            "ledger_instance_commitment",
            "ledger_authenticated_prefix_head_commitment",
            "entry_commitment",
            "previous_entry_commitment",
            "runtime_metadata_sha256",
            "runtime_content_sha256",
            "hnc_packet_commitment",
            "hnc_binding_commitment",
            "quarantine_commitment",
            "quarantine_record_commitment",
            "intrusion_id_commitment",
            "projection_commitment",
        ):
            require_sha256(parsed[name], field=name)
        if (
            type(parsed["event_name"]) is not str
            or parsed["event_name"] not in _SUPPORTED_RULE_EVENTS
            or parsed["reason_code"] != _EXPECTED_REASON_CODE
            or parsed["keyed_chain_authenticated"] is not True
            or parsed["hnc_packet_authenticated"] is not True
            or parsed["exact_runtime_route_authenticated"] is not True
            or any(
                parsed[name] is not False
                for name in (
                    "raw_intrusion_id_returned",
                    "raw_resource_commitment_returned",
                    "authentication_tag_returned",
                    "raw_arguments_retained",
                    "external_head_anchor_attested",
                    "magic_star_durable_custody_attested",
                    "production_ready",
                )
            )
        ):
            raise IntrusionProtectionBridgeError("runtime_intrusion_projection_route_invalid")
        # This public hash is a deterministic corruption check only.  It is not
        # an authenticity primitive; authenticity is established exclusively
        # by the exact ledger call in the proposal constructor below.
        core = {
            key: parsed[key]
            for key in _PROJECTION_FIELDS
            if key != "projection_commitment"
        }
        if parsed["projection_commitment"] != domain_hash(_PROJECTION_DOMAIN, core):
            raise IntrusionProtectionBridgeError("runtime_intrusion_projection_commitment_invalid")
        return cast(dict[str, Any], parsed)
    except IntrusionProtectionBridgeError:
        raise
    except (SchemaError, TypeError, ValueError) as exc:
        raise IntrusionProtectionBridgeError("runtime_intrusion_projection_invalid") from exc


@dataclass(frozen=True, slots=True, init=False)
class AureonIntrusionProtectionWorkProposalV04:
    """Deterministic commitment-only work proposal; never an authority token."""

    intrusion_evidence: Mapping[str, Any]
    proposal_id: str
    proposal_commitment: str

    def __init__(
        self,
        *,
        ledger: SQLiteRuntimeIntrusionLedgerV04,
        sequence: int,
        entry_commitment: str,
    ) -> None:
        if type(ledger) is not SQLiteRuntimeIntrusionLedgerV04:
            raise IntrusionProtectionBridgeError(
                "exact_runtime_intrusion_ledger_required"
            )
        if (
            globals().get("_validate_source_ledger_code_identity")
            is not _EXACT_SOURCE_IDENTITY_GATE
            or _EXACT_SOURCE_IDENTITY_GATE.__code__
            is not _EXACT_SOURCE_IDENTITY_GATE_CODE
        ):
            raise IntrusionProtectionBridgeError(
                "runtime_intrusion_ledger_code_identity_invalid"
            )
        _EXACT_SOURCE_IDENTITY_GATE(ledger)
        # Reject ordinary same-process class monkeypatching and the concrete
        # same-object ``function.__code__`` replacement attack.  Arbitrary code
        # execution in this interpreter can still rewrite module globals,
        # closures, or the caller itself and is outside this HOLD-only local
        # proof; production needs process isolation plus a measured external
        # trust anchor.
        if (
            vars(SQLiteRuntimeIntrusionLedgerV04).get(
                "authenticated_violation_projection"
            )
            is not _EXACT_AUTHENTICATED_PROJECTION_METHOD
            or _EXACT_AUTHENTICATED_PROJECTION_METHOD.__code__
            is not _EXACT_AUTHENTICATED_PROJECTION_CODE
        ):
            raise IntrusionProtectionBridgeError(
                "runtime_intrusion_ledger_code_identity_invalid"
            )
        projection = _EXACT_AUTHENTICATED_PROJECTION_METHOD(
            ledger,
            sequence=sequence,
            entry_commitment=entry_commitment,
        )
        validated = _validated_projection(projection)
        payload = _proposal_commitment_payload(validated)
        commitment = domain_hash(_PROPOSAL_DOMAIN, payload)
        object.__setattr__(
            self,
            "intrusion_evidence",
            freeze_mapping(validated, field="intrusion_evidence"),
        )
        object.__setattr__(
            self,
            "proposal_id",
            f"remediation-{commitment[:32]}",
        )
        object.__setattr__(self, "proposal_commitment", commitment)

    def commitment_payload(self) -> dict[str, Any]:
        return _proposal_commitment_payload(thaw_json(self.intrusion_evidence))

    def public_summary(self) -> dict[str, Any]:
        summary = {
            **self.commitment_payload(),
            "proposal_id": self.proposal_id,
            "proposal_commitment": self.proposal_commitment,
        }
        assert_public_summary_safe(summary)
        return summary


def _proposal_commitment_payload(
    intrusion_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": INTRUSION_PROTECTION_PROPOSAL_SCHEMA,
        "proposal_owner": INTRUSION_PROTECTION_PROPOSAL_OWNER,
        "owner_route": INTRUSION_PROTECTION_OWNER_ROUTE,
        "proposal_kind": "security_remediation_review",
        "remediation_template_id": INTRUSION_PROTECTION_REMEDIATION_TEMPLATE,
        "intrusion_evidence": dict(intrusion_evidence),
        "canonical_work_ledger_schema": STATE_SCHEMA,
        "canonical_proposal_forge_schema": PROPOSAL_FORGE_SCHEMA,
        "canonical_proposal_forge_id": SELF_CODER_FORGE_ID,
        "production_release_command_schema": COMMAND_SCHEMA,
        "magic_star_schema": STAR_SCHEMA,
        "disposition": "HOLD",
        "review_required": True,
        "commitment_only": True,
        "signature_present": False,
        "single_owner_route": True,
        "duplicate_queue_created": False,
        "proposal_persisted": False,
        "work_ledger_appended": False,
        "proposal_forge_invoked": False,
        "source_request_generated": False,
        "code_generation_invoked": False,
        "target_path_present": False,
        "unified_diff_present": False,
        "patch_applied": False,
        "repository_mutation_authorized": False,
        "release_broker_invoked": False,
        "magic_star_invoked": False,
        "external_action_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
        "production_ready": False,
    }


def build_runtime_intrusion_protection_proposal_v04(
    *,
    ledger: SQLiteRuntimeIntrusionLedgerV04,
    sequence: int,
    entry_commitment: str,
) -> AureonIntrusionProtectionWorkProposalV04:
    """Build one idempotent HOLD proposal from the exact trusted ledger owner."""

    if type(ledger) is not SQLiteRuntimeIntrusionLedgerV04:
        raise IntrusionProtectionBridgeError("exact_runtime_intrusion_ledger_required")
    return AureonIntrusionProtectionWorkProposalV04(
        ledger=ledger,
        sequence=sequence,
        entry_commitment=entry_commitment,
    )


__all__ = [
    "INTRUSION_PROTECTION_OWNER_ROUTE",
    "INTRUSION_PROTECTION_PROPOSAL_OWNER",
    "INTRUSION_PROTECTION_PROPOSAL_SCHEMA",
    "INTRUSION_PROTECTION_REMEDIATION_TEMPLATE",
    "AureonIntrusionProtectionWorkProposalV04",
    "IntrusionProtectionBridgeError",
    "build_runtime_intrusion_protection_proposal_v04",
]
