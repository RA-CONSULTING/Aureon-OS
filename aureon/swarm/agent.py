"""
The Swarm Agent — one harmonic mode with its own probability coordination.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each agent is one oscillator of the substrate — its own {f, w, φ} — carrying:

* a local state Ψᵢ updated by the HNC recursion
      Ψᵢ(t+1) = (1−αᵢ)Ψᵢ(t) + αᵢ·Rᵢ(Cₜ, {Ψⱼ}_cluster, M(t−τ))
  where Rᵢ is the composite operator (saliency → pattern → framing against
  the echo → living-node κ modulation → synthesis);
* a local probability simplex pᵢ over the task's actions, updated by
  multiplicative weights  pᵢ ∝ pᵢ·exp(η·score)  — SOFT mass only, the agent
  never hard-votes;
* the measured indices: resonance rᵢ, constraint λᵢ, purity Pᵢ = rᵢ/λᵢ,
  structuring κᵢ.

Everything is deterministic given the seed material (agent id + role): the
initial Ψ comes from a hash, never from an unseeded RNG — the same swarm
always runs the same march.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

__all__ = ["SwarmAgent"]

_LAMBDA_FLOOR = 1e-6  # constraint floor so purity never divides by zero


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _norm(a: list[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def _seed_vector(seed: str, dim: int) -> list[float]:
    """Deterministic unit-scale vector from a hash — no unseeded randomness."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    raw = [(digest[i % len(digest)] / 127.5) - 1.0 for i in range(dim)]
    n = _norm(raw) or 1.0
    return [x / n for x in raw]


class SwarmAgent:
    """One harmonic mode of the swarm, with its own probability simplex."""

    def __init__(self, agent_id: str, role: str, actions: list[str],
                 freq: float = 1.0, weight: float = 1.0, phase: float = 0.0,
                 alpha: float = 0.3, eta: float = 1.0, dim: int = 8):
        if not actions:
            raise ValueError("an agent needs a real action set")
        self.agent_id = str(agent_id)
        self.role = str(role)
        self.actions = list(actions)
        self.freq, self.weight, self.phase = float(freq), float(weight), float(phase)
        self.alpha, self.eta, self.dim = float(alpha), float(eta), int(dim)
        self.psi: list[float] = _seed_vector(f"{agent_id}:{role}", dim)
        self.p: dict[str, float] = {a: 1.0 / len(actions) for a in actions}
        self.resonance = 0.0
        self.constraint = _LAMBDA_FLOOR
        self.kappa = 0.0

    # ── substrate ─────────────────────────────────────────────────────────
    def substrate(self, t: float) -> float:
        """This mode's contribution to Λ(t): w·sin(2πft + φ)."""
        return self.weight * math.sin(2.0 * math.pi * self.freq * t + self.phase)

    # ── the composite operator R ──────────────────────────────────────────
    def _operator(self, context: list[float], cluster_states: list[list[float]],
                  echo: list[float] | None) -> list[float]:
        """R: saliency → pattern → framing (echo) → living node κ → synthesis."""
        # saliency: what in the context this mode already resonates with
        salient = [c * (1.0 + ps) for c, ps in zip(context, self.psi, strict=True)]
        # pattern: saturating non-linearity (the observer's tanh — no blow-up)
        pattern = [math.tanh(x) for x in salient]
        # framing: blend against the causal echo when the echo is LIVE;
        # a dark echo frames nothing — it is skipped, never invented
        if echo is not None:
            pattern = [0.7 * x + 0.3 * e for x, e in zip(pattern, echo, strict=True)]
        # living node: κ modulation by the cluster's mean field
        if cluster_states:
            mean = [sum(s[i] for s in cluster_states) / len(cluster_states)
                    for i in range(self.dim)]
            pattern = [x + self.kappa * m for x, m in zip(pattern, mean, strict=True)]
        return pattern  # synthesis

    # ── the HNC recursion ─────────────────────────────────────────────────
    def update(self, context: list[float], cluster_states: list[list[float]],
               echo: list[float] | None) -> None:
        """Ψ(t+1) = (1−α)Ψ(t) + α·R(...), then measure r, λ, P, κ."""
        r_out = self._operator(context, cluster_states, echo)
        new_psi = [(1.0 - self.alpha) * p + self.alpha * x
                   for p, x in zip(self.psi, r_out, strict=True)]
        # resonance: alignment of the operator output with the context
        denom = (_norm(r_out) * _norm(context)) or 1.0
        self.resonance = _dot(r_out, context) / denom
        # constraint: how hard the recursion had to bend the state
        self.constraint = max(_LAMBDA_FLOOR,
                              _norm([a - b for a, b in zip(new_psi, self.psi,
                                                           strict=True)]))
        # structuring: growth of internal order (norm change of Ψ)
        self.kappa = _norm(new_psi) - _norm(self.psi)
        self.psi = new_psi

    @property
    def purity(self) -> float:
        """P = r/λ — resonance earned per unit of constraint spent."""
        return self.resonance / self.constraint

    # ── the local probability coordination system ─────────────────────────
    def propose(self, action_vectors: dict[str, list[float]],
                cluster_gamma: float | None) -> dict[str, float]:
        """Multiplicative-weights update of the simplex; returns SOFT mass.

        score(action) = alignment of the action's direction with Ψ, scaled by
        the cluster's coherence when it is measured (warm-up Γ=None scales by
        nothing — honest exploration, not an invented confidence).
        """
        gain = self.eta * (cluster_gamma if cluster_gamma is not None else 0.5)
        scores = {}
        for a in self.actions:
            vec = action_vectors[a]
            denom = (_norm(vec) * _norm(self.psi)) or 1.0
            scores[a] = _dot(vec, self.psi) / denom
        new_p = {a: self.p[a] * math.exp(gain * scores[a]) for a in self.actions}
        total = sum(new_p.values()) or 1.0
        self.p = {a: v / total for a, v in new_p.items()}
        return dict(self.p)

    def to_dict(self) -> dict[str, Any]:
        return {"agent_id": self.agent_id, "role": self.role,
                "resonance": self.resonance, "constraint": self.constraint,
                "purity": self.purity, "kappa": self.kappa, "p": dict(self.p)}
