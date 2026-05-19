#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


def run_case(tail: int, min_samples: int, p95_budget_ms: float, out_json: Path) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        "scripts/diagnostics/stress_test_intelligence_to_trade_latency.py",
        "--tail", str(tail),
        "--min-samples", str(min_samples),
        "--p95-budget-ms", str(p95_budget_ms),
        "--out", str(out_json),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    report: Dict[str, Any] = {}
    if out_json.exists():
        try:
            report = json.loads(out_json.read_text(encoding="utf-8"))
        except Exception:
            report = {}
    pf = report.get("pass_fail", {}) if isinstance(report, dict) else {}
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": tail,
        "min_samples": min_samples,
        "p95_budget_ms": p95_budget_ms,
        "samples_found": pf.get("samples_found", 0),
        "p95_observed_ms": pf.get("p95_observed_ms", 0),
        "stress_test_pass": pf.get("stress_test_pass", False),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run latency stress test across threshold matrix")
    ap.add_argument("--tail", type=int, default=2000)
    ap.add_argument("--sample-steps", default="25,50,100,200")
    ap.add_argument("--budget-steps", default="200,300,400,600,900")
    ap.add_argument("--out", default="state/latency_threshold_matrix.json")
    ap.add_argument("--md-out", default="state/latency_threshold_matrix.md")
    args = ap.parse_args()

    sample_steps = [int(x.strip()) for x in str(args.sample_steps).split(",") if x.strip()]
    budget_steps = [float(x.strip()) for x in str(args.budget_steps).split(",") if x.strip()]

    results: List[Dict[str, Any]] = []
    for s in sample_steps:
        for b in budget_steps:
            out_case = Path("state") / f"latency_case_s{s}_b{int(b)}.json"
            results.append(run_case(args.tail, s, b, out_case))

    pass_count = sum(1 for r in results if r.get("stress_test_pass"))
    matrix = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "tail": args.tail,
        "sample_steps": sample_steps,
        "budget_steps": budget_steps,
        "cases": results,
        "summary": {
            "total_cases": len(results),
            "pass_cases": pass_count,
            "fail_cases": len(results) - pass_count,
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    lines = [
        f"# Latency Threshold Matrix ({matrix['generated_at']})",
        "",
        f"- Total cases: {matrix['summary']['total_cases']}",
        f"- Pass cases: {matrix['summary']['pass_cases']}",
        f"- Fail cases: {matrix['summary']['fail_cases']}",
        "",
        "| min_samples | p95_budget_ms | samples_found | p95_observed_ms | pass |",
        "|---:|---:|---:|---:|:---:|",
    ]
    for r in results:
        lines.append(
            f"| {r['min_samples']} | {r['p95_budget_ms']} | {r['samples_found']} | {r['p95_observed_ms']} | {'✅' if r['stress_test_pass'] else '❌'} |"
        )
    Path(args.md_out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(matrix, indent=2))
    return 0 if pass_count > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
