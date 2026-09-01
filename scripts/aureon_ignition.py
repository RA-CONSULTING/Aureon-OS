#!/usr/bin/env python3
"""Legacy master ignition retained as a terminal protected-runtime HOLD."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.ignition-hold.v1",
                "decision": "HOLD",
                "reason": "complete_native_protection_boundary_required",
                "production_ready": False,
                "full_os_protection_attested": False,
                "external_head_anchor_attested": False,
                "aureon_imported": False,
                "credentials_inspected": False,
                "systems_booted": False,
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
