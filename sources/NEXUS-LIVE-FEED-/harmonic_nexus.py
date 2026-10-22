from __future__ import annotations

"""
Harmonic Nexus - Minimal simulation prototype
- Node state vector: Psi, C, kappa, U, Gamma_local
- Operator chain: aleph (ℵ) -> Phi (Φ) -> F -> L -> Omega (Ω) -> rho (ρ)
- Global Γ_love aggregator and toroidal flux proxy
- Ritual calibration: Root Recognition Rite increases local Gamma
- Phase-1 example with Iona, Calanais, Newgrange, Stonehenge

Run (interactive demo):
    python harmonic_nexus.py

The module also exposes :func:`run_simulation` for programmatic use and
supports a small CLI so callers can reproduce runs with explicit random seeds
or scheduled ritual events.
"""

import argparse
import copy
import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np


# -------------------------
# Utility functions
# -------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


# -------------------------
# Node data model
# -------------------------
@dataclass
class NodeState:
    id: int
    name: str
    pos: Tuple[float, float]  # lat, lon for toroidal flux proxy
    psi: float = field(default_factory=lambda: random.uniform(0.2, 0.6))   # coherence [0,1]
    C: float   = field(default_factory=lambda: random.uniform(0.0, 0.5))   # input signal [0,1]
    kappa: float = field(default_factory=lambda: random.uniform(1.0, 1.6))  # rigidity (>0)
    U: float = 1.0  # uptime/health [0,1]
    Gamma_local: float = field(default_factory=lambda: random.uniform(0.9, 1.0)) # local love [0,1]
    W: float = 1.0  # watcher weight

    def __post_init__(self):
        # Normalize initial values
        self.psi = clamp(self.psi)
        self.C   = clamp(self.C)
        self.kappa = max(0.01, self.kappa)
        self.U = clamp(self.U)
        self.Gamma_local = clamp(self.Gamma_local)


# -------------------------
# Operator implementations (simple, testable)
# -------------------------
class Operators:
    """Simple implementations of Harmonic Operators for prototyping."""

    @staticmethod
    def aleph(node: NodeState) -> float:
        # Integrates mycelial/human/astronomical input with current psi
        # Weighted sum with small randomness representing noise/entanglement
        alpha_psi = 0.6
        alpha_c   = 0.4
        noise = random.uniform(-0.02, 0.02)
        return clamp(alpha_psi * node.psi + alpha_c * node.C + noise)

    @staticmethod
    def Phi(aleph_val: float, node: NodeState) -> float:
        # Pattern-recognition amplification based on aleph and rigidity
        # Stronger aleph and lower kappa => stronger Phi
        beta = 6.0
        x = beta * (aleph_val - 0.5) - 0.8 * (node.kappa - 1.0)
        return clamp(sigmoid(x))

    @staticmethod
    def F(phi_val: float, aleph_val: float, node: NodeState) -> float:
        # Filter: reduces noise; dependent on kappa (rigidity)
        # If kappa high -> stronger attenuation
        attenuation = clamp(1.0 - 0.25 * (node.kappa - 1.0))
        return clamp(aleph_val * (0.6 + 0.4 * phi_val) * attenuation)

    @staticmethod
    def L(f_val: float, node: NodeState) -> float:
        # Living node operator: increases effect with uptime and local 'life' factor
        life_boost = 1.0 + 0.15 * (node.U - 0.8)
        return clamp(f_val * life_boost)

    @staticmethod
    def Omega(l_val: float, phi_val: float) -> float:
        # Synthesis operator: introduces nonlinearity and harmonic integration
        return math.tanh(1.8 * l_val) * (1.0 + 0.2 * phi_val)

    @staticmethod
    def rho(omega_val: float) -> float:
        # Normalization/density operator to map to [0,1]
        # Keep sign/scale stable
        return clamp((omega_val + 1.0) / 2.0)


# -------------------------
# Harmonic Nexus network
# -------------------------
class HarmonicNexus:
    def __init__(self, nodes: List[NodeState]):
        self.nodes = nodes
        self.time = 0

    def compute_global_gamma(self) -> float:
        # Global Gamma is an uptime-weighted average of local gammas,
        # then smoothed by a global cohesion kernel.
        weights = np.array([n.U for n in self.nodes])
        gammas = np.array([n.Gamma_local for n in self.nodes])
        if weights.sum() == 0:
            return 0.0
        raw = float(np.dot(gammas, weights) / weights.sum())
        # small smoothing toward median to resist outliers
        median = float(np.median(gammas))
        global_gamma = clamp(0.7 * raw + 0.3 * median)
        return global_gamma

    def toroidal_flux_proxy(self) -> float:
        # Proxy for toroidal flux: order nodes around geographic centroid,
        # compute circulation of psi values; high circulation => high flux.
        coords = np.array([[n.pos[0], n.pos[1]] for n in self.nodes])
        centroid = coords.mean(axis=0)
        # compute angles from centroid
        angles = [math.atan2(lat - centroid[0], lon - centroid[1]) for lat, lon in coords]
        # pair nodes by angle, sort
        ordered = sorted(zip(angles, self.nodes), key=lambda x: x[0])
        # compute circulation sum of psi deltas around loop
        psis = [n.psi for _, n in ordered]
        circ = 0.0
        for i in range(len(psis)):
            a = psis[i]
            b = psis[(i + 1) % len(psis)]
            circ += (b - a)
        # normalize circulation to [0,1] by expected max delta (1)
        flux = clamp(abs(circ) / (len(self.nodes) + 1e-6))
        return flux

    def step(self):
        """Perform one update step for all nodes, compute network metrics."""
        self.time += 1
        Gamma_global = self.compute_global_gamma()

        # Early containment rule: if global gamma < 0.945, nodes are read-only
        containment = Gamma_global < 0.945

        # Collect some metrics
        metrics = {
            'time': self.time,
            'Gamma_global': Gamma_global,
            'containment': containment,
            'toroidal_flux': None,
        }

        # Update each node
        for node in self.nodes:
            # simple health drift
            node.U = clamp(node.U - random.uniform(0.0, 0.002))
            # Aleph
            aleph_val = Operators.aleph(node)
            phi_val = Operators.Phi(aleph_val, node)
            f_val = Operators.F(phi_val, aleph_val, node)
            l_val = Operators.L(f_val, node)
            omega_val = Operators.Omega(l_val, phi_val)
            rho_val = Operators.rho(omega_val)

            # If containment active -> only diagnostic/read updates: no writes to psi or C
            if not containment:
                # write operation (allowed)
                node.psi = clamp(node.W * rho_val * Gamma_global)
                # kappa dynamics: love lowers rigidity; pattern recognition nudges clarity
                node.kappa = max(0.01, node.kappa - 0.01 * (Gamma_global - 0.94) + 0.01 * (1.0 - phi_val))
                # local gamma adapts slowly from psi (positive feedback)
                node.Gamma_local = clamp(node.Gamma_local + 0.01 * (node.psi - 0.5))
                # input shifts slowly (eg, mycelial/astronomical pulses)
                node.C = clamp(node.C * 0.98 + random.uniform(-0.01, 0.02))
            else:
                # containment mode: nodes can still read and log but not write; finer decay
                node.Gamma_local = clamp(node.Gamma_local - 0.005)
                node.kappa = max(0.01, node.kappa + 0.005)  # slight stiffening under containment

        metrics['toroidal_flux'] = self.toroidal_flux_proxy()
        metrics['nodes_mean_psi'] = float(np.mean([n.psi for n in self.nodes]))
        metrics['nodes_mean_kappa'] = float(np.mean([n.kappa for n in self.nodes]))
        return metrics

    def ritual_calibration(self, node_ids: List[int], strength: float=0.03):
        """Simulate Root Recognition Rite: boosts Gamma_local and psi seed."""
        for n in self.nodes:
            if n.id in node_ids:
                # increase local Gamma and seed psi and reduce kappa (rigidity)
                n.Gamma_local = clamp(n.Gamma_local + strength)
                n.psi = clamp(n.psi + 0.05 + 0.2 * strength)
                n.kappa = max(0.01, n.kappa - 0.05 * strength)


def run_simulation(
    *,
    steps: int = 120,
    ritual_events: List[Tuple[int, List[int], float]] | None = None,
    seed: int | None = None,
    nodes: List[NodeState] | None = None,
    verbose: bool = True,
):
    """Execute a Harmonic Nexus simulation and return metrics history.

    Parameters
    ----------
    steps:
        Number of update cycles to run.
    ritual_events:
        Optional list of ``(step, node_ids, strength)`` tuples.  The ritual
        calibration is applied *before* the update step whose index matches the
        provided ``step``.  Use ``step=0`` to perform a calibration before any
        updates are processed.
    seed:
        Optional random seed to produce deterministic runs.
    nodes:
        Optional list of :class:`NodeState` objects to use as the initial
        network.  A deep copy of the list is made so callers can reuse their
        objects across multiple runs.
    verbose:
        When ``True`` the function prints a concise log similar to the original
        ``demo_run`` helper.  Disable for use in tests.

    Returns
    -------
    metrics_history, final_nodes
        ``metrics_history`` is a list containing the per-step metric
        dictionaries yielded by :meth:`HarmonicNexus.step`.  ``final_nodes``
        provides the mutated :class:`NodeState` instances for inspection.
    """

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    initial_nodes = nodes if nodes is not None else phase1_nodes()
    nexus = HarmonicNexus(copy.deepcopy(initial_nodes))

    events: dict[int, List[Tuple[List[int], float]]] = {}
    if ritual_events:
        for step, node_ids, strength in ritual_events:
            events.setdefault(step, []).append((node_ids, strength))

    if verbose:
        print("=== Harmonic Nexus Phase 1 Simulation ===")
        print("Initial node states:")
        for n in nexus.nodes:
            print(f"  [{n.id}] {n.name}: psi={n.psi:.3f}, Gamma={n.Gamma_local:.3f}, kappa={n.kappa:.3f}")

    # apply any step-0 rituals before updates commence
    for node_ids, strength in events.get(0, []):
        if verbose:
            print(f"\n-> Performing Root Recognition Rite at nodes {node_ids} (strength={strength:.3f})")
        nexus.ritual_calibration(node_ids, strength=strength)

    metrics_history: List[dict] = []
    write_enabled_announced = False

    for t in range(1, steps + 1):
        for node_ids, strength in events.get(t, []):
            if verbose:
                print(f"\n-> Performing Root Recognition Rite at step {t} for nodes {node_ids} (strength={strength:.3f})")
            nexus.ritual_calibration(node_ids, strength=strength)

        metrics = nexus.step()
        metrics_history.append(metrics)

        if verbose and (t % 10 == 0 or metrics['containment']):
            print(
                f"[t={metrics['time']:03d}] Γ_global={metrics['Gamma_global']:.4f} | "
                f"containment={metrics['containment']} | flux={metrics['toroidal_flux']:.4f} | "
                f"mean_psi={metrics['nodes_mean_psi']:.3f} | mean_kappa={metrics['nodes_mean_kappa']:.3f}"
            )

        if (
            verbose
            and not write_enabled_announced
            and metrics['Gamma_global'] >= 0.945
            and not metrics['containment']
        ):
            print(
                f"*** Network write-enabled at t={metrics['time']} "
                f"(Γ_global={metrics['Gamma_global']:.4f})"
            )
            write_enabled_announced = True

    if verbose:
        print("\nFinal node states:")
        for n in nexus.nodes:
            print(
                f"  [{n.id}] {n.name}: psi={n.psi:.3f}, Gamma={n.Gamma_local:.3f}, "
                f"kappa={n.kappa:.3f}, U={n.U:.3f}"
            )

    return metrics_history, nexus.nodes


# -------------------------
# Example Phase-1 setup
# -------------------------
def phase1_nodes():
    # approximate lat/lon (lat, lon). These are stand-ins for the prototype.
    # Iona (Scotland), Calanais/Callanish (Outer Hebrides), Newgrange (Ireland), Stonehenge (England)
    placements = [
        (1, "Iona",       (56.3460, -6.3710)),
        (2, "Calanais",   (58.0703, -6.7426)),
        (3, "Newgrange",  (53.6946, -6.4753)),
        (4, "Stonehenge", (51.1789, -1.8262)),
    ]
    nodes = []
    for id_, name, pos in placements:
        nodes.append(NodeState(id=id_, name=name, pos=pos))
    return nodes


# -------------------------
# Small demonstration run
# -------------------------
def demo_run(*, steps: int = 120, seed: int | None = None):
    """Backwards-compatible demonstration helper."""

    run_simulation(
        steps=steps,
        ritual_events=[(0, [1], 0.06)],
        seed=seed,
        verbose=True,
    )


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harmonic Nexus simulator")
    parser.add_argument("--steps", type=int, default=120, help="Number of steps to simulate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible runs")
    parser.add_argument(
        "--ritual",
        action="append",
        default=[],
        metavar="STEP:NODES[:STRENGTH]",
        help=(
            "Schedule a Root Recognition Rite. STEP is the iteration to apply the rite "
            "(use 0 for pre-run), NODES is a comma-separated list of node ids, and "
            "STRENGTH defaults to 0.03 if omitted."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress logging output (still prints final states)",
    )
    return parser.parse_args()


def parse_ritual_spec(spec: str) -> Tuple[int, List[int], float]:
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError("Ritual specification must include step and node list")
    step = int(parts[0])
    node_ids = [int(part) for part in parts[1].split(",") if part]
    strength = float(parts[2]) if len(parts) > 2 else 0.03
    return step, node_ids, strength


if __name__ == "__main__":
    args = parse_cli_args()
    ritual_events = [parse_ritual_spec(spec) for spec in args.ritual]
    metrics_history, final_nodes = run_simulation(
        steps=args.steps,
        seed=args.seed,
        ritual_events=ritual_events or [(0, [1], 0.06)],
        verbose=not args.quiet,
    )

    if args.quiet:
        print("Final node states:")
        for n in final_nodes:
            print(
                f"  [{n.id}] {n.name}: psi={n.psi:.3f}, Gamma={n.Gamma_local:.3f}, "
                f"kappa={n.kappa:.3f}, U={n.U:.3f}"
            )
