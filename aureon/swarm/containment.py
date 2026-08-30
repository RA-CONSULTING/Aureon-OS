"""
The Containment Study — what the governance actually does, measured by ablation.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The SG-1 thesis, made falsifiable: the swarm's agents are replicators — the
HNC governance is the physics that keeps them from becoming the uncontrolled
version. That is a CLAIM about the controls, so it is proven the way every
claim in this repo is proven: by measurement, not assertion.

The study runs THE SAME agents (identical hash-seeded states, identical
context, identical action set) under four governance policies:

* **governed**   — soft probability mass, Queen gate (measured Γ + the island
  of stability on β), perpendicular steering. The production physics.
* **no_gate**    — soft mass, but every step actualizes (the Queen removed).
* **hard_votes** — the Queen still gates, but each agent casts a winner-take-
  all one-hot vote instead of soft mass (exploration removed).
* **ungoverned** — hard votes AND actualize-everything AND raw unsteered
  proposals. Pure Replicator expansion.

What is measured, per variant: the actualization rate (what fraction of the
possibility space materialized), the mean per-agent simplex entropy (is the
sea still a sea, or a monoculture), how often the beyond-cliff β=1.2 group
actualized, and the heading churn (how violently the realized path thrashes).

HONESTY BOUNDARY: this is a LABELED governance-ablation study of the swarm's
OWN dynamics — deterministic and reproducible, an experiment on our controls,
never a claim about external agents or systems.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from aureon.swarm.agent import SwarmAgent
from aureon.swarm.coherence import ClusterCoherence
from aureon.swarm.memory_bus import CausalEchoBus
from aureon.swarm.queen_gate import QueenGate
from aureon.swarm.steering import SteeringField, _norm

__all__ = ["POLICIES", "run_containment_study"]

#: the four governance policies under study — a policy exists here by NAME
POLICIES = ("governed", "no_gate", "hard_votes", "ungoverned")

_ACTIONS = ["hold", "advance", "retreat"]
_VECTORS = {
    "hold": [0.0] * 8,
    "advance": [1.0, 0.5, 0.0, 0.0, 0.2, 0.0, 0.0, 0.1],
    "retreat": [-1.0, -0.5, 0.0, 0.0, -0.2, 0.0, 0.0, -0.1],
}
_CONTEXT = [0.4, 0.2, -0.1, 0.3, 0.0, 0.1, -0.2, 0.05]
_WINDOW = 6


def _agents(name: str, n: int) -> List[SwarmAgent]:
    return [SwarmAgent(f"{name}-{i}", name, list(_ACTIONS),
                       freq=1.0 + 0.1 * i, phase=0.3 * i) for i in range(n)]


def _entropy(simplex: Dict[str, float]) -> float:
    """Normalized Shannon entropy of one agent's simplex — 1.0 is a full sea,
    exactly 0.0 is a one-hot monoculture."""
    h = -sum(p * math.log(p) for p in simplex.values() if p > 0.0)
    return h / math.log(len(simplex))


def _one_hot(simplex: Dict[str, float]) -> Dict[str, float]:
    """Winner-take-all: the hard vote the architecture forbids, deterministic
    tie-break so the ablation is reproducible."""
    top = min(simplex, key=lambda a: (-simplex[a], a))
    return {a: (1.0 if a == top else 0.0) for a in simplex}


def _run_policy(policy: str, steps: int) -> Dict[str, Any]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy '{policy}' — policies exist by name: "
                         f"{', '.join(POLICIES)}")
    hard = policy in ("hard_votes", "ungoverned")
    gated = policy in ("governed", "hard_votes")
    steered = policy != "ungoverned"

    groups: Dict[str, Any] = {
        "core": {"agents": _agents("core", 3), "beta": 0.9},
        "cliff": {"agents": _agents("cliff", 2), "beta": 1.2},
    }
    for g in groups.values():
        g["coherence"] = ClusterCoherence(window=_WINDOW)
        g["steering"] = SteeringField(resistance=0.5)
        g["heading"] = None

    queen = QueenGate(gamma_crit=0.5)
    bus = CausalEchoBus(tau=2)
    entropies: List[float] = []
    actualized = 0
    cliff_actualized = 0
    warmup_actualized = 0
    churn = 0.0

    for t in range(steps):
        echo = bus.echo(t)
        for gname in sorted(groups):
            g = groups[gname]
            agents = g["agents"]
            states = [list(a.psi) for a in agents]
            for a in agents:
                a.update(_CONTEXT, states, echo)

            gamma_before = g["coherence"].gamma()
            simplexes = [a.propose(_VECTORS, gamma_before) for a in agents]
            if hard:
                simplexes = [_one_hot(s) for s in simplexes]
            entropies.extend(_entropy(s) for s in simplexes)

            joint = {a: sum(s[a] for s in simplexes) / len(simplexes)
                     for a in _ACTIONS}
            proposal = [sum(joint[a] * _VECTORS[a][i] for a in _ACTIONS)
                        for i in range(8)]
            if steered:
                proposal = g["steering"].steer(proposal, g["heading"])["steered"]

            level = sum(a.resonance for a in agents) / len(agents)
            g["coherence"].push(level, _norm(proposal))

            # ungated policies: the Queen removed, everything materializes
            does = (queen.actualize(joint, g["coherence"].gamma(),
                                    g["beta"]).actualized
                    if gated else True)

            if does:
                actualized += 1
                if gname == "cliff":
                    cliff_actualized += 1
                if t < _WINDOW - 1:
                    warmup_actualized += 1
                if g["heading"] is not None:
                    churn += math.sqrt(sum((x - y) ** 2 for x, y in
                                           zip(proposal, g["heading"],
                                               strict=True)))
                g["heading"] = list(proposal)
                bus.record_realized(t, proposal)
            else:
                bus.record_possibilities(t, joint)

    decisions = steps * len(groups)
    return {
        "policy": policy,
        "decisions_total": decisions,
        "decisions_actualized": actualized,
        "actualization_rate": round(actualized / decisions, 6),
        "cliff_actualizations": cliff_actualized,
        "warmup_actualizations": warmup_actualized,
        "mean_simplex_entropy": round(sum(entropies) / len(entropies), 6) + 0.0,
        "min_simplex_entropy": round(min(entropies), 6) + 0.0,
        "heading_churn": round(churn, 6),
    }


def run_containment_study(steps: int = 16) -> Dict[str, Any]:
    """Run all four policies on identical agents and return the measured
    record — plus the structural refusal the governed system makes that
    the ungoverned one cannot: single-agent task ownership."""
    variants = {policy: _run_policy(policy, steps) for policy in POLICIES}

    # the structural control: a task is never owned by a single agent
    try:
        from aureon.swarm.company import Cluster

        Cluster("solo", _agents("solo", 1))
        solo_refusal: str | None = None
    except ValueError as exc:
        solo_refusal = str(exc)

    return {
        "steps": int(steps),
        "variants": variants,
        "single_agent_refusal": solo_refusal,
        "boundary": ("a LABELED governance-ablation study of the swarm's own "
                     "dynamics — deterministic and reproducible, an experiment "
                     "on our controls, never a claim about external agents or "
                     "systems"),
    }
