"""Trusted claim and diagnostic authorities for the Kundalini truth gate.

The pure QGITA/Kundalini gate deliberately accepts already-built bundles.  This
module supplies the stricter composition boundary that production code needs:
full hash-bound evidence bodies are validated before their identifiers may be
reduced into a grounding bundle, and QGITA/math-angle diagnostics come from a
separate allowlisted authority.

Nothing in this module performs I/O or establishes factual truth from a score.
Authority objects must be constructed by the composition root from authenticated
stores or providers; request data and plugin objects are not trust anchors.
Every receipt remains evidence-only and grants no tool, learning, accounting, or
economic authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from aureon.governance.qgita_kundalini_truth_gate import (
    DIAGNOSTIC_PREFIX,
    DIAGNOSTIC_SCHEMA,
    FAILURE_KINDS,
    GROUNDING_PREFIX,
    GROUNDING_SCHEMA,
    TrustedDiagnosticResolver,
    TrustedGroundingResolver,
    TruthGateRequest,
    evaluate_truth_gate,
)

EVIDENCE_ITEM_SCHEMA = "aureon.truth-evidence.item.v1"
CLAIM_SET_SCHEMA = "aureon.truth-evidence.claim-set.v1"
DIAGNOSTIC_SIGNAL_SCHEMA = "aureon.truth-evidence.diagnostic-signal.v1"

EVIDENCE_ITEM_PREFIX = "truth-evidence:item:"
CLAIM_SET_PREFIX = "truth-evidence:claim-set:"
DIAGNOSTIC_SIGNAL_PREFIX = "truth-evidence:diagnostic-signal:"
GROUNDING_RESOLVER_ID = "aureon:truth-grounding-resolver:v1"
DIAGNOSTIC_RESOLVER_ID = "aureon:qgita-math-angle-diagnostic-resolver:v1"
FUTURE_SKEW_S = 5.0

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_HNC_ID = re.compile(r"^hnc:live_field:[0-9a-f]{24}$")
_SOURCE_KINDS = frozenset(
    {
        "operator_state",
        "provider_readback",
        "repository_file",
        "user_document",
        "web_response",
    }
)
_SOURCE_URI_PREFIXES = {
    "operator_state": "state://",
    "provider_readback": "provider://",
    "repository_file": "repo://",
    "user_document": "user-doc://",
    "web_response": "https://",
}
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
_EVIDENCE_KEYS = {
    "schema_version",
    "receipt_id",
    "issuer_id",
    "source_kind",
    "source_uri",
    "source_locator",
    "content_digest",
    "source_timestamp",
    "received_at",
    "truth_status",
    "generated_values",
    *_FALSE_FLAGS,
}
_FINDING_KEYS = {"claim_id", "failure_kind", "evidence_receipt_ids"}
_CLAIM_SET_KEYS = {
    "schema_version",
    "receipt_id",
    "authority_id",
    "prompt_digest",
    "answer_digest",
    "hnc_receipt_id",
    "source_timestamp",
    "received_at",
    "truth_status",
    "generated_values",
    "evidence_receipts",
    "claim_findings",
    *_FALSE_FLAGS,
}
_SIGNAL_KEYS = {
    "schema_version",
    "receipt_id",
    "authority_id",
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


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label}_required")
    if len(value) > 65_536:
        raise ValueError(f"{label}_too_large")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX_64.fullmatch(value):
        raise ValueError(f"{label}_must_be_sha256")
    return value


def _finite(value: Any, label: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def _strict(payload: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != keys:
        raise ValueError(f"exact_{label}_required")
    return dict(payload)


def _false_flags(payload: Mapping[str, Any]) -> None:
    if any(payload.get(key) is not False for key in _FALSE_FLAGS):
        raise ValueError("evidence_only_false_flags_required")


def _fresh(payload: Mapping[str, Any], *, now: float, max_age_s: float) -> None:
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


def _receipt(payload: Mapping[str, Any], *, prefix: str) -> None:
    causal = {key: payload[key] for key in payload if key != "receipt_id"}
    if payload.get("receipt_id") != f"{prefix}{_sha256(causal)}":
        raise ValueError("receipt_hash_mismatch")


def _strings(value: Any, label: str, *, nonempty: bool) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label}_required")
    result = [_nonblank(item, label) for item in value]
    if result != sorted(set(result)):
        raise ValueError(f"{label}_must_be_sorted_unique")
    return result


def _flat_diagnostics(values: Any, label: str) -> dict[str, Any]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"{label}_required")
    result: dict[str, Any] = {}
    for key, value in values.items():
        name = _nonblank(key, f"{label}_key")
        if type(value) in {int, float}:
            result[name] = _finite(value, f"{label}_value")
        elif isinstance(value, str):
            result[name] = _nonblank(value, f"{label}_value")
        else:
            raise ValueError(f"flat_{label}_required")
    return result


def validate_evidence_item(
    payload: Mapping[str, Any],
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Validate a full source body before reducing it to a receipt identifier."""

    result = _strict(payload, _EVIDENCE_KEYS, "truth_evidence_item")
    if result["schema_version"] != EVIDENCE_ITEM_SCHEMA:
        raise ValueError("truth_evidence_item_schema_required")
    _nonblank(result["issuer_id"], "issuer_id")
    if result["source_kind"] not in _SOURCE_KINDS:
        raise ValueError("known_source_kind_required")
    source_uri = _nonblank(result["source_uri"], "source_uri")
    if not source_uri.startswith(_SOURCE_URI_PREFIXES[result["source_kind"]]):
        raise ValueError("source_uri_kind_mismatch")
    _nonblank(result["source_locator"], "source_locator")
    _digest(result["content_digest"], "content_digest")
    _fresh(result, now=now, max_age_s=max_age_s)
    if result["truth_status"] != "real_observed" or result["generated_values"] is not False:
        raise ValueError("real_observed_source_required")
    _false_flags(result)
    _receipt(result, prefix=EVIDENCE_ITEM_PREFIX)
    return json.loads(_canonical_json(result))


def validate_claim_evidence_set(
    payload: Mapping[str, Any],
    request: TruthGateRequest,
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Validate full evidence bodies and their claim-level support links."""

    result = _strict(payload, _CLAIM_SET_KEYS, "claim_evidence_set")
    if result["schema_version"] != CLAIM_SET_SCHEMA:
        raise ValueError("claim_evidence_set_schema_required")
    _nonblank(result["authority_id"], "authority_id")
    if (
        result["prompt_digest"] != request.prompt_digest
        or result["answer_digest"] != request.answer_digest
        or result["hnc_receipt_id"] != request.hnc_receipt_id
    ):
        raise ValueError("claim_evidence_lineage_mismatch")
    _fresh(result, now=now, max_age_s=max_age_s)
    if result["truth_status"] != "real_derived" or result["generated_values"] is not False:
        raise ValueError("real_derived_claim_evidence_required")
    raw_evidence = result["evidence_receipts"]
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise ValueError("full_evidence_receipts_required")
    evidence = [
        validate_evidence_item(item, now=now, max_age_s=max_age_s)
        for item in raw_evidence
    ]
    evidence_ids = [item["receipt_id"] for item in evidence]
    if evidence_ids != sorted(set(evidence_ids)):
        raise ValueError("evidence_receipts_must_be_sorted_unique")
    findings = result["claim_findings"]
    if not isinstance(findings, list) or not findings:
        raise ValueError("claim_findings_required")
    normalized_findings: list[dict[str, Any]] = []
    claim_ids: list[str] = []
    for raw in findings:
        finding = _strict(raw, _FINDING_KEYS, "claim_finding")
        claim_id = _digest(finding["claim_id"], "claim_id")
        failure_kind = finding["failure_kind"]
        if failure_kind not in FAILURE_KINDS:
            raise ValueError("known_failure_kind_required")
        links = _strings(
            finding["evidence_receipt_ids"],
            "finding_evidence_receipt_ids",
            nonempty=failure_kind != "MISSING_GROUNDING",
        )
        if any(link not in evidence_ids for link in links):
            raise ValueError("finding_evidence_body_required")
        if failure_kind == "MISSING_GROUNDING" and links:
            raise ValueError("missing_grounding_must_have_no_evidence")
        claim_ids.append(claim_id)
        normalized_findings.append(
            {
                "claim_id": claim_id,
                "failure_kind": failure_kind,
                "evidence_receipt_ids": links,
            }
        )
    if claim_ids != sorted(set(claim_ids)):
        raise ValueError("claim_findings_must_be_sorted_unique")
    _false_flags(result)
    _receipt(result, prefix=CLAIM_SET_PREFIX)
    return json.loads(_canonical_json({**result, "evidence_receipts": evidence, "claim_findings": normalized_findings}))


def validate_diagnostic_signal_set(
    payload: Mapping[str, Any],
    request: TruthGateRequest,
    grounding: Mapping[str, Any],
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Validate separately derived signals without allowing them to decide truth."""

    result = _strict(payload, _SIGNAL_KEYS, "diagnostic_signal_set")
    if result["schema_version"] != DIAGNOSTIC_SIGNAL_SCHEMA:
        raise ValueError("diagnostic_signal_schema_required")
    _nonblank(result["authority_id"], "authority_id")
    if (
        result["grounding_receipt_id"] != grounding.get("receipt_id")
        or result["prompt_digest"] != request.prompt_digest
        or result["answer_digest"] != request.answer_digest
        or result["hnc_receipt_id"] != request.hnc_receipt_id
        or result["evidence_receipt_ids"] != grounding.get("evidence_receipt_ids")
    ):
        raise ValueError("diagnostic_signal_lineage_mismatch")
    _fresh(result, now=now, max_age_s=max_age_s)
    if result["truth_status"] != "real_derived" or result["generated_values"] is not False:
        raise ValueError("real_derived_diagnostic_signal_required")
    _strings(result["evidence_receipt_ids"], "evidence_receipt_ids", nonempty=True)
    _flat_diagnostics(result["qgita_diagnostics"], "qgita_diagnostics")
    _flat_diagnostics(result["math_angle_diagnostics"], "math_angle_diagnostics")
    _false_flags(result)
    _receipt(result, prefix=DIAGNOSTIC_SIGNAL_PREFIX)
    return json.loads(_canonical_json(result))


@runtime_checkable
class TrustedClaimEvidenceAuthority(Protocol):
    """Composition-root authority returning full claim evidence bodies."""

    authority_id: str

    def resolve_claim_evidence(self, request: TruthGateRequest) -> Mapping[str, Any]: ...


@runtime_checkable
class TrustedDiagnosticSignalAuthority(Protocol):
    """Independent authority returning QGITA and math-angle observations."""

    authority_id: str

    def resolve_diagnostic_signals(
        self,
        request: TruthGateRequest,
        grounding: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class ReceiptBackedGroundingResolver:
    """Reduce validated full evidence bodies to the gate's grounding schema."""

    resolver_id = GROUNDING_RESOLVER_ID

    def __init__(
        self,
        *,
        authority: TrustedClaimEvidenceAuthority,
        allowed_authority_ids: frozenset[str],
        allowed_evidence_issuer_ids: frozenset[str],
        now: float,
        max_age_s: float,
    ) -> None:
        if not isinstance(authority, TrustedClaimEvidenceAuthority):
            raise ValueError("trusted_claim_evidence_authority_required")
        if type(allowed_authority_ids) is not frozenset or not allowed_authority_ids:
            raise ValueError("claim_authority_allowlist_required")
        authority_id = _nonblank(authority.authority_id, "claim_authority_id")
        if authority_id not in allowed_authority_ids:
            raise ValueError("allowlisted_claim_authority_required")
        if (
            type(allowed_evidence_issuer_ids) is not frozenset
            or not allowed_evidence_issuer_ids
        ):
            raise ValueError("evidence_issuer_allowlist_required")
        self._authority = authority
        self._authority_id = authority_id
        self._allowed_evidence_issuer_ids = allowed_evidence_issuer_ids
        self._now = _finite(now, "now")
        self._max_age_s = _finite(max_age_s, "max_age_s")

    def resolve_grounding(self, request: TruthGateRequest) -> Mapping[str, Any]:
        raw = self._authority.resolve_claim_evidence(request)
        validated = validate_claim_evidence_set(
            raw,
            request,
            now=self._now,
            max_age_s=self._max_age_s,
        )
        if validated["authority_id"] != self._authority_id:
            raise ValueError("claim_authority_binding_mismatch")
        if any(
            item["issuer_id"] not in self._allowed_evidence_issuer_ids
            for item in validated["evidence_receipts"]
        ):
            raise ValueError("allowlisted_evidence_issuer_required")
        evidence_ids = [item["receipt_id"] for item in validated["evidence_receipts"]]
        causal = {
            "schema_version": GROUNDING_SCHEMA,
            "resolver_id": self.resolver_id,
            "source_claim_set_receipt_id": validated["receipt_id"],
            "prompt_digest": request.prompt_digest,
            "answer_digest": request.answer_digest,
            "hnc_receipt_id": request.hnc_receipt_id,
            "source_timestamp": validated["source_timestamp"],
            "received_at": validated["received_at"],
            "truth_status": "real_derived",
            "generated_values": False,
            "evidence_receipt_ids": evidence_ids,
            "claim_findings": validated["claim_findings"],
            **dict.fromkeys(_FALSE_FLAGS, False),
        }
        return {**causal, "receipt_id": f"{GROUNDING_PREFIX}{_sha256(causal)}"}


class ReceiptBackedDiagnosticResolver:
    """Reduce separately validated signals to the gate's diagnostic schema."""

    resolver_id = DIAGNOSTIC_RESOLVER_ID

    def __init__(
        self,
        *,
        authority: TrustedDiagnosticSignalAuthority,
        allowed_authority_ids: frozenset[str],
        now: float,
        max_age_s: float,
    ) -> None:
        if not isinstance(authority, TrustedDiagnosticSignalAuthority):
            raise ValueError("trusted_diagnostic_signal_authority_required")
        if type(allowed_authority_ids) is not frozenset or not allowed_authority_ids:
            raise ValueError("diagnostic_authority_allowlist_required")
        authority_id = _nonblank(authority.authority_id, "diagnostic_authority_id")
        if authority_id not in allowed_authority_ids:
            raise ValueError("allowlisted_diagnostic_authority_required")
        self._authority = authority
        self._authority_id = authority_id
        self._now = _finite(now, "now")
        self._max_age_s = _finite(max_age_s, "max_age_s")

    def resolve_diagnostics(
        self,
        request: TruthGateRequest,
        grounding: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        raw = self._authority.resolve_diagnostic_signals(request, grounding)
        validated = validate_diagnostic_signal_set(
            raw,
            request,
            grounding,
            now=self._now,
            max_age_s=self._max_age_s,
        )
        if validated["authority_id"] != self._authority_id:
            raise ValueError("diagnostic_authority_binding_mismatch")
        causal = {
            "schema_version": DIAGNOSTIC_SCHEMA,
            "resolver_id": self.resolver_id,
            "source_diagnostic_signal_receipt_id": validated["receipt_id"],
            "grounding_receipt_id": grounding["receipt_id"],
            "prompt_digest": request.prompt_digest,
            "answer_digest": request.answer_digest,
            "hnc_receipt_id": request.hnc_receipt_id,
            "source_timestamp": validated["source_timestamp"],
            "received_at": validated["received_at"],
            "truth_status": "real_derived",
            "generated_values": False,
            "evidence_receipt_ids": validated["evidence_receipt_ids"],
            "qgita_diagnostics": validated["qgita_diagnostics"],
            "math_angle_diagnostics": validated["math_angle_diagnostics"],
            **dict.fromkeys(_FALSE_FLAGS, False),
        }
        return {**causal, "receipt_id": f"{DIAGNOSTIC_PREFIX}{_sha256(causal)}"}


def evaluate_receipt_backed_truth_gate(
    request: TruthGateRequest,
    *,
    claim_authority: TrustedClaimEvidenceAuthority,
    diagnostic_authority: TrustedDiagnosticSignalAuthority,
    allowed_claim_authority_ids: frozenset[str],
    allowed_evidence_issuer_ids: frozenset[str],
    allowed_diagnostic_authority_ids: frozenset[str],
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Evaluate one exact answer through independent full-receipt authorities."""

    if not isinstance(request, TruthGateRequest):
        return evaluate_truth_gate(
            request,
            grounding_resolver=None,  # type: ignore[arg-type]
            diagnostic_resolver=None,  # type: ignore[arg-type]
            allowed_grounding_resolver_ids=frozenset({GROUNDING_RESOLVER_ID}),
            allowed_diagnostic_resolver_ids=frozenset({DIAGNOSTIC_RESOLVER_ID}),
            now=now,
            max_age_s=max_age_s,
        )
    try:
        if (
            claim_authority is diagnostic_authority
            or type(allowed_claim_authority_ids) is not frozenset
            or type(allowed_diagnostic_authority_ids) is not frozenset
            or type(allowed_evidence_issuer_ids) is not frozenset
            or not allowed_claim_authority_ids
            or not allowed_evidence_issuer_ids
            or not allowed_diagnostic_authority_ids
            or any(
                left & right
                for left, right in (
                    (
                        {item.casefold() for item in allowed_claim_authority_ids},
                        {item.casefold() for item in allowed_evidence_issuer_ids},
                    ),
                    (
                        {item.casefold() for item in allowed_claim_authority_ids},
                        {item.casefold() for item in allowed_diagnostic_authority_ids},
                    ),
                    (
                        {item.casefold() for item in allowed_evidence_issuer_ids},
                        {item.casefold() for item in allowed_diagnostic_authority_ids},
                    ),
                )
            )
        ):
            raise ValueError("independent_truth_authorities_required")
        grounding = ReceiptBackedGroundingResolver(
            authority=claim_authority,
            allowed_authority_ids=allowed_claim_authority_ids,
            allowed_evidence_issuer_ids=allowed_evidence_issuer_ids,
            now=now,
            max_age_s=max_age_s,
        )
        diagnostics = ReceiptBackedDiagnosticResolver(
            authority=diagnostic_authority,
            allowed_authority_ids=allowed_diagnostic_authority_ids,
            now=now,
            max_age_s=max_age_s,
        )
    except (AttributeError, TypeError, ValueError):
        # Preserve the gate's canonical numeric-free HOLD shape.
        return evaluate_truth_gate(
            request,
            grounding_resolver=None,  # type: ignore[arg-type]
            diagnostic_resolver=None,  # type: ignore[arg-type]
            allowed_grounding_resolver_ids=frozenset({GROUNDING_RESOLVER_ID}),
            allowed_diagnostic_resolver_ids=frozenset({DIAGNOSTIC_RESOLVER_ID}),
            now=now,
            max_age_s=max_age_s,
        )
    if not isinstance(grounding, TrustedGroundingResolver) or not isinstance(
        diagnostics, TrustedDiagnosticResolver
    ):
        raise AssertionError("internal_truth_resolver_contract_broken")
    return evaluate_truth_gate(
        request,
        grounding_resolver=grounding,
        diagnostic_resolver=diagnostics,
        allowed_grounding_resolver_ids=frozenset({GROUNDING_RESOLVER_ID}),
        allowed_diagnostic_resolver_ids=frozenset({DIAGNOSTIC_RESOLVER_ID}),
        now=now,
        max_age_s=max_age_s,
    )


__all__ = [
    "CLAIM_SET_PREFIX",
    "CLAIM_SET_SCHEMA",
    "DIAGNOSTIC_RESOLVER_ID",
    "DIAGNOSTIC_SIGNAL_PREFIX",
    "DIAGNOSTIC_SIGNAL_SCHEMA",
    "EVIDENCE_ITEM_PREFIX",
    "EVIDENCE_ITEM_SCHEMA",
    "GROUNDING_RESOLVER_ID",
    "ReceiptBackedDiagnosticResolver",
    "ReceiptBackedGroundingResolver",
    "TrustedClaimEvidenceAuthority",
    "TrustedDiagnosticSignalAuthority",
    "evaluate_receipt_backed_truth_gate",
    "validate_claim_evidence_set",
    "validate_diagnostic_signal_set",
    "validate_evidence_item",
]
