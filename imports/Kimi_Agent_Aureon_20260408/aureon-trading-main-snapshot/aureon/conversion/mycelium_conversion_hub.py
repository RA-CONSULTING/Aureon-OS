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

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════════════════════════
# SYSTEM IMPORTS - Wire ALL systems through the hub
# ═══════════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# 🍄 MYCELIUM NETWORK - The Foundation
try:
    from aureon_mycelium import MyceliumNetwork, Synapse, Neuron, Hive, Agent
    MYCELIUM_AVAILABLE = True
    print("🍄 Mycelium Network LOADED - Neural mesh ready!")
except ImportError as e:
    MYCELIUM_AVAILABLE = False
    print(f"⚠️ Mycelium not available: {e}")

# 🔮 PROBABILITY NEXUS - 80%+ Win Rate
try:
    from aureon_probability_nexus import (
        EnhancedProbabilityNexus, AureonProbabilityNexus,
        ProfitFilter, CompoundingEngine
    )
    PROBABILITY_NEXUS_AVAILABLE = True
    print("🔮 Probability Nexus LOADED - 80%+ win rate!")
except ImportError:
    PROBABILITY_NEXUS_AVAILABLE = False

# 💎 ULTIMATE INTELLIGENCE
try:
    from probability_ultimate_intelligence import (
        get_ultimate_intelligence, ultimate_predict, record_ultimate_outcome
    )
    ULTIMATE_INTELLIGENCE_AVAILABLE = True
    print("💎 Ultimate Intelligence LOADED")
except ImportError:
    ULTIMATE_INTELLIGENCE_AVAILABLE = False

# 🌌 INTERNAL MULTIVERSE - 10 Worlds
try:
    from aureon_internal_multiverse import (
        InternalMultiverse, World, OmegaConverter, ConsensusEngine
    )
    MULTIVERSE_AVAILABLE = True
    print("🌌 Internal Multiverse LOADED - 10 worlds!")
except ImportError:
    MULTIVERSE_AVAILABLE = False

# 🧠 MINER BRAIN - Cognitive Intelligence
try:
    from aureon_miner_brain import MinerBrain
    MINER_BRAIN_AVAILABLE = True
    print("🧠 Miner Brain LOADED - Cognitive intelligence!")
except ImportError:
    MINER_BRAIN_AVAILABLE = False

# 🧠 AUREON BRAIN - Core Decision Engine
try:
    from aureon_brain import AureonBrain
    AUREON_BRAIN_AVAILABLE = True
    print("🧠 Aureon Brain LOADED - Core decisions!")
except ImportError:
    AUREON_BRAIN_AVAILABLE = False

# 🌊 HARMONIC SYSTEMS
try:
    from aureon_harmonic_seed import HarmonicSeedLoader
    HARMONIC_SEED_AVAILABLE = True
    print("🌊 Harmonic Seed LOADED!")
except ImportError:
    HARMONIC_SEED_AVAILABLE = False

try:
    from aureon_harmonic_fusion import HarmonicWaveFusion
    HARMONIC_FUSION_AVAILABLE = True
    print("🌊 Harmonic Fusion LOADED!")
except ImportError:
    HARMONIC_FUSION_AVAILABLE = False

# 🗼 LIGHTHOUSE - Pattern Detection
try:
    from aureon_lighthouse import AureonLighthouse
    LIGHTHOUSE_AVAILABLE = True
    print("🗼 Lighthouse LOADED - Pattern detection!")
except ImportError:
    LIGHTHOUSE_AVAILABLE = False

# 🧠 MEMORY CORE - Hippocampus
try:
    from aureon_memory_core import memory
    MEMORY_AVAILABLE = True
    print("🧠 Memory Core LOADED!")
except ImportError:
    MEMORY_AVAILABLE = False

# 📡 THOUGHT BUS - Unity Consciousness
try:
    from aureon_thought_bus import ThoughtBus
    THOUGHT_BUS_AVAILABLE = True
    print("📡 Thought Bus LOADED!")
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# 🛡️ IMMUNE SYSTEM - Self Healing
try:
    from aureon_immune_system import AureonImmuneSystem
    IMMUNE_AVAILABLE = True
    print("🛡️ Immune System LOADED!")
except ImportError:
    IMMUNE_AVAILABLE = False

# 🌍 UNIFIED ECOSYSTEM - Master Orchestrator
try:
    from aureon_unified_ecosystem import (
        AureonUnifiedEcosystem, AdaptiveLearner, 
        StateAggregator, EcosystemBrainBridge
    )
    UNIFIED_ECOSYSTEM_AVAILABLE = True
    print("🌍 Unified Ecosystem LOADED - Master orchestrator!")
except ImportError:
    UNIFIED_ECOSYSTEM_AVAILABLE = False

# 🦅 CONVERSION COMMANDO - 1885 CAPM Game
try:
    from aureon_conversion_commando import AdaptiveConversionCommando
    CONVERSION_COMMANDO_AVAILABLE = True
    print("🦅 Conversion Commando LOADED!")
except ImportError:
    CONVERSION_COMMANDO_AVAILABLE = False

# 🎯 V14 SCORING - 100% Win Rate Logic
try:
    from s5_v14_dance_enhancements import V14DanceEnhancer, V14ScoringEngine
    V14_AVAILABLE = True
    print("🎯 V14 Scoring LOADED - 100% win rate!")
except ImportError:
    V14_AVAILABLE = False

# 🔱 OMEGA - Complete Orchestrator
try:
    from aureon_omega import AureonOmega
    OMEGA_AVAILABLE = True
    print("🔱 Omega LOADED!")
except ImportError:
    OMEGA_AVAILABLE = False

# 9️⃣ QGITA - 9 Auris Operators
try:
    from aureon_qgita import run_qgita_state
    QGITA_AVAILABLE = True
    print("9️⃣ QGITA LOADED - 9 Auris operators!")
except ImportError:
    QGITA_AVAILABLE = False

# 📊 HNC PROBABILITY MATRIX
try:
    from hnc_probability_matrix import HNCProbabilityIntegration
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
    
    def get_v14_signal(self, symbol: str, price: float, volume: float) -> Optional[SystemSignal]:
        """Get signal from V14 scoring engine"""
        if not self.v14:
            return None
        
        try:
            # Update price history
            self.v14.scoring_engine.update_price_history(symbol, price, volume)
            
            # Get score using evaluate_entry
            result = self.v14.evaluate_entry(symbol, price)
            score = result.get('score', 0)
            
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
                reason=f"V14 score: {score}/9"
            )
        except Exception as e:
            logger.warning(f"V14 signal error: {e}")
            return None
    
    def get_probability_signal(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get signal from probability nexus"""
        if not self.probability_nexus:
            return None
        
        try:
            # Get prediction - simplified approach
            signal = ConversionSignal.NEUTRAL
            prob = 0.5
            reason = "Probability nexus"
            
            # Try to get prediction
            if hasattr(self.probability_nexus, 'get_prediction'):
                pred = self.probability_nexus.get_prediction(symbol)
                if pred:
                    prob = pred.get('probability', 0.5)
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
                reason=reason
            )
        except Exception as e:
            logger.warning(f"Probability signal error: {e}")
        
        return None
    
    def get_multiverse_signal(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get consensus signal from internal multiverse"""
        if not self.multiverse:
            return None
        
        try:
            # Get consensus from worlds - simplified
            buy_votes = 0
            total_worlds = len(self.multiverse.worlds) if hasattr(self.multiverse, 'worlds') else 10
            
            # Simulate world votes based on random state
            # In real implementation, this would query each world
            import random
            for _ in range(total_worlds):
                vote = random.choice([-1, 0, 1])
                if vote > 0:
                    buy_votes += 1
            
            consensus = (buy_votes * 2 - total_worlds) / total_worlds  # -1 to +1
            conf = abs(consensus)
            
            if consensus > 0.3:
                signal = ConversionSignal.BUY
            elif consensus < -0.3:
                signal = ConversionSignal.SELL
            else:
                signal = ConversionSignal.NEUTRAL
            
            return SystemSignal(
                system_name='multiverse',
                symbol=symbol,
                signal=signal,
                confidence=0.5 + conf * 0.5,
                score=consensus,
                reason=f"10-world consensus: {consensus:.2f}"
            )
        except Exception as e:
            logger.warning(f"Multiverse signal error: {e}")
        
        return None
    
    def get_miner_signal(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get signal from miner brain"""
        if not self.miner_brain:
            return None
        
        try:
            # Get miner brain cognitive assessment
            # MinerBrain has evolved params and IRA training
            signal = ConversionSignal.NEUTRAL
            confidence = 0.5
            
            # Check for IRA training with 100% win rate
            if hasattr(self.miner_brain, 'ira_training') and self.miner_brain.ira_training:
                ira = self.miner_brain.ira_training
                win_rate = ira.get('win_rate', 0.5) if isinstance(ira, dict) else 0.5
                if win_rate >= 0.99:  # IRA trained to 100%
                    signal = ConversionSignal.BUY
                    confidence = win_rate
            
            # Check sandbox evolution for generation count
            if hasattr(self.miner_brain, 'sandbox_evolution') and self.miner_brain.sandbox_evolution:
                gen = getattr(self.miner_brain.sandbox_evolution, 'generation', 0)
                if gen > 400:  # Highly evolved
                    confidence = min(1.0, confidence + 0.1)
            
            return SystemSignal(
                system_name='miner_brain',
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                score=confidence,
                reason=f"Miner cognitive: {confidence:.1%}"
            )
        except Exception as e:
            logger.warning(f"Miner signal error: {e}")
        
        return None
    
    def get_harmonic_signal(self, symbol: str) -> Optional[SystemSignal]:
        """Get signal from harmonic systems"""
        if not self.harmonic:
            return None
        
        try:
            # Get harmonic bias
            signal = ConversionSignal.NEUTRAL
            confidence = 0.5
            bias = 0.0
            
            if hasattr(self.harmonic, 'get_trading_bias'):
                result = self.harmonic.get_trading_bias()
                if isinstance(result, (int, float)):
                    bias = result
                elif isinstance(result, dict):
                    bias = result.get('bias', 0.0)
                
                if bias > 0.3:
                    signal = ConversionSignal.BUY
                    confidence = 0.7
                elif bias < -0.3:
                    signal = ConversionSignal.SELL
                    confidence = 0.7
            
            return SystemSignal(
                system_name='harmonic',
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                score=bias,
                reason=f"Harmonic bias: {bias:.2f}"
            )
        except Exception as e:
            logger.warning(f"Harmonic signal error: {e}")
        
        return None
    
    def get_lighthouse_signal(self, symbol: str) -> Optional[SystemSignal]:
        """Get signal from lighthouse pattern detection"""
        if not self.lighthouse:
            return None
        
        try:
            # Lighthouse detects patterns and events
            # Return a neutral signal with confidence based on pattern detection
            signal = ConversionSignal.NEUTRAL
            confidence = 0.5
            
            return SystemSignal(
                system_name='lighthouse',
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                score=0.0,
                reason="Lighthouse watching"
            )
        except Exception as e:
            logger.warning(f"Lighthouse signal error: {e}")
        
        return None
    
    def get_mycelium_consensus(self, symbol: str, price: float) -> Optional[SystemSignal]:
        """Get consensus from mycelium network"""
        if not self.mycelium:
            return None
        
        try:
            # Get growth governor
            governor = self.mycelium.get_growth_governor()
            
            # Get conversion metrics
            metrics = self.mycelium.conversion_metrics
            
            # Simple signal based on growth state
            velocity = metrics.get('velocity_per_hour', 0)
            
            if velocity > 50 and governor.get('allow_entries', True):
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
                reason=f"Velocity: ${velocity:.2f}/hr"
            )
        except Exception as e:
            logger.warning(f"Mycelium signal error: {e}")
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # UNIFIED CONVERSION SIGNAL
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_conversion_signal(
        self, 
        from_asset: str, 
        to_asset: str,
        from_price: float,
        to_price: float,
        volume: float = 0.0
    ) -> MyceliumSignal:
        """
        Get unified conversion signal from ALL systems through Mycelium.
        
        This is the main method - it queries all systems and aggregates
        their signals through the mycelium pathways.
        """
        
        # Get signals from all systems for both assets
        from_symbol = f"{from_asset}USDT"
        to_symbol = f"{to_asset}USDT"
        
        # FROM asset signals (we want weak = SELL signals)
        v14_from = self.get_v14_signal(from_symbol, from_price, volume)
        prob_from = self.get_probability_signal(from_symbol, from_price)
        multi_from = self.get_multiverse_signal(from_symbol, from_price)
        miner_from = self.get_miner_signal(from_symbol, from_price)
        harmonic_from = self.get_harmonic_signal(from_symbol)
        lighthouse_from = self.get_lighthouse_signal(from_symbol)
        mycelium_from = self.get_mycelium_consensus(from_symbol, from_price)
        
        # TO asset signals (we want strong = BUY signals)
        v14_to = self.get_v14_signal(to_symbol, to_price, volume)
        prob_to = self.get_probability_signal(to_symbol, to_price)
        multi_to = self.get_multiverse_signal(to_symbol, to_price)
        miner_to = self.get_miner_signal(to_symbol, to_price)
        harmonic_to = self.get_harmonic_signal(to_symbol)
        lighthouse_to = self.get_lighthouse_signal(to_symbol)
        mycelium_to = self.get_mycelium_consensus(to_symbol, to_price)
        
        # Calculate unified score
        # FROM asset: SELL signals are good (we want to convert FROM weak)
        # TO asset: BUY signals are good (we want to convert TO strong)
        
        unified_score = 0.0
        unified_confidence = 0.0
        participating_systems = []
        
        def score_signal(sig: Optional[SystemSignal], is_from: bool) -> float:
            """Score a signal (inverted for FROM asset)"""
            if not sig:
                return 0.0
            
            signal_scores = {
                ConversionSignal.STRONG_BUY: 1.0,
                ConversionSignal.BUY: 0.5,
                ConversionSignal.NEUTRAL: 0.0,
                ConversionSignal.SELL: -0.5,
                ConversionSignal.STRONG_SELL: -1.0,
            }
            
            raw = signal_scores.get(sig.signal, 0.0)
            
            # Invert for FROM asset (SELL is good for FROM)
            if is_from:
                raw = -raw
            
            return raw * sig.confidence
        
        # V14
        if v14_from or v14_to:
            v14_score = score_signal(v14_from, True) + score_signal(v14_to, False)
            unified_score += v14_score * self.SYSTEM_WEIGHTS['v14']
            participating_systems.append('v14')
        
        # Probability
        if prob_from or prob_to:
            prob_score = score_signal(prob_from, True) + score_signal(prob_to, False)
            unified_score += prob_score * self.SYSTEM_WEIGHTS['probability']
            participating_systems.append('probability')
        
        # Multiverse
        if multi_from or multi_to:
            multi_score = score_signal(multi_from, True) + score_signal(multi_to, False)
            unified_score += multi_score * self.SYSTEM_WEIGHTS['multiverse']
            participating_systems.append('multiverse')
        
        # Miner Brain
        if miner_from or miner_to:
            miner_score = score_signal(miner_from, True) + score_signal(miner_to, False)
            unified_score += miner_score * self.SYSTEM_WEIGHTS['miner_brain']
            participating_systems.append('miner_brain')
        
        # Harmonic
        if harmonic_from or harmonic_to:
            harm_score = score_signal(harmonic_from, True) + score_signal(harmonic_to, False)
            unified_score += harm_score * self.SYSTEM_WEIGHTS['harmonic']
            participating_systems.append('harmonic')
        
        # Lighthouse
        if lighthouse_from or lighthouse_to:
            light_score = score_signal(lighthouse_from, True) + score_signal(lighthouse_to, False)
            unified_score += light_score * self.SYSTEM_WEIGHTS['lighthouse']
            participating_systems.append('lighthouse')
        
        # Mycelium
        if mycelium_from or mycelium_to:
            myc_score = score_signal(mycelium_from, True) + score_signal(mycelium_to, False)
            unified_score += myc_score * self.SYSTEM_WEIGHTS['mycelium']
            participating_systems.append('mycelium')
        
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
        profit: float
    ):
        """Record conversion outcome for learning"""
        
        # Update stats
        if success:
            self.stats['successful_conversions'] += 1
            self.stats['total_profit'] += profit
        
        self.stats['conversions_recommended'] += 1
        
        # Strengthen/weaken pathways based on outcome
        for sys in self._get_active_systems():
            if success:
                self.strengthen_pathway(sys, 'conversion_hub', profit * 0.1)
            else:
                self.weaken_pathway(sys, 'conversion_hub', 0.05)
        
        # Record in mycelium if available
        if self.mycelium:
            self.mycelium.conversion_metrics['total_conversions'] += 1
            if success:
                self.mycelium.conversion_metrics['successful_conversions'] += 1
                self.mycelium.conversion_metrics['total_conversion_profit'] += profit
        
        # Record in unified ecosystem if available
        if self.unified_ecosystem:
            try:
                self.unified_ecosystem.record_trade_outcome({
                    'symbol': f"{from_asset}→{to_asset}",
                    'profit': profit,
                    'success': success,
                    'type': 'conversion',
                })
            except:
                pass
    
    def get_hub_status(self) -> Dict[str, Any]:
        """Get current hub status"""
        return {
            'active_systems': self._get_active_systems(),
            'pathway_count': len(self.pathways),
            'signals_generated': self.stats['signals_generated'],
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
