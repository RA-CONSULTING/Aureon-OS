"""Algorithmic nodes — named seats mapped onto modules the organism already has.

metacognition, queen reasoning, logic, the neural chain, lighthouse, QGITA,
and mycelium each have a node. The node publishes its seat on the thought
bus; it does not invent a goal or place an order.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlgorithmicNode:
    name: str
    module: str
    role: str


NODES: tuple[AlgorithmicNode, ...] = (
    AlgorithmicNode("metacognition", "aureon.core.metacognition_monitor", "metacognition"),
    AlgorithmicNode("queen_reasoning", "aureon.queen.queen_layer", "reasoning"),
    AlgorithmicNode("logic", "aureon.core.deterministic_systems", "logic"),
    AlgorithmicNode("neural_chain", "aureon.utils.aureon_queen_unified_neural_chain", "neural"),
    AlgorithmicNode("lighthouse", "aureon.analytics.lighthouse_metrics", "lighthouse"),
    AlgorithmicNode("qgita", "aureon.wisdom.aureon_qgita", "qgita"),
    AlgorithmicNode("mycelium", "aureon.core.aureon_mycelium", "mycelium"),
    AlgorithmicNode("baton_relay", "aureon.core.baton_relay_monitor", "baton_relay"),
    AlgorithmicNode("council", "aureon.swarm.druidic_council", "council"),
)


def list_nodes() -> list[dict[str, str]]:
    return [
        {"name": item.name, "module": item.module, "role": item.role}
        for item in NODES
    ]
