"""Formal evidence logic for the Aureon Bluetooth battery experiment.

The legacy experiment files are useful exploratory observations, but they use
mixed protocols, sequential treatment order, coarse battery percentages, and
incomplete workload controls.  This module keeps those observations intact and
adds the missing scientific control layer:

* a deterministic experiment state machine;
* typed, high-resolution battery telemetry;
* preflight and run-quality gates;
* randomized block scheduling with a sham arm;
* paired effect estimation with an explicit confidence decision; and
* a read-only audit adapter for ``data/experiments/zpe``.

No energy-generation claim is encoded here.  Positive, negative, null, invalid,
and inconclusive outcomes are all first-class results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aureon-bluetooth-battery-experiment-v1"
LEGACY_AUDIT_VERSION = "aureon-bluetooth-battery-legacy-audit-v1"


class Arm(StrEnum):
    """Experiment arm recorded for one measurement segment."""

    BASELINE = "baseline"
    BLE_ACTIVE = "ble_active"
    SHAM = "sham"


class Stage(StrEnum):
    """Formal experiment lifecycle."""

    DRAFT = "draft"
    PREFLIGHT = "preflight"
    WARMUP = "warmup"
    MEASURING = "measuring"
    COMPLETE = "complete"
    INVALID = "invalid"
    ANALYSED = "analysed"


class Decision(StrEnum):
    """Allowed evidence decisions."""

    INVALID = "invalid"
    INCONCLUSIVE = "inconclusive"
    NO_MEASURABLE_EFFECT = "no_measurable_effect"
    BLE_REDUCED_DRAIN = "ble_reduced_drain"
    BLE_INCREASED_DRAIN = "ble_increased_drain"


class EvidenceGrade(StrEnum):
    """Strength of the design supporting a result."""

    EXPLORATORY = "exploratory"
    CONTROLLED_SINGLE_DEVICE = "controlled_single_device"
    REPLICATED_MULTI_DEVICE = "replicated_multi_device"


@dataclass(frozen=True)
class Protocol:
    """Pre-registered controls and decision thresholds."""

    protocol_id: str = "AUREON-BLE-BATTERY-RCT-V1"
    hypothesis: str = (
        "A controlled BLE treatment changes mean laptop battery discharge power "
        "relative to matched baseline and sham segments."
    )
    primary_metric: str = "battery_capacity_slope_mw"
    target_payload_label_hz: float = 12.669206131911677
    segment_duration_s: float = 1800.0
    warmup_s: float = 300.0
    washout_s: float = 300.0
    sample_interval_s: float = 1.0
    minimum_samples_per_run: int = 1500
    minimum_complete_blocks: int = 10
    minimum_devices_for_replication: int = 3
    minimum_independent_operators: int = 2
    practical_effect_pct: float = 5.0
    max_cpu_mean_delta_pct: float = 5.0
    max_temperature_mean_delta_c: float = 2.0
    require_sham: bool = True
    require_randomization: bool = True
    require_blinded_analysis: bool = True
    require_remaining_mwh: bool = True
    require_cpu_telemetry: bool = True


@dataclass(frozen=True)
class BatterySample:
    """One time-aligned observation from the laptop and BLE controller."""

    elapsed_s: float
    remaining_mwh: float | None
    rate_mw: float | None
    percent: float | None
    ac_online: bool
    cpu_percent: float | None
    temperature_c: float | None
    radio_active: bool
    advertisement_count: int


@dataclass(frozen=True)
class ExperimentRun:
    """One baseline, active, or sham segment within a randomized block."""

    run_id: str
    protocol_id: str
    arm: Arm
    block_index: int
    sequence_position: int
    samples: tuple[BatterySample, ...]
    device_id: str
    operator_id: str
    workload_hash: str
    power_mode: str
    brightness_percent: float
    block_randomization_id: str
    analyst_blinded: bool
    payload_frequency_label_hz: float | None = None
    measured_advertisement_rate_hz: float | None = None
    radio_tx_power_dbm: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = SCHEMA_VERSION
        payload["arm"] = self.arm.value
        return payload


@dataclass(frozen=True)
class RunValidation:
    """Quality-gate result for a single run."""

    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunMetric:
    """Primary and control metrics derived from one valid run."""

    run_id: str
    arm: Arm
    duration_s: float
    discharge_power_mw: float
    average_reported_discharge_mw: float | None
    average_cpu_percent: float | None
    average_temperature_c: float | None
    radio_active_fraction: float
    advertisement_count_delta: int


@dataclass(frozen=True)
class AnalysisResult:
    """Auditable experiment-level decision."""

    decision: Decision
    evidence_grade: EvidenceGrade
    complete_blocks: int
    invalid_runs: tuple[str, ...]
    invalid_blocks: tuple[int, ...]
    effect_mw: float | None
    effect_ci95_mw: tuple[float, float] | None
    relative_effect_pct: float | None
    device_count: int
    operator_count: int
    causal_claim_allowed: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        payload["evidence_grade"] = self.evidence_grade.value
        return payload


@dataclass
class ExperimentController:
    """Small deterministic state machine for one experiment run."""

    stage: Stage = Stage.DRAFT
    history: list[dict[str, str]] = field(default_factory=list)

    _TRANSITIONS = {
        Stage.DRAFT: {"register": Stage.PREFLIGHT, "invalidate": Stage.INVALID},
        Stage.PREFLIGHT: {"preflight_passed": Stage.WARMUP, "invalidate": Stage.INVALID},
        Stage.WARMUP: {"warmup_complete": Stage.MEASURING, "invalidate": Stage.INVALID},
        Stage.MEASURING: {"measurement_complete": Stage.COMPLETE, "invalidate": Stage.INVALID},
        Stage.COMPLETE: {"analysis_complete": Stage.ANALYSED, "invalidate": Stage.INVALID},
        Stage.INVALID: {},
        Stage.ANALYSED: {},
    }

    def transition(self, event: str, reason: str = "") -> Stage:
        next_stage = self._TRANSITIONS[self.stage].get(event)
        if next_stage is None:
            raise ValueError(f"event {event!r} is not allowed from stage {self.stage.value!r}")
        self.history.append(
            {
                "from": self.stage.value,
                "event": event,
                "to": next_stage.value,
                "reason": reason,
            }
        )
        self.stage = next_stage
        return self.stage


def generate_block_schedule(
    blocks: int,
    seed: int,
    *,
    include_sham: bool = True,
) -> list[dict[str, Any]]:
    """Generate a reproducible, balanced within-block arm order."""

    if blocks < 1:
        raise ValueError("blocks must be at least 1")
    rng = random.Random(seed)
    arms = [Arm.BASELINE, Arm.BLE_ACTIVE]
    if include_sham:
        arms.append(Arm.SHAM)

    schedule: list[dict[str, Any]] = []
    for block_index in range(1, blocks + 1):
        order = list(arms)
        rng.shuffle(order)
        randomization_id = hashlib.sha256(
            f"{seed}:{block_index}:{','.join(arm.value for arm in order)}".encode()
        ).hexdigest()[:16]
        for position, arm in enumerate(order, start=1):
            schedule.append(
                {
                    "block_index": block_index,
                    "sequence_position": position,
                    "arm": arm.value,
                    "block_randomization_id": randomization_id,
                }
            )
    return schedule


def protocol_manifest(protocol: Protocol, *, seed: int, blocks: int | None = None) -> dict[str, Any]:
    """Return a serializable pre-registration manifest."""

    block_count = blocks if blocks is not None else protocol.minimum_complete_blocks
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol": asdict(protocol),
        "randomization": {
            "seed_sha256": hashlib.sha256(str(seed).encode()).hexdigest(),
            "schedule": generate_block_schedule(
                block_count,
                seed,
                include_sham=protocol.require_sham,
            ),
        },
        "claim_boundary": (
            "The payload label is not proof of a physical field at that frequency. "
            "Measured radio cadence, battery energy, workload, and environmental controls are required."
        ),
    }


def validate_run(run: ExperimentRun, protocol: Protocol) -> RunValidation:
    """Apply deterministic run-level quality gates."""

    errors: list[str] = []
    warnings: list[str] = []
    samples = run.samples

    if run.protocol_id != protocol.protocol_id:
        errors.append("protocol_id does not match the active pre-registration")
    if not run.run_id.strip():
        errors.append("run_id is required")
    if run.block_index < 1 or run.sequence_position < 1:
        errors.append("block_index and sequence_position must be positive")
    if protocol.require_randomization and not run.block_randomization_id.strip():
        errors.append("block randomization evidence is required")
    if protocol.require_blinded_analysis and not run.analyst_blinded:
        errors.append("analysis must remain blinded until run metrics are frozen")
    if not run.device_id.strip() or not run.operator_id.strip():
        errors.append("device_id and operator_id are required")
    if not run.workload_hash.strip():
        errors.append("a reproducible workload hash is required")
    if not run.power_mode.strip():
        errors.append("power mode is required")
    if not 0.0 <= run.brightness_percent <= 100.0:
        errors.append("brightness_percent must be between 0 and 100")
    if len(samples) < protocol.minimum_samples_per_run:
        errors.append(
            f"run has {len(samples)} samples; minimum is {protocol.minimum_samples_per_run}"
        )
    if len(samples) < 2:
        errors.append("at least two samples are required")
        return RunValidation(False, tuple(errors), tuple(warnings))

    times = [sample.elapsed_s for sample in samples]
    if any(not math.isfinite(value) for value in times):
        errors.append("sample timestamps must be finite")
    if any(current <= previous for previous, current in zip(times, times[1:], strict=False)):
        errors.append("sample timestamps must be strictly increasing")
    duration = times[-1] - times[0]
    if duration < protocol.segment_duration_s:
        errors.append(
            f"run duration {duration:.1f}s is below required {protocol.segment_duration_s:.1f}s"
        )
    if any(sample.ac_online for sample in samples):
        errors.append("AC power was observed during the run")

    mwh_values = [sample.remaining_mwh for sample in samples]
    if protocol.require_remaining_mwh and any(value is None for value in mwh_values):
        errors.append("high-resolution remaining_mwh telemetry is required for every sample")
    if any(value is not None and not math.isfinite(value) for value in mwh_values):
        errors.append("remaining_mwh values must be finite")

    cpu_values = [sample.cpu_percent for sample in samples]
    if protocol.require_cpu_telemetry and any(value is None for value in cpu_values):
        errors.append("CPU telemetry is required for every sample")
    if any(value is not None and not 0.0 <= value <= 100.0 for value in cpu_values):
        errors.append("CPU percentages must be between 0 and 100")

    if any(sample.temperature_c is None for sample in samples):
        warnings.append("temperature telemetry is incomplete")

    radio_fraction = statistics.fmean(1.0 if sample.radio_active else 0.0 for sample in samples)
    if run.arm == Arm.BASELINE and radio_fraction > 0.05:
        errors.append("baseline arm contains active BLE radio samples")
    if run.arm in (Arm.BLE_ACTIVE, Arm.SHAM) and radio_fraction < 0.95:
        errors.append("BLE active and sham arms require radio activity for at least 95% of samples")
    if run.arm == Arm.BLE_ACTIVE and run.payload_frequency_label_hz is None:
        errors.append("active arm requires a registered payload frequency label")
    if run.arm == Arm.SHAM and run.payload_frequency_label_hz is None:
        errors.append("sham arm requires its registered payload label")
    if run.arm in (Arm.BLE_ACTIVE, Arm.SHAM) and run.measured_advertisement_rate_hz is None:
        errors.append("active and sham arms require measured advertisement cadence")

    counts = [sample.advertisement_count for sample in samples]
    if any(count < 0 for count in counts):
        errors.append("advertisement counts cannot be negative")
    if any(current < previous for previous, current in zip(counts, counts[1:], strict=False)):
        errors.append("advertisement counts must be monotonic")

    return RunValidation(not errors, tuple(errors), tuple(warnings))


def _linear_slope(x_values: Sequence[float], y_values: Sequence[float]) -> float:
    x_mean = statistics.fmean(x_values)
    y_mean = statistics.fmean(y_values)
    denominator = sum((value - x_mean) ** 2 for value in x_values)
    if denominator <= 0.0:
        raise ValueError("sample timestamps do not span a measurable interval")
    numerator = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values, strict=True)
    )
    return numerator / denominator


def derive_run_metric(run: ExperimentRun, protocol: Protocol) -> RunMetric:
    """Derive discharge power from the battery-capacity slope."""

    validation = validate_run(run, protocol)
    if not validation.valid:
        raise ValueError("invalid run: " + "; ".join(validation.errors))

    times = [sample.elapsed_s for sample in run.samples]
    capacities = [float(sample.remaining_mwh) for sample in run.samples if sample.remaining_mwh is not None]
    slope_mwh_per_second = _linear_slope(times, capacities)
    discharge_power_mw = -slope_mwh_per_second * 3600.0

    reported_rates = [
        -sample.rate_mw
        for sample in run.samples
        if sample.rate_mw is not None and math.isfinite(sample.rate_mw)
    ]
    cpu_values = [sample.cpu_percent for sample in run.samples if sample.cpu_percent is not None]
    temperature_values = [
        sample.temperature_c for sample in run.samples if sample.temperature_c is not None
    ]
    radio_fraction = statistics.fmean(
        1.0 if sample.radio_active else 0.0 for sample in run.samples
    )

    return RunMetric(
        run_id=run.run_id,
        arm=run.arm,
        duration_s=times[-1] - times[0],
        discharge_power_mw=discharge_power_mw,
        average_reported_discharge_mw=(
            statistics.fmean(reported_rates) if reported_rates else None
        ),
        average_cpu_percent=statistics.fmean(cpu_values) if cpu_values else None,
        average_temperature_c=(
            statistics.fmean(temperature_values) if temperature_values else None
        ),
        radio_active_fraction=radio_fraction,
        advertisement_count_delta=(
            run.samples[-1].advertisement_count - run.samples[0].advertisement_count
        ),
    )


_T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    25: 2.060,
    30: 2.042,
}


def _critical_t_95(degrees_of_freedom: int) -> float:
    if degrees_of_freedom in _T_CRITICAL_95:
        return _T_CRITICAL_95[degrees_of_freedom]
    lower = [key for key in _T_CRITICAL_95 if key <= degrees_of_freedom]
    if lower:
        return _T_CRITICAL_95[max(lower)]
    return 1.96


def _mean_ci95(values: Sequence[float]) -> tuple[float, tuple[float, float] | None]:
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, None
    standard_error = statistics.stdev(values) / math.sqrt(len(values))
    margin = _critical_t_95(len(values) - 1) * standard_error
    return mean, (mean - margin, mean + margin)


def analyse_experiment(runs: Iterable[ExperimentRun], protocol: Protocol) -> AnalysisResult:
    """Analyse complete randomized blocks and return one bounded decision."""

    run_list = list(runs)
    validations = {run.run_id: validate_run(run, protocol) for run in run_list}
    invalid_runs = tuple(
        run_id for run_id, validation in validations.items() if not validation.valid
    )
    valid_runs = [run for run in run_list if validations[run.run_id].valid]
    metrics = {run.run_id: derive_run_metric(run, protocol) for run in valid_runs}

    by_block: dict[int, list[ExperimentRun]] = {}
    for run in valid_runs:
        by_block.setdefault(run.block_index, []).append(run)

    block_effects: list[float] = []
    control_powers: list[float] = []
    invalid_blocks: list[int] = []
    reasons: list[str] = []

    required_arms = {Arm.BASELINE, Arm.BLE_ACTIVE}
    if protocol.require_sham:
        required_arms.add(Arm.SHAM)

    for block_index, block_runs in sorted(by_block.items()):
        arm_map = {run.arm: run for run in block_runs}
        if set(arm_map) != required_arms or len(block_runs) != len(required_arms):
            invalid_blocks.append(block_index)
            continue
        if len({run.sequence_position for run in block_runs}) != len(block_runs):
            invalid_blocks.append(block_index)
            continue
        if len({run.block_randomization_id for run in block_runs}) != 1:
            invalid_blocks.append(block_index)
            continue
        if len({run.device_id for run in block_runs}) != 1:
            invalid_blocks.append(block_index)
            continue
        if len({run.workload_hash for run in block_runs}) != 1:
            invalid_blocks.append(block_index)
            continue
        if len({run.power_mode for run in block_runs}) != 1:
            invalid_blocks.append(block_index)
            continue
        if max(run.brightness_percent for run in block_runs) - min(
            run.brightness_percent for run in block_runs
        ) > 0.5:
            invalid_blocks.append(block_index)
            continue

        active_metric = metrics[arm_map[Arm.BLE_ACTIVE].run_id]
        control_metrics = [metrics[arm_map[Arm.BASELINE].run_id]]
        if protocol.require_sham:
            control_metrics.append(metrics[arm_map[Arm.SHAM].run_id])

        cpu_values = [metric.average_cpu_percent for metric in [active_metric, *control_metrics]]
        measured_cpu_values = [float(value) for value in cpu_values if value is not None]
        if (
            len(measured_cpu_values) == len(cpu_values)
            and max(measured_cpu_values) - min(measured_cpu_values)
            > protocol.max_cpu_mean_delta_pct
        ):
            invalid_blocks.append(block_index)
            continue

        temperature_values = [
            metric.average_temperature_c for metric in [active_metric, *control_metrics]
        ]
        measured_temperatures = [value for value in temperature_values if value is not None]
        if (
            len(measured_temperatures) == len(temperature_values)
            and max(measured_temperatures) - min(measured_temperatures)
            > protocol.max_temperature_mean_delta_c
        ):
            invalid_blocks.append(block_index)
            continue

        control_power = statistics.fmean(
            metric.discharge_power_mw for metric in control_metrics
        )
        block_effects.append(control_power - active_metric.discharge_power_mw)
        control_powers.append(control_power)

    complete_blocks = len(block_effects)
    device_count = len({run.device_id for run in valid_runs})
    operator_count = len({run.operator_id for run in valid_runs})

    if invalid_runs:
        reasons.append(f"{len(invalid_runs)} run(s) failed deterministic quality gates")
    if invalid_blocks:
        reasons.append(f"{len(invalid_blocks)} block(s) failed matching or control gates")

    if run_list and not valid_runs:
        reasons.append("every supplied run failed deterministic quality gates")
        return AnalysisResult(
            decision=Decision.INVALID,
            evidence_grade=EvidenceGrade.EXPLORATORY,
            complete_blocks=0,
            invalid_runs=invalid_runs,
            invalid_blocks=tuple(invalid_blocks),
            effect_mw=None,
            effect_ci95_mw=None,
            relative_effect_pct=None,
            device_count=0,
            operator_count=0,
            causal_claim_allowed=False,
            reasons=tuple(reasons),
        )

    if complete_blocks < protocol.minimum_complete_blocks:
        reasons.append(
            f"{complete_blocks} complete block(s); {protocol.minimum_complete_blocks} required"
        )
        return AnalysisResult(
            decision=Decision.INCONCLUSIVE,
            evidence_grade=EvidenceGrade.EXPLORATORY,
            complete_blocks=complete_blocks,
            invalid_runs=invalid_runs,
            invalid_blocks=tuple(invalid_blocks),
            effect_mw=None,
            effect_ci95_mw=None,
            relative_effect_pct=None,
            device_count=device_count,
            operator_count=operator_count,
            causal_claim_allowed=False,
            reasons=tuple(reasons),
        )

    effect_mw, ci95 = _mean_ci95(block_effects)
    mean_control_power = statistics.fmean(control_powers)
    relative_effect_pct = (
        effect_mw / mean_control_power * 100.0 if mean_control_power > 0.0 else None
    )

    replicated = (
        device_count >= protocol.minimum_devices_for_replication
        and operator_count >= protocol.minimum_independent_operators
    )
    evidence_grade = (
        EvidenceGrade.REPLICATED_MULTI_DEVICE
        if replicated
        else EvidenceGrade.CONTROLLED_SINGLE_DEVICE
    )

    decision = Decision.NO_MEASURABLE_EFFECT
    if ci95 is not None and relative_effect_pct is not None:
        if ci95[0] > 0.0 and relative_effect_pct >= protocol.practical_effect_pct:
            decision = Decision.BLE_REDUCED_DRAIN
        elif ci95[1] < 0.0 and relative_effect_pct <= -protocol.practical_effect_pct:
            decision = Decision.BLE_INCREASED_DRAIN

    causal_claim_allowed = replicated and decision in {
        Decision.BLE_REDUCED_DRAIN,
        Decision.BLE_INCREASED_DRAIN,
    }
    if not replicated:
        reasons.append("multi-device, independent-operator replication is not complete")
    if decision == Decision.NO_MEASURABLE_EFFECT:
        reasons.append("the 95% interval or practical-effect threshold does not support a directional effect")

    return AnalysisResult(
        decision=decision,
        evidence_grade=evidence_grade,
        complete_blocks=complete_blocks,
        invalid_runs=invalid_runs,
        invalid_blocks=tuple(invalid_blocks),
        effect_mw=effect_mw,
        effect_ci95_mw=ci95,
        relative_effect_pct=relative_effect_pct,
        device_count=device_count,
        operator_count=operator_count,
        causal_claim_allowed=causal_claim_allowed,
        reasons=tuple(reasons),
    )


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value must be an object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _direction(effect_pct: float, *, tolerance: float = 0.5) -> str:
    if effect_pct > tolerance:
        return "reduced_drain"
    if effect_pct < -tolerance:
        return "increased_drain"
    return "no_effect"


def _legacy_observations(payloads: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []

    zero = payloads.get("zpe_zero_observer.json")
    if zero:
        duration = float(zero["duration_s"])
        baseline_rate = abs(float(zero["baseline"]["delta"])) * 3600.0 / duration
        field_rate = abs(float(zero["field"]["delta"])) * 3600.0 / duration
        effect = (baseline_rate - field_rate) / baseline_rate * 100.0 if baseline_rate else 0.0
        observations.append(
            {
                "file": "zpe_zero_observer.json",
                "comparison": "one sequential baseline segment versus one BLE segment",
                "baseline_rate_pct_per_hour": baseline_rate,
                "treatment_rate_pct_per_hour": field_rate,
                "apparent_effect_pct": effect,
                "direction": _direction(effect),
                "limitations": [
                    "one block only",
                    "fixed baseline-then-treatment order",
                    "1 percentage-point battery resolution",
                    "no workload, thermal, or measured advertisement-cadence control",
                ],
            }
        )

    thirty = payloads.get("zpe_30min_test.json")
    if thirty:
        baseline_rate = float(thirty["baseline"]["rate_pct_hr"])
        field_rate = float(thirty["field"]["rate_pct_hr"])
        effect = (baseline_rate - field_rate) / baseline_rate * 100.0 if baseline_rate else 0.0
        observations.append(
            {
                "file": "zpe_30min_test.json",
                "comparison": "sequential 15-minute baseline and BLE segments",
                "baseline_rate_pct_per_hour": baseline_rate,
                "treatment_rate_pct_per_hour": field_rate,
                "apparent_effect_pct": effect,
                "direction": _direction(effect),
                "limitations": [
                    "negative transition intervals are present",
                    "fixed order and state-of-charge confounding",
                    "1 percentage-point battery resolution",
                ],
            }
        )

    persistent = payloads.get("zpe_persistent_bt.json")
    if persistent:
        baseline_rate = float(persistent["idle_pct_hr"])
        field_rate = float(persistent["bt_pct_hr"])
        effect = (baseline_rate - field_rate) / baseline_rate * 100.0 if baseline_rate else 0.0
        observations.append(
            {
                "file": "zpe_persistent_bt.json",
                "comparison": "three idle transition intervals versus two BLE intervals",
                "baseline_rate_pct_per_hour": baseline_rate,
                "treatment_rate_pct_per_hour": field_rate,
                "apparent_effect_pct": effect,
                "direction": _direction(effect),
                "limitations": ["n=3 versus n=2", "not randomized", "percent-transition timing only"],
            }
        )

    coupling = payloads.get("zpe_coupling_test.json")
    if coupling:
        idle_interval = float(coupling["idle_drop_s"])
        field_interval = float(coupling["bt_drop_s"])
        effect = (1.0 - idle_interval / field_interval) * 100.0 if field_interval else 0.0
        observations.append(
            {
                "file": "zpe_coupling_test.json",
                "comparison": "one idle percent-drop interval versus one BLE interval",
                "apparent_effect_pct": effect,
                "direction": _direction(effect),
                "limitations": ["one transition per arm", "not randomized", "no load controls"],
            }
        )

    phi = payloads.get("zpe_phi_schumann_test.json")
    if phi:
        baseline_interval = float(phi["baseline"]["avg_s"])
        field_interval = float(phi["bubble"]["avg_s"])
        effect = (1.0 - baseline_interval / field_interval) * 100.0 if field_interval else 0.0
        observations.append(
            {
                "file": "zpe_phi_schumann_test.json",
                "comparison": "two baseline intervals versus two selected treatment intervals",
                "apparent_effect_pct": effect,
                "direction": _direction(effect),
                "limitations": [
                    "n=2 per selected arm",
                    "post-hoc best-mode selection",
                    "large within-arm spread",
                    "reported pulse count is zero",
                ],
            }
        )

    discrete_pairs = {
        "zpe_bt_only_test.json": ("baseline", "bluetooth"),
        "zpe_bt_v2_test.json": ("baseline", "bt_field"),
        "zpe_bt_transmit.json": ("baseline", "transmit"),
        "zpe_surround_v2.json": ("baseline", "surround"),
    }
    for filename, (baseline_key, field_key) in discrete_pairs.items():
        payload = payloads.get(filename)
        if not payload:
            continue
        baseline_delta = float(payload[baseline_key].get("delta", payload[baseline_key].get("d", 0)))
        field_delta = float(payload[field_key].get("delta", payload[field_key].get("d", 0)))
        if field_delta < baseline_delta:
            direction = "increased_drain"
        elif field_delta > baseline_delta:
            direction = "reduced_drain"
        else:
            direction = "no_effect"
        observations.append(
            {
                "file": filename,
                "comparison": "single coarse-percent baseline and treatment pair",
                "baseline_delta_percent": baseline_delta,
                "treatment_delta_percent": field_delta,
                "apparent_effect_pct": None,
                "direction": direction,
                "limitations": ["single pair", "coarse percentage endpoint", "not randomized"],
            }
        )

    return observations


def audit_legacy_directory(directory: Path) -> dict[str, Any]:
    """Read legacy JSON evidence and classify it without changing source files."""

    payloads: dict[str, Mapping[str, Any]] = {}
    files: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payloads[path.name] = _load_json(path)
            files.append(
                {
                    "file": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
        except Exception as exc:  # noqa: BLE001 - an audit records malformed evidence
            parse_errors.append({"file": path.name, "error": str(exc)})

    observations = _legacy_observations(payloads)
    counts = {
        direction: sum(1 for item in observations if item["direction"] == direction)
        for direction in ("reduced_drain", "increased_drain", "no_effect")
    }
    counts["not_interpretable"] = max(0, len(files) - len(observations))

    return {
        "schema_version": LEGACY_AUDIT_VERSION,
        "source_directory": str(directory.resolve()),
        "legacy_file_count": len(files),
        "parse_errors": parse_errors,
        "files": files,
        "observations": observations,
        "direction_counts": counts,
        "current_decision": Decision.INCONCLUSIVE.value,
        "evidence_grade": EvidenceGrade.EXPLORATORY.value,
        "causal_claim_allowed": False,
        "claim_boundary": (
            "The current files contain mixed exploratory observations. They do not establish "
            "that BLE reduces battery drain, extracts energy, or produces a zero-point effect."
        ),
        "blocking_findings": [
            "treatment directions conflict across legacy comparisons",
            "most endpoints are quantized whole-battery percentages",
            "treatment order was not randomized or counterbalanced",
            "no matched sham arm is recorded",
            "CPU load, brightness, power mode, temperature, and state-of-charge are not jointly controlled",
            "the encoded payload label is not a measurement of physical radio cadence or RF power",
            "multi-device independent replication is absent",
        ],
        "required_next_step": (
            "Run the pre-registered randomized baseline/BLE/sham block protocol and analyse only "
            "high-resolution mWh telemetry that passes the deterministic quality gates."
        ),
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write an auditable JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-dir", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--protocol-output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260719)
    args = parser.parse_args(argv)

    audit = audit_legacy_directory(args.legacy_dir)
    protocol = Protocol()
    manifest = protocol_manifest(protocol, seed=args.seed)
    write_json(args.audit_output, audit)
    write_json(args.protocol_output, manifest)
    print(
        json.dumps(
            {
                "audit_output": str(args.audit_output.resolve()),
                "protocol_output": str(args.protocol_output.resolve()),
                "current_decision": audit["current_decision"],
                "causal_claim_allowed": audit["causal_claim_allowed"],
                "legacy_file_count": audit["legacy_file_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
