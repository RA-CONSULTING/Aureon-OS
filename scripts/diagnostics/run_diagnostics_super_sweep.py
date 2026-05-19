#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


def run(cmd: List[str]) -> Dict[str, Any]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run full diagnostics super-sweep (synthetic gen + threshold matrix + API concurrency sweep + full suite)")
    ap.add_argument("--samples", type=int, default=300)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--fast", action="store_true", help="Use reduced sweep sizes for quick stress validation")
    ap.add_argument("--out", default="state/diagnostics_super_sweep.json")
    ap.add_argument("--md-out", default="state/diagnostics_super_sweep.md")
    args = ap.parse_args()

    if args.fast:
        threshold_samples = "25,50"
        threshold_budgets = "250,400"
        conc_steps = "1,2"
        api_exchanges = "binance,kraken"
    else:
        threshold_samples = "25,50,100,200"
        threshold_budgets = "200,250,300,400"
        conc_steps = "1,2,4,8"
        api_exchanges = "all"

    cmds = {
        "synthetic": [sys.executable, "scripts/diagnostics/generate_synthetic_latency_artifacts.py", "--samples", str(args.samples), "--seed", str(args.seed)],
        "threshold_matrix": [sys.executable, "scripts/diagnostics/run_latency_threshold_matrix.py", "--tail", "5000", "--sample-steps", threshold_samples, "--budget-steps", threshold_budgets],
        "api_concurrency": [sys.executable, "scripts/diagnostics/run_exchange_api_concurrency_sweep.py", "--concurrency-steps", conc_steps, "--stress-profile", "aggressive", "--phase-duration-sec", "1", "--rounds", "1", "--exchanges", api_exchanges],
        "full_suite": [sys.executable, "scripts/diagnostics/run_full_latency_and_api_stress_suite.py", "--sweep", "--api-phase-duration-sec", "1", "--api-concurrency", "2", "--api-rounds", "1", "--latency-min-samples", "50", "--latency-p95-budget-ms", "400"],
    }

    runs: Dict[str, Dict[str, Any]] = {}
    for name, cmd in cmds.items():
        runs[name] = run(cmd)

    threshold = load_json(Path("state/latency_threshold_matrix.json"))
    conc = load_json(Path("state/exchange_api_concurrency_sweep.json"))
    suite = load_json(Path("state/full_stress_suite_report.json"))

    pass_count = sum(1 for r in runs.values() if int(r.get("exit_code", 1)) == 0)
    overall_pass = pass_count == len(runs)

    report = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "overall_pass": overall_pass,
        "fast_mode": bool(args.fast),
        "step_pass_count": pass_count,
        "step_total": len(runs),
        "runs": {k: {"exit_code": v.get("exit_code"), "cmd": v.get("cmd")} for k, v in runs.items()},
        "threshold_summary": (threshold.get("summary") if isinstance(threshold, dict) else {}),
        "api_concurrency_best": (conc.get("best") if isinstance(conc, dict) else {}),
        "full_suite_pass": (suite.get("suite_pass") if isinstance(suite, dict) else False),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        f"# Diagnostics Super Sweep ({report['generated_at']})",
        "",
        f"- Overall pass: **{report['overall_pass']}**",
        f"- Steps passed: **{report['step_pass_count']}/{report['step_total']}**",
        "",
        "## Step Exit Codes",
    ]
    for k, v in report["runs"].items():
        md.append(f"- {k}: exit `{v['exit_code']}`")
    md.extend([
        "",
        "## Threshold Matrix Summary",
        f"- pass_cases: {report['threshold_summary'].get('pass_cases', 0)}",
        f"- fail_cases: {report['threshold_summary'].get('fail_cases', 0)}",
        "",
        "## API Concurrency Best",
        f"- concurrency: {report['api_concurrency_best'].get('concurrency', 'n/a')}",
        f"- valid_exchange_count: {report['api_concurrency_best'].get('valid_exchange_count', 'n/a')}",
        f"- total_recommended_calls_per_min: {report['api_concurrency_best'].get('total_recommended_calls_per_min', 'n/a')}",
        "",
        f"## Full Suite Pass\n- {report['full_suite_pass']}",
    ])
    Path(args.md_out).write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
