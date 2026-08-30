"""Parallel Druid Council and Queen/Chief dual-key governance."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from aureon.governance.crown_voice import (
    CROWN_SCHEMA,
    validate_crown_voice_receipt,
)
from aureon.swarm.druidic_council import (
    DEFAULT_MAX_AGE_S,
    FUTURE_SKEW_S,
    validate_council_receipt,
)

QUEEN_SCHEMA = "aureon.queen_chief_governance.v1"
DUAL_KEY_SCHEMA = "aureon.dual_key_governance.v1"
RUNE_VOICES = ("druid_council", "queen_chief")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_QUEEN_DECISIONS = frozenset({"APPROVE", "HOLD", "ABORT"})
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


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}_must_be_finite")
    return number


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    text = _text(value, name)
    if _DIGEST_RE.fullmatch(text) is None:
        raise ValueError(f"{name}_must_be_sha256")
    return text


def _ids(values: Sequence[str]) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("input_receipt_ids_required")
    normalized = [_text(value, "input_receipt_id") for value in values]
    if normalized != sorted(set(normalized)):
        raise ValueError("input_receipt_ids_must_be_sorted_unique")
    return normalized


def _provider_source_timestamp(value: Any) -> str:
    number = Decimal(str(_finite(value, "source_timestamp")))
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if Decimal(canonical) == 0:
        return "0"
    return canonical


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def _require_false_flags(payload: Mapping[str, Any]) -> None:
    for name, value in payload.items():
        lowered = name.lower()
        is_eligibility_field = (
            name in _FALSE_FLAGS
            or "eligible" in lowered
            or lowered == "actionable"
            or lowered.endswith("_gate_passed")
            or lowered == "economic_mutation"
        )
        if is_eligibility_field and value is not False:
            raise ValueError("governance_receipt_must_remain_ineligible")
    if any(payload.get(name) is not False for name in _FALSE_FLAGS):
        raise ValueError("complete_governance_ineligibility_flags_required")


def _queen_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": payload["schema"],
        "receipt_type": payload["receipt_type"],
        "decision": payload["decision"],
        "reason": payload["reason"],
        "proposal_digest": payload["proposal_digest"],
        "prompt_digest": payload["prompt_digest"],
        "hnc_receipt_id": payload["hnc_receipt_id"],
        "auris_receipt_id": payload["auris_receipt_id"],
        "source_timestamp": payload["source_timestamp"],
        "input_receipt_ids": payload["input_receipt_ids"],
        "data_status": payload["data_status"],
        "truth_status": payload["truth_status"],
        "freshness_status": payload["freshness_status"],
        "equation_inputs_complete": payload["equation_inputs_complete"],
        "generated_values": payload["generated_values"],
        "route_authorization_required": payload["route_authorization_required"],
        **_false_flags(),
    }


def _dual_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": payload["schema"],
        "receipt_type": payload["receipt_type"],
        "decision": payload["decision"],
        "reason": payload["reason"],
        "proposal_digest": payload["proposal_digest"],
        "prompt_digest": payload["prompt_digest"],
        "hnc_receipt_id": payload["hnc_receipt_id"],
        "auris_receipt_id": payload["auris_receipt_id"],
        "council_receipt_id": payload["council_receipt_id"],
        "queen_receipt_id": payload["queen_receipt_id"],
        "provider_receipt_ids": payload["provider_receipt_ids"],
        "provider_moment_digest": payload["provider_moment_digest"],
        "provider_source_timestamp": payload["provider_source_timestamp"],
        "source_timestamp": payload["source_timestamp"],
        "input_receipt_ids": payload["input_receipt_ids"],
        "rune_voices": payload["rune_voices"],
        "voices_required": payload["voices_required"],
        "voices_present": payload["voices_present"],
        "lineage_alignment": payload["lineage_alignment"],
        "harmonic_outcome": payload["harmonic_outcome"],
        "data_status": payload["data_status"],
        "truth_status": payload["truth_status"],
        "freshness_status": payload["freshness_status"],
        "equation_inputs_complete": payload["equation_inputs_complete"],
        "generated_values": payload["generated_values"],
        "route_authorization_required": payload["route_authorization_required"],
        **_false_flags(),
    }


def build_queen_receipt(
    *,
    decision: str,
    reason: str,
    proposal_digest: str,
    prompt_digest: str,
    hnc_receipt_id: str,
    auris_receipt_id: str,
    source_timestamp: float,
    input_receipt_ids: Sequence[str] | None = None,
    derived_at: float | None = None,
) -> dict[str, Any]:
    """Build a Queen/Chief receipt that remains evidence-only."""

    verdict = _text(decision, "decision").upper()
    if verdict not in _QUEEN_DECISIONS:
        raise ValueError("invalid_queen_decision")
    hnc_id = _text(hnc_receipt_id, "hnc_receipt_id")
    auris_id = _text(auris_receipt_id, "auris_receipt_id")
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith("auris:cosmic_state:"):
        raise ValueError("live_auris_receipt_required")
    receipt_ids = _ids(
        sorted({hnc_id, auris_id})
        if input_receipt_ids is None
        else input_receipt_ids
    )
    if receipt_ids != sorted({hnc_id, auris_id}):
        raise ValueError("exact_hnc_auris_links_required")
    causal = {
        "schema": QUEEN_SCHEMA,
        "receipt_type": "queen_chief_governance",
        "decision": verdict,
        "reason": _text(reason, "reason"),
        "proposal_digest": _digest(proposal_digest, "proposal_digest"),
        "prompt_digest": _digest(prompt_digest, "prompt_digest"),
        "hnc_receipt_id": hnc_id,
        "auris_receipt_id": auris_id,
        "source_timestamp": _finite(source_timestamp, "source_timestamp"),
        "input_receipt_ids": receipt_ids,
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        "route_authorization_required": True,
        **_false_flags(),
    }
    receipt = dict(causal)
    receipt["receipt_id"] = f"queen:governance:{_sha256(causal)}"
    receipt["derived_at"] = _finite(
        time.time() if derived_at is None else derived_at,
        "derived_at",
    )
    return receipt


def validate_queen_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("schema") != QUEEN_SCHEMA:
        raise ValueError("queen_receipt_required")
    if receipt.get("receipt_type") != "queen_chief_governance":
        raise ValueError("queen_receipt_type_mismatch")
    if receipt.get("decision") not in _QUEEN_DECISIONS:
        raise ValueError("invalid_queen_decision")
    _text(receipt.get("reason"), "reason")
    if receipt.get("data_status") != "live" or receipt.get("truth_status") != "real_derived":
        raise ValueError("live_real_queen_receipt_required")
    if receipt.get("freshness_status") != "fresh":
        raise ValueError("fresh_queen_receipt_required")
    if receipt.get("equation_inputs_complete") is not True:
        raise ValueError("complete_queen_receipt_required")
    if receipt.get("generated_values") is not False:
        raise ValueError("generated_queen_receipt_forbidden")
    if receipt.get("route_authorization_required") is not True:
        raise ValueError("route_authorization_boundary_required")
    _require_false_flags(receipt)
    _digest(receipt.get("proposal_digest"), "proposal_digest")
    _digest(receipt.get("prompt_digest"), "prompt_digest")
    hnc_id = _text(receipt.get("hnc_receipt_id"), "hnc_receipt_id")
    auris_id = _text(receipt.get("auris_receipt_id"), "auris_receipt_id")
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith("auris:cosmic_state:"):
        raise ValueError("live_auris_receipt_required")
    receipt_ids = _ids(receipt.get("input_receipt_ids", []))
    if receipt_ids != sorted({hnc_id, auris_id}):
        raise ValueError("exact_hnc_auris_links_required")
    source_time = _finite(receipt.get("source_timestamp"), "source_timestamp")
    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    if age_limit <= 0.0:
        raise ValueError("positive_max_age_required")
    if source_time > current + FUTURE_SKEW_S or current - source_time > age_limit:
        raise ValueError("stale_queen_receipt")
    if "derived_at" in receipt:
        _finite(receipt["derived_at"], "derived_at")
    causal = _queen_causal(receipt)
    required_keys = set(causal) | {"receipt_id"}
    allowed_keys = required_keys | {"derived_at"}
    if not required_keys.issubset(receipt) or not set(receipt).issubset(allowed_keys):
        raise ValueError("exact_queen_receipt_schema_required")
    if receipt.get("receipt_id") != f"queen:governance:{_sha256(causal)}":
        raise ValueError("queen_receipt_hash_mismatch")
    return dict(receipt)


def _no_data(reason: str) -> dict[str, Any]:
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


def _normalized_identity(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().casefold()


def _council_voice_identities(receipt: Mapping[str, Any]) -> set[str]:
    """Collect issuer identities only where the Council schema represents one."""

    identities: set[str] = set()
    for field in ("issuer_id", "council_identity"):
        normalized = _normalized_identity(receipt.get(field))
        if normalized is not None:
            identities.add(normalized)
    for collection_name in ("seat_summaries", "seat_receipts"):
        collection = receipt.get(collection_name)
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, Mapping):
                continue
            for field in ("issuer_id", "agent_id"):
                normalized = _normalized_identity(item.get(field))
                if normalized is not None:
                    identities.add(normalized)
    return identities


def _require_independent_crown_identity(
    council: Mapping[str, Any],
    crown: Mapping[str, Any],
) -> None:
    """Reject one identity speaking as both Druid Council and Crown voice."""

    if crown.get("schema") != CROWN_SCHEMA:
        return
    council_identities = _council_voice_identities(council)
    crown_identities = {
        normalized
        for field in ("issuer_id", "crown_identity", "verdict_source_id")
        if (normalized := _normalized_identity(crown.get(field))) is not None
    }
    if council_identities.intersection(crown_identities):
        raise ValueError("council_and_crown_issuer_identity_must_be_independent")


def _joined_provider_moment(
    council: Mapping[str, Any],
    queen: Mapping[str, Any],
) -> tuple[list[str], str | None]:
    """Return the exact provider moment shared by the two strict voices.

    Legacy Queen receipts pre-date provider-receipt lineage. They remain
    independently valid evidence, but their joined receipt carries an explicit
    empty provider moment instead of claiming data that was never supplied.
    """

    if queen.get("schema") != CROWN_SCHEMA:
        return [], None
    provider_ids = _ids(queen.get("provider_receipt_ids", []))
    if not provider_ids:
        raise ValueError("crown_provider_moment_required")
    provider_digest = _digest(
        queen.get("provider_moment_digest"),
        "provider_moment_digest",
    )
    # Council v2 may contain either legacy seat wrappers or trusted wrappers.
    # When the trusted provider fields are present, the generic join checks them;
    # cognition_gate additionally proves them against retained full node bodies.
    linked_seats = council.get("seat_receipts")
    if isinstance(linked_seats, list) and linked_seats:
        seat_moments = {
            (
                tuple(seat.get("provider_receipt_ids", [])),
                seat.get("provider_moment_digest"),
            )
            for seat in linked_seats
            if isinstance(seat, Mapping) and "provider_receipt_ids" in seat
        }
        if seat_moments and seat_moments != {(tuple(provider_ids), provider_digest)}:
            raise ValueError("dual_key_provider_moment_mismatch")
    return provider_ids, provider_digest


def join_dual_key(
    council_receipt: Mapping[str, Any],
    queen_receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Join the peer Council and Queen/Chief receipts over one proposal."""

    current = time.time() if now is None else now
    try:
        council = validate_council_receipt(
            council_receipt,
            now=current,
            max_age_s=max_age_s,
        )
        if queen_receipt.get("schema") == CROWN_SCHEMA:
            queen = validate_crown_voice_receipt(
                queen_receipt,
                now=current,
                max_age_s=max_age_s,
            )
        else:
            queen = validate_queen_receipt(
                queen_receipt,
                now=current,
                max_age_s=max_age_s,
            )
        _require_independent_crown_identity(council, queen)
        binding_fields = (
            "proposal_digest",
            "prompt_digest",
            "hnc_receipt_id",
            "auris_receipt_id",
        )
        if any(council[field] != queen[field] for field in binding_fields):
            raise ValueError("dual_key_lineage_mismatch")
        if council["source_timestamp"] != queen["source_timestamp"]:
            raise ValueError("dual_key_harmonic_timestamp_mismatch")
        provider_ids, provider_digest = _joined_provider_moment(council, queen)
    except (AttributeError, KeyError, TypeError, ValueError):
        return _no_data("complete_fresh_matching_council_and_queen_receipts_required")

    if council["decision"] == "ABORT" or queen["decision"] == "ABORT":
        decision, reason = "ABORT", "peer_abort_dominates"
        harmonic_outcome = "ABORT"
    elif council["decision"] == "ACCEPT" and queen["decision"] == "APPROVE":
        decision, reason = "ACCEPT", "council_and_queen_dual_key_passed"
        harmonic_outcome = "CONSTRUCTIVE"
    else:
        decision, reason = "HOLD", "both_governance_keys_required"
        harmonic_outcome = "HOLD"
    input_ids = sorted(
        {
            council["receipt_id"],
            queen["receipt_id"],
            council["hnc_receipt_id"],
            council["auris_receipt_id"],
        }
    )
    rune_voices = list(RUNE_VOICES)
    causal = {
        "schema": DUAL_KEY_SCHEMA,
        "receipt_type": "druid_queen_dual_key",
        "decision": decision,
        "reason": reason,
        "proposal_digest": council["proposal_digest"],
        "prompt_digest": council["prompt_digest"],
        "hnc_receipt_id": council["hnc_receipt_id"],
        "auris_receipt_id": council["auris_receipt_id"],
        "council_receipt_id": council["receipt_id"],
        "queen_receipt_id": queen["receipt_id"],
        "provider_receipt_ids": provider_ids,
        "provider_moment_digest": provider_digest,
        "provider_source_timestamp": _provider_source_timestamp(
            council["source_timestamp"]
        ),
        "source_timestamp": council["source_timestamp"],
        "input_receipt_ids": input_ids,
        "rune_voices": rune_voices,
        "voices_required": len(RUNE_VOICES),
        "voices_present": len(rune_voices),
        "lineage_alignment": "exact_proposal_hnc_auris_provider_moment",
        "harmonic_outcome": harmonic_outcome,
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        "route_authorization_required": True,
        **_false_flags(),
    }
    receipt = dict(causal)
    receipt["receipt_id"] = f"governance:dual_key:{_sha256(causal)}"
    receipt["derived_at"] = _finite(current, "now")
    return receipt


def validate_dual_key_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate the final two-rune artifact independently of its producer."""

    if not isinstance(receipt, Mapping) or receipt.get("schema") != DUAL_KEY_SCHEMA:
        raise ValueError("dual_key_receipt_required")
    if receipt.get("receipt_type") != "druid_queen_dual_key":
        raise ValueError("dual_key_receipt_type_mismatch")
    if receipt.get("decision") not in {"ACCEPT", "HOLD", "ABORT"}:
        raise ValueError("invalid_dual_key_decision")
    _text(receipt.get("reason"), "reason")
    if receipt.get("data_status") != "live" or receipt.get("truth_status") != "real_derived":
        raise ValueError("live_real_dual_key_receipt_required")
    if receipt.get("freshness_status") != "fresh":
        raise ValueError("fresh_dual_key_receipt_required")
    if receipt.get("equation_inputs_complete") is not True:
        raise ValueError("complete_dual_key_receipt_required")
    if receipt.get("generated_values") is not False:
        raise ValueError("generated_dual_key_receipt_forbidden")
    if receipt.get("route_authorization_required") is not True:
        raise ValueError("route_authorization_boundary_required")
    _require_false_flags(receipt)
    _digest(receipt.get("proposal_digest"), "proposal_digest")
    _digest(receipt.get("prompt_digest"), "prompt_digest")
    hnc_id = _text(receipt.get("hnc_receipt_id"), "hnc_receipt_id")
    auris_id = _text(receipt.get("auris_receipt_id"), "auris_receipt_id")
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith("auris:cosmic_state:"):
        raise ValueError("live_auris_receipt_required")
    council_id = _text(receipt.get("council_receipt_id"), "council_receipt_id")
    queen_id = _text(receipt.get("queen_receipt_id"), "queen_receipt_id")
    if not council_id.startswith("druid:council:"):
        raise ValueError("druid_council_receipt_required")
    if not queen_id.startswith("queen:governance:"):
        raise ValueError("queen_governance_receipt_required")
    provider_ids = _ids(receipt.get("provider_receipt_ids", []))
    provider_digest = receipt.get("provider_moment_digest")
    if provider_ids:
        _digest(provider_digest, "provider_moment_digest")
    elif provider_digest is not None:
        raise ValueError("provider_moment_digest_requires_provider_receipts")
    receipt_ids = _ids(receipt.get("input_receipt_ids", []))
    if receipt_ids != sorted({hnc_id, auris_id, council_id, queen_id}):
        raise ValueError("exact_dual_key_input_lineage_required")
    if receipt.get("rune_voices") != list(RUNE_VOICES):
        raise ValueError("exact_two_rune_voices_required")
    for field in ("voices_required", "voices_present"):
        value = receipt.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value != len(
            RUNE_VOICES
        ):
            raise ValueError("exact_two_rune_voices_required")
    if (
        receipt.get("lineage_alignment")
        != "exact_proposal_hnc_auris_provider_moment"
    ):
        raise ValueError("exact_dual_key_lineage_alignment_required")
    expected_harmonic = {
        "ACCEPT": "CONSTRUCTIVE",
        "HOLD": "HOLD",
        "ABORT": "ABORT",
    }[receipt["decision"]]
    if receipt.get("harmonic_outcome") != expected_harmonic:
        raise ValueError("dual_key_harmonic_outcome_mismatch")
    source_time = _finite(receipt.get("source_timestamp"), "source_timestamp")
    if receipt.get("provider_source_timestamp") != _provider_source_timestamp(
        source_time
    ):
        raise ValueError("provider_source_timestamp_mismatch")
    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    if age_limit <= 0.0:
        raise ValueError("positive_max_age_required")
    if source_time > current + FUTURE_SKEW_S or current - source_time > age_limit:
        raise ValueError("stale_dual_key_receipt")
    if "derived_at" in receipt:
        _finite(receipt["derived_at"], "derived_at")
    causal = _dual_causal(receipt)
    required_keys = set(causal) | {"receipt_id"}
    allowed_keys = required_keys | {"derived_at"}
    if not required_keys.issubset(receipt) or not set(receipt).issubset(allowed_keys):
        raise ValueError("exact_dual_key_receipt_schema_required")
    if receipt.get("receipt_id") != f"governance:dual_key:{_sha256(causal)}":
        raise ValueError("dual_key_receipt_hash_mismatch")
    return dict(receipt)


__all__ = [
    "DUAL_KEY_SCHEMA",
    "QUEEN_SCHEMA",
    "RUNE_VOICES",
    "build_queen_receipt",
    "join_dual_key",
    "validate_dual_key_receipt",
    "validate_queen_receipt",
]
