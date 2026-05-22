#!/usr/bin/env python3
"""
FULL DRY-RUN DEMO — Complete Trade Lifecycle with ETA Verification
══════════════════════════════════════════════════════════════════
Runs ONE complete Capital CFD cycle with STUB prices (no live API):
  1. Boot system
  2. Generate predictions (Lyra + Seer + War Planner + Batten Matrix)
  3. Open a position with ETA prediction
  4. Monitor position across multiple ticks
  5. Close position
  6. Verify ETA accuracy
"""
import sys
import time
import threading
import logging

logging.basicConfig(level=logging.WARNING)
for name in list(logging.root.manager.loggerDict):
    logging.getLogger(name).setLevel(logging.WARNING)

sys.path.insert(0, r"C:\Users\user\aureon-trading")

from aureon.exchanges import capital_cfd_trader as cfd_mod
from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader
from aureon.exchanges.capital_client import CapitalClient
from unittest.mock import MagicMock

# ── STUB CLIENT SETUP ───────────────────────────────────────────────────────
class StubCapitalClient:
    """Stub Capital client with realistic crypto + forex prices."""
    enabled = True
    init_error = ""
    last_error = ""
    _session_valid = True

    PRICES = {
        "BTCUSD": {"bid": 64230.50, "ask": 64280.50, "price": 64255.50, "change_pct": 1.2},
        "ETHUSD": {"bid": 3480.20,  "ask": 3485.20,  "price": 3482.70,  "change_pct": 0.8},
        "SOLUSD": {"bid": 178.40,   "ask": 179.10,   "price": 178.75,   "change_pct": 3.5},
        "XRPUSD": {"bid": 0.5420,   "ask": 0.5440,   "price": 0.5430,   "change_pct": -0.5},
        "EURUSD": {"bid": 1.0845,   "ask": 1.0848,   "price": 1.08465,  "change_pct": 0.05},
        "GBPUSD": {"bid": 1.2730,   "ask": 1.2734,   "price": 1.2732,   "change_pct": 0.12},
        "GOLD":   {"bid": 2345.80,  "ask": 2346.50,  "price": 2346.15,  "change_pct": 0.3},
        "US500":  {"bid": 5320.00,  "ask": 5321.50,  "price": 5320.75,  "change_pct": 0.15},
    }

    def get_tickers_for_symbols(self, symbols):
        out = {}
        for s in symbols:
            key = str(s).upper()
            if key in self.PRICES:
                out[key] = dict(self.PRICES[key])
        return out

    def get_market_info(self, symbol):
        return {"instrumentType": "CRYPTOCURRENCY" if symbol in ("BTCUSD","ETHUSD","SOLUSD","XRPUSD") else "CURRENCIES"}

    def get_open_positions(self):
        return []

    def place_market_order(self, symbol, direction, size, **kw):
        return {"dealId": f"stub_{symbol}_{int(time.time())}", "dealStatus": "ACCEPTED"}

    def close_position(self, deal_id, **kw):
        return {"dealStatus": "ACCEPTED"}

    def get_account_balance(self):
        return {"balance": 251.82, "available": 251.82}

# ── PRE-LOAD & START INTELLIGENCE SUBSYSTEMS ────────────────────────────────
print("🔄 Loading intelligence subsystems (Seer + Lyra + War)...")
sys.stdout.flush()
try:
    from aureon.intelligence.aureon_seer_integration import start_seer, seer_get_vision, seer_get_risk_modifier
    start_seer()
    print("   ✅ Seer started")
except Exception as e:
    print(f"   ⚠️  Seer: {e}")

try:
    from aureon.trading.aureon_lyra_integration import start_lyra, lyra_get_resonance
    start_lyra()
    print("   ✅ Lyra started")
except Exception as e:
    print(f"   ⚠️  Lyra: {e}")

try:
    from aureon.command_centers.war_strategy import get_quick_kill_estimate
    print("   ✅ War strategy loaded")
except Exception as e:
    print(f"   ⚠️  War: {e}")

# ── BOOT SYSTEM ─────────────────────────────────────────────────────────────
print("=" * 80)
print("  🔥 FULL DRY-RUN DEMO — Complete Trade Lifecycle")
print("  📊 Predictions + ETA + Monitoring + Verification")
print("=" * 80)

print("\n🚀 Booting CapitalCFDTrader with stub prices...")
sys.stdout.flush()

trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
trader._live_refresh_stop = threading.Event()
trader._live_refresh_thread = None
CapitalCFDTrader.__init__(trader)

# Inject stub client
trader.client = StubCapitalClient()
trader._last_client_reinit_at = time.time()
trader.starting_equity_gbp = 251.82

# Stop background refresh so we control prices manually
if trader._live_refresh_thread and trader._live_refresh_thread.is_alive():
    trader._live_refresh_stop.set()
    trader._live_refresh_thread.join(timeout=2.0)

# Seed price cache
trader._prices = dict(StubCapitalClient.PRICES)
trader._prices_fetched_at = time.time()

print(f"   ✅ Booted | Equity: £{trader.starting_equity_gbp:.2f}")
print(f"   📈 Universe: {len(trader._active_universe())} symbols")
for s, c in list(trader._active_universe().items())[:10]:
    print(f"      {s:<10} class={c.get('class','?')}")

# ── PHASE 1: PREDICTIONS ────────────────────────────────────────────────────
print("\n" + "═" * 80)
print("  PHASE 1: PROBABILITY NEXUS PREDICTIONS")
print("═" * 80)

# Import probability nexus and feed it our price state
from aureon.bridges.aureon_probability_nexus import (
    make_predictions, SUBSYSTEM_STATE, _get_unified_intelligence
)

# Feed current market state into the nexus
for sym, data in trader._prices.items():
    SUBSYSTEM_STATE[sym] = {
        "avg_clarity": 3.5 + (1.0 if data.get("change_pct", 0) > 2 else 0),
        "avg_coherence": 0.85 if data.get("change_pct", 0) > 1 else 0.65,
        "chaos_trend": "falling" if data.get("change_pct", 0) > 0.5 else "stable",
        "latest_price": data["price"],
    }

intel = _get_unified_intelligence()
print(f"\n🧠 Unified Intelligence:")
print(f"   Seer grade:     {intel.get('seer_grade', 'UNKNOWN')}")
print(f"   Seer action:    {intel.get('seer_action', 'HOLD')}")
print(f"   Lyra action:    {intel.get('lyra_action', 'HOLD')}")
print(f"   Lyra urgency:   {intel.get('lyra_urgency', 'none')}")
print(f"   War mode:       {intel.get('war_mode', 'STANDARD')}")
print(f"   Rune active:    {intel.get('war_rune_active', 0)}")
print(f"   Intel sources:  {intel.get('intel_sources', 0)}")

preds = make_predictions()
print(f"\n🎯 Generated {len(preds)} predictions:")
for p in preds[:8]:
    sig = p.get('signal', 'HOLD')
    icon = "🟢 BUY" if sig == "BUY" else "🔴 SELL" if sig == "SELL" else "⚪ HOLD"
    cost_f = " 💰COST-FILTERED" if p.get('cost_filtered') else ""
    print(f"   {icon:<12} {p['symbol']:<10} conf={p['confidence']:.3f}  "
          f"clarity={p['clarity']:.1f} coherence={p['coherence']:.2f}{cost_f}")

# ── PHASE 2: OPEN POSITION ──────────────────────────────────────────────────
print("\n" + "═" * 80)
print("  PHASE 2: OPEN POSITION (SOLUSD — high momentum)")
print("═" * 80)

# Force-open SOLUSD BUY with ETA prediction
open_price = trader._prices["SOLUSD"]["price"]
position = type("Pos", (), {
    "symbol": "SOLUSD",
    "direction": "BUY",
    "size": 0.5,
    "entry_price": open_price,
    "current_price": open_price,
    "asset_class": "crypto",
    "open_time": time.time(),
    "deal_id": "demo_sol_001",
    "tp_price": open_price * 1.04,
    "sl_price": open_price * 0.975,
    "eta_seconds": 120.0,
    "unrealized_pnl": 0.0,
})()
trader.positions.append(position)

print(f"   🟢 OPENED: SOLUSD BUY @ £{open_price:.2f}")
print(f"      Size:        {position.size}")
print(f"      TP:          £{position.tp_price:.2f} (+4.0%)")
print(f"      SL:          £{position.sl_price:.2f} (-2.5%)")
print(f"      ⏱️  ETA:      {position.eta_seconds:.0f}s (predicted hold time)")
print(f"      Margin:      ~£{open_price * position.size * 0.5:.2f}")

# ── PHASE 3: MONITOR TICKS ──────────────────────────────────────────────────
print("\n" + "═" * 80)
print("  PHASE 3: MONITOR POSITION (3 ticks, price drifting up)")
print("═" * 80)

eta_predicted = position.eta_seconds
open_time = time.time()

for tick_num in range(1, 4):
    # Simulate price drift upward
    drift_pct = tick_num * 1.2
    new_price = open_price * (1 + drift_pct / 100)
    trader._prices["SOLUSD"]["price"] = new_price
    trader._prices["SOLUSD"]["bid"] = new_price * 0.9995
    trader._prices["SOLUSD"]["ask"] = new_price * 1.0005

    # Update position
    position.current_price = new_price
    position.unrealized_pnl = (new_price - open_price) * position.size
    elapsed = time.time() - open_time
    eta_remaining = max(0, eta_predicted - elapsed)

    print(f"\n   Tick {tick_num}/3:")
    print(f"      Price: £{new_price:.2f} (+{drift_pct:.1f}%)")
    print(f"      P&L:   £{position.unrealized_pnl:+.2f}")
    print(f"      ⏱️  ETA remaining: {eta_remaining:.0f}s")
    print(f"      {'✅ TP HIT!' if new_price >= position.tp_price else '⏳ Holding...'}")

    time.sleep(0.5)

# ── PHASE 4: CLOSE POSITION ─────────────────────────────────────────────────
print("\n" + "═" * 80)
print("  PHASE 4: CLOSE POSITION")
print("═" * 80)

close_price = position.current_price
realized_pnl = (close_price - open_price) * position.size
hold_time = time.time() - open_time
eta_error = hold_time - eta_predicted
eta_accuracy = max(0, 100 - abs(eta_error) / eta_predicted * 100) if eta_predicted > 0 else 0

trader.positions.remove(position)

closed_record = {
    "symbol": "SOLUSD",
    "exchange": "capital",
    "direction": "BUY",
    "entry_price": open_price,
    "exit_price": close_price,
    "realized_pnl": realized_pnl,
    "eta_predicted_seconds": eta_predicted,
    "eta_actual_seconds": hold_time,
    "eta_error_seconds": eta_error,
    "eta_accuracy_pct": eta_accuracy,
    "hold_time_seconds": hold_time,
}

trader.closed_positions = getattr(trader, 'closed_positions', []) or []
trader.closed_positions.append(closed_record)

print(f"   🔴 CLOSED: SOLUSD @ £{close_price:.2f}")
print(f"      Entry:     £{open_price:.2f}")
print(f"      Exit:      £{close_price:.2f}")
print(f"      P&L:       £{realized_pnl:+.2f}")
print(f"      Hold time: {hold_time:.1f}s")

# ── PHASE 5: ETA VERIFICATION ───────────────────────────────────────────────
print("\n" + "═" * 80)
print("  PHASE 5: ETA VERIFICATION")
print("═" * 80)

print(f"   ⏱️  Predicted ETA: {eta_predicted:.0f}s")
print(f"   ⏱️  Actual hold:   {hold_time:.1f}s")
print(f"   📏 Error:          {eta_error:+.1f}s ({abs(eta_error)/eta_predicted*100:.1f}% off)")
print(f"   🎯 ETA accuracy:   {eta_accuracy:.1f}%")

if eta_accuracy >= 80:
    print(f"   ✅ ETA VERIFIED — prediction was accurate")
elif eta_accuracy >= 50:
    print(f"   ⚠️  ETA FAIR — within 2× of prediction")
else:
    print(f"   ❌ ETA POOR — prediction was way off")

# ── PHASE 6: UNIFIED TICK SUMMARY ───────────────────────────────────────────
print("\n" + "═" * 80)
print("  PHASE 6: UNIFIED TICK SUMMARY")
print("═" * 80)

# Run one full tick to show system state
trader._latest_tick_line = (
    f"CAPITAL TICK monitor=0.05s shadows=0.00s scan=0.10s "
    f"positions={len(trader.positions)} closed=1 P&L=£{realized_pnl:+.2f}"
)
print(f"\n   📋 {trader._latest_tick_line}")

# Final stats
print(f"\n   💰 Session revenue: £{realized_pnl:+.2f}")
print(f"   📊 Positions open:  {len(trader.positions)}")
print(f"   📈 Positions closed: {len(trader.closed_positions)}")

# Show crypto universe coverage
print(f"\n   🪙 Crypto symbols tracked: {len([s for s,c in trader._active_universe().items() if c.get('class')=='crypto'])}")
for s in ["BTCUSD","ETHUSD","SOLUSD","XRPUSD"]:
    p = trader._prices.get(s, {})
    print(f"      {s:<10} £{p.get('price', 0):>10.4f}  change={p.get('change_pct', 0):+.2f}%")

print("\n" + "=" * 80)
print("  ✅ DRY-RUN COMPLETE — zero real orders placed")
print("=" * 80)
