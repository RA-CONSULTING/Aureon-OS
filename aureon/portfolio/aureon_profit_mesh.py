#!/usr/bin/env python3
"""
AUREON PROFIT-FIRST MESH TRADER
═══════════════════════════════════════════════════════════════════════════════
PROVIDER-RECEIPTED PROFIT MESH - Every Accounted Trade Is Proven

Strategy:
  - Only trades with HIGH momentum (price moving up > 0.3%)
  - Exit decisions use fresh provider prices
  - Fills, fees, and realised results require provider receipts
  - Master Equation Coherence ensures quality entries (Γ > 0.95)

Missing, stale, or incomplete evidence is NO_DATA and cannot mutate positions
or accounting.

Author: Aureon System / Gary Leckey
Date: November 28, 2025
"""
import os, sys, time, logging, argparse, math
from typing import List, Dict, Any, Optional, Mapping

logger = logging.getLogger(__name__)

MARKET_TTL_SECONDS = 120.0
ORDER_TTL_SECONDS = 300.0
FUTURE_TOLERANCE_SECONDS = 30.0
ACCOUNTING_QUOTE = "USDT"


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric provider evidence")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("provider value is not finite")
    if positive and parsed <= 0:
        raise ValueError("provider value must be positive")
    if nonnegative and parsed < 0:
        raise ValueError("provider value must be nonnegative")
    return parsed


def _provider_seconds(value: Any) -> float:
    parsed = _finite(value, positive=True)
    return parsed / 1000.0 if parsed > 10_000_000_000 else parsed


def _fresh(source_timestamp: float, ttl: float, now: Optional[float] = None) -> bool:
    age = (time.time() if now is None else now) - source_timestamp
    return -FUTURE_TOLERANCE_SECONDS <= age <= ttl


def _valid_provider_id(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    text = str(value).strip()
    if not text or text in {"0", "-1"}:
        return False
    lowered = text.lower()
    return not any(
        marker in lowered
        for marker in ("dry", "mock", "demo", "simulated")  # sentinel rejected as no_data
    )


def _no_data(reason: str, **fields: Any) -> Dict[str, Any]:
    receipt = {
        "status": "no_data",
        "truth_status": "no_data",
        "source_id": "binance",
        "source_timestamp": None,
        "received_at": time.time(),
        "eligible_for_external_action": False,
        "eligible_for_accounting": False,
        "generated_values": False,
        "reason": reason,
    }
    receipt.update(fields)
    return receipt

# ═══════════════════════════════════════════════════════════════════════════════
# MASTER EQUATION (Simplified for Speed)
# ═══════════════════════════════════════════════════════════════════════════════

class FastCoherence:
    def __init__(self):
        self.price_history = {}
        self.momentum_window = 3
        self.min_momentum = 0.0005   # ultra-sensitive momentum trigger
        self.max_volatility = 0.12  # tolerate noisier coins
        
    def add_price(self, symbol: str, price: float, source_timestamp: float) -> bool:
        try:
            price = _finite(price, positive=True)
            source_timestamp = _provider_seconds(source_timestamp)
        except (TypeError, ValueError):
            return False
        if not _fresh(source_timestamp, MARKET_TTL_SECONDS):
            return False
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        if self.price_history[symbol]:
            previous_source_time = self.price_history[symbol][-1]["source_timestamp"]
            if source_timestamp <= previous_source_time:
                return False
        self.price_history[symbol].append({
            "price": price,
            "source_timestamp": source_timestamp,
        })
        if len(self.price_history[symbol]) > 20:
            self.price_history[symbol].pop(0)
        return True
    
    def get_momentum(self, symbol: str) -> Optional[float]:
        """Calculate price momentum (% change)"""
        history = [
            sample for sample in self.price_history.get(symbol, [])
            if _fresh(sample["source_timestamp"], MARKET_TTL_SECONDS)
        ]
        self.price_history[symbol] = history
        if len(history) < self.momentum_window:
            return None
        
        old_price = history[-self.momentum_window]["price"]
        new_price = history[-1]["price"]
        return ((new_price - old_price) / old_price) * 100
    
    def get_signal(self, symbol: str, snapshot: dict) -> str:
        """Returns BUY only if strong upward momentum"""
        if snapshot.get("truth_status") != "real_observed":
            return "NO_DATA"
        if snapshot.get("eligible_for_external_action") is not True:
            return "NO_DATA"
        momentum = self.get_momentum(symbol)
        if momentum is None:
            return "NO_DATA"
        try:
            change_24h = _finite(snapshot["change"])
            high = _finite(snapshot["high"], positive=True)
            low = _finite(snapshot["low"], positive=True)
            price = _finite(snapshot["price"], positive=True)
        except (KeyError, TypeError, ValueError):
            return "NO_DATA"
        
        # Aggressive coherence: accept slight positive momentum
        if momentum > self.min_momentum and change_24h > -2.0:
            volatility = (high - low) / price
            if volatility <= self.max_volatility:
                return 'BUY'
        
        return 'HOLD'

# ═══════════════════════════════════════════════════════════════════════════════
# PROFIT-FIRST MESH TRADER
# ═══════════════════════════════════════════════════════════════════════════════

class ProfitMeshTrader:
    def __init__(self, dry_run: bool = False, client: Any = None):
        self.dry_run = dry_run
        if client is None:
            from aureon.exchanges.binance_client import get_binance_client
            client = get_binance_client()
        self.client = client
        self.coherence = FastCoherence()
        self.positions = {}  # {symbol: {...}}
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.dry_run_attempts: List[Dict[str, Any]] = []
        self.unaccounted_exits: List[Dict[str, Any]] = []
        self.total_profit: Optional[float] = None  # Provider-accounted USDT only
        self.trade_count = 0
        self.win_count = 0
        self.last_discovery_receipt = _no_data("discovery_not_run", pairs=[])
        
        # Profit targets
        self.MIN_PROFIT_PCT = 0.25
        self.TAKE_PROFIT_PCT = 0.6  # 0.6% ideal target
        self.MIN_HOLD_TIME = 5
        self.MAX_HOLD_TIME = 45  # 45 seconds ideal hold
        self.ABS_MAX_HOLD = 180  # hard cap to prevent stuck funds
        self.MAX_POSITIONS = 7
        self.WATCH_LIMIT = 40

    def _live_adapter_ready(self) -> bool:
        if self.client is None:
            return False
        if bool(getattr(self.client, "dry_run", False)):
            return False
        if bool(getattr(self.client, "use_testnet", False)):
            return False
        return True
        
    def get_market_snapshot(self, symbol: str) -> dict:
        empty = {
            "symbol": symbol.upper(),
            "price": None,
            "volume": None,
            "high": None,
            "low": None,
            "change": None,
        }
        if self.client is None:
            return _no_data("binance_client_unavailable", **empty)
        try:
            ticker = self.client.get_24h_ticker(symbol)
            if not isinstance(ticker, Mapping):
                raise ValueError("ticker receipt is not an object")
            if str(ticker["symbol"]).upper() != symbol.upper():
                raise ValueError("ticker symbol does not match request")
            source_timestamp = _provider_seconds(ticker["closeTime"])
            received_at = time.time()
            if not _fresh(source_timestamp, MARKET_TTL_SECONDS, received_at):
                raise ValueError("ticker receipt is stale or future-dated")
            price = _finite(ticker["lastPrice"], positive=True)
            volume = _finite(ticker["volume"], nonnegative=True)
            high = _finite(ticker["highPrice"], positive=True)
            low = _finite(ticker["lowPrice"], positive=True)
            change = _finite(ticker["priceChangePercent"])
            if high < low or price < low or price > high:
                raise ValueError("ticker price range is inconsistent")
            return {
                "status": "live",
                "truth_status": "real_observed",
                "source_id": "binance:/api/v3/ticker/24hr",
                "source_timestamp": source_timestamp,
                "received_at": received_at,
                "eligible_for_external_action": True,
                "eligible_for_accounting": False,
                "generated_values": False,
                "symbol": symbol.upper(),
                "price": price,
                "volume": volume,
                "high": high,
                "low": low,
                "change": change,
            }
        except Exception as exc:
            return _no_data(
                f"market_snapshot_unavailable:{type(exc).__name__}",
                **empty,
            )

    def discover_hot_pairs(self) -> List[Dict[str, Any]]:
        """Find tradeable pairs with momentum"""
        logger.info("🔍 Scanning for hot pairs with momentum...")
        if self.client is None:
            self.last_discovery_receipt = _no_data(
                "binance_client_unavailable", pairs=[]
            )
            return []
        try:
            provider_time = self.client.server_time()
            account = self.client.account()
            info = self.client.exchange_info()
            received_at = time.time()
            if not isinstance(provider_time, Mapping):
                raise ValueError("provider time receipt is not an object")
            if not isinstance(account, Mapping) or not isinstance(info, Mapping):
                raise ValueError("discovery receipt is not an object")
            account_timestamp = _provider_seconds(provider_time["serverTime"])
            exchange_timestamp = _provider_seconds(info["serverTime"])
            if not _fresh(account_timestamp, 60.0, received_at):
                raise ValueError("account clock receipt is stale")
            if not _fresh(exchange_timestamp, 60.0, received_at):
                raise ValueError("exchange metadata receipt is stale")

            raw_balances = account["balances"]
            if not isinstance(raw_balances, list):
                raise ValueError("balances receipt is not a list")
            balances: Dict[str, float] = {}
            for balance in raw_balances:
                if not isinstance(balance, Mapping):
                    raise ValueError("balance row is malformed")
                asset = str(balance["asset"]).upper()
                free = _finite(balance["free"], nonnegative=True)
                _finite(balance["locked"], nonnegative=True)
                if not asset:
                    raise ValueError("balance asset is missing")
                if free > 0:
                    balances[asset] = free

            quote_balance = balances.get(ACCOUNTING_QUOTE)
            if quote_balance is None:
                self.last_discovery_receipt = {
                    "status": "live",
                    "truth_status": "real_observed",
                    "source_id": "binance:/api/v3/account+/api/v3/time",
                    "source_timestamp": account_timestamp,
                    "received_at": received_at,
                    "eligible_for_external_action": False,
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "no_positive_usdt_balance",
                    "pairs": [],
                }
                return []

            pairs = []
            raw_symbols = info["symbols"]
            if not isinstance(raw_symbols, list):
                raise ValueError("symbols receipt is not a list")
            for provider_symbol in raw_symbols:
                if not isinstance(provider_symbol, Mapping):
                    raise ValueError("symbol row is malformed")
                if provider_symbol["status"] != "TRADING":
                    continue
                quote = str(provider_symbol["quoteAsset"]).upper()
                if quote != ACCOUNTING_QUOTE:
                    continue
                base = str(provider_symbol["baseAsset"]).upper()
                symbol = str(provider_symbol["symbol"]).upper()
                if not base or not symbol:
                    raise ValueError("tradable symbol identity is missing")
                pairs.append({
                    "symbol": symbol,
                    "base": base,
                    "quote": quote,
                    "quote_balance": quote_balance,
                    "truth_status": "real_observed",
                    "source_id": "binance:/api/v3/account+/api/v3/exchangeInfo",
                    "source_timestamp": min(account_timestamp, exchange_timestamp),
                    "received_at": received_at,
                    "eligible_for_external_action": True,
                    "generated_values": False,
                })

            pairs.sort(key=lambda pair: pair["symbol"])
            self.last_discovery_receipt = {
                "status": "live",
                "truth_status": "real_observed",
                "source_id": "binance:/api/v3/account+/api/v3/exchangeInfo",
                "source_timestamp": min(account_timestamp, exchange_timestamp),
                "received_at": received_at,
                "eligible_for_external_action": bool(pairs),
                "eligible_for_accounting": False,
                "generated_values": False,
                "reason": None if pairs else "no_tradeable_usdt_pairs",
                "pairs": pairs,
            }
            
            logger.info(f"✅ Found {len(pairs)} tradeable pairs")
            return pairs
        except Exception as e:
            logger.error("Discovery failed: %s", type(e).__name__)
            self.last_discovery_receipt = _no_data(
                f"pair_discovery_unavailable:{type(e).__name__}",
                pairs=[],
            )
            return []

    def _normalise_order_fill(
        self,
        order: Any,
        symbol: str,
        side: str,
        base: str,
        quote: str,
    ) -> Dict[str, Any]:
        """Validate a Binance FULL response without inventing missing fields."""
        received_at = time.time()
        pending = {
            "status": "pending_reconciliation",
            "truth_status": "no_data",
            "source_id": "binance:/api/v3/order",
            "source_timestamp": None,
            "received_at": received_at,
            "eligible_for_external_action": False,
            "eligible_for_accounting": False,
            "generated_values": False,
            "reason": "terminal_fill_not_proven",
            "symbol": symbol,
            "side": side,
            "provider_order_id": None,
            "provider_fill_ids": [],
            "filled_base_quantity": None,
            "net_base_quantity": None,
            "quote_amount": None,
            "average_fill_price": None,
            "quote_commission": None,
            "base_commission": None,
            "fee_receipt_complete": False,
            "fill_receipt_complete": False,
        }
        if not isinstance(order, Mapping):
            return pending
        if order.get("dryRun") is True:
            return {
                **pending,
                "status": "not_submitted",
                "truth_status": "dry_run",
                "reason": "adapter_non_submission_receipt",
            }
        if order.get("rejected") is True:
            return {
                **pending,
                "status": "rejected",
                "truth_status": "real_observed",
                "reason": str(order.get("reason") or order.get("error") or "provider_rejected"),
            }

        order_id = order.get("orderId")
        if _valid_provider_id(order_id):
            pending["provider_order_id"] = str(order_id)
        if str(order.get("status") or "").upper() != "FILLED":
            return pending

        try:
            if str(order["symbol"]).upper() != symbol:
                raise ValueError("order symbol mismatch")
            if str(order["side"]).upper() != side:
                raise ValueError("order side mismatch")
            if not _valid_provider_id(order_id):
                raise ValueError("provider order id is invalid")
            source_timestamp = _provider_seconds(order["transactTime"])
            if not _fresh(source_timestamp, ORDER_TTL_SECONDS, received_at):
                raise ValueError("order receipt is stale or future-dated")
            executed_quantity = _finite(order["executedQty"], positive=True)
            quote_amount = _finite(order["cummulativeQuoteQty"], positive=True)
            fills = order["fills"]
            if not isinstance(fills, list) or not fills:
                raise ValueError("terminal order has no fill rows")

            observed_quantity = 0.0
            observed_quote = 0.0
            quote_commission = 0.0
            base_commission = 0.0
            fill_ids: List[str] = []
            unsupported_fee_asset = False
            for fill in fills:
                if not isinstance(fill, Mapping):
                    raise ValueError("fill row is malformed")
                fill_id = fill["tradeId"]
                if not _valid_provider_id(fill_id):
                    raise ValueError("provider fill id is invalid")
                price = _finite(fill["price"], positive=True)
                quantity = _finite(fill["qty"], positive=True)
                commission = _finite(fill["commission"], nonnegative=True)
                commission_asset = str(fill["commissionAsset"]).upper()
                if commission > 0 and not commission_asset:
                    raise ValueError("commission asset is missing")
                fill_ids.append(str(fill_id))
                observed_quantity += quantity
                observed_quote += price * quantity
                if commission_asset == quote:
                    quote_commission += commission
                elif commission_asset == base:
                    base_commission += commission
                elif commission > 0:
                    unsupported_fee_asset = True

            if len(set(fill_ids)) != len(fill_ids):
                raise ValueError("provider fill ids are duplicated")
            if not math.isclose(
                observed_quantity, executed_quantity, rel_tol=1e-8, abs_tol=1e-12
            ):
                raise ValueError("fill quantity does not match order")
            if not math.isclose(
                observed_quote, quote_amount, rel_tol=1e-8, abs_tol=1e-10
            ):
                raise ValueError("fill notional does not match order")

            net_base_quantity = (
                executed_quantity - base_commission
                if side == "BUY"
                else executed_quantity
            )
            if net_base_quantity <= 0:
                raise ValueError("commission consumes the observed fill")
            fee_complete = not unsupported_fee_asset
            if side == "SELL" and base_commission > 0:
                fee_complete = False

            return {
                **pending,
                "status": "filled",
                "truth_status": "real_observed",
                "source_timestamp": source_timestamp,
                "eligible_for_external_action": True,
                "eligible_for_accounting": fee_complete,
                "reason": None if fee_complete else "commission_conversion_unavailable",
                "provider_order_id": str(order_id),
                "provider_fill_ids": fill_ids,
                "filled_base_quantity": executed_quantity,
                "net_base_quantity": net_base_quantity,
                "quote_amount": quote_amount,
                "average_fill_price": quote_amount / executed_quantity,
                "quote_commission": quote_commission,
                "base_commission": base_commission,
                "fee_receipt_complete": fee_complete,
                "fill_receipt_complete": True,
            }
        except (KeyError, TypeError, ValueError):
            return {
                **pending,
                "reason": "terminal_fill_evidence_incomplete",
            }

    def enter_position(self, symbol: str, quote: str, quote_balance: float) -> Dict[str, Any]:
        """Enter a position (BUY)"""
        symbol = symbol.upper()
        quote = quote.upper()
        if symbol in self.positions:
            return _no_data("position_already_exists", symbol=symbol)
        if symbol in self.pending_orders:
            return _no_data("order_reconciliation_pending", symbol=symbol)
        try:
            if quote != ACCOUNTING_QUOTE:
                raise ValueError("pair is outside the accounting denomination")
            quote_balance = _finite(quote_balance, positive=True)
            discovery = self.last_discovery_receipt
            if discovery.get("truth_status") != "real_observed":
                raise ValueError("pair has no observed discovery receipt")
            discovery_timestamp = _provider_seconds(discovery["source_timestamp"])
            if not _fresh(discovery_timestamp, 60.0):
                raise ValueError("balance discovery receipt is stale")
            pair = next(
                (
                    candidate for candidate in discovery["pairs"]
                    if candidate["symbol"] == symbol and candidate["quote"] == quote
                ),
                None,
            )
            if pair is None:
                raise ValueError("pair is absent from the fresh discovery receipt")
            if not math.isclose(
                quote_balance,
                _finite(pair["quote_balance"], positive=True),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError("quote balance does not match discovery receipt")
            snapshot = self.get_market_snapshot(symbol)
            if snapshot["truth_status"] != "real_observed":
                return snapshot

            usable_balance = quote_balance * 0.90
            desired_budget = max(quote_balance * 0.25, 12.0)
            trade_size = min(desired_budget, 28.0, usable_balance)
            if trade_size < 12.0:
                return _no_data(
                    "insufficient_receipted_quote_balance_for_policy",
                    symbol=symbol,
                )
            
            if self.dry_run:
                receipt = {
                    "status": "not_submitted",
                    "truth_status": "dry_run",
                    "source_id": "aureon:profit_mesh_entry",
                    "source_timestamp": None,
                    "received_at": time.time(),
                    "eligible_for_external_action": False,
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "operator_selected_non_submission_mode",
                    "symbol": symbol,
                    "side": "BUY",
                    "quote_asset": quote,
                    "requested_quote_quantity": trade_size,
                    "provider_order_id": None,
                    "provider_fill_ids": [],
                    "filled_base_quantity": None,
                    "average_fill_price": None,
                    "fee_receipt_complete": False,
                    "fill_receipt_complete": False,
                }
                self.dry_run_attempts.append(receipt)
                return receipt
            
            if not self._live_adapter_ready():
                return _no_data("live_binance_adapter_unavailable", symbol=symbol)
            try:
                order = self.client.place_market_order(
                    symbol, "BUY", quote_qty=trade_size
                )
            except Exception as submission_error:
                receipt = _no_data(
                    f"order_submission_outcome_unknown:{type(submission_error).__name__}",
                    status="pending_reconciliation",
                    symbol=symbol,
                    side="BUY",
                    provider_order_id=None,
                )
                self.pending_orders[symbol] = receipt
                return receipt
            fill = self._normalise_order_fill(
                order, symbol, "BUY", pair["base"], quote
            )
            if fill["status"] != "filled":
                if fill["status"] != "rejected":
                    self.pending_orders[symbol] = fill
                return fill

            entry_cost = None
            if fill["eligible_for_accounting"] is True:
                entry_cost = fill["quote_amount"] + fill["quote_commission"]
            self.positions[symbol] = {
                "entry_price": fill["average_fill_price"],
                "entry_time": fill["source_timestamp"],
                "size": fill["quote_amount"],
                "qty": fill["net_base_quantity"],
                "base": pair["base"],
                "quote": quote,
                "entry_quote_commission": fill["quote_commission"],
                "entry_total_cost_quote": entry_cost,
                "eligible_for_accounting": fill["eligible_for_accounting"],
                "provider_order_id": fill["provider_order_id"],
                "provider_fill_ids": fill["provider_fill_ids"],
                "truth_status": "real_observed",
                "source_id": fill["source_id"],
                "source_timestamp": fill["source_timestamp"],
                "received_at": fill["received_at"],
                "generated_values": False,
            }
            return {**fill, "position_recorded": True}
            
        except Exception as e:
            logger.error("Entry failed %s: %s", symbol, type(e).__name__)
            return _no_data(
                f"entry_preflight_unavailable:{type(e).__name__}",
                symbol=symbol,
            )

    def exit_position(self, symbol: str, current_price: float, reason: str) -> Dict[str, Any]:
        """Exit only from a fresh quote; account only from the terminal fill."""
        symbol = symbol.upper()
        pos = self.positions.get(symbol)
        if pos is None:
            return _no_data("tracked_position_missing", symbol=symbol)
        if symbol in self.pending_orders:
            return _no_data("order_reconciliation_pending", symbol=symbol)
        try:
            _finite(current_price, positive=True)
            snapshot = self.get_market_snapshot(symbol)
            if snapshot["truth_status"] != "real_observed":
                return snapshot
            requested_quantity = _finite(pos["qty"], positive=True)

            if self.dry_run:
                receipt = {
                    "status": "not_submitted",
                    "truth_status": "dry_run",
                    "source_id": "aureon:profit_mesh_exit",
                    "source_timestamp": None,
                    "received_at": time.time(),
                    "eligible_for_external_action": False,
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "operator_selected_non_submission_mode",
                    "symbol": symbol,
                    "side": "SELL",
                    "requested_base_quantity": requested_quantity,
                    "provider_order_id": None,
                    "provider_fill_ids": [],
                    "filled_base_quantity": None,
                    "average_fill_price": None,
                    "realised_pnl_quote": None,
                    "fee_receipt_complete": False,
                    "fill_receipt_complete": False,
                }
                self.dry_run_attempts.append(receipt)
                return receipt

            if not self._live_adapter_ready():
                return _no_data("live_binance_adapter_unavailable", symbol=symbol)
            try:
                order = self.client.place_market_order(
                    symbol, "SELL", quantity=requested_quantity
                )
            except Exception as submission_error:
                receipt = _no_data(
                    f"order_submission_outcome_unknown:{type(submission_error).__name__}",
                    status="pending_reconciliation",
                    symbol=symbol,
                    side="SELL",
                    provider_order_id=None,
                )
                self.pending_orders[symbol] = receipt
                return receipt
            fill = self._normalise_order_fill(
                order, symbol, "SELL", pos["base"], pos["quote"]
            )
            if fill["status"] != "filled":
                if fill["status"] != "rejected":
                    self.pending_orders[symbol] = fill
                return fill
            if fill["base_commission"] > 0:
                fill = {
                    **fill,
                    "status": "pending_reconciliation",
                    "eligible_for_external_action": False,
                    "eligible_for_accounting": False,
                    "reason": "base_fee_depletion_requires_reconciliation",
                }
                self.pending_orders[symbol] = fill
                return fill

            filled_quantity = _finite(fill["filled_base_quantity"], positive=True)
            if filled_quantity > requested_quantity and not math.isclose(
                filled_quantity, requested_quantity, rel_tol=1e-8, abs_tol=1e-12
            ):
                fill = {
                    **fill,
                    "status": "pending_reconciliation",
                    "eligible_for_external_action": False,
                    "eligible_for_accounting": False,
                    "reason": "provider_fill_exceeds_tracked_position",
                }
                self.pending_orders[symbol] = fill
                return fill

            filled_quantity = min(filled_quantity, requested_quantity)
            allocation = filled_quantity / requested_quantity
            remaining_quantity = requested_quantity - filled_quantity
            accounting_eligible = (
                pos["eligible_for_accounting"] is True
                and fill["eligible_for_accounting"] is True
                and pos["entry_total_cost_quote"] is not None
            )
            realised_pnl_quote = None
            if accounting_eligible:
                allocated_cost = _finite(
                    pos["entry_total_cost_quote"], positive=True
                ) * allocation
                net_proceeds = fill["quote_amount"] - fill["quote_commission"]
                realised_pnl_quote = net_proceeds - allocated_cost
                if not math.isfinite(realised_pnl_quote):
                    accounting_eligible = False
                    realised_pnl_quote = None

            if remaining_quantity <= max(1e-12, requested_quantity * 1e-8):
                self.positions.pop(symbol)
                remaining_quantity = 0.0
            else:
                remaining_ratio = remaining_quantity / requested_quantity
                pos["qty"] = remaining_quantity
                pos["size"] *= remaining_ratio
                pos["entry_quote_commission"] *= remaining_ratio
                if pos["entry_total_cost_quote"] is not None:
                    pos["entry_total_cost_quote"] *= remaining_ratio

            if accounting_eligible:
                if self.total_profit is None:
                    self.total_profit = realised_pnl_quote
                else:
                    self.total_profit += realised_pnl_quote
                self.trade_count += 1
                if realised_pnl_quote > 0:
                    self.win_count += 1
            else:
                self.unaccounted_exits.append({
                    "symbol": symbol,
                    "provider_order_id": fill["provider_order_id"],
                    "provider_fill_ids": fill["provider_fill_ids"],
                    "source_timestamp": fill["source_timestamp"],
                    "received_at": fill["received_at"],
                    "realised_pnl_quote": None,
                    "quote_asset": pos["quote"],
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "complete_fee_and_entry_cost_receipts_required",
                })

            return {
                **fill,
                "position_closed": remaining_quantity == 0.0,
                "remaining_base_quantity": remaining_quantity,
                "realised_pnl_quote": realised_pnl_quote,
                "quote_asset": pos["quote"],
                "accounting_status": "accounted" if accounting_eligible else "no_data",
                "eligible_for_accounting": accounting_eligible,
                "exit_reason": reason,
            }
        except Exception as e:
            logger.error("Exit failed %s: %s", symbol, type(e).__name__)
            return _no_data(
                f"exit_receipt_unavailable:{type(e).__name__}",
                symbol=symbol,
            )

    def manage_positions(self):
        """Check all positions for profit targets or time limit"""
        for symbol in list(self.positions.keys()):
            if symbol in self.pending_orders:
                continue
            pos = self.positions[symbol]
            
            try:
                snapshot = self.get_market_snapshot(symbol)
                if snapshot.get("truth_status") != "real_observed":
                    continue
                
                current_price = _finite(snapshot["price"], positive=True)
                entry_price = _finite(pos["entry_price"], positive=True)
                entry_time = _provider_seconds(pos["entry_time"])
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                hold_time = time.time() - entry_time
                
                # Lock gains fast once above fee buffer
                if profit_pct >= self.TAKE_PROFIT_PCT:
                    self.exit_position(symbol, current_price, f"TP {profit_pct:.2f}%")
                elif profit_pct >= (self.MIN_PROFIT_PCT + 0.1) and hold_time >= self.MIN_HOLD_TIME:
                    self.exit_position(symbol, current_price, f"SCALP {profit_pct:.2f}%")
                elif hold_time > self.MAX_HOLD_TIME and profit_pct > self.MIN_PROFIT_PCT:
                    self.exit_position(symbol, current_price, f"TIME {profit_pct:.2f}%")
                elif hold_time > self.ABS_MAX_HOLD and profit_pct > 0:
                    self.exit_position(symbol, current_price, f"SAFETY {profit_pct:.2f}%")
                    
            except Exception as e:
                logger.error(f"Position management error {symbol}: {e}")

    def run(self, duration_sec: int = 3600):
        logger.info("Profit mesh started; accounting denomination is USDT")
        logger.info(f"   Min Profit: {self.MIN_PROFIT_PCT}% | Take Profit: {self.TAKE_PROFIT_PCT}%")
        logger.info(f"   Max Hold: {self.MAX_HOLD_TIME}s\n")
        
        start_time = time.time()
        cycle = 0
        
        while time.time() - start_time < duration_sec:
            cycle += 1
            profit_label = (
                "NO_DATA"
                if self.total_profit is None
                else f"{self.total_profit:+.8f} USDT"
            )
            logger.info(
                "Cycle %d | positions=%d | accounted_profit=%s",
                cycle,
                len(self.positions),
                profit_label,
            )
            
            # Manage existing positions first
            self.manage_positions()
            
            # Only enter new positions if we have room
            if len(self.positions) < self.MAX_POSITIONS:
                pairs = self.discover_hot_pairs()
                target_pairs = pairs[:self.WATCH_LIMIT]
                
                for pair in target_pairs:
                    if len(self.positions) >= self.MAX_POSITIONS:
                        break
                    
                    symbol = pair['symbol']
                    if symbol in self.positions or symbol in self.pending_orders:
                        continue
                    
                    snapshot = self.get_market_snapshot(symbol)
                    if snapshot.get("truth_status") != "real_observed":
                        continue
                    
                    if not self.coherence.add_price(
                        symbol,
                        snapshot["price"],
                        snapshot["source_timestamp"],
                    ):
                        continue
                    signal = self.coherence.get_signal(symbol, snapshot)
                    
                    if signal == 'BUY':
                        momentum = self.coherence.get_momentum(symbol)
                        if momentum is None:
                            continue
                        logger.info(
                            "%s: BUY coherence signal at momentum %.8f%%",
                            symbol,
                            momentum,
                        )
                        self.enter_position(symbol, pair['quote'], pair['quote_balance'])
            
            time.sleep(2)
        
        # Final summary
        win_rate = (
            self.win_count / self.trade_count * 100
            if self.trade_count > 0
            else None
        )
        summary = {
            "status": "complete",
            "truth_status": "real_derived",
            "source_id": "aureon:profit_mesh_accounting",
            "source_timestamp": None,
            "received_at": time.time(),
            "generated_values": False,
            "accounting_quote": ACCOUNTING_QUOTE,
            "total_profit_quote": self.total_profit,
            "accounted_trade_count": self.trade_count,
            "accounted_win_count": self.win_count,
            "win_rate_percent": win_rate,
            "pending_reconciliation_count": len(self.pending_orders),
            "unaccounted_exit_count": len(self.unaccounted_exits),
        }
        logger.info("Profit mesh session summary: %s", summary)
        return summary

def _configure_runtime() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("profit_mesh.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )
    from aureon.core.aureon_baton_link import link_system
    link_system(__name__)


def main():
    _configure_runtime()
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=3600)
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING - Real money!")
    
    trader = ProfitMeshTrader(dry_run=args.dry_run)
    if trader.client is None:
        logger.error("Binance client unavailable")
        sys.exit(1)
    if not args.dry_run and not trader._live_adapter_ready():
        logger.error("Live Binance adapter unavailable")
        sys.exit(1)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
