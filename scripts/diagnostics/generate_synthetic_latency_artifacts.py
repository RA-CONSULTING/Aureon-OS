#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path


def iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic intent/execution/lifecycle artifacts for stress-tool validation")
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--venues", default="binance,kraken,alpaca,capital")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="state")
    args = ap.parse_args()

    random.seed(args.seed)
    venues = [v.strip().lower() for v in args.venues.split(",") if v.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    intent_log = out_dir / "unified_exchange_order_intents.jsonl"
    exec_log = out_dir / "unified_exchange_execution_results.jsonl"
    lifecycle_log = out_dir / "unified_order_lifecycle_events.jsonl"

    t0 = datetime.now(UTC) - timedelta(minutes=10)
    intents = []
    exec_snaps = []
    life_events = []

    for i in range(args.samples):
        venue = venues[i % len(venues)] if venues else "binance"
        symbol = "BTCUSDT" if venue in {"binance", "kraken"} else "SPY"
        lid = f"olife-synth-{i}"
        intent_id = f"uintent-synth-{i}"
        t_intent = t0 + timedelta(milliseconds=50 * i)
        dt_submit_ms = random.randint(40, 260)
        dt_ack_ms = random.randint(30, 220)
        dt_exec_ms = dt_submit_ms + random.randint(10, 90)
        t_submit = t_intent + timedelta(milliseconds=dt_submit_ms)
        t_ack = t_submit + timedelta(milliseconds=dt_ack_ms)
        t_exec = t_intent + timedelta(milliseconds=dt_exec_ms)

        intents.append({
            "generated_at": iso(t_intent),
            "intents": [{
                "id": intent_id,
                "lifecycle_id": lid,
                "routes": [{"venue": venue, "market_type": "spot", "symbol": symbol}],
            }],
        })

        exec_snaps.append({
            "generated_at": iso(t_exec),
            "results": [{"ok": True, "venue": venue, "lifecycle_id": lid, "generated_at": iso(t_exec)}],
        })

        life_events.extend([
            {"lifecycle_id": lid, "venue": venue, "status": "order_submitted", "timestamp": iso(t_submit)},
            {"lifecycle_id": lid, "venue": venue, "status": "broker_acknowledged", "timestamp": iso(t_ack)},
        ])

    intent_log.write_text("\n".join(json.dumps(x) for x in intents) + "\n", encoding="utf-8")
    exec_log.write_text("\n".join(json.dumps(x) for x in exec_snaps) + "\n", encoding="utf-8")
    lifecycle_log.write_text("\n".join(json.dumps(x) for x in life_events) + "\n", encoding="utf-8")

    print(json.dumps({"samples": args.samples, "venues": venues, "out_dir": str(out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
