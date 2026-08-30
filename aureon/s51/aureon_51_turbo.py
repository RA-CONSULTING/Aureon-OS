#!/usr/bin/env python3
"""
🚀 AUREON 51% TURBO - Fast Compounding Trader 🚀
================================================
ONE GOAL: 51%+ Win Rate with NET PROFIT after ALL fees
Uses realistic price modeling for faster iteration.

Strategy:
- Take Profit: +2.0%
- Stop Loss: -0.8%  
- Position Size: 15% of balance (COMPOUNDING!)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# STRATEGY PARAMETERS
# ═══════════════════════════════════════════════════════════════
# 💰 FEE MODEL: Must match penny profit formula r = ((1 + P/A) / (1-f)²) - 1
# where f = fee + slippage + spread per leg
KRAKEN_FEE = 0.0040          # 0.40% taker fee (CORRECT Kraken rate)
SLIPPAGE_PCT = 0.0020        # 0.20% estimated slippage
SPREAD_COST_PCT = 0.0010     # 0.10% estimated spread
# Combined rate per leg = 0.70% total
TOTAL_FEE_RATE = KRAKEN_FEE + SLIPPAGE_PCT + SPREAD_COST_PCT

TAKE_PROFIT_PCT = 2.0        # 2.0% profit target
STOP_LOSS_PCT = 0.8          # 0.8% stop loss
POSITION_SIZE_PCT = 0.15     # 15% of balance per trade
MAX_POSITIONS = 4            # Max concurrent positions
MIN_TRADE_USD = 15.0         # Minimum trade size
TARGET_TRADES = 100          # Run until this many trades

# Momentum coins have positive drift
MOMENTUM_WIN_BIAS = 0.55     # 55% base chance for momentum coins to go up

@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: float
    entry_fee: float
    entry_value: float
    momentum: float
    entry_time: float

class Aureon51Turbo:
    """
    🚀 Fast Compounding Trader with Realistic Price Modeling
    """
    
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.prices: Dict[str, float] = {}
        
        # Stats
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_fees = 0.0
        self.net_profit = 0.0
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        self.trade_log: List[Dict] = []
        
    def banner(self):
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🚀 AUREON 51% TURBO - FAST COMPOUND SIMULATOR 🚀                       ║
║                                                                          ║
║   Strategy:                                                              ║
║   ├─ Take Profit: +{TAKE_PROFIT_PCT}%                                                 ║
║   ├─ Stop Loss:   -{STOP_LOSS_PCT}%                                                 ║
║   ├─ Position Size: 15% of balance (COMPOUNDING!)                       ║
║   └─ Max Positions: {MAX_POSITIONS}                                                  ║
║                                                                          ║
║   Goal: 51%+ Win Rate with NET PROFIT after fees                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
        
   💵 Starting Balance: ${self.initial_balance:.2f}
   🎯 Target Trades: {TARGET_TRADES}
""")
        
    def init_coins(self):
        """No-op retained for compatibility; live prices must be ingested."""
        self.prices = {}
            
    def simulate_price_move(self, symbol: str, momentum: float) -> Optional[float]:
        """Retained API surface; returns only the latest ingested live price."""
        return self.prices.get(symbol)
        
    def find_opportunities(self) -> List[Dict]:
        """No live scanner is connected to this legacy compatibility class."""
        return []
        
    def open_position(self, opp: Dict):
        """Open a new position"""
        symbol = opp["symbol"]
        momentum = opp["momentum"]
        
        # Position sizing with compounding
        pos_size = self.balance * POSITION_SIZE_PCT
        if pos_size < MIN_TRADE_USD:
            return
            
        price = self.prices.get(symbol)
        if price is None or price <= 0:
            return
        # Entry fee uses combined rate to match penny profit formula
        entry_fee = pos_size * TOTAL_FEE_RATE
        quantity = pos_size / price
        
        self.positions[symbol] = Position(
            symbol=symbol,
            entry_price=price,
            quantity=quantity,
            entry_fee=entry_fee,
            entry_value=pos_size,
            momentum=momentum,
            entry_time=time.time()
        )
        
        self.total_fees += entry_fee
        
        print(f"   🎯 BUY  {symbol:12s} @ ${price:.6f} | ${pos_size:.2f} | Mom: +{momentum:.1f}%")
        
    def check_positions(self):
        """Check all positions for TP/SL"""
        to_close = []
        
        for symbol, pos in self.positions.items():
            # Simulate price movement
            current_price = self.simulate_price_move(symbol, pos.momentum)
            if current_price is None:
                continue
            
            change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            
            # Check TP
            if change_pct >= TAKE_PROFIT_PCT:
                to_close.append((symbol, "TP", change_pct, current_price))
            # Check SL
            elif change_pct <= -STOP_LOSS_PCT:
                to_close.append((symbol, "SL", change_pct, current_price))
                
        for symbol, reason, pct, price in to_close:
            self.close_position(symbol, reason, pct, price)
            
    def close_position(self, symbol: str, reason: str, pct: float, price: float):
        """Close a position"""
        pos = self.positions.pop(symbol)
        
        # Calculate P&L using combined rate (fee + slippage + spread)
        exit_value = pos.quantity * price
        exit_fee = exit_value * TOTAL_FEE_RATE
        gross_pnl = exit_value - pos.entry_value
        # Total expenses = entry_fee + exit_fee (both include slippage/spread)
        net_pnl = gross_pnl - pos.entry_fee - exit_fee
        
        self.total_fees += exit_fee
        self.balance += net_pnl
        self.net_profit += net_pnl
        self.total_trades += 1
        
        if net_pnl > 0:
            self.wins += 1
            icon = "✅"
        else:
            self.losses += 1
            icon = "❌"
            
        # Track drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        dd = (self.peak_balance - self.balance) / self.peak_balance * 100
        if dd > self.max_drawdown:
            self.max_drawdown = dd
            
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        
        self.trade_log.append({
            "symbol": symbol,
            "reason": reason,
            "pct": pct,
            "net_pnl": net_pnl,
            "balance": self.balance,
            "win_rate": win_rate
        })
        
        print(f"   {icon} CLOSE {symbol:12s} | {reason} {pct:+.2f}% | Net: ${net_pnl:+.2f} | Bal: ${self.balance:.2f} | WR: {win_rate:.1f}%")
        
    def run(self):
        """Main trading loop"""
        self.banner()
        self.init_coins()
        
        print("🚀 Starting turbo simulation...\n")
        
        cycle = 0
        while self.total_trades < TARGET_TRADES:
            cycle += 1
            
            # Check existing positions
            self.check_positions()
            
            # Open new positions if we have room
            if len(self.positions) < MAX_POSITIONS:
                opps = self.find_opportunities()
                for opp in opps[:MAX_POSITIONS - len(self.positions)]:
                    self.open_position(opp)
                    
            # Small delay for readability
            time.sleep(0.05)
            
            # Progress update every 10 trades
            if self.total_trades > 0 and self.total_trades % 10 == 0:
                wr = self.wins / self.total_trades * 100
                print(f"\n   📊 Progress: {self.total_trades} trades | WR: {wr:.1f}% | Bal: ${self.balance:.2f}\n")
                
        self.final_report()
        
    def final_report(self):
        """Print final statistics"""
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100
        
        print(f"""

╔══════════════════════════════════════════════════════════════════════════╗
║              🚀 AUREON 51% TURBO - FINAL REPORT 🚀                       ║
╚══════════════════════════════════════════════════════════════════════════╝

   Starting:    ${self.initial_balance:.2f}
   Final:       ${self.balance:.2f}
   💰 NET P&L:  ${self.balance - self.initial_balance:+.2f} ({total_return:+.2f}%)

   Trades:      {self.total_trades}
   Wins:        {self.wins}
   Losses:      {self.losses}
   🎯 WIN RATE: {win_rate:.1f}%

   Total Fees:  ${self.total_fees:.2f}
   Net Profit:  ${self.net_profit:+.2f}
   Max DD:      {self.max_drawdown:.1f}%
""")
        
        # Win rate analysis
        print("   📈 STRATEGY MATH:")
        avg_win = sum(t["net_pnl"] for t in self.trade_log if t["net_pnl"] > 0) / max(self.wins, 1)
        avg_loss = sum(t["net_pnl"] for t in self.trade_log if t["net_pnl"] < 0) / max(self.losses, 1)
        
        print(f"   ├─ Avg Win:  ${avg_win:+.2f}")
        print(f"   ├─ Avg Loss: ${avg_loss:.2f}")
        print(f"   ├─ R:R Ratio: {abs(avg_win/avg_loss):.2f}:1")
        print(f"   └─ Breakeven WR: {100 * abs(avg_loss) / (avg_win + abs(avg_loss)):.1f}%")
        
        if win_rate >= 51 and self.net_profit > 0:
            print(f"\n   ✅ GOAL ACHIEVED: {win_rate:.1f}% WR + ${self.net_profit:+.2f} NET PROFIT! ✅")
        else:
            print(f"\n   ⚠️  Need adjustment: WR={win_rate:.1f}%, Net={self.net_profit:+.2f}")


if __name__ == "__main__":
    trader = Aureon51Turbo(initial_balance=1000.0)
    trader.run()
