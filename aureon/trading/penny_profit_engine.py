#!/usr/bin/env python3
"""
🪙 PENNY PROFIT ENGINE
======================
The stupidest AND smartest trading strategy:
"Am I up by the exact amount needed for 1 penny profit? SELL."

Loads validated thresholds from penny_profit_thresholds.json and provides
simple dollar-based exit rules for each exchange.

NOW ENHANCED with Sandbox Evolution parameters from 454 generations of learning!

Gary Leckey & GitHub Copilot | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import os
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Sandbox learning file
SANDBOX_LEARNING_FILE = os.path.join(os.path.dirname(__file__), "sandbox_brain_learning.json")


@dataclass
class PennyThreshold:
    """Threshold for a specific trade size on an exchange."""
    trade_size: float
    total_cost: float
    win_gte: float      # Gross P&L >= this = TAKE PROFIT
    stop_lte: float     # Gross P&L <= this = STOP LOSS
    win_pct: float      # Price move % for win
    stop_pct: float     # Price move % for stop


class PennyProfitEngine:
    """
    The Penny Profit Engine.
    
    Usage:
        engine = PennyProfitEngine()
        
        # Check if position should exit
        action = engine.check_exit(
            exchange='binance',
            entry_value=7.50,
            current_value=7.55
        )
        
        if action == 'TAKE_PROFIT':
            sell()
        elif action == 'STOP_LOSS':
            sell()
    """
    
    def __init__(self, thresholds_file: str = 'penny_profit_thresholds.json'):
        self.thresholds: Dict = {}
        self.loaded = False
        self._load_thresholds(thresholds_file)
    
    def _load_thresholds(self, filepath: str):
        """Load thresholds from JSON file."""
        try:
            # Try multiple locations
            locations = [
                filepath,
                os.path.join(os.path.dirname(__file__), filepath),
                os.path.join(os.path.dirname(__file__), '..', filepath),
            ]
            
            for loc in locations:
                if os.path.exists(loc):
                    with open(loc, 'r') as f:
                        data = json.load(f)
                    self._parse_thresholds(data)
                    self.loaded = True
                    logger.info(f"🪙 Penny Profit Engine loaded from {loc}")
                    return
            
            # If no file found, use hardcoded defaults
            logger.warning("🪙 Using hardcoded penny profit thresholds")
            self._use_defaults()
            self.loaded = True
            
        except Exception as e:
            logger.error(f"🪙 Failed to load penny profit thresholds: {e}")
            self._use_defaults()
            self.loaded = True
    
    def _parse_thresholds(self, data: Dict):
        """Parse thresholds from loaded JSON."""
        # Handle both old and new format
        if 'thresholds' in data:
            # Old format with nested taker/maker
            for exchange, sizes in data['thresholds'].items():
                self.thresholds[exchange] = {}
                for size_key, values in sizes.items():
                    # Extract size from key like "$7.50"
                    size = float(size_key.replace('$', ''))

                    # Get taker values (worst case)
                    taker = values.get('taker', values)

                    total_cost = taker.get('total_costs', taker.get('cost', 0.03))

                    # Derive stop_lte from total_cost when missing.
                    # Stop loss should be proportional to trade size (≈0.5× costs).
                    default_stop = -(total_cost * 0.5)

                    self.thresholds[exchange][size] = PennyThreshold(
                        trade_size=size,
                        total_cost=total_cost,
                        win_gte=taker.get('min_gross_profit', taker.get('win_gte', 0.04)),
                        stop_lte=taker.get('max_gross_loss', taker.get('stop_lte', default_stop)),
                        win_pct=taker.get('min_price_move_pct', taker.get('win_pct', 0.5)),
                        stop_pct=taker.get('stop_pct', -0.3),
                    )
        
        elif 'exchanges' in data:
            # New format
            for exchange, info in data['exchanges'].items():
                self.thresholds[exchange] = {}
                for size_key, values in info.get('thresholds', {}).items():
                    size = float(size_key.replace('$', ''))
                    total_cost = values.get('cost', 0.03)
                    default_stop = -(total_cost * 0.5)
                    self.thresholds[exchange][size] = PennyThreshold(
                        trade_size=size,
                        total_cost=total_cost,
                        win_gte=values.get('win_gte', 0.04),
                        stop_lte=values.get('stop_lte', default_stop),
                        win_pct=values.get('win_pct', 0.5),
                        stop_pct=values.get('stop_pct', -0.3),
                    )
    
    def _use_defaults(self):
        """Use hardcoded default thresholds."""
        # Defaults for $7.50 trade size
        self.thresholds = {
            'binance': {
                5.0: PennyThreshold(5.0, 0.020, 0.030, -0.010, 0.60, -0.20),
                7.5: PennyThreshold(7.5, 0.030, 0.040, -0.015, 0.53, -0.20),
                10.0: PennyThreshold(10.0, 0.040, 0.050, -0.020, 0.50, -0.20),
                15.0: PennyThreshold(15.0, 0.060, 0.070, -0.030, 0.47, -0.20),
                20.0: PennyThreshold(20.0, 0.080, 0.090, -0.040, 0.45, -0.20),
            },
            'kraken': {
                5.0: PennyThreshold(5.0, 0.036, 0.046, -0.018, 0.92, -0.36),
                7.5: PennyThreshold(7.5, 0.054, 0.064, -0.027, 0.85, -0.36),
                10.0: PennyThreshold(10.0, 0.072, 0.082, -0.036, 0.82, -0.36),
                15.0: PennyThreshold(15.0, 0.108, 0.118, -0.054, 0.79, -0.36),
                20.0: PennyThreshold(20.0, 0.144, 0.154, -0.072, 0.77, -0.36),
            },
            'capital': {
                10.0: PennyThreshold(10.0, 0.044, 0.054, -0.022, 0.54, -0.22),
                15.0: PennyThreshold(15.0, 0.066, 0.076, -0.033, 0.51, -0.22),
                20.0: PennyThreshold(20.0, 0.088, 0.098, -0.044, 0.49, -0.22),
            },
            'alpaca': {
                5.0: PennyThreshold(5.0, 0.035, 0.045, -0.018, 0.90, -0.35),
                7.5: PennyThreshold(7.5, 0.053, 0.063, -0.026, 0.83, -0.35),
                10.0: PennyThreshold(10.0, 0.070, 0.080, -0.035, 0.80, -0.35),
            },
        }
    
    def get_threshold(self, exchange: str, entry_value: float) -> PennyThreshold:
        """
        Get the threshold for a given exchange and trade size.
        If entry_value exceeds the largest bucket, scales thresholds linearly
        so that fees and targets remain proportional to the actual trade size.
        """
        exchange = exchange.lower()

        if exchange not in self.thresholds:
            # Default to binance if unknown exchange
            exchange = 'binance'

        sizes = self.thresholds[exchange]
        max_bucket = max(sizes.keys())

        if entry_value <= max_bucket:
            # Within range — use closest bucket
            closest_size = min(sizes.keys(), key=lambda x: abs(x - entry_value))
            return sizes[closest_size]

        # Trade size exceeds largest bucket — scale linearly
        base = sizes[max_bucket]
        scale = entry_value / max_bucket

        return PennyThreshold(
            trade_size=entry_value,
            total_cost=base.total_cost * scale,
            win_gte=base.win_gte * scale,
            stop_lte=base.stop_lte * scale,
            win_pct=base.win_pct,       # percentages stay the same
            stop_pct=base.stop_pct,
        )
    
    def check_exit(self, exchange: str, entry_value: float, current_value: float) -> Tuple[str, float]:
        """
        Check if position should exit based on penny profit rules.
        
        Args:
            exchange: Exchange name (binance, kraken, etc.)
            entry_value: Entry value in USD
            current_value: Current value in USD
        
        Returns:
            Tuple of (action, gross_pnl) where action is:
            - 'TAKE_PROFIT': Hit penny profit target
            - 'STOP_LOSS': Hit stop loss
            - 'HOLD': Neither threshold hit
        """
        threshold = self.get_threshold(exchange, entry_value)
        gross_pnl = current_value - entry_value
        
        if gross_pnl >= threshold.win_gte:
            return ('TAKE_PROFIT', gross_pnl)
        elif gross_pnl <= threshold.stop_lte:
            return ('STOP_LOSS', gross_pnl)
        else:
            return ('HOLD', gross_pnl)
    
    def get_exit_prices(self, exchange: str, entry_price: float, quantity: float) -> Dict:
        """
        Calculate exact exit prices for TP and SL.
        
        Returns dict with tp_price and sl_price.
        """
        entry_value = entry_price * quantity
        threshold = self.get_threshold(exchange, entry_value)
        
        # TP: entry_value + win_gte = target_exit_value
        tp_value = entry_value + threshold.win_gte
        tp_price = tp_value / quantity if quantity > 0 else entry_price * (1 + threshold.win_pct / 100)
        
        # SL: entry_value + stop_lte = stop_exit_value
        sl_value = entry_value + threshold.stop_lte
        sl_price = sl_value / quantity if quantity > 0 else entry_price * (1 + threshold.stop_pct / 100)
        
        return {
            'entry_price': entry_price,
            'entry_value': entry_value,
            'tp_price': tp_price,
            'tp_value': tp_value,
            'tp_gross_target': threshold.win_gte,
            'sl_price': sl_price,
            'sl_value': sl_value,
            'sl_gross_target': threshold.stop_lte,
            'total_cost': threshold.total_cost,
            'net_profit_if_tp': 0.01,  # The penny!
        }
    
    def print_summary(self):
        """Print a summary of loaded thresholds."""
        print("=" * 60)
        print("🪙 PENNY PROFIT ENGINE - LOADED THRESHOLDS")
        print("=" * 60)
        
        for exchange, sizes in self.thresholds.items():
            print(f"\n🏦 {exchange.upper()}")
            print(f"   {'Size':>8} | {'Cost':>7} | {'TP >=':>8} | {'SL <=':>8} | {'Move%':>6}")
            print(f"   {'-'*8}-+-{'-'*7}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}")
            
            for size in sorted(sizes.keys()):
                t = sizes[size]
                print(f"   ${size:>7.2f} | ${t.total_cost:>6.3f} | ${t.win_gte:>7.3f} | ${t.stop_lte:>7.3f} | {t.win_pct:>5.2f}%")


# Singleton instance
_engine: Optional[PennyProfitEngine] = None


def get_penny_engine() -> PennyProfitEngine:
    """Get the singleton penny profit engine instance."""
    global _engine
    if _engine is None:
        _engine = PennyProfitEngine()
    return _engine


def check_penny_exit(exchange: str, entry_value: float, current_value: float) -> Tuple[str, float]:
    """
    Quick check for penny profit exit.
    
    Returns: (action, gross_pnl)
    - action: 'TAKE_PROFIT', 'STOP_LOSS', or 'HOLD'
    """
    return get_penny_engine().check_exit(exchange, entry_value, current_value)


# ═══════════════════════════════════════════════════════════════
# 🧬 SANDBOX EVOLVED EXIT CALCULATOR
# ═══════════════════════════════════════════════════════════════

class SandboxEvolvedExits:
    """
    Uses sandbox-evolved parameters (454 generations) for exit calculations.
    These parameters were learned through trial and error, not given.
    
    Evolved Parameters:
    - take_profit_pct: 1.82% (let winners run)
    - stop_loss_pct: 1.43% (wide stop)
    - position_size_pct: 12.2% of capital
    - min_coherence: 73% (only trade quality markets)
    """
    
    # Default evolved parameters (from 454 generations)
    DEFAULT_EVOLVED = {
        "take_profit_pct": 1.82,
        "stop_loss_pct": 1.43,
        "position_size_pct": 0.122,
        "min_coherence": 0.73,
        "min_volatility": 0.80,
        "max_volatility": 1.63,
    }
    
    def __init__(self):
        self.params = self.DEFAULT_EVOLVED.copy()
        self.generation = 0
        self.win_rate = 0.0
        self._load_from_sandbox()
    
    def _load_from_sandbox(self):
        """Load evolved parameters from sandbox learning file."""
        try:
            if os.path.exists(SANDBOX_LEARNING_FILE):
                with open(SANDBOX_LEARNING_FILE, 'r') as f:
                    data = json.load(f)
                
                best = data.get('best_parameters', {})
                if best:
                    self.params['take_profit_pct'] = best.get('take_profit_pct', self.params['take_profit_pct'])
                    self.params['stop_loss_pct'] = best.get('stop_loss_pct', self.params['stop_loss_pct'])
                    self.params['position_size_pct'] = best.get('position_size_pct', self.params['position_size_pct'])
                    self.params['min_coherence'] = best.get('min_coherence', self.params['min_coherence'])
                    self.params['min_volatility'] = best.get('min_volatility', self.params['min_volatility'])
                    self.params['max_volatility'] = best.get('max_volatility', self.params['max_volatility'])
                
                self.generation = data.get('generation', 0)
                self.win_rate = data.get('best_win_rate', 0)
                
                logger.info(f"🧬 Loaded sandbox evolution: Gen {self.generation}, {self.win_rate:.1f}% win rate")
        except Exception as e:
            logger.warning(f"Could not load sandbox evolution: {e}")
    
    def get_exit_prices_evolved(self, entry_price: float) -> Dict:
        """
        Calculate exit prices using sandbox-evolved percentages.
        
        Args:
            entry_price: Entry price per unit
            
        Returns:
            Dict with tp_price, sl_price, and evolved parameters
        """
        tp_pct = self.params['take_profit_pct']
        sl_pct = self.params['stop_loss_pct']
        
        tp_price = entry_price * (1 + tp_pct / 100)
        sl_price = entry_price * (1 - sl_pct / 100)
        
        return {
            'entry_price': entry_price,
            'tp_price': tp_price,
            'tp_pct': tp_pct,
            'sl_price': sl_price,
            'sl_pct': sl_pct,
            'evolved_generation': self.generation,
            'evolved_win_rate': self.win_rate,
        }
    
    def check_exit_evolved(self, entry_price: float, current_price: float) -> Tuple[str, float]:
        """
        Check if position should exit using sandbox-evolved parameters.
        
        Returns: (action, pnl_pct)
        - action: 'TAKE_PROFIT', 'STOP_LOSS', or 'HOLD'
        """
        pnl_pct = ((current_price / entry_price) - 1) * 100
        
        if pnl_pct >= self.params['take_profit_pct']:
            return ('TAKE_PROFIT', pnl_pct)
        elif pnl_pct <= -self.params['stop_loss_pct']:
            return ('STOP_LOSS', pnl_pct)
        else:
            return ('HOLD', pnl_pct)
    
    def should_enter(self, market_coherence: float, volatility: float) -> Tuple[bool, str]:
        """
        Check if market conditions are favorable for entry (evolved filters).
        
        Args:
            market_coherence: 0-1 estimate of market quality
            volatility: Recent volatility percentage
            
        Returns: (should_enter, reason)
        """
        if market_coherence < self.params['min_coherence']:
            return False, f"Coherence {market_coherence:.0%} < {self.params['min_coherence']:.0%}"
        
        if volatility < self.params['min_volatility']:
            return False, f"Volatility {volatility:.2f}% too low (min {self.params['min_volatility']:.2f}%)"
        
        if volatility > self.params['max_volatility']:
            return False, f"Volatility {volatility:.2f}% too high (max {self.params['max_volatility']:.2f}%)"
        
        return True, "✅ Entry conditions met (evolved filters)"
    
    def get_position_size(self, capital: float) -> float:
        """Get evolved optimal position size."""
        return capital * self.params['position_size_pct']


# Singleton for evolved exits
_evolved_exits: Optional[SandboxEvolvedExits] = None


def get_evolved_exits() -> SandboxEvolvedExits:
    """Get the singleton evolved exits calculator."""
    global _evolved_exits
    if _evolved_exits is None:
        _evolved_exits = SandboxEvolvedExits()
    return _evolved_exits


def check_evolved_exit(entry_price: float, current_price: float) -> Tuple[str, float]:
    """
    Quick check using sandbox-evolved exit parameters.
    
    Returns: (action, pnl_pct)
    """
    return get_evolved_exits().check_exit_evolved(entry_price, current_price)


if __name__ == '__main__':
    # Test the engine
    engine = PennyProfitEngine()
    engine.print_summary()
    
    print("\n" + "=" * 60)
    print("🧪 TEST: $7.50 trade on Binance")
    print("=" * 60)
    
    entry = 7.50
    
    # Test scenarios
    tests = [
        (7.54, "Up $0.04 - should TP"),
        (7.52, "Up $0.02 - should HOLD"),
        (7.48, "Down $0.02 - should STOP"),
        (7.485, "Down $0.015 - should STOP"),
        (7.50, "Flat - should HOLD"),
    ]
    
    for current, desc in tests:
        action, pnl = engine.check_exit('binance', entry, current)
        print(f"   {desc}: gross=${pnl:+.3f} → {action}")
    
    print("\n" + "=" * 60)
    print("📊 EXIT PRICES for $7.50 entry @ $1.00/unit (7.5 units)")
    print("=" * 60)
    
    prices = engine.get_exit_prices('binance', 1.00, 7.5)
    print(f"   Entry: ${prices['entry_price']:.4f} × 7.5 = ${prices['entry_value']:.2f}")
    print(f"   TP at: ${prices['tp_price']:.4f} × 7.5 = ${prices['tp_value']:.2f} (gross +${prices['tp_gross_target']:.3f})")
    print(f"   SL at: ${prices['sl_price']:.4f} × 7.5 = ${prices['sl_value']:.2f} (gross ${prices['sl_gross_target']:.3f})")
    print(f"   Net profit if TP: ${prices['net_profit_if_tp']:.2f} 🪙")
    
    # Test Sandbox Evolved Exits
    print("\n" + "=" * 60)
    print("🧬 SANDBOX EVOLVED EXITS (454 Generations of Learning)")
    print("=" * 60)
    
    evolved = get_evolved_exits()
    print(f"\n   Generation: {evolved.generation}")
    print(f"   Win Rate: {evolved.win_rate:.1f}%")
    print(f"   Take Profit: {evolved.params['take_profit_pct']:.2f}%")
    print(f"   Stop Loss: {evolved.params['stop_loss_pct']:.2f}%")
    print(f"   Position Size: {evolved.params['position_size_pct']*100:.1f}%")
    
    # Test evolved exits
    print("\n   Exit Tests @ $100 entry:")
    evolved_tests = [
        (101.82, f"Up {evolved.params['take_profit_pct']:.2f}% - should TP"),
        (101.00, "Up 1.00% - should HOLD"),
        (100.00, "Flat - should HOLD"),
        (98.57, f"Down {evolved.params['stop_loss_pct']:.2f}% - should STOP"),
    ]
    
    for current, desc in evolved_tests:
        action, pnl_pct = evolved.check_exit_evolved(100.0, current)
        print(f"   {desc}: {pnl_pct:+.2f}% → {action}")
    
    # Test entry filter
    print("\n   Entry Filter Tests:")
    entry_tests = [
        (0.75, 1.2, "Good coherence, good volatility"),
        (0.50, 1.2, "Low coherence"),
        (0.75, 0.3, "Low volatility"),
        (0.75, 2.5, "High volatility"),
    ]
    
    for coh, vol, desc in entry_tests:
        should, reason = evolved.should_enter(coh, vol)
        emoji = "✅" if should else "❌"
        print(f"   {emoji} {desc}: {reason}")


# ═══════════════════════════════════════════════════════════════
# 🧠 WISDOM GUIDANCE HELPER
# ═══════════════════════════════════════════════════════════════

_wisdom_engine = None

def get_wisdom_guidance(fear_greed: int = 50, btc_price: float = 100000, btc_change: float = 0.0) -> Dict:
    """
    Get wisdom guidance from the 11 civilizations.
    
    This is a convenience function that all trading systems can call
    to get the brain's consensus before making trades.
    
    Returns:
        Dict with:
        - consensus: 'BULLISH', 'BEARISH', or 'NEUTRAL'
        - action: 'ACCUMULATE', 'HOLD', 'REDUCE', etc.
        - confidence: 0-100%
        - permission: True if OK to trade, False if brain says no
        - message: Human-readable guidance
    """
    global _wisdom_engine
    
    try:
        if _wisdom_engine is None:
            from aureon.utils.aureon_miner_brain import WisdomCognitionEngine
            _wisdom_engine = WisdomCognitionEngine()
        
        reading = _wisdom_engine.get_unified_reading(fear_greed, btc_price, btc_change)
        consensus = reading.get('consensus', {})
        
        sentiment = consensus.get('sentiment', 'NEUTRAL')
        action = consensus.get('action', 'HOLD')
        confidence = consensus.get('confidence', 50)
        
        # Determine if brain gives permission to trade
        permission = True
        if sentiment == 'BEARISH' and confidence > 70:
            permission = False  # Strong bearish = don't buy
        elif action in ['EXIT_NOW', 'REDUCE', 'CAUTION']:
            permission = False
        
        return {
            'consensus': sentiment,
            'action': action,
            'confidence': confidence,
            'permission': permission,
            'bullish_votes': consensus.get('bullish_votes', 0),
            'bearish_votes': consensus.get('bearish_votes', 0),
            'neutral_votes': consensus.get('neutral_votes', 0),
            'message': f"🧠 {consensus.get('civilizations_consulted', 11)} civilizations: {sentiment} ({confidence}%) - {action}"
        }
    except Exception as e:
        logger.warning(f"Wisdom guidance unavailable: {e}")
        return {
            'consensus': 'NEUTRAL',
            'action': 'HOLD',
            'confidence': 50,
            'permission': True,  # Default to allow trading
            'bullish_votes': 0,
            'bearish_votes': 0,
            'neutral_votes': 0,
            'message': f"🧠 Wisdom unavailable: {e}"
        }
