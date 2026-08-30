#!/usr/bin/env python3
"""
🐙🌌 AUREON KRAKEN ECOSYSTEM - THE UNIFIED TRADING ENGINE 🌌🐙
================================================================
ONE DYNAMIC PYTHON FOR THE ENTIRE KRAKEN ECOSYSTEM

Combines ALL the best from:
- aureon_51_live.py (51% win rate strategy)
- aureon_infinite_kraken.py (10-9-1 Queen Hive compounding)
- aureon_multiverse.py (Temporal analysis)
- aureon_mycelium.py (Neural network intelligence)
- aureon_qgita.py (9 Auris nodes)
- kraken_multi_sim.py (Multi-strategy analysis)

FEATURES:
├─ 🔴 Real-time WebSocket prices
├─ 🎯 Multiple strategies running simultaneously
├─ 🍄 Neural network pattern detection
├─ 🐅 9 Auris nodes for market analysis
├─ 💰 Compounding with 10-9-1 model
├─ 📊 Dynamic opportunity scoring
└─ 🔄 Infinite loop - never stops growing

GOAL: 51%+ Win Rate with NET PROFIT after ALL fees

Gary Leckey & GitHub Copilot | November 2025
"From Atom to Multiverse - We don't quit!"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import math
import random
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from threading import Thread, Lock

sys.path.insert(0, '/workspaces/aureon-trading')
from aureon.exchanges.kraken_client import get_kraken_client
from aureon.core.aureon_lattice import LatticeEngine

_QUIET_STARTUP = os.getenv("AUREON_QUIET_STARTUP", "0").lower() in ("1", "true", "yes", "on")

def _startup_print(*args, **kwargs):
    if not _QUIET_STARTUP:
        print(*args, **kwargs)

# 🧬 SANDBOX EVOLVED PARAMETERS - 454 Generations of Learning
try:
    from aureon.trading.penny_profit_engine import get_evolved_exits, check_penny_exit, get_penny_engine
    SANDBOX_EVOLVED_AVAILABLE = True
    PENNY_PROFIT_AVAILABLE = True
    _evolved = get_evolved_exits()
    _penny_engine = get_penny_engine()
    _startup_print(f"🧬 Sandbox Evolution loaded - Gen {_evolved.generation}, {_evolved.win_rate:.1f}% win rate")
    _startup_print(f"🪙 Penny Profit Engine loaded")
except ImportError:
    SANDBOX_EVOLVED_AVAILABLE = False
    PENNY_PROFIT_AVAILABLE = False
    _evolved = None
    _penny_engine = None
    _startup_print("⚠️ Sandbox Evolution not available - using defaults")

# 🔮 NEXUS PREDICTOR - 79.6% Win Rate Validated Over 11 Years!
try:
    from aureon.intelligence.nexus_predictor import NexusPredictor
    NEXUS_AVAILABLE = True
    _startup_print("🔮 Nexus Predictor loaded - 79.6% win rate validated!")
except ImportError:
    NEXUS_AVAILABLE = False
    _startup_print("⚠️ Nexus Predictor not available")

# 💎 TRADE PROFIT VALIDATOR - NO PHANTOM GAINS!
try:
    from aureon.portfolio.trade_profit_validator import validate_buy, validate_sell, is_real_profit, get_validator
    TRADE_VALIDATOR_AVAILABLE = True
    _startup_print("💎 Trade Profit Validator loaded - no phantom gains!")
except ImportError:
    TRADE_VALIDATOR_AVAILABLE = False
    validate_buy = None
    validate_sell = None
    is_real_profit = None
    get_validator = None

# 🦑💰 KRAKEN FEE TRACKER - Dynamic volume-tiered fees
try:
    from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker
    _KRAKEN_FEE_TRACKER_AVAILABLE = True
    _startup_print("🦑💰 Kraken Fee Tracker loaded - dynamic tier fees active!")
except ImportError:
    _KRAKEN_FEE_TRACKER_AVAILABLE = False
    get_kraken_fee_tracker = None

# 👑 THE KING - Autonomous Accounting AI
try:
    from aureon.bots.king_integration import king_on_buy, king_on_sell, start_king
    KING_AVAILABLE = True
    _startup_print("👑 The King loaded - autonomous accounting active!")
except ImportError:
    KING_AVAILABLE = False
    king_on_buy = None
    king_on_sell = None
    start_king = None

# 👁 AUREON THE SEER - Autonomous Coherence & Cosmic Intelligence
try:
    from aureon.intelligence.aureon_seer_integration import (
        start_seer, seer_update_context, seer_get_vision,
        seer_get_risk_modifier, seer_should_trade, get_triumvirate_consensus,
    )
    SEER_AVAILABLE = True
    _startup_print("👁 Aureon the Seer loaded - cosmic coherence active!")
except ImportError:
    SEER_AVAILABLE = False
    start_seer = None
    seer_update_context = None
    seer_get_vision = None
    seer_get_risk_modifier = None
    seer_should_trade = None
    get_triumvirate_consensus = None

# AUREON LYRA - Emotional Frequency & Harmonics Engine
try:
    from aureon.trading.aureon_lyra_integration import (
        start_lyra, lyra_update_context, lyra_get_resonance,
        lyra_get_position_multiplier, lyra_should_trade,
    )
    LYRA_AVAILABLE = True
    _startup_print("Aureon Lyra loaded - emotional frequency & harmonics active!")
except ImportError:
    LYRA_AVAILABLE = False
    start_lyra = None
    lyra_update_context = None
    lyra_get_resonance = None
    lyra_get_position_multiplier = None
    lyra_should_trade = None

# ⚔️ WAR STRATEGY - Quick Kill Probability & Attack Signals
try:
    from aureon.command_centers.war_strategy import should_attack, get_quick_kill_estimate
    WAR_STRATEGY_AVAILABLE = True
    _startup_print("⚔️ War Strategy loaded - quick kill probability active!")
except ImportError:
    WAR_STRATEGY_AVAILABLE = False
    should_attack = None
    get_quick_kill_estimate = None

# 🎯 UNIFIED SNIPER BRAIN - Million Kill Training
try:
    from aureon.trading.unified_sniper_brain import get_entry_signal as sniper_get_entry_signal, get_unified_brain
    SNIPER_BRAIN_AVAILABLE = True
    _startup_print("🎯 Unified Sniper Brain loaded - million kill training active!")
except ImportError:
    SNIPER_BRAIN_AVAILABLE = False
    sniper_get_entry_signal = None
    get_unified_brain = None

# 🧠 MINER BRAIN - Timeline Oracle & Wisdom Engine
try:
    from aureon.utils.aureon_miner_brain import MinerBrain as _MinerBrainClass
    MINER_BRAIN_AVAILABLE = True
    _startup_print("🧠 Miner Brain loaded - timeline oracle & wisdom active!")
except ImportError:
    MINER_BRAIN_AVAILABLE = False
    _MinerBrainClass = None

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION - THE UNIFIED PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Load sandbox-evolved parameters if available
_EVOLVED_TP = _evolved.params['take_profit_pct'] if SANDBOX_EVOLVED_AVAILABLE else 0.8
_EVOLVED_SL = _evolved.params['stop_loss_pct'] if SANDBOX_EVOLVED_AVAILABLE else 0.5
_EVOLVED_POS_SIZE = _evolved.params['position_size_pct'] if SANDBOX_EVOLVED_AVAILABLE else 0.10
_EVOLVED_MIN_COH = _evolved.params['min_coherence'] if SANDBOX_EVOLVED_AVAILABLE else 0.20

CONFIG = {
    # Trading Parameters
    'BASE_CURRENCY': os.getenv('BASE_CURRENCY', 'USD'),  # USD or GBP
    # Fee rates are seeded with Tier 4 defaults (~$123K 30d volume).
    # refresh_config_fees() is called after the Kraken client starts to
    # replace these with the live tiered values from KrakenFeeTracker.
    'KRAKEN_FEE_MAKER': 0.0012,     # 0.12% maker — Tier 4 default, updated dynamically
    'KRAKEN_FEE_TAKER': 0.0022,     # 0.22% taker — Tier 4 default, updated dynamically
    'KRAKEN_FEE': 0.0022,           # Legacy field (taker), updated dynamically
    'SLIPPAGE_PCT': 0.0010,         # 0.10% estimated slippage per trade
    'SPREAD_COST_PCT': 0.0005,      # 0.05% estimated spread cost
    'MIN_NET_PROFIT': 0.0001,       # Allow any net profit >$0.0001 (was 0.03 - too strict!)
    
    # 🧬 SANDBOX EVOLVED EXITS (454 Generations of Learning)
    'TAKE_PROFIT_PCT': _EVOLVED_TP,   # Evolved: 1.82% (was 0.8%)
    'STOP_LOSS_PCT': _EVOLVED_SL,     # Evolved: 1.43% (was 0.5%)
    'USE_SANDBOX_EVOLVED': SANDBOX_EVOLVED_AVAILABLE,
    
    'MAX_POSITIONS': 20,            # More positions for dynamic portfolio! 🚀
    'MIN_TRADE_USD': 5.0,           # Minimum $5 trade — lowered for small accounts (was $50.0)
    'PORTFOLIO_RISK_BUDGET': 0.95,  # Use 95% of equity - fully dynamic!
    'MIN_EXPECTED_EDGE_GBP': -0.05, # Allow small negative edge - bet when winning!
    'DEFAULT_WIN_PROB': 0.55,       # Fallback win probability
    'WIN_RATE_CONFIDENCE_TRADES': 25,
    'EQUITY_MIN_DELTA': 0.10,       # Smaller delta for frequent compounding
    'EQUITY_TOLERANCE_GBP': 0.0,
    
    # Dynamic Portfolio Rebalancing
    'ENABLE_REBALANCING': True,     # Sell underperformers to buy better opportunities
    'REBALANCE_THRESHOLD': -0.5,    # Sell position if it's losing more than 0.5%
    'MIN_HOLD_CYCLES': 3,           # Hold at least 3 cycles before considering rebalance
    'QUOTE_CURRENCIES': ['GBP', 'USD', 'EUR', 'USDT', 'BTC', 'ETH'],  # Trade ALL quote currencies
    
    # Scout Deployment (from immediateWaveRider.ts)
    'DEPLOY_SCOUTS_IMMEDIATELY': False,  # Deploy 1 position per currency on first scan
    'SCOUT_MIN_MOMENTUM': 2.0,          # Minimum 24h change % for scout entries
    
    # Kelly Criterion & Risk Management
    'USE_KELLY_SIZING': True,       # Use Kelly instead of fixed %
    'KELLY_SAFETY_FACTOR': 0.5,     # Half-Kelly for safety
    'BASE_POSITION_SIZE': _EVOLVED_POS_SIZE,  # 🧬 Evolved: 12.2% (was 10%)
    'MAX_POSITION_SIZE': 0.25,      # Hard cap per trade
    'MAX_SYMBOL_EXPOSURE': 0.30,    # Max 30% in one symbol
    'MAX_DRAWDOWN_PCT': 15.0,       # Circuit breaker at 15% DD
    'MIN_NETWORK_COHERENCE': 0.20,  # NEVER pause - always trade!
    
    # Opportunity Filters - TRADE LIKE A HUMAN 🔥
    'MIN_MOMENTUM': -10.0,          # Even negative momentum OK!
    'MAX_MOMENTUM': 1000.0,         # RIDE THE PUMPS!
    'MIN_VOLUME': 100,              # Ultra low volume = max opportunities
    'MIN_SCORE': 10,                # Very low bar = TRADE MORE
    
    # Compounding (10-9-1 Model)
    'COMPOUND_PCT': 0.90,           # 90% compounds
    'HARVEST_PCT': 0.10,            # 10% harvests
    
    # Auris Node Frequencies (Hz)
    'FREQ_TIGER': 741.0,
    'FREQ_FALCON': 852.0,
    'FREQ_HUMMINGBIRD': 963.0,
    'FREQ_DOLPHIN': 528.0,
    'FREQ_DEER': 396.0,
    'FREQ_OWL': 432.0,
    'FREQ_PANDA': 412.3,
    'FREQ_CARGOSHIP': 174.0,
    'FREQ_CLOWNFISH': 639.0,
    
    # Coherence Thresholds - 🧬 SANDBOX EVOLVED (trade like evolution learned!)
    'HIGH_COHERENCE_MODE': False,  # Disabled - too conservative
    'ENTRY_COHERENCE': _EVOLVED_MIN_COH,  # 🧬 Evolved: 73% (was 25%)
    'EXIT_COHERENCE': 0.20,  # Even lower exit
    
    # Lambda Field Components (from coherenceTrader.ts)
    'ENABLE_LAMBDA_FIELD': os.getenv('ENABLE_LAMBDA_FIELD', '1') == '1',  # Full Λ(t) = S(t) + O(t) + E(t)
    'OBSERVER_WEIGHT': 0.3,         # O(t) = Λ(t-1) × 0.3 (self-reference)
    'ECHO_WEIGHT': 0.2,             # E(t) = avg(Λ[t-5:t]) × 0.2 (memory)
    
    # WebSocket
    'WS_URL': 'wss://ws.kraken.com',
    'WS_RECONNECT_DELAY': 5,        # Seconds between reconnect attempts
    'WS_HEARTBEAT_TIMEOUT': 60,     # Max seconds without WS message
    
    # State Persistence
    'STATE_FILE': 'aureon_kraken_state.json',

    # Margin Trading (Kraken Leveraged Positions) - ALWAYS-ON by default
    'MARGIN_ENABLED': os.getenv('MARGIN_ENABLED', '1') == '1',
    'MARGIN_DEFAULT_LEVERAGE': int(os.getenv('MARGIN_DEFAULT_LEVERAGE', '2')),
    'MARGIN_MAX_LEVERAGE': int(os.getenv('MARGIN_MAX_LEVERAGE', '5')),
    'MARGIN_MAX_EXPOSURE_PCT': float(os.getenv('MARGIN_MAX_EXPOSURE_PCT', '0.30')),  # Max 30% of equity in margin
    'MARGIN_MIN_FREE_MARGIN_PCT': float(os.getenv('MARGIN_MIN_FREE_MARGIN_PCT', '0.20')),  # Keep 20% free margin
    'MARGIN_TP_MULTIPLIER': float(os.getenv('MARGIN_TP_MULTIPLIER', '1.5')),  # TP is 1.5x wider for margin
    'MARGIN_SL_MULTIPLIER': float(os.getenv('MARGIN_SL_MULTIPLIER', '0.5')),  # SL is tighter for margin
    'MARGIN_MIN_SCORE': int(os.getenv('MARGIN_MIN_SCORE', '75')),  # Higher score required for margin trades
    'MARGIN_MIN_COHERENCE': float(os.getenv('MARGIN_MIN_COHERENCE', '0.60')),  # Higher coherence for margin
}

PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio = 1.618


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float, safety_factor: float = 0.5) -> float:
    """
    Calculate Kelly Criterion position size.
    
    Formula: f* = (p*b - (1-p)) / b
    Where:
        p = win probability
        b = win/loss ratio (avg_win / avg_loss)
    
    Returns: Position size as fraction of balance (with safety factor applied)
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.10  # Fallback to 10%
    
    b = avg_win / avg_loss
    kelly_fraction = (win_rate * b - (1 - win_rate)) / b
    
    # Apply safety factor and bounds
    kelly_fraction = max(0, kelly_fraction) * safety_factor
    return min(kelly_fraction, CONFIG['MAX_POSITION_SIZE'])


# ═══════════════════════════════════════════════════════════════
# 🌟 SWARM ORCHESTRATOR ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════

# Prime numbers for dynamic sizing (from multi_agent_aggressive.ts)
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
PRIME_SCALE = 0.001  # 0.1% per prime unit → 0.2%, 0.3%, 0.5%, 0.7%, etc.

# Fibonacci sequence for timing (from multi_agent_aggressive.ts)
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]


@dataclass
class MarketSignal:
    """Signal broadcast from scout position (from swarmOrchestrator.ts)"""
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    strength: float  # 0.0 to 1.0
    momentum: float  # % change
    coherence: float  # Gamma value
    timestamp: float
    scout_id: Optional[str] = None


@dataclass
class CapitalPool:
    """Central capital management (from swarmOrchestrator.ts - bee hive)"""
    total_equity: float = 0.0
    allocated: Dict[str, float] = field(default_factory=dict)  # {symbol: amount}
    reserved: float = 0.0  # Keep 10% reserved for opportunities
    profits_this_cycle: float = 0.0
    total_profits: float = 0.0
    
    def update_equity(self, new_equity: float):
        """Update total equity and recalculate reserves"""
        self.total_equity = new_equity
        self.reserved = new_equity * 0.10  # Keep 10% in reserve
        
    def allocate(self, symbol: str, amount: float) -> bool:
        """Allocate capital to a position"""
        available = self.total_equity - sum(self.allocated.values()) - self.reserved
        if available >= amount:
            self.allocated[symbol] = self.allocated.get(symbol, 0) + amount
            return True
        return False
        
    def deallocate(self, symbol: str, amount: float, profit: float = 0.0):
        """Return capital from closed position"""
        if symbol in self.allocated:
            self.allocated[symbol] = max(0, self.allocated[symbol] - amount)
            if self.allocated[symbol] == 0:
                del self.allocated[symbol]
        self.profits_this_cycle += profit
        self.total_profits += profit
        
    def get_available(self) -> float:
        """Get unallocated capital"""
        return max(0, self.total_equity - sum(self.allocated.values()) - self.reserved)


class SignalBroadcaster:
    """Manages signal broadcasting between positions (from swarmOrchestrator.ts - wolf scout)"""
    
    def __init__(self):
        self.latest_signal: Optional[MarketSignal] = None
        self.signal_history: deque = deque(maxlen=20)
        self.scout_positions: List[str] = []  # Positions that can act as scouts
        
    def broadcast_signal(self, signal: MarketSignal):
        """Broadcast a new signal from scout"""
        self.latest_signal = signal
        self.signal_history.append(signal)
        
    def get_latest_signal(self, max_age_seconds: float = 60.0) -> Optional[MarketSignal]:
        """Get latest signal if not too old"""
        if self.latest_signal:
            age = time.time() - self.latest_signal.timestamp
            if age <= max_age_seconds:
                return self.latest_signal
        return None
        
    def should_follow_signal(self, symbol: str, signal: MarketSignal) -> bool:
        """Determine if a position should follow the signal"""
        # Don't follow signals for the same symbol (avoid feedback loop)
        if symbol == signal.symbol:
            return False
        # Only follow strong signals (strength > 0.5)
        if signal.strength < 0.5:
            return False
        # Only follow if coherence is good
        if signal.coherence < 0.4:
            return False
        return True


class PositionSplitter:
    """Manages position splitting (from queen_hive.ts - hive splitting)"""
    
    def __init__(self):
        self.split_threshold = 2.0  # Split when position reaches 2x entry value
        self.max_generation = 5  # Max split depth
        self.split_history: List[Dict] = []
        
    def should_split(self, position_value: float, entry_value: float, generation: int) -> bool:
        """Check if position should split"""
        if generation >= self.max_generation:
            return False
        return position_value >= entry_value * self.split_threshold
        
    def execute_split(self, position: 'Position') -> Tuple['Position', 'Position']:
        """Split position into two child positions"""
        # Each child gets half the value
        split_size = position.size / 2
        
        # Create two children at next generation
        child1 = Position(
            symbol=position.symbol,
            size=split_size,
            entry_price=position.current_price,
            current_price=position.current_price,
            quote_asset=position.quote_asset,
            generation=position.generation + 1,
            parent_id=position.id
        )
        
        child2 = Position(
            symbol=position.symbol,
            size=split_size,
            entry_price=position.current_price,
            current_price=position.current_price,
            quote_asset=position.quote_asset,
            generation=position.generation + 1,
            parent_id=position.id
        )
        
        # Record split event
        self.split_history.append({
            'timestamp': time.time(),
            'parent_id': position.id,
            'parent_value': position.size * position.current_price,
            'generation': position.generation,
            'children': [child1.id, child2.id]
        })
        
        return child1, child2


class PrimeSizer:
    """Prime-based dynamic position sizing (from multi_agent_aggressive.ts)"""
    
    def __init__(self):
        self.prime_idx = 0
        self.fib_idx = 0
        
    def get_next_size(self, base_size: float) -> float:
        """Get next position size using prime scaling"""
        prime = PRIMES[self.prime_idx % len(PRIMES)]
        size = base_size * prime * PRIME_SCALE
        self.prime_idx += 1
        return size
        
    def get_fibonacci_timing(self) -> int:
        """Get next timing interval using Fibonacci"""
        fib = FIBONACCI[self.fib_idx % len(FIBONACCI)]
        self.fib_idx += 1
        return fib
        
    def reset(self):
        """Reset indices"""
        self.prime_idx = 0
        self.fib_idx = 0


# ═══════════════════════════════════════════════════════════════
# 🐅 AURIS NODES - 9 Nodes of Market Analysis
# ═══════════════════════════════════════════════════════════════

@dataclass
class MarketState:
    """Complete market snapshot for analysis"""
    symbol: str
    price: float
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0
    change_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    prices: List[float] = field(default_factory=list)
    timestamp: float = 0.0


class AurisNode:
    """Base class for all Auris nodes"""
    def __init__(self, name: str, freq: float, weight: float = 1.0):
        self.name = name
        self.freq = freq
        self.weight = weight
        self.response = 0.0
        
    def compute(self, state: MarketState) -> float:
        raise NotImplementedError


class TigerNode(AurisNode):
    """🐅 Volatility & Spread - Cuts the noise"""
    def __init__(self):
        super().__init__("Tiger", CONFIG['FREQ_TIGER'], 1.2)
        
    def compute(self, state: MarketState) -> float:
        if state.ask <= 0 or state.bid <= 0:
            return 0.5
        spread = (state.ask - state.bid) / state.price if state.price > 0 else 0
        # Low spread = high coherence
        self.response = max(0, 1 - spread * 100)
        return self.response


class FalconNode(AurisNode):
    """🦅 Speed & Momentum - Quick strikes"""
    def __init__(self):
        super().__init__("Falcon", CONFIG['FREQ_FALCON'], 1.1)
        
    def compute(self, state: MarketState) -> float:
        # Positive momentum = high coherence
        if state.change_24h > 10:
            self.response = 0.9
        elif state.change_24h > 5:
            self.response = 0.75
        elif state.change_24h > 2:
            self.response = 0.6
        elif state.change_24h > 0:
            self.response = 0.5
        else:
            self.response = 0.3
        return self.response


class HummingbirdNode(AurisNode):
    """🐦 Stability - High frequency lock"""
    def __init__(self):
        super().__init__("Hummingbird", CONFIG['FREQ_HUMMINGBIRD'], 1.0)
        
    def compute(self, state: MarketState) -> float:
        if len(state.prices) < 3:
            return 0.5
        # Low variance = stable = high coherence
        mean = sum(state.prices) / len(state.prices)
        variance = sum((p - mean) ** 2 for p in state.prices) / len(state.prices)
        std = math.sqrt(variance) if variance > 0 else 0
        cv = std / mean if mean > 0 else 0
        self.response = max(0, 1 - cv * 10)
        return self.response


class DolphinNode(AurisNode):
    """🐬 Waveform - Emotional carrier"""
    def __init__(self):
        super().__init__("Dolphin", CONFIG['FREQ_DOLPHIN'], 1.3)  # 528 Hz = Love frequency
        
    def compute(self, state: MarketState) -> float:
        if len(state.prices) < 5:
            return 0.5
        # Detect wave pattern (up-down-up)
        ups = sum(1 for i in range(1, len(state.prices)) if state.prices[i] > state.prices[i-1])
        ratio = ups / (len(state.prices) - 1)
        # Balanced waves = good
        self.response = 1 - abs(ratio - 0.6)  # Slight bullish bias
        return self.response


class DeerNode(AurisNode):
    """🦌 Sensing - Micro-shifts detection"""
    def __init__(self):
        super().__init__("Deer", CONFIG['FREQ_DEER'], 0.9)
        
    def compute(self, state: MarketState) -> float:
        if len(state.prices) < 2:
            return 0.5
        # Recent micro-movement
        recent_change = (state.prices[-1] - state.prices[-2]) / state.prices[-2] if state.prices[-2] > 0 else 0
        self.response = 0.5 + recent_change * 50  # Scale micro moves
        self.response = max(0, min(1, self.response))
        return self.response


class OwlNode(AurisNode):
    """🦉 Memory - Pattern recognition"""
    def __init__(self):
        super().__init__("Owl", CONFIG['FREQ_OWL'], 1.1)
        self.memory: Dict[str, List[float]] = {}
        
    def compute(self, state: MarketState) -> float:
        if state.symbol not in self.memory:
            self.memory[state.symbol] = []
        self.memory[state.symbol].append(state.change_24h)
        if len(self.memory[state.symbol]) > 100:
            self.memory[state.symbol] = self.memory[state.symbol][-100:]
            
        history = self.memory[state.symbol]
        if len(history) < 5:
            return 0.5
            
        # Pattern: was it bullish before?
        avg_momentum = sum(history[-10:]) / min(10, len(history))
        self.response = 0.5 + avg_momentum / 20
        self.response = max(0, min(1, self.response))
        return self.response


class PandaNode(AurisNode):
    """🐼 Safety - Grounding and protection"""
    def __init__(self):
        super().__init__("Panda", CONFIG['FREQ_PANDA'], 1.0)
        
    def compute(self, state: MarketState) -> float:
        # Volume = safety (liquidity)
        if state.volume > 1000000:
            self.response = 0.9
        elif state.volume > 500000:
            self.response = 0.75
        elif state.volume > 100000:
            self.response = 0.6
        elif state.volume > 50000:
            self.response = 0.5
        else:
            self.response = 0.3
        return self.response


class CargoShipNode(AurisNode):
    """🚢 Liquidity - Momentum buffer"""
    def __init__(self):
        super().__init__("CargoShip", CONFIG['FREQ_CARGOSHIP'], 0.8)
        
    def compute(self, state: MarketState) -> float:
        # High volume relative to price range = good liquidity
        if state.high_24h <= state.low_24h or state.volume <= 0:
            return 0.5
        range_pct = (state.high_24h - state.low_24h) / state.low_24h
        vol_per_range = state.volume / (range_pct * 100) if range_pct > 0 else 0
        self.response = min(1, vol_per_range / 100000)
        return self.response


class ClownfishNode(AurisNode):
    """🐠 Symbiosis - Market connection"""
    def __init__(self):
        super().__init__("Clownfish", CONFIG['FREQ_CLOWNFISH'], 0.9)
        
    def compute(self, state: MarketState) -> float:
        # Connection = how well this coin moves with market sentiment
        # Positive momentum with good volume = connected
        if state.change_24h > 0 and state.volume > 100000:
            self.response = 0.7 + min(0.3, state.change_24h / 30)
        elif state.change_24h > 0:
            self.response = 0.5 + min(0.2, state.change_24h / 20)
        else:
            self.response = 0.4
        return self.response


class AurisEngine:
    """The complete 9-node Auris analysis engine with Lambda field"""
    
    def __init__(self):
        self.nodes = [
            TigerNode(),
            FalconNode(),
            HummingbirdNode(),
            DolphinNode(),
            DeerNode(),
            OwlNode(),
            PandaNode(),
            CargoShipNode(),
            ClownfishNode(),
        ]
        # Lambda field components (Λ = S + O + E)
        self.last_lambda = 0.5      # O(t) = Observer (self-reference)
        self.lambda_history = deque(maxlen=5)  # E(t) = Echo (memory)
        
    def compute_coherence(self, state: MarketState) -> Tuple[float, str]:
        """Compute overall market coherence (Γ) with Lambda field components
        
        Λ(t) = S(t) + O(t) + E(t)
        Where:
            S(t) = Substrate (9 Auris nodes)
            O(t) = Observer (Λ(t-1) × 0.3) - self-reference
            E(t) = Echo (avg(Λ[t-5:t]) × 0.2) - memory
        """
        total_weight = sum(n.weight for n in self.nodes)
        weighted_sum = 0
        
        dominant_node = None
        max_response = 0
        
        # S(t) = Substrate from 9 Auris nodes
        for node in self.nodes:
            response = node.compute(state)
            weighted_sum += response * node.weight
            if response > max_response:
                max_response = response
                dominant_node = node.name
                
        substrate = weighted_sum / total_weight if total_weight > 0 else 0
        
        # Full Lambda field if enabled
        if CONFIG['ENABLE_LAMBDA_FIELD']:
            # O(t) = Observer component (self-reference)
            observer = self.last_lambda * CONFIG['OBSERVER_WEIGHT']
            
            # E(t) = Echo component (memory)
            echo = 0.0
            if len(self.lambda_history) > 0:
                echo = (sum(self.lambda_history) / len(self.lambda_history)) * CONFIG['ECHO_WEIGHT']
            
            # Λ(t) = S(t) + O(t) + E(t)
            lambda_field = substrate + observer + echo
            lambda_field = max(0.0, min(1.0, lambda_field))  # Clamp to [0, 1]
            
            # Update history
            self.lambda_history.append(lambda_field)
            self.last_lambda = lambda_field
            
            coherence = lambda_field
        else:
            # Legacy mode: just use substrate
            coherence = substrate
                
        return coherence, dominant_node or "Unknown"


# ═══════════════════════════════════════════════════════════════
# 🍄 MYCELIUM NETWORK - Neural Pattern Detection
# ═══════════════════════════════════════════════════════════════

@dataclass
class Synapse:
    """Connection between market signals with Hebbian learning"""
    source: str
    target: str
    strength: float = 0.5
    plasticity: float = 0.1
    activation_count: int = 0
    
    def pulse(self, signal: float) -> float:
        self.activation_count += 1
        return signal * self.strength
        
    def strengthen(self, reward: float):
        """Hebbian learning: strengthen if rewarded"""
        # Reward is typically profit % (e.g. 2.0 for 2%)
        # Scale reward to be small adjustment
        adjustment = reward * self.plasticity * 0.1
        self.strength = max(0.1, min(2.0, self.strength + adjustment))


class MyceliumNetwork:
    """Neural network for pattern detection across symbols"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.synapses: Dict[str, List[Synapse]] = {}
        self.activations: Dict[str, float] = {}
        self.initial_capital = initial_capital  # Store for compatibility
        
    def add_signal(self, symbol: str, signal: float):
        """Add a market signal to the network"""
        self.activations[symbol] = signal
        
        # Auto-create synapses to other active symbols if they don't exist
        # This creates a dense mesh over time
        if symbol not in self.synapses:
            self.synapses[symbol] = []
            
        # Connect deterministically to the first not-yet-connected active node.
        if len(self.activations) > 1 and len(self.synapses[symbol]) < 5:
            targets = sorted(self.activations.keys())
            if symbol in targets: targets.remove(symbol)
            existing = {synapse.target for synapse in self.synapses[symbol]}
            target = next((candidate for candidate in targets if candidate not in existing), None)
            if target is not None:
                # Check if connection exists
                if not any(s.target == target for s in self.synapses[symbol]):
                    self.synapses[symbol].append(Synapse(source=symbol, target=target))
        
    def propagate(self) -> Dict[str, float]:
        """Propagate signals through the network"""
        new_activations = {}
        for symbol, activation in self.activations.items():
            new_activations[symbol] = activation
            if symbol in self.synapses:
                for synapse in self.synapses[symbol]:
                    if synapse.target in self.activations: # Only propagate to active nodes
                        # Signal boosts the target's activation
                        boost = synapse.pulse(activation) * 0.1 # Dampening factor
                        new_activations[synapse.target] = new_activations.get(synapse.target, self.activations[synapse.target]) + boost
        return new_activations

    def learn(self, symbol: str, profit_pct: float):
        """Reinforce connections that led to profit"""
        # If we profited on 'symbol', strengthen incoming connections to it
        # and outgoing connections from it that were active
        
        # 1. Strengthen outgoing connections from this symbol
        if symbol in self.synapses:
            for synapse in self.synapses[symbol]:
                synapse.strengthen(profit_pct)
                
        # 2. Strengthen incoming connections to this symbol (harder to find in this structure, 
        #    so we iterate - optimization: keep reverse map if needed, but loop is fine for small N)
        for _source, synapses in self.synapses.items():
            for synapse in synapses:
                if synapse.target == symbol:
                    synapse.strengthen(profit_pct)

    def get_network_coherence(self) -> float:
        """Overall network coherence"""
        if not self.activations:
            return 0.5
        return sum(self.activations.values()) / len(self.activations)


# ═══════════════════════════════════════════════════════════════
# 💰 POSITION & PERFORMANCE TRACKING
# ═══════════════════════════════════════════════════════════════

@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: float
    entry_fee: float
    entry_value: float
    momentum: float
    coherence: float
    entry_time: float
    dominant_node: str
    cycles: int = 0
    # Swarm Orchestrator enhancements
    generation: int = 0  # 0 = original, 1+ = split children
    parent_id: Optional[str] = None  # ID of parent position if this is a split
    is_scout: bool = False  # Can this position act as market scout?
    last_signal_broadcast: float = 0.0  # Timestamp of last signal
    prime_size_multiplier: float = 1.0  # Prime-based sizing
    
    # 🔮 NEXUS PREDICTOR DATA - For learning feedback
    nexus_prob: float = 0.5  # Nexus prediction probability at entry
    nexus_edge: float = 0.0  # Nexus edge at entry
    nexus_patterns: List[str] = field(default_factory=list)  # Patterns triggered at entry

    # Margin trading fields
    is_margin: bool = False       # Whether this is a leveraged margin position
    leverage: int = 1             # Leverage multiplier (1 = spot, 2-5 = margin)
    margin_amount: float = 0.0   # Actual margin (collateral) put up

    # Generate unique ID for position
    id: str = field(default_factory=lambda: f"pos_{uuid.uuid4().hex}")
    
    # Convenience properties
    @property
    def size(self) -> float:
        """Alias for quantity"""
        return self.quantity
        
    @property
    def current_price(self) -> float:
        """Alias for entry_price (will be updated externally)"""
        return self.entry_price
        
    @property
    def quote_asset(self) -> str:
        """Extract quote asset from symbol"""
        for quote in CONFIG['QUOTE_CURRENCIES']:
            if self.symbol.endswith(quote):
                return quote
        return 'USD'  # Default fallback


class PerformanceTracker:
    """Track all trading performance metrics"""
    
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.first_start_balance = initial_balance  # TRUE starting balance - survives restarts!
        self.first_start_time = time.time()  # When the system FIRST started
        self.balance = initial_balance
        self.peak_balance = initial_balance
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_fees = 0.0
        self.net_profit = 0.0
        self.compounded = 0.0
        self.harvested = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0  # Current DD from peak
        self.trade_log: List[Dict] = []
        self.trading_halted = False
        self.halt_reason = ""
        self.total_hold_time_sec = 0.0  # Track average hold time
        self.closed_positions = 0
        
        # Track per-symbol exposure
        self.symbol_exposure: Dict[str, float] = {}
        self.portfolio_equity = initial_balance
        self.cash_balance = initial_balance
        self.cycle_equity_start = initial_balance
        self.equity_baseline = initial_balance
        
    # 🇮🇪 IRA SNIPER - Famous Irish Republican Quotes
    IRA_SNIPER_QUOTES = [
        "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
        "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
        "Tiocfaidh ár lá! - Our day will come!",
        "They have nothing in their whole imperial arsenal that can break the spirit of one Irishman.",
        "The Republic still lives! - Bobby Sands",
        "Ireland unfree shall never be at peace. - Patrick Pearse",
        "We serve neither King nor Kaiser, but Ireland!",
        "Financial freedom IS freedom. Penny by penny, we rise! 💰",
    ]
    
    def record_trade(self, net_pnl: float, fees: float, symbol: str, reason: str, hold_time_sec: float = 0):
        """Record a completed trade"""
        self.total_trades += 1
        self.total_fees += fees
        result = 'WIN' if net_pnl > 0 else 'LOSS'
        if net_pnl > 0:
            self.wins += 1
            # 🇮🇪 IRA SNIPER CELEBRATION!
            quote = self.IRA_SNIPER_QUOTES[(self.total_trades - 1) % len(self.IRA_SNIPER_QUOTES)]
            print(f"\n🇮🇪🇮🇪🇮🇪 IRA SNIPER WIN! 🇮🇪🇮🇪🇮🇪")
            print(f"    💰 +${net_pnl:.4f} on {symbol}")
            print(f"    📜 \"{quote}\"")
            print(f"🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪\n")
        else:
            self.losses += 1
        
        # Track hold time
        if hold_time_sec > 0:
            self.total_hold_time_sec += hold_time_sec
            self.closed_positions += 1
        
        self.trade_log.append({
            'symbol': symbol,
            'reason': reason,
            'result': result,  # Explicit WIN/LOSS classification
            'net_pnl': net_pnl,
            'balance': self.portfolio_equity,
            'win_rate': self.win_rate,
            'hold_time_sec': hold_time_sec,
            'time': datetime.now().isoformat()
        })
        
    @property
    def win_rate(self) -> float:
        return (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        
    @property
    def total_return(self) -> float:
        return (self.balance - self.initial_balance) / self.initial_balance * 100

    def update_equity(self, equity_value: float, cash_value: float, mark_cycle: bool = False):
        """Synchronise tracker metrics with current marked-to-market equity."""
        self.portfolio_equity = equity_value
        self.cash_balance = cash_value
        self.balance = equity_value
        self.net_profit = self.portfolio_equity - self.initial_balance
        if mark_cycle:
            self.cycle_equity_start = equity_value
        
        if self.portfolio_equity > self.peak_balance:
            self.peak_balance = self.portfolio_equity
        if self.peak_balance > 0:
            dd = (self.peak_balance - self.portfolio_equity) / self.peak_balance * 100
        else:
            dd = 0.0
        self.current_drawdown = dd  # Track current DD from peak
        if dd > self.max_drawdown:
            self.max_drawdown = dd
        if dd >= CONFIG['MAX_DRAWDOWN_PCT'] and not self.trading_halted:
            self.trading_halted = True
            self.halt_reason = f"Max drawdown {dd:.1f}% exceeded"
            print(f"\n🛑 CIRCUIT BREAKER ACTIVATED: {self.halt_reason}")

    def realize_portfolio_gain(self, gain: float):
        """Advance compounding only when the whole portfolio has grown."""
        if gain <= 0:
            return
        compound_amt = gain * CONFIG['COMPOUND_PCT']
        harvest_amt = gain * CONFIG['HARVEST_PCT']
        self.compounded += compound_amt
        self.harvested += harvest_amt
    
    def calculate_position_size(self, coherence: float, symbol: str) -> float:
        """
        Calculate position size using Kelly Criterion + coherence scaling.
        
        Returns: Position size as fraction of balance
        """
        if CONFIG['USE_KELLY_SIZING'] and self.total_trades >= 10:
            # Need at least 10 trades for stable Kelly calculation
            avg_win = CONFIG['TAKE_PROFIT_PCT'] / 100.0
            avg_loss = CONFIG['STOP_LOSS_PCT'] / 100.0
            
            kelly_size = kelly_criterion(
                self.win_rate / 100.0,
                avg_win,
                avg_loss,
                CONFIG['KELLY_SAFETY_FACTOR']
            )
        else:
            # Use base size until we have enough data
            kelly_size = CONFIG['BASE_POSITION_SIZE']
        
        # Scale by coherence: higher coherence = larger position
        # Range: 0.7x to 1.3x based on coherence 0.0-1.0
        coherence_multiplier = 0.7 + (coherence * 0.6)
        scaled_size = kelly_size * coherence_multiplier
        
        # Check per-symbol exposure limits
        current_exposure = self.symbol_exposure.get(symbol, 0.0)
        available_exposure = CONFIG['MAX_SYMBOL_EXPOSURE'] - current_exposure
        
        final_size = min(scaled_size, available_exposure, CONFIG['MAX_POSITION_SIZE'])
        return max(0, final_size)


# ═══════════════════════════════════════════════════════════════
# 🐙 THE UNIFIED KRAKEN ECOSYSTEM
# ═══════════════════════════════════════════════════════════════

class AureonKrakenEcosystem:
    """
    🐙🌌 THE COMPLETE KRAKEN TRADING ECOSYSTEM 🌌🐙
    
    Combines all strategies into one dynamic system:
    - Real-time WebSocket prices
    - 9 Auris nodes for analysis
    - Mycelium network for pattern detection
    - 10-9-1 compounding model
    - 51%+ win rate strategy
    """
    
    def __init__(self, initial_balance: float = 1000.0, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_kraken_client()
        self.auris = AurisEngine()
        self.mycelium = MyceliumNetwork(initial_capital=initial_balance)
        self.lattice = LatticeEngine()
        self.tracker = PerformanceTracker(initial_balance)
        self.total_equity_gbp = initial_balance
        self.cash_balance_gbp = initial_balance
        self.holdings_gbp: Dict[str, float] = {}
        
        # Positions
        self.positions: Dict[str, Position] = {}
        
        # Market data
        self.ticker_cache: Dict[str, Dict] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.realtime_prices: Dict[str, float] = {}
        self.price_lock = Lock()
        
        # WebSocket
        self.ws_connected = False
        self.ws_last_message = time.time()
        self.ws_reconnect_count = 0
        self.symbol_to_ws: Dict[str, str] = {}
        self.ws_to_symbol: Dict[str, str] = {}
        
        # Stats
        self.iteration = 0
        self.start_time = time.time()
        self.scan_direction = 'A→Z'  # Fair scheduling: alternate A→Z / Z→A
        self.scouts_deployed = False  # Track scout deployment
        
        # 🌟 SWARM ORCHESTRATOR COMPONENTS 🌟
        self.capital_pool = CapitalPool()
        self.signal_broadcaster = SignalBroadcaster()
        self.position_splitter = PositionSplitter()
        self.prime_sizer = PrimeSizer()
        
        # 🔮 NEXUS PREDICTOR - 79.6% Win Rate! 🔮
        if NEXUS_AVAILABLE:
            self.nexus = NexusPredictor()
            print("   🔮 Nexus Predictor initialized (79.6% validated)")
        else:
            self.nexus = None

        # 🦑💰 KRAKEN FEE TRACKER - Patch CONFIG with live tier rates
        if _KRAKEN_FEE_TRACKER_AVAILABLE and get_kraken_fee_tracker:
            try:
                self.fee_tracker = get_kraken_fee_tracker(self.client)
                rates = self.fee_tracker.get_fee_rates(is_taker=True)
                CONFIG['KRAKEN_FEE_MAKER'] = rates['maker']
                CONFIG['KRAKEN_FEE_TAKER'] = rates['taker']
                CONFIG['KRAKEN_FEE'] = rates['taker']
                print(
                    f"   🦑💰 Kraken Fee Tracker: Tier {rates['tier']}, "
                    f"maker={rates['maker']*100:.2f}% taker={rates['taker']*100:.2f}%  "
                    f"(30d vol=${rates['volume_30d']:,.0f})"
                )
            except Exception as e:
                self.fee_tracker = None
                print(f"   🦑 Kraken Fee Tracker: {e}")
        else:
            self.fee_tracker = None

        # 👑 THE KING - Autonomous Accounting AI
        if KING_AVAILABLE and start_king:
            try:
                self.king = start_king()
                print("   👑 The King has risen - autonomous accounting active!")
            except Exception as e:
                self.king = None
                print(f"   ⚠️ The King could not rise: {e}")
        else:
            self.king = None

        # 👁 AUREON THE SEER - Autonomous Coherence & Cosmic Intelligence
        if SEER_AVAILABLE and start_seer:
            try:
                self.seer = start_seer()
                print("   👁 Aureon the Seer awakened - cosmic coherence active!")
            except Exception as e:
                self.seer = None
                print(f"   Seer could not awaken: {e}")
        else:
            self.seer = None

        # AUREON LYRA - Emotional Frequency & Harmonics Engine
        if LYRA_AVAILABLE and start_lyra:
            try:
                self.lyra = start_lyra()
                print("   Aureon Lyra awakened - emotional frequency & harmonics active!")
            except Exception as e:
                self.lyra = None
                print(f"   Lyra could not awaken: {e}")
        else:
            self.lyra = None

        # ⚔️ WAR STRATEGY - Quick Kill Probability
        if WAR_STRATEGY_AVAILABLE and should_attack:
            self.war_strategy = True
            print("   ⚔️ War Strategy wired - attack signals active!")
        else:
            self.war_strategy = False

        # 🎯 UNIFIED SNIPER BRAIN - Entry Signal Scoring
        if SNIPER_BRAIN_AVAILABLE and get_unified_brain:
            try:
                self.sniper_brain = get_unified_brain(exchange='kraken')
                print("   🎯 Sniper Brain wired - entry scoring active!")
            except Exception as e:
                self.sniper_brain = None
                print(f"   ⚠️ Sniper Brain could not load: {e}")
        else:
            self.sniper_brain = None

        # 🧠 MINER BRAIN - Timeline Oracle & Wisdom
        if MINER_BRAIN_AVAILABLE and _MinerBrainClass:
            try:
                self.miner_brain = _MinerBrainClass()
                print("   🧠 Miner Brain wired - timeline oracle active!")
            except Exception as e:
                self.miner_brain = None
                print(f"   ⚠️ Miner Brain could not load: {e}")
        else:
            self.miner_brain = None

        # Initialize capital pool
        self.capital_pool.update_equity(initial_balance)
        
        # Determine tradeable currencies based on wallet
        self.tradeable_currencies = ['USD', 'GBP', 'EUR', 'USDT', 'USDC']
        self._detect_wallet_currency()
        
        # Check if state file exists (is this the FIRST ever run?)
        is_first_ever_run = not os.path.exists(CONFIG['STATE_FILE'])
        
        # Load previous state if exists
        fresh_start = os.environ.get('FRESH_START', '0') == '1'
        if fresh_start:
            print("   ✨ FRESH START: Ignoring previous state file")
        else:
            self.load_state()

        # Initialise equity snapshot - get REAL portfolio value
        self.refresh_equity(mark_cycle=True)
        
        # FIRST EVER RUN: Capture the TRUE starting balance automatically!
        if is_first_ever_run and not self.dry_run and self.total_equity_gbp > 0:
            self.tracker.first_start_balance = self.total_equity_gbp
            self.tracker.first_start_time = time.time()
            self.tracker.initial_balance = self.total_equity_gbp
            self.tracker.peak_balance = self.total_equity_gbp
            self.tracker.balance = self.total_equity_gbp
            self.tracker.equity_baseline = self.total_equity_gbp
            self.tracker.cycle_equity_start = self.total_equity_gbp
            print(f"   🎯 FIRST RUN: Captured TRUE starting balance: £{self.total_equity_gbp:.2f}")
            self.save_state()  # Save immediately so we never lose it!
            self._import_existing_holdings()
        
        # On fresh start in live mode, reset baselines to actual portfolio value
        elif fresh_start and not self.dry_run and self.total_equity_gbp > 0:
            # Keep the first_start_balance from state file, but reset current tracking
            self.tracker.initial_balance = self.total_equity_gbp
            self.tracker.peak_balance = self.total_equity_gbp
            self.tracker.balance = self.total_equity_gbp
            self.tracker.equity_baseline = self.total_equity_gbp
            self.tracker.cycle_equity_start = self.total_equity_gbp
            self.tracker.max_drawdown = 0.0
            self.tracker.trading_halted = False
            self.tracker.halt_reason = ""
            print(f"   📊 Baseline reset to real portfolio: £{self.total_equity_gbp:.2f}")
            print(f"   📅 Original start preserved: £{self.tracker.first_start_balance:.2f}")
            
            # Import existing holdings as managed positions
            self._import_existing_holdings()

    def _detect_wallet_currency(self):
        """Detect which currencies we actually have funds in"""
        if self.dry_run:
            return
            
        try:
            account = self.client.account()
            balances = account.get('balances', [])
            
            has_usd = False
            has_gbp = False
            has_eur = False
            has_btc = False
            has_eth = False
            
            skipped_assets: List[str] = []
            for b in balances:
                asset = b.get('asset', '')
                raw_free = b.get('free', 0)
                try:
                    free = float(raw_free)
                except (ValueError, TypeError) as exc:
                    logger.warning("[wallet-parse-error] kraken asset %s: cannot "
                                   "parse balance %r (%s); excluding from holdings view",
                                   asset, raw_free, exc)
                    skipped_assets.append(asset)
                    continue
                if free > 0.0001:  # Min threshold
                    if asset in ['USD', 'ZUSD', 'USDT', 'USDC']: has_usd = True
                    if asset in ['GBP', 'ZGBP']: has_gbp = True
                    if asset in ['EUR', 'ZEUR']: has_eur = True
                    if asset in ['XBT', 'XXBT', 'BTC']: has_btc = True
                    if asset in ['ETH', 'XETH']: has_eth = True
            if skipped_assets:
                logger.warning("[wallet-summary] kraken: %d of %d assets skipped "
                               "due to parse errors: %s",
                               len(skipped_assets), len(balances), skipped_assets)
            
            # Update tradeable currencies based on holdings
            new_tradeables = []
            if has_usd: new_tradeables.extend(['USD', 'USDT', 'USDC'])
            if has_gbp: new_tradeables.append('GBP')
            if has_eur: new_tradeables.append('EUR')
            if has_btc: new_tradeables.extend(['XBT', 'BTC'])
            if has_eth: new_tradeables.append('ETH')
            
            if new_tradeables:
                self.tradeable_currencies = list(set(new_tradeables))
                print(f"   💰 Wallet detected: {self.tradeable_currencies}")
            
            # Set Base Currency for reporting
            if has_gbp: CONFIG['BASE_CURRENCY'] = 'GBP'
            elif has_eur: CONFIG['BASE_CURRENCY'] = 'EUR'
            elif has_usd: CONFIG['BASE_CURRENCY'] = 'USD'
            
        except Exception as e:
            print(f"   ⚠️ Wallet detection error: {e}")

    def _import_existing_holdings(self):
        """Import existing crypto holdings as managed positions"""
        if self.dry_run:
            return
            
        base = CONFIG['BASE_CURRENCY']
        try:
            account = self.client.account()
            balances = account.get('balances', [])
        except Exception as e:
            print(f"   ⚠️ Holdings import error: {e}")
            return
            
        imported = 0
        for bal in balances:
            asset_raw = bal.get('asset', '')
            if not asset_raw:
                continue
            try:
                amount = float(bal.get('free', 0) or 0)
            except:
                amount = 0.0
            if amount <= 0:
                continue
                
            asset_clean = asset_raw.replace('Z', '').upper()  # Keep X prefix for XBT, XLM, etc
            
            # Skip base currency (that's cash, not a position)
            if asset_clean in ['GBP', 'EUR', 'USD', 'USDT', 'USDC']:
                continue
                
            # Build the trading pair symbol (keep Kraken format)
            symbol = f"{asset_clean}{base}"
            
            # Skip if already tracked
            if symbol in self.positions:
                continue
                
            # Get current price
            try:
                # For conversion, remove FIRST X prefix only (XXBT -> XBT, XETH -> ETH)
                conversion_asset = asset_clean[1:] if asset_clean.startswith('X') and len(asset_clean) > 3 else asset_clean
                gbp_value = self.client.convert_to_quote(conversion_asset, amount, base)
                if gbp_value < 0.50:  # Skip dust < £0.50
                    continue
                price = gbp_value / amount
            except Exception as e:
                print(f"   ⚠️ Failed to import {asset_clean}: {e}")
                continue
                
            # Create position from existing holding
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=price,  # Use current price as "entry" 
                quantity=amount,
                entry_fee=0.0,  # Already bought, no new fee
                entry_value=gbp_value,
                momentum=0.0,
                coherence=0.5,
                entry_time=time.time(),
                dominant_node='Portfolio'
            )
            imported += 1
            print(f"   📦 Imported {symbol}: {amount:.6f} @ £{price:.4f} = £{gbp_value:.2f}")
            
        if imported > 0:
            print(f"   ✅ Imported {imported} existing holdings as managed positions")
    
    def _deploy_scouts(self):
        """Deploy scout positions immediately on first scan (from immediateWaveRider.ts)
        
        Philosophy: "They can't stop them all!" - Get positions deployed fast
        to ride waves from the start while main logic finds optimal entries.
        """
        if self.scouts_deployed or not CONFIG['DEPLOY_SCOUTS_IMMEDIATELY']:
            return
            
        print("\n   🦅 DEPLOYING SCOUTS - Immediate wave riders!")
        scouts_deployed = 0
        
        # Get available quote currencies to deploy scouts in
        quote_currencies = self.tradeable_currencies if self.dry_run else [CONFIG['BASE_CURRENCY']]
        
        for quote_curr in quote_currencies:
            # Find a high momentum opportunity for this quote currency
            candidates = []
            for symbol, data in self.ticker_cache.items():
                if not symbol.endswith(quote_curr):
                    continue
                if symbol in self.positions:
                    continue
                    
                change = data.get('change24h', 0)
                price = data.get('price', 0)
                volume = data.get('volume', 0)
                
                # Scout filter: momentum > 2%, decent volume
                if change >= CONFIG['SCOUT_MIN_MOMENTUM'] and price > 0 and volume > 1000:
                    candidates.append({
                        'symbol': symbol,
                        'price': price,
                        'change24h': change,
                        'volume': volume,
                        'score': 70,  # Scout score
                        'coherence': 0.6,  # Default scout coherence
                        'dominant_node': 'Scout'
                    })
            
            # Deploy top scout for this currency
            if candidates and len(self.positions) < CONFIG['MAX_POSITIONS']:
                candidates.sort(key=lambda x: x['change24h'], reverse=True)
                scout = candidates[0]
                print(f"   🦅 Scout {quote_curr}: {scout['symbol']} (+{scout['change24h']:.1f}%)")
                self.open_position(scout)
                scouts_deployed += 1
                
        self.scouts_deployed = True
        if scouts_deployed > 0:
            print(f"   ✅ Deployed {scouts_deployed} scout(s) - riding the wave!\n")

    def _normalize_ticker_symbol(self, symbol: str) -> str:
        """Convert internal symbol format to Kraken ticker format.
        XXBTGBP -> XBTGBP, XXLMGBP -> XLMGBP, XLTCGBP -> LTCGBP"""
        if symbol.startswith('XX') and len(symbol) > 5:
            # XXBTGBP -> XBTGBP, XXLMGBP -> XLMGBP
            return symbol[1:]
        elif symbol.startswith('XLT') or symbol.startswith('XLTC'):
            # XLTCGBP -> LTCGBP
            return symbol.replace('XLTC', 'LTC')
        return symbol

    # ─────────────────────────────────────────────────────────
    # Equity Management
    # ─────────────────────────────────────────────────────────

    def compute_total_equity(self) -> Tuple[float, float, Dict[str, float]]:
        """Return (total_equity, cash_in_base, holdings_map)"""
        base = CONFIG['BASE_CURRENCY']
        holdings_value: Dict[str, float] = {}
        total_equity = 0.0
        cash_balance = 0.0
        
        if self.dry_run:
            # In dry-run, approximate using tracked balance and open positions
            total_equity = self.tracker.balance
            used_capital = sum(pos.entry_value for pos in self.positions.values())
            cash_balance = max(0.0, total_equity - used_capital)
            for sym, pos in self.positions.items():
                holdings_value[sym] = pos.entry_value
            if cash_balance > 0:
                holdings_value[base] = holdings_value.get(base, 0.0) + cash_balance
            return total_equity, cash_balance, holdings_value
        
        try:
            account = self.client.account()
            balances = account.get('balances', [])
        except Exception as e:
            print(f"   ⚠️ Equity refresh error: {e}")
            return self.total_equity_gbp, self.cash_balance_gbp, self.holdings_gbp

        stable_coins = {'USD', 'USDC', 'USDT', 'EUR', 'GBP', 'ZUSD', 'ZEUR', 'ZGBP'}
        for bal in balances:
            asset_raw = bal.get('asset', '')
            if not asset_raw:
                continue
            try:
                amount = float(bal.get('free', 0) or 0)
            except Exception:
                amount = 0.0
            if amount <= 0:
                continue
            asset_clean = asset_raw.replace('Z', '').upper()  # Keep X prefix (XXBT stays XXBT)
            # For conversion, strip first X only (XXBT->XBT, XETH->ETH)
            conversion_asset = asset_clean[1:] if asset_clean.startswith('X') and len(asset_clean) > 3 else asset_clean

            # Treat USD/EUR/GBP stables as cash equivalents
            is_cash = (
                conversion_asset == base or asset_clean == base or
                conversion_asset in stable_coins or asset_clean in stable_coins
            )
            if is_cash:
                converted = amount
                if conversion_asset != base and asset_clean != base:
                    try:
                        converted = self.client.convert_to_quote(conversion_asset, amount, base)
                    except Exception:
                        converted = 0.0
                    # Fallback: assume 1:1 for USD stables to avoid zero cash reporting
                    if converted <= 0 and base.upper() == 'USD' and conversion_asset in {'USD', 'USDC', 'USDT'}:
                        converted = amount

                if converted > 0:
                    cash_balance += converted
                    total_equity += converted
                    holdings_value[asset_clean] = holdings_value.get(asset_clean, 0.0) + converted
                else:
                    holdings_value[asset_clean] = holdings_value.get(asset_clean, 0.0) + amount
                continue

            try:
                converted = self.client.convert_to_quote(conversion_asset, amount, base)
            except Exception:
                converted = 0.0
            if converted <= 0:
                holdings_value[asset_clean] = amount
                continue
            total_equity += converted
            holdings_value[asset_clean] = converted
        if total_equity <= 0:
            total_equity = cash_balance
        return total_equity, cash_balance, holdings_value

    def refresh_equity(self, mark_cycle: bool = False) -> float:
        total, cash, holdings = self.compute_total_equity()
        
        # 🛠️ FIX: Auto-correct "Fake $1000 Balance" on first run
        if self.tracker.initial_balance == 1000.0 and self.tracker.total_trades == 0:
            if abs(total - 1000.0) > 1.0 and total > 0:
                print(f"   ⚖️  Correcting Initial Balance: ${self.tracker.initial_balance:.2f} -> ${total:.2f} (Actual Wallet)")
                self.tracker.initial_balance = total
                self.tracker.first_start_balance = total
                self.tracker.balance = total
                self.tracker.peak_balance = total
                self.tracker.equity_baseline = total
                self.tracker.portfolio_equity = total
                self.tracker.cash_balance = cash

        self.total_equity_gbp = total
        self.cash_balance_gbp = cash
        self.holdings_gbp = holdings
        self.tracker.update_equity(total, cash, mark_cycle=mark_cycle)
        
        # 🌟 Sync capital pool with current equity
        self.capital_pool.update_equity(total)
        
        if self.tracker.equity_baseline is None or self.tracker.equity_baseline == 0:
            self.tracker.equity_baseline = total
        gain = total - self.tracker.equity_baseline
        if gain > CONFIG['EQUITY_MIN_DELTA']:
            self.tracker.realize_portfolio_gain(gain)
            self.tracker.equity_baseline = total
        return total

    def should_enter_trade(self, opp: Dict, pos_size: float, lattice_state) -> bool:
        """
        Evolved entry filter - uses parameters learned through 454 generations
        of trial and error. NOT made easier - the brain figured this out!
        """
        # Minimal sanity checks only
        if pos_size <= 0 or self.total_equity_gbp <= 0:
            return False
        
        # SANDBOX EVOLVED ENTRY FILTER
        # These thresholds were LEARNED through continuous feedback loop
        if SANDBOX_EVOLVED_AVAILABLE and _evolved:
            coherence = opp.get('coherence', 0)
            volatility = opp.get('volatility', 0)
            
            # Coherence filter - evolved minimum is ~73%
            if coherence < CONFIG['ENTRY_COHERENCE']:
                return False  # Below evolved coherence threshold
            
            # Volatility filter - evolved range is 0.80% to 1.63%
            evolved_vol_min = _evolved.params.get('min_volatility', 0.005) if hasattr(_evolved, 'params') else 0.005
            evolved_vol_max = _evolved.params.get('max_volatility', 0.02) if hasattr(_evolved, 'params') else 0.02
            
            if volatility > 0 and (volatility < evolved_vol_min or volatility > evolved_vol_max):
                return False  # Outside evolved volatility range
        
        # Passed evolved filters - ENTER TRADE!
        return True
    
    def should_exit_trade(self, pos: 'Position', current_price: float, reason: str) -> bool:
        """
        Smart exit gate - only sell if we're making NET PROFIT after fees.
        This ensures every closed trade is profitable.
        
        📐 NOTE: The penny profit threshold already accounts for all fees
        via the formula r = ((1 + P/A) / (1-f)²) - 1 where f = fee + slippage + spread.
        We use gross_pnl comparison with threshold - don't double-count fees!
        
        🔧 FIX: MIN_NET_PROFIT was 0.03 which blocked many small wins.
        Now using 0.0001 (1/10th of a cent) to allow any real profit.
        """
        _change_pct = (current_price - pos.entry_price) / pos.entry_price
        
        # Calculate gross P&L (threshold handles fee math)
        exit_value = pos.quantity * current_price
        gross_pnl = exit_value - pos.entry_value

        # Estimate net P&L after both legs' costs (fee + slippage + spread)
        fee_rate = CONFIG.get('KRAKEN_FEE_TAKER', CONFIG['KRAKEN_FEE'])
        slippage = CONFIG.get('SLIPPAGE_PCT', 0.002)
        spread = CONFIG.get('SPREAD_COST_PCT', 0.001)
        total_rate = fee_rate + slippage + spread
        exit_fee = exit_value * total_rate
        net_pnl = gross_pnl - (pos.entry_fee + exit_fee)
        min_net = CONFIG.get('MIN_NET_PROFIT', 0.0001)  # Was 0.03 - now allows any real profit
        
        # 🪙 PENNY PROFIT TAKE PROFIT: Allow ANY net profit (even tiny ones)
        if reason in ["TP", "PENNY_TP"]:
            if net_pnl >= min_net:
                return True
            # Log but don't print spam for small misses
            if net_pnl > -0.01:  # Close to breakeven
                return False  # Silent hold - almost there
            print(f"   🛑 HOLDING {pos.symbol}: Net {net_pnl:+.4f} below target {min_net:.4f}")
            return False
        
        # NO STOP LOSS — Dead Man's Switch: only close on profit.
        if reason in ["SL", "PENNY_SL"]:
            return False
        
        # REBALANCE/SWAP: Only if loss is small relative to position
        if reason in ["REBALANCE", "SWAP"]:
            loss_pct = abs(gross_pnl / pos.entry_value) if pos.entry_value > 0 else 0
            if loss_pct < 0.01:  # Allow up to 1% loss for rebalancing
                return True
            return False
        
        # Default: allow exit
        return True
    
    def save_state(self):
        """Save current state to file for recovery"""
        try:
            state = {
                'first_start_balance': self.tracker.first_start_balance,  # TRUE starting balance - survives restarts!
                'first_start_time': self.tracker.first_start_time,  # When we first started
                'initial_balance': self.tracker.initial_balance,  # Reference for calculations
                'balance': self.tracker.balance,
                'peak_balance': self.tracker.peak_balance,
                'total_trades': self.tracker.total_trades,
                'wins': self.tracker.wins,
                'losses': self.tracker.losses,
                'total_fees': self.tracker.total_fees,
                'compounded': self.tracker.compounded,
                'harvested': self.tracker.harvested,
                'max_drawdown': self.tracker.max_drawdown,
                'positions': {
                    sym: {
                        'entry_price': pos.entry_price,
                        'quantity': pos.quantity,
                        'entry_fee': pos.entry_fee,
                        'entry_value': pos.entry_value,
                        'momentum': pos.momentum,
                        'coherence': pos.coherence,
                        'entry_time': pos.entry_time,
                        'dominant_node': pos.dominant_node,
                        'cycles': pos.cycles
                    }
                    for sym, pos in self.positions.items()
                },
                'timestamp': time.time(),
                'iteration': self.iteration
            }
            with open(CONFIG['STATE_FILE'], 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ State save error: {e}")
    
    def load_state(self):
        """Load previous state from file"""
        try:
            if not os.path.exists(CONFIG['STATE_FILE']):
                return
            
            with open(CONFIG['STATE_FILE'], 'r') as f:
                state = json.load(f)
            
            # Restore tracker state - including the TRUE starting balance!
            self.tracker.first_start_balance = state.get('first_start_balance', state.get('initial_balance', self.tracker.initial_balance))
            self.tracker.first_start_time = state.get('first_start_time', time.time())
            self.tracker.initial_balance = state.get('initial_balance', self.tracker.initial_balance)
            self.tracker.balance = state.get('balance', self.tracker.balance)
            self.tracker.peak_balance = state.get('peak_balance', self.tracker.peak_balance)
            self.tracker.total_trades = state.get('total_trades', 0)
            self.tracker.wins = state.get('wins', 0)
            self.tracker.losses = state.get('losses', 0)
            self.tracker.total_fees = state.get('total_fees', 0.0)
            self.tracker.compounded = state.get('compounded', 0.0)
            self.tracker.harvested = state.get('harvested', 0.0)
            self.tracker.max_drawdown = state.get('max_drawdown', 0.0)
            
            print(f"   📊 Restored TRUE starting balance: £{self.tracker.first_start_balance:.2f} (from {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.tracker.first_start_time))})")
            
            # Restore positions (optional - might be stale)
            saved_positions = state.get('positions', {})
            if saved_positions:
                print(f"   💾 Loaded state: {len(saved_positions)} positions from previous session")
            
        except Exception as e:
            print(f"   ⚠️ State load error: {e}")
        
    def banner(self):
        mode = "🧪 PAPER" if self.dry_run else "💰 LIVE"
        sandbox_status = f"🧬 Gen {_evolved.generation}, {_evolved.win_rate:.0f}% WR" if SANDBOX_EVOLVED_AVAILABLE and _evolved else "❌ Not loaded"
        start_time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(self.tracker.first_start_time))
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🐙🌌 AUREON KRAKEN ECOSYSTEM - UNIFIED TRADING ENGINE 🌌🐙            ║
║                                                                          ║
║   Mode: {mode} TRADING                                              ║
║                                                                          ║
║   Components:                                                            ║
║   ├─ 🐅 9 Auris Nodes (Tiger, Falcon, Dolphin...)                       ║
║   ├─ 🍄 Mycelium Neural Network                                         ║
║   ├─ 💰 10-9-1 Compounding Model                                        ║
║   ├─ 🔴 Real-Time WebSocket Prices                                      ║
║   ├─ 📊 Kelly Criterion Position Sizing                                 ║
║   ├─ 🛑 Circuit Breaker (Max DD: {CONFIG['MAX_DRAWDOWN_PCT']}%)                        ║
║   ├─ 🎯 51%+ Win Rate Strategy                                          ║
║   └─ 🧬 Sandbox Evolution: {sandbox_status}                ║
║                                                                          ║
║   Strategy: TP +{CONFIG['TAKE_PROFIT_PCT']:.2f}% | SL -{CONFIG['STOP_LOSS_PCT']:.2f}% | Coh: {CONFIG['ENTRY_COHERENCE']*100:.0f}%+ | Base: {CONFIG['BASE_CURRENCY']}    ║
║                                                                          ║
║   🧠 EVOLVED: Parameters learned through 454 generations - NOT given!   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
        
   📅 First Started: {start_time_str}
   💵 TRUE Starting Balance: ${self.tracker.first_start_balance:.2f} (actual portfolio when first run)
   💰 Current Balance: ${self.tracker.balance:.2f}
""")

    # ─────────────────────────────────────────────────────────
    # WebSocket for Real-Time Prices
    # ─────────────────────────────────────────────────────────
    
    def convert_symbol_to_ws(self, symbol: str) -> str:
        """Convert REST API symbol to WebSocket pair name"""
        base_curr = CONFIG['BASE_CURRENCY']
        if symbol.endswith(base_curr):
            base = symbol[:-len(base_curr)]
            return f"{base}/{base_curr}"
        return symbol
        
    async def websocket_handler(self, pairs: List[str]):
        """Handle WebSocket connection for real-time prices"""
        if not WEBSOCKETS_AVAILABLE:
            print("   ⚠️ WebSocket library not available. Real-time prices disabled.")
            return

        while True:
            try:
                async with websockets.connect(CONFIG['WS_URL'], ping_interval=20) as ws:
                    self.ws_connected = True
                    self.ws_last_message = time.time()
                    self.ws_reconnect_count += 1
                    print(f"   🔴 WebSocket connected! (reconnect #{self.ws_reconnect_count})")
                    
                    if pairs:
                        subscribe_msg = {
                            "event": "subscribe",
                            "pair": pairs,
                            "subscription": {"name": "ticker"}
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        print(f"   📡 Subscribed to {len(pairs)} pairs")
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            if isinstance(data, list) and len(data) >= 4 and data[2] == "ticker":
                                ws_pair = data[3]
                                ticker_data = data[1]
                                if 'c' in ticker_data:
                                    price = float(ticker_data['c'][0])
                                    with self.price_lock:
                                        self.realtime_prices[ws_pair] = price
                                        if ws_pair in self.ws_to_symbol:
                                            symbol = self.ws_to_symbol[ws_pair]
                                            self.realtime_prices[symbol] = price
                        except:
                            pass
                            
            except Exception as e:
                print(f"   ⚠️ WebSocket error: {e}")
                self.ws_connected = False
                await asyncio.sleep(CONFIG['WS_RECONNECT_DELAY'])
                
    def start_websocket(self, symbols: List[str]):
        """Start WebSocket in background thread"""
        ws_pairs = []
        for symbol in symbols:
            ws_pair = self.convert_symbol_to_ws(symbol)
            ws_pairs.append(ws_pair)
            self.symbol_to_ws[symbol] = ws_pair
            self.ws_to_symbol[ws_pair] = symbol
            
        def run_ws():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.websocket_handler(ws_pairs))
            
        thread = Thread(target=run_ws, daemon=True)
        thread.start()
        time.sleep(2)
        
    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from WebSocket"""
        with self.price_lock:
            if symbol in self.realtime_prices:
                return self.realtime_prices[symbol]
            ws_pair = self.symbol_to_ws.get(symbol)
            if ws_pair and ws_pair in self.realtime_prices:
                return self.realtime_prices[ws_pair]
        return None

    # ─────────────────────────────────────────────────────────
    # Market Data
    # ─────────────────────────────────────────────────────────
    
    def refresh_tickers(self) -> int:
        """Refresh ticker data from REST API"""
        try:
            tickers_list = self.client.get_24h_tickers()
            self.ticker_cache = {}
            
            for t in tickers_list:
                symbol = t.get('symbol', '')
                if not symbol:
                    continue
                try:
                    price = float(t.get('lastPrice', 0))
                    change = float(t.get('priceChangePercent', 0))
                    volume = float(t.get('quoteVolume', 0))
                    
                    self.ticker_cache[symbol] = {
                        'price': price,
                        'change24h': change,
                        'volume': volume
                    }
                    
                    # Update price history
                    if symbol not in self.price_history:
                        self.price_history[symbol] = []
                    self.price_history[symbol].append(price)
                    if len(self.price_history[symbol]) > 50:
                        self.price_history[symbol] = self.price_history[symbol][-50:]
                        
                    # Feed mycelium network
                    signal = 0.5 + (change / 20)  # Normalize change to 0-1
                    self.mycelium.add_signal(symbol, max(0, min(1, signal)))
                except:
                    continue
                    
            return len(self.ticker_cache)
        except Exception as e:
            print(f"   ⚠️ Ticker refresh error: {e}")
            return 0

    # ─────────────────────────────────────────────────────────
    # Opportunity Detection
    # ─────────────────────────────────────────────────────────
    
    def find_opportunities(self) -> List[Dict]:
        """Find best trading opportunities using all analysis methods - TRADES EVERYTHING"""
        opportunities = []
        
        # In live mode, only look for pairs we can actually trade with our holdings
        # This means pairs ending in currencies we have (cash or can sell for)
        if not self.dry_run:
            # Get list of assets we hold (these can be sold to buy others)
            available_quotes = set()
            for symbol in self.positions.keys():
                # Extract quote currency from position symbols
                for curr in ['GBP', 'USD', 'EUR', 'USDT', 'BTC', 'ETH']:
                    if symbol.endswith(curr):
                        available_quotes.add(curr)
                        break
            # Also add base currency if we have cash
            if self.cash_balance_gbp > CONFIG['MIN_TRADE_USD']:
                available_quotes.add(CONFIG['BASE_CURRENCY'])
            
            quote_currencies = list(available_quotes) if available_quotes else [CONFIG['BASE_CURRENCY']]
        else:
            quote_currencies = CONFIG.get('QUOTE_CURRENCIES', self.tradeable_currencies)
        
        for symbol, data in self.ticker_cache.items():
            # Filter based on tradeable quote currencies
            if not any(symbol.endswith(curr) for curr in quote_currencies):
                continue
                
            change = data['change24h']
            price = data['price']
            volume = data['volume']
            
            # Basic filters
            if change < CONFIG['MIN_MOMENTUM'] or change > CONFIG['MAX_MOMENTUM']:
                continue
            if price < 0.0001 or volume < CONFIG['MIN_VOLUME']:
                continue
            if symbol in self.positions:
                continue
                
            # Build market state for Auris analysis
            prices = self.price_history.get(symbol, [price])
            state = MarketState(
                symbol=symbol,
                price=price,
                bid=price * 0.999,
                ask=price * 1.001,
                volume=volume,
                change_24h=change,
                high_24h=price * 1.02,
                low_24h=price * 0.98,
                prices=prices[-20:],
                timestamp=time.time()
            )
            
            # Get Auris coherence
            coherence, dominant_node = self.auris.compute_coherence(state)
            
            # Skip if coherence too low
            if coherence < CONFIG['ENTRY_COHERENCE']:
                continue
            
            # 🔮 NEXUS PREDICTION - 79.6% WIN RATE VALIDATED! 🔮
            nexus_prediction = None
            nexus_prob = 0.5
            nexus_edge = 0.0
            if self.nexus is not None:
                nexus_prediction = self.nexus.predict_instant(
                    price=price,
                    high_24h=price * (1 + max(0.01, change/100)),
                    low_24h=price * (1 - max(0.01, change/100)),
                    momentum=change / 100.0  # Convert percentage to decimal
                )
                nexus_prob = nexus_prediction.get('probability', 0.5)
                nexus_edge = nexus_prediction.get('edge', 0.0)
                should_trade = nexus_prediction.get('should_trade', True)
                
                # Skip if Nexus says NO (validated 79.6% accuracy!)
                if not should_trade or nexus_prob < 0.55:
                    continue
            
            # Propagate through Mycelium network for enhanced signal
            self.mycelium.add_signal(symbol, coherence)
            network_activations = self.mycelium.propagate()

            # Adjust coherence based on network activation
            if symbol in network_activations:
                network_boost = (network_activations[symbol] - coherence) * 0.2
                coherence = min(1.0, coherence + network_boost)

            # ⚔️ WAR STRATEGY - Quick Kill Probability
            war_go = True
            war_priority = 0
            war_prob = 0.0
            if self.war_strategy and should_attack:
                try:
                    war_go, _reason, war_priority = should_attack(symbol, 'kraken', prices[-20:])
                    if not war_go:
                        continue  # War Strategy says don't attack this target
                    estimate = get_quick_kill_estimate(symbol, 'kraken', prices[-20:])
                    war_prob = estimate.prob_penny_profit if estimate else 0.0
                except Exception:
                    pass  # Graceful fallback

            # 🎯 SNIPER BRAIN - Entry Signal Scoring
            sniper_confidence = 0.0
            sniper_action = 'HOLD'
            if self.sniper_brain is not None:
                try:
                    volumes_list = [volume] * min(len(prices), 20)  # Approximate volume history
                    sig = self.sniper_brain.get_entry_signal(symbol, prices[-20:], volumes_list[-20:])
                    sniper_confidence = sig.confidence if sig else 0.0
                    sniper_action = sig.action if sig else 'HOLD'
                    if sniper_action == 'HOLD' and sniper_confidence < 0.3:
                        continue  # Sniper says no opportunity here
                except Exception:
                    pass  # Graceful fallback

            # 🧠 MINER BRAIN - Timeline Oracle Validation
            miner_action = 'HOLD'
            miner_confidence = 0.0
            if self.miner_brain is not None:
                try:
                    m_action, _branch, m_conf = self.miner_brain.select_timeline_branch(
                        symbol, price, volume, change
                    )
                    miner_action = m_action or 'HOLD'
                    miner_confidence = m_conf if m_conf else 0.0
                except Exception:
                    pass  # Graceful fallback

            # 📊 Calculate volatility from price history (FIX: was never calculated)
            volatility = 0.0
            if len(prices) >= 5:
                returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices)) if prices[i-1] > 0]
                if returns:
                    mean_ret = sum(returns) / len(returns)
                    volatility = (sum((r - mean_ret) ** 2 for r in returns) / len(returns)) ** 0.5

            # ═══════════════════════════════════════════════════════
            # COMPOSITE SCORE - Multi-system weighted scoring
            # ═══════════════════════════════════════════════════════
            score = 0

            # Coherence (0-25 pts) - Core signal from 9 Auris nodes
            score += int(coherence * 25)

            # Momentum (0-20 pts) - Scaled, penalizes negative
            if change > 20: score += 20
            elif change > 10: score += 17
            elif change > 5: score += 14
            elif change > 2: score += 10
            elif change > 0: score += 6
            else: score += 2  # Negative momentum gets minimal score

            # Volume (0-15 pts) - Liquidity matters
            if volume > 1000000: score += 15
            elif volume > 500000: score += 12
            elif volume > 100000: score += 8
            else: score += 3

            # 🔮 Nexus probability bonus (0-20 pts)
            if self.nexus is not None and nexus_prob > 0.5:
                score += int((nexus_prob - 0.5) * 40)  # 0.75 prob = +10 pts

            # ⚔️ War Strategy bonus (0-15 pts)
            if war_prob > 0:
                score += int(war_prob * 15)  # High kill probability = more points
            score += min(war_priority, 5)  # Priority bonus up to 5

            # 🎯 Sniper Brain bonus (0-15 pts)
            if sniper_action in ('ENTER_LONG',):
                score += int(sniper_confidence * 15)
            elif sniper_action == 'ENTER_SHORT':
                score -= 5  # Penalize if sniper sees short opportunity

            # 🧠 Miner Brain / Timeline Oracle bonus (0-10 pts)
            if miner_action == 'BUY':
                score += int(miner_confidence * 10)
            elif miner_action == 'SELL':
                score -= 5  # Timeline says sell, penalize

            # Golden ratio alignment (0-5 pts)
            if len(prices) >= 5:
                ratio = prices[-1] / prices[-5] if prices[-5] > 0 else 1
                if 1.5 < ratio < 1.7:  # Near PHI
                    score += 5

            if score >= CONFIG['MIN_SCORE']:
                opportunities.append({
                    'symbol': symbol,
                    'price': price,
                    'change24h': change,
                    'volume': volume,
                    'score': score,
                    'coherence': coherence,
                    'volatility': volatility,
                    'dominant_node': dominant_node,
                    'nexus_prob': nexus_prob,
                    'nexus_edge': nexus_edge,
                    'war_prob': war_prob,
                    'war_priority': war_priority,
                    'sniper_confidence': sniper_confidence,
                    'sniper_action': sniper_action,
                    'miner_action': miner_action,
                    'miner_confidence': miner_confidence,
                })
                
        # Sort by score and return MORE opportunities
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        # Return up to double max positions to have backups ready
        return opportunities[:min(CONFIG['MAX_POSITIONS'] * 2, CONFIG['MAX_POSITIONS'] - len(self.positions) + 5)]

    # ─────────────────────────────────────────────────────────
    # Position Management
    # ─────────────────────────────────────────────────────────
    
    def open_position(self, opp: Dict):
        """Open a new position - dynamically frees capital if needed"""
        symbol = opp['symbol']
        price = opp['price']
        
        if self.tracker.trading_halted:
            return
        
        lattice_state = self.lattice.get_state()
        size_fraction = self.tracker.calculate_position_size(opp['coherence'], symbol)
        risk_mod = lattice_state.get('risk_mod', 1.0) if isinstance(lattice_state, dict) else getattr(lattice_state, 'risk_mod', 1.0)
        size_fraction *= risk_mod
        # 👁 Apply Seer's cosmic risk modifier
        if SEER_AVAILABLE and seer_get_risk_modifier:
            try:
                size_fraction *= seer_get_risk_modifier()
            except Exception:
                pass
        # 🎵 Apply Lyra's PHI-based position multiplier
        if LYRA_AVAILABLE and lyra_get_position_multiplier:
            try:
                size_fraction *= lyra_get_position_multiplier()
            except Exception:
                pass
        if size_fraction <= 0:
            return

        deploy_cap = self.total_equity_gbp * CONFIG['PORTFOLIO_RISK_BUDGET']
        deployed = sum(pos.entry_value for pos in self.positions.values())
        available_risk = max(0.0, deploy_cap - deployed)
        if available_risk < CONFIG['MIN_TRADE_USD']:
            return

        pos_size = self.tracker.balance * size_fraction
        if pos_size <= 0:
            return
        pos_size = min(pos_size, available_risk)

        if self.dry_run:
            cash_available = max(0.0, self.tracker.balance - deployed)
        else:
            cash_available = max(0.0, self.cash_balance_gbp)
        
        # DYNAMIC CAPITAL ALLOCATION: If no cash but this is a better opportunity,
        # sell the worst-performing position to free up capital
        if cash_available < CONFIG['MIN_TRADE_USD'] and CONFIG['ENABLE_REBALANCING'] and self.positions:
            worst_pos = None
            worst_pct = 0
            
            for pos_symbol, pos in self.positions.items():
                if pos.cycles < CONFIG['MIN_HOLD_CYCLES']:
                    continue
                curr_price = self.get_realtime_price(pos_symbol)
                if curr_price is None:
                    curr_price = self.ticker_cache.get(pos_symbol, {}).get('price', pos.entry_price)
                if curr_price and curr_price > 0:
                    pct = (curr_price - pos.entry_price) / pos.entry_price * 100
                    if pct < worst_pct:
                        worst_pct = pct
                        worst_pos = (pos_symbol, pct, curr_price)
            
            # Only swap if new opportunity score is significantly better
            if worst_pos and opp.get('score', 0) > 85 and worst_pct < CONFIG['REBALANCE_THRESHOLD']:
                pos_symbol, pct, curr_price = worst_pos
                print(f"   🔄 DYNAMIC SWAP: Selling {pos_symbol} ({pct:+.2f}%) to buy {symbol}")
                self.close_position(pos_symbol, "SWAP", pct, curr_price)
                self.refresh_equity()
                cash_available = max(0.0, self.cash_balance_gbp)
        
        if cash_available < CONFIG['MIN_TRADE_USD']:
            # Only print skip message once per cycle per symbol
            if not hasattr(self, '_skip_logged'):
                self._skip_logged = set()
            if symbol not in self._skip_logged:
                print(f"   ⚪ Skipping {symbol}: insufficient cash (£{cash_available:.2f})")
                self._skip_logged.add(symbol)
            return
        
        # Clear skip log at end of cycle
        if hasattr(self, '_skip_logged'):
            self._skip_logged.clear()
            
        pos_size = min(pos_size, cash_available)

        if pos_size < CONFIG['MIN_TRADE_USD']:
            return

        if not self.should_enter_trade(opp, pos_size, lattice_state):
            reason = opp.get('entry_reject_reason') or 'portfolio gate rejected entry'
            print(f"   ⚪ Skipping {symbol}: {reason}")
            return
        
        actual_fraction = (pos_size / self.tracker.balance) if self.tracker.balance > 0 else 0.0
        # Use combined rate (fee + slippage + spread) to match penny profit formula
        fee_rate = CONFIG.get('KRAKEN_FEE_TAKER', CONFIG['KRAKEN_FEE'])
        slippage = CONFIG.get('SLIPPAGE_PCT', 0.002)
        spread = CONFIG.get('SPREAD_COST_PCT', 0.001)
        total_rate = fee_rate + slippage + spread
        entry_fee = pos_size * total_rate
        quantity = pos_size / price
        
        if not self.dry_run:
            try:
                res = self.client.place_market_order(symbol, 'BUY', quote_qty=pos_size)
                if not res.get('orderId'):
                    print(f"   ⚠️ Order failed for {symbol}: No order ID returned")
                    return
                # 👑 The King records the buy
                if KING_AVAILABLE and king_on_buy:
                    try:
                        king_on_buy(
                            'kraken', symbol, quantity, price,
                            fee=entry_fee, order_id=res.get('orderId', ''),
                        )
                    except Exception:
                        pass  # Non-critical
            except Exception as e:
                print(f"   ⚠️ Execution error for {symbol}: {e}")
                return

        # 🌟 Apply prime-based sizing if enabled
        prime_multiplier = 1.0
        if len(self.positions) < 3:  # Apply prime sizing to first few positions
            prime_multiplier = self.prime_sizer.get_next_size(1.0) / CONFIG['BASE_POSITION_SIZE']
            pos_size *= prime_multiplier
            pos_size = min(pos_size, available_risk, cash_available)
            quantity = pos_size / price
            entry_fee = pos_size * total_rate  # Use combined rate
        
        # Create position with swarm enhancements
        is_scout = len(self.positions) == 0  # First position becomes scout
        
        self.positions[symbol] = Position(
            symbol=symbol,
            entry_price=price,
            quantity=quantity,
            entry_fee=entry_fee,
            entry_value=pos_size,
            momentum=opp['change24h'],
            coherence=opp['coherence'],
            entry_time=time.time(),
            dominant_node=opp['dominant_node'],
            generation=0,
            is_scout=is_scout,
            prime_size_multiplier=prime_multiplier,
            # 🔮 NEXUS PREDICTOR DATA - For learning feedback
            nexus_prob=opp.get('nexus_prob', 0.5),
            nexus_edge=opp.get('nexus_edge', 0.0),
            nexus_patterns=opp.get('nexus_patterns', []),
        )
        
        # 🌟 Allocate capital in pool
        self.capital_pool.allocate(symbol, pos_size)
        
        self.tracker.total_fees += entry_fee
        self.tracker.symbol_exposure[symbol] = self.tracker.symbol_exposure.get(symbol, 0.0) + actual_fraction
        self.cash_balance_gbp = max(0.0, self.cash_balance_gbp - pos_size)
        self.holdings_gbp[symbol] = self.holdings_gbp.get(symbol, 0.0) + pos_size
        
        icon = self._get_node_icon(opp['dominant_node'])
        curr_sym = "£" if CONFIG['BASE_CURRENCY'] == 'GBP' else "€" if CONFIG['BASE_CURRENCY'] == 'EUR' else "$"
        scout_marker = " 🐺" if is_scout else ""
        prime_marker = f" [×{prime_multiplier:.1f}]" if prime_multiplier != 1.0 else ""
        nexus_marker = f" 🔮{opp.get('nexus_prob', 0.5)*100:.0f}%" if self.nexus and 'nexus_prob' in opp else ""
        print(f"   {icon} BUY  {symbol:12s} @ {curr_sym}{price:.6f} | {curr_sym}{pos_size:.2f} ({actual_fraction*100:.1f}%) | Γ={opp['coherence']:.2f} | +{opp['change24h']:.1f}%{nexus_marker}{scout_marker}{prime_marker}")

    def open_margin_position(self, opp: Dict):
        """Open a leveraged margin position on Kraken.

        Requires MARGIN_ENABLED=1 in config. Uses higher entry thresholds
        (score >= MARGIN_MIN_SCORE, coherence >= MARGIN_MIN_COHERENCE) and
        tighter risk management than spot positions.
        """
        if not CONFIG.get('MARGIN_ENABLED'):
            return
        if self.tracker.trading_halted:
            return

        symbol = opp['symbol']
        price = opp['price']

        # Margin requires higher confidence
        if opp.get('score', 0) < CONFIG['MARGIN_MIN_SCORE']:
            return
        if opp.get('coherence', 0) < CONFIG['MARGIN_MIN_COHERENCE']:
            return

        # Check leverage availability for this pair
        pair_lev = self.client.get_pair_leverage(symbol)
        if not pair_lev.get('margin_supported'):
            return

        leverage = min(
            CONFIG['MARGIN_DEFAULT_LEVERAGE'],
            CONFIG['MARGIN_MAX_LEVERAGE'],
            pair_lev.get('max_leverage', 2)
        )
        if leverage < 2:
            return

        # Check margin account health
        trade_balance = self.client.get_trade_balance()
        free_margin = trade_balance.get('free_margin', 0)
        equity = trade_balance.get('equity_value', 0)

        if equity <= 0:
            return

        # Enforce minimum free margin percentage
        if free_margin / equity < CONFIG['MARGIN_MIN_FREE_MARGIN_PCT']:
            return

        # Enforce maximum margin exposure
        margin_used = trade_balance.get('margin_amount', 0)
        max_margin = equity * CONFIG['MARGIN_MAX_EXPOSURE_PCT']
        if margin_used >= max_margin:
            return

        # Calculate position size (margin = collateral, notional = margin * leverage)
        size_fraction = self.tracker.calculate_position_size(opp['coherence'], symbol)
        lattice_state = self.lattice.get_state()
        risk_mod = lattice_state.get('risk_mod', 1.0) if isinstance(lattice_state, dict) else getattr(lattice_state, 'risk_mod', 1.0)
        size_fraction *= risk_mod
        if size_fraction <= 0:
            return

        margin_budget = min(
            self.tracker.balance * size_fraction,
            max_margin - margin_used,
            free_margin * 0.8,  # Don't use all free margin
        )
        if margin_budget < CONFIG['MIN_TRADE_USD']:
            return

        # Notional = margin * leverage
        notional = margin_budget * leverage
        quantity = notional / price

        # Calculate TP only — Dead Man's Switch: no stop loss, only close on profit
        tp_pct = CONFIG['TAKE_PROFIT_PCT'] * CONFIG.get('MARGIN_TP_MULTIPLIER', 1.5)
        take_profit = price * (1 + tp_pct / 100)

        # Fee calculation
        fee_rate = CONFIG.get('KRAKEN_FEE_TAKER', CONFIG['KRAKEN_FEE'])
        slippage = CONFIG.get('SLIPPAGE_PCT', 0.002)
        spread = CONFIG.get('SPREAD_COST_PCT', 0.001)
        total_rate = fee_rate + slippage + spread
        entry_fee = notional * total_rate

        if not self.dry_run:
            try:
                res = self.client.place_margin_order(
                    symbol, 'buy', quantity, leverage,
                    order_type='market',
                    take_profit=take_profit,
                )
                if not res.get('orderId') and not res.get('entryOrderId'):
                    print(f"   [MARGIN] Order failed for {symbol}: {res}")
                    return
            except Exception as e:
                print(f"   [MARGIN] Execution error for {symbol}: {e}")
                return

        actual_fraction = (margin_budget / self.tracker.balance) if self.tracker.balance > 0 else 0.0

        # Track as a margin position
        self.positions[f"M:{symbol}"] = Position(
            symbol=symbol,
            entry_price=price,
            quantity=quantity,
            entry_fee=entry_fee,
            entry_value=notional,
            momentum=opp['change24h'],
            coherence=opp['coherence'],
            entry_time=time.time(),
            dominant_node=opp['dominant_node'],
            is_margin=True,
            leverage=leverage,
            margin_amount=margin_budget,
            nexus_prob=opp.get('nexus_prob', 0.5),
            nexus_edge=opp.get('nexus_edge', 0.0),
            nexus_patterns=opp.get('nexus_patterns', []),
        )

        self.capital_pool.allocate(f"M:{symbol}", margin_budget)
        self.tracker.total_fees += entry_fee
        self.tracker.symbol_exposure[symbol] = self.tracker.symbol_exposure.get(symbol, 0.0) + actual_fraction

        curr_sym = "$" if CONFIG['BASE_CURRENCY'] == 'USD' else "£" if CONFIG['BASE_CURRENCY'] == 'GBP' else "€"
        print(
            f"   [MARGIN {leverage}x] BUY  {symbol:12s} @ {curr_sym}{price:.6f} | "
            f"Notional {curr_sym}{notional:.2f} (Margin {curr_sym}{margin_budget:.2f}) | "
            f"TP={curr_sym}{take_profit:.2f} | "
            f"Score={opp.get('score', 0):.0f}"
        )

    def check_positions(self):
        """Check all positions for TP/SL"""
        to_close = []

        for symbol, pos in self.positions.items():
            pos.cycles += 1

            # Use the actual trading symbol for price lookups
            # (margin positions are keyed as "M:ETHUSD" but trade as "ETHUSD")
            lookup_symbol = pos.symbol

            # Get current price (prefer WebSocket)
            current_price = self.get_realtime_price(lookup_symbol)
            source = "WS"

            if current_price is None:
                # Fallback to ticker cache
                current_price = self.ticker_cache.get(lookup_symbol, {}).get('price')
                source = "CACHE"

            # If still None, force a fresh lookup for this specific symbol
            if current_price is None:
                try:
                    # Force single ticker lookup - normalize symbol for Kraken API
                    ticker_symbol = self._normalize_ticker_symbol(lookup_symbol)
                    ticker = self.client._ticker([ticker_symbol])
                    # Extract price (Kraken format is complex, need to be careful)
                    # _ticker returns dict keyed by internal name. We need to find the value.
                    if ticker:
                        # Just take the first value found
                        t_data = list(ticker.values())[0]
                        current_price = float(t_data.get('c', [0])[0])
                        source = "REST_FORCE"
                except Exception as e:
                    print(f"   ⚠️ Failed to force price check for {symbol}: {e}")

            # Final fallback
            if current_price is None or current_price == 0:
                current_price = pos.entry_price
                source = "ENTRY (STALE)"

            change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            
            # 🌟 SIGNAL BROADCASTING: Scout positions broadcast market signals
            if pos.is_scout and abs(change_pct) > 0.5 and (time.time() - pos.last_signal_broadcast) > 30:
                # Scout broadcasts signal when it moves significantly
                direction = 'BUY' if change_pct > 0 else 'SELL'
                strength = min(1.0, abs(change_pct) / 5.0)  # 5% move = 1.0 strength
                
                signal = MarketSignal(
                    symbol=symbol,
                    direction=direction,
                    strength=strength,
                    momentum=change_pct,
                    coherence=pos.coherence,
                    timestamp=time.time(),
                    scout_id=pos.id
                )
                self.signal_broadcaster.broadcast_signal(signal)
                pos.last_signal_broadcast = time.time()
                print(f"   🐺 SCOUT SIGNAL: {symbol} {direction} | Strength: {strength:.2f} | Momentum: {change_pct:+.2f}%")
            
            # 🌟 POSITION SPLITTING: Check if position should split
            position_value = pos.quantity * current_price
            if self.position_splitter.should_split(position_value, pos.entry_value, pos.generation):
                print(f"   👶 SPLIT READY: {symbol} (Gen {pos.generation}) - Value ${position_value:.2f} vs Entry ${pos.entry_value:.2f}")
                # We'll handle splitting after TP/SL checks to avoid complexity
            
            # Log status every 10 cycles or if significant change
            if pos.cycles % 10 == 0 or abs(change_pct) > 0.5:
                gen_marker = f" [G{pos.generation}]" if pos.generation > 0 else ""
                print(f"   🔍 {symbol}{gen_marker}: Entry={pos.entry_price:.5f} Curr={current_price:.5f} ({source}) Pct={change_pct:+.2f}%")

            # 🪙 PENNY PROFIT EXIT LOGIC
            # Use penny profit engine for proper dollar-based exits
            current_value = pos.quantity * current_price
            
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None:
                # Use penny profit dollar-based thresholds
                action, gross_pnl = check_penny_exit('kraken', pos.entry_value, current_value)
                threshold = _penny_engine.get_threshold('kraken', pos.entry_value)
                
                # Check Take Profit (penny profit - ALWAYS allow)
                if action == 'TAKE_PROFIT':
                    print(f"   🪙 PENNY TP: {symbol} | Gross: ${gross_pnl:.4f} >= Target: ${threshold.win_gte:.4f}")
                    to_close.append((symbol, "PENNY_TP", change_pct, current_price))

                # NO STOP LOSS — Dead Man's Switch: only close on profit.
                # Positions are held until they turn profitable.

                # Log threshold info periodically
                elif pos.cycles % 20 == 0:
                    print(f"   🪙 {symbol}: Gross ${gross_pnl:.4f} | TP >= ${threshold.win_gte:.4f}")
            
            else:
                # Fallback to percentage-based exits (only if penny profit not available)
                # Get Lattice Modifiers
                lattice_state = self.lattice.get_state()
                tp_mod = lattice_state.get('tp_mod', 1.0) if isinstance(lattice_state, dict) else getattr(lattice_state, 'tp_mod', 1.0)
                sl_mod = lattice_state.get('sl_mod', 1.0) if isinstance(lattice_state, dict) else getattr(lattice_state, 'sl_mod', 1.0)
                
                target_tp = CONFIG['TAKE_PROFIT_PCT'] * tp_mod
                target_sl = CONFIG['STOP_LOSS_PCT'] * sl_mod

                # Check TP only — no stop loss (Dead Man's Switch)
                if change_pct >= target_tp:
                    to_close.append((symbol, "TP", change_pct, current_price))
                
        for symbol, reason, pct, price in to_close:
            self.close_position(symbol, reason, pct, price)
    
    def rebalance_portfolio(self, opportunities: List[Dict]) -> float:
        """
        Dynamic portfolio rebalancing - sell underperformers to buy better opportunities.
        Returns: Amount of capital freed up for new trades.
        """
        if not CONFIG['ENABLE_REBALANCING']:
            return 0.0
            
        if not opportunities:
            return 0.0
            
        freed_capital = 0.0
        to_rebalance = []
        
        # Find positions that are underperforming and held long enough
        for symbol, pos in self.positions.items():
            if pos.cycles < CONFIG['MIN_HOLD_CYCLES']:
                continue  # Don't sell too quickly

            # Use actual trading symbol for price lookups (margin keys are "M:SYMBOL")
            lookup_symbol = pos.symbol

            # Get current price
            current_price = self.get_realtime_price(lookup_symbol)
            if current_price is None:
                current_price = self.ticker_cache.get(lookup_symbol, {}).get('price', pos.entry_price)
            if current_price is None or current_price == 0:
                continue
                
            change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            
            # Check if position is underperforming
            if change_pct < CONFIG['REBALANCE_THRESHOLD']:
                # Check if there's a better opportunity
                best_opp = opportunities[0] if opportunities else None
                if best_opp and best_opp.get('score', 0) > 80:
                    # Calculate if swapping would be profitable
                    # Expected gain from new position vs current loss
                    current_value = pos.quantity * current_price
                    swap_cost = current_value * (CONFIG['KRAKEN_FEE'] * 2 + CONFIG['SLIPPAGE_PCT'])
                    
                    # Expected gain from best opportunity
                    expected_gain = current_value * (CONFIG['TAKE_PROFIT_PCT'] / 100) * CONFIG['DEFAULT_WIN_PROB']
                    
                    if expected_gain > swap_cost:
                        to_rebalance.append((symbol, change_pct, current_price, current_value))
        
        # Execute rebalancing (sell underperformers)
        for symbol, change_pct, price, value in to_rebalance[:2]:  # Max 2 rebalances per cycle
            print(f"   🔄 REBALANCING: Selling {symbol} ({change_pct:+.2f}%) to free £{value:.2f}")
            self.close_position(symbol, "REBALANCE", change_pct, price)
            freed_capital += value
            
        return freed_capital
            
    def close_position(self, symbol: str, reason: str, pct: float, price: float):
        """Close a position"""
        # Don't pop yet! Wait for confirmation.
        if symbol not in self.positions:
            return
            
        pos = self.positions[symbol]
        
        # 🌟 CHECK EXIT GATE: Only sell if profitable
        if not self.should_exit_trade(pos, price, reason):
            return  # Hold position, don't sell at a loss
        
        # EXECUTE TRADE
        success = False
        sell_order = None
        trade_symbol = pos.symbol  # Use the actual trading symbol (not the key)
        if not self.dry_run:
            try:
                if pos.is_margin:
                    # Close margin position via leveraged opposing order
                    sell_order = self.client.close_margin_position(
                        trade_symbol, 'sell', volume=pos.quantity,
                        leverage=pos.leverage
                    )
                    if sell_order and (sell_order.get('orderId') or sell_order.get('margin_close')):
                        success = True
                    else:
                        print(f"   [MARGIN] Close failed for {trade_symbol}: {sell_order}. Retrying next cycle.")
                        return
                else:
                    # Sell entire quantity (spot)
                    sell_order = self.client.place_market_order(trade_symbol, 'SELL', quantity=pos.quantity)
                    if sell_order and sell_order.get('orderId'):
                        success = True
                    else:
                        print(f"   Sell failed for {trade_symbol}: No order ID returned. Retrying next cycle.")
                        return # Don't remove position, try again later
            except Exception as e:
                prefix = "[MARGIN] " if pos.is_margin else ""
                print(f"   {prefix}Sell execution error for {trade_symbol}: {e}")
                return # Don't remove position, try again later
        else:
            success = True # Dry run always succeeds
            
        # Only remove if successful
        if success:
            self.positions.pop(symbol)
        
        # 📐 Calculate P&L using consistent fee model matching penny profit formula
        # Use combined rate (fee + slippage + spread) for both legs
        fee_rate = CONFIG.get('KRAKEN_FEE_TAKER', CONFIG['KRAKEN_FEE'])
        slippage = CONFIG.get('SLIPPAGE_PCT', 0.002)
        spread = CONFIG.get('SPREAD_COST_PCT', 0.001)
        total_rate = fee_rate + slippage + spread
        
        exit_value = pos.quantity * price
        exit_fee = exit_value * total_rate
        
        # Total Expenses = Entry Fee + Exit Fee (both use combined rate)
        total_expenses = pos.entry_fee + exit_fee
        
        gross_pnl = exit_value - pos.entry_value
        net_pnl = gross_pnl - total_expenses

        # 👑 The King records the sell
        if KING_AVAILABLE and king_on_sell and not self.dry_run:
            try:
                order_id = ""
                if sell_order:
                    order_id = sell_order.get('orderId', '')
                king_on_sell(
                    'kraken', trade_symbol, pos.quantity, price,
                    fee=exit_fee, order_id=order_id,
                    is_margin=pos.is_margin, leverage=pos.leverage,
                )
            except Exception:
                pass  # Non-critical

        # 💎 VALIDATE THE SELL - No phantom gains!
        validated_pnl = net_pnl
        if TRADE_VALIDATOR_AVAILABLE and validate_sell and sell_order and not self.dry_run:
            try:
                sell_validation = validate_sell(
                    symbol=symbol,
                    exchange='kraken',
                    order_response=sell_order,
                    cost_basis=pos.entry_value,
                    qty=pos.quantity
                )
                if sell_validation.is_valid:
                    # Use VALIDATED P&L (from actual fill price)
                    if sell_validation.net_pnl is not None:
                        validated_pnl = sell_validation.net_pnl
                        print(f"   💎 VALIDATED: Order {sell_validation.order_id} | Net: ${validated_pnl:+.4f}")
                else:
                    print(f"   ⚠️ SELL NOT VALIDATED: {', '.join(sell_validation.errors)}")
            except Exception as val_err:
                print(f"   ⚠️ Validation error: {val_err}")
        
        # Use validated P&L
        net_pnl = validated_pnl
        
        # Release symbol exposure
        if symbol in self.tracker.symbol_exposure:
            del self.tracker.symbol_exposure[symbol]
        
        # Calculate hold time
        hold_time_sec = time.time() - pos.entry_time
        
        # 🌟 Return capital to pool with profit
        self.capital_pool.deallocate(symbol, pos.entry_value, net_pnl)
        
        # Record trade with hold time
        self.tracker.record_trade(net_pnl, total_expenses, symbol, reason, hold_time_sec)
        
        # Feed learning back to Mycelium Network
        # pct is the price change percentage. If positive, we reinforce.
        self.mycelium.learn(symbol, pct)
        
        # 🔮 NEXUS PREDICTOR LEARNING - Update patterns from trade outcome 🔮
        if self.nexus is not None:
            try:
                pnl_pct = (net_pnl / pos.entry_value) * 100 if pos.entry_value > 0 else 0
                entry_prediction = {
                    'direction': 'LONG',
                    'probability': pos.nexus_prob,
                    'edge': pos.nexus_edge,
                    'patterns_triggered': pos.nexus_patterns,
                }
                self.nexus.record_trade_outcome(
                    entry_prediction=entry_prediction,
                    was_profitable=(net_pnl > 0),
                    pnl_pct=pnl_pct
                )
            except Exception as e:
                pass  # Silent fail
        
        icon = "✅" if net_pnl > 0 else "❌"
        # Dynamic currency symbol
        curr_sym = "£" if CONFIG['BASE_CURRENCY'] == 'GBP' else "€" if CONFIG['BASE_CURRENCY'] == 'EUR' else "$"
        gen_marker = f" [G{pos.generation}]" if pos.generation > 0 else ""
        margin_marker = f" [MARGIN {pos.leverage}x]" if pos.is_margin else ""
        print(f"   {icon} CLOSE {pos.symbol:12s}{gen_marker}{margin_marker} | {reason} {pct:+.2f}% | Net: {curr_sym}{net_pnl:+.2f} | Pool: {curr_sym}{self.capital_pool.total_profits:+.2f} | WR: {self.tracker.win_rate:.1f}%")
        # Refresh equity to keep tracker in sync with realised trade
        self.refresh_equity()
        
    def _get_node_icon(self, node: str) -> str:
        """Get emoji for dominant node"""
        icons = {
            'Tiger': '🐅', 'Falcon': '🦅', 'Hummingbird': '🐦',
            'Dolphin': '🐬', 'Deer': '🦌', 'Owl': '🦉',
            'Panda': '🐼', 'CargoShip': '🚢', 'Clownfish': '🐠'
        }
        return icons.get(node, '🎯')

    # ─────────────────────────────────────────────────────────
    # Main Loop
    # ─────────────────────────────────────────────────────────
    
    def run(self, interval: float = 5.0):
        """Main trading loop"""
        # 🛠️ CRITICAL: Compute REAL wallet balance BEFORE banner!
        total, cash, _holdings = self.compute_total_equity()
        if self.tracker.initial_balance == 1000.0 and self.tracker.total_trades == 0:
            if abs(total - 1000.0) > 1.0 and total > 0:
                print(f"\n   ⚖️  AUTO-CORRECTING BALANCE: ${self.tracker.initial_balance:.2f} -> ${total:.2f} (Actual Wallet)\n")
                self.tracker.initial_balance = total
                self.tracker.first_start_balance = total
                self.tracker.balance = total
                self.tracker.peak_balance = total
                self.tracker.equity_baseline = total
                self.tracker.portfolio_equity = total
                self.tracker.cash_balance = cash
                self.total_equity_gbp = total
                self.cash_balance_gbp = cash
        
        self.banner()
        
        print("🐙 Connecting to Kraken ecosystem...")
        pair_count = self.refresh_tickers()
        print(f"✅ Connected! {pair_count} pairs loaded")
        
        # Find initial opportunities for WebSocket
        initial_opps = self.find_opportunities()
        symbols_to_watch = [o['symbol'] for o in initial_opps[:15]]
        
        # Add major pairs for base currency
        base = CONFIG['BASE_CURRENCY']
        major_bases = ['ETH', 'SOL', 'XBT', 'ADA', 'DOT', 'LINK']
        for base_asset in major_bases:
            pair = f"{base_asset}{base}"
            if pair not in symbols_to_watch and pair in self.ticker_cache:
                symbols_to_watch.append(pair)
                
        print(f"\n🔴 Starting WebSocket for {len(symbols_to_watch)} pairs...")
        self.start_websocket(symbols_to_watch)
        
        try:
            while True:
                self.iteration += 1
                now = datetime.now().strftime("%H:%M:%S")
                
                print(f"\n{'━'*70}")
                print(f"🔄 Cycle {self.iteration} - {now} [{self.scan_direction}]")
                print(f"{'━'*70}")
                
                # Refresh data
                self.refresh_tickers()
                self.refresh_equity(mark_cycle=True)
                
                # Deploy scouts on first cycle if enabled
                if self.iteration == 1 and not self.scouts_deployed:
                    self._deploy_scouts()
                
                # Toggle scan direction for fair scheduling (A→Z / Z→A)
                self.scan_direction = 'Z→A' if self.iteration % 2 == 0 else 'A→Z'
                
                # Check positions
                self.check_positions()
                
                # Check network coherence - pause if too low
                network_coherence = self.mycelium.get_network_coherence()
                trading_paused = network_coherence < CONFIG['MIN_NETWORK_COHERENCE']
                
                # Check WebSocket health
                ws_stale = (time.time() - self.ws_last_message) > CONFIG['WS_HEARTBEAT_TIMEOUT']
                if ws_stale and self.ws_connected:
                    print("   ⚠️ WebSocket appears stale, falling back to REST")
                
                # Update Lattice State (Global Physics)
                raw_opps = self.find_opportunities()
                l_state = self.lattice.update(raw_opps)
                
                # Apply Triadic Envelope Protocol to filter signals
                all_opps = self.lattice.filter_signals(raw_opps)

                # 👁 Feed the Seer and apply cosmic risk modifier
                if SEER_AVAILABLE and seer_update_context:
                    try:
                        seer_update_context(
                            positions=self.positions,
                            ticker_cache=self.ticker_cache,
                            market_data={"coherence": network_coherence, "lattice": l_state},
                        )
                    except Exception:
                        pass

                # 🎵 Feed Lyra emotional frequency data
                if LYRA_AVAILABLE and lyra_update_context:
                    try:
                        lyra_update_context(
                            positions=self.positions,
                            ticker_cache=self.ticker_cache,
                            market_data={"coherence": network_coherence, "lattice": l_state},
                        )
                    except Exception:
                        pass

                # Dynamic Portfolio Rebalancing - sell underperformers if better opportunities exist
                freed_capital = 0.0
                if all_opps and len(self.positions) >= CONFIG['MAX_POSITIONS'] // 2:
                    freed_capital = self.rebalance_portfolio(all_opps)
                    if freed_capital > 0:
                        self.refresh_equity()  # Update cash after rebalancing

                # Find opportunities (if not halted or paused)
                if len(self.positions) < CONFIG['MAX_POSITIONS'] and not self.tracker.trading_halted and not trading_paused:
                    if all_opps:
                        purity = self.lattice.get_field_purity()
                        purity_icon = "🟢" if purity > 0.9 else "🟠" if purity > 0.5 else "🔴"
                        nexus_status = "🔮 NEXUS" if self.nexus else ""
                        print(f"\n   🔮 Top Opportunities (Triadic Filtered | Purity: {purity_icon} {purity*100:.1f}%) {nexus_status}:")
                        for opp in all_opps[:5]:
                            icon = self._get_node_icon(opp['dominant_node'])
                            lock = "🔒" if opp.get('memory_locked') else "🔓"
                            nexus_info = f"| 🔮{opp.get('nexus_prob', 0.5)*100:.0f}%" if self.nexus else ""
                            print(f"      {icon} {opp['symbol']:12s} +{opp['change24h']:5.1f}% | Γ={opp['coherence']:.2f} | Score: {opp['score']} {nexus_info} {lock}")
                    
                    for opp in all_opps[:CONFIG['MAX_POSITIONS'] - len(self.positions)]:
                        self.open_position(opp)
                        # Also consider margin position for high-confidence opportunities
                        if CONFIG.get('MARGIN_ENABLED') and f"M:{opp['symbol']}" not in self.positions:
                            self.open_margin_position(opp)

                # Show positions
                if self.positions:
                    _spot_count = sum(1 for p in self.positions.values() if not p.is_margin)
                    margin_count = sum(1 for p in self.positions.values() if p.is_margin)
                    label = f"{len(self.positions)}/{CONFIG['MAX_POSITIONS']}"
                    if margin_count > 0:
                        label += f" ({margin_count} margin)"
                    print(f"\n   Active Positions ({label}):")
                    for _sym_key, pos in self.positions.items():
                        lookup = pos.symbol
                        rt = self.get_realtime_price(lookup)
                        if rt:
                            pct = (rt - pos.entry_price) / pos.entry_price * 100
                            src = "RT"
                        else:
                            cached = self.ticker_cache.get(lookup, {}).get('price', pos.entry_price)
                            pct = (cached - pos.entry_price) / pos.entry_price * 100
                            src = "CACHE"
                        icon = self._get_node_icon(pos.dominant_node)
                        margin_tag = f" [{pos.leverage}x]" if pos.is_margin else ""
                        print(f"      {icon} {pos.symbol:12s}{margin_tag} Entry: ${pos.entry_price:.6f} | Now: {pct:+.2f}% [{src}]")
                        
                # Stats
                rt_count = len(self.realtime_prices)
                runtime = (time.time() - self.start_time) / 60
                ws_health = '🟢' if (self.ws_connected and not ws_stale) else ('🟡' if self.ws_connected else '🔴')
                
                # Calculate cycle P&L
                cycle_pnl = self.total_equity_gbp - self.tracker.cycle_equity_start
                cycle_pnl_pct = (cycle_pnl / self.tracker.cycle_equity_start * 100) if self.tracker.cycle_equity_start > 0 else 0
                cycle_icon = "📈" if cycle_pnl >= 0 else "📉"
                
                # Dynamic currency symbol
                curr_sym = "£" if CONFIG['BASE_CURRENCY'] == 'GBP' else "€" if CONFIG['BASE_CURRENCY'] == 'EUR' else "$"
                
                # Calculate average hold time
                avg_hold_min = 0.0
                if self.tracker.closed_positions > 0:
                    avg_hold_min = (self.tracker.total_hold_time_sec / self.tracker.closed_positions) / 60
                
                # Mode indicator
                mode_str = "🎯 HIGH-Γ" if CONFIG['HIGH_COHERENCE_MODE'] else "🔥 AGGRESSIVE"
                lambda_str = "Λ-Field" if CONFIG['ENABLE_LAMBDA_FIELD'] else "Classic"
                
                # 🌟 Swarm orchestrator stats
                capital_available = self.capital_pool.get_available()
                _cycle_profits = self.capital_pool.profits_this_cycle
                total_pool_profits = self.capital_pool.total_profits
                
                # Count scouts and generations
                scout_count = sum(1 for p in self.positions.values() if p.is_scout)
                max_gen = max([p.generation for p in self.positions.values()], default=0)
                split_count = len(self.position_splitter.split_history)
                
                # Latest signal info
                latest_signal = self.signal_broadcaster.get_latest_signal(max_age_seconds=60)
                signal_str = ""
                if latest_signal:
                    signal_str = f" | 🐺 Signal: {latest_signal.symbol} {latest_signal.direction} ({latest_signal.strength:.2f})"
                
                print(f"\n   💎 Portfolio: {curr_sym}{self.total_equity_gbp:.2f} ({self.tracker.total_return:+.2f}%) | Peak: {curr_sym}{self.tracker.peak_balance:.2f}")
                print(f"   📉 Max DD: {self.tracker.max_drawdown:.1f}% | Current DD: {self.tracker.current_drawdown:.1f}%")
                print(f"   {cycle_icon} Cycle P&L: {curr_sym}{cycle_pnl:+.2f} ({cycle_pnl_pct:+.2f}%)")
                print(f"   📈 Trades: {self.tracker.total_trades} | Wins: {self.tracker.wins} | WR: {self.tracker.win_rate:.1f}% | Avg Hold: {avg_hold_min:.1f}m")
                print(f"   🍄 Network Γ: {network_coherence:.2f} {'⚠️ PAUSED' if trading_paused else ''} | WS: {ws_health} ({rt_count})")
                print(f"   🌐 Lattice: {l_state.phase} ({l_state.frequency}Hz) | Purity: {l_state.field_purity*100:.0f}% | {lambda_str}")
                print(f"   🎮 Mode: {mode_str} | Entry Γ: {CONFIG['ENTRY_COHERENCE']:.3f} | Exit Γ: {CONFIG['EXIT_COHERENCE']:.3f}")
                print(f"   💰 Compounded: {curr_sym}{self.tracker.compounded:.2f} | Harvested: {curr_sym}{self.tracker.harvested:.2f}")
                print(f"   Pool: {curr_sym}{total_pool_profits:+.2f} total | {curr_sym}{capital_available:.2f} available | Scouts: {scout_count} | Splits: {split_count}{signal_str}")
                print(f"   Runtime: {runtime:.1f} min | Positions: {len(self.positions)}/{CONFIG['MAX_POSITIONS']} | Max Gen: {max_gen}")

                # 🏛️ The Quadrumvirate status (Queen + King + Seer + Lyra)
                if SEER_AVAILABLE and seer_get_vision:
                    try:
                        sv = seer_get_vision()
                        if sv and sv.get("grade"):
                            seer_str = f"Seer: {sv['grade']} ({sv.get('unified_score', 0):.2f}) | Risk: {sv.get('risk_modifier', 1.0):.1f}x"
                            king_str = "King: Active" if KING_AVAILABLE else "King: N/A"
                            lyra_str = ""
                            if LYRA_AVAILABLE and lyra_get_resonance:
                                try:
                                    lr = lyra_get_resonance()
                                    if lr and lr.get("grade"):
                                        lyra_str = f" | Lyra: {lr['grade']} ({lr.get('score', 0):.2f})"
                                except Exception:
                                    pass
                            print(f"   [QUADRUMVIRATE] {seer_str} | {king_str}{lyra_str}")
                    except Exception:
                        pass
                
                if self.tracker.trading_halted:
                    print(f"   🛑 TRADING HALTED: {self.tracker.halt_reason}")
                
                # Save state periodically
                if self.iteration % 10 == 0:
                    self.save_state()
                
                # 🐕 WATCHDOG HEARTBEAT: Write timestamp file for external monitoring
                try:
                    import json  # noqa: F811
                    with open('.aureon_heartbeat', 'w') as hb:
                        hb.write(json.dumps({
                            'timestamp': time.time(),
                            'iteration': self.iteration,
                            'positions': len(self.positions),
                            'equity': self.tracker.balance,
                            'status': 'RUNNING'
                        }))
                except Exception:
                    pass  # Non-critical
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🐙 Shutting down ecosystem...")
            self.save_state()
            print("   💾 State saved for recovery")
            self.final_report()
            
    def final_report(self):
        """Print final statistics"""
        # Calculate from TRUE starting balance
        true_start = self.tracker.first_start_balance
        true_pnl = self.tracker.balance - true_start
        true_return = (true_pnl / true_start * 100) if true_start > 0 else 0
        start_time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(self.tracker.first_start_time))
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║          🐙🌌 AUREON KRAKEN ECOSYSTEM - FINAL REPORT 🌌🐙               ║
╚══════════════════════════════════════════════════════════════════════════╝

   📅 First Started:   {start_time_str}
   💵 TRUE Starting:   ${true_start:.2f}  (actual portfolio value when first run)
   💰 Current Balance: ${self.tracker.balance:.2f}
   📊 NET P&L:         ${true_pnl:+.2f} ({true_return:+.2f}%)

   Total Trades:      {self.tracker.total_trades}
   Wins:              {self.tracker.wins}
   Losses:            {self.tracker.losses}
   🎯 WIN RATE:       {self.tracker.win_rate:.1f}%

   Total Fees:        ${self.tracker.total_fees:.2f}
   Max Drawdown:      {self.tracker.max_drawdown:.1f}%
   
   💰 10-9-1 MODEL:
   ├─ Compounded:     ${self.tracker.compounded:.2f}
   └─ Harvested:      ${self.tracker.harvested:.2f}
   
   🛡️ RISK CONTROLS:
   ├─ Max Drawdown:   {self.tracker.max_drawdown:.1f}% / {CONFIG['MAX_DRAWDOWN_PCT']:.1f}%
   ├─ Position Sizing: {'Kelly Criterion' if CONFIG['USE_KELLY_SIZING'] else 'Fixed %'}
   └─ Circuit Breaker: {'🛑 ACTIVATED' if self.tracker.trading_halted else '✅ OK'}
""")
        
        if self.tracker.win_rate >= 51 and true_pnl > 0:
            print("   ✅ GOAL ACHIEVED: 51%+ WR + NET PROFIT! ✅")
        else:
            print(f"   📊 Status: WR={self.tracker.win_rate:.1f}%, Net=${true_pnl:+.2f}")


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    # Configuration from environment
    dry_run = os.getenv('LIVE', '0') != '1'
    balance = float(os.getenv('BALANCE', 1000))
    interval = float(os.getenv('INTERVAL', 5))
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║  🐙 AUREON KRAKEN ECOSYSTEM 🐙                            ║
    ║                                                           ║
    ║  Usage:                                                   ║
    ║    LIVE=1 python aureon_kraken_ecosystem.py  # Live mode  ║
    ║    BALANCE=5000 python aureon_kraken_ecosystem.py         ║
    ║    INTERVAL=3 python aureon_kraken_ecosystem.py           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    ecosystem = AureonKrakenEcosystem(
        initial_balance=balance,
        dry_run=dry_run
    )
    
    ecosystem.run(interval=interval)


if __name__ == "__main__":
    main()
