#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


def run_one(concurrency: int, profile: str, phase_duration_sec: int, rounds: int, exchanges: str) -> Dict[str, Any]:
    out = Path("state") / f"exchange_api_benchmark_c{concurrency}.json"
    cmd = [
        sys.executable,
        "scripts/diagnostics/benchmark_exchange_api_limits.py",
        "--phase-duration-sec", str(phase_duration_sec),
        "--concurrency", str(concurrency),
        "--rounds", str(rounds),
        "--stress-profile", profile,
        "--exchanges", exchanges,
        "--out", str(out),
        "--env-out", "state/exchange_api_rate_benchmark.env",
        "--csv-out", "state/exchange_api_rate_benchmark_rounds.csv",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    report: Dict[str, Any] = {}
    if out.exists():
        try:
            report = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            report = {}
    results = report.get("results", []) if isinstance(report, dict) else []
    total_rec = sum(float(r.get("recommended_runtime_calls_per_min", 0.0) or 0.0) for r in results)
    valid_count = sum(1 for r in results if bool(r.get("benchmark_valid")))
    return {
        "concurrency": concurrency,
        "exit_code": proc.returncode,
        "total_recommended_calls_per_min": round(total_rec, 3),
        "valid_exchange_count": valid_count,
        "report_path": str(out),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep API benchmark across concurrency levels")
    ap.add_argument("--concurrency-steps", default="1,2,4,8")
    ap.add_argument("--stress-profile", default="aggressive", choices=["conservative", "standard", "aggressive"])
    ap.add_argument("--phase-duration-sec", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--exchanges", default="all")
    ap.add_argument("--out", default="state/exchange_api_concurrency_sweep.json")
    ap.add_argument("--md-out", default="state/exchange_api_concurrency_sweep.md")
    args = ap.parse_args()

    steps = [int(x.strip()) for x in str(args.concurrency_steps).split(",") if x.strip()]
    rows = [run_one(c, args.stress_profile, args.phase_duration_sec, args.rounds, args.exchanges) for c in steps]

    best = max(rows, key=lambda r: (int(r.get("valid_exchange_count", 0)), float(r.get("total_recommended_calls_per_min", 0.0)))) if rows else {}
    data = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "stress_profile": args.stress_profile,
        "phase_duration_sec": args.phase_duration_sec,
        "rounds": args.rounds,
        "exchanges": args.exchanges,
        "rows": rows,
        "best": best,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")

    md = [
        f"# Exchange API Concurrency Sweep ({data['generated_at']})",
        "",
        f"- Stress profile: `{args.stress_profile}`",
        f"- Best concurrency: `{best.get('concurrency', 'n/a')}`",
        f"- Best valid exchanges: `{best.get('valid_exchange_count', 0)}`",
        f"- Best total recommended calls/min: `{best.get('total_recommended_calls_per_min', 0)}`",
        "",
        "| concurrency | exit | valid_exchanges | total_recommended_calls_per_min |",
        "|---:|---:|---:|---:|",
    ]
    for r in rows:
        md.append(f"| {r['concurrency']} | {r['exit_code']} | {r['valid_exchange_count']} | {r['total_recommended_calls_per_min']} |")
    Path(args.md_out).write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
