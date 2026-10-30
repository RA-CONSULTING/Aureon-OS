"""Record real body_call results for one open stage. Does not place orders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aureon_public.body import enabled_stage, package_depth, sweep_zero_arg
from aureon_public.paths import repo_root


def write_stage(stage: int, timeout: float) -> Path:
    if stage > enabled_stage():
        raise SystemExit(f"stage {stage} is not open (enabled through {enabled_stage()})")
    calls = sweep_zero_arg(stage, timeout=timeout)
    out = repo_root() / "measured" / f"body_stage{stage}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    called = sum(1 for item in calls if item.get("called") is True)
    record = {
        "called": called,
        "calls": calls,
        "enabled_through": enabled_stage(),
        "stage": stage,
        "tried": len(calls),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record["entry_points"] = package_depth(stage)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-body-sweep")
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args(argv)
    path = write_stage(args.stage, args.timeout)
    print(path)


if __name__ == "__main__":
    main()
