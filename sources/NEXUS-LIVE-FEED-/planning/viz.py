"""Visualization helpers for the wheel project plan."""
from typing import Dict, Tuple

import matplotlib.pyplot as plt

from .ops import build_graph, critical_path, dependency_pressure, phase_burndown
from .plan import PLAN, Node


def plot_gantt(plan: Dict[str, Node] = PLAN) -> None:
    """Render a Gantt-like view of readiness by phase."""

    graph = build_graph(plan)
    rows = [
        (name, graph.nodes[name]["phase"], graph.nodes[name]["readiness"])
        for name in graph.nodes()
    ]
    rows.sort(key=lambda entry: (entry[1], -entry[2], entry[0]))

    fig, axis = plt.subplots()
    for index, (name, phase, readiness) in enumerate(rows):
        axis.barh(index, readiness, left=phase, align="center")
        axis.text(phase + readiness + 0.02, index, f"{name} ({readiness:.2f})", va="center", fontsize=7)
    axis.set_xlabel("Phase (0..4)")
    axis.set_yticks([])
    axis.set_title("Wheel Readiness by Phase")
    plt.tight_layout()
    plt.show()


def plot_dependency_pressure(plan: Dict[str, Node] = PLAN) -> None:
    """Plot dependency pressure scatter (in vs out degree)."""

    data = dependency_pressure(plan)
    x_values = [item[1] for item in data]
    y_values = [item[2] for item in data]

    fig, axis = plt.subplots()
    axis.scatter(x_values, y_values)
    for name, indegree, outdegree in data:
        axis.text(indegree + 0.05, outdegree, name, fontsize=6)
    axis.set_xlabel("Dependencies required (in-degree)")
    axis.set_ylabel("Downstream dependents (out-degree)")
    axis.set_title("Dependency Pressure Map")
    plt.tight_layout()
    plt.show()


def console_health(plan: Dict[str, Node] = PLAN) -> None:
    """Print headline metrics for quick inspection."""

    print("Critical path:")
    print(" -> ".join(critical_path(plan)))
    print()

    print("Phase burndown (count, avg readiness):")
    for phase, (count, average) in phase_burndown(plan).items():
        print(f"  Phase {phase}: {count} nodes, avg readiness {average:.2f}")


__all__ = [
    "console_health",
    "plot_dependency_pressure",
    "plot_gantt",
]


if __name__ == "__main__":
    console_health()
    plot_gantt()
    plot_dependency_pressure()
