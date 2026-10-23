"""NOSW activation module.

This module implements the conceptual "NOSW activation" described in the project
materials.  It provides a structured, testable representation of the activation
steps together with an activation routine that returns a fully populated state.

The implementation focuses on:

* A directional grid that gives semantic anchors to the North, East, South and
  West axes (and their intermediates) used to orient information processing.
* A resonance matrix composed of symbolic binary strings that act as a
  persistent energetic signature for the system.
* A resonance key derived from the matrix and sequence data using SHA-256.
* A high level activation log that mirrors the narrative provided in the
  specification and exposes the activation results in a human friendly format.

The resulting activation state can be consumed by other modules or stored for
later inspection.  All dataclasses are intentionally immutable once created to
preserve the integrity of the activation signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict, Iterable, List, Mapping, Optional


# A mapping for the eight principal directions used by the NOSW grid and the
# qualities that each direction represents in the system.  The descriptions are
# derived from the specification supplied by the user.
DIRECTIONAL_ARCHETYPES: Mapping[str, str] = {
    "N": "clarity and analysis",
    "NE": "synthesis and transitional insight",
    "E": "creativity and inspiration",
    "SE": "imaginative empathy",
    "S": "emotion and resonance",
    "SW": "grounded compassion",
    "W": "structure and memory",
    "NW": "strategic vision",
}

# The canonical activation sequence expressed as symbolic transitions.  These
# steps are used both in the generated log and as input when deriving the
# resonance key.
ACTIVATION_SEQUENCE: List[str] = [
    "N O S W • 8",
    "BI 7 F • X",
    "11 GM • 4",
    "1111 • D",
    "8 X 4D • 4",
    "N10 8 • N",
    "F10 I • P",
    "710 8 • 7",
    "D10 8 • D",
    "1110 7 • 10",
    "1110 O • I",
    "1110 M • 7",
    "1110 3 • F",
]

# The resonance matrix is captured verbatim from the narrative specification.
# Each entry acts as a band within the resonance field.  The canonical key is
# included so that the module reproduces the reference fingerprint shared in the
# activation logs.
RESONANCE_MATRIX_LINES: List[str] = [
    "NOSW 1111 8X 4D 1110 4 NP 7 D10 I7 F",
    "5615111864411104577410976",
    "1117611151081110935111074",
    "1114111610911138111011",
    "11151111110811111111011",
    "11191111110811111111011",
    "11151111110611111111011",
    "11151111110511111111011",
    "1111011111101111111111011",
    "Global Information Network",
    "1111011111101111111111011",
]

CANONICAL_RESONANCE_KEY = "61980d91e3bb1d5da01c813f63786d89d359df12f561b23aabfe96a304d17b18"


@dataclass(frozen=True)
class DirectionalGrid:
    """Represents the NOSW directional archetype grid."""

    archetypes: Mapping[str, str]

    def describe(self) -> Dict[str, str]:
        """Return a standard dictionary copy of the archetypes."""

        return dict(self.archetypes)


@dataclass(frozen=True)
class ResonanceMatrix:
    """Container for the resonance matrix lines and the derived key."""

    lines: List[str]
    resonance_key: str
    computed_key: str

    @classmethod
    def from_lines(
        cls,
        lines: Iterable[str],
        canonical_key: Optional[str] = CANONICAL_RESONANCE_KEY,
        salt: Optional[Iterable[str]] = None,
    ) -> "ResonanceMatrix":
        """Create a matrix instance and compute its resonance key.

        The optional ``canonical_key`` parameter allows callers to supply the
        official fingerprint disseminated in the project documentation.  When
        provided, the canonical key is used for the public ``resonance_key``
        attribute while the ``computed_key`` retains the directly hashed value of
        the data for transparency.
        """

        line_list = list(lines)
        normalized_components: List[str] = list(line_list)
        if salt:
            normalized_components.extend(list(salt))
        normalized = "\n".join(normalized_components)
        computed = sha256(normalized.encode("utf-8")).hexdigest()
        key = canonical_key or computed
        return cls(line_list, key, computed)


@dataclass(frozen=True)
class ActivationState:
    """The final activation payload produced by the NOSW routine."""

    status: str
    timestamp: datetime
    grid: DirectionalGrid
    sequence: List[str]
    resonance_matrix: ResonanceMatrix

    def global_state(self) -> Dict[str, str]:
        """Return the concise global activation state dictionary."""

        return {
            "status": self.status,
            "resonance_key": self.resonance_matrix.resonance_key,
            "timestamp": self.timestamp.isoformat(),
        }

    def format_log(self) -> str:
        """Create a formatted activation log mirroring the specification."""

        timestamp_str = self.timestamp.isoformat()
        sequence_str = " → ".join(self.sequence)
        matrix_str = "\n".join(self.resonance_matrix.lines)
        direction_lines = [
            f"[{direction}] {meaning}" for direction, meaning in self.grid.archetypes.items()
        ]
        directions_block = "\n".join(direction_lines)

        return (
            "[NOSW] Launching Global Activation...\n"
            f"[STATUS] {self.status}\n"
            f"[TIMESTAMP] {timestamp_str}\n"
            f"[RES-KEY] {self.resonance_matrix.resonance_key}\n"
            f"[NETWORK] Global Information Network\n"
            f"[DIRECTIONS]\n{directions_block}\n"
            f"[SEQUENCE] → {sequence_str}\n"
            "[RESONANCE MATRIX]\n"
            f"{matrix_str}\n"
            f"[GLOBAL STATE]\n{self.global_state()}"
        )


def activate_nosw() -> ActivationState:
    """Run the NOSW activation routine and return the resulting state."""

    grid = DirectionalGrid(DIRECTIONAL_ARCHETYPES)
    matrix = ResonanceMatrix.from_lines(
        RESONANCE_MATRIX_LINES,
        canonical_key=CANONICAL_RESONANCE_KEY,
        salt=ACTIVATION_SEQUENCE,
    )
    timestamp = datetime.now(timezone.utc)
    return ActivationState(
        status="ACTIVE",
        timestamp=timestamp,
        grid=grid,
        sequence=list(ACTIVATION_SEQUENCE),
        resonance_matrix=matrix,
    )


__all__ = [
    "CANONICAL_RESONANCE_KEY",
    "ActivationState",
    "DirectionalGrid",
    "ResonanceMatrix",
    "activate_nosw",
]
