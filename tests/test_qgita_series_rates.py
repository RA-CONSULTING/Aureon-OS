"""The planted-impulse harness is test-only and stays out of market rates."""

from __future__ import annotations

from aureon.evidence.qgita import FALSE_ALARM_TAIL


def _assert_synthetic_planted(report: dict) -> None:
    assert report["tag"] == "synthetic_planted"
    assert report["role"] == "synthetic_planted"
    assert report["counts_as_market_rate"] is False
    assert report["counts_as_telemetry"] is False
    assert report["rates_verdict"] == "synthetic_planted"
    assert report["orders_placed"] is False
    assert report.get("evidence_tag") != "measured"
    assert "not a measured market rate" in report["label"].casefold()
    nested = report.get("signal_in_noise")
    if isinstance(nested, dict):
        assert nested["tag"] == "synthetic_planted"
        assert nested["verdict"] == "synthetic_planted"
        assert nested["counts_as_market_rate"] is False


def test_short_series_is_a_test_only_hold() -> None:
    from aureon.evaluation.qgita_series_rates import measure_signal_in_noise

    report = measure_signal_in_noise([float(index) for index in range(12)])
    _assert_synthetic_planted(report)
    assert report["harness_status"] == "not_scored"
    assert report["detection_rate"] is None
    assert report["false_alarm_rate"] is None
    assert "not built" in report["rates_reason"]


def test_flat_series_is_a_test_only_hold() -> None:
    from aureon.evaluation.qgita_series_rates import measure_signal_in_noise

    report = measure_signal_in_noise([3.0] * 40)
    _assert_synthetic_planted(report)
    assert report["harness_status"] == "not_scored"
    assert "variance" in report["rates_reason"]


def test_planted_impulses_stay_inside_the_test_harness() -> None:
    from aureon.evaluation.qgita_series_rates import measure_signal_in_noise, rate_phrase

    values = [float(index) + ((index * 17) % 5) * 0.01 for index in range(40)]
    report = measure_signal_in_noise(values)
    assert report == measure_signal_in_noise(values)
    _assert_synthetic_planted(report)
    assert report["harness_status"] == "scored"
    block = report["signal_in_noise"]
    assert block["tag"] == "synthetic_planted"
    assert block["verdict"] == "synthetic_planted"
    assert block["orders_placed"] is False
    assert block["labels"].startswith("planted one-sample impulse")
    assert block["calibration"]["tail"] == FALSE_ALARM_TAIL
    assert block["seeds"]["seeds_disjoint"] is True
    calibration = set(block["calibration_shifts"])
    held_out = set(block["evaluation_shifts"])
    assert calibration.isdisjoint(held_out)
    assert calibration | held_out == set(range(len(values)))
    headline = block["headline"]
    assert report["detection_rate"] == headline["detection_rate"]
    assert report["false_alarm_rate"] == headline["false_alarm_rate"]
    assert 0.0 <= report["detection_rate"] <= 1.0
    assert 0.0 <= report["false_alarm_rate"] <= 1.0
    detection_low, detection_high = report["detection_rate_ci95"]
    false_alarm_low, false_alarm_high = report["false_alarm_ci95"]
    assert detection_low <= report["detection_rate"] <= detection_high
    assert false_alarm_low <= report["false_alarm_rate"] <= false_alarm_high
    cell = next(
        item
        for item in block["cells"]
        if item["placement"] == headline["placement"] and item["snr_db"] == headline["snr_db"]
    )
    assert cell["ftcp"]["recall"] == report["detection_rate"]
    assert cell["ftcp"]["false_alarm_rate"] == report["false_alarm_rate"]
    phrase = rate_phrase(report)
    assert "synthetic_planted" in phrase
    assert "not a measured market rate" in phrase.casefold()
    assert "95%" not in phrase
    assert "**measured**" not in phrase.casefold()


def test_market_record_does_not_receive_the_harness() -> None:
    from pathlib import Path

    from aureon.evaluation.brain_proof import _market_qgita
    from aureon.evaluation.market_series import load_market_series
    from aureon.evaluation.qgita_series_rates import measure_signal_in_noise

    root = Path(__file__).resolve().parents[1]
    pack = load_market_series(root)
    market = _market_qgita(pack)
    assert market["rates_verdict"] == "HOLD"
    assert market["verdict"] == "measured_rates_hold"
    assert market["detection_rate"] is None
    assert market["false_alarm_rate"] is None
    assert "signal_in_noise" not in market
    assert "lighthouse_detection_rate" not in market
    assert market["rates_receipt"]["planted_rates_copied"] is False
    assert market["rates_receipt"]["rates_count_as_market_rate"] is False
    assert "exogenous signal-present versus noise-only labels" in market["rates_receipt"]["missing_ingredient"]
    closes = [float(bar["close"]) for bar in pack["bars"]]
    harness = measure_signal_in_noise(closes)
    _assert_synthetic_planted(harness)
    assert market.get("tag") != "synthetic_planted"
    assert market["evidence_tag"] == "measured"
    assert market["rates_verdict"] == "HOLD"
    assert harness["harness_status"] == "scored"
    assert isinstance(harness["detection_rate"], float)
    assert market["detection_rate"] != harness["detection_rate"]
    assert market["false_alarm_rate"] != harness["false_alarm_rate"]
