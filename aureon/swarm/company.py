"""
The Company — clusters as departments, departments as agents, Queen as board.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The multi-scale recursion of the source papers, executable:

* a **Cluster** couples ≥2 agents into one department — no agent ever owns
  a task alone (a one-agent cluster is refused with a named reason);
* each step, every member runs the HNC recursion, emits SOFT probability
  mass, and the cluster's Γ is measured (operator level vs proposal
  magnitude) — the joint mass is the mean of the members' simplexes;
* the joint action VECTOR passes through the steering field (perpendicular
  shaped, parallel preserved) before the Queen sees it;
* the **Company** treats clusters exactly as agents one level up: the same
  propose/measure interface, the same Queen gate, the same causal-echo bus —
  the hierarchy is the same law at every scale;
* on actualization, ONLY the realized increment is written to the echo bus;
  the unrealized ensemble is parked in the UED.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import math
from typing import Any

from aureon.swarm.agent import SwarmAgent
from aureon.swarm.coherence import ClusterCoherence
from aureon.swarm.memory_bus import CausalEchoBus
from aureon.swarm.queen_gate import Actualization, QueenGate
from aureon.swarm.steering import SteeringField

__all__ = ["Cluster", "Company"]


def _norm(a: list[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


class Cluster:
    """One department: ≥2 coupled agents holding a task together."""

    def __init__(self, name: str, agents: list[SwarmAgent], *, beta: float = 0.9,
                 window: int = 8, resistance: float = 0.5):
        if len(agents) < 2:
            raise ValueError(
                f"cluster '{name}': a task is never owned by a single agent — "
                f"couple at least 2 (got {len(agents)})")
        actions = agents[0].actions
        if any(a.actions != actions for a in agents):
            raise ValueError(f"cluster '{name}': members must share one action set")
        self.name = str(name)
        self.agents = list(agents)
        self.actions = list(actions)
        self.beta = float(beta)
        self.coherence = ClusterCoherence(window=window)
        self.steering = SteeringField(resistance=resistance)
        self.heading: list[float] | None = None

    def step(self, context: list[float], action_vectors: dict[str, list[float]],
             echo: list[float] | None) -> dict[str, Any]:
        """One cluster tick: recursion → soft proposals → Γ sample → steering."""
        states = [list(a.psi) for a in self.agents]
        for agent in self.agents:
            agent.update(context, states, echo)

        gamma_before = self.coherence.gamma()
        simplexes = [a.propose(action_vectors, gamma_before) for a in self.agents]
        joint = {act: sum(s[act] for s in simplexes) / len(simplexes)
                 for act in self.actions}

        # the cluster's proposal as a vector: probability-weighted blend
        dim = len(next(iter(action_vectors.values())))
        proposal = [sum(joint[a] * action_vectors[a][i] for a in self.actions)
                    for i in range(dim)]
        shaped = self.steering.steer(proposal, self.heading)

        operator_level = (sum(a.resonance for a in self.agents) / len(self.agents))
        self.coherence.push(operator_level, _norm(shaped["steered"]))

        return {
            "cluster": self.name,
            "joint_mass": joint,
            "proposal_steered": shaped["steered"],
            "steering_note": shaped["note"],
            "gamma": self.coherence.gamma(),
            "beta": self.beta,
            "purity": {a.agent_id: a.purity for a in self.agents},
        }

    def realize(self, steered: list[float]) -> None:
        """The Queen actualized this cluster's step — the heading moves."""
        self.heading = list(steered)


class Company:
    """The whole organism: departments under one Queen, one echo bus."""

    def __init__(self, clusters: list[Cluster], *, tau: int = 3,
                 gamma_crit: float | None = None,
                 veto: Any = None):
        if not clusters:
            raise ValueError("a company needs at least one department")
        names = [c.name for c in clusters]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate department names: {sorted(names)}")
        self.clusters = {c.name: c for c in clusters}
        self.bus = CausalEchoBus(tau=tau)
        kwargs: dict[str, Any] = {}
        if gamma_crit is not None:
            kwargs["gamma_crit"] = gamma_crit
        if veto is not None:
            kwargs["veto"] = veto
        self.queen = QueenGate(**kwargs)
        self.ledger: list[dict[str, Any]] = []

    def assign(self, task: str, cluster_name: str) -> dict[str, Any]:
        """A task lands on a CLUSTER — the single-agent path does not exist."""
        cluster = self.clusters.get(cluster_name)
        if cluster is None:
            return {"assigned": False,
                    "reason": f"no department named '{cluster_name}'"}
        return {"assigned": True, "task": str(task), "cluster": cluster.name,
                "members": [a.agent_id for a in cluster.agents]}

    def step(self, t: int, context: list[float],
             action_vectors: dict[str, list[float]]) -> dict[str, Any]:
        """One company tick: every department steps, the Queen gates each."""
        echo = self.bus.echo(t)
        outcomes: dict[str, Any] = {}
        for name, cluster in sorted(self.clusters.items()):
            tick = cluster.step(context, action_vectors, echo)
            decision: Actualization = self.queen.actualize(
                tick["joint_mass"], tick["gamma"], cluster.beta)
            if decision.actualized:
                self.bus.record_realized(t, tick["proposal_steered"])
                cluster.realize(tick["proposal_steered"])
            else:
                self.bus.record_possibilities(t, tick["joint_mass"])
            outcomes[name] = {"tick": tick, "decision": decision.to_dict()}
        entry = {"t": int(t), "echo_live": echo is not None, "outcomes": outcomes}
        self.ledger.append(entry)
        return entry

    def report(self) -> dict[str, Any]:
        """The measured record: decisions, coherences, purities — no decoration."""
        actualized = sum(1 for d in self.queen.decisions if d.actualized)
        return {
            "departments": sorted(self.clusters),
            "steps": len(self.ledger),
            "decisions_total": len(self.queen.decisions),
            "decisions_actualized": actualized,
            "bus": self.bus.to_dict(),
            "boundary": ("a measured record of swarm coordination — every "
                         "refusal named, only realized increments in memory"),
        }
