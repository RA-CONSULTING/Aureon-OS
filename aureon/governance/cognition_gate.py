"""Fail-closed adapter between cognition and two-rune governance receipts.

This module never reads the ThoughtBus, an advisory prompt router, or a provider
directly, and it grants no route authority.  It exposes two pure joins: a
proposal-bound HNC coherence decision over a caller-captured canonical field,
and the independent Council/Crown dual-key join used for authority-bearing
routes.  Both remain evidence-only.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol, runtime_checkable

from aureon.core.hnc_field import CanonicalField, validate_canonical_field_snapshot
from aureon.governance.crown_voice import (
    CROWN_SCHEMA,
    validate_crown_voice_receipt,
)
from aureon.governance.dual_key import (
    DUAL_KEY_SCHEMA,
    join_dual_key,
    validate_dual_key_receipt,
)
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_auris_node_receipt,
)
from aureon.swarm.druidic_council import (
    FUTURE_SKEW_S,
    REQUIRED_SEATS,
    validate_council_receipt,
)

PROPOSAL_SCHEMA = "aureon.cognition_governance_proposal.v1"
DISABLED_SCHEMA = "aureon.cognition_governance_disabled.v1"
HNC_COHERENCE_REQUEST_SCHEMA = "aureon.hnc_coherence.request.v1"
HNC_COHERENCE_DECISION_SCHEMA = "aureon.hnc_coherence.decision.v1"
HNC_COHERENCE_POLICY_VERSION = "aureon.hnc_coherence.policy.v1"
# These values are part of the v1 receipt contract.  Changing an upstream
# Council/Auris constant must not silently change the meaning of an existing
# signed/hash-bound policy label; a semantic change requires policy.v2.
HNC_POLICY_V1_ACTIVE_THRESHOLD = 0.80
HNC_POLICY_V1_LIGHTHOUSE_THRESHOLD = 0.945
HNC_POLICY_V1_MAX_AGE_S = 300.0
HNC_POLICY_V1_FUTURE_SKEW_S = 5.0
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

_HNC_EFFECT_THRESHOLDS = {
    "read_only": HNC_POLICY_V1_ACTIVE_THRESHOLD,
    "local_mutation": HNC_POLICY_V1_ACTIVE_THRESHOLD,
    "external_mutation": HNC_POLICY_V1_LIGHTHOUSE_THRESHOLD,
    "economic_mutation": HNC_POLICY_V1_LIGHTHOUSE_THRESHOLD,
    "privileged": HNC_POLICY_V1_LIGHTHOUSE_THRESHOLD,
}
_HNC_OUTCOMES = frozenset({"PROCEED", "REPAIR", "HOLD", "ABORT"})
_HNC_FLOWS = frozenset({"EXPAND", "STEADY", "OBSERVE", "REPAIR"})

_QUEEN_DECISION = {
    "APPROVED": "APPROVE",
    "CONCERNED": "HOLD",
    "TEACHING_MOMENT": "HOLD",
    "VETO": "ABORT",
}
_AUTHORITY_FAMILIES = frozenset({
    "office_admin_workweek",
    "safe_accounting_context",
    "safe_trading_cognition",
})
_AUTHORITY_ROUTE_KEYS = frozenset({
    "live_input_env_required",
    "live_mutation_gates",
    "manual_filing_required",
    "restart_handoff_required",
    "submit_env_required",
})
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


@dataclass(frozen=True)
class CognitionGovernanceRequest:
    """Immutable proposal material presented to each trusted voice supplier."""

    schema: str
    prompt_digest: str
    proposal_digest: str
    proposal_json: str
    provider_receipt_ids: tuple[str, ...]
    provider_moment_digest: str
    provider_source_timestamp: str
    target_provider_receipt_ids: tuple[str, ...]
    target_provider_moment_digest: str
    target_provider_source_timestamp: str
    queen_verdict: str


@dataclass(frozen=True)
class HNCCoherenceRequest:
    """Exact, non-authorizing action material presented to the HNC policy."""

    schema: str
    proposal_digest: str
    effect: str
    operation_id: str


@dataclass(frozen=True)
class TrustedCouncilEvidence:
    """Council receipt plus the full validated Auris-node bodies it used."""

    council_receipt: Mapping[str, Any]
    auris_node_receipts: tuple[Mapping[str, Any], ...]


@runtime_checkable
class TrustedCouncilReceiptSupplier(Protocol):
    """Allowlisted composition-root adapter for the independent Council voice.

    Structural conformance is not authentication. Production must inject an
    allowlisted local adapter; request data and plugins may never choose it.
    """

    supplier_id: str

    def supply_council_evidence(
        self,
        request: CognitionGovernanceRequest,
    ) -> TrustedCouncilEvidence:
        """Return the Council receipt and all four retained node receipts."""


@runtime_checkable
class TrustedCrownReceiptSupplier(Protocol):
    """Allowlisted composition-root adapter for the independent Crown voice."""

    supplier_id: str

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> Mapping[str, Any]:
        """Return one strict CROWN_SCHEMA receipt for this proposal."""


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _hnc_digest(value: str, name: str) -> str:
    candidate = _nonblank(value, name)
    digest = candidate.rsplit(":", 1)[-1]
    if _DIGEST_RE.fullmatch(digest) is None:
        raise ValueError(f"{name}_must_end_with_sha256")
    return candidate


def build_hnc_coherence_request(
    *,
    proposal_digest: str,
    effect: str,
    operation_id: str,
) -> HNCCoherenceRequest:
    """Freeze trusted action classification and the exact proposal digest."""

    normalized_effect = str(effect or "").strip().lower()
    if normalized_effect not in {*_HNC_EFFECT_THRESHOLDS, "unknown"}:
        raise ValueError("recognized_hnc_effect_required")
    return HNCCoherenceRequest(
        schema=HNC_COHERENCE_REQUEST_SCHEMA,
        proposal_digest=_hnc_digest(proposal_digest, "proposal_digest"),
        effect=normalized_effect,
        operation_id=_nonblank(operation_id, "operation_id"),
    )


def _hnc_no_data(
    request: HNCCoherenceRequest,
    reason: str,
    *,
    outcome: str = "REPAIR",
) -> dict[str, Any]:
    """Return a numeric-free adaptive decision, never a fabricated receipt."""

    normalized_outcome = outcome if outcome in _HNC_OUTCOMES else "ABORT"
    return {
        "schema": HNC_COHERENCE_DECISION_SCHEMA,
        "receipt_type": "hnc_coherence_decision",
        "receipt_id": None,
        "policy_version": HNC_COHERENCE_POLICY_VERSION,
        "proposal_digest": request.proposal_digest,
        "effect": request.effect,
        "operation_id": request.operation_id,
        "outcome": normalized_outcome,
        "flow": "REPAIR",
        "reason": reason,
        "threshold": None,
        "coherence_gamma": None,
        "hnc_receipt_id": None,
        "hnc_source_timestamp": None,
        "hnc_received_at": None,
        "hnc_input_receipt_ids": [],
        "hnc_field_digest": None,
        "checked_at": None,
        "data_status": "no_data",
        "truth_status": "no_data",
        "freshness_status": "no_data",
        "equation_inputs_complete": False,
        "generated_values": False,
        "coherence_satisfied": False,
        "repair_safe_only": normalized_outcome == "REPAIR",
        "route_authorization_required": True,
        "execution_invariants_preserved": True,
        "economic_eligible": False,
        **_false_flags(),
    }


def _hnc_flow(gamma: float) -> str:
    if gamma >= HNC_POLICY_V1_LIGHTHOUSE_THRESHOLD:
        return "EXPAND"
    if gamma >= HNC_POLICY_V1_ACTIVE_THRESHOLD:
        return "STEADY"
    return "REPAIR"


def evaluate_hnc_coherence(
    request: HNCCoherenceRequest,
    *,
    canonical_field: CanonicalField | Mapping[str, Any],
    now: float | None = None,
) -> dict[str, Any]:
    """Evaluate one exact proposal against one freshly revalidated HNC moment.

    ``PROCEED`` means only that the proposal is coherent enough to continue to
    its independent route authorization.  It never authorizes a handler,
    provider mutation, payment, filing, trade, or privileged machine action.
    """

    if not isinstance(request, HNCCoherenceRequest):
        raise TypeError("hnc_coherence_request_required")
    if request.schema != HNC_COHERENCE_REQUEST_SCHEMA:
        raise ValueError("unsupported_hnc_coherence_request_schema")
    if request.effect == "unknown":
        return _hnc_no_data(request, "known_effect_class_required", outcome="ABORT")
    current = time.time() if now is None else float(now)
    if not math.isfinite(current):
        raise ValueError("finite_hnc_check_time_required")
    try:
        field = validate_canonical_field_snapshot(canonical_field, now=current)
    except (TypeError, ValueError):
        return _hnc_no_data(request, "complete_fresh_canonical_hnc_field_required")
    threshold = float(_HNC_EFFECT_THRESHOLDS[request.effect])
    gamma = float(field.coherence_gamma)  # validated as finite by hnc_field
    flow = _hnc_flow(gamma)
    if gamma >= threshold:
        outcome = "PROCEED"
        reason = "coherence_threshold_satisfied_route_authorization_still_required"
    elif gamma < HNC_POLICY_V1_ACTIVE_THRESHOLD:
        outcome = "REPAIR"
        reason = "coherence_below_active_threshold_repair_flow"
    else:
        outcome = "HOLD"
        flow = "OBSERVE"
        reason = "coherence_below_consequential_effect_threshold"
    field_payload = field.to_dict()
    field_digest = hashlib.sha256(
        _canonical_json(field_payload).encode("utf-8")
    ).hexdigest()
    payload = {
        "schema": HNC_COHERENCE_DECISION_SCHEMA,
        "receipt_type": "hnc_coherence_decision",
        "receipt_id": "",
        "policy_version": HNC_COHERENCE_POLICY_VERSION,
        "proposal_digest": request.proposal_digest,
        "effect": request.effect,
        "operation_id": request.operation_id,
        "outcome": outcome,
        "flow": flow,
        "reason": reason,
        "threshold": threshold,
        "coherence_gamma": gamma,
        "hnc_receipt_id": field.receipt_id,
        "hnc_source_timestamp": field.source_timestamp,
        "hnc_received_at": field.received_at,
        "hnc_input_receipt_ids": list(field.input_receipt_ids),
        "hnc_field_digest": field_digest,
        "checked_at": current,
        "data_status": field.data_status,
        "truth_status": field.truth_status,
        "freshness_status": field.freshness_status,
        "equation_inputs_complete": field.equation_inputs_complete,
        "generated_values": field.generated_values,
        "coherence_satisfied": outcome == "PROCEED",
        "repair_safe_only": outcome == "REPAIR",
        "route_authorization_required": True,
        "execution_invariants_preserved": True,
        "economic_eligible": False,
        **_false_flags(),
    }
    causal = dict(payload)
    causal.pop("receipt_id")
    payload["receipt_id"] = (
        "hnc:coherence_decision:"
        + hashlib.sha256(_canonical_json(causal).encode("utf-8")).hexdigest()
    )
    return validate_hnc_coherence_decision(
        payload,
        expected_proposal_digest=request.proposal_digest,
        now=current,
    )


def validate_hnc_coherence_decision(
    receipt: Mapping[str, Any],
    *,
    expected_proposal_digest: str | None = None,
    now: float | None = None,
    max_age_s: float = HNC_POLICY_V1_MAX_AGE_S,
) -> dict[str, Any]:
    """Strictly validate a hash-bound, evidence-only HNC decision receipt."""

    if not isinstance(receipt, Mapping):
        raise TypeError("hnc_coherence_decision_receipt_required")
    payload = dict(receipt)
    expected_keys = {
        "schema", "receipt_type", "receipt_id", "policy_version",
        "proposal_digest", "effect", "operation_id", "outcome", "flow",
        "reason", "threshold", "coherence_gamma", "hnc_receipt_id",
        "hnc_source_timestamp", "hnc_received_at", "hnc_input_receipt_ids",
        "hnc_field_digest", "checked_at", "data_status", "truth_status",
        "freshness_status", "equation_inputs_complete", "generated_values",
        "coherence_satisfied", "repair_safe_only",
        "route_authorization_required", "execution_invariants_preserved",
        "economic_eligible", *_FALSE_FLAGS,
    }
    if set(payload) != expected_keys:
        raise ValueError("exact_hnc_coherence_decision_schema_required")
    if (
        payload["schema"] != HNC_COHERENCE_DECISION_SCHEMA
        or payload["receipt_type"] != "hnc_coherence_decision"
        or payload["policy_version"] != HNC_COHERENCE_POLICY_VERSION
        or payload["effect"] not in _HNC_EFFECT_THRESHOLDS
        or payload["outcome"] not in _HNC_OUTCOMES
        or payload["flow"] not in _HNC_FLOWS
        or payload["data_status"] != "live"
        or payload["truth_status"] != "real_derived"
        or payload["freshness_status"] != "fresh"
        or payload["equation_inputs_complete"] is not True
        or payload["generated_values"] is not False
        or payload["route_authorization_required"] is not True
        or payload["execution_invariants_preserved"] is not True
        or payload["economic_eligible"] is not False
        or any(payload[name] is not False for name in _FALSE_FLAGS)
    ):
        raise ValueError("valid_evidence_only_hnc_coherence_decision_required")
    proposal_digest = _hnc_digest(payload["proposal_digest"], "proposal_digest")
    if expected_proposal_digest is not None and proposal_digest != _hnc_digest(
        expected_proposal_digest,
        "expected_proposal_digest",
    ):
        raise ValueError("hnc_decision_proposal_mismatch")
    _nonblank(payload["operation_id"], "operation_id")
    _nonblank(payload["reason"], "reason")
    hnc_id = _nonblank(payload["hnc_receipt_id"], "hnc_receipt_id")
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if _DIGEST_RE.fullmatch(_nonblank(payload["hnc_field_digest"], "hnc_field_digest")) is None:
        raise ValueError("hnc_field_digest_must_be_sha256")
    raw_ids = payload["hnc_input_receipt_ids"]
    if (
        not isinstance(raw_ids, list)
        or not raw_ids
        or raw_ids != sorted(set(raw_ids))
        or any(not isinstance(value, str) or not value.strip() for value in raw_ids)
    ):
        raise ValueError("sorted_unique_hnc_input_receipt_ids_required")
    numeric_names = (
        "threshold", "coherence_gamma", "hnc_source_timestamp",
        "hnc_received_at", "checked_at",
    )
    numbers: dict[str, float] = {}
    for name in numeric_names:
        value = payload[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}_must_be_finite")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name}_must_be_finite")
        numbers[name] = number
    if not 0.0 <= numbers["coherence_gamma"] <= 1.0:
        raise ValueError("coherence_gamma_out_of_range")
    if numbers["threshold"] != float(_HNC_EFFECT_THRESHOLDS[payload["effect"]]):
        raise ValueError("effect_threshold_mismatch")
    current = time.time() if now is None else float(now)
    age_limit = float(max_age_s)
    if (
        not math.isfinite(current)
        or not math.isfinite(age_limit)
        or age_limit <= 0.0
        or age_limit > HNC_POLICY_V1_MAX_AGE_S
        or numbers["hnc_source_timestamp"] > current + HNC_POLICY_V1_FUTURE_SKEW_S
        or numbers["hnc_received_at"] > current + HNC_POLICY_V1_FUTURE_SKEW_S
        or numbers["checked_at"] > current + HNC_POLICY_V1_FUTURE_SKEW_S
        or current - numbers["hnc_source_timestamp"] > age_limit
        or current - numbers["hnc_received_at"] > age_limit
        or current - numbers["checked_at"] > age_limit
    ):
        raise ValueError("fresh_hnc_coherence_decision_required")
    gamma = numbers["coherence_gamma"]
    expected_proceed = gamma >= numbers["threshold"]
    if expected_proceed:
        expected_outcome = "PROCEED"
        expected_flow = _hnc_flow(gamma)
        expected_reason = "coherence_threshold_satisfied_route_authorization_still_required"
    elif gamma < HNC_POLICY_V1_ACTIVE_THRESHOLD:
        expected_outcome = "REPAIR"
        expected_flow = "REPAIR"
        expected_reason = "coherence_below_active_threshold_repair_flow"
    else:
        expected_outcome = "HOLD"
        expected_flow = "OBSERVE"
        expected_reason = "coherence_below_consequential_effect_threshold"
    if payload["coherence_satisfied"] is not expected_proceed:
        raise ValueError("coherence_outcome_mismatch")
    if (
        payload["outcome"] != expected_outcome
        or payload["flow"] != expected_flow
        or payload["reason"] != expected_reason
    ):
        raise ValueError("deterministic_hnc_policy_mismatch")
    if payload["repair_safe_only"] is not (payload["outcome"] == "REPAIR"):
        raise ValueError("repair_flow_binding_mismatch")
    receipt_id = _nonblank(payload["receipt_id"], "receipt_id")
    causal = dict(payload)
    causal.pop("receipt_id")
    expected_id = (
        "hnc:coherence_decision:"
        + hashlib.sha256(_canonical_json(causal).encode("utf-8")).hexdigest()
    )
    if receipt_id != expected_id:
        raise ValueError("hnc_coherence_decision_digest_mismatch")
    return payload


def _no_data(reason: str) -> dict[str, Any]:
    """Return a numeric-free HOLD that cannot be mistaken for a receipt."""

    return {
        "schema": DUAL_KEY_SCHEMA,
        "receipt_type": "druid_queen_dual_key",
        "receipt_id": None,
        "decision": "HOLD",
        "reason": reason,
        "data_status": "no_data",
        "truth_status": "no_data",
        "freshness_status": "no_data",
        "equation_inputs_complete": False,
        "generated_values": False,
        "input_receipt_ids": [],
        "rune_voices": [],
        "lineage_alignment": "unavailable",
        "harmonic_outcome": "HOLD",
        "route_authorization_required": True,
        **_false_flags(),
    }


def _json_value(value: Any, path: str = "proposal") -> Any:
    """Normalize JSON material without inventing string representations."""

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}_must_be_finite")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}_keys_must_be_strings")
            normalized[key] = _json_value(nested, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _json_value(nested, f"{path}[{index}]")
            for index, nested in enumerate(value)
        ]
    raise ValueError(f"{path}_must_be_json_material")


def _tool_call(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        tool = value.get("tool")
        arguments = value.get("arguments", {})
        blocked = value.get("blocked", False)
    else:
        tool = getattr(value, "tool", None)
        arguments = getattr(value, "arguments", {})
        blocked = getattr(value, "blocked", False)
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("tool_name_required")
    if not isinstance(arguments, Mapping) or type(blocked) is not bool:
        raise ValueError("valid_tool_call_required")
    return {
        "tool": tool.strip(),
        "arguments": _json_value(arguments, "tool.arguments"),
        "blocked": blocked,
    }


def _provider_moment(
    acquisition: Mapping[str, Any] | None,
) -> tuple[list[str], str, str, dict[str, Any]]:
    if not isinstance(acquisition, Mapping):
        raise ValueError("provider_moment_acquisition_required")
    raw_ids = acquisition.get("provider_receipt_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("provider_receipt_ids_required")
    provider_ids = [_nonblank(value, "provider_receipt_id") for value in raw_ids]
    if provider_ids != sorted(set(provider_ids)):
        raise ValueError("provider_receipt_ids_must_be_sorted_unique")
    provider_digest = _nonblank(
        acquisition.get("provider_moment_digest"),
        "provider_moment_digest",
    )
    if _DIGEST_RE.fullmatch(provider_digest) is None:
        raise ValueError("provider_moment_digest_must_be_sha256")
    raw_source_time = acquisition.get("provider_source_timestamp")
    if raw_source_time is None:
        legacy_source_time = acquisition.get("source_timestamp")
        if (
            isinstance(legacy_source_time, bool)
            or not isinstance(legacy_source_time, (int, float))
            or not math.isfinite(float(legacy_source_time))
        ):
            raise ValueError("provider_source_timestamp_required")
        source_time = _source_timestamp_text(legacy_source_time)
    else:
        source_time = _canonical_decimal_text(raw_source_time)
    normalized = dict(_json_value(dict(acquisition), "acquisition"))
    normalized.pop("source_timestamp", None)
    normalized["provider_receipt_ids"] = provider_ids
    normalized["provider_moment_digest"] = provider_digest
    normalized["provider_source_timestamp"] = source_time
    return provider_ids, provider_digest, source_time, normalized


def _governance_provider_moments(
    acquisition: Mapping[str, Any] | None,
) -> tuple[
    list[str],
    str,
    str,
    list[str],
    str,
    str,
    dict[str, Any],
]:
    """Separate the field moment which seats voices from the route target moment.

    Existing cognition proposals carry one provider moment and therefore use it
    for both roles. Economic proposals may additionally carry an explicit
    ``field_provider_*`` triple. The ordinary ``provider_*`` triple always
    remains the target acquisition and is hash-bound in the proposal.
    """

    target_ids, target_digest, target_time, normalized = _provider_moment(acquisition)
    assert isinstance(acquisition, Mapping)
    field_names = (
        "field_provider_receipt_ids",
        "field_provider_moment_digest",
        "field_provider_source_timestamp",
    )
    field_presence = tuple(name in acquisition for name in field_names)
    if any(field_presence) and not all(field_presence):
        raise ValueError("complete_field_provider_moment_required")
    if not any(field_presence):
        return (
            target_ids,
            target_digest,
            target_time,
            target_ids,
            target_digest,
            target_time,
            normalized,
        )
    field_acquisition = {
        "provider_receipt_ids": acquisition["field_provider_receipt_ids"],
        "provider_moment_digest": acquisition["field_provider_moment_digest"],
        "provider_source_timestamp": acquisition["field_provider_source_timestamp"],
    }
    field_ids, field_digest, field_time, _ = _provider_moment(field_acquisition)
    normalized["field_provider_receipt_ids"] = field_ids
    normalized["field_provider_moment_digest"] = field_digest
    normalized["field_provider_source_timestamp"] = field_time
    return (
        field_ids,
        field_digest,
        field_time,
        target_ids,
        target_digest,
        target_time,
        normalized,
    )


def _canonical_decimal_text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("provider_source_timestamp_must_be_canonical_decimal_text")
    if "e" in value.lower() or value.startswith("+"):
        raise ValueError("provider_source_timestamp_must_be_canonical_decimal_text")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(
            "provider_source_timestamp_must_be_canonical_decimal_text"
        ) from exc
    if not number.is_finite():
        raise ValueError("provider_source_timestamp_must_be_finite")
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if Decimal(canonical) == 0:
        canonical = "0"
    if value != canonical:
        raise ValueError("provider_source_timestamp_must_be_canonical_decimal_text")
    return canonical


def _source_timestamp_text(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("source_timestamp_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("source_timestamp_must_be_finite")
    canonical = format(Decimal(str(number)), "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if Decimal(canonical) == 0:
        canonical = "0"
    return _canonical_decimal_text(canonical)


def build_cognition_governance_request(
    *,
    prompt: str,
    answer: str,
    tool_calls: Sequence[Any] = (),
    capability: Mapping[str, Any] | None = None,
    bake: Mapping[str, Any] | None = None,
    acquisition: Mapping[str, Any] | None = None,
    queen_verdict: str,
) -> CognitionGovernanceRequest:
    """Bind the exact proposed answer and measured turn ledger to SHA-256."""

    if not isinstance(prompt, str) or not isinstance(answer, str):
        raise ValueError("prompt_and_answer_must_be_text")
    verdict = str(queen_verdict or "").strip().upper()
    if verdict not in _QUEEN_DECISION:
        raise ValueError("recognized_queen_verdict_required")
    (
        field_provider_ids,
        field_provider_digest,
        field_source_time,
        target_provider_ids,
        target_provider_digest,
        target_source_time,
        normalized_acquisition,
    ) = _governance_provider_moments(acquisition)
    proposal = {
        "schema": PROPOSAL_SCHEMA,
        "prompt": prompt,
        "answer": answer,
        "tool_calls": [_tool_call(item) for item in tool_calls],
        "capability": _json_value(dict(capability or {}), "capability"),
        "bake": _json_value(dict(bake or {}), "bake"),
        "acquisition": normalized_acquisition,
    }
    canonical = json.dumps(
        proposal,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return CognitionGovernanceRequest(
        schema=PROPOSAL_SCHEMA,
        prompt_digest=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        proposal_digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        proposal_json=canonical,
        provider_receipt_ids=tuple(field_provider_ids),
        provider_moment_digest=field_provider_digest,
        provider_source_timestamp=field_source_time,
        target_provider_receipt_ids=tuple(target_provider_ids),
        target_provider_moment_digest=target_provider_digest,
        target_provider_source_timestamp=target_source_time,
        queen_verdict=verdict,
    )


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _validated_council_evidence(
    supplier: TrustedCouncilReceiptSupplier,
    evidence: Any,
    *,
    now: float,
    max_age_s: float,
) -> tuple[dict[str, Any], list[str], str, float, str]:
    if not isinstance(evidence, TrustedCouncilEvidence):
        raise ValueError("trusted_council_evidence_required")
    supplier_id = _nonblank(supplier.supplier_id, "council_supplier_id")
    council = validate_council_receipt(
        evidence.council_receipt,
        now=now,
        max_age_s=max_age_s,
    )
    raw_nodes = evidence.auris_node_receipts
    if not isinstance(raw_nodes, tuple) or len(raw_nodes) != len(REQUIRED_SEATS):
        raise ValueError("four_retained_auris_node_receipts_required")
    nodes = [
        validate_auris_node_receipt(node, now=now, max_age_s=max_age_s)
        for node in raw_nodes
    ]
    if [node["seat"] for node in nodes] != list(REQUIRED_SEATS):
        raise ValueError("stable_auris_node_order_required")
    if len({node["receipt_id"] for node in nodes}) != len(REQUIRED_SEATS):
        raise ValueError("distinct_auris_node_receipts_required")
    if {node["resolver_id"] for node in nodes} != {supplier_id}:
        raise ValueError("council_supplier_resolver_binding_required")
    provider_id_sets = {
        tuple(node["provider_receipt_ids"])
        for node in nodes
    }
    provider_digests = {node["provider_moment_digest"] for node in nodes}
    if len(provider_id_sets) != 1 or len(provider_digests) != 1:
        raise ValueError("one_exact_node_provider_moment_required")
    for summary, node in zip(council["seat_summaries"], nodes, strict=True):
        if (
            summary["seat"] != node["seat"]
            or summary["agent_id"] != node["agent_id"]
            or summary["gamma"] != node["gamma"]
            or summary["auris_node_receipt_id"] != node["receipt_id"]
            or node["hnc_receipt_id"] != council["hnc_receipt_id"]
            or node["auris_receipt_id"] != council["auris_receipt_id"]
            or node["source_timestamp"] != council["source_timestamp"]
        ):
            raise ValueError("council_seat_must_bind_full_auris_node_receipt")
    return (
        council,
        list(next(iter(provider_id_sets))),
        next(iter(provider_digests)),
        float(council["source_timestamp"]),
        supplier_id,
    )


def _validated_crown_evidence(
    supplier: TrustedCrownReceiptSupplier,
    request: CognitionGovernanceRequest,
    *,
    now: float,
    max_age_s: float,
) -> tuple[dict[str, Any], str]:
    supplier_id = _nonblank(supplier.supplier_id, "crown_supplier_id")
    raw_crown = supplier.supply_crown_receipt(request)
    if not isinstance(raw_crown, Mapping) or raw_crown.get("schema") != CROWN_SCHEMA:
        raise ValueError("strict_crown_voice_receipt_required")
    crown = validate_crown_voice_receipt(
        raw_crown,
        now=now,
        max_age_s=max_age_s,
    )
    if crown.get("resolver_id") != supplier_id:
        raise ValueError("crown_supplier_resolver_binding_required")
    return crown, supplier_id


def evaluate_cognition_governance(
    *,
    prompt: str,
    answer: str,
    queen_verdict: str,
    queen_evaluated: bool,
    council_receipt_supplier: TrustedCouncilReceiptSupplier | None,
    crown_receipt_supplier: TrustedCrownReceiptSupplier | None,
    tool_calls: Sequence[Any] = (),
    capability: Mapping[str, Any] | None = None,
    bake: Mapping[str, Any] | None = None,
    acquisition: Mapping[str, Any] | None = None,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Invoke two trusted voices once and validate their exact harmonic join.

    Any missing dependency, invalid proposal material, supplier failure, Queen
    mismatch, stale receipt, or lineage mismatch becomes numeric-free no-data.
    The returned receipt remains evidence-only even when its decision is ACCEPT.
    """

    if queen_evaluated is not True:
        return _no_data("evaluated_queen_voice_required")
    if (
        not isinstance(council_receipt_supplier, TrustedCouncilReceiptSupplier)
        or not isinstance(crown_receipt_supplier, TrustedCrownReceiptSupplier)
    ):
        return _no_data("independent_council_and_crown_suppliers_required")
    if council_receipt_supplier is crown_receipt_supplier:
        return _no_data("independent_council_and_crown_suppliers_required")
    try:
        request = build_cognition_governance_request(
            prompt=prompt,
            answer=answer,
            tool_calls=tool_calls,
            capability=capability,
            bake=bake,
            acquisition=acquisition,
            queen_verdict=queen_verdict,
        )
        expected_crown_decision = _QUEEN_DECISION[request.queen_verdict]
        current = time.time() if now is None else now
        age_limit = Decimal(str(max_age_s))
        current_decimal = Decimal(str(current))
        request_source_times = (
            Decimal(request.provider_source_timestamp),
            Decimal(request.target_provider_source_timestamp),
        )
        if (
            not math.isfinite(float(current))
            or not age_limit.is_finite()
            or age_limit <= 0
            or age_limit > Decimal(str(DEFAULT_MAX_AGE_S))
            or any(
                source_time > current_decimal + Decimal(str(FUTURE_SKEW_S))
                or current_decimal - source_time > age_limit
                for source_time in request_source_times
            )
        ):
            raise ValueError("fresh_request_provider_moment_required")
        council_bundle = council_receipt_supplier.supply_council_evidence(
            request,
        )
        (
            council,
            provider_ids,
            provider_digest,
            provider_source_time,
            council_supplier_id,
        ) = _validated_council_evidence(
            council_receipt_supplier,
            council_bundle,
            now=current,
            max_age_s=max_age_s,
        )
        if (
            tuple(provider_ids) != request.provider_receipt_ids
            or provider_digest != request.provider_moment_digest
            or _source_timestamp_text(provider_source_time)
            != request.provider_source_timestamp
        ):
            raise ValueError("council_provider_moment_must_match_request_acquisition")
        crown, crown_supplier_id = _validated_crown_evidence(
            crown_receipt_supplier,
            request,
            now=current,
            max_age_s=max_age_s,
        )
        if council_supplier_id.casefold() == crown_supplier_id.casefold():
            raise ValueError("independent_council_and_crown_suppliers_required")
        if (
            crown.get("decision") != expected_crown_decision
            or crown.get("queen_verdict") != request.queen_verdict
            or crown.get("queen_evaluated") is not True
        ):
            raise ValueError("crown_receipt_must_match_evaluated_queen")
        if (
            crown.get("provider_receipt_ids") != provider_ids
            or crown.get("provider_moment_digest") != provider_digest
            or _source_timestamp_text(crown.get("source_timestamp"))
            != request.provider_source_timestamp
        ):
            raise ValueError("council_and_crown_provider_moment_mismatch")
        council_identities = {
            council_supplier_id.casefold(),
            *(
                str(item["agent_id"]).strip().casefold()
                for item in council["seat_summaries"]
            ),
        }
        crown_identities = {
            str(crown[field]).strip().casefold()
            for field in (
                "resolver_id",
                "issuer_id",
                "crown_identity",
                "verdict_source_id",
            )
        }
        if council_identities.intersection(crown_identities):
            raise ValueError("council_and_crown_identity_must_be_independent")
        joined = join_dual_key(
            council,
            crown,
            now=current,
            max_age_s=max_age_s,
        )
        if joined.get("receipt_id") is None:
            return _no_data(str(joined.get("reason") or "dual_key_join_failed"))
        validated = validate_dual_key_receipt(
            joined,
            now=current,
            max_age_s=max_age_s,
        )
        if (
            validated["prompt_digest"] != request.prompt_digest
            or validated["proposal_digest"] != request.proposal_digest
            or tuple(validated["provider_receipt_ids"])
            != request.provider_receipt_ids
            or validated["provider_moment_digest"]
            != request.provider_moment_digest
            or validated["provider_source_timestamp"]
            != request.provider_source_timestamp
            or _source_timestamp_text(validated["source_timestamp"])
            != request.provider_source_timestamp
        ):
            raise ValueError("runtime_proposal_lineage_mismatch")
        return validated
    except (AttributeError, KeyError, TypeError, ValueError):
        return _no_data("complete_fresh_runtime_bound_two_rune_receipts_required")
    except Exception:
        return _no_data("governance_supplier_unavailable")


def authority_route_requires_governance(
    capability: Mapping[str, Any] | None,
) -> bool:
    """Conservatively identify routes that may not use compatibility mode."""

    if not isinstance(capability, Mapping) or capability.get("status") != "ok":
        return True
    families = capability.get("families")
    routes = capability.get("routes")
    if not isinstance(families, list) or not isinstance(routes, list):
        return True
    if any(str(value) in _AUTHORITY_FAMILIES for value in families):
        return True
    for route in routes:
        if not isinstance(route, Mapping):
            return True
        if route.get("requires_human") is True:
            return True
        if str(route.get("risk") or "").strip().lower() == "high":
            return True
        if any(route.get(key) not in (None, False, "", []) for key in _AUTHORITY_ROUTE_KEYS):
            return True
    return False


def explicit_disabled_governance(
    capability: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Describe an explicit compatibility opt-out without granting authority."""

    if authority_route_requires_governance(capability):
        return _no_data("governance_cannot_be_disabled_for_authority_route")
    return {
        "schema": DISABLED_SCHEMA,
        "receipt_type": "cognition_governance_disabled",
        "receipt_id": None,
        "decision": "DISABLED",
        "reason": "explicit_non_authority_compatibility_mode",
        "data_status": "disabled",
        "truth_status": "configuration",
        "freshness_status": "not_applicable",
        "equation_inputs_complete": False,
        "generated_values": False,
        "input_receipt_ids": [],
        "route_authorization_required": True,
        **_false_flags(),
    }


__all__ = [
    "CognitionGovernanceRequest",
    "DISABLED_SCHEMA",
    "HNCCoherenceRequest",
    "HNC_COHERENCE_DECISION_SCHEMA",
    "HNC_COHERENCE_POLICY_VERSION",
    "HNC_COHERENCE_REQUEST_SCHEMA",
    "PROPOSAL_SCHEMA",
    "TrustedCouncilEvidence",
    "TrustedCouncilReceiptSupplier",
    "TrustedCrownReceiptSupplier",
    "authority_route_requires_governance",
    "build_cognition_governance_request",
    "build_hnc_coherence_request",
    "evaluate_cognition_governance",
    "evaluate_hnc_coherence",
    "explicit_disabled_governance",
    "validate_hnc_coherence_decision",
]
