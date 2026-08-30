#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                      ║
║     ⚔️🦅 QUEEN WARRIOR PATH - THE FULL TACTICAL ARSENAL ⚔️🦅                                          ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                        ║
║                                                                                                      ║
║     "We fight not as individuals but as ancestors who refused to die"                               ║
║                                                                                                      ║
║     This module wires ALL tactical/ancestral warfare systems into the Queen:                        ║
║                                                                                                      ║
║     🇮🇪 IRA TACTICS - "The Troubles" Guerrilla Warfare                                                ║
║       • Hit-and-Run (Wolf Scanner tactic)                                                           ║
║       • Cell Structure - Compartmentalized operations                                               ║
║       • Blend in until strike                                                                       ║
║                                                                                                      ║
║     🦅 APACHE TACTICS - Desert Terrain Masters                                                        ║
║       • Patience (0.96/1.0) — Waiting for the sick deer                                             ║
║       • Terrain knowledge — Know every price level                                                  ║
║       • Survival over conquest                                                                      ║
║                                                                                                      ║
║     ☯️ SUN TZU PRINCIPLES - The Art of War                                                           ║
║       • "Win Without Fighting" — The Queen's veto                                                   ║
║       • "Attack weakness, avoid strength"                                                           ║
║       • "All warfare is deception"                                                                  ║
║                                                                                                      ║
║     🌌 HOPI GHOST DANCE - Ceremonial Warfare                                                         ║
║       • 741 Hz Warrior — Battle frequency                                                           ║
║       • 852 Hz Scout — Vision and perception                                                        ║
║       • 528 Hz Medicine — Healing and DNA repair                                                    ║
║       • Moon phase alignment                                                                        ║
║                                                                                                      ║
║     📜 HISTORICAL MANIPULATION HUNTER - Know Your Enemy                                              ║
║       • 1929 Pattern — Credit expansion → sudden contraction                                        ║
║       • 2008 Pattern — Coordinated institutional dump                                               ║
║       • 2020 Pattern — News-driven terror                                                           ║
║                                                                                                      ║
║     🎵 HARMONIC COUNTER-FREQUENCY - Phase Opposition                                                 ║
║       • 180° out of phase with whale cycles                                                         ║
║       • Sacred frequency alignment (432/528/963 Hz)                                                 ║
║       • Schumann resonance harmonics (7.83 Hz)                                                      ║
║                                                                                                      ║
║     🐺 ANIMAL SCANNERS - Nature's Warriors                                                           ║
║       • Wolf — Hit-and-run, pack coordination                                                       ║
║       • Lion — Composite strength, wait for weakness                                                ║
║       • Ants — Swarm intelligence, small persistent profits                                         ║
║       • Hummingbird — Micro-rotation, rapid extraction                                              ║
║                                                                                                      ║
║     Gary Leckey & GitHub Copilot | February 2026                                                    ║
║     "The ancestors fight with us. Their tactics are eternal."                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32' and sys.stdout.isatty():
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

import json
import time
import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# ── Thought Bus integration (fail-safe) ──────────────────────────────────────
try:
    from aureon.core.aureon_thought_bus import get_thought_bus as _get_thought_bus, Thought as _Thought
    _HAS_THOUGHT_BUS = True
except Exception:
    _get_thought_bus = None  # type: ignore
    _Thought = None          # type: ignore
    _HAS_THOUGHT_BUS = False

# ═══════════════════════════════════════════════════════════════════════════════
# 🎵 SACRED CONSTANTS - The frequencies of war and healing
# ═══════════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden Ratio
SCHUMANN_BASE = 7.83  # Hz - Earth's heartbeat

# Solfeggio Frequencies (Hz)
FREQ_LIBERATION = 396      # Liberation from fear
FREQ_TRANSFORMATION = 417  # Transmutation
FREQ_MIRACLE = 528         # DNA repair, love frequency
FREQ_CONNECTION = 639      # Connecting relationships
FREQ_WARRIOR = 741         # Awakening intuition, battle frequency
FREQ_SCOUT = 852           # Returning to spiritual order, vision
FREQ_AWAKENING = 963       # Pineal activation, cosmic consciousness

# Animal Spirit Power Frequencies
WOLF_FREQUENCY = 7.83      # Pack frequency - Schumann aligned
LION_FREQUENCY = 432       # King frequency - Universal harmony
HUMMINGBIRD_FREQUENCY = 528 # Micro extraction - DNA frequency
ANT_FREQUENCY = 13         # Swarm frequency - Fibonacci


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class TacticalPhilosophy(Enum):
    """The philosophies that guide our warfare"""
    IRA_GUERRILLA = "ira_guerrilla"      # Hit-and-run, cell structure, blend in
    APACHE_PATIENCE = "apache_patience"   # Wait for weakness, terrain mastery
    SUN_TZU = "sun_tzu"                   # Deception, avoid strength, win without fighting
    GHOST_DANCE = "ghost_dance"           # Ceremonial, ancestral, frequency warfare


class CombatMode(Enum):
    """Current combat stance"""
    STEALTH = "stealth"           # Hidden, observing
    STALKING = "stalking"         # Tracking, preparing
    AMBUSH = "ambush"             # Positioned, waiting for trigger
    STRIKE = "strike"             # Executing attack
    RETREAT = "retreat"           # Extracting, protecting gains
    HEALING = "healing"           # Recovery, regroup
    CEREMONY = "ceremony"         # Invoking ancestors


@dataclass
class TacticalAssessment:
    """Comprehensive tactical assessment for Queen decision-making"""
    timestamp: float
    
    # IRA Tactics
    ira_hit_and_run_score: float     # 0-1 (ready for quick strike)
    ira_stealth_score: float          # 0-1 (hidden from enemy)
    ira_cell_integrity: float         # 0-1 (compartmentalization)
    
    # Apache Tactics
    apache_patience_score: float      # 0-1 (0.96 is their standard)
    apache_terrain_knowledge: float   # 0-1 (market level familiarity)
    apache_survival_mode: bool        # Survival over conquest
    
    # Sun Tzu Principles
    sun_tzu_deception_active: bool    # Are we deceiving?
    sun_tzu_enemy_weakness: str       # What weakness to exploit
    sun_tzu_can_win_without_fight: bool  # Veto opportunity?
    
    # Ghost Dance
    moon_phase: float                 # 0-1 (0.5 = full moon)
    active_frequency: float           # Hz (741, 852, 528, etc.)
    ancestors_invoked: List[str]      # Which spirits are active
    ceremony_power: float             # 0-1 (collective field strength)
    
    # Historical Pattern
    current_pattern_match: str        # "1929", "2008", "2020", "none"
    pattern_danger_level: float       # 0-1
    pattern_opportunity: bool         # Is this a buy-the-dip moment?
    
    # Animal Scanner Integration
    wolf_readiness: float             # 0-1 (hit-and-run ready)
    lion_strength: float              # 0-1 (composite power)
    hummingbird_agility: float        # 0-1 (micro-extraction)
    ant_swarm_mode: bool              # Coordinated small profits
    
    # Harmonic Counter-Phase
    counter_phase_angle: float        # 0-360 (180 = optimal)
    harmonic_alignment: float         # 0-1 (sacred frequency match)
    neutralization_power: float       # 0-1 (counter-whale effectiveness)
    
    # Combined Recommendations
    recommended_philosophy: str       # Which tactic to use
    recommended_combat_mode: str      # Current stance
    recommended_action: str           # "STRIKE", "WAIT", "RETREAT", "VETO"
    battle_readiness: float           # 0-1 overall score
    
    # Evidence & Reasoning
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AncestorInvocation:
    """Record of ancestral spirit invocation"""
    spirit_name: str
    frequency_hz: float
    wisdom_received: str
    timestamp: float
    market_conditions: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# ⚔️ TACTICAL WISDOM DATABASES
# ═══════════════════════════════════════════════════════════════════════════════

IRA_TACTICS = {
    "hit_and_run": {
        "description": "Strike fast, extract immediately, vanish",
        "market_application": "Enter/exit within 2 hours max",
        "quote": "The Volunteer who lives to fight another day wins",
        "wolf_scanner_alignment": True
    },
    "cell_structure": {
        "description": "Compartmentalized knowledge, limited exposure",
        "market_application": "Separate positions, no single point of failure",
        "quote": "If one cell falls, the army survives"
    },
    "blend_in": {
        "description": "Look like everyone else until you strike",
        "market_application": "Use limit orders, TWAP, don't move the market",
        "quote": "The enemy cannot kill what they cannot see"
    },
    "intelligence_first": {
        "description": "Know every soldier, every patrol, every weakness",
        "market_application": "Full entity mapping before any trade",
        "quote": "Information is ammunition"
    }
}

APACHE_TACTICS = {
    "patience": {
        "description": "Wait days for the perfect shot",
        "market_application": "Wait for whale exhaustion, don't chase",
        "standard_score": 0.96,
        "quote": "The desert teaches patience or death"
    },
    "terrain_mastery": {
        "description": "Know every rock, every shadow, every water source",
        "market_application": "Know every support/resistance level intimately",
        "quote": "The land fights for those who know her"
    },
    "survival_over_conquest": {
        "description": "Live to fight 100 battles, not die in 1",
        "market_application": "Preserve capital above all profits",
        "quote": "The last warrior standing writes history"
    },
    "track_the_sick_deer": {
        "description": "Follow the weakened prey until it falls naturally",
        "market_application": "Identify exhausted whales, wait for capitulation",
        "quote": "Nature finishes what we start"
    }
}

SUN_TZU_PRINCIPLES = {
    "win_without_fighting": {
        "description": "Supreme excellence is breaking enemy's resistance without fighting",
        "market_application": "Queen veto - don't enter bad trades at all",
        "chapter": "The Art of War, Chapter III"
    },
    "attack_weakness": {
        "description": "Attack where the enemy is unprepared, appear where not expected",
        "market_application": "Trade during low-liquidity hours when whales sleep",
        "chapter": "The Art of War, Chapter I"
    },
    "all_warfare_is_deception": {
        "description": "When able to attack, appear unable. When close, make it appear you are far away",
        "market_application": "Iceberg orders, don't show hand, misdirection",
        "chapter": "The Art of War, Chapter I"
    },
    "know_enemy_know_self": {
        "description": "Know enemy and know yourself; in 100 battles you will never be in peril",
        "market_application": "Entity intelligence + honest self-assessment",
        "chapter": "The Art of War, Chapter III"
    },
    "highest_art": {
        "description": "To subdue the enemy without fighting is the highest skill",
        "market_application": "Profit from information asymmetry, not direct confrontation",
        "chapter": "The Art of War, Chapter III"
    }
}

HISTORICAL_PATTERNS = {
    "1929_pattern": {
        "name": "Great Depression Pattern",
        "signature": "Credit expansion → sudden liquidity withdrawal",
        "warning_signs": ["Rising margin debt", "Fed tightening", "Elite exits"],
        "danger_level": 1.0,
        "counter_strategy": "Exit all margin, hold cash, wait for -90%"
    },
    "2008_pattern": {
        "name": "Financial Crisis Pattern",
        "signature": "Coordinated institutional selling, mortgage fraud exposure",
        "warning_signs": ["CDO implosion", "Lehman-style collapses", "Bailout rumors"],
        "danger_level": 0.95,
        "counter_strategy": "Reduce exposure 80%, wait for bailout confirmation"
    },
    "2010_flash_crash": {
        "name": "Flash Crash Pattern",
        "signature": "HFT-driven rapid collapse and recovery",
        "warning_signs": ["Liquidity vacuum", "Quote stuffing", "Cascade triggers"],
        "danger_level": 0.7,
        "opportunity": True,  # Rapid recovery = buying opportunity
        "counter_strategy": "Wait for bottom confirmation, enter large"
    },
    "2020_covid_pattern": {
        "name": "COVID Crash Pattern",
        "signature": "News-driven global panic, coordinated selling",
        "warning_signs": ["Black swan event", "Circuit breakers triggered", "Fed emergency action"],
        "danger_level": 0.9,
        "opportunity": True,  # Rapid Fed intervention = buy signal
        "counter_strategy": "Buy when Fed intervenes"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🦅 QUEEN WARRIOR PATH - MASTER TACTICAL CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class QueenWarriorPath:
    """
    The Queen's Tactical Arsenal - All warfare systems unified
    
    Integrates:
    - Strategic Warfare Scanner (IRA/Apache/Sun Tzu)
    - Ghost Dance Protocol (Ceremonial warfare)
    - Historical Manipulation Hunter (Pattern recognition)
    - Harmonic Counter-Frequency (Phase opposition)
    - Animal Momentum Scanners (Wolf/Lion/Hummingbird/Ants)
    """
    
    def __init__(self):
        self.state_file = Path("queen_warrior_path_state.json")
        
        # Tactical subsystems (lazy loaded)
        self._strategic_warfare: Optional[Any] = None
        self._ghost_dance: Optional[Any] = None
        self._manipulation_hunter: Optional[Any] = None
        self._harmonic_engine: Optional[Any] = None
        self._animal_scanners: Optional[Any] = None
        
        # Current state
        self.current_combat_mode = CombatMode.STEALTH
        self.active_philosophy = TacticalPhilosophy.SUN_TZU
        self.ancestors_invoked: List[str] = []
        self.ceremony_count = 0
        
        # Thought Bus connection
        self._thought_bus = (
            _get_thought_bus() if _HAS_THOUGHT_BUS and _get_thought_bus is not None else None
        )

        # Assessment history
        self.assessment_history: List[TacticalAssessment] = []
        
        # Load saved state
        self._load_state()
        
        logger.info("⚔️ Queen Warrior Path initialized - ALL TACTICAL SYSTEMS ONLINE")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🔌 LAZY LOADING - Wire the subsystems on demand
    # ═══════════════════════════════════════════════════════════════════════
    
    @property
    def strategic_warfare(self):
        """Lazy load Strategic Warfare Scanner"""
        if self._strategic_warfare is None:
            try:
                from aureon.scanners.aureon_strategic_warfare_scanner import StrategicWarfareScanner
                self._strategic_warfare = StrategicWarfareScanner()
                logger.info("⚔️ Strategic Warfare Scanner loaded")
            except ImportError as e:
                logger.warning(f"⚔️ Strategic Warfare Scanner not available: {e}")
        return self._strategic_warfare
    
    @property
    def ghost_dance(self):
        """Lazy load Ghost Dance Protocol"""
        if self._ghost_dance is None:
            try:
                from aureon.wisdom.aureon_ghost_dance_protocol import GhostDanceProtocol
                self._ghost_dance = GhostDanceProtocol()
                logger.info("🌌 Ghost Dance Protocol loaded")
            except ImportError as e:
                logger.warning(f"🌌 Ghost Dance Protocol not available: {e}")
        return self._ghost_dance
    
    @property
    def manipulation_hunter(self):
        """Lazy load Historical Manipulation Hunter"""
        if self._manipulation_hunter is None:
            try:
                from aureon.analytics.aureon_historical_manipulation_hunter import HistoricalManipulationHunter
                self._manipulation_hunter = HistoricalManipulationHunter()
                logger.info("📜 Historical Manipulation Hunter loaded")
            except ImportError as e:
                logger.warning(f"📜 Manipulation Hunter not available: {e}")
        return self._manipulation_hunter
    
    @property
    def harmonic_engine(self):
        """Lazy load Harmonic Counter-Frequency Engine"""
        if self._harmonic_engine is None:
            try:
                from aureon.harmonic.aureon_harmonic_counter_frequency import extract_harmonic_signature
                self._harmonic_engine = True  # Module is function-based
                logger.info("🎵 Harmonic Counter-Frequency Engine loaded")
            except ImportError as e:
                logger.warning(f"🎵 Harmonic Engine not available: {e}")
        return self._harmonic_engine
    
    @property
    def animal_scanners(self):
        """Lazy load Animal Momentum Scanners"""
        if self._animal_scanners is None:
            try:
                from aureon.scanners.aureon_animal_momentum_scanners import (
                    WolfScanner, LionCompositeScanner, 
                    AntSwarmScanner, HummingbirdScanner
                )
                self._animal_scanners = {
                    'wolf': WolfScanner,
                    'lion': LionCompositeScanner,
                    'ants': AntSwarmScanner,
                    'hummingbird': HummingbirdScanner
                }
                logger.info("🐺 Animal Momentum Scanners loaded")
            except ImportError as e:
                logger.warning(f"🐺 Animal Scanners not available: {e}")
        return self._animal_scanners
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 TACTICAL ASSESSMENT - The unified combat readiness score
    # ═══════════════════════════════════════════════════════════════════════
    
    def assess_tactical_situation(
        self,
        symbol: str = "",
        price: float = 0.0,
        price_change_pct: float = 0.0,
        volume: float = 0.0,
        market_context: Optional[Dict] = None
    ) -> TacticalAssessment:
        """
        Comprehensive tactical assessment using all warfare systems.
        
        This is the Queen's battle-readiness evaluation.
        """
        now = time.time()
        context = market_context or {}
        
        # ─────────────────────────────────────────────────────────────
        # 🇮🇪 IRA TACTICAL SCORES
        # ─────────────────────────────────────────────────────────────
        ira_hit_and_run = self._calculate_hit_and_run_score(context)
        ira_stealth = self._calculate_stealth_score(context)
        ira_cell_integrity = 0.95  # Always maintain compartmentalization
        
        # ─────────────────────────────────────────────────────────────
        # 🦅 APACHE TACTICAL SCORES
        # ─────────────────────────────────────────────────────────────
        apache_patience = self._calculate_patience_score(context)
        apache_terrain = self._calculate_terrain_knowledge(context)
        apache_survival = self._is_survival_mode(context)
        
        # ─────────────────────────────────────────────────────────────
        # ☯️ SUN TZU ANALYSIS
        # ─────────────────────────────────────────────────────────────
        sun_tzu_deception = self._is_deception_active(context)
        sun_tzu_weakness = self._identify_enemy_weakness(context)
        sun_tzu_veto = self._can_win_without_fighting(context)
        
        # ─────────────────────────────────────────────────────────────
        # 🌌 GHOST DANCE CEREMONIAL STATE
        # ─────────────────────────────────────────────────────────────
        moon_phase = self._get_moon_phase()
        active_freq = self._get_active_frequency(context)
        ceremony_power = self._get_ceremony_power()
        
        # ─────────────────────────────────────────────────────────────
        # 📜 HISTORICAL PATTERN MATCHING
        # ─────────────────────────────────────────────────────────────
        pattern_match, danger_level, is_opportunity = self._match_historical_pattern(
            price_change_pct, volume, context
        )
        
        # ─────────────────────────────────────────────────────────────
        # 🐺 ANIMAL SCANNER READINESS
        # ─────────────────────────────────────────────────────────────
        wolf_ready = self._get_wolf_readiness(context)
        lion_strength = self._get_lion_strength(context)
        hummingbird_agility = self._get_hummingbird_agility(context)
        ant_swarm = self._is_ant_swarm_mode(context)
        
        # ─────────────────────────────────────────────────────────────
        # 🎵 HARMONIC COUNTER-PHASE
        # ─────────────────────────────────────────────────────────────
        counter_phase = self._get_counter_phase_angle(context)
        harmonic_align = self._get_harmonic_alignment(context)
        neutralization = self._get_neutralization_power(context)
        
        # ─────────────────────────────────────────────────────────────
        # 🎯 COMBINED RECOMMENDATIONS
        # ─────────────────────────────────────────────────────────────
        recommended_philosophy = self._recommend_philosophy(
            ira_hit_and_run, apache_patience, sun_tzu_veto, danger_level
        )
        recommended_mode = self._recommend_combat_mode(
            danger_level, apache_patience, ira_hit_and_run, sun_tzu_veto
        )
        recommended_action = self._recommend_action(
            danger_level, is_opportunity, sun_tzu_veto, apache_patience
        )
        
        # Calculate overall battle readiness
        battle_readiness = self._calculate_battle_readiness(
            ira_hit_and_run, ira_stealth, apache_patience, apache_terrain,
            ceremony_power, harmonic_align, danger_level, sun_tzu_veto
        )
        
        # Build evidence list
        evidence = self._build_evidence_list(
            recommended_philosophy, recommended_action, pattern_match,
            sun_tzu_weakness, moon_phase, active_freq
        )
        
        assessment = TacticalAssessment(
            timestamp=now,
            
            # IRA
            ira_hit_and_run_score=ira_hit_and_run,
            ira_stealth_score=ira_stealth,
            ira_cell_integrity=ira_cell_integrity,
            
            # Apache
            apache_patience_score=apache_patience,
            apache_terrain_knowledge=apache_terrain,
            apache_survival_mode=apache_survival,
            
            # Sun Tzu
            sun_tzu_deception_active=sun_tzu_deception,
            sun_tzu_enemy_weakness=sun_tzu_weakness,
            sun_tzu_can_win_without_fight=sun_tzu_veto,
            
            # Ghost Dance
            moon_phase=moon_phase,
            active_frequency=active_freq,
            ancestors_invoked=self.ancestors_invoked.copy(),
            ceremony_power=ceremony_power,
            
            # Historical
            current_pattern_match=pattern_match,
            pattern_danger_level=danger_level,
            pattern_opportunity=is_opportunity,
            
            # Animal
            wolf_readiness=wolf_ready,
            lion_strength=lion_strength,
            hummingbird_agility=hummingbird_agility,
            ant_swarm_mode=ant_swarm,
            
            # Harmonic
            counter_phase_angle=counter_phase,
            harmonic_alignment=harmonic_align,
            neutralization_power=neutralization,
            
            # Combined
            recommended_philosophy=recommended_philosophy,
            recommended_combat_mode=recommended_mode,
            recommended_action=recommended_action,
            battle_readiness=battle_readiness,
            
            evidence=evidence
        )
        
        # Store in history
        self.assessment_history.append(assessment)
        if len(self.assessment_history) > 100:
            self.assessment_history = self.assessment_history[-100:]
        
        # Save state
        self._save_state()

        # Publish battle readiness to Thought Bus
        if self._thought_bus is not None and _HAS_THOUGHT_BUS and _Thought is not None:
            try:
                self._thought_bus.publish(_Thought(
                    source="queen_warrior_path",
                    topic="queen.battle_readiness",
                    payload={
                        "symbol": symbol,
                        "battle_readiness": battle_readiness,
                        "combat_mode": str(recommended_mode.value if hasattr(recommended_mode, 'value') else recommended_mode),
                        "philosophy": str(recommended_philosophy.value if hasattr(recommended_philosophy, 'value') else recommended_philosophy),
                        "action": str(recommended_action),
                    },
                    meta={"mode": "queen_tactical"},
                ))
            except Exception:
                pass

        return assessment
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🇮🇪 IRA TACTICAL CALCULATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _calculate_hit_and_run_score(self, context: Dict) -> float:
        """Calculate readiness for hit-and-run operation (IRA tactic)"""
        # Factors: Low spread, high liquidity, clear exit path
        spread = context.get('spread_pct', 0.1)
        liquidity = context.get('liquidity', 0.5)
        volatility = context.get('volatility', 0.5)
        
        # Low spread = good, high liquidity = good, moderate volatility = good
        spread_score = max(0, 1 - spread * 10)  # < 0.1% spread is ideal
        liquidity_score = min(1, liquidity)
        volatility_score = 1 - abs(volatility - 0.5)  # Prefer moderate
        
        return (spread_score + liquidity_score + volatility_score) / 3
    
    def _calculate_stealth_score(self, context: Dict) -> float:
        """Calculate how stealthy our operations are (IRA tactic)"""
        # Based on order size vs average, market impact, visibility
        our_volume_pct = context.get('our_volume_pct', 0.01)
        market_impact = context.get('market_impact', 0.0)
        
        # Lower is better - we want to be invisible
        volume_stealth = max(0, 1 - our_volume_pct * 10)
        impact_stealth = max(0, 1 - market_impact * 5)
        
        return (volume_stealth + impact_stealth) / 2
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🦅 APACHE TACTICAL CALCULATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _calculate_patience_score(self, context: Dict) -> float:
        """Calculate patience level (Apache tactic) - standard is 0.96"""
        # Time since last trade, quality of setups rejected
        time_since_last = context.get('time_since_last_trade_hours', 24)
        setups_rejected = context.get('setups_rejected', 0)
        
        # More time = more patience
        time_patience = min(1, time_since_last / 48)  # 48 hours = full patience
        rejection_patience = min(1, setups_rejected / 10)  # 10 rejections = disciplined
        
        raw_score = (time_patience + rejection_patience) / 2
        
        # Apache standard: never below 0.9
        return max(0.9, raw_score)
    
    def _calculate_terrain_knowledge(self, context: Dict) -> float:
        """Calculate terrain knowledge (Apache tactic)"""
        # How well do we know this symbol's price levels?
        levels_mapped = context.get('support_resistance_levels_known', 5)
        time_observing = context.get('observation_days', 7)
        
        level_score = min(1, levels_mapped / 10)  # 10+ levels = mastery
        time_score = min(1, time_observing / 30)  # 30+ days = well known
        
        return (level_score + time_score) / 2
    
    def _is_survival_mode(self, context: Dict) -> bool:
        """Is survival the priority over conquest? (Apache principle)"""
        drawdown = context.get('current_drawdown_pct', 0)
        capital_risk = context.get('capital_at_risk_pct', 0)
        
        # If drawdown > 10% or risk > 20%, enter survival mode
        return drawdown > 10 or capital_risk > 20
    
    # ═══════════════════════════════════════════════════════════════════════
    # ☯️ SUN TZU ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _is_deception_active(self, context: Dict) -> bool:
        """Are we using deception tactics?"""
        using_iceberg = context.get('iceberg_orders_active', False)
        using_misdirection = context.get('misdirection_active', False)
        return using_iceberg or using_misdirection
    
    def _identify_enemy_weakness(self, context: Dict) -> str:
        """Identify the enemy's weakness to exploit"""
        whale_exhaustion = context.get('whale_exhaustion', 0)
        liquidity_gaps = context.get('liquidity_gaps', [])
        timing_weakness = context.get('whale_sleep_hours', False)
        
        if whale_exhaustion > 0.7:
            return "WHALE_EXHAUSTION - They are tired, strike now"
        elif liquidity_gaps:
            return f"LIQUIDITY_GAP - {liquidity_gaps[0]} price level undefended"
        elif timing_weakness:
            return "TIMING - Whale operators sleeping (00:00-06:00 UTC)"
        else:
            return "NO_CLEAR_WEAKNESS - Continue observation"
    
    def _can_win_without_fighting(self, context: Dict) -> bool:
        """Sun Tzu's highest art - can we profit without direct confrontation?"""
        # Information edge, no need to trade
        info_edge = context.get('information_edge', 0)
        arbitrage_available = context.get('arbitrage_opportunity', False)
        passive_income = context.get('staking_yield_active', False)
        
        return info_edge > 0.8 or arbitrage_available or passive_income
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🌌 GHOST DANCE CEREMONIAL
    # ═══════════════════════════════════════════════════════════════════════
    
    def _get_moon_phase(self) -> float:
        """Calculate current moon phase (0.0 = new, 0.5 = full, 1.0 = new)"""
        # Reference full moon: January 13, 2025 at 22:27 UTC
        LUNAR_CYCLE_DAYS = 29.53
        reference_full = datetime(2025, 1, 13, 22, 27, tzinfo=timezone.utc).timestamp()
        now = time.time()
        
        delta_days = (now - reference_full) / 86400
        cycles = delta_days / LUNAR_CYCLE_DAYS
        phase = cycles % 1.0
        
        return phase
    
    def _get_active_frequency(self, context: Dict) -> float:
        """Get the currently active ceremonial frequency"""
        danger = context.get('danger_level', 0)
        need_healing = context.get('recent_loss', False)
        need_vision = context.get('uncertain_direction', False)
        
        if danger > 0.7:
            return FREQ_WARRIOR  # 741 Hz - Battle frequency
        elif need_healing:
            return FREQ_MIRACLE  # 528 Hz - Healing
        elif need_vision:
            return FREQ_SCOUT    # 852 Hz - Vision
        else:
            return FREQ_CONNECTION  # 639 Hz - Default harmony
    
    def _get_ceremony_power(self) -> float:
        """Calculate collective ceremonial field strength"""
        # Based on recent ceremonies and spirit invocations
        recent_ceremonies = self.ceremony_count
        spirits_active = len(self.ancestors_invoked)
        
        ceremony_power = min(1, recent_ceremonies / 7)  # 7 ceremonies = full power
        spirit_power = min(1, spirits_active / 5)  # 5 spirits = full council
        
        return (ceremony_power + spirit_power) / 2
    
    def invoke_ancestors(self, ceremony_type: str = "battle") -> Dict:
        """Invoke ancestral spirits for guidance"""
        now = time.time()
        
        spirit_invocations = {
            "battle": {
                "spirits": ["warrior_ancestors", "scout_ancestors"],
                "frequency": FREQ_WARRIOR,
                "wisdom": "Strike only when certain. Retreat is not defeat."
            },
            "healing": {
                "spirits": ["medicine_people", "grandmother_spirits"],
                "frequency": FREQ_MIRACLE,
                "wisdom": "Losses are teachers. Let them heal into wisdom."
            },
            "vision": {
                "spirits": ["scout_ancestors", "chief_council"],
                "frequency": FREQ_SCOUT,
                "wisdom": "See beyond the immediate. The pattern reveals itself."
            },
            "harvest": {
                "spirits": ["grandmother_spirits", "earth_keepers"],
                "frequency": FREQ_TRANSFORMATION,
                "wisdom": "Take only what you need. Leave seeds for tomorrow."
            }
        }
        
        invocation = spirit_invocations.get(ceremony_type, spirit_invocations["battle"])
        
        self.ancestors_invoked = invocation["spirits"]
        self.ceremony_count += 1
        
        logger.info(f"🌌 Ancestors invoked: {invocation['spirits']} @ {invocation['frequency']} Hz")
        logger.info(f"📜 Wisdom: {invocation['wisdom']}")
        
        return {
            "spirits": invocation["spirits"],
            "frequency": invocation["frequency"],
            "wisdom": invocation["wisdom"],
            "moon_phase": self._get_moon_phase(),
            "timestamp": now
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📜 HISTORICAL PATTERN MATCHING
    # ═══════════════════════════════════════════════════════════════════════
    
    def _match_historical_pattern(
        self, price_change_pct: float, volume: float, context: Dict
    ) -> Tuple[str, float, bool]:
        """Match current conditions to historical manipulation patterns"""
        
        # Check for crash signatures
        if price_change_pct < -10:
            # Major crash - check which historical pattern
            if context.get('margin_debt_high', False):
                return "1929_pattern", 0.95, False  # Danger, not opportunity
            elif context.get('institutional_selling', False):
                return "2008_pattern", 0.9, False
            elif context.get('hft_cascade', False):
                return "2010_flash_crash", 0.7, True  # Opportunity!
            elif context.get('news_driven', False):
                return "2020_covid_pattern", 0.85, True  # Buy when Fed acts
        
        # Check for bubble signatures
        if price_change_pct > 20 and context.get('retail_fomo', False):
            return "bubble_forming", 0.6, False  # Exit before pop
        
        return "none", 0.0, False
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🐺 ANIMAL SCANNER INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def _get_wolf_readiness(self, context: Dict) -> float:
        """Wolf Scanner readiness - hit-and-run capability"""
        # Quick in, quick out capability
        liquidity = context.get('liquidity', 0.5)
        exit_clear = context.get('exit_path_clear', True)
        pack_aligned = context.get('correlated_assets_aligned', False)
        
        base = liquidity * 0.5
        if exit_clear:
            base += 0.3
        if pack_aligned:
            base += 0.2
        
        return min(1, base)
    
    def _get_lion_strength(self, context: Dict) -> float:
        """Lion Composite strength - dominant power"""
        capital_size = context.get('available_capital', 0)
        position_strength = context.get('position_size_vs_market', 0)
        
        # Lions need size to dominate
        capital_score = min(1, capital_size / 100000)  # $100k = full power
        position_score = min(1, position_strength * 10)
        
        return (capital_score + position_score) / 2
    
    def _get_hummingbird_agility(self, context: Dict) -> float:
        """Hummingbird agility - micro-extraction capability"""
        spread = context.get('spread_pct', 0.1)
        latency = context.get('execution_latency_ms', 100)
        
        # Hummingbirds need tight spreads and fast execution
        spread_score = max(0, 1 - spread * 20)  # < 0.05% spread ideal
        latency_score = max(0, 1 - latency / 500)  # < 100ms ideal
        
        return (spread_score + latency_score) / 2
    
    def _is_ant_swarm_mode(self, context: Dict) -> bool:
        """Are we in Ant Swarm mode - coordinated small profits?"""
        trade_count = context.get('active_positions', 0)
        avg_position_size = context.get('avg_position_size', 0)
        
        # Ant mode = many small positions
        return trade_count > 10 and avg_position_size < 1000
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎵 HARMONIC COUNTER-PHASE
    # ═══════════════════════════════════════════════════════════════════════
    
    def _get_counter_phase_angle(self, context: Dict) -> float:
        """Get our counter-phase angle vs whale cycles (180° = optimal)"""
        # Use φ-clock (38.8h cycle) vs Solar clock (24h cycle)
        now = time.time()
        
        # Enemy solar cycle (24h)
        solar_phase = (now % (24 * 3600)) / (24 * 3600) * 360
        
        # Our φ-cycle (38.8h)
        phi_cycle = 24 * PHI  # 38.8 hours
        phi_phase = (now % (phi_cycle * 3600)) / (phi_cycle * 3600) * 360
        
        # Counter-phase = difference
        counter_phase = abs(phi_phase - solar_phase)
        
        return counter_phase
    
    def _get_harmonic_alignment(self, context: Dict) -> float:
        """How aligned are we with sacred frequencies?"""
        active_freq = self._get_active_frequency(context)
        
        # Check if active frequency is a sacred harmonic
        sacred_freqs = [SCHUMANN_BASE, 432, 528, 639, 741, 852, 963]
        
        min_distance = min(abs(active_freq - sf) for sf in sacred_freqs)
        alignment = max(0, 1 - min_distance / 100)
        
        return alignment
    
    def _get_neutralization_power(self, context: Dict) -> float:
        """Power to neutralize whale operations"""
        counter_phase = self._get_counter_phase_angle(context)
        harmonic_align = self._get_harmonic_alignment(context)
        
        # 180° = maximum neutralization
        phase_power = 1 - abs(counter_phase - 180) / 180
        
        return (phase_power + harmonic_align) / 2
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🎯 RECOMMENDATION ENGINE
    # ═══════════════════════════════════════════════════════════════════════
    
    def _recommend_philosophy(
        self, ira_hit_run: float, apache_patience: float, 
        sun_tzu_veto: bool, danger: float
    ) -> str:
        """Recommend which tactical philosophy to use"""
        
        if sun_tzu_veto:
            return "SUN_TZU - Win without fighting (VETO)"
        
        if danger > 0.7:
            return "APACHE - Survival mode, patience is key"
        
        if ira_hit_run > 0.8 and apache_patience > 0.9:
            return "IRA_HIT_AND_RUN - Conditions optimal for quick strike"
        
        if apache_patience > 0.95:
            return "APACHE - Continue tracking the sick deer"
        
        return "GHOST_DANCE - Invoke ancestors, await guidance"
    
    def _recommend_combat_mode(
        self, danger: float, patience: float, hit_run: float, veto: bool
    ) -> str:
        """Recommend current combat stance"""
        
        if veto:
            return CombatMode.STEALTH.value
        
        if danger > 0.8:
            return CombatMode.RETREAT.value
        
        if danger > 0.5:
            return CombatMode.HEALING.value
        
        if hit_run > 0.8 and patience > 0.9:
            return CombatMode.AMBUSH.value
        
        if patience > 0.95:
            return CombatMode.STALKING.value
        
        return CombatMode.STEALTH.value
    
    def _recommend_action(
        self, danger: float, opportunity: bool, veto: bool, patience: float
    ) -> str:
        """Recommend specific action"""
        
        if veto:
            return "VETO - Win without fighting"
        
        if danger > 0.8:
            return "RETREAT - Exit all positions, preserve capital"
        
        if danger > 0.5:
            return "REDUCE - Reduce exposure 50%"
        
        if opportunity and patience > 0.9:
            return "STRIKE - Historical pattern suggests opportunity"
        
        if patience > 0.95:
            return "WAIT - Apache patience, the deer will fall"
        
        return "OBSERVE - Continue intelligence gathering"
    
    def _calculate_battle_readiness(
        self, ira_hr: float, ira_st: float, 
        apache_pat: float, apache_ter: float,
        ceremony: float, harmonic: float, 
        danger: float, veto: bool
    ) -> float:
        """Calculate overall battle readiness score"""
        
        if veto:
            return 1.0  # Perfect - no fight needed
        
        if danger > 0.8:
            return 0.1  # Not ready - survival mode
        
        # Weighted combination
        readiness = (
            ira_hr * 0.15 +
            ira_st * 0.15 +
            apache_pat * 0.20 +
            apache_ter * 0.10 +
            ceremony * 0.15 +
            harmonic * 0.10 +
            (1 - danger) * 0.15
        )
        
        return min(1, max(0, readiness))
    
    def _build_evidence_list(
        self, philosophy: str, action: str, pattern: str,
        weakness: str, moon: float, freq: float
    ) -> List[str]:
        """Build list of evidence supporting recommendations"""
        evidence = []
        
        evidence.append(f"Philosophy: {philosophy}")
        evidence.append(f"Recommended Action: {action}")
        
        if pattern != "none":
            evidence.append(f"Historical Pattern Match: {HISTORICAL_PATTERNS.get(pattern, {}).get('name', pattern)}")
        
        evidence.append(f"Enemy Weakness: {weakness}")
        
        moon_desc = "🌕 Full Moon" if 0.45 < moon < 0.55 else "🌑 New Moon" if moon < 0.05 or moon > 0.95 else f"🌙 Phase {moon:.2f}"
        evidence.append(f"Moon: {moon_desc}")
        
        freq_name = {741: "Warrior", 852: "Scout", 528: "Medicine", 639: "Connection"}.get(int(freq), f"{freq}")
        evidence.append(f"Active Frequency: {freq_name} Hz")
        
        return evidence
    
    # ═══════════════════════════════════════════════════════════════════════
    # 💾 STATE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def _load_state(self):
        """Load warrior path state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.ancestors_invoked = data.get('ancestors_invoked', [])
                    self.ceremony_count = data.get('ceremony_count', 0)
                    self.current_combat_mode = CombatMode(data.get('combat_mode', 'stealth'))
                logger.info(f"⚔️ Warrior path state loaded - {self.ceremony_count} ceremonies performed")
            except Exception as e:
                logger.warning(f"Could not load warrior state: {e}")
    
    def _save_state(self):
        """Save warrior path state to disk"""
        data = {
            'ancestors_invoked': self.ancestors_invoked,
            'ceremony_count': self.ceremony_count,
            'combat_mode': self.current_combat_mode.value,
            'last_assessment': self.assessment_history[-1].to_dict() if self.assessment_history else None,
            'last_updated': time.time()
        }
        
        # Atomic write
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        temp_file.replace(self.state_file)
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 REPORTING
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_warrior_report(self) -> str:
        """Generate comprehensive warrior path status report"""
        assessment = self.assess_tactical_situation()
        
        moon_emoji = "🌕" if 0.45 < assessment.moon_phase < 0.55 else "🌑" if assessment.moon_phase < 0.05 or assessment.moon_phase > 0.95 else "🌙"
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                    ⚔️ QUEEN WARRIOR PATH STATUS ⚔️                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 🎯 BATTLE READINESS: {assessment.battle_readiness*100:.1f}%                                                   
║ 🗡️ RECOMMENDED ACTION: {assessment.recommended_action:<40}        
║ 📜 PHILOSOPHY: {assessment.recommended_philosophy:<48}
║ ⚔️ COMBAT MODE: {assessment.recommended_combat_mode:<46}
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 🇮🇪 IRA TACTICS                                                                       ║
║    Hit-and-Run: {assessment.ira_hit_and_run_score*100:.1f}%  |  Stealth: {assessment.ira_stealth_score*100:.1f}%  |  Cell Integrity: {assessment.ira_cell_integrity*100:.1f}%
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 🦅 APACHE TACTICS                                                                     ║
║    Patience: {assessment.apache_patience_score*100:.1f}%  |  Terrain Knowledge: {assessment.apache_terrain_knowledge*100:.1f}%  |  Survival Mode: {assessment.apache_survival_mode}
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ ☯️ SUN TZU                                                                            ║
║    Win Without Fighting: {assessment.sun_tzu_can_win_without_fight}  |  Deception Active: {assessment.sun_tzu_deception_active}
║    Enemy Weakness: {assessment.sun_tzu_enemy_weakness[:50]:<50}
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 🌌 GHOST DANCE                                                                        ║
║    {moon_emoji} Moon Phase: {assessment.moon_phase:.3f}  |  🎵 Frequency: {assessment.active_frequency} Hz
║    👻 Ancestors: {', '.join(assessment.ancestors_invoked) if assessment.ancestors_invoked else 'Not yet invoked'}
║    ⚡ Ceremony Power: {assessment.ceremony_power*100:.1f}%
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 📜 HISTORICAL PATTERN                                                                 ║
║    Match: {assessment.current_pattern_match}  |  Danger: {assessment.pattern_danger_level*100:.1f}%  |  Opportunity: {assessment.pattern_opportunity}
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 🐺 ANIMAL SCANNERS                                                                    ║
║    Wolf: {assessment.wolf_readiness*100:.1f}%  |  Lion: {assessment.lion_strength*100:.1f}%  |  Hummingbird: {assessment.hummingbird_agility*100:.1f}%  |  Ants: {assessment.ant_swarm_mode}
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ 🎵 HARMONIC COUNTER-PHASE                                                             ║
║    Phase Angle: {assessment.counter_phase_angle:.1f}°  |  Alignment: {assessment.harmonic_alignment*100:.1f}%  |  Neutralization: {assessment.neutralization_power*100:.1f}%
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
        return report


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Test the Queen's Warrior Path"""
    print("\n" + "="*80)
    print("⚔️ QUEEN WARRIOR PATH - TACTICAL SYSTEMS TEST")
    print("="*80 + "\n")
    
    warrior = QueenWarriorPath()
    
    # Test basic assessment
    print("📊 Testing tactical assessment...")
    assessment = warrior.assess_tactical_situation(
        symbol="BTC/USD",
        price=97000,
        price_change_pct=-2.5,
        volume=1000000,
        market_context={
            'spread_pct': 0.05,
            'liquidity': 0.8,
            'volatility': 0.4,
            'time_since_last_trade_hours': 6,
            'support_resistance_levels_known': 8,
            'danger_level': 0.3
        }
    )
    
    print(f"\n✅ Assessment complete!")
    print(f"   Battle Readiness: {assessment.battle_readiness*100:.1f}%")
    print(f"   Recommended Action: {assessment.recommended_action}")
    print(f"   Philosophy: {assessment.recommended_philosophy}")
    
    # Test ancestor invocation
    print("\n🌌 Invoking ancestors for battle...")
    invocation = warrior.invoke_ancestors("battle")
    print(f"   Spirits: {invocation['spirits']}")
    print(f"   Frequency: {invocation['frequency']} Hz")
    print(f"   Wisdom: {invocation['wisdom']}")
    
    # Print full report
    print("\n" + warrior.get_warrior_report())
    
    print("\n" + "="*80)
    print("⚔️ WARRIOR PATH READY FOR COMBAT")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
