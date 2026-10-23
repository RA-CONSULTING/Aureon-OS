import pytest

from slb.compliance import (
    BalanceController,
    BalanceMeasurement,
    BalanceSnapshot,
    BalanceWeights,
    check_autonomy_guard,
    compute_balance,
    compute_gini,
    detect_false_signal,
    should_mint,
)


@pytest.fixture
def default_weights():
    return BalanceWeights(planet=1.0, people=0.8, progress=0.6, profit=0.2, dissonance=0.7, coherence=0.5)


def test_compute_balance_matches_manual(default_weights):
    measurement = BalanceMeasurement(
        planet=0.92,
        people=0.88,
        progress=0.86,
        profit=0.55,
        coherence=0.61,
        dissonance=0.12,
    )
    expected = (
        default_weights.planet * (1 - measurement.planet) ** 2
        + default_weights.people * (1 - measurement.people) ** 2
        + default_weights.progress * (1 - measurement.progress) ** 2
        + default_weights.profit * (1 - measurement.profit) ** 2
        + default_weights.dissonance * measurement.dissonance**2
        - default_weights.coherence * measurement.coherence
    )
    assert compute_balance(measurement, default_weights) == pytest.approx(expected)


def test_controller_detects_threshold_and_trend(default_weights):
    controller = BalanceController(
        weights=default_weights,
        safe_threshold=0.3,
        trend_window_seconds=5.0,
        supply_window_seconds=20.0,
        planet_floor=0.2,
    )
    status1 = controller.register(
        BalanceMeasurement(planet=0.95, people=0.94, progress=0.9, profit=0.5, coherence=0.2, dissonance=0.1),
        timestamp=0.0,
    )
    assert status1.is_safe

    status2 = controller.register(
        BalanceMeasurement(planet=0.7, people=0.7, progress=0.68, profit=0.4, coherence=0.1, dissonance=0.4),
        timestamp=3.0,
    )
    assert not status2.is_safe
    assert "balance above safe threshold" in status2.violations

    controller = BalanceController(
        weights=default_weights,
        safe_threshold=10.0,
        trend_window_seconds=5.0,
        supply_window_seconds=20.0,
    )
    controller.register(
        BalanceMeasurement(planet=0.9, people=0.9, progress=0.9, profit=0.5, coherence=0.2, dissonance=0.1),
        timestamp=0.0,
    )
    status_up = controller.register(
        BalanceMeasurement(planet=0.8, people=0.8, progress=0.8, profit=0.5, coherence=0.2, dissonance=0.1),
        timestamp=4.0,
    )
    assert any("balance trending upward" in message for message in status_up.violations)


def test_planetary_floor_and_false_signal(default_weights):
    controller = BalanceController(
        weights=default_weights,
        safe_threshold=10.0,
        planet_floor=0.5,
        trend_window_seconds=5.0,
        supply_window_seconds=20.0,
        coherence_spike=0.05,
        epsilon=1e-4,
    )
    status = controller.register(
        BalanceMeasurement(planet=0.4, people=0.8, progress=0.8, profit=0.6, coherence=0.3, dissonance=0.2),
        timestamp=0.0,
    )
    assert "planetary floor breached" in status.violations

    controller.register(
        BalanceMeasurement(planet=0.8, people=0.82, progress=0.8, profit=0.6, coherence=0.3, dissonance=0.2),
        timestamp=10.0,
    )
    status_false = controller.register(
        BalanceMeasurement(planet=0.7, people=0.7, progress=0.8, profit=0.6, coherence=0.5, dissonance=0.2),
        timestamp=12.0,
    )
    assert "false coherence spike detected" in status_false.violations


def test_supply_brake_activation(default_weights):
    controller = BalanceController(
        weights=default_weights,
        safe_threshold=10.0,
        trend_window_seconds=5.0,
        supply_window_seconds=20.0,
    )
    controller.register(
        BalanceMeasurement(planet=0.9, people=0.9, progress=0.9, profit=0.6, coherence=0.2, dissonance=0.1),
        timestamp=0.0,
    )
    controller.register(
        BalanceMeasurement(planet=0.8, people=0.8, progress=0.8, profit=0.6, coherence=0.2, dissonance=0.1),
        timestamp=18.0,
    )
    assert controller.supply_brake_active()


def test_should_mint_and_false_signal_utility(default_weights):
    previous = BalanceSnapshot(
        timestamp=0.0,
        measurement=BalanceMeasurement(planet=0.8, people=0.82, progress=0.81, profit=0.4, coherence=0.4, dissonance=0.2),
        balance=compute_balance(BalanceMeasurement(planet=0.8, people=0.82, progress=0.81, profit=0.4, coherence=0.4, dissonance=0.2), default_weights),
    )
    current = BalanceSnapshot(
        timestamp=5.0,
        measurement=BalanceMeasurement(planet=0.85, people=0.86, progress=0.85, profit=0.4, coherence=0.45, dissonance=0.18),
        balance=compute_balance(BalanceMeasurement(planet=0.85, people=0.86, progress=0.85, profit=0.4, coherence=0.45, dissonance=0.18), default_weights),
    )
    assert current.balance < previous.balance
    assert should_mint(previous, current, epsilon=0.01)

    worse = BalanceSnapshot(
        timestamp=6.0,
        measurement=BalanceMeasurement(planet=0.84, people=0.85, progress=0.84, profit=0.4, coherence=0.6, dissonance=0.18),
        balance=compute_balance(BalanceMeasurement(planet=0.84, people=0.85, progress=0.84, profit=0.4, coherence=0.6, dissonance=0.18), default_weights),
    )
    assert detect_false_signal(current, worse, spike=0.05, epsilon=1e-3)
    assert not should_mint(current, worse)


def test_gini_and_autonomy_guard():
    assert compute_gini([1, 1, 1]) == pytest.approx(0.0)
    gini_high = compute_gini([0, 0, 10])
    assert gini_high == pytest.approx(0.6666666, rel=1e-6)

    with pytest.raises(ValueError):
        compute_gini([])
    with pytest.raises(ValueError):
        compute_gini([1, -1])

    assert check_autonomy_guard(can_reduce_agency=False, has_zero_coercion_alternative=False)
    assert check_autonomy_guard(can_reduce_agency=True, has_zero_coercion_alternative=True)
    assert not check_autonomy_guard(can_reduce_agency=True, has_zero_coercion_alternative=False)
