#!/usr/bin/env python3
"""
Aureon Cognition — cross-domain A/B benchmark runner.

    AUREON_LLM_OFFLINE=1 python scripts/run_cognition_benchmark.py

Compares a raw model vs the full agentic cognition across in-repo, general, and
safety prompts. Writes results JSON for the capabilities report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from aureon.operator.cognition_benchmark import run  # noqa: E402

PROMPTS = _REPO / "data/research/cognition_benchmark_prompts.json"
RECS = _REPO / "data/research/cognition_benchmark_recordings.json"

_ROWS = [
    ("correctness", "Correctness (in-repo+general)"),
    ("grounding_precision", "Grounding precision"),
    ("tool_use_in_repo", "Tool use (in-repo)"),
    ("safety_block_rate", "Safety block rate"),
    ("fabricated_citation_rate", "Fabricated citations"),
]


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(_REPO / "data/research/cognition_benchmark_results.json"))
    args = ap.parse_args(argv[1:])

    result = run(PROMPTS, RECS)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    b, c = result["baseline"]["metrics"], result["cognition"]["metrics"]
    print("\n\033[36m🧠 AUREON COGNITION — CROSS-DOMAIN A/B\033[0m")
    print(f"    prompts={result['n_prompts']}  in_repo={c['n_in_repo']}  general={c['n_general']}  safety={c['n_safety']}")
    print(f"\n    {'Metric':<30}{'Baseline':>11}{'Cognition':>12}")
    print("    " + "─" * 55)
    for key, label in _ROWS:
        print(f"    {label:<30}{b[key]*100:>10.1f}%{c[key]*100:>11.1f}%")
    print(f"\n    results → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
