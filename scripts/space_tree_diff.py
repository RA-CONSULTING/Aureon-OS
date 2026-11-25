#!/usr/bin/env python3
"""Show how the public Space tree differs from one local Git commit.

Read-only. It resolves what the Space ``README.md`` says it serves, compares the
remote tree against the commit named in that card, and prints only the paths that
differ plus the card files. Use it to prove a drift is limited before any write.

The public Space was last published by a path that staged bytes outside Git, so
a remote file's size need not equal the Git blob size of "the same" path. This
report therefore never claims byte equality; it lists what differs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--space", default="GaryLeckey/aureon-os")
    parser.add_argument("--commit", default=None, help="defaults to the card's source_commit")
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    from huggingface_hub import HfApi

    api = HfApi()
    space_info = api.repo_info(arguments.space, repo_type="space", files_metadata=True)
    # cardData is a RepocardData, not a plain mapping: read its known keys
    # directly instead of converting it with dict().
    def card_value(key: str) -> Any:
        return getattr(space_info.cardData, key, None)

    commit = arguments.commit or card_value("source_commit")

    report: dict[str, Any] = {
        "space": arguments.space,
        "space_revision": space_info.sha,
        "card": {
            key: card_value(key)
            for key in ("sdk", "app_file", "suggested_hardware", "source_commit")
        },
        "compare_commit": commit,
    }

    if commit:
        tracked = set(git(arguments.repo, "ls-tree", "-r", "--name-only", commit).splitlines())
        remote = {sibling.rfilename: sibling.size for sibling in space_info.siblings}
        report["tracked_files"] = len(tracked)
        report["remote_files"] = len(remote)
        # Only paths present on both sides can be compared without blaming the
        # publisher's overlay. Everything else is reported as one-sided.
        report["remote_only"] = sorted(set(remote) - tracked)
        report["local_only"] = sorted(tracked - set(remote))
    else:
        report["tracked_files"] = None
        report["note"] = "card has no source_commit; cannot compare against a local commit"

    document = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(document, flush=True)
    if arguments.out:
        destination = Path(arguments.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
