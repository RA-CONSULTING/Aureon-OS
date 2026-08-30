#!/usr/bin/env python3
"""
🦑🔌 KRAKEN TRADING ADAPTER 🔌🦑
══════════════════════════════════════════════════════════════════

Wraps KrakenClient to provide Alpaca-compatible interface for the Orca.

Kraken is SPOT trading - you OWN the crypto in your balance.
This adapter tracks "positions" by monitoring balance changes.

Gary Leckey | January 2026
"""

import json
import time
import logging
import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from decimal import Decimal

logger = logging.getLogger(__name__)
MAX_RECEIPT_AGE_SECONDS = 300.0


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _canonical_pair(value: Any) -> str:
    base, quote = _pair_assets(value)
    if base and quote:
        return base + quote
    return str(value or "").strip().upper().replace("/", "").replace("-", "")


def _canonical_asset(value: Any) -> str:
    asset = str(value or "").strip().upper()
    aliases = {
        "XBT": "BTC", "XXBT": "BTC", "XDG": "DOGE", "XXDG": "DOGE",
        "XETH": "ETH", "XXETH": "ETH", "ZUSD": "USD", "ZEUR": "EUR",
        "ZGBP": "GBP", "ZCAD": "CAD", "ZJPY": "JPY", "ZAUD": "AUD",
    }
    if asset in aliases:
        return aliases[asset]
    if asset.startswith(("X", "Z")) and len(asset) > 3:
        return asset[1:]
    return asset


def _pair_assets(value: Any) -> tuple[str, str]:
    pair = str(value or "").strip().upper().replace("/", "").replace("-", "")
    for provider_quote in (
        "USDT", "USDC", "TUSD", "ZUSD", "ZEUR", "ZGBP", "ZCAD",
        "ZJPY", "ZAUD", "USD", "EUR", "GBP", "CAD", "JPY", "AUD",
    ):
        if pair.endswith(provider_quote) and len(pair) > len(provider_quote):
            return (
                _canonical_asset(pair[:-len(provider_quote)]),
                _canonical_asset(provider_quote),
            )
    return "", ""


def _identifier(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or candidate.lower() in {"none", "null", "unknown"}:
        return None
    return candidate


def _derived_receipt_id(kind: str, payload: Dict[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"kraken_adapter_{kind}:" + hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()


def _fresh_receipt_times(receipt: Dict[str, Any]) -> Optional[tuple[float, float]]:
    now = time.time()
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    if (
        source_timestamp is None
        or received_at is None
        or source_timestamp > received_at + 5.0
        or received_at > now + 5.0
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return source_timestamp, received_at


def _pending_receipt(
    order_id: Optional[str],
    reason: str,
    *,
    input_receipt_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    inputs = []
    for value in input_receipt_ids or []:
        receipt_id = _identifier(value)
        if receipt_id is not None and receipt_id not in inputs:
            inputs.append(receipt_id)
    receipt_id = (
        _derived_receipt_id(
            "pending_order",
            {"order_id": order_id, "reason": reason, "input_receipt_ids": inputs},
        )
        if order_id or inputs else None
    )
    return {
        "id": order_id,
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "truth_status": "no_data",
        "reason": reason,
        "source_timestamp": None,
        "received_at": time.time(),
        "source_id": "aureon:kraken-trading-adapter:pending" if receipt_id else None,
        "receipt_id": receipt_id,
        "input_receipt_ids": inputs,
        "generated_values": False,
        "action": False,
        "accounting": False,
        "learning": False,
    }


def _terminal_receipt(
    receipt: Any,
    *,
    order_id: str,
    symbol: str,
    side: str,
    expected_quantity: float,
) -> Optional[Dict[str, Any]]:
    if not isinstance(receipt, dict):
        return None
    now = time.time()
    receipt_order_id = str(receipt.get("orderId") or "").strip()
    quantity = _finite(receipt.get("filled_qty"), positive=True)
    price = _finite(receipt.get("filled_avg_price"), positive=True)
    notional = _finite(receipt.get("filled_notional"), positive=True)
    fee = _finite(receipt.get("fee"), nonnegative=True)
    fee_currency = str(receipt.get("fee_currency") or "").strip().upper()
    fee_asset = str(receipt.get("fee_asset") or "").strip().upper()
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    receipt_id = _identifier(receipt.get("receipt_id"))
    source_id = _identifier(receipt.get("source_id"))
    provider_receipt_type = str(receipt.get("provider_receipt_type") or "").strip()
    raw_input_ids = receipt.get("input_receipt_ids")
    input_receipt_ids = (
        [_identifier(value) for value in raw_input_ids]
        if isinstance(raw_input_ids, list) else []
    )
    fills = receipt.get("fills")
    trade_ids = [
        str(row.get("tradeId") or "").strip()
        for row in fills
        if isinstance(row, dict) and str(row.get("tradeId") or "").strip()
    ] if isinstance(fills, list) else []
    fill_sources = [
        str(row.get("source") or "").strip()
        for row in fills
        if isinstance(row, dict)
    ] if isinstance(fills, list) else []
    expected_notional = quantity * price if quantity is not None and price is not None else None
    _base_asset, expected_fee_currency = _pair_assets(symbol)
    if (
        receipt.get("status") != "FILLED"
        or receipt.get("data_status") != "live"
        or receipt.get("truth_status") != "real_observed"
        or receipt.get("generated_values") is not False
        or receipt.get("fill_receipt_complete") is not True
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("eligible_for_learning") is not True
        or receipt.get("reconciliation_required") is not False
        or str(receipt.get("provider") or "").strip().lower() != "kraken"
        or str(receipt.get("venue") or "").strip().lower() != "kraken"
        or provider_receipt_type not in {"QueryOrders", "ClosedOrders"}
        or source_id is None
        or not source_id.startswith(f"kraken:/0/private/{provider_receipt_type}:")
        or receipt_id is None
        or not receipt_id.startswith("kraken_order:")
        or receipt_order_id != str(order_id)
        or _canonical_pair(receipt.get("symbol")) != _canonical_pair(symbol)
        or str(receipt.get("side") or "").strip().upper() != side.upper()
        or quantity is None
        or not math.isclose(quantity, expected_quantity, rel_tol=1e-12, abs_tol=1e-12)
        or price is None
        or notional is None
        or fee is None
        or not expected_fee_currency
        or fee_currency != expected_fee_currency
        or fee_asset != expected_fee_currency
        or not trade_ids
        or not isinstance(fills, list)
        or len(fills) != len(trade_ids)
        or len(set(trade_ids)) != len(trade_ids)
        or len(fill_sources) != len(trade_ids)
        or any(source != f"kraken_{provider_receipt_type.lower()}" for source in fill_sources)
        or not input_receipt_ids
        or any(value is None for value in input_receipt_ids)
        or len(input_receipt_ids) != len(set(input_receipt_ids))
        or input_receipt_ids != [f"kraken_trade:{trade_id}" for trade_id in trade_ids]
        or expected_notional is None
        or not math.isclose(notional, expected_notional, rel_tol=0.001, abs_tol=1e-8)
        or source_timestamp is None
        or received_at is None
        or source_timestamp > received_at + 5.0
        or received_at > now + 5.0
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return dict(receipt)

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker
    _FEE_TRACKER_AVAILABLE = True
except ImportError:
    _FEE_TRACKER_AVAILABLE = False


@dataclass
class KrakenPosition:
    """Simulated position for Kraken spot holdings."""
    symbol: str              # e.g., "SOL/USD"
    asset: str              # e.g., "SOL"
    qty: float              # Amount held
    avg_entry_price: float  # Estimated entry price
    current_price: float    # Current market price
    market_value: float     # qty * current_price
    unrealized_pl: float    # Estimated P&L
    unrealized_plpc: float  # P&L percentage
    entry_time: float       # When we started tracking
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict matching Alpaca position format."""
        return {
            'symbol': self.symbol,
            'asset': self.asset,
            'qty': str(self.qty),
            'avg_entry_price': str(self.avg_entry_price),
            'current_price': str(self.current_price),
            'market_value': str(self.market_value),
            'unrealized_pl': str(self.unrealized_pl),
            'unrealized_plpc': str(self.unrealized_plpc),
        }


class KrakenTradingAdapter:
    """
    🦑🔌 Adapter to make Kraken work like Alpaca for the Orca! 🔌🦑
    
    Provides:
    - place_order() - unified interface
    - get_positions() - tracks balance as positions
    - get_account() - account info
    - get_ticker() - price data
    """
    
    # Assets we consider as "base" (not quote/stablecoins)
    TRADING_ASSETS = {'BTC', 'ETH', 'SOL', 'DOGE', 'ATOM', 'SEI', 'DOT', 'LINK', 'AVAX', 'ADA'}
    STABLECOINS = {'USD', 'ZUSD', 'USDT', 'USDC', 'TUSD', 'DAI', 'BUSD'}
    
    # Kraken asset name mapping
    ASSET_MAP = {
        'XXBT': 'BTC',
        'XETH': 'ETH',
        'XBT': 'BTC',
        'ZUSD': 'USD',
    }
    
    # Fallback fee rate (taker) used when fee tracker is unavailable.
    # At ~$123K 30-day volume this is Tier 4: maker=12bps, taker=22bps.
    FEE_RATE = 0.0022  # 0.22% (Tier 4 taker, updated from old hardcoded 0.26%)

    def __init__(self):
        if not KRAKEN_AVAILABLE:
            raise RuntimeError("KrakenClient not available")

        self.client = get_kraken_client()
        self.positions_file = Path("kraken_positions.json")
        self.tracked_positions: Dict[str, Dict] = {}
        self._pending_orders: Dict[tuple[str, str, str, str], Dict[str, Any]] = {}

        # Wire up the dynamic fee tracker so every order uses the correct tier
        if _FEE_TRACKER_AVAILABLE:
            self._fee_tracker = get_kraken_fee_tracker(self.client)
        else:
            self._fee_tracker = None

        self._load_positions()
        logger.info("🦑 Kraken Trading Adapter initialized")

    def get_fee_rate(self, symbol: str = '', is_taker: bool = True) -> float:
        """
        Return the current maker or taker fee rate for *symbol*.

        Uses KrakenFeeTracker when available (dynamic tier lookup),
        otherwise falls back to FEE_RATE.
        """
        if self._fee_tracker is not None:
            try:
                rates = self._fee_tracker.get_fee_rates(symbol=symbol, is_taker=is_taker)
                return rates['current']
            except Exception as e:
                logger.warning(f"Fee tracker error: {e} — falling back to FEE_RATE")
        return self.FEE_RATE
    
    def _normalize_asset(self, asset: str) -> str:
        """Normalize Kraken asset names."""
        return self.ASSET_MAP.get(asset, asset)
    
    def _load_positions(self):
        """Load tracked positions from file."""
        try:
            if self.positions_file.exists():
                self.tracked_positions = json.loads(self.positions_file.read_text())
                logger.info(f"📂 Loaded {len(self.tracked_positions)} tracked positions")
        except Exception as e:
            logger.warning(f"Could not load positions: {e}")
            self.tracked_positions = {}
    
    def _save_positions(self):
        """Save tracked positions to file."""
        try:
            self.positions_file.write_text(json.dumps(self.tracked_positions, indent=2))
        except Exception as e:
            logger.error(f"Could not save positions: {e}")

    @staticmethod
    def _no_data_account(reason: str) -> Dict[str, Any]:
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "truth_status": "no_data",
            "generated_values": False,
            "account_scope": "incomplete",
            "source_id": None,
            "source_timestamp": None,
            "receipt_id": None,
            "input_receipt_ids": [],
            "eligible_for_action": False,
            "action": False,
            "accounting": False,
            "learning": False,
            "reason": reason,
        }

    def _account_balance_receipt(self) -> Optional[Dict[str, Any]]:
        getter = getattr(self.client, "get_account_balance_receipt", None)
        if not callable(getter):
            return None
        try:
            receipt = getter()
        except Exception:
            return None
        if not isinstance(receipt, dict):
            return None
        times = _fresh_receipt_times(receipt)
        receipt_id = _identifier(receipt.get("receipt_id"))
        source_id = str(receipt.get("source_id") or "").strip()
        raw_inputs = receipt.get("input_receipt_ids")
        inputs = (
            [_identifier(value) for value in raw_inputs]
            if isinstance(raw_inputs, list) else []
        )
        raw_balances = receipt.get("balances")
        exact_balances = receipt.get("balance_text")
        if (
            times is None
            or receipt_id is None
            or not receipt_id.startswith("kraken_balance:")
            or source_id != "kraken:/0/private/Balance+/0/public/Time"
            or str(receipt.get("provider") or "").strip().lower() != "kraken"
            or str(receipt.get("venue") or "").strip().lower() != "kraken"
            or receipt.get("provider_receipt_type") != "Balance+Time"
            or receipt.get("account_scope") != "complete"
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("eligible_for_action") is not True
            or receipt.get("action") is not False
            or receipt.get("accounting") is not False
            or receipt.get("learning") is not False
            or not isinstance(raw_balances, dict)
            or not raw_balances
            or not isinstance(exact_balances, dict)
            or set(exact_balances) != set(raw_balances)
            or not inputs
            or any(value is None for value in inputs)
            or len(inputs) != len(set(inputs))
        ):
            return None
        balances: Dict[str, float] = {}
        for raw_asset, raw_amount in raw_balances.items():
            asset = _canonical_asset(raw_asset)
            amount = _finite(raw_amount, nonnegative=True)
            exact_amount = exact_balances.get(raw_asset)
            try:
                exact_matches = Decimal(str(raw_amount)) == Decimal(str(exact_amount))
            except Exception:
                exact_matches = False
            if (
                not asset
                or amount is None
                or asset in balances
                or not exact_matches
            ):
                return None
            balances[asset] = amount
        source_timestamp, received_at = times
        return {
            **receipt,
            "balances": balances,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "input_receipt_ids": [str(value) for value in inputs],
        }
    
    def get_account(self) -> Dict[str, Any]:
        """Derive account value only from complete balance and quote receipts."""
        balance_receipt = self._account_balance_receipt()
        if balance_receipt is None:
            return self._no_data_account("complete_fresh_kraken_balance_receipt_required")
        balance = balance_receipt["balances"]
        total_usd = 0.0
        cash = balance.get("USD", 0.0)
        input_receipt_ids = [str(balance_receipt["receipt_id"])]
        source_timestamps = [float(balance_receipt["source_timestamp"])]
        received_times = [float(balance_receipt["received_at"])]
        for asset in sorted(balance):
            amount = balance[asset]
            if amount <= 0.0:
                continue
            if asset == "USD":
                total_usd += amount
                continue
            ticker = self.get_ticker(f"{asset}/USD")
            if ticker is None:
                return self._no_data_account(
                    f"complete_fresh_kraken_{asset.lower()}usd_ticker_receipt_required"
                )
            total_usd += amount * float(ticker["price"])
            ticker_receipt_id = str(ticker["receipt_id"])
            if ticker_receipt_id in input_receipt_ids:
                return self._no_data_account(
                    "unique_same_venue_ticker_receipts_required"
                )
            input_receipt_ids.append(ticker_receipt_id)
            source_timestamps.append(float(ticker["source_timestamp"]))
            received_times.append(float(ticker["received_at"]))

        receipt_payload = {
            "currency": "USD",
            "balances": balance,
            "cash": cash,
            "equity": total_usd,
            "input_receipt_ids": input_receipt_ids,
        }
        return {
            "cash": cash,
            "equity": total_usd,
            "buying_power": cash,
            "balances": dict(balance),
            "currency": "USD",
            "account_scope": "complete",
            "status": "ACTIVE",
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
            "source_id": "aureon:kraken-trading-adapter:account:v1",
            "source_timestamp": min(source_timestamps),
            "received_at": max(received_times),
            "receipt_id": _derived_receipt_id("account", receipt_payload),
            "input_receipt_ids": input_receipt_ids,
            "eligible_for_action": False,
            "action": False,
            "accounting": False,
            "learning": False,
        }
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return only a complete fresh provider-observed ticker receipt."""
        getter = getattr(self.client, "get_ticker_receipt", None)
        if not callable(getter):
            return None
        receipt = getter(symbol.replace("/", ""))
        if not isinstance(receipt, dict) or receipt.get("data_status") != "live" or receipt.get("truth_status") != "real_observed" or receipt.get("generated_values") is not False:
            return None
        required = ("bid", "ask", "price", "source_id", "source_timestamp", "received_at", "receipt_id", "input_receipt_ids")
        if any(receipt.get(key) is None for key in required):
            return None
        times = _fresh_receipt_times(receipt)
        bid = _finite(receipt.get("bid"), positive=True)
        ask = _finite(receipt.get("ask"), positive=True)
        last = _finite(receipt.get("price"), positive=True)
        raw_inputs = receipt.get("input_receipt_ids")
        inputs = (
            [_identifier(value) for value in raw_inputs]
            if isinstance(raw_inputs, list) else []
        )
        if (
            bid is None
            or ask is None
            or last is None
            or ask < bid
            or times is None
            or str(receipt.get("provider") or "").strip().lower() != "kraken"
            or str(receipt.get("venue") or "").strip().lower() != "kraken"
            or receipt.get("provider_receipt_type") != "Ticker+Time"
            or str(receipt.get("source_id") or "") != "kraken:/0/public/Ticker+/0/public/Time"
            or not str(receipt.get("receipt_id") or "").startswith("kraken_ticker:")
            or receipt.get("action") is not False
            or receipt.get("accounting") is not False
            or receipt.get("learning") is not False
            or not inputs
            or any(value is None for value in inputs)
            or len(inputs) != len(set(inputs))
            or _canonical_pair(receipt.get("symbol")) != _canonical_pair(symbol)
        ):
            return None
        source_timestamp, received_at = times
        return {**receipt, "symbol": symbol, "bid": bid, "ask": ask, "price": last, "last": last, "source_timestamp": source_timestamp, "received_at": received_at, "input_receipt_ids": [str(value) for value in inputs], "action": False, "accounting": False, "learning": False}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Return only holdings with fresh valuation and receipted cost basis."""
        balance_receipt = self._account_balance_receipt()
        if balance_receipt is None:
            return []
        balance = balance_receipt["balances"]
        positions: List[Dict[str, Any]] = []
        for asset in sorted(balance):
            amount = balance[asset]
            if asset in self.STABLECOINS or amount <= 0.0:
                continue

            symbol = f"{asset}/USD"
            ticker = self.get_ticker(symbol)
            if ticker is None:
                return []
            current_price = _finite(ticker.get("price"), positive=True)
            tracked = self.tracked_positions.get(asset)
            if not isinstance(tracked, dict):
                return []

            entry_price = _finite(tracked.get("entry_price"), positive=True)
            entry_time = _finite(tracked.get("entry_time"), positive=True)
            entry_qty = _finite(tracked.get("entry_qty"), positive=True)
            entry_cost = _finite(tracked.get("entry_cost"), positive=True)
            entry_fee = _finite(tracked.get("entry_fee"), nonnegative=True)
            entry_received_at = _finite(tracked.get("received_at"), positive=True)
            entry_fee_currency = str(
                tracked.get("entry_fee_currency") or ""
            ).strip().upper()
            entry_order_id = _identifier(tracked.get("entry_order_id"))
            entry_receipt_id = _identifier(tracked.get("entry_receipt_id"))
            entry_source_id = _identifier(tracked.get("source_id"))
            raw_trade_ids = tracked.get("entry_trade_ids")
            entry_trade_ids = (
                [_identifier(value) for value in raw_trade_ids]
                if isinstance(raw_trade_ids, list) else []
            )
            expected_cost = (
                entry_price * entry_qty
                if entry_price is not None and entry_qty is not None else None
            )
            if (
                current_price is None
                or entry_price is None
                or entry_time is None
                or entry_qty is None
                or entry_cost is None
                or entry_fee is None
                or entry_received_at is None
                or entry_fee_currency != "USD"
                or entry_order_id is None
                or entry_receipt_id is None
                or not entry_receipt_id.startswith(
                    "kraken_adapter_terminal_order:"
                )
                or entry_source_id is None
                or not entry_source_id.startswith("kraken:/0/private/")
                or not entry_trade_ids
                or any(value is None for value in entry_trade_ids)
                or len(entry_trade_ids) != len(set(entry_trade_ids))
                or tracked.get("truth_status") != "real_observed"
                or tracked.get("generated_values") is not False
                or not math.isclose(amount, entry_qty, rel_tol=1e-12, abs_tol=1e-12)
                or expected_cost is None
                or not math.isclose(entry_cost, expected_cost, rel_tol=0.001, abs_tol=1e-8)
                or entry_time > entry_received_at + 5.0
            ):
                return []

            market_value = amount * current_price
            unrealized_pl = (current_price - entry_price) * amount
            unrealized_plpc = (current_price - entry_price) / entry_price
            input_receipt_ids = [
                str(balance_receipt["receipt_id"]),
                str(ticker["receipt_id"]),
                entry_receipt_id,
            ]
            if len(input_receipt_ids) != len(set(input_receipt_ids)):
                return []
            receipt_payload = {
                "asset": asset,
                "quantity": amount,
                "entry_price": entry_price,
                "current_price": current_price,
                "input_receipt_ids": input_receipt_ids,
            }
            positions.append({
                "symbol": symbol,
                "asset": asset,
                "qty": amount,
                "avg_entry_price": entry_price,
                "entry_cost": entry_cost,
                "entry_fee": entry_fee,
                "entry_fee_currency": entry_fee_currency,
                "entry_order_id": entry_order_id,
                "entry_trade_ids": [str(value) for value in entry_trade_ids],
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pl": unrealized_pl,
                "unrealized_plpc": unrealized_plpc,
                "data_status": "live",
                "truth_status": "real_derived",
                "generated_values": False,
                "source_id": "aureon:kraken-trading-adapter:position:v1",
                "source_timestamp": min(
                    float(balance_receipt["source_timestamp"]),
                    float(ticker["source_timestamp"]),
                ),
                "received_at": max(
                    float(balance_receipt["received_at"]),
                    float(ticker["received_at"]),
                ),
                "receipt_id": _derived_receipt_id("position", receipt_payload),
                "input_receipt_ids": input_receipt_ids,
                "eligible_for_action": False,
                "action": False,
                "accounting": False,
                "learning": False,
            })
        return positions
    
    def place_order(self, symbol: str, qty: float, side: str, type: str = "market", time_in_force: str = "gtc", **kwargs) -> Optional[Dict[str, Any]]:
        """Submit once, then require a separate strict terminal status receipt."""
        normalized_side = str(side or "").strip().lower()
        normalized_type = str(type or "").strip().lower()
        quantity = _finite(qty, positive=True)
        if normalized_side not in {"buy", "sell"} or normalized_type not in {"market", "limit"} or quantity is None:
            return _pending_receipt(None, "finite_quantity_side_and_order_type_required")
        key = (symbol, normalized_side, normalized_type, format(quantity, ".16g"))
        pending = getattr(self, "_pending_orders", None)
        if not isinstance(pending, dict):
            pending = {}
            self._pending_orders = pending
        if key in pending:
            raw_state = pending[key]
            if isinstance(raw_state, str):
                raw_state = {
                    "order_id": None if raw_state == "__ambiguous__" else raw_state,
                    "ack_receipt_id": None,
                    "readback_attempted": raw_state == "__ambiguous__",
                }
                pending[key] = raw_state
            order_id = _identifier(raw_state.get("order_id"))
            ack_receipt_id = _identifier(raw_state.get("ack_receipt_id"))
            lineage = [ack_receipt_id] if ack_receipt_id else []
            if order_id is None:
                return _pending_receipt(
                    None,
                    "ambiguous_submission_requires_external_reconciliation",
                    input_receipt_ids=lineage,
                )
            if raw_state.get("readback_attempted") is True:
                return _pending_receipt(
                    order_id,
                    "single_provider_readback_exhausted_external_reconciliation_required",
                    input_receipt_ids=lineage,
                )
            raw_state["readback_attempted"] = True
            try:
                receipt = self.client.get_order_status(order_id)
            except Exception:
                receipt = None
            readback_receipt_id = (
                _identifier(receipt.get("receipt_id"))
                if isinstance(receipt, dict) else None
            )
            if readback_receipt_id:
                lineage.append(readback_receipt_id)
            terminal = _terminal_receipt(
                receipt,
                order_id=order_id,
                symbol=symbol,
                side=normalized_side,
                expected_quantity=quantity,
            )
            if terminal is None:
                return _pending_receipt(
                    order_id,
                    "terminal_provider_receipt_pending_or_incomplete",
                    input_receipt_ids=lineage,
                )
            if ack_receipt_id is None:
                return _pending_receipt(
                    order_id,
                    "complete_submission_ack_receipt_required",
                    input_receipt_ids=lineage,
                )

            provider_receipt_id = str(terminal["receipt_id"])
            terminal_inputs = terminal.get("input_receipt_ids")
            adapter_inputs: List[str] = []
            for value in [
                ack_receipt_id,
                provider_receipt_id,
                *(terminal_inputs if isinstance(terminal_inputs, list) else []),
            ]:
                normalized_id = _identifier(value)
                if normalized_id is not None and normalized_id not in adapter_inputs:
                    adapter_inputs.append(normalized_id)
            adapter_payload = {
                "order_id": order_id,
                "symbol": _canonical_pair(symbol),
                "side": normalized_side,
                "filled_qty": str(terminal["filled_qty"]),
                "filled_avg_price": str(terminal["filled_avg_price"]),
                "filled_notional": str(terminal["filled_notional"]),
                "fee": str(terminal["fee"]),
                "fee_currency": str(terminal["fee_currency"]),
                "input_receipt_ids": adapter_inputs,
            }
            adapter_receipt_id = _derived_receipt_id(
                "terminal_order", adapter_payload
            )
            adapter_terminal = {
                **terminal,
                "id": order_id,
                "symbol": symbol,
                "provider_receipt_id": provider_receipt_id,
                "receipt_id": adapter_receipt_id,
                "input_receipt_ids": adapter_inputs,
                "action": False,
                "accounting": True,
                "learning": True,
            }
            pending.pop(key, None)
            asset = _pair_assets(symbol)[0]
            trade_ids = [str(row["tradeId"]) for row in terminal["fills"]]
            if normalized_side == "buy":
                self.tracked_positions[asset] = {
                    "entry_price": float(terminal["filled_avg_price"]),
                    "entry_time": float(terminal["source_timestamp"]),
                    "entry_qty": float(terminal["filled_qty"]),
                    "entry_cost": float(terminal["filled_notional"]),
                    "entry_fee": float(terminal["fee"]),
                    "entry_fee_currency": str(terminal["fee_currency"]),
                    "entry_order_id": str(terminal["orderId"]),
                    "entry_trade_ids": trade_ids,
                    "entry_receipt_id": adapter_receipt_id,
                    "entry_provider_receipt_id": provider_receipt_id,
                    "entry_input_receipt_ids": adapter_inputs,
                    "source_id": str(terminal["source_id"]),
                    "source_timestamp": float(terminal["source_timestamp"]),
                    "received_at": float(terminal["received_at"]),
                    "truth_status": "real_observed",
                    "generated_values": False,
                }
            else:
                self.tracked_positions.pop(asset, None)
            self._save_positions()
            return adapter_terminal
        pair = symbol.replace("/", "")
        try:
            if normalized_type == "market":
                ack = self.client.place_market_order(symbol=pair, side=normalized_side, quantity=quantity)
            else:
                price = kwargs.get("limit_price") or kwargs.get("price")
                limit_price = _finite(price, positive=True)
                if limit_price is None:
                    return _pending_receipt(None, "finite_limit_price_required")
                ack = self.client.place_limit_order(
                    symbol=pair,
                    side=normalized_side,
                    quantity=quantity,
                    price=limit_price,
                )
        except Exception:
            pending[key] = {
                "order_id": None,
                "ack_receipt_id": None,
                "readback_attempted": True,
            }
            return _pending_receipt(
                None,
                "submission_outcome_ambiguous_external_reconciliation_required",
            )
        if isinstance(ack, dict) and ack.get("data_status") == "not_submitted":
            return {
                **_pending_receipt(None, "dry_run_order_not_submitted"),
                "status": "not_submitted",
                "data_status": "not_submitted",
            }
        order_id = _identifier(ack.get("orderId")) if isinstance(ack, dict) else None
        ack_receipt_id = _identifier(ack.get("receipt_id")) if isinstance(ack, dict) else None
        if not order_id:
            pending[key] = {
                "order_id": None,
                "ack_receipt_id": ack_receipt_id,
                "readback_attempted": True,
            }
            return _pending_receipt(
                None,
                "ambiguous_submission_requires_external_reconciliation",
                input_receipt_ids=[ack_receipt_id] if ack_receipt_id else [],
            )
        ack_received_at = (
            _finite(ack.get("received_at"), positive=True)
            if isinstance(ack, dict) else None
        )
        ack_requested_qty = (
            _finite(ack.get("requestedQty"), positive=True)
            if isinstance(ack, dict) else None
        )
        ack_inputs = ack.get("input_receipt_ids") if isinstance(ack, dict) else None
        ack_complete = (
            isinstance(ack, dict)
            and ack.get("status") == "pending_reconciliation"
            and ack.get("data_status") == "pending_reconciliation"
            and ack.get("truth_status") == "real_observed"
            and ack.get("generated_values") is False
            and ack.get("submitted") is True
            and ack.get("reconciliation_required") is True
            and ack.get("fill_receipt_complete") is False
            and ack.get("eligible_for_accounting") is False
            and ack.get("eligible_for_learning") is False
            and _canonical_pair(ack.get("symbol")) == _canonical_pair(symbol)
            and str(ack.get("side") or "").strip().lower() == normalized_side
            and str(ack.get("type") or "").strip().lower() == normalized_type
            and ack_requested_qty is not None
            and math.isclose(
                ack_requested_qty, quantity, rel_tol=1e-12, abs_tol=1e-12
            )
            and ack_received_at is not None
            and ack_received_at <= time.time() + 5.0
            and time.time() - ack_received_at <= MAX_RECEIPT_AGE_SECONDS
            and ack.get("filled_qty") is None
            and ack.get("filled_avg_price") is None
            and ack.get("filled_notional") is None
            and ack.get("fee") is None
            and ack.get("fills") is None
            and ack_inputs == []
            and str(ack.get("provider") or "").strip().lower() == "kraken"
            and str(ack.get("venue") or "").strip().lower() == "kraken"
            and ack.get("provider_receipt_type") == "AddOrder"
            and str(ack.get("source_id") or "").startswith(
                "kraken:/0/private/AddOrder:"
            )
            and str(ack.get("source_id") or "").endswith(f":{order_id}")
            and ack_receipt_id is not None
            and ack_receipt_id.startswith("kraken_order_ack:")
        )
        pending[key] = {
            "order_id": order_id,
            "ack_receipt_id": ack_receipt_id if ack_complete else None,
            "readback_attempted": False,
        }
        return _pending_receipt(
            order_id,
            (
                "submission_acknowledged_terminal_receipt_required"
                if ack_complete else "submission_ack_receipt_incomplete"
            ),
            input_receipt_ids=[ack_receipt_id] if ack_complete else [],
        )

    def get_available_cash(self) -> Optional[float]:
        """Return observed USD only; never assume stablecoin/USD parity."""
        receipt = self._account_balance_receipt()
        if receipt is None or "USD" not in receipt["balances"]:
            return None
        return float(receipt["balances"]["USD"])


def main():
    """Test the adapter."""
    adapter = KrakenTradingAdapter()
    
    print("=" * 70)
    print("🦑 KRAKEN TRADING ADAPTER TEST")
    print("=" * 70)
    
    # Test account
    print("\n📊 ACCOUNT:")
    account = adapter.get_account()
    print(f"   Cash: ${float(account['cash']):.2f}")
    print(f"   Equity: ${float(account['equity']):.2f}")
    
    # Test positions
    print("\n📈 POSITIONS:")
    positions = adapter.get_positions()
    for pos in positions:
        print(f"   {pos['symbol']}: {pos['qty']:.6f} @ ${pos['current_price']:.2f}")
        print(f"      P&L: ${pos['unrealized_pl']:.4f} ({pos['unrealized_plpc']*100:.2f}%)")
    
    # Test ticker
    print("\n💹 TICKER (SOL/USD):")
    ticker = adapter.get_ticker("SOL/USD")
    if ticker:
        print(f"   Bid: ${ticker['bid']:.2f}")
        print(f"   Ask: ${ticker['ask']:.2f}")
        print(f"   Last: ${ticker['price']:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ Adapter ready for trading!")
    print("=" * 70)


if __name__ == "__main__":
    main()
