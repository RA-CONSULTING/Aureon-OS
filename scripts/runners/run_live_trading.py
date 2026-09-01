#!/usr/bin/env python3
"""Legacy live-trading runner replaced by a terminal authorization HOLD."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.live-trading-runner-hold.v1",
                "decision": "HOLD",
                "reason": "live_execution_not_authorized_or_protected",
                "production_ready": False,
                "credentials_inspected": False,
                "balances_fetched": False,
                "exchange_client_imported": False,
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
