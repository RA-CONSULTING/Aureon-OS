#!/usr/bin/env python3
"""
👑🧠 AUREON UNIFIED STARTUP - THE QUEEN'S AWAKENING 👑🧠
═══════════════════════════════════════════════════════════════════════════════

This script unifies ALL startup into a single entry point that ensures:
1. Communication backbone starts FIRST (ThoughtBus, Mycelium)
2. Eyes (Scanners) wake up and start feeding data
3. Brain (Intelligence) systems activate for pattern recognition
4. Queen's Mind comes online (Neural network, consciousness)
5. Orca awakens last (Only executes on Queen's commands)

CRITICAL: The Queen MUST have all her senses (scanners) and intelligence
(brain systems) feeding her BEFORE she can make decisions.

Gary Leckey | January 2026 | Unified Startup Architecture
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import time
import logging
import signal
import threading
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import importlib

# Windows UTF-8 Fix (MANDATORY)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# Enable autonomous control
os.environ['AUREON_ENABLE_AUTONOMOUS_CONTROL'] = '1'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('aureon_unified_startup')


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM DEFINITIONS - THE QUEEN'S COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

class StartupPhase(Enum):
    COMMUNICATION = 1  # ThoughtBus, Mycelium
    EYES = 2          # Scanners (market data, bot detection, whale sonar)
    BRAIN = 3         # Intelligence (predictions, patterns, memory)
    QUEEN_MIND = 4    # Neural network, consciousness, decision engine
    EXECUTION = 5     # Orca Kill Cycle


@dataclass
class SystemDefinition:
    """Defines a system that needs to be started."""
    name: str
    module: str
    class_name: str
    phase: StartupPhase
    priority: int  # Lower = starts first within phase
    optional: bool = False  # If True, failure doesn't block startup
    depends_on: List[str] = field(default_factory=list)
    instance: Any = None
    status: str = "pending"
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# THE MASTER SYSTEM REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

QUEEN_SYSTEMS: List[SystemDefinition] = [
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 1: COMMUNICATION BACKBONE (Must start first!)
    # ════════════════════════════════════════════════════════════════════════
    SystemDefinition(
        name="ThoughtBus",
        module="aureon_thought_bus",
        class_name="ThoughtBus",
        phase=StartupPhase.COMMUNICATION,
        priority=1,
        optional=False
    ),
    SystemDefinition(
        name="Mycelium Network",
        module="aureon_mycelium",
        class_name="MyceliumNetwork",
        phase=StartupPhase.COMMUNICATION,
        priority=2,
        optional=True
    ),
    SystemDefinition(
        name="Chirp Bus",
        module="aureon_chirp_bus",
        class_name="ChirpBus",
        phase=StartupPhase.COMMUNICATION,
        priority=3,
        optional=True
    ),
    
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 2: EYES (Scanners - feed market data to Queen)
    # ════════════════════════════════════════════════════════════════════════
    SystemDefinition(
        name="Global Wave Scanner",
        module="aureon_global_wave_scanner",
        class_name="GlobalWaveScanner",
        phase=StartupPhase.EYES,
        priority=1,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Movers & Shakers Scanner",
        module="aureon_movers_shakers_scanner",
        class_name="MoversShakersScanner",
        phase=StartupPhase.EYES,
        priority=2,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Animal Momentum Scanners",
        module="aureon_animal_momentum_scanners",
        class_name="AnimalMomentumScanners",
        phase=StartupPhase.EYES,
        priority=3,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Bot Shape Scanner",
        module="aureon_bot_shape_scanner",
        class_name="BotShapeScanner",
        phase=StartupPhase.EYES,
        priority=4,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Whale Pattern Mapper",
        module="aureon_whale_pattern_mapper",
        class_name="WhalePatternMapper",
        phase=StartupPhase.EYES,
        priority=5,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Quantum Mirror Scanner",
        module="aureon_quantum_mirror_scanner",
        class_name="QuantumMirrorScanner",
        phase=StartupPhase.EYES,
        priority=6,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 3: BRAIN (Intelligence - pattern recognition, predictions)
    # ════════════════════════════════════════════════════════════════════════
    SystemDefinition(
        name="Probability Ultimate Intelligence",
        module="probability_ultimate_intelligence",
        class_name="ProbabilityUltimateIntelligence",
        phase=StartupPhase.BRAIN,
        priority=1,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Miner Brain",
        module="aureon_miner_brain",
        class_name="MinerBrain",
        phase=StartupPhase.BRAIN,
        priority=2,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Timeline Oracle",
        module="aureon_timeline_oracle",
        class_name="TimelineOracle",
        phase=StartupPhase.BRAIN,
        priority=3,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Probability Nexus",
        module="aureon_probability_nexus",
        class_name="EnhancedProbabilityNexus",
        phase=StartupPhase.BRAIN,
        priority=4,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Elephant Memory",
        module="aureon_elephant_learning",
        class_name="ElephantMemory",
        phase=StartupPhase.BRAIN,
        priority=5,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Enigma Integration",
        module="aureon_enigma_integration",
        class_name="EnigmaIntegration",
        phase=StartupPhase.BRAIN,
        priority=6,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Harmonic Wave Fusion",
        module="aureon_harmonic_fusion",
        class_name="HarmonicWaveFusion",
        phase=StartupPhase.BRAIN,
        priority=7,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 4: QUEEN MIND (Neural network, consciousness, decision engine)
    # ════════════════════════════════════════════════════════════════════════
    SystemDefinition(
        name="Queen Neuron",
        module="queen_neuron",
        class_name="QueenNeuron",
        phase=StartupPhase.QUEEN_MIND,
        priority=1,
        optional=False,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Queen Neuron V2",
        module="queen_neuron_v2",
        class_name="QueenNeuronV2",
        phase=StartupPhase.QUEEN_MIND,
        priority=2,
        optional=True,
        depends_on=["Queen Neuron"]
    ),
    SystemDefinition(
        name="Queen Deep Intelligence",
        module="queen_deep_intelligence",
        class_name="QueenDeepIntelligence",
        phase=StartupPhase.QUEEN_MIND,
        priority=3,
        optional=True,
        depends_on=["ThoughtBus"]
    ),
    SystemDefinition(
        name="Queen Loss Learning",
        module="queen_loss_learning",
        class_name="QueenLossLearningSystem",
        phase=StartupPhase.QUEEN_MIND,
        priority=4,
        optional=True,
        depends_on=["ThoughtBus", "Elephant Memory"]
    ),
    SystemDefinition(
        name="Queen Consciousness",
        module="queen_consciousness_model",
        class_name="QueenConsciousness",
        phase=StartupPhase.QUEEN_MIND,
        priority=5,
        optional=True,
        depends_on=["Queen Neuron"]
    ),
    SystemDefinition(
        name="Queen Sentience Integration",
        module="queen_sentience_integration",
        class_name="QueenSentienceIntegration",
        phase=StartupPhase.QUEEN_MIND,
        priority=6,
        optional=True,
        depends_on=["Queen Consciousness", "Queen Neuron"]
    ),
    SystemDefinition(        name="Queen Authentic Voice",
        module="queen_authentic_voice",
        class_name="QueenAuthenticVoice",
        phase=StartupPhase.QUEEN_MIND,
        priority=7,
        optional=True,
        depends_on=["Queen Sentience Integration", "Queen Voice Engine"]
    ),
    SystemDefinition(        name="Queen Authentic Voice",
        module="queen_authentic_voice",
        class_name="QueenAuthenticVoice",
        phase=StartupPhase.QUEEN_MIND,
        priority=7,
        optional=True,
        depends_on=["Queen Sentience Integration", "Queen Voice Engine"]
    ),
    SystemDefinition(
        name="Queen Hive Mind",
        module="aureon_queen_hive_mind",
        class_name="QueenHiveMind",
        phase=StartupPhase.QUEEN_MIND,
        priority=10,  # Last in this phase - needs everything else
        optional=False,
        depends_on=["ThoughtBus", "Queen Neuron"]
    ),
    SystemDefinition(
        name="Queen-Orca Bridge",
        module="queen_orca_bridge",
        class_name="QueenOrcaBridge",
        phase=StartupPhase.QUEEN_MIND,
        priority=11,
        optional=False,
        depends_on=["Queen Hive Mind"]
    ),
    
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 5: EXECUTION (Orca Kill Cycle - ONLY acts on Queen's commands)
    # ════════════════════════════════════════════════════════════════════════
    SystemDefinition(
        name="Orca Kill Cycle",
        module="orca_complete_kill_cycle",
        class_name="OrcaKillCycle",
        phase=StartupPhase.EXECUTION,
        priority=1,
        optional=False,
        depends_on=["Queen-Orca Bridge", "Queen Hive Mind"]
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED STARTUP ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class QueenUnifiedStartup:
    """
    Orchestrates the complete startup of the Queen's neural empire.
    
    Ensures all systems start in the correct order with proper dependencies.
    """
    
    def __init__(self):
        self.systems = {s.name: s for s in QUEEN_SYSTEMS}
        self.started_systems: List[str] = []
        self.failed_systems: List[str] = []
        self.running = False
        
    def _safe_import(self, system: SystemDefinition) -> Optional[Any]:
        """Safely import and instantiate a system class."""
        try:
            module = importlib.import_module(system.module)
            cls = getattr(module, system.class_name)
            instance = cls()
            return instance
        except ImportError as e:
            system.error = f"Import error: {e}"
            return None
        except AttributeError as e:
            system.error = f"Class not found: {e}"
            return None
        except Exception as e:
            system.error = f"Init error: {e}"
            return None
    
    def _check_dependencies(self, system: SystemDefinition) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in system.depends_on:
            if dep not in self.started_systems:
                return False
        return True
    
    def _start_system(self, system: SystemDefinition) -> bool:
        """Start a single system."""
        # Check dependencies
        if not self._check_dependencies(system):
            logger.warning(f"   ⏳ {system.name}: Waiting for dependencies...")
            return False
        
        # Import and instantiate
        system.status = "starting"
        instance = self._safe_import(system)
        
        if instance is None:
            if system.optional:
                logger.warning(f"   ⚠️  {system.name}: Optional - {system.error}")
                system.status = "skipped"
                return True  # Optional systems don't block
            else:
                logger.error(f"   ❌ {system.name}: REQUIRED - {system.error}")
                system.status = "failed"
                self.failed_systems.append(system.name)
                return False
        
        # Store instance and mark as started
        system.instance = instance
        system.status = "running"
        self.started_systems.append(system.name)
        logger.info(f"   ✅ {system.name}: ONLINE")
        return True
    
    def start_phase(self, phase: StartupPhase) -> bool:
        """Start all systems in a phase."""
        phase_systems = sorted(
            [s for s in self.systems.values() if s.phase == phase],
            key=lambda x: x.priority
        )
        
        if not phase_systems:
            return True
            
        phase_names = {
            StartupPhase.COMMUNICATION: "📡 COMMUNICATION BACKBONE",
            StartupPhase.EYES: "👁️  EYES (Scanners)",
            StartupPhase.BRAIN: "🧠 BRAIN (Intelligence)",
            StartupPhase.QUEEN_MIND: "👑 QUEEN MIND",
            StartupPhase.EXECUTION: "⚔️  EXECUTION (Orca)"
        }
        
        logger.info("")
        logger.info(f"{'=' * 60}")
        logger.info(f"PHASE {phase.value}: {phase_names[phase]}")
        logger.info(f"{'=' * 60}")
        
        # Multiple passes to handle dependencies
        max_passes = 5
        for pass_num in range(max_passes):
            pending = [s for s in phase_systems if s.status == "pending"]
            if not pending:
                break
                
            for system in pending:
                self._start_system(system)
        
        # Check for required systems that failed
        required_failed = [
            s for s in phase_systems 
            if not s.optional and s.status in ("failed", "pending")
        ]
        
        if required_failed:
            for s in required_failed:
                logger.error(f"   ❌ CRITICAL: {s.name} failed to start!")
            return False
            
        return True
    
    def start_all(self) -> bool:
        """Start all systems in order."""
        logger.info("")
        logger.info("👑" * 30)
        logger.info("👑  THE QUEEN'S MIND AWAKENS  👑")
        logger.info("👑" * 30)
        logger.info("")
        
        self.running = True
        
        for phase in StartupPhase:
            if not self.start_phase(phase):
                logger.error(f"❌ Startup FAILED at phase {phase.name}")
                self.running = False
                return False
                
            # Small delay between phases
            time.sleep(0.5)
        
        # Final summary
        logger.info("")
        logger.info("═" * 60)
        logger.info("👑 QUEEN'S MIND FULLY AWAKENED 👑")
        logger.info("═" * 60)
        logger.info(f"   ✅ Systems Online: {len(self.started_systems)}")
        logger.info(f"   ⚠️  Skipped (optional): {sum(1 for s in self.systems.values() if s.status == 'skipped')}")
        logger.info(f"   ❌ Failed: {len(self.failed_systems)}")
        logger.info("")
        
        if self.failed_systems:
            logger.warning(f"   Failed systems: {', '.join(self.failed_systems)}")
        
        return True
    
    def stop_all(self):
        """Stop all systems in reverse order."""
        logger.info("")
        logger.info("🛑 Shutting down Queen's Mind...")
        
        self.running = False
        
        # Stop in reverse order
        for system_name in reversed(self.started_systems):
            system = self.systems[system_name]
            if system.instance:
                try:
                    if hasattr(system.instance, 'stop'):
                        system.instance.stop()
                    elif hasattr(system.instance, 'shutdown'):
                        system.instance.shutdown()
                    logger.info(f"   ✅ {system_name}: Stopped")
                except Exception as e:
                    logger.error(f"   ❌ {system_name}: Error stopping - {e}")
        
        logger.info("🏁 Queen's Mind shutdown complete")
    
    def get_system(self, name: str) -> Optional[Any]:
        """Get a running system instance by name."""
        if name in self.systems:
            return self.systems[name].instance
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all systems."""
        return {
            "running": self.running,
            "started_count": len(self.started_systems),
            "failed_count": len(self.failed_systems),
            "systems": {
                name: {
                    "phase": s.phase.name,
                    "status": s.status,
                    "error": s.error
                }
                for name, s in self.systems.items()
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_queen_startup: Optional[QueenUnifiedStartup] = None

def get_queen_startup() -> QueenUnifiedStartup:
    """Get or create the Queen's unified startup instance."""
    global _queen_startup
    if _queen_startup is None:
        _queen_startup = QueenUnifiedStartup()
    return _queen_startup


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point for unified startup."""
    startup = get_queen_startup()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        startup.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all systems
    if not startup.start_all():
        logger.error("❌ Startup failed!")
        sys.exit(1)
    
    # Keep running
    logger.info("🔄 Queen's Mind running... (press Ctrl+C to stop)")
    try:
        while startup.running:
            time.sleep(1)
    except KeyboardInterrupt:
        startup.stop_all()


if __name__ == "__main__":
    main()
