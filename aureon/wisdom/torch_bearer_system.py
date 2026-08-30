#!/usr/bin/env python3
"""
+============================================================================+
|                                                                            |
|   TORCH BEARER SYSTEM - GUERRILLA WARFARE ON CANDLES                      |
|                                                                            |
|   "They think the candles are random. We see the campfire smoke."          |
|                                                                            |
|   PHILOSOPHY:                                                              |
|   The Apaches didn't fight in formation - they read the terrain,           |
|   waited for the right moment, struck fast, vanished. The candles          |
|   everyone calls "unpredictable" are actually broadcasting intent          |
|   at the micro-level. This system reads that intent.                       |
|                                                                            |
|   ARCHITECTURE:                                                            |
|   - Each coin gets its OWN TorchBearer instance (independent warrior)      |
|   - Each TorchBearer tracks momentum, energy, candle patterns              |
|   - Guerrilla logic: ambush entries, quick strikes, fast retreat           |
|   - Apache logic: read the terrain, stalk patiently, decisive strike      |
|   - Micro-scalps: seconds to minutes, long AND short                       |
|                                                                            |
|   WHILE THIS SYSTEM WORKS EACH COIN, THE OTHER SYSTEMS WORK THE MACHINE   |
|                                                                            |
+============================================================================+
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import json
import time
import math
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Deque, Any
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# THOUGHT BUS INTEGRATION
# ============================================================================
THOUGHT_BUS_AVAILABLE = False
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# CHIRP BUS INTEGRATION
CHIRP_BUS_AVAILABLE = False
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# ============================================================================
# SACRED CONSTANTS
# ============================================================================
PHI = 1.618033988749895
FIBONACCI_RATIOS = [0.236, 0.382, 0.500, 0.618, 0.786, 1.0, 1.618, 2.618]

# ============================================================================
# TORCH BEARER CONFIGURATION
# ============================================================================
CONFIG = {
    # Candle analysis
    'candle_window': 60,            # Number of micro-candles to track per coin
    'energy_decay': 0.95,           # Energy decays 5% per cycle (keeps it fresh)
    'min_candles_for_signal': 5,    # Need at least 5 candles before making calls

    # Guerrilla warfare thresholds
    'ambush_momentum_min': 0.15,    # 0.15% minimum momentum to set an ambush
    'strike_confidence_min': 0.60,  # 60% confidence needed to strike
    'retreat_loss_pct': 0.30,       # Retreat if losing 0.30%
    'victory_profit_pct': 0.20,     # Claim victory at 0.20% profit

    # Apache terrain reading
    'terrain_lookback': 20,         # Read 20 candles of terrain
    'stalk_patience_max': 30,       # Max 30 seconds of stalking before aborting
    'volume_surge_multiplier': 1.5, # 1.5x average volume = surge detected

    # Energy accumulation
    'energy_buy_threshold': 70.0,   # Energy > 70 = bullish accumulation
    'energy_sell_threshold': 30.0,  # Energy < 30 = bearish accumulation
    'energy_neutral_low': 40.0,     # 40-60 = neutral zone
    'energy_neutral_high': 60.0,

    # Fees
    'combined_fee_rate': 0.007,     # 0.70% round-trip (shared with war strategy)

    # Safety
    'max_active_positions': 5,      # Max 5 coins fighting simultaneously
    'position_size_usd': 10.0,     # $10 per position
}


# ============================================================================
# ENUMS
# ============================================================================

class TorchSignal(Enum):
    """What the torch bearer is signaling."""
    DARK = "DARK"               # No signal, watching
    AMBUSH_LONG = "AMBUSH_LONG" # Setting up long ambush
    AMBUSH_SHORT = "AMBUSH_SHORT"  # Setting up short ambush
    STRIKE_LONG = "STRIKE_LONG"    # Execute long NOW
    STRIKE_SHORT = "STRIKE_SHORT"  # Execute short NOW
    RETREAT = "RETREAT"            # Exit position, danger
    VICTORY = "VICTORY"            # Take profit, mission complete
    STALK = "STALK"                # Apache mode - watching, patient


class CandleFormation(Enum):
    """Guerrilla candle formations - what the "unpredictable" candles reveal."""
    SMOKE_SIGNAL = "SMOKE_SIGNAL"       # Volume spike with small body = accumulation
    AMBUSH_REVERSAL = "AMBUSH_REVERSAL" # Long wick into support/resistance = trap
    CHARGE = "CHARGE"                   # Big body, strong direction = momentum
    FEINT = "FEINT"                     # False breakout, wick rejects level
    CAMPFIRE = "CAMPFIRE"               # Consolidation, energy building
    STAMPEDE = "STAMPEDE"               # Multiple charge candles in sequence
    GHOST_TRAIL = "GHOST_TRAIL"         # Declining volume, direction fading


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MicroCandle:
    """A single micro-candle (second-level or minute-level)."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float = 0.0

    @property
    def body_pct(self) -> float:
        """Body size as percentage of price."""
        if self.open == 0:
            return 0.0
        return abs(self.close - self.open) / self.open * 100

    @property
    def upper_wick_pct(self) -> float:
        """Upper wick as percentage of price."""
        body_top = max(self.open, self.close)
        if body_top == 0:
            return 0.0
        return (self.high - body_top) / body_top * 100

    @property
    def lower_wick_pct(self) -> float:
        """Lower wick as percentage of price."""
        body_bottom = min(self.open, self.close)
        if body_bottom == 0:
            return 0.0
        return (body_bottom - self.low) / body_bottom * 100

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def range_pct(self) -> float:
        """Full candle range as percentage."""
        if self.low == 0:
            return 0.0
        return (self.high - self.low) / self.low * 100

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'body_pct': round(self.body_pct, 4),
            'bullish': self.is_bullish,
        }


@dataclass
class CoinEnergy:
    """Energy accumulation state for a single coin.

    Energy is the hidden force behind candle movements.
    High energy = strong directional conviction building.
    Low energy = exhaustion, reversal likely.
    """
    buy_energy: float = 50.0       # 0-100, starts neutral
    sell_energy: float = 50.0      # 0-100, starts neutral
    net_energy: float = 50.0       # buy_energy - sell_energy + 50 (centered at 50)
    accumulation_streak: int = 0   # Consecutive candles of same-direction energy
    peak_energy: float = 50.0      # Highest energy seen in current cycle
    trough_energy: float = 50.0    # Lowest energy seen in current cycle
    last_update: float = 0.0

    def update(self, candle: MicroCandle, avg_volume: float):
        """Update energy from a new candle."""
        now = time.time()
        decay = CONFIG['energy_decay']

        # Decay existing energy toward neutral
        self.buy_energy = 50.0 + (self.buy_energy - 50.0) * decay
        self.sell_energy = 50.0 + (self.sell_energy - 50.0) * decay

        # Volume multiplier - high volume amplifies energy
        vol_mult = 1.0
        if avg_volume > 0:
            vol_mult = min(3.0, candle.volume / avg_volume)

        # Body direction adds energy
        body_force = candle.body_pct * vol_mult

        if candle.is_bullish:
            self.buy_energy = min(100.0, self.buy_energy + body_force * 2.0)
            self.sell_energy = max(0.0, self.sell_energy - body_force * 0.5)
            if self.accumulation_streak >= 0:
                self.accumulation_streak += 1
            else:
                self.accumulation_streak = 1
        elif candle.is_bearish:
            self.sell_energy = min(100.0, self.sell_energy + body_force * 2.0)
            self.buy_energy = max(0.0, self.buy_energy - body_force * 0.5)
            if self.accumulation_streak <= 0:
                self.accumulation_streak -= 1
            else:
                self.accumulation_streak = -1

        # Wick rejection adds counter-energy (traps detected)
        if candle.upper_wick_pct > candle.body_pct * 1.5:
            # Long upper wick = sellers rejecting, bearish energy
            self.sell_energy = min(100.0, self.sell_energy + candle.upper_wick_pct * vol_mult)
        if candle.lower_wick_pct > candle.body_pct * 1.5:
            # Long lower wick = buyers absorbing, bullish energy
            self.buy_energy = min(100.0, self.buy_energy + candle.lower_wick_pct * vol_mult)

        # Calculate net energy (centered at 50)
        self.net_energy = max(0.0, min(100.0,
            50.0 + (self.buy_energy - self.sell_energy) / 2.0
        ))

        # Track peaks and troughs
        self.peak_energy = max(self.peak_energy, self.net_energy)
        self.trough_energy = min(self.trough_energy, self.net_energy)
        self.last_update = now

    def to_dict(self) -> Dict:
        return {
            'buy_energy': round(self.buy_energy, 2),
            'sell_energy': round(self.sell_energy, 2),
            'net_energy': round(self.net_energy, 2),
            'accumulation_streak': self.accumulation_streak,
            'peak': round(self.peak_energy, 2),
            'trough': round(self.trough_energy, 2),
        }


@dataclass
class TorchBearerSignal:
    """Output signal from a torch bearer for a specific coin."""
    symbol: str
    signal: TorchSignal
    confidence: float           # 0.0 - 1.0
    momentum_pct: float         # Current momentum percentage
    energy: float               # Net energy 0-100
    formation: CandleFormation  # What candle pattern was detected
    entry_price: float = 0.0   # Suggested entry price
    target_price: float = 0.0  # Suggested target
    stop_price: float = 0.0    # Suggested stop
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'signal': self.signal.value,
            'confidence': round(self.confidence, 4),
            'momentum_pct': round(self.momentum_pct, 4),
            'energy': round(self.energy, 2),
            'formation': self.formation.value,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'stop_price': self.stop_price,
            'reason': self.reason,
            'timestamp': self.timestamp,
        }


# ============================================================================
# CANDLE GUERRILLA - Reads the "unpredictable" candles
# ============================================================================

class CandleGuerrilla:
    """
    Guerrilla warfare on candlesticks.

    Everyone thinks micro-candles are noise. They're not.
    They're smoke signals from the battlefield.

    This class detects formations that reveal hidden intent:
    - SMOKE_SIGNAL: Volume spike + small body = someone accumulating quietly
    - AMBUSH_REVERSAL: Long wick rejection = trap set for breakout traders
    - CHARGE: Big body + direction = momentum is real
    - FEINT: False breakout, wick rejects = fake move
    - CAMPFIRE: Tight consolidation = energy building for explosion
    - STAMPEDE: Multiple charges in sequence = trend confirmed
    - GHOST_TRAIL: Declining volume + direction = movement is dying
    """

    @staticmethod
    def read_formation(candles: List[MicroCandle], avg_volume: float) -> Tuple[CandleFormation, float]:
        """Read the candle formation and return (formation, strength 0-1).

        Args:
            candles: Recent micro-candles (most recent last)
            avg_volume: Average volume for baseline comparison

        Returns:
            Tuple of (CandleFormation, strength 0.0-1.0)
        """
        if len(candles) < 3:
            return CandleFormation.CAMPFIRE, 0.1

        latest = candles[-1]
        prev = candles[-2]
        prev2 = candles[-3]

        vol_ratio = latest.volume / avg_volume if avg_volume > 0 else 1.0

        # SMOKE SIGNAL: High volume but small body = stealth accumulation
        if vol_ratio > CONFIG['volume_surge_multiplier'] and latest.body_pct < 0.05:
            strength = min(1.0, vol_ratio / 3.0)
            return CandleFormation.SMOKE_SIGNAL, strength

        # STAMPEDE: 3+ consecutive strong candles same direction
        if (latest.is_bullish and prev.is_bullish and prev2.is_bullish and
                latest.body_pct > 0.05 and prev.body_pct > 0.05):
            avg_body = (latest.body_pct + prev.body_pct + prev2.body_pct) / 3
            strength = min(1.0, avg_body / 0.3)
            return CandleFormation.STAMPEDE, strength

        if (latest.is_bearish and prev.is_bearish and prev2.is_bearish and
                latest.body_pct > 0.05 and prev.body_pct > 0.05):
            avg_body = (latest.body_pct + prev.body_pct + prev2.body_pct) / 3
            strength = min(1.0, avg_body / 0.3)
            return CandleFormation.STAMPEDE, strength

        # AMBUSH REVERSAL: Long wick > 2x body, rejecting a level
        if latest.upper_wick_pct > latest.body_pct * 2 and latest.is_bearish:
            strength = min(1.0, latest.upper_wick_pct / 0.2)
            return CandleFormation.AMBUSH_REVERSAL, strength

        if latest.lower_wick_pct > latest.body_pct * 2 and latest.is_bullish:
            strength = min(1.0, latest.lower_wick_pct / 0.2)
            return CandleFormation.AMBUSH_REVERSAL, strength

        # FEINT: Candle broke previous high/low but closed back inside
        if (latest.high > prev.high and latest.close < prev.high and latest.is_bearish):
            strength = min(1.0, (latest.high - prev.high) / max(0.001, latest.range_pct) * 5)
            return CandleFormation.FEINT, strength

        if (latest.low < prev.low and latest.close > prev.low and latest.is_bullish):
            strength = min(1.0, (prev.low - latest.low) / max(0.001, latest.range_pct) * 5)
            return CandleFormation.FEINT, strength

        # CHARGE: Strong body, clear direction
        if latest.body_pct > 0.1 and latest.body_pct > latest.upper_wick_pct + latest.lower_wick_pct:
            strength = min(1.0, latest.body_pct / 0.3)
            return CandleFormation.CHARGE, strength

        # GHOST TRAIL: Direction maintained but volume dying
        if vol_ratio < 0.5 and latest.body_pct > 0.02:
            strength = min(1.0, (1.0 - vol_ratio))
            return CandleFormation.GHOST_TRAIL, strength

        # CAMPFIRE: Nothing strong happening, energy building
        range_compression = 1.0
        if len(candles) >= 5:
            ranges = [c.range_pct for c in candles[-5:]]
            if ranges[0] > 0:
                range_compression = ranges[-1] / ranges[0]
        strength = max(0.1, min(1.0, 1.0 - range_compression))
        return CandleFormation.CAMPFIRE, strength


# ============================================================================
# APACHE TRACKER - Patient terrain reading
# ============================================================================

class ApacheTracker:
    """
    Apache terrain reading logic.

    The Apache didn't charge blindly - they read the land first:
    1. Find the high ground (support/resistance levels)
    2. Watch the movement patterns (momentum flow)
    3. Wait for the prey to enter the kill zone
    4. Strike decisively, then disappear

    This translates to trading:
    1. Identify micro support/resistance from recent candles
    2. Track momentum direction and strength
    3. Wait for price to enter a zone with high probability
    4. Execute and exit quickly
    """

    @staticmethod
    def read_terrain(candles: List[MicroCandle]) -> Dict[str, Any]:
        """Read the micro-terrain from recent candles.

        Returns dict with:
            - support: nearest support level
            - resistance: nearest resistance level
            - trend: 'up', 'down', or 'sideways'
            - trend_strength: 0-1
            - momentum_pct: recent momentum as percentage
            - volatility: recent volatility measure
            - kill_zone: price range where a strike has highest probability
        """
        if len(candles) < 5:
            price = candles[-1].close if candles else 0
            return {
                'support': price * 0.999,
                'resistance': price * 1.001,
                'trend': 'sideways',
                'trend_strength': 0.0,
                'momentum_pct': 0.0,
                'volatility': 0.0,
                'kill_zone_low': price * 0.999,
                'kill_zone_high': price * 1.001,
            }

        lookback = candles[-CONFIG['terrain_lookback']:]

        # Find support and resistance from recent swing points
        highs = [c.high for c in lookback]
        lows = [c.low for c in lookback]
        closes = [c.close for c in lookback]

        resistance = max(highs)
        support = min(lows)
        current_price = closes[-1]

        # Trend detection using linear regression slope approximation
        n = len(closes)
        x_mean = (n - 1) / 2.0
        y_mean = sum(closes) / n
        numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0
        slope_pct = (slope / y_mean * 100) if y_mean != 0 else 0

        if slope_pct > 0.01:
            trend = 'up'
        elif slope_pct < -0.01:
            trend = 'down'
        else:
            trend = 'sideways'

        trend_strength = min(1.0, abs(slope_pct) / 0.1)

        # Momentum: percentage change over lookback
        if closes[0] > 0:
            momentum_pct = (closes[-1] - closes[0]) / closes[0] * 100
        else:
            momentum_pct = 0.0

        # Volatility: average range as percentage
        ranges = [c.range_pct for c in lookback]
        volatility = sum(ranges) / len(ranges) if ranges else 0.0

        # Kill zone: Fibonacci retracement of recent range
        price_range = resistance - support
        if trend == 'up':
            # In uptrend, kill zone is the 38.2%-61.8% retracement (buy dip)
            kill_zone_low = resistance - price_range * 0.618
            kill_zone_high = resistance - price_range * 0.382
        elif trend == 'down':
            # In downtrend, kill zone is 38.2%-61.8% retracement (sell rally)
            kill_zone_low = support + price_range * 0.382
            kill_zone_high = support + price_range * 0.618
        else:
            # Sideways: mid-range
            mid = (support + resistance) / 2
            kill_zone_low = mid - price_range * 0.1
            kill_zone_high = mid + price_range * 0.1

        return {
            'support': support,
            'resistance': resistance,
            'trend': trend,
            'trend_strength': trend_strength,
            'momentum_pct': momentum_pct,
            'volatility': volatility,
            'kill_zone_low': kill_zone_low,
            'kill_zone_high': kill_zone_high,
        }

    @staticmethod
    def is_in_kill_zone(price: float, terrain: Dict[str, Any]) -> bool:
        """Check if current price is in the Apache kill zone."""
        return terrain['kill_zone_low'] <= price <= terrain['kill_zone_high']


# ============================================================================
# TORCH BEARER - One per coin, independent warrior
# ============================================================================

class TorchBearer:
    """
    A single torch bearer assigned to ONE coin.

    Each torch bearer:
    - Collects micro-candles for its coin
    - Tracks energy accumulation
    - Reads candle formations (guerrilla)
    - Reads terrain (Apache)
    - Produces signals: STRIKE_LONG, STRIKE_SHORT, RETREAT, etc.

    The torch bearer works independently - it doesn't know or care
    what the other torch bearers are doing. It only watches its coin.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.candles: Deque[MicroCandle] = deque(maxlen=CONFIG['candle_window'])
        self.energy = CoinEnergy()
        self.signal = TorchSignal.DARK
        self.confidence = 0.0
        self.last_formation = CandleFormation.CAMPFIRE
        self.formation_strength = 0.0

        # Position tracking
        self.in_position = False
        self.position_side: Optional[str] = None  # 'long' or 'short'
        self.entry_price: float = 0.0
        self.entry_time: float = 0.0

        # Performance tracking
        self.total_strikes: int = 0
        self.victories: int = 0
        self.retreats: int = 0
        self.total_pnl_pct: float = 0.0

        # Stalking state (Apache patience)
        self.stalk_start: float = 0.0
        self.stalking: bool = False
        self.stalk_direction: Optional[str] = None  # 'long' or 'short'

        # Terrain cache
        self._terrain: Dict[str, Any] = {}
        self._terrain_time: float = 0

        self.created_at = time.time()

    @property
    def avg_volume(self) -> float:
        """Average volume across all tracked candles."""
        if not self.candles:
            return 0.0
        vols = [c.volume for c in self.candles]
        return sum(vols) / len(vols)

    @property
    def current_price(self) -> float:
        """Latest close price."""
        return self.candles[-1].close if self.candles else 0.0

    @property
    def win_rate(self) -> float:
        """Win rate percentage."""
        if self.total_strikes == 0:
            return 0.0
        return (self.victories / self.total_strikes) * 100

    def feed_candle(self, candle: MicroCandle) -> Optional[TorchBearerSignal]:
        """Feed a new micro-candle to this torch bearer.

        This is the main entry point. Each new candle triggers:
        1. Energy update
        2. Formation reading (guerrilla)
        3. Terrain reading (Apache)
        4. Signal generation

        Returns a TorchBearerSignal if there's something to report, None if DARK.
        """
        self.candles.append(candle)

        # Not enough data yet
        if len(self.candles) < CONFIG['min_candles_for_signal']:
            return None

        # Update energy
        self.energy.update(candle, self.avg_volume)

        # Read formation (guerrilla)
        candle_list = list(self.candles)
        self.last_formation, self.formation_strength = CandleGuerrilla.read_formation(
            candle_list, self.avg_volume
        )

        # Read terrain (Apache) - cache for 5 seconds
        now = time.time()
        if now - self._terrain_time > 5.0:
            self._terrain = ApacheTracker.read_terrain(candle_list)
            self._terrain_time = now

        # If in position, check for retreat or victory
        if self.in_position:
            return self._evaluate_position(candle)

        # Not in position - look for ambush or strike opportunity
        return self._evaluate_opportunity(candle)

    def _evaluate_position(self, candle: MicroCandle) -> Optional[TorchBearerSignal]:
        """Evaluate an existing position - retreat or claim victory?"""
        if self.entry_price == 0:
            return None

        if self.position_side == 'long':
            pnl_pct = (candle.close - self.entry_price) / self.entry_price * 100
        else:
            pnl_pct = (self.entry_price - candle.close) / self.entry_price * 100

        # VICTORY: Target reached
        if pnl_pct >= CONFIG['victory_profit_pct']:
            self.victories += 1
            self.total_pnl_pct += pnl_pct - (CONFIG['combined_fee_rate'] * 100)
            self._close_position()
            return TorchBearerSignal(
                symbol=self.symbol,
                signal=TorchSignal.VICTORY,
                confidence=0.95,
                momentum_pct=self._terrain.get('momentum_pct', 0),
                energy=self.energy.net_energy,
                formation=self.last_formation,
                reason=f"Victory! +{pnl_pct:.3f}% gross, position closed",
            )

        # RETREAT: Stop hit or formation turned against us
        if pnl_pct <= -CONFIG['retreat_loss_pct']:
            self.retreats += 1
            self.total_pnl_pct += pnl_pct - (CONFIG['combined_fee_rate'] * 100)
            self._close_position()
            return TorchBearerSignal(
                symbol=self.symbol,
                signal=TorchSignal.RETREAT,
                confidence=0.90,
                momentum_pct=self._terrain.get('momentum_pct', 0),
                energy=self.energy.net_energy,
                formation=self.last_formation,
                reason=f"Retreat! {pnl_pct:.3f}% loss, cutting losses",
            )

        # GHOST TRAIL while in position = momentum dying, consider early exit
        if self.last_formation == CandleFormation.GHOST_TRAIL and self.formation_strength > 0.6:
            if pnl_pct > 0:
                self.victories += 1
                self.total_pnl_pct += pnl_pct - (CONFIG['combined_fee_rate'] * 100)
                self._close_position()
                return TorchBearerSignal(
                    symbol=self.symbol,
                    signal=TorchSignal.RETREAT,
                    confidence=0.70,
                    momentum_pct=self._terrain.get('momentum_pct', 0),
                    energy=self.energy.net_energy,
                    formation=self.last_formation,
                    reason=f"Ghost trail detected, securing +{pnl_pct:.3f}% before fade",
                )

        return None  # Hold position

    def _evaluate_opportunity(self, candle: MicroCandle) -> Optional[TorchBearerSignal]:
        """Look for an ambush or strike opportunity."""
        terrain = self._terrain
        momentum = terrain.get('momentum_pct', 0)
        trend = terrain.get('trend', 'sideways')
        trend_strength = terrain.get('trend_strength', 0)
        net_energy = self.energy.net_energy

        # ---------------------------------------------------------------
        # STAMPEDE DETECTION - strongest signal, ride the charge
        # ---------------------------------------------------------------
        if self.last_formation == CandleFormation.STAMPEDE:
            candle_list = list(self.candles)
            latest = candle_list[-1]

            if latest.is_bullish and net_energy > CONFIG['energy_neutral_high']:
                confidence = min(0.95, self.formation_strength * 0.6 + trend_strength * 0.4)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('long', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_LONG,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.STAMPEDE,
                        entry_price=candle.close,
                        target_price=candle.close * (1 + CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.close * (1 - CONFIG['retreat_loss_pct'] / 100),
                        reason=f"STAMPEDE detected! Bullish charge, energy={net_energy:.0f}",
                    )

            elif latest.is_bearish and net_energy < CONFIG['energy_neutral_low']:
                confidence = min(0.95, self.formation_strength * 0.6 + trend_strength * 0.4)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('short', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_SHORT,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.STAMPEDE,
                        entry_price=candle.close,
                        target_price=candle.close * (1 - CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.close * (1 + CONFIG['retreat_loss_pct'] / 100),
                        reason=f"STAMPEDE detected! Bearish charge, energy={net_energy:.0f}",
                    )

        # ---------------------------------------------------------------
        # AMBUSH REVERSAL - trap detected, trade the reversal
        # ---------------------------------------------------------------
        if self.last_formation == CandleFormation.AMBUSH_REVERSAL:
            candle_list = list(self.candles)
            latest = candle_list[-1]

            # Long wick rejection at top = short signal
            if latest.upper_wick_pct > latest.body_pct * 2 and net_energy < CONFIG['energy_neutral_high']:
                confidence = min(0.90, self.formation_strength * 0.5 + 0.3)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('short', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_SHORT,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.AMBUSH_REVERSAL,
                        entry_price=candle.close,
                        target_price=candle.close * (1 - CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.high * 1.001,
                        reason="Ambush reversal! Upper wick rejection, sellers defending",
                    )

            # Long wick rejection at bottom = long signal
            if latest.lower_wick_pct > latest.body_pct * 2 and net_energy > CONFIG['energy_neutral_low']:
                confidence = min(0.90, self.formation_strength * 0.5 + 0.3)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('long', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_LONG,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.AMBUSH_REVERSAL,
                        entry_price=candle.close,
                        target_price=candle.close * (1 + CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.low * 0.999,
                        reason="Ambush reversal! Lower wick rejection, buyers absorbing",
                    )

        # ---------------------------------------------------------------
        # SMOKE SIGNAL + ENERGY DIVERGENCE - stealth accumulation
        # ---------------------------------------------------------------
        if self.last_formation == CandleFormation.SMOKE_SIGNAL:
            # High volume but small body = someone is loading up
            if net_energy > CONFIG['energy_buy_threshold']:
                confidence = min(0.85, self.formation_strength * 0.4 + 0.3)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('long', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_LONG,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.SMOKE_SIGNAL,
                        entry_price=candle.close,
                        target_price=candle.close * (1 + CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.close * (1 - CONFIG['retreat_loss_pct'] / 100),
                        reason=f"Smoke signal! Stealth BUY accumulation, energy={net_energy:.0f}",
                    )
            elif net_energy < CONFIG['energy_sell_threshold']:
                confidence = min(0.85, self.formation_strength * 0.4 + 0.3)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('short', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_SHORT,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.SMOKE_SIGNAL,
                        entry_price=candle.close,
                        target_price=candle.close * (1 - CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.close * (1 + CONFIG['retreat_loss_pct'] / 100),
                        reason=f"Smoke signal! Stealth SELL distribution, energy={net_energy:.0f}",
                    )

        # ---------------------------------------------------------------
        # CHARGE + APACHE KILL ZONE - strong move into optimal zone
        # ---------------------------------------------------------------
        if self.last_formation == CandleFormation.CHARGE:
            in_zone = ApacheTracker.is_in_kill_zone(candle.close, terrain)

            if in_zone and trend == 'up' and net_energy > CONFIG['energy_neutral_high']:
                confidence = min(0.88, self.formation_strength * 0.5 + trend_strength * 0.3)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('long', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_LONG,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.CHARGE,
                        entry_price=candle.close,
                        target_price=terrain.get('resistance', candle.close * 1.003),
                        stop_price=terrain.get('support', candle.close * 0.997),
                        reason=f"Charge into Apache kill zone! Trend=UP, energy={net_energy:.0f}",
                    )

            if in_zone and trend == 'down' and net_energy < CONFIG['energy_neutral_low']:
                confidence = min(0.88, self.formation_strength * 0.5 + trend_strength * 0.3)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('short', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_SHORT,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.CHARGE,
                        entry_price=candle.close,
                        target_price=terrain.get('support', candle.close * 0.997),
                        stop_price=terrain.get('resistance', candle.close * 1.003),
                        reason=f"Charge into Apache kill zone! Trend=DOWN, energy={net_energy:.0f}",
                    )

        # ---------------------------------------------------------------
        # FEINT DETECTION - fade the false breakout
        # ---------------------------------------------------------------
        if self.last_formation == CandleFormation.FEINT and self.formation_strength > 0.5:
            candle_list = list(self.candles)
            latest = candle_list[-1]
            prev = candle_list[-2]

            # False breakout upward, fade it short
            if latest.high > prev.high and latest.close < prev.high and latest.is_bearish:
                confidence = min(0.80, self.formation_strength * 0.5 + 0.2)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('short', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_SHORT,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.FEINT,
                        entry_price=candle.close,
                        target_price=candle.close * (1 - CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.high * 1.001,
                        reason="Feint detected! False breakout high, fading short",
                    )

            # False breakout downward, fade it long
            if latest.low < prev.low and latest.close > prev.low and latest.is_bullish:
                confidence = min(0.80, self.formation_strength * 0.5 + 0.2)
                if confidence >= CONFIG['strike_confidence_min']:
                    self._open_position('long', candle.close)
                    return TorchBearerSignal(
                        symbol=self.symbol,
                        signal=TorchSignal.STRIKE_LONG,
                        confidence=confidence,
                        momentum_pct=momentum,
                        energy=net_energy,
                        formation=CandleFormation.FEINT,
                        entry_price=candle.close,
                        target_price=candle.close * (1 + CONFIG['victory_profit_pct'] / 100),
                        stop_price=candle.low * 0.999,
                        reason="Feint detected! False breakout low, fading long",
                    )

        # ---------------------------------------------------------------
        # CAMPFIRE - energy building, start stalking
        # ---------------------------------------------------------------
        if self.last_formation == CandleFormation.CAMPFIRE and self.formation_strength > 0.5:
            if abs(net_energy - 50) > 15:
                direction = 'long' if net_energy > 50 else 'short'
                if not self.stalking:
                    self.stalking = True
                    self.stalk_start = time.time()
                    self.stalk_direction = direction
                return TorchBearerSignal(
                    symbol=self.symbol,
                    signal=TorchSignal.STALK,
                    confidence=0.40,
                    momentum_pct=momentum,
                    energy=net_energy,
                    formation=CandleFormation.CAMPFIRE,
                    reason=f"Campfire detected, stalking {direction}. Energy building...",
                )
            else:
                # Reset stalk if energy went neutral
                self.stalking = False

        # Nothing actionable
        return None

    def _open_position(self, side: str, price: float):
        """Record position entry."""
        self.in_position = True
        self.position_side = side
        self.entry_price = price
        self.entry_time = time.time()
        self.total_strikes += 1
        self.stalking = False

    def _close_position(self):
        """Record position exit."""
        self.in_position = False
        self.position_side = None
        self.entry_price = 0.0
        self.entry_time = 0.0

    def get_status(self) -> Dict:
        """Get full status of this torch bearer."""
        return {
            'symbol': self.symbol,
            'signal': self.signal.value,
            'confidence': round(self.confidence, 4),
            'candles_collected': len(self.candles),
            'energy': self.energy.to_dict(),
            'formation': self.last_formation.value,
            'formation_strength': round(self.formation_strength, 4),
            'terrain': self._terrain,
            'in_position': self.in_position,
            'position_side': self.position_side,
            'entry_price': self.entry_price,
            'performance': {
                'total_strikes': self.total_strikes,
                'victories': self.victories,
                'retreats': self.retreats,
                'win_rate': round(self.win_rate, 1),
                'total_pnl_pct': round(self.total_pnl_pct, 4),
            },
        }


# ============================================================================
# TORCH BEARER SYSTEM - The Orchestrator
# ============================================================================

class TorchBearerSystem:
    """
    The Torch Bearer System orchestrator.

    Manages one TorchBearer per coin. Each bearer works independently
    on its assigned coin while the other Aureon systems work the machine.

    Usage:
        system = TorchBearerSystem()

        # Feed candles as they arrive (per-coin)
        signal = system.feed_candle('BTC/USD', candle_data)
        signal = system.feed_candle('ETH/USD', candle_data)
        signal = system.feed_candle('SOL/USD', candle_data)

        # Get all active signals
        signals = system.get_active_signals()

        # Get full system status
        status = system.get_system_status()
    """

    def __init__(self):
        self.bearers: Dict[str, TorchBearer] = {}
        self.active_signals: List[TorchBearerSignal] = []
        self.signal_history: Deque[TorchBearerSignal] = deque(maxlen=1000)
        self.started_at = time.time()
        self.total_signals_generated = 0

        # Publish to thought bus
        self._publish_thought("Torch Bearer System ONLINE. Guerrilla warfare on candles begins.")

        logger.info("Torch Bearer System initialized - per-coin guerrilla micro-scalping engine")

    def _publish_thought(self, content: str):
        """Publish a thought to the thought bus."""
        if THOUGHT_BUS_AVAILABLE:
            try:
                bus = get_thought_bus()
                bus.publish(Thought(
                    system="TorchBearerSystem",
                    content=content,
                    timestamp=time.time(),
                ))
            except Exception:
                pass

    def _get_or_create_bearer(self, symbol: str) -> TorchBearer:
        """Get existing bearer or create a new one for this coin."""
        if symbol not in self.bearers:
            self.bearers[symbol] = TorchBearer(symbol)
            logger.info(f"New torch bearer deployed for {symbol}")
        return self.bearers[symbol]

    def feed_candle(self, symbol: str, candle_data: Dict) -> Optional[TorchBearerSignal]:
        """Feed a candle to the appropriate torch bearer.

        Args:
            symbol: The coin symbol (e.g. 'BTC/USD')
            candle_data: Dict with keys: timestamp, open, high, low, close, volume
                         (and optionally vwap)

        Returns:
            TorchBearerSignal if a signal was generated, None otherwise.
        """
        bearer = self._get_or_create_bearer(symbol)

        candle = MicroCandle(
            timestamp=candle_data.get('timestamp', time.time()),
            open=float(candle_data.get('open', 0)),
            high=float(candle_data.get('high', 0)),
            low=float(candle_data.get('low', 0)),
            close=float(candle_data.get('close', 0)),
            volume=float(candle_data.get('volume', 0)),
            vwap=float(candle_data.get('vwap', 0)),
        )

        signal = bearer.feed_candle(candle)

        if signal and signal.signal not in (TorchSignal.DARK, TorchSignal.STALK):
            self.active_signals.append(signal)
            self.signal_history.append(signal)
            self.total_signals_generated += 1

            # Publish to thought bus
            self._publish_thought(
                f"{symbol}: {signal.signal.value} | "
                f"formation={signal.formation.value} | "
                f"confidence={signal.confidence:.0%} | "
                f"energy={signal.energy:.0f} | "
                f"{signal.reason}"
            )

            logger.info(
                f"TORCH [{symbol}] {signal.signal.value} "
                f"confidence={signal.confidence:.0%} "
                f"formation={signal.formation.value} "
                f"energy={signal.energy:.0f}"
            )

        return signal

    def feed_candles_batch(self, candles_by_symbol: Dict[str, List[Dict]]) -> List[TorchBearerSignal]:
        """Feed multiple candles for multiple symbols at once.

        Args:
            candles_by_symbol: Dict mapping symbol -> list of candle dicts

        Returns:
            List of all signals generated across all coins.
        """
        all_signals = []
        for symbol, candle_list in candles_by_symbol.items():
            for candle_data in candle_list:
                signal = self.feed_candle(symbol, candle_data)
                if signal:
                    all_signals.append(signal)
        return all_signals

    def get_active_signals(self, min_confidence: float = 0.0) -> List[TorchBearerSignal]:
        """Get all active (recent) signals above minimum confidence.

        Signals older than 60 seconds are pruned.
        """
        now = time.time()
        cutoff = now - 60.0
        self.active_signals = [s for s in self.active_signals if s.timestamp > cutoff]

        if min_confidence > 0:
            return [s for s in self.active_signals if s.confidence >= min_confidence]
        return list(self.active_signals)

    def get_strike_signals(self) -> List[TorchBearerSignal]:
        """Get only STRIKE signals (ready to execute trades)."""
        return [
            s for s in self.get_active_signals()
            if s.signal in (TorchSignal.STRIKE_LONG, TorchSignal.STRIKE_SHORT)
        ]

    def get_bearer_status(self, symbol: str) -> Optional[Dict]:
        """Get status of a specific coin's torch bearer."""
        bearer = self.bearers.get(symbol)
        if bearer:
            return bearer.get_status()
        return None

    def get_all_bearer_statuses(self) -> Dict[str, Dict]:
        """Get status of all torch bearers."""
        return {symbol: bearer.get_status() for symbol, bearer in self.bearers.items()}

    def get_coins_in_position(self) -> List[str]:
        """Get list of coins currently in active positions."""
        return [
            symbol for symbol, bearer in self.bearers.items()
            if bearer.in_position
        ]

    def get_energy_rankings(self) -> List[Dict]:
        """Rank all coins by energy (highest bullish energy first)."""
        rankings = []
        for symbol, bearer in self.bearers.items():
            if len(bearer.candles) >= CONFIG['min_candles_for_signal']:
                rankings.append({
                    'symbol': symbol,
                    'net_energy': bearer.energy.net_energy,
                    'buy_energy': bearer.energy.buy_energy,
                    'sell_energy': bearer.energy.sell_energy,
                    'streak': bearer.energy.accumulation_streak,
                    'momentum_pct': bearer._terrain.get('momentum_pct', 0),
                })
        rankings.sort(key=lambda x: abs(x['net_energy'] - 50), reverse=True)
        return rankings

    def get_system_status(self) -> Dict:
        """Get full system status."""
        active_positions = self.get_coins_in_position()
        total_strikes = sum(b.total_strikes for b in self.bearers.values())
        total_victories = sum(b.victories for b in self.bearers.values())
        total_retreats = sum(b.retreats for b in self.bearers.values())

        return {
            'system': 'TorchBearerSystem',
            'status': 'ACTIVE',
            'uptime_seconds': round(time.time() - self.started_at, 1),
            'coins_tracked': len(self.bearers),
            'coins_in_position': len(active_positions),
            'active_positions': active_positions,
            'total_signals': self.total_signals_generated,
            'active_signals': len(self.get_active_signals()),
            'performance': {
                'total_strikes': total_strikes,
                'victories': total_victories,
                'retreats': total_retreats,
                'win_rate': round(
                    (total_victories / total_strikes * 100) if total_strikes > 0 else 0, 1
                ),
            },
            'energy_rankings': self.get_energy_rankings()[:10],  # Top 10
            'config': {
                'strike_confidence_min': CONFIG['strike_confidence_min'],
                'victory_target_pct': CONFIG['victory_profit_pct'],
                'retreat_stop_pct': CONFIG['retreat_loss_pct'],
                'position_size_usd': CONFIG['position_size_usd'],
            },
        }

    def save_state(self, filepath: str = 'state/torch_bearer_state.json'):
        """Save system state to disk."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            state = {
                'timestamp': time.time(),
                'system_status': self.get_system_status(),
                'bearers': {
                    symbol: bearer.get_status()
                    for symbol, bearer in self.bearers.items()
                },
                'recent_signals': [
                    s.to_dict() for s in list(self.signal_history)[-50:]
                ],
            }
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.debug(f"Torch Bearer state saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")


# ============================================================================
# STANDALONE USAGE
# ============================================================================
