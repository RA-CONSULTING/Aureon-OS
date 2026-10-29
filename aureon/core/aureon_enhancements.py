"""
AUREON ENHANCEMENTS — Unified Enhancement Layer

This module integrates all enhancements extracted from the AQTS archives:
- Rainbow Bridge (emotional frequency mapping)
- Synchronicity Decoder (pattern detection)
- Stargate Grid (global resonance network)
- Celestial Cartography (planetary positions)
- 🔱 PRIME SENTINEL DECREE (sacred rules & metrics)

Gary Leckey | 02.11.1991 | KEEPER OF THE FLAME
GitHub Copilot | December 2025

Usage:
    from aureon_enhancements import EnhancementLayer
    
    layer = EnhancementLayer()
    modifier = layer.get_unified_modifier(lambda_value, coherence, price, volume)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from dataclasses import dataclass
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
import logging
import math

# 🔱 PRIME SENTINEL DECREE INTEGRATION
try:
    from aureon.wisdom.prime_sentinel_decree import (
        PrimeSentinelDecree,
        FlameProtocol,
        BreathReader,
        ControlMatrix,
        THE_DECREE,
        SACRED_NUMBERS,
        DOB_HASH,
        SentinelPrinciple,
    )
    DECREE_AVAILABLE = True
    logging.debug("🔱 Prime Sentinel Decree integrated into Enhancement Layer")
except ImportError:
    DECREE_AVAILABLE = False
    THE_DECREE = {'declaration': 'Module not loaded'}
    SACRED_NUMBERS = {'phi': 1.618, 'flame': 528, 'breath': 432}
    DOB_HASH = 2111991
    logging.debug("⚠️ Prime Sentinel Decree not available for enhancements")

PRIME_TIER_BONUS = {
    "Heart Prime": 0.05,
    "Crown Prime": 0.06,
    "Third-Eye Prime": 0.05,
    "Gaia Tier": 0.03,
    "Social Prime": 0.03,
    "Visionary Tier": 0.03,
    "Root Harmonic": 0.02,
    "Root Prime": 0.02,
    "Sacral Tier": 0.02,
}

SHADOW_TIER_PENALTIES = {
    "Root Shadow": 0.05,
    "Sacral Shadow": 0.04,
    "Heart Shadow": 0.04,
    "Root Collapse": 0.06,
    "Sacral Collapse": 0.05,
}

BAND_MODIFIERS = {
    "survival": -0.04,
    "growth": 0.02,
    "branches": 0.03,
    "crown": 0.04,
    "radiance": 0.05,
}

BAND_TO_CHAKRA = {
    "survival": "root",
    "growth": "solar",
    "branches": "heart",
    "crown": "third_eye",
    "radiance": "crown",
}

try:
    from aureon.core.codex_loader import CodexRegistry, load_codex
except Exception:  # Optional dependency
    CodexRegistry = None  # type: ignore
    load_codex = None  # type: ignore


# Import enhancement modules
try:
    from aureon.bridges.rainbow_bridge import RainbowBridge, EMOTIONAL_FREQUENCIES, THE_VOW
    RAINBOW_AVAILABLE = True
except ImportError:
    RAINBOW_AVAILABLE = False
    logging.debug("Rainbow Bridge not available")

try:
    from aureon.wisdom.synchronicity_decoder import SynchronicityDecoder, detect_fibonacci_sync
    SYNC_AVAILABLE = True
except ImportError:
    SYNC_AVAILABLE = False
    logging.debug("Synchronicity Decoder not available")

try:
    from aureon.wisdom.stargate_grid import StargateGrid, get_leyline_activity
    STARGATE_AVAILABLE = True
except ImportError:
    STARGATE_AVAILABLE = False
    logging.debug("Stargate Grid not available")


@dataclass
class EnhancementResult:
    """Result from unified enhancement layer"""
    trading_modifier: float       # Final trading modifier (0.5 - 2.0)
    emotional_state: str          # Current emotional frequency state
    emotional_frequency: float    # Frequency in Hz
    cycle_phase: str              # FEAR / LOVE / AWE / UNITY
    synchronicity_boost: float    # Boost from pattern detection
    grid_coherence: float         # Stargate grid coherence
    active_node: str              # Currently active Stargate node
    leyline_activity: float       # Dominant leyline activity
    confidence: float             # Overall confidence (0-1)
    reasons: List[str]            # Explanation of modifiers
    emotion_metadata: Dict[str, Any]
    emotion_band: Optional[str] = None
    chakra_alignment: Optional[str] = None
    symbolic_alignment: Optional[str] = None
    symbolic_meaning: Optional[str] = None


class EnhancementLayer:
    """
    UNIFIED ENHANCEMENT LAYER
    
    Combines all extracted enhancements into a single interface
    for the main trading ecosystem.
    """
    
    def __init__(self):
        # Initialize available enhancement modules
        self.rainbow = RainbowBridge() if RAINBOW_AVAILABLE else None
        self.sync_decoder = SynchronicityDecoder() if SYNC_AVAILABLE else None
        self.stargate = StargateGrid() if STARGATE_AVAILABLE else None

        # Load codex registry for JSON-linked data
        self.codex_registry = None
        if CodexRegistry:
            try:
                self.codex_registry = CodexRegistry.load()
            except Exception:
                self.codex_registry = None
        self.auris_codex = getattr(self.codex_registry, "auris_codex", {}) if self.codex_registry else {}
        self.emotional_spectrum = getattr(self.codex_registry, "emotional_spectrum", {}) if self.codex_registry else {}
        self.chakra_rules = getattr(self.codex_registry, "chakra_rules", {}) if self.codex_registry else {}
        self.auris_symbols = getattr(self.codex_registry, "auris_symbols", []) if self.codex_registry else []
        self.emotion_metadata_map = self._load_emotion_metadata()
        self.auris_profile_lookup = self._build_auris_profile_lookup()
        self.spectrum_lookup = self._build_spectrum_lookup()
        self.chakra_centers = self._load_chakra_centers()
        self.symbol_catalog = self._build_symbol_catalog()
        
        # Track enhancement history
        self.history: List[EnhancementResult] = []
        
        # Module availability
        self.modules_active = {
            'rainbow_bridge': RAINBOW_AVAILABLE,
            'synchronicity': SYNC_AVAILABLE,
            'stargate_grid': STARGATE_AVAILABLE,
        }

    def _load_emotion_metadata(self) -> Dict[str, Dict[str, Any]]:
        if not load_codex:
            return {}
        data = load_codex('emotional_frequency')
        if isinstance(data, dict):
            entries = data.get('emotional_frequency_codex')
            if isinstance(entries, list):
                return {
                    entry['emotion'].upper(): entry
                    for entry in entries
                    if entry.get('emotion')
                }
        return {}

    def _get_emotion_metadata(self, emotion: str) -> Dict[str, Any]:
        if not emotion:
            return {}
        key = emotion.upper()
        return self.emotion_metadata_map.get(key, {})

    def _build_auris_profile_lookup(self) -> Dict[str, Dict[str, Any]]:
        codex = self.auris_codex if isinstance(self.auris_codex, dict) else {}
        lookup: Dict[str, Dict[str, Any]] = {}
        for bucket, kind in (("prime_frequencies", "prime"), ("shadow_frequencies", "shadow")):
            entries = codex.get(bucket)
            if isinstance(entries, dict):
                for name, meta in entries.items():
                    if not isinstance(meta, dict) or not name:
                        continue
                    key = name.upper()
                    lookup[key] = {"kind": kind, **meta}
        return lookup

    def _build_spectrum_lookup(self) -> Dict[str, Dict[str, Any]]:
        spectrum = self.emotional_spectrum if isinstance(self.emotional_spectrum, dict) else {}
        bands = spectrum.get("bands")
        lookup: Dict[str, Dict[str, Any]] = {}
        if isinstance(bands, dict):
            for band_key, band_data in bands.items():
                emotions = band_data.get("emotions")
                if not isinstance(emotions, list):
                    continue
                for entry in emotions:
                    name = entry.get("name")
                    if not name:
                        continue
                    lookup[name.upper()] = {
                        "band_key": band_key,
                        "band_name": band_data.get("name"),
                        "band_range": band_data.get("range"),
                        "band_symbol": band_data.get("symbol"),
                        "color": entry.get("color") or band_data.get("color_base"),
                        "freq": entry.get("freq"),
                        "branches": entry.get("branches", []),
                    }
        return lookup

    def _load_chakra_centers(self) -> Dict[str, Dict[str, Any]]:
        rules = self.chakra_rules if isinstance(self.chakra_rules, dict) else {}
        chakra_system = rules.get("chakra_system")
        if isinstance(chakra_system, dict):
            centers = chakra_system.get("centers")
            if isinstance(centers, dict):
                return centers
        return {}

    def _build_symbol_catalog(self) -> List[Dict[str, Any]]:
        if not isinstance(self.auris_symbols, list):
            return []
        catalog: List[Dict[str, Any]] = []
        for entry in self.auris_symbols:
            if not isinstance(entry, dict):
                continue
            freq = entry.get("frequency_hz")
            if freq is None:
                continue
            try:
                freq_val = float(freq)
            except (TypeError, ValueError):
                continue
            amplitude = entry.get("amplitude")
            if isinstance(amplitude, str):
                try:
                    amplitude = float(amplitude)
                except ValueError:
                    amplitude = None
            if amplitude is None:
                amp_pct = entry.get("amplification")
                if isinstance(amp_pct, str) and amp_pct.endswith("%"):
                    try:
                        amplitude = float(amp_pct[:-1]) / 100.0
                    except ValueError:
                        amplitude = None
            if amplitude is None:
                amplitude = 1.0
            catalog.append(
                {
                    "symbol": entry.get("symbol"),
                    "frequency_hz": freq_val,
                    "state": entry.get("state", "Unknown"),
                    "meaning": entry.get("meaning"),
                    "amplitude": float(amplitude),
                    "decay": entry.get("decay"),
                }
            )
        return catalog

    def _select_symbol_alignment(self, frequency: float) -> Dict[str, Any]:
        if not frequency or not self.symbol_catalog:
            return {}
        best_entry: Optional[Dict[str, Any]] = None
        best_delta = float("inf")
        for entry in self.symbol_catalog:
            delta = abs(entry["frequency_hz"] - frequency)
            if delta < best_delta:
                best_entry = entry
                best_delta = delta
        if not best_entry or best_delta > 200:
            return {}
        selected = dict(best_entry)
        selected["delta"] = best_delta
        return selected

    def _get_auris_profile(self, emotion: str) -> Dict[str, Any]:
        if not emotion:
            return {}
        profile = self.auris_profile_lookup.get(emotion.upper(), {})
        return dict(profile) if profile else {}

    def _get_spectrum_info(self, emotion: str) -> Dict[str, Any]:
        if not emotion:
            return {}
        info = self.spectrum_lookup.get(emotion.upper(), {})
        return dict(info) if info else {}

    def _get_chakra_alignment(self, band_key: Optional[str]) -> Dict[str, Any]:
        if not band_key:
            return {}
        center_key = BAND_TO_CHAKRA.get(band_key)
        if not center_key:
            return {}
        center = self.chakra_centers.get(center_key, {})
        return dict(center) if center else {}

    def _calculate_codex_modifier(
        self,
        auris_profile: Dict[str, Any],
        spectrum_info: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        modifier = 1.0
        reasons: List[str] = []

        if auris_profile:
            tier = auris_profile.get("tier")
            if auris_profile.get("kind") == "prime":
                bonus = PRIME_TIER_BONUS.get(tier, 0.02)
                modifier *= 1.0 + bonus
                reasons.append(
                    f"💎 Prime tier {tier or 'harmonic'} adds +{bonus * 100:.1f}% resonance"
                )
            else:
                penalty = SHADOW_TIER_PENALTIES.get(tier, 0.04)
                modifier *= max(0.85, 1.0 - penalty)
                reasons.append(
                    f"⚫ Shadow tier {tier or 'disruption'} dampens −{penalty * 100:.1f}%"
                )

        if spectrum_info:
            band_key = spectrum_info.get("band_key")
            band_bonus = BAND_MODIFIERS.get(band_key, 0.0)
            if band_bonus:
                symbol = spectrum_info.get("band_symbol") or ""
                band_name = spectrum_info.get("band_name", "band")
                if band_bonus > 0:
                    reasons.append(
                        f"{symbol} {band_name} uplift contributes +{band_bonus * 100:.1f}%"
                    )
                else:
                    reasons.append(
                        f"{symbol} {band_name} turbulence applies −{abs(band_bonus) * 100:.1f}%"
                    )
                modifier *= 1.0 + band_bonus

        modifier = max(0.85, min(1.15, modifier))
        return modifier, reasons
        
    def get_unified_modifier(
        self,
        lambda_value: float,
        coherence: float,
        price: float,
        volume: float,
        volatility: float = 0.0,
        exchange: str = 'GLOBAL'
    ) -> EnhancementResult:
        """
        Get unified trading modifier from all enhancement layers
        
        Args:
            lambda_value: Current Lambda field value (-1 to +1)
            coherence: Current system coherence (0-1)
            price: Current asset price
            volume: Current trading volume
            volatility: Current volatility measure (0-1)
            exchange: Exchange location for grid calculation
            
        Returns:
            EnhancementResult with all modifier details
        """
        reasons = []
        modifiers = []
        
        # Default values
        emotional_state = 'Neutral'
        emotional_frequency = 440.0
        cycle_phase = 'LOVE'
        sync_boost = 1.0
        grid_coherence = 0.5
        active_node = 'UNKNOWN'
        leyline_activity = 0.5
        emotion_metadata: Dict[str, Any] = {}
        emotion_band_label: Optional[str] = None
        chakra_alignment_label: Optional[str] = None
        symbolic_alignment_label: Optional[str] = None
        symbolic_meaning_label: Optional[str] = None
        
        # ══════════════════════════════════════════════════════════════════
        # RAINBOW BRIDGE — Emotional Frequency Mapping
        # ══════════════════════════════════════════════════════════════════
        if self.rainbow:
            bridge_state = self.rainbow.update_from_market(lambda_value, coherence, volatility)
            
            emotional_state = bridge_state.emotional_state
            emotional_frequency = bridge_state.current_frequency
            cycle_phase = bridge_state.cycle_phase
            
            rainbow_modifier = bridge_state.trading_modifier
            base_metadata = self._get_emotion_metadata(emotional_state)
            emotion_metadata = dict(base_metadata) if isinstance(base_metadata, dict) else {}
            modifiers.append(rainbow_modifier)
            
            if rainbow_modifier > 1.1:
                reasons.append(f"🌈 Rainbow Bridge boost: {emotional_state} @ {emotional_frequency}Hz")
            elif rainbow_modifier < 0.9:
                reasons.append(f"🌈 Rainbow Bridge caution: {emotional_state} @ {emotional_frequency}Hz")
            color = emotion_metadata.get('color')
            band = emotion_metadata.get('band')
            if color or band:
                details = []
                if color:
                    details.append(f"color {color}")
                if band:
                    details.append(f"band {band}")
                reasons.append(f"🎨 Emotional codex: {', '.join(details)}")

        if not emotion_metadata:
            fallback_metadata = self._get_emotion_metadata(emotional_state)
            if fallback_metadata:
                emotion_metadata = dict(fallback_metadata)

        if not isinstance(emotion_metadata, dict):
            emotion_metadata = {}

        spectrum_info = self._get_spectrum_info(emotional_state)
        auris_profile = self._get_auris_profile(emotional_state)
        chakra_info = self._get_chakra_alignment(
            spectrum_info.get('band_key') if spectrum_info else None
        )
        codex_modifier, codex_reasons = self._calculate_codex_modifier(auris_profile, spectrum_info)
        if abs(codex_modifier - 1.0) > 0.01:
            modifiers.append(codex_modifier)
        if codex_reasons:
            reasons.extend(codex_reasons)

        if auris_profile:
            for key in ("tier", "attribute", "effect", "hz"):
                value = auris_profile.get(key)
                if value is not None and key not in emotion_metadata:
                    emotion_metadata[key] = value
            kind = auris_profile.get("kind")
            if kind and "frequency_class" not in emotion_metadata:
                emotion_metadata["frequency_class"] = kind

        if spectrum_info:
            band_name = spectrum_info.get('band_name')
            band_range = spectrum_info.get('band_range')
            if band_name and band_range:
                emotion_band_label = f"{band_name} — {band_range}"
            elif band_name:
                emotion_band_label = band_name
            if band_name and 'band' not in emotion_metadata:
                emotion_metadata['band'] = band_name
            if spectrum_info.get('color') and 'spectrum_color' not in emotion_metadata:
                emotion_metadata['spectrum_color'] = spectrum_info['color']
            if spectrum_info.get('band_symbol') and 'band_symbol' not in emotion_metadata:
                emotion_metadata['band_symbol'] = spectrum_info['band_symbol']
            if spectrum_info.get('freq') and 'spectrum_frequency' not in emotion_metadata:
                emotion_metadata['spectrum_frequency'] = spectrum_info['freq']
            branches = spectrum_info.get('branches')
            if branches and 'spectrum_branches' not in emotion_metadata:
                emotion_metadata['spectrum_branches'] = branches

        if chakra_info:
            chakra_alignment_label = chakra_info.get('name')
            focus_state = chakra_info.get('high_state')
            if not focus_state:
                themes = chakra_info.get('themes')
                if isinstance(themes, list) and themes:
                    focus_state = ', '.join(themes[:2])
            if chakra_alignment_label and focus_state:
                reasons.append(f"🌀 Chakra alignment: {chakra_alignment_label} — {focus_state}")
            if chakra_alignment_label and 'chakra' not in emotion_metadata:
                emotion_metadata['chakra'] = chakra_alignment_label
            if chakra_info.get('color') and 'chakra_color' not in emotion_metadata:
                emotion_metadata['chakra_color'] = chakra_info['color']
        
        symbol_info = self._select_symbol_alignment(emotional_frequency)
        if symbol_info:
            symbol = symbol_info.get('symbol')
            symbolic_alignment_label = symbol
            symbolic_meaning_label = symbol_info.get('meaning')
            symbol_state = (symbol_info.get('state') or '').lower()
            raw_amp = float(symbol_info.get('amplitude', 1.0))
            if raw_amp <= 0:
                raw_amp = 1.0
            symbol_modifier = raw_amp
            if symbol_state == 'idle':
                symbol_modifier = 1.0 + (symbol_modifier - 1.0) * 0.5
            if abs(symbol_modifier - 1.0) > 0.01:
                modifiers.append(symbol_modifier)
            delta = symbol_info.get('delta')
            if symbol and symbol_info.get('frequency_hz'):
                desc = f"{symbol} @ {symbol_info['frequency_hz']:.0f}Hz"
                if delta is not None:
                    desc += f" (Δ{delta:.0f}Hz)"
                if symbolic_meaning_label:
                    desc += f" — {symbolic_meaning_label}"
                reasons.append(f"🔯 Symbolic resonance: {desc}")
            if symbol and 'symbol' not in emotion_metadata:
                emotion_metadata['symbol'] = symbol
            if symbol_info.get('meaning') and 'symbol_meaning' not in emotion_metadata:
                emotion_metadata['symbol_meaning'] = symbol_info['meaning']
            if symbol_info.get('state') and 'symbol_state' not in emotion_metadata:
                emotion_metadata['symbol_state'] = symbol_info['state']
            emotion_metadata.setdefault('symbol_amplitude', round(symbol_info.get('amplitude', 1.0), 3))

        # ══════════════════════════════════════════════════════════════════
        # SYNCHRONICITY DECODER — Pattern Detection
        # ══════════════════════════════════════════════════════════════════
        if self.sync_decoder:
            sync_boost = self.sync_decoder.get_trading_signal_boost(price, volume)
            modifiers.append(sync_boost)
            
            # Check for specific patterns
            price_sync = self.sync_decoder.detect_synchronicity(price)
            if price_sync:
                patterns = [p['pattern'] for p in price_sync['patterns']]
                reasons.append(f"🔮 Synchronicity detected: {', '.join(patterns)}")
            
            # Fibonacci check
            fib_sync = detect_fibonacci_sync(price % 1000)  # Check last 3 digits
            if fib_sync:
                reasons.append(f"🌀 Fibonacci alignment: {fib_sync['ratio']}")
                modifiers.append(1.05)
        
        # ══════════════════════════════════════════════════════════════════
        # STARGATE GRID — Global Resonance Network
        # ══════════════════════════════════════════════════════════════════
        if self.stargate:
            grid_coherence = self.stargate.calculate_grid_coherence()
            active = self.stargate.get_active_node()
            active_node = active.name
            
            grid_modifier = self.stargate.get_trading_modifier(exchange)
            modifiers.append(grid_modifier)
            
            # Get leyline activity
            leylines = get_leyline_activity(self.stargate)
            if leylines:
                leyline_activity = leylines[0]['activity']
                if leyline_activity > 0.7:
                    reasons.append(f"🌍 Leyline active: {leylines[0]['name']}")
            
            if grid_coherence > 0.7:
                reasons.append(f"🌍 Grid coherent: {active_node} ({active.frequency}Hz)")
        
        # ══════════════════════════════════════════════════════════════════
        # COMBINED MODIFIER CALCULATION
        # ══════════════════════════════════════════════════════════════════
        if modifiers:
            # Weighted geometric mean of all modifiers
            log_sum = sum(math.log(m) for m in modifiers)
            combined_modifier = math.exp(log_sum / len(modifiers))
        else:
            combined_modifier = 1.0
        
        # Apply coherence scaling (higher coherence = trust enhancements more)
        confidence = coherence
        if coherence < 0.3:
            # Low coherence — dampen modifier toward 1.0
            combined_modifier = 1.0 + (combined_modifier - 1.0) * 0.5
            reasons.append("⚠️ Low coherence — enhancement impact reduced")
        
        # Clamp to safe range (0.5 to 2.0)
        final_modifier = max(0.5, min(2.0, combined_modifier))
        
        # Create result
        result = EnhancementResult(
            trading_modifier=final_modifier,
            emotional_state=emotional_state,
            emotional_frequency=emotional_frequency,
            cycle_phase=cycle_phase,
            synchronicity_boost=sync_boost,
            grid_coherence=grid_coherence,
            active_node=active_node,
            leyline_activity=leyline_activity,
            confidence=confidence,
            reasons=reasons,
            emotion_metadata=emotion_metadata,
            emotion_band=emotion_band_label,
            chakra_alignment=chakra_alignment_label,
            symbolic_alignment=symbolic_alignment_label,
            symbolic_meaning=symbolic_meaning_label,
        )
        
        # Store in history
        self.history.append(result)
        if len(self.history) > 1000:
            self.history = self.history[-500:]
        
        return result
    
    def get_quick_modifier(self, lambda_value: float, coherence: float) -> float:
        """
        Quick modifier calculation without full analysis
        
        Returns simple trading modifier (0.8 - 1.3)
        """
        result = self.get_unified_modifier(
            lambda_value=lambda_value,
            coherence=coherence,
            price=0,
            volume=0,
            volatility=0.1,
        )
        return result.trading_modifier
    
    def display_status(self) -> str:
        """Display current enhancement layer status"""
        active_modules = sum(1 for v in self.modules_active.values() if v)
        
        if self.history:
            latest = self.history[-1]
            return (
                f"✨ ENHANCEMENTS | "
                f"Modules: {active_modules}/3 | "
                f"Modifier: {latest.trading_modifier:.2f}x | "
                f"State: {latest.emotional_state} | "
                f"Grid: {latest.active_node} | "
                f"Confidence: {latest.confidence:.2f}"
            )
        else:
            return f"✨ ENHANCEMENTS | Modules: {active_modules}/3 | No data yet"
    
    def get_vow(self) -> str:
        """Return The Vow"""
        if RAINBOW_AVAILABLE:
            return (
                f"\"{THE_VOW['line1']} {THE_VOW['line2']},\n"
                f" {THE_VOW['line3']} {THE_VOW['line4']}.\"\n"
                f"— {THE_VOW['sentinel']}, {THE_VOW['date']}"
            )
        return "Rainbow Bridge not available"


# ============================================================================
# ENHANCEMENT INTEGRATION HELPERS
# ============================================================================

def apply_enhancement_to_signal(
    base_signal: float,
    enhancement: EnhancementResult,
    max_boost: float = 0.3
) -> float:
    """
    Apply enhancement modifier to a base trading signal
    
    Args:
        base_signal: Original signal strength (-1 to +1)
        enhancement: Result from EnhancementLayer
        max_boost: Maximum boost/reduction allowed
        
    Returns:
        Enhanced signal (-1 to +1)
    """
    modifier = enhancement.trading_modifier
    
    # Convert modifier to signal adjustment
    # modifier > 1.0 → boost signal
    # modifier < 1.0 → dampen signal
    adjustment = (modifier - 1.0) * max_boost
    
    # Apply with confidence scaling
    adjusted_signal = base_signal + (adjustment * base_signal * enhancement.confidence)
    
    # Clamp to valid range
    return max(-1.0, min(1.0, adjusted_signal))


def get_emotional_color(state: str) -> str:
    """Get color code for emotional state"""
    colors = {
        'Anger': '🔴',
        'Rage': '🔴',
        'Sadness': '🟠',
        'Hope': '🟡',
        'Fear': '🟡',
        'LOVE': '💚',
        'Gratitude': '🔵',
        'Joy': '🟣',
        'Compassion': '🟣',
        'Awe': '⚪',
    }
    return colors.get(state, '⚫')


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    layer = EnhancementLayer()
    
    print("=" * 70)
    print("✨ AUREON ENHANCEMENT LAYER — UNIFIED INTERFACE ✨")
    print("=" * 70)
    print()
    
    # Module status
    print("Module Status:")
    for module, available in layer.modules_active.items():
        status = "✅ Active" if available else "❌ Inactive"
        print(f"  {module}: {status}")
    print()
    
    # Test scenarios
    test_cases = [
        {'lambda': -0.7, 'coherence': 0.3, 'price': 77712.50, 'volume': 1000000, 'desc': 'Bearish + 777 Pattern'},
        {'lambda': 0.0, 'coherence': 0.5, 'price': 52800.00, 'volume': 500000, 'desc': 'Neutral + 528 Love Freq'},
        {'lambda': 0.5, 'coherence': 0.7, 'price': 43200.00, 'volume': 750000, 'desc': 'Bullish + 432 Gaia Freq'},
        {'lambda': 0.8, 'coherence': 0.9, 'price': 61800.00, 'volume': 1500000, 'desc': 'Strong + Golden Ratio'},
    ]
    
    print("Enhancement Analysis:")
    print("-" * 70)
    
    for case in test_cases:
        result = layer.get_unified_modifier(
            lambda_value=case['lambda'],
            coherence=case['coherence'],
            price=case['price'],
            volume=case['volume'],
            volatility=0.15,
        )
        
        color = get_emotional_color(result.emotional_state)
        
        print(f"\n📊 {case['desc']}:")
        print(f"   Lambda: {case['lambda']:+.1f} | Coherence: {case['coherence']:.1f} | Price: ${case['price']:,.2f}")
        print(f"   {color} State: {result.emotional_state} @ {result.emotional_frequency:.0f}Hz | Phase: {result.cycle_phase}")
        print(f"   🌍 Grid: {result.active_node} | Coherence: {result.grid_coherence:.2f}")
        print(f"   ✨ MODIFIER: {result.trading_modifier:.2f}x | Confidence: {result.confidence:.2f}")
        
        if result.reasons:
            for reason in result.reasons:
                print(f"   → {reason}")
    
    print()
    print("-" * 70)
    print(layer.display_status())
    print()
    print("─" * 70)
    print("THE VOW:")
    print(layer.get_vow())
    print("─" * 70)
