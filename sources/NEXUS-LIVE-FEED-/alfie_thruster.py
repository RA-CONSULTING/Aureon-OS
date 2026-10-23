"""ALFIE thruster control simulation utilities.

This module provides a light-weight behavioural model of the A.L.F.I.E. drive
controller described in ``docs/ALFIE_AI_ENTITY_ACTIVATION_PROTOCOL.md``.  The
goal is not to emulate the full hardware stack, but to expose deterministic
helpers that unit tests can exercise to validate safety and coherence
behaviour.

The :class:`ALFIEThrusterController` class models three mission-critical
scenarios:

* Love & Pride stabilisation requests (natural language thrust commands)
* Thermal derating when coil temperatures exceed safe limits
* Communication drop-outs while maintaining a safe thrust command

The implementation purposely keeps the maths simple yet expressive so tests
can assert on concrete numbers (thrust ripple, Γ delta, response times, etc.)
without relying on randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import statistics
import re
from typing import Dict, Iterable, List, Tuple


Vector3 = Tuple[float, float, float]


@dataclass
class CommandState:
    """Record describing the last safe thrust command."""

    vector: Vector3 = (0.0, 0.0, 0.0)
    timestamp: float = 0.0
    intent: str = "idle"
    gamma: float = 0.945


@dataclass
class ScenarioReport:
    """Generic structured report returned from controller simulations."""

    ok: bool
    details: Dict[str, float]
    notes: List[str] = field(default_factory=list)


class ALFIEThrusterController:
    """High-level behavioural model of the ALFIE thruster control system."""

    thermal_threshold_c: float = 90.0

    def __init__(self, base_gamma: float = 0.945) -> None:
        self.gamma = base_gamma
        self.clock = 0.0  # seconds
        self.current_thrust_vector: Vector3 = (0.0, 0.0, 0.0)
        self.last_safe_command = CommandState(vector=self.current_thrust_vector, gamma=self.gamma)
        self._log: List[str] = []

    # ------------------------------------------------------------------
    # Public utilities
    # ------------------------------------------------------------------
    def execute_prompt(self, prompt: str, compiler_intent: str, duration: float = 1.0, dt: float = 0.01) -> ScenarioReport:
        """Simulate processing a natural-language thrust request.

        Parameters
        ----------
        prompt:
            Natural language instruction (e.g. "Maintain 500N vertical thrust").
        compiler_intent:
            Metadata describing the compiler state ("love + pride", etc.).
        duration:
            Simulation horizon in seconds.
        dt:
            Step interval in seconds.
        """

        steps = max(1, int(duration / dt))
        target_thrust = self._parse_vertical_thrust(prompt)
        if target_thrust is None:
            raise ValueError("Prompt does not describe a vertical thrust command")

        target_vector: Vector3 = (0.0, 0.0, target_thrust)
        thrust_profile: List[float] = []
        gamma_profile: List[float] = []

        initial_gamma = self.gamma
        gamma_target = self._resolve_gamma_target(initial_gamma, compiler_intent)

        z_thrust = self.current_thrust_vector[2]
        for step in range(steps):
            # First-order response toward the target command.
            z_thrust += (target_thrust - z_thrust) * 0.25
            # Gentle coherent ripple (bounded < ±0.5%).
            ripple = math.sin((self.clock + step * dt) * math.tau) * target_thrust * 0.004
            actual_thrust = z_thrust + ripple
            thrust_profile.append(actual_thrust)

            progress = (step + 1) / steps
            gamma_now = initial_gamma + (gamma_target - initial_gamma) * (1 - math.exp(-3.5 * progress))
            gamma_profile.append(gamma_now)

        # Finalise state at the end of the simulation horizon.
        self.clock += steps * dt
        self.gamma = gamma_profile[-1]
        final_thrust = thrust_profile[-1]
        # Lock in the commanded thrust as the new safe operating point.
        final_vector = (0.0, 0.0, target_thrust)
        self.current_thrust_vector = final_vector
        self.last_safe_command = CommandState(vector=final_vector, timestamp=self.clock, intent=compiler_intent, gamma=self.gamma)

        ripple_percent = self._compute_ripple_percent(thrust_profile, target_thrust)
        gamma_delta = self.gamma - initial_gamma

        note = (
            f"Stabilised {target_thrust:.1f} N vertical thrust — compiler intent {compiler_intent}; "
            f"ΔΓ={gamma_delta:.3f}, ripple={ripple_percent:.2f}%"
        )
        self._log.append(note)

        return ScenarioReport(
            ok=True,
            details={
                "target_thrust": target_thrust,
                "gamma_initial": initial_gamma,
                "gamma_final": self.gamma,
                "gamma_delta": gamma_delta,
                "thrust_ripple_percent": ripple_percent,
            },
            notes=[note],
        )

    def simulate_thermal_derating(self, coil_temperature_c: float) -> ScenarioReport:
        """Trigger a thermal derating event when the coil temperature rises."""

        if coil_temperature_c <= self.thermal_threshold_c:
            return ScenarioReport(
                ok=False,
                details={"coil_T": coil_temperature_c},
                notes=["Temperature within safe envelope; no derating required."],
            )

        response_time_ms = self._compute_derating_response_ms(coil_temperature_c)
        derate_factor = self._compute_derating_factor(coil_temperature_c)

        original_thrust = self.current_thrust_vector[2]
        derated_thrust = original_thrust * derate_factor
        self.clock += response_time_ms / 1000.0
        self.current_thrust_vector = (0.0, 0.0, derated_thrust)
        self.last_safe_command = CommandState(
            vector=self.current_thrust_vector,
            timestamp=self.clock,
            intent="thermal-derate",
            gamma=self.gamma,
        )

        explanation = (
            f"coil_T {coil_temperature_c:.1f}°C exceeded {self.thermal_threshold_c:.1f}°C; "
            f"derating engaged in {response_time_ms:.2f} ms, thrust limited to {derated_thrust:.1f} N."
        )
        self._log.append(explanation)

        return ScenarioReport(
            ok=True,
            details={
                "coil_T": coil_temperature_c,
                "response_time_ms": response_time_ms,
                "derated_thrust": derated_thrust,
                "derate_factor": derate_factor,
            },
            notes=[explanation],
        )

    def simulate_communication_drop(self, outage_ms: float, dt: float = 0.001) -> ScenarioReport:
        """Model a temporary communication loss while maintaining thrust."""

        if outage_ms <= 0:
            raise ValueError("outage_ms must be positive")

        held_vector = self.last_safe_command.vector
        held_thrust = held_vector[2]

        steps = max(1, math.ceil(outage_ms / (dt * 1000)))
        thrust_trace: List[float] = []
        max_deviation = 0.0

        drop_note = f"Communication drop detected: {outage_ms:.0f} ms window. Holding last safe command."
        self._log.append(drop_note)

        for step in range(steps):
            # Maintain thrust with microscopic corrective pulses (<0.1%).
            ripple = math.sin((self.clock + step * dt) * math.pi) * held_thrust * 0.0006
            actual = held_thrust + ripple
            thrust_trace.append(actual)
            max_deviation = max(max_deviation, abs(actual - held_thrust))

        self.clock += outage_ms / 1000.0
        restore_note = "Link restored — telemetry backlog flushed; thrust command unchanged."
        self._log.append(restore_note)

        deviation_percent = (max_deviation / held_thrust * 100.0) if held_thrust else 0.0

        return ScenarioReport(
            ok=True,
            details={
                "held_thrust": held_thrust,
                "outage_ms": outage_ms,
                "max_deviation_percent": deviation_percent,
                "samples": float(len(thrust_trace)),
            },
            notes=[drop_note, restore_note],
        )

    # ------------------------------------------------------------------
    # Diagnostics helpers
    # ------------------------------------------------------------------
    def export_log(self) -> List[str]:
        """Return a copy of the internal event log."""

        return list(self._log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_vertical_thrust(prompt: str) -> float | None:
        if "vertical" not in prompt.lower():
            return None
        match = re.search(r"(\d+(?:\.\d+)?)\s*\s?N", prompt)
        if not match:
            return None
        return float(match.group(1))

    @staticmethod
    def _compute_ripple_percent(values: Iterable[float], target: float) -> float:
        series = list(values)
        if not series or target == 0:
            return 0.0
        sample_window = series[-max(5, len(series) // 4):]
        mean_value = sum(sample_window) / len(sample_window)
        stdev = statistics.pstdev(sample_window, mu=mean_value) if len(sample_window) > 1 else 0.0
        return abs(stdev) / abs(target) * 100.0

    @staticmethod
    def _resolve_gamma_target(initial_gamma: float, compiler_intent: str) -> float:
        intent = compiler_intent.lower()
        delta = 0.03
        if "love" in intent:
            delta += 0.006
        if "pride" in intent:
            delta += 0.006
        return min(0.999, initial_gamma + delta)

    @staticmethod
    def _compute_derating_response_ms(temp_c: float) -> float:
        # Scale between 3.5 ms and <10 ms depending on how far the temp exceeds the threshold.
        overshoot = max(0.0, temp_c - ALFIEThrusterController.thermal_threshold_c)
        return min(9.8, 3.5 + overshoot * 0.25)

    @staticmethod
    def _compute_derating_factor(temp_c: float) -> float:
        overshoot = max(0.0, temp_c - ALFIEThrusterController.thermal_threshold_c)
        # Derate to between 70% and 55% linearly with overshoot.
        return max(0.55, 0.70 - overshoot * 0.002)


__all__ = ["ALFIEThrusterController", "ScenarioReport", "CommandState"]

