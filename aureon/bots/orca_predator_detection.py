#!/usr/bin/env python3
"""
🦈🔍 ORCA PREDATOR DETECTION SYSTEM - WHO'S HUNTING WHO? 🔍🦈
═══════════════════════════════════════════════════════════════════════════════
🟡 The PredatorDetector class records REAL orders + REAL price reactions.
   This production module accepts observed order and reaction events only.
   Standalone generated-order drivers have been removed.
═══════════════════════════════════════════════════════════════════════════════

DETECTS WHEN MARKET MAKERS ARE ADAPTING TO *YOUR* PATTERNS

The Game:
  - You place order → Price moves against you within 50-200ms = FRONT-RUNNING
  - Your pattern works → Then suddenly stops working = THEY ADAPTED
  - Same firm shows up on ALL your trades = YOU'RE BEING TARGETED

This module tracks:
  1. Order → Adverse Move Correlation (are you being front-run?)
  2. Strategy Decay Detection (did they learn your pattern?)
  3. Firm Stalking Score (is one firm always counter-trading you?)
  4. Timing Attack Detection (suspiciously fast reactions)

Gary Leckey | Counter-Intelligence Division | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import json
import time
import math
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrderEvent:
    """Single order placement event."""
    timestamp: float
    symbol: str
    side: str  # 'buy' or 'sell'
    price: float
    quantity: float
    exchange: str
    order_id: str = ""


@dataclass  
class PriceReaction:
    """Price movement after an order."""
    order_timestamp: float
    reaction_ms: float  # How fast price moved
    adverse_move: bool  # Did price move against us?
    move_size_pct: float  # How much it moved
    suspected_firm: str = "unknown"


@dataclass
class StrategyPerformance:
    """Track if a strategy is decaying (they learned it)."""
    strategy_name: str
    win_rate_7d: float = 0.0
    win_rate_24h: float = 0.0
    win_rate_1h: float = 0.0
    decay_detected: bool = False
    decay_rate: float = 0.0  # How fast win rate is dropping


@dataclass
class PredatorProfile:
    """Profile of an entity that might be hunting us."""
    firm_id: str
    times_detected: int = 0
    avg_reaction_ms: float = 0.0
    stalking_score: float = 0.0  # 0-1, how often they counter-trade us
    symbols_targeted: List[str] = field(default_factory=list)
    last_seen: float = 0.0
    threat_level: str = "low"  # low, medium, high, critical


@dataclass
class HuntingReport:
    """Full report on who's hunting us."""
    timestamp: float
    total_orders_analyzed: int
    front_run_rate: float  # % of orders that got front-run
    strategy_decay_alert: bool
    top_predators: List[PredatorProfile] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    threat_level: str = "green"  # green, yellow, orange, red


# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 PREDATOR DETECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class OrcaPredatorDetector:
    """
    Detects when market makers/HFT firms are adapting to YOUR trading patterns.
    
    THE GAME THEORY:
    - If your orders consistently get worse fills = you're being read
    - If your strategy suddenly stops working = they adapted
    - If same entity appears on all your adverse trades = you're being stalked
    """
    
    def __init__(self, history_file: str = "predator_detection_history.json"):
        self.history_file = history_file
        
        # Order tracking
        self.recent_orders: List[OrderEvent] = []
        self.price_reactions: List[PriceReaction] = []
        
        # Predator profiles
        self.predators: Dict[str, PredatorProfile] = {}
        
        # Strategy performance tracking
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        
        # Rolling statistics
        self.front_run_count_1h = 0
        self.total_orders_1h = 0
        self.front_run_count_24h = 0
        self.total_orders_24h = 0
        
        # Thresholds
        self.FRONT_RUN_THRESHOLD_MS = 200  # Reaction faster than this = suspicious
        self.ADVERSE_MOVE_THRESHOLD_PCT = 0.05  # Move against us > 0.05%
        self.STALKING_THRESHOLD = 0.6  # Same firm on >60% of adverse trades
        self.DECAY_ALERT_THRESHOLD = 0.2  # Win rate dropped >20%
        
        # Load history
        self._load_history()
        
        print("🦈🔍 PREDATOR DETECTION SYSTEM ONLINE")
        print(f"   Front-run threshold: {self.FRONT_RUN_THRESHOLD_MS}ms")
        print(f"   Stalking threshold: {self.STALKING_THRESHOLD * 100}%")
    
    def _load_history(self):
        """Load historical data."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.front_run_count_24h = data.get('front_run_count_24h', 0)
                    self.total_orders_24h = data.get('total_orders_24h', 0)
                    # Load predator profiles
                    for firm_id, profile_data in data.get('predators', {}).items():
                        self.predators[firm_id] = PredatorProfile(**profile_data)
        except Exception as e:
            print(f"⚠️ Could not load predator history: {e}")
    
    def _save_history(self):
        """Save to disk."""
        try:
            data = {
                'front_run_count_24h': self.front_run_count_24h,
                'total_orders_24h': self.total_orders_24h,
                'predators': {k: asdict(v) for k, v in self.predators.items()},
                'last_updated': time.time()
            }
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save predator history: {e}")
    
    # ───────────────────────────────────────────────────────────────────────
    # 📡 ORDER TRACKING
    # ───────────────────────────────────────────────────────────────────────
    
    def record_order(self, order: OrderEvent):
        """Record an order we placed."""
        self.recent_orders.append(order)
        self.total_orders_1h += 1
        self.total_orders_24h += 1
        
        # Keep only recent orders (last 1000)
        if len(self.recent_orders) > 1000:
            self.recent_orders = self.recent_orders[-1000:]
    
    def record_price_after_order(self, order: OrderEvent, price_after: float, 
                                  reaction_time_ms: float, detected_firm: str = "unknown"):
        """
        Record what happened to price after we placed an order.
        
        FRONT-RUN DETECTION:
        - If we BUY and price JUMPS UP within 200ms = front-run
        - If we SELL and price DROPS within 200ms = front-run
        """
        # Calculate if move was adverse
        if order.side == 'buy':
            move_pct = (price_after - order.price) / order.price * 100
            adverse = move_pct > self.ADVERSE_MOVE_THRESHOLD_PCT
        else:  # sell
            move_pct = (order.price - price_after) / order.price * 100
            adverse = move_pct > self.ADVERSE_MOVE_THRESHOLD_PCT
        
        # Was it suspiciously fast?
        is_front_run = adverse and reaction_time_ms < self.FRONT_RUN_THRESHOLD_MS
        
        reaction = PriceReaction(
            order_timestamp=order.timestamp,
            reaction_ms=reaction_time_ms,
            adverse_move=adverse,
            move_size_pct=abs(move_pct),
            suspected_firm=detected_firm
        )
        self.price_reactions.append(reaction)
        
        if is_front_run:
            self.front_run_count_1h += 1
            self.front_run_count_24h += 1
            self._update_predator_profile(detected_firm, order.symbol, reaction_time_ms)
            print(f"🚨 FRONT-RUN DETECTED on {order.symbol}!")
            print(f"   Reaction: {reaction_time_ms:.0f}ms | Move: {move_pct:.3f}%")
            print(f"   Suspected: {detected_firm}")
        
        # Keep only recent reactions
        if len(self.price_reactions) > 1000:
            self.price_reactions = self.price_reactions[-1000:]
        
        return is_front_run
    
    def _update_predator_profile(self, firm_id: str, symbol: str, reaction_ms: float):
        """Update profile for a suspected predator."""
        if firm_id not in self.predators:
            self.predators[firm_id] = PredatorProfile(firm_id=firm_id)
        
        p = self.predators[firm_id]
        p.times_detected += 1
        p.last_seen = time.time()
        
        # Rolling average reaction time
        p.avg_reaction_ms = (p.avg_reaction_ms * (p.times_detected - 1) + reaction_ms) / p.times_detected
        
        # Track symbols they target
        if symbol not in p.symbols_targeted:
            p.symbols_targeted.append(symbol)
        
        # Calculate stalking score
        total_adverse = sum(1 for r in self.price_reactions if r.adverse_move)
        if total_adverse > 0:
            firm_adverse = sum(1 for r in self.price_reactions 
                              if r.adverse_move and r.suspected_firm == firm_id)
            p.stalking_score = firm_adverse / total_adverse
        
        # Update threat level
        if p.stalking_score > 0.8 and p.times_detected > 10:
            p.threat_level = "critical"
        elif p.stalking_score > 0.6 and p.times_detected > 5:
            p.threat_level = "high"
        elif p.stalking_score > 0.4:
            p.threat_level = "medium"
        else:
            p.threat_level = "low"
    
    # ───────────────────────────────────────────────────────────────────────
    # 📉 STRATEGY DECAY DETECTION
    # ───────────────────────────────────────────────────────────────────────
    
    def record_trade_outcome(self, strategy_name: str, won: bool, timestamp: float = None):
        """Record if a trade won or lost, to detect strategy decay."""
        timestamp = timestamp or time.time()
        
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = StrategyPerformance(
                strategy_name=strategy_name
            )
        
        # This would integrate with your actual trade history
        # For now, we'll track rolling win rates
        pass
    
    def check_strategy_decay(self, strategy_name: str, 
                             win_rate_7d: float, 
                             win_rate_24h: float,
                             win_rate_1h: float) -> Tuple[bool, float]:
        """
        Check if a strategy is decaying (they learned our pattern).
        
        DECAY DETECTION:
        - If 7-day win rate = 65% but 1-hour win rate = 40%
        - That's a 25% drop = THEY ADAPTED
        """
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = StrategyPerformance(
                strategy_name=strategy_name
            )
        
        sp = self.strategy_performance[strategy_name]
        sp.win_rate_7d = win_rate_7d
        sp.win_rate_24h = win_rate_24h
        sp.win_rate_1h = win_rate_1h
        
        # Calculate decay
        if win_rate_7d > 0:
            decay_rate = (win_rate_7d - win_rate_1h) / win_rate_7d
            sp.decay_rate = decay_rate
            sp.decay_detected = decay_rate > self.DECAY_ALERT_THRESHOLD
            
            if sp.decay_detected:
                print(f"⚠️ STRATEGY DECAY DETECTED: {strategy_name}")
                print(f"   7-day: {win_rate_7d*100:.1f}% → 1-hour: {win_rate_1h*100:.1f}%")
                print(f"   Decay rate: {decay_rate*100:.1f}% - THEY MAY HAVE LEARNED YOUR PATTERN")
            
            return sp.decay_detected, decay_rate
        
        return False, 0.0
    
    # ───────────────────────────────────────────────────────────────────────
    # 📊 HUNTING REPORT
    # ───────────────────────────────────────────────────────────────────────
    
    def generate_hunting_report(self) -> HuntingReport:
        """Generate full report on who's hunting us."""
        
        # Calculate front-run rate
        front_run_rate = 0.0
        if self.total_orders_24h > 0:
            front_run_rate = self.front_run_count_24h / self.total_orders_24h
        
        # Check for strategy decay
        strategy_decay_alert = any(
            sp.decay_detected for sp in self.strategy_performance.values()
        )
        
        # Get top predators
        top_predators = sorted(
            self.predators.values(),
            key=lambda p: (p.stalking_score, p.times_detected),
            reverse=True
        )[:5]
        
        # Determine overall threat level
        if front_run_rate > 0.5 or any(p.threat_level == "critical" for p in top_predators):
            threat_level = "red"
        elif front_run_rate > 0.3 or strategy_decay_alert:
            threat_level = "orange"
        elif front_run_rate > 0.15:
            threat_level = "yellow"
        else:
            threat_level = "green"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            front_run_rate, strategy_decay_alert, top_predators
        )
        
        report = HuntingReport(
            timestamp=time.time(),
            total_orders_analyzed=self.total_orders_24h,
            front_run_rate=front_run_rate,
            strategy_decay_alert=strategy_decay_alert,
            top_predators=top_predators,
            recommendations=recommendations,
            threat_level=threat_level
        )
        
        # Save updated history
        self._save_history()
        
        return report
    
    def _generate_recommendations(self, front_run_rate: float, 
                                   decay_alert: bool,
                                   top_predators: List[PredatorProfile]) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        
        if front_run_rate > 0.3:
            recs.append("🚨 HIGH FRONT-RUN RATE: Consider randomizing order timing")
            recs.append("   Add 50-500ms random delay before order placement")
            recs.append("   Split large orders into smaller chunks")
        
        if decay_alert:
            recs.append("⚠️ STRATEGY DECAY: Your pattern may have been learned")
            recs.append("   Rotate to different symbols/timeframes")
            recs.append("   Introduce noise into entry/exit rules")
        
        for p in top_predators:
            if p.threat_level in ["high", "critical"]:
                recs.append(f"👁️ STALKER ALERT: {p.firm_id} on {len(p.symbols_targeted)} symbols")
                recs.append(f"   Consider avoiding: {', '.join(p.symbols_targeted[:3])}")
        
        if not recs:
            recs.append("✅ No significant threats detected - stay vigilant!")
        
        return recs
    
    def print_report(self):
        """Print a nice hunting report."""
        report = self.generate_hunting_report()
        
        threat_emoji = {
            "green": "🟢",
            "yellow": "🟡", 
            "orange": "🟠",
            "red": "🔴"
        }
        
        print("\n" + "═" * 60)
        print("🦈🔍 PREDATOR DETECTION REPORT 🔍🦈")
        print("═" * 60)
        print(f"Threat Level: {threat_emoji.get(report.threat_level, '⚪')} {report.threat_level.upper()}")
        print(f"Orders Analyzed (24h): {report.total_orders_analyzed}")
        print(f"Front-Run Rate: {report.front_run_rate * 100:.1f}%")
        print(f"Strategy Decay Alert: {'⚠️ YES' if report.strategy_decay_alert else '✅ No'}")
        
        if report.top_predators:
            print("\n🎯 TOP SUSPECTED PREDATORS:")
            for i, p in enumerate(report.top_predators, 1):
                threat_color = {"low": "⚪", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                print(f"  {i}. {threat_color.get(p.threat_level, '⚪')} {p.firm_id}")
                print(f"     Stalking Score: {p.stalking_score * 100:.0f}%")
                print(f"     Times Detected: {p.times_detected}")
                print(f"     Avg Reaction: {p.avg_reaction_ms:.0f}ms")
                print(f"     Targets: {', '.join(p.symbols_targeted[:5])}")
        
        print("\n💡 RECOMMENDATIONS:")
        for rec in report.recommendations:
            print(f"  {rec}")
        
        print("═" * 60 + "\n")
        
        return report


# ═══════════════════════════════════════════════════════════════════════════════
