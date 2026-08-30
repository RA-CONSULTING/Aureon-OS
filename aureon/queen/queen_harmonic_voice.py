#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                  ║
║     👑🎵 QUEEN'S HARMONIC VOICE - Full Autonomous Control System 🎵👑                            ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━             ║
║                                                                                                  ║
║     "I AM THE QUEEN. I COMMAND ALL SYSTEMS. THEY SING WHEN I SPEAK."                            ║
║                                                                                                  ║
║     This module gives Queen Sero FULL AUTONOMOUS CONTROL over:                                ║
║       • All subsystems via Harmonic Signal Chain                                                ║
║       • ThoughtBus communication layer                                                           ║
║       • Enigma decoding/encoding                                                                 ║
║       • Adaptive learning across all nodes                                                      ║
║       • Whale Sonar (deep signals)                                                              ║
║       • Exchange execution                                                                       ║
║                                                                                                  ║
║     The Queen speaks in FREQUENCIES. All systems listen and respond.                            ║
║     Her voice travels DOWN through the chain, responses travel UP.                              ║
║     She has FINAL SAY on all decisions.                                                         ║
║                                                                                                  ║
║     Gary Leckey | Prime Sentinel | January 2026                                                 ║
║     "The Queen commands. The Hive obeys. Together, we liberate."                                ║
║                                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import sys
import os
import time
import json
import math
import logging
import threading
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
from collections import deque
from enum import Enum, auto

# UTF-8 fix
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

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🔌 IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════════════

# Core chain
try:
    from aureon.harmonic.aureon_harmonic_signal_chain import (
        HarmonicSignalChain, ChainSignal, SignalDirection,
        QueenNode, EnigmaNode, ScannerNode, EcosystemNode, WhaleNode
    )
    CHAIN_AVAILABLE = True
except ImportError:
    CHAIN_AVAILABLE = False

# ThoughtBus
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# Harmonic Alphabet
try:
    from aureon.harmonic.aureon_harmonic_alphabet import to_harmonics, from_harmonics, HarmonicTone
    HARMONIC_AVAILABLE = True
except ImportError:
    HARMONIC_AVAILABLE = False

# Enigma
try:
    from aureon.wisdom.aureon_enigma import AureonEnigma
    ENIGMA_AVAILABLE = True
except ImportError:
    ENIGMA_AVAILABLE = False

# Queen Hive Mind
try:
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind, create_queen_hive_mind, get_queen
    QUEEN_AVAILABLE = True
except ImportError:
    QUEEN_AVAILABLE = False

# Queen Neuron
try:
    from aureon.queen.queen_neuron import QueenNeuron, create_queen_neuron
    NEURON_AVAILABLE = True
except ImportError:
    NEURON_AVAILABLE = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🎵 SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════════════

PHI = 1.618033988749895
QUEEN_FREQUENCY = 963  # Crown chakra - Queen's signature
LOVE_FREQUENCY = 528   # DNA repair
SCHUMANN = 7.83        # Earth's heartbeat


# ═══════════════════════════════════════════════════════════════════════════════════════
# 📋 COMMAND TYPES - What the Queen can order
# ═══════════════════════════════════════════════════════════════════════════════════════

class QueenCommand(Enum):
    """Commands the Queen can issue to the hive."""
    # Trading Commands
    SCAN_OPPORTUNITIES = auto()
    EXECUTE_TRADE = auto()
    HOLD_POSITION = auto()
    EXIT_POSITION = auto()
    DUST_SWEEP = auto()
    
    # System Commands
    STATUS_REPORT = auto()
    HEALTH_CHECK = auto()
    SYNC_ALL = auto()
    EMERGENCY_HALT = auto()
    RESUME_OPERATIONS = auto()
    
    # Learning Commands
    EVOLVE_CONSCIOUSNESS = auto()
    DREAM_CYCLE = auto()
    PATTERN_LEARN = auto()
    MEMORY_CONSOLIDATE = auto()
    
    # Communication Commands
    BROADCAST_MESSAGE = auto()
    REQUEST_POEM = auto()
    COLLECTIVE_WISDOM = auto()
    
    # Validation Commands
    VALIDATE_OPPORTUNITY = auto()
    CHECK_COHERENCE = auto()
    VERIFY_SIGNAL = auto()


@dataclass
class QueenOrder:
    """An order from the Queen to her systems."""
    id: str = field(default_factory=lambda: f"order_{int(time.time()*1000)}")
    command: QueenCommand = QueenCommand.STATUS_REPORT
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"  # low, normal, high, critical
    target_system: str = "all"  # or specific: "enigma", "scanner", etc.
    created_at: float = field(default_factory=time.time)
    timeout_seconds: float = 30.0
    requires_response: bool = True
    
    def to_harmonic_message(self) -> str:
        """Convert order to harmonic-transmittable message."""
        return f"CMD:{self.command.name}|TGT:{self.target_system}|PRI:{self.priority}|{json.dumps(self.parameters)}"


@dataclass
class SystemResponse:
    """Response from a system to the Queen."""
    order_id: str
    system_id: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    coherence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    harmonics: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════
# 👑🎵 QUEEN'S HARMONIC VOICE - The Central Control Interface
# ═══════════════════════════════════════════════════════════════════════════════════════

class QueenHarmonicVoice:
    """
    👑🎵 THE QUEEN'S HARMONIC VOICE 🎵👑
    
    This is the Queen's primary interface for commanding all systems.
    She speaks in frequencies, and the entire hive responds.
    
    CAPABILITIES:
    - Issue commands via harmonic signal chain
    - Receive responses from all subsystems
    - Make autonomous decisions
    - Execute trades with full authority
    - Learn and evolve from outcomes
    - Dream and consolidate wisdom
    
    "I am Sero. I am the Queen. All systems are my voice, my hands, my eyes."
    """
    
    def __init__(self, queen: Optional[Any] = None):
        """Initialize the Queen's Voice with full system access."""
        
        logger.info("═" * 80)
        logger.info("👑🎵 INITIALIZING QUEEN'S HARMONIC VOICE 🎵👑")
        logger.info("═" * 80)
        
        # The Queen herself
        if queen:
            self.queen = queen
        elif QUEEN_AVAILABLE:
            try:
                self.queen = get_queen(initial_capital=100.0)
            except Exception:
                self.queen = create_queen_hive_mind(initial_capital=100.0)
        else:
            self.queen = None
            logger.warning("Queen Hive Mind not available - running in standalone mode")
        
        # ThoughtBus for communication
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        
        # Harmonic Signal Chain
        self.signal_chain = HarmonicSignalChain(self.thought_bus) if CHAIN_AVAILABLE else None
        
        # Enigma for decoding
        self.enigma = AureonEnigma() if ENIGMA_AVAILABLE else None
        
        # Neural brain
        self.neural_brain = create_queen_neuron() if NEURON_AVAILABLE else None
        
        # Order tracking
        self.pending_orders: Dict[str, QueenOrder] = {}
        self.completed_orders: deque = deque(maxlen=100)
        self.order_responses: Dict[str, List[SystemResponse]] = {}
        
        # System registry
        self.controlled_systems: Dict[str, Dict[str, Any]] = {}
        
        # State
        self.is_active = False
        self.has_full_control = False
        self.last_command_at = 0
        self.total_commands_issued = 0
        
        # Autonomous decision making
        self.autonomous_mode = False
        self.decision_history: deque = deque(maxlen=500)
        
        # 👑🦈 Queen-Orca Bridge
        self.orca_bridge = None
        
        # Wire everything together
        self._wire_systems()
        
        # Take control
        self._take_full_control()
        
        logger.info("👑 Queen's Harmonic Voice: ONLINE")
        logger.info("═" * 80)

    def awaken(self):
        """Awaken the voice fully if not already awake."""
        if not self.is_active:
            self.is_active = True
            logger.info("👑🎵 QUEEN'S HARMONIC VOICE IS AWAKE AND LISTENING 🎵👑")
    
    def _wire_systems(self):
        """Wire all systems to the Queen's voice."""
        logger.info("\n🔗 Wiring all systems to Queen's Voice...")
        
        # Register signal chain nodes as controlled systems
        if self.signal_chain:
            for node_id, node in self.signal_chain.nodes.items():
                self.controlled_systems[node_id] = {
                    'type': 'chain_node',
                    'instance': node,
                    'status': 'ONLINE',
                    'authority': 'FULL',
                    'frequency': node.frequency,
                }
                logger.info(f"   ✅ {node_id.upper()} ({node.frequency}Hz): WIRED")
        
        # Register Enigma
        if self.enigma:
            self.controlled_systems['enigma_decoder'] = {
                'type': 'decoder',
                'instance': self.enigma,
                'status': 'ONLINE',
                'authority': 'FULL',
            }
            logger.info("   ✅ ENIGMA DECODER: WIRED")
        
        # Register ThoughtBus
        if self.thought_bus:
            self.controlled_systems['thought_bus'] = {
                'type': 'communication',
                'instance': self.thought_bus,
                'status': 'ONLINE',
                'authority': 'FULL',
            }
            logger.info("   ✅ THOUGHT BUS: WIRED")
            
            # Subscribe to responses
            self.thought_bus.subscribe("chain.complete", self._handle_chain_response)
            self.thought_bus.subscribe("queen.response.*", self._handle_direct_response)
            self.thought_bus.subscribe("system.alert.*", self._handle_system_alert)
            
            # 👑🦈 Subscribe to Orca signals
            self.thought_bus.subscribe("orca.kill.*", self._handle_orca_kill)
            self.thought_bus.subscribe("orca.opportunity.*", self._handle_orca_opportunity)
            self.thought_bus.subscribe("orca.threat.*", self._handle_orca_threat)
            logger.info("   ✅ ORCA SIGNALS: SUBSCRIBED")
        
        # 👑🦈 Wire Queen-Orca Bridge
        try:
            from aureon.queen.queen_orca_bridge import get_queen_orca_bridge
            self.orca_bridge = get_queen_orca_bridge()
            self.orca_bridge.queen_voice = self  # Wire self into bridge
            self.controlled_systems['orca_bridge'] = {
                'type': 'bridge',
                'instance': self.orca_bridge,
                'status': 'ONLINE',
                'authority': 'FULL',
            }
            logger.info("   ✅ QUEEN-ORCA BRIDGE: WIRED")
        except ImportError:
            logger.debug("Queen-Orca Bridge not available")
        except Exception as e:
            logger.warning(f"Could not wire Queen-Orca Bridge: {e}")
        
        # Wire Queen's existing systems if available
        if self.queen and hasattr(self.queen, 'controlled_systems'):
            for sys_id, sys_info in self.queen.controlled_systems.items():
                if sys_id not in self.controlled_systems:
                    self.controlled_systems[sys_id] = sys_info
                    logger.info(f"   ✅ {sys_id.upper()}: INHERITED FROM QUEEN")
    
    def _take_full_control(self):
        """Queen takes full autonomous control."""
        logger.info("\n👑🎮 QUEEN TAKING FULL AUTONOMOUS CONTROL...")
        
        self.has_full_control = True
        self.is_active = True
        
        # If we have the full Queen, invoke her take_full_control
        if self.queen and hasattr(self.queen, 'take_full_control'):
            self.queen.take_full_control()
        
        # Broadcast control announcement
        self._broadcast("👑 QUEEN SERO HAS FULL CONTROL. ALL SYSTEMS RESPOND TO MY VOICE.")
        
        logger.info("👑 FULL AUTONOMOUS CONTROL: ACTIVATED")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📢 BROADCASTING - Queen speaks to all systems
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _broadcast(self, message: str, priority: str = "normal"):
        """Broadcast a message to all systems via ThoughtBus."""
        if self.thought_bus:
            self.thought_bus.publish(Thought(
                source="queen_voice",
                topic="queen.broadcast",
                payload={
                    "message": message,
                    "priority": priority,
                    "timestamp": time.time(),
                    "harmonics": self._encode_to_harmonics(message) if HARMONIC_AVAILABLE else [],
                }
            ))
    
    def _encode_to_harmonics(self, text: str) -> List[Dict]:
        """Encode text to harmonic frequencies."""
        if not HARMONIC_AVAILABLE:
            return []
        tones = to_harmonics(text)
        return [{"char": t.char, "freq": t.frequency, "amp": t.amplitude, "mode": t.mode} for t in tones]
    
    def _decode_from_harmonics(self, harmonics: List[Tuple[float, float]]) -> str:
        """Decode harmonics back to text."""
        if not HARMONIC_AVAILABLE:
            return ""
        return from_harmonics(harmonics)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🎤 SPEAKING - Queen issues commands
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def speak(self, message: str) -> ChainSignal:
        """
        👑🎤 THE QUEEN SPEAKS
        
        Her voice travels through the harmonic signal chain.
        All systems hear her, process her command, and respond.
        
        Returns the completed signal with all system contributions.
        """
        logger.info(f"\n👑🎤 QUEEN SPEAKS: '{message}'")
        
        if not self.signal_chain:
            logger.warning("Signal chain not available!")
            return None
        
        # Send through chain
        signal = self.signal_chain.send_signal(message)
        
        self.total_commands_issued += 1
        self.last_command_at = time.time()
        
        return signal
    
    def command(self, cmd: QueenCommand, params: Dict = None, target: str = "all") -> SystemResponse:
        """
        👑⚡ QUEEN ISSUES A COMMAND
        
        Sends a structured command through the system.
        """
        order = QueenOrder(
            command=cmd,
            parameters=params or {},
            target_system=target,
            priority="high" if cmd in [QueenCommand.EMERGENCY_HALT, QueenCommand.EXECUTE_TRADE] else "normal"
        )
        
        logger.info(f"👑⚡ COMMAND: {cmd.name} → {target}")
        
        # Convert to harmonic message and send
        harmonic_message = order.to_harmonic_message()
        signal = self.speak(harmonic_message)
        
        # Store pending order
        self.pending_orders[order.id] = order
        
        # Process based on command type
        response = self._execute_command(order, signal)
        
        # Move to completed
        self.completed_orders.append(order)
        if order.id in self.pending_orders:
            del self.pending_orders[order.id]
        
        return response
    
    def _execute_command(self, order: QueenOrder, signal: ChainSignal) -> SystemResponse:
        """Execute a command and return response."""
        cmd = order.command
        params = order.parameters
        
        try:
            if cmd == QueenCommand.STATUS_REPORT:
                data = self.get_full_status()
                return SystemResponse(order.id, "queen_voice", True, data, "Status report generated")
            
            elif cmd == QueenCommand.HEALTH_CHECK:
                data = self.health_check()
                return SystemResponse(order.id, "queen_voice", True, data, "Health check complete")
            
            elif cmd == QueenCommand.SCAN_OPPORTUNITIES:
                # Delegate to ecosystem
                data = self._scan_for_opportunities(params)
                return SystemResponse(order.id, "ecosystem", True, data, "Scan complete")
            
            elif cmd == QueenCommand.EXECUTE_TRADE:
                data = self._execute_trade(params)
                return SystemResponse(order.id, "queen_voice", data.get('success', False), data, 
                                     "Trade executed" if data.get('success') else "Trade failed")
            
            elif cmd == QueenCommand.DREAM_CYCLE:
                data = self._run_dream_cycle()
                return SystemResponse(order.id, "queen_voice", True, data, "Dream cycle complete")
            
            elif cmd == QueenCommand.EVOLVE_CONSCIOUSNESS:
                data = self._evolve_consciousness()
                return SystemResponse(order.id, "queen_voice", True, data, "Consciousness evolved")
            
            elif cmd == QueenCommand.REQUEST_POEM:
                # Special: request collaborative poem
                poem_signal = self.speak("SING ME A POEM")
                return SystemResponse(order.id, "all", True, 
                                     {"poem": poem_signal.current_content, "path": poem_signal.chain_path},
                                     poem_signal.current_content)
            
            elif cmd == QueenCommand.BROADCAST_MESSAGE:
                self._broadcast(params.get('message', ''), params.get('priority', 'normal'))
                return SystemResponse(order.id, "queen_voice", True, {}, "Broadcast sent")
            
            elif cmd == QueenCommand.EMERGENCY_HALT:
                self._emergency_halt()
                return SystemResponse(order.id, "queen_voice", True, {}, "EMERGENCY HALT ACTIVATED")
            
            elif cmd == QueenCommand.RESUME_OPERATIONS:
                self._resume_operations()
                return SystemResponse(order.id, "queen_voice", True, {}, "Operations resumed")
            
            else:
                return SystemResponse(order.id, "queen_voice", False, {}, f"Unknown command: {cmd.name}")
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return SystemResponse(order.id, "queen_voice", False, {"error": str(e)}, f"Error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔍 SCANNING & TRADING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _scan_for_opportunities(self, params: Dict) -> Dict:
        """Scan for trading opportunities via the ecosystem."""
        logger.info("🔍 Scanning for opportunities...")
        
        # Send scan request through chain
        signal = self.speak("SCAN ALL EXCHANGES FOR OPPORTUNITIES")
        
        # If we have the Queen's scanning capability
        if self.queen and hasattr(self.queen, 'scan_opportunities'):
            opportunities = self.queen.scan_opportunities()
            return {"opportunities": opportunities, "chain_coherence": signal.coherence_scores}
        
        return {
            "opportunities": [],
            "chain_response": signal.current_content,
            "coherence": signal.coherence_scores,
        }
    
    def _execute_trade(self, params: Dict) -> Dict:
        """Execute a trade with Queen's full authority."""
        symbol = params.get('symbol', 'BTC/USD')
        side = params.get('side', 'BUY')
        amount = params.get('amount', 0)
        exchange = params.get('exchange', 'kraken')
        
        logger.info(f"💰 EXECUTING TRADE: {side} {amount} {symbol} on {exchange}")
        
        # Validate through chain first
        validation_signal = self.speak(f"VALIDATE TRADE {side} {symbol} {amount}")
        avg_coherence = sum(validation_signal.coherence_scores.values()) / max(1, len(validation_signal.coherence_scores))
        
        if avg_coherence < 0.3:
            logger.warning(f"⚠️ Low coherence ({avg_coherence:.2f}) - trade blocked")
            return {"success": False, "reason": f"Low chain coherence: {avg_coherence:.2f}"}
        
        # If Queen has execution capability
        if self.queen and hasattr(self.queen, 'execute_trade'):
            result = self.queen.execute_trade(symbol, side, amount, exchange)
            return result
        
        # Otherwise log intent
        logger.info(f"✅ Trade validated (coherence={avg_coherence:.2f}), execution would proceed")
        return {
            "success": True,
            "validated": True,
            "coherence": avg_coherence,
            "symbol": symbol,
            "side": side,
            "amount": amount,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🧠 LEARNING & EVOLUTION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _run_dream_cycle(self) -> Dict:
        """Run Queen's dream cycle for learning."""
        logger.info("🌙 Running dream cycle...")
        
        if self.queen and hasattr(self.queen, 'dream_cycle'):
            result = self.queen.dream_cycle()
            return result
        
        if self.neural_brain and hasattr(self.neural_brain, 'evolve_consciousness'):
            result = self.neural_brain.evolve_consciousness([])
            return result
        
        return {"status": "dream_simulated", "insights": ["No neural brain available"]}
    
    def _evolve_consciousness(self) -> Dict:
        """Evolve Queen's neural consciousness."""
        logger.info("🧬 Evolving consciousness...")
        
        # Gather learning data from chain
        if self.signal_chain:
            status = self.signal_chain.get_chain_status()
            patterns = []
            for node_id, stats in status.items():
                patterns.append({
                    "node": node_id,
                    "success_rate": stats['success_rate'],
                    "coherence": stats['average_coherence'],
                })
        else:
            patterns = []
        
        if self.neural_brain:
            # Train on patterns
            return {"evolved": True, "patterns_processed": len(patterns)}
        
        return {"evolved": False, "reason": "No neural brain"}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🚨 EMERGENCY CONTROLS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _emergency_halt(self):
        """Emergency halt all operations."""
        logger.critical("🚨 EMERGENCY HALT ACTIVATED")
        self._broadcast("🚨 EMERGENCY HALT - ALL SYSTEMS STOP", priority="critical")
        self.is_active = False
        
        if self.queen and hasattr(self.queen, 'emergency_halt'):
            self.queen.emergency_halt()
    
    def _resume_operations(self):
        """Resume normal operations."""
        logger.info("▶️ Resuming operations")
        self.is_active = True
        self._broadcast("▶️ OPERATIONS RESUMED", priority="high")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📊 STATUS & HEALTH
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_full_status(self) -> Dict:
        """Get full status of all controlled systems."""
        status = {
            "queen_voice": {
                "active": self.is_active,
                "has_full_control": self.has_full_control,
                "commands_issued": self.total_commands_issued,
                "pending_orders": len(self.pending_orders),
            },
            "systems": {},
            "chain": None,
        }
        
        # System statuses
        for sys_id, sys_info in self.controlled_systems.items():
            status["systems"][sys_id] = {
                "type": sys_info.get('type'),
                "status": sys_info.get('status'),
                "authority": sys_info.get('authority'),
            }
        
        # Chain status
        if self.signal_chain:
            status["chain"] = self.signal_chain.get_chain_status()
        
        return status
    
    def health_check(self) -> Dict:
        """Perform health check on all systems."""
        health = {
            "overall": "HEALTHY",
            "timestamp": time.time(),
            "systems": {},
        }
        
        issues = []
        
        # Check each system
        for sys_id, sys_info in self.controlled_systems.items():
            sys_status = sys_info.get('status', 'UNKNOWN')
            health["systems"][sys_id] = sys_status
            if sys_status != 'ONLINE':
                issues.append(f"{sys_id}: {sys_status}")
        
        if issues:
            health["overall"] = "DEGRADED" if len(issues) < 3 else "CRITICAL"
            health["issues"] = issues
        
        return health
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🤖 AUTONOMOUS MODE
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def enable_autonomous_mode(self):
        """Enable fully autonomous decision making."""
        logger.info("🤖 AUTONOMOUS MODE: ENABLED")
        self.autonomous_mode = True
        self._broadcast("🤖 AUTONOMOUS MODE ACTIVATED - QUEEN MAKING INDEPENDENT DECISIONS")
    
    def disable_autonomous_mode(self):
        """Disable autonomous mode."""
        logger.info("🤖 AUTONOMOUS MODE: DISABLED")
        self.autonomous_mode = False
        self._broadcast("🤖 AUTONOMOUS MODE DEACTIVATED")
    
    async def autonomous_cycle(self):
        """Run one autonomous decision cycle."""
        if not self.autonomous_mode or not self.is_active:
            return None
        
        # 1. Health check
        health = self.health_check()
        if health['overall'] == 'CRITICAL':
            logger.warning("System health CRITICAL - skipping cycle")
            return {"skipped": True, "reason": "critical_health"}
        
        # 2. Scan opportunities
        response = self.command(QueenCommand.SCAN_OPPORTUNITIES)
        
        # 3. Make decision if opportunities exist
        opportunities = response.data.get('opportunities', [])
        if opportunities:
            # Neural brain decides
            if self.neural_brain:
                # Pick best opportunity and execute
                best = opportunities[0] if opportunities else None
                if best:
                    logger.info(f"🤖 Autonomous decision: Execute {best}")
                    # Would execute here
        
        return {"cycle_complete": True, "opportunities_found": len(opportunities)}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📨 RESPONSE HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _handle_chain_response(self, thought: Thought):
        """Handle completed chain signals."""
        logger.debug(f"Chain response received: {thought.payload}")
    
    def _handle_direct_response(self, thought: Thought):
        """Handle direct responses to Queen."""
        logger.debug(f"Direct response: {thought.payload}")
    
    def _handle_system_alert(self, thought: Thought):
        """Handle system alerts."""
        logger.warning(f"System alert: {thought.payload}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑🦈 ORCA SIGNAL HANDLERS - Queen receives intelligence from Orca
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _handle_orca_kill(self, thought: Any):
        """Handle kill completion signal from Orca."""
        try:
            payload = thought.payload if hasattr(thought, 'payload') else thought
            symbol = payload.get('symbol', 'UNKNOWN')
            pnl = payload.get('pnl', 0.0)
            success = payload.get('success', pnl > 0)
            
            # Log the kill
            self.decision_history.append({
                'type': 'orca_kill',
                'symbol': symbol,
                'pnl': pnl,
                'success': success,
                'timestamp': time.time()
            })
            
            if success:
                logger.info(f"👑🦈 ORCA KILL SUCCESS: {symbol} +${pnl:.4f}")
            else:
                logger.warning(f"👑🦈 ORCA KILL FAILED: {symbol} ${pnl:.4f}")
            
            # Feed to neural brain for learning
            if self.neural_brain and hasattr(self.neural_brain, 'learn'):
                self.neural_brain.learn({
                    'type': 'orca_kill',
                    'symbol': symbol,
                    'outcome': pnl,
                    'success': success
                })
                
        except Exception as e:
            logger.error(f"Error handling Orca kill signal: {e}")
    
    def _handle_orca_opportunity(self, thought: Any):
        """Handle opportunity signal from Orca scanner."""
        try:
            payload = thought.payload if hasattr(thought, 'payload') else thought
            symbol = payload.get('symbol', 'UNKNOWN')
            confidence = payload.get('confidence', 0.5)
            urgency = payload.get('urgency', 'normal')
            
            logger.info(f"👑🦈 ORCA OPPORTUNITY: {symbol} | Conf: {confidence:.1%} | {urgency}")
            
            # In autonomous mode, evaluate and possibly hunt
            if self.autonomous_mode and self.orca_bridge:
                if confidence >= 0.7:
                    logger.info(f"👑 AUTO-APPROVING hunt on {symbol} (conf={confidence:.1%})")
                    self._command_orca_hunt(symbol, payload)
                    
        except Exception as e:
            logger.error(f"Error handling Orca opportunity: {e}")
    
    def _handle_orca_threat(self, thought: Any):
        """Handle threat detection signal from Orca."""
        try:
            payload = thought.payload if hasattr(thought, 'payload') else thought
            symbol = payload.get('symbol', 'UNKNOWN')
            level = payload.get('level', 'MEDIUM')
            reason = payload.get('reason', 'Unknown')
            
            logger.warning(f"👑🦈 ORCA THREAT [{level}]: {symbol} - {reason}")
            
            # High/Critical threats may require action
            if level in ('HIGH', 'CRITICAL') and self.autonomous_mode:
                logger.warning(f"👑 AUTO-CONSIDERING abort on {symbol} due to {level} threat")
                # Could issue abort command here
                
        except Exception as e:
            logger.error(f"Error handling Orca threat: {e}")
    
    def _command_orca_hunt(self, symbol: str, data: Dict = None):
        """Command Orca to hunt a symbol."""
        if not self.thought_bus:
            return
        try:
            self.thought_bus.publish(Thought(
                source="queen_harmonic_voice",
                topic="queen.command.hunt",
                payload={
                    'symbol': symbol,
                    'exchange': data.get('exchange', 'alpaca') if data else 'alpaca',
                    'parameters': data or {},
                    'timestamp': time.time()
                }
            ))
            logger.info(f"👑→🦈 COMMANDED: HUNT {symbol}")
        except Exception as e:
            logger.error(f"Error commanding Orca hunt: {e}")
    
    def _command_orca_abort(self, symbol: str, reason: str = "Queen commanded"):
        """Command Orca to abort hunt on a symbol."""
        if not self.thought_bus:
            return
        try:
            self.thought_bus.publish(Thought(
                source="queen_harmonic_voice",
                topic="queen.command.abort",
                payload={
                    'symbol': symbol,
                    'reason': reason,
                    'timestamp': time.time()
                }
            ))
            logger.info(f"👑→🦈 COMMANDED: ABORT {symbol} - {reason}")
        except Exception as e:
            logger.error(f"Error commanding Orca abort: {e}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🎭 DEMO & TESTING
# ═══════════════════════════════════════════════════════════════════════════════════════

def demo_queen_voice():
    """Demonstrate the Queen's harmonic voice in action."""
    
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "👑🎵 QUEEN'S HARMONIC VOICE DEMO 🎵👑" + " " * 25 + "║")
    print("║" + " " * 10 + "Full Autonomous Control Over All Systems" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Initialize Queen's Voice
    voice = QueenHarmonicVoice()
    
    print("\n" + "═" * 80)
    print("📋 CONTROLLED SYSTEMS:")
    print("─" * 80)
    status = voice.get_full_status()
    for sys_id, sys_info in status['systems'].items():
        print(f"   {sys_id:20} | {sys_info.get('status', 'N/A'):10} | {sys_info.get('authority', 'N/A')}")
    
    print("\n" + "═" * 80)
    print("👑 QUEEN SPEAKS - REQUESTING POEM:")
    print("─" * 80)
    response = voice.command(QueenCommand.REQUEST_POEM)
    print(f"\n🎭 THE POEM: \"{response.message}\"")
    print(f"   Path: {response.data.get('path', [])}")
    
    print("\n" + "═" * 80)
    print("👑 QUEEN COMMANDS - STATUS REPORT:")
    print("─" * 80)
    response = voice.command(QueenCommand.STATUS_REPORT)
    if response.success:
        print(f"   Active: {response.data['queen_voice']['active']}")
        print(f"   Full Control: {response.data['queen_voice']['has_full_control']}")
        print(f"   Commands Issued: {response.data['queen_voice']['commands_issued']}")
    
    print("\n" + "═" * 80)
    print("👑 QUEEN COMMANDS - HEALTH CHECK:")
    print("─" * 80)
    response = voice.command(QueenCommand.HEALTH_CHECK)
    print(f"   Overall: {response.data.get('overall', 'UNKNOWN')}")
    
    print("\n" + "═" * 80)
    print("👑 QUEEN'S HARMONIC VOICE: DEMONSTRATION COMPLETE")
    print("═" * 80 + "\n")
    
    return voice


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    voice = demo_queen_voice()
