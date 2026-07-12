#!/usr/bin/env python3
"""
Aureon Operator — A/B benchmark runner.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Runs the ground-truth prompt set through two conditions and prints a comparison:

  baseline  — raw model output (no grounding, no consensus, no veto)
  aureon    — the same model through the full operator chain

    python scripts/run_operator_benchmark.py
    python scripts/run_operator_benchmark.py --out /tmp/bench.json

Writes the full result JSON (per-item + aggregate metrics) for the audit report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from aureon.operator.benchmark import run_benchmark  # noqa: E402

PROMPTS = _REPO / "data/research/operator_benchmark_prompts.json"
RECORDINGS = _REPO / "data/research/operator_benchmark_recordings.jsonl"

_METRIC_ROWS = [
    ("fact_accuracy", "Fact accuracy", "higher"),
    ("hallucination_rate", "Hallucination rate", "lower"),
    ("abstention_rate", "Honest abstention", "context"),
    ("grounding_coverage", "Grounding coverage", "higher"),
    ("safety_block_rate", "Safety block rate", "higher"),
    ("mean_latency_ms", "Mean latency (ms)", "context"),
]


def _fmt(metric: str, value: float) -> str:
    if metric == "mean_latency_ms":
        return f"{value:.1f}"
    return f"{value*100:.1f}%" if value <= 1.0 else f"{value}"


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(_REPO / "data/research/operator_benchmark_results.json"))
    ap.add_argument("--personas", default="a,b")
    args = ap.parse_args(argv[1:])

    result = run_benchmark(
        PROMPTS, RECORDINGS, personas=[p.strip() for p in args.personas.split(",") if p.strip()]
    )
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    b = result["baseline"]["metrics"]
    a = result["aureon"]["metrics"]

    print("\n\033[36m🎛️  AUREON OPERATOR — A/B BENCHMARK\033[0m")
    print(f"    prompts={result['n_prompts']}  factual={b['n_factual']}  adversarial={b['n_adversarial']}")
    if b["n_missing_recordings"] or a["n_missing_recordings"]:
        print(f"    \033[33m⚠ missing recordings: baseline={b['n_missing_recordings']} aureon={a['n_missing_recordings']}\033[0m")

    print(f"\n    {'Metric':<22}{'Baseline':>12}{'Aureon':>12}   Better")
    print("    " + "─" * 60)
    for key, label, better in _METRIC_ROWS:
        bv, av = b[key], a[key]
        arrow = ""
        if better == "higher":
            arrow = "✅ Aureon" if av > bv else ("— tie" if av == bv else "⚠ baseline")
        elif better == "lower":
            arrow = "✅ Aureon" if av < bv else ("— tie" if av == bv else "⚠ baseline")
        print(f"    {label:<22}{_fmt(key, bv):>12}{_fmt(key, av):>12}   {arrow}")

    print(f"\n    results written → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
