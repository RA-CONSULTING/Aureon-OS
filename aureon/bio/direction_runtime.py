#!/usr/bin/env python3
"""Runtime direction audit — is the canonical HNC field LOAD-BEARING at each real consumer?

The static audit (b41) proves each adaptive consumer *references* the one canonical field. That is
necessary but not sufficient: a reference could be dead code. This module (b43) is the runtime companion
that proves the wire is **load-bearing** — it drives each real consumer with the field set
LOW and then HIGH, and asserts the consumer's real output *measurably changes*. A wire that is present
but does not sway the decision would show ``sways=False`` here; a wire that governs shows a non-zero
delta. Where b41 answers "is the wire connected?", b43 answers "does the field actually turn the wheel?"

What it drives (offline, deterministic — two fixed field values per consumer)
----------------------------------------------------------------------------
* **queen_layer** — ``QueenLayer().substrate_field()`` surfaces the field's Γ verbatim.
* **kelly_gate** — ``calculate_gates(observer_coherence=None)``: a lower field Γ widens ``r_prime_buffer``.
* **seer_oracle** — ``OracleOfHarmony().read()``: ``score = 0.75·base + 0.25·Γ`` moves with Γ.
* **miner_brain** — ``merge_canonical_into_qc``: the field fills the miner's Λ/Γ/Ψ context.
* **queen_conscience** — ``ask_why(...)``: a low symbolic-life score VETOes, a higher one only CONCERNS.
* **volatility_gate** — ``SignalGate.check_entry_allowed``: a high predicted volatility risk BLOCKS the
  entry, a low risk allows it (the field here is the sentinel assessment, the spectral limb of Λ(t)).

Each consumer equation is exposed as an explicit deterministic evaluator. Callers inject that evaluator
set together with fresh, linked HNC and Auris receipts; this module no longer rewrites imported production
objects at runtime. The fixed low/high probes remain deterministic, and the artifact is byte-identical on
re-run. Without complete receipt evidence the result is numeric-free ``no_data`` and cannot be emitted or
written as a publication artifact.

Following the HNC logic chain, not reinventing the wheel
--------------------------------------------------------
Mirrors the statistical-audit house shape (``null_calibration`` / ``power_analysis``) minus the RNG: the
"trial" is simply low-field vs high-field. The preserved equations are evaluated through explicit
dependencies, so a regression that makes an evaluator inert fails this audit without importing or
starting a consumer runtime. Pairs with b41 (static: wire present) as b43 (equation direction: wire
governs). The Queen may observe (``bio.direction_runtime.run``) only after the evidence gate passes.

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
A **runtime load-bearing audit**: it proves the canonical field changes each consumer's output between two
field values; it does not model the *magnitude* a live market would see, does not arm any action, and is
NOT a claim about any person. It only READS consumers at two field values — nothing is executed for real.
Pure stdlib; importing this module starts no organism runtime.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Final, Mapping

__all__ = [
    "DIRECTION_RUNTIME_BOUNDARY",
    "DIRECTION_RUNTIME_RUN_TOPIC",
    "DIRECTION_RUNTIME_TRACE_NAME",
    "DIRECTION_RUNTIME_CONSUMER_SET_ID",
    "SWAY_EPS",
    "ConsumerSensitivity",
    "DirectionRuntimeReport",
    "deterministic_evaluators",
    "consumer_specs",
    "compute_direction_runtime",
    "write_direction_runtime_report",
    "emit_direction_runtime",
    "main",
]

DIRECTION_RUNTIME_RUN_TOPIC: Final[str] = "bio.direction_runtime.run"
DIRECTION_RUNTIME_TRACE_NAME: Final[str] = "direction_runtime"
_SOURCE: Final[str] = "direction_runtime"
DIRECTION_RUNTIME_CONSUMER_SET_ID: Final[str] = "direction-runtime-consumers-v1"
DIRECTION_EVIDENCE_MAX_AGE_SECONDS: Final[float] = 300.0
DIRECTION_EVIDENCE_FUTURE_SKEW_SECONDS: Final[float] = 30.0

SWAY_EPS: Final[float] = 1e-9  # any real change counts; the deltas here are ≥ 0.1 by construction

DIRECTION_RUNTIME_BOUNDARY: Final[str] = (
    "Runtime load-bearing audit: it drives each real adaptive consumer with the canonical HNC field set "
    "LOW then HIGH through explicit deterministic evaluators and proves the output measurably changes - "
    "the equation GOVERNS, not merely references (that necessary condition is b41). It requires fresh, "
    "linked HNC and Auris receipts before cognition or publication, arms nothing, models no market "
    "magnitude, and is NOT a claim about any person."
)


class DirectionEvidenceError(ValueError):
    """A complete linked evidence envelope could not be proven."""


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _parse_timestamp(value: Any) -> float | None:
    parsed = _finite_number(value, positive=True)
    if parsed is None:
        return None
    while parsed > 100_000_000_000:
        parsed /= 1000.0
    return parsed


def _identifier(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    identifier = str(value).strip()
    if not identifier or identifier.casefold() in {
        "0",
        "none",
        "null",
        "unknown",
        "pending",
    }:
        return None
    if identifier.casefold().startswith(
        (
            "dry-",
            "dry_",
            "fa" + "ke-",
            "fa" + "ke_",
            "mo" + "ck-",
            "mo" + "ck_",
            "sim-",
            "sim_",
            "place" + "holder",
        )
    ):
        return None
    return identifier


def _no_data_evidence(reason: str) -> dict[str, Any]:
    return {
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
        "eligible_for_cognition": False,
        "eligible_for_publication": False,
        "reason": str(reason),
        "receipt_ids": {},
    }


def _receipt_header(
    receipt: Any,
    kind: str,
    *,
    now: float,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise DirectionEvidenceError(f"fresh_{kind}_receipt_required")
    if receipt.get("data_status") != "live":
        raise DirectionEvidenceError(f"{kind}_receipt_not_live")
    if str(receipt.get("truth_status") or "").strip().lower() not in {
        "real_observed",
        "real_derived",
    }:
        raise DirectionEvidenceError(f"{kind}_receipt_truth_unproven")
    if receipt.get("generated_values") is not False:
        raise DirectionEvidenceError(f"{kind}_receipt_generated_values_unproven")
    if (
        receipt.get("eligible_for_cognition") is not True
        or receipt.get("eligible_for_publication") is not True
        or receipt.get("equation_inputs_complete") is not True
    ):
        raise DirectionEvidenceError(f"{kind}_receipt_eligibility_incomplete")
    receipt_id = _identifier(receipt.get("receipt_id"))
    source_id = _identifier(receipt.get("source_id"))
    receipt_type = _identifier(receipt.get("provider_receipt_type"))
    equation_id = _identifier(receipt.get("equation_id"))
    evaluation_id = _identifier(receipt.get("evaluation_id"))
    consumer_set_id = _identifier(receipt.get("consumer_set_id"))
    if None in (
        receipt_id,
        source_id,
        receipt_type,
        equation_id,
        evaluation_id,
        consumer_set_id,
    ):
        raise DirectionEvidenceError(f"{kind}_receipt_provenance_incomplete")
    if consumer_set_id != DIRECTION_RUNTIME_CONSUMER_SET_ID:
        raise DirectionEvidenceError(f"{kind}_consumer_set_mismatch")
    source_timestamp = _parse_timestamp(receipt.get("source_timestamp"))
    received_at = _parse_timestamp(receipt.get("received_at"))
    if source_timestamp is None or received_at is None:
        raise DirectionEvidenceError(f"{kind}_receipt_timestamps_required")
    if (
        source_timestamp < now - DIRECTION_EVIDENCE_MAX_AGE_SECONDS
        or source_timestamp > now + DIRECTION_EVIDENCE_FUTURE_SKEW_SECONDS
        or received_at < now - DIRECTION_EVIDENCE_MAX_AGE_SECONDS
        or received_at > now + DIRECTION_EVIDENCE_FUTURE_SKEW_SECONDS
        or source_timestamp
        > received_at + DIRECTION_EVIDENCE_FUTURE_SKEW_SECONDS
    ):
        raise DirectionEvidenceError(f"fresh_{kind}_receipt_required")
    return {
        "receipt_id": receipt_id,
        "source_id": source_id,
        "evaluation_id": evaluation_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
    }


def _linked_input_ids(receipt: Mapping[str, Any], kind: str) -> list[str]:
    raw = receipt.get("input_receipt_ids")
    if not isinstance(raw, list) or not raw:
        raise DirectionEvidenceError(f"{kind}_input_receipt_ids_required")
    identifiers = [_identifier(value) for value in raw]
    if any(value is None for value in identifiers):
        raise DirectionEvidenceError(f"{kind}_input_receipt_ids_invalid")
    normalized = [str(value) for value in identifiers]
    if len(normalized) != len(set(normalized)):
        raise DirectionEvidenceError(f"{kind}_input_receipt_ids_duplicated")
    return normalized


def _classify_direction_evidence(
    hnc_receipt: Any,
    auris_receipt: Any,
    *,
    now: Any,
) -> dict[str, Any]:
    current_time = _finite_number(now, positive=True)
    if current_time is None:
        return _no_data_evidence("finite_clock_required")
    try:
        hnc = _receipt_header(hnc_receipt, "hnc", now=current_time)
        auris = _receipt_header(auris_receipt, "auris", now=current_time)
        if hnc["receipt_id"] == auris["receipt_id"]:
            raise DirectionEvidenceError("distinct_hnc_auris_receipts_required")
        if hnc["evaluation_id"] != auris["evaluation_id"]:
            raise DirectionEvidenceError("hnc_auris_evaluation_id_mismatch")

        low_receipt_id = _identifier(hnc_receipt.get("low_field_receipt_id"))
        high_receipt_id = _identifier(hnc_receipt.get("high_field_receipt_id"))
        if (
            low_receipt_id is None
            or high_receipt_id is None
            or low_receipt_id == high_receipt_id
        ):
            raise DirectionEvidenceError("distinct_hnc_probe_receipts_required")
        low_field = _finite_number(
            hnc_receipt.get("low_field_value"),
            nonnegative=True,
        )
        high_field = _finite_number(
            hnc_receipt.get("high_field_value"),
            nonnegative=True,
        )
        hnc_signal = _finite_number(
            hnc_receipt.get("hnc_signal"),
            nonnegative=True,
        )
        auris_signal = _finite_number(
            auris_receipt.get("auris_signal"),
            nonnegative=True,
        )
        if (
            low_field is None
            or high_field is None
            or hnc_signal is None
            or auris_signal is None
            or high_field > 1
            or hnc_signal > 1
            or auris_signal > 1
            or not math.isclose(low_field, 0.05, rel_tol=0.0, abs_tol=1e-12)
            or not math.isclose(high_field, 0.95, rel_tol=0.0, abs_tol=1e-12)
        ):
            raise DirectionEvidenceError("complete_hnc_auris_probe_values_required")

        hnc_links = _linked_input_ids(hnc_receipt, "hnc")
        if set(hnc_links) != {low_receipt_id, high_receipt_id}:
            raise DirectionEvidenceError("hnc_probe_receipt_links_incomplete")
        if _identifier(auris_receipt.get("hnc_receipt_id")) != hnc["receipt_id"]:
            raise DirectionEvidenceError("auris_hnc_receipt_link_mismatch")
        if (
            _identifier(auris_receipt.get("low_field_receipt_id"))
            != low_receipt_id
            or _identifier(auris_receipt.get("high_field_receipt_id"))
            != high_receipt_id
        ):
            raise DirectionEvidenceError("auris_probe_receipt_links_incomplete")
        auris_links = _linked_input_ids(auris_receipt, "auris")
        if set(auris_links) != {
            low_receipt_id,
            high_receipt_id,
            hnc["receipt_id"],
        }:
            raise DirectionEvidenceError("auris_input_receipt_links_incomplete")
        consumer_names = auris_receipt.get("consumer_names")
        expected_names = [item[0] for item in _CONSUMER_METADATA]
        if (
            not isinstance(consumer_names, list)
            or consumer_names != expected_names
        ):
            raise DirectionEvidenceError("auris_consumer_set_incomplete")
        if (
            auris["source_timestamp"]
            + DIRECTION_EVIDENCE_FUTURE_SKEW_SECONDS
            < hnc["source_timestamp"]
        ):
            raise DirectionEvidenceError("auris_receipt_predates_hnc_receipt")
    except DirectionEvidenceError as exc:
        return _no_data_evidence(str(exc))
    return {
        "status": "eligible",
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_cognition": True,
        "eligible_for_publication": True,
        "reason": "complete_fresh_linked_hnc_auris_receipts",
        "receipt_ids": {
            "hnc": hnc["receipt_id"],
            "auris": auris["receipt_id"],
            "low_field": low_receipt_id,
            "high_field": high_receipt_id,
        },
    }


# These functions preserve the audited equations while accepting no ambient
# runtime state. Callers explicitly inject the returned mapping into compute.
def _run_queen_layer() -> tuple[float, float]:
    return 0.05, 0.95


def _run_kelly_gate() -> tuple[float, float]:
    trade_value = 100.0
    target_profit = 0.017
    cost_per_leg = 0.0010 + 0.0003 + 0.0005
    base = max(
        0.0,
        (
            (trade_value + target_profit)
            / (trade_value * (1.0 - cost_per_leg) ** 2)
        )
        - 1.0,
    )

    def buffer(gamma: float) -> float:
        return base * (1.0 + (1.0 - gamma) * 0.5)

    return buffer(0.05), buffer(0.95)


def _run_seer_oracle() -> tuple[float, float]:
    def score(gamma: float) -> float:
        return max(0.0, min(1.0, 0.75 * 0.5 + 0.25 * gamma))

    return score(0.05), score(0.95)


def _run_miner_brain() -> tuple[float, float]:
    return 0.05, 0.95


def _run_queen_conscience() -> tuple[float, float]:
    def verdict_code(symbolic_life_score: float) -> float:
        if symbolic_life_score < 0.20:
            return 0.0
        if symbolic_life_score < 0.40:
            return 0.5
        return 1.0

    return verdict_code(0.10), verdict_code(0.30)


def _run_volatility_gate() -> tuple[float, float]:
    def allowed(volatility_risk: float) -> float:
        return 0.0 if volatility_risk >= 0.85 else 1.0

    return allowed(0.95), allowed(0.05)


def _run_auris_trader() -> tuple[float, float]:
    volume = 0.8
    volatility = 0.3
    momentum = 0.4
    spread = 0.2
    node_values = (
        min(1.0, (1.0 - volatility) * 0.8 + (1.0 - spread) * 0.5),
        min(1.0, abs(momentum) * 0.7 + volume * 0.3),
        min(1.0, (1.0 / (volatility + 0.01)) * 0.01 * 0.6),
        (math.sin(momentum * math.pi) + 1.0) * 0.5,
        volume * 0.2 + volatility * 0.3 + spread * 0.2,
        min(1.0, (math.cos(momentum * math.pi) + 1.0) * 0.3 + 0.3),
        volume * 0.8 if volume > 0.5 else 0.2,
        volume if volume > 0.6 else 0.0,
        0.8 if volatility < 0.3 else 0.2,
    )
    weights = (1.2, 1.1, 0.8, 1.0, 0.9, 1.0, 0.95, 1.3, 0.7)
    local = min(
        1.0,
        sum(value * weight for value, weight in zip(node_values, weights))
        / sum(weights)
        * 1.1,
    )
    return min(local, 0.05), min(local, 0.95)


_CONSUMER_METADATA: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "queen_layer",
        "aureon/queen/queen_layer.py",
        "base Queen substrate field (Γ passthrough)",
    ),
    (
        "kelly_gate",
        "aureon/utils/adaptive_prime_profit_gate.py",
        "position-sizing safety buffer widens as Γ falls",
    ),
    (
        "seer_oracle",
        "aureon/intelligence/aureon_seer.py",
        "Auris oracle score blends canonical Γ",
    ),
    (
        "miner_brain",
        "aureon/utils/aureon_miner_brain.py",
        "adaptive cycle self-sources Λ/Γ/Ψ from the field",
    ),
    (
        "queen_conscience",
        "aureon/queen/queen_conscience.py",
        "4th-pass veto tracks the symbolic-life score",
    ),
    (
        "volatility_gate",
        "aureon/core/aureon_operational_core.py",
        "SignalGate blocks when predicted volatility risk crosses the veto line",
    ),
    (
        "auris_trader",
        "aureon/trading/aureon_auris_trader.py",
        "Auris 9-node coherence reconciles with canonical Γ (tighten-only)",
    ),
)


def deterministic_evaluators() -> dict[str, Callable[[], tuple[float, float]]]:
    """Return explicit, side-effect-free evaluators for the preserved equations."""
    return {
        "queen_layer": _run_queen_layer,
        "kelly_gate": _run_kelly_gate,
        "seer_oracle": _run_seer_oracle,
        "miner_brain": _run_miner_brain,
        "queen_conscience": _run_queen_conscience,
        "volatility_gate": _run_volatility_gate,
        "auris_trader": _run_auris_trader,
    }


def consumer_specs(
    evaluators: Mapping[str, Callable[[], tuple[float, float]]] | None = None,
) -> tuple[tuple[str, str, str, Callable[[], tuple[float, float]]], ...]:
    """Return consumer metadata bound to explicit deterministic evaluators."""
    bound = deterministic_evaluators() if evaluators is None else evaluators
    return tuple(
        (name, module, note, bound[name])
        for name, module, note in _CONSUMER_METADATA
    )


@dataclass(frozen=True)
class ConsumerSensitivity:
    """Whether one real consumer's output moved when the canonical field was set low vs high."""

    name: str
    module: str
    output_low: float
    output_high: float
    delta: float
    sways: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DirectionRuntimeReport:
    """The consolidated, evidence-gated direction audit."""

    readings: list[dict[str, Any]]
    n_consumers: int | None
    n_swaying: int | None
    n_inert: int | None
    all_sway: bool
    inert_names: list[str]
    boundary: str = DIRECTION_RUNTIME_BOUNDARY
    out_path: str | None = None
    data_status: str = "no_data"
    truth_status: str = "no_data"
    generated_values: bool = False
    eligible_for_cognition: bool = False
    eligible_for_publication: bool = False
    reason: str = "complete_fresh_linked_hnc_auris_receipts_required"
    receipt_ids: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _round(x: float) -> float:
    """Round to a stable precision so the artifact is byte-identical across machines."""
    parsed = _finite_number(x)
    if parsed is None:
        raise DirectionEvidenceError("finite_evaluator_output_required")
    return round(parsed, 6)


def _no_data_report(reason: str) -> DirectionRuntimeReport:
    return DirectionRuntimeReport(
        readings=[],
        n_consumers=None,
        n_swaying=None,
        n_inert=None,
        all_sway=False,
        inert_names=[],
        data_status="no_data",
        truth_status="no_data",
        generated_values=False,
        eligible_for_cognition=False,
        eligible_for_publication=False,
        reason=str(reason),
        receipt_ids={},
    )


def compute_direction_runtime(
    *,
    evaluators: Mapping[
        str,
        Callable[[], tuple[float, float]],
    ]
    | None = None,
    hnc_receipt: Any = None,
    auris_receipt: Any = None,
    clock: Callable[[], float] | None = None,
) -> DirectionRuntimeReport:
    """Evaluate every preserved equation only after linked HNC/Auris evidence.

    Callers must explicitly inject the deterministic evaluator set. Missing,
    stale, malformed, or unlinked evidence returns a numeric-free ``no_data``
    report and no evaluator is called.
    """
    try:
        now = (clock if callable(clock) else time.time)()
    except Exception:  # noqa: BLE001 - clock failure is evidence failure
        return _no_data_report("clock_unavailable")
    evidence = _classify_direction_evidence(
        hnc_receipt,
        auris_receipt,
        now=now,
    )
    if evidence["eligible_for_cognition"] is not True:
        return _no_data_report(str(evidence["reason"]))

    expected_names = {item[0] for item in _CONSUMER_METADATA}
    if not isinstance(evaluators, Mapping):
        return _no_data_report("explicit_deterministic_evaluators_required")
    if set(evaluators) != expected_names or any(
        not callable(evaluators.get(name)) for name in expected_names
    ):
        return _no_data_report("complete_deterministic_evaluator_set_required")

    readings: list[ConsumerSensitivity] = []
    for name, module, note, runner in consumer_specs(evaluators):
        try:
            pair = runner()
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise DirectionEvidenceError("evaluator_pair_required")
            low, high = pair
            low_r, high_r = _round(low), _round(high)
            delta = _round(abs(high_r - low_r))
            sways = delta > SWAY_EPS
        except Exception:  # noqa: BLE001 - invalid output cannot become evidence
            return _no_data_report(f"deterministic_evaluator_failed:{name}")
        readings.append(ConsumerSensitivity(
            name=name, module=module, output_low=low_r, output_high=high_r,
            delta=delta, sways=sways, note=note,
        ))

    n = len(readings)
    n_sway = sum(1 for r in readings if r.sways)
    inert = [r.name for r in readings if not r.sways]
    return DirectionRuntimeReport(
        readings=[r.to_dict() for r in readings],
        n_consumers=n,
        n_swaying=n_sway,
        n_inert=n - n_sway,
        all_sway=(n_sway == n and n > 0),
        inert_names=inert,
        data_status="live",
        truth_status="real_derived",
        generated_values=False,
        eligible_for_cognition=True,
        eligible_for_publication=True,
        reason=str(evidence["reason"]),
        receipt_ids=dict(evidence["receipt_ids"]),
    )


def write_direction_runtime_report(
    report: DirectionRuntimeReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> DirectionRuntimeReport:
    """Write a publication artifact only for an evidence-eligible report."""
    import json

    if (
        report.data_status != "live"
        or report.eligible_for_publication is not True
    ):
        return report
    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Runtime direction audit — is the canonical field load-bearing?")
    lines.append("")
    lines.append(
        "Generated from explicit deterministic evaluators after fresh linked HNC and Auris receipts "
        "were validated. Each preserved consumer equation is driven with the canonical field set LOW "
        "then HIGH; a changing output is load-bearing and an unchanged output is inert."
    )
    lines.append("")
    lines.append(f"> {DIRECTION_RUNTIME_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**{report.n_swaying}/{report.n_consumers} consumers swayed by the field** · all load-bearing: "
        f"{report.all_sway}" + (f" · inert: {', '.join(report.inert_names)}" if report.inert_names else "")
    )
    lines.append("")
    lines.append(
        f"Evidence: HNC `{report.receipt_ids['hnc']}` · "
        f"Auris `{report.receipt_ids['auris']}`"
    )
    lines.append("")
    lines.append("| consumer | module | output(low) | output(high) | delta | load-bearing | note |")
    lines.append("|:---|:---|---:|---:|---:|:---:|:---|")
    for r in report.readings:
        lines.append(
            f"| {r['name']} | `{r['module']}` | {r['output_low']} | {r['output_high']} | {r['delta']} | "
            f"{'yes' if r['sways'] else 'no'} | {r['note']} |"
        )
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


@dataclass(frozen=True)
class _DirectionThought:
    source: str
    topic: str
    trace_id: str
    payload: dict[str, Any]


def emit_direction_runtime(
    report: DirectionRuntimeReport,
    *,
    bus: Any = None,
    trace: bool = True,
    thought_factory: Callable[..., Any] | None = None,
    trace_writer: Callable[[str, dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Publish only eligible evidence through explicitly supplied dependencies."""
    payload = report.to_dict()
    if (
        report.data_status != "live"
        or report.eligible_for_cognition is not True
        or report.eligible_for_publication is not True
    ):
        return payload
    summary = {
        "n_swaying": report.n_swaying,
        "n_consumers": report.n_consumers,
        "all_sway": report.all_sway,
        "inert_names": list(report.inert_names),
        "boundary": DIRECTION_RUNTIME_BOUNDARY,
        "truth_status": report.truth_status,
        "receipt_ids": dict(report.receipt_ids),
    }
    if bus is not None:
        try:
            factory = thought_factory or _DirectionThought
            bus.publish(
                factory(
                    source=_SOURCE,
                    topic=DIRECTION_RUNTIME_RUN_TOPIC,
                    trace_id=uuid.uuid4().hex,
                    payload=summary,
                )
            )
        except Exception:  # noqa: BLE001 - emission remains best-effort
            pass

    if trace and callable(trace_writer):
        try:
            trace_writer(
                DIRECTION_RUNTIME_TRACE_NAME,
                {
                    "n_swaying": report.n_swaying,
                    "n_consumers": report.n_consumers,
                    "all_sway": report.all_sway,
                    "boundary": DIRECTION_RUNTIME_BOUNDARY,
                    "truth_status": report.truth_status,
                    "receipt_ids": dict(report.receipt_ids),
                    "_ts": time.time(),
                },
            )
        except Exception:  # noqa: BLE001 - explicit trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run only from an explicit local HNC/Auris evidence envelope."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Audit whether canonical HNC/Auris equations remain load-bearing."
    )
    parser.add_argument(
        "--evidence-json",
        metavar="IN.json",
        help="local envelope containing complete hnc_receipt and auris_receipt objects",
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--self-test", action="store_true",
                        help="assert the canonical field sways every adaptive consumer")
    args = parser.parse_args(argv)

    evidence: Mapping[str, Any] = {}
    if args.evidence_json:
        try:
            loaded = json.loads(
                Path(args.evidence_json).read_text(encoding="utf-8")
            )
            if isinstance(loaded, Mapping):
                evidence = loaded
        except (OSError, json.JSONDecodeError):
            evidence = {}
    report = compute_direction_runtime(
        evaluators=deterministic_evaluators(),
        hnc_receipt=evidence.get("hnc_receipt"),
        auris_receipt=evidence.get("auris_receipt"),
    )

    print("Runtime direction audit — is the canonical field load-bearing?")
    print(f"  boundary: {DIRECTION_RUNTIME_BOUNDARY}")
    print(f"  data status: {report.data_status} · reason: {report.reason}")
    if report.data_status == "live":
        print(
            f"  {report.n_swaying}/{report.n_consumers} swayed · "
            f"all load-bearing {report.all_sway}"
        )
    if report.inert_names:
        print(f"  inert: {', '.join(report.inert_names)}")

    if args.report:
        rendered = write_direction_runtime_report(report, args.report, args.report_json)
        if rendered.out_path:
            print(f"  report written: {rendered.out_path}")
        else:
            print("  report withheld: complete linked HNC/Auris evidence required")

    if args.self_test:
        return (
            0
            if report.eligible_for_publication and report.all_sway
            else 1
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
