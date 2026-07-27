#!/usr/bin/env python3
"""
THE KING - Autonomous Accounting AI
=====================================================
"The King counts every coin. The Queen trades them."

Inspired by the Aureon Enigma architecture (5 Rotors, Reflector, Bombe),
The King transforms signal-decoding into financial-decoding:

ENIGMA ARCHITECTURE          =>  KING ARCHITECTURE
─────────────────────────────────────────────────────
5 Signal Rotors              =>  5 Royal Deciphers
  Σ (Schumann Resonance)     =>  Σ (Transaction Decoder)
  Φ (Golden Ratio)           =>  Φ (Cost Basis Engine - FIFO)
  Ω (Market Harmonics)       =>  Ω (P&L Calculator)
  Γ (Auris Coherence)        =>  Γ (Portfolio Valuation)
  Ψ (Consciousness Field)    =>  Ψ (Tax & Compliance)
Universal Reflector          =>  Royal Treasury (unified truth)
Bombe Pattern Matcher        =>  Royal Auditor (reconciliation)
Intelligence Grades          =>  Financial Health Grades
Dream Engine                 =>  Forecast Engine
Universal Translator         =>  Royal Decree (reports)

FINANCIAL HEALTH GRADES (from Enigma Intelligence Grades):
  SOVEREIGN  (0.85+)  =>  Excellent financial health, growing equity
  PROSPEROUS (0.70+)  =>  Good health, consistent profits
  STABLE     (0.55+)  =>  Neutral, breaking even after costs
  STRAINED   (0.40+)  =>  Losses detected, needs attention
  BANKRUPT   (<0.40)  =>  Critical - trading should halt

The King is AUTONOMOUS:
  - Watches every trade in real-time
  - Maintains double-entry books
  - Tracks cost basis (FIFO) across all exchanges
  - Calculates realized + unrealized P&L
  - Generates tax reports (capital gains/losses)
  - Reconciles with exchange records
  - Detects anomalies and discrepancies
  - Produces daily/weekly/monthly financial reports
  - Works alongside the Queen: She trades, He accounts

Gary Leckey | February 2026
"The King and Queen rule the repo"
"""

import os
import sys
import json
import time
import math
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS - The King's Immutable Laws
# ═══════════════════════════════════════════════════════════════════════════

# Financial Health Grades (mapped from Enigma Intelligence Grades)
class FinancialGrade(Enum):
    SOVEREIGN  = "SOVEREIGN"    # 0.85+ Excellent (was ULTRA)
    PROSPEROUS = "PROSPEROUS"   # 0.70+ Good (was MAGIC)
    STABLE     = "STABLE"       # 0.55+ Neutral (was HUFF_DUFF)
    STRAINED   = "STRAINED"     # 0.40+ Warning (was ENIGMA)
    BANKRUPT   = "BANKRUPT"     # <0.40 Critical (was NOISE)


class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"
    DIVIDEND = "DIVIDEND"
    STAKING_REWARD = "STAKING_REWARD"
    MARGIN_OPEN = "MARGIN_OPEN"
    MARGIN_CLOSE = "MARGIN_CLOSE"
    MARGIN_FEE = "MARGIN_FEE"
    CONVERSION = "CONVERSION"
    TRANSFER = "TRANSFER"


class AccountType(Enum):
    ASSET = "ASSET"           # What we own (crypto holdings, cash)
    LIABILITY = "LIABILITY"   # What we owe (margin loans)
    EQUITY = "EQUITY"         # Net worth (assets - liabilities)
    REVENUE = "REVENUE"       # Income (realized gains, rewards)
    EXPENSE = "EXPENSE"       # Costs (fees, losses)


KING_CONFIG = {
    # Persistence
    "LEDGER_FILE": "king_ledger.json",
    "STATE_FILE": "king_state.json",
    "REPORTS_DIR": "king_reports",
    "AUDIT_LOG": "king_audit.jsonl",

    # Exchange fee profiles (from TradeProfitValidator)
    "EXCHANGE_FEES": {
        "kraken":  {"maker": 0.0016, "taker": 0.0026, "slippage": 0.0005, "spread": 0.0008},
        "binance": {"maker": 0.0010, "taker": 0.0010, "slippage": 0.0003, "spread": 0.0005},
        "alpaca":  {"maker": 0.0015, "taker": 0.0025, "slippage": 0.0005, "spread": 0.0008},
        "capital": {"maker": 0.0000, "taker": 0.0000, "slippage": 0.0005, "spread": 0.0020},
    },

    # Tax configuration
    "TAX_YEAR_START_MONTH": 4,   # UK tax year starts April
    "TAX_YEAR_START_DAY": 6,
    "CGT_ANNUAL_EXEMPTION": 3000.0,  # UK CGT exemption 2024/25
    "CGT_BASIC_RATE": 0.10,          # 10% for basic rate taxpayers
    "CGT_HIGHER_RATE": 0.20,         # 20% for higher rate taxpayers
    "BASE_CURRENCY": os.getenv("BASE_CURRENCY", "GBP"),

    # Autonomous monitoring
    "MONITOR_INTERVAL_SEC": 30,
    "RECONCILE_INTERVAL_SEC": 300,
    "REPORT_INTERVAL_SEC": 3600,

    # Health thresholds
    "SOVEREIGN_THRESHOLD": 0.85,
    "PROSPEROUS_THRESHOLD": 0.70,
    "STABLE_THRESHOLD": 0.55,
    "STRAINED_THRESHOLD": 0.40,

    # Queen's sacred number (minimum profit %)
    "QUEEN_MIN_PROFIT_PCT": 1.88,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES - The King's Records
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Transaction:
    """A single financial event - the atomic unit of accounting."""
    id: str
    timestamp: float
    tx_type: str                    # TransactionType value
    exchange: str                   # kraken, binance, alpaca, capital
    symbol: str                     # Trading pair (e.g., BTCUSD)
    asset: str                      # Base asset (e.g., BTC)
    quote: str                      # Quote asset (e.g., USD)
    side: str                       # buy/sell/deposit/withdrawal
    quantity: float                 # Amount of base asset
    price: float                    # Price per unit in quote
    value: float                    # Total value (quantity * price)
    fee: float = 0.0               # Fee paid
    fee_asset: str = ""            # Asset fee was paid in
    order_id: str = ""             # Exchange order ID
    is_margin: bool = False        # Margin trade?
    leverage: int = 1              # Leverage multiplier
    margin_cost: float = 0.0       # Margin collateral used
    notes: str = ""                # Additional context


@dataclass
class TaxLot:
    """A single buy lot for FIFO cost basis tracking."""
    id: str
    timestamp: float
    exchange: str
    symbol: str
    asset: str
    quantity: float                # Remaining quantity (decreases as sold)
    original_quantity: float       # Original buy quantity
    price: float                   # Purchase price per unit
    cost: float                    # Total cost (quantity * price + fees)
    fee: float                     # Fee paid on purchase
    order_id: str = ""


@dataclass
class RealizedGain:
    """A realized capital gain/loss from selling."""
    id: str
    timestamp: float
    exchange: str
    symbol: str
    asset: str
    quantity_sold: float
    sell_price: float
    sell_value: float
    cost_basis: float              # FIFO cost of the lots consumed
    gross_gain: float              # sell_value - cost_basis
    total_fees: float              # Entry fees + exit fees
    net_gain: float                # gross_gain - total_fees
    hold_time_seconds: float       # Time held (for short/long term classification)
    tax_lots_consumed: List[str] = field(default_factory=list)
    is_margin: bool = False


@dataclass
class PortfolioSnapshot:
    """Point-in-time snapshot of the entire portfolio."""
    timestamp: float
    total_equity: float            # Assets - Liabilities
    total_assets: float            # All asset values
    total_liabilities: float       # Margin loans, etc.
    cash_balance: float            # Fiat balance
    crypto_value: float            # Total crypto holdings value
    unrealized_pnl: float          # Unrealized gains/losses
    realized_pnl_today: float      # Today's realized P&L
    margin_used: float             # Total margin in use
    free_margin: float             # Available margin
    positions: Dict[str, Any] = field(default_factory=dict)
    health_grade: str = "STABLE"
    health_score: float = 0.55


@dataclass
class AuditAlert:
    """An anomaly or discrepancy detected by the Royal Auditor."""
    id: str
    timestamp: float
    severity: str                  # CRITICAL, WARNING, INFO
    category: str                  # RECONCILIATION, PHANTOM_TRADE, FEE_ANOMALY, etc.
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# DECIPHER Σ (SIGMA) - TRANSACTION DECODER
# (From Enigma Rotor Σ: Schumann Resonance -> Transaction Standardization)
# ═══════════════════════════════════════════════════════════════════════════

class TransactionDecipher:
    """
    Decipher Sigma: Decodes raw exchange data into standardized transactions.

    Like the Schumann Resonance rotor decoded Earth's electromagnetic heartbeat,
    this decipher decodes the financial heartbeat - raw exchange events into
    a universal transaction format.
    """

    def __init__(self):
        self.transactions: List[Transaction] = []
        self._tx_counter = 0

    def _next_id(self) -> str:
        self._tx_counter += 1
        return f"TX-{int(time.time())}-{self._tx_counter:06d}"

    def decode_trade(self, exchange: str, symbol: str, side: str,
                     quantity: float, price: float, fee: float = 0.0,
                     fee_asset: str = "", order_id: str = "",
                     is_margin: bool = False, leverage: int = 1,
                     timestamp: float = None) -> Transaction:
        """Decode a trade execution into a standardized transaction."""
        asset, quote = self._split_symbol(symbol)
        ts = timestamp or time.time()
        value = quantity * price

        tx_type = TransactionType.BUY.value if side.lower() == "buy" else TransactionType.SELL.value
        if is_margin:
            tx_type = TransactionType.MARGIN_OPEN.value if side.lower() == "buy" else TransactionType.MARGIN_CLOSE.value

        tx = Transaction(
            id=self._next_id(),
            timestamp=ts,
            tx_type=tx_type,
            exchange=exchange,
            symbol=symbol,
            asset=asset,
            quote=quote,
            side=side.lower(),
            quantity=quantity,
            price=price,
            value=value,
            fee=fee,
            fee_asset=fee_asset or quote,
            order_id=order_id,
            is_margin=is_margin,
            leverage=leverage,
            margin_cost=value / leverage if is_margin and leverage > 1 else 0.0,
        )
        self.transactions.append(tx)
        return tx

    def decode_deposit(self, exchange: str, asset: str, quantity: float,
                       timestamp: float = None) -> Transaction:
        """Decode a deposit event."""
        tx = Transaction(
            id=self._next_id(),
            timestamp=timestamp or time.time(),
            tx_type=TransactionType.DEPOSIT.value,
            exchange=exchange,
            symbol=asset,
            asset=asset,
            quote="",
            side="deposit",
            quantity=quantity,
            price=1.0,
            value=quantity,
        )
        self.transactions.append(tx)
        return tx

    def decode_withdrawal(self, exchange: str, asset: str, quantity: float,
                          fee: float = 0.0, timestamp: float = None) -> Transaction:
        """Decode a withdrawal event."""
        tx = Transaction(
            id=self._next_id(),
            timestamp=timestamp or time.time(),
            tx_type=TransactionType.WITHDRAWAL.value,
            exchange=exchange,
            symbol=asset,
            asset=asset,
            quote="",
            side="withdrawal",
            quantity=quantity,
            price=1.0,
            value=quantity,
            fee=fee,
        )
        self.transactions.append(tx)
        return tx

    def decode_fee(self, exchange: str, asset: str, amount: float,
                   reason: str = "", timestamp: float = None) -> Transaction:
        """Decode a standalone fee event (margin interest, etc.)."""
        tx = Transaction(
            id=self._next_id(),
            timestamp=timestamp or time.time(),
            tx_type=TransactionType.FEE.value if not reason.startswith("margin") else TransactionType.MARGIN_FEE.value,
            exchange=exchange,
            symbol=asset,
            asset=asset,
            quote="",
            side="fee",
            quantity=amount,
            price=1.0,
            value=amount,
            notes=reason,
        )
        self.transactions.append(tx)
        return tx

    def get_transactions(self, exchange: str = None, asset: str = None,
                         since: float = None) -> List[Transaction]:
        """Query transactions with optional filters."""
        result = self.transactions
        if exchange:
            result = [t for t in result if t.exchange == exchange]
        if asset:
            result = [t for t in result if t.asset == asset]
        if since:
            result = [t for t in result if t.timestamp >= since]
        return result

    def _split_symbol(self, symbol: str) -> Tuple[str, str]:
        """Split a trading pair into base and quote assets."""
        symbol = symbol.upper().replace("/", "")
        for q in ["USDT", "USDC", "USD", "GBP", "EUR", "BTC", "XBT", "ETH"]:
            if symbol.endswith(q) and len(symbol) > len(q):
                base = symbol[:-len(q)]
                if base == "XBT":
                    base = "BTC"
                return base, q
        return symbol, ""


# ═══════════════════════════════════════════════════════════════════════════
# DECIPHER Φ (PHI) - COST BASIS ENGINE (FIFO)
# (From Enigma Rotor Φ: Golden Ratio -> FIFO Cost Basis)
# ═══════════════════════════════════════════════════════════════════════════

class CostBasisDecipher:
    """
    Decipher Phi: Tracks cost basis using FIFO (First In, First Out).

    Like the Golden Ratio rotor found natural mathematical patterns,
    this decipher finds the true cost of every position by tracking
    every buy lot and consuming them in order when selling.
    """

    def __init__(self):
        # Keyed by "exchange:asset" for cross-exchange tracking
        self.tax_lots: Dict[str, List[TaxLot]] = defaultdict(list)
        self.realized_gains: List[RealizedGain] = []
        self._lot_counter = 0

    def _next_lot_id(self) -> str:
        self._lot_counter += 1
        return f"LOT-{int(time.time())}-{self._lot_counter:06d}"

    def record_buy(self, tx: Transaction) -> TaxLot:
        """Record a buy transaction as a new tax lot."""
        key = f"{tx.exchange}:{tx.asset}"
        lot = TaxLot(
            id=self._next_lot_id(),
            timestamp=tx.timestamp,
            exchange=tx.exchange,
            symbol=tx.symbol,
            asset=tx.asset,
            quantity=tx.quantity,
            original_quantity=tx.quantity,
            price=tx.price,
            cost=tx.value + tx.fee,
            fee=tx.fee,
            order_id=tx.order_id,
        )
        self.tax_lots[key].append(lot)
        return lot

    def record_sell(self, tx: Transaction) -> Optional[RealizedGain]:
        """
        Record a sell transaction, consuming FIFO tax lots.
        Returns the realized gain/loss.
        """
        key = f"{tx.exchange}:{tx.asset}"
        lots = self.tax_lots.get(key, [])

        if not lots:
            logger.warning(f"King: No tax lots for {key} - recording sell without cost basis")
            return None

        remaining_qty = tx.quantity
        total_cost_basis = 0.0
        total_entry_fees = 0.0
        consumed_lot_ids = []
        earliest_buy_time = tx.timestamp

        # FIFO: consume oldest lots first
        while remaining_qty > 0 and lots:
            lot = lots[0]
            earliest_buy_time = min(earliest_buy_time, lot.timestamp)

            if lot.quantity <= remaining_qty:
                # Consume entire lot
                total_cost_basis += lot.cost
                total_entry_fees += lot.fee
                remaining_qty -= lot.quantity
                consumed_lot_ids.append(lot.id)
                lots.pop(0)
            else:
                # Partial consumption
                fraction = remaining_qty / lot.quantity
                partial_cost = lot.cost * fraction
                partial_fee = lot.fee * fraction
                total_cost_basis += partial_cost
                total_entry_fees += partial_fee
                lot.quantity -= remaining_qty
                lot.cost -= partial_cost
                lot.fee -= partial_fee
                consumed_lot_ids.append(f"{lot.id}(partial)")
                remaining_qty = 0

        sell_value = tx.quantity * tx.price
        gross_gain = sell_value - total_cost_basis
        total_fees = total_entry_fees + tx.fee
        # Net gain: gross minus ONLY the exit fee.
        # Entry fees are already embedded in total_cost_basis (lot.cost = value + fee)
        # so they are already subtracted from gross_gain.
        net_gain = gross_gain - tx.fee

        if remaining_qty > 0:
            logger.warning(
                f"King FIFO: {remaining_qty:.8f} of {tx.quantity:.8f} {tx.asset} "
                f"could not be matched to buy lots — cost basis incomplete"
            )

        hold_time = tx.timestamp - earliest_buy_time

        gain = RealizedGain(
            id=f"GAIN-{int(time.time())}-{len(self.realized_gains):06d}",
            timestamp=tx.timestamp,
            exchange=tx.exchange,
            symbol=tx.symbol,
            asset=tx.asset,
            quantity_sold=tx.quantity,
            sell_price=tx.price,
            sell_value=sell_value,
            cost_basis=total_cost_basis,
            gross_gain=gross_gain,
            total_fees=total_fees,
            net_gain=net_gain,
            hold_time_seconds=hold_time,
            tax_lots_consumed=consumed_lot_ids,
            is_margin=tx.is_margin,
        )
        self.realized_gains.append(gain)
        return gain

    def get_cost_basis(self, exchange: str, asset: str) -> Dict[str, float]:
        """Get current cost basis for an asset on an exchange."""
        key = f"{exchange}:{asset}"
        lots = self.tax_lots.get(key, [])
        if not lots:
            return {"quantity": 0.0, "total_cost": 0.0, "avg_price": 0.0, "num_lots": 0}

        total_qty = sum(lot.quantity for lot in lots)
        total_cost = sum(lot.cost for lot in lots)
        avg_price = total_cost / total_qty if total_qty > 0 else 0.0

        return {
            "quantity": total_qty,
            "total_cost": total_cost,
            "avg_price": avg_price,
            "num_lots": len(lots),
        }

    def get_all_positions(self) -> Dict[str, Dict[str, float]]:
        """Get cost basis for all tracked positions."""
        positions = {}
        for key, lots in self.tax_lots.items():
            if lots:
                total_qty = sum(l.quantity for l in lots)
                if total_qty > 0:
                    total_cost = sum(l.cost for l in lots)
                    positions[key] = {
                        "quantity": total_qty,
                        "total_cost": total_cost,
                        "avg_price": total_cost / total_qty,
                        "num_lots": len(lots),
                        "exchange": lots[0].exchange,
                        "asset": lots[0].asset,
                    }
        return positions

    def can_sell_profitably(self, exchange: str, asset: str,
                            current_price: float, quantity: float,
                            fee_pct: float = 0.0026) -> Tuple[bool, Dict]:
        """Check if selling would be profitable after all costs."""
        key = f"{exchange}:{asset}"
        lots = self.tax_lots.get(key, [])
        if not lots:
            return False, {"error": "no_lots"}

        # Calculate FIFO cost basis for the quantity to sell
        remaining = quantity
        cost_basis = 0.0
        for lot in lots:
            if remaining <= 0:
                break
            take = min(lot.quantity, remaining)
            cost_basis += (take / lot.quantity) * lot.cost
            remaining -= take

        sell_value = quantity * current_price
        exit_fee = sell_value * fee_pct
        gross_pnl = sell_value - cost_basis
        net_pnl = gross_pnl - exit_fee

        return net_pnl > 0, {
            "cost_basis": cost_basis,
            "sell_value": sell_value,
            "gross_pnl": gross_pnl,
            "exit_fee": exit_fee,
            "net_pnl": net_pnl,
            "profit_pct": (net_pnl / cost_basis * 100) if cost_basis > 0 else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════
# DECIPHER Ω (OMEGA) - P&L CALCULATOR
# (From Enigma Rotor Ω: Market Harmonics -> P&L Dynamics)
# ═══════════════════════════════════════════════════════════════════════════

class PnLDecipher:
    """
    Decipher Omega: Calculates realized and unrealized P&L.

    Like the Market Harmonics rotor analyzed price-volume waves,
    this decipher tracks the harmonic flow of profits and losses
    across the entire portfolio in real-time.
    """

    def __init__(self, cost_basis: CostBasisDecipher):
        self.cost_basis = cost_basis
        self.daily_realized: Dict[str, float] = defaultdict(float)  # date_str -> pnl
        self.total_realized: float = 0.0
        self.total_fees_paid: float = 0.0
        self.wins: int = 0
        self.losses: int = 0

    def record_realized(self, gain: RealizedGain):
        """Record a realized gain/loss."""
        day = datetime.fromtimestamp(gain.timestamp).strftime("%Y-%m-%d")
        self.daily_realized[day] += gain.net_gain
        self.total_realized += gain.net_gain
        self.total_fees_paid += gain.total_fees

        if gain.net_gain > 0:
            self.wins += 1
        else:
            self.losses += 1

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> Dict[str, Dict]:
        """
        Calculate unrealized P&L for all positions.

        Args:
            current_prices: Dict of "exchange:asset" -> current_price
        """
        positions = self.cost_basis.get_all_positions()
        unrealized = {}
        total_unrealized = 0.0

        for key, pos in positions.items():
            price = current_prices.get(key, 0.0)
            if price <= 0:
                continue

            current_value = pos["quantity"] * price
            cost = pos["total_cost"]
            pnl = current_value - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

            unrealized[key] = {
                "quantity": pos["quantity"],
                "avg_entry": pos["avg_price"],
                "current_price": price,
                "cost_basis": cost,
                "current_value": current_value,
                "unrealized_pnl": pnl,
                "unrealized_pct": pnl_pct,
            }
            total_unrealized += pnl

        return {
            "positions": unrealized,
            "total_unrealized": total_unrealized,
        }

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0

    def get_summary(self) -> Dict[str, Any]:
        # total_realized already IS net of all fees:
        #   net_gain = gross_gain - exit_fee (entry fees baked into cost_basis)
        # gross_realized = total_realized + total_fees gives the pre-fee number
        gross_realized = self.total_realized + self.total_fees_paid
        return {
            "total_realized_pnl": self.total_realized,
            "gross_realized_pnl": gross_realized,
            "total_fees_paid": self.total_fees_paid,
            "net_after_fees": self.total_realized,
            "total_trades": self.wins + self.losses,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "daily_pnl": dict(self.daily_realized),
        }


# ═══════════════════════════════════════════════════════════════════════════
# DECIPHER Γ (GAMMA) - PORTFOLIO VALUATION
# (From Enigma Rotor Γ: Auris Coherence -> Portfolio Coherence)
# ═══════════════════════════════════════════════════════════════════════════

class PortfolioDecipher:
    """
    Decipher Gamma: Multi-exchange portfolio valuation and coherence.

    Like the Auris Coherence rotor measured market bio-field coherence,
    this decipher measures the coherence of the entire portfolio -
    how well-balanced, diversified, and healthy the holdings are.
    """

    def __init__(self, cost_basis: CostBasisDecipher, pnl: PnLDecipher):
        self.cost_basis = cost_basis
        self.pnl = pnl
        self.snapshots: List[PortfolioSnapshot] = []
        self.peak_equity: float = 0.0
        self.initial_equity: float = 0.0

    def take_snapshot(self, current_prices: Dict[str, float],
                      cash_balances: Dict[str, float] = None,
                      margin_info: Dict[str, float] = None) -> PortfolioSnapshot:
        """Take a point-in-time snapshot of the portfolio."""
        positions = self.cost_basis.get_all_positions()
        unrealized = self.pnl.get_unrealized_pnl(current_prices)

        # Calculate crypto value
        crypto_value = 0.0
        pos_details = {}
        for key, pos in positions.items():
            price = current_prices.get(key, 0.0)
            value = pos["quantity"] * price if price > 0 else pos["total_cost"]
            crypto_value += value
            pos_details[key] = {
                "quantity": pos["quantity"],
                "value": value,
                "cost_basis": pos["total_cost"],
                "exchange": pos.get("exchange", ""),
                "asset": pos.get("asset", ""),
            }

        # Cash balances
        total_cash = sum((cash_balances or {}).values())

        # Margin
        margin_used = (margin_info or {}).get("margin_amount", 0.0)
        free_margin = (margin_info or {}).get("free_margin", 0.0)
        margin_liability = margin_used  # Borrowed amount

        total_assets = crypto_value + total_cash
        total_liabilities = margin_liability
        total_equity = total_assets - total_liabilities

        # Track peak for drawdown calculation
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity
        if self.initial_equity == 0:
            self.initial_equity = total_equity

        # Calculate health
        health_score, health_grade = self._calculate_health(
            total_equity, unrealized["total_unrealized"]
        )

        # Today's realized
        today = datetime.now().strftime("%Y-%m-%d")
        realized_today = self.pnl.daily_realized.get(today, 0.0)

        snapshot = PortfolioSnapshot(
            timestamp=time.time(),
            total_equity=total_equity,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            cash_balance=total_cash,
            crypto_value=crypto_value,
            unrealized_pnl=unrealized["total_unrealized"],
            realized_pnl_today=realized_today,
            margin_used=margin_used,
            free_margin=free_margin,
            positions=pos_details,
            health_grade=health_grade.value,
            health_score=health_score,
        )
        self.snapshots.append(snapshot)
        return snapshot

    def _calculate_health(self, equity: float,
                          unrealized: float) -> Tuple[float, FinancialGrade]:
        """Calculate financial health score and grade."""
        score = 0.5  # Start neutral

        # Equity growth factor
        if self.initial_equity > 0:
            growth = (equity - self.initial_equity) / self.initial_equity
            score += growth * 0.3  # 30% weight on growth

        # Drawdown factor
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - equity) / self.peak_equity
            score -= drawdown * 0.4  # 40% weight on drawdown

        # Win rate factor
        if self.pnl.wins + self.pnl.losses > 0:
            wr = self.pnl.win_rate / 100.0
            score += (wr - 0.5) * 0.2  # 20% weight on win rate

        # Unrealized P&L factor
        if equity > 0:
            unrealized_ratio = unrealized / equity
            score += unrealized_ratio * 0.1  # 10% weight

        score = max(0.0, min(1.0, score))

        if score >= KING_CONFIG["SOVEREIGN_THRESHOLD"]:
            grade = FinancialGrade.SOVEREIGN
        elif score >= KING_CONFIG["PROSPEROUS_THRESHOLD"]:
            grade = FinancialGrade.PROSPEROUS
        elif score >= KING_CONFIG["STABLE_THRESHOLD"]:
            grade = FinancialGrade.STABLE
        elif score >= KING_CONFIG["STRAINED_THRESHOLD"]:
            grade = FinancialGrade.STRAINED
        else:
            grade = FinancialGrade.BANKRUPT

        return score, grade

    def get_drawdown(self) -> Dict[str, float]:
        """Get current and max drawdown."""
        if not self.snapshots:
            return {"current_dd": 0.0, "max_dd": 0.0, "peak": 0.0}

        current = self.snapshots[-1].total_equity
        current_dd = 0.0
        if self.peak_equity > 0:
            current_dd = (self.peak_equity - current) / self.peak_equity * 100

        # Calculate max historical drawdown
        peak = 0.0
        max_dd = 0.0
        for snap in self.snapshots:
            if snap.total_equity > peak:
                peak = snap.total_equity
            dd = (peak - snap.total_equity) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "current_dd_pct": current_dd,
            "max_dd_pct": max_dd,
            "peak_equity": self.peak_equity,
            "current_equity": current,
        }


# ═══════════════════════════════════════════════════════════════════════════
# DECIPHER Ψ (PSI) - TAX & COMPLIANCE
# (From Enigma Rotor Ψ: Consciousness Field -> Tax Consciousness)
# ═══════════════════════════════════════════════════════════════════════════

class TaxDecipher:
    """
    Decipher Psi: Tax calculations and compliance tracking.

    Like the Consciousness Field rotor read market psychology,
    this decipher maintains awareness of tax obligations -
    capital gains, losses, exemptions, and reporting requirements.
    """

    def __init__(self, cost_basis: CostBasisDecipher):
        self.cost_basis = cost_basis
        self.base_currency = KING_CONFIG["BASE_CURRENCY"]

    def get_tax_year_range(self, year: int = None) -> Tuple[float, float]:
        """Get start/end timestamps for a UK tax year."""
        now = datetime.now()
        if year is None:
            # Current tax year
            if now.month < 4 or (now.month == 4 and now.day < 6):
                year = now.year - 1
            else:
                year = now.year

        start = datetime(year, KING_CONFIG["TAX_YEAR_START_MONTH"],
                         KING_CONFIG["TAX_YEAR_START_DAY"])
        end = datetime(year + 1, KING_CONFIG["TAX_YEAR_START_MONTH"],
                       KING_CONFIG["TAX_YEAR_START_DAY"]) - timedelta(seconds=1)
        return start.timestamp(), end.timestamp()

    def calculate_capital_gains(self, gains: List[RealizedGain],
                                tax_year: int = None) -> Dict[str, Any]:
        """
        Calculate capital gains tax for a UK tax year.

        Uses FIFO cost basis. Separates short-term and long-term gains.
        Applies annual CGT exemption.
        """
        start_ts, end_ts = self.get_tax_year_range(tax_year)

        # Filter gains for tax year
        year_gains = [g for g in gains if start_ts <= g.timestamp <= end_ts]

        total_gains = 0.0
        total_losses = 0.0
        short_term_gains = 0.0
        long_term_gains = 0.0
        total_fees = 0.0
        trade_count = 0

        for gain in year_gains:
            trade_count += 1
            total_fees += gain.total_fees

            if gain.net_gain >= 0:
                total_gains += gain.net_gain
                # Short-term: held < 1 year (365.25 days)
                if gain.hold_time_seconds < 365.25 * 86400:
                    short_term_gains += gain.net_gain
                else:
                    long_term_gains += gain.net_gain
            else:
                total_losses += abs(gain.net_gain)

        # Net gains after losses
        net_gains = total_gains - total_losses

        # Apply annual exemption
        exemption = KING_CONFIG["CGT_ANNUAL_EXEMPTION"]
        taxable_gains = max(0, net_gains - exemption)

        # Calculate tax at basic rate (simplified - real calc depends on income band)
        tax_basic = taxable_gains * KING_CONFIG["CGT_BASIC_RATE"]
        tax_higher = taxable_gains * KING_CONFIG["CGT_HIGHER_RATE"]

        return {
            "tax_year": f"{tax_year or 'current'}/{(tax_year or 0) + 1}",
            "total_disposals": trade_count,
            "total_gains": total_gains,
            "total_losses": total_losses,
            "net_gains": net_gains,
            "short_term_gains": short_term_gains,
            "long_term_gains": long_term_gains,
            "annual_exemption": exemption,
            "taxable_gains": taxable_gains,
            "estimated_tax_basic_rate": tax_basic,
            "estimated_tax_higher_rate": tax_higher,
            "total_fees_deductible": total_fees,
            "disposals": [
                {
                    "date": datetime.fromtimestamp(g.timestamp).strftime("%Y-%m-%d"),
                    "asset": g.asset,
                    "quantity": g.quantity_sold,
                    "proceeds": g.sell_value,
                    "cost_basis": g.cost_basis,
                    "gain_loss": g.net_gain,
                    "hold_days": int(g.hold_time_seconds / 86400),
                }
                for g in year_gains
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════
# ROYAL TREASURY - Unified Financial Truth
# (From Enigma Universal Reflector)
# ═══════════════════════════════════════════════════════════════════════════

class RoyalTreasury:
    """
    The Royal Treasury: Combines all 5 Royal Deciphers into unified truth.

    Like the Enigma's Universal Reflector combined all rotor outputs through
    the 10-9-1 law, the Royal Treasury combines all accounting engines
    into one authoritative source of financial truth.
    """

    def __init__(self):
        self.sigma = TransactionDecipher()    # Transaction decoder
        self.phi = CostBasisDecipher()         # Cost basis (FIFO)
        self.omega = PnLDecipher(self.phi)     # P&L calculator
        self.gamma = PortfolioDecipher(self.phi, self.omega)  # Portfolio valuation
        self.psi = TaxDecipher(self.phi)       # Tax & compliance

    def process_trade(self, exchange: str, symbol: str, side: str,
                      quantity: float, price: float, fee: float = 0.0,
                      order_id: str = "", is_margin: bool = False,
                      leverage: int = 1, timestamp: float = None) -> Dict[str, Any]:
        """
        Process a trade through all deciphers. This is the main entry point.
        Returns a comprehensive accounting summary for the trade.
        """
        # Σ - Decode transaction
        tx = self.sigma.decode_trade(
            exchange, symbol, side, quantity, price,
            fee=fee, order_id=order_id, is_margin=is_margin,
            leverage=leverage, timestamp=timestamp,
        )

        result = {
            "transaction_id": tx.id,
            "type": tx.tx_type,
            "exchange": exchange,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "value": tx.value,
            "fee": fee,
            "is_margin": is_margin,
        }

        if side.lower() == "buy":
            # Φ - Record cost basis
            lot = self.phi.record_buy(tx)
            result["tax_lot_id"] = lot.id
            result["cost_basis"] = lot.cost

        elif side.lower() == "sell":
            # Φ - Consume FIFO lots + Ω - Record P&L
            gain = self.phi.record_sell(tx)
            if gain:
                self.omega.record_realized(gain)
                result["realized_gain"] = {
                    "gross": gain.gross_gain,
                    "net": gain.net_gain,
                    "cost_basis": gain.cost_basis,
                    "fees": gain.total_fees,
                    "hold_time_hrs": gain.hold_time_seconds / 3600,
                    "lots_consumed": gain.tax_lots_consumed,
                }
            else:
                result["warning"] = "No cost basis found for this sell"

        return result

    def process_deposit(self, exchange: str, asset: str, quantity: float,
                        timestamp: float = None) -> Dict[str, Any]:
        tx = self.sigma.decode_deposit(exchange, asset, quantity, timestamp)
        return {"transaction_id": tx.id, "type": "DEPOSIT", "asset": asset, "quantity": quantity}

    def process_withdrawal(self, exchange: str, asset: str, quantity: float,
                           fee: float = 0.0, timestamp: float = None) -> Dict[str, Any]:
        tx = self.sigma.decode_withdrawal(exchange, asset, quantity, fee, timestamp)
        return {"transaction_id": tx.id, "type": "WITHDRAWAL", "asset": asset, "quantity": quantity}


# ═══════════════════════════════════════════════════════════════════════════
# ROYAL AUDITOR - Reconciliation & Anomaly Detection
# (From Enigma Bombe Pattern Matcher)
# ═══════════════════════════════════════════════════════════════════════════

class RoyalAuditor:
    """
    The Royal Auditor: Reconciles books with exchange records, detects anomalies.

    Like the Enigma's Bombe tested hypothesis patterns against decoded signals,
    the Royal Auditor tests the King's books against exchange reality,
    flagging any discrepancy.
    """

    def __init__(self, treasury: RoyalTreasury):
        self.treasury = treasury
        self.alerts: List[AuditAlert] = []
        self._alert_counter = 0

    def _create_alert(self, severity: str, category: str,
                      message: str, details: Dict = None) -> AuditAlert:
        self._alert_counter += 1
        alert = AuditAlert(
            id=f"AUDIT-{int(time.time())}-{self._alert_counter:04d}",
            timestamp=time.time(),
            severity=severity,
            category=category,
            message=message,
            details=details or {},
        )
        self.alerts.append(alert)
        return alert

    def reconcile_balances(self, exchange: str,
                           live_balances: Dict[str, float]) -> List[AuditAlert]:
        """
        Reconcile the King's tracked positions against live exchange balances.
        Returns list of discrepancy alerts.
        """
        new_alerts = []
        tracked = self.treasury.phi.get_all_positions()

        # Check each tracked position against live
        for key, pos in tracked.items():
            if not key.startswith(f"{exchange}:"):
                continue
            asset = pos["asset"]
            tracked_qty = pos["quantity"]
            live_qty = live_balances.get(asset, 0.0)

            # Allow 1% tolerance for rounding
            if tracked_qty > 0 and abs(tracked_qty - live_qty) / tracked_qty > 0.01:
                alert = self._create_alert(
                    severity="WARNING",
                    category="RECONCILIATION",
                    message=f"Balance mismatch for {asset} on {exchange}: "
                            f"tracked={tracked_qty:.8f}, live={live_qty:.8f}",
                    details={
                        "exchange": exchange,
                        "asset": asset,
                        "tracked": tracked_qty,
                        "live": live_qty,
                        "difference": live_qty - tracked_qty,
                    }
                )
                new_alerts.append(alert)

        # Check for assets on exchange not tracked by King
        for asset, qty in live_balances.items():
            if qty <= 0:
                continue
            key = f"{exchange}:{asset}"
            if key not in tracked:
                alert = self._create_alert(
                    severity="INFO",
                    category="UNTRACKED_ASSET",
                    message=f"Untracked asset on {exchange}: {asset} = {qty:.8f}",
                    details={"exchange": exchange, "asset": asset, "quantity": qty},
                )
                new_alerts.append(alert)

        return new_alerts

    def check_fee_anomalies(self, tx: Transaction) -> Optional[AuditAlert]:
        """Check if a transaction's fee is abnormally high."""
        fee_profiles = KING_CONFIG["EXCHANGE_FEES"].get(tx.exchange, {})
        expected_taker = fee_profiles.get("taker", 0.003)
        expected_fee = tx.value * expected_taker

        if tx.fee > 0 and tx.fee > expected_fee * 3:
            return self._create_alert(
                severity="WARNING",
                category="FEE_ANOMALY",
                message=f"Unusually high fee on {tx.exchange}: "
                        f"paid={tx.fee:.4f}, expected~{expected_fee:.4f}",
                details={
                    "transaction_id": tx.id,
                    "fee_paid": tx.fee,
                    "expected_fee": expected_fee,
                    "ratio": tx.fee / expected_fee if expected_fee > 0 else 0,
                }
            )
        return None

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary of all audit findings."""
        critical = [a for a in self.alerts if a.severity == "CRITICAL" and not a.resolved]
        warnings = [a for a in self.alerts if a.severity == "WARNING" and not a.resolved]
        info = [a for a in self.alerts if a.severity == "INFO" and not a.resolved]

        return {
            "total_alerts": len(self.alerts),
            "unresolved": len(critical) + len(warnings) + len(info),
            "critical": len(critical),
            "warnings": len(warnings),
            "info": len(info),
            "recent_alerts": [
                {
                    "id": a.id,
                    "severity": a.severity,
                    "category": a.category,
                    "message": a.message,
                    "time": datetime.fromtimestamp(a.timestamp).isoformat(),
                }
                for a in sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:10]
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════
# THE KING - Autonomous Accounting AI
# ═══════════════════════════════════════════════════════════════════════════

class TheKing:
    """
    THE KING: Autonomous Accounting AI for the Aureon Trading Ecosystem.

    The King watches every trade, maintains the books, calculates taxes,
    reconciles with exchanges, detects anomalies, and generates reports.

    The Queen trades. The King counts.
    Together they rule the repo.

    Usage:
        king = get_king()
        king.ingest_trade('kraken', 'BTCUSD', 'buy', 0.001, 95000.0, fee=0.25)
        king.ingest_trade('kraken', 'BTCUSD', 'sell', 0.001, 96000.0, fee=0.25)
        print(king.get_financial_summary())
        print(king.get_tax_report())
    """

    def __init__(self):
        self.treasury = RoyalTreasury()
        self.auditor = RoyalAuditor(self.treasury)
        self.base_currency = KING_CONFIG["BASE_CURRENCY"]
        self.start_time = time.time()

        # Order Flow Velocity - The King's Speedometer
        self.order_flow = get_order_flow_velocity()

        # Autonomous monitoring state
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Load persisted state
        self._load_state()
        logger.info("The King has risen. Autonomous Accounting AI initialized.")

    # ─────────────────────────────────────────────────────────
    # Trade Ingestion - The King's Eyes
    # ─────────────────────────────────────────────────────────

    def ingest_trade(self, exchange: str, symbol: str, side: str,
                     quantity: float, price: float, fee: float = 0.0,
                     order_id: str = "", is_margin: bool = False,
                     leverage: int = 1, timestamp: float = None) -> Dict[str, Any]:
        """
        Ingest a trade into the King's accounting system.
        This is the primary method called by the trading ecosystem.
        """
        with self._lock:
            result = self.treasury.process_trade(
                exchange, symbol, side, quantity, price,
                fee=fee, order_id=order_id, is_margin=is_margin,
                leverage=leverage, timestamp=timestamp,
            )

            # ── ORDER FLOW VELOCITY ── Track buy/sell speed ──
            trade_value = quantity * price
            if side.lower() == "buy":
                self.order_flow.record_buy(trade_value, exchange)
            else:
                self.order_flow.record_sell(trade_value, exchange)

            # Audit the transaction
            tx = self.treasury.sigma.transactions[-1]
            fee_alert = self.auditor.check_fee_anomalies(tx)
            if fee_alert:
                result["audit_alert"] = fee_alert.message

            # Auto-save
            self._save_state()

            # Log the event
            self._audit_log("TRADE", result)

            return result

    def ingest_deposit(self, exchange: str, asset: str, quantity: float,
                       timestamp: float = None) -> Dict[str, Any]:
        """Record a deposit."""
        with self._lock:
            result = self.treasury.process_deposit(exchange, asset, quantity, timestamp)
            self._save_state()
            self._audit_log("DEPOSIT", result)
            return result

    def ingest_withdrawal(self, exchange: str, asset: str, quantity: float,
                          fee: float = 0.0, timestamp: float = None) -> Dict[str, Any]:
        """Record a withdrawal."""
        with self._lock:
            result = self.treasury.process_withdrawal(exchange, asset, quantity, fee, timestamp)
            self._save_state()
            self._audit_log("WITHDRAWAL", result)
            return result

    # ─────────────────────────────────────────────────────────
    # Financial Queries - The King's Voice
    # ─────────────────────────────────────────────────────────

    def get_financial_summary(self, current_prices: Dict[str, float] = None) -> Dict[str, Any]:
        """Get a comprehensive financial summary."""
        pnl = self.treasury.omega.get_summary()
        positions = self.treasury.phi.get_all_positions()
        unrealized = self.treasury.omega.get_unrealized_pnl(current_prices or {})
        audit = self.auditor.get_audit_summary()

        return {
            "timestamp": datetime.now().isoformat(),
            "the_king_says": self._get_royal_decree(pnl),
            "realized_pnl": pnl,
            "unrealized": unrealized,
            "positions": positions,
            "audit": audit,
            "total_transactions": len(self.treasury.sigma.transactions),
        }

    def get_portfolio_snapshot(self, current_prices: Dict[str, float] = None,
                               cash_balances: Dict[str, float] = None,
                               margin_info: Dict[str, float] = None) -> Dict[str, Any]:
        """Take a portfolio snapshot with health grading."""
        snapshot = self.treasury.gamma.take_snapshot(
            current_prices or {}, cash_balances, margin_info
        )
        drawdown = self.treasury.gamma.get_drawdown()

        return {
            "equity": snapshot.total_equity,
            "assets": snapshot.total_assets,
            "liabilities": snapshot.total_liabilities,
            "cash": snapshot.cash_balance,
            "crypto_value": snapshot.crypto_value,
            "unrealized_pnl": snapshot.unrealized_pnl,
            "realized_today": snapshot.realized_pnl_today,
            "margin_used": snapshot.margin_used,
            "free_margin": snapshot.free_margin,
            "health_grade": snapshot.health_grade,
            "health_score": snapshot.health_score,
            "drawdown": drawdown,
            "positions": snapshot.positions,
        }

    def get_velocity_report(self) -> Dict[str, Any]:
        """
        Get the King's Order Flow Velocity report.
        Shows how fast buys/sells are happening and what it means.
        """
        return self.order_flow.get_velocity_report()

    def get_pnl_report(self, days: int = 30) -> Dict[str, Any]:
        """Get P&L report for the last N days."""
        pnl = self.treasury.omega
        cutoff = time.time() - (days * 86400)
        recent_gains = [g for g in self.treasury.phi.realized_gains
                        if g.timestamp >= cutoff]

        daily = {}
        for gain in recent_gains:
            day = datetime.fromtimestamp(gain.timestamp).strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"gains": 0.0, "losses": 0.0, "fees": 0.0, "trades": 0}
            if gain.net_gain >= 0:
                daily[day]["gains"] += gain.net_gain
            else:
                daily[day]["losses"] += abs(gain.net_gain)
            daily[day]["fees"] += gain.total_fees
            daily[day]["trades"] += 1

        return {
            "period_days": days,
            "total_realized": sum(g.net_gain for g in recent_gains),
            "total_fees": sum(g.total_fees for g in recent_gains),
            "trade_count": len(recent_gains),
            "wins": sum(1 for g in recent_gains if g.net_gain > 0),
            "losses": sum(1 for g in recent_gains if g.net_gain <= 0),
            "best_trade": max((g.net_gain for g in recent_gains), default=0),
            "worst_trade": min((g.net_gain for g in recent_gains), default=0),
            "daily_breakdown": daily,
        }

    def get_tax_report(self, tax_year: int = None) -> Dict[str, Any]:
        """Generate a tax report for the specified tax year."""
        gains = self.treasury.phi.realized_gains
        return self.treasury.psi.calculate_capital_gains(gains, tax_year)

    def get_cost_basis(self, exchange: str, asset: str) -> Dict[str, float]:
        """Get current cost basis for a specific asset."""
        return self.treasury.phi.get_cost_basis(exchange, asset)

    def can_sell_profitably(self, exchange: str, asset: str,
                            current_price: float, quantity: float) -> Tuple[bool, Dict]:
        """Check if selling would be profitable after all costs."""
        fee_pct = KING_CONFIG["EXCHANGE_FEES"].get(exchange, {}).get("taker", 0.003)
        return self.treasury.phi.can_sell_profitably(
            exchange, asset, current_price, quantity, fee_pct
        )

    # ─────────────────────────────────────────────────────────
    # Reconciliation - The King's Justice
    # ─────────────────────────────────────────────────────────

    def reconcile(self, exchange: str,
                  live_balances: Dict[str, float]) -> Dict[str, Any]:
        """Reconcile King's books with live exchange balances."""
        alerts = self.auditor.reconcile_balances(exchange, live_balances)
        return {
            "exchange": exchange,
            "alerts_raised": len(alerts),
            "alerts": [{"severity": a.severity, "message": a.message} for a in alerts],
        }

    def get_audit_report(self) -> Dict[str, Any]:
        """Get the full audit report."""
        return self.auditor.get_audit_summary()

    # ─────────────────────────────────────────────────────────
    # Royal Decree - The King's Proclamations
    # ─────────────────────────────────────────────────────────

    def _get_royal_decree(self, pnl_summary: Dict) -> str:
        """Generate a royal proclamation about financial health."""
        total = pnl_summary.get("total_realized_pnl", 0)
        wr = pnl_summary.get("win_rate", 0)
        trades = pnl_summary.get("total_trades", 0)

        if trades == 0:
            return "The King awaits. No trades have been recorded yet."

        cs = "GBP" if self.base_currency == "GBP" else "USD"
        sym = "£" if cs == "GBP" else "$"

        if total > 0 and wr >= 55:
            return (f"The Treasury flourishes! {sym}{total:+.2f} realized "
                    f"across {trades} trades ({wr:.1f}% win rate). "
                    f"The Queen trades well.")
        elif total > 0:
            return (f"The Treasury grows modestly. {sym}{total:+.2f} realized "
                    f"but win rate ({wr:.1f}%) needs improvement.")
        elif total > -50:
            return (f"The Treasury holds steady. {sym}{total:+.2f} realized. "
                    f"The King advises caution.")
        else:
            return (f"The Treasury bleeds. {sym}{total:+.2f} realized across "
                    f"{trades} trades. The King demands the Queen review strategy.")

    # ─────────────────────────────────────────────────────────
    # Autonomous Monitoring - The King Never Sleeps
    # ─────────────────────────────────────────────────────────

    def start_autonomous(self):
        """Start the King's autonomous monitoring loop.

        Honors AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS: under the flag (audits,
        tests) the King stays fully usable synchronously but no background
        thread is started. Live runs don't set the flag — unchanged behavior."""
        if self._running:
            return
        if os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").lower() in {"1", "true", "yes", "on"}:
            logger.debug("King autonomous thread suppressed (AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS)")
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._autonomous_loop, daemon=True, name="TheKing"
        )
        self._monitor_thread.start()
        logger.info("The King is now watching. Autonomous mode engaged.")

    def stop_autonomous(self):
        """Stop autonomous monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("The King rests. Autonomous mode disengaged.")

    def _autonomous_loop(self):
        """Background loop: periodic reconciliation and reporting."""
        last_reconcile = 0
        last_report = 0

        while self._running:
            try:
                now = time.time()

                # Periodic reconciliation
                if now - last_reconcile >= KING_CONFIG["RECONCILE_INTERVAL_SEC"]:
                    self._auto_reconcile()
                    last_reconcile = now

                # Periodic reporting
                if now - last_report >= KING_CONFIG["REPORT_INTERVAL_SEC"]:
                    self._auto_report()
                    last_report = now

                time.sleep(KING_CONFIG["MONITOR_INTERVAL_SEC"])
            except Exception as e:
                logger.error(f"King autonomous loop error: {e}")
                time.sleep(10)

    def _auto_reconcile(self):
        """Automatic reconciliation with exchanges."""
        try:
            from aureon.trading.unified_exchange_client import UnifiedExchangeClient
            for ex_name in ["kraken", "binance"]:
                try:
                    client = UnifiedExchangeClient(ex_name)
                    balances = client.get_all_balances()
                    if balances:
                        self.reconcile(ex_name, balances)
                except Exception as e:
                    logger.debug(f"King auto-reconcile {ex_name}: {e}")
        except ImportError:
            pass

    def _auto_report(self):
        """Automatic periodic report generation."""
        try:
            pnl = self.treasury.omega.get_summary()
            total = pnl.get("total_realized_pnl", 0)
            trades = pnl.get("total_trades", 0)
            wr = pnl.get("win_rate", 0)
            if trades > 0:
                logger.info(
                    f"[KING REPORT] Trades: {trades} | P&L: {total:+.2f} | "
                    f"Win Rate: {wr:.1f}% | Fees: {pnl.get('total_fees_paid', 0):.2f}"
                )
        except Exception as e:
            logger.debug(f"King auto-report error: {e}")

    # ─────────────────────────────────────────────────────────
    # Persistence - The King's Memory
    # ─────────────────────────────────────────────────────────

    def _save_state(self):
        """Save the King's state to disk."""
        try:
            state = {
                "saved_at": datetime.now().isoformat(),
                "transactions": [asdict(t) for t in self.treasury.sigma.transactions[-1000:]],
                "tax_lots": {
                    k: [asdict(lot) for lot in lots]
                    for k, lots in self.treasury.phi.tax_lots.items()
                    if lots
                },
                "realized_gains": [asdict(g) for g in self.treasury.phi.realized_gains[-500:]],
                "pnl_summary": self.treasury.omega.get_summary(),
                "audit_alerts": [asdict(a) for a in self.auditor.alerts[-100:]],
            }
            path = Path(KING_CONFIG["STATE_FILE"])
            path.write_text(json.dumps(state, indent=2, default=str))
        except Exception as e:
            logger.error(f"King save state error: {e}")

    def _load_state(self):
        """Restore the King's state from disk."""
        path = Path(KING_CONFIG["STATE_FILE"])
        if not path.exists():
            return

        try:
            state = json.loads(path.read_text())

            # Restore tax lots
            for key, lots_data in state.get("tax_lots", {}).items():
                for ld in lots_data:
                    lot = TaxLot(**{k: v for k, v in ld.items() if k in TaxLot.__dataclass_fields__})
                    self.treasury.phi.tax_lots[key].append(lot)

            # Restore realized gains
            for gd in state.get("realized_gains", []):
                gain = RealizedGain(**{k: v for k, v in gd.items() if k in RealizedGain.__dataclass_fields__})
                self.treasury.phi.realized_gains.append(gain)
                self.treasury.omega.record_realized(gain)

            # Restore counters
            self.treasury.sigma._tx_counter = len(state.get("transactions", []))
            self.treasury.phi._lot_counter = sum(
                len(lots) for lots in self.treasury.phi.tax_lots.values()
            )

            logger.info(
                f"King state restored: {len(self.treasury.phi.realized_gains)} gains, "
                f"{sum(len(v) for v in self.treasury.phi.tax_lots.values())} lots"
            )
        except Exception as e:
            logger.error(f"King load state error: {e}")

    def _audit_log(self, event_type: str, data: Dict):
        """Append to the audit log (JSONL)."""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "data": data,
            }
            with open(KING_CONFIG["AUDIT_LOG"], "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass  # Non-critical

    # ─────────────────────────────────────────────────────────
    # Royal Report Generation
    # ─────────────────────────────────────────────────────────

    def generate_daily_report(self) -> str:
        """Generate a human-readable daily financial report."""
        pnl = self.treasury.omega.get_summary()
        today = datetime.now().strftime("%Y-%m-%d")
        today_pnl = pnl["daily_pnl"].get(today, 0.0)
        sym = "£" if self.base_currency == "GBP" else "$"

        lines = [
            "=" * 60,
            "THE KING'S DAILY REPORT",
            f"Date: {today}",
            "=" * 60,
            "",
            f"Today's Realized P&L:  {sym}{today_pnl:+.2f}",
            f"Total Realized P&L:    {sym}{pnl['total_realized_pnl']:+.2f}",
            f"Total Fees Paid:       {sym}{pnl['total_fees_paid']:.2f}",
            f"Total Trades:          {pnl['total_trades']}",
            f"Win Rate:              {pnl['win_rate']:.1f}%",
            f"  Wins:                {pnl['wins']}",
            f"  Losses:              {pnl['losses']}",
            "",
        ]

        # Positions
        positions = self.treasury.phi.get_all_positions()
        if positions:
            lines.append(f"Open Positions ({len(positions)}):")
            lines.append("-" * 40)
            for key, pos in positions.items():
                lines.append(
                    f"  {key:25s} | Qty: {pos['quantity']:.8f} | "
                    f"Avg: {sym}{pos['avg_price']:.2f} | "
                    f"Cost: {sym}{pos['total_cost']:.2f}"
                )
        else:
            lines.append("No open positions.")

        # Audit
        audit = self.auditor.get_audit_summary()
        if audit["unresolved"] > 0:
            lines.extend([
                "",
                f"Audit Alerts: {audit['unresolved']} unresolved "
                f"({audit['critical']} critical, {audit['warnings']} warnings)",
            ])

        lines.extend([
            "",
            "=" * 60,
            self._get_royal_decree(pnl),
            "=" * 60,
        ])

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# ORDER FLOW VELOCITY TRACKER - The King's Speedometer
# ═══════════════════════════════════════════════════════════════════════════

class OrderFlowVelocity:
    """
    Tracks HOW FAST buys and sells are happening across all exchanges.
    This gives the King a sense of WHERE people are buying and WHY.

    Metrics tracked:
      - buy_velocity:  Rate of buy orders per minute
      - sell_velocity: Rate of sell orders per minute
      - pressure_ratio: buy_vel / (buy_vel + sell_vel) [0 = all sells, 1 = all buys]
      - acceleration:  Change in velocity over time (speeding up or slowing down)
      - flow_momentum: Weighted moving average of pressure ratio
      - surge_detected: True when velocity spikes above 2x average

    The King uses this to understand market participant intent:
      - High buy velocity + rising price = FOMO / strong demand
      - High sell velocity + falling price = panic / capitulation
      - High buy velocity + flat price = accumulation (smart money)
      - High sell velocity + flat price = distribution (insiders selling)
    """

    def __init__(self, window_sec: float = 300.0):
        self._window_sec = window_sec       # 5-minute rolling window
        self._buys: List[Tuple[float, float, str]] = []   # (timestamp, value_usd, exchange)
        self._sells: List[Tuple[float, float, str]] = []  # (timestamp, value_usd, exchange)
        self._velocity_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_buy(self, value_usd: float, exchange: str = ""):
        """Record a buy order happening NOW."""
        with self._lock:
            self._buys.append((time.time(), value_usd, exchange))
            self._prune()

    def record_sell(self, value_usd: float, exchange: str = ""):
        """Record a sell order happening NOW."""
        with self._lock:
            self._sells.append((time.time(), value_usd, exchange))
            self._prune()

    def _prune(self):
        """Remove entries older than the window."""
        cutoff = time.time() - self._window_sec
        self._buys = [(t, v, e) for t, v, e in self._buys if t > cutoff]
        self._sells = [(t, v, e) for t, v, e in self._sells if t > cutoff]

    def get_velocity_report(self) -> Dict[str, Any]:
        """
        Get the current order flow velocity report.
        Called by the Seer and other pillars to understand market flow.
        """
        with self._lock:
            self._prune()
            now = time.time()
            window_min = self._window_sec / 60.0

            # Count and value
            buy_count = len(self._buys)
            sell_count = len(self._sells)
            buy_value = sum(v for _, v, _ in self._buys)
            sell_value = sum(v for _, v, _ in self._sells)

            # Velocity (trades per minute)
            buy_velocity = buy_count / window_min if window_min > 0 else 0
            sell_velocity = sell_count / window_min if window_min > 0 else 0
            total_velocity = buy_velocity + sell_velocity

            # Value velocity (USD per minute)
            buy_value_velocity = buy_value / window_min if window_min > 0 else 0
            sell_value_velocity = sell_value / window_min if window_min > 0 else 0

            # Pressure ratio: 0 = all sells, 1 = all buys, 0.5 = balanced
            if total_velocity > 0:
                pressure_ratio = buy_velocity / total_velocity
            else:
                pressure_ratio = 0.5

            # Value-weighted pressure
            total_value = buy_value + sell_value
            if total_value > 0:
                value_pressure = buy_value / total_value
            else:
                value_pressure = 0.5

            # Time-weighted recency (more recent = more weight)
            buy_recency = self._calc_recency(self._buys, now)
            sell_recency = self._calc_recency(self._sells, now)

            # Acceleration: compare first half vs second half of window
            acceleration = self._calc_acceleration()

            # Exchange breakdown
            exchange_flow = self._exchange_breakdown()

            # Surge detection (velocity > 2x historical average)
            avg_velocity = 0
            if self._velocity_history:
                avg_velocity = sum(h.get("total_velocity", 0) for h in self._velocity_history[-20:]) / min(20, len(self._velocity_history))
            surge_detected = total_velocity > avg_velocity * 2.0 if avg_velocity > 0 else False

            # Flow momentum: EMA of pressure ratio
            flow_momentum = pressure_ratio
            if self._velocity_history:
                prev_momentum = self._velocity_history[-1].get("flow_momentum", 0.5)
                alpha = 0.3  # EMA smoothing
                flow_momentum = alpha * pressure_ratio + (1 - alpha) * prev_momentum

            # Market intent interpretation
            intent = self._interpret_intent(pressure_ratio, total_velocity, acceleration)

            report = {
                "timestamp": now,
                "buy_velocity": round(buy_velocity, 3),
                "sell_velocity": round(sell_velocity, 3),
                "total_velocity": round(total_velocity, 3),
                "buy_value_velocity": round(buy_value_velocity, 2),
                "sell_value_velocity": round(sell_value_velocity, 2),
                "pressure_ratio": round(pressure_ratio, 4),
                "value_pressure": round(value_pressure, 4),
                "acceleration": round(acceleration, 4),
                "flow_momentum": round(flow_momentum, 4),
                "surge_detected": surge_detected,
                "buy_recency": round(buy_recency, 3),
                "sell_recency": round(sell_recency, 3),
                "exchange_flow": exchange_flow,
                "intent": intent,
                "buy_count": buy_count,
                "sell_count": sell_count,
                "window_sec": self._window_sec,
            }

            # Store in history
            self._velocity_history.append(report)
            if len(self._velocity_history) > 100:
                self._velocity_history = self._velocity_history[-100:]

            return report

    def _calc_recency(self, trades: List[Tuple[float, float, str]], now: float) -> float:
        """Calculate how recent the trades are (1.0 = very recent, 0.0 = old)."""
        if not trades:
            return 0.0
        recencies = []
        for t, _, _ in trades:
            age = now - t
            recency = max(0, 1.0 - (age / self._window_sec))
            recencies.append(recency)
        return sum(recencies) / len(recencies)

    def _calc_acceleration(self) -> float:
        """Acceleration: is trading speeding up or slowing down?"""
        if len(self._velocity_history) < 2:
            return 0.0
        prev = self._velocity_history[-1].get("total_velocity", 0) if self._velocity_history else 0
        # Compare current window halves
        now = time.time()
        mid = now - self._window_sec / 2
        recent_buys = sum(1 for t, _, _ in self._buys if t > mid)
        recent_sells = sum(1 for t, _, _ in self._sells if t > mid)
        older_buys = sum(1 for t, _, _ in self._buys if t <= mid)
        older_sells = sum(1 for t, _, _ in self._sells if t <= mid)
        recent_total = recent_buys + recent_sells
        older_total = older_buys + older_sells
        if older_total > 0:
            return (recent_total - older_total) / older_total
        return 0.0

    def _exchange_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Break down flow by exchange."""
        exchanges: Dict[str, Dict[str, float]] = {}
        for _, v, e in self._buys:
            if e not in exchanges:
                exchanges[e] = {"buys": 0, "sells": 0, "buy_value": 0, "sell_value": 0}
            exchanges[e]["buys"] += 1
            exchanges[e]["buy_value"] += v
        for _, v, e in self._sells:
            if e not in exchanges:
                exchanges[e] = {"buys": 0, "sells": 0, "buy_value": 0, "sell_value": 0}
            exchanges[e]["sells"] += 1
            exchanges[e]["sell_value"] += v
        return exchanges

    def _interpret_intent(self, pressure: float, velocity: float,
                          acceleration: float) -> str:
        """Interpret what the order flow means about market participants."""
        if velocity < 0.1:
            return "QUIET"  # No significant activity
        if pressure > 0.70:
            if acceleration > 0.3:
                return "FOMO_BUYING"       # Aggressive buy acceleration
            else:
                return "ACCUMULATION"      # Steady buying
        elif pressure < 0.30:
            if acceleration > 0.3:
                return "PANIC_SELLING"     # Sell acceleration
            else:
                return "DISTRIBUTION"      # Steady selling
        elif pressure > 0.55:
            return "MILD_BUY_PRESSURE"
        elif pressure < 0.45:
            return "MILD_SELL_PRESSURE"
        else:
            return "BALANCED"


# Global Order Flow Velocity singleton
_order_flow_velocity: Optional[OrderFlowVelocity] = None


def get_order_flow_velocity() -> OrderFlowVelocity:
    """Get the singleton OrderFlowVelocity tracker."""
    global _order_flow_velocity
    if _order_flow_velocity is None:
        _order_flow_velocity = OrderFlowVelocity()
    return _order_flow_velocity


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON - The King is One
# ═══════════════════════════════════════════════════════════════════════════

_king_instance: Optional[TheKing] = None


def get_king() -> TheKing:
    """Get the singleton King instance."""
    global _king_instance
    if _king_instance is None:
        _king_instance = TheKing()
    return _king_instance
