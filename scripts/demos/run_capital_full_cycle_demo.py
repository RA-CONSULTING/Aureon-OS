#!/usr/bin/env python3
"""
FULL OPEN → CLOSE CYCLE DEMO
══════════════════════════════════════════════════════════════════
Simulates a complete Capital CFD trading cycle using mocked prices,
watching the system OPEN a position, then CLOSE it for revenue.
"""
import sys
import time
import threading

sys.path.insert(0, r"C:\Users\user\aureon-trading")

# Import module first, then suppress real client init
from aureon.exchanges import capital_cfd_trader as cfd_mod
from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader, CFDPosition

# Save original
_ORIG_HAS_CAPITAL = cfd_mod.HAS_CAPITAL
cfd_mod.HAS_CAPITAL = False

trader = CapitalCFDTrader()

# Restore
cfd_mod.HAS_CAPITAL = _ORIG_HAS_CAPITAL


class DemoClient:
    """Mock Capital client that tracks calls and returns controlled responses."""
    def __init__(self):
        self.enabled = True
        self.init_error = ""
        self.order_calls = []
        self.close_calls = []
        self._positions = []
        self._next_deal_id = "DEMO1"
        self._open_result = {"dealReference": "REF1"}
        self._confirm_result = {"dealId": "DEMO1", "level": 100.0}
        self._close_result = {"success": True}
        self._accounts = [{"accountId": "A1", "balance": 1000.0, "available": 1000.0, "currency": "GBP"}]
        self._market_snapshot = {
            "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
            "snapshot": {"marketStatus": "TRADEABLE", "bid": 100.0, "offer": 100.2},
            "dealingRules": {"minDealSize": {"value": 1}},
        }

    def get_positions(self):
        return list(self._positions)

    def get_accounts(self): return list(self._accounts)
    def get_account_balance(self): return {}
    def confirm_order(self, deal_reference: str): return dict(self._confirm_result)
    def _resolve_market(self, symbol: str): return {"epic": "CS.D.SILVER.CFD.IP", "symbol": symbol}
    def _get_market_snapshot(self, epic: str): return dict(self._market_snapshot)
    def get_working_orders(self): return []

    def place_market_order(self, symbol: str, side: str, size: float, **kwargs):
        self.order_calls.append((symbol, side, size, kwargs))
        self._positions.append({
            "position": {
                "dealId": self._next_deal_id,
                "dealReference": "REF1",
                "direction": side.upper(),
                "size": size,
                "level": 100.0,
                "epic": "CS.D.SILVER.CFD.IP",
            },
            "market": {
                "epic": "CS.D.SILVER.CFD.IP",
                "instrumentName": "Silver",
                "expiry": "DFB",
            }
        })
        return dict(self._open_result)

    def close_position(self, deal_id: str):
        self.close_calls.append(deal_id)
        self._positions = [p for p in self._positions if p.get("position", {}).get("dealId") != deal_id]
        return dict(self._close_result)

    def update_position_limits(self, deal_id: str, **kwargs):
        return {"success": True}

    def place_working_order(self, symbol: str, side: str, size: float, level: float, **kwargs):
        return {"dealReference": "WREF1", "submitted": True}

    def get_tickers_for_symbols(self, symbols):
        return {}


def inject_price(trader, symbol, bid, ask):
    trader._prices[symbol.upper()] = {
        "price": (bid + ask) / 2,
        "bid": bid,
        "ask": ask,
        "change_pct": 0.0,
    }
    trader._prices_fetched_at = time.time()


def main():
    print("=" * 70)
    print("  CAPITAL CFD FULL CYCLE DEMO")
    print("  Open → Monitor → Close → Revenue")
    print("=" * 70)

    client = DemoClient()
    trader.client = client
    trader.starting_equity_gbp = 1000.0

    # ── PHASE 1: OPEN POSITION ──
    print("\n📡 PHASE 1: TRIGGERING POSITION OPEN")
    print("-" * 50)
    sys.stdout.flush()

    inject_price(trader, "SILVER", 100.0, 100.2)

    # Direct open via _open_position (bypass tick to avoid background thread)
    ticker = {"price": 100.1, "bid": 100.0, "ask": 100.2}
    cfg = {"class": "commodity", "size": 1, "direction": "BUY", "sl_pct": 2.0, "tp_pct": 5.0}

    original_preflight = trader._capital_preflight
    trader._capital_preflight = lambda sym, size, ticker, cfg=None: {
        "ok": True, "reason": "ok", "market_status": "TRADEABLE",
        "minimum_deal_size": 1.0, "available_balance": 1000.0,
    }

    pos = trader._open_position("SILVER", cfg, ticker)
    trader._capital_preflight = original_preflight

    if pos is None:
        print("   ❌ _open_position() returned None — validation may have failed")
        sys.exit(1)

    print(f"   ✅ POSITION OPENED: {pos.direction} {pos.size} {pos.symbol}")
    print(f"      Deal ID: {pos.deal_id}")
    print(f"      Entry: £{pos.entry_price:.2f}")
    print(f"      Local positions: {len(trader.positions)}")
    sys.stdout.flush()

    # ── PHASE 2: PRICE RISE ──
    print("\n📈 PHASE 2: PRICE RISES TO £103.5 (3.5% profit)")
    print("-" * 50)
    sys.stdout.flush()

    inject_price(trader, "SILVER", 103.4, 103.6)
    pos.current_price = 103.5

    # ── PHASE 3: CLOSE POSITION ──
    print("\n🔍 PHASE 3: CLOSING POSITION FOR PROFIT")
    print("-" * 50)
    sys.stdout.flush()

    record = trader._close_position(pos, reason="DEMO_TAKE_PROFIT")

    if not record:
        print("   ❌ _close_position() returned None")
        sys.exit(1)

    pnl = record.get("pnl_gbp", 0.0) if isinstance(record, dict) else getattr(record, "pnl_gbp", 0.0)
    reason = record.get("reason", "unknown") if isinstance(record, dict) else getattr(record, "close_reason", "unknown")

    print(f"   ✅ POSITION CLOSED")
    print(f"      Reason: {reason}")
    print(f"      P&L: £{pnl:.2f}")
    sys.stdout.flush()

    # ── PHASE 4: REVENUE SUMMARY ──
    print("\n💰 PHASE 4: REVENUE SUMMARY")
    print("-" * 50)
    print(f"      Trades opened this session: {int(trader.stats['trades_opened'])}")
    print(f"      Trades closed this session: {int(trader.stats['trades_closed'])}")
    print(f"      Total P&L: £{trader.stats['total_pnl_gbp']:.2f}")
    print(f"      Best trade: £{trader.stats['best_trade']:.2f}")
    print(f"      Worst trade: £{trader.stats['worst_trade']:.2f}")
    sys.stdout.flush()

    print("\n" + "=" * 70)
    print("  ✅ FULL CYCLE COMPLETE — OPEN → CLOSE → REVENUE")
    print("=" * 70)


if __name__ == "__main__":
    main()
