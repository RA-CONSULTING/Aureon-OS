#!/usr/bin/env python3
"""Receipt-gated S5 V14 execution.

Import and construction are inert. Market, account, and linked HNC/Auris
receipts must be complete and fresh before submission. An order acknowledgement
is pending only; one later provider read-back may reconcile it. Positions,
accounting, counters, and learning evidence change only for a complete terminal
fill with its observed fee and fee currency.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import signal
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional

MAX_RECEIPT_AGE_SECONDS = 300.0
FUTURE_TOLERANCE_SECONDS = 5.0


def _finite(value: Any, *, positive: bool = False,
            nonnegative: bool = False) -> Optional[float]:
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
    pair = str(value or "").strip().upper().replace("/", "").replace("-", "")
    if pair.startswith("XBT"):
        pair = "BTC" + pair[3:]
    if pair.startswith("XDG"):
        pair = "DOGE" + pair[3:]
    return pair


def _canonical_asset(value: Any) -> str:
    asset = str(value or "").strip().upper()
    return {
        "XXBT": "BTC", "XBT": "BTC", "XXDG": "DOGE", "XDG": "DOGE",
        "ZUSD": "USD",
    }.get(asset, asset)


def _fresh_times(receipt: Mapping[str, Any], now: float
                 ) -> Optional[tuple[float, float]]:
    source_timestamp = _finite(
        receipt.get("source_timestamp", receipt.get("provider_timestamp")),
        positive=True,
    )
    received_at = _finite(receipt.get("received_at"), positive=True)
    if source_timestamp is None or received_at is None:
        return None
    if source_timestamp > received_at + FUTURE_TOLERANCE_SECONDS:
        return None
    if received_at > now + FUTURE_TOLERANCE_SECONDS:
        return None
    if now - source_timestamp > MAX_RECEIPT_AGE_SECONDS:
        return None
    if now - received_at > MAX_RECEIPT_AGE_SECONDS:
        return None
    return source_timestamp, received_at


def _no_data(reason: str, *, status: str = "no_data",
             order_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status": status,
        "data_status": status,
        "truth_status": "no_data",
        "generated_values": False,
        "reason": reason,
        "order_id": order_id,
        "action": False,
        "accounting": False,
        "learning": False,
    }


@dataclass(frozen=True)
class LivePrice:
    symbol: str
    venue_symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    source_id: str
    source_timestamp: float
    received_at: float
    receipt_id: str


@dataclass
class V14Trade:
    symbol: str
    entry_price: float
    quantity: float
    entry_time: datetime
    entry_score: int
    kraken_pair: str
    entry_fee: float
    entry_fee_currency: str
    entry_order_id: str
    entry_trade_ids: tuple[str, ...]
    entry_source_id: str
    entry_source_timestamp: float
    entry_received_at: float
    market_receipt_id: str
    account_receipt_id: str
    gate_receipt_id: str
    current_price: Optional[float] = None
    current_pnl_pct: Optional[float] = None
    status: str = "OPEN"


@dataclass
class PendingOrder:
    intent_key: str
    symbol: str
    kraken_pair: str
    side: str
    requested_quantity: float
    score: int
    order_id: Optional[str]
    market_receipt_id: str
    account_receipt_id: str
    gate_receipt_id: str
    state: str = "pending_reconciliation"


class S5V14LiveEngine:
    STRATEGY_SYMBOLS = (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
        "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
        "ATOMUSDT", "UNIUSDT", "LTCUSDT", "NEARUSDT", "APTUSDT",
        "SHIBUSDT", "PEPEUSDT", "SUIUSDT", "OPUSDT", "ARBUSDT",
    )
    BINANCE_TO_KRAKEN = {
        "BTCUSDT": "XBTUSD", "ETHUSDT": "ETHUSD", "SOLUSDT": "SOLUSD",
        "XRPUSDT": "XRPUSD", "ADAUSDT": "ADAUSD", "DOGEUSDT": "DOGEUSD",
        "AVAXUSDT": "AVAXUSD", "DOTUSDT": "DOTUSD", "LINKUSDT": "LINKUSD",
        "MATICUSDT": "MATICUSD", "ATOMUSDT": "ATOMUSD", "UNIUSDT": "UNIUSD",
        "LTCUSDT": "LTCUSD", "NEARUSDT": "NEARUSD", "APTUSDT": "APTUSD",
        "SHIBUSDT": "SHIBUSD", "PEPEUSDT": "PEPEUSD", "SUIUSDT": "SUIUSD",
        "OPUSDT": "OPUSD", "ARBUSDT": "ARBUSD",
    }
    MAKER_FEE = 0.0016
    TAKER_FEE = 0.0026
    MAX_POSITION_USD = 100.0
    MIN_POSITION_USD = 10.0
    MAX_CONCURRENT_POSITIONS = 5
    MAX_DAILY_TRADES = 50

    # Accepted V14 parameters; score and P&L equations remain unchanged.
    PROFIT_TARGET_PCT = 1.52
    STOP_LOSS_PCT = None
    ENTRY_SCORE_THRESHOLD = 8

    def __init__(
        self,
        starting_capital: float = 10000.0,
        dry_run: bool = True,
        *,
        kraken: Any = None,
        v14: Any = None,
        account_receipt_supplier: Optional[Callable[[], Mapping[str, Any]]] = None,
        hnc_auris_gate_receipt_supplier: Optional[
            Callable[[], Mapping[str, Any]]
        ] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.starting_capital = starting_capital
        self.dry_run = bool(dry_run)
        self.kraken = kraken
        self.v14 = v14
        self.account_receipt_supplier = account_receipt_supplier
        self.hnc_auris_gate_receipt_supplier = hnc_auris_gate_receipt_supplier
        self._clock = clock
        self.prices: Dict[str, LivePrice] = {}
        self.prev_prices: Dict[str, float] = {}
        self.price_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self.positions: Dict[str, V14Trade] = {}
        self.closed_trades: List[Dict[str, Any]] = []
        self.running = False
        self.start_time: Optional[float] = None
        self.daily_entries = 0
        self.last_no_data: Optional[Dict[str, Any]] = None
        self.last_execution: Optional[Dict[str, Any]] = None
        self.stats: Dict[str, Any] = {
            "price_updates": 0,
            "v14_evaluations": 0,
            "entries_approved": 0,
            "entries_rejected": 0,
            "exits_profit_target": 0,
            "real_trades_placed": 0,
            "total_profit": 0.0,
            "realized_pnl_by_currency": {},
            "win_rate": None,
        }
        self._seen_market_receipts: set[str] = set()
        self._latest_market_timestamp: Dict[str, float] = {}
        self._decision_cache: Dict[str, Dict[str, Any]] = {}
        self._pending_orders: Dict[str, PendingOrder] = {}
        self._settled_intents: set[str] = set()
        self._accounted_order_ids: set[str] = set()
        self._accounted_trade_ids: set[str] = set()

    def configure_default_runtime(self) -> "S5V14LiveEngine":
        """Explicitly load native engines and clients without making API calls."""
        if self.v14 is None:
            from aureon.strategies.s5_v14_dance_enhancements import (
                V14DanceEnhancer,
            )
            self.v14 = V14DanceEnhancer()
        if self.kraken is None:
            from aureon.exchanges.kraken_client import get_kraken_client
            self.kraken = get_kraken_client()
        if self.account_receipt_supplier is None:
            supplier = getattr(self.kraken, "get_account_balance_receipt", None)
            if callable(supplier):
                self.account_receipt_supplier = supplier
        return self

    def install_signal_handlers(self) -> None:
        """Install process handlers only for an explicitly started run."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, _signum: int, _frame: Any) -> None:
        self.running = False

    def _record_no_data(
        self,
        reason: str,
        *,
        status: str = "no_data",
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        outcome = _no_data(reason, status=status, order_id=order_id)
        self.last_no_data = outcome
        return outcome

    def _validate_market_receipt(
        self, symbol: str, receipt: Any
    ) -> tuple[Optional[LivePrice], str]:
        if not isinstance(receipt, Mapping):
            return None, "kraken_market_receipt_required"
        times = _fresh_times(receipt, self._clock())
        venue_symbol = self.BINANCE_TO_KRAKEN.get(symbol)
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        price = _finite(receipt.get("price"), positive=True)
        bid = _finite(receipt.get("bid"), positive=True)
        ask = _finite(receipt.get("ask"), positive=True)
        volume = _finite(receipt.get("volume_24h"), nonnegative=True)
        change = _finite(receipt.get("change_pct"))
        if (
            venue_symbol is None
            or times is None
            or not source_id.lower().startswith("kraken:")
            or not receipt_id
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("action") is not False
            or receipt.get("accounting") is not False
            or receipt.get("learning") is not False
            or _canonical_pair(receipt.get("symbol"))
            != _canonical_pair(venue_symbol)
            or price is None
            or bid is None
            or ask is None
            or volume is None
            or change is None
            or ask < bid
        ):
            return None, "complete_fresh_same_venue_market_receipt_required"
        source_timestamp, received_at = times
        return LivePrice(
            symbol=symbol,
            venue_symbol=venue_symbol,
            price=price,
            bid=bid,
            ask=ask,
            volume_24h=volume,
            change_24h=change,
            source_id=source_id,
            source_timestamp=source_timestamp,
            received_at=received_at,
            receipt_id=receipt_id,
        ), ""

    def ingest_market_receipt(
        self, symbol: str, receipt: Any
    ) -> Dict[str, Any]:
        price, reason = self._validate_market_receipt(symbol, receipt)
        if price is None:
            return self._record_no_data(reason)
        if price.receipt_id in self._seen_market_receipts:
            return self._record_no_data("duplicate_market_receipt")
        previous_timestamp = self._latest_market_timestamp.get(symbol)
        if (
            previous_timestamp is not None
            and price.source_timestamp <= previous_timestamp
        ):
            return self._record_no_data("non_monotonic_market_receipt")
        previous = self.prices.get(symbol)
        if previous is not None:
            self.prev_prices[symbol] = previous.price
        self.prices[symbol] = price
        self.price_history[symbol].append(price)
        self._seen_market_receipts.add(price.receipt_id)
        self._latest_market_timestamp[symbol] = price.source_timestamp
        self.stats["price_updates"] += 1
        return {
            "status": "accepted",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "source_id": price.source_id,
            "source_timestamp": price.source_timestamp,
            "received_at": price.received_at,
            "receipt_id": price.receipt_id,
            "action": False,
            "accounting": False,
            "learning": False,
        }

    def _validate_account_receipt(
        self, receipt: Any
    ) -> tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(receipt, Mapping):
            return None, "complete_fresh_kraken_account_receipt_required"
        times = _fresh_times(receipt, self._clock())
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        raw_balances = receipt.get("balances")
        if (
            times is None
            or not source_id.lower().startswith("kraken")
            or not receipt_id
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("account_scope") != "complete"
            or not isinstance(raw_balances, Mapping)
            or not raw_balances
        ):
            return None, "complete_fresh_kraken_account_receipt_required"
        balances: Dict[str, float] = {}
        for raw_asset, raw_amount in raw_balances.items():
            asset = _canonical_asset(raw_asset)
            amount = _finite(raw_amount, nonnegative=True)
            if not asset or amount is None or asset in balances:
                return None, "unambiguous_account_balances_required"
            balances[asset] = amount
        source_timestamp, received_at = times
        return {
            **dict(receipt),
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "balances": balances,
        }, ""

    def _validate_hnc_auris_gate_receipt(
        self,
        receipt: Any,
        *,
        market_receipt_id: str,
        account_receipt_id: str,
    ) -> tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(receipt, Mapping):
            return None, "complete_linked_hnc_auris_gate_receipt_required"
        times = _fresh_times(receipt, self._clock())
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        raw_links = receipt.get("input_receipt_ids")
        links = (
            [str(value).strip() for value in raw_links]
            if isinstance(raw_links, (list, tuple))
            else []
        )
        earth_coherence = _finite(
            receipt.get("earth_coherence"), nonnegative=True
        )
        earth_phase_lock = _finite(
            receipt.get("earth_phase_lock"), nonnegative=True
        )
        earth_phi_boost = _finite(
            receipt.get("earth_phi_boost"), positive=True
        )
        cosmic_coherence = _finite(
            receipt.get("cosmic_coherence"), nonnegative=True
        )
        cosmic_distortion = _finite(
            receipt.get("cosmic_distortion"), nonnegative=True
        )
        cosmic_boost = _finite(receipt.get("cosmic_boost"), positive=True)
        cosmic_joy = _finite(receipt.get("cosmic_joy"))
        cosmic_reciprocity = _finite(receipt.get("cosmic_reciprocity"))
        planetary_torque = _finite(
            receipt.get("planetary_torque"), positive=True
        )
        lunar_phase = _finite(receipt.get("lunar_phase"), nonnegative=True)
        cosmic_phase = str(receipt.get("cosmic_phase") or "").strip()
        values = (
            earth_coherence,
            earth_phase_lock,
            earth_phi_boost,
            cosmic_coherence,
            cosmic_distortion,
            cosmic_boost,
            cosmic_joy,
            cosmic_reciprocity,
            planetary_torque,
            lunar_phase,
        )
        if (
            times is None
            or not source_id
            or not receipt_id
            or receipt.get("truth_status") not in {
                "real_observed", "real_derived"
            }
            or receipt.get("generated_values") is not False
            or receipt.get("eligible_for_action") is not True
            or type(receipt.get("earth_open")) is not bool
            or type(receipt.get("cosmic_open")) is not bool
            or receipt.get("earth_open") is not True
            or receipt.get("cosmic_open") is not True
            or not cosmic_phase
            or len(links) != len(set(links))
            or market_receipt_id not in links
            or account_receipt_id not in links
            or any(value is None for value in values)
            or earth_coherence > 1.0
            or earth_phase_lock > 1.0
            or cosmic_coherence > 1.0
            or lunar_phase > 1.0
        ):
            return None, "complete_linked_hnc_auris_gate_receipt_required"

        # Canonical equation from Aureon's HNC/Auris forecast gate. It gates
        # action but does not alter the V14 score or profit equations.
        combined_multiplier = (
            earth_phi_boost
            * cosmic_boost
            * min(2.0, planetary_torque)
        )
        source_timestamp, received_at = times
        return {
            **dict(receipt),
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": receipt_id,
            "combined_multiplier": combined_multiplier,
        }, ""

    def _evidence_bundle(
        self, symbol: str
    ) -> tuple[Optional[Dict[str, Any]], str]:
        market = self.prices.get(symbol)
        now = self._clock()
        if (
            market is None
            or now - market.source_timestamp > MAX_RECEIPT_AGE_SECONDS
            or now - market.received_at > MAX_RECEIPT_AGE_SECONDS
        ):
            return None, "complete_fresh_same_venue_market_receipt_required"
        if not callable(self.account_receipt_supplier):
            return None, "kraken_account_receipt_adapter_unavailable"
        try:
            raw_account = self.account_receipt_supplier()
        except Exception:
            return None, "kraken_account_receipt_unavailable"
        account, reason = self._validate_account_receipt(raw_account)
        if account is None:
            return None, reason
        if not callable(self.hnc_auris_gate_receipt_supplier):
            return None, "hnc_auris_gate_receipt_supplier_unavailable"
        try:
            raw_gate = self.hnc_auris_gate_receipt_supplier()
        except Exception:
            return None, "hnc_auris_gate_receipt_unavailable"
        gate, reason = self._validate_hnc_auris_gate_receipt(
            raw_gate,
            market_receipt_id=market.receipt_id,
            account_receipt_id=str(account["receipt_id"]),
        )
        if gate is None:
            return None, reason
        return {"market": market, "account": account, "gate": gate}, ""

    def _score_entry(
        self, symbol: str, market: LivePrice
    ) -> tuple[Optional[Dict[str, Any]], str]:
        cached = self._decision_cache.get(market.receipt_id)
        if cached is not None:
            return dict(cached), ""
        scoring_engine = getattr(self.v14, "scoring_engine", None)
        score_entry = getattr(scoring_engine, "score_entry", None)
        should_enter = getattr(scoring_engine, "should_enter", None)
        if not callable(score_entry) or not callable(should_enter):
            return None, "v14_scoring_engine_unavailable"
        try:
            score = score_entry(symbol, market.price, market.volume_24h)
            total_number = _finite(
                getattr(score, "total_score", None), nonnegative=True
            )
            decision = bool(should_enter(score))
        except Exception:
            return None, "v14_scoring_failed"
        if total_number is None or not total_number.is_integer():
            return None, "v14_score_invalid"
        result = {
            "score": int(total_number),
            "should_enter": decision,
            "market_receipt_id": market.receipt_id,
        }
        self._decision_cache[market.receipt_id] = dict(result)
        return result, ""

    @staticmethod
    def _pair_assets(pair: str) -> tuple[Optional[str], Optional[str]]:
        canonical = _canonical_pair(pair)
        for quote in ("USDT", "USDC", "USD", "EUR", "GBP"):
            if canonical.endswith(quote) and len(canonical) > len(quote):
                return canonical[: -len(quote)], quote
        return None, None

    def _account_has_capacity(
        self,
        account: Mapping[str, Any],
        *,
        pair: str,
        side: str,
        quantity: float,
        price: float,
    ) -> tuple[bool, str]:
        base, quote = self._pair_assets(pair)
        balances = account.get("balances")
        if base is None or quote is None or not isinstance(balances, Mapping):
            return False, "unambiguous_pair_and_account_balances_required"
        if side == "buy":
            available = _finite(balances.get(quote), nonnegative=True)
            required = quantity * price * (1.0 + self.TAKER_FEE)
            if available is None or available < required:
                return False, "fresh_quote_balance_does_not_cover_entry"
        else:
            available = _finite(balances.get(base), nonnegative=True)
            if available is None or available < quantity:
                return False, "fresh_base_balance_does_not_cover_exit"
        return True, ""

    def _terminal_fill_receipt(
        self, receipt: Any, pending: PendingOrder
    ) -> tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(receipt, Mapping) or not pending.order_id:
            return None, "terminal_provider_fill_receipt_required"
        times = _fresh_times(receipt, self._clock())
        order_id = str(receipt.get("orderId") or "").strip()
        source_id = str(receipt.get("source_id") or "").strip()
        quantity = _finite(receipt.get("filled_qty"), positive=True)
        price = _finite(receipt.get("filled_avg_price"), positive=True)
        notional = _finite(receipt.get("filled_notional"), positive=True)
        fee = _finite(receipt.get("fee"), nonnegative=True)
        fee_currency = _canonical_asset(receipt.get("fee_currency"))
        fills = receipt.get("fills")
        trade_ids = (
            [
                str(row.get("tradeId") or "").strip()
                for row in fills
                if isinstance(row, Mapping)
            ]
            if isinstance(fills, list)
            else []
        )
        expected_notional = (
            quantity * price
            if quantity is not None and price is not None
            else None
        )
        if (
            times is None
            or receipt.get("status") != "FILLED"
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("fill_receipt_complete") is not True
            or receipt.get("eligible_for_accounting") is not True
            or receipt.get("eligible_for_learning") is not True
            or receipt.get("reconciliation_required") is not False
            or order_id != pending.order_id
            or not source_id.lower().startswith("kraken_order:")
            or _canonical_pair(receipt.get("symbol"))
            != _canonical_pair(pending.kraken_pair)
            or str(receipt.get("side") or "").strip().lower() != pending.side
            or quantity is None
            or not math.isclose(
                quantity, pending.requested_quantity,
                rel_tol=1e-9, abs_tol=1e-12,
            )
            or price is None
            or notional is None
            or expected_notional is None
            or not math.isclose(
                notional, expected_notional,
                rel_tol=0.001, abs_tol=1e-8,
            )
            or fee is None
            or not fee_currency
            or not trade_ids
            or any(not trade_id for trade_id in trade_ids)
            or len(trade_ids) != len(set(trade_ids))
        ):
            return None, "terminal_provider_fill_fee_receipt_incomplete"
        source_timestamp, received_at = times
        return {
            **dict(receipt),
            "order_id": order_id,
            "source_id": source_id,
            "filled_qty": quantity,
            "filled_avg_price": price,
            "filled_notional": notional,
            "fee": fee,
            "fee_currency": fee_currency,
            "trade_ids": tuple(trade_ids),
            "source_timestamp": source_timestamp,
            "received_at": received_at,
        }, ""

    def _terminal_without_fill(
        self, receipt: Any, pending: PendingOrder
    ) -> bool:
        if not isinstance(receipt, Mapping) or not pending.order_id:
            return False
        status = str(receipt.get("status") or "").strip().upper()
        return bool(
            _fresh_times(receipt, self._clock()) is not None
            and status in {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}
            and receipt.get("data_status") == "live"
            and receipt.get("truth_status") == "real_observed"
            and receipt.get("generated_values") is False
            and receipt.get("reconciliation_required") is False
            and str(receipt.get("orderId") or "").strip() == pending.order_id
        )

    def _submit_intent(
        self,
        *,
        intent_key: str,
        symbol: str,
        pair: str,
        side: str,
        quantity: float,
        score: int,
        bundle: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if self.dry_run:
            return self._record_no_data(
                "dry_run_order_not_submitted", status="not_submitted"
            )
        place_order = getattr(self.kraken, "place_market_order", None)
        if not callable(place_order):
            return self._record_no_data("kraken_order_adapter_unavailable")
        try:
            acknowledgement = place_order(
                symbol=pair, side=side, quantity=quantity
            )
        except Exception:
            return self._record_no_data("order_submission_request_failed")
        if (
            isinstance(acknowledgement, Mapping)
            and acknowledgement.get("data_status") == "not_submitted"
        ):
            return self._record_no_data(
                "provider_dry_run_order_not_submitted",
                status="not_submitted",
            )
        order_id = (
            str(acknowledgement.get("orderId") or "").strip()
            if isinstance(acknowledgement, Mapping)
            else ""
        )
        acknowledged_quantity = (
            _finite(acknowledgement.get("requestedQty"), positive=True)
            if isinstance(acknowledgement, Mapping)
            else None
        )
        pending = PendingOrder(
            intent_key=intent_key,
            symbol=symbol,
            kraken_pair=pair,
            side=side,
            requested_quantity=acknowledged_quantity or quantity,
            score=score,
            order_id=order_id or None,
            market_receipt_id=bundle["market"].receipt_id,
            account_receipt_id=str(bundle["account"]["receipt_id"]),
            gate_receipt_id=str(bundle["gate"]["receipt_id"]),
            state="pending_reconciliation" if order_id else "ambiguous_submission",
        )
        self._pending_orders[intent_key] = pending
        if not order_id:
            return self._record_no_data(
                "ambiguous_submission_requires_external_reconciliation",
                status="pending_reconciliation",
            )
        return self._record_no_data(
            "submission_acknowledged_terminal_receipt_required",
            status="pending_reconciliation",
            order_id=order_id,
        )

    def _reconcile_pending(
        self,
        intent_key: str,
        apply_fill: Callable[[PendingOrder, Mapping[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        pending = self._pending_orders[intent_key]
        if pending.state == "ambiguous_submission":
            return self._record_no_data(
                "ambiguous_submission_requires_external_reconciliation",
                status="pending_reconciliation",
            )
        if pending.state == "terminal_without_fill":
            return self._record_no_data(
                "terminal_provider_receipt_without_fill",
                order_id=pending.order_id,
            )
        readback = getattr(self.kraken, "get_order_status", None)
        if not callable(readback) or not pending.order_id:
            return self._record_no_data(
                "supported_order_readback_unavailable",
                status="pending_reconciliation",
                order_id=pending.order_id,
            )
        try:
            receipt = readback(pending.order_id)
        except Exception:
            return self._record_no_data(
                "provider_order_readback_failed",
                status="pending_reconciliation",
                order_id=pending.order_id,
            )
        if self._terminal_without_fill(receipt, pending):
            pending.state = "terminal_without_fill"
            self._settled_intents.add(intent_key)
            return self._record_no_data(
                "terminal_provider_receipt_without_fill",
                order_id=pending.order_id,
            )
        terminal, reason = self._terminal_fill_receipt(receipt, pending)
        if terminal is None:
            return self._record_no_data(
                reason,
                status="pending_reconciliation",
                order_id=pending.order_id,
            )
        return apply_fill(pending, terminal)

    def _fill_already_accounted(self, terminal: Mapping[str, Any]) -> bool:
        return bool(
            str(terminal["order_id"]) in self._accounted_order_ids
            or set(terminal["trade_ids"]) & self._accounted_trade_ids
        )

    def _apply_entry_fill(
        self, pending: PendingOrder, terminal: Mapping[str, Any]
    ) -> Dict[str, Any]:
        if self._fill_already_accounted(terminal):
            return self._record_no_data(
                "duplicate_terminal_fill_receipt", order_id=pending.order_id
            )
        if pending.symbol in self.positions:
            return self._record_no_data(
                "position_already_exists", order_id=pending.order_id
            )
        source_timestamp = float(terminal["source_timestamp"])
        position = V14Trade(
            symbol=pending.symbol,
            entry_price=float(terminal["filled_avg_price"]),
            quantity=float(terminal["filled_qty"]),
            entry_time=datetime.fromtimestamp(source_timestamp, tz=timezone.utc),
            entry_score=pending.score,
            kraken_pair=pending.kraken_pair,
            entry_fee=float(terminal["fee"]),
            entry_fee_currency=str(terminal["fee_currency"]),
            entry_order_id=str(terminal["order_id"]),
            entry_trade_ids=tuple(terminal["trade_ids"]),
            entry_source_id=str(terminal["source_id"]),
            entry_source_timestamp=source_timestamp,
            entry_received_at=float(terminal["received_at"]),
            market_receipt_id=pending.market_receipt_id,
            account_receipt_id=pending.account_receipt_id,
            gate_receipt_id=pending.gate_receipt_id,
            current_price=float(terminal["filled_avg_price"]),
            current_pnl_pct=0.0,
        )
        self.positions[pending.symbol] = position
        self._accounted_order_ids.add(position.entry_order_id)
        self._accounted_trade_ids.update(position.entry_trade_ids)
        self._settled_intents.add(pending.intent_key)
        self._pending_orders.pop(pending.intent_key, None)
        self.daily_entries += 1
        self.stats["v14_evaluations"] += 1
        self.stats["entries_approved"] += 1
        self.stats["real_trades_placed"] += 1
        outcome = {
            "status": "FILLED",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "order_id": position.entry_order_id,
            "filled_qty": position.quantity,
            "filled_avg_price": position.entry_price,
            "fee": position.entry_fee,
            "fee_currency": position.entry_fee_currency,
            "source_id": position.entry_source_id,
            "source_timestamp": position.entry_source_timestamp,
            "received_at": position.entry_received_at,
            "action": False,
            "accounting": True,
            "learning": True,
        }
        self.last_execution = outcome
        return outcome

    async def _open_position(
        self,
        symbol: str,
        price: float,
        score: int,
        *,
        bundle: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        evidence = bundle
        if evidence is None:
            evidence, reason = self._evidence_bundle(symbol)
            if evidence is None:
                return self._record_no_data(reason)
        market: LivePrice = evidence["market"]
        supplied_price = _finite(price, positive=True)
        if supplied_price is None or not math.isclose(
            supplied_price, market.price,
            rel_tol=1e-12, abs_tol=1e-12,
        ):
            return self._record_no_data(
                "entry_price_must_match_market_receipt"
            )
        intent_key = f"entry:{symbol}"
        if intent_key in self._pending_orders:
            return self._reconcile_pending(intent_key, self._apply_entry_fill)
        if symbol in self.positions:
            return self._record_no_data("position_already_exists")
        starting_capital = _finite(self.starting_capital, positive=True)
        if starting_capital is None:
            return self._record_no_data("finite_starting_capital_required")

        # Preserve the accepted V14 sizing equation exactly.
        position_usd = min(
            self.MAX_POSITION_USD,
            starting_capital * 0.02,
        )
        if position_usd < self.MIN_POSITION_USD:
            return self._record_no_data(
                "position_size_below_configured_minimum"
            )
        quantity = position_usd / market.price
        pair = self.BINANCE_TO_KRAKEN[symbol]
        capacity, reason = self._account_has_capacity(
            evidence["account"],
            pair=pair,
            side="buy",
            quantity=quantity,
            price=market.price,
        )
        if not capacity:
            return self._record_no_data(reason)
        return self._submit_intent(
            intent_key=intent_key,
            symbol=symbol,
            pair=pair,
            side="buy",
            quantity=quantity,
            score=int(score),
            bundle=evidence,
        )

    @staticmethod
    def _add_currency_component(
        components: Dict[str, float], currency: str, amount: float
    ) -> None:
        components[currency] = components.get(currency, 0.0) + amount

    def _apply_exit_fill(
        self, pending: PendingOrder, terminal: Mapping[str, Any]
    ) -> Dict[str, Any]:
        if self._fill_already_accounted(terminal):
            return self._record_no_data(
                "duplicate_terminal_fill_receipt", order_id=pending.order_id
            )
        position = self.positions.get(pending.symbol)
        if position is None:
            return self._record_no_data(
                "position_missing_for_terminal_exit",
                order_id=pending.order_id,
            )
        exit_price = float(terminal["filled_avg_price"])
        quantity = float(terminal["filled_qty"])
        if not math.isclose(
            quantity, position.quantity, rel_tol=1e-9, abs_tol=1e-12
        ):
            return self._record_no_data(
                "terminal_exit_quantity_does_not_match_position",
                status="pending_reconciliation",
                order_id=pending.order_id,
            )

        # Preserve the accepted V14 equations, then book observed fees as
        # exact currency components without estimating conversion rates.
        pnl_pct = (
            (exit_price - position.entry_price) / position.entry_price
        ) * 100.0
        gross_pnl = quantity * (exit_price - position.entry_price)
        _base, quote = self._pair_assets(position.kraken_pair)
        if quote is None:
            return self._record_no_data(
                "unambiguous_quote_currency_required",
                status="pending_reconciliation",
                order_id=pending.order_id,
            )
        components: Dict[str, float] = {}
        self._add_currency_component(components, quote, gross_pnl)
        self._add_currency_component(
            components, position.entry_fee_currency, -position.entry_fee
        )
        self._add_currency_component(
            components,
            str(terminal["fee_currency"]),
            -float(terminal["fee"]),
        )
        exact_usd_pnl = (
            components.get("USD")
            if set(components).issubset({"USD"})
            else None
        )
        exit_source_timestamp = float(terminal["source_timestamp"])
        trade = {
            "symbol": pending.symbol,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl_pct": pnl_pct,
            "pnl_usd": exact_usd_pnl,
            "realized_pnl_by_currency": dict(components),
            "entry_fee": position.entry_fee,
            "entry_fee_currency": position.entry_fee_currency,
            "exit_fee": float(terminal["fee"]),
            "exit_fee_currency": str(terminal["fee_currency"]),
            "entry_score": position.entry_score,
            "entry_order_id": position.entry_order_id,
            "exit_order_id": str(terminal["order_id"]),
            "entry_trade_ids": list(position.entry_trade_ids),
            "exit_trade_ids": list(terminal["trade_ids"]),
            "entry_time": position.entry_time.isoformat(),
            "exit_time": datetime.fromtimestamp(
                exit_source_timestamp, tz=timezone.utc
            ).isoformat(),
            "hold_hours": (
                exit_source_timestamp - position.entry_source_timestamp
            ) / 3600.0,
            "reason": "PROFIT_TARGET",
            "market_receipt_id": pending.market_receipt_id,
            "account_receipt_id": pending.account_receipt_id,
            "gate_receipt_id": pending.gate_receipt_id,
            "truth_status": "real_observed",
            "generated_values": False,
            "accounting_eligible": True,
            "learning_eligible": True,
        }
        self.closed_trades.append(trade)
        del self.positions[pending.symbol]
        self._accounted_order_ids.add(str(terminal["order_id"]))
        self._accounted_trade_ids.update(terminal["trade_ids"])
        self._settled_intents.add(pending.intent_key)
        self._pending_orders.pop(pending.intent_key, None)
        self.stats["exits_profit_target"] += 1
        self.stats["real_trades_placed"] += 1
        aggregate = self.stats["realized_pnl_by_currency"]
        for currency, amount in components.items():
            aggregate[currency] = aggregate.get(currency, 0.0) + amount
        self.stats["total_profit"] = (
            aggregate.get("USD", 0.0)
            if set(aggregate).issubset({"USD"})
            else None
        )
        pnl_values = [row.get("pnl_usd") for row in self.closed_trades]
        if all(_finite(value) is not None for value in pnl_values):
            wins = sum(1 for value in pnl_values if float(value) > 0.0)
            self.stats["win_rate"] = wins / len(pnl_values)
        else:
            self.stats["win_rate"] = None
        outcome = {
            "status": "FILLED",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "order_id": str(terminal["order_id"]),
            "filled_qty": quantity,
            "filled_avg_price": exit_price,
            "fee": float(terminal["fee"]),
            "fee_currency": str(terminal["fee_currency"]),
            "realized_pnl_by_currency": dict(components),
            "source_id": str(terminal["source_id"]),
            "source_timestamp": exit_source_timestamp,
            "received_at": float(terminal["received_at"]),
            "action": False,
            "accounting": True,
            "learning": True,
        }
        self.last_execution = outcome
        return outcome

    async def _close_position(
        self,
        symbol: str,
        price: float,
        reason: str,
        *,
        bundle: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        position = self.positions.get(symbol)
        if position is None:
            return self._record_no_data("position_not_found")
        evidence = bundle
        if evidence is None:
            evidence, evidence_reason = self._evidence_bundle(symbol)
            if evidence is None:
                return self._record_no_data(evidence_reason)
        market: LivePrice = evidence["market"]
        supplied_price = _finite(price, positive=True)
        if supplied_price is None or not math.isclose(
            supplied_price, market.price,
            rel_tol=1e-12, abs_tol=1e-12,
        ):
            return self._record_no_data(
                "exit_price_must_match_market_receipt"
            )
        intent_key = f"exit:{symbol}:{position.entry_order_id}"
        if intent_key in self._pending_orders:
            return self._reconcile_pending(intent_key, self._apply_exit_fill)
        if reason != "PROFIT_TARGET":
            return self._record_no_data("unsupported_exit_reason")
        capacity, capacity_reason = self._account_has_capacity(
            evidence["account"],
            pair=position.kraken_pair,
            side="sell",
            quantity=position.quantity,
            price=market.price,
        )
        if not capacity:
            return self._record_no_data(capacity_reason)
        return self._submit_intent(
            intent_key=intent_key,
            symbol=symbol,
            pair=position.kraken_pair,
            side="sell",
            quantity=position.quantity,
            score=position.entry_score,
            bundle=evidence,
        )

    async def _v14_check(self, symbol: str) -> Dict[str, Any]:
        """Evaluate one accepted receipt and perform at most one order read."""
        bundle, reason = self._evidence_bundle(symbol)
        if bundle is None:
            return self._record_no_data(reason)
        market: LivePrice = bundle["market"]
        position = self.positions.get(symbol)
        if position is not None:
            exit_key = f"exit:{symbol}:{position.entry_order_id}"
            if exit_key in self._pending_orders:
                return await self._close_position(
                    symbol, market.price, "PROFIT_TARGET", bundle=bundle
                )
            current_pnl_pct = (
                (market.price - position.entry_price)
                / position.entry_price
            ) * 100.0
            if current_pnl_pct >= self.PROFIT_TARGET_PCT:
                return await self._close_position(
                    symbol, market.price, "PROFIT_TARGET", bundle=bundle
                )
            position.current_price = market.price
            position.current_pnl_pct = current_pnl_pct
            return {
                "status": "holding",
                "data_status": "live",
                "truth_status": "real_derived",
                "generated_values": False,
                "source_receipt_id": market.receipt_id,
                "action": False,
                "accounting": False,
                "learning": False,
            }

        entry_key = f"entry:{symbol}"
        if entry_key in self._pending_orders:
            pending = self._pending_orders[entry_key]
            return await self._open_position(
                symbol, market.price, pending.score, bundle=bundle
            )
        if len(self.positions) >= self.MAX_CONCURRENT_POSITIONS:
            return self._record_no_data(
                "maximum_concurrent_positions_reached"
            )
        if self.daily_entries >= self.MAX_DAILY_TRADES:
            return self._record_no_data("maximum_daily_entries_reached")
        evaluation, reason = self._score_entry(symbol, market)
        if evaluation is None:
            return self._record_no_data(reason)
        if not evaluation["should_enter"]:
            return {
                "status": "v14_rejected",
                "data_status": "live",
                "truth_status": "real_derived",
                "generated_values": False,
                "source_receipt_id": market.receipt_id,
                "action": False,
                "accounting": False,
                "learning": False,
            }
        return await self._open_position(
            symbol, market.price, int(evaluation["score"]), bundle=bundle
        )

    def check_runtime_ready(self) -> bool:
        return bool(
            self.kraken is not None
            and self.v14 is not None
            and callable(getattr(self.kraken, "get_ticker_receipt", None))
            and callable(self.account_receipt_supplier)
            and callable(self.hnc_auris_gate_receipt_supplier)
        )

    async def _kraken_poll_loop(self, interval_seconds: float = 2.0) -> None:
        getter = getattr(self.kraken, "get_ticker_receipt", None)
        while self.running and callable(getter):
            for symbol in self.STRATEGY_SYMBOLS:
                if not self.running:
                    break
                pair = self.BINANCE_TO_KRAKEN[symbol]
                try:
                    receipt = getter(pair)
                except Exception:
                    self._record_no_data(
                        "kraken_market_receipt_unavailable"
                    )
                    continue
                accepted = self.ingest_market_receipt(symbol, receipt)
                if accepted.get("status") == "accepted":
                    await self._v14_check(symbol)
            await asyncio.sleep(interval_seconds)

    async def run(self) -> Dict[str, Any]:
        """Run only after explicit configuration and source injection."""
        if not self.check_runtime_ready():
            return self._record_no_data(
                "market_account_and_hnc_auris_receipt_adapters_required"
            )
        self.install_signal_handlers()
        self.running = True
        self.start_time = self._clock()
        try:
            await self._kraken_poll_loop()
        except asyncio.CancelledError:
            self.running = False
        return {
            "status": "stopped",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "action": False,
            "accounting": False,
            "learning": False,
        }


async def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5 V14 receipt-gated execution"
    )
    parser.add_argument(
        "--run", action="store_true", help="Start the explicit runtime"
    )
    parser.add_argument(
        "--live", action="store_true", help="Allow provider order submission"
    )
    parser.add_argument("--capital", type=float, default=10000.0)
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps(_no_data("explicit_run_flag_required"), sort_keys=True))
        return 0
    engine = S5V14LiveEngine(
        starting_capital=args.capital,
        dry_run=not args.live,
    )
    engine.configure_default_runtime()
    outcome = await engine.run()
    print(json.dumps(outcome, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
