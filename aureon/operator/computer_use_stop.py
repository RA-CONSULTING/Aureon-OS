"""Human stop file for computer, shell, and chat actions.

``state/computer_use.stop`` is created by a person. Aureon reads it and does
not create it. While the file exists, local actions and the queen action
bridge stay dry-run. Trading gates are a different switch.
"""

from __future__ import annotations

import os
from pathlib import Path

STOP_ENV = "AUREON_COMPUTER_USE_STOP_FILE"
DEFAULT_STOP = Path("state") / "computer_use.stop"


def stop_path() -> Path:
    """Resolve the human stop file. This function does not create it."""

    override = os.environ.get(STOP_ENV, "").strip()
    if override:
        return Path(override)
    return DEFAULT_STOP


def is_stopped() -> bool:
    """True when the human stop file is already on disk."""

    return stop_path().is_file()
