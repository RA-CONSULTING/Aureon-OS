#!/usr/bin/env python3
"""Credential-setup compatibility entrypoint: terminal release HOLD."""

from __future__ import annotations

import json


def main() -> int:
    receipt = {
        "credential_collected": False,
        "credential_written": False,
        "decision": "HOLD",
        "plaintext_fallback_allowed": False,
        "production_ready": False,
        "reason": "reviewed_credential_custody_boundary_required",
        "schema": "aureon.production.credential-setup-hold.v2",
    }
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
