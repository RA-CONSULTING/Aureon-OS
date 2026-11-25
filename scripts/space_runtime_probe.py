#!/usr/bin/env python3
"""Print the live runtime state of the Aureon OS public Space.

Read-only. It never uploads, restarts, pauses, or requests hardware; it prints
the Hub's own runtime view so a capacity, build, or configuration failure can be
told apart from a release. The token comes from the normal Hub credential store
or the environment and is never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

SPACE_REPOSITORY = "GaryLeckey/aureon-os"
MODEL_REPOSITORY = "GaryLeckey/aureon-7b"
MODEL_FILES = ("model.safetensors", "config.json", "preparation_receipt.json")


def space_state(api: Any, repo_id: str) -> dict[str, Any]:
    runtime = api.get_space_runtime(repo_id)
    raw = runtime.raw if isinstance(runtime.raw, dict) else {}
    hardware = raw.get("hardware") or {}
    return {
        "space": repo_id,
        "stage": str(runtime.stage),
        "sdk": raw.get("sdk"),
        "hardware_current": hardware.get("current"),
        "hardware_requested": hardware.get("requested"),
        "dev_mode": raw.get("devMode"),
        "error_message": raw.get("errorMessage"),
        "sleep_time": raw.get("gcTimeout"),
        "domains": raw.get("domains"),
    }


def model_state(api: Any, repo_id: str, revision: str | None) -> dict[str, Any]:
    info = api.model_info(repo_id, revision=revision or "main", files_metadata=True)
    sizes = {
        sibling.rfilename: sibling.size
        for sibling in (info.siblings or [])
        if sibling.rfilename in MODEL_FILES
    }
    return {
        "model": repo_id,
        "revision": info.sha,
        "private": bool(info.private),
        "sizes": sizes,
        "complete": all(sizes.get(name) for name in MODEL_FILES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", default=SPACE_REPOSITORY)
    parser.add_argument("--model", default=MODEL_REPOSITORY)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--watch", type=int, default=0, help="poll every N seconds")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument(
        "--out",
        default=None,
        help="also write the report here as BOM-free JSON (PowerShell redirection adds a BOM)",
    )
    arguments = parser.parse_args()

    from huggingface_hub import HfApi

    # Configured here rather than with the CLI: PowerShell's text redirection
    # writes a BOM and CRLF, which breaks a downstream json.load on the receipt.
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    api = HfApi()
    for attempt in range(max(1, arguments.count)):
        if attempt:
            time.sleep(max(0, arguments.watch))
        report = {
            "space": space_state(api, arguments.space),
            "model": model_state(api, arguments.model, arguments.revision),
        }
        document = json.dumps(report, sort_keys=True, default=str)
        print(document, flush=True)
        if arguments.out:
            # newline="\n" and utf-8 keep the receipt loadable by json.load on
            # every platform; PowerShell's own redirection would prepend a BOM.
            destination = Path(arguments.out)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(document + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
