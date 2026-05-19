#!/usr/bin/env python3
"""Live exchange API throughput benchmark (public endpoints).

Expanded stress benchmark:
- ramp phases (low/med/high request pressure)
- optional concurrency
- per-phase latency + status + success RPM
- runtime tuning recommendation with buffer
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional

from aureon.core.exchange_rate_limit_registry import OFFICIAL_EXCHANGE_RATE_LIMITS


@dataclass
class Probe:
    exchange: str
    name: str
    url: str


PROBES: List[Probe] = [
    Probe("binance", "ticker_price", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"),
    Probe("kraken", "ticker", "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"),
    Probe("alpaca", "clock", "https://paper-api.alpaca.markets/v2/clock"),
    Probe("capital", "ping", "https://api-capital.backend-capital.com/api/v1/ping"),
]


def call(url: str, timeout_s: float) -> tuple[bool, int, float]:
    started = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "aureon-rate-benchmark/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read(2048)
            latency = (time.perf_counter() - started) * 1000.0
            return True, int(getattr(resp, "status", 200) or 200), latency
    except urllib.error.HTTPError as e:
        latency = (time.perf_counter() - started) * 1000.0
        return False, int(e.code or 0), latency
    except Exception:
        latency = (time.perf_counter() - started) * 1000.0
        return False, 0, latency


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    idx = min(len(v) - 1, max(0, int(round((p / 100.0) * (len(v) - 1)))))
    return v[idx]


def run_phase(probe: Probe, phase_name: str, duration_s: int, qps: float, timeout_s: float, concurrency: int) -> Dict[str, object]:
    interval = 1.0 / max(0.1, qps)
    end = time.time() + duration_s
    latencies: List[float] = []
    ok = 0
    errors = 0
    statuses: Dict[str, int] = {}
    first_429: Optional[int] = None
    submitted = 0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = []
        while time.time() < end:
            futures.append(pool.submit(call, probe.url, timeout_s))
            submitted += 1
            time.sleep(interval)

        completed = 0
        for fut in as_completed(futures):
            success, status, latency = fut.result()
            completed += 1
            latencies.append(latency)
            key = str(status)
            statuses[key] = statuses.get(key, 0) + 1
            if success:
                ok += 1
            else:
                errors += 1
                if status == 429 and first_429 is None:
                    first_429 = completed

    elapsed = max(0.001, float(duration_s))
    rpm_success = (ok / elapsed) * 60.0
    rpm_observed = (submitted / elapsed) * 60.0
    profile = OFFICIAL_EXCHANGE_RATE_LIMITS.get(probe.exchange)
    safe_cpm = float(profile.safe_governor_calls_per_min) if profile else 0.0
    pct_of_safe = (rpm_success / safe_cpm * 100.0) if safe_cpm > 0 else 0.0

    return {
        "phase": phase_name,
        "duration_sec": duration_s,
        "target_qps": qps,
        "concurrency": concurrency,
        "submitted": submitted,
        "ok": ok,
        "errors": errors,
        "status_counts": statuses,
        "first_429_at_response": first_429,
        "latency_ms": {
            "p50": round(_percentile(latencies, 50), 3),
            "p95": round(_percentile(latencies, 95), 3),
            "p99": round(_percentile(latencies, 99), 3),
            "max": round(max(latencies) if latencies else 0.0, 3),
        },
        "successful_requests_per_min": round(rpm_success, 2),
        "observed_requests_per_min": round(rpm_observed, 2),
        "safe_calls_per_min": round(safe_cpm, 2),
        "pct_of_safe_limit": round(pct_of_safe, 2),
        "phase_valid": ok > 0,
    }


def _phases_for_profile(profile: str) -> List[tuple[str, float]]:
    p = str(profile or "standard").strip().lower()
    if p == "aggressive":
        return [("low", 5.0), ("medium", 12.0), ("high", 20.0), ("burst", 30.0)]
    if p == "conservative":
        return [("low", 1.0), ("medium", 2.0), ("high", 4.0)]
    return [("low", 2.0), ("medium", 5.0), ("high", 10.0)]


def benchmark_probe(probe: Probe, phase_duration_s: int, timeout_s: float, concurrency: int, buffer_pct: float, stress_profile: str) -> Dict[str, object]:
    phases = _phases_for_profile(stress_profile)
    rows = [run_phase(probe, n, phase_duration_s, qps, timeout_s, concurrency) for n, qps in phases]

    valid_rows = [r for r in rows if r["phase_valid"]]
    max_success_rpm = max((float(r["successful_requests_per_min"]) for r in valid_rows), default=0.0)
    profile = OFFICIAL_EXCHANGE_RATE_LIMITS.get(probe.exchange)
    safe_cpm = float(profile.safe_governor_calls_per_min) if profile else 0.0
    buffer_factor = max(0.5, min(0.999, 1.0 - (buffer_pct / 100.0)))
    recommendation = min(max_success_rpm, safe_cpm) * buffer_factor if safe_cpm > 0 else max_success_rpm * buffer_factor

    return {
        "exchange": probe.exchange,
        "probe": probe.name,
        "url": probe.url,
        "phase_results": rows,
        "official_safe_calls_per_min": round(safe_cpm, 2),
        "max_successful_requests_per_min": round(max_success_rpm, 2),
        "buffer_pct": buffer_pct,
        "recommended_runtime_calls_per_min": round(recommendation, 2),
        "benchmark_valid": len(valid_rows) > 0,
        "stress_profile": stress_profile,
    }


def _env_var_for_exchange(exchange: str) -> str:
    mapping = {
        "binance": "UNIFIED_BINANCE_CALLS_PER_MIN",
        "kraken": "UNIFIED_KRAKEN_CALLS_PER_MIN",
        "alpaca": "UNIFIED_ALPACA_CALLS_PER_MIN",
        "capital": "UNIFIED_CAPITAL_CALLS_PER_MIN",
    }
    return mapping.get(exchange, f"UNIFIED_{exchange.upper()}_CALLS_PER_MIN")


def write_env_recommendations(results: List[Dict[str, object]], path: Path) -> None:
    lines = ["# Generated by benchmark_exchange_api_limits.py", "# Apply in runtime env before launch"]
    for row in results:
        ex = str(row.get("exchange") or "").lower()
        rec = float(row.get("recommended_runtime_calls_per_min") or 0.0)
        var = _env_var_for_exchange(ex)
        lines.append(f"{var}={int(max(1, round(rec)))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv_round_runs(run_results: List[Dict[str, object]], path: Path) -> None:
    headers = [
        "round","exchange","phase","duration_sec","target_qps","concurrency","submitted","ok","errors",
        "successful_requests_per_min","observed_requests_per_min","safe_calls_per_min","pct_of_safe_limit","phase_valid"
    ]
    rows = [",".join(headers)]
    for run in run_results:
        rnd = run.get("round")
        for exrow in run.get("results", []):
            exchange = exrow.get("exchange")
            for ph in exrow.get("phase_results", []):
                vals = [
                    rnd, exchange, ph.get("phase"), ph.get("duration_sec"), ph.get("target_qps"), ph.get("concurrency"),
                    ph.get("submitted"), ph.get("ok"), ph.get("errors"), ph.get("successful_requests_per_min"),
                    ph.get("observed_requests_per_min"), ph.get("safe_calls_per_min"), ph.get("pct_of_safe_limit"), ph.get("phase_valid"),
                ]
                rows.append(",".join(str(v) for v in vals))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-duration-sec", type=int, default=10)
    ap.add_argument("--timeout-sec", type=float, default=4.0)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--buffer-pct", type=float, default=1.0, help="Safety buffer percentage below measured/safe limit")
    ap.add_argument("--exchanges", default="all", help="Comma list: binance,kraken,alpaca,capital or all")
    ap.add_argument("--rounds", type=int, default=1, help="Repeat full benchmark N times")
    ap.add_argument("--stress-profile", default="standard", choices=["conservative","standard","aggressive"])
    ap.add_argument("--out", default="state/exchange_api_rate_benchmark.json")
    ap.add_argument("--env-out", default="state/exchange_api_rate_benchmark.env")
    ap.add_argument("--csv-out", default="state/exchange_api_rate_benchmark_rounds.csv")
    args = ap.parse_args()

    wanted = {x.strip().lower() for x in str(args.exchanges).split(",") if x.strip()} if str(args.exchanges).lower() != "all" else set()
    selected = [p for p in PROBES if not wanted or p.exchange in wanted]
    if not selected:
        raise SystemExit("No probes selected. Use --exchanges all or a valid comma list.")

    rounds = max(1, int(args.rounds))
    run_results = []
    for i in range(rounds):
        rows = [benchmark_probe(p, args.phase_duration_sec, args.timeout_sec, args.concurrency, args.buffer_pct, args.stress_profile) for p in selected]
        run_results.append({"round": i + 1, "results": rows})

    # flatten best recommendation per exchange across rounds
    best = {}
    for run in run_results:
        for row in run["results"]:
            ex = row["exchange"]
            cur = float(row.get("recommended_runtime_calls_per_min", 0.0) or 0.0)
            if ex not in best or cur > float(best[ex].get("recommended_runtime_calls_per_min", 0.0) or 0.0):
                best[ex] = row
    results = list(best.values())
    report = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase_duration_sec": args.phase_duration_sec,
        "concurrency": args.concurrency,
        "buffer_pct": args.buffer_pct,
        "rounds": rounds,
        "stress_profile": args.stress_profile,
        "selected_exchanges": [p.exchange for p in selected],
        "results": results,
        "round_runs": run_results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_env_recommendations(results, Path(args.env_out))
    write_csv_round_runs(run_results, Path(args.csv_out))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
