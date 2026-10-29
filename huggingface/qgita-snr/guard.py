"""Space bootstrap. Trading imports are refused. No secret file is read."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

SPACE_DIR = Path(__file__).resolve().parent
os.chdir(SPACE_DIR)

os.environ["AUREON_AUDIT_MODE"] = "1"
os.environ["AUREON_DISABLE_REAL_ORDERS"] = "1"
os.environ["AUREON_DISABLE_LIVE_BACKGROUND_STARTUP"] = "1"
os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_ENABLE_AUTONOMOUS_CONTROL"] = "0"
os.environ["AUREON_ACTIVATE_ON_IMPORT"] = "0"
os.environ["GRADIO_ANALYTICS_ENABLED"] = "0"
os.environ.setdefault(
    "AUREON_THOUGHT_BUS_PATH",
    str(Path(tempfile.gettempdir()) / "aureon-hf-space-bus.jsonl"),
)

_BLOCKED = (
    "aureon.exchanges",
    "aureon.trading",
    "unified_margin_trader",
    "aureon.bots",
    "aureon.bots_intelligence",
    "aureon.bridges",
    "aureon.scanners",
)
REFUSAL = (
    "Refused imports: aureon.exchanges, aureon.trading, unified_margin_trader, "
    "aureon.bots, aureon.bots_intelligence, aureon.bridges, aureon.scanners. "
    "No keys are present."
)


class _BlockTrading:
    def find_spec(self, fullname, path, target=None):
        for prefix in _BLOCKED:
            if fullname == prefix or fullname.startswith(prefix + "."):
                raise ImportError(f"{REFUSAL} Refused: {fullname}")
        return None


sys.meta_path.insert(0, _BlockTrading())


def _repo_root() -> Path | None:
    for parent in (SPACE_DIR, *SPACE_DIR.parents):
        if (parent / "aureon" / "core" / "hnc_field.py").is_file():
            return parent
    return None


_ROOT = _repo_root()
if _ROOT is not None and str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

UNAVAILABLE = "unavailable"
LICENCE = "MIT"
COMMIT = "a00f744d2e686e916e45b81dd4222408c368e305"


def show(value: object) -> object:
    if value is None:
        return UNAVAILABLE
    return value
