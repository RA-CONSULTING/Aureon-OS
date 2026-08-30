#!/usr/bin/env python3
"""
🎯⚔️ WAR STRATEGY - QUICK KILL PROBABILITY ⚔️🎯

"Get in, get out, get paid. Don't linger in enemy territory."

This module tells scouts:
1. What's the probability of making 1 penny net profit on this coin?
2. How FAST can we achieve it? (time estimate in bars/minutes)
3. Which coins offer the QUICKEST penny profit?

THE PENNY PROFIT MATH:
- Position: $10
- Combined fee rate: 0.70% (buy + sell)
- Required move (r): 1.5163%
- Gross profit needed: $0.151625
- Net profit target: $0.01 (1 penny)

WAR RULES:
1. Prioritize SPEED over size
2. Quick raids > long sieges
3. Time in market = risk exposure
4. The faster we cycle, the more pennies we stack

"Our revenge will be the laughter of our children." - Bobby Sands
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import time
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math

# ═══════════════════════════════════════════════════════════════
# 🪙 SHARED GOAL: PENNY PROFIT CONSTANTS
# These are FALLBACK values - use get_penny_threshold() for dynamic calc
# ═══════════════════════════════════════════════════════════════
POSITION_SIZE = 10.0  # $10 per trade
COMBINED_FEE_RATE = 0.007  # 0.70% round-trip
REQUIRED_R = 0.015163  # 1.5163% move needed
WIN_THRESHOLD = 0.151625  # $0.151625 gross profit minimum
NET_PENNY_TARGET = 0.01  # $0.01 net profit goal (🪙 SHARED GOAL)

def get_dynamic_penny_threshold(exchange: str = 'binance', trade_size: float = 10.0) -> float:
    """🪙 SHARED GOAL: Get dynamic penny threshold from ecosystem."""
    try:
        from aureon_unified_ecosystem import get_penny_threshold
        penny = get_penny_threshold(exchange, trade_size)
        if penny:
            return penny['win_gte']
    except ImportError:
        pass
    return WIN_THRESHOLD  # Fallback


def get_dynamic_required_r(exchange: str = 'binance', trade_size: float = 10.0) -> float:
    """🪙 SHARED GOAL: Get the dynamic required move (r) for net penny profit."""
    try:
        from aureon_unified_ecosystem import get_penny_threshold
        penny = get_penny_threshold(exchange, trade_size)
        if penny:
            return float(penny.get('required_r', REQUIRED_R) or REQUIRED_R)
    except ImportError:
        pass
    return REQUIRED_R

# Time constants
SECONDS_PER_BAR = 60  # Assume 1-minute bars for crypto
MAX_ACCEPTABLE_BARS = 30  # Don't want to hold longer than 30 bars
IDEAL_BARS = 10  # Ideal exit within 10 bars (10 minutes)

@dataclass
class QuickKillEstimate:
    """Estimate for how quickly we can achieve penny profit on a symbol."""
    symbol: str
    exchange: str

    # Probability estimates
    prob_penny_profit: float  # 0-1, chance of achieving penny profit
    prob_quick_kill: float  # 0-1, chance of achieving it within IDEAL_BARS

    # Time estimates
    estimated_bars_to_profit: float  # Expected bars to hit target
    estimated_seconds: float  # Expected time in seconds
    confidence: float  # 0-1, how confident we are in this estimate

    # Volatility data
    recent_volatility: float  # Recent price volatility (helps predict speed)
    avg_bar_move_pct: float  # Average move per bar

    # War recommendation
    go_signal: bool  # True = ATTACK, False = HOLD
    priority: int  # 1-10, higher = attack first
    reason: str  # Why this recommendation

    # Timestamps
    estimated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'prob_penny_profit': self.prob_penny_profit,
            'prob_quick_kill': self.prob_quick_kill,
            'estimated_bars': self.estimated_bars_to_profit,
            'estimated_seconds': self.estimated_seconds,
            'estimated_minutes': self.estimated_seconds / 60,
            'confidence': self.confidence,
            'go_signal': self.go_signal,
            'priority': self.priority,
            'reason': self.reason
        }


@dataclass
class TradeTimestamp:
    """Track actual entry/exit times for learning."""
    symbol: str
    exchange: str
    entry_time: float
    entry_price: float
    entry_value: float

    # Exit data (filled when we exit)
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    exit_value: Optional[float] = None

    # Results
    bars_held: int = 0
    seconds_held: float = 0
    gross_pnl: float = 0
    net_pnl: float = 0
    was_penny_profit: bool = False
    was_quick_kill: bool = False  # Achieved within IDEAL_BARS

    def complete_exit(self, exit_price: float, exit_value: float, bars: int):
        self.exit_time = time.time()
        self.exit_price = exit_price
        self.exit_value = exit_value
        self.bars_held = bars
        self.seconds_held = self.exit_time - self.entry_time
        self.gross_pnl = exit_value - self.entry_value

        # Calculate net P&L after fees
        total_fees = (self.entry_value + exit_value) * (COMBINED_FEE_RATE / 2)
        self.net_pnl = self.gross_pnl - total_fees

        self.was_penny_profit = self.net_pnl >= NET_PENNY_TARGET
        self.was_quick_kill = self.was_penny_profit and bars <= IDEAL_BARS


class WarStrategy:
    """
    ⚔️ THE WAR STRATEGIST ⚔️

    Tells scouts where to attack based on:
    1. Probability of penny profit
    2. Speed of expected exit
    3. Current volatility
    4. Historical performance
    """

    def __init__(self):
        self.volatility_cache: Dict[str, Dict] = {}  # symbol -> volatility data
        self.history: List[TradeTimestamp] = []  # Completed trades
        self.active_raids: Dict[str, TradeTimestamp] = {}  # symbol -> active trade
        self.symbol_stats: Dict[str, Dict] = {}  # Historical stats per symbol

        # Load historical data if exists
        self._load_history()

    def _load_history(self):
        """Load historical trade timestamps for learning."""
        try:
            if os.path.exists('war_strategy_history.json'):
                with open('war_strategy_history.json', 'r') as f:
                    data = json.load(f)
                    self.symbol_stats = data.get('symbol_stats', {})
                    print(f"⚔️ WAR STRATEGY: Loaded {len(self.symbol_stats)} symbol histories")
        except Exception as e:
            print(f"⚔️ WAR STRATEGY: Fresh start (no history): {e}")

    def _save_history(self):
        """Save trade history for learning."""
        try:
            with open('war_strategy_history.json', 'w') as f:
                json.dump({
                    'symbol_stats': self.symbol_stats,
                    'last_updated': time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"⚔️ WAR STRATEGY: Could not save history: {e}")

    def update_volatility(self, symbol: str, prices: List[float], exchange: str = 'unknown'):
        """
        Update volatility cache for a symbol based on recent prices.

        Args:
            symbol: Trading pair
            prices: List of recent prices (most recent last)
            exchange: Exchange name
        """
        if len(prices) < 2:
            return

        # Calculate bar-to-bar moves
        moves = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                move_pct = abs(prices[i] - prices[i-1]) / prices[i-1]
                moves.append(move_pct)

        if not moves:
            return

        avg_move = sum(moves) / len(moves)
        max_move = max(moves)
        volatility = sum((m - avg_move) ** 2 for m in moves) / len(moves)
        volatility = math.sqrt(volatility)  # Standard deviation

        self.volatility_cache[symbol] = {
            'avg_bar_move_pct': avg_move,
            'max_bar_move_pct': max_move,
            'volatility': volatility,
            'sample_size': len(moves),
            'updated_at': time.time(),
            'exchange': exchange
        }

    def estimate_quick_kill(self, symbol: str, exchange: str = 'unknown',
                           current_price: float = 0, prices: List[float] = None) -> QuickKillEstimate:
        """
        🎯 THE CORE FUNCTION: Estimate probability and speed of penny profit.

        Returns a QuickKillEstimate with:
        - Probability of achieving penny profit
        - Estimated time to achieve it
        - GO/NO-GO recommendation
        """
        # Update volatility if we have price data
        if prices and len(prices) > 1:
            self.update_volatility(symbol, prices, exchange)

        # Get volatility data
        vol_data = self.volatility_cache.get(symbol, {})
        avg_move = vol_data.get('avg_bar_move_pct', 0.005)  # Default 0.5% per bar
        volatility = vol_data.get('volatility', 0.003)

        # Get historical stats for this symbol
        stats = self.symbol_stats.get(symbol, {})
        historical_avg_bars = stats.get('avg_bars_to_profit', 20)
        historical_win_rate = stats.get('win_rate', 0.5)
        historical_quick_rate = stats.get('quick_kill_rate', 0.3)
        sample_size = stats.get('trades', 0)

        # ═══════════════════════════════════════════════════════════════
        # 🧮 CALCULATE PROBABILITY OF PENNY PROFIT
        # ═══════════════════════════════════════════════════════════════

        required_r = get_dynamic_required_r(exchange, POSITION_SIZE)

        # How many bars to hit REQUIRED_R based on avg move?
        if avg_move > 0:
            estimated_bars = required_r / avg_move
        else:
            estimated_bars = 50  # Conservative default

        # Factor in volatility - higher vol = faster potential but also risk
        if volatility > avg_move:
            # High volatility relative to average move - could be faster
            estimated_bars *= 0.8

        # Blend with historical if we have data
        if sample_size >= 5:
            estimated_bars = (estimated_bars * 0.3) + (historical_avg_bars * 0.7)

        estimated_bars = max(1, estimated_bars)  # At least 1 bar
        estimated_seconds = estimated_bars * SECONDS_PER_BAR

        # ═══════════════════════════════════════════════════════════════
        # 🎲 CALCULATE PROBABILITIES
        # ═══════════════════════════════════════════════════════════════

        # Probability of penny profit (based on volatility vs required move)
        # If avg_move * 10 bars > required_r, good chance
        moves_in_10_bars = avg_move * 10

        if moves_in_10_bars >= required_r:
            prob_penny = 0.7 + (moves_in_10_bars / required_r - 1) * 0.1
        else:
            prob_penny = 0.3 + (moves_in_10_bars / required_r) * 0.3

        # Adjust with historical win rate
        if sample_size >= 5:
            prob_penny = (prob_penny * 0.4) + (historical_win_rate * 0.6)

        prob_penny = max(0.1, min(0.95, prob_penny))  # Clamp 10-95%

        # Probability of QUICK kill (within IDEAL_BARS)
        if estimated_bars <= IDEAL_BARS:
            prob_quick = prob_penny * 0.9  # High chance if estimate is fast
        elif estimated_bars <= MAX_ACCEPTABLE_BARS:
            prob_quick = prob_penny * (IDEAL_BARS / estimated_bars)
        else:
            prob_quick = prob_penny * 0.2  # Low chance if slow estimate

        # Adjust with historical quick rate
        if sample_size >= 5:
            prob_quick = (prob_quick * 0.4) + (historical_quick_rate * 0.6)

        prob_quick = max(0.05, min(0.90, prob_quick))  # Clamp 5-90%

        # ═══════════════════════════════════════════════════════════════
        # 🎖️ CONFIDENCE SCORE
        # ═══════════════════════════════════════════════════════════════
        confidence = 0.5  # Base confidence

        # More data = more confidence
        if sample_size >= 20:
            confidence += 0.3
        elif sample_size >= 5:
            confidence += 0.15

        # Fresh volatility data = more confidence
        vol_age = time.time() - vol_data.get('updated_at', 0)
        if vol_age < 60:  # Less than 1 minute old
            confidence += 0.2
        elif vol_age < 300:  # Less than 5 minutes
            confidence += 0.1

        confidence = min(0.95, confidence)

        # ═══════════════════════════════════════════════════════════════
        # ⚔️ WAR RECOMMENDATION
        # ═══════════════════════════════════════════════════════════════

        # Priority score (1-10)
        # Fast + high probability = high priority
        speed_score = max(0, 10 - estimated_bars / 5)  # 10 bars = score 8
        prob_score = prob_quick * 10
        priority = int((speed_score * 0.6 + prob_score * 0.4))
        priority = max(1, min(10, priority))

        # GO signal: probability > 50% AND estimated time < MAX_ACCEPTABLE
        go_signal = prob_penny >= 0.5 and estimated_bars <= MAX_ACCEPTABLE_BARS

        # Build reason
        if go_signal:
            if estimated_bars <= IDEAL_BARS:
                reason = f"⚡ QUICK RAID: {prob_quick*100:.0f}% chance in ~{estimated_bars:.0f} bars ({estimated_seconds/60:.1f}min)"
            else:
                reason = f"✅ ATTACK: {prob_penny*100:.0f}% profit chance, ~{estimated_bars:.0f} bars"
        else:
            if prob_penny < 0.5:
                reason = f"⚠️ LOW ODDS: Only {prob_penny*100:.0f}% profit chance"
            else:
                reason = f"🐢 TOO SLOW: Would take ~{estimated_bars:.0f} bars ({estimated_seconds/60:.1f}min)"

        return QuickKillEstimate(
            symbol=symbol,
            exchange=exchange,
            prob_penny_profit=prob_penny,
            prob_quick_kill=prob_quick,
            estimated_bars_to_profit=estimated_bars,
            estimated_seconds=estimated_seconds,
            confidence=confidence,
            recent_volatility=volatility,
            avg_bar_move_pct=avg_move,
            go_signal=go_signal,
            priority=priority,
            reason=reason
        )

    def start_raid(self, symbol: str, exchange: str, entry_price: float,
                   entry_value: float = POSITION_SIZE) -> TradeTimestamp:
        """
        📍 Start tracking a raid (trade entry).

        Returns a TradeTimestamp for tracking.
        """
        raid = TradeTimestamp(
            symbol=symbol,
            exchange=exchange,
            entry_time=time.time(),
            entry_price=entry_price,
            entry_value=entry_value
        )

        self.active_raids[symbol] = raid

        # Log the entry
        estimate = self.estimate_quick_kill(symbol, exchange)
        print(f"⚔️ RAID STARTED: {symbol}")
        print(f"   📍 Entry: ${entry_price:.6f} @ {datetime.now().strftime('%H:%M:%S')}")
        print(f"   🎯 Target: +{REQUIRED_R*100:.2f}% (${WIN_THRESHOLD:.4f} gross)")
        print(f"   ⏱️ Estimated exit: ~{estimate.estimated_bars_to_profit:.0f} bars ({estimate.estimated_seconds/60:.1f}min)")
        print(f"   📊 Quick kill probability: {estimate.prob_quick_kill*100:.0f}%")

        return raid

    def complete_raid(self, symbol: str, exit_price: float, exit_value: float,
                      bars_held: int) -> Optional[TradeTimestamp]:
        """
        ✅ Complete a raid (trade exit) and record results.

        Returns the completed TradeTimestamp.
        """
        raid = self.active_raids.pop(symbol, None)
        if not raid:
            return None

        raid.complete_exit(exit_price, exit_value, bars_held)
        self.history.append(raid)

        # Update symbol stats
        if symbol not in self.symbol_stats:
            self.symbol_stats[symbol] = {
                'trades': 0,
                'wins': 0,
                'quick_kills': 0,
                'total_bars': 0,
                'total_pnl': 0
            }

        stats = self.symbol_stats[symbol]
        stats['trades'] += 1
        stats['total_bars'] += bars_held
        stats['total_pnl'] += raid.net_pnl

        if raid.was_penny_profit:
            stats['wins'] += 1
        if raid.was_quick_kill:
            stats['quick_kills'] += 1

        # Calculate derived stats
        stats['win_rate'] = stats['wins'] / stats['trades']
        stats['quick_kill_rate'] = stats['quick_kills'] / stats['trades']
        stats['avg_bars_to_profit'] = stats['total_bars'] / stats['trades']

        # Log the exit
        emoji = "💰" if raid.was_penny_profit else "❌"
        speed = "⚡ QUICK!" if raid.was_quick_kill else ""

        print(f"{emoji} RAID COMPLETE: {symbol} {speed}")
        print(f"   ⏱️ Held: {bars_held} bars ({raid.seconds_held/60:.1f}min)")
        print(f"   💵 Gross P&L: ${raid.gross_pnl:.4f}")
        print(f"   💰 Net P&L: ${raid.net_pnl:.4f}")
        print(f"   📊 Symbol stats: {stats['win_rate']*100:.0f}% WR, {stats['avg_bars_to_profit']:.1f} avg bars")

        # Save updated history
        self._save_history()

        return raid

    def get_raid_status(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        📊 Get status of an active raid.

        Returns dict with current P&L, time in trade, etc.
        """
        raid = self.active_raids.get(symbol)
        if not raid:
            return None

        current_value = POSITION_SIZE * (current_price / raid.entry_price)
        gross_pnl = current_value - raid.entry_value
        total_fees = (raid.entry_value + current_value) * (COMBINED_FEE_RATE / 2)
        net_pnl = gross_pnl - total_fees

        seconds_in = time.time() - raid.entry_time
        bars_in = int(seconds_in / SECONDS_PER_BAR)

        move_pct = (current_price - raid.entry_price) / raid.entry_price
        target_move = REQUIRED_R
        progress = move_pct / target_move if target_move > 0 else 0

        return {
            'symbol': symbol,
            'entry_price': raid.entry_price,
            'current_price': current_price,
            'move_pct': move_pct * 100,
            'target_pct': target_move * 100,
            'progress': progress,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'is_penny_profit': net_pnl >= NET_PENNY_TARGET,
            'bars_in': bars_in,
            'seconds_in': seconds_in,
            'minutes_in': seconds_in / 60,
            'entry_time': datetime.fromtimestamp(raid.entry_time).strftime('%H:%M:%S')
        }

    def rank_targets(self, candidates: List[Dict]) -> List[Dict]:
        """
        🎯 Rank potential targets by quick kill probability.

        Args:
            candidates: List of dicts with 'symbol', 'exchange', 'prices'

        Returns:
            Sorted list with QuickKillEstimate added, best targets first.
        """
        ranked = []

        for c in candidates:
            symbol = c.get('symbol', '')
            exchange = c.get('exchange', 'unknown')
            prices = c.get('prices', [])
            current_price = c.get('price', prices[-1] if prices else 0)

            estimate = self.estimate_quick_kill(symbol, exchange, current_price, prices)

            c['quick_kill'] = estimate.to_dict()
            c['war_priority'] = estimate.priority
            c['war_go'] = estimate.go_signal
            c['war_reason'] = estimate.reason

            ranked.append(c)

        # Sort by priority (highest first), then by estimated bars (lowest first)
        ranked.sort(key=lambda x: (-x['war_priority'],
                                    x['quick_kill']['estimated_bars']))

        return ranked

    def get_war_briefing(self) -> str:
        """
        📜 Get a war briefing summary.
        """
        active = len(self.active_raids)
        total_trades = sum(s.get('trades', 0) for s in self.symbol_stats.values())
        total_wins = sum(s.get('wins', 0) for s in self.symbol_stats.values())
        total_quick = sum(s.get('quick_kills', 0) for s in self.symbol_stats.values())

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        quick_rate = (total_quick / total_trades * 100) if total_trades > 0 else 0

        briefing = f"""
⚔️ ═══════════════════════════════════════════════════════════ ⚔️
                      WAR STRATEGY BRIEFING
⚔️ ═══════════════════════════════════════════════════════════ ⚔️

🎯 MISSION: 1 penny net profit per trade, as FAST as possible

📊 CAMPAIGN STATS:
   Total Raids: {total_trades}
   Victories (penny profit): {total_wins} ({win_rate:.1f}%)
   Quick Kills (<{IDEAL_BARS} bars): {total_quick} ({quick_rate:.1f}%)

🔥 ACTIVE RAIDS: {active}
"""

        for symbol, raid in self.active_raids.items():
            seconds_in = time.time() - raid.entry_time
            briefing += f"   • {symbol}: {seconds_in/60:.1f}min in enemy territory\n"

        briefing += f"""
📍 TARGET REQUIREMENTS:
   Required Move: {REQUIRED_R*100:.2f}%
   Gross Profit Needed: ${WIN_THRESHOLD:.4f}
   Net Target: ${NET_PENNY_TARGET:.4f} (1 penny)
   Max Acceptable Hold: {MAX_ACCEPTABLE_BARS} bars
   Ideal Exit: <{IDEAL_BARS} bars

"Get in, get out, get paid. Time is the enemy."
⚔️ ═══════════════════════════════════════════════════════════ ⚔️
"""
        return briefing


# ═══════════════════════════════════════════════════════════════
# 🌍 GLOBAL WAR STRATEGIST
# ═══════════════════════════════════════════════════════════════
WAR_STRATEGIST = WarStrategy()


def get_quick_kill_estimate(symbol: str, exchange: str = 'unknown',
                           prices: List[float] = None) -> QuickKillEstimate:
    """
    🎯 Quick access to get a kill estimate for a symbol.
    """
    return WAR_STRATEGIST.estimate_quick_kill(symbol, exchange, prices=prices)


def should_attack(symbol: str, exchange: str = 'unknown',
                 prices: List[float] = None) -> Tuple[bool, str, int]:
    """
    ⚔️ Should we attack this target?

    Returns: (go_signal, reason, priority)
    """
    estimate = WAR_STRATEGIST.estimate_quick_kill(symbol, exchange, prices=prices)
    return estimate.go_signal, estimate.reason, estimate.priority


def start_raid(symbol: str, exchange: str, entry_price: float) -> TradeTimestamp:
    """📍 Start tracking a trade."""
    return WAR_STRATEGIST.start_raid(symbol, exchange, entry_price)


def complete_raid(symbol: str, exit_price: float, exit_value: float,
                 bars_held: int) -> Optional[TradeTimestamp]:
    """✅ Complete a trade and record results."""
    return WAR_STRATEGIST.complete_raid(symbol, exit_price, exit_value, bars_held)


def get_raid_status(symbol: str, current_price: float) -> Optional[Dict]:
    """📊 Get status of active trade."""
    return WAR_STRATEGIST.get_raid_status(symbol, current_price)


def get_war_briefing() -> str:
    """📜 Get war briefing."""
    return WAR_STRATEGIST.get_war_briefing()


# ═══════════════════════════════════════════════════════════════
# 🧪 TEST
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    raise SystemExit(
        "Provide provider-observed price history through get_quick_kill_estimate(); generated CLI prices are retired"
    )
    print("⚔️ WAR STRATEGY - QUICK KILL PROBABILITY SYSTEM ⚔️\n")

    # Simulate price data with varying volatility

    # High volatility coin (good for quick kills)
    btc_prices = [100000]
    for _ in range(100):
        move = 0.0
        btc_prices.append(btc_prices[-1] * (1 + move))

    # Low volatility coin (slow kills)
    stable_prices = [1.0]
    for _ in range(100):
        move = 0.0
        stable_prices.append(stable_prices[-1] * (1 + move))

    # Get estimates
    print("🎯 HIGH VOLATILITY COIN (BTC-like):")
    btc_estimate = get_quick_kill_estimate('BTCUSD', 'kraken', btc_prices)
    print(f"   Probability of penny profit: {btc_estimate.prob_penny_profit*100:.1f}%")
    print(f"   Probability of quick kill: {btc_estimate.prob_quick_kill*100:.1f}%")
    print(f"   Estimated bars to profit: {btc_estimate.estimated_bars_to_profit:.1f}")
    print(f"   Estimated time: {btc_estimate.estimated_seconds/60:.1f} minutes")
    print(f"   GO SIGNAL: {'✅ ATTACK!' if btc_estimate.go_signal else '❌ HOLD'}")
    print(f"   Priority: {btc_estimate.priority}/10")
    print(f"   Reason: {btc_estimate.reason}")

    print("\n🐢 LOW VOLATILITY COIN (stablecoin-like):")
    stable_estimate = get_quick_kill_estimate('USDCUSD', 'kraken', stable_prices)
    print(f"   Probability of penny profit: {stable_estimate.prob_penny_profit*100:.1f}%")
    print(f"   Probability of quick kill: {stable_estimate.prob_quick_kill*100:.1f}%")
    print(f"   Estimated bars to profit: {stable_estimate.estimated_bars_to_profit:.1f}")
    print(f"   Estimated time: {stable_estimate.estimated_seconds/60:.1f} minutes")
    print(f"   GO SIGNAL: {'✅ ATTACK!' if stable_estimate.go_signal else '❌ HOLD'}")
    print(f"   Priority: {stable_estimate.priority}/10")
    print(f"   Reason: {stable_estimate.reason}")

    # Simulate a raid
    print("\n" + "="*60)
    print("🎯 SIMULATING A RAID...")
    print("="*60)

    # Start raid
    raid = start_raid('BTCUSD', 'kraken', 100000)

    # Simulate holding for 8 bars with profit
    time.sleep(0.5)  # Simulate some time passing
    exit_price = 100000 * (1 + REQUIRED_R + 0.001)  # Hit target + extra
    exit_value = POSITION_SIZE * (exit_price / 100000)

    # Complete raid
    completed = complete_raid('BTCUSD', exit_price, exit_value, 8)

    print("\n" + get_war_briefing())
