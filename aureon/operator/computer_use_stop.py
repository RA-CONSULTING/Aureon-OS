"""Human stop file for computer, shell, and chat actions.

``state/computer_use.stop`` under the repository root is created by a person.
The path is absolute, taken from this package's location, so the working
directory does not matter. ``AUREON_COMPUTER_USE_STOP_FILE`` overrides it.
Aureon reads the file and does not create it. While the file exists, local
actions and the queen chat bridge stay dry-run. Trading gates are a different
switch.
"""

from __future__ import annotations

import os
from pathlib import Path

STOP_ENV = "AUREON_COMPUTER_USE_STOP_FILE"
# aureon/operator/computer_use_stop.py -> repository root
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STOP = _REPO_ROOT / "state" / "computer_use.stop"


def stop_path() -> Path:
    """Resolve the human stop file. This function does not create it.

    The default is an absolute path at the repository root. An environment
    override is used as given, including a relative path.
    """

    override = os.environ.get(STOP_ENV, "").strip()
    if override:
        return Path(override)
    return DEFAULT_STOP


def is_stopped() -> bool:
    """True when the stop file is present, or when the disk cannot be read.

    An ``OSError`` fails closed: a process that cannot tell whether the human
    asked it to stop treats the stop as present. This function does not create
    the file.
    """

    try:
        return stop_path().is_file()
    except OSError:
        return True
