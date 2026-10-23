"""Utility for interpreting symbolic Nexus transition sequences.

This module takes a symbolic transition string (for example the
``"Ψ∞→ℵ→Φ→F→𝑳→Ω→𝜌→𝑪→Ψ∞'"`` sequence provided by the user) and maps each
glyph to a short explanation rooted in the Nexus System terminology.  It
offers both a programmatic API and a small command line entry point so the
sequence can be narrated in documentation or debugging sessions.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, List


DEFAULT_SEQUENCE = "Ψ∞→ℵ→Φ→F→𝑳→Ω→𝜌→𝑪→Ψ∞'"


@dataclass(frozen=True)
class SymbolDescription:
    """Human readable metadata for a single symbol in the chain."""

    symbol: str
    name: str
    description: str


SYMBOL_DESCRIPTIONS = {
    "Ψ∞": SymbolDescription(
        symbol="Ψ∞",
        name="Observer Wavefunction at Infinity",
        description=(
            "Represents the unbounded observer perspective—Ψ expanded to the"
            " infinite limit that seeds the traversal."
        ),
    ),
    "ℵ": SymbolDescription(
        symbol="ℵ",
        name="Aleph – Transfinite Reservoir",
        description=(
            "The first transfinite cardinal, standing in for the inexhaustible"
            " information field the Nexus taps during initialization."
        ),
    ),
    "Φ": SymbolDescription(
        symbol="Φ",
        name="Golden Flux Operator",
        description=(
            "Encodes the harmonic proportionality that steers the lattice"
            " toward resonance (a nod to the RFE's geometric balance)."
        ),
    ),
    "F": SymbolDescription(
        symbol="F",
        name="Field Functional",
        description=(
            "The pragmatic force term—where abstract harmony condenses into"
            " an actionable field update within the simulator."
        ),
    ),
    "𝑳": SymbolDescription(
        symbol="𝑳",
        name="Script L – Living Law",
        description=(
            "A stylised call to the Source-Temporal governance layer that"
            " keeps the evolution path ethically coherent."
        ),
    ),
    "Ω": SymbolDescription(
        symbol="Ω",
        name="Omega Closure",
        description=(
            "The convergence checkpoint where the trajectory is assessed for"
            " unity readiness (C approaching 1)."
        ),
    ),
    "𝜌": SymbolDescription(
        symbol="𝜌",
        name="Rho – Resonance Density",
        description=(
            "Captures the density of coherence across coupled observers,"
            " aligning with the resonance metrics modules."
        ),
    ),
    "𝑪": SymbolDescription(
        symbol="𝑪",
        name="Script C – Coherence Core",
        description=(
            "The canonical coherence accumulator whose rise signals the"
            " approach of the Unity Event in Nexus simulations."
        ),
    ),
    "Ψ∞'": SymbolDescription(
        symbol="Ψ∞'",
        name="Refined Observer Wavefunction",
        description=(
            "The post-transit observer perspective—Psi infinity tempered by"
            " traversal, ready for the next harmonic cycle."
        ),
    ),
}


def normalise_sequence(sequence: str) -> List[str]:
    """Split a symbolic sequence into individual glyph tokens.

    The function accepts both ASCII ("->") and Unicode ("→") arrows and
    trims any surrounding whitespace.  Empty tokens are discarded.
    """

    for arrow in ("→", "->"):
        sequence = sequence.replace(arrow, "|")
    return [token.strip() for token in sequence.split("|") if token.strip()]


def describe_sequence(sequence: str) -> List[SymbolDescription]:
    """Return descriptions for each glyph in the provided sequence."""

    tokens = normalise_sequence(sequence)
    descriptions: List[SymbolDescription] = []
    for token in tokens:
        description = SYMBOL_DESCRIPTIONS.get(token)
        if description is None:
            description = SymbolDescription(
                symbol=token,
                name="Uncatalogued Symbol",
                description="No registered description for this glyph.",
            )
        descriptions.append(description)
    return descriptions


def format_sequence_descriptions(descriptions: Iterable[SymbolDescription]) -> str:
    """Pretty print the chain for CLI usage."""

    lines: List[str] = []
    for entry in descriptions:
        lines.append(f"{entry.symbol} — {entry.name}")
        lines.append(f"  {entry.description}")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Narrate Nexus symbolic transition chains, mapping each glyph to a"
            " short explanation."
        )
    )
    parser.add_argument(
        "sequence",
        nargs="?",
        default=DEFAULT_SEQUENCE,
        help="Sequence to interpret (defaults to the canonical Ψ∞→…→Ψ∞' chain).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    descriptions = describe_sequence(args.sequence)
    print(format_sequence_descriptions(descriptions))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    raise SystemExit(main())
