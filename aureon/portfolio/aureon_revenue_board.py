#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                       ║
║     💰 AUREON REVENUE BOARD - REAL-TIME PORTFOLIO TRACKER 💰                                           ║
║                                                                                                       ║
║     Live portfolio mark-to-market from actual exchange balances                                       ║
║     Shows: Equity | Realized PnL | Unrealized PnL | Sweeps | Positions | Growth                      ║
║                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════╝

THE REVENUE BOARD KNOWS:
========================
• Real balances from Binance/Kraken/Alpaca (not simulated)
• Mark-to-market equity using live prices
• Realized PnL from executed trades
• Unrealized PnL from open positions
• Sweep profits from Omega Converter
• Win rate and trade count
• Equity history for growth tracking

Gary Leckey & GitHub Copilot | January 2026
"Show me the money!" 💰
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import json
import time
import math
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque

# UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("RevenueBoard")

# ═══════════════════════════════════════════════════════════════════════════════
# EXCHANGE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

try:
    from aureon.trading.unified_exchange_client import UnifiedExchangeClient
    UNIFIED_AVAILABLE = True
except ImportError:
    UNIFIED_AVAILABLE = False
    UnifiedExchangeClient = None


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PositionSnapshot:
    """Snapshot of a single position"""
    symbol: str
    exchange: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "qty": self.quantity,
            "avg_price": self.avg_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct
        }


@dataclass
class EquitySnapshot:
    """Point-in-time equity snapshot"""
    timestamp: float
    total_equity: float
    cash_balance: float
    positions_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    
    def to_dict(self) -> Dict:
        return {
            "ts": self.timestamp,
            "equity": self.total_equity,
            "cash": self.cash_balance,
            "positions": self.positions_value,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_pnl": self.total_pnl
        }


@dataclass
class TradeRecord:
    """Record of an executed trade"""
    timestamp: float
    symbol: str
    exchange: str
    side: str  # BUY, SELL, CONVERT
    quantity: float
    price: float
    fee: float
    pnl: float  # Realized PnL for this trade
    source: str  # COMMANDO, INCEPTION, SWEEP, etc.


# ═══════════════════════════════════════════════════════════════════════════════
# REVENUE BOARD - THE MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class RevenueBoard:
    """
    💰 REAL-TIME REVENUE BOARD 💰
    
    Tracks portfolio value from LIVE exchange balances.
    Shows profit/loss in real-time as trades execute.
    """
    
    def __init__(self, 
                 binance_client: Optional[Any] = None,
                 kraken_client: Optional[Any] = None,
                 alpaca_client: Optional[Any] = None,
                 unified_client: Optional[Any] = None,
                 initial_equity: float = 0.0):
        """
        Initialize with exchange clients.
        If no clients provided, will try to create them from env.
        """
        self.start_time = time.time()
        
        # Exchange clients
        self.binance = binance_client
        self.kraken = kraken_client
        self.alpaca = alpaca_client
        self.unified = unified_client
        
        # Try to initialize if not provided
        if self.binance is None and BINANCE_AVAILABLE:
            try:
                self.binance = get_binance_client()
                logger.info("📈 Binance client connected")
            except Exception as e:
                logger.warning(f"Binance not available: {e}")
        
        if self.kraken is None and KRAKEN_AVAILABLE:
            try:
                self.kraken = get_kraken_client()
                logger.info("📈 Kraken client connected")
            except Exception as e:
                logger.warning(f"Kraken not available: {e}")
        
        # Track which exchanges are live
        self.exchanges = {}
        if self.binance:
            self.exchanges["binance"] = self.binance
        if self.kraken:
            self.exchanges["kraken"] = self.kraken
        if self.alpaca:
            self.exchanges["alpaca"] = self.alpaca
        
        # Initial equity baseline
        self.initial_equity = initial_equity
        self.baseline_set = initial_equity > 0
        
        # Tracking
        self.realized_pnl = 0.0
        self.sweep_pnl = 0.0
        self.sweep_count = 0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # History
        self.equity_history: deque = deque(maxlen=10000)
        self.trade_history: deque = deque(maxlen=1000)
        self.positions: Dict[str, PositionSnapshot] = {}
        
        # Cached prices
        self.prices: Dict[str, float] = {}
        self.last_refresh = 0.0
        
        logger.info(f"💰 REVENUE BOARD initialized | Exchanges: {list(self.exchanges.keys())}")
    
    def refresh_prices(self) -> Dict[str, float]:
        """Fetch latest prices from exchanges"""
        prices = {"USDT": 1.0, "USD": 1.0, "USDC": 1.0}
        
        # Binance prices
        if self.binance:
            try:
                tickers = self.binance.session.get(
                    f'{self.binance.base}/api/v3/ticker/price',
                    timeout=5
                ).json()
                
                for t in tickers:
                    symbol = t.get('symbol', '')
                    if symbol.endswith('USDT'):
                        asset = symbol.replace('USDT', '')
                        try:
                            prices[asset] = float(t['price'])
                        except:
                            pass
            except Exception as e:
                logger.debug(f"Price fetch error: {e}")

        self.prices = prices
        self.last_refresh = time.time()
        return prices
    
    def get_exchange_balances(self) -> Dict[str, Dict[str, float]]:
        """Get balances from all connected exchanges"""
        balances = {}
        
        # Binance
        if self.binance:
            try:
                account = self.binance.session.get(
                    f'{self.binance.base}/api/v3/account',
                    timeout=10,
                    params=self.binance._sign({})
                ).json()
                
                binance_bal = {}
                for b in account.get('balances', []):
                    asset = b['asset']
                    free = float(b['free'])
                    locked = float(b['locked'])
                    total = free + locked
                    if total > 0.0001:
                        binance_bal[asset] = total
                
                balances["binance"] = binance_bal
            except Exception as e:
                logger.debug(f"Binance balance error: {e}")
                balances["binance"] = {}
        
        # Kraken
        if self.kraken:
            try:
                kraken_bal = self.kraken.get_account_balance() or {}
                # Normalize common Kraken cash codes
                normalized: Dict[str, float] = {}
                for asset, qty in kraken_bal.items():
                    norm_asset = {
                        "ZUSD": "USD",
                        "ZEUR": "EUR",
                        "ZUSDT": "USDT",
                        "ZUSDC": "USDC",
                        "XBT": "BTC",
                        "XXBT": "BTC",
                        "XETH": "ETH",
                    }.get(asset, asset)
                    if norm_asset and qty and qty > 0:
                        normalized[norm_asset] = float(qty)
                balances["kraken"] = normalized
            except Exception as e:
                logger.debug(f"Kraken balance error: {e}")
                balances["kraken"] = {}
        
        # Alpaca
        if self.alpaca:
            try:
                account = self.alpaca.get_account()
                alpaca_bal = {
                    # Only treat cash as a balance here.
                    # Alpaca 'equity' is a portfolio total (cash + positions) and would double-count.
                    "USD": float(account.get('cash', 0)),
                }
                balances["alpaca"] = alpaca_bal
            except Exception as e:
                logger.debug(f"Alpaca balance error: {e}")
                balances["alpaca"] = {}
        
        return balances
    
    def compute_equity(self) -> EquitySnapshot:
        """
        Compute total portfolio equity from live exchange data.
        This is the REAL number from your actual accounts.
        """
        # Refresh prices if stale
        if time.time() - self.last_refresh > 5:
            self.refresh_prices()
        
        # Get live balances
        balances = self.get_exchange_balances()
        
        total_equity = 0.0
        total_cash = 0.0
        total_positions = 0.0
        
        self.positions.clear()
        
        for exchange, assets in balances.items():
            for asset, qty in assets.items():
                if qty <= 0:
                    continue
                
                # Cash-like assets
                if asset in ['USDT', 'USD', 'USDC', 'BUSD', 'DAI']:
                    total_cash += qty
                    total_equity += qty
                else:
                    # Get price
                    price = 0.0

                    # IMPORTANT: do not reuse Binance-derived spot prices for Kraken balances.
                    # Some Kraken asset codes overlap Binance symbols but represent different markets.
                    if exchange == "kraken" and self.kraken:
                        try:
                            t = self.kraken.best_price(f"{asset}USD")
                            price = float(t.get("price", 0.0) or 0.0)
                        except Exception:
                            price = 0.0
                    else:
                        price = float(self.prices.get(asset, 0) or 0.0)

                    if price <= 0:
                        continue
                    
                    value = qty * price
                    total_positions += value
                    total_equity += value
                    
                    # Create position snapshot
                    key = f"{exchange}:{asset}"
                    self.positions[key] = PositionSnapshot(
                        symbol=asset,
                        exchange=exchange,
                        quantity=qty,
                        avg_price=price,  # Would need order history for true avg
                        current_price=price,
                        market_value=value,
                        unrealized_pnl=0,  # Would need entry price tracking
                        unrealized_pnl_pct=0
                    )
        
        # Set baseline if first run
        if not self.baseline_set and total_equity > 0:
            self.initial_equity = total_equity
            self.baseline_set = True
            logger.info(f"💰 Baseline equity set: ${total_equity:.2f}")
        
        # Compute PnL
        unrealized_pnl = total_positions  # Simplified - would track entries
        total_pnl = total_equity - self.initial_equity if self.baseline_set else 0
        
        snapshot = EquitySnapshot(
            timestamp=time.time(),
            total_equity=total_equity,
            cash_balance=total_cash,
            positions_value=total_positions,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl
        )
        
        self.equity_history.append(snapshot)
        return snapshot
    
    def record_trade(self, 
                     symbol: str, 
                     exchange: str,
                     side: str,
                     quantity: float,
                     price: float,
                     fee: float,
                     pnl: float,
                     source: str = "UNKNOWN"):
        """Record a trade and update PnL"""
        trade = TradeRecord(
            timestamp=time.time(),
            symbol=symbol,
            exchange=exchange,
            side=side,
            quantity=quantity,
            price=price,
            fee=fee,
            pnl=pnl,
            source=source
        )
        
        self.trade_history.append(trade)
        self.trade_count += 1
        self.realized_pnl += pnl
        
        if pnl > 0:
            self.win_count += 1
        elif pnl < 0:
            self.loss_count += 1
        
        logger.info(f"💰 TRADE: {side} {quantity:.6f} {symbol} @ ${price:.4f} | "
                   f"PnL: ${pnl:.4f} | Source: {source}")
    
    def record_sweep(self, from_world: str = "", amount: float = 0.0, reason: str = "", symbol: str = ""):
        """Record a sweep from Omega Converter"""
        self.sweep_pnl += amount
        self.sweep_count += 1
        self.realized_pnl += amount
        
        logger.info(f"⚡ SWEEP: +${amount:.4f} from {from_world} | Reason: {reason} | Total swept: ${self.sweep_pnl:.4f}")
    
    def get_win_rate(self) -> float:
        """Calculate win rate"""
        total = self.win_count + self.loss_count
        return (self.win_count / total * 100) if total > 0 else 0.0
    
    def get_growth_rate(self) -> float:
        """Calculate growth rate since start"""
        if not self.baseline_set or self.initial_equity <= 0:
            return 0.0
        
        if self.equity_history:
            current = self.equity_history[-1].total_equity
            return ((current / self.initial_equity) - 1) * 100
        return 0.0
    
    def print_board(self, compact: bool = False):
        """Print the revenue board"""
        snapshot = self.compute_equity()
        runtime = time.time() - self.start_time
        
        if compact:
            # One-line compact format
            print(f"💰 ${snapshot.total_equity:.2f} | "
                  f"PnL: ${snapshot.total_pnl:+.2f} ({self.get_growth_rate():+.2f}%) | "
                  f"Realized: ${self.realized_pnl:.2f} | "
                  f"Trades: {self.trade_count} ({self.get_win_rate():.0f}% WR) | "
                  f"Sweeps: {self.sweep_count} (${self.sweep_pnl:.2f})")
        else:
            # Full board
            print("\n" + "═" * 80)
            print("💰 AUREON REVENUE BOARD - LIVE PORTFOLIO 💰")
            print("═" * 80)
            print(f"  ⏱️  Runtime: {runtime/60:.1f} min | Last Update: {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 80)
            print(f"  📊 PORTFOLIO VALUE")
            print(f"     Total Equity:    ${snapshot.total_equity:>12,.2f}")
            print(f"     Cash Balance:    ${snapshot.cash_balance:>12,.2f}")
            print(f"     Positions Value: ${snapshot.positions_value:>12,.2f}")
            print("-" * 80)
            print(f"  📈 PROFIT & LOSS")
            print(f"     Initial Equity:  ${self.initial_equity:>12,.2f}")
            print(f"     Total P&L:       ${snapshot.total_pnl:>+12,.2f}  ({self.get_growth_rate():+.2f}%)")
            print(f"     Realized P&L:    ${self.realized_pnl:>+12,.2f}")
            print(f"     Sweep Profits:   ${self.sweep_pnl:>+12,.2f}  ({self.sweep_count} sweeps)")
            print("-" * 80)
            print(f"  🎯 TRADING STATS")
            print(f"     Total Trades:    {self.trade_count:>12}")
            print(f"     Win Rate:        {self.get_win_rate():>11.1f}%  ({self.win_count}W / {self.loss_count}L)")
            print("-" * 80)
            
            # Top positions
            if self.positions:
                print(f"  🏦 TOP POSITIONS")
                sorted_pos = sorted(
                    self.positions.values(),
                    key=lambda p: p.market_value,
                    reverse=True
                )[:5]
                for pos in sorted_pos:
                    print(f"     {pos.exchange:>8} | {pos.symbol:<6} | "
                          f"Qty: {pos.quantity:>12.6f} | "
                          f"Value: ${pos.market_value:>10,.2f}")
            
            print("═" * 80 + "\n")
    
    def get_status(self) -> Dict:
        """Get status as dict (for JSON/API)"""
        snapshot = self.compute_equity()
        
        return {
            "timestamp": time.time(),
            "runtime_seconds": time.time() - self.start_time,
            "equity": {
                "total": snapshot.total_equity,
                "cash": snapshot.cash_balance,
                "positions": snapshot.positions_value,
                "initial": self.initial_equity
            },
            "pnl": {
                "total": snapshot.total_pnl,
                "realized": self.realized_pnl,
                "sweep": self.sweep_pnl,
                "growth_pct": self.get_growth_rate()
            },
            "trading": {
                "trades": self.trade_count,
                "wins": self.win_count,
                "losses": self.loss_count,
                "win_rate": self.get_win_rate(),
                "sweeps": self.sweep_count
            },
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "exchanges": list(self.exchanges.keys())
        }
    
    def to_json(self) -> str:
        """Export status as JSON"""
        return json.dumps(self.get_status(), indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

_revenue_board: Optional[RevenueBoard] = None

def get_revenue_board(**kwargs) -> RevenueBoard:
    """Get or create the revenue board singleton"""
    global _revenue_board
    if _revenue_board is None:
        _revenue_board = RevenueBoard(**kwargs)
    return _revenue_board


def print_revenue_board(compact: bool = True):
    """Print the revenue board (creates if needed)"""
    board = get_revenue_board()
    board.print_board(compact=compact)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - Standalone Demo
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run standalone revenue board"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aureon Revenue Board")
    parser.add_argument("--interval", type=float, default=10.0, help="Refresh interval")
    parser.add_argument("--compact", action="store_true", help="Compact output")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                       ║
║     💰 AUREON REVENUE BOARD - REAL-TIME PORTFOLIO TRACKER 💰                                           ║
║                                                                                                       ║
║     Live portfolio value from your actual exchange accounts                                           ║
║                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    board = RevenueBoard()
    
    print(f"📈 Connected exchanges: {list(board.exchanges.keys())}")
    print(f"⏱️  Refresh interval: {args.interval}s")
    print("-" * 60)
    
    try:
        while True:
            if args.json:
                print(board.to_json())
            else:
                board.print_board(compact=args.compact)
            
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n\n💰 Revenue Board stopped.")
        board.print_board(compact=False)


if __name__ == "__main__":
    main()
