#!/usr/bin/env python3
"""Fail-closed deployment status receipt; this is not a readiness probe."""

from __future__ import annotations

import json

SCHEMA = "aureon.deployment-verification-hold.v1"


def main() -> int:
    """Report the unresolved production gates without touching dependencies."""
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "decision": "HOLD",
                "reason": "full_os_protection_not_attested",
                "production_ready": False,
                "native_outer_boundary_attested": False,
                "external_head_anchor_attested": False,
                "source_scope_protected": False,
                "aureon_imported": False,
                "file_written": False,
                "network_accessed": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
