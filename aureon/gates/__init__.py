"""The Queen's switchboard — the logic gates every lane passes through.

- :mod:`aureon.gates.panel` convenes the nine Auris nodes over the live
  organism, wiring a voter that had never been called.
- :mod:`aureon.gates.switchboard` asks each gate its question and answers
  ADVANCE / REDO / HOLD, grounded in coherence, divergence, the panel and the
  Queen's conscience.

Domain-agnostic by design: trading was lane one, grants are lane two, and the
gates ask both the same questions.
"""

from aureon.gates.panel import PanelReading, auris_panel
from aureon.gates.switchboard import (
    ADVANCE,
    DEFAULT_CHAIN,
    HOLD,
    REDO,
    Gate,
    GateReading,
    GateVerdict,
    evaluate,
    read_organism,
    run_chain,
)

__all__ = [
    "auris_panel", "PanelReading",
    "Gate", "GateReading", "GateVerdict", "DEFAULT_CHAIN",
    "ADVANCE", "REDO", "HOLD", "evaluate", "read_organism", "run_chain",
]
