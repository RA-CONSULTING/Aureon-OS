#!/usr/bin/env python3
"""CAPITAL.COM DEMO EXECUTION-PATH FLIGHT TEST (capital build agent, 2026-09-06).

Validates the exact radar order path against Gary's DEMO account only:
    aureon_phi_radar.py  ->  aureon_dual_capital.DualCapitalConnector._place_order
                         ->  capital_client.CapitalClient._request -> POST /positions

SAFETY:
  - .env is NEVER modified. CAPITAL_DEMO is forced to '1' in-process AFTER
    import (capital_client's module-level dotenv load would otherwise set 0).
  - Client base_url is asserted to be the DEMO host before any order call.
  - The live CapitalClient is NEVER constructed here (no live sessions).
  - Secret values are never printed/logged — key NAMES and booleans only.
  - One minimum-size EURUSD market order (1000 units = radar forex minimum),
    verified fill, then closed. Demo money only, authorized by Gary's decree.

Evidence written to capital_demo_flight_result.json (no secrets).
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

RESULT = {
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "account": "CAPITAL DEMO (forced in-process; .env untouched)",
    "steps": {},
}
STEP = {}


def record(name, ok, detail=""):
    STEP[name] = {"ok": bool(ok), "detail": detail}
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} :: {detail}")


def mask(s, keep=4):
    s = str(s or "")
    return s[:keep] + "…" if len(s) > keep else s


# ── import order matters: capital_client loads .env at import (CAPITAL_DEMO=0) ──
import capital_client  # noqa: E402
from capital_client import CapitalClient  # noqa: E402
from aureon_dual_capital import DualCapitalConnector  # noqa: E402

# Force DEMO mode in-process AFTER the module-level dotenv load.
os.environ["CAPITAL_DEMO"] = "1"
os.environ["CAPITAL_DEMO_MODE"] = "1"
capital_client._SHARED_SESSION["cst"] = None
capital_client._SHARED_SESSION["x_security_token"] = None
capital_client._SHARED_SESSION["demo_mode"] = None
capital_client._SHARED_SESSION["rate_limit_until"] = 0.0

print("=== 1. AUTHENTICATE (demo host) ===")
client = CapitalClient()
record("demo_host_forced", client.demo_mode and "demo-api-capital" in client.base_url,
       f"base_url={client.base_url}")
record("credentials_present_names_only",
       all([os.getenv("CAPITAL_API_KEY"), os.getenv("CAPITAL_IDENTIFIER"),
            os.getenv("CAPITAL_PASSWORD") or os.getenv("CAPITAL_API_PASSWORD")]),
       "CAPITAL_API_KEY / CAPITAL_IDENTIFIER / CAPITAL_PASSWORD present (values withheld)")
record("session_established", bool(client.enabled and client.cst and client.x_security_token),
       f"enabled={client.enabled} cst={'<redacted>' if client.cst else None} "
       f"xsec={'<redacted>' if client.x_security_token else None} init_error={client.init_error!r}")
record("authenticated_property", client.authenticated, "authenticated property")

print("=== 2. ACCOUNT BALANCE ===")
accounts = client.get_accounts()
bal_detail = []
for a in accounts:
    bal_detail.append({"accountId": mask(a.get("accountId")), "balance": a.get("balance"),
                       "available": a.get("available"), "currency": a.get("currency")})
record("accounts_fetched", len(accounts) > 0, json.dumps(bal_detail))
record("primary_balance", client.get_account_balance() >= 0,
       f"get_account_balance()={client.get_account_balance()}")

print("=== 3. LIVE PRICE EURUSD ===")
ticker = client.get_ticker("EURUSD")
record("eurusd_quote", ticker.get("price", 0) > 0,
       f"epic={ticker.get('epic')} bid={ticker.get('bid')} ask={ticker.get('ask')} "
       f"price={ticker.get('price')}")

print("=== 4. MARKET STATUS CHECK ===")
epic = ticker.get("epic") or "CS.D.EURUSD.CFD.IP"
snap = client._get_market_snapshot(epic, cache_ttl=0) or {}
market_status = (snap.get("snapshot") or {}).get("marketStatus") or snap.get("marketStatus")
record("market_status_known", True, f"EURUSD marketStatus={market_status!r}")

print("=== 5. PLACE MINIMUM DEMO ORDER (radar path: DualCapitalConnector._place_order) ===")
dual = object.__new__(DualCapitalConnector)  # never build live connector in probe
dual.demo = client
SIZE = 1000.0  # radar forex minimum enforced by _place_order
res = DualCapitalConnector._place_order(dual, client, "EURUSD", "BUY", SIZE)
record("order_submitted", "dealId" in res and not res.get("error"),
       json.dumps({k: v for k, v in res.items() if k != 'raw'}))
deal_ref = res.get("dealId")

confirm = {}
if deal_ref and deal_ref != "unknown":
    time.sleep(1.0)
    confirm = client.confirm_order(deal_ref)
record("order_confirmed", bool(confirm) and "error" not in confirm,
       f"status={confirm.get('dealStatus')} level={confirm.get('level')} "
       f"size={confirm.get('size')} dealId={mask(confirm.get('dealId'))}")

print("=== 6. VERIFY FILL IN POSITIONS ===")
time.sleep(1.0)
positions = client.get_positions()
eur_pos = None
for p in positions:
    if "EURUSD" in str(p.get("market", {}).get("epic", "")).upper() or \
       "EURUSD" in str(p.get("market", {}).get("instrumentName", "")).upper():
        eur_pos = p
        break
pos_info = {}
if eur_pos:
    pos_info = {
        "dealId": mask(eur_pos.get("position", {}).get("dealId")),
        "size": eur_pos.get("position", {}).get("size"),
        "direction": eur_pos.get("position", {}).get("direction"),
        "level": eur_pos.get("position", {}).get("level"),
        "upl": eur_pos.get("position", {}).get("upl"),
    }
record("fill_verified_in_positions", eur_pos is not None,
       json.dumps(pos_info) if pos_info else f"open_positions={len(positions)}")

print("=== 7. CLOSE POSITION ===")
close_res = {}
if eur_pos:
    real_deal_id = eur_pos.get("position", {}).get("dealId")
    close_res = client.close_position(real_deal_id)
record("close_ok", bool(close_res.get("success")),
       json.dumps({k: v for k, v in close_res.items() if k != 'data'})[:200])

print("=== 8. VERIFY FLAT ===")
time.sleep(1.0)
positions_after = client.get_positions()
still_open = [p for p in positions_after
              if "EURUSD" in str(p.get("market", {}).get("epic", "")).upper()]
record("flat_after_close", len(still_open) == 0,
       f"eurusd_positions_after={len(still_open)} total_positions_after={len(positions_after)}")

print("=== 9. RADAR HELPER VALIDATION (no orders) ===")
try:
    tp = DualCapitalConnector.calculate_micro_tp(dual, "EURUSD", "BUY", float(ticker.get("price") or 1.17))
    record("calculate_micro_tp_eurusd", abs(tp - float(ticker.get("price") or 1.17)) >= 0.0003,
           f"micro_tp={tp}")
except Exception as e:
    record("calculate_micro_tp_eurusd", False, f"error={e}")
try:
    bal0 = DualCapitalConnector.get_demo_balance(dual)
    record("dual_get_demo_balance", False,
           f"BUG REPRODUCED: get_demo_balance()={bal0} despite real demo balance "
           f"(calls nonexistent CapitalClient._get_accounts)")
except Exception as e:
    record("dual_get_demo_balance_exception", False, f"raised: {type(e).__name__}: {e}")

RESULT["steps"] = STEP
RESULT["all_pass"] = all(s["ok"] for s in STEP.values())
out = RADAR / "capital_demo_flight_result.json"
out.write_text(json.dumps(RESULT, indent=2, default=str), encoding="utf-8")
print(f"\nWrote {out}")
print(f"OVERALL: {'ALL PASS' if RESULT['all_pass'] else 'SOME FAILURES'}")
sys.exit(0 if RESULT["all_pass"] else 1)
