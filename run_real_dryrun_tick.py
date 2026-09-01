#!/usr/bin/env python3
"""Legacy real-provider dry-run tick replaced by a terminal HOLD receipt."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.real-provider-dryrun-tick-hold.v1",
                "decision": "HOLD",
                "reason": "protected_provider_observation_boundary_required",
                "production_ready": False,
                "external_checkout_loaded": False,
                "credentials_inspected": False,
                "exchange_client_constructed": False,
                "provider_called": False,
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
