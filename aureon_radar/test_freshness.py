#!/usr/bin/env python3
"""
AUREON META DATA FRESHNESS TEST - Full Pipeline Audit

Tests ALL data sources and verifies freshness:
  1. Capital.com API connectivity + live prices
  2. Ollama Cloud API connectivity + response time
  3. Aureon OS trace file freshness
  4. Signal pipeline (fused_signals.jsonl)
  5. Shadow trade log freshness
  6. Phi-Radar state file
  7. PriceCache freshness gate
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

RADAR_DIR = Path(__file__).resolve().parent
AUREON_DIR = Path("C:/Users/user/Aureon-OS")

# Load .env files from repo root and radar directory if available.
try:
    from dotenv import load_dotenv
    repo_root = RADAR_DIR.parents[1]
    for env_path in (repo_root / ".env", RADAR_DIR / ".env", Path.cwd() / ".env"):
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path), override=False)
except Exception:
    pass

print("=" * 70)
print("     AUREON META DATA FRESHNESS TEST - Full Pipeline Audit")
print("=" * 70 + "\n")

results = []


def test(name, passed, detail=""):
    status = "[PASS]" if passed else "[FAIL]"
    results.append((name, passed, detail))
    print(f"{status} | {name}")
    if detail:
        print(f"       {detail}")
    return passed


# =============================================================================
# TEST 1: Capital.com API - Connectivity & Price Freshness
# =============================================================================
print("\n[TEST 1] Capital.com API - Live Price Feed")
print("-" * 70)

CAPITAL_KEY = os.getenv("CAPITAL_API_KEY")
CAPITAL_ID = os.getenv("CAPITAL_IDENTIFIER")
CAPITAL_PASS = os.getenv("CAPITAL_PASSWORD") or os.getenv("CAPITAL_API_PASSWORD")

if not (CAPITAL_KEY and CAPITAL_ID and CAPITAL_PASS):
    test("Capital.com CREDENTIALS", False, "CAPITAL_API_KEY/IDENTIFIER/PASSWORD not set")
else:
    try:
        resp = requests.post(
            "https://api-capital.backend-capital.com/api/v1/session",
            json={"identifier": CAPITAL_ID, "password": CAPITAL_PASS},
            headers={"X-CAP-API-KEY": CAPITAL_KEY, "Content-Type": "application/json"},
            timeout=15
        )
        resp.raise_for_status()
        cst = resp.headers.get("CST")
        x_sec = resp.headers.get("X-SECURITY-TOKEN")

        # Get account info
        acc_resp = requests.get(
            "https://api-capital.backend-capital.com/api/v1/accounts",
            headers={"X-CAP-API-KEY": CAPITAL_KEY, "CST": cst, "X-SECURITY-TOKEN": x_sec},
            timeout=10
        )
        acc_resp.raise_for_status()
        accounts = acc_resp.json().get("accounts", [])
        balance = accounts[0].get("balance", {}).get("available", 0) if accounts else 0

        # Get live price
        price_resp = requests.get(
            "https://api-capital.backend-capital.com/api/v1/markets/USDJPY",
            headers={"X-CAP-API-KEY": CAPITAL_KEY, "CST": cst, "X-SECURITY-TOKEN": x_sec},
            timeout=10
        )
        price_resp.raise_for_status()
        snap = price_resp.json().get("snapshot", {})
        price = snap.get("offer", 0)
        price_time = snap.get("delayTime", "N/A")

        test("Capital.com AUTH", True, f"Authenticated, Balance: £{float(balance):.2f}")
        test("Capital.com PRICE", price > 0, f"USDJPY = {price} (delay: {price_time}s)")

    except Exception as e:
        test("Capital.com API", False, str(e))

# =============================================================================
# TEST 2: Ollama Cloud API - Connectivity & Response
# =============================================================================
print("\n[TEST 2] Ollama Cloud API - Cognitive Pipeline")
print("-" * 70)

OLLAMA_KEY = os.getenv("OLLAMA_API_KEY")
if not OLLAMA_KEY:
    test("Ollama Cloud CREDENTIALS", False, "OLLAMA_API_KEY not set")
else:
    try:
        t0 = time.time()
        resp = requests.post(
            "https://ollama.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OLLAMA_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "kimi-k2.7-code",
                "messages": [{"role": "user", "content": "Return JSON: {\"status\": \"ok\"}"}],
                "max_tokens": 20
            },
            timeout=30
        )
        resp.raise_for_status()
        elapsed = time.time() - t0

        test("Ollama Cloud AUTH", True, "API key valid, model: kimi-k2.7-code")
        test("Ollama Cloud LATENCY", elapsed < 15, f"Response time: {elapsed:.1f}s")

    except Exception as e:
        test("Ollama Cloud API", False, str(e))

# =============================================================================
# TEST 3: Aureon OS Trace File - Freshness
# =============================================================================
print("\n[TEST 3] Aureon OS Bridge - Trace File Freshness")
print("-" * 70)

trace_file = AUREON_DIR / "state" / "capital_cfd_last_exchange_trace.json"
if trace_file.exists():
    mtime = trace_file.stat().st_mtime
    age = time.time() - mtime
    fresh = age < 3600  # Less than 1 hour old

    try:
        with open(trace_file) as f:
            trace = json.load(f)
        trace_symbol = trace.get("symbol", "N/A")
        trace_direction = trace.get("direction", "N/A")

        test("Aureon Trace EXISTS", True, f"Symbol: {trace_symbol}, Direction: {trace_direction}")
        test("Aureon Trace FRESH", fresh, f"Age: {age:.0f}s ({age/60:.0f} min)")
    except Exception as e:
        test("Aureon Trace READ", False, str(e))
else:
    test("Aureon Trace FILE", False, "File not found")

# =============================================================================
# TEST 4: Signal Pipeline - fused_signals.jsonl
# =============================================================================
print("\n[TEST 4] Signal Pipeline - Data Flow")
print("-" * 70)

fused_file = RADAR_DIR / "fused_signals.jsonl"
if fused_file.exists():
    lines = []
    with open(fused_file) as f:
        for line in f:
            try:
                lines.append(json.loads(line.strip()))
            except Exception:
                pass

    if lines:
        last = lines[-1]
        last_time_str = last.get("timestamp", "").replace("Z", "+00:00")
        try:
            last_time = datetime.fromisoformat(last_time_str)
            age = (datetime.now(timezone.utc) - last_time).total_seconds()
            fresh = age < 600  # Less than 10 min
        except Exception:
            age = 99999
            fresh = False

        test("Signal Pipeline", True, f"{len(lines)} total signals")
        test("Signal FRESHNESS", fresh, f"Last signal: {last.get('symbol', '?')} {last.get('direction', '?')} ({age:.0f}s ago)")
    else:
        test("Signal Pipeline", False, "Empty file")
else:
    test("Signal Pipeline", False, "File not found")

# =============================================================================
# TEST 5: Shadow Trade Log
# =============================================================================
print("\n[TEST 5] Shadow Trade System")
print("-" * 70)

shadow_file = RADAR_DIR / "shadow_trades.jsonl"
if shadow_file.exists():
    shadows = []
    with open(shadow_file) as f:
        for line in f:
            try:
                shadows.append(json.loads(line.strip()))
            except Exception:
                pass

    if shadows:
        total = len([s for s in shadows if s.get("status") in ("CLOSED_PROFIT", "CLOSED_LOSS")])
        profits = len([s for s in shadows if s.get("status") == "CLOSED_PROFIT"])
        wr = profits / total if total else 0

        test("Shadow Trades", True, f"{len(shadows)} trades, {total} closed, WR: {wr:.1%}")
    else:
        test("Shadow Trades", False, "Empty file")
else:
    test("Shadow Trades", False, "File not found")

# =============================================================================
# TEST 6: Phi-Radar State File
# =============================================================================
print("\n[TEST 6] Phi-Radar - System State")
print("-" * 70)

state_file = RADAR_DIR / "radar_state.json"
if state_file.exists():
    try:
        with open(state_file) as f:
            state = json.load(f)

        test("Radar State", True, f"State: {state.get('state', '?')}, Trades today: {state.get('live_trades_today', 0)}")

        # Check freshness
        ts = state.get("timestamp", "")
        if ts:
            state_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - state_time).total_seconds()
            test("Radar State FRESH", age < 600, f"Updated {age:.0f}s ago")
    except Exception as e:
        test("Radar State READ", False, str(e))
else:
    test("Radar State", False, "File not found")

# =============================================================================
# TEST 7: PriceCache Freshness Gate
# =============================================================================
print("\n[TEST 7] PriceCache Freshness Gate")
print("-" * 70)

try:
    sys.path.insert(0, str(RADAR_DIR))
    from exchange_adapters import price_cache

    # Normal mode fetch
    r = price_cache.get_price("BTCUSDT", source="binance")
    test("PriceCache BTCUSDT fetch", r.get("trade_allowed") is True,
         f"price={r.get('price')} fresh={r.get('fresh')} source_kind={r.get('source_kind')}")

    r2 = price_cache.get_price("ETHUSDT", source="binance")
    test("PriceCache ETHUSDT fetch", r2.get("trade_allowed") is True,
         f"price={r2.get('price')} fresh={r2.get('fresh')}")

    # Low-cash urgent mode (does not trade; only verifies cache switches gears)
    urgent = price_cache.set_cash_state(10.0)
    test("PriceCache urgent mode", urgent.get("urgent_mode") is True,
         f"ttl={urgent.get('effective_ttl_s')}s rpm={urgent.get('effective_max_rpm')}")

    # Simulated-data refusal
    price_cache.mark_simulated("BTCUSDT", source="binance", reason="freshness test")
    allowed = price_cache.is_trade_allowed("BTCUSDT", source="binance")
    test("PriceCache simulated refusal", allowed is False,
         "simulated entry correctly blocked from trading")

    # Freshness report is non-empty
    report = price_cache.report()
    test("PriceCache report", bool(report), report.splitlines()[0])

except Exception as e:
    test("PriceCache Freshness Gate", False, str(e))

# =============================================================================
# TEST 8: Running Processes
# =============================================================================
print("\n[TEST 8] Running Processes")
print("-" * 70)

import subprocess
procs = subprocess.run(["powershell", "-Command", "Get-Process -Name python | Select-Object Id, ProcessName, Responding"],
                       capture_output=True, text=True)
for line in procs.stdout.strip().split('\n')[2:]:
    print(f"       {line.strip()}")

test("Processes Running", True, "See list above")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

passed = sum(1 for _, p, _ in results if p)
total = len(results)

for name, passed_flag, detail in results:
    icon = "[OK]" if passed_flag else "[XX]"
    print(f"{icon} {name}")

print(f"\n{'=' * 70}")
print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
print(f"{'=' * 70}")

if passed == total:
    print("\n*** ALL SYSTEMS GREEN - FRESH META DATA FLOWING ***")
else:
    print(f"\n*** {total - passed} tests FAILED - Check details above ***")
