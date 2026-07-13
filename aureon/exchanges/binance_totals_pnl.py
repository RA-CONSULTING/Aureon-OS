#!/usr/bin/env python3
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Tuple

from aureon.exchanges.binance_client import BinanceClient, get_binance_client

BASELINE_FILE = "pnl_baseline.json"


def load_baseline() -> Dict:
    if os.path.exists(BASELINE_FILE):
        try:
            with open(BASELINE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_baseline(total_value: float, details: Dict):
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_value_usdc": round(total_value, 8),
        "details": details,
    }
    with open(BASELINE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return data


def get_usdc_price(client: BinanceClient, asset: str, usdt_usdc: float) -> Tuple[float, str]:
    if asset == "USDC":
        return 1.0, "USDC"
    # Try direct USDC pair
    sym = f"{asset}USDC"
    try:
        t = client.get_ticker(sym)
        p = float(t.get("lastPrice"))
        if p > 0:
            return p, sym
    except Exception:
        pass
    # Fallback: USDT pair then convert via USDTUSDC
    sym2 = f"{asset}USDT"
    try:
        t = client.get_ticker(sym2)
        p = float(t.get("lastPrice"))
        if p > 0 and usdt_usdc > 0:
            return p * usdt_usdc, sym2 + "*USDTUSDC"
    except Exception:
        pass
    return 0.0, "(no price)"


def compute_total_account_value(client: BinanceClient) -> Tuple[float, Dict, Dict]:
    # Price for USDT in USDC
    usdt_usdc = 1.0
    try:
        t = client.get_ticker("USDTUSDC")
        usdt_usdc = float(t.get("lastPrice", 1.0)) or 1.0
    except Exception:
        pass

    acct = client.account()
    balances = acct.get("balances", [])

    breakdown = {}
    details = {}
    total_value = 0.0

    for b in balances:
        asset = b["asset"]
        free = float(b.get("free", 0))
        locked = float(b.get("locked", 0))
        qty = free + locked
        if qty <= 0:
            continue

        price_usdc, ref = get_usdc_price(client, asset, usdt_usdc)
        value = qty * price_usdc
        if value > 0:
            total_value += value
        breakdown[asset] = {
            "qty": qty,
            "price_usdc": price_usdc,
            "value_usdc": value,
            "ref": ref,
        }

    # Sort details for display
    details = dict(sorted(breakdown.items(), key=lambda kv: kv[1]["value_usdc"], reverse=True))
    return total_value, details, {"usdt_usdc": usdt_usdc}


def print_report(total_now: float, details: Dict, baseline: Dict):
    print("📊 BINANCE TOTAL ACCOUNT VALUE (USDC)")
    print("=" * 72)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Timestamp: {ts}")
    print(f"Current Total Value: ${total_now:,.4f}")

    if baseline and "total_value_usdc" in baseline:
        base = float(baseline["total_value_usdc"]) or 0.0
        delta = total_now - base
        pct = (delta / base * 100.0) if base > 0 else 0.0
        print(f"Baseline Value:      ${base:,.4f} (at {baseline.get('timestamp')})")
        print(f"Delta:               ${delta:,.4f} ({pct:+.2f}%)")
    else:
        print("Baseline Value:      (not set)")

    print("\nTop Holdings (by USDC value):")
    print("Asset    Qty            Price(USDC)   Value(USDC)   Ref")
    print("-" * 72)
    shown = 0
    for asset, info in details.items():
        if info["value_usdc"] <= 0.0:
            continue
        print(
            f"{asset:6s}  {info['qty']:12.6f}  {info['price_usdc']:12.6f}  {info['value_usdc']:12.4f}   {info['ref']}"
        )
        shown += 1
        if shown >= 15:
            break


def main():
    args = sys.argv[1:]
    reset = "--reset-baseline" in args
    show = "--show-baseline" in args

    client = get_binance_client()

    total_now, details, meta = compute_total_account_value(client)

    baseline = load_baseline()
    if reset or not baseline:
        baseline = save_baseline(total_now, {"meta": meta, "note": "Baseline set"})
        print("✅ Baseline saved.")

    if show:
        print("\nSaved Baseline:")
        print(json.dumps(baseline, indent=2))
        print()

    print_report(total_now, details, baseline)

    # Also compute quick realized PnL for USDC pairs in last N trades (best-effort)
    try:
        print("\nQuick Realized PnL (best-effort, USDC pairs only, last 50 trades per symbol):")
        info = client.exchange_info()
        usdc_symbols = [s["symbol"] for s in info.get("symbols", []) if s.get("quoteAsset") == "USDC" and s.get("status") == "TRADING"]
        realized = 0.0
        fees = 0.0
        count = 0
        for sym in usdc_symbols[:50]:  # Limit scope
            try:
                trades = client.get_my_trades(sym, limit=50)
                for t in trades:
                    qty = float(t["qty"])
                    price = float(t["price"])
                    value = qty * price
                    fee = float(t["commission"]) if t.get("commissionAsset") == "USDC" else 0.0
                    fees += fee
                    if t["isBuyer"]:
                        realized -= value
                    else:
                        realized += value
                    count += 1
            except Exception:
                pass
        print(f"  Trades analyzed: {count}")
        print(f"  Gross realized:  ${realized:.4f}")
        print(f"  Fees (USDC):     ${fees:.6f}")
        print(f"  Net realized:    ${realized - fees:.6f}")
    except Exception as e:
        print(f"(Skip realized PnL summary: {e})")


if __name__ == "__main__":
    main()
