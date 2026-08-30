"""Trusted, receipt-bound Auris nodes for Druidic Council seats.

The public issuance API deliberately accepts a resolver, not caller-supplied
agent identities, receipt identifiers, timestamps, or coherence values.  A
resolver is the production trust boundary: it must return the exact raw HNC
and Auris cycle plus a full measured agent-coherence window.  This module then
recomputes every causal identifier and Gamma before it can label a node live.

These receipts are evidence only.  They never grant route or economic
authority, and every eligibility flag is explicitly false.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aureon.swarm.druidic_council import REQUIRED_SEATS

NODE_SCHEMA = "aureon.auris_node.v1"
COHERENCE_SCHEMA = "aureon.agent_coherence.measurement.v1"
COHERENCE_METHOD = "rolling_pearson_operator_action.v1"
TRUTH_GATED_COHERENCE_SCHEMA = "aureon.agent_coherence.measurement.v2"
TRUTH_GATED_COHERENCE_METHOD = "ten_nine_one_hnc_text_correlation.v1"
DEFAULT_MAX_AGE_S = 300.0
FUTURE_SKEW_S = 5.0

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_HNC_PREFIX = "hnc:live_field:"
_AURIS_PREFIX = "auris:cosmic_state:"
_COHERENCE_PREFIX = "auris:coherence_measurement:"
_NODE_PREFIX = "auris:node:"

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
_INPUT_FALSE_FLAGS = tuple(name for name in _FALSE_FLAGS if name != "economic_mutation")

_AURIS_SOURCE_NAMES = frozenset({"hnc", "space_weather", "earth_blessing", "schumann", "earth_gate"})
_AURIS_PROVIDER_NAMES = ("space_weather", "schumann")

_SOURCE_RECEIPT_KEYS = frozenset(
    {
        "source_id",
        "source_timestamp",
        "received_at",
        "receipt_id",
        "receipt_type",
        "truth_status",
        "generated_values",
        "input_receipt_ids",
        "operational_eligible",
        "provider_eligible",
        "action_eligible",
        "actionable",
        "accounting_eligible",
        "learning_eligible",
        "eligible_for_action",
        "eligible_for_accounting",
        "eligible_for_learning",
        "action_gate_passed",
    }
)

_COHERENCE_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "source_id",
        "seat",
        "agent_id",
        "measurement_method",
        "operator_levels",
        "action_magnitudes",
        "window_size",
        "sample_count",
        "window_digest",
        "hnc_receipt_id",
        "auris_receipt_id",
        "provider_receipt_ids",
        "provider_moment_digest",
        "source_timestamp",
        "received_at",
        "input_receipt_ids",
        "data_status",
        "truth_status",
        "freshness_status",
        "equation_inputs_complete",
        "generated_values",
        *_FALSE_FLAGS,
    }
)

_TRUTH_GATED_COHERENCE_KEYS = frozenset(
    {
        *_COHERENCE_KEYS,
        "sample_receipt_ids",
        "answer_digests",
        "samples",
    }
)

_NODE_LIVE_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "seat",
        "agent_id",
        "resolver_id",
        "coherence_source_id",
        "seat_binding_digest",
        "gamma",
        "measurement_method",
        "coherence_measurement_receipt_id",
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

_NODE_NO_DATA_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "seat",
        "agent_id",
        "resolver_id",
        "reason",
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
class ResolvedAurisNodeEvidence:
    """One resolver-authenticated seat snapshot.

    ``resolver_id`` and ``coherence_source_id`` identify configured trust
    anchors; they are not accepted as parameters by the node issuer.
    """

    resolver_id: str
    coherence_source_id: str
    seat: str
    agent_id: str
    hnc_evidence: Mapping[str, Any]
    auris_evidence: Mapping[str, Any]
    coherence_evidence: Mapping[str, Any]


@runtime_checkable
class TrustedAurisNodeResolver(Protocol):
    """Production boundary for authenticated seat and evidence resolution.

    Structural protocol conformance is not itself authentication.  The
    composition root must construct an allowlisted implementation backed by
    an authenticated local bus/store; a resolver must never come from request
    data or an untrusted plugin.
    """

    def resolve_auris_node_evidence(
        self,
        seat: str,
    ) -> ResolvedAurisNodeEvidence | None:
        """Resolve one stable seat from authenticated local/runtime stores."""


@dataclass(frozen=True)
class ProviderMoment:
    """Validated immutable upstream snapshot shared by every Council seat."""

    hnc_receipt_id: str
    auris_receipt_id: str
    source_timestamp: float
    provider_receipt_ids: tuple[str, ...]
    provider_moment_digest: str


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


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name}_invalid")
    return value


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


def _require_false_flags(
    payload: Mapping[str, Any],
    names: Sequence[str] = _FALSE_FLAGS,
) -> None:
    if any(payload.get(name) is not False for name in names):
        raise ValueError("complete_false_eligibility_flags_required")
    for name, value in payload.items():
        lowered = name.lower()
        if (
            "eligible" in lowered
            or lowered == "actionable"
            or lowered.endswith("_gate_passed")
            or lowered == "economic_mutation"
        ) and value is not False:
            raise ValueError("evidence_must_remain_ineligible")


def _fresh_timestamp(
    source_timestamp: Any,
    received_at: Any,
    *,
    now: float,
    max_age_s: float,
) -> tuple[float, float]:
    source_time = _finite(source_timestamp, "source_timestamp")
    received_time = _finite(received_at, "received_at")
    if (
        source_time > now + FUTURE_SKEW_S
        or received_time > now + FUTURE_SKEW_S
        or received_time < source_time - FUTURE_SKEW_S
        or now - source_time > max_age_s
    ):
        raise ValueError("fresh_evidence_timestamp_required")
    return source_time, received_time


def _hnc_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "input_receipt_ids": payload["input_receipt_ids"],
        "source_timestamp": payload["source_timestamp"],
        "received_at": payload["received_at"],
        "step": payload["step"],
        "lambda_t": payload["lambda_t"],
        "coherence_gamma": payload["coherence_gamma"],
        "consciousness_psi": payload["consciousness_psi"],
        "symbolic_life_score": payload["symbolic_life_score"],
    }


def _validate_hnc(
    payload: Mapping[str, Any],
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("full_hnc_evidence_required")
    required = {
        "data_status",
        "source_id",
        "source_timestamp",
        "received_at",
        "ts",
        "receipt_id",
        "receipt_type",
        "provider_receipt_type",
        "truth_status",
        "generated_values",
        "input_receipt_ids",
        "memory_receipt_id",
        "memory_canonical_hash",
        "freshness_status",
        "equation_inputs_complete",
        "step",
        "lambda_t",
        "coherence_gamma",
        "consciousness_psi",
        "symbolic_life_score",
        "source_count",
        *_INPUT_FALSE_FLAGS,
    }
    if not required.issubset(payload):
        raise ValueError("full_hnc_evidence_required")
    if (
        payload.get("data_status") != "live"
        or payload.get("source_id") != "aureon:hnc:live_daemon"
        or payload.get("receipt_type") != "hnc_live_field"
        or payload.get("provider_receipt_type") != "hnc_live_field"
        or payload.get("truth_status") != "real_derived"
        or payload.get("freshness_status") != "fresh"
        or payload.get("equation_inputs_complete") is not True
        or payload.get("generated_values") is not False
    ):
        raise ValueError("live_real_hnc_evidence_required")
    _require_false_flags(payload, _INPUT_FALSE_FLAGS)
    source_time, _ = _fresh_timestamp(
        payload.get("source_timestamp"),
        payload.get("received_at"),
        now=now,
        max_age_s=max_age_s,
    )
    if payload.get("ts") != source_time:
        raise ValueError("hnc_source_timestamp_mismatch")
    links = _strings(payload.get("input_receipt_ids"), "hnc_input_receipt_ids", nonempty=True)
    memory_id = _nonblank(payload.get("memory_receipt_id"), "memory_receipt_id")
    if memory_id not in links:
        raise ValueError("hnc_memory_receipt_link_required")
    _digest(payload.get("memory_canonical_hash"), "memory_canonical_hash")
    provider_ids = [item for item in links if item != memory_id]
    if not provider_ids:
        raise ValueError("hnc_provider_receipts_required")
    _integer(payload.get("step"), "step", minimum=1)
    _integer(payload.get("source_count"), "source_count", minimum=1)
    if payload["source_count"] != len(provider_ids):
        raise ValueError("hnc_source_count_mismatch")
    for name in (
        "lambda_t",
        "coherence_gamma",
        "consciousness_psi",
        "symbolic_life_score",
    ):
        value = _finite(payload.get(name), name)
        if name != "lambda_t" and not 0.0 <= value <= 1.0:
            raise ValueError(f"{name}_out_of_range")
    expected_id = f"{_HNC_PREFIX}{_sha256(_hnc_fingerprint(payload))[:24]}"
    if payload.get("receipt_id") != expected_id:
        raise ValueError("hnc_receipt_hash_mismatch")
    return dict(payload)


def _validate_source_receipt(
    payload: Mapping[str, Any],
    *,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != _SOURCE_RECEIPT_KEYS:
        raise ValueError("exact_auris_source_receipt_schema_required")
    if (
        payload.get("truth_status") not in {"live", "real_observed", "real_provider", "real_derived"}
        or payload.get("generated_values") is not False
    ):
        raise ValueError("real_auris_source_receipt_required")
    _require_false_flags(payload, _INPUT_FALSE_FLAGS)
    _nonblank(payload.get("source_id"), "source_id")
    _nonblank(payload.get("receipt_id"), "receipt_id")
    _nonblank(payload.get("receipt_type"), "receipt_type")
    _fresh_timestamp(
        payload.get("source_timestamp"),
        payload.get("received_at"),
        now=now,
        max_age_s=max_age_s,
    )
    _strings(payload.get("input_receipt_ids"), "source_input_receipt_ids")
    return dict(payload)


def _auris_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "input_receipt_ids": payload["input_receipt_ids"],
        "lambda_t": payload["lambda_t"],
        "coherence_gamma": payload["coherence_gamma"],
        "consciousness_psi": payload["consciousness_psi"],
        "cosmic_score": payload["cosmic_score"],
        "earth_blessing": payload["earth_blessing"],
        "gate_open": payload["gate_open"],
        "advisory": payload["advisory"],
    }


def _validate_auris(
    payload: Mapping[str, Any],
    *,
    hnc: Mapping[str, Any],
    now: float,
    max_age_s: float,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not isinstance(payload, Mapping):
        raise ValueError("full_auris_evidence_required")
    required = {
        "data_status",
        "source_id",
        "source_timestamp",
        "received_at",
        "receipt_id",
        "receipt_type",
        "provider_receipt_type",
        "truth_status",
        "generated_values",
        "data_available",
        "input_receipt_ids",
        "hnc_receipt_id",
        "planetary_receipt_ids",
        "source_receipts",
        "sources_live",
        "sources_unavailable",
        "equation_inputs_complete",
        "gate_open",
        "advisory",
        "lambda_t",
        "coherence_gamma",
        "consciousness_psi",
        "cosmic_score",
        "earth_blessing",
        *_INPUT_FALSE_FLAGS,
    }
    if not required.issubset(payload):
        raise ValueError("full_auris_evidence_required")
    if (
        payload.get("data_status") != "live"
        or payload.get("source_id") != "aureon:auris:throne"
        or payload.get("receipt_type") != "auris_cosmic_state"
        or payload.get("provider_receipt_type") != "auris_cosmic_state"
        or payload.get("truth_status") != "real_derived"
        or payload.get("data_available") is not True
        or payload.get("equation_inputs_complete") is not True
        or payload.get("generated_values") is not False
        or not isinstance(payload.get("gate_open"), bool)
    ):
        raise ValueError("live_real_auris_evidence_required")
    _require_false_flags(payload, _INPUT_FALSE_FLAGS)
    source_time, _ = _fresh_timestamp(
        payload.get("source_timestamp"),
        payload.get("received_at"),
        now=now,
        max_age_s=max_age_s,
    )
    links = _strings(payload.get("input_receipt_ids"), "auris_input_receipt_ids", nonempty=True)
    hnc_id = _nonblank(payload.get("hnc_receipt_id"), "hnc_receipt_id")
    if hnc_id != hnc["receipt_id"] or hnc_id not in links:
        raise ValueError("exact_hnc_auris_link_required")
    raw_sources = payload.get("source_receipts")
    if not isinstance(raw_sources, Mapping) or set(raw_sources) != _AURIS_SOURCE_NAMES:
        raise ValueError("complete_auris_source_receipts_required")
    sources = {
        name: _validate_source_receipt(item, now=now, max_age_s=max_age_s)
        for name, item in raw_sources.items()
    }
    hnc_source = sources["hnc"]
    for key in (
        "source_id",
        "source_timestamp",
        "received_at",
        "receipt_id",
        "receipt_type",
        "truth_status",
        "generated_values",
        "input_receipt_ids",
    ):
        if hnc_source[key] != hnc[key]:
            raise ValueError("auris_embedded_hnc_mismatch")
    schumann_id = sources["schumann"]["receipt_id"]
    for name in ("earth_blessing", "earth_gate"):
        if sources[name]["input_receipt_ids"] != [schumann_id]:
            raise ValueError("exact_schumann_derivation_link_required")
    expected_planetary = sorted(sources[name]["receipt_id"] for name in _AURIS_SOURCE_NAMES if name != "hnc")
    if payload.get("planetary_receipt_ids") != expected_planetary:
        raise ValueError("exact_planetary_receipt_ids_required")
    expected_links = sorted(
        {
            *(item["receipt_id"] for item in sources.values()),
            *(link for item in sources.values() for link in item["input_receipt_ids"]),
        }
    )
    if links != expected_links:
        raise ValueError("exact_auris_input_lineage_required")
    if source_time != max(item["source_timestamp"] for item in sources.values()):
        raise ValueError("auris_provider_timestamp_mismatch")
    if payload.get("sources_live") != sorted(_AURIS_SOURCE_NAMES):
        raise ValueError("complete_auris_live_sources_required")
    if payload.get("sources_unavailable") != []:
        raise ValueError("complete_auris_live_sources_required")
    for name in (
        "lambda_t",
        "coherence_gamma",
        "consciousness_psi",
        "cosmic_score",
        "earth_blessing",
    ):
        value = _finite(payload.get(name), name)
        if name != "lambda_t" and not 0.0 <= value <= 1.0:
            raise ValueError(f"{name}_out_of_range")
    _nonblank(payload.get("advisory"), "advisory")
    expected_id = f"{_AURIS_PREFIX}{_sha256(_auris_fingerprint(payload))[:24]}"
    if payload.get("receipt_id") != expected_id:
        raise ValueError("auris_receipt_hash_mismatch")
    return dict(payload), sources


def validate_provider_moment(
    hnc_evidence: Mapping[str, Any],
    auris_evidence: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> ProviderMoment:
    """Validate and bind one exact raw HNC plus Auris provider cycle."""

    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    if age_limit <= 0.0:
        raise ValueError("positive_max_age_required")
    hnc = _validate_hnc(hnc_evidence, now=current, max_age_s=age_limit)
    auris, sources = _validate_auris(
        auris_evidence,
        hnc=hnc,
        now=current,
        max_age_s=age_limit,
    )
    memory_id = hnc["memory_receipt_id"]
    provider_ids = {item for item in hnc["input_receipt_ids"] if item != memory_id}
    for name in _AURIS_PROVIDER_NAMES:
        provider_ids.add(sources[name]["receipt_id"])
        provider_ids.update(sources[name]["input_receipt_ids"])
    normalized_provider_ids = tuple(sorted(provider_ids))
    if not normalized_provider_ids:
        raise ValueError("provider_receipt_ids_required")
    source_moments = [
        {
            "source_name": name,
            "source_id": sources[name]["source_id"],
            "receipt_id": sources[name]["receipt_id"],
            "source_timestamp": sources[name]["source_timestamp"],
        }
        for name in sorted(_AURIS_SOURCE_NAMES)
    ]
    moment_material = {
        "hnc_receipt_id": hnc["receipt_id"],
        "auris_receipt_id": auris["receipt_id"],
        "source_timestamp": auris["source_timestamp"],
        "provider_receipt_ids": list(normalized_provider_ids),
        "source_moments": source_moments,
    }
    return ProviderMoment(
        hnc_receipt_id=hnc["receipt_id"],
        auris_receipt_id=auris["receipt_id"],
        source_timestamp=auris["source_timestamp"],
        provider_receipt_ids=normalized_provider_ids,
        provider_moment_digest=_sha256(moment_material),
    )


def validate_hnc_evidence(
    hnc_evidence: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate one complete fresh HNC field without requiring Auris yet.

    This is the public stage-nine boundary used by pipelines that must organize
    an input through HNC before producing the answer that Auris will gate.
    """

    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    if age_limit <= 0.0:
        raise ValueError("positive_max_age_required")
    return _validate_hnc(hnc_evidence, now=current, max_age_s=age_limit)


def _coherence_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        _TRUTH_GATED_COHERENCE_KEYS
        if payload.get("schema") == TRUTH_GATED_COHERENCE_SCHEMA
        else _COHERENCE_KEYS
    )
    return {key: payload[key] for key in sorted(keys - {"receipt_id", "received_at"})}


def _measured_gamma(levels: Sequence[float], magnitudes: Sequence[float]) -> float:
    count = len(levels)
    # Pearson correlation is undefined for a constant window.  Detect that
    # condition before mean subtraction: fsum(levels) / count can differ from
    # an identical IEEE-754 input by one ULP and otherwise manufacture a tiny
    # signed correlation from a truly zero-variance field.
    if math.isclose(max(levels), min(levels), rel_tol=0.0, abs_tol=1e-12) or math.isclose(
        max(magnitudes),
        min(magnitudes),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return 0.0
    mean_level = math.fsum(levels) / count
    mean_magnitude = math.fsum(magnitudes) / count
    centered_levels = [value - mean_level for value in levels]
    centered_magnitudes = [value - mean_magnitude for value in magnitudes]
    level_scale = math.sqrt(math.fsum(value * value for value in centered_levels))
    magnitude_scale = math.sqrt(math.fsum(value * value for value in centered_magnitudes))
    if level_scale == 0.0 or magnitude_scale == 0.0:
        return 0.0
    gamma = math.fsum(
        left * right for left, right in zip(centered_levels, centered_magnitudes, strict=True)
    ) / (level_scale * magnitude_scale)
    if not math.isfinite(gamma):
        raise ValueError("finite_measured_gamma_required")
    return max(-1.0, min(1.0, gamma))


def validate_coherence_measurement(
    payload: Mapping[str, Any],
    *,
    seat: str,
    agent_id: str,
    source_id: str,
    moment: ProviderMoment,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> tuple[dict[str, Any], float]:
    """Validate a full raw sample window and recompute its Pearson Gamma."""

    if not isinstance(payload, Mapping):
        raise ValueError("exact_coherence_measurement_schema_required")
    schema = payload.get("schema")
    if schema == COHERENCE_SCHEMA:
        expected_keys = _COHERENCE_KEYS
        expected_method = COHERENCE_METHOD
    elif schema == TRUTH_GATED_COHERENCE_SCHEMA:
        expected_keys = _TRUTH_GATED_COHERENCE_KEYS
        expected_method = TRUTH_GATED_COHERENCE_METHOD
    else:
        raise ValueError("exact_coherence_measurement_schema_required")
    if set(payload) != expected_keys:
        raise ValueError("exact_coherence_measurement_schema_required")
    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    if age_limit <= 0.0:
        raise ValueError("positive_max_age_required")
    if (
        payload.get("receipt_type") != "agent_coherence_measurement"
        or payload.get("source_id") != source_id
        or payload.get("seat") != seat
        or payload.get("agent_id") != agent_id
        or payload.get("measurement_method") != expected_method
        or payload.get("data_status") != "live"
        or payload.get("truth_status") != "real_derived"
        or payload.get("freshness_status") != "fresh"
        or payload.get("equation_inputs_complete") is not True
        or payload.get("generated_values") is not False
    ):
        raise ValueError("linked_real_coherence_measurement_required")
    _require_false_flags(payload)
    window_size = _integer(payload.get("window_size"), "window_size", minimum=3)
    sample_count = _integer(payload.get("sample_count"), "sample_count", minimum=3)
    raw_levels = payload.get("operator_levels")
    raw_magnitudes = payload.get("action_magnitudes")
    if not isinstance(raw_levels, list) or not isinstance(raw_magnitudes, list):
        raise ValueError("full_coherence_sample_window_required")
    levels = [_finite(value, "operator_level") for value in raw_levels]
    magnitudes = [_finite(value, "action_magnitude") for value in raw_magnitudes]
    if (
        len(levels) != window_size
        or len(magnitudes) != window_size
        or sample_count != window_size
        or any(value < 0.0 for value in magnitudes)
    ):
        raise ValueError("exact_coherence_sample_window_required")
    sample_ids: list[str] = []
    answer_digests: list[str] = []
    if schema == TRUTH_GATED_COHERENCE_SCHEMA:
        from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
            validate_truth_gated_ten_nine_one_receipt,
        )
        from aureon.harmonic.harmonic_text_alignment import score_text

        raw_samples = payload.get("samples")
        if not isinstance(raw_samples, list) or len(raw_samples) != window_size:
            raise ValueError("full_truth_gated_sample_window_required")
        expected_levels: list[float] = []
        expected_magnitudes: list[float] = []
        sample_times: list[float] = []
        provider_times: list[float] = []
        for raw_sample in raw_samples:
            if not isinstance(raw_sample, Mapping) or set(raw_sample) != {
                "answer_text",
                "thought_path_receipt",
            }:
                raise ValueError("exact_truth_gated_sample_required")
            answer_text = _nonblank(raw_sample.get("answer_text"), "answer_text")
            thought = validate_truth_gated_ten_nine_one_receipt(
                raw_sample.get("thought_path_receipt", {}),
                now=current,
                max_age_s=age_limit,
            )
            inner = thought["inner_receipt"]
            if (
                inner.get("subject_type") != "agent"
                or inner.get("subject_id") != agent_id
                or inner.get("stage") != "auris_coherence_probe"
                or inner.get("work_kind") != "auris_coherence_measurement"
                or _text_sha256(answer_text) != inner.get("answer_digest")
            ):
                raise ValueError("truth_gated_sample_agent_binding_mismatch")
            sample_ids.append(_nonblank(thought.get("receipt_id"), "sample_receipt_id"))
            answer_digests.append(_digest(inner.get("answer_digest"), "answer_digest"))
            expected_levels.append(
                _finite(inner["hnc_receipt"].get("hnc_gamma"), "sample_hnc_gamma")
            )
            text_gamma = _finite(score_text(answer_text).coherence, "answer_text_coherence")
            if not 0.0 <= text_gamma <= 1.0:
                raise ValueError("answer_text_coherence_out_of_range")
            expected_magnitudes.append(text_gamma)
            sample_times.append(_finite(thought.get("derived_at"), "sample_derived_at"))
            provider_times.append(
                _finite(
                    inner["answer_receipt"].get("provider_source_timestamp"),
                    "sample_provider_source_timestamp",
                )
            )
        if (
            len(set(sample_ids)) != window_size
            or sample_times != sorted(sample_times)
            or provider_times != sorted(provider_times)
        ):
            raise ValueError("ordered_unique_truth_gated_samples_required")
        if payload.get("sample_receipt_ids") != sample_ids:
            raise ValueError("truth_gated_sample_receipt_lineage_mismatch")
        if payload.get("answer_digests") != answer_digests:
            raise ValueError("truth_gated_answer_digest_lineage_mismatch")
        if any(
            type(actual) is not float or actual.hex() != expected.hex()
            for actual, expected in zip(levels, expected_levels, strict=True)
        ):
            raise ValueError("truth_gated_operator_levels_mismatch")
        if any(
            type(actual) is not float or actual.hex() != expected.hex()
            for actual, expected in zip(magnitudes, expected_magnitudes, strict=True)
        ):
            raise ValueError("truth_gated_action_magnitudes_mismatch")
        latest_answer = raw_samples[-1]["thought_path_receipt"]["inner_receipt"][
            "answer_receipt"
        ]
        if (
            latest_answer.get("hnc_receipt_id") != moment.hnc_receipt_id
            or latest_answer.get("auris_receipt_id") != moment.auris_receipt_id
            or latest_answer.get("provider_receipt_ids") != list(moment.provider_receipt_ids)
            or latest_answer.get("provider_moment_digest") != moment.provider_moment_digest
            or _finite(
                latest_answer.get("provider_source_timestamp"),
                "latest_provider_source_timestamp",
            )
            != moment.source_timestamp
        ):
            raise ValueError("latest_truth_gated_sample_provider_moment_mismatch")
        window_material = {
            "operator_levels": levels,
            "action_magnitudes": magnitudes,
            "window_size": window_size,
            "sample_receipt_ids": sample_ids,
            "answer_digests": answer_digests,
        }
    else:
        window_material = {
            "operator_levels": levels,
            "action_magnitudes": magnitudes,
            "window_size": window_size,
        }
    if payload.get("window_digest") != _sha256(window_material):
        raise ValueError("coherence_window_digest_mismatch")
    if (
        payload.get("hnc_receipt_id") != moment.hnc_receipt_id
        or payload.get("auris_receipt_id") != moment.auris_receipt_id
        or payload.get("provider_receipt_ids") != list(moment.provider_receipt_ids)
        or payload.get("provider_moment_digest") != moment.provider_moment_digest
    ):
        raise ValueError("coherence_provider_moment_mismatch")
    expected_inputs = sorted(
        {
            moment.hnc_receipt_id,
            moment.auris_receipt_id,
            *moment.provider_receipt_ids,
            *sample_ids,
        }
    )
    if (
        _strings(payload.get("input_receipt_ids"), "coherence_input_receipt_ids", nonempty=True)
        != expected_inputs
    ):
        raise ValueError("exact_coherence_input_lineage_required")
    source_time, _ = _fresh_timestamp(
        payload.get("source_timestamp"),
        payload.get("received_at"),
        now=current,
        max_age_s=age_limit,
    )
    if source_time != moment.source_timestamp:
        raise ValueError("coherence_source_timestamp_mismatch")
    expected_id = f"{_COHERENCE_PREFIX}{_sha256(_coherence_causal(payload))}"
    if payload.get("receipt_id") != expected_id:
        raise ValueError("coherence_receipt_hash_mismatch")
    gamma = _measured_gamma(levels, magnitudes)
    if gamma < 0.0:
        raise ValueError("negative_measured_coherence_cannot_drive_council")
    return dict(payload), gamma


def _node_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in sorted(_NODE_LIVE_KEYS - {"receipt_id", "derived_at"})}


def _no_data(seat: Any, reason: str) -> dict[str, Any]:
    return {
        "schema": NODE_SCHEMA,
        "receipt_type": "auris_node",
        "receipt_id": None,
        "seat": seat if isinstance(seat, str) else None,
        "agent_id": None,
        "resolver_id": None,
        "reason": reason,
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


def issue_auris_node_receipt(
    *,
    seat: str,
    resolver: TrustedAurisNodeResolver,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Issue one node receipt solely from a configured resolver snapshot.

    The caller selects only a stable seat.  Production code is responsible for
    supplying its preconfigured trusted resolver, never a request-provided
    implementation.
    """

    current = time.time() if now is None else now
    try:
        seat_name = _nonblank(seat, "seat").lower()
        if seat_name not in REQUIRED_SEATS:
            raise ValueError("unknown_council_seat")
        if not isinstance(resolver, TrustedAurisNodeResolver):
            raise ValueError("trusted_auris_node_resolver_required")
        resolved = resolver.resolve_auris_node_evidence(seat_name)
        if not isinstance(resolved, ResolvedAurisNodeEvidence):
            raise ValueError("resolved_auris_node_evidence_required")
        if resolved.seat != seat_name:
            raise ValueError("stable_seat_binding_mismatch")
        agent_id = _nonblank(resolved.agent_id, "agent_id")
        resolver_id = _nonblank(resolved.resolver_id, "resolver_id")
        coherence_source_id = _nonblank(
            resolved.coherence_source_id,
            "coherence_source_id",
        )
        moment = validate_provider_moment(
            resolved.hnc_evidence,
            resolved.auris_evidence,
            now=current,
            max_age_s=max_age_s,
        )
        measurement, gamma = validate_coherence_measurement(
            resolved.coherence_evidence,
            seat=seat_name,
            agent_id=agent_id,
            source_id=coherence_source_id,
            moment=moment,
            now=current,
            max_age_s=max_age_s,
        )
        seat_binding_digest = _sha256(
            {
                "resolver_id": resolver_id,
                "seat": seat_name,
                "agent_id": agent_id,
            }
        )
        inputs = sorted(
            {
                moment.hnc_receipt_id,
                moment.auris_receipt_id,
                measurement["receipt_id"],
                *moment.provider_receipt_ids,
            }
        )
        causal = {
            "schema": NODE_SCHEMA,
            "receipt_type": "auris_node",
            "seat": seat_name,
            "agent_id": agent_id,
            "resolver_id": resolver_id,
            "coherence_source_id": coherence_source_id,
            "seat_binding_digest": seat_binding_digest,
            "gamma": gamma,
            "measurement_method": measurement["measurement_method"],
            "coherence_measurement_receipt_id": measurement["receipt_id"],
            "hnc_receipt_id": moment.hnc_receipt_id,
            "auris_receipt_id": moment.auris_receipt_id,
            "provider_receipt_ids": list(moment.provider_receipt_ids),
            "provider_moment_digest": moment.provider_moment_digest,
            "source_timestamp": moment.source_timestamp,
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
        receipt["receipt_id"] = f"{_NODE_PREFIX}{_sha256(causal)}"
        receipt["derived_at"] = _finite(current, "now")
        return receipt
    except (AttributeError, KeyError, TypeError, ValueError):
        return _no_data(seat, "complete_trusted_linked_auris_node_evidence_required")


def validate_auris_node_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate the strict live or numeric-free no-data node schema."""

    if not isinstance(receipt, Mapping) or receipt.get("schema") != NODE_SCHEMA:
        raise ValueError("auris_node_receipt_required")
    if receipt.get("receipt_type") != "auris_node":
        raise ValueError("auris_node_receipt_type_mismatch")
    if receipt.get("data_status") == "no_data":
        if set(receipt) != _NODE_NO_DATA_KEYS:
            raise ValueError("exact_no_data_node_schema_required")
        if (
            receipt.get("receipt_id") is not None
            or receipt.get("agent_id") is not None
            or receipt.get("resolver_id") is not None
            or receipt.get("provider_receipt_ids") != []
            or receipt.get("provider_moment_digest") is not None
            or receipt.get("input_receipt_ids") != []
            or receipt.get("truth_status") != "no_data"
            or receipt.get("freshness_status") != "no_data"
            or receipt.get("equation_inputs_complete") is not False
            or receipt.get("generated_values") is not False
            or receipt.get("route_authorization_required") is not True
        ):
            raise ValueError("invalid_no_data_node_receipt")
        _nonblank(receipt.get("reason"), "reason")
        _require_false_flags(receipt)
        return dict(receipt)
    if set(receipt) != _NODE_LIVE_KEYS:
        raise ValueError("exact_live_node_schema_required")
    if (
        receipt.get("data_status") != "live"
        or receipt.get("truth_status") != "real_derived"
        or receipt.get("freshness_status") != "fresh"
        or receipt.get("equation_inputs_complete") is not True
        or receipt.get("generated_values") is not False
        or receipt.get("route_authorization_required") is not True
        or receipt.get("measurement_method")
        not in {COHERENCE_METHOD, TRUTH_GATED_COHERENCE_METHOD}
    ):
        raise ValueError("live_real_auris_node_receipt_required")
    _require_false_flags(receipt)
    seat = _nonblank(receipt.get("seat"), "seat")
    if seat not in REQUIRED_SEATS:
        raise ValueError("unknown_council_seat")
    agent_id = _nonblank(receipt.get("agent_id"), "agent_id")
    resolver_id = _nonblank(receipt.get("resolver_id"), "resolver_id")
    _nonblank(receipt.get("coherence_source_id"), "coherence_source_id")
    if receipt.get("seat_binding_digest") != _sha256(
        {"resolver_id": resolver_id, "seat": seat, "agent_id": agent_id}
    ):
        raise ValueError("seat_binding_digest_mismatch")
    gamma = _finite(receipt.get("gamma"), "gamma")
    if not 0.0 <= gamma <= 1.0:
        raise ValueError("gamma_out_of_range")
    hnc_id = _nonblank(receipt.get("hnc_receipt_id"), "hnc_receipt_id")
    auris_id = _nonblank(receipt.get("auris_receipt_id"), "auris_receipt_id")
    coherence_id = _nonblank(
        receipt.get("coherence_measurement_receipt_id"),
        "coherence_measurement_receipt_id",
    )
    if (
        not hnc_id.startswith(_HNC_PREFIX)
        or not auris_id.startswith(_AURIS_PREFIX)
        or not coherence_id.startswith(_COHERENCE_PREFIX)
    ):
        raise ValueError("node_receipt_lineage_type_mismatch")
    provider_ids = _strings(
        receipt.get("provider_receipt_ids"),
        "provider_receipt_ids",
        nonempty=True,
    )
    _digest(receipt.get("provider_moment_digest"), "provider_moment_digest")
    expected_inputs = sorted({hnc_id, auris_id, coherence_id, *provider_ids})
    if _strings(receipt.get("input_receipt_ids"), "input_receipt_ids", nonempty=True) != expected_inputs:
        raise ValueError("exact_node_input_lineage_required")
    current = _finite(time.time() if now is None else now, "now")
    age_limit = _finite(max_age_s, "max_age_s")
    source_time = _finite(receipt.get("source_timestamp"), "source_timestamp")
    if age_limit <= 0.0 or source_time > current + FUTURE_SKEW_S or current - source_time > age_limit:
        raise ValueError("fresh_node_source_timestamp_required")
    _finite(receipt.get("derived_at"), "derived_at")
    if receipt.get("receipt_id") != f"{_NODE_PREFIX}{_sha256(_node_causal(receipt))}":
        raise ValueError("auris_node_receipt_hash_mismatch")
    return dict(receipt)


__all__ = [
    "COHERENCE_METHOD",
    "COHERENCE_SCHEMA",
    "DEFAULT_MAX_AGE_S",
    "NODE_SCHEMA",
    "ProviderMoment",
    "ResolvedAurisNodeEvidence",
    "TrustedAurisNodeResolver",
    "TRUTH_GATED_COHERENCE_METHOD",
    "TRUTH_GATED_COHERENCE_SCHEMA",
    "issue_auris_node_receipt",
    "validate_auris_node_receipt",
    "validate_coherence_measurement",
    "validate_hnc_evidence",
    "validate_provider_moment",
]
