#!/usr/bin/env python3
"""
🪙⚡ PENNY PROFIT TURBO - ENHANCED MATH FOR MAXIMUM GAINS ⚡🪙
═══════════════════════════════════════════════════════════════════

This module ENHANCES the existing penny profit system without changing it.
Import this alongside penny_profit_engine for turbo-charged profit capture.

ENHANCEMENTS:
1. 📊 Real-time spread capture from live ticker data
2. 🎯 Micro-fee tier optimization (detect your actual tier)
3. 🔥 Compound acceleration math (faster snowball)
4. ⚡ Flash profit detection (catch quick moves)
5. 🎰 Probability-weighted thresholds (adjust for win rate)

THE PHILOSOPHY:
- Don't change what works
- Add intelligence on top
- Every fraction of a percent matters
- Speed kills (in a good way)

Gary Leckey | January 2026 | TURBO MODE
═══════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque

# Windows UTF-8 fix
if sys.platform == 'win32' and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Sacred constants for harmonic alignment
PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden ratio
LOVE_FREQUENCY = 528  # Hz


# ═══════════════════════════════════════════════════════════════
# 📊 REAL-TIME SPREAD TRACKER
# ═══════════════════════════════════════════════════════════════

@dataclass
class SpreadSnapshot:
    """A single spread measurement."""
    symbol: str
    bid: float
    ask: float
    spread_pct: float
    timestamp: float = field(default_factory=time.time)


class RealTimeSpreadTracker:
    """
    Track live spreads and adjust profit thresholds dynamically.
    
    Spreads vary throughout the day:
    - Low liquidity (weekends, holidays): Higher spreads
    - High volatility events: Spreads widen
    - Normal conditions: Tighter spreads
    
    We use ACTUAL spread data instead of estimated averages.
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.spread_history: Dict[str, deque] = {}
        self.exchange_avg_spreads: Dict[str, float] = {
            'binance': 0.0005,  # 0.05% default
            'kraken': 0.0008,   # 0.08% default
            'alpaca': 0.0008,   # 0.08% default
        }
    
    def record_spread(self, exchange: str, symbol: str, bid: float, ask: float):
        """Record a live spread observation."""
        if bid <= 0 or ask <= 0:
            return
        
        spread_pct = (ask - bid) / ((ask + bid) / 2)
        
        key = f"{exchange}:{symbol}"
        if key not in self.spread_history:
            self.spread_history[key] = deque(maxlen=self.window_size)
        
        self.spread_history[key].append(SpreadSnapshot(
            symbol=symbol,
            bid=bid,
            ask=ask,
            spread_pct=spread_pct
        ))
        
        # Update exchange average
        self._update_exchange_average(exchange)
    
    def _update_exchange_average(self, exchange: str):
        """Update rolling average spread for an exchange."""
        spreads = []
        for key, history in self.spread_history.items():
            if key.startswith(exchange):
                if history:
                    recent = list(history)[-20:]  # Last 20 observations
                    spreads.extend([s.spread_pct for s in recent])
        
        if spreads:
            self.exchange_avg_spreads[exchange] = sum(spreads) / len(spreads)
    
    def get_current_spread(self, exchange: str, symbol: str = None) -> float:
        """Get current spread estimate for an exchange/symbol."""
        if symbol:
            key = f"{exchange}:{symbol}"
            if key in self.spread_history and self.spread_history[key]:
                recent = list(self.spread_history[key])[-5:]
                return sum(s.spread_pct for s in recent) / len(recent)
        
        return self.exchange_avg_spreads.get(exchange, 0.001)
    
    def get_spread_volatility(self, exchange: str) -> float:
        """Get spread volatility (how much spreads are moving)."""
        spreads = []
        for key, history in self.spread_history.items():
            if key.startswith(exchange) and history:
                spreads.extend([s.spread_pct for s in list(history)[-50:]])
        
        if len(spreads) < 10:
            return 0.0
        
        avg = sum(spreads) / len(spreads)
        variance = sum((s - avg) ** 2 for s in spreads) / len(spreads)
        return math.sqrt(variance)


# ═══════════════════════════════════════════════════════════════
# 🎯 FEE TIER OPTIMIZER
# ═══════════════════════════════════════════════════════════════

@dataclass
class FeeTier:
    """Fee tier for an exchange."""
    tier_name: str
    maker_fee: float
    taker_fee: float
    volume_requirement: float  # 30-day volume needed


# Binance fee tiers (as of 2025)
BINANCE_TIERS = [
    FeeTier("VIP 0", 0.0010, 0.0010, 0),           # < $1M
    FeeTier("VIP 1", 0.0009, 0.0010, 1_000_000),   # $1M-5M
    FeeTier("VIP 2", 0.0008, 0.0010, 5_000_000),   # $5M-10M
    FeeTier("VIP 3", 0.0007, 0.0008, 10_000_000),  # $10M-50M
]

# Kraken fee tiers
KRAKEN_TIERS = [
    FeeTier("Starter", 0.0025, 0.0040, 0),         # $0-10k
    FeeTier("Intermediate", 0.0020, 0.0035, 10_000),
    FeeTier("Pro", 0.0015, 0.0025, 50_000),
    FeeTier("Expert", 0.0010, 0.0020, 100_000),
]

# Alpaca fee tiers
ALPACA_TIERS = [
    FeeTier("Tier 1", 0.0015, 0.0025, 0),
    FeeTier("Tier 2", 0.0012, 0.0022, 100_000),
    FeeTier("Tier 3", 0.0008, 0.0018, 500_000),
]


class FeeTierOptimizer:
    """
    Detect and optimize for your actual fee tier.
    
    Most systems assume worst-case fees. This detects your ACTUAL tier
    based on trading volume and uses those lower fees in calculations.
    """
    
    def __init__(self):
        self.tiers = {
            'binance': BINANCE_TIERS,
            'kraken': KRAKEN_TIERS,
            'alpaca': ALPACA_TIERS,
        }
        
        # Track 30-day volume per exchange
        self.volume_30d: Dict[str, float] = {
            'binance': 0,
            'kraken': 0,
            'alpaca': 0,
        }
        
        # Detected tiers (start at lowest)
        self.current_tiers: Dict[str, FeeTier] = {}
        for exchange, tiers in self.tiers.items():
            self.current_tiers[exchange] = tiers[0]
    
    def record_trade_volume(self, exchange: str, volume_usd: float):
        """Record trade volume for tier tracking."""
        exchange = exchange.lower()
        if exchange in self.volume_30d:
            self.volume_30d[exchange] += volume_usd
            self._update_tier(exchange)
    
    def _update_tier(self, exchange: str):
        """Update tier based on accumulated volume."""
        volume = self.volume_30d[exchange]
        tiers = self.tiers.get(exchange, [])
        
        # Find highest qualifying tier
        best_tier = tiers[0] if tiers else None
        for tier in tiers:
            if volume >= tier.volume_requirement:
                best_tier = tier
        
        if best_tier:
            self.current_tiers[exchange] = best_tier
    
    def get_fees(self, exchange: str, is_maker: bool = True) -> float:
        """Get current fee rate for exchange."""
        exchange = exchange.lower()
        tier = self.current_tiers.get(exchange)
        if tier:
            return tier.maker_fee if is_maker else tier.taker_fee
        
        # Default fallback
        defaults = {'binance': 0.001, 'kraken': 0.0025, 'alpaca': 0.0015}
        return defaults.get(exchange, 0.001)
    
    def get_fee_savings(self, exchange: str) -> Dict:
        """Calculate how much we're saving vs worst-case fees."""
        exchange = exchange.lower()
        tiers = self.tiers.get(exchange, [])
        if not tiers:
            return {}
        
        worst = tiers[0]
        current = self.current_tiers.get(exchange, worst)
        
        maker_savings = worst.maker_fee - current.maker_fee
        taker_savings = worst.taker_fee - current.taker_fee
        
        return {
            'current_tier': current.tier_name,
            'maker_fee': current.maker_fee,
            'taker_fee': current.taker_fee,
            'maker_savings_pct': maker_savings * 100,
            'taker_savings_pct': taker_savings * 100,
            'volume_30d': self.volume_30d.get(exchange, 0),
        }


# ═══════════════════════════════════════════════════════════════
# 🔥 COMPOUND ACCELERATION MATH
# ═══════════════════════════════════════════════════════════════

class CompoundAccelerator:
    """
    Calculate optimal profit-taking for maximum compound growth.
    
    THE MATH:
    - Taking profits too early → Less per trade
    - Taking profits too late → Fewer trades
    - OPTIMAL: Take profits at the point that maximizes growth RATE
    
    For penny profits, the optimal is often LOWER than you think
    because MORE TRADES compounds faster than BIGGER PROFITS.
    
    Formula:
    Growth Rate = (1 + profit_pct) ^ trades_per_day
    
    If you can do 100 trades/day at 0.5% each:
    (1.005)^100 = 1.647 = 64.7% daily growth!
    
    vs 10 trades/day at 2% each:
    (1.02)^10 = 1.219 = 21.9% daily growth
    """
    
    def __init__(self):
        self.trade_history: List[Dict] = []
        self.trades_per_hour = 0
        self.avg_profit_pct = 0
        self.win_rate = 0.5
    
    def record_trade(self, profit_pct: float, won: bool, duration_seconds: float):
        """Record a trade for compound optimization."""
        self.trade_history.append({
            'profit_pct': profit_pct,
            'won': won,
            'duration': duration_seconds,
            'timestamp': time.time()
        })
        
        # Keep last 1000 trades
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]
        
        self._update_stats()
    
    def _update_stats(self):
        """Update running statistics."""
        if len(self.trade_history) < 10:
            return
        
        recent = self.trade_history[-100:]
        
        # Win rate
        wins = sum(1 for t in recent if t['won'])
        self.win_rate = wins / len(recent)
        
        # Average profit (on wins)
        win_profits = [t['profit_pct'] for t in recent if t['won']]
        self.avg_profit_pct = sum(win_profits) / len(win_profits) if win_profits else 0
        
        # Trades per hour
        first_ts = recent[0]['timestamp']
        last_ts = recent[-1]['timestamp']
        hours = (last_ts - first_ts) / 3600
        if hours > 0:
            self.trades_per_hour = len(recent) / hours
    
    def get_optimal_profit_target(self, current_target_pct: float) -> Dict:
        """
        Calculate if current profit target is optimal for compound growth.
        
        Returns recommendations for adjustment.
        """
        if len(self.trade_history) < 50:
            return {
                'status': 'insufficient_data',
                'current_target': current_target_pct,
                'recommendation': current_target_pct,
                'reason': 'Need more trade history',
            }
        
        # Current compound growth rate
        expected_return_per_trade = (self.win_rate * self.avg_profit_pct) - ((1 - self.win_rate) * self.avg_profit_pct)
        current_daily_growth = (1 + expected_return_per_trade / 100) ** (self.trades_per_hour * 24)
        
        # Estimate what happens if we lower target (more trades)
        # Lower target = more trades but smaller profits
        lower_target = current_target_pct * 0.7
        estimated_more_trades = self.trades_per_hour * 1.3  # ~30% more trades
        lower_daily_growth = (1 + (lower_target * self.win_rate - lower_target * (1 - self.win_rate)) / 100) ** (estimated_more_trades * 24)
        
        # Estimate what happens if we raise target (fewer trades)
        higher_target = current_target_pct * 1.3
        estimated_fewer_trades = self.trades_per_hour * 0.8  # ~20% fewer trades
        higher_daily_growth = (1 + (higher_target * self.win_rate - higher_target * (1 - self.win_rate)) / 100) ** (estimated_fewer_trades * 24)
        
        # Find best option
        options = [
            ('lower', lower_target, lower_daily_growth),
            ('current', current_target_pct, current_daily_growth),
            ('higher', higher_target, higher_daily_growth),
        ]
        
        best = max(options, key=lambda x: x[2])
        
        return {
            'status': 'analyzed',
            'current_target': current_target_pct,
            'recommendation': best[1],
            'direction': best[0],
            'current_daily_growth': current_daily_growth,
            'recommended_daily_growth': best[2],
            'improvement_pct': ((best[2] / current_daily_growth) - 1) * 100 if current_daily_growth > 0 else 0,
            'win_rate': self.win_rate,
            'trades_per_hour': self.trades_per_hour,
            'reason': f"{'Lower' if best[0] == 'lower' else 'Higher' if best[0] == 'higher' else 'Current'} target maximizes compound growth",
        }
    
    def get_kelly_fraction(self, win_rate: float = None, avg_win_pct: float = None, avg_loss_pct: float = None) -> float:
        """
        Calculate Kelly Criterion fraction for optimal bet sizing.
        
        f* = (p * b - q) / b
        
        where:
        p = probability of winning
        q = probability of losing (1 - p)
        b = ratio of win amount to loss amount
        """
        p = win_rate or self.win_rate
        q = 1 - p
        
        # Use historical data or defaults
        if avg_win_pct is None:
            avg_win_pct = self.avg_profit_pct or 0.5
        if avg_loss_pct is None:
            avg_loss_pct = avg_win_pct  # Assume symmetric
        
        if avg_loss_pct <= 0:
            return 0.0
        
        b = avg_win_pct / avg_loss_pct  # Win/loss ratio
        
        kelly = (p * b - q) / b
        
        # Never bet more than 25% of capital (half-Kelly is safer)
        return max(0, min(0.25, kelly * 0.5))


# ═══════════════════════════════════════════════════════════════
# ⚡ FLASH PROFIT DETECTOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class FlashOpportunity:
    """A flash profit opportunity detected."""
    symbol: str
    exchange: str
    direction: str  # 'UP' or 'DOWN'
    move_pct: float
    speed_pct_per_sec: float
    detected_at: float
    expires_at: float  # Act fast!
    confidence: float


class FlashProfitDetector:
    """
    Detect rapid price movements that create instant profit opportunities.
    
    When a coin moves 0.5% in 10 seconds, that's an opportunity that
    won't last. This detects those "flash" moments.
    
    Key insight: If we can detect a move WHILE it's happening,
    we can ride the momentum for instant profit.
    """
    
    def __init__(self, min_move_pct: float = 0.3, time_window_sec: float = 30):
        self.min_move_pct = min_move_pct
        self.time_window_sec = time_window_sec
        
        # Price history per symbol
        self.price_history: Dict[str, deque] = {}
        
        # Active flash opportunities
        self.active_flashes: List[FlashOpportunity] = []
    
    def record_price(self, symbol: str, exchange: str, price: float):
        """Record a price tick."""
        key = f"{exchange}:{symbol}"
        if key not in self.price_history:
            self.price_history[key] = deque(maxlen=1000)
        
        self.price_history[key].append({
            'price': price,
            'timestamp': time.time()
        })
        
        # Check for flash opportunity
        self._detect_flash(key, symbol, exchange)
    
    def _detect_flash(self, key: str, symbol: str, exchange: str):
        """Detect if there's a flash opportunity."""
        history = self.price_history.get(key)
        if not history or len(history) < 5:
            return
        
        now = time.time()
        recent = [p for p in history if now - p['timestamp'] <= self.time_window_sec]
        
        if len(recent) < 3:
            return
        
        # Calculate move
        first_price = recent[0]['price']
        last_price = recent[-1]['price']
        move_pct = ((last_price / first_price) - 1) * 100
        
        time_elapsed = recent[-1]['timestamp'] - recent[0]['timestamp']
        if time_elapsed <= 0:
            return
        
        speed = abs(move_pct) / time_elapsed  # % per second
        
        # Check if qualifies as flash
        if abs(move_pct) >= self.min_move_pct:
            direction = 'UP' if move_pct > 0 else 'DOWN'
            
            # Calculate confidence based on consistency of move
            prices = [p['price'] for p in recent]
            if direction == 'UP':
                # Count how many consecutive up ticks
                ups = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i-1])
                confidence = ups / (len(prices) - 1)
            else:
                # Count how many consecutive down ticks
                downs = sum(1 for i in range(1, len(prices)) if prices[i] < prices[i-1])
                confidence = downs / (len(prices) - 1)
            
            # Only if high confidence (consistent direction)
            if confidence >= 0.6:
                flash = FlashOpportunity(
                    symbol=symbol,
                    exchange=exchange,
                    direction=direction,
                    move_pct=move_pct,
                    speed_pct_per_sec=speed,
                    detected_at=now,
                    expires_at=now + 10,  # 10 second window to act
                    confidence=confidence
                )
                
                # Don't duplicate
                existing = [f for f in self.active_flashes 
                           if f.symbol == symbol and f.exchange == exchange]
                if not existing:
                    self.active_flashes.append(flash)
                    logger.info(f"⚡ FLASH DETECTED: {exchange} {symbol} {direction} {move_pct:+.2f}% @ {speed:.3f}%/s")
    
    def get_active_flashes(self) -> List[FlashOpportunity]:
        """Get currently active flash opportunities."""
        now = time.time()
        
        # Remove expired
        self.active_flashes = [f for f in self.active_flashes if f.expires_at > now]
        
        return sorted(self.active_flashes, key=lambda f: f.move_pct, reverse=True)


# ═══════════════════════════════════════════════════════════════
# 🎰 PROBABILITY-WEIGHTED THRESHOLDS
# ═══════════════════════════════════════════════════════════════

class ProbabilityWeightedThresholds:
    """
    Adjust profit thresholds based on historical win probability.
    
    If a symbol has 80% win rate, we can afford tighter thresholds.
    If a symbol has 40% win rate, we need wider thresholds to compensate.
    
    Expected Value = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
    
    For positive EV, we need:
    Win Rate × Avg Win > Loss Rate × Avg Loss
    Avg Win / Avg Loss > Loss Rate / Win Rate
    """
    
    def __init__(self):
        # Track outcomes per symbol/exchange
        self.outcomes: Dict[str, List[Dict]] = {}
    
    def record_outcome(self, symbol: str, exchange: str, won: bool, profit_pct: float):
        """Record a trade outcome."""
        key = f"{exchange}:{symbol}"
        if key not in self.outcomes:
            self.outcomes[key] = []
        
        self.outcomes[key].append({
            'won': won,
            'profit_pct': profit_pct,
            'timestamp': time.time()
        })
        
        # Keep last 200 per symbol
        if len(self.outcomes[key]) > 200:
            self.outcomes[key] = self.outcomes[key][-200:]
    
    def get_adjusted_threshold(
        self,
        symbol: str,
        exchange: str,
        base_win_threshold: float,
        base_stop_threshold: float
    ) -> Tuple[float, float]:
        """
        Get probability-adjusted thresholds for a symbol.
        
        Returns: (adjusted_win, adjusted_stop)
        """
        key = f"{exchange}:{symbol}"
        outcomes = self.outcomes.get(key, [])
        
        if len(outcomes) < 20:
            return base_win_threshold, base_stop_threshold
        
        # Calculate win rate
        wins = sum(1 for o in outcomes if o['won'])
        win_rate = wins / len(outcomes)
        
        # Adjust thresholds based on win rate
        # High win rate (>60%): Tighter thresholds (capture more)
        # Low win rate (<40%): Wider thresholds (be more selective)
        
        if win_rate > 0.6:
            # High win rate - can be more aggressive
            win_multiplier = 0.8  # Take profit 20% earlier
            stop_multiplier = 1.2  # Wider stop (more patience)
        elif win_rate < 0.4:
            # Low win rate - be more conservative
            win_multiplier = 1.3  # Wait for bigger profit
            stop_multiplier = 0.8  # Tighter stop (cut losses faster)
        else:
            # Normal win rate - use base thresholds
            win_multiplier = 1.0
            stop_multiplier = 1.0
        
        adjusted_win = base_win_threshold * win_multiplier
        adjusted_stop = base_stop_threshold * stop_multiplier
        
        return adjusted_win, adjusted_stop
    
    def get_symbol_stats(self, symbol: str, exchange: str) -> Dict:
        """Get statistics for a symbol."""
        key = f"{exchange}:{symbol}"
        outcomes = self.outcomes.get(key, [])
        
        if not outcomes:
            return {'status': 'no_data'}
        
        wins = sum(1 for o in outcomes if o['won'])
        win_rate = wins / len(outcomes)
        
        win_profits = [o['profit_pct'] for o in outcomes if o['won']]
        loss_amounts = [abs(o['profit_pct']) for o in outcomes if not o['won']]
        
        avg_win = sum(win_profits) / len(win_profits) if win_profits else 0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0
        
        # Expected value
        ev = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return {
            'symbol': symbol,
            'exchange': exchange,
            'trades': len(outcomes),
            'wins': wins,
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'expected_value': ev,
            'is_profitable': ev > 0,
        }


# ═══════════════════════════════════════════════════════════════
# 🪙⚡ UNIFIED PENNY PROFIT TURBO ENGINE
# ═══════════════════════════════════════════════════════════════

class PennyProfitTurbo:
    """
    The unified turbo enhancement layer for penny profits.
    
    Usage:
        turbo = PennyProfitTurbo()
        
        # Feed live data
        turbo.record_ticker(exchange, symbol, bid, ask, price)
        
        # Get enhanced thresholds
        thresholds = turbo.get_enhanced_thresholds(exchange, symbol, trade_value)
        
        # Check for flash opportunities
        flashes = turbo.get_flash_opportunities()
    """
    
    def __init__(self):
        self.spread_tracker = RealTimeSpreadTracker()
        self.fee_optimizer = FeeTierOptimizer()
        self.compound_calc = CompoundAccelerator()
        self.flash_detector = FlashProfitDetector()
        self.prob_thresholds = ProbabilityWeightedThresholds()
        
        # Integration with existing systems
        self.adaptive_gate = None
        self.penny_engine = None
        
        self._load_integrations()
        
        logger.info("🪙⚡ Penny Profit TURBO initialized!")
    
    def _load_integrations(self):
        """Load existing profit engines for enhancement."""
        try:
            from aureon.utils.adaptive_prime_profit_gate import get_adaptive_gate
            self.adaptive_gate = get_adaptive_gate()
        except ImportError:
            pass
        
        try:
            from aureon.trading.penny_profit_engine import get_penny_engine
            self.penny_engine = get_penny_engine()
        except ImportError:
            pass
    
    def record_ticker(self, exchange: str, symbol: str, bid: float, ask: float, last_price: float):
        """Feed live ticker data to all enhancement systems."""
        # Update spread tracker
        self.spread_tracker.record_spread(exchange, symbol, bid, ask)
        
        # Update flash detector
        self.flash_detector.record_price(symbol, exchange, last_price)
    
    def record_trade(self, exchange: str, symbol: str, won: bool, profit_pct: float, 
                     volume_usd: float, duration_sec: float):
        """Record a completed trade to all learning systems."""
        # Fee tier tracking
        self.fee_optimizer.record_trade_volume(exchange, volume_usd)
        
        # Compound learning
        self.compound_calc.record_trade(profit_pct, won, duration_sec)
        
        # Probability tracking
        self.prob_thresholds.record_outcome(symbol, exchange, won, profit_pct)
    
    def get_enhanced_thresholds(
        self,
        exchange: str,
        symbol: str,
        trade_value: float,
        base_win_pct: float = 0.5,
        base_stop_pct: float = -0.3,
    ) -> Dict:
        """
        Get turbo-enhanced profit thresholds.
        
        Combines:
        - Real-time spread data
        - Your actual fee tier
        - Probability-adjusted targets
        - Compound optimization
        """
        exchange = exchange.lower()
        
        # 1. Get current spread
        current_spread = self.spread_tracker.get_current_spread(exchange, symbol)
        
        # 2. Get actual fee rate
        maker_fee = self.fee_optimizer.get_fees(exchange, is_maker=True)
        taker_fee = self.fee_optimizer.get_fees(exchange, is_maker=False)
        
        # 3. Get probability-adjusted thresholds
        adj_win, adj_stop = self.prob_thresholds.get_adjusted_threshold(
            symbol, exchange, base_win_pct, base_stop_pct
        )
        
        # 4. Calculate actual costs (using REAL data)
        slippage = 0.0005  # 0.05% estimate
        total_cost_rate = taker_fee + slippage + current_spread  # Per leg
        round_trip_cost = 2 * total_cost_rate * trade_value
        
        # 5. Required move for breakeven (with REAL costs)
        # r_be = (V + costs) / V - 1 = costs / V
        r_breakeven = (round_trip_cost / trade_value) if trade_value > 0 else 0.01
        
        # 6. Required move for target profit
        target_profit = 0.01  # $0.01 (the penny!)
        r_target = ((round_trip_cost + target_profit) / trade_value) if trade_value > 0 else 0.015
        
        # 7. Convert to gross P&L thresholds
        win_gte = trade_value * r_target
        stop_lte = -(trade_value * abs(adj_stop / 100))  # Use adjusted stop
        
        # 8. Get compound recommendation
        compound_rec = self.compound_calc.get_optimal_profit_target(r_target * 100)
        
        return {
            # Core thresholds
            'win_gte': round(win_gte, 6),
            'stop_lte': round(stop_lte, 6),
            'required_move_pct': round(r_target * 100, 4),
            
            # Costs (REAL data)
            'maker_fee': maker_fee,
            'taker_fee': taker_fee,
            'current_spread': current_spread,
            'slippage_estimate': slippage,
            'total_cost_rate': total_cost_rate,
            'round_trip_cost_usd': round(round_trip_cost, 6),
            
            # Optimization
            'fee_tier': self.fee_optimizer.current_tiers.get(exchange, {}).tier_name if hasattr(self.fee_optimizer.current_tiers.get(exchange, {}), 'tier_name') else 'Unknown',
            'probability_adjusted': True,
            'compound_recommendation': compound_rec.get('recommendation', r_target * 100),
            'kelly_fraction': self.compound_calc.get_kelly_fraction(),
            
            # Meta
            'exchange': exchange,
            'symbol': symbol,
            'trade_value': trade_value,
            'turbo_enhanced': True,
        }
    
    def get_flash_opportunities(self) -> List[FlashOpportunity]:
        """Get current flash profit opportunities."""
        return self.flash_detector.get_active_flashes()
    
    def get_enhanced_threshold(self, exchange: str, symbol: str, value_usd: float) -> Dict:
        """Get turbo-enhanced threshold for a single trade.
        
        Wrapper for get_enhanced_thresholds for convenience.
        """
        return self.get_enhanced_thresholds(exchange, symbol, value_usd)
    
    def get_flash_signal(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Get flash profit signal for a specific symbol.
        
        Returns:
            Dict with is_flash, direction, strength, or None if no flash
        """
        flashes = self.flash_detector.get_active_flashes()
        for flash in flashes:
            if flash.exchange.lower() == exchange.lower():
                # Match by symbol (flexible)
                if symbol and (flash.symbol == symbol or 
                               flash.symbol.replace('/', '') == symbol.replace('/', '')):
                    return {
                        'is_flash': True,
                        'direction': flash.direction,
                        'strength': abs(flash.move_pct) / 2.0,  # Normalize: 2% move = 1.0 strength
                        'move_pct': flash.move_pct,
                        'expires_at': flash.expires_at
                    }
        return {'is_flash': False, 'strength': 0, 'direction': 'neutral'}
    
    def get_compound_bonus(self, equity_usd: float, recent_win_rate: float) -> float:
        """Get compound acceleration bonus based on Kelly criterion.
        
        Returns:
            Bonus multiplier (0.0 to 0.5) based on win rate and equity
        """
        # Use the compound calculator's Kelly logic
        # High win rate + recent success = higher compound aggressiveness
        
        # Kelly fraction: f = p - (1-p)/b where b is odds (assume 1:1 for simplicity)
        # f = 2p - 1 (but capped at 0.5 for safety)
        win_rate = max(0.45, min(0.95, recent_win_rate))  # Clamp to reasonable range
        kelly = (2 * win_rate - 1)  # Range: -0.1 to 0.9
        kelly = max(0, kelly)  # Floor at 0
        
        # Scale to bonus range 0-0.5 (max 50% boost)
        # Only applies if we have recent wins
        if self.compound_calc.win_rate > 0.55:  # Above 55% = we're doing well
            bonus = min(0.5, kelly * 0.5)  # Half-Kelly scaled
        else:
            bonus = min(0.2, kelly * 0.3)  # Conservative if win rate low
        
        # Equity scaling: smaller equity = slightly more aggressive (growth mode)
        if equity_usd < 50:
            bonus *= 1.2  # 20% more aggressive for small accounts
        elif equity_usd > 500:
            bonus *= 0.8  # 20% more conservative for larger accounts
        
        return min(0.5, bonus)  # Cap at 50% boost
    
    def get_status(self) -> Dict:
        """Get turbo engine status."""
        return {
            'spread_tracker_symbols': len(self.spread_tracker.spread_history),
            'fee_optimizer_volumes': self.fee_optimizer.volume_30d,
            'compound_trades_recorded': len(self.compound_calc.trade_history),
            'compound_win_rate': self.compound_calc.win_rate,
            'compound_trades_per_hour': self.compound_calc.trades_per_hour,
            'flash_opportunities': len(self.flash_detector.active_flashes),
            'probability_symbols_tracked': len(self.prob_thresholds.outcomes),
        }
    
    def print_summary(self):
        """Print turbo engine summary."""
        print("\n" + "=" * 70)
        print("🪙⚡ PENNY PROFIT TURBO - ENHANCED INTELLIGENCE ⚡🪙")
        print("=" * 70)
        
        status = self.get_status()
        
        print(f"\n📊 REAL-TIME SPREADS:")
        for ex, spread in self.spread_tracker.exchange_avg_spreads.items():
            print(f"   {ex.upper()}: {spread*100:.4f}%")
        
        print(f"\n🎯 FEE TIERS:")
        for ex, tier in self.fee_optimizer.current_tiers.items():
            print(f"   {ex.upper()}: {tier.tier_name} (M:{tier.maker_fee*100:.3f}% / T:{tier.taker_fee*100:.3f}%)")
        
        print(f"\n🔥 COMPOUND STATS:")
        print(f"   Win Rate: {status['compound_win_rate']*100:.1f}%")
        print(f"   Trades/Hour: {status['compound_trades_per_hour']:.1f}")
        
        flashes = self.get_flash_opportunities()
        if flashes:
            print(f"\n⚡ ACTIVE FLASH OPPORTUNITIES ({len(flashes)}):")
            for flash in flashes[:5]:
                print(f"   {flash.exchange} {flash.symbol} {flash.direction} {flash.move_pct:+.2f}%")
        
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════
# SINGLETON & HELPERS
# ═══════════════════════════════════════════════════════════════

_turbo_engine: Optional[PennyProfitTurbo] = None


def get_penny_turbo() -> PennyProfitTurbo:
    """Get the singleton turbo engine."""
    global _turbo_engine
    if _turbo_engine is None:
        _turbo_engine = PennyProfitTurbo()
    return _turbo_engine


def turbo_thresholds(exchange: str, symbol: str, trade_value: float) -> Dict:
    """Quick access to turbo-enhanced thresholds."""
    return get_penny_turbo().get_enhanced_thresholds(exchange, symbol, trade_value)


if __name__ == '__main__':
    # Demo the turbo engine
    turbo = PennyProfitTurbo()
    
    # Simulate some data
    print("🪙⚡ PENNY PROFIT TURBO DEMO")
    print("=" * 60)
    
    # Simulate ticker feeds
    for i in range(20):
        turbo.record_ticker('binance', 'BTCUSDC', 94999 + i*10, 95001 + i*10, 95000 + i*10)
        turbo.record_ticker('kraken', 'BTCUSD', 94998 + i*10, 95002 + i*10, 95000 + i*10)
    
    # Simulate some trades
    turbo.record_trade('binance', 'BTCUSDC', True, 0.45, 10.0, 30.0)
    turbo.record_trade('binance', 'BTCUSDC', True, 0.38, 10.0, 25.0)
    turbo.record_trade('binance', 'BTCUSDC', False, -0.22, 10.0, 45.0)
    turbo.record_trade('binance', 'BTCUSDC', True, 0.52, 10.0, 20.0)
    
    # Get enhanced thresholds
    print("\n📊 ENHANCED THRESHOLDS for $10 trade on Binance BTCUSDC:")
    thresholds = turbo.get_enhanced_thresholds('binance', 'BTCUSDC', 10.0)
    for key, val in thresholds.items():
        if isinstance(val, float):
            print(f"   {key}: {val:.6f}")
        else:
            print(f"   {key}: {val}")
    
    # Print full summary
    turbo.print_summary()
    
    print("\n✅ Turbo engine ready for integration!")
    print("   Use: from penny_profit_turbo import get_penny_turbo")
