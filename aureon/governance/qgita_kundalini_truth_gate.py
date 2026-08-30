"""Evidence-only QGITA, math-angle, and Kundalini correction gate.

Grounding receipts decide whether claims are supported. QGITA and math-angle
are diagnostic views of an already grounded residual: mathematical coherence
is not factual truth. A successful result is only ``READY_FOR_AURIS``; Auris
remains the next independent coherence gate before Hive/Mycelia propagation.

This module is pure. It performs no I/O and grants no action authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

GROUNDING_SCHEMA = "aureon.qgita_kundalini.grounding.v1"
DIAGNOSTIC_SCHEMA = "aureon.qgita_kundalini.diagnostics.v1"
RESULT_SCHEMA = "aureon.qgita_kundalini.result.v1"
GROUNDING_PREFIX = "grounding:truth:"
DIAGNOSTIC_PREFIX = "diagnostic:qgita-math-angle:"
RESULT_PREFIX = "truth-gate:qgita-kundalini:"
CLAIM_SOURCE_PREFIX = "truth-evidence:claim-set:"
DIAGNOSTIC_SOURCE_PREFIX = "truth-evidence:diagnostic-signal:"
FUTURE_SKEW_S = 5.0

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_HNC_ID = re.compile(r"^hnc:live_field:[0-9a-f]{24}$")
_FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "action_gate_passed",
    "actionable",
    "operational_eligible",
    "provider_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)
FAILURE_KINDS = frozenset(
    {
        "SUPPORTED",
        "MISSING_GROUNDING",
        "STALE_OR_LINEAGE",
        "UNSUPPORTED",
        "CONTRADICTED",
        "SEMANTIC_MISMATCH",
        "CROSS_CLAIM_CONFLICT",
    }
)
KUNDALINI_BLOCKERS = (
    ("Root", "MISSING_GROUNDING"),
    ("Sacral", "STALE_OR_LINEAGE"),
    ("Solar Plexus", "UNSUPPORTED"),
    ("Heart", "CONTRADICTED"),
    ("Throat", "SEMANTIC_MISMATCH"),
    ("Third Eye", "CROSS_CLAIM_CONFLICT"),
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX_64.fullmatch(value):
        raise ValueError(f"{label}_must_be_sha256")
    return value


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label}_required")
    return value


def _finite(value: Any, label: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def _fresh_pair(payload: Mapping[str, Any], *, now: float, max_age_s: float) -> None:
    current = _finite(now, "now")
    maximum = _finite(max_age_s, "max_age_s")
    if maximum <= 0:
        raise ValueError("positive_max_age_s_required")
    source = _finite(payload.get("source_timestamp"), "source_timestamp")
    received = _finite(payload.get("received_at"), "received_at")
    if received < source:
        raise ValueError("received_before_source")
    for value in (source, received):
        age = current - value
        if age < -FUTURE_SKEW_S or age > maximum:
            raise ValueError("fresh_evidence_required")


def _strings(value: Any, label: str, *, nonempty: bool) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label}_required")
    result = [_nonblank(item, label) for item in value]
    if result != sorted(set(result)):
        raise ValueError(f"{label}_must_be_sorted_unique")
    return result


def _require_flags(payload: Mapping[str, Any]) -> None:
    if any(payload.get(flag) is not False for flag in _FALSE_FLAGS):
        raise ValueError("evidence_only_false_flags_required")


def _strict(payload: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != keys:
        raise ValueError(f"strict_{label}_required")
    return dict(payload)


def _validate_receipt(payload: Mapping[str, Any], prefix: str) -> None:
    causal = {key: payload[key] for key in payload if key != "receipt_id"}
    if payload.get("receipt_id") != f"{prefix}{_sha256(causal)}":
        raise ValueError("receipt_hash_mismatch")


def _prefixed_receipt_id(value: Any, prefix: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith(prefix)
        or not _HEX_64.fullmatch(value[len(prefix) :])
    ):
        raise ValueError(f"canonical_{label}_required")
    return value


@dataclass(frozen=True, slots=True)
class TruthGateRequest:
    prompt_digest: str
    answer_digest: str
    hnc_receipt_id: str
    correction_attempt: int

    def __post_init__(self) -> None:
        _digest(self.prompt_digest, "prompt_digest")
        _digest(self.answer_digest, "answer_digest")
        if not isinstance(self.hnc_receipt_id, str) or not _HNC_ID.fullmatch(self.hnc_receipt_id):
            raise ValueError("canonical_hnc_receipt_id_required")
        if type(self.correction_attempt) is not int or not 0 <= self.correction_attempt <= 2:
            raise ValueError("correction_attempt_must_be_int_0_to_2")


@runtime_checkable
class TrustedGroundingResolver(Protocol):
    resolver_id: str

    def resolve_grounding(self, request: TruthGateRequest) -> Mapping[str, Any]: ...


@runtime_checkable
class TrustedDiagnosticResolver(Protocol):
    resolver_id: str

    def resolve_diagnostics(
        self,
        request: TruthGateRequest,
        grounding: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


_GROUNDING_KEYS = {
    "schema_version",
    "receipt_id",
    "resolver_id",
    "source_claim_set_receipt_id",
    "prompt_digest",
    "answer_digest",
    "hnc_receipt_id",
    "source_timestamp",
    "received_at",
    "truth_status",
    "generated_values",
    "evidence_receipt_ids",
    "claim_findings",
    *_FALSE_FLAGS,
}
_FINDING_KEYS = {"claim_id", "failure_kind", "evidence_receipt_ids"}
_DIAGNOSTIC_KEYS = {
    "schema_version",
    "receipt_id",
    "resolver_id",
    "source_diagnostic_signal_receipt_id",
    "grounding_receipt_id",
    "prompt_digest",
    "answer_digest",
    "hnc_receipt_id",
    "source_timestamp",
    "received_at",
    "truth_status",
    "generated_values",
    "evidence_receipt_ids",
    "qgita_diagnostics",
    "math_angle_diagnostics",
    *_FALSE_FLAGS,
}


def validate_grounding_bundle(
    payload: Mapping[str, Any],
    request: TruthGateRequest,
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Validate factual grounding; diagnostic mathematics is not used here."""

    result = _strict(payload, _GROUNDING_KEYS, "grounding_bundle")
    if result["schema_version"] != GROUNDING_SCHEMA:
        raise ValueError("grounding_schema_required")
    _nonblank(result["resolver_id"], "resolver_id")
    _prefixed_receipt_id(
        result["source_claim_set_receipt_id"],
        CLAIM_SOURCE_PREFIX,
        "source_claim_set_receipt_id",
    )
    if (
        result["prompt_digest"] != request.prompt_digest
        or result["answer_digest"] != request.answer_digest
        or result["hnc_receipt_id"] != request.hnc_receipt_id
    ):
        raise ValueError("grounding_lineage_mismatch")
    _fresh_pair(result, now=now, max_age_s=max_age_s)
    if result["truth_status"] not in {"real_observed", "real_derived"}:
        raise ValueError("real_grounding_required")
    if result["generated_values"] is not False:
        raise ValueError("generated_grounding_forbidden")
    evidence_ids = _strings(result["evidence_receipt_ids"], "evidence_receipt_ids", nonempty=True)
    findings = result["claim_findings"]
    if not isinstance(findings, list) or not findings:
        raise ValueError("claim_findings_required")
    seen: set[str] = set()
    for raw in findings:
        finding = _strict(raw, _FINDING_KEYS, "claim_finding")
        claim_id = _digest(finding["claim_id"], "claim_id")
        if claim_id in seen:
            raise ValueError("unique_claim_ids_required")
        seen.add(claim_id)
        kind = finding["failure_kind"]
        if kind not in FAILURE_KINDS:
            raise ValueError("known_failure_kind_required")
        links = _strings(
            finding["evidence_receipt_ids"],
            "finding_evidence_receipt_ids",
            nonempty=kind != "MISSING_GROUNDING",
        )
        if any(link not in evidence_ids for link in links):
            raise ValueError("finding_evidence_lineage_mismatch")
        if kind == "MISSING_GROUNDING" and links:
            raise ValueError("missing_grounding_must_have_no_evidence")
    _require_flags(result)
    _validate_receipt(result, GROUNDING_PREFIX)
    return json.loads(_canonical_json(result))


def _validate_diagnostics(values: Any, label: str) -> None:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"{label}_required")
    for key, value in values.items():
        _nonblank(key, f"{label}_key")
        if type(value) in {int, float}:
            _finite(value, f"{label}_value")
        elif isinstance(value, str):
            _nonblank(value, f"{label}_value")
        else:
            raise ValueError(f"flat_{label}_required")


def validate_diagnostic_bundle(
    payload: Mapping[str, Any],
    request: TruthGateRequest,
    grounding: Mapping[str, Any],
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Validate diagnostic lineage; QGITA and phase scores never establish truth."""

    result = _strict(payload, _DIAGNOSTIC_KEYS, "diagnostic_bundle")
    if result["schema_version"] != DIAGNOSTIC_SCHEMA:
        raise ValueError("diagnostic_schema_required")
    _nonblank(result["resolver_id"], "resolver_id")
    _prefixed_receipt_id(
        result["source_diagnostic_signal_receipt_id"],
        DIAGNOSTIC_SOURCE_PREFIX,
        "source_diagnostic_signal_receipt_id",
    )
    if (
        result["grounding_receipt_id"] != grounding.get("receipt_id")
        or result["prompt_digest"] != request.prompt_digest
        or result["answer_digest"] != request.answer_digest
        or result["hnc_receipt_id"] != request.hnc_receipt_id
        or result["evidence_receipt_ids"] != grounding.get("evidence_receipt_ids")
    ):
        raise ValueError("diagnostic_lineage_mismatch")
    _fresh_pair(result, now=now, max_age_s=max_age_s)
    if result["truth_status"] != "real_derived" or result["generated_values"] is not False:
        raise ValueError("real_non_generated_diagnostics_required")
    _strings(result["evidence_receipt_ids"], "evidence_receipt_ids", nonempty=True)
    _validate_diagnostics(result["qgita_diagnostics"], "qgita_diagnostics")
    _validate_diagnostics(result["math_angle_diagnostics"], "math_angle_diagnostics")
    _require_flags(result)
    _validate_receipt(result, DIAGNOSTIC_PREFIX)
    return json.loads(_canonical_json(result))


_RESULT_KEYS = {
    "schema_version",
    "receipt_id",
    "status",
    "reason",
    "prompt_digest",
    "answer_digest",
    "hnc_receipt_id",
    "grounding_receipt_id",
    "diagnostic_receipt_id",
    "kundalini_stage",
    "failure_kind",
    "evidence_receipt_ids",
    "correction_directive",
    *_FALSE_FLAGS,
}


def _result(
    *,
    status: str,
    reason: str,
    request: TruthGateRequest | None,
    grounding_id: str = "",
    diagnostic_id: str = "",
    stage: str = "",
    failure_kind: str = "",
    evidence_ids: list[str] | None = None,
    correction_directive: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    causal = {
        "schema_version": RESULT_SCHEMA,
        "status": status,
        "reason": reason,
        "prompt_digest": request.prompt_digest if request else "",
        "answer_digest": request.answer_digest if request else "",
        "hnc_receipt_id": request.hnc_receipt_id if request else "",
        "grounding_receipt_id": grounding_id,
        "diagnostic_receipt_id": diagnostic_id,
        "kundalini_stage": stage,
        "failure_kind": failure_kind,
        "evidence_receipt_ids": list(evidence_ids or []),
        "correction_directive": dict(correction_directive or {}),
        **dict.fromkeys(_FALSE_FLAGS, False),
    }
    return {**causal, "receipt_id": f"{RESULT_PREFIX}{_sha256(causal)}"}


def validate_truth_gate_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _strict(payload, _RESULT_KEYS, "truth_gate_result")
    if result["schema_version"] != RESULT_SCHEMA:
        raise ValueError("truth_gate_result_schema_required")
    if result["status"] not in {"HOLD", "CORRECTION_REQUIRED", "READY_FOR_AURIS"}:
        raise ValueError("truth_gate_result_status_invalid")
    _nonblank(result["reason"], "reason")
    for key in (
        "prompt_digest",
        "answer_digest",
        "hnc_receipt_id",
        "grounding_receipt_id",
        "diagnostic_receipt_id",
        "kundalini_stage",
        "failure_kind",
    ):
        if not isinstance(result[key], str):
            raise ValueError(f"string_{key}_required")
    _strings(result["evidence_receipt_ids"], "evidence_receipt_ids", nonempty=False)
    if not isinstance(result["correction_directive"], Mapping):
        raise ValueError("correction_directive_mapping_required")
    lineage = (
        result["prompt_digest"],
        result["answer_digest"],
        result["hnc_receipt_id"],
    )
    if any(lineage):
        _digest(result["prompt_digest"], "prompt_digest")
        _digest(result["answer_digest"], "answer_digest")
        if not isinstance(result["hnc_receipt_id"], str) or not _HNC_ID.fullmatch(
            result["hnc_receipt_id"]
        ):
            raise ValueError("canonical_hnc_receipt_id_required")
    elif (
        result["reason"] != "truth_gate_request_required"
        or result["status"] != "HOLD"
        or any(
            result[key]
            for key in (
                "grounding_receipt_id",
                "diagnostic_receipt_id",
                "kundalini_stage",
                "failure_kind",
                "evidence_receipt_ids",
                "correction_directive",
            )
        )
    ):
        raise ValueError("complete_result_lineage_required")
    if result["status"] == "HOLD":
        if result["correction_directive"] or result["diagnostic_receipt_id"] != "":
            raise ValueError("numeric_free_hold_required")
        if bool(result["kundalini_stage"]) != bool(result["failure_kind"]):
            raise ValueError("complete_hold_blocker_required")
        if result["failure_kind"] and dict(KUNDALINI_BLOCKERS).get(
            result["kundalini_stage"]
        ) != result["failure_kind"]:
            raise ValueError("hold_blocker_mapping_mismatch")
    elif result["status"] == "READY_FOR_AURIS":
        if (
            result["kundalini_stage"] != "Crown"
            or result["failure_kind"]
            or result["correction_directive"]
            or not result["evidence_receipt_ids"]
        ):
            raise ValueError("crown_ready_for_auris_required")
        _prefixed_receipt_id(
            result["grounding_receipt_id"], GROUNDING_PREFIX, "grounding_receipt_id"
        )
        _prefixed_receipt_id(
            result["diagnostic_receipt_id"], DIAGNOSTIC_PREFIX, "diagnostic_receipt_id"
        )
    else:
        directive = _strict(
            result["correction_directive"],
            {"failure_kind", "evidence_receipt_ids", "next_attempt"},
            "correction_directive",
        )
        if directive["failure_kind"] != result["failure_kind"]:
            raise ValueError("correction_failure_kind_mismatch")
        if directive["evidence_receipt_ids"] != result["evidence_receipt_ids"]:
            raise ValueError("correction_evidence_mismatch")
        if type(directive["next_attempt"]) is not int or directive["next_attempt"] not in {1, 2}:
            raise ValueError("bounded_next_attempt_required")
        if (
            dict(KUNDALINI_BLOCKERS).get(result["kundalini_stage"])
            != result["failure_kind"]
        ):
            raise ValueError("correction_blocker_binding_mismatch")
        _prefixed_receipt_id(
            result["grounding_receipt_id"], GROUNDING_PREFIX, "grounding_receipt_id"
        )
        _prefixed_receipt_id(
            result["diagnostic_receipt_id"], DIAGNOSTIC_PREFIX, "diagnostic_receipt_id"
        )
    _require_flags(result)
    _validate_receipt(result, RESULT_PREFIX)
    return json.loads(_canonical_json(result))


def evaluate_truth_gate(
    request: TruthGateRequest,
    *,
    grounding_resolver: TrustedGroundingResolver,
    diagnostic_resolver: TrustedDiagnosticResolver,
    allowed_grounding_resolver_ids: frozenset[str],
    allowed_diagnostic_resolver_ids: frozenset[str],
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Return HOLD, bounded correction, or READY_FOR_AURIS—never factual ACCEPT."""

    if not isinstance(request, TruthGateRequest):
        return _result(status="HOLD", reason="truth_gate_request_required", request=None)
    try:
        if (
            type(allowed_grounding_resolver_ids) is not frozenset
            or type(allowed_diagnostic_resolver_ids) is not frozenset
            or not allowed_grounding_resolver_ids
            or not allowed_diagnostic_resolver_ids
            or allowed_grounding_resolver_ids & allowed_diagnostic_resolver_ids
            or grounding_resolver is diagnostic_resolver
        ):
            raise ValueError("independent_resolvers_required")
        grounding_id = _nonblank(grounding_resolver.resolver_id, "grounding_resolver_id")
        diagnostic_id = _nonblank(diagnostic_resolver.resolver_id, "diagnostic_resolver_id")
        if (
            grounding_id not in allowed_grounding_resolver_ids
            or diagnostic_id not in allowed_diagnostic_resolver_ids
            or grounding_id.casefold() == diagnostic_id.casefold()
            or {item.casefold() for item in allowed_grounding_resolver_ids}
            & {item.casefold() for item in allowed_diagnostic_resolver_ids}
        ):
            raise ValueError("allowlisted_resolvers_required")
    except (AttributeError, TypeError, ValueError):
        return _result(status="HOLD", reason="trusted_evidence_required", request=request)
    try:
        raw_grounding = grounding_resolver.resolve_grounding(request)
    except Exception:  # noqa: BLE001 - the injected authority is an isolation boundary
        return _result(status="HOLD", reason="trusted_evidence_required", request=request)
    try:
        grounding = validate_grounding_bundle(
            raw_grounding, request, now=now, max_age_s=max_age_s
        )
        if grounding["resolver_id"] != grounding_id:
            raise ValueError("grounding_resolver_binding_mismatch")
    except (TypeError, ValueError):
        return _result(status="HOLD", reason="trusted_evidence_required", request=request)
    try:
        raw_diagnostic = diagnostic_resolver.resolve_diagnostics(request, grounding)
    except Exception:  # noqa: BLE001 - the injected authority is an isolation boundary
        return _result(status="HOLD", reason="trusted_evidence_required", request=request)
    try:
        diagnostic = validate_diagnostic_bundle(
            raw_diagnostic, request, grounding, now=now, max_age_s=max_age_s
        )
        if diagnostic["resolver_id"] != diagnostic_id:
            raise ValueError("diagnostic_resolver_binding_mismatch")
    except (TypeError, ValueError):
        return _result(status="HOLD", reason="trusted_evidence_required", request=request)

    findings = grounding["claim_findings"]
    kinds = {item["failure_kind"] for item in findings}
    blocker = next(((stage, kind) for stage, kind in KUNDALINI_BLOCKERS if kind in kinds), None)
    evidence_ids = sorted(
        {
            evidence_id
            for item in findings
            if blocker and item["failure_kind"] == blocker[1]
            for evidence_id in item["evidence_receipt_ids"]
        }
    )
    if blocker:
        stage, kind = blocker
        if request.correction_attempt >= 2:
            return _result(
                status="HOLD",
                reason="bounded_correction_exhausted",
                request=request,
                grounding_id=grounding["receipt_id"],
                stage=stage,
                failure_kind=kind,
                evidence_ids=evidence_ids,
            )
        return validate_truth_gate_result(
            _result(
                status="CORRECTION_REQUIRED",
                reason="grounding_correction_required",
                request=request,
                grounding_id=grounding["receipt_id"],
                diagnostic_id=diagnostic["receipt_id"],
                stage=stage,
                failure_kind=kind,
                evidence_ids=evidence_ids,
                correction_directive={
                    "failure_kind": kind,
                    "evidence_receipt_ids": evidence_ids,
                    "next_attempt": request.correction_attempt + 1,
                },
            )
        )
    if kinds != {"SUPPORTED"}:
        return _result(status="HOLD", reason="complete_grounding_required", request=request)
    return validate_truth_gate_result(
        _result(
            status="READY_FOR_AURIS",
            reason="grounding_supported_diagnostics_linked",
            request=request,
            grounding_id=grounding["receipt_id"],
            diagnostic_id=diagnostic["receipt_id"],
            stage="Crown",
            evidence_ids=grounding["evidence_receipt_ids"],
        )
    )


__all__ = [
    "CLAIM_SOURCE_PREFIX",
    "DIAGNOSTIC_PREFIX",
    "DIAGNOSTIC_SOURCE_PREFIX",
    "DIAGNOSTIC_SCHEMA",
    "FAILURE_KINDS",
    "GROUNDING_PREFIX",
    "GROUNDING_SCHEMA",
    "KUNDALINI_BLOCKERS",
    "RESULT_PREFIX",
    "RESULT_SCHEMA",
    "TrustedDiagnosticResolver",
    "TrustedGroundingResolver",
    "TruthGateRequest",
    "evaluate_truth_gate",
    "validate_diagnostic_bundle",
    "validate_grounding_bundle",
    "validate_truth_gate_result",
]
