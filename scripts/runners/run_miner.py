#!/usr/bin/env python3
"""Legacy runner replaced by a terminal protected-runtime HOLD receipt."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.run-miner-hold.v1",
                "decision": "HOLD",
                "reason": "protected_runtime_not_attested",
                "production_ready": False,
                "aureon_imported": False,
                "credentials_inspected": False,
                "child_process_started": False,
                "listener_started": False,
                "order_submitted": False,
                "network_accessed": False,
                "file_written": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
