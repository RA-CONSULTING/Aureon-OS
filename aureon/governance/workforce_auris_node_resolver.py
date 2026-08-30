"""Receipt-backed Auris-node resolver for the truth-gated cloud workforce.

Each seat is measured from a chronological window of full 10-9-1 receipts.
The independent variable is the canonical HNC Gamma observed for that work
unit.  The dependent variable is recomputed from the exact answer text by the
repository's deterministic harmonic-text alignment.  Every answer must have
already passed the receipt-backed QGITA/Kundalini gate and Hive/Mycelia
propagation.

The resulting Pearson Gamma is evidence only.  It cannot authorize a route,
and the final sample for every seat must share the exact current HNC/Auris
provider moment used by the Council.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    validate_truth_gated_ten_nine_one_receipt,
)
from aureon.harmonic.harmonic_text_alignment import score_text
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    TRUTH_GATED_COHERENCE_METHOD,
    TRUTH_GATED_COHERENCE_SCHEMA,
    ResolvedAurisNodeEvidence,
    TrustedAurisNodeResolver,
    validate_coherence_measurement,
    validate_provider_moment,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

_MEASUREMENT_PREFIX = "auris:coherence_measurement:"
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
_RESOLVER_TOKEN = object()


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _sha(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    return value.strip()


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}_must_be_finite")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}_must_be_finite")
    return result


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def build_truth_gated_coherence_measurement(
    *,
    seat: str,
    agent_id: str,
    source_id: str,
    hnc_evidence: Mapping[str, Any],
    auris_evidence: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Build and self-validate one v2 full-window coherence measurement."""

    current = _finite(time.time() if now is None else now, "now")
    age = _finite(max_age_s, "max_age_s")
    if age <= 0.0:
        raise ValueError("positive_max_age_required")
    seat_name = _nonblank(seat, "seat").lower()
    if seat_name not in REQUIRED_SEATS:
        raise ValueError("unknown_council_seat")
    agent = _nonblank(agent_id, "agent_id")
    source = _nonblank(source_id, "source_id")
    if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
        raise ValueError("truth_gated_sample_sequence_required")
    if not 3 <= len(samples) <= 12:
        raise ValueError("truth_gated_sample_window_must_be_between_3_and_12")
    moment = validate_provider_moment(
        hnc_evidence,
        auris_evidence,
        now=current,
        max_age_s=age,
    )
    canonical_samples: list[dict[str, Any]] = []
    levels: list[float] = []
    magnitudes: list[float] = []
    sample_ids: list[str] = []
    answer_digests: list[str] = []
    for raw in samples:
        if not isinstance(raw, Mapping) or set(raw) != {
            "answer_text",
            "thought_path_receipt",
        }:
            raise ValueError("exact_truth_gated_sample_required")
        answer = _nonblank(raw.get("answer_text"), "answer_text")
        thought = validate_truth_gated_ten_nine_one_receipt(
            raw.get("thought_path_receipt", {}),
            now=current,
            max_age_s=age,
        )
        inner = thought["inner_receipt"]
        if (
            inner.get("subject_type") != "agent"
            or inner.get("subject_id") != agent
            or inner.get("stage") != "auris_coherence_probe"
            or inner.get("work_kind") != "auris_coherence_measurement"
            or _sha(answer) != inner.get("answer_digest")
        ):
            raise ValueError("truth_gated_sample_agent_binding_mismatch")
        levels.append(_finite(inner["hnc_receipt"].get("hnc_gamma"), "hnc_gamma"))
        magnitude = _finite(score_text(answer).coherence, "answer_text_coherence")
        if not 0.0 <= magnitude <= 1.0:
            raise ValueError("answer_text_coherence_out_of_range")
        magnitudes.append(magnitude)
        sample_ids.append(_nonblank(thought.get("receipt_id"), "sample_receipt_id"))
        answer_digests.append(_nonblank(inner.get("answer_digest"), "answer_digest"))
        canonical_samples.append(
            {"answer_text": answer, "thought_path_receipt": _copy(thought)}
        )
    window_material = {
        "operator_levels": levels,
        "action_magnitudes": magnitudes,
        "window_size": len(canonical_samples),
        "sample_receipt_ids": sample_ids,
        "answer_digests": answer_digests,
    }
    causal = {
        "schema": TRUTH_GATED_COHERENCE_SCHEMA,
        "receipt_type": "agent_coherence_measurement",
        "source_id": source,
        "seat": seat_name,
        "agent_id": agent,
        "measurement_method": TRUTH_GATED_COHERENCE_METHOD,
        "operator_levels": levels,
        "action_magnitudes": magnitudes,
        "window_size": len(canonical_samples),
        "sample_count": len(canonical_samples),
        "window_digest": _sha(window_material),
        "sample_receipt_ids": sample_ids,
        "answer_digests": answer_digests,
        "samples": canonical_samples,
        "hnc_receipt_id": moment.hnc_receipt_id,
        "auris_receipt_id": moment.auris_receipt_id,
        "provider_receipt_ids": list(moment.provider_receipt_ids),
        "provider_moment_digest": moment.provider_moment_digest,
        "source_timestamp": moment.source_timestamp,
        "input_receipt_ids": sorted(
            {
                moment.hnc_receipt_id,
                moment.auris_receipt_id,
                *moment.provider_receipt_ids,
                *sample_ids,
            }
        ),
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        **_false_flags(),
    }
    receipt = {
        **causal,
        "receipt_id": f"{_MEASUREMENT_PREFIX}{_sha(causal)}",
        "received_at": current,
    }
    validated, _ = validate_coherence_measurement(
        receipt,
        seat=seat_name,
        agent_id=agent,
        source_id=source,
        moment=moment,
        now=current,
        max_age_s=age,
    )
    return validated


class TruthGatedWorkforceAurisNodeResolver:
    """Immutable four-seat resolver constructed by a trusted composition root."""

    def __init__(
        self,
        *,
        _token: object,
        resolver_id: str,
        resolved: Mapping[str, ResolvedAurisNodeEvidence],
    ) -> None:
        if _token is not _RESOLVER_TOKEN:
            raise TypeError("use_bind_truth_gated_workforce_auris_resolver")
        self.resolver_id = _nonblank(resolver_id, "resolver_id")
        self._resolved = dict(resolved)

    def resolve_auris_node_evidence(
        self,
        seat: str,
    ) -> ResolvedAurisNodeEvidence | None:
        item = self._resolved.get(str(seat).strip().lower())
        if item is None:
            return None
        return ResolvedAurisNodeEvidence(
            resolver_id=item.resolver_id,
            coherence_source_id=item.coherence_source_id,
            seat=item.seat,
            agent_id=item.agent_id,
            hnc_evidence=_copy(item.hnc_evidence),
            auris_evidence=_copy(item.auris_evidence),
            coherence_evidence=_copy(item.coherence_evidence),
        )


def bind_truth_gated_workforce_auris_resolver(
    *,
    resolver_id: str,
    trusted_resolver_ids: Collection[str],
    hnc_evidence: Mapping[str, Any],
    auris_evidence: Mapping[str, Any],
    seat_agents: Mapping[str, str],
    seat_samples: Mapping[str, Sequence[Mapping[str, Any]]],
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> TruthGatedWorkforceAurisNodeResolver:
    """Bind four distinct agents and their full sample windows to one moment."""

    resolver_name = _nonblank(resolver_id, "resolver_id")
    trusted = {
        _nonblank(item, "trusted_resolver_id").casefold()
        for item in trusted_resolver_ids
    }
    if resolver_name.casefold() not in trusted:
        raise ValueError("allowlisted_auris_node_resolver_required")
    normalized_agents = {
        _nonblank(seat, "seat").lower(): _nonblank(agent, "agent_id")
        for seat, agent in seat_agents.items()
    }
    normalized_samples = {
        _nonblank(seat, "seat").lower(): samples
        for seat, samples in seat_samples.items()
    }
    if (
        set(normalized_agents) != set(REQUIRED_SEATS)
        or set(normalized_samples) != set(REQUIRED_SEATS)
        or len(set(normalized_agents.values())) != len(REQUIRED_SEATS)
    ):
        raise ValueError("exact_distinct_four_seat_samples_required")
    resolved: dict[str, ResolvedAurisNodeEvidence] = {}
    for seat in REQUIRED_SEATS:
        agent = normalized_agents[seat]
        source_id = f"aureon:10-9-1:coherence:{seat}"
        measurement = build_truth_gated_coherence_measurement(
            seat=seat,
            agent_id=agent,
            source_id=source_id,
            hnc_evidence=hnc_evidence,
            auris_evidence=auris_evidence,
            samples=normalized_samples[seat],
            now=now,
            max_age_s=max_age_s,
        )
        resolved[seat] = ResolvedAurisNodeEvidence(
            resolver_id=resolver_name,
            coherence_source_id=source_id,
            seat=seat,
            agent_id=agent,
            hnc_evidence=_copy(hnc_evidence),
            auris_evidence=_copy(auris_evidence),
            coherence_evidence=measurement,
        )
    resolver = TruthGatedWorkforceAurisNodeResolver(
        _token=_RESOLVER_TOKEN,
        resolver_id=resolver_name,
        resolved=resolved,
    )
    if not isinstance(resolver, TrustedAurisNodeResolver):
        raise AssertionError("trusted_auris_node_resolver_contract_broken")
    return resolver


__all__ = [
    "TruthGatedWorkforceAurisNodeResolver",
    "bind_truth_gated_workforce_auris_resolver",
    "build_truth_gated_coherence_measurement",
]
