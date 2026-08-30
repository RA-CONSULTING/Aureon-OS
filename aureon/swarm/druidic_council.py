"""Receipt-bound peer governance for the Aureon Druidic Council.

The Council works beside, never beneath, the Queen/Chief.  This module is
deliberately pure: it neither spawns agents nor grants economic authority.
It only validates real seat receipts and derives a deterministic Council
decision over one immutable proposal and its exact HNC/Auris lineage.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SEAT_SCHEMA = "aureon.druidic_council.seat.v1"
TRUSTED_SEAT_SCHEMA = "aureon.druidic_council.seat.trusted.v1"
COUNCIL_SCHEMA = "aureon.druidic_council.v2"
REQUIRED_SEATS = ("seer", "sentinel", "weaver", "keeper")
ACTIVE_THRESHOLD = 0.80
LIGHTHOUSE_THRESHOLD = 0.945
ACCEPT_SUPPORT_THRESHOLD = 2.0 / 3.0
MIN_DRIVING_SEATS = 3
DEFAULT_MAX_AGE_S = 300.0
FUTURE_SKEW_S = 5.0
PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INVERSE = 1.0 / PHI
PHI_SQUARED = PHI * PHI
PHI_TOPOLOGY = "four_seat_golden_ring.v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_SEAT_DECISIONS = frozenset({"ACCEPT", "HOLD", "ABORT"})
_DECISION_EVIDENCE_PREFIX = "druid:seat_decision:"
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
class CouncilSeat:
    """A stable Council shell occupied by one named agent."""

    name: str
    agent_id: str


@dataclass(frozen=True)
class SeatReceipt:
    """Typed wrapper around a validated immutable seat receipt."""

    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


@dataclass(frozen=True)
class CouncilReceipt:
    """Typed wrapper around a validated Council decision receipt."""

    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


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


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}_must_be_finite")
    return number


def _canonical_float(value: Any, name: str) -> float:
    number = _finite_number(value, name)
    if type(value) is not float:
        raise ValueError(f"{name}_must_be_canonical_float")
    return number


def _canonical_primitive_matches(actual: Any, expected: Any) -> bool:
    """Compare receipt primitives without Python bool/int/float coercion."""

    if type(actual) is not type(expected):
        return False
    if isinstance(expected, float):
        return math.isfinite(actual) and actual.hex() == expected.hex()
    return actual == expected


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    text = _nonblank(value, name)
    if _DIGEST_RE.fullmatch(text) is None:
        raise ValueError(f"{name}_must_be_sha256")
    return text


def _receipt_ids(values: Sequence[str]) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("input_receipt_ids_required")
    normalized = [_nonblank(value, "input_receipt_id") for value in values]
    if normalized != sorted(set(normalized)):
        raise ValueError("input_receipt_ids_must_be_sorted_unique")
    return normalized


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


def voice_for_gamma(gamma: float) -> tuple[str, float]:
    """Return the deterministic voice band and raw coherence weight."""

    value = _finite_number(gamma, "gamma")
    if not 0.0 <= value <= 1.0:
        raise ValueError("gamma_out_of_range")
    if value < ACTIVE_THRESHOLD:
        return "ADVISORY", 0.0
    if value < LIGHTHOUSE_THRESHOLD:
        return "ACTIVE", value
    return "LIGHTHOUSE", value


def _seat_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    causal = {
        "schema": payload["schema"],
        "receipt_type": payload["receipt_type"],
        "seat": payload["seat"],
        "agent_id": payload["agent_id"],
        "decision": payload["decision"],
        "reason": payload["reason"],
        "gamma": payload["gamma"],
        "voice_band": payload["voice_band"],
        "voice_weight": payload["voice_weight"],
        "proposal_digest": payload["proposal_digest"],
        "prompt_digest": payload["prompt_digest"],
        "hnc_receipt_id": payload["hnc_receipt_id"],
        "auris_receipt_id": payload["auris_receipt_id"],
        "auris_node_receipt_id": payload["auris_node_receipt_id"],
        "source_timestamp": payload["source_timestamp"],
        "input_receipt_ids": payload["input_receipt_ids"],
        "data_status": payload["data_status"],
        "truth_status": payload["truth_status"],
        "freshness_status": payload["freshness_status"],
        "equation_inputs_complete": payload["equation_inputs_complete"],
        "generated_values": payload["generated_values"],
        **_false_flags(),
    }
    if payload["schema"] == TRUSTED_SEAT_SCHEMA:
        causal.update(
            {
                "resolver_id": payload["resolver_id"],
                "issuer_id": payload["issuer_id"],
                "decision_source_id": payload["decision_source_id"],
                "issuer_binding_digest": payload["issuer_binding_digest"],
                "decision_evidence_id": payload["decision_evidence_id"],
                "provider_receipt_ids": payload["provider_receipt_ids"],
                "provider_moment_digest": payload["provider_moment_digest"],
                "auris_node_receipt": payload["auris_node_receipt"],
            }
        )
    return causal


def _issuer_binding(
    *,
    resolver_id: str,
    issuer_id: str,
    decision_source_id: str,
    seat: str,
    agent_id: str,
) -> dict[str, str]:
    return {
        "resolver_id": resolver_id,
        "issuer_id": issuer_id,
        "decision_source_id": decision_source_id,
        "seat": seat,
        "agent_id": agent_id,
    }


def _decision_evidence_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "resolver_id": payload["resolver_id"],
        "issuer_id": payload["issuer_id"],
        "decision_source_id": payload["decision_source_id"],
        "issuer_binding_digest": payload["issuer_binding_digest"],
        "seat": payload["seat"],
        "agent_id": payload["agent_id"],
        "decision": payload["decision"],
        "reason": payload["reason"],
        "proposal_digest": payload["proposal_digest"],
        "prompt_digest": payload["prompt_digest"],
        "hnc_receipt_id": payload["hnc_receipt_id"],
        "auris_receipt_id": payload["auris_receipt_id"],
        "auris_node_receipt_id": payload["auris_node_receipt_id"],
        "provider_receipt_ids": payload["provider_receipt_ids"],
        "provider_moment_digest": payload["provider_moment_digest"],
        "source_timestamp": payload["source_timestamp"],
    }


def build_seat_receipt(
    *,
    seat: str,
    agent_id: str,
    decision: str,
    reason: str,
    gamma: float,
    proposal_digest: str,
    prompt_digest: str,
    hnc_receipt_id: str,
    auris_receipt_id: str,
    auris_node_receipt_id: str,
    source_timestamp: float,
    input_receipt_ids: Sequence[str] | None = None,
    derived_at: float | None = None,
) -> dict[str, Any]:
    """Build a deterministic, non-economic receipt for one Council seat."""

    seat_name = _nonblank(seat, "seat").lower()
    if seat_name not in REQUIRED_SEATS:
        raise ValueError("unknown_council_seat")
    verdict = _nonblank(decision, "decision").upper()
    if verdict not in _SEAT_DECISIONS:
        raise ValueError("invalid_seat_decision")
    hnc_id = _nonblank(hnc_receipt_id, "hnc_receipt_id")
    auris_id = _nonblank(auris_receipt_id, "auris_receipt_id")
    node_id = _nonblank(auris_node_receipt_id, "auris_node_receipt_id")
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith("auris:cosmic_state:"):
        raise ValueError("live_auris_receipt_required")
    if not node_id.startswith("auris:node:"):
        raise ValueError("seat_auris_node_receipt_required")
    source_time = _finite_number(source_timestamp, "source_timestamp")
    band, weight = voice_for_gamma(gamma)
    ids = _receipt_ids(
        sorted({hnc_id, auris_id, node_id})
        if input_receipt_ids is None
        else input_receipt_ids
    )
    if ids != sorted({hnc_id, auris_id, node_id}):
        raise ValueError("exact_hnc_auris_node_links_required")

    causal = {
        "schema": SEAT_SCHEMA,
        "receipt_type": "druidic_council_seat",
        "seat": seat_name,
        "agent_id": _nonblank(agent_id, "agent_id"),
        "decision": verdict,
        "reason": _nonblank(reason, "reason"),
        "gamma": _finite_number(gamma, "gamma"),
        "voice_band": band,
        "voice_weight": weight,
        "proposal_digest": _digest(proposal_digest, "proposal_digest"),
        "prompt_digest": _digest(prompt_digest, "prompt_digest"),
        "hnc_receipt_id": hnc_id,
        "auris_receipt_id": auris_id,
        "auris_node_receipt_id": node_id,
        "source_timestamp": source_time,
        "input_receipt_ids": ids,
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        **_false_flags(),
    }
    receipt = dict(causal)
    receipt["receipt_id"] = f"druid:seat:{_sha256(causal)}"
    receipt["derived_at"] = _finite_number(
        time.time() if derived_at is None else derived_at,
        "derived_at",
    )
    return receipt


def _build_trusted_seat_receipt(
    *,
    decision: str,
    reason: str,
    proposal_digest: str,
    prompt_digest: str,
    resolver_id: str,
    issuer_id: str,
    decision_source_id: str,
    auris_node_receipt: Mapping[str, Any],
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    """Mint a seat only after the trusted composition boundary resolves it.

    This is intentionally private. Request-facing code must use the trusted
    Council issuer so identities, Gamma, lineage identifiers, and provider
    timestamps are always derived from the complete node body.
    """

    from aureon.swarm.auris_node_receipts import validate_auris_node_receipt

    node = validate_auris_node_receipt(
        auris_node_receipt,
        now=now,
        max_age_s=max_age_s,
    )
    if node.get("data_status") != "live":
        raise ValueError("live_auris_node_receipt_required")
    seat_name = _nonblank(node.get("seat"), "seat")
    agent_id = _nonblank(node.get("agent_id"), "agent_id")
    verdict = _nonblank(decision, "decision").upper()
    if verdict not in _SEAT_DECISIONS:
        raise ValueError("invalid_seat_decision")
    resolver_name = _nonblank(resolver_id, "resolver_id")
    issuer_name = _nonblank(issuer_id, "issuer_id")
    source_id = _nonblank(decision_source_id, "decision_source_id")
    provider_ids = _receipt_ids(node.get("provider_receipt_ids", []))
    provider_digest = _digest(
        node.get("provider_moment_digest"),
        "provider_moment_digest",
    )
    binding_digest = _sha256(
        _issuer_binding(
            resolver_id=resolver_name,
            issuer_id=issuer_name,
            decision_source_id=source_id,
            seat=seat_name,
            agent_id=agent_id,
        )
    )
    band, weight = voice_for_gamma(node.get("gamma"))
    causal: dict[str, Any] = {
        "schema": TRUSTED_SEAT_SCHEMA,
        "receipt_type": "druidic_council_seat",
        "seat": seat_name,
        "agent_id": agent_id,
        "decision": verdict,
        "reason": _nonblank(reason, "reason"),
        "gamma": _finite_number(node.get("gamma"), "gamma"),
        "voice_band": band,
        "voice_weight": weight,
        "proposal_digest": _digest(proposal_digest, "proposal_digest"),
        "prompt_digest": _digest(prompt_digest, "prompt_digest"),
        "hnc_receipt_id": _nonblank(
            node.get("hnc_receipt_id"),
            "hnc_receipt_id",
        ),
        "auris_receipt_id": _nonblank(
            node.get("auris_receipt_id"),
            "auris_receipt_id",
        ),
        "auris_node_receipt_id": _nonblank(
            node.get("receipt_id"),
            "auris_node_receipt_id",
        ),
        "source_timestamp": _finite_number(
            node.get("source_timestamp"),
            "source_timestamp",
        ),
        "input_receipt_ids": [],
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        **_false_flags(),
        "resolver_id": resolver_name,
        "issuer_id": issuer_name,
        "decision_source_id": source_id,
        "issuer_binding_digest": binding_digest,
        "decision_evidence_id": "",
        "provider_receipt_ids": provider_ids,
        "provider_moment_digest": provider_digest,
        "auris_node_receipt": copy.deepcopy(node),
    }
    decision_evidence_id = (
        f"{_DECISION_EVIDENCE_PREFIX}"
        f"{_sha256(_decision_evidence_causal(causal))}"
    )
    causal["decision_evidence_id"] = decision_evidence_id
    causal["input_receipt_ids"] = sorted(
        {
            node["receipt_id"],
            decision_evidence_id,
            *node["input_receipt_ids"],
        }
    )
    receipt = dict(causal)
    receipt["receipt_id"] = f"druid:seat:{_sha256(_seat_causal(causal))}"
    receipt["derived_at"] = _finite_number(now, "now")
    return receipt


def validate_seat_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate a seat receipt completely and return a sanitized copy."""

    if not isinstance(receipt, Mapping):
        raise ValueError("seat_receipt_required")
    if receipt.get("schema") not in {SEAT_SCHEMA, TRUSTED_SEAT_SCHEMA}:
        raise ValueError("seat_schema_mismatch")
    if receipt.get("receipt_type") != "druidic_council_seat":
        raise ValueError("seat_receipt_type_mismatch")
    seat_name = _nonblank(receipt.get("seat"), "seat").lower()
    if seat_name not in REQUIRED_SEATS:
        raise ValueError("unknown_council_seat")
    decision = _nonblank(receipt.get("decision"), "decision")
    if decision not in _SEAT_DECISIONS:
        raise ValueError("invalid_seat_decision")
    agent_id = _nonblank(receipt.get("agent_id"), "agent_id")
    _nonblank(receipt.get("reason"), "reason")
    gamma = _canonical_float(receipt.get("gamma"), "gamma")
    band, weight = voice_for_gamma(gamma)
    if receipt.get("voice_band") != band or not _canonical_primitive_matches(
        receipt.get("voice_weight"),
        weight,
    ):
        raise ValueError("voice_weight_mismatch")
    _digest(receipt.get("proposal_digest"), "proposal_digest")
    _digest(receipt.get("prompt_digest"), "prompt_digest")
    hnc_id = _nonblank(receipt.get("hnc_receipt_id"), "hnc_receipt_id")
    auris_id = _nonblank(receipt.get("auris_receipt_id"), "auris_receipt_id")
    node_id = _nonblank(
        receipt.get("auris_node_receipt_id"),
        "auris_node_receipt_id",
    )
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith("auris:cosmic_state:"):
        raise ValueError("live_auris_receipt_required")
    if not node_id.startswith("auris:node:"):
        raise ValueError("seat_auris_node_receipt_required")
    ids = _receipt_ids(receipt.get("input_receipt_ids", []))
    if receipt.get("schema") == TRUSTED_SEAT_SCHEMA:
        from aureon.swarm.auris_node_receipts import validate_auris_node_receipt

        raw_node = receipt.get("auris_node_receipt")
        node = validate_auris_node_receipt(
            raw_node,
            now=now,
            max_age_s=max_age_s,
        )
        if node.get("data_status") != "live":
            raise ValueError("live_auris_node_receipt_required")
        provider_ids = _receipt_ids(receipt.get("provider_receipt_ids", []))
        provider_digest = _digest(
            receipt.get("provider_moment_digest"),
            "provider_moment_digest",
        )
        if (
            node.get("seat") != seat_name
            or node.get("agent_id") != agent_id
            or node.get("gamma") != gamma
            or node.get("receipt_id") != node_id
            or node.get("hnc_receipt_id") != hnc_id
            or node.get("auris_receipt_id") != auris_id
            or node.get("source_timestamp") != receipt.get("source_timestamp")
            or node.get("provider_receipt_ids") != provider_ids
            or node.get("provider_moment_digest") != provider_digest
        ):
            raise ValueError("trusted_seat_node_binding_mismatch")
        resolver_id = _nonblank(receipt.get("resolver_id"), "resolver_id")
        issuer_id = _nonblank(receipt.get("issuer_id"), "issuer_id")
        decision_source_id = _nonblank(
            receipt.get("decision_source_id"),
            "decision_source_id",
        )
        expected_binding = _sha256(
            _issuer_binding(
                resolver_id=resolver_id,
                issuer_id=issuer_id,
                decision_source_id=decision_source_id,
                seat=seat_name,
                agent_id=agent_id,
            )
        )
        if receipt.get("issuer_binding_digest") != expected_binding:
            raise ValueError("trusted_seat_issuer_binding_mismatch")
        expected_decision_id = (
            f"{_DECISION_EVIDENCE_PREFIX}"
            f"{_sha256(_decision_evidence_causal(receipt))}"
        )
        if receipt.get("decision_evidence_id") != expected_decision_id:
            raise ValueError("trusted_seat_decision_evidence_mismatch")
        expected_ids = sorted(
            {
                node_id,
                expected_decision_id,
                *node["input_receipt_ids"],
            }
        )
        if ids != expected_ids:
            raise ValueError("exact_trusted_seat_input_lineage_required")
    elif ids != sorted({hnc_id, auris_id, node_id}):
        raise ValueError("exact_hnc_auris_node_links_required")
    if receipt.get("data_status") != "live":
        raise ValueError("live_seat_receipt_required")
    if receipt.get("truth_status") != "real_derived":
        raise ValueError("real_derived_seat_receipt_required")
    if receipt.get("freshness_status") != "fresh":
        raise ValueError("fresh_seat_receipt_required")
    if receipt.get("equation_inputs_complete") is not True:
        raise ValueError("complete_seat_receipt_required")
    if receipt.get("generated_values") is not False:
        raise ValueError("generated_seat_receipt_forbidden")
    _require_false_flags(receipt)
    source_time = _canonical_float(
        receipt.get("source_timestamp"),
        "source_timestamp",
    )
    current = _finite_number(time.time() if now is None else now, "now")
    age_limit = _finite_number(max_age_s, "max_age_s")
    if age_limit <= 0.0 or source_time > current + FUTURE_SKEW_S:
        raise ValueError("seat_source_timestamp_invalid")
    if current - source_time > age_limit:
        raise ValueError("stale_seat_receipt")
    if "derived_at" in receipt:
        _canonical_float(receipt["derived_at"], "derived_at")
    causal = _seat_causal(receipt)
    required_keys = set(causal) | {"receipt_id"}
    allowed_keys = required_keys | {"derived_at"}
    if not required_keys.issubset(receipt) or not set(receipt).issubset(allowed_keys):
        raise ValueError("exact_seat_receipt_schema_required")
    if receipt.get("receipt_id") != f"druid:seat:{_sha256(causal)}":
        raise ValueError("seat_receipt_hash_mismatch")
    return dict(receipt)


def _no_data(reason: str) -> dict[str, Any]:
    return {
        "schema": COUNCIL_SCHEMA,
        "receipt_type": "druidic_council",
        "receipt_id": None,
        "decision": "HOLD",
        "reason": reason,
        "data_status": "no_data",
        "truth_status": "no_data",
        "freshness_status": "no_data",
        "equation_inputs_complete": False,
        "generated_values": False,
        "input_receipt_ids": [],
        "route_authorization_required": True,
        **_false_flags(),
    }


def _ring_distance(first: int, second: int) -> int:
    separation = abs(first - second)
    return min(separation, len(REQUIRED_SEATS) - separation)


def _phi_coupling(first: int, second: int) -> float:
    """Golden-ratio coupling on the four-seat peer ring.

    A seat couples to itself at 1, to either neighbour at phi^-1, and to the
    opposite seat at phi^-2. Because the geometry is a ring, no named seat is
    intrinsically ranked above another.
    """

    return PHI ** (-_ring_distance(first, second))


def _cap_normalized_influences(scores: Sequence[float]) -> tuple[list[float], bool]:
    """Normalize scores while capping every viable peer at phi^-1.

    The cap is feasible once two voices are present. A lone voice remains
    visible with influence 1 but explicitly fails the returned dominance
    condition and can never satisfy Council quorum.
    """

    positive = [index for index, score in enumerate(scores) if score > 0.0]
    influences = [0.0] * len(scores)
    if not positive:
        return influences, True
    if len(positive) == 1:
        influences[positive[0]] = 1.0
        return influences, False

    remaining = set(positive)
    remaining_mass = 1.0
    while remaining:
        score_total = math.fsum(scores[index] for index in remaining)
        proposed = {
            index: remaining_mass * scores[index] / score_total
            for index in remaining
        }
        over_cap = {
            index
            for index, influence in proposed.items()
            if influence > PHI_INVERSE
        }
        if not over_cap:
            for index, influence in proposed.items():
                influences[index] = influence
            break
        for index in over_cap:
            influences[index] = PHI_INVERSE
            remaining_mass -= PHI_INVERSE
        remaining.difference_update(over_cap)

    cap_passed = max(influences, default=0.0) <= PHI_INVERSE + 1e-12
    return influences, cap_passed


def _phi_voice_profiles(
    summaries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    driving_indices = [
        index
        for index, item in enumerate(summaries)
        if item["voice_weight"] > 0.0
    ]
    profiles: list[dict[str, Any]] = []
    scores: list[float] = []
    for index, item in enumerate(summaries):
        topology_factor = (
            math.fsum(_phi_coupling(index, peer) for peer in driving_indices)
            / len(driving_indices)
            if driving_indices
            else 0.0
        )
        band_multiplier = PHI if item["voice_band"] == "LIGHTHOUSE" else 1.0
        if item["voice_band"] == "ADVISORY":
            band_multiplier = 0.0
        score = item["voice_weight"] * band_multiplier * topology_factor
        scores.append(score)
        profiles.append(
            {
                "ring_position": index,
                "phi_topology_factor": topology_factor,
                "phi_band_multiplier": band_multiplier,
                "phi_resonance_score": score,
            }
        )
    influences, _ = _cap_normalized_influences(scores)
    for profile, influence in zip(profiles, influences, strict=True):
        profile["normalized_voice_influence"] = influence
    return profiles


def _council_metrics(summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    drivers = [item for item in summaries if item["voice_weight"] > 0.0]
    total_weight = math.fsum(item["voice_weight"] for item in drivers)
    accept_weight = math.fsum(
        item["voice_weight"] for item in drivers if item["decision"] == "ACCEPT"
    )
    support = accept_weight / total_weight if total_weight else 0.0
    weighted_gamma = (
        math.fsum(item["voice_weight"] * item["gamma"] for item in drivers)
        / total_weight
        if total_weight
        else 0.0
    )
    dispersion = (
        math.sqrt(
            math.fsum(
                item["voice_weight"] * (item["gamma"] - weighted_gamma) ** 2
                for item in drivers
            )
            / total_weight
        )
        if total_weight
        else 0.0
    )
    profiles = _phi_voice_profiles(summaries)
    resonance_scores = [item["phi_resonance_score"] for item in profiles]
    influences, dominance_cap_passed = _cap_normalized_influences(resonance_scores)
    phi_accept_support = math.fsum(
        influence
        for item, influence in zip(summaries, influences, strict=True)
        if item["decision"] == "ACCEPT"
    )
    phi_weighted_gamma = math.fsum(
        influence * item["gamma"]
        for item, influence in zip(summaries, influences, strict=True)
    )
    phi_dispersion = math.sqrt(
        math.fsum(
            influence * (item["gamma"] - phi_weighted_gamma) ** 2
            for item, influence in zip(summaries, influences, strict=True)
        )
    )
    influence_square_sum = math.fsum(value * value for value in influences)
    effective_participation = (
        1.0 / influence_square_sum if influence_square_sum else 0.0
    )
    phi_stability_ratio = effective_participation / PHI_SQUARED
    phi_stability_passed = effective_participation >= PHI_SQUARED
    driving_names = {item["seat"] for item in drivers}
    structural_quorum = (
        len(drivers) >= MIN_DRIVING_SEATS
        and {"sentinel", "keeper"}.issubset(driving_names)
    )
    quorum = structural_quorum and phi_stability_passed and dominance_cap_passed
    if any(item["decision"] == "ABORT" for item in drivers):
        decision, reason = "ABORT", "seat_abort_dominates"
    elif quorum and phi_accept_support >= ACCEPT_SUPPORT_THRESHOLD:
        decision, reason = "ACCEPT", "phi_weighted_quorum_accept"
    elif structural_quorum and not phi_stability_passed:
        decision, reason = "HOLD", "phi_squared_stability_not_satisfied"
    else:
        decision, reason = "HOLD", "phi_weighted_quorum_not_satisfied"
    return {
        "decision": decision,
        "reason": reason,
        "driving_seat_count": len(drivers),
        "total_voice_weight": total_weight,
        "accept_voice_weight": accept_weight,
        "accept_support": support,
        "weighted_gamma": weighted_gamma,
        "gamma_dispersion": dispersion,
        "phi": PHI,
        "phi_inverse": PHI_INVERSE,
        "phi_squared": PHI_SQUARED,
        "phi_topology": PHI_TOPOLOGY,
        "phi_dominance_cap": PHI_INVERSE,
        "total_resonance_score": math.fsum(resonance_scores),
        "phi_accept_support": phi_accept_support,
        "phi_weighted_gamma": phi_weighted_gamma,
        "phi_gamma_dispersion": phi_dispersion,
        "max_normalized_voice_influence": max(influences, default=0.0),
        "effective_participation": effective_participation,
        "phi_stability_ratio": phi_stability_ratio,
        "phi_stability_passed": phi_stability_passed,
        "dominance_cap_passed": dominance_cap_passed,
        "structural_quorum_passed": structural_quorum,
        "quorum_passed": quorum,
    }


def _council_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
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
        "seat_summaries": payload["seat_summaries"],
        "seat_receipts": payload["seat_receipts"],
        "driving_seat_count": payload["driving_seat_count"],
        "total_voice_weight": payload["total_voice_weight"],
        "accept_voice_weight": payload["accept_voice_weight"],
        "accept_support": payload["accept_support"],
        "weighted_gamma": payload["weighted_gamma"],
        "gamma_dispersion": payload["gamma_dispersion"],
        "phi": payload["phi"],
        "phi_inverse": payload["phi_inverse"],
        "phi_squared": payload["phi_squared"],
        "phi_topology": payload["phi_topology"],
        "phi_dominance_cap": payload["phi_dominance_cap"],
        "total_resonance_score": payload["total_resonance_score"],
        "phi_accept_support": payload["phi_accept_support"],
        "phi_weighted_gamma": payload["phi_weighted_gamma"],
        "phi_gamma_dispersion": payload["phi_gamma_dispersion"],
        "max_normalized_voice_influence": payload[
            "max_normalized_voice_influence"
        ],
        "effective_participation": payload["effective_participation"],
        "phi_stability_ratio": payload["phi_stability_ratio"],
        "phi_stability_passed": payload["phi_stability_passed"],
        "dominance_cap_passed": payload["dominance_cap_passed"],
        "structural_quorum_passed": payload["structural_quorum_passed"],
        "quorum_passed": payload["quorum_passed"],
        "data_status": payload["data_status"],
        "truth_status": payload["truth_status"],
        "freshness_status": payload["freshness_status"],
        "equation_inputs_complete": payload["equation_inputs_complete"],
        "generated_values": payload["generated_values"],
        "route_authorization_required": payload["route_authorization_required"],
        **_false_flags(),
    }


def convene_druidic_council(
    *,
    proposal_digest: str,
    prompt_digest: str,
    hnc_receipt_id: str,
    auris_receipt_id: str,
    seat_receipts: Sequence[Mapping[str, Any]],
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate all stable seats and derive the Council decision."""

    current = time.time() if now is None else now
    try:
        expected_proposal = _digest(proposal_digest, "proposal_digest")
        expected_prompt = _digest(prompt_digest, "prompt_digest")
        expected_hnc = _nonblank(hnc_receipt_id, "hnc_receipt_id")
        expected_auris = _nonblank(auris_receipt_id, "auris_receipt_id")
        validated = [
            validate_seat_receipt(item, now=current, max_age_s=max_age_s)
            for item in seat_receipts
        ]
        if len(validated) != len(REQUIRED_SEATS):
            raise ValueError("all_stable_seats_required")
        by_seat = {item["seat"]: item for item in validated}
        if tuple(sorted(by_seat)) != tuple(sorted(REQUIRED_SEATS)):
            raise ValueError("all_stable_seats_required")
        if len({item["agent_id"] for item in validated}) != len(REQUIRED_SEATS):
            raise ValueError("distinct_agent_per_stable_seat_required")
        if len({item["auris_node_receipt_id"] for item in validated}) != len(
            REQUIRED_SEATS
        ):
            raise ValueError("distinct_auris_node_per_stable_seat_required")
        if len({item["source_timestamp"] for item in validated}) != 1:
            raise ValueError("exact_seat_provider_moment_required")
        trusted_count = sum(
            item["schema"] == TRUSTED_SEAT_SCHEMA for item in validated
        )
        if trusted_count not in {0, len(REQUIRED_SEATS)}:
            raise ValueError("mixed_trusted_and_legacy_seats_forbidden")
        if trusted_count:
            node_moments = {
                (
                    tuple(item["provider_receipt_ids"]),
                    item["provider_moment_digest"],
                    item["hnc_receipt_id"],
                    item["auris_receipt_id"],
                    item["source_timestamp"],
                )
                for item in validated
            }
            if len(node_moments) != 1:
                raise ValueError("exact_trusted_node_provider_moment_required")
            if len({item["resolver_id"] for item in validated}) != 1:
                raise ValueError("single_trusted_council_resolver_required")
            issuer_count = len({item["issuer_id"] for item in validated})
            if issuer_count not in {1, len(REQUIRED_SEATS)}:
                raise ValueError("invalid_trusted_council_issuer_topology")
            if len({item["decision_source_id"] for item in validated}) != len(
                REQUIRED_SEATS
            ):
                raise ValueError("distinct_trusted_decision_sources_required")
        for item in validated:
            if (
                item["proposal_digest"] != expected_proposal
                or item["prompt_digest"] != expected_prompt
                or item["hnc_receipt_id"] != expected_hnc
                or item["auris_receipt_id"] != expected_auris
            ):
                raise ValueError("council_lineage_mismatch")
    except (KeyError, TypeError, ValueError):
        return _no_data("complete_fresh_linked_druidic_seat_receipts_required")

    summaries = []
    linked_seat_receipts = []
    for seat_name in REQUIRED_SEATS:
        item = by_seat[seat_name]
        linked = _seat_causal(item)
        linked["receipt_id"] = item["receipt_id"]
        linked_seat_receipts.append(linked)
        summaries.append(
            {
                "seat": seat_name,
                "agent_id": item["agent_id"],
                "decision": item["decision"],
                "gamma": item["gamma"],
                "voice_band": item["voice_band"],
                "voice_weight": item["voice_weight"],
                "auris_node_receipt_id": item["auris_node_receipt_id"],
                "receipt_id": item["receipt_id"],
            }
        )
    profiles = _phi_voice_profiles(summaries)
    for summary, profile in zip(summaries, profiles, strict=True):
        summary.update(profile)
    metrics = _council_metrics(summaries)
    source_time = validated[0]["source_timestamp"]
    if validated[0]["schema"] == TRUSTED_SEAT_SCHEMA:
        input_ids = sorted(
            {
                *(link for item in validated for link in item["input_receipt_ids"]),
                *(item["receipt_id"] for item in validated),
            }
        )
    else:
        input_ids = sorted(
            {
                expected_hnc,
                expected_auris,
                *(item["auris_node_receipt_id"] for item in validated),
                *(item["receipt_id"] for item in validated),
            }
        )
    causal = {
        "schema": COUNCIL_SCHEMA,
        "receipt_type": "druidic_council",
        **metrics,
        "proposal_digest": expected_proposal,
        "prompt_digest": expected_prompt,
        "hnc_receipt_id": expected_hnc,
        "auris_receipt_id": expected_auris,
        "source_timestamp": source_time,
        "input_receipt_ids": input_ids,
        "seat_summaries": summaries,
        "seat_receipts": linked_seat_receipts,
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        "route_authorization_required": True,
        **_false_flags(),
    }
    receipt = dict(causal)
    receipt["receipt_id"] = f"druid:council:{_sha256(causal)}"
    receipt["derived_at"] = _finite_number(current, "now")
    return receipt


def validate_council_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate a Council receipt before it enters a dual-key join."""

    if not isinstance(receipt, Mapping) or receipt.get("schema") != COUNCIL_SCHEMA:
        raise ValueError("council_receipt_required")
    if receipt.get("receipt_type") != "druidic_council":
        raise ValueError("council_receipt_type_mismatch")
    if receipt.get("data_status") != "live" or receipt.get("truth_status") != "real_derived":
        raise ValueError("live_real_council_receipt_required")
    if receipt.get("freshness_status") != "fresh":
        raise ValueError("fresh_council_receipt_required")
    if receipt.get("equation_inputs_complete") is not True:
        raise ValueError("complete_council_receipt_required")
    if receipt.get("generated_values") is not False:
        raise ValueError("generated_council_receipt_forbidden")
    if receipt.get("route_authorization_required") is not True:
        raise ValueError("route_authorization_boundary_required")
    _require_false_flags(receipt)
    _digest(receipt.get("proposal_digest"), "proposal_digest")
    _digest(receipt.get("prompt_digest"), "prompt_digest")
    hnc_id = _nonblank(receipt.get("hnc_receipt_id"), "hnc_receipt_id")
    auris_id = _nonblank(receipt.get("auris_receipt_id"), "auris_receipt_id")
    if not hnc_id.startswith("hnc:live_field:"):
        raise ValueError("live_hnc_receipt_required")
    if not auris_id.startswith("auris:cosmic_state:"):
        raise ValueError("live_auris_receipt_required")
    ids = _receipt_ids(receipt.get("input_receipt_ids", []))
    summaries = receipt.get("seat_summaries")
    if not isinstance(summaries, list) or len(summaries) != len(REQUIRED_SEATS):
        raise ValueError("all_stable_seats_required")
    if not all(isinstance(item, Mapping) for item in summaries):
        raise ValueError("valid_seat_summaries_required")
    if [item.get("seat") for item in summaries] != list(REQUIRED_SEATS):
        raise ValueError("stable_seat_order_required")
    for item in summaries:
        gamma = _canonical_float(item.get("gamma"), "gamma")
        band, weight = voice_for_gamma(gamma)
        claimed_weight = item.get("voice_weight")
        if item.get("voice_band") != band or not _canonical_primitive_matches(
            claimed_weight,
            weight,
        ):
            raise ValueError("voice_weight_mismatch")
        if item.get("decision") not in _SEAT_DECISIONS:
            raise ValueError("invalid_seat_decision")
        _nonblank(item.get("agent_id"), "agent_id")
        seat_receipt_id = _nonblank(item.get("receipt_id"), "seat_receipt_id")
        node_receipt_id = _nonblank(
            item.get("auris_node_receipt_id"),
            "auris_node_receipt_id",
        )
        if not node_receipt_id.startswith("auris:node:"):
            raise ValueError("seat_auris_node_receipt_required")
        if seat_receipt_id not in ids:
            raise ValueError("seat_receipt_link_required")
    expected_profiles = _phi_voice_profiles(summaries)
    for item, profile in zip(summaries, expected_profiles, strict=True):
        for name, expected in profile.items():
            claimed = item.get(name)
            if name == "ring_position":
                if isinstance(claimed, bool) or claimed != expected:
                    raise ValueError("phi_seat_profile_mismatch")
            elif not _canonical_primitive_matches(claimed, expected):
                raise ValueError("phi_seat_profile_mismatch")
    if len({item["agent_id"] for item in summaries}) != len(REQUIRED_SEATS):
        raise ValueError("distinct_agent_per_stable_seat_required")
    expected_metrics = _council_metrics(summaries)
    if any(
        not _canonical_primitive_matches(receipt.get(key), value)
        for key, value in expected_metrics.items()
    ):
        raise ValueError("council_policy_mismatch")
    source_time = _canonical_float(
        receipt.get("source_timestamp"),
        "source_timestamp",
    )
    current = _finite_number(time.time() if now is None else now, "now")
    age_limit = _finite_number(max_age_s, "max_age_s")
    if age_limit <= 0.0:
        raise ValueError("positive_max_age_required")
    linked_receipts = receipt.get("seat_receipts")
    if not isinstance(linked_receipts, list) or len(linked_receipts) != len(
        REQUIRED_SEATS
    ):
        raise ValueError("complete_linked_seat_receipts_required")
    validated_seats = [
        validate_seat_receipt(item, now=current, max_age_s=age_limit)
        for item in linked_receipts
    ]
    if [item["seat"] for item in validated_seats] != list(REQUIRED_SEATS):
        raise ValueError("stable_seat_order_required")
    if len({item["source_timestamp"] for item in validated_seats}) != 1:
        raise ValueError("exact_seat_provider_moment_required")
    if len({item["agent_id"] for item in validated_seats}) != len(REQUIRED_SEATS):
        raise ValueError("distinct_agent_per_stable_seat_required")
    if len({item["auris_node_receipt_id"] for item in validated_seats}) != len(
        REQUIRED_SEATS
    ):
        raise ValueError("distinct_auris_node_per_stable_seat_required")
    trusted_count = sum(
        item["schema"] == TRUSTED_SEAT_SCHEMA for item in validated_seats
    )
    if trusted_count not in {0, len(REQUIRED_SEATS)}:
        raise ValueError("mixed_trusted_and_legacy_seats_forbidden")
    if trusted_count:
        node_moments = {
            (
                tuple(item["provider_receipt_ids"]),
                item["provider_moment_digest"],
                item["hnc_receipt_id"],
                item["auris_receipt_id"],
                item["source_timestamp"],
            )
            for item in validated_seats
        }
        if len(node_moments) != 1:
            raise ValueError("exact_trusted_node_provider_moment_required")
        if len({item["resolver_id"] for item in validated_seats}) != 1:
            raise ValueError("single_trusted_council_resolver_required")
        issuer_count = len({item["issuer_id"] for item in validated_seats})
        if issuer_count not in {1, len(REQUIRED_SEATS)}:
            raise ValueError("invalid_trusted_council_issuer_topology")
        if len(
            {item["decision_source_id"] for item in validated_seats}
        ) != len(REQUIRED_SEATS):
            raise ValueError("distinct_trusted_decision_sources_required")
        expected_ids = sorted(
            {
                *(
                    link
                    for item in validated_seats
                    for link in item["input_receipt_ids"]
                ),
                *(item["receipt_id"] for item in validated_seats),
            }
        )
    else:
        expected_ids = sorted(
            {
                hnc_id,
                auris_id,
                *(item["auris_node_receipt_id"] for item in summaries),
                *(item["receipt_id"] for item in summaries),
            }
        )
    if ids != expected_ids:
        raise ValueError("exact_council_input_lineage_required")
    if validated_seats[0]["source_timestamp"] != source_time:
        raise ValueError("council_provider_moment_mismatch")
    binding_fields = (
        "proposal_digest",
        "prompt_digest",
        "hnc_receipt_id",
        "auris_receipt_id",
    )
    for summary, seat, profile in zip(
        summaries,
        validated_seats,
        expected_profiles,
        strict=True,
    ):
        expected_summary = {
            "seat": seat["seat"],
            "agent_id": seat["agent_id"],
            "decision": seat["decision"],
            "gamma": seat["gamma"],
            "voice_band": seat["voice_band"],
            "voice_weight": seat["voice_weight"],
            "auris_node_receipt_id": seat["auris_node_receipt_id"],
            "receipt_id": seat["receipt_id"],
            **profile,
        }
        if dict(summary) != expected_summary:
            raise ValueError("seat_summary_receipt_mismatch")
        if any(seat[field] != receipt[field] for field in binding_fields):
            raise ValueError("council_lineage_mismatch")
    if source_time > current + FUTURE_SKEW_S or current - source_time > age_limit:
        raise ValueError("stale_council_receipt")
    if "derived_at" in receipt:
        _canonical_float(receipt["derived_at"], "derived_at")
    causal = _council_causal(receipt)
    required_keys = set(causal) | {"receipt_id"}
    allowed_keys = required_keys | {"derived_at"}
    if not required_keys.issubset(receipt) or not set(receipt).issubset(allowed_keys):
        raise ValueError("exact_council_receipt_schema_required")
    if receipt.get("receipt_id") != f"druid:council:{_sha256(causal)}":
        raise ValueError("council_receipt_hash_mismatch")
    return dict(receipt)


__all__ = [
    "ACCEPT_SUPPORT_THRESHOLD",
    "ACTIVE_THRESHOLD",
    "COUNCIL_SCHEMA",
    "CouncilReceipt",
    "CouncilSeat",
    "LIGHTHOUSE_THRESHOLD",
    "PHI",
    "PHI_INVERSE",
    "PHI_SQUARED",
    "PHI_TOPOLOGY",
    "REQUIRED_SEATS",
    "SEAT_SCHEMA",
    "TRUSTED_SEAT_SCHEMA",
    "SeatReceipt",
    "build_seat_receipt",
    "convene_druidic_council",
    "validate_council_receipt",
    "validate_seat_receipt",
    "voice_for_gamma",
]
