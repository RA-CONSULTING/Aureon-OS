"""Simple readiness simulation helpers."""
from copy import deepcopy
from typing import Dict

import numpy as np
import networkx as nx

from .ops import build_graph, phase_burndown
from .plan import PLAN, Node


def _dependencies_ready(
    graph: nx.DiGraph, plan: Dict[str, Node], name: str, threshold: float = 0.60
) -> bool:
    return all(plan[dependency].readiness >= threshold for dependency in graph.predecessors(name))


def step(plan: Dict[str, Node], mean: float = 0.05, stddev: float = 0.02) -> Dict[str, Node]:
    """Advance readiness with a Gaussian increment when gates are satisfied."""

    updated = deepcopy(plan)
    graph = build_graph(plan)
    for name, node in plan.items():
        increment = 0.0
        if node.phase == 0:
            increment = max(0.0, np.random.normal(mean, stddev))
        else:
            if _dependencies_ready(graph, plan, name):
                increment = max(0.0, np.random.normal(mean, stddev))
        new_value = min(1.0, node.readiness + increment)
        updated[name] = Node(node.phase, new_value, list(node.deps))
    return updated


def simulate(months: int = 24, trials: int = 100) -> Dict[int, np.ndarray]:
    """Run a Monte Carlo readiness projection."""

    readiness_by_phase: Dict[int, list] = {}
    for _ in range(trials):
        plan = deepcopy(PLAN)
        for _ in range(months):
            plan = step(plan)
        burndown = phase_burndown(plan)
        for phase, (_, average) in burndown.items():
            readiness_by_phase.setdefault(phase, []).append(average)
    return {phase: np.array(values) for phase, values in readiness_by_phase.items()}


def summarize_simulation(data: Dict[int, np.ndarray]) -> None:
    """Print summary stats for simulation results."""

    for phase in sorted(data):
        series = data[phase]
        mean = series.mean()
        p10 = np.percentile(series, 10)
        p90 = np.percentile(series, 90)
        print(f"Phase {phase}: mean {mean:.2f}, p10 {p10:.2f}, p90 {p90:.2f}")


def final_lock_in(plan: Dict[str, Node]) -> float:
    """Return readiness for the lock-in objective."""

    return plan["Global Harmonic Coherence"].readiness


__all__ = [
    "final_lock_in",
    "simulate",
    "step",
    "summarize_simulation",
]


if __name__ == "__main__":
    results = simulate()
    summarize_simulation(results)
