"""
The Steering Field — constraint geometry that shapes, and never arrests.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Film-Reel steering law, enforced as geometry: resistance acts ONLY on
the component of a proposed action perpendicular to the current heading.
The parallel component — the motion itself — passes through untouched, so
pure opposition and deadlock are impossible by construction. The field can
bend a path; it cannot stop one.

Honesty rule: with no heading (a cluster that has not yet moved), there is
nothing to be perpendicular to — the proposal passes through unchanged and
the pass-through is named, not hidden.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import math
from typing import Any

__all__ = ["SteeringField"]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _norm(a: list[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


class SteeringField:
    """Perpendicular-only resistance: R ∈ [0, 1) scales the sideways component."""

    def __init__(self, resistance: float = 0.5):
        if not 0.0 <= resistance < 1.0:
            raise ValueError("resistance must sit in [0, 1) — the field may bend "
                             "a path but never arrest it")
        self.resistance = float(resistance)

    def steer(self, proposal: list[float],
              heading: list[float] | None) -> dict[str, Any]:
        """Shape ``proposal`` around ``heading``; parallel part preserved EXACTLY."""
        if heading is None or _norm(heading) == 0.0:
            return {"steered": list(proposal), "parallel": list(proposal),
                    "perpendicular_scaled": [0.0] * len(proposal),
                    "note": "no heading yet — nothing to be perpendicular to, "
                            "proposal passed through unchanged"}
        h_norm = _norm(heading)
        unit = [h / h_norm for h in heading]
        along = _dot(proposal, unit)
        parallel = [along * u for u in unit]
        perpendicular = [p - q for p, q in zip(proposal, parallel, strict=True)]
        scaled = [(1.0 - self.resistance) * x for x in perpendicular]
        return {
            "steered": [a + b for a, b in zip(parallel, scaled, strict=True)],
            "parallel": parallel,
            "perpendicular_scaled": scaled,
            "note": f"perpendicular component scaled by {1.0 - self.resistance:.3f}; "
                    f"parallel component untouched",
        }
