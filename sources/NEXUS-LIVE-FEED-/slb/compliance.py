"""Balance functional and compliance checks for the Source Law of Balance."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Sequence


@dataclass(frozen=True)
class BalanceWeights:
    """Weights applied to the Balance functional.

    The default values follow the Quadrinity ordering ``Planet ≥ People ≥ Progress ≫ Profit``
    with additional coefficients for dissonance and coherence.  All weights must be
    non-negative.
    """

    planet: float = 1.0
    people: float = 0.8
    progress: float = 0.6
    profit: float = 0.0
    dissonance: float = 0.7
    coherence: float = 0.5

    def __post_init__(self) -> None:  # pragma: no cover - dataclass hook
        if min(self.planet, self.people, self.progress, self.profit, self.dissonance, self.coherence) < 0:
            raise ValueError("weights must be non-negative")
        if not (self.planet >= self.people >= self.progress):
            raise ValueError("weights must satisfy planet ≥ people ≥ progress")
        if not (self.progress >= self.profit):
            raise ValueError("progress weight must be ≥ profit weight")


@dataclass(frozen=True)
class BalanceMeasurement:
    """Normalized benefits and signals used to evaluate the Balance functional."""

    planet: float
    people: float
    progress: float
    profit: float
    coherence: float
    dissonance: float

    def clamped(self) -> "BalanceMeasurement":
        """Return a copy with all values constrained to ``[0, 1]``."""

        return BalanceMeasurement(
            *(max(0.0, min(1.0, value)) for value in (
                self.planet,
                self.people,
                self.progress,
                self.profit,
                self.coherence,
                self.dissonance,
            ))
        )


def compute_balance(measurement: BalanceMeasurement, weights: BalanceWeights) -> float:
    """Compute the Balance functional ``B(t)``.

    The implementation mirrors the red-line equation provided by the SLB council:

    ``B(t) = Σ w_i (1 - V_i)^2 + w_D D^2 - w_Λ Λ``.
    """

    normalized = measurement.clamped()
    vp = normalized.planet
    vh = normalized.people
    vg = normalized.progress
    vpi = normalized.profit
    lam = normalized.coherence
    diss = normalized.dissonance

    return (
        weights.planet * (1.0 - vp) ** 2
        + weights.people * (1.0 - vh) ** 2
        + weights.progress * (1.0 - vg) ** 2
        + weights.profit * (1.0 - vpi) ** 2
        + weights.dissonance * (diss ** 2)
        - weights.coherence * lam
    )


@dataclass(frozen=True)
class BalanceSnapshot:
    """Immutable record of a Balance evaluation."""

    timestamp: float
    measurement: BalanceMeasurement
    balance: float


@dataclass
class BalanceStatus:
    """Result of registering a measurement with the controller."""

    snapshot: BalanceSnapshot
    is_safe: bool
    average_derivative: float
    violations: List[str] = field(default_factory=list)

    @property
    def requires_halt(self) -> bool:
        return bool(self.violations)


class BalanceController:
    """Streaming guard that enforces the Lyapunov-style Balance requirement."""

    def __init__(
        self,
        *,
        weights: BalanceWeights | None = None,
        safe_threshold: float = 3.0,
        trend_window_seconds: float = 24 * 3600.0,
        supply_window_seconds: float = 30 * 24 * 3600.0,
        planet_floor: float = 0.2,
        coherence_spike: float = 0.05,
        epsilon: float = 1e-3,
    ) -> None:
        self.weights = weights or BalanceWeights()
        self.safe_threshold = safe_threshold
        self.trend_window_seconds = trend_window_seconds
        self.supply_window_seconds = max(supply_window_seconds, trend_window_seconds)
        self.planet_floor = planet_floor
        self.coherence_spike = coherence_spike
        self.epsilon = epsilon
        self._history: Deque[BalanceSnapshot] = deque()

    def register(self, measurement: BalanceMeasurement, *, timestamp: float) -> BalanceStatus:
        """Record a new measurement and evaluate compliance conditions."""

        balance_value = compute_balance(measurement, self.weights)
        snapshot = BalanceSnapshot(timestamp=timestamp, measurement=measurement, balance=balance_value)
        self._history.append(snapshot)

        # prune history beyond supply window
        lower_bound = timestamp - self.supply_window_seconds
        while self._history and self._history[0].timestamp < lower_bound:
            self._history.popleft()

        violations: List[str] = []
        average_derivative = self._average_derivative(self.trend_window_seconds)

        if balance_value > self.safe_threshold:
            violations.append("balance above safe threshold")
        if average_derivative is not None and average_derivative > self.epsilon:
            violations.append("balance trending upward (⟨B˙⟩ > 0)")
        if measurement.planet < self.planet_floor:
            violations.append("planetary floor breached")

        previous = self._history[-2] if len(self._history) >= 2 else None
        if previous is not None:
            coherence_delta = measurement.coherence - previous.measurement.coherence
            if coherence_delta > self.coherence_spike:
                if (
                    measurement.planet + self.epsilon < previous.measurement.planet
                    and measurement.people + self.epsilon < previous.measurement.people
                ):
                    violations.append("false coherence spike detected")

        status = BalanceStatus(
            snapshot=snapshot,
            is_safe=not violations,
            average_derivative=average_derivative or 0.0,
            violations=violations,
        )
        return status

    def _average_derivative(self, window_seconds: float) -> float | None:
        """Compute the average derivative over ``window_seconds`` if possible."""

        if not self._history:
            return None
        latest = self._history[-1]
        cutoff = latest.timestamp - window_seconds
        start_snapshot = None
        for entry in self._history:
            if entry.timestamp >= cutoff:
                start_snapshot = entry
                break
        if start_snapshot is None or start_snapshot.timestamp == latest.timestamp:
            return 0.0
        return (latest.balance - start_snapshot.balance) / (latest.timestamp - start_snapshot.timestamp)

    def supply_brake_active(self) -> bool:
        """Return ``True`` when the 30-day trend is non-negative."""

        derivative = self._average_derivative(self.supply_window_seconds)
        if derivative is None:
            return False
        return derivative >= 0.0

    def last_snapshot(self) -> BalanceSnapshot | None:
        return self._history[-1] if self._history else None

    def second_last_snapshot(self) -> BalanceSnapshot | None:
        return self._history[-2] if len(self._history) >= 2 else None


def should_mint(
    previous: BalanceSnapshot,
    current: BalanceSnapshot,
    *,
    epsilon: float = 1e-3,
) -> bool:
    """Return ``True`` when the issuance guard rails are satisfied."""

    if current.balance >= previous.balance:
        return False

    prev_meas = previous.measurement
    curr_meas = current.measurement

    return (
        curr_meas.planet >= prev_meas.planet + epsilon
        and curr_meas.people >= prev_meas.people + epsilon
        and curr_meas.progress >= prev_meas.progress + epsilon
    )


def compute_gini(values: Sequence[float]) -> float:
    """Compute the Gini coefficient for ``values``.

    Zero values are allowed; negative values raise ``ValueError``.
    """

    if not values:
        raise ValueError("values must not be empty")
    if any(value < 0 for value in values):
        raise ValueError("values must be non-negative")
    sorted_values = sorted(values)
    n = len(sorted_values)
    cumulative = 0.0
    weighted_sum = 0.0
    for index, value in enumerate(sorted_values, start=1):
        cumulative += value
        weighted_sum += index * value
    if cumulative == 0:
        return 0.0
    return (2 * weighted_sum) / (n * cumulative) - (n + 1) / n


def governance_is_within_bounds(values: Sequence[float], *, gini_max: float) -> bool:
    """Return ``True`` when holdings respect the configured Gini ceiling."""

    return compute_gini(values) < gini_max


def check_autonomy_guard(*, can_reduce_agency: bool, has_zero_coercion_alternative: bool) -> bool:
    """Validate the non-domination autonomy guard condition."""

    if not can_reduce_agency:
        return True
    return has_zero_coercion_alternative


def detect_false_signal(previous: BalanceSnapshot, current: BalanceSnapshot, *, spike: float, epsilon: float) -> bool:
    """Utility used by tests to expose the false-signal guard logic."""

    coherence_delta = current.measurement.coherence - previous.measurement.coherence
    if coherence_delta <= spike:
        return False
    return (
        current.measurement.planet + epsilon < previous.measurement.planet
        and current.measurement.people + epsilon < previous.measurement.people
    )
