"""Load the gallery market-series fixture. No live fetch and no order.

From the repository root::

    PYTHONPATH=. python3 examples/offline/load_market_series.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import offline

    return offline.run_market()


if __name__ == "__main__":
    raise SystemExit(main())
