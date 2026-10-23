#!/usr/bin/env python3
"""
THE KING'S LEDGER - Double-Entry Accounting System
=====================================================
"Every coin has two sides. Every transaction, two entries."

Proper double-entry bookkeeping for the Aureon trading ecosystem.
Every financial event creates balanced debit and credit journal entries.

ACCOUNT STRUCTURE (Chart of Accounts):
─────────────────────────────────────────
ASSETS (Debit-normal)
  1000  Cash            - Fiat currency balances
  1100  Crypto Holdings - Cryptocurrency at cost basis
  1200  Margin Deposits - Collateral posted for margin trades
  1300  Receivables     - Pending settlements

LIABILITIES (Credit-normal)
  2000  Margin Loans    - Borrowed funds for leveraged trades
  2100  Payables        - Pending fees, taxes owed

EQUITY (Credit-normal)
  3000  Opening Capital - Initial deposits
  3100  Retained P&L    - Accumulated profits/losses

REVENUE (Credit-normal)
  4000  Trading Gains   - Realized trading profits
  4100  Staking Rewards - Staking/yield income
  4200  Other Income    - Dividends, airdrops

EXPENSES (Debit-normal)
  5000  Trading Losses  - Realized trading losses
  5100  Exchange Fees   - Transaction fees
  5200  Margin Interest - Interest on margin loans
  5300  Withdrawal Fees - Network/withdrawal fees
  5400  Slippage        - Price slippage costs

Gary Leckey | February 2026
"The King's books are always balanced."
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CHART OF ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════

class AccountCode(Enum):
    # ASSETS (1xxx) - Debit increases, Credit decreases
    CASH = "1000"
    CASH_KRAKEN = "1001"
    CASH_BINANCE = "1002"
    CASH_ALPACA = "1003"
    CASH_CAPITAL = "1004"
    CRYPTO_HOLDINGS = "1100"
    MARGIN_DEPOSITS = "1200"
    RECEIVABLES = "1300"

    # LIABILITIES (2xxx) - Credit increases, Debit decreases
    MARGIN_LOANS = "2000"
    PAYABLES = "2100"

    # EQUITY (3xxx) - Credit increases, Debit decreases
    OPENING_CAPITAL = "3000"
    RETAINED_PNL = "3100"

    # REVENUE (4xxx) - Credit increases, Debit decreases
    TRADING_GAINS = "4000"
    STAKING_REWARDS = "4100"
    OTHER_INCOME = "4200"

    # EXPENSES (5xxx) - Debit increases, Credit decreases
    TRADING_LOSSES = "5000"
    EXCHANGE_FEES = "5100"
    MARGIN_INTEREST = "5200"
    WITHDRAWAL_FEES = "5300"
    SLIPPAGE_COST = "5400"


# Which accounts increase with debits vs credits
DEBIT_NORMAL = {"1", "5"}   # Assets, Expenses
CREDIT_NORMAL = {"2", "3", "4"}  # Liabilities, Equity, Revenue

EXCHANGE_CASH_ACCOUNTS = {
    "kraken": AccountCode.CASH_KRAKEN,
    "binance": AccountCode.CASH_BINANCE,
    "alpaca": AccountCode.CASH_ALPACA,
    "capital": AccountCode.CASH_CAPITAL,
}

LEDGER_FILE = "king_double_entry_ledger.json"


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class JournalLine:
    """A single line in a journal entry (one debit or credit)."""
    account_code: str         # AccountCode value
    account_name: str         # Human-readable name
    debit: float = 0.0       # Debit amount
    credit: float = 0.0      # Credit amount
    asset: str = ""           # Specific asset (e.g., BTC, ETH)
    exchange: str = ""        # Exchange name
    memo: str = ""            # Line-level memo


@dataclass
class JournalEntry:
    """A complete journal entry with balanced debits and credits."""
    id: str
    timestamp: float
    date: str                 # Human-readable date
    description: str          # What happened
    lines: List[JournalLine] = field(default_factory=list)
    reference: str = ""       # External reference (order_id, tx_id)
    is_posted: bool = True    # Whether this entry is finalized

    @property
    def total_debits(self) -> float:
        return sum(line.debit for line in self.lines)

    @property
    def total_credits(self) -> float:
        return sum(line.credit for line in self.lines)

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debits - self.total_credits) < 0.000001


# ═══════════════════════════════════════════════════════════════════════════
# THE KING'S LEDGER
# ═══════════════════════════════════════════════════════════════════════════

class KingLedger:
    """
    Double-entry accounting ledger for the Aureon trading ecosystem.

    Every transaction creates balanced journal entries (debits = credits).
    This ensures the books are always in balance and provides a complete
    audit trail of every financial event.

    Usage:
        ledger = get_ledger()

        # Record a crypto purchase
        ledger.record_buy('kraken', 'BTC', 0.001, 95000.0, fee=0.25, order_id='ABC123')

        # Record a crypto sale
        ledger.record_sell('kraken', 'BTC', 0.001, 96000.0, cost_basis=95.25, fee=0.25)

        # Check balance
        print(ledger.trial_balance())
    """

    def __init__(self):
        self.journal: List[JournalEntry] = []
        self.account_balances: Dict[str, float] = defaultdict(float)
        self._entry_counter = 0
        self._load()

    def _next_id(self) -> str:
        self._entry_counter += 1
        return f"JE-{int(time.time())}-{self._entry_counter:06d}"

    # ─────────────────────────────────────────────────────────
    # Journal Entry Creation
    # ─────────────────────────────────────────────────────────

    def _post_entry(self, entry: JournalEntry):
        """Validate and post a journal entry."""
        if not entry.is_balanced:
            diff = abs(entry.total_debits - entry.total_credits)
            logger.error(
                f"UNBALANCED ENTRY {entry.id} (off by {diff:.8f}): "
                f"debits={entry.total_debits:.8f} credits={entry.total_credits:.8f} "
                f"desc='{entry.description}'"
            )
            # Log each line for debugging
            for i, line in enumerate(entry.lines):
                logger.error(
                    f"  Line {i}: {line.account_name} "
                    f"DR={line.debit:.8f} CR={line.credit:.8f} "
                    f"({line.memo})"
                )
            return

        # Update account balances
        for line in entry.lines:
            code = line.account_code
            # Determine if this account is debit-normal or credit-normal
            is_debit_normal = code[0] in DEBIT_NORMAL

            if is_debit_normal:
                self.account_balances[code] += line.debit - line.credit
            else:
                self.account_balances[code] += line.credit - line.debit

        self.journal.append(entry)

    # ─────────────────────────────────────────────────────────
    # Transaction Recording Methods
    # ─────────────────────────────────────────────────────────

    def record_deposit(self, exchange: str, asset: str, amount: float,
                       reference: str = "") -> JournalEntry:
        """
        Record a fiat/crypto deposit.
        DR  Cash (exchange)     amount
          CR  Opening Capital   amount
        """
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)

        entry = JournalEntry(
            id=self._next_id(),
            timestamp=time.time(),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=f"Deposit {amount:.8f} {asset} to {exchange}",
            reference=reference,
            lines=[
                JournalLine(
                    account_code=cash_acct.value,
                    account_name=f"Cash ({exchange})",
                    debit=amount, asset=asset, exchange=exchange,
                ),
                JournalLine(
                    account_code=AccountCode.OPENING_CAPITAL.value,
                    account_name="Opening Capital",
                    credit=amount, asset=asset,
                ),
            ],
        )
        self._post_entry(entry)
        self._save()
        return entry

    def record_buy(self, exchange: str, asset: str, quantity: float,
                   price: float, fee: float = 0.0,
                   order_id: str = "",
                   ts: float = None) -> JournalEntry:
        """
        Record a crypto purchase.
        DR  Crypto Holdings    (quantity * price)
        DR  Exchange Fees      fee
          CR  Cash (exchange)  (quantity * price + fee)

        Args:
            ts: Optional historical timestamp (epoch). If None, uses current time.
        """
        total_cost = quantity * price
        total_outflow = total_cost + fee
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)

        lines = [
            JournalLine(
                account_code=AccountCode.CRYPTO_HOLDINGS.value,
                account_name="Crypto Holdings",
                debit=total_cost, asset=asset, exchange=exchange,
                memo=f"Buy {quantity:.8f} {asset} @ {price:.2f}",
            ),
            JournalLine(
                account_code=cash_acct.value,
                account_name=f"Cash ({exchange})",
                credit=total_outflow, asset=asset, exchange=exchange,
            ),
        ]
        if fee > 0:
            lines.insert(1, JournalLine(
                account_code=AccountCode.EXCHANGE_FEES.value,
                account_name="Exchange Fees",
                debit=fee, exchange=exchange,
                memo=f"Fee on buy {asset}",
            ))

        _ts = ts or time.time()
        _dt = datetime.fromtimestamp(_ts).strftime("%Y-%m-%d %H:%M:%S")
        entry = JournalEntry(
            id=self._next_id(),
            timestamp=_ts,
            date=_dt,
            description=f"Buy {quantity:.8f} {asset} @ {price:.2f} on {exchange}",
            reference=order_id,
            lines=lines,
        )
        self._post_entry(entry)
        self._save()
        return entry

    def record_sell(self, exchange: str, asset: str, quantity: float,
                    price: float, cost_basis: float, fee: float = 0.0,
                    order_id: str = "",
                    ts: float = None) -> JournalEntry:
        """
        Record a crypto sale with realized gain/loss.

        The fee is recorded as a SEPARATE expense line (DR Exchange Fees).
        Therefore the gain/loss line uses GROSS P&L (proceeds - cost_basis),
        NOT net P&L. This keeps debits = credits:

        DR  Cash (exchange)     (proceeds - fee)   money we actually receive
        DR  Exchange Fees       fee                 fee is an expense
          CR  Crypto Holdings   cost_basis          remove asset at FIFO cost
          CR  Trading Gains     (proceeds - cost_basis)  gross gain
        -- OR --
        DR  Trading Losses      (cost_basis - proceeds)  gross loss

        Proof of balance:
          Total DR = (proceeds - fee) + fee [+ loss if any] = proceeds [+ loss]
          Total CR = cost_basis + (proceeds - cost_basis) [if gain] = proceeds
          Balanced ✓
        """
        proceeds = quantity * price
        net_proceeds = proceeds - fee
        # CRITICAL: Use GROSS P&L for the journal entry.
        # The fee is tracked separately as an Exchange Fees debit.
        # Using (proceeds - cost_basis - fee) here would double-count the fee
        # and create an unbalanced entry that gets silently dropped!
        gross_pnl = proceeds - cost_basis
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)

        lines = [
            JournalLine(
                account_code=cash_acct.value,
                account_name=f"Cash ({exchange})",
                debit=net_proceeds, asset=asset, exchange=exchange,
            ),
            JournalLine(
                account_code=AccountCode.CRYPTO_HOLDINGS.value,
                account_name="Crypto Holdings",
                credit=cost_basis, asset=asset, exchange=exchange,
                memo=f"Sell {quantity:.8f} {asset} @ {price:.2f}",
            ),
        ]

        if fee > 0:
            lines.append(JournalLine(
                account_code=AccountCode.EXCHANGE_FEES.value,
                account_name="Exchange Fees",
                debit=fee, exchange=exchange,
                memo=f"Fee on sell {asset}",
            ))

        if gross_pnl >= 0:
            lines.append(JournalLine(
                account_code=AccountCode.TRADING_GAINS.value,
                account_name="Trading Gains",
                credit=gross_pnl, asset=asset,
                memo=f"Realized gain on {asset}",
            ))
        else:
            lines.append(JournalLine(
                account_code=AccountCode.TRADING_LOSSES.value,
                account_name="Trading Losses",
                debit=abs(gross_pnl), asset=asset,
                memo=f"Realized loss on {asset}",
            ))

        # Net P&L (after fees) for the description only
        net_pnl = gross_pnl - fee

        _ts = ts or time.time()
        _dt = datetime.fromtimestamp(_ts).strftime("%Y-%m-%d %H:%M:%S")
        entry = JournalEntry(
            id=self._next_id(),
            timestamp=_ts,
            date=_dt,
            description=f"Sell {quantity:.8f} {asset} @ {price:.2f} on {exchange} (gross: {gross_pnl:+.4f}, net: {net_pnl:+.4f})",
            reference=order_id,
            lines=lines,
        )
        self._post_entry(entry)
        self._save()
        return entry

    def record_margin_open(self, exchange: str, asset: str, quantity: float,
                           price: float, leverage: int, margin_amount: float,
                           fee: float = 0.0, order_id: str = "") -> JournalEntry:
        """
        Record opening a margin position.
        DR  Crypto Holdings     (notional = quantity * price)
        DR  Exchange Fees       fee
          CR  Margin Deposits   margin_amount (collateral)
          CR  Margin Loans      (notional - margin_amount) (borrowed)
          CR  Cash (exchange)   fee
        """
        notional = quantity * price
        borrowed = notional - margin_amount
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)

        lines = [
            JournalLine(
                account_code=AccountCode.CRYPTO_HOLDINGS.value,
                account_name="Crypto Holdings (Margin)",
                debit=notional, asset=asset, exchange=exchange,
                memo=f"Margin long {quantity:.8f} {asset} @ {price:.2f} ({leverage}x)",
            ),
            JournalLine(
                account_code=AccountCode.MARGIN_DEPOSITS.value,
                account_name="Margin Deposits",
                credit=margin_amount, exchange=exchange,
                memo=f"Collateral for {asset} margin position",
            ),
            JournalLine(
                account_code=AccountCode.MARGIN_LOANS.value,
                account_name="Margin Loans",
                credit=borrowed, exchange=exchange,
                memo=f"Borrowed {borrowed:.2f} for {leverage}x leverage",
            ),
        ]

        if fee > 0:
            lines.append(JournalLine(
                account_code=AccountCode.EXCHANGE_FEES.value,
                account_name="Exchange Fees",
                debit=fee, exchange=exchange,
            ))
            lines.append(JournalLine(
                account_code=cash_acct.value,
                account_name=f"Cash ({exchange})",
                credit=fee, exchange=exchange,
            ))

        entry = JournalEntry(
            id=self._next_id(),
            timestamp=time.time(),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=(
                f"Open margin long {quantity:.8f} {asset} @ {price:.2f} "
                f"({leverage}x, margin={margin_amount:.2f}) on {exchange}"
            ),
            reference=order_id,
            lines=lines,
        )
        self._post_entry(entry)
        self._save()
        return entry

    def record_margin_close(self, exchange: str, asset: str, quantity: float,
                            price: float, cost_basis: float, margin_amount: float,
                            borrowed: float, fee: float = 0.0,
                            order_id: str = "") -> JournalEntry:
        """
        Record closing a margin position.

        Uses GROSS P&L (proceeds - cost_basis) for the gain/loss line,
        with fees tracked separately, same as record_sell.

        DR  Margin Deposits     margin_amount  (reclaim collateral)
        DR  Margin Loans        borrowed       (repay loan)
        DR  Cash (exchange)     proceeds - borrowed - fee  (net cash received)
        DR  Exchange Fees       fee
          CR  Crypto Holdings   cost_basis     (remove position at FIFO cost)
          CR  Trading Gains     gross_pnl      (if profitable)
        -- OR --
        DR  Trading Losses      abs(gross_pnl) (if loss)
        """
        proceeds = quantity * price
        # CRITICAL: Use GROSS P&L — fee is tracked separately
        gross_pnl = proceeds - cost_basis
        net_pnl = gross_pnl - fee
        # Cash user actually receives: proceeds minus loan repayment minus fee
        cash_received = proceeds - borrowed - fee
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)

        lines = [
            JournalLine(
                account_code=AccountCode.MARGIN_DEPOSITS.value,
                account_name="Margin Deposits",
                debit=margin_amount, exchange=exchange,
                memo="Return collateral",
            ),
            JournalLine(
                account_code=AccountCode.MARGIN_LOANS.value,
                account_name="Margin Loans",
                debit=borrowed, exchange=exchange,
                memo="Repay margin loan",
            ),
            JournalLine(
                account_code=AccountCode.CRYPTO_HOLDINGS.value,
                account_name="Crypto Holdings (Margin)",
                credit=cost_basis, asset=asset, exchange=exchange,
            ),
        ]

        # Cash received (may be zero or negative if loss exceeds collateral)
        if cash_received > 0:
            lines.append(JournalLine(
                account_code=cash_acct.value,
                account_name=f"Cash ({exchange})",
                debit=cash_received,
                exchange=exchange,
                memo="Margin close proceeds",
            ))
        elif cash_received < 0:
            # Margin call / loss exceeded collateral
            lines.append(JournalLine(
                account_code=cash_acct.value,
                account_name=f"Cash ({exchange})",
                credit=abs(cash_received),
                exchange=exchange,
                memo="Margin close deficit (loss > collateral)",
            ))

        if fee > 0:
            lines.append(JournalLine(
                account_code=AccountCode.EXCHANGE_FEES.value,
                account_name="Exchange Fees",
                debit=fee, exchange=exchange,
                memo=f"Fee on margin close {asset}",
            ))

        if gross_pnl >= 0:
            lines.append(JournalLine(
                account_code=AccountCode.TRADING_GAINS.value,
                account_name="Trading Gains (Margin)",
                credit=gross_pnl, asset=asset,
                memo=f"Realized margin gain on {asset}",
            ))
        else:
            lines.append(JournalLine(
                account_code=AccountCode.TRADING_LOSSES.value,
                account_name="Trading Losses (Margin)",
                debit=abs(gross_pnl), asset=asset,
                memo=f"Realized margin loss on {asset}",
            ))

        # Safety check: verify balance before posting
        total_dr = sum(l.debit for l in lines)
        total_cr = sum(l.credit for l in lines)
        diff = abs(total_dr - total_cr)
        if diff > 0.000001:
            logger.warning(
                f"Margin close entry off by {diff:.8f} — adding balancing line. "
                f"DR={total_dr:.8f} CR={total_cr:.8f}"
            )
            if total_dr > total_cr:
                lines.append(JournalLine(
                    account_code=AccountCode.RETAINED_PNL.value,
                    account_name="Retained P&L (Balancing)",
                    credit=total_dr - total_cr,
                ))
            else:
                lines.append(JournalLine(
                    account_code=AccountCode.RETAINED_PNL.value,
                    account_name="Retained P&L (Balancing)",
                    debit=total_cr - total_dr,
                ))

        entry = JournalEntry(
            id=self._next_id(),
            timestamp=time.time(),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=(
                f"Close margin {asset} on {exchange} "
                f"(gross: {gross_pnl:+.4f}, net: {net_pnl:+.4f})"
            ),
            reference=order_id,
            lines=lines,
        )
        self._post_entry(entry)
        self._save()
        return entry

    def record_withdrawal(self, exchange: str, asset: str, amount: float,
                          fee: float = 0.0, reference: str = "") -> JournalEntry:
        """
        Record a withdrawal.
        DR  [External - reduces equity]
          CR  Cash (exchange)         amount
          DR  Withdrawal Fees         fee (if any)
        """
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)

        lines = [
            JournalLine(
                account_code=AccountCode.RETAINED_PNL.value,
                account_name="Retained P&L (Withdrawal)",
                debit=amount, asset=asset,
            ),
            JournalLine(
                account_code=cash_acct.value,
                account_name=f"Cash ({exchange})",
                credit=amount + fee, asset=asset, exchange=exchange,
            ),
        ]

        if fee > 0:
            lines.append(JournalLine(
                account_code=AccountCode.WITHDRAWAL_FEES.value,
                account_name="Withdrawal Fees",
                debit=fee, exchange=exchange,
            ))

        entry = JournalEntry(
            id=self._next_id(),
            timestamp=time.time(),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=f"Withdraw {amount:.8f} {asset} from {exchange}",
            reference=reference,
            lines=lines,
        )
        self._post_entry(entry)
        self._save()
        return entry

    def record_fee(self, exchange: str, amount: float,
                   reason: str = "trading fee") -> JournalEntry:
        """
        Record a standalone fee.
        DR  Exchange Fees / Margin Interest    amount
          CR  Cash (exchange)                  amount
        """
        cash_acct = EXCHANGE_CASH_ACCOUNTS.get(exchange, AccountCode.CASH)
        is_margin = "margin" in reason.lower()
        fee_acct = AccountCode.MARGIN_INTEREST if is_margin else AccountCode.EXCHANGE_FEES

        entry = JournalEntry(
            id=self._next_id(),
            timestamp=time.time(),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=f"Fee: {reason} on {exchange} ({amount:.4f})",
            lines=[
                JournalLine(
                    account_code=fee_acct.value,
                    account_name=fee_acct.name.replace("_", " ").title(),
                    debit=amount, exchange=exchange, memo=reason,
                ),
                JournalLine(
                    account_code=cash_acct.value,
                    account_name=f"Cash ({exchange})",
                    credit=amount, exchange=exchange,
                ),
            ],
        )
        self._post_entry(entry)
        self._save()
        return entry

    # ─────────────────────────────────────────────────────────
    # Financial Statements
    # ─────────────────────────────────────────────────────────

    def trial_balance(self) -> Dict[str, Any]:
        """
        Generate a trial balance. Total debits must equal total credits.
        """
        accounts = {}
        total_debit = 0.0
        total_credit = 0.0

        for code, balance in sorted(self.account_balances.items()):
            if abs(balance) < 0.000001:
                continue
            is_debit_normal = code[0] in DEBIT_NORMAL

            if is_debit_normal:
                dr = balance if balance > 0 else 0.0
                cr = abs(balance) if balance < 0 else 0.0
            else:
                cr = balance if balance > 0 else 0.0
                dr = abs(balance) if balance < 0 else 0.0

            name = self._account_name(code)
            accounts[code] = {"name": name, "debit": dr, "credit": cr}
            total_debit += dr
            total_credit += cr

        balanced = abs(total_debit - total_credit) < 0.01

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "accounts": accounts,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "is_balanced": balanced,
            "difference": total_debit - total_credit,
        }

    def balance_sheet(self) -> Dict[str, Any]:
        """Generate a balance sheet (Assets = Liabilities + Equity)."""
        assets = {}
        liabilities = {}
        equity = {}

        for code, balance in self.account_balances.items():
            if abs(balance) < 0.000001:
                continue
            name = self._account_name(code)
            if code.startswith("1"):
                assets[name] = balance
            elif code.startswith("2"):
                liabilities[name] = balance
            elif code.startswith("3"):
                equity[name] = balance

        # Revenue and expenses roll into retained P&L
        revenue = sum(v for k, v in self.account_balances.items() if k.startswith("4"))
        expenses = sum(v for k, v in self.account_balances.items() if k.startswith("5"))
        net_income = revenue - expenses

        total_assets = sum(assets.values())
        total_liabilities = sum(liabilities.values())
        total_equity = sum(equity.values()) + net_income

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "assets": assets,
            "total_assets": total_assets,
            "liabilities": liabilities,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "net_income": net_income,
            "total_equity": total_equity,
            "accounting_equation_balanced": abs(total_assets - total_liabilities - total_equity) < 0.01,
        }

    def income_statement(self, since: float = None) -> Dict[str, Any]:
        """Generate an income statement (Revenue - Expenses = Net Income)."""
        revenue_items = {}
        expense_items = {}

        # Filter journal entries by date if needed
        entries = self.journal
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        for entry in entries:
            for line in entry.lines:
                name = self._account_name(line.account_code)
                if line.account_code.startswith("4"):
                    revenue_items[name] = revenue_items.get(name, 0.0) + line.credit - line.debit
                elif line.account_code.startswith("5"):
                    expense_items[name] = expense_items.get(name, 0.0) + line.debit - line.credit

        total_revenue = sum(revenue_items.values())
        total_expenses = sum(expense_items.values())
        net_income = total_revenue - total_expenses

        return {
            "period": f"Since {datetime.fromtimestamp(since).strftime('%Y-%m-%d')}" if since else "All time",
            "revenue": revenue_items,
            "total_revenue": total_revenue,
            "expenses": expense_items,
            "total_expenses": total_expenses,
            "net_income": net_income,
        }

    def get_account_history(self, account_code: str,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a specific account."""
        history = []
        for entry in reversed(self.journal):
            for line in entry.lines:
                if line.account_code == account_code:
                    history.append({
                        "date": entry.date,
                        "description": entry.description,
                        "debit": line.debit,
                        "credit": line.credit,
                        "memo": line.memo,
                        "reference": entry.reference,
                    })
                    if len(history) >= limit:
                        return history
        return history

    def _account_name(self, code: str) -> str:
        """Get human-readable account name from code."""
        for ac in AccountCode:
            if ac.value == code:
                return ac.name.replace("_", " ").title()
        return f"Account {code}"

    # ─────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────

    def _save(self):
        """Save ledger to disk."""
        try:
            data = {
                "saved_at": datetime.now().isoformat(),
                "entry_counter": self._entry_counter,
                "account_balances": dict(self.account_balances),
                "journal_entries": [
                    {
                        "id": e.id,
                        "timestamp": e.timestamp,
                        "date": e.date,
                        "description": e.description,
                        "reference": e.reference,
                        "lines": [
                            {
                                "account_code": l.account_code,
                                "account_name": l.account_name,
                                "debit": l.debit,
                                "credit": l.credit,
                                "asset": l.asset,
                                "exchange": l.exchange,
                                "memo": l.memo,
                            }
                            for l in e.lines
                        ],
                    }
                    for e in self.journal[-2000:]  # Keep last 2000 entries
                ],
            }
            Path(LEDGER_FILE).write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"King Ledger save error: {e}")

    def _load(self):
        """Load ledger from disk."""
        path = Path(LEDGER_FILE)
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())
            self._entry_counter = data.get("entry_counter", 0)
            self.account_balances = defaultdict(float, data.get("account_balances", {}))

            for je_data in data.get("journal_entries", []):
                lines = [
                    JournalLine(
                        account_code=l["account_code"],
                        account_name=l.get("account_name", ""),
                        debit=l.get("debit", 0.0),
                        credit=l.get("credit", 0.0),
                        asset=l.get("asset", ""),
                        exchange=l.get("exchange", ""),
                        memo=l.get("memo", ""),
                    )
                    for l in je_data.get("lines", [])
                ]
                entry = JournalEntry(
                    id=je_data["id"],
                    timestamp=je_data["timestamp"],
                    date=je_data["date"],
                    description=je_data["description"],
                    reference=je_data.get("reference", ""),
                    lines=lines,
                )
                self.journal.append(entry)

            logger.info(
                f"King Ledger loaded: {len(self.journal)} journal entries, "
                f"{len(self.account_balances)} accounts"
            )
        except Exception as e:
            logger.error(f"King Ledger load error: {e}")

    # ─────────────────────────────────────────────────────────
    # Report Generation
    # ─────────────────────────────────────────────────────────

    def print_trial_balance(self) -> str:
        """Generate a human-readable trial balance."""
        tb = self.trial_balance()
        lines = [
            "=" * 65,
            "THE KING'S TRIAL BALANCE",
            f"Date: {tb['date']}",
            "=" * 65,
            f"{'Account':<30s} {'Debit':>15s} {'Credit':>15s}",
            "-" * 65,
        ]

        for code, acct in tb["accounts"].items():
            dr = f"{acct['debit']:.2f}" if acct["debit"] > 0 else ""
            cr = f"{acct['credit']:.2f}" if acct["credit"] > 0 else ""
            lines.append(f"{acct['name']:<30s} {dr:>15s} {cr:>15s}")

        lines.extend([
            "-" * 65,
            f"{'TOTALS':<30s} {tb['total_debit']:>15.2f} {tb['total_credit']:>15.2f}",
            "=" * 65,
            f"Balanced: {'YES' if tb['is_balanced'] else 'NO (INVESTIGATE!)'}",
        ])

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_ledger_instance: Optional[KingLedger] = None


def get_ledger() -> KingLedger:
    """Get the singleton KingLedger instance."""
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = KingLedger()
    return _ledger_instance
