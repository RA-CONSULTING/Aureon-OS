#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║   🍄 MYCELIUM CONVERSION HUB 🍄                                                   ║
║                                                                                   ║
║   "The Underground Network Where EVERYTHING Connects"                             ║
║                                                                                   ║
║   ALL SYSTEMS → MYCELIUM → ONE GOAL: CONVERSIONS                                 ║
║                                                                                   ║
║   ┌─────────────────────────────────────────────────────────────────────────┐    ║
║   │                    🍄 MYCELIUM NEURAL MESH 🍄                           │    ║
║   │                                                                         │    ║
║   │   ╔═══════════╗  ╔═══════════╗  ╔═══════════╗  ╔═══════════╗           │    ║
║   │   ║ PROBAB.   ║──║ HARMONIC  ║──║  MINER    ║──║ INTERNAL  ║           │    ║
║   │   ║ NEXUS     ║  ║ SYSTEMS   ║  ║  BRAIN    ║  ║ MULTIVERSE║           │    ║
║   │   ╚═════╤═════╝  ╚═════╤═════╝  ╚═════╤═════╝  ╚═════╤═════╝           │    ║
║   │         │              │              │              │                  │    ║
║   │         └──────────────┴──────┬───────┴──────────────┘                  │    ║
║   │                               │                                         │    ║
║   │                    ╔══════════╧══════════╗                              │    ║
║   │                    ║   CONVERSION HUB    ║                              │    ║
║   │                    ║   ═══════════════   ║                              │    ║
║   │                    ║  V14 + MYCELIUM +   ║                              │    ║
║   │                    ║  UNIFIED ECOSYSTEM  ║                              │    ║
║   │                    ╚══════════╤══════════╝                              │    ║
║   │                               │                                         │    ║
║   │         ┌──────────────┬──────┴───────┬──────────────┐                  │    ║
║   │         │              │              │              │                  │    ║
║   │   ╔═════╧═════╗  ╔═════╧═════╗  ╔═════╧═════╗  ╔═════╧═════╗           │    ║
║   │   ║ THOUGHT   ║  ║ MEMORY    ║  ║ LIGHTHOUSE║  ║ OMEGA     ║           │    ║
║   │   ║ BUS       ║  ║ CORE      ║  ║ PATTERNS  ║  ║ CONVERTER ║           │    ║
║   │   ╚═══════════╝  ╚═══════════╝  ╚═══════════╝  ╚═══════════╝           │    ║
║   └─────────────────────────────────────────────────────────────────────────┘    ║
║                                                                                   ║
║   ONE GOAL: BARTER WEAK → STRONG | SNOWBALL GAINS | GROW BUYING POWER           ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════════════════════════
# SYSTEM IMPORTS - Wire ALL systems through the hub
# ═══════════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)


def _configured_max_age_seconds() -> float:
    """Return the provider-evidence TTL without allowing a bad env value to fail open."""
    try:
        value = float(os.getenv("AUREON_CONVERSION_SIGNAL_MAX_AGE_SECONDS", "120"))
    except (TypeError, ValueError):
        return 120.0
    return value if math.isfinite(value) and value > 0 else 120.0


CONVERSION_SIGNAL_MAX_AGE_SECONDS = _configured_max_age_seconds()


def _coerce_source_timestamp(value: Any) -> Optional[datetime]:
    """Parse a provider/source timestamp. Receipt time is never substituted."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        if numeric > 10_000_000_000:
            numeric /= 1000.0
        try:
            parsed = datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh_source_timestamp(value: Any, *, now: Optional[datetime] = None) -> Optional[datetime]:
    parsed = _coerce_source_timestamp(value)
    if parsed is None:
        return None
    reference = now or datetime.now(timezone.utc)
    age = (reference - parsed).total_seconds()
    if age < -5.0 or age > CONVERSION_SIGNAL_MAX_AGE_SECONDS:
        return None
    return parsed


def _finite_number(value: Any, *, minimum: Optional[float] = None,
                   maximum: Optional[float] = None) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    if minimum is not None and numeric < minimum:
        return None
    if maximum is not None and numeric > maximum:
        return None
    return numeric

# 🍄 MYCELIUM NETWORK - The Foundation
try:
    from aureon.core.aureon_mycelium import MyceliumNetwork, Synapse, Neuron, Hive, Agent
    MYCELIUM_AVAILABLE = True
    print("🍄 Mycelium Network LOADED - Neural mesh ready!")
except ImportError as e:
    MYCELIUM_AVAILABLE = False
    print(f"⚠️ Mycelium not available: {e}")

# 🔮 PROBABILITY NEXUS - 80%+ Win Rate
try:
    from aureon.bridges.aureon_probability_nexus import (
        EnhancedProbabilityNexus, AureonProbabilityNexus,
        ProfitFilter, CompoundingEngine
    )
    PROBABILITY_NEXUS_AVAILABLE = True
    print("🔮 Probability Nexus LOADED - 80%+ win rate!")
except ImportError:
    PROBABILITY_NEXUS_AVAILABLE = False

# 💎 ULTIMATE INTELLIGENCE - 95% Accuracy
try:
    from aureon.strategies.probability_ultimate_intelligence import (
        get_ultimate_intelligence, ultimate_predict, record_ultimate_outcome
    )
    ULTIMATE_INTELLIGENCE_AVAILABLE = True
    print("💎 Ultimate Intelligence LOADED - 95% accuracy!")
except ImportError:
    ULTIMATE_INTELLIGENCE_AVAILABLE = False

# 🌌 INTERNAL MULTIVERSE - 10 Worlds
try:
    from aureon.simulation.aureon_internal_multiverse import (
        InternalMultiverse, World, OmegaConverter, ConsensusEngine
    )
    MULTIVERSE_AVAILABLE = True
    print("🌌 Internal Multiverse LOADED - 10 worlds!")
except ImportError:
    MULTIVERSE_AVAILABLE = False

# 🧠 MINER BRAIN - Cognitive Intelligence
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    MINER_BRAIN_AVAILABLE = True
    print("🧠 Miner Brain LOADED - Cognitive intelligence!")
except ImportError:
    MINER_BRAIN_AVAILABLE = False

# 🧠 AUREON BRAIN - Core Decision Engine
try:
    from aureon.intelligence.aureon_brain import AureonBrain
    AUREON_BRAIN_AVAILABLE = True
    print("🧠 Aureon Brain LOADED - Core decisions!")
except ImportError:
    AUREON_BRAIN_AVAILABLE = False

# 🌊 HARMONIC SYSTEMS
try:
    from aureon.harmonic.aureon_harmonic_seed import HarmonicSeedLoader
    HARMONIC_SEED_AVAILABLE = True
    print("🌊 Harmonic Seed LOADED!")
except ImportError:
    HARMONIC_SEED_AVAILABLE = False

try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    HARMONIC_FUSION_AVAILABLE = True
    print("🌊 Harmonic Fusion LOADED!")
except ImportError:
    HARMONIC_FUSION_AVAILABLE = False

# 🗼 LIGHTHOUSE - Pattern Detection
try:
    from aureon.analytics.aureon_lighthouse import AureonLighthouse
    LIGHTHOUSE_AVAILABLE = True
    print("🗼 Lighthouse LOADED - Pattern detection!")
except ImportError:
    LIGHTHOUSE_AVAILABLE = False

# 🧠 MEMORY CORE - Hippocampus
try:
    from aureon.core.aureon_memory_core import memory
    MEMORY_AVAILABLE = True
    print("🧠 Memory Core LOADED!")
except ImportError:
    MEMORY_AVAILABLE = False

# 📡 THOUGHT BUS - Unity Consciousness
try:
    from aureon.core.aureon_thought_bus import ThoughtBus
    THOUGHT_BUS_AVAILABLE = True
    print("📡 Thought Bus LOADED!")
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# 🛡️ IMMUNE SYSTEM - Self Healing
try:
    from aureon.core.aureon_immune_system import AureonImmuneSystem
    IMMUNE_AVAILABLE = True
    print("🛡️ Immune System LOADED!")
except ImportError:
    IMMUNE_AVAILABLE = False

# 🌍 UNIFIED ECOSYSTEM - Master Orchestrator
try:
    from aureon.trading.aureon_unified_ecosystem import (
        AureonUnifiedEcosystem, AdaptiveLearner, 
        StateAggregator, EcosystemBrainBridge
    )
    UNIFIED_ECOSYSTEM_AVAILABLE = True
    print("🌍 Unified Ecosystem LOADED - Master orchestrator!")
except ImportError:
    UNIFIED_ECOSYSTEM_AVAILABLE = False

# 🦅 CONVERSION COMMANDO - 1885 CAPM Game
try:
    from aureon.conversion.aureon_conversion_commando import AdaptiveConversionCommando
    CONVERSION_COMMANDO_AVAILABLE = True
    print("🦅 Conversion Commando LOADED!")
except ImportError:
    CONVERSION_COMMANDO_AVAILABLE = False

# 🎯 V14 SCORING - 100% Win Rate Logic
try:
    from aureon.strategies.s5_v14_dance_enhancements import V14DanceEnhancer, V14ScoringEngine
    V14_AVAILABLE = True
    print("🎯 V14 Scoring LOADED - 100% win rate!")
except ImportError:
    V14_AVAILABLE = False

# 🔱 OMEGA - Complete Orchestrator
try:
    from aureon.trading.aureon_omega import AureonOmega
    OMEGA_AVAILABLE = True
    print("🔱 Omega LOADED!")
except ImportError:
    OMEGA_AVAILABLE = False

# 9️⃣ QGITA - 9 Auris Operators
try:
    from aureon.wisdom.aureon_qgita import run_qgita_state
    QGITA_AVAILABLE = True
    print("9️⃣ QGITA LOADED - 9 Auris operators!")
except ImportError:
    QGITA_AVAILABLE = False

# 📊 HNC PROBABILITY MATRIX
try:
    from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration
    HNC_MATRIX_AVAILABLE = True
    print("📊 HNC Probability Matrix LOADED!")
except ImportError:
    HNC_MATRIX_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════════
# CONVERSION TYPES
# ═══════════════════════════════════════════════════════════════════════════════════

class ConversionSignal(Enum):
    """Signal types from systems"""
    STRONG_BUY = "strong_buy"       # Convert TO this asset
    BUY = "buy"                     # Favor converting TO
    NEUTRAL = "neutral"             # No preference
    SELL = "sell"                   # Convert FROM this asset
    STRONG_SELL = "strong_sell"    # Definitely convert FROM


@dataclass
class SystemSignal:
    """Signal from a single system"""
    system_name: str
    symbol: str
    signal: ConversionSignal
    confidence: float  # 0.0 to 1.0
    score: float       # Raw score
    reason: str
    source_timestamp: Optional[datetime] = None
    provenance: str = ""
    data_status: str = "ok"
    proof_eligible: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MyceliumSignal:
    """Unified signal from all systems through Mycelium"""
    from_asset: str
    to_asset: str
    
    # Individual system signals
    v14_signal: Optional[SystemSignal] = None
    mycelium_signal: Optional[SystemSignal] = None
    probability_signal: Optional[SystemSignal] = None
    multiverse_signal: Optional[SystemSignal] = None
    miner_signal: Optional[SystemSignal] = None
    harmonic_signal: Optional[SystemSignal] = None
    lighthouse_signal: Optional[SystemSignal] = None
    omega_signal: Optional[SystemSignal] = None
    
    # Consensus
    unified_score: float = 0.0
    unified_confidence: float = 0.0
    recommendation: ConversionSignal = ConversionSignal.NEUTRAL
    
    # Pathway info
    pathway_strength: float = 0.0  # How strong the mycelium pathway is
    participating_systems: List[str] = field(default_factory=list)

    # A no_data signal can be displayed, but cannot drive conversion execution
    # or learning.
    data_status: str = "no_data"
    no_data_reason: str = "unscored"
    proof_eligible: bool = False
    source_timestamps: Dict[str, str] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════════════════════════════════
# MYCELIUM CONVERSION HUB
# ═══════════════════════════════════════════════════════════════════════════════════

class MyceliumConversionHub:
    """
    The Central Hub Where ALL Systems Connect Through Mycelium
    
    Every system is a node in the mycelium network.
    Signals flow between systems like nutrients in a fungal network.
    The hub aggregates all signals for conversion decisions.
    """
    
    # System weights for unified scoring
    SYSTEM_WEIGHTS = {
        'v14': 0.25,           # V14 has proven 100% win rate
        'mycelium': 0.20,      # Mycelium consensus
        'probability': 0.20,   # Probability nexus
        'multiverse': 0.15,    # 10 world consensus
        'miner_brain': 0.10,   # Cognitive intelligence
        'harmonic': 0.05,      # Harmonic alignment
        'lighthouse': 0.03,    # Pattern detection
        'omega': 0.02,         # Final verification
    }
    
    def __init__(self, starting_capital: float = 10000.0):
        self.starting_capital = starting_capital
        
        print("\n🍄 INITIALIZING MYCELIUM CONVERSION HUB...")
        print("   Wiring ALL systems through the Mycelium network...")
        print()
        
        # ═══════════════════════════════════════════════════════════════════════
        # Initialize ALL systems
        # ═══════════════════════════════════════════════════════════════════════
        
        # Core Mycelium Network
        self.mycelium: Optional[MyceliumNetwork] = None
        if MYCELIUM_AVAILABLE:
            self.mycelium = MyceliumNetwork(
                initial_capital=starting_capital,
                agents_per_hive=5,
                target_multiplier=2.0
            )
            print("   🍄 Mycelium Network: WIRED")
        
        # V14 Scoring Engine
        self.v14: Optional[V14DanceEnhancer] = None
        if V14_AVAILABLE:
            self.v14 = V14DanceEnhancer()
            print("   🎯 V14 Scoring: WIRED")
        
        # Probability Nexus
        self.probability_nexus: Optional[EnhancedProbabilityNexus] = None
        if PROBABILITY_NEXUS_AVAILABLE:
            self.probability_nexus = EnhancedProbabilityNexus(
                exchange='binance',
                leverage=1.0,
                starting_balance=starting_capital
            )
            print("   🔮 Probability Nexus: WIRED")
        
        # Internal Multiverse
        self.multiverse: Optional[InternalMultiverse] = None
        if MULTIVERSE_AVAILABLE:
            self.multiverse = InternalMultiverse(initial_equity=starting_capital)
            print("   🌌 Internal Multiverse: WIRED")
        
        # Miner Brain
        self.miner_brain: Optional[MinerBrain] = None
        if MINER_BRAIN_AVAILABLE:
            self.miner_brain = MinerBrain()
            print("   🧠 Miner Brain: WIRED")
        
        # Aureon Brain
        self.aureon_brain: Optional[AureonBrain] = None
        if AUREON_BRAIN_AVAILABLE:
            self.aureon_brain = AureonBrain()
            print("   🧠 Aureon Brain: WIRED")
        
        # Harmonic Fusion
        self.harmonic: Optional[HarmonicWaveFusion] = None
        if HARMONIC_FUSION_AVAILABLE:
            try:
                self.harmonic = HarmonicWaveFusion()
                print("   🌊 Harmonic Fusion: WIRED")
            except:
                pass
        
        # Lighthouse
        self.lighthouse: Optional[AureonLighthouse] = None
        if LIGHTHOUSE_AVAILABLE:
            try:
                self.lighthouse = AureonLighthouse()
                print("   🗼 Lighthouse: WIRED")
            except:
                pass
        
        # Unified Ecosystem
        self.unified_ecosystem: Optional[AureonUnifiedEcosystem] = None
        if UNIFIED_ECOSYSTEM_AVAILABLE:
            try:
                self.unified_ecosystem = AureonUnifiedEcosystem()
                print("   🌍 Unified Ecosystem: WIRED")
            except:
                pass
        
        # Conversion Commando
        self.commando: Optional[AdaptiveConversionCommando] = None
        if CONVERSION_COMMANDO_AVAILABLE:
            try:
                self.commando = AdaptiveConversionCommando()
                print("   🦅 Conversion Commando: WIRED")
            except:
                pass
        
        # HNC Probability Matrix
        self.hnc_matrix: Optional[HNCProbabilityIntegration] = None
        if HNC_MATRIX_AVAILABLE:
            try:
                self.hnc_matrix = HNCProbabilityIntegration()
                print("   📊 HNC Probability Matrix: WIRED")
            except:
                pass
        
        # Thought Bus
        self.thought_bus: Optional[ThoughtBus] = None
        if THOUGHT_BUS_AVAILABLE:
            try:
                self.thought_bus = ThoughtBus.get_instance()
                print("   📡 Thought Bus: WIRED")
            except:
                pass
        
        # Omega
        self.omega: Optional[AureonOmega] = None
        if OMEGA_AVAILABLE:
            try:
                self.omega = AureonOmega()
                print("   🔱 Omega: WIRED")
            except:
                pass
        
        # ═══════════════════════════════════════════════════════════════════════
        # Mycelium Pathways - Neural connections between systems
        # ═══════════════════════════════════════════════════════════════════════
        
        self.pathways: Dict[str, Synapse] = {}
        self._create_mycelium_pathways()
        
        # ═══════════════════════════════════════════════════════════════════════
        # Signal aggregation
        # ═══════════════════════════════════════════════════════════════════════
        
        self.signal_history: deque = deque(maxlen=1000)
        self.conversion_history: deque = deque(maxlen=5000)
        
        # Stats
        self.stats = {
            'signals_generated': 0,
            'no_data_signals': 0,
            'last_no_data_reason': None,
            'conversions_recommended': 0,
            'successful_conversions': 0,
            'total_profit': 0.0,
        }
        
        print()
        print("   🍄 MYCELIUM CONVERSION HUB ONLINE!")
        print(f"      Systems wired: {len(self._get_active_systems())}")
        print(f"      Pathways created: {len(self.pathways)}")
        print()
    
    def _get_active_systems(self) -> List[str]:
        """Get list of active systems"""
        systems = []
        if self.mycelium: systems.append('mycelium')
        if self.v14: systems.append('v14')
        if self.probability_nexus: systems.append('probability')
        if self.multiverse: systems.append('multiverse')
        if self.miner_brain: systems.append('miner_brain')
        if self.aureon_brain: systems.append('aureon_brain')
        if self.harmonic: systems.append('harmonic')
        if self.lighthouse: systems.append('lighthouse')
        if self.unified_ecosystem: systems.append('unified_ecosystem')
        if self.commando: systems.append('commando')
        if self.hnc_matrix: systems.append('hnc_matrix')
        if self.thought_bus: systems.append('thought_bus')
        if self.omega: systems.append('omega')
        return systems
    
    def _create_mycelium_pathways(self):
        """Create synaptic pathways between systems"""
        
        # All systems connect to the central hub
        systems = self._get_active_systems()
        
        # Create bi-directional pathways
        for i, sys1 in enumerate(systems):
            for sys2 in systems[i+1:]:
                pathway_id = f"{sys1}_to_{sys2}"
                self.pathways[pathway_id] = Synapse(
                    source_id=sys1,
                    target_id=sys2,
                    weight=1.0,
                    plasticity=0.1
                )
                
                # Reverse pathway
                reverse_id = f"{sys2}_to_{sys1}"
                self.pathways[reverse_id] = Synapse(
                    source_id=sys2,
                    target_id=sys1,
                    weight=1.0,
                    plasticity=0.1
                )
        
        logger.info(f"🍄 Created {len(self.pathways)} mycelium pathways")
    
    def strengthen_pathway(self, from_system: str, to_system: str, reward: float = 0.1):
        """Strengthen a pathway after successful conversion"""
        pathway_id = f"{from_system}_to_{to_system}"
        if pathway_id in self.pathways:
            self.pathways[pathway_id].strengthen(reward)
    
    def weaken_pathway(self, from_system: str, to_system: str, penalty: float = 0.05):
        """Weaken a pathway after failed conversion"""
        pathway_id = f"{from_system}_to_{to_system}"
        if pathway_id in self.pathways:
            self.pathways[pathway_id].weaken(penalty)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SIGNAL GENERATION FROM ALL SYSTEMS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_v14_signal(
        self,
        symbol: str,
        price: float,
        volume: Optional[float],
        source_timestamp: Any = None,
    ) -> Optional[SystemSignal]:
        """Get signal from V14 scoring engine"""
        if not self.v14:
            return None

        observed_at = _fresh_source_timestamp(source_timestamp)
        clean_price = _finite_number(price, minimum=0.000000000001)
        clean_volume = _finite_number(volume, minimum=0.0)
        if observed_at is None or clean_price is None or clean_volume is None:
            return None
        
        try:
            # Update price history
            self.v14.scoring_engine.update_price_history(symbol, clean_price, clean_volume)
            
            # Get score using evaluate_entry
            result = self.v14.evaluate_entry(symbol, clean_price)
            if not isinstance(result, dict) or 'score' not in result:
                return None
            score = _finite_number(result['score'], minimum=0.0, maximum=9.0)
            if score is None:
                return None
            
            # Convert to signal
            if score >= 8:
                signal = ConversionSignal.STRONG_BUY
            elif score >= 6:
                signal = ConversionSignal.BUY
            elif score >= 4:
                signal = ConversionSignal.NEUTRAL
            elif score >= 2:
                signal = ConversionSignal.SELL
            else:
                signal = ConversionSignal.STRONG_SELL
            
            return SystemSignal(
                system_name='v14',
                symbol=symbol,
                signal=signal,
                confidence=score / 9.0,
                score=score,
                reason=f"V14 score: {score}/9",
                source_timestamp=observed_at,
                provenance='v14:provider_price_observation',
            )
        except Exception as e:
            logger.warning(f"V14 signal error: {e}")
            return None
    
    def get_probability_signal(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get signal from probability nexus"""
        if not self.probability_nexus:
            return None
        
        try:
            if not hasattr(self.probability_nexus, 'get_prediction'):
                return None
            pred = self.probability_nexus.get_prediction(symbol)
            if not isinstance(pred, dict) or 'probability' not in pred:
                return None

            prob = _finite_number(pred['probability'], minimum=0.0, maximum=1.0)
            observed_at = _fresh_source_timestamp(
                pred.get('source_timestamp', pred.get('timestamp', pred.get('ts')))
            )
            if prob is None or observed_at is None:
                return None

            signal = ConversionSignal.NEUTRAL
            if prob > 0.65:
                signal = ConversionSignal.BUY
            elif prob < 0.35:
                signal = ConversionSignal.SELL
            reason = f"Probability: {prob:.1%}"
            
            return SystemSignal(
                system_name='probability',
                symbol=symbol,
                signal=signal,
                confidence=prob,
                score=prob,
                reason=reason,
                source_timestamp=observed_at,
                provenance='probability_nexus:provider_derived',
            )
        except Exception as e:
            logger.warning(f"Probability signal error: {e}")
        
        return None
    
    def get_multiverse_signal(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get consensus signal from internal multiverse"""
        if not self.multiverse:
            return None
        
        try:
            worlds = getattr(self.multiverse, 'worlds', None)
            consensus_engine = getattr(self.multiverse, 'consensus', None)
            if not isinstance(worlds, list) or not worlds or consensus_engine is None:
                return None

            votes = []
            source_times = []
            for world in worlds:
                state = getattr(world, 'state', None)
                vote = getattr(state, 'last_signal', None)
                if vote is None or getattr(vote, 'symbol', None) != symbol:
                    return None
                observed_at = _fresh_source_timestamp(getattr(vote, 'timestamp', None))
                strength = _finite_number(
                    getattr(vote, 'strength', None), minimum=-1.0, maximum=1.0
                )
                confidence = _finite_number(
                    getattr(vote, 'confidence', None), minimum=0.0, maximum=1.0
                )
                if (
                    observed_at is None
                    or strength is None
                    or confidence is None
                    or getattr(vote, 'signal_type', None) not in {'BUY', 'SELL', 'HOLD'}
                ):
                    return None
                votes.append(vote)
                source_times.append(observed_at)

            result = consensus_engine.compute_consensus(votes)
            if not isinstance(result, dict):
                return None
            action = result.get('action')
            consensus = _finite_number(
                result.get('strength'), minimum=-1.0, maximum=1.0
            )
            conf = _finite_number(
                result.get('confidence'), minimum=0.0, maximum=1.0
            )
            if action not in {'BUY', 'SELL', 'HOLD'} or consensus is None or conf is None:
                return None

            signal = {
                'BUY': ConversionSignal.BUY,
                'SELL': ConversionSignal.SELL,
                'HOLD': ConversionSignal.NEUTRAL,
            }[action]
            
            return SystemSignal(
                system_name='multiverse',
                symbol=symbol,
                signal=signal,
                confidence=conf,
                score=consensus,
                reason=f"{len(votes)}-world consensus: {consensus:.2f}",
                source_timestamp=min(source_times),
                provenance='internal_multiverse:fresh_world_votes',
            )
        except Exception as e:
            logger.warning(f"Multiverse signal error: {e}")
        
        return None
    
    def get_miner_signal(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get signal from miner brain"""
        if not self.miner_brain:
            return None
        
        try:
            if not hasattr(self.miner_brain, 'get_signal'):
                return None
            result = self.miner_brain.get_signal(symbol)
            if not isinstance(result, dict):
                return None

            raw = _finite_number(result.get('signal'), minimum=-1.0, maximum=1.0)
            confidence = _finite_number(
                result.get('confidence'), minimum=0.0, maximum=1.0
            )
            observed_at = _fresh_source_timestamp(
                result.get('source_timestamp', result.get('timestamp', result.get('ts')))
            )
            if raw is None or confidence is None or observed_at is None:
                return None

            if raw > 0.3:
                signal = ConversionSignal.BUY
            elif raw < -0.3:
                signal = ConversionSignal.SELL
            else:
                signal = ConversionSignal.NEUTRAL
            
            return SystemSignal(
                system_name='miner_brain',
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                score=raw,
                reason=f"Miner cognitive signal: {raw:.3f}",
                source_timestamp=observed_at,
                provenance='miner_brain:fresh_signal',
            )
        except Exception as e:
            logger.warning(f"Miner signal error: {e}")
        
        return None
    
    def get_harmonic_signal(self, symbol: str) -> Optional[SystemSignal]:
        """Get signal from harmonic systems"""
        if not self.harmonic:
            return None
        
        try:
            if not hasattr(self.harmonic, 'get_trading_bias'):
                return None
            result = self.harmonic.get_trading_bias()
            if not isinstance(result, dict):
                return None

            bias = _finite_number(result.get('bias'), minimum=-1.0, maximum=1.0)
            confidence = _finite_number(
                result.get('confidence'), minimum=0.0, maximum=1.0
            )
            observed_at = _fresh_source_timestamp(
                result.get('source_timestamp', result.get('timestamp', result.get('ts')))
            )
            if bias is None or confidence is None or observed_at is None:
                return None

            if bias > 0.3:
                signal = ConversionSignal.BUY
            elif bias < -0.3:
                signal = ConversionSignal.SELL
            else:
                signal = ConversionSignal.NEUTRAL
            
            return SystemSignal(
                system_name='harmonic',
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                score=bias,
                reason=f"Harmonic bias: {bias:.2f}",
                source_timestamp=observed_at,
                provenance='harmonic:fresh_bias',
            )
        except Exception as e:
            logger.warning(f"Harmonic signal error: {e}")
        
        return None
    
    def get_lighthouse_signal(self, symbol: str) -> Optional[SystemSignal]:
        """Get signal from lighthouse pattern detection"""
        if not self.lighthouse:
            return None
        
        try:
            getter = getattr(self.lighthouse, 'get_signal', None)
            if getter is None:
                getter = getattr(self.lighthouse, 'get_pattern_signal', None)
            if not callable(getter):
                return None
            result = getter(symbol)
            if not isinstance(result, dict):
                return None

            action = str(result.get('signal', result.get('action', ''))).upper()
            confidence = _finite_number(
                result.get('confidence'), minimum=0.0, maximum=1.0
            )
            score = _finite_number(result.get('score'), minimum=-1.0, maximum=1.0)
            observed_at = _fresh_source_timestamp(
                result.get('source_timestamp', result.get('timestamp', result.get('ts')))
            )
            signal_map = {
                'STRONG_BUY': ConversionSignal.STRONG_BUY,
                'BUY': ConversionSignal.BUY,
                'HOLD': ConversionSignal.NEUTRAL,
                'NEUTRAL': ConversionSignal.NEUTRAL,
                'SELL': ConversionSignal.SELL,
                'STRONG_SELL': ConversionSignal.STRONG_SELL,
            }
            if (
                action not in signal_map
                or confidence is None
                or score is None
                or observed_at is None
            ):
                return None
            
            return SystemSignal(
                system_name='lighthouse',
                symbol=symbol,
                signal=signal_map[action],
                confidence=confidence,
                score=score,
                reason=str(result.get('reason') or f"Lighthouse signal: {action}"),
                source_timestamp=observed_at,
                provenance='lighthouse:fresh_pattern_signal',
            )
        except Exception as e:
            logger.warning(f"Lighthouse signal error: {e}")
        
        return None
    
    def get_mycelium_consensus(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get consensus from mycelium network"""
        if not self.mycelium:
            return None
        
        try:
            governor = self.mycelium.get_growth_governor()
            metrics = self.mycelium.conversion_metrics
            if (
                not isinstance(governor, dict)
                or not isinstance(metrics, dict)
                or 'allow_entries' not in governor
                or not isinstance(governor['allow_entries'], bool)
                or 'velocity_per_hour' not in metrics
            ):
                return None

            velocity = _finite_number(metrics['velocity_per_hour'])
            observed_at = _fresh_source_timestamp(
                metrics.get('source_timestamp', metrics.get('timestamp', metrics.get('ts')))
            )
            if velocity is None or observed_at is None:
                return None
            
            if velocity > 50 and governor['allow_entries']:
                signal = ConversionSignal.STRONG_BUY
                conf = 0.8
            elif velocity > 20:
                signal = ConversionSignal.BUY
                conf = 0.6
            elif velocity < -20:
                signal = ConversionSignal.SELL
                conf = 0.6
            else:
                signal = ConversionSignal.NEUTRAL
                conf = 0.5
            
            return SystemSignal(
                system_name='mycelium',
                symbol=symbol,
                signal=signal,
                confidence=conf,
                score=velocity,
                reason=f"Velocity: USD {velocity:.2f}/hr",
                source_timestamp=observed_at,
                provenance='mycelium:fresh_conversion_metrics',
            )
        except Exception as e:
            logger.warning(f"Mycelium signal error: {e}")
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # UNIFIED CONVERSION SIGNAL
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _no_data_conversion_signal(
        self,
        from_asset: str,
        to_asset: str,
        reason: str,
    ) -> MyceliumSignal:
        """Return a visible, non-actionable result without contaminating history."""
        stats = getattr(self, 'stats', None)
        if isinstance(stats, dict):
            if 'no_data_signals' not in stats:
                stats['no_data_signals'] = 0
            stats['no_data_signals'] += 1
            stats['last_no_data_reason'] = reason
        return MyceliumSignal(
            from_asset=from_asset,
            to_asset=to_asset,
            unified_score=0.0,
            unified_confidence=0.0,
            recommendation=ConversionSignal.NEUTRAL,
            data_status='no_data',
            no_data_reason=reason,
            proof_eligible=False,
        )

    @staticmethod
    def _valid_system_signal(signal: Optional[SystemSignal]) -> bool:
        if signal is None or signal.data_status != 'ok' or not signal.proof_eligible:
            return False
        return (
            isinstance(signal.signal, ConversionSignal)
            and _finite_number(signal.confidence, minimum=0.0, maximum=1.0) is not None
            and _finite_number(signal.score) is not None
            and _fresh_source_timestamp(signal.source_timestamp) is not None
            and bool(signal.provenance)
        )

    def get_conversion_signal(
        self, 
        from_asset: str, 
        to_asset: str,
        from_price: float,
        to_price: float,
        volume: Optional[float] = None,
        *,
        from_source_timestamp: Any = None,
        to_source_timestamp: Any = None,
        from_volume: Optional[float] = None,
        to_volume: Optional[float] = None,
    ) -> MyceliumSignal:
        """
        Get unified conversion signal from ALL systems through Mycelium.
        
        This is the main method - it queries all systems and aggregates
        their signals through the mycelium pathways.
        """
        
        clean_from_price = _finite_number(from_price, minimum=0.000000000001)
        clean_to_price = _finite_number(to_price, minimum=0.000000000001)
        from_observed_at = _fresh_source_timestamp(from_source_timestamp)
        to_observed_at = _fresh_source_timestamp(to_source_timestamp)
        if clean_from_price is None or clean_to_price is None:
            return self._no_data_conversion_signal(
                from_asset, to_asset, 'malformed_provider_price'
            )
        if from_observed_at is None or to_observed_at is None:
            return self._no_data_conversion_signal(
                from_asset, to_asset, 'missing_or_stale_provider_timestamp'
            )

        # Get signals from all systems for both assets
        from_symbol = f"{from_asset}USDT"
        to_symbol = f"{to_asset}USDT"
        clean_from_volume = from_volume if from_volume is not None else volume
        clean_to_volume = to_volume if to_volume is not None else volume
        
        # FROM asset signals (we want weak = SELL signals)
        v14_from = self.get_v14_signal(
            from_symbol, clean_from_price, clean_from_volume, from_observed_at
        )
        prob_from = self.get_probability_signal(from_symbol, clean_from_price)
        multi_from = self.get_multiverse_signal(from_symbol, clean_from_price)
        miner_from = self.get_miner_signal(from_symbol, clean_from_price)
        harmonic_from = self.get_harmonic_signal(from_symbol)
        lighthouse_from = self.get_lighthouse_signal(from_symbol)
        mycelium_from = self.get_mycelium_consensus(from_symbol, clean_from_price)
        
        # TO asset signals (we want strong = BUY signals)
        v14_to = self.get_v14_signal(
            to_symbol, clean_to_price, clean_to_volume, to_observed_at
        )
        prob_to = self.get_probability_signal(to_symbol, clean_to_price)
        multi_to = self.get_multiverse_signal(to_symbol, clean_to_price)
        miner_to = self.get_miner_signal(to_symbol, clean_to_price)
        harmonic_to = self.get_harmonic_signal(to_symbol)
        lighthouse_to = self.get_lighthouse_signal(to_symbol)
        mycelium_to = self.get_mycelium_consensus(to_symbol, clean_to_price)

        configured_pairs = [
            ('v14', getattr(self, 'v14', None), v14_from, v14_to),
            (
                'probability',
                getattr(self, 'probability_nexus', None),
                prob_from,
                prob_to,
            ),
            ('multiverse', getattr(self, 'multiverse', None), multi_from, multi_to),
            ('miner_brain', getattr(self, 'miner_brain', None), miner_from, miner_to),
            ('harmonic', getattr(self, 'harmonic', None), harmonic_from, harmonic_to),
            (
                'lighthouse',
                getattr(self, 'lighthouse', None),
                lighthouse_from,
                lighthouse_to,
            ),
            ('mycelium', getattr(self, 'mycelium', None), mycelium_from, mycelium_to),
        ]
        expected_pairs = [pair for pair in configured_pairs if pair[1] is not None]
        if not expected_pairs:
            return self._no_data_conversion_signal(
                from_asset, to_asset, 'no_decision_systems_with_evidence'
            )

        missing = [
            name
            for name, _, from_signal, to_signal in expected_pairs
            if not self._valid_system_signal(from_signal)
            or not self._valid_system_signal(to_signal)
        ]
        if missing:
            return self._no_data_conversion_signal(
                from_asset,
                to_asset,
                'missing_stale_or_malformed_factor:' + ','.join(missing),
            )
        
        # Calculate unified score
        # FROM asset: SELL signals are good (we want to convert FROM weak)
        # TO asset: BUY signals are good (we want to convert TO strong)
        
        unified_score = 0.0
        participating_systems = []
        
        def score_signal(sig: SystemSignal, is_from: bool) -> float:
            """Score a signal (inverted for FROM asset)"""
            signal_scores = {
                ConversionSignal.STRONG_BUY: 1.0,
                ConversionSignal.BUY: 0.5,
                ConversionSignal.NEUTRAL: 0.0,
                ConversionSignal.SELL: -0.5,
                ConversionSignal.STRONG_SELL: -1.0,
            }
            
            raw = signal_scores[sig.signal]
            
            # Invert for FROM asset (SELL is good for FROM)
            if is_from:
                raw = -raw
            
            return raw * sig.confidence

        for name, _, from_signal, to_signal in expected_pairs:
            pair_score = score_signal(from_signal, True) + score_signal(to_signal, False)
            unified_score += pair_score * self.SYSTEM_WEIGHTS[name]
            participating_systems.append(name)
        
        # Normalize score to 0-1 range
        unified_score = (unified_score + 2.0) / 4.0  # -2 to +2 → 0 to 1
        unified_confidence = len(participating_systems) / len(self.SYSTEM_WEIGHTS)
        
        # Determine recommendation
        if unified_score >= 0.75:
            recommendation = ConversionSignal.STRONG_BUY  # Strong convert
        elif unified_score >= 0.6:
            recommendation = ConversionSignal.BUY  # Convert
        elif unified_score >= 0.4:
            recommendation = ConversionSignal.NEUTRAL  # Hold
        elif unified_score >= 0.25:
            recommendation = ConversionSignal.SELL  # Don't convert
        else:
            recommendation = ConversionSignal.STRONG_SELL  # Definitely don't
        
        # Calculate pathway strength (average synapse weight of participating systems)
        pathway_strength = 0.0
        for sys in participating_systems:
            for pathway_id, synapse in self.pathways.items():
                if sys in pathway_id:
                    pathway_strength += synapse.weight
        pathway_strength /= max(len(participating_systems) * 2, 1)

        source_timestamps = {
            'price:from': from_observed_at.isoformat(),
            'price:to': to_observed_at.isoformat(),
        }
        for name, _, from_signal, to_signal in expected_pairs:
            source_timestamps[f'{name}:from'] = (
                _coerce_source_timestamp(from_signal.source_timestamp).isoformat()
            )
            source_timestamps[f'{name}:to'] = (
                _coerce_source_timestamp(to_signal.source_timestamp).isoformat()
            )
        
        # Create unified signal
        signal = MyceliumSignal(
            from_asset=from_asset,
            to_asset=to_asset,
            v14_signal=v14_to,  # Use TO asset for display
            mycelium_signal=mycelium_to,
            probability_signal=prob_to,
            multiverse_signal=multi_to,
            miner_signal=miner_to,
            harmonic_signal=harmonic_to,
            lighthouse_signal=lighthouse_to,
            unified_score=unified_score,
            unified_confidence=unified_confidence,
            recommendation=recommendation,
            pathway_strength=pathway_strength,
            participating_systems=participating_systems,
            data_status='ok',
            no_data_reason='',
            proof_eligible=True,
            source_timestamps=source_timestamps,
        )
        
        # Record in history
        self.signal_history.append(signal)
        self.stats['signals_generated'] += 1
        
        # Publish to thought bus if available
        if self.thought_bus:
            try:
                self.thought_bus.think(
                    topic='conversion.signal',
                    content={
                        'from': from_asset,
                        'to': to_asset,
                        'score': unified_score,
                        'recommendation': recommendation.value,
                        'systems': participating_systems,
                        'data_status': signal.data_status,
                        'proof_eligible': signal.proof_eligible,
                        'source_timestamps': source_timestamps,
                    }
                )
            except:
                pass
        
        return signal
    
    def record_conversion_outcome(
        self, 
        from_asset: str, 
        to_asset: str, 
        success: bool, 
        profit: float,
        execution_receipt: Optional[Dict[str, Any]] = None,
        source_timestamp: Any = None,
    ) -> bool:
        """Record a provider-proven outcome for learning.

        A local estimate, dry-run result, or outcome without a fresh execution
        receipt must never strengthen or weaken organism pathways.
        """
        if not isinstance(success, bool) or not isinstance(execution_receipt, dict):
            return False
        receipt_id = (
            execution_receipt.get('receipt_id')
            or execution_receipt.get('order_id')
            or execution_receipt.get('txid')
            or execution_receipt.get('id')
        )
        clean_profit = _finite_number(profit)
        observed_at = _fresh_source_timestamp(
            source_timestamp
            if source_timestamp is not None
            else execution_receipt.get(
                'source_timestamp',
                execution_receipt.get('timestamp', execution_receipt.get('ts')),
            )
        )
        if not receipt_id or clean_profit is None or observed_at is None:
            return False
        
        # Update stats
        if success:
            self.stats['successful_conversions'] += 1
            self.stats['total_profit'] += clean_profit
        
        self.stats['conversions_recommended'] += 1
        
        # Strengthen/weaken pathways based on outcome
        for sys in self._get_active_systems():
            if success:
                self.strengthen_pathway(sys, 'conversion_hub', clean_profit * 0.1)
            else:
                self.weaken_pathway(sys, 'conversion_hub', 0.05)
        
        # Record in mycelium if available
        if self.mycelium:
            self.mycelium.conversion_metrics['total_conversions'] += 1
            if success:
                self.mycelium.conversion_metrics['successful_conversions'] += 1
                self.mycelium.conversion_metrics['total_conversion_profit'] += clean_profit
        
        # Record in unified ecosystem if available
        if self.unified_ecosystem:
            try:
                self.unified_ecosystem.record_trade_outcome({
                    'symbol': f"{from_asset}→{to_asset}",
                    'profit': clean_profit,
                    'success': success,
                    'type': 'conversion',
                    'provider_receipt_id': str(receipt_id),
                    'source_timestamp': observed_at.isoformat(),
                })
            except:
                pass
        return True
    
    def get_hub_status(self) -> Dict[str, Any]:
        """Get current hub status"""
        return {
            'active_systems': self._get_active_systems(),
            'pathway_count': len(self.pathways),
            'signals_generated': self.stats['signals_generated'],
            'no_data_signals': self.stats.get('no_data_signals'),
            'last_no_data_reason': self.stats.get('last_no_data_reason'),
            'conversions': self.stats['conversions_recommended'],
            'successful': self.stats['successful_conversions'],
            'total_profit': self.stats['total_profit'],
            'success_rate': (self.stats['successful_conversions'] / 
                           max(self.stats['conversions_recommended'], 1) * 100),
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════════

_hub_instance: Optional[MyceliumConversionHub] = None

def get_conversion_hub(starting_capital: float = 10000.0) -> MyceliumConversionHub:
    """Get or create the singleton hub instance"""
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = MyceliumConversionHub(starting_capital)
    return _hub_instance


# ═══════════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🍄 TESTING MYCELIUM CONVERSION HUB 🍄\n")
    
    hub = get_conversion_hub(10000.0)
    
    print("\n📊 HUB STATUS:")
    status = hub.get_hub_status()
    for k, v in status.items():
        print(f"   {k}: {v}")
    
    print("\n🔄 TESTING CONVERSION SIGNALS:")
    
    # Test conversion signal
    signal = hub.get_conversion_signal(
        from_asset='ETH',
        to_asset='BTC',
        from_price=3400.0,
        to_price=97000.0,
        volume=1000.0
    )
    
    print(f"\n   ETH → BTC Conversion Signal:")
    print(f"      Unified Score: {signal.unified_score:.1%}")
    print(f"      Confidence: {signal.unified_confidence:.1%}")
    print(f"      Recommendation: {signal.recommendation.value}")
    print(f"      Pathway Strength: {signal.pathway_strength:.2f}")
    print(f"      Participating Systems: {', '.join(signal.participating_systems)}")
    
    print("\n✅ Mycelium Conversion Hub Test Complete!")
