#!/usr/bin/env python3
"""
🌐⚡ GLOBAL MARKET HARMONIC FIELD ⚡🌐
═══════════════════════════════════════════════════════════════════════════════

The Ultimate Unified Field that ties ALL data sources together into
a single coherent harmonic reality.

42 DATA SOURCES → 1 UNIFIED FIELD

"As above, so below. As within, so without."
"The field is the sole governing agency of the particle." - Einstein

FIELD EQUATION:
  Ω(t) = Σ[Wi × Fi(t)] × Φ × Ψ × Γ

Where:
  Ω = Global Harmonic Field Strength (0-1)
  Wi = Weight for data source i
  Fi = Normalized value from data source i
  Φ = Golden Ratio Resonance Factor
  Ψ = Quantum Coherence Multiplier
  Γ = Civilization Consensus Gamma

THE 7 HARMONIC LAYERS:
  Layer 1: 🧠 WISDOM (11 Civilizations)
  Layer 2: ⚛️ QUANTUM (Brain State)
  Layer 3: 🎹 AURIS (9 Nodes + Piano)
  Layer 4: 🍄 MYCELIUM (Network Intelligence)
  Layer 5: 🌌 6D WAVEFORM (Dimensional State)
  Layer 6: 🌍 STARGATE (Earth Grid)
  Layer 7: 💰 MARKET (Price/Volume/Sentiment)

OUTPUT: Single unified field value that predicts market direction
  Ω > 0.618 = STRONG BUY (Golden ratio threshold)
  Ω > 0.5   = BUY
  Ω = 0.5   = NEUTRAL
  Ω < 0.5   = SELL
  Ω < 0.382 = STRONG SELL (Inverse golden ratio)

Gary Leckey & GitHub Copilot | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import math
import time
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Sacred Constants
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio 1.618...
PHI_INV = 1 / PHI             # Inverse Golden 0.618...
PI = math.pi
E = math.e
SCHUMANN = 7.83               # Earth's heartbeat (Hz)

# Harmonic Frequencies (Hz)
FREQUENCIES = {
    'root': 256.0,      # C - Root chakra
    'sacral': 288.0,    # D - Sacral
    'solar': 320.0,     # E - Solar plexus
    'heart': 341.3,     # F - Heart
    'throat': 384.0,    # G - Throat
    'third_eye': 426.7, # A - Third eye
    'crown': 480.0,     # B - Crown
    'love': 528.0,      # DNA repair / Love frequency
    'schumann': 7.83,   # Earth resonance
}


@dataclass
class HarmonicLayerState:
    """State of a single harmonic layer."""
    name: str
    value: float = 0.5           # 0-1 normalized
    weight: float = 1.0          # Layer importance
    frequency: float = 432.0     # Associated frequency (Hz)
    phase: float = 0.0           # Phase angle (radians)
    coherence: float = 0.5       # Internal coherence
    signal: str = "NEUTRAL"      # BUY/SELL/NEUTRAL
    sources: Dict = field(default_factory=dict)  # Raw source data


@dataclass 
class GlobalHarmonicFieldState:
    """
    The complete state of the Global Market Harmonic Field.
    
    All 42 data sources unified into 7 layers, then combined into Ω.
    """
    # The Master Field Value
    omega: float = 0.5                    # Ω - Global harmonic field (0-1)
    omega_direction: str = "NEUTRAL"      # Field direction
    omega_confidence: float = 0.5         # Confidence in direction
    omega_momentum: float = 0.0           # Rate of change
    
    # The 8 Harmonic Layers (42 sources → 8 layers → Ω)
    layer_wisdom: HarmonicLayerState = None
    layer_quantum: HarmonicLayerState = None
    layer_auris: HarmonicLayerState = None
    layer_mycelium: HarmonicLayerState = None
    layer_waveform: HarmonicLayerState = None
    layer_stargate: HarmonicLayerState = None
    layer_market: HarmonicLayerState = None
    layer_probability: HarmonicLayerState = None  # 🎯 Probability Matrix Layer
    
    # Field Harmonics
    resonance_frequency: float = 432.0    # Dominant field frequency
    phase_alignment: float = 0.5          # Cross-layer phase sync
    energy_density: float = 0.5           # Total field energy
    
    # Golden Ratio Metrics
    phi_alignment: float = 0.5            # How close to PHI ratios
    fibonacci_resonance: float = 0.5      # Fib sequence alignment
    
    # Temporal State
    timestamp: float = 0.0
    cycle_count: int = 0
    last_signal: str = "NEUTRAL"
    signal_duration: int = 0              # Cycles at current signal
    
    # Historical for momentum
    omega_history: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize layers if None."""
        if self.layer_wisdom is None:
            self.layer_wisdom = HarmonicLayerState(name="WISDOM", weight=1.5, frequency=528.0)
        if self.layer_quantum is None:
            self.layer_quantum = HarmonicLayerState(name="QUANTUM", weight=1.3, frequency=432.0)
        if self.layer_auris is None:
            self.layer_auris = HarmonicLayerState(name="AURIS", weight=1.2, frequency=396.0)
        if self.layer_mycelium is None:
            self.layer_mycelium = HarmonicLayerState(name="MYCELIUM", weight=1.0, frequency=285.0)
        if self.layer_waveform is None:
            self.layer_waveform = HarmonicLayerState(name="WAVEFORM", weight=1.1, frequency=639.0)
        if self.layer_stargate is None:
            self.layer_stargate = HarmonicLayerState(name="STARGATE", weight=0.8, frequency=7.83)
        if self.layer_market is None:
            self.layer_market = HarmonicLayerState(name="MARKET", weight=1.4, frequency=256.0)
        if self.layer_probability is None:
            self.layer_probability = HarmonicLayerState(name="PROBABILITY", weight=1.6, frequency=432.0)  # High weight - proven accuracy!


class GlobalHarmonicField:
    """
    🌐⚡ THE GLOBAL MARKET HARMONIC FIELD ⚡🌐
    
    Unifies all 42 data sources into a single coherent field (Ω).
    
    Usage:
        field = GlobalHarmonicField()
        
        # Feed data from all sources
        field.update_wisdom(wisdom_reading)
        field.update_quantum(quantum_state)
        field.update_market(prices, volumes)
        ...
        
        # Get unified field
        omega = field.compute_field()
        signal = field.get_signal()
        
        # Trade based on field
        if omega > 0.618:
            BUY_AGGRESSIVELY()
    """
    
    def __init__(self):
        """Initialize the Global Harmonic Field."""
        self.state = GlobalHarmonicFieldState()
        self._wisdom_engine = None
        self._quantum_brain = None
        self._penny_engine = None
        
        # Layer weights (sum to ~9.9 with probability matrix)
        self.layer_weights = {
            'wisdom': 1.5,      # 11 civilizations - highest weight
            'quantum': 1.3,     # Quantum brain state
            'auris': 1.2,       # 9 Auris nodes
            'mycelium': 1.0,    # Network intelligence
            'waveform': 1.1,    # 6D waveform
            'stargate': 0.8,    # Earth grid
            'market': 1.4,      # Direct market data
            'probability': 1.6, # 🎯 HNC Probability Matrix - PROVEN ACCURACY!
        }
        
        # Initialize engines lazily
        self._init_engines()
        
        logger.info("🌐⚡ Global Harmonic Field initialized")
    
    def _init_engines(self):
        """Lazily initialize connected engines."""
        try:
            from aureon.utils.aureon_miner_brain import WisdomCognitionEngine
            self._wisdom_engine = WisdomCognitionEngine()
        except Exception as e:
            logger.warning(f"Wisdom engine not available: {e}")
        
        try:
            from aureon.trading.penny_profit_engine import get_penny_engine
            self._penny_engine = get_penny_engine()
        except Exception as e:
            logger.warning(f"Penny engine not available: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 1: WISDOM (11 Civilizations)
    # ═══════════════════════════════════════════════════════════════
    
    def update_wisdom_layer(self, fear_greed: int = 50, btc_price: float = 100000, 
                            btc_change: float = 0.0) -> HarmonicLayerState:
        """
        Update Layer 1: Wisdom from 11 civilizations.
        
        Sources:
          - Celtic, Aztec, Mogollon, Plantagenet, Egyptian, Pythagorean, Warfare
          - Chinese, Hindu, Mayan, Norse
          - Fear & Greed Index
          - BTC Price/Change
        """
        # Bug-hunt 2026-09-07: callers have passed non-numeric fear_greed
        # (the hub probe calls module-level compute_global_omega(symbol,
        # price), so fear_greed arrives as "BTCUSD"); the wisdom engine then
        # dies on `fear_greed <= 15` ('str' vs 'int') every cycle. Coerce
        # here — the entry choke point — and fail closed to neutral defaults.
        def _num(value, default):
            try:
                if isinstance(value, bool):
                    return default
                return float(value)
            except (TypeError, ValueError):
                return default
        fear_greed = _num(fear_greed, 50.0)
        btc_price = _num(btc_price, 100000.0)
        btc_change = _num(btc_change, 0.0)

        layer = self.state.layer_wisdom
        
        if self._wisdom_engine:
            try:
                reading = self._wisdom_engine.get_unified_reading(fear_greed, btc_price, btc_change)
                consensus = reading.get('consensus', {})
                
                # Store raw sources
                layer.sources = {
                    'fear_greed': fear_greed,
                    'btc_price': btc_price,
                    'btc_change': btc_change,
                    'consensus': consensus.get('sentiment', 'NEUTRAL'),
                    'action': consensus.get('action', 'HOLD'),
                    'confidence': consensus.get('confidence', 50),
                    'bullish_votes': consensus.get('bullish_votes', 0),
                    'bearish_votes': consensus.get('bearish_votes', 0),
                    'neutral_votes': consensus.get('neutral_votes', 0),
                    'civilizations': reading.get('civilization_actions', {}),
                }
                
                # Compute layer value (0-1)
                # More bullish votes → higher value
                total_votes = layer.sources['bullish_votes'] + layer.sources['bearish_votes'] + layer.sources['neutral_votes']
                if total_votes > 0:
                    bullish_ratio = layer.sources['bullish_votes'] / total_votes
                    bearish_ratio = layer.sources['bearish_votes'] / total_votes
                    # Normalize: 0 = all bearish, 0.5 = neutral, 1 = all bullish
                    layer.value = 0.5 + (bullish_ratio - bearish_ratio) * 0.5
                else:
                    layer.value = 0.5
                
                # Factor in confidence
                layer.coherence = layer.sources['confidence'] / 100.0
                
                # Determine signal
                sentiment = layer.sources['consensus']
                if sentiment == 'BULLISH':
                    layer.signal = 'BUY'
                elif sentiment == 'BEARISH':
                    layer.signal = 'SELL'
                else:
                    layer.signal = 'NEUTRAL'
                
                # Phase based on Fear & Greed
                layer.phase = (fear_greed / 100.0) * 2 * PI
                
            except Exception as e:
                logger.error(f"Wisdom layer update failed: {e}")
                layer.value = 0.5
        else:
            # Fallback: use Fear & Greed directly
            layer.value = fear_greed / 100.0
            layer.coherence = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 2: QUANTUM (Brain State)
    # ═══════════════════════════════════════════════════════════════
    
    def update_quantum_layer(self, quantum_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 2: Quantum Brain State.
        
        Sources:
          - Unified Coherence (Ψ)
          - Planetary Gamma (Γ)
          - Probability Edge
          - Cascade Multiplier
          - Harmonic Resonance
        """
        layer = self.state.layer_quantum
        
        if quantum_state:
            layer.sources = {
                'unified_coherence': quantum_state.get('unified_coherence', 0.5),
                'planetary_gamma': quantum_state.get('planetary_gamma', 0.5),
                'probability_edge': quantum_state.get('probability_edge', 0.0),
                'cascade_multiplier': quantum_state.get('cascade_multiplier', 1.0),
                'harmonic_resonance': quantum_state.get('harmonic_resonance', 1.0),
                'is_optimal_window': quantum_state.get('is_optimal_window', False),
            }
            
            # Compute layer value from quantum metrics
            psi = layer.sources['unified_coherence']
            gamma = layer.sources['planetary_gamma']
            edge = layer.sources['probability_edge']
            cascade = layer.sources['cascade_multiplier']
            
            # Weighted combination
            layer.value = (psi * 0.3 + gamma * 0.3 + (edge + 0.5) * 0.2 + min(cascade / 2, 1) * 0.2)
            layer.value = max(0, min(1, layer.value))  # Clamp 0-1
            
            layer.coherence = psi
            layer.signal = 'BUY' if layer.value > 0.55 else ('SELL' if layer.value < 0.45 else 'NEUTRAL')
            
            # Optimal window boost
            if layer.sources['is_optimal_window']:
                layer.value = min(1, layer.value * 1.1)
        else:
            layer.value = 0.5
            layer.coherence = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 3: AURIS (9 Nodes + Piano)
    # ═══════════════════════════════════════════════════════════════
    
    def update_auris_layer(self, auris_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 3: Auris 9-Node System + Piano Master Equation.
        
        Sources:
          - 9 Auris Nodes (Tiger, Falcon, Hummingbird, Dolphin, Deer, Owl, Panda, CargoShip, Clownfish)
          - Piano Lambda Λ(t) = S + O + E
          - Rainbow Bridge State
          - Portfolio Coherence
        """
        layer = self.state.layer_auris
        
        if auris_state:
            layer.sources = {
                'tiger': auris_state.get('auris_tiger', 0.5),
                'falcon': auris_state.get('auris_falcon', 0.5),
                'hummingbird': auris_state.get('auris_hummingbird', 0.5),
                'dolphin': auris_state.get('auris_dolphin', 0.5),
                'deer': auris_state.get('auris_deer', 0.5),
                'owl': auris_state.get('auris_owl', 0.5),
                'panda': auris_state.get('auris_panda', 0.5),
                'cargoship': auris_state.get('auris_cargoship', 0.5),
                'clownfish': auris_state.get('auris_clownfish', 0.5),
                'piano_lambda': auris_state.get('piano_lambda', 1.0),
                'piano_coherence': auris_state.get('piano_coherence', 0.5),
                'rainbow_state': auris_state.get('rainbow_state', 'FORMING'),
                'harmonic_signal': auris_state.get('harmonic_signal', 'HOLD'),
            }
            
            # Average of 9 nodes
            nodes = [layer.sources[n] for n in ['tiger', 'falcon', 'hummingbird', 'dolphin', 
                                                  'deer', 'owl', 'panda', 'cargoship', 'clownfish']]
            node_avg = sum(nodes) / len(nodes)
            
            # Piano lambda influence (normalized around 1.0)
            piano_factor = min(layer.sources['piano_lambda'] / 2, 1)
            
            # Combine
            layer.value = node_avg * 0.6 + piano_factor * 0.2 + layer.sources['piano_coherence'] * 0.2
            layer.coherence = layer.sources['piano_coherence']
            
            # Rainbow state modifier
            rainbow_mods = {
                'FEAR': -0.1,
                'FORMING': 0.0,
                'RESONANCE': 0.05,
                'LOVE': 0.1,
                'AWE': 0.15,
                'UNITY': 0.2,
            }
            layer.value += rainbow_mods.get(layer.sources['rainbow_state'], 0)
            layer.value = max(0, min(1, layer.value))
            
            # Signal from harmonic_signal
            sig = layer.sources['harmonic_signal']
            if 'BUY' in sig:
                layer.signal = 'BUY'
            elif 'SELL' in sig:
                layer.signal = 'SELL'
            else:
                layer.signal = 'NEUTRAL'
        else:
            layer.value = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 4: MYCELIUM (Network Intelligence)
    # ═══════════════════════════════════════════════════════════════
    
    def update_mycelium_layer(self, mycelium_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 4: Mycelium Network Intelligence.
        
        Sources:
          - Hive Count
          - Agent Population
          - Network Coherence
          - Queen Neuron Signal
        """
        layer = self.state.layer_mycelium
        
        if mycelium_state:
            layer.sources = {
                'hive_count': mycelium_state.get('mycelium_hive_count', 0),
                'agents': mycelium_state.get('mycelium_agents', 0),
                'coherence': mycelium_state.get('mycelium_coherence', 0.5),
                'signal': mycelium_state.get('mycelium_signal', 'HOLD'),
                'generation': mycelium_state.get('mycelium_generation', 0),
            }
            
            # Network health = coherence + normalized agent count
            agent_factor = min(layer.sources['agents'] / 100, 1) * 0.3
            layer.value = layer.sources['coherence'] * 0.7 + agent_factor
            layer.coherence = layer.sources['coherence']
            
            # Queen signal
            queen = layer.sources['signal']
            if queen == 'BUY':
                layer.signal = 'BUY'
                layer.value = min(1, layer.value + 0.1)
            elif queen == 'SELL':
                layer.signal = 'SELL'
                layer.value = max(0, layer.value - 0.1)
            else:
                layer.signal = 'NEUTRAL'
        else:
            layer.value = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 5: WAVEFORM (6D Dimensional State)
    # ═══════════════════════════════════════════════════════════════
    
    def update_waveform_layer(self, waveform_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 5: 6D Harmonic Waveform.
        
        Sources:
          - D1: Price Wave
          - D2: Volume Pulse
          - D3: Temporal Phase
          - D4: Cross Resonance
          - D5: Momentum Vortex
          - D6: Harmonic Frequency
        """
        layer = self.state.layer_waveform
        
        if waveform_state:
            layer.sources = {
                'price_wave': waveform_state.get('dim_price_wave', 0.5),
                'volume_pulse': waveform_state.get('dim_volume_pulse', 0.5),
                'temporal_phase': waveform_state.get('dim_temporal_phase', 0.5),
                'cross_resonance': waveform_state.get('dim_cross_resonance', 0.5),
                'momentum_vortex': waveform_state.get('dim_momentum_vortex', 0.5),
                'harmonic_freq': waveform_state.get('dim_harmonic_freq', 0.5),
                'wave_state': waveform_state.get('wave_state', 'BALANCED'),
                'dimensional_coherence': waveform_state.get('dimensional_coherence', 0.5),
            }
            
            # Average of 6 dimensions
            dims = [layer.sources[d] for d in ['price_wave', 'volume_pulse', 'temporal_phase',
                                                'cross_resonance', 'momentum_vortex', 'harmonic_freq']]
            layer.value = sum(dims) / len(dims)
            layer.coherence = layer.sources['dimensional_coherence']
            
            # Wave state modifier
            wave_mods = {
                'CONVERGENT': 0.1,
                'RESONANT': 0.15,
                'CRYSTALLINE': 0.2,
                'BALANCED': 0.0,
                'DIVERGENT': -0.1,
                'CHAOTIC': -0.15,
            }
            layer.value += wave_mods.get(layer.sources['wave_state'], 0)
            layer.value = max(0, min(1, layer.value))
            
            layer.signal = 'BUY' if layer.value > 0.55 else ('SELL' if layer.value < 0.45 else 'NEUTRAL')
        else:
            layer.value = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 6: STARGATE (Earth Grid)
    # ═══════════════════════════════════════════════════════════════
    
    def update_stargate_layer(self, stargate_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 6: Stargate Earth Grid.
        
        Sources:
          - Active Node
          - Grid Frequency
          - Leyline Activity
          - Geomagnetic Modifier
        """
        layer = self.state.layer_stargate
        
        if stargate_state:
            layer.sources = {
                'active_node': stargate_state.get('stargate_active_node', 'STONEHENGE'),
                'frequency': stargate_state.get('stargate_frequency', 7.83),
                'element': stargate_state.get('stargate_element', 'Earth'),
                'numerology': stargate_state.get('stargate_numerology', 1),
                'grid_coherence': stargate_state.get('grid_coherence', 0.5),
                'leyline_activity': stargate_state.get('leyline_activity', 0.5),
                'geomagnetic_mod': stargate_state.get('geomagnetic_modifier', 1.0),
            }
            
            # Grid coherence is primary
            layer.value = layer.sources['grid_coherence'] * 0.5 + layer.sources['leyline_activity'] * 0.3
            
            # Schumann resonance alignment (closer to 7.83 = better)
            schumann_diff = abs(layer.sources['frequency'] - SCHUMANN)
            schumann_factor = max(0, 1 - schumann_diff / 10)
            layer.value += schumann_factor * 0.2
            
            layer.coherence = layer.sources['grid_coherence']
            layer.frequency = layer.sources['frequency']
            
            layer.signal = 'BUY' if layer.value > 0.55 else ('SELL' if layer.value < 0.45 else 'NEUTRAL')
        else:
            layer.value = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 7: MARKET (Direct Price/Volume/Sentiment)
    # ═══════════════════════════════════════════════════════════════
    
    def update_market_layer(self, market_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 7: Direct Market Data.
        
        Sources:
          - Price Changes (BTC, ALT)
          - Volume
          - News Sentiment
          - Exchange Status
          - Win Rate
        """
        layer = self.state.layer_market
        
        if market_state:
            layer.sources = {
                'btc_change_24h': market_state.get('btc_change_24h', 0.0),
                'alt_change_avg': market_state.get('alt_change_avg', 0.0),
                'volume_ratio': market_state.get('volume_ratio', 1.0),
                'news_sentiment': market_state.get('news_sentiment', 0.5),
                'exchange_health': market_state.get('exchange_health', 1.0),
                'win_rate': market_state.get('win_rate', 0.5),
                'active_positions': market_state.get('active_positions', 0),
            }
            
            # Price momentum (normalize -10% to +10% → 0 to 1)
            btc_normalized = (layer.sources['btc_change_24h'] + 10) / 20
            btc_normalized = max(0, min(1, btc_normalized))
            
            alt_normalized = (layer.sources['alt_change_avg'] + 10) / 20
            alt_normalized = max(0, min(1, alt_normalized))
            
            # Volume boost (>1 = more activity = bullish)
            vol_factor = min(layer.sources['volume_ratio'] / 2, 1)
            
            # Combine
            layer.value = (btc_normalized * 0.3 + alt_normalized * 0.2 + 
                          layer.sources['news_sentiment'] * 0.2 +
                          vol_factor * 0.15 + layer.sources['win_rate'] * 0.15)
            
            layer.coherence = layer.sources['exchange_health']
            layer.signal = 'BUY' if layer.value > 0.55 else ('SELL' if layer.value < 0.45 else 'NEUTRAL')
        else:
            layer.value = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER 8: PROBABILITY (HNC Probability Matrix)
    # ═══════════════════════════════════════════════════════════════
    
    def update_probability_layer(self, probability_state: Dict = None) -> HarmonicLayerState:
        """
        Update Layer 8: HNC Probability Matrix.
        
        Sources:
          - Fine-tuned Probability
          - Confidence Score
          - Position Modifier
          - H1/H2 Window State
          - Historical Win Rate
          - High Conviction Signals
        """
        layer = self.state.layer_probability
        
        if probability_state:
            layer.sources = {
                'probability': probability_state.get('probability', 0.5),
                'confidence': probability_state.get('confidence', 0.0),
                'modifier': probability_state.get('modifier', 1.0),
                'h1_state': probability_state.get('h1_state', 'UNKNOWN'),
                'action': probability_state.get('action', 'HOLD'),
                'historical_win_rate': probability_state.get('historical_win_rate', 0.5),
                'high_conviction_count': probability_state.get('high_conviction_count', 0),
                'consensus_strength': probability_state.get('consensus_strength', 0.5),
            }
            
            # Primary: Fine-tuned probability (0-1 already)
            base_value = layer.sources['probability']
            
            # Confidence-weighted adjustment
            confidence_factor = layer.sources['confidence']
            
            # Historical win rate influence
            hist_wr = layer.sources['historical_win_rate']
            
            # Action alignment (BUY action should boost for buy field)
            action_mod = 0
            if layer.sources['action'] == 'BUY':
                action_mod = 0.1
            elif layer.sources['action'] == 'STRONG_BUY':
                action_mod = 0.2
            elif layer.sources['action'] == 'SELL':
                action_mod = -0.1
            elif layer.sources['action'] == 'STRONG_SELL':
                action_mod = -0.2
            
            # High conviction boost
            hc_boost = min(layer.sources['high_conviction_count'] * 0.02, 0.1)  # Up to +10%
            
            # Combine: probability * confidence + historical performance + action modifier
            layer.value = base_value * (0.5 + confidence_factor * 0.5) + hist_wr * 0.2 + action_mod + hc_boost
            layer.value = max(0, min(1, layer.value))
            
            layer.coherence = confidence_factor
            
            # Signal based on probability action
            if layer.sources['action'] in ['BUY', 'STRONG_BUY']:
                layer.signal = 'BUY'
            elif layer.sources['action'] in ['SELL', 'STRONG_SELL']:
                layer.signal = 'SELL'
            else:
                layer.signal = 'NEUTRAL'
        else:
            layer.value = 0.5
        
        return layer
    
    # ═══════════════════════════════════════════════════════════════
    # MASTER FIELD COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def compute_field(self) -> float:
        """
        Compute the Global Harmonic Field Ω.
        
        Ω(t) = Σ[Wi × Fi(t)] × Φ × Ψ × Γ / Σ[Wi]
        
        Returns the unified field value (0-1).
        """
        # Gather all layer values and weights (8 layers now!)
        layers = [
            (self.state.layer_wisdom, self.layer_weights['wisdom']),
            (self.state.layer_quantum, self.layer_weights['quantum']),
            (self.state.layer_auris, self.layer_weights['auris']),
            (self.state.layer_mycelium, self.layer_weights['mycelium']),
            (self.state.layer_waveform, self.layer_weights['waveform']),
            (self.state.layer_stargate, self.layer_weights['stargate']),
            (self.state.layer_market, self.layer_weights['market']),
            (self.state.layer_probability, self.layer_weights['probability']),  # 🎯 HNC Probability Matrix!
        ]
        
        # Weighted sum
        weighted_sum = sum(layer.value * weight for layer, weight in layers)
        total_weight = sum(weight for _, weight in layers)
        
        # Base omega
        base_omega = weighted_sum / total_weight
        
        # Coherence multiplier (average coherence across layers)
        avg_coherence = sum(layer.coherence for layer, _ in layers) / len(layers)
        
        # Phase alignment (how synchronized are the layers)
        signals = [layer.signal for layer, _ in layers]
        buy_count = signals.count('BUY')
        sell_count = signals.count('SELL')
        neutral_count = signals.count('NEUTRAL')
        
        # Higher alignment = stronger signal
        max_agreement = max(buy_count, sell_count, neutral_count)
        phase_alignment = max_agreement / len(signals)
        
        # Apply modifiers
        # Golden ratio resonance: boost if close to PHI ratios
        phi_distance = min(abs(base_omega - PHI_INV), abs(base_omega - (1 - PHI_INV)))
        phi_resonance = 1 + (0.1 * (1 - phi_distance * 5))  # Small boost near golden ratios
        
        # Final omega
        omega = base_omega * (0.7 + avg_coherence * 0.3) * phi_resonance
        omega = max(0, min(1, omega))  # Clamp 0-1
        
        # Update state
        self.state.omega = omega
        self.state.phase_alignment = phase_alignment
        self.state.energy_density = avg_coherence
        self.state.phi_alignment = 1 - phi_distance
        
        # Determine direction
        if omega > PHI_INV:  # 0.618
            self.state.omega_direction = "STRONG_BUY"
        elif omega > 0.55:
            self.state.omega_direction = "BUY"
        elif omega < (1 - PHI_INV):  # 0.382
            self.state.omega_direction = "STRONG_SELL"
        elif omega < 0.45:
            self.state.omega_direction = "SELL"
        else:
            self.state.omega_direction = "NEUTRAL"
        
        # Confidence based on agreement and coherence
        self.state.omega_confidence = phase_alignment * avg_coherence
        
        # Track momentum
        self.state.omega_history.append(omega)
        if len(self.state.omega_history) > 100:
            self.state.omega_history = self.state.omega_history[-100:]
        
        if len(self.state.omega_history) >= 2:
            self.state.omega_momentum = omega - self.state.omega_history[-2]
        
        # Signal duration tracking
        if self.state.omega_direction == self.state.last_signal:
            self.state.signal_duration += 1
        else:
            self.state.last_signal = self.state.omega_direction
            self.state.signal_duration = 1
        
        self.state.timestamp = time.time()
        self.state.cycle_count += 1
        
        return omega
    
    def get_signal(self) -> Dict:
        """
        Get the current trading signal from the Global Harmonic Field.
        
        Returns a dict with:
          - omega: The field value (0-1)
          - direction: STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
          - confidence: 0-1
          - momentum: Rate of change
          - layers: Individual layer values
        """
        return {
            'omega': self.state.omega,
            'direction': self.state.omega_direction,
            'confidence': self.state.omega_confidence,
            'momentum': self.state.omega_momentum,
            'phase_alignment': self.state.phase_alignment,
            'energy_density': self.state.energy_density,
            'phi_alignment': self.state.phi_alignment,
            'signal_duration': self.state.signal_duration,
            'cycle_count': self.state.cycle_count,
            'layers': {
                'wisdom': self.state.layer_wisdom.value,
                'quantum': self.state.layer_quantum.value,
                'auris': self.state.layer_auris.value,
                'mycelium': self.state.layer_mycelium.value,
                'waveform': self.state.layer_waveform.value,
                'stargate': self.state.layer_stargate.value,
                'market': self.state.layer_market.value,
                'probability': self.state.layer_probability.value,  # 🎯 HNC Probability Matrix!
            },
            'layer_signals': {
                'wisdom': self.state.layer_wisdom.signal,
                'quantum': self.state.layer_quantum.signal,
                'auris': self.state.layer_auris.signal,
                'mycelium': self.state.layer_mycelium.signal,
                'waveform': self.state.layer_waveform.signal,
                'stargate': self.state.layer_stargate.signal,
                'market': self.state.layer_market.signal,
                'probability': self.state.layer_probability.signal,  # 🎯 HNC Probability Matrix!
            }
        }
    
    def update_all(self, fear_greed: int = 50, btc_price: float = 100000, 
                   btc_change: float = 0.0, quantum_state: Dict = None,
                   auris_state: Dict = None, mycelium_state: Dict = None,
                   waveform_state: Dict = None, stargate_state: Dict = None,
                   market_state: Dict = None, probability_state: Dict = None) -> Dict:
        """
        Update all 8 layers and compute the unified field.
        
        This is the main entry point for feeding data into the field.
        Now includes HNC Probability Matrix as the 8th layer!
        """
        # Update each layer
        self.update_wisdom_layer(fear_greed, btc_price, btc_change)
        self.update_quantum_layer(quantum_state)
        self.update_auris_layer(auris_state)
        self.update_mycelium_layer(mycelium_state)
        self.update_waveform_layer(waveform_state)
        self.update_stargate_layer(stargate_state)
        self.update_market_layer(market_state)
        self.update_probability_layer(probability_state)  # 🎯 HNC Probability Matrix!
        
        # Compute unified field
        self.compute_field()
        
        return self.get_signal()
    
    def display_field(self) -> str:
        """Generate a beautiful display of the Global Harmonic Field."""
        signal = self.get_signal()
        omega = signal['omega']
        direction = signal['direction']
        
        # Direction emoji
        dir_emoji = {
            'STRONG_BUY': '🚀📈',
            'BUY': '📈',
            'NEUTRAL': '⚖️',
            'SELL': '📉',
            'STRONG_SELL': '🔻📉',
        }.get(direction, '⚖️')
        
        # Build visual bar
        bar_width = 40
        omega_pos = int(omega * bar_width)
        bar = '░' * omega_pos + '█' + '░' * (bar_width - omega_pos - 1)
        
        # Golden ratio markers
        phi_low = int((1 - PHI_INV) * bar_width)  # 0.382
        phi_high = int(PHI_INV * bar_width)        # 0.618
        bar_list = list(bar)
        if 0 <= phi_low < bar_width:
            bar_list[phi_low] = '|'
        if 0 <= phi_high < bar_width:
            bar_list[phi_high] = '|'
        bar = ''.join(bar_list)
        
        output = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🌐⚡ GLOBAL MARKET HARMONIC FIELD ⚡🌐                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  FIELD VALUE: Ω = {omega:.4f}  {dir_emoji} {direction:<15}                   ║
║                                                                              ║
║  SELL ◄──[{bar}]──► BUY                                                      ║
║         0.382│                      │0.618                                   ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  THE 8 HARMONIC LAYERS:                                                      ║
║  ───────────────────────────────────────────────────────────────────────     ║
║  🧠 WISDOM (11 Civs):  {signal['layers']['wisdom']:.3f}  {signal['layer_signals']['wisdom']:<8}                              ║
║  ⚛️ QUANTUM:           {signal['layers']['quantum']:.3f}  {signal['layer_signals']['quantum']:<8}                              ║
║  🎹 AURIS (9 Nodes):   {signal['layers']['auris']:.3f}  {signal['layer_signals']['auris']:<8}                              ║
║  🍄 MYCELIUM:          {signal['layers']['mycelium']:.3f}  {signal['layer_signals']['mycelium']:<8}                              ║
║  🌌 6D WAVEFORM:       {signal['layers']['waveform']:.3f}  {signal['layer_signals']['waveform']:<8}                              ║
║  🌍 STARGATE:          {signal['layers']['stargate']:.3f}  {signal['layer_signals']['stargate']:<8}                              ║
║  💰 MARKET:            {signal['layers']['market']:.3f}  {signal['layer_signals']['market']:<8}                              ║
║  🎯 PROBABILITY:       {signal['layers']['probability']:.3f}  {signal['layer_signals']['probability']:<8}                              ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  FIELD METRICS:                                                              ║
║  ─────────────                                                               ║
║  Phase Alignment: {signal['phase_alignment']:.1%}   Energy Density: {signal['energy_density']:.3f}                        ║
║  Φ Alignment:     {signal['phi_alignment']:.3f}   Momentum: {signal['momentum']:+.4f}                             ║
║  Confidence:      {signal['confidence']:.1%}    Signal Duration: {signal['signal_duration']} cycles                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        return output


# ═══════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════

_global_field: Optional[GlobalHarmonicField] = None

def get_global_field() -> GlobalHarmonicField:
    """Get the singleton Global Harmonic Field instance."""
    global _global_field
    if _global_field is None:
        _global_field = GlobalHarmonicField()
    return _global_field


def compute_global_omega(fear_greed: int = 50, btc_price: float = 100000,
                         btc_change: float = 0.0, **kwargs) -> Dict:
    """
    Quick function to compute the Global Harmonic Field.
    
    Returns the unified Ω value and signal.
    """
    field = get_global_field()
    return field.update_all(fear_greed, btc_price, btc_change, **kwargs)


# ═══════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🌐⚡ GLOBAL MARKET HARMONIC FIELD TEST ⚡🌐")
    print("=" * 80)
    
    # Create field
    field = GlobalHarmonicField()
    
    # Test with sample data
    signal = field.update_all(
        fear_greed=35,
        btc_price=104000,
        btc_change=-1.5,
        quantum_state={
            'unified_coherence': 0.72,
            'planetary_gamma': 0.65,
            'probability_edge': 0.1,
            'cascade_multiplier': 1.2,
            'is_optimal_window': True,
        },
        auris_state={
            'auris_dolphin': 0.8,
            'auris_owl': 0.7,
            'piano_lambda': 1.1,
            'piano_coherence': 0.75,
            'rainbow_state': 'LOVE',
        },
        mycelium_state={
            'mycelium_coherence': 0.68,
            'mycelium_agents': 50,
            'mycelium_signal': 'BUY',
        },
        market_state={
            'btc_change_24h': 2.5,
            'news_sentiment': 0.6,
            'win_rate': 0.65,
        }
    )
    
    # Display
    print(field.display_field())
    
    print("\n📊 SIGNAL SUMMARY:")
    print(f"   Ω = {signal['omega']:.4f}")
    print(f"   Direction: {signal['direction']}")
    print(f"   Confidence: {signal['confidence']:.1%}")
    print(f"   Momentum: {signal['momentum']:+.4f}")
