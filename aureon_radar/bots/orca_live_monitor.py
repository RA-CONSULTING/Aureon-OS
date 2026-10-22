#!/usr/bin/env python3
"""
ORCA LIVE TRADE MONITOR
========================
Monitors active positions across Alpaca, Binance, Kraken, and Capital.com
and evaluates fee-aware exit conditions.

Run modes:
  python orca_live_monitor.py --once                         # single shadow scan
  python orca_live_monitor.py --duration 300                 # monitor N seconds
  python orca_live_monitor.py --live                         # real exit orders
  python orca_live_monitor.py --live --test-order            # minimal live order test
  python orca_live_monitor.py --live --test-order --venue kraken

Safety:
  - Shadow mode is the default; --live is required for real orders.
  - Test orders use the smallest practical size ($1-5 crypto notional,
    1000-unit Capital forex lot).
  - Limit orders are used when the adapter supports them and a price can be
    fetched; otherwise market orders are used with the minimum size.
  - Every real order attempt is recorded in orca_live_journal.jsonl with
    timestamp, venue, symbol, side, qty, price, status, reason/error, and id.
"""

import sys
from pathlib import Path

RADAR_ROOT = Path(__file__).resolve().parent.parent
if str(RADAR_ROOT) not in sys.path:
    sys.path.insert(0, str(RADAR_ROOT))

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import time
import json
import math
import argparse
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple

from exchange_adapters import price_cache

# Load .env from the radar root regardless of cwd (never print values)
_env_path = RADAR_ROOT / '.env'
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# Settings
# Owner decree 2026-09-07: target ~1p/1c NET profit per winning trade.
# Defaults are intentionally tight; every threshold can be overridden via env.
TAKE_PROFIT_PCT = float(os.getenv("ORCA_TAKE_PROFIT_PCT", "0.000015"))   # 0.0015% gross
STOP_LOSS_PCT = float(os.getenv("ORCA_STOP_LOSS_PCT", "0.000030"))       # 0.0030% stop
MAX_HOLD_MINUTES = int(os.getenv("ORCA_MAX_HOLD_MINUTES", "5"))          # quick in/out
ROUND_TRIP_FEE = float(os.getenv("ORCA_ROUND_TRIP_FEE", "0.005"))        # 0.5% total fees

# 1p/1c net-profit floor: the minimum absolute price move that must remain
# after fees for a win to count as a real profit. 0.0001 = 1 pip/cent/pence.
NET_PROFIT_FLOOR_PCT = float(os.getenv("ORCA_NET_PROFIT_FLOOR_PCT", "0.0001"))

# Dynamic sizing: the stop width scales with symbol volatility when fresh
# public data is available. ATR% multiplier -> effective stop_pct.
_DYNAMIC_STOP_ATR_MULT = float(os.getenv("ORCA_DYNAMIC_STOP_ATR_MULT", "1.5"))
_DYNAMIC_TP_ATR_MULT = float(os.getenv("ORCA_DYNAMIC_TP_ATR_MULT", "2.0"))
_DYNAMIC_ATR_MIN_PCT = float(os.getenv("ORCA_DYNAMIC_ATR_MIN_PCT", "0.00002"))

STATE_FILE = RADAR_ROOT / "orca_trade_history.json"
SHADOW_JOURNAL = RADAR_ROOT / "orca_live_monitor_shadow.jsonl"
LIVE_JOURNAL = RADAR_ROOT / "orca_live_journal.jsonl"

# Minimum practical test-order sizes (fail-closed: never larger)
TEST_ORDER_SIZES = {
    "alpaca": {"symbol": "BTC/USD", "side": "buy", "notional": 1.0, "order_type": "market", "tif": "ioc"},
    "binance": {"symbol": "BTCUSDT", "side": "BUY", "notional": 5.0, "order_type": "MARKET"},
    "kraken": {"symbol": "XBT/USD", "side": "buy", "notional": 5.0, "order_type": "limit", "limit_slip": 0.001},
    "capital": {"symbol": "GOLD", "side": "buy", "quantity": 0.01, "order_type": "market"},
}


@dataclass
class TradeResult:
    """Full cycle trade result (shadow or live)."""
    symbol: str
    exchange: str
    qty: float
    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    hold_minutes: float
    gross_pnl_usd: float
    gross_pnl_pct: float
    fees_usd: float
    net_pnl_usd: float
    net_pnl_pct: float
    exit_reason: str
    portfolio_before: float
    portfolio_after: float
    portfolio_growth_pct: float
    shadow: bool = True


def load_history():
    """Load trade history."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"trades": [], "total_net_pnl": 0.0, "wins": 0, "losses": 0}


def save_history(history):
    """Save trade history."""
    STATE_FILE.write_text(json.dumps(history, indent=2))


def journal_live_order(record: Dict[str, Any]) -> None:
    """Append a real order attempt to the live journal."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "venue": record.get("venue"),
        "symbol": record.get("symbol"),
        "side": record.get("side"),
        "qty": record.get("qty"),
        "price": record.get("price"),
        "status": record.get("status"),
        "reason": record.get("reason"),
        "error": record.get("error"),
        "deal_id": record.get("deal_id"),
        "order_id": record.get("order_id"),
        "raw": record.get("raw"),
    }
    LIVE_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(LIVE_JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def journal_shadow_exit(trade: TradeResult):
    """Append a shadow exit event to the JSONL journal."""
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': 'shadow_exit',
        'symbol': trade.symbol,
        'exit_reason': trade.exit_reason,
        'entry_price': trade.entry_price,
        'exit_price': trade.exit_price,
        'qty': trade.qty,
        'net_pnl_usd': trade.net_pnl_usd,
        'net_pnl_pct': trade.net_pnl_pct,
        'shadow': True,
        'note': 'Exit condition evaluated; NOT executed. Use --live for real orders.',
    }
    with open(SHADOW_JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Data-freshness gate
# ---------------------------------------------------------------------------
_VENUE_TO_PRICE_SOURCE = {
    "alpaca": "alpaca",
    "binance": "binance",
    "kraken": "kraken",
    # Capital.com is not covered by the public price_cache; its own API is the
    # freshness authority. We still guard Capital exits against globally
    # simulated/stale data.
}


def _log_freshness_state() -> None:
    """Log the current price-cache freshness report."""
    try:
        report = price_cache.report()
        for line in report.splitlines():
            print(f"[FRESHNESS] {line}")
    except Exception as exc:
        print(f"[FRESHNESS WARN] report failed: {exc}")


def _get_fresh_price(venue: str, symbol: str, fallback: float) -> Tuple[float, bool]:
    """Return (price, fresh_flag). If a fresher public price is available and
    trade_allowed, use it; otherwise return the venue's price unchanged."""
    source = _VENUE_TO_PRICE_SOURCE.get(str(venue).lower())
    if not source:
        return fallback, False
    try:
        q = price_cache.get_price(symbol, source=source)
        if q.get("trade_allowed") and q.get("price"):
            return float(q["price"]), True
    except Exception as exc:
        print(f"[FRESH PRICE WARN] {venue} {symbol}: {exc}")
    return fallback, False


def _dynamic_exit_levels(symbol: str, entry_price: float,
                          venue: Optional[str] = None) -> Tuple[float, float]:
    """Return (take_profit_pct, stop_loss_pct) for a symbol.

    Starts from the env/default base levels. If fresh public data has a
    recent ATR%, widen/narrow the stop around that value. The profit target
    is always set so that, after ROUND_TRIP_FEE, at least NET_PROFIT_FLOOR_PCT
    net remains. Falls back to base levels when no fresh data is available.
    """
    tp_pct = TAKE_PROFIT_PCT
    sl_pct = STOP_LOSS_PCT

    if entry_price <= 0 or not symbol:
        return tp_pct, sl_pct

    source = _VENUE_TO_PRICE_SOURCE.get(str(venue).lower()) if venue else None
    if not source:
        source = "binance"  # best-effort public source for ATR context

    try:
        summary = price_cache.get_summary(symbol, source=source)
        closes = summary.get("closes") or []
        if len(closes) >= 15:
            # ATR% approximation from 15m closes
            moves = [abs(closes[i] - closes[i - 1]) / closes[i - 1]
                     for i in range(1, len(closes)) if closes[i - 1] > 0]
            if len(moves) >= 10:
                atr_pct = sum(moves[-10:]) / 10.0
                if atr_pct and math.isfinite(atr_pct):
                    dynamic_sl = max(_DYNAMIC_ATR_MIN_PCT,
                                     atr_pct * _DYNAMIC_STOP_ATR_MULT)
                    dynamic_tp = max(dynamic_sl + NET_PROFIT_FLOOR_PCT + ROUND_TRIP_FEE,
                                     atr_pct * _DYNAMIC_TP_ATR_MULT)
                    # Never let the dynamic stop be looser than 2x the base SL.
                    sl_pct = min(dynamic_sl, sl_pct * 2.0)
                    tp_pct = min(dynamic_tp, tp_pct * 5.0)
    except Exception:
        pass

    # Fee-aware floor: gross TP must clear fees + 1p/1c net.
    min_tp_after_fees = ROUND_TRIP_FEE + NET_PROFIT_FLOOR_PCT
    tp_pct = max(tp_pct, min_tp_after_fees)
    # Stop must never be wider than a sensible quick-out ceiling.
    sl_pct = min(sl_pct, 0.01)
    return tp_pct, sl_pct


def _freshness_block_reason(symbol: Optional[str] = None,
                            venue: Optional[str] = None) -> Optional[str]:
    """Return a reason string if live trading should be blocked, else None.

    Fail-closed: any simulated data anywhere blocks live orders. Stale or
    non-trade-allowed data for the requested venue/symbol also blocks.
    """
    try:
        state = price_cache.freshness_state()
    except Exception as exc:
        return f"freshness_state_error: {exc}"

    simulated = [k for k, e in state.items() if e.get("source_kind") == "simulated"]
    if simulated:
        return f"simulated data detected: {simulated[0]}"

    source = _VENUE_TO_PRICE_SOURCE.get(str(venue).lower()) if venue else None
    if source and symbol:
        key = f"{source}:{str(symbol).upper()}"
        entry = state.get(key)
        if entry and not entry.get("trade_allowed"):
            return (
                f"data not trade-allowed for {key} "
                f"(fresh={entry.get('fresh')}, age_s={entry.get('age_s')}, "
                f"error={entry.get('error')})"
            )

    # If any REST source is stale (>60s) and no websocket is updating it,
    # block live actions until the feed recovers.
    for key, e in state.items():
        if not e.get("fresh") and e.get("source_kind") != "websocket":
            return f"stale data detected: {key} age_s={e.get('age_s')}"

    return None


# ---------------------------------------------------------------------------
# Venue adapters
# ---------------------------------------------------------------------------
def get_alpaca_adapter():
    from exchange_adapters.alpaca_adapter import AlpacaAdapter
    return AlpacaAdapter()


def get_binance_adapter():
    from exchange_adapters.binance_adapter import BinanceAdapter
    return BinanceAdapter()


def get_kraken_adapter():
    from exchange_adapters.kraken_adapter import KrakenAdapter, get_kraken_adapter
    return get_kraken_adapter()


def get_capital_client():
    from capital_client import CapitalClient
    # Owner decree 2026-09-07: when LIVE=1, force Capital.com LIVE account.
    if os.getenv("LIVE", "0") == "1":
        os.environ["CAPITAL_DEMO"] = "0"
    return CapitalClient()


def get_all_positions() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch open positions from every configured venue."""
    positions: Dict[str, List[Dict[str, Any]]] = {}

    try:
        alpaca = get_alpaca_adapter()
        alpaca_positions = alpaca.get_positions()
        positions["alpaca"] = [
            {
                "symbol": p.get("symbol"),
                "qty": float(p.get("qty", 0)),
                "avg_entry_price": float(p.get("avg_entry_price", 0) or 0),
                "current_price": float(p.get("current_price", 0) or 0),
                "unrealized_pl": float(p.get("unrealized_pl", 0) or 0),
                "unrealized_plpc": float(p.get("unrealized_plpc", 0) or 0),
                "side": p.get("side", "long"),
            }
            for p in alpaca_positions
        ]
    except Exception as exc:
        positions["alpaca"] = [{"error": str(exc)}]

    try:
        binance = get_binance_adapter()
        binance_balance = binance.get_balance()
        # Treat non-zero crypto balances as positions for exit monitoring.
        binance_positions = []
        for asset, amount in binance_balance.items():
            if asset in ("USDT", "BUSD", "USD", "USDC"):
                continue
            if amount > 0:
                symbol = f"{asset}USDT"
                price_quote = binance.get_price(symbol)
                price = price_quote.get("price", 0.0) if price_quote.get("ok") else 0.0
                binance_positions.append({
                    "symbol": symbol,
                    "qty": float(amount),
                    "avg_entry_price": 0.0,
                    "current_price": float(price),
                    "unrealized_pl": 0.0,
                    "unrealized_plpc": 0.0,
                    "side": "long",
                    "note": "balance-derived position",
                })
        positions["binance"] = binance_positions
    except Exception as exc:
        positions["binance"] = [{"error": str(exc)}]

    try:
        kraken = get_kraken_adapter()
        kraken_balance = kraken.get_balance()
        kraken_positions = []
        for asset, amount in kraken_balance.items():
            if asset in ("USD", "USDT", "USDC", "ZUSD"):
                continue
            if amount > 0:
                pair = f"{asset}/USD"
                try:
                    ticker = kraken.get_ticker(pair)
                    price = ticker.get("last", 0.0)
                except Exception:
                    price = 0.0
                kraken_positions.append({
                    "symbol": pair,
                    "qty": float(amount),
                    "avg_entry_price": 0.0,
                    "current_price": float(price),
                    "unrealized_pl": 0.0,
                    "unrealized_plpc": 0.0,
                    "side": "long",
                    "note": "balance-derived position",
                })
        positions["kraken"] = kraken_positions
    except Exception as exc:
        positions["kraken"] = [{"error": str(exc)}]

    try:
        capital = get_capital_client()
        capital_positions = []
        if capital.enabled:
            for pos in capital.get_positions():
                pos_meta = pos.get("position", {})
                market = pos.get("market", {})
                capital_positions.append({
                    "symbol": market.get("epic") or pos_meta.get("epic"),
                    "deal_id": pos_meta.get("dealId"),
                    "deal_reference": pos_meta.get("dealReference"),
                    "qty": float(pos_meta.get("size", 0)),
                    "avg_entry_price": float(pos_meta.get("level", 0) or 0),
                    "current_price": float(market.get("bid", 0) or market.get("offer", 0) or 0),
                    "unrealized_pl": 0.0,
                    "unrealized_plpc": 0.0,
                    "side": "long" if str(pos_meta.get("direction", "")).upper() == "BUY" else "short",
                })
        positions["capital"] = capital_positions
    except Exception as exc:
        positions["capital"] = [{"error": str(exc)}]

    return positions


def submit_exit_order(
    venue: str,
    symbol: str,
    qty: float,
    current_price: float,
    reason: str,
    position: Dict[str, Any],
) -> Dict[str, Any]:
    """Submit a real exit order for the given venue and position.

    Returns a normalized receipt; the caller journals it.
    """
    record = {
        "venue": venue,
        "symbol": symbol,
        "side": "sell",
        "qty": qty,
        "price": current_price,
        "status": "pending",
        "reason": reason,
        "error": None,
        "deal_id": None,
        "order_id": None,
        "raw": None,
    }

    block = _freshness_block_reason(symbol=symbol, venue=venue)
    if block:
        record["status"] = "blocked_freshness"
        record["error"] = block
        print(f"[FRESHNESS BLOCK] Exit order blocked: {block}")
        journal_live_order(record)
        return record

    try:
        if venue == "alpaca":
            alpaca = get_alpaca_adapter()
            # Alpaca crypto uses IOC time-in-force; equities use DAY.
            is_crypto = "/" in symbol or symbol.upper() in (
                "BTC", "ETH", "LTC", "XRP", "SOL", "DOGE", "AVAX", "DOT", "LINK", "UNI",
                "AAVE", "BCH", "XLM", "ATOM", "ALGO", "MATIC", "SHIB", "ADA", "BNB",
                "ETC", "FIL", "NEAR", "APT", "OP", "ARB", "CRV", "MKR", "SNX", "COMP",
                "XTZ", "SUI", "SEI", "INJ", "TIA", "WIF", "BONK", "PEPE", "TRUMP",
            )
            tif = "ioc" if is_crypto else "day"
            result = alpaca.submit_order(symbol, "sell", qty=qty, time_in_force=tif)
            record["status"] = result.get("status", "UNKNOWN")
            record["order_id"] = result.get("order_id")
            record["raw"] = result

        elif venue == "binance":
            binance = get_binance_adapter()
            result = binance.place_order(symbol, "SELL", qty, order_type="MARKET")
            record["status"] = "LIVE" if result.get("mode") == "LIVE" else result.get("mode", "UNKNOWN")
            record["order_id"] = str(result.get("result", {}).get("order_id")) if isinstance(result.get("result"), dict) else None
            record["raw"] = result

        elif venue == "kraken":
            kraken = get_kraken_adapter()
            result = kraken.place_order(symbol, "sell", qty, ordertype="market", reason=reason)
            record["status"] = result.get("status", "UNKNOWN")
            record["order_id"] = (result.get("txids") or [None])[0]
            record["raw"] = result

        elif venue == "capital":
            capital = get_capital_client()
            deal_id = position.get("deal_id")
            if not deal_id:
                record["status"] = "error"
                record["error"] = "missing deal_id for Capital close"
            else:
                result = capital.close_position(deal_id)
                record["status"] = "closed" if result.get("success") else "error"
                record["error"] = result.get("error")
                record["deal_id"] = deal_id
                record["raw"] = result
        else:
            record["status"] = "error"
            record["error"] = f"unknown venue: {venue}"
    except Exception as exc:
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"

    journal_live_order(record)
    return record


# ---------------------------------------------------------------------------
# Test-order probes
# ---------------------------------------------------------------------------
def run_balance_price_check(venue: str) -> Dict[str, Any]:
    """Read-only balance and price check for a single venue."""
    result = {"venue": venue, "balance_ok": False, "price_ok": False, "error": None}
    try:
        if venue == "alpaca":
            adapter = get_alpaca_adapter()
            account = adapter.get_account()
            result["balance"] = {
                "cash": account.get("cash"),
                "equity": account.get("equity"),
                "buying_power": account.get("buying_power"),
                "mode": account.get("mode"),
                "environment": "LIVE" if not adapter.paper else "paper",
            }
            result["balance_ok"] = account.get("mode") == "paper_live" and account.get("equity", 0) > 0
            quote = adapter.get_quote(TEST_ORDER_SIZES[venue]["symbol"])
            result["price"] = quote.get("last")
            result["price_ok"] = quote.get("last", 0) > 0

        elif venue == "binance":
            adapter = get_binance_adapter()
            balance = adapter.get_balance()
            result["balance"] = {"total_usdt": balance.get("USDT", 0.0), "assets": list(balance.keys())[:10]}
            result["balance_ok"] = balance.get("USDT", 0) > 0
            price = adapter.get_price(TEST_ORDER_SIZES[venue]["symbol"])
            result["price"] = price.get("price")
            result["price_ok"] = price.get("ok", False)
            result["endpoint"] = adapter.config.base_url
            result["testnet"] = adapter.config.testnet

        elif venue == "kraken":
            adapter = get_kraken_adapter()
            auth = adapter.authenticate()
            balance = adapter.get_balance()
            result["balance"] = {"authenticated": auth.get("authenticated"), "assets": list(balance.keys())[:10]}
            result["balance_ok"] = auth.get("authenticated", False) and (balance.get("USD", 0) > 0 or len(balance) > 0)
            ticker = adapter.get_ticker(TEST_ORDER_SIZES[venue]["symbol"])
            result["price"] = ticker.get("last")
            result["price_ok"] = ticker.get("last", 0) > 0
            result["live_enabled"] = adapter.live_enabled

        elif venue == "capital":
            client = get_capital_client()
            result["enabled"] = client.enabled
            result["demo_mode"] = client.demo_mode
            if not client.enabled:
                result["error"] = "Capital client disabled (credentials missing)"
                return result
            client.authenticate()
            balance = client.get_account_balance()
            result["balance"] = {"available": balance}
            result["balance_ok"] = balance > 0
            ticker = client.get_ticker(TEST_ORDER_SIZES[venue]["symbol"])
            result["price"] = ticker.get("price")
            result["price_ok"] = ticker.get("price", 0) > 0

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def run_test_order(venue: str, live: bool = False) -> Dict[str, Any]:
    """Submit the smallest practical order on a single venue.

    If live=False the adapters may still execute in dry-run if keys/mode
    dictate; the function still records the attempt honestly.
    """
    spec = TEST_ORDER_SIZES[venue]
    record = {
        "venue": venue,
        "symbol": spec["symbol"],
        "side": spec["side"],
        "qty": spec.get("quantity") or spec.get("notional"),
        "price": None,
        "status": "pending",
        "reason": "live_test_order_probe",
        "error": None,
        "deal_id": None,
        "order_id": None,
        "raw": None,
    }

    if not live:
        record["status"] = "shadow"
        record["error"] = "--live not passed; test order not submitted"
        journal_live_order(record)
        return record

    block = _freshness_block_reason(symbol=spec["symbol"], venue=venue)
    if block:
        record["status"] = "blocked_freshness"
        record["error"] = block
        print(f"[FRESHNESS BLOCK] Test order blocked: {block}")
        journal_live_order(record)
        return record

    try:
        if venue == "alpaca":
            adapter = get_alpaca_adapter()
            quote = adapter.get_quote(spec["symbol"])
            record["price"] = quote.get("last")
            result = adapter.submit_order(
                spec["symbol"], spec["side"], notional=spec["notional"], time_in_force=spec["tif"]
            )
            record["status"] = result.get("status", "UNKNOWN")
            record["order_id"] = result.get("order_id")
            record["raw"] = result

        elif venue == "binance":
            adapter = get_binance_adapter()
            result = adapter.place_order_by_notional(
                spec["symbol"], spec["side"], spec["notional"], order_type=spec["order_type"]
            )
            record["price"] = result.get("reference_price")
            record["status"] = result.get("mode", "UNKNOWN")
            record["order_id"] = str(result.get("result", {}).get("order_id")) if isinstance(result.get("result"), dict) else None
            record["raw"] = result

        elif venue == "kraken":
            adapter = get_kraken_adapter()
            ticker = adapter.get_ticker(spec["symbol"])
            price = ticker.get("ask", 0.0)
            slip = spec.get("limit_slip", 0.0)
            limit_price = round(price * (1.0 + slip), 1) if price > 0 and slip else price
            record["price"] = limit_price
            if price > 0:
                volume = round(spec["notional"] / price, 6)
                result = adapter.place_order(
                    spec["symbol"], spec["side"], volume,
                    ordertype=spec["order_type"],
                    price=limit_price,
                    reason="live_test_order_probe",
                )
                record["qty"] = volume
                record["status"] = result.get("status", "UNKNOWN")
                record["order_id"] = (result.get("txids") or [None])[0]
                record["raw"] = result
            else:
                record["status"] = "error"
                record["error"] = "could not fetch Kraken price"

        elif venue == "capital":
            client = get_capital_client()
            if not client.enabled:
                record["status"] = "error"
                record["error"] = "Capital client disabled (credentials missing)"
            else:
                ticker = client.get_ticker(spec["symbol"])
                price = ticker.get("price") or 0.0
                record["price"] = price
                # Owner decree: mandatory broker-side stop loss on every live order.
                # Use a 2% stop level for quick-in/out probes; this clears
                # Capital.com's minimum-distance gate on GOLD while
                # keeping the probe tiny and short-lived.
                side = str(spec["side"]).upper()
                stop_pct = 0.02
                if side == "BUY":
                    stop_level = round(price * (1.0 - stop_pct), 2) if price else None
                else:
                    stop_level = round(price * (1.0 + stop_pct), 2) if price else None

                # Margin-based size cap: never risk more than 50% of available
                # balance on a test-order probe. For EURUSD at ~1.16 that keeps
                # the 1000-unit lot well under risk budget on a £75 balance.
                quantity = spec["quantity"]
                try:
                    available = client.get_account_balance()
                    if available and available > 0:
                        max_notional = available * 0.50
                        if price > 0:
                            quantity = min(quantity, max(1.0, max_notional / price))
                        record["margin_note"] = f"available={available:.2f} capped_qty={quantity:.2f}"
                except Exception as exc:
                    record["margin_note"] = f"balance_fetch_failed: {exc}"

                result = client.place_market_order(
                    spec["symbol"], spec["side"], quantity,
                    stop_level=stop_level,
                )
                record["status"] = "submitted" if result.get("submitted") else "error"
                record["deal_id"] = result.get("dealId") or result.get("dealReference")
                record["order_id"] = result.get("dealReference")
                record["error"] = result.get("reason") if not result.get("submitted") else None
                record["raw"] = result

    except Exception as exc:
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"

    journal_live_order(record)
    return record


def run_all_test_orders(live: bool = False, venues: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Run read-only checks then minimal live test orders for each venue.

    Guard: this function is intentionally a no-op when imported as a module
    (e.g. by unified_hub's bot loader); it must only run from the CLI entry
    point to avoid accidental order probes inside the hub process.
    """
    if __name__ != "__main__":
        return []

    venues = venues or ["alpaca", "binance", "kraken", "capital"]
    results = []
    print("\n" + "=" * 70)
    print("ORCA LIVE VENUE PROBE")
    print("=" * 70)
    print(f"Mode: {'LIVE orders' if live else 'SHADOW / dry-run (pass --live for real orders)'}")

    for venue in venues:
        print(f"\n--- {venue.upper()} ---")
        check = run_balance_price_check(venue)
        print(f"Balance/price check: {'OK' if check['balance_ok'] and check['price_ok'] else 'ISSUE'}")
        if check.get("balance"):
            print(f"  Balance: {check['balance']}")
        if check.get("price"):
            print(f"  Price: {check['price']}")
        if check.get("error"):
            print(f"  Check error: {check['error']}")

        if not check["balance_ok"] or not check["price_ok"]:
            print(f"  Skipping test order: venue not ready.")
            results.append({"venue": venue, "check": check, "order": {"status": "skipped", "error": "balance or price check failed"}})
            continue

        order = run_test_order(venue, live=live)
        results.append({"venue": venue, "check": check, "order": order})
        print(f"Test order status: {order.get('status')}")
        if order.get("order_id"):
            print(f"  Order/Deal ID: {order['order_id']}")
        if order.get("error"):
            print(f"  Order error: {order['error']}")

    print("\n" + "=" * 70)
    print(f"Live journal: {LIVE_JOURNAL}")
    print("=" * 70)
    return results


# ---------------------------------------------------------------------------
# Monitoring loop
# ---------------------------------------------------------------------------
def monitor_and_trade(duration_seconds=None, once=False, live=False):
    """Main monitoring loop.

    Guard: this function is intentionally a no-op when imported as a module
    (e.g. by unified_hub's bot loader); it must only run from the CLI entry
    point to avoid spawning a position-monitoring loop inside the hub process.
    """
    if __name__ != "__main__":
        return

    print("\n" + "=" * 70)
    print(" ORCA LIVE TRADE MONITOR ")
    print("=" * 70)
    print(f"*  Base Take Profit: {TAKE_PROFIT_PCT*100:.4f}% gross")
    print(f"*  Base Stop Loss: {STOP_LOSS_PCT*100:.4f}%")
    print(f"*  Max Hold: {MAX_HOLD_MINUTES} minutes")
    print(f"*  Fees: {ROUND_TRIP_FEE*100:.1f}% round-trip")
    print(f"*  Net-profit floor: {NET_PROFIT_FLOOR_PCT*100:.4f}% (~1p/1c)")
    print(f"*  Dynamic exits enabled (fresh public ATR% when available)")
    if live:
        print("[LIVE] LIVE MODE — real exit orders will be submitted")
    else:
        print("[LOCKED] SHADOW MODE — exits are journaled as shadow events only")
        print("   Add --live to submit real exit orders")
    print(f"[JOURNAL] Shadow journal: {SHADOW_JOURNAL}")
    print(f"[JOURNAL] Live journal:   {LIVE_JOURNAL}")
    print("=" * 70)

    _log_freshness_state()

    history = load_history()
    entry_times: Dict[str, datetime] = {}
    initial_equity: Optional[float] = None

    iteration = 0
    started = time.time()
    while True:
        if duration_seconds is not None and time.time() - started >= duration_seconds:
            print("\n[TIME]  Monitor duration reached — stopping.")
            break
        iteration += 1

        try:
            all_positions = get_all_positions()

            if initial_equity is None:
                try:
                    alpaca = get_alpaca_adapter()
                    acct = alpaca.get_account()
                    initial_equity = float(acct.get("equity", 0.0) or 0.0)
                    # Drive price-cache urgency mode from available equity.
                    price_cache.set_cash_state(initial_equity)
                except Exception:
                    initial_equity = 0.0

            total_positions = sum(len(p) for p in all_positions.values() if isinstance(p, list))
            if total_positions == 0:
                print(f"\r[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] ... No positions on any venue — waiting...", end="", flush=True)
                time.sleep(10)
                if once:
                    print()
                    break
                continue

            print()  # clear the waiting line
            for venue, positions in all_positions.items():
                if not isinstance(positions, list):
                    continue
                for pos in positions:
                    if "error" in pos:
                        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {venue}: position fetch error — {pos['error']}")
                        continue

                    symbol = pos.get("symbol", "")
                    qty = float(pos.get("qty", 0))
                    entry_price = float(pos.get("avg_entry_price", 0))
                    venue_price = float(pos.get("current_price", 0))
                    current_price, fresh = _get_fresh_price(venue, symbol, venue_price)
                    if fresh:
                        print(f"[FRESH PRICE] {venue} {symbol}: using price_cache price ${current_price:.4f} (venue had ${venue_price:.4f})")
                    unrealized_pl = float(pos.get("unrealized_pl", 0))
                    unrealized_plpc = float(pos.get("unrealized_plpc", 0))

                    position_key = f"{venue}:{symbol}"
                    if position_key not in entry_times:
                        entry_times[position_key] = datetime.now(timezone.utc)

                    hold_minutes = (datetime.now(timezone.utc) - entry_times[position_key]).total_seconds() / 60

                    # If we don't have a P&L percentage from the venue, estimate it
                    if unrealized_plpc == 0 and entry_price > 0 and current_price > 0:
                        unrealized_plpc = (current_price - entry_price) / entry_price

                    position_value = qty * (entry_price or current_price)
                    fee_cost = position_value * ROUND_TRIP_FEE
                    net_pnl = unrealized_pl - fee_cost
                    net_pnl_pct = unrealized_plpc - ROUND_TRIP_FEE

                    # Per-symbol dynamic exit levels (fresh public data + fee floor).
                    tp_pct, sl_pct = _dynamic_exit_levels(symbol, entry_price or current_price, venue)

                    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {venue} {symbol}: "
                          f"${current_price:.4f} | GROSS: ${unrealized_pl:+.4f} ({unrealized_plpc*100:+.2f}%) | "
                          f"NET: ${net_pnl:+.4f} ({net_pnl_pct*100:+.2f}%) | Hold: {hold_minutes:.1f}m | "
                          f"TP={tp_pct*100:.4f}% SL={sl_pct*100:.4f}%")

                    exit_reason = None
                    if unrealized_plpc >= tp_pct:
                        exit_reason = f"TAKE PROFIT ({unrealized_plpc*100:.2f}% gross >= {tp_pct*100:.4f}%)"
                    elif unrealized_plpc <= -sl_pct:
                        exit_reason = f"STOP LOSS ({unrealized_plpc*100:.2f}% <= -{sl_pct*100:.4f}%)"
                    elif hold_minutes >= MAX_HOLD_MINUTES:
                        exit_reason = f"MAX HOLD ({hold_minutes:.0f} min)"

                    # Fee-aware profit floor: even if gross TP is hit, require
                    # net P&L > 1p/1c-equivalent after fees before calling it a
                    # winning exit. If not, treat as a time-based/floor exit.
                    if exit_reason and exit_reason.startswith("TAKE PROFIT") and net_pnl_pct < NET_PROFIT_FLOOR_PCT:
                        exit_reason = (
                            f"PROFIT FLOOR EXIT ({unrealized_plpc*100:.4f}% gross, "
                            f"net {net_pnl_pct*100:.4f}% < floor {NET_PROFIT_FLOOR_PCT*100:.4f}%)"
                        )

                    if exit_reason:
                        print(f"\n{'='*70}")
                        print(f"[EXIT] EXIT CONDITION MET: {venue} {symbol} — {exit_reason}")
                        print(f"{'='*70}")

                        if live:
                            receipt = submit_exit_order(venue, symbol, qty, current_price, exit_reason, pos)
                            print(f"Live exit submitted: status={receipt['status']}")
                            if receipt.get("order_id"):
                                print(f"  Order ID: {receipt['order_id']}")
                            if receipt.get("deal_id"):
                                print(f"  Deal ID: {receipt['deal_id']}")
                            if receipt.get("error"):
                                print(f"  Error: {receipt['error']}")
                        else:
                            print("Shadow mode — order NOT submitted (pass --live to execute)")

                        # Record shadow/hypothetical trade for P&L tracking
                        final_equity = initial_equity
                        try:
                            alpaca = get_alpaca_adapter()
                            acct = alpaca.get_account()
                            final_equity = float(acct.get("equity", initial_equity) or initial_equity)
                        except Exception:
                            pass

                        gross_pnl = (current_price - entry_price) * qty if entry_price else unrealized_pl
                        actual_fee_cost = abs(position_value * ROUND_TRIP_FEE)
                        actual_net_pnl = gross_pnl - actual_fee_cost
                        portfolio_growth = ((final_equity - initial_equity) / initial_equity * 100) if initial_equity else 0.0

                        trade = TradeResult(
                            symbol=symbol,
                            exchange=venue,
                            qty=qty,
                            entry_price=entry_price or current_price,
                            exit_price=current_price,
                            entry_time=entry_times[position_key].isoformat(),
                            exit_time=datetime.now(timezone.utc).isoformat(),
                            hold_minutes=hold_minutes,
                            gross_pnl_usd=gross_pnl,
                            gross_pnl_pct=unrealized_plpc,
                            fees_usd=actual_fee_cost,
                            net_pnl_usd=actual_net_pnl,
                            net_pnl_pct=net_pnl_pct,
                            exit_reason=exit_reason,
                            portfolio_before=initial_equity,
                            portfolio_after=final_equity,
                            portfolio_growth_pct=portfolio_growth,
                            shadow=not live,
                        )

                        history["trades"].append(asdict(trade))
                        history["total_net_pnl"] += actual_net_pnl
                        if actual_net_pnl > 0:
                            history["wins"] += 1
                        else:
                            history["losses"] += 1
                        save_history(history)
                        journal_shadow_exit(trade)

                        # Reset tracker for this position key
                        entry_times[position_key] = datetime.now(timezone.utc)
                        initial_equity = final_equity

            if once:
                print()
                break

            time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n[STOP] Monitor stopped by user")
            break
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=" Orca Live Trade Monitor")
    parser.add_argument('--once', action='store_true', help='Single scan then exit')
    parser.add_argument('--duration', type=int, default=None, help='Monitor for N seconds then exit')
    parser.add_argument('--live', action='store_true', help='Submit real exit orders (default is shadow)')
    parser.add_argument('--test-order', action='store_true', help='Place minimal test orders and exit')
    parser.add_argument('--venue', type=str, default=None, help='Limit test-order to one venue (alpaca/binance/kraken/capital)')
    args = parser.parse_args()

    # Owner decree 2026-09-07: when the suite supervisor passes LIVE=1,
    # the monitor treats that as --live unless the operator explicitly passed
    # --no-live (not implemented; --live remains the explicit flag).
    live = args.live or os.getenv("LIVE", "0") == "1"
    if live:
        print("[LIVE] LIVE environment flag active — real orders enabled")

    if args.test_order:
        venues = [args.venue] if args.venue else None
        run_all_test_orders(live=live, venues=venues)
    else:
        monitor_and_trade(duration_seconds=args.duration, once=args.once, live=live)
