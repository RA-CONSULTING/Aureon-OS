#!/usr/bin/env python3
"""
☘️🔥 IRISH PATRIOT SCOUTS - FORCE SCOUTS WITH CELTIC INTELLIGENCE 🔥☘️
═══════════════════════════════════════════════════════════════════════════════
                        WIRED FOR WAR - TRAINED LIKE TRUE PATRIOTS
═══════════════════════════════════════════════════════════════════════════════

"Give me a scout with Celtic blood and I'll give you an army that never loses."

This module transforms ordinary scouts into Irish Patriots:
- Wired with guerrilla warfare intelligence
- Trained in preemptive strike doctrine
- Connected to multi-battlefront coordination
- United under Celtic command

THE PATRIOT OATH:
═══════════════════════════════════════════════════════════════════════════════
"I am an Irish Patriot Scout.
I serve the portfolio with Celtic fury.
I strike before the market knows I'm coming.
I retreat before the market can respond.
I NEVER surrender a single penny to the enemy.
Tiocfaidh ár lá - Our day will come."

WIRING ARCHITECTURE:
═══════════════════════════════════════════════════════════════════════════════

                    ┌─────────────────────────────────────────┐
                    │         CELTIC WAR COUNCIL              │
                    │    (Central Command & Intelligence)     │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
    ┌─────────▼─────────┐   ┌─────────▼─────────┐   ┌─────────▼─────────┐
    │   GUERRILLA       │   │   PREEMPTIVE      │   │   MULTI-FRONT     │
    │   WARFARE ENGINE  │   │   STRIKE ENGINE   │   │   COORDINATOR     │
    │   (Flying Columns)│   │   (Early Exit)    │   │   (Unity)         │
    └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                    ┌─────────────────▼───────────────────────┐
                    │         PATRIOT SCOUT NETWORK           │
                    │    (Irish-Trained Force Scouts)         │
                    └─────────────────┬───────────────────────┘
                                      │
        ┌─────────────┬───────────────┼───────────────┬─────────────┐
        │             │               │               │             │
   ┌────▼────┐   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
   │ SCOUT 1 │   │ SCOUT 2 │    │ SCOUT 3 │    │ SCOUT 4 │   │ SCOUT N │
   │ Binance │   │ Kraken  │    │ Binance │    │ Capital │   │  ....   │
   │ BTCUSDC │   │ ETHGBP  │    │ SOLUSDT │    │ XAUUSD  │   │         │
   └─────────┘   └─────────┘    └─────────┘    └─────────┘   └─────────┘

Gary Leckey | December 2025
"Turn scouts into warriors, warriors into legends."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import math
import random
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict
from enum import Enum

# =============================================================================
# ☘️ IMPORT CELTIC WARFARE SYSTEMS
# =============================================================================

try:
    from aureon.wisdom.guerrilla_warfare_engine import (
        IntelligenceNetwork, FlyingColumn, BattlefrontStatus,
        TacticalMode, IntelligenceReport, GUERRILLA_CONFIG, get_celtic_wisdom
    )
    GUERRILLA_ENGINE_AVAILABLE = True
except ImportError:
    print("⚠️ Guerrilla Warfare Engine not available - Patriots running in basic mode")
    GUERRILLA_ENGINE_AVAILABLE = False

# 🎯⏱️ ETA VERIFICATION SYSTEM - Track and verify kill predictions
try:
    from aureon.analytics.eta_verification_system import (
        get_eta_verifier, register_eta, verify_kill as eta_verify_kill,
        check_expired, get_corrected_eta, ETAOutcome
    )
    ETA_VERIFICATION_AVAILABLE = True
    print("🎯⏱️ ETA Verification System WIRED to Patriots!")
except ImportError:
    ETA_VERIFICATION_AVAILABLE = False
    print("⚠️ ETA Verification System not available - Patriots running without prediction tracking")

# 🔬 IMPROVED ETA CALCULATOR - Fixes naive velocity decay assumptions
try:
    from aureon.analytics.improved_eta_calculator import ImprovedETACalculator, ImprovedETA
    IMPROVED_ETA_AVAILABLE = True
    IMPROVED_ETA_CALC = ImprovedETACalculator()
    print("🔬 Improved ETA Calculator WIRED to Patriots! (velocity decay model)")
except ImportError:
    IMPROVED_ETA_AVAILABLE = False
    IMPROVED_ETA_CALC = None
    print("⚠️ Improved ETA Calculator not available - using naive ETA")

try:
    from aureon.wisdom.celtic_preemptive_strike import (
        PreemptiveExitEngine, DawnRaidDetector, 
        PreemptiveSignal, PreemptiveSignalType
    )
    PREEMPTIVE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Preemptive Strike Engine not available - Patriots running without early exit: {e}")
    PREEMPTIVE_AVAILABLE = False

# 🧠 PROBABILITY INTELLIGENCE MATRIX - Stops Mistakes Before They Happen
try:
    from aureon.strategies.probability_intelligence_matrix import (
        get_probability_matrix, calculate_intelligent_probability,
        record_outcome as prob_record_outcome, ProbabilityIntelligence
    )
    PROBABILITY_MATRIX_AVAILABLE = True
    PROB_MATRIX = get_probability_matrix()
    print("🧠 Probability Intelligence Matrix WIRED to Patriots! (prevents bad trades)")
except ImportError:
    PROBABILITY_MATRIX_AVAILABLE = False
    PROB_MATRIX = None
    print("⚠️ Probability Intelligence Matrix not available for Patriots")

# 💎 PROBABILITY ULTIMATE INTELLIGENCE - 95% Accuracy Pattern Learning
try:
    from aureon.strategies.probability_ultimate_intelligence import (
        get_ultimate_intelligence, ultimate_predict, record_ultimate_outcome,
        UltimatePrediction
    )
    ULTIMATE_INTELLIGENCE_AVAILABLE = True
    ULTIMATE_INTEL = get_ultimate_intelligence()
    print("💎 Probability Ultimate Intelligence WIRED to Patriots! (95% accuracy)")
except ImportError:
    ULTIMATE_INTELLIGENCE_AVAILABLE = False
    ULTIMATE_INTEL = None
    print("⚠️ Ultimate Intelligence not available for Patriots")

# 🌍🍄 AUREON ULTIMATE ECOSYSTEM - Lazy load to avoid circular import
# aureon_ultimate_ecosystem_wiring imports irish_patriot_scouts
ECOSYSTEM_AVAILABLE = False
_ECOSYSTEM_INSTANCE = None

def _get_ecosystem():
    """Lazy load ecosystem to avoid circular import"""
    global _ECOSYSTEM_INSTANCE, ECOSYSTEM_AVAILABLE
    if _ECOSYSTEM_INSTANCE is None:
        try:
            from aureon.trading.aureon_ultimate_ecosystem_wiring import get_ultimate_ecosystem
            _ECOSYSTEM_INSTANCE = get_ultimate_ecosystem()
            ECOSYSTEM_AVAILABLE = True
        except ImportError:
            pass
    return _ECOSYSTEM_INSTANCE

def ecosystem_predict(*args, **kwargs):
    """Lazy wrapper for ecosystem predict"""
    try:
        from aureon.trading.aureon_ultimate_ecosystem_wiring import ecosystem_predict as _eco_predict
        return _eco_predict(*args, **kwargs)
    except ImportError:
        return None

def ecosystem_record_outcome(*args, **kwargs):
    """Lazy wrapper for ecosystem record outcome"""
    try:
        from aureon.trading.aureon_ultimate_ecosystem_wiring import ecosystem_record_outcome as _eco_record
        return _eco_record(*args, **kwargs)
    except ImportError:
        pass

# Ultimate Ecosystem availability will be checked lazily to avoid circular imports
ECOSYSTEM_AVAILABLE = None

def _check_ecosystem():
    """Check ecosystem availability lazily."""
    global ECOSYSTEM_AVAILABLE
    if ECOSYSTEM_AVAILABLE is None:
        try:
            from aureon.trading.aureon_ultimate_ecosystem_wiring import get_ultimate_ecosystem
            _test_eco = get_ultimate_ecosystem()
            ECOSYSTEM_AVAILABLE = True
        except ImportError:
            ECOSYSTEM_AVAILABLE = False
    return ECOSYSTEM_AVAILABLE

try:
    from aureon.wisdom.multi_battlefront_coordinator import (
        MultiBattlefrontWarRoom, CampaignPhase, ArbitrageOpportunity
    )
    COORDINATOR_AVAILABLE = True
except ImportError:
    print("⚠️ Multi-Battlefront Coordinator not available - Patriots running independently")
    COORDINATOR_AVAILABLE = False

# Try to import existing systems for integration
# NOTE: IRA Sniper import moved to lazy loading to avoid circular import
# ira_sniper_mode.py imports PatriotScoutNetwork from this file
IRA_SNIPER_MODE = None
IRA_SNIPER_AVAILABLE = False

def _get_ira_sniper():
    """Lazy load IRA Sniper to avoid circular import"""
    global IRA_SNIPER_MODE, IRA_SNIPER_AVAILABLE
    if IRA_SNIPER_MODE is None and not IRA_SNIPER_AVAILABLE:
        try:
            from aureon.scanners.ira_sniper_mode import IRA_SNIPER_MODE as sniper
            IRA_SNIPER_MODE = sniper
            IRA_SNIPER_AVAILABLE = True
        except ImportError:
            pass
    return IRA_SNIPER_MODE

try:
    from aureon.trading.penny_profit_engine import get_penny_engine, check_penny_exit
    PENNY_ENGINE_AVAILABLE = True
except ImportError:
    PENNY_ENGINE_AVAILABLE = False

try:
    from aureon.command_centers.war_strategy import WarStrategy
    WAR_STRATEGY_AVAILABLE = True
    # Initialize global war strategist
    _GLOBAL_WAR_STRATEGIST = WarStrategy()
except ImportError:
    WAR_STRATEGY_AVAILABLE = False
    _GLOBAL_WAR_STRATEGIST = None


# =============================================================================
# 🏛️ PATRIOT SCOUT CONFIGURATION
# =============================================================================

PATRIOT_CONFIG = {
    # ═══════════════════════════════════════════════════════════════════════
    # ☘️ IRISH PATRIOT IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    'PATRIOT_NAME_PREFIX': 'IRA',          # Irish Patriot prefix
    'PATRIOT_CODENAMES': [
        'Wolfhound', 'Banshee', 'Leprechaun', 'Selkie', 'Pooka',
        'Clurichaun', 'Dullahan', 'Changeling', 'Merrow', 'Sidhe',
        'Collins', 'Boru', 'Cuchulainn', 'Fionn', 'Granuaile',
        'Pearse', 'Connolly', 'Markievicz', 'deValera', 'Sands'
    ],
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎯 SCOUT MISSION PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════
    'SCOUT_SIZE_USD': 10.0,               # $10 flying column
    'MAX_SCOUTS_PER_EXCHANGE': 5,         # 5 patriots per battlefront
    'MAX_TOTAL_SCOUTS': 15,               # 15 total patriots
    'SCOUT_DEPLOYMENT_INTERVAL_SEC': 0.5, # Deploy fast like Collins
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🧠 INTELLIGENCE WIRING
    # ═══════════════════════════════════════════════════════════════════════
    'WIRE_GUERRILLA_ENGINE': True,        # Connect to guerrilla warfare
    'WIRE_PREEMPTIVE_STRIKE': True,       # Connect to preemptive exits
    'WIRE_MULTI_BATTLEFRONT': True,       # Connect to coordination
    'WIRE_PENNY_PROFIT': True,            # Connect to penny profit
    'WIRE_WAR_STRATEGY': True,            # Connect to war strategy
    
    # ═══════════════════════════════════════════════════════════════════════
    # ⚔️ ENGAGEMENT RULES
    # ═══════════════════════════════════════════════════════════════════════
    'MIN_AMBUSH_SCORE': 0.35,             # Lower threshold - scouts are BRAVE!
    'MIN_QUICK_KILL_PROB': 0.30,          # 30% quick kill or don't engage
    'MAX_TIME_IN_POSITION_SEC': 300,      # 5 min max exposure
    'PREEMPTIVE_EXIT_ENABLED': True,      # Exit before reversal completes
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🏃 RETREAT PROTOCOL
    # ═══════════════════════════════════════════════════════════════════════
    'AUTO_RETREAT_ON_LOSS': True,         # Never accept loss
    'RETREAT_THRESHOLD_PCT': -0.1,        # Retreat at -0.1%
    'COORDINATE_RETREAT': True,           # All scouts retreat together
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎖️ VICTORY CONDITIONS - 🚀 COMPOUND MODE: ANY PROFIT COMPOUNDS!
    # ═══════════════════════════════════════════════════════════════════════
    'PENNY_PROFIT_TARGET': 0.0,           # 🚀 COMPOUND MODE: $0 minimum - take ANY profit!
    'USE_DYNAMIC_PENNY_MATH': True,       # 🚀 Use ecosystem penny threshold
    'INSTANT_VICTORY_EXIT': True,         # Exit immediately on ANY profit
    'CELEBRATE_KILLS': True,              # Celebrate like Irish
}


# =============================================================================
# 📜 PATRIOT WISDOM - SAYINGS OF THE IRISH SCOUTS
# =============================================================================

PATRIOT_WISDOM = [
    # Historical Irish
    "Tiocfaidh ár lá - Our day will come",
    "Níl neart go cur le chéile - Unity is strength",
    "Sinn Féin Amháin - Ourselves Alone",
    "Éirinn go Brách - Ireland Forever",
    
    # Scout Doctrine
    "A scout sees all, fears nothing",
    "Report first, engage second, profit always",
    "The unseen scout is the undefeated scout",
    "Intelligence is the sword, patience is the shield",
    "We are the eyes of the Celtic war machine",
    
    # Battle Wisdom
    "One penny at a time builds empires",
    "Move like mist, strike like thunder",
    "They have algorithms, we have ancestors",
    "The market sleeps, but patriots never rest",
    "Every kill is a victory for Ireland",
    
    # Unity
    "Divided we're traders, united we're unstoppable",
    "What one scout knows, all scouts know",
    "The network is stronger than any single node",
    "Signal to your brothers, they will follow",
    "From atom to multiverse - WE DON'T QUIT!",
]

def get_patriot_wisdom() -> str:
    """Get a piece of Irish Patriot wisdom"""
    return random.choice(PATRIOT_WISDOM)


# =============================================================================
# 🎖️ PATRIOT SCOUT CLASS - THE IRISH WARRIOR
# =============================================================================

@dataclass
class PatriotScout:
    """
    An Irish Patriot Scout - trained in Celtic warfare.
    
    This is not just a position - this is a WARRIOR.
    Wired with intelligence, trained for preemptive action,
    united with brothers across all battlefronts.
    
    🎯⚡ ACTIVE KILL SCANNER INTEGRATION ⚡🎯
    Now includes same capabilities as IRA Sniper:
    - P&L velocity tracking ($/second toward profit)
    - Momentum scoring (-1 to +1)
    - ETA to kill prediction
    - Probability of kill calculation
    - Cascade amplification (up to 10x)
    - Adaptive learning from kills
    """
    # Identity
    scout_id: str
    codename: str
    exchange: str
    symbol: str
    
    # Position details
    entry_price: float = 0.0
    entry_time: float = 0.0
    position_size: float = 0.0
    entry_value_usd: float = 0.0
    
    # Celtic warfare state
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    cycles_held: int = 0
    status: str = "ready"  # ready, deployed, engaged, retreating, victorious
    
    # Intelligence wiring
    intelligence_report: Optional[Any] = None
    preemptive_signal: Optional[Any] = None
    ambush_score: float = 0.0
    quick_kill_probability: float = 0.0
    
    # Tactical state
    momentum_at_entry: float = 0.0
    peak_pnl: float = 0.0
    min_pnl: float = 0.0
    target_profit_usd: float = 0.0
    
    # Performance tracking
    kills: int = 0
    total_profit: float = 0.0
    battles_fought: int = 0
    
    # 🎯⚡ ACTIVE KILL SCANNER STATE ⚡🎯
    pnl_history: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, pnl)
    pnl_velocity: float = 0.0              # $/second - positive means approaching kill
    momentum_score: float = 0.0            # -1 to +1, current momentum
    eta_to_kill: float = float('inf')      # Estimated seconds to hit threshold
    probability_of_kill: float = 0.0       # 0-1 probability we'll hit target
    scans: int = 0                         # Number of price scans
    last_scan_time: float = 0.0            # Last scan timestamp
    
    # ⛏️ CASCADE AMPLIFIER STATE ⛏️
    cascade_factor: float = 1.0            # From miner (up to 10x)
    kappa_t: float = 1.0                   # κt efficiency (up to 2.49x)
    lighthouse_gamma: float = 0.5          # Planetary coherence
    consecutive_kills: int = 0             # Kill streak
    
    # 🎯⏱️ ETA VERIFICATION STATE
    eta_prediction_id: Optional[str] = None  # Registered prediction ID
    eta_registered: bool = False             # Has ETA been registered?
    eta_corrected: float = float('inf')      # Corrected ETA after learning
    eta_confidence: float = 0.0              # Confidence in prediction
    eta_model: str = "naive"                 # Model used (naive, velocity_decay, etc.)
    
    # 🧠 PROBABILITY INTELLIGENCE MATRIX STATE
    prob_intel: Optional[Any] = None         # Full intelligence object
    risk_flags: List[str] = field(default_factory=list)  # Active risk flags
    prob_action: str = "HOLD"                # Recommended action
    
    def get_battle_cry(self) -> str:
        """Generate a battle cry for this patriot"""
        cries = [
            f"☘️ {self.codename} engaging on {self.exchange}! Tiocfaidh ár lá!",
            f"⚔️ Patriot {self.codename} deployed! {self.symbol} is our target!",
            f"🔥 {self.codename} moving in! Collins would be proud!",
            f"🇮🇪 {self.codename} on station! Ireland watches!",
            f"💚 Flying column {self.codename} ready! Strike fast, vanish faster!",
        ]
        return random.choice(cries)
    
    def get_victory_cry(self, profit: float) -> str:
        """Generate a victory cry after successful kill"""
        cries = [
            f"🏆 {self.codename} VICTORIOUS! +${profit:.4f} for Ireland!",
            f"☘️ {self.codename} KILL CONFIRMED! Another penny for the cause!",
            f"⚔️ VICTORY! {self.codename} extracts +${profit:.4f}! Éirinn go Brách!",
            f"🇮🇪 {self.codename} mission complete! +${profit:.4f} secured!",
            f"🔥 KILL #{self.kills}! {self.codename} unstoppable! +${profit:.4f}!",
        ]
        return random.choice(cries)
    
    def get_retreat_cry(self) -> str:
        """Generate a retreat cry (strategic withdrawal)"""
        cries = [
            f"🏃 {self.codename} executing tactical withdrawal! Live to fight again!",
            f"☘️ {self.codename} retreating! No surrender of capital!",
            f"⚔️ Strategic retreat by {self.codename}! The war continues!",
            f"🇮🇪 {self.codename} disengaging! Better position awaits!",
        ]
        return random.choice(cries)
    
    def update_price(self, price: float):
        """
        Update current price and recalculate P&L.
        
        🎯⚡ NOW WITH ACTIVE KILL SCANNER ⚡🎯
        Tracks P&L velocity, momentum, and ETA to kill.
        """
        now = time.time()
        self.current_price = price
        self.scans += 1
        self.last_scan_time = now
        
        if self.entry_price > 0 and self.position_size > 0:
            current_value = self.position_size * price
            self.unrealized_pnl = current_value - self.entry_value_usd
            self.peak_pnl = max(self.peak_pnl, self.unrealized_pnl)
            self.min_pnl = min(self.min_pnl, self.unrealized_pnl)
            
            # 🎯 Track P&L history for velocity calculation (keep last 10)
            self.pnl_history.append((now, self.unrealized_pnl))
            if len(self.pnl_history) > 10:
                self.pnl_history.pop(0)
            
            # 🎯 Calculate P&L velocity (change per second)
            if len(self.pnl_history) >= 2:
                oldest = self.pnl_history[0]
                newest = self.pnl_history[-1]
                time_diff = newest[0] - oldest[0]
                if time_diff > 0:
                    self.pnl_velocity = (newest[1] - oldest[1]) / time_diff
            
            # 🎯 Calculate momentum score (-1 to +1)
            if self.pnl_velocity > 0:
                self.momentum_score = min(1.0, self.pnl_velocity / 0.01)
            else:
                self.momentum_score = max(-1.0, self.pnl_velocity / 0.01)
            
            # ═══════════════════════════════════════════════════════════════════
            # 🔬 IMPROVED ETA CALCULATION - Uses velocity decay model
            # ═══════════════════════════════════════════════════════════════════
            gap_to_kill = self.target_profit_usd - self.unrealized_pnl
            
            # Store naive ETA for comparison/fallback
            naive_eta = float('inf')
            if self.pnl_velocity > 0 and gap_to_kill > 0:
                naive_eta = gap_to_kill / self.pnl_velocity
            elif gap_to_kill <= 0:
                naive_eta = 0  # Ready NOW!
            
            # Use IMPROVED ETA calculator if available
            improved_eta_result = None
            if IMPROVED_ETA_AVAILABLE and len(self.pnl_history) >= 3 and gap_to_kill > 0:
                try:
                    improved_eta_result = IMPROVED_ETA_CALC.calculate_eta(
                        current_pnl=self.unrealized_pnl,
                        target_pnl=self.target_profit_usd,
                        pnl_history=self.pnl_history
                    )
                    
                    # Use improved ETA with confidence weighting
                    if improved_eta_result.improved_eta < float('inf'):
                        # Blend naive and improved based on confidence
                        confidence = improved_eta_result.confidence
                        self.eta_to_kill = (
                            confidence * improved_eta_result.improved_eta + 
                            (1 - confidence) * naive_eta
                        ) if naive_eta < float('inf') else improved_eta_result.improved_eta
                        
                        # Store extra metrics
                        self.eta_confidence = confidence
                        self.eta_model = improved_eta_result.model_used
                        
                        # Adjust momentum if decelerating
                        if improved_eta_result.acceleration < -0.00001:
                            self.momentum_score *= max(0.3, 1 + improved_eta_result.acceleration * 1000)
                    else:
                        self.eta_to_kill = float('inf')
                        self.eta_confidence = improved_eta_result.confidence
                except Exception as e:
                    # Fall back to naive
                    self.eta_to_kill = naive_eta
            else:
                # Use naive ETA (not enough history for improved)
                self.eta_to_kill = naive_eta
            
            # 🎯⏱️ ETA VERIFICATION - Register prediction for tracking
            if ETA_VERIFICATION_AVAILABLE and self.eta_to_kill < float('inf') and self.eta_to_kill > 0:
                self._register_eta_prediction()
            
            # 🎯 Calculate probability of kill with cascade boost
            self._calculate_kill_probability()
    
    def _register_eta_prediction(self):
        """🎯⏱️ Register ETA prediction with verification system."""
        try:
            verifier = get_eta_verifier()
            
            proximity = self.unrealized_pnl / self.target_profit_usd if self.target_profit_usd > 0 else 0
            
            # Get confidence and corrected ETA
            confidence = verifier.get_prediction_confidence(
                self.momentum_score, self.pnl_velocity, proximity, self.cascade_factor
            )
            corrected_eta = verifier.get_corrected_eta(
                self.eta_to_kill, self.momentum_score, self.pnl_velocity, confidence
            )
            
            self.eta_corrected = corrected_eta
            self.eta_confidence = confidence
            
            # Only register if not already registered or ETA changed significantly
            should_register = (
                not self.eta_registered or
                abs(corrected_eta - self.eta_to_kill) > self.eta_to_kill * 0.3
            )
            
            if should_register:
                self.eta_prediction_id = verifier.register_eta_prediction(
                    symbol=self.symbol,
                    exchange=self.exchange,
                    eta_seconds=corrected_eta,
                    current_pnl=self.unrealized_pnl,
                    target_pnl=self.target_profit_usd,
                    pnl_velocity=self.pnl_velocity,
                    momentum_score=self.momentum_score,
                    cascade_factor=self.cascade_factor,
                    confidence=confidence
                )
                self.eta_registered = True
            else:
                # Update state for existing prediction
                verifier.update_prediction_state(
                    self.symbol, self.exchange,
                    self.unrealized_pnl, self.pnl_velocity, self.momentum_score
                )
        except Exception:
            pass  # Don't let verification errors affect trading
    
    def _calculate_kill_probability(self):
        """
        🎯 Calculate probability of hitting profit target.
        🧠 Uses PROBABILITY INTELLIGENCE MATRIX to stop mistakes before they happen.
        """
        if self.target_profit_usd <= 0:
            self.probability_of_kill = 0.0
            return
        
        # 🧠 PROBABILITY INTELLIGENCE MATRIX - Enhanced probability with risk detection
        self.prob_intel = None
        if PROBABILITY_MATRIX_AVAILABLE and len(self.pnl_history) >= 2:
            try:
                self.prob_intel = PROB_MATRIX.calculate_intelligent_probability(
                    current_pnl=self.unrealized_pnl,
                    target_pnl=self.target_profit_usd,
                    pnl_history=self.pnl_history,
                    momentum_score=self.momentum_score,
                    cascade_factor=self.cascade_factor,
                    kappa_t=self.kappa_t,
                    lighthouse_gamma=self.lighthouse_gamma
                )
                
                # Store intelligence for analysis
                self.risk_flags = self.prob_intel.risk_flags
                self.prob_action = self.prob_intel.action
                
                # Use adjusted probability from intelligence matrix
                self.probability_of_kill = self.prob_intel.adjusted_probability
                
                # Log warnings for dangerous patterns
                if self.prob_intel.action in ["CAUTION", "DANGER"]:
                    print(f"   ⚠️ {self.codename}: {self.prob_intel.action} - Risks: {self.prob_intel.risk_flags}")
                
                return  # Intelligence matrix handled probability
                
            except Exception:
                pass  # Fall back to legacy
        
        # LEGACY: Base probability from proximity
        proximity = self.unrealized_pnl / self.target_profit_usd
        proximity = max(0, min(1, proximity))
        
        # Momentum factor
        if self.momentum_score > 0:
            base_prob = proximity * (0.5 + 0.5 * self.momentum_score)
        else:
            base_prob = proximity * (0.5 + 0.5 * self.momentum_score)
        
        # ⛏️ CASCADE AMPLIFICATION
        cascade_mult = self._get_cascade_multiplier()
        
        self.probability_of_kill = max(0, min(1, base_prob * cascade_mult))
    
    def _get_cascade_multiplier(self) -> float:
        """
        ⛏️ Calculate cascade multiplier for probability boost.
        Same formula as IRA Sniper: CASCADE × κt × Lighthouse
        """
        cascade_mult = 1.0 + (self.cascade_factor - 1.0) * 0.3
        kappa_mult = 1.0 + (self.kappa_t - 1.0) * 0.2
        lighthouse_mult = 1.0
        if self.lighthouse_gamma >= 0.75:
            lighthouse_mult = 1.0 + (self.lighthouse_gamma - 0.75) * 0.4
        return min(3.0, cascade_mult * kappa_mult * lighthouse_mult)
    
    def sync_cascade(self, cascade_factor: float, kappa_t: float, lighthouse_gamma: float):
        """
        ⛏️ MINER SYNC: Import cascade state from ecosystem.
        """
        self.cascade_factor = cascade_factor
        self.kappa_t = kappa_t
        self.lighthouse_gamma = lighthouse_gamma
    
    def should_exit(self) -> Tuple[bool, str]:
        """
        Determine if scout should exit position.
        Uses ALL Celtic warfare intelligence.
        🪙 SHARED GOAL: Only exit on NET PENNY PROFIT after fees.
        """
        reasons = []
        
        # 1. 🪙 SHARED GOAL: PENNY PROFIT VICTORY (Dynamic calculation)
        if PATRIOT_CONFIG['INSTANT_VICTORY_EXIT']:
            # Use dynamic ecosystem penny math if available; otherwise fall back to penny_profit_engine.
            # IMPORTANT: `unrealized_pnl` is a gross P&L figure, so the target must be a gross threshold.
            target_gross = None
            approx_cost = 0.0

            if PATRIOT_CONFIG.get('USE_DYNAMIC_PENNY_MATH', True):
                try:
                    from aureon.trading.aureon_unified_ecosystem import get_penny_threshold
                    penny = get_penny_threshold(self.exchange, self.entry_value_usd)
                    if penny:
                        target_gross = float(penny.get('win_gte', 0) or 0)
                        approx_cost = float(penny.get('cost', 0) or 0)
                except ImportError:
                    pass

            if target_gross is None and PENNY_ENGINE_AVAILABLE:
                try:
                    threshold = get_penny_engine().get_threshold(self.exchange, self.entry_value_usd)
                    target_gross = float(threshold.win_gte)
                    approx_cost = float(threshold.total_cost)
                except Exception:
                    target_gross = None

            if target_gross is None:
                # Last-resort fallback (treat config as gross)
                target_gross = float(PATRIOT_CONFIG.get('PENNY_PROFIT_TARGET', 0.01) or 0.01)

            if self.unrealized_pnl >= target_gross:
                approx_net = self.unrealized_pnl - approx_cost
                return True, f"🪙 SHARED GOAL! gross +${self.unrealized_pnl:.4f} >= ${target_gross:.4f} (≈net +${approx_net:.4f})"
        
        # 2. PREEMPTIVE EXIT SIGNAL
        if self.preemptive_signal and PATRIOT_CONFIG['PREEMPTIVE_EXIT_ENABLED']:
            if hasattr(self.preemptive_signal, 'signal_type'):
                if self.preemptive_signal.signal_type in ['EXIT', 'URGENT_EXIT']:
                    return True, f"PREEMPTIVE: {self.preemptive_signal.reason}"
        
        # 3. TIME LIMIT
        if self.entry_time > 0:
            time_held = time.time() - self.entry_time
            max_time = PATRIOT_CONFIG.get('MAX_TIME_IN_POSITION_SEC', 300)
            if time_held > max_time:
                return True, f"TIME LIMIT: {time_held:.0f}s > {max_time}s"
        
        # 4. RETREAT THRESHOLD
        if PATRIOT_CONFIG['AUTO_RETREAT_ON_LOSS']:
            threshold = PATRIOT_CONFIG.get('RETREAT_THRESHOLD_PCT', -0.1)
            if self.entry_value_usd > 0:
                pnl_pct = (self.unrealized_pnl / self.entry_value_usd) * 100
                if pnl_pct < threshold:
                    return True, f"RETREAT: {pnl_pct:.2f}% < {threshold}%"
        
        # 5. INTELLIGENCE SAYS EXIT
        if self.intelligence_report:
            report = self.intelligence_report
            if hasattr(report, 'trend_direction'):
                # Exit if momentum reversed against us
                if report.trend_direction == "bearish" and self.unrealized_pnl < 0:
                    return True, f"INTEL: Bearish trend + negative P&L"
        
        return False, ""


# =============================================================================
# 🏛️ PATRIOT SCOUT NETWORK - THE IRISH ARMY
# =============================================================================

class PatriotScoutNetwork:
    """
    The unified network of Irish Patriot Scouts.
    
    All scouts wired together, sharing intelligence,
    coordinating strikes, united under Celtic command.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.scouts: Dict[str, PatriotScout] = {}
        self.scout_counter = 0
        
        # Celtic warfare components
        self.intelligence_network: Optional[IntelligenceNetwork] = None
        self.preemptive_engine: Optional[PreemptiveExitEngine] = None
        self.war_room: Optional[MultiBattlefrontWarRoom] = None
        self.war_strategist: Optional[Any] = None
        
        # Statistics
        self.total_kills = 0
        self.total_profit = 0.0
        self.total_battles = 0
        self.active_scouts = 0
        self.victories = 0
        self.retreats = 0
        
        # 🧠 ADAPTIVE LEARNING STATE - Same as IRA Sniper
        self.kill_history: List[Dict] = []  # Historical kills for learning
        self.avg_kill_time: float = 30.0    # Average seconds to kill
        self.avg_kill_velocity: float = 0.002  # Average $/s at kill time
        self.momentum_success_rate: Dict[str, float] = {}  # Momentum band -> success rate
        
        # ⛏️ CASCADE AMPLIFIER STATE - Synced from ecosystem
        self.cascade_factor: float = 1.0
        self.kappa_t: float = 1.0
        self.lighthouse_gamma: float = 0.5
        self.consecutive_kills: int = 0
        
        # Load learned state
        self._load_learned_state()
        
        # Initialize Celtic warfare systems
        self._wire_celtic_systems()
        
        print("\n" + "=" * 70)
        print("☘️🔥 IRISH PATRIOT SCOUT NETWORK INITIALIZED 🔥☘️")
        print("=" * 70)
        print(f"   🎯 Mode: {'DRY RUN' if dry_run else '🔥 LIVE COMBAT 🔥'}")
        print(f"   🧠 Guerrilla Engine: {'✅ WIRED' if self.intelligence_network else '❌'}")
        print(f"   ⚡ Preemptive Strike: {'✅ WIRED' if self.preemptive_engine else '❌'}")
        print(f"   🌐 Multi-Battlefront: {'✅ WIRED' if self.war_room else '❌'}")
        print(f"   ⚔️ War Strategy: {'✅ WIRED' if self.war_strategist else '❌'}")
        print("=" * 70)
        print(f"   📜 \"{get_patriot_wisdom()}\"")
        print("=" * 70 + "\n")
    
    def _wire_celtic_systems(self):
        """Wire up all Celtic warfare systems"""
        
        # Wire Guerrilla Engine
        if PATRIOT_CONFIG['WIRE_GUERRILLA_ENGINE'] and GUERRILLA_ENGINE_AVAILABLE:
            try:
                self.intelligence_network = IntelligenceNetwork()
                print("   ✅ Intelligence Network WIRED")
            except Exception as e:
                print(f"   ⚠️ Intelligence Network wire failed: {e}")
        
        # Wire Preemptive Strike
        if PATRIOT_CONFIG['WIRE_PREEMPTIVE_STRIKE'] and PREEMPTIVE_AVAILABLE:
            try:
                self.preemptive_engine = PreemptiveExitEngine()
                print("   ✅ Preemptive Strike Engine WIRED")
            except Exception as e:
                print(f"   ⚠️ Preemptive Strike wire failed: {e}")
        
        # Wire Multi-Battlefront Coordinator
        if PATRIOT_CONFIG['WIRE_MULTI_BATTLEFRONT'] and COORDINATOR_AVAILABLE:
            try:
                self.war_room = MultiBattlefrontWarRoom()
                print("   ✅ Multi-Battlefront War Room WIRED")
            except Exception as e:
                print(f"   ⚠️ War Room wire failed: {e}")
        
        # Wire War Strategy
        if PATRIOT_CONFIG['WIRE_WAR_STRATEGY'] and WAR_STRATEGY_AVAILABLE:
            try:
                if _GLOBAL_WAR_STRATEGIST:
                    self.war_strategist = _GLOBAL_WAR_STRATEGIST
                else:
                    self.war_strategist = WarStrategy()
                print("   ✅ War Strategist WIRED")
            except Exception as e:
                print(f"   ⚠️ War Strategist wire failed: {e}")
                self.war_strategist = None
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🧠 ADAPTIVE LEARNING METHODS - Same as IRA Sniper
    # ═══════════════════════════════════════════════════════════════════════
    
    def _load_learned_state(self):
        """Load learned parameters from adaptive learning history."""
        try:
            history_file = 'adaptive_learning_history.json'
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    data = json.load(f)
                
                # Extract patriot-specific learning
                patriot_data = data.get('patriot_learning', {})
                self.avg_kill_time = patriot_data.get('avg_kill_time', 30.0)
                self.avg_kill_velocity = patriot_data.get('avg_kill_velocity', 0.002)
                self.momentum_success_rate = patriot_data.get('momentum_success_rate', {})
                self.kill_history = patriot_data.get('kill_history', [])[-100:]
                
                # Get cascade state
                cascade_data = data.get('cascade_state', {})
                self.cascade_factor = cascade_data.get('cascade_factor', 1.0)
                self.kappa_t = cascade_data.get('kappa_t', 1.0)
                self.lighthouse_gamma = cascade_data.get('lighthouse_gamma', 0.5)
                
                print(f"   🧠 Loaded learning: avg_kill={self.avg_kill_time:.0f}s CASCADE={self.cascade_factor:.1f}x")
        except Exception:
            pass  # Use defaults
    
    def _save_learned_state(self):
        """Save learned parameters to adaptive learning history."""
        try:
            history_file = 'adaptive_learning_history.json'
            data = {}
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    data = json.load(f)
            
            data['patriot_learning'] = {
                'avg_kill_time': self.avg_kill_time,
                'avg_kill_velocity': self.avg_kill_velocity,
                'momentum_success_rate': self.momentum_success_rate,
                'total_kills': self.total_kills,
                'total_profit': self.total_profit,
                'kill_history': self.kill_history[-100:],
            }
            
            data['cascade_state'] = {
                'cascade_factor': self.cascade_factor,
                'kappa_t': self.kappa_t,
                'lighthouse_gamma': self.lighthouse_gamma,
                'consecutive_kills': self.consecutive_kills,
            }
            
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    def _learn_from_kill(self, scout: PatriotScout, net_pnl: float, hold_time: float):
        """🧠 ADAPTIVE LEARNING: Record kill data and update predictions."""
        kill_record = {
            'codename': scout.codename,
            'symbol': scout.symbol,
            'exchange': scout.exchange,
            'hold_time': hold_time,
            'net_pnl': net_pnl,
            'final_velocity': scout.pnl_velocity,
            'final_momentum': scout.momentum_score,
            'scans': scout.scans,
            'entry_value': scout.entry_value_usd,
            'timestamp': time.time(),
        }
        self.kill_history.append(kill_record)
        
        alpha = 0.1
        self.avg_kill_time = (1 - alpha) * self.avg_kill_time + alpha * hold_time
        
        if scout.pnl_velocity > 0:
            self.avg_kill_velocity = (1 - alpha) * self.avg_kill_velocity + alpha * scout.pnl_velocity
        
        momentum_band = self._get_momentum_band(scout.momentum_score)
        if momentum_band not in self.momentum_success_rate:
            self.momentum_success_rate[momentum_band] = 0.5
        
        success = 1.0 if net_pnl > 0 else 0.0
        current_rate = self.momentum_success_rate[momentum_band]
        self.momentum_success_rate[momentum_band] = (1 - alpha) * current_rate + alpha * success
        
        if net_pnl > 0:
            self.consecutive_kills += 1
            boost = 1.15 * (1 + net_pnl * 5)
            self.cascade_factor = min(10.0, self.cascade_factor * boost)
            self.kappa_t = min(2.49, self.kappa_t + 0.05)
        else:
            self.consecutive_kills = 0
            self.cascade_factor = max(1.0, self.cascade_factor * 0.95)
            self.kappa_t = max(1.0, self.kappa_t - 0.025)
        
        if len(self.kill_history) % 5 == 0:
            self._save_learned_state()
    
    def _get_momentum_band(self, momentum: float) -> str:
        """Categorize momentum into bands for learning."""
        if momentum >= 0.7:
            return 'STRONG_UP'
        elif momentum >= 0.3:
            return 'UP'
        elif momentum >= 0:
            return 'WEAK_UP'
        elif momentum >= -0.3:
            return 'WEAK_DOWN'
        elif momentum >= -0.7:
            return 'DOWN'
        else:
            return 'STRONG_DOWN'
    
    def sync_cascade_to_scouts(self):
        """Sync cascade state to all active scouts."""
        for scout in self.scouts.values():
            if scout.status in ['deployed', 'engaged']:
                scout.sync_cascade(self.cascade_factor, self.kappa_t, self.lighthouse_gamma)
    
    def sync_from_ecosystem(self, cascade_factor: float, kappa_t: float, lighthouse_gamma: float):
        """⛏️ MINER SYNC: Import cascade state from ecosystem's CascadeAmplifier."""
        self.cascade_factor = cascade_factor
        self.kappa_t = kappa_t
        self.lighthouse_gamma = lighthouse_gamma
        self.sync_cascade_to_scouts()

    def _generate_scout_id(self) -> str:
        """Generate unique scout ID with Irish prefix"""
        self.scout_counter += 1
        timestamp = int(time.time() * 1000) % 10000
        return f"IRA-{self.scout_counter:04d}-{timestamp}"
    
    def _get_codename(self) -> str:
        """Get a random Irish codename"""
        return random.choice(PATRIOT_CONFIG['PATRIOT_CODENAMES'])
    
    def recruit_scout(self, exchange: str, symbol: str, 
                     price: float, size_usd: float = None) -> PatriotScout:
        """
        Recruit a new Irish Patriot Scout.
        Train them with Celtic wisdom and wire them to all intelligence.
        """
        scout_id = self._generate_scout_id()
        codename = self._get_codename()
        size = size_usd or PATRIOT_CONFIG['SCOUT_SIZE_USD']
        
        # Create the patriot
        scout = PatriotScout(
            scout_id=scout_id,
            codename=codename,
            exchange=exchange,
            symbol=symbol,
            entry_price=price,
            entry_time=time.time(),
            position_size=size / price if price > 0 else 0,
            entry_value_usd=size,
            current_price=price,
            status="recruited",
            target_profit_usd=PATRIOT_CONFIG.get('PENNY_PROFIT_TARGET', 0.01)
        )
        
        # Wire intelligence
        if self.intelligence_network:
            report = self.intelligence_network.update_price_feed(
                exchange, symbol, price, volume=0
            )
            scout.intelligence_report = report
            scout.ambush_score = report.ambush_score if hasattr(report, 'ambush_score') else 0.5
            scout.quick_kill_probability = report.quick_kill_probability if hasattr(report, 'quick_kill_probability') else 0.5
            scout.momentum_at_entry = report.price_momentum_1m if hasattr(report, 'price_momentum_1m') else 0
        
        # Register scout
        self.scouts[scout_id] = scout
        self.active_scouts += 1
        
        print(scout.get_battle_cry())
        return scout
    
    def deploy_scout(self, scout: PatriotScout) -> bool:
        """
        Deploy a recruited scout into combat.
        Returns True if deployment successful.
        """
        if scout.status != "recruited":
            return False
        
        # Check engagement rules
        if scout.ambush_score < PATRIOT_CONFIG['MIN_AMBUSH_SCORE']:
            print(f"   ⚠️ {scout.codename} ambush score too low: {scout.ambush_score:.2f}")
            return False
        
        if scout.quick_kill_probability < PATRIOT_CONFIG['MIN_QUICK_KILL_PROB']:
            print(f"   ⚠️ {scout.codename} quick kill prob too low: {scout.quick_kill_probability:.2f}")
            return False
        
        scout.status = "deployed"
        scout.battles_fought += 1
        self.total_battles += 1
        
        print(f"   🚀 {scout.codename} DEPLOYED! Target: ${scout.target_profit_usd:.4f} profit")
        return True
    
    def update_scout_intelligence(self, scout: PatriotScout, 
                                  price: float, volume: float = 0):
        """Update scout with latest intelligence"""
        scout.update_price(price)
        
        # Update from intelligence network
        if self.intelligence_network:
            report = self.intelligence_network.update_price_feed(
                scout.exchange, scout.symbol, price, volume
            )
            scout.intelligence_report = report
        
        # Check preemptive signals
        if self.preemptive_engine and hasattr(self.preemptive_engine, 'check_all_signals'):
            try:
                prices = self.intelligence_network.price_history.get(
                    f"{scout.exchange}:{scout.symbol}", [price]
                ) if self.intelligence_network else [price]
                
                signal = self.preemptive_engine.check_all_signals(
                    symbol=scout.symbol,
                    prices=prices,
                    entry_price=scout.entry_price,
                    current_price=price,
                    position_pnl_pct=(scout.unrealized_pnl / scout.entry_value_usd * 100) if scout.entry_value_usd > 0 else 0,
                    time_in_position=time.time() - scout.entry_time
                )
                scout.preemptive_signal = signal
            except Exception as e:
                pass  # Preemptive check failed - continue without
        
        scout.cycles_held += 1
    
    def check_all_scouts(self) -> List[Tuple[PatriotScout, str]]:
        """
        Check all scouts and return list of (scout, reason) for those that should exit.
        """
        exits = []
        
        for scout_id, scout in self.scouts.items():
            if scout.status not in ["deployed", "engaged"]:
                continue
            
            should_exit, reason = scout.should_exit()
            if should_exit:
                exits.append((scout, reason))
        
        return exits
    
    def execute_victory(self, scout: PatriotScout, actual_profit: float = None):
        """
        Record a VICTORY for this scout.
        Celebrate like true Irish!
        
        🧠 Now with ADAPTIVE LEARNING - learns from each kill!
        🎯⏱️ Now with ETA VERIFICATION - verifies our predictions!
        🧠 Now with PROBABILITY INTELLIGENCE - records successful patterns!
        """
        profit = actual_profit if actual_profit is not None else scout.unrealized_pnl
        hold_time = time.time() - scout.entry_time if scout.entry_time > 0 else 0
        
        # 🧠 PROBABILITY INTELLIGENCE - Record successful outcome
        if PROBABILITY_MATRIX_AVAILABLE and scout.prob_intel is not None:
            try:
                prob_record_outcome(scout.prob_intel, success=True, symbol=scout.symbol)
            except Exception:
                pass
        
        # 🎯⏱️ VERIFY ETA PREDICTION - Did we hit when we said we would?
        eta_verification_info = ""
        if ETA_VERIFICATION_AVAILABLE and scout.eta_registered:
            try:
                verifier = get_eta_verifier()
                verification = verifier.verify_kill(
                    scout.symbol, scout.exchange,
                    actual_pnl=profit, kill_success=True
                )
                if verification:
                    if verification.outcome == ETAOutcome.HIT_ON_TIME:
                        eta_verification_info = f"   ✅ ETA ACCURATE ({verification.time_error_pct*100:+.1f}%)"
                    elif verification.outcome == ETAOutcome.HIT_EARLY:
                        eta_verification_info = f"   ⚡ EARLY KILL ({verification.time_error_pct*100:+.1f}%)"
                    elif verification.outcome == ETAOutcome.HIT_LATE:
                        eta_verification_info = f"   ⏳ LATE KILL ({verification.time_error_pct*100:+.1f}%) - ADAPTING"
            except Exception:
                pass
        
        scout.kills += 1
        scout.total_profit += profit
        scout.status = "victorious"
        
        self.total_kills += 1
        self.total_profit += profit
        self.victories += 1
        
        # 🧠 ADAPTIVE LEARNING - Record this kill
        self._learn_from_kill(scout, profit, hold_time)
        
        if PATRIOT_CONFIG['CELEBRATE_KILLS']:
            print(scout.get_victory_cry(profit))
            cascade_info = f"CASCADE: {self.cascade_factor:.1f}x" if self.cascade_factor > 1.0 else ""
            streak_info = f"🔥{self.consecutive_kills}" if self.consecutive_kills > 1 else ""
            print(f"   📊 Network Stats: {self.total_kills} kills, +${self.total_profit:.4f} total {cascade_info} {streak_info}")
            if eta_verification_info:
                print(eta_verification_info)
    
    def execute_retreat(self, scout: PatriotScout, reason: str):
        """
        Execute strategic retreat for a scout.
        Live to fight another day!
        
        🎯⏱️ Also verifies the ETA prediction as FAILED so we learn.
        🧠 Records failed pattern for intelligence learning.
        """
        # 🧠 PROBABILITY INTELLIGENCE - Record failed outcome
        if PROBABILITY_MATRIX_AVAILABLE and scout.prob_intel is not None:
            try:
                prob_record_outcome(scout.prob_intel, success=False, symbol=scout.symbol)
                # Log if risk flags correctly predicted failure
                if scout.risk_flags:
                    print(f"   🧠 Risk flags correctly predicted failure: {scout.risk_flags}")
            except Exception:
                pass
        
        # 🎯⏱️ VERIFY ETA PREDICTION AS FAILED - We learn from our misses
        if ETA_VERIFICATION_AVAILABLE and scout.eta_registered:
            try:
                verifier = get_eta_verifier()
                verification = verifier.verify_kill(
                    scout.symbol, scout.exchange,
                    actual_pnl=scout.unrealized_pnl,
                    kill_success=False  # This was NOT a successful kill
                )
                if verification:
                    print(f"""
⚠️ ETA PREDICTION MISS - {scout.codename}
   Predicted ETA: {scout.eta_corrected:.1f}s
   Outcome: {verification.outcome.value}
   Reason: {verification.miss_reason}
   >>> System adapting predictions...
""")
            except Exception:
                pass
        
        scout.status = "retreated"
        self.retreats += 1
        
        print(scout.get_retreat_cry())
        print(f"   📊 Reason: {reason}")
    
    def coordinate_strike(self, exchange: str, symbol: str, 
                         num_scouts: int = 3) -> List[PatriotScout]:
        """
        Coordinate a multi-scout strike on a target.
        Brian Boru's tactics - multiple fronts, unified command.
        """
        deployed = []
        
        # Check if war room approves coordinated strike
        if self.war_room:
            # Get arbitrage opportunities
            pass  # War room integration
        
        print(f"\n   ⚔️ COORDINATED STRIKE: {num_scouts} scouts on {symbol} ({exchange})")
        
        for i in range(num_scouts):
            if len(self.scouts) >= PATRIOT_CONFIG['MAX_TOTAL_SCOUTS']:
                print(f"   ⚠️ Max scouts reached: {len(self.scouts)}")
                break
            
            # Each scout gets slightly different entry for diversification
            scout = self.recruit_scout(exchange, symbol, 0)  # Price will be set on deploy
            deployed.append(scout)
            
            time.sleep(PATRIOT_CONFIG['SCOUT_DEPLOYMENT_INTERVAL_SEC'])
        
        print(f"   ✅ Deployed {len(deployed)} scouts in coordinated strike")
        return deployed
    
    def broadcast_intelligence(self, source_scout: PatriotScout, intel: Any):
        """
        Broadcast intelligence from one scout to all others.
        "What one scout knows, all scouts know."
        """
        for scout_id, scout in self.scouts.items():
            if scout_id == source_scout.scout_id:
                continue
            
            # Share relevant intelligence
            if scout.exchange == source_scout.exchange:
                # Same exchange - higher relevance
                scout.intelligence_report = intel
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        deployed = len([s for s in self.scouts.values() if s.status == "deployed"])
        
        by_exchange: Dict[str, int] = defaultdict(int)
        for scout in self.scouts.values():
            by_exchange[scout.exchange] += 1
        
        return {
            'total_scouts': len(self.scouts),
            'active_scouts': self.active_scouts,
            'deployed_scouts': deployed,
            'by_exchange': dict(by_exchange),
            'total_kills': self.total_kills,
            'total_profit': self.total_profit,
            'victories': self.victories,
            'retreats': self.retreats,
            'win_rate': (self.victories / max(1, self.total_battles)) * 100,
            'systems_wired': {
                'guerrilla': self.intelligence_network is not None,
                'preemptive': self.preemptive_engine is not None,
                'coordinator': self.war_room is not None,
                'war_strategy': self.war_strategist is not None
            },
            # 🧠 Adaptive Learning Stats
            'avg_kill_time': self.avg_kill_time,
            'avg_kill_velocity': self.avg_kill_velocity,
            'momentum_success_rate': self.momentum_success_rate,
            # ⛏️ Cascade Stats
            'cascade_factor': self.cascade_factor,
            'kappa_t': self.kappa_t,
            'consecutive_kills': self.consecutive_kills,
        }

    def get_net_profit_ready_positions(self, price_getter: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Return scouts that already meet the penny profit (net after fees) threshold.

        If a price_getter is provided, refresh each scout's P&L first so the
        sniper acts on the latest metrics from the field.
        """
        ready: List[Dict[str, Any]] = []

        for scout_id, scout in self.scouts.items():
            if scout.status not in ["deployed", "engaged"]:
                continue

            try:
                if price_getter and scout.symbol:
                    price = price_getter(scout.exchange, scout.symbol)
                    if price:
                        scout.update_price(price)
            except Exception:
                # If we cannot refresh price, fall back to last known metrics
                pass

            if scout.target_profit_usd <= 0:
                continue

            if scout.unrealized_pnl >= scout.target_profit_usd:
                hold_time = time.time() - scout.entry_time if scout.entry_time > 0 else 0
                ready.append({
                    'scout_id': scout_id,
                    'symbol': scout.symbol,
                    'exchange': scout.exchange,
                    'pnl': scout.unrealized_pnl,
                    'threshold': scout.target_profit_usd,
                    'net_after_fees': True,
                    'eta': 0,
                    'probability': scout.probability_of_kill,
                    'cycles': scout.cycles_held,
                    'hold_time': hold_time,
                })

        ready.sort(key=lambda x: x.get('pnl', 0), reverse=True)
        return ready

    def hunt_quickest_exit(self, price_getter=None) -> Optional[Dict]:
        """
        🎯⚡ PROACTIVE EXIT HUNTER - Patriots seek FASTEST net profit exit ⚡🎯
        
        Scans all deployed scouts and identifies the one that can exit SOONEST
        with net profit. Works in tandem with Kill Scanner via Mycelium.
        
        Args:
            price_getter: Optional function(exchange, symbol) -> price
        
        Returns:
            Dict with quickest exit details, or None if no exits ready
        """
        if not self.scouts:
            return None
        
        quickest_kill = None
        quickest_eta = float('inf')
        ready_kills = []

        # First, pull any scouts already at net profit (after fees)
        ready_signals = self.get_net_profit_ready_positions(price_getter=price_getter)
        ready_by_id = {signal['scout_id'] for signal in ready_signals}
        for signal in ready_signals:
            ready_kills.append({**signal, 'status': 'KILL_NOW'})

        for scout_id, scout in self.scouts.items():
            if scout.status != 'deployed':
                continue

            # Already accounted for via ready_signals
            if scout_id in ready_by_id:
                continue
            
            try:
                # Update price if getter provided
                if price_getter and scout.symbol:
                    price = price_getter(scout.exchange, scout.symbol)
                    if price:
                        scout.update_price(price)
                
                # Check if KILL READY NOW
                if scout.unrealized_pnl >= scout.target_profit_usd:
                    ready_kills.append({
                        'scout_id': scout_id,
                        'codename': scout.codename,
                        'symbol': scout.symbol,
                        'exchange': scout.exchange,
                        'pnl': scout.unrealized_pnl,
                        'threshold': scout.target_profit_usd,
                        'eta': 0,
                        'probability': scout.probability_of_kill,
                        'status': 'KILL_NOW',
                        'hold_time': time.time() - scout.entry_time if scout.entry_time > 0 else 0,
                        'war_cry': scout.generate_victory_cry(),
                    })
                    continue
                
                # Track quickest ETA
                if scout.eta_to_kill < quickest_eta and scout.eta_to_kill > 0:
                    quickest_eta = scout.eta_to_kill
                    quickest_kill = {
                        'scout_id': scout_id,
                        'codename': scout.codename,
                        'symbol': scout.symbol,
                        'exchange': scout.exchange,
                        'pnl': scout.unrealized_pnl,
                        'threshold': scout.target_profit_usd,
                        'eta': scout.eta_to_kill,
                        'probability': scout.probability_of_kill,
                        'velocity': scout.pnl_velocity,
                        'momentum': scout.momentum_score,
                        'status': 'TRACKING',
                        'gap': scout.target_profit_usd - scout.unrealized_pnl,
                        'hold_time': time.time() - scout.entry_time if scout.entry_time > 0 else 0,
                    }
            except Exception:
                continue
        
        # Return ready kills first (sorted by P&L - highest first)
        if ready_kills:
            ready_kills.sort(key=lambda x: x['pnl'], reverse=True)
            best_kill = ready_kills[0]
            best_kill['all_ready'] = len(ready_kills)
            return best_kill
        
        return quickest_kill
    
    def get_exit_leaderboard(self) -> List[Dict]:
        """
        📊 PATRIOT EXIT LEADERBOARD - Ranks all scouts by exit readiness
        
        Returns list sorted by:
        1. Kill-ready scouts first (P&L >= threshold)
        2. Then by ETA (soonest first)
        3. Then by probability (highest first)
        """
        leaderboard = []
        
        for scout_id, scout in self.scouts.items():
            if scout.status != 'deployed':
                continue
            
            hold_time = time.time() - scout.entry_time if scout.entry_time > 0 else 0
            gap = scout.target_profit_usd - scout.unrealized_pnl
            proximity_pct = (scout.unrealized_pnl / scout.target_profit_usd * 100) if scout.target_profit_usd > 0 else 0
            
            entry = {
                'rank': 0,
                'scout_id': scout_id,
                'codename': scout.codename,
                'symbol': scout.symbol,
                'exchange': scout.exchange,
                'pnl': scout.unrealized_pnl,
                'threshold': scout.target_profit_usd,
                'gap': gap,
                'proximity_pct': proximity_pct,
                'eta': scout.eta_to_kill,
                'probability': scout.probability_of_kill,
                'velocity': scout.pnl_velocity,
                'momentum': scout.momentum_score,
                'hold_time': hold_time,
                'scans': scout.scans,
                'is_ready': scout.unrealized_pnl >= scout.target_profit_usd,
            }
            leaderboard.append(entry)
        
        # Sort: ready first, then by ETA, then by probability
        leaderboard.sort(key=lambda x: (
            not x['is_ready'],
            x['eta'] if x['eta'] < float('inf') else 999999,
            -x['probability'],
        ))
        
        # Assign ranks
        for i, entry in enumerate(leaderboard):
            entry['rank'] = i + 1
        
        return leaderboard
    
    def print_status(self):
        """Print beautiful status display with learning/cascade stats"""
        status = self.get_network_status()
        
        print("\n" + "═" * 70)
        print("☘️ IRISH PATRIOT SCOUT NETWORK STATUS ☘️")
        print("═" * 70)
        print(f"   🎖️ Total Scouts:    {status['total_scouts']}")
        print(f"   🚀 Deployed:        {status['deployed_scouts']}")
        print(f"   ⚔️ Total Battles:   {self.total_battles}")
        print(f"   🏆 Victories:       {status['victories']}")
        print(f"   🏃 Retreats:        {status['retreats']}")
        print(f"   📊 Win Rate:        {status['win_rate']:.1f}%")
        print(f"   💰 Total Profit:    +${status['total_profit']:.4f}")
        
        print("\n   📍 By Exchange:")
        for ex, count in status['by_exchange'].items():
            print(f"      • {ex}: {count} scouts")
        
        print("\n   🧠 Systems Wired:")
        for system, wired in status['systems_wired'].items():
            emoji = "✅" if wired else "❌"
            print(f"      {emoji} {system.replace('_', ' ').title()}")
        
        # 🧠⛏️ ENHANCED STATS - Same as IRA Sniper
        print("\n   🎯⚡ KILL SCANNER STATS ⚡🎯")
        cascade_str = f"{status['cascade_factor']:.1f}x" if status['cascade_factor'] > 1.0 else "1.0x"
        kappa_str = f"{status['kappa_t']:.2f}" if status['kappa_t'] > 1.0 else "1.00"
        streak_str = f"🔥{status['consecutive_kills']}" if status['consecutive_kills'] > 1 else "0"
        print(f"      ⛏️ CASCADE: {cascade_str} | κt: {kappa_str} | STREAK: {streak_str}")
        print(f"      🧠 Avg Kill Time: {status['avg_kill_time']:.0f}s | Velocity: ${status['avg_kill_velocity']:.4f}/s")
        
        if status['momentum_success_rate']:
            print("      📊 Momentum Success:")
            for band, rate in status['momentum_success_rate'].items():
                print(f"         • {band}: {rate:.0%}")
        
        print("═" * 70)
        print(f"   📜 \"{get_patriot_wisdom()}\"")
        print("═" * 70 + "\n")


# =============================================================================
# 🔌 ECOSYSTEM INTEGRATION - WIRE INTO AUREON
# =============================================================================

class PatriotScoutDeployer:
    """
    Integrates Patriot Scouts into the Aureon Unified Ecosystem.
    Replaces basic _deploy_scouts with Celtic-trained patriots.
    
    🧬 ENHANCED: Consumes Mycelium coherence + symbol memory for smarter deployment ordering.
    """
    
    def __init__(self, ecosystem=None):
        self.ecosystem = ecosystem
        self.network = PatriotScoutNetwork(dry_run=False)
        # Mycelium reference (set by ecosystem wiring or via ecosystem attr)
        self._mycelium = None
        if ecosystem and hasattr(ecosystem, 'mycelium'):
            self._mycelium = ecosystem.mycelium
        
        # Track pending deployments
        self.pending_deployments: List[Dict] = []
        self.deployment_lock = threading.Lock()
        
        print("\n   🔌 PatriotScoutDeployer initialized - Ready to deploy Irish warriors!\n")

    def set_mycelium(self, mycelium) -> None:
        """Wire Mycelium reference for neural-guided deployment."""
        self._mycelium = mycelium

    def _neural_candidate_score(self, candidate: Dict) -> float:
        """Compute neural score for a candidate (higher = deploy first)."""
        if self._mycelium is None:
            return candidate.get('celtic_score', 0.0)
        try:
            symbol = candidate.get('symbol', '')
            exchange = candidate.get('source', candidate.get('exchange', 'kraken'))
            mem = self._mycelium.get_symbol_memory(symbol)
            friction = self._mycelium.get_exchange_friction(exchange)
            queen = self._mycelium.get_queen_signal()
            coherence = self._mycelium.get_network_coherence()
            
            wr = float(mem.get('win_rate', 0.5))
            act = float(mem.get('activation', 0.5))
            friction_penalty = 1.0 - min(0.5, friction.get('reject_count', 0) * 0.05)
            queen_factor = 1.0 + 0.1 * queen
            coh_factor = 0.7 + 0.3 * coherence
            
            base = candidate.get('celtic_score', 0.0)
            neural_bonus = wr * act * friction_penalty * queen_factor * coh_factor * 50
            return base + neural_bonus
        except Exception:
            return candidate.get('celtic_score', 0.0)
    
    def deploy_patriots(self, candidates: List[Dict], 
                       target_count: int = 10) -> List[PatriotScout]:
        """
        Deploy patriot scouts instead of basic scouts.
        
        Args:
            candidates: List of {symbol, price, exchange, score, ...} dicts
            target_count: Number of patriots to deploy
            
        Returns:
            List of deployed PatriotScout objects
        """
        deployed = []
        
        if not candidates:
            print("   ⚠️ No candidates for patriot deployment")
            return deployed
        
        print(f"\n   ☘️🔥 DEPLOYING IRISH PATRIOTS - Target: {target_count} warriors 🔥☘️")
        print(f"   📊 Analyzing {len(candidates)} potential battlegrounds...\n")
        
        # Analyze candidates with Celtic warfare intelligence
        ranked_candidates = self._analyze_with_celtic_intelligence(candidates)
        
        for candidate in ranked_candidates[:target_count]:
            symbol = candidate.get('symbol', '')
            exchange = candidate.get('source', candidate.get('exchange', 'kraken'))
            price = candidate.get('price', 0)
            
            if price <= 0:
                continue
            
            # Recruit and deploy
            scout = self.network.recruit_scout(
                exchange=exchange,
                symbol=symbol,
                price=price,
                size_usd=PATRIOT_CONFIG['SCOUT_SIZE_USD']
            )
            
            # Update with candidate intelligence
            scout.ambush_score = candidate.get('ambush_score', 0.5)
            scout.quick_kill_probability = candidate.get('quick_kill_prob', 
                                                         candidate.get('quick_kill', {}).get('prob_quick_kill', 0.5))
            
            if self.network.deploy_scout(scout):
                deployed.append(scout)
            
            # Respect deployment interval
            time.sleep(PATRIOT_CONFIG['SCOUT_DEPLOYMENT_INTERVAL_SEC'])
        
        print(f"\n   🎯 DEPLOYED {len(deployed)} IRISH PATRIOTS!")
        print(f"   📜 \"{get_patriot_wisdom()}\"")
        
        return deployed
    
    def _analyze_with_celtic_intelligence(self, candidates: List[Dict]) -> List[Dict]:
        """
        Analyze candidates using all Celtic warfare systems.
        Returns sorted list by combat readiness.
        """
        analyzed = []
        
        for c in candidates:
            symbol = c.get('symbol', '')
            exchange = c.get('source', c.get('exchange', 'kraken'))
            price = c.get('price', 0)
            
            # Get intelligence report
            ambush_score = 0.5
            quick_kill_prob = 0.5
            
            if self.network.intelligence_network:
                try:
                    report = self.network.intelligence_network.update_price_feed(
                        exchange, symbol, price, c.get('volume', 0)
                    )
                    ambush_score = report.ambush_score
                    quick_kill_prob = report.quick_kill_probability
                except:
                    pass
            
            # War strategy ranking
            war_score = c.get('war_score', 0)
            war_go = c.get('war_go', True)
            
            # Celtic composite score
            celtic_score = (
                ambush_score * 100 +
                quick_kill_prob * 100 +
                (50 if war_go else 0) +
                war_score * 10 +
                c.get('score', 0) * 0.1
            )
            
            c['ambush_score'] = ambush_score
            c['quick_kill_prob'] = quick_kill_prob
            c['celtic_score'] = celtic_score
            analyzed.append(c)
        
        # 🧬 Sort by neural-enhanced score (higher = deploy first)
        analyzed.sort(key=lambda c: self._neural_candidate_score(c), reverse=True)
        
        # 🏴⚔️ MULTI-BATTLEFIELD DISTRIBUTION: Ensure scouts spread across ALL exchanges!
        # Don't let all scouts go to one exchange - we fight on ALL fronts!
        analyzed.sort(key=lambda x: x.get('celtic_score', 0), reverse=True)
        
        # Group by exchange and round-robin select to ensure distribution
        by_exchange = {}
        for c in analyzed:
            ex = c.get('source', c.get('exchange', 'binance')).lower()
            if ex not in by_exchange:
                by_exchange[ex] = []
            by_exchange[ex].append(c)
        
        # Round-robin selection across exchanges
        distributed = []
        exchange_list = list(by_exchange.keys())
        exchange_indices = {ex: 0 for ex in exchange_list}
        
        # Target per exchange based on config (default: spread evenly)
        max_per_exchange = PATRIOT_CONFIG.get('MAX_SCOUTS_PER_EXCHANGE', 5)
        exchange_counts = {ex: 0 for ex in exchange_list}
        
        while len(distributed) < len(analyzed):
            added_this_round = False
            for ex in exchange_list:
                if exchange_counts[ex] >= max_per_exchange:
                    continue
                idx = exchange_indices[ex]
                if idx < len(by_exchange[ex]):
                    distributed.append(by_exchange[ex][idx])
                    exchange_indices[ex] += 1
                    exchange_counts[ex] += 1
                    added_this_round = True
            if not added_this_round:
                break
        
        # Log distribution
        final_counts = {}
        for c in distributed[:20]:  # Top 20
            ex = c.get('source', c.get('exchange', 'unknown')).lower()
            final_counts[ex] = final_counts.get(ex, 0) + 1
        print(f"   ⚔️ Scout distribution across battlefronts: {final_counts}")
        
        return distributed
    
    def check_and_exit_patriots(self) -> List[Tuple[PatriotScout, float]]:
        """
        Check all patriots and execute exits as needed.
        Returns list of (scout, profit) for exited positions.
        """
        exits = []
        
        for scout, reason in self.network.check_all_scouts():
            profit = scout.unrealized_pnl
            
            if profit >= 0:
                self.network.execute_victory(scout, profit)
            else:
                self.network.execute_retreat(scout, reason)
            
            exits.append((scout, profit))
        
        return exits
    
    def get_status(self) -> Dict[str, Any]:
        """Get deployer and network status"""
        return self.network.get_network_status()
