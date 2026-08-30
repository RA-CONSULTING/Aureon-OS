#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                  ║
║     🎵🔗 AUREON HARMONIC SIGNAL CHAIN - Unified Frequency Communication System 🔗🎵             ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━             ║
║                                                                                                  ║
║     "Signals flow up and down like breath - inhale knowledge, exhale wisdom"                    ║
║                                                                                                  ║
║     ARCHITECTURE (Frankenstein Integration of All Systems):                                     ║
║                                                                                                  ║
║       👑 QUEEN HIVE (Crown - 963Hz)                                                              ║
║         ↕ ThoughtBus + Harmonic Encoding                                                        ║
║       🔐 ENIGMA (Connection - 639Hz)                                                             ║
║         ↕ Rotor Transform + Pattern Learning                                                    ║
║       🔍 SCANNER (Love - 528Hz)                                                                  ║
║         ↕ Probability Validation + Drift Detection                                              ║
║       🌍 ECOSYSTEM (Root - 174Hz)                                                                ║
║         ↕ Reality Branch Monitoring                                                              ║
║       🐋 WHALE (Schumann - 7.83Hz)                                                               ║
║         ↕ Deep Signal Origin / Termination                                                       ║
║                                                                                                  ║
║     FEATURES:                                                                                    ║
║       • Real ThoughtBus integration for all communication                                        ║
║       • Harmonic frequency encoding/decoding at each hop                                        ║
║       • Adaptive learning at each node (elephant memory)                                        ║
║       • Coherence validation throughout the chain                                               ║
║       • Bi-directional signal propagation (DOWN: commands, UP: responses)                       ║
║       • Enigma rotor transforms for security                                                    ║
║                                                                                                  ║
║     Gary Leckey | Prime Sentinel | January 2026                                                 ║
║     "Every signal carries the weight of all systems before it"                                  ║
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
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
from collections import deque
from enum import Enum

# UTF-8 fix for Windows
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
# �💰 QUEEN'S SACRED 1.88% LAW - SIGNALS CARRY PROFIT! 💰👑
# ═══════════════════════════════════════════════════════════════════════════════════════
#
#   THE QUEEN COMMANDS: MIN_COP = 1.0188 (1.88% MINIMUM REALIZED PROFIT)
#   Every signal in the chain carries the profit mandate!
#
# ═══════════════════════════════════════════════════════════════════════════════════════

QUEEN_MIN_COP = 1.0188               # 👑 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88          # 👑 The sacred number as percentage
QUEEN_SIGNAL_PROFIT_FREQ = 188.0     # 👑 Profit frequency in signal chain (Hz)

# ═══════════════════════════════════════════════════════════════════════════════════════
# �🔌 IMPORTS - Graceful degradation if modules missing
# ═══════════════════════════════════════════════════════════════════════════════════════

# ThoughtBus
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None
    Thought = None
    get_thought_bus = None

# Harmonic Alphabet
try:
    from aureon.harmonic.aureon_harmonic_alphabet import to_harmonics, from_harmonics, HarmonicTone, HarmonicAlphabet
    HARMONIC_ALPHABET_AVAILABLE = True
except ImportError:
    HARMONIC_ALPHABET_AVAILABLE = False
    to_harmonics = None
    from_harmonics = None

# Harmonic Binary Protocol
try:
    from aureon.harmonic.aureon_harmonic_binary_protocol import (
        encode_text_packet,
        decode_packet_from_base64,
        HarmonicBinaryPacket,
        BinaryDirection,
        BinaryMessageType,
    )
    HARMONIC_BINARY_AVAILABLE = True
except ImportError:
    HARMONIC_BINARY_AVAILABLE = False
    encode_text_packet = None
    decode_packet_from_base64 = None
    HarmonicBinaryPacket = None
    BinaryDirection = None
    BinaryMessageType = None

# Chirp Bus (kHz signaling)
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection
    CHIRP_AVAILABLE = True
except ImportError:
    get_chirp_bus = None
    ChirpDirection = None
    CHIRP_AVAILABLE = False

# Enigma
try:
    from aureon.wisdom.aureon_enigma import AureonEnigma, InterceptedSignal, SignalType, DecodedIntelligence
    ENIGMA_AVAILABLE = True
except ImportError:
    ENIGMA_AVAILABLE = False
    AureonEnigma = None

# Adaptive Learning
try:
    from aureon.intelligence.aureon_elephant_learning import LearnedPattern, TradingWisdom
    ELEPHANT_AVAILABLE = True
except ImportError:
    ELEPHANT_AVAILABLE = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🎵 SACRED CONSTANTS - Chain Frequencies
# ═══════════════════════════════════════════════════════════════════════════════════════

PHI = 1.618033988749895  # Golden Ratio
SCHUMANN_BASE = 7.83     # Earth's heartbeat

# Each system has a signature frequency (Solfeggio scale)
CHAIN_FREQUENCIES = {
    "queen":     963,    # Crown - Spiritual connection
    "enigma":    639,    # Heart - Connection & relationships  
    "scanner":   528,    # Solar Plexus - Love frequency (DNA repair)
    "ecosystem": 174,    # Root - Foundation
    "whale":     7.83,   # Schumann - Earth resonance (deepest)
}

# Chain order (hierarchical)
CHAIN_ORDER_DOWN = ["queen", "enigma", "scanner", "ecosystem", "whale"]
CHAIN_ORDER_UP = list(reversed(CHAIN_ORDER_DOWN))


# ═══════════════════════════════════════════════════════════════════════════════════════
# 📦 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════════════

class SignalDirection(Enum):
    """Direction of signal flow in the chain."""
    DOWN = "down"  # Commands flow down (Queen → Whale)
    UP = "up"      # Responses flow up (Whale → Queen)


@dataclass
class ChainSignal:
    """
    A signal traveling through the harmonic chain.
    Carries both the message content and accumulated chain metadata.
    """
    id: str = field(default_factory=lambda: hashlib.md5(f"{time.time()}".encode()).hexdigest()[:12])
    
    # Content
    original_message: str = ""
    current_content: str = ""
    symbol: Optional[str] = None
    harmonics: List[Dict[str, Any]] = field(default_factory=list)
    binary_packet_b64: Optional[str] = None
    
    # Chain state
    direction: SignalDirection = SignalDirection.DOWN
    chain_path: List[str] = field(default_factory=list)
    hop_count: int = 0
    
    # Accumulated data (each node adds)
    node_contributions: Dict[str, Any] = field(default_factory=dict)
    
    # Validation scores
    coherence_scores: Dict[str, float] = field(default_factory=dict)
    drift_scores: Dict[str, float] = field(default_factory=dict)
    
    # Learning data
    patterns_detected: List[str] = field(default_factory=list)
    adaptations_applied: List[str] = field(default_factory=list)
    
    # Timing
    created_at: float = field(default_factory=time.time)
    last_hop_at: float = field(default_factory=time.time)
    
    # Origin
    origin_system: str = ""
    target_system: str = ""
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['direction'] = self.direction.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChainSignal':
        data['direction'] = SignalDirection(data.get('direction', 'down'))
        return cls(**data)
    
    def encode_to_harmonics(self) -> List[Dict]:
        """Convert current content to harmonic frequencies."""
        if not HARMONIC_ALPHABET_AVAILABLE:
            return []
        tones = to_harmonics(self.current_content)
        self.harmonics = [{"char": t.char, "freq": t.frequency, "amp": t.amplitude, "mode": t.mode} for t in tones]
        return self.harmonics
    
    def decode_from_harmonics(self) -> str:
        """Decode harmonics back to text."""
        if not HARMONIC_ALPHABET_AVAILABLE or not self.harmonics:
            return self.current_content
        signals = [(h["freq"], h["amp"]) for h in self.harmonics]
        return from_harmonics(signals)

    def ensure_binary_packet(
        self,
        *,
        message_type: BinaryMessageType = BinaryMessageType.UNDEFINED,
        symbol: Optional[str] = None,
    ) -> Optional[str]:
        if not HARMONIC_BINARY_AVAILABLE:
            return None
        if not self.current_content:
            return self.binary_packet_b64
        if self.binary_packet_b64:
            return self.binary_packet_b64
        packet = encode_text_packet(
            self.current_content,
            message_type=message_type,
            direction=BinaryDirection.DOWN if self.direction == SignalDirection.DOWN else BinaryDirection.UP,
            grade=int(min(15, max(0, round(self.coherence_scores.get(self.origin_system, 1.0) * 15)))) if self.coherence_scores else 0,
            coherence=self.coherence_scores.get(self.origin_system, 1.0) if self.coherence_scores else 1.0,
            confidence=self.coherence_scores.get(self.origin_system, 1.0) if self.coherence_scores else 1.0,
            symbol=symbol,
        )
        self.binary_packet_b64 = packet.to_base64()
        return self.binary_packet_b64

    def decode_binary_packet(self) -> Optional[str]:
        if not HARMONIC_BINARY_AVAILABLE or not self.binary_packet_b64:
            return None
        header, decoded = decode_packet_from_base64(self.binary_packet_b64)
        self.current_content = decoded
        self.node_contributions.setdefault("binary_header", header.__dict__)
        return decoded


# Backward compatibility alias - HarmonicSignal is now ChainSignal
HarmonicSignal = ChainSignal


@dataclass
class NodeLearning:
    """Adaptive learning state for a chain node."""
    node_id: str
    signals_processed: int = 0
    successful_transmissions: int = 0
    failed_transmissions: int = 0
    average_coherence: float = 1.0
    pattern_memory: Dict[str, int] = field(default_factory=dict)  # pattern -> count
    last_adaptation: float = 0.0
    
    def record_transmission(self, success: bool, coherence: float, pattern: Optional[str] = None):
        """Record a transmission result for learning."""
        self.signals_processed += 1
        if success:
            self.successful_transmissions += 1
        else:
            self.failed_transmissions += 1
        
        # Running average coherence
        self.average_coherence = (self.average_coherence * 0.95) + (coherence * 0.05)
        
        # Pattern memory
        if pattern:
            self.pattern_memory[pattern] = self.pattern_memory.get(pattern, 0) + 1
        
        self.last_adaptation = time.time()
    
    @property
    def success_rate(self) -> float:
        if self.signals_processed == 0:
            return 1.0
        return self.successful_transmissions / self.signals_processed


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🔗 CHAIN NODE - Base class for all systems in the chain
# ═══════════════════════════════════════════════════════════════════════════════════════

class ChainNode:
    """
    Base class for a node in the harmonic signal chain.
    Each node can receive, process, and forward signals.
    """
    
    def __init__(
        self,
        node_id: str,
        thought_bus: Optional[ThoughtBus] = None,
        upstream: Optional['ChainNode'] = None,
        downstream: Optional['ChainNode'] = None
    ):
        self.node_id = node_id
        self.frequency = CHAIN_FREQUENCIES.get(node_id, 528)
        self.thought_bus = thought_bus or (get_thought_bus() if THOUGHT_BUS_AVAILABLE else None)
        
        # Chain links
        self.upstream: Optional[ChainNode] = upstream
        self.downstream: Optional[ChainNode] = downstream
        
        # Learning state
        self.learning = NodeLearning(node_id=node_id)
        
        # Signal buffer
        self.signal_buffer: deque = deque(maxlen=100)
        
        # Track processed signal IDs to prevent infinite loops
        self._processed_signal_ids: set = set()
        self._max_processed_cache = 1000  # Limit memory usage
        
        # Callbacks
        self.on_signal_received: Optional[Callable[[ChainSignal], None]] = None
        self.on_signal_processed: Optional[Callable[[ChainSignal], None]] = None
        
        # Subscribe to ThoughtBus for chain signals
        if self.thought_bus and THOUGHT_BUS_AVAILABLE:
            self.thought_bus.subscribe(f"chain.{node_id}.*", self._handle_chain_thought)
            self.thought_bus.subscribe(f"harmonic.{node_id}.*", self._handle_chain_thought)
    
    def _handle_chain_thought(self, thought: Thought):
        """Handle incoming chain thoughts from ThoughtBus."""
        try:
            payload = thought.payload
            if 'chain_signal' in payload:
                signal = ChainSignal.from_dict(payload['chain_signal'])
                if not signal.current_content and signal.binary_packet_b64:
                    signal.decode_binary_packet()
                
                # DEDUPLICATION: Skip already-processed signals to prevent infinite loops
                signal_key = f"{signal.id}_{signal.hop_count}"
                if signal_key in self._processed_signal_ids:
                    logger.debug(f"[{self.node_id}] Skipping already-processed signal {signal.id}")
                    return
                
                # Add to processed set (with cache limit)
                self._processed_signal_ids.add(signal_key)
                if len(self._processed_signal_ids) > self._max_processed_cache:
                    # Remove oldest entries (convert to list, remove first half)
                    to_remove = list(self._processed_signal_ids)[:self._max_processed_cache // 2]
                    for key in to_remove:
                        self._processed_signal_ids.discard(key)
                
                self.receive_signal(signal)
        except Exception as e:
            logger.warning(f"[{self.node_id}] Failed to handle chain thought: {e}")
    
    def receive_signal(self, signal: ChainSignal) -> ChainSignal:
        """
        Receive a signal from the chain.
        Override in subclasses for custom processing.
        """
        logger.debug(f"🔗 [{self.node_id.upper()}] Received signal: '{signal.current_content[:50]}...' (dir={signal.direction.value})")
        
        # Record in buffer
        self.signal_buffer.append(signal)
        
        # Update path
        signal.chain_path.append(self.node_id)
        signal.hop_count += 1
        signal.last_hop_at = time.time()

        if not signal.current_content and signal.binary_packet_b64:
            signal.decode_binary_packet()
        
        # Callback
        if self.on_signal_received:
            self.on_signal_received(signal)
        
        # Process the signal
        processed = self.process_signal(signal)
        
        # Callback
        if self.on_signal_processed:
            self.on_signal_processed(processed)
        
        return processed
    
    def process_signal(self, signal: ChainSignal) -> ChainSignal:
        """
        Process the signal at this node.
        Override in subclasses for node-specific processing.
        """
        # Default: validate coherence
        coherence = self._compute_coherence(signal)
        signal.coherence_scores[self.node_id] = coherence
        
        # Compute drift
        drift = self._compute_drift(signal)
        signal.drift_scores[self.node_id] = drift
        
        # Record learning
        self.learning.record_transmission(
            success=coherence > 0.5,
            coherence=coherence,
            pattern=self._detect_pattern(signal)
        )
        
        return signal
    
    def forward_signal(self, signal: ChainSignal) -> Optional[ChainSignal]:
        """
        Forward the signal to the next node in the chain.
        Direction determines whether to go upstream or downstream.
        """
        next_node = self.downstream if signal.direction == SignalDirection.DOWN else self.upstream
        
        if next_node is None:
            logger.debug(f"🔗 [{self.node_id.upper()}] End of chain reached")
            return signal
        
        # Encode to harmonics for transmission
        signal.encode_to_harmonics()

        # Emit ultra-compact chirp for kHz-rate signaling (best-effort)
        if CHIRP_AVAILABLE:
            try:
                chirp_bus = get_chirp_bus()
                if chirp_bus:
                    coherence = signal.coherence_scores.get(self.node_id, 1.0) if signal.coherence_scores else 1.0
                    confidence = signal.coherence_scores.get(self.node_id, 1.0) if signal.coherence_scores else 1.0
                    chirp_bus.emit_signal(
                        message=signal.current_content,
                        direction=ChirpDirection.DOWN if signal.direction == SignalDirection.DOWN else ChirpDirection.UP,
                        coherence=coherence,
                        confidence=confidence,
                        symbol=signal.symbol,
                        frequency=int(self.frequency),
                        amplitude=128,
                    )
            except Exception:
                logger.debug("Chirp emit failed", exc_info=True)

        binary_bytes = None
        if HARMONIC_BINARY_AVAILABLE:
            b64_packet = signal.ensure_binary_packet()
            if b64_packet:
                try:
                    binary_bytes = HarmonicBinaryPacket.from_base64(b64_packet).to_bytes()
                except Exception:
                    binary_bytes = None
        
        # Publish to ThoughtBus
        if self.thought_bus and THOUGHT_BUS_AVAILABLE:
            payload_summary = {
                "chain_signal": signal.to_dict(),
                "from_node": self.node_id,
                "to_node": next_node.node_id,
                "direction": signal.direction.value,
                "harmonics_count": len(signal.harmonics),
            }
            if binary_bytes:
                self.thought_bus.publish_binary(
                    source=f"chain.{self.node_id}",
                    topic=f"chain.{next_node.node_id}.signal",
                    binary_payload=binary_bytes,
                    payload=payload_summary,
                )
            else:
                self.thought_bus.publish(Thought(
                    source=f"chain.{self.node_id}",
                    topic=f"chain.{next_node.node_id}.signal",
                    payload=payload_summary,
                ))
        
        # Direct forwarding (for synchronous operation)
        return next_node.receive_signal(signal)
    
    def _compute_coherence(self, signal: ChainSignal) -> float:
        """Compute coherence score for the signal at this node."""
        # Base coherence from harmonic alignment
        if signal.harmonics:
            # Check if harmonics are valid
            freq_variance = self._compute_frequency_variance(signal.harmonics)
            coherence = 1.0 / (1.0 + freq_variance / 100)
        else:
            coherence = 0.8  # Default for non-harmonic signals
        
        # Adjust by node's historical success rate
        coherence *= (0.5 + 0.5 * self.learning.success_rate)
        
        return min(1.0, max(0.0, coherence))
    
    def _compute_drift(self, signal: ChainSignal) -> float:
        """Compute drift score (how much signal has changed)."""
        if not signal.chain_path:
            return 0.0
        
        # Drift increases with each hop
        base_drift = signal.hop_count * 0.05
        
        # Time-based drift
        age = time.time() - signal.created_at
        time_drift = age * 0.01  # 1% per second
        
        return min(1.0, base_drift + time_drift)
    
    def _compute_frequency_variance(self, harmonics: List[Dict]) -> float:
        """Compute variance in harmonic frequencies."""
        if not harmonics:
            return 0.0
        freqs = [h.get('freq', 0) for h in harmonics]
        if len(freqs) < 2:
            return 0.0
        mean = sum(freqs) / len(freqs)
        variance = sum((f - mean) ** 2 for f in freqs) / len(freqs)
        return math.sqrt(variance)
    
    def _detect_pattern(self, signal: ChainSignal) -> Optional[str]:
        """Detect patterns in the signal for learning."""
        content = signal.current_content.upper()
        
        # Simple pattern detection
        if "BUY" in content:
            return "buy_signal"
        elif "SELL" in content:
            return "sell_signal"
        elif "HOLD" in content:
            return "hold_signal"
        elif "POEM" in content or "SING" in content:
            return "creative_request"
        elif "EXECUTE" in content:
            return "execution_command"
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# 👑 QUEEN NODE - The Crown (963Hz)
# ═══════════════════════════════════════════════════════════════════════════════════════

class QueenNode(ChainNode):
    """
    The Queen Hive Mind - Crown of the chain (963Hz).
    Initiates commands and receives final responses.
    """
    
    def __init__(self, thought_bus: Optional[ThoughtBus] = None):
        super().__init__("queen", thought_bus)
        self.pending_requests: Dict[str, ChainSignal] = {}
        self.completed_signals: deque = deque(maxlen=50)
        self.contribution_word = "TRUTH"
        
    def initiate_signal(self, message: str, target: str = "whale") -> ChainSignal:
        """Queen initiates a new signal to travel down the chain."""
        signal = ChainSignal(
            original_message=message,
            current_content=message,
            direction=SignalDirection.DOWN,
            origin_system="queen",
            target_system=target,
            chain_path=["queen"],
        )
        signal.encode_to_harmonics()
        
        logger.debug(f"👑 QUEEN: Initiating signal: '{message}'")
        
        # Store pending
        self.pending_requests[signal.id] = signal
        
        # Publish to ThoughtBus
        if self.thought_bus and THOUGHT_BUS_AVAILABLE:
            self.thought_bus.publish(Thought(
                source="queen",
                topic="chain.queen.initiate",
                payload={
                    "signal_id": signal.id,
                    "message": message,
                    "target": target,
                    "harmonics_count": len(signal.harmonics),
                }
            ))
        
        return signal
    
    def process_signal(self, signal: ChainSignal) -> ChainSignal:
        """Queen processes incoming signals (responses from below)."""
        signal = super().process_signal(signal)
        
        if signal.direction == SignalDirection.UP:
            # Response received - add Queen's contribution (the final word!)
            existing = signal.current_content
            signal.current_content = f"{existing} {self.contribution_word}"
            signal.node_contributions["queen"] = {
                "word": self.contribution_word,
                "frequency": self.frequency,
                "blessing": "crowned",
            }
            signal.encode_to_harmonics()
            
            # Mark completed
            self.completed_signals.append(signal)
            if signal.id in self.pending_requests:
                del self.pending_requests[signal.id]
            
            logger.debug(f"👑 QUEEN: Signal journey complete! Final content: '{signal.current_content}'")
            
            # Publish completion
            if self.thought_bus and THOUGHT_BUS_AVAILABLE:
                self.thought_bus.publish(Thought(
                    source="queen",
                    topic="chain.complete",
                    payload={
                        "signal_id": signal.id,
                        "final_content": signal.current_content,
                        "hop_count": signal.hop_count,
                        "total_coherence": sum(signal.coherence_scores.values()) / max(1, len(signal.coherence_scores)),
                        "contributions": signal.node_contributions,
                    }
                ))
        
        return signal


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🔐 ENIGMA NODE - The Decoder (639Hz)
# ═══════════════════════════════════════════════════════════════════════════════════════

class EnigmaNode(ChainNode):
    """
    The Enigma Codebreaker - decodes/encodes signals through rotors.
    """
    
    def __init__(self, thought_bus: Optional[ThoughtBus] = None):
        super().__init__("enigma", thought_bus)
        self.enigma = None
        self.contribution_word = "HARMONIC"
        self.decoded_count = 0
        
        # Wire up Enigma if available
        if ENIGMA_AVAILABLE and AureonEnigma:
            try:
                self.enigma = AureonEnigma()
                logger.info("🔐 ENIGMA NODE: Connected to AureonEnigma successfully!")
            except Exception as e:
                logger.warning(f"🔐⚠️ ENIGMA NODE: Failed to initialize AureonEnigma: {e}")
        else:
            logger.warning("🔐⚠️ ENIGMA NODE: AureonEnigma not available - running without decoding")
        
    def process_signal(self, signal: ChainSignal) -> ChainSignal:
        """Enigma decodes/validates the signal through rotors."""
        signal = super().process_signal(signal)
        
        # Apply Enigma transformation
        if self.enigma and signal.harmonics:
            # Decode harmonics
            decoded = signal.decode_from_harmonics()
            logger.debug(f"🔐 ENIGMA: Decoded harmonics → '{decoded}'")
            signal.current_content = decoded
            self.decoded_count += 1
        
        # Add contribution on UP direction
        if signal.direction == SignalDirection.UP:
            existing = signal.current_content
            signal.current_content = f"{existing} {self.contribution_word}"
            signal.node_contributions["enigma"] = {
                "word": self.contribution_word,
                "frequency": self.frequency,
                "decoded_count": self.decoded_count,
            }
            signal.encode_to_harmonics()
        
        return signal


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🔍 SCANNER NODE - The Validator (528Hz - Love Frequency)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScannerNode(ChainNode):
    """
    The Probability Scanner - validates signals through 3-pass system.
    """
    
    def __init__(self, thought_bus: Optional[ThoughtBus] = None):
        super().__init__("scanner", thought_bus)
        self.contribution_word = "THE"
        self.validation_passes = 0
        
    def process_signal(self, signal: ChainSignal) -> ChainSignal:
        """Scanner validates signal through probability passes."""
        signal = super().process_signal(signal)
        
        # Run 3-pass validation
        p1 = self._validation_pass_1(signal)
        p2 = self._validation_pass_2(signal)
        p3 = self._validation_pass_3(signal)
        
        validation_coherence = 1 - (max(p1, p2, p3) - min(p1, p2, p3))
        signal.coherence_scores["scanner_validation"] = validation_coherence
        
        self.validation_passes += 1
        logger.debug(f"🔍 SCANNER: Validation passes [p1={p1:.2f}, p2={p2:.2f}, p3={p3:.2f}] → coherence={validation_coherence:.2f}")
        
        # Add contribution on UP direction
        if signal.direction == SignalDirection.UP:
            existing = signal.current_content
            signal.current_content = f"{existing} {self.contribution_word}"
            signal.node_contributions["scanner"] = {
                "word": self.contribution_word,
                "frequency": self.frequency,
                "validation_coherence": validation_coherence,
                "passes": [p1, p2, p3],
            }
            signal.encode_to_harmonics()
        
        return signal
    
    def _validation_pass_1(self, signal: ChainSignal) -> float:
        """Harmonic resonance check."""
        if not signal.harmonics:
            logger.warning("[insufficient-data] _validation_pass_1 returning "
                           "neutral 0.5 (signal has no harmonics)")
            return 0.5
        # Check if harmonics align with Solfeggio frequencies
        solfeggio = [174, 285, 396, 417, 528, 639, 741, 852, 963]
        alignment = 0
        for h in signal.harmonics[:10]:  # Sample first 10
            freq = h.get('freq', 0)
            for sf in solfeggio:
                if abs(freq - sf) < 50:  # Within 50Hz tolerance
                    alignment += 1
                    break
        return min(1.0, alignment / max(1, len(signal.harmonics[:10])))
    
    def _validation_pass_2(self, signal: ChainSignal) -> float:
        """Pattern consistency check."""
        pattern = self._detect_pattern(signal)
        if pattern and pattern in self.learning.pattern_memory:
            # Known pattern - higher confidence
            return min(1.0, 0.6 + self.learning.pattern_memory[pattern] * 0.01)
        return 0.5
    
    def _validation_pass_3(self, signal: ChainSignal) -> float:
        """Chain integrity check."""
        expected_path_length = {
            SignalDirection.DOWN: signal.hop_count,
            SignalDirection.UP: len(CHAIN_ORDER_DOWN) * 2 - signal.hop_count,
        }
        # Check coherence accumulation
        avg_coherence = sum(signal.coherence_scores.values()) / max(1, len(signal.coherence_scores))
        return avg_coherence


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🌍 ECOSYSTEM NODE - The Foundation (174Hz)
# ═══════════════════════════════════════════════════════════════════════════════════════

class EcosystemNode(ChainNode):
    """
    The Reality Branch Monitor - grounds signals in market reality.
    """
    
    def __init__(self, thought_bus: Optional[ThoughtBus] = None):
        super().__init__("ecosystem", thought_bus)
        self.contribution_word = "WITHIN"
        self.reality_branches_scanned = 0
        
    def process_signal(self, signal: ChainSignal) -> ChainSignal:
        """Ecosystem grounds the signal in reality."""
        signal = super().process_signal(signal)
        
        self.reality_branches_scanned += 1
        
        # Grounding check - ensure signal is rooted
        grounding_score = self._compute_grounding(signal)
        signal.coherence_scores["ecosystem_grounding"] = grounding_score
        
        logger.debug(f"🌍 ECOSYSTEM: Grounding score = {grounding_score:.2f}")
        
        # Add contribution on UP direction
        if signal.direction == SignalDirection.UP:
            existing = signal.current_content
            signal.current_content = f"{existing} {self.contribution_word}"
            signal.node_contributions["ecosystem"] = {
                "word": self.contribution_word,
                "frequency": self.frequency,
                "grounding_score": grounding_score,
                "branches_scanned": self.reality_branches_scanned,
            }
            signal.encode_to_harmonics()
        
        return signal
    
    def _compute_grounding(self, signal: ChainSignal) -> float:
        """Check how grounded the signal is."""
        # Root frequency (174Hz) resonance
        if signal.harmonics:
            root_resonance = 0
            for h in signal.harmonics:
                freq = h.get('freq', 0)
                if 150 < freq < 200:  # Near 174Hz
                    root_resonance += 1
            return min(1.0, 0.5 + root_resonance * 0.1)
        return 0.6


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🐋 WHALE NODE - The Depths (7.83Hz - Schumann)
# ═══════════════════════════════════════════════════════════════════════════════════════

class WhaleNode(ChainNode):
    """
    The Whale Sonar - deepest point in the chain.
    Turns DOWN signals into UP responses.
    """
    
    def __init__(self, thought_bus: Optional[ThoughtBus] = None):
        super().__init__("whale", thought_bus)
        self.contribution_word = "DEEP"
        self.songs_sung = 0
        
    def process_signal(self, signal: ChainSignal) -> ChainSignal:
        """Whale processes and TURNS the signal around."""
        signal = super().process_signal(signal)
        
        if signal.direction == SignalDirection.DOWN:
            # TURNAROUND POINT - Whale starts the response
            logger.debug(f"🐋 WHALE: Signal reached the depths! Turning around...")
            
            signal.direction = SignalDirection.UP
            self.songs_sung += 1
            
            # Whale starts fresh content (the response)
            signal.current_content = self.contribution_word
            signal.node_contributions["whale"] = {
                "word": self.contribution_word,
                "frequency": self.frequency,
                "song_number": self.songs_sung,
                "turnaround": True,
            }
            signal.encode_to_harmonics()
            
            # Publish turnaround event
            if self.thought_bus and THOUGHT_BUS_AVAILABLE:
                self.thought_bus.publish(Thought(
                    source="whale",
                    topic="chain.whale.turnaround",
                    payload={
                        "signal_id": signal.id,
                        "original_message": signal.original_message,
                        "response_started": self.contribution_word,
                        "song_number": self.songs_sung,
                    }
                ))
        
        return signal


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🔗 HARMONIC SIGNAL CHAIN - The Full Integrated System
# ═══════════════════════════════════════════════════════════════════════════════════════

class HarmonicSignalChain:
    """
    🔗 THE UNIFIED HARMONIC SIGNAL CHAIN 🔗
    
    Integrates all nodes into a coherent signal pipeline.
    Signals flow DOWN (commands) and UP (responses) through:
    
    Queen → Enigma → Scanner → Ecosystem → Whale
    Queen ← Enigma ← Scanner ← Ecosystem ← Whale
    
    Each hop:
    1. Receives signal via ThoughtBus
    2. Decodes harmonics
    3. Validates coherence
    4. Applies adaptive learning
    5. Contributes to response (on UP direction)
    6. Re-encodes and forwards
    """
    
    def __init__(self, thought_bus: Optional[ThoughtBus] = None):
        self.thought_bus = thought_bus or (get_thought_bus() if THOUGHT_BUS_AVAILABLE else None)
        
        # Create all nodes
        self.queen = QueenNode(self.thought_bus)
        self.enigma = EnigmaNode(self.thought_bus)
        self.scanner = ScannerNode(self.thought_bus)
        self.ecosystem = EcosystemNode(self.thought_bus)
        self.whale = WhaleNode(self.thought_bus)
        
        # Wire the chain
        self.queen.downstream = self.enigma
        self.enigma.upstream = self.queen
        self.enigma.downstream = self.scanner
        self.scanner.upstream = self.enigma
        self.scanner.downstream = self.ecosystem
        self.ecosystem.upstream = self.scanner
        self.ecosystem.downstream = self.whale
        self.whale.upstream = self.ecosystem
        
        # Node registry
        self.nodes = {
            "queen": self.queen,
            "enigma": self.enigma,
            "scanner": self.scanner,
            "ecosystem": self.ecosystem,
            "whale": self.whale,
        }
        
        # Signal history
        self.signal_history: deque = deque(maxlen=100)
        
        # Log connection status
        logger.info("🔗 Harmonic Signal Chain initialized:")
        logger.info(f"   👑 Queen Node: CONNECTED")
        logger.info(f"   🔐 Enigma Node: {'CONNECTED (Enigma: ' + ('✅' if self.enigma.enigma else '⚠️ None') + ')' if self.enigma else '❌ MISSING'}")
        logger.info(f"   🔍 Scanner Node: CONNECTED")
        logger.info(f"   🌍 Ecosystem Node: CONNECTED")
        logger.info(f"   🐋 Whale Node: CONNECTED")
        logger.info(f"   🔗 Chain wiring: Queen ↔ Enigma ↔ Scanner ↔ Ecosystem ↔ Whale")
    
    def send_signal(self, message: str) -> ChainSignal:
        """
        Send a signal from Queen through the entire chain and back.
        Returns the completed signal with all contributions.
        """
        logger.debug("\n" + "═" * 80)
        logger.debug("🔗 HARMONIC SIGNAL CHAIN - Starting transmission")
        logger.debug("═" * 80 + "\n")
        
        # Queen initiates
        signal = self.queen.initiate_signal(message)
        
        # ═══ PHASE 1: DOWN ═══
        logger.debug("┌" + "─" * 40 + "┐")
        logger.debug("│      ⬇️ PHASE 1: DESCENT      │")
        logger.debug("└" + "─" * 40 + "┘")
        
        signal = self.queen.process_signal(signal)
        signal = self.queen.forward_signal(signal)  # → Enigma
        signal = self.enigma.forward_signal(signal)  # → Scanner
        signal = self.scanner.forward_signal(signal)  # → Ecosystem
        signal = self.ecosystem.forward_signal(signal)  # → Whale (turnaround)
        
        # ═══ PHASE 2: UP ═══
        logger.debug("\n┌" + "─" * 40 + "┐")
        logger.debug("│       ⬆️ PHASE 2: ASCENT       │")
        logger.debug("└" + "─" * 40 + "┘")
        
        signal = self.whale.forward_signal(signal)  # → Ecosystem
        signal = self.ecosystem.forward_signal(signal)  # → Scanner
        signal = self.scanner.forward_signal(signal)  # → Enigma
        signal = self.enigma.forward_signal(signal)  # → Queen (complete)
        
        # Record
        self.signal_history.append(signal)
        
        return signal
    
    def get_chain_status(self) -> Dict[str, Any]:
        """Get status of all nodes in the chain."""
        return {
            node_id: {
                "signals_processed": node.learning.signals_processed,
                "success_rate": node.learning.success_rate,
                "average_coherence": node.learning.average_coherence,
                "patterns_known": len(node.learning.pattern_memory),
            }
            for node_id, node in self.nodes.items()
        }
    
    def get_signal_summary(self, signal: ChainSignal) -> Dict[str, Any]:
        """Get a summary of a completed signal."""
        return {
            "id": signal.id,
            "original_message": signal.original_message,
            "final_content": signal.current_content,
            "hop_count": signal.hop_count,
            "path": signal.chain_path,
            "contributions": signal.node_contributions,
            "average_coherence": sum(signal.coherence_scores.values()) / max(1, len(signal.coherence_scores)),
            "total_drift": sum(signal.drift_scores.values()),
            "journey_time_ms": (signal.last_hop_at - signal.created_at) * 1000,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🎭 DEMO: HARMONIC POEM THROUGH THE CHAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

def run_harmonic_poem_demo():
    """Run the harmonic poem demonstration through the full chain."""
    
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "🎵🔗 HARMONIC SIGNAL CHAIN DEMO 🔗🎵" + " " * 26 + "║")
    print("║" + " " * 10 + "Integrated ThoughtBus + Enigma + Adaptive Learning" + " " * 17 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Initialize chain
    chain = HarmonicSignalChain()
    
    # Send the poem request
    signal = chain.send_signal("SING ME A POEM")
    
    # Display results
    summary = chain.get_signal_summary(signal)
    
    print("\n" + "═" * 80)
    print("═" * 80)
    
    print(f"""
    
    ╔{'═' * 60}╗
    ║{'🎭 THE COMPLETE HARMONIC POEM 🎭':^60}║
    ╠{'═' * 60}╣
    ║{' ' * 60}║
    ║{f'"{signal.current_content}"':^60}║
    ║{' ' * 60}║
    ╠{'═' * 60}╣
    ║{'Composed by: All Systems in Harmony':^60}║
    ╚{'═' * 60}╝
    
    """)
    
    # Show chain status
    print("📊 CHAIN STATUS:")
    print("─" * 60)
    status = chain.get_chain_status()
    for node_id, stats in status.items():
        print(f"   {node_id.upper():12} | Signals: {stats['signals_processed']:3} | "
              f"Success: {stats['success_rate']*100:.0f}% | "
              f"Coherence: {stats['average_coherence']:.2f}")
    
    print("\n📈 SIGNAL SUMMARY:")
    print("─" * 60)
    print(f"   Hops: {summary['hop_count']}")
    print(f"   Path: {' → '.join(summary['path'])}")
    print(f"   Avg Coherence: {summary['average_coherence']:.3f}")
    print(f"   Journey Time: {summary['journey_time_ms']:.1f}ms")
    
    # Show harmonic encoding
    if HARMONIC_ALPHABET_AVAILABLE:
        print("\n🎵 FINAL HARMONIC SIGNATURE:")
        print("─" * 60)
        harmonics = to_harmonics(signal.current_content)
        words = signal.current_content.split()
        word_idx = 0
        char_idx = 0
        for word in words:
            word_freqs = []
            for char in word:
                if char_idx < len(harmonics):
                    word_freqs.append(f"{harmonics[char_idx].frequency:.0f}Hz")
                char_idx += 1
            char_idx += 1  # space
            print(f"   '{word}' → [{', '.join(word_freqs)}]")
    
    # Round-trip verification
    print("\n🔄 ROUND-TRIP VERIFICATION:")
    print("─" * 60)
    if HARMONIC_ALPHABET_AVAILABLE:
        encoded = [(t.frequency, t.amplitude) for t in to_harmonics(signal.current_content)]
        decoded = from_harmonics(encoded)
        print(f"   Original:  '{signal.current_content}'")
        print(f"   Decoded:   '{decoded}'")
        print(f"   Match:     {'✅ PERFECT' if decoded == signal.current_content else '❌ MISMATCH'}")
    
    return chain, signal


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    chain, signal = run_harmonic_poem_demo()
    
    print("\n" + "═" * 80)
    print("🎵 Harmonic Signal Chain Complete - All Systems Sang in Unity 🎵")
    print("═" * 80 + "\n")
