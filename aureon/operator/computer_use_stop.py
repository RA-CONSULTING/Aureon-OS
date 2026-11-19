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


def computer_use_stop_path() -> Path:
    """Path of the human stop file. This function does not create it."""

    override = os.environ.get(STOP_ENV, "").strip()
    if override:
        return Path(override)
    return DEFAULT_STOP


def computer_use_stopped() -> bool:
    """True when the human stop file is already on disk."""

    return computer_use_stop_path().is_file()
