from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.symbolic_sequence_mapper import (  # noqa: E402
    DEFAULT_SEQUENCE,
    describe_sequence,
    format_sequence_descriptions,
)


def test_describe_sequence_returns_known_entries():
    descriptions = describe_sequence(DEFAULT_SEQUENCE)
    assert len(descriptions) == 9
    assert descriptions[0].symbol == "Ψ∞"
    assert "observer perspective" in descriptions[0].description.lower()


def test_format_sequence_descriptions_produces_readable_text():
    output = format_sequence_descriptions(describe_sequence(DEFAULT_SEQUENCE))
    assert "Ψ∞ — Observer Wavefunction at Infinity" in output
    assert "Ψ∞' — Refined Observer Wavefunction" in output
