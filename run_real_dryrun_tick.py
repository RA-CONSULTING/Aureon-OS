#!/usr/bin/env python3
"""
REAL MARKET DATA — DRY RUN CYCLE
══════════════════════════════════════════════════════════════════
Runs ONE unified market tick with REAL price feeds from Binance,
Kraken, Alpaca and Capital — but ZERO real orders (dry_run=True).
Shows exactly what the system would open/close with live data.
"""
import sys
import time
import json
import logging

# SILENCE ALL LOGGING before any imports
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
for handler in logging.root.handlers[:]:
    handler.setLevel(logging.WARNING)
logging.root.setLevel(logging.WARNING)

sys.path.insert(0, r"C:\Users\user\aureon-trading")

# Force synchronous exchange initialization so we actually get real data
import aureon.exchanges.unified_market_trader as umt_mod
umt_mod.EXCHANGE_BOOT_ASYNC_ENABLED = False
umt_mod.EXCHANGE_SYNC_RETRY_ENABLED = True

from aureon.exchanges.unified_market_trader import UnifiedMarketTrader

print("=" * 70)
print("  REAL MARKET DATA — DRY RUN TICK")
print("  ✅ Prices are LIVE  |  ❌ Orders are BLOCKED")
print("=" * 70)

start = time.time()
print("\n📡 Initializing UnifiedMarketTrader (dry_run=True, sync boot)...")
sys.stdout.flush()

try:
    trader = UnifiedMarketTrader(dry_run=True, setup_kraken_cli=False)
except Exception as e:
    print(f"\n❌ Initialization failed: {e}")
    sys.exit(1)

init_elapsed = time.time() - start
print(f"   ✅ Initialized in {init_elapsed:.1f}s")
print(f"      Kraken ready: {trader.kraken_ready}")
print(f"      Capital ready: {trader.capital_ready}")
print(f"      Alpaca ready: {getattr(trader, 'alpaca_ready', False)}")
print(f"      Binance ready: {getattr(trader, 'binance_ready', False)}")
print(f"      Dry run: {trader.dry_run}")
sys.stdout.flush()

# If Capital isn't ready, show why
if not trader.capital_ready and getattr(trader, 'capital', None):
    print(f"      Capital error: {getattr(trader, 'capital_error', 'unknown')}")
    print(f"      Capital enabled: {getattr(trader.capital, 'enabled', False)}")
    sys.stdout.flush()

print("\n🔄 Executing ONE tick with real market data...")
sys.stdout.flush()

tick_start = time.time()
try:
    result = trader.tick()
except Exception as e:
    print(f"\n❌ Tick failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

tick_elapsed = time.time() - tick_start

print(f"\n✅ Tick completed in {tick_elapsed:.2f}s")
print("-" * 50)

# Show closed trades
kraken_closed = result.get("kraken_closed", [])
kraken_spot_closed = result.get("kraken_spot_closed", [])
capital_closed = result.get("capital_closed", [])

if kraken_closed:
    print(f"\n🔴 Kraken margin CLOSED: {len(kraken_closed)}")
    for t in kraken_closed:
        pnl = t.get("realized_pnl", t.get("pnl", 0))
        print(f"      {t.get('symbol','?')}  PnL: {pnl}")

if kraken_spot_closed:
    print(f"\n🔴 Kraken spot CLOSED: {len(kraken_spot_closed)}")
    for t in kraken_spot_closed:
        pnl = t.get("realized_pnl", t.get("pnl", 0))
        print(f"      {t.get('symbol','?')}  PnL: {pnl}")

if capital_closed:
    print(f"\n🔴 Capital CFD CLOSED: {len(capital_closed)}")
    for t in capital_closed:
        pnl = t.get("pnl_gbp", t.get("pnl", 0))
        print(f"      {t.get('symbol','?')}  PnL: £{pnl}")

if not (kraken_closed or kraken_spot_closed or capital_closed):
    print("\n🟡 No positions closed this tick")

# Show current state
print("\n📊 CURRENT STATE")
print("-" * 50)
try:
    state = trader.get_local_dashboard_state()
    combined = state.get("combined", {})
    print(f"   Open positions: {combined.get('open_positions', 'N/A')}")
    print(f"   Kraken equity:  ${combined.get('kraken_equity', 'N/A')}")
    print(f"   Capital equity: £{combined.get('capital_equity_gbp', 'N/A')}")
except Exception as e:
    print(f"   (State snapshot unavailable: {e})")

# Show latest prices sampled
print("\n📈 PRICE SNAPSHOT (from exchange feeds)")
print("-" * 50)
try:
    if getattr(trader, 'capital', None):
        prices = getattr(trader.capital, '_prices', {})
        if prices:
            for sym, data in list(prices.items())[:5]:
                print(f"   {sym}: bid={data.get('bid')} ask={data.get('ask')} price={data.get('price')}")
        else:
            print("   (No prices cached yet)")
except Exception as e:
    print(f"   (Price snapshot unavailable: {e})")

# Show latest target
if getattr(trader, 'capital', None) and getattr(trader.capital, '_latest_target_snapshot', {}):
    snap = trader.capital._latest_target_snapshot
    if snap.get('symbol'):
        print(f"\n🎯 Capital latest target:")
        print(f"   Symbol: {snap.get('symbol')}")
        print(f"   Direction: {snap.get('direction')}")
        print(f"   Size: {snap.get('size')}")
        print(f"   Preflight: {snap.get('preflight_reason') or 'N/A'}")

print("\n" + "=" * 70)
print(f"  DRY RUN COMPLETE — {tick_elapsed:.2f}s  (no real orders placed)")
print("=" * 70)
