"""Plug-and-play entry to Aureon's self-repair.

    python -m aureon_fusion.repair --root /path/to/project

The project needs pytest tests. The repair edits implementation files, reruns
the tests, and commits on a local branch named aureon-self-repair/<timestamp>.
It stays disabled unless AUREON_SELF_REPAIR_ENABLE=1 and the project has
state/self_repair_config.json with {"enabled": true}. A missing config stops
it. The kill variable and the kill file do not. Explicit guarded mode refuses
live-trading flags, evidence gates, position sizing, and credential files
before a patch is applied. The public default is full. See AUTONOMY.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

_UPSTREAM = Path(__file__).resolve().parents[1] / "aureon-os-upstream"
if not (_UPSTREAM / "aureon" / "autonomous" / "aureon_sandbox_self_repair.py").is_file():
    _UPSTREAM = Path(__file__).resolve().parents[1]
if str(_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM))

from aureon.autonomous.aureon_sandbox_self_repair import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
