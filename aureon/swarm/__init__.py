"""
The Harmonic Swarm — the company that thinks like the Master Formula.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Single-agent task handling is replaced by an HNC-grounded hive: every agent
is a harmonic mode (substrate), every cluster a coupled domain, the shared
memory a causal echo β·Λ(t−τ), and the Queen the observer whose conscience
gate actualizes one trajectory out of the possibility ensemble.

    Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ)  +  α tanh(g Λ_Δt(t))  +  β Λ(t−τ)
           substrate                observer               causal echo

The doctrine carried over from the source papers, enforced in code:

* **No agent owns a task** — a task is always held by a cluster.
* **Soft mass, never hard votes** — every agent keeps its own probability
  simplex and updates it by the HNC recursion; collapse happens only when
  cluster coherence Γ clears the gate.
* **Steering shapes, never arrests** — the resistance field acts only on
  the perpendicular component of a proposed action; the parallel component
  is preserved exactly, so deadlock is impossible by construction.
* **Island of stability** — actualization is refused outside 0.6 < β < 1.1
  (the measured stability cliff), with the refusal named.
* **Realized-only memory** — only the actualized increment is written to
  the delayed echo bus; unrealized possibilities stay in the UED ensemble.
* **b46 tighten-only** — the canonical HNC field, when live, may only
  TIGHTEN the Queen's gate (min), never loosen it; a dark field is
  reported dark, never invented.

Gary Leckey · Aureon Institute
"""

from aureon.swarm.agent import SwarmAgent
from aureon.swarm.coherence import ClusterCoherence
from aureon.swarm.company import Cluster, Company
from aureon.swarm.memory_bus import CausalEchoBus
from aureon.swarm.queen_gate import BETA_ISLAND, GAMMA_CRIT, QueenGate
from aureon.swarm.steering import SteeringField

__all__ = [
    "BETA_ISLAND", "GAMMA_CRIT",
    "SwarmAgent", "ClusterCoherence", "Cluster", "Company",
    "CausalEchoBus", "QueenGate", "SteeringField",
]
