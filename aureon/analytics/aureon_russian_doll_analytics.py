"""
Aureon Russian Doll Analytics - Fractal Measurement System
===========================================================

Three-level nested analytics architecture:
- QUEEN (Macro): Global market state, cross-exchange coherence
- HIVE (System): Per-exchange, per-validator analytics  
- BEE (Micro): Individual symbol/trade-level measurements

Data flows A→Z (top-down directives) and Z→A (bottom-up insights)
Each level measures its domain and passes insights up/down the chain.

Integration Points:
- micro_profit_labyrinth.py: Bee-level trade metrics
- aureon_probability_nexus.py: Hive-level validation stats
- aureon_queen_hive_mind.py: Queen-level decisions
- aureon_thought_bus.py: Cross-module signal distribution
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix (MANDATORY)
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
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

import math
import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden ratio
LOVE_FREQUENCY = 528
SCHUMANN_BASE = 7.83

logger = logging.getLogger(__name__)

# 🌐 ThoughtBus Integration - Cross-module signal distribution
THOUGHT_BUS_AVAILABLE = False
_thought_bus = None
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    _thought_bus = get_thought_bus()
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    ThoughtBus = None
    Thought = None
    get_thought_bus = None

# ============================================================================
# BEE LEVEL (Micro) - Individual Symbol/Trade Measurements
# ============================================================================

@dataclass
class BeeMetrics:
    """Micro-level metrics for individual symbols/trades."""
    symbol: str
    exchange: str
    timestamp: float = field(default_factory=time.time)
    
    # Price metrics
    bid: float = 0.0
    ask: float = 0.0
    spread_pct: float = 0.0
    last_price: float = 0.0
    
    # Momentum metrics
    momentum_1m: float = 0.0  # 1-minute momentum %
    momentum_5m: float = 0.0  # 5-minute momentum %
    momentum_direction: str = "FLAT"  # UP, DOWN, FLAT
    
    # Probability metrics
    pip_score: float = 0.0
    expected_pnl: float = 0.0
    fee_cost: float = 0.0
    
    # Validation pass results
    pass_1_score: float = 0.0
    pass_2_score: float = 0.0
    pass_3_score: float = 0.0
    coherence: float = 0.0
    
    # Decision outcome
    action_taken: str = "NONE"  # SCAN, REJECT, EXECUTE
    rejection_reason: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def compute_coherence(self) -> float:
        """Compute coherence from 3-pass validation scores."""
        scores = [self.pass_1_score, self.pass_2_score, self.pass_3_score]
        if max(scores) == 0:
            return 0.0
        self.coherence = 1 - (max(scores) - min(scores))
        return self.coherence


@dataclass 
class BeeSwarmSummary:
    """Aggregated summary of all Bee measurements in a scan cycle."""
    timestamp: float = field(default_factory=time.time)
    total_symbols_scanned: int = 0
    symbols_with_momentum: int = 0
    symbols_rejected: int = 0
    symbols_executed: int = 0
    
    # Momentum distribution
    momentum_up_count: int = 0
    momentum_down_count: int = 0
    momentum_flat_count: int = 0
    avg_momentum: float = 0.0
    max_momentum: float = 0.0
    max_momentum_symbol: str = ""
    
    # Probability distribution
    avg_pip_score: float = 0.0
    avg_coherence: float = 0.0
    above_threshold_count: int = 0  # Symbols above φ threshold
    
    # Rejection reasons breakdown
    rejection_breakdown: Dict[str, int] = field(default_factory=dict)
    
    # Top opportunities (even if rejected)
    top_opportunities: List[Dict] = field(default_factory=list)


# ============================================================================
# HIVE LEVEL (System) - Per-Exchange/Validator Analytics
# ============================================================================

@dataclass
class HiveMetrics:
    """System-level metrics for exchanges and validators."""
    hive_id: str  # e.g., "kraken", "alpaca", "validator_1"
    hive_type: str  # "exchange" or "validator"
    timestamp: float = field(default_factory=time.time)
    
    # Exchange-specific metrics
    symbols_available: int = 0
    symbols_scanned: int = 0
    scan_latency_ms: float = 0.0
    api_calls_made: int = 0
    api_errors: int = 0
    
    # Validation metrics (for validator hives)
    validations_performed: int = 0
    pass_rate: float = 0.0  # % of symbols passing this validator
    avg_validation_score: float = 0.0
    
    # Execution metrics (for exchange hives)
    orders_attempted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    fill_rate: float = 0.0
    avg_slippage_pct: float = 0.0
    total_fees_paid: float = 0.0
    
    # Aggregated Bee insights (bottom-up)
    bee_swarm: Optional[BeeSwarmSummary] = None
    
    # Coherence with other hives
    inter_hive_coherence: float = 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if self.bee_swarm:
            d['bee_swarm'] = asdict(self.bee_swarm)
        return d


@dataclass
class HiveClusterSummary:
    """Aggregated view of all Hives in the system."""
    timestamp: float = field(default_factory=time.time)
    
    # Exchange cluster
    exchanges_active: int = 0
    total_symbols_across_exchanges: int = 0
    healthiest_exchange: str = ""
    weakest_exchange: str = ""
    
    # Validator cluster
    validators_active: int = 0
    avg_pass_rate_across_validators: float = 0.0
    validator_agreement: float = 0.0  # How much validators agree
    
    # Cross-hive metrics
    total_orders_attempted: int = 0
    total_orders_filled: int = 0
    system_fill_rate: float = 0.0
    total_fees_paid: float = 0.0
    
    # Insights to pass UP to Queen
    market_sentiment: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    opportunity_density: float = 0.0  # % of symbols showing opportunity
    recommended_action: str = "WAIT"  # AGGRESSIVE, NORMAL, WAIT


# ============================================================================
# QUEEN LEVEL (Macro) - Global Market State
# ============================================================================

@dataclass
class QueenMetrics:
    """Macro-level metrics for global market state and Queen decisions."""
    timestamp: float = field(default_factory=time.time)
    
    # Global market state
    market_regime: str = "UNKNOWN"  # VOLATILE, TRENDING, RANGING, QUIET
    global_momentum: float = 0.0
    global_coherence: float = 0.0
    
    # Queen decision metrics
    queen_confidence: float = 0.0
    queen_strategy: str = "SNIPER"  # SNIPER, AGGRESSIVE, DEFENSIVE
    risk_level: float = 0.0  # 0-1 scale
    
    # Portfolio metrics
    total_portfolio_value: float = 0.0
    cash_available: float = 0.0
    positions_held: int = 0
    unrealized_pnl: float = 0.0
    
    # Session metrics
    session_start: float = 0.0
    trades_executed: int = 0
    trades_rejected: int = 0
    win_rate: float = 0.0
    session_pnl: float = 0.0
    
    # Quantum Mirror state
    quantum_branches_ready: int = 0
    timeline_convergences: int = 0
    
    # Aggregated Hive insights (bottom-up)
    hive_cluster: Optional[HiveClusterSummary] = None
    
    # Directives to pass DOWN to Hives
    target_exchanges: List[str] = field(default_factory=list)
    min_momentum_threshold: float = 0.15  # %/min required
    min_coherence_threshold: float = 0.618  # φ threshold
    max_position_size: float = 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if self.hive_cluster:
            d['hive_cluster'] = asdict(self.hive_cluster)
        return d


# ============================================================================
# RUSSIAN DOLL ANALYTICS ENGINE
# ============================================================================

class RussianDollAnalytics:
    """
    Fractal analytics engine managing three nested measurement levels.
    
    Data Flow:
    - A→Z (Top-Down): Queen sets thresholds → Hives distribute → Bees filter
    - Z→A (Bottom-Up): Bees report metrics → Hives aggregate → Queen decides
    """
    
    def __init__(self, state_file: str = "russian_doll_state.json"):
        self.state_file = Path(state_file)
        
        # Current state at each level
        self.queen_metrics = QueenMetrics()
        self.hive_metrics: Dict[str, HiveMetrics] = {}
        self.bee_metrics: Dict[str, BeeMetrics] = {}  # keyed by "exchange:symbol"
        
        # Historical aggregations
        self.scan_history: List[Dict] = []
        self.max_history = 1000
        
        # Bottom-up insight accumulators
        self._bee_buffer: List[BeeMetrics] = []
        self._hive_buffer: List[HiveMetrics] = []
        
        # Load previous state if exists
        self._load_state()
        
        logger.info("🪆 Russian Doll Analytics initialized")
    
    # ========================================================================
    # BEE LEVEL (Micro) Operations
    # ========================================================================
    
    def record_bee(self, bee: BeeMetrics) -> None:
        """Record a single Bee-level measurement."""
        key = f"{bee.exchange}:{bee.symbol}"
        self.bee_metrics[key] = bee
        self._bee_buffer.append(bee)
        
        # Keep buffer bounded
        if len(self._bee_buffer) > 10000:
            self._bee_buffer = self._bee_buffer[-5000:]
    
    def record_symbol_scan(
        self,
        symbol: str,
        exchange: str,
        bid: float,
        ask: float,
        momentum_1m: float,
        pip_score: float,
        expected_pnl: float,
        pass_scores: Tuple[float, float, float],
        action: str = "SCAN",
        rejection_reason: str = ""
    ) -> BeeMetrics:
        """Convenience method to record a symbol scan as a Bee metric."""
        spread_pct = ((ask - bid) / bid * 100) if bid > 0 else 0
        
        bee = BeeMetrics(
            symbol=symbol,
            exchange=exchange,
            bid=bid,
            ask=ask,
            spread_pct=spread_pct,
            last_price=(bid + ask) / 2,
            momentum_1m=momentum_1m,
            momentum_direction="UP" if momentum_1m > 0.01 else ("DOWN" if momentum_1m < -0.01 else "FLAT"),
            pip_score=pip_score,
            expected_pnl=expected_pnl,
            pass_1_score=pass_scores[0],
            pass_2_score=pass_scores[1],
            pass_3_score=pass_scores[2],
            action_taken=action,
            rejection_reason=rejection_reason
        )
        bee.compute_coherence()
        self.record_bee(bee)
        return bee
    
    def aggregate_bee_swarm(self) -> BeeSwarmSummary:
        """Aggregate recent Bee metrics into a swarm summary (Z→A flow)."""
        if not self._bee_buffer:
            return BeeSwarmSummary()
        
        # Use recent buffer (last scan cycle)
        recent_bees = self._bee_buffer[-1000:]  # Last 1000 measurements
        
        summary = BeeSwarmSummary(
            total_symbols_scanned=len(recent_bees),
            symbols_with_momentum=sum(1 for b in recent_bees if abs(b.momentum_1m) > 0.01),
            symbols_rejected=sum(1 for b in recent_bees if b.action_taken == "REJECT"),
            symbols_executed=sum(1 for b in recent_bees if b.action_taken == "EXECUTE"),
        )
        
        # Momentum distribution
        summary.momentum_up_count = sum(1 for b in recent_bees if b.momentum_direction == "UP")
        summary.momentum_down_count = sum(1 for b in recent_bees if b.momentum_direction == "DOWN")
        summary.momentum_flat_count = sum(1 for b in recent_bees if b.momentum_direction == "FLAT")
        
        momentums = [b.momentum_1m for b in recent_bees]
        if momentums:
            summary.avg_momentum = sum(momentums) / len(momentums)
            max_idx = momentums.index(max(momentums, key=abs))
            summary.max_momentum = momentums[max_idx]
            summary.max_momentum_symbol = recent_bees[max_idx].symbol
        
        # Probability distribution
        pip_scores = [b.pip_score for b in recent_bees if b.pip_score > 0]
        coherences = [b.coherence for b in recent_bees if b.coherence > 0]
        
        if pip_scores:
            summary.avg_pip_score = sum(pip_scores) / len(pip_scores)
        if coherences:
            summary.avg_coherence = sum(coherences) / len(coherences)
            summary.above_threshold_count = sum(1 for c in coherences if c >= (1 / PHI))
        
        # Rejection breakdown
        rejection_counts: Dict[str, int] = defaultdict(int)
        for b in recent_bees:
            if b.rejection_reason:
                rejection_counts[b.rejection_reason] += 1
        summary.rejection_breakdown = dict(rejection_counts)
        
        # Top opportunities
        sorted_bees = sorted(recent_bees, key=lambda b: b.pip_score, reverse=True)[:5]
        summary.top_opportunities = [
            {"symbol": b.symbol, "exchange": b.exchange, "pip_score": b.pip_score, 
             "momentum": b.momentum_1m, "coherence": b.coherence}
            for b in sorted_bees
        ]
        
        return summary
    
    # ========================================================================
    # HIVE LEVEL (System) Operations
    # ========================================================================
    
    def record_hive(self, hive: HiveMetrics) -> None:
        """Record a Hive-level measurement."""
        self.hive_metrics[hive.hive_id] = hive
        self._hive_buffer.append(hive)
        
        if len(self._hive_buffer) > 1000:
            self._hive_buffer = self._hive_buffer[-500:]
    
    def record_exchange_scan(
        self,
        exchange: str,
        symbols_available: int,
        symbols_scanned: int,
        scan_latency_ms: float,
        orders_attempted: int = 0,
        orders_filled: int = 0,
        fees_paid: float = 0.0
    ) -> HiveMetrics:
        """Record an exchange scan cycle as a Hive metric."""
        # Get Bee swarm for this exchange
        exchange_bees = [b for b in self._bee_buffer[-1000:] if b.exchange == exchange]
        bee_swarm = None
        if exchange_bees:
            bee_swarm = BeeSwarmSummary(
                total_symbols_scanned=len(exchange_bees),
                symbols_with_momentum=sum(1 for b in exchange_bees if abs(b.momentum_1m) > 0.01),
                symbols_rejected=sum(1 for b in exchange_bees if b.action_taken == "REJECT"),
                symbols_executed=sum(1 for b in exchange_bees if b.action_taken == "EXECUTE"),
            )
        
        hive = HiveMetrics(
            hive_id=exchange,
            hive_type="exchange",
            symbols_available=symbols_available,
            symbols_scanned=symbols_scanned,
            scan_latency_ms=scan_latency_ms,
            orders_attempted=orders_attempted,
            orders_filled=orders_filled,
            fill_rate=(orders_filled / orders_attempted * 100) if orders_attempted > 0 else 0,
            total_fees_paid=fees_paid,
            bee_swarm=bee_swarm
        )
        self.record_hive(hive)
        return hive
    
    def record_validator_pass(
        self,
        validator_id: str,
        validations_performed: int,
        passes: int,
        avg_score: float
    ) -> HiveMetrics:
        """Record a validation pass cycle as a Hive metric."""
        hive = HiveMetrics(
            hive_id=validator_id,
            hive_type="validator",
            validations_performed=validations_performed,
            pass_rate=(passes / validations_performed * 100) if validations_performed > 0 else 0,
            avg_validation_score=avg_score
        )
        self.record_hive(hive)
        return hive
    
    def aggregate_hive_cluster(self) -> HiveClusterSummary:
        """Aggregate Hive metrics into cluster summary (Z→A flow)."""
        summary = HiveClusterSummary()
        
        exchange_hives = [h for h in self.hive_metrics.values() if h.hive_type == "exchange"]
        validator_hives = [h for h in self.hive_metrics.values() if h.hive_type == "validator"]
        
        # Exchange cluster
        summary.exchanges_active = len(exchange_hives)
        if exchange_hives:
            summary.total_symbols_across_exchanges = sum(h.symbols_scanned for h in exchange_hives)
            
            # Find healthiest (highest fill rate) and weakest
            sorted_by_health = sorted(exchange_hives, key=lambda h: h.fill_rate, reverse=True)
            summary.healthiest_exchange = sorted_by_health[0].hive_id
            summary.weakest_exchange = sorted_by_health[-1].hive_id
            
            summary.total_orders_attempted = sum(h.orders_attempted for h in exchange_hives)
            summary.total_orders_filled = sum(h.orders_filled for h in exchange_hives)
            summary.total_fees_paid = sum(h.total_fees_paid for h in exchange_hives)
            
            if summary.total_orders_attempted > 0:
                summary.system_fill_rate = summary.total_orders_filled / summary.total_orders_attempted * 100
        
        # Validator cluster
        summary.validators_active = len(validator_hives)
        if validator_hives:
            pass_rates = [h.pass_rate for h in validator_hives]
            summary.avg_pass_rate_across_validators = sum(pass_rates) / len(pass_rates)
            
            # Agreement = inverse of variance in pass rates
            if len(pass_rates) > 1:
                mean_rate = sum(pass_rates) / len(pass_rates)
                variance = sum((r - mean_rate) ** 2 for r in pass_rates) / len(pass_rates)
                summary.validator_agreement = max(0, 1 - (variance / 100))  # Normalize
        
        # Derive market sentiment from Bee swarms
        all_bees = self._bee_buffer[-500:]
        if all_bees:
            up_count = sum(1 for b in all_bees if b.momentum_direction == "UP")
            down_count = sum(1 for b in all_bees if b.momentum_direction == "DOWN")
            total = len(all_bees)
            
            if up_count > total * 0.6:
                summary.market_sentiment = "BULLISH"
            elif down_count > total * 0.6:
                summary.market_sentiment = "BEARISH"
            else:
                summary.market_sentiment = "NEUTRAL"
            
            # Opportunity density
            opportunities = sum(1 for b in all_bees if b.pip_score > 0.07 and b.coherence > 0.5)
            summary.opportunity_density = opportunities / total * 100 if total > 0 else 0
            
            # Recommended action
            if summary.opportunity_density > 10 and summary.validator_agreement > 0.7:
                summary.recommended_action = "AGGRESSIVE"
            elif summary.opportunity_density > 5:
                summary.recommended_action = "NORMAL"
            else:
                summary.recommended_action = "WAIT"
        
        return summary
    
    # ========================================================================
    # QUEEN LEVEL (Macro) Operations
    # ========================================================================
    
    def update_queen_state(
        self,
        portfolio_value: float,
        cash_available: float,
        positions_held: int,
        queen_confidence: float,
        queen_strategy: str,
        market_regime: str = "UNKNOWN"
    ) -> QueenMetrics:
        """Update Queen-level metrics with current state."""
        # Aggregate from Hives (Z→A)
        hive_cluster = self.aggregate_hive_cluster()
        bee_swarm = self.aggregate_bee_swarm()
        
        # Compute global coherence from Bee swarm
        global_coherence = bee_swarm.avg_coherence if bee_swarm.avg_coherence > 0 else 0.5
        
        # Compute global momentum
        global_momentum = bee_swarm.avg_momentum
        
        self.queen_metrics = QueenMetrics(
            market_regime=market_regime,
            global_momentum=global_momentum,
            global_coherence=global_coherence,
            queen_confidence=queen_confidence,
            queen_strategy=queen_strategy,
            risk_level=1 - queen_confidence,  # Inverse confidence = risk
            total_portfolio_value=portfolio_value,
            cash_available=cash_available,
            positions_held=positions_held,
            hive_cluster=hive_cluster,
            trades_executed=bee_swarm.symbols_executed,
            trades_rejected=bee_swarm.symbols_rejected,
        )
        
        # Set directives based on market state (A→Z)
        self._set_queen_directives()
        
        return self.queen_metrics
    
    def _set_queen_directives(self) -> None:
        """Queen sets directives to flow down to Hives/Bees (A→Z flow)."""
        q = self.queen_metrics
        
        # Adjust thresholds based on market regime
        if q.market_regime == "VOLATILE":
            q.min_momentum_threshold = 0.20  # Higher bar in volatile markets
            q.min_coherence_threshold = 0.70
        elif q.market_regime == "QUIET":
            q.min_momentum_threshold = 0.10  # Lower bar in quiet markets
            q.min_coherence_threshold = 0.55
        else:
            q.min_momentum_threshold = 0.15  # Default
            q.min_coherence_threshold = 1 / PHI  # φ threshold
        
        # Position sizing based on confidence
        if q.queen_confidence > 0.8:
            q.max_position_size = q.cash_available * 0.5  # 50% max
        elif q.queen_confidence > 0.6:
            q.max_position_size = q.cash_available * 0.3  # 30% max
        else:
            q.max_position_size = q.cash_available * 0.1  # 10% max (conservative)
        
        # Target exchanges based on hive health
        if q.hive_cluster and q.hive_cluster.healthiest_exchange:
            q.target_exchanges = [q.hive_cluster.healthiest_exchange]
    
    def get_queen_directives(self) -> Dict[str, Any]:
        """Get current Queen directives for downstream systems (A→Z)."""
        q = self.queen_metrics
        return {
            "min_momentum_threshold": q.min_momentum_threshold,
            "min_coherence_threshold": q.min_coherence_threshold,
            "max_position_size": q.max_position_size,
            "target_exchanges": q.target_exchanges,
            "queen_strategy": q.queen_strategy,
            "queen_confidence": q.queen_confidence,
            "market_regime": q.market_regime
        }
    
    # ========================================================================
    # Full Analytics Snapshot
    # ========================================================================
    
    def get_full_snapshot(self) -> Dict[str, Any]:
        """Get complete Russian Doll snapshot at all levels."""
        bee_swarm = self.aggregate_bee_swarm()
        hive_cluster = self.aggregate_hive_cluster()
        
        return {
            "timestamp": time.time(),
            "timestamp_human": datetime.now(timezone.utc).isoformat(),
            
            # QUEEN LEVEL (Macro)
            "queen": {
                "market_regime": self.queen_metrics.market_regime,
                "global_momentum": round(self.queen_metrics.global_momentum, 4),
                "global_coherence": round(self.queen_metrics.global_coherence, 4),
                "queen_confidence": round(self.queen_metrics.queen_confidence, 2),
                "queen_strategy": self.queen_metrics.queen_strategy,
                "portfolio_value": round(self.queen_metrics.total_portfolio_value, 2),
                "cash_available": round(self.queen_metrics.cash_available, 2),
                "positions_held": self.queen_metrics.positions_held,
                "directives": self.get_queen_directives()
            },
            
            # HIVE LEVEL (System)
            "hive_cluster": {
                "exchanges_active": hive_cluster.exchanges_active,
                "total_symbols": hive_cluster.total_symbols_across_exchanges,
                "validators_active": hive_cluster.validators_active,
                "validator_agreement": round(hive_cluster.validator_agreement, 2),
                "market_sentiment": hive_cluster.market_sentiment,
                "opportunity_density": round(hive_cluster.opportunity_density, 2),
                "recommended_action": hive_cluster.recommended_action,
                "system_fill_rate": round(hive_cluster.system_fill_rate, 2),
                "total_fees_paid": round(hive_cluster.total_fees_paid, 4)
            },
            
            # BEE LEVEL (Micro)
            "bee_swarm": {
                "total_scanned": bee_swarm.total_symbols_scanned,
                "with_momentum": bee_swarm.symbols_with_momentum,
                "rejected": bee_swarm.symbols_rejected,
                "executed": bee_swarm.symbols_executed,
                "momentum_distribution": {
                    "up": bee_swarm.momentum_up_count,
                    "down": bee_swarm.momentum_down_count,
                    "flat": bee_swarm.momentum_flat_count
                },
                "avg_momentum": round(bee_swarm.avg_momentum, 4),
                "max_momentum": round(bee_swarm.max_momentum, 4),
                "max_momentum_symbol": bee_swarm.max_momentum_symbol,
                "avg_pip_score": round(bee_swarm.avg_pip_score, 4),
                "avg_coherence": round(bee_swarm.avg_coherence, 4),
                "above_phi_threshold": bee_swarm.above_threshold_count,
                "rejection_breakdown": bee_swarm.rejection_breakdown,
                "top_opportunities": bee_swarm.top_opportunities
            }
        }
    
    def print_dashboard(self) -> str:
        """Print formatted analytics dashboard."""
        snap = self.get_full_snapshot()
        q = snap["queen"]
        h = snap["hive_cluster"]
        b = snap["bee_swarm"]
        
        lines = [
            "",
            "=" * 70,
            "🪆 RUSSIAN DOLL ANALYTICS DASHBOARD",
            "=" * 70,
            "",
            "👑 QUEEN LEVEL (Macro)",
            "─" * 35,
            f"   Market Regime:    {q['market_regime']}",
            f"   Global Momentum:  {q['global_momentum']:.4f}%/min",
            f"   Global Coherence: {q['global_coherence']:.4f}",
            f"   Queen Confidence: {q['queen_confidence']:.0%}",
            f"   Queen Strategy:   {q['queen_strategy']}",
            f"   Portfolio Value:  ${q['portfolio_value']:.2f}",
            f"   Cash Available:   ${q['cash_available']:.2f}",
            f"   Positions Held:   {q['positions_held']}",
            "",
            "🐝 HIVE LEVEL (System)",
            "─" * 35,
            f"   Exchanges Active:    {h['exchanges_active']}",
            f"   Total Symbols:       {h['total_symbols']}",
            f"   Validators Active:   {h['validators_active']}",
            f"   Validator Agreement: {h['validator_agreement']:.0%}",
            f"   Market Sentiment:    {h['market_sentiment']}",
            f"   Opportunity Density: {h['opportunity_density']:.1f}%",
            f"   Recommended Action:  {h['recommended_action']}",
            f"   System Fill Rate:    {h['system_fill_rate']:.1f}%",
            "",
            "🐝 BEE LEVEL (Micro)",
            "─" * 35,
            f"   Symbols Scanned:  {b['total_scanned']}",
            f"   With Momentum:    {b['with_momentum']}",
            f"   Rejected:         {b['rejected']}",
            f"   Executed:         {b['executed']}",
            "",
            f"   Momentum Distribution:",
            f"      ▲ UP:   {b['momentum_distribution']['up']}",
            f"      ▼ DOWN: {b['momentum_distribution']['down']}",
            f"      ─ FLAT: {b['momentum_distribution']['flat']}",
            "",
            f"   Avg Momentum:     {b['avg_momentum']:.4f}%/min",
            f"   Max Momentum:     {b['max_momentum']:.4f}% ({b['max_momentum_symbol']})",
            f"   Avg PIP Score:    {b['avg_pip_score']:.4f}",
            f"   Avg Coherence:    {b['avg_coherence']:.4f}",
            f"   Above φ Threshold: {b['above_phi_threshold']}",
            "",
        ]
        
        if b['rejection_breakdown']:
            lines.append("   Rejection Breakdown:")
            for reason, count in sorted(b['rejection_breakdown'].items(), key=lambda x: -x[1]):
                lines.append(f"      {reason}: {count}")
            lines.append("")
        
        if b['top_opportunities']:
            lines.append("   Top Opportunities:")
            for opp in b['top_opportunities'][:3]:
                lines.append(f"      {opp['symbol']} ({opp['exchange']}): PIP={opp['pip_score']:.4f}, Mom={opp['momentum']:.4f}%")
            lines.append("")
        
        lines.extend([
            "=" * 70,
            f"   Timestamp: {snap['timestamp_human']}",
            "=" * 70,
            ""
        ])
        
        dashboard = "\n".join(lines)
        print(dashboard)
        return dashboard
    
    # ========================================================================
    # Persistence
    # ========================================================================
    
    def _load_state(self) -> None:
        """Load previous state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Restore scan history
                    self.scan_history = data.get('scan_history', [])[-self.max_history:]
                    logger.info(f"Loaded {len(self.scan_history)} historical scan records")
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
    
    def save_state(self) -> None:
        """Save current state to disk."""
        try:
            snapshot = self.get_full_snapshot()
            self.scan_history.append(snapshot)
            
            # Trim history
            if len(self.scan_history) > self.max_history:
                self.scan_history = self.scan_history[-self.max_history:]
            
            data = {
                'scan_history': self.scan_history,
                'last_snapshot': snapshot
            }
            
            # Atomic write
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.rename(self.state_file)
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    # ========================================================================
    # ThoughtBus Integration - Cross-Module Broadcasting
    # ========================================================================
    
    def broadcast_snapshot(self, topic: str = "analytics.russian_doll") -> bool:
        """
        Broadcast current analytics snapshot to ThoughtBus.
        
        This enables other modules to subscribe and receive:
        - Queen-level directives (A→Z)
        - Aggregated Bee insights (Z→A)
        - Market regime changes
        - Opportunity density alerts
        
        Args:
            topic: ThoughtBus topic to publish on
            
        Returns:
            True if broadcast successful
        """
        if not THOUGHT_BUS_AVAILABLE or _thought_bus is None:
            return False
        
        try:
            snapshot = self.get_full_snapshot()
            
            # Create compact broadcast payload
            payload = {
                "level": "queen",  # Originating level
                "market_regime": snapshot['queen']['market_regime'],
                "queen_confidence": snapshot['queen']['queen_confidence'],
                "queen_strategy": snapshot['queen']['queen_strategy'],
                "global_momentum": snapshot['queen']['global_momentum'],
                "global_coherence": snapshot['queen']['global_coherence'],
                "opportunity_density": snapshot['hive_cluster']['opportunity_density'],
                "market_sentiment": snapshot['hive_cluster']['market_sentiment'],
                "recommended_action": snapshot['hive_cluster']['recommended_action'],
                "symbols_scanned": snapshot['bee_swarm']['total_scanned'],
                "directives": snapshot['queen']['directives'],
                "timestamp": snapshot['timestamp'],
            }
            
            # Publish as Thought
            thought = Thought(
                source="russian_doll_analytics",
                topic=topic,
                payload=payload
            )
            _thought_bus.publish(thought)
            
            logger.debug(f"🪆📡 Broadcast analytics snapshot on '{topic}'")
            return True
            
        except Exception as e:
            logger.warning(f"🪆⚠️ Failed to broadcast: {e}")
            return False
    
    def subscribe_to_signals(self, handler: callable) -> None:
        """
        Subscribe to incoming market signals for bottom-up aggregation.
        
        Handler will receive Thoughts with topics like:
        - market.snapshot
        - execution.result
        - risk.alert
        
        Args:
            handler: Callable(Thought) to process incoming signals
        """
        if not THOUGHT_BUS_AVAILABLE or _thought_bus is None:
            logger.warning("ThoughtBus not available for subscription")
            return
        
        # Subscribe to relevant topics
        topics = ["market.*", "execution.*", "risk.*", "miner.*"]
        for topic in topics:
            _thought_bus.subscribe(topic, handler)
        
        logger.info(f"🪆👂 Subscribed to {len(topics)} ThoughtBus topics")
    
    def _handle_incoming_thought(self, thought) -> None:
        """Internal handler for incoming ThoughtBus signals."""
        try:
            topic = thought.topic
            payload = thought.payload
            
            # Extract market data for Bee-level recording
            if topic.startswith("market."):
                symbol = payload.get("symbol")
                exchange = payload.get("exchange")
                if symbol and exchange:
                    self.record_symbol_scan(
                        symbol=symbol,
                        exchange=exchange,
                        bid=payload.get("bid", 0),
                        ask=payload.get("ask", 0),
                        momentum_1m=payload.get("momentum", 0),
                        pip_score=payload.get("pip_score", 0),
                        expected_pnl=payload.get("expected_pnl", 0),
                        pass_scores=(0, 0, 0),
                        action="THOUGHT_SIGNAL"
                    )
            
            # Extract execution data for metrics
            elif topic.startswith("execution."):
                exchange = payload.get("exchange", "unknown")
                if exchange in self.hive_metrics:
                    hive = self.hive_metrics[exchange]
                    if payload.get("status") == "filled":
                        hive.orders_filled += 1
                    hive.orders_attempted += 1
                    
        except Exception as e:
            logger.debug(f"🪆⚠️ Error handling thought: {e}")


# ============================================================================
# GLOBAL INSTANCE & CONVENIENCE FUNCTIONS
# ============================================================================

_analytics: Optional[RussianDollAnalytics] = None

def get_analytics() -> RussianDollAnalytics:
    """Get or create the global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = RussianDollAnalytics()
    return _analytics


def record_scan(
    symbol: str,
    exchange: str,
    bid: float,
    ask: float,
    momentum: float,
    pip_score: float,
    expected_pnl: float,
    pass_scores: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    action: str = "SCAN",
    rejection_reason: str = ""
) -> BeeMetrics:
    """Convenience function to record a symbol scan."""
    return get_analytics().record_symbol_scan(
        symbol, exchange, bid, ask, momentum, pip_score, expected_pnl,
        pass_scores, action, rejection_reason
    )


def record_exchange(
    exchange: str,
    symbols_available: int,
    symbols_scanned: int,
    latency_ms: float,
    orders_attempted: int = 0,
    orders_filled: int = 0,
    fees: float = 0.0
) -> HiveMetrics:
    """Convenience function to record an exchange scan."""
    return get_analytics().record_exchange_scan(
        exchange, symbols_available, symbols_scanned, latency_ms,
        orders_attempted, orders_filled, fees
    )


def update_queen(
    portfolio_value: float,
    cash: float,
    positions: int,
    confidence: float,
    strategy: str,
    regime: str = "UNKNOWN"
) -> QueenMetrics:
    """Convenience function to update Queen state."""
    return get_analytics().update_queen_state(
        portfolio_value, cash, positions, confidence, strategy, regime
    )


def get_snapshot() -> Dict[str, Any]:
    """Get full analytics snapshot."""
    return get_analytics().get_full_snapshot()


def print_dashboard() -> str:
    """Print and return analytics dashboard."""
    return get_analytics().print_dashboard()


def get_directives() -> Dict[str, Any]:
    """Get Queen's current directives for downstream systems."""
    return get_analytics().get_queen_directives()


def broadcast_analytics(topic: str = "analytics.russian_doll") -> bool:
    """Broadcast analytics snapshot to ThoughtBus."""
    return get_analytics().broadcast_snapshot(topic)


def print_and_broadcast() -> str:
    """Print dashboard and broadcast to ThoughtBus (combined operation)."""
    dashboard = get_analytics().print_dashboard()
    get_analytics().broadcast_snapshot()
    return dashboard


# ============================================================================
# MAIN - Demonstration
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("🪆 Russian Doll Analytics - Demonstration")
    print("=" * 50)
    
    # Initialize analytics
    analytics = get_analytics()
    
    # Simulate some Bee-level scans
    symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "LINK/USD", "UNI/USD"]
    for i, symbol in enumerate(symbols):
        momentum = 0.02 * (i - 2)  # Range from -0.04 to +0.04
        pip_score = 0.05 + 0.03 * i
        expected_pnl = pip_score - 0.15 if momentum > 0 else -0.10
        
        record_scan(
            symbol=symbol,
            exchange="alpaca",
            bid=100.0 + i * 10,
            ask=100.5 + i * 10,
            momentum=momentum,
            pip_score=pip_score,
            expected_pnl=expected_pnl,
            pass_scores=(0.6 + 0.05*i, 0.55 + 0.05*i, 0.58 + 0.05*i),
            action="REJECT" if expected_pnl < 0 else "SCAN",
            rejection_reason="negative_pnl" if expected_pnl < 0 else ""
        )
    
    # Record exchange-level metrics
    record_exchange(
        exchange="alpaca",
        symbols_available=50,
        symbols_scanned=5,
        latency_ms=150.0,
        orders_attempted=0,
        orders_filled=0,
        fees=0.0
    )
    
    # Update Queen state
    update_queen(
        portfolio_value=12.63,
        cash=0.52,
        positions=5,
        confidence=0.65,
        strategy="SNIPER",
        regime="QUIET"
    )
    
    # Print full dashboard
    print_dashboard()
    
    # Save state
    analytics.save_state()
    print("\n✅ State saved to russian_doll_state.json")
