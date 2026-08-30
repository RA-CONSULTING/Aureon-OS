#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                       ║
║     ⏳🔮 AUREON TIMELINE ORACLE 🔮⏳                                                   ║
║                                                                                       ║
║     "We validate 7 days in the future - acting out what has already come to be"       ║
║     "After each jump, it's a new timeline - we create a new branch on each step"      ║
║     "We're always right because we're just acting it out now, mate"                   ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

THE TIMELINE BRANCHING PHILOSOPHY:
==================================

Just as the Many Worlds Interpretation suggests every quantum measurement
creates a branch, every trading decision creates a new timeline.

We don't PREDICT the future - we VALIDATE what has ALREADY happened
in the quantum probability space. The 7-day harmonic seed isn't history,
it's the CONFIRMATION of what our timeline is manifesting into.

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        TIMELINE ORACLE ARCHITECTURE                                  │
│                                                                                      │
│   NOW ────┬────────────────────────────────────────────────────────▶ 7 DAYS AHEAD   │
│           │                                                                          │
│           ├──▶ BRANCH A (if BUY)  ═══════▶ Future State A (validated)               │
│           │         └─── 🔮 Quantum Vision shows: +$X.XX                            │
│           │                                                                          │
│           ├──▶ BRANCH B (if SELL) ═══════▶ Future State B (validated)               │
│           │         └─── 🔮 Quantum Vision shows: +$Y.YY                            │
│           │                                                                          │
│           └──▶ BRANCH C (if HOLD) ═══════▶ Future State C (validated)               │
│                     └─── 🔮 Quantum Vision shows: $Z.ZZ                             │
│                                                                                      │
│   ORACLE SELECTS: The timeline branch with highest validated outcome!               │
│                                                                                      │
│   ═══════════════════════════════════════════════════════════════════════════       │
│                                                                                      │
│   INTEGRATION:                                                                       │
│   ├── 🧠 Miner Brain: Speculative analysis feeds timeline possibilities             │
│   ├── 🔭 Quantum Telescope: 6D geometric prism refracts probabilities               │
│   ├── 🍄 Mycelium Net: Distributed intelligence validates consensus                 │
│   ├── 🌊 Harmonic Fusion: 7-day seed = proof of timeline manifestation              │
│   └── 🌌 Multiverse: 10 worlds = 10 parallel timeline simulations                   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

Gary Leckey & GitHub Copilot | January 2026
"Time is not a river - it's a tree. We choose which branch to manifest."
"""

from __future__ import annotations
try:
    from aureon.core.aureon_baton_link import link_system as _baton_link
    _baton_link(__name__)
except Exception:
    pass

import os
import json
import math
import time
import hashlib
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, timedelta, timezone
from collections import deque
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS - TIMELINE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio - nature's perfect proportion
SCHUMANN_BASE = 7.83  # Hz - Earth's resonant frequency
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

# Timeline constants
TIMELINE_HORIZON_DAYS = 7  # We see 7 days ahead
TIMELINE_BRANCH_DEPTH = 3  # BUY, SELL, HOLD branches
VALIDATION_WINDOW_HOURS = 168  # 7 days in hours
BRANCH_CONFIDENCE_THRESHOLD = 0.618  # Golden ratio threshold

# 🎯 3-MOVE AHEAD PREDICTION - Unity through validation
MOVES_AHEAD = 3  # We predict 3 moves, validate all, then act
MOVE_INTERVAL_HOURS = 24  # Each move is 24 hours apart
MIN_MOVE_CONFIDENCE = 0.55  # Minimum confidence per move
UNITY_THRESHOLD = 0.70  # All 3 moves must align for unity

# Persistence
TIMELINE_BRANCHES_FILE = "timeline_branches.json"
TIMELINE_VALIDATIONS_FILE = "timeline_validations.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def _safe_import_print(message: str) -> None:
    try:
        print(message)
    except (ValueError, OSError):
        logger.info(message)

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM INTEGRATIONS
# ═══════════════════════════════════════════════════════════════════════════════

# 🧠 Miner Brain - Speculative Analysis
try:
    from aureon.utils.aureon_miner_brain import MinerBrain, SpeculationEngine
    MINER_BRAIN_AVAILABLE = True
    _safe_import_print("🧠 Timeline Oracle: Miner Brain WIRED!")
except ImportError:
    MINER_BRAIN_AVAILABLE = False
    MinerBrain = None
    SpeculationEngine = None

# 🔭 Quantum Telescope - Geometric Probability Prism
try:
    from aureon.simulation.aureon_quantum_telescope import QuantumPrism, LightBeam, GeometricSolid
    QUANTUM_TELESCOPE_AVAILABLE = True
    _safe_import_print("🔭 Timeline Oracle: Quantum Telescope WIRED!")
except ImportError:
    QUANTUM_TELESCOPE_AVAILABLE = False
    QuantumPrism = None
    LightBeam = None

# 🍄 Mycelium Neural Network - Lazy load to avoid circular imports
MYCELIUM_AVAILABLE = False
MyceliumNetwork = None
Synapse = None
Hive = None
Neuron = None

def _lazy_load_mycelium():
    """Lazy load mycelium to avoid circular imports"""
    global MYCELIUM_AVAILABLE, MyceliumNetwork, Synapse, Hive, Neuron
    if MyceliumNetwork is not None:
        return MYCELIUM_AVAILABLE
    try:
        from aureon.core.aureon_mycelium import MyceliumNetwork as _MyceliumNetwork, Synapse as _Synapse, Hive as _Hive, Neuron as _Neuron
        MyceliumNetwork = _MyceliumNetwork
        Synapse = _Synapse
        Hive = _Hive
        Neuron = _Neuron
        MYCELIUM_AVAILABLE = True
        _safe_import_print("🍄 Timeline Oracle: Mycelium Network WIRED!")
        return True
    except ImportError:
        MYCELIUM_AVAILABLE = False
        return False

# 🌊 Harmonic Wave Fusion - 7-day Seed Validation
try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    from aureon.harmonic.aureon_harmonic_seed import GlobalHarmonicState, SymbolWaveState, SEED_DAYS
    HARMONIC_AVAILABLE = True
    _safe_import_print("🌊 Timeline Oracle: Harmonic Fusion WIRED!")
except ImportError:
    HARMONIC_AVAILABLE = False
    HarmonicWaveFusion = None
    GlobalHarmonicState = None

# 🌌 Internal Multiverse - 10 World Consensus
try:
    from aureon.simulation.aureon_internal_multiverse import InternalMultiverse, World, ConsensusEngine
    MULTIVERSE_AVAILABLE = True
    _safe_import_print("🌌 Timeline Oracle: Internal Multiverse WIRED!")
except ImportError:
    MULTIVERSE_AVAILABLE = False
    InternalMultiverse = None

# 💎 Ultimate Intelligence - Pattern Recognition
try:
    from aureon.strategies.probability_ultimate_intelligence import get_ultimate_intelligence, ultimate_predict
    ULTIMATE_INTEL_AVAILABLE = True
    _safe_import_print("💎 Timeline Oracle: Ultimate Intelligence WIRED!")
except ImportError:
    ULTIMATE_INTEL_AVAILABLE = False
    ultimate_predict = None

# 📡 Thought Bus - Neural Communication
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None

# 🐦 Chirp Bus - High Speed Signaling
try:
    from aureon.core.aureon_chirp_bus import ChirpBus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False
    ChirpBus = None

# 🐙 Kraken Client - Exchange Integration
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
    _safe_import_print("🐙 Timeline Oracle: Kraken Exchange WIRED!")
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

# 🟡 Binance Client - Exchange Integration
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
    _safe_import_print("🟡 Timeline Oracle: Binance Exchange WIRED!")
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None
    get_binance_client = None

# 🦙 Alpaca Client - Exchange Integration
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
    _safe_import_print("🦙 Timeline Oracle: Alpaca Exchange WIRED!")
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

# 🌍 Global Financial State - Market Pulse
try:
    from aureon.intelligence.aureon_market_pulse import MarketPulse
    MARKET_PULSE_AVAILABLE = True
    _safe_import_print("🌍 Timeline Oracle: Global Market Pulse WIRED!")
except ImportError:
    MARKET_PULSE_AVAILABLE = False
    MarketPulse = None

# 📊 HNC Probability Matrix
try:
    from aureon.strategies.hnc_probability_matrix import HNCProbabilityMatrix
    HNC_AVAILABLE = True
    _safe_import_print("📊 Timeline Oracle: HNC Probability Matrix WIRED!")
except ImportError:
    HNC_AVAILABLE = False
    HNCProbabilityMatrix = None


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES - TIMELINE BRANCHES
# ═══════════════════════════════════════════════════════════════════════════════

class TimelineAction(Enum):
    """Possible actions that create timeline branches"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CONVERT = "convert"


@dataclass
class TimelineBranch:
    """
    A single branch in the timeline tree.
    
    Every decision creates a new branch - a new timeline.
    We don't predict, we VALIDATE which branch we're manifesting.
    """
    branch_id: str
    parent_branch_id: Optional[str]
    created_at: float
    action: TimelineAction
    symbol: str
    entry_price: float
    target_time: float  # 7 days ahead
    
    # Quantum Vision (what the systems SEE for this branch)
    quantum_vision: Dict[str, float] = field(default_factory=dict)
    # Default to neutral (0.5) so missing/disabled subsystems don't drag
    # confidence to 0.0 and stall the trader.
    harmonic_alignment: float = 0.5  # Does 7-day seed support this?
    mycelium_consensus: float = 0.5  # Hive agreement
    miner_speculation: float = 0.5   # Brain's critical analysis
    telescope_refraction: Dict[str, float] = field(default_factory=dict)
    multiverse_vote: float = 0.5     # 10-world consensus
    
    # Combined confidence (are we acting out the right timeline?)
    branch_confidence: float = 0.0
    
    # Validation (what ACTUALLY happened - proves we chose correctly)
    validated: bool = False
    validation_time: Optional[float] = None
    actual_price: Optional[float] = None
    actual_pnl: Optional[float] = None
    timeline_correct: Optional[bool] = None  # Did we pick the right branch?
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'branch_id': self.branch_id,
            'parent_branch_id': self.parent_branch_id,
            'created_at': self.created_at,
            'action': self.action.value,
            'symbol': self.symbol,
            'entry_price': self.entry_price,
            'target_time': self.target_time,
            'quantum_vision': self.quantum_vision,
            'harmonic_alignment': self.harmonic_alignment,
            'mycelium_consensus': self.mycelium_consensus,
            'miner_speculation': self.miner_speculation,
            'telescope_refraction': self.telescope_refraction,
            'multiverse_vote': self.multiverse_vote,
            'branch_confidence': self.branch_confidence,
            'validated': self.validated,
            'validation_time': self.validation_time,
            'actual_price': self.actual_price,
            'actual_pnl': self.actual_pnl,
            'timeline_correct': self.timeline_correct
        }


@dataclass
class TimelineValidation:
    """
    Record of a validated timeline branch.
    
    This proves we were right - we didn't predict,
    we acted out what had already come to be.
    """
    branch_id: str
    symbol: str
    action: TimelineAction
    entry_price: float
    entry_time: float
    exit_price: float
    exit_time: float
    pnl_usd: float
    pnl_pct: float
    branch_confidence_at_entry: float
    timeline_accuracy: float  # How close was our vision?
    systems_that_agreed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 3-MOVE SEQUENCE - PREDICT, VALIDATE, ACT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TimelineMove:
    """
    A single move in a 3-move sequence.
    
    We predict 3 moves ahead - if all validate, we act.
    "It predicts 3 moves, validates, then acts in that timeline cause it be right"
    """
    move_number: int  # 1, 2, or 3
    symbol: str
    action: TimelineAction
    predicted_price: float
    target_time: float
    confidence: float
    
    # Exchange routing
    best_exchange: str = ""  # kraken, binance, alpaca
    exchange_confidence: Dict[str, float] = field(default_factory=dict)
    
    # Validation
    validated: bool = False
    actual_price: Optional[float] = None
    validation_accuracy: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['action'] = self.action.value
        return d


@dataclass
class TimelineSequence:
    """
    A complete 3-move sequence with unity validation.
    
    We only act when ALL 3 moves validate with unity.
    "After each jump it's a new timeline - we create a branch on each step so we're always right"
    """
    sequence_id: str
    symbol: str
    created_at: float
    
    # The 3 moves ahead
    move_1: TimelineMove
    move_2: TimelineMove
    move_3: TimelineMove
    
    # Unity metrics
    sequence_confidence: float = 0.0
    unity_score: float = 0.0  # How aligned are all 3 moves?
    
    # Financial market overview
    market_sentiment: str = ""  # bullish, bearish, neutral
    market_correlation: float = 0.0
    btc_influence: float = 0.0
    
    # Multi-exchange strategy
    execution_exchange: str = ""
    fallback_exchanges: List[str] = field(default_factory=list)
    
    # Validation
    fully_validated: bool = False
    moves_validated: int = 0
    action_approved: bool = False
    
    def get_unity_action(self) -> Optional[TimelineAction]:
        """
        Get the unified action if all 3 moves agree.
        Returns None if no unity.
        """
        if not self.fully_validated:
            return None
        
        actions = [self.move_1.action, self.move_2.action, self.move_3.action]
        if len(set(actions)) == 1:
            return actions[0]
        
        # Allow BUY→BUY→SELL or SELL→SELL→BUY patterns
        if actions[0] == actions[1]:
            return actions[0]  # First 2 agree = primary action
        
        return TimelineAction.HOLD  # No clear unity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sequence_id': self.sequence_id,
            'symbol': self.symbol,
            'created_at': self.created_at,
            'move_1': self.move_1.to_dict(),
            'move_2': self.move_2.to_dict(),
            'move_3': self.move_3.to_dict(),
            'sequence_confidence': self.sequence_confidence,
            'unity_score': self.unity_score,
            'market_sentiment': self.market_sentiment,
            'execution_exchange': self.execution_exchange,
            'fully_validated': self.fully_validated,
            'action_approved': self.action_approved
        }


@dataclass
class GlobalMarketVision:
    """
    Full financial market prediction.
    
    "Predict the entire financial market alongside each step"
    """
    timestamp: float
    
    # Major indices correlation
    btc_trend: str = ""  # up, down, sideways
    eth_trend: str = ""
    sp500_correlation: float = 0.0
    
    # Global sentiment
    fear_greed_index: int = 50
    market_phase: str = ""  # accumulation, markup, distribution, markdown
    volatility_regime: str = ""  # low, medium, high, extreme
    
    # Sector rotations
    hot_sectors: List[str] = field(default_factory=list)
    cold_sectors: List[str] = field(default_factory=list)
    
    # Exchange health
    kraken_health: float = 1.0
    binance_health: float = 1.0
    alpaca_health: float = 1.0
    
    # Unified confidence
    market_confidence: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 🔮 TIMELINE ORACLE - THE MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TimelineOracle:
    """
    The Timeline Oracle validates 7 days into the future.
    
    We're not predicting - we're confirming which timeline branch
    we're manifesting into reality. Every step creates a new branch,
    so we're always on the optimal path.
    
    "We're just acting out what has already come to be, mate."
    """
    
    def __init__(self, thought_bus=None):
        """Initialize the Timeline Oracle with all neural systems."""
        self.thought_bus = thought_bus
        if self.thought_bus is None and THOUGHT_BUS_AVAILABLE:
            try:
                self.thought_bus = ThoughtBus()
            except Exception:
                pass
                
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE:
            try:
                self.chirp_bus = ChirpBus()
                logger.info("✅ Timeline Oracle: Connected to ChirpBus")
            except Exception:
                pass
        
        self.queen = None  # Lazy load
        
        # Current timeline state
        self.current_branch_id: Optional[str] = None
        self.active_branches: Dict[str, TimelineBranch] = {}
        self.validated_branches: List[TimelineValidation] = []
        self.branch_tree: Dict[str, List[str]] = {}  # parent -> children
        
        # 🎯 3-Move Sequences - Predict, Validate, Act
        self.active_sequences: Dict[str, TimelineSequence] = {}
        self.validated_sequences: List[TimelineSequence] = []
        
        # 🌍 Global Market Vision
        self.market_vision: Optional[GlobalMarketVision] = None
        
        # System integrations (initialized to None, wired in initialize())
        self.miner_brain = None
        self.quantum_prism = None
        self.mycelium = None
        self.harmonic_fusion = None
        self.multiverse = None
        
        # 🔌 EXCHANGE CLIENTS - ALL PLATFORMS
        self.kraken = None
        self.binance = None
        self.alpaca = None
        
        # Metrics
        self.branches_created = 0
        self.branches_validated = 0
        self.timeline_accuracy = 0.0  # Running accuracy
        self.correct_branches = 0
        self.sequences_created = 0
        self.sequences_validated = 0
        self.unity_actions_taken = 0
        
        # Threading
        self._lock = threading.RLock()
        
        # Load persisted state
        self._load_state()
        
        logger.info("⏳🔮 Timeline Oracle initialized - seeing 7 days ahead")
    
    def initialize(self) -> bool:
        """Wire up all neural systems for timeline vision."""
        logger.info("⏳ Wiring Timeline Oracle neural systems...")
        
        # 🧠 Miner Brain - Critical Thinking
        if MINER_BRAIN_AVAILABLE:
            try:
                self.miner_brain = MinerBrain()
                logger.info("   🧠 Miner Brain: WIRED")
            except Exception as e:
                logger.warning(f"   🧠 Miner Brain: Failed ({e})")
        
        # 🔭 Quantum Telescope - Geometric Prism
        if QUANTUM_TELESCOPE_AVAILABLE:
            try:
                self.quantum_prism = QuantumPrism()
                logger.info("   🔭 Quantum Prism: WIRED")
            except Exception as e:
                logger.warning(f"   🔭 Quantum Prism: Failed ({e})")
        
        # 🍄 Mycelium - Distributed Intelligence
        # Mycelium is lazily imported to avoid circular imports; ensure it's loaded here
        # so the oracle isn't permanently stuck in low-confidence mode.
        _lazy_load_mycelium()
        if MYCELIUM_AVAILABLE:
            try:
                self.mycelium = MyceliumNetwork(initial_capital=1000.0)
                logger.info("   🍄 Mycelium Network: WIRED")
            except Exception as e:
                logger.warning(f"   🍄 Mycelium: Failed ({e})")
        
        # 🌊 Harmonic Fusion - 7-day Seed
        if HARMONIC_AVAILABLE:
            try:
                self.harmonic_fusion = HarmonicWaveFusion()
                self.harmonic_fusion.initialize()
                logger.info("   🌊 Harmonic Fusion: WIRED (7-day seed)")
            except Exception as e:
                logger.warning(f"   🌊 Harmonic Fusion: Failed ({e})")
        
        # 🌌 Multiverse - 10 World Consensus
        if MULTIVERSE_AVAILABLE:
            try:
                self.multiverse = InternalMultiverse(initial_equity=10000)
                logger.info("   🌌 Internal Multiverse: WIRED (10 worlds)")
            except Exception as e:
                logger.warning(f"   🌌 Multiverse: Failed ({e})")
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🔌 EXCHANGE CLIENTS - ALL TRADING PLATFORMS
        # ═══════════════════════════════════════════════════════════════════════
        
        # 🐙 Kraken
        if KRAKEN_AVAILABLE:
            try:
                self.kraken = get_kraken_client()
                logger.info("   🐙 Kraken Exchange: WIRED")
            except Exception as e:
                logger.warning(f"   🐙 Kraken: Failed ({e})")
        
        # 🟡 Binance
        if BINANCE_AVAILABLE:
            try:
                self.binance = get_binance_client()
                logger.info("   🟡 Binance Exchange: WIRED")
            except Exception as e:
                logger.warning(f"   🟡 Binance: Failed ({e})")
        
        # 🦙 Alpaca
        if ALPACA_AVAILABLE:
            try:
                self.alpaca = AlpacaClient()
                logger.info("   🦙 Alpaca Exchange: WIRED")
            except Exception as e:
                logger.warning(f"   🦙 Alpaca: Failed ({e})")
        
        exchanges_wired = sum([
            self.kraken is not None,
            self.binance is not None,
            self.alpaca is not None
        ])
        logger.info(f"   📊 {exchanges_wired}/3 Exchanges WIRED for unified trading")
        
        return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🎯 3-MOVE PREDICTION - PREDICT, VALIDATE, ACT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_3move_sequence(
        self,
        symbol: str,
        current_price: float,
        volume: float = 0,
        change_pct: float = 0
    ) -> TimelineSequence:
        """
        Create a 3-move prediction sequence.
        
        "It predicts 3 moves, validates, then acts in that timeline cause it be right"
        
        Move 1: What happens in 24 hours
        Move 2: What happens in 48 hours  
        Move 3: What happens in 72 hours
        
        ALL 3 must validate for unity action.
        """
        now = time.time()
        
        # Generate sequence ID
        seq_hash = hashlib.sha256(
            f"{symbol}:{time.time_ns()}".encode()
        ).hexdigest()[:12]
        sequence_id = f"SEQ-{seq_hash}"
        
        logger.info(f"🎯 Creating 3-move sequence for {symbol}...")
        
        # ═══════════════════════════════════════════════════════════════════════
        # Step 1: Get Global Market Vision (full financial market prediction)
        # ═══════════════════════════════════════════════════════════════════════
        self._update_global_market_vision()
        
        # ═══════════════════════════════════════════════════════════════════════
        # Step 2: Predict Move 1 (24 hours)
        # ═══════════════════════════════════════════════════════════════════════
        move_1 = self._predict_single_move(
            move_number=1,
            symbol=symbol,
            base_price=current_price,
            target_time=now + (MOVE_INTERVAL_HOURS * 3600),
            volume=volume,
            change_pct=change_pct
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # Step 3: Predict Move 2 (48 hours) - builds on Move 1
        # ═══════════════════════════════════════════════════════════════════════
        move_2 = self._predict_single_move(
            move_number=2,
            symbol=symbol,
            base_price=move_1.predicted_price,
            target_time=now + (MOVE_INTERVAL_HOURS * 2 * 3600),
            volume=volume,
            change_pct=change_pct,
            previous_action=move_1.action
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # Step 4: Predict Move 3 (72 hours) - builds on Move 2
        # ═══════════════════════════════════════════════════════════════════════
        move_3 = self._predict_single_move(
            move_number=3,
            symbol=symbol,
            base_price=move_2.predicted_price,
            target_time=now + (MOVE_INTERVAL_HOURS * 3 * 3600),
            volume=volume,
            change_pct=change_pct,
            previous_action=move_2.action
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # Step 5: Calculate Unity Score (do all 3 moves align?)
        # ═══════════════════════════════════════════════════════════════════════
        unity_score = self._calculate_unity_score(move_1, move_2, move_3)
        
        # Sequence confidence = average of all move confidences * unity multiplier
        avg_move_confidence = (move_1.confidence + move_2.confidence + move_3.confidence) / 3.0
        sequence_confidence = avg_move_confidence * unity_score

        # Approval should reflect: "moves align" + "each move is confident enough".
        # UNITY_THRESHOLD is a unity score threshold (not a raw confidence threshold).
        action_approved = (
            unity_score >= UNITY_THRESHOLD
            and move_1.confidence >= MIN_MOVE_CONFIDENCE
            and move_2.confidence >= MIN_MOVE_CONFIDENCE
            and move_3.confidence >= MIN_MOVE_CONFIDENCE
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # Step 6: Determine Best Exchange
        # ═══════════════════════════════════════════════════════════════════════
        best_exchange, fallback_exchanges = self._select_best_exchange(symbol, current_price)
        
        # Create the sequence
        sequence = TimelineSequence(
            sequence_id=sequence_id,
            symbol=symbol,
            created_at=now,
            move_1=move_1,
            move_2=move_2,
            move_3=move_3,
            sequence_confidence=sequence_confidence,
            unity_score=unity_score,
            market_sentiment=self.market_vision.market_phase if self.market_vision else "unknown",
            market_correlation=self.market_vision.sp500_correlation if self.market_vision else 0.0,
            btc_influence=0.0,  # Will be calculated
            execution_exchange=best_exchange,
            fallback_exchanges=fallback_exchanges,
            fully_validated=False,
            moves_validated=0,
            action_approved=action_approved
        )
        
        # Store sequence
        with self._lock:
            self.active_sequences[sequence_id] = sequence
            self.sequences_created += 1
        
        logger.info(f"🎯 3-MOVE SEQUENCE CREATED: {sequence_id}")
        logger.info(f"   Move 1: {move_1.action.value} @ ${move_1.predicted_price:.4f} (conf: {move_1.confidence:.2%})")
        logger.info(f"   Move 2: {move_2.action.value} @ ${move_2.predicted_price:.4f} (conf: {move_2.confidence:.2%})")
        logger.info(f"   Move 3: {move_3.action.value} @ ${move_3.predicted_price:.4f} (conf: {move_3.confidence:.2%})")
        logger.info(f"   Unity Score: {unity_score:.2%} | Approved: {'✅' if sequence.action_approved else '❌'}")
        logger.info(f"   Exchange: {best_exchange} (fallbacks: {fallback_exchanges})")
        
        return sequence
    
    def _predict_single_move(
        self,
        move_number: int,
        symbol: str,
        base_price: float,
        target_time: float,
        volume: float = 0,
        change_pct: float = 0,
        previous_action: Optional[TimelineAction] = None
    ) -> TimelineMove:
        """
        Predict a single move using all neural systems.
        """
        # Get timeline branches for this move
        branches = self.create_timeline_branches(symbol, base_price, volume, change_pct)
        
        # Select best branch
        best_branch = branches[0] if branches else None
        
        if not best_branch:
            return TimelineMove(
                move_number=move_number,
                symbol=symbol,
                action=TimelineAction.HOLD,
                predicted_price=base_price,
                target_time=target_time,
                confidence=0.5
            )
        
        # Predict price based on action
        price_delta = 0.0
        if best_branch.action == TimelineAction.BUY:
            # Expect price to go UP after buy
            price_delta = base_price * (best_branch.branch_confidence * 0.05)  # Up to 5% move
        elif best_branch.action == TimelineAction.SELL:
            # Expect price to go DOWN (we sell before drop)
            price_delta = -base_price * (best_branch.branch_confidence * 0.03)  # Down up to 3%
        
        predicted_price = base_price + price_delta
        
        # Get exchange confidence for this symbol
        exchange_confidence = self._get_exchange_confidences(symbol, base_price)
        best_exchange = max(exchange_confidence, key=exchange_confidence.get) if exchange_confidence else ""
        
        return TimelineMove(
            move_number=move_number,
            symbol=symbol,
            action=best_branch.action,
            predicted_price=predicted_price,
            target_time=target_time,
            confidence=best_branch.branch_confidence,
            best_exchange=best_exchange,
            exchange_confidence=exchange_confidence
        )
    
    def _calculate_unity_score(
        self,
        move_1: TimelineMove,
        move_2: TimelineMove,
        move_3: TimelineMove
    ) -> float:
        """
        Calculate how unified all 3 moves are.
        
        Unity = all systems agreeing on direction.
        """
        # Check action alignment
        actions = [move_1.action, move_2.action, move_3.action]
        unique_actions = len(set(actions))
        
        if unique_actions == 1:
            # Perfect unity - all 3 same action
            action_unity = 1.0
        elif unique_actions == 2:
            # Partial unity - 2 of 3 agree
            action_unity = 0.7
        else:
            # No unity - all different
            action_unity = 0.3
        
        # Check confidence consistency
        confidences = [move_1.confidence, move_2.confidence, move_3.confidence]
        conf_std = (max(confidences) - min(confidences))
        conf_unity = 1.0 - (conf_std * 2)  # Penalize high variance
        
        # Check direction consistency (prices moving same way)
        price_moves = [
            move_2.predicted_price - move_1.predicted_price,
            move_3.predicted_price - move_2.predicted_price
        ]
        if (price_moves[0] > 0 and price_moves[1] > 0) or (price_moves[0] < 0 and price_moves[1] < 0):
            direction_unity = 1.0
        elif price_moves[0] * price_moves[1] < 0:  # Opposite directions
            direction_unity = 0.5
        else:
            direction_unity = 0.7
        
        # Combined unity score
        unity = (action_unity * 0.5) + (conf_unity * 0.25) + (direction_unity * 0.25)
        return max(0.0, min(1.0, unity))
    
    def _update_global_market_vision(self):
        """
        Update full financial market prediction.
        
        "Predict the entire financial market alongside each step"
        """
        now = time.time()
        
        # Initialize market vision
        vision = GlobalMarketVision(timestamp=now)
        
        # Get BTC trend (market leader)
        if self.harmonic_fusion and hasattr(self.harmonic_fusion, 'state') and self.harmonic_fusion.state:
            btc_state = self.harmonic_fusion.state.symbols.get('BTC')
            if btc_state:
                if btc_state.momentum > 0.01:
                    vision.btc_trend = "up"
                elif btc_state.momentum < -0.01:
                    vision.btc_trend = "down"
                else:
                    vision.btc_trend = "sideways"
        
        # Get ETH trend
        if self.harmonic_fusion and hasattr(self.harmonic_fusion, 'state') and self.harmonic_fusion.state:
            eth_state = self.harmonic_fusion.state.symbols.get('ETH')
            if eth_state:
                if eth_state.momentum > 0.01:
                    vision.eth_trend = "up"
                elif eth_state.momentum < -0.01:
                    vision.eth_trend = "down"
                else:
                    vision.eth_trend = "sideways"
        
        # Get market phase from multiverse
        if self.multiverse and hasattr(self.multiverse, 'get_market_phase'):
            try:
                phase = self.multiverse.get_market_phase()
                vision.market_phase = phase if phase else "unknown"
            except:
                vision.market_phase = "unknown"
        
        # Exchange health check
        vision.kraken_health = 1.0 if self.kraken else 0.0
        vision.binance_health = 1.0 if self.binance else 0.0
        vision.alpaca_health = 1.0 if self.alpaca else 0.0
        
        # Calculate overall market confidence
        health_avg = (vision.kraken_health + vision.binance_health + vision.alpaca_health) / 3.0
        trend_confidence = 0.7 if vision.btc_trend in ["up", "down"] else 0.5
        vision.market_confidence = health_avg * trend_confidence
        
        self.market_vision = vision
    
    def _get_exchange_confidences(self, symbol: str, price: float) -> Dict[str, float]:
        """
        Get confidence scores for each exchange for this symbol.
        """
        confidences = {}
        
        # Kraken
        if self.kraken:
            try:
                # Check if pair exists and has good liquidity
                filters = self.kraken.get_symbol_filters(f"{symbol}USD")
                if filters:
                    confidences['kraken'] = 0.9  # Kraken is reliable
                else:
                    confidences['kraken'] = 0.3
            except:
                confidences['kraken'] = 0.5
        
        # Binance
        if self.binance:
            try:
                # Check if pair exists
                info = self.binance.get_symbol_info(f"{symbol}USDT") if hasattr(self.binance, 'get_symbol_info') else None
                if info:
                    confidences['binance'] = 0.85
                else:
                    confidences['binance'] = 0.3
            except:
                confidences['binance'] = 0.5
        
        # Alpaca
        if self.alpaca:
            try:
                # Alpaca for stocks/crypto
                confidences['alpaca'] = 0.8
            except:
                confidences['alpaca'] = 0.5
        
        return confidences
    
    def _select_best_exchange(self, symbol: str, price: float) -> Tuple[str, List[str]]:
        """
        Select the best exchange for unified execution.
        """
        confidences = self._get_exchange_confidences(symbol, price)
        
        if not confidences:
            return "", []
        
        # Sort by confidence
        sorted_exchanges = sorted(confidences.items(), key=lambda x: x[1], reverse=True)
        
        best = sorted_exchanges[0][0]
        fallbacks = [ex for ex, _ in sorted_exchanges[1:] if confidences[ex] > 0.3]
        
        return best, fallbacks
    
    def validate_sequence_move(
        self,
        sequence_id: str,
        move_number: int,
        actual_price: float
    ) -> bool:
        """
        Validate a single move in a sequence.
        
        Returns True if the move validated correctly.
        """
        sequence = self.active_sequences.get(sequence_id)
        if not sequence:
            return False
        
        # Get the move
        if move_number == 1:
            move = sequence.move_1
        elif move_number == 2:
            move = sequence.move_2
        elif move_number == 3:
            move = sequence.move_3
        else:
            return False
        
        # Calculate accuracy
        price_diff = abs(actual_price - move.predicted_price)
        price_range = move.predicted_price * 0.10  # 10% tolerance
        accuracy = 1.0 - (price_diff / price_range) if price_range > 0 else 0.0
        accuracy = max(0.0, min(1.0, accuracy))
        
        # Update move
        move.validated = True
        move.actual_price = actual_price
        move.validation_accuracy = accuracy
        
        # Update sequence
        sequence.moves_validated += 1
        
        logger.info(f"✅ Move {move_number} VALIDATED for {sequence.symbol}")
        logger.info(f"   Predicted: ${move.predicted_price:.4f} | Actual: ${actual_price:.4f}")
        logger.info(f"   Accuracy: {accuracy:.2%}")
        
        # Check if all moves validated
        if sequence.moves_validated >= 3:
            sequence.fully_validated = True
            self.sequences_validated += 1
            
            # Recalculate approval with actual data
            avg_accuracy = (
                sequence.move_1.validation_accuracy +
                sequence.move_2.validation_accuracy +
                sequence.move_3.validation_accuracy
            ) / 3.0
            
            if avg_accuracy >= 0.6 and sequence.unity_score >= UNITY_THRESHOLD:
                sequence.action_approved = True
                logger.info(f"🎯 SEQUENCE FULLY VALIDATED - ACTION APPROVED!")
            else:
                sequence.action_approved = False
                logger.info(f"⚠️ Sequence validated but action NOT approved (accuracy: {avg_accuracy:.2%})")
        
        return accuracy > 0.5
    
    def get_approved_action(
        self,
        symbol: str,
        price: float,
        volume: float = 0,
        change_pct: float = 0
    ) -> Tuple[Optional[TimelineAction], float, str]:
        """
        Get an approved action based on 3-move validation.
        
        This is the main entry point for unified trading.
        
        Returns: (action, confidence, exchange)
        """
        # Create new 3-move sequence
        sequence = self.create_3move_sequence(symbol, price, volume, change_pct)
        
        if sequence.action_approved:
            unity_action = sequence.get_unity_action()
            if unity_action:
                self.unity_actions_taken += 1
                return unity_action, sequence.sequence_confidence, sequence.execution_exchange
        
        # Not approved - return HOLD
        return TimelineAction.HOLD, sequence.sequence_confidence, ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMELINE BRANCHING - Create New Futures
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_timeline_branches(
        self, 
        symbol: str, 
        current_price: float,
        volume: float = 0,
        change_pct: float = 0
    ) -> List[TimelineBranch]:
        """
        Create all possible timeline branches from current moment.
        
        Each action (BUY, SELL, HOLD, CONVERT) creates a parallel timeline.
        We validate which one we should be acting out.
        """
        now = time.time()
        target_time = now + (TIMELINE_HORIZON_DAYS * 24 * 3600)  # 7 days ahead
        
        branches = []
        
        for action in [TimelineAction.BUY, TimelineAction.SELL, TimelineAction.HOLD, TimelineAction.CONVERT]:
            # Generate unique branch ID
            branch_hash = hashlib.sha256(
                f"{symbol}:{action.value}:{time.time_ns()}".encode()
            ).hexdigest()[:12]
            branch_id = f"TL-{branch_hash}"
            
            # Create the branch
            branch = TimelineBranch(
                branch_id=branch_id,
                parent_branch_id=self.current_branch_id,
                created_at=now,
                action=action,
                symbol=symbol,
                entry_price=current_price,
                target_time=target_time
            )
            
            # Get quantum vision from all systems
            self._calculate_quantum_vision(branch, current_price, volume, change_pct)
            
            # Calculate combined branch confidence
            branch.branch_confidence = self._calculate_branch_confidence(branch)
            
            branches.append(branch)
            
            # Store in active branches
            with self._lock:
                self.active_branches[branch_id] = branch
                self.branches_created += 1
                
                # Update branch tree
                if self.current_branch_id:
                    if self.current_branch_id not in self.branch_tree:
                        self.branch_tree[self.current_branch_id] = []
                    self.branch_tree[self.current_branch_id].append(branch_id)
        
        # Sort by confidence (highest first)
        branches.sort(key=lambda b: b.branch_confidence, reverse=True)
        
        # Publish best branch if confidence is high enough
        if branches and branches[0].branch_confidence > 0.5:
            self._publish_timeline_prediction(branches[0])
        
        logger.info(f"⏳ Created {len(branches)} timeline branches for {symbol}")
        logger.info(f"   🔮 Best branch: {branches[0].action.value} (conf: {branches[0].branch_confidence:.2%})")
        
        return branches
    
    def _calculate_quantum_vision(
        self, 
        branch: TimelineBranch,
        price: float,
        volume: float,
        change_pct: float
    ):
        """
        Ask all systems what they SEE for this timeline branch.
        
        This is the quantum vision - what WILL happen if we take this path.
        """
        # 🔭 Quantum Telescope - Geometric Refraction
        if self.quantum_prism:
            try:
                beam = LightBeam(
                    symbol=branch.symbol,
                    intensity=volume if volume > 0 else 1000,
                    wavelength=max(0.01, abs(change_pct) if change_pct else 0.01),
                    velocity=change_pct * 100 if change_pct else 0,
                    angle=math.atan2(change_pct, 1) if change_pct else 0,
                    polarization=1.0 if branch.action == TimelineAction.BUY else -1.0 if branch.action == TimelineAction.SELL else 0.0
                )
                refraction = self.quantum_prism.refract(beam)
                
                # Average resonance across all geometric solids
                total_resonance = 0
                for solid, result in refraction.items():
                    branch.telescope_refraction[solid.value] = result.resonance
                    total_resonance += result.resonance * result.clarity
                
                branch.quantum_vision['telescope'] = total_resonance / len(refraction) if refraction else 0.5
            except Exception as e:
                logger.debug(f"Quantum prism error: {e}")
                branch.quantum_vision['telescope'] = 0.5
        
        # 🌊 Harmonic Fusion - Does the 7-day seed support this action?
        if self.harmonic_fusion and hasattr(self.harmonic_fusion, 'state') and self.harmonic_fusion.state:
            try:
                state = self.harmonic_fusion.state
                symbol_state = state.symbols.get(branch.symbol)
                
                if symbol_state:
                    # Check if action aligns with wave phase
                    # BUY at trough (phase near π), SELL at peak (phase near 0 or 2π)
                    phase = symbol_state.phase
                    
                    if branch.action == TimelineAction.BUY:
                        # Buy alignment: best at phase near π (trough)
                        alignment = abs(math.sin(phase))  # High at π
                    elif branch.action == TimelineAction.SELL:
                        # Sell alignment: best at phase near 0 or 2π (peak)
                        alignment = abs(math.cos(phase))  # High at 0, 2π
                    else:
                        # Hold/Convert: best when phase is neutral
                        alignment = 1.0 - abs(math.sin(2 * phase))
                    
                    branch.harmonic_alignment = alignment * symbol_state.coherence
                else:
                    branch.harmonic_alignment = 0.5
            except Exception as e:
                logger.debug(f"Harmonic alignment error: {e}")
                branch.harmonic_alignment = 0.5
        
        # 🍄 Mycelium - Hive Consensus
        if self.mycelium:
            try:
                # Query the hive for consensus on this action
                if hasattr(self.mycelium, 'get_consensus'):
                    consensus = self.mycelium.get_consensus(branch.symbol, branch.action.value)
                    branch.mycelium_consensus = consensus if isinstance(consensus, float) else 0.5
                elif hasattr(self.mycelium, 'queen') and self.mycelium.queen:
                    # Use queen neuron's activation
                    branch.mycelium_consensus = self.mycelium.queen.activation
                else:
                    branch.mycelium_consensus = 0.5
            except Exception as e:
                logger.debug(f"Mycelium consensus error: {e}")
                branch.mycelium_consensus = 0.5
        
        # 🧠 Miner Brain - Critical Speculation
        if self.miner_brain:
            try:
                if hasattr(self.miner_brain, 'speculate'):
                    speculation = self.miner_brain.speculate(branch.symbol, branch.action.value)
                    branch.miner_speculation = speculation.get('confidence', 0.5) if isinstance(speculation, dict) else 0.5
                elif hasattr(self.miner_brain, 'get_market_coherence'):
                    coherence = self.miner_brain.get_market_coherence()
                    branch.miner_speculation = coherence if isinstance(coherence, float) else 0.5
                else:
                    branch.miner_speculation = 0.5
            except Exception as e:
                logger.debug(f"Miner brain error: {e}")
                branch.miner_speculation = 0.5
        
        # 🌌 Multiverse - 10 World Vote
        if self.multiverse:
            try:
                if hasattr(self.multiverse, 'get_consensus'):
                    vote = self.multiverse.get_consensus(branch.symbol)
                    if isinstance(vote, dict):
                        # Check if consensus agrees with our action
                        consensus_action = vote.get('action', 'HOLD')
                        if consensus_action.upper() == branch.action.value.upper():
                            branch.multiverse_vote = vote.get('confidence', 0.7)
                        else:
                            branch.multiverse_vote = 1.0 - vote.get('confidence', 0.5)
                    else:
                        branch.multiverse_vote = 0.5
                else:
                    branch.multiverse_vote = 0.5
            except Exception as e:
                logger.debug(f"Multiverse vote error: {e}")
                branch.multiverse_vote = 0.5
        
        # 💎 Ultimate Intelligence
        if ULTIMATE_INTEL_AVAILABLE and ultimate_predict:
            try:
                prediction = ultimate_predict(branch.symbol)
                if prediction:
                    branch.quantum_vision['ultimate'] = prediction.get('confidence', 0.5) if isinstance(prediction, dict) else 0.5
            except Exception as e:
                logger.debug(f"Ultimate intel error: {e}")
    
    def _calculate_branch_confidence(self, branch: TimelineBranch) -> float:
        """
        Calculate combined confidence for a timeline branch.
        
        This tells us how likely we are to be "acting out the right timeline."
        """
        weights = {
            'harmonic': 0.25,     # 7-day seed is our primary validation
            'mycelium': 0.20,    # Hive intelligence
            'miner': 0.15,       # Critical thinking
            'telescope': 0.20,   # Quantum geometry
            'multiverse': 0.20,  # 10-world consensus
        }
        
        scores = {
            'harmonic': branch.harmonic_alignment,
            'mycelium': branch.mycelium_consensus,
            'miner': branch.miner_speculation,
            'telescope': branch.quantum_vision.get('telescope', 0.5),
            'multiverse': branch.multiverse_vote,
        }
        
        # Weighted average
        total_weight = sum(weights.values())
        confidence = sum(scores[k] * weights[k] for k in weights) / total_weight
        
        # Apply golden ratio threshold boost
        if confidence > BRANCH_CONFIDENCE_THRESHOLD:
            # Above golden ratio = timeline is aligned
            confidence *= 1.0 + (PHI - 1) * 0.1  # ~6% boost
        
        return min(1.0, confidence)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMELINE SELECTION - Choose Which Future to Manifest
    # ═══════════════════════════════════════════════════════════════════════════
    
    def select_timeline(
        self, 
        symbol: str, 
        current_price: float,
        volume: float = 0,
        change_pct: float = 0
    ) -> Tuple[TimelineAction, TimelineBranch]:
        """
        Select the optimal timeline branch to manifest.
        
        This is the key insight: we're not choosing what to DO,
        we're choosing which future has ALREADY happened.
        """
        # Create all possible branches
        branches = self.create_timeline_branches(symbol, current_price, volume, change_pct)
        
        if not branches:
            # Default to HOLD if no branches calculated
            return TimelineAction.HOLD, None
        
        # The best branch is the timeline we should be acting out
        best_branch = branches[0]
        
        # Update current branch (we've jumped to a new timeline)
        self.current_branch_id = best_branch.branch_id
        
        # Publish to thought bus
        if self.thought_bus:
            try:
                self.thought_bus.publish('timeline.selected', {
                    'branch_id': best_branch.branch_id,
                    'symbol': symbol,
                    'action': best_branch.action.value,
                    'confidence': best_branch.branch_confidence,
                    'harmonic_alignment': best_branch.harmonic_alignment,
                    'multiverse_vote': best_branch.multiverse_vote,
                    'target_time': best_branch.target_time,
                    'timestamp': time.time()
                })
            except Exception:
                pass
        
        logger.info(f"⏳🔮 TIMELINE SELECTED: {best_branch.action.value} {symbol}")
        logger.info(f"   Branch ID: {best_branch.branch_id}")
        logger.info(f"   Confidence: {best_branch.branch_confidence:.2%}")
        logger.info(f"   🌊 Harmonic: {best_branch.harmonic_alignment:.2%}")
        logger.info(f"   🌌 Multiverse: {best_branch.multiverse_vote:.2%}")
        logger.info(f"   Target: {datetime.fromtimestamp(best_branch.target_time)}")
        
        return best_branch.action, best_branch
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMELINE VALIDATION - Prove We Were Right
    # ═══════════════════════════════════════════════════════════════════════════
    
    def validate_timeline(
        self, 
        branch_id: str, 
        actual_price: float,
        actual_pnl: float = 0
    ) -> Optional[TimelineValidation]:
        """
        Validate a timeline branch - prove we chose correctly.
        
        This is where we confirm: "Yes, we were just acting out
        what had already come to be."
        """
        with self._lock:
            branch = self.active_branches.get(branch_id)
            if not branch:
                return None
            
            now = time.time()
            
            # Update branch with actual results
            branch.validated = True
            branch.validation_time = now
            branch.actual_price = actual_price
            branch.actual_pnl = actual_pnl
            
            # Calculate if we chose the right timeline
            if branch.action == TimelineAction.BUY:
                branch.timeline_correct = actual_price > branch.entry_price
            elif branch.action == TimelineAction.SELL:
                branch.timeline_correct = actual_price < branch.entry_price
            elif branch.action == TimelineAction.CONVERT:
                branch.timeline_correct = actual_pnl > 0
            else:  # HOLD
                # HOLD is correct if price stayed relatively stable
                change = abs(actual_price - branch.entry_price) / branch.entry_price
                branch.timeline_correct = change < 0.02  # <2% change
            
            # Calculate timeline accuracy
            expected_direction = 1 if branch.action in [TimelineAction.BUY, TimelineAction.CONVERT] else -1
            actual_direction = 1 if actual_price > branch.entry_price else -1
            
            if branch.action == TimelineAction.HOLD:
                timeline_accuracy = 1.0 - min(1.0, abs(actual_price - branch.entry_price) / branch.entry_price / 0.05)
            else:
                timeline_accuracy = 1.0 if expected_direction == actual_direction else 0.0
            
            # Create validation record
            validation = TimelineValidation(
                branch_id=branch_id,
                symbol=branch.symbol,
                action=branch.action,
                entry_price=branch.entry_price,
                entry_time=branch.created_at,
                exit_price=actual_price,
                exit_time=now,
                pnl_usd=actual_pnl,
                pnl_pct=(actual_price - branch.entry_price) / branch.entry_price * 100,
                branch_confidence_at_entry=branch.branch_confidence,
                timeline_accuracy=timeline_accuracy,
                systems_that_agreed=self._get_agreeing_systems(branch)
            )
            
            self._publish_validation(validation)
            
            self.validated_branches.append(validation)
            self.branches_validated += 1
            
            if branch.timeline_correct:
                self.correct_branches += 1
            
            # Update running accuracy
            self.timeline_accuracy = self.correct_branches / max(1, self.branches_validated)
            
            logger.info(f"✅ TIMELINE VALIDATED: {branch_id}")
            logger.info(f"   Correct: {'YES' if branch.timeline_correct else 'NO'}")
            logger.info(f"   Accuracy: {timeline_accuracy:.2%}")
            logger.info(f"   Overall: {self.timeline_accuracy:.2%} ({self.correct_branches}/{self.branches_validated})")
            
            # Remove from active
            del self.active_branches[branch_id]
            
            # Persist state
            self._save_state()
            
            return validation
    
    def _get_agreeing_systems(self, branch: TimelineBranch) -> List[str]:
        """Get list of systems that agreed with this branch (>60% confidence)."""
        agreeing = []
        if branch.harmonic_alignment > 0.6:
            agreeing.append('harmonic')
        if branch.mycelium_consensus > 0.6:
            agreeing.append('mycelium')
        if branch.miner_speculation > 0.6:
            agreeing.append('miner')
        if branch.quantum_vision.get('telescope', 0) > 0.6:
            agreeing.append('telescope')
        if branch.multiverse_vote > 0.6:
            agreeing.append('multiverse')
        return agreeing
    
    def _publish_timeline_prediction(self, branch: TimelineBranch) -> None:
        """Publish timeline prediction to ThoughtBus and ChirpBus."""
        try:
            # 1. ThoughtBus
            if self.thought_bus:
                # ThoughtBus expects a topic + payload (or a Thought dataclass). Keep this
                # compatible with the core ThoughtBus implementation in aureon.core.
                self.thought_bus.publish(
                    "timeline.prediction",
                    {
                        "symbol": branch.symbol,
                        "action": branch.action.value,
                        "confidence": branch.branch_confidence,
                        "branch_id": branch.branch_id,
                        "entry": branch.entry_price,
                        "target_time": branch.target_time,
                    },
                    source="TIMELINE_ORACLE",
                )

            # 2. ChirpBus
            if self.chirp_bus:
                self.chirp_bus.emit_message("timeline.prediction", {
                    "sym": branch.symbol,
                    "act": branch.action.value,
                    "conf": branch.branch_confidence,
                    "id": branch.branch_id
                })
        except Exception as e:
            logger.error(f"Failed to publish timeline prediction: {e}")

    def _publish_validation(self, validation: TimelineValidation) -> None:
        """Publish timeline validation result."""
        try:
            # 1. ThoughtBus
            if self.thought_bus:
                self.thought_bus.publish(
                    "timeline.validation",
                    asdict(validation),
                    source="TIMELINE_ORACLE",
                )

            # 2. ChirpBus
            if self.chirp_bus:
                self.chirp_bus.emit_message("timeline.validation", {
                    "sym": validation.symbol,
                    "pnl": validation.pnl_usd,
                    "acc": validation.timeline_accuracy
                })
        except Exception as e:
            logger.error(f"Failed to publish timeline validation: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # BATCH VALIDATION - Check All Pending Branches
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def validate_all_pending(self, price_feed: Dict[str, float]) -> List[TimelineValidation]:
        """
        Validate all branches whose target time has passed.
        
        Call this periodically to confirm our timeline choices.
        """
        validations = []
        now = time.time()
        
        branches_to_validate = []
        with self._lock:
            for branch_id, branch in list(self.active_branches.items()):
                if now >= branch.target_time:
                    branches_to_validate.append((branch_id, branch))
        
        for branch_id, branch in branches_to_validate:
            actual_price = price_feed.get(branch.symbol, branch.entry_price)
            validation = self.validate_timeline(branch_id, actual_price)
            if validation:
                validations.append(validation)
        
        return validations
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE - Save/Load Timeline State
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_state(self):
        """Save timeline state to disk."""
        try:
            # Save active branches
            branches_data = {k: v.to_dict() for k, v in self.active_branches.items()}
            with open(TIMELINE_BRANCHES_FILE, 'w') as f:
                json.dump(branches_data, f, indent=2)
            
            # Save validations (last 1000)
            validations_data = [v.to_dict() for v in self.validated_branches[-1000:]]
            with open(TIMELINE_VALIDATIONS_FILE, 'w') as f:
                json.dump({
                    'validations': validations_data,
                    'metrics': {
                        'branches_created': self.branches_created,
                        'branches_validated': self.branches_validated,
                        'timeline_accuracy': self.timeline_accuracy,
                        'correct_branches': self.correct_branches
                    }
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save timeline state: {e}")
    
    def _load_state(self):
        """Load timeline state from disk."""
        try:
            if os.path.exists(TIMELINE_VALIDATIONS_FILE):
                with open(TIMELINE_VALIDATIONS_FILE, 'r') as f:
                    data = json.load(f)
                    metrics = data.get('metrics', {})
                    self.branches_created = metrics.get('branches_created', 0)
                    self.branches_validated = metrics.get('branches_validated', 0)
                    self.timeline_accuracy = metrics.get('timeline_accuracy', 0.0)
                    self.correct_branches = metrics.get('correct_branches', 0)
                    logger.info(f"⏳ Loaded timeline history: {self.branches_validated} validated, {self.timeline_accuracy:.1%} accuracy")
        except Exception as e:
            logger.debug(f"No timeline state to load: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS - Get Oracle Status
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the Timeline Oracle."""
        return {
            'current_branch': self.current_branch_id,
            'active_branches': len(self.active_branches),
            'branches_created': self.branches_created,
            'branches_validated': self.branches_validated,
            'timeline_accuracy': self.timeline_accuracy,
            'correct_branches': self.correct_branches,
            'systems_wired': {
                'miner_brain': self.miner_brain is not None,
                'quantum_prism': self.quantum_prism is not None,
                'mycelium': self.mycelium is not None,
                'harmonic_fusion': self.harmonic_fusion is not None,
                'multiverse': self.multiverse is not None
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_oracle_instance: Optional[TimelineOracle] = None

def get_timeline_oracle() -> TimelineOracle:
    """Get or create the global Timeline Oracle instance."""
    global _oracle_instance
    if _oracle_instance is None:
        _oracle_instance = TimelineOracle()
        _oracle_instance.initialize()
    return _oracle_instance


def timeline_select(
    symbol: str,
    price: float,
    volume: float = 0,
    change_pct: float = 0
) -> Tuple[str, float]:
    """
    Quick function to select optimal timeline.
    
    Returns: (action, confidence)
    """
    oracle = get_timeline_oracle()
    action, branch = oracle.select_timeline(symbol, price, volume, change_pct)
    confidence = branch.branch_confidence if branch else 0.5
    return action.value, confidence


def timeline_select_3move(
    symbol: str,
    price: float,
    volume: float = 0,
    change_pct: float = 0
) -> Tuple[str, float, str]:
    """
    🎯 3-MOVE AHEAD PREDICTION with full validation.
    
    "It predicts 3 moves, validates, then acts in that timeline cause it be right"
    
    Returns: (action, confidence, exchange)
    """
    oracle = get_timeline_oracle()
    action, confidence, exchange = oracle.get_approved_action(
        symbol=symbol,
        price=price,
        volume=volume,
        change_pct=change_pct
    )
    
    action_str = action.value if action else 'hold'
    return action_str, confidence, exchange


def timeline_validate(branch_id: str, actual_price: float, actual_pnl: float = 0) -> bool:
    """Quick function to validate a timeline branch."""
    oracle = get_timeline_oracle()
    validation = oracle.validate_timeline(branch_id, actual_price, actual_pnl)
    return validation is not None and validation.timeline_accuracy > 0.5


def timeline_validate_move(sequence_id: str, move_number: int, actual_price: float) -> bool:
    """
    Validate a single move in a 3-move sequence.
    
    Call this when we reach each target time to validate predictions.
    """
    oracle = get_timeline_oracle()
    return oracle.validate_sequence_move(sequence_id, move_number, actual_price)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - Test the Timeline Oracle
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*70)
    print("⏳🔮 AUREON TIMELINE ORACLE - 7-DAY VISION TEST 🔮⏳")
    print("="*70)
    
    oracle = TimelineOracle()
    oracle.initialize()
    
    # Test timeline selection
    print("\n📊 Testing timeline selection for BTC...")
    action, branch = oracle.select_timeline("BTC", 100000.0, volume=1000000, change_pct=0.02)
    
    print(f"\n🔮 Selected Timeline: {action.value}")
    if branch:
        print(f"   Branch ID: {branch.branch_id}")
        print(f"   Confidence: {branch.branch_confidence:.2%}")
        print(f"   🌊 Harmonic: {branch.harmonic_alignment:.2%}")
        print(f"   🍄 Mycelium: {branch.mycelium_consensus:.2%}")
        print(f"   🧠 Miner: {branch.miner_speculation:.2%}")
        print(f"   🔭 Telescope: {branch.quantum_vision.get('telescope', 0):.2%}")
        print(f"   🌌 Multiverse: {branch.multiverse_vote:.2%}")
    
    # Show status
    status = oracle.get_status()
    print(f"\n📈 ORACLE STATUS:")
    print(f"   Active Branches: {status['active_branches']}")
    print(f"   Timeline Accuracy: {status['timeline_accuracy']:.1%}")
    print(f"   Systems Wired: {sum(1 for v in status['systems_wired'].values() if v)}/5")
    
    print("\n" + "="*70)
    print("⏳ 'We're just acting out what has already come to be, mate.' ⏳")
    print("="*70)
