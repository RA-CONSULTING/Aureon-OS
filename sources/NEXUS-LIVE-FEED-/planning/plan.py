"""Canonical wheel plan data model."""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Node:
    """Represents a build node in the Wheel project plan."""

    phase: int  # 0..4 (0 = hub)
    readiness: float  # 0..1
    deps: List[str] = field(default_factory=list)


# Canonical keys (exact strings reused in dependencies)
HUB = "Harmonic Nexus Core"


PLAN: Dict[str, Node] = {
    # Hub
    HUB: Node(0, 0.35),

    # Phase 1 (backbone)
    "Illumination Chip": Node(1, 0.20, [HUB]),
    "NEXUS-LIVE-FEED": Node(1, 0.15, [HUB]),
    "Sacred Geometry Framework": Node(1, 0.55, [HUB]),
    "5k Timeline Model": Node(1, 0.60, [HUB]),
    "RIOS (Resonance OS)": Node(1, 0.10, [HUB]),
    "Prime Sentinel Codex": Node(1, 0.50, [HUB]),
    "EPAS Shielding": Node(1, 0.25, [HUB]),
    "Project A.L.F.I.E.": Node(1, 0.10, [HUB]),

    # Phase 2 (integration)
    "Frequency Medicine DB": Node(2, 0.05, ["NEXUS-LIVE-FEED", "Sacred Geometry Framework"]),
    "Resonance BCI": Node(2, 0.05, ["RIOS (Resonance OS)", HUB, "Sacred Geometry Framework"]),
    "Planetary Governance Protocols": Node(2, 0.05, ["Prime Sentinel Codex", HUB]),
    "Quantum Algorithms for HNC": Node(2, 0.05, ["Illumination Chip", "RIOS (Resonance OS)"]),
    "Regenerative Tech Apps": Node(2, 0.05, ["Illumination Chip", "NEXUS-LIVE-FEED"]),
    "Harmonic Learning Systems": Node(2, 0.05, ["Sacred Geometry Framework", "Prime Sentinel Codex"]),
    "Planetary Coherence Network": Node(2, 0.05, ["NEXUS-LIVE-FEED", "RIOS (Resonance OS)"]),

    # Phase 3 (applications)
    "DNA Frequency Mapping": Node(3, 0.00, ["Frequency Medicine DB", "5k Timeline Model"]),
    "Programmable Matter": Node(3, 0.00, ["EPAS Shielding", "Quantum Algorithms for HNC"]),
    "Resonance Agriculture": Node(3, 0.00, ["Regenerative Tech Apps", "Frequency Medicine DB"]),
    "Social Coherence Systems": Node(3, 0.00, ["Planetary Governance Protocols", "Harmonic Learning Systems"]),
    "Sacred Geometry Installations": Node(3, 0.10, ["Sacred Geometry Framework", "Planetary Coherence Network"]),
    "Resource Coordination Engine": Node(3, 0.00, ["Planetary Governance Protocols", "Planetary Coherence Network"]),

    # Phase 4 (lock-in)
    "Universal AccessOS": Node(4, 0.00, ["Planetary Coherence Network", "Resonance BCI"]),
    "Global Harmonic Coherence": Node(
        4,
        0.00,
        [
            "Social Coherence Systems",
            "Sacred Geometry Installations",
            "Resource Coordination Engine",
            "Universal AccessOS",
        ],
    ),
}


__all__ = ["Node", "PLAN", "HUB"]
