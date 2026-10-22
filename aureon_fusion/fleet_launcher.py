"""Supervised launcher for the paper-mode organ fleet.

``python -m aureon_fusion.fleet_launcher --check`` reads the flight recorder
health file and exits 0 only when all 11 faculties are fresh. It does not
invent a mark. ``--supervise`` starts the unity supervisor, which keeps the
organs alive. The launcher refuses to start when live trading is requested
or the capital-release pin is present.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .flight_recorder import FACULTY_FILES, FLIGHT_HEALTH
from .paths import FUSION_STATE

FACULTY_COUNT = len(FACULTY_FILES)
CAPITAL_RELEASE_FLAG = FUSION_STATE / "capital_release.flag"


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def blocked_reason() -> str | None:
    """Why the launcher must not start. None when paper mode is allowed."""

    if _truthy("AUREON_LIVE_TRADING") or _truthy("AUREON_FUSION_ARM_LIVE"):
        return "live trading flag is set"
    if CAPITAL_RELEASE_FLAG.exists():
        return f"{CAPITAL_RELEASE_FLAG.name} is present"
    return None


def read_health(path: Path | None = None) -> dict:
    health_path = path or FLIGHT_HEALTH
    if not health_path.is_file():
        return {
            "ok": False,
            "blocked": f"flight health file is missing: {health_path.name}",
            "fresh_count": 0,
            "faculties_count": FACULTY_COUNT,
        }
    try:
        health = json.loads(health_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "blocked": f"flight health file is unreadable: {exc.__class__.__name__}",
            "fresh_count": 0,
            "faculties_count": FACULTY_COUNT,
        }
    fresh = health.get("fresh_count")
    total = health.get("faculties_count")
    stale = health.get("stale_list") or []
    simulated = health.get("simulated_detected") or []
    ok = (
        health.get("all_fresh") is True
        and fresh == FACULTY_COUNT
        and total == FACULTY_COUNT
        and stale == []
        and simulated == []
    )
    report = {
        "ok": ok,
        "fresh_count": fresh,
        "faculties_count": total,
        "all_fresh": health.get("all_fresh"),
        "stale_list": stale,
        "simulated_detected": simulated,
        "ts": health.get("ts"),
    }
    if not ok:
        report["blocked"] = "one or more faculties are not fresh"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aureon_fusion.fleet_launcher")
    parser.add_argument("--check", action="store_true", help="exit 0 only when all 11 faculties are fresh")
    parser.add_argument("--supervise", action="store_true", help="run the unity supervisor loop")
    parser.add_argument("--interval", type=float, default=45.0)
    args = parser.parse_args(argv)

    reason = blocked_reason()
    if reason:
        print(json.dumps({"ok": False, "blocked": reason}))
        return 2

    if args.check:
        report = read_health()
        print(json.dumps(report))
        return 0 if report.get("ok") else 1

    if args.supervise:
        from .unity_supervisor import main as supervise

        return supervise(["--interval", str(args.interval)])

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
