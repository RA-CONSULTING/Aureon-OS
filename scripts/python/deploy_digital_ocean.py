#!/usr/bin/env python3
"""Legacy deployment compatibility surface; remote activation is on HOLD."""

from __future__ import annotations

import json

SCHEMA = "aureon.legacy-deployment-hold.v1"


def main() -> int:
    """Emit a machine-readable refusal without importing or starting Aureon."""
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "decision": "HOLD",
                "reason": "complete_native_protection_boundary_required",
                "production_ready": False,
                "aureon_imported": False,
                "child_process_started": False,
                "file_written": False,
                "network_accessed": False,
                "listener_started": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
