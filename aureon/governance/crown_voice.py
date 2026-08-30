"""Trusted Crown/Queen peer-voice receipts for two-rune governance.

The Crown voice is deliberately independent from the Druid Council.  Public
issuance accepts only proposal anchors plus a preconfigured resolver; callers
cannot provide the Queen identity, issuer, verdict receipt identifier, source
timestamp, HNC/Auris identifiers, or provider-moment digest.

``TrustedCrownVoiceResolver`` is a composition-root trust boundary, not magic
authentication supplied by a Python protocol.  Production code must construct
an allowlisted resolver backed by the authenticated Queen/Chief runtime and
must never accept a resolver implementation from request data or a plugin.

Every emitted artifact is evidence only.  Even ``APPROVE`` keeps every action,
accounting, learning, provider, route-gate, and economic flag false.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    FUTURE_SKEW_S,
    validate_provider_moment,
)

CROWN_SCHEMA = "aureon.crown_voice.v1"
VERDICT_EVIDENCE_SCHEMA = "aureon.queen_verdict.evaluation.v1"

_CROWN_PREFIX = "queen:governance:"
_VERDICT_PREFIX = "queen:verdict:"
_HNC_PREFIX = "hnc:live_field:"
_AURIS_PREFIX = "auris:cosmic_state:"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

_VERDICT_DECISIONS = {
    "APPROVED": "APPROVE",
    "VETO": "ABORT",
    "CONCERNED": "HOLD",
    "TEACHING_MOMENT": "HOLD",
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

_CROWN_LIVE_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "decision",
        "reason",
        "resolver_id",
        "issuer_id",
        "crown_identity",
        "verdict_source_id",
        "issuer_binding_digest",
        "queen_verdict",
        "queen_evaluated",
        "verdict_evidence_id",
        "proposal_digest",
        "prompt_digest",
        "hnc_receipt_id",
        "auris_receipt_id",
        "provider_receipt_ids",
        "provider_moment_digest",
        "source_timestamp",
        "input_receipt_ids",
        "data_status",
        "truth_status",
        "freshness_status",
        "equation_inputs_complete",
        "generated_values",
        "route_authorization_required",
        "derived_at",
        *_FALSE_FLAGS,
    }
)

_CROWN_NO_DATA_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "decision",
        "reason",
        "resolver_id",
        "issuer_id",
        "crown_identity",
        "verdict_source_id",
        "issuer_binding_digest",
        "queen_verdict",
        "queen_evaluated",
        "verdict_evidence_id",
        "provider_receipt_ids",
        "provider_moment_digest",
        "input_receipt_ids",
        "data_status",
        "truth_status",
        "freshness_status",
        "equation_inputs_complete",
        "generated_values",
        "route_authorization_required",
        *_FALSE_FLAGS,
    }
)


@dataclass(frozen=True)
class ResolvedCrownVoiceEvidence:
    """One authenticated Queen/Chief evaluation and its causal field inputs."""

    resolver_id: str
    issuer_id: str
    crown_identity: str
    verdict_source_id: str
    queen_verdict: str
    queen_evaluated: bool
    reason: str
    proposal_digest: str
    prompt_digest: str
    hnc_evidence: Mapping[str, Any]
    auris_evidence: Mapping[str, Any]


@runtime_checkable
class TrustedCrownVoiceResolver(Protocol):
    """Resolve a Crown evaluation from authenticated local/runtime stores."""

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence | None:
        """Return the evaluated Queen verdict for these exact proposal anchors."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    text = _nonblank(value, name)
    if _DIGEST_RE.fullmatch(text) is None:
        raise ValueError(f"{name}_must_be_sha256")
    return text


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}_must_be_finite")
    return number


def _strings(value: Any, name: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name}_must_be_list")
    items = [_nonblank(item, name) for item in value]
    if items != sorted(set(items)):
        raise ValueError(f"{name}_must_be_sorted_unique")
    if nonempty and not items:
        raise ValueError(f"{name}_required")
    return items


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def _require_false_flags(payload: Mapping[str, Any]) -> None:
    if any(payload.get(name) is not False for name in _FALSE_FLAGS):
        raise ValueError("complete_false_eligibility_flags_required")
    for name, value in payload.items():
        lowered = name.lower()
        if (
            "eligible" in lowered
            or lowered == "actionable"
            or lowered.endswith("_gate_passed")
            or lowered == "economic_mutation"
        ) and value is not False:
            raise ValueError("crown_evidence_must_remain_ineligible")


def _issuer_binding(
    *,
    resolver_id: str,
    issuer_id: str,
    crown_identity: str,
    verdict_source_id: str,
) -> dict[str, str]:
    return {
        "resolver_id": resolver_id,
        "issuer_id": issuer_id,
        "crown_identity": crown_identity,
        "verdict_source_id": verdict_source_id,
    }


def _verdict_evidence_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": VERDICT_EVIDENCE_SCHEMA,
        "receipt_type": "queen_conscience_evaluation",
        "resolver_id": payload["resolver_id"],
        "issuer_id": payload["issuer_id"],
        "crown_identity": payload["crown_identity"],
        "verdict_source_id": payload["verdict_source_id"],
        "queen_verdict": payload["queen_verdict"],
        "queen_evaluated": payload["queen_evaluated"],
        "reason": payload["reason"],
        "proposal_digest": payload["proposal_digest"],
        "prompt_digest": payload["prompt_digest"],
        "hnc_receipt_id": payload["hnc_receipt_id"],
        "auris_receipt_id": payload["auris_receipt_id"],
        "provider_receipt_ids": payload["provider_receipt_ids"],
        "provider_moment_digest": payload["provider_moment_digest"],
        "source_timestamp": payload["source_timestamp"],
    }


def _crown_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in sorted(_CROWN_LIVE_KEYS - {"receipt_id", "derived_at"})
    }


def _no_data(reason: str) -> dict[str, Any]:
    """Return a strict numeric-free HOLD without asserting any causal identity."""

    return {
        "schema": CROWN_SCHEMA,
        "receipt_type": "queen_chief_governance",
        "receipt_id": None,
        "decision": "HOLD",
        "reason": reason,
        "resolver_id": None,
        "issuer_id": None,
        "crown_identity": None,
        "verdict_source_id": None,
        "issuer_binding_digest": None,
        "queen_verdict": None,
        "queen_evaluated": False,
        "verdict_evidence_id": None,
        "provider_receipt_ids": [],
        "provider_moment_digest": None,
        "input_receipt_ids": [],
        "data_status": "no_data",
        "truth_status": "no_data",
        "freshness_status": "no_data",
        "equation_inputs_complete": False,
        "generated_values": False,
        "route_authorization_required": True,
        **_false_flags(),
    }


def issue_crown_voice_receipt(
    *,
    proposal_digest: str,
    prompt_digest: str,
    resolver: TrustedCrownVoiceResolver,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Issue the independent Crown rune from one trusted resolved evaluation."""

    try:
        current = _finite(time.time() if now is None else now, "now")
        age_limit = _finite(max_age_s, "max_age_s")
        if age_limit <= 0.0:
            raise ValueError("positive_max_age_required")
        expected_proposal = _digest(proposal_digest, "proposal_digest")
        expected_prompt = _digest(prompt_digest, "prompt_digest")
        if not isinstance(resolver, TrustedCrownVoiceResolver):
            raise ValueError("trusted_crown_voice_resolver_required")
        resolved = resolver.resolve_crown_voice_evidence(
            expected_proposal,
            expected_prompt,
        )
        if not isinstance(resolved, ResolvedCrownVoiceEvidence):
            raise ValueError("resolved_crown_voice_evidence_required")
        if (
            resolved.proposal_digest != expected_proposal
            or resolved.prompt_digest != expected_prompt
        ):
            raise ValueError("resolved_crown_proposal_binding_mismatch")
        if resolved.queen_evaluated is not True:
            raise ValueError("explicit_evaluated_queen_verdict_required")
        queen_verdict = _nonblank(
            resolved.queen_verdict,
            "queen_verdict",
        ).upper()
        decision = _VERDICT_DECISIONS.get(queen_verdict)
        if decision is None:
            raise ValueError("recognized_queen_verdict_required")
        resolver_id = _nonblank(resolved.resolver_id, "resolver_id")
        issuer_id = _nonblank(resolved.issuer_id, "issuer_id")
        crown_identity = _nonblank(resolved.crown_identity, "crown_identity")
        verdict_source_id = _nonblank(
            resolved.verdict_source_id,
            "verdict_source_id",
        )
        reason = _nonblank(resolved.reason, "reason")
        moment = validate_provider_moment(
            resolved.hnc_evidence,
            resolved.auris_evidence,
            now=current,
            max_age_s=age_limit,
        )
        hnc_id = _nonblank(moment.hnc_receipt_id, "hnc_receipt_id")
        auris_id = _nonblank(moment.auris_receipt_id, "auris_receipt_id")
        if not hnc_id.startswith(_HNC_PREFIX):
            raise ValueError("live_hnc_receipt_required")
        if not auris_id.startswith(_AURIS_PREFIX):
            raise ValueError("live_auris_receipt_required")
        provider_ids = _strings(
            list(moment.provider_receipt_ids),
            "provider_receipt_ids",
            nonempty=True,
        )
        provider_digest = _digest(
            moment.provider_moment_digest,
            "provider_moment_digest",
        )
        source_timestamp = _finite(
            moment.source_timestamp,
            "source_timestamp",
        )
        if (
            source_timestamp > current + FUTURE_SKEW_S
            or current - source_timestamp > age_limit
        ):
            raise ValueError("fresh_crown_provider_moment_required")

        causal_fields = {
            "resolver_id": resolver_id,
            "issuer_id": issuer_id,
            "crown_identity": crown_identity,
            "verdict_source_id": verdict_source_id,
            "queen_verdict": queen_verdict,
            "queen_evaluated": True,
            "reason": reason,
            "proposal_digest": expected_proposal,
            "prompt_digest": expected_prompt,
            "hnc_receipt_id": hnc_id,
            "auris_receipt_id": auris_id,
            "provider_receipt_ids": provider_ids,
            "provider_moment_digest": provider_digest,
            "source_timestamp": source_timestamp,
        }
        verdict_evidence_id = (
            f"{_VERDICT_PREFIX}"
            f"{_sha256(_verdict_evidence_causal(causal_fields))}"
        )
        issuer_binding_digest = _sha256(
            _issuer_binding(
                resolver_id=resolver_id,
                issuer_id=issuer_id,
                crown_identity=crown_identity,
                verdict_source_id=verdict_source_id,
            )
        )
        inputs = sorted(
            {
                hnc_id,
                auris_id,
                verdict_evidence_id,
                *provider_ids,
            }
        )
        causal = {
            "schema": CROWN_SCHEMA,
            "receipt_type": "queen_chief_governance",
            "decision": decision,
            "reason": reason,
            "resolver_id": resolver_id,
            "issuer_id": issuer_id,
            "crown_identity": crown_identity,
            "verdict_source_id": verdict_source_id,
            "issuer_binding_digest": issuer_binding_digest,
            "queen_verdict": queen_verdict,
            "queen_evaluated": True,
            "verdict_evidence_id": verdict_evidence_id,
            "proposal_digest": expected_proposal,
            "prompt_digest": expected_prompt,
            "hnc_receipt_id": hnc_id,
            "auris_receipt_id": auris_id,
            "provider_receipt_ids": provider_ids,
            "provider_moment_digest": provider_digest,
            "source_timestamp": source_timestamp,
            "input_receipt_ids": inputs,
            "data_status": "live",
            "truth_status": "real_derived",
            "freshness_status": "fresh",
            "equation_inputs_complete": True,
            "generated_values": False,
            "route_authorization_required": True,
            **_false_flags(),
        }
        receipt = dict(causal)
        receipt["receipt_id"] = f"{_CROWN_PREFIX}{_sha256(causal)}"
        receipt["derived_at"] = current
        return receipt
    except Exception:
        return _no_data("complete_trusted_linked_crown_evidence_required")


def validate_crown_voice_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate the strict live or numeric-free no-data Crown schema."""

    if not isinstance(receipt, Mapping) or receipt.get("schema") != CROWN_SCHEMA:
        raise ValueError("crown_voice_receipt_required")
    if receipt.get("receipt_type") != "queen_chief_governance":
        raise ValueError("crown_voice_receipt_type_mismatch")
    if receipt.get("data_status") == "no_data":
        if set(receipt) != _CROWN_NO_DATA_KEYS:
            raise ValueError("exact_no_data_crown_schema_required")
        if (
            receipt.get("receipt_id") is not None
            or receipt.get("decision") != "HOLD"
            or receipt.get("resolver_id") is not None
            or receipt.get("issuer_id") is not None
            or receipt.get("crown_identity") is not None
            or receipt.get("verdict_source_id") is not None
            or receipt.get("issuer_binding_digest") is not None
            or receipt.get("queen_verdict") is not None
            or receipt.get("queen_evaluated") is not False
            or receipt.get("verdict_evidence_id") is not None
            or receipt.get("provider_receipt_ids") != []
            or receipt.get("provider_moment_digest") is not None
            or receipt.get("input_receipt_ids") != []
            or receipt.get("truth_status") != "no_data"
            or receipt.get("freshness_status") != "no_data"
            or receipt.get("equation_inputs_complete") is not False
            or receipt.get("generated_values") is not False
            or receipt.get("route_authorization_required") is not True
        ):
            raise ValueError("invalid_no_data_crown_receipt")
        _nonblank(receipt.get("reason"), "reason")
        _require_false_flags(receipt)
        return dict(receipt)
    if set(receipt) != _CROWN_LIVE_KEYS:
        raise ValueError("exact_live_crown_schema_required")
    if (
        receipt.get("data_status") != "live"
        or receipt.get("truth_status") != "real_derived"
        or receipt.get("freshness_status") != "fresh"
        or receipt.get("equation_inputs_complete") is not True
        or receipt.get("generated_values") is not False
        or receipt.get("route_authorization_required") is not True
        or receipt.get("queen_evaluated") is not True
    ):
        raise ValueError("live_real_evaluated_crown_receipt_required")
    _require_false_flags(receipt)
    queen_verdict = _nonblank(
        receipt.get("queen_verdict"),
        "queen_verdict",
    )
    expected_decision = _VERDICT_DECISIONS.get(queen_verdict)
    if expected_decision is None or receipt.get("decision") != expected_decision:
        raise ValueError("queen_verdict_decision_mismatch")
    _nonblank(receipt.get("reason"), "reason")
    resolver_id = _nonblank(receipt.get("resolver_id"), "resolver_id")
    issuer_id = _nonblank(receipt.get("issuer_id"), "issuer_id")
    crown_identity = _nonblank(
        receipt.get("crown_identity"),
        "crown_identity",
    )
    verdict_source_id = _nonblank(
        receipt.get("verdict_source_id"),
        "verdict_source_id",
    )
    expected_binding = _sha256(
        _issuer_binding(
            resolver_id=resolver_id,
            issuer_id=issuer_id,
            crown_identity=crown_identity,
            verdict_source_id=verdict_source_id,
        )
    )
    if receipt.get("issuer_binding_digest") != expected_binding:
        raise ValueError("crown_issuer_binding_mismatch")
    _digest(receipt.get("proposal_digest"), "proposal_digest")
    _digest(receipt.get("prompt_digest"), "prompt_digest")
    hnc_id = _nonblank(receipt.get("hnc_receipt_id"), "hnc_receipt_id")
    auris_id = _nonblank(receipt.get("auris_receipt_id"), "auris_receipt_id")
    if not hnc_id.startswith(_HNC_PREFIX):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith(_AURIS_PREFIX):
        raise ValueError("live_auris_receipt_required")
    provider_ids = _strings(
        receipt.get("provider_receipt_ids"),
        "provider_receipt_ids",
        nonempty=True,
    )
    _digest(
        receipt.get("provider_moment_digest"),
        "provider_moment_digest",
    )
    verdict_evidence_id = _nonblank(
        receipt.get("verdict_evidence_id"),
        "verdict_evidence_id",
    )
    expected_verdict_id = (
        f"{_VERDICT_PREFIX}"
        f"{_sha256(_verdict_evidence_causal(receipt))}"
    )
    if verdict_evidence_id != expected_verdict_id:
        raise ValueError("queen_verdict_evidence_hash_mismatch")
    expected_inputs = sorted(
        {hnc_id, auris_id, verdict_evidence_id, *provider_ids}
    )
    if _strings(
        receipt.get("input_receipt_ids"),
        "input_receipt_ids",
        nonempty=True,
    ) != expected_inputs:
        raise ValueError("exact_crown_input_lineage_required")
    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    source_time = _finite(receipt.get("source_timestamp"), "source_timestamp")
    if (
        age_limit <= 0.0
        or source_time > current + FUTURE_SKEW_S
        or current - source_time > age_limit
    ):
        raise ValueError("fresh_crown_source_timestamp_required")
    _finite(receipt.get("derived_at"), "derived_at")
    if receipt.get("receipt_id") != f"{_CROWN_PREFIX}{_sha256(_crown_causal(receipt))}":
        raise ValueError("crown_voice_receipt_hash_mismatch")
    return dict(receipt)


__all__ = [
    "CROWN_SCHEMA",
    "ResolvedCrownVoiceEvidence",
    "TrustedCrownVoiceResolver",
    "VERDICT_EVIDENCE_SCHEMA",
    "issue_crown_voice_receipt",
    "validate_crown_voice_receipt",
]
