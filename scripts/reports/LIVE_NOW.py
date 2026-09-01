#!/usr/bin/env python3
"""Terminal HOLD facade for the archived unprotected live-trading loop."""

from __future__ import annotations

import json


def main() -> int:
    """Emit a non-mutating release receipt and refuse provider access."""
    print(
        json.dumps(
            {
                "schema": "aureon.live-now-hold.v1",
                "decision": "HOLD",
                "reason": "registered_protected_execution_route_unavailable",
                "production_ready": False,
                "provider_accessed": False,
                "credentials_loaded": False,
                "order_submitted": False,
                "file_written": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
