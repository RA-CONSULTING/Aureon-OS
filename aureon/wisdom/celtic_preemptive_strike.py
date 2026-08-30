#!/usr/bin/env python3
"""
☘️⚡ CELTIC PREEMPTIVE STRIKE SYSTEM ⚡☘️
═══════════════════════════════════════════════════════════════════════════════
                    MOVE BEFORE THE MARKET REACTS
═══════════════════════════════════════════════════════════════════════════════

"The art of war teaches us to rely not on the likelihood of the enemy's
not coming, but on our own readiness to receive him."
                                                    - Sun Tzu (via Celtic adaptation)

THE CELTIC PREEMPTIVE DOCTRINE:
═══════════════════════════════════════════════════════════════════════════════

In ancient Celtic warfare, the element of surprise was everything. The Celts
would strike at dawn, from unexpected directions, using terrain the enemy
thought impassable. They didn't wait for the enemy to be ready.

In financial warfare, we apply the same principle:
- ENTER positions BEFORE momentum confirms (anticipate, don't react)
- EXIT positions BEFORE reversals complete (protect gains proactively)
- MOVE capital BEFORE opportunities become obvious (front-run the crowd)

THE PREEMPTIVE SIGNALS:
═══════════════════════════════════════════════════════════════════════════════

1. MOMENTUM DIVERGENCE
   - Price making highs but momentum weakening = EXIT SIGNAL
   - Price making lows but momentum strengthening = ENTRY SIGNAL

2. VOLUME PRECURSORS
   - Volume spike before price move = opportunity incoming
   - Volume drying up = move exhaustion incoming

3. VOLATILITY COMPRESSION
   - Tight range after expansion = breakout imminent
   - We position BEFORE the breakout

4. ORDER FLOW IMBALANCE
   - More bids than asks = buy pressure building
   - More asks than bids = sell pressure building

5. CROSS-MARKET CORRELATION BREAKS
   - When correlated assets diverge = reversion trade opportunity
   - Act before the correlation restores

IMPLEMENTATION:
═══════════════════════════════════════════════════════════════════════════════

This module provides:
1. PreemptiveSignalDetector - Detects signals before they're obvious
2. PreemptiveEntryEngine - Enters positions anticipating moves
3. PreemptiveExitEngine - Exits positions before reversals complete
4. MomentumDivergenceScanner - Scans for divergences in real-time

Gary Leckey | December 2025
"Strike while the iron is hot - better yet, strike before it heats up."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import math
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
from enum import Enum

# =============================================================================
# 📊 SIGNAL TYPES
# =============================================================================

class PreemptiveSignalType(Enum):
    """Types of preemptive signals"""
    MOMENTUM_DIVERGENCE_BULLISH = "mom_div_bull"
    MOMENTUM_DIVERGENCE_BEARISH = "mom_div_bear"
    VOLUME_PRECURSOR_UP = "vol_pre_up"
    VOLUME_PRECURSOR_DOWN = "vol_pre_down"
    VOLATILITY_COMPRESSION = "vol_compress"
    VOLATILITY_EXPANSION = "vol_expand"
    ORDER_FLOW_BULLISH = "order_bull"
    ORDER_FLOW_BEARISH = "order_bear"
    CORRELATION_BREAK_LONG = "corr_break_long"
    CORRELATION_BREAK_SHORT = "corr_break_short"
    
    # Celtic-specific signals
    DAWN_RAID = "dawn_raid"          # Market open opportunities
    AMBUSH_SETUP = "ambush"          # Perfect setup detected
    FLYING_COLUMN_DEPLOY = "fly_col" # Multiple aligned signals


@dataclass
class PreemptiveSignal:
    """A preemptive signal detection"""
    signal_type: PreemptiveSignalType
    exchange: str
    symbol: str
    timestamp: float
    
    # Signal strength (0-1)
    strength: float
    confidence: float
    
    # Action recommendation
    action: str  # "BUY", "SELL", "EXIT_LONG", "EXIT_SHORT", "HOLD"
    urgency: str  # "IMMEDIATE", "SOON", "WATCH"
    
    # Supporting data
    current_price: float
    target_price: float = 0.0
    stop_price: float = 0.0
    reasoning: str = ""
    
    # Timing
    expected_move_bars: int = 5
    window_expires_at: float = 0.0
    
    def is_valid(self) -> bool:
        """Check if signal is still valid"""
        if self.window_expires_at > 0:
            return time.time() < self.window_expires_at
        return True


# =============================================================================
# 📈 MOMENTUM DIVERGENCE DETECTOR
# =============================================================================

class MomentumDivergenceDetector:
    """
    Detects momentum divergence - when price and momentum disagree.
    
    This is the KEY preemptive signal:
    - Price making new high + momentum failing = SELL COMING
    - Price making new low + momentum rising = BUY COMING
    """
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.price_history: Dict[str, deque] = {}
        self.momentum_history: Dict[str, deque] = {}
        
    def update(self, key: str, price: float, volume: float = 0):
        """Update price data for a symbol"""
        if key not in self.price_history:
            self.price_history[key] = deque(maxlen=self.lookback * 2)
            self.momentum_history[key] = deque(maxlen=self.lookback * 2)
        
        self.price_history[key].append(price)
        
        # Calculate momentum (rate of change)
        if len(self.price_history[key]) >= 2:
            old_price = self.price_history[key][-2]
            if old_price > 0:
                momentum = (price - old_price) / old_price * 100
            else:
                momentum = 0
            self.momentum_history[key].append(momentum)
    
    def detect_divergence(self, key: str) -> Optional[PreemptiveSignal]:
        """
        Detect momentum divergence.
        
        Returns PreemptiveSignal if divergence detected.
        """
        if key not in self.price_history:
            return None
        
        prices = list(self.price_history[key])
        momentums = list(self.momentum_history[key])
        
        if len(prices) < self.lookback or len(momentums) < self.lookback:
            return None
        
        # Get recent peaks and troughs in price
        recent_prices = prices[-self.lookback:]
        recent_mom = momentums[-self.lookback:]
        
        # Find price high/low in first and second half of lookback
        half = self.lookback // 2
        first_half_prices = recent_prices[:half]
        second_half_prices = recent_prices[half:]
        first_half_mom = recent_mom[:half]
        second_half_mom = recent_mom[half:]
        
        # Bearish divergence: price higher high, momentum lower high
        if (max(second_half_prices) > max(first_half_prices) and
            max(second_half_mom) < max(first_half_mom)):
            
            strength = (max(first_half_mom) - max(second_half_mom)) / abs(max(first_half_mom)) if max(first_half_mom) != 0 else 0
            strength = max(0, min(1, strength))
            
            exchange, symbol = key.split(':') if ':' in key else ('unknown', key)
            
            return PreemptiveSignal(
                signal_type=PreemptiveSignalType.MOMENTUM_DIVERGENCE_BEARISH,
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                strength=strength,
                confidence=0.7,
                action="EXIT_LONG",
                urgency="SOON" if strength < 0.5 else "IMMEDIATE",
                current_price=prices[-1],
                reasoning=f"Bearish divergence: Price making higher high but momentum failing (strength: {strength:.2f})"
            )
        
        # Bullish divergence: price lower low, momentum higher low
        if (min(second_half_prices) < min(first_half_prices) and
            min(second_half_mom) > min(first_half_mom)):
            
            strength = (min(second_half_mom) - min(first_half_mom)) / abs(min(first_half_mom)) if min(first_half_mom) != 0 else 0
            strength = max(0, min(1, abs(strength)))
            
            exchange, symbol = key.split(':') if ':' in key else ('unknown', key)
            
            return PreemptiveSignal(
                signal_type=PreemptiveSignalType.MOMENTUM_DIVERGENCE_BULLISH,
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                strength=strength,
                confidence=0.7,
                action="BUY",
                urgency="SOON" if strength < 0.5 else "IMMEDIATE",
                current_price=prices[-1],
                reasoning=f"Bullish divergence: Price making lower low but momentum strengthening (strength: {strength:.2f})"
            )
        
        return None


# =============================================================================
# 📊 VOLUME PRECURSOR DETECTOR
# =============================================================================

class VolumePrecursorDetector:
    """
    Detects volume spikes that precede price moves.
    
    Big volume often leads price - "volume leads, price follows"
    """
    
    def __init__(self, lookback: int = 20, spike_threshold: float = 2.0):
        self.lookback = lookback
        self.spike_threshold = spike_threshold
        self.volume_history: Dict[str, deque] = {}
        self.price_history: Dict[str, deque] = {}
        
    def update(self, key: str, price: float, volume: float):
        """Update volume data"""
        if key not in self.volume_history:
            self.volume_history[key] = deque(maxlen=self.lookback * 2)
            self.price_history[key] = deque(maxlen=self.lookback * 2)
        
        self.volume_history[key].append(volume)
        self.price_history[key].append(price)
    
    def detect_precursor(self, key: str) -> Optional[PreemptiveSignal]:
        """Detect volume spike that may precede price move"""
        if key not in self.volume_history:
            return None
        
        volumes = list(self.volume_history[key])
        prices = list(self.price_history[key])
        
        if len(volumes) < 5:
            return None
        
        # Calculate average volume (excluding most recent)
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
        current_volume = volumes[-1]
        
        if avg_volume == 0:
            return None
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio < self.spike_threshold:
            return None
        
        # Volume spike detected! Determine direction
        # Look at recent price action during the spike
        recent_prices = prices[-5:] if len(prices) >= 5 else prices
        price_direction = recent_prices[-1] - recent_prices[0] if len(recent_prices) > 1 else 0
        
        exchange, symbol = key.split(':') if ':' in key else ('unknown', key)
        
        if price_direction > 0:
            return PreemptiveSignal(
                signal_type=PreemptiveSignalType.VOLUME_PRECURSOR_UP,
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                strength=min(1.0, volume_ratio / 4),
                confidence=0.6,
                action="BUY",
                urgency="IMMEDIATE",
                current_price=prices[-1],
                reasoning=f"Volume spike {volume_ratio:.1f}x average with bullish price action"
            )
        else:
            return PreemptiveSignal(
                signal_type=PreemptiveSignalType.VOLUME_PRECURSOR_DOWN,
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                strength=min(1.0, volume_ratio / 4),
                confidence=0.6,
                action="EXIT_LONG",
                urgency="IMMEDIATE",
                current_price=prices[-1],
                reasoning=f"Volume spike {volume_ratio:.1f}x average with bearish price action"
            )


# =============================================================================
# 🔄 VOLATILITY COMPRESSION DETECTOR
# =============================================================================

class VolatilityCompressionDetector:
    """
    Detects volatility compression (squeeze) that precedes breakouts.
    
    Tight range after expansion = energy building up = breakout coming
    """
    
    def __init__(self, lookback: int = 20, compression_threshold: float = 0.5):
        self.lookback = lookback
        self.compression_threshold = compression_threshold
        self.price_history: Dict[str, deque] = {}
        
    def update(self, key: str, price: float):
        """Update price data"""
        if key not in self.price_history:
            self.price_history[key] = deque(maxlen=self.lookback * 3)
        self.price_history[key].append(price)
    
    def _calculate_range(self, prices: List[float]) -> float:
        """Calculate price range as percentage"""
        if len(prices) < 2:
            return 0
        high = max(prices)
        low = min(prices)
        if low == 0:
            return 0
        return (high - low) / low * 100
    
    def detect_compression(self, key: str) -> Optional[PreemptiveSignal]:
        """Detect volatility compression"""
        if key not in self.price_history:
            return None
        
        prices = list(self.price_history[key])
        
        if len(prices) < self.lookback * 2:
            return None
        
        # Compare recent range to older range
        recent_range = self._calculate_range(prices[-self.lookback:])
        older_range = self._calculate_range(prices[-self.lookback*2:-self.lookback])
        
        if older_range == 0:
            return None
        
        compression_ratio = recent_range / older_range
        
        if compression_ratio > self.compression_threshold:
            return None
        
        # Compression detected!
        # Direction bias based on recent trend
        recent_trend = prices[-1] - prices[-self.lookback] if len(prices) >= self.lookback else 0
        
        exchange, symbol = key.split(':') if ':' in key else ('unknown', key)
        
        return PreemptiveSignal(
            signal_type=PreemptiveSignalType.VOLATILITY_COMPRESSION,
            exchange=exchange,
            symbol=symbol,
            timestamp=time.time(),
            strength=1 - compression_ratio,  # Tighter = stronger
            confidence=0.65,
            action="BUY" if recent_trend > 0 else "WATCH",
            urgency="SOON",
            current_price=prices[-1],
            reasoning=f"Volatility compression {compression_ratio:.2f}x - breakout imminent",
            expected_move_bars=10,
            window_expires_at=time.time() + 600  # 10 minute window
        )


# =============================================================================
# 🎯 PREEMPTIVE SIGNAL AGGREGATOR
# =============================================================================

class PreemptiveSignalAggregator:
    """
    Aggregates multiple preemptive signals into actionable intelligence.
    
    Multiple signals pointing same direction = HIGH CONFIDENCE
    """
    
    def __init__(self):
        self.momentum_detector = MomentumDivergenceDetector()
        self.volume_detector = VolumePrecursorDetector()
        self.volatility_detector = VolatilityCompressionDetector()
        
        self.active_signals: Dict[str, List[PreemptiveSignal]] = {}
        self.signal_history: List[PreemptiveSignal] = []
        
    def update(self, exchange: str, symbol: str, price: float, volume: float = 0):
        """Update all detectors with new data"""
        key = f"{exchange}:{symbol}"
        
        self.momentum_detector.update(key, price, volume)
        self.volume_detector.update(key, price, volume)
        self.volatility_detector.update(key, price)
    
    def scan_for_signals(self, exchange: str, symbol: str) -> List[PreemptiveSignal]:
        """Scan all detectors for preemptive signals"""
        key = f"{exchange}:{symbol}"
        signals = []
        
        # Check momentum divergence
        mom_signal = self.momentum_detector.detect_divergence(key)
        if mom_signal:
            signals.append(mom_signal)
        
        # Check volume precursor
        vol_signal = self.volume_detector.detect_precursor(key)
        if vol_signal:
            signals.append(vol_signal)
        
        # Check volatility compression
        volatility_signal = self.volatility_detector.detect_compression(key)
        if volatility_signal:
            signals.append(volatility_signal)
        
        # Store signals
        if signals:
            self.active_signals[key] = signals
            self.signal_history.extend(signals)
        
        return signals
    
    def get_consensus_signal(self, exchange: str, symbol: str) -> Optional[PreemptiveSignal]:
        """
        Get consensus signal if multiple detectors agree.
        
        This is the CELTIC FLYING COLUMN signal - multiple scouts agree!
        """
        key = f"{exchange}:{symbol}"
        signals = self.active_signals.get(key, [])
        
        if len(signals) < 2:
            return None
        
        # Check for consensus (multiple signals same direction)
        buy_signals = [s for s in signals if s.action in ("BUY", "ENTER_LONG")]
        sell_signals = [s for s in signals if s.action in ("SELL", "EXIT_LONG")]
        
        if len(buy_signals) >= 2:
            # FLYING COLUMN DEPLOY - multiple bullish signals
            avg_strength = sum(s.strength for s in buy_signals) / len(buy_signals)
            avg_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)
            
            return PreemptiveSignal(
                signal_type=PreemptiveSignalType.FLYING_COLUMN_DEPLOY,
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                strength=avg_strength,
                confidence=min(0.95, avg_confidence + 0.15),  # Consensus boosts confidence
                action="BUY",
                urgency="IMMEDIATE",
                current_price=buy_signals[0].current_price,
                reasoning=f"☘️ FLYING COLUMN: {len(buy_signals)} bullish signals aligned"
            )
        
        if len(sell_signals) >= 2:
            avg_strength = sum(s.strength for s in sell_signals) / len(sell_signals)
            avg_confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)
            
            return PreemptiveSignal(
                signal_type=PreemptiveSignalType.FLYING_COLUMN_DEPLOY,
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                strength=avg_strength,
                confidence=min(0.95, avg_confidence + 0.15),
                action="EXIT_LONG",
                urgency="IMMEDIATE",
                current_price=sell_signals[0].current_price,
                reasoning=f"☘️ PREEMPTIVE RETREAT: {len(sell_signals)} bearish signals aligned"
            )
        
        return None


# =============================================================================
# ⚡ PREEMPTIVE EXIT ENGINE
# =============================================================================

class PreemptiveExitEngine:
    """
    The most critical component: EXIT BEFORE THE REVERSAL COMPLETES.
    
    "The wise warrior strikes and withdraws, never lingering."
    
    This engine monitors positions and triggers exits based on:
    1. Momentum divergence (exit before reversal)
    2. Volatility expansion (exit before spike hurts us)
    3. Target approach (exit before resistance rejects us)
    4. Time decay (exit before patience becomes losses)
    """
    
    def __init__(self, aggregator: PreemptiveSignalAggregator = None):
        self.aggregator = aggregator or PreemptiveSignalAggregator()
        self.position_entry_momentum: Dict[str, float] = {}  # Track momentum at entry
        
    def register_entry(self, key: str, entry_momentum: float):
        """Register a position entry with its momentum"""
        self.position_entry_momentum[key] = entry_momentum
    
    def check_preemptive_exit(self, exchange: str, symbol: str, 
                              entry_price: float, current_price: float,
                              current_momentum: float = None) -> Tuple[bool, str, float]:
        """
        Check if we should exit PREEMPTIVELY.
        
        Returns: (should_exit, reason, confidence)
        """
        key = f"{exchange}:{symbol}"
        
        # Check for preemptive signals
        signals = self.aggregator.scan_for_signals(exchange, symbol)
        
        # Check consensus (multiple bearish signals)
        consensus = self.aggregator.get_consensus_signal(exchange, symbol)
        if consensus and consensus.action in ("EXIT_LONG", "SELL"):
            return True, f"⚡ PREEMPTIVE EXIT: {consensus.reasoning}", consensus.confidence
        
        # Check momentum deterioration
        if key in self.position_entry_momentum and current_momentum is not None:
            entry_mom = self.position_entry_momentum[key]
            mom_change = current_momentum - entry_mom
            
            # If momentum dropped significantly while we're in profit, EXIT
            gross_pnl = (current_price - entry_price) / entry_price
            if gross_pnl > 0.001 and mom_change < -0.3:
                return True, f"⚡ MOMENTUM DECAY: Momentum dropped {mom_change:.2f} while profitable", 0.7
        
        # Check for bearish divergence specifically
        for signal in signals:
            if signal.signal_type == PreemptiveSignalType.MOMENTUM_DIVERGENCE_BEARISH:
                if signal.strength > 0.5:
                    return True, f"⚡ DIVERGENCE EXIT: {signal.reasoning}", signal.confidence
        
        return False, "No preemptive exit signals", 0.0
    
    def get_entry_signal(self, symbol: str, price: float) -> Dict:
        """
        Check if entry is recommended based on preemptive signals.
        
        Returns:
            {'entry_blocked': bool, 'reason': str, 'confidence': float}
        """
        # Check for any exit signals (which would block entry)
        signals = self.aggregator.scan_for_signals("unknown", symbol)
        
        for signal in signals:
            # Block entry if we're seeing bearish signals
            if signal.signal_type in (
                PreemptiveSignalType.MOMENTUM_DIVERGENCE_BEARISH,
                PreemptiveSignalType.VOLUME_PRECURSOR,
                PreemptiveSignalType.RANGE_CONTRACTION
            ):
                if signal.strength > 0.6 and signal.confidence > 0.5:
                    return {
                        'entry_blocked': True,
                        'reason': f'Preemptive signal: {signal.signal_type.name}',
                        'confidence': signal.confidence
                    }
        
        # Look for bullish signals that support entry
        bullish_count = sum(1 for s in signals if s.action == "ENTRY_LONG")
        
        return {
            'entry_blocked': False,
            'reason': f'Entry clear ({bullish_count} bullish signals)',
            'confidence': 0.5 + (bullish_count * 0.1)
        }
    
    def clear_position(self, key: str):
        """Clear a position from tracking"""
        self.position_entry_momentum.pop(key, None)


# =============================================================================
# 🌅 DAWN RAID DETECTOR
# =============================================================================

class DawnRaidDetector:
    """
    Detects "Dawn Raid" opportunities - the Celtic tactic of striking at dawn.
    
    In markets, this translates to:
    - Market open momentum (first 15-30 minutes)
    - Overnight gap analysis
    - Pre-market news impact
    
    "Strike when the enemy is still waking"
    """
    
    def __init__(self):
        self.session_start_prices: Dict[str, Dict] = {}
        
    def record_session_start(self, exchange: str, symbol: str, 
                            open_price: float, prev_close: float = None):
        """Record session opening data"""
        key = f"{exchange}:{symbol}"
        self.session_start_prices[key] = {
            'open': open_price,
            'prev_close': prev_close,
            'timestamp': time.time(),
            'gap': ((open_price - prev_close) / prev_close * 100) if prev_close else 0
        }
    
    def detect_dawn_raid(self, exchange: str, symbol: str,
                        current_price: float) -> Optional[PreemptiveSignal]:
        """
        Detect dawn raid opportunity.
        
        We look for:
        1. Gap up/down at open
        2. Strong momentum in gap direction (continuation)
        3. OR fade setup (gap fill opportunity)
        """
        key = f"{exchange}:{symbol}"
        
        if key not in self.session_start_prices:
            return None
        
        session_data = self.session_start_prices[key]
        open_price = session_data['open']
        gap = session_data['gap']
        session_age = time.time() - session_data['timestamp']
        
        # Only valid in first 30 minutes of session
        if session_age > 1800:  # 30 minutes
            return None
        
        # Calculate current move from open
        move_from_open = (current_price - open_price) / open_price * 100
        
        # Gap continuation (momentum in gap direction)
        if abs(gap) > 0.5:  # Significant gap
            if gap > 0 and move_from_open > gap:
                # Gap up continuing higher - BUY
                return PreemptiveSignal(
                    signal_type=PreemptiveSignalType.DAWN_RAID,
                    exchange=exchange,
                    symbol=symbol,
                    timestamp=time.time(),
                    strength=min(1.0, move_from_open / 2),
                    confidence=0.65,
                    action="BUY",
                    urgency="IMMEDIATE",
                    current_price=current_price,
                    reasoning=f"☘️ DAWN RAID: Gap up {gap:.1f}% continuing ({move_from_open:.1f}% from open)"
                )
            
            if gap < 0 and move_from_open < gap:
                # Gap down continuing lower - potential short or avoid
                return PreemptiveSignal(
                    signal_type=PreemptiveSignalType.DAWN_RAID,
                    exchange=exchange,
                    symbol=symbol,
                    timestamp=time.time(),
                    strength=min(1.0, abs(move_from_open) / 2),
                    confidence=0.65,
                    action="EXIT_LONG",
                    urgency="IMMEDIATE",
                    current_price=current_price,
                    reasoning=f"☘️ DAWN RAID: Gap down {gap:.1f}% continuing ({move_from_open:.1f}% from open)"
                )
        
        return None


# =============================================================================
# 🎯 MASTER PREEMPTIVE STRIKE CONTROLLER
# =============================================================================

class CelticPreemptiveStrikeController:
    """
    Master controller for all preemptive strike operations.
    
    Coordinates all detectors and provides unified interface for:
    - Preemptive entries
    - Preemptive exits
    - Dawn raids
    - Flying column deployments
    
    "Unity is strength - all scouts report to one command"
    """
    
    def __init__(self):
        self.aggregator = PreemptiveSignalAggregator()
        self.exit_engine = PreemptiveExitEngine(self.aggregator)
        self.dawn_detector = DawnRaidDetector()
        
        self.all_signals: List[PreemptiveSignal] = []
        self.signal_callback: Optional[callable] = None
        
        logging.info("☘️⚡ Celtic Preemptive Strike Controller initialized")
    
    def set_signal_callback(self, callback: callable):
        """Set callback for when signals are detected"""
        self.signal_callback = callback
    
    def update(self, exchange: str, symbol: str, price: float, volume: float = 0):
        """Update all systems with new market data"""
        self.aggregator.update(exchange, symbol, price, volume)
    
    def record_session_open(self, exchange: str, symbol: str,
                           open_price: float, prev_close: float = None):
        """Record session opening for dawn raid detection"""
        self.dawn_detector.record_session_start(exchange, symbol, open_price, prev_close)
    
    def register_position_entry(self, exchange: str, symbol: str, momentum: float):
        """Register a new position for preemptive exit monitoring"""
        key = f"{exchange}:{symbol}"
        self.exit_engine.register_entry(key, momentum)
    
    def scan_all(self, exchange: str, symbol: str, 
                current_price: float) -> List[PreemptiveSignal]:
        """
        Comprehensive scan for all preemptive signals.
        
        Returns list of all detected signals.
        """
        signals = []
        
        # Standard preemptive signals
        std_signals = self.aggregator.scan_for_signals(exchange, symbol)
        signals.extend(std_signals)
        
        # Consensus signals
        consensus = self.aggregator.get_consensus_signal(exchange, symbol)
        if consensus:
            signals.append(consensus)
        
        # Dawn raid signals
        dawn_signal = self.dawn_detector.detect_dawn_raid(exchange, symbol, current_price)
        if dawn_signal:
            signals.append(dawn_signal)
        
        # Store and notify
        self.all_signals.extend(signals)
        
        if signals and self.signal_callback:
            for signal in signals:
                self.signal_callback(signal)
        
        return signals
    
    def check_preemptive_exit(self, exchange: str, symbol: str,
                             entry_price: float, current_price: float,
                             current_momentum: float = None) -> Tuple[bool, str, float]:
        """
        Check if position should exit preemptively.
        
        This is the key function - it tells you to EXIT BEFORE losses occur.
        """
        return self.exit_engine.check_preemptive_exit(
            exchange, symbol, entry_price, current_price, current_momentum
        )
    
    def clear_position(self, exchange: str, symbol: str):
        """Clear a closed position from monitoring"""
        key = f"{exchange}:{symbol}"
        self.exit_engine.clear_position(key)
    
    def get_best_entry_opportunities(self, min_confidence: float = 0.6,
                                    limit: int = 5) -> List[PreemptiveSignal]:
        """Get the best entry opportunities across all monitored symbols"""
        entry_signals = [
            s for s in self.all_signals
            if s.is_valid() and 
               s.action == "BUY" and 
               s.confidence >= min_confidence
        ]
        
        # Sort by confidence * strength
        entry_signals.sort(key=lambda x: x.confidence * x.strength, reverse=True)
        
        return entry_signals[:limit]
    
    def get_status_report(self) -> str:
        """Get status report of preemptive strike system"""
        valid_signals = [s for s in self.all_signals if s.is_valid()]
        buy_signals = [s for s in valid_signals if s.action == "BUY"]
        exit_signals = [s for s in valid_signals if s.action in ("EXIT_LONG", "SELL")]
        
        return f"""
☘️⚡═══════════════════════════════════════════════════════════════════════⚡☘️
                    CELTIC PREEMPTIVE STRIKE STATUS
☘️⚡═══════════════════════════════════════════════════════════════════════⚡☘️

📡 ACTIVE SIGNALS:
   Total Valid: {len(valid_signals)}
   Buy Signals: {len(buy_signals)}
   Exit Signals: {len(exit_signals)}

🎯 TOP OPPORTUNITIES:
"""
        + "\n".join([
            f"   • {s.exchange}:{s.symbol} - {s.action} ({s.confidence*100:.0f}% confidence)"
            for s in self.get_best_entry_opportunities(limit=3)
        ]) + f"""

⚡ "Strike before the iron heats - be the first, not the last"
☘️⚡═══════════════════════════════════════════════════════════════════════⚡☘️
"""


# =============================================================================
# 🌍 GLOBAL INSTANCE
# =============================================================================

_PREEMPTIVE_CONTROLLER: Optional[CelticPreemptiveStrikeController] = None


def get_preemptive_controller() -> CelticPreemptiveStrikeController:
    """Get the global preemptive strike controller"""
    global _PREEMPTIVE_CONTROLLER
    if _PREEMPTIVE_CONTROLLER is None:
        _PREEMPTIVE_CONTROLLER = CelticPreemptiveStrikeController()
    return _PREEMPTIVE_CONTROLLER


# Quick access functions
def update_preemptive(exchange: str, symbol: str, price: float, volume: float = 0):
    """Quick update for preemptive system"""
    return get_preemptive_controller().update(exchange, symbol, price, volume)


def scan_preemptive(exchange: str, symbol: str, price: float) -> List[PreemptiveSignal]:
    """Quick scan for preemptive signals"""
    return get_preemptive_controller().scan_all(exchange, symbol, price)


def check_preemptive_exit(exchange: str, symbol: str, entry_price: float,
                         current_price: float, momentum: float = None) -> Tuple[bool, str, float]:
    """Quick check for preemptive exit"""
    return get_preemptive_controller().check_preemptive_exit(
        exchange, symbol, entry_price, current_price, momentum
    )


# =============================================================================
