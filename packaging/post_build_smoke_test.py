"""Packaging activation is disabled until a protected native build exists."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema": "aureon.native-package-smoke-hold.v1",
                "decision": "HOLD",
                "reason": "protected_native_package_not_attested",
                "production_ready": False,
                "binary_selected": False,
                "binary_executed": False,
                "child_process_started": False,
                "file_written": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
