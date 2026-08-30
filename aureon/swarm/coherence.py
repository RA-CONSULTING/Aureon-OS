"""
Cluster Coherence — Γ as a rolling correlation, measured, never asserted.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Film-Reel definition, lifted verbatim: Γ is the rolling-window Pearson
correlation between the cluster's operator levels and the magnitudes of the
actions it proposes. A cluster whose thinking and whose proposals move
together is coherent; one whose proposals ignore its own operator output
is not.

Honesty rules:

* Γ is ``None`` until the window is FULL — a warming metric is reported
  warming, never padded;
* zero-variance windows (nothing moved) return Γ = 0.0 with the reason
  available — correlation of constants is not coherence.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any

__all__ = ["ClusterCoherence"]


class ClusterCoherence:
    """Rolling Pearson correlation between operator levels and action magnitudes."""

    def __init__(self, window: int = 8):
        if window < 3:
            raise ValueError("a correlation window needs at least 3 samples")
        self.window = int(window)
        self._levels: deque[float] = deque(maxlen=self.window)
        self._magnitudes: deque[float] = deque(maxlen=self.window)

    def push(self, operator_level: float, action_magnitude: float) -> None:
        self._levels.append(float(operator_level))
        self._magnitudes.append(float(action_magnitude))

    @property
    def warm(self) -> bool:
        return len(self._levels) >= self.window

    def gamma(self) -> float | None:
        """Γ over the window; ``None`` while warming — never a placeholder."""
        if not self.warm:
            return None
        xs, ys = list(self._levels), list(self._magnitudes)
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        dx = [x - mx for x in xs]
        dy = [y - my for y in ys]
        sx = math.sqrt(sum(d * d for d in dx))
        sy = math.sqrt(sum(d * d for d in dy))
        if sx == 0.0 or sy == 0.0:
            return 0.0  # constants correlate with nothing — measured, not assumed
        return sum(a * b for a, b in zip(dx, dy, strict=True)) / (sx * sy)

    def to_dict(self) -> dict[str, Any]:
        return {"window": self.window, "samples": len(self._levels),
                "warm": self.warm, "gamma": self.gamma()}
