#!/usr/bin/env python3
"""
AUREON PROFIT SIMULATION - Live Market Data
============================================

Simulates trades on LIVE market data using QGITA metrics.
Goal: Net profit of at least £0.02 (2 pence) per trade AFTER fees.

Binance fees: 0.1% maker/taker (0.075% with BNB discount)
To profit 2p after fees on a £10 trade:
  - Need price to move 0.1% (fee) + 0.1% (fee) + 0.02/10 = 0.4% minimum

Strategy: Only enter when coherence > 0.938 (high-conviction setup)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio
FEE_RATE = 0.001  # 0.1% Binance fee
MIN_PROFIT_GBP = 0.02  # 2 pence minimum profit target
GBP_USD_RATE = 0.79  # Approximate

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE MARKET DATA COLLECTOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketTick:
    timestamp: float
    symbol: str
    price: float
    bid: float
    ask: float
    spread: float
    volume_24h: float
    price_change_pct: float

class LiveMarketFeed:
    """Collects live market data from Binance"""
    
    def __init__(self, client: BinanceClient, symbols: List[str]):
        self.client = client
        self.symbols = symbols
        self.price_history: Dict[str, deque] = {s: deque(maxlen=100) for s in symbols}
        self.volume_history: Dict[str, deque] = {s: deque(maxlen=100) for s in symbols}
    
    def get_tick(self, symbol: str) -> Optional[MarketTick]:
        """Get current market tick for symbol"""
        try:
            # Get 24hr ticker
            ticker_resp = self.client.session.get(
                f"{self.client.base}/api/v3/ticker/24hr",
                params={'symbol': symbol}
            )
            ticker = ticker_resp.json()
            
            # Get order book for spread
            book_resp = self.client.session.get(
                f"{self.client.base}/api/v3/ticker/bookTicker",
                params={'symbol': symbol}
            )
            book = book_resp.json()
            
            bid = float(book['bidPrice'])
            ask = float(book['askPrice'])
            price = float(ticker['lastPrice'])
            spread = (ask - bid) / price if price > 0 else 0
            
            tick = MarketTick(
                timestamp=time.time(),
                symbol=symbol,
                price=price,
                bid=bid,
                ask=ask,
                spread=spread,
                volume_24h=float(ticker['volume']),
                price_change_pct=float(ticker['priceChangePercent'])
            )
            
            # Store in history
            self.price_history[symbol].append(price)
            self.volume_history[symbol].append(float(ticker['volume']))
            
            return tick
            
        except Exception as e:
            logger.error(f"Failed to get tick for {symbol}: {e}")
            return None

# ═══════════════════════════════════════════════════════════════════════════════
# QGITA COHERENCE ENGINE (from aureon_nexus.py)
# ═══════════════════════════════════════════════════════════════════════════════

class CoherenceEngine:
    """
    Calculates coherence Γ from market data.
    Entry threshold: Γ > 0.938
    """
    
    def __init__(self):
        self.entry_threshold = 0.938
        self.exit_threshold = 0.934
        self.coherence_history = deque(maxlen=50)
    
    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate normalized volatility"""
        if len(prices) < 2:
            return 0.5
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        if not returns:
            return 0.5
        
        std = (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) ** 0.5
        # Normalize: typical crypto volatility 1-5%
        return min(1.0, std * 100)
    
    def calculate_momentum(self, prices: List[float]) -> float:
        """Calculate momentum score 0-1"""
        if len(prices) < 5:
            return 0.5
        
        short_ma = sum(prices[-5:]) / 5
        long_ma = sum(prices[-20:]) / min(20, len(prices))
        
        momentum = (short_ma - long_ma) / long_ma if long_ma > 0 else 0
        # Normalize to 0-1
        return 0.5 + momentum * 10  # Scale factor
    
    def calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength using linear regression R²"""
        if len(prices) < 10:
            return 0.5
        
        n = len(prices)
        x = list(range(n))
        
        # Linear regression
        x_mean = sum(x) / n
        y_mean = sum(prices) / n
        
        num = sum((x[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
        den_x = sum((x[i] - x_mean)**2 for i in range(n))
        den_y = sum((prices[i] - y_mean)**2 for i in range(n))
        
        if den_x == 0 or den_y == 0:
            return 0.5
        
        r = num / (den_x * den_y) ** 0.5
        return abs(r)  # R² as trend strength
    
    def calculate_golden_ratio_alignment(self, prices: List[float]) -> float:
        """Check if price movements align with golden ratio"""
        if len(prices) < 8:
            return 0.5
        
        # Look at ratios of consecutive moves
        moves = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        if len(moves) < 3:
            return 0.5
        
        phi_matches = 0
        checks = 0
        
        for i in range(len(moves) - 1):
            if moves[i] > 0:
                ratio = moves[i+1] / moves[i]
                # Check if ratio is near φ or 1/φ
                if abs(ratio - PHI) < 0.2 or abs(ratio - 1/PHI) < 0.2:
                    phi_matches += 1
                checks += 1
        
        return phi_matches / checks if checks > 0 else 0.5
    
    def calculate_coherence(self, prices: List[float], tick: MarketTick) -> Tuple[float, Dict]:
        """
        Calculate full coherence Γ from price history and current tick.
        Returns (coherence, breakdown)
        """
        volatility = self.calculate_volatility(prices)
        momentum = self.calculate_momentum(prices)
        trend = self.calculate_trend_strength(prices)
        phi_align = self.calculate_golden_ratio_alignment(prices)
        
        # Spread quality (lower is better)
        spread_score = 1.0 - min(1.0, tick.spread * 1000)  # Penalize high spreads
        
        # Volume trend (increasing volume = good)
        volume_score = 0.5
        if len(prices) >= 5:
            # Simple volume proxy from price movement
            recent_range = max(prices[-5:]) - min(prices[-5:])
            avg_range = (max(prices) - min(prices)) / (len(prices) / 5)
            volume_score = min(1.0, recent_range / avg_range) if avg_range > 0 else 0.5
        
        # Substrate (weighted combination)
        substrate = (
            volatility * 0.15 +
            momentum * 0.20 +
            trend * 0.25 +
            phi_align * 0.20 +
            spread_score * 0.10 +
            volume_score * 0.10
        )
        
        # Observer (rate of change of coherence)
        observer = 0.5
        if len(self.coherence_history) >= 2:
            delta = list(self.coherence_history)[-1] - list(self.coherence_history)[-2]
            observer = 0.5 + delta * 5  # Scale up small changes
        
        # Echo (momentum memory)
        echo = momentum * 0.6 + trend * 0.4
        
        # Lambda and coherence
        lambda_val = substrate + observer + echo
        coherence = lambda_val / 3.0
        coherence = max(0, min(1, coherence))
        
        self.coherence_history.append(coherence)
        
        breakdown = {
            'volatility': volatility,
            'momentum': momentum,
            'trend': trend,
            'phi_align': phi_align,
            'spread_score': spread_score,
            'substrate': substrate,
            'observer': observer,
            'echo': echo,
            'lambda': lambda_val
        }
        
        return coherence, breakdown
    
    def get_signal(self, coherence: float, momentum: float) -> Tuple[str, float]:
        """Get trading signal based on coherence"""
        if coherence >= self.entry_threshold:
            # High coherence - direction from momentum
            if momentum > 0.55:
                return ('BUY', coherence)
            elif momentum < 0.45:
                return ('SELL', coherence)
        return ('HOLD', coherence)

# ═══════════════════════════════════════════════════════════════════════════════
# PROFIT CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ProfitCalculator:
    """
    Calculates if a trade will be profitable after fees.
    Target: 2p (£0.02) minimum profit per trade.
    """
    
    def __init__(self, fee_rate: float = 0.001, min_profit_gbp: float = 0.02):
        self.fee_rate = fee_rate
        self.min_profit_gbp = min_profit_gbp
        self.usd_to_gbp = 0.79
    
    def calculate_breakeven_move(self, trade_size_usd: float) -> float:
        """
        Calculate minimum price move % needed to break even + profit.
        
        Entry fee: trade_size * 0.1%
        Exit fee: trade_size * 0.1%
        Profit target: £0.02 = $0.025
        
        Total needed: 0.1% + 0.1% + (0.025 / trade_size)
        """
        entry_fee_pct = self.fee_rate
        exit_fee_pct = self.fee_rate
        profit_target_usd = self.min_profit_gbp / self.usd_to_gbp
        profit_pct = profit_target_usd / trade_size_usd
        
        return entry_fee_pct + exit_fee_pct + profit_pct
    
    def will_be_profitable(self, entry_price: float, current_price: float, 
                           side: str, trade_size_usd: float) -> Tuple[bool, float]:
        """
        Check if closing now would be profitable.
        Returns (is_profitable, expected_profit_gbp)
        """
        if side == 'BUY':
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SELL/SHORT
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Subtract fees
        net_pnl_pct = pnl_pct - (self.fee_rate * 2)
        net_pnl_usd = trade_size_usd * net_pnl_pct
        net_pnl_gbp = net_pnl_usd * self.usd_to_gbp
        
        return (net_pnl_gbp >= self.min_profit_gbp, net_pnl_gbp)

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADE SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SimulatedPosition:
    symbol: str
    side: str
    entry_price: float
    entry_time: float
    size_usd: float
    target_price: float
    stop_price: float

class ProfitSimulator:
    """
    Simulates trades on live market data.
    Only enters when coherence > 0.938.
    Targets 2p profit per trade.
    """
    
    def __init__(self, trade_size_usd: float = 10.0):
        self.client = get_binance_client()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        self.feed = LiveMarketFeed(self.client, self.symbols)
        self.coherence = CoherenceEngine()
        self.profit_calc = ProfitCalculator()
        
        self.trade_size_usd = trade_size_usd
        self.position: Optional[SimulatedPosition] = None
        
        # Stats
        self.trades: List[Dict] = []
        self.total_profit_gbp = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
    
    def find_opportunity(self) -> Optional[Tuple[str, MarketTick, float, Dict]]:
        """Scan all symbols for high-coherence opportunity"""
        best = None
        best_coherence = 0
        
        for symbol in self.symbols:
            tick = self.feed.get_tick(symbol)
            if not tick:
                continue
            
            prices = list(self.feed.price_history[symbol])
            if len(prices) < 20:
                continue
            
            coherence, breakdown = self.coherence.calculate_coherence(prices, tick)
            
            if coherence > best_coherence and coherence >= self.coherence.entry_threshold:
                best = (symbol, tick, coherence, breakdown)
                best_coherence = coherence
        
        return best
    
    def calculate_targets(self, entry_price: float, side: str) -> Tuple[float, float]:
        """Calculate target and stop prices for 2p profit"""
        breakeven_move = self.profit_calc.calculate_breakeven_move(self.trade_size_usd)
        
        # Add 20% buffer for safety
        target_move = breakeven_move * 1.2
        stop_move = breakeven_move * 0.5  # Cut losses at half the target
        
        if side == 'BUY':
            target = entry_price * (1 + target_move)
            stop = entry_price * (1 - stop_move)
        else:
            target = entry_price * (1 - target_move)
            stop = entry_price * (1 + stop_move)
        
        return target, stop
    
    def check_position(self) -> Optional[Dict]:
        """Check if current position should be closed"""
        if not self.position:
            return None
        
        tick = self.feed.get_tick(self.position.symbol)
        if not tick:
            return None
        
        current_price = tick.price
        
        # Check target hit
        if self.position.side == 'BUY':
            if current_price >= self.position.target_price:
                return self.close_position(tick, 'TARGET_HIT')
            if current_price <= self.position.stop_price:
                return self.close_position(tick, 'STOP_HIT')
        else:
            if current_price <= self.position.target_price:
                return self.close_position(tick, 'TARGET_HIT')
            if current_price >= self.position.stop_price:
                return self.close_position(tick, 'STOP_HIT')
        
        return None
    
    def close_position(self, tick: MarketTick, reason: str) -> Dict:
        """Close position and record result"""
        is_profit, pnl_gbp = self.profit_calc.will_be_profitable(
            self.position.entry_price,
            tick.price,
            self.position.side,
            self.position.size_usd
        )
        
        trade_result = {
            'symbol': self.position.symbol,
            'side': self.position.side,
            'entry_price': self.position.entry_price,
            'exit_price': tick.price,
            'entry_time': self.position.entry_time,
            'exit_time': time.time(),
            'duration_s': time.time() - self.position.entry_time,
            'size_usd': self.position.size_usd,
            'pnl_gbp': pnl_gbp,
            'reason': reason,
            'profitable': pnl_gbp > 0
        }
        
        self.trades.append(trade_result)
        self.total_profit_gbp += pnl_gbp
        
        if pnl_gbp > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        emoji = "✅" if pnl_gbp > 0 else "❌"
        logger.info(f"{emoji} CLOSED {self.position.side} {self.position.symbol}: £{pnl_gbp:.4f} ({reason})")
        
        self.position = None
        return trade_result
    
    def run_simulation(self, duration_seconds: int = 300, check_interval: float = 2.0):
        """Run simulation for specified duration"""
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    💰 AUREON PROFIT SIMULATION 💰                             ║
║                                                                               ║
║   Target: £0.02 profit per trade (after fees)                                 ║
║   Trade Size: ${self.trade_size_usd:.2f}                                      ║
║   Coherence Threshold: {self.coherence.entry_threshold}                       ║
║   Symbols: {', '.join(self.symbols)}                                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        start_time = time.time()
        cycles = 0
        
        # Warm up price history
        logger.info("📊 Warming up price history...")
        for _ in range(10):
            for symbol in self.symbols:
                self.feed.get_tick(symbol)
            time.sleep(0.5)
        
        logger.info("🚀 Starting simulation...")
        
        while time.time() - start_time < duration_seconds:
            cycles += 1
            
            # Check existing position
            if self.position:
                result = self.check_position()
            
            # Look for new opportunity if no position
            if not self.position:
                opportunity = self.find_opportunity()
                
                if opportunity:
                    symbol, tick, coherence, breakdown = opportunity
                    
                    # Determine direction from momentum
                    signal, _ = self.coherence.get_signal(coherence, breakdown['momentum'])
                    
                    if signal in ['BUY', 'SELL']:
                        target, stop = self.calculate_targets(tick.price, signal)
                        
                        self.position = SimulatedPosition(
                            symbol=symbol,
                            side=signal,
                            entry_price=tick.price,
                            entry_time=time.time(),
                            size_usd=self.trade_size_usd,
                            target_price=target,
                            stop_price=stop
                        )
                        
                        logger.info(f"🎯 ENTER {signal} {symbol} @ ${tick.price:.2f}")
                        logger.info(f"   Coherence: {coherence:.4f} | Target: ${target:.2f} | Stop: ${stop:.2f}")
            
            # Status update every 10 cycles
            if cycles % 10 == 0:
                elapsed = time.time() - start_time
                win_rate = (self.winning_trades / (self.winning_trades + self.losing_trades) * 100) if (self.winning_trades + self.losing_trades) > 0 else 0
                
                status = "IN POSITION" if self.position else "SCANNING"
                logger.info(f"⏱️ {elapsed:.0f}s | Trades: {len(self.trades)} | Win Rate: {win_rate:.1f}% | Total P&L: £{self.total_profit_gbp:.4f} | {status}")
            
            time.sleep(check_interval)
        
        # Final report
        self.print_report()
    
    def print_report(self):
        """Print final simulation report"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         SIMULATION COMPLETE                                   ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Total Trades:    {total_trades:>6}                                          ║
║   Winning Trades:  {self.winning_trades:>6}                                   ║
║   Losing Trades:   {self.losing_trades:>6}                                    ║
║   Win Rate:        {win_rate:>6.1f}%                                          ║
║   ─────────────────────────────────────────────────────────────────────────   ║
║   Total Profit:    £{self.total_profit_gbp:>8.4f}                             ║
║   Avg Per Trade:   £{(self.total_profit_gbp/total_trades if total_trades > 0 else 0):>8.4f}                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        if self.trades:
            print("\n📋 Trade Log:")
            for t in self.trades:
                emoji = "✅" if t['profitable'] else "❌"
                print(f"  {emoji} {t['side']:4} {t['symbol']:8} Entry: ${t['entry_price']:.2f} Exit: ${t['exit_price']:.2f} P&L: £{t['pnl_gbp']:.4f} ({t['reason']})")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Aureon Profit Simulation')
    parser.add_argument('--duration', type=int, default=300, help='Simulation duration in seconds')
    parser.add_argument('--size', type=float, default=10.0, help='Trade size in USD')
    parser.add_argument('--interval', type=float, default=2.0, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    sim = ProfitSimulator(trade_size_usd=args.size)
    sim.run_simulation(duration_seconds=args.duration, check_interval=args.interval)
