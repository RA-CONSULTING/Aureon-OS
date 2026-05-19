#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


def _run(cmd: List[str]) -> Dict[str, Any]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_api_cmd(py: str, args: argparse.Namespace, profile: str, api_json: Path, api_env: Path, api_csv: Path) -> List[str]:
    return [
        py,
        "scripts/diagnostics/benchmark_exchange_api_limits.py",
        "--phase-duration-sec", str(args.api_phase_duration_sec),
        "--concurrency", str(args.api_concurrency),
        "--rounds", str(args.api_rounds),
        "--stress-profile", str(profile),
        "--exchanges", str(args.api_exchanges),
        "--out", str(api_json),
        "--env-out", str(api_env),
        "--csv-out", str(api_csv),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run expanded API + latency stress suite and emit one consolidated report")
    ap.add_argument("--api-phase-duration-sec", type=int, default=3)
    ap.add_argument("--api-concurrency", type=int, default=4)
    ap.add_argument("--api-rounds", type=int, default=2)
    ap.add_argument("--api-stress-profile", default="aggressive", choices=["conservative", "standard", "aggressive"])
    ap.add_argument("--api-exchanges", default="all")
    ap.add_argument("--latency-tail", type=int, default=10000)
    ap.add_argument("--latency-min-samples", type=int, default=25)
    ap.add_argument("--latency-p95-budget-ms", type=float, default=900.0)
    ap.add_argument("--sweep", action="store_true", help="Run conservative/standard/aggressive API profile sweep")
    ap.add_argument("--out", default="state/full_stress_suite_report.json")
    ap.add_argument("--markdown-out", default="state/full_stress_suite_report.md")
    args = ap.parse_args()

    api_json = Path("state/exchange_api_rate_benchmark.json")
    api_env = Path("state/exchange_api_rate_benchmark.env")
    api_csv = Path("state/exchange_api_rate_benchmark_rounds.csv")
    lat_json = Path("state/latency_stress_report.json")

    lat_cmd = [
        sys.executable,
        "scripts/diagnostics/stress_test_intelligence_to_trade_latency.py",
        "--tail", str(args.latency_tail),
        "--min-samples", str(args.latency_min_samples),
        "--p95-budget-ms", str(args.latency_p95_budget_ms),
        "--out", str(lat_json),
    ]

    sweep_runs: List[Dict[str, Any]] = []
    if args.sweep:
        for profile in ["conservative", "standard", "aggressive"]:
            cmd = _build_api_cmd(sys.executable, args, profile, api_json, api_env, api_csv)
            run = _run(cmd)
            rep = _load_json(api_json)
            score = sum(float(r.get("recommended_runtime_calls_per_min", 0.0) or 0.0) for r in rep.get("results", [])) if isinstance(rep, dict) else 0.0
            sweep_runs.append({"profile": profile, "exit_code": run["exit_code"], "score": score, "report": rep})
        best = max(sweep_runs, key=lambda x: float(x.get("score", 0.0)), default={"profile": "standard"})
        chosen_profile = str(best.get("profile") or "standard")
    else:
        chosen_profile = str(args.api_stress_profile)

    api_cmd = _build_api_cmd(sys.executable, args, chosen_profile, api_json, api_env, api_csv)
    api_run = _run(api_cmd)
    lat_run = _run(lat_cmd)

    api_report = _load_json(api_json)
    lat_report = _load_json(lat_json)

    suite_pass = (api_run["exit_code"] == 0) and (lat_run["exit_code"] == 0)

    consolidated = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "suite_pass": suite_pass,
        "api_sweep": sweep_runs,
        "api_benchmark": {
            "chosen_profile": chosen_profile,
            "command": api_cmd,
            "exit_code": api_run["exit_code"],
            "report_path": str(api_json),
            "env_path": str(api_env),
            "csv_path": str(api_csv),
            "report": api_report,
        },
        "latency_stress": {
            "command": lat_cmd,
            "exit_code": lat_run["exit_code"],
            "report_path": str(lat_json),
            "report": lat_report,
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")

    pf = (lat_report.get("pass_fail") if isinstance(lat_report, dict) else {}) or {}
    md_lines = [
        f"# Full Stress Suite Report ({consolidated['generated_at']})",
        "",
        f"- Suite pass: **{consolidated['suite_pass']}**",
        f"- API profile used: `{chosen_profile}`",
        f"- API exit code: `{api_run['exit_code']}`",
        f"- Latency exit code: `{lat_run['exit_code']}`",
        "",
        "## API Recommendations",
    ]
    for row in api_report.get("results", []) if isinstance(api_report, dict) else []:
        md_lines.append(f"- {row.get('exchange')}: recommended {row.get('recommended_runtime_calls_per_min')} calls/min (valid={row.get('benchmark_valid')})")
    md_lines.extend([
        "",
        "## Latency Gate",
        f"- Samples found: {pf.get('samples_found', 0)} (min required: {pf.get('min_samples_required', 0)})",
        f"- p95 observed: {pf.get('p95_observed_ms', 0)} ms (budget: {pf.get('p95_budget_ms', 0)} ms)",
        f"- Stress pass: **{pf.get('stress_test_pass', False)}**",
    ])
    Path(args.markdown_out).write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(consolidated, indent=2))
    return 0 if suite_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
