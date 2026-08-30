"""aureon.queen — Queen AI decision layer.

Implements the hive-mind architecture, neural decision networks, cognitive
narrator, and autonomous power modules that form the central decision
authority. The Queen Layer sits at the top of the system — she boots first,
activates all subsystems beneath her, and monitors them through the ThoughtBus.
"""

from aureon.queen.queen_layer import QueenLayer, boot_queen_layer, get_queen_layer
from aureon.queen.queen_process_roof import (
    QueenProcessRoof,
    bind_queen_process_roof,
    configure_canonical_queen_process_roof,
    discover_queen_process_manifest,
    get_canonical_queen_process_roof,
)

__all__ = [
    "QueenLayer",
    "QueenProcessRoof",
    "bind_queen_process_roof",
    "boot_queen_layer",
    "configure_canonical_queen_process_roof",
    "discover_queen_process_manifest",
    "get_canonical_queen_process_roof",
    "get_queen_layer",
]
