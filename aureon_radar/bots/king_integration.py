#!/usr/bin/env python3
"""
THE KING'S INTEGRATION - Wiring into the Aureon Ecosystem
=====================================================
"The King sees all. The King records all."

Bridges The King (Autonomous Accounting AI) into the full Aureon
trading ecosystem - connecting to exchanges, the Queen, the Enigma
systems, and all trading engines.

INTEGRATION MAP (mirrors aureon_enigma_integration.py):
─────────────────────────────────────────────────────────
  Exchange APIs     =>  Transaction Decoder (Sigma)
  CostBasisTracker  =>  Cost Basis Engine (Phi)
  TradeProfitValidator => P&L Calculator (Omega)
  Live Balances     =>  Portfolio Valuation (Gamma)
  Tax Configuration =>  Tax & Compliance (Psi)
  Queen Hive Mind   =>  Royal Decree (reports to Queen)
  Enigma System     =>  Intelligence Grades inform Health Grades
  Thought Bus       =>  King broadcasts financial events

Gary Leckey | February 2026
"The King and Queen rule the repo together."
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Lazy Kraken fee tracker (auto-calculates correct fee for Kraken trades) ──
_kraken_fee_tracker = None

def _get_kraken_fee_tracker():
    global _kraken_fee_tracker
    if _kraken_fee_tracker is None:
        try:
            from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker
            _kraken_fee_tracker = get_kraken_fee_tracker()
        except ImportError:
            pass
    return _kraken_fee_tracker


def _compute_kraken_fee(symbol: str, quantity: float, price: float,
                        is_taker: bool = True) -> float:
    """
    Return the correct Kraken fee in USD for a trade, based on the
    account's current 30-day volume tier.  Falls back to Tier 4
    taker rate (0.22%) if the tracker is unavailable.
    """
    tracker = _get_kraken_fee_tracker()
    if tracker is not None:
        try:
            rates = tracker.get_fee_rates(symbol=symbol, is_taker=is_taker)
            return quantity * price * rates['current']
        except Exception:
            pass
    # Fallback: Tier 4 taker 0.22%
    return quantity * price * 0.0022

# Lazy imports to avoid circular dependencies
_king = None
_ledger = None
_queen = None
_cost_basis_tracker = None
_validator = None


def _get_king():
    global _king
    if _king is None:
        from aureon.bots.king_accounting import get_king
        _king = get_king()
    return _king


def _get_ledger():
    global _ledger
    if _ledger is None:
        from aureon.bots.king_ledger import get_ledger
        _ledger = get_ledger()
    return _ledger


def _get_cost_basis_tracker():
    global _cost_basis_tracker
    if _cost_basis_tracker is None:
        try:
            from aureon.portfolio.cost_basis_tracker import CostBasisTracker
            _cost_basis_tracker = CostBasisTracker()
        except ImportError:
            _cost_basis_tracker = None
    return _cost_basis_tracker


def _get_validator():
    global _validator
    if _validator is None:
        try:
            from aureon.portfolio.trade_profit_validator import get_validator
            _validator = get_validator()
        except ImportError:
            _validator = None
    return _validator


# ═══════════════════════════════════════════════════════════════════════════
# TRADE HOOKS - Called by the trading ecosystem on every trade
# ═══════════════════════════════════════════════════════════════════════════

def king_on_buy(exchange: str, symbol: str, quantity: float, price: float,
                fee: float = 0.0, order_id: str = "",
                is_margin: bool = False, leverage: int = 1) -> Dict[str, Any]:
    """
    Hook called when a BUY order executes.
    Records the trade in the King's accounting system and double-entry ledger.

    For Kraken trades where fee=0 (not yet paid / not captured from API),
    the fee is auto-computed from KrakenFeeTracker using the live tier rate.
    """
    # Auto-compute Kraken fee from live tier if caller didn't provide one
    if fee == 0.0 and exchange.lower() == 'kraken':
        fee = _compute_kraken_fee(symbol, quantity, price, is_taker=True)

    king = _get_king()
    ledger = _get_ledger()

    # Record in King's accounting engine
    result = king.ingest_trade(
        exchange, symbol, "buy", quantity, price,
        fee=fee, order_id=order_id,
        is_margin=is_margin, leverage=leverage,
    )

    # Record in double-entry ledger
    asset = symbol
    for q in ["USDT", "USDC", "USD", "GBP", "EUR", "BTC", "XBT", "ETH"]:
        if symbol.upper().endswith(q) and len(symbol) > len(q):
            asset = symbol[:-len(q)]
            break

    if is_margin:
        margin_amount = (quantity * price) / leverage if leverage > 1 else quantity * price
        ledger.record_margin_open(
            exchange, asset, quantity, price, leverage,
            margin_amount=margin_amount, fee=fee, order_id=order_id,
        )
    else:
        ledger.record_buy(exchange, asset, quantity, price, fee=fee, order_id=order_id)

    # Broadcast to ThoughtBus if available
    _broadcast_financial_event("BUY", {
        "exchange": exchange, "symbol": symbol, "quantity": quantity,
        "price": price, "fee": fee, "is_margin": is_margin,
    })

    return result


def king_on_sell(exchange: str, symbol: str, quantity: float, price: float,
                 fee: float = 0.0, order_id: str = "",
                 is_margin: bool = False, leverage: int = 1) -> Dict[str, Any]:
    """
    Hook called when a SELL order executes.
    Records the trade, calculates realized P&L, updates ledger.

    For Kraken trades where fee=0 (not yet captured from API),
    the fee is auto-computed from KrakenFeeTracker using the live tier rate.
    """
    # Auto-compute Kraken fee from live tier if caller didn't provide one
    if fee == 0.0 and exchange.lower() == 'kraken':
        fee = _compute_kraken_fee(symbol, quantity, price, is_taker=True)

    king = _get_king()
    ledger = _get_ledger()

    # Record in King's accounting engine (handles FIFO cost basis)
    result = king.ingest_trade(
        exchange, symbol, "sell", quantity, price,
        fee=fee, order_id=order_id,
        is_margin=is_margin, leverage=leverage,
    )

    # Extract asset name
    asset = symbol
    for q in ["USDT", "USDC", "USD", "GBP", "EUR", "BTC", "XBT", "ETH"]:
        if symbol.upper().endswith(q) and len(symbol) > len(q):
            asset = symbol[:-len(q)]
            break

    # Get cost basis for ledger entry
    realized = result.get("realized_gain", {})
    cost_basis = realized.get("cost_basis", quantity * price)

    if is_margin:
        margin_amount = cost_basis / leverage if leverage > 1 else cost_basis
        borrowed = cost_basis - margin_amount
        ledger.record_margin_close(
            exchange, asset, quantity, price,
            cost_basis=cost_basis, margin_amount=margin_amount,
            borrowed=borrowed, fee=fee, order_id=order_id,
        )
    else:
        ledger.record_sell(
            exchange, asset, quantity, price,
            cost_basis=cost_basis, fee=fee, order_id=order_id,
        )

    # Broadcast
    pnl = realized.get("net", 0)
    _broadcast_financial_event("SELL", {
        "exchange": exchange, "symbol": symbol, "quantity": quantity,
        "price": price, "fee": fee, "pnl": pnl, "is_margin": is_margin,
    })

    return result


def king_on_deposit(exchange: str, asset: str, quantity: float) -> Dict[str, Any]:
    """Hook called when a deposit is detected."""
    king = _get_king()
    ledger = _get_ledger()

    result = king.ingest_deposit(exchange, asset, quantity)
    ledger.record_deposit(exchange, asset, quantity)

    _broadcast_financial_event("DEPOSIT", {
        "exchange": exchange, "asset": asset, "quantity": quantity,
    })
    return result


def king_on_withdrawal(exchange: str, asset: str, quantity: float,
                       fee: float = 0.0) -> Dict[str, Any]:
    """Hook called when a withdrawal is detected."""
    king = _get_king()
    ledger = _get_ledger()

    result = king.ingest_withdrawal(exchange, asset, quantity, fee=fee)
    ledger.record_withdrawal(exchange, asset, quantity, fee=fee)

    _broadcast_financial_event("WITHDRAWAL", {
        "exchange": exchange, "asset": asset, "quantity": quantity, "fee": fee,
    })
    return result


# ═══════════════════════════════════════════════════════════════════════════
# SYNC WITH EXISTING SYSTEMS
# ═══════════════════════════════════════════════════════════════════════════

def sync_king_from_cost_basis_tracker():
    """
    Import existing position data from CostBasisTracker into the King.
    This bootstraps the King's books from the existing tracking system.
    """
    king = _get_king()
    tracker = _get_cost_basis_tracker()

    if not tracker:
        logger.warning("CostBasisTracker not available for sync")
        return {"synced": 0}

    synced = 0
    try:
        # Load existing positions
        if hasattr(tracker, 'positions'):
            for key, pos_data in tracker.positions.items():
                if not isinstance(pos_data, dict):
                    continue
                exchange = pos_data.get("exchange", "unknown")
                symbol = pos_data.get("symbol", key)
                quantity = float(pos_data.get("total_quantity", 0))
                avg_price = float(pos_data.get("avg_entry_price", 0))
                total_cost = float(pos_data.get("total_cost", 0))
                total_fees = float(pos_data.get("total_fees", 0))

                if quantity > 0 and avg_price > 0:
                    king.ingest_trade(
                        exchange, symbol, "buy", quantity, avg_price,
                        fee=total_fees,
                        order_id=pos_data.get("last_order_id", ""),
                    )
                    synced += 1

        logger.info(f"King synced {synced} positions from CostBasisTracker")
    except Exception as e:
        logger.error(f"Error syncing King from CostBasisTracker: {e}")

    return {"synced": synced}


def sync_king_from_exchanges():
    """
    Pull trade history from exchanges and import into the King.
    This is a heavy operation - call sparingly.
    """
    king = _get_king()
    synced = 0

    # Sync from Kraken
    try:
        from aureon.exchanges.kraken_client import get_kraken_client
        client = get_kraken_client()
        if client and not client.dry_run:
            # Get trade history from Kraken
            trades = client._private("/0/private/TradesHistory", {"type": "all"})
            if isinstance(trades, dict) and "trades" in trades:
                for txid, trade in trades["trades"].items():
                    pair = trade.get("pair", "")
                    side = trade.get("type", "")
                    vol = float(trade.get("vol", 0))
                    price = float(trade.get("price", 0))
                    fee = float(trade.get("fee", 0))
                    ts = float(trade.get("time", 0))
                    leverage = trade.get("leverage", "")

                    is_margin = leverage and leverage != "none" and leverage != ""

                    king.ingest_trade(
                        "kraken", pair, side, vol, price,
                        fee=fee, order_id=txid,
                        is_margin=bool(is_margin),
                        leverage=int(leverage.split(":")[0]) if is_margin and ":" in str(leverage) else 1,
                        timestamp=ts,
                    )
                    synced += 1
    except Exception as e:
        logger.error(f"Error syncing King from Kraken: {e}")

    logger.info(f"King synced {synced} trades from exchanges")
    return {"synced": synced}


# ═══════════════════════════════════════════════════════════════════════════
# RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════

def reconcile_all_exchanges() -> Dict[str, Any]:
    """Reconcile the King's books with all exchange balances."""
    king = _get_king()
    results = {}

    for exchange_name in ["kraken", "binance", "alpaca", "capital"]:
        try:
            from aureon.trading.unified_exchange_client import UnifiedExchangeClient
            client = UnifiedExchangeClient(exchange_name)
            balances = client.get_all_balances()
            if balances:
                result = king.reconcile(exchange_name, balances)
                results[exchange_name] = result
        except Exception as e:
            results[exchange_name] = {"error": str(e)}

    return results


# ═══════════════════════════════════════════════════════════════════════════
# REPORTING
# ═══════════════════════════════════════════════════════════════════════════

def get_king_dashboard() -> Dict[str, Any]:
    """Get a comprehensive dashboard view from the King."""
    king = _get_king()
    ledger = _get_ledger()

    # Get current prices from exchanges
    current_prices = _fetch_current_prices()

    summary = king.get_financial_summary(current_prices)
    portfolio = king.get_portfolio_snapshot(current_prices)
    pnl_30d = king.get_pnl_report(days=30)
    audit = king.get_audit_report()

    # Ledger statements
    trial_balance = ledger.trial_balance()
    balance_sheet = ledger.balance_sheet()

    return {
        "timestamp": datetime.now().isoformat(),
        "royal_decree": summary.get("the_king_says", ""),
        "financial_summary": summary,
        "portfolio": portfolio,
        "pnl_30d": pnl_30d,
        "audit": audit,
        "trial_balance": trial_balance,
        "balance_sheet": balance_sheet,
    }


def print_king_report():
    """Print a full King report to stdout."""
    king = _get_king()
    ledger = _get_ledger()

    print("\n" + king.generate_daily_report())
    print("\n" + ledger.print_trial_balance())

    bs = ledger.balance_sheet()
    sym = "£" if king.base_currency == "GBP" else "$"

    print("\n" + "=" * 60)
    print("THE KING'S BALANCE SHEET")
    print("=" * 60)
    print(f"\nASSETS:")
    for name, val in bs.get("assets", {}).items():
        print(f"  {name:<30s} {sym}{val:>12.2f}")
    print(f"  {'TOTAL ASSETS':<30s} {sym}{bs['total_assets']:>12.2f}")
    print(f"\nLIABILITIES:")
    for name, val in bs.get("liabilities", {}).items():
        print(f"  {name:<30s} {sym}{val:>12.2f}")
    print(f"  {'TOTAL LIABILITIES':<30s} {sym}{bs['total_liabilities']:>12.2f}")
    print(f"\nEQUITY:")
    for name, val in bs.get("equity", {}).items():
        print(f"  {name:<30s} {sym}{val:>12.2f}")
    print(f"  {'Net Income':<30s} {sym}{bs['net_income']:>12.2f}")
    print(f"  {'TOTAL EQUITY':<30s} {sym}{bs['total_equity']:>12.2f}")
    balanced = "YES" if bs.get("accounting_equation_balanced") else "NO"
    print(f"\nA = L + E balanced: {balanced}")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════════════
# AUTONOMOUS STARTUP
# ═══════════════════════════════════════════════════════════════════════════

def start_king():
    """
    Start the King's autonomous monitoring.
    Call this from the main trading engine startup.
    """
    king = _get_king()
    king.start_autonomous()
    logger.info("The King has risen. Long live the King!")
    return king


def stop_king():
    """Stop the King's autonomous monitoring."""
    king = _get_king()
    king.stop_autonomous()
    logger.info("The King rests.")


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_current_prices() -> Dict[str, float]:
    """Fetch current prices from exchanges for portfolio valuation."""
    prices = {}
    try:
        from aureon.trading.unified_exchange_client import UnifiedExchangeClient
        for exchange_name in ["kraken", "binance"]:
            try:
                client = UnifiedExchangeClient(exchange_name)
                tickers = client.get_24h_tickers()
                for t in tickers:
                    sym = t.get("symbol", "")
                    price = 0.0
                    if "lastPrice" in t:
                        try:
                            price = float(t["lastPrice"])
                        except (ValueError, TypeError):
                            pass
                    elif "price" in t:
                        try:
                            price = float(t["price"])
                        except (ValueError, TypeError):
                            pass
                    if price > 0 and sym:
                        # Map to "exchange:asset" format
                        for q in ["USDT", "USDC", "USD", "GBP", "EUR"]:
                            if sym.endswith(q) and len(sym) > len(q):
                                asset = sym[:-len(q)]
                                if asset == "XBT":
                                    asset = "BTC"
                                prices[f"{exchange_name}:{asset}"] = price
                                break
            except Exception:
                pass
    except ImportError:
        pass
    return prices


def _broadcast_financial_event(event_type: str, data: Dict):
    """Broadcast a financial event to the ThoughtBus if available."""
    try:
        from aureon.autonomous.aureon_mind_thought_action_hub import ThoughtBus
        bus = ThoughtBus.get_instance() if hasattr(ThoughtBus, "get_instance") else None
        if bus and hasattr(bus, "emit"):
            bus.emit({
                "source": "TheKing",
                "event": f"KING_{event_type}",
                "data": data,
                "timestamp": time.time(),
            })
    except (ImportError, Exception):
        pass  # ThoughtBus not available, that's fine


# ═══════════════════════════════════════════════════════════════════════════
# HISTORICAL RECONCILIATION - Feed all past trades through the King
# ═══════════════════════════════════════════════════════════════════════════

# ── Live price cache for fee-to-USD conversion ──
_fee_price_cache: Dict[str, float] = {}
_fee_price_cache_ts: float = 0.0
_FEE_PRICE_CACHE_TTL = 300  # 5 minutes


def _fetch_live_price_usd(asset: str) -> float:
    """
    Fetch a LIVE USD price for an asset using Binance public API.
    Uses a short-lived cache to avoid hammering rate limits during batch reconciliation.
    Returns 0.0 if the price can't be determined.
    """
    global _fee_price_cache, _fee_price_cache_ts

    asset_upper = asset.upper()

    # Expire stale cache
    if time.time() - _fee_price_cache_ts > _FEE_PRICE_CACHE_TTL:
        _fee_price_cache.clear()
        _fee_price_cache_ts = time.time()

    if asset_upper in _fee_price_cache:
        return _fee_price_cache[asset_upper]

    # Try Binance public ticker (no auth needed)
    import requests
    for quote in ("USDC", "USDT", "USD"):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={asset_upper}{quote}"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                price = float(r.json().get("price", 0))
                if price > 0:
                    _fee_price_cache[asset_upper] = price
                    return price
        except Exception:
            pass

    # Try Kraken public (for assets that exist there but not Binance)
    kraken_map = {"XXBT": "BTC", "XETH": "ETH", "XBT": "BTC"}
    kraken_asset = asset_upper
    for k, v in kraken_map.items():
        if asset_upper == v:
            kraken_asset = k
    try:
        url = f"https://api.kraken.com/0/public/Ticker?pair={kraken_asset}USD"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if not data.get("error"):
                for pair_data in data.get("result", {}).values():
                    price = float(pair_data["c"][0])
                    if price > 0:
                        _fee_price_cache[asset_upper] = price
                        return price
    except Exception:
        pass

    _fee_price_cache[asset_upper] = 0.0
    return 0.0


def _estimate_fee_usd(fee_raw: float, fee_asset: str, trade_price: float,
                      trade_symbol: str) -> float:
    """
    Convert a fee denominated in any asset to approximate USD value.

    Strategy:
      1. If fee_asset is already USD/USDC/USDT → use raw value
      2. If fee_asset matches the traded base asset → use trade_price * fee_raw
      3. Fetch LIVE price from Binance/Kraken public API (cached 5 min)
      4. Last resort: fee_raw * 1 (conservative fallback, logged)
    """
    if fee_raw == 0 or fee_raw is None:
        return 0.0

    usd_stables = {"USD", "USDC", "USDT", "BUSD", "DAI", "TUSD", "FDUSD"}
    if fee_asset.upper() in usd_stables:
        return fee_raw

    # If fee_asset matches the base of the traded pair, use the trade price
    # e.g. BNBUSDC trade, fee in BNB → fee_usd = fee_raw * trade_price
    base = trade_symbol
    for q in ["USDT", "USDC", "USD", "GBP", "EUR", "BTC", "ETH"]:
        if trade_symbol.upper().endswith(q) and len(trade_symbol) > len(q):
            base = trade_symbol[:-len(q)]
            break
    # Also handle slash-separated symbols like BTC/USD
    if "/" in trade_symbol:
        base = trade_symbol.split("/")[0]

    if fee_asset.upper() == base.upper():
        return fee_raw * trade_price

    # ── NEW: Fetch LIVE price instead of using stale hardcoded values ──
    live_price = _fetch_live_price_usd(fee_asset)
    if live_price > 0:
        return fee_raw * live_price

    # Last resort: if the fee amount itself is tiny, treat it as negligible
    logger.warning(f"_estimate_fee_usd: No price found for fee asset '{fee_asset}', "
                   f"using 1:1 fallback (fee_raw={fee_raw:.6f})")
    return fee_raw  # Assume 1:1 as conservative fallback


def king_reconcile_history(trade_history_file: str = "trade_history_audit.json",
                           reset: bool = True, verbose: bool = True) -> Dict[str, Any]:
    """
    Feed ALL historical trades through the King's accounting system.

    This creates:
      - king_state.json: Full FIFO tax lots + realized gains
      - king_double_entry_ledger.json: Complete double-entry journal
      - king_audit.jsonl: Comprehensive audit trail

    Args:
        trade_history_file: Path to the reconciled trade history JSON
        reset: If True, clear existing King/Ledger state first (recommended)
        verbose: Print progress

    Returns:
        Summary dict with stats
    """
    from collections import defaultdict as _dd

    # Load trade history
    path = Path(trade_history_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Trade history not found: {trade_history_file}\n"
            f"Run reconciliation first: python cost_basis_tracker.py reconcile"
        )

    with open(path) as f:
        data = json.load(f)

    trades = data.get("trades", [])
    if not trades:
        raise ValueError("No trades found in trade history file")

    # Sort chronologically (critical for FIFO accuracy)
    trades.sort(key=lambda t: t.get("timestamp", 0))

    if verbose:
        print("=" * 70)
        print("👑 THE KING'S HISTORICAL RECONCILIATION")
        print(f"   Trades to process: {len(trades)}")
        print(f"   Date range: {trades[0].get('datetime', '?')[:10]} → "
              f"{trades[-1].get('datetime', '?')[:10]}")
        print(f"   Reset existing state: {reset}")
        print("=" * 70)

    # Get King and Ledger instances
    king = _get_king()
    ledger = _get_ledger()

    if reset:
        # Clear King state
        king.treasury.sigma.transactions.clear()
        king.treasury.sigma._tx_counter = 0
        king.treasury.phi.tax_lots.clear()
        king.treasury.phi._lot_counter = 0
        king.treasury.phi.realized_gains.clear()
        king.treasury.omega.daily_realized.clear()
        king.treasury.omega.total_realized = 0.0
        king.treasury.omega.total_fees_paid = 0.0
        king.treasury.omega.wins = 0
        king.treasury.omega.losses = 0

        # Clear Ledger state
        ledger.journal.clear()
        ledger.account_balances.clear()
        ledger._entry_counter = 0

        # Clear audit log
        audit_path = Path("king_audit.jsonl")
        if audit_path.exists():
            audit_path.write_text("")

        if verbose:
            print("   🧹 Cleared existing state")

    # Stats
    stats = {
        "total": len(trades),
        "buys": 0, "sells": 0,
        "buy_value": 0.0, "sell_value": 0.0,
        "fees_usd": 0.0,
        "errors": 0,
        "by_exchange": _dd(lambda: {"buys": 0, "sells": 0, "value": 0.0}),
        "by_symbol": _dd(int),
    }

    # ── Batch mode: temporarily disable per-trade saves ──
    # We'll save once at the end instead of 2,110 times
    original_king_save = king._save_state
    original_ledger_save = ledger._save
    king._save_state = lambda: None  # no-op during batch
    ledger._save = lambda: None      # no-op during batch

    try:
        for i, trade in enumerate(trades):
            exchange = trade.get("exchange", "unknown")
            symbol = trade.get("symbol", "")
            side = trade.get("side", "").lower()
            quantity = float(trade.get("quantity", 0))
            price = float(trade.get("price", 0))
            fee_raw = float(trade.get("fee", 0))
            fee_asset = trade.get("fee_asset", "USD")
            order_id = str(trade.get("order_id", ""))
            timestamp = float(trade.get("timestamp", 0))

            if quantity <= 0 or price <= 0:
                stats["errors"] += 1
                continue

            # Convert fee to USD
            fee_usd = _estimate_fee_usd(fee_raw, fee_asset, price, symbol)

            # Extract asset name for ledger
            asset = symbol
            for q in ["USDT", "USDC", "USD", "GBP", "EUR", "BTC", "XBT", "ETH"]:
                if symbol.upper().endswith(q) and len(symbol) > len(q):
                    asset = symbol[:-len(q)]
                    break
            if "/" in symbol:
                asset = symbol.split("/")[0]

            try:
                if side == "buy":
                    # King: FIFO lot creation + audit
                    king.ingest_trade(
                        exchange, symbol, "buy", quantity, price,
                        fee=fee_usd, order_id=order_id, timestamp=timestamp,
                    )
                    # Ledger: double-entry journal with historical timestamp
                    ledger.record_buy(exchange, asset, quantity, price,
                                      fee=fee_usd, order_id=order_id, ts=timestamp)

                    stats["buys"] += 1
                    stats["buy_value"] += quantity * price
                    stats["by_exchange"][exchange]["buys"] += 1

                elif side == "sell":
                    # King: FIFO lot consumption + realized P&L + audit
                    result = king.ingest_trade(
                        exchange, symbol, "sell", quantity, price,
                        fee=fee_usd, order_id=order_id, timestamp=timestamp,
                    )
                    # Get cost basis from King for ledger
                    realized = result.get("realized_gain", {})
                    cost_basis = realized.get("cost_basis", quantity * price)

                    # Ledger: double-entry journal with historical timestamp
                    ledger.record_sell(exchange, asset, quantity, price,
                                       cost_basis=cost_basis, fee=fee_usd,
                                       order_id=order_id, ts=timestamp)

                    stats["sells"] += 1
                    stats["sell_value"] += quantity * price
                    stats["by_exchange"][exchange]["sells"] += 1

                stats["fees_usd"] += fee_usd
                stats["by_exchange"][exchange]["value"] += quantity * price
                stats["by_symbol"][symbol] += 1

            except Exception as e:
                stats["errors"] += 1
                if verbose and stats["errors"] <= 10:
                    print(f"   ⚠ Error on trade {i+1} ({symbol} {side}): {e}")

            # Progress
            if verbose and (i + 1) % 250 == 0:
                print(f"   📊 Processed {i+1}/{len(trades)} trades...")

    finally:
        # Restore save functions
        king._save_state = original_king_save
        ledger._save = original_ledger_save

    # ── Single final save ──
    if verbose:
        print("   💾 Saving King state...")

    # Increase state limits for full history
    # Monkey-patch _save_state temporarily to save ALL data
    def _save_full_state():
        try:
            state = {
                "saved_at": datetime.now().isoformat(),
                "reconciliation": True,
                "source": trade_history_file,
                "trades_processed": len(trades),
                "transactions": [
                    {"id": t.id, "timestamp": t.timestamp, "tx_type": t.tx_type,
                     "exchange": t.exchange, "symbol": t.symbol, "asset": t.asset,
                     "side": t.side, "quantity": t.quantity, "price": t.price,
                     "value": t.value, "fee": t.fee, "order_id": t.order_id}
                    for t in king.treasury.sigma.transactions
                ],
                "tax_lots": {
                    k: [{"id": lot.id, "timestamp": lot.timestamp, "exchange": lot.exchange,
                         "symbol": lot.symbol, "asset": lot.asset, "quantity": lot.quantity,
                         "original_quantity": lot.original_quantity, "price": lot.price,
                         "cost": lot.cost, "fee": lot.fee, "order_id": lot.order_id}
                        for lot in lots]
                    for k, lots in king.treasury.phi.tax_lots.items() if lots
                },
                "realized_gains": [
                    {"id": g.id, "timestamp": g.timestamp, "exchange": g.exchange,
                     "symbol": g.symbol, "asset": g.asset, "quantity_sold": g.quantity_sold,
                     "sell_price": g.sell_price, "sell_value": g.sell_value,
                     "cost_basis": g.cost_basis, "gross_gain": g.gross_gain,
                     "total_fees": g.total_fees, "net_gain": g.net_gain,
                     "hold_time_seconds": g.hold_time_seconds,
                     "tax_lots_consumed": g.tax_lots_consumed}
                    for g in king.treasury.phi.realized_gains
                ],
                "pnl_summary": king.treasury.omega.get_summary(),
            }
            tmp = Path("king_state.json.tmp")
            tmp.write_text(json.dumps(state, indent=2, default=str))
            tmp.rename("king_state.json")
        except Exception as e:
            logger.error(f"King full save error: {e}")

    _save_full_state()
    ledger._save()

    if verbose:
        print("   💾 Saving Ledger...")

    # ── Summary ──
    pnl = king.treasury.omega.get_summary()
    positions = king.treasury.phi.get_all_positions()

    stats["realized_pnl"] = pnl.get("total_realized_pnl", 0)
    stats["total_fees_paid"] = pnl.get("total_fees_paid", 0)
    stats["win_rate"] = pnl.get("win_rate", 0)
    stats["wins"] = pnl.get("wins", 0)
    stats["losses"] = pnl.get("losses", 0)
    stats["open_positions"] = len(positions)
    stats["journal_entries"] = len(ledger.journal)

    if verbose:
        print()
        print("=" * 70)
        print("👑 THE KING'S HISTORICAL RECONCILIATION — COMPLETE")
        print("=" * 70)
        print(f"   Trades processed:    {stats['buys'] + stats['sells']:,}")
        print(f"   Buys:                {stats['buys']:,} (${stats['buy_value']:,.2f})")
        print(f"   Sells:               {stats['sells']:,} (${stats['sell_value']:,.2f})")
        print(f"   Total fees (USD):    ${stats['fees_usd']:.2f}")
        print(f"   Errors:              {stats['errors']}")
        print()
        print(f"   Realized P&L:        ${stats['realized_pnl']:+,.2f}")
        print(f"   Win Rate:            {stats['win_rate']:.1f}% "
              f"({stats['wins']}W / {stats['losses']}L)")
        print(f"   Open Positions:      {stats['open_positions']}")
        print(f"   Journal Entries:     {stats['journal_entries']:,}")
        print()
        print("   Files written:")
        print("    • king_state.json           (FIFO lots + realized gains)")
        print("    • king_double_entry_ledger.json  (double-entry journal)")
        print("    • king_audit.jsonl           (audit trail)")
        print()

        # Trial balance
        tb = ledger.trial_balance()
        print(ledger.print_trial_balance())
        if not tb["is_balanced"]:
            diff = abs(tb["total_debit"] - tb["total_credit"])
            print(f"\n   ⚠ IMBALANCE: ${diff:.2f} — investigate!")
        print()

        # Top positions
        if positions:
            print("   Top 10 Open Positions:")
            print(f"   {'Position':<25s} {'Qty':>12s} {'Avg Price':>12s} {'Total Cost':>12s}")
            print("   " + "-" * 65)
            sorted_pos = sorted(positions.items(),
                                key=lambda x: x[1].get("total_cost", 0), reverse=True)
            for key, pos in sorted_pos[:10]:
                print(f"   {key:<25s} {pos['quantity']:>12.6f} "
                      f"${pos['avg_price']:>11.2f} ${pos['total_cost']:>11.2f}")
            print()

    return stats


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys as _sys

    if len(_sys.argv) > 1 and _sys.argv[1] in ("reconcile", "history", "reconcile-history"):
        file = _sys.argv[2] if len(_sys.argv) > 2 else "trade_history_audit.json"
        no_reset = "--no-reset" in _sys.argv
        result = king_reconcile_history(file, reset=not no_reset)
        print(f"\n✅ Historical reconciliation complete: {result['buys'] + result['sells']} trades")

    elif len(_sys.argv) > 1 and _sys.argv[1] == "summary":
        king = _get_king()
        summary = king.get_financial_summary()
        print(json.dumps(summary, indent=2, default=str))

    elif len(_sys.argv) > 1 and _sys.argv[1] == "trial-balance":
        ledger = _get_ledger()
        print(ledger.print_trial_balance())

    elif len(_sys.argv) > 1 and _sys.argv[1] == "balance-sheet":
        ledger = _get_ledger()
        bs = ledger.balance_sheet()
        print(json.dumps(bs, indent=2, default=str))

    elif len(_sys.argv) > 1 and _sys.argv[1] == "tax-report":
        king = _get_king()
        year = int(_sys.argv[2]) if len(_sys.argv) > 2 else None
        report = king.get_tax_report(year)
        print(json.dumps(report, indent=2, default=str))

    elif len(_sys.argv) > 1 and _sys.argv[1] == "daily-report":
        king = _get_king()
        print(king.generate_daily_report())

    else:
        print("👑 The King's Commands:")
        print("  python king_integration.py reconcile       Feed all historical trades")
        print("  python king_integration.py summary         Financial summary")
        print("  python king_integration.py trial-balance   Trial balance (DR=CR)")
        print("  python king_integration.py balance-sheet   Balance sheet")
        print("  python king_integration.py tax-report [yr] Tax report (UK CGT)")
        print("  python king_integration.py daily-report    Daily P&L report")
