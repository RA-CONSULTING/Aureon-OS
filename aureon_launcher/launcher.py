#!/usr/bin/env python3
"""Legacy desktop launcher replaced by a terminal protected-runtime HOLD."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.desktop-launcher-hold.v1",
                "decision": "HOLD",
                "reason": "protected_desktop_runtime_not_attested",
                "production_ready": False,
                "ui_started": False,
                "credentials_loaded": False,
                "trading_started": False,
                "child_process_started": False,
                "browser_opened": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
