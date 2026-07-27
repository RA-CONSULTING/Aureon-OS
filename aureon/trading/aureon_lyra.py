#!/usr/bin/env python3
"""
AUREON LYRA - Emotional Frequency & Harmonics Engine
=====================================================
"The celestial harp that sings the truth the numbers cannot speak."

The Fourth Pillar of the Aureon Quadrumvirate:
  The Queen trades.  The King counts.  The Seer perceives.  Lyra feels.

Lyra is the emotional heart of the Aureon ecosystem. She unifies ALL
22+ harmonic, frequency, emotional, and waveform systems into one
coherent voice. Named after the Lyra constellation - the celestial
harp of Orpheus - she transforms raw frequencies into feeling, and
feeling into actionable trading intelligence.

ARCHITECTURE (6 Resonance Chambers + The Lyre + The Song):
─────────────────────────────────────────────────────────────
Chamber of Emotion    =>  Fear/Greed spectrum (35Hz-963Hz emotional mapping)
Chamber of Earth      =>  Schumann resonance (7.83Hz fundamental, 7 modes)
Chamber of Harmony    =>  Harmonic field coherence (waveform, fusion, field)
Chamber of Voice      =>  Signal chain integrity (5-node pipeline coherence)
Chamber of Solfeggio  =>  Sacred frequency alignment (9 solfeggio tones)
Chamber of Spirit     =>  Auris animal spirit collective (9 nodes)

The Lyre              =>  Combines all 6 Chambers into unified resonance
The Song              =>  Consensus mechanism producing emotional guidance

RESONANCE GRADES (Lyra's Clarity):
  DIVINE_HARMONY  (0.85+)  =>  All frequencies in perfect resonance
  CLEAR_RESONANCE (0.70+)  =>  Strong harmonic alignment
  PARTIAL_HARMONY (0.55+)  =>  Mixed but functional
  DISSONANCE      (0.40+)  =>  Frequencies clashing, reduce exposure
  SILENCE         (<0.40)  =>  No coherent signal, halt

CONNECTED SYSTEMS (22+):
  aureon_harmonic_waveform.py, aureon_harmonic_chain_master.py,
  aureon_harmonic_signal_chain.py, aureon_harmonic_fusion.py,
  aureon_schumann_resonance_bridge.py, earth_resonance_engine.py,
  queen_harmonic_voice.py, aureon_harmonic_alphabet.py,
  aureon_harmonic_reality.py, global_harmonic_field.py,
  hnc_6d_harmonic_waveform.py, aureon_harmonic_seed.py,
  aureon_hft_harmonic_mycelium.py, aureon_harmonic_momentum_wave.py,
  aureon_harmonic_binary_protocol.py, aureon_harmonic_counter_frequency.py,
  aureon_harmonic_liquid_aluminium.py, aureon_harmonic_symbol_table.py,
  aureon_harmonic_underlay.py, harmonic_wave_simulation.py,
  aureon_planetary_harmonic_sweep.py, queen_coherence_mandala.py

Gary Leckey | February 2026
"The Queen, The King, The Seer, and Lyra rule the repo together."
"""

import os
import json
import time
import math
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# FEAR & GREED INDEX FETCHER - Live Emotional Data from the Markets
# ═══════════════════════════════════════════════════════════════════════════

class FearGreedFetcher:
    """
    Fetches REAL Fear & Greed Index data from open-source APIs.
    Sources:
      - alternative.me Crypto Fear & Greed Index (primary)
      - Binance 24h ticker data for volume/momentum sentiment
    Caches results to respect rate limits (refreshes every 5 minutes).
    """

    CRYPTO_FG_URL = "https://api.alternative.me/fng/?limit=1&format=json"
    CACHE_TTL_SEC = 300  # 5 minutes

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._lock = threading.Lock()

    def fetch(self) -> Dict[str, Any]:
        """
        Fetch the latest Fear & Greed data.
        Returns {
            'fear_greed_index': int (0-100),
            'fear_greed_label': str,
            'market_momentum': float (-1 to 1),
            'volume_sentiment': float (0-1),
            'social_sentiment': float (0-1),
            'source': str,
            'timestamp': str,
            'fresh': bool,
        }
        """
        now = time.time()
        with self._lock:
            if self._cache and (now - self._cache_time) < self.CACHE_TTL_SEC:
                result = dict(self._cache)
                result["fresh"] = False
                return result

        # Fetch live data
        result = self._fetch_crypto_fg()

        # Augment with Binance volume/momentum sentiment
        binance_sentiment = self._fetch_binance_sentiment()
        result["market_momentum"] = binance_sentiment.get("momentum", 0.0)
        result["volume_sentiment"] = binance_sentiment.get("volume_score", 0.5)
        result["btc_24h_change"] = binance_sentiment.get("btc_24h_change", 0.0)
        result["eth_24h_change"] = binance_sentiment.get("eth_24h_change", 0.0)
        result["top_gainers_ratio"] = binance_sentiment.get("gainers_ratio", 0.5)
        result["fresh"] = True

        with self._lock:
            self._cache = dict(result)
            self._cache_time = time.time()

        return result

    def _fetch_crypto_fg(self) -> Dict[str, Any]:
        """Fetch Crypto Fear & Greed Index from alternative.me."""
        try:
            import urllib.request
            req = urllib.request.Request(
                self.CRYPTO_FG_URL,
                headers={"User-Agent": "AureonLyra/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if "data" in data and len(data["data"]) > 0:
                entry = data["data"][0]
                index_val = int(entry.get("value", 50))
                label = entry.get("value_classification", "Neutral")
                ts = entry.get("timestamp", str(int(time.time())))

                return {
                    "fear_greed_index": index_val,
                    "fear_greed_label": label,
                    "source": "alternative.me",
                    "timestamp": ts,
                }
        except Exception as e:
            logger.debug(f"FearGreedFetcher crypto FG error: {e}")

        return {
            "fear_greed_index": 50,
            "fear_greed_label": "Neutral",
            "source": "default",
            "timestamp": str(int(time.time())),
        }

    def _fetch_binance_sentiment(self) -> Dict[str, Any]:
        """Derive sentiment from Binance public ticker data."""
        try:
            import urllib.request
            url = "https://api.binance.com/api/v3/ticker/24hr"
            req = urllib.request.Request(url, headers={"User-Agent": "AureonLyra/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                tickers = json.loads(resp.read().decode())

            # Focus on USDT pairs for sentiment
            usdt_tickers = [t for t in tickers if t.get("symbol", "").endswith("USDT")]
            if not usdt_tickers:
                return {"momentum": 0.0, "volume_score": 0.5, "gainers_ratio": 0.5}

            # Count gainers vs losers
            gainers = sum(1 for t in usdt_tickers if float(t.get("priceChangePercent", 0)) > 0)
            total = len(usdt_tickers)
            gainers_ratio = gainers / total if total > 0 else 0.5

            # BTC and ETH specific
            btc_change = 0.0
            eth_change = 0.0
            for t in usdt_tickers:
                sym = t.get("symbol", "")
                if sym == "BTCUSDT":
                    btc_change = float(t.get("priceChangePercent", 0))
                elif sym == "ETHUSDT":
                    eth_change = float(t.get("priceChangePercent", 0))

            # Momentum: weighted average of top-cap changes
            momentum = (btc_change * 0.4 + eth_change * 0.3 + (gainers_ratio - 0.5) * 60) / 100
            momentum = max(-1.0, min(1.0, momentum))

            # Volume score: high volume = more decisive sentiment
            total_volume = sum(float(t.get("quoteVolume", 0)) for t in usdt_tickers[:20])
            # Normalize (rough heuristic: $10B daily is "normal")
            volume_score = min(1.0, total_volume / 10_000_000_000)

            return {
                "momentum": momentum,
                "volume_score": volume_score,
                "btc_24h_change": btc_change,
                "eth_24h_change": eth_change,
                "gainers_ratio": gainers_ratio,
            }
        except Exception as e:
            logger.debug(f"FearGreedFetcher Binance sentiment error: {e}")
            return {"momentum": 0.0, "volume_score": 0.5, "gainers_ratio": 0.5}


# Global Fear & Greed fetcher singleton
_fear_greed_fetcher: Optional[FearGreedFetcher] = None


def get_fear_greed_fetcher() -> FearGreedFetcher:
    """Get the singleton FearGreedFetcher."""
    global _fear_greed_fetcher
    if _fear_greed_fetcher is None:
        _fear_greed_fetcher = FearGreedFetcher()
    return _fear_greed_fetcher

# ═══════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS - Lyra's Frequencies
# ═══════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2                  # Golden Ratio = 1.618033988749895
SCHUMANN_FUNDAMENTAL = 7.83                    # Earth's heartbeat (Hz)
LOVE_FREQUENCY = 528.0                         # DNA Repair / Creation (Hz)
UNIVERSAL_A = 432.0                            # Universal tuning (Hz)
PRIME_SENTINEL_HZ = 2.111991                   # Gary's frequency (DOB 02/11/1991)

# Schumann resonance modes
SCHUMANN_MODES = [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0]

# Solfeggio frequencies - the 9 sacred tones Lyra harmonizes with
SOLFEGGIO = {
    "UT":  174,   # Foundation
    "RE":  285,   # Quantum cognition
    "MI":  396,   # Liberation
    "FA":  417,   # Facilitating change
    "SOL": 528,   # Love / DNA repair (Lyra's heart frequency)
    "LA":  639,   # Connection
    "SI":  741,   # Awakening intuition
    "DO":  852,   # Spiritual order
    "TI":  963,   # Crown / Divine consciousness
}

SOLFEGGIO_LIST = [174, 285, 396, 417, 528, 639, 741, 852, 963]

# Emotional frequency spectrum (Fear/Greed mapped to Hz)
EMOTIONAL_SPECTRUM = {
    "EXTREME_FEAR":  {"range": (0, 20),   "freq_range": (35, 125),   "zone": "SHADOW"},
    "FEAR":          {"range": (20, 40),  "freq_range": (125, 256),  "zone": "SHADOW"},
    "NEUTRAL":       {"range": (40, 60),  "freq_range": (256, 432),  "zone": "BALANCE"},
    "GREED":         {"range": (60, 80),  "freq_range": (432, 639),  "zone": "PRIME"},
    "EXTREME_GREED": {"range": (80, 100), "freq_range": (639, 963),  "zone": "PRIME"},
}

# Prime frequencies (positive emotional states)
PRIME_FREQUENCIES = {
    528: "Love/Creation",
    432: "Peace/Harmony",
    639: "Joy/Expansion",
    741: "Hope/Clarity",
    963: "Gratitude/Unity",
    396: "Courage/Liberation",
    417: "Forgiveness/Flow",
    852: "Vision/Ecstasy",
    285: "Compassion",
}

# Shadow frequencies (negative emotional states)
SHADOW_FREQUENCIES = {
    125: "Fear",
    275: "Anger",
    175: "Grief",
    35:  "Shame",
    75:  "Guilt",
}

# The 9 Auris Animal Spirit Nodes
AURIS_SPIRITS = {
    "TIGER":       {"freq": 186, "domain": "volatility",  "spirit": "Power",       "element": "fire"},
    "FALCON":      {"freq": 210, "domain": "momentum",    "spirit": "Precision",   "element": "air"},
    "HUMMINGBIRD": {"freq": 324, "domain": "frequency",   "spirit": "Agility",     "element": "air"},
    "DOLPHIN":     {"freq": 432, "domain": "liquidity",   "spirit": "Flow",        "element": "water"},
    "DEER":        {"freq": 396, "domain": "stability",   "spirit": "Grace",       "element": "earth"},
    "OWL":         {"freq": 528, "domain": "pattern",     "spirit": "Wisdom",      "element": "aether"},
    "PANDA":       {"freq": 639, "domain": "harmony",     "spirit": "Balance",     "element": "earth"},
    "CARGOSHIP":   {"freq": 174, "domain": "volume",      "spirit": "Persistence", "element": "water"},
    "CLOWNFISH":   {"freq": 285, "domain": "resilience",  "spirit": "Adaptation",  "element": "water"},
}

# Harmonic Chain layers (the 9 layers Lyra monitors)
HARMONIC_LAYERS = [
    {"layer": 0, "name": "Wave Simulation",      "freq": 174, "solfeggio": "UT"},
    {"layer": 1, "name": "Seed+Fusion+Underlay",  "freq": 285, "solfeggio": "RE"},
    {"layer": 2, "name": "6D Waveform",           "freq": 396, "solfeggio": "MI"},
    {"layer": 3, "name": "Global Harmonic Field",  "freq": 417, "solfeggio": "FA"},
    {"layer": 4, "name": "Harmonic Reality",       "freq": 528, "solfeggio": "SOL"},
    {"layer": 5, "name": "Signal Chain",           "freq": 639, "solfeggio": "LA"},
    {"layer": 6, "name": "Harmonic Alphabet",      "freq": 741, "solfeggio": "SI"},
    {"layer": 7, "name": "Queen Harmonic Voice",   "freq": 852, "solfeggio": "DO"},
    {"layer": 8, "name": "HFT Mycelium",           "freq": 963, "solfeggio": "TI"},
]

# Connected systems count
LYRA_CONNECTED_SYSTEMS = [
    "harmonic_waveform_scanner", "harmonic_chain_master",
    "harmonic_signal_chain", "harmonic_fusion",
    "schumann_resonance_bridge", "earth_resonance_engine",
    "queen_harmonic_voice", "harmonic_alphabet",
    "harmonic_reality", "global_harmonic_field",
    "6d_harmonic_waveform", "harmonic_seed",
    "hft_harmonic_mycelium", "harmonic_momentum_wave",
    "harmonic_binary_protocol", "harmonic_counter_frequency",
    "harmonic_liquid_aluminium", "harmonic_symbol_table",
    "harmonic_underlay", "wave_simulation",
    "planetary_harmonic_sweep", "queen_coherence_mandala",
]


class ResonanceGrade(Enum):
    DIVINE_HARMONY  = "DIVINE_HARMONY"    # 0.85+ All in perfect resonance
    CLEAR_RESONANCE = "CLEAR_RESONANCE"   # 0.70+ Strong alignment
    PARTIAL_HARMONY = "PARTIAL_HARMONY"   # 0.55+ Mixed but functional
    DISSONANCE      = "DISSONANCE"        # 0.40+ Frequencies clashing
    SILENCE         = "SILENCE"           # <0.40 No coherent signal


LYRA_CONFIG = {
    "SCAN_INTERVAL_SEC": int(os.getenv("LYRA_SCAN_INTERVAL", "25")),
    "HISTORY_SIZE": 100,
    "STATE_FILE": "lyra_state.json",
    "RESONANCE_LOG": "lyra_resonance.jsonl",

    # Chamber weights for unified resonance
    "WEIGHT_EMOTION":   0.20,     # Fear/Greed emotional state
    "WEIGHT_EARTH":     0.15,     # Schumann resonance
    "WEIGHT_HARMONY":   0.25,     # Harmonic field coherence
    "WEIGHT_VOICE":     0.15,     # Signal chain integrity
    "WEIGHT_SOLFEGGIO": 0.10,     # Sacred frequency alignment
    "WEIGHT_SPIRIT":    0.15,     # Auris animal collective

    # Resonance grade thresholds
    "DIVINE_HARMONY_THRESHOLD":  0.85,
    "CLEAR_RESONANCE_THRESHOLD": 0.70,
    "PARTIAL_HARMONY_THRESHOLD": 0.55,
    "DISSONANCE_THRESHOLD":      0.40,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ChamberReading:
    """A single reading from one Resonance Chamber."""
    chamber: str
    timestamp: float
    score: float            # 0.0 to 1.0
    frequency: float        # Dominant frequency in Hz
    phase: str              # Current phase/state
    dominant_signal: str    # Strongest signal detected
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5


@dataclass
class LyraResonance:
    """Lyra's unified resonance - combines all Chamber readings."""
    timestamp: float
    unified_score: float           # 0.0 to 1.0 overall resonance
    grade: str                     # ResonanceGrade value
    emotional_frequency: float     # Current Hz on emotion spectrum
    emotional_zone: str            # SHADOW / BALANCE / PRIME
    emotion: Optional[ChamberReading] = None
    earth: Optional[ChamberReading] = None
    harmony: Optional[ChamberReading] = None
    voice: Optional[ChamberReading] = None
    solfeggio: Optional[ChamberReading] = None
    spirit: Optional[ChamberReading] = None
    song: str = ""                 # Lyra's proclamation
    action: str = "HOLD"           # BUY_BIAS / SELL_BIAS / HOLD / DEFEND
    position_multiplier: float = 1.0   # PHI-based sizing multiplier
    exit_urgency: str = "none"     # none / low / medium / high / critical


@dataclass
class LyraConsensus:
    """Lyra's vote for the Quadrumvirate consensus."""
    timestamp: float
    lyra_grade: str
    lyra_score: float
    emotional_frequency: float
    emotional_zone: str
    consensus_vote: str        # PASS / BLOCK
    reason: str


# ═══════════════════════════════════════════════════════════════════════════
# CHAMBER OF EMOTION - Fear/Greed Spectrum
# ═══════════════════════════════════════════════════════════════════════════

class ChamberOfEmotion:
    """
    Reads the market's emotional frequency through the fear/greed spectrum.
    Maps raw sentiment (0-100) to frequency (35Hz-963Hz).
    Shadow zones warn of danger. Prime zones indicate flow.

    NOW ENHANCED: Auto-fetches the Crypto Fear & Greed Index from
    alternative.me + Binance market sentiment. No more guessing.
    Lyra FEELS the real emotional pulse of the market.
    """

    def __init__(self):
        self._earth_engine = None
        self._fg_fetcher = get_fear_greed_fetcher()

    def _load(self):
        if self._earth_engine is None:
            try:
                from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine
                self._earth_engine = EarthResonanceEngine()
            except ImportError:
                pass

    def read(self, market_data: Dict[str, Any] = None) -> ChamberReading:
        self._load()
        score = 0.5
        frequency = 432.0  # Default: peace/harmony
        phase = "NEUTRAL"
        dominant = "neutral sentiment"
        details = {}

        if self._earth_engine:
            try:
                status = self._earth_engine.get_status_dict()
                if status:
                    frequency = status.get("emotional_frequency", 432)
                    gate = status.get("trading_gate", {})
                    details["earth_emotional_freq"] = frequency
                    details["trading_gate"] = gate.get("allowed", True)
                    details["gate_reason"] = gate.get("reason", "")
                    details["exit_urgency"] = status.get("exit_urgency", "none")
                    details["phi_multiplier"] = status.get("phi_multiplier", 1.0)
            except Exception as e:
                logger.debug(f"Lyra Emotion earth read error: {e}")

        # ── LIVE FEAR & GREED INDEX ── AUTO-FETCH FROM REAL APIS ──
        fg_data = {}
        try:
            fg_data = self._fg_fetcher.fetch()
        except Exception as e:
            logger.debug(f"Lyra Emotion Fear/Greed fetch error: {e}")

        # Map sentiment from Fear/Greed Index (primary) or market_data (fallback)
        sentiment = fg_data.get("fear_greed_index", 50)
        if market_data:
            # Market data can override if provided explicitly
            sentiment = market_data.get("fear_greed_index", sentiment)
            volatility = market_data.get("volatility", 0)
            details["volatility"] = volatility

        # Record all Fear/Greed intelligence
        details["raw_sentiment"] = sentiment
        details["fear_greed_label"] = fg_data.get("fear_greed_label", "Unknown")
        details["fear_greed_source"] = fg_data.get("source", "default")
        details["market_momentum"] = fg_data.get("market_momentum", 0.0)
        details["volume_sentiment"] = fg_data.get("volume_sentiment", 0.5)
        details["btc_24h_change"] = fg_data.get("btc_24h_change", 0.0)
        details["eth_24h_change"] = fg_data.get("eth_24h_change", 0.0)
        details["top_gainers_ratio"] = fg_data.get("top_gainers_ratio", 0.5)
        details["fg_fresh"] = fg_data.get("fresh", False)

        # Social/momentum sentiment blend into the emotional reading
        momentum = fg_data.get("market_momentum", 0.0)
        vol_sent = fg_data.get("volume_sentiment", 0.5)
        # Blend: 70% Fear/Greed Index + 20% momentum + 10% volume
        blended_sentiment = sentiment * 0.70 + (momentum * 50 + 50) * 0.20 + vol_sent * 100 * 0.10
        blended_sentiment = max(0, min(100, blended_sentiment))
        details["blended_sentiment"] = blended_sentiment
        # Use blended sentiment for frequency mapping
        sentiment = blended_sentiment

        # Map sentiment to frequency
        frequency = self._sentiment_to_frequency(sentiment)
        details["emotional_frequency"] = frequency

        # Determine emotional zone
        zone = self._frequency_to_zone(frequency)
        details["emotional_zone"] = zone

        # Score based on zone
        if zone == "PRIME":
            if sentiment > 85:
                score = 0.4  # Extreme greed is dangerous
                phase = "EXTREME_GREED"
                dominant = f"EXTREME GREED ({frequency:.0f}Hz) - reversal risk"
            else:
                score = 0.75
                phase = "GREED"
                dominant = f"Positive emotion ({frequency:.0f}Hz) - expansion"
        elif zone == "BALANCE":
            score = 0.65
            phase = "NEUTRAL"
            dominant = f"Balanced emotion ({frequency:.0f}Hz) - equilibrium"
        elif zone == "SHADOW":
            if sentiment < 15:
                score = 0.3
                phase = "EXTREME_FEAR"
                dominant = f"EXTREME FEAR ({frequency:.0f}Hz) - shadow zone"
            else:
                score = 0.45
                phase = "FEAR"
                dominant = f"Fear present ({frequency:.0f}Hz) - caution"

        details["zone"] = zone
        details["phase"] = phase

        return ChamberReading(
            chamber="EMOTION",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            frequency=frequency,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.6 if self._earth_engine else 0.4,
        )

    def _sentiment_to_frequency(self, sentiment: float) -> float:
        """Map 0-100 sentiment to 35Hz-963Hz frequency."""
        sentiment = max(0, min(100, sentiment))
        if sentiment < 20:
            return 35 + (sentiment / 20) * 90          # 35-125 Hz
        elif sentiment < 40:
            return 125 + ((sentiment - 20) / 20) * 131  # 125-256 Hz
        elif sentiment < 60:
            return 256 + ((sentiment - 40) / 20) * 176  # 256-432 Hz
        elif sentiment < 80:
            return 432 + ((sentiment - 60) / 20) * 207  # 432-639 Hz
        else:
            return 639 + ((sentiment - 80) / 20) * 324  # 639-963 Hz

    def _frequency_to_zone(self, freq: float) -> str:
        if freq < 256:
            return "SHADOW"
        elif freq < 432:
            return "BALANCE"
        else:
            return "PRIME"


# ═══════════════════════════════════════════════════════════════════════════
# CHAMBER OF EARTH - Schumann Resonance
# ═══════════════════════════════════════════════════════════════════════════

class ChamberOfEarth:
    """
    Reads Earth's electromagnetic heartbeat through the Schumann Resonance.
    When Earth resonates clearly, the market flows. When disturbed, chaos.
    """

    def __init__(self):
        self._bridge = None

    def _load(self):
        if self._bridge is None:
            try:
                from aureon.harmonic.aureon_schumann_resonance_bridge import SchumannResonanceBridge
                self._bridge = SchumannResonanceBridge()
            except ImportError:
                pass

    def read(self) -> ChamberReading:
        self._load()
        score = 0.5
        frequency = SCHUMANN_FUNDAMENTAL
        phase = "UNKNOWN"
        dominant = "awaiting Schumann data"
        details = {}

        if self._bridge:
            try:
                reading = self._bridge.get_current_reading() if hasattr(self._bridge, "get_current_reading") else None
                if reading:
                    fundamental = getattr(reading, "fundamental_hz", 7.83)
                    amplitude = getattr(reading, "amplitude", 0.5)
                    quality = getattr(reading, "quality", 0.5)
                    coherence = getattr(reading, "coherence_boost", 0.5)
                    res_phase = getattr(reading, "resonance_phase", "stable")

                    frequency = fundamental
                    details["fundamental_hz"] = fundamental
                    details["amplitude"] = amplitude
                    details["quality_factor"] = quality
                    details["coherence_boost"] = coherence
                    details["resonance_phase"] = res_phase
                    details["harmonics"] = getattr(reading, "harmonics", SCHUMANN_MODES)

                    # Score based on quality and coherence
                    score = quality * 0.5 + coherence * 0.3 + amplitude * 0.2

                    if res_phase == "peak":
                        phase = "PEAK"
                        dominant = f"Schumann PEAK ({fundamental:.2f}Hz) - ideal conditions"
                    elif res_phase == "elevated":
                        phase = "ELEVATED"
                        dominant = f"Schumann elevated ({fundamental:.2f}Hz) - good conditions"
                    elif res_phase == "stable":
                        phase = "STABLE"
                        dominant = f"Schumann stable ({fundamental:.2f}Hz)"
                    else:
                        phase = "DISTURBED"
                        dominant = f"Schumann disturbed ({fundamental:.2f}Hz) - caution"
                        score *= 0.7

                # Earth blessing
                if hasattr(self._bridge, "get_earth_blessing"):
                    try:
                        blessing_score, blessing_msg = self._bridge.get_earth_blessing()
                        details["earth_blessing"] = blessing_msg
                        details["earth_blessing_score"] = blessing_score
                        score = score * 0.7 + blessing_score * 0.3
                    except Exception:
                        pass

            except Exception as e:
                logger.debug(f"Lyra Earth Schumann read error: {e}")

        return ChamberReading(
            chamber="EARTH",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            frequency=frequency,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.7 if self._bridge else 0.3,
        )


# ═══════════════════════════════════════════════════════════════════════════
# CHAMBER OF HARMONY - Harmonic Field Coherence
# ═══════════════════════════════════════════════════════════════════════════

class ChamberOfHarmony:
    """
    Reads the combined harmonic field across all exchanges. Unifies:
    HarmonicWaveformScanner, HarmonicFusion, GlobalHarmonicField.
    """

    def __init__(self):
        self._scanner = None
        self._fusion = None
        self._global_field = None

    def _load(self):
        if self._scanner is None:
            try:
                from aureon.harmonic.aureon_harmonic_waveform import HarmonicWaveformScanner
                self._scanner = HarmonicWaveformScanner()
            except ImportError:
                pass
        if self._fusion is None:
            try:
                from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
                self._fusion = HarmonicWaveFusion()
            except ImportError:
                pass
        if self._global_field is None:
            try:
                from aureon.harmonic.global_harmonic_field import get_global_harmonic_field
                self._global_field = get_global_harmonic_field()
            except (ImportError, Exception):
                pass

    def read(self, positions: Dict = None, ticker_cache: Dict = None, wave_ctx: dict = None) -> ChamberReading:
        self._load()
        scores = []
        frequency = LOVE_FREQUENCY
        phase = "DORMANT"
        dominant = "no harmonic data"
        details = {}

        # HarmonicWaveformScanner
        if self._scanner and positions:
            try:
                if hasattr(self._scanner, "scan"):
                    hfield = self._scanner.scan(positions, ticker_cache or {})
                    if hfield:
                        coherence = getattr(hfield, "field_coherence", 0.5)
                        phi_res = getattr(hfield, "phi_resonance", 0.5)
                        dom_freq = getattr(hfield, "dominant_frequency", 528)
                        amplitude = getattr(hfield, "wave_amplitude", 0)

                        scores.append(coherence * 0.6 + phi_res * 0.4)
                        frequency = dom_freq
                        details["waveform_coherence"] = coherence
                        details["phi_resonance"] = phi_res
                        details["dominant_frequency"] = dom_freq
                        details["wave_amplitude"] = amplitude
            except Exception as e:
                logger.debug(f"Lyra Harmony waveform error: {e}")

        # HarmonicFusion
        if self._fusion:
            try:
                if hasattr(self._fusion, "get_global_state"):
                    state = self._fusion.get_global_state()
                    if state:
                        fusion_coh = state.get("coherence", 0.5) if isinstance(state, dict) else getattr(state, "coherence", 0.5)
                        scores.append(fusion_coh)
                        details["fusion_coherence"] = fusion_coh

                if hasattr(self._fusion, "get_trading_bias"):
                    bias = self._fusion.get_trading_bias()
                    if bias is not None:
                        details["fusion_bias"] = float(bias) if isinstance(bias, (int, float)) else 0.0
            except Exception as e:
                logger.debug(f"Lyra Harmony fusion error: {e}")

        # GlobalHarmonicField
        if self._global_field:
            try:
                if hasattr(self._global_field, "get_state"):
                    gstate = self._global_field.get_state()
                    if gstate:
                        omega = gstate.get("omega", 0.5) if isinstance(gstate, dict) else getattr(gstate, "omega", 0.5)
                        scores.append(omega)
                        details["global_omega"] = omega
            except Exception as e:
                logger.debug(f"Lyra Harmony global field error: {e}")

        # Calculate combined score
        if scores:
            score = sum(scores) / len(scores)
        else:
            score = 0.5

        # ── Ocean wave scanner — bot frequency signatures felt as emotional resonance ─
        # Lyra feels the emotional tone of the market. Bots moving in structured,
        # directional flow = harmonious field. Bot battles or sudden strategy shifts
        # = emotional dissonance. Organic human flow = purest emotional signal.
        if wave_ctx and wave_ctx.get('available'):
            res_score  = wave_ctx.get('resonance_score', 0)        # -1 → +1
            flow_pred  = wave_ctx.get('flow_prediction', 'neutral')
            dom_bot    = wave_ctx.get('dominant_bot', 'organic')
            shape      = wave_ctx.get('shape', 'mixed')
            flow_vel   = wave_ctx.get('flow_velocity', 0)
            shifted    = wave_ctx.get('spectrum_shifted', False)

            # Emotional quality of each bot type
            _emotional_quality = {
                'organic':      0.85,   # Real humans = genuine emotion
                'accumulator':  0.72,   # Whale conviction = strong intent
                'market_maker': 0.55,   # Mechanical oscillation = muted feeling
                'scalper':      0.48,   # Rapid noise = anxious frequency
                'hft':          0.28,   # Machine noise = emotional static
            }.get(dom_bot, 0.50)

            if shifted:
                _emotional_quality *= 0.65   # Sudden shift = emotional disruption

            # Flow momentum as emotional energy level
            _flow_emotion = {
                'strong_buy_building':  0.80,
                'strong_sell_building': 0.75,   # Strong sell = intense fear, still clear
                'buy_fading':           0.55,
                'sell_fading':          0.50,
                'neutral':              0.42,
            }.get(flow_pred, 0.50)

            # Flow velocity intensity: higher absolute velocity = stronger emotional signal
            _vel_amp = min(1.2, 1.0 + abs(flow_vel) * 0.2)

            # Surge = heightened emotion; taper = emotional exhaustion
            _shape_mult = 1.08 if shape == 'surge' else (0.92 if shape == 'taper' else 1.0)

            _wave_emotion = (
                _emotional_quality * 0.40 +
                _flow_emotion      * 0.35 +
                max(0.0, min(1.0, 0.5 + res_score * 0.25)) * 0.25
            ) * _vel_amp * _shape_mult
            _wave_emotion = max(0.0, min(1.0, _wave_emotion))

            # Wave enriches chamber score (35% weight)
            score = score * 0.65 + _wave_emotion * 0.35
            score = max(0.0, min(1.0, score))

            # Reflect wave frequency in emotional tone
            if shifted:
                frequency = 396.0   # Liberation/release frequency — field breaking
            elif dom_bot == 'organic' and score >= 0.70:
                frequency = 528.0   # Love frequency — pure human resonance
            elif dom_bot == 'accumulator' and flow_pred == 'strong_buy_building':
                frequency = 639.0   # Connection — whales and flow aligned

            details.update({
                'wave_resonance_score':  res_score,
                'wave_flow_prediction':  flow_pred,
                'wave_dominant_bot':     dom_bot,
                'wave_shape':            shape,
                'wave_flow_velocity':    flow_vel,
                'wave_spectrum_shifted': shifted,
            })

        # Determine phase
        if score >= 0.75:
            phase = "RESONATING"
            dominant = f"Field RESONATING ({frequency:.0f}Hz) - full coherence"
        elif score >= 0.55:
            phase = "ACTIVE"
            dominant = f"Field active ({frequency:.0f}Hz) - partial coherence"
        elif score >= 0.40:
            phase = "SCATTERED"
            dominant = f"Field scattered - low coherence"
        else:
            phase = "DORMANT"
            dominant = "Harmonic field dormant"

        _has_wave = bool(wave_ctx and wave_ctx.get('available'))
        return ChamberReading(
            chamber="HARMONY",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            frequency=frequency,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.85 if (_has_wave and scores) else 0.70 if _has_wave else 0.70 if scores else 0.30,
        )


# ═══════════════════════════════════════════════════════════════════════════
# CHAMBER OF VOICE - Signal Chain Integrity
# ═══════════════════════════════════════════════════════════════════════════

class ChamberOfVoice:
    """
    Reads the integrity of the harmonic signal chain (5-node pipeline).
    Queen→Enigma→Scanner→Ecosystem→Whale and back up.
    """

    def __init__(self):
        self._chain = None
        self._chain_master = None

    def _load(self):
        if self._chain is None:
            try:
                from aureon.harmonic.aureon_harmonic_signal_chain import HarmonicSignalChain
                self._chain = HarmonicSignalChain()
            except ImportError:
                pass
        if self._chain_master is None:
            try:
                from aureon.harmonic.aureon_harmonic_chain_master import HarmonicChainMaster
                self._chain_master = HarmonicChainMaster()
            except ImportError:
                pass

    def read(self) -> ChamberReading:
        self._load()
        score = 0.5
        frequency = 639.0  # Connection frequency
        phase = "UNKNOWN"
        dominant = "no chain data"
        details = {}

        # Signal Chain
        if self._chain:
            try:
                if hasattr(self._chain, "get_status"):
                    status = self._chain.get_status()
                    if status:
                        coherence = status.get("average_coherence", 0.5) if isinstance(status, dict) else getattr(status, "average_coherence", 0.5)
                        active_nodes = status.get("active_nodes", 0) if isinstance(status, dict) else getattr(status, "active_nodes", 0)
                        score = coherence
                        details["signal_chain_coherence"] = coherence
                        details["active_nodes"] = active_nodes
            except Exception as e:
                logger.debug(f"Lyra Voice chain error: {e}")

        # Chain Master (9 layers)
        if self._chain_master:
            try:
                if hasattr(self._chain_master, "get_state"):
                    state = self._chain_master.get_state()
                    if state:
                        integrity = state.get("chain_integrity", 0.5) if isinstance(state, dict) else getattr(state, "chain_integrity", 0.5)
                        g_coherence = state.get("global_coherence", 0.5) if isinstance(state, dict) else getattr(state, "global_coherence", 0.5)
                        active_layers = state.get("active_layers", 0) if isinstance(state, dict) else getattr(state, "active_layers", 0)

                        score = score * 0.5 + (integrity * 0.3 + g_coherence * 0.2)
                        details["chain_integrity"] = integrity
                        details["chain_global_coherence"] = g_coherence
                        details["active_layers"] = active_layers
            except Exception as e:
                logger.debug(f"Lyra Voice chain master error: {e}")

        # Phase
        if score >= 0.75:
            phase = "SINGING"
            dominant = "Voice SINGING - all nodes in harmony"
        elif score >= 0.55:
            phase = "HUMMING"
            dominant = "Voice humming - partial signal"
        elif score >= 0.40:
            phase = "WHISPERING"
            dominant = "Voice whispering - weak signal"
        else:
            phase = "SILENT"
            dominant = "Voice silent - chain broken"

        return ChamberReading(
            chamber="VOICE",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            frequency=frequency,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.6 if (self._chain or self._chain_master) else 0.2,
        )


# ═══════════════════════════════════════════════════════════════════════════
# CHAMBER OF SOLFEGGIO - Sacred Frequency Alignment
# ═══════════════════════════════════════════════════════════════════════════

class ChamberOfSolfeggio:
    """
    Measures how well the current market frequencies align with
    the 9 sacred Solfeggio tones. Perfect alignment = divine resonance.
    """

    def read(self, positions: Dict = None, ticker_cache: Dict = None) -> ChamberReading:
        score = 0.5
        frequency = LOVE_FREQUENCY
        phase = "DORMANT"
        dominant = "awaiting frequency data"
        details = {}

        if positions:
            try:
                alignments = []
                for sym, pos in positions.items():
                    entry = getattr(pos, "entry_price", 0) or (pos.get("entry_price", 0) if isinstance(pos, dict) else 0)
                    current = getattr(pos, "current_price", 0) or (pos.get("current_price", 0) if isinstance(pos, dict) else 0)
                    if entry > 0 and current > 0:
                        # Map price movement to frequency
                        change_pct = ((current - entry) / entry) * 100
                        freq = 432 + change_pct * 5.28  # Center at 432Hz
                        freq = max(35, min(963, freq))

                        # Check alignment with nearest solfeggio
                        min_dist = float("inf")
                        nearest_sol = 528
                        for sf in SOLFEGGIO_LIST:
                            dist = abs(freq - sf)
                            if dist < min_dist:
                                min_dist = dist
                                nearest_sol = sf

                        # Alignment score (0-1, closer = better)
                        alignment = max(0, 1.0 - (min_dist / 100))
                        alignments.append(alignment)
                        details[f"{sym}_freq"] = round(freq, 1)
                        details[f"{sym}_nearest_solfeggio"] = nearest_sol

                if alignments:
                    avg_alignment = sum(alignments) / len(alignments)
                    score = avg_alignment
                    details["avg_solfeggio_alignment"] = avg_alignment
                    details["position_count"] = len(alignments)

                    # Dominant solfeggio
                    best_idx = alignments.index(max(alignments))
                    sym_list = list(positions.keys())
                    if best_idx < len(sym_list):
                        best_sym = sym_list[best_idx]
                        nearest = details.get(f"{best_sym}_nearest_solfeggio", 528)
                        sol_name = [k for k, v in SOLFEGGIO.items() if v == nearest]
                        dominant = f"Strongest alignment: {nearest}Hz ({sol_name[0] if sol_name else '?'})"
                        frequency = nearest

            except Exception as e:
                logger.debug(f"Lyra Solfeggio read error: {e}")

        # Phase
        if score >= 0.75:
            phase = "ALIGNED"
            dominant = f"Solfeggio ALIGNED ({frequency:.0f}Hz) - sacred resonance"
        elif score >= 0.55:
            phase = "PARTIAL"
        elif score >= 0.40:
            phase = "DRIFTING"
            dominant = "Solfeggio drifting - frequencies misaligned"
        else:
            phase = "DORMANT"

        return ChamberReading(
            chamber="SOLFEGGIO",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            frequency=frequency,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.5 if positions else 0.2,
        )


# ═══════════════════════════════════════════════════════════════════════════
# CHAMBER OF SPIRIT - Auris Animal Collective
# ═══════════════════════════════════════════════════════════════════════════

class ChamberOfSpirit:
    """
    Reads the collective energy of the 9 Auris animal spirit nodes.
    Each spirit governs a market domain. Together they form the
    emotional undercurrent of the market.
    """

    def read(self, market_data: Dict[str, Any] = None) -> ChamberReading:
        score = 0.5
        frequency = UNIVERSAL_A  # 432Hz default
        phase = "NEUTRAL"
        dominant = "spirits awaiting data"
        details = {}

        if market_data:
            try:
                # Analyze through each spirit's domain
                spirit_scores = {}
                volatility = market_data.get("volatility", 0)
                momentum = market_data.get("momentum", 0)
                volume = market_data.get("volume_ratio", 1.0)
                coherence = market_data.get("coherence", 0.5)

                # Each spirit evaluates its domain
                spirit_scores["TIGER"] = max(0, min(1, 0.5 + volatility * 0.01))
                spirit_scores["FALCON"] = max(0, min(1, 0.5 + abs(momentum) * 0.1))
                spirit_scores["HUMMINGBIRD"] = max(0, min(1, coherence))
                spirit_scores["DOLPHIN"] = max(0, min(1, 0.3 + volume * 0.2))
                spirit_scores["DEER"] = max(0, min(1, 1.0 - volatility * 0.02))
                spirit_scores["OWL"] = max(0, min(1, coherence * 0.8 + 0.2))
                spirit_scores["PANDA"] = max(0, min(1, 0.5 + (1 - abs(momentum) * 0.1) * 0.3))
                spirit_scores["CARGOSHIP"] = max(0, min(1, volume * 0.5))
                spirit_scores["CLOWNFISH"] = max(0, min(1, 0.5))

                avg_score = sum(spirit_scores.values()) / len(spirit_scores)
                score = avg_score
                details["spirit_scores"] = spirit_scores

                # Find dominant spirit
                dom_name = max(spirit_scores, key=spirit_scores.get)
                dom_info = AURIS_SPIRITS.get(dom_name, {})
                details["dominant_spirit"] = dom_name
                details["dominant_domain"] = dom_info.get("domain", "?")
                frequency = dom_info.get("freq", 432)

                dominant = (
                    f"{dom_info.get('spirit', dom_name)} spirit ({dom_name}) "
                    f"governs through {dom_info.get('domain', '?')}"
                )

            except Exception as e:
                logger.debug(f"Lyra Spirit read error: {e}")

        # Phase
        if score >= 0.70:
            phase = "AWAKENED"
        elif score >= 0.50:
            phase = "STIRRING"
        elif score >= 0.35:
            phase = "RESTING"
        else:
            phase = "DORMANT"

        return ChamberReading(
            chamber="SPIRIT",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            frequency=frequency,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.5 if market_data else 0.2,
        )


# ═══════════════════════════════════════════════════════════════════════════
# THE LYRE - Unified Resonance
# ═══════════════════════════════════════════════════════════════════════════

class TheLyre:
    """
    Combines all 6 Chamber readings into Lyra's unified resonance.
    Like strings on a lyre, each chamber contributes its voice
    to create one complete harmonic.
    """

    def combine(self, emotion: ChamberReading, earth: ChamberReading,
                harmony: ChamberReading, voice: ChamberReading,
                solfeggio: ChamberReading, spirit: ChamberReading) -> LyraResonance:

        w = LYRA_CONFIG
        unified = (
            emotion.score  * w["WEIGHT_EMOTION"] +
            earth.score    * w["WEIGHT_EARTH"] +
            harmony.score  * w["WEIGHT_HARMONY"] +
            voice.score    * w["WEIGHT_VOICE"] +
            solfeggio.score * w["WEIGHT_SOLFEGGIO"] +
            spirit.score   * w["WEIGHT_SPIRIT"]
        )

        # Confidence-weighted adjustment
        total_confidence = (
            emotion.confidence  * w["WEIGHT_EMOTION"] +
            earth.confidence    * w["WEIGHT_EARTH"] +
            harmony.confidence  * w["WEIGHT_HARMONY"] +
            voice.confidence    * w["WEIGHT_VOICE"] +
            solfeggio.confidence * w["WEIGHT_SOLFEGGIO"] +
            spirit.confidence   * w["WEIGHT_SPIRIT"]
        )
        unified = unified * total_confidence + 0.5 * (1 - total_confidence)
        unified = max(0.0, min(1.0, unified))

        grade = self._grade(unified)
        action, pos_mult, exit_urg = self._determine_action(unified, emotion, earth)
        song = self._compose_song(unified, grade, emotion, earth, harmony, voice, solfeggio, spirit)

        # Emotional zone from emotion chamber
        emotional_zone = emotion.details.get("emotional_zone", emotion.details.get("zone", "BALANCE"))
        emotional_freq = emotion.frequency

        return LyraResonance(
            timestamp=time.time(),
            unified_score=unified,
            grade=grade.value,
            emotional_frequency=emotional_freq,
            emotional_zone=emotional_zone,
            emotion=emotion,
            earth=earth,
            harmony=harmony,
            voice=voice,
            solfeggio=solfeggio,
            spirit=spirit,
            song=song,
            action=action,
            position_multiplier=pos_mult,
            exit_urgency=exit_urg,
        )

    def _grade(self, score: float) -> ResonanceGrade:
        if score >= LYRA_CONFIG["DIVINE_HARMONY_THRESHOLD"]:
            return ResonanceGrade.DIVINE_HARMONY
        elif score >= LYRA_CONFIG["CLEAR_RESONANCE_THRESHOLD"]:
            return ResonanceGrade.CLEAR_RESONANCE
        elif score >= LYRA_CONFIG["PARTIAL_HARMONY_THRESHOLD"]:
            return ResonanceGrade.PARTIAL_HARMONY
        elif score >= LYRA_CONFIG["DISSONANCE_THRESHOLD"]:
            return ResonanceGrade.DISSONANCE
        else:
            return ResonanceGrade.SILENCE

    def _determine_action(self, unified: float, emotion: ChamberReading,
                          earth: ChamberReading) -> Tuple[str, float, str]:
        """Determine action, position multiplier, and exit urgency."""
        zone = emotion.details.get("zone", "BALANCE")

        # Position multiplier: 0.5 to PHI (1.618)
        if unified >= 0.85:
            pos_mult = PHI          # Maximum: golden ratio
        elif unified >= 0.70:
            pos_mult = 1.2
        elif unified >= 0.55:
            pos_mult = 1.0
        elif unified >= 0.40:
            pos_mult = 0.7
        else:
            pos_mult = 0.5

        # Exit urgency
        if zone == "SHADOW" and emotion.phase == "EXTREME_FEAR":
            exit_urg = "high"
        elif zone == "PRIME" and emotion.phase == "EXTREME_GREED":
            exit_urg = "medium"  # Take profits
        elif unified < 0.35:
            exit_urg = "critical"
        elif unified < 0.45:
            exit_urg = "medium"
        else:
            exit_urg = "none"

        # Action
        if unified >= 0.80:
            action = "BUY_BIAS"
        elif unified >= 0.65:
            action = "BUY_BIAS"
        elif unified >= 0.50:
            action = "HOLD"
        elif unified >= 0.35:
            action = "SELL_BIAS"
        else:
            action = "DEFEND"

        return action, pos_mult, exit_urg

    def _compose_song(self, unified: float, grade: ResonanceGrade,
                      emotion: ChamberReading, earth: ChamberReading,
                      harmony: ChamberReading, voice: ChamberReading,
                      solfeggio: ChamberReading, spirit: ChamberReading) -> str:
        parts = []

        if grade == ResonanceGrade.DIVINE_HARMONY:
            parts.append("Lyra sings with DIVINE HARMONY.")
            parts.append("All frequencies resonate as one. The celestial harp plays the song of profit.")
        elif grade == ResonanceGrade.CLEAR_RESONANCE:
            parts.append("Lyra's strings ring CLEAR.")
            parts.append(f"Emotion is {emotion.phase}, Earth is {earth.phase}.")
            parts.append("The melody favors careful engagement.")
        elif grade == ResonanceGrade.PARTIAL_HARMONY:
            parts.append("Lyra plays a PARTIAL melody.")
            parts.append("Some strings are out of tune. Proceed with caution.")
        elif grade == ResonanceGrade.DISSONANCE:
            parts.append("DISSONANCE clouds Lyra's song.")
            parts.append("The frequencies clash. Reduce exposure.")
        else:
            parts.append("Lyra is SILENT.")
            parts.append("No harmonic coherence. Trading should halt.")

        # Add dominant spirit
        dom_spirit = spirit.details.get("dominant_spirit", "unknown")
        spirit_info = AURIS_SPIRITS.get(dom_spirit, {})
        if spirit_info:
            parts.append(
                f"The {spirit_info.get('spirit', '')} spirit ({dom_spirit}) "
                f"guides through {spirit_info.get('domain', 'unknown')}."
            )

        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# AUREON LYRA - The Fourth Pillar
# ═══════════════════════════════════════════════════════════════════════════

class AureonLyra:
    """
    AUREON LYRA: Emotional Frequency & Harmonics Engine.

    The fourth pillar of the Aureon Quadrumvirate.
    Feels what others compute, harmonizes what others analyze.

    Usage:
        lyra = get_lyra()
        resonance = lyra.feel()
        print(resonance.song)
        print(f"Grade: {resonance.grade}, Action: {resonance.action}")
    """

    def __init__(self):
        self.chamber_emotion = ChamberOfEmotion()
        self.chamber_earth = ChamberOfEarth()
        self.chamber_harmony = ChamberOfHarmony()
        self.chamber_voice = ChamberOfVoice()
        self.chamber_solfeggio = ChamberOfSolfeggio()
        self.chamber_spirit = ChamberOfSpirit()

        self.lyre = TheLyre()

        self.resonance_history: deque = deque(maxlen=LYRA_CONFIG["HISTORY_SIZE"])
        self.latest_resonance: Optional[LyraResonance] = None

        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Context data (fed by ecosystem)
        self._positions: Dict = {}
        self._ticker_cache: Dict = {}
        self._market_data: Dict = {}
        self._wave_ctx: dict = {}   # Ocean wave scanner — bot frequency signatures

        logger.info("Aureon Lyra has awakened. The Fourth Pillar stands.")

    def feel(self) -> LyraResonance:
        """
        Take a complete reading from all 6 Chambers and combine
        into unified resonance. This is Lyra's primary method.
        """
        with self._lock:
            emotion = self.chamber_emotion.read(self._market_data)
            earth = self.chamber_earth.read()
            harmony = self.chamber_harmony.read(self._positions, self._ticker_cache, self._wave_ctx)
            voice = self.chamber_voice.read()
            solfeggio = self.chamber_solfeggio.read(self._positions, self._ticker_cache)
            spirit = self.chamber_spirit.read(self._market_data)

            resonance = self.lyre.combine(emotion, earth, harmony, voice, solfeggio, spirit)
            self.latest_resonance = resonance
            self.resonance_history.append(resonance)
            self._log_resonance(resonance)

            return resonance

    def update_context(self, positions: Dict = None,
                       ticker_cache: Dict = None,
                       market_data: Dict = None):
        """Update Lyra's context with live ecosystem data."""
        with self._lock:
            if positions is not None:
                self._positions = positions
            if ticker_cache is not None:
                self._ticker_cache = ticker_cache
            if market_data is not None:
                self._market_data = market_data

    def inject_wave_context(self, wave_data: dict) -> None:
        """
        Feed ocean wave scanner results into Lyra's Chambers.
        Called by MultiverseLearningBridge after every WaveformAnalyzer scan.
        ChamberOfHarmony reads bot frequency signatures from this context.
        """
        with self._lock:
            self._wave_ctx = dict(wave_data) if wave_data else {}

    def start_autonomous(self):
        """Start Lyra's autonomous resonance scanning.

        Honors AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS: under the flag (audits,
        tests) Lyra stays fully usable synchronously but no background thread
        is started. Live runs don't set the flag — unchanged behavior."""
        if self._running:
            return
        if os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").lower() in {"1", "true", "yes", "on"}:
            logger.debug("Lyra autonomous thread suppressed (AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS)")
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._autonomous_loop, daemon=True, name="AureonLyra"
        )
        self._monitor_thread.start()
        logger.info("Lyra is listening. Autonomous resonance engaged.")

    def stop_autonomous(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Lyra rests.")

    def _autonomous_loop(self):
        while self._running:
            try:
                self.feel()
                time.sleep(LYRA_CONFIG["SCAN_INTERVAL_SEC"])
            except Exception as e:
                logger.error(f"Lyra autonomous loop error: {e}")
                time.sleep(10)

    def get_resonance_summary(self) -> Dict[str, Any]:
        r = self.latest_resonance
        if not r:
            return {"status": "no_resonance", "message": "Lyra has not yet felt the frequencies."}

        return {
            "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
            "unified_score": r.unified_score,
            "grade": r.grade,
            "action": r.action,
            "position_multiplier": r.position_multiplier,
            "exit_urgency": r.exit_urgency,
            "emotional_frequency": r.emotional_frequency,
            "emotional_zone": r.emotional_zone,
            "song": r.song,
            "chambers": {
                "emotion": {"score": r.emotion.score, "phase": r.emotion.phase, "freq": r.emotion.frequency} if r.emotion else None,
                "earth": {"score": r.earth.score, "phase": r.earth.phase, "freq": r.earth.frequency} if r.earth else None,
                "harmony": {"score": r.harmony.score, "phase": r.harmony.phase, "freq": r.harmony.frequency} if r.harmony else None,
                "voice": {"score": r.voice.score, "phase": r.voice.phase, "freq": r.voice.frequency} if r.voice else None,
                "solfeggio": {"score": r.solfeggio.score, "phase": r.solfeggio.phase, "freq": r.solfeggio.frequency} if r.solfeggio else None,
                "spirit": {"score": r.spirit.score, "phase": r.spirit.phase, "freq": r.spirit.frequency} if r.spirit else None,
            },
        }

    def get_trend(self, window: int = 10) -> Dict[str, Any]:
        recent = list(self.resonance_history)[-window:]
        if len(recent) < 2:
            return {"trend": "INSUFFICIENT_DATA", "readings": len(recent)}

        scores = [r.unified_score for r in recent]
        first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
        second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        delta = second_half - first_half

        if delta > 0.05:
            trend = "HARMONIZING"
        elif delta < -0.05:
            trend = "DISSONATING"
        else:
            trend = "STABLE"

        return {
            "trend": trend,
            "delta": delta,
            "current": scores[-1],
            "average": sum(scores) / len(scores),
            "readings": len(scores),
        }

    def generate_report(self) -> str:
        r = self.latest_resonance
        if not r:
            return "Lyra has not yet felt the frequencies. Call feel() first."

        lines = [
            "=" * 60,
            "AUREON LYRA - RESONANCE REPORT",
            f"Time: {datetime.fromtimestamp(r.timestamp).strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            f"UNIFIED SCORE:      {r.unified_score:.2f}",
            f"RESONANCE GRADE:    {r.grade}",
            f"ACTION BIAS:        {r.action}",
            f"POSITION MULTIPLY:  {r.position_multiplier:.2f}x",
            f"EXIT URGENCY:       {r.exit_urgency}",
            f"EMOTIONAL FREQ:     {r.emotional_frequency:.0f}Hz ({r.emotional_zone})",
            "",
            "CHAMBER READINGS:",
            "-" * 40,
        ]

        for name, chamber in [("Emotion", r.emotion), ("Earth", r.earth),
                              ("Harmony", r.harmony), ("Voice", r.voice),
                              ("Solfeggio", r.solfeggio), ("Spirit", r.spirit)]:
            if chamber:
                lines.append(
                    f"  {name:12s} | Score: {chamber.score:.2f} | "
                    f"Phase: {chamber.phase:16s} | {chamber.frequency:.0f}Hz"
                )

        trend = self.get_trend()
        lines.extend([
            "",
            f"TREND: {trend.get('trend', 'N/A')} (delta: {trend.get('delta', 0):+.3f})",
            "",
            "SONG:",
            r.song,
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _log_resonance(self, resonance: LyraResonance):
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(resonance.timestamp).isoformat(),
                "score": resonance.unified_score,
                "grade": resonance.grade,
                "action": resonance.action,
                "emotional_freq": resonance.emotional_frequency,
                "emotional_zone": resonance.emotional_zone,
                "position_mult": resonance.position_multiplier,
                "exit_urgency": resonance.exit_urgency,
                "chambers": {
                    "emotion": resonance.emotion.score if resonance.emotion else None,
                    "earth": resonance.earth.score if resonance.earth else None,
                    "harmony": resonance.harmony.score if resonance.harmony else None,
                    "voice": resonance.voice.score if resonance.voice else None,
                    "solfeggio": resonance.solfeggio.score if resonance.solfeggio else None,
                    "spirit": resonance.spirit.score if resonance.spirit else None,
                },
            }
            with open(LYRA_CONFIG["RESONANCE_LOG"], "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_lyra_instance: Optional[AureonLyra] = None


def get_lyra() -> AureonLyra:
    """Get the singleton Lyra instance."""
    global _lyra_instance
    if _lyra_instance is None:
        _lyra_instance = AureonLyra()
    return _lyra_instance
