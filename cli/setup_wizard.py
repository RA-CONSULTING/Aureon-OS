"""Credential setup is disabled while the local runtime remains on HOLD."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.cli-setup-wizard-hold.v1",
                "decision": "HOLD",
                "reason": "approved_credential_custody_required",
                "production_ready": False,
                "credentials_requested": False,
                "credentials_displayed": False,
                "credentials_written": False,
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
