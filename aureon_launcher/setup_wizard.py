#!/usr/bin/env python3
"""Legacy desktop credential wizard replaced by a terminal HOLD receipt."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.desktop-setup-wizard-hold.v1",
                "decision": "HOLD",
                "reason": "approved_credential_custody_required",
                "production_ready": False,
                "ui_started": False,
                "credentials_requested": False,
                "credentials_displayed": False,
                "credentials_written": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
