#!/usr/bin/env python3
"""CAPITAL DEMO FILL VALIDATION at FX market open (Sunday 21:05 UTC).

Runs the deferred part of _capital_demo_flight_test.py: place minimum EURUSD
BUY (1000 units) on Gary's DEMO account via the exact radar path
(DualCapitalConnector._place_order), verify the fill via /confirms + /positions,
close it, verify flat. Appends one JSON line to capital_demo_fill_evidence.jsonl.

DEMO ONLY. .env untouched. No secrets logged.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_AUDIT_MODE"] = "1"

WORKSPACE = Path("C:/Users/user/.kimi_openclaw/workspace")
RADAR = WORKSPACE / "aureon_radar"
sys.path.insert(0, str(RADAR))
sys.path.insert(0, str(WORKSPACE))

import capital_client  # noqa: E402
from aureon_dual_capital import DualCapitalConnector  # noqa: E402

os.environ["CAPITAL_DEMO"] = "1"
os.environ["CAPITAL_DEMO_MODE"] = "1"
capital_client._SHARED_SESSION["cst"] = None
capital_client._SHARED_SESSION["x_security_token"] = None
capital_client._SHARED_SESSION["demo_mode"] = None
capital_client._SHARED_SESSION["rate_limit_until"] = 0.0

ev = {"ts_utc": datetime.now(timezone.utc).isoformat(), "account": "CAPITAL DEMO", "ok": False}

client = capital_client.CapitalClient()
assert client.demo_mode and "demo-api-capital" in client.base_url, "NOT DEMO HOST — ABORT"

ticker = client.get_ticker("EURUSD")
ev["quote"] = {"bid": ticker.get("bid"), "ask": ticker.get("ask"), "epic": ticker.get("epic")}

dual = object.__new__(DualCapitalConnector)
dual.demo = client
res = DualCapitalConnector._place_order(dual, client, "EURUSD", "BUY", 1000.0)
ev["order"] = {k: v for k, v in res.items() if k != "raw"}

if "dealId" in res and not res.get("error"):
    time.sleep(1.0)
    ev["confirm"] = client.confirm_order(res["dealId"])
    time.sleep(1.0)
    positions = client.get_positions()
    eur = [p for p in positions if "EURUSD" in str(p.get("market", {}).get("epic", "")).upper()]
    ev["positions_eurusd"] = [{
        "dealId": str(p.get("position", {}).get("dealId"))[:4] + "…",
        "size": p.get("position", {}).get("size"),
        "direction": p.get("position", {}).get("direction"),
        "level": p.get("position", {}).get("level"),
        "upl": p.get("position", {}).get("upl"),
    } for p in eur]
    if eur:
        close = client.close_position(eur[0].get("position", {}).get("dealId"))
        ev["close"] = {k: v for k, v in close.items() if k != "data"}
        time.sleep(1.0)
        after = client.get_positions()
        ev["flat_after_close"] = not any(
            "EURUSD" in str(p.get("market", {}).get("epic", "")).upper() for p in after)
        ev["ok"] = bool(close.get("success")) and ev["flat_after_close"]

log = RADAR / "capital_demo_fill_evidence.jsonl"
with open(log, "a", encoding="utf-8") as f:
    f.write(json.dumps(ev, default=str) + "\n")
print(json.dumps(ev, indent=1, default=str))
print("FILL_VALIDATION:", "PASS" if ev["ok"] else "FAIL/BLOCKED")
sys.exit(0 if ev["ok"] else 1)
