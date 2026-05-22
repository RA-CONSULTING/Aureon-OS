#!/usr/bin/env python3
"""
FULL SYSTEM SMOKE TEST — DRY RUN WITH REAL DATA
══════════════════════════════════════════════════════════════════
Runs ONE complete Aureon trading ecosystem tick in dry-run mode with
live exchange data. Shows:
  • What the system WOULD trade (no real orders)
  • Real-time monitoring of all exchanges
  • ETA predictions and tracking
  • Revenue tracking
"""
import sys
import time
import threading
import logging

# Suppress noise
logging.basicConfig(level=logging.WARNING)
for name in list(logging.root.manager.loggerDict):
    logging.getLogger(name).setLevel(logging.WARNING)

sys.path.insert(0, r"C:\Users\user\aureon-trading")

from aureon.exchanges.unified_market_trader import UnifiedMarketTrader

print("=" * 80)
print("  🔥 AUREON FULL SYSTEM SMOKE TEST — DRY RUN")
print("  ✅ Real exchange data (Kraken, Binance, Alpaca)")
print("  ⚠️  Capital.com disabled (API unreachable)")
print("  ❌ ZERO real orders placed (dry_run=True)")
print("  📊 ETA predictions + revenue tracking enabled")
print("=" * 80)

# ── INITIALISE ──────────────────────────────────────────────────────────────
print("\n🚀 Booting UnifiedMarketTrader (dry_run=True)...")
sys.stdout.flush()
start = time.time()

try:
    trader = UnifiedMarketTrader(dry_run=True)
except Exception as e:
    print(f"\n❌ Failed to initialise: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

init_elapsed = time.time() - start
print(f"   ✅ Booted in {init_elapsed:.1f}s")

# DISABLE Capital — API is down and would hang every tick
if trader.capital:
    trader.capital.enabled = False
    trader.capital_ready = False
    trader.capital_error = "API unreachable — disabled for smoke test"
    # Clear any inflight capital tick from initialization
    trader._capital_tick_inflight = {"running": False}
    trader.capital = None
    print(f"   ⚠️  Capital.com manually disabled (API down)")

# Show exchange health
print("\n📡 EXCHANGE HEALTH:")
exchanges = {
    "Kraken":   trader.kraken,
    "Binance":  trader.binance,
    "Alpaca":   trader.alpaca,
    "Capital":  trader.capital,
}
for name, ex in exchanges.items():
    if ex is None:
        print(f"   ⚪ {name:8}: not configured / disabled")
    else:
        enabled = getattr(ex, 'enabled', False)
        err = getattr(ex, 'init_error', '') or getattr(ex, 'last_error', '')
        status = "🟢 ONLINE" if enabled else "🔴 OFFLINE"
        print(f"   {status} {name:8} {err}")

# ── RUN ONE TICK ────────────────────────────────────────────────────────────
print("\n" + "═" * 80)
print("  EXECUTING ONE FULL TICK CYCLE")
print("═" * 80)

sys.stdout.flush()
tick_start = time.time()

try:
    result = trader.tick()
except Exception as e:
    print(f"\n❌ Tick failed: {e}")
    import traceback
    traceback.print_exc()
    result = []

tick_elapsed = time.time() - tick_start
print(f"\n⏱️  Tick completed in {tick_elapsed:.2f}s")

# ── POSITIONS ───────────────────────────────────────────────────────────────
positions = getattr(trader, 'positions', []) or []
print(f"\n📊 Open positions: {len(positions)}")
for p in positions:
    eta = getattr(p, 'eta_seconds', None)
    eta_str = f" ETA={eta:.1f}s" if eta else ""
    pnl = getattr(p, 'unrealized_pnl', 0.0) or 0.0
    ex_name = getattr(p, 'exchange', '?')
    sym = getattr(p, 'symbol', '?')
    direction = getattr(p, 'direction', '?')
    entry = getattr(p, 'entry_price', 0.0) or 0.0
    current = getattr(p, 'current_price', 0.0) or 0.0
    size = getattr(p, 'size', 0.0) or 0.0
    print(f"   {ex_name:8} {sym:12} {direction:4} "
          f"size={size:.4f} @ {entry:.4f} → {current:.4f} "
          f"P&L={pnl:+.2f}{eta_str}")

# ── ORDER INTENTS ───────────────────────────────────────────────────────────
intents = getattr(trader, '_latest_order_intents', {}) or {}
print(f"\n🎯 Order intents generated: {len(intents)}")
for key, intent in list(intents.items())[:10]:
    sym = intent.get('symbol', '?')
    direction = intent.get('direction', '?')
    size = intent.get('size', 0)
    confidence = intent.get('confidence', 0)
    exchange = intent.get('exchange', '?')
    eta = intent.get('eta_seconds')
    eta_str = f" ETA={eta:.1f}s" if eta else ""
    print(f"   {exchange:8} {sym:12} {direction:4} size={size:.4f} conf={confidence:.2f}{eta_str}")

# ── REVENUE ─────────────────────────────────────────────────────────────────
revenue = getattr(trader, 'total_revenue', 0.0) or 0.0
print(f"\n💰 Total revenue: £{revenue:.2f}")

# ── ETA VERIFIER ────────────────────────────────────────────────────────────
eta_verifier = getattr(trader, 'eta_verifier', None)
if eta_verifier:
    stats = getattr(eta_verifier, 'get_accuracy_stats', lambda: {})()
    if stats:
        print(f"\n🎯 ETA VERIFICATION:")
        print(f"   Accuracy:        {stats.get('accuracy_pct', 0):.1f}%")
        print(f"   Verified:        {stats.get('verified_count', 0)}")
        print(f"   Avg error:       {stats.get('avg_error_seconds', 0):.2f}s")

# ── CLOSED TRADES ───────────────────────────────────────────────────────────
closed = getattr(trader, 'closed_positions', []) or []
print(f"\n📈 Closed trades this session: {len(closed)}")
for c in closed[-5:]:
    pnl = c.get('realized_pnl', 0.0) or 0.0
    eta_actual = c.get('eta_actual_seconds')
    eta_predicted = c.get('eta_predicted_seconds')
    eta_diff = ""
    if eta_actual and eta_predicted:
        diff = eta_actual - eta_predicted
        eta_diff = f" (ETA diff: {diff:+.1f}s)"
    print(f"   {c.get('exchange','?'):8} {c.get('symbol','?'):12} P&L={pnl:+.2f}{eta_diff}")

# ── TICK STATE ──────────────────────────────────────────────────────────────
print(f"\n📋 Latest tick error: {getattr(trader, '_last_tick_error', 'none') or 'none'}")
print(f"📋 Last execution:    {getattr(trader, '_last_execution_at', 0) and time.strftime('%H:%M:%S', time.localtime(trader._last_execution_at)) or 'none'}")

print("\n" + "=" * 80)
print("  ✅ SMOKE TEST COMPLETE — zero orders placed")
print("=" * 80)
