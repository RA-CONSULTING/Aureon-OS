#!/usr/bin/env python3
"""Legacy Orca launcher replaced by a terminal protected-runtime HOLD."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.unified-orca-runner-hold.v1",
                "decision": "HOLD",
                "reason": "protected_orca_runtime_not_attested",
                "production_ready": False,
                "aureon_imported": False,
                "child_process_started": False,
                "listener_started": False,
                "browser_opened": False,
                "order_submitted": False,
                "network_accessed": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
