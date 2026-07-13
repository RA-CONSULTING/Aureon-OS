#!/usr/bin/env python3
"""Quick Capital.com ticker diagnostic — shows change_pct format."""
import os, sys, io, time

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, ".env"), override=False)
except Exception:
    pass

print("Connecting to Capital.com...", flush=True)
from aureon.exchanges.capital_client import CapitalClient

client = CapitalClient()
if not client.enabled:
    print(f"Client disabled: {client.init_error}")
    sys.exit(1)

print(f"Session OK. Fetching tickers + raw snapshot...", flush=True)

SYMBOLS = ["EURUSD", "GBPUSD", "GOLD", "US500"]
for sym in SYMBOLS:
    # Fetch via updated get_ticker (now includes high/low)
    t = client.get_ticker(sym)
    print(f"  {sym:<12} price={t.get('price',0):.4f}  change_pct={t.get('change_pct',0):.4f}  high={t.get('high',0):.4f}  low={t.get('low',0):.4f}")

    # Also show raw snapshot fields
    try:
        market = client._resolve_market(sym) or {}
        epic = market.get('epic') or sym
        snap_resp = client._get_market_snapshot(epic) or {}
        snap = snap_resp.get('snapshot', {})
        print(f"    raw snap keys: {list(snap.keys())}")
        print(f"    bid={snap.get('bid')} offer={snap.get('offer')} high={snap.get('high')} low={snap.get('low')} pctChange={snap.get('percentageChange')}")
    except Exception as e:
        print(f"    raw snap error: {e}")

print("\nDone.", flush=True)
