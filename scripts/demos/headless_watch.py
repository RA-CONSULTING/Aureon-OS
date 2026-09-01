#!/usr/bin/env python3
"""Fail-closed replacement for the unreleased headless ICS watcher.

The historical script patched autonomy and started a daemon thread during
module import. The public entrypoint now performs only the inert ICS release
preflight and never imports autonomy, provider, network, or thread runtimes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aureon.core.integrated_cognitive_system import (  # noqa: E402
    integrated_cognitive_system_security_preflight,
)


def main() -> int:
    """Report HOLD without creating the former autonomy or tick threads."""

    status = integrated_cognitive_system_security_preflight()
    print(json.dumps(status, sort_keys=True))
    return 0 if status.get("production_ready") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
