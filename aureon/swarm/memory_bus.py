"""
The Causal Echo Bus — β·Λ(t−τ) as shared, delayed, realized-only memory.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Film-Reel discipline, enforced:

* only the REALIZED increment of each step is written to the bus — the
  single trajectory the Queen actualized;
* the unrealized possibilities of that step stay in the UED (the possibility
  ensemble), retrievable but never mistaken for memory of what happened;
* reads are delayed by τ steps — ``echo(t)`` returns what was realized at
  t−τ, and returns ``None`` when nothing was (a dark echo is reported dark,
  never invented).

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any

__all__ = ["CausalEchoBus"]


class CausalEchoBus:
    """Delayed shared memory: realized increments only, echo at t−τ."""

    def __init__(self, tau: int = 3):
        if tau < 1:
            raise ValueError("the causal echo needs a real delay (τ ≥ 1)")
        self.tau = int(tau)
        self._realized: dict[int, list[float]] = {}
        self._possibilities: dict[int, dict[str, float]] = {}

    def record_realized(self, step: int, increment: list[float]) -> None:
        """Write the ONE actualized increment for this step."""
        self._realized[int(step)] = list(increment)

    def record_possibilities(self, step: int, ensemble: dict[str, float]) -> None:
        """Park the unrealized possibility mass in the UED — NOT memory."""
        self._possibilities[int(step)] = dict(ensemble)

    def echo(self, step: int) -> list[float] | None:
        """M(t−τ): the realized increment τ steps ago, or None (dark echo)."""
        return self._realized.get(int(step) - self.tau)

    def possibilities(self, step: int) -> dict[str, float] | None:
        """The UED ensemble parked at a step — retrievable, never replayed as fact."""
        return self._possibilities.get(int(step))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tau": self.tau,
            "realized_steps": sorted(self._realized),
            "possibility_steps": sorted(self._possibilities),
            "boundary": ("only actualized increments live here; the possibility "
                         "ensemble is parked separately and never becomes memory"),
        }
