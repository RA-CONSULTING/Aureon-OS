#!/usr/bin/env python3
"""
👻 AUREON PHANTOM SIGNAL FILTER & PATTERN CORRELATOR 👻
═══════════════════════════════════════════════════════════════════════════════
"Trust, but verify with the cosmos."

This module eliminates "Phantom Signals" by cross-referencing events across
distinct monitoring layers. A signal is only "Verified" if it resonates
simultaneously across different reality layers.

LAYERS OF REALITY:
1. 🌊 PHYSICAL:   Whale Sonar (Money Movement)
2. 🤖 DIGITAL:     Bot Shape Scanner (Algo Microstructure)
3. 🌌 HARMONIC:   HNC Surge Detector (Frequency Alignment)
4. 🌍 PLANETARY:  Stargate Protocol (Global Coherence)

PHANTOM SIGNAL THEORY:
A signal appearing in only ONE layer is likely noise or a trap (Phantom).
A signal appearing in MULTIPLE layers is a standing wave of truth.

OUTPUTS:
- `intelligence.signal.verified`: Validated opportunities (High Conviction)
- `intelligence.signal.phantom`: Rejected noise (Trap Avoidance)

Gary Leckey | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import time
import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - 👻 %(message)s'
)
logger = logging.getLogger('PhantomFilter')

# Try importing ThoughtBus
try:
    from aureon.core.aureon_thought_bus import get_thought_bus, Thought, ThoughtBus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    logger.warning("ThoughtBus not available - Phantom Filter running in isolation (simulation mode)")

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 COHERENCE MEMORY STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SignalEvent:
    source_layer: str  # 'PHYSICAL', 'DIGITAL', 'HARMONIC', 'PLANETARY'
    topic: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    
    @property
    def symbol(self) -> Optional[str]:
        # Attempt to extract symbol from payload
        return self.payload.get('symbol') or \
               self.payload.get('whale') or \
               self.payload.get('asset')

@dataclass
class Patternoverlap:
    """A detected overlap of signals"""
    primary_event: SignalEvent
    supporting_events: List[SignalEvent]
    layers_involved: List[str]
    coherence_score: float
    timestamp: float = field(default_factory=time.time)

# ═══════════════════════════════════════════════════════════════════════════════
# 🚦 PHANTOM FILTER CORE
# ═══════════════════════════════════════════════════════════════════════════════

class PhantomSignalFilter:
    def __init__(self, window_seconds: float = 3.0):
        self.window_seconds = window_seconds  # Coincidence window
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        
        # Recent event buffers (Layer -> deque)
        self.buffers: Dict[str, deque[SignalEvent]] = {
            'PHYSICAL': deque(maxlen=100),   # Whale
            'DIGITAL': deque(maxlen=100),    # Bot
            'HARMONIC': deque(maxlen=100),   # HNC
            'PLANETARY': deque(maxlen=100)   # Stargate
        }
        
        self.running = False
        self._lock = threading.Lock()
        
        logger.info(f"Phantom Filter Initialized (Window: {window_seconds}s)")

    def start(self):
        """Start listening to the ThoughtBus"""
        if not self.thought_bus:
            logger.error("Cannot start - ThoughtBus not connected")
            return
            
        self.running = True
        
        # Subscribe to all relevant layers
        
        # 🌊 PHYSICAL (Whales)
        self.thought_bus.subscribe("whale.sonar.*", self._on_whale_event)
        
        # 🤖 DIGITAL (Bots)
        self.thought_bus.subscribe("bot.shape.*", self._on_bot_event)
        
        # 🌌 HARMONIC (Surges)
        self.thought_bus.subscribe("intelligence.surge.hnc", self._on_hnc_event)
        
        # 🌍 PLANETARY (Stargates)
        self.thought_bus.subscribe("stargate.node.coherence", self._on_stargate_event)
        self.thought_bus.subscribe("stargate.timeline.anchored", self._on_stargate_event)
        self.thought_bus.subscribe("stargate.mirror.pull", self._on_stargate_event) # Added mirror pull
        
        logger.info("👻 Listening for signals on all reality layers...")

    def _on_whale_event(self, thought):
        self._ingest_signal('PHYSICAL', thought)

    def _on_bot_event(self, thought):
        self._ingest_signal('DIGITAL', thought)
        
    def _on_hnc_event(self, thought):
        # Determine urgency - HNC Surge is often the trigger
        self._ingest_signal('HARMONIC', thought)
        # Immediate validation analysis for Surges
        self._validate_surge(thought)

    def _on_stargate_event(self, thought):
        self._ingest_signal('PLANETARY', thought)

    def _ingest_signal(self, layer: str, thought):
        """Buffer a signal and perform clean-up"""
        with self._lock:
            # Respect source timestamp if available (for simulation/replay)
            ts = getattr(thought, 'ts', None) or getattr(thought, 'timestamp', None) or time.time()
            
            event = SignalEvent(layer, thought.topic, thought.payload, timestamp=ts)
            self.buffers[layer].append(event)
            
            # Debug log
            sym = event.symbol or "GLOBAL"
            logger.debug(f"Received {layer} signal: {thought.topic} ({sym})")
            
            # Prune old events
            # Use the latest event time as 'now' reference if we are in simulation mode (inferred from old ts)
            # Otherwise use wall clock
            ref_time = time.time()
            if abs(ts - ref_time) > 3600: # If timestamp is way off wall clock, assume simulation
                ref_time = ts
            
            for l in self.buffers:
                while self.buffers[l] and (ref_time - self.buffers[l][0].timestamp > self.window_seconds * 2):
                    self.buffers[l].popleft()

    def _validate_surge(self, surge_thought):
        """
        Special handling when an HNC Surge happens.
        Does it align with other layers?
        """
        ts = getattr(surge_thought, 'ts', None) or getattr(surge_thought, 'timestamp', None) or time.time()
        surge = SignalEvent('HARMONIC', surge_thought.topic, surge_thought.payload, timestamp=ts)
        
        # Use surge time as reference
        now = ts 
        
        supporting_events = []
        layers_hit = ['HARMONIC']
        
        symbol = surge.symbol
        
        with self._lock:
            # Check other layers
            for layer, buffer in self.buffers.items():
                if layer == 'HARMONIC': continue
                
                for event in buffer:
                    # Time check
                    if abs(event.timestamp - surge.timestamp) <= self.window_seconds:
                        # Correlation check
                        # 1. Symbol match (if available)
                        # 2. Or Global Stargate Coherence (applies to all)
                        
                        is_correlated = False
                        
                        if layer == 'PLANETARY':
                            # Stargate coherence is global - it validates ALL surges
                            payload = event.payload
                            if payload.get('coherence', 0) > 0.618 or payload.get('score', 0) > 0.6:
                                is_correlated = True
                        else:
                            # Whale/Bot needs symbol match or correlation
                            evt_sym = event.symbol
                            if evt_sym and symbol and (evt_sym in symbol or symbol in evt_sym):
                                is_correlated = True
                        
                        if is_correlated:
                            supporting_events.append(event)
                            if layer not in layers_hit:
                                layers_hit.append(layer)

        # ⚖️ JUDGMENT DAY
        coherence_score = len(layers_hit) / 4.0 # simple score
        
        if len(layers_hit) >= 2:
            # ✅ VERIFIED SIGNAL
            self._publish_verification(surge, supporting_events, layers_hit, coherence_score)
        else:
            # 👻 PHANTOM SIGNAL
            self._publish_phantom_warning(surge)

    def _publish_verification(self, primary: SignalEvent, support: List[SignalEvent], layers: List[str], score: float):
        """Publish a Verified Signal"""
        overlap_desc = " + ".join(layers)
        logger.info(pass_msg := f"✅ VERIFIED SIGNAL [{primary.symbol}]: {overlap_desc} (Score: {score:.2f})")
        
        payload = {
            'symbol': primary.symbol,
            'signal_type': 'VERIFIED',
            'layers': layers,
            'primary_source': primary.topic,
            'support_sources': [e.topic for e in support],
            'confidence': score,
            'timestamp': primary.timestamp,
            'action': 'ENGAGE_QUANTUM_GATES'
        }
        
        if self.thought_bus:
            # Emit Verified thought with correct timestamp
            t = Thought(
                source='phantom_filter', 
                topic='intelligence.signal.verified', 
                payload=payload,
                ts=primary.timestamp
            )
            self.thought_bus.publish(t)

            # Optional: Send to UI / Notification
            # self.thought_bus.publish(Thought(source='phantom_filter', topic='ui.alert', payload={'msg': pass_msg}))

    def _publish_phantom_warning(self, primary: SignalEvent):
        """Flag a Phantom Signal"""
        logger.warning(fail_msg := f"👻 PHANTOM SIGNAL DETECTED [{primary.symbol}]: HNC Surge without confirmation. (Ignored)")
        
        payload = {
            'symbol': primary.symbol,
            'signal_type': 'PHANTOM',
            'reason': 'Lack of multi-layer coherence',
            'timestamp': time.time(),
            'action': 'DISCARD'
        }
        
        if self.thought_bus:
            t = Thought(source='phantom_filter', topic='intelligence.signal.phantom', payload=payload)
            self.thought_bus.publish(t)

# ═══════════════════════════════════════════════════════════════════════════════
# 🏃 MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("👻 Starting Phantom Signal Filter...")
    
    if not THOUGHT_BUS_OK:
        print("❌ ThoughtBus library not found using mock for demo")
        
        # MOCK IMPLEMENTATION FOR DEMO IF NEEDED
        class MockThoughtBus:
            def subscribe(self, topic, cb): print(f"Subscribed to {topic}")
            def publish(self, t): print(f"📢 PUB: {t.topic} -> {t.payload}")
        
        THOUGHT_BUS_AVAILABLE = True
        get_thought_bus = lambda: MockThoughtBus()
        class Thought:
            def __init__(self, source, topic, payload):
                self.source, self.topic, self.payload = source, topic, payload

    filter_node = PhantomSignalFilter(window_seconds=5.0)
    filter_node.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("👻 Filter Stopped.")
