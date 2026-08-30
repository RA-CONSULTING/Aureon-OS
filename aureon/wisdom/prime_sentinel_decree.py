#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════════
🔱 PRIME SENTINEL DECREE 🔱
═══════════════════════════════════════════════════════════════════════════════════════════

    GARY LECKEY | 02.11.1991 | DOB-HASH: 2111991
    
    ╔═══════════════════════════════════════════════════════════════════════════════════╗
    ║  KEEPER OF THE FLAME | WITNESS OF THE FIRST BREATH | PRIME SENTINEL OF GAIA      ║
    ║  "HERE I DECREE: I HAVE TAKEN BACK CONTROL OF THE PLANET"                         ║
    ╚═══════════════════════════════════════════════════════════════════════════════════╝

This module establishes the PRIME RULES AND METRICS that govern all trading decisions.
It integrates directly with:
    - aureon_probability_nexus.py (Probability Matrix)
    - aureon_enhancements.py (Enhancement Layer)
    - aureon_unified_ecosystem.py (Trading Engine)

THE DECREE HIERARCHY:
    Level 0: GAIA FOUNDATION (Sacred Constants)
    Level 1: SENTINEL PRINCIPLES (Immutable Laws)
    Level 2: FLAME PROTOCOLS (Risk/Reward Calculus)
    Level 3: BREATH PATTERNS (Market Flow Reading)
    Level 4: CONTROL MATRIX (Position Management)

═══════════════════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import math
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════════════════
# THE SACRED CONSTANTS - LEVEL 0: GAIA FOUNDATION
# ═══════════════════════════════════════════════════════════════════════════════════════════

# DOB-HASH: Gary Leckey's birth encoding → 02.11.1991 → 2111991
DOB_HASH = 2111991
SENTINEL_PRIME = 211  # First 3 digits - Prime marker
GAIA_RESONANCE = 1991  # Birth year - Gaia frequency anchor

# Sacred Numbers (derived from DOB_HASH)
SACRED_NUMBERS = {
    'phi': (1 + math.sqrt(5)) / 2,           # Golden Ratio: 1.618033988749895
    'pi': math.pi,                            # Circle constant: 3.141592653589793
    'e': math.e,                              # Euler's number: 2.718281828459045
    'sentinel': SENTINEL_PRIME,               # 211 - Prime Sentinel marker
    'gaia': GAIA_RESONANCE,                   # 1991 - Gaia resonance
    'flame': 528,                             # Love frequency (Hz)
    'breath': 432,                            # Gaia frequency (Hz)
    'control': 777,                           # Divine alignment
}

# THE VOW
THE_DECREE = {
    'keeper': "KEEPER OF THE FLAME",
    'witness': "WITNESS OF THE FIRST BREATH",
    'sentinel': "PRIME SENTINEL OF GAIA",
    'declaration': "HERE I DECREE: I HAVE TAKEN BACK CONTROL OF THE PLANET",
    'encoded_by': "Gary Leckey",
    'dob_hash': DOB_HASH,
    'timestamp': "02.11.1991",
}


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SENTINEL PRINCIPLES - LEVEL 1: IMMUTABLE LAWS
# ═══════════════════════════════════════════════════════════════════════════════════════════

class SentinelPrinciple(Enum):
    """The 7 Immutable Laws of the Prime Sentinel"""
    
    # Principle 1: PRESERVE THE FLAME (Capital Protection)
    PRESERVE_FLAME = (1, "PRESERVE THE FLAME", 
        "Never risk more than the flame can sustain. Capital is sacred.")
    
    # Principle 2: BREATHE WITH THE MARKET (Flow Alignment)
    BREATHE_MARKET = (2, "BREATHE WITH THE MARKET",
        "Enter on exhale, exit on inhale. Trade the breath, not the noise.")
    
    # Principle 3: WITNESS BEFORE ACTION (Confirmation Required)
    WITNESS_FIRST = (3, "WITNESS BEFORE ACTION",
        "No trade without confirmation. Patience is the sentinel's weapon.")
    
    # Principle 4: CONTROL THE CONTROLLABLE (Risk Management)
    CONTROL_CONTROLLABLE = (4, "CONTROL THE CONTROLLABLE",
        "Size, entry, exit - these you control. Market direction - you don't.")
    
    # Principle 5: COMPOUND THE SACRED (Geometric Growth)
    COMPOUND_SACRED = (5, "COMPOUND THE SACRED",
        "Reinvest the blessing. 10-9-1 is the way. Geometric, not arithmetic.")
    
    # Principle 6: HONOR THE PATTERN (Respect Probabilities)
    HONOR_PATTERN = (6, "HONOR THE PATTERN",
        "Probability is not prediction. Honor the edge, accept the variance.")
    
    # Principle 7: RETURN TO GAIA (Sustainable Trading)
    RETURN_GAIA = (7, "RETURN TO GAIA",
        "Take from the system only what you need. Leave no trace of greed.")


# ═══════════════════════════════════════════════════════════════════════════════════════════
# FLAME PROTOCOLS - LEVEL 2: RISK/REWARD CALCULUS
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FlameProtocol:
    """Risk management parameters derived from the Decree"""
    
    # Maximum risk per trade (% of equity)
    max_risk_per_trade: float = 0.02  # 2% max - PRESERVE THE FLAME
    
    # Maximum daily drawdown (% of equity)
    max_daily_drawdown: float = 0.05  # 5% daily limit
    
    # Maximum total exposure (% of equity)
    max_total_exposure: float = 0.30  # 30% max across all positions
    
    # Minimum reward:risk ratio
    min_reward_risk: float = 1.5  # 1.5:1 minimum
    
    # Optimal reward:risk ratio
    optimal_reward_risk: float = 2.0  # 2:1 target
    
    # Position sizing based on Kelly Criterion (scaled)
    kelly_fraction: float = 0.25  # Quarter-Kelly for safety
    
    # Compounding rules (10-9-1 Protocol)
    profit_to_position: float = 0.10  # 10% to compound
    profit_to_reserve: float = 0.90  # 90% to reserve initially
    profit_to_withdraw: float = 0.01  # 1% to take out (rounded from 10-9-1)
    
    # Scout parameters
    min_scout_size: float = 10.0  # Minimum $10 per scout
    max_scout_size: float = 50.0  # Maximum $50 per scout
    scout_increment: float = 5.0  # Grow by $5 per successful cycle
    
    # Stop loss boundaries
    min_stop_loss: float = 0.5   # 0.5% minimum stop
    max_stop_loss: float = 3.0   # 3.0% maximum stop
    default_stop_loss: float = 1.0  # 1.0% default
    
    # Take profit boundaries
    min_take_profit: float = 0.5   # 0.5% minimum TP
    max_take_profit: float = 5.0   # 5.0% maximum TP
    default_take_profit: float = 1.5  # 1.5% default


# ═══════════════════════════════════════════════════════════════════════════════════════════
# BREATH PATTERNS - LEVEL 3: MARKET FLOW READING
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class BreathPattern:
    """Market flow patterns mapped to breathing phases"""
    
    phase: str  # 'INHALE' | 'EXHALE' | 'HOLD' | 'TRANSITION'
    intensity: float  # 0-1 strength
    direction: str  # 'BULL' | 'BEAR' | 'NEUTRAL'
    coherence: float  # 0-1 pattern clarity
    frequency_hz: float  # Dominant frequency
    resonance: str  # Which sacred frequency aligns


class BreathReader:
    """
    Reads market breath from price/volume data
    Aligns with GAIA frequencies for optimal entry
    """
    
    GAIA_FREQUENCY = 432  # Hz - Earth frequency
    LOVE_FREQUENCY = 528  # Hz - DNA repair frequency
    FLAME_FREQUENCY = 777  # Hz - Divine alignment
    
    BREATH_PHASES = {
        'INHALE': {'bias': 'accumulation', 'action': 'WAIT'},
        'HOLD_IN': {'bias': 'tension_build', 'action': 'PREPARE'},
        'EXHALE': {'bias': 'distribution', 'action': 'ENTER'},
        'HOLD_OUT': {'bias': 'completion', 'action': 'EXIT'},
    }
    
    def __init__(self):
        self.breath_history: List[BreathPattern] = []
        self.current_phase = 'INHALE'
        self.breath_count = 0
        
    def read_breath(
        self, 
        prices: List[float], 
        volumes: List[float],
        coherence: float = 0.5
    ) -> BreathPattern:
        """
        Analyze market breath from recent price/volume
        
        Returns BreathPattern indicating current market phase
        """
        if len(prices) < 12:
            return BreathPattern(
                phase='INHALE',
                intensity=0.5,
                direction='NEUTRAL',
                coherence=coherence,
                frequency_hz=self.GAIA_FREQUENCY,
                resonance='GAIA'
            )
        
        # Calculate momentum
        recent = prices[-12:]
        trend = (recent[-1] - recent[0]) / recent[0] * 100
        volatility = max(recent) - min(recent)
        vol_pct = volatility / recent[0] * 100 if recent[0] > 0 else 1
        
        # Calculate volume trend
        recent_vol = volumes[-12:] if len(volumes) >= 12 else volumes
        vol_avg = sum(recent_vol) / len(recent_vol) if recent_vol else 1
        vol_trend = recent_vol[-1] / vol_avg if vol_avg > 0 else 1
        
        # Determine phase
        if trend > 0.5 and vol_trend > 1.2:
            phase = 'EXHALE'  # Strong upward movement
            direction = 'BULL'
        elif trend < -0.5 and vol_trend > 1.2:
            phase = 'EXHALE'  # Strong downward movement
            direction = 'BEAR'
        elif abs(trend) < 0.2 and vol_trend < 0.8:
            phase = 'HOLD_OUT'  # Consolidation after move
            direction = 'NEUTRAL'
        elif vol_trend > 1.5 and abs(trend) < 0.3:
            phase = 'HOLD_IN'  # Volume building, price coiling
            direction = 'NEUTRAL'
        else:
            phase = 'INHALE'  # Accumulation phase
            direction = 'BULL' if trend > 0 else 'BEAR' if trend < 0 else 'NEUTRAL'
        
        # Calculate intensity
        intensity = min(1.0, abs(trend) / 2 + vol_trend / 3)
        
        # Determine resonance frequency
        if coherence >= 0.8:
            freq = self.FLAME_FREQUENCY  # Divine alignment
            resonance = 'FLAME'
        elif coherence >= 0.6:
            freq = self.LOVE_FREQUENCY  # Love frequency
            resonance = 'LOVE'
        else:
            freq = self.GAIA_FREQUENCY  # Base Gaia
            resonance = 'GAIA'
        
        pattern = BreathPattern(
            phase=phase,
            intensity=intensity,
            direction=direction,
            coherence=coherence,
            frequency_hz=freq,
            resonance=resonance
        )
        
        self.breath_history.append(pattern)
        if len(self.breath_history) > 100:
            self.breath_history = self.breath_history[-100:]
        
        self.current_phase = phase
        self.breath_count += 1
        
        return pattern
    
    def get_action_signal(self, pattern: BreathPattern) -> str:
        """Get recommended action based on breath pattern"""
        return self.BREATH_PHASES.get(pattern.phase, {}).get('action', 'WAIT')
    
    def is_entry_breath(self, pattern: BreathPattern) -> bool:
        """Check if current breath is optimal for entry"""
        return (
            pattern.phase == 'EXHALE' and
            pattern.intensity >= 0.6 and
            pattern.coherence >= 0.5
        )
    
    def is_exit_breath(self, pattern: BreathPattern) -> bool:
        """Check if current breath signals exit"""
        return (
            pattern.phase == 'HOLD_OUT' and
            pattern.intensity <= 0.4
        )


# ═══════════════════════════════════════════════════════════════════════════════════════════
# CONTROL MATRIX - LEVEL 4: POSITION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ControlMetrics:
    """Real-time control metrics for position management"""
    
    # Position metrics
    total_positions: int = 0
    winning_positions: int = 0
    losing_positions: int = 0
    
    # Exposure metrics
    total_exposure: float = 0.0
    max_single_exposure: float = 0.0
    exposure_utilization: float = 0.0
    
    # Risk metrics
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    
    # Performance metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Decree compliance
    flame_health: float = 1.0  # 0-1, capital preservation status
    breath_alignment: float = 0.5  # 0-1, market alignment
    control_score: float = 0.5  # 0-1, overall control level
    gaia_connection: float = 0.5  # 0-1, system harmony


class ControlMatrix:
    """
    Real-time position and risk management
    Enforces SENTINEL PRINCIPLES at execution level
    """
    
    def __init__(self, protocol: FlameProtocol = None):
        self.protocol = protocol or FlameProtocol()
        self.metrics = ControlMetrics()
        self.positions: List[Dict] = []
        self.trade_history: List[Dict] = []
        self.daily_trades: List[Dict] = []
        self.daily_start_equity: float = 0.0
        
    def calculate_position_size(
        self,
        equity: float,
        confidence: float,
        volatility: float,
        win_rate: float = 0.55
    ) -> float:
        """
        Calculate optimal position size using Decree protocols
        
        Implements:
        - Kelly Criterion (scaled by kelly_fraction)
        - Volatility adjustment
        - Confidence scaling
        - Maximum risk limits
        """
        if equity <= 0:
            return 0.0
        
        # Base Kelly calculation
        # f* = (bp - q) / b where:
        # b = odds (reward:risk ratio)
        # p = probability of winning
        # q = probability of losing (1-p)
        b = self.protocol.optimal_reward_risk
        p = win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b if b > 0 else 0
        kelly = max(0, kelly)  # No negative sizing
        
        # Scale by protocol fraction
        scaled_kelly = kelly * self.protocol.kelly_fraction
        
        # Adjust for confidence (higher confidence = closer to full Kelly)
        confidence_factor = 0.5 + (confidence * 0.5)  # 0.5 to 1.0
        
        # Adjust for volatility (higher volatility = smaller size)
        volatility_factor = 1.0 / (1.0 + volatility)  # Inverse relationship
        
        # Calculate position fraction
        position_fraction = scaled_kelly * confidence_factor * volatility_factor
        
        # Apply maximum risk limit
        position_fraction = min(position_fraction, self.protocol.max_risk_per_trade)
        
        # Calculate dollar amount
        position_size = equity * position_fraction
        
        # Apply scout boundaries
        position_size = max(self.protocol.min_scout_size, position_size)
        position_size = min(self.protocol.max_scout_size, position_size)
        
        # Check total exposure limit
        remaining_exposure = (
            equity * self.protocol.max_total_exposure - 
            self.metrics.total_exposure
        )
        position_size = min(position_size, max(0, remaining_exposure))
        
        return round(position_size, 2)
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        volatility: float,
        support_level: float = None,
        resistance_level: float = None
    ) -> float:
        """
        Calculate optimal stop loss using Decree protocols
        """
        # Base stop on volatility
        base_stop = self.protocol.default_stop_loss * (1 + volatility)
        
        # Clamp to boundaries
        stop_pct = max(self.protocol.min_stop_loss, 
                      min(self.protocol.max_stop_loss, base_stop))
        
        # Calculate stop price
        if direction == 'LONG':
            stop_price = entry_price * (1 - stop_pct / 100)
            # Use support level if provided and closer
            if support_level and support_level < entry_price:
                level_stop = support_level * 0.995  # Just below support
                if level_stop > stop_price:
                    stop_price = level_stop
        else:
            stop_price = entry_price * (1 + stop_pct / 100)
            # Use resistance level if provided and closer
            if resistance_level and resistance_level > entry_price:
                level_stop = resistance_level * 1.005  # Just above resistance
                if level_stop < stop_price:
                    stop_price = level_stop
        
        return round(stop_price, 6)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        direction: str,
        stop_price: float,
        confidence: float
    ) -> float:
        """
        Calculate optimal take profit using Decree protocols
        """
        # Calculate risk distance
        if direction == 'LONG':
            risk = entry_price - stop_price
        else:
            risk = stop_price - entry_price
        
        # Reward ratio based on confidence
        if confidence >= 0.8:
            reward_ratio = 2.5  # High confidence = larger target
        elif confidence >= 0.6:
            reward_ratio = self.protocol.optimal_reward_risk  # 2.0
        else:
            reward_ratio = self.protocol.min_reward_risk  # 1.5
        
        # Calculate reward distance
        reward = risk * reward_ratio
        
        # Calculate TP price
        if direction == 'LONG':
            tp_price = entry_price + reward
        else:
            tp_price = entry_price - reward
        
        # Clamp to boundaries
        tp_pct = abs((tp_price - entry_price) / entry_price * 100)
        if tp_pct > self.protocol.max_take_profit:
            if direction == 'LONG':
                tp_price = entry_price * (1 + self.protocol.max_take_profit / 100)
            else:
                tp_price = entry_price * (1 - self.protocol.max_take_profit / 100)
        
        return round(tp_price, 6)
    
    def validate_trade(
        self,
        side: str,
        size: float,
        confidence: float,
        breath: BreathPattern = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate trade against SENTINEL PRINCIPLES
        
        Returns: (is_valid, reason, warnings)
        """
        violations = []
        warnings = []
        
        # Principle 1: PRESERVE THE FLAME
        if self.metrics.current_drawdown > self.protocol.max_daily_drawdown:
            violations.append("FLAME VIOLATION: Daily drawdown limit exceeded")
        
        if self.metrics.total_exposure + size > self.protocol.max_total_exposure:
            violations.append("FLAME VIOLATION: Total exposure limit exceeded")
        
        # Principle 2: BREATHE WITH THE MARKET
        if breath:
            if not (breath.phase in ['EXHALE', 'HOLD_IN']):
                warnings.append(f"BREATH WARNING: Suboptimal phase ({breath.phase})")
            if breath.coherence < 0.4:
                warnings.append(f"BREATH WARNING: Low coherence ({breath.coherence:.2f})")
        
        # Principle 3: WITNESS BEFORE ACTION
        if confidence < 0.55:
            violations.append(f"WITNESS VIOLATION: Insufficient confidence ({confidence:.2f})")
        
        # Principle 4: CONTROL THE CONTROLLABLE
        if size < self.protocol.min_scout_size:
            violations.append(f"CONTROL VIOLATION: Size too small (${size:.2f})")
        
        if size > self.protocol.max_scout_size:
            warnings.append(f"CONTROL WARNING: Size near maximum (${size:.2f})")
        
        # Principle 6: HONOR THE PATTERN
        if confidence >= 0.55 and confidence < 0.60:
            warnings.append("PATTERN WARNING: Edge is marginal")
        
        is_valid = len(violations) == 0
        reason = violations[0] if violations else "Trade approved by Decree"
        
        return is_valid, reason, warnings
    
    def update_metrics(
        self,
        equity: float,
        positions: List[Dict],
        daily_pnl: float = 0.0
    ):
        """Update control metrics from current state"""
        self.positions = positions
        
        # Position metrics
        self.metrics.total_positions = len(positions)
        self.metrics.winning_positions = sum(
            1 for p in positions if p.get('unrealized_pnl', 0) > 0
        )
        self.metrics.losing_positions = sum(
            1 for p in positions if p.get('unrealized_pnl', 0) < 0
        )
        
        # Exposure metrics
        self.metrics.total_exposure = sum(
            p.get('size', 0) * p.get('entry_price', 0) 
            for p in positions
        )
        self.metrics.max_single_exposure = max(
            (p.get('size', 0) * p.get('entry_price', 0) for p in positions),
            default=0
        )
        self.metrics.exposure_utilization = (
            self.metrics.total_exposure / (equity * self.protocol.max_total_exposure)
            if equity > 0 else 0
        )
        
        # Risk metrics
        self.metrics.daily_pnl = daily_pnl
        if self.daily_start_equity > 0:
            self.metrics.current_drawdown = max(
                0, 
                (self.daily_start_equity - equity) / self.daily_start_equity
            )
        
        # Performance metrics (from history)
        if self.trade_history:
            wins = [t for t in self.trade_history if t.get('pnl', 0) > 0]
            losses = [t for t in self.trade_history if t.get('pnl', 0) < 0]
            
            self.metrics.win_rate = (
                len(wins) / len(self.trade_history) 
                if self.trade_history else 0
            )
            
            gross_profit = sum(t.get('pnl', 0) for t in wins)
            gross_loss = abs(sum(t.get('pnl', 0) for t in losses))
            
            self.metrics.profit_factor = (
                gross_profit / gross_loss 
                if gross_loss > 0 else float('inf')
            )
        
        # Decree compliance scores
        self.metrics.flame_health = 1.0 - min(1.0, self.metrics.current_drawdown * 10)
        self.metrics.control_score = 1.0 - self.metrics.exposure_utilization
        self.metrics.gaia_connection = self.metrics.flame_health * self.metrics.control_score
    
    def get_decree_status(self) -> Dict[str, Any]:
        """Get current Decree compliance status"""
        return {
            'flame_health': self.metrics.flame_health,
            'breath_alignment': self.metrics.breath_alignment,
            'control_score': self.metrics.control_score,
            'gaia_connection': self.metrics.gaia_connection,
            'total_exposure_pct': self.metrics.exposure_utilization * 100,
            'daily_drawdown_pct': self.metrics.current_drawdown * 100,
            'win_rate': self.metrics.win_rate * 100,
            'profit_factor': self.metrics.profit_factor,
            'positions': self.metrics.total_positions,
            'compliance': 'ALIGNED' if self.metrics.gaia_connection > 0.7 else 'CAUTION' if self.metrics.gaia_connection > 0.4 else 'WARNING'
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PROBABILITY MATRIX INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════════════════

class DecreeProbabilityIntegration:
    """
    Integrates PRIME SENTINEL DECREE with Aureon Probability Nexus
    
    This class applies the sacred rules and metrics as modifiers
    to the base probability calculations.
    """
    
    def __init__(self):
        self.protocol = FlameProtocol()
        self.breath_reader = BreathReader()
        self.control_matrix = ControlMatrix(self.protocol)
        
        # Sacred multipliers derived from DOB_HASH
        self.sacred_multipliers = self._calculate_sacred_multipliers()
        
    def _calculate_sacred_multipliers(self) -> Dict[str, float]:
        """Calculate multipliers from sacred numbers"""
        phi = SACRED_NUMBERS['phi']
        
        return {
            'golden_boost': phi / 10,  # ~0.162 boost when aligned
            'gaia_resonance': 1.0 + (GAIA_RESONANCE % 100) / 1000,  # 1.091
            'sentinel_edge': 1.0 + SENTINEL_PRIME / 10000,  # 1.0211
            'flame_factor': SACRED_NUMBERS['flame'] / 1000,  # 0.528
            'breath_factor': SACRED_NUMBERS['breath'] / 1000,  # 0.432
        }
    
    def apply_decree_modifiers(
        self,
        base_probability: float,
        coherence: float,
        breath: BreathPattern = None,
        decree_status: Dict = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Apply Decree modifiers to base probability
        
        Returns: (modified_probability, modifier_breakdown)
        """
        modifiers = {}
        modified_prob = base_probability
        
        # 1. GAIA RESONANCE MODIFIER
        # Higher coherence = closer to Gaia frequency = stronger signal
        if coherence >= 0.8:
            gaia_mod = self.sacred_multipliers['gaia_resonance']
            modifiers['gaia_resonance'] = gaia_mod
            if modified_prob > 0.5:
                modified_prob = 0.5 + (modified_prob - 0.5) * gaia_mod
            else:
                modified_prob = 0.5 - (0.5 - modified_prob) * gaia_mod
        
        # 2. BREATH ALIGNMENT MODIFIER
        if breath:
            if breath.phase == 'EXHALE' and breath.intensity >= 0.7:
                # Perfect breath - boost the signal
                breath_mod = 1.0 + self.sacred_multipliers['breath_factor'] * 0.5
                modifiers['breath_exhale'] = breath_mod
                modified_prob = 0.5 + (modified_prob - 0.5) * breath_mod
            
            elif breath.phase == 'HOLD_IN' and breath.intensity >= 0.6:
                # Building tension - slight boost
                modifiers['breath_tension'] = 1.05
                modified_prob = 0.5 + (modified_prob - 0.5) * 1.05
            
            elif breath.phase == 'INHALE':
                # Accumulation - dampen signal (wait mode)
                modifiers['breath_wait'] = 0.95
                modified_prob = 0.5 + (modified_prob - 0.5) * 0.95
        
        # 3. FLAME HEALTH MODIFIER
        if decree_status:
            flame_health = decree_status.get('flame_health', 1.0)
            if flame_health < 0.5:
                # Capital under threat - be conservative
                modifiers['flame_danger'] = flame_health
                modified_prob = 0.5 + (modified_prob - 0.5) * flame_health
            elif flame_health > 0.9:
                # Flame is strong - can be more aggressive
                modifiers['flame_strong'] = self.sacred_multipliers['flame_factor'] + 0.5
                modified_prob = 0.5 + (modified_prob - 0.5) * (self.sacred_multipliers['flame_factor'] + 0.5)
        
        # 4. SENTINEL EDGE (DOB-derived constant boost)
        modifiers['sentinel_edge'] = self.sacred_multipliers['sentinel_edge']
        
        # Clamp final probability
        modified_prob = max(0.01, min(0.99, modified_prob))
        
        return modified_prob, modifiers
    
    def get_full_decree_signal(
        self,
        base_probability: float,
        prices: List[float],
        volumes: List[float],
        coherence: float,
        equity: float,
        positions: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate complete trading signal with Decree integration
        
        This is the main entry point for the probability matrix integration.
        """
        # Read current breath
        breath = self.breath_reader.read_breath(prices, volumes, coherence)
        
        # Update control metrics
        self.control_matrix.update_metrics(equity, positions)
        decree_status = self.control_matrix.get_decree_status()
        
        # Apply Decree modifiers
        modified_prob, modifiers = self.apply_decree_modifiers(
            base_probability, coherence, breath, decree_status
        )
        
        # Calculate confidence
        confidence = abs(modified_prob - 0.5) * 2
        
        # Determine direction
        if modified_prob > 0.55:
            direction = 'LONG'
        elif modified_prob < 0.45:
            direction = 'SHORT'
        else:
            direction = 'NEUTRAL'
        
        # Calculate position size
        position_size = self.control_matrix.calculate_position_size(
            equity, confidence, coherence, self.control_matrix.metrics.win_rate or 0.55
        )
        
        # Validate trade
        is_valid, reason, warnings = self.control_matrix.validate_trade(
            direction, position_size, confidence, breath
        )
        
        # Get action signal from breath
        breath_action = self.breath_reader.get_action_signal(breath)
        
        return {
            'direction': direction,
            'probability': modified_prob,
            'confidence': confidence,
            'position_size': position_size if is_valid else 0,
            'is_valid': is_valid,
            'validation_reason': reason,
            'warnings': warnings,
            'modifiers_applied': modifiers,
            'breath': {
                'phase': breath.phase,
                'intensity': breath.intensity,
                'resonance': breath.resonance,
                'action': breath_action,
            },
            'decree_status': decree_status,
            'the_decree': THE_DECREE,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════════════════

# Primary classes
__all__ = [
    'PrimeSentinelDecree',
    'FlameProtocol',
    'BreathReader',
    'BreathPattern',
    'ControlMatrix',
    'ControlMetrics',
    'DecreeProbabilityIntegration',
    'SentinelPrinciple',
    'THE_DECREE',
    'SACRED_NUMBERS',
    'DOB_HASH',
]


class PrimeSentinelDecree:
    """
    🔱 MAIN INTERFACE FOR PRIME SENTINEL DECREE 🔱
    
    Combines all decree components into a single interface.
    Wire this to your probability matrix and enhancement layer.
    """
    
    def __init__(self):
        self.protocol = FlameProtocol()
        self.breath_reader = BreathReader()
        self.control_matrix = ControlMatrix(self.protocol)
        self.probability_integration = DecreeProbabilityIntegration()
        
        # Decree metadata
        self.keeper = THE_DECREE['keeper']
        self.witness = THE_DECREE['witness']
        self.sentinel = THE_DECREE['sentinel']
        self.declaration = THE_DECREE['declaration']
        self.dob_hash = DOB_HASH
        
        print("=" * 80)
        print("🔱 PRIME SENTINEL DECREE ACTIVATED 🔱")
        print("=" * 80)
        print(f"   {self.keeper}")
        print(f"   {self.witness}")
        print(f"   {self.sentinel}")
        print(f"   DOB-HASH: {self.dob_hash}")
        print()
        print(f"   \"{self.declaration}\"")
        print("=" * 80)
    
    def get_signal(
        self,
        base_probability: float,
        prices: List[float],
        volumes: List[float],
        coherence: float,
        equity: float,
        positions: List[Dict]
    ) -> Dict[str, Any]:
        """Get complete trading signal with Decree integration"""
        return self.probability_integration.get_full_decree_signal(
            base_probability, prices, volumes, coherence, equity, positions
        )
    
    def validate_trade(
        self,
        side: str,
        size: float,
        confidence: float
    ) -> Tuple[bool, str, List[str]]:
        """Validate trade against Sentinel Principles"""
        breath = self.breath_reader.breath_history[-1] if self.breath_reader.breath_history else None
        return self.control_matrix.validate_trade(side, size, confidence, breath)
    
    def get_position_size(
        self,
        equity: float,
        confidence: float,
        volatility: float
    ) -> float:
        """Get optimal position size"""
        return self.control_matrix.calculate_position_size(
            equity, confidence, volatility
        )
    
    def get_stop_loss(
        self,
        entry_price: float,
        direction: str,
        volatility: float
    ) -> float:
        """Get optimal stop loss price"""
        return self.control_matrix.calculate_stop_loss(
            entry_price, direction, volatility
        )
    
    def get_take_profit(
        self,
        entry_price: float,
        direction: str,
        stop_price: float,
        confidence: float
    ) -> float:
        """Get optimal take profit price"""
        return self.control_matrix.calculate_take_profit(
            entry_price, direction, stop_price, confidence
        )
    
    def update_state(
        self,
        equity: float,
        positions: List[Dict],
        daily_pnl: float = 0.0
    ):
        """Update decree state from current trading state"""
        self.control_matrix.update_metrics(equity, positions, daily_pnl)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current decree status"""
        return {
            'decree': THE_DECREE,
            'sacred_numbers': SACRED_NUMBERS,
            'principles': [p.value for p in SentinelPrinciple],
            'protocol': {
                'max_risk_per_trade': self.protocol.max_risk_per_trade,
                'max_daily_drawdown': self.protocol.max_daily_drawdown,
                'max_total_exposure': self.protocol.max_total_exposure,
                'min_reward_risk': self.protocol.min_reward_risk,
            },
            'control_status': self.control_matrix.get_decree_status(),
            'breath': {
                'current_phase': self.breath_reader.current_phase,
                'breath_count': self.breath_reader.breath_count,
            },
        }
    
    def display_decree(self) -> str:
        """Display the full decree"""
        lines = [
            "═" * 80,
            "🔱 PRIME SENTINEL DECREE 🔱",
            "═" * 80,
            "",
            f"  GARY LECKEY | DOB-HASH: {DOB_HASH}",
            "",
            f"  {self.keeper}",
            f"  {self.witness}", 
            f"  {self.sentinel}",
            "",
            f"  \"{self.declaration}\"",
            "",
            "─" * 80,
            "THE 7 SENTINEL PRINCIPLES:",
            "─" * 80,
        ]
        
        for principle in SentinelPrinciple:
            num, name, desc = principle.value
            lines.append(f"  {num}. {name}")
            lines.append(f"     → {desc}")
        
        lines.append("")
        lines.append("─" * 80)
        lines.append("SACRED NUMBERS:")
        lines.append("─" * 80)
        
        for name, value in SACRED_NUMBERS.items():
            lines.append(f"  {name}: {value}")
        
        lines.append("")
        lines.append("═" * 80)
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════════
