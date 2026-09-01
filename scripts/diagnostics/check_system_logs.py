#!/usr/bin/env python3
"""Legacy provider health check replaced by a non-mutating HOLD receipt."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.system-log-diagnostic-hold.v1",
                "decision": "HOLD",
                "reason": "protected_provider_diagnostic_boundary_required",
                "production_ready": False,
                "credentials_inspected": False,
                "exchange_client_constructed": False,
                "account_queried": False,
                "aureon_imported": False,
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
