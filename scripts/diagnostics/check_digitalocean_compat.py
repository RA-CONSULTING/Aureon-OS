#!/usr/bin/env python3
"""Legacy cloud compatibility check replaced by a non-mutating HOLD receipt."""

from __future__ import annotations

import json

SCHEMA = "aureon.digitalocean-compatibility-hold.v1"


def main() -> int:
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "decision": "HOLD",
                "reason": "cloud_runtime_protection_not_attested",
                "production_ready": False,
                "filesystem_probed": False,
                "network_probed": False,
                "credentials_inspected": False,
                "file_written": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
