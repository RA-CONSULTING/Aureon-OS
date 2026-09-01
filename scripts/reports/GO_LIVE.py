#!/usr/bin/env python3
"""Legacy go-live entrypoint replaced by a terminal release HOLD receipt."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.go-live-hold.v1",
                "decision": "HOLD",
                "reason": "live_execution_not_authorized_or_protected",
                "production_ready": False,
                "live_execution_authorized": False,
                "exchange_client_imported": False,
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
