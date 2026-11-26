#!/usr/bin/env python3
"""Upload the captured Space tree to the Hub, then verify the served card.

Reads the receipt and content directory produced by ``publish_space
--content-dir`` and uploads exactly those bytes: the manifest path is the Hub
path, and a file stored under an escaped ``.case-collision-`` name is uploaded
at its real case-distinct path.

Default is a dry run. ``--apply`` performs the commit. Paid hardware is never
requested here; ``publish_space --activate-l40s`` guards that separately.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SPACE_REPOSITORY = "GaryLeckey/aureon-os"
ESCAPE_PREFIX = ".case-collision-"


def disk_name_for(relative: str) -> str:
    """Mirror publish_space._case_collision_safe_name for one path."""
    prefix, _, name = relative.rpartition("/")
    encoded = name.encode("utf-8").hex()
    return f"{prefix}/{ESCAPE_PREFIX}{encoded}" if prefix else f"{ESCAPE_PREFIX}{encoded}"


def locate(content_root: Path, relative: str) -> Path:
    """Return the on-disk file holding the bytes for a manifest path."""
    direct = content_root.joinpath(*PurePosixPath(relative).parts)
    if direct.is_file():
        return direct
    escaped = content_root.joinpath(*PurePosixPath(disk_name_for(relative)).parts)
    if escaped.is_file():
        return escaped
    raise SystemExit(f"captured bytes are missing for {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--space", default=SPACE_REPOSITORY)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt-out", type=Path, default=None)
    arguments = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    manifest = json.loads(arguments.receipt.read_text(encoding="utf-8-sig"))
    rows: list[dict[str, Any]] = manifest["files"]
    content_root = arguments.content_dir.resolve()

    # Verify every captured byte against the manifest digest before any upload.
    verified = 0
    mismatched: list[str] = []
    import hashlib

    for row in rows:
        source = locate(content_root, row["path"])
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            mismatched.append(row["path"])
        else:
            verified += 1
    if mismatched:
        raise SystemExit(f"captured bytes do not match the manifest: {mismatched[:5]}")

    summary = {
        "space": arguments.space,
        "source_commit": manifest["source_commit"],
        "files": len(rows),
        "verified": verified,
        "applied": False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)

    if arguments.apply:
        from huggingface_hub import CommitOperationAdd, HfApi

        api = HfApi()
        space = api.repo_info(arguments.space, repo_type="space")
        sdk = getattr(space.cardData, "sdk", None)
        if sdk != "docker":
            raise SystemExit(f"refusing upload: live card sdk is {sdk!r}, not docker")

        operations = [
            CommitOperationAdd(path_in_repo=row["path"], path_or_fileobj=locate(content_root, row["path"]))
            for row in rows
        ]
        commit = api.create_commit(
            repo_id=arguments.space,
            repo_type="space",
            operations=operations,
            commit_message=(
                f"Publish the complete organism from source {manifest['source_commit']}\n\n"
                "Staged from Git objects with the Docker card, the deploy Dockerfile, and\n"
                "neutral root SDK metadata, so the Hub builds the image instead of\n"
                f"serving an SDK app. {len(rows)} tracked paths."
            ),
        )
        summary["applied"] = True
        summary["space_revision_after"] = getattr(commit, "oid", None) or getattr(commit, "sha", None)
        after = api.repo_info(arguments.space, repo_type="space")
        summary["card_after"] = {
            "sdk": getattr(after.cardData, "sdk", None),
            "suggested_hardware": getattr(after.cardData, "suggested_hardware", None),
        }

    if arguments.receipt_out:
        arguments.receipt_out.parent.mkdir(parents=True, exist_ok=True)
        arguments.receipt_out.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
