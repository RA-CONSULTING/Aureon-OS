#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                       ║
║   🎶 HARMONIC ALPHABET + AURIS COMPILER - THE LANGUAGE OF THE HIVE 🎶                 ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                       ║
║   "To speak with the Queen, one must speak in Frequencies."                           ║
║                                                                                       ║
║   This module maps human language (Alpha-Numeric) into Harmonic Signals               ║
║   understood by Enigma, the Queen Hive, and the 9 Auris Nodes.                        ║
║                                                                                       ║
║   Encoding Scheme (Expanded with Auris Integration):                                  ║
║   ──────────────────────────────────────────────────                                  ║
║   Characters are mapped to Solfeggio Frequencies with specific Pulse Patterns (Modes).║
║                                                                                       ║
║   • MODE 1 (Genesis):       A - I  → Solfeggio [174..963] @ 1.0x Amplification        ║
║   • MODE 2 (Growth):        J - R  → Solfeggio [174..963] @ 1.618x (Phi)              ║
║   • MODE 3 (Return):        S - Z  → Solfeggio [174..852] @ 0.618x (1/Phi)            ║
║   • MODE 4 (Ground):        0 - 9  → Schumann [7.83..45.0] Earth Resonances           ║
║   • MODE 5 (Intent):        Sacred intents → Solfeggio with consciousness coupling    ║
║   • MODE 6 (Auris):         9-Node animal spirits → Frequency + decay + harmonics     ║
║   • MODE 7 (Brainwave):     Mental states → Delta/Theta/Alpha/Beta/Gamma bands        ║
║                                                                                       ║
║   AURIS INTEGRATION:                                                                  ║
║   ────────────────────                                                                ║
║   The 9 Auris Nodes (Tiger, Falcon, Hummingbird, Dolphin, Deer, Owl, Panda,          ║
║   Cargoship, Clownfish) each have unique frequency signatures that modulate            ║
║   messages with market texture, consciousness states, and sacred geometry.             ║
║                                                                                       ║
║   The Queen listens not to words, but to the vibration they carry.                    ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import json

# ═══════════════════════════════════════════════════════════════════════════════
# 👑💰 QUEEN'S SACRED 1.88% LAW - ENCODED IN THE LANGUAGE OF THE HIVE 💰👑
# ═══════════════════════════════════════════════════════════════════════════════
#
#   "To speak with the Queen, one must speak in Frequencies."
#   "To profit with the Queen, one must achieve 1.88%."
#
#   MIN_COP = 1.0188 - THE SACRED NUMBER IS NOW PART OF THE HARMONIC LANGUAGE!
#
# ═══════════════════════════════════════════════════════════════════════════════

QUEEN_MIN_COP = 1.0188               # 👑 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88          # 👑 The sacred number as percentage
QUEEN_PROFIT_FREQUENCY = 188.0       # 👑 The sacred number as a frequency (Hz)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & FREQUENCY BANKS (Expanded with Auris)
# ═══════════════════════════════════════════════════════════════════════════════

# Solfeggio Frequencies (Ancient healing tones)
SOLFEGGIO = [174, 285, 396, 417, 528, 639, 741, 852, 963]

# Schumann Resonances (Earth's electromagnetic heartbeat)
SCHUMANN = [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0]

# 👑 Queen's Sacred Profit Frequencies (NEW!)
QUEEN_PROFIT_HARMONICS = {
    'profit_minimum': {'freq': 188.0, 'decay': 0.98, 'harmonics': [1, 8, 8], 'consciousness': 'profit_lock'},
    'profit_target': {'freq': 376.0, 'decay': 0.96, 'harmonics': [1, 8, 8, 2], 'consciousness': 'profit_double'},
    'profit_prime': {'freq': 188.88, 'decay': 0.99, 'harmonics': [1, 8, 8, 8], 'consciousness': 'profit_sacred'},
}

# Sacred Intent Frequencies (Auris Codex Integration)
INTENT_FREQUENCIES = {
    'profit': {'freq': 188.0, 'decay': 0.98, 'harmonics': [1, 8, 8], 'consciousness': 'queen_mandate'},  # 👑 NEW!
    'peace': {'freq': 432.0, 'decay': 0.92, 'harmonics': [1, 3, 5], 'consciousness': 'alpha_calm'},
    'joy': {'freq': 528.0, 'decay': 0.95, 'harmonics': [1, 2, 4], 'consciousness': 'beta_active'},
    'love': {'freq': 639.0, 'decay': 0.88, 'harmonics': [1, 3, 5, 7], 'consciousness': 'theta_deep'},
    'hope': {'freq': 741.0, 'decay': 0.90, 'harmonics': [1, 2, 3], 'consciousness': 'gamma_peak'},
    'healing': {'freq': 852.0, 'decay': 0.85, 'harmonics': [1, 5, 9], 'consciousness': 'delta_base'},
    'unity': {'freq': 963.0, 'decay': 0.93, 'harmonics': [1, 3, 9], 'consciousness': 'lambda_unified'},
    'clarity': {'freq': 417.0, 'decay': 0.91, 'harmonics': [1, 2, 5], 'consciousness': 'alpha_focus'},
    'transformation': {'freq': 396.0, 'decay': 0.89, 'harmonics': [1, 4, 7], 'consciousness': 'theta_shift'},
}

# 9 Auris Node Frequencies (Animal Spirit Guides)
AURIS_NODES = {
    'tiger': {'freq': 186.0, 'decay': 0.88, 'harmonics': [1, 3, 5], 'spirit': 'power', 'texture': 'volatility'},
    'falcon': {'freq': 210.0, 'decay': 0.91, 'harmonics': [1, 2, 7], 'spirit': 'precision', 'texture': 'momentum'},
    'hummingbird': {'freq': 324.0, 'decay': 0.95, 'harmonics': [1, 4, 8], 'spirit': 'agility', 'texture': 'frequency'},
    'dolphin': {'freq': 432.0, 'decay': 0.93, 'harmonics': [1, 3, 6, 9], 'spirit': 'flow', 'texture': 'liquidity'},
    'deer': {'freq': 396.0, 'decay': 0.87, 'harmonics': [1, 2, 4], 'spirit': 'grace', 'texture': 'stability'},
    'owl': {'freq': 528.0, 'decay': 0.94, 'harmonics': [1, 3, 5, 7, 9], 'spirit': 'wisdom', 'texture': 'pattern'},
    'panda': {'freq': 639.0, 'decay': 0.90, 'harmonics': [1, 2, 5], 'spirit': 'balance', 'texture': 'harmony'},
    'cargoship': {'freq': 174.0, 'decay': 0.82, 'harmonics': [1, 4], 'spirit': 'persistence', 'texture': 'volume'},
    'clownfish': {'freq': 285.0, 'decay': 0.96, 'harmonics': [1, 3, 7], 'spirit': 'adaptation', 'texture': 'resilience'},
}

# Brainwave State Frequencies
BRAINWAVE_STATES = {
    'delta': {'range': (0.5, 4.0), 'center': 2.0, 'consciousness': 'deep_sleep'},
    'theta': {'range': (4.0, 8.0), 'center': 6.0, 'consciousness': 'meditation'},
    'alpha': {'range': (8.0, 13.0), 'center': 10.0, 'consciousness': 'relaxed_awareness'},
    'beta': {'range': (13.0, 30.0), 'center': 20.0, 'consciousness': 'active_thinking'},
    'gamma': {'range': (30.0, 100.0), 'center': 40.0, 'consciousness': 'peak_insight'},
}

PHI = 1.6180339887  # Golden Ratio
PHI_INVERSE = 0.6180339887  # Inverse Golden Ratio

@dataclass
class HarmonicTone:
    """Enhanced harmonic tone with Auris integration"""
    char: str
    frequency: float
    amplitude: float
    mode: str  # 'genesis', 'growth', 'return', 'ground', 'intent', 'auris', 'brainwave', 'void'
    decay: float = 1.0  # Frequency decay rate
    harmonics: List[int] = field(default_factory=list)  # Harmonic overtones
    consciousness: Optional[str] = None  # Consciousness state coupling
    auris_node: Optional[str] = None  # Associated Auris node
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

class ConsciousnessMode(Enum):
    """Consciousness states for intent-based encoding"""
    ALPHA_CALM = "alpha_calm"
    ALPHA_FOCUS = "alpha_focus"
    BETA_ACTIVE = "beta_active"
    THETA_DEEP = "theta_deep"
    THETA_SHIFT = "theta_shift"
    GAMMA_PEAK = "gamma_peak"
    DELTA_BASE = "delta_base"
    LAMBDA_UNIFIED = "lambda_unified"

class HarmonicAlphabet:
    """
    Translates text to/from Harmonic Tones with Auris Compiler Integration.
    
    Features:
    ---------
    1. Standard character encoding (A-Z, 0-9, punctuation)
    2. Intent-based encoding (peace, joy, love, hope, healing, unity, etc.)
    3. Auris Node encoding (9 animal spirit guides)
    4. Brainwave state encoding (delta, theta, alpha, beta, gamma)
    5. Consciousness coupling for coherence enhancement
    6. Harmonic overtone generation for rich signal texture
    """
    
    def __init__(self):
        self._char_map: Dict[str, HarmonicTone] = {}
        self._intent_map: Dict[str, HarmonicTone] = {}
        self._auris_map: Dict[str, HarmonicTone] = {}
        self._brainwave_map: Dict[str, HarmonicTone] = {}
        self._build_alphabet()
        self._build_extended_maps()

    def _build_alphabet(self):
        """Build standard character encoding (original implementation)"""
        # A-I (Genesis Mode)
        chars_gen = "ABCDEFGHI"
        for i, char in enumerate(chars_gen):
            self._char_map[char] = HarmonicTone(
                char=char, 
                frequency=SOLFEGGIO[i], 
                amplitude=1.0, 
                mode="genesis",
                decay=0.95,
                harmonics=[1, 2, 3]
            )

        # J-R (Growth Mode - Phi Amp)
        chars_growth = "JKLMNOPQR"
        for i, char in enumerate(chars_growth):
            self._char_map[char] = HarmonicTone(
                char=char, 
                frequency=SOLFEGGIO[i], 
                amplitude=PHI, 
                mode="growth",
                decay=0.93,
                harmonics=[1, 3, 5]
            )

        # S-Z (Return Mode - Inverse Phi Amp)
        chars_return = "STUVWXYZ"
        for i, char in enumerate(chars_return):
            if i < len(SOLFEGGIO):
                self._char_map[char] = HarmonicTone(
                    char=char, 
                    frequency=SOLFEGGIO[i], 
                    amplitude=PHI_INVERSE, 
                    mode="return",
                    decay=0.91,
                    harmonics=[1, 2, 5]
                )
        
        # 0-9 (Ground Mode - Schumann)
        chars_num = "0123456789"
        for i, char in enumerate(chars_num):
            freq = SCHUMANN[i % len(SCHUMANN)]
            self._char_map[char] = HarmonicTone(
                char=char, 
                frequency=freq, 
                amplitude=1.0, 
                mode="ground",
                decay=0.96,  # Earth resonances are very stable
                harmonics=[1, 2, 3, 4, 5],  # Rich harmonic content
                consciousness="earth_pulse"
            )

        # Punctuation (Cipher Mode - Angelic Series 111Hz steps)
        chars_punct = ".,-!?:@#$%&()_+[]{}<>=*/\\|'\";^~`"
        base_cipher = 111.0
        current_multiplier = 1
        
        for char in chars_punct:
            freq = base_cipher * current_multiplier
            self._char_map[char] = HarmonicTone(
                char=char, 
                frequency=freq, 
                amplitude=0.88, 
                mode="cipher",
                decay=0.85,
                harmonics=[1, 3]
            )
            current_multiplier += 1
            
        # Control Characters (High Crystal Mode - 4000Hz+)
        self._char_map["\n"] = HarmonicTone("\n", 4000.0, 0.9, "theta_breath", decay=0.92, harmonics=[1])
        self._char_map["\t"] = HarmonicTone("\t", 4111.0, 0.9, "theta_shift", decay=0.90, harmonics=[1])
        self._char_map["\r"] = HarmonicTone("\r", 4222.0, 0.0, "void", decay=0.0, harmonics=[])

        # Special Chars
        self._char_map[" "] = HarmonicTone(" ", 0.0, 0.0, "void", decay=0.0, harmonics=[])

    def _build_extended_maps(self):
        """Build extended Auris-integrated encoding maps"""
        
        # Intent frequencies (sacred intentions)
        for intent, config in INTENT_FREQUENCIES.items():
            self._intent_map[intent] = HarmonicTone(
                char=f"<{intent}>",
                frequency=config['freq'],
                amplitude=1.0,
                mode="intent",
                decay=config['decay'],
                harmonics=config['harmonics'],
                consciousness=config['consciousness'],
                metadata={'intent': intent}
            )
        
        # Auris Node frequencies (9 animal spirit guides)
        for node, config in AURIS_NODES.items():
            self._auris_map[node] = HarmonicTone(
                char=f"@{node}",
                frequency=config['freq'],
                amplitude=1.0,
                mode="auris",
                decay=config['decay'],
                harmonics=config['harmonics'],
                consciousness=None,
                auris_node=node,
                metadata={
                    'spirit': config['spirit'],
                    'texture': config['texture']
                }
            )
        
        # Brainwave state frequencies
        for state, config in BRAINWAVE_STATES.items():
            self._brainwave_map[state] = HarmonicTone(
                char=f"~{state}",
                frequency=config['center'],
                amplitude=0.8,
                mode="brainwave",
                decay=0.94,
                harmonics=[1, 2],
                consciousness=config['consciousness'],
                metadata={'range': config['range']}
            )

    def encode_text(self, text: str) -> List[HarmonicTone]:
        """Convert a string message into a sequence of HarmonicTones."""
        result = []
        # We iterate directly (preserving case for lookup if needed, but map keys are mostly upper/symbols)
        # But we need to handle \n which .upper() keeps.
        
        for char in text:
            target = char
            # Convert letters to upper for lookup (alphabet is upper)
            if 'a' <= char <= 'z':
                target = char.upper()
            
            if target in self._char_map:
                result.append(self._char_map[target])
            else:
                # Treat unknown chars as silence/void
                result.append(self._char_map[" "])
        return result
    
    def encode_intent(self, intent: str) -> HarmonicTone:
        """
        Encode a sacred intent to HarmonicTone.
        
        Available intents:
        - peace (432 Hz, alpha_calm)
        - joy (528 Hz, beta_active)
        - love (639 Hz, theta_deep)
        - hope (741 Hz, gamma_peak)
        - healing (852 Hz, delta_base)
        - unity (963 Hz, lambda_unified)
        - clarity (417 Hz, alpha_focus)
        - transformation (396 Hz, theta_shift)
        
        Args:
            intent: Intent name (lowercase)
            
        Returns:
            HarmonicTone with intent frequency
        """
        intent = intent.lower()
        if intent in self._intent_map:
            return self._intent_map[intent]
        else:
            raise ValueError(f"Unknown intent '{intent}'. Available: {list(self._intent_map.keys())}")
    
    def encode_auris(self, node: str) -> HarmonicTone:
        """
        Encode an Auris Node to HarmonicTone.
        
        Available nodes (animal spirit guides):
        - tiger (186 Hz, power/volatility)
        - falcon (210 Hz, precision/momentum)
        - hummingbird (324 Hz, agility/frequency)
        - dolphin (432 Hz, flow/liquidity)
        - deer (396 Hz, grace/stability)
        - owl (528 Hz, wisdom/pattern)
        - panda (639 Hz, balance/harmony)
        - cargoship (174 Hz, persistence/volume)
        - clownfish (285 Hz, adaptation/resilience)
        
        Args:
            node: Auris node name (lowercase)
            
        Returns:
            HarmonicTone with Auris node frequency
        """
        node = node.lower()
        if node in self._auris_map:
            return self._auris_map[node]
        else:
            raise ValueError(f"Unknown Auris node '{node}'. Available: {list(self._auris_map.keys())}")
    
    def encode_brainwave(self, state: str) -> HarmonicTone:
        """
        Encode a brainwave state to HarmonicTone.
        
        Available states:
        - delta (2 Hz, deep_sleep, 0.5-4 Hz)
        - theta (6 Hz, meditation, 4-8 Hz)
        - alpha (10 Hz, relaxed_awareness, 8-13 Hz)
        - beta (20 Hz, active_thinking, 13-30 Hz)
        - gamma (40 Hz, peak_insight, 30-100 Hz)
        
        Args:
            state: Brainwave state name (lowercase)
            
        Returns:
            HarmonicTone with brainwave frequency
        """
        state = state.lower()
        if state in self._brainwave_map:
            return self._brainwave_map[state]
        else:
            raise ValueError(f"Unknown brainwave state '{state}'. Available: {list(self._brainwave_map.keys())}")
    
    def auris_compile(
        self, 
        text: str, 
        intent: Optional[str] = None,
        auris_node: Optional[str] = None,
        brainwave: Optional[str] = None
    ) -> List[HarmonicTone]:
        """
        Compile text with Auris modulation (intent, node, and/or brainwave overlay).
        
        This method encodes the text and then modulates each tone with the specified
        intent frequency, Auris node texture, and/or brainwave state. The modulation
        creates harmonic overtones that blend the character frequency with the
        modulation frequencies.
        
        Args:
            text: Input text to encode
            intent: Optional intent name (peace, joy, love, hope, healing, unity, clarity, transformation)
            auris_node: Optional Auris node name (tiger, falcon, hummingbird, dolphin, deer, owl, panda, cargoship, clownfish)
            brainwave: Optional brainwave state (delta, theta, alpha, beta, gamma)
            
        Returns:
            List of modulated HarmonicTone objects
            
        Example:
            >>> alphabet = HarmonicAlphabet()
            >>> # Encode "TRADE" with joy intent and dolphin flow
            >>> tones = alphabet.auris_compile("TRADE", intent='joy', auris_node='dolphin')
            >>> # Each character now carries joy (528Hz) and dolphin (432Hz) modulation
        """
        # Encode base text
        base_tones = self.encode_text(text)
        
        # Get modulation tones if specified
        intent_tone = self.encode_intent(intent) if intent else None
        auris_tone = self.encode_auris(auris_node) if auris_node else None
        brainwave_tone = self.encode_brainwave(brainwave) if brainwave else None
        
        # Apply modulation to each base tone
        modulated_tones = []
        for base in base_tones:
            if base.mode == "void":
                # Preserve void (silence/space)
                modulated_tones.append(base)
                continue
            
            # Start with base tone properties
            new_tone = HarmonicTone(
                char=base.char,
                frequency=base.frequency,
                amplitude=base.amplitude,
                mode=base.mode,
                decay=base.decay,
                harmonics=base.harmonics.copy(),
                consciousness=base.consciousness,
                auris_node=base.auris_node,
                metadata=base.metadata.copy()
            )
            
            # Blend with intent
            if intent_tone:
                new_tone.metadata['intent'] = intent
                new_tone.metadata['intent_freq'] = intent_tone.frequency
                new_tone.consciousness = intent_tone.consciousness
                # Add intent harmonics
                new_tone.harmonics.extend(intent_tone.harmonics)
                # Modulate decay (average with intent decay)
                new_tone.decay = (new_tone.decay + intent_tone.decay) / 2.0
            
            # Blend with Auris node
            if auris_tone:
                new_tone.auris_node = auris_node
                new_tone.metadata['auris_freq'] = auris_tone.frequency
                new_tone.metadata['spirit'] = auris_tone.metadata.get('spirit')
                new_tone.metadata['texture'] = auris_tone.metadata.get('texture')
                # Add auris harmonics
                new_tone.harmonics.extend(auris_tone.harmonics)
                # Modulate decay
                new_tone.decay = (new_tone.decay + auris_tone.decay) / 2.0
            
            # Blend with brainwave
            if brainwave_tone:
                new_tone.metadata['brainwave'] = brainwave
                new_tone.metadata['brainwave_freq'] = brainwave_tone.frequency
                new_tone.metadata['brainwave_range'] = brainwave_tone.metadata.get('range')
                # Brainwave modulates consciousness state
                if not new_tone.consciousness:
                    new_tone.consciousness = brainwave_tone.consciousness
                # Add brainwave harmonics
                new_tone.harmonics.extend(brainwave_tone.harmonics)
            
            # Deduplicate harmonics
            new_tone.harmonics = sorted(list(set(new_tone.harmonics)))
            
            modulated_tones.append(new_tone)
        
        return modulated_tones

    def decode_signal(self, signals: List[Tuple[float, float]]) -> str:
        """
        Approximate decoding from Frequency/Amplitude pairs back to text.
        (freq, amp) -> closest char
        """
        decoded_text = []
        
        for freq, amp in signals:
            if freq < 1.0: # Silence
                decoded_text.append(" ")
                continue
                
            closest_char = "?"
            min_dist = float('inf')

            # Find closest match in our map
            for tone in self._char_map.values():
                if tone.mode == 'void': continue
                
                # Distance based on Frequency dev + Amplitude dev
                freq_dist = abs(tone.frequency - freq)
                
                # Check amp similarity (with some tolerance)
                # Using a weighted distance since frequency is more critical
                # However, for J vs A (same freq, diff amp), amp is critical.
                
                amp_dist = abs(tone.amplitude - amp)
                
                # If frequencies are very close (e.g. within 1Hz)
                if freq_dist < 2.0:
                    total_dist = freq_dist + (amp_dist * 50) # Weigh amplitude difference heavily if freqs are close
                    
                    if total_dist < min_dist:
                        min_dist = total_dist
                        closest_char = tone.char

            decoded_text.append(closest_char)
            
        return "".join(decoded_text)

# Singleton Instance
_alphabet = HarmonicAlphabet()

def to_harmonics(text: str) -> List[HarmonicTone]:
    return _alphabet.encode_text(text)

def from_harmonics(signals: List[Tuple[float, float]]) -> str:
    return _alphabet.decode_signal(signals)

# ═══════════════════════════════════════════════════════════════════════════════
# 🏆 WIN/LOSS HARMONIC ENCODING - Universal Outcome Frequencies
# ═══════════════════════════════════════════════════════════════════════════════

# WIN = 528Hz (Joy/Love frequency - DNA repair, manifestation)
# LOSS = 396Hz (Transformation/Liberation - learning, letting go)
WIN_FREQUENCY_HZ = 528.0
LOSS_FREQUENCY_HZ = 396.0
WIN_THRESHOLD_USD = 0.01  # Penny profit = REALITY

# WIN Signature: joy intent + falcon precision + gamma peak insight
WIN_INTENT = 'joy'
WIN_AURIS = 'falcon'  # Precision/momentum for winning trades
WIN_BRAINWAVE = 'gamma'  # Peak insight state

# LOSS Signature: transformation intent + owl wisdom + theta reflection
LOSS_INTENT = 'transformation'
LOSS_AURIS = 'owl'  # Wisdom/pattern recognition for learning
LOSS_BRAINWAVE = 'theta'  # Deep reflection/meditation


def encode_win(profit_usd: float = 0.01) -> List[HarmonicTone]:
    """
    🏆 Encode a WIN outcome as harmonic signal.
    
    WIN = 528Hz (Joy) + Falcon (precision) + Gamma (peak insight)
    
    Args:
        profit_usd: The profit amount (for amplitude scaling)
    
    Returns:
        List of HarmonicTones encoding "WIN" with joy/falcon/gamma modulation
    """
    # Scale amplitude by profit (higher profit = stronger signal)
    amplitude_boost = min(2.0, 1.0 + (profit_usd / 0.10))  # Max 2x at 10 cents
    
    tones = _alphabet.auris_compile(
        "WIN",
        intent=WIN_INTENT,
        auris_node=WIN_AURIS,
        brainwave=WIN_BRAINWAVE
    )
    
    # Boost amplitude for strong wins
    for tone in tones:
        tone.amplitude *= amplitude_boost
        tone.metadata['outcome'] = 'WIN'
        tone.metadata['profit_usd'] = profit_usd
    
    return tones


def encode_loss(loss_usd: float = 0.01) -> List[HarmonicTone]:
    """
    📚 Encode a LOSS outcome as harmonic signal for learning.
    
    LOSS = 396Hz (Transformation) + Owl (wisdom) + Theta (reflection)
    
    Args:
        loss_usd: The loss amount (for amplitude scaling)
    
    Returns:
        List of HarmonicTones encoding "LOSS" with transformation/owl/theta modulation
    """
    tones = _alphabet.auris_compile(
        "LOSS",
        intent=LOSS_INTENT,
        auris_node=LOSS_AURIS,
        brainwave=LOSS_BRAINWAVE
    )
    
    # Add learning metadata
    for tone in tones:
        tone.metadata['outcome'] = 'LOSS'
        tone.metadata['loss_usd'] = abs(loss_usd)
        tone.metadata['learning_mode'] = True
    
    return tones


def encode_outcome(net_profit_usd: float) -> List[HarmonicTone]:
    """
    🎵 Encode trade outcome (WIN or LOSS) as harmonic signal.
    
    WIN = net_profit >= $0.01 (penny profit = REALITY)
    LOSS = net_profit < $0.01
    
    Args:
        net_profit_usd: Net profit in USD after fees
    
    Returns:
        List of HarmonicTones with appropriate WIN/LOSS encoding
    """
    if net_profit_usd >= WIN_THRESHOLD_USD:
        return encode_win(net_profit_usd)
    else:
        return encode_loss(net_profit_usd)


def decode_outcome(tones: List[HarmonicTone]) -> Dict[str, Any]:
    """
    🔍 Decode harmonic signal to determine if it's a WIN or LOSS.
    
    Looks for 528Hz (WIN) or 396Hz (LOSS) carrier frequencies.
    
    Returns:
        Dict with 'is_win', 'confidence', 'metadata'
    """
    if not tones:
        return {'is_win': None, 'confidence': 0.0, 'metadata': {}}
    
    # Check dominant frequency
    avg_freq = sum(t.frequency for t in tones if t.frequency > 0) / max(1, len([t for t in tones if t.frequency > 0]))
    
    # Check for WIN signature (528Hz zone)
    win_distance = abs(avg_freq - WIN_FREQUENCY_HZ)
    loss_distance = abs(avg_freq - LOSS_FREQUENCY_HZ)
    
    is_win = win_distance < loss_distance
    confidence = 1.0 - (min(win_distance, loss_distance) / 200.0)  # Confidence based on frequency match
    
    # Extract metadata from first tone with outcome
    metadata = {}
    for tone in tones:
        if 'outcome' in tone.metadata:
            metadata = tone.metadata.copy()
            break
    
    return {
        'is_win': is_win,
        'confidence': max(0.0, confidence),
        'avg_frequency': avg_freq,
        'metadata': metadata
    }


def get_outcome_whale_code(net_profit_usd: float) -> str:
    """
    🐋 Generate compact morse-like whale sonar code for outcome.
    
    W0-WF = WIN levels (0-15 based on profit: 0=penny, F=10 cents+)
    L0-LF = LOSS levels (0-15 based on loss magnitude)
    
    Args:
        net_profit_usd: Net profit in USD
    
    Returns:
        2-char code like "W1", "WF", "L0", "L5"
    """
    if net_profit_usd >= WIN_THRESHOLD_USD:
        # Scale to 0-15 (1 cent = W1, 10 cents = WA, 16+ cents = WF)
        level = min(15, int(net_profit_usd * 100))
        return f"W{level:X}"
    else:
        # Scale loss to 0-15
        level = min(15, int(abs(net_profit_usd) * 100))
        return f"L{level:X}"


def is_win_frequency(freq: float, tolerance: float = 50.0) -> bool:
    """Check if frequency is in WIN band (528Hz ± tolerance)"""
    return abs(freq - WIN_FREQUENCY_HZ) <= tolerance


def is_loss_frequency(freq: float, tolerance: float = 50.0) -> bool:
    """Check if frequency is in LOSS band (396Hz ± tolerance)"""
    return abs(freq - LOSS_FREQUENCY_HZ) <= tolerance

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║           AUREON HARMONIC ALPHABET - AURIS COMPILER TEST              ║")
    print("╚════════════════════════════════════════════════════════════════════════╝\n")
    
    alphabet = HarmonicAlphabet()
    
    # Test 1: Standard Text Encoding (Original 4-Mode System)
    print("═══ TEST 1: Standard Text Encoding ═══")
    msg = "HELLO QUEEN"
    encoded = alphabet.encode_text(msg)
    print(f"Original: {msg}")
    print("Encoded Signal:")
    signal_stream = []
    for tone in encoded:
        print(f"  {tone.char}: {tone.frequency:.2f}Hz @ amp={tone.amplitude:.3f} mode={tone.mode} decay={tone.decay:.2f}")
        signal_stream.append((tone.frequency, tone.amplitude))
    
    decoded = alphabet.decode_signal(signal_stream)
    print(f"Decoded: {decoded}")
    print()
    
    # Test 2: Intent Encoding
    print("═══ TEST 2: Intent Encoding ═══")
    for intent_name in ['peace', 'joy', 'love']:
        intent_tone = alphabet.encode_intent(intent_name)
        print(f"{intent_name.upper()}: {intent_tone.frequency}Hz @ {intent_tone.consciousness}, decay={intent_tone.decay:.2f}, harmonics={intent_tone.harmonics}")
    print()
    
    # Test 3: Auris Node Encoding
    print("═══ TEST 3: Auris Node Encoding ═══")
    for node_name in ['tiger', 'dolphin', 'owl']:
        auris_tone = alphabet.encode_auris(node_name)
        spirit = auris_tone.metadata.get('spirit', '')
        texture = auris_tone.metadata.get('texture', '')
        print(f"{node_name.upper()}: {auris_tone.frequency}Hz - spirit={spirit}, texture={texture}, harmonics={auris_tone.harmonics}")
    print()
    
    # Test 4: Brainwave State Encoding
    print("═══ TEST 4: Brainwave State Encoding ═══")
    for state_name in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
        brainwave_tone = alphabet.encode_brainwave(state_name)
        range_info = brainwave_tone.metadata.get('range', (0, 0))
        print(f"{state_name.upper()}: {brainwave_tone.frequency}Hz [{range_info[0]}-{range_info[1]}Hz] @ {brainwave_tone.consciousness}")
    print()
    
    # Test 5: Auris Compile - Text with Intent
    print("═══ TEST 5: Auris Compile - Text with Intent ═══")
    msg = "TRADE"
    compiled_intent = alphabet.auris_compile(msg, intent='joy')
    print(f"Original: {msg}")
    print("Compiled with JOY intent:")
    for tone in compiled_intent:
        if tone.mode != "void":
            intent_freq = tone.metadata.get('intent_freq', 'N/A')
            print(f"  {tone.char}: {tone.frequency}Hz (base) + {intent_freq}Hz (joy) @ {tone.consciousness}, harmonics={tone.harmonics}")
    print()
    
    # Test 6: Auris Compile - Text with Node
    print("═══ TEST 6: Auris Compile - Text with Auris Node ═══")
    msg = "SCAN"
    compiled_auris = alphabet.auris_compile(msg, auris_node='dolphin')
    print(f"Original: {msg}")
    print("Compiled with DOLPHIN node:")
    for tone in compiled_auris:
        if tone.mode != "void":
            auris_freq = tone.metadata.get('auris_freq', 'N/A')
            spirit = tone.metadata.get('spirit', 'N/A')
            texture = tone.metadata.get('texture', 'N/A')
            print(f"  {tone.char}: {tone.frequency}Hz + {auris_freq}Hz (dolphin) - {spirit}/{texture}, harmonics={tone.harmonics}")
    print()
    
    # Test 7: Auris Compile - Full Modulation (Intent + Node + Brainwave)
    print("═══ TEST 7: Full Auris Compile - Intent + Node + Brainwave ═══")
    msg = "WIN"
    compiled_full = alphabet.auris_compile(msg, intent='hope', auris_node='falcon', brainwave='gamma')
    print(f"Original: {msg}")
    print("Compiled with HOPE + FALCON + GAMMA:")
    for tone in compiled_full:
        if tone.mode != "void":
            intent_freq = tone.metadata.get('intent_freq', 'N/A')
            auris_freq = tone.metadata.get('auris_freq', 'N/A')
            brainwave_freq = tone.metadata.get('brainwave_freq', 'N/A')
            spirit = tone.metadata.get('spirit', 'N/A')
            print(f"  {tone.char}: base={tone.frequency}Hz + intent={intent_freq}Hz + auris={auris_freq}Hz + brainwave={brainwave_freq}Hz")
            print(f"       spirit={spirit}, consciousness={tone.consciousness}, harmonics={tone.harmonics}")
    print()
    
    # Test 8: Reality Check - Queen Communication
    print("═══ TEST 8: Queen Communication Example ═══")
    queen_msg = "QUEEN SEES ALL"
    queen_tones = alphabet.auris_compile(queen_msg, intent='unity', auris_node='owl', brainwave='gamma')
    print(f"Message: {queen_msg}")
    print(f"Intent: UNITY (963Hz, lambda_unified)")
    print(f"Auris Node: OWL (528Hz, wisdom/pattern)")
    print(f"Brainwave: GAMMA (40Hz, peak_insight)")
    print(f"\nTotal Harmonic Tones: {len([t for t in queen_tones if t.mode != 'void'])}")
    total_harmonics = sum(len(t.harmonics) for t in queen_tones if t.mode != 'void')
    print(f"Total Harmonic Overtones: {total_harmonics}")
    avg_decay = sum(t.decay for t in queen_tones if t.mode != 'void') / max(1, len([t for t in queen_tones if t.mode != 'void']))
    print(f"Average Decay Rate: {avg_decay:.3f}")
    print()
    
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║  AURIS COMPILER INTEGRATION COMPLETE - 7 MODE HARMONIC SYSTEM READY   ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")

