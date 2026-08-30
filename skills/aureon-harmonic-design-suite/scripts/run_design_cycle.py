#!/usr/bin/env python3
"""Run Aureon's bounded public-website Design Nexus cycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_repo(start: Path) -> Path:
    candidate = start.resolve()
    for directory in (candidate, *candidate.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "website").is_dir():
            return directory
    raise SystemExit("Could not find an Aureon repository containing pyproject.toml and website/.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a source-bound, local-only Aureon website design-cycle receipt."
    )
    parser.add_argument("--goal", required=True, help="Bounded website design objective.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--route",
        action="append",
        default=[],
        help="Public route (/research/) or website-relative HTML route (research/index.html).",
    )
    parser.add_argument("--previous-cycle", type=Path)
    parser.add_argument(
        "--skip-external",
        action="store_true",
        help="Diagnostic only: skipped external checks can never verify or authorise packaging.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    repo = _find_repo(args.repo_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    from aureon.operator.website_operator import WebsiteOperator

    operator = WebsiteOperator.from_paths(repo_root=repo)
    receipt = operator.design_cycle(
        goal=args.goal,
        output=args.output,
        routes=args.route or None,
        run_external=not args.skip_external,
        previous_cycle=args.previous_cycle,
    )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "receipt": str(receipt),
                "state": payload.get("state"),
                "source_tree_sha256": payload.get("source_tree_sha256"),
                "design_nexus_score": payload.get("design_nexus", {}).get("score"),
                "hard_gates_pass": payload.get("hard_gates_pass"),
                "ready_for_deployment": payload.get("summary", {}).get("ready_for_deployment"),
            },
            indent=2,
        )
    )
    return 0 if payload.get("hard_gates_pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
