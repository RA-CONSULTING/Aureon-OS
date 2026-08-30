"""
The Fleadh Swarm — the hive specialised to a living city under festival load.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Belfast Fleadh Cheoil equations, executable. Two agent populations share
one city field Λ(t):

* **Workers** W — fixed roles, skill s ∈ [0,1]; observation gain α = α₀·s
  and reliability ρ = s^γ (higher skill weighs more in the zone's observer
  term and in what gets written to memory);
* **Visitors** V(t) — arriving in singles/pairs/groups with hash-seeded
  intent vectors; lower observation gain; state coupling by the NAMED group
  registry β_single/β_pair/β_group/β_cross.

Zones (stage, street segment, hospitality, …) are mixed clusters with a
capacity; the steering law u′ = u − Proj_{u⊥}(∇R) shapes flow around the
constraint field with STEP LENGTH PRESERVED EXACTLY — corridors open,
streams separate, motion is never arrested. The city-scale Queen actualises
road closures / reroutes / holds only when the zone's Γ clears the gate,
β sits inside the island of stability, the canonical field (when live) has
only TIGHTENED, and — before any of that — the HARD SAFETY BOUNDARY holds:
a zone at capacity refuses flow-increasing actions regardless of how
coherent the cluster is. Safety beats coherence, always, by construction.

HONESTY BOUNDARY: this is a coordination/planning instrument running on
LABELED scenario data — deterministic, reproducible, and never a claim
about real people or a live crowd feed. Connecting real telemetry is a
separate, credentialed step.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any

from aureon.swarm.agent import SwarmAgent, _seed_vector
from aureon.swarm.coherence import ClusterCoherence
from aureon.swarm.memory_bus import CausalEchoBus
from aureon.swarm.queen_gate import QueenGate
from aureon.swarm.steering import _dot, _norm

__all__ = ["BETA_COUPLING", "GAMMA_RELIABILITY", "VISITOR_WEIGHT",
           "WorkerAgent", "VisitorAgent", "Zone", "steer_flow", "FleadhCompany"]

#: visitor group couplings — a coupling exists in this registry by NAME
BETA_COUPLING: dict[str, float] = {
    "single": 0.65, "pair": 0.95, "group": 0.85, "cross": 0.70,
}
#: reliability exponent: ρ = s^γ — skill compounds into trust
GAMMA_RELIABILITY = 1.5
#: a visitor's fixed observer weight in a zone (workers carry ρ = s^γ)
VISITOR_WEIGHT = 0.3
#: the city actions the Queen may actualise
CITY_ACTIONS = ["open_corridor", "hold_flow", "reroute", "close_road"]
#: actions that INCREASE flow into a zone — refused at capacity, always
_FLOW_INCREASING = {"open_corridor"}


class WorkerAgent(SwarmAgent):
    """A shift worker: role-fixed, skill-modulated gain, reliability ρ = s^γ."""

    def __init__(self, agent_id: str, role: str, skill: float,
                 actions: list[str], alpha0: float = 0.5, **kw: Any):
        if not 0.0 <= skill <= 1.0:
            raise ValueError(f"skill must sit in [0, 1] (got {skill})")
        super().__init__(agent_id, role, actions,
                         alpha=alpha0 * max(0.05, skill), **kw)
        self.skill = float(skill)

    @property
    def reliability(self) -> float:
        """ρ = s^γ — the weight this worker carries in the zone's observer."""
        return self.skill ** GAMMA_RELIABILITY


class VisitorAgent(SwarmAgent):
    """A festival visitor: group-coupled, intent-carrying, lower gain."""

    def __init__(self, agent_id: str, group_kind: str, group_id: str,
                 actions: list[str], alpha0: float = 0.5, **kw: Any):
        if group_kind not in ("single", "pair", "group"):
            raise ValueError(f"unknown group kind '{group_kind}' — groups join "
                             f"by name: single, pair, group")
        super().__init__(agent_id, f"visitor:{group_kind}", actions,
                         alpha=alpha0 * 0.35, **kw)
        self.group_kind = group_kind
        self.group_id = str(group_id)
        self.intent = _seed_vector(f"intent:{agent_id}", self.dim)

    def couple(self, others: list[VisitorAgent]) -> None:
        """Blend Ψ toward companions by the NAMED coupling β_jk."""
        for other in others:
            if other is self:
                continue
            beta = (BETA_COUPLING[self.group_kind]
                    if other.group_id == self.group_id
                    else BETA_COUPLING["cross"])
            step = 0.1 * beta
            self.psi = [(1.0 - step) * a + step * b
                        for a, b in zip(self.psi, other.psi, strict=True)]


def steer_flow(u: list[float], grad: list[float]) -> dict[str, Any]:
    """u′ = u − Proj_{u⊥}(∇R), step length preserved EXACTLY.

    The constraint field bends the path (removes the sideways push of the
    gradient) and the result is rescaled to |u| — flows are shaped, never
    arrested, and forward motion never reverses.
    """
    speed = _norm(u)
    if speed == 0.0 or _norm(grad) == 0.0:
        return {"steered": list(u),
                "note": "no motion or no gradient — nothing to shape"}
    unit = [x / speed for x in u]
    along = _dot(grad, unit)
    perp = [g - along * e for g, e in zip(grad, unit, strict=True)]
    bent = [x - p for x, p in zip(u, perp, strict=True)]
    scale = speed / (_norm(bent) or 1.0)
    return {"steered": [x * scale for x in bent],
            "note": f"perpendicular push removed; step length {speed:.6f} preserved"}


class Zone:
    """One festival zone: mixed workers + visitors, capacity, measured Γ."""

    def __init__(self, name: str, workers: list[WorkerAgent], capacity: int,
                 *, beta: float = 0.9, window: int = 6):
        if len(workers) < 2:
            raise ValueError(f"zone '{name}': a zone is never run by one agent")
        if capacity < 1:
            raise ValueError(f"zone '{name}': capacity must be positive")
        self.name = str(name)
        self.workers = list(workers)
        self.visitors: list[VisitorAgent] = []
        self.capacity = int(capacity)
        self.beta = float(beta)
        self.coherence = ClusterCoherence(window=window)
        self.heading: list[float] | None = None

    @property
    def occupancy(self) -> int:
        return len(self.visitors)

    @property
    def pressure(self) -> float:
        """The zone's contribution to the constraint field R."""
        return self.occupancy / self.capacity

    def admit(self, visitor: VisitorAgent) -> None:
        self.visitors.append(visitor)

    def step(self, context: list[float], action_vectors: dict[str, list[float]],
             echo: list[float] | None, grad: list[float]) -> dict[str, Any]:
        members: list[SwarmAgent] = [*self.workers, *self.visitors]
        states = [list(m.psi) for m in members]
        for member in members:
            member.update(context, states, echo)
        for visitor in self.visitors:
            visitor.couple(self.visitors)

        gamma_before = self.coherence.gamma()
        simplexes = [m.propose(action_vectors, gamma_before) for m in members]
        actions = sorted(action_vectors)
        joint = {a: sum(s[a] for s in simplexes) / len(simplexes) for a in actions}

        dim = len(next(iter(action_vectors.values())))
        proposal = [sum(joint[a] * action_vectors[a][i] for a in actions)
                    for i in range(dim)]
        shaped = steer_flow(proposal, grad)

        # reliability-weighted observer level: ρ for workers, fixed visitor weight
        weights = ([w.reliability for w in self.workers]
                   + [VISITOR_WEIGHT] * len(self.visitors))
        levels = [m.resonance for m in members]
        total_w = sum(weights) or 1.0
        operator_level = sum(w * r for w, r in zip(weights, levels, strict=True)) / total_w
        self.coherence.push(operator_level, _norm(shaped["steered"]))

        return {"zone": self.name, "joint_mass": joint,
                "proposal_steered": shaped["steered"],
                "gamma": self.coherence.gamma(), "beta": self.beta,
                "occupancy": self.occupancy, "pressure": round(self.pressure, 4),
                "operator_level_weighted": round(operator_level, 6)}


class FleadhCompany:
    """The festival company: zones under one Queen, one echo bus, hard safety."""

    def __init__(self, zones: list[Zone], *, tau: int = 2,
                 gamma_crit: float = 0.5, veto: Any = None):
        names = [z.name for z in zones]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate zone names: {sorted(names)}")
        self.zones = {z.name: z for z in zones}
        self.bus = CausalEchoBus(tau=tau)
        self.queen = QueenGate(gamma_crit=gamma_crit,
                               **({"veto": veto} if veto is not None else {}))
        self.action_vectors = {a: _seed_vector(f"city:{a}", 8) for a in CITY_ACTIONS}
        self.ledger: list[dict[str, Any]] = []
        self.safety_refusals: list[str] = []

    def _gradient_for(self, zone: Zone) -> list[float]:
        """∇R from the OTHER zones' pressures — congestion pushes flow away."""
        others = [z for z in self.zones.values() if z is not zone]
        if not others:
            return [0.0] * 8
        grad = [0.0] * 8
        for other in others:
            direction = _seed_vector(f"zonedir:{other.name}", 8)
            grad = [g + other.pressure * d
                    for g, d in zip(grad, direction, strict=True)]
        return grad

    def step(self, t: int, context: list[float],
             arrivals: list[VisitorAgent] | None = None,
             arrival_zone: str | None = None) -> dict[str, Any]:
        """One city tick: arrivals land, zones step, the Queen gates each."""
        if arrivals:
            zone = self.zones.get(arrival_zone or "")
            if zone is None:
                raise ValueError(f"arrivals need a real zone (got '{arrival_zone}')")
            for visitor in arrivals:
                zone.admit(visitor)

        echo = self.bus.echo(t)
        outcomes: dict[str, Any] = {}
        for name, zone in sorted(self.zones.items()):
            tick = zone.step(context, self.action_vectors, echo,
                             self._gradient_for(zone))
            # HARD SAFETY BOUNDARY — checked BEFORE coherence, beats it always
            top = min(tick["joint_mass"],
                      key=lambda a: (-tick["joint_mass"][a], a))
            if top in _FLOW_INCREASING and zone.occupancy >= zone.capacity:
                reason = (f"hard safety boundary: zone '{name}' at capacity "
                          f"({zone.occupancy}/{zone.capacity}) — '{top}' refused "
                          f"regardless of coherence")
                self.safety_refusals.append(reason)
                outcomes[name] = {"tick": tick,
                                  "decision": {"actualized": False,
                                               "action": None,
                                               "reasons": [reason],
                                               "safety_refusal": True}}
                self.bus.record_possibilities(t, tick["joint_mass"])
                continue
            decision = self.queen.actualize(tick["joint_mass"], tick["gamma"],
                                            zone.beta)
            if decision.actualized:
                self.bus.record_realized(t, tick["proposal_steered"])
                zone.heading = list(tick["proposal_steered"])
            else:
                self.bus.record_possibilities(t, tick["joint_mass"])
            outcomes[name] = {"tick": tick, "decision": decision.to_dict()}
        entry = {"t": int(t), "echo_live": echo is not None,
                 "population": {"workers": sum(len(z.workers)
                                               for z in self.zones.values()),
                                "visitors": sum(z.occupancy
                                                for z in self.zones.values())},
                 "outcomes": outcomes}
        self.ledger.append(entry)
        return entry

    def report(self) -> dict[str, Any]:
        actualized = sum(1 for d in self.queen.decisions if d.actualized)
        return {
            "zones": sorted(self.zones),
            "steps": len(self.ledger),
            "decisions_total": len(self.queen.decisions) + len(self.safety_refusals),
            "decisions_actualized": actualized,
            "safety_refusals": len(self.safety_refusals),
            "final_population": self.ledger[-1]["population"] if self.ledger else {},
            "bus": self.bus.to_dict(),
            "boundary": ("a planning instrument on LABELED scenario data — "
                         "deterministic and reproducible, never a claim about "
                         "real people or a live crowd feed"),
        }
