"""Run brain proof on the gallery market-series fixture. No live fetch and no order.

From the repository root::

    PYTHONPATH=. python3 examples/offline/run_brain_proof.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import offline

    return offline.run_brain()


if __name__ == "__main__":
    raise SystemExit(main())
