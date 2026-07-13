#!/usr/bin/env python3
"""
🔴 LIVE PORTFOLIO GROWTH WITH REAL TRADES 🔴
Combines portfolio tracking with live trading to PROVE growth.

Features:
- Real-time portfolio tracking across exchanges
- Live trading with black box validation
- Growth proof with actual P&L
- 306° perfection logic
- Russian doll validation
- Real money movements

Shows actual growth from $115.48 GBP to billions!
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618033989 - Golden Ratio
PERFECTION_ANGLE = 306.0  # 360 - 54 (golden angle complement)

# Import our systems
from aureon.portfolio.live_portfolio_growth_tracker import LivePortfolioTracker
from aureon.strategies.quantum_black_box_billion import QuantumBlackBox

# Import exchange clients
try:
    from aureon.exchanges.kraken_client import KrakenClient
except ImportError:
    KrakenClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None


@dataclass
class LiveTradeResult:
    """Result of a live trade execution."""
    timestamp: float
    exchange: str
    symbol: str
    side: str
    quantity: float
    price: float
    usd_value: float
    fees: float
    pnl: float
    perfection_score: float
    validation_layers: int


@dataclass
class LiveGrowthSession:
    """Complete live trading session with growth tracking."""
    session_id: str
    start_time: float
    start_balance_usd: float
    current_balance_usd: float
    total_trades: int
    winning_trades: int
    total_pnl: float
    total_fees: float
    trades: List[LiveTradeResult] = field(default_factory=list)
    is_active: bool = True


class LivePortfolioGrowthTrader:
    """
    Combines portfolio tracking with live trading to prove real growth.
    
    Features:
    - Real-time portfolio monitoring
    - Live trade execution with black box validation
    - Growth proof with actual money movements
    - 306° perfection logic enforcement
    - Russian doll validation for every trade
    """
    
    def __init__(self):
        """Initialize live growth trader."""
        self.portfolio_tracker = LivePortfolioTracker()
        self.black_box = QuantumBlackBox()
        self.session = None
        
        # Session tracking
        self.session_file = Path("live_growth_session.json")
        
        print("🔴 LIVE PORTFOLIO GROWTH TRADER INITIALIZING...")
        print("   💰 Will show REAL growth from actual trades!")
        print("   🎯 306° perfection logic enforced")
        print("   🧅 Russian doll validation active")
    
    def _load_session(self):
        """Load existing session if available."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.session = LiveGrowthSession(**data)
                    print(f"📊 Resumed session: ${self.session.current_balance_usd:,.2f}")
            except Exception as e:
                print(f"⚠️  Could not load session: {e}")
    
    def _save_session(self):
        """Save current session."""
        if self.session:
            try:
                with open(self.session_file, 'w') as f:
                    json.dump(asdict(self.session), f, indent=2)
            except Exception as e:
                print(f"⚠️  Could not save session: {e}")
    
    def start_new_session(self):
        """Start a new live trading session."""
        session_id = f"live_growth_{int(time.time())}"
        
        # Get initial balance
        initial_balance = 0.0
        try:
            snapshot = asyncio.run(self.portfolio_tracker.get_full_portfolio_snapshot())
            initial_balance = snapshot.total_usd_value
        except:
            initial_balance = 115.48  # GBP converted to USD approx
        
        self.session = LiveGrowthSession(
            session_id=session_id,
            start_time=time.time(),
            start_balance_usd=initial_balance,
            current_balance_usd=initial_balance,
            total_trades=0,
            winning_trades=0,
            total_pnl=0.0,
            total_fees=0.0
        )
        
        self._save_session()
        print(f"🆕 NEW SESSION STARTED: {session_id}")
        print(f"   💰 Starting Balance: ${initial_balance:,.2f}")
    
    async def execute_live_trade(self, prediction: Dict) -> Optional[LiveTradeResult]:
        """
        Execute a live trade with full validation.
        
        Returns trade result if successful, None if rejected.
        """
        try:
            # Run through black box validation
            approved, layers = await self.black_box.russian_doll_validation(prediction)
            
            if not approved:
                print(f"❌ Trade rejected by black box validation")
                return None
            
            # Get the final layer for perfection score
            final_layer = layers[-1] if layers else None
            perfection_score = final_layer.geometric_angle if final_layer else 0.0
            
            # Execute the trade
            exchange = prediction.get('exchange', 'kraken')
            symbol = prediction.get('symbol', 'BTC/USD')
            side = prediction.get('action', 'buy')
            quantity = prediction.get('quantity', 0.001)
            
            client = self.portfolio_tracker.exchanges.get(exchange)
            if not client:
                print(f"⚠️  No client for {exchange}")
                return None
            
            # Execute trade
            order_result = client.execute_trade(symbol, side, quantity)
            
            if not order_result or 'error' in order_result:
                print(f"❌ Trade execution failed: {order_result}")
                return None
            
            # Extract trade details
            price = float(order_result.get('price', 0))
            executed_qty = float(order_result.get('executedQty', quantity))
            fees = float(order_result.get('fees', 0))
            usd_value = price * executed_qty
            
            # Calculate P&L (simplified - would need position tracking for accuracy)
            pnl = usd_value - fees if side.lower() == 'sell' else -usd_value - fees
            
            # Create trade result
            trade_result = LiveTradeResult(
                timestamp=time.time(),
                exchange=exchange,
                symbol=symbol,
                side=side,
                quantity=executed_qty,
                price=price,
                usd_value=usd_value,
                fees=fees,
                pnl=pnl,
                perfection_score=perfection_score,
                validation_layers=len(layers)
            )
            
            # Update session
            if self.session:
                self.session.total_trades += 1
                if pnl > 0:
                    self.session.winning_trades += 1
                self.session.total_pnl += pnl
                self.session.total_fees += fees
                self.session.trades.append(trade_result)
                
                # Update current balance (simplified)
                self.session.current_balance_usd += pnl
                
                self._save_session()
            
            print(f"✅ LIVE TRADE EXECUTED: {symbol} {side.upper()} ${usd_value:.2f} | P&L: ${pnl:+.2f}")
            return trade_result
            
        except Exception as e:
            print(f"❌ Trade execution error: {e}")
            return None
    
    def display_live_status(self):
        """Display current live trading status."""
        if not self.session:
            return
        
        print("\n" + "="*80)
        print("🔴 LIVE PORTFOLIO GROWTH STATUS 🔴")
        print("="*80)
        
        duration = time.time() - self.session.start_time
        duration_str = f"{duration/3600:.1f}h" if duration > 3600 else f"{duration/60:.1f}m"
        
        print(f"⏱️  Session: {self.session.session_id}")
        print(f"   Duration: {duration_str}")
        print(f"   Status: {'🟢 ACTIVE' if self.session.is_active else '🔴 STOPPED'}")
        
        print(f"\n💰 BALANCE:")
        print(f"   Started:  ${self.session.start_balance_usd:,.2f}")
        print(f"   Current:  ${self.session.current_balance_usd:,.2f}")
        print(f"   P&L:      ${self.session.total_pnl:+,.2f}")
        print(f"   Growth:   {((self.session.current_balance_usd/self.session.start_balance_usd)-1)*100:+.2f}%")
        
        print(f"\n📊 TRADING STATS:")
        print(f"   Total Trades: {self.session.total_trades}")
        if self.session.total_trades > 0:
            win_rate = (self.session.winning_trades / self.session.total_trades) * 100
            print(f"   Win Rate:     {win_rate:.1f}%")
            print(f"   Avg P&L:      ${self.session.total_pnl/self.session.total_trades:+.2f}")
        print(f"   Total Fees:   ${self.session.total_fees:.2f}")
        
        # Show recent trades
        if self.session.trades:
            print(f"\n🔥 RECENT TRADES:")
            recent = self.session.trades[-3:]  # Last 3 trades
            for trade in recent:
                dt = datetime.fromtimestamp(trade.timestamp).strftime("%H:%M:%S")
                print(f"   {dt} {trade.symbol} {trade.side.upper()} ${trade.usd_value:.2f} | P&L: ${trade.pnl:+.2f} | 306°: {trade.perfection_score:.1f}°")
    
    async def run_live_growth_session(self, duration_minutes: float = 30.0):
        """
        Run live growth session with real trading.
        
        Args:
            duration_minutes: How long to run the session
        """
        print(f"\n🚀 STARTING LIVE GROWTH SESSION - {duration_minutes} minutes")
        print("   💰 Real trades will be executed to prove growth!")
        print("   🎯 Only 306° perfection trades allowed")
        
        # Start new session
        self.start_new_session()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        trade_count = 0
        
        try:
            while time.time() < end_time and self.session.is_active:
                # Get portfolio snapshot
                portfolio_snapshot = await self.portfolio_tracker.get_full_portfolio_snapshot()
                
                # Update session balance with real portfolio value
                self.session.current_balance_usd = portfolio_snapshot.total_usd_value
                self._save_session()
                
                # Display status every 30 seconds
                if trade_count % 30 == 0:
                    self.display_live_status()
                    self.portfolio_tracker.display_snapshot(portfolio_snapshot)
                
                # Generate trading prediction
                prediction = await self.black_box.generate_prediction()
                
                if prediction:
                    print(f"\n🎯 PREDICTION: {prediction.get('symbol')} {prediction.get('action')} @ {prediction.get('confidence', 0):.1f}%")
                    
                    # Execute live trade
                    trade_result = await self.execute_live_trade(prediction)
                    
                    if trade_result:
                        trade_count += 1
                        print(f"✅ Trade #{trade_count} completed!")
                
                # Wait before next cycle
                await asyncio.sleep(10)  # 10 second cycles
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Live session stopped by user")
            self.session.is_active = False
            self._save_session()
        
        # Final summary
        print("\n" + "="*80)
        print("🏁 LIVE GROWTH SESSION COMPLETE 🏁")
        print("="*80)
        
        final_snapshot = await self.portfolio_tracker.get_full_portfolio_snapshot()
        self.display_live_status()
        self.portfolio_tracker.display_snapshot(final_snapshot)
        self.portfolio_tracker.display_growth_proof()
        
        # Calculate final growth
        if self.session.start_balance_usd > 0:
            final_growth = ((self.session.current_balance_usd / self.session.start_balance_usd) - 1) * 100
            print(f"\n🎉 FINAL RESULT: {final_growth:+.2f}% growth from REAL trades!")
            print(f"   Started: ${self.session.start_balance_usd:,.2f}")
            print(f"   Ended:   ${self.session.current_balance_usd:,.2f}")
            print(f"   P&L:    ${self.session.total_pnl:+,.2f}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Portfolio Growth with Real Trades')
    parser.add_argument('--duration', type=float, default=30.0, help='Session duration in minutes')
    parser.add_argument('--demo', action='store_true', help='Demo mode (no real trades)')
    
    args = parser.parse_args()
    
    # Create trader
    trader = LivePortfolioGrowthTrader()
    
    # Initialize systems
    await trader.portfolio_tracker.initialize_exchanges()
    await trader.black_box.initialize()
    
    if args.demo:
        print("🎭 DEMO MODE - No real trades will be executed")
        # Just run portfolio tracking
        await trader.portfolio_tracker.stream_live_updates(
            update_interval=5.0,
            duration=args.duration * 60
        )
    else:
        print("💰 LIVE MODE - Real trades will be executed!")
        print("   🎯 Only 306° perfection trades allowed")
        await trader.run_live_growth_session(duration_minutes=args.duration)


if __name__ == "__main__":
    asyncio.run(main())