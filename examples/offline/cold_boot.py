"""Judge a containment cold-boot fixture. Does not boot a namespace and does not trade.

From the repository root::

    PYTHONPATH=. python3 examples/offline/cold_boot.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import offline

    return offline.run_cold_boot()


if __name__ == "__main__":
    raise SystemExit(main())
