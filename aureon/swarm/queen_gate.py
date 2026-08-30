"""
The Queen's Gate — actualization only inside the island of stability.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The board-level observer. A cluster's joint possibility mass collapses into
ONE realized action only when every gate holds, and every refusal is named:

1. **Coherence measured** — Γ_cluster must exist (a warming metric refuses).
2. **Island of stability** — the causal-echo coupling must sit inside
   0.6 < β < 1.1; beyond 1.1 is the measured stability cliff (chaos).
3. **b46 tighten-only** — when the canonical HNC field is LIVE, the
   effective gate is min(Γ_cluster, Γ_canonical): the one shared field may
   only tighten a local decision, never loosen it. A dark field is used as
   dark — the cluster's own Γ stands alone, and the darkness is recorded.
4. **Γ ≥ Γ_crit** — below the threshold the ensemble stays OPEN (soft
   exploration continues); nothing is forced.
5. **Conscience veto** — a final hard boundary; a veto is a recorded
   refusal, never a silent drop.

Collapse itself is deterministic: the highest joint mass wins, ties broken
lexicographically — the same swarm always actualizes the same trajectory.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["GAMMA_CRIT", "BETA_ISLAND", "Actualization", "QueenGate"]

#: collapse threshold on effective coherence — named, never inline magic
GAMMA_CRIT = 0.80
#: the island of stability for the causal-echo coupling β (source: Master
#: Formula stability survey — beyond 1.1 lies the stability cliff)
BETA_ISLAND = (0.6, 1.1)


def _canonical_gamma() -> float | None:
    """Canonical field Γ when live; ``None`` when dark. Never invents."""
    try:
        from aureon.core.hnc_field import read_canonical_field

        f = read_canonical_field()
        g = getattr(f, "coherence_gamma", None)
        if getattr(f, "is_live", False) and g is not None:
            return float(g)
    except Exception:  # noqa: BLE001 — a dark field must not crash the gate
        pass
    return None


@dataclass(frozen=True)
class Actualization:
    """One gate decision — actualized or honestly refused, with reasons."""

    actualized: bool
    action: str | None
    gamma_cluster: float | None
    gamma_effective: float | None
    canonical_status: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"actualized": self.actualized, "action": self.action,
                "gamma_cluster": self.gamma_cluster,
                "gamma_effective": self.gamma_effective,
                "canonical_status": self.canonical_status,
                "reasons": list(self.reasons)}


class QueenGate:
    """The final actualization gate; every decision is recorded."""

    def __init__(self, gamma_crit: float = GAMMA_CRIT,
                 veto: Callable[[str], bool] | None = None):
        self.gamma_crit = float(gamma_crit)
        self.veto = veto
        self.decisions: list[Actualization] = []

    def actualize(self, joint_mass: dict[str, float], gamma_cluster: float | None,
                  beta: float) -> Actualization:
        reasons: list[str] = []
        canonical = _canonical_gamma()
        status = "canonical_live" if canonical is not None else "canonical_dark"

        if gamma_cluster is None:
            reasons.append("cluster coherence still warming — the ensemble stays "
                           "open, nothing is forced")
            return self._record(None, None, None, status, reasons)

        lo, hi = BETA_ISLAND
        if not (lo < beta < hi):
            reasons.append(f"β={beta:.3f} outside the island of stability "
                           f"({lo} < β < {hi}) — beyond the cliff lies chaos, "
                           f"actualization refused")
            return self._record(None, gamma_cluster, None, status, reasons)

        # b46: the canonical field may only TIGHTEN — min(), never max()
        effective = (min(gamma_cluster, canonical) if canonical is not None
                     else gamma_cluster)
        if canonical is None:
            reasons.append("canonical field dark — cluster Γ stands alone")

        if effective < self.gamma_crit:
            reasons.append(f"Γ_effective={effective:.3f} below Γ_crit="
                           f"{self.gamma_crit} — soft exploration continues")
            return self._record(None, gamma_cluster, effective, status, reasons)

        # deterministic collapse: highest mass, ties lexicographic
        action = min(joint_mass, key=lambda a: (-joint_mass[a], a))
        if self.veto is not None and self.veto(action):
            reasons.append(f"conscience veto on '{action}' — hard boundary, "
                           f"refusal recorded")
            return self._record(None, gamma_cluster, effective, status, reasons)

        return self._record(action, gamma_cluster, effective, status, reasons)

    def _record(self, action: str | None, g_cluster: float | None,
                g_eff: float | None, status: str,
                reasons: list[str]) -> Actualization:
        decision = Actualization(actualized=action is not None, action=action,
                                 gamma_cluster=g_cluster, gamma_effective=g_eff,
                                 canonical_status=status, reasons=reasons)
        self.decisions.append(decision)
        return decision
