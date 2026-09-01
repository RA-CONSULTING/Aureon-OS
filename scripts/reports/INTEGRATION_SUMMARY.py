#!/usr/bin/env python3
"""Current integration status: evidence-gated and deliberately fail-closed."""

from __future__ import annotations

import json

SCHEMA = "aureon.integration-status-hold.v1"


def main() -> int:
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "decision": "HOLD",
                "production_ready": False,
                "remote_deployment_authorized": False,
                "full_os_protection_attested": False,
                "native_outer_boundary_attested": False,
                "external_head_anchor_attested": False,
                "reason": "verified_production_evidence_required",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
