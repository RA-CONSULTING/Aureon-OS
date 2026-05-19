#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

INTENT_LOG = Path("state/unified_exchange_order_intents.jsonl")
EXEC_LOG = Path("state/unified_exchange_execution_results.jsonl")
LIFECYCLE_LOG = Path("state/unified_order_lifecycle_events.jsonl")


def parse_iso(ts: str) -> Optional[float]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def tail_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            pass
    return out


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    idx = min(len(vs) - 1, max(0, int(round((p / 100.0) * (len(vs) - 1)))))
    return vs[idx]


def summarize(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    return {
        "count": len(values),
        "min_ms": round(min(values) * 1000, 3),
        "p50_ms": round(percentile(values, 50) * 1000, 3),
        "p95_ms": round(percentile(values, 95) * 1000, 3),
        "p99_ms": round(percentile(values, 99) * 1000, 3),
        "max_ms": round(max(values) * 1000, 3),
        "avg_ms": round(statistics.fmean(values) * 1000, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Expanded stress test for intelligence→trade latency")
    ap.add_argument("--tail", type=int, default=10000)
    ap.add_argument("--min-samples", type=int, default=25)
    ap.add_argument("--p95-budget-ms", type=float, default=900.0)
    ap.add_argument("--out", default="state/latency_stress_report.json")
    args = ap.parse_args()

    intents = tail_jsonl(INTENT_LOG, args.tail)
    execs = tail_jsonl(EXEC_LOG, args.tail)
    lifecycle = tail_jsonl(LIFECYCLE_LOG, args.tail * 5)

    intent_ts: Dict[str, float] = {}
    venue_by_lid: Dict[str, str] = {}
    for item in intents:
        ts = parse_iso(str(item.get("generated_at") or ""))
        for intent in item.get("intents", []):
            if isinstance(intent, dict):
                lid = str(intent.get("lifecycle_id") or "")
                if lid and ts is not None:
                    intent_ts[lid] = ts
                    routes = intent.get("routes", []) if isinstance(intent.get("routes"), list) else []
                    venue_by_lid[lid] = str((routes[0] if routes else {}).get("venue") or "unknown").lower()

    exec_ts: Dict[str, float] = {}
    for snap in execs:
        for res in snap.get("results", []):
            if not isinstance(res, dict):
                continue
            lid = str(res.get("lifecycle_id") or "")
            ts = parse_iso(str(res.get("generated_at") or ""))
            if lid and ts is not None and bool(res.get("ok")):
                exec_ts.setdefault(lid, ts)
                venue_by_lid.setdefault(lid, str(res.get("venue") or "unknown").lower())

    life_by_lid: Dict[str, Dict[str, float]] = {}
    for ev in lifecycle:
        lid = str(ev.get("lifecycle_id") or "")
        status = str(ev.get("status") or "")
        ts = parse_iso(str(ev.get("timestamp") or ev.get("generated_at") or ""))
        if not lid or ts is None:
            continue
        life_by_lid.setdefault(lid, {})
        life_by_lid[lid].setdefault(status, ts)
        venue_by_lid.setdefault(lid, str(ev.get("venue") or "unknown").lower())

    global_i2e: List[float] = []
    global_i2s: List[float] = []
    global_s2a: List[float] = []
    per_venue: Dict[str, Dict[str, List[float]]] = {}

    for lid, t0 in intent_ts.items():
        venue = venue_by_lid.get(lid, "unknown")
        per_venue.setdefault(venue, {"i2e": [], "i2s": [], "s2a": []})

        t_exec = exec_ts.get(lid)
        if t_exec and t_exec >= t0:
            d = t_exec - t0
            global_i2e.append(d)
            per_venue[venue]["i2e"].append(d)

        life = life_by_lid.get(lid, {})
        t_submit = life.get("order_submitted")
        t_ack = life.get("broker_acknowledged")
        if t_submit and t_submit >= t0:
            d = t_submit - t0
            global_i2s.append(d)
            per_venue[venue]["i2s"].append(d)
        if t_submit and t_ack and t_ack >= t_submit:
            d = t_ack - t_submit
            global_s2a.append(d)
            per_venue[venue]["s2a"].append(d)

    metrics = {
        "intent_to_execution_result": summarize(global_i2e),
        "intent_to_order_submitted": summarize(global_i2s),
        "order_submitted_to_broker_ack": summarize(global_s2a),
    }
    venue_metrics = {
        venue: {
            "intent_to_execution_result": summarize(vals["i2e"]),
            "intent_to_order_submitted": summarize(vals["i2s"]),
            "order_submitted_to_broker_ack": summarize(vals["s2a"]),
        }
        for venue, vals in per_venue.items()
    }

    pass_fail = {
        "min_samples_required": args.min_samples,
        "samples_found": len(global_i2s),
        "p95_budget_ms": args.p95_budget_ms,
        "p95_observed_ms": float(metrics.get("intent_to_order_submitted", {}).get("p95_ms", 0.0) or 0.0),
    }
    pass_fail["enough_samples"] = pass_fail["samples_found"] >= args.min_samples
    pass_fail["p95_within_budget"] = pass_fail["p95_observed_ms"] > 0 and pass_fail["p95_observed_ms"] <= args.p95_budget_ms
    pass_fail["stress_test_pass"] = bool(pass_fail["enough_samples"] and pass_fail["p95_within_budget"])

    report = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "input_counts": {
            "intent_snapshots": len(intents),
            "execution_snapshots": len(execs),
            "lifecycle_events": len(lifecycle),
            "lifecycles_with_intent": len(intent_ts),
        },
        "metrics": metrics,
        "metrics_by_venue": venue_metrics,
        "pass_fail": pass_fail,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not pass_fail["stress_test_pass"]:
        print("STRESS_TEST_FAIL: insufficient matched samples or p95 above budget")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
