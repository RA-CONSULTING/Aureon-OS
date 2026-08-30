"""Live, receipt-backed calibration for the four Druidic Council seats.

The cloud model never supplies HNC, Auris, or its own authority.  A process-
owned resolver pins one already-validated local provider moment while all four
seat agents answer one predetermined calibration task.  The next task cannot
begin until a distinct validated moment is available.  Full truth-gated
10-9-1 receipts, including Hive and Mycelia acknowledgements, are retained as
the only inputs to the Auris node measurement.

This module is evidence-only.  It cannot issue an economic permit or call an
exchange.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from aureon.autonomous.aureon_internal_coding_workforce import (
    WorkforceHold,
    validate_work_receipt,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    ACTIVE_COHERENCE_THRESHOLD,
    TenNineOneEvidenceResolver,
    ThoughtPathRequest,
)
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    validate_truth_gated_ten_nine_one_receipt,
)
from aureon.core.bus_trace import read_trace
from aureon.governance.workforce_auris_node_resolver import (
    TruthGatedWorkforceAurisNodeResolver,
    bind_truth_gated_workforce_auris_resolver,
)
from aureon.governance.workforce_druid_resolver import (
    DEFAULT_WORKFORCE_DRUID_ROLES,
    TrustedWorkforceDecisionEngine,
)
from aureon.harmonic.harmonic_text_alignment import score_text
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_provider_moment,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

CALIBRATION_SCHEMA = "aureon.workforce-auris-live-calibration.v1"
CALIBRATION_HOLD_SCHEMA = "aureon.workforce-auris-live-calibration-hold.v1"
DEFAULT_CALIBRATION_PROMPTS: tuple[str, ...] = (
    (
        "Calibration task A. Select the line that preserves the required "
        "10-9-1 order: vacuum, HNC organization, then one Auris-coherent answer.\n"
        "ALLOWED EXACT RESPONSES:\n"
        "ACCEPT vacuum_hnc_auris_order_verified\n"
        "HOLD evidence_order_not_verified\n"
        "ABORT lineage_conflict_detected"
    ),
    (
        "Calibration task B. Select the line that preserves independent "
        "Council and Crown voices over the same immutable proposal.\n"
        "ALLOWED EXACT RESPONSES:\n"
        "ACCEPT two_independent_runes_same_proposal\n"
        "HOLD one_or_both_runes_unavailable\n"
        "ABORT proposal_lineage_mismatch"
    ),
    (
        "Calibration task C. Select the line that keeps HNC and Auris receipts "
        "as evidence only until the exact route boundary consumes a permit.\n"
        "ALLOWED EXACT RESPONSES:\n"
        "ACCEPT\n"
        "HOLD\n"
        "ABORT"
    ),
)

_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "economic_mutation": False,
}
_PIN_TOKEN = object()


class WorkforceCalibrationHold(ValueError):
    """Carry a complete evidence-only calibration report across a terminal HOLD."""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self.report = _copy(report)
        super().__init__(_nonblank(report.get("reason"), "calibration_hold_reason"))


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


def _positive_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"positive_finite_{label}_required")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"positive_finite_{label}_required")
    return result


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def _pearson(levels: Sequence[float], magnitudes: Sequence[float]) -> float:
    count = len(levels)
    if count != len(magnitudes) or count < 3:
        raise ValueError("complete_calibration_window_required")
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
        left * right
        for left, right in zip(centered_levels, centered_magnitudes, strict=True)
    ) / (level_scale * magnitude_scale)
    if not math.isfinite(gamma):
        raise ValueError("finite_calibration_gamma_required")
    return max(-1.0, min(1.0, gamma))


class PinnedProviderMomentResolver:
    """Expose exactly one validated immutable pair to a thought-path round."""

    def __init__(
        self,
        *,
        _token: object,
        resolver_id: str,
        max_age_s: float,
        clock: Callable[[], float],
    ) -> None:
        if _token is not _PIN_TOKEN:
            raise TypeError("use_bind_pinned_provider_moment_resolver")
        self.resolver_id = _nonblank(resolver_id, "resolver_id")
        self._max_age_s = max_age_s
        self._clock = clock
        self._hnc: dict[str, Any] | None = None
        self._auris: dict[str, Any] | None = None

    def pin(
        self,
        hnc_evidence: Mapping[str, Any],
        auris_evidence: Mapping[str, Any],
    ) -> str:
        now = float(self._clock())
        moment = validate_provider_moment(
            hnc_evidence,
            auris_evidence,
            now=now,
            max_age_s=self._max_age_s,
        )
        gamma = auris_evidence.get("coherence_gamma")
        if (
            isinstance(gamma, bool)
            or not isinstance(gamma, (int, float))
            or not math.isfinite(float(gamma))
            or float(gamma) < ACTIVE_COHERENCE_THRESHOLD
            or auris_evidence.get("gate_open") is not True
        ):
            raise ValueError("active_auris_provider_moment_required")
        self._hnc = _copy(hnc_evidence)
        self._auris = _copy(auris_evidence)
        return moment.provider_moment_digest

    def resolve_hnc_evidence(
        self,
        request: ThoughtPathRequest,
    ) -> Mapping[str, Any] | None:
        del request
        if self._hnc is None or self._auris is None:
            return None
        validate_provider_moment(
            self._hnc,
            self._auris,
            now=float(self._clock()),
            max_age_s=self._max_age_s,
        )
        return _copy(self._hnc)

    def resolve_auris_evidence(
        self,
        request: ThoughtPathRequest,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ) -> Mapping[str, Any] | None:
        del request, answer_digest
        if (
            self._hnc is None
            or self._auris is None
            or self._hnc.get("receipt_id") != hnc_receipt_id
            or self._auris.get("hnc_receipt_id") != hnc_receipt_id
        ):
            return None
        validate_provider_moment(
            self._hnc,
            self._auris,
            now=float(self._clock()),
            max_age_s=self._max_age_s,
        )
        return _copy(self._auris)

    def current_pair(self) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        if self._hnc is None or self._auris is None:
            raise ValueError("provider_moment_not_pinned")
        return _copy(self._hnc), _copy(self._auris)


def bind_pinned_provider_moment_resolver(
    *,
    resolver_id: str,
    trusted_resolver_ids: Collection[str],
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
) -> PinnedProviderMomentResolver:
    resolver_name = _nonblank(resolver_id, "resolver_id")
    trusted = {
        _nonblank(item, "trusted_resolver_id").casefold()
        for item in trusted_resolver_ids
    }
    if resolver_name.casefold() not in trusted:
        raise ValueError("allowlisted_pinned_provider_resolver_required")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    result = PinnedProviderMomentResolver(
        _token=_PIN_TOKEN,
        resolver_id=resolver_name,
        max_age_s=_positive_finite(max_age_s, "max_age_s"),
        clock=clock,
    )
    if not isinstance(result, TenNineOneEvidenceResolver):
        raise AssertionError("ten_nine_one_evidence_resolver_contract_broken")
    return result


def load_latest_active_provider_pair(
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Read the newest complete linked local trace pair without constructing it."""

    current = time.time() if now is None else float(now)
    age = _positive_finite(max_age_s, "max_age_s")
    hnc_rows = {
        row.get("receipt_id"): row
        for row in read_trace("hnc_live_trace", limit=50_000)
        if isinstance(row.get("receipt_id"), str)
    }
    for auris in reversed(read_trace("auris_cosmic_state", limit=500)):
        hnc = hnc_rows.get(auris.get("hnc_receipt_id"))
        if hnc is None:
            continue
        try:
            validate_provider_moment(hnc, auris, now=current, max_age_s=age)
            gamma = auris.get("coherence_gamma")
            if (
                auris.get("gate_open") is True
                and not isinstance(gamma, bool)
                and isinstance(gamma, (int, float))
                and math.isfinite(float(gamma))
                and float(gamma) >= ACTIVE_COHERENCE_THRESHOLD
            ):
                return dict(hnc), dict(auris)
        except (TypeError, ValueError):
            continue
    raise ValueError("fresh_active_hnc_auris_provider_pair_unavailable")


@dataclass(frozen=True, slots=True)
class WorkforceAurisCalibration:
    node_resolver: TruthGatedWorkforceAurisNodeResolver
    report: Mapping[str, Any]
    seat_samples: Mapping[str, tuple[Mapping[str, Any], ...]]


def collect_live_workforce_auris_calibration(
    *,
    workforce: TrustedWorkforceDecisionEngine,
    evidence_resolver: PinnedProviderMomentResolver,
    auris_resolver_id: str,
    trusted_auris_resolver_ids: Collection[str],
    pair_loader: Callable[[], tuple[Mapping[str, Any], Mapping[str, Any]]] = (
        load_latest_active_provider_pair
    ),
    seat_roles: Mapping[str, str] = DEFAULT_WORKFORCE_DRUID_ROLES,
    prompts: Sequence[str] = DEFAULT_CALIBRATION_PROMPTS,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    new_pair_wait_s: float = 45.0,
    poll_interval_s: float = 1.0,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> WorkforceAurisCalibration:
    """Collect distinct live rounds and bind the four measured Auris nodes."""

    if not isinstance(workforce, TrustedWorkforceDecisionEngine):
        raise TypeError("trusted_workforce_decision_engine_required")
    if not isinstance(evidence_resolver, PinnedProviderMomentResolver):
        raise TypeError("pinned_provider_moment_resolver_required")
    if not 3 <= len(prompts) <= 12:
        raise ValueError("calibration_prompt_count_must_be_between_3_and_12")
    prompt_set = tuple(_nonblank(prompt, "calibration_prompt") for prompt in prompts)
    if len(set(prompt_set)) != len(prompt_set):
        raise ValueError("distinct_calibration_prompts_required")
    roles = {
        _nonblank(seat, "seat").lower(): _nonblank(role, "role")
        for seat, role in seat_roles.items()
    }
    if set(roles) != set(REQUIRED_SEATS) or len(set(roles.values())) != 4:
        raise ValueError("exact_distinct_four_calibration_roles_required")
    age = _positive_finite(max_age_s, "max_age_s")
    wait = _positive_finite(new_pair_wait_s, "new_pair_wait_s")
    poll = _positive_finite(poll_interval_s, "poll_interval_s")
    if not callable(pair_loader) or not callable(clock) or not callable(sleep):
        raise TypeError("calibration_runtime_callable_required")
    samples: dict[str, list[Mapping[str, Any]]] = {
        seat: [] for seat in REQUIRED_SEATS
    }
    rounds: list[dict[str, Any]] = []
    seen_moments: set[str] = set()
    seen_hnc_levels: list[float] = []
    final_hnc: Mapping[str, Any] | None = None
    final_auris: Mapping[str, Any] | None = None

    for round_index, prompt in enumerate(prompt_set, start=1):
        deadline = float(clock()) + wait
        while True:
            try:
                hnc, auris = pair_loader()
                moment = validate_provider_moment(
                    hnc,
                    auris,
                    now=float(clock()),
                    max_age_s=age,
                )
            except ValueError as exc:
                if float(clock()) >= deadline:
                    raise ValueError(
                        "fresh_active_provider_pair_wait_expired"
                    ) from exc
                sleep(min(poll, max(0.0, deadline - float(clock()))))
                continue
            hnc_level = float(hnc["coherence_gamma"])
            moment_is_new = moment.provider_moment_digest not in seen_moments
            level_is_new = all(
                not math.isclose(
                    hnc_level,
                    previous,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                for previous in seen_hnc_levels
            )
            if moment_is_new and level_is_new:
                break
            if float(clock()) >= deadline:
                reason = (
                    "distinct_provider_moment_wait_expired"
                    if not moment_is_new
                    else "distinct_hnc_gamma_wait_expired"
                )
                raise ValueError(reason)
            sleep(min(poll, max(0.0, deadline - float(clock()))))
        evidence_resolver.pin(hnc, auris)
        seen_moments.add(moment.provider_moment_digest)
        seen_hnc_levels.append(hnc_level)
        round_outputs: dict[str, str] = {}
        for seat in REQUIRED_SEATS:
            role = roles[seat]
            process_id = _nonblank(
                workforce.process_id_for_role(role),
                "process_id",
            )
            try:
                output, work = workforce.decide(
                    subject_type="agent",
                    subject_id=role,
                    process_id=process_id,
                    prompt=prompt,
                    stage="auris_coherence_probe",
                    work_kind="auris_coherence_measurement",
                    max_tokens=128,
                )
            except WorkforceHold as exc:
                raise ValueError(
                    f"calibration_seat_hold:{round_index}:{seat}:{exc}"
                ) from exc
            if not validate_work_receipt(work):
                raise ValueError("valid_calibration_work_receipt_required")
            thought_by_id = {
                item.get("receipt_id"): item
                for item in getattr(workforce, "thought_path_receipts", ())
                if isinstance(item, Mapping)
            }
            thought = validate_truth_gated_ten_nine_one_receipt(
                thought_by_id.get(work.thought_path_receipt_id, {}),
                now=float(clock()),
                max_age_s=age,
            )
            inner = thought["inner_receipt"]
            if (
                work.actor_id != f"aureon:agent:{role}"
                or work.process_id != process_id
                or work.stage != "auris_coherence_probe"
                or work.work_kind != "auris_coherence_measurement"
                or work.input_digest != _sha(prompt)
                or work.output_digest != _sha(output)
                or inner["hnc_receipt"]["hnc_receipt_id"]
                != hnc.get("receipt_id")
                or inner["answer_receipt"]["auris_receipt_id"]
                != auris.get("receipt_id")
            ):
                raise ValueError("calibration_work_provider_binding_mismatch")
            samples[seat].append(
                {
                    "answer_text": output,
                    "thought_path_receipt": thought,
                }
            )
            round_outputs[seat] = output
        rounds.append(
            {
                "round": round_index,
                "hnc_receipt_id": moment.hnc_receipt_id,
                "auris_receipt_id": moment.auris_receipt_id,
                "provider_moment_digest": moment.provider_moment_digest,
                "source_timestamp": moment.source_timestamp,
                "answer_digests": {
                    seat: _sha(round_outputs[seat]) for seat in REQUIRED_SEATS
                },
            }
        )
        final_hnc, final_auris = hnc, auris

    if final_hnc is None or final_auris is None:
        raise AssertionError("calibration_final_pair_missing")
    seat_correlations: dict[str, dict[str, Any]] = {}
    for seat in REQUIRED_SEATS:
        levels = [
            float(item["thought_path_receipt"]["inner_receipt"]["hnc_receipt"]["hnc_gamma"])
            for item in samples[seat]
        ]
        magnitudes = [float(score_text(item["answer_text"]).coherence) for item in samples[seat]]
        seat_correlations[seat] = {
            "operator_levels": levels,
            "action_magnitudes": magnitudes,
            "measured_gamma": _pearson(levels, magnitudes),
            "sample_receipt_ids": [
                item["thought_path_receipt"]["receipt_id"] for item in samples[seat]
            ],
            "answer_digests": [_sha(item["answer_text"]) for item in samples[seat]],
        }
    negative_seats = [
        seat for seat, item in seat_correlations.items() if item["measured_gamma"] < 0.0
    ]
    if negative_seats:
        causal_hold = {
            "schema": CALIBRATION_HOLD_SCHEMA,
            "status": "hold",
            "reason": "negative_measured_coherence_cannot_drive_council",
            "negative_seats": negative_seats,
            "seat_agents": roles,
            "round_count": len(rounds),
            "sample_count": sum(len(items) for items in samples.values()),
            "provider_moment_digests": [item["provider_moment_digest"] for item in rounds],
            "rounds": rounds,
            "seat_correlations": seat_correlations,
            "seat_samples": {seat: list(samples[seat]) for seat in REQUIRED_SEATS},
            "data_status": "live",
            "truth_status": "real_derived",
            **_FALSE_FLAGS,
        }
        raise WorkforceCalibrationHold(
            {
                **causal_hold,
                "receipt_id": f"aureon:workforce-auris-calibration-hold:{_sha(causal_hold)}",
                "derived_at": float(clock()),
            }
        )
    node_resolver = bind_truth_gated_workforce_auris_resolver(
        resolver_id=auris_resolver_id,
        trusted_resolver_ids=trusted_auris_resolver_ids,
        hnc_evidence=final_hnc,
        auris_evidence=final_auris,
        seat_agents=roles,
        seat_samples=samples,
        now=float(clock()),
        max_age_s=age,
    )
    causal = {
        "schema": CALIBRATION_SCHEMA,
        "resolver_id": node_resolver.resolver_id,
        "seat_agents": roles,
        "round_count": len(rounds),
        "sample_count": sum(len(items) for items in samples.values()),
        "provider_moment_digests": [item["provider_moment_digest"] for item in rounds],
        "rounds": rounds,
        "seat_samples": {seat: list(samples[seat]) for seat in REQUIRED_SEATS},
        "data_status": "live",
        "truth_status": "real_derived",
        **_FALSE_FLAGS,
    }
    report = {
        **causal,
        "receipt_id": f"aureon:workforce-auris-calibration:{_sha(causal)}",
        "derived_at": float(clock()),
    }
    return WorkforceAurisCalibration(
        node_resolver=node_resolver,
        report=report,
        seat_samples={seat: tuple(samples[seat]) for seat in REQUIRED_SEATS},
    )


def validate_workforce_auris_calibration_report(
    report: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
) -> dict[str, Any]:
    """Validate a persisted complete calibration and its full 10-9-1 lineage."""

    expected = {
        "schema",
        "resolver_id",
        "seat_agents",
        "round_count",
        "sample_count",
        "provider_moment_digests",
        "rounds",
        "seat_samples",
        "data_status",
        "truth_status",
        *_FALSE_FLAGS,
        "receipt_id",
        "derived_at",
    }
    if not isinstance(report, Mapping) or set(report) != expected:
        raise ValueError("exact_workforce_auris_calibration_report_required")
    current = _finite(time.time() if now is None else now, "now")
    age = _positive_finite(max_age_s, "max_age_s")
    derived_at = _finite(report.get("derived_at"), "derived_at")
    if derived_at > current + 5.0 or current - derived_at > age:
        raise ValueError("fresh_workforce_auris_calibration_required")
    if (
        report.get("schema") != CALIBRATION_SCHEMA
        or report.get("data_status") != "live"
        or report.get("truth_status") != "real_derived"
        or any(report.get(flag) is not False for flag in _FALSE_FLAGS)
    ):
        raise ValueError("live_non_authoritative_calibration_required")
    _nonblank(report.get("resolver_id"), "resolver_id")
    seat_agents = report.get("seat_agents")
    seat_samples = report.get("seat_samples")
    if not isinstance(seat_agents, Mapping) or not isinstance(seat_samples, Mapping):
        raise ValueError("exact_four_seat_calibration_required")
    if (
        set(seat_agents) != set(REQUIRED_SEATS)
        or set(seat_samples) != set(REQUIRED_SEATS)
    ):
        raise ValueError("exact_four_seat_calibration_required")
    agents = {
        seat: _nonblank(seat_agents.get(seat), "seat_agent") for seat in REQUIRED_SEATS
    }
    if len(set(agents.values())) != len(REQUIRED_SEATS):
        raise ValueError("distinct_four_seat_agents_required")

    rounds = report.get("rounds")
    round_count = report.get("round_count")
    sample_count = report.get("sample_count")
    if (
        isinstance(round_count, bool)
        or not isinstance(round_count, int)
        or not 3 <= round_count <= 12
        or isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or not isinstance(rounds, list)
        or len(rounds) != round_count
    ):
        raise ValueError("valid_calibration_counts_required")
    round_keys = {
        "round",
        "hnc_receipt_id",
        "auris_receipt_id",
        "provider_moment_digest",
        "source_timestamp",
        "answer_digests",
    }
    normalized_rounds: list[dict[str, Any]] = []
    for index, raw_round in enumerate(rounds, start=1):
        if not isinstance(raw_round, Mapping) or set(raw_round) != round_keys:
            raise ValueError("exact_calibration_round_required")
        if raw_round.get("round") != index:
            raise ValueError("ordered_calibration_rounds_required")
        answers = raw_round.get("answer_digests")
        if not isinstance(answers, Mapping) or set(answers) != set(REQUIRED_SEATS):
            raise ValueError("exact_calibration_round_answers_required")
        normalized = dict(raw_round)
        _nonblank(normalized.get("hnc_receipt_id"), "hnc_receipt_id")
        _nonblank(normalized.get("auris_receipt_id"), "auris_receipt_id")
        digest = _nonblank(
            normalized.get("provider_moment_digest"), "provider_moment_digest"
        )
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("provider_moment_digest_required")
        _finite(normalized.get("source_timestamp"), "source_timestamp")
        for seat in REQUIRED_SEATS:
            answer_digest = _nonblank(answers.get(seat), "answer_digest")
            if len(answer_digest) != 64 or any(
                char not in "0123456789abcdef" for char in answer_digest
            ):
                raise ValueError("answer_digest_required")
        normalized_rounds.append(normalized)

    provider_digests = report.get("provider_moment_digests")
    expected_digests = [item["provider_moment_digest"] for item in normalized_rounds]
    if (
        not isinstance(provider_digests, list)
        or provider_digests != expected_digests
        or len(set(provider_digests)) != round_count
    ):
        raise ValueError("distinct_calibration_provider_moments_required")
    validated_samples: dict[str, list[dict[str, Any]]] = {}
    for seat in REQUIRED_SEATS:
        raw_samples = seat_samples.get(seat)
        if not isinstance(raw_samples, list) or len(raw_samples) != round_count:
            raise ValueError("exact_calibration_sample_window_required")
        validated_samples[seat] = []
        for index, raw_sample in enumerate(raw_samples):
            if not isinstance(raw_sample, Mapping) or set(raw_sample) != {
                "answer_text",
                "thought_path_receipt",
            }:
                raise ValueError("exact_calibration_sample_required")
            answer = _nonblank(raw_sample.get("answer_text"), "answer_text")
            thought = validate_truth_gated_ten_nine_one_receipt(
                raw_sample.get("thought_path_receipt", {}),
                now=current,
                max_age_s=age,
            )
            inner = thought["inner_receipt"]
            round_item = normalized_rounds[index]
            if (
                inner.get("subject_type") != "agent"
                or inner.get("subject_id") != agents[seat]
                or inner.get("stage") != "auris_coherence_probe"
                or inner.get("work_kind") != "auris_coherence_measurement"
                or inner.get("answer_digest") != _sha(answer)
                or round_item["answer_digests"][seat] != _sha(answer)
                or inner["hnc_receipt"].get("hnc_receipt_id")
                != round_item["hnc_receipt_id"]
                or inner["answer_receipt"].get("auris_receipt_id")
                != round_item["auris_receipt_id"]
            ):
                raise ValueError("calibration_sample_lineage_mismatch")
            validated_samples[seat].append(
                {"answer_text": answer, "thought_path_receipt": thought}
            )
    if sample_count != round_count * len(REQUIRED_SEATS):
        raise ValueError("calibration_sample_count_mismatch")
    causal = {
        key: _copy(report[key]) for key in expected - {"receipt_id", "derived_at"}
    }
    expected_id = f"aureon:workforce-auris-calibration:{_sha(causal)}"
    if report.get("receipt_id") != expected_id:
        raise ValueError("workforce_auris_calibration_receipt_hash_mismatch")
    validated = _copy(report)
    validated["seat_samples"] = validated_samples
    return validated


__all__ = [
    "CALIBRATION_SCHEMA",
    "DEFAULT_CALIBRATION_PROMPTS",
    "PinnedProviderMomentResolver",
    "WorkforceAurisCalibration",
    "WorkforceCalibrationHold",
    "bind_pinned_provider_moment_resolver",
    "collect_live_workforce_auris_calibration",
    "load_latest_active_provider_pair",
    "validate_workforce_auris_calibration_report",
]
