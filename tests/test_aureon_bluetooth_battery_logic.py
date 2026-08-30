from __future__ import annotations

from pathlib import Path

import pytest

from aureon.monitors.aureon_bluetooth_battery_logic import (
    Arm,
    BatterySample,
    Decision,
    EvidenceGrade,
    ExperimentController,
    ExperimentRun,
    Protocol,
    Stage,
    analyse_experiment,
    audit_legacy_directory,
    derive_run_metric,
    generate_block_schedule,
    protocol_manifest,
    validate_run,
)


def _protocol(**overrides):
    values = {
        "segment_duration_s": 60.0,
        "minimum_samples_per_run": 3,
        "minimum_complete_blocks": 3,
        "minimum_devices_for_replication": 1,
        "minimum_independent_operators": 1,
        "require_blinded_analysis": True,
        "require_cpu_telemetry": True,
    }
    values.update(overrides)
    return Protocol(**values)


def _run(
    arm: Arm,
    block: int,
    power_mw: float,
    *,
    sequence: int,
    randomization_id: str | None = None,
    ac_online: bool = False,
    device_id: str = "device-a",
    operator_id: str = "operator-a",
    cpu_percent: float = 20.0,
) -> ExperimentRun:
    start_mwh = 20_000.0
    samples = []
    for elapsed_s in (0.0, 30.0, 60.0):
        remaining = start_mwh - power_mw * elapsed_s / 3600.0
        samples.append(
            BatterySample(
                elapsed_s=elapsed_s,
                remaining_mwh=remaining,
                rate_mw=-power_mw,
                percent=remaining / 400.0,
                ac_online=ac_online,
                cpu_percent=cpu_percent,
                temperature_c=35.0,
                radio_active=arm != Arm.BASELINE,
                advertisement_count=(int(elapsed_s * 2) if arm != Arm.BASELINE else 0),
            )
        )
    return ExperimentRun(
        run_id=f"block-{block}-{arm.value}",
        protocol_id="AUREON-BLE-BATTERY-RCT-V1",
        arm=arm,
        block_index=block,
        sequence_position=sequence,
        samples=tuple(samples),
        device_id=device_id,
        operator_id=operator_id,
        workload_hash="sha256:workload",
        power_mode="balanced",
        brightness_percent=50.0,
        block_randomization_id=randomization_id or f"random-{block}",
        analyst_blinded=True,
        payload_frequency_label_hz=(12.669 if arm == Arm.BLE_ACTIVE else 17.0 if arm == Arm.SHAM else None),
        measured_advertisement_rate_hz=(2.0 if arm != Arm.BASELINE else None),
    )


def _blocks(active_power_mw: float, *, blocks: int = 3):
    runs = []
    for block in range(1, blocks + 1):
        runs.extend(
            [
                _run(Arm.BASELINE, block, 1000.0, sequence=1),
                _run(Arm.BLE_ACTIVE, block, active_power_mw, sequence=2),
                _run(Arm.SHAM, block, 1000.0, sequence=3),
            ]
        )
    return runs


def test_state_machine_accepts_only_declared_transitions():
    controller = ExperimentController()
    assert controller.transition("register") == Stage.PREFLIGHT
    assert controller.transition("preflight_passed") == Stage.WARMUP
    assert controller.transition("warmup_complete") == Stage.MEASURING
    assert controller.transition("measurement_complete") == Stage.COMPLETE
    assert controller.transition("analysis_complete") == Stage.ANALYSED
    assert len(controller.history) == 5


def test_state_machine_rejects_skipped_stage():
    controller = ExperimentController()
    with pytest.raises(ValueError, match="not allowed"):
        controller.transition("measurement_complete")


def test_schedule_is_deterministic_and_balanced():
    first = generate_block_schedule(4, 42, include_sham=True)
    second = generate_block_schedule(4, 42, include_sham=True)
    assert first == second
    for block in range(1, 5):
        arms = {item["arm"] for item in first if item["block_index"] == block}
        assert arms == {"baseline", "ble_active", "sham"}


def test_protocol_manifest_hashes_seed_and_records_claim_boundary():
    manifest = protocol_manifest(_protocol(), seed=42, blocks=2)
    assert manifest["schema_version"] == "aureon-bluetooth-battery-experiment-v1"
    assert manifest["randomization"]["seed_sha256"] != "42"
    assert len(manifest["randomization"]["schedule"]) == 6
    assert "not proof" in manifest["claim_boundary"]


def test_valid_run_derives_capacity_slope_power():
    protocol = _protocol()
    run = _run(Arm.BLE_ACTIVE, 1, 850.0, sequence=2)
    validation = validate_run(run, protocol)
    metric = derive_run_metric(run, protocol)
    assert validation.valid is True
    assert metric.discharge_power_mw == pytest.approx(850.0)
    assert metric.average_reported_discharge_mw == pytest.approx(850.0)


def test_ac_power_invalidates_run():
    validation = validate_run(
        _run(Arm.BASELINE, 1, 1000.0, sequence=1, ac_online=True),
        _protocol(),
    )
    assert validation.valid is False
    assert any("AC power" in error for error in validation.errors)


def test_active_run_requires_measured_advertisement_cadence():
    run = _run(Arm.BLE_ACTIVE, 1, 850.0, sequence=2)
    run = ExperimentRun(**{**run.__dict__, "measured_advertisement_rate_hz": None})
    validation = validate_run(run, _protocol())
    assert validation.valid is False
    assert any("advertisement cadence" in error for error in validation.errors)


def test_incomplete_experiment_is_inconclusive():
    result = analyse_experiment(_blocks(800.0, blocks=2), _protocol(minimum_complete_blocks=3))
    assert result.decision == Decision.INCONCLUSIVE
    assert result.evidence_grade == EvidenceGrade.EXPLORATORY
    assert result.causal_claim_allowed is False


def test_all_invalid_runs_produce_invalid_decision():
    invalid = _run(Arm.BASELINE, 1, 1000.0, sequence=1, ac_online=True)
    result = analyse_experiment([invalid], _protocol())
    assert result.decision == Decision.INVALID
    assert result.invalid_runs == (invalid.run_id,)
    assert result.causal_claim_allowed is False


def test_controlled_blocks_can_detect_reduced_drain():
    result = analyse_experiment(_blocks(800.0), _protocol())
    assert result.decision == Decision.BLE_REDUCED_DRAIN
    assert result.effect_mw == pytest.approx(200.0)
    assert result.relative_effect_pct == pytest.approx(20.0)
    assert result.causal_claim_allowed is True


def test_single_device_directional_result_is_not_a_replicated_causal_claim():
    result = analyse_experiment(
        _blocks(800.0),
        _protocol(minimum_devices_for_replication=3, minimum_independent_operators=2),
    )
    assert result.decision == Decision.BLE_REDUCED_DRAIN
    assert result.evidence_grade == EvidenceGrade.CONTROLLED_SINGLE_DEVICE
    assert result.causal_claim_allowed is False


def test_controlled_blocks_can_detect_increased_drain():
    result = analyse_experiment(_blocks(1200.0), _protocol())
    assert result.decision == Decision.BLE_INCREASED_DRAIN
    assert result.relative_effect_pct == pytest.approx(-20.0)


def test_controlled_blocks_return_no_effect_inside_threshold():
    result = analyse_experiment(_blocks(980.0), _protocol(practical_effect_pct=5.0))
    assert result.decision == Decision.NO_MEASURABLE_EFFECT
    assert result.causal_claim_allowed is False


def test_cpu_mismatch_invalidates_block():
    runs = _blocks(800.0)
    changed = []
    for run in runs:
        if run.block_index == 1 and run.arm == Arm.BLE_ACTIVE:
            changed.append(_run(Arm.BLE_ACTIVE, 1, 800.0, sequence=2, cpu_percent=40.0))
        else:
            changed.append(run)
    result = analyse_experiment(changed, _protocol())
    assert 1 in result.invalid_blocks
    assert result.decision == Decision.INCONCLUSIVE


def test_legacy_repo_evidence_is_classified_as_mixed_and_inconclusive():
    legacy_dir = Path(__file__).resolve().parents[1] / "data" / "experiments" / "zpe"
    audit = audit_legacy_directory(legacy_dir)
    assert audit["legacy_file_count"] >= 19
    assert audit["current_decision"] == "inconclusive"
    assert audit["causal_claim_allowed"] is False
    assert audit["direction_counts"]["reduced_drain"] >= 1
    assert audit["direction_counts"]["increased_drain"] >= 1
    thirty = next(item for item in audit["observations"] if item["file"] == "zpe_30min_test.json")
    assert thirty["direction"] == "increased_drain"
