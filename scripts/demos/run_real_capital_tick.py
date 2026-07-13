#!/usr/bin/env python3
"""
REAL CAPITAL CFD TICK — DRY RUN with per-phase timing
"""
import sys
import time
import threading
import logging
import traceback

logging.basicConfig(level=logging.WARNING)
for name in list(logging.root.manager.loggerDict):
    logging.getLogger(name).setLevel(logging.WARNING)

sys.path.insert(0, r"C:\Users\user\aureon-trading")

from aureon.exchanges import capital_cfd_trader as cfd_mod
from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader

cfd_mod.HAS_CAPITAL = True

print("=" * 70)
print("  REAL CAPITAL CFD TICK — PHASE TIMING DIAGNOSTIC")
print("=" * 70)

print("\n📡 Initializing CapitalCFDTrader...")
sys.stdout.flush()
start = time.time()

trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
trader._live_refresh_stop = threading.Event()
trader._live_refresh_thread = None
CapitalCFDTrader.__init__(trader)

if trader._live_refresh_thread and trader._live_refresh_thread.is_alive():
    trader._live_refresh_stop.set()
    trader._live_refresh_thread.join(timeout=2.0)

init_elapsed = time.time() - start
print(f"   ✅ Initialized in {init_elapsed:.1f}s")
print(f"      Client enabled: {getattr(trader.client, 'enabled', False)}")
print(f"      Starting GBP:   £{trader.starting_equity_gbp:.2f}")

if not getattr(trader.client, 'enabled', False):
    print("\n❌ Capital client not ready")
    sys.exit(1)

# Intercept orders
trader._open_position = lambda sym, cfg, ticker: (print(f"   🚫 BLOCKED OPEN: {sym} {cfg.get('direction')}") or None)
trader._close_position = lambda pos, reason="dry_run": (print(f"   🚫 BLOCKED CLOSE: {pos.symbol} {reason}") or None)

print("\n🔄 Executing ONE real tick with phase timing...")
sys.stdout.flush()

phases = []

def phase(name, fn):
    t0 = time.time()
    sys.stdout.flush()
    try:
        result = fn()
    except Exception as e:
        result = e
    elapsed = time.time() - t0
    phases.append((name, elapsed))
    print(f"   [{elapsed:6.2f}s] {name}")
    sys.stdout.flush()
    return result

# Run tick() but time each internal phase manually
phase("_ensure_client_ready", lambda: trader._ensure_client_ready())
phase("_ensure_live_refresh", lambda: trader._ensure_live_refresh())
phase("_sync_positions_from_exchange", lambda: trader._sync_positions_from_exchange())
phase("_refresh_prices", lambda: trader._refresh_prices())
phase("_refresh_unified_intel_snapshot", lambda: trader._refresh_unified_intel_snapshot())
phase("_refresh_mind_map_snapshot", lambda: trader._refresh_mind_map_snapshot())
phase("_refresh_thought_bus_snapshot", lambda: trader._refresh_thought_bus_snapshot())

# Now the locked part
print("\n   Acquiring _state_lock...")
sys.stdout.flush()
lock_acquired_at = time.time()
with trader._state_lock:
    lock_wait = time.time() - lock_acquired_at
    print(f"   Lock acquired after {lock_wait:.2f}s")

    now = time.time()
    phase("_deadman_guard", lambda: trader._deadman_guard(now))

    phase("_refresh_mycelium_snapshot", lambda: trader._refresh_mycelium_snapshot(force=True))

    if now - trader._last_monitor >= cfd_mod.CFD_CONFIG["monitor_interval"]:
        phase("_update_position_prices", lambda: trader._update_position_prices())
        phase("_monitor_positions", lambda: trader._monitor_positions())
        trader._last_monitor = now
    else:
        print(f"   Skipping monitor (interval not reached)")

    phase("_update_shadows", lambda: trader._update_shadows())

    should_scan = (now - trader._last_scan >= cfd_mod.CFD_CONFIG["scan_interval_secs"])
    if should_scan:
        trader._last_scan = now
        phase("_quad_gate", lambda: trader._quad_gate())
        phase("_find_best_opportunity", lambda: trader._find_best_opportunity())
        phase("_queue_background_shadows", lambda: trader._queue_background_shadows())
        phase("_fill_live_monitoring_slots", lambda: trader._fill_live_monitoring_slots(now))
        phase("_ranked_opportunities + loop", lambda: list(trader._ranked_opportunities())[:3])
    else:
        print(f"   Skipping scan (interval not reached)")

    phase("_build_lane_snapshot", lambda: trader._build_lane_snapshot())
    phase("_refresh_live_system_activity_snapshot", lambda: trader._refresh_live_system_activity_snapshot())

print("\n" + "-" * 50)
print("  PHASE TIMING SUMMARY")
print("-" * 50)
total = sum(t for _, t in phases)
for name, t in phases:
    pct = (t / total * 100) if total > 0 else 0
    print(f"  {t:6.2f}s ({pct:5.1f}%)  {name}")
print(f"  {'':>6}  {'':>5}   TOTAL: {total:.2f}s")

print(f"\n📊 EXCHANGE POSITIONS: {len(trader.positions)}")
for p in trader.positions:
    print(f"   {p.symbol} {p.direction} @ £{p.entry_price:.2f} → £{p.current_price:.2f}")

prices = getattr(trader, '_prices', {})
print(f"\n📈 PRICES CACHED: {len(prices)}")
for sym, data in list(prices.items())[:5]:
    print(f"   {sym}: bid={data.get('bid')} ask={data.get('ask')} price={data.get('price')}")

if trader._latest_tick_line:
    print(f"\n📋 TICK SUMMARY: {trader._latest_tick_line}")

print("\n" + "=" * 70)
print("  REAL DRY-RUN COMPLETE")
print("=" * 70)
