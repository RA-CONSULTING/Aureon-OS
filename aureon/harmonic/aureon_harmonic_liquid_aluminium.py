#!/usr/bin/env python3
"""
🌊🔩 AUREON HARMONIC LIQUID ALUMINIUM FIELD 🔩🌊
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

    "Like a big sheet of liquid aluminium dancing on hertz in a measured sandbox"

THE VISION:
    Every position, every price, every exchange - transformed into FREQUENCY.
    The entire trading system becomes a LIVING WAVEFORM - oscillating, resonating,
    breathing like liquid metal vibrating on a speaker cone at specific frequencies.

LIQUID ALUMINIUM PHYSICS:
    When you put aluminium powder on a speaker cone and play frequencies,
    it forms CYMATICS - geometric patterns based on the Hz. This is that.
    
    Each position = a NODE in the field
    Each price = a FREQUENCY (Hz)
    Each exchange = a HARMONIC LAYER (different resonance)
    P&L = AMPLITUDE (+ = peaks rising, - = troughs deepening)
    Volume = WAVE DENSITY (how thick the liquid pools)

FREQUENCY MAPPING (Sacred Numbers):
    Base: 432 Hz (Universal A tuning)
    $1 = 1 Hz shift from base
    $0.01 = 0.01 Hz micro-ripple
    
    Exchanges are HARMONIC LAYERS:
        Layer 1: Alpaca    → 174 Hz base (Root - Foundation)
        Layer 2: Kraken    → 285 Hz base (Sacral - Flow)  
        Layer 3: Binance   → 396 Hz base (Solar - Power)
        Layer 4: Capital   → 528 Hz base (Heart - Love)
    
    These layers INTERFERE - creating complex waveforms when combined.

LIVE STREAM OUTPUT:
    Every 100ms, the field state broadcasts to ThoughtBus:
    - All node frequencies
    - Combined waveform snapshot
    - Interference patterns
    - Standing wave formations (support/resistance)
    - Cymatics geometry prediction

Gary Leckey | Harmonic Liquid Aluminium | January 2026
"The market is sound. Price is frequency. We are the waveform."
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import sys
import os
import math
import time
import json
import asyncio
import logging
import threading
import inspect
from functools import wraps
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
from collections import deque
from enum import Enum

# UTF-8 fix for Windows
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# NumPy for waveform calculations
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)


def harmonic_streaming_runtime(method):
    """Own harmonic streaming for the lifetime of a blocking runtime method.

    Constructors only wire the field. A runtime entrypoint decorated with this
    helper starts the publisher explicitly and stops/joins it on every exit
    path. Nested runtime calls do not stop a stream owned by their caller.
    """

    def _start_owned(instance):
        field = getattr(instance, "harmonic_field", None)
        if field is None:
            return None
        try:
            return field if field.start_streaming() else None
        except Exception as exc:
            logger.warning("Harmonic streaming could not start: %s", exc)
            return None

    def _stop_owned(field):
        if field is None:
            return
        try:
            field.stop_streaming()
        except Exception as exc:
            logger.warning("Harmonic streaming could not stop cleanly: %s", exc)

    if inspect.iscoroutinefunction(method):
        @wraps(method)
        async def async_runtime(instance, *args, **kwargs):
            owned_field = _start_owned(instance)
            try:
                return await method(instance, *args, **kwargs)
            finally:
                _stop_owned(owned_field)

        return async_runtime

    @wraps(method)
    def runtime(instance, *args, **kwargs):
        owned_field = _start_owned(instance)
        try:
            return method(instance, *args, **kwargs)
        finally:
            _stop_owned(owned_field)

    return runtime

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🔩 SACRED CONSTANTS - THE FREQUENCIES OF REALITY
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2           # 1.618033988749895 - Golden Ratio
PHI_INV = 1 / PHI                       # 0.618033988749895 - Inverse Golden
SCHUMANN = 7.83                         # Hz - Earth's heartbeat
UNIVERSAL_A = 432                       # Hz - Universal tuning (base frequency)
LOVE_FREQ = 528                         # Hz - DNA repair / Love frequency
QUEEN_PROFIT_HZ = 188.0                 # Hz - Queen's profit frequency
ALUMINIUM_RESONANCE = 6420              # m/s - Speed of sound in aluminium

# Solfeggio Scale - The healing frequencies
SOLFEGGIO = {
    'UT':  174,   # Foundation - Alpaca base
    'RE':  285,   # Flow - Kraken base  
    'MI':  396,   # Power - Binance base
    'FA':  417,   # Change
    'SOL': 528,   # Love - Capital base
    'LA':  639,   # Connection
    'SI':  741,   # Intuition
    'DO':  852,   # Spirit
    'TI':  963,   # Crown - Queen frequency
}

# Exchange → Harmonic Layer Mapping
EXCHANGE_LAYERS = {
    'alpaca':  {'base_hz': 174, 'note': 'UT',  'color': '#00D4AA', 'icon': '🦙', 'layer': 1},
    'kraken':  {'base_hz': 285, 'note': 'RE',  'color': '#5B4FFF', 'icon': '🐙', 'layer': 2},
    'binance': {'base_hz': 396, 'note': 'MI',  'color': '#F3BA2F', 'icon': '🟡', 'layer': 3},
    'capital': {'base_hz': 528, 'note': 'SOL', 'color': '#FF6B6B', 'icon': '🏛️', 'layer': 4},
}

# Price → Frequency conversion constants
PRICE_TO_HZ_RATIO = 0.1                 # $1 = 0.1 Hz shift (gentle ripples)
VOLUME_TO_AMPLITUDE = 0.001             # Volume scaling to amplitude
PNL_TO_PHASE_SHIFT = math.pi / 100      # $1 PnL = small phase shift


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🌊 DATA STRUCTURES - The Shape of Waves
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class WaveState(Enum):
    """State of a wave in the liquid field"""
    RISING = "📈 RISING"           # Amplitude increasing
    FALLING = "📉 FALLING"         # Amplitude decreasing
    PEAK = "🏔️ PEAK"              # At maximum
    TROUGH = "🌊 TROUGH"           # At minimum
    STANDING = "🎯 STANDING"       # Standing wave (support/resistance)
    RESONATING = "🎵 RESONATING"   # In harmonic resonance
    CHAOTIC = "🌀 CHAOTIC"         # Interference disruption


class CymaticPattern(Enum):
    """Cymatics patterns formed by frequency interference"""
    CIRCLE = "⭕ CIRCLE"           # Single frequency dominant
    HEXAGON = "⬡ HEXAGON"         # Two frequencies in harmony
    STAR = "✡️ STAR"              # Multiple harmonics
    SPIRAL = "🌀 SPIRAL"          # Phase drift pattern
    MANDALA = "🔮 MANDALA"        # Complex multi-layer resonance
    CHAOS = "💫 CHAOS"            # No stable pattern


@dataclass
class LiquidNode:
    """
    A single node in the liquid aluminium field.
    Represents one position/asset vibrating at a specific frequency.
    """
    # Identity
    node_id: str                  # Exchange-Symbol: "kraken-BTCUSD"
    exchange: str
    symbol: str
    asset_class: str = "crypto"   # crypto, stock, forex
    
    # Wave Properties
    frequency: float = 432.0      # Current frequency (Hz)
    base_frequency: float = 432.0 # Exchange base frequency
    amplitude: float = 0.5        # Wave height (0-1)
    phase: float = 0.0           # Phase angle (radians)
    wavelength: float = 1.0      # Derived from frequency
    
    # Financial Mapping
    current_price: float = 0.0
    entry_price: float = 0.0
    quantity: float = 0.0
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    value_usd: float = 0.0
    
    # Wave State
    state: WaveState = WaveState.STANDING
    energy: float = 0.5          # Wave energy (amplitude² × frequency)
    
    # Historical (for wave animation)
    frequency_history: List[float] = field(default_factory=list)
    amplitude_history: List[float] = field(default_factory=list)
    
    # Timestamp
    last_update: float = 0.0
    
    def calculate_energy(self) -> float:
        """E = A² × f (wave energy formula)"""
        return (self.amplitude ** 2) * self.frequency
    
    def to_dict(self) -> Dict:
        return {
            'node_id': self.node_id,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'frequency': round(self.frequency, 2),
            'amplitude': round(self.amplitude, 4),
            'phase': round(self.phase, 4),
            'state': self.state.value,
            'energy': round(self.calculate_energy(), 2),
            'pnl_usd': round(self.pnl_usd, 2),
            'pnl_pct': round(self.pnl_pct, 2),
            'value_usd': round(self.value_usd, 2),
        }


@dataclass
class HarmonicLayer:
    """
    One exchange = one harmonic layer in the liquid field.
    Each layer vibrates at its base frequency with all its nodes.
    """
    layer_id: int
    exchange: str
    base_frequency: float
    note: str
    color: str
    icon: str
    
    # Aggregate metrics
    total_nodes: int = 0
    total_energy: float = 0.0
    average_frequency: float = 0.0
    average_amplitude: float = 0.0
    dominant_state: WaveState = WaveState.STANDING
    
    # Combined waveform (sampled)
    waveform_samples: List[float] = field(default_factory=list)
    
    # Nodes in this layer
    nodes: Dict[str, LiquidNode] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        # Include a light-weight waveform for visualization (capped to 240 samples to keep payload lean)
        waveform = self.waveform_samples[:240] if self.waveform_samples else []
        return {
            'layer': self.layer_id,
            'exchange': self.exchange,
            'base_hz': self.base_frequency,
            'note': self.note,
            'color': self.color,
            'icon': self.icon,
            'total_nodes': self.total_nodes,
            'total_energy': round(self.total_energy, 2),
            'avg_frequency': round(self.average_frequency, 2),
            'avg_amplitude': round(self.average_amplitude, 4),
            'dominant_state': self.dominant_state.value,
            'waveform': waveform,
        }


@dataclass
class FieldSnapshot:
    """
    Complete snapshot of the liquid aluminium field at a moment in time.
    This is what gets streamed to ThoughtBus.
    """
    timestamp: float
    cycle: int
    
    # Layers
    layers: Dict[str, HarmonicLayer] = field(default_factory=dict)
    
    # Global metrics
    total_nodes: int = 0
    total_energy: float = 0.0
    global_frequency: float = 432.0    # Dominant frequency
    global_amplitude: float = 0.5
    global_phase: float = 0.0
    
    # Interference patterns
    standing_waves: List[Dict] = field(default_factory=list)  # Support/resistance levels
    cymatics_pattern: CymaticPattern = CymaticPattern.CIRCLE
    
    # Combined waveform (master)
    master_waveform: List[float] = field(default_factory=list)
    
    # Financial summary
    total_value_usd: float = 0.0
    total_pnl_usd: float = 0.0
    
    def to_dict(self) -> Dict:
        def _downsample(seq: List[float], max_len: int = 360) -> List[float]:
            if not seq:
                return []
            step = max(1, len(seq) // max_len)
            return seq[::step][:max_len]

        # Flatten a small subset of nodes for the UI (cap to avoid payload bloat)
        nodes: List[Dict] = []
        for layer in self.layers.values():
            for node in layer.nodes.values():
                nodes.append(node.to_dict())
                if len(nodes) >= 200:  # keep payload lightweight for WebSocket
                    break
            if len(nodes) >= 200:
                break

        return {
            'timestamp': self.timestamp,
            'cycle': self.cycle,
            'layers': {k: v.to_dict() for k, v in self.layers.items()},
            'global': {
                'total_nodes': self.total_nodes,
                'total_energy': round(self.total_energy, 2),
                'frequency': round(self.global_frequency, 2),
                'amplitude': round(self.global_amplitude, 4),
                'phase': round(self.global_phase, 4),
            },
            'cymatics': self.cymatics_pattern.value,
            'standing_waves': self.standing_waves,
            'master_waveform': _downsample(self.master_waveform, 360),
            'nodes': nodes,
            'financial': {
                'total_value_usd': round(self.total_value_usd, 2),
                'total_pnl_usd': round(self.total_pnl_usd, 2),
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🔩 HARMONIC LIQUID ALUMINIUM FIELD - The Main Engine
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class HarmonicLiquidAluminiumField:
    """
    The Liquid Aluminium Field - transforms trading data into harmonic waveforms.
    
    Like liquid aluminium on a Chladni plate, the field vibrates and forms
    cymatics patterns based on the frequencies of all positions across all exchanges.
    
    LIVE STREAMING:
        - Publishes to ThoughtBus every 100ms
        - Each node = one vibrating particle of liquid
        - Combined waveform = superposition of all node waves
        - Cymatics pattern = the emergent geometry
    """
    
    def __init__(self, stream_interval_ms: int = 100):
        self.stream_interval_ms = stream_interval_ms
        self.stream_interval_s = stream_interval_ms / 1000.0
        
        # Initialize layers
        self.layers: Dict[str, HarmonicLayer] = {}
        for exchange, config in EXCHANGE_LAYERS.items():
            self.layers[exchange] = HarmonicLayer(
                layer_id=config['layer'],
                exchange=exchange,
                base_frequency=config['base_hz'],
                note=config['note'],
                color=config['color'],
                icon=config['icon'],
            )
        
        # All nodes (flat lookup)
        self.nodes: Dict[str, LiquidNode] = {}
        
        # Field state
        self.cycle_count = 0
        self.running = False
        self.start_time = time.time()
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_stop_event = threading.Event()
        self._stream_lifecycle_lock = threading.Lock()
        
        # Waveform calculation
        self.sample_rate = 1000   # Samples per second for waveform
        self.waveform_duration = 0.1  # 100ms of waveform data
        self.waveform_samples = int(self.sample_rate * self.waveform_duration)
        
        # History (for animation)
        self.snapshot_history: deque = deque(maxlen=100)
        
        # ThoughtBus
        self.thought_bus = None
        self._init_thought_bus()
        
        # Callbacks for visualization
        self.on_snapshot_callbacks: List[Callable] = []
        
        logger.info("🔩 Harmonic Liquid Aluminium Field initialized")
        logger.info(f"   Stream interval: {stream_interval_ms}ms")
        logger.info(f"   Layers: {len(self.layers)}")
        
    def _init_thought_bus(self):
        """Initialize ThoughtBus connection."""
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
            # Try to get existing bus or create new
            try:
                self.thought_bus = get_thought_bus()
            except:
                self.thought_bus = ThoughtBus()
            self.Thought = Thought
            logger.info("   ✅ ThoughtBus connected")
        except ImportError:
            self.thought_bus = None
            self.Thought = None
            logger.warning("   ⚠️ ThoughtBus not available")
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 🎵 FREQUENCY MAPPING - Price to Sound
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def price_to_frequency(self, price: float, base_hz: float = UNIVERSAL_A) -> float:
        """
        Convert price to frequency (Hz).
        
        Formula: f = base_hz + (price × PRICE_TO_HZ_RATIO)
        
        This creates gentle ripples in the field based on price.
        Higher prices = higher frequencies = blue shift.
        Lower prices = lower frequencies = red shift.
        """
        if price <= 0:
            return base_hz
        
        # Log scale for large price ranges (BTC $100K vs SHIB $0.00001)
        log_price = math.log10(max(price, 0.000001))
        
        # Map to frequency: base + scaled log
        freq = base_hz + (log_price * 50)  # 50 Hz per order of magnitude
        
        # Clamp to audible range (20 Hz - 20,000 Hz)
        return max(20.0, min(freq, 20000.0))
    
    def pnl_to_amplitude(self, pnl_usd: float, entry_value: float) -> float:
        """
        Convert P&L to wave amplitude.
        
        Profitable = higher amplitude (peaks)
        Loss = lower amplitude (troughs)
        """
        if entry_value <= 0:
            return 0.5  # Neutral
        
        pnl_pct = (pnl_usd / entry_value) * 100
        
        # Map to 0-1 range: -10% → 0.0, 0% → 0.5, +10% → 1.0
        amplitude = 0.5 + (pnl_pct / 20.0)
        
        return max(0.0, min(1.0, amplitude))
    
    def pnl_to_phase(self, pnl_usd: float) -> float:
        """
        Convert P&L to phase shift.
        
        Positive P&L = positive phase (leading wave)
        Negative P&L = negative phase (lagging wave)
        """
        # $10 = π/10 phase shift
        return (pnl_usd / 100.0) * math.pi
    
    def detect_wave_state(self, node: LiquidNode) -> WaveState:
        """Detect the current wave state based on history."""
        if len(node.frequency_history) < 3:
            return WaveState.STANDING
        
        recent = node.frequency_history[-3:]
        
        # Check trend
        if recent[-1] > recent[-2] > recent[-3]:
            return WaveState.RISING
        elif recent[-1] < recent[-2] < recent[-3]:
            return WaveState.FALLING
        elif recent[-1] == max(recent):
            return WaveState.PEAK
        elif recent[-1] == min(recent):
            return WaveState.TROUGH
        
        # Check for resonance (stable frequency near harmonic)
        for note, freq in SOLFEGGIO.items():
            if abs(node.frequency - freq) < 5:  # Within 5 Hz of harmonic
                return WaveState.RESONATING
        
        return WaveState.STANDING
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 🔩 NODE MANAGEMENT - Particles in the Liquid
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def add_or_update_node(
        self,
        exchange: str,
        symbol: str,
        current_price: float,
        entry_price: float = 0.0,
        quantity: float = 0.0,
        asset_class: str = "crypto"
    ) -> LiquidNode:
        """
        Add or update a node in the liquid field.
        
        Each position becomes a vibrating particle of liquid aluminium,
        oscillating at a frequency determined by its price.
        """
        exchange = exchange.lower()
        node_id = f"{exchange}-{symbol}"
        
        # Get or create layer
        if exchange not in self.layers:
            # Unknown exchange - use Universal A
            self.layers[exchange] = HarmonicLayer(
                layer_id=len(self.layers) + 1,
                exchange=exchange,
                base_frequency=UNIVERSAL_A,
                note='A',
                color='#888888',
                icon='❓',
            )
        
        layer = self.layers[exchange]
        
        # Calculate wave properties
        base_hz = layer.base_frequency
        frequency = self.price_to_frequency(current_price, base_hz)
        
        entry_value = entry_price * quantity if entry_price > 0 else current_price * quantity
        current_value = current_price * quantity
        pnl_usd = current_value - entry_value if entry_price > 0 else 0.0
        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
        
        amplitude = self.pnl_to_amplitude(pnl_usd, entry_value)
        phase = self.pnl_to_phase(pnl_usd)
        wavelength = ALUMINIUM_RESONANCE / frequency if frequency > 0 else 1.0
        
        # Get or create node
        if node_id in self.nodes:
            node = self.nodes[node_id]
            # Update history
            node.frequency_history.append(frequency)
            node.amplitude_history.append(amplitude)
            # Keep last 100 samples
            if len(node.frequency_history) > 100:
                node.frequency_history = node.frequency_history[-100:]
                node.amplitude_history = node.amplitude_history[-100:]
        else:
            node = LiquidNode(
                node_id=node_id,
                exchange=exchange,
                symbol=symbol,
                asset_class=asset_class,
                base_frequency=base_hz,
            )
            self.nodes[node_id] = node
            layer.nodes[node_id] = node
        
        # Update node properties
        node.frequency = frequency
        node.amplitude = amplitude
        node.phase = phase
        node.wavelength = wavelength
        node.current_price = current_price
        node.entry_price = entry_price
        node.quantity = quantity
        node.pnl_usd = pnl_usd
        node.pnl_pct = pnl_pct
        node.value_usd = current_value
        node.energy = node.calculate_energy()
        node.state = self.detect_wave_state(node)
        node.last_update = time.time()
        
        return node
    
    def remove_node(self, exchange: str, symbol: str):
        """Remove a node from the field."""
        node_id = f"{exchange.lower()}-{symbol}"
        if node_id in self.nodes:
            node = self.nodes.pop(node_id)
            if node.exchange in self.layers:
                self.layers[node.exchange].nodes.pop(node_id, None)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 🌊 WAVEFORM CALCULATION - The Dance of Liquid Metal
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def calculate_layer_waveform(self, layer: HarmonicLayer, t: float = 0.0) -> List[float]:
        """
        Calculate combined waveform for one layer (one exchange).
        
        Each node contributes a sine wave: y = A × sin(2πft + φ)
        Layer waveform = superposition of all node waves.
        """
        if not NUMPY_AVAILABLE:
            return []
        
        # Time array for waveform samples
        t_array = np.linspace(t, t + self.waveform_duration, self.waveform_samples)
        
        # Start with zero
        combined = np.zeros(self.waveform_samples)
        
        for node in layer.nodes.values():
            # y = A × sin(2πft + φ)
            wave = node.amplitude * np.sin(2 * np.pi * node.frequency * t_array + node.phase)
            combined += wave
        
        # Normalize
        if len(layer.nodes) > 0:
            combined /= len(layer.nodes)
        
        return combined.tolist()
    
    def calculate_master_waveform(self, t: float = 0.0) -> List[float]:
        """
        Calculate the MASTER waveform - all layers combined.
        
        This is the "liquid aluminium sheet" - the full field visualization.
        Different layers create interference patterns = cymatics.
        """
        if not NUMPY_AVAILABLE:
            return []
        
        # Time array
        t_array = np.linspace(t, t + self.waveform_duration, self.waveform_samples)
        
        # Start with zero
        master = np.zeros(self.waveform_samples)
        
        for layer in self.layers.values():
            layer_wave = self.calculate_layer_waveform(layer, t)
            if layer_wave:
                master += np.array(layer_wave)
        
        # Normalize by number of layers
        if len(self.layers) > 0:
            master /= len(self.layers)
        
        return master.tolist()
    
    def detect_standing_waves(self, waveform: List[float]) -> List[Dict]:
        """
        Detect standing waves (nodes and antinodes).
        
        Standing waves = support/resistance levels in trading terms.
        Where waves consistently cancel = support
        Where waves consistently amplify = resistance
        """
        if not waveform or not NUMPY_AVAILABLE:
            return []
        
        wave = np.array(waveform)
        standing = []
        
        # Find zero crossings (nodes)
        zero_crossings = np.where(np.diff(np.signbit(wave)))[0]
        for idx in zero_crossings:
            standing.append({
                'type': 'node',
                'position': idx / len(waveform),
                'description': 'Standing wave node (support level)'
            })
        
        # Find peaks and troughs (antinodes)
        for i in range(1, len(wave) - 1):
            if wave[i] > wave[i-1] and wave[i] > wave[i+1]:
                standing.append({
                    'type': 'antinode_peak',
                    'position': i / len(waveform),
                    'amplitude': float(wave[i]),
                    'description': 'Standing wave antinode (resistance)'
                })
            elif wave[i] < wave[i-1] and wave[i] < wave[i+1]:
                standing.append({
                    'type': 'antinode_trough',
                    'position': i / len(waveform),
                    'amplitude': float(wave[i]),
                    'description': 'Standing wave antinode (support)'
                })
        
        return standing[:10]  # Limit to top 10
    
    def detect_cymatics_pattern(self) -> CymaticPattern:
        """
        Detect the cymatics pattern formed by layer interference.
        
        Like liquid aluminium on a Chladni plate, the combined frequencies
        create geometric patterns. This predicts the pattern.
        """
        active_layers = [l for l in self.layers.values() if l.total_nodes > 0]
        
        if len(active_layers) == 0:
            return CymaticPattern.CHAOS
        elif len(active_layers) == 1:
            return CymaticPattern.CIRCLE
        elif len(active_layers) == 2:
            # Check frequency ratio for harmony
            freqs = sorted([l.average_frequency for l in active_layers if l.average_frequency > 0])
            if len(freqs) >= 2 and freqs[0] > 0:
                ratio = freqs[1] / freqs[0]
                # Simple ratios = harmonious patterns
                if abs(ratio - 2.0) < 0.1:    # Octave
                    return CymaticPattern.HEXAGON
                elif abs(ratio - 1.5) < 0.1:  # Fifth
                    return CymaticPattern.STAR
                elif abs(ratio - PHI) < 0.1:  # Golden ratio
                    return CymaticPattern.MANDALA
            return CymaticPattern.HEXAGON
        elif len(active_layers) == 3:
            return CymaticPattern.STAR
        else:
            return CymaticPattern.MANDALA
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 📸 SNAPSHOT - Capture Field State
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def capture_snapshot(self) -> FieldSnapshot:
        """
        Capture complete field state at this moment.
        
        This is what gets live-streamed to ThoughtBus.
        """
        self.cycle_count += 1
        t = time.time() - self.start_time
        
        # Update layer aggregates
        total_nodes = 0
        total_energy = 0.0
        total_value = 0.0
        total_pnl = 0.0
        
        for layer in self.layers.values():
            layer.total_nodes = len(layer.nodes)
            
            if layer.total_nodes > 0:
                layer.total_energy = sum(n.energy for n in layer.nodes.values())
                layer.average_frequency = sum(n.frequency for n in layer.nodes.values()) / layer.total_nodes
                layer.average_amplitude = sum(n.amplitude for n in layer.nodes.values()) / layer.total_nodes
                
                # Dominant state
                states = [n.state for n in layer.nodes.values()]
                layer.dominant_state = max(set(states), key=states.count) if states else WaveState.STANDING
                
                # Layer waveform
                layer.waveform_samples = self.calculate_layer_waveform(layer, t)
            else:
                layer.total_energy = 0.0
                layer.average_frequency = layer.base_frequency
                layer.average_amplitude = 0.0
                layer.dominant_state = WaveState.STANDING
                layer.waveform_samples = []
            
            total_nodes += layer.total_nodes
            total_energy += layer.total_energy
            total_value += sum(n.value_usd for n in layer.nodes.values())
            total_pnl += sum(n.pnl_usd for n in layer.nodes.values())
        
        # Master waveform
        master_waveform = self.calculate_master_waveform(t)
        
        # Global frequency (energy-weighted average)
        if total_energy > 0:
            global_frequency = sum(
                n.frequency * n.energy 
                for n in self.nodes.values()
            ) / total_energy
        else:
            global_frequency = UNIVERSAL_A
        
        # Global amplitude (average)
        global_amplitude = sum(n.amplitude for n in self.nodes.values()) / max(total_nodes, 1)
        
        # Global phase (average)
        global_phase = sum(n.phase for n in self.nodes.values()) / max(total_nodes, 1)
        
        # Detect patterns
        standing_waves = self.detect_standing_waves(master_waveform)
        cymatics_pattern = self.detect_cymatics_pattern()
        
        snapshot = FieldSnapshot(
            timestamp=time.time(),
            cycle=self.cycle_count,
            layers=self.layers.copy(),
            total_nodes=total_nodes,
            total_energy=total_energy,
            global_frequency=global_frequency,
            global_amplitude=global_amplitude,
            global_phase=global_phase,
            standing_waves=standing_waves,
            cymatics_pattern=cymatics_pattern,
            master_waveform=master_waveform,
            total_value_usd=total_value,
            total_pnl_usd=total_pnl,
        )
        
        # Add to history
        self.snapshot_history.append(snapshot)
        
        return snapshot
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 📡 LIVE STREAMING - Broadcast to ThoughtBus
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def publish_snapshot(self, snapshot: FieldSnapshot):
        """Publish snapshot to ThoughtBus."""
        if self.thought_bus and self.Thought:
            thought = self.Thought(
                source="liquid_aluminium_field",
                topic="harmonic.field.snapshot",
                payload=snapshot.to_dict(),
                meta={
                    'stream_interval_ms': self.stream_interval_ms,
                    'uptime_s': time.time() - self.start_time,
                }
            )
            self.thought_bus.publish(thought)
        
        # Call registered callbacks
        for callback in self.on_snapshot_callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def on_snapshot(self, callback: Callable[[FieldSnapshot], None]):
        """Register callback for snapshot events."""
        self.on_snapshot_callbacks.append(callback)
    
    def _stream_loop(self):
        """Internal streaming loop."""
        try:
            while not self._stream_stop_event.is_set():
                try:
                    snapshot = self.capture_snapshot()
                    self.publish_snapshot(snapshot)
                    self._stream_stop_event.wait(self.stream_interval_s)
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    self._stream_stop_event.wait(1.0)
        finally:
            self.running = False

    def start_streaming(self) -> bool:
        """Explicitly start the live publisher thread.

        Returns True only when this call starts a new thread. Construction
        never calls this method; the runtime owner must do so explicitly.
        """
        if os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").lower() in {"1", "true", "yes", "on"}:
            logger.debug("streaming thread suppressed (AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS)")
            return False

        with self._stream_lifecycle_lock:
            if self.running or (self._stream_thread is not None and self._stream_thread.is_alive()):
                return False
            self._stream_stop_event.clear()
            self.running = True
            self.start_time = time.time()
            self._stream_thread = threading.Thread(
                target=self._stream_loop,
                name="HarmonicLiquidAluminiumField",
                daemon=True,
            )
            try:
                self._stream_thread.start()
            except Exception:
                self.running = False
                self._stream_thread = None
                raise

        logger.info("Harmonic Liquid Aluminium Field streaming started")
        return True

    def stop_streaming(self, timeout: float = 2.0) -> bool:
        """Stop and join the owned publisher thread."""
        with self._stream_lifecycle_lock:
            self.running = False
            self._stream_stop_event.set()
            worker = self._stream_thread

        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=max(0.0, float(timeout)))

        stopped = worker is None or not worker.is_alive()
        if stopped:
            with self._stream_lifecycle_lock:
                if self._stream_thread is worker:
                    self._stream_thread = None
            logger.info("Harmonic Liquid Aluminium Field streaming stopped")
        else:
            logger.warning("Harmonic streaming thread did not stop within %.2fs", timeout)
        return stopped
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 🎨 VISUALIZATION - Console Art
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def render_ascii_field(self) -> str:
        """Render the field as ASCII art."""
        snapshot = self.capture_snapshot()
        
        lines = []
        lines.append("")
        lines.append("🔩═══════════════════════════════════════════════════════════════════🔩")
        lines.append("║     🌊 HARMONIC LIQUID ALUMINIUM FIELD 🌊     ║")
        lines.append("🔩═══════════════════════════════════════════════════════════════════🔩")
        lines.append("")
        lines.append(f"  Cycle: {snapshot.cycle:,}  |  Nodes: {snapshot.total_nodes}  |  Cymatics: {snapshot.cymatics_pattern.value}")
        lines.append(f"  Global Hz: {snapshot.global_frequency:.1f}  |  Amplitude: {snapshot.global_amplitude:.3f}  |  Energy: {snapshot.total_energy:.1f}")
        lines.append(f"  Value: ${snapshot.total_value_usd:,.2f}  |  P&L: ${snapshot.total_pnl_usd:+,.2f}")
        lines.append("")
        
        # Render each layer
        for layer in sorted(self.layers.values(), key=lambda l: l.layer_id):
            icon = layer.icon
            nodes = layer.total_nodes
            hz = layer.average_frequency
            amp = layer.average_amplitude
            
            # Waveform bar
            if layer.waveform_samples:
                wave_chars = "▁▂▃▄▅▆▇█"
                wave_display = ""
                step = max(1, len(layer.waveform_samples) // 40)
                for i in range(0, min(40, len(layer.waveform_samples)), step):
                    val = (layer.waveform_samples[i] + 1) / 2  # Normalize to 0-1
                    idx = int(val * (len(wave_chars) - 1))
                    wave_display += wave_chars[max(0, min(idx, len(wave_chars)-1))]
            else:
                wave_display = "░" * 40
            
            lines.append(f"  {icon} Layer {layer.layer_id} ({layer.exchange.upper()}) │ {layer.note} @ {hz:.0f}Hz")
            lines.append(f"     Nodes: {nodes}  |  Amp: {amp:.3f}  |  {layer.dominant_state.value}")
            lines.append(f"     ┌{'─'*42}┐")
            lines.append(f"     │ {wave_display} │")
            lines.append(f"     └{'─'*42}┘")
            lines.append("")
        
        # Master waveform
        lines.append("  🌊 MASTER WAVEFORM (All Layers Combined)")
        if snapshot.master_waveform:
            wave_chars = "▁▂▃▄▅▆▇█"
            wave_display = ""
            step = max(1, len(snapshot.master_waveform) // 60)
            for i in range(0, min(60, len(snapshot.master_waveform)), step):
                val = (snapshot.master_waveform[i] + 1) / 2
                idx = int(val * (len(wave_chars) - 1))
                wave_display += wave_chars[max(0, min(idx, len(wave_chars)-1))]
            lines.append(f"     ┌{'─'*62}┐")
            lines.append(f"     │ {wave_display} │")
            lines.append(f"     └{'─'*62}┘")
        
        lines.append("")
        lines.append("🔩═══════════════════════════════════════════════════════════════════🔩")
        
        return "\n".join(lines)
    
    def print_field(self):
        """Print field state to console."""
        print(self.render_ascii_field())


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🔗 INTEGRATION WITH UNIFIED KILL CHAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class HarmonicKillChainAdapter:
    """
    Adapter to feed UnifiedKillChain data into the Harmonic Liquid Aluminium Field.
    
    This wraps the UnifiedKillChain and transforms every scan into
    harmonic waveform updates.
    """
    
    def __init__(self, field: HarmonicLiquidAluminiumField):
        self.field = field
        self.kill_chain = None
        
        # Import and wrap the kill chain
        try:
            from aureon.trading.unified_kill_chain import UnifiedKillChain
            self.kill_chain = UnifiedKillChain()
            logger.info("🔗 HarmonicKillChainAdapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize UnifiedKillChain: {e}")
    
    def scan_and_harmonize(self):
        """Scan all exchanges and update the harmonic field."""
        if not self.kill_chain:
            return
        
        # Scan Alpaca
        self._harmonize_alpaca()
        
        # Scan Kraken
        self._harmonize_kraken()
        
        # Scan Binance
        self._harmonize_binance()
        
        # Scan Capital
        self._harmonize_capital()
    
    def _harmonize_alpaca(self):
        """Transform Alpaca positions into harmonic nodes."""
        try:
            client = self.kill_chain.alpaca
            positions = client.get_positions()
            
            if not positions:
                return
            
            for p in positions:
                symbol = p.get('symbol', '')
                qty = float(p.get('qty', 0))
                current_price = float(p.get('current_price', 0))
                entry_price = float(p.get('avg_entry_price', 0))
                asset_class = p.get('asset_class', 'crypto')
                
                if qty > 0 and current_price > 0:
                    self.field.add_or_update_node(
                        exchange='alpaca',
                        symbol=symbol,
                        current_price=current_price,
                        entry_price=entry_price,
                        quantity=qty,
                        asset_class=asset_class
                    )
        except Exception as e:
            logger.error(f"Alpaca harmonize error: {e}")
    
    def _harmonize_kraken(self):
        """Transform Kraken balances into harmonic nodes."""
        try:
            client = self.kill_chain.kraken
            balances = client.get_account_balance()
            
            if not balances or isinstance(balances, list):
                return
            
            # Batch fetch tickers
            all_tickers = {}
            try:
                ticker_list = client.get_24h_tickers()
                for t in ticker_list:
                    sym = t.get('symbol', '')
                    if sym:
                        all_tickers[sym] = float(t.get('lastPrice', 0))
            except:
                pass
            
            SKIP = {'ZUSD', 'USD', 'USDC', 'USDT', 'ZEUR', 'EUR', 'KFEE'}
            
            for asset, qty in balances.items():
                qty = float(qty)
                if qty <= 0 or asset in SKIP:
                    continue
                
                # Find price
                clean_asset = asset.lstrip('X').lstrip('Z')
                price = 0.0
                
                for pair in [f"{asset}USD", f"{clean_asset}USD", f"{asset}USDT"]:
                    if pair in all_tickers and all_tickers[pair] > 0:
                        price = all_tickers[pair]
                        break
                
                if price > 0:
                    # Get cost basis if available
                    entry_price = 0.0
                    try:
                        cost = client.calculate_cost_basis(f"{clean_asset}USD")
                        if cost:
                            entry_price = cost.get('avg_entry_price', 0)
                    except:
                        pass
                    
                    self.field.add_or_update_node(
                        exchange='kraken',
                        symbol=clean_asset,
                        current_price=price,
                        entry_price=entry_price,
                        quantity=qty,
                        asset_class='crypto'
                    )
        except Exception as e:
            logger.error(f"Kraken harmonize error: {e}")
    
    def _harmonize_binance(self):
        """Transform Binance balances into harmonic nodes."""
        try:
            client = self.kill_chain.binance
            acct = client.account()
            
            if not acct or 'balances' not in acct:
                return
            
            # Batch fetch tickers
            all_tickers = {}
            try:
                ticker_list = client.get_24h_tickers()
                for t in ticker_list:
                    sym = t.get('symbol', '')
                    if sym:
                        all_tickers[sym] = float(t.get('lastPrice', 0))
            except:
                pass
            
            SKIP = {'USDT', 'USDC', 'BUSD', 'GBP', 'USD', 'EUR', 'DAI', 'FDUSD'}
            
            for b in acct['balances']:
                asset = b['asset']
                qty = float(b['free']) + float(b['locked'])
                
                if qty <= 0 or asset in SKIP or asset.startswith('LD'):
                    continue
                
                # Find price
                price = 0.0
                for quote in ['USDT', 'USDC']:
                    pair = f"{asset}{quote}"
                    if pair in all_tickers and all_tickers[pair] > 0:
                        price = all_tickers[pair]
                        break
                
                if price > 0:
                    entry_price = 0.0
                    try:
                        cost = client.calculate_cost_basis(f"{asset}USDT")
                        if cost:
                            entry_price = cost.get('avg_entry_price', 0)
                    except:
                        pass
                    
                    self.field.add_or_update_node(
                        exchange='binance',
                        symbol=asset,
                        current_price=price,
                        entry_price=entry_price,
                        quantity=qty,
                        asset_class='crypto'
                    )
        except Exception as e:
            logger.error(f"Binance harmonize error: {e}")
    
    def _harmonize_capital(self):
        """Transform Capital.com positions into harmonic nodes."""
        try:
            client = self.kill_chain.capital
            if not client.enabled:
                return
            
            positions = client.get_positions()
            if not positions:
                return
            
            for p in positions:
                market = p.get('market', {})
                pos_data = p.get('position', {})
                
                symbol = market.get('epic', '')
                level = float(market.get('bid', 0)) or float(market.get('offer', 0))
                entry = float(pos_data.get('openLevel', 0))
                size = float(pos_data.get('dealSize', 0))
                
                if symbol and level > 0:
                    self.field.add_or_update_node(
                        exchange='capital',
                        symbol=symbol,
                        current_price=level,
                        entry_price=entry,
                        quantity=size,
                        asset_class='forex' if 'USD' in symbol or 'EUR' in symbol else 'crypto'
                    )
        except Exception as e:
            logger.error(f"Capital harmonize error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🌊 GLOBAL MARKET FLUID - FFT SPECTRUM MAPPER (PAST → PRESENT → FUTURE)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def run_global_market_fluid():
    """
    Treats the global market as a single LIVING FLUID.
    Fetches live prices, builds waveform, runs FFT, maps temporal dimensions.
    
    LIVE DATA SOURCES (no API keys):
      - CoinGecko public API (top 100 cryptos)
      - Binance public ticker stream
      - Historical state files (cost_basis, positions)
    
    FREQUENCY DOMAIN:
      - FFT extracts dominant harmonics from price waveforms
      - Maps past (historical cost basis) → present (live price) → future (spectral prediction)
    """
    import urllib.request
    from collections import defaultdict
    
    print()
    print("🌊",  "═"*68, "🌊")
    print("║   GLOBAL MARKET FLUID — FFT SPECTRUM MAPPER                         ║")
    print("║   'The entire world market flows as liquid light through time'      ║")
    print("🌊", "═"*68, "🌊")
    
    # ─── 1. Fetch live global prices ───────────────────────────────────────
    print("\n📡 Fetching live global market data...")
    
    live_prices = {}
    
    # CoinGecko top 100
    try:
        url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&sparkline=true'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            markets = json.loads(r.read())
        for m in markets:
            sym = m['symbol'].upper()
            price = m.get('current_price', 0)
            if price and price > 0:
                live_prices[sym] = {
                    'price': price,
                    'mktcap': m.get('market_cap', 0) or 0,
                    'vol_24h': m.get('total_volume', 0) or 0,
                    'change_24h': m.get('price_change_percentage_24h', 0) or 0,
                    'sparkline': m.get('sparkline_in_7d', {}).get('price', []) or [],
                }
        print(f"✅ CoinGecko: {len(live_prices)} coins loaded")
    except Exception as e:
        print(f"⚠️  CoinGecko error: {e}")
    
    # ─── 2. Load historical state (cost basis = "past") ──────────────────────
    print("📚 Loading portfolio history (PAST dimension)...")
    
    past_prices = {}  # symbol → entry prices from history
    try:
        if os.path.exists('cost_basis_history.json'):
            with open('cost_basis_history.json') as f:
                history = json.load(f)
            if isinstance(history, list):
                for item in history:
                    sym = item.get('symbol', '')
                    if sym:
                        past_prices[sym] = float(item.get('cost_basis', 0)) / float(item.get('quantity', 1)) if item.get('quantity') else 0
        print(f"✅ History loaded: {len(past_prices)} symbol entry points")
    except Exception as e:
        print(f"⚠️  History load error: {e}")
    
    # ─── 3. Load current portfolio (present dimension) ──────────────────────
    print("💰 Loading current portfolio (PRESENT dimension)...")
    
    portfolio = {'total_cost': 0, 'total_value': 0, 'positions': []}
    try:
        if os.path.exists('alpaca_truth_tracker_state.json'):
            state = json.load(open('alpaca_truth_tracker_state.json'))
            for pos in state.get('positions', []):
                sym = pos.get('symbol', '').replace('USD', '')
                qty = float(pos.get('qty', 0))
                entry = float(pos.get('avg_entry_price', 0))
                current = live_prices.get(sym, {}).get('price', entry)
                cost = qty * entry
                val = qty * current
                portfolio['total_cost'] += cost
                portfolio['total_value'] += val
                portfolio['positions'].append({
                    'symbol': sym,
                    'qty': qty,
                    'entry_price': entry,
                    'current_price': current,
                    'pnl': val - cost,
                    'pnl_pct': ((val - cost) / cost * 100) if cost else 0,
                })
        print(f"✅ Portfolio: {len(portfolio['positions'])} positions, P&L: ${portfolio['total_value'] - portfolio['total_cost']:+.2f}")
    except Exception as e:
        print(f"⚠️  Portfolio load error: {e}")
    
    # ─── 4. Build master waveform from live prices ──────────────────────────
    print("\n🌊 Building master waveform (price → frequency space)...")
    
    # Sort by market cap, take top symbols with data
    ranked = sorted(
        [(sym, data) for sym, data in live_prices.items() if data['price'] > 0],
        key=lambda x: x[1]['mktcap'],
        reverse=True
    )[:50]  # Top 50 liquid assets
    
    master_waveform = []
    symbol_order = []
    
    for sym, data in ranked:
        # Price as frequency: $X.XX → X.XX Hz (scaled down)
        base_hz = min(data['price'], 500)  # Cap at 500 Hz
        symbol_order.append(sym)
        master_waveform.append(base_hz)
    
    print(f"✅ Master waveform: {len(master_waveform)} nodes (top assets)")
    
    # ─── 5. FFT analysis (extract harmonic structure) ──────────────────────
    print("🎼 Running FFT spectral analysis...")
    
    fft_result = None
    frequencies = None
    magnitudes = None
    
    if NUMPY_AVAILABLE and len(master_waveform) > 1:
        try:
            # Zero-pad to power of 2
            n = 2 ** int(math.ceil(math.log2(len(master_waveform))))
            wf = np.array(master_waveform, dtype=np.float32)
            wf = np.pad(wf, (0, n - len(wf)), 'constant')
            
            # FFT
            fft_vals = np.fft.fft(wf)
            magnitudes = np.abs(fft_vals[:n//2])
            frequencies = np.fft.fftfreq(n, d=1.0)[:n//2]
            
            # Find dominant frequencies (peaks)
            top_indices = np.argsort(magnitudes)[-5:][::-1]  # Top 5 harmonics
            top_freqs = [(frequencies[i], magnitudes[i]) for i in top_indices if magnitudes[i] > 0]
            
            print(f"✅ FFT complete: {len(top_freqs)} dominant harmonics")
            print("   Top harmonic frequencies:")
            for freq, mag in top_freqs:
                print(f"      {freq:.3f} Hz (magnitude: {mag:.2f})")
            
            fft_result = {'freqs': top_freqs, 'full_magnitudes': magnitudes}
        except Exception as e:
            print(f"⚠️  FFT error: {e}")
    else:
        print("⚠️  NumPy unavailable or insufficient data for FFT")
    
    # ─── 6. Temporal dimension mapping (PAST → PRESENT → FUTURE) ──────────────
    print("\n🕐 Mapping temporal dimensions...")
    
    temporal_map = {
        'past': {'avg_entry': 0, 'count': 0},
        'present': {'avg_price': 0, 'count': 0},
        'future': {'predicted_mean': 0, 'predicted_trend': 'unknown'},
    }
    
    # PAST: average entry from history
    if past_prices:
        temporal_map['past']['avg_entry'] = sum(past_prices.values()) / len(past_prices)
        temporal_map['past']['count'] = len(past_prices)
    
    # PRESENT: current portfolio P&L
    if portfolio['total_cost'] > 0:
        temporal_map['present']['avg_price'] = portfolio['total_value'] / len(portfolio['positions']) if portfolio['positions'] else 0
        temporal_map['present']['pnl'] = portfolio['total_value'] - portfolio['total_cost']
        temporal_map['present']['pnl_pct'] = (temporal_map['present']['pnl'] / portfolio['total_cost'] * 100)
        temporal_map['present']['count'] = len(portfolio['positions'])
    
    # FUTURE: predict from FFT harmonics + momentum
    if fft_result and len(fft_result['freqs']) > 0:
        # Naive prediction: average of dominant frequencies
        dominant_freq = fft_result['freqs'][0][0] if fft_result['freqs'] else 100
        temporal_map['future']['predicted_mean'] = dominant_freq
        
        # Trend: compare present to past
        if temporal_map['past']['avg_entry'] > 0 and temporal_map['present']['avg_price'] > 0:
            change = (temporal_map['present']['avg_price'] - temporal_map['past']['avg_entry']) / temporal_map['past']['avg_entry']
            temporal_map['future']['predicted_trend'] = 'UP' if change > 0.05 else 'DOWN' if change < -0.05 else 'STABLE'
    
    # ─── 7. Render spectrum map (ASCII art) ─────────────────────────────────
    print("\n" + "🌊", "═"*70, "🌊")
    print("║   GLOBAL MARKET FLUID SPECTRUM MAP                             ║")
    print("🌊", "═"*70, "🌊")
    
    print(f"\n📊 TEMPORAL DIMENSIONS:")
    print(f"   PAST        — {temporal_map['past']['count']} historical entries  avg=${temporal_map['past']['avg_entry']:>8.2f}")
    print(f"   PRESENT     — {temporal_map['present']['count']} live positions  avg=${temporal_map['present']['avg_price']:>8.2f}  P&L=${temporal_map['present'].get('pnl',0):>+8.2f} ({temporal_map['present'].get('pnl_pct',0):>+6.2f}%)")
    print(f"   FUTURE      — predicted mean freq={temporal_map['future']['predicted_mean']:>8.2f} Hz  trend={temporal_map['future']['predicted_trend']}")
    
    print(f"\n🎼 HARMONIC STRUCTURE (FFT analysis):")
    if fft_result and fft_result['freqs']:
        for i, (freq, mag) in enumerate(fft_result['freqs'][:5], 1):
            bar_len = int(mag / (max([m for _, m in fft_result['freqs']], default=1) or 1) * 40)
            bar = '█' * bar_len
            print(f"   Harmonic {i}  {freq:>7.3f} Hz  {bar}  magnitude={mag:.2f}")
    else:
        print("   (FFT analysis unavailable)")
    
    print(f"\n🌍 MASTER WAVEFORM ({len(master_waveform)} nodes):")
    print("   Top 10 assets by frequency:")
    for i, (sym, hz) in enumerate(zip(symbol_order[:10], master_waveform[:10]), 1):
        data = live_prices.get(sym, {})
        price = data.get('price', 0)
        change = data.get('change_24h', 0)
        print(f"   {i:2d}. {sym:8} → {hz:>7.3f} Hz  price=${price:>10,.2f}  24h:{change:>+6.2f}%")
    
    print(f"\n💼 PORTFOLIO POSITIONS ({len(portfolio['positions'])} open):")
    for pos in portfolio['positions'][:10]:  # Top 10
        sym = pos['symbol']
        pnl = pos['pnl']
        pnl_pct = pos['pnl_pct']
        icon = "🟢" if pnl >= 0 else "🔴"
        print(f"   {icon} {sym:8}  entry=${pos['entry_price']:>10.4f}  live=${pos['current_price']:>10.4f}  "
              f"P&L=${pnl:>+10.4f} ({pnl_pct:>+7.2f}%)")
    
    print("\n" + "🌊", "═"*70, "🌊\n")
    
    # ─── 8. Conclusion ──────────────────────────────────────────────────────
    market_verdict = "RISE ↗️" if temporal_map['future']['predicted_trend'] == 'UP' else "FALL ↘️" if temporal_map['future']['predicted_trend'] == 'DOWN' else "STABLE ↔️"
    print(f"🔮 FLUID VERDICT:  Market trend = {market_verdict}")
    print(f"   The waveform speaks — listen to the frequencies.\n")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN - Run the Harmonic Live Stream
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def main():
    """Run the Harmonic Liquid Aluminium Field with live streaming."""
    print()
    print("🔩═══════════════════════════════════════════════════════════════════🔩")
    print("║   HARMONIC LIQUID ALUMINIUM FIELD - LIVE STREAM                  ║")
    print("║   'Like liquid metal dancing on frequencies in a measured sandbox'║")
    print("🔩═══════════════════════════════════════════════════════════════════🔩")
    print()
    
    # Initialize the field
    field = HarmonicLiquidAluminiumField(stream_interval_ms=100)
    
    # Initialize the kill chain adapter
    adapter = HarmonicKillChainAdapter(field)
    
    # Register a callback to print field state
    def on_snapshot(snapshot: FieldSnapshot):
        # Clear and print every 10 cycles
        if snapshot.cycle % 10 == 0:
            print("\033[2J\033[H")  # Clear screen
            print(field.render_ascii_field())
    
    field.on_snapshot(on_snapshot)
    
    # Start streaming
    field.start_streaming()
    
    print("🌊 Field streaming started. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            # Scan exchanges and update field
            adapter.scan_and_harmonize()
            
            # Wait before next scan
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🔩 Shutting down Harmonic Liquid Aluminium Field...")
        field.stop_streaming()
        print("✅ Field collapsed. Goodbye.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--global-fluid':
        # Run the global market fluid FFT spectrum mapper
        run_global_market_fluid()
    elif len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
AUREON HARMONIC LIQUID ALUMINIUM FIELD

Usage:
    python3 aureon_harmonic_liquid_aluminium.py              # Run live harmonic field stream
    python3 aureon_harmonic_liquid_aluminium.py --global-fluid  # Run global market fluid FFT
    python3 aureon_harmonic_liquid_aluminium.py --help          # Show this help
        """)
    else:
        # Default: run the live harmonic field
        main()
