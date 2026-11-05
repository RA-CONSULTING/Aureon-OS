"""`python -m aureon.evidence` rebuilds the committed evidence and checks it."""

from __future__ import annotations

import sys

from aureon.evidence.runner import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
