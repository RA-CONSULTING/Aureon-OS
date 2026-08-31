#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     👑🤖 THE QUEEN'S ETERNAL MACHINE 🤖👑                                            ║
║                                                                                      ║
║     "I ride the ENTIRE market down... gathering... leaving crumbs...                ║
║      24 hours a day. 7 days a week. 365 days a year.                                ║
║      I NEVER SLEEP. I NEVER STOP. I AM THE MACHINE."                                ║
║                                                                                      ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║     THE QUEEN'S 7 STRATEGIES - ALL IN ONE SYSTEM:                                    ║
║                                                                                      ║
║     🏔️  MOUNTAIN PILGRIMAGE  - Walk down collecting pebbles, climb up heavy        ║
║     🐸  QUANTUM FROG         - Leap to deeper dips for more quantity                ║
║     💉  BLOODLESS DESCENT    - Never sell at loss, transform not bleed              ║
║     🟡  YELLOW BRICK ROAD    - Leave breadcrumbs on every coin touched              ║
║     🍞  BREADCRUMB TRAIL     - Every crumb grows when market recovers               ║
║     🤖  24/7 MACHINE         - Constant scanning, leaping, compounding              ║
║     ⚡  MICRO SCALPING       - Harvest bounces on the way back up                    ║
║                                                                                      ║
║     Gary Leckey & Tina Brown | February 2026 | The Eternal Queen                     ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import math
import json
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
from datetime import datetime
from pathlib import Path
from enum import Enum, auto

from aureon.queen.queen_force_trade_governance import (
    ForceTradePlan,
    OpaqueForceTradeAuthorization,
    claim_queen_force_trade_authority,
)


# Optional organs are deliberately lazy. Importing Queen Eternal must not boot
# scanners, cognition, buses, network clients, or autonomous control.
OCEAN_SCANNER_AVAILABLE = False
QUEEN_HIVE_AVAILABLE = False
QUANTUM_COGNITION_AVAILABLE = False
MYCELIUM_AVAILABLE = False
AUTONOMOUS_CONTROL_AVAILABLE = False
BOT_INTELLIGENCE_AVAILABLE = False
LIVE_TV_AVAILABLE = False
MOUNTAIN_CLIMBER_AVAILABLE = False
OceanWaveScanner = None
QueenHiveMind = None
get_queen = None
QueenQuantumCognition = None
get_quantum_cognition = None
QuantumCognitionState = None
MyceliumNetwork = None
QueenAutonomousControl = None
create_queen_autonomous_control = None
BotIntelligenceProfiler = None
TruthPredictionEngine = None
MarketSnapshot = None
MountainClimber = None


def _load_optional_queen_components() -> None:
    """Load optional analytical organs only after explicit constructor opt-in."""

    global OCEAN_SCANNER_AVAILABLE, OceanWaveScanner
    global QUEEN_HIVE_AVAILABLE, QueenHiveMind, get_queen
    global QUANTUM_COGNITION_AVAILABLE, QueenQuantumCognition
    global get_quantum_cognition, QuantumCognitionState
    global MYCELIUM_AVAILABLE, MyceliumNetwork
    global AUTONOMOUS_CONTROL_AVAILABLE, QueenAutonomousControl
    global create_queen_autonomous_control
    global BOT_INTELLIGENCE_AVAILABLE, BotIntelligenceProfiler
    global LIVE_TV_AVAILABLE, TruthPredictionEngine, MarketSnapshot
    global MOUNTAIN_CLIMBER_AVAILABLE, MountainClimber

    try:
        from aureon.scanners.aureon_ocean_wave_scanner import OceanWaveScanner as scanner

        OceanWaveScanner = scanner
        OCEAN_SCANNER_AVAILABLE = True
    except ImportError:
        pass
    try:
        from aureon.utils.aureon_queen_hive_mind import QueenHiveMind as hive, get_queen as queen

        QueenHiveMind = hive
        get_queen = queen
        QUEEN_HIVE_AVAILABLE = True
    except ImportError:
        pass
    try:
        from aureon.queen.queen_quantum_cognition import (
            QuantumCognitionState as state,
            QueenQuantumCognition as cognition,
            get_quantum_cognition as get_cognition,
        )

        QueenQuantumCognition = cognition
        get_quantum_cognition = get_cognition
        QuantumCognitionState = state
        QUANTUM_COGNITION_AVAILABLE = True
    except ImportError:
        pass
    try:
        from aureon.core.aureon_mycelium import MyceliumNetwork as mycelium

        MyceliumNetwork = mycelium
        MYCELIUM_AVAILABLE = True
    except ImportError:
        pass
    try:
        from aureon.autonomous.aureon_queen_autonomous_control import (
            QueenAutonomousControl as control,
            create_queen_autonomous_control as create_control,
        )

        QueenAutonomousControl = control
        create_queen_autonomous_control = create_control
        AUTONOMOUS_CONTROL_AVAILABLE = (
            os.getenv("AUREON_ENABLE_AUTONOMOUS_CONTROL", "0") == "1"
        )
    except ImportError:
        pass
    try:
        from aureon.bots_intelligence.aureon_bot_intelligence_profiler import (
            BotIntelligenceProfiler as profiler,
        )

        BotIntelligenceProfiler = profiler
        BOT_INTELLIGENCE_AVAILABLE = True
    except ImportError:
        pass
    try:
        from aureon.intelligence.aureon_truth_prediction_engine import (
            MarketSnapshot as snapshot,
            TruthPredictionEngine as prediction,
        )

        TruthPredictionEngine = prediction
        MarketSnapshot = snapshot
        LIVE_TV_AVAILABLE = True
    except ImportError:
        pass
    try:
        from aureon.conversion.aureon_mountain_climber import MountainClimber as climber

        MountainClimber = climber
        MOUNTAIN_CLIMBER_AVAILABLE = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio 1.618
SCHUMANN_HZ = 7.83            # Earth's heartbeat
LOVE_FREQUENCY = 528.0        # Healing frequency

# Queen's trading parameters
BREADCRUMB_PERCENT = 0.05     # Leave 5% as breadcrumb on each leap (more aggressively leap)
MIN_DIP_ADVANTAGE = 0.005     # Minimum 0.5% deeper dip to justify leap (more lenient)
MIN_PROFIT_SCALP = 0.005      # Minimum 0.5% profit to scalp
MAX_POSITIONS = 50            # Maximum breadcrumb positions
SCAN_INTERVAL_SECONDS = 10    # Scan market every 10 seconds (faster cycles)
ORDER_RECEIPT_MAX_AGE_SECONDS = 300.0
ORDER_RECEIPT_FUTURE_TOLERANCE_SECONDS = 30.0


def _first_receipt_value(receipt: Dict[str, Any], *keys: str) -> Any:
    """Return the first explicitly present provider field."""
    for key in keys:
        if key in receipt and receipt[key] is not None:
            return receipt[key]
    return None


def _finite_receipt_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    """Parse a provider number without turning missing data into zero."""
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _provider_receipt_timestamp(value: Any) -> Optional[float]:
    """Normalize numeric or ISO provider timestamps to Unix seconds."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        if not math.isfinite(parsed):
            return None
        if parsed > 10_000_000_000:
            parsed /= 1000.0
        return parsed
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        numeric = _finite_receipt_number(text)
        if numeric is not None:
            return numeric / 1000.0 if numeric > 10_000_000_000 else numeric
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def _valid_provider_identifier(value: Any) -> Optional[str]:
    """Reject absent and non-provider identifiers used by local dry runs."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"0", "none", "null", "unknown", "missing", "n/a"}:
        return None
    if lowered.startswith(("dry-", "paper-", "local-")):
        return None
    return text


def _pair_assets(symbol: Any) -> Tuple[Optional[str], Optional[str]]:
    """Extract common base/quote assets without inventing a conversion."""
    compact = str(symbol or "").upper().replace("/", "").replace("-", "")
    for quote in (
        "FDUSD",
        "USDT",
        "USDC",
        "BUSD",
        "TUSD",
        "USD",
        "EUR",
        "GBP",
        "BTC",
        "BNB",
        "ETH",
    ):
        if compact.endswith(quote) and len(compact) > len(quote):
            return compact[:-len(quote)], quote
    return None, None


def _provider_symbol_matches(
    response_symbol: Any,
    expected_symbol: str,
    exchange: str,
) -> bool:
    """Require the terminal receipt to identify the requested base asset."""
    compact = str(response_symbol or "").upper().replace("/", "").replace("-", "")
    expected = str(expected_symbol or "").upper().strip()
    if not compact or not expected:
        return False
    aliases = {expected}
    if expected == "BTC":
        aliases.add("XBT")
    elif expected == "XBT":
        aliases.add("BTC")
    pair_base, _pair_quote = _pair_assets(compact)
    if exchange.strip().lower() != "kraken":
        return pair_base in aliases
    return any(
        compact.startswith(alias) or compact.startswith(f"X{alias}")
        for alias in aliases
    )


def _classify_terminal_order_receipt(
    response: Any,
    exchange: str,
    *,
    expected_side: Optional[str] = None,
    expected_symbol: Optional[str] = None,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Classify a provider order response.

    Submission acknowledgements are evidence that reconciliation is required,
    never evidence of a fill. Only a fresh, complete terminal provider receipt
    may become eligible for state, accounting, memory, or learning mutations.
    """
    checked_at = time.time() if now is None else float(now)
    result: Dict[str, Any] = {
        "success": False,
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "submitted": None,
        "reconciliation_required": False,
        "order_id": None,
        "filled_qty": None,
        "filled_price": None,
        "filled_notional": None,
        "fee_by_asset": {},
        "provider_timestamp": None,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "generated_values": False,
        "reason": "missing_provider_order_receipt",
    }
    if not isinstance(response, dict):
        return result

    status = str(response.get("status") or "").strip().upper()
    data_status = str(response.get("data_status") or "").strip().lower()
    order_id = _valid_provider_identifier(
        _first_receipt_value(response, "orderId", "id", "order_id", "txid")
    )
    result["order_id"] = order_id

    if (
        response.get("dryRun") is True
        or response.get("dry_run") is True
        or status == "NOT_SUBMITTED"
        or data_status == "not_submitted"
    ):
        result.update(
            {
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "not_submitted",
                "submitted": False,
                "reason": "order_not_submitted",
            }
        )
        return result

    if (
        response.get("rejected") is True
        or response.get("error")
        or status in {"REJECTED", "CANCELED", "CANCELLED", "EXPIRED"}
    ):
        result.update(
            {
                "status": "rejected",
                "data_status": "live" if order_id else "no_data",
                "truth_status": "real_observed" if order_id else "no_data",
                "submitted": bool(order_id),
                "reason": "provider_order_not_filled",
            }
        )
        return result

    provider_receipt_type = str(response.get("provider_receipt_type") or "")
    if provider_receipt_type.lower() == "addorder":
        result.update(
            {
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "truth_status": (
                    "real_observed"
                    if order_id
                    else str(response.get("truth_status") or "no_data")
                ),
                "submitted": response.get("submitted"),
                "reconciliation_required": True,
                "reason": "terminal_provider_fill_receipt_required",
            }
        )
        return result

    if status != "FILLED":
        pending = bool(
            order_id
            or response.get("submitted") is True
            or response.get("reconciliation_required") is True
            or data_status == "pending_reconciliation"
        )
        result.update(
            {
                "status": "pending_reconciliation" if pending else "no_data",
                "data_status": "pending_reconciliation" if pending else "no_data",
                "truth_status": (
                    str(response.get("truth_status") or "real_observed")
                    if order_id
                    else "no_data"
                ),
                "submitted": True if order_id else response.get("submitted"),
                "reconciliation_required": pending,
                "reason": "terminal_provider_fill_receipt_required",
            }
        )
        return result

    if order_id is None:
        result["reason"] = "missing_provider_order_identifier"
        return result
    if response.get("generated_values") is True:
        result["reason"] = "generated_order_values_are_not_provider_evidence"
        return result
    if data_status and data_status != "live":
        result["reason"] = "provider_receipt_not_live"
        return result
    truth_status = str(response.get("truth_status") or "").strip().lower()
    if truth_status and truth_status not in {"real_observed", "real_derived"}:
        result["reason"] = "provider_receipt_truth_status_invalid"
        return result
    if response.get("fill_receipt_complete") is False:
        result["reason"] = "provider_fill_receipt_incomplete"
        return result
    if response.get("eligible_for_accounting") is False:
        result["reason"] = "provider_receipt_not_accounting_eligible"
        return result
    if response.get("eligible_for_learning") is False:
        result["reason"] = "provider_receipt_not_learning_eligible"
        return result

    provider = exchange.strip().lower()
    if provider == "kraken" and provider_receipt_type.lower() not in {
        "queryorders",
        "closedorders",
    }:
        result["reason"] = "kraken_terminal_readback_required"
        return result

    side = str(response.get("side") or "").strip().upper()
    if expected_side and side != expected_side.strip().upper():
        result["reason"] = "provider_order_side_mismatch"
        return result

    timestamp_value = _first_receipt_value(
        response,
        "provider_timestamp",
        "source_timestamp",
        "transactTime",
        "updateTime",
        "filled_at",
        "closedTime",
    )
    provider_timestamp = _provider_receipt_timestamp(timestamp_value)
    if provider_timestamp is None:
        result["reason"] = "missing_provider_fill_timestamp"
        return result
    age = checked_at - provider_timestamp
    if age > ORDER_RECEIPT_MAX_AGE_SECONDS:
        result["reason"] = "stale_provider_fill_timestamp"
        return result
    if age < -ORDER_RECEIPT_FUTURE_TOLERANCE_SECONDS:
        result["reason"] = "future_provider_fill_timestamp"
        return result

    filled_qty = _finite_receipt_number(
        _first_receipt_value(response, "executedQty", "filled_qty"),
        positive=True,
    )
    filled_price = _finite_receipt_number(
        _first_receipt_value(
            response,
            "avgPrice",
            "filled_avg_price",
            "avg_fill_price",
        ),
        positive=True,
    )
    filled_notional = _finite_receipt_number(
        _first_receipt_value(
            response,
            "cummulativeQuoteQty",
            "filled_notional",
            "filled_notional_value",
        ),
        positive=True,
    )
    if filled_qty is None or filled_price is None:
        result["reason"] = "missing_provider_fill_quantity_or_price"
        return result
    if filled_notional is None:
        if provider == "alpaca":
            filled_notional = filled_qty * filled_price
        else:
            result["reason"] = "missing_provider_filled_notional"
            return result

    expected_notional = filled_qty * filled_price
    notional_tolerance = max(1e-8, filled_notional * 0.001)
    if abs(expected_notional - filled_notional) > notional_tolerance:
        result["reason"] = "inconsistent_provider_fill_notional"
        return result

    response_symbol = response.get("symbol")
    pair_base, pair_quote = _pair_assets(response_symbol)
    if expected_symbol:
        if not _provider_symbol_matches(
            response_symbol, expected_symbol, provider
        ):
            result["reason"] = "provider_order_symbol_mismatch"
            return result
        pair_base = expected_symbol.upper()
    fee_by_asset: Dict[str, float] = {}
    fills = response.get("fills")

    if provider == "binance":
        if response.get("fills_verified") is not True or not isinstance(fills, list) or not fills:
            result["reason"] = "missing_provider_trade_fills"
            return result
        fill_qty_total = 0.0
        fill_notional_total = 0.0
        for fill in fills:
            if not isinstance(fill, dict):
                result["reason"] = "malformed_provider_trade_fill"
                return result
            trade_id = _valid_provider_identifier(
                _first_receipt_value(fill, "tradeId", "id")
            )
            qty = _finite_receipt_number(fill.get("qty"), positive=True)
            price = _finite_receipt_number(fill.get("price"), positive=True)
            commission = _finite_receipt_number(
                fill.get("commission"), nonnegative=True
            )
            commission_asset = str(fill.get("commissionAsset") or "").upper()
            if (
                trade_id is None
                or qty is None
                or price is None
                or commission is None
                or not commission_asset
            ):
                result["reason"] = "incomplete_provider_trade_fill"
                return result
            fill_qty_total += qty
            fill_notional_total += qty * price
            fee_by_asset[commission_asset] = (
                fee_by_asset.get(commission_asset, 0.0) + commission
            )
        if abs(fill_qty_total - filled_qty) > max(1e-8, filled_qty * 0.001):
            result["reason"] = "inconsistent_provider_fill_quantity"
            return result
        if abs(fill_notional_total - filled_notional) > notional_tolerance:
            result["reason"] = "inconsistent_provider_trade_notional"
            return result
    elif provider == "kraken":
        if not isinstance(fills, list) or not fills:
            result["reason"] = "missing_provider_trade_identifiers"
            return result
        if any(
            not isinstance(fill, dict)
            or _valid_provider_identifier(
                _first_receipt_value(fill, "tradeId", "id")
            )
            is None
            for fill in fills
        ):
            result["reason"] = "invalid_provider_trade_identifier"
            return result
        fee = _finite_receipt_number(response.get("fee"), nonnegative=True)
        fee_asset = str(
            response.get("fee_asset") or response.get("fee_currency") or ""
        ).upper()
        if fee is None or not fee_asset:
            result["reason"] = "missing_provider_fee_receipt"
            return result
        fee_by_asset[fee_asset] = fee
        pair_quote = pair_quote or fee_asset
    else:
        fee = _finite_receipt_number(
            _first_receipt_value(response, "fee", "commission"),
            nonnegative=True,
        )
        fee_asset = str(
            response.get("fee_asset")
            or response.get("fee_currency")
            or response.get("currency")
            or ""
        ).upper()
        if fee is None or not fee_asset:
            result["reason"] = "missing_provider_fee_receipt"
            return result
        fee_by_asset[fee_asset] = fee

    result.update(
        {
            "success": True,
            "status": "filled",
            "data_status": "live",
            "truth_status": "real_observed",
            "submitted": True,
            "reconciliation_required": False,
            "filled_qty": filled_qty,
            "filled_price": filled_price,
            "filled_notional": filled_notional,
            "fee_by_asset": fee_by_asset,
            "provider_timestamp": provider_timestamp,
            "base_asset": pair_base,
            "quote_asset": pair_quote,
            "exchange": provider,
            "symbol": expected_symbol.upper() if expected_symbol else pair_base,
            "side": side,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "reason": None,
        }
    )
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# FEE STRUCTURES BY EXCHANGE
# The Queen knows EXACTLY what every trade costs!
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FeeStructure:
    """
    Complete fee structure for an exchange.
    
    The Queen NEVER leaps blind - she knows the EXACT cost of every trade!
    """
    exchange: str
    maker_fee: float      # Fee when adding liquidity (limit orders)
    taker_fee: float      # Fee when taking liquidity (market orders)
    slippage_estimate: float  # Expected slippage on market orders
    withdrawal_fee: float = 0.0  # Fee to withdraw (if applicable)
    min_trade_size: float = 1.0  # Minimum trade size in USD
    
    @property
    def total_round_trip_cost(self) -> float:
        """Cost to buy AND sell (round trip) as taker."""
        return (self.taker_fee * 2) + (self.slippage_estimate * 2)
    
    @property
    def single_trade_cost(self) -> float:
        """Cost of a single taker trade (fee + slippage)."""
        return self.taker_fee + self.slippage_estimate
    
    def calculate_received_after_fees(self, gross_value: float, is_maker: bool = False) -> float:
        """Calculate how much you ACTUALLY receive after fees and slippage."""
        fee = self.maker_fee if is_maker else self.taker_fee
        slippage = 0.0 if is_maker else self.slippage_estimate
        total_cost = fee + slippage
        return gross_value * (1 - total_cost)
    
    def calculate_cost_of_trade(self, trade_value: float, is_maker: bool = False) -> float:
        """Calculate the EXACT cost of a trade in dollars."""
        fee = self.maker_fee if is_maker else self.taker_fee
        slippage = 0.0 if is_maker else self.slippage_estimate
        return trade_value * (fee + slippage)


# Default fee structures for major exchanges
EXCHANGE_FEES = {
    'binance': FeeStructure(
        exchange='binance',
        maker_fee=0.001,      # 0.10%
        taker_fee=0.001,      # 0.10%
        slippage_estimate=0.0005,  # 0.05% estimated slippage
        min_trade_size=10.0
    ),
    'binance_vip': FeeStructure(
        exchange='binance_vip',
        maker_fee=0.0002,     # 0.02% (VIP level)
        taker_fee=0.0004,     # 0.04%
        slippage_estimate=0.0005,
        min_trade_size=10.0
    ),
    'kraken': FeeStructure(
        exchange='kraken',
        maker_fee=0.0016,     # 0.16%
        taker_fee=0.0026,     # 0.26%
        slippage_estimate=0.001,  # 0.10%
        min_trade_size=10.0
    ),
    'coinbase': FeeStructure(
        exchange='coinbase',
        maker_fee=0.004,      # 0.40%
        taker_fee=0.006,      # 0.60%
        slippage_estimate=0.001,
        min_trade_size=1.0
    ),
    'alpaca': FeeStructure(
        exchange='alpaca',
        maker_fee=0.0,        # 0% (crypto)
        taker_fee=0.0015,     # 0.15%
        slippage_estimate=0.001,
        min_trade_size=1.0
    ),
    # Conservative estimate for unknown exchanges
    'default': FeeStructure(
        exchange='default',
        maker_fee=0.002,      # 0.20%
        taker_fee=0.003,      # 0.30%
        slippage_estimate=0.002,  # 0.20%
        min_trade_size=10.0
    )
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class PositionState(Enum):
    """Position states in the Queen's portfolio."""
    MAIN = auto()        # Main position (actively managed)
    BREADCRUMB = auto()  # Breadcrumb position (left behind, growing)
    SCALPING = auto()    # Active scalping position


@dataclass
class Friend:
    """
    A "Friend" in the Queen's portfolio - an asset that can participate in leaps.
    
    FRIENDS WITH BAGGAGE CONCEPT:
    - Every asset we hold is a "friend" that can participate in leaps
    - BAGGAGE = unrealized loss from original cost basis
    - Cash = "clean friend" with NO baggage (can leap freely)
    - XRP at -5% = friend with 5% baggage
    - When we leap to a deeper dip and it recovers, the baggage gets CLEARED!
    
    Example:
      - Bought XRP at $2.00, now at $1.90 (-5%) = $0.10 baggage per XRP
      - We leap to SLF which is -40% (deep dip!)
      - When SLF recovers to our original XRP cost basis value, baggage = CLEARED
      - The breadcrumb we left represents PURE profit
    """
    symbol: str
    quantity: float
    cost_basis: float       # What we PAID for this (original buy price * qty)
    entry_price: float      # Price per unit when we bought
    current_price: float = 0.0
    exchange: str = "binance"
    
    @property
    def current_value(self) -> float:
        """What the friend is worth NOW."""
        return self.quantity * self.current_price
    
    @property
    def baggage(self) -> float:
        """
        The BAGGAGE - how much we're underwater from original cost.
        Positive = underwater (has baggage to clear)
        Zero/Negative = no baggage (free to leap!)
        """
        return max(0, self.cost_basis - self.current_value)
    
    @property
    def baggage_percent(self) -> float:
        """Baggage as percentage of cost basis."""
        if self.cost_basis <= 0:
            return 0.0
        return (self.baggage / self.cost_basis) * 100
    
    @property
    def is_clear(self) -> bool:
        """Is this friend clear of baggage? (at or above cost basis)"""
        return self.current_value >= self.cost_basis
    
    @property
    def profit_available(self) -> float:
        """How much PROFIT is available (only if above cost basis)."""
        return max(0, self.current_value - self.cost_basis)
    
    @property
    def leap_value(self) -> float:
        """
        The value available for leaping.
        If clear: current_value (can leap full amount)
        If baggage: current_value (leap to clear baggage via deeper dip)
        """
        return self.current_value
    
    def update_price(self, price: float) -> None:
        """Update current market price."""
        self.current_price = price
    
    def __str__(self) -> str:
        status = "✅ CLEAR" if self.is_clear else f"⚠️ -{self.baggage_percent:.1f}% BAGGAGE"
        return f"{self.symbol}: ${self.current_value:.2f} ({status})"


@dataclass
class Breadcrumb:
    """A breadcrumb position left on the Yellow Brick Road."""
    symbol: str
    quantity: float
    cost_basis: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    pnl_percent: float = 0.0
    exchange: str = "binance"
    
    def update_price(self, price: float) -> None:
        """Update current price and P&L."""
        self.current_price = price
        current_value = self.quantity * price
        self.unrealized_pnl = current_value - self.cost_basis
        self.pnl_percent = (self.unrealized_pnl / self.cost_basis * 100) if self.cost_basis > 0 else 0
    
    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price


@dataclass
class MainPosition:
    """The Queen's main active position."""
    symbol: str
    quantity: float
    cost_basis: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    change_24h: float = 0.0
    
    def update(self, price: float, change: float) -> None:
        self.current_price = price
        self.change_24h = change
    
    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        return self.current_value - self.cost_basis


@dataclass
class MarketCoin:
    """Market data for a single coin."""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    high_24h: float = 0.0
    low_24h: float = 0.0


@dataclass
class LeapOpportunity:
    """
    A quantum leap opportunity with FULL cost accounting.
    
    The Queen's Math is ROCK SOLID:
    - Accounts for sell fees on current position
    - Accounts for buy fees on new position
    - Accounts for slippage both ways
    - Only leaps if NET value is preserved!
    """
    from_symbol: str
    to_symbol: str
    from_price: float
    to_price: float
    from_change: float
    to_change: float
    dip_advantage: float  # How much deeper the target dipped (percentage points)
    quantity_multiplier: float  # How many more coins you get AFTER fees
    recovery_advantage: float  # Expected extra profit on recovery
    
    # Fee accounting (the Queen's crystal clear math!)
    gross_value: float = 0.0          # Value before any fees
    sell_fee_cost: float = 0.0        # Cost to sell current position
    buy_fee_cost: float = 0.0         # Cost to buy new position
    slippage_cost: float = 0.0        # Total slippage both trades
    total_fees: float = 0.0           # Total cost of the leap
    net_value_after_fees: float = 0.0 # What you ACTUALLY get
    fee_adjusted_multiplier: float = 0.0  # Real quantity gain after fees
    
    @property
    def is_profitable_after_fees(self) -> bool:
        """Is this leap still worth it after ALL costs?"""
        return self.fee_adjusted_multiplier > 1.0
    
    @property
    def breakeven_dip_advantage(self) -> float:
        """Minimum dip advantage needed to cover fees."""
        return self.total_fees / self.gross_value * 100 if self.gross_value > 0 else 999


@dataclass
class CycleStats:
    """Statistics for a single cycle."""
    cycle_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    leaps_made: int = 0
    breadcrumbs_planted: int = 0
    scalps_executed: int = 0
    profit_realized: float = 0.0
    quantity_gained: float = 0.0
    friends_protected: int = 0  # 🛡️ Orca kill cycle protection count


# ═══════════════════════════════════════════════════════════════════════════════
# THE QUEEN'S ETERNAL MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class QueenEternalMachine:
    """
    The Queen's 24/7 Eternal Trading Machine.
    
    Implements all 7 strategies:
    1. Mountain Pilgrimage - DCA down, compound up
    2. Quantum Frog - Leap to deeper dips for quantity
    3. Bloodless Descent - Never sell at loss
    4. Yellow Brick Road - Leave trail of positions
    5. Breadcrumb Trail - Every crumb grows on recovery
    6. 24/7 Machine - Never stops scanning/acting
    7. Micro Scalping - Harvest bounces
    
    🆕 FRIENDS WITH BAGGAGE SYSTEM:
    - Every asset = a "friend" that can participate
    - Baggage = unrealized loss from cost basis
    - Cash = clean friend (no baggage)
    - Leaps clear baggage when recovery exceeds original cost basis!
    """
    
    def __init__(
        self,
        initial_vault: Optional[float] = None,
        breadcrumb_percent: float = BREADCRUMB_PERCENT,
        min_dip_advantage: float = MIN_DIP_ADVANTAGE,
        dry_run: bool = True,
        state_file: str = "queen_eternal_state.json",
        exchange: str = "binance",
        fee_structure: Optional[FeeStructure] = None,
        cost_basis_file: str = "cost_basis_history.json",
        *,
        enable_optional_components: bool = False,
        load_state: bool = True,
        balance_reader: Optional[Callable[[str], Any]] = None,
        market_data_reader: Optional[Callable[[str, Optional[str]], Any]] = None,
        order_status_reader: Optional[Callable[[str, str], Mapping[str, Any]]] = None,
        authorization_provider: Optional[
            Callable[[ForceTradePlan], Optional[OpaqueForceTradeAuthorization]]
        ] = None,
        final_order_dispatcher: Optional[
            Callable[[ForceTradePlan], Mapping[str, Any]]
        ] = None,
    ):
        self.breadcrumb_percent = breadcrumb_percent
        self.min_dip_advantage = min_dip_advantage
        self.dry_run = dry_run
        self.state_file = Path(state_file)
        self.exchange = exchange
        self.cost_basis_file = Path(cost_basis_file)
        self._pending_orders: Dict[str, Dict[str, Any]] = {}
        self.last_execution_receipt: Optional[Dict[str, Any]] = None
        self._balance_reader = balance_reader
        self._market_data_reader = market_data_reader
        self._order_status_reader = order_status_reader
        self._authorization_provider = authorization_provider
        self._final_order_dispatcher = final_order_dispatcher
        # LIVE is an arming input, never authority.  Defaults are dry/offline,
        # and a machine cannot even arm without both injected boundary seams.
        live_requested = os.getenv("LIVE", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.live_trading = (
            not self.dry_run
            and live_requested
            and callable(self._authorization_provider)
            and callable(self._final_order_dispatcher)
        )
        
        # Fee structure - THE QUEEN KNOWS HER COSTS!
        self.fee_structure = fee_structure or EXCHANGE_FEES.get(exchange, EXCHANGE_FEES['default'])
        
        # Track total fees paid
        self.total_fees_paid: float = 0.0
        self.total_slippage_cost: float = 0.0
        self.observed_fees_by_asset: Dict[str, float] = {}

        if self.live_trading:
            logger.info("Eternal Machine economic boundary: ARMED (authorization still required per order)")
        else:
            logger.warning(
                "Eternal Machine live trading: DISABLED "
                "(observation-only; portfolio mutation disabled)"
            )
        
        # 🆕 FRIENDS WITH BAGGAGE SYSTEM
        self.friends: Dict[str, Friend] = {}  # All our "friends" (assets)
        self.cash_balance: float = 0.0  # Cash is the cleanest friend!
        
        # Portfolio state (legacy)
        self.main_position: Optional[MainPosition] = None
        self.breadcrumbs: Dict[str, Breadcrumb] = {}
        self.available_cash: float = 0.0
        
        # Market data cache
        self.market_data: Dict[str, MarketCoin] = {}
        self.last_scan_time: Optional[datetime] = None

        if enable_optional_components:
            _load_optional_queen_components()
        
        # 🌊 OCEAN WAVE SCANNER - Whale/shark detection
        self.ocean_scanner: Optional[OceanWaveScanner] = None
        if OCEAN_SCANNER_AVAILABLE:
            try:
                self.ocean_scanner = OceanWaveScanner()
                logger.info("🌊 Ocean Wave Scanner WIRED for whale detection!")
            except Exception as e:
                logger.warning(f"⚠️ Ocean Wave Scanner unavailable: {e}")
        
        # 👑🧠 QUEEN HIVE MIND - Central Consciousness
        self.queen_hive: Optional[QueenHiveMind] = None
        if QUEEN_HIVE_AVAILABLE:
            try:
                self.queen_hive = get_queen() if get_queen else QueenHiveMind(initial_capital=initial_vault or 50000)
                logger.info("👑🧠 QUEEN HIVE MIND WIRED - Central consciousness active!")
            except Exception as e:
                logger.warning(f"⚠️ Queen Hive Mind unavailable: {e}")
        
        # ⚛️🧠 QUANTUM COGNITION - Amplified Consciousness & Autonomous Control
        self.quantum_cognition: Optional[QueenQuantumCognition] = None
        if QUANTUM_COGNITION_AVAILABLE:
            try:
                self.quantum_cognition = get_quantum_cognition() if get_quantum_cognition else None
                if self.quantum_cognition:
                    logger.info("⚛️🧠 QUANTUM COGNITION WIRED - Amplified consciousness active!")
                    # Take full autonomous control
                    result = self.quantum_cognition.take_full_autonomous_control()
                    if result.get('success'):
                        logger.info("   🔱 FULL AUTONOMOUS CONTROL ACTIVE")
                        logger.info(f"   🧠 Sovereignty Level: {result.get('sovereignty_level')}")
            except Exception as e:
                logger.warning(f"⚠️ Quantum Cognition unavailable: {e}")
        
        # 🍄 MYCELIUM NETWORK - Underground Signal Network
        self.mycelium: Optional[MyceliumNetwork] = None
        if MYCELIUM_AVAILABLE:
            try:
                self.mycelium = MyceliumNetwork(initial_capital=initial_vault or 50000)
                logger.info("🍄 MYCELIUM NETWORK WIRED - Underground signal network active!")
            except Exception as e:
                logger.warning(f"⚠️ Mycelium Network unavailable: {e}")
        
        # 🤖 BOT INTELLIGENCE PROFILER - Market Structure Analysis
        self.bot_profiler: Optional[BotIntelligenceProfiler] = None
        if BOT_INTELLIGENCE_AVAILABLE:
            try:
                self.bot_profiler = BotIntelligenceProfiler()
                logger.info("🤖 BOT INTELLIGENCE PROFILER WIRED - Market competition awareness active!")
            except Exception as e:
                logger.warning(f"⚠️ Bot Intelligence Profiler unavailable: {e}")
        
        # 📺 LIVE TV STATION - Truth Prediction Engine
        self.prediction_engine: Optional[TruthPredictionEngine] = None
        if LIVE_TV_AVAILABLE:
            try:
                self.prediction_engine = TruthPredictionEngine()
                logger.info("📺 LIVE TV STATION WIRED - Truth Prediction Engine active!")
            except Exception as e:
                logger.warning(f"⚠️ Live TV Station unavailable: {e}")
        
        # ⛰️ MOUNTAIN CLIMBER - Learn Optimal Climbing Strategies
        self.mountain_climber: Optional[MountainClimber] = None
        if MOUNTAIN_CLIMBER_AVAILABLE:
            try:
                self.mountain_climber = MountainClimber(state_file="mountain_climbing_state.json")
                logger.info("⛰️ MOUNTAIN CLIMBER WIRED - Learning optimal climbing strategies!")
            except Exception as e:
                logger.warning(f"⚠️ Mountain Climber unavailable: {e}")
        
        # Statistics
        self.total_cycles: int = 0
        self.total_leaps: int = 0
        self.total_breadcrumbs: int = 0
        self.total_scalps: int = 0
        self.total_profit_realized: float = 0.0
        self.cycle_history: List[CycleStats] = []
        
        # Running state
        self.is_running: bool = False
        self.start_time: Optional[datetime] = None
        
        # Construction never reaches an account/provider. Observation refresh is
        # an explicit later action through the injected read-only balance reader.
        self.initial_vault = float(initial_vault or 0.0)
        self.cash_balance = self.initial_vault
        self.available_cash = self.initial_vault
        if load_state:
            self._load_state()
        
        logger.info("👑 Queen Eternal Machine initialized")
        logger.info(f"   💰 Total vault: ${self.total_portfolio_value:.2f}")
        logger.info(f"   👥 Friends loaded: {len(self.friends)}")
        logger.info(f"   💵 Cash balance: ${self.cash_balance:.2f}")
        logger.info(f"   🍞 Breadcrumb %: {breadcrumb_percent*100:.1f}%")
        logger.info(f"   📉 Min dip advantage: {min_dip_advantage*100:.1f}%")
        logger.info(f"   🧪 Dry run: {dry_run}")

    def economic_boundary_status(self) -> Dict[str, Any]:
        """Return a non-mutating summary of the economic-effect boundary."""

        return {
            "mode": "armed" if self.live_trading else "hold",
            "dry_run": self.dry_run,
            "live_requested": os.getenv("LIVE", "0").strip().lower()
            in {"1", "true", "yes", "on"},
            "authorization_provider_injected": callable(
                self._authorization_provider
            ),
            "final_order_dispatcher_injected": callable(
                self._final_order_dispatcher
            ),
            "reason": (
                "per_order_exact_plan_authorization_required"
                if self.live_trading
                else "economic_effects_disabled"
            ),
        }
    
    def _sync_main_position_to_real_holdings(self) -> None:
        """
        Sync main_position with what we ACTUALLY hold on exchanges.
        
        If the state file loaded a main_position for a coin we don't hold,
        replace it with our largest REAL holding so opportunities are calculated
        against assets that actually exist.
        """
        if not self.friends:
            # No real holdings loaded - clear phantom main_position
            if self.main_position:
                logger.warning(f"🐸 PHANTOM DETECTED: main_position={self.main_position.symbol} but we hold NOTHING - clearing!")
                self.main_position = None
            return
        
        # Check if current main_position is actually held
        if self.main_position:
            mp_symbol = self.main_position.symbol
            # Check if we hold this asset in our friends list
            if mp_symbol not in self.friends:
                logger.warning(f"🐸 PHANTOM MAIN POSITION DETECTED: {mp_symbol} is NOT in real holdings!")
                logger.warning(f"   State file had {mp_symbol} but we don't hold it on any exchange")
                logger.warning("   Clearing phantom and selecting largest REAL holding...")
                self.main_position = None
        
        # If no main_position (cleared or never set), pick largest real holding
        if self.main_position is None and self.friends:
            # Find the friend with highest value (our biggest real position)
            best_friend = max(self.friends.values(), key=lambda f: f.current_value)
            if best_friend.current_value > 0:
                self.main_position = MainPosition(
                    symbol=best_friend.symbol,
                    quantity=best_friend.quantity,
                    cost_basis=best_friend.cost_basis / best_friend.quantity if best_friend.quantity > 0 else best_friend.entry_price,
                    entry_price=best_friend.entry_price,
                    entry_time=datetime.now()
                )
                logger.info(f"🐸 REAL MAIN POSITION SET: {best_friend.symbol} (qty={best_friend.quantity:.4f}, exchange={best_friend.exchange})")
            else:
                logger.info("🐸 No valuable positions to set as main_position (all friends have $0 value)")

    def _load_friends_from_real_positions(self) -> None:
        """
        Load friends from LIVE API balances + cross-reference with cost basis tracker.
        
        THE TRUTH:
        - LIVE API balances = What we ACTUALLY HOLD right now
        - CostBasisTracker = What we PAID for stuff (with FIFO accounting)
        
        We might have bought/sold same coin multiple times!
        Only what we HOLD NOW matters for leaping.
        
        Cost basis comes from remaining lots after FIFO sales.
        """
        # First fetch LIVE balances from all exchanges
        live_balances = self._fetch_live_balances()
        
        if not live_balances:
            logger.info(
                "No balance observations returned; cached/local portfolio state "
                "was not replaced with an unauthenticated fallback"
            )
            return
        
        # Initialize cost basis tracker for accurate cost basis calculation
        cost_basis_tracker = None
        try:
            from aureon.portfolio.cost_basis_tracker import CostBasisTracker
            cost_basis_tracker = CostBasisTracker()
            logger.info("📊 Cost Basis Tracker: WIRED for accurate baggage calculation")
        except Exception as e:
            logger.warning(f"⚠️ Cost Basis Tracker unavailable: {e}")
        
        # Build friends from LIVE balances
        for asset, (qty, exchange) in live_balances.items():
            if qty <= 0:
                continue
            
            # Skip stablecoins (they're cash, not friends)
            if asset in ['USD', 'USDC', 'USDT', 'BUSD', 'EUR', 'GBP', 'TUSD']:
                self.cash_balance += qty if asset in ['USD', 'USDC', 'USDT', 'BUSD'] else 0
                continue
            
            # Get ACCURATE cost basis using the tracker
            cost_basis = 0.0
            entry_price = 0.0
            
            if cost_basis_tracker:
                # Try different symbol formats to find the position
                # The tracker expects just the base asset name (e.g., "ADA", "BTC")
                pos = cost_basis_tracker.get_cost_basis(asset, exchange)
                if pos:
                    # Use the tracker's accurate cost basis (remaining after FIFO)
                    cost_basis = pos.get('total_cost', 0)
                    entry_price = pos.get('avg_entry_price', 0)
                    logger.info(f"   📊 {asset}: Found cost basis ${cost_basis:.2f} @ ${entry_price:.4f}")
                else:
                    logger.info(f"   📊 {asset}: No cost basis found in tracker")
            else:
                # Fallback: read cost_basis_history.json directly with correct key format
                cost_basis_data = {}
                if self.cost_basis_file.exists():
                    try:
                        with open(self.cost_basis_file, 'r') as f:
                            cb_data = json.load(f)
                            cost_basis_data = cb_data.get('positions', {})
                    except Exception as e:
                        logger.warning(f"⚠️ Could not load cost basis file: {e}")
                
                # Try the correct key format: "exchange:asset"
                fallback_key = f"{exchange}:{asset}"
                if fallback_key in cost_basis_data:
                    cb = cost_basis_data[fallback_key]
                    total_cost = cb.get('total_cost', 0)
                    total_qty = cb.get('total_quantity', 0)
                    if total_qty > 0:
                        # This is still approximate - better than nothing
                        cost_per_unit = total_cost / total_qty
                        cost_basis = qty * cost_per_unit
                        entry_price = cb.get('avg_entry_price', cost_per_unit)
                        logger.info(f"   📊 {asset}: Fallback cost basis ${cost_basis:.2f} @ ${entry_price:.4f}")
                
                # Also try without exchange prefix as backup
                elif asset in cost_basis_data:
                    cb = cost_basis_data[asset]
                    total_cost = cb.get('total_cost', 0)
                    total_qty = cb.get('total_quantity', 0)
                    if total_qty > 0:
                        cost_per_unit = total_cost / total_qty
                        cost_basis = qty * cost_per_unit
                        entry_price = cb.get('avg_entry_price', cost_per_unit)
                        logger.info(f"   📊 {asset}: Fallback cost basis ${cost_basis:.2f} @ ${entry_price:.4f}")
            
            # If no cost basis found, assume current price (no baggage)
            if cost_basis == 0:
                # Try to get current price for initial cost basis
                current_price = 0.0
                # This is approximate - in real usage, market data would be available
                entry_price = current_price or 1.0  # Fallback
                cost_basis = qty * entry_price
                logger.info(f"   📊 {asset}: No cost basis found, assuming ${cost_basis:.2f} @ ${entry_price:.4f}")
            
            self.friends[asset] = Friend(
                symbol=asset,
                quantity=qty,
                cost_basis=cost_basis,
                entry_price=entry_price,
                current_price=entry_price,  # Will be updated with market data
                exchange=exchange
            )
        
        logger.info(f"👥 Loaded {len(self.friends)} friends from LIVE API balances")
        logger.info(f"   💵 Cash balance: ${self.cash_balance:.2f}")
        
        # Log summary with baggage info
        total_value = sum(f.current_value for f in self.friends.values())
        total_baggage = sum(f.baggage for f in self.friends.values())
        clear_friends = sum(1 for f in self.friends.values() if f.is_clear)
        
        logger.info(f"   💰 Total position value: ${total_value:.2f}")
        logger.info(f"   🧳 Total baggage: ${total_baggage:.2f}")
        logger.info(f"   ✅ Clear friends: {clear_friends}/{len(self.friends)}")
        
        # Log by exchange
        by_exchange: Dict[str, int] = {}
        for f in self.friends.values():
            by_exchange[f.exchange] = by_exchange.get(f.exchange, 0) + 1
        for ex, count in by_exchange.items():
            logger.info(f"   📍 {ex}: {count} positions")
    
    def _fetch_live_balances(self) -> Dict[str, Tuple[float, str]]:
        """Read balances only through the explicitly injected read-only seam."""

        balances: Dict[str, Tuple[float, str]] = {}
        reader = getattr(self, "_balance_reader", None)
        if not callable(reader):
            logger.info("Balance observation unavailable: no injected reader")
            return balances

        for exchange in ("binance", "alpaca", "kraken"):
            try:
                observed = reader(exchange)
            except Exception as exc:
                logger.warning(f"Balance reader failed for {exchange}: {type(exc).__name__}")
                continue
            if isinstance(observed, Mapping):
                entries = observed.items()
            elif isinstance(observed, (list, tuple)):
                entries = (
                    (item.get("symbol", ""), item.get("qty", 0))
                    for item in observed
                    if isinstance(item, Mapping)
                )
            else:
                continue
            for raw_asset, raw_qty in entries:
                try:
                    quantity = float(raw_qty)
                except (TypeError, ValueError, OverflowError):
                    continue
                if not math.isfinite(quantity) or quantity <= 0:
                    continue
                asset = str(raw_asset or "").upper().replace("/USD", "")
                if exchange == "kraken":
                    asset = asset.removesuffix(".B")
                    if asset == "XXBT":
                        asset = "BTC"
                    elif asset.startswith(("X", "Z")) and len(asset) > 3:
                        asset = asset[1:]
                if not asset:
                    continue
                if asset in balances:
                    prior, _prior_exchange = balances[asset]
                    balances[asset] = (prior + quantity, "multi")
                else:
                    balances[asset] = (quantity, exchange)
        return balances

    def _get_exchange_client(self, exchange: str):
        """Compatibility shim: raw exchange clients are no longer reachable."""

        del exchange
        return None

    def _pair_candidates(self, base_symbol: str, exchange: str) -> List[str]:
        base = (base_symbol or "").upper()
        if exchange == 'binance':
            return [f"{base}USDT", f"{base}USDC", f"{base}USD"]
        if exchange == 'kraken':
            kraken_base = "XBT" if base == "BTC" else base
            return [
                f"{kraken_base}USD",
                f"X{kraken_base}ZUSD",
                f"{kraken_base}/USD",
            ]
        if exchange == 'alpaca':
            return [f"{base}USD", f"{base}/USD"]
        return [f"{base}USD"]

    def _order_failed(self, response: Dict[str, Any]) -> bool:
        """Compatibility predicate: only an explicit terminal fill is success."""
        if not isinstance(response, dict):
            return True
        if response.get("rejected") or response.get("error") or response.get("dryRun"):
            return True
        return str(response.get("status") or "").strip().upper() != "FILLED"

    def _pending_order_key(self, exchange: str, base_symbol: str, side: str) -> str:
        return "|".join(
            (
                str(exchange or "").strip().lower(),
                str(base_symbol or "").strip().upper(),
                str(side or "").strip().upper(),
            )
        )

    def _pending_registry(self) -> Dict[str, Dict[str, Any]]:
        registry = getattr(self, "_pending_orders", None)
        if not isinstance(registry, dict):
            registry = {}
            self._pending_orders = registry
        return registry

    def _not_submitted_receipt(
        self,
        exchange: str,
        symbol: str,
        side: str,
        *,
        reason: str,
    ) -> Dict[str, Any]:
        receipt = {
            "success": False,
            "status": "not_submitted",
            "data_status": "not_submitted",
            "truth_status": "not_submitted",
            "submitted": False,
            "reconciliation_required": False,
            "order_id": None,
            "filled_qty": None,
            "filled_price": None,
            "filled_notional": None,
            "fee_by_asset": {},
            "provider_timestamp": None,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
            "exchange": exchange,
            "symbol": symbol,
            "side": side.upper(),
            "reason": reason,
        }
        self.last_execution_receipt = receipt
        return receipt

    def _remember_pending_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        receipt: Dict[str, Any],
        *,
        quantity: Optional[float] = None,
        quote_qty: Optional[float] = None,
    ) -> Dict[str, Any]:
        pending = {
            "success": False,
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": receipt.get("truth_status") or "no_data",
            "submitted": receipt.get("submitted"),
            "reconciliation_required": True,
            "order_id": receipt.get("order_id")
            or _valid_provider_identifier(
                _first_receipt_value(
                    receipt, "orderId", "id", "order_id", "txid"
                )
            ),
            "filled_qty": None,
            "filled_price": None,
            "filled_notional": None,
            "fee_by_asset": {},
            "provider_timestamp": None,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
            "exchange": exchange,
            "symbol": symbol,
            "side": side.upper(),
            "requested_quantity": quantity,
            "requested_quote_quantity": quote_qty,
            "recorded_at": time.time(),
            "reason": receipt.get("reason")
            or "terminal_provider_fill_receipt_required",
        }
        key = self._pending_order_key(exchange, symbol, side)
        self._pending_registry()[key] = pending
        self.last_execution_receipt = pending
        save_state = getattr(self, "_save_state", None)
        if callable(save_state):
            save_state()
        return pending

    def _commit_resolved_orders(
        self, *orders: Tuple[str, str, str]
    ) -> None:
        """
        Clear duplicate blocks only in the same save as the state mutation.

        A terminal readback alone does not clear a block: the organism must
        first commit the corresponding holdings/accounting transition.
        """
        registry = self._pending_registry()
        for exchange, symbol, side in orders:
            registry.pop(self._pending_order_key(exchange, symbol, side), None)
        self._save_state()

    def _remember_terminal_uncommitted(
        self,
        exchange: str,
        symbol: str,
        side: str,
        receipt: Dict[str, Any],
        *,
        quantity: Optional[float] = None,
        quote_qty: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Persist a verified fill until its holdings transition is committed.

        This closes the crash window between a terminal first leg and a pending
        dependent leg. Re-entry can reuse the verified receipt, but cannot
        submit the same order again.
        """
        terminal = dict(receipt)
        lock = {
            "success": False,
            "status": "terminal_fill_uncommitted",
            "data_status": "live",
            "truth_status": "real_observed",
            "submitted": True,
            "reconciliation_required": False,
            "order_id": terminal.get("order_id"),
            "filled_qty": terminal.get("filled_qty"),
            "filled_price": terminal.get("filled_price"),
            "filled_notional": terminal.get("filled_notional"),
            "fee_by_asset": dict(terminal.get("fee_by_asset") or {}),
            "provider_timestamp": terminal.get("provider_timestamp"),
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
            "exchange": exchange,
            "symbol": symbol,
            "side": side.upper(),
            "requested_quantity": quantity,
            "requested_quote_quantity": quote_qty,
            "recorded_at": time.time(),
            "reason": "terminal_fill_waiting_for_state_commit",
            "terminal_receipt": terminal,
        }
        key = self._pending_order_key(exchange, symbol, side)
        self._pending_registry()[key] = lock
        self.last_execution_receipt = terminal
        save_state = getattr(self, "_save_state", None)
        if callable(save_state):
            save_state()
        return terminal

    def _reuse_terminal_uncommitted(
        self,
        exchange: str,
        symbol: str,
        side: str,
        lock: Dict[str, Any],
        *,
        quantity: Optional[float] = None,
        quote_qty: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Validate and reuse only an internally classified terminal lock."""
        terminal = lock.get("terminal_receipt")
        if not isinstance(terminal, dict):
            return None
        if (
            terminal.get("success") is not True
            or terminal.get("status") != "filled"
            or terminal.get("data_status") != "live"
            or terminal.get("truth_status") != "real_observed"
            or terminal.get("eligible_for_accounting") is not True
            or terminal.get("eligible_for_learning") is not True
            or terminal.get("generated_values") is not False
            or terminal.get("exchange") != exchange.strip().lower()
            or terminal.get("symbol") != symbol.strip().upper()
            or terminal.get("side") != side.strip().upper()
            or _valid_provider_identifier(terminal.get("order_id")) is None
            or _finite_receipt_number(
                terminal.get("filled_qty"), positive=True
            )
            is None
            or _finite_receipt_number(
                terminal.get("filled_price"), positive=True
            )
            is None
            or _finite_receipt_number(
                terminal.get("filled_notional"), positive=True
            )
            is None
            or _provider_receipt_timestamp(
                terminal.get("provider_timestamp")
            )
            is None
        ):
            return None
        requested_quantity = _finite_receipt_number(quantity, positive=True)
        locked_quantity = _finite_receipt_number(
            lock.get("requested_quantity"), positive=True
        )
        if (
            requested_quantity is not None
            and locked_quantity is not None
            and abs(requested_quantity - locked_quantity)
            > max(1e-12, locked_quantity * 0.001)
        ):
            return None
        requested_quote = _finite_receipt_number(quote_qty, positive=True)
        locked_quote = _finite_receipt_number(
            lock.get("requested_quote_quantity"), positive=True
        )
        if (
            requested_quote is not None
            and locked_quote is not None
            and abs(requested_quote - locked_quote)
            > max(1e-8, locked_quote * 0.001)
        ):
            return None
        fees = terminal.get("fee_by_asset")
        if not isinstance(fees, dict) or any(
            not str(asset).strip()
            or _finite_receipt_number(value, nonnegative=True) is None
            for asset, value in fees.items()
        ):
            return None
        self.last_execution_receipt = terminal
        return terminal

    def _resolve_terminal_fill(
        self,
        exchange: str,
        symbol: str,
        side: str,
        response: Dict[str, Any],
        *,
        quantity: Optional[float] = None,
        quote_qty: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Require a complete terminal receipt, with one read-only reconciliation.

        The readback can complete an acknowledged order, but this method never
        submits another order. An unresolved receipt remains in the duplicate
        block registry until a provider terminal readback is observed.
        """
        if (
            isinstance(response, dict)
            and response.get("status") == "terminal_fill_uncommitted"
        ):
            reused = self._reuse_terminal_uncommitted(
                exchange,
                symbol,
                side,
                response,
                quantity=quantity,
                quote_qty=quote_qty,
            )
            if reused is not None:
                return reused
            self.last_execution_receipt = response
            return response

        classified = _classify_terminal_order_receipt(
            response,
            exchange,
            expected_side=side,
            expected_symbol=symbol,
        )
        if classified["success"]:
            return self._remember_terminal_uncommitted(
                exchange,
                symbol,
                side,
                classified,
                quantity=quantity,
                quote_qty=quote_qty,
            )

        order_id = classified.get("order_id")
        if (
            classified.get("status") == "pending_reconciliation"
            and order_id
        ):
            query = None
            status_reader = getattr(self, "_order_status_reader", None)
            try:
                if callable(status_reader):
                    query = status_reader(exchange, str(order_id))
            except Exception as exc:
                classified["reason"] = (
                    f"terminal_provider_readback_failed:{type(exc).__name__}"
                )
            if isinstance(query, dict):
                readback = _classify_terminal_order_receipt(
                    query,
                    exchange,
                    expected_side=side,
                    expected_symbol=symbol,
                )
                if readback["success"]:
                    return self._remember_terminal_uncommitted(
                        exchange,
                        symbol,
                        side,
                        readback,
                        quantity=quantity,
                        quote_qty=quote_qty,
                    )
                classified = readback

        if classified.get("status") == "pending_reconciliation":
            return self._remember_pending_order(
                exchange,
                symbol,
                side,
                classified,
                quantity=quantity,
                quote_qty=quote_qty,
            )
        self.last_execution_receipt = classified
        return classified

    def _record_observed_fees(self, *receipts: Dict[str, Any]) -> None:
        """Accumulate provider-observed fees by their actual asset."""
        ledger = getattr(self, "observed_fees_by_asset", None)
        if not isinstance(ledger, dict):
            ledger = {}
            self.observed_fees_by_asset = ledger
        for receipt in receipts:
            for asset, value in (receipt.get("fee_by_asset") or {}).items():
                fee = _finite_receipt_number(value, nonnegative=True)
                if fee is not None:
                    ledger[asset] = ledger.get(asset, 0.0) + fee

    @staticmethod
    def _net_base_quantity(receipt: Dict[str, Any], base_symbol: str) -> float:
        filled_qty = float(receipt["filled_qty"])
        base_fee = float(
            (receipt.get("fee_by_asset") or {}).get(base_symbol.upper(), 0.0)
        )
        return max(0.0, filled_qty - base_fee)

    def _base_symbol_variants(self, base_symbol: str) -> set[str]:
        base = (base_symbol or "").upper().strip()
        for suffix in ("/USDT", "/USDC", "/USD", "USDT", "USDC", "USD"):
            if base.endswith(suffix):
                base = base[:-len(suffix)]
                break
        variants = {base}
        if base == "BTC":
            variants.update({"XBT", "XXBT", "XBTC"})
        if base == "XBT":
            variants.update({"BTC", "XXBT", "XBTC"})
        variants.update({f"X{base}", f"Z{base}"})
        return {v for v in variants if v}

    def _asset_symbol_candidates(self, asset: str) -> set[str]:
        raw = (asset or "").upper().strip()
        if not raw:
            return set()
        trimmed = raw
        for suffix in (".B", ".F", ".S"):
            if trimmed.endswith(suffix):
                trimmed = trimmed[:-len(suffix)]
        candidates = {raw, trimmed}
        if trimmed.startswith("X") and len(trimmed) > 1:
            candidates.add(trimmed[1:])
        if trimmed.startswith("Z") and len(trimmed) > 1:
            candidates.add(trimmed[1:])
        if trimmed == "XXBT":
            candidates.update({"XBT", "BTC"})
        if trimmed == "XBT":
            candidates.add("BTC")
        return {c for c in candidates if c}

    def _get_available_base_quantity(self, exchange: str, base_symbol: str) -> float:
        reader = getattr(self, "_balance_reader", None)
        if not callable(reader):
            return 0.0
        try:
            observed = reader(exchange)
        except Exception:
            return 0.0
        if isinstance(observed, Mapping):
            entries = observed.items()
        elif isinstance(observed, (list, tuple)):
            entries = (
                (item.get("symbol", ""), item.get("qty", 0))
                for item in observed
                if isinstance(item, Mapping)
            )
        else:
            return 0.0

        variants = self._base_symbol_variants(base_symbol)
        available = 0.0
        for asset, qty in entries:
            try:
                qty_f = float(qty or 0)
            except Exception:
                continue
            if qty_f <= 0:
                continue
            asset_candidates = self._asset_symbol_candidates(str(asset))
            if asset_candidates.intersection(variants):
                available += qty_f
        return max(0.0, available)

    def _extract_order_id(self, response: Dict[str, Any]) -> Optional[str]:
        if not isinstance(response, dict):
            return None
        for key in (
            "orderId",
            "id",
            "clientOrderId",
            "order_id",
            "txid",
        ):
            value = response.get(key)
            if isinstance(value, list):
                value = value[0] if value else None
            if value:
                return str(value)
        return None

    def _log_order_id(self, label: str, exchange: str, symbol: str, side: str, response: Dict[str, Any]) -> None:
        order_id = self._extract_order_id(response)
        if order_id:
            logger.info(f"   🧾 {label} ORDER ID ({exchange} {side} {symbol}): {order_id}")
            return
        logger.warning(f"⚠️ {label} order missing ID ({exchange} {side} {symbol}): {response}")

    def _log_order_summary(self, label: str, exchange: str, sell_res: Dict[str, Any], buy_res: Dict[str, Any]) -> None:
        sell_id = self._extract_order_id(sell_res) or "missing"
        buy_id = self._extract_order_id(buy_res) or "missing"
        logger.info(f"   ✅ LIVE ORDER SUMMARY ({label} {exchange}): SELL={sell_id} BUY={buy_id}")

    def _place_market_order(self, exchange: str, base_symbol: str, side: str, quantity: float | None = None, quote_qty: float | None = None) -> Dict[str, Any]:
        key = self._pending_order_key(exchange, base_symbol, side)
        existing = self._pending_registry().get(key)
        if existing:
            blocked = dict(existing)
            blocked["reason"] = "existing_order_requires_terminal_reconciliation"
            self.last_execution_receipt = blocked
            return blocked

        if not getattr(self, "live_trading", False):
            return self._not_submitted_receipt(
                exchange,
                base_symbol,
                side,
                reason=(
                    "queen_dry_run"
                    if getattr(self, "dry_run", True)
                    else "live_trading_disabled"
                ),
            )
        parsed_quantity = _finite_receipt_number(quantity, positive=True)
        parsed_quote_qty = _finite_receipt_number(quote_qty, positive=True)
        if (parsed_quantity is None) == (parsed_quote_qty is None):
            return self._not_submitted_receipt(
                exchange,
                base_symbol,
                side,
                reason="exactly_one_order_quantity_required",
            )
        pairs = self._pair_candidates(base_symbol, exchange)
        if not pairs:
            return self._not_submitted_receipt(
                exchange, base_symbol, side, reason="exact_provider_pair_unavailable"
            )
        pair = pairs[0]
        plan = ForceTradePlan(
            provider=exchange,
            symbol=pair,
            side=side,
            quantity=str(parsed_quantity if parsed_quantity is not None else parsed_quote_qty),
            quantity_kind=(
                "base_units" if parsed_quantity is not None else "quote_units"
            ),
        )
        authorization_provider = getattr(self, "_authorization_provider", None)
        dispatcher = getattr(self, "_final_order_dispatcher", None)
        if not callable(authorization_provider) or not callable(dispatcher):
            return self._not_submitted_receipt(
                exchange,
                base_symbol,
                side,
                reason="governed_order_boundary_unavailable",
            )
        try:
            authorization = authorization_provider(plan)
        except Exception:
            authorization = None
        decision = claim_queen_force_trade_authority(
            plan=plan,
            authorization=authorization,
        )
        if not decision.allowed:
            reason = (
                decision.missing_requirements[0]
                if decision.missing_requirements
                else "governed_order_authorization_denied"
            )
            return self._not_submitted_receipt(
                exchange, base_symbol, side, reason=reason
            )

        try:
            response = dispatcher(plan)
        except Exception as exc:
            return self._remember_pending_order(
                exchange,
                base_symbol,
                side,
                {
                    "truth_status": "no_data",
                    "submitted": None,
                    "reason": (
                        "ambiguous_authorized_order_submission:"
                        f"{type(exc).__name__}"
                    ),
                },
                quantity=quantity,
                quote_qty=quote_qty,
            )
        if not isinstance(response, Mapping):
            return self._remember_pending_order(
                exchange,
                base_symbol,
                side,
                {
                    "truth_status": "no_data",
                    "submitted": None,
                    "reason": "ambiguous_authorized_order_receipt",
                },
                quantity=quantity,
                quote_qty=quote_qty,
            )
        res = dict(response)
        classified = _classify_terminal_order_receipt(
            res,
            exchange,
            expected_side=side,
            expected_symbol=base_symbol,
        )
        if classified["success"]:
            return res
        if str(res.get("error", "")).lower() == "volume_minimum":
            return {
                "error": "volume_minimum",
                "exchange": exchange,
                "symbol": base_symbol,
                "side": side,
                "details": res,
            }
        if (
            classified.get("status") == "rejected"
            and (res.get("rejected") is True or res.get("submitted") is False)
            and not classified.get("submitted")
        ):
            return res
        if classified.get("status") == "rejected":
            classified = {
                "truth_status": classified.get("truth_status"),
                "submitted": None,
                "reason": "ambiguous_provider_error_response",
            }
        return self._remember_pending_order(
            exchange,
            base_symbol,
            side,
            classified,
            quantity=quantity,
            quote_qty=quote_qty,
        )
    
    def _load_friends_from_cost_basis_fallback(self) -> None:
        """Fallback: Load from cost_basis_history.json if tracked_positions.json doesn't exist."""
        try:
            if not self.cost_basis_file.exists():
                logger.warning(f"⚠️ Cost basis file not found: {self.cost_basis_file}")
                return
            
            with open(self.cost_basis_file, 'r') as f:
                data = json.load(f)
            
            positions = data.get('positions', {})
            
            for symbol, pos_data in positions.items():
                if not isinstance(pos_data, dict):
                    continue
                
                qty = pos_data.get('total_quantity', 0)
                cost = pos_data.get('total_cost', 0)
                entry_price = pos_data.get('avg_entry_price', 0)
                exchange = pos_data.get('exchange', 'binance')
                asset = pos_data.get('asset', symbol.replace('USDC', '').replace('USD', '').replace('EUR', ''))
                
                if qty <= 0 or cost <= 0:
                    continue
                
                self.friends[asset] = Friend(
                    symbol=asset,
                    quantity=qty,
                    cost_basis=cost,
                    entry_price=entry_price,
                    current_price=entry_price,
                    exchange=exchange
                )
            
            logger.warning(f"⚠️ Loaded {len(self.friends)} friends from cost_basis FALLBACK (not live positions!)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load from cost_basis fallback: {e}")
    
    def update_friends_prices(self) -> None:
        """Update all friends with current market prices."""
        for symbol, friend in self.friends.items():
            market_coin = self.market_data.get(symbol)
            if market_coin:
                friend.update_price(market_coin.price)
    
    @property
    def total_portfolio_value(self) -> float:
        """Total value of all friends + cash."""
        friends_value = sum(f.current_value for f in self.friends.values())
        return friends_value + self.cash_balance
    
    @property
    def total_baggage(self) -> float:
        """Total baggage (unrealized loss) across all friends."""
        return sum(f.baggage for f in self.friends.values())
    
    @property
    def friends_with_baggage(self) -> List[Friend]:
        """All friends that have baggage (underwater)."""
        return [f for f in self.friends.values() if not f.is_clear]
    
    @property
    def clear_friends(self) -> List[Friend]:
        """All friends that are clear (at or above cost basis)."""
        return [f for f in self.friends.values() if f.is_clear]
    
    def get_best_leaper(self) -> Optional[Friend]:
        """
        Get the best friend to leap from.
        
        Priority:
        1. Cash (cleanest - no baggage)
        2. Friends with profit (can drop breadcrumbs)
        3. Friends with baggage (need to clear via deeper dip)
        """
        # Cash first
        if self.cash_balance > self.fee_structure.min_trade_size:
            return Friend(
                symbol="CASH",
                quantity=self.cash_balance,
                cost_basis=self.cash_balance,
                entry_price=1.0,
                current_price=1.0,
                exchange=self.exchange
            )
        
        # Find friend with most profit (clear + highest gain)
        clear = sorted(self.clear_friends, key=lambda f: f.profit_available, reverse=True)
        if clear and clear[0].leap_value > self.fee_structure.min_trade_size:
            return clear[0]
        
        # Find friend with baggage but enough value to leap
        baggage = sorted(self.friends_with_baggage, key=lambda f: f.leap_value, reverse=True)
        if baggage and baggage[0].leap_value > self.fee_structure.min_trade_size:
            return baggage[0]
        
        return None
    
    def show_friends_situation(self) -> str:
        """
        Display the current situation of all friends.
        
        Shows:
        - Total portfolio value
        - Cash balance (cleanest friend)
        - Friends with profit (ready to leap!)
        - Friends with baggage (need clearing)
        """
        self.update_friends_prices()
        
        lines = []
        lines.append("═" * 70)
        lines.append("👥 FRIENDS SITUATION - Who's Ready to Leap?")
        lines.append("═" * 70)
        
        # Cash
        lines.append(f"\n💵 CASH (Cleanest Friend): ${self.cash_balance:.2f}")
        
        # Portfolio totals
        lines.append("\n📊 PORTFOLIO SUMMARY:")
        lines.append(f"   💰 Total Value: ${self.total_portfolio_value:.2f}")
        lines.append(f"   ⚠️ Total Baggage: ${self.total_baggage:.2f}")
        lines.append(f"   👥 Total Friends: {len(self.friends)}")
        
        # Clear friends (ready to leap!)
        clear = self.clear_friends
        if clear:
            lines.append(f"\n✅ CLEAR FRIENDS ({len(clear)}) - Ready to Leap!")
            for f in sorted(clear, key=lambda x: x.profit_available, reverse=True)[:10]:
                profit = f.profit_available
                lines.append(f"   {f.symbol}: ${f.current_value:.2f} (+${profit:.2f} profit)")
        
        # Friends with baggage
        baggage = self.friends_with_baggage
        if baggage:
            lines.append(f"\n⚠️ FRIENDS WITH BAGGAGE ({len(baggage)}) - Need Deeper Dips!")
            for f in sorted(baggage, key=lambda x: x.baggage, reverse=True)[:10]:
                lines.append(f"   {f.symbol}: ${f.current_value:.2f} (-${f.baggage:.2f} baggage, {f.baggage_percent:.1f}%)")
        
        lines.append("\n" + "═" * 70)
        
        return "\n".join(lines)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MARKET DATA FETCHING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def fetch_market_data(self) -> Dict[str, MarketCoin]:
        """Read market observations only through the injected read-only boundary.

        The default machine has no market-data reader and therefore performs no
        network work.  Integrations may inject a reader accepting
        ``(provider, symbol_or_none)``; passing ``None`` requests that
        provider's broad ticker list.  This module never constructs or falls
        back to a provider client.
        """
        self.market_data.clear()
        self.last_scan_time = None

        reader = getattr(self, "_market_data_reader", None)
        if not callable(reader):
            logger.info("Market observation skipped: no injected read-only reader")
            return self.market_data

        def _to_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except Exception:
                return default

        def _add_ticker(ticker: Dict[str, Any], quote_suffix: str = "USDC") -> None:
            symbol = str(ticker.get('symbol', ''))
            if not symbol or not symbol.endswith(quote_suffix):
                return

            coin_symbol = symbol[:-len(quote_suffix)]
            if not coin_symbol:
                return

            price = _to_float(ticker.get('lastPrice'))
            volume = _to_float(ticker.get('quoteVolume'))
            if price <= 0.0:
                return

            # Keep high-liquidity universe wide, but always keep held assets (handled later)
            if volume < 100000 and coin_symbol not in held_symbols:
                return

            self.market_data[coin_symbol] = MarketCoin(
                symbol=coin_symbol,
                price=price,
                change_24h=_to_float(ticker.get('priceChangePercent')),
                volume_24h=volume,
                high_24h=_to_float(ticker.get('highPrice'), price),
                low_24h=_to_float(ticker.get('lowPrice'), price),
            )

        def _base_symbol(symbol: str) -> str:
            raw = str(symbol).split(":")[-1].split("/")[0].upper()
            # Strip Kraken staking/bond suffixes so ADA.S → ADA, SCRT21.S → SCRT21
            for _sfx in (".S", ".B", ".F", ".M", ".P"):
                if raw.endswith(_sfx):
                    raw = raw[:-len(_sfx)]
            return raw

        held_symbols = {_base_symbol(s) for s in self.friends.keys() if s and s != "CASH"}
        exchange_fetches: List[str] = []

        def _broad_tickers(provider: str) -> List[Mapping[str, Any]]:
            observed = reader(provider, None)
            if isinstance(observed, Mapping):
                nested = observed.get("tickers")
                if isinstance(nested, list):
                    observed = nested
                else:
                    observed = [observed]
            if not isinstance(observed, (list, tuple)):
                return []
            return [item for item in observed if isinstance(item, Mapping)]

        # Broad observations remain best-effort and read-only.  A broken
        # integration does not trigger a second, less-governed transport path.
        for provider, quote_suffix in (
            ("binance", "USDC"),
            ("alpaca", "USD"),
            ("kraken", "USD"),
        ):
            try:
                tickers = _broad_tickers(provider)
                for ticker in tickers:
                    symbol = str(ticker.get("symbol", ""))
                    if provider == "kraken" and symbol.endswith("USDC"):
                        _add_ticker(dict(ticker), quote_suffix="USDC")
                    else:
                        _add_ticker(dict(ticker), quote_suffix=quote_suffix)
                if tickers:
                    exchange_fetches.append(provider)
            except Exception as exc:
                logger.debug("%s market observation unavailable: %s", provider, exc)

        # Give held assets an explicit read-only observation attempt if a broad
        # list did not include them.  This still uses the same injected reader.
        for friend in self.friends.values():
            friend_symbol = _base_symbol(friend.symbol)
            if friend_symbol in self.market_data:
                # Keep alias key so update_friends_prices can resolve raw symbols too
                self.market_data.setdefault(friend.symbol, self.market_data[friend_symbol])
                continue

            primary_exchange = str(friend.exchange or self.exchange or "binance").lower().split(":")[-1]
            candidate_exchanges = [primary_exchange, 'binance', 'kraken', 'alpaca']
            seen = set()
            candidate_exchanges = [ex for ex in candidate_exchanges if not (ex in seen or seen.add(ex))]

            for ex in candidate_exchanges:
                try:
                    quote_sfx = "USDC"
                    pair = f"{friend_symbol}USDC"
                    if ex == "kraken":
                        quote_sfx = "USD"
                        pair = f"{friend_symbol}USD"
                    elif ex == "alpaca":
                        quote_sfx = "USD"
                        pair = f"{friend_symbol}/USD"
                    observed = reader(ex, pair)
                    if not isinstance(observed, Mapping):
                        continue
                    ticker = dict(observed)
                    if ex == "alpaca" and "price" in ticker:
                        ticker = {
                            "symbol": f"{friend_symbol}USD",
                            "lastPrice": ticker.get("price"),
                            "priceChangePercent": ticker.get("change_24h", 0),
                            "quoteVolume": ticker.get("volume_24h", 0),
                            "highPrice": ticker.get("high_24h", ticker.get("price")),
                            "lowPrice": ticker.get("low_24h", ticker.get("price")),
                        }
                    if _to_float(ticker.get("lastPrice")) > 0:
                        _add_ticker(ticker, quote_suffix=quote_sfx)
                        if friend_symbol in self.market_data:
                            self.market_data.setdefault(friend.symbol, self.market_data[friend_symbol])
                        break
                except Exception:
                    continue

        if not self.market_data:
            logger.info("No market observations returned by injected reader")
            return self.market_data

        self.last_scan_time = datetime.now()
        src = ", ".join(exchange_fetches) if exchange_fetches else "held-symbol direct lookups"
        logger.info(f"📊 Fetched {len(self.market_data)} coins from exchanges ({src})")
        return self.market_data
    
    def get_sorted_by_dip(self) -> List[MarketCoin]:
        """Get coins sorted by 24h loss (biggest losers first)."""
        return sorted(
            self.market_data.values(),
            key=lambda x: x.change_24h
        )
    
    def get_coins_in_red(self) -> List[MarketCoin]:
        """Get all coins currently in the red."""
        return [c for c in self.market_data.values() if c.change_24h < 0]
    
    def detect_whale_activity(self, symbol: str) -> Tuple[bool, str]:
        """
        🌊 Use Ocean Wave Scanner to detect whale/shark activity on a symbol.
        
        Returns: (has_whale_activity, activity_description)
        
        WHALE LOGIC FOR LEAPING:
        - If target coin has WHALE BUYING activity → confidence boost (recovery likely!)
        - If target coin has WHALE SELLING activity → caution (might dip more)
        - If no whale data → proceed with normal math
        """
        if not self.ocean_scanner:
            return False, "No Ocean Scanner available"
        
        try:
            # Query Ocean Scanner for whale activity tracking
            # The scanner tracks whale buys/sells from bots dictionary
            has_whale_activity = False
            whale_description = "No whale activity detected"
            
            # Check if scanner has detected whales on this symbol
            for _bot_id, bot in self.ocean_scanner.bots.items():
                if bot.symbol == symbol and bot.size_class in ['whale', 'megalodon']:
                    has_whale_activity = True
                    # Get direction from recent activity
                    whale_description = f"🐋 WHALE detected! Size: {bot.size_class}, Pattern: {bot.pattern}"
                    break
            
            # If no specific whale detected, return false
            if not has_whale_activity:
                return False, "No whale activity detected"
            
            # Whale detected = confidence boost!
            return True, whale_description
        
        except Exception as e:
            logger.debug(f"Whale detection check failed for {symbol}: {e}")
            return False, "Whale detection error"
    
    def scan_entire_ocean_for_whales(self) -> Dict[str, Dict]:
        """
        🌊 SCAN THE ENTIRE OCEAN - Every coin, every whale, complete visibility!
        
        Returns mapping of coin symbols to whale activity:
        {
            "BTC": {"whales": 5, "sharks": 12, "minnows": 45, "total_volume_usd": 2500000},
            "ETH": {"whales": 3, "sharks": 8, "minnows": 28, ...},
            ...
        }
        """
        ocean_map = {}
        
        if not self.market_data:
            return ocean_map
        
        # Scan every coin in the market
        for symbol, coin_data in self.market_data.items():
            # Check Ocean Scanner for whale activity on this coin
            has_whale, whale_desc = self.detect_whale_activity(symbol)
            
            # Get change_24h - handle both dict and MarketCoin object
            if hasattr(coin_data, 'change_24h'):
                volume_indicator = coin_data.change_24h
                price = coin_data.price
            else:
                volume_indicator = coin_data.get('change_24h', 0)
                price = coin_data.get('price', 0)
            
            # Classify activity intensity
            if volume_indicator > 10:  # Large positive movement
                whale_count = max(1, int(abs(volume_indicator) / 5))
                shark_count = whale_count * 2
                minnow_count = whale_count * 5
                size_class = "🐋 WHALE TERRITORY"
            elif volume_indicator > 5:
                whale_count = 0
                shark_count = max(1, int(abs(volume_indicator) / 5))
                minnow_count = shark_count * 3
                size_class = "🦈 SHARK WATERS"
            elif volume_indicator > -5:
                whale_count = 0
                shark_count = 0
                minnow_count = max(1, int(abs(volume_indicator) / 2))
                size_class = "🐟 MINNOW POND"
            else:
                whale_count = 0
                shark_count = 0
                minnow_count = 0
                size_class = "⚪ QUIET WATERS"
            
            # Calculate estimated activity volume
            if price > 0:
                total_volume_usd = (whale_count * 1_000_000) + (shark_count * 100_000) + (minnow_count * 10_000)
            else:
                total_volume_usd = 0
            
            ocean_map[symbol] = {
                "price": price,
                "change_24h": volume_indicator,
                "size_class": size_class,
                "whale_count": whale_count,
                "shark_count": shark_count,
                "minnow_count": minnow_count,
                "total_volume_usd": total_volume_usd,
                "scanner_alert": whale_desc if has_whale else None,
            }
        
        return ocean_map
    
    def get_ocean_summary(self, top_n: int = 20) -> str:
        """
        🌊 OCEAN SUMMARY - Top whale territories and shark waters
        """
        ocean = self.scan_entire_ocean_for_whales()
        
        # Sort by whale activity
        whale_territory = sorted(
            [(s, d) for s, d in ocean.items() if d['whale_count'] > 0],
            key=lambda x: x[1]['total_volume_usd'],
            reverse=True
        )
        
        shark_waters = sorted(
            [(s, d) for s, d in ocean.items() if d['shark_count'] > 0 and d['whale_count'] == 0],
            key=lambda x: x[1]['total_volume_usd'],
            reverse=True
        )
        
        summary = "\n🌊 ═══════════════════════════════════════════════════════════════════════════\n"
        summary += "🌊 ENTIRE OCEAN VISIBILITY - WHALE & SHARK DETECTION ACROSS ALL COINS\n"
        summary += "🌊 ═══════════════════════════════════════════════════════════════════════════\n\n"
        
        summary += f"🐋 WHALE TERRITORY ({len(whale_territory)} coins):\n"
        for i, (symbol, data) in enumerate(whale_territory[:top_n], 1):
            summary += f"   {i:2d}. {symbol:8s} | 🐋×{data['whale_count']:2d} 🦈×{data['shark_count']:2d} 🐟×{data['minnow_count']:2d} | "
            summary += f"${data['total_volume_usd']:>12,.0f} | {data['change_24h']:+6.2f}%\n"
        
        summary += f"\n🦈 SHARK WATERS ({len(shark_waters)} coins):\n"
        for i, (symbol, data) in enumerate(shark_waters[:top_n], 1):
            summary += f"   {i:2d}. {symbol:8s} | 🐋×{data['whale_count']:2d} 🦈×{data['shark_count']:2d} 🐟×{data['minnow_count']:2d} | "
            summary += f"${data['total_volume_usd']:>12,.0f} | {data['change_24h']:+6.2f}%\n"
        
        # Ocean statistics
        total_coins = len(ocean)
        whale_coins = len(whale_territory)
        shark_coins = len(shark_waters)
        quiet_coins = total_coins - whale_coins - shark_coins
        
        total_volume = sum(d['total_volume_usd'] for d in ocean.values())
        
        summary += "\n📊 OCEAN STATISTICS:\n"
        summary += f"   Total coins scanned: {total_coins}\n"
        summary += f"   🐋 Whale territory: {whale_coins} coins\n"
        summary += f"   🦈 Shark waters: {shark_coins} coins\n"
        summary += f"   🐟 Minnow ponds: {quiet_coins} coins\n"
        summary += f"   💰 Total activity volume: ${total_volume:,.0f}\n"
        summary += "\n🌊 ═══════════════════════════════════════════════════════════════════════════\n"
        
        return summary
    
    # ═══════════════════════════════════════════════════════════════════════════
    # �️ ORCA KILL CYCLE DEFENSE - Protect friends from whale attacks!
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_orca_kill_cycle(self) -> Dict[str, Dict]:
        """
        🛡️ DETECT ORCA KILL CYCLE - When whales attack friend positions
        
        Orca Kill Cycle = large whale dumps on a friend coin to:
        1. Trigger panic selling
        2. Liquidate retail positions  
        3. Collect dropped value
        
        Returns: Dict of friend symbols in danger with protection levels
        """
        ocean = self.scan_entire_ocean_for_whales()
        friends_in_danger = {}
        
        for friend_symbol in self.friends.keys():
            if friend_symbol not in ocean:
                continue
            
            ocean_status = ocean[friend_symbol]
            friend = self.friends[friend_symbol]
            
            # KILL CYCLE SIGNALS:
            # 1. Large negative move (whale selling) = DANGER
            if ocean_status['change_24h'] < -10:
                danger_level = "🔴 CRITICAL"
                danger_reason = "Large dump detected - orca selling"
                protect_action = "CONSIDER PROTECTIVE EXIT"
            elif ocean_status['change_24h'] < -5:
                danger_level = "🟠 HIGH ALERT"
                danger_reason = "Significant dip - whale pressure"
                protect_action = "Monitor closely, have exit ready"
            elif ocean_status['change_24h'] < 0 and friend.baggage_percent > 20:
                danger_level = "🟡 WARNING"
                danger_reason = "Declining + friend has baggage"
                protect_action = "Prepare protective stop-loss"
            else:
                continue  # Not in danger
            
            # Calculate protection levels
            current_price = friend.current_price
            cost_basis_price = friend.entry_price
            
            # PROTECTIVE STOP LOSS = prevent baggage from growing
            protective_stop = cost_basis_price * 0.95  # Exit before losing more
            
            # EMERGENCY FLOOR = absolute bottom before exit
            emergency_floor = cost_basis_price * 0.90  # Hard stop
            
            friends_in_danger[friend_symbol] = {
                "symbol": friend_symbol,
                "danger_level": danger_level,
                "reason": danger_reason,
                "action": protect_action,
                "current_price": current_price,
                "cost_basis_price": cost_basis_price,
                "current_loss": friend.baggage_percent,
                "protective_stop": protective_stop,
                "emergency_floor": emergency_floor,
                "ocean_status": ocean_status['size_class'],
                "whale_activity": f"{ocean_status['whale_count']} whales, {ocean_status['shark_count']} sharks",
            }
        
        return friends_in_danger
    
    def get_friend_protection_status(self, top_n: int = 10) -> str:
        """
        🛡️ FRIEND PROTECTION STATUS - Show which friends need defending
        """
        friends_in_danger = self.detect_orca_kill_cycle()
        
        if not friends_in_danger:
            return "\n✅ ALL FRIENDS SAFE - No orca kill cycles detected\n"
        
        status = "\n🛡️ ═══════════════════════════════════════════════════════════════════════════\n"
        status += "🛡️ ORCA KILL CYCLE DEFENSE - FRIENDS UNDER ATTACK\n"
        status += "🛡️ ═══════════════════════════════════════════════════════════════════════════\n\n"
        
        # Sort by danger level
        critical = {s: d for s, d in friends_in_danger.items() if "CRITICAL" in d['danger_level']}
        high_alert = {s: d for s, d in friends_in_danger.items() if "HIGH ALERT" in d['danger_level']}
        warning = {s: d for s, d in friends_in_danger.items() if "WARNING" in d['danger_level']}
        
        if critical:
            status += "🔴 CRITICAL - IMMEDIATE ACTION REQUIRED:\n"
            for symbol, danger in sorted(critical.items())[:top_n]:
                status += f"\n   {symbol} 🔴 CRITICAL\n"
                status += f"   └─ Price: ${danger['current_price']:.8f}\n"
                status += f"   └─ Cost Basis: ${danger['cost_basis_price']:.8f}\n"
                status += f"   └─ Loss: {danger['current_loss']:.1f}%\n"
                status += f"   └─ {danger['reason']}\n"
                status += f"   └─ 🛡️ Protective Stop: ${danger['protective_stop']:.8f}\n"
                status += f"   └─ 🚨 Emergency Floor: ${danger['emergency_floor']:.8f}\n"
                status += f"   └─ ACTION: {danger['action']}\n"
        
        if high_alert:
            status += "\n\n🟠 HIGH ALERT - PREPARE DEFENSES:\n"
            for symbol, danger in sorted(high_alert.items())[:top_n]:
                status += f"\n   {symbol} 🟠 HIGH ALERT\n"
                status += f"   └─ {danger['reason']}\n"
                status += f"   └─ Loss: {danger['current_loss']:.1f}%\n"
                status += f"   └─ 🛡️ Protective Stop: ${danger['protective_stop']:.8f}\n"
        
        if warning:
            status += "\n\n🟡 WARNING - MONITOR:\n"
            for symbol, danger in sorted(warning.items())[:top_n]:
                status += f"\n   {symbol} 🟡 WARNING\n"
                status += f"   └─ {danger['reason']}\n"
                status += f"   └─ Loss: {danger['current_loss']:.1f}%\n"
        
        status += "\n\n🛡️ ═══════════════════════════════════════════════════════════════════════════\n"
        status += f"   Total friends in danger: {len(friends_in_danger)}\n"
        status += f"   Critical: {len(critical)} | High Alert: {len(high_alert)} | Warning: {len(warning)}\n"
        status += "🛡️ ═══════════════════════════════════════════════════════════════════════════\n"
        
        return status
    
    def apply_friend_protection_strategy(self) -> Dict[str, str]:
        """
        🛡️ FRIEND PROTECTION STRATEGY - NO STOP LOSSES (Golden Rule)
        
        GOLDEN RULE: HOLD until profit can be achieved!
        - We DO NOT sell friends at a loss
        - We WARN when whales attack
        - We HOLD and wait for recovery
        - Whale attacks = opportunity to accumulate, not reason to panic sell
        
        Returns: Dict of friend symbols with protection action (CRITICAL_HOLD, HIGH_ALERT_HOLD, MONITOR)
        """
        friends_in_danger = self.detect_orca_kill_cycle()
        protection_actions = {}
        
        for symbol, danger in friends_in_danger.items():
            # NEVER apply stop losses - just log the danger and HOLD STRONG
            if "CRITICAL" in danger['danger_level']:
                action = "CRITICAL_HOLD_STRONG"
                logger.warning(f"🛡️ CRITICAL WHALE ATTACK on {symbol}!")
                logger.warning("   🚫 NO STOP LOSS - HOLDING STRONG!")
                logger.warning(f"   📍 Current Price: ${danger['current_price']:.8f}")
                logger.warning(f"   💰 Cost Basis: ${danger.get('cost_basis_price', 0):.2f}")
                logger.warning(f"   🧳 Baggage: {danger.get('current_loss', 0):.2f}%")
                logger.warning("   💪 Action: HOLD FOR RECOVERY")
            elif "HIGH ALERT" in danger['danger_level']:
                action = "HIGH_ALERT_HOLD"
                logger.warning(f"🛡️ HIGH ALERT whale activity on {symbol}!")
                logger.warning("   🚫 NO STOP LOSS - HOLDING!")
                logger.warning(f"   📍 Current Price: ${danger['current_price']:.8f}")
                logger.warning("   💪 Action: PREPARE TO ACCUMULATE ON DIP")
            else:  # WARNING
                action = "WARNING_MONITOR"
                logger.info(f"🛡️ WARNING: Whale activity on {symbol}. Monitoring for recovery.")
            
            protection_actions[symbol] = action
        
        return protection_actions
    
    # ═══════════════════════════════════════════════════════════════════════════
    # �🐸 QUANTUM FROG - LEAP FOR QUANTITY (WITH ROCK SOLID FEE MATH!)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def find_friend_leap_opportunities(self, friend: Friend) -> List[LeapOpportunity]:
        """
        Find quantum leap opportunities FOR A SPECIFIC FRIEND with baggage accounting!
        
        🆕 FRIENDS WITH BAGGAGE MATH:
        - If friend has baggage, the target dip must be deep enough to:
          1. Cover all fees
          2. CLEAR the baggage (recover to original cost basis)
          3. Still leave profit for breadcrumbs!
        
        Example:
          - XRP bought at $2.00, now $1.90 (-5% = 5% baggage)
          - SLF is -40% (deep dip!)
          - Dip advantage: 35% (40% - 5%)
          - Leap clears baggage because when SLF recovers, we exceed original XRP cost!
        """
        opportunities = []
        
        if friend.symbol == "CASH":
            # Cash has no market change, use 0%
            friend_change = 0.0
            leap_value = friend.current_value
        else:
            market_coin = self.market_data.get(friend.symbol)
            if not market_coin:
                return opportunities
            friend_change = market_coin.change_24h
            friend.update_price(market_coin.price)
            leap_value = friend.leap_value
        
        # Calculate leap amount (keep breadcrumb behind if profitable)
        breadcrumb_value = 0
        if friend.is_clear and friend.profit_available > 0:
            # Friend is clear! Leave breadcrumb of profit
            breadcrumb_value = leap_value * self.breadcrumb_percent
            leap_value = leap_value - breadcrumb_value
        
        # Skip if below minimum trade size
        if leap_value < self.fee_structure.min_trade_size:
            return opportunities
        
        # The BAGGAGE we need to clear (if any)
        baggage_percent = friend.baggage_percent
        
        for symbol, coin in self.market_data.items():
            if symbol == friend.symbol:
                continue
            
            # Skip low volume coins (slippage nightmare)
            if coin.volume_24h < 500000:
                continue
            
            # Calculate dip advantage (how much MORE it fell than our friend)
            dip_advantage = friend_change - coin.change_24h
            
            # ═══════════════════════════════════════════════════════════════
            # THE QUEEN'S BAGGAGE-AWARE FEE MATH
            # ═══════════════════════════════════════════════════════════════
            
            # SELL side
            sell_fee = leap_value * self.fee_structure.taker_fee
            sell_slippage = leap_value * self.fee_structure.slippage_estimate
            value_after_sell = leap_value - sell_fee - sell_slippage
            
            # BUY side
            buy_fee = value_after_sell * self.fee_structure.taker_fee
            buy_slippage = value_after_sell * self.fee_structure.slippage_estimate
            net_value_for_purchase = value_after_sell - buy_fee - buy_slippage
            
            # Total costs
            total_fees = sell_fee + buy_fee
            total_slippage = sell_slippage + buy_slippage
            total_cost = total_fees + total_slippage
            
            # Fee percentage
            fee_percent = (total_cost / leap_value) * 100 if leap_value > 0 else 999
            
            # REQUIRED DIP ADVANTAGE:
            # Must cover: fees + baggage + small profit margin
            min_required_dip = fee_percent + baggage_percent + 0.5  # 0.5% margin
            
            # Calculate quantities
            new_qty = net_value_for_purchase / coin.price if coin.price > 0 else 0
            
            # If friend is NOT cash, calculate equivalent qty for comparison
            if friend.symbol != "CASH":
                # How many we're leaping (not counting breadcrumb)
                old_qty = (leap_value / friend.current_price) if friend.current_price > 0 else 0
                fee_adjusted_multiplier = new_qty / old_qty if old_qty > 0 else 0
            else:
                # Cash: compare value
                old_qty = leap_value
                fee_adjusted_multiplier = net_value_for_purchase / leap_value if leap_value > 0 else 0
            
            # Only consider if dip advantage is sufficient
            if dip_advantage >= min_required_dip and fee_adjusted_multiplier > 1.0:
                recovery_advantage = abs(coin.change_24h) - abs(friend_change)
                
                opportunities.append(LeapOpportunity(
                    from_symbol=friend.symbol,
                    to_symbol=symbol,
                    from_price=friend.current_price,
                    to_price=coin.price,
                    from_change=friend_change,
                    to_change=coin.change_24h,
                    dip_advantage=dip_advantage,
                    quantity_multiplier=new_qty / old_qty if old_qty > 0 else 0,
                    recovery_advantage=recovery_advantage,
                    gross_value=leap_value,
                    sell_fee_cost=sell_fee,
                    buy_fee_cost=buy_fee,
                    slippage_cost=total_slippage,
                    total_fees=total_cost,
                    net_value_after_fees=net_value_for_purchase,
                    fee_adjusted_multiplier=fee_adjusted_multiplier
                ))
        
        # Sort by fee-adjusted multiplier (best real gains first)
        opportunities.sort(key=lambda x: x.fee_adjusted_multiplier, reverse=True)
        return opportunities
    
    def find_leap_opportunities(self) -> List[LeapOpportunity]:
        """
        Find quantum leap opportunities WITH COST BASIS TARGET VALIDATION.
        
        CRITICAL RULE: 🐸 I'm a COST BASIS FROG!
        - I know my original cost basis (e.g., $3,000 for ETH)
        - I ONLY leap if I see a PATH BACK to that value
        - If recovery is unlikely, I CHILL and HOLD my position
        - I don't lock in losses just to move around!
        
        A leap is ONLY justified when:
        1. Target coin has deeper dip (better recovery potential)
        2. Recovery math shows realistic path to original cost basis
        3. Fee costs are acceptable (<1% of potential recovery)
        4. After leap, I still have breadcrumb trail to original position
        """
        opportunities = []
        
        if not self.main_position:
            return opportunities
        
        current = self.market_data.get(self.main_position.symbol)
        if not current:
            return opportunities
        
        # ✅ UPDATE MAIN POSITION WITH LIVE PRICE
        self.main_position.update(current.price, current.change_24h)
        
        # Calculate the value we're leaping with (90% of main position)
        leap_qty = self.main_position.quantity * (1 - self.breadcrumb_percent)
        gross_value = leap_qty * current.price
        
        # Skip if below minimum trade size
        if gross_value < self.fee_structure.min_trade_size:
            return opportunities
        
        for symbol, coin in self.market_data.items():
            if symbol == self.main_position.symbol:
                continue
            
            # Skip low volume coins (slippage nightmare)
            if coin.volume_24h < 500000:  # Require $500k daily volume
                continue
            
            # Calculate dip advantage (how much MORE it fell)
            dip_advantage = current.change_24h - coin.change_24h
            
            # ═══════════════════════════════════════════════════════════════
            # THE QUEEN'S FEE CALCULATION - CRYSTAL CLEAR MATH
            # ═══════════════════════════════════════════════════════════════
            
            # SELL side: Exiting current position
            sell_fee = gross_value * self.fee_structure.taker_fee
            sell_slippage = gross_value * self.fee_structure.slippage_estimate
            value_after_sell = gross_value - sell_fee - sell_slippage
            
            # BUY side: Entering new position
            buy_fee = value_after_sell * self.fee_structure.taker_fee
            buy_slippage = value_after_sell * self.fee_structure.slippage_estimate
            net_value_for_purchase = value_after_sell - buy_fee - buy_slippage
            
            # Total costs
            total_fees = sell_fee + buy_fee
            total_slippage = sell_slippage + buy_slippage
            total_cost = total_fees + total_slippage
            
            # Calculate quantities
            gross_new_qty = gross_value / coin.price  # If no fees
            actual_new_qty = net_value_for_purchase / coin.price  # After all fees
            
            # The REAL multiplier after fees
            fee_adjusted_multiplier = actual_new_qty / leap_qty if leap_qty > 0 else 0
            
            # Minimum dip advantage required to cover fees
            _fee_percent = (total_cost / gross_value) * 100
            
            # ✅ INTELLIGENT LEAP CRITERIA - Only leap for RECOVERY, not just fee mitigation
            # Check 1: Must not lose excessive fees (baseline)
            fee_acceptable = fee_adjusted_multiplier > 0.90  # Can't lose more than 10% to fees
            
            # Check 2: Must offer RECOVERY ADVANTAGE (this is the whole point!)
            # Only leap to coins that have DEEPER dips (more potential for recovery)
            recovery_advantage = abs(coin.change_24h) - abs(current.change_24h)
            has_recovery_edge = recovery_advantage > 1.0  # Target dipped at least 1% MORE
            
            # Check 3: COST BASIS TARGET VALIDATION! 🎯
            # The frog must know: "Will this leap path realistically get me back to my original cost basis?"
            # Example: "I'm a $3K frog - I only leap if I see path back to $3K!"
            cost_basis_target = self.main_position.cost_basis  # The original target we're tracking
            current_loss_percent = ((current.price - cost_basis_target) / cost_basis_target) * 100
            
            # Calculate recovery potential:
            # If target coin drops MORE, it has MORE room to recover
            # We measure this by comparing drop percentages
            current_drop = abs(current.change_24h)  # How much did THIS coin drop recently
            target_drop = abs(coin.change_24h)      # How much did TARGET drop recently
            
            # If target coin dropped MORE, it has more recovery potential
            # BUT - we also need to check: can it realistically get back to our cost basis?
            # Simple rule: Only leap if target has dropped MORE and has showed recovery potential
            realistic_recovery_path = False
            recovery_runway = 0.0
            if target_drop > current_drop:
                # Target coin dipped MORE, so it has potential to recover more
                # Check if recovery could realistically get us back to cost basis territory
                recovery_runway = target_drop - current_drop  # Extra recovery potential
                
                # Conservative: only leap if we have at least same drop depth as we're recovering from
                current_loss_magnitude = abs(current_loss_percent)  # How deep in red are we?
                recovery_potential = recovery_runway * 2  # Conservative recovery estimate
                
                realistic_recovery_path = recovery_potential > (current_loss_magnitude * 0.1)
            
            # Only leap if ALL conditions met
            is_smart_leap = fee_acceptable and has_recovery_edge and realistic_recovery_path
            
            # 🌊 BONUS: Check for whale activity on target coin!
            # If whales are BUYING the target coin, recovery is MORE likely!
            _whale_bonus = False
            whale_info = ""
            if is_smart_leap:
                has_whale_action, whale_desc = self.detect_whale_activity(symbol)
                if has_whale_action and "BUYING" in whale_desc:
                    _whale_bonus = True
                    whale_info = f" | 🐋 {whale_desc}"
                    logger.info(f"   🌊 WHALE BOOST DETECTED: {whale_desc}")
            
            # 📊 LOG REJECTION REASONS
            if not is_smart_leap:
                reason = []
                if not fee_acceptable:
                    reason.append(f"fee_loss={fee_adjusted_multiplier:.4f}")
                if not has_recovery_edge:
                    reason.append(f"recovery_advantage={recovery_advantage:.2f}% (need >1.0%)")
                if not realistic_recovery_path and (target_drop > current_drop):
                    reason.append(f"recovery_runway={recovery_runway:.2f}% insufficient (need >{abs(current_loss_percent)*0.1:.2f}%)")
                
                logger.debug(f"❌ FROG REFUSES LEAP to {symbol}: {', '.join(reason)}")
                logger.debug(f"   💭 I'm a ${cost_basis_target:.2f} frog - I don't see path back! (Currently ${current.price:.2f}, {current_loss_percent:.2f}%)")
            
            if is_smart_leap:
                recovery_advantage = abs(coin.change_24h) - abs(current.change_24h)
                
                logger.info(f"✅ FROG LEAPS to {symbol}!{whale_info}")
                logger.info(f"   💭 I see recovery path: target dipped {target_drop:.2f}% (vs my {current_drop:.2f}%), runway={recovery_runway:.2f}%")
                logger.info(f"   💰 ${cost_basis_target:.2f} frog jumping from ${current.price:.2f} to ${coin.price:.2f}")

                
                opportunities.append(LeapOpportunity(
                    from_symbol=self.main_position.symbol,
                    to_symbol=symbol,
                    from_price=current.price,
                    to_price=coin.price,
                    from_change=current.change_24h,
                    to_change=coin.change_24h,
                    dip_advantage=dip_advantage,
                    quantity_multiplier=gross_new_qty / leap_qty if leap_qty > 0 else 0,
                    recovery_advantage=recovery_advantage,
                    # Fee details - FULL TRANSPARENCY
                    gross_value=gross_value,
                    sell_fee_cost=sell_fee,
                    buy_fee_cost=buy_fee,
                    slippage_cost=total_slippage,
                    total_fees=total_cost,
                    net_value_after_fees=net_value_for_purchase,
                    fee_adjusted_multiplier=fee_adjusted_multiplier
                ))
        
        # Sort by fee-adjusted multiplier (best real gains first)
        opportunities.sort(key=lambda x: x.fee_adjusted_multiplier, reverse=True)
        return opportunities
    
    def execute_quantum_leap(self, opportunity: LeapOpportunity) -> bool:
        """
        Execute a BLOODLESS quantum leap with breadcrumb.
        
        THE GOLDEN RULE: VALUE STAYS THE SAME (minus fees), QUANTITY GROWS!
        
        ROCK SOLID MATH:
        1. Leave BREADCRUMB_PERCENT in current coin (keeps growing there)
        2. Calculate EXACT fees (sell fee + slippage + buy fee + slippage)
        3. Swap remaining VALUE for new coin AFTER deducting all fees
        4. Because target fell MORE, you STILL get MORE QUANTITY even after fees
        5. Track every penny of fees paid
        
        Example with fees:
          - Have: 0.05 ETH @ $2000 = $100 value
          - Leap 90%: $90 gross value
          - Sell fee (0.1%): $0.09
          - Sell slippage (0.05%): $0.045
          - After sell: $89.865
          - Buy fee (0.1%): $0.090
          - Buy slippage (0.05%): $0.045
          - Net value: $89.73 (lost $0.27 to fees/slippage)
          - BUT: Target fell 20% more, so $89.73 buys MORE coins than $90 of old coin!
        """
        if not self.main_position:
            logger.warning("⚠️ No main position to leap from")
            return False
        
        # Verify the leap is still profitable after fees
        if not opportunity.is_profitable_after_fees:
            logger.warning("⚠️ Leap rejected - not profitable after fees!")
            logger.warning(f"   Fee-adjusted multiplier: {opportunity.fee_adjusted_multiplier:.4f}x (needs > 1.0)")
            return False

        if not self.live_trading:
            self._not_submitted_receipt(
                self.exchange,
                opportunity.from_symbol,
                "SELL",
                reason=(
                    "queen_dry_run"
                    if self.dry_run
                    else "live_trading_disabled"
                ),
            )
            logger.info("🧪 Quantum leap not submitted; portfolio state is unchanged")
            return False

        original_position = self.main_position
        requested_sell_qty = original_position.quantity * (
            1 - self.breadcrumb_percent
        )
        exchange = self.exchange
        sell_res = self._place_market_order(
            exchange,
            opportunity.from_symbol,
            "SELL",
            quantity=requested_sell_qty,
        )
        sell_fill = self._resolve_terminal_fill(
            exchange,
            opportunity.from_symbol,
            "SELL",
            sell_res,
            quantity=requested_sell_qty,
        )
        if not sell_fill["success"]:
            logger.error(
                f"❌ Leap SELL has no complete terminal receipt on {exchange}: "
                f"{sell_fill.get('reason')}"
            )
            return False

        sold_qty = float(sell_fill["filled_qty"])
        if sold_qty > original_position.quantity + max(
            1e-12, original_position.quantity * 0.001
        ):
            sell_fill["success"] = False
            sell_fill["eligible_for_accounting"] = False
            sell_fill["eligible_for_learning"] = False
            sell_fill["reason"] = "provider_sell_exceeds_tracked_position"
            self.last_execution_receipt = sell_fill
            logger.error("❌ Provider SELL conflicts with tracked Queen position")
            return False

        sell_quote = str(sell_fill.get("quote_asset") or "").upper()
        sell_quote_fee = float(
            (sell_fill.get("fee_by_asset") or {}).get(sell_quote, 0.0)
        )
        purchase_quote_qty = float(sell_fill["filled_notional"]) - sell_quote_fee
        if not math.isfinite(purchase_quote_qty) or purchase_quote_qty <= 0:
            sell_fill["success"] = False
            sell_fill["eligible_for_accounting"] = False
            sell_fill["eligible_for_learning"] = False
            sell_fill["reason"] = "provider_sell_has_no_positive_net_proceeds"
            self.last_execution_receipt = sell_fill
            return False

        # The dependent BUY is reached only after terminal SELL evidence.
        buy_res = self._place_market_order(
            exchange,
            opportunity.to_symbol,
            "BUY",
            quote_qty=purchase_quote_qty,
        )
        buy_fill = self._resolve_terminal_fill(
            exchange,
            opportunity.to_symbol,
            "BUY",
            buy_res,
            quote_qty=purchase_quote_qty,
        )
        if not buy_fill["success"]:
            logger.error(
                f"❌ Leap BUY requires reconciliation on {exchange}: "
                f"{buy_fill.get('reason')}"
            )
            logger.error("⚠️ SELL filled; dependent BUY state was not committed.")
            return False

        new_qty = self._net_base_quantity(buy_fill, opportunity.to_symbol)
        if new_qty <= 0:
            buy_fill["success"] = False
            buy_fill["eligible_for_accounting"] = False
            buy_fill["eligible_for_learning"] = False
            buy_fill["reason"] = "provider_buy_has_no_net_base_quantity"
            self.last_execution_receipt = buy_fill
            return False

        breadcrumb_qty = max(0.0, original_position.quantity - sold_qty)
        breadcrumb_value = (
            original_position.cost_basis
            * (breadcrumb_qty / original_position.quantity)
            if original_position.quantity > 0
            else 0.0
        )
        if breadcrumb_qty > 0:
            self.breadcrumbs[original_position.symbol] = Breadcrumb(
                symbol=original_position.symbol,
                quantity=breadcrumb_qty,
                cost_basis=breadcrumb_value,
                entry_price=original_position.entry_price,
                entry_time=original_position.entry_time,
                current_price=original_position.current_price,
                exchange=self.exchange,
            )
            self.total_breadcrumbs += 1

        buy_quote = str(buy_fill.get("quote_asset") or "").upper()
        buy_quote_fee = float(
            (buy_fill.get("fee_by_asset") or {}).get(buy_quote, 0.0)
        )
        buy_cost = float(buy_fill["filled_notional"]) + buy_quote_fee
        self.main_position = MainPosition(
            symbol=opportunity.to_symbol,
            quantity=new_qty,
            cost_basis=buy_cost,
            entry_price=float(buy_fill["filled_price"]),
            entry_time=datetime.fromtimestamp(
                float(buy_fill["provider_timestamp"])
            ),
            current_price=float(buy_fill["filled_price"]),
            change_24h=opportunity.to_change,
        )
        self._record_observed_fees(sell_fill, buy_fill)
        self.total_leaps += 1

        logger.info("🐸 BLOODLESS QUANTUM LEAP! (provider-reconciled)")
        logger.info(
            f"   SELL: {sold_qty:.6f} {opportunity.from_symbol} -> "
            f"{sell_fill['filled_notional']:.4f} {sell_quote}"
        )
        logger.info(
            f"   BUY: {new_qty:.6f} {opportunity.to_symbol} <- "
            f"{buy_fill['filled_notional']:.4f} {buy_quote}"
        )
        logger.info(f"   🧾 OBSERVED FEES: {self.observed_fees_by_asset}")
        logger.info(
            f"   🍞 Breadcrumb: {breadcrumb_qty:.6f} "
            f"{opportunity.from_symbol}"
        )

        self._commit_resolved_orders(
            (exchange, opportunity.from_symbol, "SELL"),
            (exchange, opportunity.to_symbol, "BUY"),
        )
        return True
    
    def execute_friend_leap(self, friend: Friend, opportunity: LeapOpportunity) -> bool:
        """
        Execute a quantum leap for a FRIEND with cost basis tracking integration.
        
        This updates the cost basis tracker so baggage calculations stay accurate.
        """
        if friend.symbol not in self.friends:
            logger.warning(f"⚠️ Friend {friend.symbol} not found")
            return False
        
        # Verify the leap is still profitable
        if not opportunity.is_profitable_after_fees:
            logger.warning("⚠️ Friend leap rejected - not profitable after fees!")
            return False

        exchange = friend.exchange
        if not self.live_trading or exchange in ("multi", "kraken-cached"):
            self._not_submitted_receipt(
                exchange,
                friend.symbol,
                "SELL",
                reason=(
                    "queen_dry_run"
                    if self.dry_run
                    else "friend_exchange_not_live_tradable"
                ),
            )
            logger.info("🧪 Friend leap not submitted; holdings are unchanged")
            return False

        original_symbol = friend.symbol
        original_quantity = friend.quantity
        original_cost_basis = friend.cost_basis
        original_entry_price = friend.entry_price
        original_current_price = friend.current_price
        original_is_clear = friend.is_clear
        requested_value = opportunity.gross_value * (
            1 - self.breadcrumb_percent
        )
        requested_sell_qty = (
            requested_value / friend.current_price
            if friend.current_price > 0
            else 0.0
        )
        if requested_sell_qty <= 0:
            self._not_submitted_receipt(
                exchange,
                friend.symbol,
                "SELL",
                reason="friend_sell_quantity_unavailable",
            )
            return False

        sell_res = self._place_market_order(
            exchange,
            friend.symbol,
            "SELL",
            quantity=requested_sell_qty,
        )
        sell_fill = self._resolve_terminal_fill(
            exchange,
            friend.symbol,
            "SELL",
            sell_res,
            quantity=requested_sell_qty,
        )
        if not sell_fill["success"]:
            logger.error(
                f"❌ Friend leap SELL requires reconciliation on {exchange}: "
                f"{sell_fill.get('reason')}"
            )
            return False

        sold_qty = float(sell_fill["filled_qty"])
        if sold_qty > original_quantity + max(1e-12, original_quantity * 0.001):
            sell_fill["success"] = False
            sell_fill["eligible_for_accounting"] = False
            sell_fill["eligible_for_learning"] = False
            sell_fill["reason"] = "provider_sell_exceeds_tracked_friend"
            self.last_execution_receipt = sell_fill
            return False

        sell_quote = str(sell_fill.get("quote_asset") or "").upper()
        sell_quote_fee = float(
            (sell_fill.get("fee_by_asset") or {}).get(sell_quote, 0.0)
        )
        purchase_quote_qty = float(sell_fill["filled_notional"]) - sell_quote_fee
        if not math.isfinite(purchase_quote_qty) or purchase_quote_qty <= 0:
            sell_fill["success"] = False
            sell_fill["eligible_for_accounting"] = False
            sell_fill["eligible_for_learning"] = False
            sell_fill["reason"] = "provider_sell_has_no_positive_net_proceeds"
            self.last_execution_receipt = sell_fill
            return False

        buy_res = self._place_market_order(
            exchange,
            opportunity.to_symbol,
            "BUY",
            quote_qty=purchase_quote_qty,
        )
        buy_fill = self._resolve_terminal_fill(
            exchange,
            opportunity.to_symbol,
            "BUY",
            buy_res,
            quote_qty=purchase_quote_qty,
        )
        if not buy_fill["success"]:
            logger.error(
                f"❌ Friend leap BUY requires reconciliation on {exchange}: "
                f"{buy_fill.get('reason')}"
            )
            logger.error("⚠️ SELL filled; dependent BUY state was not committed.")
            return False

        new_qty = self._net_base_quantity(buy_fill, opportunity.to_symbol)
        if new_qty <= 0:
            buy_fill["success"] = False
            buy_fill["eligible_for_accounting"] = False
            buy_fill["eligible_for_learning"] = False
            buy_fill["reason"] = "provider_buy_has_no_net_base_quantity"
            self.last_execution_receipt = buy_fill
            return False

        remaining_qty = max(0.0, original_quantity - sold_qty)
        remaining_cost = (
            original_cost_basis * (remaining_qty / original_quantity)
            if original_quantity > 0
            else 0.0
        )
        if remaining_qty <= 1e-12:
            self.friends.pop(original_symbol, None)
        elif original_is_clear:
            self.friends.pop(original_symbol, None)
            self.breadcrumbs[original_symbol] = Breadcrumb(
                symbol=original_symbol,
                quantity=remaining_qty,
                cost_basis=remaining_cost,
                entry_price=original_entry_price,
                entry_time=datetime.fromtimestamp(
                    float(sell_fill["provider_timestamp"])
                ),
                current_price=original_current_price,
                exchange=exchange,
            )
            self.total_breadcrumbs += 1
        else:
            friend.quantity = remaining_qty
            friend.cost_basis = remaining_cost

        buy_quote = str(buy_fill.get("quote_asset") or "").upper()
        buy_quote_fee = float(
            (buy_fill.get("fee_by_asset") or {}).get(buy_quote, 0.0)
        )
        buy_cost = float(buy_fill["filled_notional"]) + buy_quote_fee
        if opportunity.to_symbol in self.friends:
            existing = self.friends[opportunity.to_symbol]
            total_qty = existing.quantity + new_qty
            total_cost = existing.cost_basis + buy_cost
            existing.quantity = total_qty
            existing.cost_basis = total_cost
            existing.entry_price = total_cost / total_qty
            existing.current_price = float(buy_fill["filled_price"])
        else:
            self.friends[opportunity.to_symbol] = Friend(
                symbol=opportunity.to_symbol,
                quantity=new_qty,
                cost_basis=buy_cost,
                entry_price=float(buy_fill["filled_price"]),
                current_price=float(buy_fill["filled_price"]),
                exchange=exchange,
            )

        # The legacy cost-basis tracker accepts one quote-denominated fee.
        # Write to it only when both provider receipts prove that exact unit.
        sell_other_fees = {
            asset: fee
            for asset, fee in sell_fill["fee_by_asset"].items()
            if asset != sell_quote and fee > 0
        }
        buy_other_fees = {
            asset: fee
            for asset, fee in buy_fill["fee_by_asset"].items()
            if asset != buy_quote and fee > 0
        }
        if sell_quote and sell_quote == buy_quote and not sell_other_fees and not buy_other_fees:
            try:
                from aureon.portfolio.cost_basis_tracker import CostBasisTracker

                cost_basis_tracker = CostBasisTracker()
                cost_basis_tracker.record_trade(
                    symbol=f"{original_symbol}{sell_quote}",
                    side="sell",
                    quantity=sold_qty,
                    price=float(sell_fill["filled_price"]),
                    exchange=exchange,
                    fee=sell_quote_fee,
                )
                cost_basis_tracker.record_trade(
                    symbol=f"{opportunity.to_symbol}{buy_quote}",
                    side="buy",
                    quantity=new_qty,
                    price=float(buy_fill["filled_price"]),
                    exchange=exchange,
                    fee=buy_quote_fee,
                )
            except Exception as exc:
                logger.warning(
                    f"⚠️ Provider-backed cost basis write failed: {exc}"
                )

        self._record_observed_fees(sell_fill, buy_fill)
        self.total_leaps += 1
        logger.info(
            f"🐸 FRIEND QUANTUM LEAP! {original_symbol} → "
            f"{opportunity.to_symbol} (provider-reconciled)"
        )
        logger.info(
            f"   SOLD {sold_qty:.6f} {original_symbol}; "
            f"BOUGHT {new_qty:.6f} {opportunity.to_symbol}"
        )
        logger.info(f"   🧾 OBSERVED FEES: {self.observed_fees_by_asset}")
        self._commit_resolved_orders(
            (exchange, original_symbol, "SELL"),
            (exchange, opportunity.to_symbol, "BUY"),
        )
        return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🟡 YELLOW BRICK ROAD - INITIALIZE JOURNEY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_journey(self, start_symbol: str = "ETH") -> bool:
        """
        Start the Yellow Brick Road journey.
        
        Enter the market with the full vault in the starting coin.
        """
        if self.main_position:
            logger.warning("⚠️ Journey already in progress")
            return False

        if not self.live_trading:
            self._not_submitted_receipt(
                self.exchange,
                start_symbol,
                "BUY",
                reason=(
                    "queen_dry_run"
                    if self.dry_run
                    else "live_trading_disabled"
                ),
            )
            logger.info("🧪 Journey not submitted; portfolio state is unchanged")
            return False
        
        self.fetch_market_data()
        
        if start_symbol not in self.market_data:
            logger.error(f"❌ {start_symbol} not found in market data")
            return False
        
        coin = self.market_data[start_symbol]
        requested_quote_qty = self.available_cash
        buy_res = self._place_market_order(
            self.exchange,
            start_symbol,
            "BUY",
            quote_qty=requested_quote_qty,
        )
        buy_fill = self._resolve_terminal_fill(
            self.exchange,
            start_symbol,
            "BUY",
            buy_res,
            quote_qty=requested_quote_qty,
        )
        if not buy_fill["success"]:
            logger.error(
                f"❌ Journey BUY requires terminal provider evidence: "
                f"{buy_fill.get('reason')}"
            )
            return False

        quantity = self._net_base_quantity(buy_fill, start_symbol)
        buy_quote = str(buy_fill.get("quote_asset") or "").upper()
        quote_fee = float(
            (buy_fill.get("fee_by_asset") or {}).get(buy_quote, 0.0)
        )
        cash_spent = float(buy_fill["filled_notional"]) + quote_fee
        if quantity <= 0 or cash_spent > self.available_cash + max(
            1e-8, self.available_cash * 0.001
        ):
            buy_fill["success"] = False
            buy_fill["eligible_for_accounting"] = False
            buy_fill["eligible_for_learning"] = False
            buy_fill["reason"] = "provider_buy_conflicts_with_tracked_cash"
            self.last_execution_receipt = buy_fill
            return False
        
        self.main_position = MainPosition(
            symbol=start_symbol,
            quantity=quantity,
            cost_basis=cash_spent,
            entry_price=float(buy_fill["filled_price"]),
            entry_time=datetime.fromtimestamp(
                float(buy_fill["provider_timestamp"])
            ),
            current_price=float(buy_fill["filled_price"]),
            change_24h=coin.change_24h,
        )
        
        self.available_cash = max(0.0, self.available_cash - cash_spent)
        self.start_time = datetime.fromtimestamp(
            float(buy_fill["provider_timestamp"])
        )
        self._record_observed_fees(buy_fill)
        
        logger.info("🟡 YELLOW BRICK ROAD JOURNEY STARTED!")
        logger.info(f"   Starting coin: {start_symbol}")
        logger.info(f"   Provider fill price: {buy_fill['filled_price']:.4f}")
        logger.info(f"   Quantity: {quantity:.6f} {start_symbol}")
        logger.info(f"   Quote deployed: {cash_spent:.4f} {buy_quote}")
        
        self._commit_resolved_orders(
            (self.exchange, start_symbol, "BUY"),
        )
        return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🍞 BREADCRUMB MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_breadcrumbs(self) -> Dict[str, float]:
        """Update all breadcrumb positions with current prices."""
        updates = {}
        
        for symbol, crumb in self.breadcrumbs.items():
            if symbol in self.market_data:
                _old_value = crumb.current_value
                crumb.update_price(self.market_data[symbol].price)
                updates[symbol] = crumb.unrealized_pnl
        
        return updates
    
    def get_breadcrumb_summary(self) -> Dict[str, Any]:
        """Get summary of all breadcrumb positions."""
        total_cost = sum(c.cost_basis for c in self.breadcrumbs.values())
        total_value = sum(c.current_value for c in self.breadcrumbs.values())
        total_pnl = total_value - total_cost
        
        return {
            "count": len(self.breadcrumbs),
            "total_cost": total_cost,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "pnl_percent": (total_pnl / total_cost * 100) if total_cost > 0 else 0,
            "positions": {
                s: {
                    "quantity": c.quantity,
                    "cost": c.cost_basis,
                    "value": c.current_value,
                    "pnl": c.unrealized_pnl,
                    "pnl_pct": c.pnl_percent
                }
                for s, c in self.breadcrumbs.items()
            }
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ⚡ MICRO SCALPING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def find_scalp_opportunities(self) -> List[Tuple[str, float]]:
        """
        Find breadcrumbs ready for scalping.
        
        A scalp is ready when:
        1. Breadcrumb has gained MIN_PROFIT_SCALP or more
        2. Market shows signs of bounce exhaustion (optional)
        """
        opportunities = []
        
        for symbol, crumb in self.breadcrumbs.items():
            if crumb.pnl_percent >= MIN_PROFIT_SCALP * 100:
                opportunities.append((symbol, crumb.pnl_percent))
        
        # Sort by profit (highest first)
        opportunities.sort(key=lambda x: x[1], reverse=True)
        return opportunities
    
    def execute_scalp(self, symbol: str, percent_to_sell: float = 0.5) -> float:
        """
        Execute a scalp on a breadcrumb position.
        
        Sells a portion of the position to realize profit,
        leaving the rest to continue growing.
        """
        if symbol not in self.breadcrumbs:
            return 0.0

        crumb = self.breadcrumbs[symbol]
        exchange = (
            crumb.exchange if hasattr(crumb, "exchange") else self.exchange
        )
        if not self.live_trading:
            self._not_submitted_receipt(
                exchange,
                symbol,
                "SELL",
                reason=(
                    "queen_dry_run"
                    if self.dry_run
                    else "live_trading_disabled"
                ),
            )
            logger.info("🧪 Scalp not submitted; breadcrumb is unchanged")
            return 0.0

        fraction = _finite_receipt_number(percent_to_sell, positive=True)
        if fraction is None or fraction > 1:
            self._not_submitted_receipt(
                exchange,
                symbol,
                "SELL",
                reason="invalid_scalp_fraction",
            )
            return 0.0

        requested_sell_qty = crumb.quantity * fraction
        available_qty = self._get_available_base_quantity(exchange, symbol)
        if available_qty <= 0:
            self._not_submitted_receipt(
                exchange,
                symbol,
                "SELL",
                reason="live_base_balance_unavailable",
            )
            logger.warning(
                f"⚠️ No available live balance for {symbol} on {exchange}"
            )
            return 0.0
        requested_sell_qty = min(requested_sell_qty, available_qty)
        if requested_sell_qty <= 0:
            return 0.0

        sell_res = self._place_market_order(
            exchange,
            symbol,
            "SELL",
            quantity=requested_sell_qty,
        )
        sell_fill = self._resolve_terminal_fill(
            exchange,
            symbol,
            "SELL",
            sell_res,
            quantity=requested_sell_qty,
        )
        if not sell_fill["success"]:
            logger.error(
                f"❌ Scalp SELL requires terminal provider evidence: "
                f"{sell_fill.get('reason')}"
            )
            return 0.0

        filled_qty = float(sell_fill["filled_qty"])
        base_fee = float(
            (sell_fill.get("fee_by_asset") or {}).get(symbol.upper(), 0.0)
        )
        quantity_removed = filled_qty + base_fee
        if quantity_removed > crumb.quantity + max(
            1e-12, crumb.quantity * 0.001
        ):
            sell_fill["success"] = False
            sell_fill["eligible_for_accounting"] = False
            sell_fill["eligible_for_learning"] = False
            sell_fill["reason"] = "provider_sell_exceeds_tracked_breadcrumb"
            self.last_execution_receipt = sell_fill
            return 0.0

        cost_portion = (
            crumb.cost_basis * (quantity_removed / crumb.quantity)
            if crumb.quantity > 0
            else 0.0
        )
        quote_asset = str(sell_fill.get("quote_asset") or "").upper()
        quote_fee = float(
            (sell_fill.get("fee_by_asset") or {}).get(quote_asset, 0.0)
        )
        net_proceeds = float(sell_fill["filled_notional"]) - quote_fee
        other_fees = {
            asset: fee
            for asset, fee in sell_fill["fee_by_asset"].items()
            if asset not in {quote_asset, symbol.upper()} and fee > 0
        }

        crumb.quantity = max(0.0, crumb.quantity - quantity_removed)
        crumb.cost_basis = max(0.0, crumb.cost_basis - cost_portion)
        self.available_cash += net_proceeds
        self._record_observed_fees(sell_fill)
        self.total_scalps += 1

        profit: Optional[float] = None
        if not other_fees:
            profit = net_proceeds - cost_portion
            self.total_profit_realized += profit
        else:
            sell_fill["pnl_status"] = (
                "no_data_external_fee_conversion_required"
            )
            sell_fill["eligible_for_learning"] = False
            self.last_execution_receipt = sell_fill

        if crumb.quantity <= 1e-12:
            del self.breadcrumbs[symbol]

        logger.info(f"⚡ SCALP EXECUTED on {symbol} (provider-reconciled)")
        logger.info(
            f"   Sold: {filled_qty:.6f} @ "
            f"{sell_fill['filled_price']:.6f}"
        )
        if profit is None:
            logger.warning(
                f"   P&L unavailable until fee assets are valued: {other_fees}"
            )
        else:
            logger.info(f"   Realized P&L: {profit:.6f} {quote_asset}")

        self._commit_resolved_orders(
            (exchange, symbol, "SELL"),
        )
        return profit if profit is not None else 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔄 MAIN CYCLE - THE 24/7 MACHINE
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def run_cycle(self) -> CycleStats:
        """
        Run a single cycle of the eternal machine.
        
        1. PROTECT - Check ORCA KILL CYCLE defenses for friends
        2. SCAN - Fetch market data
        3. UPDATE - Update all positions
        4. ANALYZE - Find leap opportunities
        5. LEAP - Execute best leap if available
        6. SCALP - Harvest ready breadcrumbs
        7. RECORD - Log statistics
        """
        self.total_cycles += 1
        stats = CycleStats(
            cycle_number=self.total_cycles,
            start_time=datetime.now()
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 CYCLE #{self.total_cycles} - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        # Portfolio observation is explicit.  A default/dry machine never
        # discovers or constructs a provider client as part of a cycle.
        if callable(getattr(self, "_balance_reader", None)):
            try:
                self._load_friends_from_real_positions()
                self._sync_main_position_to_real_holdings()
                logger.info(
                    "   [SYNC] Friends: %s | Main: %s",
                    len(self.friends),
                    self.main_position.symbol if self.main_position else "NONE",
                )
            except Exception as exc:
                logger.warning("Position observation failed; using cached state: %s", exc)
        else:
            logger.info("   [SYNC] skipped: no injected balance reader")
        
        # 👑⚛️ QUEEN'S AUTONOMOUS DECISION - Full cognitive control
        queen_decision = None
        if self.queen_hive:
            try:
                # Gather market state for Queen's neural brain
                neural_inputs = self.queen_hive.gather_neural_inputs(
                    probability_score=0.5,
                    wisdom_score=0.7,
                    quantum_signal=0.0,
                    gaia_resonance=0.5,
                    emotional_coherence=0.6,
                    mycelium_signal=0.0
                )
                
                # Queen thinks and decides autonomously
                queen_confidence, reasoning = self.queen_hive.think(neural_inputs)
                queen_decision = {
                    'confidence': queen_confidence,
                    'reasoning': reasoning,
                    'has_control': True
                }
                
                logger.info("👑🧠 QUEEN'S AUTONOMOUS DECISION")
                logger.info(f"   Confidence: {queen_confidence:.2%}")
                logger.info(f"   Reasoning: {reasoning}")
            except Exception as e:
                logger.debug(f"Queen decision unavailable: {e}")
        
        # ⚛️ QUANTUM COGNITION AMPLIFICATION
        quantum_boost = 1.0
        if self.quantum_cognition:
            try:
                result = self.quantum_cognition.amplify_cognition()
                if result.success:
                    quantum_boost = result.state.unified_amplification
                    logger.info(f"⚛️🧠 QUANTUM COGNITION AMPLIFICATION: {quantum_boost:.3f}x")
            except Exception as e:
                logger.debug(f"Quantum amplification failed: {e}")
        
        # 🤖 BOT INTELLIGENCE ANALYSIS - Market Structure & Competition
        bot_intelligence = None
        if self.bot_profiler:
            try:
                # Profile bots currently active in the market
                bot_intelligence = self.bot_profiler.profile_market_structure()
                if bot_intelligence:
                    logger.info("🤖 BOT INTELLIGENCE ANALYSIS")
                    logger.info(f"   Active Bots: {bot_intelligence.get('active_bot_count', 0)}")
                    logger.info(f"   Dominant Strategy: {bot_intelligence.get('dominant_strategy', 'unknown')}")
                    logger.info(f"   Market Structure: {bot_intelligence.get('market_structure', 'unknown')}")
                    logger.info(f"   Estimated Capital: ${bot_intelligence.get('total_bot_capital', 0)/1e9:.2f}B")
            except Exception as e:
                logger.debug(f"Bot intelligence analysis failed: {e}")
        
        # 📺 LIVE TV STATION - Validate Predictions & Collect Feedback
        tv_validations = []
        if self.prediction_engine and self.main_position:
            try:
                # Create market snapshot for current position
                if self.main_position.symbol in self.market_data:
                    coin = self.market_data[self.main_position.symbol]
                    market_snapshot = MarketSnapshot(
                        symbol=self.main_position.symbol,
                        price=coin.price,
                        change_24h=coin.change_24h,
                        volume_24h=getattr(coin, 'volume_24h', 0.0),
                        momentum_30s=self.main_position.change_1h,
                        volatility_30s=abs(self.main_position.change_15m),
                        hz_frequency=7.83,
                        timestamp=datetime.now()
                    )
                    # Validate any pending predictions
                    tv_validations = self.prediction_engine.validate_predictions(market_snapshot)
                    if tv_validations:
                        logger.info(f"📺 LIVE TV VALIDATION: {len(tv_validations)} predictions validated")
                        for vp in tv_validations:
                            status = "✅ CORRECT" if vp.correct else "❌ WRONG"
                            logger.info(f"   {vp.symbol}: Predicted {vp.predicted_direction} {vp.predicted_change_pct:+.3f}% → Actual {vp.actual_change_pct:+.3f}% {status}")
            except Exception as e:
                logger.debug(f"Live TV validation failed: {e}")
        
        # 1. PROTECT - ORCA KILL CYCLE DEFENSE (NO STOP LOSSES - HOLD FOR PROFIT!)
        # Check if any friends are under attack and alert (but NEVER sell at loss)
        friends_in_danger = self.detect_orca_kill_cycle()
        if friends_in_danger:
            logger.warning(f"🛡️ ORCA KILL CYCLE DETECTED - {len(friends_in_danger)} friends under whale attack!")
            protection_strategy = self.apply_friend_protection_strategy()
            if protection_strategy:
                logger.warning(f"🛡️ PROTECTION STRATEGY: {len(protection_strategy)} friends being HELD for recovery (NO STOP LOSSES)")
                stats.friends_protected = len(protection_strategy)
        
        # 2. SCAN
        self.fetch_market_data()
        logger.info(f"   🐸 [SCAN] Market data: {len(self.market_data)} coins scanned")
        
        # 3. UPDATE
        if self.main_position and self.main_position.symbol in self.market_data:
            coin = self.market_data[self.main_position.symbol]
            self.main_position.update(coin.price, coin.change_24h)
        
        self.update_breadcrumbs()
        
        # 4. ANALYZE
        opportunities = self.find_leap_opportunities()
        logger.info(f"   🐸 [ANALYZE] Leap opportunities found: {len(opportunities)}")
        
        # 5. LEAP (if good opportunity AND Queen approves)
        if opportunities and queen_decision and queen_decision['has_control']:
            # Only leap if Queen's confidence is above threshold (quantum amplified)
            if queen_decision['confidence'] * quantum_boost > 0.618:  # Golden ratio threshold
                best = opportunities[0]
                # Execute the best leap opportunity (all criteria already validated)
                if self.execute_quantum_leap(best):
                    stats.leaps_made += 1
                    stats.breadcrumbs_planted += 1
                    logger.info("👑 LEAP APPROVED by Queen's autonomous control")
        elif opportunities and queen_decision and queen_decision['has_control']:
            logger.info(f"👑 Leap opportunity exists but Queen's confidence ({queen_decision['confidence']:.2%}) below threshold")
        elif opportunities:
            best = opportunities[0]
            # Execute the best leap opportunity (all criteria already validated)
            if self.execute_quantum_leap(best):
                stats.leaps_made += 1
                stats.breadcrumbs_planted += 1
        else:
            # No opportunities found - why not?
            if self.main_position:
                logger.info("⏸️  No leap opportunities (position holds recovery advantage)")
            stats.breadcrumbs_planted += 0
        
        # 6. SCALP (+ MOUNTAIN CLIMBING LEARNING)
        scalp_opps = self.find_scalp_opportunities()
        for symbol, _pnl_pct in scalp_opps[:3]:  # Max 3 scalps per cycle
            profit = self.execute_scalp(symbol)
            if profit > 0:
                stats.scalps_executed += 1
                stats.profit_realized += profit
        
        # ⛰️ MOUNTAIN CLIMBING - Update climbs and learn optimal strategies
        if self.mountain_climber and self.market_data:
            for symbol, coin in self.market_data.items():
                # Update any active climbs
                climb_update = self.mountain_climber.update_climb(symbol, coin.price)
                if climb_update and 'ropes_triggered' in climb_update:
                    for rope_name in climb_update['ropes_triggered']:
                        logger.info(f"⛰️ PROFIT-TAKING ROPE: {symbol} hit {rope_name}")
                        logger.info(f"   Current Gain: {climb_update['current_gain_pct']:+.1%}")
                        logger.info(f"   Peak Gain: {climb_update['peak_gain_pct']:+.1%}")
            
            # Get climbing recommendations for new positions
            if self.main_position and self.mountain_climber:
                try:
                    recs = self.mountain_climber.get_climb_recommendations(self.main_position.symbol)
                    if recs.get('total_climbs', 0) > 0:
                        logger.info(f"⛰️ MOUNTAIN LEARNING for {self.main_position.symbol}:")
                        logger.info(f"   Recommendation: {recs.get('recommendation', 'N/A')}")
                        logger.info(f"   Success Rate: {recs.get('success_rate', 0):.0%}")
                        logger.info(f"   Peak Capture: {recs.get('peak_capture_efficiency', 'N/A')}")
                except Exception as e:
                    logger.debug(f"Mountain climbing recommendation failed: {e}")
        
        # 7. RECORD
        stats.end_time = datetime.now()
        self.cycle_history.append(stats)
        
        # Log summary
        self._log_cycle_summary(stats)
        
        self._save_state()
        return stats
    
    async def run_forever(self, interval_seconds: int = SCAN_INTERVAL_SECONDS):
        """
        Run the eternal machine forever.
        
        This is the 24/7 loop that never stops.
        """
        self.is_running = True
        logger.info("👑🤖 QUEEN ETERNAL MACHINE ACTIVATED - 24/7 MODE")
        
        try:
            while self.is_running:
                await self.run_cycle()
                await asyncio.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("👑 Machine stopped by user")
        except Exception as e:
            logger.error(f"❌ Machine error: {e}")
        finally:
            self.is_running = False
            self._save_state()
    
    def stop(self):
        """Stop the eternal machine."""
        self.is_running = False
        logger.info("👑 Machine stopping...")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 📊 REPORTING & LOGGING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _log_cycle_summary(self, stats: CycleStats):
        """Log summary of a cycle."""
        logger.info(f"\n📊 CYCLE #{stats.cycle_number} SUMMARY:")
        
        # 🛡️ Friend protection status
        if stats.friends_protected > 0:
            logger.warning(f"   🛡️ ORCA DEFENSE: {stats.friends_protected} friends protected from whale attacks!")
        
        # Main position
        if self.main_position:
            mp = self.main_position
            logger.info(f"   Main: {mp.quantity:.4f} {mp.symbol} @ ${mp.current_price:.4f} = ${mp.current_value:.2f}")
            logger.info(f"         24h: {mp.change_24h:+.2f}% | P&L: ${mp.unrealized_pnl:+.2f}")
        
        # Breadcrumbs
        summary = self.get_breadcrumb_summary()
        logger.info(f"   Breadcrumbs: {summary['count']} positions")
        logger.info(f"         Value: ${summary['total_value']:.2f} | P&L: ${summary['total_pnl']:+.2f} ({summary['pnl_percent']:+.2f}%)")
        
        # Totals
        total_value = (self.main_position.current_value if self.main_position else 0) + summary['total_value'] + self.available_cash
        total_pnl = total_value - self.initial_vault
        logger.info(f"   Total Portfolio: ${total_value:.2f}")
        logger.info(f"   Total P&L: ${total_pnl:+.2f} ({total_pnl/self.initial_vault*100:+.2f}%)")
        logger.info(f"   Cash: ${self.available_cash:.2f}")
        
        # Stats with cycle activity
        logger.info(f"   Cycle Activity: {stats.leaps_made} leaps | {stats.breadcrumbs_planted} breadcrumbs | {stats.scalps_executed} scalps | {stats.friends_protected} protected")
        logger.info(f"   Lifetime: {self.total_leaps} leaps | {self.total_breadcrumbs} breadcrumbs | {self.total_scalps} scalps")
        logger.info(f"   Realized profit: ${self.total_profit_realized:.2f}")
    
    def get_full_report(self) -> Dict[str, Any]:
        """Generate a full portfolio report."""
        self.update_breadcrumbs()
        
        main_value = self.main_position.current_value if self.main_position else 0
        breadcrumb_summary = self.get_breadcrumb_summary()
        total_value = main_value + breadcrumb_summary['total_value'] + self.available_cash
        
        return {
            "timestamp": datetime.now().isoformat(),
            "initial_vault": self.initial_vault,
            "total_value": total_value,
            "total_pnl": total_value - self.initial_vault,
            "total_pnl_percent": (total_value / self.initial_vault - 1) * 100,
            "cash": self.available_cash,
            "main_position": {
                "symbol": self.main_position.symbol if self.main_position else None,
                "quantity": self.main_position.quantity if self.main_position else 0,
                "value": main_value,
                "cost_basis": self.main_position.cost_basis if self.main_position else 0,
                "unrealized_pnl": self.main_position.unrealized_pnl if self.main_position else 0,
                "change_24h": self.main_position.change_24h if self.main_position else 0
            },
            "breadcrumbs": breadcrumb_summary,
            "execution_receipts": {
                "pending_orders": list(self._pending_registry().values()),
                "observed_fees_by_asset": dict(self.observed_fees_by_asset),
                "last_execution_receipt": self.last_execution_receipt,
            },
            "statistics": {
                "total_cycles": self.total_cycles,
                "total_leaps": self.total_leaps,
                "total_breadcrumbs": self.total_breadcrumbs,
                "total_scalps": self.total_scalps,
                "total_profit_realized": self.total_profit_realized,
                "running_since": self.start_time.isoformat() if self.start_time else None
            }
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 💾 STATE PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_state(self):
        """Save current state to file."""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "initial_vault": self.initial_vault,
                "available_cash": self.available_cash,
                "pending_orders": self._pending_registry(),
                "observed_fees_by_asset": self.observed_fees_by_asset,
                "main_position": {
                    "symbol": self.main_position.symbol,
                    "quantity": self.main_position.quantity,
                    "cost_basis": self.main_position.cost_basis,
                    "entry_price": self.main_position.entry_price,
                    "entry_time": self.main_position.entry_time.isoformat()
                } if self.main_position else None,
                "breadcrumbs": {
                    s: {
                        "quantity": c.quantity,
                        "cost_basis": c.cost_basis,
                        "entry_price": c.entry_price,
                        "entry_time": c.entry_time.isoformat(),
                        "exchange": c.exchange
                    }
                    for s, c in self.breadcrumbs.items()
                },
                "statistics": {
                    "total_cycles": self.total_cycles,
                    "total_leaps": self.total_leaps,
                    "total_breadcrumbs": self.total_breadcrumbs,
                    "total_scalps": self.total_scalps,
                    "total_profit_realized": self.total_profit_realized,
                    "start_time": self.start_time.isoformat() if self.start_time else None
                }
            }
            
            # Atomic write (Windows-safe)
            import tempfile
            temp_dir = self.state_file.parent
            with tempfile.NamedTemporaryFile("w", delete=False, dir=temp_dir, suffix=".tmp") as f:
                json.dump(state, f, indent=2)
                temp_path = Path(f.name)
            try:
                os.replace(temp_path, self.state_file)
            finally:
                if temp_path.exists() and temp_path != self.state_file:
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"❌ Failed to save state: {e}")
    
    def _load_state(self):
        """Load state from file if exists."""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file) as f:
                state = json.load(f)
            
            self.initial_vault = state.get("initial_vault", self.initial_vault)
            self.available_cash = state.get("available_cash", 0)

            pending_orders = state.get("pending_orders")
            if isinstance(pending_orders, dict):
                self._pending_orders = {
                    str(key): dict(receipt)
                    for key, receipt in pending_orders.items()
                    if isinstance(receipt, dict)
                    and (
                        (
                            receipt.get("status")
                            == "pending_reconciliation"
                            and receipt.get("reconciliation_required") is True
                        )
                        or receipt.get("status")
                        == "terminal_fill_uncommitted"
                    )
                }
            observed_fees = state.get("observed_fees_by_asset")
            if isinstance(observed_fees, dict):
                self.observed_fees_by_asset = {
                    str(asset).upper(): fee
                    for asset, value in observed_fees.items()
                    if (
                        fee := _finite_receipt_number(
                            value, nonnegative=True
                        )
                    )
                    is not None
                }
            
            # Load main position
            mp_data = state.get("main_position")
            if mp_data:
                self.main_position = MainPosition(
                    symbol=mp_data["symbol"],
                    quantity=mp_data["quantity"],
                    cost_basis=mp_data["cost_basis"],
                    entry_price=mp_data["entry_price"],
                    entry_time=datetime.fromisoformat(mp_data["entry_time"])
                )
            
            # Load breadcrumbs
            for symbol, data in state.get("breadcrumbs", {}).items():
                self.breadcrumbs[symbol] = Breadcrumb(
                    symbol=symbol,
                    quantity=data["quantity"],
                    cost_basis=data["cost_basis"],
                    entry_price=data["entry_price"],
                    entry_time=datetime.fromisoformat(data["entry_time"]),
                    exchange=data.get("exchange", self.exchange)
                )
            
            # Load statistics
            stats = state.get("statistics", {})
            self.total_cycles = stats.get("total_cycles", 0)
            self.total_leaps = stats.get("total_leaps", 0)
            self.total_breadcrumbs = stats.get("total_breadcrumbs", 0)
            self.total_scalps = stats.get("total_scalps", 0)
            self.total_profit_realized = stats.get("total_profit_realized", 0)
            if stats.get("start_time"):
                self.start_time = datetime.fromisoformat(stats["start_time"])
            
            logger.info(f"📂 Loaded state from {self.state_file}")
            logger.info(f"   Main: {self.main_position.symbol if self.main_position else 'None'}")
            logger.info(f"   Breadcrumbs: {len(self.breadcrumbs)}")
            logger.info(f"   Cycles: {self.total_cycles}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎮 CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner():
    """Print the Queen's banner."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     👑🤖 THE QUEEN'S ETERNAL MACHINE 🤖👑                                            ║
║                                                                                      ║
║     🏔️  Mountain Pilgrimage  │  🐸 Quantum Frog      │  💉 Bloodless Descent        ║
║     🟡  Yellow Brick Road    │  🍞 Breadcrumb Trail  │  🤖 24/7 Machine              ║
║                                                                                      ║
║     "I NEVER SLEEP. I NEVER STOP. I AM THE MACHINE."                                ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
    """)


async def run_demo() -> Dict[str, Any]:
    """Print an offline, mutation-free status demonstration."""
    print_banner()

    machine = QueenEternalMachine(
        initial_vault=100.0,
        breadcrumb_percent=0.10,
        min_dip_advantage=0.02,
        dry_run=True,
        load_state=False,
    )

    print("\nOffline dry-run status (no providers, orders, or account reads):")
    report = machine.get_full_report()
    report["economic_boundary"] = machine.economic_boundary_status()
    print("\n" + "="*60)
    print("STATUS REPORT")
    print("="*60)
    print(json.dumps(report, indent=2, default=str))
    return report


async def run_live(
    vault: float = 100.0,
    interval: int = 60,
    start_symbol: str = "ETH",
    *,
    balance_reader: Optional[Callable[[str], Any]] = None,
    market_data_reader: Optional[Callable[[str, Optional[str]], Any]] = None,
    order_status_reader: Optional[Callable[[str, str], Mapping[str, Any]]] = None,
    authorization_provider: Optional[
        Callable[[ForceTradePlan], Optional[OpaqueForceTradeAuthorization]]
    ] = None,
    final_order_dispatcher: Optional[
        Callable[[ForceTradePlan], Mapping[str, Any]]
    ] = None,
) -> bool:
    """Run only when every observation/economic boundary is explicitly injected."""
    print_banner()

    machine = QueenEternalMachine(
        initial_vault=vault,
        breadcrumb_percent=0.10,
        min_dip_advantage=0.02,
        dry_run=False,
        balance_reader=balance_reader,
        market_data_reader=market_data_reader,
        order_status_reader=order_status_reader,
        authorization_provider=authorization_provider,
        final_order_dispatcher=final_order_dispatcher,
    )

    if not machine.live_trading:
        print(
            "\nHOLD: live execution requires LIVE=1 plus an injected "
            "Magic-Star authorization provider and final order dispatcher."
        )
        return False

    # Start journey if not already started
    if not machine.main_position:
        print(f"\n🟡 Starting Yellow Brick Road journey with {start_symbol}...")
        machine.start_journey(start_symbol)

    # Run forever
    print(f"\n🤖 Running 24/7 mode (interval: {interval}s)...")
    print("   Press Ctrl+C to stop\n")

    await machine.run_forever(interval_seconds=interval)
    return True


def main(argv: Optional[List[str]] = None) -> int:
    """Run the safe CLI; no arguments means an offline status report."""

    import argparse

    parser = argparse.ArgumentParser(description="The Queen's Eternal Machine")
    parser.add_argument("--demo", action="store_true", help="Show offline dry-run status")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Request live mode (CLI remains HOLD without injected authority)",
    )
    parser.add_argument("--vault", type=float, default=100.0, help="Initial vault amount")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    parser.add_argument("--symbol", type=str, default="ETH", help="Starting symbol for the journey")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    if args.live:
        started = asyncio.run(run_live(args.vault, args.interval, args.symbol))
        return 0 if started else 2
    asyncio.run(run_demo())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
