"""Alignment entry points. Calls go through dispatch, so the pin and the fence stay.

Fixtures are the inputs in tests/stress/stress_test_inhouse_ai.py test_harmonic_math.
No formula was added. A missing or non-finite input is unavailable.
"""

from __future__ import annotations

import json
from typing import Any

from aureon_public.body import _unavailable, dispatch
from aureon_public.quiet import quiet
from aureon_public.tools import _finite

# Inputs copied from tests/stress/stress_test_inhouse_ai.py::test_harmonic_math.
SPLIT_SIGNALS = ["BUY", "BUY", "SELL", "SELL", "NEUTRAL", "NEUTRAL"]
AGREE_SIGNALS = ["BUY", "BUY", "BUY", "BUY", "BUY", "BUY"]
ALIGNED_PHASES = [0.0, 0.0, 0.0]
PILLAR_FREQUENCIES = {
    "Nexus": 432.0,
    "Omega": 432.0,
    "Infinite": 528.0,
    "Piano": 396.0,
    "QGITA": 528.0,
    "Auris": 741.0,
}
PERFECT_STACK = [
    {
        "pillar": f"P{index}",
        "signal": "BUY",
        "confidence": 0.95,
        "coherence": 0.96,
        "frequency_hz": 528.0,
    }
    for index in range(6)
]
GEOMETRIC_ONES = [1.0, 1.0, 1.0, 1.0]


def _loads(text: str, kind: type) -> Any | str:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return "arguments are not JSON"
    if not isinstance(loaded, kind):
        return "arguments have the wrong shape"
    return loaded


def _call(module: str, symbol: str, arguments: dict[str, Any]) -> str:
    return dispatch(module, symbol, arguments, server="public")


@quiet
def alignment_signal_consensus(signals_json: str = "") -> str:
    """compute_signal_consensus. Provenance: cited.

    The default list is the three-way split in test_harmonic_math. No pillar agent is built.

    Args:
        signals_json: JSON list of signal names. Empty uses the split fixture. Label: cited.
    """

    raw = signals_json.strip() or json.dumps(SPLIT_SIGNALS)
    parsed = _loads(raw, list)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    if not parsed or not all(isinstance(item, str) for item in parsed):
        return _unavailable("signals must be a non-empty list of strings")
    return _call(
        "alignment/harmonic_resonance.py",
        "compute_signal_consensus",
        {"signals": parsed},
    )


@quiet
def alignment_consonance_read(ratio: float = 1.0) -> str:
    """consonance_score. Provenance: cited.

    This is the inventory entry point, called through the pin check. The helper
    alignment_consonance is a separate tool and is not this call.

    Args:
        ratio: Frequency ratio. The default 1.0 is unison in test_harmonic_math. Label: cited.
    """

    number = _finite(ratio)
    if number is None:
        return _unavailable("ratio is missing")
    return _call("alignment/harmonic_resonance.py", "consonance_score", {"ratio": number})


@quiet
def alignment_frequency_harmony(frequencies_json: str = "") -> str:
    """analyse_frequency_harmony. Provenance: cited.

    fundamental_hz is omitted, so the function uses its own FUNDAMENTAL_HZ.
    The default map is the six pillar frequencies in test_harmonic_math.

    Args:
        frequencies_json: JSON object of name to Hz. Empty uses that map. Label: cited.
    """

    raw = frequencies_json.strip() or json.dumps(PILLAR_FREQUENCIES)
    parsed = _loads(raw, dict)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    frequencies: dict[str, float] = {}
    for key, value in parsed.items():
        number = _finite(value)
        if number is None:
            return _unavailable(f"{key} is not a frequency")
        frequencies[str(key)] = number
    return _call(
        "alignment/harmonic_resonance.py",
        "analyse_frequency_harmony",
        {"pillar_frequencies": frequencies},
    )


@quiet
def alignment_phase_coherence(phases_json: str = "") -> str:
    """compute_phase_coherence. Provenance: cited.

    The default phases are the aligned triple in test_harmonic_math.

    Args:
        phases_json: JSON list of radians. Empty uses that triple. Label: cited.
    """

    raw = phases_json.strip() or json.dumps(ALIGNED_PHASES)
    parsed = _loads(raw, list)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    phases: list[float] = []
    for value in parsed:
        number = _finite(value)
        if number is None:
            return _unavailable("phases must be numbers")
        phases.append(number)
    return _call(
        "alignment/harmonic_resonance.py",
        "compute_phase_coherence",
        {"phases_rad": phases},
    )


@quiet
def alignment_derive_phase(frequency_hz: float = 528.0, t: float = 0.0, signal: str = "BUY") -> str:
    """derive_phase. Provenance: cited.

    528 Hz is FUNDAMENTAL_HZ in harmonic_resonance.py. t is 0 so the drift term is zero.
    BUY, SELL, and any other string are the branches already in derive_phase.

    Args:
        frequency_hz: Pillar frequency in Hz. Label: cited, derive_phase.
        t: Time in seconds. Label: cited, derive_phase.
        signal: BUY, SELL, or another string. Label: cited, derive_phase.
    """

    frequency = _finite(frequency_hz)
    moment = _finite(t)
    if frequency is None or moment is None:
        return _unavailable("frequency_hz or t is missing")
    if not isinstance(signal, str) or not signal.strip():
        return _unavailable("signal is missing")
    return _call(
        "alignment/harmonic_resonance.py",
        "derive_phase",
        {"frequency_hz": frequency, "t": moment, "signal": signal},
    )


@quiet
def alignment_geometric_mean(values_json: str = "") -> str:
    """geometric_mean. Provenance: cited.

    The default is the four ones in test_harmonic_math.

    Args:
        values_json: JSON list of numbers. Empty uses that list. Label: cited.
    """

    raw = values_json.strip() or json.dumps(GEOMETRIC_ONES)
    parsed = _loads(raw, list)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    values: list[float] = []
    for value in parsed:
        number = _finite(value)
        if number is None:
            return _unavailable("values must be numbers")
        values.append(number)
    return _call("alignment/harmonic_resonance.py", "geometric_mean", {"values": values})


@quiet
def alignment_full_analysis(pillar_results_json: str = "", t: float = 0.0) -> str:
    """full_harmonic_analysis. Provenance: cited.

    t is passed, so the function does not read the clock. The default stack is the
    perfect six-pillar stack in test_harmonic_math, including frequency_hz 528.

    Args:
        pillar_results_json: JSON list of pillar result objects. Empty uses that stack. Label: cited.
        t: Time passed to full_harmonic_analysis. Label: cited.
    """

    moment = _finite(t)
    if moment is None:
        return _unavailable("t is missing")
    raw = pillar_results_json.strip() or json.dumps(PERFECT_STACK)
    parsed = _loads(raw, list)
    if isinstance(parsed, str):
        return _unavailable(parsed)
    if not all(isinstance(item, dict) for item in parsed):
        return _unavailable("pillar_results must be a list of objects")
    return _call(
        "alignment/harmonic_resonance.py",
        "full_harmonic_analysis",
        {"pillar_results": parsed, "t": moment},
    )


@quiet
def alignment_harmonic_to_dict() -> str:
    """HarmonicAnalysis.to_dict on the dataclass defaults. Provenance: cited.

    The class has no constructor body. Defaults are the literals in the class.
    No pillar agent is built.

    Args:
        none: This tool takes no inputs. Label: cited, HarmonicAnalysis.to_dict.
    """

    return _call("alignment/harmonic_resonance.py", "HarmonicAnalysis.to_dict", {})


@quiet
def alignment_cycle_to_dict(cycle_id: str = "fixed", timestamp: float = 0.0) -> str:
    """AlignmentCycleResult.to_dict with a fixed id and timestamp. Provenance: cited.

    The dataclass defaults would call uuid and the clock. Those arguments are passed
    so this call does not. Other fields stay the dataclass defaults.

    Args:
        cycle_id: Passed as the constructor cycle_id. Label: cited.
        timestamp: Passed as the constructor timestamp. Label: cited.
    """

    moment = _finite(timestamp)
    if moment is None or not isinstance(cycle_id, str) or not cycle_id:
        return _unavailable("cycle_id or timestamp is missing")
    return _call(
        "alignment/pillar_alignment.py",
        "AlignmentCycleResult.to_dict",
        {"init": {"cycle_id": cycle_id, "timestamp": moment}},
    )


@quiet
def alignment_directive_to_dict(directive_id: str = "fixed", timestamp: float = 0.0) -> str:
    """MasterDirective.to_dict with a fixed id and timestamp. Provenance: cited.

    The dataclass defaults would call uuid and the clock. Those arguments are passed
    so this call does not. Other fields stay the dataclass defaults, including
    dominant_frequency_hz = FUNDAMENTAL_HZ.

    Args:
        directive_id: Passed as the constructor directive_id. Label: cited.
        timestamp: Passed as the constructor timestamp. Label: cited.
    """

    moment = _finite(timestamp)
    if moment is None or not isinstance(directive_id, str) or not directive_id:
        return _unavailable("directive_id or timestamp is missing")
    return _call(
        "alignment/unified_directive.py",
        "MasterDirective.to_dict",
        {"init": {"directive_id": directive_id, "timestamp": moment}},
    )


@quiet
def alignment_pillar_factory() -> str:
    """get_pillar_alignment. Provenance: cited.

    The function's own default config sets auto_load_pillars false, so this call
    does not load pillar agents. The constructor still runs its thought-bus wire.
    If that call fails, the result is unavailable. No order is sent.

    Args:
        none: This tool takes no inputs. Label: cited, get_pillar_alignment.
    """

    return _call("alignment/pillar_alignment.py", "get_pillar_alignment", {})


@quiet
def alignment_unified_factory() -> str:
    """get_unified_directive. Provenance: cited.

    The constructor auto-wires and swallows a missing queen bridge, miner bridge,
    or thought bus. This tool does not fill those in. If the call fails, the
    result is unavailable. No order is sent.

    Args:
        none: This tool takes no inputs. Label: cited, get_unified_directive.
    """

    return _call("alignment/unified_directive.py", "get_unified_directive", {})


TOOLS: list[Any] = [
    alignment_signal_consensus,
    alignment_consonance_read,
    alignment_frequency_harmony,
    alignment_phase_coherence,
    alignment_derive_phase,
    alignment_geometric_mean,
    alignment_full_analysis,
    alignment_harmonic_to_dict,
    alignment_cycle_to_dict,
    alignment_directive_to_dict,
    alignment_pillar_factory,
    alignment_unified_factory,
]
