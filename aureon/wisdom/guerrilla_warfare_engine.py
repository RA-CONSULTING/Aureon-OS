#!/usr/bin/env python3
"""
☘️🔥 GUERRILLA FINANCIAL WARFARE ENGINE 🔥☘️
═══════════════════════════════════════════════════════════════════════════════
                    CELTIC HIT-AND-RUN TACTICS FOR FINANCIAL MARKETS
═══════════════════════════════════════════════════════════════════════════════

Historical Lessons Applied:
══════════════════════════════════════════════════════════════════════════════

1. CELTIC CHARIOT WARFARE (~800 BC - 400 AD)
   - Lightning strikes and rapid withdrawal
   - Never engage in prolonged combat
   - Use terrain (market structure) to advantage
   → Applied: Sub-second entry/exit decisions

2. BRIAN BORU'S TACTICS (Battle of Clontarf 1014)
   - Multiple coordinated fronts
   - Feigned retreats to draw enemy into traps
   - Unity of disparate forces under single command
   → Applied: Multi-exchange coordination with unified brain

3. GUERRILLA WAR TACTICS (1919-1921)
   - Flying columns - small, mobile, lethal
   - Intelligence network supremacy
   - Strike where enemy is weak, vanish before response
   → Applied: Scout networks across exchanges, penny profit strikes

4. AMBUSH DOCTRINE
   - Choose the battlefield (only enter favorable setups)
   - Strike fast, disengage faster
   - Never be where the enemy expects
   → Applied: Dynamic position rotation, preemptive movement

THE PHILOSOPHY:
═══════════════════════════════════════════════════════════════════════════════
"Our portfolio energy is IRISH - relentless, united, unconquerable.
Our enemy is the global financial ecosystem - vast but slow.
Our battlefronts are our exchanges - multiple simultaneous engagements.
Our weapon is cash and crypto - deployed with surgical precision.
Our goal: NEVER take a net loss. Every engagement is a victory."

TACTICAL PRINCIPLES:
═══════════════════════════════════════════════════════════════════════════════
1. MOVE BEFORE THE MARKET REACTS
   - Predictive positioning based on momentum signatures
   - Exit signals trigger BEFORE price reversal completes

2. MULTIPLE BATTLEFRONTS
   - Simultaneous operations across Binance, Kraken, Capital, Alpaca
   - Cross-exchange intelligence sharing
   - Coordinated strikes when opportunity aligns

3. FLYING COLUMNS
   - Small, nimble position sizes ($10-$20)
   - Quick in, quick out
   - Multiple columns operating independently

4. INTELLIGENCE SUPREMACY
   - Probability matrices guide all decisions
   - Historical pattern recognition
   - Real-time volatility assessment

5. UNITY OF COMMAND
   - Single brain coordinates all operations
   - No conflicting signals
   - All systems report to central command

"Tiocfaidh ár lá" - Our day will come. Through penny by penny, we build empire.

Gary Leckey | December 2025
"The flame ignited cannot be extinguished - it only grows stronger."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import math
import random
import threading
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict
from enum import Enum
import asyncio

# =============================================================================
# 🏛️ TACTICAL DOCTRINE CONFIGURATION
# =============================================================================

class TacticalMode(Enum):
    """Combat modes based on Celtic warfare phases"""
    RECONNAISSANCE = "recon"           # Gathering intelligence, no engagement
    AMBUSH = "ambush"                  # Waiting for perfect setup
    FLYING_COLUMN = "flying_column"   # Active hit-and-run operations
    COORDINATED_STRIKE = "coord"      # Multi-front simultaneous attack
    RETREAT = "retreat"               # Defensive, close positions only
    SIEGE = "siege"                   # Patient hold for inevitable victory


@dataclass
class BattlefrontStatus:
    """Status of each exchange battlefront"""
    exchange: str
    is_active: bool = True
    positions_open: int = 0
    capital_deployed: float = 0.0
    capital_available: float = 0.0
    kills_today: int = 0
    net_pnl_today: float = 0.0
    last_kill_time: float = 0
    volatility_index: float = 0.5
    response_time_ms: float = 100.0
    best_pairs: List[str] = field(default_factory=list)
    

@dataclass
class FlyingColumn:
    """A flying column - small mobile trading unit"""
    column_id: str
    exchange: str
    symbol: str
    entry_price: float
    entry_time: float
    position_size: float
    entry_value: float
    
    # Tactical state
    target_profit: float = 0.0
    max_drawdown_seen: float = 0.0
    cycles_held: int = 0
    status: str = "active"
    
    # Preemptive exit triggers
    momentum_at_entry: float = 0.0
    momentum_reversal_threshold: float = -0.5
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """Calculate current unrealized P&L"""
        current_value = self.position_size * current_price / self.entry_price
        return current_value - self.entry_value


@dataclass
class IntelligenceReport:
    """Intelligence gathered about market conditions"""
    timestamp: float
    exchange: str
    symbol: str
    
    # Price intelligence
    current_price: float
    price_momentum_1m: float  # 1-minute momentum
    price_momentum_5m: float  # 5-minute momentum
    price_momentum_15m: float  # 15-minute momentum
    
    # Volume intelligence
    volume_surge: bool = False
    volume_ratio: float = 1.0
    
    # Volatility intelligence
    current_volatility: float = 0.0
    volatility_trend: str = "stable"  # expanding, contracting, stable
    
    # Pattern intelligence
    support_nearby: bool = False
    resistance_nearby: bool = False
    trend_direction: str = "neutral"
    
    # Opportunity score
    ambush_score: float = 0.0  # 0-1, suitability for ambush
    quick_kill_probability: float = 0.0
    estimated_bars_to_profit: int = 0


# =============================================================================
# ☘️ THE CELTIC WAR COUNCIL - CENTRAL COMMAND
# =============================================================================

GUERRILLA_CONFIG = {
    # ═══════════════════════════════════════════════════════════════════════
    # 🗡️ STRIKE PARAMETERS - PREEMPTIVE AND FAST
    # ═══════════════════════════════════════════════════════════════════════
    'PREEMPTIVE_EXIT_ENABLED': True,      # Exit BEFORE price reverses fully
    'MOMENTUM_REVERSAL_THRESHOLD': -0.3,   # Exit if momentum drops this much
    'VOLATILITY_SPIKE_EXIT': True,         # Exit on sudden volatility increase
    'MAX_TIME_IN_POSITION_SEC': 300,       # 5 minutes max exposure (siege override)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ⚔️ FLYING COLUMN CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════
    'MAX_COLUMNS_PER_EXCHANGE': 3,         # 3 flying columns per battlefront
    'MAX_TOTAL_COLUMNS': 10,               # 10 total across all fronts
    'COLUMN_SIZE_USD': 10.0,               # $10 per column (small and nimble)
    'COLUMN_SPACING_SEC': 2.0,             # Minimum 2 sec between column deployments
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎯 AMBUSH PARAMETERS - CHOOSE YOUR BATTLEFIELD
    # ═══════════════════════════════════════════════════════════════════════
    'MIN_AMBUSH_SCORE': 0.65,              # Only ambush with 65%+ score
    'REQUIRE_MOMENTUM_ALIGNMENT': True,    # All timeframes must agree
    'REQUIRE_VOLUME_CONFIRMATION': True,   # Need volume supporting move
    'AVOID_RESISTANCE_ZONE': True,         # Don't enter near resistance
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🌐 MULTI-FRONT COORDINATION
    # ═══════════════════════════════════════════════════════════════════════
    'COORDINATED_STRIKE_THRESHOLD': 0.80,  # 80%+ score triggers coord strike
    'CROSS_EXCHANGE_ARBITRAGE': True,      # Exploit price differences
    'INTELLIGENCE_SHARING': True,          # Share intel between fronts
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🏃 RETREAT PARAMETERS - LIVE TO FIGHT ANOTHER DAY
    # ═══════════════════════════════════════════════════════════════════════
    'DAILY_LOSS_LIMIT_PCT': 0.0,           # 0% - WE DON'T LOSE
    'EMERGENCY_RETREAT_DRAWDOWN': 0.05,    # 5% portfolio drawdown triggers retreat
    'RETREAT_COOLDOWN_SEC': 60,            # 1 minute cooldown after retreat
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🧠 INTELLIGENCE PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════
    'INTEL_UPDATE_INTERVAL_SEC': 1.0,      # Update intel every second
    'MOMENTUM_LOOKBACK_BARS': 10,          # Bars for momentum calculation
    'VOLATILITY_LOOKBACK_BARS': 20,        # Bars for volatility calculation
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎖️ VICTORY CONDITIONS - 🚀 COMPOUND MODE!
    # ═══════════════════════════════════════════════════════════════════════
    'PENNY_PROFIT_TARGET': 0.0,            # 🚀 COMPOUND MODE: $0 minimum - take ANY profit!
    'INSTANT_VICTORY_EXIT': True,          # Exit immediately on ANY profit
    'CELEBRATE_KILLS': True,               # Log kills with celebration
    'TRACK_ALL_KILLS': True,               # Keep detailed kill records
}


# =============================================================================
# 📜 CELTIC WISDOM - THE SAYINGS OF THE WARRIORS
# =============================================================================

CELTIC_WISDOM = [
    # Ancient Celtic Proverbs
    "Níl neart go cur le chéile - There is no strength without unity",
    "Is fearr Gaeilge briste, ná Béarla cliste - Broken Irish beats clever English",
    "Mol an óige agus tiocfaidh sí - Praise the young and they will flourish",
    "Ní neart go cur le chéile - Unity is strength",
    
    # Irish Warrior Wisdom
    "Strike like the wind, vanish like the mist",
    "The wolf does not concern himself with the opinion of sheep",
    "Better to die on your feet than live on your knees",
    "Our revenge will be the laughter of our children - Bobby Sands",
    
    # Trading Warrior Adaptation
    "One penny at a time, we build our freedom",
    "The market sleeps, but we do not",
    "They have the clocks, we have the time",
    "Every kill brings us closer to victory",
    "We don't lose - we only win or wait",
    "The flame ignited cannot be extinguished",
    "Tiocfaidh ár lá - Our day will come",
    
    # Battle Tactics
    "Choose your battlefield - never let them choose for you",
    "Move before they see you coming",
    "A flying column fears no army",
    "The ambush succeeds through patience",
    "Intelligence wins wars, not brute force",
]

def get_celtic_wisdom() -> str:
    """Get a random piece of Celtic wisdom"""
    return random.choice(CELTIC_WISDOM)


# =============================================================================
# 🎯 INTELLIGENCE NETWORK - KNOW YOUR ENEMY
# =============================================================================

class IntelligenceNetwork:
    """
    The eyes and ears of the guerrilla operation.
    Gathers intelligence across all battlefronts.
    """
    
    def __init__(self):
        self.intel_cache: Dict[str, Dict[str, IntelligenceReport]] = defaultdict(dict)
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self.volume_history: Dict[str, List[float]] = defaultdict(list)
        self.last_update: Dict[str, float] = {}
        
        # Pattern detection
        self.support_levels: Dict[str, List[float]] = defaultdict(list)
        self.resistance_levels: Dict[str, List[float]] = defaultdict(list)
        
    def update_price_feed(self, exchange: str, symbol: str, price: float, 
                         volume: float = 0) -> IntelligenceReport:
        """
        Update price feed and generate intelligence report.
        This is called continuously for each symbol being monitored.
        """
        key = f"{exchange}:{symbol}"
        now = time.time()
        
        # Store price history
        self.price_history[key].append(price)
        if len(self.price_history[key]) > 100:
            self.price_history[key] = self.price_history[key][-100:]
        
        # Store volume history
        self.volume_history[key].append(volume)
        if len(self.volume_history[key]) > 100:
            self.volume_history[key] = self.volume_history[key][-100:]
        
        # Calculate intelligence
        report = self._analyze_conditions(exchange, symbol, price, now)
        
        # Cache the report
        self.intel_cache[exchange][symbol] = report
        self.last_update[key] = now
        
        return report
    
    def _analyze_conditions(self, exchange: str, symbol: str, 
                           current_price: float, timestamp: float) -> IntelligenceReport:
        """Analyze market conditions and generate intelligence report"""
        key = f"{exchange}:{symbol}"
        prices = self.price_history[key]
        volumes = self.volume_history[key]
        
        # Calculate momentum at different timeframes
        mom_1m = self._calculate_momentum(prices, 6)    # ~1 minute (6 x 10sec)
        mom_5m = self._calculate_momentum(prices, 30)   # ~5 minutes
        mom_15m = self._calculate_momentum(prices, 90)  # ~15 minutes
        
        # Volume analysis
        volume_surge = False
        volume_ratio = 1.0
        if len(volumes) >= 10:
            avg_vol = sum(volumes[-20:-1]) / max(1, len(volumes[-20:-1]))
            if avg_vol > 0:
                volume_ratio = volumes[-1] / avg_vol
                volume_surge = volume_ratio > 1.5
        
        # Volatility analysis
        volatility = self._calculate_volatility(prices)
        vol_recent = self._calculate_volatility(prices[-10:]) if len(prices) >= 10 else volatility
        vol_older = self._calculate_volatility(prices[-30:-10]) if len(prices) >= 30 else volatility
        
        if vol_recent > vol_older * 1.2:
            vol_trend = "expanding"
        elif vol_recent < vol_older * 0.8:
            vol_trend = "contracting"
        else:
            vol_trend = "stable"
        
        # Trend detection
        if len(prices) >= 10:
            short_ma = sum(prices[-5:]) / 5
            long_ma = sum(prices[-20:]) / min(20, len(prices))
            if short_ma > long_ma * 1.001:
                trend = "bullish"
            elif short_ma < long_ma * 0.999:
                trend = "bearish"
            else:
                trend = "neutral"
        else:
            trend = "neutral"
        
        # Support/Resistance detection
        support, resistance = self._detect_sr_levels(prices)
        support_nearby = abs(current_price - support) / current_price < 0.01 if support > 0 else False
        resistance_nearby = abs(current_price - resistance) / current_price < 0.01 if resistance > 0 else False
        
        # Calculate ambush score
        ambush_score = self._calculate_ambush_score(
            mom_1m, mom_5m, mom_15m, volume_surge, volatility,
            vol_trend, support_nearby, resistance_nearby, trend
        )
        
        # Calculate quick kill probability
        quick_kill_prob, estimated_bars = self._estimate_quick_kill(
            volatility, mom_1m, trend
        )
        
        return IntelligenceReport(
            timestamp=timestamp,
            exchange=exchange,
            symbol=symbol,
            current_price=current_price,
            price_momentum_1m=mom_1m,
            price_momentum_5m=mom_5m,
            price_momentum_15m=mom_15m,
            volume_surge=volume_surge,
            volume_ratio=volume_ratio,
            current_volatility=volatility,
            volatility_trend=vol_trend,
            support_nearby=support_nearby,
            resistance_nearby=resistance_nearby,
            trend_direction=trend,
            ambush_score=ambush_score,
            quick_kill_probability=quick_kill_prob,
            estimated_bars_to_profit=estimated_bars
        )
    
    def _calculate_momentum(self, prices: List[float], lookback: int) -> float:
        """Calculate price momentum over lookback period"""
        if len(prices) < lookback + 1:
            return 0.0
        old_price = prices[-lookback - 1]
        new_price = prices[-1]
        if old_price == 0:
            return 0.0
        return (new_price - old_price) / old_price * 100
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility (standard deviation of returns)"""
        if len(prices) < 3:
            return 0.0
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        if not returns:
            return 0.0
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)
    
    def _detect_sr_levels(self, prices: List[float]) -> Tuple[float, float]:
        """Detect support and resistance levels"""
        if len(prices) < 10:
            return 0.0, 0.0
        
        # Simple method: use recent lows as support, highs as resistance
        recent = prices[-20:] if len(prices) >= 20 else prices
        support = min(recent)
        resistance = max(recent)
        
        return support, resistance
    
    def _calculate_ambush_score(self, mom_1m: float, mom_5m: float, mom_15m: float,
                                volume_surge: bool, volatility: float, vol_trend: str,
                                support_nearby: bool, resistance_nearby: bool,
                                trend: str) -> float:
        """
        Calculate ambush suitability score (0-1).
        Higher = better setup for hit-and-run trade.
        """
        score = 0.5  # Base score
        
        # Momentum alignment bonus
        if mom_1m > 0 and mom_5m > 0 and mom_15m > 0:
            score += 0.15  # All bullish
        elif mom_1m < 0 and mom_5m < 0 and mom_15m < 0:
            score += 0.10  # All bearish (can short)
        elif mom_1m * mom_5m > 0:
            score += 0.05  # At least two aligned
        else:
            score -= 0.10  # Conflicting signals
        
        # Volume surge bonus
        if volume_surge:
            score += 0.10
        
        # Volatility sweet spot
        if 0.003 < volatility < 0.015:
            score += 0.10  # Good volatility for quick moves
        elif volatility > 0.02:
            score -= 0.15  # Too volatile - dangerous
        
        # Volatility trend
        if vol_trend == "expanding":
            score += 0.05  # Expanding vol = opportunity
        elif vol_trend == "contracting":
            score -= 0.05  # Contracting = harder to profit
        
        # Support/Resistance
        if support_nearby and trend == "bullish":
            score += 0.10  # Bouncing off support
        if resistance_nearby:
            score -= 0.20  # Near resistance - dangerous
        
        return max(0.0, min(1.0, score))
    
    def _estimate_quick_kill(self, volatility: float, momentum: float, 
                            trend: str) -> Tuple[float, int]:
        """Estimate probability and time to penny profit"""
        # Required move for penny profit (approximately 1.5%)
        required_move = 0.015
        
        if volatility <= 0:
            return 0.3, 30
        
        # How many bars to hit target based on volatility
        bars_estimate = required_move / volatility
        bars_estimate = max(1, min(100, bars_estimate))
        
        # Probability based on momentum alignment
        if momentum > 0 and trend == "bullish":
            prob = 0.7
        elif momentum > 0:
            prob = 0.6
        elif trend == "bullish":
            prob = 0.55
        else:
            prob = 0.4
        
        # Adjust for time estimate
        if bars_estimate <= 10:
            prob += 0.1
        elif bars_estimate >= 30:
            prob -= 0.1
        
        return max(0.1, min(0.95, prob)), int(bars_estimate)
    
    def get_intel(self, exchange: str, symbol: str) -> Optional[IntelligenceReport]:
        """Get cached intelligence report"""
        return self.intel_cache.get(exchange, {}).get(symbol)
    
    def get_best_targets(self, exchange: str = None, min_score: float = 0.6,
                        limit: int = 10) -> List[IntelligenceReport]:
        """Get best ambush targets across battlefronts"""
        targets = []
        
        exchanges = [exchange] if exchange else self.intel_cache.keys()
        
        for ex in exchanges:
            for symbol, report in self.intel_cache.get(ex, {}).items():
                if report.ambush_score >= min_score:
                    targets.append(report)
        
        # Sort by score
        targets.sort(key=lambda x: x.ambush_score, reverse=True)
        
        return targets[:limit]


# =============================================================================
# ⚔️ FLYING COLUMN COMMANDER - TACTICAL OPERATIONS
# =============================================================================

class FlyingColumnCommander:
    """
    Commands all flying columns across battlefronts.
    Coordinates attacks, retreats, and intelligence operations.
    """
    
    def __init__(self):
        self.columns: Dict[str, FlyingColumn] = {}  # column_id -> FlyingColumn
        self.battlefronts: Dict[str, BattlefrontStatus] = {}
        self.intelligence = IntelligenceNetwork()
        
        # Kill tracking
        self.kills_today: int = 0
        self.net_pnl_today: float = 0.0
        self.total_kills: int = 0
        self.total_net_pnl: float = 0.0
        
        # Column management
        self._column_counter = 0
        self._last_deployment: Dict[str, float] = {}  # exchange -> timestamp
        
        # Tactical state
        self.current_mode = TacticalMode.RECONNAISSANCE
        self._retreat_until: float = 0
        
        # Load saved state
        self._load_state()
        
        logging.info("☘️ Flying Column Commander initialized")
        logging.info(f"   ⚔️ Total historical kills: {self.total_kills}")
        logging.info(f"   💰 Total historical P&L: ${self.total_net_pnl:.2f}")
    
    def _load_state(self):
        """Load saved war state"""
        try:
            if os.path.exists('guerrilla_state.json'):
                with open('guerrilla_state.json', 'r') as f:
                    data = json.load(f)
                    self.total_kills = data.get('total_kills', 0)
                    self.total_net_pnl = data.get('total_net_pnl', 0.0)
                    logging.info(f"☘️ Loaded guerrilla state: {self.total_kills} kills, ${self.total_net_pnl:.2f} total")
        except Exception as e:
            logging.warning(f"☘️ Fresh guerrilla state: {e}")
    
    def _save_state(self):
        """Save war state"""
        try:
            with open('guerrilla_state.json', 'w') as f:
                json.dump({
                    'total_kills': self.total_kills,
                    'total_net_pnl': self.total_net_pnl,
                    'last_updated': time.time(),
                    'kills_today': self.kills_today,
                    'pnl_today': self.net_pnl_today
                }, f, indent=2)
        except Exception as e:
            logging.error(f"☘️ Could not save state: {e}")
    
    def register_battlefront(self, exchange: str, capital: float = 1000.0):
        """Register a new battlefront (exchange)"""
        self.battlefronts[exchange] = BattlefrontStatus(
            exchange=exchange,
            capital_available=capital
        )
        logging.info(f"⚔️ Battlefront registered: {exchange} (${capital:.2f} available)")
    
    def update_intelligence(self, exchange: str, symbol: str, price: float,
                           volume: float = 0) -> IntelligenceReport:
        """Update intelligence for a symbol"""
        return self.intelligence.update_price_feed(exchange, symbol, price, volume)
    
    def should_deploy_column(self, exchange: str, symbol: str) -> Tuple[bool, str]:
        """
        Determine if we should deploy a new flying column.
        
        Returns: (should_deploy, reason)
        """
        config = GUERRILLA_CONFIG
        
        # Check if in retreat mode
        if time.time() < self._retreat_until:
            return False, "🏃 In retreat - cooling down"
        
        # Check column limits
        columns_on_exchange = sum(1 for c in self.columns.values() 
                                  if c.exchange == exchange and c.status == "active")
        if columns_on_exchange >= config['MAX_COLUMNS_PER_EXCHANGE']:
            return False, f"❌ Max columns on {exchange} ({columns_on_exchange})"
        
        total_columns = sum(1 for c in self.columns.values() if c.status == "active")
        if total_columns >= config['MAX_TOTAL_COLUMNS']:
            return False, f"❌ Max total columns ({total_columns})"
        
        # Check spacing
        last_deploy = self._last_deployment.get(exchange, 0)
        if time.time() - last_deploy < config['COLUMN_SPACING_SEC']:
            return False, "⏳ Deployment spacing - wait"
        
        # Check if we already have a column on this symbol
        for c in self.columns.values():
            if c.exchange == exchange and c.symbol == symbol and c.status == "active":
                return False, f"⚠️ Already have column on {symbol}"
        
        # Get intelligence
        intel = self.intelligence.get_intel(exchange, symbol)
        if not intel:
            return False, "📡 No intelligence available"
        
        # Check ambush score
        if intel.ambush_score < config['MIN_AMBUSH_SCORE']:
            return False, f"📊 Ambush score too low ({intel.ambush_score:.2f})"
        
        # Check momentum alignment
        if config['REQUIRE_MOMENTUM_ALIGNMENT']:
            if not (intel.price_momentum_1m > 0 and intel.price_momentum_5m > 0):
                return False, "📈 Momentum not aligned"
        
        # Avoid resistance
        if config['AVOID_RESISTANCE_ZONE'] and intel.resistance_nearby:
            return False, "🚧 Near resistance - avoid"
        
        # ✅ All checks passed
        return True, f"✅ DEPLOY! Score: {intel.ambush_score:.2f}, Quick kill: {intel.quick_kill_probability*100:.0f}%"
    
    def deploy_column(self, exchange: str, symbol: str, entry_price: float,
                     position_size: float = None) -> Optional[FlyingColumn]:
        """
        Deploy a new flying column.
        
        Returns the FlyingColumn if deployed, None if rejected.
        """
        config = GUERRILLA_CONFIG
        
        # Final check
        can_deploy, reason = self.should_deploy_column(exchange, symbol)
        if not can_deploy:
            logging.warning(f"☘️ Column deployment rejected: {reason}")
            return None
        
        # Get intelligence for this target
        intel = self.intelligence.get_intel(exchange, symbol)
        
        # Create column
        self._column_counter += 1
        column_id = f"COL-{self._column_counter:04d}"
        pos_size = position_size or config['COLUMN_SIZE_USD']
        
        column = FlyingColumn(
            column_id=column_id,
            exchange=exchange,
            symbol=symbol,
            entry_price=entry_price,
            entry_time=time.time(),
            position_size=pos_size,
            entry_value=pos_size,
            target_profit=0.01,  # $0.01 penny profit target
            momentum_at_entry=intel.price_momentum_1m if intel else 0,
            status="active"
        )
        
        self.columns[column_id] = column
        self._last_deployment[exchange] = time.time()
        
        # Update battlefront status
        if exchange in self.battlefronts:
            self.battlefronts[exchange].positions_open += 1
            self.battlefronts[exchange].capital_deployed += pos_size
        
        # Log deployment with Celtic wisdom
        wisdom = get_celtic_wisdom()
        ambush_str = f"{intel.ambush_score:.2f}" if intel else 'N/A'
        quick_kill_str = f"{intel.quick_kill_probability*100:.0f}%" if intel else 'N/A'
        logging.info(f"""
☘️⚔️ FLYING COLUMN DEPLOYED ⚔️☘️
   Column: {column_id}
   Battlefront: {exchange}
   Target: {symbol}
   Entry: ${entry_price:.6f}
   Size: ${pos_size:.2f}
   Ambush Score: {ambush_str}
   Quick Kill Prob: {quick_kill_str}
   
   ☘️ "{wisdom}"
""")
        
        return column
    
    def check_column_exit(self, column_id: str, current_price: float,
                         fee_rate: float = 0.007) -> Tuple[bool, str, float]:
        """
        Check if a column should exit.
        
        Returns: (should_exit, reason, net_pnl)
        """
        column = self.columns.get(column_id)
        if not column or column.status != "active":
            return False, "Column not active", 0.0
        
        config = GUERRILLA_CONFIG
        
        # Calculate P&L
        current_value = column.position_size * (current_price / column.entry_price)
        gross_pnl = current_value - column.entry_value
        total_fees = (column.entry_value + current_value) * (fee_rate / 2)
        net_pnl = gross_pnl - total_fees
        
        # Track max drawdown
        if gross_pnl < 0:
            column.max_drawdown_seen = max(column.max_drawdown_seen, abs(gross_pnl))
        
        column.cycles_held += 1
        
        # ═══════════════════════════════════════════════════════════════
        # 🪙 SHARED GOAL: PENNY PROFIT ACHIEVED - INSTANT EXIT
        # ═══════════════════════════════════════════════════════════════
        # Try to get dynamic penny threshold
        penny_target = column.target_profit
        try:
            from aureon.trading.aureon_unified_ecosystem import get_penny_threshold
            penny = get_penny_threshold(column.exchange, column.entry_value)
            if penny:
                penny_target = penny['win_gte']
        except ImportError:
            pass
        if net_pnl >= penny_target:
            return True, f"🪙 SHARED GOAL! Net: ${net_pnl:.4f} >= ${penny_target:.4f}", net_pnl
        
        # ═══════════════════════════════════════════════════════════════
        # 🏃 EXIT CHECK 2: PREEMPTIVE MOMENTUM REVERSAL
        # ═══════════════════════════════════════════════════════════════
        if config['PREEMPTIVE_EXIT_ENABLED']:
            intel = self.intelligence.get_intel(column.exchange, column.symbol)
            if intel:
                # Check if momentum has reversed significantly
                mom_change = intel.price_momentum_1m - column.momentum_at_entry
                if mom_change < config['MOMENTUM_REVERSAL_THRESHOLD']:
                    # Only exit if we're at profit (even tiny)
                    if net_pnl > 0:
                        return True, f"🏃 PREEMPTIVE EXIT - momentum reversal (net: ${net_pnl:.4f})", net_pnl
        
        # ═══════════════════════════════════════════════════════════════
        # ⏱️ EXIT CHECK 3: MAX TIME IN POSITION (Siege mode override)
        # ═══════════════════════════════════════════════════════════════
        time_held = time.time() - column.entry_time
        if time_held > config['MAX_TIME_IN_POSITION_SEC']:
            # Only exit if profitable
            if net_pnl > 0:
                return True, f"⏱️ TIME LIMIT - exiting with profit (${net_pnl:.4f})", net_pnl
            # Otherwise, switch to siege mode - wait for victory
            column.status = "siege"
            return False, f"🏰 SIEGE MODE - holding for victory ({time_held:.0f}s)", net_pnl
        
        # ═══════════════════════════════════════════════════════════════
        # 🛡️ NO EXIT - HOLD FOR VICTORY
        # ═══════════════════════════════════════════════════════════════
        return False, f"🛡️ Holding... P&L: ${net_pnl:.4f}, held: {column.cycles_held} cycles", net_pnl
    
    def complete_column_kill(self, column_id: str, exit_price: float, 
                            net_pnl: float, reason: str) -> bool:
        """Record a completed column operation (kill)"""
        column = self.columns.get(column_id)
        if not column:
            return False
        
        # Update column status
        column.status = "completed"
        
        # Update battlefront
        if column.exchange in self.battlefronts:
            bf = self.battlefronts[column.exchange]
            bf.positions_open -= 1
            bf.capital_deployed -= column.position_size
            if net_pnl > 0:
                bf.kills_today += 1
                bf.last_kill_time = time.time()
            bf.net_pnl_today += net_pnl
        
        # Update global stats
        if net_pnl > 0:
            self.kills_today += 1
            self.total_kills += 1
        self.net_pnl_today += net_pnl
        self.total_net_pnl += net_pnl
        
        # Save state
        self._save_state()
        
        # Log the kill
        time_held = time.time() - column.entry_time
        emoji = "💰" if net_pnl > 0 else "❌"
        wisdom = get_celtic_wisdom() if net_pnl > 0 else ""
        
        logging.info(f"""
{emoji}☘️ COLUMN OPERATION COMPLETE ☘️{emoji}
   Column: {column_id}
   Symbol: {column.symbol}
   Battlefront: {column.exchange}
   Entry: ${column.entry_price:.6f} → Exit: ${exit_price:.6f}
   Time Held: {time_held:.1f}s ({column.cycles_held} cycles)
   Net P&L: ${net_pnl:.4f}
   Reason: {reason}
   
   📊 Today: {self.kills_today} kills, ${self.net_pnl_today:.4f} P&L
   📊 Total: {self.total_kills} kills, ${self.total_net_pnl:.2f} P&L
   
   {"☘️ " + wisdom if wisdom else ""}
""")
        
        return True
    
    def initiate_retreat(self, reason: str = "Manual retreat"):
        """Initiate a tactical retreat - close all profitable positions"""
        self._retreat_until = time.time() + GUERRILLA_CONFIG['RETREAT_COOLDOWN_SEC']
        self.current_mode = TacticalMode.RETREAT
        
        logging.warning(f"""
🏃☘️ TACTICAL RETREAT INITIATED ☘️🏃
   Reason: {reason}
   Cooldown: {GUERRILLA_CONFIG['RETREAT_COOLDOWN_SEC']}s
   
   "Live to fight another day"
""")
    
    def get_active_columns(self) -> List[FlyingColumn]:
        """Get all active flying columns"""
        return [c for c in self.columns.values() if c.status in ("active", "siege")]
    
    def get_war_status(self) -> str:
        """Get comprehensive war status"""
        active_columns = self.get_active_columns()
        
        status = f"""
☘️═══════════════════════════════════════════════════════════════════════════════☘️
                        GUERRILLA WARFARE STATUS REPORT
☘️═══════════════════════════════════════════════════════════════════════════════☘️

🎖️ CAMPAIGN STATUS:
   Mode: {self.current_mode.value.upper()}
   Total Kills (All Time): {self.total_kills}
   Total Net P&L (All Time): ${self.total_net_pnl:.2f}
   
📊 TODAY'S OPERATIONS:
   Kills Today: {self.kills_today}
   Net P&L Today: ${self.net_pnl_today:.4f}

⚔️ ACTIVE FLYING COLUMNS: {len(active_columns)}
"""
        for col in active_columns:
            time_held = time.time() - col.entry_time
            status += f"""
   • {col.column_id} | {col.exchange}:{col.symbol}
     Entry: ${col.entry_price:.6f} | Size: ${col.position_size:.2f}
     Status: {col.status.upper()} | Held: {time_held:.0f}s
"""

        status += """
🌐 BATTLEFRONT STATUS:
"""
        for ex, bf in self.battlefronts.items():
            status += f"""
   {ex}:
     Positions: {bf.positions_open} | Capital Deployed: ${bf.capital_deployed:.2f}
     Kills Today: {bf.kills_today} | P&L Today: ${bf.net_pnl_today:.4f}
"""

        status += f"""
☘️═══════════════════════════════════════════════════════════════════════════════☘️
                    "{get_celtic_wisdom()}"
☘️═══════════════════════════════════════════════════════════════════════════════☘️
"""
        return status


# =============================================================================
# 🔥 THE COORDINATED STRIKE ENGINE - MULTI-FRONT ATTACKS
# =============================================================================

class CoordinatedStrikeEngine:
    """
    Coordinates simultaneous strikes across multiple battlefronts.
    When an exceptional opportunity appears, strike everywhere at once.
    """
    
    def __init__(self, commander: FlyingColumnCommander):
        self.commander = commander
        self.strike_history: List[Dict] = []
        
    def detect_coordination_opportunity(self) -> Optional[Dict]:
        """
        Detect if there's an opportunity for a coordinated strike.
        
        Returns strike plan if opportunity exists.
        """
        config = GUERRILLA_CONFIG
        
        # Get best targets across all battlefronts
        targets = self.commander.intelligence.get_best_targets(
            min_score=config['COORDINATED_STRIKE_THRESHOLD']
        )
        
        if len(targets) < 2:
            return None
        
        # Check if multiple battlefronts have good opportunities
        exchanges_with_opportunities = set(t.exchange for t in targets)
        
        if len(exchanges_with_opportunities) < 2:
            return None
        
        # Build strike plan
        strike_plan = {
            'timestamp': time.time(),
            'targets': [],
            'total_capital': 0,
            'expected_kills': 0
        }
        
        for target in targets[:5]:  # Max 5 targets in coordinated strike
            strike_plan['targets'].append({
                'exchange': target.exchange,
                'symbol': target.symbol,
                'score': target.ambush_score,
                'quick_kill_prob': target.quick_kill_probability,
                'price': target.current_price
            })
            strike_plan['total_capital'] += config['COLUMN_SIZE_USD']
            strike_plan['expected_kills'] += target.quick_kill_probability
        
        return strike_plan
    
    def execute_coordinated_strike(self, strike_plan: Dict, 
                                   execute_fn: Callable) -> int:
        """
        Execute a coordinated strike across multiple battlefronts.
        
        Args:
            strike_plan: Plan from detect_coordination_opportunity
            execute_fn: Function to execute trades (exchange, symbol, price) -> bool
            
        Returns: Number of columns deployed
        """
        deployed = 0
        
        logging.info(f"""
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
                      COORDINATED STRIKE INITIATED
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
   Targets: {len(strike_plan['targets'])}
   Total Capital: ${strike_plan['total_capital']:.2f}
   Expected Kills: {strike_plan['expected_kills']:.1f}
""")
        
        for target in strike_plan['targets']:
            try:
                success = execute_fn(target['exchange'], target['symbol'], target['price'])
                if success:
                    deployed += 1
                    logging.info(f"   ✅ {target['exchange']}:{target['symbol']} - DEPLOYED")
                else:
                    logging.warning(f"   ❌ {target['exchange']}:{target['symbol']} - FAILED")
            except Exception as e:
                logging.error(f"   💥 {target['exchange']}:{target['symbol']} - ERROR: {e}")
        
        strike_plan['columns_deployed'] = deployed
        self.strike_history.append(strike_plan)
        
        logging.info(f"""
   
   ⚔️ STRIKE COMPLETE: {deployed}/{len(strike_plan['targets'])} columns deployed
   
☘️🔥═══════════════════════════════════════════════════════════════════════🔥☘️
""")
        
        return deployed


# =============================================================================
# 🌐 GLOBAL GUERRILLA COMMANDER - SINGLETON
# =============================================================================

_COMMANDER: Optional[FlyingColumnCommander] = None
_STRIKE_ENGINE: Optional[CoordinatedStrikeEngine] = None


def get_guerrilla_commander() -> FlyingColumnCommander:
    """Get the global guerrilla commander instance"""
    global _COMMANDER
    if _COMMANDER is None:
        _COMMANDER = FlyingColumnCommander()
    return _COMMANDER


def get_strike_engine() -> CoordinatedStrikeEngine:
    """Get the global coordinated strike engine"""
    global _STRIKE_ENGINE, _COMMANDER
    if _STRIKE_ENGINE is None:
        _STRIKE_ENGINE = CoordinatedStrikeEngine(get_guerrilla_commander())
    return _STRIKE_ENGINE


# =============================================================================
# 🎯 QUICK ACCESS FUNCTIONS
# =============================================================================

def update_intel(exchange: str, symbol: str, price: float, volume: float = 0) -> IntelligenceReport:
    """Quick function to update intelligence"""
    return get_guerrilla_commander().update_intelligence(exchange, symbol, price, volume)


def should_attack(exchange: str, symbol: str) -> Tuple[bool, str]:
    """Should we attack this target?"""
    return get_guerrilla_commander().should_deploy_column(exchange, symbol)


def deploy_flying_column(exchange: str, symbol: str, entry_price: float,
                        position_size: float = None) -> Optional[FlyingColumn]:
    """Deploy a new flying column"""
    return get_guerrilla_commander().deploy_column(exchange, symbol, entry_price, position_size)


def check_exit(column_id: str, current_price: float) -> Tuple[bool, str, float]:
    """Check if column should exit"""
    return get_guerrilla_commander().check_column_exit(column_id, current_price)


def complete_kill(column_id: str, exit_price: float, net_pnl: float, reason: str) -> bool:
    """Complete a column kill"""
    return get_guerrilla_commander().complete_column_kill(column_id, exit_price, net_pnl, reason)


def get_war_status() -> str:
    """Get current war status"""
    return get_guerrilla_commander().get_war_status()


def get_active_columns() -> List[FlyingColumn]:
    """Get all active columns"""
    return get_guerrilla_commander().get_active_columns()


# =============================================================================
