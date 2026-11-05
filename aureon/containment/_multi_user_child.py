"""Contained multi-user payload. The wrapper execs this file.

The process may import aureon. It does not bind a listener, place an order,
or read the parent environment. ``HOME`` is the contained work directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Contained multi-user smoke payload")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    sys.path.insert(0, str(root))
    from aureon.containment.multi_user_smoke import redact_text, run_contained

    try:
        report = run_contained()
        code = 0 if report.get("ok") else 1
    except Exception as exc:  # noqa: BLE001 — the parent must receive a record
        report = {
            "schema": "aureon.measured.multi-user-child.v1",
            "ok": False,
            "error": redact_text(f"{type(exc).__name__}: {exc}"),
            "listener_bound": False,
            "orders_placed": False,
            "live_trading": False,
            "market_data_fetched": False,
            "go_live_clear": False,
        }
        code = 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    sys.stdout.write(json.dumps({"wrote": str(args.out), "ok": bool(report.get("ok"))}) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
