"""Fail-closed immune-gate aggregation for Plumber v0."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .crypto import domain_hash
from .schema import (
    DenialCode,
    SchemaError,
    format_timestamp,
    parse_timestamp,
    require_aware_datetime,
    require_nonblank,
    require_sha256,
)


class GateClass(StrEnum):
    FIELD = "field"
    IDENTITY = "identity"
    TEMPORAL = "temporal"
    HEART = "heart"
    CONSCIENCE = "conscience"
    GOVERNANCE = "governance"


class GateVerdict(StrEnum):
    APPROVED = "approved"
    DENIED = "denied"


REQUIRED_GATE_CLASSES = tuple(GateClass)


@dataclass(frozen=True, slots=True)
class GateEvidence:
    gate_class: GateClass
    receipt_commitment: str
    valid: bool
    context_commitment: str | None = None
    denial_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            parsed_class = GateClass(self.gate_class)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="gate_class") from exc
        object.__setattr__(self, "gate_class", parsed_class)
        require_sha256(self.receipt_commitment, field="receipt_commitment")
        if type(self.valid) is not bool:
            raise SchemaError(DenialCode.INVALID_TYPE, field="valid")
        if self.context_commitment is not None:
            require_sha256(self.context_commitment, field="context_commitment")
        if not isinstance(self.denial_codes, tuple) or any(
            not isinstance(code, str) or not code for code in self.denial_codes
        ):
            raise SchemaError(DenialCode.INVALID_TYPE, field="denial_codes")
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if self.valid and self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_class": str(self.gate_class),
            "receipt_commitment": self.receipt_commitment,
            "valid": self.valid,
            "context_commitment": self.context_commitment,
            "denial_codes": list(self.denial_codes),
        }


@dataclass(frozen=True, slots=True)
class GateDecision:
    verdict: GateVerdict
    evaluated_classes: tuple[str, ...]
    missing_classes: tuple[str, ...]
    denial_codes: tuple[str, ...]
    packet_inspection_commitment: str
    context_commitment: str
    evidence_commitment: str
    evaluated_at: str
    expires_at: str
    decision_commitment: str
    quarantine_required: bool

    def __post_init__(self) -> None:
        try:
            verdict = GateVerdict(self.verdict)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="verdict") from exc
        object.__setattr__(self, "verdict", verdict)
        for field in (
            "packet_inspection_commitment",
            "context_commitment",
            "evidence_commitment",
            "decision_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        expected_classes = tuple(sorted(str(item) for item in REQUIRED_GATE_CLASSES))
        if tuple(sorted(set(self.evaluated_classes))) != self.evaluated_classes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="evaluated_classes")
        if tuple(sorted(set(self.missing_classes))) != self.missing_classes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="missing_classes")
        if set(self.evaluated_classes) | set(self.missing_classes) != set(expected_classes):
            raise SchemaError(DenialCode.INVALID_VALUE, field="evaluated_classes")
        if set(self.evaluated_classes) & set(self.missing_classes):
            raise SchemaError(DenialCode.INVALID_VALUE, field="missing_classes")
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if type(self.quarantine_required) is not bool:
            raise SchemaError(DenialCode.INVALID_TYPE, field="quarantine_required")
        if (verdict is GateVerdict.APPROVED) == self.quarantine_required:
            raise SchemaError(DenialCode.INVALID_VALUE, field="quarantine_required")
        if verdict is GateVerdict.APPROVED and (
            self.evaluated_classes != expected_classes
            or self.missing_classes
            or self.denial_codes
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="verdict")
        evaluated = parse_timestamp(self.evaluated_at, field="evaluated_at")
        expires = parse_timestamp(self.expires_at, field="expires_at")
        if expires <= evaluated:
            raise SchemaError(DenialCode.INVALID_VALUE, field="expires_at")
        if domain_hash("aureon.plumber.immune-decision.v0", self.commitment_payload()) != self.decision_commitment:
            raise SchemaError(DenialCode.INVALID_VALUE, field="decision_commitment")

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "verdict": str(self.verdict),
            "evaluated_classes": list(self.evaluated_classes),
            "missing_classes": list(self.missing_classes),
            "denial_codes": list(self.denial_codes),
            "packet_inspection_commitment": self.packet_inspection_commitment,
            "context_commitment": self.context_commitment,
            "evidence_commitment": self.evidence_commitment,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
            "quarantine_required": self.quarantine_required,
        }

    def public_summary(self) -> dict[str, Any]:
        return {
            "verdict": str(self.verdict),
            "evaluated_classes": list(self.evaluated_classes),
            "missing_classes": list(self.missing_classes),
            "denial_codes": list(self.denial_codes),
            "packet_inspection_commitment": self.packet_inspection_commitment,
            "context_commitment": self.context_commitment,
            "evidence_commitment": self.evidence_commitment,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
            "decision_commitment": self.decision_commitment,
            "quarantine_required": self.quarantine_required,
            "release_state": "not_released",
        }


def evaluate_immune_gate(
    evidence: Sequence[GateEvidence],
    *,
    packet_inspection_commitment: str,
    evaluated_at: datetime,
    expires_at: datetime,
) -> GateDecision:
    if isinstance(evidence, (str, bytes, bytearray)) or not isinstance(evidence, Sequence):
        raise SchemaError(DenialCode.INVALID_TYPE, field="evidence")
    inspection_commitment = require_sha256(
        packet_inspection_commitment,
        field="packet_inspection_commitment",
    )
    evaluated_at_text = format_timestamp(
        require_aware_datetime(evaluated_at, field="evaluated_at")
    )
    expires_at_text = format_timestamp(
        require_aware_datetime(expires_at, field="expires_at")
    )
    if parse_timestamp(expires_at_text, field="expires_at") <= parse_timestamp(
        evaluated_at_text,
        field="evaluated_at",
    ):
        raise SchemaError(DenialCode.INVALID_VALUE, field="expires_at")
    by_class: dict[GateClass, GateEvidence] = {}
    denials: set[str] = set()
    for item in evidence:
        if not isinstance(item, GateEvidence):
            raise SchemaError(DenialCode.INVALID_TYPE, field="evidence")
        if item.gate_class in by_class:
            denials.add(str(DenialCode.INVALID_SCHEMA))
        else:
            by_class[item.gate_class] = item
        if not item.valid:
            denials.update(item.denial_codes or (str(DenialCode.POLICY_RECEIPT_INVALID),))
    missing = tuple(sorted(str(item) for item in set(REQUIRED_GATE_CLASSES) - set(by_class)))
    if missing:
        denials.add(str(DenialCode.POLICY_RECEIPT_MISSING))
    serialized = [by_class[key].to_dict() for key in sorted(by_class, key=str)]
    supplied_contexts = {
        item.context_commitment
        for item in by_class.values()
        if item.context_commitment is not None
    }
    if len(supplied_contexts) > 1 or (
        supplied_contexts and any(item.context_commitment is None for item in by_class.values())
    ):
        denials.add("gate_context_mismatch")
    context_commitment = (
        next(iter(supplied_contexts))
        if len(supplied_contexts) == 1
        else domain_hash("aureon.plumber.unbound-gate-context.v0", serialized)
    )
    evidence_commitment = domain_hash("aureon.plumber.immune-evidence.v0", serialized)
    denial_tuple = tuple(sorted(denials))
    verdict = GateVerdict.DENIED if denial_tuple else GateVerdict.APPROVED
    payload = {
        "verdict": str(verdict),
        "evaluated_classes": sorted(str(item) for item in by_class),
        "missing_classes": list(missing),
        "denial_codes": list(denial_tuple),
        "packet_inspection_commitment": inspection_commitment,
        "context_commitment": context_commitment,
        "evidence_commitment": evidence_commitment,
        "evaluated_at": evaluated_at_text,
        "expires_at": expires_at_text,
        "quarantine_required": verdict is GateVerdict.DENIED,
    }
    return GateDecision(
        verdict=verdict,
        evaluated_classes=tuple(sorted(str(item) for item in by_class)),
        missing_classes=missing,
        denial_codes=denial_tuple,
        packet_inspection_commitment=inspection_commitment,
        context_commitment=context_commitment,
        evidence_commitment=evidence_commitment,
        evaluated_at=evaluated_at_text,
        expires_at=expires_at_text,
        decision_commitment=domain_hash("aureon.plumber.immune-decision.v0", payload),
        quarantine_required=verdict is GateVerdict.DENIED,
    )


def build_gate_context_commitment(
    *, packet_identity: str, session_identity: str, purpose_commitment: str
) -> str:
    require_nonblank(packet_identity, field="packet_identity")
    require_nonblank(session_identity, field="session_identity")
    require_sha256(purpose_commitment, field="purpose_commitment")
    return domain_hash(
        "aureon.plumber.immune-gate-context.v0",
        {
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "purpose_commitment": purpose_commitment,
        },
    )


__all__ = [
    "GateClass",
    "GateDecision",
    "GateEvidence",
    "GateVerdict",
    "REQUIRED_GATE_CLASSES",
    "evaluate_immune_gate",
    "build_gate_context_commitment",
]
