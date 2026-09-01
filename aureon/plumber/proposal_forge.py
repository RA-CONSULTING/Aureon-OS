"""Proposal-only self-coder forge for local development.

The forge has no filesystem, subprocess, import, compile, execution, or patch
application path.  It seals an exact source request and unified-diff candidate
through :class:`LocalOSProtectionBoundary`, retaining the admitted HNC carrier
only behind an opaque handle.  Rejected material follows the boundary's
metadata-only quarantine path.

Promotion is permanently HOLD in this local implementation.  The checked-in
Magic Star and custody components are non-production, so neither they nor an
injected applier are called.  A future production release implementation must
define a separately reviewed trust and transaction boundary; it cannot be
unlocked by a self-attested local receipt.

This is explicitly an in-memory, local-development design.  It is not a
durable proposal ledger, production HSM/sandbox, independent review service,
or proof that caller-supplied adviser metadata is externally authentic.
"""

from __future__ import annotations

import re
import secrets
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Final, Protocol, TypeAlias

from .audit import assert_public_summary_safe
from .crypto import canonical_json_bytes, decode_canonical_json, domain_hash, sha256_hex
from .os_protection import (
    AdmittedHNC,
    LocalOSProtectionBoundary,
    OpaqueHNCHandle,
    OSProtectionError,
    QuarantinedHNC,
)
from .schema import (
    SchemaError,
    format_timestamp,
    freeze_mapping,
    parse_timestamp,
    require_exact_keys,
    require_int,
    require_nonblank,
    require_sha256,
    thaw_json,
)
from .star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
)

PROPOSAL_FORGE_SCHEMA: Final = "aureon.plumber.proposal-forge.v0"
PROPOSAL_FORGE_PREFLIGHT_SCHEMA: Final = "aureon.plumber.proposal-forge-preflight.v0"
PROPOSAL_PURPOSE: Final = "aureon.plumber.self-coder.proposal.v0"
AUTHORSHIP_STATEMENT: Final = (
    "Aureon proposal generation with OpenAI adviser/reviewer assistance; "
    "this record makes no ownership claim."
)
_PROPOSAL_PAYLOAD_SCHEMA: Final = "aureon.plumber.proposal-payload.v0"
_PROPOSAL_AAD_SCHEMA: Final = "aureon.plumber.proposal-aad.v0"
_PROPOSAL_SOURCE_ID: Final = "aureon.autonomous.internal-self-coder"
_PROPOSAL_INGRESS_KIND: Final = "application/vnd.aureon.unified-diff-proposal+json"
_PROPOSAL_GENERATOR: Final = "Aureon"
_OPENAI_ORGANIZATION: Final = "OpenAI"
_OPENAI_ROLE: Final = "adviser_and_reviewer"
_OWNERSHIP_CLAIM: Final = "none"
_METADATA_VERIFICATION: Final = "caller_supplied_receipt_commitment_not_independently_verified"
_MAX_DIFF_BYTES: Final = 128 * 1024
_MAX_REQUEST_BYTES: Final = 8 * 1024
_MAX_PROVENANCE_BYTES: Final = 128 * 1024
_MAX_ID_BYTES: Final = 512
_MAX_DIFF_FILES: Final = 8
_MAX_DIFF_HUNKS: Final = 128
_MAX_DIFF_LINE_BYTES: Final = 16 * 1024
_GIT_COMMIT_RE: Final = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

_DESCRIPTOR_FIELDS: Final = {
    "schema",
    "forge_id",
    "proposal_id",
    "source_request_sha256",
    "source_request_size_bytes",
    "model_id",
    "adviser_organization",
    "adviser_id",
    "reviewer_id",
    "adviser_evidence_sha256",
    "provenance_sha256",
    "base_commit",
    "diff_sha256",
    "diff_size_bytes",
    "proposal_generator",
    "openai_role",
    "ownership_claim",
    "authorship_statement",
    "metadata_verification",
    "proposal_commitment",
}


class ProposalForgeError(ValueError):
    """Stable proposal-forge contract error with no rejected value in text."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


class PromotionDisposition(StrEnum):
    HOLD = "HOLD"


def _bounded_text(value: object, *, field_name: str, maximum_bytes: int) -> str:
    try:
        text = require_nonblank(value, field=field_name, max_length=maximum_bytes)
        encoded = text.encode("utf-8", errors="strict")
    except (SchemaError, UnicodeEncodeError) as exc:
        raise ProposalForgeError(f"{field_name}_invalid") from exc
    if len(encoded) > maximum_bytes:
        raise ProposalForgeError(f"{field_name}_invalid")
    return text


def _base_commit(value: object) -> str:
    if not isinstance(value, str) or _GIT_COMMIT_RE.fullmatch(value) is None:
        raise ProposalForgeError("base_commit_invalid")
    return value


def _canonical_mapping(
    value: object,
    *,
    field_name: str,
    maximum_bytes: int,
) -> tuple[dict[str, Any], bytes]:
    if not isinstance(value, Mapping):
        raise ProposalForgeError(f"{field_name}_invalid")
    try:
        encoded = canonical_json_bytes(dict(value))
        if len(encoded) > maximum_bytes:
            raise ProposalForgeError(f"{field_name}_invalid")
        decoded = decode_canonical_json(encoded, require_mapping=True, max_bytes=maximum_bytes)
    except BaseException as exc:
        if isinstance(exc, ProposalForgeError):
            raise
        raise ProposalForgeError(f"{field_name}_invalid") from exc
    if not isinstance(decoded, dict):  # pragma: no cover - required by decoder
        raise ProposalForgeError(f"{field_name}_invalid")
    return decoded, encoded


def _safe_diff_path(value: str, *, expected_prefix: str) -> str | None:
    raw = value.split("\t", 1)[0].strip()
    if raw == "/dev/null":
        return raw
    if (
        not raw.startswith(expected_prefix)
        or "\\" in raw
        or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in raw)
    ):
        return None
    relative = raw[len(expected_prefix) :]
    parts = relative.split("/")
    if (
        not relative
        or len(relative.encode("utf-8", errors="strict")) > _MAX_ID_BYTES
        or any(part in {"", ".", ".."} for part in parts)
        or any(":" in part for part in parts)
    ):
        return None
    return relative


def _diff_contract_valid(diff: str, diff_bytes: bytes) -> bool:
    if (
        not diff_bytes
        or len(diff_bytes) > _MAX_DIFF_BYTES
        or "\x00" in diff
        or "GIT binary patch" in diff
    ):
        return False
    lines = diff.splitlines()
    try:
        if any(len(line.encode("utf-8", errors="strict")) > _MAX_DIFF_LINE_BYTES for line in lines):
            return False
    except UnicodeEncodeError:
        return False
    if any(
        line.startswith(("rename from ", "rename to ", "copy from ", "copy to "))
        for line in lines
    ):
        return False
    old_headers = [line[4:] for line in lines if line.startswith("--- ")]
    new_headers = [line[4:] for line in lines if line.startswith("+++ ")]
    hunk_count = sum(line.startswith("@@") for line in lines)
    if (
        not old_headers
        or len(old_headers) != len(new_headers)
        or len(old_headers) > _MAX_DIFF_FILES
        or not 1 <= hunk_count <= _MAX_DIFF_HUNKS
    ):
        return False
    for old_header, new_header in zip(old_headers, new_headers, strict=True):
        old_path = _safe_diff_path(old_header, expected_prefix="a/")
        new_path = _safe_diff_path(new_header, expected_prefix="b/")
        if old_path is None or new_path is None:
            return False
        if old_path == "/dev/null" and new_path == "/dev/null":
            return False
        if old_path != "/dev/null" and new_path != "/dev/null" and old_path != new_path:
            return False
    for line in lines:
        if not line.startswith("diff --git "):
            continue
        fields = line.split()
        if len(fields) != 4:
            return False
        old_path = _safe_diff_path(fields[2], expected_prefix="a/")
        new_path = _safe_diff_path(fields[3], expected_prefix="b/")
        if old_path is None or new_path is None or old_path != new_path:
            return False
    return True


def _descriptor_core(descriptor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: descriptor[key]
        for key in _DESCRIPTOR_FIELDS
        if key not in {"proposal_id", "proposal_commitment"}
    }


def _validate_descriptor(value: Mapping[str, Any]) -> dict[str, Any]:
    parsed = require_exact_keys(value, _DESCRIPTOR_FIELDS, field="proposal_descriptor")
    if parsed["schema"] != PROPOSAL_FORGE_SCHEMA:
        raise ProposalForgeError("proposal_descriptor_schema_invalid")
    for name in ("forge_id", "proposal_id", "model_id", "adviser_id", "reviewer_id"):
        _bounded_text(parsed[name], field_name=name, maximum_bytes=_MAX_ID_BYTES)
    if (
        parsed["adviser_organization"] != _OPENAI_ORGANIZATION
        or parsed["proposal_generator"] != _PROPOSAL_GENERATOR
        or parsed["openai_role"] != _OPENAI_ROLE
        or parsed["ownership_claim"] != _OWNERSHIP_CLAIM
        or parsed["authorship_statement"] != AUTHORSHIP_STATEMENT
        or parsed["metadata_verification"] != _METADATA_VERIFICATION
    ):
        raise ProposalForgeError("proposal_authorship_invalid")
    if not str(parsed["model_id"]).startswith(("aureon-local:", "ollama:")):
        raise ProposalForgeError("aureon_generator_model_id_invalid")
    _base_commit(parsed["base_commit"])
    for name in (
        "source_request_sha256",
        "adviser_evidence_sha256",
        "provenance_sha256",
        "diff_sha256",
        "proposal_commitment",
    ):
        require_sha256(parsed[name], field=name)
    require_int(parsed["source_request_size_bytes"], field="source_request_size_bytes", minimum=1)
    require_int(parsed["diff_size_bytes"], field="diff_size_bytes", minimum=1)
    expected = domain_hash("aureon.plumber.proposal.v0", _descriptor_core(parsed))
    if parsed["proposal_commitment"] != expected:
        raise ProposalForgeError("proposal_commitment_invalid")
    expected_id = f"proposal-{expected[:32]}"
    if parsed["proposal_id"] != expected_id:
        raise ProposalForgeError("proposal_id_invalid")
    return parsed


def _proposal_handle_commitment(
    *,
    forge_id: str,
    proposal_id: str,
    proposal_commitment: str,
    os_handle_commitment: str,
    token: str,
) -> str:
    return domain_hash(
        "aureon.plumber.opaque-proposal-handle.v0",
        {
            "forge_id": forge_id,
            "proposal_id": proposal_id,
            "proposal_commitment": proposal_commitment,
            "os_handle_commitment": os_handle_commitment,
            "token": token,
        },
    )


@dataclass(frozen=True, slots=True)
class OpaqueProposalHandle:
    """One-use proposal reference; no request, diff, HNC carrier, or key."""

    descriptor: Mapping[str, Any]
    os_handle_commitment: str
    token: str = field(repr=False)
    handle_commitment: str

    def __post_init__(self) -> None:
        parsed = _validate_descriptor(self.descriptor)
        object.__setattr__(
            self,
            "descriptor",
            freeze_mapping(parsed, field="proposal_descriptor"),
        )
        require_sha256(self.os_handle_commitment, field="os_handle_commitment")
        require_sha256(self.handle_commitment, field="handle_commitment")
        if not isinstance(self.token, str) or not self.token:
            raise ProposalForgeError("proposal_handle_token_invalid")
        expected = _proposal_handle_commitment(
            forge_id=self.forge_id,
            proposal_id=self.proposal_id,
            proposal_commitment=self.proposal_commitment,
            os_handle_commitment=self.os_handle_commitment,
            token=self.token,
        )
        if self.handle_commitment != expected:
            raise ProposalForgeError("proposal_handle_commitment_invalid")

    @classmethod
    def issue(
        cls,
        *,
        descriptor: Mapping[str, Any],
        os_handle: OpaqueHNCHandle,
    ) -> OpaqueProposalHandle:
        parsed = _validate_descriptor(descriptor)
        token = secrets.token_urlsafe(32)
        return cls(
            descriptor=parsed,
            os_handle_commitment=os_handle.handle_commitment,
            token=token,
            handle_commitment=_proposal_handle_commitment(
                forge_id=parsed["forge_id"],
                proposal_id=parsed["proposal_id"],
                proposal_commitment=parsed["proposal_commitment"],
                os_handle_commitment=os_handle.handle_commitment,
                token=token,
            ),
        )

    @property
    def forge_id(self) -> str:
        return str(self.descriptor["forge_id"])

    @property
    def proposal_id(self) -> str:
        return str(self.descriptor["proposal_id"])

    @property
    def proposal_commitment(self) -> str:
        return str(self.descriptor["proposal_commitment"])

    def public_summary(self) -> dict[str, Any]:
        summary = {
            "schema": PROPOSAL_FORGE_SCHEMA,
            "descriptor": thaw_json(self.descriptor),
            "os_handle_commitment": self.os_handle_commitment,
            "handle_commitment": self.handle_commitment,
            "promotion_disposition": str(PromotionDisposition.HOLD),
            "promotion_authority": "none_until_reviewed_magic_star_final_applier",
            "raw_request_returned": False,
            "raw_diff_returned": False,
            "local_development_only": True,
            "production_ready": False,
        }
        assert_public_summary_safe(summary)
        return summary


@dataclass(frozen=True, slots=True)
class QuarantinedProposal:
    descriptor: Mapping[str, Any]
    quarantine: QuarantinedHNC

    def __post_init__(self) -> None:
        parsed = _validate_descriptor(self.descriptor)
        object.__setattr__(
            self,
            "descriptor",
            freeze_mapping(parsed, field="proposal_descriptor"),
        )
        if not isinstance(self.quarantine, QuarantinedHNC):
            raise ProposalForgeError("proposal_quarantine_invalid")

    def public_summary(self) -> dict[str, Any]:
        summary = {
            "schema": PROPOSAL_FORGE_SCHEMA,
            "descriptor": thaw_json(self.descriptor),
            "outcome": "QUARANTINED_PROPOSAL",
            "promotion_disposition": str(PromotionDisposition.HOLD),
            "quarantine": self.quarantine.public_summary(),
            "raw_request_returned": False,
            "raw_diff_returned": False,
            "local_development_only": True,
            "production_ready": False,
        }
        assert_public_summary_safe(summary)
        return summary


ProposalForgeOutcome: TypeAlias = OpaqueProposalHandle | QuarantinedProposal


@dataclass(frozen=True, slots=True)
class ProposalReview:
    proposal_commitment: str
    base_commit: str
    diff_sha256: str
    decision: str
    reviewer_organization: str
    reviewer_id: str
    reviewer_role: str
    review_receipt_sha256: str
    reviewed_at: str
    review_commitment: str

    def __post_init__(self) -> None:
        for name in (
            "proposal_commitment",
            "diff_sha256",
            "review_receipt_sha256",
            "review_commitment",
        ):
            require_sha256(getattr(self, name), field=name)
        _base_commit(self.base_commit)
        if self.decision not in {"APPROVE", "HOLD", "REJECT"}:
            raise ProposalForgeError("review_decision_invalid")
        for name in ("reviewer_organization", "reviewer_id", "reviewer_role"):
            _bounded_text(getattr(self, name), field_name=name, maximum_bytes=_MAX_ID_BYTES)
        parse_timestamp(self.reviewed_at, field="reviewed_at")
        if self.review_commitment != domain_hash(
            "aureon.plumber.proposal-review.v0",
            self.commitment_payload(),
        ):
            raise ProposalForgeError("review_commitment_invalid")

    @classmethod
    def build(
        cls,
        *,
        proposal_commitment: str,
        base_commit: str,
        diff_sha256: str,
        decision: str,
        reviewer_organization: str,
        reviewer_id: str,
        reviewer_role: str,
        review_receipt_sha256: str,
        reviewed_at: datetime,
    ) -> ProposalReview:
        values = {
            "proposal_commitment": proposal_commitment,
            "base_commit": base_commit,
            "diff_sha256": diff_sha256,
            "decision": decision,
            "reviewer_organization": reviewer_organization,
            "reviewer_id": reviewer_id,
            "reviewer_role": reviewer_role,
            "review_receipt_sha256": review_receipt_sha256,
            "reviewed_at": format_timestamp(reviewed_at),
        }
        return cls(
            **values,
            review_commitment=domain_hash(
                "aureon.plumber.proposal-review.v0",
                values,
            ),
        )

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "proposal_commitment": self.proposal_commitment,
            "base_commit": self.base_commit,
            "diff_sha256": self.diff_sha256,
            "decision": self.decision,
            "reviewer_organization": self.reviewer_organization,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "review_receipt_sha256": self.review_receipt_sha256,
            "reviewed_at": self.reviewed_at,
        }

    def public_summary(self) -> dict[str, Any]:
        summary = {**self.commitment_payload(), "review_commitment": self.review_commitment}
        assert_public_summary_safe(summary)
        return summary


class ReviewedFinalApplier(Protocol):
    """Reserved production-applier shape; the local forge never invokes it."""

    applier_id: str
    measurement_sha256: str

    def apply_reviewed_proposal(
        self,
        *,
        protected_proposal: object,
        proposal_summary: Mapping[str, Any],
        review: ProposalReview,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ProposalPromotionResult:
    proposal_id: str
    proposal_commitment: str
    review_commitment: str
    disposition: PromotionDisposition
    denial_codes: tuple[str, ...]
    proposal_handle_consumed: bool
    production_magic_star_release_available: bool
    final_applier_invoked: bool
    promotion_commitment: str
    local_development_only: bool = True
    production_ready: bool = False

    def __post_init__(self) -> None:
        _bounded_text(self.proposal_id, field_name="proposal_id", maximum_bytes=_MAX_ID_BYTES)
        require_sha256(self.proposal_commitment, field="proposal_commitment")
        require_sha256(self.review_commitment, field="review_commitment")
        require_sha256(self.promotion_commitment, field="promotion_commitment")
        if not isinstance(self.disposition, PromotionDisposition):
            raise ProposalForgeError("promotion_disposition_invalid")
        if (
            type(self.proposal_handle_consumed) is not bool
            or type(self.production_magic_star_release_available) is not bool
            or type(self.final_applier_invoked) is not bool
        ):
            raise ProposalForgeError("promotion_boolean_invalid")
        if (
            any(not isinstance(code, str) or not code for code in self.denial_codes)
            or tuple(sorted(set(self.denial_codes))) != self.denial_codes
        ):
            raise ProposalForgeError("promotion_denial_codes_invalid")
        if self.local_development_only is not True or self.production_ready is not False:
            raise ProposalForgeError("promotion_scope_invalid")
        if not self.denial_codes:
            raise ProposalForgeError("promotion_hold_denial_required")
        if (
            self.disposition is not PromotionDisposition.HOLD
            or self.proposal_handle_consumed
            or self.production_magic_star_release_available
            or self.final_applier_invoked
        ):
            raise ProposalForgeError("nonproduction_promotion_must_hold")
        if self.promotion_commitment != domain_hash(
            "aureon.plumber.proposal-promotion.v0",
            self.commitment_payload(),
        ):
            raise ProposalForgeError("promotion_commitment_invalid")

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_commitment": self.proposal_commitment,
            "review_commitment": self.review_commitment,
            "disposition": str(self.disposition),
            "denial_codes": list(self.denial_codes),
            "proposal_handle_consumed": self.proposal_handle_consumed,
            "production_magic_star_release_available": self.production_magic_star_release_available,
            "final_applier_invoked": self.final_applier_invoked,
            "local_development_only": True,
            "production_ready": False,
        }

    def public_summary(self) -> dict[str, Any]:
        summary = {
            **self.commitment_payload(),
            "promotion_commitment": self.promotion_commitment,
        }
        assert_public_summary_safe(summary)
        return summary


@dataclass(slots=True)
class _ProposalRecord:
    os_handle: OpaqueHNCHandle
    descriptor: dict[str, Any]
    proposal_handle_commitment: str


class LocalProposalForge:
    """In-memory proposal-only bridge from self-coder output to Magic Star."""

    production_ready = False

    def __init__(
        self,
        *,
        forge_id: str,
        os_boundary: LocalOSProtectionBoundary,
    ) -> None:
        self._forge_id = _bounded_text(
            forge_id,
            field_name="forge_id",
            maximum_bytes=_MAX_ID_BYTES,
        )
        if not isinstance(os_boundary, LocalOSProtectionBoundary):
            raise ProposalForgeError("local_os_protection_boundary_required")
        self._os_boundary = os_boundary
        self._records: dict[str, _ProposalRecord] = {}
        self._consumed_handle_commitments: set[str] = set()
        self._lock = threading.RLock()

    def preflight(self) -> dict[str, Any]:
        """Return a metadata-only readiness check before sensitive authoring."""

        key = self._os_boundary.key_preflight()
        ready = key.get("ready") is True
        summary = {
            "schema": PROPOSAL_FORGE_PREFLIGHT_SCHEMA,
            "forge_id": self._forge_id,
            "ready": ready,
            "reason_code": "ready" if ready else str(key.get("reason_code") or "hold"),
            "os_key_preflight_schema": str(key.get("schema") or ""),
            "key_material_returned": False,
            "proposal_admission_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
            "local_development_only": True,
            "production_ready": False,
        }
        assert_public_summary_safe(summary)
        return summary

    def forge_proposal(
        self,
        *,
        source_request: str,
        unified_diff: str,
        model_id: str,
        adviser_id: str,
        reviewer_id: str,
        adviser_evidence_sha256: str,
        provenance: Mapping[str, Any],
        base_commit: str,
    ) -> ProposalForgeOutcome:
        """Seal one exact candidate; never write, apply, import, or execute it."""

        request = _bounded_text(
            source_request,
            field_name="source_request",
            maximum_bytes=_MAX_REQUEST_BYTES,
        )
        if not isinstance(unified_diff, str):
            raise ProposalForgeError("unified_diff_invalid")
        try:
            diff_bytes = unified_diff.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ProposalForgeError("unified_diff_invalid") from exc
        bounded_model = _bounded_text(
            model_id,
            field_name="model_id",
            maximum_bytes=_MAX_ID_BYTES,
        )
        bounded_adviser = _bounded_text(
            adviser_id,
            field_name="adviser_id",
            maximum_bytes=_MAX_ID_BYTES,
        )
        bounded_reviewer = _bounded_text(
            reviewer_id,
            field_name="reviewer_id",
            maximum_bytes=_MAX_ID_BYTES,
        )
        require_sha256(adviser_evidence_sha256, field="adviser_evidence_sha256")
        commit = _base_commit(base_commit)
        normalized_provenance, provenance_bytes = _canonical_mapping(
            provenance,
            field_name="provenance",
            maximum_bytes=_MAX_PROVENANCE_BYTES,
        )
        request_bytes = request.encode("utf-8")
        core: dict[str, Any] = {
            "schema": PROPOSAL_FORGE_SCHEMA,
            "forge_id": self._forge_id,
            "source_request_sha256": sha256_hex(request_bytes),
            "source_request_size_bytes": len(request_bytes),
            "model_id": bounded_model,
            "adviser_organization": _OPENAI_ORGANIZATION,
            "adviser_id": bounded_adviser,
            "reviewer_id": bounded_reviewer,
            "adviser_evidence_sha256": adviser_evidence_sha256,
            "provenance_sha256": sha256_hex(provenance_bytes),
            "base_commit": commit,
            "diff_sha256": sha256_hex(diff_bytes),
            "diff_size_bytes": len(diff_bytes),
            "proposal_generator": _PROPOSAL_GENERATOR,
            "openai_role": _OPENAI_ROLE,
            "ownership_claim": _OWNERSHIP_CLAIM,
            "authorship_statement": AUTHORSHIP_STATEMENT,
            "metadata_verification": _METADATA_VERIFICATION,
        }
        provisional = {**core, "proposal_id": ""}
        # The proposal ID is derived from a core that excludes the ID itself,
        # preventing random identifiers from defeating OS replay detection.
        commitment_core = {key: value for key, value in provisional.items() if key != "proposal_id"}
        proposal_commitment = domain_hash("aureon.plumber.proposal.v0", commitment_core)
        descriptor = {
            **core,
            "proposal_id": f"proposal-{proposal_commitment[:32]}",
            "proposal_commitment": proposal_commitment,
        }
        _validate_descriptor(descriptor)
        payload = {
            "schema": _PROPOSAL_PAYLOAD_SCHEMA,
            "descriptor": descriptor,
            "source_request": request,
            "unified_diff": unified_diff,
            "provenance": normalized_provenance,
        }
        payload_bytes = canonical_json_bytes(payload)
        operator_aad = {
            "schema": _PROPOSAL_AAD_SCHEMA,
            "descriptor": descriptor,
            "payload_sha256": sha256_hex(payload_bytes),
            "promotion_initial_disposition": str(PromotionDisposition.HOLD),
            "repository_mutation_authorized": False,
            "generated_code_execution_authorized": False,
        }

        def validate_payload(view: memoryview) -> bool:
            try:
                decoded = decode_canonical_json(view.tobytes(), require_mapping=True)
                if not isinstance(decoded, dict) or set(decoded) != set(payload):
                    return False
                return (
                    decoded == payload
                    and _diff_contract_valid(unified_diff, diff_bytes)
                    and sha256_hex(payload_bytes) == operator_aad["payload_sha256"]
                )
            except BaseException:
                return False

        outcome = self._os_boundary.admit_external(
            payload_bytes,
            source_id=_PROPOSAL_SOURCE_ID,
            ingress_kind=_PROPOSAL_INGRESS_KIND,
            purpose=PROPOSAL_PURPOSE,
            operator_aad=operator_aad,
            content_validator=validate_payload,
        )
        if isinstance(outcome, QuarantinedHNC):
            return QuarantinedProposal(descriptor=descriptor, quarantine=outcome)
        if not isinstance(outcome, AdmittedHNC):  # pragma: no cover - total OS outcome
            raise ProposalForgeError("os_admission_outcome_invalid")
        handle = OpaqueProposalHandle.issue(
            descriptor=descriptor,
            os_handle=outcome.handle,
        )
        record = _ProposalRecord(
            os_handle=outcome.handle,
            descriptor=dict(descriptor),
            proposal_handle_commitment=handle.handle_commitment,
        )
        with self._lock:
            if handle.proposal_id in self._records:
                raise ProposalForgeError("proposal_record_collision")
            self._records[handle.proposal_id] = record
        return handle

    def _promotion_result(
        self,
        *,
        handle: OpaqueProposalHandle,
        review: ProposalReview,
        denial_codes: tuple[str, ...],
    ) -> ProposalPromotionResult:
        normalized_codes = tuple(sorted(set(denial_codes)))
        values = {
            "proposal_id": handle.proposal_id,
            "proposal_commitment": handle.proposal_commitment,
            "review_commitment": review.review_commitment,
            "disposition": str(PromotionDisposition.HOLD),
            "denial_codes": list(normalized_codes),
            "proposal_handle_consumed": False,
            "production_magic_star_release_available": False,
            "final_applier_invoked": False,
            "local_development_only": True,
            "production_ready": False,
        }
        return ProposalPromotionResult(
            proposal_id=handle.proposal_id,
            proposal_commitment=handle.proposal_commitment,
            review_commitment=review.review_commitment,
            disposition=PromotionDisposition.HOLD,
            denial_codes=normalized_codes,
            proposal_handle_consumed=False,
            production_magic_star_release_available=False,
            final_applier_invoked=False,
            promotion_commitment=domain_hash(
                "aureon.plumber.proposal-promotion.v0",
                values,
            ),
        )

    def discard_proposal(
        self,
        handle: OpaqueProposalHandle,
        *,
        reason_code: str,
    ) -> dict[str, Any]:
        """Atomically burn one transient proposal and its OS admission.

        This is the terminal path for a proposal that cannot enter a durable,
        authenticated review vault.  It never decodes or releases the carrier.
        """

        if not isinstance(handle, OpaqueProposalHandle):
            raise ProposalForgeError("opaque_proposal_handle_required")
        reason = _bounded_text(
            reason_code,
            field_name="discard_reason_code",
            maximum_bytes=128,
        )
        with self._lock:
            record = self._records.get(handle.proposal_id)
            available = (
                record is not None
                and handle.forge_id == self._forge_id
                and record.proposal_handle_commitment == handle.handle_commitment
                and handle.handle_commitment not in self._consumed_handle_commitments
                and secrets.compare_digest(
                    handle.handle_commitment,
                    _proposal_handle_commitment(
                        forge_id=handle.forge_id,
                        proposal_id=handle.proposal_id,
                        proposal_commitment=handle.proposal_commitment,
                        os_handle_commitment=handle.os_handle_commitment,
                        token=handle.token,
                    ),
                )
            )
            if not available or record is None:
                raise ProposalForgeError("proposal_handle_unavailable_or_replayed")
            try:
                os_discard = self._os_boundary.discard_admitted(
                    record.os_handle,
                    reason_code=reason,
                )
            except OSProtectionError as exc:
                raise ProposalForgeError("proposal_os_discard_failed") from exc
            self._records.pop(handle.proposal_id, None)
            self._consumed_handle_commitments.add(handle.handle_commitment)

        summary = {
            "schema": PROPOSAL_FORGE_SCHEMA,
            "proposal_id": handle.proposal_id,
            "proposal_commitment": handle.proposal_commitment,
            "disposition": "DISCARDED_HNC",
            "reason_code": reason,
            "proposal_handle_consumed": True,
            "carrier_released": False,
            "plaintext_decoded": False,
            "os_discard_handle_commitment": str(
                os_discard.get("handle_commitment") or ""
            ),
            "local_development_only": True,
            "production_ready": False,
        }
        assert_public_summary_safe(summary)
        return summary

    def promote_reviewed(
        self,
        handle: OpaqueProposalHandle,
        *,
        review: ProposalReview,
        custody: LocalDevelopmentStarCustodyV02,
        release_context_sha256: str,
        final_applier: ReviewedFinalApplier,
    ) -> ProposalPromotionResult:
        """Return HOLD without touching non-production custody or an applier.

        The checked-in OS boundary, Magic Star custody, and release boundary
        are local-development components with ``production_ready=False``.
        Consequently no injected object can create release authority here.
        """

        if not isinstance(handle, OpaqueProposalHandle):
            raise ProposalForgeError("opaque_proposal_handle_required")
        if not isinstance(review, ProposalReview):
            raise ProposalForgeError("proposal_review_required")
        require_sha256(release_context_sha256, field="release_context_sha256")
        with self._lock:
            record = self._records.get(handle.proposal_id)
            available = (
                record is not None
                and record.proposal_handle_commitment == handle.handle_commitment
                and handle.handle_commitment not in self._consumed_handle_commitments
                and secrets.compare_digest(
                    handle.handle_commitment,
                    _proposal_handle_commitment(
                        forge_id=handle.forge_id,
                        proposal_id=handle.proposal_id,
                        proposal_commitment=handle.proposal_commitment,
                        os_handle_commitment=handle.os_handle_commitment,
                        token=handle.token,
                    ),
                )
            )
        if not available or record is None:
            raise ProposalForgeError("proposal_handle_unavailable_or_replayed")

        descriptor = record.descriptor
        if (
            review.proposal_commitment != descriptor["proposal_commitment"]
            or review.base_commit != descriptor["base_commit"]
            or review.diff_sha256 != descriptor["diff_sha256"]
            or review.reviewer_organization != descriptor["adviser_organization"]
            or review.reviewer_id != descriptor["reviewer_id"]
        ):
            return self._promotion_result(
                handle=handle,
                review=review,
                denial_codes=("review_binding_mismatch",),
            )
        if review.decision != "APPROVE":
            return self._promotion_result(
                handle=handle,
                review=review,
                denial_codes=("review_not_approved",),
            )
        # Deliberately do not inspect either object: hostile properties and
        # self-attested receipts must not become a code-execution escape hatch.
        _ = custody
        _ = final_applier
        return self._promotion_result(
            handle=handle,
            review=review,
            denial_codes=("production_magic_star_release_unavailable",),
        )

    def public_summary(self) -> dict[str, Any]:
        with self._lock:
            summary = {
                "schema": PROPOSAL_FORGE_SCHEMA,
                "forge_id": self._forge_id,
                "active_opaque_proposal_count": len(self._records),
                "consumed_opaque_proposal_count": len(self._consumed_handle_commitments),
                "proposal_only": True,
                "repository_mutation_implemented": False,
                "generated_code_execution_implemented": False,
                "production_magic_star_release_available": False,
                "reviewed_final_applier_invocation_implemented": False,
                "persistent": False,
                "local_development_only": True,
                "production_ready": False,
            }
        assert_public_summary_safe(summary)
        return summary


__all__ = [
    "AUTHORSHIP_STATEMENT",
    "PROPOSAL_FORGE_SCHEMA",
    "PROPOSAL_FORGE_PREFLIGHT_SCHEMA",
    "PROPOSAL_PURPOSE",
    "LocalProposalForge",
    "OpaqueProposalHandle",
    "PromotionDisposition",
    "ProposalForgeError",
    "ProposalForgeOutcome",
    "ProposalPromotionResult",
    "ProposalReview",
    "QuarantinedProposal",
    "ReviewedFinalApplier",
]
