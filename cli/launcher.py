"""Legacy local launcher retained as a terminal compatibility HOLD."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.local-launcher-hold.v1",
                "decision": "HOLD",
                "reason": "protected_local_runtime_not_attested",
                "production_ready": False,
                "setup_wizard_started": False,
                "credentials_collected": False,
                "trading_started": False,
                "dashboard_started": False,
                "autostart_registered": False,
                "file_written": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
