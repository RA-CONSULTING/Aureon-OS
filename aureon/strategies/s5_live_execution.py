#!/usr/bin/env python3
"""
🔥🔥🔥 S5 LIVE EXECUTION ENGINE - REAL MONEY 🔥🔥🔥
═══════════════════════════════════════════════════════════════
LIVE trading with real Kraken execution.
Real-time WebSocket data → S5 Decision → Real Order Execution

Gary Leckey & GitHub Copilot | January 2026
"Taking Over The World - One Conversion At A Time"

⚠️  WARNING: THIS EXECUTES REAL TRADES WITH REAL MONEY! ⚠️
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import math
import os
import signal
import tempfile
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from aureon.governance.durable_contingency import (
    DurableContingencyRecordRef,
    DurableContingencyRecovery,
)
from aureon.governance.economic_boundary import (
    ContingencyWarrant,
    ContingencyWarrantScope,
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
)

MAX_RECEIPT_AGE_SECONDS = 300.0
FUTURE_TOLERANCE_SECONDS = 5.0
KRAKEN_ADD_ORDER_METHOD = 'POST'
KRAKEN_ADD_ORDER_PATH = '/0/private/AddOrder'
_DIGEST_LENGTH = 64
INTENT_STATE_SCHEMA = "aureon.s5_live_execution.intent.v2"


def _finite(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
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
        "XXBT": "BTC",
        "XBT": "BTC",
        "XXDG": "DOGE",
        "XDG": "DOGE",
        "ZUSD": "USD",
    }.get(asset, asset)


def _canonical_decimal_text(value: Any, *, positive: bool = False) -> str:
    if isinstance(value, bool):
        raise ValueError('finite_decimal_required')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('finite_decimal_required') from exc
    if not number.is_finite() or (positive and number <= 0):
        raise ValueError('finite_decimal_required')
    text = format(number, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return '0' if Decimal(text) == 0 else text


def _valid_digest(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if (
        candidate != value
        or len(candidate) != _DIGEST_LENGTH
        or any(character not in '0123456789abcdef' for character in candidate)
    ):
        return None
    return candidate


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _accepts_keyword(function: Any, name: str) -> bool:
    """Inspect an adapter without invoking it or masking its own TypeError."""
    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError):
        return False
    parameter = parameters.get(name)
    if parameter is not None and parameter.kind in {
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    }:
        return True
    return any(
        item.kind is inspect.Parameter.VAR_KEYWORD
        for item in parameters.values()
    )


def _client_order_id(intent_key: str) -> str:
    """Derive Kraken's 32-hex short UUID form from a durable intent key."""
    return hashlib.sha256(intent_key.encode("utf-8")).hexdigest()[:32]


def _validated_client_order_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    if len(candidate) != 32:
        return None
    if any(character not in "0123456789abcdef" for character in candidate):
        return None
    return candidate


def _fresh_times(
    receipt: Mapping[str, Any],
    now: float,
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


def _no_data(
    reason: str,
    *,
    status: str = "no_data",
    order_id: Optional[str] = None,
    intent_key: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "data_status": status,
        "truth_status": "no_data",
        "generated_values": False,
        "reason": reason,
        "order_id": order_id,
        "intent_key": intent_key,
        "action": False,
        "accounting": False,
        "learning": False,
    }


@dataclass
class LivePrice:
    """Complete provider-observed market receipt accepted by the engine."""

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
class ConversionOpportunity:
    """Receipt-derived S5 opportunity; estimates never enter accounting."""

    from_asset: str
    to_asset: str
    gross_profit: float
    fee: float
    net_profit: float
    price_change: float
    timestamp: datetime
    opportunity_type: str
    s5_score: float
    symbol: str
    venue_symbol: str
    quantity: float
    side: str
    market_receipt_id: str
    account_receipt_id: str
    gate_receipt_id: str


@dataclass
class PendingIntent:
    intent_key: str
    symbol: str
    venue_symbol: str
    side: str
    requested_quantity: float
    opportunity: Dict[str, Any]
    market_receipt_id: str
    account_receipt_id: str
    gate_receipt_id: str
    state: str
    order_id: Optional[str]
    client_order_id: Optional[str] = None
    durable_state_anchor: Optional[str] = None
    economic_intent_digest: Optional[str] = None
    economic_body_digest: Optional[str] = None
    provider_moment_digest: Optional[str] = None
    governance_permit_id: Optional[str] = None
    governance_dual_receipt_id: Optional[str] = None
    governance_proposal_digest: Optional[str] = None
    governance_permit_consumed: bool = False
    contingency_warrant_id: Optional[str] = None
    contingency_scope_digest: Optional[str] = None
    contingency_warrant: Optional[Dict[str, Any]] = None
    contingency_scope: Optional[Dict[str, Any]] = None
    contingency_recovery_record_digest: Optional[str] = None
    contingency_recovery_entry_state_anchor: Optional[str] = None
    contingency_recovery_route_binding_anchor: Optional[str] = None
    containment_client_order_id: Optional[str] = None
    pre_entry_base_balance: Optional[str] = None


class S5LiveExecutionEngine:
    """
    🔥 REAL MONEY S5 TRADING ENGINE 🔥
    
    Executes real trades on Kraken based on S5 signals.
    """
    
    # Trading pairs - Binance format for WebSocket
    # Include pairs that match YOUR HOLDINGS!
    BINANCE_PAIRS = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
        'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT',
        'ATOMUSDT', 'UNIUSDT', 'LTCUSDT', 'NEARUSDT', 'APTUSDT',
        'LUNAUSDT', 'LUNCUSDT',
    ]
    
    # Kraken pair mapping
    BINANCE_TO_KRAKEN = {
        'BTCUSDT': 'XBTUSD',
        'ETHUSDT': 'ETHUSD',
        'SOLUSDT': 'SOLUSD',
        'XRPUSDT': 'XRPUSD',
        'ADAUSDT': 'ADAUSD',
        'DOGEUSDT': 'DOGEUSD',
        'AVAXUSDT': 'AVAXUSD',
        'DOTUSDT': 'DOTUSD',
        'LINKUSDT': 'LINKUSD',
        'MATICUSDT': 'MATICUSD',
        'ATOMUSDT': 'ATOMUSD',
        'UNIUSDT': 'UNIUSD',
        'LTCUSDT': 'LTCUSD',
        'NEARUSDT': 'NEARUSD',
        'APTUSDT': 'APTUSD',
        'LUNAUSDT': 'LUNAUSD',
        'LUNCUSDT': 'LUNCUSD',
    }
    
    # Risk management
    MAX_POSITION_USD = 50.0      # Max $50 per trade
    MIN_POSITION_USD = 5.0       # Min $5 per trade
    MAX_DAILY_TRADES = 100       # Max trades per day
    MAX_DAILY_LOSS = 25.0        # Stop if loss exceeds $25
    
    # Opportunity detection thresholds (very aggressive)
    MIN_PRICE_CHANGE = 0.0003    # 0.03% minimum move (3 bps)
    MIN_VOLATILITY = 0.0005      # 0.05% minimum volatility
    MIN_PROFIT = 0.001           # $0.001 minimum profit
    
    def __init__(
        self,
        starting_capital: Optional[float] = None,
        dry_run: bool = True,
        *,
        kraken: Any = None,
        network: Any = None,
        account_receipt_supplier: Optional[
            Callable[[], Mapping[str, Any]]
        ] = None,
        hnc_auris_gate_receipt_supplier: Optional[
            Callable[[], Mapping[str, Any]]
        ] = None,
        economic_governance_boundary: Optional[
            EconomicGovernanceBoundary
        ] = None,
        contingency_recovery: Optional[
            DurableContingencyRecovery
        ] = None,
        intent_store_path: Optional[Path] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.starting_capital = starting_capital
        self.dry_run = bool(dry_run)
        self.kraken = kraken
        self.network = network
        self.account_receipt_supplier = account_receipt_supplier
        self.hnc_auris_gate_receipt_supplier = (
            hnc_auris_gate_receipt_supplier
        )
        self.economic_governance_boundary = economic_governance_boundary
        self.contingency_recovery = contingency_recovery
        self.intent_store_path = (
            Path(intent_store_path) if intent_store_path is not None else None
        )
        self._clock = clock

        # Price tracking
        self.prices: Dict[str, LivePrice] = {}
        self.prev_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[tuple]] = defaultdict(list)

        # Trading state
        self.running = False
        self.start_time: Optional[float] = None
        self.ws_connected = False
        self.execution_enabled = not self.dry_run

        # Risk tracking
        self.daily_trades = 0
        self.daily_pnl_by_currency: Dict[str, float] = {}
        self.open_positions: Dict[str, Dict] = {}

        # Stats
        self.stats = {
            'price_updates': 0,
            'opportunities_found': 0,
            'conversions_executed': 0,
            'real_trades_placed': 0,
            'observed_fees_by_currency': {},
            'realized_pnl_by_currency': {},
            'best_conversion': None,
            'failed_trades': 0,
        }

        self.execution_queue: List[ConversionOpportunity] = []
        self.execution_lock = threading.Lock()
        self._intent_lock_local = threading.local()

        self.last_no_data: Optional[Dict[str, Any]] = None
        self.last_execution: Optional[Dict[str, Any]] = None
        self._seen_market_receipts: set[str] = set()
        self._latest_market_timestamp: Dict[str, float] = {}
        self._pending_intents: Dict[str, PendingIntent] = {}
        self._closed_intents: Dict[str, Dict[str, Any]] = {}
        self._settled_fills: List[Dict[str, Any]] = []
        self._accounted_order_ids: set[str] = set()
        self._accounted_trade_ids: set[str] = set()
        self._learning_applied_receipt_ids: set[str] = set()
        self._state_load_error: Optional[str] = None
        self._readback_consumed = False
        if self.intent_store_path is not None:
            self._load_intent_state()

    def configure_default_runtime(self) -> "S5LiveExecutionEngine":
        """Explicitly construct native adapters without making provider calls."""
        capital = _finite(self.starting_capital, positive=True)
        if capital is None:
            raise ValueError("finite starting_capital required")
        if self.network is None:
            from aureon.core.aureon_mycelium import MyceliumNetwork

            self.network = MyceliumNetwork(initial_capital=capital)
        if self.kraken is None:
            from aureon.exchanges.kraken_client import get_kraken_client

            self.kraken = get_kraken_client()
        if self.account_receipt_supplier is None:
            supplier = getattr(
                self.kraken, "get_account_balance_receipt", None
            )
            if callable(supplier):
                self.account_receipt_supplier = supplier
        return self

    def install_signal_handlers(self) -> None:
        """Install process handlers only for an explicitly managed runtime."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _record_no_data(
        self,
        reason: str,
        *,
        status: str = "no_data",
        order_id: Optional[str] = None,
        intent_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        outcome = _no_data(
            reason,
            status=status,
            order_id=order_id,
            intent_key=intent_key,
        )
        self.last_no_data = outcome
        return outcome

    @staticmethod
    def _pending_from_state(raw: Any) -> PendingIntent:
        if not isinstance(raw, Mapping):
            raise ValueError("pending intent must be an object")
        requested_quantity = _finite(
            raw.get("requested_quantity"), positive=True
        )
        opportunity = raw.get("opportunity")
        required_text = {
            name: str(raw.get(name) or "").strip()
            for name in (
                "intent_key",
                "symbol",
                "venue_symbol",
                "side",
                "market_receipt_id",
                "account_receipt_id",
                "gate_receipt_id",
                "state",
            )
        }
        if (
            requested_quantity is None
            or any(not value for value in required_text.values())
            or required_text["side"] not in {"buy", "sell"}
            or not isinstance(opportunity, Mapping)
        ):
            raise ValueError("pending intent fields are incomplete")
        order_id_value = raw.get("order_id")
        order_id = (
            str(order_id_value).strip()
            if order_id_value is not None
            else None
        )
        if order_id == "":
            order_id = None
        raw_client_order_id = raw.get("client_order_id")
        client_order_id = (
            _validated_client_order_id(raw_client_order_id)
            if raw_client_order_id is not None
            else None
        )
        if raw_client_order_id is not None and client_order_id is None:
            raise ValueError("pending client order identifier is invalid")
        optional_names = (
            'durable_state_anchor',
            'economic_intent_digest',
            'economic_body_digest',
            'provider_moment_digest',
            'governance_permit_id',
            'governance_dual_receipt_id',
            'governance_proposal_digest',
            'contingency_warrant_id',
            'contingency_scope_digest',
            'contingency_recovery_record_digest',
            'contingency_recovery_entry_state_anchor',
            'contingency_recovery_route_binding_anchor',
            'containment_client_order_id',
            'pre_entry_base_balance',
        )
        optional_text: Dict[str, Optional[str]] = {}
        for name in optional_names:
            value = raw.get(name)
            if value is None:
                optional_text[name] = None
                continue
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError('pending governance lineage is invalid')
            optional_text[name] = value
        for name in (
            'durable_state_anchor',
            'economic_intent_digest',
            'economic_body_digest',
            'provider_moment_digest',
            'governance_proposal_digest',
            'contingency_scope_digest',
            'contingency_recovery_record_digest',
            'contingency_recovery_entry_state_anchor',
            'contingency_recovery_route_binding_anchor',
        ):
            value = optional_text[name]
            if value is not None and _valid_digest(value) is None:
                raise ValueError('pending governance digest is invalid')
        containment_id = optional_text['containment_client_order_id']
        if (
            containment_id is not None
            and _validated_client_order_id(containment_id) is None
        ):
            raise ValueError('pending containment identifier is invalid')
        pre_entry_balance = optional_text['pre_entry_base_balance']
        if pre_entry_balance is not None:
            try:
                _canonical_decimal_text(pre_entry_balance)
            except ValueError as exc:
                raise ValueError('pending pre-entry balance is invalid') from exc
        permit_consumed = raw.get('governance_permit_consumed', False)
        if type(permit_consumed) is not bool:
            raise ValueError('pending permit consumption marker is invalid')
        contingency_warrant = raw.get('contingency_warrant')
        contingency_scope = raw.get('contingency_scope')
        if (
            contingency_warrant is not None
            and not isinstance(contingency_warrant, Mapping)
        ) or (
            contingency_scope is not None
            and not isinstance(contingency_scope, Mapping)
        ):
            raise ValueError('pending contingency material is invalid')
        return PendingIntent(
            intent_key=required_text["intent_key"],
            client_order_id=client_order_id,
            symbol=required_text["symbol"],
            venue_symbol=required_text["venue_symbol"],
            side=required_text["side"],
            requested_quantity=requested_quantity,
            opportunity=dict(opportunity),
            market_receipt_id=required_text["market_receipt_id"],
            account_receipt_id=required_text["account_receipt_id"],
            gate_receipt_id=required_text["gate_receipt_id"],
            state=required_text["state"],
            order_id=order_id,
            governance_permit_consumed=permit_consumed,
            contingency_warrant=(
                dict(contingency_warrant)
                if contingency_warrant is not None else None
            ),
            contingency_scope=(
                dict(contingency_scope)
                if contingency_scope is not None else None
            ),
            **optional_text,
        )

    @staticmethod
    def _stored_fill_from_state(raw: Any) -> Dict[str, Any]:
        """Validate historical accounting without imposing current freshness."""
        if not isinstance(raw, Mapping):
            raise ValueError("settled fill must be an object")
        required_text = {
            name: str(raw.get(name) or "").strip()
            for name in (
                "receipt_id",
                "order_id",
                "symbol",
                "venue_symbol",
                "side",
                "fee_currency",
                "source_id",
                "market_receipt_id",
                "account_receipt_id",
                "gate_receipt_id",
            )
        }
        quantity = _finite(raw.get("filled_qty"), positive=True)
        price = _finite(raw.get("filled_avg_price"), positive=True)
        notional = _finite(raw.get("filled_notional"), positive=True)
        fee = _finite(raw.get("fee"), nonnegative=True)
        source_timestamp = _finite(
            raw.get("source_timestamp"), positive=True
        )
        received_at = _finite(raw.get("received_at"), positive=True)
        trade_rows = raw.get("trade_ids")
        trade_ids = (
            [str(value).strip() for value in trade_rows]
            if isinstance(trade_rows, list)
            else []
        )
        opportunity = raw.get("opportunity")
        expected_notional = (
            quantity * price
            if quantity is not None and price is not None
            else None
        )
        has_realized_pnl = (
            "realized_pnl" in raw or "realized_pnl_currency" in raw
        )
        realized_pnl = (
            _finite(raw.get("realized_pnl"))
            if has_realized_pnl
            else None
        )
        realized_currency = (
            _canonical_asset(raw.get("realized_pnl_currency"))
            if has_realized_pnl
            else ""
        )
        if (
            any(not value for value in required_text.values())
            or required_text["side"] not in {"buy", "sell"}
            or not required_text["source_id"].lower().startswith(
                "kraken_order:"
            )
            or raw.get("truth_status") != "real_observed"
            or raw.get("generated_values") is not False
            or raw.get("accounting_eligible") is not True
            or type(raw.get("learning_eligible")) is not bool
            or quantity is None
            or price is None
            or notional is None
            or expected_notional is None
            or not math.isclose(
                notional,
                expected_notional,
                rel_tol=0.001,
                abs_tol=1e-8,
            )
            or fee is None
            or source_timestamp is None
            or received_at is None
            or source_timestamp
            > received_at + FUTURE_TOLERANCE_SECONDS
            or not trade_ids
            or any(not trade_id for trade_id in trade_ids)
            or len(trade_ids) != len(set(trade_ids))
            or not isinstance(opportunity, Mapping)
            or (
                has_realized_pnl
                and (realized_pnl is None or not realized_currency)
            )
        ):
            raise ValueError("settled fill evidence is incomplete")
        normalized = {
            **dict(raw),
            **required_text,
            "filled_qty": quantity,
            "filled_avg_price": price,
            "filled_notional": notional,
            "fee": fee,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "trade_ids": trade_ids,
            "opportunity": dict(opportunity),
        }
        if has_realized_pnl:
            normalized["realized_pnl"] = realized_pnl
            normalized["realized_pnl_currency"] = realized_currency
        return normalized

    @property
    def _intent_lock_path(self) -> Optional[Path]:
        if self.intent_store_path is None:
            return None
        path = self.intent_store_path
        return path.with_name(path.stem + '.lock')

    @contextmanager
    def _intent_store_lock(self):
        path = self._intent_lock_path
        depth = int(getattr(self._intent_lock_local, 'depth', 0))
        if path is None or depth:
            self._intent_lock_local.depth = depth + 1
            try:
                yield
            finally:
                self._intent_lock_local.depth = depth
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a+b') as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            self._intent_lock_local.depth = 1
            try:
                yield
            finally:
                self._intent_lock_local.depth = 0
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt

                    msvcrt.locking(
                        handle.fileno(),
                        msvcrt.LK_UNLCK,
                        1,
                    )
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_verified_intent_state(
        self,
    ) -> Optional[Dict[str, Any]]:
        path = self.intent_store_path
        if path is None or not path.exists():
            return None
        with self._intent_store_lock():
            raw = json.loads(path.read_text(encoding='utf-8'))
            if (
                not isinstance(raw, dict)
                or raw.get('schema') != INTENT_STATE_SCHEMA
            ):
                raise ValueError('unsupported intent state schema')
            observed_hash = _valid_digest(raw.get('state_hash'))
            core = {
                key: value for key, value in raw.items()
                if key != 'state_hash'
            }
            if observed_hash is None or observed_hash != _canonical_hash(core):
                raise ValueError('intent state hash mismatch')
            return raw

    def _load_intent_state(self) -> None:
        path = self.intent_store_path
        if path is None or not path.exists():
            return
        try:
            raw = self._read_verified_intent_state()
            if not isinstance(raw, Mapping):
                return
            pending_rows = raw.get("pending_intents")
            closed = raw.get("closed_intents")
            fills = raw.get("settled_fills")
            order_ids = raw.get("accounted_order_ids")
            trade_ids = raw.get("accounted_trade_ids")
            learning_ids = raw.get("learning_applied_receipt_ids")
            if (
                not isinstance(pending_rows, list)
                or not isinstance(closed, Mapping)
                or not isinstance(fills, list)
                or not isinstance(order_ids, list)
                or not isinstance(trade_ids, list)
                or not isinstance(learning_ids, list)
            ):
                raise ValueError("intent state collections are incomplete")
            pending: Dict[str, PendingIntent] = {}
            for row in pending_rows:
                intent = self._pending_from_state(row)
                if intent.intent_key in pending:
                    raise ValueError("duplicate pending intent key")
                pending[intent.intent_key] = intent
            normalized_fills = [
                self._stored_fill_from_state(row) for row in fills
            ]
            self._pending_intents = pending
            self._closed_intents = {
                str(key): dict(value)
                for key, value in closed.items()
                if str(key).strip() and isinstance(value, Mapping)
            }
            if len(self._closed_intents) != len(closed):
                raise ValueError("closed intent entries are invalid")
            self._settled_fills = normalized_fills
            self._accounted_order_ids = {
                str(value).strip() for value in order_ids if str(value).strip()
            }
            self._accounted_trade_ids = {
                str(value).strip() for value in trade_ids if str(value).strip()
            }
            self._learning_applied_receipt_ids = {
                str(value).strip()
                for value in learning_ids
                if str(value).strip()
            }
            if (
                len(self._accounted_order_ids) != len(order_ids)
                or len(self._accounted_trade_ids) != len(trade_ids)
                or len(self._learning_applied_receipt_ids)
                != len(learning_ids)
            ):
                raise ValueError("intent state identifiers are invalid")
            fill_order_ids = {
                str(fill["order_id"]) for fill in normalized_fills
            }
            fill_trade_ids = {
                str(trade_id)
                for fill in normalized_fills
                for trade_id in fill["trade_ids"]
            }
            fill_receipt_ids = {
                str(fill["receipt_id"]) for fill in normalized_fills
            }
            if (
                len(fill_order_ids) != len(normalized_fills)
                or len(fill_receipt_ids) != len(normalized_fills)
                or self._accounted_order_ids != fill_order_ids
                or self._accounted_trade_ids != fill_trade_ids
                or not self._learning_applied_receipt_ids.issubset(
                    fill_receipt_ids
                )
                or set(self._pending_intents)
                & set(self._closed_intents)
            ):
                raise ValueError("intent state evidence links are invalid")
            self._rebuild_accounting_views()
        except (
            KeyError,
            OSError,
            TypeError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            self._state_load_error = type(exc).__name__
            self._pending_intents = {}
            self._closed_intents = {}
            self._settled_fills = []
            self._accounted_order_ids = set()
            self._accounted_trade_ids = set()
            self._learning_applied_receipt_ids = set()
            self._rebuild_accounting_views()

    def _state_payload(self) -> Dict[str, Any]:
        core = {
            "schema": INTENT_STATE_SCHEMA,
            "pending_intents": [
                asdict(self._pending_intents[key])
                for key in sorted(self._pending_intents)
            ],
            "closed_intents": self._closed_intents,
            "settled_fills": self._settled_fills,
            "accounted_order_ids": sorted(self._accounted_order_ids),
            "accounted_trade_ids": sorted(self._accounted_trade_ids),
            "learning_applied_receipt_ids": sorted(
                self._learning_applied_receipt_ids
            ),
        }
        return {**core, 'state_hash': _canonical_hash(core)}

    def _persist_intent_state(self) -> bool:
        path = self.intent_store_path
        if (
            path is None
            or not path.parent.exists()
            or self._state_load_error is not None
        ):
            return False
        try:
            with self._intent_store_lock():
                payload = json.dumps(
                    self._state_payload(),
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                temporary_name: Optional[str] = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode='w',
                        encoding='utf-8',
                        dir=path.parent,
                        prefix=f'.{path.name}.',
                        suffix='.tmp',
                        delete=False,
                    ) as temporary:
                        temporary_name = temporary.name
                        temporary.write(payload + '\n')
                        temporary.flush()
                        os.fsync(temporary.fileno())
                    os.chmod(temporary_name, 0o600)
                    os.replace(temporary_name, path)
                    temporary_name = None
                finally:
                    if temporary_name is not None:
                        try:
                            Path(temporary_name).unlink()
                        except OSError:
                            pass
            return True
        except (OSError, TypeError, ValueError):
            return False

    def _rebuild_accounting_views(self) -> None:
        self.daily_trades = len(self._settled_fills)
        self.daily_pnl_by_currency = {}
        self.open_positions = {}
        self.stats = {
            'price_updates': 0,
            'opportunities_found': len(self._settled_fills),
            'conversions_executed': len(self._settled_fills),
            'real_trades_placed': len(self._settled_fills),
            'observed_fees_by_currency': {},
            'realized_pnl_by_currency': {},
            'best_conversion': None,
            'failed_trades': 0,
        }
        for fill in self._settled_fills:
            fee_currency = str(fill["fee_currency"])
            fee = float(fill["fee"])
            fee_totals = self.stats["observed_fees_by_currency"]
            fee_totals[fee_currency] = (
                fee_totals.get(fee_currency, 0.0) + fee
            )
            if "realized_pnl" in fill:
                pnl_currency = str(fill["realized_pnl_currency"])
                pnl = float(fill["realized_pnl"])
                pnl_totals = self.stats["realized_pnl_by_currency"]
                pnl_totals[pnl_currency] = (
                    pnl_totals.get(pnl_currency, 0.0) + pnl
                )
                self.daily_pnl_by_currency[pnl_currency] = (
                    self.daily_pnl_by_currency.get(pnl_currency, 0.0) + pnl
                )
            if fill["side"] == "buy":
                self.open_positions[str(fill["order_id"])] = {
                    "symbol": fill["symbol"],
                    "venue_symbol": fill["venue_symbol"],
                    "quantity": fill["filled_qty"],
                    "entry_price": fill["filled_avg_price"],
                    "fee": fill["fee"],
                    "fee_currency": fill["fee_currency"],
                    "source_timestamp": fill["source_timestamp"],
                    "terminal_receipt_id": fill["receipt_id"],
                }

    def _signal_handler(self, signum, frame):
        """Handle shutdown gracefully"""
        print("\n\n🛑 Shutdown signal received...")
        self.running = False
        
    def banner(self):
        """Display configuration only; never imply a live connection."""
        mode = "dry_run" if self.dry_run else "receipt_gated_live"
        print(
            "S5 receipt-gated execution engine "
            f"(mode={mode}, runtime_ready={self.check_runtime_ready()})"
        )

    def check_runtime_ready(self) -> bool:
        """Return adapter readiness without contacting any provider."""
        return bool(
            self.kraken is not None
            and self.network is not None
            and callable(getattr(self.kraken, "get_ticker_receipt", None))
            and callable(self.account_receipt_supplier)
            and callable(self.hnc_auris_gate_receipt_supplier)
            and (
                self.dry_run
                or (
                    isinstance(
                        self.economic_governance_boundary,
                        EconomicGovernanceBoundary,
                    )
                    and
                    self.intent_store_path is not None
                    and self._state_load_error is None
                )
            )
        )

    def check_kraken_connection(self) -> bool:
        """Compatibility readiness check; deliberately performs no I/O."""
        return self.check_runtime_ready()

    def _estimate_usd_value(
        self,
        asset: str,
        amount: float,
        market: Optional[LivePrice] = None,
    ) -> Optional[float]:
        """Derive value only from an accepted same-venue market receipt."""
        canonical_asset = _canonical_asset(asset)
        observed_amount = _finite(amount, nonnegative=True)
        if observed_amount is None:
            return None
        if canonical_asset == "USD":
            return observed_amount
        if market is None:
            return None
        pair_base, pair_quote = self._pair_assets(market.venue_symbol)
        if pair_base != canonical_asset or pair_quote != "USD":
            return None
        return observed_amount * market.price

    def _validate_market_receipt(
        self,
        symbol: str,
        receipt: Any,
    ) -> tuple[Optional[LivePrice], str]:
        if not isinstance(receipt, Mapping):
            return None, "complete_fresh_kraken_market_receipt_required"
        expected_pair = self.BINANCE_TO_KRAKEN.get(symbol)
        times = _fresh_times(receipt, self._clock())
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        price = _finite(receipt.get("price"), positive=True)
        bid = _finite(receipt.get("bid"), positive=True)
        ask = _finite(receipt.get("ask"), positive=True)
        volume = _finite(receipt.get("volume_24h"), nonnegative=True)
        change = _finite(receipt.get("change_pct"))
        venue_symbol = str(receipt.get("symbol") or "").strip().upper()
        if (
            expected_pair is None
            or times is None
            or not source_id.lower().startswith("kraken")
            or not receipt_id
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("action") is not False
            or receipt.get("accounting") is not False
            or receipt.get("learning") is not False
            or _canonical_pair(venue_symbol)
            != _canonical_pair(expected_pair)
            or price is None
            or bid is None
            or ask is None
            or bid > ask
            or volume is None
            or change is None
        ):
            return None, "complete_fresh_kraken_market_receipt_required"
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
        self,
        symbol: str,
        receipt: Any,
    ) -> Dict[str, Any]:
        market, reason = self._validate_market_receipt(symbol, receipt)
        if market is None:
            return self._record_no_data(reason)
        if market.receipt_id in self._seen_market_receipts:
            return self._record_no_data("duplicate_market_receipt")
        previous_timestamp = self._latest_market_timestamp.get(symbol)
        if (
            previous_timestamp is not None
            and market.source_timestamp <= previous_timestamp
        ):
            return self._record_no_data("non_monotonic_market_receipt")
        previous = self.prices.get(symbol)
        if previous is not None:
            self.prev_prices[symbol] = previous.price
        self.prices[symbol] = market
        self.price_history[symbol].append(
            (
                datetime.fromtimestamp(
                    market.source_timestamp, tz=timezone.utc
                ),
                market.price,
            )
        )
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol].pop(0)
        self._seen_market_receipts.add(market.receipt_id)
        self._latest_market_timestamp[symbol] = market.source_timestamp
        return {
            "status": "accepted",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "receipt_id": market.receipt_id,
            "action": False,
            "accounting": False,
            "learning": False,
        }

    async def _fetch_initial_prices(self) -> Dict[str, Any]:
        """Legacy REST acquisition is disabled; inject provider receipts."""
        return self._record_no_data(
            "provider_market_receipt_injection_required"
        )

    async def _binance_websocket(self) -> Dict[str, Any]:
        """Cross-venue raw WebSocket acquisition is disabled."""
        return self._record_no_data(
            "same_venue_kraken_market_receipt_required"
        )

    @staticmethod
    def _pair_assets(pair: str) -> tuple[Optional[str], Optional[str]]:
        canonical = _canonical_pair(pair)
        for quote in ("USDT", "USDC", "USD", "EUR", "GBP"):
            if canonical.endswith(quote) and len(canonical) > len(quote):
                return canonical[: -len(quote)], quote
        return None, None

    def _validate_account_receipt(
        self,
        receipt: Any,
        *,
        expected_pair: Optional[str] = None,
    ) -> tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(receipt, Mapping):
            return None, "complete_fresh_kraken_account_receipt_required"
        times = _fresh_times(receipt, self._clock())
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        raw_balances = receipt.get("balances")
        taker_fee_rate = _finite(
            receipt.get("taker_fee_rate"), nonnegative=True
        )
        raw_taker_fee_pair = receipt.get("taker_fee_pair")
        taker_fee_pair = (
            _canonical_pair(raw_taker_fee_pair)
            if raw_taker_fee_pair is not None
            else ""
        )
        provider_receipt_type = str(
            receipt.get("provider_receipt_type") or ""
        ).strip()
        pair_scoped_provider_receipt = (
            provider_receipt_type == "Balance+TradeVolume+Time+KeyInfo"
        )
        provider_balance_receipt = provider_receipt_type in {
            "Balance+Time+KeyInfo",
            "Balance+TradeVolume+Time+KeyInfo",
        }
        canonical_expected_pair = (
            _canonical_pair(expected_pair) if expected_pair is not None else ""
        )
        if (
            times is None
            or str(receipt.get("provider") or "").strip().lower()
            != "kraken"
            or not source_id.lower().startswith("kraken")
            or not receipt_id
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("account_scope") != "complete"
            or _valid_digest(receipt.get("account_id_hash")) is None
            or receipt.get("api_key_query_funds") is not True
            or receipt.get("api_key_modify_trades") is not True
            or receipt.get("api_key_funding_mutations_absent") is not True
            or not str(receipt.get("api_key_permission_receipt_id") or "").startswith(
                "kraken_api_key_permissions:"
            )
            or not isinstance(raw_balances, Mapping)
            or not raw_balances
            or taker_fee_rate is None
            or taker_fee_rate > 0.1
            or (
                raw_taker_fee_pair is not None
                and not taker_fee_pair
            )
            or (
                taker_fee_pair
                and canonical_expected_pair
                and taker_fee_pair != canonical_expected_pair
            )
            or (
                provider_balance_receipt
                and (
                    not pair_scoped_provider_receipt
                    or not taker_fee_pair
                    or taker_fee_pair != canonical_expected_pair
                )
            )
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
            "taker_fee_rate": taker_fee_rate,
            "taker_fee_pair": taker_fee_pair or None,
        }, ""

    def _validate_hnc_auris_gate_receipt(
        self,
        receipt: Any,
        *,
        symbol: str,
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
        lunar_phase = _finite(
            receipt.get("lunar_phase"), nonnegative=True
        )
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
        gate_symbol = receipt.get("symbol")
        if (
            times is None
            or source_id.lower() != "aureon:hnc_auris_gate"
            or not receipt_id
            or receipt.get("truth_status")
            not in {"real_observed", "real_derived"}
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
            or (
                gate_symbol is not None
                and _canonical_pair(gate_symbol)
                != _canonical_pair(self.BINANCE_TO_KRAKEN[symbol])
            )
            or any(value is None for value in values)
            or earth_coherence > 1.0
            or earth_phase_lock > 1.0
            or cosmic_coherence > 1.0
            or lunar_phase > 1.0
        ):
            return None, "complete_linked_hnc_auris_gate_receipt_required"

        # Canonical equation from Aureon's HNC/Auris forecast gate. It gates
        # action but does not alter the S5 score or profit equations.
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
        self,
        symbol: str,
    ) -> tuple[Optional[Dict[str, Any]], str]:
        market = self.prices.get(symbol)
        now = self._clock()
        if (
            market is None
            or now - market.source_timestamp > MAX_RECEIPT_AGE_SECONDS
            or now - market.received_at > MAX_RECEIPT_AGE_SECONDS
        ):
            return None, "complete_fresh_kraken_market_receipt_required"
        if not callable(self.account_receipt_supplier):
            return None, "kraken_account_receipt_adapter_unavailable"
        try:
            expected_pair = self.BINANCE_TO_KRAKEN[symbol]
            if _accepts_keyword(self.account_receipt_supplier, "pair"):
                raw_account = self.account_receipt_supplier(pair=expected_pair)
            else:
                raw_account = self.account_receipt_supplier()
        except Exception:
            return None, "kraken_account_receipt_unavailable"
        account, reason = self._validate_account_receipt(
            raw_account,
            expected_pair=expected_pair,
        )
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
            symbol=symbol,
            market_receipt_id=market.receipt_id,
            account_receipt_id=str(account["receipt_id"]),
        )
        if gate is None:
            return None, reason
        latest_input_timestamp = max(
            market.source_timestamp,
            float(account["source_timestamp"]),
        )
        if (
            float(gate["source_timestamp"]) + FUTURE_TOLERANCE_SECONDS
            < latest_input_timestamp
        ):
            return None, "causal_hnc_auris_gate_receipt_required"
        if self.network is None:
            return None, "mycelium_network_adapter_unavailable"
        return {
            "market": market,
            "account": account,
            "gate": gate,
        }, ""

    def _pending_for_symbol(self, symbol: str) -> Optional[str]:
        for intent_key, pending in self._pending_intents.items():
            if pending.symbol == symbol:
                return intent_key
        return None

    async def process_market_receipt(
        self,
        symbol: str,
        receipt: Any,
    ) -> Dict[str, Any]:
        """Evaluate one receipt and perform at most one order read-back."""
        self._readback_consumed = False
        accepted = self.ingest_market_receipt(symbol, receipt)
        if accepted.get("status") != "accepted":
            return accepted
        pending_key = self._pending_for_symbol(symbol)
        if pending_key is not None:
            return self._reconcile_pending(pending_key)
        if symbol not in self.prev_prices:
            return self._record_no_data(
                "two_monotonic_market_receipts_required"
            )
        if not self.execution_enabled:
            return self._record_no_data(
                "dry_run_order_not_submitted", status="not_submitted"
            )
        bundle, reason = self._evidence_bundle(symbol)
        if bundle is None:
            return self._record_no_data(reason)
        return await self._check_opportunity(symbol, bundle=bundle)

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
        fee_rate = _finite(account.get("taker_fee_rate"), nonnegative=True)
        if (
            base is None
            or quote is None
            or not isinstance(balances, Mapping)
            or fee_rate is None
        ):
            return False, "unambiguous_pair_account_and_fee_receipt_required"
        if side == "buy":
            available = _finite(balances.get(quote), nonnegative=True)
            required = quantity * price * (1.0 + fee_rate)
            if available is None or available < required:
                return False, "fresh_quote_balance_does_not_cover_order"
        elif side == "sell":
            available = _finite(balances.get(base), nonnegative=True)
            if available is None or available < quantity:
                return False, "fresh_base_balance_does_not_cover_order"
        else:
            return False, "supported_order_side_required"
        return True, ""

    @staticmethod
    def _opportunity_payload(
        opportunity: ConversionOpportunity,
    ) -> Dict[str, Any]:
        return {
            "from_asset": opportunity.from_asset,
            "to_asset": opportunity.to_asset,
            "gross_profit": opportunity.gross_profit,
            "fee": opportunity.fee,
            "net_profit": opportunity.net_profit,
            "price_change": opportunity.price_change,
            "source_timestamp": opportunity.timestamp.timestamp(),
            "opportunity_type": opportunity.opportunity_type,
            "s5_score": opportunity.s5_score,
            "symbol": opportunity.symbol,
            "venue_symbol": opportunity.venue_symbol,
            "quantity": opportunity.quantity,
            "side": opportunity.side,
            "market_receipt_id": opportunity.market_receipt_id,
            "account_receipt_id": opportunity.account_receipt_id,
            "gate_receipt_id": opportunity.gate_receipt_id,
            "truth_status": "real_derived",
            "generated_values": False,
            "accounting_eligible": False,
            "learning_eligible": False,
        }

    async def _check_opportunity(
        self,
        symbol: str,
        *,
        bundle: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate accepted data without treating estimates as accounting."""
        if self.daily_trades >= self.MAX_DAILY_TRADES:
            return self._record_no_data("maximum_daily_fills_reached")
        usd_pnl = self.daily_pnl_by_currency.get("USD")
        if usd_pnl is not None and usd_pnl <= -self.MAX_DAILY_LOSS:
            return self._record_no_data("observed_daily_loss_limit_reached")
        if not self.execution_enabled:
            return self._record_no_data(
                "dry_run_order_not_submitted", status="not_submitted"
            )
        evidence = bundle
        if evidence is None:
            evidence, reason = self._evidence_bundle(symbol)
            if evidence is None:
                return self._record_no_data(reason)
        current = evidence["market"]
        if not isinstance(current, LivePrice) or symbol not in self.prev_prices:
            return self._record_no_data(
                "two_monotonic_market_receipts_required"
            )
        previous_price = _finite(self.prev_prices.get(symbol), positive=True)
        if previous_price is None:
            return self._record_no_data("previous_observed_price_required")
        price_change = (current.price - previous_price) / previous_price

        history = self.price_history.get(symbol, [])
        volatility: Optional[float] = None
        if len(history) >= 10:
            recent_prices = [
                _finite(price, positive=True) for _, price in history[-10:]
            ]
            if all(price is not None for price in recent_prices):
                observed_prices = [float(price) for price in recent_prices]
                minimum = min(observed_prices)
                maximum = max(observed_prices)
                if maximum > minimum:
                    volatility = (maximum - minimum) / minimum

        pair = self.BINANCE_TO_KRAKEN.get(symbol)
        if pair is None:
            return self._record_no_data("same_venue_pair_mapping_required")
        base_asset, quote_asset = self._pair_assets(pair)
        if base_asset is None or quote_asset != "USD":
            return self._record_no_data(
                "unambiguous_usd_quoted_kraken_pair_required"
            )
        account = evidence["account"]
        balances = account.get("balances")
        fee_rate = _finite(account.get("taker_fee_rate"), nonnegative=True)
        if not isinstance(balances, Mapping) or fee_rate is None:
            return self._record_no_data(
                "complete_fresh_kraken_account_receipt_required"
            )
        base_balance = _finite(balances.get(base_asset), nonnegative=True)
        quote_balance = _finite(balances.get(quote_asset), nonnegative=True)
        base_usd_value = (
            self._estimate_usd_value(base_asset, base_balance, current)
            if base_balance is not None
            else None
        )

        opportunity_type: Optional[str] = None
        from_asset: Optional[str] = None
        to_asset: Optional[str] = None
        side: Optional[str] = None
        position_usd: Optional[float] = None
        gross_profit: Optional[float] = None
        fee: Optional[float] = None

        if (
            price_change >= self.MIN_PRICE_CHANGE
            and base_usd_value is not None
            and base_usd_value > 1.0
        ):
            # Preserve the accepted S5 sell sizing equation.
            sell_pct = min(0.25, 0.1 + abs(price_change) * 10.0)
            position_usd = min(
                self.MAX_POSITION_USD,
                max(self.MIN_POSITION_USD, base_usd_value * sell_pct),
            )
            if position_usd > base_usd_value:
                return self._record_no_data(
                    "fresh_base_balance_does_not_cover_order"
                )
            gross_profit = position_usd * abs(price_change)
            fee = position_usd * fee_rate
            opportunity_type = "LABYRINTH_SELL"
            from_asset, to_asset, side = base_asset, quote_asset, "sell"
        elif (
            price_change <= -self.MIN_PRICE_CHANGE
            and quote_balance is not None
            and quote_balance > 0.0
        ):
            size_method = getattr(
                self.network, "s5_calculate_optimal_size", None
            )
            if not callable(size_method):
                return self._record_no_data(
                    "mycelium_s5_sizing_adapter_unavailable"
                )
            try:
                raw_size = size_method(
                    quote_asset, base_asset, abs(price_change) * 100.0
                )
            except Exception:
                return self._record_no_data(
                    "mycelium_s5_sizing_evaluation_failed"
                )
            observed_size = _finite(raw_size, positive=True)
            if observed_size is None:
                return self._record_no_data(
                    "finite_mycelium_s5_position_size_required"
                )
            # Preserve the accepted S5 buy sizing equation.
            position_usd = min(
                self.MAX_POSITION_USD,
                max(self.MIN_POSITION_USD, observed_size),
            )
            gross_profit = position_usd * abs(price_change)
            fee = position_usd * fee_rate
            opportunity_type = "BUY_LOW"
            from_asset, to_asset, side = quote_asset, base_asset, "buy"
        elif (
            volatility is not None
            and volatility >= self.MIN_VOLATILITY
            and base_usd_value is not None
            and base_usd_value > 1.0
        ):
            position_usd = min(
                self.MAX_POSITION_USD,
                max(self.MIN_POSITION_USD, base_usd_value * 0.1),
            )
            if position_usd > base_usd_value:
                return self._record_no_data(
                    "fresh_base_balance_does_not_cover_order"
                )
            # Preserve the accepted S5 volatility opportunity equations.
            gross_profit = position_usd * volatility * 0.5
            fee = position_usd * fee_rate * 2.0
            opportunity_type = "VOLATILITY_SCALP"
            from_asset, to_asset, side = base_asset, quote_asset, "sell"
        else:
            return self._record_no_data(
                "no_receipt_supported_s5_opportunity"
            )

        values = (position_usd, gross_profit, fee)
        if any(_finite(value, nonnegative=True) is None for value in values):
            return self._record_no_data(
                "finite_receipt_derived_opportunity_values_required"
            )
        net_profit = float(gross_profit) - float(fee)
        if net_profit < self.MIN_PROFIT:
            return self._record_no_data(
                "receipt_derived_profit_below_configured_minimum"
            )
        quantity = float(position_usd) / current.price
        capacity, reason = self._account_has_capacity(
            account,
            pair=pair,
            side=str(side),
            quantity=quantity,
            price=current.price,
        )
        if not capacity:
            return self._record_no_data(reason)
        opportunity = ConversionOpportunity(
            from_asset=str(from_asset),
            to_asset=str(to_asset),
            gross_profit=float(gross_profit),
            fee=float(fee),
            net_profit=net_profit,
            price_change=price_change,
            timestamp=datetime.fromtimestamp(
                current.source_timestamp, tz=timezone.utc
            ),
            opportunity_type=str(opportunity_type),
            s5_score=0.0,
            symbol=symbol,
            venue_symbol=pair,
            quantity=quantity,
            side=str(side),
            market_receipt_id=current.receipt_id,
            account_receipt_id=str(account["receipt_id"]),
            gate_receipt_id=str(evidence["gate"]["receipt_id"]),
        )
        return await self._process_opportunity(opportunity, bundle=evidence)

    async def _process_opportunity(
        self,
        opportunity: ConversionOpportunity,
        *,
        bundle: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Apply S5 decision logic without committing estimates."""
        pending_key = self._pending_for_symbol(opportunity.symbol)
        if pending_key is not None:
            return self._reconcile_pending(pending_key)
        score_method = getattr(
            self.network, "s5_adaptive_labyrinth_score", None
        )
        decision_method = getattr(self.network, "should_convert", None)
        if not callable(score_method) or not callable(decision_method):
            return self._record_no_data(
                "mycelium_s5_decision_adapters_unavailable"
            )
        path_key = f"{opportunity.from_asset}->{opportunity.to_asset}"
        try:
            raw_score = score_method(path_key, opportunity.net_profit)
            raw_decision = decision_method(
                opportunity.from_asset,
                opportunity.to_asset,
                opportunity.net_profit,
            )
        except Exception:
            return self._record_no_data(
                "mycelium_s5_decision_evaluation_failed"
            )
        score = _finite(raw_score)
        if score is None or type(raw_decision) is not bool:
            return self._record_no_data(
                "finite_explicit_mycelium_s5_decision_required"
            )
        opportunity.s5_score = score
        if score <= 0.0 or raw_decision is not True:
            return {
                "status": "s5_rejected",
                "data_status": "live",
                "truth_status": "real_derived",
                "generated_values": False,
                "source_receipt_ids": [
                    opportunity.market_receipt_id,
                    opportunity.account_receipt_id,
                    opportunity.gate_receipt_id,
                ],
                "action": False,
                "accounting": False,
                "learning": False,
            }
        return self._submit_intent(opportunity, bundle=bundle)

    def _durable_state_anchor(self) -> Optional[str]:
        try:
            state = self._read_verified_intent_state()
            return (
                str(state['state_hash'])
                if isinstance(state, Mapping) else None
            )
        except (OSError, TypeError, ValueError):
            return None

    def _exact_add_order_body(
        self,
        opportunity: ConversionOpportunity,
        client_order_id: str,
    ) -> tuple[Optional[Dict[str, str]], str]:
        prepare = getattr(
            self.kraken,
            'prepare_economic_market_order',
            None,
        )
        body: Any = None
        if callable(prepare):
            try:
                body = prepare(
                    symbol=opportunity.venue_symbol,
                    side=opportunity.side,
                    quantity=opportunity.quantity,
                    client_order_id=client_order_id,
                )
            except Exception:
                return None, 'exact_kraken_add_order_body_unavailable'
        else:
            pairs = getattr(self.kraken, '_pairs_cache', None)
            alt_to_internal = getattr(self.kraken, '_alt_to_int', None)
            if not isinstance(pairs, Mapping) or not isinstance(
                alt_to_internal, Mapping
            ):
                return None, 'exact_kraken_add_order_body_unavailable'
            requested_pair = opportunity.venue_symbol.strip().upper()
            provider_pair = alt_to_internal.get(requested_pair)
            if provider_pair is None and requested_pair in pairs:
                provider_pair = requested_pair
            pair_info = pairs.get(provider_pair)
            if (
                not isinstance(provider_pair, str)
                or not provider_pair
                or not isinstance(pair_info, Mapping)
            ):
                return None, 'exact_kraken_add_order_body_unavailable'
            try:
                lot_decimals = int(pair_info.get('lot_decimals', 8))
                minimum = float(pair_info.get('ordermin', 0.0001))
                rounded = round(float(opportunity.quantity), lot_decimals)
                if lot_decimals < 0 or rounded < minimum:
                    return None, 'kraken_order_volume_below_provider_minimum'
                formatter = getattr(self.kraken, '_format_order_value', None)
                volume = (
                    formatter(rounded)
                    if callable(formatter)
                    else _canonical_decimal_text(rounded, positive=True)
                )
            except (TypeError, ValueError):
                return None, 'exact_kraken_add_order_body_unavailable'
            body = {
                'pair': provider_pair,
                'type': opportunity.side,
                'ordertype': 'market',
                'volume': volume,
                'cl_ord_id': client_order_id,
            }
        if not isinstance(body, Mapping) or set(body) != {
            'pair',
            'type',
            'ordertype',
            'volume',
            'cl_ord_id',
        }:
            return None, 'exact_kraken_add_order_body_unavailable'
        normalized = {name: str(value) for name, value in body.items()}
        try:
            normalized['volume'] = _canonical_decimal_text(
                normalized['volume'], positive=True
            )
        except ValueError:
            return None, 'exact_kraken_add_order_body_unavailable'
        if (
            not normalized['pair']
            or normalized['type'] != opportunity.side
            or normalized['ordertype'] != 'market'
            or normalized['cl_ord_id'] != client_order_id
        ):
            return None, 'exact_kraken_add_order_body_unavailable'
        return normalized, ''

    def _economic_context(
        self,
        opportunity: ConversionOpportunity,
        bundle: Mapping[str, Any],
        state_anchor: str,
    ) -> tuple[Optional[Dict[str, Any]], str]:
        market = bundle.get('market')
        account = bundle.get('account')
        gate = bundle.get('gate')
        if (
            market is None
            or any(
                not hasattr(market, name)
                for name in (
                    'receipt_id',
                    'source_id',
                    'source_timestamp',
                    'venue_symbol',
                    'price',
                    'bid',
                    'ask',
                )
            )
            or not isinstance(account, Mapping)
            or not isinstance(gate, Mapping)
            or _valid_digest(state_anchor) is None
        ):
            return None, 'complete_economic_provider_context_required'
        account_hash = _valid_digest(account.get('account_id_hash'))
        hnc_receipt_id = str(gate.get('hnc_receipt_id') or '').strip()
        auris_receipt_id = str(gate.get('auris_receipt_id') or '').strip()
        authorization_receipt_id = str(
            gate.get('authorization_receipt_id') or ''
        ).strip()
        cycle_id = str(gate.get('cycle_id') or '').strip()
        input_ids = account.get('input_receipt_ids')
        provider_inputs = (
            [str(value).strip() for value in input_ids]
            if isinstance(input_ids, (list, tuple))
            else []
        )
        gate_links = gate.get('input_receipt_ids')
        linked = (
            [str(value).strip() for value in gate_links]
            if isinstance(gate_links, (list, tuple))
            else []
        )
        if (
            account_hash is None
            or account.get('provider_receipt_type')
            != 'Balance+TradeVolume+Time+KeyInfo'
            or len(provider_inputs) != 4
            or any(not value for value in provider_inputs)
            or len(provider_inputs) != len(set(provider_inputs))
            or not hnc_receipt_id.startswith('hnc:live_field:')
            or not auris_receipt_id.startswith('auris:cosmic_state:')
            or hnc_receipt_id not in linked
            or auris_receipt_id not in linked
            or not authorization_receipt_id
            or not cycle_id
            or str(gate.get('environment') or '').strip().lower() != 'live'
        ):
            return None, 'complete_economic_provider_context_required'
        balances = account.get('balances')
        base_asset, _ = self._pair_assets(opportunity.venue_symbol)
        if not isinstance(balances, Mapping) or base_asset is None:
            return None, 'complete_economic_provider_context_required'
        try:
            canonical_balances = {
                str(asset): _canonical_decimal_text(amount)
                for asset, amount in sorted(
                    balances.items(), key=lambda item: str(item[0])
                )
            }
            fee_rate = _canonical_decimal_text(
                account.get('taker_fee_rate')
            )
            pre_entry_base_balance = _canonical_decimal_text(
                balances.get(base_asset, 0)
            )
            provider_timestamp = _canonical_decimal_text(
                min(
                    market.source_timestamp,
                    float(account['source_timestamp']),
                )
            )
        except (KeyError, TypeError, ValueError):
            return None, 'complete_economic_provider_context_required'
        provider_receipt_ids = tuple(
            sorted(
                {
                    market.receipt_id,
                    str(account.get('receipt_id') or ''),
                    *provider_inputs,
                }
            )
        )
        if any(not value for value in provider_receipt_ids):
            return None, 'complete_economic_provider_context_required'
        provider_moment = {
            'venue': 'kraken',
            'state_anchor': state_anchor,
            'provider_receipt_ids': list(provider_receipt_ids),
            'market': {
                'receipt_id': market.receipt_id,
                'source_id': market.source_id,
                'source_timestamp': _canonical_decimal_text(
                    market.source_timestamp
                ),
                'pair': market.venue_symbol,
                'price': _canonical_decimal_text(market.price),
                'bid': _canonical_decimal_text(market.bid),
                'ask': _canonical_decimal_text(market.ask),
            },
            'account': {
                'receipt_id': str(account['receipt_id']),
                'source_id': str(account.get('source_id') or ''),
                'source_timestamp': _canonical_decimal_text(
                    account['source_timestamp']
                ),
                'fee_pair': str(account.get('taker_fee_pair') or ''),
                'taker_fee_rate': fee_rate,
                'balances': canonical_balances,
            },
        }
        return {
            'account_id_hash': account_hash,
            'authorization_receipt_id': authorization_receipt_id,
            'cycle_id': cycle_id,
            'position_receipt_id': str(account['receipt_id']),
            'hnc_receipt_id': hnc_receipt_id,
            'auris_receipt_id': auris_receipt_id,
            'provider_receipt_ids': provider_receipt_ids,
            'provider_moment_digest': _canonical_hash(provider_moment),
            'provider_source_timestamp': provider_timestamp,
            'pre_entry_base_balance': pre_entry_base_balance,
        }, ''

    @staticmethod
    def _entry_economic_intent(
        body: Mapping[str, str],
        context: Mapping[str, Any],
        *,
        side: str,
    ) -> EconomicIntent:
        return EconomicIntent.build(
            venue='kraken',
            environment='live',
            account_id_hash=str(context['account_id_hash']),
            method=KRAKEN_ADD_ORDER_METHOD,
            path=KRAKEN_ADD_ORDER_PATH,
            operation='MARKET_ORDER',
            purpose='ENTRY' if side == 'buy' else 'POSITION_REDUCTION',
            symbol=str(body['pair']),
            side=str(body['type']).upper(),
            order_type=str(body['ordertype']).upper(),
            quantity=str(body['volume']),
            quote_quantity=None,
            limit_price=None,
            stop_price=None,
            take_profit=None,
            reduce_only=False,
            client_order_id=str(body['cl_ord_id']),
            authorization_receipt_id=str(
                context['authorization_receipt_id']
            ),
            cycle_id=str(context['cycle_id']),
            position_receipt_id=str(context['position_receipt_id']),
            hnc_receipt_id=str(context['hnc_receipt_id']),
            auris_receipt_id=str(context['auris_receipt_id']),
            provider_receipt_ids=context['provider_receipt_ids'],
            provider_moment_digest=str(context['provider_moment_digest']),
            provider_source_timestamp=str(
                context['provider_source_timestamp']
            ),
            body=body,
            body_bindings={
                'client_order_id': '/cl_ord_id',
                'order_type': '/ordertype',
                'quantity': '/volume',
                'side': '/type',
                'symbol': '/pair',
            },
        )

    @staticmethod
    def _contingency_scope(
        intent: EconomicIntent,
        containment_client_order_id: str,
    ) -> ContingencyWarrantScope:
        return ContingencyWarrantScope.build(
            venue=intent.venue,
            environment=intent.environment,
            account_id_hash=intent.account_id_hash,
            symbol=intent.symbol,
            exposure_side='LONG',
            reduction_side='SELL',
            method=intent.method,
            path=intent.path,
            order_type=intent.order_type,
            max_reduce_quantity=str(intent.quantity),
            entry_intent_digest=intent.intent_digest,
            entry_client_order_id=intent.client_order_id,
            containment_client_order_id=containment_client_order_id,
            authorization_receipt_id=intent.authorization_receipt_id,
            cycle_id=intent.cycle_id,
            pre_entry_position_receipt_id=intent.position_receipt_id,
            provider_reduce_only_supported=False,
            hnc_receipt_id=intent.hnc_receipt_id,
            auris_receipt_id=intent.auris_receipt_id,
            provider_receipt_ids=intent.provider_receipt_ids,
            provider_moment_digest=intent.provider_moment_digest,
            provider_source_timestamp=intent.provider_source_timestamp,
        )

    def _close_without_submission(
        self,
        pending: PendingIntent,
        reason: str,
    ) -> Dict[str, Any]:
        pending.state = 'governance_blocked_no_submission'
        self._closed_intents[pending.intent_key] = {
            **asdict(pending),
            'reason': reason,
            'truth_status': 'no_data',
            'generated_values': False,
        }
        self._pending_intents.pop(pending.intent_key, None)
        if not self._persist_intent_state():
            self._closed_intents.pop(pending.intent_key, None)
            self._pending_intents[pending.intent_key] = pending
            return self._record_no_data(
                'governance_blocked_state_write_failed',
                intent_key=pending.intent_key,
            )
        return self._record_no_data(reason, intent_key=pending.intent_key)

    def _submit_intent(
        self,
        opportunity: ConversionOpportunity,
        *,
        bundle: Mapping[str, Any],
    ) -> Dict[str, Any]:
        try:
            with self._intent_store_lock():
                self._load_intent_state()
                return self._submit_intent_locked(
                    opportunity,
                    bundle=bundle,
                )
        except (OSError, BlockingIOError):
            return self._record_no_data(
                'intent_store_lock_unavailable'
            )

    def _submit_intent_locked(
        self,
        opportunity: ConversionOpportunity,
        *,
        bundle: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if self.dry_run:
            return self._record_no_data(
                "dry_run_order_not_submitted", status="not_submitted"
            )
        if self._state_load_error is not None:
            return self._record_no_data(
                "valid_intent_state_readback_required"
            )
        if self.intent_store_path is None:
            return self._record_no_data(
                "durable_intent_store_required_before_live_submission"
            )
        boundary = self.economic_governance_boundary
        if not isinstance(boundary, EconomicGovernanceBoundary):
            return self._record_no_data(
                "economic_governance_boundary_required"
            )
        recovery = self.contingency_recovery
        if (
            not isinstance(recovery, DurableContingencyRecovery)
            or recovery.boundary is not boundary
        ):
            return self._record_no_data(
                'trusted_contingency_recovery_adapter_required'
            )
        existing = self._pending_for_symbol(opportunity.symbol)
        if existing is not None:
            return self._record_no_data(
                "unresolved_intent_suppresses_duplicate_submission",
                status="pending_reconciliation",
                intent_key=existing,
            )
        place_order = getattr(self.kraken, "place_market_order", None)
        if not callable(place_order):
            return self._record_no_data("kraken_order_adapter_unavailable")
        intent_key = (
            f"conversion:{opportunity.symbol}:{opportunity.side}:"
            f"{opportunity.market_receipt_id}"
        )
        if intent_key in self._closed_intents:
            return self._record_no_data(
                "closed_intent_client_order_id_reuse_blocked",
                intent_key=intent_key,
            )
        supports_client_order_id = _accepts_keyword(
            place_order,
            "client_order_id",
        )
        if not supports_client_order_id:
            return self._record_no_data(
                "kraken_client_order_id_binding_required"
            )
        client_order_id = _client_order_id(intent_key)
        body, reason = self._exact_add_order_body(
            opportunity,
            client_order_id,
        )
        if body is None:
            return self._record_no_data(reason, intent_key=intent_key)
        context, reason = self._economic_context(
            opportunity,
            bundle,
            "0" * _DIGEST_LENGTH,
        )
        if context is None:
            return self._record_no_data(reason, intent_key=intent_key)
        pending = PendingIntent(
            intent_key=intent_key,
            client_order_id=client_order_id,
            symbol=opportunity.symbol,
            venue_symbol=opportunity.venue_symbol,
            side=opportunity.side,
            requested_quantity=opportunity.quantity,
            opportunity=self._opportunity_payload(opportunity),
            market_receipt_id=str(bundle["market"].receipt_id),
            account_receipt_id=str(bundle["account"]["receipt_id"]),
            gate_receipt_id=str(bundle["gate"]["receipt_id"]),
            state="governance_pending",
            order_id=None,
            pre_entry_base_balance=str(
                context["pre_entry_base_balance"]
            ),
        )
        self._pending_intents[intent_key] = pending
        if not self._persist_intent_state():
            self._pending_intents.pop(intent_key, None)
            return self._record_no_data(
                "durable_intent_latch_write_failed_before_submission"
            )
        state_anchor = self._durable_state_anchor()
        if state_anchor is None:
            return self._close_without_submission(
                pending,
                "durable_intent_latch_readback_required",
            )
        context, reason = self._economic_context(
            opportunity,
            bundle,
            state_anchor,
        )
        if context is None:
            return self._close_without_submission(pending, reason)
        try:
            economic_intent = self._entry_economic_intent(
                body,
                context,
                side=opportunity.side,
            )
        except (KeyError, TypeError, ValueError):
            return self._close_without_submission(
                pending,
                "valid_exact_economic_intent_required",
            )
        pending.durable_state_anchor = state_anchor
        pending.economic_intent_digest = economic_intent.intent_digest
        pending.economic_body_digest = economic_intent.body_digest
        pending.provider_moment_digest = (
            economic_intent.provider_moment_digest
        )
        warrant: Optional[ContingencyWarrant] = None
        scope: Optional[ContingencyWarrantScope] = None
        recovery_reference: Optional[
            DurableContingencyRecordRef
        ] = None
        try:
            permit = boundary.prepare_mutation(economic_intent)
            if opportunity.side == "buy":
                containment_client_order_id = _client_order_id(
                    f"{intent_key}:containment"
                )
                scope = self._contingency_scope(
                    economic_intent,
                    containment_client_order_id,
                )
                warrant = boundary.approve_contingency_warrant(scope)
                pending.containment_client_order_id = (
                    containment_client_order_id
                )
                pending.contingency_warrant_id = warrant.warrant_id
                pending.contingency_scope_digest = scope.scope_digest
                recovery_reference = recovery.register(
                    warrant,
                    scope,
                    entry_state_anchor=state_anchor,
                )
                pending.contingency_warrant = asdict(warrant)
                pending.contingency_scope = scope.payload()
                pending.contingency_recovery_record_digest = (
                    recovery_reference.record_digest
                )
                pending.contingency_recovery_entry_state_anchor = (
                    recovery_reference.entry_state_anchor
                )
                pending.contingency_recovery_route_binding_anchor = (
                    recovery_reference.bound_route_state_anchor
                )
        except (EconomicGovernanceBlocked, TypeError, ValueError):
            return self._close_without_submission(
                pending,
                "economic_governance_not_accepted",
            )
        pending.governance_permit_id = permit.permit_id
        pending.governance_dual_receipt_id = permit.dual_receipt_id
        pending.governance_proposal_digest = permit.proposal_digest
        pending.state = "submission_in_progress"
        if not self._persist_intent_state():
            return self._close_without_submission(
                pending,
                "governance_lineage_write_failed_before_submission",
            )
        if recovery_reference is not None:
            try:
                recovery.bind_route_state(recovery_reference)
                recovery.verify_route_binding(recovery_reference)
            except Exception:
                return self._close_without_submission(
                    pending,
                    'reciprocal_contingency_binding_required',
                )
        order_arguments = {
            "symbol": opportunity.venue_symbol,
            "side": opportunity.side,
            "quantity": opportunity.quantity,
            "client_order_id": client_order_id,
        }
        try:
            acknowledgement = boundary.consume_and_call(
                permit,
                method=KRAKEN_ADD_ORDER_METHOD,
                path=KRAKEN_ADD_ORDER_PATH,
                body=body,
                transport=lambda: place_order(**order_arguments),
            )
            pending.governance_permit_consumed = True
        except EconomicGovernanceBlocked:
            pending.governance_permit_consumed = True
            return self._close_without_submission(
                pending,
                "economic_permit_rejected_before_transport",
            )
        except Exception:
            pending.governance_permit_consumed = True
            pending.state = "ambiguous_submission"
            self._persist_intent_state()
            return self._record_no_data(
                "ambiguous_submission_requires_external_reconciliation",
                status="pending_reconciliation",
                intent_key=intent_key,
            )
        if (
            isinstance(acknowledgement, Mapping)
            and acknowledgement.get("data_status") == "not_submitted"
            and acknowledgement.get("generated_values") is False
        ):
            pending.state = "provider_not_submitted"
            self._closed_intents[intent_key] = {
                **asdict(pending),
                "truth_status": "no_data",
                "generated_values": False,
            }
            self._pending_intents.pop(intent_key, None)
            if not self._persist_intent_state():
                self._closed_intents.pop(intent_key, None)
                self._pending_intents[intent_key] = pending
                pending.state = "ambiguous_submission"
                return self._record_no_data(
                    "provider_non_submission_state_write_failed",
                    status="pending_reconciliation",
                    intent_key=intent_key,
                )
            return self._record_no_data(
                "provider_dry_run_order_not_submitted",
                status="not_submitted",
                intent_key=intent_key,
            )
        order_id = (
            str(acknowledgement.get("orderId") or "").strip()
            if isinstance(acknowledgement, Mapping)
            else ""
        )
        acknowledged_client_order_id = (
            _validated_client_order_id(acknowledgement.get("cl_ord_id"))
            if isinstance(acknowledgement, Mapping)
            else None
        )
        pending.order_id = order_id or None
        pending.state = (
            "pending_reconciliation" if order_id else "ambiguous_submission"
        )
        if (
            acknowledged_client_order_id != client_order_id
        ):
            pending.state = "ambiguous_submission"
        persisted = self._persist_intent_state()
        if not persisted:
            return self._record_no_data(
                "unresolved_state_write_failed_after_submission",
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        if not order_id:
            return self._record_no_data(
                "ambiguous_submission_requires_external_reconciliation",
                status="pending_reconciliation",
                intent_key=intent_key,
            )
        if pending.state == "ambiguous_submission":
            return self._record_no_data(
                "provider_client_order_id_link_required",
                status="pending_reconciliation",
                order_id=order_id,
                intent_key=intent_key,
            )
        return self._record_no_data(
            "submission_acknowledged_terminal_receipt_required",
            status="pending_reconciliation",
            order_id=order_id,
            intent_key=intent_key,
        )

    def submit_preapproved_contingency_reduction(
        self,
        *,
        entry_order_id: str,
    ) -> Dict[str, Any]:
        try:
            with self._intent_store_lock():
                self._load_intent_state()
                return (
                    self._submit_preapproved_contingency_reduction_locked(
                        entry_order_id=entry_order_id,
                    )
                )
        except (OSError, BlockingIOError):
            return self._record_no_data(
                'intent_store_lock_unavailable'
            )

    def _submit_preapproved_contingency_reduction_locked(
        self,
        *,
        entry_order_id: str,
    ) -> Dict[str, Any]:
        if self.dry_run:
            return self._record_no_data(
                'dry_run_contingency_not_submitted',
                status='not_submitted',
            )
        boundary = self.economic_governance_boundary
        if not isinstance(boundary, EconomicGovernanceBoundary):
            return self._record_no_data(
                'economic_governance_boundary_required'
            )
        recovery = self.contingency_recovery
        if (
            not isinstance(recovery, DurableContingencyRecovery)
            or recovery.boundary is not boundary
        ):
            return self._record_no_data(
                'trusted_contingency_recovery_adapter_required'
            )
        entry_id = str(entry_order_id or '').strip()
        fill = next(
            (
                item
                for item in self._settled_fills
                if str(item.get('order_id') or '') == entry_id
            ),
            None,
        )
        if (
            not isinstance(fill, Mapping)
            or fill.get('side') != 'buy'
            or fill.get('truth_status') != 'real_observed'
        ):
            return self._record_no_data(
                'observed_long_entry_fill_required_for_contingency'
            )
        entry_intent_digest = _valid_digest(
            fill.get('economic_intent_digest')
        )
        if entry_intent_digest is None:
            return self._record_no_data(
                'entry_economic_lineage_required_for_contingency'
            )
        intent_key = f'containment:{entry_intent_digest}'
        if (
            intent_key in self._pending_intents
            or intent_key in self._closed_intents
        ):
            return self._record_no_data(
                'contingency_attempt_already_recorded',
                intent_key=intent_key,
            )
        try:
            recovery_reference = DurableContingencyRecordRef(
                record_digest=str(
                    fill['contingency_recovery_record_digest']
                ),
                entry_state_anchor=str(
                    fill['contingency_recovery_entry_state_anchor']
                ),
                bound_route_state_anchor=str(
                    fill[
                        'contingency_recovery_route_binding_anchor'
                    ]
                ),
            )
            material = recovery.material_for_recovery(
                recovery_reference
            )
        except (KeyError, TypeError, ValueError, EconomicGovernanceBlocked):
            return self._record_no_data(
                'verified_durable_contingency_warrant_required'
            )
        warrant, scope = material.warrant, material.scope
        if (
            fill.get('contingency_warrant') != asdict(warrant)
            or fill.get('contingency_scope') != scope.payload()
            or scope.entry_intent_digest != entry_intent_digest
        ):
            return self._record_no_data(
                'reciprocal_route_recovery_material_mismatch'
            )
        place_order = getattr(self.kraken, 'place_market_order', None)
        if (
            not callable(place_order)
            or not _accepts_keyword(place_order, 'client_order_id')
        ):
            return self._record_no_data(
                'kraken_client_order_id_binding_required'
            )
        if not callable(self.account_receipt_supplier):
            return self._record_no_data(
                'post_entry_account_receipt_required'
            )
        pair = str(fill.get('venue_symbol') or '').strip()
        try:
            if _accepts_keyword(self.account_receipt_supplier, 'pair'):
                raw_account = self.account_receipt_supplier(pair=pair)
            else:
                raw_account = self.account_receipt_supplier()
        except Exception:
            return self._record_no_data(
                'post_entry_account_receipt_required'
            )
        account, reason = self._validate_account_receipt(
            raw_account,
            expected_pair=pair,
        )
        market = self.prices.get(str(fill.get('symbol') or ''))
        now = self._clock()
        if (
            account is None
            or market is None
            or now - market.source_timestamp > MAX_RECEIPT_AGE_SECONDS
            or now - market.received_at > MAX_RECEIPT_AGE_SECONDS
        ):
            return self._record_no_data(
                reason or 'fresh_post_entry_provider_moment_required'
            )
        input_ids = account.get('input_receipt_ids')
        provider_inputs = (
            [str(value).strip() for value in input_ids]
            if isinstance(input_ids, (list, tuple))
            else []
        )
        account_hash = _valid_digest(account.get('account_id_hash'))
        base_asset, quote_asset = self._pair_assets(pair)
        balances = account.get('balances')
        if (
            account_hash != scope.account_id_hash
            or account.get('provider_receipt_type')
            != 'Balance+TradeVolume+Time+KeyInfo'
            or len(provider_inputs) != 4
            or len(provider_inputs) != len(set(provider_inputs))
            or any(not value for value in provider_inputs)
            or base_asset is None
            or quote_asset is None
            or not isinstance(balances, Mapping)
        ):
            return self._record_no_data(
                'complete_post_entry_position_receipt_required'
            )
        try:
            current_balance = Decimal(
                _canonical_decimal_text(balances.get(base_asset, 0))
            )
            pre_entry_balance = Decimal(
                _canonical_decimal_text(fill.get('pre_entry_base_balance'))
            )
            filled_quantity = Decimal(
                _canonical_decimal_text(
                    fill.get('filled_qty'), positive=True
                )
            )
            observed_increase = current_balance - pre_entry_balance
            reduction_quantity = min(
                filled_quantity,
                observed_increase,
                Decimal(scope.max_reduce_quantity),
            )
        except (InvalidOperation, TypeError, ValueError):
            return self._record_no_data(
                'complete_post_entry_position_receipt_required'
            )
        if reduction_quantity <= 0:
            return self._record_no_data(
                'positive_observed_post_entry_exposure_required'
            )
        quantity_text = _canonical_decimal_text(
            reduction_quantity,
            positive=True,
        )
        containment_opportunity = ConversionOpportunity(
            from_asset=base_asset,
            to_asset=quote_asset,
            gross_profit=0.0,
            fee=0.0,
            net_profit=0.0,
            price_change=0.0,
            timestamp=datetime.fromtimestamp(
                market.source_timestamp,
                tz=timezone.utc,
            ),
            opportunity_type='PREAPPROVED_CONTAINMENT_REDUCTION',
            s5_score=0.0,
            symbol=str(fill['symbol']),
            venue_symbol=pair,
            quantity=float(reduction_quantity),
            side='sell',
            market_receipt_id=market.receipt_id,
            account_receipt_id=str(account['receipt_id']),
            gate_receipt_id=str(fill['gate_receipt_id']),
        )
        body, reason = self._exact_add_order_body(
            containment_opportunity,
            scope.containment_client_order_id,
        )
        if body is None or Decimal(body['volume']) > reduction_quantity:
            return self._record_no_data(
                reason or 'exact_capped_containment_body_required'
            )
        pending = PendingIntent(
            intent_key=intent_key,
            client_order_id=scope.containment_client_order_id,
            symbol=str(fill['symbol']),
            venue_symbol=pair,
            side='sell',
            requested_quantity=float(body['volume']),
            opportunity=self._opportunity_payload(
                containment_opportunity
            ),
            market_receipt_id=market.receipt_id,
            account_receipt_id=str(account['receipt_id']),
            gate_receipt_id=str(fill['gate_receipt_id']),
            state='governance_pending',
            order_id=None,
            contingency_warrant_id=warrant.warrant_id,
            contingency_scope_digest=scope.scope_digest,
            contingency_warrant=asdict(warrant),
            contingency_scope=scope.payload(),
            contingency_recovery_record_digest=(
                recovery_reference.record_digest
            ),
            contingency_recovery_entry_state_anchor=(
                recovery_reference.entry_state_anchor
            ),
            contingency_recovery_route_binding_anchor=(
                recovery_reference.bound_route_state_anchor
            ),
            containment_client_order_id=(
                scope.containment_client_order_id
            ),
            pre_entry_base_balance=_canonical_decimal_text(
                pre_entry_balance
            ),
        )
        self._pending_intents[intent_key] = pending
        if not self._persist_intent_state():
            self._pending_intents.pop(intent_key, None)
            return self._record_no_data(
                'durable_containment_latch_write_failed'
            )
        state_anchor = self._durable_state_anchor()
        if state_anchor is None:
            return self._close_without_submission(
                pending,
                'durable_containment_latch_readback_required',
            )
        try:
            canonical_balances = {
                str(asset): _canonical_decimal_text(amount)
                for asset, amount in sorted(
                    balances.items(), key=lambda item: str(item[0])
                )
            }
            provider_timestamp = _canonical_decimal_text(
                min(
                    market.source_timestamp,
                    float(account['source_timestamp']),
                )
            )
        except (KeyError, TypeError, ValueError):
            return self._close_without_submission(
                pending,
                'complete_post_entry_position_receipt_required',
            )
        provider_receipt_ids = tuple(
            sorted(
                {
                    market.receipt_id,
                    str(account['receipt_id']),
                    str(fill['receipt_id']),
                    *provider_inputs,
                }
            )
        )
        provider_moment_digest = _canonical_hash(
            {
                'venue': 'kraken',
                'state_anchor': state_anchor,
                'entry_receipt_id': str(fill['receipt_id']),
                'provider_receipt_ids': list(provider_receipt_ids),
                'market_receipt_id': market.receipt_id,
                'market_source_timestamp': _canonical_decimal_text(
                    market.source_timestamp
                ),
                'position_receipt_id': str(account['receipt_id']),
                'position_source_timestamp': _canonical_decimal_text(
                    account['source_timestamp']
                ),
                'balances': canonical_balances,
                'taker_fee_rate': _canonical_decimal_text(
                    account['taker_fee_rate']
                ),
            }
        )
        try:
            intent = EconomicIntent.build(
                venue='kraken',
                environment='live',
                account_id_hash=scope.account_id_hash,
                method=KRAKEN_ADD_ORDER_METHOD,
                path=KRAKEN_ADD_ORDER_PATH,
                operation='MARKET_ORDER',
                purpose='CONTAINMENT_REDUCTION',
                symbol=str(body['pair']),
                side='SELL',
                order_type='MARKET',
                quantity=str(body['volume']),
                quote_quantity=None,
                limit_price=None,
                stop_price=None,
                take_profit=None,
                reduce_only=True,
                client_order_id=scope.containment_client_order_id,
                authorization_receipt_id=(
                    scope.authorization_receipt_id
                ),
                cycle_id=scope.cycle_id,
                position_receipt_id=str(account['receipt_id']),
                parent_intent_digest=entry_intent_digest,
                entry_receipt_id=str(fill['receipt_id']),
                position_side='LONG',
                observed_exposure_quantity=quantity_text,
                hnc_receipt_id=scope.hnc_receipt_id,
                auris_receipt_id=scope.auris_receipt_id,
                provider_receipt_ids=provider_receipt_ids,
                provider_moment_digest=provider_moment_digest,
                provider_source_timestamp=provider_timestamp,
                body=body,
                body_bindings={
                    'client_order_id': '/cl_ord_id',
                    'order_type': '/ordertype',
                    'quantity': '/volume',
                    'side': '/type',
                    'symbol': '/pair',
                },
            )
            recovered = recovery.prepare_reduction(
                recovery_reference,
                intent,
            )
            permit = recovered.permit
        except (EconomicGovernanceBlocked, TypeError, ValueError):
            return self._close_without_submission(
                pending,
                'preapproved_contingency_not_applicable',
            )
        pending.durable_state_anchor = state_anchor
        pending.economic_intent_digest = intent.intent_digest
        pending.economic_body_digest = intent.body_digest
        pending.provider_moment_digest = provider_moment_digest
        pending.governance_permit_id = permit.permit_id
        pending.governance_dual_receipt_id = permit.dual_receipt_id
        pending.governance_proposal_digest = permit.proposal_digest
        pending.state = 'submission_in_progress'
        if not self._persist_intent_state():
            return self._close_without_submission(
                pending,
                'containment_lineage_write_failed_before_submission',
            )
        order_arguments = {
            'symbol': pair,
            'side': 'sell',
            'quantity': float(body['volume']),
            'client_order_id': scope.containment_client_order_id,
        }
        try:
            acknowledgement = recovery.consume_and_call(
                recovered,
                method=KRAKEN_ADD_ORDER_METHOD,
                path=KRAKEN_ADD_ORDER_PATH,
                body=body,
                transport=lambda: place_order(**order_arguments),
            )
            pending.governance_permit_consumed = True
        except EconomicGovernanceBlocked:
            pending.governance_permit_consumed = True
            return self._close_without_submission(
                pending,
                'contingency_permit_rejected_before_transport',
            )
        except Exception:
            pending.governance_permit_consumed = True
            pending.state = 'ambiguous_submission'
            self._persist_intent_state()
            return self._record_no_data(
                'ambiguous_containment_requires_external_reconciliation',
                status='pending_reconciliation',
                intent_key=intent_key,
            )
        order_id = (
            str(acknowledgement.get('orderId') or '').strip()
            if isinstance(acknowledgement, Mapping)
            else ''
        )
        acknowledged_client_order_id = (
            _validated_client_order_id(
                acknowledgement.get('cl_ord_id')
            )
            if isinstance(acknowledgement, Mapping)
            else None
        )
        pending.order_id = order_id or None
        pending.state = (
            'pending_reconciliation'
            if order_id
            and acknowledged_client_order_id
            == scope.containment_client_order_id
            else 'ambiguous_submission'
        )
        if not self._persist_intent_state():
            return self._record_no_data(
                'unresolved_containment_state_write_failed',
                status='pending_reconciliation',
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        if pending.state == 'ambiguous_submission':
            return self._record_no_data(
                'ambiguous_containment_requires_external_reconciliation',
                status='pending_reconciliation',
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        return self._record_no_data(
            'containment_acknowledged_terminal_receipt_required',
            status='pending_reconciliation',
            order_id=order_id,
            intent_key=intent_key,
        )

    def _terminal_fill_receipt(
        self,
        receipt: Any,
        pending: PendingIntent,
    ) -> tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(receipt, Mapping) or not pending.order_id:
            return None, "terminal_provider_fill_receipt_required"
        times = _fresh_times(receipt, self._clock())
        order_id = str(receipt.get("orderId") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        source_id = str(receipt.get("source_id") or "").strip()
        quantity = _finite(receipt.get("filled_qty"), positive=True)
        price = _finite(receipt.get("filled_avg_price"), positive=True)
        notional = _finite(receipt.get("filled_notional"), positive=True)
        fee = _finite(receipt.get("fee"), nonnegative=True)
        fee_currency = _canonical_asset(receipt.get("fee_currency"))
        fills = receipt.get("fills")
        trade_ids: List[str] = []
        fill_sources: List[str] = []
        if isinstance(fills, list):
            for row in fills:
                if not isinstance(row, Mapping):
                    return (
                        None,
                        "terminal_provider_fill_fee_receipt_incomplete",
                    )
                trade_ids.append(
                    str(row.get("tradeId") or "").strip()
                )
                fill_sources.append(
                    str(row.get("source") or "").strip().lower()
                )
        expected_notional = (
            quantity * price
            if quantity is not None and price is not None
            else None
        )
        has_realized_pnl = (
            "realized_pnl" in receipt
            or "realized_pnl_currency" in receipt
        )
        realized_pnl = (
            _finite(receipt.get("realized_pnl"))
            if has_realized_pnl
            else None
        )
        realized_pnl_currency = (
            _canonical_asset(receipt.get("realized_pnl_currency"))
            if has_realized_pnl
            else ""
        )
        if (
            times is None
            or str(receipt.get("status") or "").strip().upper() != "FILLED"
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("fill_receipt_complete") is not True
            or receipt.get("eligible_for_accounting") is not True
            or receipt.get("eligible_for_learning") is not True
            or receipt.get("reconciliation_required") is not False
            or order_id != pending.order_id
            or not receipt_id
            or not source_id.lower().startswith("kraken_order:")
            or _canonical_pair(receipt.get("symbol"))
            != _canonical_pair(pending.venue_symbol)
            or str(receipt.get("side") or "").strip().lower()
            != pending.side
            or quantity is None
            or not math.isclose(
                quantity,
                pending.requested_quantity,
                rel_tol=1e-9,
                abs_tol=1e-12,
            )
            or price is None
            or notional is None
            or expected_notional is None
            or not math.isclose(
                notional,
                expected_notional,
                rel_tol=0.001,
                abs_tol=1e-8,
            )
            or fee is None
            or not fee_currency
            or not trade_ids
            or any(not trade_id for trade_id in trade_ids)
            or len(trade_ids) != len(set(trade_ids))
            or any(not source.startswith("kraken") for source in fill_sources)
            or (
                has_realized_pnl
                and (
                    realized_pnl is None
                    or not realized_pnl_currency
                )
            )
        ):
            return None, "terminal_provider_fill_fee_receipt_incomplete"
        source_timestamp, received_at = times
        normalized = {
            **dict(receipt),
            "receipt_id": receipt_id,
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
        }
        if has_realized_pnl:
            normalized["realized_pnl"] = realized_pnl
            normalized["realized_pnl_currency"] = realized_pnl_currency
        else:
            normalized.pop("realized_pnl", None)
            normalized.pop("realized_pnl_currency", None)
        return normalized, ""

    def _terminal_without_fill(
        self,
        receipt: Any,
        pending: PendingIntent,
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
            and str(receipt.get("orderId") or "").strip()
            == pending.order_id
            and str(receipt.get("source_id") or "")
            .strip()
            .lower()
            .startswith("kraken_order:")
            and _canonical_pair(receipt.get("symbol"))
            == _canonical_pair(pending.venue_symbol)
            and str(receipt.get("side") or "").strip().lower()
            == pending.side
        )

    def _reconcile_pending(self, intent_key: str) -> Dict[str, Any]:
        pending = self._pending_intents.get(intent_key)
        if pending is None:
            return self._record_no_data("pending_intent_not_found")
        if pending.state in {
            "submission_in_progress",
            "ambiguous_submission",
        }:
            return self._record_no_data(
                "ambiguous_submission_requires_external_reconciliation",
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        if pending.state == "terminal_without_fill":
            return self._record_no_data(
                "terminal_provider_receipt_without_fill",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        if self._readback_consumed:
            return self._record_no_data(
                "order_readback_already_consumed_this_cycle",
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        readback = getattr(self.kraken, "get_order_status", None)
        if not callable(readback) or not pending.order_id:
            return self._record_no_data(
                "supported_order_readback_unavailable",
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        self._readback_consumed = True
        try:
            receipt = readback(pending.order_id)
        except Exception:
            return self._record_no_data(
                "provider_order_readback_failed",
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        if self._terminal_without_fill(receipt, pending):
            closed = {
                **asdict(pending),
                "state": "terminal_without_fill",
                "order_id": pending.order_id,
                "intent_key": intent_key,
                "client_order_id": pending.client_order_id,
                "truth_status": "real_observed",
                "generated_values": False,
            }
            self._closed_intents[intent_key] = closed
            self._pending_intents.pop(intent_key, None)
            if not self._persist_intent_state():
                self._closed_intents.pop(intent_key, None)
                self._pending_intents[intent_key] = pending
                return self._record_no_data(
                    "terminal_nonfill_state_write_failed",
                    status="pending_reconciliation",
                    order_id=pending.order_id,
                    intent_key=intent_key,
                )
            return self._record_no_data(
                "terminal_provider_receipt_without_fill",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        terminal, reason = self._terminal_fill_receipt(receipt, pending)
        if terminal is None:
            return self._record_no_data(
                reason,
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=intent_key,
            )
        return self._apply_terminal_fill(pending, terminal)

    def _fill_already_accounted(
        self,
        terminal: Mapping[str, Any],
    ) -> bool:
        return bool(
            str(terminal["order_id"]) in self._accounted_order_ids
            or set(terminal["trade_ids"]) & self._accounted_trade_ids
        )

    def _apply_terminal_fill(
        self,
        pending: PendingIntent,
        terminal: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if self._fill_already_accounted(terminal):
            return self._record_no_data(
                "duplicate_terminal_fill_receipt",
                order_id=pending.order_id,
                intent_key=pending.intent_key,
            )
        receipt_id = str(terminal["receipt_id"])
        opportunity = dict(pending.opportunity)
        fill = {
            "receipt_id": receipt_id,
            "order_id": str(terminal["order_id"]),
            "client_order_id": pending.client_order_id,
            "trade_ids": list(terminal["trade_ids"]),
            "symbol": pending.symbol,
            "venue_symbol": pending.venue_symbol,
            "side": pending.side,
            "filled_qty": float(terminal["filled_qty"]),
            "filled_avg_price": float(terminal["filled_avg_price"]),
            "filled_notional": float(terminal["filled_notional"]),
            "fee": float(terminal["fee"]),
            "fee_currency": str(terminal["fee_currency"]),
            "source_id": str(terminal["source_id"]),
            "source_timestamp": float(terminal["source_timestamp"]),
            "received_at": float(terminal["received_at"]),
            "market_receipt_id": pending.market_receipt_id,
            "account_receipt_id": pending.account_receipt_id,
            "gate_receipt_id": pending.gate_receipt_id,
            "durable_state_anchor": pending.durable_state_anchor,
            "economic_intent_digest": pending.economic_intent_digest,
            "economic_body_digest": pending.economic_body_digest,
            "provider_moment_digest": pending.provider_moment_digest,
            "governance_permit_id": pending.governance_permit_id,
            "governance_dual_receipt_id": (
                pending.governance_dual_receipt_id
            ),
            "governance_proposal_digest": (
                pending.governance_proposal_digest
            ),
            "governance_permit_consumed": (
                pending.governance_permit_consumed
            ),
            "contingency_warrant_id": pending.contingency_warrant_id,
            "contingency_scope_digest": pending.contingency_scope_digest,
            "contingency_warrant": pending.contingency_warrant,
            "contingency_scope": pending.contingency_scope,
            "contingency_recovery_record_digest": (
                pending.contingency_recovery_record_digest
            ),
            "contingency_recovery_entry_state_anchor": (
                pending.contingency_recovery_entry_state_anchor
            ),
            "contingency_recovery_route_binding_anchor": (
                pending.contingency_recovery_route_binding_anchor
            ),
            "containment_client_order_id": (
                pending.containment_client_order_id
            ),
            "pre_entry_base_balance": pending.pre_entry_base_balance,
            "opportunity": opportunity,
            "truth_status": "real_observed",
            "generated_values": False,
            "accounting_eligible": True,
            "learning_eligible": "realized_pnl" in terminal,
        }
        if "realized_pnl" in terminal:
            fill["realized_pnl"] = float(terminal["realized_pnl"])
            fill["realized_pnl_currency"] = str(
                terminal["realized_pnl_currency"]
            )

        previous_pending = dict(self._pending_intents)
        previous_closed = dict(self._closed_intents)
        previous_fills = list(self._settled_fills)
        previous_order_ids = set(self._accounted_order_ids)
        previous_trade_ids = set(self._accounted_trade_ids)
        previous_learning_ids = set(
            self._learning_applied_receipt_ids
        )

        record_learning = getattr(
            self.network, "record_conversion_profit", None
        )
        update_learning = getattr(
            self.network, "s5_update_labyrinth_cache", None
        )
        learning_possible = bool(
            "realized_pnl" in fill
            and callable(record_learning)
            and callable(update_learning)
            and receipt_id not in self._learning_applied_receipt_ids
        )
        self._settled_fills.append(fill)
        self._accounted_order_ids.add(fill["order_id"])
        self._accounted_trade_ids.update(fill["trade_ids"])
        if learning_possible:
            # Persist the at-most-once marker before invoking mutable learning.
            self._learning_applied_receipt_ids.add(receipt_id)
        self._closed_intents[pending.intent_key] = {
            **asdict(pending),
            "state": "filled",
            "intent_key": pending.intent_key,
            "order_id": fill["order_id"],
            "client_order_id": pending.client_order_id,
            "terminal_receipt_id": receipt_id,
            "truth_status": "real_observed",
            "generated_values": False,
        }
        self._pending_intents.pop(pending.intent_key, None)
        if not self._persist_intent_state():
            self._pending_intents = previous_pending
            self._closed_intents = previous_closed
            self._settled_fills = previous_fills
            self._accounted_order_ids = previous_order_ids
            self._accounted_trade_ids = previous_trade_ids
            self._learning_applied_receipt_ids = previous_learning_ids
            self._rebuild_accounting_views()
            return self._record_no_data(
                "terminal_fill_state_write_failed",
                status="pending_reconciliation",
                order_id=pending.order_id,
                intent_key=pending.intent_key,
            )
        self._rebuild_accounting_views()

        learning_applied = False
        learning_error: Optional[str] = None
        if learning_possible:
            path_key = (
                f"{opportunity['from_asset']}->"
                f"{opportunity['to_asset']}"
            )
            exact_pnl = float(fill["realized_pnl"])
            try:
                record_learning(
                    {
                        "from_asset": opportunity["from_asset"],
                        "to_asset": opportunity["to_asset"],
                        "exchange": "kraken",
                        "net_profit": exact_pnl,
                        "realized_pnl_currency": fill[
                            "realized_pnl_currency"
                        ],
                        "fees": fill["fee"],
                        "fee_currency": fill["fee_currency"],
                        "success": True,
                        "hops": 1,
                        "terminal_receipt_id": receipt_id,
                        "order_id": fill["order_id"],
                        "trade_ids": list(fill["trade_ids"]),
                        "truth_status": "real_observed",
                        "generated_values": False,
                    }
                )
                update_learning(path_key, exact_pnl, True)
                learning_applied = True
            except Exception as exc:
                learning_error = type(exc).__name__

        outcome = {
            "status": "FILLED",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "receipt_id": receipt_id,
            "order_id": fill["order_id"],
            "trade_ids": list(fill["trade_ids"]),
            "filled_qty": fill["filled_qty"],
            "filled_avg_price": fill["filled_avg_price"],
            "filled_notional": fill["filled_notional"],
            "fee": fill["fee"],
            "fee_currency": fill["fee_currency"],
            "source_id": fill["source_id"],
            "source_timestamp": fill["source_timestamp"],
            "received_at": fill["received_at"],
            "action": False,
            "accounting": True,
            "learning": learning_applied,
        }
        if "realized_pnl" in fill:
            outcome["realized_pnl"] = fill["realized_pnl"]
            outcome["realized_pnl_currency"] = fill[
                "realized_pnl_currency"
            ]
        if learning_error is not None:
            outcome["learning_error"] = learning_error
        self.last_execution = outcome
        return outcome

    async def _kraken_poll_loop(
        self,
        interval_seconds: float = 2.0,
    ) -> None:
        getter = getattr(self.kraken, "get_ticker_receipt", None)
        while self.running and callable(getter):
            for symbol, pair in self.BINANCE_TO_KRAKEN.items():
                if not self.running:
                    break
                try:
                    receipt = getter(pair)
                except Exception:
                    self._record_no_data(
                        "kraken_market_receipt_unavailable"
                    )
                    continue
                await self.process_market_receipt(symbol, receipt)
            await asyncio.sleep(interval_seconds)

    async def run(self) -> Dict[str, Any]:
        """Run only after explicit adapter and receipt-source injection."""
        if self._state_load_error is not None:
            return self._record_no_data(
                "valid_intent_state_readback_required"
            )
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
    """Inert CLI preflight; adapters must be injected programmatically."""
    parser = argparse.ArgumentParser(
        description="Validate S5 receipt-gated runtime configuration."
    )
    parser.parse_args(argv)
    engine = S5LiveExecutionEngine()
    outcome = await engine.run()
    print(json.dumps(outcome, sort_keys=True, allow_nan=False))
    return 0 if outcome.get("status") == "stopped" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
