#!/usr/bin/env python3
"""Request a specific GPU for the public Space and report what actually happened.

The card and the runtime request are separate. ``l40sx1`` was requested for days
and never scheduled; the served checkpoint is ~1.17B parameters (about 2.3 GB in
bf16), so an L4 carries it with wide headroom.

A successful API call only means the request was accepted. This prints the Hub's
own runtime view afterwards, and never reports a GPU as running unless the Hub
says ``hardware.current`` is set.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

SPACE_REPOSITORY = "GaryLeckey/aureon-os"
EXPECTED_SDK = "docker"
APPROVED = ("l40sx1", "l4x1", "a10g-small", "a10g-large")


def runtime_view(api: Any, repo_id: str) -> dict[str, Any]:
    runtime = api.get_space_runtime(repo_id)
    raw = runtime.raw or {}
    hardware = raw.get("hardware") or {}
    return {
        "stage": str(runtime.stage),
        "requested": hardware.get("requested"),
        "current": hardware.get("current"),
        "error": raw.get("errorMessage"),
        "sleep_time": raw.get("gcTimeout"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", default=SPACE_REPOSITORY)
    parser.add_argument("--hardware", default="l4x1", choices=APPROVED)
    parser.add_argument("--apply", action="store_true", help="send the request")
    parser.add_argument("--watch", type=int, default=0, help="poll every N seconds for this long")
    parser.add_argument("--receipt", type=Path, default=None)
    arguments = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    from huggingface_hub import HfApi

    api = HfApi()
    space = api.repo_info(arguments.space, repo_type="space")
    sdk = getattr(space.cardData, "sdk", None)
    if sdk != EXPECTED_SDK:
        raise SystemExit(f"refusing: live card sdk is {sdk!r}, not {EXPECTED_SDK}")

    report: dict[str, Any] = {
        "space": arguments.space,
        "requested_hardware": arguments.hardware,
        "before": runtime_view(api, arguments.space),
        "request_sent": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)

    if arguments.apply:
        api.request_space_hardware(
            repo_id=arguments.space,
            hardware=arguments.hardware,
            sleep_time=-1,
        )
        report["request_sent"] = True

    deadline = time.time() + max(0, arguments.watch)
    while True:
        view = runtime_view(api, arguments.space)
        report["after"] = view
        report["running_verified"] = bool(view["current"])
        print(json.dumps(view, sort_keys=True), flush=True)
        if view["current"] or time.time() >= deadline:
            break
        time.sleep(20)

    if arguments.receipt:
        arguments.receipt.parent.mkdir(parents=True, exist_ok=True)
        arguments.receipt.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
