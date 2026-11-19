"""
HNCDeployer — Λ(t)-driven White Cell Deployment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Deploy the agents to act like white blood cells based on HNC theory."

Given the current Λ(t) master field strength and the cortex gamma band,
this module decides how many white cells to spawn on each tick.

Deployment rules (ordered):

  1. If the cortex gamma band amplitude exceeds 0.3 (a gamma spike) and
     Λ(t) is a finite reading, deploy up to ceil(|Λ(t)| × 10) cells.
     With no Λ(t) reading, that count is not computed.
  2. If the Auris metacognitive verdict is "RALLY", deploy at least 3.
  3. If gratitude score drops below 0.4, deploy 1 for recovery.
  4. Otherwise, deploy 0 (let the system breathe).

The deployment count is bounded by `max_cells_per_tick` so a spike can't
spawn hundreds of cells at once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _read_lambda_t(raw: Any) -> Optional[float]:
    """A published Lambda(t), or None when there is no reading.

    Missing and None stay None. A real 0.0 stays 0.0. A bool, a
    non-number, or a non-finite value is not a reading.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    number = float(raw)
    if not math.isfinite(number):
        return None
    return number


@dataclass
class DeploymentDecision:
    count: int
    reason: str
    gamma_amplitude: float
    lambda_t: Optional[float]
    auris_consensus: str
    gratitude_score: float


class HNCDeployer:
    """
    Deploy-count decision engine.

    Usage:
        deployer = HNCDeployer(max_cells_per_tick=8)
        decision = deployer.should_deploy(vault, auris_result)
        print(decision.count, decision.reason)
    """

    def __init__(
        self,
        max_cells_per_tick: int = 8,
        gamma_threshold: float = 0.3,
        gratitude_recovery_threshold: float = 0.4,
    ):
        self.max_cells_per_tick = int(max_cells_per_tick)
        self.gamma_threshold = float(gamma_threshold)
        self.gratitude_recovery_threshold = float(gratitude_recovery_threshold)
        self._last_decision: Optional[DeploymentDecision] = None
        self._total_deployed: int = 0

    def should_deploy(self, vault: Any, auris_result: Any = None) -> DeploymentDecision:
        cortex = getattr(vault, "cortex_snapshot", {}) or {}
        gamma_amp = float(cortex.get("gamma", 0.0) or 0.0)
        try:
            lambda_t = _read_lambda_t(getattr(vault, "last_lambda_t", None))
        except Exception:
            lambda_t = None
        gratitude = float(getattr(vault, "gratitude_score", 0.5) or 0.5)

        consensus = "NEUTRAL"
        if auris_result is not None:
            consensus = str(getattr(auris_result, "consensus", "NEUTRAL") or "NEUTRAL")

        count = 0
        reason = "no-trigger"

        # Rule 1: gamma spike. The cell count uses Λ(t). No reading, no count.
        if gamma_amp > self.gamma_threshold:
            if lambda_t is None:
                count = 0
                reason = f"gamma-spike γ={gamma_amp:.2f} Λ no reading"
            else:
                raw = math.ceil(abs(lambda_t) * 10.0) + 1
                count = max(1, min(self.max_cells_per_tick, int(raw)))
                reason = f"gamma-spike γ={gamma_amp:.2f} Λ={lambda_t:.2f}"

        # Rule 2: Auris rally
        elif consensus == "RALLY":
            count = max(3, min(self.max_cells_per_tick, count or 3))
            reason = "auris-rally"

        # Rule 3: low gratitude → minimal recovery deploy
        elif gratitude < self.gratitude_recovery_threshold:
            count = max(1, count)
            reason = f"gratitude-recovery ({gratitude:.2f})"

        # Rule 4: nothing to do
        else:
            count = 0
            if lambda_t is None:
                reason = (
                    f"calm γ={gamma_amp:.2f} Λ no reading "
                    f"consensus={consensus} grat={gratitude:.2f}"
                )
            else:
                reason = (
                    f"calm γ={gamma_amp:.2f} Λ={lambda_t:.2f} "
                    f"consensus={consensus} grat={gratitude:.2f}"
                )

        decision = DeploymentDecision(
            count=count,
            reason=reason,
            gamma_amplitude=gamma_amp,
            lambda_t=lambda_t,
            auris_consensus=consensus,
            gratitude_score=gratitude,
        )
        self._last_decision = decision
        self._total_deployed += count
        return decision

    @property
    def last_decision(self) -> Optional[DeploymentDecision]:
        return self._last_decision

    def get_status(self) -> Dict[str, Any]:
        d = self._last_decision
        return {
            "max_cells_per_tick": self.max_cells_per_tick,
            "gamma_threshold": self.gamma_threshold,
            "total_deployed": self._total_deployed,
            "last_count": d.count if d else None,
            "last_reason": d.reason if d else None,
        }
