"""Graph analysis utilities for the wheel plan."""
from typing import Dict, List, Tuple

import networkx as nx

from .plan import PLAN, Node


def build_graph(plan: Dict[str, Node]) -> nx.DiGraph:
    """Construct a DAG from the plan definition."""

    graph = nx.DiGraph()
    for name, node in plan.items():
        graph.add_node(name, phase=node.phase, readiness=node.readiness)
    for name, node in plan.items():
        for dependency in node.deps:
            if dependency not in plan:
                raise KeyError(f"Dependency '{dependency}' not found for node '{name}'")
            graph.add_edge(dependency, name)
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("Graph has cycles; check dependencies.")
    return graph


def remaining_effort(graph: nx.DiGraph) -> Dict[str, float]:
    """Return remaining effort (1 - readiness) per node."""

    return {
        node: max(0.0, 1.0 - float(graph.nodes[node]["readiness"])) for node in graph.nodes()
    }


def critical_path(plan: Dict[str, Node]) -> List[str]:
    """Compute the critical path weighted by remaining effort."""

    graph = build_graph(plan)
    effort = remaining_effort(graph)
    for source, target in graph.edges():
        # Weight edges by the target node effort to bias toward unfinished work.
        weight = effort[target] if effort[target] > 0 else 1e-6
        graph.edges[source, target]["weight"] = weight
    return list(nx.dag_longest_path(graph, weight="weight"))


def phase_burndown(plan: Dict[str, Node]) -> Dict[int, Tuple[int, float]]:
    """Aggregate readiness metrics per phase."""

    phase_map: Dict[int, List[float]] = {}
    for node in plan.values():
        phase_map.setdefault(node.phase, []).append(node.readiness)
    return {
        phase: (len(values), sum(values) / len(values))
        for phase, values in sorted(phase_map.items())
    }


def dependency_pressure(plan: Dict[str, Node]) -> List[Tuple[str, int, int]]:
    """Return nodes sorted by downstream impact (out-degree)."""

    graph = build_graph(plan)
    rows = [
        (node, graph.in_degree(node), graph.out_degree(node)) for node in graph.nodes()
    ]
    rows.sort(key=lambda entry: (-entry[2], entry[1], entry[0]))
    return rows


__all__ = [
    "build_graph",
    "critical_path",
    "dependency_pressure",
    "phase_burndown",
    "remaining_effort",
    "PLAN",
    "Node",
]
