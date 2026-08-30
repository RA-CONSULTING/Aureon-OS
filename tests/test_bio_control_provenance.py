"""Offline contract tests for generated bio/statistical controls."""

from __future__ import annotations

import numpy as np
import pytest

from aureon.bio import authenticity_discriminator as authenticity
from aureon.bio import calibration_curve
from aureon.bio import false_discovery
from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import null_calibration
from aureon.bio import power_analysis
from aureon.bio import proxy_suite


def _assert_control(payload: dict) -> None:
    assert payload["data_origin"] == "derived_statistical_control"
    assert payload["truth_status"] == "statistical_control"
    assert payload["control_only"] is True
    assert payload["live_data"] is False
    assert payload["provider_observation"] is False
    assert payload["operational_eligible"] is False
    assert payload["actionable"] is False
    assert payload["accounting_eligible"] is False


def _proxy_result(*, control_only: bool = True) -> proxy.ProxyResult:
    return proxy.ProxyResult(
        valid=True,
        structure_present=True,
        test_A_p=0.01,
        test_B_p=0.01,
        n_tones=6,
        controls={},
        provenance="declared statistical control; no human subject",
        consent=True,
        modality="statistical_control",
        label="control",
        control_only=control_only,
    )


def _reports() -> list[tuple[object, object]]:
    auth_child = authenticity.ClassOutcome(
        name="control",
        description="declared control",
        structural_rate=1.0,
        provenance_rate=1.0,
        authentic_rate=1.0,
        is_surface_imitation=False,
        is_clone=False,
    )
    auth_report = authenticity.AuthenticityReport(
        classes=[auth_child],
        n_classes=1,
        trials=1,
        nulls=1,
        alpha=0.05,
        jitter_hz=0.0,
        authentic_rate=1.0,
        max_surface_imitation_rate=0.0,
        clone_structural_rate=0.0,
        clone_authentic_rate=0.0,
        clone_blocked_by_provenance=True,
        separation=1.0,
    )

    null_child = null_calibration.AdapterCalibration(
        adapter="control",
        modality="statistical_control",
        trials=1,
        false_positives=0,
        fpr=0.0,
        bound=0.05,
        structured_fires=True,
        conforms=True,
    )
    null_report = null_calibration.CalibrationReport(
        readings=[null_child],
        n_adapters=1,
        n_conforming=1,
        trials=1,
        nulls=1,
        alpha=0.05,
        nominal_fpr=0.0025,
    )

    suite_child = proxy_suite.AdapterReading(
        adapter="control",
        modality="statistical_control",
        present_valid=True,
        present_structure=True,
        present_A_p=0.01,
        present_B_p=0.01,
        absent_valid=True,
        absent_structure=False,
        control_provenance_valid=True,
        conforms=True,
    )
    suite_report = proxy_suite.SuiteReport(
        readings=[suite_child],
        n_adapters=1,
        n_conforming=1,
    )

    fdr_child = false_discovery.MethodOutcome(
        name="benjamini_hochberg",
        fdr=0.01,
        power=0.8,
        mean_rejections=1.0,
        controls_fdr=True,
    )
    fdr_report = false_discovery.FalseDiscoveryReport(
        methods=[fdr_child],
        n_methods=1,
        trials=1,
        nulls=1,
        m_lanes=2,
        m_null=1,
        m_signal=1,
        jitter_lo=0.0,
        jitter_hi=1.0,
        q=0.05,
        alpha=0.05,
        tolerance=0.03,
        bh_controls_fdr=True,
        bh_dominates_bonferroni=True,
    )

    curve_child = calibration_curve.CurvePoint(
        alpha=0.05,
        rate_A=0.05,
        rate_B=0.05,
        rate_joint=0.01,
        joint_conservative=True,
        test_A_conservative=True,
    )
    curve_report = calibration_curve.CalibrationCurveReport(
        points=[curve_child],
        n_points=1,
        trials=1,
        nulls=1,
        tolerance=0.02,
        joint_conservative=True,
        test_A_conservative=True,
        max_joint_exceedance=0.0,
    )

    power_child = power_analysis.PowerLevel(
        jitter_hz=0.0,
        trials=1,
        detections=1,
        power=1.0,
    )
    power_report = power_analysis.PowerReport(
        levels=[power_child],
        n_levels=1,
        trials=1,
        nulls=1,
        alpha=0.05,
        clean_power=1.0,
        degraded_power=1.0,
    )
    return [
        (auth_child, auth_report),
        (null_child, null_report),
        (suite_child, suite_report),
        (fdr_child, fdr_report),
        (curve_child, curve_report),
        (power_child, power_report),
    ]


def test_every_control_report_and_child_is_explicitly_non_operational() -> None:
    _assert_control(_proxy_result().to_dict())
    for child, report in _reports():
        _assert_control(child.to_dict())
        _assert_control(report.to_dict())


def test_observed_input_analysis_is_still_not_action_or_accounting_data() -> None:
    payload = _proxy_result(control_only=False).to_dict()
    assert payload["data_origin"] == "derived_signal_analysis"
    assert payload["truth_status"] == "derived_analysis"
    assert payload["control_only"] is False
    assert payload["live_data"] is None
    assert payload["provider_observation"] is False
    assert payload["operational_eligible"] is False
    assert payload["actionable"] is False
    assert payload["accounting_eligible"] is False


def test_runtime_authenticity_has_no_test_key_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(authenticity.PROVENANCE_KEY_ENV, raising=False)
    tones = np.array([1100.0, 1104.0, 1779.0, 1783.0])
    control_token = authenticity.provenance_token(tones, key=authenticity._TEST_KEY)
    result = authenticity.discriminate(tones, token=control_token, nulls=8, seed=0)
    assert result["input_valid"] is True
    assert result["provenance_valid"] is False
    assert result["authentic"] is False
    assert result["reason"] == "runtime provenance key unavailable"
    assert result["operational_eligible"] is False


def test_malformed_authenticity_input_returns_no_fabricated_p_values() -> None:
    result = authenticity.discriminate(
        np.array([np.nan]),
        token="not-a-receipt",
        key="runtime-key",
        nulls=8,
    )
    assert result["input_valid"] is False
    assert result["p_A"] is None
    assert result["p_B"] is None
    assert result["authentic"] is False

    non_numeric = authenticity.discriminate(
        ["not-a-tone"],
        token="not-a-receipt",
        key="runtime-key",
        nulls=None,
    )
    assert non_numeric["input_valid"] is False
    assert non_numeric["p_A"] is None
    assert non_numeric["p_B"] is None


def test_control_emitters_never_resolve_the_process_global_bus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aureon.core import aureon_thought_bus

    def _forbidden_global_bus():
        raise AssertionError("generated controls must not resolve the process-global bus")

    monkeypatch.setattr(aureon_thought_bus, "get_thought_bus", _forbidden_global_bus)
    proxy.emit_proxy_result(_proxy_result(), bus=None, trace=False)
    reports = [report for _, report in _reports()]
    authenticity.emit_authenticity(reports[0], bus=None, trace=False)
    null_calibration.emit_calibration(reports[1], bus=None, trace=False)
    proxy_suite.emit_suite(reports[2], bus=None, trace=False)
    false_discovery.emit_false_discovery(reports[3], bus=None, trace=False)
    calibration_curve.emit_curve(reports[4], bus=None, trace=False)
    power_analysis.emit_power(reports[5], bus=None, trace=False)


def test_explicit_control_bus_receives_only_labeled_payloads() -> None:
    class _Bus:
        def __init__(self) -> None:
            self.thoughts = []

        def publish(self, thought) -> None:
            self.thoughts.append(thought)

    calls = [
        lambda bus: proxy.emit_proxy_result(_proxy_result(), bus=bus, trace=False),
    ]
    reports = [report for _, report in _reports()]
    calls.extend(
        [
            lambda bus: authenticity.emit_authenticity(reports[0], bus=bus, trace=False),
            lambda bus: null_calibration.emit_calibration(reports[1], bus=bus, trace=False),
            lambda bus: proxy_suite.emit_suite(reports[2], bus=bus, trace=False),
            lambda bus: false_discovery.emit_false_discovery(reports[3], bus=bus, trace=False),
            lambda bus: calibration_curve.emit_curve(reports[4], bus=bus, trace=False),
            lambda bus: power_analysis.emit_power(reports[5], bus=bus, trace=False),
        ]
    )
    for call in calls:
        bus = _Bus()
        returned = call(bus)
        assert len(bus.thoughts) == 1
        assert bus.thoughts[0].topic.startswith("bio.control.")
        _assert_control(bus.thoughts[0].payload)
        _assert_control(returned)


@pytest.mark.parametrize(
    ("fn", "kwargs"),
    [
        (null_calibration.calibrate_nulls, {"trials": 0}),
        (calibration_curve.compute_calibration, {"trials": 0}),
        (false_discovery.compute_false_discovery, {"m_signal": 0}),
        (power_analysis.detection_power, {"jitter_levels": ()}),
        (authenticity.compute_authenticity, {"trials": 0}),
    ],
)
def test_empty_control_experiments_fail_instead_of_manufacturing_zeroes(fn, kwargs) -> None:
    with pytest.raises(ValueError):
        fn(**kwargs)
