"""Simulated visuals and simulated capital stay off the default boot.

Harmonic Wave Simulation, the Internal Multiverse (10 worlds × $10), and the
mycelium $1000 hive seed are labeled simulated. They start only when
``AUREON_SIMULATED_BOOT`` is explicitly set. They are not exchange balances
and they are not live prices.
"""

from __future__ import annotations

import logging
import os

HARMONIC_WAVE_SIMULATION = "Harmonic Wave Simulation"
INTERNAL_MULTIVERSE = "Internal Multiverse"
MYCELIUM_HIVE_SEED = "mycelium hive seed ($1000)"

_ON = {"1", "true", "yes"}


def simulated_boot_enabled() -> bool:
    """Unset ``AUREON_SIMULATED_BOOT`` keeps simulated components off."""
    raw = os.getenv("AUREON_SIMULATED_BOOT", "0").strip().lower()
    return raw in _ON


def simulated_notice(name: str, detail: str) -> str:
    return f"SIMULATED {name} — {detail} — not live capital"


def take_simulated(name: str, detail: str) -> bool:
    """Log the simulated label at debug. Return True only when the operator opted in."""
    notice = simulated_notice(name, detail)
    if simulated_boot_enabled():
        logging.debug("%s (AUREON_SIMULATED_BOOT=1)", notice)
        return True
    logging.debug("%s — skipped on the default boot", notice)
    return False


RANDOM_DASHBOARD = "random dashboard generator"


def random_dashboard_allowed() -> bool:
    """Pages that draw invented readings stay off unless the operator opted in."""
    return take_simulated(RANDOM_DASHBOARD, "invented readings are not a live bus")
